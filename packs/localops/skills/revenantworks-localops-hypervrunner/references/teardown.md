# Teardown: the controlled soft delete

**Read this file when:** running `teardown` or `purge`, or when someone asks to delete, remove or
clean up a VM.

`scripts/teardown.py` is the only hypervrunner script that holds a remove command. gatewarden's
`hyperv_lock.py` allows the remove commands through it and through nothing else, so every other
Hyper-V delete Claude tries is blocked (owner decision 2026-10-02).

## The locks

Every lock must hold; any miss is a reason in the plan and the verdict is `refuse`.

| Lock | Holds when | Why |
|---|---|---|
| 1 · creation record | the VM's GUID is in `own-vms.json`, written only by `vmctl.py create` | the skill never adopts a VM it did not make |
| 2 · Notes marker | the VM's Notes carry `hypervrunner:own` | a second, independent sign; a name alone is never enough |
| disk lock | each disk's **real path** (junctions and symlinks followed) lies inside the skill's disk folder, ends in `.vhdx` or `.vhd`, is not on the protected list, not attached to another VM and not already in quarantine | a junction inside the folder that points elsewhere resolves outside and is refused |
| state | the VM is Off and has no checkpoints | teardown never turns a VM off; the user removes checkpoints in Hyper-V Manager first |
| clean room | the VM is not a clean-room VM | its golden base and checkpoint are protected |

The disk folder is the user's `disk_root` in `config.json` (an absolute path), else
`<state>/hypervrunner/disks`. `vmctl.py create` makes new disks there. A VM created on an
existing `--vhdx` outside that folder cannot be torn down by the skill; `plan-create` says so.
VMs made before the marker existed fail lock 2: the user removes those in Hyper-V Manager.

**Protected list** (`protected.json`, disks and checkpoint GUIDs): `teardown.py protect --disk P` or
`--checkpoint-id G` adds an entry. Taking an entry off is the user's own edit of that file.

## Plan, then only that plan

1. `teardown.py plan --vm-id <GUID> [--run-id R]` reads live state and prints the plan: the VM
   (name, GUID, state), each disk's path, real path and size, the quarantine folder, who may
   approve, the reasons, and the plan's **sha256**. It changes nothing.
2. Show the plan and the sha256. Authority:
   - **`--ephemeral` VM, same run:** a VM made with `vmctl.py plan-create --ephemeral` carries a
     `run_id` in its record. The run holding that `run_id` may execute without asking.
   - **Every other VM:** the user's yes to this plan. Only then pass `--owner-ok`.
3. `teardown.py execute --vm-id <GUID> --sha <sha256> [--run-id R | --owner-ok]` re-reads live
   state and rebuilds the plan. Any change (a disk grew, the VM started, a lock moved) changes the
   sha256, and it refuses without touching anything: re-plan and show it again.

Unattended mode tears down only its own same-run ephemeral VMs; anything else is set aside with
the reason.

## Soft delete

- **Quarantine first:** the quarantine folder is made and checked writable **before** the
  unregister. If either fails, the teardown stops with the VM still registered and nothing moved.
- **Unregister:** one PowerShell call fetches the VM by GUID, re-checks the GUID, the marker and
  the Off state, then unregisters that object (never by name). If it fails, nothing is moved, and
  the empty quarantine folder this run made is taken back so a fresh plan can run.
- **Move:** each disk goes to `<disk folder>/_quarantine/<GUID>/<n>-<file>` by a same-volume
  rename (never a copy), and `manifest.json` records the VM, each disk's old and new path and
  size, the time, the authority and the plan sha256.
- **Record:** the GUID's record stays and gains `torn_down`; nothing in it is deleted.
- **Log and verify:** one line in `teardown-log.jsonl`; verify checks the VM no longer
  registers, each original path is gone and each quarantined file has its planned size. Any
  miss is FAIL, exit 1, with expected and actual. Report the checks, never "deleted".

**Undo** while the entry exists: the user moves the disk back and Claude runs
`vmctl.py plan-create --vhdx <disk>` (a new VM, a new GUID, on the old disk).

## Purge

Purge frees the space for good.

- **Owner command:** `teardown.py purge-command --entry <GUID>` prints
  `python <script> purge --entry <GUID>` and what it discards. The user runs it in their own
  terminal; gatewarden blocks Claude running it.
- **After N days:** if the user set `purge_after_days` in `config.json`, Claude may run
  `teardown.py purge --due`, which purges only entries at least that old. Not set: nothing is due.
- Each purge re-checks the entry: inside the quarantine folder by real path, every file named in
  the manifest resolves inside the entry, matches its recorded size and is not protected, and the
  entry holds no file the manifest does not name. Any miss refuses the entry and leaves it whole.
  Purge deletes only those files, then the manifest and the empty folder, then logs and verifies.

`teardown.py list` shows each entry's VM, age, size and whether it is due.

## Limits, stated plainly

The locks bind the commands Claude runs. Admin rights and Hyper-V Administrators membership let
the user run any removal in their own terminal; this skill neither can nor tries to stop that.

Unregistering is assumed to need only the group right the other VM cmdlets use
(`admin-split.md`); moving the disks needs write access to the disk folder, which the account
owns. Neither has run on a live host yet: on the first live teardown, show the raw output of the
unregister and of verify before any summary.
