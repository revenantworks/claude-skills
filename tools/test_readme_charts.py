#!/usr/bin/env python3
"""Unit tests for readme_charts: the README chart comes from the repo's own data and drifts loudly.

Run: python3 -m unittest discover -s tools -p "test_*.py"
Stdlib only; every fixture lives in a temp directory.
"""
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import readme_charts as rc


def tree(packs):
    root = Path(tempfile.mkdtemp())
    for name, (version, members) in packs.items():
        p = root / "packs" / name
        (p / ".claude-plugin").mkdir(parents=True)
        (p / ".claude-plugin" / "plugin.json").write_text(json.dumps({"name": name, "version": version}), encoding="utf-8")
        for m in members:
            (p / "skills" / m).mkdir(parents=True)
        (p / "skills" / "_shared").mkdir(parents=True, exist_ok=True)  # skipped, as build.py skips it
    return root


class Collect(unittest.TestCase):
    def test_counts_and_order(self):
        root = tree({"b": ("1.2.0", ["x", "y"]), "a": ("1.0.0", ["z"]), "c": ("2.0.0", ["p", "q"])})
        rows = rc.collect(root)
        self.assertEqual([(r["name"], r["skills"]) for r in rows], [("b", 2), ("c", 2), ("a", 1)])
        self.assertEqual(rows[0]["version"], "1.2.0")


class Render(unittest.TestCase):
    def test_svg_parses_with_viewbox_and_fits(self):
        rows = [{"name": "a", "version": "1.0.0", "skills": 3}, {"name": "b", "version": "1.0.0", "skills": 0}]
        for theme in rc.THEMES:
            svg = ET.fromstring(rc.render(rows, theme))
            vb = svg.get("viewBox").split()
            self.assertLessEqual(float(vb[2]), 900)
            self.assertIsNone(svg.get("width") if svg.get("width") != "100%" else None)
            text = rc.render(rows, theme)
            self.assertIn("3 skills in 2 packs", text)

    def test_contrast(self):
        for theme, t in rc.THEMES.items():
            self.assertGreaterEqual(rc.contrast(t["ink"], t["surface"]), 4.5, theme)
            self.assertGreaterEqual(rc.contrast(t["ink2"], t["surface"]), 4.5, theme)
            self.assertGreaterEqual(rc.contrast(t["bar"], t["surface"]), 3.0, theme)


class Sync(unittest.TestCase):
    def test_write_then_check_then_drift(self):
        root = tree({"a": ("1.0.0", ["x"])})
        self.assertEqual(len(rc.sync(root, write=True)), 2)
        self.assertEqual(rc.sync(root, write=False), [])
        (root / "packs" / "a" / "skills" / "y").mkdir()
        drift = rc.sync(root, write=False)
        self.assertEqual(drift, ["docs/assets/skills-per-pack-light.svg", "docs/assets/skills-per-pack-dark.svg"])

    def test_committed_charts_match_the_repo(self):
        self.assertEqual(rc.sync(rc.ROOT, write=False), [], "run python tools/readme_charts.py")


if __name__ == "__main__":
    unittest.main()
