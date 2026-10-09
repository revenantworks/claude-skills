#!/usr/bin/env python3
"""Unit tests for pack-shared files (owner Q2, run 2026-09-28-pack-split, unit P1e).

A pack may keep files that several members carry byte for byte (localops: the GPU seam
reference and the GPU pre-flight script). The source lives once in `packs/<pack>/shared/`,
`shared/holders.json` names which members carry which file, and build.py writes every copy
(the real build) or fails on any drift (--check). Before this, the copies were kept in step
by hand (observation 0209; S0 report section 6).

Run: python3 -m unittest discover -s tools -p "test_*.py"
Stdlib only; every fixture lives in a temp directory.
"""
import json
import unittest
from pathlib import Path

import build
from test_build_split import MINI_REGISTRY, Rooted, capture, mini_root

SHARED_REGISTRY = MINI_REGISTRY.replace(
    "|---|---|---|\n\n## Cross-pack",
    "|---|---|---|\n| `tools` | standard | Demo pack. |\n\n**tools members**\n\n"
    "| Member | Job | Route there when |\n|---|---|---|\n"
    "| `acme-tools-hammerwright` | Hammers | Nails |\n"
    "| `acme-tools-sawwright` | Saws | Boards |\n"
    "| `acme-tools-drillwright` | Drills | Holes |\n\n"
    "**tools capstone:** none.\n\n## Cross-pack")

SEAM = b"# Seam\n\nOne card, several holders.\n"
PRE = b"#!/usr/bin/env python3\nprint('preflight')\n"
MEMBERS = ("hammerwright", "sawwright", "drillwright")


def skill(short: str) -> bytes:
    return (f"---\nname: acme-tools-{short}\ndescription: Does {short} work. Trigger on {short}.\n"
            f"license: Apache-2.0\nmetadata:\n  version: \"1.0.0\"\n---\n\n# {short}\n\nWork.\n").encode()


def make(test: unittest.TestCase, holders: dict | None = None) -> Path:
    """A three-member pack; hammerwright and sawwright hold both shared files, drillwright none."""
    root = mini_root(test, SHARED_REGISTRY)
    pack = root / "packs" / "tools"
    for short in MEMBERS:
        m = pack / "skills" / f"acme-tools-{short}"
        (m / "references").mkdir(parents=True)
        (m / "SKILL.md").write_bytes(skill(short))
        (m / "volatile.json").write_bytes(b"[]\n")
        (m / "CHANGELOG.md").write_bytes(b"# Changelog\n\n## [1.0.0] - 2026-10-01\n\n- first\n")
    shared = pack / "shared"
    (shared / "references").mkdir(parents=True)
    (shared / "scripts").mkdir()
    (shared / "references" / "seam.md").write_bytes(SEAM)
    (shared / "scripts" / "pre.py").write_bytes(PRE)
    if holders is None:
        holders = {"references/seam.md": ["hammerwright", "acme-tools-sawwright"],
                   "scripts/pre.py": ["hammerwright", "sawwright"]}
    (shared / "holders.json").write_bytes(json.dumps({"files": holders}, indent=2).encode())
    (pack / ".claude-plugin").mkdir()
    (pack / ".claude-plugin" / "plugin.json").write_bytes(b'{"name": "tools", "version": "1.0.0"}\n')
    (root / ".claude-plugin" / "marketplace.json").write_bytes(json.dumps(
        {"name": "acme", "owner": {"name": "Acme"},
         "plugins": [{"name": "tools", "source": "./packs/tools", "version": "1.0.0"}]}, indent=2).encode())
    return root


ROSTER = [f"acme-tools-{s}" for s in MEMBERS]


def member(root: Path, short: str) -> Path:
    return root / "packs" / "tools" / "skills" / f"acme-tools-{short}"


def sync(root: Path, write: bool, report_only: bool = False):
    return capture(build.sync_shared, "tools", ROSTER, root, write, report_only)


