"""Tests for the owner-override band of dispatch_ledger_guard (owner 2026-10-14).

Run: python -m unittest discover -s .claude/hooks -p "test_*.py"

The band: a launch at or above the stop band is refused, unless the call carries the phrase
`owner-override` AND the window is below HARD_CEILING_PCT (99). At or above 99 nothing passes.
"""
import importlib.util
import json
import os
import tempfile
import time
import unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "dispatch_ledger_guard.py"


def load_hook():
    spec = importlib.util.spec_from_file_location("dispatch_ledger_guard_under_test", HOOK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class OwnerOverrideBand(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.g = load_hook()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.ledger = self.dir / "ledger.md"
        self.ledger.write_text("# ledger\n", encoding="utf-8")
        saved = {k: os.environ.get(k) for k in ("DISPATCH_BUDGET_FILE",)}
        os.environ["DISPATCH_BUDGET_FILE"] = str(self.dir / "no-budget.json")

        def restore():
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
        self.addCleanup(restore)

    def windows(self, five):
        p = self.dir / "windows.json"
        p.write_text(json.dumps({
            "written_at": time.time(),
            "five_hour": {"used_percentage": five, "resets_at": 1738425600},
            "seven_day": {"used_percentage": 10, "resets_at": 1738857600},
        }), encoding="utf-8")
        return p

    @staticmethod
    def call(prompt):
        return {"tool_name": "Task", "session_id": "abc",
                "tool_input": {"description": "verify findings", "prompt": prompt}}

    def step(self, five, prompt):
        return self.g.window_step(self.ledger, self.call(prompt), fixture_windows=self.windows(five))

    def test_hard_ceiling_is_99(self):
        self.assertEqual(self.g.HARD_CEILING_PCT, 99.0)

    def test_is_owner_override_reads_the_phrase(self):
        self.assertTrue(self.g.is_owner_override(self.call("go on, owner-override")))
        self.assertTrue(self.g.is_owner_override(self.call("OWNER-OVERRIDE")))
        self.assertFalse(self.g.is_owner_override(self.call("an owner override of sorts")))
        self.assertFalse(self.g.is_owner_override({"tool_input": "owner-override"}))
        self.assertFalse(self.g.is_owner_override({}))

    def test_stop_band_blocks_without_the_phrase(self):
        code, reason, _ = self.step(97.5, "check the findings")
        self.assertEqual(code, 2)
        self.assertIn("97.5% used", reason)

    def test_override_passes_the_stop_band_below_the_ceiling(self):
        code, reason, ctx = self.step(97.5, "check the findings owner-override")
        self.assertEqual(code, 0)
        self.assertIsNone(reason)
        self.assertIn("OWNER OVERRIDE", ctx)

    def test_override_cannot_pass_the_hard_ceiling(self):
        for pct in (99, 99.5, 100):
            code, reason, _ = self.step(pct, "check the findings owner-override")
            self.assertEqual(code, 2, f"override passed at {pct}%")
            self.assertIn("used", reason)


class LaunchMessages(unittest.TestCase):
    """Observations 0613, 0627, 0642, 0675, 0702, 0709 (observer review 2026-11-20)."""

    @classmethod
    def setUpClass(cls):
        cls.g = load_hook()
        spec = importlib.util.spec_from_file_location("dispatch_gate_under_test", HOOK.parent / "dispatch_gate.py")
        cls.gate = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.gate)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def ledger(self, rows, v2=False, header="| unit_id | task | class | model | effort | surface | repo | dispatch_ts | status |"):
        run = self.dir / ".dispatch" / "runs" / "2026-11-20-x"
        run.mkdir(parents=True, exist_ok=True)
        p = run / "ledger.md"
        sep = "|" + "---|" * (header.count("|") - 1)
        p.write_text(("ledger: v2\n\n" if v2 else "") + "\n".join([header, sep] + rows) + "\n", encoding="utf-8")
        return p

    @staticmethod
    def call(prompt):
        return {"tool_name": "Agent", "session_id": "abc", "tool_input": {"prompt": prompt}}

    def test_0627_unit_at_line_start_binds_its_row(self):
        p = self.ledger(["| W2-KES | read | judgment | Opus 5.5 | high | subagent (background) | — | 2026-11-20 10:00Z | dispatched |"])
        self.assertEqual(self.g.launch_unit_id(self.call("Unit W2-KES (read-only on the repo). Read x."), p), "W2-KES")
        self.assertIsNone(self.g.launch_unit_id(self.call("Unit tests pass on main."), p))

    def test_0675_untiered_cell_is_named(self):
        p = self.ledger(["| U1 | t | judgment | opus | high | subagent (background) | — | 2026-11-20 10:00Z | dispatched |"])
        self.assertFalse(self.g.ledger_has_populated_row(p))
        cells = self.g.untiered_cells(p)
        self.assertEqual(len(cells), 1)
        self.assertIn("model 'opus'", cells[0])
        self.assertIn("Opus 5.5", cells[0])

    def test_0675_brief_path_names_its_run_ledger(self):
        p = self.ledger(["| U1 | t | judgment | Opus 5.5 | high | subagent (background) | — | 2026-11-20 10:00Z | dispatched |"])
        brief = (self.dir / ".dispatch" / "runs" / "2026-11-20-x" / "brief.md").as_posix()
        run_id, found = self.g.named_run(self.call(f"Ledger row U1. Read {brief} first."))
        self.assertEqual(run_id, "2026-11-20-x")
        self.assertEqual(found, p)
        self.assertEqual(self.g.named_run(self.call("Unit U1 of run 2026-11-03-lab."))[0], "2026-11-03-lab")
        self.assertIn("Wrong ledger", self.g.wrong_ledger_note("2026-11-03-lab", p))
        self.assertEqual(self.g.wrong_ledger_note("2026-11-20-x", p), "")

    def test_0642_v2_missing_status_column_names_the_header(self):
        p = self.ledger(["| U1 | t | judgment | Opus 5.5 | high | subagent (background) | — | 2026-11-20 10:00Z |"],
                        v2=True, header="| unit_id | task | class | model | effort | surface | repo | dispatch_ts |")
        problems = self.g.v2_row_problems(p)
        self.assertTrue(any("no estimated_tokens, status column" in x and "| unit_id |" in x for x in problems), problems)

    def test_0702_qualified_status_gets_the_bare_word_hint(self):
        p = self.ledger(["| U1 | t | judgment | Opus 5.5 | high | subagent (background) | — | 2026-11-20 10:00Z | dispatched (unfitted, owner go) |"])
        why = self.g.unit_row_problem(p, "U1")
        self.assertIn("bare word", why)

    def test_0709_dispatch_ts_ahead_of_the_clock_is_refused(self):
        now = 1_800_000_000  # a fixed clock
        stamp = lambda s: time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(s))  # noqa: E731
        self.assertIsNone(self.g.dispatch_ts_problem({"dispatch_ts": stamp(now - 60)}, True, now))
        self.assertIsNone(self.g.dispatch_ts_problem({"dispatch_ts": stamp(now + 60)}, True, now))
        self.assertIn("ahead of the clock", self.g.dispatch_ts_problem({"dispatch_ts": stamp(now + 600)}, True, now))
        self.assertIn("empty", self.g.dispatch_ts_problem({"dispatch_ts": "—"}, True, now))
        self.assertIsNone(self.g.dispatch_ts_problem({"dispatch_ts": "—"}, False, now))
        self.assertIsNone(self.g.dispatch_ts_problem({"status": "dispatched"}, True, now))

    def test_0613_gate_ignores_words_inside_a_task_notification(self):
        patterns = self.gate.load_patterns()
        handback = "<task-notification><result>I checked every repo and everything is fine.</result></task-notification>"
        self.assertIsNone(self.gate.first_match(self.gate.strip_harness_blocks(handback), patterns))
        owner = "I want to do a complete estate sweep, run that routine but also lets analyze every skill, project, routine"
        self.assertIsNotNone(self.gate.first_match(self.gate.strip_harness_blocks(owner + "\n" + handback), patterns))


