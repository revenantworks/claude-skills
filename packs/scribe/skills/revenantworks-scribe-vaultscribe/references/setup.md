# Setup — scaffold a vault

Read on `setup`. The rules file text is in `rules-template.md`.

## Contents

- Ask first
- Layout
- Files setup writes
- Steps that work in PowerShell and in bash
- Optional CI file
- Obsidian as the viewer
- Hand checklist (no shell)

## Ask first

One batch, before any file is written:

1. **Groups.** The kinds of thing the vault is about (for example `projects`, `tools`, `topics`). Each group gets a folder under `wiki/` and a hub page. Default when the user has no view: one group, `topics`.
2. **Web clips.** Will the vault take clipped web pages or other outside text? Yes means offer `harden` straight after setup.
3. **Living sources.** Are there documents that keep changing after they are filed (repo READMEs, a handbook in a clone)? Yes means a `tools/snapshot-sources.txt` list and the `refresh` entry.
4. **Rules file name.** `CLAUDE.md` for Claude Code; `AGENTS.md` when other agents also work in the vault. One file, never two copies that can drift.
5. **CI.** Only when the vault has a remote and the user wants a hosted check.

## Layout

```
<vault>/
├── CLAUDE.md                 # the rules file (or AGENTS.md)
├── README.md                 # a short guide for the user
├── raw/                      # sources: the user adds, Claude never changes
│   ├── notes/                # the user's own notes (the user may edit them)
│   └── snapshots/<date>/     # living-source copies, written only by tools/vault_snapshot.py
├── wiki/
│   ├── index.md              # every page, one line each
│   ├── log.md                # append-only: ## YYYY-MM-DD ingest|query|lint|refresh | title
│   ├── privacy-signals.md    # one line per turned-away item: date and category only
│   ├── <group>.md            # one hub page per group
│   └── <group>/              # that group's pages
├── tools/
│   ├── vault_lint.py
│   ├── vault_snapshot.py     # only with living sources
│   └── snapshot-sources.txt  # only with living sources
├── .gitignore
└── .gitattributes
```

## Files setup writes

**`.gitattributes`** — union merge keeps both sides' appended lines when two machines or a cloud branch append at once:

```
* text=auto
wiki/log.md merge=union
wiki/index.md merge=union
wiki/privacy-signals.md merge=union
```

Union merge can keep a line twice or out of order; lint and the next ingest tidy `index.md`. It is never set on a page.

**`.gitignore`**:

```
.obsidian/*
!.obsidian/app.json
!.obsidian/graph.json
!.obsidian/bookmarks.json
.claude/settings.local.json
.trash/
private/
__pycache__/
*.pyc
.venv/
.env
*.key
*.pem
```

`private/` is the escalation folder (`lint-review.md`); it is ignored from day one so moving material there is one step.

**Wiki seed files.** `index.md` (a heading and one line per hub), `log.md` (a heading and one `setup` entry dated today), `privacy-signals.md` (a heading only), and one hub page per group at `wiki/` root. A hub holds links and one-line descriptions only, never a claim, so lint does not ask it for sources; a claim belongs on a page in the group's folder. Setup writes nothing into `raw/`.

**Scripts.** Copy `scripts/vault_lint.py` (and `scripts/vault_snapshot.py` with living sources) from this skill into `tools/` byte for byte. Never copy the `test_*.py` files.

**`tools/snapshot-sources.txt`** (living sources only): a comment header, then one `<group>:<path>` per line relative to the folder that holds the sources (`refresh.md`).

## Steps that work in PowerShell and in bash

Write every file with the surface's file tools, not shell redirection: `>` and `echo` write UTF-16 in Windows PowerShell 5.1, and `touch`, `cp -r` and heredocs do not exist there. The commands below run unchanged in PowerShell 5.1, PowerShell 7, bash and zsh (one command per line, no `&&`):

```
git init
python tools/vault_lint.py .
git status --short
```

Use `python` on Windows and `python3` where `python` is absent. A path is written with forward slashes; both shells accept them. Never run a command that needs elevation. The user makes the first commit, or asks for it (rule 6).

## Optional CI file

Only on request, as `.github/workflows/vault-lint.yml`. It runs on pushes to the default branch only, cancels a superseded run and has a time cap; it has no `pull_request` trigger while the repo has no branch protection, and no `paths-ignore`, because the check must see every merge.

```yaml
name: vault-lint
on:
  push:
    branches: [main]
  workflow_dispatch:
permissions:
  contents: read
concurrency:
  group: vault-lint-${{ github.ref }}
  cancel-in-progress: true
jobs:
  lint:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          fetch-depth: 0
          persist-credentials: false
      - uses: actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0 # v7.1.0
        with:
          python-version: "3.12"
      - run: python tools/vault_lint.py .
```

`fetch-depth: 0` gives lint the history its raw change check reads. The two actions are pinned to commit hashes (as read 2026-11-09); bump them through the repo's update tooling, never to a moving tag.

## Obsidian as the viewer

Open the vault folder as a vault in Obsidian. Wikilinks (`[[page]]`) resolve by file name, which is why lint refuses two pages with one name. Bookmark `index.md` and the hubs. Obsidian is optional; every rule holds in any Markdown editor.

## Hand checklist (no shell)

- Every folder in the layout exists; `raw/` holds nothing Claude wrote.
- `.gitattributes` and `.gitignore` hold the lines above.
- `index.md` links every hub; every hub links back to `index.md`.
- Say `vault_lint.py: NOT-RUN (no shell)` in the close.
