# revenantworks-foundation-grillwright

grillwright interviews a request until nothing essential is left for the builder to guess, on
any target — a code feature, a plan, a prompt, a skill, an agent or a document. Other grill
skills each serve one target and hand off to their own next step. grillwright swaps a **lens**
over one fixed spine of MUST, SHOULD and MAY areas, and hands one builder-neutral
**settled-decisions record** to whichever skill builds next.

## Package

```
revenantworks-foundation-grillwright/
├── SKILL.md
├── README.md · CHANGELOG.md · SOURCES.md · LICENSE · NOTICE
├── references/
│   ├── grill.md     # every grill: spine, lenses, indicators, impact, question form, stop rule
│   ├── record.md    # record, resume, questionnaire, hand-off: the record's shape and log
│   └── pack.md      # sibling boundaries, read on boundary doubt only
└── evals/
    ├── trigger-evals.md · test-cases.md · RESULTS.md
    └── <case>/      # native `claude plugin eval` cases (prompt.md + graders/)
```

## Install

**claude.ai** — Settings → Capabilities → Skills, upload the zip.
**Claude Code** — the foundation plugin carries it; or drop the folder in `~/.claude/skills/`.

## Commands and switches

| Invocation | Does |
|---|---|
| `grillwright grill` or "grill me" | The interview, then the record and a routing line |
| `grillwright record` | Writes the record from what is already said, asking nothing |
| `grillwright resume` | Re-asks only the record's open `[?]` items |
| `grillwright questionnaire` | Questions for someone else to answer later |
| `--until MUST\|SHOULD\|MAY` | Ends once every area at that severity is clear |
| `--focus <area>` | Limits a round to the named areas |
| `yes` · `1A` · `SKIP GRILLING` | Take the recommendation · pick an option · stop and keep what was answered |

## What sets it apart

- **Facts are read, decisions are asked.** It never asks what a file or the repo can answer.
- **Hybrid cadence.** HIGH-impact questions one at a time; MEDIUM and LOW as one table.
- **Two marks per question.** `⚑` for what the request implies, `➡` for the recommendation.
- **A three-part stop rule.** Every MUST clear, the next three answers predictable, and an
  explicit yes — "sounds good" is recorded as assumed, not as agreement.
- **A durable record.** Written as answers land, with a dated log and `[?]` items that `resume`
  picks up in a later session, with no issue tracker required.
- **Restraint.** It refuses to grill a clear request or an unattended run.

## Boundaries

grillwright builds nothing. A prompt is **promptwright's**, a skill **skillwright's**, an
agent's guardrails **agentwright's**, game code **slicesmith's** (gamedev pack). What a running
agent may do is **gatewarden's** scan; a sourced comparison is **researchscribe's**.

## Staying current

`SOURCES.md` carries the dated parity register on a 90-day stamp; `skillwright upkeep` sweeps it
through `volatile.json`.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
