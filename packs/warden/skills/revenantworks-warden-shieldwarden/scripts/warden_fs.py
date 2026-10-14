"""warden_fs.py: path helpers shared by gatewarden's map, footprint, drift and loads scripts and
shieldwarden's signposts scan (pack-shared source: packs/warden/shared/). Stdlib only; imported,
never run.

Every script that prints a path passes it through `redact()` first, so no output
carries the home folder or the user name. Links (junctions, symlinks) are
detected without following them.
"""
from __future__ import annotations

import json
import os
import re
import stat
import sys
import time
from pathlib import Path

REPARSE = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
SCHEMA_VERSION = 1

# Secret shapes. A path segment or token matching one of these is dropped, never printed.
SECRET_RES = [
    re.compile(r"sk-[A-Za-z0-9_\-]{16,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"xox[abprs]-[A-Za-z0-9\-]{10,}"),
    re.compile(r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"),
    re.compile(r"(?=[A-Za-z0-9+/_\-]*\d)(?=[A-Za-z0-9+/_\-]*[A-Za-z])[A-Za-z0-9+/_\-]{40,}"),
]


def looks_secret(text: str) -> bool:
    return any(r.search(text) for r in SECRET_RES)


def norm(path: str) -> str:
    """Forward slashes; a Git Bash drive form (/<letter>/...) becomes the drive form; drive letter lowercased."""
    p = str(path).replace("\\", "/")
    m = re.match(r"^/([A-Za-z])(/|$)", p)
    if m and os.name == "nt":
        p = f"{m.group(1)}:/" + p[3:]
    m = re.match(r"^([A-Za-z]):(/|$)", p)
    if m:
        p = m.group(1).lower() + p[1:]
    if len(p) > 1 and p.endswith("/") and not re.match(r"^[a-z]:/$", p):
        p = p.rstrip("/")
    return p


def _home_forms() -> list[str]:
    forms = set()
    for h in (os.environ.get("USERPROFILE"), os.environ.get("HOME"), str(Path.home())):
        if h:
            forms.add(norm(h))
    return sorted(forms, key=len, reverse=True)


def _user_names() -> set[str]:
    names = set()
    for k in ("USERNAME", "USER", "LOGNAME"):
        v = os.environ.get(k)
        if v and len(v) > 1:
            names.add(v.casefold())
    try:
        names.add(Path.home().name.casefold())
    except RuntimeError:
        pass
    return {n for n in names if n}


HOMES = _home_forms()
USERS = _user_names()


def redact(path: str) -> str:
    """Home prefix -> '~', any segment equal to the user name -> '<user>', secret-shaped segments dropped."""
    p = norm(path)
    low = p.casefold()
    for h in HOMES:
        hl = h.casefold()
        if low == hl or low.startswith(hl + "/"):
            p = "~" + p[len(h):]
            break
    parts = []
    for seg in p.split("/"):
        if seg.casefold() in USERS:
            parts.append("<user>")
        elif looks_secret(seg):
            parts.append("<redacted>")
        else:
            parts.append(seg)
    return "/".join(parts)


def link_kind(entry) -> str | None:
    """'junction', 'symlink' or None for an os.DirEntry or Path, never following it."""
    try:
        if entry.is_symlink():
            return "symlink"
        p = Path(entry.path) if hasattr(entry, "path") else Path(entry)
        if hasattr(p, "is_junction") and p.is_junction():
            return "junction"
        st = entry.stat(follow_symlinks=False) if hasattr(entry, "stat") else os.lstat(p)
        if getattr(st, "st_file_attributes", 0) & REPARSE:
            return "junction"
    except OSError:
        return None
    return None


def link_target(path: str) -> str | None:
    try:
        return os.readlink(path)
    except (OSError, ValueError, AttributeError):
        return None


def is_repo(path: str) -> bool:
    return os.path.lexists(os.path.join(path, ".git"))


def write_json(obj: dict, out: str | None) -> None:
    text = json.dumps(obj, indent=2, ensure_ascii=False)
    if out and out != "-":
        Path(out).write_text(text + "\n", encoding="utf-8", newline="\n")
    else:
        sys.stdout.write(text + "\n")


def header(tool: str) -> dict:
    return {"tool": f"warden.{tool}", "schema": SCHEMA_VERSION,
            "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}


def human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"
