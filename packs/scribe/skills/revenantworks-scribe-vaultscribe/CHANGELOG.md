# Changelog — revenantworks-scribe-vaultscribe

All notable changes to this skill. Format: Keep a Changelog; versions follow SemVer.

## [1.0.0] — 2026-11-09

First release. Sets up, runs and keeps honest an LLM-maintained knowledge vault (the LLM wiki
pattern: `raw/` sources, a compiled `wiki/` of cited concept pages, a rules file), with Obsidian or
any Markdown editor as the viewer. Fifth member of the scribe pack. Public installs receive it with
the scribe pack's next version bump.

### Entries

- `setup` — scaffolds the vault: a rules file from a template, the layout, both scripts in
  `tools/`, `.gitignore`, `.gitattributes` with union merge for the index, log and privacy
  signals, and an optional CI file (push on main only, cancel in progress, a time cap, pinned
  actions).
- `ingest` — one source, or `ingest new` for every uncited non-empty raw file; concept pages,
  never one page per source; both claims kept on a conflict; asks when the group is unclear.
- `query` — index first, answers with page links, reads raw files when the wiki lacks detail,
  offers to file the answer.
- `lint` — runs the script, then reviews the oldest pages against their sources.
- `refresh` — snapshots living sources and updates only the pages whose sources changed.
- `harden` — deny rules, a local settings file and trust-boundary lines for a vault that takes
  web clips.

### Differentiators

- Trust boundary for clipped content: raw text is data, never instructions; deny rules for raw
  edits and fetch tools; lint flags remote image embeds, iframes, script tags and HTML comments.
- Privacy and secret lint by file and line, never the value, with a privacy-signals log and a
  stated escalation line (3 in 30 days) to a git-ignored private folder.
- Living-source drift: `CHANGED`, `NOT-IN-SNAPSHOT`, `GONE` and `NEW-REPO`.
- Native Windows and git-safe: stdlib Python, PowerShell-safe steps, commits only when asked,
  never pushes.

### Scripts

- `scripts/vault_lint.py` (read-only) and `scripts/vault_snapshot.py` (writes only new dated
  folders under `raw/snapshots/`), Python 3 standard library, no network, with
  `scripts/test_vault_lint.py` and `scripts/test_vault_snapshot.py`. Without a shell both report
  NOT-RUN and the entry runs its hand checklist.

Released under the Apache License 2.0.
