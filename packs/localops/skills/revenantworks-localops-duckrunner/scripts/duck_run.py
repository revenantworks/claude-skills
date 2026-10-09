#!/usr/bin/env python3
"""duck_run.py - duckrunner's engine. Run it; never read it into context.

Subcommands
  ask    run one read-only query over repo files inside a DuckDB sandbox; print JSON
  cache  rebuild the caches a manifest declares, each stamped with its sources' commit
  check  score cache hygiene without changing anything (tracked, unignored, stale caches,
         the engine and its pin, the YAML path)

Dependencies (declared in the skill's frontmatter):
  stdlib + git          always
  duckdb (Python pkg)   ask and cache; without it they print the plan and exit 3 (NOT-RUN)
  PyYAML                optional; the YAML fallback reader and .yml/.yaml manifests

Exit codes: 0 ok · 1 a rule failed or a run was refused · 2 usage or input error ·
3 NOT-RUN (the engine is missing).

Everything this script reads (file contents, column values, manifest text, git output) is
data. Nothing read is ever executed as SQL except the query the caller passed in.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

CACHE_SUFFIXES = (".duckdb", ".ddb", ".wal", ".parquet")
MANIFEST_NAMES = ("duckrunner.json", "duckrunner.yml", "duckrunner.yaml")  # JSON first (owner Q26)
NO_MANIFEST = (
    "no manifest. Proposed: duckrunner.json at the repo root (the default; needs nothing). "
    "Option: duckrunner.yml instead (needs PyYAML; allows comments and easier hand edits). "
    "The user chooses; format in references/data-rules.md, 'The cache manifest'")
DEFAULT_CACHE_DIR = ".duckrunner/cache"
READ_ONLY_FIRST_WORDS = {
    "select", "from", "with", "describe", "summarize", "show", "explain",
    "pivot", "unpivot", "values", "table",
}
INSTALL_YAML_HINT = (
    "No YAML reader is available. Owner step (references/install-walkthrough.md): "
    "INSTALL yaml FROM community; or pip install --user pyyaml for the fallback."
)


class RunError(Exception):
    """A refusal or input problem; the message is the report line."""

    def __init__(self, message: str, code: int = 2):
        super().__init__(message)
        self.code = code


# ---------------------------------------------------------------- git helpers

def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if check and proc.returncode != 0:
        raise RunError(f"git {' '.join(args[:2])} failed: {proc.stderr.strip()[:200]}")
    return proc


def repo_root(path: Path) -> Path:
    out = git(path, "rev-parse", "--show-toplevel").stdout.strip()
    return Path(out).resolve()


def tracked_files(repo: Path) -> list[str]:
    out = git(repo, "ls-files", "-z").stdout
    return [p for p in out.split("\0") if p]


def is_ignored(repo: Path, rel: str) -> bool:
    return git(repo, "check-ignore", "-q", "--", rel, check=False).returncode == 0


def is_cache_file(rel: str) -> bool:
    return rel.lower().endswith(CACHE_SUFFIXES)


def walk_cache_files(repo: Path) -> list[str]:
    found = []
    for dirpath, dirnames, filenames in os.walk(repo):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for name in filenames:
            if is_cache_file(name):
                found.append(Path(dirpath, name).relative_to(repo).as_posix())
    return sorted(found)


def sources_state(repo: Path, rels: list[str]) -> tuple[str, bool]:
    """(last commit touching the sources, whether any source has uncommitted changes)."""
    commit = git(repo, "log", "-1", "--format=%H", "--", *rels, check=False).stdout.strip()
    dirty = bool(git(repo, "status", "--porcelain", "--", *rels, check=False).stdout.strip())
    return commit, dirty


# ---------------------------------------------------------------- inputs

def load_structured(path: Path) -> object:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        return json.loads(text)
    try:
        import yaml  # PyYAML, optional
    except ImportError:
        raise RunError(f"{path.name} is YAML and PyYAML is not installed; use a .json "
                       f"manifest or install PyYAML (references/install-walkthrough.md)")
    return yaml.safe_load(text)


def find_manifest(repo: Path, given: str | None) -> Path | None:
    if given:
        p = Path(given)
        p = p if p.is_absolute() else repo / p
        if not p.is_file():
            raise RunError(f"manifest not found: {given}")
        return p
    for name in MANIFEST_NAMES:
        if (repo / name).is_file():
            return repo / name
    return None


def load_manifest(path: Path) -> dict:
    data = load_structured(path)
    if not isinstance(data, dict):
        raise RunError(f"{path.name}: the manifest must be a mapping")
    caches = data.get("caches") or []
    if not isinstance(caches, list):
        raise RunError(f"{path.name}: 'caches' must be a list")
    names = set()
    for c in caches:
        if not isinstance(c, dict) or not c.get("name") or not c.get("sources"):
            raise RunError(f"{path.name}: every cache needs a name and a sources list")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", str(c["name"])):
            raise RunError(f"{path.name}: cache name {c['name']!r} must be letters, digits, - or _")
        if c["name"] in names:
            raise RunError(f"{path.name}: duplicate cache name {c['name']!r}")
        names.add(c["name"])
        if c.get("format", "parquet") not in ("parquet", "duckdb"):
            raise RunError(f"{path.name}: cache {c['name']!r} format must be parquet or duckdb")
    data.setdefault("cache_dir", DEFAULT_CACHE_DIR)
    data.setdefault("allow_tracked", [])
    return data


def expand_sources(repo: Path, patterns: list[str]) -> list[Path]:
    out: list[Path] = []
    for pat in patterns:
        full = pat if os.path.isabs(pat) else str(repo / pat)
        matches = sorted(glob.glob(full, recursive=True))
        if not matches:
            raise RunError(f"no file matches {pat!r}")
        for m in matches:
            p = Path(m).resolve()
            try:
                p.relative_to(repo)
            except ValueError:
                raise RunError(f"{pat!r} resolves outside the repo; sources must live in it")
            if p.is_file() and p not in out:
                out.append(p)
    if not out:
        raise RunError("no source files")
    return out


# ---------------------------------------------------------------- SQL helpers

def sql_str(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def posix(p: Path) -> str:
    return p.as_posix()


def strip_sql(sql: str) -> str:
    """Remove comments and string bodies so keyword and ';' checks see only code."""
    out, i, n = [], 0, len(sql)
    while i < n:
        c = sql[i]
        if sql.startswith("--", i):
            j = sql.find("\n", i)
            i = n if j < 0 else j
        elif sql.startswith("/*", i):
            j = sql.find("*/", i + 2)
            i = n if j < 0 else j + 2
        elif c in ("'", '"'):
            j = i + 1
            while j < n:
                if sql[j] == c and j + 1 < n and sql[j + 1] == c:
                    j += 2
                elif sql[j] == c:
                    break
                else:
                    j += 1
            out.append(c + c)
            i = j + 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def validate_read_only(sql: str) -> str:
    """One read-only statement, or RunError. Returns the SQL without a trailing ';'."""
    code = strip_sql(sql).strip()
    if not code:
        raise RunError("empty query")
    body = code.rstrip(";").rstrip()
    if ";" in body:
        raise RunError("one statement per ask; split the query")
    first = re.match(r"\(*\s*([A-Za-z_]+)", body)
    if not first or first.group(1).lower() not in READ_ONLY_FIRST_WORDS:
        word = first.group(1) if first else body[:12]
        raise RunError(f"refused: {word!r} is not a read-only statement "
                       f"(allowed: {', '.join(sorted(READ_ONLY_FIRST_WORDS))})", code=1)
    if re.search(r"\b(copy|attach|install|load|pragma|export|import|checkpoint)\b",
                 body, re.IGNORECASE):
        raise RunError("refused: the query contains a statement keyword that writes, "
                       "loads or attaches", code=1)
    stripped = sql.strip()
    return stripped[:-1].rstrip() if stripped.endswith(";") else stripped


# ---------------------------------------------------------------- reader plan

def view_name(path: Path, used: set[str]) -> str:
    base = re.sub(r"[^a-z0-9_]", "_", path.stem.lower()).strip("_") or "src"
    if base[0].isdigit():
        base = "t_" + base
    name, k = base, 2
    while name in used:
        name, k = f"{base}_{k}", k + 1
    used.add(name)
    return name


def yaml_to_json(src: Path, dst: Path) -> int:
    """PyYAML fallback: a top-level list becomes rows; a mapping becomes one row;
    several documents become one row each. Returns the row count."""
    import yaml
    docs = [d for d in yaml.safe_load_all(src.read_text(encoding="utf-8")) if d is not None]
    if len(docs) == 1 and isinstance(docs[0], list):
        rows = docs[0]
    else:
        rows = docs
    if not all(isinstance(r, dict) for r in rows):
        raise RunError(f"{src.name}: YAML rows must be mappings for the fallback reader")
    dst.write_text(json.dumps(rows, default=str), encoding="utf-8")
    return len(rows)


def pyyaml_available() -> bool:
    try:
        import yaml  # noqa: F401
        return True
    except ImportError:
        return False


def build_plan(repo: Path, sources: list[Path], yaml_ext: bool | None, workdir: Path) -> dict:
    """Map each source to a reader. yaml_ext: True = extension loaded, False = absent,
    None = engine not running (plan only)."""
    used: set[str] = set()
    views, attaches, allowed = [], [], []
    for src in sources:
        ext = src.suffix.lower()
        rel = src.relative_to(repo).as_posix()
        name = view_name(src, used)
        if ext in (".duckdb", ".ddb"):
            attaches.append({"alias": name, "path": rel, "reader": "attach (read-only)",
                             "sql": f"ATTACH {sql_str(posix(src))} AS {name} (READ_ONLY)"})
            # duckdb-skills issue 17: the sandbox must allow the .wal file too.
            allowed += [posix(src), posix(src) + ".wal"]
            continue
        if ext in (".csv", ".tsv", ".txt"):
            opts = ", delim='\\t'" if ext == ".tsv" else ""
            reader, expr = "core read_csv", f"read_csv({sql_str(posix(src))}{opts})"
        elif ext in (".json", ".jsonl", ".ndjson"):
            opts = ", format='newline_delimited'" if ext != ".json" else ""
            reader, expr = "core read_json", f"read_json({sql_str(posix(src))}{opts})"
        elif ext == ".parquet":
            reader, expr = "core read_parquet", f"read_parquet({sql_str(posix(src))})"
        elif ext in (".yaml", ".yml"):
            if yaml_ext:
                reader, expr = "yaml extension", f"read_yaml({sql_str(posix(src))})"
            elif pyyaml_available():
                dst = workdir / f"{name}.json"
                yaml_to_json(src, dst)
                reader = "fallback (PyYAML to JSON, then core read_json)"
                expr = f"read_json({sql_str(posix(dst))})"
                allowed.append(posix(dst))
            else:
                raise RunError(f"{rel}: {INSTALL_YAML_HINT}", code=3)
        else:
            raise RunError(f"{rel}: no reader for {ext or 'files without an extension'}")
        allowed.append(posix(src))
        views.append({"name": name, "path": rel, "reader": reader,
                      "sql": f"CREATE TEMP VIEW {name} AS SELECT * FROM {expr}"})
    return {"views": views, "attaches": attaches, "allowed_paths": allowed}


def sandbox_statements(allowed: list[str], memory_limit: str | None) -> list[str]:
    stmts = []
    if memory_limit:
        stmts.append(f"SET memory_limit = {sql_str(memory_limit)}")
    stmts.append("SET allowed_paths = [" + ", ".join(sql_str(p) for p in allowed) + "]")
    stmts.append("SET enable_external_access = false")
    stmts.append("SET lock_configuration = true")
    return stmts


# ---------------------------------------------------------------- engine

def open_engine():
    try:
        import duckdb
        return duckdb
    except ImportError:
        return None


def engine_version() -> str | None:
    duckdb = open_engine()
    return getattr(duckdb, "__version__", None) if duckdb else None


def load_yaml_extension(con) -> bool:
    """Load the yaml extension only if the user already installed it. Never installs."""
    try:
        con.execute("SET autoinstall_known_extensions = false")
        con.execute("LOAD yaml")
        return True
    except Exception:
        return False


def prepare(con, plan: dict, memory_limit: str | None) -> None:
    for a in plan["attaches"]:
        con.execute(a["sql"])
    for v in plan["views"]:
        con.execute(v["sql"])
    for s in sandbox_statements(plan["allowed_paths"], memory_limit):
        con.execute(s)


# ---------------------------------------------------------------- ask

def cmd_ask(args) -> int:
    repo = repo_root(Path(args.repo))
    sql_text = sys.stdin.read() if args.sql == "-" else Path(args.sql).read_text(encoding="utf-8")
    sql = validate_read_only(sql_text)
    sources = expand_sources(repo, args.sources)
    duckdb = open_engine()
    with tempfile.TemporaryDirectory(prefix="duckrunner-") as tmp:
        if duckdb is None:
            plan = build_plan(repo, sources, None, Path(tmp))
            emit({"status": "NOT-RUN", "reason": "the duckdb Python package is not importable "
                  "(owner step: references/install-walkthrough.md)", "sql": sql,
                  "plan": plan, "sandbox": sandbox_statements(plan["allowed_paths"],
                                                             args.memory_limit)})
            return 3
        con = duckdb.connect(":memory:")
        try:
            yaml_ext = load_yaml_extension(con)
            plan = build_plan(repo, sources, yaml_ext, Path(tmp))
            prepare(con, plan, args.memory_limit)
            cur = con.execute(sql)
            cols = [d[0] for d in cur.description] if cur.description else []
            rows = cur.fetchmany(args.max_rows + 1)
        finally:
            con.close()
    truncated = len(rows) > args.max_rows
    rows = rows[: args.max_rows]
    emit({"status": "ok", "engine": f"duckdb {duckdb.__version__} (Python, in-process)",
          "sql": sql, "sources": [v["path"] for v in plan["views"]] +
          [a["path"] for a in plan["attaches"]],
          "readers": {**{v["path"]: v["reader"] for v in plan["views"]},
                      **{a["path"]: a["reader"] for a in plan["attaches"]}},
          "columns": cols, "rows": [list(r) for r in rows], "rows_shown": len(rows),
          "truncated": truncated, "external_access": False})
    return 0


# ---------------------------------------------------------------- cache

def cache_dir_ignored(repo: Path, cache_dir: str) -> bool:
    probe = f"{cache_dir.rstrip('/')}/probe.parquet"
    return is_ignored(repo, probe)


def cmd_cache(args) -> int:
    repo = repo_root(Path(args.repo))
    mpath = find_manifest(repo, args.manifest)
    if mpath is None:
        raise RunError(NO_MANIFEST)
    manifest = load_manifest(mpath)
    cache_dir = manifest["cache_dir"]
    if not cache_dir_ignored(repo, cache_dir):
        raise RunError(f"refused: {cache_dir}/ is not gitignored. Add the line "
                       f"'{cache_dir.rstrip('/')}/' to .gitignore first (the user's yes).", code=1)
    selected = [c for c in manifest["caches"] if not args.name or c["name"] in args.name]
    if not selected:
        raise RunError("no cache matches --name")
    plans = []
    for c in selected:
        srcs = expand_sources(repo, list(c["sources"]))
        rels = [s.relative_to(repo).as_posix() for s in srcs]
        commit, dirty = sources_state(repo, rels)
        if not commit:
            raise RunError(f"{c['name']}: its sources have no commit yet; commit them first", code=1)
        if dirty and not args.allow_dirty:
            raise RunError(f"refused: {c['name']} has uncommitted source changes; commit them "
                           f"or pass --allow-dirty (the stamp then records dirty)", code=1)
        plans.append((c, srcs, rels, commit, dirty))
    duckdb = open_engine()
    if duckdb is None:
        emit({"status": "NOT-RUN", "reason": "the duckdb Python package is not importable",
              "would_build": [{"name": c["name"], "sources": rels, "source_commit": commit,
                               "dirty": dirty} for c, _, rels, commit, dirty in plans]})
        return 3
    out_dir = repo / cache_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for c, srcs, rels, commit, dirty in plans:
        results.append(build_one(duckdb, repo, out_dir, c, srcs, rels, commit, dirty,
                                 args.memory_limit))
    emit({"status": "ok", "cache_dir": cache_dir, "caches": results})
    return 0


def build_one(duckdb, repo, out_dir, c, srcs, rels, commit, dirty, memory_limit) -> dict:
    fmt = c.get("format", "parquet")
    final = out_dir / f"{c['name']}.{fmt}"
    tmp_out = out_dir / f"{c['name']}.{fmt}.tmp"
    lock = out_dir / f"{c['name']}.lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise RunError(f"{c['name']}: another cache run holds {lock.name}; if no run is live, "
                       f"the user removes it", code=1)
    os.close(fd)
    try:
        with tempfile.TemporaryDirectory(prefix="duckrunner-") as tmp:
            for p in (tmp_out, Path(str(tmp_out) + ".wal")):
                if p.exists():
                    p.unlink()
            con = duckdb.connect(posix(tmp_out) if fmt == "duckdb" else ":memory:")
            try:
                yaml_ext = load_yaml_extension(con)
                plan = build_plan(repo, srcs, yaml_ext, Path(tmp))
                if c.get("sql"):
                    sql = validate_read_only(str(c["sql"]))
                elif len(plan["views"]) == 1:
                    sql = f"FROM {plan['views'][0]['name']}"
                else:
                    raise RunError(f"{c['name']}: several sources need an explicit sql")
                if fmt == "parquet":
                    plan["allowed_paths"].append(posix(tmp_out))
                prepare(con, plan, memory_limit)
                if fmt == "parquet":
                    con.execute(f"COPY ({sql}) TO {sql_str(posix(tmp_out))} (FORMAT parquet)")
                    rows = con.execute(
                        f"SELECT count(*) FROM read_parquet({sql_str(posix(tmp_out))})").fetchone()[0]
                else:
                    con.execute(f"CREATE TABLE {c['name'].replace('-', '_')} AS {sql}")
                    rows = con.execute(
                        f"SELECT count(*) FROM {c['name'].replace('-', '_')}").fetchone()[0]
            finally:
                con.close()
        os.replace(tmp_out, final)
        stamp = {"name": c["name"], "format": fmt, "sources": rels, "source_commit": commit,
                 "dirty": dirty, "rows": rows, "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                                         time.gmtime()),
                 "engine": f"duckdb {duckdb.__version__}",
                 "readers": {v["path"]: v["reader"] for v in plan["views"]}}
        (out_dir / f"{c['name']}.stamp.json").write_text(json.dumps(stamp, indent=2),
                                                          encoding="utf-8")
        return {"name": c["name"], "path": final.relative_to(repo).as_posix(), "rows": rows,
                "source_commit": commit, "dirty": dirty}
    finally:
        try:
            lock.unlink()
        except FileNotFoundError:
            pass


# ---------------------------------------------------------------- check

def check_stamps(repo: Path, manifest: dict) -> list[dict]:
    items = []
    out_dir = repo / manifest["cache_dir"]
    for c in manifest["caches"]:
        fmt = c.get("format", "parquet")
        cache = out_dir / f"{c['name']}.{fmt}"
        stamp_p = out_dir / f"{c['name']}.stamp.json"
        try:
            srcs = expand_sources(repo, list(c["sources"]))
        except RunError as e:
            items.append({"name": c["name"], "status": "sources-missing", "detail": str(e)})
            continue
        rels = [s.relative_to(repo).as_posix() for s in srcs]
        commit, dirty = sources_state(repo, rels)
        if not cache.is_file() or not stamp_p.is_file():
            items.append({"name": c["name"], "status": "missing",
                          "detail": "not built yet; run cache"})
            continue
        try:
            stamp = json.loads(stamp_p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            items.append({"name": c["name"], "status": "stale", "detail": "stamp unreadable"})
            continue
        if stamp.get("source_commit") != commit or sorted(stamp.get("sources", [])) != sorted(rels):
            status, detail = "stale", f"stamped {str(stamp.get('source_commit'))[:12]}, sources now {commit[:12]}"
        elif dirty or stamp.get("dirty"):
            status, detail = "stale", "built from or now has uncommitted source changes"
        else:
            status, detail = "fresh", f"matches {commit[:12]}"
        items.append({"name": c["name"], "status": status, "detail": detail})
    return items


def cmd_check(args) -> int:
    repo = repo_root(Path(args.repo))
    mpath = find_manifest(repo, args.manifest)
    manifest = load_manifest(mpath) if mpath else None
    allow = set(manifest["allow_tracked"]) if manifest else set()
    rules = []

    tracked = [p for p in tracked_files(repo) if is_cache_file(p) and p not in allow]
    rules.append({"rule": "no tracked cache", "status": "fail" if tracked else "pass",
                  "items": tracked,
                  "fix": "owner command per file: git rm --cached -- <path> (then ignore it)"
                  if tracked else ""})

    tracked_set = set(tracked_files(repo))
    loose = [p for p in walk_cache_files(repo) if p not in tracked_set and not is_ignored(repo, p)]
    rules.append({"rule": "every cache ignored", "status": "fail" if loose else "pass",
                  "items": loose, "fix": "add an ignore line for each, or delete it" if loose else ""})

    if manifest:
        ok = cache_dir_ignored(repo, manifest["cache_dir"])
        rules.append({"rule": "cache dir ignored", "status": "pass" if ok else "fail",
                      "items": [] if ok else [manifest["cache_dir"]]})
        stamps = check_stamps(repo, manifest)
        bad = [s for s in stamps if s["status"] != "fresh"]
        rules.append({"rule": "caches match their sources", "status": "warn" if bad else "pass",
                      "items": stamps})
    else:
        rules.append({"rule": "caches match their sources", "status": "n/a",
                      "items": [], "fix": "no manifest; nothing declared to compare"})

    version = engine_version()
    engine = {"rule": "engine", "duckdb": version, "pin": args.pin,
              "pyyaml": pyyaml_available(), "yaml_extension": None}
    if version is None:
        engine["status"] = "not-run"
    else:
        engine["status"] = "pass"
        if args.pin and not (version == args.pin or version.startswith(args.pin.rstrip(".") + ".")):
            engine["status"] = "fail"
            engine["fix"] = f"installed {version} is outside the pin {args.pin}"
        duckdb = open_engine()
        con = duckdb.connect(":memory:")
        try:
            engine["yaml_extension"] = load_yaml_extension(con)
        finally:
            con.close()
    rules.append(engine)

    verdict = "fail" if any(r["status"] == "fail" for r in rules) else "pass"
    emit({"repo": repo.name, "manifest": mpath.relative_to(repo).as_posix() if mpath else None,
          "rules": rules, "verdict": verdict})
    return 1 if verdict == "fail" else 0


# ---------------------------------------------------------------- main

def emit(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj, indent=2, default=str) + "\n")


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="duck_run.py", description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("ask", help="one read-only query in a sandbox")
    a.add_argument("--sql", required=True, help="a .sql file, or - for stdin")
    a.add_argument("--sources", nargs="+", required=True, help="files or globs inside the repo")
    a.add_argument("--repo", default=".")
    a.add_argument("--max-rows", type=int, default=50)
    a.add_argument("--memory-limit", default=None, help="DuckDB memory_limit, e.g. 2GB")
    c = sub.add_parser("cache", help="rebuild declared caches, stamped with the source commit")
    c.add_argument("--manifest", default=None)
    c.add_argument("--name", nargs="*", default=None, help="only these caches")
    c.add_argument("--repo", default=".")
    c.add_argument("--allow-dirty", action="store_true")
    c.add_argument("--memory-limit", default=None)
    k = sub.add_parser("check", help="score cache hygiene; changes nothing")
    k.add_argument("--manifest", default=None)
    k.add_argument("--repo", default=".")
    k.add_argument("--pin", default=None, help="DuckDB version prefix from references/readers.md")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        return {"ask": cmd_ask, "cache": cmd_cache, "check": cmd_check}[args.cmd](args)
    except RunError as e:
        emit({"status": "refused" if e.code == 1 else ("NOT-RUN" if e.code == 3 else "error"),
              "reason": str(e)})
        return e.code


if __name__ == "__main__":
    sys.exit(main())
