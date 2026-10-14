#!/usr/bin/env python3
"""Unit tests for tools/blind_queries.py (run 2026-09-28-pack-split, unit TX).

Covers the five defects a cold re-judge found (T1-T5): --help crashed, a key row naming a
member was read as a query header, the "Request" column was not a query column, TRIGGERS.md
suites were unread, and --all stopped at the first member with no suite. Plus the stated-count
check: a blind list must hold as many rows as its suite says it does.

Run: python3 -m unittest discover -s tools -p "test_*.py"
Stdlib only. Every fixture is written to a temp directory; nothing here touches the repo.
"""
import contextlib
import io
import shutil
import tempfile
import unittest
from pathlib import Path

import blind_queries as bq


def tmpdir(test: unittest.TestCase) -> Path:
    root = Path(tempfile.mkdtemp())
    test.addCleanup(shutil.rmtree, root, True)
    return root


def run_main(argv: list[str]) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    saved = bq.sys.argv
    bq.sys.argv = ["blind_queries.py", *argv]
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = bq.main()
    finally:
        bq.sys.argv = saved
    return rc, out.getvalue(), err.getvalue()


KEY_TABLE_SUITE = (
    "# Trigger Evals — 2 queries (1 should / 1 shouldn't)\n\n"
    "| # | Query | Tag |\n"
    "|---|---|---|\n"
    '| 1 | "write trigger evals for my skill" | explicit |\n'
    '| 2 | "tighten this system prompt" | noisy |\n\n'
    "## Key\n\n"
    "| # | Expected |\n"
    "|---|---|\n"
    "| Q1 | SHOULD |\n"
    "| Q2 | SHOULD NOT — promptwright |\n"
    "| Q3 | SHOULD NOT — input validation, not ours |\n"
)

REQUEST_SUITE = (
    "Balance: 2 should-fire · 1 should-not — 3 in all.\n\n"
    "## Should fire\n\n"
    "| # | Request | Why it lands here |\n"
    "|---|---|---|\n"
    '| 1 | "free up the disk WSL ate" | vhdx compaction |\n'
    '| 2 | "prune old volumes" | prune |\n\n'
    "## Should not fire\n\n"
    "| # | Request | Routes to | Kind |\n"
    "|---|---|---|---|\n"
    '| 3 | "write a Dockerfile for my app" | engineering | near-miss |\n'
)


class HeaderDetection(unittest.TestCase):
    """T2: only a table's first row can be its header, matched as a whole cell."""

    def test_key_row_naming_a_member_is_never_the_header(self):
        skipped: list = []
        got = bq.extract_queries(KEY_TABLE_SUITE, skipped)
        self.assertEqual(got, ['"write trigger evals for my skill"', '"tighten this system prompt"'])
        for leak in ("promptwright", "SHOULD", "input validation"):
            self.assertFalse(any(leak in q for q in got), got)
        self.assertEqual(skipped, [(["#", "Expected"], 3)])

    def test_substring_of_a_header_word_is_not_a_header(self):
        md = ("| # | Prompt engineering note | Expected |\n|---|---|---|\n"
              '| 1 | "x" | yes |\n')
        skipped: list = []
        self.assertEqual(bq.extract_queries(md, skipped), [])
        self.assertEqual(skipped[0][1], 1)

    def test_header_cell_variants_match_whole(self):
        for cell in ("Query", "**Query**", "query?", "Request", "Prompt", "Utterance", "Input"):
            md = f"| # | {cell} | Expected |\n|---|---|---|\n| 1 | hello | yes |\n"
            self.assertEqual(bq.extract_queries(md), ["hello"], cell)

    def test_pair_table_emits_both_sides_as_queries(self):
        """Owner rule 2026-10-01: boundary pairs are judged in full, one query per side,
        with the key column stripped."""
        for header in ("| # | A (fires) | B (does not) | The key |",
                       "| Pair | Request A (fires) | Request B (does not) | The deciding signal |"):
            md = (header + "\n|---|---|---|---|\n"
                  '| P1 | "render it on the GPU" | "draw it by hand" | lease vs art |\n'
                  '| P2 | "free VRAM first" | "buy a GPU" | key two |\n')
            skipped: list = []
            got = bq.extract_queries(md, skipped)
            self.assertEqual(sorted(got), sorted(['"render it on the GPU"', '"draw it by hand"',
                                                  '"free VRAM first"', '"buy a GPU"']), header)
            self.assertEqual(skipped, [])
            blind = bq.render_blind("x", bq.blind_order(got))
            for leak in ("fires", "does not", "lease vs art", "key two", "P1"):
                self.assertNotIn(leak, blind)

    def test_pair_table_beside_a_query_table(self):
        md = ("| # | Request | Why it lands here |\n|---|---|---|\n| 1 | one | x |\n\n"
              "| # | A (fires) | B (does not) | The key |\n|---|---|---|---|\n| P1 | two | three | y |\n")
        self.assertEqual(bq.extract_queries(md), ["one", "two", "three"])


