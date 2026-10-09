# revenantworks-localops-hypervrunner

Runs Hyper-V VMs and Windows Sandbox on a Windows machine for isolation and testing, and proves
what it built. Other Hyper-V tools wrap the cmdlets; this one **verifies a Gen2 VM's security
profile after building it** (secure boot, template, virtual TPM: FAIL on any miss), **runs a
clean-room install test of a public Claude Code plugin from a golden checkpoint** with a receipt,
and **tests untrusted downloads in a locked-down Windows Sandbox** whose networking is checked after
start; what a download holds is data, never instructions. It works as a member of Hyper-V Administrators and never elevates itself. Restores, turn-offs
and resets go to the user as one command; removing a VM is a **controlled soft delete** of its own
VMs only (two locks, a junction-safe disk lock, the plan's sha256, the user's OK, a quarantine
folder, then purge), and gatewarden's Hyper-V lock blocks every other delete.

Part of the **localops** pack (`-runner` motif, standard profile). Agent Skills open standard
(agentskills.io).

## Package

```
revenantworks-localops-hypervrunner/
├── SKILL.md
├── README.md · CHANGELOG.md · SOURCES.md · LICENSE
├── references/
│   ├── admin-split.md          # group member vs one elevated setup (volatile, 90 days)
│   ├── gen2-profile.md         # build, verify, start/stop, checkpoints, owner commands
│   ├── teardown.md             # the locks, plan and sha256, soft delete, quarantine, purge
│   ├── cleanroom.md            # golden image, the run, the receipt
│   ├── sandbox.md              # sandbox vs VM, the locked-down config, the network proof
│   ├── ram-preflight.md        # RAM and commit check, the pack's GPU lease (read only)
│   ├── install-walkthrough.md  # owner steps with checks and rollbacks
│   └── pack.md                 # generated pack manifest
├── scripts/                    # stdlib Python, run not read
│   ├── hyperv_common.py · hyperv_audit.py · hyperv_setup.py
│   ├── vmctl.py · teardown.py · cleanroom.py · sandbox_config.py
│   └── test_hypervrunner.py · test_teardown.py
└── evals/                      # hand-run suites + native claude plugin eval cases
```

## Install

Claude Code: install the localops pack from the plugin marketplace. claude.ai: upload the
folder as a skill (the scripts need a shell, so on claude.ai it hands back PowerShell instead).
Windows features, group membership and the golden image are owner steps:
`references/install-walkthrough.md`.

## Commands

| Say | Does |
|---|---|
| `hypervrunner audit` | Read-only: build, Hyper-V, group in account and token, VMs and their profile, checkpoints, switches, guardian, sandbox tools, memory, GPU lease |
| `hypervrunner setup` | Writes the one elevated script with only the missing steps, its SHA-256 and the command; the user runs it |
| `hypervrunner vm` | Plan, create (on yes), verify the Gen2 profile; start with a RAM pre-flight; stop by guest shutdown |
| `hypervrunner checkpoint` | Take or list; a restore is an owner command, removing one is the user's act in Hyper-V Manager |
| `hypervrunner teardown <VM>` | Plan with sha256 → the user's OK (or same-run `--ephemeral`) → unregister, disks to quarantine, log, verify |
| `hypervrunner purge` | List quarantine; `purge --due` after the user's `purge_after_days`, or hand the user the purge command |
| `hypervrunner cleanroom <plugin@marketplace> <source>` | Revert golden, install in the guest, list, revert, receipt |
| `hypervrunner sandbox <file or folder>` | Locked-down Windows Sandbox, read-only input, one empty output, network proof |
| `hypervrunner status` | VMs, running sandboxes, lease holder, last receipt |
| `hypervrunner refresh` | Re-verify `admin-split.md` and restamp it |

Switches: `interactive` / `unattended` mode (stated on every proposal), `--linux` (UEFI CA
template), `--cleanroom` (tags the VM), `--ephemeral` (the same run may tear it down),
`--accept-install-command` and `--owner-ok` (owner's yes only).

## Tests

```
python -m unittest discover -s scripts -p "test_*.py"
```

Pure logic and temp files only: PowerShell is a fake, no Hyper-V or sandbox is touched.

## Staying current

`references/admin-split.md` and `SOURCES.md` are calendar surfaces (90 days); `skillwright
upkeep` flags them, `hypervrunner refresh` re-verifies the first. The rows still marked
unverified (first vTPM guardian, Internal and External switch rights) move only on a live test.

History: [CHANGELOG.md](CHANGELOG.md).
