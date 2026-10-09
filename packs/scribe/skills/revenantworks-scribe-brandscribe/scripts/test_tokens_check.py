"""Tests for tokens_check.py (stdlib unittest; run from this folder or via discover)."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tokens_check as tc  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "tokens_check.py")


class ContrastRatio(unittest.TestCase):
    def test_black_on_white_is_21(self):
        self.assertAlmostEqual(tc.contrast_ratio("#000000", "#ffffff"), 21.0, places=2)

    def test_same_colour_is_1(self):
        self.assertAlmostEqual(tc.contrast_ratio("#777777", "#777777"), 1.0, places=4)

    def test_order_does_not_matter(self):
        a = tc.contrast_ratio("#336699", "#f0f0f0")
        b = tc.contrast_ratio("#f0f0f0", "#336699")
        self.assertAlmostEqual(a, b, places=6)

    def test_known_pair_767676_on_white(self):
        # The classic smallest grey that clears 4.5:1 on white.
        self.assertAlmostEqual(tc.contrast_ratio("#767676", "#ffffff"), 4.54, places=2)

    def test_short_hex(self):
        self.assertAlmostEqual(tc.contrast_ratio("#000", "#fff"), 21.0, places=2)

    def test_bad_hex_raises(self):
        with self.assertRaises(ValueError):
            tc.contrast_ratio("blue", "#ffffff")


def _good_doc():
    return {
        "name": "Example",
        "color": {
            "themes": [{"id": "light", "name": "Light"}],
            "tokens": [
                {"name": "surface", "value": "#ffffff", "usage": "Page ground."},
                {"name": "ink", "value": {"light": "#1a1a1a"}, "usage": "Text on surface."},
                {"name": "border-lit", "value": "{ink}", "usage": "Focus edge."},
            ],
        },
        "spacing": {"tokens": [{"name": "space-4", "value": "16px", "usage": "Card padding."}]},
        "type": {"fonts": [], "families": {"sans": "system-ui, sans-serif"}, "groups": []},
    }


class CheckTokens(unittest.TestCase):
    def test_clean_doc_has_no_findings(self):
        self.assertEqual(tc.check_tokens(_good_doc()), [])

    def test_map_shaped_family_is_flagged(self):
        doc = _good_doc()
        doc["color"] = {"brand": {"$value": "#ff0000", "$type": "color"}}
        findings = tc.check_tokens(doc)
        self.assertTrue(any("SHAPE" in f and "color" in f for f in findings), findings)

    def test_bad_name_is_flagged(self):
        doc = _good_doc()
        doc["spacing"]["tokens"].append({"name": "space 8", "value": "32px", "usage": "x"})
        self.assertTrue(any("NAME" in f and "space 8" in f for f in tc.check_tokens(doc)))

    def test_duplicate_across_families_is_flagged(self):
        doc = _good_doc()
        doc["spacing"]["tokens"].append({"name": "ink", "value": "4px", "usage": "x"})
        self.assertTrue(any("DUPLICATE" in f and "ink" in f for f in tc.check_tokens(doc)))

    def test_dropping_colour_values_are_flagged(self):
        for bad in ("red", "var(--x)", "color-mix(in oklch, #fff, #000)", "transparent"):
            doc = _good_doc()
            doc["color"]["tokens"].append({"name": "bad", "value": bad, "usage": "x"})
            self.assertTrue(any("VALUE" in f for f in tc.check_tokens(doc)), bad)

    def test_alias_to_missing_token_is_flagged(self):
        doc = _good_doc()
        doc["color"]["tokens"].append({"name": "ghost", "value": "{nope}", "usage": "x"})
        self.assertTrue(any("ALIAS" in f and "nope" in f for f in tc.check_tokens(doc)))

    def test_self_alias_is_flagged(self):
        doc = _good_doc()
        doc["color"]["tokens"].append({"name": "loop", "value": "{loop}", "usage": "x"})
        self.assertTrue(any("ALIAS" in f and "loop" in f for f in tc.check_tokens(doc)))

    def test_missing_usage_is_flagged(self):
        doc = _good_doc()
        doc["spacing"]["tokens"].append({"name": "space-8", "value": "32px"})
        self.assertTrue(any("USAGE" in f and "space-8" in f for f in tc.check_tokens(doc)))


class DtcgToList(unittest.TestCase):
    def test_nested_groups_become_list_entries(self):
        src = {
            "color": {
                "brand": {"primary": {"$type": "color", "$value": "#225588", "$description": "Links."}},
                "ink": {"$type": "color", "$value": "{color.brand.primary}"},
            },
            "spacing": {"md": {"$type": "dimension", "$value": "16px"}},
        }
        out = tc.dtcg_to_list(src)
        names = {t["name"]: t for t in out["color"]["tokens"]}
        self.assertEqual(names["brand-primary"]["value"], "#225588")
        self.assertEqual(names["brand-primary"]["usage"], "Links.")
        self.assertEqual(names["ink"]["value"], "{brand-primary}")
        self.assertEqual(out["spacing"]["tokens"][0]["name"], "md")
        # Shape, names and aliases are clean; a token with no $description still needs a
        # usage note, and the check says so rather than the converter inventing one.
        findings = tc.check_tokens(out)
        self.assertTrue(findings and all(f.startswith("USAGE") for f in findings), findings)

    def test_converted_output_is_list_shaped(self):
        out = tc.dtcg_to_list({"radius": {"sm": {"$value": "4px"}}})
        self.assertIsInstance(out["radius"]["tokens"], list)


class Cli(unittest.TestCase):
    def _run(self, *args):
        return subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True)

    def test_contrast_cli_prints_ratio(self):
        r = self._run("contrast", "#000000", "#ffffff")
        self.assertEqual(r.returncode, 0)
        self.assertIn("21.00", r.stdout)

    def test_check_cli_exits_1_on_findings(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "tokens.json")
            with open(p, "w", encoding="utf-8") as fh:
                json.dump({"color": {"brand": {"$value": "#ff0000"}}}, fh)
            r = self._run("check", p)
        self.assertEqual(r.returncode, 1)
        self.assertIn("SHAPE", r.stdout)

    def test_check_cli_exits_0_when_clean(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "tokens.json")
            with open(p, "w", encoding="utf-8") as fh:
                json.dump(_good_doc(), fh)
            r = self._run("check", p)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_convert_cli_writes_list_shape(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "dtcg.json")
            with open(p, "w", encoding="utf-8") as fh:
                json.dump({"color": {"a": {"$value": "#123456"}}}, fh)
            r = self._run("convert", p)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["color"]["tokens"][0]["name"], "a")


if __name__ == "__main__":
    unittest.main()
