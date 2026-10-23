"""warden_suites.py: the 0-tests guard and suite discovery (observation 0372)."""
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ci_local  # noqa: E402
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


FIX_OK = """import unittest


class A(unittest.TestCase):
    def test_a1(self): pass
    def test_a2(self): pass


class B(unittest.TestCase):
    def test_b1(self): pass
"""
FIX_BAD = """import unittest


class C(unittest.TestCase):
    def test_c1(self): pass
    def test_c2(self): self.fail("red")
"""


def fixture(root, members):
    """A skills tree: {member: {file name: source}}."""
    for m, files in members.items():
        d = root / m / "scripts"
        d.mkdir(parents=True)
        for f, src in files.items():
            (d / f).write_text(src, encoding="utf-8")
    return root


def run_main(skills, argv=()):
    out = io.StringIO()
    with redirect_stdout(out):
        rc = ws.main(list(argv), skills=skills)
    return rc, out.getvalue()


class Tally(unittest.TestCase):
    def test_ok(self):
        self.assertEqual(ws.tally("Ran 12 tests in 1s\n\nOK\n"), (12, 0))

    def test_failures_and_errors(self):
        self.assertEqual(ws.tally("Ran 12 tests\n\nFAILED (failures=2, errors=1)\n"), (12, 3))

    def test_nothing(self):
        self.assertEqual(ws.tally("ImportError: boom\n"), (0, 0))


class Totals(unittest.TestCase):
    """ci_local reads the last Ran/FAILED lines: they must be the sum of every suite."""

    def test_the_last_lines_are_the_sum(self):
        with tempfile.TemporaryDirectory() as t:
            sk = fixture(Path(t), {"m-one": {"test_a.py": FIX_OK}, "m-two": {"test_c.py": FIX_BAD}})
            rc, out = run_main(sk)
        self.assertEqual(rc, 1, out)
        self.assertEqual(ci_local.counts(out), (5, 1), out)
        self.assertIn("m-one: 3 tests, 0 failures, exit 0", out)

    def test_green_total(self):
        with tempfile.TemporaryDirectory() as t:
            sk = fixture(Path(t), {"m-one": {"test_a.py": FIX_OK}, "m-two": {"test_b.py": FIX_OK}})
            rc, out = run_main(sk)
        self.assertEqual(rc, 0, out)
        self.assertEqual(ci_local.counts(out), (6, 0), out)
        self.assertTrue(out.rstrip().endswith("OK"), out)

    def test_a_suite_with_zero_tests_fails_the_run(self):
        with tempfile.TemporaryDirectory() as t:
            sk = fixture(Path(t), {"m-one": {"test_a.py": FIX_OK},
                                   "m-two": {"test_e.py": "import unittest\n"}})
            rc, out = run_main(sk)
        self.assertEqual(rc, 1, out)
        self.assertIn("m-two: Ran 0 tests", out)


if __name__ == "__main__":
    unittest.main()
