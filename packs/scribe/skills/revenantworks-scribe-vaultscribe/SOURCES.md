# Sources

Last verified: 2026-11-09

Where vaultscribe's guidance comes from, and its parity register. The register is a calendar
surface (90 days): re-run the incumbent scan when it ages out.

## Guidance

| Area | Claim | Source | Checked |
|---|---|---|---|
| Method | `raw/` sources, a compiled wiki the model keeps, a rules file; ingest, query and lint as the three operations | Andrej Karpathy, "LLM wiki" gist (the method source; ideas only) | 2026-11-09 (as summarised in the build brief) |
| Scripts and rules file | Lint checks (links, sources, index, orphans, raw changes, active HTML, emails, home paths, secret shapes, privacy signals) and the snapshot `--check` codes | A maintainer's working private vault, its `lint.py`, `snapshot.py` and rules file, generalised here: paths as arguments, no personal names or paths, hubs exempt from sources, codes per line | 2026-11-09 |
| Permission rules | `/path` is project-relative; file path checks use `Edit(…)` (a `Write(…)` path rule is never consulted); an Edit deny covers named-file shell writes and redirections, not a script that opens the file itself; a bare `WebFetch` deny removes the tool | gatewarden `references/rule-grammar.md` (this repo; verified there 2026-10-01 against code.claude.com/docs/en/permissions) | 2026-11-09 |
| No `ask` in tracked settings | A committed `ask` rule stalls an unattended or cloud run | This repo's `CLAUDE.md`, Hard rules | 2026-11-09 |
| Local settings | `disableClaudeAiConnectors` and an `mcp__*` deny in a git-ignored `settings.local.json` | The working vault's local settings (as read); flagged in `harden.md` to confirm against the settings page | 2026-11-09 |
| PowerShell aliases | `curl` and `wget` are aliases of `Invoke-WebRequest` in Windows PowerShell 5.1; `iwr` and `irm` are aliases in every edition | Microsoft PowerShell documentation, about_Aliases and the 5.1 alias list | 2026-11-09 |
| CI file | Push on the default branch only, `concurrency` with cancel-in-progress, `timeout-minutes`, no `pull_request` trigger while there is no branch protection; actions pinned to commit hashes | skillwright `references/build-templates.md` (CI template) and the working vault's CI file; hashes as pinned in this repo's `.github/workflows/pack-ci.yml` | 2026-11-09 |
| Union merge | `merge=union` keeps both sides' lines for append-only files; it can duplicate or reorder lines | git documentation, gitattributes ("union") | 2026-11-09 |
| Native evals | Case folders with `prompt.md`, optional `case.yaml` with a scaffold script, `graders/*.md` (`regex`, `tool_used`, `llm`); two-arm baseline | code.claude.com/docs/en/plugin-evals (via lorescribe's SOURCES.md) and this repo's `tools/build.py` grader check | 2026-11-09 |
| Grader design | A write or fetch detector matches the target command; phrase graders accept synonyms or are judged | Observation 0581, carried into skillwright's eval guidance (`references/eval-audit.md`, staged) | 2026-11-09 |

## Parity register

Scan date: 2026-11-09. The incumbent facts below come from the dispatch brief's scan (dated
2026-11-10 there; this file cannot carry a future stamp), at README level. This build did not
re-read the repositories; the next refresh re-reads each one.

### Incumbents

| Incumbent | Kind | Licence | Scope | Checked |
|---|---|---|---|---|
| [kepano/obsidian-skills](https://github.com/kepano/obsidian-skills) | Official Obsidian skills, about 51k stars | MIT | Obsidian file formats (Markdown extensions, Bases, Canvas) and the CLI; no wiki upkeep | 2026-11-09 (brief) |
| [AgriciDaniel/claude-obsidian](https://github.com/AgriciDaniel/claude-obsidian) | Full LLM wiki plugin, about 16k stars | MIT | Ingest, query, lint and verifier agents; no injection posture; native Windows writes need WSL | 2026-11-09 (brief) |
| [eugeniughelbur/obsidian-second-brain](https://github.com/eugeniughelbur/obsidian-second-brain) | Second-brain plugin, about 5k stars | MIT | 49 commands, a freshness lint, a retrieval eval, CI; no privacy or secret scan, no clipped-content defence | 2026-11-09 (brief) |
| [chobizzy/llm-wiki](https://github.com/chobizzy/llm-wiki) | LLM wiki skill | MIT | Lint and a hash manifest that skips unchanged files on re-ingest | 2026-11-09 (brief) |
| alirezarezvani llm-wiki skill | LLM wiki skill in a large skills collection | not checked | The ingest, query, lint loop | 2026-11-09 (brief) |

### Parity table

| Capability | Mark | Note |
|---|---|---|
| Ingest sources into cited concept pages | met | Concept pages, update before create, both claims kept on conflict |
| Query with page citations, file the answer | met | Index first; raw read when the wiki lacks detail |
| Structural lint (links, orphans, index, sources) | met | `vault_lint.py`; review of the oldest pages against their sources |
| Trust boundary for clipped content | **margin M1** | Data-not-instructions rule, deny rules, local settings, active-HTML lint codes. No incumbent states an injection posture. Cases C4, C7 |
| Privacy and secret lint with an escalation path | **margin M2** | By file and line, never the value; 3 signals in 30 days to a git-ignored folder; history warning. No incumbent scans for privacy or secrets. Case C5 |
| Living-source drift after filing | **margin M3** | `CHANGED`, `NOT-IN-SNAPSHOT`, `GONE`, `NEW-REPO`; only affected pages refreshed. Incumbents skip unchanged files on re-ingest; none detect that a source changed afterwards. Case C6 |
| Native Windows and git-safe | **margin M4** | stdlib Python, PowerShell-safe steps, union merge, commit only when asked, never push. claude-obsidian needs WSL for native Windows writes. Cases C1, C8 |
| Freshness lint by page age | met | `REVIEW:` lists the oldest pages by `updated:` |
| Many commands, retrieval eval | out of scope | obsidian-second-brain is stronger; adopt it for breadth |
| Verifier agents | out of scope | claude-obsidian's agents; vaultscribe reviews by hand in `lint` |
| Obsidian formats, Bases, Canvas, CLI | out of scope | Adopt kepano/obsidian-skills |

### Iterate proposals

- M1: a lint mode that lists every URL in `raw/` clips next to the pages that cite the clip, so a reviewer sees what a page could have been steered towards.
- M2: let the user add their own secret shapes in a vault-local file, read by the lint, never committed.
- M3: a `--pages` flag on the snapshot check that prints the pages citing each `CHANGED` source, so refresh needs no search.
- M4: a PowerShell-only smoke test in the script suite on a Windows runner.
- Met lines: a retrieval eval (questions with known answer pages) to measure query quality, after obsidian-second-brain.

### Retire condition

Retire when an incumbent ships both an injection trust boundary for clipped content (data-not-instructions plus deny rules or an equivalent tool restriction) and a privacy and secret lint that never prints the value, each covered by its own test; then route vault work to it and keep only the snapshot drift check if no incumbent has one.

## Licence note

No incumbent text or code was copied: ideas only. The two scripts are generalised from a
maintainer's own vault scripts and carry no third-party code.
