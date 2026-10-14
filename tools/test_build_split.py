#!/usr/bin/env python3
"""Unit tests for the five-pack build machinery (run 2026-09-28-pack-split, unit T1):
the two bumper fixes (observations 0220 and 0239), the native plugin-eval layout check,
cross-pack seams, new-pack scaffolding and the featured generator.

Run: python3 -m unittest discover -s tools -p "test_*.py"
Stdlib only. Every fixture is written to a temp directory; nothing here touches the repo.
"""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import build


def tmpdir(test: unittest.TestCase) -> Path:
    root = Path(tempfile.mkdtemp())
    test.addCleanup(shutil.rmtree, root, True)
    return root


def capture(fn, *args, **kwargs):
    """Run fn and return (result, new problems, new warnings), leaving the globals as found."""
    p0, w0 = len(build.problems), len(build.warnings)
    out = fn(*args, **kwargs)
    new_p, new_w = build.problems[p0:], build.warnings[w0:]
    del build.problems[p0:]
    del build.warnings[w0:]
    return out, new_p, new_w


class BumpPackLineEndings(unittest.TestCase):
    """Observation 0220: bump_pack wrote marketplace.json, plugin.json and CHANGELOG.md
    with write_text, which turns LF into CRLF on Windows. Each file keeps its own ending.
    The fixture mixes both endings so the test fails before the fix on either platform."""

    def make(self) -> Path:
        root = tmpdir(self)
        (root / ".claude-plugin").mkdir()
        (root / "packs" / "demo" / ".claude-plugin").mkdir(parents=True)
        cat = {"name": "m", "plugins": [{"name": "demo", "source": "./packs/demo", "version": "1.0.0"}]}
        (root / ".claude-plugin" / "marketplace.json").write_bytes(
            (json.dumps(cat, indent=2) + "\n").encode())                       # LF
        (root / "packs" / "demo" / ".claude-plugin" / "plugin.json").write_bytes(
            (json.dumps({"name": "demo", "version": "1.0.0"}, indent=2) + "\n").replace("\n", "\r\n").encode())  # CRLF
        (root / "CHANGELOG.md").write_bytes(b"# Changelog\n\n## [demo-v1.0.0] - 2026-01-01\n\n- first\n")  # LF
        return root

    def test_each_file_keeps_its_own_line_ending(self):
        root = self.make()
        self.assertEqual(build.bump_pack("demo", "1.1.0", root=root, today="2026-10-01"), 0)
        mkt = (root / ".claude-plugin" / "marketplace.json").read_bytes()
        pj = (root / "packs" / "demo" / ".claude-plugin" / "plugin.json").read_bytes()
        clog = (root / "CHANGELOG.md").read_bytes()
        self.assertNotIn(b"\r\n", mkt, "LF marketplace.json came back CRLF")
        self.assertEqual(pj.count(b"\r\n"), pj.count(b"\n"), "CRLF plugin.json came back LF or mixed")
        self.assertNotIn(b"\r\n", clog, "LF CHANGELOG.md came back CRLF")
        self.assertEqual(json.loads(pj)["version"], "1.1.0")
        self.assertEqual(json.loads(mkt)["plugins"][0]["version"], "1.1.0")
        self.assertIn(b"## [demo-v1.1.0] - 2026-10-01", clog)

    def test_write_text_helper_writes_lf_for_a_new_file(self):
        root = tmpdir(self)
        build._write_text(root / "new.md", "a\nb\n")
        self.assertEqual((root / "new.md").read_bytes(), b"a\nb\n")


