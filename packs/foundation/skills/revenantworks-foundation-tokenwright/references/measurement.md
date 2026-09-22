# Measurement — Volatile Baseline *(stamped update surface)*

> **Last verified: 2026-09-22.** `tokenwright refresh` restamps this file: ratios, cache mechanics, and platform reference points drift with models and pricing; the taxonomy and doctrine in `waste-taxonomy.md` do not. Refresh's full scope — including the three platform values the SKILL body mirrors from here: cap, counting unit, listing budget — is stated in SKILL.md — Entry — Refresh. When the stamp is >60 days old, treat every number here as possibly stale and say so in reports.

## Contents

- Method ladder
- Estimation ratios
- Net-cost accounting
- Cache mechanics
- Platform reference points
- Model tier costs
- Honesty rules

---

## Method ladder

Highest available method wins; the report names which was used.

1. **Exact** — a real tokenizer or counting endpoint on the current surface (a code-execution surface with a tokenizer library installed; an API token-count endpoint). Label: `exact (<tool>)`. Different model families tokenize differently — an exact count is exact *for the named tokenizer*.
2. **Estimate** — character- or word-ratio arithmetic from the table below. The character/word count feeding that arithmetic must itself come from a **named counting method** — a language runtime's length function, a shell count, a script — stated alongside the number; never eyeballed, approximated, or recalled from a prior report. Label: `estimate (±15%, chars via <tool>)`. Show the arithmetic once per report (`chars ÷ ratio`), not per line item.
3. **Never** — word counts presented as token counts, counts with no stated method, or a character/word input with no named counting source (an eyeballed, approximated, or remembered figure dressed as `estimate (±15%)`). All three are report defects, and the last one is invisible to the ±15% band — a wrong count that happens to land inside the band still ships as fact unless the source is checked.

## Estimation ratios

| Content type | Ratio | Notes |
|---|---|---|
| English prose | ~4 chars/token · ~0.75 tokens/word | The default for docs, prompts, instructions |
| Source code | ~3–3.5 chars/token | Identifiers and symbols tokenize denser than prose |
| Dense markup (tables, JSON, YAML) | prose ratio, then add structural overhead | Pipes, braces, fences, and indentation are tokens too — a markdown table can cost 30–50% more than the same facts as terse lines |
| Non-Latin scripts | measure, don't assume | Chars/token runs materially lower; the prose ratio misleads |

Estimates carry a ±15% band. When a decision sits inside the band (an artifact "just fits" a budget on the estimate), say so and prefer an exact count before calling it fit.

## Net-cost accounting

- **Always-on text bills per turn.** Cost = size × turns in scope. A 300-token rule that trims 150 tokens of output per turn is profit; the same rule saving 20 is a loss by turn three. Every recommendation that *adds* instruction text states this arithmetic.
- **Tokens-per-task is the target, not tokens-per-request.** A larger one-shot that finishes beats a lean loop that retries — savings are counted across the whole task, including the re-prompts a too-aggressive cut causes.
- **A slim that costs behavior isn't a saving.** Re-prompting, corrections, and broken evals are token costs; the preservation contract exists because they usually exceed what the cut recovered.

## Cache mechanics *(rates and the per-model minimum-cacheable-length table re-verified live 2026-09-22)*

*Units: every number in this section is in **tokens**. Character limits — the description caps — live in Platform reference points below, and no threshold here is one.*

