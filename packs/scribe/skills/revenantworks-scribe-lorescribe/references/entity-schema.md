# Entity schema

Read in `bible`, `timeline` (state section) and `audit` modes. One Markdown file per entity, YAML frontmatter on top, prose notes below. The layout reads a story-skills bible as-is (`story-skills-interop.md`); the fields marked *(lorescribe)* are additions that tool ignores.

## Contents

- Folder layout
- Common fields
- Per-kind fields
- State progressions
- Visual tags and motif line
- Index files
- Worked example (invented world)

## Folder layout

```
<bible>/
├── bible.md                # name, canon version, universe pin, branches (canon-levels.md)
├── characters/_index.md    # one registry per kind
├── places/_index.md
├── factions/_index.md
├── artifacts/_index.md
├── timeline.md             # dated events, one row each
├── names/<culture>.md      # naming rules and pronunciation key (names-method.md)
└── generated/              # optional: log.md, drafts, charts, manuscript/ ledger; never canon
```

File names are kebab-case ids (`ila-varn.md`). The id never changes; a renamed entity keeps its id and lists the old name under `aliases`.

## Common fields

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | kebab-case, equals the file name |
| `kind` | yes | `character`, `place`, `faction`, `artifact` |
| `name` | yes | display name, as canon spells it |
| `aliases` | no | other spellings or titles that are canon, never typos |
| `level` | yes | `hard`, `soft`, `rumour`, `retired` (`canon-levels.md`) |
| `links` | no | ids of related entities; each link exists in both files |
| `pronounce` | when voiced | key from the culture's naming file, e.g. `KAY-len` |
| `source` | yes | where the fact was set: file and line, or "owner, <date>"; a single fact may carry its own (`canon-levels.md`) |

## Per-kind fields

- **character:** `born`, `culture`, `faction`, `state` (list, below).
- **place:** `region`, `parent` (id of the containing place), `state`.
- **faction:** `leader` (id), `seat` (place id), `stance` (list of `<faction id>: ally|rival|war|neutral`, quoted), `state`.
- **artifact:** `holder` (id), `state`.

## State progressions

`state` is an ordered list of changes, each tied to a timeline row:

```yaml
state:
  - {at: "T-0412", value: alive}
  - {at: "T-0587", value: dead, cause: "drowned at the weir"}
```

A later scene or event that has the entity act in a way its current state forbids is `STATE-AFTER-DEATH` (for dead or destroyed) or `TIME-PARADOX` (for any other order break). Memories, flashbacks, ghosts and letters are not acts; the text has to frame them so, or the check reports and asks.

## Visual tags and motif line *(lorescribe)*

Plain data for any art or audio tool; no consumer is assumed.

```yaml
visual: [rust-red banners, round shields, salt-white stone]
motif: "low reed pipes, slow three-beat pulse"
```

`check` on an art or audio brief compares the brief's claims with these fields and reports `CANON-CONTRA` on a clash (a brief giving the faction blue banners).

## Index files

Each `_index.md` holds one table: `| id | name | level | one-line summary |`. `audit` compares it with the files in the folder: a row with no file and a file with no row are both `INDEX-DRIFT`.

## Worked example (invented world)

```yaml
---
id: ila-varn
kind: character
name: Ila Varn
aliases: ["the Weir Captain"]
level: hard
culture: reedfolk
faction: salt-guild
links: [salt-guild, the-weir]
pronounce: "EE-lah VARN"
state:
  - {at: "T-0412", value: alive}
  - {at: "T-0587", value: dead, cause: "drowned at the weir"}
source: "owner, 2026-01-10"
---
Captain of the guild barge. Her death at the weir starts book two.
```
