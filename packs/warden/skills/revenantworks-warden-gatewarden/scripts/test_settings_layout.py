#!/usr/bin/env python3
"""Tests for settings_layout.py, gatewarden's read-only `layout` map (stdlib unittest).

Every fixture is built in a temp folder: a fake home with user settings, a project with tracked
and local settings, an installed plugin and a mod, and an event log. The map must find the
overlaps, rank interruptions, propose one home per rule and hook, write nothing, and never print
an env value or a hook's full command line.

Run: python -m unittest discover -s scripts -p "test_*.py"
"""
from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import settings_layout as sl  # noqa: E402

CANARY = "CANARY-" + "4b1d" + "77c02"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = sl.main(argv)
    return code, out.getvalue(), err.getvalue()


def snapshot(root: Path) -> dict:
    return {str(p): p.stat().st_mtime_ns for p in root.rglob("*")}


class Layout(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="gw-layout-"))
        self.home = self.tmp / "home"
        self.proj = self.tmp / "proj"
        (self.home / ".claude").mkdir(parents=True)
        (self.proj / ".claude").mkdir(parents=True)
        hooks_dir = "~/.claude/hooks"
        user = {
            "env": {"API_TOKEN": CANARY},
            "permissions": {"deny": ["Read(~/.ssh/**)", "Bash(git push *)"],
                            "allow": ["Bash(npm test)"]},
            "hooks": {"PreToolUse": [
                {"matcher": "Bash|PowerShell", "hooks": [{"type": "command",
                 "command": f'python "{hooks_dir}/push_gate.py" --token {CANARY}'}]},
                {"matcher": "Bash", "hooks": [{"type": "command",
                 "command": f'python "{hooks_dir}/dispatch_gate.py"'}]}]},
        }
        project = {
            "permissions": {"ask": ["Bash(npm publish *)"], "allow": ["Bash(git push origin main)", "Bash(npm test)"],
                            "deny": ["Read(./secrets/**)"]},
            "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command",
                      "command": 'python ".claude/hooks/dispatch_gate.py"'}]}]},
        }
        local = {"permissions": {"additionalDirectories": ["../shared-assets"]}}
        (self.home / ".claude" / "settings.json").write_text(json.dumps(user), encoding="utf-8")
        (self.proj / ".claude" / "settings.json").write_text(json.dumps(project), encoding="utf-8")
        (self.proj / ".claude" / "settings.local.json").write_text(json.dumps(local), encoding="utf-8")
        mod = self.home / ".claude" / "plugins" / "cache" / "mk" / "dash" / "1.0.0"
        (mod / "hooks").mkdir(parents=True)
        (mod / ".claude-plugin").mkdir()
        (mod / ".claude-plugin" / "plugin.json").write_text('{"name": "dash"}', encoding="utf-8")
        (mod / "hooks" / "hooks.json").write_text('{"hooks": {}, "modules": ["./register.tsx"]}', encoding="utf-8")
        state = self.home / ".claude" / "gatewarden"
        state.mkdir()
        now = time.time()
        rows = ([{"at": now - 60, "rule": "push_gate.no_ci", "outcome": "nudged", "session": f"s{i}"} for i in range(3)]
                + [{"at": now - 60, "rule": "heredoc_guard", "outcome": "logged", "session": "s1"} for _ in range(5)]
                + [{"at": now - 60, "rule": "push_gate.irreversible", "outcome": "blocked", "session": "s2"}]
                + [{"at": now - 90 * 86400, "rule": "call_cap", "outcome": "blocked", "session": "old"}])
        (state / "events.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\nnot json\n", encoding="utf-8")
        (state / "modes.json").write_text('{"default": "watch", "rules": {"push_gate.no_ci": "nudge"}}',
                                          encoding="utf-8")
        self.env = mock.patch.dict(os.environ, {"GATEWARDEN_STATE": "", "GATEWARDEN_EVENTS": "",
                                                "GATEWARDEN_MODES": "", "ProgramFiles": ""})
        self.env.start()
        for k in ("GATEWARDEN_STATE", "GATEWARDEN_EVENTS", "GATEWARDEN_MODES", "ProgramFiles"):
            os.environ.pop(k, None)

    def tearDown(self):
        self.env.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def layout(self):
        out = self.tmp / "map.json"
        code, text, err = run(["--home", str(self.home), "--project", str(self.proj), "--json", str(out)])
        return code, json.loads(out.read_text(encoding="utf-8")), text, err

    def test_every_level_rule_and_hook_is_mapped(self):
        code, m, text, _ = self.layout()
        self.assertEqual(code, 0)
        self.assertEqual([f["scope"] for f in m["files"]], ["local", "project", "user"])
        kinds = {(r["kind"], r["rule"]) for r in m["rules"]}
        self.assertIn(("ask", "Bash(npm publish *)"), kinds)
        self.assertIn(("directory", "../shared-assets"), kinds)
        fams = {(h["hook"], h["family"], h["scope"]) for h in m["hooks"]}
        self.assertIn(("push_gate.py", "gatewarden", "user"), fams)
        self.assertIn(("dispatch_gate.py", "dispatchwright", "project"), fams)
        self.assertEqual([p["plugin"] for p in m["plugins"] if p["mod"]], ["dash"])
        self.assertIn("proposed homes", text)

    def test_overlaps_found(self):
        _, m, _, _ = self.layout()
        got = {(o["kind"], o["rule"]) for o in m["overlaps"]}
        self.assertIn(("duplicate", "Bash(npm test)"), got)                 # user and project
        self.assertIn(("shadowed", "Bash(git push origin main)"), got)      # deny Bash(git push *) wins
        self.assertIn(("hook-twice", "dispatch_gate.py"), got)              # user and project: double-fire
        self.assertIn(("mod-beside-hook", "push_gate.py"), got)

    def test_interruptions_ranked_from_the_event_log(self):
        _, m, _, _ = self.layout()
        ev = m["events"]["rules"]
        self.assertEqual(ev[0]["rule"], "push_gate.no_ci")                  # three nudges outrank one refusal
        self.assertEqual(ev[0]["mode"], "nudge")
        self.assertEqual(ev[0]["sessions"], 3)
        hard = next(r for r in ev if r["rule"] == "push_gate.irreversible")
        self.assertEqual(hard["mode"], "guard")
        self.assertNotIn("call_cap", [r["rule"] for r in ev])               # outside the window

    def test_one_proposed_home_per_rule_and_hook(self):
        _, m, _, _ = self.layout()
        homes = {h["what"]: h for h in m["homes"]}
        self.assertEqual(len(homes), len(m["homes"]))
        self.assertEqual(homes["ask Bash(npm publish *)"]["home"], "local")
        self.assertEqual(homes["deny Read(~/.ssh/**)"]["home"], "user")
        self.assertEqual(homes["deny Read(./secrets/**)"]["home"], "project")
        self.assertEqual(homes["hook PreToolUse dispatch_gate.py"]["home"], "user")
        self.assertIn("drop the copies in project", homes["hook PreToolUse dispatch_gate.py"]["why"])
        self.assertEqual(homes["directory ../shared-assets"]["home"], "local")

    def test_writes_nothing_and_never_prints_env_or_commands(self):
        before = snapshot(self.tmp)
        code, text, err = run(["--home", str(self.home), "--project", str(self.proj)])
        self.assertEqual(code, 0)
        self.assertEqual(snapshot(self.tmp), before)
        for leak in (CANARY, "API_TOKEN", "--token", str(self.home)):
            self.assertNotIn(leak, text + err)

    def test_not_run_with_nothing_to_read(self):
        empty = self.tmp / "empty"
        empty.mkdir()
        code, _, err = run(["--home", str(empty), "--project", str(empty)])
        self.assertEqual(code, 3)
        self.assertIn("NOT-RUN", err)
        self.assertFalse((empty / ".claude").exists())                      # no state folder created

    def test_missing_settings_flag_is_input_error(self):
        code, _, _ = run(["--settings", str(self.tmp / "nope.json"), "--home", str(self.home)])
        self.assertEqual(code, 2)

    def test_runs_as_a_script(self):
        p = subprocess.run([sys.executable, str(HERE / "settings_layout.py"), "--home", str(self.home),
                            "--project", str(self.proj), "--json", "-"], capture_output=True, text=True,
                           timeout=60, creationflags=NO_WINDOW)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)["tool"], "gatewarden.settings_layout")
        self.assertNotIn(CANARY, p.stdout + p.stderr)


if __name__ == "__main__":
    unittest.main()
