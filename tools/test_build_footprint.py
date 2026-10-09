#!/usr/bin/env python3
"""Unit tests for the footprint counter (run 2026-09-28-pack-split, unit P1e2; owner answer to P1b's
open question on observation 0223): `--footprint` and the per-member budget check count every file
EVERY entry reads on every run, whatever form the Load budget states it in. Before this, only a
bullet that opened with the backticked path and the words "every run" counted, so a prose line
("Every run touches `x.md`."), an "on every run" clause, an "Every mode reads" line, or a file read
by every row of an entry table was invisible, and the member read as having headroom it did not.

Run: python3 -m unittest discover -s tools -p "test_*.py"
Stdlib only. Fixtures are written to temp directories.
"""
import unittest

import build
from test_build_split import capture
from test_build_t2 import foot_root


def member_with(test: unittest.TestCase, load_budget: str, files: dict, budget: int = 5000):
    """A one-member pack whose `## Load budget` section is `load_budget`; `files` maps a path
    under the member folder to its size in tokens (chars/4)."""
    root = foot_root(test, budget)
    member = root / "packs" / "tools" / "skills" / "acme-tools-hammerwright"
    body = "# hammerwright\n\nHit the nail.\n\n## Load budget\n\n" + load_budget + "\n\n## Steps\n\nHit it.\n"
    (member / "SKILL.md").write_bytes(("---\nname: acme-tools-hammerwright\ndescription: Hammers nails.\n"
                                       "metadata:\n  version: \"1.0.0\"\n---\n\n" + body).encode())
    for rel, tokens in files.items():
        p = member / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(("abcd" * tokens).encode())
    return root, member


def refs_of(member) -> list:
    out, _, _ = capture(build.every_run_refs, member)
    return [r for r, _ in out]


class EveryRunProseForms(unittest.TestCase):
    def test_prose_sentence_counts_only_its_own_file(self):
        _, m = member_with(self, "Every run touches `eval-doctrine.md`. Open `claim-cases.md` on a generate; "
                                 "`pack.md` only on boundary doubt.",
                           {"references/eval-doctrine.md": 100, "references/claim-cases.md": 900})
        self.assertEqual(refs_of(m), ["references/eval-doctrine.md"])

    def test_on_every_run_clause(self):
        _, m = member_with(self, "`references/verification.md` on every run, plus the entry's files:\n\n"
                                 "Open `references/verdict-mode.md` for a verdict.",
                           {"references/verification.md": 100, "references/verdict-mode.md": 100})
        self.assertEqual(refs_of(m), ["references/verification.md"])

    def test_every_mode_and_every_entry(self):
        _, m = member_with(self, "Every mode reads `references/shapes.md` before a command. `scope` reads "
                                 "`references/scope.md`.\n\nEvery entry opens `rules.md`.",
                           {"references/shapes.md": 10, "references/scope.md": 10, "references/rules.md": 10})
        self.assertEqual(refs_of(m), ["references/shapes.md", "references/rules.md"])

    def test_prose_wrapped_over_lines_and_semicolon_clause(self):
        _, m = member_with(self, "Every run touches `def.md` (the roster, plus the primary\nidentity); a selected "
                                 "sibling opens `def-<slug>.md` in addition.",
                           {"references/def.md": 50})
        self.assertEqual(refs_of(m), ["references/def.md"])

    def test_negated_every_run_is_not_counted(self):
        _, m = member_with(self, "`release.md` is not read on every run. `audit.md` is never every run.",
                           {"references/release.md": 10, "references/audit.md": 10})
        self.assertEqual(refs_of(m), [])

    def test_bullet_form_still_counts_and_files_count_once(self):
        _, m = member_with(self, "- `references/band.md` — every run: the numbers\n"
                                 "- `references/look.md` — `test` only\n\nEvery run reads `band.md` too.",
                           {"references/band.md": 10, "references/look.md": 10})
        self.assertEqual(refs_of(m), ["references/band.md"])

    def test_missing_file_warns(self):
        _, m = member_with(self, "Every run touches `gone.md`.", {})
        out, _, warns = capture(build.every_run_refs, m)
        self.assertEqual(out, [])
        self.assertTrue(any("gone.md" in w for w in warns), warns)


class EveryRunTables(unittest.TestCase):
    TABLE = ("| Entry | Reads |\n|---|---|\n"
             "| `sweep` | `source-map.md`, `diffing.md`, `output.md` |\n"
             "| `watch` | `source-map.md` (that area's rows), `output.md` |\n"
             "| `adopt` | `output.md` (+ `diffing.md` on a fork) |\n")

    def test_a_file_in_every_row_counts(self):
        _, m = member_with(self, self.TABLE, {"references/source-map.md": 10, "references/diffing.md": 10,
                                              "references/output.md": 10})
        self.assertEqual(refs_of(m), ["references/output.md"])

    def test_a_file_missing_from_one_row_does_not(self):
        table = self.TABLE + "| `sources` | `source-map.md` |\n"
        _, m = member_with(self, table, {"references/source-map.md": 10, "references/diffing.md": 10,
                                         "references/output.md": 10})
        self.assertEqual(refs_of(m), [])

    def test_a_single_row_table_proves_nothing(self):
        _, m = member_with(self, "| Entry | Reads |\n|---|---|\n| `go` | `only.md` |\n", {"references/only.md": 10})
        self.assertEqual(refs_of(m), [])


class BudgetCheckCountsTheLoad(unittest.TestCase):
    """--check (not only --footprint) compares body + every-run files with the registry row."""

    def run_check(self, root):
        from test_build_split import Rooted
        with Rooted(root, check=True):
            return capture(build.main)

    def test_check_warns_when_body_fits_but_load_does_not(self):
        root, _ = member_with(self, "Every run touches `big.md`.", {"references/big.md": 600}, budget=300)
        rc, probs, warns = self.run_check(root)
        self.assertFalse([p for p in probs if "budget" in p], probs)  # the fixture has no pack.md
        over = [w for w in warns if "hammerwright" in w and "every-run" in w]
        self.assertEqual(len(over), 1, warns)
        self.assertIn("references/big.md", over[0])

    def test_check_quiet_when_load_fits(self):
        root, _ = member_with(self, "Every run touches `small.md`.", {"references/small.md": 50}, budget=3000)
        rc, probs, warns = self.run_check(root)
        self.assertFalse([p for p in probs if "budget" in p], probs)  # the fixture has no pack.md
        self.assertFalse([w for w in warns if "hammerwright" in w and "budget" in w], warns)


if __name__ == "__main__":
    unittest.main()
