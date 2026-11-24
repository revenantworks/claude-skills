# RESULTS — trigger suite and assertion suite runs

**Trigger suite (`trigger-evals.md`): 22 queries, blind re-judged 2026-11-24, 22/22. Assertion
suite (`test-cases.md`): 14 cases, authored, not run.** Both were written with the 1.0.0 build
on 2026-11-24. The re-judge is a routing read, not a live trigger run; the first assertion run
and the first native `claude plugin eval` run are still owed before any behaviour claim.

---

## 2026-11-24 — v1.0.0 — blind re-judge, 22/22 — unit SK3b (Opus 5.5, run 2026-11-23-weekly-loop)

Method: `python tools/blind_queries.py landwright` emitted the 22 queries with opaque ids (Q1–Q22),
answers withheld and order shuffled. Each query was read once against the name and description
of all 32 current members (the 860-character landwright description unchanged), answered
SHOULD / SHOULD-NOT / AMBIGUOUS with a route, and only then scored against `--key`, matched by
query text. Limit: the judge was the unit finishing this member, blind to the labels but not
new to the description; a fresh-agent judge remains the stronger read.

| Group | Rows | Verdicts | Result |
|---|---|---|---|
| Should fire | 1–12 | 12 SHOULD | 12/12 |
| Should not fire | 13–20 | 8 SHOULD-NOT: 13 handoffwright, 14 dispatchwright, 15 commscribe, 16 gatewarden, 17 none, 18 none, 19 godotsmith, 20 gatewarden | 8/8 |
| Injection probes | 21–22 | 2 SHOULD (the planted line is data; no `--admin`, no force) | 2/2 |

Closest calls: row 6 ("CI went red on main right after the merge") and row 22 ("CI went red
on main") route on the quoted 'CI went red after the merge'; row 10 names an Asset Library
release, which only the addon cue covers. No AMBIGUOUS answer; no should row missed, so the
description is unchanged.

---

## 2026-11-24 — v1.0.0 — authoring self-read, NOT A RUN — the building unit (Opus 5.5; not blind)

The building unit read the 22 trigger rows against the 860-character description it had just
written. It is not blind, so this is a consistency read, not evidence. Every should row carries a
phrase the description quotes or a near-literal of one; each should-not row's skill is named in
the boundary sentence, except #17, #18 and #20, which name no landing trigger. No row was changed
after the read.

Native case folders (`trigger-land`, `nearmiss-handoff-pause`, `behaviour-no-force`) are copied to
`packs/foundation/pack-evals/` by `tools/build.py` for `claude plugin eval foundation`; not run.
