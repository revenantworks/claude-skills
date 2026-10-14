# Gate doctrine — when a milestone may close, and who closes it

Loaded by **Entry — Gate**, and by **Entry — Review** when a change's trigger lies outside
the pinned runs' horizon (section 6). A gate is the point where a project
decides a milestone is done. It is the most expensive thing to get wrong, because
everything after it is built on the answer.

## Contents

1. The two kinds of gate
2. The four verdicts
3. Re-deriving a figure, and the thin pass
4. The gate sheet
5. Failure shapes
6. Populations: what the gate seeds represent
7. Attribution: which change caused the figure

---

## 1. The two kinds of gate

**A machine gate** is defined entirely by measurements: the suite passes, lint is clean,
the headless harnesses return zero, the counts match. A machine can close it, and should.

**A judgment gate** is defined by a person's assessment: is this fun, does it read, is the
pacing right, would I keep playing. **No quantity of green checks closes one.** An agent
that reports a judgment gate closed has failed, however complete its evidence, and the
failure is worse than a missed bug because it removes the one check the project kept for a
human.

Most real gates are both, and the sequence matters: the machine half closes first and
produces the sheet the person uses to close the other half. A machine half that is still
red does not get handed over as "ready to play".

**Parking is not closing.** When a judgment gate is set aside so other work can proceed,
record it as parked, still open, and still blocking whatever it blocked. Never let a park
decay into an assumption that the gate passed. If the user wants the next milestone to
start without the judgment half, that is a separate explicit ruling that overrides the gate
in writing — never an inference from "set it aside".

## 2. The four verdicts

Every gate item gets exactly one, and the four are not interchangeable:

| Verdict | Means | Written when |
|---|---|---|
| **PASS** | measured, and it cleared the stated bar | the raw counts are in hand and re-derived |
| **FAIL** | measured, and it did not clear the bar | same, with the shortfall named |
| **UNMEASURED** | nobody measured it | the instrument was unavailable, or the run never happened |
| **PARKED** | measured or not, deliberately deferred | with the condition that reopens it |

**UNMEASURED is not FAIL and must never be written as one**, nor as PASS. It is its own
answer, and it is the honest one when a figure was never taken. Writing it as FAIL invents
a defect; writing it as PASS invents a measurement. Both destroy the sheet's value.

## 3. Re-deriving a figure

Any number a gate decision hangs on is re-derived at the gate, from raw counts, by whoever
is ruling. A printed summary line is the previous step's **claim about its own work**, not
independent evidence of it.

The procedure:

1. **Name the raw inputs.** Not "frame rate" — frames counted, seconds elapsed, and the
   scene, load and build they were counted under.
2. **Recompute from them.** If the inputs are not available, the figure is UNMEASURED. Say
   so rather than quoting the summary. A perf figure read against a stale baseline, or
   against a relative gate narrower than the rig's measured noise, is UNMEASURED or
   advisory too (`perf-figures.md` section 8).
3. **State the conditions beside the figure, always.** A number without its conditions is
   not a measurement. `4.24 ms/frame` means nothing; `4.24 ms/frame under a 300-person load,
   headless, debug build` is a fact someone can check.
4. **Compare against the bar as the plan stated it.** Not as anyone remembers it, and not
   as it would need to be for this result to pass.

Three false PASSes in one project came from trusting a printed summary line rather than
doing this. The step is cheap; skipping it is how a gate certifies something nobody
measured.

**A thin pass is a claim to re-derive twice over.** When a result clears its bar by less
than the run's noise (+0.182 against a +0.2 ms/tick bar), recompute the mean, the median and
a trimmed or steady-window mean from the raw pairs. Then confirm the verdict rule (which
statistic, over which rounds) was fixed **before** any extra rounds were added. A rule
chosen after seeing the numbers is not a rule.

## 4. The gate sheet

The deliverable of a machine gate is a sheet the person closing the judgment half can use
without having read the plan. It carries:

- **How to start, and what to press.** Written for someone who has not read anything.
- **The numbered things to look at**, each with what to watch for.
- **What is known to be wrong**, stated plainly and in advance, so the player is not
  hunting for a bug the team already logged. A sheet that hides a known failure wastes the
  one session it was written for.
- **The raw figures with their conditions**, per section 3.
- **A blank verdict block** the person fills in themselves.

