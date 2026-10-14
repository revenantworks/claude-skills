#!/usr/bin/env python3
"""pii_scan.py: the repo's PII barrier. Blocks personal data from reaching a commit.

    python tools/pii_scan.py --staged     # the pre-commit hook: added lines of the staged diff
    python tools/pii_scan.py --tree       # CI and before a release: every tracked file
    python tools/pii_scan.py --tree --identities   # plus every commit identity in the history

One engine: shieldwarden's `shield_scan.py` (packs/warden/.../scripts/). This file adds no
regex of its own except the drive-letter path rule below; every other shape is the engine's.

Rules that always run, for every contributor and in CI:
  user-folder, user-folder-slug, home-folder   a Windows, macOS or Unix home folder path
  drive-path                                   a drive-letter path outside the system folders
  email-address                                any address except no-reply and example domains
  secret shapes                                API keys, tokens, private-key blocks
  identity (--staged only)                     the commit author and committer email must be a
                                               no-reply address
  local-machine (local runs only)              this machine's host name and login name

Runs when present, never committed: a private names list (the warden pack's names list), found
by --names-file, else the WARDEN_NAMES_FILE environment variable, else ~/.warden/wordlist.txt.
No list is a NOTE line, not a failure: a public contributor has none, and the generic rules
still run.

Known, deliberate hits (test fixtures that must hold a fake path or address) are accepted by
rule and file in `.pii-scan.json` at the repo root. Keep each entry to one file.

Output never echoes a found value: each hit prints `path:line  rule  fp=<salted sha256 prefix>`.
Exit codes: 0 clean, 1 hits, 3 NOT-RUN (no git, or a refused input), 4 crashed.
Stdlib only. Python 3.9+.
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import re
import socket
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ENGINE_DIR = REPO / "packs" / "warden" / "skills" / "revenantworks-warden-shieldwarden" / "scripts"
sys.path.insert(0, str(ENGINE_DIR))
import shield_scan as ss  # noqa: E402

POLICY = ".pii-scan.json"
CLEAN, HITS, NOT_RUN, CRASH = 0, 1, 3, 4

# A drive-letter path: the letter, a colon, one or two separators, then the first folder.
DRIVE = re.compile(r"(?<![A-Za-z0-9_])([A-Za-z]):(?:\\\\|\\|/)([^\s\\/\"'`<>|*?:;,()\[\]{}]+)")
BACKSLASH_RUN = re.compile(r"\\{2,}")
# First folders that name no person and no machine: system folders and doc placeholders.
SYSTEM_ROOTS = {
    "program", "programdata", "windows", "users", "temp", "tmp", "path", "dir", "folder",
    "foo", "bar", "x", "...", "msys64", "cygwin64",
}
# A versioned system install folder, such as a Python install at the drive root.
SYSTEM_ROOT_SHAPE = re.compile(r"python\d*")
# Login and host names too generic to scan for as text.
GENERIC_LOCAL = {"admin", "administrator", "user", "users", "runner", "root", "owner", "localhost",
                 "default", "guest", "public", "home", "test", "dev", "ubuntu", "build"}


class Engine(ss.Engine):
    """shieldwarden's engine plus the drive-path rule."""

    def pii_line(self, text, cls, where, line, file=None):
        # JSON inside JSON doubles every backslash again; fold any run to one so a path
        # escaped twice still matches the engine's one-or-two-separator shapes.
        text = BACKSLASH_RUN.sub(lambda _m: "\\", text)
        super().pii_line(text, cls, where, line, file=file)
        for m in DRIVE.finditer(text):
            seg = m.group(2).rstrip(".")
            low = seg.lower()
            if not seg or low in SYSTEM_ROOTS or low in self.placeholders or seg[:1] in "$%<~" \
                    or SYSTEM_ROOT_SHAPE.fullmatch(low):
                continue
            # `users` is the user-folder rule's; a placeholder in angle brackets is a doc example.
            self.add(cls, "drive-path", where, line, f"{m.group(1)}:{seg}", file=file)


# A hook runs with GIT_DIR, GIT_INDEX_FILE and friends set (absolute in a worktree). This scan's
# own git calls keep them, so `git commit <paths>` is judged on the index git will commit; the
# engine's probes (is the names list inside a work tree?) must not inherit them, or every folder
# reads as inside the hook's repo.
HOOK_ENV = dict(os.environ)
for _var in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_PREFIX",
             "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES"):
    os.environ.pop(_var, None)


def git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-c", "core.quotePath=false", "-C", str(root), *args], capture_output=True,
                          env=HOOK_ENV, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def local_names() -> list[tuple[str, str]]:
    """This machine's host and login names, as extra whole-word names. Skipped in CI."""
    if os.environ.get("CI"):
        return []
    out = []
    for val in (socket.gethostname().split(".")[0], os.environ.get("COMPUTERNAME", ""), _login()):
        val = (val or "").strip()
        if len(val) >= 3 and val.lower() not in GENERIC_LOCAL and val.lower() not in {n.lower() for n, _ in out}:
            out.append((val, "local-machine"))
    return out


