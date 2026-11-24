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
| `page.on("console")` and `page.on("pageerror")` report logged and thrown errors; `checkVisibility` separates rendered from hidden; Chromium lays out a closed fold's body | Run, not read: Playwright for Python with Chromium 153, `RealBrowser` in `scripts/test_probe.py`, 2026-11-03 |
| A blank section passes every fit check, and closed folds hide overflow from one, so the probe fails on page errors and empty sections and measures with folds open | Internal observations of a published page whose script crashed and of a layout pass that folded wide content (2026-11) |
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
| **in-house** uismith `critique` (brandscribe `ui` until 2026-11-24) | The scored floor review of a built page: a 31-rule static checker, six areas, a verdict, a bounded render pass at desktop and mobile | 2026-10-13 (read) |

| Line | vs U1 | vs U2 | vs U3 | vs U4 | vs critique | Reason |
|---|---|---|---|---|---|---|
| A design brief with every state and both scales | beaten | out of scope | met | met | out of scope (it reviews what is built) | The brief makes empty, loading, error and long content fields, not afterthoughts. Case: `behaviour-direct-states` |
| Measured fit at five widths in every theme | beaten† | beaten† | beaten† | beaten† | beaten† | U2 screenshots what a script asks for; brandscribe's render pass captures two sizes and judges by eye. The probe measures overflow, edges and clipped text per width and theme. Case: `behaviour-probe-overflow` |
| Probe a fresh build, not a stale copy | beaten† | beaten† | beaten† | beaten† | beaten | Law 4; nobody checks the page against its generator. Case: `behaviour-audit-stale-copy` |
| Game menus and HUD (resolution set, gamepad focus path) | beaten† | beaten† | beaten† | met | beaten (web only) | `surfaces.md`: anchors and containers, first focus, focus neighbours. Case: `trigger-godot-pause-menu` |
| Plugin panes in the host theme | beaten | beaten | beaten | beaten | met | VS Code body classes in the theme set. Case: `trigger-pane-dark-theme` |
| Palettes and fonts | out of scope | out of scope | met | beaten by U4 | out of scope | Law 1: tokens come from brandscribe or the project. Near-miss: a palette request routes to brandscribe |
| Generic-look checklist | met | out of scope | met | met | met | Ours is a set of questions answered in the brief; brandscribe asks similar questions of a built page |

† **Unverified.** U1-U4 were read by name and description only, not fetched. The probe's browser path
first ran on 2026-11-03, on real clean and overflowing pages. Restore a plain "beaten" after one fetch
of each incumbent.

**Named margins.**

1. **Measured fit across widths and themes** (the probe's three checks per row, with screenshots).
2. **Every state designed before the build** (the brief's states table).
3. **One checklist across web, pane and game UI** (`surfaces.md`).

Each beaten line names its native case under `evals/<case>/`; margin 1 is also `behaviour-probe-not-run`
and test cases 4-6, margin 2 test case 1, margin 3 test cases 8 and 10 (`evals/test-cases.md`). Near-miss
cases: `nearmiss-brandscribe-palette`, `nearmiss-pixelsmith-icons`,
`nearmiss-godotsmith-scene`. All authored 2026-10-13, not run. 2026-11-24: `nearmiss-brandscribe-verdict` became
`trigger-critique-verdict`, `nearmiss-brandscribe-critique` moved to brandscribe as `nearmiss-uismith-critique`,
and five critique cases came in from brandscribe.

**Retire condition.** Retire the probe half if a maintained public skill measures overflow and
clipped text at a width set in every theme with a no-dependency fallback; retire the direction half
if one covers game UI and plugin panes with a states-first brief. Keep a pointer to the survivor.

**Verdict: PARITY + MARGIN.** Direction is crowded (U1, U3, U4); the margin is the measured probe,
the states-first brief and game and pane surfaces, none of which an incumbent combines.

## Critique sources (moved from brandscribe `ui`, 2026-11-24)

| Claim | Source | Checked |
|---|---|---|
| Critique floor: target size "at least 24 by 24 CSS pixels" with five exceptions (spacing, equivalent, inline, user agent control, essential) | W3C WCAG 2.2 Understanding 2.5.8 | 2026-10-01 |
| Critique floor: visible keyboard focus; text resizable to 200%; non-text contrast 3:1 | W3C WCAG 2.2, success criteria 2.4.7, 1.4.4, 1.4.11 | 2026-10-01 |
| Critique review areas grounded in general usability heuristics (visibility of status, error prevention and recovery, consistency, recognition over recall) | Nielsen Norman Group, "10 Usability Heuristics for User Interface Design" | as published |

- The Critique entry (brandscribe's `ui` mode until 2026-11-24), `references/ui-floor.md`, `references/ui-review.md` and `scripts/ui_check.py`: ideas harvested from the third-party impeccable skill (Apache-2.0, v4.3.1, read 2026-10-01). Ideas only, restated in our own words and shape; no text or code copied. Taken: check built output once at the end, not per edit; unmeasured instead of failed when the ground is unresolvable; the verify floor; theming browser-default surfaces; generic-UI patterns as questions; the brief wins over taste; scored areas with n/a and a severity tiebreak; judge before reading checker output; a bounded render pass with an evidence check; motion bands; truth in demo data. Dropped: per-edit hooks, a bundled binary, a live page-injection mode, persona and playbook commands. The checker's 31 rules are our own design (the source's detector rules are compiled and unreadable), plus two rig lessons: a missing webfont caught only on built output, and contrast false positives against an unpainted ground.
