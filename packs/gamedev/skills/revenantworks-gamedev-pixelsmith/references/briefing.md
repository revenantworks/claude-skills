# Briefing — the artist brief and the generator prompt

Loaded for `pixelsmith brief`. Both templates are filled from a rule set; neither is written from nothing. The brief states the test the art will face, so the artist or the generator aims at the pass line and not at "nice".

## Contents

- What every brief carries
- The spec block (every brief emits one)
- Artist brief template
- Generator prompt template — instruction-following generator
- Diffusion generator — prompt plus post-process contract
- Style lock for a set
- What a brief withholds
- Receiving the result

---

## What every brief carries

- The band model: what each band shows and what one asset becomes in it.
- The value ladder: the reserved ends, the 25-step gap, the per-material base/shadow/highlight.
- The color count per asset and the user-color slot.
- The silhouette vocabulary: the shape word per class and the pose word per activity.
- The terrain set with the two check terrains named and their values stated.
- The pass line: the checklist lines the asset must clear, by number, and the scene it will be tested in.
- For an animated asset: the frame count per activity, the direction count per class (4 or 8), and the animation value rule from `band-rules.md`.
- The spec block below.

## The spec block (every brief emits one)

The palette and the hard constraints also go out as one fenced block, so a quantizer, a palette-snap step or a pre-screen reads them without parsing prose. The prose brief and the block must agree; where they differ, the block is corrected.

**Every palette entry is a hex taken from the palette's own record** (the brand definition, the art bible), with its source. A colour named without a hex ("gunmetal grey") is an open item resolved there before any snap runs; it is never sampled from the art, because the art carries the generator's drift, not the palette.

```spec
asset:        <class> — <activity>
native:       <w>x<h> px            # the sprite's real pixel size
grid:         <cell> px
directions:   <1 | 4 | 8>              # 8 for a sprite on a 3D-band billboard
palette:      [#rrggbb, #rrggbb, …]  # ordered: darkest to lightest
palette_source: <record and section>  # where every hex above was read; a runner refuses a palette without it
count:        <n>                    # len(palette); the snap enforces it
owner_slot:   <index into palette>
dominant:     <value 0-100>          # target dominant value after snap
terrains:     {<A>: <value>, <B>: <value>}
key_colour:   #rrggbb                # background only; outside the palette, far from every value
pass_lines:   [N1, N2, N3, M2, M3, …]  # add D2, D3 for a 3D band
```

For a sprite shown in a 3D band (`pixel-3d.md`), the brief also states: even pixel width, foot pivot, the mirroring rule (mirror only a left-right symmetric design), and the outline colour and width shared with the mesh pass.

## Artist brief template

```
BRIEF — <asset class or set> — <game> — <date>

Purpose. This art is drawn once and read at <n> zoom bands: <near / mid / far — what each shows>.
It will be tested in one scene on <terrain A> (value <a>) and <terrain B> (value <b>) and must
pass every line of the near, mid, and far checklists attached.

Canvas. <grid> px grid. Person <h> px tall; building at least <2h> wide; animal under <h> tall.
Top-down / three-quarter view at <angle>. No anti-aliasing against transparency.

Value. Dominant value at <70+ | 15−>. Shadow = base − 15 to 20; highlight = base + 10 to 15.
Highlights cover no more than a tenth of the sprite. Six to twelve colors per asset.

Owner color. One slot, hue only, value <v> ± 5, at most a fifth of the sprite's pixels.
Owners: <list of hues>.

Silhouette. <class>: <shape word>. Activities: working — <pose word>; fighting — <pose word>;
idle — <pose word>. Each shape is unique to its class or activity.

Mid-band rule. Interior detail collapses at mid; the sprite's job there is an even cell in a
block. No highlight the size of the body.

Far-band rule. This asset does not appear at far; its class icon is <shape>. Do not draw an icon.

Style lock. Match the set to <reference sprite>. The whole set is re-checked on both terrains.

Deliverables. <list of sprites and frames>, PNG, transparent background, unscaled.
Reference. The attached checklists (N1–N6, M1–M6, F1–F6) and the contrast table.
```

## Generator prompt template — instruction-following generator

For a generator that obeys stated counts, sizes and colours (a sprite service with palette and size parameters). A diffusion model does not: use the next section. When the request does not say which kind, fill this template and the spec block, and offer the diffusion variant in one line. Every generator brief asks for one object per generation and states the grid size; a scene is assembled from separate sprites, never prompted whole, and a set in one prompt drifts.

```
Pixel art sprite, <w>x<h> pixels, <top-down | three-quarter> view, of <asset class> <doing activity>.
Flat colors, exactly <n> colors: base <#hex>, shadow <#hex>, highlight <#hex>, owner accent <#hex>.
Dominant value light (above 70 of 100) so it reads on dark terrain. Silhouette: <shape word>,
<pose word>. One-pixel outline in <#hex>. Transparent background. Crisp pixels, no smoothing.
Negative: no gradients, no anti-aliasing, no drop shadow, no text, no background scene, no
dithering, no extra colors.
```

Fill every angle bracket from the rule set, and attach the spec block. The output is checked against the block's count and palette in Entry — Test.

