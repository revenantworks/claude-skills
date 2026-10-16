"""Tests for godot_check.py. No test starts Godot: every run goes through a fake runner.

    python -m unittest discover -s scripts -p "test_*.py"
"""
import io
import json
import os
import sys
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import godot_check as gc  # noqa: E402

GREEN = """\
res://tests/test_a.gd
Totals
------
Warnings              2
Scripts              43
Tests               411
Passing Tests       411
Asserts           324558
Time              117.556s

---- All tests passed! ----
"""

PENDING = """\
Totals
------
Scripts              43
Tests               412
Passing Tests       411
Pending               1
Asserts             900
"""

FAILING = """\
Totals
------
Scripts              43
Tests               411
Passing Tests       409
Failing Tests         2
"""

DROPPED = GREEN.replace("Scripts              43", "Scripts              42").replace(
    "res://tests/test_a.gd", "SCRIPT ERROR: Parse Error: Unexpected token\n   at: res://tests/test_b.gd:12")


class FakeRun:
    """Records each command and answers with a scripted (rc, output) per step."""

    def __init__(self, answers):
        self.answers = answers
        self.calls = []

    def __call__(self, cmd, cwd=None):
        self.calls.append(cmd)
        key = "import" if "--import" in cmd else "lint" if "gdtoolkit.linter" in cmd else \
            "before" if cmd[:1] == ["make"] else "suite"
        return self.answers.get(key, (0, ""))


class Summary(unittest.TestCase):
    def test_reads_the_three_numbers(self):
        s = gc.parse_summary(GREEN)
        self.assertEqual((s["scripts"], s["tests"], s["failures"]), (43, 411, 0))

    def test_tests_line_is_anchored_with_pending(self):
        s = gc.parse_summary(PENDING)
        self.assertEqual(s["tests"], 412)
        self.assertEqual(s["passing"], 411)
        self.assertEqual(s["pending"], 1)
        self.assertEqual(s["failures"], 0)

    def test_failing_line(self):
        self.assertEqual(gc.parse_summary(FAILING)["failures"], 2)

    def test_no_summary(self):
        self.assertIsNone(gc.parse_summary("Godot Engine v4.5\nquit\n"))


class Markers(unittest.TestCase):
    def test_engine_markers_found(self):
        log = "ok\nSCRIPT ERROR: x\nParse Error: y\nERROR: Failed to load script res://a.gd\n"
        self.assertEqual(len(gc.find_markers(log)), 3)

    def test_clean_log(self):
        self.assertEqual(gc.find_markers(GREEN), [])


class Verdict(unittest.TestCase):
    def test_all_match(self):
        ok, why = gc.judge(gc.parse_summary(GREEN), [], 0, 43, 411)
        self.assertTrue(ok, why)

    def test_marker_fails_a_green_summary(self):
        ok, why = gc.judge(gc.parse_summary(GREEN), ["SCRIPT ERROR: x"], 0, 43, 411)
        self.assertFalse(ok)
        self.assertIn("marker", why)

    def test_dropped_script_fails_by_count(self):
        ok, why = gc.judge(gc.parse_summary(DROPPED), [], 0, 43, 411)
        self.assertFalse(ok)
        self.assertIn("scripts 42", why)

    def test_missing_summary_fails(self):
        ok, why = gc.judge(None, [], 0, 43, 411)
        self.assertFalse(ok)

    def test_nonzero_exit_fails(self):
        ok, _ = gc.judge(gc.parse_summary(GREEN), [], 1, 43, 411)
        self.assertFalse(ok)

    def test_numbers_line_prints_slack(self):
        line = gc.numbers_line(gc.parse_summary(PENDING), 43, 411)
        self.assertIn("scripts 43/43", line)
        self.assertIn("tests 412/411 (+1)", line)
        self.assertIn("failures 0", line)


