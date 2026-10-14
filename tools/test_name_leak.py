"""tools/name_leak.py: the local name-leak check, run before a push (owner Q31; local only 2026-10-02).

Every term here is invented. The real list lives on the owner's machine, outside every repo
(--list, else WARDEN_NAMES_FILE, else ~/.warden/wordlist.txt). Every run here points the home
folder at an empty temp folder, so the real list is never read. A test that needed a real name
to pass would be the leak it guards against.
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
SCRIPT = ROOT / "tools" / "name_leak.py"
TERMS = ("zorblax", "quuxcorp")
HOME = Path(tempfile.mkdtemp(prefix="nl-home-"))
atexit.register(shutil.rmtree, HOME, True)


def _env(**extra):
    env = {k: v for k, v in os.environ.items() if k != "WARDEN_NAMES_FILE"}
    env.update(HOME=str(HOME), USERPROFILE=str(HOME))
    env.update(extra)
    return env


class NameLeak(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.repo = base / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.outside = base / "outside"
        self.outside.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def track(self, rel, text):
        p = self.repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(text.encode("utf-8"))
        subprocess.run(["git", "-C", str(self.repo), "add", rel], check=True)

    def untracked(self, rel, text):
        (self.repo / rel).write_bytes(text.encode("utf-8"))

    def terms_file(self, text):
        p = self.outside / "terms.txt"
        p.write_bytes(text.encode("utf-8"))
        return p

    def run_check(self, *args, env=None):
        r = subprocess.run([sys.executable, str(SCRIPT), "--root", str(self.repo), *args],
                           capture_output=True, text=True, env=env or _env())
        return r.returncode, r.stdout + r.stderr

    # --- no list: NOT-RUN with the setup command, never a pass ---------------------
    def test_no_list_is_not_run_with_the_setup_command(self):
        self.track("a.md", "zorblax lives here\n")
        code, out = self.run_check()
        self.assertEqual(code, 3, out)
        self.assertIn("NOT-RUN: no list", out)
        self.assertIn("setup names", out)

    def test_named_list_missing_is_refused(self):
        code, out = self.run_check("--list", str(self.outside / "nope.txt"))
        self.assertEqual(code, 2, out)

    def test_empty_list_is_not_run(self):
        """A template with comment lines only must not read as a pass."""
        lst = self.terms_file("# only a comment\n\n")
        code, out = self.run_check("--list", str(lst))
        self.assertEqual(code, 3, out)
        self.assertIn("NOT-RUN", out)

    def test_default_private_folder_is_read(self):
        folder = HOME / ".warden"
        folder.mkdir(exist_ok=True)
        (folder / "wordlist.txt").write_bytes(b"zorblax\n")
        try:
            self.track("a.md", "zorblax\n")
            code, out = self.run_check()
            self.assertEqual(code, 1, out)
        finally:
            shutil.rmtree(folder, ignore_errors=True)

    def test_rewrite_form_reads_the_name_only(self):
        """shieldwarden's `Name==>replacement` form shares the list; the replacement is not a term."""
        self.track("a.md", "the owner wrote this\n")
        code, out = self.run_check("--list", str(self.terms_file("zorblax==>the owner\n")))
        self.assertEqual(code, 0, out)
        self.track("b.md", "zorblax wrote this\n")
        code, out = self.run_check("--list", str(self.terms_file("zorblax==>the owner\n")))
        self.assertEqual(code, 1, out)

    # --- hits ---------------------------------------------------------------------
    def test_hit_exits_nonzero_with_file_and_line(self):
        self.track("docs/a.md", "clean line\nsent by Zorblax today\n")
        code, out = self.run_check("--list", str(self.terms_file("zorblax\n")))
        self.assertEqual(code, 1, out)
        self.assertIn("docs/a.md:2", out)

    def test_hit_never_echoes_the_term(self):
        self.track("a.md", "ZORBLAX and quuxcorp\n")
        code, out = self.run_check("--list", str(self.terms_file("\n".join(TERMS) + "\n")))
        self.assertEqual(code, 1, out)
        for t in TERMS:
            self.assertNotIn(t, out.lower())
        self.assertIn("list entry #1", out)
        self.assertIn("list entry #2", out)
        self.assertNotIn("chars)", out)

    def test_env_var_names_the_list(self):
        self.track("a.md", "quuxcorp\n")
        lst = self.terms_file("quuxcorp\n")
        code, out = self.run_check(env=_env(WARDEN_NAMES_FILE=str(lst)))
        self.assertEqual(code, 1, out)

    def test_clean_tree_passes(self):
        self.track("a.md", "nothing to see\n")
        code, out = self.run_check("--list", str(self.terms_file("zorblax\n")))
        self.assertEqual(code, 0, out)
        self.assertIn("OK", out)
        self.assertIn("1 term", out)

    # --- modes --------------------------------------------------------------------
    def test_word_mode_ignores_a_longer_word(self):
        self.track("a.md", "the zorblaxian empire\n")
        code, out = self.run_check("--list", str(self.terms_file("zorblax\n")))
        self.assertEqual(code, 0, out)

    def test_substring_mode_flag_catches_a_longer_word(self):
        self.track("a.md", "the zorblaxian empire\n")
        code, out = self.run_check("--list", str(self.terms_file("zorblax\n")), "--mode", "substring")
        self.assertEqual(code, 1, out)

    def test_per_term_substring_prefix(self):
        self.track("a.md", "mail.quuxcorpmail.example\n")
        code, out = self.run_check("--list", str(self.terms_file("sub:quuxcorp\n")))
        self.assertEqual(code, 1, out)
        self.assertNotIn("quuxcorp", out.lower())

    def test_word_mode_treats_underscore_and_digits_as_edges(self):
        """Letters end a word; `_`, `-`, digits and punctuation do not hide a name in a file name."""
        self.track("a.md", "path/zorblax_notes\n")
        self.track("b.md", "zorblax2026-draft\n")
        code, out = self.run_check("--list", str(self.terms_file("zorblax\n")))
        self.assertEqual(code, 1, out)
        self.assertIn("a.md:1", out)
        self.assertIn("b.md:1", out)

    def test_multiword_term(self):
        self.track("a.md", "Project   Quuxcorp Zorblax\n")
        code, out = self.run_check("--list", str(self.terms_file("quuxcorp zorblax\n")))
        self.assertEqual(code, 1, out)

    # --- scope --------------------------------------------------------------------
    def test_only_tracked_files_are_scanned(self):
        self.track("a.md", "clean\n")
        self.untracked("scratch.md", "zorblax\n")
        code, out = self.run_check("--list", str(self.terms_file("zorblax\n")))
        self.assertEqual(code, 0, out)

    def test_binary_files_are_skipped(self):
        p = self.repo / "img.bin"
        p.write_bytes(b"\x00\x01zorblax\x00")
        subprocess.run(["git", "-C", str(self.repo), "add", "img.bin"], check=True)
        code, out = self.run_check("--list", str(self.terms_file("zorblax\n")))
        self.assertEqual(code, 0, out)

    def test_list_inside_the_repo_is_refused(self):
        """The list must live outside the repo; a tracked list is itself the leak."""
        self.track("terms.txt", "zorblax\n")
        code, out = self.run_check("--list", str(self.repo / "terms.txt"))
        self.assertEqual(code, 2, out)
        self.assertNotIn("zorblax", out.lower())

    def test_list_inside_any_other_repo_is_refused(self):
        other = self.outside / "other-repo"
        other.mkdir()
        subprocess.run(["git", "init", "-q", str(other)], check=True)
        lst = other / "terms.txt"
        lst.write_bytes(b"zorblax\n")
        code, out = self.run_check("--list", str(lst))
        self.assertEqual(code, 2, out)
        self.assertNotIn("zorblax", out.lower())


if __name__ == "__main__":
    unittest.main()
