# Results — revenantworks-gamedev-soundsmith

Run records for every suite in `evals/`: the trigger table (`trigger-evals.md`, 20 rows), the assertion
cases (`test-cases.md`, 13 cases) and the five native `claude plugin eval` cases under `evals/<case>/`.
Newest block last. No pass rate below is a tier result until a block says which models ran.

---

## 2026-10-01 — v0.1.0 (unchanged) — **FIX ROUND FX5: 20 / 20 TRIGGERS RE-JUDGED BY HAND; NATIVE AND TIER RUNS BLOCKED ON A6** — runner: the fix unit (FX5), one model (Opus)

**Why this block exists.** Audit A5 (SS-P1-2) found no run record for any suite. This file starts that
record. It does not claim a live run.

**Description edit (J1 edit E5, misroute M7).** "Direction, not DSP — it never generates or processes
audio." gained "; a request to generate a game sound starts here with the brief." (894 → 957
characters). The paired comfyrunner edit (E6) is outside this pack and goes to the controller.

**Triggers, 20 / 20, hand re-judge.** Judged against the new description and the named siblings'
descriptions. The judge had seen the labels, so this is a re-judge, not a cold blind pass.

| row | query (short) | expected | verdict | note |
|---|---|---|---|---|
| 10 | Generate a jump sound for my platformer | fire | fire | **changed**: J1's cold judge sent it to comfyrunner; the new clause claims it |
| 11 | Run this ComfyUI audio workflow JSON | not fire | not fire | the description still names running a workflow as comfyrunner's |
| 1-9, 12-20 | unchanged | as table | as table | no row reads the edited clause |

**Assertion cases.** TC8 (asked to generate) already expects the brief first and the runner named; the
edit matches it. No case changed. Count check: 13 `## TC` headings = 13 in the header.

**Native suite and tier runs: BLOCKED to A6.** The five native cases and the Haiku and Sonnet tier runs
need A6's live `claude plugin eval` run. Until that block is appended here, the README quotes no pass
rate.
