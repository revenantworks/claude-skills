#!/usr/bin/env python3
"""Unit tests for three `--check` checks added from the pack-split run's observations (unit OBA):

- cold-listing cells against the live descriptions: a seam row's `both descriptions` /
  `one description` / `none — table only` cell must equal how many of the two descriptions name
  the other member (19 seam cells had drifted by the time a registry pass caught them);
- script declarations: where a pack row's rule says scripts are declared in `compatibility:`,
  the README and the Load budget, every shipped script is named in each place the rule names
  (a near-budget member went over when a required line was added by hand);
- the fixed trigger-suite count line `Counts: N queries (S should, T should-not, P pairs)`:
  S + T = N and P <= min(S, T) when the line is present; a suite without it is listed once.

Run: python3 -m unittest discover -s tools -p "test_*.py"
Stdlib only. Fixtures are written to temp directories with relative paths only.
"""
import unittest

import build
from test_build_split import capture, tmpdir


DESCS = {
    "acme-tools-hammerwright": "Hits nails. A screw is screwwright's.",
    "acme-tools-screwwright": "Turns screws. A nail is hammerwright's.",
    "acme-tools-sawwright": "Cuts boards.",
}


class ColdListingAgainstDescriptions(unittest.TestCase):
    def check(self, left, right, cell):
        _, problems, _ = capture(build.validate_cold_listing, "tools", left, right, cell, DESCS)
        return problems

    def test_both_descriptions_holds_when_each_names_the_other(self):
        self.assertEqual(self.check("hammerwright", "screwwright", "both descriptions"), [])

    def test_both_descriptions_fails_when_only_one_names_the_other(self):
        problems = self.check("hammerwright", "sawwright", "both descriptions")
        self.assertEqual(len(problems), 1)
        self.assertIn("0 of 2", problems[0])

    def test_none_table_only_fails_when_a_description_names_the_sibling(self):
        problems = self.check("screwwright", "hammerwright", "none — table only")
        self.assertEqual(len(problems), 1)
        self.assertIn("2 of 2", problems[0])

    def test_one_description_and_bold_markup(self):
        descs = dict(DESCS, **{"acme-tools-sawwright": "Cuts boards; a nail is hammerwright's."})
        _, problems, _ = capture(build.validate_cold_listing, "tools", "hammerwright", "sawwright",
                                 "**one description**", descs)
        self.assertEqual(problems, [])

    def test_cross_pack_prose_cell_is_read_from_its_marker(self):
        cell = "Left owns the nail. Cold-listing signal: none — table only (re-read 2026-10-01)."
        self.assertEqual(self.check("sawwright", "screwwright", cell), [])
        self.assertEqual(len(self.check("hammerwright", "screwwright", cell)), 1)

    def test_cell_without_a_marker_or_a_planned_member_is_skipped(self):
        self.assertEqual(self.check("hammerwright", "sawwright", "Left owns the nail."), [])
        self.assertEqual(self.check("hammerwright", "drillwright", "both descriptions"), [])


def scripted_member(test, pack_notes_places: str, readme: str, load_budget: str, compat: str):
    root = tmpdir(test)
    m = root / "acme-tools-hammerwright"
    (m / "scripts").mkdir(parents=True)
    for name in ("nail_check.py", "test_nail_check.py", "__init__.py"):
        (m / "scripts" / name).write_bytes(b"print('x')\n")
    (m / "SKILL.md").write_bytes((
        "---\nname: acme-tools-hammerwright\ndescription: Hits nails.\ncompatibility: " + compat +
        "\nmetadata:\n  version: \"1.0.0\"\n---\n\n# hammerwright\n\n## Load budget\n\n" + load_budget +
        "\n\n## Steps\n\nHit it.\n").encode())
    (m / "README.md").write_bytes(readme.encode())
    notes = "Standard-library scripts are allowed when declared — in " + pack_notes_places + "."
    return notes, m


class ScriptDeclarations(unittest.TestCase):
    THREE = "`compatibility:`, the README and the member's Load budget"

    def test_three_place_rule_holds(self):
        notes, m = scripted_member(self, self.THREE, "Runs scripts/nail_check.py.",
                                   "`scripts/nail_check.py` is run, not read.", "Python 3 runs nail_check.py.")
        _, problems, _ = capture(build.validate_script_declarations, "tools", notes, m)
        self.assertEqual(problems, [])

    def test_missing_load_budget_line_fails_and_names_the_place(self):
        notes, m = scripted_member(self, self.THREE, "Runs scripts/nail_check.py.",
                                   "Nothing here.", "Python 3 runs nail_check.py.")
        _, problems, _ = capture(build.validate_script_declarations, "tools", notes, m)
        self.assertEqual(len(problems), 1)
        self.assertIn("Load budget", problems[0])
        self.assertIn("nail_check.py", problems[0])

    def test_missing_readme_fails(self):
        notes, m = scripted_member(self, self.THREE, "No scripts named.",
                                   "`nail_check.py`", "Python 3 runs nail_check.py.")
        _, problems, _ = capture(build.validate_script_declarations, "tools", notes, m)
        self.assertEqual(len(problems), 1)
        self.assertIn("README", problems[0])

    def test_compatibility_may_summarise_under_its_cap(self):
        notes, m = scripted_member(self, "`compatibility:` and the README", "nail_check.py",
                                   "Nothing here.", "Python 3 runs the stdlib scripts.")
        _, problems, _ = capture(build.validate_script_declarations, "tools", notes, m)
        self.assertEqual(problems, [])

    def test_compatibility_silent_on_scripts_fails(self):
        notes, m = scripted_member(self, "`compatibility:` and the README", "nail_check.py",
                                   "Nothing here.", "No packages.")
        _, problems, _ = capture(build.validate_script_declarations, "tools", notes, m)
        self.assertEqual(len(problems), 1)
        self.assertIn("compatibility", problems[0])

    def test_pack_without_a_declaration_rule_is_not_checked(self):
        _, m = scripted_member(self, self.THREE, "", "", "No packages.")
        _, problems, _ = capture(build.validate_script_declarations, "tools", "Script-free pack.", m)
        self.assertEqual(problems, [])


