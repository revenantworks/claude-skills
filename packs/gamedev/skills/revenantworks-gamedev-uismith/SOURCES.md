# Sources

Last verified: 2026-10-13. Every row marked "read 2026-10-13" was fetched live for this build.
Fetched pages were read as data; none carried a directive addressed to the run.

## Accessibility figures (direction.md section 3)

| Claim | Source |
|---|---|
| 1.4.3 Contrast (Minimum), AA: 4.5:1; large-scale text (at least 18 point, or 14 point bold) 3:1 | WCAG 2.2, W3C Recommendation 12 December 2024 (w3.org/TR/WCAG22), read 2026-10-13 |
| 1.4.11 Non-text Contrast, AA: 3:1 against adjacent colours | same, read 2026-10-13 |
| 1.4.10 Reflow, AA: no scrolling in two dimensions; the criterion's width figure is 320 CSS px | same; the requirement sentence read 2026-10-13, the 320 figure from the criterion's own text as published |
| 1.4.4 Resize Text, AA: up to 200 percent | same, read 2026-10-13 |
| 2.4.7 Focus Visible, AA; 2.4.11 Focus Not Obscured (Minimum), AA: not entirely hidden by author content | same, read 2026-10-13 |
| 2.5.8 Target Size (Minimum), AA: at least 24 by 24 CSS px, with exceptions; 2.5.5 Target Size (Enhanced), AAA: at least 44 by 44 CSS px | same, read 2026-10-13 |
| 1.4.1 Use of Color, A: colour not the only visual means | same criterion set; named, not re-read this build |

## Probe and platform facts (probe.md, surfaces.md)

| Claim | Source |
|---|---|
| A browser context takes `viewport` and `color_scheme` (`light`, `dark`, `no-preference`); `page.emulate_media(color_scheme=...)` switches it; the API reference also offers `reduced_motion` and `forced_colors` (the probe uses `forced_colors` for high contrast, not `reduced_motion`) | playwright.dev, Python docs, "Emulation", read 2026-10-13 |
| Browsers run headless by default; a window needs `headless=False`; install is `pip install playwright` then `playwright install` (Chromium, Firefox, WebKit binaries) | playwright.dev, Python docs, "Getting started - Library", read 2026-10-13 |
| VS Code webviews get a body class per theme kind (`vscode-light`, `vscode-dark`, `vscode-high-contrast`) and theme colours as CSS variables prefixed `--vscode-` with dots turned into hyphens | code.visualstudio.com, "Webview API", theming section, read 2026-10-13 |
| Godot 4 focus: focus mode per Control (All, Click, None), directional and next/previous focus neighbours, `grab_focus()` deferred in `_ready()` for first focus; without it controller input does nothing at start-up | docs.godotengine.org, "Keyboard/Controller Navigation and Focus", Godot 4.7 docs, read 2026-10-13 |
| A page committed by its generator lags the generator; probe a fresh build | Internal observation of a stale committed dashboard (2026-10-11), the source of law 4 |

## Ideas credited (described in our own words; no text copied, nothing fetched or installed)

