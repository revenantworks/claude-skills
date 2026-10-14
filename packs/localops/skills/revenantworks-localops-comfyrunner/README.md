# revenantworks-localops-comfyrunner

Runs image, video and audio generation on a local ComfyUI server — and checks the
job before it reaches the GPU, because the wrong video job can take the whole
machine down.

## Why it exists

In a reported case (a 16 GB consumer card running under math attention), a
Wan 2.2 video render at 1024×1024 and 121 frames sampled for 44
minutes and then crashed the whole PC twelve seconds into the decode. The decode
was untiled. Nothing warned about the size, nothing had tried a smaller run first,
and an LLM might as well have been resident on the same card.

Several ComfyUI tools already exist. They build, submit and watch workflows well.
None of them looks at a graph before it runs and says *this one is too big, and
its decode is the kind that crashed you last time.* That is this skill's job.

## The four guards

Every run passes them, in order:

1. **The LLM is unloaded first.** LM Studio and ComfyUI share one card. The pack's
   GPU lease tells each runner whether the other is mid-run. Each resident model
   is named and unloaded by its instance id on your yes (or, unattended, only when
   you have set the standing rule); never all at once.
2. **Video decodes are tiled.** An untiled decode on a video latent is refused,
   and the skill offers the `VAEDecodeTiled` swap.
3. **The size fits a budget.** Pixels for images, pixels × frames for video,
   seconds for audio — scored against your values, with the ratio to your card's
   crash size (`comfy.crash_size`; the reported case until you set it). Until you
   set a value, it is a labelled proposal.
4. **A small test runs first.** The same graph, scaled down to 832×480, 33
   frames and 8 steps, with a projection of how long the full run will take.

## The two modes

**Interactive** — you are watching. Proposals, near-crash sizes and missing
readings are put to you.

**Unattended** — nobody is watching. Every value must be yours, every reading
measured, and a clean test on record. Anything less is set aside with the
reason.

## Entry points

| Command | What it does |
|---|---|
| `comfyrunner audit` | Score the server and your saved workflows against the guards; nothing runs |
| `comfyrunner check <workflow>` | Lint one workflow: media, size, budget, crash ratio, decode, the fix |
| `comfyrunner test <workflow>` | The pre-flight, one short test run, and the projection |
| `comfyrunner run <workflow>` | The whole sequence, test first |
| `comfyrunner status` | Queue, VRAM, who holds the GPU, the last result |
| `comfyrunner refresh` | Re-verify the API notes and restamp them |

## Pixel art with pixelsmith

pixelsmith writes the brief — the prompt, the spec block, the palette — and owns
the post-process. This skill only renders: it runs the generator inside its four
guards, records what it ran, then runs pixelsmith's own `scripts/pixel_post.py`
on each candidate and hands the survivors to `pixelsmith test`, which decides.

## Requirements

A ComfyUI server on this machine (default port 8188). Optional: Python 3 for the
four scripts (its own `scripts/workflow_guard.py`, `scripts/comfy_client.py` and
`scripts/gpu_preflight.py`, plus pixelsmith's `scripts/pixel_post.py` when
pixelsmith is installed) and the `lms` CLI for the LLM unload. No packages, no
cloud network.
Without a shell it hands back the exact `curl` commands and marks each guard
NOT RUN.

## What it is not

It does not write art briefs or judge art (pixelsmith), run LM Studio models
(lmstudiorunner), or design the schedule and kill switch around an unattended
run (agentwright). It never starts or restarts ComfyUI, never edits its launch
flags, never interrupts a running job, and never commits or sends anything.
