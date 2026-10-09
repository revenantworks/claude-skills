# Eval results — revenantworks-gamedev-godotsmith

## v1.1.0 — 2026-09-28

**Status: TRACED ON ONE MODEL. Tier runs OWED.**

- **What ran:** a single-pass trace by the author model (Opus) during the parity-run apply
  unit U14/C2. It is not a blind run: the tracer wrote the changes it traced. Each trigger
  row was read against name and description only; each assertion case was traced to the
  rule in `SKILL.md` or a reference that its path loads.
- **Roster at the trace:** the rig's revenantworks packs (foundation, gamedev with
  pixelsmith and godotsmith, localops) plus the adopted third-party skills task-observer,
  book-to-skill and polish. No Godot skill set is installed.
- **Owed:** a Haiku run and a Sonnet run of both suites, each recording model, date and
  roster. No pass rate below is a tier result.

### Trigger evals — 24 queries (12 should / 12 shouldn't)

| Result | Rows |
|---|---|
| Pull, as expected | 1, 2, 3, 4, 5, 6, 7, 9, 11, 12 |
| Weak pull (the query names no Godot term and the description carries no invariant or structural-claim wording) | 8, 10 |
| No pull, as expected | 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24 |
| Probable false pull ("engine upgrades" is in the description) | 21 |

Traced 21 of 24 clean, 3 at risk. The description is byte-identical to v1.0.1, so the
v1.0.0 predictions below still stand; row 21 is added to them.

### Assertion suite — 34 cases

| Result | Cases |
|---|---|
| Anchor rule present on the case's path | A1–A6, B1–B4, C1–C12, D1, D2, D4, D5, E1–E3, F1–F3 |
| No anchor rule in the skill text; a pass rests on model judgment (pre-existing at v1.0.0, not caused by this change) | D3 (evalwright, retired 2026-10-08 into skillwright's evals, is not named anywhere in the skill), D6 (the game-design decline is in the README, not the body) |

32 of 34 anchored. The new cases trace as follows: **F1** to L1 ("the one witness that
needs no engine marker") and `gut-traps.md` section 1 (three-number reconciliation);
**F2** to L1, Entry — Check step 3 (an adopted runner's JSON is a summary line) and L3;
**F3** to `ci-guards.md` section 5 (a stamp is not a result) and the UNMEASURED verdict.
A4 now also traces to `ci-guards.md` section 3 (signature-asserting known red).

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
| `trigger-evals.md` | 24 (12 should / 12 shouldn't; corrected 2026-09-28 from a stale 20) | per-row verdict, the model, the date, and the full installed roster at the time — a trigger eval scores a description **against its neighbours**, so the same queries give different answers on a different roster |
| `test-cases.md` | 31 across five groups at v1.0.0 (corrected 2026-09-28 from a stale 21); 34 across six at v1.1.0 | per-case pass/fail with the reason, not just the verdict; a case that produced the right answer for the wrong reason is a fail |

### The rows most likely to fail, and why they were kept

Recording the prediction before the run, so the result can falsify it rather than confirm
whatever happened.

- **Trigger 15 and 16** (`author an eval suite`, `score this assertion suite`) sit directly
  on the evalwright seam (evalwright retired 2026-10-08; now skillwright's evals). If godotsmith's description pulls them, the description is too
  broad and the fix is in the description, not the eval.
- **Trigger 19** (`write more tests for the ecology module`) is the near-miss that matters
  most: ordinary test authoring is not this skill's job, but the vocabulary overlaps almost
  completely. A pull here means the description is claiming test writing.
- **Trigger 22** (`profile why the game drops frames`) tests whether the skill can tell
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

---

## 2026-10-01 — v1.1.1 (unchanged) — **FIX ROUND FX5: DESCRIPTION EDIT E4, 30 / 30 TRIGGERS RE-JUDGED; TIER RUNS BLOCKED ON A6** — runner: the fix unit (FX5), one model (Opus)

**Description edit (J1 E4, misroute M6).** "engine upgrades" became "the engine-upgrade rule, not the migration" (937 → 964 characters). Changed row: 21 ("Migrate the project from Godot 4.3 to 4.7", SHOULD NOT) now stays off, as the suite expects; the cold re-judge in J1 had it firing. The other 29 rows read the same against the new text: no row asked about upgrade cadence, and the parenthesis lost no other convention.

**Body edits (audit A5).** Invocation-control line in Behavior notes (GS-P1-1); the design-rule paragraph now says godotsmith proves a stated rule and never authors one, which anchors D6 (GS-P2-2); `perf-figures.md` section 8 (noise band and baseline age, observation 0255; 0250 was already in section 3) and a pointer from `gate-doctrine.md` section 3 (GS-P2-3). D3's evalwright anchor is a registry seam row, sent to the controller (GS-P2-1).

**Tier runs (A5 GS-P2-4): BLOCKED to A6.** The Haiku and Sonnet runs of the native suite are A6's live run.
