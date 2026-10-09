# Changelog — revenantworks-localops-comfyrunner

## [1.0.0] — 2026-10-01

First public release. Runs image, video and audio generation on a local ComfyUI server, and checks
each job before it reaches the GPU.

Description cut to about 600 characters, main use case first (2026-10-08).

### What it does

- Discovers the server and classifies each job from its graph (image, video, audio), never from a
  model list.
- Four guards, in order, before every run:
  1. the local LLM is off the GPU: each resident model is named and unloaded by its instance id on
     the owner's yes (or under a standing rule when unattended), never all at once;
  2. video decodes are tiled: an untiled decode on a video latent is refused, with the
     `VAEDecodeTiled` swap offered;
  3. the size fits a budget: pixels for images, pixels times frames for video, seconds for audio,
     scored against the owner's values with the ratio to the card's crash size;
  4. a small test runs first (832×480, 33 frames, 8 steps) with a projection of the full run's time.
- Two modes: interactive (proposals and missing readings are put to the owner) and unattended (every
  value must be the owner's, every reading measured and a clean test on record, or the job is set
  aside with the reason).
- Verifies each output and records what ran. Runs a pixelsmith generator brief and hands the
  candidates to pixelsmith's post-process and look test.

### Entry points

- `audit` (score the server and saved workflows; nothing runs), `check <workflow>`,
  `test <workflow>`, `run <workflow>` (test first), `status` (queue, VRAM, who holds the GPU, the
  last result), `refresh` (re-verifies and restamps the API notes).

### Scripts

- `workflow_guard.py` (the graph lint), `comfy_client.py` (the API client) and the pack-shared
  `gpu_preflight.py` (read-only GPU pre-flight), Python 3 stdlib, run and never read; tests ship
  beside them. The `lms` CLI is an optional, declared helper for the LLM unload.

### Safety rules

- Never starts or restarts ComfyUI, never edits its launch flags, never interrupts a running job,
  never commits or sends anything.
- Files reach ComfyUI through its API only. No packages, no cloud network; local HTTP only (default
  `127.0.0.1:8188`). Without a shell it hands back curl commands and marks each guard NOT-RUN.

### Integrations

- The localops GPU lease, shared with lmstudiorunner, whisperrunner and obsrunner, tells each runner
  whether another is mid-run.
- pixelsmith writes art briefs, owns the pixel post-process and judges the result; soundsmith writes
  game-sound briefs; agentwright designs the cadence and kill switch around a scheduled run.
