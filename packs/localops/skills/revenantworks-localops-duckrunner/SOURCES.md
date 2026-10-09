# Sources — revenantworks-localops-duckrunner

> **Last verified: 2026-10-01** — the primary sources and the parity register below
> (calendar surface, 90 days, declared in `volatile.json`). The incumbent scan was run on
> 2026-09-28 (research unit R1) and spot-checked live on 2026-10-01 where marked.

## Primary — the engine this skill drives

- **DuckDB release calendar** — duckdb.org/release_calendar, read 2026-10-01: stable 1.5.6
  (2026-09-28), LTS 1.4.0 to 2026-11-17, 2.0.0 planned 2026-10-21 and marked tentative. The
  figures live in `references/readers.md` only.
- **DuckDB security settings** — duckdb.org/docs, "Securing DuckDB" (the `stable` path
  redirected to `current`), read 2026-10-01: `enable_external_access`, `allowed_paths`,
  `allowed_directories`, `lock_configuration`. Quoted in `readers.md`, "The sandbox".
- **The yaml community extension** — duckdb/community-extensions
  `extensions/yaml/description.yml` (raw), read 2026-10-01: version 1.9.2, functions
  `read_yaml`, `read_yaml_objects`, `yaml_to_json`, `yaml_structure` and others. Windows builds
  for v1.5.6, v1.5.5 and v1.4.4 answered HTTP 200 on 2026-09-28 (R1).
- **PyPI `duckdb`** — 1.5.6, read 2026-09-28 (R1).

## Primary — the eval format

- **Claude Code plugin evals** — code.claude.com/docs/en/plugin-evals (raw Markdown), read
  2026-10-01: case folders with `prompt.md` and `graders/*.md`; grader types `regex`,
  `tool_used`, `tool_order`, `file_exists`, `llm`, `baseline`; `min: 0`, `max: 0`, `arm: both`
  for a must-not-invoke check; `case.yaml` with `schema_version: "1.1"` and
  `context.scaffold_script` (runs only with `--scaffold`).

## Owner decisions applied

- Pin DuckDB at 1.5.x until the yaml extension ships for 2.0; YAML via the extension with a
  PyYAML fallback (pack-split run, summary item 7, 2026-09-29).
