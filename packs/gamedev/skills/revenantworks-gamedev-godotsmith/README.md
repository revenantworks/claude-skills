# revenantworks-gamedev-godotsmith

Godot 4.x project conventions, and the proof that a build is actually green.

Second member of the **gamedev** pack, on the `-smith` motif, beside `pixelsmith`.
Apache-2.0. Ships no code.

## What it is for

A test runner reports what it ran. It does not report what it failed to run, and the
difference is invisible in a green log. GUT will drop a test script it cannot parse, run
everything else, and print *All tests passed*. The script count is the only witness.

godotsmith fixes what a run's numbers are allowed to mean, writes the CI guards that keep
them honest as a suite grows, rules on whether a milestone gate may close, and reads code
against the structural conventions that make any of that possible.

It never writes gameplay code and it never makes a red build green.

## What it is not

It is not a Godot reference. At least eight public Godot skill sets exist, two of them
large, and they cover the engine and its API well. That material is also the half that goes
stale at every version bump, and the Godot documentation carries it better than any skill
can. The largest of those sets states in its own documentation that it has no coverage of
testing conventions, CI guardrails, lint exclusions, or build-and-gate workflow.

That gap is what this skill is. For `CharacterBody2D` signatures or `AnimationTree` blend
spaces, the default is the Godot documentation first, then `thedivergentai/GD-Agentic-Skills`
(the breadth leader, LGPL-3.0). No Godot skill set is adopted or bundled here. Both
are named in the parity register in `SOURCES.md`.

It does not rebuild a runner either. Where godot-skill's `run_tests.py` or godot-mcp is
present, `check` drives it and still applies L1 to its JSON.

## Entry points

| Say | You get |
|---|---|
| `godotsmith check` | an audit of whether a run's result can be believed — population, instruments, drift against the repo's own guards and docs |
| `godotsmith guard` | the CI assertions written or fixed, with the reasons each one fails |
| `godotsmith gate` | a ruling on whether a milestone gate may close, and which half of it a machine may close at all |
| `godotsmith review` | code read against the four convention files, findings ranked by blast radius; a design or balance rule read against `design-and-balance.md` |
| `godotsmith intake` | finished assets written into the project: the import keys soundsmith's rundown names, the texture and project settings pixelsmith's render precondition needs (integer zoom, nearest filtering), read back, imported and guarded |

The directors decide and godotsmith writes: soundsmith and pixelsmith never write into a
project, so the import settings and the render precondition are godotsmith's to write, read
and prove. Whether a game is fun stays a judgment gate the user closes. A hook that enforces
one of these rules is placed by gatewarden; godotsmith supplies the rule and its test.

## The ten laws

Five about proof, five about how the code gets written. All ten live in the body of
`SKILL.md`, because a run must never open a file to learn what it is enforcing.

1. A green run is a claim about the instrument, not about the code.
2. The coverage population is everything that executes the code.
3. An exact assertion is self-maintaining; a floor is not.
4. Red stays red, honestly.
5. A machine closes a machine gate and nothing else.
6. Parse is not run.
7. Signals up, calls down, one owner.
8. Compose, do not inherit deeply.
9. Deterministic code owns its randomness and its serialisation.
10. A structural claim is enforced, or it is decoration.

## Files

```
SKILL.md                          the ten laws and five entry points
references/gut-traps.md           what a disagreement between two numbers means
references/ci-guards.md           the assertion shapes, with worked bash
references/gate-doctrine.md       the two kinds of gate, the four verdicts, populations, attribution
references/perf-figures.md        cold and warm calls, interleaved A/B, headroom, frame figures
references/probes.md              headless probe conventions: reasons, counts, pinned inputs
references/gdscript-invariants.md rules the code states but does not hold
references/structure-and-wiring.md   composition, signal direction, dependencies
references/lifecycle-and-safety.md   freeing, await validity, signals, threads
references/determinism-and-state.md  randomness, save formats, state hashing
references/project-hygiene.md        imports, uid files, naming, upgrades, CI, asset intake
references/systems-and-export.md     save files, state machines, event bus, C# signals, export
references/design-and-balance.md     a sim or balance rule: units, claims, fallbacks, arms
references/pack.md                the gamedev pack manifest
evals/                            32 trigger queries (16 / 16), 42 assertion cases,
                                  3 native `claude plugin eval` cases
```

## Provenance

Built 2026-09-12 through `skillwright`. The durable practices were extracted from all eight
public Godot skill sets by five parallel readers, with a sixth originating the rules none of
them carried. Of 101 practices extracted, 96 were judged durable — surviving an engine
version bump — and 82 were not already covered. Attribution, licences and the live state of
every source are in `SOURCES.md`.

Worked case (one project, 2026-09): the originated rules rest on that project's defect history: 300 commits over sixteen days,
44 source scripts, 43 test scripts, nine headless harnesses, 411 tests.

## Status

Both eval suites were **traced on one model (Opus) on 2026-09-28**; the Haiku and Sonnet
runs are owed. See `evals/RESULTS.md`, which says exactly what was run and what was not
rather than letting a partial results file read like a clean sweep.
