#!/usr/bin/env python3
"""follow_sweep.py: stop follow-mode watchers that earlier sessions left running. Stdlib only.

Called by warden_digest.py at every session start. A `tail -f ... | grep --line-buffered ...` wait
never exits by itself, so it outlives the wait and the session; 24 such processes once ran for five
days and blocked a Git for Windows update (observation 0403). heredoc_guard's follow rule refuses
new ones from the shell tools; this sweep is the backstop for any other path (a Monitor command, a
script, a crash).

What it stops: tail.exe and grep.exe from Git for Windows' usr\\bin, older than AGE_HOURS, whose
command line follows a file (-f, -F, --follow) or waits on a stream (--line-buffered). Nothing else.
Windows only (elsewhere a no-op). It runs detached with no window, so session start never waits on
it, and it appends one line per stopped process to follow_sweep.log in the gatewarden state folder.
Never blocks, never prompts.
"""
from __future__ import annotations

import os
import subprocess

AGE_HOURS = 12
CREATE_NO_WINDOW = 0x08000000
CREATE_NEW_PROCESS_GROUP = 0x00000200

PS = (
    "$cut=(Get-Date).AddHours(-{age}); "
    "Get-CimInstance Win32_Process -Filter \"Name='tail.exe' OR Name='grep.exe'\" | "
    "Where-Object {{ $_.CreationDate -lt $cut -and $_.ExecutablePath -like '*\\usr\\bin\\*' -and "
    "$_.CommandLine -match '(\\s-[A-Za-z0-9]*[fF][A-Za-z0-9]*(\\s|$)|--follow|--line-buffered)' }} | "
    "ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; "
    "Add-Content -LiteralPath '{log}' -Value ((Get-Date -Format s) + ' stopped ' + $_.Name + ' ' + "
    "$_.ProcessId + ' from ' + $_.CreationDate.ToString('s')) }}"
)


def script(log: str, age: int = AGE_HOURS) -> str:
    return PS.format(age=int(age), log=log.replace("'", "''"))


def spawn(state_dir: str, age: int = AGE_HOURS):
    """Start the sweep detached; return the Popen, or None where it does not apply or cannot start."""
    if os.name != "nt":
        return None
    log = os.path.join(state_dir, "follow_sweep.log")
    try:
        return subprocess.Popen(
            ["powershell", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command",
             script(log, age)],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP)
    except OSError:
        return None
