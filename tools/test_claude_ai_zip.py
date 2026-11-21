"""Tests for claude_ai_zip.py: one plugin.json per zip, sub-plugin servers kept at the root (#0690)."""
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_ai_zip as cz  # noqa: E402


def git(root, *args):
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def put(root, rel, data):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data) if not isinstance(data, str) else data, encoding="utf-8")


class ClaudeAiZipTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        git(self.root, "init", "-q")
        base = "packs/gd"
        put(self.root, f"{base}/.claude-plugin/plugin.json", {"name": "gd", "version": "1.2.1"})
        put(self.root, f"{base}/skills/a/SKILL.md", "---\nname: a\n---\n")
        put(self.root, f"{base}/plugins/mcp/.claude-plugin/plugin.json", {"name": "mcp"})
        put(self.root, f"{base}/plugins/mcp/.mcp.json",
            {"mcpServers": {"godot": {"command": "python", "args": ["${CLAUDE_PLUGIN_ROOT}/scripts/s.py"]}}})
        put(self.root, f"{base}/plugins/lsp/.claude-plugin/plugin.json", {"name": "lsp"})
        put(self.root, f"{base}/plugins/lsp/.lsp.json",
            {"gdscript": {"command": "python", "args": ["${CLAUDE_PLUGIN_ROOT}/scripts/b.py"]}})
        put(self.root, f"{base}/untracked.txt", "x")
        git(self.root, "add", "packs/gd/.claude-plugin", "packs/gd/skills", "packs/gd/plugins")
        self.out = self.root / "dist"

    def names(self, z):
        with zipfile.ZipFile(z) as f:
            return set(f.namelist()), f

    def test_one_manifest_and_the_servers_at_the_root(self):
        z = cz.build("gd", self.out, self.root)
        with zipfile.ZipFile(z) as f:
            names = set(f.namelist())
            mcp = json.loads(f.read(".mcp.json"))
            lsp = json.loads(f.read(".lsp.json"))
        self.assertEqual([".claude-plugin/plugin.json"], sorted(n for n in names if n.endswith("plugin.json")))
        self.assertEqual(["${CLAUDE_PLUGIN_ROOT}/plugins/mcp/scripts/s.py"], mcp["mcpServers"]["godot"]["args"])
        self.assertEqual(["${CLAUDE_PLUGIN_ROOT}/plugins/lsp/scripts/b.py"], lsp["gdscript"]["args"])
        self.assertNotIn("untracked.txt", names)
        self.assertTrue(z.name.endswith("gd-claude-ai-v1.2.1.zip"))

    def test_a_server_defined_twice_is_refused(self):
        put(self.root, "packs/gd/.mcp.json", {"mcpServers": {"godot": {"command": "x"}}})
        git(self.root, "add", "packs/gd/.mcp.json")
        with self.assertRaises(SystemExit):
            cz.build("gd", self.out, self.root)

    def test_compare_names_a_top_level_entry_the_new_zip_lacks(self):
        old = self.root / "old.zip"
        with zipfile.ZipFile(old, "w") as f:
            f.writestr(".claude-plugin/plugin.json", "{}")
            f.writestr("hand-added.json", "{}")
        new = cz.build("gd", self.out, self.root)
        self.assertEqual({"hand-added.json"}, cz.top_level(old) - cz.top_level(new))


if __name__ == "__main__":
    unittest.main()
