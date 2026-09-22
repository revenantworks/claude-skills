# Model Snapshot — Volatile Data *(single update surface)*

> **Last verified: 2026-09-22** — all five vendor columns re-verified live against the primary sources below and cross-checked against the LiteLLM registry (occasion: Claude Opus 5.5, released 2026-09-22). Rows marked *not re-verified* keep their earlier date. This is the **only** file to edit when model lineups change — durable routing logic lives in `model-notes.md` §2 and never needs touching for a lineup update. If today is more than 60 days past this stamp and the output names a specific model, verify against the canonical sources below first (one or two searches). **A lineup can also move inside the window** (estate finding `promptwright-model-snapshot-stale-frontier-string`, 2026-09-10) — the calendar cadence catches staleness by age, not by event; when in doubt whether the roster in front of you is current, a quick check against the canonical sources costs one search. If verification isn't possible, recommend by tier name ("current Claude balanced tier"), never a possibly-retired model string. To regenerate this file, say **"promptwright refresh"** (procedure in SKILL.md → Entry — Refresh).

---

## Current tier map *(verified 2026-09-22)*

| Tier | Claude *(default)* | OpenAI | Gemini | Grok (xAI) | DeepSeek |
|---|---|---|---|---|---|
| **S — frontier** | Fable 5.1 | GPT-6 Astra⁴ | —² | Grok 4 Heavy¹ | V4 Pro |
| **A — flagship** | Opus 5.5 | GPT-5.6 Sol | Gemini 3.1 Pro² | Grok 4.7³ | V4 Pro |
| **B — balanced** | Sonnet 5 | GPT-5.6 Terra | Gemini 3.8 Flash | Grok 4.3 | V4.1-Flash |
| **C — fast** | Haiku 4.5 | GPT-5.6 Luna | Gemini 3.5 Flash-Lite | Grok 4.3 (the 4.20 non-reasoning variant, same rate, when latency rules) | V4.1-Flash (non-thinking mode) |

