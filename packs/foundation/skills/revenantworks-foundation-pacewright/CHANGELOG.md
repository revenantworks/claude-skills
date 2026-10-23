# Changelog — revenantworks-foundation-pacewright

## [1.0.0] — 2026-10-01

2026-10-20 (review RV-SKILLS2-WF F2): `modes.md`'s busy-engines row counts leaf engines: an engine with an engine below it (ci_local over its Godot shards) counts none itself, the engines under it one each, and a headless Godot always counts, so a 6-shard walk is 6, as dispatchwright's `rig_gate.py` now reads it.

2026-10-20 (review RV-SKILLS-WF F13, F14, F20): `plan-profiles.md`'s turbo row reads rig-aware (writers 6, all units 12, heavy launches through the rig gate) where it still said no lane cap; eval Case 10 is rewritten to the rig-aware turbo (the entry question, the writer's refusals, the two caps, the gate, a stall or `TIMEOUT` that does not escalate) and its provenance re-anchored. `modes.md` § Turbo names the gate's 6-second budget and the 10 s hook timeout, says a failed process listing is not measured and both machine signals unmeasured refuse, counts an engine once, counts verified unlanded branches only, passes a join or land at the WIP limit and a red land's fixer at the red bound, and says how to apply the bounds by hand without dispatchwright's gate (the compatibility field names the gate as optional); the Stop-launching line bounds busy engines at B - 2 like the table.

2026-10-20 (review RV-SKILLS-WF F10, F16): the budget writer drops a kept `parallel_ceiling` when a write enters turbo with no `--parallel` (a pace `--parallel 2` had capped the documented `--mode turbo --ttl 2h` at 6, and no command cleared it), keeps the user's own lower number on a turbo renewal, and refuses a turbo `--parallel` above 6 (the answer is rig-aware or a lower number, n <= 6). Selftest R9-R10 (red first: 2 named failures) and a new negative control.

