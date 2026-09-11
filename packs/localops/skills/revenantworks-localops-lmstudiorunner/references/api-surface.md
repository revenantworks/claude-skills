# LM Studio API surface *(calendar surface — 90 days)*

> **Last verified: 2026-09-10** against LM Studio's developer documentation and
> a live server. Re-verify with `lmstudiorunner refresh`. Field names and endpoint
> paths are the volatile part; the reasons for reading them are not.

## Contents

- Finding the server
- Listing models — the fields that matter
- Chat completions
- Structured output
- Sizing the budget: a one-request probe
- Model lifecycle: TTL and just-in-time loading
- Speculative decoding
- Degrading without a shell

---

## Finding the server

LM Studio serves an OpenAI-compatible API and a native API from the same port.
**The default is 1234, but never assume it** — a user who changed it in the
Server tab will otherwise be told their server is down.

Probe in this order, taking the first that answers, with a short connect
timeout on every probe so a closed port fails fast instead of hanging:

```
curl -s --connect-timeout 2 http://127.0.0.1:1234/api/v0/models
curl -s --connect-timeout 2 http://localhost:1234/api/v0/models
curl -s --connect-timeout 2 http://127.0.0.1:1235/api/v0/models
curl -s --connect-timeout 2 http://localhost:1235/api/v0/models
```

**Try the literal address as well as the name.** On Windows `localhost` may
resolve to IPv6 `::1` first, and a server bound only to IPv4 is unreachable by
name while answering perfectly on `127.0.0.1`. This costs one extra request and
removes a whole class of false "server is down".

If nothing answers, report it with `lms server start` and stop. Never guess
what is installed.

## Listing models — the fields that matter

`GET /api/v0/models` (native) returns richer metadata than the
OpenAI-compatible `GET /v1/models`, which returns little more than ids. **Use
the native endpoint for anything that decides which model to use.**

A live response, one entry:

```json
{
  "id": "some-model-id",
  "object": "model",
  "type": "vlm",
  "publisher": "lmstudio-community",
  "arch": "gemma4",
  "compatibility_type": "gguf",
  "quantization": "Q4_K_M",
  "state": "loaded",
  "max_context_length": 262144,
  "loaded_context_length": 12288,
  "capabilities": ["tool_use"]
}
```

| Field | Why it decides something |
|---|---|
| `type` | `llm`, `vlm` (vision), `embeddings`. A vision task needs `vlm`; an embeddings model cannot chat |
| `arch` | Model family. Useful for grouping, never for ranking |
| `quantization` | Accuracy/memory trade. A tiebreak between similar models, not a ranking |
| `state` | `loaded` or `not-loaded`. A loaded model answers immediately; another may need loading first |
| `max_context_length` | The ceiling the model supports |
| `loaded_context_length` | **What it is actually loaded with, and the one people miss.** Present only when `state` is `loaded` — absent from a not-loaded entry, never `0` or `null` |
| `capabilities` | Advertised abilities, e.g. `tool_use`. The only honest way to know. **May be absent entirely** on a non-chat entry such as `embeddings` — read a missing key as no advertised capability, never as an error |
| `publisher` | Who ships the model. Informational, not a ranking signal |
| `compatibility_type` | The runtime format, e.g. `gguf`. Informational |

**Always compare `loaded_context_length` against `max_context_length` and
report a divergence.** A model loaded far below its ceiling silently truncates
long inputs, and nothing in the OpenAI-compatible endpoint reveals it. In the
run that motivated this note the gap was 12,288 against 262,144 — a twenty-fold
shortfall on a machine with memory to spare. **On a just-in-time rig with
nothing loaded, every entry omits `loaded_context_length`** — that state is
routine, not an error: judge fit against `max_context_length` instead and say
the resident context is unknown until something actually loads.

## Chat completions

`POST /v1/chat/completions`, OpenAI-shaped: `model`, `messages`, `max_tokens`,
`temperature`. The native `POST /api/v0/chat/completions` accepts the same plus
LM Studio extensions such as `ttl`.

Two response details that matter:

