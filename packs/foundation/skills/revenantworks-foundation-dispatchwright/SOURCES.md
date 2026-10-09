# Sources — revenantworks-foundation-dispatchwright

Last verified: 2026-09-28 (the parity register below; upkeep reads this stamp, 90-day cadence).

## Contents

- Parity register — the incumbents, the parity rows, the margin, what is owed
- Prior-art read — orchestrate-skill and deliver, ideas only
- Surface sources — the degradation table in README.md
- Lineup source — the tier table's model row
- Internal sources
- Unsourced by design
- Unit review and decision map — idea credits (2026-10-08)

## Parity register (dated 2026-09-28; 90-day cadence)

The incumbents that do part of this skill's job. The pages were fetched on 2026-09-26 for the
parity audit; the two prior-art repos were fetched again on 2026-09-28. Re-check them before
claiming a capability no incumbent has.

| Key | Incumbent | Checked | Licence / state | What it does |
|---|---|---|---|---|
| **O** | [Casey-Stewart/orchestrate-skill](https://github.com/Casey-Stewart/orchestrate-skill) | 2026-10-01 | MIT | A committed file ledger with git as the truth; a per-batch scope fence checked by `git diff --name-status`; a fresh read-only reviewer that maps every diff hunk to a batch item; file-disjoint batches in worktrees; a metrics token per row; resume by reconciling against git; a fail-first check on fix batches; since 2026-09-27 a compaction window, reviewer at effort max and a four-line implementer reply (BL-064). Green means the local integration tip, not remote CI; no non-git reversal field. |
| **S** | [obra/superpowers — subagent-driven-development](https://github.com/obra/superpowers/blob/main/skills/subagent-driven-development/SKILL.md) | 2026-09-26 | No licence shown on the fetched page | A fresh subagent per task, a two-stage review (spec, then quality), a progress ledger as the recovery map, role-based model choice, a tier-up after repeated fix rounds; never runs implementers in parallel |
| **T** | [Claude Code agent teams](https://code.claude.com/docs/en/agent-teams) | 2026-09-26 | First-party, experimental | A shared task list with dependencies and locked claiming, task hooks, a model per teammate; teammates inherit the lead's effort; no resume of in-process teammates, no nested teams |
| **B** | [pmcbride/claude-cost-control](https://github.com/pmcbride/claude-cost-control) | 2026-09-26 | Public repo, self-tested hooks | A budget adjunct: hooks on agent launch escalate across the 5-hour window and block new spawns at 80%. Pacing is now pacewright's; B stays here only for the window rows |
| — | [deliver (josteinhanssen/skills)](https://github.com/josteinhanssen/skills) | 2026-09-28 | MIT | A ticket-batch delivery skill: a carry list, a token target per ticket, explicit tools per agent, report word caps, two reviewers, risk tags answered in the commit |
| — | [shanehaynes/apex-training PR 319](https://github.com/shanehaynes/apex-training/pull/319) | 2026-09-26 | Public PR | Supporting evidence: shared resources classed as partition, serialize or orchestrator-owned; a lane-declaration hook; a lessons ledger |
| — | [Agent Skills best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) | 2026-09-26 | First-party docs | The authoring bar: a short body, references one level deep, a contents list on long references, no time-sensitive text, at least three evaluations |

**Parity rows** (the 2026-09-26 audit's table; the dispatchwright column re-read from this
package's files at 1.4.0, not re-audited):

| # | Core-job capability | Audit 2026-09-26 | At 1.4.0 |
|---|---|---|---|
| 1 | Shape check — is this a fan-out at all | beaten | beaten |
| 2 | Decompose — boundaries, stop conditions, sizing | beaten | beaten |
| 3 | Per-unit model tiering | met | met |
| 4 | Effort binds to the executor | missing | met — through an agent definition (tier-routing.md) |
| 5 | Committed ledger, git as truth | met | met |
| 6 | Resume from real state | met | met — row repair to `unverified` stated |
| 7 | Scope fence by `git diff --name-status` | missing | met — `files_allowed` per row |
| 8 | Independent per-unit review | missing | met — fresh context, every hunk mapped |
| 9 | Parallel writers in one repo on disjoint files | missing | met — disjoint `files_allowed` and worktrees |
| 10 | Per-row actuals in fixed form | missing | met — `actual` and `rework` |
| 11 | Test ratchet | met | met — fail-first stated |
| 12 | Plan-time fit to the usage windows | beaten | moved to pacewright; §6 keeps a fallback |
| 13 | Live usage throttle | missing | met — §6 live gate, pacewright's budget file |
| 14 | Reconcile against origin and CI | beaten | beaten |
| 15 | Escalation ladder | beaten | beaten |
| 16 | Durability — commit per piece, identity check, smallest return | beaten | beaten |
| 17 | Inter-agent messaging, self-claiming tasks | out of scope | out of scope — hub and spoke, because reconcile needs one controller |
| 18 | Waiting on long jobs without polling | missing | met — unit-brief-template.md |

**Margin held on 2026-10-01** (re-scanned live by unit PR; no incumbent above has it). Margin 1, the plan-time window fit,
moved to pacewright with the split. The rest stay here:

2. Reconcile credits a row only on green remote CI, re-derives gate figures from raw counts, and
   checks the test total against a baseline expectation.
3. An identity check covers the push and every later API step, and the row records the controller
   split.
4. A `reversal` field is required for every landed non-git change.
5. Shared content is enumerated before a document set is split across parallel writers.
6. The skill degrades cleanly on a surface with no tools (README.md — Surface support).

**Owed:** the margin cases (evals/test-cases.md, Cases 18–22) have one simulated run each; see
evals/RESULTS.md for what that run can and cannot prove. A live run is still owed.

Injection check, 2026-09-28: no fetched page addressed an agent reader. No incumbent's text is
copied here; practices are restated in this skill's own words.

## Prior-art read — ideas only

Both repos were read on 2026-09-28 for ideas only; no text was copied (the pack's policy for
MIT prior art is the same as for unlicensed prior art: restate, never paste).

- **orchestrate-skill (MIT).** Already matched here: the ledger, the scope fence, fail-first,
  worktrees, resume by git. Taken as ideas: the hunk-to-item reviewer (now §7 and tier-routing.md).
  Candidates, not applied: a merge-tree dry run plus a suite re-run on the integration branch when
  several writers stack on one branch; fence-bounce and round counts in the `actual` cell.
- **deliver (MIT).** Already matched: a state file (the ledger), explicit tools per unit (the
  brief's tools field), short returns (the brief's return shape). Candidates, not applied: a carry
  list for open items between waves; a token target per unit checked against `actual`; risk tags
  that the unit answers in its commit; a Decisions section in the commit body; a confirm pass only
  after a blocking finding. A two-reviewer check is worth its cost only on high-risk units.

## Surface sources

The surface table in README.md is sourced from these pages, fetched 2026-09-28 as raw Markdown
where the host serves it:

- https://code.claude.com/docs/en/skills
- https://code.claude.com/docs/en/sub-agents
- https://code.claude.com/docs/en/hooks
- https://code.claude.com/docs/en/statusline
- https://code.claude.com/docs/en/agent-sdk/overview
- https://code.claude.com/docs/en/agent-sdk/subagents
- https://code.claude.com/docs/en/agent-sdk/skills
- https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
- https://support.claude.com/en/articles/12512180-use-skills-in-claude

## Lineup source

| Source | Checked | Used for |
|---|---|---|
| [Models overview](https://platform.claude.com/docs/en/about-claude/models/overview) (raw `.md`) | 2026-09-28 | `references/tier-routing.md` — the model-name row and the API default-effort line (Sonnet 5.5, `claude-sonnet-5-5`, default effort `high`) |

## Internal sources

| Source | Applies to | Key guidance |
|---|---|---|
| The user's lessons page from one large multi-agent rebuild (`handbook/lessons-2026-08-17-rebuild.md`, a private repo) | §5 Durability contract, §6 Wave execution, §7 Escalation, §9 Anti-patterns; `references/anti-patterns.md` | Each lesson names a concrete failure from a real run: one tier for all work, a commit lost at the end, two writers on one repo, a read-only pass that wrote, a result that overflowed context, self-reports that did not match reality. This skill is the enforcement for the fan-out lessons. |
| `revenantworks-foundation-promptwright` — `references/model-snapshot.md` | §4 Tier; `references/tier-routing.md` | The four tiers, the effort-before-tier ladder and the living-table rule. **A one-time copy made 2026-09-14; independent since.** `dispatchwright refresh` re-verifies this skill's copy against the provider's models page, never against promptwright. |
| `revenantworks-foundation-rigwright` — the layer-placement stack | §1 Scope and seams | Which layer (CLAUDE.md, a hook, a permission rule) makes the trigger fire is rigwright's call, quoted rather than re-argued. |
| `revenantworks-foundation-agentwright` and the pack router file — the attended-vs-unattended line | §1 Scope and seams | A same-session fan-out is in scope here; anything unattended is agentwright's, whole. |
| The task-observer log (observation ids cited in the body and references) | Every rule that names an observation | The ids are provenance, not names. The incident behind each rule is in `references/doctrine-cases.md`. |

## Unsourced by design

The numeric caps in §6 (six concurrent units, two nesting levels, a twelve-unit split line) and
the durability mechanics in §5 (a local commit per piece, controller-batched pushes, the ledger
checkpoints) are doctrine authored from the user's runs, not drawn from a published orchestration
standard. They are declared here so the gap is visible rather than implied.

## Unit review and decision map (added 2026-10-08)

Ideas only, written in this skill's own words; no text copied. Not re-fetched for this change.

- The two-stage review, spec conformance before quality — obra/superpowers
  `subagent-driven-development` (incumbent **S** above).
- The worktree per writer and the hunk-mapped fresh reviewer were already here — Casey-Stewart/
  orchestrate-skill (incumbent **O** above).
- The decision map — an owner-approved idea list (2026-10-08); no outside text.
