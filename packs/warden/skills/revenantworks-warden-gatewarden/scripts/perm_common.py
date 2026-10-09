#!/usr/bin/env python3
"""perm_common.py: settings discovery, masked loading and rule matching shared by
perm_audit.py and perm_explain.py. Stdlib only.

Matching follows the Claude Code permissions docs as read on 2026-10-01
(references/rule-grammar.md): deny, then ask, then allow, first match wins; a
Bash line is split on && || ; | and each part is checked; wrappers such as
timeout, nice and nohup are stripped; PowerShell rules match case-insensitively.
This is a model of the documented behaviour for audit and explanation, not the
harness itself: `perm_explain.py` says so on every answer.
"""
from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "hooks"))
import hooklib as hl  # noqa: E402

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
RULE_RE = re.compile(r"^\s*([A-Za-z_][\w-]*)\s*(?:\((.*)\))?\s*$", re.S)
SHELL_FAMILY = {"Bash", "PowerShell"}
WRAPPERS = {"time", "nice", "nohup", "stdbuf", "command", "builtin", "noglob", "timeout"}  # docs list; not xargs
PRIMARY_FIELD = {"Bash": "command", "PowerShell": "command", "Read": "file_path", "Edit": "file_path",
                 "Write": "file_path", "Grep": "path", "Glob": "path", "NotebookEdit": "notebook_path",
                 "WebFetch": "url"}


def parse_rule(rule: str) -> tuple[str, str | None]:
    m = RULE_RE.match(rule or "")
    if not m:
        return (rule or "", None)
    return m.group(1), m.group(2)


def fingerprint(value) -> str:
    raw = json.dumps(value, sort_keys=True) if not isinstance(value, str) else value
    return "sha256:" + hashlib.sha256(raw.encode("utf-8", "replace")).hexdigest()[:12]


def is_tracked(path: str) -> bool:
    d, name = os.path.split(os.path.abspath(path))
    try:
        p = subprocess.run(["git", "ls-files", "--error-unmatch", name], cwd=d, capture_output=True,
                           timeout=15, creationflags=NO_WINDOW)
        return p.returncode == 0
    except Exception:
        return False


def discover(project: str) -> list[tuple[str, str]]:
    """(scope, path) for every settings file that exists, managed first."""
    home = os.path.expanduser("~")
    program_files = os.environ.get("ProgramFiles")  # Windows managed-settings folder, read live
    cands = [
        ("managed", os.path.join(program_files, "ClaudeCode", "managed-settings.json") if program_files else ""),
        ("managed", "/Library/Application Support/ClaudeCode/managed-settings.json"),
        ("managed", "/etc/claude-code/managed-settings.json"),
        ("local", os.path.join(project, ".claude", "settings.local.json")),
        ("project", os.path.join(project, ".claude", "settings.json")),
        ("user", os.path.join(home, ".claude", "settings.json")),
    ]
    return [(s, p) for s, p in cands if os.path.isfile(p)]


def load(path: str) -> dict:
    """Load one settings file. Never returns or raises with file content in it."""
    info = {"path": path, "data": None, "raw": "", "error": None, "eol": "\n"}
    try:
        with open(path, encoding="utf-8", newline="") as fh:
            raw = fh.read()
    except OSError as exc:
        info["error"] = f"unreadable ({type(exc).__name__})"
        return info
    info["raw"] = raw
    info["eol"] = "\r\n" if "\r\n" in raw else "\n"
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("top level is not an object")
        info["data"] = data
    except json.JSONDecodeError as exc:
        info["error"] = f"invalid JSON at line {exc.lineno} column {exc.colno}"
    except ValueError as exc:
        info["error"] = str(exc)
    return info


def line_of(raw: str, needle: str) -> int:
    idx = raw.find(json.dumps(needle))
    return raw.count("\n", 0, idx) + 1 if idx >= 0 else 0


def rules_of(data: dict) -> dict[str, list[str]]:
    perms = data.get("permissions") or {}
    return {k: [r for r in (perms.get(k) or []) if isinstance(r, str)] for k in ("deny", "ask", "allow")}


# ---------------------------------------------------------------- matching

def strip_wrappers(cmd: str) -> str:
    toks = cmd.split()
    i = 0
    while i < len(toks):
        t = toks[i]
        if re.match(r"^[A-Za-z_]\w*=", t):
            i += 1
            continue
        if t in WRAPPERS:
            i += 1
            while i < len(toks) and toks[i].startswith("-"):
                i += 1
            if t == "timeout" and i < len(toks) and re.match(r"^\d", toks[i]):
                i += 1
            if t == "nice" and i < len(toks) and re.match(r"^-?\d+$", toks[i]):
                i += 1
            continue
        break
    return " ".join(toks[i:])


def spec_matches(tool: str, spec: str | None, text: str) -> bool:
    if spec is None or spec.strip() in ("", "*"):
        return True
    flags = re.I if tool == "PowerShell" else 0
    text = text.strip()
    if tool in SHELL_FAMILY:
        if spec.endswith(":*"):
            return text.lower().startswith(spec[:-2].lower()) if flags else text.startswith(spec[:-2])
        if spec.endswith(" *"):
            pat = re.escape(spec[:-2]).replace(r"\*", ".*") + r"(?:\s.*)?"
        else:
            pat = re.escape(spec).replace(r"\*", ".*")
        return re.fullmatch(pat, text, flags | re.S) is not None
    def norm(s: str) -> str:
        s = s.replace("\\", "/")
        while s.startswith("./"):
            s = s[2:]
        return s

    s, t = norm(spec), norm(text)
    if tool == "WebFetch" and s.startswith("domain:"):
        host = re.sub(r"^\w+://", "", t).split("/")[0]
        return host == s[7:] or host.endswith("." + s[7:])
    pat = re.escape(s).replace(r"\*\*", "\0").replace(r"\*", "[^/]*").replace("\0", ".*")
    return re.fullmatch(pat, t) is not None or fnmatch.fnmatch(t, s)


def tool_family_match(rule_tool: str, tool: str) -> bool:
    if rule_tool == tool:
        return True
    return (rule_tool == "Read" and tool in ("Grep", "Glob")) or \
           (rule_tool == "Edit" and tool in ("Write", "MultiEdit", "NotebookEdit"))


def decide(tool: str, text: str, files: list[dict]) -> dict:
    """First-match walk for one simple input. files: [{path, rules}]."""
    for kind in ("deny", "ask", "allow"):
        for f in files:
            for r in f["rules"][kind]:
                rt, spec = parse_rule(r)
                if tool_family_match(rt, tool) and spec_matches(tool, spec, text):
                    return {"decision": kind, "rule": r, "file": f["path"]}
    return {"decision": "default", "rule": None, "file": None}


def split_command(tool: str, command: str) -> list[str]:
    if tool not in SHELL_FAMILY:
        return [command]
    return [strip_wrappers(s) for s in hl.segments(command)] or [command]


def sample_of(spec: str) -> str:
    s = spec[:-2] if spec.endswith(":*") or spec.endswith(" *") else spec
    return s.replace("*", "x")
