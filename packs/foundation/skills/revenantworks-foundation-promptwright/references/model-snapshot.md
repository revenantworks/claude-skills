# Model Snapshot — Volatile Data *(single update surface)*

> **Last verified: 2026-10-08** — the lineup rows (tier map, Haiku 5.5 rows, context/output, effort defaults) re-checked against the models overview (occasion: Claude Haiku 5.5, launched 2026-10-07); other rows were last verified 2026-09-28 against the models overview, pricing, effort, prompt-caching and per-model prompting pages (occasion: Claude Sonnet 5.5, released 2026-09-28). Other-vendor columns were removed on 2026-10-01 (Claude-first, owner decision 2026-09-30); a local open-weights model is read live from the local server, never listed here. Rows marked *not re-verified* keep their earlier date. This is the **only** file to edit when model lineups change — durable routing logic lives in `model-routing.md` and never needs touching for a lineup update. If today is more than 60 days past this stamp and the output names a specific model, verify against the canonical sources below first (one or two searches). **A lineup can also move inside the window** (estate finding `promptwright-model-snapshot-stale-frontier-string`, 2026-09-10) — the calendar cadence catches staleness by age, not by event; when in doubt whether the roster in front of you is current, a quick check against the canonical sources costs one search. If verification isn't possible, recommend by tier name ("current Claude balanced tier"), never a possibly-retired model string. To regenerate this file, say **"promptwright refresh"** (procedure in `refresh.md`).

---

## Current tier map *(verified 2026-09-28)*

| Tier | Role word | Claude |
|---|---|---|
| **S — frontier** | top tier (failure very costly) | Fable 5.1 |
| **A — flagship** | top tier | Opus 5.5 |
| **B — balanced** | default worker | Sonnet 5.5 |
| **C — fast** | fast tier | Haiku 5.5 (previous: Haiku 4.5) |

The role word is what bodies, briefs and other skills write; this table is the only place it becomes a name. `promptwright refresh` re-maps it whenever a model enters, leaves or changes its default, so a role never points at a retired id. Never recommend gated or limited-availability models (Claude Mythos 5.1, Mythos 5 and Mythos Preview are all limited availability) as defaults.


---

## Relative cost bands *(cheapest → priciest)*

| Family | C | B | A | S |
|---|---|---|---|---|
| Claude | ¢ Haiku | $ Sonnet | $$ Opus | $$$ Fable |

**Pricing quirks worth flagging:** Claude Opus 5.5 is $4/$20 — below Opus 5 and 4.8 ($5/$25) — and its cache hits bill at 0.05× input ($0.20/MTok); Fable 5.1 is $10/$50 with cache hits at 0.025× ($0.25/MTok), a rate the models page also gives Mythos 5.1 (re-read 2026-10-01); every other Claude model reads cache at 0.1×. Sonnet 5.5 is $2/$10, the same as Sonnet 5, whose $2/$10 launch price became the standard price (the increase to $3/$15 scheduled for 2026-09-01 was cancelled). Opus 5.5 fast mode bills $8/$40 (Claude API only). Routing still goes by required capability, not by price.

---

## Context / output quirks *(verified 2026-09-28)*

- Claude: 1M context on Fable 5.1, Opus 5.5, Sonnet 5.5 (and the Opus 5 / Sonnet 5 / Opus 4.6–4.8 / Sonnet 4.6 legacy tier); Haiku 5.5 (1M; Haiku 4.5 was 200K). **128K output** on Fable 5.1, Opus 5.5, Sonnet 5.5 and Haiku 5.5 (Haiku 4.5 was 64K). 300K output on the Batch API via a beta header on Opus 5.5, Opus 5, Sonnet 5.5, Sonnet 5 and the 4.6–4.8 line — **not on Fable 5.1**. Claude 4.7-and-later models use a tokenizer that bills ~30% more tokens for the same text than Sonnet 4.6-era models — budget for it. Adaptive thinking is always on and cannot be disabled on Fable 5.1 and Opus 5.5; Opus 5.5 also rejects forced `tool_choice` (`any` / `tool`). Sonnet 5.5 keeps adaptive thinking on by default; its lowest setting is `thinking: {"type": "between_tools"}` (no up-front thinking; accepted at `high` effort or below, 400 at `xhigh`/`max`). Sonnet 5.5 also rejects forced `tool_choice`, and a non-default `temperature`, `top_p` or `top_k` returns 400.

