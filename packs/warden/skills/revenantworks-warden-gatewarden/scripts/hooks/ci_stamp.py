#!/usr/bin/env python3
"""ci_stamp.py: run a repo's local CI steps and stamp HEAD when they pass.

  python ci_stamp.py run --repo <dir> [--excluded "NAME: REASON" ...] [--runs N] -- <command> [args...]
  python ci_stamp.py run --repo <dir> --step "<step 1>" --step "<step 2>" ...
  python ci_stamp.py run --repo <dir> --no-ci
  python ci_stamp.py show --repo <dir>

`run` refuses a tree with uncommitted changes (the stamp must describe a commit),
runs the command with no shell, stdin from the null device and PYTHONUTF8=1, and
writes `<git dir>/gatewarden/ci-pass.json` only when the command exits 0 and HEAD
did not move while it ran. push_gate.py reads that file. The run's combined output
goes to `<git dir>/gatewarden/ci-last.log` and is echoed; on failure the last 20
lines are printed again. Each `--excluded` item is recorded in the stamp and
printed, so the gate shows what the local run did not cover, and the stamp is
marked partial: the push gate then says loudly that the local verdict is not the CI
verdict (observation 0354).

Several CI steps: repeat `--step`, one command line each, split like a shell line
(no shell runs; write paths with forward slashes). They run in order and the first
failure stops the run. Never wrap the steps in `bash -c`: on Windows a bare `bash`
can resolve to the System32 WSL launcher instead of Git Bash, and `run` refuses it
(observation 0346).

A missing tool is not a pass. When a passing run's log says a check was skipped or
not run because its tool is missing, or a command was not found, no stamp is
written unless that check is named with `--excluded` (observation 0354). A count of
zero is not a skip: "0 skipped" and "missing none" in a summary line pass
(observation 0546).

A repo with no CI (no tracked `.github/workflows/*.yml` and no `ci-local` or
`ci_local` script): `--no-ci` runs the gate's own baseline instead of improvised
steps (observation 0455). The baseline reads the commits since the upstream (or
origin's default branch; the whole tree when there is neither): `git diff --check`
(whitespace errors, conflict markers), every changed `.json` file parses, and no
added line holds a token-shaped value. The stamp records `no_ci: true`. `--no-ci`
is refused in a repo that has CI: run that CI.

A step's program path that is relative (`.venv/Scripts/python.exe`) is resolved
against `--repo`, and on Windows a bare name gets PATHEXT (`godot` finds
`godot.cmd`). A program that still cannot be started fails the run with exit 127
and no stamp, not a traceback (observation 0454).

A check known to flake: `--runs N` repeats the whole step list N times and stamps
only when every run passes. One lucky pass is not a verdict (observation 0353).
Stdlib only; no window opens.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hooklib as hl  # noqa: E402

TAIL_LINES = 20
# A log line that says a check did not run because its tool is missing.
MISSING_TOOL = re.compile(r"(?im)^.*(?:command not found|is not recognized as an internal or external command"
                          r"|\b(?:skip\w*|not run)\b.*\b(?:not installed|not found|missing)\b).*$")
# A count of zero names the thing it counts: "0 skipped", "0 tests skipped", "missing none",
# "skipped: 0". Such a phrase is struck before a line is read as a skip (observation 0546).
ZERO_COUNT = re.compile(r"(?i)\b0\s+(?:\w+\s+)?(?:skip\w*|not run|missing)\b"
                        r"|\b(?:skip\w*|not run|missing)\s*[:=]?\s*(?:none|0)\b(?![.\d])")
# A repo's own CI: a tracked workflow or a ci-local script (observation 0455).
HAS_CI = re.compile(r"(?i)^\.github/workflows/[^/]+\.ya?ml$|(?:^|/)ci[-_]local(?:\.[a-z0-9]+)?$")
# A token-shaped value on an added line (the prefix shapes of hooklib's mask; no URL rule, which
# would flag ssh://git@ in docs).
TOKEN_SHAPE = re.compile(r"(?<![A-Za-z0-9])(?:ghp_|gho_|ghs_|ghu_|ghr_|github_pat_|glpat-|sk-|xox[abprs]-|AKIA)"
                         r"[A-Za-z0-9_\-]{16,}")
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


def missing_tools(text: str) -> list[str]:
    """Log lines that say a check did not run, zero counts struck first (observation 0546)."""
    return [m.group(0).strip() for m in MISSING_TOOL.finditer(text)
            if MISSING_TOOL.search(ZERO_COUNT.sub("", m.group(0)))]


def resolve_exe(argv0: str, repo: str) -> str:
    """The program to start: a relative path joined to --repo, a bare name given PATHEXT on Windows
    (observation 0454). Anything not found is returned as given."""
    if os.path.isabs(argv0):
        return argv0
    if os.path.dirname(argv0):
        cand = os.path.abspath(os.path.join(repo, argv0))
        return (shutil.which(cand) or cand) if os.path.exists(cand) or shutil.which(cand) else argv0
    return (shutil.which(argv0) or argv0) if os.name == "nt" else argv0


def ci_files(repo: str) -> list[str]:
    """Tracked files that make up the repo's own CI (observation 0455)."""
    out = hl.run_git(repo, "ls-files")
    return [f for f in out.splitlines() if HAS_CI.search(f)]


