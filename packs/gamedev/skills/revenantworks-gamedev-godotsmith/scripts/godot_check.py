#!/usr/bin/env python3
"""godot_check: run a Godot project's Check steps in order and print three numbers.

    python scripts/godot_check.py --project <dir> [--import-only] [--before "<cmd>"]
        [--lint <paths>...] [--gut "<gut args>" | --script <res path>]
        --expect-scripts N --expect-tests M [--repeat K] [--json] [--godot <exe>]
    python scripts/godot_check.py --project <repo root> --parse-all
        [--exclude "<path>=<reason>"]... [--before "<cmd>"] [--jobs N] [--json] [--godot <exe>]

Order is the Check entry's: an optional --before command, the headless import (Check step 1),
then gdtoolkit's linter when it is installed (else the lint step prints NOT-RUN, never a pass),
then the GUT suite (or one --script) headless. Every step's output is scanned for the engine's
error markers (SCRIPT ERROR, Parse Error, Failed to load) BEFORE the summary is read; a marker
fails the run even under "All tests passed". The suite prints scripts, tests and failures as
three numbers against the expected totals with the slack (L1, L3). --repeat K runs the suite K
times and prints each run's numbers.

--parse-all answers one other question: does every .gd file under --project parse, not only the
folders CI lints? It finds the files itself (hidden folders aside), imports each project that
holds one, and has Godot parse each file with --check-only. That runs no _init or _ready, but
static initialisers do run, and the import writes beside the scripts: use it on a clean checkout of
code you would run anyway. A positive control comes first: a broken script made under .godot/ and
parsed by res:// like the rest must be rejected and a valid one accepted, or the run is NOT-RUN,
since a check that cannot see a parse error proves nothing. A file that cannot be parsed, a folder
that cannot be read, a linked folder holding scripts, a file in no project and an exclusion that
matches no file all fail the run, and so does finding nothing to parse.

Exit: 0 every number matched and no marker fired; 1 a mismatch, a marker, a failure or a
nonzero step; 2 a usage error; 3 NOT-RUN (no Godot binary, or a control that did not behave).
Stdlib only; run, not read.
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
import signal
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable

NOT_RUN = 3
PARSE_TIMEOUT = 120  # seconds per file; a parse takes well under one
KILL_WAIT = 5  # seconds to collect the output after killing a timed-out tree
CONTROL_BROKEN = "extends RefCounted\nfunc broken(:\n\tpass\n"
CONTROL_VALID = "extends RefCounted\n"
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


def parse_cmd(godot: str, project: str, script: str) -> list[str]:
    return [godot, "--headless", "--path", project, "--check-only", "-s", script]


def run_process(cmd: list[str], cwd: str | None = None, timeout: int | None = None) -> tuple[int, str]:
    """The only live call: run with no window, output captured."""
    kw = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {"start_new_session": True}
    p = subprocess.Popen(cmd, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, **kw)
    try:
        out, _ = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        _kill_tree(p)
        try:
            p.communicate(timeout=KILL_WAIT)
        except subprocess.TimeoutExpired:  # something outside the tree still holds the pipe
            pass
        return 124, f"timed out after {timeout} s\n"
    return p.returncode, out.decode("utf-8", "replace")


def _kill_tree(p: subprocess.Popen) -> None:
    """Kill the process and its children: a shim's child holds the pipe after the shim dies."""
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], stdin=subprocess.DEVNULL,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            os.killpg(p.pid, signal.SIGKILL)
    except OSError:
        p.kill()


