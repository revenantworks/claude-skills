# Probe: a rendered page runs, holds its content and fits, at every width and theme

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
| Spilled text | a table cell (`td`, `th`) or grid item with text whose content is wider than the box while its overflow is visible, such as a `nowrap` cell in a fixed-layout table | it is wider by 1 px or more: the text paints over its neighbour though nothing scrolls or clips. Listed in the Clipped column as `<selector> spills` |
| Page errors | every uncaught exception, from before the page loads to the end of the row | any one, however well the page fits |
| Console errors | every `console.error`, and what the browser logs at that level (a failed request, a blocked script) | any one; warnings and logs are not |
| Empty sections | each rendered `main`, `section`, `article`, open `details`, `role=main`, `role=region` or `role=tabpanel`, plus each `--section SELECTOR` | it, and everything inside it, draws nothing: no visible text; no visible image, `svg`, `canvas`, video, audio, frame or form control; no background colour or image; no visible border; no `::before` or `::after` content |
| Named sections | each `--section SELECTOR` | it matches nothing rendered or in a fold, or is not a valid selector |
| Console errors' source | the URL the browser gives with each console error | appended to the error text, so a failed request says which one |
| Screenshot | full-page PNG | always written, named `<width>-<theme>.png`, and `<width>-<theme>-open.png` for the folds-open state |

Each finding row names the element by a short selector, the pixels past the edge, and the
screenshot that shows it. A section's selector carries its first heading.

