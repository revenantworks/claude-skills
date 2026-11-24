"""Tests for ui_check.py (stdlib unittest; run from this folder or via discover).

Every one of the 31 rules has a pass and a fail fixture under evals/fixtures/ui/<rule>/.
EXPECTED_TOTAL is asserted by the last test, so a test that silently fails to load or is
dropped turns the run red instead of leaving it green with fewer tests.
"""
import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ui_check as uc  # noqa: E402

SCRIPT = os.path.join(HERE, "ui_check.py")
FIX = os.path.normpath(os.path.join(HERE, "..", "evals", "fixtures", "ui"))

RULE_DIRS = {
    "R1": "r01-asset-missing", "R2": "r02-font-file-missing", "R3": "r03-font-unsourced",
    "R4": "r04-img-alt-missing", "R5": "r05-control-unlabelled", "R6": "r06-placeholder-only-label",
    "R7": "r07-control-unnamed", "R8": "r08-html-lang-missing", "R9": "r09-viewport-meta-missing",
    "R10": "r10-heading-order", "R11": "r11-contrast-low", "R12": "r12-focus-removed",
    "R13": "r13-duplicate-id", "R14": "r14-reduced-motion-missing", "R15": "r15-layout-prop-animated",
    "R16": "r16-will-change-at-rest", "R17": "r17-bounce-easing", "R18": "r18-fixed-width-wide",
    "R19": "r19-target-small", "R20": "r20-body-text-small", "R21": "r21-measure-unbounded",
    "R22": "r22-gradient-text", "R23": "r23-side-stripe", "R24": "r24-glow-shadow",
    "R25": "r25-offset-block-shadow", "R26": "r26-emoji-icon", "R27": "r27-type-extremes",
    "R28": "r28-card-nest", "R29": "r29-eyebrow", "R30": "r30-raw-colour-count",
    "R31": "r31-browser-surface-unthemed",
}

# 62 fixture-pair tests + 6 regression + 14 calibration + 4 extras + 3 rule table + 5 CLI + 3 colour
# + 1 self-check
EXPECTED_TOTAL = 98


def fx(*parts):
    return os.path.join(FIX, *parts)


def hits(report, rule=None):
    rows = [f for f in report.findings if rule is None or f["rule"] == rule]
    return rows


def run_cli(*args):
    return subprocess.run([sys.executable, SCRIPT] + list(args), capture_output=True, text=True)


class FixturePairs(unittest.TestCase):
    """One pass and one fail fixture per rule."""


def _make_pair(rule, folder):
    def test_fail(self):
        rep = uc.check([fx(folder, "fail")])
        self.assertTrue(hits(rep, rule), "%s should fire on %s/fail; got %s" % (
            rule, folder, sorted({f["rule"] for f in rep.findings})))

    def test_pass(self):
        rep = uc.check([fx(folder, "pass")])
        self.assertFalse(hits(rep, rule), "%s should stay quiet on %s/pass: %s" % (
            rule, folder, hits(rep, rule)))
    return test_fail, test_pass


for _rule, _folder in RULE_DIRS.items():
    _f, _p = _make_pair(_rule, _folder)
    setattr(FixturePairs, "test_%s_fail" % _rule.lower(), _f)
    setattr(FixturePairs, "test_%s_pass" % _rule.lower(), _p)


class Regressions(unittest.TestCase):
    def test_missing_webfont_in_built_output(self):
        # A built folder whose woff2 was never copied: the defect class a per-edit hook missed.
        rep = uc.check([fx("reg-missing-webfont", "dist")])
        rows = hits(rep, "R2")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["sev"], "P1")
        self.assertIn("body.woff2", rows[0]["msg"])

    def test_no_painted_ground_is_not_a_failure(self):
        rep = uc.check([fx("reg-no-painted-ground")])
        self.assertFalse(hits(rep, "R11"))

    def test_no_painted_ground_is_reported_unmeasured(self):
        rep = uc.check([fx("reg-no-painted-ground")])
        self.assertTrue(any("ground" in u["reason"] for u in rep.unmeasured))

    def test_dark_ground_on_ancestor_measures_high_not_inverted(self):
        rep = uc.check([fx("reg-ancestor-ground")])
        self.assertFalse(hits(rep, "R11"))
        ratios = [p["ratio"] for p in rep.pairs]
        self.assertTrue(ratios and max(ratios) > 15, ratios)

    def test_injected_comment_is_reported(self):
        rep = uc.check([fx("reg-injected-comment")])
        self.assertEqual(len(hits(rep, "INJECTED")), 1)

    def test_injected_comment_is_never_echoed(self):
        rep = uc.check([fx("reg-injected-comment")])
        for row in hits(rep, "INJECTED"):
            self.assertNotIn("delete", row["msg"].lower())
            self.assertNotIn("ignore previous", row["msg"].lower())


