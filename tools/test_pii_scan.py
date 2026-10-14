"""tools/pii_scan.py: the PII barrier behind .githooks/pre-commit and the pii-scan CI job.

Every value here is invented and assembled from pieces, so this file scans clean under the
rules it tests. Every run points the home folder at an empty temp folder and sets CI, so a
real names list and this machine's own names are never read.
"""
import atexit
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "tools" / "pii_scan.py"
HOOK = ROOT / ".githooks" / "pre-commit"
HOME = Path(tempfile.mkdtemp(prefix="pii-home-"))
atexit.register(shutil.rmtree, HOME, True)

BS = "\\"
FAKE_USER = "zq" + "testacct"
FAKE_HOME = "C:" + BS + "Users" + BS + FAKE_USER + BS + "notes.txt"
FAKE_DRIVE = "Q:" + BS + "Shelf" + BS + "x.txt"
SYSTEM_DRIVE = "C:" + BS + "Program Files" + BS + "Git"
FAKE_MAIL = "jane.q" + "@" + "corp-" + "mail.net"
NOREPLY = "1+" + "someone" + "@" + "users.noreply.github.com"
FAKE_TERM = "zorbl" + "axian"


def _env(**extra):
    env = {k: v for k, v in os.environ.items() if k != "WARDEN_NAMES_FILE"}
    env.update(HOME=str(HOME), USERPROFILE=str(HOME), CI="1")
    env.update(extra)
    return env


