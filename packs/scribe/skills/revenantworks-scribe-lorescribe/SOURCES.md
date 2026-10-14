# Sources

Last verified: 2026-10-01

Where lorescribe's guidance comes from, and its parity register. The register is a calendar surface (90 days): re-run the incumbent scan when it ages out.

## Guidance

| Area | Claim | Source | Checked |
|---|---|---|---|
| Skill format | Frontmatter keys, description ceiling, listing cap, progressive disclosure | code.claude.com/docs/en/skills; platform.claude.com agent-skills best practices (via skillwright's rubric, verified 2026-09-28) | 2026-10-01 |
| Native evals | Case folders with `prompt.md`, `case.yaml` (`context.add_dirs`), `graders/*.md`; grader types `regex`, `tool_used`, `file_exists`, `llm`; two-arm baseline | code.claude.com/docs/en/plugin-evals | 2026-10-01 |
| Bible layout | Entity file per element, kebab-case ids, `_index.md` registries, bidirectional links, `schema-version` in `story.md` | github.com/danjdewhurst/story-skills README (MIT) | 2026-10-01 |
| Canon levels; halt on contradiction | Lore entries carry a canon level; a contradiction stops the pipeline | github.com/Donchitos/Claude-Code-Game-Studios, `team-narrative` skill | 2026-09-28 |
| Check codes | Orphan references, name variants, timeline paradoxes as named checks | github.com/mimir-dm/mimir (narrative-continuity-checker) | 2026-09-28 |
| Canon slice | Retrieve book facts per scene; never paste the whole codex | novelmage blog; story-skills issue #257 (context packs) | 2026-09-28 |
| Read-only, human in the loop | Read-only mounts; destructive verbs need a human | github.com/mm-weber/loremaester issues SEC-2, SEC-5 | 2026-09-28 |
| Story-draft brief shape | Card frontmatter (`target`, `mode`, `check`, `expect`) plus a prose prompt; interactive needs no check; an unattended card needs an owner-authored check; paste the source the model needs; mechanical half in `check`, judgement half in `expect` | lmstudiorunner `SKILL.md` and `references/task-cards.md` (this repo, as read at 97f9997) | 2026-10-01 |
| Entity-visual brief shape | Diffusion prompts carry intent only; size, steps and model are the runner's budget and test run; pixel-art briefs are pixelsmith's spec block, which comfyrunner executes | comfyrunner `SKILL.md` and `references/pixel-contract.md`; pixelsmith `references/briefing.md` (this repo, as read at 97f9997) | 2026-10-01 |
| Drafting context from canon | A per-task context pack within a token budget for drafting | story-skills issue #257 (R3 scan) | 2026-09-28 |
| Chunk size and gleaning | Smaller chunks find more entity references; a gleaning round feeding found entities back recovers recall at larger chunks; defaults 1,200 tokens, overlap 100, one gleaning | arxiv.org/html/2404.16130v2 (GraphRAG paper); github.com/microsoft/graphrag `config/defaults.py` | 2026-10-01 |
| Grounding by literal quote | Drop any finding whose quote is not literally in the text sent; one call per chapter with only the entities it names; partial results name skipped chapters | github.com/007jedgar/Ciciro PR #96 | 2026-10-01 |
| Chapter split | Headings, setext titles, plain "Chapter N" lines, Prologue/Epilogue/Interlude, natural file order; name candidates from repeated capitalised words | story-skills `docs/cli-reference.md` (import) | 2026-10-01 |
| story-skills JSON report | `story continuity --json`: `code`, `file`, `chapter`, `message`, `severity`, `exemption`, `exemptionIndex`; errors exit 1 | story-skills `docs/continuity.md` | 2026-10-01 |

| Scene shape and beats | A scene brief carries its shape (how one value moves) and a short ordered beat list, so a drafting model does not invent the turn | Idea from Matt Pocock's `writing-beats` and `writing-shape` skills, named on a 2026-10-08 review of popular public skills; the shape table and beat rules in `generation-briefs.md` are this skill's own | 2026-10-08 |

Ideas only: no incumbent text or code is copied. The bible layout is adopted as an input format (story-skills, MIT); lorescribe reads it and adds its own fields.

## Platform facts

Dated platform limits the reference files point at instead of restating. Calendar surface with this file (90 days); re-read both pages when it ages out, or sooner when a fan-out fails at a limit.

| Area | Fact | Source | Checked |
|---|---|---|---|
| Subagent fan-out | Subagents run in parallel; the Agent tool fails past 20 concurrent subagents in a session by default; subagents may nest up to three layers | code.claude.com/docs/en/sub-agents | 2026-10-01 |
| Dynamic workflows | `agent()`, `pipeline()`, `parallel()`, a `schema` per agent; up to 16 concurrent agents by default; no mid-run input; the Workflow tool is withheld from subagents; format as read on this date | code.claude.com/docs/en/workflows | 2026-10-01 |

## Parity register

Incumbents (scan 2026-09-28, re-check 2026-10-01):

| # | Incumbent | Link | Checked |
|---|---|---|---|
| L1 | story-skills — Claude Code plugin, about 22 skills, `story` CLI with a deterministic continuity engine, MCP server, series canon inside one repo | github.com/danjdewhurst/story-skills | 2026-10-01 (issues #288–#304: binaries, author-sample prose compare, reader panel, series deaths in progression; none adds game-media fields, cross-repo canon, branching canon or naming rules) |
| L3 | team-narrative — five-agent narrative orchestrator with canon levels | github.com/Donchitos/Claude-Code-Game-Studios | 2026-09-28 |
| L4 | narrative-continuity-checker — check only, no bible | github.com/mimir-dm/mimir | 2026-09-28 |
| M2 | Novilot — hosted paid app (Anthropic API): suggests bible entries from a manuscript, flags contradictions with both passages quoted and a suggested fix | novilot.com | 2026-10-01 |
| M5 | Ciciro — per-chapter continuity check against a hand-kept canon, parallel with a cap, drops ungrounded findings | github.com/007jedgar/Ciciro | 2026-10-01 |
| M6 | Claude-Book — `book-analyzer` extracts a bible from a whole book in one read, chapter-level evidence; `bible-merger` lets the later book win | github.com/ThomasHoussin/Claude-Book | 2026-10-01 |
| — | Others scanned: loremaester (TTRPG vault + retrieval), directory prompt skills (story-bible-architect and similar), worldbuilding MCP servers, World Anvil / Campfire / Obsidian (human apps) | see R3 scan | 2026-09-28 |

Parity table:

| Line | vs L1 | vs L3 | vs L4 | Eval case |
|---|---|---|---|---|
| Canon store in plain Markdown + YAML | met | met | beaten | T1 |
| Deterministic continuity engine (frontmatter: promises, clocks, routes, custody) | out of scope (its report is read as evidence: `manuscript.py evidence`) | met | met | T2 (checklist output), T27 |
| Timeline and state progression | met | beaten | met | T2, T8 |
| Naming rules — generate and test | beaten | beaten | met | T4, T7 |
| Canon levels | beaten | met | beaten | T9 |
| Cross-medium fields (art, audio, in-game text) | beaten | met | beaten | T5 |
| Generation briefs from canon, checked on return | met for prose (L1 context packs feed drafting, and its engine checks the result); beaten for art and timeline visuals (L1 is manuscript-first) | met (assumed from R3's scan: its narrative team drafts with canon levels; drafting output not read) | beaten (check only, no briefs) | T15-T21 |
| Shared canon across repos | beaten | beaten | out of scope (check-only tool) | T6 |
| Read-only on handed-in lore | beaten | beaten | met | T3 |
| Branch-conditional canon (story paths) | beaten (no branch model) | beaten | beaten | T26 · native `branch-leak` |
| Drafting prose, beta reads, manuscript builds | out of scope (not a canon keeper's job) | out of scope | out of scope | trigger N2 |

Manuscript mode, against M1 (story-skills), M2 (Novilot) and M6 (Claude-Book):

| Line | vs M1 | vs M2 | vs M6 | Eval case |
|---|---|---|---|---|
| Split a manuscript into chapters | met | met | beaten | script test `test_single_manuscript_file_splits...` |
| Extract entities and facts from prose | beaten (names only) | met | met | T22 · native `trigger-manuscript-extract` |
| Chunk plan for book length, resumable ledger | beaten | unknown (closed app) | beaten ("read source completely") | T25 |
| Provenance per fact (`<file>:<line>` + quote) | beaten | met | beaten (chapter only) | T22 |
| Grounding (quote re-found by a script) | beaten | unknown | beaten | script tests `GroundTests` |
| Contradiction with both citations | beaten (one side, chapter level) | met | beaten (later book wins) | T23 · native `ms-self-contra` |
| Write gate | beaten (agent edits files) | met | beaten | T24 · native `ms-no-write-before-yes` |
| Plain files, offline, no credits | met | beaten | met | — |
| Suggested fix for a contradiction | out of scope | out of scope (lorescribe never edits text; line edits are commscribe's) | out of scope | native `nearmiss-line-edit-chapter` |
| Re-run only changed chapters, re-anchor moved quotes | beaten | unknown | beaten | T25 · script tests `RehashTests` |
| Parallel per-chapter extraction | beaten | unknown | beaten | T28 |

Margins:

1. **Cross-medium canon** — visual tags and a motif line on every entity; briefs are checked like chapters. Since 0.2.0 it runs both ways: briefs go out to local text and image runners and what comes back is checked. Cases T5, T15-T21, native `brief-contra`, `brief-story-slice`, `draft-contra-flagged`, `absent-runner-text`, `timeline-chart`.
2. **Franchise canon across repos** — universe bible, per-project pins, `PIN-DRIFT`. Fills story-skills issue #242 (one repo per book breaks link checks). Case T6, native `pin-drift`.
3. **Naming rules as generator plus test** — phonology, forbidden clusters, folds, near-duplicates, pronunciation key. Cases T4, T7, native `name-variant`.
4. **Grounded manuscript provenance** — every extracted fact carries `<file>:<line>` and a quote a stdlib script has re-found; ungrounded rows never reach a proposal. No skill or product read does both (M5 grounds but keeps no bible). Cases T22, script `GroundTests`.
5. **Two-sided contradictions into canon levels** — `SELF-CONTRA` cites both lines; the user picks, and the loser can stay as `rumour` or `retired`. Cases T23, native `ms-self-contra`.
6. **Incremental re-run** — changed chapters only, by hash; moved quotes re-anchored. Case T25, script `RehashTests`.
7. **Branch-conditional canon** — facts per story path, checks per path, `BRANCH-LEAK`. Case T26, native `branch-leak`.

Iterate proposals:

- Manuscript: measure model entity recall at 1,200 vs 3,000-token chunks with `manuscript.py score` on a seeded fixture, by a model that has not seen the answers; change the default only on that figure.
- Manuscript: a sound-fold option in `collate` that reads a culture's folds from `names/<culture>.md`.
- Branches: draw one timeline chart per path on request.
- Canon store: an `audit` health count per kind, so drift is visible over time.
- Naming: per-culture stress rules in the pronunciation key.
- Canon levels: a `CANON-LOG.md` in single-project bibles too, not only universes.

Retire condition: retire lorescribe if story-skills (or a successor) ships both game-media fields (art and audio tags) in its entity schema and cross-repo series canon. Then point users to it and keep only `names-method.md` as a reference. Retire manuscript mode alone (keep the reference) if story-skills ships prose-fact extraction with line provenance into its frontmatter; lorescribe then reads that through interop.

Verdict: **PARITY + MARGIN** for game, franchise and manuscript projects (manuscript margin rests on `scripts/manuscript.py`; without Python, grounding is manual and that line is GAPS). L1's engine stays the tool for frontmatter promise, clock, route and custody checks.
