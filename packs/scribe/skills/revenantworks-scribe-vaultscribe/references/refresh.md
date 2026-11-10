# Refresh living sources

Read on `refresh`. A living source keeps changing after it is filed: a repo's README, a runbook,
a handbook kept in a clone. The vault never cites the live file. It cites a dated copy under
`raw/snapshots/<date>/`, and `vault_snapshot.py` tells when that copy has gone stale.

## Contents

- The source list
- Check
- Refresh
- Adding a source
- Hand checklist (no shell)

## The source list

`tools/snapshot-sources.txt`, one `<group>:<path>` per line, `#` for a comment:

```
# Living sources that tools/vault_snapshot.py copies into raw/snapshots/<date>/.
# <group> is a folder under the sources root (a repo clone); <path> is relative to it.
team/handbook:README.md
team/handbook:docs/onboarding.md
team/tools:README.md
```

A line that is absolute, holds a drive letter or a second colon, or climbs out with `..` is refused, and nothing is copied (exit 2). The list names only documents the user trusts and owns; a public web page is a clip, not a living source.

## Check

```
python tools/vault_snapshot.py --check --root <sources root>
python tools/vault_snapshot.py --check --root <sources root> --expect team/handbook,team/tools,team/site
```

`--root` is the folder holding every group (`~` is accepted in both shells). It writes nothing and compares the newest snapshot with the originals, line endings set aside:

| Line | Means | Next |
|---|---|---|
| `CHANGED: <line>` | The original differs from its snapshot | Refresh, then update the pages that cite it |
| `NOT-IN-SNAPSHOT: <line>` | Listed after the newest snapshot was taken | Refresh; no page cites it yet, so offer an ingest |
| `GONE: <line>` | The original no longer exists | Tell the user; pages keep citing the old snapshot until the user decides |
| `NEW-REPO: <group>` | A group named in `--expect` that no line covers | Offer to add its main doc to the list |
| `snapshot <date>: N stale` | The summary | — |

Exit 0 fresh, 1 stale, 2 usage error, 3 NOT-RUN (no snapshot yet).

## Refresh

1. **Check** (above) and show its lines.
2. **Snapshot**: `python tools/vault_snapshot.py --root <sources root>`. It writes `raw/snapshots/<today>/…` byte for byte and refuses when today's folder exists; an older snapshot is never touched. `--dry-run` lists what it would copy.
3. **Find the affected pages**: every page whose `sources:` cites the previous snapshot of a `CHANGED` line. Pages that cite only unchanged sources are not touched, not re-read and not re-dated.
4. **Plan**: per affected page, the claims that changed (old text, new text, from the two snapshot copies) and the source line repointed at the new snapshot. A newer copy of the same source is an update, not a second source disagreeing, so the claim is updated in place and the plan shows old and new text; when the user wants the history on the page, the old line stays marked `superseded` with its snapshot date. A claim that another source still supports keeps both, per `ingest-query.md` (Conflicts).
5. **Execute on the user's yes**, then one log entry: `## YYYY-MM-DD refresh | snapshot <date>`, one line per page updated.
6. **Lint**, and report the count.

Older snapshot folders stay as they are: they are evidence for the pages that cited them. Pruning one is the user's call and needs every page moved off it first.

## Adding a source

A new living source is one list line, then a refresh (its line shows `NOT-IN-SNAPSHOT` until then), then an ingest of the new snapshot copy.

## Hand checklist (no shell)

Say `vault_snapshot.py: NOT-RUN (no shell)`. With file tools only: for each list line, read the original and the newest snapshot copy and compare them; report `CHANGED`, `GONE` or `NOT-IN-SNAPSHOT` the same way, labelled a hand check. Without a shell no snapshot is taken: the user copies the files into a new dated folder, or the refresh waits.
