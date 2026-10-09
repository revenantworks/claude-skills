# CI guards — the assertion shapes, with worked bash

Loaded by **Entry — Guard**, and by **Entry — Check** step 4 to find the pinned counts. The bash here is for a GUT run under GitHub Actions; the
shapes are runner-agnostic, the commands are not.

## Contents

1. The full guard, annotated
2. Why the floor is bounded rather than exact
3. The honest-red pattern
4. Guard smells
5. What "green" means

---

## 1. The full guard, annotated

```yaml
      - name: Tests
        run: |
          set -o pipefail
          godot --headless -s addons/gut/gut_cmdln.gd \
            -gdir=res://tests -ginclude_subdirs -gexit 2>&1 | tee gut.log

          # (a) The engine's error markers, checked BEFORE any summary line.
          # A summary printed after a script error is a summary of a partial run.
          # Godot can log any of these and still exit 0. Benign lines are pinned
          # by exact text in ci/benign-errors.txt, each with a comment saying why.
          ERR='SCRIPT ERROR|Parse Error|Failed to load|Cannot open file|Resource file not found'
          if grep -E "$ERR" gut.log | grep -v -F -x -f ci/benign-errors.txt; then
            echo "engine errors (above)"; exit 1
          fi

          # (b) Exact, because this number moves rarely. It is the witness that does
          # not depend on the engine printing a marker: (a) catches most dropped
          # files, this catches the drop that printed nothing.
          grep -E '^\s*Scripts\s+43\s*$' gut.log || { echo "expected 43 scripts"; exit 1; }

          # (c) Floored, because a test total moves on nearly every commit.
          tests_line=$(grep -E '^\s*Tests\s+[0-9]+\s*$' gut.log)
          tests_count=$(echo "$tests_line" | grep -oE '[0-9]+')
          TESTS_FLOOR=411
          SLACK_MAX=10
          [ -n "$tests_count" ] || { echo "no Tests line in gut.log"; exit 1; }
          [ "$tests_count" -ge "$TESTS_FLOOR" ] \
            || { echo "expected >= $TESTS_FLOOR tests, got '$tests_line'"; exit 1; }

          # (d) The slack, printed on every green run and bounded. Without these
          # two lines the floor decays invisibly: a passing guard says "pass",
          # never "pass, with four to spare".
          slack=$(( tests_count - TESTS_FLOOR ))
          echo "tests=$tests_count floor=$TESTS_FLOOR slack=$slack"
          [ "$slack" -le "$SLACK_MAX" ] \
            || { echo "the floor is $slack behind the suite -- raise TESTS_FLOOR to $tests_count"; exit 1; }
```

Four things that are easy to get wrong:

- **`set -o pipefail` is load-bearing.** Without it, `godot ... | tee` returns `tee`'s
  status and a crashed runner passes the step.
- **The error grep runs first, and it greps the whole marker set.** Order is the rule, not a
  preference. `SCRIPT ERROR` alone misses a missing resource or an unopenable file, and
  Godot's exit code does not cover for it. The allow-list is exact lines, never a pattern:
  a broad exclusion hides the next real error of the same shape. An empty allow-list file
  must still exist, or `grep -f` fails the step for the wrong reason.
- **The `-n` check on `tests_count` is not paranoia.** If the summary format changes, the
  arithmetic comparison silently becomes a string test against empty and the guard stops
  guarding. Fail on the missing line instead.
- **Anchored patterns.** `^\s*Scripts\s+43\s*$` matches the summary row and not a passing
  mention of the word elsewhere in a 100 KB log.

## 2. Why the floor is bounded rather than exact

Both assertions in the same step are written at the same time against the same run for the
same purpose, and they decay at completely different rates.

| | Exact assert | Bare floor |
|---|---|---|
| Can go stale silently | no | **yes** |
| Maintenance moment | every change, enforced by a red build | none |
| Cost of a real change | edit one number | nothing, so nobody edits it |
| Failure it leaves open | none | anything inside the margin |

Making the test count exact too is the tempting wrong fix: a total that legitimately moves
on nearly every commit turns every real change into a two-line change, and trains people to
edit the number without reading it. Bounding the slack keeps the floor cheap and gives it
the one property it lacked — it now fails when it falls behind, and names the number to
raise it to.

Pick `SLACK_MAX` from how fast the suite grows. Ten is right for a suite adding a few tests
a week; smaller for a stable one.

## 3. The honest-red pattern

A check that fails because the game genuinely fails is information. Keep it running and
keep it visible — and **assert how it fails, not only that it does.** A bare
`continue-on-error` tolerates any failure. When the failure changes shape (the harness now
dies before it reaches the measurement it is named for) the log still prints the same
"failed, continuing" line, and everyone matches it against the documented reason.

