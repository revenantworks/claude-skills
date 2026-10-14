# Changelog — revenantworks-foundation-promptwright

## [1.0.0] — 2026-10-01

2026-10-08 (K8 fix round): states why it stays model-invocable; an edge note in the trigger evals routes a standalone suite to skillwright `evals` (audit K7-1-09, -11).

2026-10-08: description cut to about 600 characters, main use case first; trigger phrases and seams kept (routing proof: K9 evals).

2026-10-08: model-snapshot.md names Haiku 5.5 (`claude-haiku-5-5`) in the tier map, context/output, effort and per-model rows; lineup rows and stamp only.

First public release. Builds, scores, hardens, red-teams and optimizes prompts into copy-paste-ready
artifacts, and picks which model tier runs a prompt or task.

### What it does

- A seven-phase build: intake, analyze and score, pick a structure, clarify (only when genuinely
  ambiguous), build, re-score and self-check, output.
- Scores on five dimensions (clarity, specificity, context, completeness, structure) as a
  before-and-after delta; every prompt leads with a plain TL;DR and a mandatory Model line.
- A framework menu carried in the skill (CO-STAR, RISEN, TIDD-EC, BAB, RTF/APE, Chain of Thought,
  Agent/System): a named framework is honoured, otherwise promptwright picks.
- A hostile read on every draft: the prompt as a maximally literal, bad-faith reader takes it.
- An excuses table beside the 15 self-checks (in `anti-patterns.md`), naming the reasons a build
  skips them.
- Hardening for injection resistance and production guardrails.
- A fast path for genuinely small prompts with published exit conditions; a quiet build collapses
  the phases into one trace line. The 15 self-checks and the hostile read always run.
- Restraint rules that refuse to build prompts that should not exist.
- An opt-in offline HTML prompt card with a mandatory Run on section.
- An optional discernment note for prompts that give a person factual answers: one line naming
  where to check the claim that matters most, never an invented citation.
- A new model's per-class fit is scoutwright `fit`'s; a tier change still goes only through
  Refresh.

### Entry points

- `build`, `improve`, `score`, `red-team`, `model` (a tier and the cheapest clearing model for a live
  task or a plan's subtasks), `optimize` (measured runs against a 3–8-case slice with one holdout;
  can emit promptfoo or GEPA/DSPy configs as text), `slim` (cuts a prompt's tokens with behavior
  held constant: lossless rungs apply, lossy cuts gate, counts name their method), `refresh`
  (re-verifies the model snapshot).
- A grill asked for by name is grillwright's; its settled-decisions record replaces Phase 4.

### Safety rules

- Model names come from a dated snapshot with a 60-day staleness rule; past the stamp it verifies
  before naming a model, or recommends by tier name, never a possibly retired string.
- Ships no code; web search only for an external fact a prompt needs and for refresh.

### Integrations

- Routes Claude and local open-weights models; another hosted vendor gets a vendor-neutral prompt.
- Fan-out tiering is dispatchwright's, installed local models lmstudiorunner's, skill packages and
  their slim skillwright's, standing config and its slim rigwright's, a sourced model comparison
  researchscribe's, a handoff handoffwright's, a requirements interview grillwright's. Runtime
  output cutting is left to external tools (caveman, rtk), named as optional.
