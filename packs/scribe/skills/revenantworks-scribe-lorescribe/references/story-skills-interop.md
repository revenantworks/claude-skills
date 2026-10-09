# story-skills interop

Read when the bible was made by story-skills (github.com/danjdewhurst/story-skills, MIT). lorescribe reads that layout as input; it never converts or rewrites it without a PROPOSAL and a yes. Layout as read from its README on 2026-10-01; read the bible's own files for the real field names, never assume beyond this list.

## Recognise it

A top-level `story.md` with `schema-version` in its frontmatter, and `_index.md` registries under `characters/`, `worldbuilding/` (with `locations/`, `factions/`, `artifacts/`, `systems/`), `plot/`, `scenes/` and `chapters/`. Entity files are kebab-case ids with two-way links.

## Map

| story-skills | lorescribe |
|---|---|
| `characters/<id>.md` | character entity |
| `worldbuilding/locations/<id>.md` | place entity |
| `worldbuilding/factions/<id>.md` | faction entity |
| `worldbuilding/artifacts/<id>.md` | artifact entity |
| status and death fields | `state` (read as the current state; order from `plot/timeline.md` and scene dates) |
| `plot/timeline.md` | timeline |
| `continuity/state.md` | extra state evidence |
| no canon level | treat as `soft`, and say so once |

## Rules

- Read in place. lorescribe's own fields (`level`, `visual`, `motif`, `pronounce`) are offered as PROPOSAL additions to the existing files, never as a parallel copy.
- Its continuity report is evidence beside lorescribe's checklist. `scripts/manuscript.py evidence <report.json>` reads `story continuity --json` output (fields `code`, `file`, `chapter`, `message`, `severity`, `exemption`, as its docs list them on 2026-10-01) and prints one `STORY-SKILLS · <code> · ...` line per item; name which findings each source raised.
- Its engine is the tool for promises, clocks, routes and prop custody; lorescribe does not rebuild those checks. For a book that never had frontmatter, manuscript mode's `cast` proposes per-chapter `mentions:` so that engine can run (`manuscript-mode.md`).
