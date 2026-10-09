# Recipes — what each model family needs before submit

**Read this file when:** Classify names the family of a workflow, or a submit came back with
`node_errors`, or a job is a thumbnail. Measured times are this machine's, never a promise
for another card.

## Contents

1. The recipe check
2. Family table
3. Measured times
4. Thumbnail brief
5. Refreshing this file

---

## 1. The recipe check

`comfy_client.py nodes WF --save-info INFO.json` reads `/object_info` for every class in the
workflow and saves it. `workflow_guard.py WF --object-info INFO.json` then refuses, with the
reason, before anything is submitted:

- a **node class** the server does not have (a custom node not installed);
- a **choice input** whose literal value the server does not offer — a loader's file
  (`ckpt_name`, `unet_name`, `clip_name`, `vae_name`, `lora_name`) that is not in its model
  folder, or any other option that is not on the list;
- a **CLIP loader `type`** that does not match the family the latent source names (section 2).
  A wrong type loads the wrong tokenizer; the run fails late or produces noise.

Each refusal names the node, the input and the value. The fix is the user's: install the
node, put the file in place, or pick the listed option. The skill never edits the graph to
make a check pass, and never builds a path into ComfyUI's folders to look for a file.

## 2. Family table

The family is read from the latent source's class, never from a model file name.

| Family (latent source class contains) | Media | CLIP loader `type` | Shape rules |
|---|---|---|---|
| `Wan` | video (image-to-video, text-to-video) | `wan` | frames 4n+1; sides on a multiple of 16; tiled decode always |
| `Hunyuan` | video | `hunyuan_video` | frames 4n+1; tiled decode always |
| `LTXV` | video | `ltxv` | frames 8n+1; tiled decode always |
| `EmptyLatentAudio` / `StableAudio` | audio | `stable_audio` | seconds against the audio budget |
| `EmptyLatentImage` / `EmptySD3LatentImage` | image | the checkpoint's own encoder (no `type` to match) | near 1 MP per pass, then upscale |
| `EmptyFlux2LatentImage` | image, FLUX.2 Klein (UNETLoader + CLIPLoader + VAELoader) | `flux2` | BasicGuider, KSamplerSelect euler, `Flux2Scheduler` at 4 steps, SamplerCustomAdvanced; near 1 MP |
| `EmptySD3LatentImage` with a UNETLoader Z-Image file | image, text in images | `lumina2` | ModelSamplingAuraFlow shift 3, 8 steps, res_multistep, simple, cfg 1 |

The `type` strings are read from `/object_info` on the user's server; when the server's list
differs from this table, the server wins and this file is refreshed (section 5).

### Picking the family from the job

When the user names the result but not the model, the job picks the family, from what is
installed (`/object_info` loader lists), and the pick is stated with its reason:

| The job | Family | Why |
|---|---|---|
| Legible text in the image (a sign, a title) | Z-Image | renders short text exactly |
| An edit of an existing image (change one part, keep the rest) | FLUX.2 Klein, reference edit | the reference holds the rest; paste back the region |
| A style a LoRA carries (pixel art, a set look) | SDXL + the LoRA | the LoRA ecosystem is SDXL's |
| More pixels from a finished image | an upscale model (RealESRGAN x4, then scale down) | no new content |
| Motion | a video family, with every video guard | never an image family |
| A transparent cutout of a finished image | BiRefNet through the core `RemoveBackground` node ("Background removal" below) | a segmentation model separates by shape, not by brightness |

A family that is not installed is named with the job it would serve, never substituted silently.

### Batching by model

The first load dominates a short job. Queue a batch grouped by model (every Klein job, then every
Z-Image job), never interleaved; a switch evicts and reloads. Families that share a text encoder
(Klein and Z-Image both use `qwen_3_4b`) switch faster than unrelated ones, which the measured
times show.

### Reference edits (FLUX.2 Klein)

An edit encodes the source with `VAEEncode` into `ReferenceLatent` on the conditioning, over an empty
Flux2 latent; a second reference chains a second `ReferenceLatent`. **It is a full redraw, not an
inpaint:** every pixel is regenerated, so an edit meant for one region is pasted back into the source
by a mask in code, and the result is compared against the source outside that region before it is
kept. Where a flat copy of a render is wanted (for tracing), ask for the same shapes with no texture;
check that small details (a spike, a notch) survived, because the copy tends to straighten them.

