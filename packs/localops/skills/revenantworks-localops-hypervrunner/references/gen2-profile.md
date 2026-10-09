# Gen2 security profile, VM control and checkpoints

**Read this file when:** running `vm` or `checkpoint`.

## The profile, built and then proved

`vmctl.py plan-create` writes these steps (names and paths enter only as PowerShell
single-quoted literals, after an allowlist check):

1. `New-VM -Generation 2 -MemoryStartupBytes … -NewVHDPath … -NewVHDSizeBytes …` (or `-VHDPath`
   for an existing disk), with `-SwitchName` when one is named. A new disk goes in the host's
   default virtual-disk folder.
2. `Set-VMProcessor -Count`; `Set-VM -CheckpointType Production -AutomaticCheckpointsEnabled $false`
   (production checkpoints apply cleanly; automatic ones pile up unseen).
3. With an ISO: `Add-VMDvdDrive`, then `Set-VMFirmware -FirstBootDevice` to the DVD.
4. `Set-VMFirmware -EnableSecureBoot On -SecureBootTemplate MicrosoftWindows`
   (`MicrosoftUEFICertificateAuthority` with `--linux`).
5. `Set-VMKeyProtector -NewLocalKeyProtector`, then `Enable-VMTPM`. The first key protector on a
   host needs the untrusted guardian (setup step `create-guardian`).
6. `Set-VM -Notes 'hypervrunner:own'` on every VM (teardown's lock 2), with
   `hypervrunner:cleanroom golden=golden` added under `--cleanroom`.

A new disk goes in the skill's own disk folder (the user's `disk_root` in `config.json`, else
`<state>/hypervrunner/disks`), so a later teardown can move it. `create` records the VM's GUID
(lock 1); `--ephemeral` adds a `run_id` to the plan and the record, and only that run may tear the
VM down without asking (`teardown.md`). A clean-room VM cannot be ephemeral.

`create --plan` rebuilds the steps from the plan's parameters and refuses the plan if its steps
differ, so an edited plan file can never smuggle in another command. It needs a RAM verdict of
`go`, or `ask` answered by the user.

**Verify** reads `Get-VM`, `Get-VMFirmware` and `Get-VMSecurity` and checks four values:

| Check | Expected |
|---|---|
| generation | 2 |
| secure_boot | On |
| secure_boot_template | MicrosoftWindows (or MicrosoftUEFICertificateAuthority for Linux) |
| tpm_enabled | True |

Any miss is **FAIL**, exit 1, with expected and actual per check. Report the failing check; never
call a VM "created with TPM" on the strength of the commands having run.

## Start and stop

- `start` reads the VM's startup memory, runs the RAM pre-flight (`ram-preflight.md`) and starts
  only on `go`.
- `stop` is `Stop-VM` with neither `-TurnOff` nor `-Force`: a guest shutdown through the
  integration services. If the guest refuses, report it; turning off is an owner command.

## Checkpoints

- `checkpoint --checkpoint-name C` runs `Checkpoint-VM -SnapshotName C` (production type).
- `checkpoints` lists name, id, type and creation time (UTC).
- A restore is an **owner command** (`owner-command --op restore`): hand over the line and what
  it discards, everything since the checkpoint.
- Removing a checkpoint is the user's own act in Hyper-V Manager; a removal merges it away for
  good. Teardown refuses a VM that still has checkpoints.

## Owner commands, the full set

| op | Command handed over | What it discards |
|---|---|---|
| restore | `Restore-VMSnapshot -VMName 'N' -Name 'C' -Confirm:$false` | the VM's state since C |
| turnoff | `Stop-VM -Name 'N' -TurnOff -Confirm:$false` | unsaved guest work |
| reset | `Restart-VM -Name 'N' -Force` | unsaved guest work |

Removing a VM is not an owner command here: it is `teardown.py`'s controlled soft delete
(`teardown.md`), and the purge that frees its disks is the user's `purge-command` line.

## Degrading without a shell

Hand back the same statements for the user to paste into Windows PowerShell, one block per
step, and mark verify NOT-RUN until the user pastes back the output of:

```powershell
$v=Get-VM -Name 'N'; $fw=Get-VMFirmware -VM $v; $s=Get-VMSecurity -VM $v
[ordered]@{name=$v.Name; generation=$v.Generation; secure_boot=[string]$fw.SecureBoot; template=$fw.SecureBootTemplate; tpm=$s.TpmEnabled} | ConvertTo-Json
```

Save that JSON and run `vmctl.py verify --from-json F` when Python is available, or check the four
rows above by eye and say so.
