#!/usr/bin/env python3
"""gatewarden install_hooks: put the repo's hook files into the live hooks folder, or check them.

Run, never read into context. Stdlib only, no network, windowless. The owner runs this;
gatewarden itself installs nothing.

    install_hooks.py --check [--hooks DIR] [--source DIR]
    install_hooks.py [--hooks DIR] [--source DIR] [--allow-branch]
                     [--settings FILE] [--no-settings-note]

--check lists each hook file in the source (`scripts/hooks/*.py` beside this script) with its
live hash, its repo hash and `same`, `differs` or `missing`; it writes nothing and exits 1 on
any difference (a scheduled drift check can call it). Without --check it installs:
each live file that differs is copied first to `<hooks>/.backup/<UTC stamp>/`, the repo
version is written in, the live file is read back and its hash verified, and one line per file
prints. It refuses to run from a checkout that is dirty or not on `main` unless
--allow-branch is given, and refuses outside a git checkout. It never writes settings.json:
it only reads it to say which documented hooks the settings do not register. Files in the
hooks folder that the repo does not ship (pin files, other hooks) are left alone.

--hooks defaults to `~/.claude/hooks/gatewarden`. Hashes ignore CRLF against LF, as drift.py
does, so a Windows checkout with autocrlf reads `same`.
Exit codes: 0 same or installed, 1 a difference (--check) or a failed verify, 2 refusal or input error.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
DEFAULT_SOURCE = HERE / "hooks"
DEFAULT_HOOKS = Path("~/.claude/hooks/gatewarden").expanduser()
DEFAULT_SETTINGS = Path("~/.claude/settings.json").expanduser()
HOOKS_DOC = SKILL / "references" / "hooks.md"
NAME = re.compile(r"[A-Za-z0-9_]+\.py")


def sha(p: Path, raw: bool = False) -> str:
    h = hashlib.sha256()
    data = p.read_bytes()
    h.update(data if raw else data.replace(b"\r\n", b"\n"))
    return h.hexdigest()


def hook_files(source: Path) -> list[Path]:
    return sorted(p for p in source.glob("*.py") if p.is_file())


def compare(source: Path, hooks: Path) -> list[tuple[str, str, str, str]]:
    """(name, live hash or '-', repo hash, status) for each shipped hook file."""
    rows = []
    for src in hook_files(source):
        live = hooks / src.name
        want = sha(src)
        if not live.is_file():
            rows.append((src.name, "-", want, "missing"))
            continue
        have = sha(live)
        rows.append((src.name, have, want, "same" if have == want else "differs"))
    return rows


def git(repo: Path, *args: str) -> str | None:
    kw: dict = {}
    if os.name == "nt":
        kw["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
    try:
        r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                           stdin=subprocess.DEVNULL, timeout=60, **kw)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def checkout_problem(source: Path) -> str | None:
    """Why the source checkout may not install, or None when it is clean and on main."""
    if git(source, "rev-parse", "--show-toplevel") is None:
        return "the source is not inside a git checkout (use --check, or run from a clone)"
    branch = git(source, "rev-parse", "--abbrev-ref", "HEAD")
    if branch != "main":
        return f"the checkout is on {branch or 'an unreadable HEAD'}, not main"
    status = git(source, "status", "--porcelain")
    if status is None:
        return "git status failed"
    if status:
        return "the checkout has uncommitted changes"
    return None


def documented_hooks() -> set[str]:
    try:
        text = HOOKS_DOC.read_text(encoding="utf-8")
    except OSError:
        return set()
    block = text.split("## The settings block", 1)
    if len(block) < 2:
        return set()
    return set(re.findall(r"<dir>/(" + NAME.pattern + r")", block[1]))


def registered_hooks(settings: Path) -> set[str] | None:
    try:
        data = json.loads(settings.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    found: set[str] = set()

    def walk(x) -> None:
        if isinstance(x, dict):
            cmd = x.get("command")
            if isinstance(cmd, str) and "gatewarden" in cmd.replace("\\", "/"):
                found.update(NAME.findall(cmd))
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(data.get("hooks", {}) if isinstance(data, dict) else {})
    return found


def settings_note(settings: Path, shipped: set[str]) -> list[str]:
    reg = registered_hooks(settings)
    if reg is None:
        return ["settings: not read (missing or not JSON); nothing compared"]
    documented = documented_hooks() & shipped
    if not documented:
        return ["settings: the documented hook block was not found; nothing compared"]
    out = []
    missing = sorted(documented - reg)
    extra = sorted(n for n in reg if n not in shipped)
    if missing:
        out.append("settings: documented but not registered: " + ", ".join(missing)
                   + " (the owner's choice; settings.json is never written here)")
    if extra:
        out.append("settings: registers a gatewarden file the repo does not ship: " + ", ".join(extra))
    if not out:
        out.append("settings: every documented hook is registered")
    return out


def run_check(source: Path, hooks: Path) -> int:
    rows = compare(source, hooks)
    for name, have, want, status in rows:
        print(f"{status:8} {name}  live={have[:12]}  repo={want[:12]}")
    extra = sorted(p.name for p in hooks.glob("*.py")) if hooks.is_dir() else []
    extra = [n for n in extra if n not in {r[0] for r in rows}]
    if extra:
        print("extra (not shipped by the repo, left alone): " + ", ".join(extra))
    bad = [r for r in rows if r[3] != "same"]
    print(f"{len(rows) - len(bad)} same, {len(bad)} not same")
    return 1 if bad else 0


def run_install(source: Path, hooks: Path, stamp: str) -> int:
    rows = compare(source, hooks)
    backup = hooks / ".backup" / stamp
    failed = 0
    for name, _have, _want, status in rows:
        src, live = source / name, hooks / name
        if status == "same":
            print(f"same      {name}")
            continue
        try:
            hooks.mkdir(parents=True, exist_ok=True)
            if status == "differs":
                backup.mkdir(parents=True, exist_ok=True)
                shutil.copy2(live, backup / name)
            tmp = hooks / (name + ".install-tmp")
            shutil.copyfile(src, tmp)
            os.replace(tmp, live)
            ok = sha(live, raw=True) == sha(src, raw=True)
        except OSError as e:
            print(f"FAILED    {name}: {e.__class__.__name__}")
            failed += 1
            continue
        if ok:
            print(f"{'updated' if status == 'differs' else 'added':9} {name}  verified {sha(live)[:12]}"
                  + (f"  (old copy in .backup/{stamp})" if status == "differs" else ""))
        else:
            print(f"FAILED    {name}: hash after copy does not match the repo")
            failed += 1
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Install or check the gatewarden hook files.")
    ap.add_argument("--check", action="store_true", help="compare only; exit 1 on any difference")
    ap.add_argument("--hooks", type=Path, default=DEFAULT_HOOKS, help="live hooks folder")
    ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="repo hooks folder")
    ap.add_argument("--allow-branch", action="store_true", help="install from a dirty or non-main checkout")
    ap.add_argument("--settings", type=Path, default=DEFAULT_SETTINGS, help="settings file, read only")
    ap.add_argument("--no-settings-note", action="store_true")
    a = ap.parse_args(argv)

    source, hooks = a.source.expanduser(), a.hooks.expanduser()
    if not hook_files(source):
        print(f"no hook files in {source}", file=sys.stderr)
        return 2
    if a.check:
        return run_check(source, hooks)
    if not a.allow_branch:
        why = checkout_problem(source)
        if why:
            print(f"refused: {why}. Fix that, or pass --allow-branch.", file=sys.stderr)
            return 2
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rc = run_install(source, hooks, stamp)
    if not a.no_settings_note:
        for line in settings_note(a.settings.expanduser(), {p.name for p in hook_files(source)}):
            print(line)
    return rc


if __name__ == "__main__":
    sys.exit(main())
