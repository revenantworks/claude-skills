"""Tests for manuscript.py (lorescribe manuscript mode). Stdlib unittest only; every fixture is
invented text written into a temporary folder.

Run: python -m unittest discover -s <skill>/scripts -p "test_*.py"
"""
import contextlib
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import manuscript  # noqa: E402

CH01 = """# Chapter One

Maren walked the salt road at dawn. Maren had grey eyes, like her mother.

The ferry at Oddwater was late. Maren waited by the weir.

* * *

Toller found her there. Toller sold rope and lies in equal measure.
"""

CH02 = """# Chapter Two

Toller counted coins on the jetty at Oddwater.

Maren did not come back that night.
"""

CH03 = """# Chapter Three

At the inn, Marren looked up. Her brown eyes caught the lamp.

Maren paid Toller for the rope.
"""


def run(argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = manuscript.main(argv)
    return code, out.getvalue()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="lorescribe-ms-")
        self.base = Path(self._tmp.name).resolve()
        self.chapters = self.base / "chapters"
        self.chapters.mkdir()
        for name, text in (("ch01.md", CH01), ("ch02.md", CH02), ("ch03.md", CH03)):
            (self.chapters / name).write_text(text, encoding="utf-8", newline="\n")
        self.ledger_dir = self.base / "bible" / "generated" / "manuscript"
        self.ledger_dir.mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def write_ledger(self, rows, name="ledger.jsonl"):
        path = self.ledger_dir / name
        path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
        return path

    def read_jsonl(self, path):
        return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]


class ChunkTests(Base):
    def test_chunk_writes_plan_with_line_ranges_inside_each_file(self):
        code, _ = run(["chunk", str(self.chapters), "--out", str(self.ledger_dir), "--target", "3000"])
        self.assertEqual(code, 0)
        plan = json.loads((self.ledger_dir / "chunks.json").read_text(encoding="utf-8"))
        self.assertEqual([c["file"] for c in plan["chapters"]], ["ch01.md", "ch02.md", "ch03.md"])
        for ch in plan["chapters"]:
            self.assertEqual(ch["sha256"], sha(self.chapters / ch["file"]))
        for c in plan["chunks"]:
            n = len((self.chapters / c["file"]).read_text(encoding="utf-8").splitlines())
            self.assertTrue(1 <= c["start_line"] <= c["end_line"] <= n)

    def test_chunk_never_cuts_a_paragraph(self):
        para = " ".join(["The barge drifted past the reed beds while the crew sang."] * 12)
        text = "\n\n".join([para] * 10) + "\n"
        (self.chapters / "ch04.md").write_text(text, encoding="utf-8")
        run(["chunk", str(self.chapters), "--out", str(self.ledger_dir), "--target", "300"])
        plan = json.loads((self.ledger_dir / "chunks.json").read_text(encoding="utf-8"))
        lines = text.splitlines()
        ch4 = [c for c in plan["chunks"] if c["file"] == "ch04.md"]
        self.assertGreater(len(ch4), 1)
        for c in ch4:
            self.assertNotEqual(lines[c["start_line"] - 1].strip(), "")
            if c["start_line"] > 1:
                self.assertEqual(lines[c["start_line"] - 2].strip(), "")

    def test_smaller_target_gives_more_chunks(self):
        para = " ".join(["Toller sold rope at Oddwater and counted every coin twice."] * 10)
        (self.chapters / "ch04.md").write_text("\n\n".join([para] * 40) + "\n", encoding="utf-8")
        run(["chunk", str(self.chapters), "--out", str(self.ledger_dir), "--target", "1200"])
        small = len(json.loads((self.ledger_dir / "chunks.json").read_text(encoding="utf-8"))["chunks"])
        run(["chunk", str(self.chapters), "--out", str(self.ledger_dir), "--target", "3000"])
        large = len(json.loads((self.ledger_dir / "chunks.json").read_text(encoding="utf-8"))["chunks"])
        self.assertGreater(small, large)

    def test_name_list_counts_repeated_capitalised_names_and_skips_common_words(self):
        run(["chunk", str(self.chapters), "--out", str(self.ledger_dir)])
        plan = json.loads((self.ledger_dir / "chunks.json").read_text(encoding="utf-8"))
        names = {n["name"]: n for n in plan["names"]}
        self.assertIn("Maren", names)
        self.assertIn("Toller", names)
        self.assertEqual(names["Maren"]["first"], "ch01.md:3")
        self.assertNotIn("The", names)
        self.assertNotIn("Her", names)

    def test_single_manuscript_file_splits_on_chapter_lines_and_headings(self):
        book = self.base / "book.md"
        book.write_text(
            "# Prologue\n\nThe weir was old.\n\nChapter 1\n\nMaren woke.\n\nChapter 2\n\nToller sold rope.\n",
            encoding="utf-8")
        run(["chunk", str(book), "--out", str(self.ledger_dir)])
        plan = json.loads((self.ledger_dir / "chunks.json").read_text(encoding="utf-8"))
        self.assertEqual([u["start_line"] for u in plan["units"]], [1, 5, 9])
        self.assertEqual({c["file"] for c in plan["chunks"]}, {"book.md"})

    def test_natural_file_order(self):
        (self.chapters / "ch10.md").write_text("Maren slept.\n", encoding="utf-8")
        (self.chapters / "ch2.md").write_text("Toller woke.\n", encoding="utf-8")
        run(["chunk", str(self.chapters), "--out", str(self.ledger_dir)])
        files = [c["file"] for c in json.loads((self.ledger_dir / "chunks.json").read_text(encoding="utf-8"))["chapters"]]
        self.assertLess(files.index("ch2.md"), files.index("ch10.md"))

    def test_refuses_to_write_into_the_chapters_folder(self):
        code, _ = run(["chunk", str(self.chapters), "--out", str(self.chapters)])
        self.assertEqual(code, 2)
        self.assertFalse((self.chapters / "chunks.json").exists())

    def test_refuses_to_write_inside_the_chapters_folder(self):
        code, _ = run(["chunk", str(self.chapters), "--out", str(self.chapters / "ledger")])
        self.assertEqual(code, 2)
        self.assertFalse((self.chapters / "ledger").exists())

    def test_refuses_to_write_over_the_manuscript_file(self):
        book = self.base / "book.md"
        book.write_text("Chapter 1\n\nMaren woke.\n", encoding="utf-8")
        before = sha(book)
        code, _ = run(["chunk", str(book), "--out", str(book)])
        self.assertEqual(code, 2)
        self.assertEqual(sha(book), before)