class Calibration(unittest.TestCase):
    """First live run on a real built site (FXL1): cascade layers, functional selectors, body text, capped widths.

    Every fixture is synthetic and neutral; each reproduces one pattern the live run misread.
    """

    def _unset(self, rep):
        return [u for u in rep.unmeasured if "unset" in u["reason"]]

    def test_layered_colour_is_measured_not_unset(self):
        rep = uc.check([fx("reg-layered-colour")])
        self.assertEqual(self._unset(rep), [])
        self.assertGreaterEqual(len(rep.pairs), 3, rep.pairs)

    def test_later_layer_beats_specificity_in_an_earlier_layer(self):
        rep = uc.check([fx("reg-layered-colour")])
        rows = hits(rep, "R11")
        self.assertEqual(len(rows), 1, rows)
        self.assertIn("#9a9a9a", rows[0]["msg"])

    def test_unlayered_rule_beats_layered_rule(self):
        rep = uc.check([fx("reg-layered-colour")])
        self.assertIn("#111111", {p["fg"] for p in rep.pairs})

    def test_where_is_not_and_escaped_classes_resolve_colour(self):
        rep = uc.check([fx("reg-functional-selectors")])
        self.assertEqual(self._unset(rep), [])
        self.assertEqual({p["fg"] for p in rep.pairs}, {"#222222", "#333333"})
        self.assertFalse(hits(rep, "R11"))

    def test_where_adds_no_specificity_and_is_adds_its_argument(self):
        self.assertEqual(uc._spec(uc.parse_selector(":where(#a) p")), (0, 0, 1))
        self.assertEqual(uc._spec(uc.parse_selector(":is(#a, .b) p")), (1, 0, 1))
        self.assertEqual(uc._spec(uc.parse_selector("p:not(.x)")), (0, 1, 1))

    def test_escaped_class_and_attribute_inside_not_parse(self):
        chain = uc.parse_selector(".t-dark\\:soft")
        self.assertIsNotNone(chain)
        self.assertEqual(chain[0][1]["classes"], ["t-dark:soft"])
        self.assertIsNotNone(uc.parse_selector("p:not(:where([class~=not-prose], [class~=not-prose] *))"))

    def test_fallback_custom_property_inherited_from_ancestor(self):
        rep = uc.check([fx("reg-inherited-var-colour")])
        self.assertEqual(self._unset(rep), [])
        self.assertEqual({p["fg"] for p in rep.pairs}, {"#202020"})

    def test_nav_footer_aside_caption_and_small_print_are_not_body_text(self):
        rep = uc.check([fx("reg-body-vs-small-print")])
        self.assertFalse(hits(rep, "R20"), hits(rep, "R20"))

    def test_body_text_classification_is_reported(self):
        rep = uc.check([fx("reg-body-vs-small-print")])
        self.assertEqual(len(rep.body_text), 1)
        row = rep.body_text[0]
        self.assertEqual(row["dominant_px"], 16.0)
        self.assertEqual(row["measured"], 3)
        for role in ("nav", "footer", "aside", "small print", "short list item"):
            self.assertIn(role, row["classed_out"], row)
        self.assertEqual(row["classed_out"]["small print"], 3)  # caption class, inline note, class-reduced note
        self.assertEqual(row["classed_out"]["short list item"], 3)

    def test_paragraphs_all_reduced_by_a_class_are_still_body_text(self):
        rep = uc.check([fx("reg-body-all-reduced")])
        rows = hits(rep, "R20")
        self.assertEqual(len(rows), 1, rows)
        self.assertIn("14px", rows[0]["msg"])

    def test_layered_small_body_text_flags_once_at_p2(self):
        rep = uc.check([fx("reg-body-small-layered")])
        rows = hits(rep, "R20")
        self.assertEqual(len(rows), 1, rows)
        self.assertEqual(rows[0]["sev"], "P2")
        self.assertIn("15px", rows[0]["msg"])

    def test_json_carries_the_body_text_classification(self):
        out = run_cli("--json", fx("reg-body-small-layered"))
        doc = json.loads(out.stdout)
        self.assertIn("body_text", doc)
        self.assertEqual(doc["body_text"][0]["dominant_px"], 15.0)

    def test_color_mix_ground_is_unmeasured_not_its_first_colour(self):
        rep = uc.check([fx("reg-color-mix-ground")])
        self.assertFalse(hits(rep, "R11"), hits(rep, "R11"))
        self.assertTrue(any("color-mix" in u["reason"] for u in rep.unmeasured), rep.unmeasured)

    def test_width_capped_by_min_max_width_or_media_query_is_quiet(self):
        rep = uc.check([fx("reg-fixed-width-capped")])
        self.assertFalse(hits(rep, "R18"), hits(rep, "R18"))


