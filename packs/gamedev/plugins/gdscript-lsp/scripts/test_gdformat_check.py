"""Tests for gdformat_check.py. No test needs a real formatter: GDSCRIPT_FORMAT_CMD points at a
fake one, and PATH is emptied for the NOT-RUN cases.

    python -m unittest discover -s scripts -p "test_*.py"
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOOK = HERE / "gdformat_check.py"
sys.path.insert(0, str(HERE))

import gdformat_check as gf  # noqa: E402

NO_WINDOW = 0x08000000 if os.name == "nt" else 0

FAKE = """\
import os, sys
mode = os.environ.get("FAKE_MODE", "clean")
with open(os.environ["FAKE_LOG"], "a", encoding="utf-8") as f:
    f.write(" ".join(sys.argv[1:]) + "\\n")
if mode == "clean":
    sys.exit(0)
if mode == "dirty":
    print("would reformat " + sys.argv[-1])
    sys.exit(1)
if mode == "crash":
    print("Error: unexpected token", file=sys.stderr)
    sys.exit(3)
if mode == "hang":
    import time
    time.sleep(30)
"""


class HookTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.gd = self.dir / "player.gd"
        self.gd.write_text("extends Node\nfunc _ready():\n\tpass\n", encoding="utf-8")
        self.fake = self.dir / "fake_fmt.py"
        self.fake.write_text(FAKE, encoding="utf-8")
        self.log = self.dir / "calls.log"

    def tearDown(self):
        self.tmp.cleanup()

    def run_hook(self, payload, mode="clean", fake=True, timeout_s=None):
        env = dict(os.environ, FAKE_MODE=mode, FAKE_LOG=str(self.log))
        env.pop("GDSCRIPT_FORMAT_CMD", None)
        if fake:
            env["GDSCRIPT_FORMAT_CMD"] = json.dumps([sys.executable, str(self.fake)])
        else:
            env["PATH"] = str(self.dir / "empty-path")
        if timeout_s is not None:
            env["GDSCRIPT_FORMAT_TIMEOUT"] = str(timeout_s)
        data = payload if isinstance(payload, str) else json.dumps(payload)
        return subprocess.run([sys.executable, str(HOOK)], input=data, capture_output=True,
                              text=True, env=env, timeout=60, creationflags=NO_WINDOW)

    def edit(self, path=None, tool="Edit"):
        return {"hook_event_name": "PostToolUse", "tool_name": tool,
                "tool_input": {"file_path": str(path or self.gd)}}

    def calls(self):
        return self.log.read_text(encoding="utf-8").splitlines() if self.log.exists() else []

    def test_clean_file_is_silent_and_exit_0(self):
        r = self.run_hook(self.edit())
        self.assertEqual((r.returncode, r.stdout, r.stderr), (0, "", ""))
        self.assertEqual(len(self.calls()), 1)

    def test_check_flag_is_always_passed_and_file_is_untouched(self):
        before = self.gd.read_bytes()
        self.run_hook(self.edit(), mode="dirty")
        self.assertIn("--check", self.calls()[0].split())
        self.assertEqual(self.gd.read_bytes(), before)

    def test_unformatted_file_exits_2_with_feedback_on_stderr(self):
        r = self.run_hook(self.edit(), mode="dirty")
        self.assertEqual(r.returncode, 2)
        self.assertIn("player.gd", r.stderr)
        self.assertIn("check only", r.stderr)
        self.assertIn("would reformat", r.stderr)

    def test_write_and_multiedit_are_checked_too(self):
        for tool in ("Write", "MultiEdit"):
            self.run_hook(self.edit(tool=tool))
        self.assertEqual(len(self.calls()), 2)

    def test_non_gd_file_is_ignored(self):
        other = self.dir / "notes.md"
        other.write_text("x", encoding="utf-8")
        r = self.run_hook(self.edit(other))
        self.assertEqual((r.returncode, r.stdout, r.stderr), (0, "", ""))
        self.assertEqual(self.calls(), [])

    def test_missing_file_is_ignored(self):
        r = self.run_hook(self.edit(self.dir / "gone.gd"))
        self.assertEqual(r.returncode, 0)
        self.assertEqual(self.calls(), [])

    def test_no_formatter_reports_not_run_and_exit_0(self):
        r = self.run_hook(self.edit(), fake=False)
        self.assertEqual(r.returncode, 0)
        self.assertIn("NOT-RUN", r.stdout)
        self.assertIn("nothing was installed", r.stdout)
        self.assertEqual(r.stderr, "")

    def test_formatter_crash_is_not_run_not_a_block(self):
        r = self.run_hook(self.edit(), mode="crash")
        self.assertEqual(r.returncode, 0)
        self.assertIn("NOT-RUN", r.stdout)
        self.assertIn("exit 3", r.stdout)

    def test_formatter_timeout_is_not_run(self):
        r = self.run_hook(self.edit(), mode="hang", timeout_s=1)
        self.assertEqual(r.returncode, 0)
        self.assertIn("NOT-RUN", r.stdout)
        self.assertIn("timed out", r.stdout)

    def test_bad_stdin_is_ignored(self):
        for payload in ("", "not json", "[]", json.dumps({"tool_input": "x"})):
            r = self.run_hook(payload)
            self.assertEqual(r.returncode, 0, payload)
        self.assertEqual(self.calls(), [])


class PickTest(unittest.TestCase):
    def test_prefers_gdscript_formatter_then_gdformat(self):
        found = {"gdscript-formatter": "/bin/gdscript-formatter", "gdformat": "/bin/gdformat"}
        name, argv = gf.pick_formatter({}, found.get)
        self.assertEqual(name, "gdscript-formatter")
        self.assertEqual(argv, ["/bin/gdscript-formatter", "--check"])
        name, argv = gf.pick_formatter({}, {"gdformat": "/bin/gdformat"}.get)
        self.assertEqual(name, "gdformat")
        self.assertEqual(argv, ["/bin/gdformat", "--check", "--diff"])
        self.assertEqual(gf.pick_formatter({}, {}.get), (None, None))

    def test_env_override_must_be_a_json_list(self):
        name, argv = gf.pick_formatter({"GDSCRIPT_FORMAT_CMD": '["fmt", "-q"]'}, {}.get)
        self.assertEqual(argv, ["fmt", "-q", "--check"])
        self.assertEqual(gf.pick_formatter({"GDSCRIPT_FORMAT_CMD": "fmt -q"}, {}.get), (None, None))

    def test_gdformat_exit_1_without_would_reformat_is_a_parse_failure(self):
        self.assertEqual(gf.classify("gdformat", 1, "would reformat a.gd\n"), "dirty")
        self.assertEqual(gf.classify("gdformat", 1, "Failed to format 'a.gd'"), "error")
        self.assertEqual(gf.classify("gdscript-formatter", 1, "a.gd"), "dirty")
        self.assertEqual(gf.classify("gdscript-formatter", 0, ""), "clean")
        self.assertEqual(gf.classify("gdscript-formatter", 101, "panic"), "error")


if __name__ == "__main__":
    unittest.main()
