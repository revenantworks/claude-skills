# Band Rules — palette, silhouette, and "reads" per band

Every run. SKILL.md's laws say what holds; this file gives the numbers. They are house defaults for a 16–32 px game with three bands; a rule set states any departure. Checklist lines read `ID (law) line`.

## Render precondition

Each band renders at a whole-number zoom with nearest-neighbour filtering. For 16:9 targets the art grid is 640x360 and P (screen pixels per art pixel) = screen height / 360: 2 at 720p, 3 at 1080p, 4 at 1440p, 6 at 2160p. A non-integer P at any supported resolution, a non-integer band zoom, or bilinear filtering smears pixels before the art is judged: a finding handed to godotsmith by name, not an art fix.

## Value ladder

Value = brightness with hue removed, 0–100: (0.30 R + 0.59 G + 0.11 B) / 2.55 on 0–255 channels.

- **Terrain owns the middle:** every terrain pixel sits in 25–60. Terrains differ by hue and texture more than value.
- **Assets own the ends:** a mobile unit's dominant value is ≥70 or ≤15; a building's is ≥70. Nothing decorative uses the ends.
- **The gap:** an asset's dominant value differs from every terrain it can sit on by ≥25 (checked in `contrast.md`).
- **Per material:** base, shadow (base −15 to −20), highlight (base +10 to +15). Shadows shift cool and highlights warm in hue; the value steps stay as stated. 6–12 colours per asset; more flatten the silhouette at mid.

**Terrain tiles.** Texture stays within ±8 of the tile base (so inside 25–60, and no speckle in a mid block). A transition tile keeps each side's own values, never an invented middle. Decoration on its own layer follows the detail budget.

**Animation.** Dominant value constant across frames within ±3, so a block does not flicker at mid. The brief states directions per class (4 or 8) and frames per activity; each frame is scored as its own silhouette (N1, N2).

## Near band — one asset is itself

**Palette.** Per-material ladder; one owner-colour slot; no gradients; no anti-aliasing against transparency; a 1 px outline only where the edge value is within 15 of a terrain it can stand on.

**Silhouette** (the asset filled black). Class is a shape word: person tall-narrow with a head bump; building wide-low with a straight ground edge; animal long-low with a raised head; tree a lollipop or a cone on a stick. Activity is a pose word carried by arms and held object: working bends the body, tool below the waist; fighting extends one limb, weapon above the waist; idle upright and symmetrical. No two classes or activities share a silhouette.

**Size.** Person 12–16 px tall on a 16 px grid, 24–32 on a 32 px grid; building ≥2x a person's width; animal ≥ a person's width and under a person's height. People under 8 px carry no activity: that game has no near band, and is told so.

- N1 (3) Filled black, every class is told apart from every other
- N2 (3) Filled black, working, fighting and idle are told apart on a person
- N3 (2) In grayscale, every asset clears the 25-step gap on every terrain in the scene
- N4 (2) In grayscale, a person is told apart from a building beside it
- N5 (—) Owner colour on every unit and building, nowhere on terrain
- N6 (3) No asset needs interior detail to be identified

## Mid band — one asset is a cell of a block

**Palette.** Interior collapses to the dominant value; assets forming a block share one dominant value. Owner colour is the one hue that survives, in the block's fill or edge.

**Block shape** carries meaning, not the sprite: a formation is a filled rectangle or wedge with a straight leading edge; a settlement cluster an irregular blob with a rounded edge; a convoy a line 1–2 cells wide. Density carries size or strength; edge carries formation vs settlement; hue carries owner. Grouping is the engine's job; cleanliness is the art's: even fill, no stray high- or low-value pixels. A highlight the size of the body speckles the block (M2).

- M1 (4) Formation and settlement cluster told apart by edge shape alone
- M2 (4) Even fill: no speckle from sprite highlights, shadows or terrain texture
- M3 (2) In grayscale, a block clears the 25-step gap on every terrain
- M4 (—) Adjacent owners' blocks told apart by hue
- M5 (4) Block density visibly differs between a small and a large group
- M6 (1) No new art drawn for this band

## Far band — one asset is an icon or a tint

**Palette.** Terrain may be busy. Icons are two-value: fill ≥85 or ≤15, edge at the opposite end. A territory tint is the user colour at 30–40% over terrain with a 1 px full-strength border of the same hue.

**Icons** use a closed geometric vocabulary, fixed for the whole game and listed in the rule set: square settlement, triangle fortified place, circle resource, diamond army, bar fleet or convoy. Size tier = 1–4 ticks under the icon; role = at most one glyph inside. Nothing else is drawn at far: a surviving sprite is noise (F3).

- F1 (5) Every icon class told apart by shape alone, in grayscale
- F2 (2) Every icon clears the 25-step gap over dark and over light terrain
- F3 (5) Nothing drawn except terrain, border, tint and icon
- F4 (—) Adjacent owners' territories told apart by tint and border hue
- F5 (5) Icon short side ≥7 px at the smallest far zoom
- F6 (1) One icon vocabulary at every far zoom

## Detail budget and density

Every Direct rule set carries both tables; the audit checks each asset against them.

| Layer | Near | Mid | Far |
|---|---|---|---|
| Terrain texture | shown | within ±8 of base | flattened to base |
| Ground decoration | shown | hidden | hidden |
| Cast shadows | shown | hidden | hidden |
| Trees, large props | shown | as a cluster | tint or hidden |
| Sprites | shown | cells of blocks | hidden (F3) |

A layer kept against this default is named with the line it risks (M2, F3).

**Density table** (required): per band, art pixels per world unit = zoom at band centre / P. Each asset is drawn at the density of the band it is drawn for; an asset drawn at another density is a finding.

## Owner colour

One hue per owner, all at the same value within 5, so owner rides on hue and never disturbs the ladder. Up to six owners; past six add a pattern (stripe, dot) to the mid block fill and the far icon edge. At near, owner colour is an accent of at most a fifth of the sprite's pixels, never its dominant value.

## More bands

A fourth or fifth band (a system view, a star map) re-runs the roles: the world below becomes an icon on the next map. Add its row to the band model, copy the far checklist with its nouns renamed, and keep its icon vocabulary distinct from the band below. A band whose checklist reads the same as its neighbour's is merged.
