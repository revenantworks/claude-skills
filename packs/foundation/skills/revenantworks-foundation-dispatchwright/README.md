# revenantworks-foundation-dispatchwright

Runs a session's fan-out. Turns one large request — a rebuild, a re-architecture, a sweep
across many repos or skills — into units small enough to finish, tiers each one from its own
tier table, fits the wave into the usage windows, shows the table and stops for a go, dispatches
with a durability contract, and reconciles the result against the repo itself, never against an
agent's own report.

What separates it from ad hoc multi-agent orchestration:

- **It never invents a tier.** Every unit's tier, model, and effort come from this skill's own
  `references/tier-routing.md` (self-contained since 1.2.9), written into the ledger before the
  unit launches.
- **Nothing launches before the table and the go.** A plan ends on one table per wave — unit,
  class, model, effort, est. tokens, est. wall, window — and one confirmation line, then stops
  (since 1.3.0). The window column comes from the rig's usage-windows reading, or from the owner
  when there is no fresh reading; a percent becomes tokens only through a measured calibration,
  never a guess.
- **Every unit is done when it is on the remote, not when it is written.** Commit and push are
  one atomic call, pushed after every finished piece of work, never held to the end.
- **A ledger row, not a report, is the record.** Reconcile checks every row against
  `git rev-parse origin/main`; a unit's own account of what it did is never the proof.
- **Resume never redoes landed work.** The first action on picking up a dead or stalled run is
  reading origin and the ledger — before anything else.
- **Waves are capped.** Six concurrent units, two nesting levels, a worktree for every writer, a
  stagger across launch, and a check of the remaining usage window before a top-tier wave.

**Workflow:** Shape check → Decompose → Tier → Durability contract → Wave execution → Escalation
→ Reconcile

## Package contents

```
revenantworks-foundation-dispatchwright/
├── SKILL.md                      # entry point — scope, shape check, decompose, tier, durability
│                                  # contract, wave execution, escalation, reconcile, anti-patterns
├── README.md · LICENSE · CHANGELOG.md · SOURCES.md
├── references/
│   ├── ledger-schema.md          # the run ledger's fields, a worked row, and where it lives
│   ├── unit-brief-template.md    # the copy-paste brief every dispatched unit carries
│   ├── tier-routing.md           # the skill's own tier table, effort ladder and overrides (1.2.9)
│   ├── window-fit.md             # the plan table, the stop, and fitting a wave into the usage windows (1.3.0)
│   └── anti-patterns.md          # the 13 failure modes, one line each, with the 2026-08-17 examples
└── evals/                        # in full folder-zips, excluded from .skill
    ├── trigger-evals.md          # 16 should-fire, 13 should-not, 2 injection probes
    ├── test-cases.md             # 18 assertion cases
    └── RESULTS.md                # the run ledger — what was judged, what is authored-not-run, what is owed
```

## Install

Follows the [Agent Skills](https://agentskills.io/) open standard. Drop the folder into your
skills directory, or upload the archive in Claude settings. Trigger it by saying `dispatchwright`,
by describing a request that spans many agents, repos, skills, or files at once, or by naming a
stalled fan-out that needs to resume without redoing landed work. Self-contained: no executable
code ships. `git` and the surface's subagent/Task tools are optional — without `git` a run still
plans, tiers and dispatches but reports an unverifiable row as unverified rather than done;
without subagent tools a run ends at the tiered plan and the ledger.

The two forcing hooks are not package contents. They are rig infrastructure, kept in the
`claude-skills` repo under `.claude/hooks/` and installed from there into `~/.claude/hooks/` by a
rig that wants them. Nothing below depends on them.

## Entry points

| Entry | What it does |
|---|---|
| **plan** | Runs Shape check first — says so and stops if the request isn't a real fan-out. Otherwise decomposes, tiers from its own table, fits the wave into the usage windows (reads `~/.claude/usage-windows.json` when fresh, else asks the owner per window), writes the ledger, and ends on one table — unit, class, model, effort, est. tokens, est. wall, window — plus one confirmation line, then stops for the go |
| **dispatch** | An approved plan → a ledger row per unit before launch, then the wave runs per the wave-execution caps, with no second ask; a unit added mid-run is announced and asks again only if it no longer fits the window |
| **resume** | A dead, stalled, or usage-limited run → reads origin and the ledger first, re-dispatches only what is unfinished or unverified |
| **audit** | Reconciles a running or finished run against `git rev-parse origin/main`; read-only, reports and never re-dispatches on its own |

## The seams

- **Tiering is its own** (since 1.2.9, observation #0073): `references/tier-routing.md`, a
  one-time copy of promptwright's snapshot, refreshed by `dispatchwright refresh` — no sibling
  is needed to complete a plan.
- **Where the trigger lives is rigwright's.** The hook or CLAUDE.md rule that makes a big request
  reach for dispatchwright is rigwright's placement call.
- **Unattended runs are agentwright's, whole.** A cron job or anything firing with nobody reading
  the result is out of scope here.
- **A general session handoff is resumewright's.** Inside an active fan-out the ledger and
  `dispatchwright resume` carry the state; everything outside that is resumewright's.

## Usage windows, in one line

Only a statusLine command sees the subscription windows, so the rig's `usage_windows.py` writes
them to `~/.claude/usage-windows.json`; a plan reads that file when it is under 15 minutes old
and asks the owner otherwise, converts percent to tokens only through
`~/.dispatch/usage-calibration.json` (a running median of verified waves — with fewer than two
measurements it says so and asks), and marks every unit with the first window it fits. Full
contract: `references/window-fit.md`.

## Durability contract, in one line

Atomic commit+push, pushed after every finished piece of work and before any report, a ledger row
at dispatch/commit/push, and `git log --oneline origin/main -5` plus the ledger as resume's first
action — never the last.

## What did not land at 1.0.0

- ~~No routing-seam row.~~ **Closed at 1.0.1 (2026-08-18).** `pack-registry.md`'s seam table now
  carries dispatchwright ↔ promptwright, ↔ rigwright, and ↔ agentwright, riding the generated
  table the way an established pack member's do. All three are recorded as one-sided, uncontested
  edges — none of the three siblings' descriptions name dispatchwright back — which is the
  accurate state, not a placeholder for a future negotiation.
- **No assertion suite.** `evals/` ships trigger evals only; a mechanical `test-cases.md` proving
  the durability contract and Reconcile behavior under a live dispatch is owed.
- **No cold-listing judge.** `evals/RESULTS.md` records the trigger suite as authored, not run.

## What landed at 1.0.1

- **Shipped hooks synced to the fixed live originals.** `references/hooks/dispatch_gate.py` and
  `dispatch_ledger_guard.py` had drifted to the pre-fix, fail-open versions while the installed
  hooks at `~/.claude/hooks/` were repaired (D1-D4, see CHANGELOG.md). Both files are now byte-for-
  byte the fixed versions, and both selftests pass against the copies shipped here.

## What landed at 1.2.0

- **The forcing hooks left the package; the profile went back to standalone.** `dispatch_gate.py`,
  `dispatch_ledger_guard.py` and `dispatch_patterns.txt` moved to the `claude-skills` repo's own
  `.claude/hooks/`. No line of either script changed and both selftests pass from the new
  location. With no executable code shipped, and `git` and subagent tools restated as optional
  with their degradation named, `profile: standalone` is true again — earned by the change, not
  by the label.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
