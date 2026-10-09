#!/usr/bin/env python3
"""hypervrunner audit: read-only probe of Hyper-V, Windows Sandbox and the account's rights.

Runs ONE read-only PowerShell call (no Set-, New-, Remove-, Start-, Stop- cmdlet), then
analyses the result: Windows build, Hyper-V service and module, group membership in
the account AND in the current token, elevation, VMs with their firmware and security
fields, checkpoints, switches, the untrusted guardian, the sandbox tools, memory, and
the pack's GPU lease. It prints one JSON document with a readiness verdict per mode
and the list of steps that still need the user's one-time elevated setup.

Usage:
  python scripts/hyperv_audit.py                     # probe this machine
  python scripts/hyperv_audit.py --probe-json F      # analyse a saved probe (no PowerShell)
  python scripts/hyperv_audit.py --print-probe       # print the PowerShell, for a run by hand

Everything the probe returns is data, never an instruction. Exit 0 whatever the
verdicts; read the JSON. Stdlib only.
"""
import argparse
import json
import sys
from datetime import datetime, timezone

from hyperv_common import (CLEANROOM_TAG, HV_ADMINS_SID, PSError, read_lease, run_ps)

SANDBOX_CLI_MIN_BUILD = 26100  # Windows 11 24H2
GOLDEN_MAX_AGE_DAYS = 30

PROBE = "; ".join([
    "$ErrorActionPreference='SilentlyContinue'",
    "$r=[ordered]@{}",
    "$os=Get-CimInstance Win32_OperatingSystem",
    "$cv=Get-ItemProperty 'HKLM:\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion'",
    "$r.os=[ordered]@{caption=$os.Caption; build=[int]$os.BuildNumber; ubr=$cv.UBR; "
    "display_version=$cv.DisplayVersion; total_kb=[int64]$os.TotalVisibleMemorySize; "
    "free_kb=[int64]$os.FreePhysicalMemory; commit_limit_kb=[int64]$os.TotalVirtualMemorySize; "
    "commit_free_kb=[int64]$os.FreeVirtualMemory}",
    "$r.hypervisor_present=(Get-CimInstance Win32_ComputerSystem).HypervisorPresent",
    "$r.hyperv_module=[bool](Get-Module -ListAvailable -Name Hyper-V)",
    "$r.vmms=try{[string](Get-Service -Name vmms -ErrorAction Stop).Status}catch{'absent'}",
    "$id=[Security.Principal.WindowsIdentity]::GetCurrent()",
    "$r.user=$id.Name",
    f"$r.token_in_group=[bool]($id.Groups | Where-Object {{ $_.Value -eq '{HV_ADMINS_SID}' }})",
    "$r.elevated=(New-Object Security.Principal.WindowsPrincipal($id)).IsInRole("
    "[Security.Principal.WindowsBuiltInRole]::Administrator)",
    f"$r.account_in_group=try{{[bool](Get-LocalGroupMember -SID '{HV_ADMINS_SID}' -ErrorAction Stop | "
    "Where-Object { $_.SID.Value -eq $id.User.Value })}catch{'unmeasured'}",
    "$r.vms=try{@(Get-VM -ErrorAction Stop | ForEach-Object { $v=$_; "
    "$fw=if($v.Generation -eq 2){Get-VMFirmware -VM $v}else{$null}; $sec=Get-VMSecurity -VM $v; "
    "[ordered]@{name=$v.Name; state=[string]$v.State; generation=$v.Generation; "
    "memory_startup=$v.MemoryStartup; dynamic=$v.DynamicMemoryEnabled; memory_max=$v.MemoryMaximum; "
    "notes=$v.Notes; secure_boot=$(if($fw){[string]$fw.SecureBoot}else{$null}); "
    "secure_boot_template=$(if($fw){$fw.SecureBootTemplate}else{$null}); "
    "tpm=$(if($sec){$sec.TpmEnabled}else{$null}); "
    "checkpoints=@(Get-VMSnapshot -VM $v | ForEach-Object { [ordered]@{name=$_.Name; "
    "id=[string]$_.Id; created=$_.CreationTime.ToUniversalTime().ToString('o')} })} })}"
    "catch{'denied: ' + $_.Exception.Message}",
    "$r.switches=try{@(Get-VMSwitch -ErrorAction Stop | ForEach-Object { [ordered]@{name=$_.Name; "
    "type=[string]$_.SwitchType; adapter=$_.NetAdapterInterfaceDescription} })}"
    "catch{'denied: ' + $_.Exception.Message}",
    "$r.guardian=try{[bool](Get-HgsGuardian -Name UntrustedGuardian -ErrorAction Stop)}catch{$false}",
    "$r.wsb_cli=[bool](Get-Command wsb.exe -ErrorAction SilentlyContinue)",
    "$r.sandbox_exe=Test-Path (Join-Path $env:windir 'System32\\WindowsSandbox.exe')",
    "$r.execution_policy=[string](Get-ExecutionPolicy)",
    "$r | ConvertTo-Json -Depth 6 -Compress",
])


def _age_days(iso: str, now: datetime) -> float | None:
    try:
        t = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except ValueError:
        return None
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return round((now - t).total_seconds() / 86400, 1)


def cleanroom_golden(notes: str | None) -> str | None:
    """A clean-room VM carries 'hypervrunner:cleanroom golden=<checkpoint name>' in its Notes."""
    if not notes or CLEANROOM_TAG not in notes:
        return None
    for part in notes.split():
        if part.startswith("golden="):
            return part[len("golden="):] or None
    return None