def baseline(repo: str) -> int:
    """The --no-ci checks over the commits since the upstream (observation 0455). 0 pass, 1 fail."""
    base = ""
    for ref in ("@{upstream}", "refs/remotes/origin/HEAD", "refs/remotes/origin/main"):
        try:
            base = hl.run_git(repo, "merge-base", "HEAD", ref)
        except RuntimeError:  # no such ref, or no common history
            continue
        if base:
            break
    span = f"{base[:12]}..HEAD" if base else "the whole tree"
    base = base or EMPTY_TREE
    failed = []
    p = subprocess.run(["git", "-C", repo, "diff", "--check", base, "HEAD"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL, creationflags=hl.NO_WINDOW)
    if p.returncode != 0:
        failed.append("git diff --check:\n" + (p.stdout + p.stderr).strip())
    names = [n for n in hl.run_git(repo, "diff", "--name-only", "--diff-filter=AM", base, "HEAD").splitlines() if n]
    bad_json = []
    for n in (n for n in names if n.lower().endswith(".json")):
        body = subprocess.run(["git", "-C", repo, "show", f"HEAD:{n}"], capture_output=True,
                              stdin=subprocess.DEVNULL, creationflags=hl.NO_WINDOW).stdout
        try:
            json.loads(body.decode("utf-8-sig"))
        except (ValueError, UnicodeDecodeError) as exc:
            bad_json.append(f"{n}: {exc}")
    if bad_json:
        failed.append("JSON that does not parse:\n" + "\n".join(bad_json))
    diff = subprocess.run(["git", "-C", repo, "diff", "--no-color", "-U0", base, "HEAD"], capture_output=True,
                          text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL,
                          creationflags=hl.NO_WINDOW).stdout
    tokens = sum(1 for line in diff.splitlines()
                 if line.startswith("+") and not line.startswith("+++") and TOKEN_SHAPE.search(line))
    if tokens:
        failed.append(f"{tokens} added line(s) hold a token-shaped value (values not printed)")
    for f in failed:
        print(f"no-CI baseline FAILED: {f}")
    n_json = sum(1 for n in names if n.lower().endswith(".json"))
    print(f"no-CI baseline: {len(names)} changed file(s) over {span}; whitespace and conflict markers, "
          f"{n_json} JSON file(s), token shapes: " + ("FAILED" if failed else "OK"))
    return 1 if failed else 0


def wsl_shim(argv0: str) -> str:
    """The resolved path when a bare shell name would start the Windows WSL launcher, else ""."""
    if os.name != "nt" or os.path.splitext(os.path.basename(argv0))[0].lower() not in ("bash", "sh", "wsl"):
        return ""
    found = shutil.which(argv0) or ""
    low = found.lower().replace("/", "\\")
    return found if ("\\system32\\" in low or "\\windowsapps\\" in low) else ""


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="ci_stamp.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--repo", default=".")
    r.add_argument("--excluded", action="append", default=[], metavar="NAME: REASON",
                   help="a check the local run skips on purpose; repeat; recorded in the stamp")
    r.add_argument("--step", action="append", default=[], metavar="COMMAND LINE",
                   help="one CI step, split like a shell line (no shell); repeat, in order")
    r.add_argument("--runs", type=int, default=1,
                   help="run every step N times; stamp only when every run passes (a flaky check)")
    r.add_argument("--workflow", metavar="FILE",
                   help="the CI workflow this run stands in for; its `run:` steps are counted into the stamp")
    r.add_argument("--covers", metavar="N|all",
                   help="how many of the workflow's run: steps this run covers (default: the step count; "
                        "`all` for a runner generated from the workflow)")
    r.add_argument("--quiet", action="store_true",
                   help="print the one-line verdict only; the full log stays in ci-last.log")
    r.add_argument("command", nargs=argparse.REMAINDER)
    r.add_argument("--no-ci", action="store_true",
                   help="the repo has no CI: run the gate's baseline checks instead of steps (observation 0455)")
    s = sub.add_parser("show")
    s.add_argument("--repo", default=".")
    b = sub.add_parser("baseline", help="the --no-ci checks alone; writes no stamp")
    b.add_argument("--repo", default=".")
    a = ap.parse_args(argv)
    if a.cmd == "baseline":
        return baseline(a.repo)
    d = os.path.join(hl.run_git(a.repo, "rev-parse", "--absolute-git-dir"), "gatewarden")
    path = os.path.join(d, "ci-pass.json")
    if a.cmd == "show":
        try:
            print(open(path, encoding="utf-8").read())
            return 0
        except OSError:
            print("no CI stamp", file=sys.stderr)
            return 1
    cmd = a.command[1:] if a.command[:1] == ["--"] else a.command
    steps = ([cmd] if cmd else []) + [shlex.split(s) for s in a.step]
    steps = [s for s in steps if s]
    if a.no_ci:
        if steps:
            print("ci_stamp: --no-ci runs the gate's own baseline; give no steps with it", file=sys.stderr)
            return 2
        found = ci_files(a.repo)
        if found:
            print(f"ci_stamp: --no-ci refused: this repo has CI ({', '.join(found[:3])}); run that CI",
                  file=sys.stderr)
            return 2
        steps = [[sys.executable, os.path.abspath(__file__), "baseline", "--repo", os.path.abspath(a.repo)]]
    if not steps:
        print("ci_stamp: give the CI command after --, or each step with --step", file=sys.stderr)
        return 2
    for s in steps:
        shim = wsl_shim(s[0])
        if shim:
            print(f"ci_stamp: `{s[0]}` resolves to {shim}, the WSL launcher, not Git Bash. Give each CI "
                  "step with --step \"<command>\" (no shell wrapper), or name Git Bash by its full path.",
                  file=sys.stderr)
            return 2
    try:
        workflow = workflow_cover(a.repo, a.workflow, a.covers, len(steps))
    except (OSError, ValueError) as exc:
        print(f"ci_stamp: --workflow/--covers could not be read ({exc})", file=sys.stderr)
        return 2
    if hl.run_git(a.repo, "status", "--porcelain", "--untracked-files=no"):
        print("ci_stamp: the tree has uncommitted changes; commit first so the stamp names a commit",
              file=sys.stderr)
        return 2
    head = hl.run_git(a.repo, "rev-parse", "HEAD")
    started = time.time()
    os.makedirs(d, exist_ok=True)
    log = os.path.join(d, "ci-last.log")
    # A no-window child that inherits an invalid stdin handle dies with WinError 6 in any
    # grandchild it spawns, so stdin is always the null device. PYTHONUTF8=1 stops Windows'
    # cp1252 default from failing a UTF-8 read that passes on a Linux runner.
    env = dict(os.environ, PYTHONUTF8="1")
    runs = max(1, a.runs)
    returncode = 0
    with open(log, "wb") as out:
        for n in range(runs):
            for s in steps:
                if len(steps) > 1 or runs > 1:
                    out.write(f"== ci_stamp: run {n + 1}/{runs}: {' '.join(s)}\n".encode())
                    out.flush()
                try:
                    returncode = subprocess.run([resolve_exe(s[0], a.repo), *s[1:]], cwd=a.repo,
                                                stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT,
                                                env=env, creationflags=hl.NO_WINDOW).returncode
                except OSError as exc:
                    out.write(f"ci_stamp: could not start `{s[0]}` ({exc})\n".encode())
                    out.flush()
                    returncode = 127
                if returncode != 0:
                    break
            if returncode != 0:
                break
    text = open(log, "rb").read().decode("utf-8", errors="replace")
    if not a.quiet:
        _echo(sys.stdout, text)
    if returncode != 0:
        if a.quiet:
            print(f"ci_stamp: CI failed (exit {returncode}); no stamp written; log: {log}", file=sys.stderr)
            return returncode
        tail = "\n".join(text.rstrip("\n").splitlines()[-TAIL_LINES:])
        _echo(sys.stderr, f"ci_stamp: last {TAIL_LINES} lines of the run (full log: {log}):\n{tail}\n")
        print(f"ci_stamp: CI failed (exit {returncode}); no stamp written", file=sys.stderr)
        return returncode
    if hl.run_git(a.repo, "rev-parse", "HEAD") != head:
        print("ci_stamp: HEAD moved during the run; no stamp written", file=sys.stderr)
        return 2
    missing = missing_tools(text)
    if missing and not a.excluded:
        _echo(sys.stderr, "ci_stamp: the run exited 0, but its log says a check did not run:\n  "
              + "\n  ".join(missing[:5]) + "\nA skipped check is not a pass; no stamp written. Install the "
              "tool, or name the check with --excluded \"NAME: REASON\" so the stamp says partial.\n")
        return 3
    stamp = {
        "head": head, "passed_at": time.time(), "seconds": round(time.time() - started, 1),
        "command_sha256": hashlib.sha256(" && ".join(" ".join(s) for s in steps).encode()).hexdigest()[:16],
        "runs": runs, "excluded": a.excluded, "partial": bool(a.excluded)}
    if a.no_ci:
        stamp["no_ci"] = True
    if workflow:
        stamp.update(workflow=workflow[0], workflow_steps=workflow[1], steps_covered=workflow[2])
    hl.write_json_atomic(path, stamp)
    cover = f"; covers {workflow[2]} of {workflow[1]} run: steps in {workflow[0]}" if workflow else ""
    print(f"ci_stamp: {'no-CI baseline' if a.no_ci else 'CI'} passed for {head[:12]}" + (f" ({runs} runs)" if runs > 1 else "") + "; stamp written"
          + cover + (" (PARTIAL: " + "; ".join(a.excluded) + ")" if a.quiet and a.excluded else ""))
    if not a.quiet:
        for item in a.excluded:
            print(f"ci_stamp: PARTIAL stamp, not run locally: {item}")
    return 0


RUN_STEP = re.compile(r"^\s*(?:-\s+)?run\s*:", re.M)


def workflow_cover(repo: str, wf: str | None, covers: str | None, n_steps: int) -> tuple | None:
    """(workflow path as given, its run: step count, steps this run covers), or None without
    --workflow (B6, observation 0367). Raises ValueError for a workflow file that cannot be read."""
    if not wf:
        return None
    full = wf if os.path.isabs(wf) else os.path.join(repo, wf)
    with open(full, encoding="utf-8", errors="replace") as fh:
        total = len(RUN_STEP.findall(fh.read()))
    if covers is None:
        covered = n_steps
    elif covers.strip().lower() == "all":
        covered = total
    else:
        covered = int(covers)
    return wf.replace("\\", "/"), total, covered


def _echo(stream, text: str) -> None:
    """Write text without failing on a console code page that cannot encode it. Token shapes and
    URL credentials are masked: the echo reaches the transcript (K7-4-12); ci-last.log keeps the raw run."""
    text = hl.mask(text)
    buf = getattr(stream, "buffer", None)
    if buf is not None:
        stream.flush()
        buf.write(text.encode(stream.encoding or "utf-8", errors="replace"))
        buf.flush()
    else:
        stream.write(text)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