class SharedGenerator(unittest.TestCase):
    def test_check_reports_missing_copies_then_build_writes_them(self):
        root = make(self)
        n, probs, _ = sync(root, write=False)
        self.assertEqual(n, 4)
        self.assertEqual(len(probs), 4, probs)
        self.assertTrue(all("shared" in p and "run tools/build.py" in p for p in probs), probs)
        self.assertFalse((member(root, "hammerwright") / "references" / "seam.md").exists())
        n, probs, _ = sync(root, write=True)
        self.assertEqual((n, probs), (4, []))
        for short in ("hammerwright", "sawwright"):
            self.assertEqual((member(root, short) / "references" / "seam.md").read_bytes(), SEAM)
            self.assertEqual((member(root, short) / "scripts" / "pre.py").read_bytes(), PRE)
        self.assertFalse((member(root, "drillwright") / "references" / "seam.md").exists())
        _, probs, _ = sync(root, write=False)
        self.assertEqual(probs, [])

    def test_hand_edit_of_a_copy_fails_check_and_build_restores_it(self):
        root = make(self)
        sync(root, write=True)
        copy = member(root, "sawwright") / "references" / "seam.md"
        copy.write_bytes(SEAM + b"\nA hand edit.\n")
        _, probs, _ = sync(root, write=False)
        self.assertEqual(len(probs), 1, probs)
        self.assertIn("acme-tools-sawwright/references/seam.md", probs[0])
        _, probs, _ = sync(root, write=True)
        self.assertEqual(probs, [])
        self.assertEqual(copy.read_bytes(), SEAM)

    def test_line_ending_alone_is_not_drift(self):
        root = make(self)
        sync(root, write=True)
        copy = member(root, "hammerwright") / "references" / "seam.md"
        copy.write_bytes(SEAM.replace(b"\n", b"\r\n"))
        _, probs, _ = sync(root, write=False)
        self.assertEqual(probs, [])

    def test_report_only_warns_and_writes_nothing(self):
        root = make(self)
        _, probs, warns = sync(root, write=False, report_only=True)
        self.assertEqual(probs, [])
        self.assertEqual(len(warns), 4, warns)
        self.assertFalse((member(root, "hammerwright") / "references" / "seam.md").exists())

    def test_unlisted_member_carrying_a_shared_path_fails(self):
        root = make(self)
        sync(root, write=True)
        stray = member(root, "drillwright") / "references" / "seam.md"
        stray.write_bytes(SEAM)
        _, probs, _ = sync(root, write=False)
        self.assertEqual(len(probs), 1, probs)
        self.assertIn("acme-tools-drillwright", probs[0])
        self.assertIn("holders.json", probs[0])

    def test_manifest_errors_fail(self):
        root = make(self, {"references/seam.md": ["hammerwright", "ghostwright"],
                           "references/gone.md": ["hammerwright"],
                           "scripts/pre.py": ["hammerwright"]})
        _, probs, _ = sync(root, write=True)
        self.assertTrue(any("'ghostwright'" in p for p in probs), probs)
        self.assertTrue(any("references/gone.md" in p and "no source" in p for p in probs), probs)
        # the listed, valid pairs are still written
        self.assertEqual((member(root, "hammerwright") / "scripts" / "pre.py").read_bytes(), PRE)

    def test_source_file_not_in_manifest_fails(self):
        root = make(self)
        (root / "packs" / "tools" / "shared" / "references" / "extra.md").write_bytes(b"x\n")
        _, probs, _ = sync(root, write=False)
        self.assertTrue(any("references/extra.md" in p and "not listed" in p for p in probs), probs)

    def test_missing_or_malformed_manifest_fails(self):
        root = make(self)
        manifest = root / "packs" / "tools" / "shared" / "holders.json"
        manifest.write_bytes(b"{not json")
        _, probs, _ = sync(root, write=False)
        self.assertTrue(any("holders.json" in p for p in probs), probs)
        manifest.unlink()
        _, probs, _ = sync(root, write=False)
        self.assertTrue(any("holders.json" in p for p in probs), probs)

    def test_pack_without_shared_folder_is_a_no_op(self):
        root = make(self)
        import shutil
        shutil.rmtree(root / "packs" / "tools" / "shared")
        n, probs, warns = sync(root, write=False)
        self.assertEqual((n, probs, warns), (0, [], []))

    def test_main_generates_then_check_is_clean(self):
        root = make(self)
        with Rooted(root, check=True):
            rc, probs, _ = capture(build.main)
        self.assertEqual(rc, 1)
        self.assertTrue(any("shared" in p for p in probs), probs)
        with Rooted(root, check=False):
            rc, probs, _ = capture(build.main)
        self.assertEqual((rc, probs), (0, []))
        self.assertEqual((member(root, "sawwright") / "scripts" / "pre.py").read_bytes(), PRE)
        with Rooted(root, check=True):
            rc, probs, _ = capture(build.main)
        self.assertEqual((rc, probs), (0, []))


class LiveShared(unittest.TestCase):
    def test_live_localops_shared_copies_are_in_step(self):
        text = build.registry_text()
        roster = [m for m, _, _ in build.pack_members(text, "localops")]
        n, probs, _ = capture(build.sync_shared, "localops", roster, build.ROOT, False)
        self.assertEqual(probs, [])
        self.assertGreaterEqual(n, 8)  # the seam and the pre-flight, in at least four GPU members


if __name__ == "__main__":
    unittest.main()