class RequestColumn(unittest.TestCase):
    """T3: "Request" is a query column, and its answer columns never leak."""

    def test_request_suite_reads_every_row(self):
        got = bq.extract_queries(REQUEST_SUITE)
        self.assertEqual(len(got), 3)
        blind = bq.render_blind("x", bq.blind_order(got))
        for leak in ("vhdx", "engineering", "near-miss", "Routes to", "Why it lands here"):
            self.assertNotIn(leak, blind)

    def test_answer_headers_cover_the_suite_census(self):
        for h in ("routes to", "where it belongs", "owner", "why it lands here", "expected owner",
                  "goes to", "kind", "tag", "entry", "native case", "boundary", "owner instead"):
            self.assertIn(h, bq.ANSWER_HEADERS)


class SuiteFiles(unittest.TestCase):
    """T4: TRIGGERS.md is read when trigger-evals.md is absent; T5: --all keeps going."""

    def make_packs(self) -> Path:
        root = tmpdir(self)
        packs = root / "packs"
        a = packs / "alpha" / "skills" / "acme-alpha-onewright" / "evals"
        b = packs / "alpha" / "skills" / "acme-alpha-tworunner" / "evals"
        c = packs / "beta" / "skills" / "acme-beta-threewarden" / "evals"
        for d in (a, b, c):
            d.mkdir(parents=True)
        (a / "trigger-evals.md").write_bytes(KEY_TABLE_SUITE.encode())
        (c / "TRIGGERS.md").write_bytes(REQUEST_SUITE.encode())
        # tworunner has an evals/ folder but no suite at all.
        saved = bq.PACKS
        bq.PACKS = packs
        self.addCleanup(setattr, bq, "PACKS", saved)
        return packs

    def test_triggers_md_is_the_fallback(self):
        packs = self.make_packs()
        folder = packs / "beta" / "skills" / "acme-beta-threewarden"
        self.assertEqual(bq.suite_of(folder).name, "TRIGGERS.md")
        (folder / "evals" / "trigger-evals.md").write_bytes(KEY_TABLE_SUITE.encode())
        self.assertEqual(bq.suite_of(folder).name, "trigger-evals.md")

    def test_all_continues_past_a_member_without_a_suite(self):
        self.make_packs()
        rc, out, err = run_main(["--all"])
        self.assertIn("acme-alpha-onewright", out)
        self.assertIn("acme-beta-threewarden", out)   # after the suiteless member
        self.assertIn("acme-alpha-tworunner", err)
        self.assertIn("no trigger suite", err)
        self.assertEqual(rc, 1)

    def test_counts_mode_reports_matches_and_mismatches(self):
        packs = self.make_packs()
        rc, out, _ = run_main(["--counts"])
        self.assertRegex(out, r"acme-alpha-onewright\s.*\b2\b.*\b2\b.*ok")
        self.assertRegex(out, r"acme-beta-threewarden\s.*\b3\b.*\b3\b.*ok")
        self.assertIn("acme-alpha-tworunner", out)
        self.assertEqual(rc, 1)                       # the suiteless member is a failure
        (packs / "alpha" / "skills" / "acme-alpha-tworunner" / "evals" / "trigger-evals.md").write_bytes(
            b"# Trigger evals - 5 queries\n\n| # | Query |\n|---|---|\n| 1 | a |\n")
        rc, out, _ = run_main(["--counts"])
        self.assertRegex(out, r"acme-alpha-tworunner\s.*\b1\b.*\b5\b.*MISMATCH")
        self.assertEqual(rc, 1)

    def test_probe_rows_in_the_stated_count_are_named_not_failed(self):
        packs = self.make_packs()
        (packs / "alpha" / "skills" / "acme-alpha-tworunner" / "evals" / "trigger-evals.md").write_bytes(
            b"# Trigger evals - 3 queries (1 should / 2 injection probes)\n\n| # | Query |\n|---|---|\n| 1 | a |\n\n"
            b"| # | Handed-in text | Correct handling |\n|---|---|---|\n| 2 | x | y |\n| 3 | x | y |\n")
        rc, out, _ = run_main(["--counts"])
        self.assertIn("ok, 2 outside the list", out)
        self.assertEqual(rc, 0)

    def test_count_in_a_query_row_is_not_the_stated_count(self):
        md = "# Suite\n\n| # | Query |\n|---|---|\n| 1 | the intro says 18 queries but I count 22 |\n"
        self.assertIsNone(bq.stated_count(md))


