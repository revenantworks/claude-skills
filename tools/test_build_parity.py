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

    def test_plugin_read_from_this_checkout_is_not_drift(self):
        rc, out = self.run_parity({PLUGIN_ID: str(build.PACKS / PACK)})
        self.assertEqual(rc, 0, out)
        self.assertIn("loaded from checkout - nothing to compare", out)
        self.assertNotIn("DRIFT", out)

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