def find_scripts(root: str) -> tuple[list[Path], list[str], dict[str, int]]:
    """(every .gd under root, folders that could not be read, {linked folder not followed: .gd inside})."""
    files: list[Path] = []
    unread: list[str] = []
    linked: dict[str, int] = {}

    def note_unread(err: OSError) -> None:
        unread.append(str(err.filename))

    for here, dirs, names in os.walk(root, onerror=note_unread):
        keep = []
        for d in sorted(dirs):
            if d.startswith("."):  # .git, .godot and tool folders hold no project script
                continue
            if os.path.islink(os.path.join(here, d)):
                link = os.path.join(here, d)
                linked[link] = sum(n.endswith(".gd") for _, _, ns in os.walk(link, onerror=note_unread) for n in ns)
                continue
            keep.append(d)
        dirs[:] = keep
        files += [Path(here) / n for n in sorted(names) if n.endswith(".gd")]
    return files, unread, linked


def owning_project(script: Path) -> Path | None:
    """The nearest folder at or above the script holding project.godot."""
    return next((d for d in script.parents if (d / "project.godot").is_file()), None)


def parse_excludes(items: list[str]) -> dict[str, str]:
    """{posix path relative to --project: reason}. A reason is required, so an exclusion explains itself."""
    out = {}
    for item in items:
        path, _, reason = item.partition("=")
        if not path.strip() or not reason.strip():
            raise ValueError(f"--exclude {item!r} needs the form <path>=<reason>")
        out[Path(path.strip()).as_posix()] = reason.strip()
    return out


def parse_verdict(rc: int, out: str) -> list[str]:
    """Why a parse did not pass; empty when it did."""
    marks = find_markers(out)
    return marks or ([f"exit {rc}"] if rc != 0 else [])


def control_problem(run: Callable, godot: str, project: Path) -> str | None:
    """None when Godot rejects a broken script and accepts a valid one in this project.

    The controls live under .godot/ and go by res://, the route every real file takes, and are removed.
    """
    cache = project / ".godot"
    made_cache = not cache.exists()

    def parse(body: str, name: str, folder: Path) -> tuple[int, str]:
        (folder / name).write_text(body, encoding="utf-8")
        res = f"res://.godot/{folder.name}/{name}"
        return run(parse_cmd(godot, str(project), res), cwd=None, timeout=PARSE_TIMEOUT)

    try:
        cache.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="godot-check-control-", dir=cache) as tmp:
            rc, out = parse(CONTROL_BROKEN, "control_broken.gd", Path(tmp))
            if rc == 0 or not find_markers(out):
                return f"a deliberately broken script was not rejected (exit {rc}, no error marker)"
            rc, out = parse(CONTROL_VALID, "control_valid.gd", Path(tmp))
            why = parse_verdict(rc, out)
            if why:
                return f"a valid script was rejected: {why[0]}"
    except OSError as err:
        return f"the control files could not be written under .godot/: {err}"
    finally:
        if made_cache:
            try:
                cache.rmdir()
            except OSError:  # the import or Godot put something there: it stays
                pass
    return None


