#!/usr/bin/env python3
"""Unit tests for check_mods (owner 2026-10-06): mod-only plugins are listed in the
marketplace at their own version, keep the empty hooks key, hold no skills, and hook code
never sits inside a skill or a featured plugin, so it cannot reach a claude.ai zip.

Run: python3 -m unittest discover -s tools -p "test_*.py"
Stdlib only; every fixture lives in a temp directory.
"""
import json
import tempfile
import unittest
from pathlib import Path

import build


def mod_root(entry_version="1.0.0", hooks=None, extra=None, with_module_missing=False):
    tmp = Path(tempfile.mkdtemp())
    (tmp / ".claude-plugin").mkdir()
    plugins = [{"name": "demo-mods", "source": "./mods/demo-mods", "version": entry_version}]
    (tmp / ".claude-plugin" / "marketplace.json").write_text(json.dumps({"name": "x", "plugins": plugins}), encoding="utf-8")
    d = tmp / "mods" / "demo-mods"
    (d / ".claude-plugin").mkdir(parents=True)
    (d / "hooks").mkdir()
    (d / ".claude-plugin" / "plugin.json").write_text(json.dumps({"name": "demo-mods", "version": "1.0.0"}), encoding="utf-8")
    (d / "hooks" / "hooks.json").write_text(json.dumps(hooks if hooks is not None else {"hooks": {}, "modules": ["./register.tsx"]}), encoding="utf-8")
    if hooks is None and not with_module_missing:
        (d / "hooks" / "register.tsx").write_text("const VERSION = '1.0.0'\n", encoding="utf-8")
    for rel in extra or []:
        p = tmp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x", encoding="utf-8")
    return tmp


class CheckMods(unittest.TestCase):
    def tearDown(self):
        build.problems.clear()  # the next test's main() starts from a clean list

    def run_check(self, root):
        build.problems.clear()
        n = build.check_mods(root)
        return n, list(build.problems)

    def test_clean(self):
        n, problems = self.run_check(mod_root())
        self.assertEqual(n, 1)
        self.assertEqual(problems, [])

    def test_version_drift(self):
        _, problems = self.run_check(mod_root(entry_version="1.0.1"))
        self.assertTrue(any("version" in p for p in problems))

    def test_hooks_key_required(self):
        _, problems = self.run_check(mod_root(hooks={"modules": ["./register.tsx"]}))
        self.assertTrue(any("older Claude Code" in p for p in problems))

    def test_hook_code_inside_a_skill(self):
        root = mod_root(extra=["packs/p/skills/s/hooks/register.tsx", "featured/f/skills/f/x.ts", "packs/p/skills/s/scripts/hooks/push_gate.py"])
        (root / "packs/p/skills/s/hooks/hooks.json").write_text('{"hooks": {}, "modules": ["./register.tsx"]}', encoding="utf-8")
        _, problems = self.run_check(root)
        self.assertEqual(len([p for p in problems if "would ship in its zip" in p]), 3)
        self.assertFalse(any("push_gate" in p for p in problems))

    def test_module_must_exist_and_match_version(self):
        root = mod_root(with_module_missing=True)
        _, problems = self.run_check(root)
        self.assertTrue(any("does not exist" in p for p in problems))
        (root / "mods/demo-mods/hooks/register.tsx").write_text("const VERSION = '1.0.1'\n", encoding="utf-8")
        _, problems = self.run_check(root)
        self.assertTrue(any("VERSION" in p for p in problems))

    def test_missing_entry(self):
        root = mod_root()
        (root / ".claude-plugin" / "marketplace.json").write_text(json.dumps({"name": "x", "plugins": []}), encoding="utf-8")
        _, problems = self.run_check(root)
        self.assertTrue(any("no entry for mod plugin" in p for p in problems))


class CheckBundle(unittest.TestCase):
    def tearDown(self):
        build.problems.clear()

    def bundle(self, deps):
        root = mod_root()
        b = root / "mods" / "all-mods" / ".claude-plugin"
        b.mkdir(parents=True)
        (b / "plugin.json").write_text(json.dumps({"name": "all-mods", "version": "1.0.0", "dependencies": deps}), encoding="utf-8")
        cat = json.loads((root / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
        cat["plugins"].append({"name": "all-mods", "source": "./mods/all-mods", "version": "1.0.0"})
        (root / ".claude-plugin" / "marketplace.json").write_text(json.dumps(cat), encoding="utf-8")
        build.problems.clear()
        build.check_mods(root)
        return list(build.problems)

    def test_bundle_lists_every_mod(self):
        self.assertEqual(self.bundle(["demo-mods"]), [])

    def test_bundle_missing_a_mod(self):
        self.assertTrue(any("bundle must depend" in p for p in self.bundle([])))


if __name__ == "__main__":
    unittest.main()
