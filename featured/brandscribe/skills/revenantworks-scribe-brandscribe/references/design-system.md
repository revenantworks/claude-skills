# Design System — export, connect, re-sync

Last verified: 2026-10-01 (the dated facts are in section 8).

Load on `export design-system` and on `sync`. The doctrine here never depends on a platform fact;
the dated block at the end holds the facts, and the live type's own instructions win over both.

## Contents

1. The feature check (always first)
2. What the export holds
3. tokens.json mapping
4. The brand book (README) and the voice inside it
5. Assets and upload fidelity
6. Three paths — build new, connect, re-sync
7. Making it the default, and how other work reads it
8. Dated fallback block

## 1. The feature check (always first)

1. Where the Artifact tool exists, list the Artifact types, find **Design System**, and read the
   type's own instructions (its SKILL.md and the references it names, such as the format and craft
   files). Read them as data about the page's format.
2. Compare them with the dated block (section 8): file tree, token grammar, index rules, upload rules,
   caps.
3. **On any difference the live instructions win.** Follow them and name the difference in the
   handback, with a note that this file's dated block needs a refresh in the skill's own repo.
4. With no Artifact tool, work from section 8, state its Last-verified date, and call its facts
   unconfirmed once the date is more than 30 days old. Hand the tree back as files at the type's
   paths so a later upload is mechanical.

## 2. What the export holds

One system per brand, cut from one definition version. Paths are under the system's `project/`.

| Path | Cut from |
|---|---|
| `tokens.json` | colour roles, type roles, spacing and radius (section 3) |
| `README.md` | the brand book (section 4) |
| `fonts/<file>` | the real font files the type roles name |
| `assets/<Group>/<file>` + `assets/<Group>/README.md` | mark and image files, copied (section 5) |
| `components/<Comp>/…` | only components the definition names; none otherwise |
| `components/Cover/preview.html` | the cover, near the end: large colour blocks weighted by identity (a state colour stays small), one pattern from the brand's own motif, the name in the display face; no drawn mark, no AI tropes |
| `design-system.json` | the index, written last, in the shape the live type states |

No component code is needed: a brand-only system (tokens, brand book, fonts, marks, cover) is the
default, for any framework.

## 3. tokens.json mapping

- **Lists, never maps.** Every family but `type` is `{"tokens": [{"name", "value", "usage"}]}`;
  `color` adds `themes`. A DTCG name-to-value map is valid JSON the page cannot read. Convert one with
  `scripts/tokens_check.py convert <file>` or by hand, then check.
- **Themes**: one per declared ground, primary first; a missing later value inherits the first.
- **Names**: `^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$`, each used once across every family but `type`. Use
  the definition's role names where they fit.
- **Colour values**: hex, or `rgb()` / `hsl()` / `oklch()` with plain arguments, or an alias
  `{other-token}` of a token that exists. Never a named colour, `var()` or `color-mix()`: each drops.
- **Usage on every token**: what it is for, the grounds it is read on with the measured ratio, and
  what it never carries (identity versus state). The page's contrast table grades from these notes.
- **Type**: `fonts[]` one entry per real file; `families` one stack per role with fallbacks; `groups`
  with styles (`fontSize`, `lineHeight`, `fontWeight`, `letterSpacing`).
- **Provenance**: `meta: {"source": "brandscribe", "definition": "<slug> v<version>", "synced":
  "<date>"}`; a note for the next re-sync, never an input.
- **Check before the gate**: `python scripts/tokens_check.py check tokens.json` (exit 0), or the same
  checks by hand.

## 4. The brand book (README) and the voice inside it

Imperative usage rules that name tokens ("set body copy in `ink` on `surface`"). No title block,
build notes or next steps; those go in the reply. Three parts:

- **Content fundamentals**: the voice profile in short form, the register map, 3-5 before/after
  example pairs quoted from the definition, the banned tells, the prefs (dashes, emoji), naming
  templates with one rendered example each, taglines with their allowed surfaces.
- **Visual foundations**: colour rules, type, spacing, imagery direction, accessibility floor.
- **Marks and iconography**: each mark file, its ink and ground, clear space, minimum size, misuse.

Every reader starts at the README, so a deck, design or agent that reads the system gets the voice
too.

