# Sources — revenantworks-foundation-grillwright

Where this skill's guidance comes from, and how to re-check it.

Last verified: 2026-10-08 (the parity register; upkeep reads this stamp, 90-day cadence).

## The grill pattern

*Applies to: `references/grill.md`, SKILL.md — Entry — Grill.*

The pattern is ported from **`ase-task-grill`** in the ASE agentic-engineering framework by
Ralf S. Engelschall — https://github.com/rse/ase (Apache-2.0), read at
`plugin/meta/ase-common-grill.md` and `plugin/skills/ase-task-grill/SKILL.md`; first ported into
promptwright on 2026-09-09 and moved here on 2026-10-08. Re-read at v1.0.7 (HEAD 2026-10-07).

Taken: outside-in focus areas with severity fixed by area; the indicator list; sort-then-truncate
rounds at 10; grounded answers with the current option flagged; the skip exit; rounds restart
from the updated request; a per-question impact rating that orders an area and decides what the
cap drops; `--until` and `--focus`; open items saved as `[?]` and re-asked on resume.

Changed: the six code-plan areas became five target-neutral areas (JOB, CONTRACT, PROOF,
STRUCTURE, DETAIL) with a lens per target. ASE's all-questions-in-one-table cadence became a
hybrid: one at a time for HIGH impact, a table for the rest. ASE's task files, CLI, config system
and MCP server were not adopted.

## Docs-grounded grill (added 2026-10-08)

*Applies to: `references/docs.md`, SKILL.md — Entry — Docs.*

The idea of grilling against a repo's own glossary and decision records comes from Matt Pocock's
**`grill-with-docs`** skill in https://github.com/mattpocock/skills (MIT), named in the 2026-10-08
estate review. Taken as an idea only, in our own words: settled records answer questions before
they are asked, answers are checked against them, and new terms and hard-to-reverse choices are
offered back as additions. Added here: the keep / supersede / scope choice on a conflict, the
conflict as an open MUST item, and write-back only after an explicit yes. No text was copied.

## Anthropic guidance

| Claim | Source | Checked |
|---|---|---|
| Third-person what-and-when description; body under 500 lines; references one level deep | https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices | 2026-10-08 |
| A default plus an escape hatch rather than many options | same page | 2026-10-08 |
| At least three evals and a no-skill baseline before shipping | same page | 2026-10-08 |

## Parity register

*Volatile: declared in `volatile.json` (calendar, 90 days); `skillwright upkeep` re-checks it.*

Last verified: 2026-10-08. Ideas were taken as patterns; no code or text was copied.

| Incumbent | URL | Licence | Checked | Capability taken |
|---|---|---|---|---|
| mattpocock/skills `grilling`, `grill-me`, `grill-with-docs`, `to-questionnaire` | https://github.com/mattpocock/skills | MIT | 2026-10-08 | A recommended answer per question, `yes` accepts it; facts looked up, decisions asked; frontier ordering; glossary and decision-record additions as terms settle; the questionnaire for a third party |
| addyosmani/agent-skills `interview-me`, `idea-refine` | https://github.com/addyosmani/agent-skills | MIT | 2026-10-08 | Hypothesis and confidence percent; want-versus-should-want probe; "predict the next three answers" stop test; explicit yes, "sounds good" is not one; refuse non-interactive runs; Out of scope |
| github/spec-kit `/clarify` | https://github.com/github/spec-kit | MIT | 2026-10-08 | Coverage map Clear / Partial / Missing; full questions ending in `?` with a why-it-matters line; answers written into the artifact as they land with a dated session log |
| obra/superpowers `brainstorming` | https://github.com/obra/superpowers | MIT | 2026-10-08 | Read context before asking; classify weight and only move heavier; split oversized requests first |
| BMAD-METHOD `bmad-forge-idea` | https://github.com/bmad-code-org/BMAD-METHOD | MIT | 2026-10-08 | Append-only log that a later session resumes; an outcome that may be "not worth building" |

**Parity table**

| Line | Verdict | Reason | Case |
|---|---|---|---|
| One question at a time, grounded options | met | All five do it | C3 |
| Recommended answer, `yes` accepts | met | `➡` beside `⚑` | C3 |
| Facts read, never asked | met | Turn shape rule 1 | C2 |
| Explicit yes and anti-sycophancy | met | Stop rule part 3 | C5 |
| Durable, resumable record | met | `record.md`, `[?]`, `resume` | C7 |
| Severity tiers that a MUST can never leave open | **beaten** | Only ASE has them, and only for code plans | C4 |
| Target-typed lenses over one spine | **beaten** | Every incumbent serves one target | C1, C8 |
| Builder-neutral hand-off | **beaten** | Each incumbent hands only to its own next skill | C9 |
| Restraint on clear requests and unattended runs | **beaten** | addy refuses unattended runs; none pairs it with a written questionnaire | C10, C11 |

**Named margins.** (1) Lenses: one grill for six targets — case C8. (2) The three-part stop
rule — coverage, prediction, explicit yes — that no incumbent combines — case C5. (3) A record
any builder reads without knowing grillwright — case C9.

**Iterate.** Add a lens when a seventh target recurs in RESULTS. Measure whether the hybrid
cadence beats one-at-a-time on user turns per closed MUST. Watch spec-kit's question cap (5)
against ours (10).

**Retire condition.** Retire grillwright when one incumbent ships target lenses, a severity spine
and a builder-neutral record together; recommend that incumbent and route its record to the
foundation builders.
