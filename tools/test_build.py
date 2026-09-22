#!/usr/bin/env python3
"""Unit tests for build.py's registry parsers — the single point every manifest
derives from. Guards the regex-table bug class that has bitten twice: the
budgets table matching the roster regex (16 = 16 = 16 on an eight-member pack)
and the parser edits that shipped unexercised ("unit blindness").

Run: python3 -m unittest discover -s tools -p "test_*.py"
Stdlib only, no fixtures on disk — the synthetic registry below is the fixture.
"""
import unittest

import build

SYNTH = """# Pack Registry

## Build defaults

| Parameter | Value |
|---|---|
| Brand token *(label)* | `revenantworks` |

## Pack registry

| Pack | Profile | Notes |
|---|---|---|
| `demo` | standalone | Test pack. Conformance checks (2026-01-02): D-1 first · D-2 second. Integrate policy: restamp: lazy |
| `other` | standalone | Second pack, no conformance line of its own |

**demo members**

| Member | Job | Route there when |
|---|---|---|
| `revenantworks-demo-alpha` | Does alpha | The deliverable is alpha |
| `revenantworks-demo-beta` | Does beta | The deliverable is beta |

**demo budgets**

| Member | Tokens | Why it earns the room |
|---|---|---|
| `revenantworks-demo-alpha` | 3000 | reasons |
| `revenantworks-demo-beta` | 2000 | reasons |

**demo seams**

| Seam | Left owns | Right owns | Router keys on | Cold-listing signal |
|---|---|---|---|---|
| alpha ↔ beta | the alpha half | the beta half | the object | both descriptions |

**demo capstone:** none.

**demo canonical repo:** `github.com/example/demo`
"""


class RegistryParsers(unittest.TestCase):
    def test_registry_packs(self):
        # Documented quirk: the parser scans everything after "## Pack registry",
        # so backticked member/budget rows are collected too — harmless because
        # downstream treats an empty members table as "not a pack". The contract
        # under test: the real pack row parses with its profile intact.
        packs = build.registry_packs(SYNTH)
        self.assertEqual(packs["demo"], "standalone")

    def test_pack_members_stops_before_budgets(self):
        # The budgets table's rows also match `| `name` | x | y |` — the roster
        # parser must stop at the budgets marker or every member counts twice.
        members = build.pack_members(SYNTH, "demo")
        self.assertEqual([m[0] for m in members],
                         ["revenantworks-demo-alpha", "revenantworks-demo-beta"])

    def test_pack_budgets(self):
        budgets = build.pack_budgets(SYNTH, "demo")
        self.assertEqual(budgets["revenantworks-demo-alpha"][0], 3000)
        self.assertEqual(budgets["revenantworks-demo-beta"][0], 2000)

    def test_pack_seams(self):
        seams = build.pack_seams(SYNTH, "demo")
        self.assertEqual(len(seams), 1)
        self.assertEqual(seams[0][:2], ("alpha", "beta"))
        self.assertEqual(seams[0][5], "both descriptions")

    def test_unknown_pack_is_empty(self):
        self.assertEqual(build.pack_members(SYNTH, "nope"), [])

    def test_registry_pack_notes_is_per_pack(self):
        # The Notes cell, not the Profile cell — pack_lines reads conformance from here.
        self.assertIn("Conformance checks (2026-01-02)", build.registry_pack_notes(SYNTH, "demo"))
        self.assertNotIn("Conformance", build.registry_pack_notes(SYNTH, "other"))
        self.assertEqual(build.registry_pack_notes(SYNTH, "nope"), "")

    def test_pack_lines_does_not_borrow_another_packs_conformance(self):
        # The bug the second pack exposed (2026-08-07): pack_lines was handed the
        # Profile cell, never matched, and fell through to a whole-document search
        # that returns the FIRST pack's conformance line — so pack #2's manifest was
        # stamped with pack #1's checks. A pack with no line of its own must get the
        # stated default, never a neighbour's.
        _, _, (adopted, checks) = build.pack_lines(SYNTH, "demo", build.registry_pack_notes(SYNTH, "demo"))
        self.assertEqual((adopted, checks), ("2026-01-02", "D-1 first · D-2 second"))
        _, _, other = build.pack_lines(SYNTH, "other", build.registry_pack_notes(SYNTH, "other"))
        self.assertEqual(other, build.DEFAULT_CHECKS)


class LiveRegistry(unittest.TestCase):
    """The real registry, parsed with the real parsers — count integrity at
    the unit level, independent of --check's aggregate run."""

    @classmethod
    def setUpClass(cls):
        cls.text = build.registry_text()

    def test_foundation_registered(self):
        self.assertIn("foundation", build.registry_packs(self.text))

    def test_roster_budgets_agree(self):
        members = {m[0] for m in build.pack_members(self.text, "foundation")}
        budgets = set(build.pack_budgets(self.text, "foundation"))
        self.assertEqual(members, budgets)
        # 10 -> 11 at resumewright's 1.0.0 build (2026-09-11, estate-audit unit H2).
        self.assertEqual(len(members), 11)

    def test_seams_reference_roster_members(self):
        members = {m[0].split("-")[-1] for m in build.pack_members(self.text, "foundation")}
        for seam in build.pack_seams(self.text, "foundation"):
            self.assertIn(seam[0], members, seam[:2])
            self.assertIn(seam[1], members, seam[:2])

    def test_each_pack_has_its_own_conformance_line(self):
        # Guards the borrowed-conformance bug on the LIVE registry, not just the fixture:
        # every registered pack carries a conformance line of its own. The cross-pack half
        # — two packs must not resolve to the same (adopted, checks) pair by accident —
        # needs two live packs; with one registered it is carried by the SYNTH fixture in
        # test_pack_lines_does_not_borrow_another_packs_conformance. Add the second name to
        # the tuple the moment a second pack lands and the pairwise check returns for free.
        seen = {}
        for pack in ("foundation",):
            notes = build.registry_pack_notes(self.text, pack)
            self.assertIn("Conformance checks (", notes, pack)
            seen[pack] = build.pack_lines(self.text, pack, notes)[2]
        self.assertEqual(len(set(seen.values())), len(seen), "two packs share one conformance line")


