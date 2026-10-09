# GDScript invariants — rules the code states but does not hold

Loaded by **Entry — Check** step 4 and **Entry — Review** when a rule the code states
does not hold, or when writing the test that holds it. Each pattern here is a defect shape that a suite can be
made to catch, with the test that catches it. Godot 4.x GDScript throughout.

## Contents

1. The magic constant
2. The single path
3. The test that cannot fail
4. The lint config that records what but not why
5. Determinism harnesses
6. Scripted edits across a Godot tree
7. Prose claims that are measurements
8. Geometry and movement rules
9. Changing a function signature

---

## 1. The magic constant

A clamp, floor, threshold or margin whose value was chosen once and never checked against
the geometry it bounds. It works until something reaches the end of its range.

**The shape.** A zoom-band controller fades three views in and out by distance from their
band centres. A dev key narrows the band width, clamped at a bare `0.4`. The three centres
sit `2.0` apart, and the views hide themselves below alpha `0.01`. Ten presses reached
`0.9`, where the midpoints between centres drove all three alphas to zero at once and the
world stopped drawing. Nothing in the code connected the clamp to the spacing.

**The fix is not a better number.** It is deriving the number and showing the arithmetic:

```gdscript
## Adjacent centres are CENTER_SPACING apart, so the worst case is the midpoint
## between two of them, where each neighbour is CENTER_SPACING / 2.0 away and
## _alpha() returns 1.0 - (CENTER_SPACING / 2.0) / band_width. The views hide at
## band_alpha <= ALPHA_VISIBLE_FLOOR, so that must stay strictly above it:
##
##     1.0 - 1.0 / w > 0.01   ->   w > 1.0101...
##
## MIN_BAND_WIDTH rounds up to 1.1. Keep this derived if the centres ever move.
const CENTER_SPACING := 2.0
const ALPHA_VISIBLE_FLOOR := 0.01
const MIN_BAND_WIDTH := 1.1
```

**Then close the loop structurally.** The three views each carried their own `0.01`
literal. Having them reference `ALPHA_VISIBLE_FLOOR` turns a comment naming three line
numbers into a dependency the compiler keeps true.

**The test** asserts the derivation, not the value:

```gdscript
var derived: float = (CENTER_SPACING / 2.0) / (1.0 - ALPHA_VISIBLE_FLOOR)
assert_gt(MIN_BAND_WIDTH, derived, "must stay above the width at which the midpoints hide")
```

so that moving a centre fails the suite before it blanks the screen.

## 2. The single path

A class doc says every departure, every write, every release goes through one function.
The test is whether **every branch** calls it. Bypasses hide in the branch nobody exercised.

**The shape.** A class doc claimed every way a person leaves — age, starvation, a named
death, emigration — routes through one `_depart`, so a carried load always becomes a pile
rather than vanishing. One branch of `emigrate_one` called `state.people.remove_at(i)`
directly, skipping the release entirely. The doc had been true when written.

**The check:** grep for the primitive the single path wraps (`remove_at`, `erase`, `free`,
a direct field write) and confirm every hit is inside that path. When a branch legitimately
reaches the path in a state where it is a no-op, say so in the comment — the point is that
the path is taken, not that it does work every time.

## 3. The test that cannot fail

A sweep or invariant test that always passes looks identical to one that is incapable of
failing. Pair it with a **positive control**: the value that used to break it.

```gdscript
func test_the_sweep_catches_a_band_width_below_the_floor() -> void:
	# 0.9 is what ten presses reached when the clamp was a bare maxf(0.4, ...).
	var bc: BandController = autofree(BandController.new())
	bc.band_width = 0.9
	assert_lt(bc.band_width, BandController.MIN_BAND_WIDTH, "the clamp now forbids this")
	assert_lt(_max_band_alpha(bc, 0.0), BandController.ALPHA_VISIBLE_FLOOR, "nothing drawn")
```

If someone later breaks the detector, this test fails and names what it was written for.

