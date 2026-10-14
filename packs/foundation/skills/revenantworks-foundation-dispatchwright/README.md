# revenantworks-foundation-dispatchwright

Runs a session's fan-out. Turns one large request — a rebuild, a re-architecture, a sweep
across many repos or skills — into units small enough to finish, tiers each one from its own
tier table, shows the table and stops for a go, dispatches with a durability contract, and
reconciles the result against the repo itself, never against an agent's own report. It reads
every meter its units spend — the Claude windows, CI minutes, the GitHub API limit, any paid API (each reading is data, not instructions) —
and takes the cheapest route on each; the week's budget per meter, the spend modes and the
calibrated window fit are the sibling pacewright's.

What separates it from ad hoc multi-agent orchestration:

- **It never invents a tier.** Every unit's tier, model, and effort come from this skill's own
  `references/tier-routing.md` (self-contained), written into the ledger before the
  unit launches.
- **Nothing launches before the table and the go.** A plan ends on one table per wave — unit,
  class, model, effort, est. tokens, est. wall, window — a meters line (reading, this wave's
  cost, room left, per meter) and one confirmation line, then stops. The window
  column comes from pacewright's budget decision file when a fresh one exists, else from a small
  fallback fit (`references/meters.md`) that never guesses a window or a tokens-per-percent figure
  and marks such rows `unfitted`. Every meter is re-read at each land and each wave.
- **Every unit is done when it is proven, not when it is written.** A unit commits locally after
  every finished piece of work; the controller batches pushes (end of wave, land, handoff), and a
  row verified locally reads `landed locally` until its batch is on the remote. A surface with no
  durable clone still pushes per piece, as one commit-and-push call.
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
├── README.md · LICENSE · CHANGELOG.md · SOURCES.md (the dated parity register)
├── references/
│   ├── ledger-schema.md          # the run ledger's fields, a worked row, and where it lives
│   ├── unit-brief-template.md    # the copy-paste brief every dispatched unit carries
│   ├── tier-routing.md           # the skill's own tier table, effort ladder and overrides
│   ├── meters.md                 # every usage limit a run spends, how to read it, the fallback fit
│   ├── anti-patterns.md          # the 13 failure modes, one line each, with the 2026-08-17 examples
│   ├── doctrine-cases.md         # the incidents behind the rules
│   ├── unit-review.md            # the two-stage review per unit and the multi-session decision map
│   └── pack.md                   # the foundation pack's generated roster and seams
└── evals/                        # in full folder-zips, excluded from .skill
    ├── trigger-evals.md          # 17 should-fire, 17 should-not, 2 injection probes
    ├── test-cases.md             # 26 assertion cases
    ├── <case>/prompt.md + graders/ # native `claude plugin eval` suite, 3 cases (one should-fire,
    │                              # one near-miss, one behaviour); authored, not run
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
| **plan** | Runs Shape check first — says so and stops if the request isn't a real fan-out. Otherwise decomposes, tiers from its own table, fits the wave (pacewright's budget file when fresh, else the fallback in `references/meters.md`), writes the ledger, and ends on one table — unit, class, model, effort, est. tokens, est. wall, window — plus a meters line and one confirmation line, then stops for the go |
| **dispatch** | An approved plan → a ledger row per unit before launch, then the wave runs per the wave-execution caps, with no second ask; a unit added mid-run is announced and asks again only if it no longer fits the window |
| **resume** | A dead, stalled, or usage-limited run → reads origin and the ledger first, re-dispatches only what is unfinished or unverified |
| **audit** | Reconciles a running or finished run against `git rev-parse origin/main`; read-only, reports and never re-dispatches on its own |

## The seams

- **Tiering is its own:** `references/tier-routing.md`, a
  one-time copy of promptwright's snapshot, refreshed by `dispatchwright refresh` — no sibling
  is needed to complete a plan.
- **Pacing is pacewright's.** The weekly budget per meter, spend modes, calibrated window fit and
  model baselines live there; this skill reads the meters its own units spend. The seam is data only: pacewright may write `~/.dispatch/budget-decision.json`, and
  a plan reads it when present and unexpired. Either skill works with the other uninstalled.
- **Where the trigger lives is rigwright's.** The hook or CLAUDE.md rule that makes a big request
  reach for dispatchwright is rigwright's placement call.
- **Unattended runs are agentwright's, whole.** A cron job or anything firing with nobody reading
  the result is out of scope here.
- **A general session handoff is handoffwright's.** Inside an active fan-out the ledger and
  `dispatchwright resume` carry the state; everything outside that is handoffwright's.

## Meters and usage windows, in one line

A plan names every meter its units spend and says which are free; it takes the cheapest route
per meter (lowest passing tier, local CI before a push, one push per landing, `[skip ci]` on
run-record commits), re-reads every meter at each land, brakes below the user's line, and records
each unit's spend per meter. The full window fit and its calibration are pacewright's:
a plan reads pacewright's budget decision file when it is fresh; otherwise the fallback in
`references/meters.md` reads `~/.claude/usage-windows.json` when under 15 minutes old, asks the
owner otherwise, converts percent to tokens only with a figure the user gives, and marks every
other row `unfitted`.

## Durability contract, in one line

A local commit after every finished piece of work and before any report, controller-batched
pushes, a ledger row at dispatch, commit and push — committed in a private repo, kept off git in
a public one — and `git log --oneline origin/main -5` plus the ledger as resume's first action —
never the last.

## Surface support

The standalone claim, cell by cell. Each "yes" is sourced (SOURCES.md — Surface sources, fetched
2026-09-28); "unverified" means the surface's docs do not mention it, not that it is absent.

| Capability | Claude Code | Agent SDK | claude.ai | API with Agent Skills |
|---|---|---|---|---|
| The skill loads | yes | yes | yes (code execution on) | yes (`skill_id` in the container) |
| Subagents | yes | yes | unverified | unverified |
| Effort set per agent definition | yes | yes | unverified | unverified |
| Hooks | yes | yes | unverified | unverified |
| Statusline sees the usage meters | yes (Pro or Max sign-in) | unverified | unverified | unverified |
| Background tasks | yes | yes | unverified | unverified |

What the skill does on each: in Claude Code and the Agent SDK it runs every entry point. Where a
cell is unverified or no, it degrades as SKILL.md states: with no subagent tools it ends at the
tiered table and the ledger, printed in chat; with no `git` every row reads `unverified`; with no
meter it asks the user for the reading; with no hooks nothing is forced, and the doctrine stands
alone. Custom skills do not sync across surfaces, so each surface needs its own install.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
