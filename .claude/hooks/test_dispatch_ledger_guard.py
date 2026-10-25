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


if __name__ == "__main__":
    unittest.main()
