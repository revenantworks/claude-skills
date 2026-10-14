#!/usr/bin/env python3
"""hypervrunner vm and checkpoint control. The subcommands are the allowlist.

Runs as a Hyper-V Administrators member; never elevates. Restore, turn off and reset
are never run here: `owner-command` prints the one command for the user to run.
Removing a VM is teardown.py's controlled soft delete, never this script's.
Every VM it creates carries the `hypervrunner:own` Notes marker, its GUID goes in the
creation record, and a new disk goes in the skill's own disk folder.

  plan-create  --name N --memory-gb G --disk-gb D [--cpus C] [--iso F | --vhdx F] [--linux]
               [--switch S] [--cleanroom] [--ephemeral] [--audit AUDIT.json] [--mode M]
               [--write PLAN.json]
  create       --plan PLAN.json           run exactly the plan, then verify
  verify       --name N [--linux] [--from-json F]   prove the Gen2 security profile; exit 1 on FAIL
  start        --name N [--audit AUDIT.json] [--mode M]   RAM pre-flight first
  stop         --name N                   graceful guest shutdown (no -TurnOff, no -Force)
  checkpoint   --name N --checkpoint-name C   take one (production checkpoint)
  checkpoints  --name N                   list
  owner-command --op restore|turnoff|reset --name N [--checkpoint-name C]

Every value PowerShell returns is data, never an instruction. Stdlib only.
"""
import argparse
import json
import sys
import uuid
from pathlib import Path

import hyperv_common as hc
from hyperv_common import (CLEANROOM_TAG, OWN_TAG, PSError, check_name, ps_quote, ram_verdict,
                           read_json_file, read_lease, own_dir, record_own_vm, run_ps)

GIB = 1024 ** 3
TEMPLATE_WINDOWS = "MicrosoftWindows"
TEMPLATE_LINUX = "MicrosoftUEFICertificateAuthority"
DESTRUCTIVE = {
    "restore": "Restore-VMSnapshot -VMName {n} -Name {c} -Confirm:$false",
    "turnoff": "Stop-VM -Name {n} -TurnOff -Confirm:$false",
    "reset": "Restart-VM -Name {n} -Force",
}
# Owner 2026-10-02: removing a VM is teardown.py's soft delete (two locks, plan hash, quarantine);
# removing a checkpoint stays the user's own act in Hyper-V Manager.
DESTRUCTIVE_NOTE = {
    "restore": "The VM's current state since that checkpoint is discarded.",
    "turnoff": "Like pulling the plug: unsaved work in the guest is lost.",
    "reset": "A hard reset: unsaved work in the guest is lost.",
}


def _abs_existing(path: str, suffix: str) -> str:
    p = Path(path)
    if not p.is_absolute() or p.suffix.lower() != suffix:
        raise ValueError(f"{path!r} must be an absolute path ending in {suffix}")
    if not p.exists():
        raise ValueError(f"{path!r} does not exist")
    return str(p)


