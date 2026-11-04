"""Tests for godot_check.py. Every run goes through a fake runner, except LiveParse, which parses
real scripts with the real binary and skips where there is no Godot on PATH.

    python -m unittest discover -s scripts -p "test_*.py"
"""
import io
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
import unittest.mock
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

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

    def __call__(self, cmd, cwd=None, timeout=None):
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

    def test_godot_starts_by_the_resolved_path(self):
        run = FakeRun({"suite": (0, GREEN)})
        out = io.StringIO()
        with redirect_stdout(out):
            gc.main(self.BASE, run=run, have_lint=lambda: False, which=lambda name: f"/shims/{name}.cmd")
        self.assertEqual({c[0] for c in run.calls}, {"/shims/godot.cmd"})

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


PARSE_ERROR = "SCRIPT ERROR: Parse Error: Expected parameter name.\n   at: GDScript::reload (x.gd:2)\n"


class FakeParse:
    """Answers a parse by the script's name; the two controls behave unless told otherwise."""

    def __init__(self, answers=None, broken_control=(1, PARSE_ERROR), valid_control=(0, "")):
        self.answers = answers or {}
        self.broken_control, self.valid_control = broken_control, valid_control
        self.calls = []

    def __call__(self, cmd, cwd=None, timeout=None):
        self.calls.append(cmd)
        if "--import" in cmd:
            return self.answers.get("import", (0, ""))
        script = cmd[-1]
        if script.endswith("control_broken.gd"):
            return self.broken_control
        if script.endswith("control_valid.gd"):
            return self.valid_control
        return self.answers.get(script, (0, ""))

    def parsed(self):
        return sorted(c[-1] for c in self.calls if "--check-only" in c and "control_" not in c[-1])


