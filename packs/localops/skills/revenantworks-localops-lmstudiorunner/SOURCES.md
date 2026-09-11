# Sources — revenantworks-localops-lmstudiorunner

All verified 2026-09-09 unless noted.

## Primary — the API this skill drives

- **LM Studio developer documentation** — `lmstudio.ai/docs`: API changelog
  (TTL from 0.3.9, speculative decoding from 0.3.10, native `/api/v0` and the
  later `/api/v1`), structured response with JSON schema, model parameters.
- **A live `GET /api/v0/models` response**, 2026-09-09. The field table in
  `references/api-surface.md` is transcribed from an actual response, not from
  documentation — the docs do not enumerate every field the endpoint returns.
- **Three live chat-completion probes against `gemma-4-12b-it` (Q4_K_M,
  `tool_use`, loaded at full 262144 context), 2026-09-10** — the basis for
  `references/api-surface.md`'s `enable_thinking` caveat and the "Sizing the
  budget" section. `chat_template_kwargs.enable_thinking: false` did not
  suppress reasoning (~168-200 tokens on all three requests, `max_tokens` 200
  and 600). `response_format.json_schema` (`strict: true`) did not add
  reasoning cost by itself — the difference between a 200-token budget failing
  and a 600-token budget succeeding on the same schema was `max_tokens`, not
  the schema. Cross-checked against `lmstudio.ai/docs/app/api/structured-output`
  and `lmstudio.ai/docs/app/api/endpoints/openai`, fetched 2026-09-10: neither
  page documents `chat_template_kwargs`, `reasoning_content`, `reasoning_effort`,
  `enable_thinking`, or `reasoning_tokens` — the switch is a llama.cpp/vLLM
  chat-template convention LM Studio passes through, not a first-party
  documented field, treated here as best-effort per model, never guaranteed.

## Incumbents reviewed before building

- **`github.com/IsmaelMartinez/delegate-local`** — the closest prior art.
  Delegates summarization, log triage and bulk text to local models. Routes by
  capability tier (`code`, `prose`, `reasoning`, `long-context`) resolved
  against installed models rather than by hardcoded name, and audits
  recommendations against hardware via `llmfit`. Verification is, in its own
  words, deliberately lightweight, and it is an in-session tool.
- **`github.com/TerminalSkills/skills` → `lm-studio-subagents`** — offloads
  summarization and classification through LM Studio's OpenAI-compatible API.
  Names specific recommended models, which is the staleness this skill avoids.
- **OpenClaw's `lm-studio-subagents`** — the same shape on another runtime.

## Ecosystem context

- **LM Studio's Bionic agent** runs SKILL.md skills natively and reads Claude
  Code and Codex skill directories without conversion, which is why this skill
  depends on no Claude Code-only frontmatter key.
- **The Agent Skills open standard** (`agentskills.io`) — the SKILL.md format
  this file conforms to.

## Measured, not sourced

The failure numbers in `references/work-classes.md` and
`references/task-cards.md` are observations from real runs against a local
model on one machine, recorded with their conditions. They are evidence for the
shape of the failure, not published benchmarks, and they are labelled as
measurements in the text so nobody mistakes them for vendor claims.
