# Franchise canon

Read when several repos or projects share one universe. The problem it solves: a series kept as one repo per book or per game breaks link checks that assume one folder.

## Layout

```
<universe-bible>/            # its own folder or repo; the user's single source
├── bible.md                 # canon_version: "1.4"
├── characters/ places/ factions/ artifacts/ timeline.md names/
└── CANON-LOG.md             # one row per version: what changed level or retired

<project-repo>/
└── <bible>/
    ├── bible.md             # universe: <path or repo>, pin: "1.3"
    └── ...                  # project-local entities only
```

- Universe entities live once, in the universe bible. A project never copies them; it references them by id.
- A project-local entity may promote to the universe through a PROPOSAL against the universe bible, never by copying.
- `CANON-LOG.md` rows: `| version | date | id | change (level, retire, edit) |`.

## Check across repos

1. Read the project's `bible.md` for `universe` and `pin`.
2. Resolve every id first in the project bible, then in the universe bible.
3. For each universe fact the text uses, read `CANON-LOG.md` rows after the pin. A change to that id is `PIN-DRIFT`, with the version that changed it.
4. The universe bible is read-only from a project session unless the user says otherwise (SKILL.md rule 3); proposals against it go back in chat.

## Moving a pin

Raising a project's pin is a canon change for that project: a PROPOSAL listing every `PIN-DRIFT` it clears and any new findings it causes. The user approves it once.