class StatedCount(unittest.TestCase):
    def test_forms_in_use(self):
        cases = {
            "# Trigger Evals — 34 queries (17 should / 17 shouldn't)\n": 34,
            "- Counts: 31 queries, judged cold\n": 31,
            "Balance: 12 should-fire · 12 should-not (8 near-misses) — 24 in all.\n": 24,
            "Balance: 16 should-fire · 12 should-not · 6 boundary pairs (12 more queries) — 40 in all.\n": 40,
            "Balance: 20 should-fire · 12 should-not · 7 boundary pairs.\n": 46,
            "Balance: 16 should-fire · 12 should-not · 6 boundary pairs.\n": 40,
            "description alone. 10 should fire, 10 should not.\n": 20,
            "column. Twelve should fire, twelve should not; the rest\n": 24,
            "Twenty-two queries, eleven should fire and eleven should not\n": 22,
            "20 queries: 10 should fire, 10 should not.\n": 20,
            "## Should fire (12)\n\n| # | Query |\n\n## Should not fire (11)\n": 23,
            "no number here\n": None,
        }
        for text, want in cases.items():
            self.assertEqual(bq.stated_count(text), want, text)


class Cli(unittest.TestCase):
    """T1: --help prints usage and exits 0 instead of crashing."""

    def test_help(self):
        for flag in ("--help", "-h"):
            rc, out, _ = run_main([flag])
            self.assertEqual(rc, 0)
            self.assertIn("--all", out)

    def test_selftest_passes(self):
        rc, out, _ = run_main(["--selftest"])
        self.assertEqual(rc, 0, out)


class LiveRepo(unittest.TestCase):
    def test_every_live_member_has_a_readable_suite(self):
        rows = bq.count_rows()
        self.assertTrue(rows)
        missing = [r["member"] for r in rows if r["status"] == "no suite"]
        self.assertEqual(missing, [])
        empty = [r["member"] for r in rows if r["routing"] == 0]
        self.assertEqual(empty, [])

    def test_pair_suites_are_read_in_full(self):
        rows = {r["member"].rsplit("-", 1)[-1]: r for r in bq.count_rows()}
        for short in ("comfyrunner", "lmstudiorunner", "shieldwarden"):
            r = rows[short]
            self.assertEqual((r["status"], r["skipped"]), ("ok", 0), r)


if __name__ == "__main__":
    unittest.main()
