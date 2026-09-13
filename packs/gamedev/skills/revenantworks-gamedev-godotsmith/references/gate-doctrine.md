# Gate doctrine — when a milestone may close, and who closes it

Loaded by **Entry — Gate**, and by nothing else. A gate is the point where a project
decides a milestone is done. It is the most expensive thing to get wrong, because
everything after it is built on the answer.

## Contents

1. The two kinds of gate
2. The four verdicts
3. Re-deriving a figure
4. The gate sheet
5. Failure shapes

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
decay into an assumption that the gate passed. If the owner wants the next milestone to
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
   so rather than quoting the summary.
3. **State the conditions beside the figure, always.** A number without its conditions is
   not a measurement. `4.24 ms/frame` means nothing; `4.24 ms/frame under a 300-person load,
   headless, debug build` is a fact someone can check.
4. **Compare against the bar as the plan stated it.** Not as anyone remembers it, and not
   as it would need to be for this result to pass.

Three false PASSes in one project came from trusting a printed summary line rather than
doing this. The step is cheap; skipping it is how a gate certifies something nobody
measured.

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
- **Treating silence as progress.** An interrupted or rejected call ends every unit running
  under it and nothing announces the stop. Absence of output is unknown state. Re-read the
  ledger and the journals before assuming anything is still running.