- **Caches hit on prefixes.** Stable content first, variable content last; anything ordered after a variable element does not cache. The high-hit order: system prompt → tool definitions → long static context → slow-changing context → the live request.
- **Anthropic:** explicit `cache_control` breakpoints (≤4 per prompt); cache writes bill ~1.25× the input rate for the 5-minute TTL, ~2× for the 1-hour TTL; reads ~0.10× (a ~90% discount) — **except Claude Fable 5.1 and Claude Mythos 5.1, whose cache hits and refreshes price at ~0.025×** the base input rate *(confirmed 2026-09-10)*, **and Claude Opus 5.5, whose hits price at ~0.05×** *(new 2026-09-22)*; the TTL refreshes on each read. **The claim that cache reads do not count against rate-limit utilization is now confirmed** at the primary source, cited under "When to use the 1-hour cache" — the prior stamp (2026-07-27) carried this unsourced and flagged it for re-verification; that flag is now closed. **Minimum cacheable length**: a prefix shorter than the model's floor never caches — `cache_control` is accepted and **silently ignored**, with no error. **Diagnose it on BOTH counters:** a prompt was not cached only when `cache_creation_input_tokens` **and** `cache_read_input_tokens` are both 0 — on a successful cache *read* the creation counter is also 0, so the one-field test misreads a working hit as "never cached".

  **The floor is per-model, not a single number or a smooth range — read the row for the model in scope** *(https://platform.claude.com/docs/en/build-with-claude/prompt-caching, fetched and verified 2026-09-22; applies on the Claude API, Claude Platform on AWS, Google Cloud, and Microsoft Foundry)*:

  | Minimum tokens | Models |
  |---|---|
  | 512 | Claude Opus 5.5 *(new 2026-09-22)*, Claude Opus 5, Claude Fable 5, Claude Mythos 5, Claude Fable 5.1, Claude Mythos 5.1 |
  | 1,024 | Claude Opus 4.8, Claude Sonnet 5, Claude Sonnet 4.6, Claude Sonnet 4.5, Claude Opus 4.1 (retired), Claude Opus 4 (retired), Claude Sonnet 4 (retired) |
  | 2,048 | Claude Mythos Preview, Claude Opus 4.7, Claude Haiku 3.5 (retired) |
  | 4,096 | Claude Opus 4.6, Claude Opus 4.5, Claude Haiku 4.5 |

  It does not track capability tier or release recency: the newest Opus tier (Opus 5.5, like Opus 5) sits at the *lowest* floor (512) while the previous Opus generation (4.6/4.5) sits at the *highest* (4,096), and Haiku 4.5 shares that same 4,096 ceiling with them. So tier, generation, or "it's the flagship/fast one" is never a proxy for the floor — name the model in scope and read its row; a single flat range invites assuming the low end applies pack-wide, which it does not. **OpenAI** *(re-verified live 2026-09-22 against its prompt-caching guide and pricing page)*: automatic caching; on GPT-5.6 and later (GPT-6 Astra included) the floor is 1,024 visible input **tokens** — a token threshold, not a character count, and not a cap on description length — reads bill 0.1× and writes 1.25× of input, and a cache lives at least 30 minutes after its latest write or reuse. GPT-5.4 and GPT-5.5 also read at 0.1×, with no cache-write charge; GPT-5.5 Pro has no cached-input discount at all. The old ~50% discount belongs to gpt-4o-era models (not re-checked).
- **The cache-safety corollary:** editing a cached artifact invalidates its prefix and forces one re-write. A slim is cache-positive when `(tokens saved × reads × read rate) > (rewrite cost)` — for hot prefixes that's almost always (a 5-minute Anthropic write breaks even inside one read), for rarely-read ones it may not be. Reordering *within* the stable block is free at the next write; interleaving anything volatile into it is the expensive mistake.
- **The floor gates that arithmetic.** Check the prefix against the minimum cacheable length before running it. Under the floor there is no cache to hit: the read saving is zero however hot the prefix looks, so the payback never lands. Report "below the minimum cacheable length — this prefix cannot cache" and name what it would take to clear the floor; never project a saving for a prefix that cannot cache.
- **Volatile facts belong in stamped, isolated files**, which is also what keeps the big stable body cacheable.

## Platform reference points

- **Skill metadata** (name + description) is always-on — measured discovery cost runs a median of ~80 tokens per installed skill (range ~55–235 across Anthropic's official skills), every session. The description is the one surface where thrift and routing compete; routing wins, then trim.
- **Description cap — 1,536 characters, per listing entry** *(added 2026-07-24; re-sourced to Anthropic's own docs 2026-07-25; re-confirmed verbatim 2026-09-10 and 2026-09-22)*. Counted in **characters, not tokens**: the skill listing sent to the model truncates each entry's routing text at Claude Code's `skillListingMaxDescChars`, whose default is 1,536. **Counting unit — `description` and `when_to_use` concatenated.** Anthropic's Claude Code skills documentation (`https://code.claude.com/docs/en/skills`) states this again on the 2026-09-22 read (raw page), same wording as 2026-07-25: "the combined `description` and `when_to_use` text is truncated at 1,536 characters in the skill listing," and "[when_to_use is] Appended to `description` in the skill listing and counts toward the 1,536-character cap" — SOURCES.md — Description cap. No member of this pack declares `when_to_use`, so for them the combined text is the description. The setting is user-configurable, so the figure drifts: this stamp is its source of truth, SKILL.md's Description cap rule mirrors it, and Refresh re-verifies the unit as well as the number (sync scope: SKILL.md — Entry — Refresh).
- **Skill-listing budget — 1% of the model's context window** *(added 2026-07-25; **re-confirmed 2026-09-22**, closing the 2026-09-10 caveat)*. A second, separate mechanism from the per-entry cap, as sourced 2026-07-25: the listing always carries every skill *name*; the descriptions are held to a budget that "scales at 1% of the model's context window" (`skillListingBudgetFraction`, or the `SLASH_COMMAND_TOOL_CHAR_BUDGET` environment variable), and on overflow Claude Code shortens descriptions to fit and then drops them starting with the least-invoked skills. **2026-09-22 re-check — confirmed at the primary source:** the troubleshooting section *"Skill descriptions are cut short"* is on the skills page with the quoted wording, and the settings reference (`https://code.claude.com/docs/en/settings-reference`) lists `skillListingBudgetFraction` (default `0.01`, "which reserves 1% of the context window") and `skillListingMaxDescChars` (default `1536`); the env-vars page gives `SLASH_COMMAND_TOOL_CHAR_BUDGET` a fallback of 8,000 characters. The 2026-09-10 "could not locate" result was a false negative from a summarizing fetch: this pass read the raw Markdown (`<page>.md`), which carries every term the summarizer reported absent, and the earlier checks read `/settings`, not `/settings-reference`. Read the raw page before recording an absence. `/skill-doctor` (Claude Code v2.1.252+) and `skillOverrides` (`"name-only"` entries list without a description) are the page's tools for freeing budget.
- **Skill bodies** load on trigger, not always-on, so their cost is per-invocation rather than a standing tax; the discovery layer is the always-on surface. Two separate measures, and conflating them is a real error: the **≤500-line norm** is the ecosystem spec (agentskills.io), while **token weight** is the truer cost and does not track line count — a dense 265-line body can outweigh a sparse 500-line one, which is why a flat token gloss fires on spec-compliant skills. Measure both, and where a body earns extra weight by carrying enforceable rules inline, declare the budget rather than mute the signal. References load on demand one level deep; that progressive-disclosure shape is still the reference architecture for any artifact set.
- **Tool/MCP schemas load whole and always** in most harnesses — documented sessions show five-figure always-on schema costs versus double-digit costs for an equivalent trigger-loaded skill. The strongest standing argument for conditional surfaces over resident ones.
- **Session floors are real:** agent CLIs commonly start tens of thousands of tokens deep (system prompt + instruction files + schemas + skill metadata) before the first user word. Budget sheets treat that floor as spent, not available.

## Model tier costs *(self-contained as of 2026-09-14, observation #0072/#0073 — no longer sourced from promptwright at report time)*

Cost scales with tier (frontier > flagship > balanced > fast). Bands, cheapest to priciest
within a tier, Claude (this pack's default vendor):

| Tier | Claude | Relative cost |
|---|---|---|
| **C — fast** | Haiku 4.5 | ¢ |
| **B — balanced** | Sonnet 5 | $ |
| **A — flagship** | Opus 5.5 | $$ |
| **S — frontier** | Fable 5.1 | $$$ |

Sonnet 5 is $2/$10 (input/output per million tokens); Opus 5.5 is $4/$20; Fable 5.1 is $10/$50;
Haiku 4.5 is $1/$5, the cheapest current Claude model (all re-verified 2026-09-22). **A report reasons in relative bands (¢/$/$$/$$$), never a specific model's price
per token, unless the exact figure was just re-verified this pass** — the bands are stable
longer than the underlying prices. Where a different vendor's model is named by the user, its
tier and relative cost are whatever `tokenwright refresh` last verified against that vendor's own
pricing page; this table's absolute figures are Claude-only.

## Honesty rules

Before → after pairs on every slim; method named on every count; the ± band shown on every estimate; net-cost arithmetic shown whenever text is added; "verified as of" language on anything from this file when the stamp is aging.
