# Briefing — the artist brief and the generator prompt

Loaded for `pixelsmith brief`. Both templates are filled from a rule set; neither is written from nothing. The brief states the test the art will face, so the artist or the generator aims at the pass line and not at "nice".

## Contents

- What every brief carries
- Artist brief template
- Generator prompt template
- What a brief withholds
- Receiving the result

---

## What every brief carries

- The band model: what each band shows and what one asset becomes in it.
- The value ladder: the reserved ends, the 25-step gap, the per-material base/shadow/highlight.
- The color count per asset and the owner-color slot.
- The silhouette vocabulary: the shape word per class and the pose word per activity.
- The terrain set with the two check terrains named and their values stated.
- The pass line: the checklist lines the asset must clear, by number, and the scene it will be tested in.

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

Deliverables. <list of sprites and frames>, PNG, transparent background, unscaled.
Reference. The attached checklists (N1–N6, M1–M6, F1–F6) and the contrast table.
```

## Generator prompt template

One asset per prompt; a generator given a set produces a set that drifts.

```
Pixel art sprite, <w>x<h> pixels, <top-down | three-quarter> view, of <asset class> <doing activity>.
Flat colors, exactly <n> colors: base <#hex>, shadow <#hex>, highlight <#hex>, owner accent <#hex>.
Dominant value light (above 70 of 100) so it reads on dark terrain. Silhouette: <shape word>,
<pose word>. One-pixel outline in <#hex>. Transparent background. Crisp pixels, no smoothing.
Negative: no gradients, no anti-aliasing, no drop shadow, no text, no background scene, no
dithering, no extra colors.
```

Fill every angle bracket from the rule set. A generator that cannot hold a color count is told the palette twice — once as hex, once as the count — and its output is checked against the count in Entry — Test.

## What a brief withholds

- Engine detail the artist cannot act on: crossfade timings, aggregation thresholds, which zoom switches band. The brief says what one asset becomes at each band, not how the engine does it.
- Brand identity: no brand palette, wordmark, or tagline. A game's own palette is in the brief as the game's palette; a brand palette arrives only when brandwright has applied it and the owner says so.
- Names: no person, employer, or client name. "The owner", "the artist", "the game".

## Receiving the result

A delivered sprite or a generated image goes into the scene and through Entry — Test. The brief is not the acceptance; the scorecard is. A result that passes near but fails mid is returned with the M-line and the fix class, not a request to "try again".
