#!/usr/bin/env python3
"""Tests for compact_gate.py (observation 0730: a dispatched unit wrote its findings file straight
after two auto-compactions without re-reading it).

Most cases call compact_gate.check() in-process (observation 0725: per-case process spawns dominate
the hook suites on Windows). Two run the hook as Claude Code does, to prove the exit code in guard
mode and the log-only path in watch mode.

Run: python -m unittest test_hooks_compact_gate
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _scratch import force_rmtree

HERE = Path(__file__).resolve().parent
HOOKS = HERE / "hooks"
sys.path.insert(0, str(HOOKS))
import compact_gate as cg  # noqa: E402

PY = sys.executable
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class Transcript:
    """Builds a subagent transcript (JSONL) in the shape Claude Code writes."""

    def __init__(self, path: Path):
        self.path = path
        self.lines: list[dict] = [{"type": "user", "message": {"role": "user", "content": "unit: PROOF-A brief"}}]
        self.n = 0

    def call(self, name: str, result: str | None = "ok", error: bool = False, **inp) -> str:
        self.n += 1
        tid = f"toolu_{self.n:03d}"
        self.lines.append({"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "tool_use", "id": tid, "name": name, "input": inp}]}})
        if result is not None:
            self.lines.append({"type": "user", "message": {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": tid, "content": result, "is_error": error}]}})
        return tid

    def compact(self, pre: int = 153888) -> None:
        self.lines.append({"type": "system", "subtype": "compact_boundary", "content": "Conversation compacted",
                           "compactMetadata": {"trigger": "auto", "preTokens": pre}})
        self.lines.append({"type": "user", "isCompactSummary": True, "message": {"role": "user", "content":
                           "Summary: the unit was writing findings.md and its brief REVIEW-ADV.md."}})

    def save(self) -> str:
        self.path.write_text("\n".join(json.dumps(x) for x in self.lines) + "\n", encoding="utf-8")
        return str(self.path)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="gw-compact-"))
        self.state = self.tmp / "state"
        self._env = {k: os.environ.get(k) for k in ("GATEWARDEN_STATE", "GATEWARDEN_MODE")}
        os.environ["GATEWARDEN_STATE"] = str(self.state)
        self.work = self.tmp / "run"
        self.work.mkdir()
        self.findings = self.work / "findings.md"
        self.findings.write_text("# Findings\n- MED 1\n", encoding="utf-8")
        self.brief = self.work / "brief.md"
        self.brief.write_text("# Brief\n", encoding="utf-8")
        self.t = Transcript(self.tmp / "agent-a1.jsonl")

    def tearDown(self):
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        force_rmtree(str(self.tmp))

    def event(self, tool: str = "Write", path: str | None = None, agent: str | None = "a1",
              tool_use_id: str | None = None, **extra) -> dict:
        key = "notebook_path" if tool == "NotebookEdit" else "file_path"
        ev = {"session_id": "s1", "hook_event_name": "PreToolUse", "tool_name": tool,
              "tool_input": {key: path or str(self.findings)}, "cwd": str(self.work),
              "agent_transcript_path": self.t.save()}
        if agent:
            ev["agent_id"], ev["agent_type"] = agent, "opus-high"
        if tool_use_id:
            ev["tool_use_id"] = tool_use_id
        ev.update(extra)
        return ev

    def blocked(self, ev: dict, msg: str = "") -> None:
        self.assertIsNotNone(cg.check(ev), msg or "expected the gate to refuse")

    def passed(self, ev: dict, msg: str = "") -> None:
        self.assertIsNone(cg.check(ev), msg or "expected the gate to allow")


class Observation0730(Base):
    """The two writes the proof caught, each with its positive control."""

    def test_write_after_compaction_without_reread_refused(self):  # boundary 1: call 36, a full Write
        self.t.call("Read", file_path=str(self.brief))
        self.t.call("Read", file_path=str(self.findings))
        self.t.call("Write", file_path=str(self.findings), content="x")
        self.t.compact(153888)
        for _ in range(10):
            self.t.call("Grep", pattern="def ")
        self.blocked(self.event("Write"))

    def test_edit_straight_after_compaction_refused(self):  # boundary 2: call 61, an Edit
        self.t.call("Read", file_path=str(self.findings))
        self.t.compact(152077)
        self.blocked(self.event("Edit"))

    def test_reread_after_compaction_allows_write(self):  # control: the re-read the brief asked for
        self.t.call("Read", file_path=str(self.findings))
        self.t.compact()
        self.t.call("Read", file_path=str(self.findings))
        self.passed(self.event("Write"))
        self.passed(self.event("Edit"))

    def test_reason_names_the_summary(self):
        self.t.compact()
        reason = cg.check(self.event("Edit")) or ""
        self.assertIn("compact", reason.lower())
        self.assertIn("summary is not a re-read", reason)


class Scope(Base):
    def test_main_session_never_gated(self):
        self.t.compact()
        self.passed(self.event("Write", agent=None))

    def test_no_compaction_no_gate(self):
        self.t.call("Grep", pattern="x")
        self.passed(self.event("Write"))
        self.passed(self.event("Edit"))

    def test_other_tools_pass(self):
        self.t.compact()
        for tool in ("Read", "Bash", "Grep", "Agent"):
            self.passed(self.event(tool), tool)

    def test_new_file_passes(self):  # nothing on disk the summary could have dropped
        self.t.compact()
        self.passed(self.event("Write", path=str(self.work / "new-report.md")))

    def test_notebook_edit_gated(self):
        nb = self.work / "a.ipynb"
        nb.write_text("{}", encoding="utf-8")
        self.t.compact()
        self.blocked(self.event("NotebookEdit", path=str(nb)))
        self.t.call("Read", file_path=str(nb))
        self.passed(self.event("NotebookEdit", path=str(nb)))

    def test_multiedit_gated(self):
        self.t.compact()
        self.blocked(self.event("MultiEdit"))


class WhatCountsAsARead(Base):
    def test_read_before_the_boundary_does_not_count(self):
        self.t.call("Read", file_path=str(self.findings))
        self.t.compact()
        self.blocked(self.event("Edit"))

    def test_read_between_two_boundaries_does_not_count(self):
        self.t.compact(153888)
        self.t.call("Read", file_path=str(self.findings))
        self.t.compact(152077)
        self.blocked(self.event("Edit"))

    def test_read_of_another_file_does_not_count(self):
        self.t.compact()
        self.t.call("Read", file_path=str(self.brief))
        self.blocked(self.event("Edit"))

    def test_failed_read_does_not_count(self):
        self.t.compact()
        self.t.call("Read", result="File does not exist.", error=True, file_path=str(self.findings))
        self.blocked(self.event("Edit"))

    def test_partial_read_counts(self):
        self.t.compact()
        self.t.call("Read", file_path=str(self.findings), offset=1, limit=20)
        self.passed(self.event("Edit"))

    def test_read_in_the_same_batch_counts(self):  # parallel calls: the Read's result is not written yet
        self.t.compact()
        self.t.call("Read", result=None, file_path=str(self.findings))
        tid = self.t.call("Edit", result=None, file_path=str(self.findings))
        self.passed(self.event("Edit", tool_use_id=tid))

    def test_failed_write_does_not_count(self):  # a refused Write put nothing on disk
        self.t.compact()
        self.t.call("Write", result="refused", error=True, file_path=str(self.findings), content="new")
        self.blocked(self.event("Edit"))

    def test_successful_write_after_boundary_then_edit_passes(self):
        new = self.work / "made-after.md"
        self.t.compact()
        self.t.call("Write", file_path=str(new), content="a")
        new.write_text("a", encoding="utf-8")
        self.passed(self.event("Edit", path=str(new)))

    def test_pending_write_does_not_count(self):  # the call being gated is in the transcript already
        self.t.compact()
        tid = self.t.call("Write", result=None, file_path=str(self.findings), content="x")
        self.blocked(self.event("Write", tool_use_id=tid))

    def test_path_spelling_matches(self):  # Windows forms: separators and case
        self.t.compact()
        self.t.call("Read", file_path=str(self.findings).replace(os.sep, "\\").upper())
        self.passed(self.event("Edit", path=str(self.findings).replace("\\", "/")))

    def test_relative_path_resolves_from_cwd(self):
        self.t.compact()
        self.t.call("Read", file_path=str(self.findings))
        self.passed(self.event("Edit", path="findings.md"))


class FailOpen(Base):
    def test_no_transcript_allows(self):
        self.t.compact()
        ev = self.event("Edit")
        ev["agent_transcript_path"] = str(self.tmp / "missing.jsonl")
        self.passed(ev)

    def test_garbled_lines_skipped(self):
        self.t.compact()
        ev = self.event("Edit")  # writes the transcript
        with open(self.t.path, "a", encoding="utf-8") as fh:
            fh.write("not json\n[1, 2]\n{\"type\": 3}\n")
        self.blocked(ev)

    def test_transcript_found_from_session_path(self):  # no agent_transcript_path in the event
        sess = self.tmp / "sess.jsonl"
        sess.write_text("", encoding="utf-8")
        sub = self.tmp / "sess" / "subagents"
        sub.mkdir(parents=True)
        self.t.path = sub / "agent-a1.jsonl"
        self.t.compact()
        ev = self.event("Edit")
        ev.pop("agent_transcript_path")
        ev["transcript_path"] = str(sess)
        self.blocked(ev)


class AsClaudeCodeRunsIt(Base):
    def run_hook(self, ev: dict, mode: str):
        env = {**os.environ, "GATEWARDEN_STATE": str(self.state), "GATEWARDEN_MODE": mode,
               "GATEWARDEN_MODES": str(self.tmp / "no-modes.json")}
        return subprocess.run([PY, str(HOOKS / "compact_gate.py")], input=json.dumps(ev), text=True,
                              capture_output=True, env=env, creationflags=NO_WINDOW, timeout=60)

    def test_guard_mode_refuses_with_exit_2(self):
        self.t.compact()
        p = self.run_hook(self.event("Edit"), "guard")
        self.assertEqual(p.returncode, 2, p.stderr)
        self.assertIn("compact_gate", p.stderr)
        events = (self.state / "events.jsonl").read_text(encoding="utf-8")
        self.assertIn('"rule": "compact_gate"', events)
        self.assertNotIn(str(self.findings), events)  # never a path in the log

    def test_watch_mode_logs_and_lets_it_run(self):
        self.t.compact()
        p = self.run_hook(self.event("Edit"), "watch")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn('"outcome": "logged"', (self.state / "events.jsonl").read_text(encoding="utf-8"))

    def test_guard_mode_allows_after_reread(self):
        self.t.compact()
        self.t.call("Read", file_path=str(self.findings))
        p = self.run_hook(self.event("Edit"), "guard")
        self.assertEqual(p.returncode, 0, p.stderr)

    def test_bad_stdin_allows(self):
        env = {**os.environ, "GATEWARDEN_STATE": str(self.state), "GATEWARDEN_MODE": "guard"}
        p = subprocess.run([PY, str(HOOKS / "compact_gate.py")], input="not json", text=True,
                           capture_output=True, env=env, creationflags=NO_WINDOW, timeout=60)
        self.assertEqual(p.returncode, 0, p.stderr)


if __name__ == "__main__":
    unittest.main()
