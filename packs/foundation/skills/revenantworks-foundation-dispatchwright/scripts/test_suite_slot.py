"""Tests for suite_slot.py: argument parsing and the suite-process count.

    python -m unittest discover -s scripts -p "test_*.py"

No test starts, lists or waits on a live process: the process listing is replaced by
plain strings.
"""
import contextlib
import datetime as dt
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

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


class WrapperCountsOnce(unittest.TestCase):
    """A suite process under a counted suite process shares its slot (A22)."""

    def test_wrapper_and_its_suite_child_are_one_slot(self):
        procs = [
            (10, 1, "python ci_stamp.py -- python tools/ci_local.py"),
            (11, 10, "python tools/ci_local.py"),
            (12, 11, "python -m unittest discover -s tools"),
        ]
        self.assertEqual(suite_slot.count_slots(procs), 1)

    def test_a_non_suite_shell_between_does_not_split_the_slot(self):
        procs = [
            (20, 1, "python tools/ci_local.py"),
            (21, 20, "cmd /c call.bat"),
            (22, 21, "python -m unittest discover"),
        ]
        self.assertEqual(suite_slot.count_slots(procs), 1)

    def test_separate_suites_under_one_plain_parent_each_count(self):
        procs = [
            (30, 1, "bash"),
            (31, 30, "python -m pytest -q a"),
            (32, 30, "python -m pytest -q b"),
        ]
        self.assertEqual(suite_slot.count_slots(procs), 2)

    def test_godots_under_a_plain_runner_each_count(self):
        procs = [(40, 1, "python run_all.py")] + [
            (41 + i, 40, f"godot --headless -s gut_cmdln.gd -gdir=res://{i}") for i in range(3)]
        self.assertEqual(suite_slot.count_slots(procs), 3)

    def test_the_slot_runners_own_child_counts(self):
        procs = [
            (50, 1, "python suite_slot.py -- python -m pytest"),
            (51, 50, "python -m pytest"),
        ]
        self.assertEqual(suite_slot.count_slots(procs), 1)

    def test_a_parent_loop_ends(self):
        procs = [(60, 61, "python -m pytest"), (61, 60, "bash"), (70, 70, "python -m unittest")]
        self.assertEqual(suite_slot.count_slots(procs), 2)

    def test_parse_listing_reads_pid_ppid_and_command(self):
        out = "10\t1\tpython -m pytest -q\n\n11\t10\t\nbad line\n"
        self.assertEqual(suite_slot.parse_listing(out),
                         [(10, 1, "python -m pytest -q"), (11, 10, "")])

    def test_running_suites_counts_slots_from_the_listing(self):
        listing = lambda: [(1, 0, "python tools/ci_local.py"), (2, 1, "python -m unittest"),
                           (3, 0, "python -m pytest")]
        self.assertEqual(suite_slot.running_suites(listing), 2)


NOW = dt.datetime(2026, 10, 16, 22, 30, tzinfo=dt.timezone.utc)


class CapFile(unittest.TestCase):
    """The cap file: {"cap": N, "until": ISO UTC, "cpu_target": P}; only temp files are read."""

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = Path(self.dir.name) / "suite-cap.json"

    def tearDown(self):
        self.dir.cleanup()

    def write(self, text):
        self.path.write_text(text, encoding="utf-8")

    def cap(self, override=None):
        return suite_slot.current_cap(override, self.path, NOW)

    def test_unexpired_cap_is_used(self):
        self.write('{"cap": 6, "until": "2026-10-17T04:00:00Z"}')
        self.assertEqual(self.cap(), 6)

    def test_expired_cap_falls_back(self):
        self.write('{"cap": 6, "until": "2026-10-16T22:00:00Z"}')
        self.assertEqual(self.cap(), 4)

    def test_missing_and_malformed_files_fall_back(self):
        self.assertEqual(self.cap(), 4)  # no file
        for text in ["not json", "[]", '{"cap": 6}', '{"until": "2026-10-17T04:00:00Z"}',
                     '{"cap": "6", "until": "2026-10-17T04:00:00Z"}',
                     '{"cap": 0, "until": "2026-10-17T04:00:00Z"}',
                     '{"cap": true, "until": "2026-10-17T04:00:00Z"}',
                     '{"cap": 6, "until": "tomorrow"}']:
            with self.subTest(text=text):
                self.write(text)
                self.assertEqual(self.cap(), 4)

    def test_cap_flag_wins(self):
        self.write('{"cap": 6, "until": "2026-10-17T04:00:00Z"}')
        self.assertEqual(self.cap(2), 2)

    def test_parse_args_keeps_the_override_apart(self):
        self.assertIsNone(suite_slot.parse_args(["--", "pytest"]).cap_override)
        self.assertEqual(suite_slot.parse_args(["--cap", "3", "--", "pytest"]).cap_override, 3)

    def test_cpu_target(self):
        self.assertEqual(suite_slot.cpu_target(self.path), 75)  # no file
        self.write('{"cap": 6, "until": "2026-10-16T22:00:00Z", "cpu_target": 60}')
        self.assertEqual(suite_slot.cpu_target(self.path), 60)
        for text in ["nope", '{"cpu_target": 0}', '{"cpu_target": 150}', '{"cpu_target": "60"}']:
            with self.subTest(text=text):
                self.write(text)
                self.assertEqual(suite_slot.cpu_target(self.path), 75)


