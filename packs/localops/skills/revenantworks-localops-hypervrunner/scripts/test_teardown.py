"""Tests for hypervrunner's controlled teardown (soft delete) and purge.

Pure logic and temp files only: PowerShell is a fake, no Hyper-V call is ever made.
Run: python -m unittest discover -s scripts -p "test_*.py"
"""
import json
import os
import re
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import hyperv_common as hc
import teardown
import vmctl

G = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
OTHER = "12345678-1234-1234-1234-123456789abc"
NOW = datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc)
# Built by concatenation so this file never carries the literal command text.
RM_VM = "Remove-" + "VM"
RM_VHD = "Remove-" + "VHD"


class FakePS:
    """Stands in for run_ps. Answers the three teardown scripts; records every call."""

    def __init__(self, probe, gone=0, fail_unregister=False):
        self.probe, self.gone, self.fail_unregister, self.calls = probe, gone, fail_unregister, []

    def __call__(self, script, timeout=120):
        self.calls.append(script)
        if script == teardown.probe_ps(G):
            return self.probe
        if script == teardown.unregister_ps(G):
            if self.fail_unregister:
                raise hc.PSError("access denied")
            return None
        if script == teardown.gone_ps(G):
            return self.gone
        raise AssertionError(f"unexpected PowerShell: {script[:80]}")

    def unregistered(self):
        return any(RM_VM in c for c in self.calls)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="hv-td-"))
        self.state = self.tmp / "state"
        self.state.mkdir()
        p = mock.patch.object(hc, "own_dir", return_value=self.state)
        p.start()
        self.addCleanup(p.stop)
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.root = hc.disk_root()
        self.root.mkdir(parents=True)
        self.disk = self.root / "V.vhdx"
        self.disk.write_bytes(b"x" * 1000)

    def probe(self, **over):
        d = {"found": True, "id": G, "name": "V", "state": "Off", "notes": "hypervrunner:own",
             "checkpoints": [], "disks": [str(self.disk)], "other_disks": []}
        d.update(over)
        return d

    def own(self, ephemeral=False, run_id=None, cleanroom=False):
        hc.record_own_vm(G, "V", cleanroom, ephemeral=ephemeral, run_id=run_id)

    def plan(self, probe=None, resolve=None):
        kw = {"resolve": resolve} if resolve else {}
        return teardown.build_plan(G, probe or self.probe(), hc.read_register(), hc.disk_root(),
                                   hc.read_protected(), **kw)

    def reasons(self, plan):
        return " ".join(plan["reasons"])


