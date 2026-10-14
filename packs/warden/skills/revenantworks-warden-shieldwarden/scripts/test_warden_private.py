"""Tests for warden_private.py. Run: python -m unittest test_warden_private (from scripts/).

Each test points the home folder (HOME and USERPROFILE) at a temp folder and clears the two
WARDEN_* variables, so the real private folder is never read or written. Every entry is invented,
and none may appear in the output.
"""
from __future__ import annotations

import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import warden_private as wp  # noqa: E402

ENTRY = "Zorblat" + " Quixfield"


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="wpv-"))
        self.home = self.tmp / "home"
        self.home.mkdir()
        env = {k: v for k, v in os.environ.items() if k not in ("WARDEN_NAMES_FILE", "WARDEN_IDENTITY_VALUES_FILE")}
        env.update(HOME=str(self.home), USERPROFILE=str(self.home))
        self.env = mock.patch.dict(os.environ, env, clear=True)
        self.env.start()

    def tearDown(self):
        self.env.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_main(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = wp.main(list(argv))
        self.assertNotIn(ENTRY, out.getvalue())
        self.assertNotIn(str(self.home), out.getvalue())
        return code, out.getvalue()


class Resolution(Base):
    def test_nothing_anywhere_names_the_setup_command(self):
        r = wp.resolve("names")
        self.assertFalse(r.ok)
        self.assertIsNone(r.path)
        self.assertIn("setup names", r.problem)

    def test_default_path_is_used_when_present(self):
        d = self.home / ".warden"
        d.mkdir()
        (d / "wordlist.txt").write_text(ENTRY + "\n", encoding="utf-8")
        r = wp.resolve("names")
        self.assertTrue(r.ok)
        self.assertEqual(r.source, "default")

    def test_env_beats_default_and_flag_beats_env(self):
        d = self.home / ".warden"
        d.mkdir()
        (d / "wordlist.txt").write_text("a\n", encoding="utf-8")
        other = self.tmp / "other.txt"
        other.write_text("b\n", encoding="utf-8")
        flag = self.tmp / "flag.txt"
        flag.write_text("c\n", encoding="utf-8")
        os.environ["WARDEN_NAMES_FILE"] = str(other)
        self.assertEqual(wp.resolve("names").source, "env")
        r = wp.resolve("names", str(flag))
        self.assertEqual((r.source, r.path), ("flag", flag))

    def test_named_file_missing_is_a_problem_not_a_fallback(self):
        r = wp.resolve("names", str(self.tmp / "nope.txt"))
        self.assertFalse(r.ok)
        self.assertIn("not found", r.problem)

    def test_file_inside_a_work_tree_is_refused(self):
        repo = self.tmp / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
        f = repo / "wordlist.txt"
        f.write_text(ENTRY + "\n", encoding="utf-8")
        r = wp.resolve("names", str(f))
        self.assertFalse(r.ok)
        self.assertIn("git work tree", r.problem)


class Commands(Base):
    def test_setup_writes_comment_lines_only_and_never_overwrites(self):
        code, out = self.run_main("setup", "names")
        self.assertEqual(code, 0, out)
        f = self.home / ".warden" / "wordlist.txt"
        lines = f.read_text(encoding="utf-8").splitlines()
        self.assertTrue(lines and all(ln.startswith("#") for ln in lines))
        self.assertIn("~", out)
        f.write_text(ENTRY + "\n", encoding="utf-8")
        code, out = self.run_main("setup", "names")
        self.assertEqual(code, 0)
        self.assertIn("already exists", out)
        self.assertEqual(f.read_text(encoding="utf-8"), ENTRY + "\n")

    def test_setup_elsewhere_prints_the_env_command(self):
        code, out = self.run_main("setup", "identity-values", "--path", str(self.home / "private" / "v.txt"))
        self.assertEqual(code, 0, out)
        self.assertIn("WARDEN_IDENTITY_VALUES_FILE", out)
        self.assertTrue((self.home / "private" / "v.txt").is_file())

    def test_setup_inside_a_repo_is_refused(self):
        repo = self.tmp / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
        code, out = self.run_main("setup", "names", "--path", str(repo / "wordlist.txt"))
        self.assertEqual(code, 3)
        self.assertFalse((repo / "wordlist.txt").exists())

    def test_where_counts_entries_and_never_prints_them(self):
        d = self.home / ".warden"
        d.mkdir()
        (d / "wordlist.txt").write_text("# c\n" + ENTRY + "\n", encoding="utf-8")
        code, out = self.run_main("where", "names")
        self.assertEqual(code, 0)
        self.assertIn("1 entr", out)

    def test_where_without_a_file_is_not_run(self):
        code, out = self.run_main("where", "names")
        self.assertEqual(code, 3)
        self.assertIn("NOT-RUN", out)

    def test_adopt_moves_an_old_file_and_refuses_to_clobber(self):
        old = self.tmp / "aliases.txt"
        old.write_text("real-name:owner = " + ENTRY + "\n", encoding="utf-8")
        code, out = self.run_main("adopt", "identity-values", str(old))
        self.assertEqual(code, 0, out)
        self.assertFalse(old.exists())
        self.assertTrue((self.home / ".warden" / "aliases.txt").is_file())
        old.write_text("x:y = zzz\n", encoding="utf-8")
        code, out = self.run_main("adopt", "identity-values", str(old))
        self.assertEqual(code, 3)
        self.assertTrue(old.exists())


if __name__ == "__main__":
    unittest.main()
