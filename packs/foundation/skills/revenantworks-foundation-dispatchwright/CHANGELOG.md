# Changelog — revenantworks-foundation-dispatchwright

## [1.0.0] — 2026-10-01

2026-10-22 (weekly observation review, slice 0447-0462): §7's stuck count is per row, whoever ran the check, so the controller stops hand-fixing at its second failed check too (0461); a PR this run did not open gets a fresh-context review unit before any merge (§7 and meters.md, Wave conduct; 0459). `unit-brief-template.md`: a `Tools you never call` field naming every `mcp__hearthbot__` tool, backed by `disallowedTools` in the tier agent definitions (0449); design and brief units take the decision log over the research and list where sources disagree (0460); code that talks to the operating system lands on every CI platform's proof (0447); one land is one suite slot, whatever wraps it (0448).

2026-10-22 (weekly observation review; observations 0463, 0529, 0532, 0536): the ledger guard reads `Ledger row <id>` first, with or without parentheses, so the brief's explicit id wins over a prose `You are unit U2.1`; a short id that is the hyphenated tail of exactly one row binds that row (`U2.1` binds `FIX1-U2.1`), and a no-row refusal names the rows that nearly match. `You are dispatched unit <id>` names a unit. A column headed `id` reads as `unit_id`, and a no-row refusal says when the table has neither column or the unit's own row is the wrong width. A unit id written in more than one row is warned with its line numbers, and a launch of that id is refused. `ledger-schema.md` says the same and gains a read-only research example row (0416). Guard selftest T20 (red first: 6 named failures).

2026-10-20 (review RV-SKILLS2-WF F2): `scripts/rig_gate.py` counts the leaf engines. It dropped every engine below another engine, so a ci_local walk that Popens `godot --headless` once per shard counted 1 for N Godots; now an engine with an engine below it counts none itself, the engines under it count one each, and a headless Godot always counts, even with an engine below it. Tests: rig_gate 41 -> 47 (`LeafEngines`, a ci_local parent with 1, 2 and 6 Godot shards; red first: 5 failing); the REAL_SHAPE listing still reads 4.

2026-10-20 (review RV-SKILLS2-WF F1): the ledger guard binds a launch to its row for any unit id shape (LAND31, JOIN-31, FIX-SW, HUT-F, RV-SKILLS-WF), not only an id of up to three letters and a digit, so `kind:`, `fixer-of:` and the read-only test reach the gate and the writer cap for this run's real ids. The id follows `You are unit <id>`, `Unit <id> of run <run>` or `(ledger row <id>)` and is looked up as a literal `unit_id` (never a prefix); an id-shaped token with no row is refused as before, and a lowercase word that is no row's id names no unit. `ledger-schema.md` states how a brief names its unit. Guard selftest T16-T19 (red first: 8 named failures).

2026-10-20 (review RV-SKILLS-WF F15, F18, F20): SKILL.md is back under its 5000-token row (≈4938): the standing go, the asking-the-user detail and the meters paragraph's detail moved to `meters.md` (Wave conduct), each rule kept with a pointer. §6 credits the rig gate to this skill's `scripts/rig_gate.py`, and the recovery fixer's row notes `fixer-of: <land>`; §7's stuck rule exempts a stall behind a closed rig gate or the check queue and a `TIMEOUT` verdict (the row requeues), and the call-count line names the 2x-estimate stuck rule. `ledger-schema.md` states the writer cap on writer launches only and the `kind:` and `fixer-of:` notes tokens.

