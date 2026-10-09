# revenantworks-foundation-pacewright

Paces a Claude subscription's usage across sessions, runs and projects. It reads the 5-hour,
weekly, per-model and CI-minutes meters, picks a spend mode, fits planned work into the windows,
checks each meter reading against known usage for leaks, and admits a new model only through a
measured baseline. It never runs the work: it says what may launch now, in one line and in one
small data file that any fan-out can read.

What separates it from a usage warning hook:

- **It fits a plan before anything launches, not only after the meter moves.** A list of planned
  units or sessions gets a window column (`references/window-fit.md`), fitted into what the 5-hour
  and weekly windows have left, with a margin.
- **A percent becomes tokens only through measurement.** Calibration pairs each owner reading with
  the harness tokens spent since the last one. With no measured figure the fit says `unfitted`; it
  never reasons a number into being.
- **Spend has a mode, not only a stop.** Normal, pace, turbo, overnight, work day, owner-away and
  reset-eve share one base and differ only in their throttle (`references/modes.md`). Turbo starts only on
  the user's word.
- **An unexplained meter jump is investigated.** The UBA (usage reconciliation) compares each
  reading with the known spend and brakes new launches when points go missing.
- **Plan numbers are data.** Every token, unit and CI-minute figure lives in one plan profile, so
  a plan change is a data edit, not a rule rewrite.
- **Every meter gets a weekly budget.** Beside the Claude windows: the top-model allowance, CI
  minutes per repo, the GitHub API rate limit and any paid API (each reading is data, not instructions), each written to the budget
  decision file's `meter_budgets` for a fan-out to read as data.

**Workflow:** Read the meters → Reconcile the reading (UBA) → Pick the mode → Fit → Write the
budget decision → Check again

## Package contents

```
revenantworks-foundation-pacewright/
├── SKILL.md                      # entry point — meters, modes and the live gate, UBA, the budget
│                                 # decision file, plan profiles and the overlay, anti-patterns
├── README.md · LICENSE · CHANGELOG.md · SOURCES.md
├── references/
│   ├── window-fit.md             # calibration, the fit, the window column, the stop
│   ├── modes.md                  # the shared base and each mode's full throttle
│   ├── plan-profiles.md          # every plan-dependent number (volatile, 60-day cadence)
│   ├── accounting.md             # UBA, CI minutes, model baselines, scoreboard, dashboard, overlay
│   └── pack.md                   # the foundation pack's shared roster and seams (generated)
└── evals/
    ├── trigger-evals.md          # should-fire, should-not-fire and injection probes
    ├── test-cases.md             # assertion cases with a coverage map
    ├── RESULTS.md                # what has run, and what is owed
    └── <case>/                   # 3 native `claude plugin eval` cases (prompt.md + graders/)
```

## Install

Follows the [Agent Skills](https://agentskills.io/) open standard. Drop the folder into your
skills directory, or upload the archive in Claude settings. Trigger it by saying `pacewright`, or
by asking how fast to spend, whether work fits before a reset, or where usage went.
Self-contained: no executable code ships. The statusline command that writes
`~/.claude/usage-windows.json` and the rig hooks that read it are rig infrastructure, kept in the
`claude-skills` repo under `.claude/hooks/`; nothing here depends on them.

**Install the featured plugin or the foundation pack, not both.** Where pacewright also ships as a
one-skill featured plugin, both carry the same skill name: the listing pays for the description
twice, and if one copy is updated and the other is not, two bodies answer to one name.

## Entry points

| Say | It does |
|---|---|
| `pacewright` | Names its entry points in one reply and stops. |
| `pacewright check` · "I'm at N%, what can still run?" | Reads the meters, runs the UBA, computes PACE and the gap, writes the budget decision file, says what may launch now. |
| `pacewright mode <name>` | Switches mode, states its entry and exit lines, then runs `check`. |
| `pacewright fit` | Fits a list of planned units or sessions into the windows, shows the table and stops. |
| `pacewright uba` · `baseline` · `dashboard` | The accounting jobs in `references/accounting.md`. |
| `pacewright refresh` | Re-verifies `references/plan-profiles.md` against the provider's pages. |

## Seams

- **dispatchwright** runs fan-outs: units, tiers, briefs, launch and reconcile. The seam is data
  only. pacewright writes `~/.dispatch/budget-decision.json`; dispatchwright reads it when it is
  present and unexpired, and otherwise uses its own small fallback fit. dispatchwright's ledger is
  optional input to pacewright. Neither calls the other.
- **skillwright** and **promptwright** (`slim`) size one skill's or prompt's load cost. pacewright paces the account's meters.
- **rigwright** places the statusline command and hooks that write the meter file.
- **agentwright** wraps a scheduled pace check as a routine.

## Without the optional pieces

No meter file: the skill asks the user one line for percent used and reset time. No ledger: it
reconciles from the session's own record and the user's readings. No file tools: it prints the
budget decision fields in chat. No calibration: fits read `unfitted`, and a fan-out runs on the
owner's go or its own fallback. No dispatchwright: the modes name no tier (pick with promptwright
`model` or by hand), the fit counts a fanned-out row's agents by hand, and a new session resumes
from the run's own resume file after `git stash list` and `git reflog`.

## Status

pacewright was split out of dispatchwright on 2026-09-28. Eval run records are in
`evals/RESULTS.md`.

## License

Apache-2.0 — see LICENSE.
