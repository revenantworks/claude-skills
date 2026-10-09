# Rewrite recipes

Loaded for `plan`, `rewrite`, `land` and `after`. Flags that move between releases live in
`tool-surface.md`; check it first. Every recipe works on a **fresh clone in a scratch folder
outside every repo**, never on the working checkout. `<outside>` below is such a folder.

**These steps bind any rewrite, not only this skill's.** A sweep once wrote its own rewrite script:
filter-repo ran in a TEMP mirror, the commit map stayed there for cleanup to delete, and no record
was re-pointed, so the next session found every run record citing ids that no longer existed
(observation 0336). Whoever writes the script copies the map in the same command as the rewrite and
ends with `after`. If someone else's script already ran, rescue `.git/filter-repo/commit-map` from
its clone before anything cleans it up.

**Commands for the user.** The auto-mode classifier refuses a history rewrite (`filter-branch`,
`filter-repo`) as destructive, so the user runs it. Hand it over as a plain-shell line without a `!`
prefix: a pasted `!` stops a PowerShell window with an error (observation 0360). Give the `!` form
as well only when the user runs it inside the Claude prompt.

## Before anything: secrets

A rewrite removes a secret from the history you control. It does not remove it from any
clone, fork, cache or log that already has it. The user rotates or revokes the secret
first. The plan states this even when no secret was found, so the reader knows it was
checked. How to rotate (where the credential lives, the user's issue and revoke steps, the
swap) is keywarden's runbook; shieldwarden names it and keeps the rotation-first rule.

## Plan: measure and pick the mode

1. `python scripts/shield_scan.py scan <repo> --history --identities --json` (the names
   list resolves from the private folder; confirm `owner-name` is not NOT-RUN). Record counts
   by rule, never values.
2. For each flagged commit, `git -C <repo> branch -r --contains <commit>`.
   - Every list empty: **local mode**. The leak never left the machine.
   - Any list non-empty: **published mode**.
3. Name the branches and tags the rewrite touches. A leak on a branch nobody pushed is a
   local-mode rewrite even when other branches are published.

## Gate 1: the backup bundle

    git -C <repo> bundle create <outside>/pre-rewrite.bundle --all
    git -C <repo> bundle verify <outside>/pre-rewrite.bundle

The bundle is the undo. Keep it until `after` closes, then the user decides.

## Emit the inputs

    python scripts/shield_scan.py emit <repo> --out <outside>/filters \
      --mailmap-to "Name <no-reply address>"

Writes `replace-text.txt`, `replace-message.txt` and, with `--mailmap-to`, `mailmap.txt`.
Account segments become `<user>` (or `user` in slugs and home folders), names become the
names list's replacement (default "the user"), emails and secrets become `***REMOVED***`.
The script prints paths and counts only. Read the files only if a line must be judged, and
never paste them anywhere.

## Gate 2: rewrite a fresh clone

    git clone --no-local <repo> <outside>/clone

**Local mode** (start at the last pushed commit, so published history is untouched):

    git -C <outside>/clone filter-repo --refs <upstream>..<branch> \
      --replace-text <outside>/filters/replace-text.txt \
      --replace-message <outside>/filters/replace-message.txt \
      --mailmap <outside>/filters/mailmap.txt

**Published mode** (every ref that carries the leak):

    git -C <outside>/clone filter-repo \
      --replace-text <outside>/filters/replace-text.txt \
      --replace-message <outside>/filters/replace-message.txt \
      --mailmap <outside>/filters/mailmap.txt

Add `--sensitive-data-removal` when the installed filter-repo supports it (see
`tool-surface.md`); it reports the first changed commits and what the host must purge. To
drop a whole file instead of editing lines: `--invert-paths --path <file>`.

