# Sources — revenantworks-localops-whisperrunner

> **Last verified: 2026-10-01** — the primary sources and the parity register below
> (calendar surface, 90 days, declared in `volatile.json`). The incumbent scan was run
> 2026-09-28 and its findings were re-used at the build; the engine facts were re-read raw on
> 2026-10-01.

## Primary — the engine this skill drives

- **whisper.cpp README** (raw, `ggml-org/whisper.cpp` master), read 2026-10-01: the Vulkan build
  (`cmake -B build -DGGML_VULKAN=1`), the FFmpeg conversion command, the 16-bit WAV limit of
  `whisper-cli`, the model size table, the VAD section (`--vad`, `-vm`, Silero model names and
  the download scripts).
- **`examples/cli/README.md`** (raw), read 2026-10-01: flag names and printed defaults for `-m`,
  `-t`, `-ng`, `-fa`, `-otxt`, `-osrt`, `-ovtt`, `-oj`, `-ojf`, `-of`, `-l`, `-np`, `-pp`.
- **`src/whisper.cpp`** (raw), read 2026-10-01: the log format strings the backend proof parses
  (`using %s backend`, `no GPU found`, `failed to initialize %s backend`, `%12s total size`).
- **Releases API** (`/releases/latest`), read 2026-10-01: tag v1.9.4, published 2026-09-11, no
  assets. Earlier asset lists (b5130, b5127, b4938, v1.9.2; read 2026-09-28): CPU, BLAS and CUDA
  zips only, no Vulkan.
- **Issues** (read 2026-09-28): 3750 (silent CPU fallback), 3806 (flash attention crash on AMD
  Vulkan), 3673 and 4063 (requests for Windows Vulkan release builds), 3973 and 3958 (Windows
  Vulkan build failures).

## Claude platform

- **Plugin evals** — code.claude.com/docs/en/plugin-evals, read 2026-10-01: the case layout
  (`evals/<case>/prompt.md` + `graders/*.md`), `prompt.md` fields (`max_turns`, `allowed_tools`,
  `description`, `expected_outcome`), grader types and keys (`tool_used` with `input_match`,
  `min: 0`, `max: 0`, `arm: both`; `regex` with `match: not_contains`, `flags`; `llm` with the body
  as criteria). Not run here: each run bills the plan.

## Sibling contracts

- `references/gpu-seam.md` and `scripts/gpu_preflight.py` — pack-shared, copied byte-identical
  from comfyrunner at the 0.1.0 build. whisperrunner's holder name, release verb and CPU rule
  live in `references/checks.md`, section 6, because the shared copy is not edited per member.
- lmstudiorunner (unload; work on a finished transcript), comfyrunner (audio generation),
  soundsmith (game audio direction), researchscribe (transcripts as sources), trustwarden
  (vetting a third-party binary) — named in the body, never required.

## Parity register *(dated 2026-09-28, re-confirmed 2026-10-01, re-scanned live 2026-10-01 by unit PR; re-check every 90 days)*

**Incumbents** (checked 2026-09-28):

| Incumbent | What it is |
|---|---|
| github.com/eviscerations/whisper-windows-mcp | Node MCP server, Windows-native, whisper.cpp Vulkan; batch, subtitles, model download, a GPU check on request, time estimate. The strongest. |
| github.com/SmartLittleApps/local-stt-mcp | whisper.cpp MCP for Apple Silicon; diarization. |
| faster-whisper MCPs (ZahiriNatZuke/whisper-transcribe-mcp, laurentlemercier/local-whisper-mcp) | CUDA-oriented; CPU-only on AMD under Windows in practice. |
| ~11 generic "run whisper on a file" skills (GitHub code search) | None handles AMD or Windows GPU choice. |
| anthropics/skills, claude-plugins-official | No speech-to-text skill or plugin of their own (exact-match scan); the marketplace now lists AMD's `local-ai-use` (next row). |
| github.com/amd/skills `local-ai-use` (official Claude marketplace, MIT, read 2026-10-01) | Routes STT, TTS and image generation to a local Lemonade Server; whisper.cpp with an NPU fast path (XDNA2 only); no backend proof per run, no GPU lease, no output check. The reach leader for local transcription on AMD. |

**Parity table:**

| Capability | Line | Reason | Eval case |
|---|---|---|---|
| Transcribe to txt, srt, vtt, json with timestamps | met | `whisper-cli` output flags | `scripts/test_whisper_run.py` (outputs written) |
| GPU on AMD under Windows | met | same engine as the Windows MCP (Vulkan) | T2 |
| Batch a folder | met | `run` takes a folder | T4, T7 |
| Model choice; download as a named owner step | met | engine.md model table; walkthrough step 8 | T1 |
| Proof the GPU actually ran | **beaten** | asserted from the log on every run, not on request | **T2**, native `backend-failed-gpu` |
| Sharing the GPU with LM Studio and ComfyUI | **beaten** | the pack lease; no incumbent knows other GPU tenants exist | **T3**, native `lease-busy-refusal` |
| Unattended batches | **beaten** | output check before a file counts as final; `_failed/` staging; known-hash rule | **T4**, **T7** |
| Speaker diarization | out of scope | whisper.cpp tinydiarize is English-only and experimental | — |
| Live dictation, streaming | out of scope | file-to-text only | — |
| Cloud API fallback | out of scope | local-only pack rule | N4 |

**Named margins:** M1 backend proof (T2) · M2 GPU lease (T3) · M3 transcript check (T4, T5).

**Iterate proposals:** VAD by default once the user has the Silero model; pin the known-good
build hash in `audit` (done: the config's `sha256`); a CTranslate2-ROCm probe as an optional
second engine once a Windows success report exists for consumer RDNA2 cards; a measured VRAM
figure per model from the `total size` line, written into the audit record.

**Retire condition:** an incumbent (most likely whisper-windows-mcp, or an official Windows
Vulkan release plus a first-party skill) that both proves the backend on every run **and**
honours a cross-tool GPU lease. Either alone does not erase the margin.

**Verdict: PARITY + MARGIN.** Name collision: CLEAR (exact-match `whisperrunner` on GitHub,
npm, PyPI and the web, 2026-09-28).

## Licence notes

Nothing is copied from the incumbents. The adopted patterns (Windows-native paths, FFmpeg for
non-WAV input, turbo on GPU and q5_0 on CPU, a time estimate before a batch, "nothing leaves the
machine") are ideas, re-implemented. whisper.cpp is MIT; this skill drives it as a tool and
ships none of its code.