2026-10-20 (review RV-SKILLS-WF F11, F12, F19): the hook controls no longer read live state. The ledger guard takes `--budget-file` and `--rig-gate` fixture paths on argv; every guard control names absent ones, the negatives add the documented windows fixture, and three new controls run a stamped turbo fixture against a passing, a refusing and a missing stub gate (`.claude/hooks/fixtures/rig-gate/`). `dispatch_gate.py`'s reset-eve line honours `--windows-file` and a new `--budget-file` (it read the live files, so its ordinary-prompt negatives failed for 48 h before every weekly reset), and its cap reads the rig-aware turbo as the guard does: 12 units and 6 writers for a stamped turbo file, its lower number as written, 6 unstamped; the no-lane-cap text is gone. Selftests: guard T15, gate F12 and F19 cases (red first: 4 named failures); controls red first 2 + 2.

2026-10-20 (review RV-SKILLS-WF, F1-F2, F4-F9, F16-F17): `scripts/rig_gate.py` answers inside a 6 s budget (the listing, CPU sample and git run at once, each timeout sized to fit); a listing that fails, exits non-zero, times out or comes back empty is "not measured", and a heavy launch with engines and CPU both unmeasured is refused. An engine counts once, as the process that is the engine: suite_slot waiters, cmd, Git Bash and MSYS `timeout` wrappers never count, a waiting slot record never counts, and the registry's running count is a floor. A running check counts once in the queue wait. The WIP bound counts verified branches only (a GREEN, not superseded queue verdict on the branch tip, or `wip.verified_file`), any branch name, and refuses builds only; `--kind join|land` passes at the limit, and `--fixer-of <land>` passes the red-verdict bound. The ledger guard keeps its whole run under 8 s (register it with a hook timeout of 10 s or more), hands the gate the row's `kind:` and `fixer-of:`, applies the writer cap to writer launches only, holds a stamped turbo's lower number as written (1..6), and refuses a top-tier launch outside dispatch mode unless the stamped file opens it. Tests: rig_gate 20 -> 41 (red first: 20 failing), guard selftest T9-T14 (red first: 14 named failures).

2026-10-20 (owner ruling "adopt the rig gate" and the owner's orders of 02:00Z and 02:20Z; TURBO-ADV, FINAL-ADV C15 and C18; observations 0464, 0465, 0470, 0471): SKILL.md §6 caps 6 writer units in every mode, turbo adding read-only lanes to 12 through the rig gate; recovery also covers a red land in flight; a standing go (the user's pre-approval of the next phase) advances on a recorded done-when; a slow-step log. §7: a join review may stand in for its rows' reviews when every line is read once by a skilled review; stuck (blocked, past 2x, or a second failed check) goes one effort step up unasked in any mode, Fable still on the user's word. `meters.md`: fill to the real count on reset eve only, within the rig gate; the slow-steps file. `tier-routing.md`: an escalation may propose the top tier, the user's word opens it. `unit-brief-template.md`: the brief is a file the unit re-reads after a reset and the launch prompt only points at it; results to the wave report as they arrive and each green piece committed at once; the repo's own worktree tool; count literals left to the join; queue the final check and exit where the repo has a queue; every foreground wait under `timeout`; a correction goes into the brief file.

2026-10-20 (owner ruling "adopt the rig gate", observation 0470; reverses the 2026-10-16 no-cap ruling): the ledger guard's `concurrent_cap()` never returns None. A turbo budget file stamped by `dispatch_budget_write.py` (writer id plus a matching content hash) gives 12 units in all; an unstamped or hand-edited turbo file gives 6. Writer rows stay at 6 in every mode. In stamped turbo every launch's row needs a numeric estimated-tokens cell (a base sha is refused), and every heavy launch (`lane: heavy`, a writer row with no lane cell, or a brief naming no unit) runs the new `scripts/rig_gate.py`; its refusal, absence or timeout refuses the launch. `checking` counts as open. A `fable*` agent type or model is refused in every mode unless the stamped file says `top_tier_open` with the user's quoted word and the unit's row says `owner-called`. New stdlib `scripts/rig_gate.py`: busy engines (B - 2, B = cores + 2; +2 for a self-hosted runner job), CPU under 85%, check-queue wait under 45 min and no hosted run in flight, no land walk and no red land or main, unlanded branches under 6; each signal read through an adapter with a documented file contract and reported "not measured" when its source is absent, never a crash. Tests: `scripts/test_rig_gate.py` (20, red first as a missing module); guard selftest T1-T8 (29 cases, red first: 16 named failures), the 2026-10-16 turbo cases rewritten to the new ruling, and a top-tier positive control. `ledger-schema.md` gains `checking`, the writer count, the turbo estimate and the `lane` cell.