class BumpMember(unittest.TestCase):
    """--bump-member moves every file a member bump's gate forces to move, in one stroke
    (observation #0129: a refresh said "patch bump" and never named the eval re-anchor
    build.py --check fails without; the same gap produced dispatchwright 1.2.10)."""

    SKILL = '---\nname: revenantworks-demo-alpha\nmetadata:\n  version: "1.0.0"\n---\n\n# alpha\n'
    TRIGGER = ("# Trigger evals\n\nProvenance: authored at member version 1.0.0. "
               "**Re-anchored to v1.0.0, 2026-01-01.**\n\n## Should fire\n")
    CASES = "# Assertion Suite\r\n\r\n> **Provenance:** target v1.0.0\r\n\r\n## Case 1\r\n"
    RESULTS = "# Results\n\nRun at v0.9.0.\n"

    def make(self, clog: str) -> "Path":
        import shutil
        import tempfile
        from pathlib import Path
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, True)
        (root / "evals").mkdir()
        (root / "SKILL.md").write_bytes(self.SKILL.encode())
        (root / "CHANGELOG.md").write_bytes(clog.encode())
        (root / "evals" / "trigger-evals.md").write_bytes(self.TRIGGER.encode())
        (root / "evals" / "test-cases.md").write_bytes(self.CASES.encode())
        (root / "evals" / "RESULTS.md").write_bytes(self.RESULTS.encode())
        return root

    def gate_problems(self, root, ver):
        before = len(build.problems)
        build.validate_evals(root, ver)
        new = build.problems[before:]
        del build.problems[before:]
        return new

    def test_unreleased_heading_becomes_the_version(self):
        root = self.make("# Changelog\n\n## [Unreleased]\n\n- staged fix\n\n## [1.0.0] — 2026-01-01\n")
        self.assertEqual(build.bump_member(root, "1.1.0", "staged batch installed", "2026-09-22"), 0)
        self.assertIn('version: "1.1.0"', (root / "SKILL.md").read_text(encoding="utf-8"))
        clog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("## [1.1.0] — 2026-09-22\n\n- staged fix", clog)
        self.assertNotIn("Unreleased", clog)
        self.assertEqual(self.gate_problems(root, "1.1.0"), [])

    def test_unbracketed_unreleased_heading_is_renamed_too(self):
        root = self.make("# Changelog\n\n## Unreleased\n\n- staged fix\n\n## [1.0.0] — 2026-01-01\n")
        build.bump_member(root, "1.1.0", "r", "2026-09-22")
        clog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("## [1.1.0] — 2026-09-22\n\n- staged fix", clog)
        self.assertEqual(clog.count("## ["), 2)

    def test_no_unreleased_scaffolds_a_heading_with_the_reason(self):
        root = self.make("# Changelog\n\n## [1.0.0] — 2026-01-01\n\n- first\n")
        build.bump_member(root, "1.0.1", "model row refreshed", "2026-09-22")
        clog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertLess(clog.index("## [1.0.1] — 2026-09-22"), clog.index("## [1.0.0]"))
        self.assertIn("- model row refreshed", clog)

    def test_evals_re_anchored_line_endings_kept_results_untouched(self):
        root = self.make("# Changelog\n\n## [1.0.0] — 2026-01-01\n")
        self.assertEqual(len(self.gate_problems(root, "1.0.1")), 2)  # the gate this closes
        build.bump_member(root, "1.0.1", "model row refreshed", "2026-09-22")
        self.assertEqual(self.gate_problems(root, "1.0.1"), [])
        cases = (root / "evals" / "test-cases.md").read_bytes()
        self.assertEqual(cases.count(b"\r\n"), cases.count(b"\n"), "CRLF file came back mixed")
        self.assertIn(b"Re-anchored to v1.0.1, 2026-09-22", cases)
        self.assertEqual((root / "evals" / "RESULTS.md").read_text(encoding="utf-8"), self.RESULTS)

    def test_idempotent(self):
        root = self.make("# Changelog\n\n## [1.0.0] — 2026-01-01\n")
        build.bump_member(root, "1.0.1", "r", "2026-09-22")
        snap = {p: p.read_bytes() for p in root.rglob("*.md")}
        build.bump_member(root, "1.0.1", "r", "2026-09-22")
        self.assertEqual({p: p.read_bytes() for p in root.rglob("*.md")}, snap)

    def test_rejects_a_bad_version(self):
        root = self.make("# Changelog\n\n## [1.0.0] — 2026-01-01\n")
        self.assertEqual(build.bump_member(root, "1.0", "r", "2026-09-22"), 1)
        self.assertIn('version: "1.0.0"', (root / "SKILL.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
