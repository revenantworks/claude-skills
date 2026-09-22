# Measurement Doctrine — what ships beside a measured palette

*(durable doctrine — added 2026-09-11 from task-observer observations #0029, #0030, #0035,
#0036 and #0037, and from two brand rebuilds that applied an owner colour decision and
recomputed every consequence)*

A brand definition is the estate's densest artefact of derived numbers: contrast ratios,
lightnesses, chroma margins, hue gaps, perceptual separations. Every one of them is a claim
about a process, and a document that says "every value below is measured" without shipping the
process has published trust, not evidence. This file states what has to ship beside the figures,
and how a rendered surface is actually checked.

## Contents

1. The instrument ships with the definition
2. The canary cell
3. Gamut-ceiling margin is a measurement, not a rule
4. The reflow module — what a definition ships besides tokens
5. The 400 px iframe harness — the only narrow-viewport check
6. Direction boards — one lever, measured figures
7. The swatch-board pick loop
8. History rows carry hunt targets; dated records freeze
9. Rig-copy parity
10. Propagation is its own unit
11. Palette exploration and refresh

---

## 1. The instrument ships with the definition

A definition that publishes derived figures ships **two** things beside them, in the same repo:

- **The instrument that produced them**, with its own reference-data self-test. Colour work
  means sRGB/WCAG, CIELAB, CIEDE2000, OKLab/OKLCH, gamut-boundary mapping and lightness solving
  at the final chroma; the self-test is the full published reference set for the metric, not a
  sample of it. One definition cited 11 CIEDE2000 reference pairs where the published set is 34
  — the count was the least of it, because a claim about an instrument nobody can run is not
  checkable in either direction.
- **A check that parses the definition's own tables and re-derives every published figure**,
  wired into whatever gate the repo already runs. Prefer re-deriving from the artefact's own
  printed formulas over comparing against stored expectations, so a rule change and a value
  change cannot drift apart.

**Give the check a negative control before trusting it.** Inject a wrong digit into three
different tables and confirm it fails on all three, named, then revert. A check that has only
ever passed is an untested claim.

**Verify the instrument against the existing figures before using it on new ones.** Reproduce
the current version's published values first; only then compute the new ones. An instrument that
disagrees with the file it is about to grade is either wrong or has found something, and you
cannot tell which until the old numbers reproduce.

Writing the instrument is also how the asserted claims surface. One pass found four in a file
whose own hard rules demand measurement: a claim asserted from a shape rather than measured (a
hue gap that was real while the room in it was not), a claim true when written and invalidated
by a later unrelated change, a claim the file contradicted three lines on, and the reference-set
count above. Care was not the missing ingredient — an instrument was.

**Same rule, other artefacts.** Where a playbook, verdict or report rests on computed figures,
publish the computation, not only the result.

## 2. The canary cell

After any palette move, name the **tightest measured pair in the palette** explicitly in the
definition and call it the canary: the cell that will fail first if a neutral is nudged. State
its current figure and its floor, and state what breaks the day it drops below — which surface,
which generator, which component. One palette's canary read 3.01:1 against a 3:1 floor, clearing
by a hundredth; a later re-pick moved it to 3.35:1. Both numbers belong in the file, because the
useful fact is not the margin but which cell holds it.

Re-measure the canary **first** after any change to a neutral, before recomputing the rest.

## 3. Gamut-ceiling margin is a measurement, not a rule

