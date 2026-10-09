# Canon levels

Read in `bible` and `check` modes. Every entity, and any single fact that differs from its entity's level, carries one level.

| Level | Meaning | A clash with new text is |
|---|---|---|
| `hard` | Published or owner-fixed. Text must agree. | `CANON-CONTRA`; any write that would break it is stopped |
| `soft` | Working canon. Expected to hold, may still change. | `CANON-CONTRA`, flagged as soft; the user may move canon instead of the text |
| `rumour` | In-world belief, unreliable narrator, or an open question. | Not a contradiction; reported only if text states it as fact (`LEVEL-CONFLICT`) |
| `retired` | Was canon, no longer is. Kept for history. | `LEVEL-CONFLICT` when new text relies on it |

Rules:

- A fact-level marker overrides its entity's level: `level: hard` on the file, `born: {value: "T-0390", level: soft}` on one field.
- Unstated level defaults to `soft`, and `bible` mode says which entries took the default.
- Retiring is a level change, never a delete. The file stays, with `level: retired` and a `retired_at` note naming the canon version.
- Raising a level (`soft` → `hard`) is a canon change: it goes through a PROPOSAL like any other.
- When two `hard` entries contradict each other, report both as `CANON-CONTRA` and stop; lorescribe never picks the winner.
- A fact can carry its provenance: `eyes: {value: grey, source: "chapters/ch01.md:3", level: soft}`. Manuscript mode writes every extracted fact this way.

## Branches

Interactive fiction and games have story paths. A fact true only on one path carries `branch: <id>`; a fact with no `branch` is trunk and holds on every path.

- `bible.md` lists the branches: `branches: [{id: sided-guild, at: "T-0600", excludes: [sided-crown]}, {id: sided-crown, at: "T-0600", excludes: [sided-guild]}]`. `at` is the timeline row of the choice; `excludes` names the paths that cannot both happen. An optional `rejoins: "T-0700"` marks where paths merge again.
- Field form: `ruler: [{value: ila-varn, branch: sided-guild}, {value: toller-ash, branch: sided-crown}]`. State entries and timeline rows take the same `branch:` key.
- Text declares its path in frontmatter (`branch: sided-guild`) or the user names it. Text with no path is trunk.
- `check` builds the canon slice per path: trunk facts plus the facts of the branches on that path. Two values on mutually excluded branches are not a contradiction. Two values on one path are `CANON-CONTRA`.
- `BRANCH-LEAK`: text on one path states or relies on a fact that holds only on an excluded branch, or trunk text relies on a branch-only fact as if it held everywhere. A fact used after a `rejoins` row must hold on every incoming path or be stated per branch.
- `STATE-AFTER-DEATH` and `TIME-PARADOX` run per path: a character dead only on `sided-crown` may act in `sided-guild` text.
- Adding, renaming or retiring a branch is a canon change: it goes through a PROPOSAL.
