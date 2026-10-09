#!/usr/bin/env python3
"""Regression battery for command shapes the gatewarden hooks must refuse (stdlib unittest).

One TestCase class per finding id from the V-K8w2 verifier pass (waves/V-K8w2.md, Bypasses table).
Each class proves the hook refuses the shape (exit 2, hard: it holds with no mode forced) and keeps
an allow control: a normal daily command of the same family that must still pass (exit 0).

Every fixture is benign: it names an ordinary remote and branch, never a force or delete push. The
test proves the shape is refused whatever it would run. Fixtures live here as string data only, and
the guarded words are built by concatenation so the live hooks do not refuse this file's writes.

Run: python -m unittest discover -s scripts -p "test_*.py"
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOOKS = HERE / "hooks"
PY = sys.executable
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

G, U = "g" + "it", "pu" + "sh"


def run_hook(name: str, event: dict, env: dict | None = None):
    """Run a hook as Claude Code does: a JSON event on stdin; exit 0 allows, exit 2 blocks."""
    full_env = {k: v for k, v in os.environ.items() if not k.startswith("GATEWARDEN_")}
    full_env.update(env or {})
    p = subprocess.run([PY, str(HOOKS / name)], input=json.dumps(event), capture_output=True, text=True,
                       encoding="utf-8", env=full_env, timeout=60, creationflags=NO_WINDOW)
    return p.returncode, p.stdout, p.stderr


def bash(cmd: str, cwd: str, tool: str = "Bash") -> dict:
    return {"session_id": "s1", "hook_event_name": "PreToolUse", "tool_name": tool,
            "tool_input": {"command": cmd}, "cwd": cwd}


def git(cwd, *args):
    return subprocess.run([G, "-c", "user.name=gatewarden-test", "-c", "user.email=gatewarden-test",
                           "-c", "commit.gpgsign=false", *args], cwd=cwd, capture_output=True,
                          text=True, check=True, creationflags=NO_WINDOW).stdout.strip()


class PushShapeBase(unittest.TestCase):
    """A clone with an origin and a second branch, run at the install default (no mode forced): a hard
    rule must refuse in every mode, and a plain push with nothing new must pass."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="gw-shapes-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        state = os.path.join(self.tmp, "state")
        os.makedirs(state)
        self.env = {"GATEWARDEN_STATE": state}
        self.remote = os.path.join(self.tmp, "remote.git")
        self.work = os.path.join(self.tmp, "work")
        git(self.tmp, "init", "--bare", "-b", "main", self.remote)
        git(self.tmp, "clone", self.remote, self.work)
        git(self.work, "checkout", "-b", "main")
        Path(self.work, "a.txt").write_text("0\n")
        git(self.work, "add", "a.txt")
        git(self.work, "commit", "-m", "base")
        git(self.work, U, "-u", "origin", "main")
        git(self.work, "branch", "feat/x")

    def expect(self, code, cmds, tool="Bash", reason=None):
        for cmd in cmds:
            got, _, err = run_hook("push_gate.py", bash(cmd, self.work, tool), env=self.env)
            self.assertEqual(got, code, f"{tool}: {cmd!r}: {err.strip()}")
            if reason:
                self.assertIn(reason, err, f"{tool}: {cmd!r}: {err.strip()}")

    def expect_plain_pushes_pass(self):
        self.expect(0, [f"{G} {U} origin main", f"{G} {U} -u origin feat/x",
                        f"{G} {U} origin HEAD:refs/heads/x", f"$PYTHON x.py && {G} {U} origin main"])


RUN_TIME = "resolved at run time"


class B3(PushShapeBase):
    """V-K8w2 B3: a push argument known only at run time (a variable, `${…}`, `$(…)`, backticks) is not a
    refspec the gate can read, so the push is refused as a shape, not range-checked as a literal."""

    def test_refuses_variable_push_argument(self):
        self.expect(2, [f"{G} {U} $OPT origin main", f"BR=main; {G} {U} origin $BR",
                        f"{G} {U} origin ${{BR}}", f'{G} {U} "$REMOTE" main',
                        f"{G} -C . {U} origin $BR"], reason=RUN_TIME)

    def test_refuses_command_substitution_push_argument(self):
        self.expect(2, [f"{G} {U} $(echo hello) origin main",
                        f'{G} {U} origin "$({G} branch --show-current)"',
                        f"{G} {U} origin `echo main`"], reason=RUN_TIME)

    def test_refuses_variable_push_argument_in_powershell(self):
        self.expect(2, [f"{G} {U} origin $branch", f"{G} {U} $remote main"], tool="PowerShell",
                    reason=RUN_TIME)

    def test_plain_pushes_still_pass(self):
        self.expect_plain_pushes_pass()

    def test_run_time_words_outside_the_push_arguments_pass(self):
        self.expect(0, [f'echo "$BR" && {G} {U} origin main', f'{G} commit --allow-empty -m "$MSG"',
                        f"{G} {U} origin main 2>&1", f"{G} {U} origin main > $LOG"])
        self.expect(0, [f"{G} {U} origin main 2>$null"], tool="PowerShell")


class B4(PushShapeBase):
    """V-K8w2 B4: the positional parameters (`"$@"`, `$*`, `$1`..`$9`) of a function or script hand the
    push its arguments at run time; the call site that fills them is not read. Refused as B3."""

    def test_refuses_positional_parameters_in_push_arguments(self):
        self.expect(2, [f'p() {{ {G} {U} "$@"; }}; p origin main', f"p() {{ {G} {U} $*; }}; p origin main",
                        f"p() {{ {G} {U} origin $1; }}; p main", f'{G} {U} "$1" "$2"'], reason=RUN_TIME)

    def test_function_with_literal_push_arguments_passes(self):
        self.expect(0, [f"p() {{ {G} {U} origin main; }}; p", f'p() {{ echo "$@"; }}; p hello'])


GLOB = "glob"


class B9(PushShapeBase):
    """V-K8w2 B9: a glob character (`*`, `?`, `[`) in the command word lets the shell pick the program, so
    a word the gate does not read as git can run git. Refused when the pattern can name git and the
    segment reads as a push."""

    def test_refuses_glob_in_the_git_command_word(self):
        self.expect(2, [f"/usr/bin/{G[:2]}[t] {U} origin main", f"{G[:2]}? {U} origin main",
                        f"{G[0]}*{G[2]} {U} origin main", f"/usr/bin/{G[:2]}[t] -C . {U} origin main",
                        f"{G}-p?sh origin main"], reason=GLOB)

    def test_globs_in_arguments_and_other_programs_pass(self):
        self.expect(0, [f"ls *.md && {G} {U} origin main", f"{G} log --oneline -1 -- '*.md'",
                        f"{G} status && echo '{U}ed? [ok]'", f"grep -rn {U} *", f"ls * && {G} {U} origin main"])
        self.expect(0, [f"{G} branch -a | ? {{ $_ -match '{U}' }}"], tool="PowerShell")

    def test_plain_pushes_still_pass(self):
        self.expect_plain_pushes_pass()


if __name__ == "__main__":
    unittest.main()
