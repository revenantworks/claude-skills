# revenantworks-localops-duckrunner

Answers questions over the CSV, JSON, Parquet and YAML files in a repo with DuckDB, shows the
SQL every time, and keeps DuckDB's caches out of git.

## What sets it apart

Several DuckDB skills and servers already run SQL over files well, DuckDB's own plugin first
among them. Three things none of them does:

- **YAML is a first-class source.** DuckDB has no core YAML reader. duckrunner uses the yaml
  community extension when you have installed it, falls back to a PyYAML conversion when you
  have not, and every answer says which path ran.
- **Caches are disposable and stamped.** A `.duckdb` or `.parquet` file built from your files is
  a cache. duckrunner rebuilds it from a manifest, records the commit its sources were at, and
  tells you when the sources have moved on.
- **A hygiene check.** `check` fails when a cache is committed or not ignored, and hands you the
  one command to fix it. It never runs that command itself.

**Versus duckdb-skills** (read 2026-10-08): DuckDB's plugin adds docs search, remote reads and an extension installer; duckrunner keeps every query read-only and sandboxed, reads YAML, and keeps stamped caches out of git.

## Package

```
revenantworks-localops-duckrunner/
├── SKILL.md
├── README.md · CHANGELOG.md · SOURCES.md · LICENSE
├── references/
│   ├── readers.md              # versions, the pin, readers, YAML path, sandbox (dated)
│   ├── data-rules.md           # sources in git, caches ignored, the manifest and the stamp
│   ├── analytics-csv.md        # recipes for a video platform's analytics exports
│   ├── install-walkthrough.md  # owner-run installs with verify and rollback
│   └── pack.md                 # the localops roster
├── scripts/
│   ├── duck_run.py             # ask, cache, check
│   └── test_duck_run.py
└── evals/                      # hand-run suites + native claude plugin eval cases
```

## Install

The skill installs nothing. In Claude Code it arrives with the localops plugin. It needs git,
Python 3.9 or newer, and, for `ask` and `cache`, the `duckdb` Python package at the pinned
version: the one package this skill drives, allowed by the localops package rule, and you
install it. The yaml extension and PyYAML are optional. `references/install-walkthrough.md` walks
through each step with a verification command and a rollback; no step needs an administrator.

## Commands

| Say | What happens |
|---|---|
| `duckrunner ask <question>` | One read-only query in a sandbox; the answer, the SQL, the files and the reader per file |
| `duckrunner cache [name]` | Rebuild the caches the manifest declares, each stamped with its sources' commit |
| `duckrunner check` | Score cache hygiene, stamps, the engine pin and the YAML paths; change nothing |
| `duckrunner refresh` | Re-verify the dated facts in `references/readers.md` |

You rarely need the word: "how many items in queue.yml are done?", "which videos in my
analytics export had the most watch time?" or "is a parquet file committed here?" is enough.

## Staying current

`references/readers.md` holds every version and date and is re-checked every 90 days with
`duckrunner refresh`. The engine stays on its pinned line until the yaml extension ships for the
next major release; the walkthrough's last section covers the upgrade.

## Boundaries

DuckDB documentation, S3 and MotherDuck belong to DuckDB's own duckdb-skills plugin or the docs
site. Research across outside sources is researchscribe's. Setting up a database server is not
this skill's job.

See [CHANGELOG.md](CHANGELOG.md).
