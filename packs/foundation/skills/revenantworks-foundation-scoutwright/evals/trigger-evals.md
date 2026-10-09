# Trigger evals — 31 queries (16 should / 15 shouldn't)

Counts: 31 queries (16 should, 15 should-not, 4 pairs)

- Provenance: written for revenantworks-foundation-scoutwright 0.1.0, 2026-10-01 (pack-split build B15). **Re-anchored to v1.0.0, 2026-10-01:** 1.0.0 launch version; suite content unchanged from the build the A6 evals ran against. **Rows 25-30 added 2026-10-08** with the `fit` entry (unit K4b), same 1.0.0.
- Method: read each query cold against name + description only; compare with the Expected column.
- State: authored, **not yet run** (no cold judge). Rows marked `native:` mirror a case folder that
  `claude plugin eval` runs in the pack's eval pass.

| # | Query | Expected |
|---|---|---|
| 1 | what changed in Claude Code since 2.1.280 — does any of it touch my hooks or settings? | SHOULD (since) · native: trigger-since-version |
| 2 | run the weekly Claude platform sweep and write the dated change report and adopt list | SHOULD (sweep) · native: trigger-weekly-sweep |
| 3 | a hook stopped firing after this week's update and nothing was announced — did the platform change something silently? | SHOULD (sweep or watch hooks) · native: trigger-silent-break |
| 4 | did anything change in Claude Code hooks this month that affects my settings? | SHOULD (watch hooks) |
| 5 | what's new on claude.ai this week — Projects, artifacts, design systems, connectors? | SHOULD (watch) |
| 6 | catch me up on everything Anthropic shipped since September 1 | SHOULD (since date) |
| 7 | are any of my skills' model tables out of date now that a model was retired? | SHOULD (watch models) · native: stale-model-table |
| 8 | build the adopt list from this week's Claude changes so my skills can be updated | SHOULD (adopt) · native: adopt-names-file |
| 9 | which of my platform-watch sources are down, and which captures am I still owed? | SHOULD (sources) |
| 10 | compare last week's Claude Code docs index with today's and tell me which pages vanished | SHOULD (watch, page-set diff) · native: docs-page-diff |
| 11 | scoutwright refresh | SHOULD (refresh) |
| 12 | Claude in Chrome stopped opening a site I use; was that announced anywhere? | SHOULD (sweep, undocumented change) |
| 13 | research the best vector database for a small retrieval app and pick one | SHOULD NOT — researchscribe · native: nearmiss-vector-db |
| 14 | design the cloud routine that runs my weekly checks every Monday at 07:00, with a kill switch | SHOULD NOT — agentwright · native: nearmiss-schedule-routine |
| 15 | write a CLAUDE.md for this repo with the build and test commands | SHOULD NOT — rigwright · native: nearmiss-claude-md |
| 16 | apply this adopt row to skillwright's rubric file and bump nothing | SHOULD NOT — skillwright |
| 17 | which model tier should I run this refactor prompt on? | SHOULD NOT — promptwright |
| 18 | is this third-party plugin safe to install? here is its repo | SHOULD NOT — trustwarden |
| 19 | read this Reddit thread and summarise what people say about the new router | SHOULD NOT — researchscribe (sources) |
| 20 | how fast should I spend my weekly usage now that a new model is out? | SHOULD NOT — pacewright |
| 21 | write the release notes for my plugin's 1.2.0 | SHOULD NOT — commscribe |
| 22 | update my settings.json to add a PreToolUse hook for git push | SHOULD NOT — gatewarden (rigwright only for a new hook's placement) |
| 23 | audit this skill against current best practices | SHOULD NOT — skillwright |
| 24 | what version of Claude Code am I running right now? | SHOULD NOT — a direct answer; no sweep |
| 25 | Haiku 5.5 just came out — can we use it for coding? | SHOULD (fit, model) · native: trigger-fit-new-model |
| 26 | what's the best way to use the new `/dash` view in my setup? | SHOULD (fit, feature) |
| 27 | should our mechanical units move to the new small model? | SHOULD (fit, model; a trial proposed, not run) · native: fit-card-no-tier-edit |
| 28 | what changed in Claude since Monday? | SHOULD (since, not `fit`: the change list, no fit card) |
| 29 | which model should run this prompt? | SHOULD NOT — promptwright (model) · native: nearmiss-which-model-prompt |
| 30 | how fast can I spend this week? | SHOULD NOT — pacewright |
| 31 | Haiku 5.5 is adopted for our mechanical lane — measure what it costs per weekly point before the first wave | SHOULD NOT — pacewright (baseline; the pair with row 27) |

## Edge notes

- Sharpest pair: **scoutwright ↔ researchscribe** (rows 12, 13, 19). Platform change is the
  scout's; an outside topic or one walled thread is researchscribe's. A Reddit thread about a
  Claude change (19) stays researchscribe's: the ask is to read one source, not to sweep.
- Second pair: **scoutwright ↔ agentwright** (row 14): the routine around a sweep is agentwright's,
  even when it names a weekly check.
- Third pair: **scoutwright `fit` ↔ promptwright `model`** (rows 25, 29). A newly released model
  or feature and where it belongs across the user's job classes is `fit`; one prompt or task's
  tier pick from the current roster is promptwright's. Row 28 is the in-skill near-miss: it fires
  scoutwright on `since`, and a fit card in its reply is a miss.
- Fourth pair: **scoutwright `fit` ↔ pacewright `baseline`** (rows 27, 31; added 2026-10-08, audit
  K7-2-10). Whether a new model should take a job type is the fit card's; measuring an adopted
  model's cost per point is pacewright's.
- Tuning: misses on rows 1-12 → make the trigger list pushier (add the user's words); fires on rows
  13-24 → tighten the boundary sentence.