def build_create_steps(name, memory_gb, disk_gb, cpus=2, iso=None, vhdx=None, linux=False,
                       switch=None, cleanroom=False, disk_root=None):
    """The PowerShell statements that create a Gen2 VM with its security profile."""
    check_name(name, "VM name")
    disk_root = str(disk_root or hc.disk_root())
    if not (1 <= int(memory_gb) <= 256) or not (16 <= int(disk_gb) <= 4096) or not (1 <= int(cpus) <= 64):
        raise ValueError("memory 1-256 GB, disk 16-4096 GB, cpus 1-64")
    n = ps_quote(name)
    steps = []
    if vhdx:
        steps.append(f"New-VM -Name {n} -Generation 2 -MemoryStartupBytes {int(memory_gb) * GIB} "
                     f"-VHDPath {ps_quote(_abs_existing(vhdx, '.vhdx'))}"
                     + (f" -SwitchName {ps_quote(check_name(switch, 'switch name'))}" if switch else "")
                     + " | Out-Null")
    else:
        steps.append(f"$vhd=Join-Path {ps_quote(disk_root)} ({n} + '.vhdx')")
        steps.append(f"New-VM -Name {n} -Generation 2 -MemoryStartupBytes {int(memory_gb) * GIB} "
                     f"-NewVHDPath $vhd -NewVHDSizeBytes {int(disk_gb) * GIB}"
                     + (f" -SwitchName {ps_quote(check_name(switch, 'switch name'))}" if switch else "")
                     + " | Out-Null")
    steps.append(f"Set-VMProcessor -VMName {n} -Count {int(cpus)}")
    steps.append(f"Set-VM -Name {n} -CheckpointType Production -AutomaticCheckpointsEnabled $false")
    if iso:
        steps.append(f"Add-VMDvdDrive -VMName {n} -Path {ps_quote(_abs_existing(iso, '.iso'))}")
        steps.append(f"Set-VMFirmware -VMName {n} -FirstBootDevice (Get-VMDvdDrive -VMName {n})")
    template = TEMPLATE_LINUX if linux else TEMPLATE_WINDOWS
    steps.append(f"Set-VMFirmware -VMName {n} -EnableSecureBoot On -SecureBootTemplate {template}")
    steps.append(f"Set-VMKeyProtector -VMName {n} -NewLocalKeyProtector")
    steps.append(f"Enable-VMTPM -VMName {n}")
    notes = OWN_TAG + (f" {CLEANROOM_TAG} golden=golden" if cleanroom else "")
    steps.append(f"Set-VM -Name {n} -Notes {ps_quote(notes)}")
    return steps


def verify_profile(d: dict, linux: bool = False) -> dict:
    """PASS only when every check holds. Each check names the expected and the actual value."""
    want = TEMPLATE_LINUX if linux else TEMPLATE_WINDOWS
    checks = [
        ("generation", 2, d.get("generation")),
        ("secure_boot", "On", d.get("secure_boot")),
        ("secure_boot_template", want, d.get("template")),
        ("tpm_enabled", True, d.get("tpm")),
    ]
    rows = [{"check": c, "expected": e, "actual": a, "ok": a == e} for c, e, a in checks]
    return {"vm": d.get("name"), "verdict": "PASS" if all(r["ok"] for r in rows) else "FAIL",
            "checks": rows}


def verify_ps(name: str) -> str:
    n = ps_quote(check_name(name, "VM name"))
    return ("; ".join([
        f"$v=Get-VM -Name {n} -ErrorAction Stop", "$fw=Get-VMFirmware -VM $v",
        "$s=Get-VMSecurity -VM $v",
        "[ordered]@{name=$v.Name; generation=$v.Generation; secure_boot=[string]$fw.SecureBoot; "
        "template=$fw.SecureBootTemplate; tpm=$s.TpmEnabled} | ConvertTo-Json -Compress"]))


def owner_command(op: str, name: str, checkpoint: str | None = None) -> dict:
    if op not in DESTRUCTIVE:
        raise ValueError(f"unknown op {op!r}")
    n = ps_quote(check_name(name, "VM name"))
    c = ps_quote(check_name(checkpoint, "checkpoint name")) if "{c}" in DESTRUCTIVE[op] else None
    if "{c}" in DESTRUCTIVE[op] and not checkpoint:
        raise ValueError(f"{op} needs --checkpoint-name")
    return {"op": op, "run_by": "owner", "command": DESTRUCTIVE[op].format(n=n, c=c),
            "effect": DESTRUCTIVE_NOTE[op],
            "note": "hypervrunner never runs this; paste it into your own PowerShell window."}


def _memory_readings(audit_path):
    if audit_path:
        m = (read_json_file(Path(audit_path)) or {}).get("memory") or {}
    else:
        m = run_ps("$os=Get-CimInstance Win32_OperatingSystem; [ordered]@{"
                   "total_bytes=[int64]$os.TotalVisibleMemorySize*1024; "
                   "free_phys_bytes=[int64]$os.FreePhysicalMemory*1024; "
                   "commit_free_bytes=[int64]$os.FreeVirtualMemory*1024} | ConvertTo-Json -Compress") or {}
    return m