class BumpMemberProvenanceInPlace(unittest.TestCase):
    """Observation 0239: --bump-member appended its re-anchor clause to a provenance line
    whose last sentence had no closing period. The fix rewrites the re-anchor version in
    place; a line with no re-anchor phrase gets a closed sentence appended."""

    SKILL = '---\nname: revenantworks-demo-alpha\nmetadata:\n  version: "1.0.0"\n---\n\n# alpha\n'

    def make(self, header: str) -> Path:
        root = tmpdir(self)
        (root / "evals").mkdir()
        (root / "SKILL.md").write_bytes(self.SKILL.encode())
        (root / "CHANGELOG.md").write_bytes(b"# Changelog\n\n## [1.0.0] - 2026-01-01\n")
        (root / "evals" / "test-cases.md").write_bytes(f"# Test Cases\n\n{header}\n- Counts: 3 cases.\n".encode())
        return root

    def line(self, root: Path) -> str:
        return (root / "evals" / "test-cases.md").read_text(encoding="utf-8").splitlines()[2]

    def test_re_anchor_version_is_rewritten_in_place(self):
        root = self.make("- Provenance: derived from revenantworks-demo-alpha v1.0.0; last re-anchored to "
                         "v1.0.0, 2026-01-01. Full re-anchor history moved to evals/RESULTS.md.")
        build.bump_member(root, "1.0.1", "model row refreshed", "2026-10-01")
        self.assertEqual(self.line(root),
                         "- Provenance: derived from revenantworks-demo-alpha v1.0.0; last re-anchored to "
                         "v1.0.1, 2026-10-01. Full re-anchor history moved to evals/RESULTS.md.")

    def test_unclosed_line_gets_a_closed_sentence(self):
        root = self.make("- Provenance: target v1.0.0")
        build.bump_member(root, "1.0.1", "model row refreshed", "2026-10-01")
        self.assertEqual(self.line(root),
                         "- Provenance: target v1.0.0. **Re-anchored to v1.0.1, 2026-10-01:** model row refreshed.")

    def test_closed_line_is_not_double_punctuated(self):
        root = self.make("- Provenance: target v1.0.0.")
        build.bump_member(root, "1.0.1", "model row refreshed.", "2026-10-01")
        self.assertEqual(self.line(root),
                         "- Provenance: target v1.0.0. **Re-anchored to v1.0.1, 2026-10-01:** model row refreshed.")

    def test_gate_passes_after_in_place_rewrite(self):
        root = self.make("- Provenance: derived from x v1.0.0; last re-anchored to v1.0.0, 2026-01-01.")
        build.bump_member(root, "1.0.1", "r", "2026-10-01")
        _, probs, _ = capture(build.validate_evals, root, "1.0.1")
        self.assertEqual(probs, [])


class NativeEvalLayout(unittest.TestCase):
    """`--check` validates native `claude plugin eval` case folders: prompt.md present,
    every grader a known type. Hand-run evals/*.md and evals/fixtures/ stay valid."""

    def make(self) -> Path:
        ev = tmpdir(self) / "evals"
        (ev / "fixtures").mkdir(parents=True)
        (ev / "fixtures" / "sample.md").write_text("not a case\n", encoding="utf-8")
        (ev / "test-cases.md").write_text("# hand-run suite\n", encoding="utf-8")
        return ev

    def case(self, ev: Path, name: str, prompt: str | None = "---\nmax_turns: 4\n---\nDo the thing.\n",
             graders: dict | None = None) -> None:
        d = ev / name
        (d / "graders").mkdir(parents=True)
        if prompt is not None:
            (d / "prompt.md").write_text(prompt, encoding="utf-8")
        for gname, gtext in (graders if graders is not None
                             else {"fires.md": "---\ntype: tool_used\nweight: 2\n---\nSkill tool called.\n"}).items():
            (d / "graders" / gname).write_text(gtext, encoding="utf-8")

    def test_valid_suite_counts_cases_and_passes(self):
        ev = self.make()
        self.case(ev, "routes-to-alpha")
        self.case(ev, "baseline-arm", graders={"g.md": "---\ntype: baseline\narm: without\n---\n"})
        (ev / "results").mkdir()
        n, probs, warns = capture(build.validate_native_evals, ev, "alpha")
        self.assertEqual((n, probs, warns), (2, [], []))

    def test_missing_suite_is_zero_cases_not_a_failure(self):
        n, probs, _ = capture(build.validate_native_evals, self.make(), "alpha")
        self.assertEqual((n, probs), (0, []))

    def test_missing_prompt_fails(self):
        ev = self.make()
        self.case(ev, "no-prompt", prompt=None)
        _, probs, _ = capture(build.validate_native_evals, ev, "alpha")
        self.assertTrue(any("no prompt.md" in p for p in probs), probs)

    def test_unknown_grader_type_fails(self):
        ev = self.make()
        self.case(ev, "bad-type", graders={"g.md": "---\ntype: vibes\n---\n"})
        _, probs, _ = capture(build.validate_native_evals, ev, "alpha")
        self.assertTrue(any("'vibes'" in p for p in probs), probs)

    def test_case_with_no_graders_fails(self):
        ev = self.make()
        self.case(ev, "ungraded", graders={})
        _, probs, _ = capture(build.validate_native_evals, ev, "alpha")
        self.assertTrue(any("no graders" in p for p in probs), probs)

    def test_unclosed_frontmatter_and_bad_weight_fail(self):
        ev = self.make()
        self.case(ev, "broken", prompt="---\nmax_turns: 4\nDo it.\n",
                  graders={"g.md": "---\ntype: regex\nweight: heavy\n---\n"})
        _, probs, _ = capture(build.validate_native_evals, ev, "alpha")
        self.assertEqual(len(probs), 2, probs)

    def test_live_repo_has_no_malformed_native_case(self):
        for evdir in sorted(build.PACKS.glob("*/skills/*/evals")):
            _, probs, _ = capture(build.validate_native_evals, evdir, evdir.parent.name)
            self.assertEqual(probs, [], evdir.parent.name)