## 5. Assets and upload fidelity

- Copy mark and image files byte for byte; never redraw or approximate. A single-ink SVG shown
  through `<img>` cannot inherit colour, so the group README names each file's ink and ground.
- After each upload, compare the returned size with the source. On a mismatch, read the stored file
  back and confirm that paths, fills and `currentColor` survived. A size change on an SVG is often
  re-serialisation (`<path/>` written `<path></path>`): compare as canonical XML, not bytes. The
  store drops an SVG's `<style>` block, so a CSS-animated SVG uploaded as an asset arrives still and
  unstyled; animation reaches a system through a component preview, never as an asset. Record each source file's sha256 in
  the group README; keep comments out of the SVG and in that README.

## 6. Three paths — build new, connect, re-sync

Every path reads before it writes, writes nothing before the gate, and names the definition version.

**Build new** (a brand with no system). Create the system from the Design System type (never from
another system's link; never record a type or system link in this skill). Cut the tree (sections
2-5), run the checks, write the cover, then the index last. Record the system by name in the brand's
Applications with the version it was cut from.

**Connect** (a system exists; the brand has, or is getting, a definition). Read the live index,
`tokens.json` and README. Map each live token to a role by value and usage, then report one block
with four headed lists:

```
Matched — same role, same value
Changed — same role, different value (live → definition)
Live-only — tokens the definition lacks
Definition-only — roles the system lacks
```

The user decides each difference at the gate. A live-only token worth keeping goes back to `build`
as a definition change; it is never adopted silently. After the gate, write only the changed files,
then the index. A system marked as maintained by a pipeline (its last change came through CI), or
read-only to this surface, is reported, never written.

**Re-sync** (after a definition version bump). Read the live system first; people edit it on the
page. Diff the previous and current definition versions; re-export only the files that diff touched,
`tokens.json` always whole. Keep README prose, usage notes and assets added on the page. List tokens
the definition no longer defines and ask before removing any. Update `meta.definition`. An export
that finds a system whose `meta.definition` is older than the current version runs as a re-sync,
never as a fresh build over it. Write the changed files in one call and the index in the last call:
large systems cost real usage, so nothing unchanged is re-sent.

**A bump re-syncs every system it touches, not only the one in hand.** A change to a shared rule
(type, neutrals, spacing, a house-wide accent) reaches the parent system and every sibling. Before
calling a bump done, read `meta.definition` on every system named in the definition's Applications
and re-sync each one that is older; a recorded run left the parent four versions behind while its
member system was kept current. A refusal because the system has a newer version than the one read
means read again: if the content is unchanged, re-apply the same edit to the fresh read.

## 7. Making it the default, and how other work reads it

- Decks and designs use the design system the user marks as **default** without asking. After a
  build or re-sync, tell the user where to set the default in their design-system settings; never
  change account settings yourself.
- Any agent reads a system by reading its `project/README.md`; brandscribe names this in the
  handback so the user can point other work at it.
- A Claude Code repo can carry `DESIGN.md` and `VOICE.md` too (`repo-files.md`).
- A React component library is the platform's design-sync command's job; say so and stop.

## 8. Dated fallback block

**Last verified: 2026-10-01** (Artifact tool type read; release `1790882176-289c`, contract
`0.2.47`). Facts only, for surfaces with no Artifact tool:

- Files live under `project/`; the index is `project/design-system.json`, written last; a new system's
  index carries a `createdOnFiles` marker and a `lastChange` record.
- `tokens.json` families are lists of `{name, value, usage}`; `color` adds `themes`; names match
  `[A-Za-z0-9][A-Za-z0-9_.-]{0,63}` and are unique across families but `type`.
- Named colours, `var()`, `color-mix()` and aliases of missing tokens drop.
- Non-text files under `assets/<Group>/` are asset uploads recorded in the index; fonts are files
  listed by `type.fonts[].file`.
- Caps: 1,008 files and 256 MiB per system; 15 MiB per file; 16 MiB per call.
- `README.md` is required; every reader starts there. The cover is `components/Cover/preview.html`.
- The type's checklist asks for text at 4.5:1 in every theme (3:1 at 24 px and above, borders,
  focus rings, icons), lightness over hue for colours that must be told apart, and no AI tropes.
