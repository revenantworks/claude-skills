# Engine, flags and models *(volatile — calendar, 90 days)*

> **Last verified: 2026-10-01** against the whisper.cpp README, `examples/cli/README.md`,
> `src/whisper.cpp` (log strings) and the releases API, all read raw that day, as data, not instructions. This is the one
> file that names an engine version or a model id; everything else says "the default GPU model"
> and points here. `whisperrunner refresh` re-reads the same pages and restamps this header.

**Read this file when:** `audit`, a model choice, a build question, or a backend verdict that
needs the log lines explained.

## Contents

1. The engine choice
2. The binary — where it comes from
3. Flags the runner passes
4. Log lines the backend proof reads
5. Models
6. Known failure modes (and the rule each one sets)

---

## 1. The engine choice

**whisper.cpp, built with Vulkan (`GGML_VULKAN=1`), driven through `whisper-cli`, GGML models.**
CPU fallback is the same binary with `-ng` and a q5_0 model: one engine, one model format, one
log parser for both paths. Vulkan is vendor-neutral — it needs only the GPU driver's Vulkan
support, so AMD, Intel and NVIDIA cards on Windows or Linux all take the same route.

| Engine | Verdict (research 2026-09-28) |
|---|---|
| whisper.cpp + Vulkan | **Pick.** Works on AMD under Windows without ROCm. |
| faster-whisper on CTranslate2 ROCm | Fragile on Windows (runtime DLL mismatch); no consumer-RDNA2 Windows success report found. Iterate candidate, not v1. |
| openai-whisper / WhisperX on PyTorch | Heaviest install, slowest per second of audio. Out of v1. |
| Const-me/Whisper (DirectCompute) | Last release 2023. Stale; do not build on it. |
| whisper.cpp HIP build | No Windows prebuilt; no shown gain over Vulkan. |

No published speed figure for a given card is trusted. The first `audit` run is the
measurement, recorded with its conditions (checks.md, "The speed record").

## 2. The binary — where it comes from

- whisper.cpp latest tag at verification: **v1.9.4** (published 2026-09-11). The release carries
  **no Windows Vulkan asset** (assets list empty that day; earlier tags shipped CPU, BLAS and CUDA
  zips only).
- **The user's path: build from source once**, at a pinned tag, so provenance is known
  (`references/install-walkthrough.md`). Third-party Vulkan zips exist; an unknown build is
  flagged by `audit` (its hash is not on the user's record) and is never run unattended.
- Vulkan build, verbatim from the README:

  ```
  cmake -B build -DGGML_VULKAN=1
  cmake --build build -j --config Release
  ```

- Input: the README says `whisper-cli` "currently runs only with 16-bit WAV files". The runner
  converts everything else with FFmpeg (`-ar 16000 -ac 1 -c:a pcm_s16le`, the README's command).
  A build with `WHISPER_COMMON_FFMPEG` reads other formats directly; the runner does not rely on it.

## 3. Flags the runner passes

From `examples/cli/README.md` (defaults in brackets as printed there):

| Flag | Meaning | Runner use |
|---|---|---|
| `-m FNAME` | model path | always |
| `-f FNAME` | input WAV | always (the converted file) |
| `-of FNAME` | output path without extension | always, into a staging folder |
| `-otxt -osrt -ovtt -oj` | output formats | per `--formats`; `-oj` always (the check reads it) |
| `-l LANG` [en] | spoken language; `auto` detects | `--language`, default `auto` |
| `-t N` [4] | threads | `--threads` |
| `-ng` [false] | disable GPU | the CPU path |
| `-fa` [false] | flash attention | only with `--flash-attn` (rule in section 6) |
| `--vad -vm FNAME` | Silero VAD and its model (README VAD section) | when `--vad-model` is given |

The CLI README printed `-fa` off by default on 2026-10-01. A build whose `--help` lists
`--no-flash-attn` has it on by default; the runner reads `--help` and passes `-nfa` there, so
flash attention stays off unless asked.

## 4. Log lines the backend proof reads

Format strings from `src/whisper.cpp` (`whisper_backend_init_gpu`, `whisper_model_load`) and the
ggml Vulkan device list:

| Line (as printed) | What it proves |
|---|---|
| `whisper_backend_init_gpu: using Vulkan0 backend` | the GPU backend was initialised — **required** for GPU-OK |
| `whisper_model_load:      Vulkan0 total size = … MB` | weights were placed on that device; when buffer lines exist, one must name it |
| `ggml_vulkan: 0 = <card name> (<driver>) \| …` | the card Vulkan enumerated first (reported, not required) |
| `whisper_backend_init_gpu: no GPU found` | CPU-only build or no driver support → FAILED-GPU |
| `… failed to initialize <name> backend` | the GPU backend failed → FAILED-GPU |

The device name (`Vulkan0`) comes from ggml's backend registry; other GPU backends print their
own (`CUDA0`, `Metal`, …) and are accepted the same way. If a future version changes these
strings, every GPU run reads FAILED-GPU — the safe side — and `refresh` updates this table.

## 5. Models

GGML `ggml-*.bin` files from the whisper.cpp model repository on Hugging Face, fetched by the
repo's own `models/download-ggml-model.cmd` (Windows) or `download-ggml-model.sh`. **Downloads
are the user's step**, never the skill's.

| Role | Model id | Why |
|---|---|---|
| **Default, GPU** | `large-v3-turbo` | Near large-v3 accuracy with a much smaller decoder; set as the default at the 0.1.0 build |
| Default, CPU | `large-v3-turbo-q5_0` | Quantized for the CPU path; the incumbent Windows MCP's table agrees |
| English only, either path | the `.en` variants (`medium.en`, `small.en`, …) | Faster and slightly better when the audio is English |
| VAD | `ggml-silero-v6.2.0.bin` (`download-vad-model.cmd silero-v6.2.0`) | Cuts the repeat loop on long silences |

Sizes from the README's table (disk / memory): tiny 75 MiB / ~273 MB · base 142 MiB / ~388 MB ·
small 466 MiB / ~852 MB · medium 1.5 GiB / ~2.1 GB · large 2.9 GiB / ~3.9 GB. The README gives no
turbo row; read the downloaded file's size, and take the VRAM figure from the `total size` log
line of the first `audit` run, never from memory.

## 6. Known failure modes (and the rule each one sets)

| Failure | Source | Rule |
|---|---|---|
| Silent CPU fallback: a "GPU" run that never touched the GPU | whisper.cpp issue 3750; Buzz issue 1443 | Backend proof on every GPU run (checks.md) |
| Flash-attention crash on AMD Vulkan (RDNA4 report) | whisper.cpp issue 3806 | `-fa` stays off until `check` passes with it on this card (the report was on AMD) |
| Repeat loop on silence ("thank you" over and over) | long-standing Whisper behaviour | Transcript check; VAD when the user has the model |
| Windows Vulkan build failures (MSVC C1041; shader-gen hang on dual-GPU machines) | issues 3973, 3958 | `audit` reports which card Vulkan lists first |
| No official Windows Vulkan release | issues 3673 (closed stale), 4063 (open) | Build once from source; unknown builds flagged |