- **A reasoning model returns its thinking separately** — commonly a
  `reasoning_content` field beside `content`, with reasoning counted in
  `usage.completion_tokens_details.reasoning_tokens`. **Those tokens are billed
  against `max_tokens`.** Budget for the whole completion, not the answer.
- **`finish_reason` distinguishes a short answer from a truncated one.** A
  length stop with empty `content` means the budget ran out during reasoning.
  Report that as a budget failure.
- **`chat_template_kwargs.enable_thinking: false` is not a documented LM
  Studio field and is not guaranteed to zero out reasoning** — it is a
  llama.cpp chat-template convention LM Studio passes through per model. A
  live probe on 2026-09-10 against `gemma-4-12b-it` showed reasoning
  continuing (~168-200 tokens) with the flag set to `false`. Verify per model
  with one probe request before relying on it; never assume it.

## Structured output

Pass a JSON schema and the server constrains generation so the output conforms.
**Prefer this to validating afterwards** — malformed output is not produced
rather than caught, which removes a whole retry loop.

```json
{
  "model": "<id from the models call>",
  "messages": [{"role": "user", "content": "..."}],
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "name": "result",
      "strict": true,
      "schema": {
        "type": "object",
        "properties": {"items": {"type": "array", "items": {"type": "string"}}},
        "required": ["items"]
      }
    }
  }
}
```

**What it does not do:** a schema constrains *shape*, never *content*. A
schema-valid array of 180 strings can still be 60 distinct values repeated —
the measured failure. Schema plus a count-and-uniqueness check, not schema
alone.

**Structured output does not, by itself, add reasoning cost** — a schema
changes the shape of the answer emitted after reasoning, not whether or how
much the model reasons first. The failure mode ("schema mode ate the budget")
is a `max_tokens` sizing problem restated: if the budget was already tight
against the model's normal reasoning cost, adding a schema exposes that by
giving the answer nowhere to land. Size `max_tokens` from a probe (below), not
from the expected answer length alone.

## Sizing the budget: a one-request probe

Before sizing a batch, send one representative card with a generous
`max_tokens` (600-800 for a short answer) and read two fields:
`usage.completion_tokens_details.reasoning_tokens` and `finish_reason`.

- `finish_reason: "length"` with empty `content`: the budget ran out inside
  reasoning. Raise `max_tokens` and re-probe — never retry the same number
  expecting a different result.
- `finish_reason: "stop"` with content present: subtract `reasoning_tokens`
  from `completion_tokens` for the true answer length, and set the batch's
  `max_tokens` to `reasoning_tokens + (expected_answer_tokens × 1.5)` as a
  margin, since reasoning cost is roughly stable across similar prompts on one
  model but not identical.

This is the probe `lmstudiorunner size <task>` (SKILL.md — Entry points) runs
to answer "should I even hand this over" — the same request, just read for
these two fields now, not only pass/fail.

## Model lifecycle: TTL and just-in-time loading

A request may name a model that is not loaded; the server loads it on demand.
Passing `"ttl": <seconds>` lets an idle model evict itself afterwards.

This is what makes **per-task model routing** practical: match the capability
class, load what fits with a TTL, let it fall out of memory when the batch
moves on. Auto-eviction applies to just-in-time-loaded models; a model loaded
by hand in the GUI or by `lms load` stays until it is unloaded.

Newer builds add explicit load and unload endpoints. Prefer TTL where it works
— it needs no cleanup path and survives a crashed run.

## Speculative decoding

A small draft model proposes tokens a larger model validates, raising
throughput at equal quality. Where the server reports a draft model in the
response, note it when explaining timings — otherwise generation speed looks
inexplicably good.

## Degrading without a shell

Where the surface cannot make HTTP requests, hand back the exact `curl`
commands and ask for the output to be pasted. Every decision here rests on the
models listing and one completion, both of which are one command each. The
skill still works; it just runs through the user.

## Sources

- LM Studio developer docs — API changelog, structured response, speculative
  decoding, model parameters (`lmstudio.ai/docs`)
- A live `GET /api/v0/models` response, 2026-09-09, the field table above
