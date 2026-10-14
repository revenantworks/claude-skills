# Admin split: what a group member can do, and what needs the one setup

> **Last verified: 2026-10-01** (calendar surface, 90 days, declared in `volatile.json`).
> Sources and their dates are in `SOURCES.md`. `hypervrunner refresh` re-reads them and runs one
> live audit; a row moves from "unverified" only on a primary source or a live test.

**Read this file when:** running `audit` or `setup`, or when Hyper-V says access denied.

## The rule

Day-to-day VM work needs membership of **Hyper-V Administrators** (SID `S-1-5-32-578`, the same
in every Windows language), not a full administrator token. Host changes need elevation, and
they all go into one script the user runs once. hypervrunner never elevates itself.

## The table

| Operation | Needs | Evidence | Status |
|---|---|---|---|
| `New-VM -Generation 2`, `Set-VMFirmware`, `Start-VM`, `Stop-VM`, `Get-VM`, `Checkpoint-VM`, `Restore-VMSnapshot`, `Remove-VMSnapshot`, `Set-VMMemory`, `Set-VMProcessor` | group | podman release note for the merged Hyper-V non-admin work ("all actions without … full local Administrator"); hyperv-mcp README prefers the group over elevation | verified by secondary sources; confirm on the first live audit |
| `Invoke-Command -VMName`, `Copy-VMFile` (PowerShell Direct) | group, plus a guest credential | Hyper-V module docs | verified |
| `Set-VMKeyProtector -NewLocalKeyProtector`, `Enable-VMTPM` | group **once the guardian exists**; the first guardian is a setup step | raw cmdlet pages (2026-10-01) state no elevation rule either way | **unverified**: the setup creates the guardian so the question never blocks a run |
| `New-VMSwitch -SwitchType Internal` / `Private` | group (likely) | group description; no primary source | **unverified**: kept in setup |
| `New-VMSwitch` External (binds a physical adapter) | admin (treat as) | it rebinds a host adapter | **unverified**: kept in setup |
| `Enable-WindowsOptionalFeature` (Hyper-V, Windows Sandbox) | admin | optional features are host changes | verified by definition |
| `Add-LocalGroupMember` (join the group) | admin | local groups are host changes | verified by definition |
| `New-HgsGuardian -Name UntrustedGuardian -GenerateCertificates` | admin (treat as) | writes machine certificates | **unverified**: kept in setup |
| `Mount-VHD`, `Optimize-VHD` | admin (treat as) | storage stack | **unverified**: not used by hypervrunner |
| Writing HKLM keys (for example guest-service registrations) | admin | podman: non-admin works only once the entries exist | verified (secondary); not used by hypervrunner |
| `wsb start`, `wsb list`, `wsb ip`, `wsb stop`, opening a `.wsb` file | the signed-in user | Windows Sandbox CLI docs | verified |

## The token, not the account

Windows builds a session's token at sign-in. Membership added afterwards is in the **account**
but not in the running session's **token**, so every Hyper-V call still fails. The audit reads
both: the account from `Get-LocalGroupMember -SID S-1-5-32-578`, the token from the current
identity's groups. In the account but not the token → **sign out and back in** (a restart also
works). Never answer this with elevation: an elevated window hides the problem and teaches the
wrong fix. Build tools that check rights in a stale or filtered session fail the same way
(packer issue 13512).

## What the setup script does

`hyperv_setup.py` writes only the steps the saved audit lists in `needs_setup`:

| Step | Command in the script |
|---|---|
| `enable-hyperv` | `Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All -NoRestart` |
| `enable-sandbox` | `Enable-WindowsOptionalFeature -Online -FeatureName Containers-DisposableClientVM -All -NoRestart` |
| `add-to-group` | `Add-LocalGroupMember -SID 'S-1-5-32-578' -Member '<the audited account>'` |
| `create-guardian` | `New-HgsGuardian -Name UntrustedGuardian -GenerateCertificates`, only if absent |
| switch (on request) | `New-VMSwitch -SwitchType Internal`, or External with `-NetAdapterName` and `-AllowManagementOS $true` |

The script refuses to run unelevated, stops on the first error, downloads nothing, and prints
whether a restart or a sign-out is needed. The user runs it with
`powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File '<path>'` from a PowerShell window
they opened as administrator. `RemoteSigned` applies to that one process and still blocks
downloaded scripts; `Bypass` is never used. The printed SHA-256 lets the user check the file
they run is the file they read (`Get-FileHash`).

## Identify the build first

Windows Sandbox's CLI (`wsb`) arrived in Windows 11 24H2 (build 26100). The `.wsb` file works
from build 18342. The audit reports the build and UBR so every other answer can depend on it.