2026-10-16 (thread sweep, U28 and U35): the ledger guard reads rows by writer and width, accepts `none` beside `—` as the read-only marker, treats `dispatched` and `committed` as the open states, and logs each launch in `~/.claude/dispatch-launches.json` so a second launch of a unit whose row was not rewritten is refused (observation 0425, B4). ledger-schema.md says the same.

2026-10-16 (thread sweep A22, A5): `scripts/suite_slot.py` counts a wrapper and its suite child as one slot. It now lists every process with its parent, and a suite process with a suite process among its ancestors (ci_stamp over ci_local, ci_local over unittest, through a plain shell too) shares that ancestor's slot; separate suites still each count, so a plain runner's N headless Godots use N. Owner rulings 2026-10-16 22:30Z-22:32Z ("raise the cap", "maybe just like 75% of CPU", "track any metric that would go into performance"): the hard cap is re-read on every poll from `~/.dispatch/suite-cap.json` (`cap` while `until` is unexpired, else 4); a suite is admitted below 2 running, or under the cap while the machine's CPU over 3 s is under `cpu_target` (default 75); each run appends a path-free row to `~/.dispatch/suite-perf.jsonl` (wait, run, exit, tests ran, CPU avg and peak, and through one windowless typeperf process disk, memory and processor-queue counters; null off Windows); new `suite_slot.py report` gives per cap and CPU target the runs and median wait_s, run_s, cpu_avg, disk_busy_avg, mem_avail_mb_min and seconds per test. Tests: 32 new cases (42 in all) (wrapper chains, a shell between, siblings, a parent loop, the listing parser; cap file incl. expired and malformed; CPU target; admission with a stubbed CPU reading; typeperf parsing and the rig summary from canned lines; the test counter; a perf row with no path separators; the report). `unit-brief-template.md` says the same. SKILL.md body trimmed under its 5000-token budget with no meaning change (five phrasings shortened).

2026-10-16 (owner ruling "both" on observation 0446): one machine-wide cap of 4 suite processes across every session and thread, each process counted (a runner that fans out N headless Godots uses N slots), and every background suite at below-normal priority with no window; it sits beside pacewright's derived machine cap (the stricter holds). New optional stdlib helper `scripts/suite_slot.py` waits for a slot and runs the suite that way; the brief template points at it. Tests: `scripts/test_suite_slot.py` (argument parsing and the suite count; no live process calls).

2026-10-16 (full observation review, U21): the brief template generates its local CI from the CI file and brackets a pinned host version (0367, 0368); a field for writes the classifier may refuse, with plugin refreshes as owner steps and an end-state check (0378, 0429); out-of-tree shared state and stopping background processes (0438, 0439); run-record moves are privacy-scanned (0434); generated artifacts are probed fresh (0393); the land order (0433). `ledger-schema.md`: `—` as the one read-only marker (0387), a distinct report path (0416), the open-status vocabulary and the row width (0437), hook-written run records out of a still-tree repo (0380), and the caps-file sentence corrected (0371). `tier-routing.md`: adversarial-input rows (0366), headless model trials (0390). Suites capped machine-wide apart from the unit cap, merge run first (owner ruling, 0446; the cap's number is the newer entry's).

2026-10-16: section 6 points at pacewright's turbo machine cap: under turbo's null ceiling, CPU-heavy local lanes keep the machine cap and the land run goes first. Observation citations in the body shortened to the `#NNNN` form to stay under the body budget.

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
