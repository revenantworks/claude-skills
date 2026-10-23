"""Tests for tools/ci_local.py. No test runs a real step: every step goes through a fake runner."""
import io
import sys
import tempfile
import threading
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ci_local  # noqa: E402


def make_tree(root: Path) -> None:
    for pack in ("foundation", "warden"):
        (root / "packs" / pack / ".claude-plugin").mkdir(parents=True)
        (root / "packs" / pack / ".claude-plugin" / "plugin.json").write_text("{}")
    (root / "mods" / "vigil" / ".claude-plugin").mkdir(parents=True)
    (root / "mods" / "vigil" / ".claude-plugin" / "plugin.json").write_text("{}")
    s = root / "packs" / "foundation" / "skills" / "m-one" / "scripts"
    s.mkdir(parents=True)
    (s / "test_one.py").write_text("")
    w = root / "packs" / "warden" / "skills" / "w-one" / "scripts"
    w.mkdir(parents=True)
    (w / "test_w.py").write_text("")
    (root / "packs" / "foundation" / "skills" / "m-two").mkdir(parents=True)


class Fake:
    def __init__(self, answers=None):
        self.answers = answers or {}
        self.calls = []

    def __call__(self, step):
        self.calls.append(step.name)
        return self.answers.get(step.name, (0, "Ran 3 tests in 0.1s\n\nOK\n"))


class Steps(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        make_tree(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def names(self, **kw):
        return [s.name for s in ci_local.plan(self.root, which=kw.get("which", lambda n: n))]

    def test_order_follows_the_read_only_list(self):
        names = self.names()
        self.assertEqual(names[:4], ["build-check", "tools-tests", "warden-suites", "pii-tree"])
        self.assertLess(names.index("pii-tree"), names.index("name-leak"))
        self.assertIn("mods-sync", names)
        self.assertIn("validate:packs/foundation", names)
        self.assertIn("validate:mods/vigil", names)
        self.assertEqual(names[-1], "suite:m-one")

    def test_member_suites_skip_warden_and_folders_without_tests(self):
        names = self.names()
        self.assertNotIn("suite:w-one", names)
        self.assertNotIn("suite:m-two", names)

    def test_missing_tools_are_not_run(self):
        steps = ci_local.plan(self.root, which=lambda n: None if n in ("claude", "node") else n)
        nr = {s.name for s in steps if s.not_run}
        self.assertIn("validate:packs/foundation", nr)
        self.assertIn("vscode-node", nr)
        self.assertNotIn("build-check", nr)


class Parse(unittest.TestCase):
    def test_counts(self):
        log = "....\nRan 12 tests in 1.0s\n\nFAILED (failures=2, errors=1)\n"
        self.assertEqual(ci_local.counts(log), (12, 3))

    def test_counts_ok_and_none(self):
        self.assertEqual(ci_local.counts("Ran 1 test in 0s\n\nOK\n"), (1, 0))
        self.assertEqual(ci_local.counts("check: clean\n"), (None, 0))


class Main(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        make_tree(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def go(self, argv, fake, which=lambda n: n):
        out = io.StringIO()
        with redirect_stdout(out):
            rc = ci_local.main(argv, root=self.root, run=fake, which=which)
        return rc, out.getvalue()

    def test_all_green(self):
        rc, out = self.go([], Fake())
        self.assertEqual(rc, 0, out)
        self.assertIn("ci_local: PASS", out)

    def test_a_red_step_fails_and_every_step_still_runs(self):
        fake = Fake({"tools-tests": (1, "Ran 9 tests\n\nFAILED (failures=1)\n")})
        rc, out = self.go([], fake)
        self.assertEqual(rc, 1)
        self.assertIn("tools-tests: exit 1", out)
        self.assertIn("suite:m-one", fake.calls)
        self.assertIn("ci_local: FAIL", out)

    def test_zero_tests_is_a_failure(self):
        rc, out = self.go(["--only", "suite:m-one"], Fake({"suite:m-one": (0, "Ran 0 tests\n\nOK\n")}))
        self.assertEqual(rc, 1)
        self.assertIn("0 tests", out)

    def test_not_run_is_never_a_pass(self):
        rc, out = self.go([], Fake(), which=lambda n: None if n == "claude" else n)
        self.assertEqual(rc, ci_local.NOT_RUN)
        self.assertIn("NOT-RUN", out)
        self.assertNotIn("ci_local: PASS", out)

    def test_name_leak_exit_3_is_not_run(self):
        rc, out = self.go(["--only", "name-leak"], Fake({"name-leak": (3, "no list\n")}))
        self.assertEqual(rc, ci_local.NOT_RUN)

    def test_skip_is_named_and_not_a_failure(self):
        rc, out = self.go(["--skip", "name-leak"], Fake())
        self.assertEqual(rc, 0)
        self.assertIn("name-leak: SKIPPED (--skip)", out)

    def test_unknown_step_name_is_an_error(self):
        with self.assertRaises(SystemExit):
            self.go(["--only", "nope"], Fake())

    def test_list_prints_steps_and_runs_nothing(self):
        fake = Fake()
        rc, out = self.go(["--list"], fake)
        self.assertEqual(rc, 0)
        self.assertEqual(fake.calls, [])
        self.assertIn("build-check", out)

    def test_jobs_1_runs_in_plan_order_one_at_a_time(self):
        fake = Slow()
        rc, out = self.go(["--jobs", "1"], fake)
        self.assertEqual(rc, 0, out)
        self.assertEqual(fake.calls, [s.name for s in ci_local.plan(self.root, which=lambda n: n)])
        self.assertEqual(fake.peak, 1)

    def test_parallel_is_bounded_and_output_keeps_plan_order(self):
        fake = Slow(slow={"build-check": 0.3})
        rc, out = self.go(["--jobs", "3"], fake)
        self.assertEqual(rc, 0, out)
        self.assertGreater(fake.peak, 1)
        self.assertLessEqual(fake.peak, 3)
        names = [s.name for s in ci_local.plan(self.root, which=lambda n: n)]
        printed = [ln.split(":")[0] if not ln.startswith(("validate:", "suite:"))
                   else ":".join(ln.split(":")[:2]) for ln in out.splitlines()
                   if ": exit" in ln]
        self.assertEqual(printed, names)

    def test_parallel_failure_still_prints_its_tail(self):
        fake = Slow(slow={"build-check": 0.2},
                    answers={"tools-tests": (1, "boom-line\nRan 9 tests\n\nFAILED (failures=1)\n")})
        rc, out = self.go(["--jobs", "4"], fake)
        self.assertEqual(rc, 1)
        self.assertIn("    boom-line", out)
        self.assertLess(out.index("build-check: exit"), out.index("tools-tests: exit 1"))

    def test_default_jobs(self):
        self.assertEqual(ci_local.default_jobs(), min(6, __import__("os").cpu_count() or 1))

    def test_jobs_below_one_is_an_error(self):
        with self.assertRaises(SystemExit):
            self.go(["--jobs", "0"], Fake())


class Slow(Fake):
    """A thread-safe fake that sleeps per step and records the most steps at once."""

    def __init__(self, slow=None, answers=None):
        super().__init__(answers)
        self.slow = slow or {}
        self.lock = threading.Lock()
        self.now = self.peak = 0

    def __call__(self, step):
        with self.lock:
            self.now += 1
            self.peak = max(self.peak, self.now)
        time.sleep(self.slow.get(step.name, 0.02))
        with self.lock:
            self.now -= 1
        return super().__call__(step)


if __name__ == "__main__":
    unittest.main()