class GroundTests(Base):
    def test_quote_on_its_line_is_grounded_and_absent_quote_is_ungrounded(self):
        led = self.write_ledger([
            {"entity": "Maren", "kind": "character", "field": "eyes", "value": "grey",
             "at": "ch01.md:3", "quote": "Maren had grey eyes"},
            {"entity": "Maren", "kind": "character", "field": "hair", "value": "red",
             "at": "ch01.md:3", "quote": "her red hair"},
        ])
        before = sha(self.chapters / "ch01.md")
        code, out = run(["ground", str(led), "--root", str(self.chapters)])
        self.assertEqual(code, 1)
        self.assertIn("UNGROUNDED", out)
        self.assertEqual(len(self.read_jsonl(self.ledger_dir / "grounded.jsonl")), 1)
        bad = self.read_jsonl(self.ledger_dir / "ungrounded.jsonl")
        self.assertEqual(bad[0]["field"], "hair")
        self.assertEqual(sha(self.chapters / "ch01.md"), before)

    def test_whole_word_match_only(self):
        led = self.write_ledger([{"entity": "Maren", "field": "eyes", "value": "gre",
                                  "at": "ch01.md:3", "quote": "had gre"}])
        code, _ = run(["ground", str(led), "--root", str(self.chapters)])
        self.assertEqual(code, 1)

    def test_curly_quotes_and_spacing_fold(self):
        (self.chapters / "ch05.md").write_text("Toller said “the  weir’s” gone.\n", encoding="utf-8")
        led = self.write_ledger([{"entity": "Toller", "field": "said", "value": "weir gone",
                                  "at": "ch05.md:1", "quote": "said \"the weir's\" gone"}])
        code, _ = run(["ground", str(led), "--root", str(self.chapters)])
        self.assertEqual(code, 0)

    def test_path_outside_root_is_ungrounded(self):
        (self.base / "secret.md").write_text("Maren had grey eyes\n", encoding="utf-8")
        led = self.write_ledger([{"entity": "Maren", "field": "eyes", "value": "grey",
                                  "at": "../secret.md:1", "quote": "Maren had grey eyes"}])
        code, out = run(["ground", str(led), "--root", str(self.chapters)])
        self.assertEqual(code, 1)
        self.assertIn("outside", out)


