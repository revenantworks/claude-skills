#!/usr/bin/env python3
"""Tests for call_cap.py's event log and cap_review.py's classifier. Stdlib only.

Fixtures are built in each test: a looping agent, a steadily progressing agent and an
unclear one, driven through the real hook so the log is the one the hook writes.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "hooks"))
import cap_review as cr  # noqa: E402

PY = sys.executable
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
SECRET = "do-not-log-this-value-7Q2"


def run(script: Path, stdin: str = "", args: list | None = None, env: dict | None = None):
    full = {k: v for k, v in os.environ.items() if not k.startswith("GATEWARDEN_")}
    full.update(env or {})
    p = subprocess.run([PY, str(script), *(args or [])], input=stdin, capture_output=True, text=True,
                       env=full, timeout=60, creationflags=NO_WINDOW)
    return p.returncode, p.stdout, p.stderr


def write_transcript(path: Path, prompt: str, calls: list[tuple]) -> None:
    """calls: (tool name, input, is_error, result text)."""
    lines = [{"type": "user", "timestamp": "2026-10-02T10:00:00Z", "message": {"role": "user", "content": prompt}}]
    for i, (name, ti, err, text) in enumerate(calls):
        tid = f"t{i}"
        lines.append({"type": "assistant", "timestamp": "2026-10-02T10:00:%02dZ" % min(i, 59),
                      "message": {"content": [{"type": "tool_use", "id": tid, "name": name, "input": ti}]}})
        lines.append({"type": "user", "timestamp": "2026-10-02T10:01:%02dZ" % min(i, 59),
                      "message": {"content": [{"type": "tool_result", "tool_use_id": tid, "is_error": err,
                                               "content": text}]}})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(x) for x in lines) + "\n", encoding="utf-8")


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="gw-capreview-"))
        self.state = self.tmp / "state"
        self.state.mkdir()
        (self.state / "call-caps.json").write_text(json.dumps(
            {"by_agent_type": {"worker": 5}, "grace": 1, "warn_at": 0.6}))
        self.env = {"GATEWARDEN_STATE": str(self.state), "GATEWARDEN_MODE": "guard"}

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def call(self, agent: str, tool: str, ti: dict, atype: str = "worker", session: str = "s1"):
        ev = {"session_id": session, "hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": ti,
              "agent_id": agent, "agent_type": atype}
        return run(HERE / "hooks" / "call_cap.py", json.dumps(ev), env=self.env)

    def stop(self, agent: str, transcript: Path | None = None, atype: str = "worker"):
        ev = {"session_id": "s1", "hook_event_name": "SubagentStop", "agent_id": agent, "agent_type": atype,
              "stop_hook_active": False}
        if transcript:
            ev["agent_transcript_path"] = str(transcript)
        return run(HERE / "hooks" / "call_cap.py", json.dumps(ev), env=self.env)

    def events(self) -> list[dict]:
        p = self.state / "call-cap-events.jsonl"
        return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines()] if p.exists() else []

    def review(self, *args):
        code, out, err = run(HERE / "cap_review.py", args=["--state", str(self.state), "--json", *args], env=self.env)
        self.assertEqual(code, 0, err)
        return json.loads(out)

    # the three fixture agents
    def looping(self, agent="loop1"):
        for _ in range(8):
            self.call(agent, "Bash", {"command": f"pytest -k one  # {SECRET}"})

    def steady(self, agent="steady1"):
        for i in range(8):
            tool = ("Read", "Edit", "Write", "Bash")[i % 4]
            self.call(agent, tool, {"file_path": f"f{i}.py", "old_string": str(i), "new_string": str(i + 1),
                                    "command": f"step {i}"})

    def unclear(self, agent="vague1"):
        for i in range(8):
            self.call(agent, ("Read", "Grep")[i % 2], {"file_path": f"doc{i}.md", "pattern": f"p{i}"})


class EventLogTests(Base):
    def test_warn_cap_and_block_are_logged_once_each(self):
        codes = [self.call("a1", "Read", {"file_path": f"x{i}"})[0] for i in range(8)]
        self.assertEqual(codes, [0, 0, 0, 0, 0, 0, 2, 2])
        kinds = [e["event"] for e in self.events()]
        self.assertEqual(kinds, ["warn", "cap", "block", "block"])
        blk = self.events()[2]
        for key in ("ts", "session", "agent_id", "agent_type", "count", "cap", "grace", "tool", "sig", "recent"):
            self.assertIn(key, blk)
        self.assertEqual((blk["count"], blk["cap"], blk["grace"], blk["tool"]), (7, 5, 1, "Read"))
        self.assertEqual(len(blk["recent"]), 7)
        self.assertTrue(blk["sig"].startswith("Read#"))

    def test_block_lines_stop_after_three(self):
        for _ in range(12):
            self.call("a1", "Read", {"file_path": "x"})
        self.assertEqual(sum(e["event"] == "block" for e in self.events()), 3)

    def test_input_is_hashed_never_logged(self):
        self.looping()
        text = (self.state / "call-cap-events.jsonl").read_text(encoding="utf-8")
        self.assertNotIn(SECRET, text)
        self.assertNotIn("pytest", text)
        for f in self.state.glob("count-*"):
            self.assertNotIn(SECRET, f.read_text(encoding="utf-8"))

    def test_ring_keeps_the_last_thirty(self):
        (self.state / "call-caps.json").write_text(json.dumps({"by_agent_type": {"worker": 100}}))
        for i in range(40):
            self.call("a1", "Read", {"file_path": f"x{i}"})
        rec = json.loads(next(self.state.glob("count-*")).read_text())
        self.assertEqual(len(rec["ring"]), 30)

    def test_rereads_and_reverted_edits_are_counted(self):
        (self.state / "call-caps.json").write_text(json.dumps({"by_agent_type": {"worker": 100}}))
        for _ in range(4):
            self.call("a1", "Read", {"file_path": "same.py"})
        self.call("a1", "Edit", {"file_path": "m.py", "old_string": "a", "new_string": "b"})
        self.call("a1", "Edit", {"file_path": "m.py", "old_string": "b", "new_string": "a"})
        rec = json.loads(next(self.state.glob("count-*")).read_text())
        self.assertEqual((rec["rereads"], rec["reread_max"], rec["reverts"]), (2, 4, 1))

    def test_subagent_stop_logs_one_end_line_from_the_transcript(self):
        t = self.tmp / "proj" / "sess" / "subagents" / "agent-e1.jsonl"
        prompt = f"You are unit CCR.\nbrief: some/where/CCR-brief.md\n{SECRET}"
        write_transcript(t, prompt, [
            ("Skill", {"skill": "demo-skill"}, False, "ok"),
            ("Write", {"file_path": "a.py"}, False, "ok"),
            ("Bash", {"command": "x"}, True, "boom"),
            ("Bash", {"command": "y"}, True, "boom"),
            ("Bash", {"command": "cat <<EOF"}, True,
             'PreToolUse:Bash hook error: [python "h/heredoc_guard.py"]: heredoc guard: no'),
            ("Bash", {"command": "git commit -m z"}, False, "ok")])
        for i in range(3):
            self.call("e1", "Read", {"file_path": f"r{i}"})
        code, out, _ = self.stop("e1", t)
        self.assertEqual((code, out.strip()), (0, ""))
        self.stop("e1", t)  # a second stop for the same agent adds nothing
        ends = [e for e in self.events() if e["event"] == "end"]
        self.assertEqual(len(ends), 1)
        e = ends[0]
        self.assertEqual((e["calls"], e["errors"], e["max_error_run"], e["writes"], e["unit"]),
                         (3, 3, 3, 2, "CCR-brief"))
        self.assertEqual(e["hook_blocks"], {"heredoc_guard": 1})
        self.assertEqual(e["skills"], ["demo-skill"])
        self.assertEqual(e["duration_s"], 65)
        self.assertEqual(len(e["prompt_hash"]), 12)
        raw = (self.state / "call-cap-events.jsonl").read_text(encoding="utf-8")
        self.assertNotIn(SECRET, raw)
        self.assertNotIn("You are unit", raw)
        self.assertNotIn("some/where", raw)

    def test_unit_id_from_a_unit_line_or_a_you_are_line(self):
        import call_cap as cc
        self.assertEqual(cc.unit_of("intro\nunit: W3-T02\nmore"), "W3-T02")
        self.assertEqual(cc.unit_of("You are unit A3 of run x"), "A3")
        self.assertIsNone(cc.unit_of("no id here"))

    def test_stop_without_a_transcript_still_logs_totals(self):
        for i in range(2):
            self.call("e2", "Read", {"file_path": f"r{i}"})
        self.stop("e2")
        e = [x for x in self.events() if x["event"] == "end"][0]
        self.assertEqual(e["calls"], 2)
        self.assertNotIn("errors", e)

    def test_log_is_skipped_inside_a_git_work_tree(self):
        (self.tmp / ".git").mkdir()
        self.looping()
        self.assertEqual(self.events(), [])
        self.assertEqual(self.call("loop1", "Bash", {"command": "again"})[0], 2)  # the cap still binds

    def test_main_session_is_never_logged(self):
        for _ in range(8):
            run(HERE / "hooks" / "call_cap.py", json.dumps({"session_id": "s1", "tool_name": "Read",
                                                            "tool_input": {}}), env=self.env)
        self.assertEqual(self.events(), [])


class ClassifierTests(Base):
    def test_the_three_fixture_agents(self):
        self.looping()
        self.steady()
        self.unclear()
        res = self.review()
        verdicts = {b["agent_id"]: b["verdict"] for b in res["blocks"]}
        self.assertEqual(verdicts, {"loop1": "runaway", "steady1": "premature", "vague1": "unclear"})
        loop = next(b for b in res["blocks"] if b["agent_id"] == "loop1")
        self.assertIn("repeated", " ".join(loop["evidence"]))
        self.assertEqual(loop["target_skill"], "dispatchwright")

    def test_premature_proposes_a_complete_caps_file(self):
        self.steady()
        res = self.review()
        prop = res["proposal"]
        self.assertEqual(prop["by_agent_type"]["worker"], 9)  # ceil(7 x 1.25)
        self.assertEqual(prop["grace"], 1)                      # the rest of the file is kept
        self.assertEqual(json.loads((self.state / "call-caps.json").read_text())["by_agent_type"]["worker"], 5)

    def test_runaway_alone_proposes_nothing(self):
        self.looping()
        self.assertIsNone(self.review()["proposal"])

    def test_transcript_error_run_makes_a_runaway(self):
        self.steady("err1")
        t = self.tmp / "tx" / "agent-err1.jsonl"
        write_transcript(t, "unit: E1", [("Write", {"file_path": "w"}, False, "ok")]
                         + [("Bash", {"command": f"c{i}"}, True, "fail") for i in range(5)]
                         + [("Bash", {"command": "late"}, True, "after the block: cut by the limit")])
        res = self.review("--transcripts", str(self.tmp / "tx"))
        b = res["blocks"][0]
        self.assertEqual(b["verdict"], "runaway")
        self.assertIn("error run", " ".join(b["evidence"]))
        self.assertEqual(b["unit"], "E1")

    def test_classify_rules_directly(self):
        self.assertEqual(cr.classify(["Bash#a"] * 12, None)[0], "runaway")
        self.assertEqual(cr.classify(["Bash#a", "Read#b", "Grep#c"] * 4, None)[0], "runaway")
        self.assertEqual(cr.classify([f"Edit#{i}" for i in range(12)], None)[0], "premature")
        self.assertEqual(cr.classify([f"Read#{i}" for i in range(12)], None)[0], "unclear")
        stall = {"writes": 3, "calls_since_write": 30, "max_error_run": 0}
        self.assertEqual(cr.classify([f"Read#{i}" for i in range(12)], stall)[0], "runaway")

    def test_data_driven_caps_need_twenty_finished_units(self):
        lines = [{"event": "end", "session": "s", "agent_id": f"u{i}", "agent_type": "worker", "calls": 10 + i,
                  "recent": [f"Edit#{i}-{k}" for k in range(12)], "errors": 0, "max_error_run": 0,
                  "writes": 5, "calls_since_write": 1} for i in range(20)]
        lines.append({"event": "end", "session": "s", "agent_id": "bad", "agent_type": "worker", "calls": 400,
                      "recent": ["Bash#x"] * 12})
        log = self.state / "call-cap-events.jsonl"
        log.write_text("\n".join(json.dumps(x) for x in lines[:19]) + "\n")
        self.assertIsNone(self.review()["proposal"])
        log.write_text("\n".join(json.dumps(x) for x in lines) + "\n")
        self.assertEqual(self.review()["proposal"]["by_agent_type"]["worker"], 37)  # ceil(29 x 1.25), runaway left out

    def test_out_refuses_a_work_tree_and_the_live_file(self):
        self.steady()
        repo = self.tmp / "repo"
        (repo / ".git").mkdir(parents=True)
        code, _, err = run(HERE / "cap_review.py", args=["--state", str(self.state), "--out", str(repo / "c.json")],
                           env=self.env)
        self.assertEqual(code, 2)
        self.assertIn("work tree", err)
        code, _, err = run(HERE / "cap_review.py", args=["--state", str(self.state), "--out",
                                                         str(self.state / "call-caps.json")], env=self.env)
        self.assertEqual(code, 2)
        self.assertIn("live caps", err)
        ok = self.tmp / "proposed.json"
        code, _, _ = run(HERE / "cap_review.py", args=["--state", str(self.state), "--out", str(ok)], env=self.env)
        self.assertEqual((code, json.loads(ok.read_text())["by_agent_type"]["worker"]), (0, 9))

    def test_no_log_is_not_run(self):
        code, out, _ = run(HERE / "cap_review.py", args=["--state", str(self.state)], env=self.env)
        self.assertEqual(code, 3)
        self.assertIn("NOT-RUN", out)

    def test_markdown_report_names_each_block(self):
        self.looping()
        self.steady()
        code, out, _ = run(HERE / "cap_review.py", args=["--state", str(self.state)], env=self.env)
        self.assertEqual(code, 0)
        self.assertIn("| loop1 |", out)
        self.assertIn("**runaway**", out)
        self.assertIn("Complete call-caps.json", out)


if __name__ == "__main__":
    unittest.main()
