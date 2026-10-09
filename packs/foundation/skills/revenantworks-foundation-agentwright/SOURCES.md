# Sources

Where this skill's guidance comes from, and who else does its job. Current platform facts live in `references/platform-notes.md` behind their own stamp; this file records provenance and the parity register.

Last verified: 2026-10-01 (parity re-scan of the register below: AR and AGT re-read, LO and BR added; SCH not re-fetched and keeps 2026-09-26; upkeep reads this stamp, 90-day cadence).

## Doctrine sources

| Source | Guidance drawn |
|---|---|
| Anthropic — Agent Skills best-practices + overview docs (platform.claude.com, re-read 2026-09-26) | Body/reference split, description routing, body under 500 lines, one-level references, a contents list past 100 lines, eval-driven iteration. |
| Agent Skills open standard — https://agentskills.io | Frontmatter, naming/description limits. |
| Anthropic — finance-agents reference architecture (anthropic.com/news/finance-agents) | Trust tiers: quarantined reader, deny-by-default tools, schema-validated boundaries, centralized connector access. |
| ironclaw / shellward agent-security review guides | Code-level threat review — cited as adopted references; not duplicated here. |
| Production guardrail practice (kill-switch layering, permission/approval/audit/kill framing; build-time research 2026-07-12) | Soft-vs-hard tiering, kill-switch drill, cap-as-number rule. |

The checklist encodes control doctrine (durable). `references/platform-notes.md` is their stamped, calendar-class companion.

## Parity register (dated 2026-10-01; 90-day cadence)

The incumbents that do part of this skill's job, what each covers, and where this skill stands. Re-check before claiming a capability no incumbent has. This register supersedes the 2026-07-12 niche verdict, which called the corner uncontested; the 2026-09-26 re-audit of that ceded corner found three real incumbents (observation #0190).

| Incumbent | Licence / origin | Covers | Verdict |
|---|---|---|---|
| **AR** Agentic Radar — https://github.com/splx-ai/agentic-radar | Apache-2.0 (re-read 2026-10-01) — **idea source only**, no text copied | Static scan of framework-agent workflows: workflow graph, tool and MCP-server enumeration, findings mapped to the OWASP LLM and agentic lists, runtime adversarial tests. No kill-switch, cadence or schedule design | Ahead on the graph and runtime probes. The runtime scan it competes with moved to gatewarden `scan` on 2026-10-01; agentwright's design and emit margin is untouched |
| **AGT** Microsoft Agent Governance Toolkit — https://opensource.microsoft.com/blog/2026/04/02/introducing-the-agent-governance-toolkit-open-source-runtime-security-for-ai-agents/ | MIT, 2026-04-02 — **idea source only** | Runtime policy engine that intercepts each action, execution rings, an emergency kill switch, grading across all ten OWASP agentic risks, ten framework integrations. No design-time spec, cadence, zero-signal line or scheduler rendering | Runtime infrastructure, so it is named as a hard-tier mechanism for framework agents (`platform-notes.md`), not rebuilt |
| **SCH** Anthropic `/schedule` + the routines docs — https://code.claude.com/docs/en/routines.md | First-party Claude Code | Creates, updates, lists and runs routines in conversation; reads a run's log to explain tool errors and denials (v2.1.227) | Creation is the platform's. Emit drives it: a Claude Code routine hand-back carries one `/schedule` line and a post-create check |
| **LO** claude-mods `loop-ops` — https://github.com/0xDarkMatter/claude-mods (skills/loop-ops) | MIT — **idea source only** | Outer-loop design across session cron, desktop tasks and cloud routines: risk tiers L1–L3 with the host as part of the tier, a state/run-log/budget spine, a mandatory kill switch checked by `loop-check`, heartbeat staleness, one catch-up for the latest missed window | The nearest rival (found 2026-10-01). It covers the kill switch, missed-run catch-up and a per-host tier; it has no enforcement-gap table, no kill-switch verify read or absence proof, no zero-signal line, no restraint verdict at emit |
| **BR** pm-claude-skills `blast-radius-drill` — https://github.com/mohitagw15856/pm-claude-skills | MIT — **idea source only** | A worst-case drill before go-live: caps, kill switch, reversibility, isolation, a recovery runbook | Covers the blast-radius-first framing; no schedule, cadence or target rendering |

**Ideas borrowed** (cited, not copied): the effective tool surface read from a run log (AR's enumeration, SCH's run-log reading) became Audit-only question 4; the per-meter cost of a routine (SCH's usage-and-limits section) became checklist areas 1 and 6; the `/schedule` hand-back line comes from SCH.

**Margin re-scanned 2026-10-01 (narrowed).** LO and BR now cover a kill switch per loop, a missed-run catch-up rule and a blast-radius drill. Still no incumbent has: ten control areas with never-pad excusal; an enforcement-gap table per target, thin targets named as thin; one kill-switch verify read per target with the stop order and one-minute absence proof; the zero-signal line and first actionable fire on every emitted schedule; the restraint rule and the surface-is-wrong verdict at emit; the regeneration-guard question; terminal conditions read from loaded state, hold-and-announce; the audit-only questions no scanner asks.

**Adopted 2026-10-01 from LO** (idea only, cited, no text or code copied): the heartbeat-staleness check, now a named control in `design-checklist.md` area 7.

**Adopted 2026-10-08** (owner-approved estate review; ideas only, restated in our own words, no text or code copied): loop pacing — the cron / dynamic wake / `/loop` pick with interval floor, ceiling and pass cap — from the `ralph-loop` pattern (a prompt re-run until a scripted check passes) and the community `loopify` skill; the long-run objective draft (outcome, done check, non-goals, budget, stop-and-ask, progress file) from Trail of Bits' `goal-prompt` skill (https://github.com/trailofbits/skills). All three named in the review; this unit did not re-fetch them. Both now sit in `design-checklist.md` area 1.

**Moved, 2026-10-01 (owner Q3):** the runtime security scan, with its data-flow diagram and probe plan (audit P1-14, P2-2), is gatewarden's `scan`; agentwright keeps two spec questions from it (Audit-only 5 and 6). **Out of scope by choice:** runtime enforcement (the platform's), prompt hardening (promptwright's), compliance grading.

## Re-checking

`agentwright refresh` re-verifies `references/platform-notes.md` and restamps that file only. This register is re-checked on its own 90-day stamp: re-read each incumbent's page, update the Covers and Verdict cells, and restamp the line above.
