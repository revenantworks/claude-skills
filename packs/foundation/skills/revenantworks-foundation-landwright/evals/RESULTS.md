# RESULTS — trigger suite and assertion suite runs

**Trigger suite (`trigger-evals.md`): 22 queries, authored, not run. Assertion suite
(`test-cases.md`): 14 cases, authored, not run.** Both were written with the 1.0.0 build on
2026-11-24. No blind judge has read the trigger rows against the description, and no case has
run. That is a finding, not a footnote: the first blind re-judge and the first assertion run are
owed before any routing or behaviour claim is made at 1.0.0.

---

## 2026-11-24 — v1.0.0 — authoring self-read, NOT A RUN — the building unit (Opus 5.5; not blind)

The building unit read the 22 trigger rows against the 860-character description it had just
written. It is not blind, so this is a consistency read, not evidence. Every should row carries a
phrase the description quotes or a near-literal of one; each should-not row's skill is named in
the boundary sentence, except #17, #18 and #20, which name no landing trigger. No row was changed
after the read.

Native case folders (`trigger-land`, `nearmiss-handoff-pause`, `behaviour-no-force`) are copied to
`packs/foundation/pack-evals/` by `tools/build.py` for `claude plugin eval foundation`; not run.