CROSS = """## Pack registry

| Pack | Profile | Notes |
|---|---|---|
| `alpha` | standalone | A |
| `beta` | standard | B |

**alpha members**

| Member | Job | Route there when |
|---|---|---|
| `revenantworks-alpha-onewright` | one | one |
| `revenantworks-alpha-twowright` | two | two |

**beta members**

| Member | Job | Route there when |
|---|---|---|
| `revenantworks-beta-threescribe` | three | three |

## Cross-pack seams

**cross-pack seams** *(note)*

| Member A | Member B | Boundary line |
|---|---|---|
| onewright | threescribe | Files are onewright's; messages are threescribe's |
| twowright | fourscribe | Builds are twowright's; canon is fourscribe's |

**planned:** fourscribe (beta), fivewarden
"""


class CrossPackSeams(unittest.TestCase):
    ROSTERS = {"alpha": ["revenantworks-alpha-onewright", "revenantworks-alpha-twowright"],
               "beta": ["revenantworks-beta-threescribe"]}

    def test_parsers(self):
        self.assertEqual(build.cross_pack_seams(CROSS)[0],
                         ("onewright", "threescribe", "Files are onewright's; messages are threescribe's"))
        self.assertEqual(len(build.cross_pack_seams(CROSS)), 2)
        self.assertEqual(build.registry_planned(CROSS), {"fourscribe": "beta", "fivewarden": None})
        self.assertEqual(build.registry_planned("**planned:** none\n"), {})
        # The cross-pack table must not leak into the per-pack roster parser.
        self.assertEqual(len(build.pack_members(CROSS, "beta")), 1)

    def test_rows_render_into_both_packs(self):
        rows, probs, _ = capture(build.validate_cross_pack, build.cross_pack_seams(CROSS), self.ROSTERS,
                                 build.registry_planned(CROSS))
        self.assertEqual(probs, [])
        alpha = build.cross_rows_for("alpha", rows)
        beta = build.cross_rows_for("beta", rows)
        self.assertEqual([r[:2] for r in alpha], [("onewright", "threescribe (beta)"),
                                                  ("twowright", "fourscribe (beta, planned)")])
        self.assertEqual([r[:2] for r in beta], [("threescribe", "onewright (alpha)")])
        md = build.render_pack_md("alpha", "standalone", [("revenantworks-alpha-onewright", "j", "r")],
                                  "—", "`x`", build.DEFAULT_CHECKS, cross=alpha)
        self.assertIn("**Cross-pack seams**", md)
        self.assertIn("| twowright | fourscribe (beta, planned) | Builds are twowright's; canon is fourscribe's |", md)

    def test_no_rows_leaves_the_manifest_unchanged(self):
        args = ("alpha", "standalone", [("revenantworks-alpha-onewright", "j", "r")], "—", "`x`", build.DEFAULT_CHECKS)
        self.assertEqual(build.render_pack_md(*args), build.render_pack_md(*args, cross=[]))

    def check(self, rows, planned=None):
        return capture(build.validate_cross_pack, rows, self.ROSTERS, planned or {})

    def test_unregistered_and_unplanned_member_fails(self):
        _, probs, _ = self.check([("onewright", "ghostscribe", "line")])
        self.assertTrue(any("'ghostscribe' is neither a registered member" in p for p in probs), probs)

    def test_planned_member_passes(self):
        rows, probs, _ = self.check([("onewright", "ghostscribe", "line")], {"ghostscribe": None})
        self.assertEqual((len(rows), probs), (1, []))
        self.assertEqual(build.cross_rows_for("alpha", rows)[0][1], "ghostscribe (planned)")

    def test_same_pack_pair_fails(self):
        _, probs, _ = self.check([("onewright", "twowright", "line")])
        self.assertTrue(any("belongs in **alpha seams**" in p for p in probs), probs)

    def test_empty_line_self_pair_and_duplicate_fail(self):
        _, probs, _ = self.check([("onewright", "threescribe", " "), ("onewright", "onewright", "x"),
                                  ("onewright", "threescribe", "a"), ("threescribe", "onewright", "b")])
        self.assertEqual(len(probs), 3, probs)

    def test_planned_name_now_registered_warns(self):
        _, probs, warns = self.check([], {"threescribe": "beta"})
        self.assertEqual(probs, [])
        self.assertTrue(any("now registered" in w for w in warns), warns)

    def test_seam_table_stops_at_the_earliest_marker(self):
        # A `## ` heading after the LAST pack made the old tuple-order stop pick "\n## " for the
        # first pack's seam table, which then swallowed every later pack's rows.
        text = ("**a seams**\n\n| Seam | L | R | K | C |\n|---|---|---|---|---|\n| x ↔ y | l | r | k | both descriptions |\n\n"
                "**b seams**\n\n| Seam | L | R | K | C |\n|---|---|---|---|---|\n| p ↔ q | l | r | k | both descriptions |\n\n"
                "## Cross-pack seams\n")
        self.assertEqual([s[:2] for s in build.pack_seams(text, "a")], [("x", "y")])
        self.assertEqual([s[:2] for s in build.pack_seams(text, "b")], [("p", "q")])

    def test_live_registry_cross_pack_rows_resolve(self):
        text = build.registry_text()
        rosters = {p: [m for m, _, _ in build.pack_members(text, p)] for p in build.registry_packs(text)}
        _, probs, _ = capture(build.validate_cross_pack, build.cross_pack_seams(text), rosters,
                              build.registry_planned(text))
        self.assertEqual(probs, [])


