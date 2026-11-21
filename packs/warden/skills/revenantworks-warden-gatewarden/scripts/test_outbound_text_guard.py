#!/usr/bin/env python3
"""Tests for outbound_text_guard.py (observation 0561). Stdlib unittest; the hook runs as a
subprocess with a JSON event on stdin, and the names list is a temp file with a made-up entry.

Run: python -m unittest discover -s scripts -p "test_*.py"
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "hooks" / "outbound_text_guard.py"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
ENTRY = "Zorvexa"   # a made-up names-list entry, never a real one


class OutboundTextGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="gw-otg-")
        self.names = os.path.join(self.tmp.name, "wordlist.txt")
        Path(self.names).write_text("# test list\n" + ENTRY + "\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def run_hook(self, tool, tool_input, names=True):
        env = {k: v for k, v in os.environ.items() if not k.startswith("GATEWARDEN_")}
        env.update({"GATEWARDEN_MODE": "watch", "GATEWARDEN_STATE": self.tmp.name,
                    "WARDEN_NAMES_FILE": self.names if names else os.path.join(self.tmp.name, "absent.txt")})
        ev = {"session_id": "s1", "hook_event_name": "PreToolUse", "tool_name": tool,
              "tool_input": tool_input, "cwd": self.tmp.name}
        p = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(ev), capture_output=True,
                           text=True, encoding="utf-8", env=env, timeout=60, creationflags=NO_WINDOW)
        return p.returncode, p.stdout, p.stderr

    def test_pr_body_with_entry_is_refused_in_any_mode(self):
        code, _, err = self.run_hook("Bash", {"command": f'gh pr create --title t --body "by {ENTRY.lower()}"'})
        self.assertEqual(code, 2)
        self.assertNotIn(ENTRY.lower(), err.lower())   # the refusal never prints the entry

    def test_heredoc_body_is_read(self):
        cmd = f"gh pr comment 4 --body-file - <<'EOF'\nthanks {ENTRY}\nEOF"
        self.assertEqual(self.run_hook("Bash", {"command": cmd})[0], 2)

    def test_body_file_is_read(self):
        Path(self.tmp.name, "body.md").write_text(f"Requested by {ENTRY}\n", encoding="utf-8")
        self.assertEqual(self.run_hook("Bash", {"command": "gh pr create --title t --body-file body.md"})[0], 2)

    def test_clean_pr_and_other_commands_pass(self):
        self.assertEqual(self.run_hook("Bash", {"command": "gh pr create --title t --body 'the owner'"})[0], 0)
        self.assertEqual(self.run_hook("Bash", {"command": f"grep -rn {ENTRY} notes.md"})[0], 0)
        self.assertEqual(self.run_hook("Bash", {"command": f"gh pr view 4 --json body # {ENTRY}"})[0], 0)

    def test_word_boundary(self):
        self.assertEqual(self.run_hook("Bash", {"command": f"gh issue create --body x{ENTRY}y"})[0], 0)

    def test_mcp_writer_is_checked(self):
        code, _, _ = self.run_hook("mcp__github__create_pull_request",
                                   {"owner": "o", "repo": "r", "title": "t", "body": f"cc {ENTRY}"})
        self.assertEqual(code, 2)
        code, _, _ = self.run_hook("mcp__github-revenantworks__push_files",
                                   {"files": [{"path": "a.md", "content": f"{ENTRY} wrote this"}]})
        self.assertEqual(code, 2)
        self.assertEqual(self.run_hook("mcp__github__get_file_contents", {"path": ENTRY})[0], 0)

    def test_missing_list_allows_with_a_warning(self):
        code, out, _ = self.run_hook("Bash", {"command": f"gh pr create --body {ENTRY}"}, names=False)
        self.assertEqual(code, 0)
        self.assertIn("not checked", out)


if __name__ == "__main__":
    unittest.main()