- Do not install DuckDB's duckdb-skills plugin; route to it or cite it (item 9).
- Installs are manual; the skill ships an owner walkthrough (handoff decision 6).
- Files in git are the source of truth; Parquet and `.duckdb` files are gitignored caches; no
  database server (the user's data rule, carried here as a general rule).

## Parity register

**Incumbents** (checked 2026-09-28 by R1 unless marked):

| Incumbent | Link | What it is |
|---|---|---|
| duckdb-skills | github.com/duckdb/duckdb-skills (also listed in anthropics/claude-plugins-official) | DuckDB's own plugin: attach-db, query, read-file, convert-file, duckdb-docs, install-duckdb, read-memories and more; a one-skill rewrite closed as issue 18 on 2026-09-18. Re-scanned 2026-10-01 (unit PR): exact-match code search for "yaml" in the repo returns 0 hits (verified absence); last code commit 2026-04-14; issue 17 (.wal) still open; issue 19 (name prefix) open. Re-read 2026-10-08 (K4 C8, public pages only): its `query` sandbox covers ad-hoc mode only; session mode on an attached database runs unsandboxed and its reference suggests write patterns; it does not state that it shows the SQL; Windows not yet fully supported. Verdict: keep duckrunner. |
| mcp-server-motherduck | github.com/motherduckdb/mcp-server-motherduck | MotherDuck's local DuckDB MCP server, v1.0.8 (2026-08-19); read-only by default |
| TerminalSkills duckdb and about twelve similar | GitHub code search `filename:SKILL.md duckdb` | generic SQL-over-files helpers |

**Parity table:**

| Capability | Line | Reason | Eval case |
|---|---|---|---|
| Ask a question over CSV, JSON, Parquet with SQL | met | same engine as duckdb-skills `query` and `read-file` | TC-01, unit `test_ask_counts_rows_and_reports_reader` |
| Show the query used | met | required in every answer, not optional | TC-01, native `behaviour-no-shell-shows-sql` |
| YAML sources | **beaten** | no incumbent reads YAML; the extension, or the fallback, and the answer names which | TC-01, TC-02, TC-03, native `behaviour-no-shell-shows-sql` |
| Read-only safety | met | sources opened read-only, attaches READ_ONLY, writes refused before DuckDB sees them | TC-08 |
| Sandboxed query | met, with a fix | adopts duckdb-skills' `allowed_paths` plus `enable_external_access=false`, adds the `.wal` path (their issue 17) and `lock_configuration` | TC-07, TC-09 |
| Cache rebuild from git sources | **beaten** | no incumbent treats the database as a disposable cache built from files in git | TC-05, TC-06 |
| Cache hygiene (ignored, never committed) | **beaten** | `check` fails on a tracked or unignored cache | TC-04, native `behaviour-check-tracked-cache` |
| No database server | met | in-process only; stated and never started | trigger row 11, native `nearmiss-postgres-server` |
| Docs search | out of scope | duckdb-skills `duckdb-docs` does it; routed | native `nearmiss-duckdb-docs` |
| S3, MotherDuck, spatial | out of scope | local files in git only | trigger rows 14, 15 |
| Session memory over Claude logs | out of scope | a different job | — |

**Margins** (each with its case):

1. *Cache hygiene check* — `duck_run.py check` fails on any tracked or unignored `.duckdb`,
   `.wal`, `.parquet` or `.ddb` file and hands the user the untrack command. TC-04;
   native `behaviour-check-tracked-cache`; unit `test_tracked_parquet_fails_and_is_named`.
2. *YAML as a first-class source* — the extension or the PyYAML fallback, and the answer names
   the path that ran; NOT-RUN rather than a guess when neither exists. TC-01 to TC-03; native
   `behaviour-no-shell-shows-sql`; units `test_yaml_fallback_converts_and_says_so`,
   `test_yaml_with_no_reader_refuses_with_the_install_line`.
3. *Caches stamped with the source commit* — `cache` records the last commit touching the
   sources, and `check` marks a cache stale when that commit moves or a source is dirty. TC-05;
   units `test_stamp_fresh_then_stale_after_source_commit`, `test_stamp_stale_when_sources_dirty`.

**Iterate proposals:**

- Adopt the one-skill, progressive-disclosure shape of duckdb-skills' rewrite (done: one skill,
  three modes, three references).
- Open databases read-only by default to avoid the lock clash of duckdb-skills issue 11 (done).
- Pin the engine in `check` and warn before a major upgrade breaks the yaml extension (done:
  `--pin`).
- Next: store the stamp inside the Parquet file's key-value metadata as well as the sidecar, so a
  copied cache still carries its commit.
- Next: a `--explain` flag on `ask` that returns `EXPLAIN` output for slow queries.

**Retire condition.** duckdb-skills (or its rewrite) adds a YAML reader and a git-aware cache
hygiene check. YAML alone landing removes margin 2; margins 1 and 3 remain. The verdict at build
is **PARITY + MARGIN**, with a narrow margin.

## Ideas adopted, no text copied

From duckdb-skills (MIT, per its repository): the sandbox settings for ad-hoc queries, format
detection by file extension, and friendly SQL in shown queries. From mcp-server-motherduck:
read-only by default. Ideas only; no text or code was copied.

## Not verified

- Whether `allowed_paths` applies while external access is still enabled (the docs example sets
  both; so does the script).
- Whether the winget `DuckDB.cli` package installs per user or per machine.
- The engine path of `duck_run.py` (`ask`, `cache` and the extension load) was not executed at
  build: the duckdb package was not installed, and units install nothing. Four engine tests skip
  until the user's walkthrough step 2 is done.
