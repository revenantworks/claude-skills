# Tier routing — self-contained (dispatchwright's own copy)

> **Last verified: 2026-09-14.** This is the **only** file to edit when the Claude model lineup
> changes — the routing logic in this file (tiers, the effort ladder, role-based overrides) is
> durable and never needs touching for a lineup update. To regenerate the model-name row, say
> **"dispatchwright refresh"** (SKILL.md — Entry — Refresh). If today is more than 60 days past
> this stamp, verify the model names against `https://platform.claude.com/docs/en/about-claude/models/overview`
> before writing one into a ledger row — recommend by tier name ("current balanced tier") if you
> can't verify.
>
> Made self-contained 2026-09-14 (observation #0073, owner ruling): dispatchwright previously
> called promptwright's Entry — Model for every unit's tier row. The owner ruled that every
> foundation-pack skill that picks a model for its own recurring job should carry that logic
> itself rather than depend on a sibling skill's live output. This file is the result — dispatch's
> tiering no longer requires promptwright to be installed.

---

## The four tiers

| Tier | Claude model | When |
|---|---|---|
| **S — frontier** | Fable 5.1 | Failure is very costly; the hardest reasoning; longest-horizon agents |
| **A — flagship** | Opus 5 | Hard multi-step reasoning, complex agents, expensive-mistake analysis |
| **B — balanced** *(default)* | Sonnet 5 | Most writing, coding, analysis, summarization, agent work |
| **C — fast** | Haiku 4.5 | Classification, extraction, routing, high-volume or latency-bound work |

Start at B. Move up only when B genuinely can't hold the reasoning depth the unit needs; move
down when the unit is simple, high-volume, or latency-bound.

## Raise effort before tier

**The first lever is the `effort` parameter (low / medium / high / xhigh / max on Claude), not a
tier jump.** A tier change costs more per call than raising effort one notch, and most units that
"need a bigger model" actually need more thinking time on the one they're already assigned.
Escalate to the next tier only when a raised-effort attempt at the current tier still fails on a
verifiable signal (Escalation, §7) — never pre-emptively, and never because a unit "seems hard."

## Role-based overrides

- **A pure planning/orchestrator unit defaults one effort notch lower than its tier suggests.**
  High effort reliably over-thinks and scope-creeps a plan; raise it only once the plan fails to
  converge.
- **A review or verification unit changes model *family*, not just a fresh instance of the same
  model.** Checking another unit's output on the model that produced it tends to miss exactly what
  that model already rationalized away.
- **A verifier that only re-derives evidence already on disk defaults to balanced or fast tier at
  low or medium effort.** Re-reading a file to confirm a finding already made is not the same job
  as weighing the votes across a wave, and the top tier belongs to the judge, not to every voter
  re-checking its own homework. This has a budget form too: **verification costs less than the
  discovery it verifies** — a verification wave's estimated spend is stated beside the finding
  wave's, and effort is raised only on the rows that weigh evidence rather than fetch it.
- **A row that fans out to N agents (a Workflow/Task call spawning a wave) states the count and the
  effort those N agents inherit in the same row** — `subagent (workflow) ×N` — never a default the
  agents pick up from the session. One row hiding 245 agents once skipped both the wave cap and
  the usage-window check built to catch exactly that.

## Reading this table into a ledger row

Per unit: pick the tier from the table above by the work's actual demands (reasoning depth,
horizon, volume/latency, stakes — the same four questions any tier pick answers), apply the
role-based overrides above where they fit, then write `tier · model · effort · inline-vs-subagent`
into the ledger row (`references/ledger-schema.md`) — tiered before dispatch, never after. A unit
added mid-run gets a row through this same table before it launches, exactly as the living-table
rule (SKILL.md §4) requires.

## Sources

Model names and their tier mapping are copied from `revenantworks-foundation-promptwright`'s
`references/model-snapshot.md` as of this file's Last-verified stamp — a one-time copy, not a live
reference. The two files can drift after a refresh on either side; `dispatchwright refresh`
re-verifies this file's own row independently rather than re-reading promptwright's copy.