**A blank section is not an overflow.** A script that crashes leaves the page's frame in place, so
the page fits and every width passes while most of it is empty. That is why page errors and empty
sections are findings beside the fit checks. A heading, a `legend`, a `caption`, a table head and a
fold's own `summary` are labels, not content: a section holding only those counts as empty. Visually
hidden text (section 4's shapes) does not count either. Only the outermost empty section is named. The
walk follows what the browser draws: through `display: contents`, open shadow roots and slots. A
section with height 0 and hidden overflow is empty whatever it holds, unless it is a collapsed panel:
an `aria-expanded="false"` control's `aria-controls` names it or an ancestor with no box. A section
that is `hidden`, `inert` or `aria-hidden`, or sits inside one, is not checked. Text in a box of no
height or width is not reported as clipped, since nothing of it shows.

The default list finds semantic sections only. A page built from plain `div`s gets nothing from it,
and the report says when no section was found, with the verdict `PASS (empty sections not checked)`:
name that page's regions with `--section`.

**Settling.** Before each state is measured, and after each round of opening folds, the probe waits
for fonts, two frames, then 300 ms with no change to the page's content (at most 2 s), so a section a
script fills straight after load or after a fold opens is measured filled.

**Two states, when the page has folds.** A fit check measures only the state it renders, and a
layout pass that folds wide content away reads as a fix. So a page with any closed `details` is
measured as loaded, then again with every fold open, nested ones and a fold another fold's handler
adds included, and each state gets its own report line and screenshot. An exclusive accordion
(`<details name>`) loses the `name` in the probe's own copy of the page, so all of it opens at once.
As loaded, a closed fold's body is skipped by every check, though its `summary` is not; Chromium
still lays that body out, and its boxes would otherwise read as visible. An error thrown while the
folds open is charged to the folds-open state. A page with no closed fold is measured once.

## 4. Evidence check

Before a row is judged, it must be non-blank (at least one visible element painted), at the
intended width (the window's inner width equals the row's width), free of a browser error page and
an HTTP error status, its screenshot file must exist, and a non-light theme must have taken effect
(section 2). The folds-open state passes the same checks, and its folds must stay open: a page that
keeps closing them was not measured open. A failed check or a load that throws gets one retry; a
second failure makes that row NOT-RUN with the reason. A page error is a finding on a row that ran,
never a reason to retry it.

Skipped before judging: a box clipped to nothing on purpose (a 1 by 1 px visually hidden label, a
clip rect of zeros, `clip-path: inset(50%)`), and a box wholly off-screen inside `aria-hidden="true"`
or `inert` (a closed drawer).

## 5. Report and exit codes

One table per theme, one line per width and state (`as loaded`, then `N folds open`): document
width against viewport, elements past the right edge and off the left, clipped and truncated text,
empty and missing sections, page and console errors, status, screenshot path. Error text is page
data: each is cut to one line of 300 characters, at most 20 per row. A `--json` form carries the same
rows: `result` for the page as loaded and `folds_open` (`folds`, `result`, `screenshot`) when it has
folds; `folds_open` also counts toward the row's `status`.

| Exit | Meaning |
|---|---|
| 0 | every row ran and passed |
| 1 | at least one finding, or a NOT-RUN row (a row nobody measured is never a pass) |
| 2 | Playwright or its browser is missing (a plain message names the install lines in section 7), or the browser could not start (the message gives the first line of the error) |
| 3 | a usage error: a bad width or theme, or a target that is neither a URL nor an existing file |

## 6. Limits

- **Interaction states are not reached, beyond folds.** The probe measures the page as it loads and
  with its `details` open. Any other state reached only by clicking (an open menu, an inactive tab,
  an error after submit) is listed from the brief as not probed, for the user's own capture. A
  hidden tab panel is neither measured nor called empty; `--section` naming one reports it missing.
- **Errors are seen until the row ends.** One thrown later (a timer, a late response on a local file,
  where the probe does not wait for the network) is not seen.
- **An empty section can be on purpose.** A results panel waiting for a search reads as empty; hide
  it until it fills (`hidden`), or name it in the report as intended, never as clean.
- **Spills are checked in cells and grid items only.** Text that paints out of any other box with
  visible overflow (a flex child, a plain block) is not reported unless it passes the viewport edge;
  a positioned child (a tooltip) can widen a cell and read as a spill. Look at the screenshot.
- **The page's data is the data it was given.** A data-driven page passes here only for the data it
  loaded; run its script in a test with empty, sparse and real data before it ships, and read each
  section of the rendered page before calling it done.
- **A crushed box is not called clipped.** Text in a box with no height or width reports nothing, so an
  overflow-hidden block crushed to zero height passes here. Look at the screenshot.
- **A drawn box can be empty.** Anything the CSS draws counts as content, so a card with a background
  or border and nothing but a heading does not read as empty, and neither does a skeleton placeholder.
  That shape is caught only if the script logged or threw an error. Look at the screenshot.
- **Unseen content.** A closed shadow root reads as empty, and a section inside any shadow root is not
  in the default list. A section filled after the wait above reads as empty: name it in the report as
  intended, or make it fill sooner.
- **A canvas is opaque.** A game exported to the web draws into a canvas; element checks say
  nothing about it. Game UI is checked from screenshots per resolution (`surfaces.md`).
- **No sign-in, no forms.** A page behind a login is probed only at a URL the user has already made
  reachable without one.
- **Known false positives.** A skip link parked at `left: -9999px` without `aria-hidden` or `inert`
  reads as off the left edge at every width; an off-canvas menu moved by `transform` without either
  attribute does too. Name them in the report as intended, never as clean.
- **Where it has run.** `test_probe.py`'s `RealBrowser` class loads small real pages in headless
  Chromium; it skips where Playwright or its browser is absent, so a machine without them proves
  only the fake browser and the in-page measure under Node on fixture boxes.

## 7. Playwright facts and the no-Playwright path

- A browser context takes a viewport size and a colour scheme (`light`, `dark`, `no-preference`);
  a page can switch its colour scheme later with `emulate_media` (playwright.dev, Python docs,
  "Emulation", read 2026-10-13). The probe does not emulate reduced motion (Playwright's API offers
  `reduced_motion`; not used here). It uses `forced_colors="active"` on the context for
  high contrast outside a VS Code pane (the API reference's `new_context` parameter).
- `page.on("console", ...)` with `msg.type == "error"` and `page.on("pageerror", ...)` report a
  thrown exception and a logged error; `Element.checkVisibility` tells a rendered section from a
  hidden one, and Chromium lays out a closed fold's body (run on Playwright for Python with Chromium
  153, 2026-11-03, in `RealBrowser`; not a docs read).
- Playwright runs its browsers headless by default; a window opens only when `headless` is set to
  false, which the probe never does (playwright.dev, Python docs, "Getting started - Library",
  read 2026-10-13).
- **Install, run by the user, never by the skill:** `pip install playwright`, then
  `playwright install` (the same page: the package, then the browser binaries for Chromium, Firefox
  and WebKit). The probe uses Chromium.
- **Without Playwright** the script exits 2 with those two lines. Without a shell, the skill hands
  back the exact probe command and the install lines, marks every row NOT-RUN, and continues the
  audit from the source and any screenshots the user provides.
