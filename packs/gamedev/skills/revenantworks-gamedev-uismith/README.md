# revenantworks-gamedev-uismith

Design direction for screens, a scored critique of built pages, and the measured proof that they fit. It writes the brief a builder
works from (layout, hierarchy, spacing and type scales, every state, interaction feedback and the
accessibility bars) for game menus and HUD, web dashboards, single-page artifacts, store-page
layouts and plugin panes, and then probes the rendered page at phone-to-desktop widths in every
theme. What separates it from the UI skills around it: **fit is measured** (page width against
viewport, elements past the edge and clipped text, per width and theme, with screenshots), **every
state is designed before the build**, and **tokens come in, never out**: colours, type families and
voice come from a brand definition or the project, never from uismith. The fifth member of the
`gamedev` pack.

**Workflow:** Surface → Brief → Build (not here) → Probe → Findings

## Package contents

```
revenantworks-gamedev-uismith/
├── SKILL.md            # five laws, four entries, restraint, seams
├── README.md · LICENSE · NOTICE · CHANGELOG.md · SOURCES.md · volatile.json
├── references/
│   ├── direction.md    # surface class, brief template, WCAG 2.2 bars, taste checklist, finding rows
│   ├── probe.md        # widths, themes, what is measured, evidence check, exit codes (90-day stamp)
│   ├── surfaces.md     # plugin panes, game menus and HUD, store pages
│   ├── ui-floor.md     # critique: the UI floor rules (moved from brandscribe 2026-11-24)
│   ├── ui-review.md    # critique: the six-area review and verdict
│   └── pack.md         # gamedev advisory manifest (generated from the registry)
├── scripts/
│   ├── probe.py        # run, not read: the rendered fit check (Playwright for Python, optional)
│   ├── test_probe.py   # stdlib unit tests, plus real-page tests that skip without Playwright
│   ├── ui_check.py     # critique: the 31-rule static floor check (stdlib)
│   └── test_ui_check.py # its rule tests against evals/fixtures/ui/
└── evals/              # hand-run suites + native `claude plugin eval` cases
```

## Install

Follows the [Agent Skills](https://agentskills.io/) open standard. Install the `gamedev` pack from
the marketplace in Claude Code, drop the folder into a skills directory, or upload it in claude.ai
settings. Profile `standard`.

**Optional dependency.** `scripts/probe.py` needs Python 3 and the Playwright for Python package
with its browser, the gamedev pack's one declared third-party package. You install them yourself
(`pip install playwright`, then `playwright install`); the skill never installs anything. The probe
runs headless, so no browser window opens. Without Playwright the probe exits 2 with those lines,
and direct and audit still work from the page source, your screenshots or a description.

## Entry points

| Entry | Say | Delivers |
|---|---|---|
| Direct | "design the pause menu", "lay out the settings pane", "review this dashboard mockup" | A design brief, or ranked findings on a design |
| Probe | `uismith probe`, "does this fit on a phone", "check it at every width in light and dark" | A table per theme with screenshot paths: fit, page errors and empty sections, as loaded and with every fold open; exit 0, 1 or 2 |
| Audit | `uismith audit`, "audit the side pane", "why does this page scroll sideways on my phone" | Probe plus the checklist, findings ranked from measured breaks to taste |
| Critique | `uismith critique`, "critique this dashboard before we ship it", "check dist/ for UI problems" | The 31-rule floor check, six areas scored, a P0-P3 catalog and a ship, fix or recapture verdict |

## Commands and switches

| Invocation | Effect |
|---|---|
| `uismith` | Bare invocation: the four entries in one line and a question |
| `python scripts/ui_check.py <built folder>` | The critique's static floor check: exit 0 clean, 1 findings, 2 error (`--json`, `--list-rules`) |
| `python scripts/probe.py <file-or-url>` | The probe at the default widths 320, 375, 768, 1024 and 1440 in every theme the page offers |
| "apply all" / "just write it" | Skips the one gate |

## Evals

- `evals/trigger-evals.md`: 27 trigger queries (17 should, 10 should-not, 3 boundary pairs with
  brandscribe, godotsmith and pixelsmith).
- `evals/test-cases.md`: 13 assertion cases covering direct, probe, audit and critique, each with a `Without:`
  line.
- `evals/<case>/`: 15 native `claude plugin eval` cases. Four behaviour cases grade the behaviour
  itself (every state drawn, a probe report read, NOT-RUN without Playwright, a stale copy caught),
  two critique behaviour cases (checker rows, taste stays P3), six should-fire cases, and three near-misses that must stay quiet.
- `scripts/test_probe.py`: 32 stdlib tests (argument parsing, theme detection, the overflow
  judgement from fixture numbers, the evidence check, exit codes, the missing-dependency path, and
  the run loop through a fake browser). Run `python -m unittest discover -s scripts -p "test_*.py"`.
- `scripts/test_ui_check.py`: the critique checker's rule tests against `evals/fixtures/ui/`.

All suites are authored, not run against a model yet. The probe's real browser path needs
Playwright and has not been run by these tests.

## Boundaries

`revenantworks-scribe-brandscribe` owns brand definitions, palettes, type and voice, and the brand
pass of a built page (its `gate` entry). `revenantworks-gamedev-pixelsmith` owns pixel art,
sprites and icons. `revenantworks-gamedev-godotsmith` owns Godot conventions and run proof, a UI
scene's review included. `revenantworks-scribe-commscribe` owns every word on the screen.
`revenantworks-gamedev-slicesmith` builds a game screen test-first from the brief. Each is named and
never required.

## Staying current

`references/probe.md` (90 days) carries a Last-verified stamp for its Playwright facts; `SOURCES.md`
holds the dated parity register (90 days); `references/direction.md` is event-driven (re-checked
when WCAG publishes a new version). `skillwright upkeep` reads them from `volatile.json`.

History in [CHANGELOG.md](CHANGELOG.md).