def _login() -> str:
    try:
        return getpass.getuser()
    except Exception:  # noqa: BLE001  (no login name is fine: the rule just has one name fewer)
        return ""


def staged_lines(root: Path):
    """Yield (path, line_number, text) for every added line in the staged diff, plus each path."""
    r = git(root, "diff", "--cached", "--no-color", "--no-ext-diff", "-U0", "--diff-filter=ACMR")
    if r.returncode != 0:
        raise ss.Refused("git diff --cached failed")
    path, ln = None, 0
    for raw in r.stdout.decode("utf-8", errors="replace").split("\n"):
        if raw.startswith("+++ "):
            head = raw[4:]
            if head.startswith('"') and head.endswith('"'):
                head = head[1:-1]  # a path git still quotes (control bytes); scanned as written
            path = head[2:] if head.startswith("b/") else None
            if path:
                yield path, None, path  # the file name itself is published too
            continue
        if raw.startswith("@@"):
            m = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)", raw)
            ln = int(m.group(1)) if m else 0
            continue
        if path and raw.startswith("+"):
            yield path, ln, raw[1:].rstrip("\r")
            ln += 1


def check_identity(eng: Engine, root: Path) -> None:
    for role, var in (("author", "GIT_AUTHOR_IDENT"), ("committer", "GIT_COMMITTER_IDENT")):
        r = git(root, "var", var)
        ident = r.stdout.decode("utf-8", errors="replace")
        m = re.search(r"<([^>]*)>", ident)
        email = m.group(1) if m else ""
        if not email or not ss.IDENTITY_ALLOWED.search(email):
            eng.add("identity", f"{role}-email", "git config", None, email or "(none)",
                    domain=email.partition("@")[2].lower() or "none")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="PII barrier over the staged diff or every tracked file.")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--staged", action="store_true", help="added lines of the staged diff (pre-commit)")
    mode.add_argument("--tree", action="store_true", help="every tracked file (CI)")
    ap.add_argument("--identities", action="store_true",
                    help="with --tree: every commit's author and committer must be a no-reply address")
    ap.add_argument("--names-file", help="private names list (default: WARDEN_NAMES_FILE, then ~/.warden/wordlist.txt)")
    ap.add_argument("--repo", help="work tree to scan (default: the clone holding this file)")
    ap.add_argument("--salt-env", default="SHIELD_SALT")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    root = Path(args.repo).resolve() if args.repo else REPO
    try:
        if git(root, "rev-parse", "--show-toplevel").returncode != 0:
            print("pii_scan: NOT-RUN (not a git work tree)")
            return NOT_RUN
        pol = root / POLICY
        cfg = ss.load_json(str(pol)) if pol.exists() else {}
        names, note = ss.load_names(args.names_file, root)
        local = local_names()
        eng = Engine(cfg, names + local, args.salt_env)
        if args.tree:
            ss.tree_pass(eng, root, True, False, want_inj=False)
            if args.identities:
                ss.identity_pass(eng, root)
        else:
            for path, ln, text in staged_lines(root):
                eng.pii_line(text, "pii", path, ln, file=path)
            check_identity(eng, root)
    except ss.Refused as e:
        print(f"pii_scan: NOT-RUN ({e})")
        return NOT_RUN
    except Exception as e:  # noqa: BLE001  (never print a message: it could hold a value)
        print(f"pii_scan: CRASH ({type(e).__name__})")
        return CRASH
    for h in eng.hits:
        if h["rule"] == "owner-name" and h.get("entry", 0) > len(names):
            h["rule"] = "local-machine"
            h["entry"] -= len(names)
    if args.json:
        print(json.dumps({"hits": eng.hits, "accepted": len(eng.accepted_hits),
                          "names": len(names), "note": note}, indent=1))
    else:
        for h in eng.hits:
            where = f"{h['where']}:{h['line']}" if "line" in h else h["where"]
            tag = f"fp={h['fp']}" if "fp" in h else f"entry #{h.get('entry', '?')}"
            print(f"{where}  {h['rule']}  {tag}")
        scope = "staged diff" if args.staged else f"{eng.files_scanned} tracked files"
        print(f"pii_scan: {len(eng.hits)} hit(s), {len(eng.accepted_hits)} accepted, {scope}; "
              f"names list: {len(names)} term(s){' (' + note + ')' if note else ''}; "
              f"local names: {len(local)}")
        if eng.hits:
            print("pii_scan: BLOCKED. Remove each value (never print it), or, for a test fixture only, "
                  f"accept it by rule and file in {POLICY}.")
    return HITS if eng.hits else CLEAN


if __name__ == "__main__":
    raise SystemExit(main())