```yaml
      # Known red, pending the user's ruling on <decision id>: the harness fails
      # its own survival bar. Remove this wrapper when that ruling closes.
      - name: Survival year (known red)
        run: |
          set +e
          godot --headless -s tools/check_survival.gd > survival.log 2>&1
          code=$?
          set -e
          cat survival.log
          if [ "$code" -eq 0 ]; then
            echo "known-red check PASSED: retire the wrapper and make it a gate"; exit 1
          fi
          grep -F 'heads below MIN_HEADS' survival.log \
            || { echo "known-red check failed for an unexpected reason"; exit 1; }
```

The step is now a real guard: it fails when the pinned fragment is absent **or** when the
check starts passing, and stays green only while the failure is the documented one. The
comment carries what the tolerance costs: **which ruling it waits on, and the condition that
removes it.** A tolerance with no comment becomes permanent, and a permanent one is the same
as deleting the check with extra steps. The same holds for every other way of turning a
failure into a note: a skipped test, a quarantined case, an expected-failure marker, a
known-issue line in a status file. Each carries the failure's signature, not just its
existence.

A design that depends on a measurement names the harness by **file and function**, never by
a label ("the tool policy"). When that harness goes known red, the design's measurement row
is flagged in the same commit.

Never soften the bar itself. A survival floor lowered until the check passes is not a check.

## 4. Guard smells

- **A guard that can fail three ways with one message.** Diagnosing it costs more than it
  saves. One guard, one reason.
- **An expected number with no comment saying where it came from.** The next person cannot
  tell a deliberate bar from a stale one, so they raise it to match the failure.
- **A number in the guard, in a doc, and in a handoff, with nothing reconciling them.**
  Pick one home; have the others quote it and name the source.
- **A guard that only runs on one branch.** It is not a guard, it is a preference.
- **A step that reports a figure it did not compute.** If the step prints a frame rate it
  read from another job's summary, it is repeating a claim, not making one.
- **Known red with no signature.** A `continue-on-error` (or skip, or quarantine) that does
  not grep for its expected failure fragment. Section 3.
- **A guard narrower than its name.** A check called "no one starves" that only tests the
  first day. The failure message names its actual subject (what was checked, over which
  population, at which tick), and a design that cites the guard quotes its assert line,
  not its name.
- **Pins over a dead state.** A set of pinned values taken at checkpoints that are all the
  same state (everyone is dead by the first one, the store is empty at all three) collapses
  silently: every later change "keeps" the pins. Assert the checkpoints are distinguishable
  (`assert_ne(mid, final)`, a precondition such as heads > 0 at each one), and pair every
  "over all X" invariant with a positive control that X was actually exercised.

## 5. What "green" means

**Green means every step the CI file runs, and the list of those steps is read from the
workflow file — never from a document that describes it.** A brief, a README, a CLAUDE.md or
a reviewer's checklist is a copy of the verification contract, and a copy drifts the moment
the contract grows a step. In one real project the workflow gained a lint step; every brief
written afterwards restated the older list, three review rounds reported green on every check
they had been told about — and they were green, for the checks named — while two pushes sat
red on lint alone over thirty findings in a single new test file. Nobody ran the linter
because nobody was told to, and the reviewer was reading the same list as the implementer, so
the gap was invisible from inside the work.

So: derive the checklist by opening `.github/workflows/ci.yml` (or the runner's equivalent)
at the moment the checklist is written, name that file in it, and quote each step's own
command rather than a paraphrase. A check nobody is told to run is a check nobody runs.

The consequences:

- **A push is verified by the remote run on that commit, not by a local pass.** A sha on
  `origin` says the work arrived, not that it is green.
- **A stamp that a run happened is not a result.** A verify hook that accepts a turn because
  a marker file is newer than the last edit records that something ran, not what it found.
  Verification is the recorded numbers (script, test and failure counts from a run on that
  commit); with none recorded, the check is UNMEASURED.
- **A red step hides every step after it.** While an early gate is red the later steps never
  execute, so their results are *unverified*, not passing. In one run that gap ran eight
  commits deep: the first CI run to reach the test step failed two tests that had been green
  locally on every one of them, for a reason no local run could have shown
  (`determinism-and-state.md` section 3). A red gate loses its own signal and the signal of
  everything downstream, and work that lands on a red base inherits an unknown — say so
  rather than calling it untested.
- **A change that removes a platform's pins lands through a branch.** When only the CI
  runner can produce one platform's pinned values, push the change to a branch first. Its
  CI run fails on exactly the expected tests; derive that platform's values from the log,
  commit them on the branch, and let the branch go green. `main` fast-forwards only to the
  green commit, so it never goes red. Landing on `main` and re-pinning afterwards spends the
  green base every later merge depends on.
