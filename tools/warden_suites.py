#!/usr/bin/env python3
"""claude-skills — warden_suites: run every warden member's script suite locally.

    python tools/warden_suites.py [--jobs N] [--shards N] [--split-over SECONDS]

The local twin of the warden-ci workflow (observation 0372). Each suite runs from its own
`scripts` folder: packs/warden has no __init__.py, so a discover from the pack root finds
0 tests and exits 0. A suite that fails, or that ran 0 tests, fails the run, and so does
finding no suite at all. Every suite runs and reports; the line per member is
`<member>: <n> tests, <f> failures, exit <rc>`. The closing lines are unittest-shaped
totals over every suite (`Ran <sum> tests`, then `OK` or `FAILED (...)`), so a reader that
takes the last `Ran N` line (ci_local) gets the whole count, not the last suite's.

Speed: the suites run in parallel, one windowless process each (--jobs, default the cpu
count; --jobs 1 runs them one after another). A member whose tests are estimated to cost
more than --split-over seconds (default 60; gatewarden's push-gate tests spawn git, bash and
python, about 650 s serial) is split by test id into one process per --split-over seconds
of cost, at most --shards (default 12), balanced by the measured per-class cost in COST.
A member whose test listing fails (an import error) runs unsplit, so the error prints as it
always did. --shards 1 never splits. Output stays in member order whatever finishes first.

Exit 0 when every suite ran tests and passed, 1 otherwise.
Stdlib only. Run from anywhere; paths resolve from this file.
"""
from __future__ import annotations

import argparse
import math
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "packs" / "warden" / "skills"
RAN = re.compile(r"(?m)^Ran (\d+) tests?\b")
FAILED = re.compile(r"(?m)^FAILED \(([^)]*)\)")

