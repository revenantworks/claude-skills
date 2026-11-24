# Addon ship — the Godot addon release checks

Read by `landwright ship`. A free Godot 4 addon is checked here before its release commit lands
and before anyone tags it. Every check reads a file; a check that cannot read its file reports
`unread`, never pass. The checks report; the tag, the release and any listing wait for the
owner's go.

## Contents

- What the release carries
- The checks
- A repo's own release kit
- Tag and release — the owner's go
- What stays out of scope

## What the release carries

The release zip carries the addon folder, `addons/<addon>/`, whole: code, `plugin.cfg`, icons,
demo and tests, with its own `LICENSE` and `NOTICE` inside it. A Godot Asset Library or Asset
Store download installs that folder alone, so a licence that sits only at the repo root does not
travel with the addon.

## The checks

| # | Check | Pass when |
|---|---|---|
| A1 | Licence in the folder | `addons/<addon>/LICENSE` exists and matches the repo-root licence (Apache-2.0 for free code); the README names it |
| A2 | NOTICE | `addons/<addon>/NOTICE` exists, names the copyright holder as the brand or organisation (never a personal name) and every third-party item that ships inside the folder |
| A3 | `plugin.cfg` | `name`, `description`, `author`, `version` and `script` are filled; `author` matches the NOTICE holder; `description` is generic; `version` equals the CHANGELOG's top entry |
| A4 | CHANGELOG | an entry for the release version, dated |
| A5 | SUPPORT | `SUPPORT.md` states a support period with an `until YYYY-MM-DD` date not in the past, points to issues or discussions, and promises **no reply time and no fix time** |
| A6 | SECURITY | `SECURITY.md` lists supported versions and a private report channel (the repository's security advisory form), carries **no email address**, and promises no response or fix time |
| A7 | Asset-library metadata | an icon at the path `plugin.cfg` or the listing names; the Godot version the addon targets is stated in the README; the zip's top level is `addons/<addon>/` only |
| A8 | No personal data | no personal name, user-folder path or email address (no-reply ones aside) in any file the zip carries; the repo's PII scan passes on the tree |
| A9 | Proof | the addon's tests or headless build proof pass on the release commit (godotsmith judges a Godot result when installed) |

A5 and A6 promise nothing on purpose: a free addon's maintainer owes no reply, and a written reply
time reads as a promise. Wording that says "best effort" with no number passes; "within 48 hours"
fails.

## A repo's own release kit

When the repo, or a sibling tools repo, ships a release-check command (one that prints PASS and
FAIL rows for licence, support, security, notice and PII), run it read-only on the addon folder
and quote each FAIL row. Its PASS means the files are present, not that their wording is legally
enough; legal review is the owner's call. A kit row that disagrees with a check above is reported
both ways; the kit's own row wins for that repo.

## Tag and release — the owner's go

Each of these waits for the owner's word naming it ("tag it", "draft the release"). With the go:

1. Land the release commit through the normal land (CHANGELOG, `plugin.cfg` version).
2. Read the repo's tag pattern first: `git tag -l`. A repo holding several addons prefixes the
   addon folder name (`<addon>-v<x.y.z>`); a one-addon repo uses `v<x.y.z>`.
3. The merge commit is made on GitHub, so `git fetch --prune` first and check that
   `git cat-file -t <merge-sha>` reads `commit`. Then tag it:
   `git tag -a <tag> -m "<Addon> <x.y.z>" <merge-sha>`, and send that one tag:
   `git push origin <tag>`. Never `--tags`.
4. Draft the release with the zip: `gh release create <tag> <zip> --repo <o>/<r> --draft --title
   "..." --notes-file <file>`. Publishing the draft, an Asset Library submission and any store
   listing are the owner's own steps; hand each over as one command or one link.

`[skip ci]` never goes on a release tag.

## What stays out of scope

Paid products, EULAs and store payouts follow the repo's own release kit and the owner. Release
notes and store-page text are commscribe's. Whether a Godot test result is real is godotsmith's.
