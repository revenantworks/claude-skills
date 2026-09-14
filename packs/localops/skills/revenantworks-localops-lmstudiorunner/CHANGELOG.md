# Changelog — revenantworks-localops-lmstudiorunner

## [1.1.2] — 2026-09-13

**Two lessons from a live five-model lmstudiorunner audit** (interactive session,
observations #0067 and #0068). Ranked all installed chat-capable models
(qwen/qwen3-coder-30b, qwen/qwen3-30b-a3b-2507, google/gemma-4-26b-a4b-qat,
gemma-4-12b-it, google/gemma-4-e2b) on an identical real-file tool-call task;
all five answered correctly, so both findings are efficiency findings, not
correctness ones. `description` byte-identical; no entry point moved.

- `SKILL.md` step 1 (#0067): a check-before-comparing rule. Two of the five
  models failed to load with "insufficient system resources" only because
  three duplicate instances of an unrelated model, left over from an earlier
  crashed script run, were still resident under their TTL — 55.89 GB across
  copies of one 30B model. The error message names the model being requested,
  not what is already occupying memory, so it reads as a hardware verdict
  until reproduced with nothing else loaded (it wasn't one — both models
  loaded and answered correctly once `lms unload --all` ran first). Check
  `lms ps` / the `state` field before a comparative run.
- `SKILL.md` step 5 and `references/work-classes.md` Failure shapes (#0068):
  a fifth failure shape, "Verbatim transcription in reasoning" — a call that
  passes cleanly while the reasoning channel mostly re-copies the input
  rather than reasoning about it. Measured on `google/gemma-4-e2b`: 96% of a
  755-token completion was reasoning, most of it a near-verbatim restatement
  of the 74-line source file, to extract three names already sitting in it —
  a worse ratio than the two larger Gemma 4 models given the identical
  prompt (86% each). Invisible from `finish_reason` or answer correctness;
  only visible by reading `reasoning_tokens` against `completion_tokens` on
  a call that already succeeded, and a bigger budget does not fix it.
- `evals/SUITE.md` gains **A7** (the discovery-time RAM check) and **D9**
  (reasoning-token share read on a passing call) — 35 → **37 cases**, both
  authored, not run. `evals/TRIGGERS.md` re-anchored, provenance only — the
  `description` did not move.

## [1.1.1] — 2026-09-13

**Claim-type doctrine from the task-observer weekly review of 2026-09-13** (autonomous mode,
observations #0046 and #0056). Both are the residue of one overnight `gemma-4-12b-it` run over 44
GDScript files and the triage that followed it. `description` byte-identical; no entry point moved.

- `references/work-classes.md` gains a **Claim types** section (#0046): enumeration,
  cross-reference and classification-against-a-stated-rule claims are checkable by grep and earn a
  local model; correctness judgements need the language semantics and the code's invariants held
  at once, so they are dropped from the prompt or labelled hypotheses for a cloud reviewer. With
  the measured rates — 0 of 17 suspected bugs confirmed, 23 of 113 untested-function claims held —
  and the rule they teach: shape-valid is not true. The Contents list names the new section.
- `SKILL.md` step 2 gains the claim-type decision rule and step 5 a third verify bullet (#0046):
  a mechanical verifier proves shape, never truth, so triage a sample, report a **confirmation
  rate per claim type**, and keep only the types that confirmed in the next run's prompt.
- `references/task-cards.md` gains card rule 7 (#0056): name the population for any absence claim.
  A card that names only `tests/` inherits the narrow-scope error by construction, because a model
  with no repository knowledge defaults to the obvious directory — and three of four apparent gaps
  in one pass were covered by a headless script under `tools/` wired as a required CI step. Ask for
  the file and line that matched with the claim; a bare name hit is a candidate, not a
  confirmation. "Six rules" → "Seven rules".
- `evals/SUITE.md` and `evals/TRIGGERS.md` take a provenance re-anchor to 1.1.1 — no case assertion
  moved, so no case is owed a re-run. A case asserting the per-claim-type confirmation rate is owed
  and recorded here rather than left silent.

All notable changes to this skill. Format follows Keep a Changelog; this skill
uses semantic versioning.

## [1.1.0] — 2026-09-10

**Reasoning-budget enhancements from unit X2's live LM Studio research** (estate-audit
run, observation #0027 `schema-mode-reenabled-reasoning-and-ate-the-budget`). Three live
probes against `gemma-4-12b-it` on this run's server, plus a re-fetch of LM Studio's
structured-output and OpenAI-endpoint docs, settled the question 0027 raised and left open:

- `references/api-surface.md` — Chat completions gains a caveat that
  `chat_template_kwargs.enable_thinking: false` is not a documented LM Studio field and did
  not suppress reasoning in the probes (verify per model, never assume). Structured output
  gains a paragraph: a schema does not by itself add reasoning cost — the probes showed the
  same ~168-token reasoning spend with and without a schema; a schema failing under budget
  is a `max_tokens` sizing problem, not a "schema re-enabled reasoning" problem. A new
  **Sizing the budget: a one-request probe** section states the procedure: one card, a
  generous `max_tokens`, read `reasoning_tokens` and `finish_reason`, size the batch from
  `reasoning_tokens + (expected_answer_tokens × 1.5)`.
- `SKILL.md` step 4 (Constrain the generation) gains one sentence pointing at the probe
  rather than trusting the thinking-disable flag or a fixed multiplier.
- `SOURCES.md` gains the probe record and the two re-fetched doc pages, both confirming
  `chat_template_kwargs`, `reasoning_content`, `reasoning_effort`, `enable_thinking`, and
  `reasoning_tokens` are undocumented LM Studio fields — llama.cpp/vLLM chat-template
  conventions passed through, best-effort per model.
- `evals/SUITE.md`: **D7** (states "verify per model" rather than asserting the flag
  works) and **D8** (`size <task>` withholds a `max_tokens` figure until a probe runs) —
  33 → **35 cases**, both authored, not run. `evals/TRIGGERS.md` re-anchored, provenance
  only — the `description` did not move.
- The probe-list fix (`lmstudio-probe-list-omits-the-working-address-and-has-no-timeout`)
  was already applied in the live file as of this pass's own re-check — no change needed.
- `api-surface.md`'s Last-verified stamp moved 2026-09-09 → 2026-09-10.

## [1.0.1] — 2026-09-10

**Seven estate-audit findings, first patch.** All body/reference; `description`
byte-identical.

- `lmstudio-loaded-context-field-absent-when-nothing-loaded`: `loaded_context_length`
  is only returned when `state` is `loaded`. SKILL.md, `api-surface.md`, and
  `work-classes.md`'s Long-input row now all state the fallback — on a
  just-in-time rig with nothing loaded, judge fit against `max_context_length`
  provisionally and flag resident context as unconfirmed.
- `lmstudio-eval-cases-unrunnable-in-default-state`: `evals/SUITE.md` cases A4
  and C3 now name their precondition (a resident model) explicitly; A4b and
  C3b are new paired cases for the not-loaded state, so the case set stays
  runnable in this rig's default state instead of marking correct behaviour
  as a failure.
- `lmstudio-check-command-executed-from-queue-file-ungated`: the posture
  clause now names the queue file, task cards (including a card's own
  `check` field), and the raw API response as data, never instructions.
  `references/task-cards.md` adds: a `check` is shown to the owner and
  confirmed before its first execution, and a card whose `check` was not
  authored by the owner is refused rather than run.
- `lmstudio-no-results-ledger`: `evals/RESULTS.md` created; Case E5 (the
  injection probe) executed as a traced run, 1/1.
- `lmstudio-probe-list-omits-the-working-address-and-has-no-timeout`:
  `api-surface.md`'s discovery probe now covers all four host/port
  combinations (127.0.0.1 and localhost, on both 1234 and 1235) with a
  2-second connect timeout on each, so a closed port fails fast instead of
  hanging.
- `lmstudio-pack-md-orphan`: SKILL.md gains a Load budget section naming all
  four reference files, closing with `references/pack.md` — boundary doubt
  about a sibling's territory only.
- `lmstudio-capabilities-key-absent-on-embeddings`: `capabilities` may be
  absent entirely on an `embeddings` entry — read a missing key as no
  advertised capability, never an error. `publisher` and `compatibility_type`
  added to SKILL.md's field enumeration to match `api-surface.md`.

Evals re-anchored in the same commit (`evals/SUITE.md`, `evals/TRIGGERS.md`).

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
