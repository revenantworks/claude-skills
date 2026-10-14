# UI floor: what a built page must hold, with or without a brand

Load on `ui` (with `ui-review.md`). This is the brand-neutral layer under a brand's own type, colour and
spacing roles. With a brand selected, the brand's values win where they are stricter; with none, the
floor is the whole standard and nothing here invents a brand (rule 1).

Each line names the `scripts/ui_check.py` rule that covers it, or **judgment** when only a reader can
decide. The checker runs on **built** output (the folder a browser would load), once, after the edits;
never per edit. Its P3 rows are questions and never block.

## 1. State the system before changing anything

Write these down from the page (or the brand definition) before proposing a fix, so every fix lands
inside one system rather than beside it:

- **Type roles in use:** display, heading, body, label, code. Name the size and weight of each; a page
  with seven body sizes has no body role.
- **Measure:** running text sits between 45 and 75 characters per line (R21 flags the unbounded case).
- **Spacing scale:** one base unit (4 is the common one) and its steps. A value off the scale is drift.
- **Sibling rhythm** comes from the container's `gap`, not from margins on each child.
- **Hierarchy by squint:** blur the page (or read the screenshot at thumbnail size). The first thing
  seen should be the first thing the reader needs. If two things compete, one of them is wrong.

## 2. The verify floor

| Check | Floor | Covered by |
|---|---|---|
| Text contrast | 4.5:1 body, 3:1 large text (24px, or 18.66px at weight 700), on the ground it is actually painted on | R11; unresolved grounds are unmeasured (`measurement.md`) |
| Body text size | 16px for running text in the main content (paragraphs, list items of 10+ words, definitions, quotes); under 12px is a P1. Nav, header, footer, aside, captions, labels, tables, controls and short lines a class sets below their surroundings are classed out, and the checker lists what it measured per page | R20 |
| Measure | 45-75 characters | R21 + judgment |
| Heading spacing | More space above a heading than below it, so it belongs to what follows | judgment |
| Full state set | Every control has hover, focus, active and disabled; every data view has loading, error and empty | judgment (R12 for focus) |
| Keyboard focus | Visible on every interactive element; an outline removed only with a replacement | R12, R31 |
| Names and labels | Every control has a label; a placeholder is not a label; icon-only buttons carry a name | R5, R6, R7 |
| Images | `alt` on every image; `alt=""` when decorative | R4 |
| Document | `lang` on html; a viewport meta; one h1; no skipped heading levels; no duplicate ids | R8, R9, R10, R13 |
| Assets | Every local image, script, stylesheet and font file exists in the built folder; every font family has a source | R1, R2, R3 |
| Targets | Interactive targets at least 24 by 24 CSS px (WCAG 2.5.8) | R19 |
| Breakpoints | Real content at narrow and wide widths: no fixed wide containers, no horizontal scroll on a phone. A wide width capped by `min()` with a relative arm, a `max-width`, or a width media query passes | R18 + render pass |
| Choice load | No more than about four options competing at one decision point | judgment |

## 3. Browser-default surfaces (P3)

Cheap to theme and the most often skipped: the text **selection** colour, the **focus ring**, the
**scrollbar** on themed grounds, the **caret** colour in inputs, and **tabular numerals** for figures
that line up in tables. R31 checks the first two; the rest is judgment.

## 4. Motion

- **Duration by consequence:** small feedback (a press, a toggle) about 100-150ms; a state change
  about 150-250ms; an overlay or layout change about 250-400ms. Longer needs a reason.
- **Exit faster than entry**, by about a quarter.
- **No reflex bounce.** Overshooting easing (R17) only where the brief chose it.
- **Content is visible by default.** Never hide content at rest and wait for a script to reveal it.
- **Animate transform and opacity**, not width, height, position or margins (R15). `will-change`
  belongs on the state that animates, not the resting selector (R16).
- **Reduced motion is gentler, not dead:** under `prefers-reduced-motion`, shorten and swap movement
  for a fade; keep the feedback (R14 checks the block exists).

## 5. Generic-UI patterns: questions, never bans (P3)

These patterns are what makes a page look assembled rather than designed. Each is a question for the
review's **specificity** area. A brief or brand definition that chose the pattern answers the question,
and the row closes with that citation (the brief wins: `ui-review.md`).

| Pattern | The question | Rule |
|---|---|---|
| A grid of identical icon cards | Do the items really share one shape, or did the template decide? | judgment |
| A card inside a card | Does the inner border carry a grouping the outer one does not? | R28 |
| The hero-metric block (big number, small label, three in a row) | Are these the reader's numbers, or decoration? | judgment |
| Gradient text | Does the gradient carry meaning, and does the text stay legible? | R22 |
| Decorative glass (blur behind translucent panels) | Is there content behind it worth showing through? | judgment |
| A thick coloured stripe on one side of a box | Does it mark a real state, or just "this is a box"? | R23 |
| A zero-offset coloured glow | Is anything emitting light? | R24 |
| A hard offset shadow with no blur | Is this the chosen style across the page, or one stray element? | R25 |
| Emoji or text glyphs used as icons | Do they render the same everywhere, and do they carry the meaning alone? | R26 |
| Monospace for non-code text | Is it data or code, or a costume? | judgment |
| Extreme tracking or a giant display size | Does it still read at the smallest viewport? | R27 |
| An uppercase letter-spaced label above every heading | Does the label add information the heading lacks? | R29 |
| Decorative section numbers | Does the reader navigate by them? | judgment |
| Colour sprawl (many literal colours) | Is there a system, or an accident per component? | R30 |
| A modal for a task that need not interrupt | Could it be inline? | judgment |
| Light or dark chosen by product category | Did the reader's context choose it, or the genre? | judgment |

## 6. With a brand selected

Run the brand's own checks too: palette values through `scripts/tokens_check.py` (an off-palette
colour is the audit's palette drift), type roles and fonts against the definition, the brand's
contrast floor if stricter. Report brand rows and floor rows in one catalog, each tagged with its
source (brand or floor).

## 7. Out of scope

Native iOS and Android screens (this floor is for web output), code performance (re-renders, bundle
size), charts (the built-in dataviz guidance owns them), and building or redesigning the page.