class CollateTests(Base):
    def rows(self):
        return [
            {"entity": "Maren", "kind": "character", "field": "eyes", "value": "grey",
             "at": "ch01.md:3", "quote": "Maren had grey eyes"},
            {"entity": "Maren", "kind": "character", "field": "eyes", "value": "brown",
             "at": "ch03.md:3", "quote": "Her brown eyes caught the lamp"},
            {"entity": "Marren", "kind": "character", "field": "seen", "value": "inn",
             "at": "ch03.md:3", "quote": "At the inn, Marren looked up"},
            {"entity": "Toller", "kind": "character", "field": "state", "value": "alive",
             "at": "ch01.md:9", "quote": "Toller found her there"},
            {"entity": "Toller", "kind": "character", "field": "state", "value": "wounded",
             "at": "ch02.md:3", "quote": "Toller counted coins"},
        ]

    def test_self_contra_carries_both_citations(self):
        led = self.write_ledger(self.rows(), "grounded.jsonl")
        code, out = run(["collate", str(led)])
        self.assertEqual(code, 1)
        line = [x for x in out.splitlines() if x.startswith("SELF-CONTRA")][0]
        self.assertIn("ch01.md:3", line)
        self.assertIn("ch03.md:3", line)
        self.assertIn("maren.eyes", line)

    def test_state_changes_are_not_contradictions(self):
        led = self.write_ledger(self.rows(), "grounded.jsonl")
        _, out = run(["collate", str(led)])
        self.assertNotIn("toller.state", out)

    def test_near_names_flagged_and_never_merged(self):
        led = self.write_ledger(self.rows(), "grounded.jsonl")
        _, out = run(["collate", str(led)])
        self.assertIn("NAME-VARIANT", out)
        col = json.loads((self.ledger_dir / "collated.json").read_text(encoding="utf-8"))
        self.assertIn("maren", col["entities"])
        self.assertIn("marren", col["entities"])

    def test_alias_row_suppresses_name_variant(self):
        rows = self.rows() + [{"entity": "Maren", "field": "alias", "value": "Marren",
                               "at": "ch03.md:3", "quote": "Marren looked up"}]
        led = self.write_ledger(rows, "grounded.jsonl")
        _, out = run(["collate", str(led)])
        self.assertNotIn("NAME-VARIANT", out)

    def test_values_on_different_branches_are_branch_conditional_not_contradictions(self):
        rows = [
            {"entity": "Keep", "kind": "place", "field": "ruler", "value": "Ila",
             "at": "ch01.md:3", "quote": "Maren had grey eyes", "branch": "sided-guild"},
            {"entity": "Keep", "kind": "place", "field": "ruler", "value": "Toller",
             "at": "ch02.md:3", "quote": "Toller counted coins", "branch": "sided-crown"},
        ]
        led = self.write_ledger(rows, "grounded.jsonl")
        code, out = run(["collate", str(led)])
        self.assertNotIn("SELF-CONTRA", out)
        col = json.loads((self.ledger_dir / "collated.json").read_text(encoding="utf-8"))
        self.assertEqual(sorted(col["branch_conditional"][0]["branches"]), ["sided-crown", "sided-guild"])
        self.assertEqual(code, 0)

    def test_unbranched_value_against_branched_value_still_contradicts(self):
        rows = [
            {"entity": "Keep", "field": "ruler", "value": "Ila", "at": "ch01.md:3", "quote": "x"},
            {"entity": "Keep", "field": "ruler", "value": "Toller", "at": "ch02.md:3", "quote": "y",
             "branch": "sided-crown"},
        ]
        led = self.write_ledger(rows, "grounded.jsonl")
        _, out = run(["collate", str(led)])
        self.assertIn("SELF-CONTRA", out)


