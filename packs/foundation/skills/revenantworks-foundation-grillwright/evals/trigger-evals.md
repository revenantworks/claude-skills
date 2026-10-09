# Trigger Evals — revenantworks-foundation-grillwright

- Provenance: derived from revenantworks-foundation-grillwright v1.0.0, 2026-10-08.
- Counts: 24 queries (12 should, 12 should-not, 5 pairs), judged cold against name + description only.
- Owed: every row authored, not run. Rows 1-3 were carried from promptwright's trigger rows 35-37, now routed here.

## Should fire

| # | Query | Why |
|---|---|---|
| 1 | "grillwright" | Quoted invocation keyword |
| 2 | "Grill me on this before you write the prompt — I don't want you guessing at the output format." | Named grill ahead of a prompt build (was promptwright #36) |
| 3 | "Grill me on my plan to move the team to a four-day week." | Plan lens, the verb named |
| 4 | "Interview me before you build the inventory screen." | Code-feature lens, interview named |
| 5 | "Ask me questions until the spec for autosave is clear." | Paraphrase of the job |
| 6 | "What am I missing before we start on the save migration?" | Pre-build gap question |
| 7 | "Stress-test this idea for a weekly newsletter before I commit to it." | Idea stress-test |
| 8 | "grillwright resume — pick up the open questions in GRILL-autosave.md" | Named subcommand with a record |
| 9 | "Write up the decisions we've settled so far as a record; don't ask me anything." | `record` entry, unnamed |
| 10 | "Make a list of questions for the art lead to answer about the tileset." | `questionnaire` entry |
| 11 | "Before you design the skill, pin down with me what it should actually do." | Pre-build interview for a skill |
| 23 | "Grill me on the sync feature, but check my answers against our glossary and the ADRs in docs/adr first." | `docs` entry, unnamed; pair-mate of #24 |

## Should not fire

| # | Query | Route | Why |
|---|---|---|---|
| 12 | "Write a system prompt for a support bot that answers refund questions." | promptwright | A build, no interview asked |
| 13 | "Grill my nightly backup agent on what it's allowed to delete." | gatewarden | A running agent's blast radius; the shared verb is the seam (was promptwright #37) |
| 14 | "Build me a skill that summarises PR comments." | skillwright | A build; skillwright's own step 1 interviews |
| 15 | "Implement the autosave spec in GRILL-autosave.md." | slicesmith | The record is settled; the build starts |
| 16 | "Compare Linear and Jira for a five-person team, with sources." | researchscribe | Sourced comparison |
| 17 | "Write a handoff so the next session can continue this work." | handoffwright | A handoff, not an interview |
| 18 | "Quiz me on Spanish verb conjugations." | none | Teaching, not requirements |
| 19 | "Review this pull request for bugs." | code review | Review, not pre-build |
| 20 | "Design the kill switch and cadence for my scheduled scraper." | agentwright | Agent system design |
| 21 | "Shorten this prompt without changing what it does." | promptwright (slim) | Pure trim |
| 22 | "Fix the failing GUT test in combat_test.gd." | godotsmith | A test run to believe |
| 24 | "Write the support-bot system prompt using the terms defined in our CONTEXT.md glossary." | promptwright | A build that reads a glossary; no interview asked |

## Edge notes

Sharpest pairs: #2 vs #12 (the grill named versus a plain build); #13 vs #3 (the object decides,
not the verb); #15 vs #4 (a settled record versus an open request); #14 vs #11 (build versus the
interview before it); #23 vs #24 (a glossary-grounded grill versus a build that only reads the
glossary). Misses on the yes-set: make the triggers pushier. Fires on the no-set:
tighten the boundary sentence.
