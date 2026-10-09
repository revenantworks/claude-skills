# claude-skills - Runbook

*Pairs with `tools/build.py`, `tools/release.py`, and `.github/workflows/pack-ci.yml`. The loop:*
**edit -> `python tools/build.py` -> commit -> tag `<pack>-vX.Y.Z` -> push -> CI attaches all member zips.**

**One command runs the whole close-of-pass loop (added 2026-08-17):**
`python tools/release.py foundation=X.Y.Z -m "<message>"` —
bump-pack, changelog gate, build, `--check`, tests, commit, tag, push with
tags, then the list of member zips that changed and the exact claude.ai
upload list. Add `--swaps <dir>` to also build install zips carrying your own
`LICENSE` or namespace token (see below), `--export-dir <dir>` to copy every zip
plus a README.txt there, `--dry-run` to see the plan. Steps 1 to 5 below
describe what it does by hand.

**Pack-shared files** live in `packs/<pack>/shared/` with `holders.json`;
`tools/build.py` writes each holder's copy and `--check` fails on drift (owner
Q2, 2026-10-01). Edit the shared source, never a copy.

**Pack eval folders** `packs/<pack>/pack-evals/<short>--<case>/` are tracked copies of
each member's native cases, written by `tools/build.py` (`claude plugin eval`
refuses an eval dir inside `skills/`); `--check` fails on drift or a stale folder,
and `results/` is gitignored. Edit the member case, never a copy.

**Footprint counter.** `python tools/build.py --footprint` (writes nothing)
counts the SKILL.md body plus every file every entry reads on every run (bullet,
prose, every-mode line, or a file in every row of an entry table); `--check`
warns past the member's budget row too (P1e2, 2026-10-01).

## Local install by junction (optional, for contributors)

**Edit in the clone; it is live next session.** A local install can load
members by user-scope junction or symlink from a clone —
`~/.claude/skills/<member>` -> `packs/<pack>/skills/<member>/` in the
working tree (PowerShell `New-Item -ItemType Junction`, or `ln -s`). Such an
install does not need the marketplace plugin, and `claude plugin update` is
not part of its loop. The marketplace registration is how the public
installs. `python tools/build.py --parity` is for CI and plugin installs (it
skips cleanly with no plugin installed). Verify the links with
`ls -la ~/.claude/skills`; a missing one is recreated the same way, never by
re-installing the plugin.

## PII barrier (every clone, every worktree)

`.githooks/pre-commit` runs `python tools/pii_scan.py --staged` on the staged
diff and blocks the commit on any hit. Arm it once per clone:

    git config core.hooksPath .githooks

`core.hooksPath` lives in the clone's shared config, so every `git worktree`
of that clone runs the same hook. The `pii-scan` job in
`.github/workflows/pii-scan.yml` runs `python tools/pii_scan.py --tree` on
every push to `main`. Generic rules always run: email addresses (no-reply
addresses pass), user and home folder paths, drive-letter paths outside the
system folders, and secret shapes. A private names list (the same one
`tools/name_leak.py` reads, below) adds the name rule when it exists on your
machine; it is never committed. Hits print `path:line rule fingerprint`,
never the value. Never bypass the hook with `--no-verify`: fix the file.

**Post-commit hook.** `.claude/settings.json` wires a PostToolUse hook on
`git commit` (`.claude/hooks/bump-check.py`) that runs `build.py --check`
and surfaces `pack bump needed: <pack>` when shipped files differ from the
pack's current tag while its version has not moved. Advisory, never
blocking; no `ask` rules anywhere in this repo.

## Release a pack version
1. Make the change (member content, registry row, roster). On any member
   version bump, re-anchor its eval provenance lines in the same commit
   (skillwright `eval-refresh.md`, Provenance discipline; the build gate warns on drift).
   **Any change to a member's shipped files — evals and fixtures included —
   bumps that member's version in the same commit.** The claude.ai re-upload
   step is keyed on the member zip's version, so an unbumped change is
   invisible to the lazy-upload rule and never ships there: three members
   went out that way in foundation-v2.2.3 (eval changes at unchanged
   versions, two of them in members since retired), and for one the stranded
   change was the personal-name scrub itself.
