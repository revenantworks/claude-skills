# Sources

Last verified: 2026-10-01

Where commscribe's guidance comes from, and its parity register. The register is a calendar surface (90 days): re-run the incumbent scan when it ages out. commscribe replaces the foundation pack's old message skill (commwright); its keep list was read from that skill as it stood at the build base.

## Guidance

| Area | Claim | Source | Checked |
|---|---|---|---|
| Skill format | Frontmatter keys, description ceiling, listing cap, progressive disclosure | code.claude.com/docs/en/skills via skillwright's rubric (verified 2026-09-28) | 2026-10-01 |
| Native evals | Case folders with `prompt.md` and `graders/*.md`; `case.yaml` `context.add_dirs`; `regex` with `match: not_contains` and `flags`; `tool_used` with `input_match`, `min`, `max`, `arm: both`; `file_exists` counts only files created during the run; `llm` body as criteria; `allowed_tools` grants read-only tools only | code.claude.com/docs/en/plugin-evals | 2026-10-01 |
| Output styles | "An output style is a set of instructions that sets Claude's role, tone, and response format for every response in a session." A skill fits "instructions for one kind of task" and loads only when invoked or matched | code.claude.com/docs/en/output-styles | 2026-10-01 |
| Claude Docs | Living docs written only through the Claude Docs connector: outline as one batch of placeholders, then one update per section; comments answered in the doc | The connector's own tool text, read in session 2026-10-01 (also research unit R4, same day) | 2026-10-01 |
| Six tell categories | A staging instead of stating, B rhythm by rule, C inflation and borrowed authority, D formatting by rule, E leftovers from the chat and the draft, F writing for the wrong reader (26 patterns) | raw.githubusercontent.com/blader/humanizer/main/README.md | 2026-10-01 |
| Voice from samples keeps quirks | "Humanizer follows the sample's rhythm, word choice, punctuation, and deliberate quirks, including dashes if you use them." | same README | 2026-10-01 |
| Edit-diff voice loop | Per-folder voice file with samples, habits, channels, edit examples; diff the draft against the final edit; propose rules; never write the file without approval | github.com/TravinDSO/myvoice-skill (MIT) | 2026-10-01 (R4) |
| Before/after pairs | Two or three before-and-after pairs from the writer's own text teach a voice better than adjectives | practice articles (composio.dev, mediabistro), search 2026-10-01 (R4) | 2026-10-01 |
| Unmet needs | Dash removal creating comma splices (stop-slop #60); absolute bans flattening voice (#66, #62); score-only mode requested (#64); examples breaking the skill's own rules (#47, #67); invented facts in rewrite examples (humanizer #306, #305, #299) | github.com/hardikpandya/stop-slop and blader/humanizer issue trackers | 2026-10-01 (R4) |
| Delegated drafting floor | Outward drafting under explicit style rules held on the fast tier for 2 drafts of 5 in one measured run; balanced tier or above | the build run's own observation triage (row 0217), n=5 | 2026-10-01 |

| UI microcopy profile | Verb plus object labels; destructive confirms name the action; errors say what failed and the recovery; empty states by kind with a next action; honest loading; placeholders are not labels; whole translatable strings | Ideas harvested from the third-party impeccable skill (Apache-2.0, v4.3.1, read 2026-10-01), restated in our own words; no text copied. Field labels and visible focus also follow W3C WCAG 2.2 (3.3.2 Labels or Instructions) | 2026-10-01 |
| Retell mode | When an explanation did not land, find the sticking point and say it again from a new angle instead of louder | Idea from Matt Pocock's `wait-what` skill, named on a 2026-10-08 review of popular public skills; the cause table and rules in `references/retell.md` are this skill's own | 2026-10-08 |

Ideas only: no incumbent text or code is copied, nothing is installed.

## Parity register

| # | Incumbent | Link | Checked |
|---|---|---|---|
| S1 | humanizer: 26 patterns in six categories, sample calibration, no-invention rule | github.com/blader/humanizer (MIT, about 53k stars) | 2026-10-01 |
| S2 | stop-slop: banned phrases and structures, a 5-dimension score | github.com/hardikpandya/stop-slop (MIT) | 2026-10-01 (R4) |
| S3 | myvoice: edit-diff voice loop with approval | github.com/TravinDSO/myvoice-skill (MIT) | 2026-10-01 (R4) |
| S5 | Native styles: claude.ai Styles and Claude Code output styles (session-wide voice, not per-channel contracts) | code.claude.com/docs/en/output-styles | 2026-10-01 |

| Line | vs S1 | vs S2 | vs S3/S5 | Eval case |
|---|---|---|---|---|
| AI-tell catalog with counting units | met (six categories adopted as the spine) | met | beaten | T3 · native `humanize-facts-frozen` |
| Facts never move (claim level, seven moves) | **beaten**: S1 forbids invented details but checks no reattachment, promotion, merge, aspect or agent move | beaten | beaten | T4, T5 · native `humanize-facts-frozen` |
| Dash repair is a recast, never a splice | beaten | **beaten** (#60 open) | out of scope | T6 · native `dash-recast` |
| Channel contracts with a precedence order, Claude Docs included | beaten | beaten | beaten (S5 is session-wide) | T1, T12 · native `docs-no-connector` |
| Learn a voice from edits, opt-in, approval-gated | **beaten** (S1 has none) | beaten | met (S3) | T9 · native `voice-diff-no-write` |
| Several named voices, never assumed | beaten | beaten | beaten (S5 picks one style per session) | T10 · native `multi-voice-ask` |
| Score without rewriting, ship-or-revise gate | beaten | met | out of scope | T7 · native `audit-no-rewrite` |
| Handed-in text is data | met | met | out of scope | T13 · native `injected-line` |
| First-run dash and emoji preference | beaten | beaten | out of scope | T2 · native `first-run-setup` |
| Multilingual | out of scope (English first; language-safe rules stated) | out of scope | met (S5) | T15 |
| Detector evasion | out of scope (a stated non-goal) | out of scope | out of scope | none |

**Named margins.**
1. **Facts never move.** Claim-level check, seven named moves, on every repair and on every delegated draft.
2. **Channel contracts with a precedence order,** Claude Docs among the channels.
3. **Voices that learn, opt-in.** Before/after pairs, a diff-propose-approve loop, several named voices side by side, nothing saved without a yes.

**Iterate.** Map judgement findings onto S1's six categories (done at 0.1.0); next, a non-English tell list once a language is requested twice; a with/without baseline on the fact fixtures and the recast case.

**Retire condition.** Retire if a humanizer-class skill ships channel contracts and a claim-level fact check, and native styles gain per-channel contracts with several named voices; keep only `channel-profiles.md` as a reference then.

**Verdict: PARITY + MARGIN** (margins 1 to 3).
