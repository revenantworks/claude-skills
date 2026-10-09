# Media budgets and the four pre-flight guards

**Read this file when:** any step is about to submit a workflow (`run`, `test`), when
`check` scores one, or when the user asks why a job was refused, reduced or set aside.
`scripts/workflow_guard.py` computes everything here in one call; this file is the why.

## Contents

1. A reported case: the crash this exists for
2. The four guards, in order
3. Budgets per media type
4. Owner values in `gpu-config.json`
5. Tiled decode values
6. The test run and the projection
7. Unloading the LLM first — the lmstudiorunner seam
8. Hand-back
9. Verdicts and modes

---

## 1. A reported case: the crash this exists for

A measured case on one machine (a 16 GB consumer card with no memory-efficient
attention, native Windows ROCm; ComfyUI forced to math attention). It is a reference, not
your card: read your own card's VRAM live (`scripts/gpu_preflight.py`). Wan 2.2 TI2V 5B, **1024×1024, 121 frames,
20 steps, a plain `VAEDecode`**. Sampling finished in 44 minutes (about 133 s a step).
Twelve seconds into the decode the whole machine stopped with bugcheck 0x133,
`DPC_WATCHDOG_VIOLATION`. The cause is not proven. What is proven: the largest single
allocation of the run was a full-video decode in one pass, on a size no smaller run had
tried, on a card with no memory-efficient attention.

That run was 126,877,696 pixel-frames (1024 × 1024 × 121), at an aspect the model was
not trained at (its native is 1280×704). The guard reads the **crash reference** from
`gpu-config.json` `comfy.crash_size` (section 4) and every video job reports its ratio to
it. Unset, this reported case is the labelled `PROPOSED` figure: set your own card's
measured size, never inherit this one silently.

## 2. The four guards, in order

1. **Unload the LLM first** (section 7). One diffusion model and one LLM resident at once
   is the failure class the pack seam targets.
2. **Tiled decode for video.** A video latent decoded by a non-tiled node is refused, in
   both modes. `workflow_guard.py --write-fixed` swaps in `VAEDecodeTiled` (section 5).
3. **A resolution × frames budget.** Math attention makes memory and time grow faster
   than the pixel count. Every job is scored against the user's budget (section 3).
4. **A short low-resolution test before any long run.** Section 6. The test exercises the
   same decode path the full run will use, so a decode that would fail, fails small.

The order is fixed: an LLM still resident makes every later reading wrong.

## 3. Budgets per media type

| Media | Unit the guard counts | Why that unit |
|---|---|---|
| Image | pixels per pass (width × height) | One pass near 1 MP is what math attention handles at a usable rate (SDXL ran about 1.5 it/s at 1024² in the reported case's setup). Above it, generate near 1 MP and upscale as a second pass |
| Video | pixel-frames (width × height × frames) | The latent's token count scales with it; attention cost grows up to its square |
| Audio | seconds | The latent length scales with it. No audio failure is recorded; the budget is a placeholder |

Media class comes from the latent source's inputs — `width`/`height` with a frame count
is video, `seconds` is audio, `width`/`height` alone is image — and from the output
nodes (a video combine or save node turns an image-latent batch into frames). No model
name list; a new model with the same input shape is guarded the same way.

Shape notes (reported, never gating): Wan and Hunyuan frame counts are 4n+1; sizes off a
multiple of 16 are off-grid; far from the model's native size is off-distribution.

## 4. Owner values in `gpu-config.json`

The budgets are values, and a value is set by someone accountable for it. They live in
the pack's `gpu-config.json` (the same file as the headroom, `references/gpu-seam.md`
section 6), under a `comfy` key:

```json
{"comfy": {"crash_size": {"width": 1024, "height": 1024, "frames": 121},
           "image_pixels_max": 1048576, "video_pixel_frames_max": 63438848,
           "audio_seconds_max": 120, "max_run_minutes": 60,
           "unload_llm_before_run": true}}
```

| Key | Proposed when absent | Basis |
|---|---|---|
| `crash_size` | 1024 × 1024 × 121 (the reported case) | `{width, height, frames}` or a pixel-frame count; the reference every video ratio and the at-or-above-crash rule use. Unset, the report labels it `PROPOSED`, and it gates nothing on its own |
| `image_pixels_max` | 1,048,576 (1024²) | About 1 MP per pass under math attention |
| `video_pixel_frames_max` | half of `crash_size` (63,438,848 for the reported case) | Half the crash reference |
| `audio_seconds_max` | 120 | Placeholder; no measured failure |
| `max_run_minutes` | none | Projections are reported, not gated, until set |
| `unload_llm_before_run` | false | The user's standing yes to unload LM Studio (section 7) |