class FixedCountsLine(unittest.TestCase):
    def run_on(self, head: str, rows: int, name: str = "trigger-evals.md"):
        lines = ["# Trigger evals", "", head, "", "| # | Query | Expected |", "|---|---|---|"]
        lines += [f"| {i} | q{i} | x |" for i in range(1, rows + 1)]
        return capture(build.validate_eval_counts, "acme-tools-hammerwright", name, lines)

    def test_fixed_form_that_adds_up_passes(self):
        _, problems, _ = self.run_on("Counts: 6 queries (3 should, 3 should-not, 2 pairs)", 6)
        self.assertEqual(problems, [])

    def test_split_that_does_not_add_up_fails(self):
        _, problems, _ = self.run_on("Counts: 6 queries (3 should, 2 should-not, 1 pairs)", 6)
        self.assertEqual(len(problems), 1)
        self.assertIn("3 + 2", problems[0])

    def test_more_pairs_than_the_smaller_half_fails(self):
        _, problems, _ = self.run_on("Counts: 6 queries (4 should, 2 should-not, 3 pairs)", 6)
        self.assertEqual(len(problems), 1)
        self.assertIn("pairs", problems[0])

    def test_injection_probes_count_toward_the_total(self):
        # Unit FXL2: three suites carry injection-probe rows beside the routing rows.
        _, problems, _ = self.run_on("Counts: 8 queries (3 should, 3 should-not, 2 pairs, 2 injection probes)", 8)
        self.assertEqual(problems, [])

    def test_probes_that_do_not_add_up_fail(self):
        _, problems, _ = self.run_on("Counts: 8 queries (3 should, 3 should-not, 2 pairs, 1 injection probe)", 8)
        self.assertEqual(len(problems), 1)
        self.assertIn("3 + 3 + 1", problems[0])

    def test_a_probe_line_is_the_fixed_form(self):
        saved = list(build.COUNTS_FORM_MISSING)
        build.COUNTS_FORM_MISSING.clear()
        try:
            self.run_on("Counts: 8 queries (3 should, 3 should-not, 2 pairs, 2 injection probes)", 8)
            added = list(build.COUNTS_FORM_MISSING)
        finally:
            build.COUNTS_FORM_MISSING[:] = saved
        self.assertEqual(added, [])

    def test_suite_without_the_fixed_form_is_recorded_once(self):
        saved = list(build.COUNTS_FORM_MISSING)
        build.COUNTS_FORM_MISSING.clear()
        try:
            self.run_on("Counts: 6 queries, judged cold.", 6)
            self.run_on("Counts: 6 queries, judged cold.", 6)
            self.run_on("Counts: 6 queries, judged cold.", 6, name="test-cases.md")
            added = list(build.COUNTS_FORM_MISSING)
        finally:
            build.COUNTS_FORM_MISSING[:] = saved
        self.assertEqual(added, ["acme-tools-hammerwright"])


class AccumulatorsResetPerRun(unittest.TestCase):
    """Unit FXL2: main() clears the module-level accumulators (COUNTS_FORM_MISSING, FOOTPRINTS)
    at its start, so entries left by an earlier call or a direct validator test never leak into
    the next run's advisory or footprint table, even when main() returns early."""

    def setUp(self):
        self.saved_counts = list(build.COUNTS_FORM_MISSING)
        self.saved_foot = dict(build.FOOTPRINTS)
        self.saved_bump = build.BUMP_MEMBER
        build.COUNTS_FORM_MISSING[:] = ["acme-tools-ghostwright"]
        build.FOOTPRINTS.clear()
        build.FOOTPRINTS["acme-tools-ghostwright"] = (1, None, [])

    def tearDown(self):
        build.COUNTS_FORM_MISSING[:] = self.saved_counts
        build.FOOTPRINTS.clear()
        build.FOOTPRINTS.update(self.saved_foot)
        build.BUMP_MEMBER = self.saved_bump

    def test_early_return_still_clears(self):
        # A --bump-member on a member that does not exist returns 1 before any build step.
        build.BUMP_MEMBER = ("acme-tools-no-such-member", "9.9.9", "test")
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):
            rc, _, _ = capture(build.main)
        self.assertEqual(rc, 1)
        self.assertEqual(build.COUNTS_FORM_MISSING, [])
        self.assertEqual(build.FOOTPRINTS, {})

    def test_full_run_drops_stale_footprints(self):
        from test_build_footprint import member_with
        from test_build_split import Rooted
        import contextlib
        import io
        root, _ = member_with(self, "Every run touches `small.md`.", {"references/small.md": 50})
        with Rooted(root, check=True), contextlib.redirect_stdout(io.StringIO()):
            capture(build.main)
        self.assertNotIn("acme-tools-ghostwright", build.FOOTPRINTS)
        self.assertNotIn("acme-tools-ghostwright", build.COUNTS_FORM_MISSING)
        self.assertIn("acme-tools-hammerwright", build.FOOTPRINTS)


if __name__ == "__main__":
    unittest.main()
