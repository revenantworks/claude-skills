#!/usr/bin/env python3
"""push_gate.public_branch: a branch carrying commits not on the remote's main is not pushed to a
public repository (observation 0441; owner decision 2026-10-17).

Fixture repos only, no network: the remote's URL reads as a GitHub repository, and a git
`insteadOf` rewrite sends every git call to a local bare repo. The visibility lookup is stubbed: a
seeded cache file in the test state folder, or a stub `gh` named by GATEWARDEN_GH.

Run: python -m unittest test_hooks_public_branch
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOOKS = HERE / "hooks"
PY = sys.executable
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
SLUG = "acme/widgets"
URL = f"https://github.com/{SLUG}.git"
RULE = "push_gate.public_branch"

sys.path.insert(0, str(HOOKS))
import push_gate  # noqa: E402


def git(cwd, *args):
    return subprocess.run(["git", "-c", "user.name=gatewarden-test", "-c", "user.email=gatewarden-test",
                           "-c", "commit.gpgsign=false", *args], cwd=cwd, capture_output=True, text=True,
                          check=True, creationflags=NO_WINDOW, stdin=subprocess.DEVNULL).stdout.strip()


def commit(work, name, text):
    Path(work, name).write_text(text)
    git(work, "add", name)
    git(work, "commit", "-m", f"add {name}")


class PublicBranchBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="gw-public-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.state = os.path.join(self.tmp, "state")
        os.makedirs(self.state)
        self.remote = os.path.join(self.tmp, "remote.git")
        self.work = os.path.join(self.tmp, "work")
        git(self.tmp, "init", "--bare", "-b", "main", self.remote)
        git(self.tmp, "clone", self.remote, self.work)
        git(self.work, "checkout", "-b", "main")
        commit(self.work, "a.txt", "0\n")
        git(self.work, "push", "-u", "origin", "main")
        # The remote reads as a GitHub repo; insteadOf keeps every git call local.
        git(self.work, "config", "remote.origin.url", URL)
        git(self.work, "config", f"url.{Path(self.remote).as_posix()}.insteadOf", URL)
        git(self.work, "fetch", "origin")
        self.mode = "guard"
        self.gh = os.path.join(self.tmp, "no-such-gh")  # a lookup that fails unless a test stubs one

    def env(self):
        return {"GATEWARDEN_STATE": self.state, "GATEWARDEN_MODE": self.mode, "GATEWARDEN_GH": self.gh}

    def run_hook(self, cmd):
        full = {k: v for k, v in os.environ.items() if not k.startswith("GATEWARDEN_")}
        full.update(self.env())
        ev = {"session_id": "s1", "hook_event_name": "PreToolUse", "tool_name": "Bash",
              "tool_input": {"command": cmd}, "cwd": self.work}
        p = subprocess.run([PY, str(HOOKS / "push_gate.py")], input=json.dumps(ev), capture_output=True,
                           text=True, encoding="utf-8", env=full, timeout=60, creationflags=NO_WINDOW)
        return p.returncode, p.stdout, p.stderr

    def seed(self, private, age=0.0):
        with open(os.path.join(self.state, "repo-visibility.json"), "w", encoding="utf-8") as fh:
            json.dump({f"github.com/{SLUG}": {"private": private, "checked_at": time.time() - age}}, fh)

    def cache(self):
        with open(os.path.join(self.state, "repo-visibility.json"), encoding="utf-8") as fh:
            return json.load(fh)

    def stub_gh(self, answer):
        """A stub gh that records its arguments and prints `answer` (true/false)."""
        script = os.path.join(self.tmp, "gh_stub.py")
        self.gh_log = os.path.join(self.tmp, "gh-called.txt")
        Path(script).write_text(
            "import sys\n"
            f"open({self.gh_log!r}, 'a').write(' '.join(sys.argv[1:]) + '\\n')\n"
            f"print({answer!r})\n")
        self.gh = json.dumps([PY, script])

    def ready(self, n):
        """A live intent and a CI stamp for HEAD, so only the public-branch rule can refuse."""
        p = subprocess.run([PY, str(HOOKS / "push_gate.py"), "intend", "--repo", self.work, "--max", str(n)],
                           capture_output=True, text=True, creationflags=NO_WINDOW, stdin=subprocess.DEVNULL)
        self.assertEqual(p.returncode, 0, p.stderr)
        p = subprocess.run([PY, str(HOOKS / "ci_stamp.py"), "run", "--repo", self.work, "--", PY, "-c",
                            "raise SystemExit(0)"], capture_output=True, text=True, creationflags=NO_WINDOW,
                           stdin=subprocess.DEVNULL)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def feature(self, n=2):
        git(self.work, "checkout", "-b", "feature")
        for i in range(n):
            commit(self.work, f"f{i}.txt", f"{i}\n")

    def events(self):
        try:
            with open(os.path.join(self.state, "events.jsonl"), encoding="utf-8") as fh:
                return [json.loads(x) for x in fh if x.strip()]
        except OSError:
            return []


class PublicBranchGuardTests(PublicBranchBase):
    def test_public_branch_with_commits_off_main_is_refused(self):
        self.seed(private=False)
        self.feature(2)
        self.ready(2)
        code, _, err = self.run_hook("git push -u origin feature")
        self.assertEqual(code, 2, err)
        self.assertIn("feature", err)
        self.assertIn("2 commits not on origin/main", err)
        self.assertIn("public", err)
        self.assertIn("land", err.lower())
        self.assertIn("private remote", err)
        self.assertEqual([e["outcome"] for e in self.events() if e["rule"] == RULE], ["blocked"])

    def test_refused_before_the_intent_and_stamp_are_asked_for(self):
        self.seed(private=False)
        self.feature(1)
        code, _, err = self.run_hook("git push origin feature")
        self.assertEqual(code, 2)
        self.assertIn("1 commit not on origin/main", err)
        self.assertNotIn("intent", err.split("\n")[1])

    def test_main_itself_is_unchanged_on_a_public_repo(self):
        self.seed(private=False)
        commit(self.work, "b.txt", "1\n")
        self.ready(1)
        code, out, err = self.run_hook("git push origin main")
        self.assertEqual(code, 0, err)
        self.assertNotIn("public", out)

    def test_private_repo_branch_push_is_unchanged(self):
        self.seed(private=True)
        self.feature(2)
        self.ready(2)
        code, out, err = self.run_hook("git push -u origin feature")
        self.assertEqual(code, 0, err)
        self.assertNotIn("visibility unknown", out)

    def test_unknown_visibility_falls_back_and_says_so(self):
        self.feature(2)
        self.ready(2)
        code, out, err = self.run_hook("git push -u origin feature")
        self.assertEqual(code, 0, err)
        self.assertIn("visibility unknown", json.loads(out)["hookSpecificOutput"]["additionalContext"])

    def test_branch_with_nothing_off_main_passes(self):
        self.seed(private=False)
        git(self.work, "branch", "mirror-of-main")
        commit(self.work, "b.txt", "1\n")
        git(self.work, "push", "origin", "main")  # fixture step, outside the hook
        git(self.work, "checkout", "mirror-of-main")
        git(self.work, "merge", "--ff-only", "main")
        code, out, err = self.run_hook("git push origin mirror-of-main")
        self.assertEqual(code, 0, err)

    def test_branch_built_on_a_stale_local_main_is_refused(self):
        # 0441: the public main was fresh-started; the local main still holds the old history.
        self.seed(private=False)
        for i in range(3):
            commit(self.work, f"old{i}.txt", f"{i}\n")
        fresh = os.path.join(self.tmp, "fresh")
        git(self.tmp, "init", "-b", "main", fresh)
        commit(fresh, "new.txt", "new\n")
        git(fresh, "push", "--force", self.remote, "main")  # fixture step: the rewrite on the remote
        self.feature(1)
        self.ready(5)
        code, _, err = self.run_hook("git push -u origin feature")
        self.assertEqual(code, 2, err)
        self.assertIn("not in this clone", err)
        self.assertIn("feature", err)


class PublicBranchModeTests(PublicBranchBase):
    def test_watch_logs_and_lets_the_push_run(self):
        self.mode = "watch"
        self.seed(private=False)
        self.feature(2)
        self.ready(2)
        code, out, err = self.run_hook("git push -u origin feature")
        self.assertEqual(code, 0, err)
        self.assertNotIn("public", out)
        self.assertEqual([e["outcome"] for e in self.events() if e["rule"] == RULE], ["logged"])

    def test_nudge_tells_claude_and_lets_the_push_run(self):
        self.mode = "nudge"
        self.seed(private=False)
        self.feature(2)
        self.ready(2)
        code, out, err = self.run_hook("git push -u origin feature")
        self.assertEqual(code, 0, err)
        self.assertIn("2 commits not on origin/main", json.loads(out)["hookSpecificOutput"]["additionalContext"])
        self.assertEqual([e["outcome"] for e in self.events() if e["rule"] == RULE], ["nudged"])

    def test_rule_is_settable_by_the_review_tool(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith("GATEWARDEN_")}
        env["GATEWARDEN_STATE"] = self.state
        p = subprocess.run([PY, str(HOOKS / "warden_review.py"), "set", RULE, "guard"], capture_output=True,
                           text=True, env=env, creationflags=NO_WINDOW, stdin=subprocess.DEVNULL)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)


class VisibilityLookupTests(PublicBranchBase):
    def test_fresh_cache_makes_no_lookup(self):
        self.seed(private=False)
        self.stub_gh("true")
        self.feature(1)
        self.ready(1)
        code, _, _ = self.run_hook("git push origin feature")
        self.assertEqual(code, 2)
        self.assertFalse(os.path.exists(self.gh_log))

    def test_stale_cache_is_refreshed_by_one_read_only_call(self):
        self.seed(private=True, age=10 * 86400)
        self.stub_gh("false")
        self.feature(1)
        self.ready(1)
        code, _, err = self.run_hook("git push origin feature")
        self.assertEqual(code, 2, err)
        self.assertEqual(Path(self.gh_log).read_text().split(), ["api", f"repos/{SLUG}", "--jq", ".private"])
        self.assertIs(self.cache()[f"github.com/{SLUG}"]["private"], False)

    def test_failed_lookup_is_not_cached(self):
        self.stub_gh("not json")
        self.feature(1)
        self.ready(1)
        code, out, err = self.run_hook("git push origin feature")
        self.assertEqual(code, 0, err)
        self.assertIn("visibility unknown", out)
        self.assertFalse(os.path.exists(os.path.join(self.state, "repo-visibility.json")))

    def test_visibility_command_reads_the_cache(self):
        self.seed(private=False)
        env = {k: v for k, v in os.environ.items() if not k.startswith("GATEWARDEN_")}
        env.update(self.env())
        p = subprocess.run([PY, str(HOOKS / "push_gate.py"), "visibility", "--repo", self.work],
                           capture_output=True, text=True, env=env, creationflags=NO_WINDOW,
                           stdin=subprocess.DEVNULL)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn(f"{SLUG}: public", p.stdout)


class SlugTests(unittest.TestCase):
    def test_github_urls_name_the_repo(self):
        for url in ("https://github.com/Acme/Widgets.git", "https://github.com/acme/widgets",
                    "git@github.com:acme/widgets.git", "ssh://git@github.com/acme/widgets.git",
                    "https://token@github.com/acme/widgets.git/"):
            self.assertEqual(push_gate.github_slug(url), SLUG, url)

    def test_other_remotes_have_no_slug(self):
        for url in ("../repos/widgets.git", "/srv/git/widgets.git", "file:///srv/git/widgets.git", "https://gitlab.com/acme/widgets.git",
                    "https://github.com.evil.example/acme/widgets.git", ""):
            self.assertIsNone(push_gate.github_slug(url), url)


if __name__ == "__main__":
    unittest.main()