### Prompt budget by family

One prompt across families is not one test: budget it to the encoder that reads it.

| Family | Text encoder | Budget |
|---|---|---|
| SDXL, SD1.5 | CLIP, 77 tokens per chunk (start and end markers included) | the traits that must survive (identity, colours, palette) go first; keep under about 70 tokens, or carry the look in a reference image or a LoRA. Traits past the first chunk are often lost |
| Z-Image, FLUX.2 Klein | an LLM text encoder | long prompts are read whole; order still helps, but length is not the limit |

`workflow_guard.py` reads back each sampler's positive and negative text (first 120 characters)
and adds a note, never a refusal, when an SDXL or SD1.5 positive prompt is likely over 77 tokens.
The count is an estimate from words and punctuation; CLIP splits rare words further, so the true
count is usually higher.

### Background removal

| Model | File | Node | Known failure | Fallback |
|---|---|---|---|---|
| BiRefNet (Comfy-Org) | `models/background_removal/birefnet.safetensors` | core `RemoveBackground`; the only model it loads | on an AMD card under Windows ROCm (gfx1030), every GPU job can fail with `miopenStatusUnknownError` | the same weights on the CPU, below |

**Never retry the GPU path blind.** One `miopenStatusUnknownError` on this node means the kernel
fails on this card; a retry spends the queue and fails the same way. For a handful of images the
CPU is the fastest honest path (well under a minute an image at 1024):

- run a short script with the ComfyUI install's own venv Python, with the ComfyUI package folder
  on `sys.path`;
- put `--cpu` in `sys.argv` **before** the first `import comfy`, so ComfyUI's device choice
  never touches the GPU;
- build ComfyUI's own `comfy.background_removal.birefnet.BiRefNet` class in float32 on the CPU
  and load the safetensors state dict into it; report missing and unexpected keys (both should
  be 0);
- feed the image as RGB in the 0–1 range, resized to 1024×1024; apply a sigmoid to the output
  logits, then resize the mask back to the source size (bicubic) and use it as alpha.

The script is the caller's, written per run and not shipped here: its imports follow ComfyUI's
code, which moves between versions. Check each cutout on a dark and on a light ground before
handing it back.

## 3. Measured times

| Family and job | Size | Steps | Measured | Source |
|---|---|---|---|---|
| Wan 2.2 TI2V 5B, plain decode | 1024×1024×121 | 20 | about 133 s a step; the decode crashed the machine | media-budgets.md section 1 |
| SDXL base, image | 1024×1024 | — | 1.5 it/s | media-budgets.md section 3 |
| FLUX.2 Klein 4B, one-reference edit | 512×512 test | 4 | 18-24 s | /history, 2026-10-02 |
| FLUX.2 Klein 4B, one-reference edit | 1024×1024 | 4 | 50-70 s (first run includes the load) | /history, 2026-10-02 |
| FLUX.2 Klein 4B, two-reference edit | 1024×1024 | 4 | 184-196 s | /history, 2026-10-02 |
| Z-Image Turbo, text to image | 1024×1024 | 8 | 34 s first after a Klein session (text encoder already resident), 26 s warm | /history, 2026-10-03 |
| Any other family or size | — | — | not measured | the first clean test run measures it |

A row is added only from a finished run's `/history` wall time, with its date, size, steps and
decode settings. The test run (media-budgets.md section 6) is the measurement; a projection is
never written here as a measured time.

## 4. Thumbnail brief

For a video thumbnail generated in ComfyUI (obsrunner grabs frames from a recording; this is
generating new art):

- **Size:** 16:9 at 1280×720 or larger for a long video; 9:16 for a short. Generate near 1 MP
  at the aspect, then upscale as a second pass to the target size.
- **Text:** never generated. Leave clear space for a title; the words are placed afterwards
  by hand or in an editor, and their wording is commscribe's.
- **Faces and likeness:** only the user's own material, from a reference image the user
  supplies.
- **Output:** two to four candidates, each recorded with its seed, for the user to pick.

## 5. Refreshing this file

`comfyrunner refresh` re-reads `/object_info` for the CLIP loaders on the live server and
compares their `type` lists with section 2. A new or renamed type is added with the date; a
family the server no longer offers is marked, not deleted.
