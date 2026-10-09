# Sources — revenantworks-localops-comfyrunner

> **Last verified: 2026-09-28** — the primary sources and the parity register below
> (calendar surface, 90 days, declared in `volatile.json`).

## Primary — the server this skill drives

- **ComfyUI server routes** — `docs.comfy.org` (server routes) and `server.py` on
  Comfy-Org/ComfyUI master: `/system_stats`, `/queue`, `/object_info`, `/prompt`,
  `/history`, `/view`, `/upload/image`, `/free`, `/interrupt`, the WebSocket events.
  Fetched 2026-09-26 for the pack's GPU seam and re-read 2026-09-28.
- **Built-in node pages** — `docs.comfy.org`: `VAEDecodeTiled` (tile size, overlap,
  temporal size and overlap; lower memory for large images and video),
  `VAEDecodeAudioTiled`, and the Wan 2.2 tutorial (TI2V 5B native 1280×704 at 24 fps;
  frame counts 4n+1). Fetched 2026-09-28.
- **A live, read-only probe of ComfyUI 0.37.0**, 2026-09-28: `GET /system_stats`
  (device name, `vram_total` 17,163,091,968, empty queue) and `GET /object_info/<class>`
  for `VAEDecodeTiled`, `VAEDecodeAudioTiled`, `Wan22ImageToVideoLatent`,
  `EmptyLatentAudio` and `EmptyHunyuanLatentVideo`. The node table in
  `references/comfy-api.md` is transcribed from those responses. Nothing was submitted.
- **AMD launch guidance** — the ComfyUI README's AMD section (attention flags for RDNA2,
  `--disable-triton-backend` for RDNA1/2 hangs), fetched 2026-09-28. Recorded as the
  owner's choice; the skill never applies it.

## Measured, not sourced

- **The crash reference** — one measured machine, 2026-09 (the build's rig notes): Wan 2.2 TI2V
  5B at 1024×1024×121 frames, 20 steps, plain `VAEDecode`, math attention; 44 minutes
  of sampling, then bugcheck 0x133 twelve seconds into the decode. One case; the cause
  is not proven. The budgets in `references/media-budgets.md` carry it as a reference,
  not a law.
- **SDXL at 1024² runs at about 1.5 it/s** on the same card (the rig notes, 2026-09-26) —
  the basis for the proposed 1 MP image budget.

## Sibling contracts

- **pixelsmith** (`packs/gamedev/skills/revenantworks-gamedev-pixelsmith`),
  `references/briefing.md`, "Diffusion generator": the spec block, the seven-step
  post-process contract, the value method and the terrain-gap bands. Read at build,
  2026-09-28; `references/pixel-contract.md` executes it and restates no rule.
- **lmstudiorunner** — `references/gpu-seam.md` and `scripts/gpu_preflight.py`, carried
  byte-identical (the pack-shared rule).

## Parity register *(dated 2026-09-28; re-check every 90 days)*

Re-scanned 2026-10-01 (unit PR): AK row 9 corrected; margin 4 narrowed to the lease.

Incumbents doing the same core job, each fetched on the date shown. Page text was read
as data. AK was read in full; the others from their repository or docs listing, so a
"not stated" there means the listing did not say, not that the tool lacks it.

| Code | Incumbent | Kind | Fetched | What it does |
|---|---|---|---|---|
| AK | `github.com/artokun/comfyui-mcp` | MCP server + agent skills, MIT | 2026-09-28 | Generates image, video and audio; authors, runs and edits workflows. A VRAM watchdog warns when under 1 GB is free before a run; `clear_vram`; per-model VRAM estimates in a troubleshooting skill; an interrupt on a stalled render |
| SR | `github.com/shawnrushefsky/comfyui-mcp` | MCP server | 2026-09-28 | Image, video, audio and 3D generation from an assistant through ComfyUI |
| CC | Comfy Cloud MCP (`docs.comfy.org`) | Official MCP server, cloud | 2026-09-28 | Runs API-format workflows on Comfy Cloud, async with a task id; searches models, nodes and templates |
| MS | `github.com/MieMieeeee/comfyui-agent-skill` | Agent skill + CLI | 2026-09-28 | Runs registered workflows on a local ComfyUI server; structured JSON output |
| HY | `github.com/HuangYuChuh/ComfyUI_Skill_CLI` | CLI for skills | 2026-09-28 | Server status, workflow discovery, parameter check, run; JSON output |

| # | Core-job capability | AK | SR | CC | MS | HY | This skill |
|---|---|---|---|---|---|---|---|
| 1 | Run an API workflow and collect outputs | met | met | met | met | met | met |
| 2 | Image, video and audio | met | met | met | not stated | not stated | met |
| 3 | Author or edit graphs in natural language | met | partial | met | missing | missing | out of scope (the user's saved workflows) |
| 4 | Free VRAM at hand-back | met (`clear_vram`) | not stated | out of scope | not stated | not stated | met (`free`, idle queue only) |
| 5 | Warn on low free VRAM before a run | met (< 1 GB) | not stated | out of scope | not stated | not stated | met (the pack pre-flight) |
| 6 | Refuse an untiled video decode before submit | missing | not stated | not stated | not stated | not stated | beaten (sole holder) |
| 7 | Resolution × frames budget with a crash reference | missing | not stated | not stated | not stated | not stated | beaten (sole holder) |
| 8 | Scaled test run first, with a time projection | missing | not stated | not stated | not stated | not stated | beaten (sole holder) |
| 9 | Unload another GPU consumer (the LLM) through a shared lease | partial — its panel unloads LM Studio, Ollama and llama.cpp during a render (since 2026-07-09); no shared lease | not stated | out of scope | not stated | not stated | beaten on the lease only |
| 10 | Never interrupt a running job | partial (interrupts a stalled one) | not stated | n/a | not stated | not stated | met — no interrupt command |
| 11 | Pixel-art post-process: palette snap, key out, pre-screen | missing | not stated | not stated | not stated | not stated | beaten (sole holder) — runs pixelsmith's `pixel_post.py`; the contract is pixelsmith's |
| 12 | A no-shell fallback | MCP clients | MCP clients | MCP clients | CLI | CLI | met — `curl` hand-back, NOT RUN |

**Margin** (capabilities no incumbent states, as of 2026-09-28), each mapped to a claim
case in `evals/SUITE.md`, section K:

1. Refuses an untiled decode on a video latent, before submit (K1).
2. A resolution × frames budget with the ratio to a measured crash (K2).
3. A low-resolution test of the same graph first, and a projected range for the full run (K3).
4. A shared lease with the LM Studio runner and the rest of the pack, refused rather than swallowed on failure (K4). AK unloads its own panel's local LLM during a render (re-scan 2026-10-01, `docs/local-llms.mdx`); the cross-tool lease (the pack-shared `references/gpu-seam.md` and `scripts/gpu_preflight.py`) is the margin, not a sole-holder claim.
5. Renders a pixel-art brief and runs its owner's post-process and pre-screen (pixelsmith's `pixel_post.py`; the contract is pixelsmith's) (K5).

**Retire condition.** If an incumbent ships a pre-submit graph check that covers margins
1–3 (tiled decode, a size budget, a scaled test run) and a way to yield the GPU to
another local consumer, this skill keeps only the pixelsmith contract and the lease,
and the rest is retired in its favour. Re-check at the next refresh.

Also seen at build, not in the register because they generate images only, with no
video or audio run path: `Peleke/comfyui-mcp` and several LobeHub-listed ComfyUI MCP
servers.
