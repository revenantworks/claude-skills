# Trigger Evals — 20 queries (10 should / 10 shouldn't)

Read each cold against name + description only. Provenance: derived from revenantworks-gamedev-pixelsmith v1.0.0, 2026-08-29. **Re-anchored to v1.0.1, 2026-09-09 — provenance only, nothing executed here.** The 1.0.1 bump is bookkeeping for a run record added at the same member version; the `description` field is byte-identical to 1.0.0's, so the routing surface these queries judge did not move — no row, expectation or count touched, and no re-judge is owed by this bump. Authored, not run. **Re-anchored to v1.0.2, 2026-09-12 — provenance only, nothing executed here.** In full: the 1.0.2 bump restamped `references/pack.md` only — the gamedev roster became two members and the pack's first routing-seam row appeared. The `description` field is byte-identical to 1.0.1's, so the routing surface these queries judge did not move. No row, expectation or count touched, and no re-judge is owed. NOTE for the next run: a sibling now exists, and a trigger eval scores a description against its neighbours, so the next actual execution of this suite should include a query that could plausibly pull godotsmith.

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
| 10 | "pixelsmith" | SHOULD — bare invocation |
| 11 | "Draw me a 32x32 warrior sprite" | SHOULD NOT — drawing is an art tool's |
| 12 | "Implement the crossfade shader between the near and mid render bands in Godot" | SHOULD NOT — engineering |
| 13 | "Pick the brand palette for the studio's launch page" | SHOULD NOT — brandwright |
| 14 | "Make my platformer's hero sprite look better" | SHOULD NOT — near-miss: single scale, no band model |
| 15 | "Add dithering and a CRT filter to my retro game's sprites" | SHOULD NOT — near-miss: single-scale pixel-art polish |
| 16 | "Convert this photo into pixel art" | SHOULD NOT — near-miss: conversion, not direction |
| 17 | "Write the LOD system so distant units swap to billboards" | SHOULD NOT — near-miss: LOD code, not art rules |
| 18 | "Summarize this GDC talk about art bibles for my team" | SHOULD NOT — summary, not direction |
| 19 | "Build a skill for tracking my game's bug reports" | SHOULD NOT — skillwright |
| 20 | "Balance the unit stats so cavalry beats archers" | SHOULD NOT — game design, not art |

## Edge notes

Sharpest pair: 1 vs 14. Both are "my sprite looks wrong"; 1 names a second zoom level and terrain, 14 names one scale and no terrain. The description keys on *several zoom scales*, *vanishes against terrain*, and *zoomed out*; a single-scale polish ask carries none of those and stays off.

Second pair: 3 vs 18. An art bible to *build* fires; an art bible to *summarize* does not — the description claims building a style guide, not reading one.

Tuning rule: misses on 1–10 → make the band and terrain triggers pushier; fires on 11–20 → tighten the boundary sentence (drawing, engine, brand).
