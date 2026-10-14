"""Tests for duck_run.py. Stdlib unittest; git required. The engine tests run only when the
duckdb Python package is importable, and the fallback tests only when PyYAML is; both are
skipped (and reported as skipped) otherwise.

Run: python -m unittest discover -s <skill>/scripts -p "test_*.py"
"""
import contextlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import duck_run  # noqa: E402

HAS_DUCKDB = duck_run.open_engine() is not None
HAS_PYYAML = duck_run.pyyaml_available()
HAS_GIT = shutil.which("git") is not None


def run_main(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = duck_run.main(argv)
    return code, json.loads(buf.getvalue())


@unittest.skipUnless(HAS_GIT, "git not on PATH")
class RepoCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="duckrunner-test-")
        self.repo = Path(self._tmp.name).resolve()
        self.git("init", "-q")
        self.git("config", "user.email", "duckrunner-test")
        self.git("config", "user.name", "test")
        self.git("config", "core.autocrlf", "false")

    def tearDown(self):
        self._tmp.cleanup()

    def git(self, *args):
        subprocess.run(["git", "-C", str(self.repo), *args], check=True,
                       capture_output=True, text=True)

    def write(self, rel, text):
        p = self.repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    def commit(self, msg="c"):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", msg)


class CheckTests(RepoCase):
    def test_tracked_parquet_fails_and_is_named(self):
        self.write("data/cache.parquet", "not really parquet")
        self.write("data/a.csv", "x\n1\n")
        self.commit()
        code, out = run_main(["check", "--repo", str(self.repo)])
        self.assertEqual(code, 1)
        self.assertEqual(out["verdict"], "fail")
        rule = next(r for r in out["rules"] if r["rule"] == "no tracked cache")
        self.assertEqual(rule["items"], ["data/cache.parquet"])
        self.assertIn("git rm --cached", rule["fix"])

    def test_untracked_unignored_duckdb_fails_then_ignored_passes(self):
        self.write("a.csv", "x\n1\n")
        self.commit()
        self.write("scratch.duckdb", "x")
        code, out = run_main(["check", "--repo", str(self.repo)])
        self.assertEqual(code, 1)
        rule = next(r for r in out["rules"] if r["rule"] == "every cache ignored")
        self.assertEqual(rule["items"], ["scratch.duckdb"])
        self.write(".gitignore", "*.duckdb\n")
        code, out = run_main(["check", "--repo", str(self.repo)])
        self.assertEqual(code, 0, out)

    def test_allow_tracked_exempts_a_deliberate_parquet_source(self):
        self.write("published/data.parquet", "x")
        self.write("duckrunner.json", json.dumps({"allow_tracked": ["published/data.parquet"],
                                                  "caches": []}))
        self.write(".gitignore", ".duckrunner/\n")
        self.commit()
        code, out = run_main(["check", "--repo", str(self.repo)])
        self.assertEqual(code, 0, out)

    def manifest_repo(self):
        self.write("state/queue.csv", "id,done\n1,true\n2,false\n")
        self.write(".gitignore", ".duckrunner/\n")
        self.write("duckrunner.json", json.dumps({"caches": [
            {"name": "queue", "sources": ["state/queue.csv"]}]}))
        self.commit()

    def stamp(self, commit, dirty=False):
        out = self.repo / ".duckrunner/cache"
        out.mkdir(parents=True, exist_ok=True)
        (out / "queue.parquet").write_text("x")
        (out / "queue.stamp.json").write_text(json.dumps(
            {"source_commit": commit, "sources": ["state/queue.csv"], "dirty": dirty}))

    def head(self):
        return subprocess.run(["git", "-C", str(self.repo), "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()

    def stamp_status(self):
        code, out = run_main(["check", "--repo", str(self.repo)])
        rule = next(r for r in out["rules"] if r["rule"] == "caches match their sources")
        return code, rule["items"][0]["status"]

    def test_stamp_fresh_then_stale_after_source_commit(self):
        self.manifest_repo()
        self.stamp(self.head())
        self.assertEqual(self.stamp_status(), (0, "fresh"))
        self.write("state/queue.csv", "id,done\n1,true\n2,true\n")
        self.commit("source moved")
        code, status = self.stamp_status()
        self.assertEqual(status, "stale")
        self.assertEqual(code, 0, "stale is a warning, not a failure")

    def test_stamp_stale_when_sources_dirty(self):
        self.manifest_repo()
        self.stamp(self.head())
        self.write("state/queue.csv", "id,done\n9,true\n")
        self.assertEqual(self.stamp_status()[1], "stale")

    def test_stamp_missing(self):
        self.manifest_repo()
        self.assertEqual(self.stamp_status()[1], "missing")

    def test_pin_outside_range_fails(self):
        self.write("a.csv", "x\n1\n")
        self.commit()
        with mock.patch.object(duck_run, "engine_version", return_value="2.0.0"), \
                mock.patch.object(duck_run, "open_engine") as eng:
            eng.return_value.connect.return_value.execute.side_effect = Exception("no yaml")
            code, out = run_main(["check", "--repo", str(self.repo), "--pin", "1.5"])
        engine = next(r for r in out["rules"] if r["rule"] == "engine")
        self.assertEqual(engine["status"], "fail")
        self.assertEqual(code, 1)


class CacheRefusalTests(RepoCase):
    def test_cache_refuses_when_cache_dir_not_ignored(self):
        self.write("a.csv", "x\n1\n")
        self.write("duckrunner.json", json.dumps({"caches": [{"name": "a", "sources": ["a.csv"]}]}))
        self.commit()
        code, out = run_main(["cache", "--repo", str(self.repo)])
        self.assertEqual(code, 1)
        self.assertIn("not gitignored", out["reason"])

    def test_cache_refuses_dirty_sources(self):
        self.write("a.csv", "x\n1\n")
        self.write(".gitignore", ".duckrunner/\n")
        self.write("duckrunner.json", json.dumps({"caches": [{"name": "a", "sources": ["a.csv"]}]}))
        self.commit()
        self.write("a.csv", "x\n2\n")
        code, out = run_main(["cache", "--repo", str(self.repo)])
        self.assertEqual(code, 1)
        self.assertIn("uncommitted", out["reason"])

    def test_cache_without_engine_is_not_run_with_the_commit(self):
        self.write("a.csv", "x\n1\n")
        self.write(".gitignore", ".duckrunner/\n")
        self.write("duckrunner.json", json.dumps({"caches": [{"name": "a", "sources": ["a.csv"]}]}))
        self.commit()
        with mock.patch.object(duck_run, "open_engine", return_value=None):
            code, out = run_main(["cache", "--repo", str(self.repo)])
        self.assertEqual(code, 3)
        self.assertEqual(out["would_build"][0]["source_commit"], self.head_commit())

    def head_commit(self):
        return subprocess.run(["git", "-C", str(self.repo), "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()


class ManifestChoiceTests(unittest.TestCase):
    """Owner Q26: JSON is the default manifest; YAML is the offered option (audit K-1)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="duckrunner-manifest-")
        self.repo = Path(self._tmp.name).resolve()

    def tearDown(self):
        self._tmp.cleanup()

    def test_json_is_listed_first(self):
        self.assertEqual(duck_run.MANIFEST_NAMES[0], "duckrunner.json")

    def test_json_wins_when_both_exist(self):
        (self.repo / "duckrunner.yml").write_text("caches: []\n", encoding="utf-8")
        (self.repo / "duckrunner.json").write_text('{"caches": []}\n', encoding="utf-8")
        self.assertEqual(duck_run.find_manifest(self.repo, None).name, "duckrunner.json")

    def test_yaml_alone_is_still_found(self):
        (self.repo / "duckrunner.yml").write_text("caches: []\n", encoding="utf-8")
        self.assertEqual(duck_run.find_manifest(self.repo, None).name, "duckrunner.yml")

    def test_no_manifest_message_proposes_json_and_offers_yaml(self):
        msg = duck_run.NO_MANIFEST
        self.assertIn("duckrunner.json", msg)
        self.assertLess(msg.index("duckrunner.json"), msg.index("duckrunner.yml"))
        self.assertIn("PyYAML", msg)
        self.assertIn("comments", msg)


class SqlTests(unittest.TestCase):
    def test_read_only_statements_pass(self):
        for sql in ("SELECT 1", "FROM queue LIMIT 10;", "WITH a AS (SELECT 1) SELECT * FROM a",
                    "select ';' as semi", "-- note\nSUMMARIZE queue", "DESCRIBE queue"):
            duck_run.validate_read_only(sql)

    def test_writes_and_multi_statements_refused(self):
        for sql in ("COPY queue TO 'x.csv'", "ATTACH 'x.duckdb'", "INSTALL yaml",
                    "SELECT 1; SELECT 2", "CREATE TABLE t AS SELECT 1", "SET x = 1",
                    "SELECT * FROM t; DROP TABLE t", "PRAGMA version"):
            with self.assertRaises(duck_run.RunError, msg=sql):
                duck_run.validate_read_only(sql)

    def test_keyword_inside_string_is_not_a_statement(self):
        duck_run.validate_read_only("SELECT 'copy this' AS note")

    def test_sandbox_order(self):
        stmts = duck_run.sandbox_statements(["/r/a.csv"], "2GB")
        self.assertEqual(stmts[0], "SET memory_limit = '2GB'")
        self.assertEqual(stmts[-2:], ["SET enable_external_access = false",
                                      "SET lock_configuration = true"])


class PlanTests(RepoCase):
    def test_attached_duckdb_allows_its_wal(self):
        db = self.write("cache/state.duckdb", "x")
        plan = duck_run.build_plan(self.repo, [db.resolve()], None, self.repo)
        self.assertIn(db.resolve().as_posix() + ".wal", plan["allowed_paths"])
        self.assertIn("READ_ONLY", plan["attaches"][0]["sql"])

    def test_yaml_with_extension_uses_read_yaml(self):
        y = self.write("state/queue.yml", "- id: 1\n  done: true\n")
        plan = duck_run.build_plan(self.repo, [y.resolve()], True, self.repo)
        self.assertEqual(plan["views"][0]["reader"], "yaml extension")
        self.assertIn("read_yaml(", plan["views"][0]["sql"])

    @unittest.skipUnless(HAS_PYYAML, "PyYAML not installed")
    def test_yaml_fallback_converts_and_says_so(self):
        y = self.write("state/queue.yml", "- id: 1\n  done: true\n- id: 2\n  done: false\n")
        with tempfile.TemporaryDirectory() as tmp:
            plan = duck_run.build_plan(self.repo, [y.resolve()], False, Path(tmp))
            view = plan["views"][0]
            self.assertTrue(view["reader"].startswith("fallback"))
            rows = json.loads((Path(tmp) / "queue.json").read_text(encoding="utf-8"))
            self.assertEqual(len(rows), 2)
            self.assertIn((Path(tmp) / "queue.json").as_posix(), plan["allowed_paths"])

    def test_yaml_with_no_reader_refuses_with_the_install_line(self):
        y = self.write("state/queue.yml", "- id: 1\n")
        with mock.patch.object(duck_run, "pyyaml_available", return_value=False):
            with self.assertRaises(duck_run.RunError) as ctx:
                duck_run.build_plan(self.repo, [y.resolve()], False, self.repo)
        self.assertEqual(ctx.exception.code, 3)
        self.assertIn("INSTALL yaml FROM community", str(ctx.exception))

    def test_sources_outside_repo_refused(self):
        with tempfile.TemporaryDirectory() as other:
            outside = Path(other, "x.csv")
            outside.write_text("x\n1\n")
            with self.assertRaises(duck_run.RunError):
                duck_run.expand_sources(self.repo, [str(outside)])

    def test_ask_without_engine_returns_plan_not_run(self):
        self.write("a.csv", "x\n1\n")
        sql = self.write("q.sql", "SELECT count(*) FROM a")
        with mock.patch.object(duck_run, "open_engine", return_value=None):
            code, out = run_main(["ask", "--repo", str(self.repo), "--sql", str(sql),
                                  "--sources", "a.csv"])
        self.assertEqual(code, 3)
        self.assertEqual(out["status"], "NOT-RUN")
        self.assertEqual(out["sql"], "SELECT count(*) FROM a")
        self.assertIn("SET enable_external_access = false", out["sandbox"])


@unittest.skipUnless(HAS_DUCKDB, "duckdb Python package not installed")
class EngineTests(RepoCase):
    def test_ask_counts_rows_and_reports_reader(self):
        self.write("state/queue.csv", "id,done\n1,true\n2,false\n3,true\n")
        sql = self.write("q.sql", "SELECT count(*) AS n FROM queue WHERE done")
        code, out = run_main(["ask", "--repo", str(self.repo), "--sql", str(sql),
                              "--sources", "state/*.csv"])
        self.assertEqual(code, 0, out)
        self.assertEqual(out["rows"], [[2]])
        self.assertEqual(out["readers"]["state/queue.csv"], "core read_csv")
        self.assertFalse(out["external_access"])

    def test_sandbox_blocks_a_file_outside_the_sources(self):
        self.write("a.csv", "x\n1\n")
        self.write("secret.csv", "k\nv\n")
        sql = self.write("q.sql", f"SELECT * FROM read_csv('{(self.repo / 'secret.csv').as_posix()}')")
        code, _ = run_main(["ask", "--repo", str(self.repo), "--sql", str(sql),
                            "--sources", "a.csv"])
        self.assertNotEqual(code, 0)

    def test_attached_duckdb_first_query_succeeds(self):
        import duckdb
        db = self.repo / "cache" / "state.duckdb"
        db.parent.mkdir()
        con = duckdb.connect(str(db))
        con.execute("CREATE TABLE t AS SELECT 1 AS x")
        con.close()
        sql = self.write("q.sql", "SELECT x FROM state.t")
        code, out = run_main(["ask", "--repo", str(self.repo), "--sql", str(sql),
                              "--sources", "cache/state.duckdb"])
        self.assertEqual(code, 0, out)
        self.assertEqual(out["rows"], [[1]])

    def test_cache_builds_and_stamps_then_check_is_fresh(self):
        self.write("state/queue.csv", "id,done\n1,true\n")
        self.write(".gitignore", ".duckrunner/\n")
        self.write("duckrunner.json", json.dumps({"caches": [
            {"name": "queue", "sources": ["state/queue.csv"]}]}))
        self.commit()
        code, out = run_main(["cache", "--repo", str(self.repo)])
        self.assertEqual(code, 0, out)
        self.assertEqual(out["caches"][0]["rows"], 1)
        code, out = run_main(["check", "--repo", str(self.repo)])
        rule = next(r for r in out["rules"] if r["rule"] == "caches match their sources")
        self.assertEqual(rule["items"][0]["status"], "fresh")


if __name__ == "__main__":
    unittest.main()
