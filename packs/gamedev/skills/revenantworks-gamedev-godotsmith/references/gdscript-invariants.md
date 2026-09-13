# GDScript invariants — rules the code states but does not hold

Loaded by **Entry — Invariants**. Each pattern here is a defect shape that a suite can be
made to catch, with the test that catches it. Godot 4.x GDScript throughout.

## Contents

1. The magic constant
2. The single path
3. The test that cannot fail
4. The lint config that records what but not why
5. Determinism harnesses
6. Scripted edits across a Godot tree

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

## 4. The lint config that records what but not why

A `.gdlintrc` full of bare disables is a list of rules someone turned off. Nobody can tell
a deliberate exemption from a silenced warning, so the next person adds one more.

**The pattern:** one comment per disable, naming the files and the reason, plus a header
rule that new code gets fixed rather than exempted.

```
# main.gd, plant.gd, work.gd and l1_view.gd interleave signals/consts/vars with
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