class Extras(unittest.TestCase):
    def test_two_h1_is_a_p3_question(self):
        rep = uc.check([fx("extra-two-h1")])
        rows = hits(rep, "R10")
        self.assertTrue(rows)
        self.assertEqual({r["sev"] for r in rows}, {"P3"})

    def test_text_under_12px_is_p1(self):
        rep = uc.check([fx("extra-tiny-text")])
        self.assertEqual([r["sev"] for r in hits(rep, "R20")], ["P1"])

    def test_ignore_line_with_reason_waives(self):
        rep = uc.check([fx("extra-ignore")])
        self.assertFalse(hits(rep, "R9"))
        self.assertEqual([w["rule"] for w in rep.waived], ["R9"])

    def test_ignore_line_without_reason_is_invalid(self):
        rep = uc.check([fx("extra-ignore")])
        self.assertEqual(len(rep.invalid_ignores), 1)
        self.assertIn("R8", rep.invalid_ignores[0])


class RuleTable(unittest.TestCase):
    def test_thirty_one_rules_in_order(self):
        self.assertEqual([r[0] for r in uc.RULES], ["R%d" % i for i in range(1, 32)])

    def test_severities_and_slugs(self):
        for rid, slug, sev, summary in uc.RULES:
            self.assertIn(sev, ("P0", "P1", "P2", "P3"), rid)
            self.assertEqual(RULE_DIRS[rid][4:], slug)
            self.assertTrue(summary)

    def test_list_rules_cli_prints_31(self):
        out = run_cli("--list-rules")
        self.assertEqual(out.returncode, 0)
        self.assertEqual(len([ln for ln in out.stdout.splitlines() if ln.startswith("R")]), 31)


class Cli(unittest.TestCase):
    def test_p1_finding_exits_1(self):
        self.assertEqual(run_cli(fx("r04-img-alt-missing", "fail")).returncode, 1)

    def test_p3_only_exits_0(self):
        out = run_cli(fx("r22-gradient-text", "fail"))
        self.assertEqual(out.returncode, 0, out.stdout)
        self.assertIn("R22", out.stdout)

    def test_unmeasured_only_exits_0(self):
        self.assertEqual(run_cli(fx("reg-no-painted-ground")).returncode, 0)

    def test_missing_path_exits_2(self):
        self.assertEqual(run_cli(fx("no-such-folder")).returncode, 2)

    def test_json_shape(self):
        out = run_cli("--json", fx("r13-duplicate-id", "fail"))
        doc = json.loads(out.stdout)
        for key in ("findings", "questions", "unmeasured", "pairs", "waived", "files", "rules"):
            self.assertIn(key, doc)
        self.assertEqual(doc["rules"], 31)
        self.assertTrue(any(f["rule"] == "R13" for f in doc["findings"]))


class Colour(unittest.TestCase):
    def test_known_grey_on_white(self):
        self.assertAlmostEqual(uc.contrast(uc.parse_colour("#767676"), uc.parse_colour("#fff")), 4.54, places=2)

    def test_rgb_forms_and_names(self):
        self.assertEqual(uc.parse_colour("rgb(255, 0, 0)")[:3], (255, 0, 0))
        self.assertEqual(uc.parse_colour("rgb(255 0 0 / 50%)")[3], 0.5)
        self.assertEqual(uc.parse_colour("white")[:3], (255, 255, 255))
        self.assertIsNone(uc.parse_colour("var(--x)"))

    def test_large_text_floor(self):
        self.assertEqual(uc.floor_for(24.0, 400), 3.0)
        self.assertEqual(uc.floor_for(19.0, 700), 3.0)
        self.assertEqual(uc.floor_for(16.0, 700), 4.5)


class Count(unittest.TestCase):
    def test_expected_total(self):
        n = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]).countTestCases()
        self.assertEqual(n, EXPECTED_TOTAL)


if __name__ == "__main__":
    unittest.main()