# Measured seconds per test, by "<module>.<Class>" (gatewarden, the rig, 2026-10-23,
# `unittest --durations 0`, modules run side by side, so
# the figures are inflated alike). A class not listed costs DEFAULT_COST. Only the balance
# between shards reads these; a stale figure costs speed, never a test.
COST: dict[str, float] = {
    "test_hooks.PushGateTests": 5.8,  # 34 tests, 198 s
    "test_hooks.PushGateBypassTests": 8.2,  # 17 tests, 139 s
    "test_hooks_public_branch.PublicBranchGuardTests": 6.9,  # 7 tests, 49 s
    "test_hooks.VerifierPushTests": 3.7,  # 11 tests, 41 s
    "test_hooks_shapes.B5": 4.1,  # 8 tests, 33 s
    "test_hooks.HookBacklogStampTests": 5.2,  # 5 tests, 26 s
    "test_hooks.CiStampTests": 2.3,  # 11 tests, 25 s
    "test_hooks.HyperVLockTests": 1.3,  # 17 tests, 23 s
    "test_cap_review.EventLogTests": 2.3,  # 10 tests, 23 s
    "test_hooks_public_branch.PublicBranchModeTests": 7.2,  # 3 tests, 22 s
    "test_cap_review.ClassifierTests": 2.4,  # 9 tests, 22 s
    "test_hooks_shapes.B3": 4.1,  # 5 tests, 21 s
    "test_hooks_shapes.B5redirect": 3.8,  # 5 tests, 19 s
    "test_hooks.K8w3bPushTests": 2.2,  # 8 tests, 18 s
    "test_hooks.GoLiveBlockTests": 1.8,  # 9 tests, 16 s
    "test_hooks.PushConfigAtInstallDefaultTests": 2.7,  # 6 tests, 16 s
    "test_hooks_shapes.B5env": 2.6,  # 6 tests, 16 s
    "test_hooks.HiddenScriptTests": 7.5,  # 2 tests, 15 s
    "test_hooks.Obs0384Tests": 2.1,  # 7 tests, 14 s
    "test_hooks_public_branch.VisibilityLookupTests": 3.6,  # 4 tests, 14 s
    "test_hooks_shapes.B9": 4.5,  # 3 tests, 14 s
    "test_hooks.HookBacklogCapTests": 4.5,  # 3 tests, 13 s
    "test_hooks_shapes.B8": 3.1,  # 4 tests, 13 s
    "test_hooks.K8w3bDirectRuleTests": 2.0,  # 6 tests, 12 s
    "test_hooks_shapes.B10": 6.0,  # 2 tests, 12 s
    "test_hooks.HyperVBypassTests": 1.6,  # 7 tests, 11 s
    "test_hooks_shapes.B1": 2.2,  # 5 tests, 11 s
    "test_hooks_shapes.B2": 2.6,  # 4 tests, 10 s
    "test_hooks_shapes.FP_D": 3.2,  # 3 tests, 10 s
    "test_hooks.HookBacklogB1Tests": 2.9,  # 3 tests, 9 s
    "test_hooks.Obs0403FollowTests": 2.6,  # 3 tests, 8 s
    "test_perm_audit.AuditTests": 0.3,  # 21 tests, 7 s
    "test_hooks.CallCapTests": 0.9,  # 7 tests, 6 s
    "test_hooks.VerifierStdinTests": 1.2,  # 5 tests, 6 s
    "test_hooks_shapes.GhRefs": 1.8,  # 3 tests, 5 s
    "test_hooks.HardRulesAtInstallDefaultTests": 0.7,  # 8 tests, 5 s
    "test_hooks.Obs0414Tests": 2.6,  # 2 tests, 5 s
    "test_hooks_shapes.FP_A": 2.3,  # 2 tests, 5 s
    "test_hooks.HeredocGuardTests": 0.4,  # 11 tests, 4 s
    "test_hooks_shapes.B4": 2.2,  # 2 tests, 4 s
    "test_hooks_shapes.FP_C": 2.2,  # 2 tests, 4 s
    "test_hooks.RunnerPositionTests": 1.4,  # 3 tests, 4 s
    "test_hooks_shapes.FP_B": 2.0,  # 2 tests, 4 s
    "test_hooks.Obs0410Tests": 1.3,  # 3 tests, 4 s
    "test_hooks.HookTestFileExemptionTests": 1.6,  # 2 tests, 3 s
    "test_hooks.ReviewSetTests": 0.4,  # 5 tests, 2 s
    "test_hooks.GoLiveBypassTests": 0.8,  # 2 tests, 2 s
    "test_hooks_shapes.B6": 0.7,  # 2 tests, 1 s
    "test_hooks.VerifierHardTextTests": 0.7,  # 2 tests, 1 s
    "test_hooks.ReviewSnoozeTests": 0.7,  # 2 tests, 1 s
    "test_hooks.CiStampMaskTests": 1.2,  # 1 tests, 1 s
    "test_hooks.HookBacklogFollowTests": 0.3,  # 3 tests, 1 s
    # shieldwarden, measured alone
    "test_shield_scan.TestTree": 1.3,  # 13 tests, 17 s (serial)
    "test_shield_scan.TestExposure": 1.4,  # 8 tests, 11 s (serial)
    "test_shield_scan.TestInjectionAndControl": 1.5,  # 6 tests, 9 s (serial)
    "test_shield_scan.TestEmitVerify": 1.5,  # 4 tests, 6 s (serial)
    "test_shield_scan.TestHistory": 1.4,  # 3 tests, 4 s (serial)
    "test_identity_check.IdentityMode": 0.7,  # 6 tests, 4 s (serial)
    "test_rewrite_tools.RestoreAndSizeTests": 1.2,  # 2 tests, 2 s (serial)
    "test_shield_scan.TestSurface": 0.3,  # 3 tests, 1 s (serial)
}
DEFAULT_COST = 0.2

# Child programs (run with `python -c` from the member's scripts folder).
LIST_IDS = r"""
import sys, unittest
def walk(s):
    for t in s:
        if isinstance(t, unittest.TestSuite):
            yield from walk(t)
        else:
            yield t
ids = [t.id() for t in walk(unittest.defaultTestLoader.discover(".", "test_*.py"))]
print("\n".join(ids))
sys.exit(3 if any(i.startswith("unittest.") for i in ids) else 0)
"""
RUN_IDS = r"""
import sys, unittest
ids = sys.stdin.read().split()
suite = unittest.defaultTestLoader.loadTestsFromNames(ids)
r = unittest.TextTestRunner(stream=sys.stderr, verbosity=1).run(suite)
sys.exit(5 if not r.testsRun else (0 if r.wasSuccessful() else 1))
"""


@dataclass
class Job:
    member: str
    label: str                 # the header line: member, plus "(shard i/n)" when split
    cwd: Path
    cmd: list[str]
    stdin: str | None = None


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


def weight(test_id: str) -> float:
    """Estimated seconds for one test id `<module>.<Class>.<method>`."""
    return COST.get(test_id.rsplit(".", 1)[0], DEFAULT_COST)