MINI_REGISTRY = """# Pack Registry

## Build defaults

| Parameter | Value |
|---|---|
| Brand token *(label)* | `acme` — names skills |

## Pack registry

| Pack | Profile | Notes |
|---|---|---|

## Cross-pack seams

**cross-pack seams** *(note)*

| Member A | Member B | Boundary line |
|---|---|---|

**planned:** none
"""


class Rooted:
    """Point build.py's module paths at a temp tree for one full main() run, then restore."""
    NAMES = ("ROOT", "PACKS", "REGISTRY", "MARKETPLACE", "FEATURED", "DIST", "CHECK")

    def __init__(self, root: Path, check: bool = True):
        self.root, self.check, self.saved = root, check, {}

    def __enter__(self):
        for n in self.NAMES:
            self.saved[n] = getattr(build, n)
        build.ROOT, build.PACKS = self.root, self.root / "packs"
        build.REGISTRY = self.root / self.saved["REGISTRY"].relative_to(self.saved["ROOT"])
        build.MARKETPLACE = self.root / ".claude-plugin" / "marketplace.json"
        build.FEATURED = self.root / "featured"
        build.DIST = self.root / "dist"
        build.CHECK = self.check
        return self

    def __exit__(self, *exc):
        for n, v in self.saved.items():
            setattr(build, n, v)