class Commands(unittest.TestCase):
    def test_import_command(self):
        self.assertEqual(gc.import_cmd("godot", "game"),
                         ["godot", "--headless", "--path", "game", "--import"])

    def test_gut_command(self):
        cmd = gc.suite_cmd("godot", "game", gut="-gdir=res://tests -gexit", script=None)
        self.assertEqual(cmd[:6], ["godot", "--headless", "--path", "game", "-s",
                                   "addons/gut/gut_cmdln.gd"])
        self.assertEqual(cmd[6:], ["-gdir=res://tests", "-gexit"])

    def test_gut_command_adds_gexit(self):
        self.assertIn("-gexit", gc.suite_cmd("godot", "game", gut="", script=None))

    def test_script_command(self):
        self.assertEqual(gc.suite_cmd("godot", "game", gut=None, script="res://tools/probe.gd"),
                         ["godot", "--headless", "--path", "game", "-s", "res://tools/probe.gd"])


class Main(unittest.TestCase):
    def run_main(self, argv, run, lint=True, godot=True):
        out = io.StringIO()
        with redirect_stdout(out):
            rc = gc.main(argv, run=run, have_lint=lambda: lint,
                         which=lambda name: name if godot else None)
        return rc, out.getvalue()

    BASE = ["--project", "game", "--expect-scripts", "43", "--expect-tests", "411"]

    def test_green_run_order_and_exit(self):
        run = FakeRun({"suite": (0, GREEN)})
        rc, out = self.run_main(self.BASE + ["--before", "make gen", "--lint", "src"], run)
        self.assertEqual(rc, 0, out)
        order = ["before" if c[:1] == ["make"] else "import" if "--import" in c else
                 "lint" if "gdtoolkit.linter" in c else "suite" for c in run.calls]
        self.assertEqual(order, ["before", "import", "lint", "suite"])
        self.assertIn("PASS", out)

    def test_import_marker_stops_before_the_suite(self):
        run = FakeRun({"import": (0, "SCRIPT ERROR: Parse Error: bad\n"), "suite": (0, GREEN)})
        rc, out = self.run_main(self.BASE, run)
        self.assertEqual(rc, 1)
        self.assertFalse(any("gut_cmdln.gd" in c for c in run.calls))

    def test_dropped_script_is_red(self):
        rc, out = self.run_main(self.BASE, FakeRun({"suite": (0, DROPPED)}))
        self.assertEqual(rc, 1)
        self.assertIn("FAIL", out)

    def test_lint_absent_is_not_run_never_pass(self):
        rc, out = self.run_main(self.BASE + ["--lint", "src"], FakeRun({"suite": (0, GREEN)}),
                                lint=False)
        self.assertEqual(rc, 0)
        self.assertIn("lint: NOT-RUN", out)

    def test_godot_absent_is_not_run(self):
        rc, out = self.run_main(self.BASE, FakeRun({}), godot=False)
        self.assertEqual(rc, gc.NOT_RUN)
        self.assertIn("NOT-RUN", out)

    def test_repeat_prints_each_run(self):
        run = FakeRun({"suite": (0, GREEN)})
        rc, out = self.run_main(self.BASE + ["--repeat", "3"], run)
        self.assertEqual(rc, 0)
        self.assertEqual(out.count("run 1/3"), 1)
        self.assertEqual(out.count("scripts 43/43"), 3)

    def test_import_only_needs_no_expected_totals(self):
        rc, _ = self.run_main(["--project", "game", "--import-only"], FakeRun({}))
        self.assertEqual(rc, 0)

    def test_suite_needs_expected_totals(self):
        with self.assertRaises(SystemExit):
            self.run_main(["--project", "game"], FakeRun({}))

    def test_json_record(self):
        rc, out = self.run_main(self.BASE + ["--json"], FakeRun({"suite": (0, GREEN)}))
        rec = json.loads(out.strip().splitlines()[-1])
        self.assertEqual(rec["verdict"], "PASS")
        self.assertEqual(rec["runs"][0]["scripts"], 43)


if __name__ == "__main__":
    unittest.main()