class CreateMarksTests(unittest.TestCase):
    def test_every_vm_gets_the_marker_and_its_disk_goes_in_the_skill_folder(self):
        joined = "; ".join(vmctl.build_create_steps("V", 4, 64, disk_root="D:\\hv"))
        self.assertIn("Join-Path 'D:\\hv' ('V' + '.vhdx')", joined)
        self.assertIn("Set-VM -Name 'V' -Notes 'hypervrunner:own'", joined)
        self.assertNotIn("VirtualHardDiskPath", joined)
        cr = "; ".join(vmctl.build_create_steps("C", 4, 64, cleanroom=True, disk_root="D:\\hv"))
        self.assertIn("'hypervrunner:own hypervrunner:cleanroom golden=golden'", cr)

    def test_plan_create_ephemeral_carries_a_run_id(self):
        with mock.patch.object(vmctl, "preflight", return_value={"verdict": "go"}), \
                mock.patch("builtins.print") as out:
            self.assertEqual(vmctl.main(["plan-create", "--name", "E", "--memory-gb", "2", "--ephemeral"]), 0)
        plan = json.loads(out.call_args[0][0])
        self.assertTrue(plan["params"]["ephemeral"])
        self.assertRegex(plan["params"]["run_id"], r"^[0-9a-f]{12}$")
        self.assertTrue(plan["params"]["disk_root"])

    def test_record_keeps_ephemeral_and_run_id(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(hc, "own_dir", return_value=Path(d)):
            hc.record_own_vm(G.upper(), "V", False, ephemeral=True, run_id="r1")
            rec = hc.read_register()[G]
            self.assertEqual((rec["ephemeral"], rec["run_id"]), (True, "r1"))


class PlanTests(Base):
    def test_go_for_own_marked_off_vm(self):
        self.own()
        p = self.plan()
        self.assertEqual(p["verdict"], "go", p["reasons"])
        self.assertEqual(p["disks"][0]["size_bytes"], 1000)
        self.assertTrue(p["disks"][0]["to"].endswith(os.path.join("_quarantine", G, "0-V.vhdx")))
        self.assertRegex(p["sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(p["authority"], "needs the user's OK")

    def test_lock1_guid_not_in_creation_record(self):
        p = self.plan()  # marker present, name right, but never recorded at creation
        self.assertEqual(p["verdict"], "refuse")
        self.assertIn("lock 1", self.reasons(p))

    def test_lock2_marker_missing(self):
        self.own()
        p = self.plan(self.probe(notes="build box"))
        self.assertEqual(p["verdict"], "refuse")
        self.assertIn("lock 2", self.reasons(p))

    def test_guid_from_probe_must_match(self):
        self.own()
        p = self.plan(self.probe(id=OTHER))
        self.assertIn("GUID", self.reasons(p))
        self.assertEqual(p["verdict"], "refuse")

    def test_disk_outside_the_skill_folder(self):
        self.own()
        outside = self.tmp / "elsewhere.vhdx"
        outside.write_bytes(b"y")
        p = self.plan(self.probe(disks=[str(outside)]))
        self.assertEqual(p["verdict"], "refuse")
        self.assertIn("disk lock", self.reasons(p))

    def test_resolved_path_decides_not_the_spelling(self):
        # A junction inside the folder that points out: the spelled path is inside, the real one not.
        self.own()
        real_out = str(self.tmp / "out" / "V.vhdx")
        fake = lambda s: real_out if os.path.normcase(s) == os.path.normcase(str(self.disk)) \
            else os.path.realpath(s)
        p = self.plan(resolve=fake)
        self.assertEqual(p["verdict"], "refuse")
        self.assertIn("disk lock", self.reasons(p))

    @unittest.skipUnless(os.name == "nt", "junctions are a Windows feature")
    def test_real_junction_pointing_out_is_refused(self):
        try:
            import _winapi
        except ImportError:
            self.skipTest("no _winapi")
        target = self.tmp / "target"
        target.mkdir()
        (target / "J.vhdx").write_bytes(b"z" * 10)
        link = self.root / "link"
        _winapi.CreateJunction(str(target), str(link))
        self.own()
        p = self.plan(self.probe(disks=[str(link / "J.vhdx")]))
        self.assertEqual(p["verdict"], "refuse")
        self.assertIn("disk lock", self.reasons(p))

    def test_protected_disk_and_clean_room_vm(self):
        self.own()
        teardown.protect(disk=str(self.disk))
        self.assertIn("protected", self.reasons(self.plan()))
        hc.write_json(hc.protected_path(), {"disks": [], "checkpoints": []})
        self.own(cleanroom=True)
        p = self.plan(self.probe(notes="hypervrunner:own hypervrunner:cleanroom golden=golden"))
        self.assertEqual(p["verdict"], "refuse")
        self.assertIn("clean-room", self.reasons(p))

    def test_running_vm_checkpoints_and_shared_disk(self):
        self.own()
        self.assertIn("not Off", self.reasons(self.plan(self.probe(state="Running"))))
        self.assertIn("checkpoint", self.reasons(self.plan(self.probe(checkpoints=[OTHER]))))
        self.assertIn("another VM", self.reasons(self.plan(self.probe(other_disks=[str(self.disk)]))))

    def test_sha_follows_the_disk_size(self):
        self.own()
        a = self.plan()["sha256"]
        self.disk.write_bytes(b"x" * 1001)
        self.assertNotEqual(a, self.plan()["sha256"])

    def test_vm_not_found(self):
        self.own()
        p = self.plan({"found": False})
        self.assertEqual(p["verdict"], "refuse")


class ExecuteTests(Base):
    def run_exec(self, ps, sha=None, run_id=None, owner_ok=False):
        if sha is None:
            sha = teardown.plan_live(G, ps=ps)["sha256"]
        return teardown.execute(G, sha, run_id=run_id, owner_ok=owner_ok, ps=ps, now=NOW)

    def test_sha_mismatch_runs_nothing(self):
        self.own()
        ps = FakePS(self.probe())
        out = self.run_exec(ps, sha="0" * 64, owner_ok=True)
        self.assertEqual(out["status"], "refused")
        self.assertFalse(ps.unregistered())
        self.assertTrue(self.disk.exists())

    def test_needs_owner_ok_unless_ephemeral_same_run(self):
        self.own()
        ps = FakePS(self.probe())
        self.assertEqual(self.run_exec(ps)["status"], "refused")
        self.assertFalse(ps.unregistered())
        self.own(ephemeral=True, run_id="r1")
        self.assertEqual(self.run_exec(ps, run_id="r2")["status"], "refused")
        self.assertFalse(ps.unregistered())
        out = self.run_exec(ps, run_id="r1")
        self.assertEqual(out["status"], "done", out)
        self.assertEqual(out["authority"], "ephemeral, same run")

    def test_soft_delete_moves_logs_and_verifies(self):
        self.own()
        ps = FakePS(self.probe())
        out = self.run_exec(ps, owner_ok=True)
        self.assertEqual(out["status"], "done", out)
        self.assertEqual(out["verify"]["verdict"], "PASS")
        self.assertTrue(ps.unregistered())
        self.assertFalse(self.disk.exists())
        q = self.root / "_quarantine" / G
        self.assertEqual((q / "0-V.vhdx").stat().st_size, 1000)
        man = json.loads((q / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(man["vm"]["id"], G)
        self.assertEqual(man["disks"][0]["from"], str(self.disk))
        log = (self.state / "teardown-log.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(json.loads(log[-1])["event"], "teardown")
        self.assertTrue(hc.read_register()[G]["torn_down"])
        # torn down once: a second plan refuses
        self.assertEqual(self.plan()["verdict"], "refuse")

    def test_verify_fails_when_vm_still_registered(self):
        self.own()
        out = self.run_exec(FakePS(self.probe(), gone=1), owner_ok=True)
        self.assertEqual(out["verify"]["verdict"], "FAIL")
        self.assertEqual(teardown.exit_code(out), 1)

    def test_unregister_failure_moves_nothing(self):
        self.own()
        out = self.run_exec(FakePS(self.probe(), fail_unregister=True), owner_ok=True)
        self.assertEqual(out["status"], "error")
        self.assertTrue(self.disk.exists())

    def test_quarantine_failure_leaves_the_vm_registered(self):
        # Audit H-3: the quarantine folder is made (and checked writable) before the unregister,
        # so a filesystem failure costs nothing.
        self.own()
        ps = FakePS(self.probe())
        sha = teardown.plan_live(G, ps=ps)["sha256"]
        with mock.patch.object(teardown.os, "makedirs", side_effect=OSError("disk full")):
            out = teardown.execute(G, sha, owner_ok=True, ps=ps, now=NOW)
        self.assertEqual(out["status"], "error", out)
        self.assertIn("quarantine", out["reasons"][0])
        self.assertFalse(ps.unregistered())
        self.assertTrue(self.disk.exists())

    def test_unwritable_quarantine_leaves_the_vm_registered(self):
        self.own()
        ps = FakePS(self.probe())
        sha = teardown.plan_live(G, ps=ps)["sha256"]
        with mock.patch.object(teardown.os, "access", return_value=False):
            out = teardown.execute(G, sha, owner_ok=True, ps=ps, now=NOW)
        self.assertEqual(out["status"], "error", out)
        self.assertFalse(ps.unregistered())
        self.assertFalse((self.root / "_quarantine" / G).exists())

    def test_unregister_failure_leaves_no_quarantine_entry(self):
        self.own()
        out = self.run_exec(FakePS(self.probe(), fail_unregister=True), owner_ok=True)
        self.assertEqual(out["status"], "error")
        self.assertFalse((self.root / "_quarantine" / G).exists())
        self.assertEqual(self.plan()["verdict"], "go")

    def test_unregister_script_is_guid_and_marker_locked(self):
        s = teardown.unregister_ps(G)
        self.assertIn(G, s)
        self.assertIn("hypervrunner:own", s)
        self.assertIn(RM_VM + " -VM $v -Force", s)
        self.assertNotIn(RM_VM + " -Name", s)
        self.assertNotIn('"', s + teardown.probe_ps(G) + teardown.gone_ps(G))
        with self.assertRaises(ValueError):
            teardown.unregister_ps("V; " + RM_VM + " x")


class PurgeTests(Base):
    def torn_down(self, when):
        self.own()
        teardown.execute(G, teardown.plan_live(G, ps=FakePS(self.probe()))["sha256"], owner_ok=True,
                         ps=FakePS(self.probe()), now=when)
        return self.root / "_quarantine" / G

    def test_due_only_after_the_configured_days(self):
        q = self.torn_down(NOW - timedelta(days=8))
        self.assertEqual(teardown.purge(due=True, now=NOW), [])  # no purge_after_days set
        hc.write_json(self.state / "config.json", {"purge_after_days": 10})
        self.assertEqual(teardown.purge(due=True, now=NOW), [])
        hc.write_json(self.state / "config.json", {"purge_after_days": 7})
        res = teardown.purge(due=True, now=NOW)
        self.assertEqual(res[0]["status"], "purged", res)
        self.assertEqual(res[0]["verify"]["verdict"], "PASS")
        self.assertFalse(q.exists())
        log = (self.state / "teardown-log.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(json.loads(log[-1])["event"], "purge")

    def test_owner_entry_purge(self):
        q = self.torn_down(NOW)
        res = teardown.purge(entry=G, now=NOW)
        self.assertEqual(res[0]["status"], "purged")
        self.assertFalse(q.exists())

    def test_refuses_a_file_outside_the_entry_or_changed(self):
        q = self.torn_down(NOW)
        victim = self.tmp / "keep.vhdx"
        victim.write_bytes(b"k" * 1000)
        man = json.loads((q / "manifest.json").read_text(encoding="utf-8"))
        man["disks"][0]["to"] = str(victim)
        (q / "manifest.json").write_text(json.dumps(man), encoding="utf-8")
        self.assertEqual(teardown.purge(entry=G, now=NOW)[0]["status"], "refused")
        self.assertTrue(victim.exists())
        man["disks"][0]["to"] = str(q / "0-V.vhdx")
        man["disks"][0]["size_bytes"] = 5
        (q / "manifest.json").write_text(json.dumps(man), encoding="utf-8")
        self.assertEqual(teardown.purge(entry=G, now=NOW)[0]["status"], "refused")
        self.assertTrue((q / "0-V.vhdx").exists())

    def test_purge_command_is_the_owners(self):
        c = teardown.purge_command(G)
        self.assertEqual(c["run_by"], "owner")
        self.assertIn(f"teardown.py purge --entry {G}", c["command"])
        with self.assertRaises(ValueError):
            teardown.purge_command("x; del y")


class LockSurfaceTests(unittest.TestCase):
    def test_remove_commands_live_only_in_teardown(self):
        # Owner 2026-10-02: the teardown/purge script is the only caller of the remove commands.
        remove = re.compile(r"(?i)" + RM_VM + r"(?![\w-])|" + RM_VHD + r"|os\.remove|os\.unlink|shutil\.rmtree")
        restore = re.compile(r"(?i)Restore-" + "VM")
        for f in Path(__file__).resolve().parent.glob("*.py"):
            if f.name.startswith("test_"):
                continue
            text = f.read_text(encoding="utf-8")
            if f.name != "teardown.py":
                self.assertIsNone(remove.search(text), f"{f.name} carries a remove command")
            if f.name not in ("cleanroom.py", "vmctl.py"):
                self.assertIsNone(restore.search(text), f"{f.name} carries a restore command")
        self.assertNotIn("shutil.rmtree", (Path(teardown.__file__)).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
