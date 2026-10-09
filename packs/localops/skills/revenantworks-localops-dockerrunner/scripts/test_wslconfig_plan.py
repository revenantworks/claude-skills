"""Tests for wslconfig_plan.py: section-aware edits, line endings kept, never in place."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wslconfig_plan as wp  # noqa: E402

SCRIPT = str(Path(wp.__file__))


def cli(*args):
    r = subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True, timeout=60)
    return r.returncode, json.loads(r.stdout) if r.stdout.strip().startswith("{") else r.stdout


class Plan(unittest.TestCase):
    def test_replace_keeps_other_lines_and_crlf(self):
        before = "# owner notes\r\n[wsl2]\r\nmemory=24GB\r\nprocessors=8\r\n\r\n[experimental]\r\nsparseVhd=false\r\n"
        after = wp.plan(before, {"memory": "10GB", "sparseVhd": "true"}, "\r\n")
        self.assertEqual(after.count("\r\n"), before.count("\r\n"))
        self.assertNotIn("\n", after.replace("\r\n", ""))
        self.assertIn("# owner notes", after)
        self.assertIn("processors=8", after)
        self.assertEqual(wp.validate(before, after, {"memory": "10GB", "sparseVhd": "true"}), [])

    def test_adds_into_existing_section_not_another(self):
        before = "[wsl2]\nprocessors=4\n\n[experimental]\nautoMemoryReclaim=gradual\n"
        after = wp.plan(before, {"memory": "8GB"}, "\n")
        parsed = wp.parse(after)
        self.assertEqual(parsed["wsl2"], {"processors": "4", "memory": "8GB"})
        self.assertEqual(parsed["experimental"], {"automemoryreclaim": "gradual"})
        self.assertEqual(after.count("[wsl2]"), 1)

    def test_missing_sections_are_appended(self):
        after = wp.plan("[general]\ninstanceIdleTimeout=60000\n", {"memory": "8GB", "sparseVhd": "true"}, "\n")
        parsed = wp.parse(after)
        self.assertEqual(parsed["general"], {"instanceidletimeout": "60000"})
        self.assertEqual(parsed["wsl2"], {"memory": "8GB"})
        self.assertEqual(parsed["experimental"], {"sparsevhd": "true"})

    def test_validate_catches_a_dropped_key(self):
        errs = wp.validate("[wsl2]\nswap=4GB\n", "[wsl2]\nmemory=8GB\n", {"memory": "8GB"})
        self.assertTrue(any("swap" in e for e in errs), errs)


class Cli(unittest.TestCase):
    def test_writes_beside_never_in_place_and_proposes_a_third(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / ".wslconfig"
            src.write_bytes(b"[wsl2]\r\nprocessors=8\r\n")
            code, out = cli("--source", str(src), "--total-ram-gb", "32")
            self.assertEqual(code, 0, out)
            self.assertEqual(src.read_bytes(), b"[wsl2]\r\nprocessors=8\r\n")  # untouched
            prop = Path(out["proposal"])
            self.assertEqual(prop.name, ".wslconfig.proposed")
            self.assertIn(b"memory=10GB\r\n", prop.read_bytes())
            self.assertTrue(any("PROPOSED" in n for n in out["notes"]))
            self.assertIn(".bak-", out["owner_command"])
            self.assertTrue(out["owner_command"].endswith("wsl --shutdown"))

    def test_refuses_above_installed_ram(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out = cli("--source", str(Path(tmp) / ".wslconfig"), "--total-ram-gb", "16",
                            "--memory-gb", "24")
            self.assertEqual(code, 2)
            self.assertEqual(out["status"], "refused")
            self.assertFalse((Path(tmp) / ".wslconfig.proposed").exists())

    def test_no_source_file_still_plans_without_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out = cli("--source", str(Path(tmp) / ".wslconfig"), "--memory-gb", "8", "--dry-run")
            self.assertEqual(code, 0)
            self.assertEqual(out["status"], "dry-run")
            self.assertNotIn(".bak-", out["owner_command"])
            self.assertFalse((Path(tmp) / ".wslconfig.proposed").exists())

    def test_selftest(self):
        code, out = cli("--selftest")
        self.assertIn("selftest: ok", out)


if __name__ == "__main__":
    unittest.main()
