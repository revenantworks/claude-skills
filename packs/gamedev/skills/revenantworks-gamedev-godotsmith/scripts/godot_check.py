#!/usr/bin/env python3
"""godot_check: run a Godot project's Check steps in order and print three numbers.

    python scripts/godot_check.py --project <dir> [--import-only] [--before "<cmd>"]
        [--lint <paths>...] [--gut "<gut args>" | --script <res path>]
        --expect-scripts N --expect-tests M [--repeat K] [--json] [--godot <exe>]

Order is the Check entry's: an optional --before command, the headless import (Check step 1),
then gdtoolkit's linter when it is installed (else the lint step prints NOT-RUN, never a pass),
then the GUT suite (or one --script) headless. Every step's output is scanned for the engine's
error markers (SCRIPT ERROR, Parse Error, Failed to load) BEFORE the summary is read; a marker
fails the run even under "All tests passed". The suite prints scripts, tests and failures as
three numbers against the expected totals with the slack (L1, L3). --repeat K runs the suite K
times and prints each run's numbers.

Exit: 0 every number matched and no marker fired; 1 a mismatch, a marker, a failure or a
nonzero step; 2 a usage error; 3 NOT-RUN (no Godot binary found). Stdlib only; run, not read.
Godot starts headless with no window. The repo's own CI runner stays the verdict where it has
one; this script is the shell-side Check, and it may be called by that runner.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from typing import Callable

NOT_RUN = 3
GUT_RUNNER = "addons/gut/gut_cmdln.gd"
MARKER = re.compile(r"SCRIPT ERROR|Parse Error|Failed to load", re.I)
LINE = {
    "scripts": re.compile(r"^\s*Scripts\s+(\d+)\s*$", re.M),
    "tests": re.compile(r"^\s*Tests\s+(\d+)\s*$", re.M),
    "passing": re.compile(r"^\s*Passing Tests\s+(\d+)\s*$", re.M),
    "failing": re.compile(r"^\s*Failing Tests\s+(\d+)\s*$", re.M),
    "pending": re.compile(r"^\s*(?:Pending|Risky/Pending)\s+(\d+)\s*$", re.M),
}


def parse_summary(log: str) -> dict | None:
    """The last GUT Totals block, read with line-anchored patterns; None when there is none."""
    found = {k: rx.findall(log) for k, rx in LINE.items()}
    if not found["scripts"] or not found["tests"]:
        return None
    s = {k: int(v[-1]) if v else None for k, v in found.items()}
    if s["failing"] is not None:
        s["failures"] = s["failing"]
    elif s["passing"] is not None:
        s["failures"] = max(0, s["tests"] - s["passing"] - (s["pending"] or 0))
    else:
        s["failures"] = None
    return s


def find_markers(log: str) -> list[str]:
    return [ln.strip() for ln in log.splitlines() if MARKER.search(ln)]


def numbers_line(s: dict, exp_scripts: int, exp_tests: int) -> str:
    def part(name, got, exp):
        slack = got - exp
        return f"{name} {got}/{exp}" + (f" ({slack:+d})" if slack else "")
    fails = "?" if s.get("failures") is None else s["failures"]
    return f"{part('scripts', s['scripts'], exp_scripts)} · {part('tests', s['tests'], exp_tests)}" \
           f" · failures {fails}" + (f" · pending {s['pending']}" if s.get("pending") else "")


def judge(s: dict | None, markers: list[str], rc: int, exp_scripts: int, exp_tests: int):
    """(ok, reason). Markers are read before the summary; every number must match."""
    if markers:
        return False, f"{len(markers)} engine error marker(s): {markers[0]}"
    if s is None:
        return False, "no GUT summary in the output"
    bad = []
    if s["scripts"] != exp_scripts:
        bad.append(f"scripts {s['scripts']} != expected {exp_scripts}")
    if s["tests"] != exp_tests:
        bad.append(f"tests {s['tests']} != expected {exp_tests}")
    if s.get("failures") != 0:
        bad.append(f"failures {s.get('failures')}")
    if rc != 0:
        bad.append(f"exit {rc}")
    return (not bad), ("; ".join(bad) if bad else "all numbers match")


def import_cmd(godot: str, project: str) -> list[str]:
    return [godot, "--headless", "--path", project, "--import"]


def suite_cmd(godot: str, project: str, gut: str | None, script: str | None) -> list[str]:
    head = [godot, "--headless", "--path", project, "-s"]
    if script:
        return head + [script]
    args = shlex.split(gut or "")
    if "-gexit" not in args:
        args.append("-gexit")
    return head + [GUT_RUNNER] + args


def lint_cmd(paths: list[str]) -> list[str]:
    return [sys.executable, "-m", "gdtoolkit.linter"] + paths


def run_process(cmd: list[str], cwd: str | None = None) -> tuple[int, str]:
    """The only live call: run with no window, output captured."""
    kw = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
    p = subprocess.run(cmd, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, **kw)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def gdtoolkit_present() -> bool:
    return importlib.util.find_spec("gdtoolkit") is not None


def parse_args(argv: list[str]) -> argparse.Namespace:
    ap = argparse.ArgumentParser(prog="godot_check.py", description=__doc__.split("\n\n")[0])
    ap.add_argument("--project", required=True, help="the folder holding project.godot")
    ap.add_argument("--godot", default="godot", help="Godot binary or shim (default: godot)")
    ap.add_argument("--import-only", action="store_true", help="run the headless import only")
    ap.add_argument("--before", help="a command to run first (codegen, a fixture build)")
    ap.add_argument("--lint", nargs="+", metavar="PATH", help="paths for gdtoolkit's linter")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--gut", help="GUT arguments, quoted (default: the project's .gutconfig)")
    g.add_argument("--script", help="run one res:// script headless instead of GUT")
    ap.add_argument("--expect-scripts", type=int)
    ap.add_argument("--expect-tests", type=int)
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--json", action="store_true", help="also print one JSON record last")
    a = ap.parse_args(argv)
    if not a.import_only and (a.expect_scripts is None or a.expect_tests is None):
        ap.error("--expect-scripts and --expect-tests are required (state the totals before the run)")
    if a.repeat < 1:
        ap.error("--repeat must be 1 or more")
    return a


def main(argv: list[str] | None = None, run: Callable = run_process,
         have_lint: Callable[[], bool] = gdtoolkit_present,
         which: Callable[[str], str | None] = shutil.which) -> int:
    a = parse_args(sys.argv[1:] if argv is None else argv)
    rec = {"project": a.project, "steps": {}, "runs": [], "verdict": None}

    def finish(verdict: str, rc: int) -> int:
        rec["verdict"] = verdict
        print(f"godot_check: {verdict}")
        if a.json:
            print(json.dumps(rec))
        return rc

    def step(name: str, cmd: list[str]) -> bool:
        rc, out = run(cmd, cwd=None)
        marks = find_markers(out)
        ok = rc == 0 and not marks
        rec["steps"][name] = {"exit": rc, "markers": marks[:5]}
        print(f"{name}: exit {rc}" + (f", {len(marks)} marker(s): {marks[0]}" if marks else "") +
              ("" if ok else " -> FAIL"))
        return ok

    if a.before and not step("before", shlex.split(a.before)):
        return finish("FAIL", 1)
    godot = which(a.godot)
    if not godot:
        print(f"godot: NOT-RUN ({a.godot} not found on PATH); nothing was measured")
        return finish("NOT-RUN", NOT_RUN)
    if not step("import", import_cmd(a.godot, a.project)):
        return finish("FAIL", 1)
    if a.import_only:
        return finish("PASS", 0)
    if a.lint:
        if have_lint():
            if not step("lint", lint_cmd(a.lint)):
                return finish("FAIL", 1)
        else:
            print("lint: NOT-RUN (gdtoolkit not installed); not a pass")
            rec["steps"]["lint"] = "NOT-RUN"
    all_ok = True
    for i in range(1, a.repeat + 1):
        rc, out = run(suite_cmd(a.godot, a.project, a.gut, a.script), cwd=None)
        marks = find_markers(out)
        s = parse_summary(out)
        ok, why = judge(s, marks, rc, a.expect_scripts, a.expect_tests)
        nums = numbers_line(s, a.expect_scripts, a.expect_tests) if s else "no summary"
        print(f"suite run {i}/{a.repeat}: {nums} · exit {rc} -> {'ok' if ok else 'FAIL: ' + why}")
        rec["runs"].append({"exit": rc, "markers": marks[:5], "ok": ok, "why": why,
                            **({k: s[k] for k in ("scripts", "tests", "failures", "pending")} if s else {})})
        all_ok = all_ok and ok
    return finish("PASS" if all_ok else "FAIL", 0 if all_ok else 1)


if __name__ == "__main__":
    sys.exit(main())
