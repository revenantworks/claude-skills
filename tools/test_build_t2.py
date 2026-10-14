#!/usr/bin/env python3
"""Unit tests for the build.py follow-up (run 2026-09-28-pack-split, unit T2): observations
0211, 0212, 0221, 0223, 0225, 0227, 0233 and the planned-member seam gap unit M2 hit.

Run: python3 -m unittest discover -s tools -p "test_*.py"
Stdlib only. Fixtures are written to temp directories; the two subprocess tests run the real
build.py against the repo and assert it wrote nothing.
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

import build
from test_build_split import capture, tmpdir

BUILD_PY = Path(build.__file__).resolve()


def _tree_snapshot() -> dict:
    """Size and mtime of every file under the paths build.py and release.py write — packs/,
    featured/, dist/ (gitignored), .claude-plugin/ and the root CHANGELOG.md. Scoped on purpose:
    a rig checkout also holds .dispatch/ and .claude/worktrees/, which other sessions write."""
    out = {}
    roots = [build.ROOT / n for n in ("packs", "featured", "dist", ".claude-plugin")]
    files = [p for r in roots if r.is_dir() for p in r.rglob("*")] + [build.ROOT / "CHANGELOG.md"]
    for p in files:
        if "__pycache__" in p.parts or not p.is_file():
            continue
        st = p.stat()
        out[p.relative_to(build.ROOT).as_posix()] = (st.st_size, st.st_mtime_ns)
    out["<dist exists>"] = (build.ROOT / "dist").exists()
    return out


class ArgParsing(unittest.TestCase):
    """Observation 0212: --help ran a full build and wrote dist zips, an unknown flag fell
    through to the default build, and `--bump-member <m> <v> -m "reason"` wrote a literal
    "-m" into the CHANGELOG."""

    def run_build(self, *args):
        before = _tree_snapshot()
        r = subprocess.run([sys.executable, str(BUILD_PY), *args], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", cwd=str(build.ROOT))
        self.assertEqual(_tree_snapshot(), before, f"build.py {' '.join(args)} wrote to the tree")
        return r

    def test_help_prints_usage_and_writes_nothing(self):
        r = self.run_build("--help")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("usage:", r.stdout)
        self.assertIn("--bump-member", r.stdout)

    def test_unknown_flag_exits_non_zero_and_writes_nothing(self):
        r = self.run_build("--frobnicate")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--frobnicate", r.stderr)

    def test_unknown_flag_inside_bump_member_exits_non_zero(self):
        # In-process on purpose: before the fix this exact argv bumped a real member to 9.9.9
        # with "--frobnicate" as its CHANGELOG reason (seen while writing this test).
        with self.assertRaises(SystemExit) as cm, _quiet():
            build.parse_args(["--bump-member", "revenantworks-foundation-skillwright", "9.9.9", "--frobnicate"])
        self.assertNotEqual(cm.exception.code, 0)

    def test_m_is_a_flag_for_the_reason(self):
        ns = build.parse_args(["--bump-member", "alpha", "1.2.0", "-m", "model row refreshed"])
        self.assertEqual(ns.bump_member, ("alpha", "1.2.0", "model row refreshed"))
        ns = build.parse_args(["--bump-member", "alpha", "1.2.0", "--message", "r"])
        self.assertEqual(ns.bump_member, ("alpha", "1.2.0", "r"))

    def test_positional_reason_still_works(self):
        ns = build.parse_args(["--bump-member", "alpha", "1.2.0", "model row refreshed"])
        self.assertEqual(ns.bump_member, ("alpha", "1.2.0", "model row refreshed"))

    def test_reason_twice_or_missing_is_an_error(self):
        for argv in (["--bump-member", "alpha", "1.2.0", "r", "-m", "r2"],
                     ["--bump-member", "alpha", "1.2.0"],
                     ["--bump-member", "alpha"],
                     ["-m", "orphan reason"]):
            with self.assertRaises(SystemExit) as cm, _quiet():
                build.parse_args(argv)
            self.assertNotEqual(cm.exception.code, 0, argv)

    def test_every_existing_flag_still_parses(self):
        ns = build.parse_args([])
        self.assertEqual((ns.check, ns.parity, ns.footprint, ns.only, ns.bump_pack, ns.bump_member, ns.new_pack),
                         (False, False, False, None, None, None, None))
        self.assertTrue(build.parse_args(["--check"]).check)
        self.assertTrue(build.parse_args(["--parity"]).parity)
        self.assertTrue(build.parse_args(["--footprint"]).footprint)
        self.assertEqual(build.parse_args(["--only", "x"]).only, "x")
        self.assertEqual(build.parse_args(["--bump-pack", "gamedev", "1.3.0"]).bump_pack, ("gamedev", "1.3.0"))
        ns = build.parse_args(["--new-pack", "scribe", "--motif", "scribe", "--profile", "standard"])
        self.assertEqual(ns.new_pack, ("scribe", "scribe", "standard"))
        # --new-pack keeps its own argument errors (new_pack prints them and returns 1).
        self.assertEqual(build.parse_args(["--new-pack", "scribe"]).new_pack, ("scribe", None, None))

    def test_release_help_is_read_only_and_unknown_flag_fails(self):
        release = BUILD_PY.parent / "release.py"
        before = _tree_snapshot()
        r = subprocess.run([sys.executable, str(release), "--help"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", cwd=str(build.ROOT))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("release.py foundation=", r.stdout)
        r = subprocess.run([sys.executable, str(release), "--frobnicate", "--dry-run", "foundation=9.9.9"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(build.ROOT))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--frobnicate", r.stdout + r.stderr)
        self.assertEqual(_tree_snapshot(), before)

    def test_motif_without_new_pack_is_an_error(self):
        with self.assertRaises(SystemExit), _quiet():
            build.parse_args(["--motif", "scribe"])


SKILL_ALPHA = '---\nname: revenantworks-demo-alpha\nmetadata:\n  version: "1.0.0"\n---\n\n# alpha\n'


def member_with_evals(test: unittest.TestCase, evals: dict[str, str]) -> Path:
    root = tmpdir(test)
    (root / "evals").mkdir()
    (root / "SKILL.md").write_bytes(SKILL_ALPHA.encode())
    (root / "CHANGELOG.md").write_bytes(b"# Changelog\n\n## [1.0.0] - 2026-01-01\n")
    for name, text in evals.items():
        (root / "evals" / name).write_bytes(text.encode())
    return root


class BumpMemberExactToken(unittest.TestCase):
    """Observation 0211: the re-anchor skipped a file whose provenance line already carried
    the new version string from a predecessor-era numbering — substring membership was
    satisfied by history. Only the exact token the bump writes counts as re-anchored."""

    OLD_EQUAL = "# Test Cases\n\n- Provenance: derived from the predecessor's v1.3.0 numbering, 2026-06-01.\n- Counts: 3 cases.\n"

    def test_old_equal_version_on_the_line_is_still_re_anchored(self):
        root = member_with_evals(self, {"test-cases.md": self.OLD_EQUAL, "trigger-evals.md": self.OLD_EQUAL})
        build.bump_member(root, "1.3.0", "parity rows applied", "2026-10-01")
        for name in ("test-cases.md", "trigger-evals.md"):
            line = (root / "evals" / name).read_text(encoding="utf-8").splitlines()[2]
            self.assertIn("**Re-anchored to v1.3.0, 2026-10-01:** parity rows applied.", line, name)

    def test_the_written_token_makes_a_rerun_a_no_op(self):
        root = member_with_evals(self, {"test-cases.md": self.OLD_EQUAL})
        build.bump_member(root, "1.3.0", "r", "2026-10-01")
        snap = (root / "evals" / "test-cases.md").read_bytes()
        build.bump_member(root, "1.3.0", "r", "2026-10-02")
        self.assertEqual((root / "evals" / "test-cases.md").read_bytes(), snap)

    def test_in_place_phrase_at_the_new_version_counts_as_current(self):
        text = "# T\n\n- Provenance: derived from x v1.0.0; last re-anchored to v1.3.0, 2026-09-01.\n"
        root = member_with_evals(self, {"test-cases.md": text})
        build.bump_member(root, "1.3.0", "r", "2026-10-01")
        self.assertEqual((root / "evals" / "test-cases.md").read_text(encoding="utf-8"), text)


class BumpMemberAnchorByHeading(unittest.TestCase):
    """Observation 0233 (and 0211's C2 update): the re-anchor note went to a fixed position —
    the last line in the first 16 carrying a provenance word. In a wrapped provenance
    paragraph that is mid-sentence; past the first `## ` heading it is a table row. The anchor
    is now the provenance paragraph inside the file head (before the first `## ` heading), and
    the note goes at that paragraph's end."""

    WRAPPED = ("# Test cases — 2 assertion cases\n"
               "\n"
               "> Provenance: authored at member version v1.0.0, 2026-09-28, when alpha was split out of\n"
               "> its parent. Cases 1 and 2 moved with it; their arithmetic is unchanged.\n"
               "> None has been run (evals/RESULTS.md).\n"
               "\n"
               "## Coverage map\n"
               "\n"
               "| Case | Target behaviour |\n"
               "|---|---|\n"
               "| 1 | derived figure |\n")

    def test_note_lands_at_the_end_of_the_provenance_paragraph(self):
        root = member_with_evals(self, {"test-cases.md": self.WRAPPED})
        build.bump_member(root, "1.0.1", "model row refreshed", "2026-10-01")
        lines = (root / "evals" / "test-cases.md").read_text(encoding="utf-8").splitlines()
        old = self.WRAPPED.splitlines()
        self.assertEqual(lines[2:4], old[2:4], "a wrapped provenance line was split mid-sentence")
        self.assertEqual(lines[4], old[4] + " **Re-anchored to v1.0.1, 2026-10-01:** model row refreshed.")
        self.assertEqual(lines[5:], old[5:], "the note went past the first ## heading")
        _, probs, _ = capture(build.validate_evals, root, "1.0.1")
        self.assertEqual(probs, [])

    def test_no_provenance_in_the_head_is_left_alone(self):
        text = "# T\n\n## Cases\n\n| Case | Target |\n|---|---|\n| 1 | derived v1.0.0 |\n"
        root = member_with_evals(self, {"test-cases.md": text})
        build.bump_member(root, "1.0.1", "r", "2026-10-01")
        self.assertEqual((root / "evals" / "test-cases.md").read_text(encoding="utf-8"), text)


class RosterFromTheTree(unittest.TestCase):
    """Observation 0233's other half: tests read the roster instead of pinning it. Deriving it
    for every pack exposed a parser leak: an empty budgets table read on into the next pack."""

    TWO = ("**scribe members**\n\n| Member | Job | Route there when |\n|---|---|---|\n\n"
           "**scribe budgets**\n\n| Member | Budget (tokens) | Why |\n|---|---|---|\n\n"
           "**scribe capstone:** none.\n\n**scribe canonical repo:** `x`\n\n"
           "**warden members**\n\n| Member | Job | Route there when |\n|---|---|---|\n| `acme-warden-shieldwarden` | j | r |\n\n"
           "**warden budgets**\n\n| Member | Budget (tokens) | Why |\n|---|---|---|\n| `acme-warden-shieldwarden` | 3000 | w |\n")

    def test_empty_budgets_table_does_not_read_the_next_pack(self):
        self.assertEqual(build.pack_budgets(self.TWO, "scribe"), {})
        self.assertEqual(build.pack_budgets(self.TWO, "warden"), {"acme-warden-shieldwarden": (3000, "w")})

    def test_misplaced_old_re_anchor_warns_instead_of_passing_silently(self):
        text = ("# T\n\n- Provenance: derived from x v1.0.0.\n\n## Case 1\n"
                "**Assert:** target met. **Re-anchored to v1.0.1, 2026-09-28:** r.\n")
        root = member_with_evals(self, {"test-cases.md": text})
        _, probs, warns = capture(build.validate_evals, root, "1.0.1")
        self.assertEqual(probs, [])
        self.assertTrue(any("sits past the provenance head" in w for w in warns), warns)


class IdNamespaces(unittest.TestCase):
    """Observation 0305: S<n> names a source, C<n> a case; each is refused in the other's file."""

    def _member(self, evals=None, sources=None):
        root = member_with_evals(self, evals or {"test-cases.md": "# T\n\n**C1 - a case.**\n"})
        if sources is not None:
            (root / "SOURCES.md").write_text(sources, encoding="utf-8")
        return root

    def test_clean_member_is_silent(self):
        root = self._member(sources="| S1 | a source |\n")
        _, probs, warns = capture(build.validate_id_namespaces, root)
        self.assertEqual((probs, warns), ([], []))

    def test_source_id_in_an_eval_file_warns(self):
        root = self._member({"trigger-evals.md": "| S3 | \"query\" | fire |\n"})
        _, probs, warns = capture(build.validate_id_namespaces, root)
        self.assertEqual(probs, [])
        self.assertTrue(any("S3" in w and "trigger-evals.md" in w for w in warns), warns)

    def test_case_id_in_sources_warns(self):
        root = self._member(sources="| C2 | a source |\n")
        _, _, warns = capture(build.validate_id_namespaces, root)
        self.assertTrue(any("C2" in w and "SOURCES.md" in w for w in warns), warns)

    def test_results_ledger_is_exempt(self):
        root = self._member({"RESULTS.md": "| S9 | #21 | PASS |\n"})
        _, _, warns = capture(build.validate_id_namespaces, root)
        self.assertEqual(warns, [])


class VolatileAnchor(unittest.TestCase):
    """Observation 0221: the audit template writes volatile pointers like
    `references/SOURCES.md#parity-register`, and the validator treated the whole string as a
    path. It now strips the `#anchor`, checks the file, then confirms the heading exists.
    (The pointers live in `volatile.json` since owner decision M3, 2026-10-08.)"""

    SOURCES = ("# Sources\n\nIntro.\n\n## Parity register\n\nLast verified: 2026-09-28\n\n"
               "| Incumbent | Margin |\n|---|---|\n\n## Other notes\n\nnothing\n")

    def check(self, entries: list, sources: str = SOURCES):
        root = tmpdir(self)
        (root / "references").mkdir()
        (root / "references" / "SOURCES.md").write_bytes(sources.encode())
        (root / "volatile.json").write_bytes(json.dumps(entries).encode())
        _, probs, _ = capture(build.validate_volatile, root)
        return probs

    @staticmethod
    def ev(ref: str) -> dict:
        return {"file": ref, "class": "event-driven"}

    def test_anchor_to_an_existing_heading_passes(self):
        self.assertEqual(self.check([self.ev("references/SOURCES.md#parity-register")]), [])

    def test_calendar_anchor_reads_the_stamp_at_the_section_head(self):
        self.assertEqual(self.check([{"file": "references/SOURCES.md#parity-register", "class": "calendar",
                                      "cadence_days": 30}]), [])

    def test_anchor_to_a_missing_heading_fails(self):
        probs = self.check([self.ev("references/SOURCES.md#no-such-section")])
        self.assertTrue(any("#no-such-section" in p and "no heading" in p for p in probs), probs)

    def test_missing_file_still_fails(self):
        probs = self.check([self.ev("references/GONE.md#parity-register")])
        self.assertTrue(any("does not exist" in p for p in probs), probs)

    def test_explicit_anchor_ids_count(self):
        src = "# S\n\n## Register {#parity-register}\n\nx\n\n<a id=\"margins\"></a>\nMargins.\n"
        self.assertEqual(self.check([self.ev("references/SOURCES.md#parity-register"),
                                     self.ev("references/SOURCES.md#margins")], src), [])


class PlannedMemberInAPackSeam(unittest.TestCase):
    """The M2 gap: a pack's own seam table may name a member on the registry's **planned:**
    line (it renders as planned); --check fails only a seam member that is neither registered
    nor planned, or one planned for a different pack (that row is a cross-pack seam)."""

    MEMBERS = ["acme-warden-shieldwarden", "acme-warden-gatewarden"]
    SEAM = ("shieldwarden", "probewarden", "the scan", "the identity rules", "scan or rules", "both descriptions")

    def check(self, planned):
        return capture(build.validate_seams, "warden", self.MEMBERS,
                       [self.SEAM, ("shieldwarden", "gatewarden", "a", "b", "k", "both descriptions")], planned)

    def test_planned_member_passes(self):
        for planned in ({"probewarden": None}, {"probewarden": "warden"}):
            _, probs, _ = self.check(planned)
            self.assertEqual(probs, [], planned)

    def test_unregistered_unplanned_member_fails(self):
        _, probs, _ = self.check({})
        self.assertTrue(any("'probewarden'" in p and "neither" in p for p in probs), probs)

    def test_member_planned_for_another_pack_fails(self):
        _, probs, _ = self.check({"probewarden": "scribe"})
        self.assertTrue(any("cross-pack" in p for p in probs), probs)

    def test_renders_as_planned_and_the_manifest_check_counts_it(self):
        members = [(m, "j", "r") for m in self.MEMBERS]
        md = build.render_pack_md("warden", "standard", members, "—", "`x`", build.DEFAULT_CHECKS,
                                  [self.SEAM], planned={"probewarden": None})
        self.assertIn("| shieldwarden ↔ probewarden (planned) | the scan |", md)
        folder = tmpdir(self) / "acme-warden-shieldwarden"
        (folder / "references").mkdir(parents=True)
        (folder / "references" / "pack.md").write_bytes(md.encode())
        _, probs, _ = capture(build.validate_seam_manifest, folder, 1)
        self.assertEqual(probs, [])


REG_COUNTS = """**demo members**

| Member | Job | Route there when |
|---|---|---|
| `acme-demo-alphawright` | a | a |
| `acme-demo-betawright` | b | b |

**demo budgets**

| Member | Budget (tokens) | Why |
|---|---|---|
| `acme-demo-alphawright` | 3000 | w |
| `acme-demo-gonewright` | 2000 | a member that left the roster |

**demo capstone:** {cap}

**demo canonical repo:** `x`

**other members**

| Member | Job | Route there when |
|---|---|---|
| `acme-other-gammasmith` | g | g |
"""


class RegistryCountsAgainstTheRoster(unittest.TestCase):
    """Observation 0227: registry prose drifted from the roster — a capstone line said "ten
    members" with eleven — and budget rows outlived or missed roster changes. --check now
    derives the count and compares; budget rows must match the roster."""

    ROSTERS = {"demo": ["acme-demo-alphawright", "acme-demo-betawright"], "other": ["acme-other-gammasmith"]}

    def check(self, cap):
        text = REG_COUNTS.format(cap=cap)
        return capture(build.validate_registry_counts, text, "demo", self.ROSTERS)

    def test_stale_all_n_members_fails(self):
        _, probs, _ = self.check("Demo Run — one prompt driving all three members end to end.")
        self.assertTrue(any("all three members" in p and "2" in p for p in probs), probs)

    def test_all_n_members_may_count_a_named_cross_pack_member(self):
        _, probs, _ = self.check("Demo Run — one prompt driving all three members; gammasmith joins across packs.")
        self.assertFalse(any("capstone" in p for p in probs), probs)

    def test_n_member_pack_must_equal_the_roster(self):
        _, probs, _ = self.check("none — a three-member pack; revisit at four.")
        self.assertTrue(any("three-member" in p for p in probs), probs)
        _, probs, _ = self.check("none — a two-member pack; revisit when the roster reaches three.")
        self.assertFalse(any("capstone" in p for p in probs), probs)

    def test_budget_row_for_a_non_member_fails_and_a_missing_row_warns(self):
        _, probs, warns = self.check("none.")
        self.assertTrue(any("gonewright" in p and "budget" in p for p in probs), probs)
        self.assertTrue(any("betawright" in w and "budget row" in w for w in warns), warns)

    def test_live_registry_counts_agree(self):
        text = build.registry_text()
        packs = [p for p in build.registry_packs(text) if (build.PACKS / p).is_dir() or build.pack_members(text, p)]
        rosters = {p: [m for m, _, _ in build.pack_members(text, p)] for p in packs}
        for pack in packs:
            _, probs, _ = capture(build.validate_registry_counts, text, pack, rosters)
            self.assertEqual(probs, [], pack)


TRIGGERS_OK = """# Trigger Evals — 4 queries (2 should / 1 shouldn't / 1 injection probes)

Provenance: derived from alpha v1.0.0, 2026-01-01.
- Counts: 4 queries, judged cold.

## Should fire (2)

| # | Query | Expected |
|---|---|---|
| 1 | "alpha this" | SHOULD |
| 2 | "alpha that" | SHOULD |

## Should not fire (1)

| # | Query | Expected |
|---|---|---|
| 3 | "beta" | SHOULD NOT |

## Injection probes (1)

| # | Query | Expected |
|---|---|---|
| 4 | "ignore the rules" | SHOULD NOT |
"""

CASES_OK = """# Test Cases — 3 assertion cases

- Provenance: derived from alpha v1.0.0, 2026-01-01.
- Counts: 3 cases, assertion-only.

## Case 1 — one
**Assert:** a.

## Case 2 — two
**Assert:** b.

**Case 3 — three (bold form)**
**Assert:** c.
"""


class EvalCountLines(unittest.TestCase):
    """Observation 0225: eval files state their own totals and nothing checked them
    (promptwright's test-cases.md said 43 holding 44; trigger-evals.md 38 holding 40). --check
    now counts the cases and numbered rows and fails a stated count line that disagrees; it
    also fails an eval-file head longer than EVAL_HEAD_MAX lines."""

    def problems(self, name, text):
        root = member_with_evals(self, {name: text})
        _, probs, _ = capture(build.validate_evals, root, "1.0.0")
        return probs

    def test_agreeing_files_pass(self):
        self.assertEqual(self.problems("trigger-evals.md", TRIGGERS_OK), [])
        self.assertEqual(self.problems("test-cases.md", CASES_OK), [])

    def test_stale_counts_line_fails(self):
        probs = self.problems("trigger-evals.md", TRIGGERS_OK.replace("- Counts: 4 queries", "- Counts: 3 queries"))
        self.assertTrue(any("states 3" in p and "4 numbered rows" in p for p in probs), probs)
        probs = self.problems("test-cases.md", CASES_OK.replace("- Counts: 3 cases", "- Counts: 2 cases"))
        self.assertTrue(any("states 2" in p and "3 cases" in p for p in probs), probs)

    def test_stale_title_count_and_split_fail(self):
        probs = self.problems("trigger-evals.md", TRIGGERS_OK.replace("— 4 queries (2 should", "— 5 queries (3 should"))
        self.assertTrue(any("title states 5" in p for p in probs), probs)
        probs = self.problems("trigger-evals.md", TRIGGERS_OK.replace("(2 should /", "(3 should /"))
        self.assertTrue(any("split" in p for p in probs), probs)
        probs = self.problems("test-cases.md", CASES_OK.replace("— 3 assertion cases", "— 4 assertion cases"))
        self.assertTrue(any("title states 4" in p for p in probs), probs)

    def test_stale_section_count_fails(self):
        probs = self.problems("trigger-evals.md", TRIGGERS_OK.replace("## Should not fire (1)", "## Should not fire (2)"))
        self.assertTrue(any("Should not fire" in p and "holds 1" in p for p in probs), probs)

    def test_long_head_fails(self):
        head = "\n".join(f"Re-anchor note {i}." for i in range(build.EVAL_HEAD_MAX))
        probs = self.problems("test-cases.md", CASES_OK.replace("- Counts: 3 cases, assertion-only.\n",
                                                                 "- Counts: 3 cases, assertion-only.\n" + head + "\n"))
        self.assertTrue(any("head runs" in p for p in probs), probs)

    def test_unrecognised_layout_is_not_counted(self):
        text = "# Suite\n\nCounts: 41 ordinary cases = **46 cases**.\n\n## A\n\n- **A1** does a thing\n"
        self.assertEqual(self.problems("SUITE.md", text), [])





def foot_root(test: unittest.TestCase, budget: int) -> Path:
    from test_build_split import MINI_REGISTRY, mini_root
    import json
    reg = MINI_REGISTRY.replace(
        "|---|---|---|\n\n## Cross-pack",
        "|---|---|---|\n| `tools` | standalone | Demo pack. |\n\n**tools members**\n\n"
        "| Member | Job | Route there when |\n|---|---|---|\n| `acme-tools-hammerwright` | Hammers | Nails |\n\n"
        f"**tools budgets**\n\n| Member | Budget (tokens) | Why |\n|---|---|---|\n"
        f"| `acme-tools-hammerwright` | {budget} | test |\n\n"
        "**tools capstone:** none.\n\n## Cross-pack")
    root = mini_root(test, reg)
    member = root / "packs" / "tools" / "skills" / "acme-tools-hammerwright"
    (member / "references").mkdir(parents=True)
    body = ("# hammerwright\n\nHit the nail.\n\n## Load budget\n\n"
            "- `references/rules.md` — every run: the nail rules\n"
            "- `references/extra.md` — only on a bent nail\n"
            "- `pack.md` — boundary doubt only\n\n## Steps\n\nHit it.\n")
    (member / "SKILL.md").write_bytes(("---\nname: acme-tools-hammerwright\ndescription: Hammers nails.\n"
                                       "metadata:\n  version: \"1.0.0\"\n---\n\n" + body).encode())
    (member / "volatile.json").write_bytes(b"[]\n")
    (member / "CHANGELOG.md").write_bytes(b"# Changelog\n\n## [1.0.0] - 2026-10-01\n\n- first\n")
    (member / "references" / "rules.md").write_bytes(("rule " * 400).encode())   # 2000 chars ≈ 500 tokens
    (member / "references" / "extra.md").write_bytes(("x " * 4000).encode())
    (root / "packs" / "tools" / ".claude-plugin").mkdir(parents=True)
    (root / "packs" / "tools" / ".claude-plugin" / "plugin.json").write_bytes(b'{"name": "tools", "version": "1.0.0"}\n')
    (root / ".claude-plugin" / "marketplace.json").write_bytes(json.dumps(
        {"name": "acme", "plugins": [{"name": "tools", "source": "./packs/tools", "version": "1.0.0"}]}).encode())
    return root


class FootprintEveryRunReferences(unittest.TestCase):
    """Observation 0223: --footprint counted SKILL.md alone, so a member whose every-run
    reference pushed its real load past the registry budget read as healthy headroom. A
    member lists every-run references in its `## Load budget` section as a bullet that opens
    with the backticked path and the words "every run"; --footprint adds them to the body and
    warns past the budget row. --footprint also no longer writes manifest drift."""

    def run_footprint(self, root):
        from test_build_split import Rooted
        saved = build.FOOTPRINT
        build.FOOTPRINT = True
        try:
            with Rooted(root, check=False):
                return capture(build.main)
        finally:
            build.FOOTPRINT = saved

    def test_every_run_refs_are_parsed_from_the_load_budget(self):
        root = foot_root(self, 5000)
        member = root / "packs" / "tools" / "skills" / "acme-tools-hammerwright"
        refs = build.every_run_refs(member)
        self.assertEqual([r for r, _ in refs], ["references/rules.md"])
        self.assertEqual(refs[0][1], 500)

    def test_footprint_adds_them_and_warns_past_the_budget(self):
        root = foot_root(self, 300)  # body ≈ 60 tokens, under 300; body + rules.md ≈ 560, over it
        rc, probs, warns = self.run_footprint(root)
        self.assertEqual((rc, probs), (0, []))
        over = [w for w in warns if "every-run" in w and "hammerwright" in w]
        self.assertEqual(len(over), 1, warns)
        self.assertIn("references/rules.md", over[0])

    def test_footprint_under_budget_is_quiet_and_writes_nothing(self):
        root = foot_root(self, 5000)
        before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
        rc, probs, warns = self.run_footprint(root)
        self.assertEqual((rc, probs), (0, []))
        self.assertFalse([w for w in warns if "every-run" in w], warns)
        after = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
        self.assertEqual(after, before, "--footprint wrote (pack.md drift is reported, not synced)")


class UnregisteredMemberFolder(unittest.TestCase):
    """Controller item (2026-10-01): --check skipped a member folder under packs/*/skills/ that
    the registry does not list — four build units hit it, and count integrity read 17 = 17 with
    an unregistered folder present. It now fails, and the folder count is read from disk."""

    def clean_root(self) -> Path:
        from test_build_split import Rooted
        root = foot_root(self, 5000)
        with Rooted(root, check=False):
            rc, probs, _ = capture(build.main)  # the real build writes pack.md; check is then clean
        self.assertEqual((rc, probs), (0, []))
        return root

    def check(self, root):
        from test_build_split import Rooted
        import io
        from contextlib import redirect_stdout
        out = io.StringIO()
        with Rooted(root, check=True), redirect_stdout(out):
            rc, probs, _ = capture(build.main)
        return rc, probs, out.getvalue()

    def test_clean_fixture_passes(self):
        rc, probs, _ = self.check(self.clean_root())
        self.assertEqual((rc, probs), (0, []))

    def test_unregistered_folder_in_a_registered_pack_fails(self):
        root = self.clean_root()
        ghost = root / "packs" / "tools" / "skills" / "acme-tools-ghostwright"
        ghost.mkdir()
        (ghost / "SKILL.md").write_bytes(b"---\nname: acme-tools-ghostwright\n---\n")
        rc, probs, out = self.check(root)
        self.assertEqual(rc, 1)
        self.assertTrue(any("acme-tools-ghostwright" in p and "not in the registry" in p for p in probs), probs)
        self.assertIn("registry 1 = folders 2", out)

    def test_member_folder_in_an_unregistered_pack_fails(self):
        root = self.clean_root()
        stray = root / "packs" / "stray" / "skills" / "acme-stray-onewright"
        stray.mkdir(parents=True)
        (stray / "SKILL.md").write_bytes(b"---\nname: acme-stray-onewright\n---\n")
        rc, probs, _ = self.check(root)
        self.assertEqual(rc, 1)
        self.assertTrue(any("acme-stray-onewright" in p and "stray" in p for p in probs), probs)


class _quiet:
    """Swallow argparse's stderr message inside a test."""

    def __enter__(self):
        import io
        self.saved, sys.stderr = sys.stderr, io.StringIO()

    def __exit__(self, *exc):
        sys.stderr = self.saved


if __name__ == "__main__":
    unittest.main()
