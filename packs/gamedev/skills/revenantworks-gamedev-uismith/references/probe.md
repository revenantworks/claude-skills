# Probe: rendered fit at every width and theme

Last verified: 2026-10-13 (the Playwright for Python facts in section 7; 90-day calendar).

Load on Probe and Audit. `scripts/probe.py` runs the checks below; this file is the contract it
keeps and the reading of its report.

## Contents

1. Target and the fresh-build rule
2. Widths and themes
3. What is measured
4. Evidence check
5. Report and exit codes
6. Limits
7. Playwright facts and the no-Playwright path

## 1. Target and the fresh-build rule

The target is a local HTML file or a URL the user names, usually a dev server the user started.
The probe never starts a server and never signs in. It loads the named file or URL and whatever that
page itself requests (scripts, web fonts, images, frames, analytics, from any host, redirects
followed, just as a browser would); it adds no request and sends no data of its own. A local file
that links a web font or a CDN script reaches the network for it.

A page built by a generator (a dashboard script, a static-site build, an artifact made from a
template) is rebuilt from the generator at the current commit, into a scratch folder, and that build
is probed. A committed copy older than its generator is reported **stale** with both commits; its
findings point at the generator, never at the copy.

When, and only when, the copy is stale, the audit reply opens with that report, stated flatly,
before anything else, in this shape (a hand-written page, or a copy no older than its generator,
gets no stale line):

```
Stale: <page> (last changed at <page-commit>) is older than its generator <script> (changed at <generator-commit>).
Plan: rebuild from <script> into a scratch folder (never over <page>), probe that build, and aim
every fix at <script>. The committed copy is not audited as the source and never hand-edited.
```

Name both commits even when the repo is absent or git cannot confirm them; the user's statement is
the evidence, and the line says so. A missing file changes what was run (NOT-RUN rows), never the
stale line or the plan. Regenerating the committed copy is a separate step after the generator fix.

## 2. Widths and themes

**Widths**, default `320, 375, 768, 1024, 1440` CSS px. 320 is the width WCAG 2.2 criterion 1.4.10
Reflow names; 1440 stands for a desktop window. A plugin pane adds the narrowest width its host lets
it shrink to (`surfaces.md`). The height is a fixed desktop-like value; the screenshot is full page.

**Themes**, every theme the page offers:

| How the page offers a theme | How the probe sets it |
|---|---|
| A `prefers-color-scheme` media query | the browser context's colour scheme, `light` and `dark` |
| An attribute or class toggle (`data-theme="dark"`, `.dark`) | the attribute or class found in the source or named by the user (`--theme-attr`, `--theme-class`), set before capture on the element the selector names: `<body>` for `body.dark` or `body[data-theme=…]`, else `<html>` |
| A VS Code webview pane | the host's body class: `vscode-light`, `vscode-dark`, `vscode-high-contrast` (found in the source, or `--vscode`) |
| `high-contrast` outside a VS Code pane | the dark colour scheme plus forced colours (`forced_colors="active"`) |

The probe reads the page's own stylesheets and root classes to find these. When the page source
shows no theme mechanism, the probe runs light only and the report says one theme was found;
`--themes light,dark` overrides the choice.

**Each theme is verified.** After the toggle the probe reads the computed background and text
colours of the root, the body and the first 60 elements, and compares them with the light row at
the same width (or, when no light row ran, with the page as first loaded in a light context). Equal
colours mean the theme did not take effect: that row is NOT-RUN with the reason, never a pass. A
theme that changes only elements past the first 60 reads as not taken; set it with `--theme-attr` or
`--theme-class` and check the screenshot.

## 3. What is measured

For each width and theme, after the page settles (load, network quiet for a URL, fonts ready):

| Check | Measure | Finding when |
|---|---|---|
| Page width | the document's scroll width against the viewport width | the document is wider than the viewport by 1 px or more (sideways scroll) |
| Past the right edge | each visible element's right edge | it passes the viewport's right edge, outside a container that scrolls or clips sideways on purpose |
| Off the left edge | each visible element's left edge | it sits left of 0 |
| Clipped text | a box with text anywhere inside it (its own or a child's, such as a cell's `<span>`) whose content is wider or taller than the box while its overflow is hidden or clipped | text is cut by 1 px sideways or 2 px vertically (a 1 px line-height overhang is not); an ellipsis or a `line-clamp` is reported separately as truncated, a note rather than a finding |
| Screenshot | full-page PNG | always written, named `<width>-<theme>.png` |

Each finding row names the element by a short selector, the pixels past the edge, and the
screenshot that shows it.

## 4. Evidence check

Before a row is judged, it must be non-blank (at least one visible element painted), at the
intended width (the window's inner width equals the row's width), free of a browser error page and
an HTTP error status, its screenshot file must exist, and a non-light theme must have taken effect
(section 2). A failed check or a load that throws gets one retry; a second failure makes that row
NOT-RUN with the reason.

Skipped before judging: a box clipped to nothing on purpose (a 1 by 1 px visually hidden label, a
clip rect of zeros, `clip-path: inset(50%)`), and a box wholly off-screen inside `aria-hidden="true"`
or `inert` (a closed drawer).

## 5. Report and exit codes

One table per theme: width, document width against viewport, elements past the right edge, clipped
or truncated text, screenshot path. A `--json` form carries the same rows.

| Exit | Meaning |
|---|---|
| 0 | every row ran and passed |
| 1 | at least one finding, or a NOT-RUN row (a row nobody measured is never a pass) |
| 2 | Playwright or its browser is missing (a plain message names the install lines in section 7), or the browser could not start (the message gives the first line of the error) |
| 3 | a usage error: a bad width or theme, or a target that is neither a URL nor an existing file |

## 6. Limits

- **Interaction states are not reached.** The probe measures the page as it loads. A state reached
  only by clicking (an open menu, an error after submit) is listed from the brief as not probed,
  for the user's own capture.
- **A canvas is opaque.** A game exported to the web draws into a canvas; element checks say
  nothing about it. Game UI is checked from screenshots per resolution (`surfaces.md`).
- **No sign-in, no forms.** A page behind a login is probed only at a URL the user has already made
  reachable without one.
- **Known false positives.** A skip link parked at `left: -9999px` without `aria-hidden` or `inert`
  reads as off the left edge at every width; an off-canvas menu moved by `transform` without either
  attribute does too. Name them in the report as intended, never as clean.
- **Not exercised here.** The in-page measure is tested under Node on fixture boxes; the Playwright
  path itself has not yet run on the build machine (no Playwright there). The first real run on a
  clean page and an overflowing one is the open check.

## 7. Playwright facts and the no-Playwright path

- A browser context takes a viewport size and a colour scheme (`light`, `dark`, `no-preference`);
  a page can switch its colour scheme later with `emulate_media` (playwright.dev, Python docs,
  "Emulation", read 2026-10-13). The probe does not emulate reduced motion (Playwright's API offers
  `reduced_motion`; not used here). It uses `forced_colors="active"` on the context for
  high contrast outside a VS Code pane (the API reference's `new_context` parameter).
- Playwright runs its browsers headless by default; a window opens only when `headless` is set to
  false, which the probe never does (playwright.dev, Python docs, "Getting started - Library",
  read 2026-10-13).
- **Install, run by the user, never by the skill:** `pip install playwright`, then
  `playwright install` (the same page: the package, then the browser binaries for Chromium, Firefox
  and WebKit). The probe uses Chromium.
- **Without Playwright** the script exits 2 with those two lines. Without a shell, the skill hands
  back the exact probe command and the install lines, marks every row NOT-RUN, and continues the
  audit from the source and any screenshots the user provides.
