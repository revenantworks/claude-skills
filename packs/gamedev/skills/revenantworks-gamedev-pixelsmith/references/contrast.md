# Contrast — terrain versus unit, the method and the case log

Loaded on a vanish-against-terrain finding and on any palette decision. The method computes the one number the laws depend on: the value gap between an asset and the ground it sits on.

## Contents

- The method
- The contrast table
- The fix ladder
- Case log

---

## The method

1. Take each color as R, G, B on 0–255. Engine float colors (0.0–1.0) are multiplied by 255 first.
2. Value = (0.30 R + 0.59 G + 0.11 B) / 2.55, on 0–100.
3. Gap = |value(asset) − value(terrain)|.
4. **Pass at 25 or more.** 15–24 is a marginal that passes only with a one-pixel outline in the opposite value. Under 15 fails at every band.

Use the asset's **dominant** color — the one covering most of its pixels — not its highlight. A highlight is a few pixels and vanishes at mid.

Hue is checked second, only among assets that already clear the value gap: two owners' colors must differ in hue by at least 60 degrees on the color wheel while holding the same value within 5 steps.

## The contrast table

Every asset class against every terrain type. Written once in the rule set and re-run when any color changes.

```
| Asset (dominant) | value | Terrain A (value) gap | Terrain B (value) gap | … | Result |
|---|---|---|---|---|---|
| hut | 33 | hills 50 → 17 | forest 37 → 4 | | FAIL (forest) |
```

A row fails when any cell is under 25 without an outline, or under 15 at all.

## The fix ladder

Same order as the look test's findings — cheapest first.

1. **Move the asset's value** to the reserved end of the ladder (70+ for buildings and most units, 15− for a dark-unit class). Terrain stays where it is; terrain is the ground and moving it moves everything.
2. **Outline** one pixel in the opposite value, when the gap is 15–24 on one terrain only.
3. **Halo** — a one-pixel ring of a terrain-neutral value (around 62) — when the asset must sit on both a dark and a light terrain and no single value clears both.
4. **Split the class** — two variants with different dominant values, chosen by the terrain underneath — only when the halo fails, and stated in the rule set as a deliberate exception to law 1.

Never fix contrast by adding saturation. A saturated color at the same value vanishes exactly as before in grayscale, and at mid.

## Case log

One row per recorded failure, oldest first. Each row is a real result, not an example; a run cites the row number when the same failure recurs.

| # | Date | Game | Band | Asset (color) | Terrain (color) | Gap | What happened | Fix applied | Result |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 2026-08-29 | A three-band strategy prototype (Godot 4), milestone 1 gate | near and mid | Hut, dark brown `Color(0.45, 0.30, 0.15)` → value 33 | Hills `Color(0.55, 0.50, 0.40)` → value 50; Forest `Color(0.25, 0.45, 0.25)` → value 37 | 17 on hills; 4 on forest | The huts vanished against forest and were marginal on hills; the milestone gate recorded the cross-band art test as not run because the placeholder art could not be read | Value shift (fix class 1) — light sand `Color(0.92, 0.80, 0.52)` → value 80 | Gap 30 on hills, 44 on forest; passes N3 and M3 on both terrains |

**Reading Case 1.** The brown was chosen by hue — a hut is brown — and hue is the second channel. In grayscale the hut and the forest were the same gray. The fix moved the hut to the building end of the value ladder (70+) and kept it there; the hue that followed (sand) was a consequence, not the decision. This is the law-2 failure in its plainest form, and it is the first case a new rule set is checked against.

A run adds a row here only when the owner confirms the fix landed. Rows are never edited, only added.
