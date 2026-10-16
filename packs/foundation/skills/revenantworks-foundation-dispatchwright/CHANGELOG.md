# Changelog — revenantworks-foundation-dispatchwright

## [1.0.0] — 2026-10-01

2026-10-16 (weekly observation review): unit briefs gain a mandatory "Never read" field for protected paths and the hard rules of every store a question leads to; a worktree keeps its repo's folder name and a "fails on base too" check runs where the base normally runs; hash-pinned fixtures get `-text` in `.gitattributes`; an owner budget is carried "in total" with its split; a gate that needs another task's secret is reported pending with its owner; a rename sweep keeps record lines and rewrites, never swaps, where the successor works differently (`unit-brief-template.md`). The ledger header records the controller session id that owns the run's actuals, and a row write is verified before its launch, never batched with it (`ledger-schema.md`) (observations 0395, 0396, 0397, 0400, 0408, 0411, 0424, 0425).

2026-10-16: the wave cap's turbo exception (owner ruling: turbo runs with no lane cap unless the user names one). A live budget file with `"mode": "turbo"` and `"parallel_ceiling": null` lifts the 6-unit cap; every other launch gate still applies (SKILL.md section 6). The ledger guard reads it the same way: no cap for turbo plus null while unexpired; 6 when the file is missing, expired, malformed, or null outside turbo; a numeric ceiling unchanged and still clamped at 12. Guard self-tests: 13 cap cases and 4 exit-code cases, with the old cap as positive control.

2026-10-15 (lessons from a long Godot build): land cadence is per arc for pin-moving lanes, with one pin-arc join row, and view lanes land freely (SKILL.md section 3; `unit-brief-template.md`); build briefs say narrow runs while building, the full suite once, counts files the controller's, and a perf window; a refused report file falls back to the final message; per-unit reviews drop a tier when the meter is tight (`tier-routing.md`); briefs written ahead get a join check before launch (observations 0432, 0417, 0422, 0379). Eval cases 30-31 and `behaviour-pin-arc-cadence`.

2026-10-08 (K8 fix round): the ledger guard enforces the documented stop band (95% default, or the budget file's tighter band) on both the 5-hour and weekly windows, and writes the ledger atomically; the gate's built-in lane rate is labelled a default, not a measurement (audit K7-2-22, -23, -24). The meter-floor rule reads in room left; trigger rows #31 and #38 name their pacewright and scoutwright boundaries (K7-2-11, -12, -25, -26).

2026-10-08: description cut to about 600 characters, main use case first; trigger phrases and seams kept (routing proof: K9 evals).

2026-10-08: tier-routing.md and the ledger-schema example name Haiku 5.5 (`claude-haiku-5-5`, default effort `medium`); lineup rows and stamp only.

First public release. Runs a session's fan-out: turns one large request into tiered, recoverable
units, dispatches them, and reconciles them against the repo, never against an agent's own report.

### What it does

- Shape check first: says so and stops when a request is not a real fan-out.
- Decomposes into units small enough to finish, and tiers each one (model, effort, surface) from its
  own tier table, written into the ledger before the unit launches. It never invents a tier.
- Nothing launches before the table and the go: one table per wave (unit, class, model, effort,
  estimated tokens, estimated wall time, window), a meters line and one confirmation line.
- Reads every meter its units spend (the Claude windows, CI minutes, the GitHub API limit, any paid
  API) as data, takes the cheapest route on each, re-reads them at each land and wave, and brakes
  below the owner's line.
- Durability contract: a local commit after every finished piece, controller-batched pushes to
  origin only, a ledger row at dispatch, and a row reads `landed locally` until its batch is on the
  remote.
- Wave caps: six concurrent units, two nesting levels, a worktree for every writer, one writer per
  repo, a stagger across launch, and a usage-window check before a top-tier wave.
- Escalation within a tier before jumping a tier.
- A two-stage review per writer unit on its own worktree diff — spec conformance first, then
  quality — and a decision map (decided, open, what blocks what) for work longer than one
  session, both in `references/unit-review.md`.
- Seam: a new model's per-class fit is scoutwright's `fit`; a tier change still goes only through
  this skill's `refresh`.
- Reconcile checks every row against `git rev-parse origin/main`; without git a row reads
  unverified, never done.
- Resume reads origin and the ledger first and never redoes landed work.
- An excuses and red-flags table in `anti-patterns.md`, read before every Reconcile report, naming
  the reasons a unit gets rounded up to done.
- The go is asked under the plan table in the same reply; a file path is never what is approved.
- Every blocking question waits until each launchable row has launched; overnight, questions go to
  a morning file. A pace-motivated launch names the planned row it serves; spend never creates a
  row. Unattended runs list each unit's commands for the allow list and watch liveness from
  something a permission prompt cannot block.
- Times in the ledger and the budget file come from the clock in the writing command, never typed.
- Owner answers become ruling rows with an apply step on the brief lines they change; wave
  triggers are checked against the brief order; cited bases are checked by ancestry, not
  existence; a brief's stated test delta must equal its numbered test list.
- A check that fails on any run of the tree is red; a step the local runner skips makes the local
  verdict partial. A row that moves a path a live schedule reads waits for the schedule swap.
- Units commit before the last 10 calls of their cap and verify an edit landed before a commit
  message names it. Tracked run records are never edited while that repo's local CI runs.

### Entry points

- `plan`, `dispatch`, `resume`, `audit` (read-only reconcile), `refresh` (re-syncs the tier table).

### References

- Ledger schema, unit brief template, the tier table and effort ladder, meters and the fallback
  window fit, 13 anti-patterns, and the doctrine cases behind the rules.

### Safety rules

- A unit's own account of what it did is never the proof.
- Without subagent tools a run ends at the tiered plan and the ledger; without a meter reading it
  asks the owner. Ships no code.

### Integrations

- Pacing is pacewright's: a plan reads its budget decision file as data when fresh, and either skill
  works with the other uninstalled.
- The trigger hook is rigwright's placement call; unattended runs are agentwright's; a handoff
  outside an active fan-out is handoffwright's.
- Two optional forcing hooks are kept as repo infrastructure for a rig to install; nothing depends
  on them. The ledger guard reads the first table whose header names model, effort and surface,
  so header-block tables above the rows are allowed, and a refusal names the table it read.
- Optional mods: `dash` (ledger cost sidecar, task pane) and `privacy`; they never block.
