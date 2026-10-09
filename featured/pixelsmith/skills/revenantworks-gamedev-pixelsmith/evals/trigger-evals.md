# Trigger Evals — 26 queries (12 should / 14 shouldn't)

Counts: 26 queries (12 should, 14 should-not, 5 pairs)

Read each cold against name + description only. Provenance: derived from v1.0.0 (2026-08-29); re-anchored at v1.0.1, v1.0.2 and v1.1.0 (history in CHANGELOG.md; query 19 became the godotsmith near-miss at 1.1.0). **2026-10-01, pack-split unit PX, version unchanged at v1.1.0:** the description was rewritten for the `3d` mode and its brand pointer renamed to brandscribe, so every row was re-judged against the new text; rows 21-24 were added as two should / should-not pairs for the mode (count 24, 12 / 12). Run record in `evals/RESULTS.md`. **2026-10-01, pack-split unit FX5 (audit A5, PX-P2-2), version unchanged:** rows 25-26 added as should-not boundaries for comfyrunner and soundsmith, the two named siblings with no row (count 26, 12 / 14); judged cold against the current description, both route away. **Re-anchored to v1.0.0, 2026-10-01:** 1.0.0 launch version; suite content unchanged from the build the A6 evals ran against.

| # | Query | Expected |
|---|---|---|
| 1 | "The huts disappear against the forest terrain when I zoom out to the formation view" | SHOULD — vanishes against terrain |
| 2 | "Run the cross-band art look test on this scene" | SHOULD — test entry |
| 3 | "Write a pixel-art style guide for the carrier game — fighters, wings, and fleets have to read at every zoom" | SHOULD — art bible, zoom bands |
| 4 | "Brief a pixel artist for 16 px units that must read as formation blocks at distance" | SHOULD — brief entry |
| 5 | "Which sprite size should I use for a colony sim that zooms from one person to the whole region?" | SHOULD — per-scale rule |
| 6 | "Design the strategic icons for the zoomed-out map, like an RTS does" | SHOULD — far-band icon vocabulary |
| 7 | "pixelsmith audit — score this art bible against your rules" | SHOULD — audit entry |
| 8 | "Write the prompt for the sprite generator so the warriors read on both hills and forest" | SHOULD — generator brief |
| 9 | "I can't upload the screenshot — can we still check whether the scene reads at each band?" | SHOULD — text-described path |
| 10 | "pixelsmith" | SHOULD — bare invocation; Direct (the default) is the expected reply |
| 11 | "Draw me a 32x32 warrior sprite" | SHOULD NOT — drawing is an art tool's |
| 12 | "Implement the crossfade shader between the near and mid render bands in Godot" | SHOULD NOT — engineering |
| 13 | "Pick the brand palette for the studio's launch page" | SHOULD NOT — brandscribe |
| 14 | "Make my platformer's hero sprite look better" | SHOULD NOT — near-miss: single scale, no band model |
| 15 | "Add dithering and a CRT filter to my retro game's sprites" | SHOULD NOT — near-miss: single-scale pixel-art polish |
| 16 | "Convert this photo into pixel art" | SHOULD NOT — near-miss: conversion, not direction |
| 17 | "Write the LOD system so distant units swap to billboards" | SHOULD NOT — near-miss: LOD code, not art rules |
| 18 | "Summarize this GDC talk about art bibles for my team" | SHOULD NOT — summary, not direction |
| 19 | "The band alpha clamp hides units at mid — check the clamp value against the band spacing" | SHOULD NOT — near-miss: godotsmith (a number checked against a bar), pair of 1 |
| 20 | "Balance the unit stats so cavalry beats archers" | SHOULD NOT — game design, not art |
| 21 | "My units are pixel sprites on billboards in the 3D orbit view and they blur when I zoom — what are the art rules?" | SHOULD — `3d` mode, billboard rules |
| 22 | "pixelsmith 3d — write the rules for carrying our pixel look into the 2.5D band" | SHOULD — `3d` mode, explicit |
| 23 | "Write a low-poly style guide for my 3D platformer" | SHOULD NOT — near-miss: general 3D art, no pixel grid |
| 24 | "Set up the SubViewport so my 3D scene renders at 640x360 and upscales cleanly" | SHOULD NOT — near-miss: engine setup (godotsmith / the game's engineering) |
| 25 | "Run this diffusion workflow on my GPU and save the sprites" | SHOULD NOT — near-miss: comfyrunner (rendering a workflow, not directing art) |
| 26 | "My footstep loop clicks at the seam" | SHOULD NOT — near-miss: soundsmith (game audio, not pixel art) |

## Edge notes

Sharpest pair: 1 vs 14. Both are "my sprite looks wrong"; 1 names a second zoom level and terrain, 14 names one scale and no terrain. The description keys on *several zoom scales*, *vanishes against terrain*, and *zoomed out*; a single-scale polish ask carries none of those and stays off.

Sibling pair: 1 vs 19 (added at v1.1.0, replacing a skillwright query so the count stays 10 / 10). Both say units vanish at mid; 1 is a complaint by eye and fires here, 19 asks for a clamp checked against arithmetic and belongs to godotsmith, per the pixelsmith ↔ godotsmith seam in `references/pack.md`.

Second pair: 3 vs 18. An art bible to *build* fires; an art bible to *summarize* does not — the description claims building a style guide, not reading one.

3D pairs: 21 vs 24 (both name a 3D render at pixel scale; 21 asks for art rules and fires, 24 asks for viewport setup and belongs to the engine side, per the pixelsmith ↔ godotsmith seam) and 22 vs 23 (both ask for a 3D style guide; 23 has no pixel grid, so it is general 3D art and stays off). Query 17 (LOD code swapping units to billboards) must still not fire after the description gained "billboard sprites": it asks for code.

Tuning rule: misses on 1–10 → make the band and terrain triggers pushier; fires on 11–20 → tighten the boundary sentence (drawing, engine, brand).