class ParseAll(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.root = Path(d.name)

    def tree(self, *paths):
        for rel in paths:
            f = self.root / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text("config_version=5\n" if rel.endswith("project.godot") else "extends RefCounted\n",
                         encoding="utf-8")

    def go(self, run, *argv, godot=True):
        out = io.StringIO()
        with redirect_stdout(out):
            rc = gc.main(["--project", str(self.root), "--parse-all", *argv], run=run,
                         have_lint=lambda: False, which=lambda name: name if godot else None)
        return rc, out.getvalue()

    def test_every_folder_is_parsed_not_only_the_linted_ones(self):
        self.tree("project.godot", "src/a.gd", "tests/t.gd", "tools/helper.gd", "addons/x/p.gd", "a.gd")
        run = FakeParse()
        rc, out = self.go(run)
        self.assertEqual(rc, 0, out)
        self.assertEqual(run.parsed(), ["res://a.gd", "res://addons/x/p.gd", "res://src/a.gd",
                                        "res://tests/t.gd", "res://tools/helper.gd"])
        self.assertIn("5 found · 5 parsed · 0 failed · 0 excluded", out)
        self.assertIn("PASS", out)

    def test_parse_uses_check_only_headless(self):
        self.tree("project.godot", "a.gd")
        run = FakeParse()
        self.go(run)
        self.assertEqual(run.calls[-1], ["godot", "--headless", "--path", str(self.root.resolve()),
                                         "--check-only", "-s", "res://a.gd"])

    def test_a_broken_helper_outside_the_linted_folders_fails_by_name(self):
        self.tree("project.godot", "src/a.gd", "tools/check_hud.gd")
        rc, out = self.go(FakeParse({"res://tools/check_hud.gd": (1, PARSE_ERROR)}))
        self.assertEqual(rc, 1)
        self.assertIn("FAIL tools/check_hud.gd: SCRIPT ERROR: Parse Error", out)
        self.assertIn("2 found · 1 parsed · 1 failed", out)

    def test_a_marker_at_exit_zero_fails(self):
        self.tree("project.godot", "a.gd")
        rc, _ = self.go(FakeParse({"res://a.gd": (0, PARSE_ERROR)}))
        self.assertEqual(rc, 1)

    def test_a_crash_with_no_marker_fails(self):
        self.tree("project.godot", "a.gd")
        rc, out = self.go(FakeParse({"res://a.gd": (-11, "")}))
        self.assertEqual(rc, 1)
        self.assertIn("exit -11", out)

    def test_a_control_that_parses_clean_is_not_run_and_no_file_is_parsed(self):
        self.tree("project.godot", "a.gd")
        run = FakeParse(broken_control=(0, ""))
        rc, out = self.go(run)
        self.assertEqual(rc, gc.NOT_RUN)
        self.assertIn("control: NOT-RUN", out)
        self.assertNotIn("PASS", out)
        self.assertEqual(run.parsed(), [])

    def test_a_control_rejected_with_no_marker_is_not_run(self):
        self.tree("project.godot", "a.gd")
        self.assertEqual(self.go(FakeParse(broken_control=(1, "")))[0], gc.NOT_RUN)

    def test_a_valid_control_rejected_is_not_run(self):
        self.tree("project.godot", "a.gd")
        rc, out = self.go(FakeParse(valid_control=(1, PARSE_ERROR)))
        self.assertEqual(rc, gc.NOT_RUN)
        self.assertIn("valid script was rejected", out)

    def test_the_controls_take_the_res_route_under_godot_and_leave_nothing(self):
        self.tree("project.godot", "a.gd")
        run = FakeParse()
        self.go(run)
        controls = [c[-1] for c in run.calls if "control_" in c[-1]]
        self.assertEqual(len(controls), 2)
        for c in controls:
            self.assertTrue(c.startswith("res://.godot/"), c)
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ["a.gd", "project.godot"])

    def test_a_control_cache_folder_that_was_there_stays(self):
        self.tree("project.godot", "a.gd", ".godot/keep.txt")
        self.go(FakeParse())
        self.assertEqual([p.name for p in (self.root / ".godot").iterdir()], ["keep.txt"])

    def test_a_linked_folder_holding_scripts_fails_by_name(self):
        self.tree("project.godot", "a.gd", "shared/x.gd", "shared/y.gd")
        with unittest.mock.patch.object(gc.os.path, "islink", lambda p: Path(p).name == "shared"):
            run = FakeParse()
            rc, out = self.go(run)
        self.assertEqual(rc, 1, out)
        self.assertIn("FAIL shared: linked folder holding 2 .gd file(s)", out)
        self.assertEqual(run.parsed(), ["res://a.gd"])

    def test_a_linked_folder_with_no_script_is_only_a_note(self):
        self.tree("project.godot", "a.gd", "assets/x.txt")
        with unittest.mock.patch.object(gc.os.path, "islink", lambda p: Path(p).name == "assets"):
            rc, out = self.go(FakeParse())
        self.assertEqual(rc, 0, out)
        self.assertIn("note assets: linked folder with no .gd file", out)

    def test_a_linked_folder_can_be_excluded_with_its_reason(self):
        self.tree("project.godot", "a.gd", "shared/x.gd")
        with unittest.mock.patch.object(gc.os.path, "islink", lambda p: Path(p).name == "shared"):
            rc, out = self.go(FakeParse(), "--exclude", "shared=parsed in its own repo")
        self.assertEqual(rc, 0, out)
        self.assertIn("excluded shared: parsed in its own repo", out)

    def test_nothing_to_parse_fails(self):
        self.tree("project.godot")
        rc, out = self.go(FakeParse())
        self.assertEqual(rc, 1)
        self.assertIn("nothing was parsed", out)

    def test_a_missing_folder_fails_never_clean(self):
        out = io.StringIO()
        with redirect_stdout(out):
            rc = gc.main(["--project", str(self.root / "gone"), "--parse-all"], run=FakeParse(),
                         have_lint=lambda: False, which=lambda name: name)
        self.assertEqual(rc, 1)
        self.assertIn("folder could not be read", out.getvalue())

    def test_an_unreadable_folder_is_named_and_fails(self):
        self.tree("project.godot", "a.gd")
        real = os.walk

        def walk(root, **kw):
            if "topdown" not in kw:  # the temp folder's own clean-up walks too
                kw["onerror"](OSError(13, "denied", "locked/dir"))
            return real(root, **kw)

        with unittest.mock.patch.object(gc.os, "walk", walk):
            rc, out = self.go(FakeParse())
        self.assertEqual(rc, 1)
        self.assertIn("FAIL locked/dir: folder could not be read", out)

    def test_exclusion_is_printed_with_its_reason_and_not_parsed(self):
        self.tree("project.godot", "a.gd", "fixtures/broken_on_purpose.gd")
        run = FakeParse({"res://fixtures/broken_on_purpose.gd": (1, PARSE_ERROR)})
        rc, out = self.go(run, "--exclude", "fixtures/broken_on_purpose.gd=a parser test's input")
        self.assertEqual(rc, 0, out)
        self.assertIn("excluded fixtures/broken_on_purpose.gd: a parser test's input", out)
        self.assertEqual(run.parsed(), ["res://a.gd"])

    def test_an_exclusion_that_matches_nothing_fails(self):
        self.tree("project.godot", "a.gd")
        rc, out = self.go(FakeParse(), "--exclude", "old/gone.gd=retired")
        self.assertEqual(rc, 1)
        self.assertIn("--exclude old/gone.gd: matches no file", out)

    def test_excluding_every_file_proves_nothing(self):
        self.tree("project.godot", "a.gd")
        self.assertEqual(self.go(FakeParse(), "--exclude", "a.gd=why")[0], 1)

    def test_a_file_in_no_project_fails(self):
        self.tree("game/project.godot", "game/a.gd", "scripts/orphan.gd")
        rc, out = self.go(FakeParse())
        if (self.root.parent / "project.godot").exists():
            self.skipTest("a project.godot sits above the temp folder")
        self.assertEqual(rc, 1)
        self.assertIn("FAIL scripts/orphan.gd: in no project", out)

    def test_a_nested_project_is_imported_and_parsed_as_itself(self):
        self.tree("project.godot", "a.gd", "demo/project.godot", "demo/b.gd")
        run = FakeParse()
        rc, _ = self.go(run)
        self.assertEqual(rc, 0)
        self.assertEqual(run.parsed(), ["res://a.gd", "res://b.gd"])
        self.assertEqual(sum("--import" in c for c in run.calls), 2)

    def test_hidden_folders_are_skipped(self):
        self.tree("project.godot", "a.gd", ".godot/cache.gd", ".git/x.gd")
        run = FakeParse()
        self.go(run)
        self.assertEqual(run.parsed(), ["res://a.gd"])

    def test_a_failed_import_fails_but_every_file_is_still_named(self):
        self.tree("project.godot", "a.gd")
        run = FakeParse({"import": (1, "")})
        rc, _ = self.go(run)
        self.assertEqual(rc, 1)
        self.assertEqual(run.parsed(), ["res://a.gd"])

    def test_import_markers_do_not_stop_the_per_file_list(self):
        self.tree("project.godot", "a.gd", "b.gd")
        rc, out = self.go(FakeParse({"import": (0, PARSE_ERROR), "res://a.gd": (1, PARSE_ERROR)}))
        self.assertEqual(rc, 1)
        self.assertIn("FAIL a.gd", out)
        self.assertIn("1 parsed", out)

    def test_godot_absent_is_not_run(self):
        self.tree("project.godot", "a.gd")
        rc, out = self.go(FakeParse(), godot=False)
        self.assertEqual(rc, gc.NOT_RUN)

    def test_before_runs_first_and_a_failure_stops(self):
        self.tree("project.godot", "a.gd")
        run = FakeParse({"import": (0, "")})
        calls = []

        def spy(cmd, cwd=None, timeout=None):
            calls.append(cmd[0])
            return (1, "") if cmd[0] == "make" else run(cmd, cwd, timeout)

        rc, _ = self.go(spy, "--before", "make gen")
        self.assertEqual((rc, calls), (1, ["make"]))

    def test_json_record(self):
        self.tree("project.godot", "a.gd", "b.gd")
        rc, out = self.go(FakeParse({"res://b.gd": (1, PARSE_ERROR)}), "--json")
        rec = json.loads(out.strip().splitlines()[-1])
        self.assertEqual((rec["verdict"], rec["parse"]["found"], rec["parse"]["parsed"]), ("FAIL", 2, 1))
        self.assertEqual(rec["parse"]["failed"][0]["path"], "b.gd")

    def test_usage(self):
        for argv in (["--parse-all", "--gut", "x"], ["--parse-all", "--expect-tests", "1"],
                     ["--parse-all", "--lint", "src"], ["--parse-all", "--import-only"],
                     ["--parse-all", "--script", "x"], ["--parse-all", "--exclude", "nowhy"],
                     ["--parse-all", "--jobs", "0"], ["--exclude", "a=b", "--import-only"]):
            with self.subTest(argv=argv), self.assertRaises(SystemExit), redirect_stderr(io.StringIO()):
                gc.parse_args(["--project", "game", *argv])