The sheet is inside the review scope, not outside it. In one real run, a whole-milestone
review found that 14 of its 26 findings were defects in the gate sheet rather than in the
game — which is an argument for reviewing the sheet last, after everything it describes has
settled.

## 5. Failure shapes

- **Self-certification.** Covered above; the single worst one.
- **Softening the bar.** A plan-stated bar is moved so the result clears it. If the bar was
  wrong, say the bar was wrong and get a ruling, in the open. Never quietly.
- **Deleting the failing check.** Same failure as softening, with less evidence left behind.
  Use the honest-red pattern in `ci-guards.md` instead.
- **A gate figure with no conditions.** Unfalsifiable, so worthless.
- **Crediting an agent's report.** Completion is what the repository shows, never what a
  report claims. Check the sha, re-run the count, open the file.
- **A time limit with no measurements behind it.** A brief that caps a foreground call (about
  9 minutes; a call past 600 s is moved to the background) and says "split the suite into
  batches" sends every worker to measure first. GUT prints no per-script times, and one file ran
  476-602 s alone in a ~1900 s suite. Keep a measured per-script timing table beside the suite,
  from the last green run, and a ready batch split (`-gconfig` files) sized to it. Keep a standard
  poll helper (start the run detached, one foreground call that waits and reads the result) for
  any run that can pass the limit. A runner caps one call at one pool, or sums the per-pool
  budgets before chaining; three ~230 s pools in one call went to the background.
- **Treating silence as progress.** An interrupted or rejected call ends every unit running
  under it and nothing announces the stop. Absence of output is unknown state. Re-read the
  ledger and the journals before assuming anything is still running.

## 6. Populations: what the gate seeds represent

- **Cheap behavioural proofs run before the long measurement.** A change to a supply the camp
  lives on (food, stone, wood) is briefed with the behavioural positive-proof tests that consume
  that supply (a "flour by day 60" proof depends on early food), named beside the pins that move
  by construction, and those run first. They are cheap and catch real defects; the spread is
  expensive and only measures. A proof that went red after a 2-hour spread had already run was
  also the first sign of a targeting defect (deer at home, food at 0) that the change exposed.

A handful of gate seeds is a smoke test, not a population. A figure over them says what
those worlds did.

- **A rule's population is what the reroll reaches.** If a player can reroll the start,
  the population is every world the reroll can produce, and the gate samples it. In one
  project a 60-world census found 52% of reachable worlds went extinct while the pinned
  seeds all lived.
- **A seed-conditional mechanic gets condition-scanned seeds.** A rule that only fires
  near a river, in a drought or with a late event is measured on seeds scanned for that
  condition, named with the scan that found them.
- **Census before a run of balance rows.** Measure the spread across the population before
  tuning; several rows aimed at a symptom on four seeds can each pass while the population
  does not move.
- **A rule outside the pins' horizon needs a spread run before it ships.** A change whose
  trigger lies beyond what the pinned runs reach (an age, a season, a late event) is
  invisible to a keep-neutral round: the pins stay green because they never reach it. Run it
  on real camps across the population, and report that spread before landing.
- **A balance or design rule brings its own arms.** Units first, the unavailable arm for
  anything that unlocks, the end states of a converter, survival-or-grace fallbacks and
  levers measured in pairs are in `design-and-balance.md`; a gate on a balance figure reads
  that file beside this one.

## 7. Attribution: which change caused the figure

- **Run the control before predicting it.** A prediction written before the control arm
  ran is an expectation, and a figure compared against it inherits the guess.
- **Prove a pin round's claimed cause by reverting it in memory.** State the cause as a
  revertible transformation (a field value, a format line, a rule branch). In a probe on
  the new tree, revert exactly that and hash the result: landing byte-for-byte on the old
  pin proves the attribution on that platform, with no base worktree and no second build.
  A cause that cannot be reverted to the old value is not the whole cause. The other
  platform's row needs its CI log; name that dependency.
- **Attribute a spread loss by switching each rule off.** When a change has a cost to
  adopt (building the thing) and an effect once adopted (its rules), a comparison against
  "never adopted" measures both. Add a **built, rules off** arm, and a later adoption point
  as a third arm. Judge the rules on rules-on against rules-off; report the adoption cost
  separately. A verdict never names a rule as the cause until that rule was switched off.
