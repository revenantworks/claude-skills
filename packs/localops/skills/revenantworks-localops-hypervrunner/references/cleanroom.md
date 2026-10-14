# Clean-room plugin install test

**Read this file when:** running `cleanroom`, or helping the user build the golden image.

## Why

A plugin that installs on the author's machine can still fail on a clean one: a marketplace
path, a missing dependency, a skill that only loads because something else was already
installed. The clean-room test installs the public plugin on a machine that has never seen it,
from the same golden state every time, and keeps a receipt.

## The golden image (owner steps, once)

1. `hypervrunner vm` with `--cleanroom` (Windows guest, 4 GB or more, Gen2 profile). The VM's
   Notes get `hypervrunner:cleanroom golden=golden`.
2. Inside the VM: install Windows, create a **separate local test account** (never the user's
   own account), install Claude Code for that account, and sign Claude Code in with the
   **separate test login** the user chose for this. Windows updates applied.
3. Shut the VM down, then take the golden checkpoint: `vmctl.py checkpoint --name <vm>
   --checkpoint-name golden` (production type, VM off, so a restore always lands powered off).
4. On the host, make the guest credential file once, in the user's own PowerShell window:
   `Get-Credential | Export-Clixml -Path "$env:LOCALAPPDATA\localops\hypervrunner\guest-credential.xml"`
   (the guest test account's user name and password). Export-Clixml encrypts the password with
   Windows DPAPI for this user on this machine only. hypervrunner checks the file exists and is
   outside every repo; it never reads, prints or copies it.

To rename the golden checkpoint, change both the checkpoint and the `golden=` token in the Notes;
`plan` refuses a mismatch.

## A run

1. `cleanroom.py plan --vm <vm> --golden golden --source <owner/repo[#ref] or https URL .git>
   --plugin <name@marketplace> --write P.json`. It refuses a VM without the exact tag, a missing
   checkpoint, a missing credential file or one inside a git repository, and any source or plugin
   string outside the allowlist patterns.
2. RAM pre-flight for the VM's memory (`ram-preflight.md`).
3. `cleanroom.py run --plan P.json`. On the host: re-check the tag, revert to golden, start, wait
   for the heartbeat. In the guest, through PowerShell Direct as the test account:
   `claude --version`, `claude plugin marketplace add <source>`,
   `claude plugin install <plugin> --json`, `claude plugin list --json`. Then, in a `finally`,
   revert to golden again: a failed or hung run never leaves the VM dirty.
4. Receipt (JSON, in the per-user state folder unless `--out`): plugin, source, VM, golden
   checkpoint id and creation time, start and finish times, Claude Code version, each step's exit
   code, PASS or FAIL with problems. Guest output is kept out of the receipt; only exit codes and
   the version line are recorded.

**PASS** needs all four steps at exit 0 and the plugin's id in the `claude plugin list --json`
output. Anything else is FAIL with the reason; a plugin that installs but is not listed is a FAIL.

**Install commands.** A plugin whose marketplace entry runs a command at install asks
`Run this command now?`; without a terminal the install is refused and the receipt says so.
`--accept-install-command` passes `-y`. Use it only on the user's yes, after trustwarden (or the
owner) has looked at what the command does; it runs inside the throwaway VM, which is reverted
afterwards.

## Golden age

The audit reports the golden checkpoint's age. Past 30 days it warns: patch the image (start,
update, shut down, retake the checkpoint by the same name after the user removes the old one
through an owner command). A stale image tests against an old Windows and an old Claude Code.

## Hand-off

The receipt is the evidence a release check can cite; skillwright's release step may ask for it.
A FAIL is reported with the failing step, never retried silently.
