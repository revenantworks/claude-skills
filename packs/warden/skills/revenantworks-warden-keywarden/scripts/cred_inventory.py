#!/usr/bin/env python3
"""cred_inventory.py - where every credential lives, as fingerprints (stdlib only).

Stores (pick with --stores, comma list; default files,env):
  files    .env and .env.* files, Claude Code settings.json / settings.local.json
           `env` blocks, .mcp.json and .claude.json MCP server `env` and `headers`,
           under each --root (links and junctions are not followed)
  env      this process's environment variables with secret-like names
  wincred  Windows Credential Manager target names via `cmdkey /list`
           (or a saved listing with --cmdkey-file); values are never readable here
  gcm      git credential.helper / credentialStore, plus a plaintext
           ~/.git-credentials file under --home
  gh       the GitHub CLI hosts.yml: keyring (fine) or a plaintext oauth_token
  docker   Docker config.json (DOCKER_CONFIG, else <home>/.docker): credsStore,
           credHelpers, inline auths (plaintext); with --docker-list the helper's
           `list` (server names; user names dropped), or a saved --docker-list-file

Never runs `git credential fill`, `gh auth token`, `--show-token` or a helper `get`.
A value is only ever reported as {kind, prefix_class, length, fingerprint}.

Out: JSON on stdout. Exit 0 clean, 1 plaintext findings, 3 nothing could run,
4 crash (type and location only; the message is withheld).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import kw_common

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".tox", "dist", "build",
             ".mypy_cache", ".pytest_cache", "site-packages"}
ALL_STORES = ("files", "env", "wincred", "gcm", "gh", "docker")


class Inventory:
    def __init__(self, salt: str):
        self.salt = salt
        self.rows: list[dict] = []
        self.not_read: list[dict] = []
        self.stores: dict[str, str] = {}

    def add(self, store, location, target, consumer, value=None, kind=None, **extra):
        row = {"store": store, "location": location, "target": target, "consumer": consumer}
        if value is not None:
            row.update(kw_common.describe(value, self.salt))
        else:
            row.update({"kind": kind or "stored (value not read)", "prefix_class": "n/a",
                        "length": None, "fingerprint": None})
        row["plaintext_risk"] = extra.pop("plaintext_risk", row["kind"] == "plaintext")
        row.update(extra)
        self.rows.append(row)

    def link_consumers(self):
        by_fp: dict[str, list[dict]] = {}
        for r in self.rows:
            if r.get("fingerprint"):
                by_fp.setdefault(r["fingerprint"], []).append(r)
        for r in self.rows:
            same = by_fp.get(r.get("fingerprint") or "", [])
            r["seen_at"] = [f"{o['location']} :: {o['target']}" for o in same if o is not r]


# ------------------------------------------------------------------ files
def walk(root: Path, max_depth: int):
    root = root.resolve()
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        here = Path(dirpath)
        depth = len(here.relative_to(root).parts)
        keep = []
        for d in dirnames:
            p = here / d
            if d in SKIP_DIRS or p.is_symlink() or (hasattr(os.path, "isjunction") and os.path.isjunction(p)):
                continue
            if depth < max_depth:
                keep.append(d)
        dirnames[:] = keep
        for f in filenames:
            yield here / f


def is_env_file(name: str) -> bool:
    return name == ".env" or name.startswith(".env.")


def read_text(inv: Inventory, path: Path) -> str | None:
    try:
        if path.stat().st_size > 2_000_000:
            inv.not_read.append({"file": str(path), "reason": "over 2 MB"})
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        inv.not_read.append({"file": str(path), "reason": f"unreadable ({type(e).__name__})"})
        return None


def scan_env_file(inv: Inventory, path: Path):
    text = read_text(inv, path)
    if text is None:
        return
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        if s.startswith("export "):
            s = s[7:]
        key, _, value = s.partition("=")
        key, value = key.strip(), value.strip().strip("'\"")
        if key and kw_common.looks_secret(key, value):
            inv.add("files", str(path), key, f"env file {path.name}", value)


def load_json(inv: Inventory, path: Path):
    text = read_text(inv, path)
    if text is None:
        return None
    try:
        return json.loads(text)
    except ValueError:
        # The decoder's message is never surfaced: it can quote the document.
        inv.not_read.append({"file": str(path), "reason": "unparseable JSON"})
        return None


def scan_block(inv: Inventory, path: Path, block, consumer: str):
    if not isinstance(block, dict):
        return
    for key, value in block.items():
        if isinstance(value, str) and kw_common.looks_secret(str(key), kw_common.strip_scheme(value)):
            inv.add("files", str(path), str(key), consumer, value)


def scan_servers(inv: Inventory, path: Path, servers, where: str):
    if not isinstance(servers, dict):
        return
    for name, spec in servers.items():
        if isinstance(spec, dict):
            consumer = f"mcp server {name}{where}"
            scan_block(inv, path, spec.get("env"), consumer)
            scan_block(inv, path, spec.get("headers"), consumer)


def scan_files(inv: Inventory, roots: list[Path], max_depth: int):
    seen = False
    for root in roots:
        if not root.is_dir():
            inv.not_read.append({"file": str(root), "reason": "root is not a folder"})
            continue
        seen = True
        for path in walk(root, max_depth):
            name = path.name
            if is_env_file(name):
                scan_env_file(inv, path)
            elif name in ("settings.json", "settings.local.json") and path.parent.name == ".claude":
                doc = load_json(inv, path)
                if isinstance(doc, dict):
                    scan_block(inv, path, doc.get("env"), f"Claude Code settings env ({name})")
            elif name == ".mcp.json":
                doc = load_json(inv, path)
                if isinstance(doc, dict):
                    scan_servers(inv, path, doc.get("mcpServers"), "")
            elif name == ".claude.json":
                doc = load_json(inv, path)
                if isinstance(doc, dict):
                    scan_servers(inv, path, doc.get("mcpServers"), " (user scope)")
                    projects = doc.get("projects")
                    if isinstance(projects, dict):
                        for proj, pdoc in projects.items():
                            if isinstance(pdoc, dict):
                                scan_servers(inv, path, pdoc.get("mcpServers"),
                                             f" (project {Path(str(proj)).name})")
    return "RUN" if seen else "NOT-RUN: no readable --root"


# -------------------------------------------------------------------- env
def scan_env(inv: Inventory):
    for key, value in sorted(os.environ.items()):
        if key in ("SHIELD_SALT",) or not value:
            continue
        if kw_common.secret_named(key):
            inv.add("process-env", "environment", key, "this shell and its children", value)
    return "RUN"


# ---------------------------------------------------------------- wincred
def scan_wincred(inv: Inventory, cmdkey_file: str | None):
    if cmdkey_file:
        try:
            text = Path(cmdkey_file).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return "NOT-RUN: --cmdkey-file unreadable"
    else:
        exe = shutil.which("cmdkey")
        if not exe:
            return "NOT-RUN: cmdkey not found (Windows only)"
        try:
            proc = subprocess.run([exe, "/list"], capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.SubprocessError) as e:
            return f"NOT-RUN: cmdkey failed ({type(e).__name__})"
        if proc.returncode != 0:
            return f"NOT-RUN: cmdkey exit {proc.returncode}"
        text = proc.stdout
    current = None
    for line in text.splitlines():
        m = re.match(r"^\s*(Target|Type|User)\s*:\s*(.*?)\s*$", line)
        if not m:
            continue
        label, val = m.group(1), m.group(2)
        if label == "Target":
            target = kw_common.strip_userinfo(val)
            target = re.sub(r"(https?://)[^/@\s]+@", r"\1", target)
            current = {"target": target, "type": None, "user_present": False}
            inv.add("wincred", "Windows Credential Manager", target, "unknown until mapped",
                    kind="stored (value not read)", plaintext_risk=False, user_present=False)
            current["row"] = inv.rows[-1]
        elif current is not None and label == "Type":
            current["row"]["cred_type"] = val
        elif current is not None and label == "User":
            current["row"]["user_present"] = bool(val and val != "<none>")
    if current is None and "Target" not in text:
        inv.not_read.append({"file": "cmdkey /list", "reason": "no Target lines (empty vault, or a "
                             "non-English listing this parser does not read)"})
    return "RUN"


# -------------------------------------------------------------------- gcm
def git_config(key: str) -> list[str] | None:
    exe = shutil.which("git")
    if not exe:
        return None
    proc = subprocess.run([exe, "config", "--global", "--get-all", key], capture_output=True,
                          text=True, timeout=30)
    return [v.strip() for v in proc.stdout.splitlines() if v.strip()]


def scan_gcm(inv: Inventory, home: Path):
    helpers = git_config("credential.helper")
    if helpers is None:
        return "NOT-RUN: git not found"
    store = (git_config("credential.credentialStore") or [""])[-1]
    store = os.environ.get("GCM_CREDENTIAL_STORE", store)
    for h in helpers or ["<none>"]:
        risky = h.split()[0] == "store" if h != "<none>" else False
        inv.add("gcm", "git config --global", "credential.helper", "every git remote over https",
                kind=f"helper {h.split()[0] if h != '<none>' else 'none set'}", plaintext_risk=risky)
    if store:
        inv.add("gcm", "git config / GCM_CREDENTIAL_STORE", "credential.credentialStore",
                "Git Credential Manager", kind=f"store {store}", plaintext_risk=store == "plaintext")
    creds = home / ".git-credentials"
    if creds.is_file():
        text = read_text(inv, creds)
        for line in (text or "").splitlines():
            m = re.match(r"^(\w+://)(?:[^:@/\s]*)(?::([^@\s]*))?@([^/\s]+)", line.strip())
            if m and m.group(2):
                inv.add("gcm", str(creds), m.group(1) + m.group(3), "git store helper", m.group(2),
                        plaintext_risk=True)
    return "RUN"


# --------------------------------------------------------------------- gh
def gh_config_dir(home: Path) -> Path:
    if os.environ.get("GH_CONFIG_DIR"):
        return Path(os.environ["GH_CONFIG_DIR"])
    if os.name == "nt" and os.environ.get("APPDATA"):
        return Path(os.environ["APPDATA"]) / "GitHub CLI"
    return home / ".config" / "gh"


def scan_gh(inv: Inventory, home: Path):
    hosts = gh_config_dir(home) / "hosts.yml"
    if not hosts.is_file():
        return "NOT-RUN: no gh hosts.yml (gh not signed in, or another config dir)"
    text = read_text(inv, hosts)
    if text is None:
        return "NOT-RUN: hosts.yml unreadable"
    host = None
    found_hosts: dict[str, bool] = {}
    for line in text.splitlines():
        top = re.match(r"^([A-Za-z0-9.\-]+):\s*$", line)
        if top:
            host = top.group(1)
            found_hosts.setdefault(host, False)
            continue
        tok = re.match(r"^\s+oauth_token:\s*(\S+)\s*$", line)
        if tok and host:
            found_hosts[host] = True
            inv.add("gh", str(hosts), host, "gh and every tool that calls it", tok.group(1),
                    plaintext_risk=True)
    for h, plain in found_hosts.items():
        if not plain:
            inv.add("gh", str(hosts), h, "gh and every tool that calls it",
                    kind="keyring (value not read)", plaintext_risk=False)
    return "RUN"


# ----------------------------------------------------------------- docker
DOCKER_SECRET_FIELDS = ("auth", "identitytoken", "registrytoken", "password")
DOCKER_CONSUMER = "docker login, pull and push"


def docker_target(server: str) -> str:
    t = kw_common.strip_userinfo(str(server))
    return re.sub(r"^[^/@\s]+@", "", t)


def docker_listing(inv: Inventory, text: str, helper: str, source: str):
    try:
        listed = json.loads(text)
    except ValueError:
        inv.not_read.append({"file": source, "reason": "unparseable helper listing"})
        return
    if not isinstance(listed, dict):
        inv.not_read.append({"file": source, "reason": "helper listing is not a JSON object"})
        return
    for server, user in listed.items():
        # The listing maps server URL to user name; the user name is dropped.
        inv.add("docker", f"docker-credential-{helper} list", docker_target(server), DOCKER_CONSUMER,
                kind="stored (value not read)", plaintext_risk=False, user_present=bool(user))


def scan_docker(inv: Inventory, home: Path, list_file: str | None, live: bool):
    cfg_dir = Path(os.environ["DOCKER_CONFIG"]) if os.environ.get("DOCKER_CONFIG") else home / ".docker"
    cfg = cfg_dir / "config.json"
    if not cfg.is_file():
        return "NOT-RUN: no Docker config.json (Docker not set up, or another DOCKER_CONFIG)"
    doc = load_json(inv, cfg)
    if not isinstance(doc, dict):
        return "NOT-RUN: Docker config.json unreadable or not an object"
    store = doc.get("credsStore") if isinstance(doc.get("credsStore"), str) else ""
    helpers = doc.get("credHelpers") if isinstance(doc.get("credHelpers"), dict) else {}
    inv.add("docker", str(cfg), "credsStore", DOCKER_CONSUMER,
            kind=f"helper {store or 'none set'}", plaintext_risk=False)
    for server, helper in helpers.items():
        inv.add("docker", str(cfg), docker_target(server), DOCKER_CONSUMER,
                kind=f"helper {helper}", plaintext_risk=False)
    auths = doc.get("auths") if isinstance(doc.get("auths"), dict) else {}
    for server, entry in auths.items():
        entry = entry if isinstance(entry, dict) else {}
        found = False
        for field in DOCKER_SECRET_FIELDS:
            value = entry.get(field)
            if isinstance(value, str) and value:
                found = True
                inv.add("docker", str(cfg), docker_target(server), DOCKER_CONSUMER, value,
                        plaintext_risk=True, field=field)
        if not found:
            held = helpers.get(server) or store
            inv.add("docker", str(cfg), docker_target(server), DOCKER_CONSUMER,
                    kind=f"in helper {held} (value not read)" if held else "empty entry",
                    plaintext_risk=False)
    names = [h for h in dict.fromkeys([store, *helpers.values()]) if isinstance(h, str) and h]
    if list_file:
        try:
            text = Path(list_file).read_text(encoding="utf-8", errors="replace")
        except OSError:
            inv.not_read.append({"file": "--docker-list-file", "reason": "unreadable"})
        else:
            docker_listing(inv, text, store or "helper", "--docker-list-file")
    elif live:
        for name in names:
            # `list` returns server URLs and user names only; `get` would return the secret
            # and is never run.
            exe = shutil.which(f"docker-credential-{name}")
            if not exe:
                inv.not_read.append({"file": f"docker-credential-{name}", "reason": "helper not on PATH"})
                continue
            try:
                proc = subprocess.run([exe, "list"], capture_output=True, text=True, timeout=30,
                                      stdin=subprocess.DEVNULL)
            except (OSError, subprocess.SubprocessError) as e:
                inv.not_read.append({"file": f"docker-credential-{name}",
                                     "reason": f"list failed ({type(e).__name__})"})
                continue
            if proc.returncode != 0:
                inv.not_read.append({"file": f"docker-credential-{name}",
                                     "reason": f"list exit {proc.returncode}"})
                continue
            docker_listing(inv, proc.stdout, name, f"docker-credential-{name} list")
    return "RUN"


# ------------------------------------------------------------------- main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", action="append", default=[], help="folder to walk (repeatable)")
    ap.add_argument("--home", default=str(Path.home()), help="home folder for ~/.git-credentials")
    ap.add_argument("--stores", default="files,env")
    ap.add_argument("--salt-env", default="SHIELD_SALT")
    ap.add_argument("--max-depth", type=int, default=6)
    ap.add_argument("--cmdkey-file", help="a saved `cmdkey /list` listing instead of running cmdkey")
    ap.add_argument("--docker-list", action="store_true",
                    help="run each Docker credential helper's `list` (server names only)")
    ap.add_argument("--docker-list-file", help="a saved helper `list` JSON instead of running it")
    args = ap.parse_args(argv)

    stores = [s.strip() for s in args.stores.split(",") if s.strip()]
    bad = [s for s in stores if s not in ALL_STORES]
    if bad or not stores:
        sys.stderr.write(f"unknown store(s); choose from {', '.join(ALL_STORES)}\n")
        return kw_common.NOT_RUN
    salt, salt_kind = kw_common.get_salt(args.salt_env)
    inv = Inventory(salt)
    home = Path(args.home)
    for store in stores:
        if store == "files":
            if not args.root:
                inv.stores[store] = "NOT-RUN: no --root given"
            else:
                inv.stores[store] = scan_files(inv, [Path(r) for r in args.root], args.max_depth)
        elif store == "env":
            inv.stores[store] = scan_env(inv)
        elif store == "wincred":
            inv.stores[store] = scan_wincred(inv, args.cmdkey_file)
        elif store == "gcm":
            inv.stores[store] = scan_gcm(inv, home)
        elif store == "gh":
            inv.stores[store] = scan_gh(inv, home)
        elif store == "docker":
            inv.stores[store] = scan_docker(inv, home, args.docker_list_file, args.docker_list)
    inv.link_consumers()
    risky = sum(1 for r in inv.rows if r["plaintext_risk"])
    ran = [s for s, st in inv.stores.items() if st == "RUN"]
    doc = {"tool": "cred_inventory", "version": kw_common.VERSION, "salt": salt_kind,
           "stores": inv.stores, "rows": inv.rows, "not_read": inv.not_read,
           "summary": {"rows": len(inv.rows), "plaintext_risk": risky, "stores_run": len(ran),
                       "stores_not_run": [s for s in inv.stores if s not in ran]}}
    print(json.dumps(doc, indent=2))
    if not ran:
        return kw_common.NOT_RUN
    return kw_common.FINDINGS if risky else kw_common.CLEAN


def safe_main(argv=None) -> int:
    return kw_common.run_guarded(main, argv)


if __name__ == "__main__":
    sys.exit(safe_main())