Publish each base's margin below its hue's sRGB chroma ceiling as a measured figure. When an
owner's chosen hex lands exactly on the ceiling, **ship the hex and state the exception** — an
explicit colour decision outranks a published margin, and the honest record is the flagged zero,
not a nearby substitute quietly swapped in. Retire the old blanket claim ("every base carries at
least N%") in the same pass, in History, rather than leaving a sentence the file now falsifies.
Offer the alternative in one line: a slightly less saturated value restores the old posture, at
the cost of the owner's pick.

## 4. The reflow module — what a definition ships besides tokens

A brand rendered by more than one generator ships a **small layout module** beside its tokens,
as one file every generator imports or embeds — not as prose in the guide:

- tile and swatch grids: `repeat(auto-fit, minmax(<min>px, 1fr))`, min stated
- chip and badge rows wrap
- every table inside its own `overflow-x: auto` container
- one side gutter, stated in pixels, honoured at every width
- the theme-token pattern (bare-root light palette, `prefers-color-scheme` block, explicit
  `[data-theme]` override) as a single copyable block
- the type scale

The reason is structural. Four generators, written at different times by different sessions,
each carried the same phone-width clipping defect independently — every one of them using the
brand's hexes correctly, so every one of them passed the definition's own test while breaking on
a phone. **A style guide that specifies only what things look like leaves how they reflow to each
author separately, and separate authors converge on the same bug.** Ship the convention as code,
and check it at the width where it breaks.

## 5. The 400 px iframe harness — the only narrow-viewport check

**State the narrow-viewport check as the harness, never as a window-size recipe.**

Load the page into an `<iframe>` of exactly 400 CSS px inside a normally sized window, and read
the **inner** document's `clientWidth` and `body.scrollWidth`. The frame is a real viewport for
the inner document — media queries, percentages and wrapping all honour it — and no window floor
applies. A 400 px frame measures 385 CSS px of content (the 15 px is the frame's own scrollbar).
Calibrate the harness once with a page carrying a right-anchored marker and a `width:100%` bar:
if the right marker is missing from the capture, the layout is wider than the image.

Serve the pages over a throwaway loopback HTTP server when `file://` access is blocked; a
headless browser may also need an explicit flag to let the harness read the inner document over
`file://`.

**Print the measured viewport width into the artefact being checked**, so a reviewer sees the
width the page actually rendered at rather than the width somebody requested.

Two recipes that look right and are not, both recorded because each cost a wave:

- `--window-size=400,H` — this browser floors the window near 500 CSS px and still writes the
  PNG at the *requested* width. The file is a crop of a wider layout, and content that would
  wrap at a true 400 px looks identical to genuine overflow (#0029).
- `--force-device-scale-factor=2 --window-size=800,H` — prescribed as the correction for the
  above, and measured at `innerWidth` **770**. The scale factor multiplies the output raster; it
  does not divide the CSS viewport. Anything wrapping between 400 and 770 px verifies as correct
  at a width the page never rendered at (#0035, #0036).

And two remedies that cannot run in a headless context: an injected `window.innerWidth` probe
(JavaScript may not execute at all — a probe with a placeholder default rendered its placeholder
text verbatim) and `--dump-dom` (returned nothing). **A remedy is only a remedy where it runs.**

One more instrument trap worth carrying: measuring "does content reach the right edge" from
pixels reports overflow on every page at every width, because the rightmost columns are the
**scrollbar**. Filter for a contiguous greyscale band at the right first, then measure inside it.

**The rule underneath all of it.** A recipe handed down with its result already asserted ("this
yields 400 CSS px") suppresses the very check that would catch it, and the more precisely it is
written the more it is trusted — a prescribed correction most of all, because it arrives framed
as the careful option. Prescribe the **property and its calibration**, not the command. Before a
replacement recipe is written into any skill or brief, run it once and read the value it was
supposed to fix out of the render itself.

## 6. Direction boards — one lever, measured figures

A direction board that offers the owner a choice moves **one lever per direction** — structure,
or type, or a ground — and names it. Every figure a board prints is measured by the instrument,
not estimated for the mock-up, so a direction the owner picks arrives with its consequences
already true rather than needing a second pass to discover them. Each direction states what it
costs: which rules bend, which figures move, what has to be re-derived if it is chosen.

## 7. The swatch-board pick loop

When an owner is picking a ground colour, do not offer hexes in prose. Build a swatch board of
candidate grounds, letter-labelled, each shown with **the ramp regenerated at that candidate's
own hue** rather than the current ramp recoloured — the ramp is what the owner is actually
choosing. Include deliberately darker steps beyond the expected answer; the pick has repeatedly
landed outside the range a session would have offered on its own. Take the letter, then
regenerate: neutrals at the new hue holding each token's own chroma and the same lightness step
sizes, accent `lit`/`glow` re-derived at the new grounds (accent-derived and ground-independent
values stay put, and saying which is which is part of the record), and every published figure
recomputed by the instrument.

## 8. History rows carry hunt targets; dated records freeze

Every History row that retires a value lists **the retired hexes as hunt targets** — the exact
strings a later audit greps for across every generator. Stale-identity hunting is one of the
audit's seven categories and it only works if the strings are written down.

Two rules keep the hunt honest:

- **A dated History row is frozen.** A new version adds a new row; it never edits an older one.
  The retired values must keep appearing there, which is why the definition's own History table
  is the one place a retired hex is allowed to live.
- **A hunt-target occurrence outside History is a finding unless the sentence containing it
  declares it a hunt target.** Say that in the file, so the sweep can tell a declaration from a
  leak without a human reading every hit.

## 9. Rig-copy parity

Where a definition is mirrored to a local path something else loads (a rig copy, an installed
copy, a knowledge file), **diff the copy before writing it, write it after, then verify it
byte-identical** — a sha256 of both, stated in the report. Diff first, because the copy may
carry an edit the tracked file does not, and an overwrite is silent.

## 10. Propagation is its own unit

Applying a definition change and propagating it to the generators that consume it are **two
units, sequenced, never one**. The definition repo is one writer's; each consuming repo is
another's. A propagation unit's job is: take the new tokens, retire the old hexes by their hunt
strings, recompute contrast in that repo's own tests, regenerate the outputs, verify reflow with
the harness in section 5, and leave dated reports untouched.

**Where the definition declares only one ground, light mode comes from the definition's own ink
companions, never from invented hexes.** A generator that needs a light variant and finds none
in the definition stops and says so; it does not mint three plausible values. The correct fix is
in the definition — a documented light variant — and until it exists, generators keep their
current theme branches unchanged.

**A change that renames or re-roles tokens publishes a role map beside its retired hexes**
(observation #0134): each retired token name, the token that now carries its job, and "none —
the job moved to a neutral" where no successor exists. A list of dead values tells a propagator
what to delete; only the map tells it what the surviving code should be called. Propagation
then renames consumer keys against the map, so no legacy name (`gold`, `teal`) is left carrying
a colour it no longer means — and a stale-string hunt can tell a key kept on purpose from one
that was missed.

**Two propagation traps, both seen in one pass.** A test that asserts a string never appears in
a rendered page must strip the page's `<style>` blocks first: an embedded base64 font subset
contains arbitrary three-letter runs, and one failed a "this acronym never reaches the reader"
check. And a headless screenshot follows the machine's colour-scheme preference, so a light-mode
capture is taken with the theme forced (`data-theme`), never assumed from a default run.

**Hold propagation while the palette is still moving.** When the owner revises the palette
more than once in a session, finish the definition, the guide and the design system first and
propagate once, on the owner's go — every intermediate rollout is a sweep across N repos that the
next revision undoes.

---

## 11. Palette exploration and refresh

When the owner asks for a new palette, a refresh, or "more pop", the work is a comparison, not a
proposal. Six rules, each learned by getting it wrong once.

1. **Draw every option, beside the current design.** A palette described in prose is not a
   palette the owner can pick: render each option as the same small surface — the wordmark, a
   card, a status chip pair, a short data series — next to the live palette as the baseline.
   "I need to see the options" means the prose already failed.
2. **Start from the owner's themes and hard constraints, and apply the constraints to every
   option before it is shown.** A from-scratch pass offers around six distinct directions; a
   constraint the owner states mid-way ("the mark is always X on a ground of Y") is re-applied to
   all of them and re-measured, never only to the favourite.
3. **Report each option's usability, not only its separation.** For every accent, print its
   ratio on the ground *and* its maximum ground (section: the definition's Maximum-ground table);
   for the set, the minimum ΔE00 pair. An accent that clears the collision floor but fails 3:1 on
   the raised grounds the product actually uses is not a usable accent — show a usable candidate
   at the floor beside the maximally separated one, and let the owner see both.
4. **"Nothing pops" is diagnosed before it is fixed.** Check whether every surface is one neutral
   and whether the identity accent appears only as thin lines and small text. Tinted washes add
   depth but can read as clutter; the cheapest reliable fix is often a **highlight token** — one
   existing accent at a much higher lightness, spent once per view, never a fill, never a state.
   It adds brightness without adding a hue, so it sits outside the collision floor by construction.
5. **A wordmark may take its own neutral.** Setting the name in a warm or cool white distinct
   from body text (ΔE00 ≥ 10 from the text colour) keeps the identity accent singular — the mark
   carries the colour, the name carries the weight — and is a legitimate identity decision, not
   a demotion of the accent.
6. **An owner's pick that lands on the gamut ceiling is recorded, not corrected.** State the 0.0%
   margin as an exception in the palette section (section 3) with the reason, rather than quietly
   shifting the hex the owner chose.

**Imagery rules name families, not items.** When a definition sets its imagery, it lists the
motif families that are on-brand and the ones that are out unless a piece calls for them, and it
separates *imagery* from *the mark*: a motif that is allowed as illustration (a many-pointed rose,
say) is never allowed to stand beside the wordmark as if it were the logo.
