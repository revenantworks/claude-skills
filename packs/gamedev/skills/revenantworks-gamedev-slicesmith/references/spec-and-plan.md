# Spec and plan — weight, templates, slice sizing

Read by `spec` and `plan`. Templates are shapes, not quotas: drop a section that has nothing in it.

## Contents

- Weight classes
- The spec
- Spikes
- The plan
- Where the files live

## Weight classes

| Weight | Signals | What runs |
|---|---|---|
| **Spike** | One file, one behaviour, the diff fits in a sentence | One slice; no spec, no plan |
| **Bounded** | One system, a few files, no new boundary | A short spec, a plan of 2–6 slices |
| **Architectural** | A new boundary, a save or network format, a milestone others build on | Full spec, spikes first, plan with checkpoints, `exit` at the end |

Announce the weight. A later answer may move it heavier, never lighter.

## The spec

Read the code before writing a line of it. Start with an **Assumptions** block — "Assumptions
I am making; correct me now" — and turn every vague ask into a measurable criterion.

```markdown
# Spec — <title>

Weight: <Bounded|Architectural> · Status: draft — awaiting approval

## Outcome
<what a player can do or see afterwards, one paragraph>

## Proof (S1)
<the one thing that becomes true, and how someone who did not write it checks it>
e.g. "A save from build 41 loads in build 42 with every unit in place — `SaveCompatTest` loads
the committed fixture `saves/b41.json` and compares the state hash."

## Contract
- Inputs, outputs, save or network format, failure modes, the public API other code calls

## Boundaries
- Always: <rules the code must hold, e.g. sim code never touches the scene tree>
- Ask first: <changes that need the user, e.g. a save format version bump>
- Never: <e.g. global RNG on a deterministic path>

## Test seams
<where tests attach — agreed with the user before any test is written>

## Out of scope
- <what this work will not do>

## Assumptions
- <each, marked Said / Read / Assumed>
```

A grill record (`GRILL-<slug>.md`) is read as the spec's source: its Settled rows fill
Contract and Boundaries, its Done means fills Proof, and its `[?]` items stay open questions.

Save the spec, then **end the turn**. Approval is an explicit yes on the file.

## Spikes

A spike answers one load-bearing unknown before the plan depends on it. It runs the real
thing: a real export, an executed binary, a real device. Grade its answer **A** (observed) or
**A-by-inference** (read from docs or source); only A may carry the architecture. Record the
access pattern it modelled; if the real code later reads, writes or locks differently, the spike
is re-run before that slice is called verified.

## The plan

Read-only: the plan step changes no code. Order: spikes, then slices by dependency, then risk
(riskiest first), with the boring boundary before the gameplay and the renderer last.

```markdown
# Plan — <title>

Spec: <path> · Slices: <n> · Checkpoints after: <ids>

| # | Player-visible change | Failing test first | Verify command | Expected line | Files | Size |
|---|---|---|---|---|---|---|
| S0 | Spike — save file held open by the reader | — | `godot --headless --export-release "Linux" build/` then run it | `[S0] MOVE OK` | — | S |
| 1 | One unit moves one tile on command | `Unit_moves_one_tile_on_move_command` | `dotnet test --filter Unit_moves` | `Passed! - Failed: 0, Passed: 1` | `src/Sim/Unit.cs` | S |

## Interfaces
- Slice 1 produces `Unit.MoveTo(Vector2I)`; slice 2 consumes it.

## Global constraints
- Zero warnings · deterministic sim · no engine types under `src/Sim/`

## Review focus
- <failure modes no planned test covers>
```

Sizes: XS (one function), S (one file plus test), M (a few files), L (split it). An L is never
planned; split it until each slice fits one context. A checkpoint every two or three slices
runs the full ladder and stops for the user.

Never overwrite an unfinished plan: append a dated revision section instead.

## Where the files live

The repo's own convention wins (a `docs/` work folder, milestone files). With none:
`SPEC-<slug>.md`, `PLAN-<slug>.md` and `RUN-LOG.md` at the project root.
