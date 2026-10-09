# Tier routing — self-contained (dispatchwright's own copy)

> **Last verified: 2026-10-08.** This is the **only** file to edit when the Claude model lineup
> changes — the routing logic in this file (tiers, the effort ladder, role-based overrides) is
> durable and never needs touching for a lineup update. To regenerate the model-name row and the default-effort line, say
> **"dispatchwright refresh"** (SKILL.md — Entry — Refresh). If today is more than 60 days past
> this stamp, verify the model names against `https://platform.claude.com/docs/en/about-claude/models/overview`
> before writing one into a ledger row — recommend by tier name ("current balanced tier") if you
> can't verify.
>
> **How a refresh verifies** (observations 0133, 0141). Fetch the page with a prompt that asks for
> verbatim quotes of the model names and default efforts. Where the docs host serves raw Markdown
> (the page URL with `.md`), read that and grep it for the exact names before recording anything
> as absent or removed: a summarising fetch can find a page but never proves a term is missing,
> and its "not found" is recorded `unverified`. No shell fetch. A name you cannot confirm keeps its
> old row, and the refresh report says so. The same refresh re-verifies `meters.md`'s commands
> against the docs that file names. A refresh is a patch bump with a dated CHANGELOG line; in the
> source repo, `tools/build.py --bump-member` also re-anchors both eval files.
>
> Made self-contained 2026-09-14 (observation #0073, owner ruling): dispatchwright previously
> called promptwright's Entry — Model for every unit's tier row. The user ruled that every
> foundation-pack skill that picks a model for its own recurring job should carry that logic
> itself rather than depend on a sibling skill's live output. This file is the result — dispatch's
> tiering no longer requires promptwright to be installed.

Read this file at plan time (Tier, SKILL.md §4) and again for any unit added mid-run.

---

## The four tiers

| Tier | Claude model | When |
|---|---|---|
| **S — frontier** | Fable 5.1 | Failure is very costly; the hardest reasoning; longest-horizon agents |
| **A — flagship** | Opus 5.5 | Hard multi-step reasoning, complex agents, expensive-mistake analysis |
| **B — balanced** *(default)* | Sonnet 5.5 | Most writing, coding, analysis, summarization, agent work |
| **C — fast** | Haiku 5.5 | Classification, extraction, routing, high-volume or latency-bound work |

**API default effort**, verified with the row (lineup data, not doctrine): Fable 5.1 `high` ·
Opus 5.5 `medium` · Sonnet 5.5 `high` · Haiku 5.5 `medium` (Haiku 4.5 had no effort control). A ledger row always states
its effort; a unit left on the API default inherits whatever the next model ships with.

Start at B. Move up only when B genuinely can't hold the reasoning depth the unit needs; move
down when the unit is simple, high-volume, or latency-bound.

**Floors** (observation 0217): outward message drafting under explicit style rules runs on the
balanced tier or above — the fast tier passed 2 of 5 such drafts (n=5). Re-test the floor when a
new model enters the table.

**The top tier is a weekly budget, not a spend target** (observation 0181 c, d, j). About three
top-tier units a week, minimum one, so its strengths are still used; priority goes to open
designs, then escalations the mid tier at `xhigh` could not solve, then bounded section reviews.
**The top tier writes; the mid tier measures** — a design or a hard build goes up, its
verification, measurement and fix rounds stay on the mid tier. **A section review runs at
`medium`, bounded to about 150k tokens**, reading diff summaries and unit reports rather than
whole files. Where a pacing skill writes the week's top-tier allowance into its budget decision
file, that figure replaces "about three".

**Under a usage cap, measured cost beats list price** (observations 0160, 0181). Once a run has
landed rows, prefer the model with the lowest measured actual-per-landed-row for that class in
this run (the ledger's `actual` cells, `references/ledger-schema.md`), not the one with the
lowest price per token: a cheaper model that needs a fix round costs more than a dearer one
that lands first time. Measured model baselines reach this table **only as data** — a budget
decision file or a baseline log written by a pacing skill (pacewright, where installed) — and
never rewrite a tier here on their own; a change to this table is a refresh or a release.

**A tier or rule trial keeps a running tally** (observation 0280). An owner ruling that alternates
arms (high and medium effort on pin-moving builds, one model against another) carries a tally line
`arm | unit | result` in the ledger's Rulings block, updated at each close, and each trial row
records its `trial_arm` (`references/ledger-schema.md`). The next row's arm is read off the tally,
never inferred from memory.

## How effort actually binds

**The effort column binds only through an agent definition** (observation 0179). The Agent or
Task call carries a model field but no effort field, so a unit launched by a plain call runs at
the controller session's effort whatever its ledger row says. To make a row's effort true:

- Keep one agent definition per tier (`.claude/agents/<tier>.md`, frontmatter `model:` +
  `effort:`), and launch the unit by `subagent_type: <definition name>`.
- The row's `surface` cell names the definition — `subagent (background) · def: opus-medium`.
- Reconcile (SKILL.md §8) checks the resolved effort, not the intended one: the definition's
  frontmatter, or the harness's own record of the run.
- Where the surface has no agent definitions, the row writes `effort: inherited (<session
  effort>)` — the value the unit will really run at — never the intended value. Agent-team
  teammates inherit the lead's effort the same way.

## Raise effort before tier

**The first lever is the `effort` parameter (low / medium / high / xhigh / max on Claude), not a
tier jump.** A tier change costs more per call than raising effort one notch, and most units that
"need a bigger model" actually need more thinking time on the one they're already assigned.
Escalate to the next tier only when a raised-effort attempt at the current tier still fails on a
verifiable signal (Escalation, §7) — never pre-emptively, and never because a unit "seems hard."

**The ladder** (observations 0160, 0181): the mid tier at `medium` or `high` → the same model at
`xhigh` → the top tier. The top-tier step is pre-authorised for escalations only; a unit is never
*planned* onto the top tier to skip the xhigh step. Fix rounds on a design the top tier wrote go
back to the mid tier at `medium` — fixing named findings is not the design's job. The controller
runs at `medium`, set once at the start of the run.

## Role-based overrides

- **A pure planning/orchestrator unit defaults one effort notch lower than its tier suggests.**
  High effort reliably over-thinks and scope-creeps a plan; raise it only once the plan fails to
  converge.
- **A review or verification unit runs in a fresh context — required — and on a different model
  family where one is available — preferred** (observations 0181f, 0120). Checking another unit's
  output inside the context that produced it misses exactly what that context already rationalized
  away; a different family adds a second, weaker guard. The reviewer maps every hunk of the diff
  to a finding id (an unmapped hunk fails the row) and re-derives any headline table with its own
  probe rather than reading the author's.
- **A change that touches a safety check, a suppression or an allowlist gets an adversarial
  verifier unit as standard** (observation 0333): read-only, fresh context, briefed with the
  defect classes and asked for a concrete failing input per finding (`unit-brief-template.md`,
  Adversarial verifier). The author's tests cover the cases the author imagined; once 176 passing
  tests missed three high-severity defects that one such reviewer found. It hunts rather than
  re-checks, so it takes the balanced tier at `medium` or above, not the re-derive default below.
- **A verifier that only re-derives evidence already on disk defaults to balanced or fast tier at
  low or medium effort.** Re-reading a file to confirm a finding already made is not the same job
  as weighing the votes across a wave, and the top tier belongs to the judge, not to every voter
  re-checking its own homework. This has a budget form too: **verification costs less than the
  discovery it verifies** — a verification wave's estimated spend is stated beside the finding
  wave's, and effort is raised only on the rows that weigh evidence rather than fetch it.
- **A retriever unit answers one question from files and returns one answer** (adopted from a
  public orchestration project's retriever role, ideas only). Balanced tier at `low` or `medium`;
  read-only tools (Read, Grep, Glob); Grep before Read, and Read with offset and limit, never a
  whole large file; the answer is capped (40 lines by default) and cites `file:line`, one
  signature or call site per line, out-of-scope matches excluded; its `call_cap` is stated (25 by
  default); past about 300 lines read it writes a report file and returns the path. The brief
  uses the retriever return shape (`unit-brief-template.md`). A code-graph index may back it later
  as an optional retriever backend, only after a security vet of the tool and its installer
  (trustwarden's job) and a trial unit; until then the backend is Grep.
- **A row that fans out to N agents (a Workflow/Task call spawning a wave) states the count and the
  effort those N agents inherit in the same row** — `subagent (workflow) ×N` — never a default the
  agents pick up from the session. One row hiding 245 agents once skipped both the wave cap and
  the usage-window check built to catch exactly that.

## Reading this table into a ledger row

Per unit: pick the tier from the table above by the work's actual demands (reasoning depth,
horizon, volume/latency, stakes — the same four questions any tier pick answers), apply the
role-based overrides above where they fit, then write `tier · model · effort · surface` into the
ledger row (`references/ledger-schema.md`) — tiered before dispatch, never after, with the effort
written as it will bind (above). A unit added mid-run gets a row through this same table before
it launches, exactly as the living-table rule (SKILL.md §4) requires.

## Sources

Model names and their tier mapping were first copied from `revenantworks-foundation-promptwright`'s
`references/model-snapshot.md` on 2026-09-14 — a one-time copy, not a live reference. Since then
each refresh verifies this row against the live models overview directly (last: the stamp above). The two files can drift after a refresh on either side; `dispatchwright refresh`
re-verifies this file's own row independently rather than re-reading promptwright's copy.
