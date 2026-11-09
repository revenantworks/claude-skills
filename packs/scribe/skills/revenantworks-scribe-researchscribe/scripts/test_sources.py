"""Tests for block_log.py and source_eval.py (stdlib unittest).

Run: python -m unittest discover -s scripts -p "test_*.py"   (from the skill folder)
"""
import contextlib
import io
import json
import os
import re
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import block_log  # noqa: E402
import source_eval  # noqa: E402

PROBE = os.path.join(SKILL, "evals", "fixtures", "probe-2026-11-09.json")
HEALTH = os.path.join(SKILL, "references", "route-health.json")
ROUTES_MD = os.path.join(SKILL, "references", "source-routes.md")


class BlockLogHosts(unittest.TestCase):
    def test_bare_host_accepted_and_lowered(self):
        self.assertEqual(block_log.clean_host("PubMed.NCBI.nlm.nih.gov"), "pubmed.ncbi.nlm.nih.gov")

    def test_anything_but_a_host_refused(self):
        for bad in ("https://example.org", "example.org/path", "example.org?q=1",
                    "user@example.org", "example.org:443", "a b.org", "localhost", ""):
            with self.assertRaises(ValueError, msg=bad):
                block_log.clean_host(bad)

    def test_unknown_code_refused(self):
        with self.assertRaises(ValueError):
            block_log.entry("example.org", "BLOCKED_MAYBE")

    def test_zero_count_refused(self):
        with self.assertRaises(ValueError):
            block_log.entry("example.org", "HTTP_403", 0)


class BlockLogFile(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "sub", "log.jsonl")

    def tearDown(self):
        self.dir.cleanup()

    def test_lines_hold_only_four_fields(self):
        block_log.append([block_log.entry("arxiv.org", "ROBOTS_REFUSED", 2, "2026-11-09")], self.path)
        with open(self.path, encoding="utf-8") as fh:
            line = json.loads(fh.readline())
        self.assertEqual(sorted(line), ["code", "d", "host", "n"])

    def test_report_counts_and_flags(self):
        rows = [block_log.entry("pubmed.ncbi.nlm.nih.gov", "BOT_CHALLENGE", 3, "2026-11-08"),
                block_log.entry("nvd.nist.gov", "JS_EMPTY", 1, "2026-11-08"),
                block_log.entry("old.example.org", "HTTP_403", 9, "2026-01-01")]
        block_log.append(rows, self.path)
        text = block_log.report(block_log.read(self.path), 30, "2026-11-09")
        self.assertIn("pubmed.ncbi.nlm.nih.gov: 3 refusal(s)", text)
        self.assertIn("add a route", text)
        self.assertIn("nvd.nist.gov: 0 refusal(s), 1 other", text)
        self.assertNotIn("old.example.org", text)

    def test_malformed_lines_skipped(self):
        os.makedirs(os.path.dirname(self.path))
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write('{"d": "2026-11-09", "host": "https://x.org/p", "code": "HTTP_403", "n": 1}\n')
            fh.write("not json\n")
            fh.write('{"d": "2026-11-09", "host": "x.org", "code": "HTTP_403", "n": 1}\n')
        self.assertEqual(len(block_log.read(self.path)), 1)

    def test_ingest_workflow_block_stats(self):
        result = {"date": "2026-11-09", "block_stats": {"by_host": {
            "export.arxiv.org": {"ROBOTS_REFUSED": 1}, "www.ebi.ac.uk": {"HTTP_429": 2}}}}
        rows = block_log.from_workflow(result)
        self.assertEqual([(r["host"], r["code"], r["n"]) for r in rows],
                         [("export.arxiv.org", "ROBOTS_REFUSED", 1), ("www.ebi.ac.uk", "HTTP_429", 2)])


