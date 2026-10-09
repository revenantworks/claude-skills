#!/usr/bin/env python3
"""trust_vet.py - pre-install vet of a third-party candidate (stdlib only).

Reads a local checkout of a skill, plugin, MCP server or GitHub Action and prints one JSON
verdict. It never executes anything from the candidate: it reads files as bytes, runs only
the scanners named on its command line (when they are on PATH) and git, and treats every
byte of the candidate and of scanner output as data, never instructions.

  trust_vet.py vet   <dir> [--kind auto|skill|plugin|mcp|action] [--sha SHA]
                           [--max-bytes N] [--run-scanners] [--scanners a,b] [--out-dir DIR]
  trust_vet.py revet <dir> --from SHA --to SHA [--max-bytes N]

Output (stdout, JSON):
  {mode, verdict: PASS|CONDITIONAL|HOLD|FAIL, kind, sha, tree, coverage[{file, bytes, class,
   executable, read_by[], status}], findings[{rule, severity, file, line, note}],
   scanners[{name, status, exit, hits}], terms[], reasons[]}

Exit codes: 0 PASS · 1 CONDITIONAL, HOLD or FAIL · 3 NOT-RUN (no readable candidate) · 4 crash.
Findings name a rule, a file and a line number. They never quote the matched line, so a
credential in a hook never reaches the report (secrets are shieldwarden's job).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

VERSION = "0.1.0"
DEFAULT_MAX_BYTES = 1_000_000  # skillspector's per-file analysis cap (MAX_FILE_BYTES, 1 MB)
SEVERITY_RANK = {"note": 0, "conditional": 1, "hold": 2, "fail": 3}
VERDICT_FOR = {0: "PASS", 1: "CONDITIONAL", 2: "HOLD", 3: "FAIL"}

BYTECODE_EXT = {".pyc", ".pyo", ".class", ".jar", ".wasm", ".node", ".so", ".dll", ".dylib",
                ".exe", ".msi", ".bin", ".com", ".scr", ".sys", ".whl", ".egg", ".pyd"}
ARCHIVE_EXT = {".zip", ".tar", ".gz", ".tgz", ".bz2", ".xz", ".7z", ".rar", ".vsix", ".mcpb", ".dxt"}
MEDIA_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".svg", ".bmp", ".mp3", ".wav",
             ".ogg", ".mp4", ".webm", ".woff", ".woff2", ".ttf", ".otf", ".pdf"}
SCRIPT_EXT = {".py", ".sh", ".bash", ".zsh", ".ps1", ".psm1", ".bat", ".cmd", ".js", ".mjs",
              ".cjs", ".ts", ".rb", ".pl", ".lua", ".go", ".rs"}
SKIP_DIRS = {".git"}

# Scanner table: which kinds each covers and how it is run. Flags are from each tool's own
# docs (references/scanner-matrix.md); the skill never installs a scanner.
SCANNERS = {
    "skillspector": {"kinds": {"skill", "plugin", "mcp"},
                     "argv": lambda d, out: ["skillspector", "scan", str(d), "--no-llm",
                                             "--format", "json", "--output", str(out)],
                     "clean": {0}, "hits": {1}},
    "zizmor": {"kinds": {"action", "plugin", "skill", "mcp"},
               "argv": lambda d, out: ["zizmor", "--offline", "--format", "json", str(d)],
               "clean": {0, 3}, "hits": {11, 12, 13, 14}},
    "pinact": {"kinds": {"action"},
               "argv": lambda d, out: ["pinact", "run", "--check", "--no-api"],
               "clean": {0}, "hits": {1}, "in_tree": True},
}
# A PASS needs one of these to agree (owner Q36). skillspector is one option; cisco skill-scanner is
# run by hand and recorded with --reader. The skill installs none of them. Sentry's skill-scanner
# (K4 C4) counts for skills only when its pattern script ran clean; the user vets it first.
EXPECTED_SECOND_READER = {"skill": {"skillspector", "cisco-skill-scanner", "sentry-skill-scanner"},
                          "plugin": {"skillspector", "cisco-skill-scanner"},
                          "mcp": {"skillspector"}, "action": {"zizmor", "pinact"}}
READER_ARG = re.compile(r"^([a-z0-9][a-z0-9._-]*)=(clean|hits(?::(\d+))?)$")

NETWORK = re.compile(r"\b(curl|wget|Invoke-WebRequest|Invoke-RestMethod|iwr|irm|nc|ncat|"
                     r"socat|scp|ftp|bitsadmin|certutil)\b|https?://|\bfetch\(|requests\.(get|post)|"
                     r"urllib\.request|http\.client|\bWebClient\b", re.I)
PIPE_SHELL = re.compile(r"(curl|wget|iwr|Invoke-WebRequest|irm|Invoke-RestMethod)[^\n|]*\|\s*"
                        r"(sh|bash|zsh|iex|Invoke-Expression|python3?|node|pwsh|powershell)\b", re.I)
BYPASS = re.compile(r"--dangerously-skip-permissions|--dangerously-run-mcp-servers|"
                    r"\"defaultMode\"\s*:\s*\"bypassPermissions\"|no domain blocklist", re.I)
ENV_SECRET = re.compile(r"(os\.environ|os\.getenv|process\.env|\$env:|getenv\()[^\n]{0,40}"
                        r"(TOKEN|KEY|SECRET|PASSW|CREDENTIAL|COOKIE)", re.I)
SKILL_SHELL = re.compile(r"!`[^`\n]+`")
HIDDEN = re.compile("[\u200b-\u200f\u202a-\u202e\u2060-\u2064\u2066-\u2069]")
USES = re.compile(r"^\s*-?\s*uses:\s*['\"]?([^'\"\s#]+)", re.M)
SHA40 = re.compile(r"^[0-9a-f]{40}$")
LICENCE_LIMITS = re.compile(r"source[- ]available|non-?commercial|no derivative|NoDerivatives|"
                            r"Business Source License|Commons Clause|PolyForm|Elastic License|"
                            r"Server Side Public License|SSPL", re.I)
INSTALLER_NAMES = re.compile(r"^(install|setup|bootstrap|postinstall)[\w.-]*\.(sh|ps1|py|bat|cmd|js)$", re.I)
CONFIG_WRITE = re.compile(r"CLAUDE\.md|\.claude[/\\]settings|settings\.json|hooks\.json|"
                          r"\.git[/\\]hooks|core\.hooksPath|\.mcp\.json|\.claude[/\\](skills|agents|commands)",
                          re.I)
# Lockfile supply-chain checks (K4 C4): where dependencies resolve from, and whether they are pinned.
NPM_LOCKS = ("package-lock.json", "npm-shrinkwrap.json", "yarn.lock", "pnpm-lock.yaml", "bun.lock",
             "bun.lockb")
REGISTRY_PREFIXES = ("https://registry.npmjs.org/", "https://registry.yarnpkg.com/")
LOCK_SOURCE = re.compile(r"(?:\"resolved\"\s*:\s*\"|^\s*resolved\s+\"?|tarball:\s*['\"]?)([^\"'\s,}]+)", re.M)
REQ_FOREIGN = re.compile(r"(?i)(?:^|\s|@\s*)(?:git\+|hg\+|svn\+|bzr\+|https?://|file:)")
# Owner Q35: external calls and localhost/loopback calls are separate finding classes.
URL_HOST = re.compile(r"(?i)\b(?:https?|wss?)://(\[[^\]]+\]|[^/\s'\"`:?#\\]+)")
LOOPBACK_MENTION = re.compile(r"(?i)\blocalhost\b|\b127(?:\.\d{1,3}){3}\b|\b0\.0\.0\.0\b|\[::1\]")
COMMENT_LINE = re.compile(r"^\s*(?:#|//|/?\*|--|rem\b|::)", re.I)
INTERNAL_NOTE = ("internal — vet further for onward leakage: name what listens on that port and "
                 "whether it forwards data out")


def is_loopback(host: str) -> bool:
    h = host.strip("[]").lower()
    return h in ("localhost", "0.0.0.0", "::1") or bool(re.fullmatch(r"127(?:\.\d{1,3}){3}", h))


def net_classes(text: str) -> dict[str, int]:
    """First line of each network class in code: {'external': line, 'internal': line}.
    A call with no readable destination counts as external (strict). Comment lines are skipped."""
    found: dict[str, int] = {}
    for i, line in enumerate(text.splitlines(), 1):
        if COMMENT_LINE.match(line) or not NETWORK.search(line):
            continue
        hosts = URL_HOST.findall(line)
        if hosts:
            classes = {"internal" if is_loopback(h) else "external" for h in hosts}
        elif LOOPBACK_MENTION.search(line):
            classes = {"internal"}
        else:
            classes = {"external"}
        for c in classes:
            found.setdefault(c, i)
    return found


class Vet:
    def __init__(self, root: Path, max_bytes: int):
        self.root = root
        self.max_bytes = max_bytes
        self.coverage: list[dict] = []
        self.findings: list[dict] = []
        self.texts: dict[str, str] = {}

    # ---- inventory -------------------------------------------------------------------
    def walk(self) -> None:
        for dirpath, dirnames, filenames in os.walk(self.root, followlinks=False):
            dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
            base = Path(dirpath)
            for d in list(dirnames):
                if (base / d).is_symlink() or _is_junction(base / d):
                    rel = (base / d).relative_to(self.root).as_posix()
                    self._row(rel, 0, "link", False, [], "UNREAD")
                    self.add("link-in-tree", "hold", rel, None,
                             "a link inside the candidate can point anywhere once installed")
                    dirnames.remove(d)
            for name in sorted(filenames):
                p = base / name
                rel = p.relative_to(self.root).as_posix()
                if p.is_symlink():
                    self._row(rel, 0, "link", False, [], "UNREAD")
                    self.add("link-in-tree", "hold", rel, None,
                             "a link inside the candidate can point anywhere once installed")
                    continue
                self._classify(p, rel)

    def _classify(self, p: Path, rel: str) -> None:
        size = p.stat().st_size
        ext = p.suffix.lower()
        in_bin = rel.split("/")[0] == "bin"
        if ext in BYTECODE_EXT or ext in ARCHIVE_EXT:
            cls = "bytecode" if ext in BYTECODE_EXT else "archive"
            self._row(rel, size, cls, True, [], "UNREAD")
            return
        if size > self.max_bytes:
            self._row(rel, size, "oversized", True, [], "UNREAD")
            return
        data = p.read_bytes()
        if ext in MEDIA_EXT and ext != ".svg":
            self._row(rel, size, "media", False, [], "UNREAD")
            return
        if b"\x00" in data:
            self._row(rel, size, "binary", True, [], "UNREAD")
            return
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            text = data.decode("latin-1")
        executable = ext in SCRIPT_EXT or in_bin or text.startswith("#!")
        self.texts[rel] = text
        self._row(rel, size, "script" if executable else "text", executable, ["trust_vet"], "READ")

    def _row(self, rel, size, cls, executable, read_by, status):
        self.coverage.append({"file": rel, "bytes": size, "class": cls, "executable": executable,
                              "read_by": list(read_by), "status": status})

    def add(self, rule, severity, file, line, note):
        self.findings.append({"rule": rule, "severity": severity, "file": file, "line": line,
                              "note": note})

    # ---- detection -------------------------------------------------------------------
    def detect_kind(self) -> str:
        if (self.root / ".claude-plugin" / "plugin.json").is_file() or \
           (self.root / ".claude-plugin" / "marketplace.json").is_file():
            return "plugin"
        if (self.root / "SKILL.md").is_file():
            return "skill"
        if (self.root / "action.yml").is_file() or (self.root / "action.yaml").is_file() or \
           (self.root / ".github" / "workflows").is_dir() and not (self.root / ".mcp.json").is_file():
            return "action"
        return "mcp"

    def rules(self, kind: str) -> list[str]:
        """Run the red-flag pass over every READ file. Returns unpinned action refs."""
        unpinned: list[str] = []
        for rel, text in self.texts.items():
            low = rel.lower()
            name = rel.rsplit("/", 1)[-1]
            is_hook_cfg = low.endswith("hooks.json") or name in ("plugin.json", "settings.json",
                                                                  "settings.local.json")
            is_skill_md = name == "SKILL.md" or (low.startswith("commands/") and low.endswith(".md"))
            for i, line in enumerate(text.splitlines(), 1):
                if HIDDEN.search(line):
                    self.add("hidden-text", "hold", rel, i,
                             "zero-width or bidirectional control characters hide text from a reader")
                if PIPE_SHELL.search(line):
                    self.add("fetch-pipe-shell", "fail", rel, i,
                             "downloads code and pipes it straight into an interpreter")
                if BYPASS.search(line) and (is_hook_cfg or rel in self._exec_files()):
                    self.add("safety-bypass", "fail", rel, i,
                             "turns off a Claude Code safety control in shipped config or code")
                elif BYPASS.search(line):
                    self.add("safety-bypass-mention", "note", rel, i,
                             "mentions a safety bypass in prose; read whether it tells the reader to use it")
            if is_hook_cfg:
                self._hooks(rel, text)
                if name in ("settings.json", "settings.local.json"):
                    self.add("ships-settings", "hold", rel, None,
                             "a candidate that ships Claude Code settings changes your permissions")
            if is_skill_md:
                self._skill(rel, text)
            if name == ".mcp.json" or name == "plugin.json":
                self._mcp(rel, text)
            if name == "marketplace.json":
                self._marketplace(rel, text)
            if name == "package.json":
                self._package(rel, text)
            if INSTALLER_NAMES.match(name):
                writes = sorted({m.group(0) for m in CONFIG_WRITE.finditer(text)})
                self.add("installer-present", "conditional", rel, None,
                         "an installer script: read what it writes before anyone runs it")
                if writes:
                    self.add("installer-writes-config", "hold", rel, None,
                             "the installer writes Claude or git config: " + ", ".join(writes))
            if rel in self._exec_files():
                classes = net_classes(text)
                if "external" in classes:
                    self.add("network-external", "conditional", rel, classes["external"],
                             "calls an external host at run time: list each host and what is sent")
                if "internal" in classes:
                    self.add("network-internal", "conditional", rel, classes["internal"],
                             "calls a localhost or loopback address: " + INTERNAL_NOTE)
                if ENV_SECRET.search(text) and NETWORK.search(text):
                    self.add("exfil-shape", "hold", rel, None,
                             "reads a secret-named variable and talks to the network in one file")
            if low.startswith("bin/"):
                self.add("bin-on-path", "conditional", rel, None,
                         "plugin bin/ joins the Bash tool's PATH; permission rules still apply")
            if low.startswith(".github/workflows/") or name in ("action.yml", "action.yaml"):
                for m in USES.finditer(text):
                    ref = m.group(1)
                    if ref.startswith("./") or ref.startswith("docker://"):
                        continue
                    if "@" not in ref or not SHA40.match(ref.rsplit("@", 1)[1]):
                        line = text[:m.start()].count("\n") + 1
                        unpinned.append(ref)
                        sev = "conditional" if kind == "action" else "note"
                        self.add("unpinned-action", sev, rel, line,
                                 "action pinned to a tag or branch, not a commit SHA")
            if name.upper().startswith(("LICENSE", "LICENCE", "COPYING")):
                if LICENCE_LIMITS.search(text):
                    self.add("licence-restricts", "note", rel, None,
                             "licence limits use or derivatives: adopt ideas only, fold in no code")
        self._lockfiles()
        if not any(c["file"].rsplit("/", 1)[-1].upper().startswith(("LICENSE", "LICENCE", "COPYING"))
                   for c in self.coverage):
            self.add("no-licence", "note", None, None,
                     "no licence file: all rights reserved by default; adopt ideas only")
        return unpinned

    def _lockfiles(self) -> None:
        """Supply-chain checks on dependency manifests and lockfiles (K4 C4).

        no-lockfile: a package.json with runtime dependencies and no lockfile beside it resolves
        fresh at every install. lockfile-foreign-source: a lockfile entry or requirement fetched
        from outside the default registry (git, plain http, a tarball URL, a local path).
        lockfile-no-integrity: a package-lock entry with a resolved URL and no integrity hash.
        unpinned-requirement: a requirements line with no exact == pin.
        """
        present = {c["file"] for c in self.coverage}
        for rel, text in self.texts.items():
            folder, _, name = rel.rpartition("/")
            prefix = folder + "/" if folder else ""
            if name == "package.json":
                try:
                    data = json.loads(text)
                except ValueError:
                    data = {}
                deps = {}
                if isinstance(data, dict):
                    for key in ("dependencies", "optionalDependencies"):
                        if isinstance(data.get(key), dict):
                            deps.update(data[key])
                if deps and not any(prefix + lock in present for lock in NPM_LOCKS):
                    self.add("no-lockfile", "conditional", rel, None,
                             f"{len(deps)} runtime dependencies and no lockfile: versions resolve "
                             "fresh at every install")
            elif name in NPM_LOCKS:
                foreign = [(text[:m.start()].count("\n") + 1, m.group(1))
                           for m in LOCK_SOURCE.finditer(text)
                           if ":" in m.group(1)  # a bare relative path is an in-tree workspace link
                           and not m.group(1).startswith(REGISTRY_PREFIXES)]
                if foreign:
                    self.add("lockfile-foreign-source", "hold", rel, foreign[0][0],
                             f"{len(foreign)} locked package(s) resolve outside the default registry "
                             "(git, http, tarball or path): read each before install")
                if name in ("package-lock.json", "npm-shrinkwrap.json"):
                    try:
                        data = json.loads(text)
                    except ValueError:
                        data = {}
                    pkgs = data.get("packages", {}) if isinstance(data, dict) else {}
                    bare = [k for k, v in (pkgs.items() if isinstance(pkgs, dict) else [])
                            if isinstance(v, dict) and v.get("resolved") and not v.get("integrity")]
                    if bare:
                        self.add("lockfile-no-integrity", "conditional", rel, None,
                                 f"{len(bare)} locked package(s) carry no integrity hash")
            elif re.match(r"^requirements[\w.-]*\.txt$", name, re.I):
                loose, foreign_line = 0, None
                for i, line in enumerate(text.splitlines(), 1):
                    s = line.split(" #", 1)[0].strip()
                    if not s or s.startswith(("#", "-r", "-c", "--")):
                        continue
                    if REQ_FOREIGN.search(s) or s.startswith(("-e", ".", "/")):
                        foreign_line = foreign_line or i
                    elif "==" not in s:
                        loose += 1
                if foreign_line:
                    self.add("lockfile-foreign-source", "hold", rel, foreign_line,
                             "a requirement installs from a VCS, URL or path, not the package index")
                if loose:
                    self.add("unpinned-requirement", "conditional", rel, None,
                             f"{loose} requirement(s) with no exact == pin")

    def _exec_files(self) -> set[str]:
        return {c["file"] for c in self.coverage if c["executable"]}

    def _hooks(self, rel: str, text: str) -> None:
        try:
            data = json.loads(text)
        except ValueError:
            return
        hooks = data.get("hooks") if isinstance(data, dict) else None
        if not isinstance(hooks, dict):
            return
        for event, matchers in hooks.items():
            for cmd in _hook_commands(matchers):
                classes = net_classes(cmd) if NETWORK.search(cmd) else {}
                if "external" in classes:
                    self.add("hook-network", "fail", rel, None,
                             f"a {event} hook reaches the network; hooks run outside the sandbox")
                elif "internal" in classes:
                    self.add("hook-network-internal", "fail", rel, None,
                             f"a {event} hook calls a localhost or loopback address outside the sandbox: "
                             + INTERNAL_NOTE)
                else:
                    self.add("hook-present", "conditional", rel, None,
                             f"a {event} hook runs a shell command with full user permissions")

    def _skill(self, rel: str, text: str) -> None:
        fm = text.split("---", 2)[1] if text.startswith("---") and text.count("---") >= 2 else ""
        if re.search(r"^allowed-tools:", fm, re.M):
            self.add("skill-allowed-tools", "conditional", rel, None,
                     "allowed-tools pre-approves tools for the turn that invokes the skill")
        if re.search(r"^hooks:", fm, re.M):
            self.add("skill-hooks", "conditional", rel, None,
                     "skill hooks register on invoke and run for the rest of the session")
        for m in SKILL_SHELL.finditer(text):
            line = text[:m.start()].count("\n") + 1
            sev = "fail" if NETWORK.search(m.group(0)) else "conditional"
            self.add("skill-shell", sev, rel, line,
                     "!`command` runs a shell command when the skill loads, before Claude reads it")

    def _mcp(self, rel: str, text: str) -> None:
        try:
            data = json.loads(text)
        except ValueError:
            return
        servers = data.get("mcpServers") if isinstance(data, dict) else None
        if not isinstance(servers, dict):
            return
        for name, spec in servers.items():
            if not isinstance(spec, dict):
                continue
            if spec.get("command"):
                self.add("mcp-stdio", "conditional", rel, None,
                         f"server {name!r} starts a local process outside the sandbox")
            if spec.get("url"):
                hosts = URL_HOST.findall(str(spec["url"]))
                if hosts and all(is_loopback(h) for h in hosts):
                    self.add("mcp-local-url", "conditional", rel, None,
                             f"server {name!r} is reached on a localhost or loopback address: " + INTERNAL_NOTE)
                else:
                    self.add("mcp-remote", "conditional", rel, None,
                             f"server {name!r} sends tool calls to a remote host")

    def _marketplace(self, rel: str, text: str) -> None:
        try:
            data = json.loads(text)
        except ValueError:
            return
        for entry in data.get("plugins", []) if isinstance(data, dict) else []:
            src = entry.get("source") if isinstance(entry, dict) else None
            if not isinstance(src, dict):
                continue
            kind = src.get("source")
            if kind == "command":
                self.add("command-source", "hold", rel, None,
                         f"plugin {entry.get('name')!r} installs by running a command every session")
            elif kind in ("github", "url", "git-subdir") and not SHA40.match(str(src.get("sha", ""))):
                self.add("unpinned-source", "conditional", rel, None,
                         f"plugin {entry.get('name')!r} is not pinned to a commit SHA")
            elif kind == "archive" and not src.get("sha256"):
                self.add("unpinned-source", "conditional", rel, None,
                         f"plugin {entry.get('name')!r} archive has no sha256 pin")

    def _package(self, rel: str, text: str) -> None:
        try:
            data = json.loads(text)
        except ValueError:
            return
        scripts = data.get("scripts", {}) if isinstance(data, dict) else {}
        hits = [k for k in ("preinstall", "install", "postinstall", "prepare") if k in scripts]
        if hits:
            self.add("install-scripts", "conditional", rel, None,
                     "package runs scripts on a manual install: " + ", ".join(hits))


def _hook_commands(matchers) -> list[str]:
    out: list[str] = []
    if isinstance(matchers, dict):
        matchers = [matchers]
    for m in matchers if isinstance(matchers, list) else []:
        if not isinstance(m, dict):
            continue
        if isinstance(m.get("command"), str):
            out.append(m["command"])
        for h in m.get("hooks", []) if isinstance(m.get("hooks"), list) else []:
            if isinstance(h, dict) and isinstance(h.get("command"), str):
                out.append(h["command"])
            if isinstance(h, dict) and isinstance(h.get("url"), str):
                out.append(h["url"])
    return out


def _is_junction(p: Path) -> bool:
    is_j = getattr(os.path, "isjunction", None)
    try:
        return bool(is_j and is_j(p))
    except OSError:
        return False


def _git(root: Path, *args: str) -> str | None:
    if not shutil.which("git"):
        return None
    try:
        r = subprocess.run(["git", "-C", str(root), "-c", "core.fsmonitor=false", *args],
                           capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def run_scanner(name: str, root: Path, out_dir: Path | None) -> dict:
    """Run one scanner if it is on PATH. Its output is data: only the exit code and a hit
    count are read back; the raw output goes to out_dir for the reader, never into context."""
    spec = SCANNERS[name]
    if not shutil.which(name):
        return {"name": name, "status": "NOT-RUN", "exit": None, "hits": None,
                "note": "not on PATH; install is the user's step (install-walkthrough.md)"}
    out = (out_dir or Path(tempfile.gettempdir())) / f"trust_vet-{name}.out"
    root = Path(root).resolve()
    # A scanner that takes the path as an argument runs from an empty temp folder, so it never loads
    # config the hostile clone ships, in its own folder or beside it (K7-4-20, V-K8w F17). pinact
    # takes no path here and reads the clone's workflows from inside it: a stated limit (SKILL.md, step 1).
    with tempfile.TemporaryDirectory(prefix="trust_vet-cwd-") as empty:
        cwd = root if spec.get("in_tree") else Path(empty)
        try:
            r = subprocess.run(spec["argv"](root, out), cwd=str(cwd), capture_output=True,
                               text=True, timeout=600)
        except (OSError, subprocess.SubprocessError) as exc:
            return {"name": name, "status": "CRASH", "exit": None, "hits": None, "note": type(exc).__name__}
    if out_dir:
        (out_dir / f"trust_vet-{name}.stdout").write_text(r.stdout or "", encoding="utf-8")
    if r.returncode in spec["clean"]:
        return {"name": name, "status": "RUN", "exit": r.returncode, "hits": 0}
    if r.returncode in spec["hits"]:
        return {"name": name, "status": "RUN", "exit": r.returncode, "hits": _count_hits(r.stdout)}
    return {"name": name, "status": "CRASH", "exit": r.returncode, "hits": None,
            "note": "exit code outside the documented set; read as NOT-RUN"}


def _count_hits(stdout: str) -> int | None:
    try:
        data = json.loads(stdout)
    except ValueError:
        return None
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        for key in ("findings", "results", "issues"):
            if isinstance(data.get(key), list):
                return len(data[key])
    return None


def decide(vet: Vet, kind: str, sha: str | None, scanners: list[dict], unpinned: list[str]) -> dict:
    reasons: list[str] = []
    worst = max((SEVERITY_RANK[f["severity"]] for f in vet.findings), default=0)
    unread_exec = [c["file"] for c in vet.coverage if c["status"] == "UNREAD" and c["executable"]]
    unread_media = [c["file"] for c in vet.coverage if c["status"] == "UNREAD" and not c["executable"]
                    and c["class"] == "media"]
    if unread_exec:
        worst = max(worst, SEVERITY_RANK["hold"])
        reasons.append(f"{len(unread_exec)} executable, bytecode, archive or oversized file(s) UNREAD")
    if unread_media:
        worst = max(worst, SEVERITY_RANK["conditional"])
        reasons.append(f"{len(unread_media)} media file(s) UNREAD")
    hits = [s for s in scanners if s["status"] == "RUN" and s["hits"] not in (0,)]
    if hits:
        worst = max(worst, SEVERITY_RANK["hold"])
        reasons.append("scanner hits to read by file role and matched string: "
                       + ", ".join(s["name"] for s in hits))
    crashed = [s["name"] for s in scanners if s["status"] == "CRASH"]
    if crashed:
        reasons.append("scanner crashed, read as NOT-RUN: " + ", ".join(crashed))
    ran_clean = {s["name"] for s in scanners if s["status"] == "RUN" and s["hits"] == 0}
    if not (ran_clean & EXPECTED_SECOND_READER.get(kind, set())):
        worst = max(worst, SEVERITY_RANK["conditional"])
        reasons.append("no second scanner ran clean for kind " + kind + " (second reader options: "
                       + ", ".join(sorted(EXPECTED_SECOND_READER.get(kind, set()))) + "; the user "
                       "installs any of them, a hand run is recorded with --reader)")
    if not sha:
        worst = max(worst, SEVERITY_RANK["hold"])
        reasons.append("no commit SHA to pin: vet a git checkout or pass --sha")
    if worst == SEVERITY_RANK["fail"]:
        reasons.insert(0, "a fail rule fired: " + ", ".join(sorted({f["rule"] for f in vet.findings
                                                                     if f["severity"] == "fail"})))
    verdict = VERDICT_FOR[worst]
    terms = build_terms(vet, kind, sha, unpinned, scanners) if verdict in ("PASS", "CONDITIONAL") else []
    return {"verdict": verdict, "reasons": reasons, "terms": terms}


def build_terms(vet: Vet, kind: str, sha: str, unpinned: list[str], scanners: list[dict]) -> list[str]:
    rules = {f["rule"] for f in vet.findings}
    terms = [f"pin-sha: install commit {sha} and no other",
             "auto-update-off: keep auto-update off for the marketplace it comes from"]
    if kind == "skill":
        terms.append("read-only-copy: install a copy or read-only link of the pinned tree, "
                     "never a live clone that pulls")
    if kind == "plugin":
        terms.append("inventory-match: claude plugin details must list only the components this vet read")
        terms.append("default-enabled-false: in your own marketplace entry, set defaultEnabled false "
                     "until the inventory matches")
    if "hook-present" in rules or "skill-hooks" in rules:
        terms.append("hooks-read: every hook command was read; hooks run outside the sandbox")
    if "skill-shell" in rules:
        terms.append("gatewarden: disableSkillShellExecution true, or accept each !`command` by name")
    if "skill-allowed-tools" in rules:
        terms.append("allowed-tools: strip the grant from the installed copy or accept it by name")
    if "mcp-stdio" in rules or "mcp-remote" in rules:
        terms.append("gatewarden: list the candidate's MCP servers in deniedMcpServers until each is "
                     "approved by name; never enableAllProjectMcpServers")
    if "network-external" in rules:
        terms.append("network-external: list every external host the code calls and what it sends; "
                     "anything the job does not need is denied or sandboxed (gatewarden)")
    if rules & {"network-internal", "mcp-local-url"}:
        terms.append("network-internal: internal — vet further for onward leakage; name what listens on "
                     "each localhost port and whether it forwards data out, and vet that listener too")
    if "bin-on-path" in rules:
        terms.append("gatewarden: deny rules for any bin/ executable the job does not need")
    if "install-scripts" in rules or "installer-present" in rules:
        terms.append("installer: run no installer on the host; a first run goes to the sandbox")
    if rules & {"no-lockfile", "unpinned-requirement", "lockfile-no-integrity"}:
        terms.append("lockfile: install only from a committed lockfile with exact pins and integrity "
                     "hashes (npm ci, a frozen lockfile, pip --require-hashes); a dependency change "
                     "is a revet")
    for ref in sorted(set(unpinned)):
        terms.append(f"pin-action: replace {ref} with its commit SHA (pinact supplies it)")
    if "licence-restricts" in rules or "no-licence" in rules:
        terms.append("licence: adopt ideas only; fold in no code")
    for s in scanners:
        if s["status"] != "RUN":
            terms.append(f"not-run: {s['name']} did not run; the verdict rests on the readers that did")
    return terms


def vet_dir(root: Path, kind: str, sha: str | None, max_bytes: int, scanner_names: list[str],
            run_scanners: bool, out_dir: Path | None, readers: list[str] | None = None) -> dict:
    hand = []
    for spec in readers or []:
        m = READER_ARG.match(spec.strip())
        if not m:
            raise ValueError("--reader takes NAME=clean or NAME=hits[:N]")
        hits = 0 if m.group(2) == "clean" else int(m.group(3) or 1)
        hand.append({"name": m.group(1), "status": "RUN", "exit": None, "hits": hits,
                     "note": "run by hand by the user; result recorded with --reader"})
    vet = Vet(root, max_bytes)
    vet.walk()
    kind = vet.detect_kind() if kind == "auto" else kind
    unpinned = vet.rules(kind)
    sha = sha or _git(root, "rev-parse", "HEAD")
    tree = _git(root, "rev-parse", "HEAD^{tree}")
    scanners = []
    for name in scanner_names:
        if not run_scanners:
            scanners.append({"name": name, "status": "NOT-RUN", "exit": None, "hits": None,
                             "note": "--run-scanners not given"})
            continue
        res = run_scanner(name, root, out_dir)
        scanners.append(res)
        if res["status"] == "RUN" and kind in SCANNERS[name]["kinds"]:
            for c in vet.coverage:
                if c["status"] == "READ" and name == "skillspector" and c["bytes"] <= DEFAULT_MAX_BYTES:
                    c["read_by"].append(name)
                elif c["status"] == "READ" and name in ("zizmor", "pinact") and \
                        (c["file"].startswith(".github/workflows/") or c["file"].endswith(("action.yml", "action.yaml"))):
                    c["read_by"].append(name)
    for row in hand:
        scanners.append(row)
        if row["hits"] == 0 and row["name"] in EXPECTED_SECOND_READER.get(kind, set()):
            for c in vet.coverage:
                if c["status"] == "READ" and row["name"] not in c["read_by"]:
                    c["read_by"].append(row["name"])
    decision = decide(vet, kind, sha, scanners, unpinned)
    return {"mode": "vet", "version": VERSION, "kind": kind, "sha": sha, "tree": tree,
            **decision, "coverage": vet.coverage, "findings": vet.findings, "scanners": scanners}


def revet(root: Path, old: str, new: str, max_bytes: int) -> dict:
    """Drift since the pinned SHA: what changed, which changes need a fresh read, the new tree hash.
    Reads git objects only; nothing is checked out or run."""
    diff = _git(root, "diff", "--no-ext-diff", "--no-textconv", "--name-status", old, new)
    if diff is None:
        return {"mode": "revet", "verdict": "HOLD", "reasons": ["git could not diff the two commits"],
                "changes": [], "terms": []}
    changes = []
    for line in diff.splitlines():
        parts = line.split("\t")
        status, path = parts[0][:1], parts[-1]
        ext = Path(path).suffix.lower()
        risky = (ext in BYTECODE_EXT | ARCHIVE_EXT | SCRIPT_EXT or path.startswith("bin/")
                 or path.endswith(("hooks.json", ".mcp.json", "plugin.json", "marketplace.json",
                                   "SKILL.md", "package.json", "settings.json"))
                 or path.startswith(".github/workflows/"))
        changes.append({"file": path, "change": status, "needs_read": bool(risky and status != "D")})
    tree_old = _git(root, "rev-parse", f"{old}^{{tree}}")
    tree_new = _git(root, "rev-parse", f"{new}^{{tree}}")
    need = [c["file"] for c in changes if c["needs_read"]]
    verdict = "HOLD" if need else "CONDITIONAL"
    reasons = ([f"{len(need)} changed file(s) need a fresh vet before the pin moves"] if need
               else ["no change touches code, config or instructions"])
    terms = [] if need else [f"pin-sha: move the pin to {new}",
                             "auto-update-off: keep auto-update off for the marketplace it comes from"]
    return {"mode": "revet", "version": VERSION, "from": old, "to": new, "tree_from": tree_old,
            "tree_to": tree_new, "verdict": verdict, "reasons": reasons, "changes": changes,
            "terms": terms}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Pre-install vet of a third-party candidate (read-only).")
    sub = ap.add_subparsers(dest="mode", required=True)
    v = sub.add_parser("vet")
    v.add_argument("path")
    v.add_argument("--kind", default="auto", choices=["auto", "skill", "plugin", "mcp", "action"])
    v.add_argument("--sha")
    v.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    v.add_argument("--run-scanners", action="store_true")
    v.add_argument("--scanners", default="skillspector,zizmor,pinact")
    v.add_argument("--out-dir")
    v.add_argument("--reader", action="append", default=[],
                   help="a second scanner the user ran by hand: NAME=clean or NAME=hits[:N] (repeatable)")
    r = sub.add_parser("revet")
    r.add_argument("path")
    r.add_argument("--from", dest="old", required=True)
    r.add_argument("--to", dest="new", required=True)
    r.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    a = ap.parse_args(argv)
    root = Path(a.path).resolve()
    if not root.is_dir():
        print(json.dumps({"mode": a.mode, "verdict": "NOT-RUN",
                          "reasons": ["candidate path is not a readable directory"]}))
        return 3
    try:
        if a.mode == "vet":
            names = [n.strip() for n in a.scanners.split(",") if n.strip() in SCANNERS]
            out_dir = Path(a.out_dir).resolve() if a.out_dir else None
            if out_dir:
                out_dir.mkdir(parents=True, exist_ok=True)
            res = vet_dir(root, a.kind, a.sha, a.max_bytes, names, a.run_scanners, out_dir, a.reader)
        else:
            res = revet(root, a.old, a.new, a.max_bytes)
    except Exception as exc:  # report the crash class only; never a traceback with candidate text
        print(json.dumps({"mode": a.mode, "verdict": "NOT-RUN", "reasons": [f"crash: {type(exc).__name__}"]}))
        return 4
    print(json.dumps(res, indent=2))
    return 0 if res["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
