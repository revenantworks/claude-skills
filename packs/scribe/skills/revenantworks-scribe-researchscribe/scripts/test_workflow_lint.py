"""Tests for workflow_lint.py (stdlib unittest).

Run: python -m unittest discover -s scripts -p "test_*.py"   (from the skill folder)
"""
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import workflow_lint  # noqa: E402

SHIPPED = os.path.join(os.path.dirname(HERE), "workflows", "research.js")

GOOD = """export const meta = {
  name: 'demo',
  description: 'A demo workflow',
  phases: [
    { title: 'Plan', detail: 'one planner' },
    { title: 'Search' },
  ],
}

phase('Plan')
const plan = await agent(`Plan: ${args.question}`, { label: 'plan' })
phase('Search')
return plan
"""


def codes(text):
    return sorted({f.split(":", 1)[0] for f in workflow_lint.lint(text)})


class CleanScript(unittest.TestCase):
    def test_good_script_has_no_findings(self):
        self.assertEqual(workflow_lint.lint(GOOD), [])

    def test_leading_comment_before_meta_is_allowed(self):
        self.assertEqual(workflow_lint.lint("// header\n" + GOOD), [])


class MetaRules(unittest.TestCase):
    def test_meta_must_be_first_statement(self):
        text = "const x = 1\n" + GOOD
        self.assertIn("META-FIRST", codes(text))

    def test_missing_meta_is_reported(self):
        self.assertIn("META-FIRST", codes("phase('Plan')\n"))

    def test_meta_with_variable_is_not_literal(self):
        text = GOOD.replace("name: 'demo'", "name: NAME")
        self.assertIn("META-LITERAL", codes(text))

    def test_meta_with_call_is_not_literal(self):
        text = GOOD.replace("description: 'A demo workflow'", "description: describe()")
        self.assertIn("META-LITERAL", codes(text))

    def test_meta_with_spread_is_not_literal(self):
        text = GOOD.replace("name: 'demo',", "name: 'demo', ...extra,")
        self.assertIn("META-LITERAL", codes(text))

    def test_meta_with_template_interpolation_is_not_literal(self):
        text = GOOD.replace("name: 'demo'", "name: `demo-${v}`")
        self.assertIn("META-LITERAL", codes(text))

    def test_meta_needs_description(self):
        text = GOOD.replace("  description: 'A demo workflow',\n", "")
        self.assertIn("META-FIELD", codes(text))

    def test_meta_needs_name(self):
        text = GOOD.replace("  name: 'demo',\n", "")
        self.assertIn("META-FIELD", codes(text))


class BodyRules(unittest.TestCase):
    def test_phase_call_without_meta_entry(self):
        text = GOOD.replace("phase('Search')", "phase('Searching')")
        self.assertIn("PHASE-MISMATCH", codes(text))

    def test_banned_date_now(self):
        self.assertIn("BANNED-CALL", codes(GOOD + "const t = Date.now()\n"))

    def test_banned_math_random(self):
        self.assertIn("BANNED-CALL", codes(GOOD + "const r = Math.random()\n"))

    def test_banned_argless_new_date(self):
        self.assertIn("BANNED-CALL", codes(GOOD + "const d = new Date()\n"))

    def test_new_date_with_argument_is_allowed(self):
        self.assertEqual(workflow_lint.lint(GOOD + "const d = new Date(args.date)\n"), [])

    def test_banned_dynamic_import(self):
        self.assertIn("BANNED-CALL", codes(GOOD + "const m = await import('x')\n"))

    def test_banned_require(self):
        self.assertIn("BANNED-CALL", codes(GOOD + "const fs = require('fs')\n"))

    def test_banned_text_inside_a_string_is_ignored(self):
        self.assertEqual(workflow_lint.lint(GOOD + "log('never call Date.now() here')\n"), [])

    def test_model_literal_is_reported(self):
        text = GOOD.replace("{ label: 'plan' }", "{ label: 'plan', model: 'opus' }")
        self.assertIn("MODEL-LITERAL", codes(text))

    def test_model_from_args_is_allowed(self):
        text = GOOD.replace("{ label: 'plan' }", "{ label: 'plan', model: args.models.plan }")
        self.assertEqual(workflow_lint.lint(text), [])


class ShippedWorkflow(unittest.TestCase):
    def test_shipped_research_workflow_is_clean(self):
        with open(SHIPPED, encoding="utf-8") as fh:
            self.assertEqual(workflow_lint.lint(fh.read()), [])

    def test_cli_exit_codes(self):
        ok = subprocess.run([sys.executable, os.path.join(HERE, "workflow_lint.py"), SHIPPED],
                            capture_output=True, text=True)
        self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
        self.assertIn("OK", ok.stdout)
        missing = subprocess.run([sys.executable, os.path.join(HERE, "workflow_lint.py"),
                                  os.path.join(HERE, "no-such-file.js")],
                                 capture_output=True, text=True)
        self.assertEqual(missing.returncode, 2)


if __name__ == "__main__":
    unittest.main()
