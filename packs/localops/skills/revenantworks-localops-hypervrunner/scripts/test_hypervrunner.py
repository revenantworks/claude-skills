"""Tests for hypervrunner's scripts. Pure logic only: no PowerShell, Hyper-V or sandbox runs.

Run: python -m unittest discover -s scripts -p "test_*.py"
"""
import json
import re
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock
from pathlib import Path

import cleanroom
import hyperv_audit
import hyperv_common as hc
import hyperv_setup
import sandbox_config
import vmctl

NOW = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)
VID, GID = "11111111-2222-3333-4444-555555555555", "66666666-7777-8888-9999-000000000000"
GIB = 1024 ** 3


def probe(**over):
    base = {"os": {"caption": "Windows 11 Pro", "build": 26200, "total_kb": 32 * 1024 * 1024,
                   "free_kb": 16 * 1024 * 1024, "commit_free_kb": 20 * 1024 * 1024},
            "hyperv_module": True, "vmms": "Running", "user": "PC\\tester",
            "token_in_group": True, "account_in_group": True, "elevated": False,
            "vms": [], "switches": [], "guardian": True, "wsb_cli": True, "sandbox_exe": True}
    base.update(over)
    return base


class CommonTests(unittest.TestCase):
    def test_ps_quote_doubles_every_single_quote_form(self):
        self.assertEqual(hc.ps_quote("it's"), "'it''s'")
        for q in "\u2018\u2019\u201a\u201b":
            self.assertEqual(hc.ps_quote(f"a{q}b"), f"'a{q}{q}b'")

    def test_ps_quote_refuses_control_characters(self):
        with self.assertRaises(ValueError):
            hc.ps_quote("a\nRemove-VM x")

    def test_check_name_allowlist(self):
        self.assertEqual(hc.check_name("Win11 Test-1"), "Win11 Test-1")
        for bad in ("a;b", "$x", "a'b", " lead", "", "x" * 64, "a`b"):
            with self.assertRaises(ValueError):
                hc.check_name(bad)

    def test_run_ps_refuses_double_quote_before_launching(self):
        with self.assertRaises(ValueError):
            hc.run_ps('Write-Host "x"')

    def test_worst_verdict(self):
        self.assertEqual(hc.worst("go", "ask"), "ask")
        self.assertEqual(hc.worst("reduce", "unmeasured", "go"), "unmeasured")
        self.assertEqual(hc.worst("refuse", "ask"), "refuse")

    def test_ram_go_with_owner_headroom(self):
        v = hc.ram_verdict(4 * GIB, 16 * GIB, 20 * GIB, 32 * GIB, 2 * GIB, {"status": "none"})
        self.assertEqual(v["verdict"], "go")

    def test_ram_reduce_when_short(self):
        v = hc.ram_verdict(16 * GIB, 8 * GIB, 20 * GIB, 32 * GIB, 2 * GIB, {"status": "none"})
        self.assertEqual(v["verdict"], "reduce")

    def test_ram_proposed_headroom_asks_or_refuses(self):
        self.assertEqual(hc.ram_verdict(4 * GIB, 16 * GIB, 20 * GIB, 32 * GIB)["verdict"], "ask")
        v = hc.ram_verdict(4 * GIB, 16 * GIB, 20 * GIB, 32 * GIB, mode="unattended")
        self.assertEqual(v["verdict"], "refuse")
        self.assertIn("PROPOSED", v["headroom_source"])

    def test_ram_live_lease_asks_interactive_refuses_unattended(self):
        lease = {"status": "live", "holder": "comfyrunner", "purpose": "render"}
        self.assertEqual(hc.ram_verdict(4 * GIB, 16 * GIB, 20 * GIB, 32 * GIB, GIB, lease)["verdict"], "ask")
        self.assertEqual(hc.ram_verdict(4 * GIB, 16 * GIB, 20 * GIB, 32 * GIB, GIB, lease,
                                        "unattended")["verdict"], "refuse")

    def test_ram_unmeasured(self):
        self.assertEqual(hc.ram_verdict(4 * GIB, None, 20 * GIB, 32 * GIB, GIB)["verdict"], "unmeasured")

    def test_read_lease_live_and_expired(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "gpu-lease.json"
            f.write_text(json.dumps({"holder": "lmstudiorunner", "expires": (NOW + timedelta(minutes=5)).isoformat()}))
            self.assertEqual(hc.read_lease(NOW, f)["status"], "live")
            f.write_text(json.dumps({"holder": "lmstudiorunner", "expires": (NOW - timedelta(minutes=5)).isoformat()}))
            self.assertEqual(hc.read_lease(NOW, f)["status"], "stale")
            self.assertEqual(hc.read_lease(NOW, Path(d) / "none.json")["status"], "none")

    def test_read_lease_carries_the_ram_estimate(self):
        # Owner Q24: GPU holders record est_ram_bytes; the reader passes it on, None when absent.
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "gpu-lease.json"
            exp = (NOW + timedelta(minutes=5)).isoformat()
            f.write_text(json.dumps({"holder": "comfyrunner", "expires": exp, "est_ram_bytes": 8 * GIB}))
            self.assertEqual(hc.read_lease(NOW, f)["est_ram_bytes"], 8 * GIB)
            f.write_text(json.dumps({"holder": "comfyrunner", "expires": exp}))
            self.assertIsNone(hc.read_lease(NOW, f)["est_ram_bytes"])


class AuditTests(unittest.TestCase):
    def test_probe_is_read_only_and_has_no_double_quote(self):
        self.assertNotIn('"', hyperv_audit.PROBE)
        mutating = re.compile(r"\b(Set|New|Remove|Start|Stop|Restore|Enable|Disable|Add|Checkpoint)-"
                              r"(VM|WindowsOptionalFeature|LocalGroupMember|HgsGuardian)")
        self.assertIsNone(mutating.search(hyperv_audit.PROBE))

    def test_group_in_account_not_token_says_sign_out_not_elevate(self):
        a = hyperv_audit.analyse(probe(token_in_group=False, account_in_group=True), {"status": "none"}, NOW)
        self.assertEqual(a["ready"]["vm"], "sign-out-in")
        self.assertNotIn("add-to-group", a["needs_setup"])
        text = " ".join(a["findings"])
        self.assertIn("sign out", text)
        self.assertNotRegex(text, r"(?i)run as administrator|elevate it|RunAs")

    def test_not_in_group_needs_setup(self):
        a = hyperv_audit.analyse(probe(token_in_group=False, account_in_group=False), {}, NOW)
        self.assertIn("add-to-group", a["needs_setup"])
        self.assertEqual(a["ready"]["vm"], "needs-setup")

    def test_hyperv_off_and_no_guardian(self):
        a = hyperv_audit.analyse(probe(vmms="absent", hyperv_module=False, guardian=False), {}, NOW)
        self.assertEqual(set(a["needs_setup"]) & {"enable-hyperv", "create-guardian"},
                         {"enable-hyperv", "create-guardian"})

    def test_golden_age_and_profile_findings(self):
        old = (NOW - timedelta(days=45)).isoformat()
        vm = {"name": "CR1", "state": "Off", "generation": 2, "secure_boot": "On",
              "secure_boot_template": "MicrosoftWindows", "tpm": False,
              "notes": "hypervrunner:cleanroom golden=golden",
              "checkpoints": [{"name": "golden", "id": "x", "created": old}]}
        a = hyperv_audit.analyse(probe(vms=[vm]), {}, NOW)
        text = " ".join(a["findings"])
        self.assertIn("45.0 days old", text)
        self.assertIn("security profile incomplete", text)
        self.assertEqual(a["ready"]["cleanroom"], "ready")

    def test_no_sandbox_feature(self):
        a = hyperv_audit.analyse(probe(sandbox_exe=False, wsb_cli=False), {}, NOW)
        self.assertIn("enable-sandbox", a["needs_setup"])


class SetupTests(unittest.TestCase):
    def test_only_needed_steps_and_never_self_elevates(self):
        s, steps = hyperv_setup.build_script({"needs_setup": ["add-to-group", "create-guardian"],
                                              "user": "PC\\o'tester"})
        self.assertEqual(steps, ["add-to-group", "create-guardian"])
        self.assertIn("Add-LocalGroupMember -SID 'S-1-5-32-578' -Member 'PC\\o''tester'", s)
        self.assertIn("New-HgsGuardian -Name UntrustedGuardian", s)
        self.assertNotIn("Enable-WindowsOptionalFeature", s)
        self.assertIn("IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)", s)
        self.assertNotRegex(s, r"(?i)bypass|-Verb\s+RunAs|Invoke-WebRequest|DownloadString")

    def test_nothing_to_do(self):
        self.assertEqual(hyperv_setup.build_script({"needs_setup": []}), (None, []))

    def test_external_switch_needs_adapter(self):
        with self.assertRaises(ValueError):
            hyperv_setup.build_script({"needs_setup": []}, external_switch="Ext")


class VmctlTests(unittest.TestCase):
    def test_create_steps_carry_the_gen2_profile(self):
        steps = vmctl.build_create_steps("Win11 Test", 4, 64)
        joined = "; ".join(steps)
        self.assertIn("-Generation 2", joined)
        self.assertIn("-EnableSecureBoot On -SecureBootTemplate MicrosoftWindows", joined)
        self.assertIn("Set-VMKeyProtector -VMName 'Win11 Test' -NewLocalKeyProtector", joined)
        self.assertIn("Enable-VMTPM -VMName 'Win11 Test'", joined)
        self.assertNotIn('"', joined)

    def test_linux_template(self):
        self.assertIn("MicrosoftUEFICertificateAuthority", "; ".join(vmctl.build_create_steps("L1", 2, 32, linux=True)))

    def test_cleanroom_tag(self):
        self.assertIn("hypervrunner:cleanroom golden=golden", "; ".join(vmctl.build_create_steps("C", 4, 64, cleanroom=True)))

    def test_verify_fails_when_tpm_off(self):
        out = vmctl.verify_profile({"name": "V", "generation": 2, "secure_boot": "On",
                                    "template": "MicrosoftWindows", "tpm": False})
        self.assertEqual(out["verdict"], "FAIL")
        self.assertFalse(next(c for c in out["checks"] if c["check"] == "tpm_enabled")["ok"])

    def test_verify_passes_full_profile_and_fails_wrong_template(self):
        good = {"name": "V", "generation": 2, "secure_boot": "On", "template": "MicrosoftWindows", "tpm": True}
        self.assertEqual(vmctl.verify_profile(good)["verdict"], "PASS")
        self.assertEqual(vmctl.verify_profile(good, linux=True)["verdict"], "FAIL")

    def test_owner_commands_hold_no_removal(self):
        # Owner 2026-10-02: removal is teardown.py's soft delete only (test_teardown.py holds the
        # file scan); vmctl's owner commands stay restore, turn off and reset.
        self.assertEqual(set(vmctl.DESTRUCTIVE), {"restore", "turnoff", "reset"})
        for cmd in vmctl.DESTRUCTIVE.values():
            self.assertNotRegex(cmd, r"(?i)^remove-")

    def test_cleanroom_restore_is_guid_locked(self):
        # Owner Q27: automatic restore only for the skill's own test VM, checked by GUID, to its own
        # golden checkpoint by id; a name or tag alone is never enough.
        import cleanroom
        s = cleanroom.host_script("V", "golden", "C:\\g.xml", "o/r", "p@m",
                                  vm_id="11111111-2222-3333-4444-555555555555",
                                  golden_id="66666666-7777-8888-9999-000000000000")
        self.assertIn("11111111-2222-3333-4444-555555555555", s)
        self.assertIn("66666666-7777-8888-9999-000000000000", s)
        self.assertIn("Restore-VMSnapshot -VMSnapshot $snap", s)
        self.assertNotIn("Restore-VMSnapshot -VMName", s)

    def test_own_vm_register_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(hc, "own_dir", return_value=Path(d)):
                self.assertFalse(hc.is_own_vm("abc"))
                hc.record_own_vm("abc", "V", True)
                self.assertTrue(hc.is_own_vm("abc"))
                self.assertFalse(hc.is_own_vm("ABD"))

    def test_destructive_ops_are_owner_commands_only(self):
        c = vmctl.owner_command("restore", "V", "pre-update")
        self.assertEqual(c["run_by"], "owner")
        self.assertIn("Restore-VMSnapshot -VMName 'V' -Name 'pre-update'", c["command"])
        with self.assertRaises(ValueError):
            vmctl.owner_command("restore", "V")

    def test_create_refuses_an_edited_plan(self):
        params = {"name": "V", "memory_gb": 4, "disk_gb": 64, "cpus": 2, "iso": None, "vhdx": None,
                  "linux": False, "switch": None, "cleanroom": False}
        steps = vmctl.build_create_steps("V", 4, 64)
        steps[-1] = "Remove-VM -Name 'Other' -Force"
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "plan.json"
            f.write_text(json.dumps({"params": params, "steps": steps, "ram": {"verdict": "go"}}))
            self.assertEqual(vmctl.main(["create", "--plan", str(f)]), 2)


class CleanroomTests(unittest.TestCase):
    def test_inputs(self):
        cleanroom.check_inputs("some-owner/some-repo#v1.0.0", "my-plugin@some-market", "golden")
        cleanroom.check_inputs("https://example.com/org/repo.git", "p@m", "golden-2026.10")
        for src, plug, gold in (("a/b; rm", "p@m", "g"), ("a/b", "P@M", "g"), ("a/b", "p@m", "gold en")):
            with self.assertRaises(ValueError):
                cleanroom.check_inputs(src, plug, gold)

    def test_tag_match_is_exact(self):
        self.assertTrue(cleanroom.tag_matches("hypervrunner:cleanroom golden=golden", "golden"))
        self.assertFalse(cleanroom.tag_matches("hypervrunner:cleanroom golden=golden", "gold"))
        self.assertFalse(cleanroom.tag_matches("golden=golden", "golden"))

    def test_host_script_reverts_in_finally_and_has_no_double_quote(self):
        s = cleanroom.host_script("CR1", "golden", "C:\\state\\guest.xml", "o/r", "p@m", vm_id=VID, golden_id=GID)
        self.assertNotIn('"', s)
        self.assertIn("finally { Restore-VMSnapshot -VMSnapshot $snap -Confirm:$false }", s)
        self.assertNotIn("'-y'", s)
        self.assertIn("'-y'", cleanroom.host_script("CR1", "golden", "C:\\g.xml", "o/r", "p@m", True, VID, GID))

    def test_receipt_pass_and_fail(self):
        plan = {"plugin": "p@m", "source": "o/r", "vm": "CR1", "golden": "golden"}
        listed = json.dumps([{"id": "p@m", "version": "1.0.0"}])
        ok = {"steps": [{"step": "version", "exit": 0, "output": "2.1.300 (Claude Code)"},
                        {"step": "marketplace-add", "exit": 0, "output": ""},
                        {"step": "install", "exit": 0, "output": "{}"},
                        {"step": "list", "exit": 0, "output": listed}]}
        self.assertEqual(cleanroom.build_receipt(plan, ok)["verdict"], "PASS")
        bad = json.loads(json.dumps(ok))
        bad["steps"][2]["exit"] = 1
        bad["steps"][3]["output"] = "[]"
        r = cleanroom.build_receipt(plan, bad)
        self.assertEqual(r["verdict"], "FAIL")
        self.assertIn("step install exit 1", r["problems"])
        self.assertIn("p@m not in claude plugin list", r["problems"])
        self.assertEqual(cleanroom.build_receipt(plan, {"error": "heartbeat timeout"})["verdict"], "FAIL")


class SandboxTests(unittest.TestCase):
    def test_config_is_locked_down(self):
        with tempfile.TemporaryDirectory() as d:
            i, o = Path(d) / "in", Path(d) / "out"
            i.mkdir(); o.mkdir()
            xml = sandbox_config.build_config(i, o)
            self.assertEqual(sandbox_config.validate(xml), [])
            self.assertIn("<Networking>Disable</Networking>", xml)
            self.assertEqual(xml.count("<ReadOnly>false</ReadOnly>"), 1)
            self.assertEqual(xml.count("<ReadOnly>true</ReadOnly>"), 1)
            self.assertNotIn("<LogonCommand>", xml)

    def test_validate_catches_unsafe_configs(self):
        bad = ("<Configuration><Networking>Default</Networking><MappedFolders>"
               "<MappedFolder><HostFolder>C:\\a</HostFolder><ReadOnly>false</ReadOnly></MappedFolder>"
               "<MappedFolder><HostFolder>C:\\b</HostFolder></MappedFolder></MappedFolders>"
               "<LogonCommand><Command>x.exe</Command></LogonCommand></Configuration>")
        problems = " ".join(sandbox_config.validate(bad))
        self.assertIn("Networking is not Disable", problems)
        self.assertIn("2 writable mapped folders", problems)
        self.assertIn("LogonCommand", problems)

    def test_output_folder_rules(self):
        with tempfile.TemporaryDirectory() as d:
            i, o = Path(d) / "in", Path(d) / "out"
            i.mkdir(); o.mkdir()
            (o / "x.txt").write_text("x")
            with self.assertRaises(ValueError):
                sandbox_config.check_folders(str(i), str(o))
            nested = i / "out2"
            nested.mkdir()
            with self.assertRaises(ValueError):
                sandbox_config.check_folders(str(i), str(nested))


if __name__ == "__main__":
    unittest.main()