class RunProcess(unittest.TestCase):
    def test_timeout_is_a_failure_not_a_hang(self):
        rc, out = gc.run_process([sys.executable, "-c", "import time; time.sleep(30)"], timeout=1)
        self.assertEqual(rc, 124)
        self.assertIn("timed out", out)

    def _hung_grandchild_returns_at_the_timeout(self, cmd):
        start = time.monotonic()
        rc, out = gc.run_process(cmd, timeout=2)
        self.assertLess(time.monotonic() - start, 10)
        self.assertEqual(rc, 124)

    def test_a_hung_grandchild_holding_the_pipe_does_not_hang_the_check(self):
        inner = "import time; time.sleep(15)"
        code = f"import subprocess, sys; subprocess.run([sys.executable, '-c', {inner!r}])"
        self._hung_grandchild_returns_at_the_timeout([sys.executable, "-c", code])

    @unittest.skipUnless(os.name == "nt", "the .cmd shim shape exists only on Windows")
    def test_a_hung_godot_under_a_cmd_shim_does_not_hang_the_check(self):
        self._hung_grandchild_returns_at_the_timeout(
            ["cmd", "/c", sys.executable, "-c", "import time; time.sleep(15)"])

    def test_output_and_exit_code_still_come_back(self):
        rc, out = gc.run_process([sys.executable, "-c", "import sys; print('hello'); sys.exit(3)"], timeout=30)
        self.assertEqual(rc, 3)
        self.assertIn("hello", out)


