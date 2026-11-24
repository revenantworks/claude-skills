# Eval results — revenantworks-foundation-scoutwright

Runs of `trigger-evals.md` and `test-cases.md`, newest last. Started 2026-11-24.

## Cold re-judge after the neighbour trim (2026-11-24, run 2026-11-23-weekly-loop SK2d)

Method: one fresh judge with no repo access read `tools/blind_queries.py` output (answers withheld,
order decorrelated) against the current name + description of every member in the repo, plus
task-observer's description. Scored by the source row. Scope: the rows whose expected owner is a
sibling the 2026-11-24 trim dropped from this description, or whose cue review RV-SK2c restored.

Dropped: rigwright, promptwright; bench words restored. **6 / 6**.

- #15 CLAUDE.md: SHOULD NOT, rigwright. Pass.
- #17 tier pick: SHOULD NOT, promptwright. Pass.
- #29 which model for a prompt: SHOULD NOT, promptwright. Pass.
- #22 gate my pushes: SHOULD NOT, gatewarden (rigwright contender, as the row allows). Pass.
- #32 bench, popular repos: SHOULD. Pass.
- #33 little-known plugins: SHOULD, keyed on "little-known". Pass.

Rows outside that scope were judged too; disagreements there are listed as seen, not re-scored.

Seen outside scope: #27 AMBIGUOUS (scoutwright / promptwright).