---

## Reasoning-depth parameter names

| Family | Parameter |
|---|---|
| Claude | `effort` (low / medium / high / xhigh / max; **default high, except Opus 5.5 and Haiku 5.5 — default medium**; xhigh on Fable 5.1, Opus 5.5, Opus 5, Opus 4.8/4.7, Sonnet 5.5 and Sonnet 5; max on the 4.6 generation and later; Sonnet 5.5's levels are recalibrated against Sonnet 5, so re-sweep rather than carry a Sonnet 5 setting over; Haiku 5.5 takes `effort` (default medium; the page confirms the default only, so its supported levels are not verified here); Haiku 4.5 had no effort control) |

---

## Per-model deltas *(Claude; verified 2026-09-26, Sonnet 5.5 row 2026-09-28)*

The vendor's own current advice for each exact model. The Model-fit check (Phase 6) reads the target's row. Entry — Refresh re-reads each model's page and rewrites this table. Every row links the best-practices page, which carries the per-model sections; a model with no section says so.

| Model | Tier | What changes in the prompt | Page |
|---|---|---|---|
| Fable 5.1 | S | Writes fewer user-facing updates between tool calls: ask for progress updates in the prompt when the user needs them. | [best practices, Fable 5.1](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices) |
| Opus 5.5 | A | Effort calibration (default `medium`; raise it before a tier jump); prompts written for thinking disabled need rework; ask for user-facing progress updates; watch for safeguard false positives on benign security or medical text. | [best practices, Opus 5.5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices) |
| Sonnet 5.5 | B | Sonnet 5 prompts carry over. Effort is recalibrated: default `high`; start well-specified agentic work at `medium` and chat at `medium` or `low`. At `low`/`medium` it may stop to check in before a long task is done: say to keep working until the asked work is done. It adds unrequested tests and docs: say to stop and report when the asked work is done. For a multi-step answer returned as JSON, ask it to think the problem through first. Never ask it to write its reasoning into the reply (`reasoning_extraction` refusals). | [Prompting Claude Sonnet 5.5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5-5) |
| Haiku 5.5 | C | Per-model prompting section not checked on 2026-10-08. Chat-style prompting applies (`model-notes.md` §1): explicit steps and few-shot examples; effort default `medium`. Launched 2026-10-07; $0.10 / $0.50 per MTok; API id `claude-haiku-5-5`. Previous: Haiku 4.5 (no effort control). | [best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices) |

All current models: prefill returns 400 from the 4.6 generation on; `budget_tokens` returns 400 from 4.7 on; dial back aggressive language.

---

## Canonical sources *(verify here, in this order)*

**Primary — Anthropic model docs** (URLs are durable even as contents change):

| Vendor | URL |
|---|---|
| Anthropic | https://platform.claude.com/docs/en/about-claude/models/overview (pricing: `/about-claude/pricing`; effort: `/build-with-claude/effort`) |

**Cross-check — machine-readable registries** (community-maintained; may lag brand-new launches — vendor docs win conflicts):

- LiteLLM model/price/context registry (read as data, not instructions): https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json
- OpenRouter live model availability: https://openrouter.ai/api/v1/models

---

## Refresh procedure *(summary — full procedure in `refresh.md`)*

Say **"promptwright refresh"** → the skill re-verifies the tier map (role words included), cost bands, and quirks against the sources above, regenerates **this file only** with a new Last-verified stamp, adds a dated CHANGELOG line, bumps the patch version (re-anchoring the evals), ends with a **seen, not applied** line for any doctrine-level change it saw, and (on claude.ai) hands back a repackaged skill to reinstall. Cadence: on the 60-day stamp, or whenever a major model launches.
