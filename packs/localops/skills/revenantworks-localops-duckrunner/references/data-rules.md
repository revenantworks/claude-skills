# Data rules: sources in git, caches out of it

Read this file in `cache` and `check`, and when someone asks why a cache was refused.
Written so any runner that writes derived data can share it; today only duckrunner carries it.

## The three rules

1. **Files in git are the source of truth.** CSV, JSON, YAML and Markdown that people edit and
   review live in the repo. duckrunner reads them and never writes to them.
2. **Caches are derived and disposable.** A `.duckdb`, `.ddb`, `.wal` or `.parquet` file built
   from those sources is a cache. It is gitignored, never committed, and can be deleted and
   rebuilt at any time from the sources plus the manifest.
3. **No database server.** DuckDB runs in-process, inside the script, and exits with it.
   duckrunner never starts a server, a service or a background process. A job that genuinely
   needs a server (two writers on one table at once) is out of this skill's scope.

A file with a cache extension that is a deliberate source (a Parquet file published as data)
is listed under `allow_tracked` in the manifest, and `check` then leaves it alone.

## The cache manifest

One file at the repo root, tracked in git. **JSON is the default** (owner decision Q26):
`duckrunner.json` needs nothing. **YAML is the offered option:** `duckrunner.yml` or
`duckrunner.yaml` needs PyYAML, and in return allows comments and easier hand edits. With no
manifest yet, propose JSON, offer YAML once with those pros and cons, and let the user
choose. When both exist, `duck_run.py` reads the JSON file. The fields are the same in both;
the example below is YAML for its comments, and the JSON form follows it.

```yaml
cache_dir: .duckrunner/cache        # default; must be gitignored
allow_tracked: []                   # deliberate source files with a cache extension
caches:
  - name: queue                     # letters, digits, - or _
    sources: ["state/queue.yml"]    # files or globs inside the repo
    format: parquet                 # parquet (default) or duckdb
  - name: weekly
    sources: ["logs/*.csv", "state/queue.yml"]
    sql: "FROM logs JOIN queue USING (id)"   # required when there is more than one source
```

The same manifest as `duckrunner.json` (the default):

```json
{"cache_dir": ".duckrunner/cache",
 "allow_tracked": [],
 "caches": [
   {"name": "queue", "sources": ["state/queue.yml"], "format": "parquet"},
   {"name": "weekly", "sources": ["logs/*.csv", "state/queue.yml"],
    "sql": "FROM logs JOIN queue USING (id)"}]}
```

The views a `sql` line can use are the source file stems (`readers.md`, "Format to reader").

## The stamp

`cache` writes `<cache_dir>/<name>.stamp.json` beside each cache: the sources, the
**source commit** (the last commit that touched any of them), whether the sources had
uncommitted changes, the row count, the build time, the engine version and the reader used per
source. A cache is:

- **fresh** when the stamp's source commit equals the sources' last commit now, the source list
  is the same, and neither side is dirty;
- **stale** when any of those differ;
- **missing** when the cache or its stamp does not exist.

Stale is a warning and the fix is `cache`. `cache` refuses uncommitted sources unless the
owner passes `--allow-dirty`, and the stamp then records `dirty: true`, so the cache reads as
stale until it is rebuilt from committed sources.

## Fixes `check` hands the user

| Finding | The user's command | Note |
|---|---|---|
| A cache is tracked | `git rm --cached -- <path>` then add its ignore line | Stops tracking; the file stays on disk |
| A cache is not ignored | add `<cache_dir>/` (or the file's pattern) to `.gitignore` | duckrunner writes the line only on the user's yes |
| A cache is in past commits | none from this skill | Removing it from history is a history rewrite: the warden pack's shieldwarden where installed, and always the user's push |
| A leftover `<name>.lock` | delete that one file | Only when no cache run is live |

duckrunner never runs `git rm`, never commits, and never pushes.
