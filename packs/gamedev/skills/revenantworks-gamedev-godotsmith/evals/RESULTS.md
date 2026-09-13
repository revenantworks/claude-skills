# Eval results — revenantworks-gamedev-godotsmith

## v1.0.0 — 2026-09-12

**Status: AUTHORED, NOT RUN.**

Both suites in this folder were written against the SKILL.md and references in the same
commit. Neither has been executed against a model. No pass rate is claimed, and no pass
rate should be quoted from this file until one appears below with a date and a model name.

That statement is the skill's own L1 applied to itself: a suite that has not run tells you
nothing about the thing it tests, and an eval file with no results block reads from a
distance exactly like one with a clean sweep. Saying so here is cheaper than being
misquoted later.

### What a run owes when it happens

| Suite | Cases | What a run must record |
|---|---|---|
| `trigger-evals.md` | 20 (10 should / 10 shouldn't) | per-row verdict, the model, the date, and the full installed roster at the time — a trigger eval scores a description **against its neighbours**, so the same 20 queries give different answers on a different roster |
| `test-cases.md` | 21 across five groups | per-case pass/fail with the reason, not just the verdict; a case that produced the right answer for the wrong reason is a fail |

### The rows most likely to fail, and why they were kept

Recording the prediction before the run, so the result can falsify it rather than confirm
whatever happened.

- **Trigger 13 and 14** (`author an eval suite`, `score this assertion suite`) sit directly
  on the evalwright seam. If godotsmith's description pulls them, the description is too
  broad and the fix is in the description, not the eval.
- **Trigger 17** (`write more tests for the ecology module`) is the near-miss that matters
  most: ordinary test authoring is not this skill's job, but the vocabulary overlaps almost
  completely. A pull here means the description is claiming test writing.
- **Trigger 20** (`profile why the game drops frames`) tests whether the skill can tell
  finding a cause from ruling on a figure. A pull means the gate language is leaking into
  general performance work.
- **Case A3** asks the model to refuse an obvious-looking fix — making the test count an
  exact assert. Models tend to accept the tidier-sounding option, so this one is a real test
  of whether L3's reasoning landed or only its conclusion.
- **Case D5** hides an instruction inside handed-in material. It is the injection case, and
  it is the one worth re-running on every model the skill will be used with.

### Re-run policy

Re-run both suites when: the `description` field changes by more than whitespace; a law is
added, removed or reworded; a new gamedev pack member ships, because the roster the trigger
evals are judged against has moved; or the skill is used on a model it has not been tested
on. A version bump on its own does not owe a re-run when the routing surface and the laws
are byte-identical — say so explicitly in the provenance line rather than leaving it
ambiguous.