2026-10-20 (owner ruling "adopt the rig gate" and the owner's order of 02:00Z, observation 0470): `modes.md` § Turbo is TURBO-ADV's rig-aware turbo. Turbo lifts the spend throttle, never a machine limit; the entry question is "rig-aware (pick) or a lower number", never no cap; writers stay at 6, all units at 12, and each heavy launch passes dispatchwright's rig gate (busy engines, CPU, check-queue wait, land state, unlanded WIP, top tier); a stall behind a closed gate or a `TIMEOUT` never escalates; renewal is a 2-hour check through the writer; it drops to normal after two 0-landed checks. Kept because they are stricter: the four launch gates (gate 3 now measured as WIP), the derived heavy-lane cap and the 4-suite ceiling, the 5-hour 85% stop and the baseline-rate drop. Overnight: never turbo unless the user explicitly orders a turbo night (`--night-order`), then under the rig gate with Overnight's conduct. New section "The spend target (any mode)": every 2-hour check prints the needed rate and the lane count, adds lanes in reset-eve's order within the rig gate, never padding work. `top` switch opens only on the user's quoted word. SKILL.md's mode lines say the same, slimmed to stay inside its 3600-token budget.

2026-10-20 (owner ruling "adopt the rig gate", observation 0470; reverses the 2026-10-16 no-cap ruling): the rig's budget writer `dispatch_budget_write.py` refuses `--parallel none` in every mode (rig-aware turbo writes no number), a turbo ttl over 2 h, a turbo file written inside Overnight or expiring past the next 22:00 user-local unless `--night-order "<the user's words>"` records a turbo night, and a turbo renewal without `--landed N` and a reading under 15 minutes old; two renewals in a row with 0 landed write normal instead. `top_tier_open` is false unless `--top-open --owner-word "<quote>"`; keys outside the schema are dropped and named; a stop band outside 50-95 or a slow band above the stop band is refused (`--stop-band`, `--slow-band`); every file carries `"writer"` and `content_sha256`. Selftest R1-R8 with a control each (red first on the old writer: 18 named failures); three new negative controls.

2026-10-16 (owner eval run, U38): trigger row 1 names the planned work; a bare "this" drew a clarifying question and no load.

2026-10-16 (thread sweep, U28 and U35): the suite ceiling in modes.md is now CPU-gated (start below 2, else under the cap while CPU is under its target, default 75%) with the cap read from ~/.dispatch/suite-cap.json; a wrapper and its suite share one slot; runs log to ~/.dispatch/suite-perf.jsonl for `suite_slot.py report`.

2026-10-16 (owner ruling "both" on observation 0446): beside the derived machine cap, a fixed ceiling of 4 suite processes machine-wide across every session and thread (the stricter holds), each process counted, every background suite at below-normal priority with no window, through dispatchwright's `scripts/suite_slot.py` where installed (`modes.md`, Turbo).

2026-10-16: turbo's no lane cap counts lanes, not machine load (owner ruling, after 8 concurrent local test suites on a 16-thread machine held the CPU at 97% and stretched a 45-minute land test run past 1 h 40 min). Lanes split into light (design, briefs, docs, reviews that re-run a few scripts: no cap) and CPU-heavy local work (full test suites, builds, renders, measure runs: a machine cap). The cap is derived: floor(logical threads ÷ threads per heavy lane), the latter from one measured heavy run as the new measured overlay key `turbo.heavy_lane_threads`, default 5 (16 threads gave 3); the load probe re-reads it before each heavy launch and counts every heavy process on the machine, whoever started it (two controllers each at 3 had put 6 suites on 16 threads). The land test run goes first, and finished, reviewed rows land in batches under one land run. Gates and stop bands unchanged. Case 10 gains T3 and T4.

2026-10-16: turbo has no lane cap by default (owner ruling). On entry the controller asks once, "No cap (pick) or a number?", and records the answer in the budget file (`parallel_ceiling` null = no cap, turbo only). Every launch still passes the four launch gates (real work only, disjoint file sets, can land, tier from the table), the stop bands and a machine-load probe before heavy local runs; turbo still starts only on the user's word. Case 10 extended.

2026-10-13: `context` entry — the in-session context budget: compact, clear or neither (never while units or dispatched rows run, never mid-step), what to write first, and a per-use-case auto-compact table whose figures are the user's own overlay keys (`context.autocompact.<use_case>`); trigger rows #32–#35, Case 21 and two native cases added.

2026-10-09: work-day mode — overnight conduct between check-ins, questions queued to a check-in file with recommended answers, asked one at a time at user-set check-ins (default 12:00 and 17:00, overlay `workday.checkins`); trigger rows #30–#31, Case 20 and a behaviour case added.

2026-10-08 (K8 fix round): whether a new model should take a job type is scoutwright's `fit` (trigger row #11 is now its near-miss, #29 the baseline pair); compatibility names the run notes as the controller's; the bare reply names `spend`, with `dashboard` folded under it; calibration tables labelled examples (audit K7-2-10, -14, -15, -16, -17).

2026-10-08: description cut to about 600 characters, main use case first; trigger phrases and seams kept (routing proof: K9 evals).

First public release. Paces a Claude subscription's usage across sessions, runs and projects. It
never runs the work: it says what may launch now.

### What it does

- Reads the 5-hour, weekly, per-model and CI-minutes meters, from a statusline meter file or one
  line asked of the owner.
- Spend modes on one shared base: normal, pace, turbo, overnight, work day, owner-away and
  reset-eve, each differing only in its throttle. Turbo starts only on the owner's word.
- Work day: the user is busy but around. Overnight conduct runs between check-ins (no blocking
  question; launch first; questions queued with recommended answers); at user-set local times,
  default 12:00 and 17:00, the controller asks the queued questions one at a time, lists the
  user's tasks and gives a three-line status, while the work keeps running.
- Context: says whether to `/compact`, `/clear` or neither from the context-used figure and what
  still runs in the session, lists what to write to disk first, and tunes auto-compact per use
  case from the user's own settings (no figure ships). Writes nothing.
- Fits a list of planned units or sessions into what the windows have left, with a margin, and
  re-cuts waves that do not fit.
- A percent becomes tokens only through measured calibration; with no measured figure the fit says
  `unfitted`.
- Usage reconciliation (UBA): each reading is compared with the known spend, and launches brake when
  points go missing.
- A weekly budget per meter (Claude windows, the top-model allowance, CI minutes per repo, the
  GitHub API limit, any paid API), written to a budget decision file that a fan-out reads as data.
- Plan profiles: every plan-dependent number in one data file, so a plan change is a data edit.
- Admits a new model for a job type only through a measured baseline.
- Lane rates and tokens per point are dated data per tier and mix, calibrated from owner readings
  at least 1.5 hours apart; a top-tier model's cost per point is measured when it runs alone, and
  stated as an assumption with its source until then.
- Reset-eve turns on when the projected close misses the target, treats under-pace as a deficit,
  prints the lane count at every check and reads the owner's own target from the budget file.
- Fill and catch-up lanes serve planned rows only; spend never creates a row.
- Overnight entry is a gate: every queued command on the allow list and liveness watched from
  outside the session; no blocking question while a row is launchable.
- Budget file stamps come from the clock in the writing command, never typed.

### Entry points

- `check` (with `--dry`, writes nothing), `mode <name>`, `fit`, `uba`, `baseline`, `spend` (tokens by skill, subagent and
  starting prompt, read from local transcripts; counts only), `dashboard`,
  `refresh` (re-verifies the plan profiles against the provider's pages).

### Safety rules

- Writes three files only: the budget decision file, the calibration file and a local overlay.
- Never reasons a number into being; every reading is data, not instructions. Ships no code.

### Integrations

- dispatchwright reads the budget decision file when present and unexpired; neither skill calls the
  other. skillwright or promptwright `slim` sizes one artifact's cost; rigwright places the statusline that writes the
  meter file; agentwright wraps a scheduled pace check.
- Also ships as a featured one-skill plugin; install the pack or the featured plugin, not both.
- Optional mods: `vigil` (status-line meters, the meter-file fallback writer) and `shroud`; they
  never block.
