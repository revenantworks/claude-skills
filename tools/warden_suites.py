#!/usr/bin/env python3
"""claude-skills — warden_suites: run every warden member's script suite locally.

    python tools/warden_suites.py

The local twin of the warden-ci workflow (observation 0372). Each suite runs from its own
`scripts` folder: packs/warden has no __init__.py, so a discover from the pack root finds
0 tests and exits 0. A suite that fails, or that ran 0 tests, fails the run, and so does
finding no suite at all. Every suite runs and reports; the line per member is
`<member>: <n> tests, <f> failures, exit <rc>`. The closing lines are unittest-shaped
totals over every suite (`Ran <sum> tests`, then `OK` or `FAILED (...)`), so a reader that
takes the last `Ran N` line (ci_local) gets the whole count, not the last suite's.

Exit 0 when every suite ran tests and passed, 1 otherwise.
Stdlib only. Run from anywhere; paths resolve from this file.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "packs" / "warden" / "skills"
RAN = re.compile(r"(?m)^Ran (\d+) tests?\b")
FAILED = re.compile(r"(?m)^FAILED \(([^)]*)\)")


def ran_count(log: str) -> int:
    """The test total from unittest's last `Ran N tests` line, 0 when there is none."""
    found = RAN.findall(log)
    return int(found[-1]) if found else 0


def tally(log: str) -> tuple[int, int]:
    """(tests ran, failures + errors) from unittest's closing lines; (0, 0) when absent."""
    bad = 0
    m = FAILED.findall(log)
    if m:
        bad = sum(int(n) for n in re.findall(r"(?:failures|errors)=(\d+)", m[-1]))
    return ran_count(log), bad


def suites(skills: Path = SKILLS) -> list[Path]:
    """Every member scripts folder that holds a test_*.py, in name order."""
    return sorted(d for d in skills.glob("*/scripts") if any(d.glob("test_*.py")))


def run_suite(d: Path) -> tuple[int, str]:
    """One member's discover, as a plain windowless process; (exit code, output)."""
    kw = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
    r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-p", "test_*.py"],
                       cwd=str(d), stdin=subprocess.DEVNULL, capture_output=True, text=True,
                       encoding="utf-8", errors="replace",
                       env=dict(os.environ, PYTHONUTF8="1"), **kw)
    return r.returncode, r.stdout + r.stderr


def main(argv: list[str] | None = None, skills: Path = SKILLS) -> int:
    ap = argparse.ArgumentParser(prog="warden_suites.py", description=__doc__.split("\n\n")[0])
    ap.parse_args(sys.argv[1:] if argv is None else argv)
    folders = suites(skills)
    if not folders:
        print(f"✗ no warden scripts folder holds test_*.py under {skills}")
        return 1
    status, total, total_bad, summary = 0, 0, 0, []
    for d in folders:
        member = d.parent.name
        print(f"── {member}", flush=True)
        rc, log = run_suite(d)
        print(log.rstrip(), flush=True)
        ran, bad = tally(log)
        if (rc != 0 or ran == 0) and not bad:
            bad = 1                       # a crash or an empty suite with no FAILED line
        total += ran
        total_bad += bad
        summary.append(f"{member}: {ran} tests, {bad} failures, exit {rc}")
        if rc != 0:
            print(f"✗ {member}: unittest exited {rc}")
            status = 1
        if ran == 0:
            print(f"✗ {member}: Ran 0 tests")
            status = 1
    print("\n".join(summary))
    print(f"\nRan {total} tests across {len(folders)} suites\n")
    print(f"FAILED (failures={total_bad})" if status else "OK")
    return status


if __name__ == "__main__":
    sys.exit(main())