**Every negative assert ships its positive control, built by the same fixture.** "X is not
used / not chosen / not counted" passes just as well when the fixture never built X. Assert
the fixture's state before the negative check (`progress < 1.0` stated, not assumed), and
pair it with the matching "does" case (a finished building that *must* be used) made by the
same helper with the same arguments. In one build the negative assert passed because a
positional argument set the wrong field; only the positive control's failure exposed it.

Three more shapes of the same defect, (the fourth is the last bullet):

- **An "over all X" invariant over an empty X.** "No one carries more than their limit"
  passes trivially on a day nobody carries anything. Pair it with a positive control that
  X was exercised (at least one carrier this run), and when pinned checkpoints stand in for
  the run, assert they differ from each other (`ci-guards.md` section 4, pins over a dead
  state).
- **A recovery test that passes with the recovery deleted.** A test for "a lost input is
  recovered" must first assert the input was lost: drop the event, assert the state
  missed it, then run the recovery and assert it caught up. Without the first assert the
  test passes whenever the event simply arrived. GUT dispatches
  `Input.parse_input_event` under `--headless`, so input tests need no window.
- **A refusal enforced by `assert`.** In a debug run a failed `assert` is a `SCRIPT ERROR`,
  and a CI that fails on the engine's error markers (it should) then fails the very test
  that proves the refusal. A behaviour the project must **test** is enforced by an explicit
  guard that ignores the write and calls `push_warning`, and the test asserts the value did
  not change. `assert` is for states no test should ever reach. A brief that asks for both
  on the same line has a defect to fix before dispatch.

- **A layout figure taken from the design.** A width or size the design document states (or shows in example strings) is a claim, not a measurement: probe it in the engine at the base scale before an assertion or a pin uses it (obs 0098, 0086). The engine is the only instrument.

**The exception: a literal only the running mechanism can produce.** Writing the test first
and observing the red before any source changes is the checkpoint that proves a test can fail
— and it assumes the expected value follows from the design. For a geometric recovery point,
a tick-exact arrival, a save size after a format change or a state fingerprint, no literal
exists before the mechanism does, and typing one from expectation violates the older rule
that a literal is measured, never guessed. The two rules collide, and the collision has one
answer:

1. Build the mechanism.
2. Take the literal with a probe, under stated conditions, and pin it with those conditions
   beside it (`determinism-and-state.md` section 3 for what makes a pinned literal portable).
3. Prove the test can fail *after the fact*, by perturbing the measured value once — the
   positive control above, taken in the other order.
4. Say in the commit body which tests took that path and why.

The dropped-script trap is still covered, because the `Scripts` count is checked on every run
whatever the order (L1). Name this path in the process so each implementer follows a step
rather than writing a paragraph justifying an exception nobody wrote down.

## 4. The lint config that records what but not why

A `.gdlintrc` full of bare disables is a list of rules someone turned off. Nobody can tell
a deliberate exemption from a silenced warning, so the next person adds one more.

**The pattern:** one comment per disable, naming the files and the reason, plus a header
rule that new code gets fixed rather than exempted.

```
# main.gd, plant.gd, work.gd and world_view.gd interleave signals/consts/vars with
# doc comments in an order gdlint's default ordering does not recognize.
- class-definitions-order
```

**Parser limitations are excluded by path, not by config**, and the config says so. A
source file declaring `var set := {...}` cannot be parsed by gdtoolkit at all, because the
grammar reserves `set` for property syntax. No lint rule fixes that; CI excludes the one
file by path and the config's header explains why, so nobody later "fixes" the config and
wonders why lint still fails.

## 5. Determinism harnesses

A simulation that claims determinism proves it with a round trip, not an assertion:
advance to a tick, hash the state, save, load, hash again, compare, then advance both a
long way and compare again. Run it from a headless tool script wired as a required CI job.

Two rules:

- **The hash covers what matters.** A hash over a subset is a claim about that subset.
- **The harness is part of the coverage population** (L2). It drives real functions with
  real assertions, and a `tests/`-only sweep will report them as untested.

