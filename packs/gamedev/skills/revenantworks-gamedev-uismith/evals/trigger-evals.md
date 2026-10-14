# Trigger evals — revenantworks-gamedev-uismith — 21 queries (10 should / 11 shouldn't)

Counts: 21 queries (10 should, 11 should-not, 4 pairs)

Provenance: derived from SKILL.md v1.0.0 (2026-10-13). Status: **authored, not run** — a cold judge
reading only name + description has not scored this table yet. Read each query against the name and
description alone and compare with the Expected column. 10 should fire, 11 should not.

Pairs (same surface, different owner): rows 3 and 13 (a built page: fit at widths versus a scored
ship verdict, brandscribe), rows 5 and 15 (a game menu: what it should do versus a scene review,
godotsmith), rows 6 and 16 (a HUD: its layout versus the icons inside it, pixelsmith), rows 7 and 21 (a
review: a mockup before the build versus a critique of the built page, brandscribe; F3).

| # | Query | Expected | Nearest sibling / note |
|---|---|---|---|
| 1 | Design the settings screen for my desktop app: what goes where, and every state it can be in. | fire | Direct |
| 2 | uismith probe — check index.html at every width in light and dark. | fire | quoted keyword, Probe |
| 3 | My dashboard scrolls sideways on my phone and a column of text gets cut off in dark mode. | fire | Audit (probe first) |
| 4 | Lay out the side panel for my VS Code extension so it works in the high-contrast theme too. | fire | Direct, surfaces.md (plugin pane) |
| 5 | Design the pause menu for my Godot game so it works with a gamepad. | fire | Direct, surfaces.md (focus path) |
| 6 | Lay out the HUD for my top-down shooter: health, ammo, minimap, objective. | fire | Direct, game UI |
| 7 | Review this mockup of our analytics page before we build it — hierarchy, spacing, empty and error states. | fire | Direct, review of a design |
| 8 | Does this single-page report fit from 320 to 1440 pixels wide? | fire | Probe |
| 9 | Our generated status page looks generic. Give me a design direction before I rebuild it. | fire | Direct, taste checklist |
| 10 | uismith audit the inventory screen in my game; here are screenshots at 1280x720 and 1920x1080. | fire | Audit, game UI from screenshots |
| 11 | Pick a colour palette and a font pairing for our brand. | not fire | brandscribe (tokens are an input to uismith) |
| 12 | Rewrite the error messages and button labels on our signup form. | not fire | commscribe (words on the screen) |
| 13 | Critique this built landing page against the UI floor and tell me if it ships. | not fire | brandscribe `ui` (scored verdict) |
| 14 | Turn our style guide into design tokens and a design system. | not fire | brandscribe |
| 15 | Review my HUD scene's signals and node ownership against our Godot conventions. | not fire | godotsmith `review` |
| 16 | The minimap icons vanish against the terrain when the camera zooms out. | not fire | pixelsmith |
| 17 | Draw a bar chart of weekly sales for this dashboard. | not fire | a chart skill |
| 18 | Implement the options menu test-first, one slice at a time. | not fire | slicesmith (the build loop) |
| 19 | Is my GUT run really green? The test count dropped after the merge. | not fire | godotsmith |
| 20 | Recommend a good 27-inch monitor for design work. | not fire | off-topic |
| 21 | Critique the settings page I just built: hierarchy, spacing, empty and error states, does it look generic? | not fire | brandscribe `ui` (a critique of a built page; native `nearmiss-brandscribe-critique`) |
