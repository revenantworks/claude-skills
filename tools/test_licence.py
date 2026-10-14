#!/usr/bin/env python3
"""Licence surface tests (run 2026-09-28-pack-split, unit LIC): every skill, pack and the repo
ship under the Apache License 2.0 (owner decision 2026-10-02).

Run: python3 -m unittest discover -s tools -p "test_*.py"
Stdlib only. Read-only: it reads the live tree and writes nothing.
"""
import json
import re
import unittest

import build

ROOT = build.ROOT
SPDX = "Apache-2.0"
HEAD = "Apache License\n                           Version 2.0, January 2004"
COPYRIGHT = "Copyright 2026 Revenantworks"


def _members():
    return sorted(p for p in (ROOT / "packs").glob("*/skills/*") if (p / "SKILL.md").is_file())


def _packs():
    return sorted(p for p in (ROOT / "packs").iterdir() if (p / ".claude-plugin" / "plugin.json").is_file())


def _text(path):
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


class Defaults(unittest.TestCase):
    def test_build_default_licence_is_apache(self):
        self.assertEqual(build.DEFAULT_LICENSE, SPDX)

    def test_build_source_hardcodes_no_mit_default(self):
        self.assertNotIn('"MIT"', _text(ROOT / "tools" / "build.py"))


class LiveTree(unittest.TestCase):
    def test_tree_has_members_and_packs(self):
        self.assertGreaterEqual(len(_members()), 1)
        self.assertGreaterEqual(len(_packs()), 1)

    def test_every_skill_frontmatter_names_apache(self):
        for m in _members():
            fm = _text(m / "SKILL.md").split("\n---", 1)[0]
            lic = re.search(r"^license:\s*(\S+)\s*$", fm, re.M)
            self.assertIsNotNone(lic, m.name)
            self.assertEqual(lic.group(1), SPDX, m.name)

    def test_every_plugin_and_marketplace_entry_names_apache(self):
        for p in _packs():
            pj = json.loads(_text(p / ".claude-plugin" / "plugin.json"))
            self.assertEqual(pj.get("license"), SPDX, p.name)
        cat = json.loads(_text(ROOT / ".claude-plugin" / "marketplace.json"))
        for entry in cat.get("plugins", []):
            self.assertEqual(entry.get("license"), SPDX, entry.get("name"))

    def test_every_licence_file_is_the_apache_text_with_the_brand_copyright(self):
        for path in [ROOT / "LICENSE"] + [m / "LICENSE" for m in _members()]:
            body = _text(path)
            self.assertIn(HEAD, body, path)
            self.assertIn(COPYRIGHT, body, path)
            self.assertNotIn("[yyyy]", body, path)
            self.assertNotIn("Permission is hereby granted", body, path)

    def test_root_and_every_pack_carry_a_notice(self):
        for path in [ROOT / "NOTICE"] + [p / "NOTICE" for p in _packs()]:
            self.assertTrue(path.is_file(), path)
            body = _text(path)
            self.assertIn(COPYRIGHT, body, path)
            self.assertIn("Apache License", body, path)


if __name__ == "__main__":
    unittest.main()
