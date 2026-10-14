# Sources

This skill is assembled from public, citable material: Anthropic's prompt- and context-engineering documentation, the named originators of each prompt framework, peer-reviewed research, the OWASP security guidance for LLM applications, and the Agent Skills open standard. This file maps each part of the skill to where its ideas come from, so the guidance can be checked and updated against primary sources.

> **Last verified: 2026-09-28** — the row marked 2026-09-28 (Sonnet 5.5), the rows marked 2026-09-26 and the Parity register (the 1.6.0 parity audit). The older Foundations rows are not re-verified; everything else was verified against the listed sources as of **2026-07-06**. The hostile-read entries added **2026-07-24** cite nothing new — they map to the Self-Refine row already listed, or declare themselves unsourced. Model facts and product details change quickly — durable routing guidance lives in `references/model-routing.md`, and volatile facts (names, prices, context windows) are isolated in `references/model-snapshot.md` behind a Last-verified stamp. Re-check the snapshot against the vendor docs before relying on specifics, or run "promptwright refresh".

---

## Foundations — Anthropic prompt & context engineering

*Applies to: `SKILL.md` (workflow, restraint, long-context ordering), `references/frameworks.md` (long-context and agent/system patterns), `references/model-notes.md`, `references/evaluation.md`.*

| Source | Key guidance |
|---|---|
| Anthropic — Prompt engineering overview and best practices. https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview | Be clear and direct; give the model a role; use XML tags to separate instructions from data; show 3–5 diverse examples rather than exhaustively enumerating edge cases. |
| Anthropic — Use XML tags / long context tips. https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/long-context-tips | For long inputs, place documents / context at the **top** of the prompt and put the question or instruction **after** them. This ordering can materially improve answer quality on long-context tasks. |
| Anthropic — "Effective context engineering for AI agents." https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents | Aim for the smallest set of high-signal tokens; find the "right altitude" for system prompts (specific enough to steer, general enough to leave room); curate a minimal, well-described tool set rather than exposing everything. |
| Anthropic — Prompting best practices, with per-model sections (Fable 5.1, Fable 5, Sonnet 5, Opus 5.5, Opus 4.8). https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices *(verified 2026-09-26)* | Source of `model-snapshot.md`'s per-model deltas table and the Model-fit check's per-model row: Fable 5.1 writes fewer user-facing updates; Opus 5.5 effort calibration, prompts written for thinking disabled, progress updates, safeguard false positives; prefill returns 400 from 4.6 on; dial back aggressive language. |
| Anthropic — Prompting Claude Sonnet 5.5. https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5-5 *(verified 2026-09-28)*; with the Sonnet 5.5 model page and the effort page | Source of `model-snapshot.md`'s Sonnet 5.5 row: Sonnet 5 prompts carry over; effort recalibrated (default `high`, `medium` for well-specified agentic work); check-ins at low effort; unrequested additions; think-first for JSON answers; `between_tools` as the lowest thinking setting; `reasoning_extraction` refusals. |
| Anthropic — Develop tests. https://platform.claude.com/docs/en/test-and-evaluate/develop-tests *(verified 2026-09-26)* | Success criteria first, then evals: test cases, preliminary prompt, iterative testing, final validation. Basis for Entry — Optimize's contract-then-slice order. |
| Anthropic — Console prompting tools (prompt generator, prompt improver). https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-tools and `.../prompt-improver` | **Redirect — tool status unverified (2026-09-26).** Both URLs now redirect to the best-practices page. A redirect is not a retirement notice; no part of promptwright depends on the tools. |
| Anthropic — Interactive prompt-engineering tutorial. https://github.com/anthropics/prompt-eng-interactive-tutorial | Source for the staged "intake → structure → refine" mental model and for the principle that more capable models need *less* prescriptive scaffolding. |

---

## Prompt frameworks — named origins

*Applies to: `references/frameworks.md`.*

