#!/usr/bin/env python3
"""Tests for work_guard.py (observations 0563, 0632, 0671, 0711, 0691 via 0725; controls from 0392).

Most cases call work_guard.check() in-process: one import, no Python spawn per case (observation 0725:
per-case process spawns dominate the hook suites on Windows). A few run the hook as Claude Code does,
to prove the exit code and the hard mode.

Run: python -m unittest test_hooks_work_guard
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _scratch import force_rmtree

HERE = Path(__file__).resolve().parent
HOOKS = HERE / "hooks"
sys.path.insert(0, str(HOOKS))
import work_guard as wg  # noqa: E402

PY = sys.executable
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def git(cwd, *args):
    return subprocess.run(["git", "-c", "user.name=gatewarden-test", "-c", "user.email=gatewarden-test",
                           "-c", "commit.gpgsign=false", "-c", "core.hooksPath=", *args], cwd=cwd,
                          capture_output=True, text=True, check=True, creationflags=NO_WINDOW,
                          stdin=subprocess.DEVNULL).stdout.strip()


def event(cmd: str, cwd: str, tool: str = "Bash", session: str = "s1") -> dict:
    return {"session_id": session, "hook_event_name": "PreToolUse", "tool_name": tool,
            "tool_input": {"command": cmd}, "cwd": cwd}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="gw-work-")
        self.state = os.path.join(self.tmp, "state")
        self._env = os.environ.get("GATEWARDEN_STATE")
        os.environ["GATEWARDEN_STATE"] = self.state
        self.repo = os.path.join(self.tmp, "repo")
        os.makedirs(self.repo)
        git(self.repo, "init", "-b", "main")
        Path(self.repo, "a.txt").write_text("0\n")
        git(self.repo, "add", "a.txt")
        git(self.repo, "commit", "-m", "base")

    def tearDown(self):
        if self._env is None:
            os.environ.pop("GATEWARDEN_STATE", None)
        else:
            os.environ["GATEWARDEN_STATE"] = self._env
        force_rmtree(self.tmp)

    def rule(self, cmd, tool="Bash", session="s1", cwd=None):
        hit = wg.check(event(cmd, cwd or self.repo, tool, session))
        return hit.rule if hit else None

    def refused(self, rule, cmds, tool="Bash", cwd=None):
        for cmd in cmds:
            self.assertEqual(self.rule(cmd, tool, cwd=cwd), rule, f"{tool}: {cmd!r}")

    def passes(self, cmds, tool="Bash", cwd=None):
        for cmd in cmds:
            self.assertIsNone(self.rule(cmd, tool, cwd=cwd), f"{tool}: {cmd!r}")

    def add_worktree(self):
        git(self.repo, "worktree", "add", "--detach", os.path.join(self.tmp, "wt"))


class StashTests(Base):  # observations 0559, 0563
    def test_one_worktree_stash_passes(self):  # positive control
        self.passes(["git stash", "git stash pop", "git stash -u"])

    def test_shared_checkout_stash_is_refused(self):
        self.add_worktree()
        self.refused("work_guard.stash", ["git stash", "git stash pop", "git stash -u", "git stash push -m wip",
                                          "git stash drop", "git status && git stash apply",
                                          f'git -C "{self.repo}" stash', f'cd "{self.repo}" && git stash',
                                          "bash <<'EOF'\ngit stash\nEOF"])
        self.refused("work_guard.stash", ["git stash", f'Set-Location "{self.repo}"; git stash'], tool="PowerShell")
        self.refused("work_guard.stash", [f'git -C "{self.repo}" stash'], cwd=self.tmp)

    def test_stash_reads_and_text_pass(self):
        self.add_worktree()
        self.passes(["git stash list", "git stash show -p", 'git commit -m "never git stash here"',
                     "echo 'git stash'", "grep -n \"git stash\" notes.md",
                     "cat > notes.md <<'EOF'\ngit stash\nEOF"])


class SedTests(Base):  # observation 0632
    def test_in_place_is_refused(self):
        self.refused("work_guard.sed_inplace", [
            "sed -i 's/a/b/' a.txt", "sed -Ei 's/a/b/' a.txt", "sed -i.bak 's/a/b/' a.txt",
            "sed --in-place=.b 's/a/b/' a.txt", "sed -n -i 's/a/b/' a.txt",
            "find . -name '*.md' -exec sed -i 's/a/b/' {} +", "git ls-files | xargs sed -i 's/a/b/'",
            "python x.py && sed -i 's/a/b/' a.txt && python -m unittest"])

    def test_other_sed_and_text_pass(self):
        self.passes(["sed -n '1,5p' a.txt", "sed -e 's/i/x/' a.txt > b.txt", "sed -f fix.sed a.txt",
                     "sed -ne 's/i/x/p' a.txt", "grep -n \"sed -i\" notes.md",
                     'git commit -m "no sed -i here"', "cat > n.md <<'EOF'\nsed -i 's/a/b/' x\nEOF"])


class NoVerifyTests(Base):  # observation 0711
    def test_hook_skips_are_refused(self):
        cmds = ["git commit --no-verify -m x", "git commit -n -m x", "git commit -anm x",
                "git commit --no-veri -m x", "git push --no-verify origin main",
                "git -c core.hooksPath=/dev/null commit -m x", "git merge --no-verify feat",
                "git add -A && git commit -q --no-verify -m wip"]
        self.refused("work_guard.no_verify", cmds)
        self.refused("work_guard.no_verify", ["git commit --no-verify -m x"], tool="PowerShell")

    def test_lookalikes_pass(self):
        self.passes(['git commit -m "-n is banned"', "git push -n origin main", 'git commit -am "x --no-verify"',
                     "git log -n 3", "git commit -F msg.txt", "git commit -C HEAD", "git commit -m n",
                     "git commit -m x -- -n", "git commit -q -m x"])

    def test_owner_word_lets_one_skip_through_until_it_expires(self):
        gate = str(HOOKS / "work_guard.py")
        run = lambda *a: subprocess.run([PY, gate, "owner-ok", "--repo", self.repo, *a], capture_output=True,
                                        text=True, creationflags=NO_WINDOW, stdin=subprocess.DEVNULL)
        self.assertNotEqual(run("--said", " ").returncode, 0)
        self.assertEqual(run("--said", "skip the hook this once").returncode, 0)
        self.passes(["git commit --no-verify -m x"])
        self.assertEqual(run("--said", "skip the hook this once", "--ttl", "-1").returncode, 0)
        self.refused("work_guard.no_verify", ["git commit --no-verify -m x"])


class BranchMovedTests(Base):  # observation 0671
    def test_branch_switched_by_another_session_is_refused(self):
        self.assertIsNone(self.rule("git commit -m one"))  # learns main
        git(self.repo, "checkout", "-q", "-b", "other-session")  # not this session's call
        self.assertEqual(self.rule("git commit -m two"), "work_guard.branch_moved")
        self.assertEqual(self.rule("git commit -m two"), "work_guard.branch_moved")  # still, until it acts
        self.assertIsNone(self.rule("git commit -m two", session="s2"))  # a session that never saw main

    def test_own_switch_relearns(self):
        self.assertIsNone(self.rule("git commit -m one"))
        git(self.repo, "checkout", "-q", "-b", "feat")
        self.assertIsNone(self.rule("git switch feat"))  # this session's own switch clears the record
        self.assertIsNone(self.rule("git commit -m two"))
        git(self.repo, "checkout", "-q", "main")
        self.assertIsNone(self.rule("git switch -c feat2 && git commit -m three"))  # same line moves it

    def test_no_session_id_is_not_tracked(self):
        self.assertIsNone(self.rule("git commit -m one", session=""))
        git(self.repo, "checkout", "-q", "-b", "x")
        self.assertIsNone(self.rule("git commit -m one", session=""))


class MergeChainTests(Base):  # observation 0691, carried by 0725
    def test_merge_after_checks_read_on_one_line_is_refused(self):
        self.refused("work_guard.merge_chain", [
            "gh pr checks 5 && gh pr merge 5 --merge", "gh run view 1; gh pr merge 5 --merge",
            "gh pr view 5 --json statusCheckRollup && gh pr merge 5 --merge",
            "gh api repos/o/r/commits/abc/check-runs | head; gh pr merge 5 --squash"])
        self.refused("work_guard.merge_chain", ["gh pr checks 5; gh pr merge 5 --merge"], tool="PowerShell")

    def test_separate_calls_pass(self):
        self.passes(["gh pr merge 5 --merge", "gh pr checks 5", "gh pr view 5 --json title && gh pr merge 5 --merge",
                     "gh pr merge 5 --merge && gh run list --limit 1"])


class HookProcessTests(Base):
    def hook(self, ev, env=None, raw=None):
        full = {k: v for k, v in os.environ.items() if not k.startswith("GATEWARDEN_")}
        full.update({"GATEWARDEN_STATE": self.state, **(env or {})})
        p = subprocess.run([PY, str(HOOKS / "work_guard.py")], input=raw if raw is not None else json.dumps(ev),
                           capture_output=True, text=True, encoding="utf-8", env=full, timeout=60,
                           creationflags=NO_WINDOW)
        return p.returncode, p.stderr

    def test_refusal_is_hard_in_watch_mode(self):
        self.add_worktree()
        code, err = self.hook(event("git stash", self.repo), env={"GATEWARDEN_MODE": "watch"})
        self.assertEqual(code, 2, err)
        self.assertIn("work guard", err)
        self.assertIn("worktree add --detach", err)

    def test_ordinary_and_unreadable_pass(self):
        self.assertEqual(self.hook(event("git status", self.repo))[0], 0)
        self.assertEqual(self.hook({}, raw="not json")[0], 0)
        self.assertEqual(self.hook({"tool_name": "Read", "tool_input": {"file_path": "x"}})[0], 0)


if __name__ == "__main__":
    unittest.main()