def mini_root(test: unittest.TestCase, registry: str = MINI_REGISTRY) -> Path:
    root = tmpdir(test)
    reg = root / build.REGISTRY.relative_to(build.ROOT)
    reg.parent.mkdir(parents=True)
    reg.write_bytes(registry.encode())
    (root / ".claude-plugin").mkdir()
    (root / ".claude-plugin" / "marketplace.json").write_bytes(
        b'{\n  "name": "acme",\n  "owner": {"name": "Acme"},\n  "plugins": []\n}\n')
    return root


class NewPackScaffold(unittest.TestCase):
    def test_scaffold_then_check_passes_with_zero_members(self):
        root = mini_root(self)
        self.assertEqual(build.new_pack("scribe", "scribe", "standalone", root=root, today="2026-10-01"), 0)
        pj = json.loads((root / "packs" / "scribe" / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual((pj["name"], pj["version"]), ("scribe", "0.1.0"))
        cat = json.loads((root / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
        self.assertEqual([(p["name"], p["source"], p["version"]) for p in cat["plugins"]],
                         [("scribe", "./packs/scribe", "0.1.0")])
        self.assertIn("`-scribe` motif", (root / "packs" / "scribe" / "README.md").read_text(encoding="utf-8"))
        text = (root / build.REGISTRY.relative_to(build.ROOT)).read_text(encoding="utf-8")
        self.assertEqual(build.registry_packs(text)["scribe"], "standalone")
        self.assertEqual(build.pack_members(text, "scribe"), [])
        self.assertLess(text.index("**scribe members**"), text.index("## Cross-pack seams"))
        with Rooted(root):
            rc, probs, _ = capture(build.main)
        self.assertEqual((rc, probs), (0, []))

    def test_rerun_is_a_no_op_and_writes_lf(self):
        root = mini_root(self)
        build.new_pack("warden", "-warden", "standard", root=root, today="2026-10-01")
        snap = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
        build.new_pack("warden", "-warden", "standard", root=root, today="2026-10-02")
        self.assertEqual({p: p.read_bytes() for p in root.rglob("*") if p.is_file()}, snap)
        for data in snap.values():
            self.assertNotIn(b"\r\n", data)

    def test_rejects_bad_arguments(self):
        root = mini_root(self)
        self.assertEqual(build.new_pack("Scribe", "scribe", "standalone", root=root), 1)
        self.assertEqual(build.new_pack("scribe", None, "standalone", root=root), 1)
        self.assertEqual(build.new_pack("scribe", "scribe", "fancy", root=root), 1)
        self.assertFalse((root / "packs" / "scribe").exists())


FEAT_REGISTRY = MINI_REGISTRY.replace(
    "|---|---|---|\n\n## Cross-pack",
    "|---|---|---|\n| `tools` | standalone | Demo pack. |\n\n**tools members**\n\n"
    "| Member | Job | Route there when |\n|---|---|---|\n| `acme-tools-hammerwright` | Hammers | Nails |\n\n"
    "**tools capstone:** none.\n\n## Cross-pack") + "\n## Featured\n\n**featured:** hammerwright\n"

HAMMER_SKILL = ("---\nname: acme-tools-hammerwright\ndescription: Hammers nails. Trigger on nails.\nlicense: Apache-2.0\n"
                "metadata:\n  version: \"1.2.0\"\n---\n\n# hammerwright\n\nHit the nail.\n")


class FeaturedGenerator(unittest.TestCase):
    """featured/<skill>/ is a generated one-skill plugin; --check fails on drift."""

    def make(self, registry: str = FEAT_REGISTRY) -> Path:
        self.assertEqual(registry.count("**featured:**"), 1)
        root = mini_root(self, registry)
        member = root / "packs" / "tools" / "skills" / "acme-tools-hammerwright"
        (member / "references").mkdir(parents=True)
        (member / "SKILL.md").write_bytes(HAMMER_SKILL.encode())
        (member / "volatile.json").write_bytes(b"[]\n")
        (member / "CHANGELOG.md").write_bytes(b"# Changelog\n\n## [1.2.0] - 2026-10-01\n\n- first\n")
        (member / "references" / "notes.md").write_bytes(b"notes\n")
        (root / "packs" / "tools" / ".claude-plugin").mkdir(parents=True)
        (root / "packs" / "tools" / ".claude-plugin" / "plugin.json").write_bytes(
            b'{"name": "tools", "version": "1.0.0", "author": {"name": "Acme"}, "license": "Apache-2.0"}\n')
        (root / ".claude-plugin" / "marketplace.json").write_bytes(json.dumps(
            {"name": "acme", "owner": {"name": "Acme"},
             "plugins": [{"name": "tools", "source": "./packs/tools", "version": "1.0.0"}]}, indent=2).encode())
        return root

    def run_main(self, root: Path, check: bool):
        with Rooted(root, check=check):
            return capture(build.main)

    def test_build_generates_then_check_is_clean(self):
        root = self.make()
        rc, probs, _ = self.run_main(root, check=True)       # nothing generated yet: drift
        self.assertEqual(rc, 1)
        self.assertTrue(any(p.startswith("featured/hammerwright: drifts") for p in probs), probs)
        rc, probs, _ = self.run_main(root, check=False)      # the real build generates it
        self.assertEqual((rc, probs), (0, []))
        feat = root / "featured" / "hammerwright"
        pj = json.loads((feat / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual((pj["name"], pj["version"], pj["author"]), ("hammerwright", "1.2.0", {"name": "Acme"}))
        self.assertTrue((feat / "skills" / "acme-tools-hammerwright" / "references" / "pack.md").is_file())
        self.assertIn("/plugin install hammerwright@acme", (feat / "README.md").read_text(encoding="utf-8"))
        cat = json.loads((root / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
        self.assertIn({"name": "hammerwright", "source": "./featured/hammerwright", "version": "1.2.0"},
                      [{k: p[k] for k in ("name", "source", "version")} for p in cat["plugins"]])
        rc, probs, _ = self.run_main(root, check=True)
        self.assertEqual((rc, probs), (0, []))

    def test_check_fails_on_source_edit_extra_file_and_orphan(self):
        root = self.make()
        self.run_main(root, check=False)
        src = root / "packs" / "tools" / "skills" / "acme-tools-hammerwright" / "references" / "notes.md"
        src.write_bytes(b"notes, edited\n")
        copy = root / "featured" / "hammerwright" / "skills" / "acme-tools-hammerwright"
        (copy / "stray.md").write_bytes(b"x\n")
        (root / "featured" / "orphan").mkdir()
        _, probs, _ = self.run_main(root, check=True)
        drift = [p for p in probs if p.startswith("featured/hammerwright")]
        self.assertEqual(len(drift), 1, probs)
        self.assertIn("references/notes.md", drift[0])
        self.assertIn("stray.md (not in the pack source)", drift[0])
        self.assertTrue(any("featured/orphan/" in p for p in probs), probs)

    def test_readme_is_written_once_and_never_overwritten(self):
        root = self.make()
        self.run_main(root, check=False)
        readme = root / "featured" / "hammerwright" / "README.md"
        readme.write_bytes(b"# hammerwright\n\nThe real landing page.\n")
        self.run_main(root, check=False)
        self.assertEqual(readme.read_bytes(), b"# hammerwright\n\nThe real landing page.\n")

    def test_featured_skill_copy_carries_the_member_notice(self):
        """Apache-2.0 4(d): the NOTICE travels inside the skill folder (unit NM), so the featured
        copy carries it as an ordinary member file and the plugin root needs no second copy."""
        root = self.make()
        notice = root / "packs" / "tools" / "NOTICE"
        notice.write_bytes(b"tools (a pack)\nCopyright 2026 Acme\n")
        self.run_main(root, check=False)
        feat = root / "featured" / "hammerwright"
        copy = feat / "skills" / "acme-tools-hammerwright" / "NOTICE"
        self.assertEqual(copy.read_bytes(), notice.read_bytes())
        self.assertFalse((feat / "NOTICE").exists())
        self.assertEqual(self.run_main(root, check=True)[:2], (0, []))
        notice.write_bytes(b"tools (a pack)\nCopyright 2027 Acme\n")      # pack NOTICE edited
        rc, probs, _ = self.run_main(root, check=True)
        self.assertEqual(rc, 1)
        self.assertTrue(any("acme-tools-hammerwright/NOTICE" in p for p in probs), probs)
        self.run_main(root, check=False)
        copy.unlink()                                                       # copy missing
        rc, probs, _ = self.run_main(root, check=True)
        self.assertTrue(any(p.startswith("featured/hammerwright") and "NOTICE" in p for p in probs), probs)

    def test_featured_notice_ignores_line_endings_only(self):
        root = self.make()
        (root / "packs" / "tools" / "NOTICE").write_bytes(b"tools\nCopyright 2026 Acme\n")
        self.run_main(root, check=False)
        copy = root / "featured" / "hammerwright" / "skills" / "acme-tools-hammerwright" / "NOTICE"
        copy.write_bytes(b"tools\r\nCopyright 2026 Acme\r\n")
        self.assertEqual(self.run_main(root, check=True)[:2], (0, []))

    def test_unregistered_featured_name_fails(self):
        _, probs, _ = capture(build.sync_featured, ["ghostwright"], {"tools": ["acme-tools-hammerwright"]},
                              self.make(), False)
        self.assertTrue(any("'ghostwright' is not a registered member" in p for p in probs), probs)

    def tag_tree(self, root: Path, tag: str) -> bool:
        """Tag the current tree of `root` (a tree tag needs no commit and no identity)."""
        import subprocess
        try:
            for cmd in (["init", "-q"], ["add", "-A"]):
                subprocess.run(["git", "-C", str(root), *cmd], check=True, capture_output=True)
            tree = subprocess.run(["git", "-C", str(root), "write-tree"], check=True, capture_output=True,
                                  text=True).stdout.strip()
            subprocess.run(["git", "-C", str(root), "tag", tag, tree], check=True, capture_output=True)
        except (OSError, subprocess.CalledProcessError):
            return False
        return True

    def skew(self, warns):
        return [w for w in warns if w.startswith("featured/hammerwright") and "last released" in w]

    def test_featured_copy_newer_than_the_pack_release_warns(self):
        """J1 featured verdict: a user with the pack AND the featured plugin installed gets two
        bodies under one skill name when the featured copy moved past the pack's last release."""
        root = self.make()
        self.run_main(root, check=False)
        if not self.tag_tree(root, "tools-v1.0.0"):
            self.skipTest("git not available")
        rc, probs, warns = self.run_main(root, check=True)
        self.assertEqual((rc, probs, self.skew(warns)), (0, [], []))
        src = root / "packs" / "tools" / "skills" / "acme-tools-hammerwright" / "references" / "notes.md"
        src.write_bytes(b"notes, edited after the release\n")
        self.run_main(root, check=False)                      # regenerate the featured copy
        rc, probs, warns = self.run_main(root, check=True)
        self.assertEqual((rc, probs), (0, []))                # advisory, never a failure
        skew = self.skew(warns)
        self.assertEqual(len(skew), 1, warns)
        self.assertIn("tools-v1.0.0", skew[0])
        self.assertIn("references/notes.md", skew[0])

    def test_no_release_tag_means_no_skew_warning(self):
        root = self.make()
        self.run_main(root, check=False)
        rc, probs, warns = self.run_main(root, check=True)
        self.assertEqual((rc, probs, self.skew(warns)), (0, [], []))

    def test_live_registry_featured_line_is_parseable(self):
        text = build.registry_text()
        self.assertEqual(text.count("**featured:**"), 1)
        self.assertEqual(build.registry_featured("**featured:** none\n"), [])
        self.assertEqual(build.registry_featured("**featured:** pacewright, `skillwright`\n"),
                         ["pacewright", "skillwright"])


if __name__ == "__main__":
    unittest.main()
