# Changelog — revenantworks-gamedev-godotsmith

## [1.0.0] — 2026-10-01

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