def balance(ids: list[tuple[str, float]], n: int) -> list[list[str]]:
    """Split (id, cost) pairs into at most n non-empty shards, heaviest first onto the
    lightest shard (longest-processing-time); each shard keeps discovery order."""
    n = max(1, min(n, len(ids)))
    order = {i: k for k, (i, _) in enumerate(ids)}
    loads, shards = [0.0] * n, [[] for _ in range(n)]
    for i, w in sorted(ids, key=lambda p: -p[1]):
        k = loads.index(min(loads))
        loads[k] += w
        shards[k].append(i)
    return [sorted(s, key=order.__getitem__) for s in shards if s]


def _run(cmd: list[str], cwd: Path, stdin: str | None = None) -> tuple[int, str]:
    """One plain windowless process; (exit code, stdout + stderr)."""
    kw = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
    r = subprocess.run(cmd, cwd=str(cwd), input=stdin if stdin is not None else "",
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=dict(os.environ, PYTHONUTF8="1"), **kw)
    return r.returncode, r.stdout + r.stderr


def jobs_for(d: Path, shards: int, split_over: float) -> list[Job]:
    """One job for a member, or several when its estimated cost is over split_over."""
    member = d.parent.name
    whole = Job(member, member, d, [sys.executable, "-m", "unittest", "discover", "-p", "test_*.py"])
    if shards <= 1:
        return [whole]
    rc, out = _run([sys.executable, "-c", LIST_IDS], d)
    ids = [ln.strip() for ln in out.splitlines() if ln.strip()]
    if rc != 0 or not ids:
        return [whole]                     # an import error or no tests: report it unsplit
    costed = [(i, weight(i)) for i in ids]
    cost = sum(w for _, w in costed)
    if cost <= split_over:
        return [whole]
    n = shards if split_over <= 0 else min(shards, math.ceil(cost / split_over))
    parts = balance(costed, n)
    return [Job(member, f"{member} (shard {k}/{len(parts)})", d,
                [sys.executable, "-c", RUN_IDS], "\n".join(p))
            for k, p in enumerate(parts, 1)]


def main(argv: list[str] | None = None, skills: Path = SKILLS) -> int:
    ap = argparse.ArgumentParser(prog="warden_suites.py", description=__doc__.split("\n\n")[0])
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 1,
                    help="processes at once (1 = one after another)")
    ap.add_argument("--shards", type=int, default=12,
                    help="most processes a heavy member splits into")
    ap.add_argument("--split-over", type=float, default=60.0, metavar="SECONDS",
                    help="split a member whose estimated cost is over this")
    a = ap.parse_args(sys.argv[1:] if argv is None else argv)
    if a.jobs < 1 or a.shards < 1:
        ap.error("--jobs and --shards must be at least 1")
    folders = suites(skills)
    if not folders:
        print(f"✗ no warden scripts folder holds test_*.py under {skills}")
        return 1
    with ThreadPoolExecutor(max_workers=a.jobs) as pool:
        plans = list(pool.map(lambda d: jobs_for(d, a.shards, a.split_over), folders))
        jobs = [j for p in plans for j in p]
        results = list(pool.map(lambda j: _run(j.cmd, j.cwd, j.stdin), jobs))
    per: dict[str, list[int]] = {}           # member -> [ran, bad, worst rc]
    for j, (rc, log) in zip(jobs, results):
        print(f"── {j.label}", flush=True)
        print(log.rstrip(), flush=True)
        ran, bad = tally(log)
        if rc != 0 and not bad:
            bad = 1                           # a crash with no FAILED line still counts
        m = per.setdefault(j.member, [0, 0, 0])
        m[0] += ran
        m[1] += bad
        m[2] = m[2] or rc
    status, summary = 0, []
    for d in folders:
        member = d.parent.name
        ran, bad, rc = per[member]
        if rc != 0:
            print(f"✗ {member}: unittest exited {rc}")
            status = 1
        if ran == 0:
            print(f"✗ {member}: Ran 0 tests")
            status = 1
            bad = bad or 1
            per[member][1] = bad
        summary.append(f"{member}: {ran} tests, {bad} failures, exit {rc}")
    print("\n".join(summary))
    total = sum(v[0] for v in per.values())
    total_bad = sum(v[1] for v in per.values())
    print(f"\nRan {total} tests across {len(folders)} suites, {len(jobs)} processes\n")
    print(f"FAILED (failures={total_bad})" if status else "OK")
    return status


if __name__ == "__main__":
    sys.exit(main())
