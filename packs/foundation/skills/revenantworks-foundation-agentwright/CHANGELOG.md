# Changelog — revenantworks-foundation-agentwright

## [1.0.0] — 2026-10-01

2026-10-08 (K8 fix round): the description says it never schedules or runs what it designs (trigger row #18's exclusion); Emit states why it stays model-invocable (audit K7-1-19, -21).

2026-10-08: description cut to about 600 characters, main use case first; trigger phrases and seams kept (routing proof: K9 evals).

First public release. Designs and audits the system around an autonomous or scheduled agent,
everything but the prompt text, and renders it into the surface that runs it.

### What it does

- A ten-area control checklist: cadence, soft and hard guardrail tiers, kill-switch layers,
  protected resources, handoff schemas, output contracts, the zero-signal rule, failure and retry,
  injection hygiene, and trust tiers.
- Design: a new agent from intent, sized to its blast radius, as a complete ops spec behind one gate.
- Emit: renders a spec into the target's native form (a Cowork task, a Claude Code routine, a desktop
  scheduled task, a CI job), states the enforcement gap for every control that surface cannot hold,
  and carries the three invariants no scheduler's form asks for: the zero-signal line, the first
  actionable fire and missed-run behaviour. A request with no spec runs design first.
- Audit: a 1–10 score per area and a P0/P1/P2 finding catalog for an existing agent, prompt or spec;
  naming one area gives a spot-check of that area alone.
- Trust tiers: the untrusted-content rule for agents that read email, web pages or documents.
- Every routine spec lists the repo paths its prompt reads (`reads:`); an audit flags a branch
  that deletes or renames one, and the consumer moves before the merge.
- Loop pacing (fixed cron, dynamic wake or in-session `/loop`, with interval floor, ceiling and
  pass cap) and a drafted objective for long goal-driven runs (outcome, done check, non-goals,
  budget, stop-and-ask, progress file), both in checklist area 1; a scheduled platform sweep runs
  scoutwright `since` then `fit`, proposing trials for the owner's yes.
- Refresh: re-verifies the dated platform notes (enforcement layers, schedulers, kill-switch and
  injection state, the emit targets), with per-row stamps so only rows actually reached are
  restamped.

### Entry points

- `design` (default), `emit`, `audit`, `refresh`. "apply all" or "just spec it" skips the gate.

### Safety rules

- Never schedules, enables, runs or commits what it emits; hands it back paste-ready.
- Never emits something that only looks safe: every unenforceable control is named.
- Writes only on emit and refresh. Ships no code; behaves the same on claude.ai, Claude Code and the
  API.

### Integrations

- Prompt text is promptwright's; standing config a person reads in session, rigwright's; skill
  packages, skillwright's; what a built agent may do at runtime, gatewarden's scan.
- Optional mods: `privacy` (received and untrusted markers) and `dash` (task pane); they never
  block.