A proposal is labelled `PROPOSED` in the guard's output. **Interactive:** state it and its
basis, and ask. **Unattended:** refuse until the user sets it. Every report names the
value used and its source. This skill never writes `gpu-config.json`; the user does.

## 5. Tiled decode values

`--write-fixed` and the test variant use **`tile_size` 256, `overlap` 64,
`temporal_size` 32, `temporal_overlap` 8** — PROPOSED, smaller than the node defaults
(512/64/64/8) because the reported case failed in the decode. The test run is where they are
proved: a clean test decode at these values, then the full run at the same values. Raise
them only after a clean full run, one at a time, and say which. Tile seams can show as
faint grid lines; if they do, raise `overlap` first. Long audio: `VAEDecodeAudioTiled`
lowers decode memory at a small speed cost.

## 6. The test run and the projection

`workflow_guard.py WF --write-test TEST.json` writes a variant of the same graph:

- video: area scaled to at most 832×480 (aspect kept, sides on a multiple of 32), 33
  frames; image: at most 512×512, batch 1; audio: at most 10 s;
- sampler `steps` capped at 8; `filename_prefix` moved under `comfyrunner-test/`;
- every video decode tiled with the section 5 values.

Run it, then `workflow_guard.py WF --baseline TEST.json --baseline-seconds S` with the
test's wall time from `/history`. The projection is a range:
`full steps × (S ÷ test steps) × work ratio^p`, with p = 1 (low, linear) and p = 2 (high,
attention). The per-step figure includes load and decode, so it is an upper bound per
step; the range is wide on purpose. Against `max_run_minutes`: low bound over → `reduce`;
high bound over → `ask`. A test that errors, or decodes wrong (black frames, tiling
grid), stops the full run: report it with the node and the exception.

**No full run without a clean test run in the same session** — unless the same workflow,
at the same size, already finished cleanly on this machine and the user says so.

## 7. Unloading the LLM first — the lmstudiorunner seam

Run `python scripts/gpu_preflight.py --holder comfyrunner --mode <mode>` (no `--model`:
this is an occupancy read). It reads the pack lease, LM Studio's loaded instances and
ComfyUI's queue. Then:

- **Lease held by another holder and live** (lmstudiorunner mid-run, or `owner`): its work
  is in flight. Do not unload anything. Interactive: say who holds it and why.
  Unattended: set the job aside as `GPU busy`.
- **Stale lease:** report its content. The user clears it; never taken over unattended.
- **LM Studio instances resident, no live lease:** name each one by instance id.
  **Interactive:** propose unloading each named instance (`lms unload <instance id>`) and
  run it on the user's yes. **Unattended:** run it only when `unload_llm_before_run` is
  `true` in `gpu-config.json`; otherwise set the job aside. Never `lms unload --all`: it
  can evict an instance another session loaded by hand (`gpu-seam.md`, release table).
  Without the `lms` CLI, unload each by `POST /api/v1/models/unload` with its instance id.
- **Re-run the pre-flight** after any unload and act on the new verdict, never the old one.
- **Take the lease** (`comfy_client.py lease take --purpose "…" --minutes N --est-ram-gib R`),
  with an expiry longer than the projection's high bound, and renew it on long runs.

**RAM in the lease (owner Q24).** Every GPU holder records `est_ram_bytes`. For a ComfyUI
run, R is at least the sum of the workflow's model files (checkpoint, text encoders, VAE —
each loads through system RAM, and offloaded weights stay there), plus a few GiB for a video
decode. State the figure and how it was summed. Without it the lease records RAM as
unknown, and dockerrunner and hypervrunner ask or refuse until the lease is released.

This is the mirror of lmstudiorunner's rule in `gpu-seam.md` section 4: each runner frees
its own models at hand-back, and touches the other's only when the lease or the user
says it may.

## 8. Hand-back

When the run, or the batch of runs the user asked for, is done: `comfy_client.py free`
(refuses while anything is queued), then `comfy_client.py lease release`. Never reload the
LLM; lmstudiorunner loads what it needs. Report what was freed.

## 9. Verdicts and modes

The guard and the pre-flight print `go`, `ask`, `reduce`, `unmeasured` or `refuse`; the
worst wins, and the skill acts on the worse of the two.

| Verdict | Interactive | Unattended |
|---|---|---|
| `go` | Run | Run |
| `ask` | State the reason, ask | Refuse, set aside with the reason |
| `reduce` | Offer the smaller size, frames or steps, re-check | Set aside; never shrink the user's job unasked |
| `unmeasured` | Say which reading is missing, ask | Refuse |
| `refuse` | Explain, offer the fix (`--write-fixed`, a smaller job) | Set aside |

At or above the crash reference: interactive runs name the crash and ask; unattended runs
never start it.
