#!/usr/bin/env python3
"""follow_sweep.py: stop follow-mode watchers that earlier sessions left running. Stdlib only.

Called by warden_digest.py at every session start. A `tail -f ... | grep --line-buffered ...` wait
never exits by itself, so it outlives the wait and the session; 24 such processes once ran for five
days and blocked a Git for Windows update (observation 0403). heredoc_guard's follow rule refuses
new ones from the shell tools, and from a script file a line runs (observation 0439); this sweep is
the backstop for any other path (a Monitor command, a crash).

What it stops: tail.exe and grep.exe from Git for Windows' usr\\bin whose command line follows a file
(-f, -F, --follow) or waits on a stream (--line-buffered), when they are older than AGE_HOURS, or
older than ORPHAN_MINUTES with their parent process gone (an orphan: the shell that started it
ended, so nothing will ever read or stop it; observation 0439). Nothing else. Windows only
(elsewhere a no-op). It runs detached with no window, so session start never waits on it, and it
appends one line per stopped process to follow_sweep.log in the gatewarden state folder.
Never blocks, never prompts.
"""
from __future__ import annotations

import os
import re
import subprocess

AGE_HOURS = 12
ORPHAN_MINUTES = 30
CREATE_NO_WINDOW = 0x08000000
CREATE_NEW_PROCESS_GROUP = 0x00000200
FOLLOWS = re.compile(r"(\s-[A-Za-z0-9]*[fF][A-Za-z0-9]*(\s|$)|--follow|--line-buffered)")

PS = (
    "$cut=(Get-Date).AddHours(-{age}); $ocut=(Get-Date).AddMinutes(-{orphan}); "
    "$all=@(Get-CimInstance Win32_Process); $ids=@($all | ForEach-Object {{ $_.ProcessId }}); "
    "$all | Where-Object {{ ($_.Name -eq 'tail.exe' -or $_.Name -eq 'grep.exe') -and "
    "$_.ExecutablePath -like '*\\usr\\bin\\*' -and "
    "$_.CommandLine -match '(\\s-[A-Za-z0-9]*[fF][A-Za-z0-9]*(\\s|$)|--follow|--line-buffered)' -and "
    "($_.CreationDate -lt $cut -or ($_.CreationDate -lt $ocut -and -not ($ids -contains $_.ParentProcessId))) }} | "
    "ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; "
    "Add-Content -LiteralPath '{log}' -Value ((Get-Date -Format s) + ' stopped ' + $_.Name + ' ' + "
    "$_.ProcessId + ' from ' + $_.CreationDate.ToString('s')) }}"
)


def script(log: str, age: int = AGE_HOURS, orphan: int = ORPHAN_MINUTES) -> str:
    return PS.format(age=int(age), orphan=int(orphan), log=log.replace("'", "''"))


def pick(procs: list[dict], now: float, age: int = AGE_HOURS, orphan: int = ORPHAN_MINUTES) -> list[int]:
    """The rule the PowerShell sweep applies, in Python (for the tests and a reader): each proc is
    {pid, ppid, name, path, cmd, started (epoch s)}; returns the pids to stop."""
    alive = {p.get("pid") for p in procs}
    out = []
    for p in procs:
        if str(p.get("name", "")).lower() not in ("tail.exe", "grep.exe"):
            continue
        if "\\usr\\bin\\" not in str(p.get("path", "")).lower().replace("/", "\\"):
            continue
        if not FOLLOWS.search(" " + str(p.get("cmd", ""))):
            continue
        old = now - float(p.get("started", now))
        if old > age * 3600 or (old > orphan * 60 and p.get("ppid") not in alive):
            out.append(p["pid"])
    return out


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
