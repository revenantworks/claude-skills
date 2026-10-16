"""`build.py --parity` must not report DRIFT for a plugin Claude Code reads from this checkout.

A plugin installed from a local directory marketplace keeps an `installPath` cache copy in
installed_plugins.json, but `claude plugin list --json` reports `readFromFolder` for it: Claude
Code loads the checkout, not the cache. Comparing the stale cache copy then reports drift that
nothing loads. Parity now prefers the loaded-from-folder fact and compares only genuinely
cached installs. Fixtures are neutral temp folders; the real ~/.claude is never read.
"""
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402

PACK = "foundation"
PLUGIN_ID = f"{PACK}@revenantworks"


class ParityLoadedFromFolder(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home = Path(tmp.name)
        plugins = self.home / ".claude" / "plugins"
        self.cache = plugins / "cache" / "revenantworks" / PACK / "1.0.0"
        self.cache.mkdir(parents=True)
        (self.cache / "stale.md").write_text("an old cache copy\n", encoding="utf-8")
        (plugins / "installed_plugins.json").write_text(json.dumps({"plugins": {PLUGIN_ID: [
            {"scope": "user", "version": "1.0.0", "installPath": str(self.cache)}]}}),
            encoding="utf-8")

    def run_parity(self, folders):
        out = io.StringIO()
        with mock.patch("pathlib.Path.home", return_value=self.home), \
                mock.patch.object(build, "_plugin_folders", return_value=folders, create=True), \
                redirect_stdout(out):
            rc = build.parity({PACK: "standard"})
        return rc, out.getvalue()

    def test_cache_is_compared_even_when_the_cli_reports_a_checkout_load(self):
        # B7 (observation 0420), replacing the 0416-era "nothing to compare" skip: a desktop-app
        # session ran the cache copy while the CLI said "Read from" the checkout.
        rc, out = self.run_parity({PLUGIN_ID: str(build.PACKS / PACK)})
        self.assertEqual(rc, 1, out)
        self.assertIn("the CLI says loaded from checkout", out)
        self.assertIn("DRIFT", out)

    def test_genuinely_cached_install_still_compares_and_drifts(self):
        rc, out = self.run_parity({})
        self.assertEqual(rc, 1, out)
        self.assertIn("DRIFT", out)

    def test_folder_outside_this_checkout_still_compares_the_cache(self):
        elsewhere = self.home / "another-clone" / "packs" / PACK
        elsewhere.mkdir(parents=True)
        rc, out = self.run_parity({PLUGIN_ID: str(elsewhere)})
        self.assertEqual(rc, 1, out)
        self.assertNotIn("loaded from checkout", out)


class ParityCoversMods(unittest.TestCase):
    """B7 (observation 0420): a stale mod cache is drift, even while the CLI reports a checkout load."""

    def setUp(self):
        import shutil
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home = Path(tmp.name)
        plugins = self.home / ".claude" / "plugins"
        self.cache = plugins / "cache" / "revenantworks" / "dash" / "1.0.0"
        shutil.copytree(build.MODS / "dash", self.cache,
                        ignore=shutil.ignore_patterns(*build.PARITY_SKIP, "*.pyc", "node_modules"))
        (plugins / "installed_plugins.json").write_text(json.dumps({"plugins": {"dash@revenantworks": [
            {"scope": "user", "version": "1.0.0", "installPath": str(self.cache)}]}}), encoding="utf-8")

    def run_parity(self):
        out = io.StringIO()
        folders = {"dash@revenantworks": str(build.MODS / "dash")}
        with mock.patch("pathlib.Path.home", return_value=self.home), \
                mock.patch.object(build, "_plugin_folders", return_value=folders), redirect_stdout(out):
            rc = build.parity({}, mods=["dash"])
        return rc, out.getvalue()

    def test_mod_cache_matching_the_checkout_is_clean(self):
        rc, out = self.run_parity()
        self.assertEqual(rc, 0, out)
        self.assertIn("the CLI says loaded from checkout", out)

    def test_mod_cache_one_commit_stale_is_drift(self):
        stale = sorted(p for p in self.cache.rglob("*.ts") if p.is_file())[0]
        stale.write_text(stale.read_text(encoding="utf-8") + "\n// one commit older\n", encoding="utf-8")
        rc, out = self.run_parity()
        self.assertEqual(rc, 1, out)
        self.assertIn("DRIFT", out)
        self.assertIn(f"differs: {stale.relative_to(self.cache).as_posix()}", out)

    def test_the_mod_list_holds_dash_and_privacy(self):
        self.assertEqual(build.mod_plugins(), ["dash", "privacy"])


class PluginFolders(unittest.TestCase):
    def test_reads_read_from_folder_out_of_plugin_list_json(self):
        listing = [{"id": PLUGIN_ID, "readFromFolder": "/clone/packs/foundation"},
                   {"id": "scribe@revenantworks", "installPath": "/cache/scribe/1.0.0"}]

        def run(*_a, **_k):
            return subprocess.CompletedProcess([], 0, stdout=json.dumps(listing), stderr="")
        with mock.patch.object(build.shutil, "which", return_value="claude"):
            self.assertEqual(build._plugin_folders(run), {PLUGIN_ID: "/clone/packs/foundation"})

    def test_no_claude_on_path_or_a_failed_listing_yields_nothing(self):
        with mock.patch.object(build.shutil, "which", return_value=None):
            self.assertEqual(build._plugin_folders(), {})

        def bad(*_a, **_k):
            return subprocess.CompletedProcess([], 1, stdout="not json", stderr="")
        with mock.patch.object(build.shutil, "which", return_value="claude"):
            self.assertEqual(build._plugin_folders(bad), {})


if __name__ == "__main__":
    unittest.main()
