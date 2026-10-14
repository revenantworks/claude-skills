"""warden_suites.py: the 0-tests guard and suite discovery (observation 0372)."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import warden_suites as ws  # noqa: E402


class RanCount(unittest.TestCase):
    def test_reads_the_total(self):
        self.assertEqual(ws.ran_count("....\n----\nRan 36 tests in 0.2s\n\nOK\n"), 36)

    def test_one_test(self):
        self.assertEqual(ws.ran_count("Ran 1 test in 0.001s\nOK\n"), 1)

    def test_no_tests_found_is_zero(self):
        self.assertEqual(ws.ran_count("\n----\nRan 0 tests in 0.000s\n\nNO TESTS RAN\n"), 0)

    def test_no_line_is_zero(self):
        self.assertEqual(ws.ran_count("ImportError: boom\n"), 0)

    def test_last_line_wins(self):
        self.assertEqual(ws.ran_count("Ran 2 tests in 0s\nRan 7 tests in 0s\n"), 7)


class Suites(unittest.TestCase):
    def test_only_folders_with_tests(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            for m, f in (("b", "test_x.py"), ("a", "test_y.py"), ("c", "helper.py")):
                (root / m / "scripts").mkdir(parents=True)
                (root / m / "scripts" / f).write_text("", encoding="utf-8")
            self.assertEqual([p.parent.name for p in ws.suites(root)], ["a", "b"])

    def test_the_real_tree_has_every_member(self):
        names = {p.parent.name.rsplit("-", 1)[-1] for p in ws.suites()}
        self.assertEqual(names, {"gatewarden", "keywarden", "shieldwarden", "trustwarden"})


if __name__ == "__main__":
    unittest.main()
