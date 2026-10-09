# Voice profile — fields, example pairs, banned tells, the edit-diff loop

Load on `build` (the voice group) and on `export voice`. The stored voice belongs to a brand and
lives in its definition (or `brands/<slug>/voice.md`). Applying it to one message is commscribe's
job, or any writer's; brandscribe defines, exports and audits it.

## Contents

1. Fields, in order
2. Register map
3. Example pairs
4. Banned tells
5. The edit-diff loop (proposals only)
6. Export forms

## 1. Fields, in order

1. **name** — what the voice is called (often the brand name plus a surface class).
2. **register map** — section 2.
3. **cadence** — sentence length range, paragraph length, how lists and headings are used.
4. **lexicon** — two lists in one field: *use* (preferred terms, product names in their exact form)
   and *avoid* (terms, with the replacement where one exists).
5. **sign-off** — closings and taglines, each with the surfaces it is allowed on.
6. **allowed surfaces** — where this voice speaks (docs, release notes, social, support), and where
   it must not.
7. **example pairs** — section 3.
8. **banned tells** — section 4, plus the brand's prefs (dashes, emoji).

Each field records its source. A field the guide left open ships as a `STUB` row.

## 2. Register map

One row per surface, three dials and a note. Dials are 1-5.

| Surface | Formality | Energy | Depth | Note |
|---|---|---|---|---|
| `<surface>` | 1 casual … 5 formal | 1 calm … 5 lively | 1 headline … 5 full detail | what changes here |

A surface not in the map takes the nearest row and the audit says which row it used.

## 3. Example pairs

Three to five pairs, each `Before` (plain or off-voice text) → `After` (in voice) → `why` (one line
naming the dial or lexicon rule it shows). Rules:

- **Quote, do not paraphrase.** Take `After` lines from the brand's own approved copy where it
  exists, quoted exactly with their source. A pair written in an interview is marked `interview`.
- Cover at least two different surfaces.
- No pair carries a fact that is not true of the brand; pairs teach style, not claims.

## 4. Banned tells

A starting list of six classes, kept or dropped per brand at the gate:

1. **Inflated significance** — "pivotal", "game-changing", "testament to", "in today's fast-paced".
2. **Filler and hedges** — "it's worth noting", "arguably", "in order to", stacked qualifiers.
3. **Formula shapes** — reflexive groups of three, "not just X but Y", a summary line that repeats
   the paragraph.
4. **Chat residue** — "Great question", "I hope this helps", "Certainly!", closing offers.
5. **Em dashes** — avoided by default; the brand's `prefs.dashes` decides.
6. **Emoji** — avoided by default; the brand's `prefs.emoji` decides.

A brand adds its own (overused words in its market, a competitor's slogan shape). Each entry gives
the replacement move, not only the ban.

## 5. The edit-diff loop (proposals only)

When the user hands in a draft and the version they edited by hand:

1. Diff the two at phrase level. Group the edits: lexicon swaps, cuts, register shifts, structure.
2. For each group seen twice or more, propose one profile change (a lexicon row, a dial move, a new
   example pair quoted from the user's edit, a new banned tell).
3. Show the proposals as one block at the gate. **Nothing is written to the voice file without the
   owner's yes**, and a one-off edit is never promoted to a rule.

## 6. Export forms

- **Voice profile block** — the eight fields in order, cut from the definition without reshaping,
  headed by `<slug> v<version>`. For pasting into a claude.ai Project, a custom style or a brief.
- **VOICE.md** for a repo — shape in `repo-files.md` section 2.
- **Vale style** for the lexicon — `repo-files.md` section 5.
- Inside the Design System — the README's content fundamentals (`design-system.md` section 4).
