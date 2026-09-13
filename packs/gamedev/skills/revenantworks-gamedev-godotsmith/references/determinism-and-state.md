# Determinism and state

Loaded by **Entry — Review**, third of four. What a project must do so that "the same input
gives the same output" is a checkable claim rather than a hope. This matters more in an
agent-built project than a human-built one: an agent cannot eyeball a result, so
reproducibility is its only way to tell a regression from noise.

Sources for the borrowed practices are in `SOURCES.md`. Nothing here is copied text.

## Contents

1. Randomness
2. Save formats and the canonical form
3. State hashing
4. Fixed tick versus render tick
5. Typed state containers
6. Perceived fairness

---

## 1. Randomness

**Ban the global random functions from any path whose output must reproduce, and enforce the
ban with a CI check.** A global call reads from process-wide state that anything can advance,
so one extra call anywhere changes every result downstream. The bug presents as "the seed
stopped working", days after the actual change.

Randomness in deterministic code comes from an explicitly seeded generator that the
simulation state owns and serialises with everything else. If the generator is not in the
save, the save is not a save.

The CI check is a grep, and it is worth writing because this rule decays silently: a single
convenience call added under deadline pressure is invisible in review and breaks
reproducibility for good. This is C5 applied to randomness — a rule nobody enforces is a
rule nobody follows.

## 2. Save formats and the canonical form

A save must serialise to the same bytes for the same state, every time.

- **Sorted keys.** Dictionary iteration order is not a guarantee you should rely on across
  runs or versions. Sort on write.
- **Fixed-order literals.** Anything written as a sequence writes in a defined order, not in
  whatever order the source collection happened to hold.
- **No incidental floats.** A value derived through floating-point accumulation will differ
  in the last bits across platforms. Round at the boundary, or store the integer the float
  was derived from.

Without a canonical form, two saves of identical state differ, and a round-trip test cannot
tell a real serialisation bug from formatting noise.

## 3. State hashing

The round trip is the proof, and it has four steps: advance to a tick, hash, save, load,
hash again, compare, then advance both a long way and compare again. The second comparison
is the one that catches state that loaded but loaded wrong.

Two rules:

- **The hash covers the canonical form**, not a live object graph whose traversal order can
  vary.
- **A hash over a subset is a claim about that subset.** Say which fields it covers. A
  round-trip test that hashes only the fields somebody remembered is how a dropped field
  survives for months.

The harness that runs this belongs in the coverage population (L2). It drives real functions
with real assertions, and a search scoped to the test directory will report those functions
as untested.

## 4. Fixed tick versus render tick

**Simulation runs on the fixed tick. Presentation runs on the render tick.** Mixing them
makes behaviour frame-rate dependent, which means the game plays differently on different
hardware and a determinism test passes or fails depending on the machine.

Concretely: movement, forces and anything the physics solver owns go in the fixed-step hook.
Animation, UI and camera smoothing go in the variable one.

**Never write a physics body's position directly during normal movement.** The solver owns
it; writing it behind the solver's back skips collision resolution and produces tunnelling
that looks random. Teleporting is the deliberate exception and should be written so it reads
as one.

## 5. Typed state containers

**Type the dictionaries that carry persisted or cross-module state.** A bare dictionary is
an undeclared struct: every reader re-derives what the keys mean, and a typo in a key is a
runtime miss rather than a compile error.

Static typing generally is worth it in GDScript even where inference would do, because the
type is documentation the parser checks. This matters most exactly where state crosses a
module boundary, which is where a wrong assumption is cheapest to make and most expensive to
find.

## 6. Perceived fairness

Worth stating because it is counter-intuitive and it interacts with determinism: when a
distribution needs to feel fair to a player rather than be statistically pure, a weighted or
shuffled-bag approach beats independent draws. True independence produces streaks, and a
player reads a streak as a broken system.

Whichever you choose, it still comes from the seeded generator. "Feels fair" is a design
decision about the distribution, never a licence to reach for the global one.
