# Sources

Last verified: 2026-10-01 (the two parity registers below; upkeep reads this stamp, 90-day cadence).

Format, craft and reference-case rows checked live 2026-08-29 during the build's research pass; the parity register checked live 2026-09-26. Fetched pages were read as data; none carried a directive addressed to the run.

## Skill format

| Claim | Source |
|---|---|
| Name ≤64 chars, description ≤1024 third person, body ≤500 lines, references one level deep, TOC on long reference files | platform.claude.com — Agent Skills, "Skill authoring best practices" (fetched 2026-08-29) |
| Official skill set carries no game-art-at-scale skill (canvas-design, algorithmic-art, brand-guidelines are the nearest) | github.com/anthropics/skills (checked 2026-08-29) |

## Parity register (dated 2026-09-26; 90-day cadence)

The incumbents that do part of this skill's job, what each covers, and where this skill stands. Re-check before claiming a capability no incumbent has. This register supersedes the 2026-08-29 niche scan, which listed single-scale sprite tools; the 2026-09-26 audit picked the three strongest on the core job.

| Incumbent | Licence / origin | Covers | Verdict |
|---|---|---|---|
| **A** PixelLab MCP — https://github.com/pixellab-code/pixellab-mcp and https://www.pixellab.ai/mcp | Proprietary service, API key (fetched 2026-09-26) | Character creation in 4 or 8 directions, animation, chained terrain tilesets, map objects with style matching, generation from labelled reference images. No documented palette, pixel-grid or readability control | A generator, never rebuilt. Its direction count and reference images shaped the animation rule and the style lock |
| **B** `pixel-art-sprites` skill — https://claudemarketplaces.com/skills/absolutelyskilled/absolutelyskilled/pixel-art-sprites | Marketplace listing (fetched 2026-09-26; repo tree unreadable) | 16 and 32 px canvases, indexed palettes, hue-shifted ramps, low-resolution silhouettes, edge-first tiles, sprite sheets, animation, integer scaling and no bilinear filtering | Single scale. Its tile, animation and integer-scaling coverage became the terrain-tile rule, the animation rule and the render precondition |
| **C** Pixel Art XL LoRA + ComfyUI-PixelArt-Detector — https://huggingface.co/nerijs/pixel-art-xl and https://github.com/dimtoneff/ComfyUI-PixelArt-Detector | creativeml-openrail-m (LoRA); MIT, v1.7.3 (nodes) (fetched 2026-09-26) | Local diffusion in pixel-art style with a nearest-neighbour downscale by the LoRA's factor; palette reduction, palette conversion to a loaded palette, dithering | The user-class local generator. It shaped the diffusion brief and its post-process contract; model numbers stay with the runner |

**Margin held on 2026-09-26** (no incumbent has it): cross-band readability rules with per-band "reads" checklists; numeric terrain-versus-unit contrast with a pass line, a fix ladder and a case log; a repeatable one-scene look test with a full text path; briefs tied to the checklist lines the asset will be scored on.

**Supporting finding:** a strategy-game devlog on keeping detail at close zoom and hiding it zoomed out so units do not blend into the ground — https://temesagames.itch.io/the-omins (devlog, fetched 2026-09-26). It shaped the detail budget.

**Out of scope by choice:** producing the asset (a generator's or an artist's), engine rendering and filtering (godotsmith's for the finding, the game's for the code).

## Parity register — the `3d` mode (dated 2026-10-01; 90-day cadence)

Research unit G1 of the 2026-09-28 pack-split run, all sources read 2026-10-01. Verdict **PARITY + MARGIN, narrow**: warranted only for pixelated 3D (pixel art carried into a 3D or 2.5D band); general 3D art direction is out of scope and left to incumbents.

| Incumbent | Licence / origin | Covers | Verdict |
|---|---|---|---|
| **D** xenodot-forge 3D-pixel-art skills — https://github.com/arthur0n/xenodot-forge | MIT, one Godot framework | Low-res SubViewport, nearest filter, pixel lighting, mesh import for pixel art; camera snap flagged "advanced"; meshes only | Met on the render recipe (routed to godotsmith); beaten on billboards, the seam, measured pass lines, neutrality |
| **E** `art-direction` skill — https://github.com/SummerEngine/summer | MIT, one engine's tools | Art-bible interview, technique pick, a colour-count constraint, a lighting plan | Met on palette constraint and light plan; no billboards, bands or measured acceptance |
| **F** `asset-audit` / `asset-spec` — https://github.com/Donchitos/Claude-Code-Game-Studios | MIT | File-size, naming and format budgets; "NOT ASSESSED, never an estimate" | Its NOT ASSESSED rule adopted for the 3D scorecard |

Technique reference: davidhol.land "3D Pixel Art Rendering" (low-res render, texel-grid camera snap with a screen-space shift, outlines, toon light, billboard foliage), read 2026-10-01.

**Margin held on 2026-10-01:** M1 one look test spanning the 2D bands and a pixelated-3D band (the seam test); M2 art pass lines a capture can be measured against (block uniformity, palette membership, billboard texel = art pixel, seam match); M3 a detail budget stated in art pixels. Pass lines are PROVISIONAL until a running prototype tunes them.

**Not in scope:** image-to-3D generation. ComfyUI core had shape-only Hunyuan3D 2.0 on 2026-10-01; native textured Hunyuan3D 2.1 was an open, unmerged PR (#15020). The gate: that node merged, and one live run succeeds on the user's GPU.

**Retire condition:** a maintained, neutral incumbent ships billboard rules, a 2D-to-3D seam test and measured pass lines for pixelated 3D; or no project uses the mode within two releases.

## Re-checking

Both registers are re-checked on their own 90-day stamps (next due 2026-12-25 and 2026-12-30): re-read each incumbent's page, update the Covers and Verdict cells, and restamp the heading.

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
| CIELAB L* = 116 f(Y/Yn) − 16, f(t) = t^(1/3) above (6/29)^3, else t/(3 (6/29)^2) + 4/29; L* 0 black to 100 white; intended as perceptually uniform | en.wikipedia.org "CIELAB color space" (fetched 2026-10-01) |
| sRGB to linear: c/12.92 at or below 0.04045, else ((c + 0.055)/1.055)^2.4; Y = 0.2126 R + 0.7152 G + 0.0722 B | en.wikipedia.org "sRGB" (fetched 2026-10-01) |
| Hue-shifted ramps: shadows toward cool, highlights toward warm | Parity incumbent B's coverage ("hue-shifted ramps"), above; triage row P2-1 of the 2026-09-28 run |
| 640x360 base: 360 divides 720, 1080, 1440 and 2160, so P = screen height / 360 is a whole number at each | Arithmetic; a pixel-scale correction recorded 2026-10-01 in a research unit's style-guide work |
| Art density per band: art pixels per world unit = zoom at band centre / P | Texel-density practice (artyx-marketplace `texel-density`, read 2026-10-01 by G1), restated in art pixels |
| A diffusion pixel-art LoRA merges a two-object prompt into one object | A local model test, 2026-09-29 (hut beside a campfire rendered as one object) |

## Reference case

| Claim | Source |
|---|---|
| Three render bands (people, formations, territories); a one-scene cross-band art test with "reads" defined per band and checked against two terrain types; a fail at any band is a milestone finding | A three-band strategy game's design spec, §4.4 and §8, read 2026-08-29 (private repo; the band definitions are restated in SKILL.md) |
| Case 1 colors and fix | The same game's milestone 1 gate record, 2026-08-29 |

No volatile file: the doctrine is durable. Directory and marketplace specifics live here with their check dates and are re-checked on any refresh.
