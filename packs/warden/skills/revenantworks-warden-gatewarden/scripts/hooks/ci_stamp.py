#!/usr/bin/env python3
"""ci_stamp.py: run a repo's local CI steps and stamp HEAD when they pass.

  python ci_stamp.py run --repo <dir> [--excluded "NAME: REASON" ...] [--runs N] -- <command> [args...]
  python ci_stamp.py run --repo <dir> --step "<step 1>" --step "<step 2>" ...
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
written unless that check is named with `--excluded` (observation 0354).

A check known to flake: `--runs N` repeats the whole step list N times and stamps
only when every run passes. One lucky pass is not a verdict (observation 0353).
Stdlib only; no window opens.
"""
from __future__ import annotations

import argparse
import hashlib
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
    r.add_argument("command", nargs=argparse.REMAINDER)
    s = sub.add_parser("show")
    s.add_argument("--repo", default=".")
    a = ap.parse_args(argv)
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
                returncode = subprocess.run(s, cwd=a.repo, stdin=subprocess.DEVNULL, stdout=out,
                                            stderr=subprocess.STDOUT, env=env,
                                            creationflags=hl.NO_WINDOW).returncode
                if returncode != 0:
                    break
            if returncode != 0:
                break
    text = open(log, "rb").read().decode("utf-8", errors="replace")
    _echo(sys.stdout, text)
    if returncode != 0:
        tail = "\n".join(text.rstrip("\n").splitlines()[-TAIL_LINES:])
        _echo(sys.stderr, f"ci_stamp: last {TAIL_LINES} lines of the run (full log: {log}):\n{tail}\n")
        print(f"ci_stamp: CI failed (exit {returncode}); no stamp written", file=sys.stderr)
        return returncode
    if hl.run_git(a.repo, "rev-parse", "HEAD") != head:
        print("ci_stamp: HEAD moved during the run; no stamp written", file=sys.stderr)
        return 2
    missing = [m.group(0).strip() for m in MISSING_TOOL.finditer(text)]
    if missing and not a.excluded:
        _echo(sys.stderr, "ci_stamp: the run exited 0, but its log says a check did not run:\n  "
              + "\n  ".join(missing[:5]) + "\nA skipped check is not a pass; no stamp written. Install the "
              "tool, or name the check with --excluded \"NAME: REASON\" so the stamp says partial.\n")
        return 3
    hl.write_json_atomic(path, {
        "head": head, "passed_at": time.time(), "seconds": round(time.time() - started, 1),
        "command_sha256": hashlib.sha256(" && ".join(" ".join(s) for s in steps).encode()).hexdigest()[:16],
        "runs": runs, "excluded": a.excluded, "partial": bool(a.excluded)})
    print(f"ci_stamp: CI passed for {head[:12]}" + (f" ({runs} runs)" if runs > 1 else "") + "; stamp written")
    for item in a.excluded:
        print(f"ci_stamp: PARTIAL stamp, not run locally: {item}")
    return 0


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
