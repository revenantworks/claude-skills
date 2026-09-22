# CI guards — the assertion shapes, with worked bash

Loaded by **Entry — Guard**. The bash here is for a GUT run under GitHub Actions; the
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

          # (a) The runner's own error marker, checked BEFORE any summary line.
          # A summary printed after a script error is a summary of a partial run.
          if grep -q 'SCRIPT ERROR' gut.log; then echo "script errors"; exit 1; fi

          # (b) Exact, because this number moves rarely and it is the ONLY check
          # that catches a test file GUT silently failed to parse.
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
- **`grep -q 'SCRIPT ERROR'` runs first.** Order is the rule, not a preference.
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
keep it visible:

```yaml
      # red pending the owner's ruling: the camp year under D-19, the reroll gap
      # as a T24 finding under D-03 -- remove continue-on-error when both close
      - name: Camp year
        continue-on-error: true
        run: godot --headless -s tools/check_camp_year.gd
```

The comment carries what the flag costs: **which ruling it waits on, and the condition that
removes it.** A `continue-on-error` with no comment becomes permanent, and a permanent one
is the same as deleting the check with extra steps.

Never soften the bar itself. A `MIN_HEADS` lowered until the check passes is not a check.

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

Two consequences:

- **A push is verified by the remote run on that commit, not by a local pass.** A sha on
  `origin` says the work arrived, not that it is green.
- **A red step hides every step after it.** While an early gate is red the later steps never
  execute, so their results are *unverified*, not passing. In one run that gap ran eight
  commits deep: the first CI run to reach the test step failed two tests that had been green
  locally on every one of them, for a reason no local run could have shown
  (`determinism-and-state.md` section 3). A red gate loses its own signal and the signal of
  everything downstream, and work that lands on a red base inherits an unknown — say so
  rather than calling it untested.