## 6. Scripted edits across a Godot tree

Multi-file edits applied by script are normal in a large GDScript repo. Two rules keep them
from failing silently:

- **Detect each file's own line ending.** Endings are a per-file property, not a per-repo
  one. Five files in one directory of a real project carried three different answers.
  Sampling one and normalising the rest makes every search string miss in the others.
- **Assert the occurrence count before writing.** `bytes.replace()` on a string that does
  not occur returns the original bytes: the script writes the file unchanged and exits
  zero. A per-edit count assertion turns every silent no-op — wrong ending, wrong
  indentation, a string that moved, a script already applied — into a loud stop at the
  first one, and gives idempotency for free.

```python
def eol(b):
    return "\r\n" if b.count(b"\r\n") > b.count(b"\n") - b.count(b"\r\n") else "\n"
```

## 7. Prose claims that are measurements

A doc comment that states a bound is a measurement nobody took until a test takes it.

- **A conservation claim is a measurement.** "Nothing is created or lost in a haul" is a
  test that sums the goods before and after a run, not a sentence in a class doc.
- **A worst-case string derives from the format's bounds.** The longest label a HUD must
  fit is built from the largest value each field can hold, not from a sample screenshot.
- **A lattice is a test.** A claim that positions, sizes or ticks fall on a grid is
  asserted over every member, not over the three that were eyeballed.
- **"Never" carries its horizon.** "The store never empties" means "within N days on these
  seeds". Name N and the seeds, or the claim is untestable.
- **A literal in CI names its derivation.** Every expected number in a guard carries a
  comment saying which run, command or formula produced it.
- **A rule that assumes a task fits a period is tested at the slowest work factor.** A tend
  task sized to fit a day at full speed stops fitting when later rows add needs that slow
  work, and the rule breaks silently. List the rules that assume a fit, and assert each one
  at the slowest multiplier the code can produce, again whenever a row adds a multiplier.
  Before designing a fix for a shortfall, measure the flow by source and by season.

## 8. Geometry and movement rules

Section 1's derivation, applied before the build rather than after the bug.

- **Put the interacting constants side by side, on paper, first.** A block radius, a reach,
  a cell size and a band width that live in separate documents interact anyway. Before a
  geometry or movement rule is built, the brief lists them in one table and checks the
  inequality the rule needs (reach > radius + half a cell, and so on). The check is cheap;
  finding it in play is not.
- **Every counter a rule needs has a saved owner.** "Stuck for N ticks" needs a field that
  holds N and is in the save, or the rule cannot survive a load deterministically
  (`determinism-and-state.md`). A shared static result that any nested call overwrites is
  not an owner.
- **Obstacles 8-connected, walkable land 4-connected.** A raster obstacle set that touches
  at corners blocks a diagonal step only if the walk rule says so. Refuse a diagonal step
  through a corner (both orthogonal neighbours must be free), and ship a test that no
  diagonal cuts a corner whenever a blocked set can be built at a free angle.
- **A hang guard measures net progress.** A guard that resets on "closer than the last
  step" never trips on a jiggle that gets closer every other tick (one walker logged 3,501
  reversals in 4,000 ticks and never arrived). Measure against a best-so-far distance, or
  count reversals, and add the property test that no walker oscillates beyond a bound on the
  gate seeds. A probe's non-arrival flag is keyed per walk, not per walker and spot, or a
  second trip to the same spot fires it.

A guard must fail on the behaviour it exists for, not only on the case its author pictured.

## 9. Changing a function signature

GDScript does not reject a call whose old argument now lands in the next parameter of the
same type. Removing `seed: int` from `camp(seed: int, heads: int = 300)` turned an untouched
`camp(1337)` into a 1,337-head camp, with no error; only a head-count assertion caught it.

When a removed or reordered parameter's neighbour has the same type, either **rename the
function** (every old call then fails to parse, which is the safe failure) or **grep every
call site and fix each one in the same commit**, naming the grep in the commit body. Default
values make the hazard worse, because a shorter old call still parses.
