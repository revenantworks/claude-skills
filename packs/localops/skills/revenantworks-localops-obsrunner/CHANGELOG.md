# Changelog — revenantworks-localops-obsrunner

## [1.0.0] — 2026-10-01

First public release. Drives OBS Studio through its built-in WebSocket, read-only by default, and
turns its recordings into clips, vertical versions, chapters and upload sheets on the same machine.

Description cut to about 600 characters, main use case first (2026-10-08).

### What it does

- Live-safe OBS: reads freely, writes one confirmed change at a time (scene, source, mute, volume,
  profile parameter), and refuses every go-live, output, hotkey and stream-service request before it
  is sent. Responses are masked.
- Audit: profile rows against this GPU (encoder, rate control, keyframes, AMF B-frames, recording
  format, the VOD music track, disk).
- Check: a 20-second stats window that names render, encode, network or disk as the bottleneck.
- Marks: a chapter mark and a line in the marks sidecar; `--replay` saves the replay buffer.
- Post: `cut`, `vertical` (fixed crop per segment), `captions` (burn-in), `loudness`, `frames`,
  `chapters` (from markers) and `moments` (best moments from marks, transcripts and loudness peaks).
- Proved renders: pre-flight, a 5-second test render, the full render, a re-probe (yuv420p,
  H.264/HEVC, AAC, duration within a frame) and a receipt with hashes.
- An upload sheet per clip that the owner uploads from.
- One GPU, shared: no GPU render while OBS is live or recording; `hold` makes the other runners wait
  during a session and `release` drops the lease.

### Entry points

- `audit`, `check`, `set <change>`, `mark [label]`, `post <sub-mode> <recording>`, `sheet <clip>`,
  `status`, `hold`, `release`, `refresh`.

### Scripts

- `obs_ws.py` (the allow-list gate), `obs_audit.py` (offline profile audit), `obs_post.py` (the post
  sub-modes, sheet, hold and release) and the pack-shared `gpu_preflight.py`, Python 3, run and never
  read. `test_obsrunner.py`: 47 tests with a fake client and fake FFmpeg; no OBS or GPU needed.
- Drives one owner-installed package, `obsws-python`, for live modes; `audit` and `post` work without
  it. FFmpeg and FFprobe on PATH for `post`.

### Safety rules

- Never starts or stops a stream, never reads the stream key and never uploads. Chat moderation is
  out of scope.
- A check that did not run is NOT-RUN, never a pass. Loopback only, no cloud key.
- Installs nothing: `references/install-walkthrough.md` gives the owner steps, each with a verify and
  a rollback.

### Integrations

- Caption files come from whisperrunner, thumbnail art from comfyrunner, titles and descriptions
  from commscribe, analytics CSVs from duckrunner. gatewarden ships a go-live block hook as a second
  lock.
