"""release.py step 7 (observation 0618): annotated tags, main pushed by name, and success only after
origin is read back holding main and every tag at the release commit.

On 2026-11-04 four releases reached origin with no tags: the script made lightweight tags and pushed
with --follow-tags, which carries annotated tags only. Fixture repos only, a local bare remote.
"""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import release  # noqa: E402

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def git(cwd, *args):
    return subprocess.run(["git", "-c", "user.name=release-test", "-c", "user.email=release-test@users.noreply.github.com",
                           "-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false", *args], cwd=cwd,
                          capture_output=True, text=True, check=True, creationflags=NO_WINDOW,
                          stdin=subprocess.DEVNULL).stdout.strip()


class ReleaseTagTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="rel-tags-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.remote = self.tmp / "remote.git"
        self.work = self.tmp / "work"
        git(self.tmp, "init", "--bare", "-b", "main", str(self.remote))
        git(self.tmp, "clone", "-q", str(self.remote), str(self.work))
        git(self.work, "checkout", "-q", "-b", "main")
        for k, v in (("user.name", "release-test"), ("user.email", "release-test@users.noreply.github.com"),
                     ("tag.gpgsign", "false"), ("commit.gpgsign", "false"), ("core.hooksPath", "")):
            git(self.work, "config", k, v)
        (self.work / "a.txt").write_text("a\n")
        git(self.work, "add", "a.txt")
        git(self.work, "commit", "-q", "-m", "release: x")
        self.head = git(self.work, "rev-parse", "HEAD")

    def test_tags_are_annotated_and_reach_origin_at_the_release_commit(self):
        tags = ["foundation-v1.1.0", "scribe-v1.0.1"]
        release.make_tags(tags, cwd=self.work)
        for t in tags:
            self.assertEqual("tag", git(self.work, "cat-file", "-t", f"refs/tags/{t}"))
        release.push_release(tags, cwd=self.work)
        self.assertEqual({t: self.head for t in tags}, release.remote_tags(tags, cwd=self.work))
        self.assertEqual(self.head, git(self.remote, "rev-parse", "refs/heads/main"))

    def test_a_lightweight_tag_is_refused_not_reused(self):
        git(self.work, "tag", "warden-v1.1.0")
        with self.assertRaises(SystemExit) as cm:
            release.make_tags(["warden-v1.1.0"], cwd=self.work)
        self.assertIn("lightweight", str(cm.exception))

    def test_an_existing_tag_elsewhere_is_refused(self):
        git(self.work, "tag", "-a", "warden-v1.1.0", "-m", "x")
        (self.work / "b.txt").write_text("b\n")
        git(self.work, "add", "b.txt")
        git(self.work, "commit", "-q", "-m", "later")
        with self.assertRaises(SystemExit) as cm:
            release.make_tags(["warden-v1.1.0"], cwd=self.work)
        self.assertIn("not at HEAD", str(cm.exception))

    def test_push_only_from_main(self):
        git(self.work, "checkout", "-q", "-b", "side")
        release.make_tags(["localops-v1.0.1"], cwd=self.work)
        with self.assertRaises(SystemExit) as cm:
            release.push_release(["localops-v1.0.1"], cwd=self.work)
        self.assertIn("main by name", str(cm.exception))
        self.assertEqual({}, release.remote_tags(["localops-v1.0.1"], cwd=self.work))

    def test_a_tag_push_that_exits_zero_but_sends_nothing_fails_the_read_back(self):
        # The 2026-11-04 shape: the push "succeeded" and origin held no tag.
        from unittest import mock
        real = release.sh

        def silent_tag_push(*args, **kw):
            if args[:2] == ("git", "push") and any(a.startswith("refs/tags/") for a in args):
                return subprocess.CompletedProcess(list(args), 0, "", "")
            return real(*args, **kw)

        release.make_tags(["scribe-v1.0.1"], cwd=self.work)
        with mock.patch.object(release, "sh", silent_tag_push), self.assertRaises(SystemExit) as cm:
            release.push_release(["scribe-v1.0.1"], cwd=self.work)
        self.assertIn("does not hold scribe-v1.0.1", str(cm.exception))

    def test_each_tag_goes_in_its_own_push(self):
        # GitHub fires no tag event when more than three tags arrive in one push.
        from unittest import mock
        real, pushes = release.sh, []

        def record(*args, **kw):
            if args[:2] == ("git", "push"):
                pushes.append([a for a in args if a.startswith("refs/tags/")])
            return real(*args, **kw)

        tags = ["foundation-v1.1.0", "warden-v1.1.0", "localops-v1.0.1", "scribe-v1.0.1"]
        release.make_tags(tags, cwd=self.work)
        with mock.patch.object(release, "sh", record):
            release.push_release(tags, cwd=self.work)
        self.assertEqual([[]] + [[f"refs/tags/{t}"] for t in tags], pushes)

    def test_the_script_no_longer_uses_follow_tags_or_push_head(self):
        src = (Path(release.__file__)).read_text(encoding="utf-8")
        code = src.split('"""', 2)[2]  # past the module docstring
        self.assertNotIn('"--follow-tags"', code)
        self.assertNotIn('"origin", "HEAD"', code)
        self.assertNotIn('"--tags", quiet', code)


if __name__ == "__main__":
    unittest.main()
