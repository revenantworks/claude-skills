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


class ToolResultCasts(unittest.TestCase):
    """Obs 0344: a tool result cast `as never` or `as any` hid a shape the host refuses on every
    call. check_mods fails on such a cast in any mods/**/*.ts(x), hooks and test stubs alike."""

    def tearDown(self):
        build.problems.clear()

    def casts(self, rel, text):
        root = mod_root()
        p = root / "mods" / "demo-mods" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        build.problems.clear()
        build.check_mods(root)
        return [x for x in build.problems if "tool result" in x]

    def test_hook_result_cast_as_never_fails(self):
        found = self.casts("hooks/tools.tsx", "on('tool.call', async () => {\n  return { result: { text: 'x' } as never }\n})\n")
        self.assertEqual(len(found), 1)
        self.assertIn("mods/demo-mods/hooks/tools.tsx:2", found[0])

    def test_stub_result_cast_as_any_fails(self):
        found = self.casts("tests/a.test.ts", "on('tool.call', async () => ({ result: 'Ignore' as any }))\n")
        self.assertEqual(len(found), 1)

    def test_typed_result_and_other_casts_pass(self):
        text = ("on('tool.call', async () => ({ result: { stdout: '', stderr: '', interrupted: false } }))\n"
                "await $.session.append({ message } as never)\n"
                "const resultText = (v: unknown) => v as string\n")
        self.assertEqual(self.casts("tests/a.test.ts", text), [])

    # R4-01: the forms a line scan missed.
    def test_multi_line_result_cast_fails(self):
        text = "on('tool.call', async () => {\n  return {\n    result: {\n      text: t,\n    } as never,\n  }\n})\n"
        found = self.casts("hooks/tools.tsx", text)
        self.assertEqual(len(found), 1)
        self.assertIn("mods/demo-mods/hooks/tools.tsx:3", found[0])

    def test_as_unknown_as_fails(self):
        found = self.casts("tests/a.test.ts", "on('tool.call', async () => ({ result: x as unknown as string }))\n")
        self.assertEqual(len(found), 1)

    def test_angle_casts_fail(self):
        text = ("on('tool.call', async () => ({ result: <never>{ text: 'x' } }))\n"
                "on('tool.call', async () => ({ result: <any>'Ignore' }))\n")
        found = self.casts("tests/a.test.ts", text)
        self.assertEqual(len(found), 2)

    def test_shorthand_of_a_cast_result_fails(self):
        text = "on('tool.call', async () => {\n  const result = { text: 'x' } as never\n  return { result }\n})\n"
        found = self.casts("hooks/tools.tsx", text)
        self.assertEqual(len(found), 1)
        self.assertIn("tools.tsx:2", found[0])

    # R4-02: a cast that is not the result's, or not code, passes.
    def test_sibling_cast_comment_and_string_pass(self):
        text = ("on('tool.call', async () => ({ result: r, meta: m as never }))\n"
                "// result: x as any is banned\n"
                "/* result: y as never */\n"
                "const s = 'result: cast as any'\n"
                'const d = "result: z as never"\n'
                "const t = `result: w as never`\n"
                "const re = /result: v as never/\n"
                "const g = { result: Array<any>(), other: f<never>() }\n")
        self.assertEqual(self.casts("tests/a.test.ts", text), [])

    def test_known_limits_are_not_caught(self):
        """Pinned on purpose: a cast reached only through another name, or nested inside the
        value, is the type checker's business, not this lint's (it stays narrow)."""
        text = ("const r = { text: 'x' } as never\n"
                "on('tool.call', async () => ({ result: r }))\n"
                "on('tool.call', async () => ({ result: { text: t as never } }))\n")
        self.assertEqual(self.casts("tests/a.test.ts", text), [])


class Launcher(unittest.TestCase):
    """The /rw-<skill> list (build plan phase 1): generated from the registry, checked for drift."""
    def tearDown(self):
        build.problems.clear()

    def tree(self):
        tmp = Path(tempfile.mkdtemp())
        d = tmp / "mods" / build.LAUNCHER_MOD
        (d / ".claude-plugin").mkdir(parents=True)
        (d / "hooks").mkdir()
        (d / ".claude-plugin" / "plugin.json").write_text("{}", encoding="utf-8")
        return tmp

    ROSTERS = {"foundation": ["revenantworks-foundation-agentwright"]}
    DESCS = {"revenantworks-foundation-agentwright": "Designs agents. Trigger for guardrails."}

    def test_render_rows(self):
        text = build.render_launcher(self.ROSTERS, self.DESCS)
        self.assertIn('short: "agentwright", pack: "foundation"', text)
        self.assertIn('about: "Designs agents"', text)
        self.assertTrue(text.startswith("// GENERATED by tools/build.py"))

    def test_about_is_cut_at_a_word(self):
        about = build._launcher_about("word " * 40)
        self.assertLessEqual(len(about), 91)
        self.assertTrue(about.endswith("…"))

    def test_write_then_check_clean(self):
        root = self.tree()
        self.assertEqual(build.sync_launcher(self.ROSTERS, self.DESCS, root, write=True), 1)
        build.problems.clear()
        build.sync_launcher(self.ROSTERS, self.DESCS, root, write=False)
        self.assertEqual(build.problems, [])

    def test_check_fails_on_drift(self):
        root = self.tree()
        build.sync_launcher(self.ROSTERS, self.DESCS, root, write=True)
        build.problems.clear()
        build.sync_launcher({"foundation": []}, {}, root, write=False)
        self.assertTrue(any("drifts from the pack registry" in p for p in build.problems))

    def test_absent_mod_is_skipped(self):
        self.assertEqual(build.sync_launcher(self.ROSTERS, self.DESCS, Path(tempfile.mkdtemp()), write=False), 0)


if __name__ == "__main__":
    unittest.main()
