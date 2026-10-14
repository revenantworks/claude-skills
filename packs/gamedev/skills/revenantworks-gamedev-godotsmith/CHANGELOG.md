# Changelog — revenantworks-gamedev-godotsmith

## [1.0.0] — 2026-10-01

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
