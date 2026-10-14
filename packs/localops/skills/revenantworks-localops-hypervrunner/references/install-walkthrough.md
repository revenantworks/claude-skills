# Install walkthrough (the user runs every step)

**Read this file when:** the audit reports a missing feature, tool or golden image.

hypervrunner installs nothing. These are the user's steps, each with a check and a rollback.
Steps 1 to 3 are what `hypervrunner setup` writes into its one elevated script; this page is the
by-hand version and the rollback reference.

## 0. Check the edition and build

`Get-CimInstance Win32_OperatingSystem | Select-Object Caption, BuildNumber`
Hyper-V needs Pro, Enterprise or Education. The `wsb` CLI needs build 26100 (24H2) or later.
Virtualisation must be on in the firmware: `(Get-CimInstance Win32_ComputerSystem).HypervisorPresent`
is `True` once Hyper-V runs.

## 1. Enable Hyper-V (elevated, restart)

`Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All -NoRestart`, then restart.
- **Check:** `Get-Service vmms` shows Running; `Get-Module -ListAvailable Hyper-V` lists the module.
- **Rollback:** `Disable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All`, restart.
  Docker Desktop and WSL 2 share the hypervisor; disabling Hyper-V does not remove the platform
  they use, but check them afterwards.

## 2. Enable Windows Sandbox (elevated, restart)

`Enable-WindowsOptionalFeature -Online -FeatureName Containers-DisposableClientVM -All -NoRestart`, then restart.
- **Check:** `Test-Path "$env:windir\System32\WindowsSandbox.exe"` is True; on 24H2 or later,
  `wsb --help` answers.
- **Rollback:** `Disable-WindowsOptionalFeature -Online -FeatureName Containers-DisposableClientVM`, restart.

## 3. Join Hyper-V Administrators (elevated, sign out)

`Add-LocalGroupMember -SID 'S-1-5-32-578' -Member '<your account>'`, then sign out and back in.
- **Check:** `whoami /groups | Select-String S-1-5-32-578` returns a line in a normal (not
  elevated) window.
- **Rollback:** `Remove-LocalGroupMember -SID 'S-1-5-32-578' -Member '<your account>'`, sign out.

## 4. The untrusted guardian for virtual TPMs (elevated)

`New-HgsGuardian -Name UntrustedGuardian -GenerateCertificates` (skip if
`Get-HgsGuardian -Name UntrustedGuardian` already answers).
- **Check:** `Get-HgsGuardian -Name UntrustedGuardian` returns it.
- **Rollback:** only with no VM using it: `Remove-HgsGuardian -Name UntrustedGuardian`. A VM
  whose key protector came from it will not start afterwards.

## 5. The clean-room golden image (normal window)

Follow `cleanroom.md`, "The golden image": VM, Windows, a separate test account, Claude Code,
the separate test login, updates, shut down, checkpoint `golden`, and the DPAPI credential file.
- **Check:** `hypervrunner audit` lists the VM with `cleanroom_golden` and an age in days.
- **Rollback:** a clean-room VM holds the golden base, so teardown refuses it by design. Remove it
  yourself in Hyper-V Manager, then delete its `.vhdx` and the credential file by hand.

## 6. Optional settings for teardown (normal window)

`config.json` in the skill's state folder (`%LOCALAPPDATA%\localops\hypervrunner\`) takes
`disk_root` (an absolute folder for new VM disks and their quarantine; keep it on one volume) and
`purge_after_days` (an integer; unset means only your own purge command frees space).
- **Check:** `python <skill>\scripts\teardown.py list` answers with a JSON list.
- **Rollback:** delete the key. Disks already made stay where they are; teardown refuses any disk
  outside the folder it reads at plan time.

## 7. Re-pin after any change to the pinned scripts (only with gatewarden's Hyper-V lock)

gatewarden's `hyperv_lock` runs `teardown.py`, `cleanroom.py` and `vmctl.py` only while each
matches the sha256 you pinned. Any edit to one of them — an update, a fix round, one character —
blocks it silently until you re-pin, so every change to these three files says so in its
CHANGELOG line and its report, and names this step.
- **Run:** `python "$HOME\.claude\hooks\gatewarden\hyperv_lock.py" --pin "<skill>\scripts"` (from
  the files on disk; never copy a hash from a document).
- **Check:** `python <skill>\scripts\teardown.py list` runs instead of being blocked with "does not
  match its pinned sha256".
- **Rollback:** none needed; re-running the pin replaces the old pins.
