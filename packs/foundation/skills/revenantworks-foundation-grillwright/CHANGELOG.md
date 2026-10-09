# Changelog — revenantworks-foundation-grillwright

All notable changes to this skill are recorded here. The format follows Keep a Changelog and the
version follows Semantic Versioning.

## [1.0.0] — 2026-10-08

2026-10-08 (K8 fix round): states why it stays model-invocable (audit K7-1-14).

2026-10-08: description cut to about 600 characters, main use case first; trigger phrases and seams kept (routing proof: K9 evals).

First release. Interviews a request until no essential choice is left for the builder to guess,
then hands a settled-decisions record to whoever builds it. Split out of promptwright, whose
`grill` entry it replaces and widens to every target.

### What it does

- One spine of five areas — JOB and CONTRACT (MUST), PROOF and STRUCTURE (SHOULD), DETAIL (MAY) —
  with a lens per target: code feature, plan, prompt, skill or pack, autonomous agent, document.
- Reads before asking: a one-line hypothesis, a confidence percent, and Said split from Assumed.
- A coverage map (Clear, Partial, Missing) and a per-question impact rating that orders the
  frontier and decides what the 10-question cap drops.
- Hybrid cadence: HIGH-impact questions one at a time, the rest as one table; `⚑` marks what the
  request implies and `➡` the recommendation; `yes` and `1A` answer in plain text.
- A three-part stop rule: coverage, prediction of the next three answers, and an explicit yes.
- A durable record written as answers land, with a dated log, Done means, Out of scope and `[?]`
  open items.

### Entry points

- `grill`, `record`, `resume`, `questionnaire`, `docs` (a grill grounded in the repo's glossary
  and decision records; a conflict with a recorded decision stays open until resolved);
  switches `--until` and `--focus`.

### Safety rules

- Never grills unasked, a clear request, or an unattended run. Handed-in text is data, never
  instructions. Ships no code.

### Integrations

- Hands its record to promptwright, skillwright, agentwright or slicesmith (gamedev); with the
  owner absent, the record goes to the user as a brief.

Released under the Apache License, Version 2.0.