**Keep the commit map.** filter-repo writes `<outside>/clone/.git/filter-repo/commit-map`
(one `old new` pair per line). Copy it beside the bundle in the same command as the rewrite, so no
script that copies the rewrite line can drop the copy:

    git -C <outside>/clone filter-repo <the flags above> && cp <outside>/clone/.git/filter-repo/commit-map <outside>/commit-map.txt    (PowerShell: Copy-Item)

`git filter-branch` writes no map; pair `git rev-list` of the old and new branch in order instead,
and check the pair count against the commit count before trusting it.

Old ids cited in tracked records (ledgers, handoffs, changelogs, run records, issue text in a
repo) stop resolving after the rewrite. The map is how they are found and fixed in `after`.

## Gate 3: verify

    python scripts/shield_scan.py verify <outside>/clone \
      --bundle <outside>/pre-rewrite.bundle

Exit 0 or stop. Then run the repo's own build and tests in the clone, and compare commit
counts per branch against the plan. A count that moved without a reason is a stop.

## Gate 4: the user's go

Show: mode, branches and tags touched, counts by rule before and after, the build and test
result, and what the host keeps after the push (pull-request refs, cached commit views,
forks). Then the command block below. Wait for an explicit go.

## Land

The skill never pushes.

**Local mode.** Bring the rewritten commits back to the working checkout (for example
`git -C <repo> fetch <outside>/clone <branch>` and a fast-forward reset of the unpushed
branch after the user's go), then the ordinary push goes through the repo's normal gated
path.

**Paths that must stay on disk.** A rewrite that drops paths from history (`--invert-paths`, or
`filter-branch --index-filter 'git rm --cached ...'`) also removes them from the working tree when
the checkout moves to the rewritten HEAD. Never tell the user "they stay on disk, now ignored": 3123
logs vanished that way (observation 0360). End the land with the restore and the count, from the
pre-rewrite ref (`refs/original/...` after filter-branch, or the bundle):

    python scripts/rewrite_tools.py restore --ref <pre-rewrite ref> --repo <repo> <path> ... --apply

It prints `expected N = present N`; any other count is a stop.

**Size before a batch push.** Before pushing many commits at once, measure the new blobs, so a host's
per-file limit (100 MB on GitHub) stops the push here and not at the host:

    python scripts/rewrite_tools.py push-size --repo <repo> [--range <upstream>..<branch>] [--limit-mb 100]

It lists the five largest new blobs and the total, and exits 1 when one is over the limit.

**Published mode.** Hand the user one block, branches and tags by name, never `--mirror`:

    cd <outside>/clone
    git remote add origin <remote-url>
    git push --force-with-lease origin <branch-1> <branch-2>
    git push --force-with-lease origin <tag-1> <tag-2>

## After

1. Re-clone every copy of the repo: the rig checkout, worktrees, other machines, cloud
   routine clones. An old clone pushes the leak straight back.
2. Owner steps at the host: ask support to purge cached views and pull-request refs that
   still reference old commits; review forks; turn on the email-privacy setting that keeps
   a private address out of web commits; confirm push protection is on.
3. Confirm the rotated secret is dead.
4. **Re-point cited ids (a gated step).** List the records that cite a rewritten id, in every
   repo and run folder the user names (run records and briefs live outside the rewritten repo too):

       python scripts/rewrite_tools.py repoint --map <outside>/commit-map.txt <dir> [<dir> ...]

   It counts the old ids per file, full and the 7-character short form, and lists a cited id with
   no map row (a commit the rewrite dropped) and a short id two old commits share; those are fixed
   by hand, never guessed. With the user's yes, add `--apply`: it rewrites bytes, so each file
   keeps its own line endings, checks replaced = found, searches again and exits 1 unless none is
   left. Commit the edits as one ordinary commit per repo through its normal gated path. The map
   file itself sits outside every repo.
5. Delete `<outside>/filters` once the user confirms the rewrite landed. Keep the bundle and
   the commit map until the user says otherwise.
6. Record counts only: rules, commits rewritten, refs pushed, cited ids re-pointed. No values,
   no fingerprints of names in a tracked file.