| Framework | Origin | Signature contribution |
|---|---|---|
| **CO-STAR** (Context, Objective, Style, Tone, Audience, Response) | Sheila Teo, winner of Singapore's first GPT-4 Prompt Engineering Competition (2023). Popularized in Maximilian Vogel's "Prompt Engineering Cheat Sheet." | The Style / Tone split — most frameworks merge them. |
| **RISEN** (Role, Instructions, Steps, End goal, Narrowing) | Kyle Balmer. (Commonly linked to the earlier RISE pattern; the letters do not map one-to-one, so no lineage is claimed here.) | Explicit Narrowing — constraints as a named component rather than an implied one. |
| **RTF** (Role, Task, Format) | Widely-used community pattern. | Minimal three-part scaffold for simple, well-defined tasks. |
| **BAB** (Before, After, Bridge) | Community pattern derived from the Before–After–Bridge copywriting structure. | Frames the task as a current → target transition with the Bridge carrying the rules. |
| **TIDD-EC** (Task, Instructions, Do, Don't, Examples, Context) | Community framework. | Explicit Do / Don't pairing — tells the model directly which characteristics must and must not appear. |
| **Chain of Thought** ("think step by step") | See Research section below. | — |

---

## Research papers

*Applies to: `references/frameworks.md` (CoT, Chain of Density), `references/evaluation.md` (self-refinement loop), `references/prompt-hardening.md` (constitutional framing), `references/hostile-interpreter.md` (the critique loop it adapts).*

| Paper | Citation | Application |
|---|---|---|
| Chain-of-Thought prompting | Wei et al., 2022 — "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models." arXiv:2201.11903. | Basis for the explicit step-by-step reasoning instruction on non-reasoning / chat models. |
| Self-Refine | Madaan et al., 2023 — "Self-Refine: Iterative Refinement with Self-Feedback." arXiv:2303.17651 (NeurIPS 2023). | Basis for the score → critique → revise loop and for the skill's re-scoring phase. The Phase 6 hostile read is that loop with the critic's lens fixed on literal compliance instead of quality. |
| Chain of Density | Adams et al., 2023 — "From Sparse to Dense: GPT-4 Summarization with Chain of Density Prompting." arXiv:2309.04269. | Basis for the iterative summarization guidance in the Advanced / critique set. |
| Constitutional AI | Bai et al. (Anthropic), 2022 — "Constitutional AI: Harmlessness from AI Feedback." arXiv:2212.08073. | Background for principle-based self-critique in hardening. |

**Unsourced by design:** the hostile read's four failure shapes and the catalog in `references/hostile-interpreter.md` are doctrine assembled for this skill, not a taxonomy taken from published work. Declared here so the gap is visible rather than implied.

---

## Security & hardening

*Applies to: `references/prompt-hardening.md`.*

**OWASP Top 10 for LLM Applications (2025)** — https://genai.owasp.org/

| Risk | ID | How it's reflected in the skill |
|---|---|---|
| Prompt Injection (direct and indirect) | LLM01 | Treated as the top risk. The guidance that you cannot fully "patch" injection and must design around it comes from here. Mitigations: separate instructions from untrusted data, segregate and label external content, constrain output formats, apply defense-in-depth. |
| Sensitive Information Disclosure | LLM02 | Least-exposure guidance in the sensitive data section. |
| Excessive Agency | LLM06 | Least-privilege tooling and human-in-the-loop guidance for agentic prompts. |
| System Prompt Leakage | LLM07 | Don't put secrets in the system prompt; instruct the model not to reveal its instructions. |

---

## Skill format — the Agent Skills open standard

*Applies to: the packaging of this skill itself (`SKILL.md` frontmatter, `references/` layout, progressive disclosure).*

**Agent Skills open standard** — https://agentskills.io/ · reference repository: https://github.com/anthropics/skills

| Principle | How it's applied |
|---|---|
| A skill is a folder with a `SKILL.md` containing YAML frontmatter (`name` and `description` required) plus Markdown instructions, with optional `references/`, scripts, and assets. | Package structure follows this exactly. |
| **Progressive disclosure:** the model first sees the frontmatter, then the body, then pulls in reference files only as needed. | Heavy material lives in `references/` rather than in `SKILL.md`. |
| Descriptions should be explicit and "pushy" about when to trigger. | Reflected in the skill's `description` field. |
| **Conciseness:** the context window is a public good — once loaded, every SKILL.md token competes with the conversation. Keep the entry file lean; split mutually-exclusive contexts into separate files. (Anthropic — Skill authoring best practices, https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices · "Equipping agents for the real world with Agent Skills," https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) | Drives the load budget, the lean SKILL.md, and the situational (rather than mandatory) reference loads. |
| `allowed-tools` grants no-prompt use of the listed tools while the skill is active. | Omitted, since no step needs one. |

*Standard provenance: released as an open standard in December 2025. Specification code under Apache-2.0; documentation under CC BY 4.0.*

---

## Model-specific notes

*Applies to: `references/model-notes.md`, and model-tagged guidance throughout.*

These reflect vendor documentation and product facts current as of **2026-07-06** and will drift. The tier-routing model (`model-routing.md`) is durable; the specific names, prices, and context windows in `model-snapshot.md` are the parts that rot. Primary sources (vendor model docs, verify in this order):

- Anthropic — https://platform.claude.com/docs/en/about-claude/models/overview

Cross-check registries (community-maintained, machine-readable; may lag brand-new launches — vendor docs win conflicts):

- LiteLLM model/price/context registry — https://github.com/BerriAI/litellm/blob/main/model_prices_and_context_window.json
- OpenRouter live model list — https://openrouter.ai/api/v1/models

The single-update-surface pattern (isolating volatile facts in one stamped file) and the fetch-first / verify-against-canonical-source approach follow Anthropic's own `product-self-knowledge` skill, which handles the same drift problem by keeping stable pointer URLs instead of baked-in facts.

---

## Parity register

*Applies to: `references/optimize.md`, `references/tool-handoff.md`, `references/frameworks.md` (Agent/System non-goals, layer owner, path inventory), SKILL.md Phase 1 and Phase 2 (bottleneck check). Volatile: declared in `volatile.json` (calendar, 90 days); `skillwright upkeep` re-checks it.*

Last verified: 2026-09-26. The incumbents promptwright was measured against in the 1.6.0 parity audit, and what each one contributed. Ideas were taken as patterns; no code or text was copied.

| Incumbent | URL | Licence | Checked | Capability taken |
|---|---|---|---|---|
| Sentry prompt-optimizer skill | https://github.com/getsentry/skills (`skills/prompt-optimizer/SKILL.md`) | Apache-2.0 | 2026-09-26 | Capture-contract step (layer owners, non-goals); eval slice before rewrite; 2–4 candidates on the same cases; optimization log; holdout validation; stop on plateau, oscillation, overfit, cost or non-prompt bottleneck; external-context inventory (loaded / referenced / out of scope). |
| promptfoo | https://github.com/promptfoo/promptfoo · https://www.promptfoo.dev/docs/red-team/ | MIT | 2026-09-26 | The eval and red-team runtime promptwright hands off to: `promptfooconfig.yaml` with asserts, and red-team plugins chosen by capability. Driven, never rebuilt. |
| GEPA, with DSPy | https://github.com/gepa-ai/gepa · the DSPy repository | MIT | 2026-09-26 | The automated optimizer promptwright hands off to: a seed prompt, a metric, a trainset, and textual feedback its reflection step reads. Driven, never rebuilt. |
| wshobson prompt-engineering-patterns (reach benchmark) | https://github.com/wshobson/agents (`plugins/llm-application-dev/skills/prompt-engineering-patterns`) | MIT | 2026-09-26 | Not a parity column: the most-installed prompt-engineering skill, a technique catalogue with no scoring, hardening or routing. Recorded as the reach benchmark only. |

**Margin claims** (tested against these incumbents in `evals/test-cases.md`; re-scanned 2026-10-01): the static Hostile read of the prompt's own wording (promptfoo Code Scanning reads code data flow for injection before runs, not wording), restraint, the bottleneck check, data-not-instructions, tier routing, and a Score line that shows rubric and measured scores side by side.

---

## The grill

Moved to grillwright on 2026-10-08, with its ASE credit, when the grill became its own foundation member. promptwright's Phase 4 reads grillwright's record when a grill is asked for by name.

## Discernment note (added 2026-10-08)

*Applies to: `references/discernment.md`.* The idea of an optional "where to double-check this" line on factual answers comes from Anthropic's discernment-nudge material in the anthropics GitHub organisation, named in the user-approved 2026-10-08 estate review; this unit did not re-fetch it. Taken as an idea only, in our own words: the four binding rules (when, a reachable kind of source, the claim most worth checking, one line after the answer) and the no-invented-citation rule are promptwright's. No text copied.

## Slim (added 2026-10-08)

*Applies to: Entry — Slim and `references/slim.md`.* The ladder, preservation contract, measuring rules and cache-floor rule were moved here, condensed, from the retired tokenwright when each owner took the slim of its own artifacts; the pack's full doctrine and its sources (Anthropic's context-engineering guidance, the token-counting and prompt-caching docs, the description-cap sources) now sit in skillwright's `SOURCES.md` — Slim entry, which this file does not restate. Runtime tools named as optional, never required: JuliusBrussee/caveman (https://github.com/JuliusBrussee/caveman, output compression) and rtk-ai/rtk (https://github.com/rtk-ai/rtk, Apache-2.0, command-output compression), both read 2026-10-08.
