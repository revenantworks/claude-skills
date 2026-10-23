#!/usr/bin/env python3
"""claude-skills — ci_local: the repo's whole local CI as one plain Python process.

    python tools/ci_local.py [--only NAME ...] [--skip NAME ...] [--list] [--verbose] [--jobs N]

Runs, in order, the read-only list in CLAUDE.md and the CI workflows' checks:
build.py --check, the tools suite, warden_suites.py, pii_scan.py --tree, name_leak.py
(local only), mods/sync_shared.py --check, the VS Code bridge's Python and node tests,
`claude plugin validate --strict` for every pack and mod plugin, then every other member's
script suite (warden's run inside warden_suites). One line per step: name, exit code, tests
ran and failures where the step prints them. A failed step prints its last lines; every step
runs and reports. A step whose tool is absent (`claude`, `node`, the name list) prints NOT-RUN,
never a pass. No `bash -c`: each step is a plain process with no window, so it is the single
command for `ci_stamp.py run --repo . -- python tools/ci_local.py`.

Independent steps run side by side, at most --jobs at once (default min(6, cpu count));
--jobs 1 runs them one after another as before. Output stays in the fixed step order: each
step's line prints when it and every step before it have finished.

Exit 0 every step passed; 1 any step failed (or a suite ran 0 tests); 3 nothing failed but a
step was NOT-RUN; 2 a usage error. --skip names a step deliberately left out (printed SKIPPED,
not a failure). Stdlib only. Run from anywhere; paths resolve from this file.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
NOT_RUN = 3
RAN = re.compile(r"(?m)^Ran (\d+) tests?\b")
FAILED = re.compile(r"(?m)^FAILED \(([^)]*)\)")
TAIL = 25


@dataclass
class Step:
    name: str
    cmd: list[str]
    cwd: Path
    suite: bool = False            # a unittest suite: 0 tests fails it
    not_run: str = ""              # why it cannot run here, when its tool is absent
    not_run_codes: tuple = field(default_factory=tuple)  # exit codes the step uses for NOT-RUN


def counts(log: str) -> tuple[int | None, int]:
    """(tests ran or None, failures + errors) from unittest's closing lines."""
    ran = RAN.findall(log)
    bad = 0
    m = FAILED.findall(log)
    if m:
        bad = sum(int(n) for n in re.findall(r"(?:failures|errors)=(\d+)", m[-1]))
    return (int(ran[-1]) if ran else None), bad


def plan(root: Path = ROOT, which: Callable[[str], str | None] = shutil.which) -> list[Step]:
    tools = root / "tools"
    steps = [
        Step("build-check", [PY, str(tools / "build.py"), "--check"], root),
        Step("tools-tests", [PY, "-m", "unittest", "discover", "-s", "tools", "-p", "test_*.py"],
             root, suite=True),
        Step("warden-suites", [PY, str(tools / "warden_suites.py")], root),
        Step("pii-tree", [PY, str(tools / "pii_scan.py"), "--tree"], root),
        Step("name-leak", [PY, str(tools / "name_leak.py")], root, not_run_codes=(NOT_RUN,)),
        Step("mods-sync", [PY, str(root / "mods" / "sync_shared.py"), "--check"], root),
        Step("vscode-py", [PY, "-m", "unittest", "discover", "-s", "mods/vscode", "-p", "test_*.py"],
             root, suite=True),
        Step("vscode-node", ["node", "--test", "mods/vscode"], root,
             not_run="" if which("node") else "node not on PATH"),
    ]
    claude = which("claude")
    for manifest in sorted(root.glob("packs/*/.claude-plugin/plugin.json")) + \
            sorted(root.glob("mods/*/.claude-plugin/plugin.json")):
        d = manifest.parent.parent.relative_to(root).as_posix()
        steps.append(Step(f"validate:{d}", [claude or "claude", "plugin", "validate", "--strict", d],
                          root, not_run="" if claude else "claude not on PATH"))
    for sdir in sorted(root.glob("packs/*/skills/*/scripts")):
        if sdir.parts[-4] == "warden" or not any(sdir.glob("test_*.py")):
            continue
        steps.append(Step(f"suite:{sdir.parent.name}",
                          [PY, "-m", "unittest", "discover", "-s", ".", "-p", "test_*.py"],
                          sdir, suite=True))
    return steps