**Every colour gets a job.** A bare colour list lets the generator spend its brightest colour on the biggest shape: a recorded run repainted a dark hooded figure's whole cloak in the palette's off-white. In the prompt, name what each colour paints and the surfaces it must never touch (the light colour above all), and when a reference image is attached, restate its key colours in the "keep" clause ("the dark grey hood, never white or pale"), because a colour list later in the prompt outweighs a bare "keep it exactly".

## Diffusion generator — prompt plus post-process contract

A diffusion model (a Stable Diffusion checkpoint with a pixel-art LoRA, for example) cannot hold an exact colour count, a hex palette, an exact pixel size or a transparent background. Its "pixels" are soft cells several screen pixels wide that become real pixels only after a downscale. So the prompt carries only intent, and every hard constraint moves into a post-process contract that the runner executes and that pixelsmith states as requirements. Model-specific numbers (the LoRA's downscale factor, the VAE, sampler settings) belong to the runner that owns the model, not to the brief.

**One object per generation** (above): a diffusion prompt naming two objects (a hut beside a campfire) merges them. The grid is stated as native size and the integer factor to the generation size (for example 128 px native at 1024, factor 8).

**Prompt.**

```
<the LoRA's own style words>, pixel art, <top-down | three-quarter> view, <asset class> <doing activity>,
silhouette <shape word>, <pose word>, simple, flat colors, limited palette, light high-contrast subject,
plain <key colour name> background
Negative: <the LoRA's own negatives>, 3d render, realistic, gradient, soft shading, blurry,
anti-aliased, text, background scene
```

Never in a diffusion prompt: "transparent background", "exactly <n> colors", a hex value, or a pixel size. Each is asked of a model that cannot deliver it, and each belongs to the contract below.

**Post-process contract** — the runner does these, in this order, on every candidate:

1. **Native grid.** Generation size = native size × one integer factor (the model's own), inside the model's single-pass limit. A subject that does not fill the frame is cropped, never resampled.
2. **Downscale.** Nearest-neighbour, integer factor only, then re-detect the grid (a LoRA's cell grid is approximate). Any bilinear or bicubic step fails the asset.
3. **Palette snap.** Quantize to the spec block's exact palette, count included. The value-gap check runs after the snap, on the snapped colours.
4. **Key out.** Remove the flat key colour after the snap. Transparency is made here, never asked for. A cutout of a dark subject from a dark render (no flat key) uses a segmentation model or a re-render on a flat chroma ground, never a brightness key: the subject and the ground share a value range, so any threshold leaks into the body or keeps the floor.
5. **Candidates and record.** N candidates per asset; each carries checkpoint, LoRA and weight, sampler, steps, CFG, seed, VAE and the model licence, so a passing asset is reproducible.
6. **Pre-screen.** A mechanical check per candidate from the spec block: colour count, off-palette pixel count, dominant value, gap per terrain. Only survivors go on.
7. **Acceptance.** Survivors go through Entry — Test. The brief is not the acceptance; the scorecard is.

The contract is pixelsmith's, and so is its script: `scripts/pixel_post.py` (stdlib; run, not read) runs steps 2–4 and 6 on any generator's candidate. A local runner such as `revenantworks-localops-comfyrunner` (ComfyUI) only renders: it generates at the native grid and writes the step-5 record; the script then runs on its candidates and the survivors go to step 7. The runner is named, never required; with no shell, hand back the script command and mark the post-process NOT-RUN. pixelsmith never draws or generates.

## Style lock for a set

A set briefed one asset at a time still drifts unless it shares a lock. Every set brief, artist or generator, carries one style-lock line: for an artist, the one reference sprite the set is matched to; for a generator, a shared seed family, one LoRA weight and one reference image, recorded in each candidate's record. When the set is done, the contrast table in `contrast.md` is re-run across the whole set, so drift shows as a number, not an impression.

## What a brief withholds

- Engine detail the artist cannot act on: crossfade timings, aggregation thresholds, which zoom switches band. The brief says what one asset becomes at each band, not how the engine does it.
- Brand identity: no brand palette, wordmark, or tagline. A game's own palette is in the brief as the game's palette; a brand palette arrives only when brandscribe has supplied it and the user says so.
- Names: no person, employer, or client name. "The user", "the artist", "the game".
- Credentials: no API key, token or account detail, ever. A service generator takes its key from the runner's own environment. The model licence travels with each asset in the runner's record (contract step 5); the brief requires the record, it never carries the key.

## Receiving the result

A delivered sprite or a generated image goes into the scene and through Entry — Test. The brief is not the acceptance; the scorecard is. A result that passes near but fails mid is returned with the M-line and the fix class, not a request to "try again".

**Assemble before you re-prompt.** When several candidates edited from one base each get a different part right, measure their alignment first (mean difference over a region that should not move). Aligned candidates are composited: each part from the candidate that got it right, joined by feathered masks (hand-traced silhouettes where outlines do not close), and the next generator call harmonises the composite with only the changed region pasted back. After two drifts on an otherwise approved image, stop re-describing the whole picture: a generator gives parts, not a picture.

**One piece at a time.** A change with more than two visual parts is split into pieces, one part each; each piece is shown alone, at real size and in place, and approved before the next is built on it. "Iterate until it looks right" means iterate each piece, never skip the approvals: a self-judged final hides every wrong guess inside one picture. A dictated request is read back as numbered pieces first, since speech-to-text garbles terms.