class Admission(unittest.TestCase):
    def test_below_two_always_admits(self):
        self.assertTrue(suite_slot.admit(0, 4, 99.0, 75))
        self.assertTrue(suite_slot.admit(1, 1, 99.0, 75))

    def test_under_cap_needs_cpu_under_target(self):
        self.assertTrue(suite_slot.admit(3, 4, 60.0, 75))
        self.assertFalse(suite_slot.admit(3, 4, 80.0, 75))
        self.assertFalse(suite_slot.admit(3, 4, 75.0, 75))

    def test_the_hard_cap_holds(self):
        self.assertFalse(suite_slot.admit(4, 4, 5.0, 75))

    def test_no_cpu_reading_leaves_the_cap_alone(self):
        self.assertTrue(suite_slot.admit(3, 4, None, 75))
        self.assertFalse(suite_slot.admit(4, 4, None, 75))

    def test_cpu_now_uses_the_stubbed_reading(self):
        reads = iter([(100, 1000), (150, 1100)])  # 50 idle of 100 ticks: 50% busy
        slept = []
        got = suite_slot.cpu_now(3.0, read=lambda: next(reads), sleep=slept.append)
        self.assertAlmostEqual(got, 50.0)
        self.assertEqual(slept, [3.0])

    def test_cpu_now_without_a_reading_is_none(self):
        self.assertIsNone(suite_slot.cpu_now(3.0, read=lambda: None, sleep=lambda s: None))

    def test_busy_percent_bounds(self):
        self.assertIsNone(suite_slot.busy_percent((5, 10), (5, 10)))
        self.assertEqual(suite_slot.busy_percent((0, 0), (0, 100)), 100.0)


