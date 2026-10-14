# GUT traps — what a disagreement between two numbers means

Loaded by **Entry — Check**, steps 3–5, when a run's numbers disagree with each other or
with a document. Every entry here is a real failure shape, not a hypothetical. Godot 4.x
with GUT is the worked runner; where a rule is runner-specific it says so.

## Contents

1. The summary block, the three-number reconciliation, and the runner marker table
2. The eight disagreements
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

**The three-number reconciliation.** One number alone proves nothing. Three must agree:

1. **on disk** — the test files the discovery pattern would find (`find`, below);
2. **reported** — the `Scripts` line the runner printed;
3. **pinned** — the exact assert in the CI guard (`ci-guards.md` section 1).

Disk = reported = pinned, stated as three figures. Disk ≠ reported is a dropped file (D1).
Reported ≠ pinned is a guard the suite has outgrown. Disk ≠ pinned with reported matching
disk is a pin nobody moved. An adopted runner's JSON (`SOURCES.md`) is a fourth copy of
"reported", not a replacement for disk: it is built from the same summary.

**The runner marker table.** The same three questions for each runner. Confirm the exit
codes against the installed runner version before wiring a guard to them.

| Runner | Summary line | Error marker (grep first) | Exit codes |
|---|---|---|---|
| GUT (`-gexit`) | the `Totals` block: `Scripts`, `Tests`, `Passing Tests` | engine `SCRIPT ERROR`, `Parse Error`, `Failed to load` | 0 all passed · 1 any failure |
| GdUnit4 (CLI tool) | the overall summary: test cases, errors, failures, orphans | the same engine markers | 0 passed · 100 failures or errors · 101 warnings only (orphans) |
| Any wrapper emitting JSON | a normalised object: tests, passed, failed, errors, skipped | whatever it forwards; check it forwards the engine markers | the wrapper's own; read its source |

A wrapper's JSON is still a summary line. Check its own identity (the parts sum to the
total) and then reconcile the total with disk, exactly as for the raw runner.

## 2. The eight disagreements

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

**D8 — GdUnit4 exits 101 and the step reads it as a pass.**
101 means "warnings only", most often orphan nodes from a test that created a node without
`auto_free`. A step written as "fail on 100" or "pass unless 1" turns 101 green, and the
orphans it reports are leaks the suite is teaching everyone to ignore. Decide 101 on
purpose in the guard: fail on it, or allow it with a comment naming the orphan count it
tolerates. Never inherit the decision from a GUT-shaped `exit != 1` test.

## 3. Baseline before change

Before editing a suite, run it unchanged and record the numbers. Prefer a **detached
worktree** of the base commit over a stash: it leaves your tree untouched and cannot lose
untracked files.

```bash
git worktree add --detach ../base HEAD
cd ../base && godot --headless --import && <run the suite>
cd - && git worktree remove ../base
```

The new worktree has never been imported, so run the headless import in it first
(`project-hygiene.md` section 1). On Windows, check the worktree's line endings match the
live tree (`core.autocrlf`): a checkout that converts to CRLF can change a hashed or
byte-compared fixture and give a baseline that differs for no code reason.

If you stash instead: run `git stash list` before and after, and include untracked files
explicitly (`git stash push -u`). A plain `git stash` leaves new test files in place, so the
"baseline" runs them.

Without that baseline, the post-change numbers look like a clean pass and any pre-existing
drift stays invisible. With it, "411 tests pass" becomes "411 pass, the baseline was 408,
the guard's floor says 404, and it has been four short since four separate commits each
added a test without touching it." The second sentence is a finding. The first is a
formality.

Same rule for the stash itself: **`git stash list` before trusting a clean tree.** A
continued session or a worktree switch can stash state silently.

**A unit carrying several tasks proves each commit alone**, before the all-together run:
stash the rest, run the suite against that commit's code, restore. A later task's code can
mask an earlier task's defect, and the combined run is green over both. In one real wave that
isolation caught a ramp that stepped at `dt = 0` on the same call that started it — undoing
its own repaint, so the effect would have frozen after the first flip — and a completed fade
that never painted at its final colour. The all-together run passed both. The review checks
that each commit's suite line was taken alone, not copied from the final run.

## 4. What GUT does not tell you at all

- **Whether an assert was meaningful.** 324,558 asserts and a suite that never exercises
  the branch you changed are perfectly compatible.
- **Whether a test file exists that nobody wired in.** A file outside the `-gdir` tree, or
  not matching the discovery pattern, is not dropped — it was never seen. `find` catches
  this; `Scripts` does not.
- **Whether `-gtest` narrowed anything.** When `.gutconfig.json` names directories, GUT
  still loads them and `-gtest` does not reduce the run to one file: the "single-file" run
  is the whole suite. Narrow with the directory, the file and the test name together:
  `-gdir=res://tests/unit -gselect=test_camp.gd -gunit_test_name=test_winter` (check the
  flag names against the installed GUT version). Confirm the narrowing worked by reading
  `Scripts` — a narrowed run says 1.
- **Whether the thing it measured is the thing that ships.** A headless run proves headless
  behaviour. Anything gated on `DisplayServer.get_name() != "headless"` took the other
  branch.
- **What a texture actually holds.** Under `--headless` the dummy renderer does not carry an
  `update()` through: `ImageTexture.get_image()` returns the image from before the call. A
  test asserting on a baked or painted texture reads the live `Image` the system itself
  holds, never the texture. It is a limit of the harness, not a defect in the code, and it
  costs a round of false failures to anyone who trusts the texture first.