@unittest.skipIf(shutil.which("godot") is None, "no Godot on PATH; the real parse cannot run")
class LiveParse(unittest.TestCase):
    """The real binary on a small project: the positive control, class_name lookups, no script run."""

    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.TemporaryDirectory()
        cls.root = Path(cls.dir.name)
        for rel, body in {
            "project.godot": "config_version=5\n[application]\nconfig/name=\"t\"\n",
            "base.gd": "class_name LiveBase\nextends RefCounted\nfunc a() -> int:\n\treturn 1\n",
            "src/child.gd": "extends LiveBase\nfunc b() -> int:\n\treturn a()\n",
            "tools/runs.gd": "extends SceneTree\nfunc _init():\n\tprint(\"SCRIPT ERROR: ran\")\n\tquit(3)\n",
            "tools/broken.gd": "extends RefCounted\nfunc x(:\n\tpass\n",
            "tools/shadow.gd": "@tool\nextends EditorPlugin\nfunc _run_scene() -> void:\n\tpass\n",
        }.items():
            f = cls.root / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(body, encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.dir.cleanup()

    def go(self, *argv):
        out = io.StringIO()
        with redirect_stdout(out):
            rc = gc.main(["--project", str(self.root), "--parse-all", *argv])
        return rc, out.getvalue()

    def test_broken_and_shadowing_scripts_fail_and_the_rest_pass(self):
        rc, out = self.go()
        self.assertEqual(rc, 1, out)
        self.assertIn("control: a broken script was rejected", out)
        self.assertIn("5 found · 3 parsed · 2 failed", out)
        self.assertIn("FAIL tools/broken.gd", out)
        self.assertIn("FAIL tools/shadow.gd: SCRIPT ERROR: Parse Error: The function signature", out)
        self.assertNotIn("FAIL tools/runs.gd", out)  # the parse did not run its _init
        self.assertNotIn("FAIL src/child.gd", out)   # class_name resolved after the import

    def test_excluding_the_broken_ones_passes(self):
        rc, out = self.go("--exclude", "tools/broken.gd=input for a test",
                          "--exclude", "tools/shadow.gd=input for a test")
        self.assertEqual(rc, 0, out)
        self.assertIn("5 found · 3 parsed · 0 failed · 2 excluded", out)
        self.assertEqual(list((self.root / ".godot").glob("godot-check-control-*")), [])

    def test_static_initialisers_run_under_check_only_as_the_reference_warns(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "project.godot").write_text("config_version=5\n", encoding="utf-8")
            (root / "statics.gd").write_text(
                "extends RefCounted\n"
                "static var x = _boom()\n"
                "static func _boom() -> int:\n"
                "\tFileAccess.open(\"res://var_ran.txt\", FileAccess.WRITE).store_string(\"x\")\n"
                "\treturn 1\n"
                "static func _static_init() -> void:\n"
                "\tFileAccess.open(\"res://init_ran.txt\", FileAccess.WRITE).store_string(\"x\")\n",
                encoding="utf-8")
            out = io.StringIO()
            with redirect_stdout(out):
                rc = gc.main(["--project", d, "--parse-all"])
            self.assertEqual(rc, 0, out.getvalue())
            self.assertTrue((root / "var_ran.txt").is_file())
            self.assertTrue((root / "init_ran.txt").is_file())


if __name__ == "__main__":
    unittest.main()