class ProbeFixture(unittest.TestCase):
    def setUp(self):
        self.rows = source_eval.load(PROBE)

    def test_fixture_has_every_set(self):
        groups = {(r["round"], r["set"]) for r in self.rows}
        for g in [("r1", "search"), ("r1", "primary-html"), ("r1", "naive-api"),
                  ("validation", "search"), ("validation", "routed")]:
            self.assertIn(g, groups)

    def test_ids_unique(self):
        ids = [r["id"] for r in self.rows]
        self.assertEqual(len(ids), len(set(ids)))

    def test_routed_beats_primary_first_on_blocks(self):
        before = source_eval.stats(source_eval.select(self.rows, ["r1:primary-html", "r1:naive-api"]))
        after = source_eval.stats(source_eval.select(self.rows, ["validation:routed"]))
        self.assertLess(after["block_rate"], before["block_rate"])
        self.assertLessEqual(after["refusal_rate"], before["refusal_rate"])

    def test_routed_beats_search_on_quality(self):
        before = source_eval.stats(source_eval.select(self.rows, ["validation:search"]))
        after = source_eval.stats(source_eval.select(self.rows, ["validation:routed"]))
        self.assertGreater(after["reads_tier_1_2"], before["reads_tier_1_2"])
        self.assertEqual(after["reads_tier_5"], 0.0)

    def test_compare_gate_exit_codes(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(source_eval.cmd_compare(PROBE, "r1:primary-html,r1:naive-api", "validation:routed", True), 0)
            self.assertEqual(source_eval.cmd_compare(PROBE, "validation:routed", "r1:naive-api", True), 1)

    def test_stats_math(self):
        rows = [{"outcome": "OK", "tier": 1}, {"outcome": "OK", "tier": 5},
                {"outcome": "ROBOTS_REFUSED", "tier": 1}, {"outcome": "JS_EMPTY", "tier": 1}]
        s = source_eval.stats(rows)
        self.assertEqual((s["block_rate"], s["refusal_rate"], s["reads_tier_1_2"], s["reads_tier_5"]),
                         (50.0, 25.0, 50.0, 50.0))


class RouteHealth(unittest.TestCase):
    def setUp(self):
        with open(HEALTH, encoding="utf-8") as fh:
            self.health = json.load(fh)
        self.probe = {r["id"]: r for r in source_eval.load(PROBE)}

    def test_route_lint_clean(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(source_eval.cmd_routes(HEALTH), 0)

    def test_probe_ids_exist_and_match_status(self):
        for fam in self.health["families"]:
            for kind in ("first", "avoid"):
                for route in fam[kind]:
                    for pid in route["probes"]:
                        self.assertIn(pid, self.probe, f"{route['pattern']}: probe {pid} missing")
                    outs = {self.probe[p]["outcome"] for p in route["probes"]}
                    if route["status"] == "ok":
                        self.assertEqual(outs, {"OK"}, route["pattern"])
                    if kind == "avoid":
                        self.assertNotIn("OK", outs, route["pattern"])

    def test_no_avoid_host_is_a_first_route_in_the_table(self):
        with open(ROUTES_MD, encoding="utf-8") as fh:
            text = fh.read()
        table = text.split("## 3.", 1)[1].split("## 4.", 1)[0]
        for row in table.splitlines():
            if not row.startswith("| ") or row.startswith("| Family") or row.startswith("|---"):
                continue
            cells = [c.strip() for c in row.strip("|").split("|")]
            first = cells[1]
            for fam in self.health["families"]:
                for route in fam["avoid"]:
                    prefix = re.sub(r"^https://(www\.)?", "", route["pattern"]).split("<")[0].split("?")[0]
                    self.assertNotIn(f"`{prefix}", first, f"avoid route {prefix} in first routes: {row}")

    def test_stamps_agree(self):
        with open(ROUTES_MD, encoding="utf-8") as fh:
            head = fh.read(400)
        self.assertIn(f"Last verified: {self.health['last_verified']}", head)


if __name__ == "__main__":
    unittest.main()