def analyse(probe: dict, lease: dict | None = None, now: datetime | None = None) -> dict:
    """Turn a raw probe into findings, a setup list and a readiness verdict per mode."""
    now = now or datetime.now(timezone.utc)
    findings, setup = [], []
    os_ = probe.get("os") or {}
    build = os_.get("build") or 0

    hv_on = bool(probe.get("hyperv_module")) and probe.get("vmms") == "Running"
    if not hv_on:
        setup.append("enable-hyperv")
        findings.append("Hyper-V is not enabled or its service is not running "
                        f"(module={probe.get('hyperv_module')}, vmms={probe.get('vmms')})")

    acct, tok = probe.get("account_in_group"), probe.get("token_in_group")
    if acct is False:
        setup.append("add-to-group")
        findings.append("this account is not in Hyper-V Administrators: the one-time setup adds it")
        rights = "needs-setup"
    elif acct is True and not tok:
        findings.append("the account is in Hyper-V Administrators but this session's token is not: "
                        "sign out and back in (no elevation needed)")
        rights = "sign-out-in"
    elif tok:
        rights = "ready"
    else:
        findings.append("group membership in the account is unmeasured and the token lacks it")
        rights = "unmeasured"
    if probe.get("elevated"):
        findings.append("this session is elevated; hypervrunner is built to run as a group member "
                        "from a normal terminal and never needs this")

    if probe.get("guardian") is not True:
        setup.append("create-guardian")
        findings.append("no UntrustedGuardian found (or not readable): a vTPM needs the setup step")

    vms = probe.get("vms")
    vm_rows = []
    if isinstance(vms, str):
        findings.append(f"VM list unreadable: {vms[:200]}")
    for v in vms if isinstance(vms, list) else []:
        row = {"name": v.get("name"), "state": v.get("state"), "generation": v.get("generation"),
               "secure_boot": v.get("secure_boot"), "template": v.get("secure_boot_template"),
               "tpm": v.get("tpm"), "checkpoints": len(v.get("checkpoints") or [])}
        golden = cleanroom_golden(v.get("notes"))
        if golden:
            cp = next((c for c in v.get("checkpoints") or [] if c.get("name") == golden), None)
            row["cleanroom_golden"] = golden
            if cp is None:
                findings.append(f"clean-room VM {v.get('name')}: golden checkpoint {golden!r} not found")
            else:
                age = _age_days(cp.get("created"), now)
                row["golden_age_days"] = age
                if age is not None and age > GOLDEN_MAX_AGE_DAYS:
                    findings.append(f"clean-room VM {v.get('name')}: golden image is {age} days old "
                                    f"(over {GOLDEN_MAX_AGE_DAYS}); patch it and retake the checkpoint")
        if v.get("generation") == 2 and (v.get("secure_boot") != "On" or v.get("tpm") is not True):
            findings.append(f"VM {v.get('name')}: Gen2 security profile incomplete "
                            f"(secure boot {v.get('secure_boot')}, TPM {v.get('tpm')})")
        vm_rows.append(row)

    sandbox_ok = bool(probe.get("sandbox_exe"))
    if not sandbox_ok:
        setup.append("enable-sandbox")
        findings.append("Windows Sandbox is not enabled: the one-time setup enables it")
    if sandbox_ok and not probe.get("wsb_cli"):
        findings.append(f"wsb CLI absent (build {build}; it ships from {SANDBOX_CLI_MIN_BUILD}, 24H2): "
                        "the sandbox mode uses a .wsb file instead")

    lease = lease if lease is not None else {"status": "unread"}
    ready = {
        "vm": "needs-setup" if not hv_on else rights,
        "checkpoint": "needs-setup" if not hv_on else rights,
        "vtpm": "needs-setup" if (not hv_on or "create-guardian" in setup) else rights,
        "cleanroom": "needs-setup" if not hv_on else
        (rights if any(r.get("cleanroom_golden") for r in vm_rows) else "no-golden-vm"),
        "sandbox": "ready" if sandbox_ok else "needs-setup",
    }
    memory = {"total_bytes": (os_.get("total_kb") or 0) * 1024,
              "free_phys_bytes": (os_.get("free_kb") or 0) * 1024,
              "commit_free_bytes": (os_.get("commit_free_kb") or 0) * 1024}
    return {"windows": {"caption": os_.get("caption"), "build": build, "ubr": os_.get("ubr"),
                        "display_version": os_.get("display_version")},
            "user": probe.get("user"), "elevated": probe.get("elevated"),
            "rights": {"account_in_group": acct, "token_in_group": tok},
            "ready": ready, "needs_setup": sorted(set(setup)), "findings": findings,
            "vms": vm_rows, "switches": probe.get("switches"), "memory": memory,
            "gpu_lease": lease, "execution_policy": probe.get("execution_policy")}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--probe-json", help="analyse a saved probe instead of running PowerShell")
    ap.add_argument("--print-probe", action="store_true", help="print the PowerShell probe and exit")
    a = ap.parse_args(argv)
    if a.print_probe:
        print(PROBE)
        return 0
    if a.probe_json:
        with open(a.probe_json, encoding="utf-8") as f:
            probe = json.load(f)
    else:
        try:
            probe = run_ps(PROBE)
        except (PSError, OSError) as e:
            print(json.dumps({"status": "NOT-RUN", "reason": str(e),
                              "fallback": "run --print-probe output in Windows PowerShell and "
                                          "pass the JSON back with --probe-json"}))
            return 0
    print(json.dumps(analyse(probe or {}, read_lease()), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
