# revenantworks-localops-dockerrunner

Runs Docker Desktop on Windows, and the WSL2 virtual machine under it, and checks the machine
before any container work starts.

## Why it exists

Docker tools for agents already exist. They list containers, bring up compose stacks and prune
on request, and they do it well. None of them looks at the machine first. Three problems come
up again and again on Windows:

- **WSL holds RAM and does not give it back.** The `vmmem` process grows to the VM's cap, which
  defaults to half of all RAM (microsoft/WSL issue 4166).
- **The Docker disk only grows.** A prune frees space inside the VM; the VHDX file on the host
  stays the same size (microsoft/WSL issue 4699).
- **Other local jobs share the RAM.** On a machine that also runs local models or renders, a
  container job started mid-render competes for the same memory.

dockerrunner reads the WSL memory cap in `.wslconfig`, the localops pack's lease (who is running
a GPU job right now), and the VHDX size on the host, before it acts.

## What it will not do

- Install anything. Missing Docker Desktop, WSL or a distro gets an owner walkthrough with a
  check per step and a way back.
- Run a destructive step. A prune, a volume removal, `wsl --shutdown` or a disk compaction goes
  to you as **one command** you run.
- Prune volumes by default. A volume is removed only when you name it and nothing uses it.
- Edit `.wslconfig` in place. It writes a proposal beside the file and gives you one copy line.
- Elevate itself. Steps that need admin say so and stop.
- Drive Docker's MCP Toolkit or Docker Model Runner. It routes those away.

## The two modes

**Interactive** — you are present. Proposals and missing readings are put to you.

**Unattended** — nobody is watching. Every value must be yours, every reading measured; only a
compose file you named runs, and only pinned image tags are pulled. Anything less is refused with
the reason.

## Entry points

| Command | What it does |
|---|---|
| `dockerrunner audit` | Desktop version, backend, context, distros, `.wslconfig` vs RAM, vmmem, VHDX sizes, `docker system df`, the lease; findings. Changes nothing |
| `dockerrunner check` | Pass or fail for a job's RAM and disk needs against the WSL cap, the lease and the host |
| `dockerrunner up <file>` | Shows the resolved compose plan and its risky lines, then starts the stack on your yes |
| `dockerrunner down <file>` | Stops the stack; never deletes its volumes or images |
| `dockerrunner prune` | A dry list and one command that removes exactly the listed IDs; reclaim advice for the VHDX |
| `dockerrunner status` | Running containers, stacks, the lease, disk growth since the last recorded audit |
| `dockerrunner refresh` | Re-verify the WSL and command references and restamp them |

## The WSL memory cap

The default rule is **about a third of installed RAM**, so local GPU jobs keep room. The audit
reads your real RAM first and proposes the figure. `scripts/wslconfig_plan.py` writes
`.wslconfig.proposed` beside your file; you run one line that backs up the original, copies the
proposal in and restarts WSL (which stops running containers).

## Package

```
revenantworks-localops-dockerrunner/
├── SKILL.md
├── README.md · CHANGELOG.md · SOURCES.md · LICENSE
├── references/
│   ├── wslconfig.md            # keys, defaults, the cap rule (dated)
│   ├── commands.md             # CLI surface, compose, exec, no-shell (dated)
│   ├── disk-reclaim.md         # prune list, volumes, VHDX compaction, admin
│   ├── ram-lease.md            # how the pack lease is read
│   ├── install-walkthrough.md  # owner-run install steps
│   └── pack.md                 # localops roster (generated)
├── scripts/
│   ├── docker_preflight.py     # read-only: audit, check, status, prune-list
│   ├── wslconfig_plan.py       # proposal beside the file, never in place
│   └── test_*.py
└── evals/
    ├── trigger-evals.md · test-cases.md   # hand-run suites
    └── <case>/prompt.md + graders/        # native `claude plugin eval` cases
```

## Install

Ships in the localops pack: `/plugin marketplace add revenantworks/claude-skills`, then
`/plugin install localops@<marketplace>`. On claude.ai, upload the skill folder (Customize →
Skills); without a shell it hands you commands to run and reads the pasted output.

## Staying current

`references/wslconfig.md`, `references/commands.md` and `SOURCES.md` carry a Last-verified stamp
and a 90-day cadence. Run `dockerrunner refresh` when one is due.

[CHANGELOG.md](CHANGELOG.md)