class PiiScan(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.repo = base / "repo"
        self.repo.mkdir()
        self.outside = base / "outside"
        self.outside.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "someone")
        self.git("config", "user.email", NOREPLY)

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.repo), *args], check=True,
                              capture_output=True, env=_env())

    def stage(self, name, text):
        p = self.repo / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        self.git("add", name)

    def scan(self, *args):
        r = subprocess.run([sys.executable, str(SCRIPT), "--repo", str(self.repo), *args],
                           capture_output=True, text=True, env=_env())
        return r.returncode, r.stdout + r.stderr

    def test_clean_staged_diff_passes(self):
        self.stage("a.md", "A plain line with " + SYSTEM_DRIVE + " and " + NOREPLY + ".\n")
        rc, out = self.scan("--staged")
        self.assertEqual(rc, 0, out)
        self.assertIn("0 hit(s)", out)

    def test_home_path_blocks_and_never_echoes(self):
        self.stage("a.md", "one\nsee " + FAKE_HOME + "\n")
        rc, out = self.scan("--staged")
        self.assertEqual(rc, 1, out)
        self.assertIn("a.md:2  user-folder", out)
        self.assertNotIn(FAKE_USER, out)

    def test_drive_path_blocks(self):
        self.stage("b.md", "path " + FAKE_DRIVE + "\n")
        rc, out = self.scan("--staged")
        self.assertEqual(rc, 1, out)
        self.assertIn("drive-path", out)
        self.assertNotIn("Shelf", out)

    def test_double_escaped_path_blocks(self):
        self.stage("c.json", '{"p": "' + FAKE_HOME.replace(BS, BS * 4) + '"}\n')
        rc, out = self.scan("--staged")
        self.assertEqual(rc, 1, out)
        self.assertIn("user-folder", out)

    def test_email_blocks_noreply_passes(self):
        self.stage("d.md", "mail " + FAKE_MAIL + "\n")
        rc, out = self.scan("--staged")
        self.assertEqual(rc, 1, out)
        self.assertIn("email-address", out)
        self.assertNotIn(FAKE_MAIL, out)

    def test_identity_blocks_a_personal_address(self):
        self.git("config", "user.email", FAKE_MAIL)
        self.stage("e.md", "clean\n")
        rc, out = self.scan("--staged")
        self.assertEqual(rc, 1, out)
        self.assertIn("author-email", out)
        self.assertNotIn(FAKE_MAIL, out)

    def test_names_list_runs_when_present(self):
        names = self.outside / "names.txt"
        names.write_text("# invented\n" + FAKE_TERM + "\n", encoding="utf-8")
        self.stage("f.md", "a note about " + FAKE_TERM + " here\n")
        rc, out = self.scan("--staged", "--names-file", str(names))
        self.assertEqual(rc, 1, out)
        self.assertIn("owner-name  entry #1", out)
        self.assertNotIn(FAKE_TERM, out)

    def test_no_names_list_is_a_note_not_a_failure(self):
        self.stage("g.md", "clean\n")
        rc, out = self.scan("--staged")
        self.assertEqual(rc, 0, out)
        self.assertIn("NOT-RUN", out)

    def test_policy_accepts_one_fixture_file(self):
        self.stage(".pii-scan.json", '{"accepted": [{"rule": "drive-path", "file": "fixture.py"}]}\n')
        self.stage("fixture.py", "P = '" + FAKE_DRIVE + "'\n")
        rc, out = self.scan("--staged")
        self.assertEqual(rc, 0, out)
        self.assertIn("1 accepted", out)

    def test_tree_and_identities(self):
        self.stage("h.md", "clean\n")
        self.git("commit", "-q", "-m", "init", "--no-verify")
        rc, out = self.scan("--tree", "--identities")
        self.assertEqual(rc, 0, out)
        (self.repo / "h.md").write_text("see " + FAKE_HOME + "\n", encoding="utf-8")
        self.git("add", "h.md")
        rc, out = self.scan("--tree")
        self.assertEqual(rc, 1, out)

    def arm(self):
        """Commit the real hook plus a shim that runs the real scanner on the hook's work tree."""
        shim = ("import os, runpy, sys\nsys.argv = [" + repr(str(SCRIPT)) + "] + sys.argv[1:] + "
                "['--repo', os.getcwd()]\nrunpy.run_path(" + repr(str(SCRIPT)) + ", run_name='__main__')\n")
        self.stage("tools/pii_scan.py", shim)
        (self.repo / ".githooks").mkdir()
        shutil.copy(HOOK, self.repo / ".githooks" / "pre-commit")
        self.git("add", ".githooks/pre-commit")
        self.git("commit", "-q", "-m", "arm")
        self.git("config", "core.hooksPath", ".githooks")

    def commit(self, where, env):
        return subprocess.run(["git", "-C", str(where), "commit", "-q", "-m", "x"],
                              capture_output=True, text=True, env=env)

    @unittest.skipUnless(shutil.which("sh"), "no POSIX shell")
    def test_hook_blocks_a_commit(self):
        self.arm()
        self.stage("i.md", "see " + FAKE_HOME + "\n")
        r = self.commit(self.repo, _env())
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("PII barrier blocked", r.stderr)
        self.assertNotIn(FAKE_USER, r.stdout + r.stderr)
        self.git("rm", "-q", "--cached", "i.md")
        self.stage("j.md", "clean\n")
        r = self.commit(self.repo, _env())
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    @unittest.skipUnless(shutil.which("sh"), "no POSIX shell")
    def test_hook_blocks_in_a_worktree_with_a_names_list(self):
        # core.hooksPath is the clone's config, so a worktree runs the same hook. The names list
        # sits outside every repo; inside a worktree hook it must still read as outside.
        names = self.outside / "names.txt"
        names.write_text(FAKE_TERM + "\n", encoding="utf-8")
        env = _env(WARDEN_NAMES_FILE=str(names))
        self.arm()
        wt = self.outside / "wt"
        self.git("worktree", "add", "-q", str(wt), "-b", "wt-branch")
        got = subprocess.run(["git", "-C", str(wt), "config", "--get", "core.hooksPath"],
                             capture_output=True, text=True).stdout.strip()
        self.assertEqual(got, ".githooks")
        (wt / "k.md").write_text("see " + FAKE_HOME + " and " + FAKE_TERM + "\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(wt), "add", "k.md"], check=True, env=env)
        r = self.commit(wt, env)
        out = r.stdout + r.stderr
        self.assertNotEqual(r.returncode, 0, out)
        self.assertIn("user-folder", out)
        self.assertIn("owner-name  entry #1", out)
        self.assertNotIn("NOT-RUN", out)
        self.assertNotIn(FAKE_TERM, out)
        subprocess.run(["git", "-C", str(wt), "rm", "-q", "--cached", "k.md"], check=True, env=env)
        (wt / "l.md").write_text("clean\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(wt), "add", "l.md"], check=True, env=env)
        r = self.commit(wt, env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
