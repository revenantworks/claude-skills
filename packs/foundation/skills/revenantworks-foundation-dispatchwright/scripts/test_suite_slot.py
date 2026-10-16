"""Tests for suite_slot.py: argument parsing and the suite-process count.

    python -m unittest discover -s scripts -p "test_*.py"

No test starts, lists or waits on a live process: the process listing is replaced by
plain strings.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import suite_slot  # noqa: E402


class ParseArgs(unittest.TestCase):
    def test_defaults_and_double_dash(self):
        a = suite_slot.parse_args(["--", "python", "-m", "unittest", "discover"])
        self.assertEqual(a.cap, 4)
        self.assertIsNone(a.cwd)
        self.assertEqual(a.cmd, ["python", "-m", "unittest", "discover"])

    def test_cap_and_cwd(self):
        a = suite_slot.parse_args(["--cap", "2", "--cwd", "repo", "--", "godot", "--headless"])
        self.assertEqual((a.cap, a.cwd), (2, "repo"))
        self.assertEqual(a.cmd, ["godot", "--headless"])

    def test_command_flags_after_double_dash_stay_the_commands(self):
        a = suite_slot.parse_args(["--", "python", "tools/ci_local.py", "--cap", "9"])
        self.assertEqual(a.cap, 4)
        self.assertEqual(a.cmd, ["python", "tools/ci_local.py", "--cap", "9"])

    def test_command_without_double_dash(self):
        a = suite_slot.parse_args(["pytest", "-q"])
        self.assertEqual(a.cmd, ["pytest", "-q"])

    def test_no_command_is_an_error(self):
        with self.assertRaises(SystemExit):
            suite_slot.parse_args(["--cap", "3"])
        with self.assertRaises(SystemExit):
            suite_slot.parse_args(["--"])

    def test_cap_below_one_is_an_error(self):
        with self.assertRaises(SystemExit):
            suite_slot.parse_args(["--cap", "0", "--", "pytest"])


class SuiteCount(unittest.TestCase):
    def test_suite_lines_match(self):
        for line in [
            r"python.exe -m unittest discover -s tools -p test_*.py",
            "python3 -m pytest -q tests",
            "python tools/ci_local.py",
            "python scripts/ci-local.py --fast",
            "python tools/warden_suites.py",
            "Godot_v4.5-stable_win64.exe --headless -s addons/gut/gut_cmdln.gd",
            "godot --path game --headless --import",
        ]:
            with self.subTest(line=line):
                self.assertTrue(suite_slot.is_suite(line))

    def test_other_lines_do_not_match(self):
        for line in [
            "",
            "python -m http.server 8000",
            "python scripts/build.py --check",
            "godot --editor --path game",
            "python suite_slot.py -- python -m unittest discover",
        ]:
            with self.subTest(line=line):
                self.assertFalse(suite_slot.is_suite(line))

    def test_each_process_counts(self):
        lines = [
            "python tools/ci_local.py",
            "godot --headless -s addons/gut/gut_cmdln.gd -gdir=res://a",
            "godot --headless -s addons/gut/gut_cmdln.gd -gdir=res://b",
            "godot --headless -s addons/gut/gut_cmdln.gd -gdir=res://c",
            "python -m http.server",
            "python suite_slot.py --cap 4 -- python -m pytest",
        ]
        self.assertEqual(suite_slot.count_suites(lines), 4)

    def test_running_suites_reads_the_listing(self):
        listing = lambda: ["python -m pytest", "python -m unittest", "node server.js"]
        self.assertEqual(suite_slot.running_suites(listing), 2)


if __name__ == "__main__":
    unittest.main()
