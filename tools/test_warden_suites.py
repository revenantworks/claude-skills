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

    def test_expected_failures_are_not_failures(self):
        self.assertEqual(ws.tally("Ran 5 tests\n\nFAILED (failures=1, expected failures=2)\n"),
                         (5, 1))

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


FIX_MORE = """import unittest


class D(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.k = 1
    def test_d1(self): self.assertEqual(self.k, 1)
    def test_d2(self): pass
    def test_d3(self): pass


class E(unittest.TestCase):
    def test_e1(self): pass
"""


FIX_EXIT = """import os
import unittest


class X(unittest.TestCase):
    def test_x1(self): os._exit(0)
    def test_x2(self): pass
"""
FIX_NOISY = """import unittest
print("not.a.test.id")


class N(unittest.TestCase):
    def test_n1(self): pass
"""


class Shards(unittest.TestCase):
    def test_a_shard_that_exits_early_fails_the_run(self):
        members = {"m-one": {"test_a.py": FIX_OK, "test_x.py": FIX_EXIT}}
        with tempfile.TemporaryDirectory() as t:
            sk = fixture(Path(t), members)
            rc, out = run_main(sk, ["--shards", "3", "--split-over", "0"])
        self.assertEqual(rc, 1, out)
        self.assertIn("tests of", out)
        self.assertNotEqual(ci_local.counts(out)[1], 0, out)

    def test_an_import_time_print_adds_no_ids(self):
        members = {"m-one": {"test_a.py": FIX_OK, "test_n.py": FIX_NOISY}}
        with tempfile.TemporaryDirectory() as t:
            sk = fixture(Path(t), members)
            rc, out = run_main(sk, ["--shards", "3", "--split-over", "0"])
        self.assertEqual(rc, 0, out)
        self.assertEqual(ci_local.counts(out), (4, 0), out)

    def test_no_suite_message_names_no_absolute_path(self):
        with tempfile.TemporaryDirectory() as t:
            rc, out = run_main(Path(t) / "skills")
        self.assertEqual(rc, 1)
        self.assertNotIn(t, out)
        self.assertIn("skills", out)

    def test_balance_spreads_heavy_tests(self):
        ids = [("m.A.t1", 10.0), ("m.A.t2", 10.0), ("m.A.t3", 10.0), ("m.A.t4", 10.0),
               ("m.B.t1", 1.0), ("m.B.t2", 1.0)]
        got = ws.balance(ids, 4)
        self.assertEqual(len(got), 4)
        self.assertEqual(sorted(i for s in got for i in s), sorted(i for i, _ in ids))
        loads = [sum(w for i, w in ids if i in s) for s in got]
        self.assertLessEqual(max(loads), 11.0)

    def test_balance_never_makes_an_empty_shard(self):
        got = ws.balance([("m.A.t1", 1.0), ("m.A.t2", 1.0)], 4)
        self.assertEqual(len(got), 2)
        self.assertTrue(all(got))

    def test_weight_uses_the_measured_class_cost(self):
        self.assertGreater(ws.weight("test_hooks.PushGateTests.test_x"),
                           ws.weight("test_nothing_known.Foo.test_y"))

    def test_sharded_counts_equal_the_serial_counts(self):
        members = {"m-one": {"test_a.py": FIX_OK, "test_c.py": FIX_BAD, "test_d.py": FIX_MORE},
                   "m-two": {"test_b.py": FIX_OK}}
        with tempfile.TemporaryDirectory() as t:
            sk = fixture(Path(t), members)
            rc1, serial = run_main(sk, ["--shards", "1", "--jobs", "1"])
            rc4, sharded = run_main(sk, ["--shards", "3", "--split-over", "0"])
        self.assertEqual((rc1, rc4), (1, 1))
        self.assertEqual(ci_local.counts(serial), (12, 1), serial)
        self.assertEqual(ci_local.counts(sharded), ci_local.counts(serial), sharded)
        self.assertIn("m-one: 9 tests, 1 failures", serial)
        self.assertIn("m-one: 9 tests, 1 failures", sharded)
        self.assertIn("m-one (shard 3/3)", sharded)
        self.assertNotIn("shard", serial)

    def test_an_import_error_is_not_lost_by_sharding(self):
        members = {"m-one": {"test_a.py": FIX_OK, "test_z.py": "import no_such_module_zz\n"}}
        with tempfile.TemporaryDirectory() as t:
            sk = fixture(Path(t), members)
            rc, out = run_main(sk, ["--shards", "3", "--split-over", "0"])
        self.assertEqual(rc, 1, out)
        self.assertIn("no_such_module_zz", out)

    def test_output_keeps_member_order(self):
        members = {"m-b": {"test_a.py": FIX_OK}, "m-a": {"test_b.py": FIX_OK}}
        with tempfile.TemporaryDirectory() as t:
            sk = fixture(Path(t), members)
            rc, out = run_main(sk, ["--jobs", "4"])
        self.assertEqual(rc, 0, out)
        self.assertLess(out.index("── m-a"), out.index("── m-b"))


if __name__ == "__main__":
    unittest.main()
