# revenantworks-foundation-landwright

Owns the last mile of finished work: from committed local work to a merged pull request with a
green run on main. It also checks a free Godot addon before a release. Built because the landing
flow had no owner: gatewarden holds the push and CI hooks, handoffwright commits and pauses,
dispatchwright's controller lands units, and commscribe writes release notes, but no skill ran the
whole land in order.

What separates it from a commit-push-PR command:

- **Local CI is the verdict.** The repo's own CI steps run on the exact commit before anything
  leaves the machine, stamped through gatewarden's `ci_stamp` when installed. A skipped step or a
  missing tool is not a pass.
- **The push intent is its own call.** The commit count and head sha are recorded before the push,
  never on the same line as a commit.
- **Checks are read row by row, then merged in the next call.** Never chained, never a `--watch`
  exit code.
- **The run on main is read.** A red run is reported at once and enters a fixer loop with a
  three-round limit.
- **The owner decides what is irreversible or public.** Force pushes, CI changes, public repos,
  tags, releases and listings stop and ask.
- **Addon ship checks.** Licence and NOTICE inside the addon folder, a SUPPORT and SECURITY policy
  that promises no reply or fix time, `plugin.cfg` metadata and a zip that carries the folder alone.

**Workflow:** Sync in → Local CI (stamped) → Intent → Push branch → PR → Read checks → Merge →
Read main

## Package contents

```
revenantworks-foundation-landwright/
├── SKILL.md                      # modes, the eight land steps, stops, rules, report
├── README.md · LICENSE · NOTICE · CHANGELOG.md · SOURCES.md (sources + dated parity register)
├── volatile.json                 # SOURCES.md, calendar, 90 days
├── references/
│   ├── land-procedure.md         # commands per step, CI step list, merge method, account switch, [skip ci], red run
│   ├── addon-ship.md             # Godot addon release checks, tag and release with the owner's go
│   └── pack.md                   # generated pack manifest
└── evals/                        # trigger-evals, test-cases, RESULTS, native case folders
```

## Install

Part of the `foundation` pack: `/plugin install foundation@revenantworks`. Say `/rw-landwright`
or "land it".

## Dependencies

git (required). The GitHub CLI `gh` for the PR, checks, merge and run-on-main steps; without it a
land stops at the pushed branch. gatewarden's `ci_stamp` and `push_gate` hooks are optional; when
absent the local verdict is the run's own exit code, written in the report.

## Licence

Apache-2.0 (LICENSE, NOTICE).