class PerfLog(unittest.TestCase):
    NAMES = ["disk_idle", "mem_avail_mb"]

    def test_typeperf_parser(self):
        got = suite_slot.parse_typeperf('"10/16/2026 22:31:05.123","92.5","8100"\n', self.NAMES)
        self.assertEqual(got, {"disk_idle": 92.5, "mem_avail_mb": 8100.0})
        for line in ['"(PDH-CSV 4.0)","\\\\host\\PhysicalDisk(_Total)\\% Idle Time","\\\\host\\Memory"',
                     "", "Exiting, please wait...", '"10/16/2026 22:31:15.123"," ","8000"',
                     '"10/16/2026 22:31:20.123","90"']:
            with self.subTest(line=line):
                self.assertIsNone(suite_slot.parse_typeperf(line, self.NAMES))

    def test_the_real_counter_list_parses(self):
        names = list(suite_slot.COUNTERS)
        line = '"10/16/2026 22:31:05.123",' + ",".join(f'"{i}"' for i in range(len(names)))
        self.assertEqual(len(suite_slot.parse_typeperf(line, names)), len(names))

    def test_rig_summary_from_canned_rows(self):
        rows = [{"disk_idle": 90.0, "disk_read_mbs": 1048576.0, "mem_avail_mb": 8000.0, "cpu_queue": 1.0},
                {"disk_idle": 70.0, "disk_read_mbs": 3145728.0, "mem_avail_mb": 6000.4, "cpu_queue": 3.0},
                {"disk_idle": 101.0}]
        s = suite_slot.summarise_rig(rows)
        self.assertEqual((s["disk_busy_avg"], s["disk_busy_peak"]), (13.3, 30.0))
        self.assertEqual((s["disk_read_mbs_avg"], s["disk_read_mbs_peak"]), (2.0, 3.0))
        self.assertEqual((s["cpu_queue_avg"], s["cpu_queue_peak"]), (2.0, 3.0))
        self.assertEqual(s["mem_avail_mb_min"], 6000)
        self.assertIsNone(s["disk_queue_avg"])
        self.assertEqual(s["samples"], 3)
        self.assertEqual(set(suite_slot.RIG_KEYS) - set(s), set())

    def test_rig_sampler_reads_nothing_without_typeperf(self):
        r = suite_slot.RigSampler.__new__(suite_slot.RigSampler)
        r.names, r.rows, r.p = list(suite_slot.COUNTERS), [], None
        r.run()
        r.close()
        self.assertEqual(r.summary()["samples"], 0)
        self.assertIsNone(r.summary()["mem_avail_mb_min"])

    def test_test_counter_sums_ran_lines_across_chunks(self):
        c = suite_slot.TestCounter()
        for chunk in [b"....\nRan 1", b"8 tests in 0.1s\nOK\n", b"Ran 2 tests in 0s\r\nRan 1 test"]:
            c.feed(chunk)
        self.assertEqual(c.done(), 21)
        self.assertEqual(suite_slot.TestCounter().done(), 0)

    def test_secs_per_test(self):
        self.assertEqual(suite_slot.secs_per_test({"run_s": 30, "tests_ran": 60}), 0.5)
        self.assertIsNone(suite_slot.secs_per_test({"run_s": 30, "tests_ran": None}))
        self.assertIsNone(suite_slot.secs_per_test({"run_s": 30, "tests_ran": 0}))

    def test_row_has_no_path_separators(self):
        cmd = [r"..\Tools\Python313\python.exe", "/opt/repo/tools/ci_local.py",
               "--only", "/secret/place"]
        rig = suite_slot.summarise_rig([{"disk_idle": 90.0}, {"disk_idle": 70.0}])
        row = suite_slot.perf_row(cmd, r"..\work\wt-unit", 6, 2, 100.0, 130.0, 190.0, 0,
                                  [40.0, 60.0], 55.0, 75, rig, 3, 120)
        for key, value in row.items():
            with self.subTest(key=key):
                self.assertNotIn("/", str(value) if key != "start" else "")
                self.assertNotIn("\\", str(value))
        self.assertEqual(row["cmd"], "python.exe ci_local.py --only")
        self.assertEqual(row["repo"], "wt-unit")
        self.assertEqual((row["wait_s"], row["run_s"], row["exit"]), (30, 60, 0))
        self.assertEqual((row["cpu_avg"], row["cpu_peak"], row["cpu_at_start"]), (50.0, 60.0, 55.0))
        self.assertEqual((row["cap"], row["cpu_target"], row["suites_at_start"]), (6, 75, 2))
        self.assertEqual((row["disk_busy_avg"], row["disk_busy_peak"]), (20.0, 30.0))
        self.assertEqual((row["queued_at_start"], row["tests_ran"], row["samples"]), (3, 120, 2))
        self.assertEqual(set(suite_slot.RIG_KEYS) - set(row), set())

    def test_row_without_samples_logs_null(self):
        row = suite_slot.perf_row(["pytest"], None, 4, 0, 0.0, 0.0, 1.0, 1, [])
        self.assertIsNone(row["cpu_avg"])
        self.assertIsNone(row["tests_ran"])
        for key in suite_slot.RIG_KEYS:
            with self.subTest(key=key):
                self.assertIsNone(row[key])

    def test_summarise_groups_by_cap_and_cpu_target(self):
        rows = [
            {"cap": 4, "wait_s": 10, "run_s": 100, "cpu_avg": 50.0},
            {"cap": 6, "cpu_target": 75, "wait_s": 0, "run_s": 80, "cpu_avg": 70.0,
             "disk_busy_avg": 10.0, "mem_avail_mb_min": 9000, "tests_ran": 40},
            {"cap": 6, "cpu_target": 75, "wait_s": 20, "run_s": 120, "cpu_avg": None,
             "disk_busy_avg": 30.0, "mem_avail_mb_min": 5000, "tests_ran": 120},
            {"cap": 6, "cpu_target": 75, "wait_s": 5, "run_s": 90, "cpu_avg": 80.0,
             "mem_avail_mb_min": 7000},
            {"cap": 6, "cpu_target": 60, "wait_s": 1, "run_s": 2, "cpu_avg": 3.0},
        ]
        lines = [json.dumps(r) for r in rows] + ["not json", '{"cap": "x"}', ""]
        got = suite_slot.summarise(lines)
        self.assertEqual([(s["cap"], s["cpu_target"], s["runs"]) for s in got],
                         [(4, None, 1), (6, 60, 1), (6, 75, 3)])
        six = got[2]
        self.assertEqual((six["wait_s"], six["run_s"], six["cpu_avg"]), (5, 90, 75.0))
        self.assertEqual((six["disk_busy_avg"], six["mem_avail_mb_min"]), (20.0, 7000))
        self.assertEqual(six["s_per_test"], 1.5)  # median of 2.0 and 1.0
        self.assertIsNone(got[0]["disk_busy_avg"])
        self.assertIsNone(got[0]["s_per_test"])

    def test_report_reads_a_log(self):
        with tempfile.TemporaryDirectory() as d:
            log = Path(d) / "perf.jsonl"
            log.write_text(json.dumps({"cap": 6, "cpu_target": 75, "wait_s": 4, "run_s": 9,
                                       "cpu_avg": 61.0, "disk_busy_avg": 12.0,
                                       "mem_avail_mb_min": 8000, "tests_ran": 18}) + "\n",
                           encoding="utf-8")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = suite_slot.main(["report", "--log", str(log)])
            self.assertEqual(rc, 0)
            text = out.getvalue()
            for col in ("median wait_s", "median disk_busy_avg", "median mem_avail_mb_min",
                        "median s_per_test"):
                self.assertIn(col, text)
            self.assertIn("6 | 75 | 1 | 4 | 9 | 61 | 12 | 8000 | 0.5", text)
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(suite_slot.main(["report", "--log", str(Path(d) / "none")]), 2)

    def test_empty_summary_reads_no_runs(self):
        self.assertIn("no runs", suite_slot.format_report([]))


if __name__ == "__main__":
    unittest.main()
