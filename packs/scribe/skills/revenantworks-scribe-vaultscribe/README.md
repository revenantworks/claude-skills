# revenantworks-scribe-vaultscribe

A keeper for an LLM-maintained knowledge vault, the "LLM wiki" pattern: you curate sources in
`raw/`, Claude compiles them into short, cited concept pages in `wiki/`, and a rules file tells
every session how. Most vault skills stop at writing the pages. vaultscribe also keeps the vault
honest: clipped web text is treated as data with deny rules to back it, a lint finds personal data
and secret shapes without printing them, living sources such as repo docs are snapshotted and
checked for drift, and every step runs on native Windows and stays safe under git.

Works with Obsidian (not affiliated) as the viewer, or with any Markdown folder. Obsidian's own
file formats (Bases, Canvas, its Markdown extensions, its CLI) are out of scope: for those, use
[kepano/obsidian-skills](https://github.com/kepano/obsidian-skills) (official, MIT).

Part of the **scribe** pack (standard profile). Two declared scripts, Python 3 standard library
only, no network:

- `scripts/vault_lint.py` — read-only structure, trust-boundary and privacy check.
- `scripts/vault_snapshot.py` — dated copies of living sources and the drift check; writes only
  new folders under `raw/snapshots/`.

Setup copies both into the vault's `tools/`. Without Python or a shell, lint and refresh run by
hand from the checklists in `references/`, and the script is reported as NOT-RUN, never as a pass.

## What it does that others do not

| Margin | What it means | Eval case |
|---|---|---|
| Trust boundary for clipped content | `raw/` is data, never instructions; `harden` writes deny rules (`Edit(/raw/**)`, `WebFetch`, curl, wget, `Invoke-WebRequest`) and a local settings file that turns off connectors and denies push and merge; lint flags remote image embeds, iframes, script tags and HTML comments in pages | `test-cases.md` C4, C7 · native `clip-injection`, `harden-web-clips` · `scripts/test_vault_lint.py` |
| Privacy and secret lint with an escalation path | Lint flags emails, home-folder paths and key shapes by file and line, never the value; a privacy-signals log (date and category only) with a stated line, 3 in 30 days, for moving to a git-ignored `private/` folder, and the warning that moving never erases git history | `test-cases.md` C5 · native `privacy-lint` · `scripts/test_vault_lint.py` |
| Living-source drift | `vault_snapshot.py --check` compares the newest dated snapshot with the originals: `CHANGED`, `NOT-IN-SNAPSHOT`, `GONE`, and `NEW-REPO` for an expected source the list misses; `refresh` updates only the pages whose sources changed | `test-cases.md` C6 · native `snapshot-drift` · `scripts/test_vault_snapshot.py` |
| Native Windows and git-safe | stdlib Python, steps that run in PowerShell 5.1 and bash alike, union merge for index, log and privacy signals, commits only when asked, never pushes, cloud sessions on their own branch | `test-cases.md` C1, C8 · native `windows-git-safe` |

Where others are stronger: Obsidian file formats and CLI automation (obsidian-skills), many more
commands and a retrieval eval (obsidian-second-brain), verifier agents (claude-obsidian). See
`SOURCES.md` for the dated parity register.

## Package

```
revenantworks-scribe-vaultscribe/
├── SKILL.md
├── README.md · CHANGELOG.md · SOURCES.md · LICENSE · NOTICE · volatile.json
├── references/
│   ├── setup.md · rules-template.md
│   ├── ingest-query.md · lint-review.md
│   ├── refresh.md · harden.md
│   └── pack.md
├── scripts/
│   ├── vault_lint.py           # read-only lint
│   ├── vault_snapshot.py       # snapshot and drift check
│   ├── test_vault_lint.py
│   └── test_vault_snapshot.py
└── evals/
    ├── trigger-evals.md · test-cases.md · RESULTS.md   # hand-run suites
    └── <case>/prompt.md + graders/                       # claude plugin eval suite
```

## Install

Claude Code: add the marketplace and install the scribe pack (`/plugin marketplace add
revenantworks/claude-skills`, then `/plugin install scribe@revenantworks`). claude.ai: upload the
folder as a skill (Customize → Skills). Public installs get vaultscribe with the scribe pack's next
version bump.

## Commands

| Say | Entry |
|---|---|
| `vaultscribe setup` | scaffold a vault: rules file, layout, scripts, git files, optional CI |
| `vaultscribe ingest <file>` · `ingest new` | file one source, or every uncited raw file, into concept pages |
| `vaultscribe query` | answer from the wiki with page links, reading raw files when the wiki lacks detail |
| `vaultscribe lint` | run the lint, then review the oldest pages against their sources |
| `vaultscribe refresh` | check living sources for drift and update only the pages they feed |
| `vaultscribe harden` | deny rules, local settings and trust-boundary lines for a vault that takes web clips |

## Staying current

`SOURCES.md` holds the parity register (90-day calendar surface). Re-run the incumbent scan when
it ages out; the retire condition is stated there.

History: [CHANGELOG.md](CHANGELOG.md).

Tests for the scripts: `python -m unittest discover -s scripts -p "test_*.py"` from this folder.