¹ Consumer product only (the SuperGrok Heavy subscription) — not an API model; *not re-verified 2026-09-22* (API docs only). xAI's own API guidance now points at Grok 4.7, "the most capable model we've built." Never recommend gated or limited-availability models (Claude Mythos 5.1, Mythos 5 and Mythos Preview are all limited availability) as defaults.
² **Gemini 3.5 Pro is still not available** (announced at I/O May 2026; absent from the Gemini API model list and the pricing page on 2026-09-22) — never recommend it until it ships. Gemini's S slot is effectively empty; 3.1 Pro (Feb 2026, still served under the `-preview` id) is their top recommendable model.
³ Grok 4.7 (xAI's current recommendation), 4.6 and 4.5 carry a **500K context — smaller than Grok 4.3's 1M**; pick 4.3 when the window matters more than the newest weights. Grok 4.1 Fast is not on xAI's model list — do not recommend it. `grok-build-0.1` (256K) is listed without positioning; not routed here.
⁴ **GPT-6 Astra** is OpenAI's own start-here pick and "most capable model for complex end-to-end work." GPT-5.5 Pro is still listed and not deprecated, but at 3× Astra's price it is no longer the S pick.

---

## Relative cost bands *(within vendor, cheapest → priciest)*

| Vendor | C | B | A | S |
|---|---|---|---|---|
| Claude | ¢ Haiku | $ Sonnet | $$ Opus | $$$ Fable |
| OpenAI | ¢ Luna | $ Terra | $$ Sol | $$$ 6 Astra (2.5× Sol — try Sol at `xhigh`/`max` first) |
| Gemini | ¢ Flash-Lite | ¢–$ 3.8 Flash | $ 3.1 Pro | — |
| Grok | ¢–$ 4.3 | ¢–$ 4.3 | $ 4.7 | consumer sub |
| DeepSeek | ¢ V4.1-Flash | ¢ V4.1-Flash | ¢–$ V4 Pro | ¢–$ V4 Pro |

**Pricing quirks worth flagging:** Claude Opus 5.5 is $4/$20 — below Opus 5 and 4.8 ($5/$25) — and its cache hits bill at 0.05× input ($0.20/MTok); Fable 5.1 is $10/$50 with cache hits at 0.025× ($0.25/MTok); every other Claude model reads cache at 0.1×. Sonnet 5's $2/$10 launch price is the standard price (the increase to $3/$15 scheduled for 2026-09-01 was cancelled). Opus 5.5 fast mode bills $8/$40 (Claude API only). Gemini 3.8, 3.7 and 3.6 Flash bill $0.75/$3.75 through 2026-12-31 and double on 2027-01-01; Gemini 3.1 Pro doubles input and lifts output ×1.5 on prompts over 200K tokens; Gemini 3.1 Flash-Lite ($0.25/$1.50) undercuts 3.5 Flash-Lite ($0.30/$2.50) and is the vendor's price floor. OpenAI's 5.x and 6 lines charge a long-context premium on prompts over 272K tokens (2× input / 1.5× output for the full request); GPT-5.6 and later bill cache *writes* at 1.25× and reads at 0.1×, with a 1,024-token minimum and a cache life of at least 30 minutes; GPT-5.5 Pro ($30/$180) has no cached-input discount. Grok 4.7, 4.6, 4.5 and 4.3 double their rates at 200K tokens and above. DeepSeek's off-peak rates are half of peak (hours on its pricing page) — V4.1-Flash is the cheapest capable model anywhere. Gemini 3.8 Flash, Grok 4.3, and the whole DeepSeek line deliver near-flagship capability at budget prices — the reason routing goes by required capability, not by price.

---

## Context / output quirks *(verified 2026-09-22)*

- Claude: 1M context on Fable 5.1, Opus 5.5, Sonnet 5 (and the Opus 5 / Opus 4.6–4.8 / Sonnet 4.6 legacy tier); **Haiku 4.5 200K**. **128K output** on Fable 5.1, Opus 5.5 and Sonnet 5; Haiku 64K. 300K output on the Batch API via a beta header on Opus 5.5, Opus 5, Sonnet 5 and the 4.6–4.8 line — **not on Fable 5.1**. Claude 4.7-and-later models use a tokenizer that bills ~30% more tokens for the same text than Sonnet 4.6-era models — budget for it. Adaptive thinking is always on and cannot be disabled on Fable 5.1 and Opus 5.5; Opus 5.5 also rejects forced `tool_choice` (`any` / `tool`).
- OpenAI: GPT-6 Astra and the GPT-5.6 family (Sol/Terra/Luna) are **1.05M context / 128K output**; GPT-5.5 Pro shares that window.
- Gemini: 1,048,576-token input / 65,536-token output across 3.8 Flash, 3.7 Flash, 3.6 Flash and 3.1 Pro (registry figures — Google's models page no longer prints limits); **3.8 Flash** (stable, built for "long-horizon software engineering, autonomous agents") is the workhorse; **3.5 Flash-Lite** is the fastest 3.5 model and 3.1 Flash-Lite the price floor.
- Grok: **the flagships (4.7, 4.6, 4.5) carry 500K; the cheaper 4.3 and 4.20 variants carry 1M** — the smaller model has the bigger window. Check before assuming newest = biggest.
- DeepSeek: `deepseek-flash` now serves **V4.1-Flash** (the `deepseek-v4-flash` ids are retired but still routed to it at the Flash price); V4 Pro (0813) is unchanged. Both are 1M context / 384K output, thinking on by default with a non-thinking mode.

---

## Reasoning-depth parameter names

| Vendor | Parameter |
|---|---|
| Claude | `effort` (low / medium / high / xhigh / max; **default high, except Opus 5.5 — default medium**; xhigh on Fable 5.1, Opus 5.5, Opus 5, Opus 4.8/4.7 and Sonnet 5; max on the 4.6 generation and later; Haiku 4.5 has no effort control) |
| OpenAI | `reasoning_effort` (none / low / medium / high / xhigh / max on the 5.6 family; low–max on GPT-6 Astra, no `none`) |
| Gemini | `thinking_level` (low / medium / high on 3.8 and 3.7 Flash; `minimal` added on 3.6 Flash, 3.5 Flash and 3.5 Flash-Lite; default medium on most 3-series) |
| Grok | 4.20 ships reasoning and non-reasoning variants; reasoning-by-default on the flagships *not re-verified 2026-09-22* |
| DeepSeek | thinking mode on by default, non-thinking mode for chat-style work — both on V4 Pro and V4.1-Flash |

---

## Canonical sources *(verify here, in this order)*

**Primary — vendor model docs** (URLs are durable even as contents change):

| Vendor | URL |
|---|---|
| Anthropic | https://platform.claude.com/docs/en/about-claude/models/overview (pricing: `/about-claude/pricing`; effort: `/build-with-claude/effort`) |
| OpenAI | https://developers.openai.com/api/docs/models (pricing: `/api/docs/pricing`) |
| Google | https://ai.google.dev/gemini-api/docs/models (pricing: `/gemini-api/docs/pricing`) |
| xAI | https://docs.x.ai/developers/models |
| DeepSeek | https://api-docs.deepseek.com/quick_start/pricing |

**Cross-check — machine-readable registries** (community-maintained; may lag brand-new launches — vendor docs win conflicts):

- LiteLLM model/price/context registry: https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json
- OpenRouter live model availability: https://openrouter.ai/api/v1/models

---

## Refresh procedure *(summary — full procedure in SKILL.md → Entry — Refresh)*

Say **"promptwright refresh"** → the skill re-verifies the tier map, cost bands, and quirks against the sources above, regenerates **this file only** with a new Last-verified stamp, adds a dated CHANGELOG line, bumps the patch version (re-anchoring the evals), ends with a **seen, not applied** line for any doctrine-level change it saw, and (on claude.ai) hands back a repackaged skill to reinstall. Cadence: on the 60-day stamp, or whenever a major model launches.
