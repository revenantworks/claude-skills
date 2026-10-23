# Spec and plan — weight, templates, slice sizing

Read by `spec` and `plan`. Templates are shapes, not quotas: drop a section that has nothing in it.

## Contents

- Weight classes
- The spec
- Spikes
- The plan
- Stacked pin round: units that move determinism pins
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

A slice that rescales or regroups constants a save or migration depends on lists a migration
test in its row: a save from before the change, loaded under the new rules, asserting a relative
invariant (joints closed, distances from an anchor), not only that it loads. A migration that
applied one factor to everything is wrong once a later change scales only part of the world.

Never overwrite an unfinished plan: append a dated revision section instead.

## Stacked pin round: units that move determinism pins

A **pin** is a literal the suite compares a simulated run against: a trajectory hash, a
fingerprint, a state hash. A unit that moves pins costs a re-pin, a review, a platform measure
and a CI run. Paid once per unit, an arc of four units pays it four times, and each rebase onto
a moved main pays the re-pin again (one unit re-pinned 14 rows a second time after another unit
landed first). When every unit in the arc ships an `*_OFF` control, plan the arc as a **stack**:

1. **One integration branch per design arc.** Units build on it in dependency order.
2. **Every unit proves itself with all controls on.** With each control on, the suite equals the
   base pins, so the unit is green without a re-pin. A unit that cannot show that is not
   stackable (see below).
3. **Every unit gets its own fresh review** before the next stacks on it. The stack saves the
   re-pin, never the review.
4. **Re-pin once, at the join, as its own unit.** It measures with all controls off, writes an
   old -> new table per pin row, and attributes every moved row by switching one control at a
   time (godotsmith `determinism-and-state.md`, pin rounds). One platform measure, one land,
   one CI run. When the join points older control rows at the new stack, it deletes any row
   whose setup and table now equal the stack row's, in the same commit (godotsmith
   `test-tiers.md` section 8: one project kept 56 such rows, 45% of its suite).
5. **Put the join row in the plan**, after the last unit. Its test is the pin table itself and
   its verify line is "controls on = base pins; controls off = new pins".

**Do not stack** when:

- a control cannot return the base pins exactly. Its stub covers only part of the unit's
  behaviour: in one stack, eleven stubs applied together returned none of nine rows to base,
  so no row could be attributed;
- the arc is longer than about four units, where blame for an interaction between two units
  costs more than the saved rounds;
- a unit's design is still open, or likely to change another unit's control;
- a unit must land alone first (a hotfix, or a figure only CI can produce).

Units that move no pins (view, UI, tooling) are not part of the stack. They land freely.

## Where the files live

The repo's own convention wins (a `docs/` work folder, milestone files). With none:
`SPEC-<slug>.md`, `PLAN-<slug>.md` and `RUN-LOG.md` at the project root.