class RehashTests(Base):
    def test_changed_chapter_listed_and_moved_quote_reanchored(self):
        run(["chunk", str(self.chapters), "--out", str(self.ledger_dir)])
        led = self.write_ledger([
            {"entity": "Maren", "field": "eyes", "value": "brown", "at": "ch03.md:3",
             "quote": "Her brown eyes caught the lamp"},
            {"entity": "Maren", "field": "paid", "value": "Toller", "at": "ch03.md:5",
             "quote": "Maren paid Toller for the rope"},
            {"entity": "Maren", "field": "eyes", "value": "grey", "at": "ch01.md:3",
             "quote": "Maren had grey eyes"},
        ], "grounded.jsonl")
        new = CH03.replace("# Chapter Three\n\n", "# Chapter Three\n\nRain fell all week.\n\n")
        new = new.replace("Maren paid Toller for the rope.", "Maren left without paying.")
        (self.chapters / "ch03.md").write_text(new, encoding="utf-8", newline="\n")
        code, out = run(["rehash", str(self.ledger_dir / "chunks.json"), str(led)])
        self.assertEqual(code, 1)
        summary = json.loads(out)
        self.assertEqual(summary["changed"], ["ch03.md"])
        rows = {r["field"] + r["value"]: r for r in self.read_jsonl(self.ledger_dir / "rehashed.jsonl")}
        self.assertEqual(rows["eyesbrown"]["at"], "ch03.md:5")
        self.assertEqual(rows["eyesbrown"]["status"], "moved")
        self.assertEqual(rows["paidToller"]["status"], "stale")
        self.assertEqual(rows["eyesgrey"]["status"], "kept")


    def test_new_chapter_file_is_listed_for_reading(self):
        run(["chunk", str(self.chapters), "--out", str(self.ledger_dir)])
        led = self.write_ledger([], "grounded.jsonl")
        (self.chapters / "ch04.md").write_text("Maren returned.\n", encoding="utf-8")
        code, out = run(["rehash", str(self.ledger_dir / "chunks.json"), str(led)])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out)["reread"], ["ch04.md"])

    def test_unchanged_book_is_clean(self):
        run(["chunk", str(self.chapters), "--out", str(self.ledger_dir)])
        led = self.write_ledger([], "grounded.jsonl")
        code, _ = run(["rehash", str(self.ledger_dir / "chunks.json"), str(led)])
        self.assertEqual(code, 0)


class SameBranchTests(Base):
    def test_two_values_on_one_branch_contradict(self):
        rows = [
            {"entity": "Keep", "field": "ruler", "value": "Ila", "at": "a.md:1", "quote": "x", "branch": "b1"},
            {"entity": "Keep", "field": "ruler", "value": "Toller", "at": "a.md:2", "quote": "y", "branch": "b1"},
        ]
        led = self.write_ledger(rows, "grounded.jsonl")
        _, out = run(["collate", str(led)])
        self.assertIn("SELF-CONTRA", out)


