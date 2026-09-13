# GUT traps — what a disagreement between two numbers means

Loaded by **Entry — Check**, step 3. Every entry here is a real failure shape, not a
hypothetical. Godot 4.x with GUT is the worked runner; where a rule is runner-specific it
says so.

## Contents

1. The summary block and what each line is worth
2. The seven disagreements
3. The baseline-before-change rule
4. What GUT does not tell you at all

---

## 1. The summary block

A GUT run ends with a block of this shape:

```
Totals
------
Warnings              2
Scripts              43
Tests               411
Passing Tests       411
Asserts           324558
Time              117.556s

---- All tests passed! ----
```

What each line is actually worth:

| Line | What it proves | What it does not prove |
|---|---|---|
| `Scripts` | how many test files GUT successfully **parsed and ran** | that this is every file in the test tree |
| `Tests` | how many `test_` methods ran | that any of them asserted anything |
| `Passing Tests` | how many did not fail | that the ones that did not run would have passed |
| `Asserts` | assertions executed | that they were about the right thing |
| `All tests passed!` | nothing on its own | anything at all, without the counts beside it |

**`Scripts` is the load-bearing number.** It is the only line that changes when a file is
dropped, and dropping a file is the failure mode that produces a confident green run over
code nobody tested.

## 2. The seven disagreements

Each row is a comparison to run in Entry — Check step 3, and what it means when the two
numbers differ.

**D1 — `Scripts` is lower than the number of test files on disk.**
A file failed to parse and GUT dropped it silently. The run is green over a suite that is
missing a whole file. This is the trap the exact script-count assert exists for. Find it by
counting the files yourself and diffing against the reported count:

```bash
find tests -name 'test_*.gd' | wc -l     # what is on disk
grep -E '^\s*Scripts\s+[0-9]+\s*$' gut.log   # what GUT parsed
```

**D2 — `Scripts` matches, `Tests` is lower than last run.**
No file was dropped, so a method stopped being collected. Usually a `func test_x` renamed
out of the prefix, a block commented out, or a suite behind a flag that no longer flips.
A floor with slack will not catch this; that is L3's whole point.

**D3 — The guard's expected `Tests` floor is below the real count.**
The floor has decayed. Every test added since the floor was last written widened the gap
invisibly, and the margin is exactly how many tests could vanish with CI still green. Fix
by re-deriving the floor from a real run, then bound it so it cannot decay again
(`ci-guards.md`). Do **not** convert it to an exact assert: a test total moves on nearly
every commit, and an exact assert there trains everyone to edit the number without reading
it, which turns the guard into a formality.

**D4 — A document records a different total from the run.**
The docs are stale, the run is right, and the gap tells you how long nobody checked. Worth
tracing which commits moved the number, because a series of single-test commits that each
skipped the guard and the docs is a process finding, not a typo.

**D5 — `SCRIPT ERROR` appears in the log and the summary still says passed.**
The run is not a pass. Grep for the runner's own error marker **before** reading any
summary line, and fail the step on a hit. A summary printed after an error is a summary of
a partial run.

**D6 — A function looks untested but is driven from outside `tests/`.**
Not a gap. L2: the population was too narrow. Check every CI job's own scripts before
reporting a coverage gap. In one real pass, three of four apparent gaps were covered by a
single required headless script under `tools/`, and a `tests/`-only sweep would have
reported all three as uncovered — a 75% error in the finding count from one scope choice.

**D7 — A name matches in the test tree but on a different class.**
Not coverage. Generic names — `_process`, `to_dict`, `size`, `_grow` — match everywhere.
One local-model pass produced 90 false coverage claims almost entirely this way. Read every
hit and confirm which class is being exercised before counting it.

## 3. Baseline before change

Before editing a suite, run it unchanged and record the numbers.

```bash
git stash -q && <run the suite> ; git stash pop
```

Without that baseline, the post-change numbers look like a clean pass and any pre-existing
drift stays invisible. With it, "411 tests pass" becomes "411 pass, the baseline was 408,
the guard's floor says 404, and it has been four short since four separate commits each
added a test without touching it." The second sentence is a finding. The first is a
formality.

Same rule for the stash itself: **`git stash list` before trusting a clean tree.** A
continued session or a worktree switch can stash state silently.

## 4. What GUT does not tell you at all

- **Whether an assert was meaningful.** 324,558 asserts and a suite that never exercises
  the branch you changed are perfectly compatible.
- **Whether a test file exists that nobody wired in.** A file outside the `-gdir` tree, or
  not matching the discovery pattern, is not dropped — it was never seen. `find` catches
  this; `Scripts` does not.
- **Whether the thing it measured is the thing that ships.** A headless run proves headless
  behaviour. Anything gated on `DisplayServer.get_name() != "headless"` took the other
  branch.
