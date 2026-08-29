# Band Rules — palette, silhouette, and "reads" per band

Loaded on every run. The five laws in SKILL.md say what holds; this file says how, with numbers. Numbers are house defaults for a 16–32 px pixel-art game with three bands; a run states any departure in the rule set it hands back.

## Contents

- Value ladder (shared by every band)
- Near band — rules and "reads" checklist
- Mid band — rules and "reads" checklist
- Far band — rules and "reads" checklist
- Owner color
- Extending to more bands
- Terms

---

## Value ladder

Value is brightness with hue removed. Every rule below is stated in value steps on a 0–100 scale (0 black, 100 white). Convert a color to value with the luminance formula 0.30 R + 0.59 G + 0.11 B on 0–255 channels, divided by 2.55.

- **Terrain occupies the middle.** Every terrain tile sits between value 25 and 60. Terrains differ from each other by hue and texture more than by value, so the units above them own the top and the bottom of the ladder.
- **Units and buildings occupy the ends.** A mobile unit's dominant value sits at 70 or above, or at 15 or below; a building's dominant value sits at 70 or above. The two ends are the two reserved bands of the ladder; nothing decorative uses them.
- **The gap.** An asset's dominant value differs from every terrain it can sit on by at least 25 steps. This is the number the contrast method in `contrast.md` checks.
- **Per-asset ladder.** Three values per material: base, shadow (base minus 15–20), highlight (base plus 10–15). Six to twelve colors per asset in total. More colors flatten the silhouette at mid.

## Near band

The camera shows individuals. One asset is itself.

**Palette.** Base, shadow, highlight per material as above; one owner-color slot (below); no gradients, no anti-aliasing against transparency; an outline of one pixel where the sprite's edge value is within 15 steps of any terrain it can stand on, otherwise none.

**Silhouette.** Class is a shape word: a person is tall-narrow with a head bump; a building is wide-low with a straight ground edge; an animal is long-low with a raised head; a tree is a lollipop or a cone on a stick. Activity is a pose word carried by the arms and the object held: working bends the body and shows a tool below waist level; fighting extends one limb outward with a weapon above waist level; idle is upright and symmetrical. Each class and each activity has one silhouette that no other class or activity shares.

**Pixel size.** A person is 12–16 px tall on a 16 px grid, 24–32 on a 32 px grid; a building is at least twice a person's width; an animal is at least a person's width and under a person's height. Under 8 px tall nothing carries activity, so a game whose near band draws people under 8 px has no near band and is told so.

**"Reads" checklist — near.**

| # | Line | Law |
|---|---|---|
| N1 | Filled black, every class is told apart from every other class | 3 |
| N2 | Filled black, working, fighting, and idle are told apart on a person | 3 |
| N3 | In grayscale, every asset clears the 25-step gap on every terrain in the scene | 2 |
| N4 | In grayscale, a person is told apart from a building standing beside it | 2 |
| N5 | Owner color is present on every unit and building and nowhere on terrain | — |
| N6 | No asset needs its interior detail to be identified | 3 |

## Mid band

The camera shows groups. One asset is a cell of a block.

**Palette.** At mid an asset is a few pixels; its interior collapses to its dominant value. Assets that form a block share one dominant value so the block reads as one shape. The owner color is the one hue that survives, carried by the block's fill or its edge.

**Silhouette.** The block's shape carries meaning, not the sprite's. Rules for the block: a formation is a filled rectangle or wedge with a straight leading edge; a settlement cluster is an irregular filled blob with a rounded edge; a convoy or column is a line one or two cells wide. Block density (cells per area) carries size or strength; block edge (straight vs rounded) carries formation vs settlement; block hue carries owner.

**Grouping is the engine's job; cleanliness is the art's.** The art passes at mid when the aggregated block has an even fill and no stray high-value or low-value pixels inside it. A sprite with a bright highlight the size of its body puts speckle into the block and fails M2.

**"Reads" checklist — mid.**

| # | Line | Law |
|---|---|---|
| M1 | A formation block and a settlement cluster are told apart by edge shape alone | 4 |
| M2 | Blocks have even fill — no speckle from single-sprite highlights or shadows | 4 |
| M3 | In grayscale, a block clears the 25-step gap on every terrain in the scene | 2 |
| M4 | Two owners' blocks are told apart by hue when adjacent | — |
| M5 | Block density visibly differs between a small group and a large one | 4 |
| M6 | No new art was drawn for this band | 1 |

## Far band

The camera shows territories. One asset is an icon or a tint.

**Palette.** The terrain is the ground and is allowed to be busy; icons are two-value (icon fill and icon edge) with the fill at value 85 or above, or 15 or below, and the edge the opposite end. A territory tint is the owner color at 30–40 percent over the terrain, edged by a one-pixel border of the same hue at full strength.

**Silhouette.** Icons use a closed geometric vocabulary: a square for a settlement, a triangle for a fortified place, a circle for a resource, a diamond for an army, a bar for a fleet or a convoy. Size tier is a count of ticks under the icon (one to four). Role is a glyph inside the icon, at most one. The vocabulary is fixed for the whole game and listed in the rule set.

**Noise rule.** Nothing at far is drawn that is neither a terrain, a border, a tint, nor an icon. A sprite that survives into the far band is noise and fails F3.

**"Reads" checklist — far.**

| # | Line | Law |
|---|---|---|
| F1 | Every icon class is told apart from every other by shape alone, in grayscale | 5 |
| F2 | Every icon clears the 25-step gap on every terrain, both over dark and over light terrain | 2 |
| F3 | Nothing is drawn at far except terrain, border, tint, and icon | 5 |
| F4 | Two owners' territories are told apart by tint and border hue when adjacent | — |
| F5 | Icon size stays readable at the game's smallest far zoom — at least 7 px on the icon's short side | 5 |
| F6 | The same icon vocabulary is used at every far-band zoom | 1 |

## Owner color

One hue per owner, chosen so that in grayscale every owner hue has the same value (within 5 steps) — owner is carried by hue only, so it never disturbs the value ladder that carries class. Six owners is the practical ceiling before hues crowd; past six, add a pattern (stripe, dot) to the block fill at mid and the icon edge at far. Owner color is never the dominant value of a sprite at near; it is an accent of at most a fifth of the sprite's pixels.

## Extending to more bands

A fourth or fifth band (a solar view, a star map) re-runs the same three roles: the new band's "asset" is the whole world or system below it, which becomes an icon on the next map. Write the band's row in the band model, copy the far-band checklist, rename its nouns, and keep the icon vocabulary distinct from the lower band's. A band whose checklist would read identically to its neighbor's is merged.

## Terms

- **Value** — brightness with hue removed; the grayscale of a color.
- **Silhouette** — the shape of an asset filled solid black.
- **Block** — the shape a group of assets forms at mid when the engine aggregates them.
- **Icon** — the fixed geometric mark that stands for a class at far.
- **Tint** — a translucent owner color laid over terrain to mark territory.
