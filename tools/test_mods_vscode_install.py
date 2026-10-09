"""mods/vscode/install.py: the dash extension lands in one versioned folder per VS Code, the
mods status bar it replaced and older dash copies are removed, and --dry-run writes nothing."""
import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "mods" / "vscode" / "install.py"


def load():
    spec = importlib.util.spec_from_file_location("vscode_install", SRC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestVscodeInstall(unittest.TestCase):
    def setUp(self):
        self.inst = load()
        self.version = json.loads((SRC.parent / "package.json").read_text(encoding="utf-8"))["version"]
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def run_install(self, dry_run=False):
        with contextlib.redirect_stdout(io.StringIO()):
            return self.inst.install(self.home, dry_run=dry_run)

    def test_package_names_the_dash_extension_and_the_dash_plugin_version(self):
        pkg = json.loads((SRC.parent / "package.json").read_text(encoding="utf-8"))
        plugin = json.loads((ROOT / "mods" / "dash" / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(pkg["name"], "dash")
        self.assertEqual(self.inst.PREFIX, f"{pkg['publisher']}.{pkg['name']}-")
        self.assertEqual(pkg["version"], plugin["version"])

    def test_installs_every_file_into_one_versioned_folder(self):
        written = self.run_install()
        dest = self.home / ".vscode" / "extensions" / f"revenantworks.dash-{self.version}"
        self.assertEqual(written, [dest])
        self.assertEqual(sorted(p.name for p in dest.iterdir()), sorted(self.inst.FILES))
        for name in self.inst.FILES:
            self.assertEqual((dest / name).read_bytes(), (SRC.parent / name).read_bytes())

    def test_removes_the_old_status_bar_and_older_dash_copies(self):
        ext = self.home / ".vscode" / "extensions"
        legacy = ext / "revenantworks.mods-statusbar-1.0.0"
        older = ext / "revenantworks.dash-0.9.0"
        other = ext / "someone.else-1.0.0"
        for d in (legacy, older, other):
            d.mkdir(parents=True)
            (d / "package.json").write_text("{}", encoding="utf-8")
        self.run_install()
        self.assertFalse(legacy.exists())
        self.assertFalse(older.exists())
        self.assertTrue(other.exists(), "another publisher's extension is never touched")
        self.assertTrue((ext / f"revenantworks.dash-{self.version}" / "extension.js").is_file())

    def test_insiders_only_when_present(self):
        self.assertEqual(len(self.run_install()), 1)
        (self.home / ".vscode-insiders").mkdir()
        written = self.run_install()
        self.assertEqual(len(written), 2)
        self.assertTrue((written[1] / "logic.js").is_file())
        self.assertIn(".vscode-insiders", str(written[1]))

    def test_dry_run_writes_and_removes_nothing(self):
        legacy = self.home / ".vscode" / "extensions" / "revenantworks.mods-statusbar-1.0.0"
        legacy.mkdir(parents=True)
        self.run_install(dry_run=True)
        self.assertTrue(legacy.exists())
        self.assertFalse((self.home / ".vscode" / "extensions" / f"revenantworks.dash-{self.version}").exists())


if __name__ == "__main__":
    unittest.main()