def run_step(step: Step) -> tuple[int, str]:
    """The only live call: one plain process, no window, output captured."""
    kw = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
    p = subprocess.run(step.cmd, cwd=step.cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, **kw)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def default_jobs() -> int:
    """Steps at once by default: min(6, cpu count)."""
    return min(6, os.cpu_count() or 1)


def main(argv: list[str] | None = None, root: Path = ROOT, run: Callable = run_step,
         which: Callable[[str], str | None] = shutil.which) -> int:
    ap = argparse.ArgumentParser(prog="ci_local.py", description=__doc__.split("\n\n")[0])
    ap.add_argument("--only", nargs="+", default=[], metavar="NAME", help="run only these steps")
    ap.add_argument("--skip", nargs="+", default=[], metavar="NAME", help="leave these steps out")
    ap.add_argument("--list", action="store_true", help="print the steps and run nothing")
    ap.add_argument("--verbose", action="store_true", help="print every step's whole output")
    ap.add_argument("--jobs", type=int, default=default_jobs(), metavar="N",
                    help="steps at once (default min(6, cpu count); 1 = one after another)")
    a = ap.parse_args(sys.argv[1:] if argv is None else argv)
    if a.jobs < 1:
        ap.error("--jobs must be at least 1")
    steps = plan(root, which)
    known = {s.name for s in steps}
    unknown = [n for n in a.only + a.skip if n not in known]
    if unknown:
        ap.error(f"unknown step(s): {', '.join(unknown)} (see --list)")
    if a.list:
        for s in steps:
            print(f"{s.name}: {' '.join(s.cmd)}" + (f"  [NOT-RUN: {s.not_run}]" if s.not_run else ""))
        return 0
    chosen = [s for s in steps if not (a.only and s.name not in a.only)]
    live = [s for s in chosen if s.name not in a.skip and not s.not_run]
    pool = ThreadPoolExecutor(max_workers=a.jobs)
    futures = {s.name: pool.submit(run, s) for s in live}   # submitted in plan order
    failed, not_run = [], []
    for s in chosen:
        if s.name in a.skip:
            print(f"{s.name}: SKIPPED (--skip)")
            continue
        if s.not_run:
            print(f"{s.name}: NOT-RUN ({s.not_run})")
            not_run.append(s.name)
            continue
        rc, out = futures[s.name].result()
        ran, bad = counts(out)
        if rc in s.not_run_codes:
            print(f"{s.name}: NOT-RUN (exit {rc})")
            not_run.append(s.name)
            continue
        zero = s.suite and not ran
        line = f"{s.name}: exit {rc}"
        if ran is not None:
            line += f", {ran} tests, {bad} failures"
        elif s.suite:
            line += ", 0 tests"
        ok = rc == 0 and not zero
        print(line + ("" if ok else " -> FAIL" + (" (0 tests)" if zero and rc == 0 else "")))
        if a.verbose or not ok:
            for ln in out.rstrip().splitlines()[-TAIL if not a.verbose else None:]:
                print(f"    {ln}")
        if not ok:
            failed.append(s.name)
        sys.stdout.flush()
    pool.shutdown()
    if failed:
        print(f"ci_local: FAIL ({len(failed)}: {', '.join(failed)})"
              + (f"; NOT-RUN: {', '.join(not_run)}" if not_run else ""))
        return 1
    if not_run:
        print(f"ci_local: NOT-RUN ({', '.join(not_run)}); every step that ran passed, not a pass")
        return NOT_RUN
    print("ci_local: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
