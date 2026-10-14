#!/usr/bin/env python3
"""claude-skills — warden_suites: run every warden member's script suite locally.

    python tools/warden_suites.py

The local twin of the warden-ci workflow (observation 0372). Each suite runs from its own
`scripts` folder: packs/warden has no __init__.py, so a discover from the pack root finds
0 tests and exits 0. A suite that fails, or that ran 0 tests, fails the run, and so does
finding no suite at all. Every suite runs and reports; the last line per member is
`<member>: <n> tests, exit <rc>`.

Exit 0 when every suite ran tests and passed, 1 otherwise.
Stdlib only. Run from anywhere; paths resolve from this file.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "packs" / "warden" / "skills"
RAN = re.compile(r"(?m)^Ran (\d+) tests?\b")


def ran_count(log: str) -> int:
    """The test total from unittest's last `Ran N tests` line, 0 when there is none."""
    found = RAN.findall(log)
    return int(found[-1]) if found else 0


def suites(skills: Path = SKILLS) -> list[Path]:
    """Every member scripts folder that holds a test_*.py, in name order."""
    return sorted(d for d in skills.glob("*/scripts") if any(d.glob("test_*.py")))


def main() -> int:
    folders = suites()
    if not folders:
        print(f"✗ no warden scripts folder holds test_*.py under {SKILLS.relative_to(ROOT)}")
        return 1
    env = dict(os.environ, PYTHONUTF8="1")
    status = 0
    summary = []
    for d in folders:
        member = d.parent.name
        print(f"── {member}", flush=True)
        r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-p", "test_*.py"],
                           cwd=str(d), stdin=subprocess.DEVNULL, capture_output=True,
                           text=True, encoding="utf-8", errors="replace", env=env)
        log = r.stdout + r.stderr
        print(log.rstrip(), flush=True)
        ran = ran_count(log)
        summary.append(f"{member}: {ran} tests, exit {r.returncode}")
        if r.returncode != 0:
            print(f"✗ {member}: unittest exited {r.returncode}")
            status = 1
        if ran == 0:
            print(f"✗ {member}: Ran 0 tests")
            status = 1
    print("\n".join(summary))
    return status


if __name__ == "__main__":
    sys.exit(main())
