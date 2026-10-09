"""Tests for install.py: a replaced extension leaves both the folder and VS Code's registry.

Run: python -m unittest discover -s mods/vscode -p "test_*.py"
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import install  # noqa: E402


def entry(ext_id: str, folder: str, version: str = "0.1.0") -> dict:
    return {"identifier": {"id": ext_id}, "version": version, "location": {"$mid": 1, "fsPath": f"/nowhere/{folder}", "scheme": "file"}, "relativeLocation": folder}


class InstallTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.ext = self.home / ".vscode" / "extensions"
        (self.ext / "revenantworks.mods-statusbar-0.3.0").mkdir(parents=True)
        (self.ext / "revenantworks.dash-0.9.0").mkdir()
        (self.ext / "someone.other-1.2.3").mkdir()
        self.entries = [
            entry("revenantworks.mods-statusbar", "revenantworks.mods-statusbar-0.3.0", "0.3.0"),
            entry("someone.other", "someone.other-1.2.3", "1.2.3"),
            entry("Revenantworks.Dash", "revenantworks.dash-0.9.0", "0.9.0"),
            entry("someone.gone", "someone.gone-2.0.0", "2.0.0"),
        ]
        (self.ext / "extensions.json").write_text(json.dumps(self.entries), encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_install(self, which, runner=lambda argv: 1, dry=False):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            install.install(self.home, dry_run=dry, which=which, runner=runner)
        return out.getvalue()

    def registry(self) -> list:
        return json.loads((self.ext / "extensions.json").read_text(encoding="utf-8"))

    def test_without_the_code_cli_the_registry_entry_goes_with_the_folder(self) -> None:
        self.run_install(which=lambda name: None)
        ids = [e["identifier"]["id"] for e in self.registry()]
        # The legacy and old dash entries are gone; another publisher's entries stay, even a stale one.
        self.assertEqual(ids, ["someone.other", "someone.gone"])
        self.assertFalse((self.ext / "revenantworks.mods-statusbar-0.3.0").exists())
        self.assertTrue((self.ext / "revenantworks.dash-1.0.0" / "extension.js").is_file())

    def test_the_code_cli_uninstalls_the_legacy_id_first(self) -> None:
        calls: list[list[str]] = []

        def runner(argv: list[str]) -> int:
            calls.append(argv)
            return 0

        self.run_install(which=lambda name: f"/bin/{name}", runner=runner)
        self.assertEqual(calls, [["/bin/code", "--uninstall-extension", "revenantworks.mods-statusbar"]])
        self.assertNotIn("revenantworks.mods-statusbar", [e["identifier"]["id"] for e in self.registry()])

    def test_a_registry_that_is_not_a_list_is_left_alone(self) -> None:
        (self.ext / "extensions.json").write_text('{"odd": true}', encoding="utf-8")
        self.run_install(which=lambda name: None)
        self.assertEqual((self.ext / "extensions.json").read_text(encoding="utf-8"), '{"odd": true}')

    def test_dry_run_writes_nothing(self) -> None:
        before = (self.ext / "extensions.json").read_bytes()
        out = self.run_install(which=lambda name: None, dry=True)
        self.assertIn("unregister", out)
        self.assertEqual((self.ext / "extensions.json").read_bytes(), before)
        self.assertTrue((self.ext / "revenantworks.mods-statusbar-0.3.0").is_dir())


if __name__ == "__main__":
    unittest.main()
