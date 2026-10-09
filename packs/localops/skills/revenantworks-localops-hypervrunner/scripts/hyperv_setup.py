#!/usr/bin/env python3
"""hypervrunner setup: write the ONE elevated script the user runs, and the one command.

It never runs the script and never elevates. From a saved audit (hyperv_audit.py output)
it writes only the steps still needed: enable Hyper-V, enable Windows Sandbox, add the
audited account to Hyper-V Administrators, create the untrusted guardian for vTPMs, and
an optional Internal or External switch. The script refuses to run unelevated, stops on
the first error, and ends by saying whether a restart or a sign-out is needed.

Usage:
  python scripts/hyperv_setup.py --audit AUDIT.json [--internal-switch NAME]
         [--external-switch NAME --adapter "ADAPTER NAME"] [--out PATH]

Prints JSON: the script path, its SHA-256, the steps, and the command for the user to
run in a terminal they opened with Run as administrator. Stdlib only.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

from hyperv_common import HV_ADMINS_SID, check_name, own_dir, ps_quote

HEADER = [
    "# hypervrunner one-time setup. Written for the user to read, then run elevated once.",
    "# It never downloads anything and never changes execution policy beyond this process.",
    "$ErrorActionPreference = 'Stop'",
    "$p = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())",
    "if (-not $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {",
    "  Write-Error 'Run this from a terminal opened with Run as administrator.'; exit 1 }",
    "$restart = $false; $signout = $false",
]


def build_script(audit: dict, internal_switch=None, external_switch=None, adapter=None):
    """Return (script_text, steps). Only the steps the audit says are missing."""
    need = set(audit.get("needs_setup") or [])
    steps, body = [], []
    if "enable-hyperv" in need:
        steps.append("enable-hyperv")
        body += ["Write-Host 'Enabling Hyper-V...'",
                 "$f = Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All -NoRestart",
                 "if ($f.RestartNeeded) { $restart = $true }"]
    if "enable-sandbox" in need:
        steps.append("enable-sandbox")
        body += ["Write-Host 'Enabling Windows Sandbox...'",
                 "$f = Enable-WindowsOptionalFeature -Online -FeatureName Containers-DisposableClientVM -All -NoRestart",
                 "if ($f.RestartNeeded) { $restart = $true }"]
    if "add-to-group" in need:
        user = audit.get("user")
        if not user:
            raise ValueError("the audit names no user to add to Hyper-V Administrators")
        steps.append("add-to-group")
        body += ["Write-Host " + ps_quote(f"Adding {user} to Hyper-V Administrators..."),
                 f"Add-LocalGroupMember -SID '{HV_ADMINS_SID}' -Member {ps_quote(user)}",
                 "$signout = $true"]
    if "create-guardian" in need:
        steps.append("create-guardian")
        body += ["Write-Host 'Creating the local untrusted guardian for virtual TPMs...'",
                 "if (-not (Get-HgsGuardian -Name UntrustedGuardian -ErrorAction SilentlyContinue)) {",
                 "  New-HgsGuardian -Name UntrustedGuardian -GenerateCertificates | Out-Null }"]
    if internal_switch:
        check_name(internal_switch, "switch name")
        steps.append(f"internal-switch:{internal_switch}")
        body += [f"if (-not (Get-VMSwitch -Name {ps_quote(internal_switch)} -ErrorAction SilentlyContinue)) {{",
                 f"  New-VMSwitch -Name {ps_quote(internal_switch)} -SwitchType Internal | Out-Null }}"]
    if external_switch:
        check_name(external_switch, "switch name")
        if not adapter:
            raise ValueError("an External switch needs --adapter (the physical adapter's name)")
        steps.append(f"external-switch:{external_switch}")
        body += ["Write-Host 'Creating an External switch: the network drops for a few seconds.'",
                 f"if (-not (Get-VMSwitch -Name {ps_quote(external_switch)} -ErrorAction SilentlyContinue)) {{",
                 f"  New-VMSwitch -Name {ps_quote(external_switch)} -NetAdapterName {ps_quote(adapter)} "
                 "-AllowManagementOS $true | Out-Null }"]
    footer = ["Write-Host 'Setup finished.'",
              "if ($restart) { Write-Host 'Restart Windows to finish enabling the features.' }",
              "if ($signout) { Write-Host 'Sign out and back in so the group membership reaches your session.' }"]
    if not steps:
        return None, []
    return "\r\n".join(HEADER + body + footer) + "\r\n", steps


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--audit", required=True, help="hyperv_audit.py output, saved as JSON")
    ap.add_argument("--internal-switch")
    ap.add_argument("--external-switch")
    ap.add_argument("--adapter")
    ap.add_argument("--out", help="where to write the .ps1 (default: the per-user state folder)")
    a = ap.parse_args(argv)
    audit = json.loads(Path(a.audit).read_text(encoding="utf-8"))
    script, steps = build_script(audit, a.internal_switch, a.external_switch, a.adapter)
    if not script:
        print(json.dumps({"status": "nothing-to-do", "steps": []}))
        return 0
    out = Path(a.out) if a.out else own_dir() / "setup" / "hypervrunner-setup.ps1"
    out.parent.mkdir(parents=True, exist_ok=True)
    data = script.encode("utf-8-sig")  # BOM: Windows PowerShell 5.1 reads non-ASCII correctly
    out.write_bytes(data)
    print(json.dumps({"status": "written", "path": str(out), "steps": steps,
                      "sha256": hashlib.sha256(data).hexdigest(),
                      "verify": f"Get-FileHash -Algorithm SHA256 {ps_quote(out)}",
                      "owner_command": "powershell.exe -NoProfile -ExecutionPolicy RemoteSigned "
                                       f"-File {ps_quote(out)}",
                      "owner_note": "Read the script first. Run the command in a Windows PowerShell "
                                    "window you opened with Run as administrator. hypervrunner "
                                    "never runs it."}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