class LaunchRootFallback(unittest.TestCase):
    """Observation 0735: a unit in a worktree (a `.git` FILE, no live `.dispatch`) or in a clone
    that is not the launch root found a stale ledger or none. After the cwd walk finds nothing
    current, the guard reads the launch-root pointer (`~/.dispatch/ledger-path`, overridable by
    CLAUDE_DISPATCH_HOME_POINTER), in the same one-line format as the per-dir pointer."""

    @classmethod
    def setUpClass(cls):
        cls.g = load_hook()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        keys = ("CLAUDE_DISPATCH_HOME_POINTER", "CLAUDE_DISPATCH_LEDGER", "CLAUDE_DISPATCH_ROOTS")
        saved = {k: os.environ.get(k) for k in keys}
        for k in keys:
            os.environ.pop(k, None)

        def restore():
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
        self.addCleanup(restore)
        # The launch root holds the live run.
        run = self.dir / "launch-root" / ".dispatch" / "runs" / "2026-11-26-live"
        run.mkdir(parents=True)
        self.live = run / "ledger.md"
        self.live.write_text("| unit_id | model | effort | surface | status |\n|---|---|---|---|---|\n"
                             "| U1 | Claude Opus 5.5 | high | subagent (background) | dispatched |\n", encoding="utf-8")
        self.pointer = self.dir / "home" / ".dispatch" / "ledger-path"
        self.pointer.parent.mkdir(parents=True)
        self.pointer.write_text(str(self.live) + "\n", encoding="utf-8")
        # A worktree: `.git` is a file, and no `.dispatch` of its own.
        self.worktree = self.dir / "wt"
        (self.worktree / "sub").mkdir(parents=True)
        (self.worktree / ".git").write_text("gitdir: elsewhere\n", encoding="utf-8")

    def test_worktree_with_no_dispatch_finds_the_launch_root_ledger(self):
        os.environ["CLAUDE_DISPATCH_HOME_POINTER"] = str(self.pointer)
        self.assertEqual(self.g.find_ledger(str(self.worktree / "sub"), "abc"), self.live)

    def test_stale_worktree_ledger_falls_through_to_the_launch_root(self):
        old = self.worktree / ".dispatch" / "runs" / "2026-11-01-old" / "ledger.md"
        old.parent.mkdir(parents=True)
        old.write_text(self.live.read_text(encoding="utf-8"), encoding="utf-8")
        ancient = time.time() - self.g.STALE_SECONDS - 3600
        os.utime(old, (ancient, ancient))
        os.environ["CLAUDE_DISPATCH_HOME_POINTER"] = str(self.pointer)
        self.assertEqual(self.g.find_ledger(str(self.worktree), "abc"), self.live)

    def test_a_current_cwd_ledger_still_wins_over_the_pointer(self):
        near = self.worktree / ".dispatch" / "runs" / "2026-11-26-near" / "ledger.md"
        near.parent.mkdir(parents=True)
        near.write_text(self.live.read_text(encoding="utf-8"), encoding="utf-8")
        os.environ["CLAUDE_DISPATCH_HOME_POINTER"] = str(self.pointer)
        self.assertEqual(self.g.find_ledger(str(self.worktree), "abc"), near)

    def test_no_pointer_still_finds_nothing(self):
        os.environ["CLAUDE_DISPATCH_HOME_POINTER"] = str(self.dir / "missing" / "ledger-path")
        self.assertIsNone(self.g.find_ledger(str(self.worktree), "abc"))
        self.assertEqual(self.g.home_pointer_path(), self.dir / "missing" / "ledger-path")


if __name__ == "__main__":
    unittest.main()