def parse_all(a: argparse.Namespace, run: Callable, rec: dict) -> tuple[str, int]:
    """Parse every .gd under --project. Returns (verdict, exit code); prints as it goes."""
    root = Path(a.project)
    files, unread, linked = find_scripts(a.project)
    excludes = parse_excludes(a.exclude)
    excluded, stale, targets, homeless, unparsed_links, empty_links = [], dict(excludes), [], [], [], []
    for link, count in linked.items():
        rel = Path(os.path.relpath(link, root)).as_posix()
        if rel in excludes:
            excluded.append(rel)
            stale.pop(rel)
        elif count:
            unparsed_links.append((rel, count))
        else:
            empty_links.append(rel)
    for f in files:
        rel = f.relative_to(root).as_posix()
        if rel in excludes:
            excluded.append(rel)
            stale.pop(rel)
            continue
        project = owning_project(f.resolve())
        if project is None:
            homeless.append(rel)
        else:
            targets.append((rel, project, f.resolve().relative_to(project).as_posix()))
    projects = sorted({t[1] for t in targets}, key=str)
    import_failed = []
    for project in projects:
        rc, out = run(import_cmd(a.godot, str(project)), cwd=None)
        marks = find_markers(out)
        print(f"import {project.name}: exit {rc}" + (f", {len(marks)} marker(s), per file below" if marks else ""))
        if rc != 0:
            import_failed.append(project.name)
    if projects:
        problem = control_problem(run, a.godot, projects[0])
        if problem:
            print(f"control: NOT-RUN ({problem}); this check cannot see a parse error here")
            rec["parse"] = {"control": problem}
            return "NOT-RUN", NOT_RUN
        print("control: a broken script was rejected and a valid one accepted")

    def one(target: tuple) -> tuple[str, list[str]]:
        rel, project, res = target
        rc, out = run(parse_cmd(a.godot, str(project), "res://" + res), cwd=None, timeout=PARSE_TIMEOUT)
        return rel, parse_verdict(rc, out)

    with ThreadPoolExecutor(max_workers=a.jobs) as pool:
        results = list(pool.map(one, targets))
    failed = [(rel, why) for rel, why in results if why]
    print(f"parse: {len(files)} found · {len(results) - len(failed)} parsed · {len(failed)} failed · "
          f"{len(excluded)} excluded")
    for rel, why in failed:
        print(f"  FAIL {rel}: {why[0]}")
    for rel in excluded:
        print(f"  excluded {rel}: {excludes[rel]}")
    for rel in homeless:
        print(f"  FAIL {rel}: in no project (no project.godot at or above it), so not parsed")
    for path in stale:
        print(f"  FAIL --exclude {path}: matches no file")
    for path in unread:
        print(f"  FAIL {path}: folder could not be read")
    for rel, count in unparsed_links:
        print(f"  FAIL {rel}: linked folder holding {count} .gd file(s), not parsed; "
              "point --project at its target too, or --exclude it with a reason")
    for rel in empty_links:
        print(f"  note {rel}: linked folder with no .gd file, not followed")
    rec["parse"] = {"found": len(files), "parsed": len(results) - len(failed),
                    "failed": [{"path": rel, "errors": why[:3]} for rel, why in failed],
                    "excluded": {rel: excludes[rel] for rel in excluded}, "no_project": homeless,
                    "stale_excludes": list(stale), "unread": unread,
                    "linked_unparsed": {rel: count for rel, count in unparsed_links},
                    "import_failed": import_failed}
    if not results and not failed:
        print("parse: nothing was parsed, so nothing is proved")
    ok = results and not (failed or homeless or stale or unread or import_failed or unparsed_links)
    return ("PASS", 0) if ok else ("FAIL", 1)


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
    ap.add_argument("--parse-all", action="store_true",
                    help="parse every .gd under --project (pass the repo root); needs no totals")
    ap.add_argument("--exclude", action="append", default=[], metavar="PATH=REASON",
                    help="with --parse-all: leave one file out, path relative to --project, reason printed")
    ap.add_argument("--jobs", type=int, default=min(4, os.cpu_count() or 1),
                    help="with --parse-all: files parsed side by side (default min(4, cpu count))")
    a = ap.parse_args(argv)
    if a.parse_all:
        mixed = [flag for flag, on in (("--import-only", a.import_only), ("--lint", a.lint), ("--gut", a.gut),
                                       ("--script", a.script), ("--expect-scripts", a.expect_scripts is not None),
                                       ("--expect-tests", a.expect_tests is not None)) if on]
        if mixed:
            ap.error(f"--parse-all runs alone; drop {', '.join(mixed)}")
        if a.jobs < 1:
            ap.error("--jobs must be 1 or more")
        try:
            parse_excludes(a.exclude)
        except ValueError as err:
            ap.error(str(err))
        return a
    if a.exclude:
        ap.error("--exclude needs --parse-all")
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
    a.godot = godot  # the resolved path: Windows cannot start a .cmd shim from its bare name
    if a.parse_all:
        return finish(*parse_all(a, run, rec))
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
