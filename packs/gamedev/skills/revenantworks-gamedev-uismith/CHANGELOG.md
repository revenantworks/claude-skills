# Changelog — revenantworks-gamedev-uismith

## [1.0.0] — 2026-10-13

2026-10-17 (eval rerun, U41): an element past the edge gets a cause-proof change (a sideways-scroll wrapper or a reflow) before any guessed cause; case `behaviour-probe-overflow`'s judge, which failed compliant replies 3/3, is split into a shorter judge plus two regex graders (probe pixels, `td.name`).

2026-10-16 (owner eval run, U38): a measured-break row carries the probe's own pixel figure; the reply to `behaviour-probe-overflow` cited a derived width, not the 92 and 37 px the probe reported.

First public release. Design direction for screens and the measured proof that they fit. It never
defines a palette and never builds the screen.

### What it does

- A design brief for a screen: purpose, layout, hierarchy, one spacing scale and one type scale,
  a states table (default, empty, loading, error, long content, disabled), interaction feedback,
  motion with a reduced-motion fallback, and word slots handed to commscribe.
- Accessibility bars taken from WCAG 2.2 (contrast, reflow at 320 CSS px, focus, target size), with
  contrast computed, never eyeballed.
- A taste checklist: questions the brief answers so a generic-looking default is chosen or dropped,
  never left by accident.
- A rendered probe at 320, 375, 768, 1024 and 1440 px in every theme the page offers: page width
  against viewport, elements past the edge, clipped text, a screenshot per row.
- A fresh-build rule: a generated page is rebuilt and probed; a stale committed copy is reported.
- Surface notes for plugin panes (host theme classes and variables) and game menus and HUD (a
  resolution set, anchors and containers, the gamepad focus path).

### Scripts

- `scripts/probe.py` — the probe: a local file or a URL, a width list and a theme list, headless
  Chromium through optional Playwright for Python; exit 0 pass, 1 finding or NOT-RUN row, 2
  Playwright or its browser missing, 3 usage error. `scripts/test_probe.py` tests it without a
  browser.

### Entry points

- Direct (default) — the brief, or a review of a design.
- `probe` — the rendered fit check (optional Playwright).
- `audit` — probe plus the checklist on an existing page, pane or game screen, findings ranked.

Released under the Apache-2.0 licence.