2. `python tools/build.py --bump-pack <pack> <X.Y.Z>`: writes the
   marketplace entry + pack plugin.json + root CHANGELOG scaffold in one
   stroke (never hand-edit the two version fields separately: the
   1.0.0/1.1.0 split-brain shipped for a month that way).
3. `python tools/build.py`: regenerates every `references/pack.md` from the
   registry, validates all members (name/folder match, description <=1024
   chars, `compatibility` <=500 chars — the only field limit confirmed
   against a real upload error, and the reason `description` carries no
   second one, body <=500 lines, CHANGELOG head == frontmatter version,
   plugin.json == marketplace version, eval provenance freshness + table
   integrity, string-only `metadata`, and each `volatile.json`: legal classes, files
   exist, calendar surfaces stamped `Last verified:` with a sane cadence),
   builds `dist/` zips. `--check` = CI mode, writes nothing.
4. Commit, tag `<pack>-vX.Y.Z`, push branch + tag. Confirm CI attached the
   member zips to the Release. README points installers at Releases, so a
   tag whose assets lag main ships stale skills. Two closes on this step:
   - **Fetch the tag back**: `git fetch --tags origin`. A release cut with
     `gh release create` tags server-side and the clone never learns it, so
     any local "newest tagged version" check answers one release stale
     (ossuary-v2.2.4 sat on the remote and not in the clone for two days).
   - **Before the next bump lands, assert the current one has a tag**:
     `git tag -l "<pack>-v$(python -c "import json;print(json.load(open('packs/<pack>/.claude-plugin/plugin.json'))['version'])")"`
     must print. ossuary 2.2.2 reached main and was superseded 4.5 minutes
     later; the tag namespace still skips it (recorded in `CHANGELOG.md`).
     Either tag it or record the skip — silence is the failure.
5. **Sync your own install.** A junction install (above) has nothing to
   sync. A plugin install runs `claude plugin marketplace update revenantworks`,
   then `claude plugin update <pack>@revenantworks`, then `--parity`: the
   plugin cache is what Claude Code loads and the pack version is its key, so
   a member-only bump never reaches it. Then re-upload changed members on
   claude.ai below.

## Install / update on claude.ai
Per skill: download the member zip from Releases -> Customize -> Skills -> + ->
Create skill -> upload. `python tools/release.py` prints, at the end of every
release, which member zips changed; every upload is an optional convenience
copy (an install zip from `apply-install-swaps.py`, see below, is listed in
place of the plain one when you built it). Every SKILL.md frontmatter carries only the six keys the
upload form accepts (name, description, license, compatibility, metadata,
allowed-tools — `build.py --check` does not enforce this; the 2026-08-14
upload failure was on `compatibility` length, which it does). Every release
carries the full foundation member set frozen at that moment (10 members).
Releases stay immutable — this is a reading
rule, not an asset to go back and fix. Updating is delete-then-re-upload — the unavoidable
manual step **on personal accounts**. Team/Enterprise accounts have had
org-wide admin provisioning since Dec 2025 (as of 2026-08-01; Organization
settings -> Skills, zip upload, enabled by default with per-user opt-out).
One central upload replaces the per-user x8.

**No skill applies a brand (decision 36, 2026-10-01).** The repo and every
install ship neutral; the brand member and its definition swap retired that day.
`apply-install-swaps.py` overlays your private files onto neutral repo copies
of every member in every pack and emits install-ready zips; upload those, and
plain `dist/` zips for anything you did not override.

| Put in your swaps dir | Overlays | Effect |
|---|---|---|
| `LICENSE` | every member's `LICENSE` | your copyright holder |
| `brand-token.txt` | every member's `metadata.brand:` | your namespace token (one line) |

Both are optional and independent. Omit one and its neutral value ships.
Every override is printed per member as it is applied — a build that silently
rewrote your copyright would be worse than one that refused to. A
`brand-definition.md` or `prompt-card.md` left in the dir is ignored with a note.