class CastEvidenceScoreTests(Base):
    def test_cast_proposes_mentions_per_chapter(self):
        led = self.write_ledger([
            {"entity": "Maren", "kind": "character", "field": "eyes", "value": "grey", "at": "ch01.md:3", "quote": "a"},
            {"entity": "Toller", "kind": "character", "field": "trade", "value": "rope", "at": "ch01.md:9", "quote": "b"},
            {"entity": "Oddwater", "kind": "place", "field": "has", "value": "ferry", "at": "ch01.md:5", "quote": "c"},
        ], "grounded.jsonl")
        code, out = run(["cast", str(led)])
        self.assertEqual(code, 0)
        self.assertIn("PROPOSAL 1 · edit · chapters/ch01.md", out)
        self.assertIn("mentions: [maren, toller]", out)
        self.assertNotIn("oddwater", out.split("mentions:")[1].splitlines()[0])

    def test_evidence_reads_story_skills_json_list_or_wrapped(self):
        items = [{"code": "death-recurrence", "file": "chapters/chapter-04.md", "chapter": "chapter-04",
                  "message": "edran-vale appears after death", "severity": "error"},
                 {"code": "promise-unpaid", "file": "plot/promises.md", "message": "p1 unpaid",
                  "severity": "warning", "exemption": "sequel"}]
        for payload in (items, {"diagnostics": items}):
            path = self.base / "report.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            code, out = run(["evidence", str(path)])
            self.assertEqual(code, 1)
            self.assertIn("STORY-SKILLS · death-recurrence · chapters/chapter-04.md", out)
            self.assertIn("dismissed: sequel", out)

    def test_score_reports_recall_and_precision_against_seeded_truth(self):
        led = self.write_ledger([
            {"entity": "Maren", "field": "eyes", "value": "grey", "at": "ch01.md:3", "quote": "a"},
            {"entity": "Tolly", "field": "x", "value": "y", "at": "ch01.md:9", "quote": "b"},
        ], "grounded.jsonl")
        truth = self.base / "truth.json"
        truth.write_text(json.dumps({"entities": [{"name": "Maren"}, {"name": "Toller", "aliases": ["Tolly"]},
                                                  {"name": "Oddwater"}]}), encoding="utf-8")
        code, out = run(["score", str(led), str(truth)])
        self.assertEqual(code, 0)
        res = json.loads(out)
        self.assertAlmostEqual(res["recall"], 2 / 3, places=3)
        self.assertEqual(res["precision"], 1.0)
        self.assertEqual(res["missed"], ["Oddwater"])

    def test_score_allowed_extras_leave_the_extras_count_and_named_key_precision(self):
        led = self.write_ledger([
            {"entity": "Maren", "field": "eyes", "value": "grey", "at": "ch01.md:3", "quote": "a"},
            {"entity": "Brass Key", "field": "holder", "value": "Maren", "at": "ch01.md:5", "quote": "b"},
            {"entity": "Old Pilot", "field": "trade", "value": "pilot", "at": "ch01.md:7", "quote": "c"},
            {"entity": "Gauge Stone", "field": "x", "value": "y", "at": "ch01.md:9", "quote": "d"},
        ], "grounded.jsonl")
        truth = self.base / "truth.json"
        truth.write_text(json.dumps({"entities": [{"name": "Maren"}],
                                     "allowed_extras": ["Brass Key", "old pilot"]}), encoding="utf-8")
        code, out = run(["score", str(led), str(truth)])
        self.assertEqual(code, 0)
        res = json.loads(out)
        self.assertEqual(res["recall"], 1.0)
        self.assertEqual(res["precision"], 0.25)            # every extracted entity counts
        self.assertEqual(res["named_key_precision"], 0.5)   # allowed extras leave the denominator
        self.assertEqual(res["extra"], ["gauge-stone"])
        self.assertEqual(res["allowed_extra"], ["brass-key", "old-pilot"])

    def test_score_without_allowed_extras_named_key_precision_equals_precision(self):
        led = self.write_ledger([
            {"entity": "Maren", "field": "eyes", "value": "grey", "at": "ch01.md:3", "quote": "a"},
            {"entity": "Gauge Stone", "field": "x", "value": "y", "at": "ch01.md:9", "quote": "d"},
        ], "grounded.jsonl")
        truth = self.base / "truth.json"
        truth.write_text(json.dumps({"entities": [{"name": "Maren"}]}), encoding="utf-8")
        code, out = run(["score", str(led), str(truth)])
        res = json.loads(out)
        self.assertEqual(res["precision"], 0.5)
        self.assertEqual(res["named_key_precision"], 0.5)
        self.assertEqual(res["allowed_extra"], [])


class UsageTests(unittest.TestCase):
    def test_no_subcommand_is_usage_error(self):
        code, _ = run([])
        self.assertEqual(code, 2)

    def test_missing_file_is_usage_error(self):
        code, _ = run(["collate", "does-not-exist.jsonl"])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
