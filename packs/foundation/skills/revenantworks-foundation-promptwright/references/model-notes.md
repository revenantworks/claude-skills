# Model Notes — Durable Per-Model Prompting Guidance

> This file holds the **durable** per-model prompting behavior that survives model releases; tier routing lives in `model-routing.md`. **Volatile facts — current model names, cost bands, context quirks — live only in `model-snapshot.md`** under a Last-verified stamp. When naming a specific model, load the snapshot alongside this file. If the snapshot is stale (>60 days) and unverifiable, recommend by tier name, never a possibly-retired model string.

This skill targets Claude, plus local open-weights models the user runs on their own machine (owner decision 2026-09-30: other hosted vendors are out of scope). The structures in `frameworks.md` are universal; this file holds the per-model differences.

---

## Contents

1. The reasoning-model split *(read first)*
2. Tier routing *(moved to `model-routing.md`)*
3. Claude
4. Open-weight / local models
5. Cross-model rule

---

## 1. The reasoning-model split *(read first)*

Current models ship in two modes, and the prompt changes with the mode — this distinction matters more than which model you target.

| Mode | Examples | How to prompt |
|---|---|---|
| **Reasoning / "thinking" models** | Claude with adaptive thinking; local open-weights families run with a thinking variant on | Give the objective, the constraints, and what "done" looks like, then get out of the way. Do **not** add "think step by step" or a prescribed reasoning outline — it's redundant and can degrade quality or inflate cost. Control depth with the model's API parameter, not prompt language. |
| **Non-reasoning / chat models** | Most fast-tier models, any model with thinking off, local open-weights models in chat mode, most smaller open models | Explicit chain-of-thought framing and few-shot examples still earn their keep. Spell out the steps and show examples. |

Before engineering an elaborate CoT prompt, check whether the target has a reasoning mode you can switch on with a parameter — you get better results with less prompt complexity.

> **Recurring trap:** legacy "booster" instructions written for older models (e.g. "ALWAYS use the search tool before answering," heavy step-by-step scaffolding) now backfire on newer, more capable models, causing over-triggering and overthinking. Newer models usually need *less* prompt, not more. Strip boosters when you move up a generation.

---

## 2. Tier routing *(moved)*

Tier routing lives in `model-routing.md` since 1.6.0: the tier table, the local-target rule, escalation heuristic, role overrides and the staleness rule. `SKILL.md` Phase 5 keeps the short rule a standard build runs. This file keeps only per-model prompt syntax.

---

## 3. Claude

*(Current lineup, context windows, and pricing: `model-snapshot.md`.)*

| Behavior | Guidance |
|---|---|
| **Literal instruction following** | Current Claude does what you say precisely. Be exact, remove contradictory rules, and request "above and beyond" behavior explicitly. Give the reason behind a constraint ("no ellipses — read by text-to-speech") and the model honors it more reliably. |
| **Adaptive thinking** | Recommended mode; default on current flagship tiers. The model decides per turn whether and how much to think — don't add CoT framing when it's on. Set depth with the `effort` parameter, not with prompt text. On the newest frontier tier, thinking is always on and cannot be disabled. Manual token budgets are deprecated. |
| **Mid-task instruction updates** | The Messages API accepts `system` entries inside the `messages` array, so an agent harness can update instructions, permissions, or context mid-run without breaking the prompt cache. |
| **No assistant prefill** | Current Claude models reject a prefilled final assistant turn. Steer format with explicit output-format instructions, structured outputs, or strict tool use. |
| **XML tags** | Claude respects hierarchical tags for separating instructions, context, examples, and input. A terse, clean prompt yields terse, clean output. |
| **Structured output** | Prefer a native structured-output feature or strict tool use when you need a guaranteed shape. For free-form JSON: specify the exact schema and require only that structure with no preamble and no code fences. |
| **Tool use** | Don't over-force. Aggressive "always call X" language causes over-triggering on newer Claude models. State when a tool is appropriate and let the model judge. |
| **Long-context placement** | Put the data at the top and the question after it. See `frameworks.md` — long-context structuring. |
| **Caching** | Split into a stable prefix (instructions, tool definitions, background) and a dynamic suffix (the query and injected data). Cache hits need an exact prefix match. |

**Effort starting points:** medium for coding, agentic, tool-heavy, and frontend work; low for chat, content, search, and classification. Raise only when evals show it pays.

---

## 4. Open-weight / local models

*(Llama, Qwen, Gemma, Mistral, DeepSeek open weights, and similar)*

| Consideration | Guidance |
|---|---|
| **Scaffolding** | Smaller or older instruction-tuned models need more explicit, simpler instructions and more examples than frontier models. What one line buys on a frontier model may take three here. |
| **Reasoning variants** | Many open families ship thinking variants. When thinking is on, apply the reasoning-model rules from section 1. |
| **Context windows** | Often shorter than frontier models — keep inputs tight and put the critical instruction at the start or end. |
| **Testing** | Behavior varies widely by checkpoint and quantization. Test on the exact model and quant; don't port a frontier-model prompt unchanged. |

---

## 5. Cross-model rule

Keep the universal scaffold — role, context, examples, explicit output format — for any model. Then:

1. Pick the capability tier first (section 2), before any model-specific syntax.
2. Decide whether the target is a reasoning or a chat model and prompt accordingly (section 1).
3. Control reasoning depth with the model's API parameter, not with prompt padding.
4. Drop Claude-specific conventions (XML-as-preferred, adaptive-thinking phrasing, prefill warnings) for a local open-weights target.
5. Re-test on every model switch and version bump — newer models often need less prompt, and legacy booster instructions that once helped can quietly hurt.

A hosted model from another vendor is out of scope: build a vendor-neutral prompt from the universal scaffold and say on the Model line that it is not routed.