```bash
python3 tools/apply-install-swaps.py <your-private-dir>
```

> History: 1.0.x had three swap surfaces; the 2026-07-23 law retired the
> prompt-card swap; 2026-08-07 extended `LICENSE` and the token to every
> member; 2026-10-01 retired the definition swap with the brand member.

## Install / update in Claude Code
Public consumers: `/plugin marketplace add revenantworks/claude-skills` once,
then `/plugin install <pack>@revenantworks`. No zips, no swaps: installs from
the repo; config lives in your local `~/.claude` copy. Updating: `claude plugin
marketplace update revenantworks`, then `claude plugin update
foundation@revenantworks` (both, in that order — the pack version is the
cache key). A junction install does none of this (above).
Migrating from the pre-2.0.0 `revenant` marketplace name: remove the old
marketplace locally first, then add + install under the new name.

## Add a member or a pack
New member: build it, add its registry row (registry members table), run
`python tools/build.py`, upload per policy. New pack: add the pack row +
`**<pack> members**` table to the registry, create `packs/<pack>/` with its
`.claude-plugin/plugin.json`, add the marketplace catalog entry, run the build.

A pack needs **four** registry surfaces, not one — `**<pack> members**`,
`**<pack> budgets**` (one row per member, honest ceiling + stated reason; the
build hard-fails on undeclared overage), `**<pack> seams**` (one row per
boundary pair, or `--check` warns that every edge is unrecorded), and a
`Conformance checks (YYYY-MM-DD): ...` clause **in the pack row's own Notes
cell**. That last one is not optional decoration: the generated `pack.md`
prints a conformance line for every pack, so a pack without its own clause
gets the stated default. Before 2026-08-07 it silently got the *first* pack's
line instead — see `ossuary-v1.0.0` in `CHANGELOG.md`. Optional but expected:
`**<pack> capstone:**`, `**<pack> canonical repo:**`, a `**<pack> seam notes:**`
block, and a pack router at `packs/<pack>/CLAUDE.md`.

If a pack's members must also exist somewhere else — a repo whose runner clones
only itself — the outside copy is a **declared downstream mirror**, never a
second source of truth: keep it byte-identical, name this repo (`revenantworks/claude-skills`) as canonical in a
header note at the mirror, and record it in that repo's file map.

## Name-leak check (before every push)

`tools/name_leak.py` fails when a tracked file holds a banned name. It runs
**locally, before every push**; CI does not run it, because the list never leaves
your machine: no repository secret, no upload, nothing in the repo.

The list is the warden pack's private names list, one term per line (`sub:` prefix
for a substring match, `#` for a comment), found in this order: `--list <path>`,
the `WARDEN_NAMES_FILE` variable, then `~/.warden/wordlist.txt`
(`%USERPROFILE%\.warden\wordlist.txt` on Windows). The same file feeds
shieldwarden's owner-name rule. First time, create the folder and a comment-only
template, then fill it in your own editor:

    python packs/warden/shared/scripts/warden_private.py setup names

Before a push:

    python tools/name_leak.py

Exit 0 clean; 1 a hit (`path:line: list entry #n`, never the name or its length): fix the
file, commit, run it again, then push; 2 a refused list (a named file missing, or
one inside a git work tree); 3 NOT-RUN (no list, or no terms): run the setup
command. A NOT-RUN is not a pass.

## Before a release tag

1. Validate the commit history: every subject on `main` follows the commit rule in CLAUDE.md
   (`git log --format=%s`).
2. `python tools/build.py --check`, the tools suite, `python tools/pii_scan.py --tree`, the
   name-leak check and a shieldwarden `scan . --history --identities --pii-only` all clean.
3. Push the tag (it publishes the Release).

## Policies
Restamp per pack (registry Notes; default lazy): rebuild/upload only changed
members + the registry carrier. Release bar: discoverability pass, no open
P0/P1, repo/release/account parity, current capstone card.
