#!/usr/bin/env python3
"""gdformat_check - a check-only GDScript format hook for Claude Code (PostToolUse).

After Write, Edit or MultiEdit touches a `.gd` file, run a formatter in check mode on that one
file. The file is never changed: the hook only reports.

Formatter, first found wins:
  GDSCRIPT_FORMAT_CMD  a JSON list, such as ["gdscript-formatter"]; `--check` and the file are
                       appended
  gdscript-formatter   GDQuest's formatter: `gdscript-formatter --check <file>`
  gdformat             gdtoolkit: `gdformat --check --diff <file>`

Outcomes:
  formatted               silent, exit 0
  needs formatting        the formatter's output on stderr, exit 2 (Claude Code shows it to
                          Claude after the tool ran; nothing is blocked or undone)
  no formatter on PATH    one NOT-RUN line on stdout, exit 0; nothing is installed
  crash, timeout, a gdformat parse failure
                          one NOT-RUN line with the reason on stdout, exit 0
Not a .gd file, a missing file or unreadable hook input: silent, exit 0.

GDSCRIPT_FORMAT_TIMEOUT sets the formatter's time limit in seconds (default 20).
Python 3 standard library only. No network.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable

CREATE_NO_WINDOW = 0x08000000
TOOLS = ("Write", "Edit", "MultiEdit")
MAX_LINES = 40


def pick_formatter(env, which: Callable[[str], str | None]):
    """(name, argv-before-the-file) for the first formatter found, or (None, None)."""
    raw = env.get("GDSCRIPT_FORMAT_CMD")
    if raw:
        try:
            cmd = json.loads(raw)
        except ValueError:
            return None, None
        if not (isinstance(cmd, list) and cmd and all(isinstance(c, str) for c in cmd)):
            return None, None
        return Path(cmd[0]).stem, [*cmd, "--check"]
    exe = which("gdscript-formatter")
    if exe:
        return "gdscript-formatter", [exe, "--check"]
    exe = which("gdformat")
    if exe:
        return "gdformat", [exe, "--check", "--diff"]
    return None, None


def classify(name: str, code: int, output: str) -> str:
    """clean, dirty (needs formatting) or error (could not check)."""
    if code == 0:
        return "clean"
    if code == 1:
        if name == "gdformat":
            # gdformat exits 1 both for "would reformat" and for a file it cannot parse.
            return "dirty" if "would reformat" in output else "error"
        return "dirty"
    return "error"


def target_file(payload) -> Path | None:
    if not isinstance(payload, dict) or payload.get("tool_name") not in TOOLS:
        return None
    ti = payload.get("tool_input")
    if not isinstance(ti, dict) or not isinstance(ti.get("file_path"), str):
        return None
    p = Path(ti["file_path"])
    if p.suffix.lower() != ".gd" or not p.is_file():
        return None
    return p


def not_run(reason: str) -> int:
    print(f"gdscript format check: NOT-RUN - {reason}")
    return 0


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "null")
    except ValueError:
        return 0
    path = target_file(payload)
    if path is None:
        return 0
    name, argv = pick_formatter(os.environ, shutil.which)
    if name is None:
        return not_run("neither gdscript-formatter nor gdformat is on PATH, and "
                       "GDSCRIPT_FORMAT_CMD is unset or not a JSON list; nothing was installed")
    try:
        limit = float(os.environ.get("GDSCRIPT_FORMAT_TIMEOUT", "20"))
    except ValueError:
        limit = 20.0
    kw = {"creationflags": CREATE_NO_WINDOW} if os.name == "nt" else {}
    try:
        r = subprocess.run([*argv, str(path)], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=limit,
                           stdin=subprocess.DEVNULL, **kw)
    except subprocess.TimeoutExpired:
        return not_run(f"{name} timed out after {limit:g}s on {path.name}")
    except OSError as e:
        return not_run(f"{name} could not start: {e}")
    output = (r.stdout + r.stderr).strip()
    verdict = classify(name, r.returncode, output)
    if verdict == "clean":
        return 0
    if verdict == "error":
        first = output.splitlines()[0] if output else "no output"
        return not_run(f"{name} exit {r.returncode} on {path.name}: {first}")
    lines = output.splitlines()
    shown = "\n".join(lines[:MAX_LINES])
    more = f"\n... {len(lines) - MAX_LINES} more lines" if len(lines) > MAX_LINES else ""
    sys.stderr.write(f"{name} --check: {path} is not formatted (check only; the file was not "
                     f"changed). To apply, run the formatter on it yourself.\n{shown}{more}\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
