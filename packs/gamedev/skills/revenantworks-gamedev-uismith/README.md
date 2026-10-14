# revenantworks-gamedev-uismith

Design direction for screens, and the measured proof that they fit. It writes the brief a builder
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
├── SKILL.md            # five laws, three entries, restraint, seams
├── README.md · LICENSE · NOTICE · CHANGELOG.md · SOURCES.md · volatile.json
├── references/
│   ├── direction.md    # surface class, brief template, WCAG 2.2 bars, taste checklist, finding rows
│   ├── probe.md        # widths, themes, what is measured, evidence check, exit codes (90-day stamp)
│   ├── surfaces.md     # plugin panes, game menus and HUD, store pages
│   └── pack.md         # gamedev advisory manifest (generated from the registry)
├── scripts/
│   ├── probe.py        # run, not read: the rendered fit check (Playwright for Python, optional)
│   └── test_probe.py   # stdlib unit tests for everything that runs without a browser
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
| Probe | `uismith probe`, "does this fit on a phone", "check it at every width in light and dark" | A fit table per theme with screenshot paths; exit 0, 1 or 2 |
| Audit | `uismith audit`, "audit the side pane", "why does this page scroll sideways on my phone" | Probe plus the checklist, findings ranked from measured breaks to taste |

## Commands and switches

| Invocation | Effect |
|---|---|
| `uismith` | Bare invocation: the three entries in one line and a question |
| `python scripts/probe.py <file-or-url>` | The probe at the default widths 320, 375, 768, 1024 and 1440 in every theme the page offers |
| "apply all" / "just write it" | Skips the one gate |

## Evals

- `evals/trigger-evals.md`: 20 trigger queries (10 should, 10 should-not, 3 boundary pairs with
  brandscribe, godotsmith and pixelsmith).
- `evals/test-cases.md`: 10 assertion cases covering direct, probe and audit, each with a `Without:`
  line.
- `evals/<case>/`: 10 native `claude plugin eval` cases. Four behaviour cases grade the behaviour
  itself (every state drawn, a probe report read, NOT-RUN without Playwright, a stale copy caught),
  two should-fire cases, and four near-misses that must stay quiet.
- `scripts/test_probe.py`: 32 stdlib tests (argument parsing, theme detection, the overflow
  judgement from fixture numbers, the evidence check, exit codes, the missing-dependency path, and
  the run loop through a fake browser). Run `python -m unittest discover -s scripts -p "test_*.py"`.

All suites are authored, not run against a model yet. The probe's real browser path needs
Playwright and has not been run by these tests.

## Boundaries

`revenantworks-scribe-brandscribe` owns brand definitions, palettes, type and voice, and the scored
floor review of a built page (its `ui` entry). `revenantworks-gamedev-pixelsmith` owns pixel art,
sprites and icons. `revenantworks-gamedev-godotsmith` owns Godot conventions and run proof, a UI
scene's review included. `revenantworks-scribe-commscribe` owns every word on the screen.
`revenantworks-gamedev-slicesmith` builds a game screen test-first from the brief. Each is named and
never required.

## Staying current

`references/probe.md` (90 days) carries a Last-verified stamp for its Playwright facts; `SOURCES.md`
holds the dated parity register (90 days); `references/direction.md` is event-driven (re-checked
when WCAG publishes a new version). `skillwright upkeep` reads them from `volatile.json`.

History in [CHANGELOG.md](CHANGELOG.md).
