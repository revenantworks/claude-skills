# Direction: the brief, the checklist and the finding row

Load on Direct and Audit. The brief is what a builder works from; the same checklist reviews a
mockup before the build and a page after it.

## Contents

1. Surface class
2. The brief template
3. Accessibility bars (WCAG 2.2)
4. The taste checklist
5. Finding rows and ranking

## 1. Surface class

Name one class before writing anything; it sets the density and the primary action.

| Class | People come to | Density | Example |
|---|---|---|---|
| task | get something done | high, scannable | a dashboard, a settings pane, an inventory screen |
| persuade | decide | low, one path | a store page, a landing page |
| read | read and come back | text first, measured line length | docs, a report, a codex screen |
| showcase | look | the look is the point | a title screen, a portfolio |

These are the classes brandscribe's `ui` review uses, so a brief and a later scored review speak
one language.

## 2. The brief template

One document, one section per field. A field with nothing to say is written `none` with the reason.

| Field | What it holds |
|---|---|
| Purpose | One sentence: what the screen is for and the one primary action per view |
| Users and input | Device, viewing distance, input methods (touch, mouse, keyboard, gamepad) |
| Content inventory | Real or realistic content, with the longest value, the empty case and the largest number |
| Layout | Regions, reading order, the grid, and the width or resolution set it must hold |
| Hierarchy | What is seen first, second and third, and what carries the rank (weight, space, position, contrast) |
| Spacing scale | One base unit and its steps, named from the tokens; every gap on the page is a step |
| Type scale | Roles (display, heading, body, label, caption) as steps of one scale from the tokens; body line length |
| States | A table per component: default, hover, focus, active, disabled, loading, empty, error, long content |
| Interaction feedback | Every input gets a visible response; anything that waits shows a pending state; errors say where |
| Motion | What each motion shows (a change of state or place) and its reduced-motion fallback (`prefers-reduced-motion` on the web) |
| Accessibility | The bars in section 3 that apply, and the focus path (order, first focus, how focus returns) |
| Tokens | Each role used, mapped to its source (brand definition, project tokens, host theme); open roles listed, never filled with invented values |
| Word slots | Each label, message and empty-state line as a slot with a length budget, handed to commscribe |
| Open questions | What the brief could not settle, one line each |

## 3. Accessibility bars (WCAG 2.2)

From WCAG 2.2, W3C Recommendation of 12 December 2024. The level is the conformance level the
criterion sits at.

| Bar | Criterion | Figure |
|---|---|---|
| Text contrast | 1.4.3 Contrast (Minimum), AA | 4.5:1; large-scale text (18 pt, or 14 pt bold) 3:1 |
| Control and graphic contrast | 1.4.11 Non-text Contrast, AA | 3:1 against adjacent colours, for component boundaries, states and meaningful graphics |
| Colour alone | 1.4.1 Use of Color, A | colour is never the only way a state or meaning is shown |
| Reflow | 1.4.10 Reflow, AA | no scrolling in two dimensions at a width equal to 320 CSS px — why the probe's width set starts at 320 |
| Text resize | 1.4.4 Resize Text, AA | text resizes to 200 percent without loss of content or function |
| Focus visible | 2.4.7 Focus Visible, AA | a keyboard focus indicator is visible |
| Focus not hidden | 2.4.11 Focus Not Obscured (Minimum), AA | the focused component is not entirely hidden by author content (sticky headers, toasts, a HUD panel) |
| Target size | 2.5.8 Target Size (Minimum), AA | pointer targets at least 24 by 24 CSS px, with the criterion's exceptions (spacing among them) |
| Larger targets | 2.5.5 Target Size (Enhanced), AAA | at least 44 by 44 CSS px; the brief states when it aims for this |

**Contrast is computed**, never read off a screenshot by eye: brandscribe's `tokens_check.py` when it
is installed, or Claude's code tool, from the two colour values. With neither, the bar is stated and
the figure written "unmeasured".

**Game UI.** WCAG is written for web content. A game's menus take these bars as the floor where a
pointer applies, and add the gamepad path: every control reachable by directional focus, a first
focus on every screen, and focus never lost when a panel opens or closes (`surfaces.md`).

## 4. The taste checklist

Questions the brief answers before anything is built. A pattern is not wrong; a pattern nobody chose
is the finding. P3 rows, never blocks.

1. **Point of view.** One sentence naming the feel the screen is going for, chosen for this product
   and these users. "Clean and modern" is not a point of view.
2. **One thing to remember.** The single element a user would recall: a layout move, a type choice
   from the tokens, a transition. A screen with none reads as a template.
3. **Real content.** The brief carries realistic content: the longest name, the empty list, the
   five-digit number, the translated label that runs longer. Placeholder text hides the layout's
   failures.
4. **Density fits the class.** A task screen is denser than a showcase; a HUD shows only what the
   current moment needs.
5. **Defaults questioned.** A centred headline over three identical cards, a gradient on every
   surface, the same radius and shadow on everything, emoji standing in for icons, a purple-to-blue
   accent nobody picked: each is fine when the brief says why, and a finding when it says nothing.
6. **Rank by more than size.** Weight, space, position and contrast each carry hierarchy; a screen
   that only scales type up and down has one tool where it needs four.
7. **One rhythm.** Every gap is a step of the spacing scale; a one-off value is a finding.
8. **Motion with a job.** Each motion shows a change of state or place; motion that only decorates is
   cut, and every motion has its reduced-motion fallback.

## 5. Finding rows and ranking

Row: `ID · P0-P3 · where · finding · exact change · Apply / Optional / Skip`. "Where" is a file and
line, a selector, a width and theme (`375 × dark`), or a screen and resolution for game UI.

| Level | Meaning |
|---|---|
| P0 | A task cannot be done, or content cannot be reached, at a width or resolution in the set (a button off-screen at 320) |
| P1 | A measured break: page wider than the viewport, clipped text, focus lost or hidden, a section 3 bar missed |
| P2 | A missing state, an off-scale value, weak hierarchy, a gamepad path that works but jumps |
| P3 | A taste question from section 4; never blocks |

Order the catalog: measured rows first, then missing states, then hierarchy and spacing, then taste.
A row about words (a vague error, a label that truncates, an empty state with no next step) is
tagged **copy** and handed to commscribe; uismith names the slot and its length budget, never the
new string.
