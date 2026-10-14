# revenantworks-localops-obsrunner

Drives OBS Studio (the streaming and recording app — not the Open Build Service) from Claude,
read-only by default, and turns its recordings into clips, vertical versions, chapters and upload
sheets on your own machine. It cannot go live and never touches the stream key.

## Why it exists

Several OBS MCP servers already expose the whole WebSocket protocol to an agent. None has a
read-only mode or a confirm step, and one request in that protocol hands back the stream key in
plain JSON. None knows that the same graphics card may be running a local language model, an
image render or a Whisper transcription. And the clip pipelines that do exist lean on a paid
cloud transcription key or an NVIDIA-only GPU.

## The three promises

1. **Live-safe OBS.** Reads freely, writes one confirmed change at a time, and refuses every
   go-live, output, hotkey and stream-service request before it is sent. Responses are masked.
2. **One GPU, shared.** OBS's hardware encoder, LM Studio, ComfyUI and Whisper meet at the
   localops pack lease: no GPU render while OBS is live or recording, and `obsrunner hold` makes
   the other runners wait while you stream.
3. **Proved renders.** Preflight, a 5-second test render, the full render, a re-probe (yuv420p,
   H.264/HEVC, AAC, duration within a frame) and a receipt with hashes. A check that did not run
   is NOT-RUN, never a pass.

Fully local: marks, whisper.cpp transcripts (via whisperrunner), loudness peaks and AMF or CPU
encoding. No cloud key.

## Requirements

- **OBS Studio 28+** with its WebSocket server on (built in).
- **The `obsws-python` package** — the one package this skill drives, allowed by the localops
  package rule; GPL-3.0; you install it (`references/install-walkthrough.md`, step 4). Without it,
  `audit` and `post` still work and live modes report NOT-RUN.
- **FFmpeg and FFprobe** on PATH for `post`.
- **Python 3** for the scripts (standard library otherwise).

## Package

```
revenantworks-localops-obsrunner/
├── SKILL.md
├── README.md · CHANGELOG.md · SOURCES.md · LICENSE
├── references/
│   ├── websocket-allowlist.md   # tiers, deny list and why, masking, Safe Mode
│   ├── obs-settings.md          # dated: versions, profile keys, encoder ids, GPU table
│   ├── post-recipes.md          # render loop, sub-modes, checks, receipts, moments, lease part
│   ├── platform-notes.md        # dated: chapters, thumbnails, upload rules, policy pointers
│   ├── install-walkthrough.md   # owner-run steps, each with a verify and a rollback
│   ├── gpu-seam.md              # pack-shared, byte-identical across the GPU runners
│   └── pack.md                  # the localops roster
├── scripts/
│   ├── obs_ws.py                # the allow-list gate: classify, call, status, check, mark
│   ├── obs_audit.py             # offline profile audit against this GPU
│   ├── obs_post.py              # cut, vertical, captions, loudness, frames, chapters, moments, sheet, hold, release
│   ├── gpu_preflight.py         # pack-shared, byte-identical
│   └── test_obsrunner.py        # 47 tests with a fake client and fake FFmpeg; no OBS or GPU needed
└── evals/                       # hand-run suites + claude plugin eval cases
```

## Install

The skill installs nothing. Follow `references/install-walkthrough.md`, then add the skill with
the localops pack from the plugin marketplace, or upload the folder as a skill on claude.ai
(chat-only surfaces get the commands and NOT-RUN checks).

## Commands

| Say | What happens |
|---|---|
| `obsrunner audit` | profile rows vs this GPU: encoder, rate control, keyframes, AMF B-frames, format, VOD track, disk |
| `obsrunner check` | a 20 s stats window; names render, encode, network or disk as the bottleneck |
| `obsrunner set <change>` | one write (scene, source, mute, volume, profile parameter) after your yes |
| `obsrunner mark [label]` | record chapter + a line in the marks sidecar; `--replay` saves the replay buffer |
| `obsrunner post <sub-mode> <recording>` | `cut`, `vertical`, `captions`, `loudness`, `frames`, `chapters`, `moments` |
| `obsrunner sheet <clip>` | the upload sheet you upload from |
| `obsrunner status` | OBS version and output state, record folder, the lease |
| `obsrunner hold` / `release` | take or drop the GPU lease around a live or recorded session |
| `obsrunner refresh` | re-verify the two dated reference files |

Switches on `post`: `--encoder`, `--obs-state`, `--mode unattended`, `--take-stale`, `--start`,
`--end`, `--crop`, `--srt`, `--lufs`, `--count` (each one is your call).

## Staying current

`references/obs-settings.md`, `references/platform-notes.md` and `SOURCES.md` are calendar
surfaces (90 days). `obsrunner refresh` re-reads the OBS releases, the encoder and settings
sources and the platform rules, then restamps. Re-verify when OBS 33 ships as stable.

History: [CHANGELOG.md](CHANGELOG.md).
