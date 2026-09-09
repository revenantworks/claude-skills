# Changelog — revenantworks-localops-lmstudiorunner

All notable changes to this skill. Format follows Keep a Changelog; this skill
uses semantic versioning.

## [1.0.0] — 2026-09-09

First release. First member of the `localops` pack.

### Added

- **Two modes with a stated difference.** Interactive work recommends a check;
  unattended work requires one and is refused without it. The skill states the
  mode and the reason every time it proposes work, because the distinction is
  about who reads the result and when — not about how big the task is.
- **Live model audit.** Reads the running LM Studio native API for each
  model's `type`, `arch`, `quantization`, `state`, context lengths and
  `capabilities`. No model name is written anywhere in the skill, so the
  guidance cannot go stale as models change.
- **The loaded-context check.** Compares `loaded_context_length` against
  `max_context_length` and reports a divergence unprompted. A model loaded far
  below its ceiling silently truncates long input and nothing in the
  OpenAI-compatible endpoint reveals it.
- **Work classes and a four-question scoring pass**, so a task can be scored
  before anything is delegated — and often answered with "do this yourself".
- **Capability classes** matched from live metadata rather than model names;
  where nothing installed fits, the skill describes the shape needed.
- **Structured output preferred over post-hoc validation**, with the limit
  stated: a schema constrains shape, never content.
- **Named failure shapes** with distinct diagnoses — empty answer from budget
  exhaustion on a reasoning model, looping from atomic saturation, passing but
  wrong, and instruction over-compliance.
- **Task cards** as the unit of delegated work, each carrying its own check.
- Trigger evals (18 fire / 12 do not / 6 boundary pairs) and a 30-case
  assertion suite.

### Notes

The doctrine here is measured, not assumed. The numbers that appear in the
reference files — 2,053 reasoning tokens for eight lines of output, 649 slots
containing 60 distinct values, 168 unique results from a compositional request
in the same session — come from real runs against a local model, and are
recorded with the conditions that produced them.

Two incumbents were reviewed before building: `IsmaelMartinez/delegate-local`,
which already routes by capability tier and audits against hardware, and
`TerminalSkills/skills` `lm-studio-subagents`, which hardcodes its recommended
models. Both verify lightly and run in-session. This skill's claim is the
unattended, checked path and the live-metadata model audit; see SOURCES.md.
