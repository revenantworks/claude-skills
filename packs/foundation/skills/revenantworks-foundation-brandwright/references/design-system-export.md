# Design System export — and a definition built to take one

Load on Entry — Export's fifth payload; on Entry — Build when the owner wants the definition
ready for a Claude Design System; on Entry — Audit's export-readiness check (section 4). Nothing
here is identity content: every value comes from the selected definition.

## 1. The payload

A **Claude Design System** is the claude.ai Artifact type that holds one brand as a browsable
reference other agents build on: a brand book, tokens across themes, fonts, components with live
previews, and assets. The export is that system's `project/` file tree, cut from one definition —
never two, per the cross-brand law.

| Path under `project/` | Cut from |
|---|---|
| `tokens.json` | palette role tokens, typography roles, application quick-specs (section 2) |
| `README.md` | the brand book: content fundamentals (voice profile, register map, taglines, naming), visual foundations (palette rules, type, spacing, imagery, motion, borders and light effects, accessibility floor), iconography and mark usage |
| `fonts/<file>` | the real font files the typography roles name |
| `assets/<Group>/<file>` | mark and logo files, copied byte for byte, plus a `README.md` per group |
| `components/<Comp>/README.md`, `preview.html` | only the components the application quick-specs name |
| `components/Cover/preview.html` | the cover, written last (section 5) |
| `design-system.json` | the index — written last, in the shape the type's own instructions give |

**Where the Artifact tool offers the Design System type, create the system from it and follow the
type's own instructions** for file shapes, uploads, and the save call; on any shape they state,
they win over this file. Where it does not, hand the tree back as files at these paths, so a later
upload is mechanical.

**README rules.** Imperative usage rules that name tokens ("set body copy in `text` on
`surface`"). No title, provenance, build notes, or next steps — those go in the reply. Quote the
definition's own example copy under content fundamentals. Length tracks the definition; never pad.

**Assets are copied, never approximated.** A definition with no mark file ships no drawn mark: the
export sets the name in type and says so in the README. A single-ink SVG shown through `<img>`
cannot inherit colour, so the group README names each file's ink and the ground it is for.

**Components.** Build only what the definition's application quick-specs describe (a status chip,
a card, a section rule). A component the definition never names is an invention; leave it out.

## 2. `tokens.json` mapping

- **Lists, never maps.** Every family but `type` is `{"tokens": [{"name", "value", "usage"}]}`;
  `color` adds `themes`. A name-to-value map (the DTCG shape) is valid JSON the page cannot read.
- **Themes.** One theme per ground the definition declares, **the primary ground first** — a token
  missing a later theme's value inherits the first. A role that is the same in every theme is a
  plain string.
- **Names.** `^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$`, unique across every family but `type`. Use the
  definition's role token names verbatim where they fit the grammar.
- **Values.** Hex, or `rgb()` / `hsl()` / `oklch()` with plain numeric arguments, or an alias
  `"{other-token}"` for a derived role (a lit border that equals the identity accent's lit). Never
  `var()`, `color-mix()`, or a named colour: each drops.
- **Usage on every token.** The grounds it reads on with the measured ratio, and what it is for —
  including what it never carries (identity versus state).
- **Type.** `fonts[]` gets one entry per real file (`family`, `file`, `weight`, `style`); `families`
  one stack per role, fallback included; `groups` one per role, with styles carrying `fontSize`,
  `lineHeight`, `fontWeight`, `letterSpacing`, `sample`, and `usage`.
- **Lengths.** Spacing, radius, and other size families come from the application quick-specs.
- **Provenance.** `meta: {"source": "brandwright", "definition": "<slug> v<version>", "synced":
  "<date>"}` — a note for a later re-sync, never an input.

## 3. A design-system-ready definition

A definition exports cleanly when all eight hold. Build asks about them only when the owner wants a
Design System or the definition is headed for one; an unanswered rule ships as a marked stub, like
any thin answer.

1. **Every palette role has a token name** in section 2's grammar.
2. **Every theme the brand renders in is declared with its ground**, and every role carries a value
   per theme. A second theme's values are **derived** from the first (ink companions and their
   highlights, `measurement-doctrine.md` section 10), never minted by eye.
3. **Every text token names its grounds** and clears 4.5:1 on each, in every theme (3:1 at 24 px and
   above, or 19 px bold). Borders, marks, and icons that carry meaning clear 3:1.
4. **Every fill that carries text declares an `on-` companion**, so a dark theme that lightens an
   accent does not leave white text on it.
5. **A focus ring per theme** clears 3:1 on every ground it lands on.
6. **Typography roles name real font files** or a hosted source, and each keeps a fallback stack.
7. **Marks exist as files.** A definition without one says so.
8. **States survive colour blindness.** Each state carries its word; success and danger differ by at
   least 3:1 in lightness, or success leaves the red–green axis toward blue.

## 4. Audit — export readiness

Where the brand has a Design System or the owner wants one, run section 3 against the definition.
Each failing rule is a **P2 finding in the category it belongs to** — palette drift for rules 1–5
and 8, typography and logo usage for 6 and 7 — never an eighth category.

## 5. Cover and re-sync

**Cover.** Written last: the palette as a few large solid blocks weighted by identity (a colour
that only means a state stays small), one pattern drawn from the definition's own structural motif
or rule, and the brand name in the display face. Shapes only — no drawn mark, no scene.

**Re-sync.** A definition change re-exports only the files it changed. Read the live system first —
people edit it on the page — keep README prose, usage notes, and assets added there, list tokens the
definition no longer defines, and ask before removing any.
