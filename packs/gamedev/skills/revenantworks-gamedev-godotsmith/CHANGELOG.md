# Changelog — revenantworks-gamedev-godotsmith

## [1.0.1] — 2026-11-13

- reference updates from the 2026-11-09 review

## [1.0.0] — 2026-10-01

2026-11-09 (weekly observation review, slice b; observations 0478, 0484, 0486, 0493, 0494, 0501, 0502, 0506, 0516, 0520, 0524, 0548, 0549, 0554, 0565, 0599, 0608, 0617, 0621): `gut-traps.md` section 4 says `-gselect` is a substring match (keep the `.gd` suffix) and a one-script run with no summary is no run (the `ClassName.call` parse drop, reproduced on Godot 4.7.2); section 3 excuses a known-red base by test name, never by script, and checks a union-merged `.gd` file for duplicate functions. `gdscript-invariants.md` section 3 pairs an absence check over transformed output with a survivor line (the `\u0000` RegEx trap, reproduced), section 5 holds every clock a harness reads and makes a live-run fixture assert its premise, section 6 counts line endings as bytes, never with a shell grep. `determinism-and-state.md` rounds in the engine before formatting, runs a round trip's load in a fresh process, and gives every control a witness that the feature fired. `systems-and-export.md` keys a view's memory on the game, `lifecycle-and-safety.md` keeps helpers off virtual names, `project-hygiene.md` has editor code read `override.cfg` itself, `ci-guards.md` section 5 makes a local stand-in for a CI step run that step's other commands, `test-tiers.md` names the one-process proof a shard removes, and `probes.md` gains a bot-as-instrument check and sections 6 (a headless editor-side probe) and 7 (a real render on a hidden Windows desktop). SKILL.md unchanged.

2026-11-04 (a fresh review of `--parse-all`, reproduced on Godot 4.7.2): `--check-only` runs static initialisers, so `ci-guards.md` section 6 no longer says it runs none of the script and warns about a pull request's code; the import writes `.gd.uid` and `.import` files too, so run it on a clean checkout. A timeout now kills the whole process tree, since a killed `.cmd` shim left Godot holding the pipe and the check hung. A linked folder holding scripts fails the run. The controls go under `.godot/` by `res://`, the route real files take.

2026-11-03: `godot_check.py --parse-all` has Godot parse every `.gd` file in a repo with `--check-only`, not only the folders CI lints, because a broken helper outside them hid for several commits and a plugin that failed to parse loaded silently disabled. A positive control runs first: a broken script must be rejected and a valid one accepted, or the run is NOT-RUN. An unreadable folder, a file in no project, a stale `--exclude` and finding nothing to parse all fail it; each exclusion prints its reason. `ci-guards.md` section 6 holds the contract and a workflow shape. Fixed on the way: the script now starts Godot by the path it resolved, since Windows cannot start a `.cmd` shim by its bare name, which left the whole Check path failing with a traceback there. SKILL.md stays at its 3200-token row.