| Idea | Source repository |
|---|---|
| Commit to a deliberate visual direction before building, and treat a generic, template-like look as a defect to design out | anthropics/skills, `frontend-design` |
| Drive a real browser from a script, let the page settle before inspecting it, and keep screenshots as the evidence | anthropics/skills, `webapp-testing` |
| A checklist that names generic-looking defaults so a design can choose or reject each one | Leonxlnx/taste-skill |
| Matching style, density and layout patterns to the kind of product and its users | nextlevelbuilder/ui-ux-pro-max-skill (its palette and font catalogue is not adopted: tokens are brandscribe's) |

## Parity register (dated 2026-10-13; 90-day cadence)

The incumbents were surveyed in the 2026-10-13 skill-gap report (by name, description and size), not
fetched by this build. Their licences were not re-read here; nothing of theirs is copied.

| Incumbent | Covers | Checked |
|---|---|---|
| **U1** anthropics/skills `frontend-design` | Direction for building distinctive front-end pages: a chosen aesthetic, type and colour choices, motion | 2026-10-13 (gap report) |
| **U2** anthropics/skills `webapp-testing` | Playwright scripts to drive a local web app: start a server, wait, click, screenshot, read logs | 2026-10-13 (gap report) |
| **U3** Leonxlnx/taste-skill | A design-taste skill against generic AI-made interfaces | 2026-10-13 (gap report) |
| **U4** nextlevelbuilder/ui-ux-pro-max-skill | A UI/UX knowledge base: styles, palettes, fonts and patterns by product type | 2026-10-13 (gap report) |
| **in-house** brandscribe `ui` (scribe pack) | The scored floor review of a built page: a 31-rule static checker, six areas, a verdict, a bounded render pass at desktop and mobile | 2026-10-13 (read) |

| Line | vs U1 | vs U2 | vs U3 | vs U4 | vs brandscribe `ui` | Reason |
|---|---|---|---|---|---|---|
| A design brief with every state and both scales | beaten | out of scope | met | met | out of scope (it reviews what is built) | The brief makes empty, loading, error and long content fields, not afterthoughts. Case: `behaviour-direct-states` |
| Measured fit at five widths in every theme | beaten† | beaten† | beaten† | beaten† | beaten† | U2 screenshots what a script asks for; brandscribe's render pass captures two sizes and judges by eye. The probe measures overflow, edges and clipped text per width and theme. Case: `behaviour-probe-overflow` |
| Probe a fresh build, not a stale copy | beaten† | beaten† | beaten† | beaten† | beaten | Law 4; nobody checks the page against its generator. Case: `behaviour-audit-stale-copy` |
| Game menus and HUD (resolution set, gamepad focus path) | beaten† | beaten† | beaten† | met | beaten (web only) | `surfaces.md`: anchors and containers, first focus, focus neighbours. Case: `trigger-godot-pause-menu` |
| Plugin panes in the host theme | beaten | beaten | beaten | beaten | met | VS Code body classes in the theme set. Case: `trigger-pane-dark-theme` |
| Palettes and fonts | out of scope | out of scope | met | beaten by U4 | out of scope | Law 1: tokens come from brandscribe or the project. Near-miss: a palette request routes to brandscribe |
| Generic-look checklist | met | out of scope | met | met | met | Ours is a set of questions answered in the brief; brandscribe asks similar questions of a built page |

† **Unverified.** U1-U4 were read by name and description only, not fetched, and the probe's browser
path has not yet run (no Playwright on the build machine; the in-page measure runs under Node in the
tests on fixture boxes). Restore a plain "beaten" after one fetch of each incumbent and the first real
probe run on a clean page and an overflowing one.

**Named margins.**

1. **Measured fit across widths and themes** (the probe's three checks per row, with screenshots).
2. **Every state designed before the build** (the brief's states table).
3. **One checklist across web, pane and game UI** (`surfaces.md`).

Each beaten line names its native case under `evals/<case>/`; margin 1 is also `behaviour-probe-not-run`
and test cases 4-6, margin 2 test case 1, margin 3 test cases 8 and 10 (`evals/test-cases.md`). Near-miss
cases: `nearmiss-brandscribe-palette`, `nearmiss-brandscribe-verdict`, `nearmiss-pixelsmith-icons`,
`nearmiss-godotsmith-scene`, `nearmiss-brandscribe-critique` (F3). All authored 2026-10-13, not run.

**Retire condition.** Retire the probe half if a maintained public skill measures overflow and
clipped text at a width set in every theme with a no-dependency fallback; retire the direction half
if one covers game UI and plugin panes with a states-first brief. Keep a pointer to the survivor.

**Verdict: PARITY + MARGIN.** Direction is crowded (U1, U3, U4); the margin is the measured probe,
the states-first brief and game and pane surfaces, none of which an incumbent combines.