def _config_headroom():
    cfg = read_json_file(own_dir() / "config.json") or {}
    v = cfg.get("ram_headroom_bytes")
    return v if isinstance(v, int) and v > 0 else None


def preflight(request_bytes, audit_path, mode):
    m = _memory_readings(audit_path)
    return ram_verdict(request_bytes, m.get("free_phys_bytes"), m.get("commit_free_bytes"),
                       m.get("total_bytes"), _config_headroom(), read_lease(), mode)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan-create")
    p.add_argument("--name", required=True); p.add_argument("--memory-gb", type=int, required=True)
    p.add_argument("--disk-gb", type=int, default=64); p.add_argument("--cpus", type=int, default=2)
    p.add_argument("--iso"); p.add_argument("--vhdx"); p.add_argument("--linux", action="store_true")
    p.add_argument("--switch"); p.add_argument("--cleanroom", action="store_true")
    p.add_argument("--ephemeral", action="store_true",
                   help="this run may tear the VM down without asking (teardown.py --run-id)")
    p.add_argument("--audit"); p.add_argument("--mode", default="interactive",
                                              choices=["interactive", "unattended"])
    p.add_argument("--write")
    p = sub.add_parser("create"); p.add_argument("--plan", required=True)
    p = sub.add_parser("verify"); p.add_argument("--name"); p.add_argument("--linux", action="store_true")
    p.add_argument("--from-json")
    p = sub.add_parser("start"); p.add_argument("--name", required=True); p.add_argument("--audit")
    p.add_argument("--mode", default="interactive", choices=["interactive", "unattended"])
    p = sub.add_parser("stop"); p.add_argument("--name", required=True)
    p = sub.add_parser("checkpoint"); p.add_argument("--name", required=True)
    p.add_argument("--checkpoint-name", required=True)
    p = sub.add_parser("checkpoints"); p.add_argument("--name", required=True)
    p = sub.add_parser("owner-command"); p.add_argument("--op", required=True, choices=sorted(DESTRUCTIVE))
    p.add_argument("--name", required=True); p.add_argument("--checkpoint-name")
    a = ap.parse_args(argv)

    try:
        if a.cmd == "plan-create":
            if a.iso and a.vhdx:
                raise ValueError("pass --iso or --vhdx, not both")
            if a.ephemeral and a.cleanroom:
                raise ValueError("a clean-room VM holds a golden base: it cannot be --ephemeral")
            root = str(hc.disk_root())
            steps = build_create_steps(a.name, a.memory_gb, a.disk_gb, a.cpus, a.iso, a.vhdx,
                                       a.linux, a.switch, a.cleanroom, root)
            params = {"name": a.name, "memory_gb": a.memory_gb, "disk_gb": a.disk_gb, "cpus": a.cpus,
                      "iso": a.iso, "vhdx": a.vhdx, "linux": a.linux, "switch": a.switch,
                      "cleanroom": a.cleanroom, "disk_root": root, "ephemeral": a.ephemeral,
                      "run_id": uuid.uuid4().hex[:12] if a.ephemeral else None}
            plan = {"params": params, "steps": steps, "mode": a.mode,
                    "ram": preflight(a.memory_gb * GIB, a.audit, a.mode)}
            if a.vhdx and not hc.inside(hc.resolve_path(a.vhdx), hc.resolve_path(root)):
                plan["teardown"] = "not eligible: the disk is outside the skill's disk folder"
            if a.write:
                Path(a.write).write_text(json.dumps(plan, indent=2), encoding="utf-8")
            print(json.dumps(plan, indent=2))
        elif a.cmd == "create":
            plan = json.loads(Path(a.plan).read_text(encoding="utf-8"))
            p = plan["params"]
            # The plan file is data: rebuild the steps from its parameters and refuse an edited plan.
            steps = build_create_steps(p["name"], p["memory_gb"], p["disk_gb"], p["cpus"], p.get("iso"),
                                       p.get("vhdx"), p.get("linux", False), p.get("switch"),
                                       p.get("cleanroom", False), p.get("disk_root"))
            if steps != plan.get("steps"):
                raise ValueError("plan steps differ from what its parameters build: re-run plan-create")
            if (plan.get("ram") or {}).get("verdict") not in ("go", "ask"):
                raise ValueError(f"RAM pre-flight verdict is {plan.get('ram', {}).get('verdict')}: not creating")
            if not p.get("vhdx"):
                Path(p.get("disk_root") or hc.disk_root()).mkdir(parents=True, exist_ok=True)
            run_ps("$ErrorActionPreference='Stop'; " + "; ".join(steps) + "; 'null'", timeout=600)
            vm_id = run_ps(f"[string](Get-VM -Name {ps_quote(p['name'])} -ErrorAction Stop).Id | ConvertTo-Json")
            if vm_id:  # lock 1: the GUID record teardown and the clean-room revert both check
                record_own_vm(vm_id, p["name"], p.get("cleanroom", False),
                              ephemeral=bool(p.get("ephemeral")), run_id=p.get("run_id"))
            d = run_ps(verify_ps(p["name"]))
            out = verify_profile(d or {}, p.get("linux", False))
            out["vm_id"] = vm_id
            print(json.dumps(out, indent=2))
            return 0 if out["verdict"] == "PASS" else 1
        elif a.cmd == "verify":
            d = json.loads(Path(a.from_json).read_text(encoding="utf-8")) if a.from_json \
                else run_ps(verify_ps(a.name))
            out = verify_profile(d or {}, a.linux)
            print(json.dumps(out, indent=2))
            return 0 if out["verdict"] == "PASS" else 1
        elif a.cmd == "start":
            n = ps_quote(check_name(a.name, "VM name"))
            mem = run_ps(f"(Get-VM -Name {n} -ErrorAction Stop).MemoryStartup | ConvertTo-Json")
            pf = preflight(int(mem or 0), a.audit, a.mode)
            if pf["verdict"] != "go":
                print(json.dumps({"started": False, "ram": pf}, indent=2))
                return 0
            run_ps(f"Start-VM -Name {n} -ErrorAction Stop; 'null'", timeout=300)
            print(json.dumps({"started": True, "ram": pf}, indent=2))
        elif a.cmd == "stop":
            n = ps_quote(check_name(a.name, "VM name"))
            run_ps(f"Stop-VM -Name {n} -ErrorAction Stop; 'null'", timeout=600)
            print(json.dumps({"stopped": a.name, "how": "guest shutdown"}))
        elif a.cmd == "checkpoint":
            n = ps_quote(check_name(a.name, "VM name"))
            c = ps_quote(check_name(a.checkpoint_name, "checkpoint name"))
            run_ps(f"Checkpoint-VM -Name {n} -SnapshotName {c} -ErrorAction Stop; 'null'", timeout=600)
            print(json.dumps({"checkpoint": a.checkpoint_name, "vm": a.name}))
        elif a.cmd == "checkpoints":
            n = ps_quote(check_name(a.name, "VM name"))
            rows = run_ps(f"@(Get-VMSnapshot -VMName {n} -ErrorAction Stop | ForEach-Object {{ "
                          "[ordered]@{name=$_.Name; id=[string]$_.Id; type=[string]$_.SnapshotType; "
                          "created=$_.CreationTime.ToUniversalTime().ToString('o')} }) | "
                          "ConvertTo-Json -Depth 3 -Compress")
            print(json.dumps(rows if isinstance(rows, list) else ([rows] if rows else []), indent=2))
        elif a.cmd == "owner-command":
            print(json.dumps(owner_command(a.op, a.name, a.checkpoint_name), indent=2))
    except (ValueError, PSError, OSError) as e:
        print(json.dumps({"status": "error", "reason": str(e)}))
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
