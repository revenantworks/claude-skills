#!/usr/bin/env python3
"""suite_slot: run one test suite under a machine-wide suite cap, at low priority.

    python scripts/suite_slot.py [--cap 4] [--cwd DIR] -- <command> [args...]

Optional helper for dispatchwright's suite cap (owner ruling 2026-10-16, observation 0446):
one cap of 4 suite processes on the whole machine, across every session and thread, and every
background suite at below-normal priority with no window. It waits until fewer than --cap
suite processes run, then starts the command at below-normal priority (Windows) or nice 10
(elsewhere), with no new window, relays its output and returns its exit code.

A suite process is one whose command line runs unittest, pytest, a ci_local runner,
warden_suites, or a headless Godot. Each process counts: a runner that fans out N headless
Godots uses N slots. Counting live processes needs no lock file and cannot leak a slot when a
run dies. The count is best effort: two runners that check in the same instant can both start.

Stdlib only. Exit code: the command's, or 2 on a usage error.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from typing import Callable, Iterable

SUITE = re.compile(r"unittest|pytest|ci_local|ci-local|warden_suites|godot.*--headless", re.I)
SELF = "suite_slot.py"
WINDOWS = os.name == "nt"
POLL_SECONDS = 15


def parse_args(argv: list[str]) -> argparse.Namespace:
    """--cap and --cwd, then the command after `--` (or every token when there is no `--`)."""
    ap = argparse.ArgumentParser(prog="suite_slot.py",
                                 description="Run a suite under a machine-wide suite cap.")
    ap.add_argument("--cap", type=int, default=4, help="suite processes allowed at once (default 4)")
    ap.add_argument("--cwd", default=None, help="folder to run the command in")
    if "--" in argv:
        i = argv.index("--")
        a = ap.parse_args(argv[:i])
        cmd = argv[i + 1:]
    else:
        ap.add_argument("cmd", nargs=argparse.REMAINDER)
        a = ap.parse_args(argv)
        cmd = a.cmd
    if not cmd:
        ap.error("no command (put it after --)")
    if a.cap < 1:
        ap.error("--cap must be 1 or more")
    a.cmd = cmd
    return a


def is_suite(cmdline: str) -> bool:
    """True for a suite process's command line; never for this runner's own."""
    return bool(cmdline) and SELF not in cmdline and bool(SUITE.search(cmdline))


def count_suites(cmdlines: Iterable[str]) -> int:
    return sum(1 for line in cmdlines if is_suite(line))


def list_cmdlines() -> list[str]:
    """Every live python or godot command line on the machine (the only live call)."""
    if WINDOWS:
        cmd = ["powershell", "-NoProfile", "-NonInteractive", "-Command",
               "Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python|godot' } | "
               "ForEach-Object { $_.CommandLine }"]
        kw = {"creationflags": subprocess.CREATE_NO_WINDOW}
    else:
        cmd, kw = ["ps", "-eo", "args="], {}
    out = subprocess.run(cmd, capture_output=True, text=True, **kw).stdout
    return out.splitlines()


def running_suites(listing: Callable[[], list[str]] = list_cmdlines) -> int:
    return count_suites(listing())


def child_options() -> dict:
    if WINDOWS:
        # CREATE_NO_WINDOW gives the child its own hidden console, so its output is relayed.
        return {"creationflags": subprocess.BELOW_NORMAL_PRIORITY_CLASS | subprocess.CREATE_NO_WINDOW}
    return {"preexec_fn": lambda: os.nice(10)}


def main(argv: list[str] | None = None) -> int:
    a = parse_args(sys.argv[1:] if argv is None else argv)
    waited = 0
    while (n := running_suites()) >= a.cap:
        if waited % 60 == 0:
            print(f"suite_slot: {n} suites running, cap {a.cap}; waiting", flush=True)
        time.sleep(POLL_SECONDS)
        waited += POLL_SECONDS
    p = subprocess.Popen(a.cmd, cwd=a.cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, **child_options())
    for chunk in iter(lambda: p.stdout.read1(65536), b""):
        sys.stdout.buffer.write(chunk)
        sys.stdout.flush()
    return p.wait()


if __name__ == "__main__":
    sys.exit(main())