2026-10-23 (a game's test-speed fix round: an 11-hour serial suite, a 5-hour per-merge check; observations 0483, 0533, 0551, 0552, 0553, 0555, 0557, 0559): new `references/test-tiers.md` — measure first, three tiers (build, join on the merged head, gate), a short-run horizon with checkpoint pins, selection by changed symbol, a whole-plan budget that never drops edited work and prints what it left, one run per tree, a short-run mode refused by every gate tool, duplicate rows after a stack rewire, and a switch-retirement checklist. `ci-guards.md` §4 gains the source-scan and inherited short-run smells; `determinism-and-state.md` §3a the per-control pin copy, the rewire dedupe and retirement; `gate-doctrine.md` §3 says tier before cutting; `gut-traps.md` §3 never stashes in a shared checkout. Group H (H1-H7) added. SKILL.md gains one Load budget line and drops the stash sentence from Check step 5 (now in `gut-traps.md`): ≈3199 of 3200.

2026-10-22 (weekly observation review, observation 0447): `ci-guards.md` says code that talks to the operating system (process and pid calls, file locks, paths, line endings, cleanup on quit) needs each CI platform's proof before the land.

2026-10-21 (a recorded game playtest, seam with obsrunner's new `playtest` mode): `systems-and-export.md` section 6, a play log and engine errors: one autoload writing JSON Lines per launch (wall ms, `Time.get_ticks_msec()`, session, seg, tick, day, kind, detail), views and IO only with the state hash unchanged, the mark key, engine errors through a `Logger` registered with `OS.add_logger()` (threads and a Mutex, `push_error` routing, no `print`, backtraces need Always Track Call Stacks in a release export), dedupe on (file, line, code), and `godot.log` rotation (pick by span). `gdscript-invariants.md` section 8: draw polygons near the origin, since float32 triangulation fails at world coordinates in the thousands (1,236 of 92,241 pieces failed near 9,000, none made local). The Load budget line names the play log; SKILL.md stays at its 3200-token row (≈3200).

2026-10-20 (review RV-SKILLS-WF F15): SKILL.md is back under its 3200-token row (≈3198): Entry — Gate keeps the CI-time rule in one line and its detail moved to `gate-doctrine.md` §3 with L1's worked +9 example; no rule dropped.

2026-10-20 (observation 0472): the Gate entry fits CI wall time to the step's real cost driver from the CI API's step times, never by test count when one class dominates, and raises a timeout inside the land's own commit past 80% of the projection.

2026-10-17 (eval rerun, U41): the description names a one-file run that ran the whole suite, and the load list gives the single-script form (`-gconfig= -gtest=`, then `Scripts` must read 1); case `behaviour-single-script-gconfig` had loaded nothing.

2026-10-16 (dash triage S1): ships one declared stdlib script, `scripts/godot_check.py`: the headless import, gdtoolkit's lint when installed (NOT-RUN otherwise, never a pass), then GUT or one `--script` headless with no window; engine error markers are read before the summary; scripts, tests and failures print as three numbers against `--expect-scripts` and `--expect-tests` with the slack, `--repeat K` prints each run, exit 0 only when all match. Check steps 1 and 3, the Load budget, `gut-traps.md` section 3 and the README name it; eval case G15; tests in `scripts/test_godot_check.py`.

2026-10-16 (full observation review, U21): `gut-traps.md` section 4, a shared `user://` across worktrees voids a parallel run (observation 0438); `ci-guards.md` section 5, the local CI counts only on the pushed head and through the stamp (observation 0433).

2026-10-15 (lessons from a long Godot build): `determinism-and-state.md` gains section 3a (a control that restores the base pins makes a deferred re-pin sound; the join needs a per-control table; an incomplete control stops the re-pin) and the migration re-read; `gut-traps.md` gains the line-anchored summary parser and the `-gconfig=` single-script form; `perf-figures.md` section 9 (the timed window must contain the changed path); `project-hygiene.md` the `.import` churn rule (observations 0432, 0422, 0373, 0379, 0409, 0423). Evals G9-G14, `behaviour-single-script-gconfig`, `behaviour-deferred-repin`.

First public release. Godot 4.x project conventions, and the proof that a build is actually green.

Description cut to about 600 characters, main use case first (2026-10-08).

K8c fix round (2026-10-08): the two evalwright mentions in evals/RESULTS.md are marked as
retired (K7-3-22).

### What it does

- Rules on what a test run's numbers may mean: a green GUT or GDScript run is a claim about the
  instrument, so a script that failed to parse, a dropped test file or a drifted count is found,
  not trusted. A brief's stated test delta is counted against its numbered test list before the
  build (observation 0339; 2026-10-08, test phase).
- Ten laws in the body: five about proof (green is an instrument claim, the coverage population is
  everything that runs the code, exact assertions over floors, red stays red, a machine closes only
  a machine gate) and five about how the code is written (parse is not run, signals up and calls
  down with one owner, compose over deep inheritance, deterministic code owns its randomness and
  serialisation, a structural claim is enforced or it is decoration).
- Proves simulation and balance rules: units, claims, fallbacks, unlock arms, tuning sweeps and
  converters.
- Writes finished assets into a project: the audio import keys soundsmith names and the texture and
  project settings pixelsmith's render precondition needs (integer zoom, nearest filtering), then
  reads them back, imports and guards them.

### Entry points

- `check` — an audit of whether a run's result can be believed: population, instruments, drift
  against the repo's own guards and docs.
- `guard` — CI assertions written or fixed, with the reason each one fails.
- `gate` — a ruling on whether a milestone gate may close, and which half a machine may close at all.
- `review` — code read against the convention files, findings ranked by blast radius; a design or
  balance rule read against the design reference.
- `intake` — asset import settings and the pixel-art render precondition written, read back,
  imported and guarded.

### References

- GUT traps, CI guard shapes with worked bash, gate doctrine (two kinds of gate, four verdicts,
  populations, attribution), performance figures (cold and warm calls, interleaved A/B, headroom,
  frame figures) and headless probe conventions.
- Convention files: GDScript invariants, structure and wiring, lifecycle and safety (freeing, await
  validity, threads), determinism and state (randomness, save formats, state hashing), project
  hygiene (imports, `.uid` files, naming, the engine-upgrade rule, CI, asset intake), design and
  balance; systems and export (save files written safely and migrated, state machine transitions,
  when an event bus fits, C# signals, the export pipeline and its credentials) (K4 C6, 2026-10-08).
- `SOURCES.md`: the parity register of the public Godot skill sets, with attribution and licences.

### Safety rules

- Never writes gameplay code, and never makes a red build green by deleting or softening a check.
- Whether a game is fun stays a judgment gate a person closes.
- With no shell, every check degrades to a read of committed logs and config, and says so.

### Integrations

- Ships no code. Runs the project's own import, test and lint commands where a shell exists, or an
  adopted runner (godot-skill `run_tests.py`, godot-mcp) whose JSON it still checks.
- pixelsmith and soundsmith decide; godotsmith writes their settings into the project. A hook that
  enforces one of its rules is placed by gatewarden. Engine API reference stays with the Godot docs.

### Evals

- 32 trigger queries (16 should / 16 should-not), 42 assertion cases and native `claude plugin eval`
  cases.
