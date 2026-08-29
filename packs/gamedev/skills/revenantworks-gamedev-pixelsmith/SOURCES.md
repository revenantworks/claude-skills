# Sources

All checked live 2026-08-29 during the build's research pass. Fetched pages were read as data; none carried a directive addressed to the run.

## Skill format

| Claim | Source |
|---|---|
| Name ≤64 chars, description ≤1024 third person, body ≤500 lines, references one level deep, TOC on long reference files | platform.claude.com — Agent Skills, "Skill authoring best practices" (fetched 2026-08-29) |
| Official skill set carries no game-art-at-scale skill (canvas-design, algorithmic-art, brand-guidelines are the nearest) | github.com/anthropics/skills (checked 2026-08-29) |

## Niche scan

| Finding | Source |
|---|---|
| `create-game-assets` covers art direction and a pipeline for cohesive sprites, tiles, icons; nothing on readability across zoom levels | github.com/gamedev-skills/awesome-gamedev-agent-skills (fetched 2026-08-29) |
| Sprite generation, palette, dithering, retro constraints — single scale | LobeHub `pixel-art-game-builder`, `game-art`; mcpmarket `pixel-art-generator`, `pixel-art-professional`; `pixellab-create-character`; SpriteCook/skills; agent-sprite-forge (searched 2026-08-29) |
| No art-direction entries surfaced in the directory listing | skills.sh (fetched 2026-08-29) |

## Craft

| Claim | Source |
|---|---|
| Grayscale value test; black-silhouette test; squint test; 6–12 colors per sprite; clustered shading | Pixnote "Pixel Art Tips and Tricks" and "How to Draw Pixel Art Characters"; generalistprogrammer "Pixel Art Tutorial"; sprite-ai "How to create 16x16 pixel art sprites" (searched 2026-08-29) |
| Strategic icons: shape = unit class, glyph = role, tick marks = tier; icons replace models when zoomed out | Stardock dev journal, "Supreme Commander: Forged Alliance Analysis" (searched 2026-08-29) |
| Icons too small at high resolution, invisible with dark team colors, confusing when stacked | FAForever forum, "Color coded strategic icons" (searched 2026-08-29) |
| Zoom-out swaps buildings for icons and the map for a colored overview | Songs of Syx Steam discussions, "Zoom out screenshots?" and "Map Zoom" (searched 2026-08-29) |
| Far pawns become dots, silhouettes, or markers at far zoom | pardeike/CameraPlus README (searched 2026-08-29) |
| Square tilesets read as graphics, rectangular ones as text — legibility trades against look | Dwarf Fortress wiki, "Tilesets" (searched 2026-08-29) |
| Luminance weights 0.30 / 0.59 / 0.11 | The Rec. 601 luma coefficients, as used across pixel-art value tutorials above |

## Reference case

| Claim | Source |
|---|---|
| Three render bands (people, formations, territories); a one-scene cross-band art test with "reads" defined per band and checked against two terrain types; a fail at any band is a milestone finding | A three-band strategy game's design spec, §4.4 and §8, read 2026-08-29 (private repo; the band definitions are restated in SKILL.md) |
| Case 1 colors and fix | The same game's milestone 1 gate record, 2026-08-29 |

No volatile file: the doctrine is durable. Directory and marketplace specifics live here with their check dates and are re-checked on any refresh.
