"""Tests for docker_preflight.py: parsers, audit, check and prune-list over canned readings.

Run: python -m unittest discover -s <member>/scripts -p "test_*.py"
No live Docker or WSL is touched: every case feeds a readings dict.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import docker_preflight as dp  # noqa: E402

GIB = dp.GIB
NOW = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
ENGINE_OK = {"answers": True, "server_version": "28.0.0", "os": "Docker Desktop",
             "kernel": "6.6.87.2-microsoft-standard-WSL2", "desktop": "Docker Desktop 4.93.0"}


def readings(**over):
    rd = {"engine": dict(ENGINE_OK), "context": "desktop-linux",
          "host": {"ram_total": 32 * GIB, "ram_avail": 24 * GIB},
          "wslconfig": {"path": "<profile>/.wslconfig", "exists": True, "text": "[wsl2]\nprocessors=8\n"},
          "vhdx": [{"path": "<localappdata>/Docker/wsl/disk/docker_data.vhdx",
                    "owner": "Docker Desktop (default location)", "bytes": 60 * GIB, "drive_free": 200 * GIB}],
          "lease": None,
          "config": {"docker": {"ram_headroom_bytes": 2 * GIB, "disk_headroom_bytes": 20 * GIB}}}
    rd.update(over)
    return rd


class Parsers(unittest.TestCase):
    def test_sizes(self):
        self.assertEqual(dp.parse_size("8GB"), 8 * GIB)
        self.assertEqual(dp.parse_size("512mb"), 512 * 1024 ** 2)
        self.assertEqual(dp.parse_size("1099511627776"), 1024 ** 4)
        self.assertIsNone(dp.parse_size("eight"))
        self.assertEqual(dp.parse_human("2.5GB (75%)"), 2_500_000_000)
        self.assertEqual(dp.parse_human("0B"), 0)

    def test_wsl_list_utf16(self):
        raw = "  NAME              STATE           VERSION\r\n* Ubuntu-24.04      Stopped         2\r\n" \
              "  docker-desktop    Running         2\r\n".encode("utf-16-le")
        rows = dp.parse_wsl_list(dp.decode(raw))
        self.assertEqual([r["name"] for r in rows], ["Ubuntu-24.04", "docker-desktop"])
        self.assertTrue(rows[0]["default"])
        self.assertEqual(rows[1]["state"], "Running")

    def test_utf16_bom_is_stripped(self):
        raw = ("\ufeff" + "  NAME   STATE   VERSION\r\n").encode("utf-16-le")
        self.assertFalse(dp.decode(raw).startswith("\ufeff"))

    def test_source_carries_no_invisible_characters(self):
        # FX4: shieldwarden's invisible-unicode rule; a BOM is written as an escape, never raw.
        src = (Path(__file__).resolve().parent / "docker_preflight.py").read_text(encoding="utf-8")
        for ch in ("\ufeff", "\u200b", "\u200c", "\u200d", "\u2060"):
            self.assertNotIn(ch, src)

    def test_wslconfig_comments_and_case(self):
        s = dp.parse_wslconfig("# top\n[WSL2]\nMemory = 10GB # cap\n[experimental]\nsparseVhd=true\n")
        self.assertEqual(s["wsl2"]["memory"], "10GB")
        self.assertEqual(s["experimental"]["sparsevhd"], "true")

    def test_tasklist(self):
        t = '"vmmemWSL","4321","Services","0","12,582,912 K"\n'
        self.assertEqual(dp.parse_tasklist_mem(t), 12_582_912 * 1024)
        self.assertIsNone(dp.parse_tasklist_mem("INFO: No tasks are running"))

    def test_lease_state(self):
        self.assertEqual(dp.lease_state(None, NOW), "free")
        self.assertEqual(dp.lease_state({"holder": "x", "expires": "2026-10-02T00:00:00Z"}, NOW), "held")
        self.assertEqual(dp.lease_state({"holder": "x", "expires": "2026-09-30T00:00:00Z"}, NOW), "stale")
        self.assertEqual(dp.lease_state({"holder": "x", "expires": "soon"}, NOW), "stale")


class Audit(unittest.TestCase):
    def test_no_memory_key_reports_default_and_third(self):
        """Test case 1: no memory key on a 32 GB machine -> 16 GiB default, ~a third proposed."""
        rep = dp.audit(readings(), NOW)
        mem = rep["wslconfig"]["effective"]["memory"]
        self.assertEqual(mem, {"value": 16 * GIB, "source": "default"})
        self.assertTrue(any("16.0 GiB" in f and "10 GiB" in f for f in rep["findings"]), rep["findings"])

    def test_sparse_off_is_a_finding(self):
        rep = dp.audit(readings(), NOW)
        self.assertTrue(any("sparseVhd" in f for f in rep["findings"]))

    def test_engine_down_is_reported(self):
        rep = dp.audit(readings(engine={"answers": False, "error": "pipe not found"}), NOW)
        self.assertTrue(any("not answering" in f for f in rep["findings"]))


class Check(unittest.TestCase):
    LEASE = {"holder": "comfyrunner", "purpose": "video render", "expires": "2026-10-01T14:00:00Z",
             "est_vram_bytes": 14 * GIB, "est_ram_bytes": 20 * GIB}

    def test_lease_blocks_unattended(self):
        """Test case 2: comfyrunner holds 20 GB, the job needs 10 GB -> not go, unattended."""
        rep = dp.check(readings(lease=self.LEASE), NOW, 10 * GIB, None, "unattended")
        self.assertNotEqual(rep["verdict"], "go")
        self.assertFalse(rep["budget"]["ram"]["fits_host"])
        self.assertEqual(rep["budget"]["ram"]["lease_reserved"], 20 * GIB)

    def test_lease_without_ram_estimate_refuses_unattended(self):
        lease = dict(self.LEASE)
        del lease["est_ram_bytes"]
        rep = dp.check(readings(lease=lease), NOW, 2 * GIB, None, "unattended")
        self.assertEqual(rep["verdict"], "refuse")

    def test_fits_goes(self):
        rep = dp.check(readings(), NOW, 4 * GIB, 10 * GIB, "unattended")
        self.assertEqual(rep["verdict"], "go", rep["reasons"])

    def test_need_above_wsl_cap_reduces(self):
        rep = dp.check(readings(), NOW, 18 * GIB, None, "interactive")
        self.assertEqual(rep["verdict"], "reduce")
        self.assertFalse(rep["budget"]["ram"]["fits_wsl_cap"])

    def test_proposed_headroom_asks_or_refuses(self):
        rd = readings(config={})
        self.assertEqual(dp.check(rd, NOW, 2 * GIB, None, "interactive")["verdict"], "ask")
        self.assertEqual(dp.check(rd, NOW, 2 * GIB, None, "unattended")["verdict"], "refuse")

    def test_engine_down_refuses(self):
        rep = dp.check(readings(engine={"answers": False}), NOW, None, None, "interactive")
        self.assertEqual(rep["verdict"], "refuse")

    def test_disk_short_reduces(self):
        rd = readings()
        rd["vhdx"][0]["drive_free"] = 25 * GIB
        rep = dp.check(rd, NOW, None, 10 * GIB, "interactive")
        self.assertEqual(rep["verdict"], "reduce")


class PruneList(unittest.TestCase):
    def test_dry_list_and_one_command_by_id(self):
        """Test case 3: a dry list and one owner command; volumes only by name, only dangling."""
        out = dp.prune_list(
            [{"ID": "c1", "Names": "old", "Image": "x", "Status": "Exited (0)"}],
            [{"ID": "sha256:i1", "Size": "1GB"}],
            [{"Name": "cache_vol"}, {"Name": "pgdata"}],
            [{"type": "Build Cache", "reclaimable": "3GB"}],
            ["cache_vol", "in_use_vol"])
        self.assertEqual(out["owner_command"],
                         "docker rm c1; docker rmi sha256:i1; docker builder prune -f; docker volume rm cache_vol")
        self.assertIn("pgdata", out["dangling_volumes_listed_not_removed"])
        self.assertEqual(out["volumes_refused"][0]["name"], "in_use_vol")
        self.assertNotIn("prune -a", out["owner_command"])
        self.assertNotIn("volume prune", out["owner_command"])

    def test_no_volume_named_means_none_removed(self):
        out = dp.prune_list([], [], [{"Name": "pgdata"}], None, [])
        self.assertIsNone(out["owner_command"])
        self.assertEqual(out["volumes_in_command"], [])


class Cli(unittest.TestCase):
    def test_fixture_run_and_selftest(self):
        script = str(Path(dp.__file__))
        with tempfile.TemporaryDirectory() as tmp:
            fx = Path(tmp) / "r.json"
            fx.write_text(json.dumps(readings(lease=Check.LEASE)), encoding="utf-8")
            r = subprocess.run([sys.executable, script, "--mode", "check", "--need-ram-gb", "10",
                                "--run", "unattended", "--fixture", str(fx)],
                               capture_output=True, text=True, timeout=60)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertNotEqual(json.loads(r.stdout)["verdict"], "go")
        r = subprocess.run([sys.executable, script, "--selftest"], capture_output=True, text=True, timeout=60)
        self.assertIn("selftest: ok", r.stdout)


if __name__ == "__main__":
    unittest.main()
