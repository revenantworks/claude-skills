# Measurement — contrast, colour distance, the canary

Load whenever a figure is published, checked or re-derived. A figure is a claim about a computation;
without the computation it is not published.

## 1. Instruments, in order of preference

1. `python scripts/tokens_check.py contrast <fg> <bg>` — WCAG 2.x ratio of two hex colours.
   `check <tokens.json>` — list shape, names, duplicates, dropping values, aliases, usage notes.
   Standard library only; it reads its inputs and writes nothing.
2. Claude's own code tool, with the same formula (relative luminance per WCAG 2.x, ratio
   `(L1 + 0.05) / (L2 + 0.05)`), for anything the script does not cover (Delta E 2000, OKLCH conversion).
3. Neither available: write **"unmeasured on this surface"** beside the value and name the command a
   later run with a shell would execute. Never estimate by eye and publish the estimate.

Validate any colour-distance code before trusting it: reproduce at least one published CIEDE2000
reference pair (the Sharma, Wu and Dalal test data) and print it beside the first result.

## 2. Floors

- Body text 4.5:1 on every ground it is read on, in every theme. Large text (24 px and above, or
  19 px bold) 3:1.
- Borders, focus rings, icons and marks that carry meaning 3:1 on their ground.
- A brand's own floor overrides when stricter.
- State is never colour alone: a word or a form change goes with it. Colours that must be told apart
  differ in lightness, not hue alone; blue/orange pairs survive colour blindness better than red/green.

## 3. Measure the composed pair

Check a mark against the background it is actually painted on. A token correct on its designed ground
can fail on a raised surface or inside a chip. The fix changes the mark's token or its ground, never
the floor.

## 4. The canary

After any palette change, name the tightest measured pair in the palette (its two tokens, its figure,
its floor) in the definition's colour group, and re-measure it first after any later change to a
neutral. The useful fact is which cell holds the margin.

## 5. Verify against the consumer's own grader

When a downstream surface grades the palette (a Design System's contrast table, a CI gate, a linter),
a fix is verified against that surface's grading, not a stand-in that computes a similar number on
another ground. Token `usage` notes are grader input: they name the grounds the page checks. Fix one
token at a time and re-check the whole palette, because one fix can move another pair. A linter that
scores every colour against a fixed white ground gives false failures on themed pages; confirm themed
pairs with the script and report the linter's rows as unresolved, not failed.
