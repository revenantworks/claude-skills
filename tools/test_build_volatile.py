"""Owner decision M3 (2026-10-08): the volatile list leaves SKILL.md frontmatter for a
`volatile.json` beside it, and `metadata` holds string values only.

The Agent Skills spec (agentskills.io/specification) defines `metadata` as "A map from string
keys to string values". Every member carried `metadata.volatile` as a nested list, which the
claude.ai upload path and a strict parser are entitled to reject. `--check` now fails on any
nested structure or non-string scalar under `metadata`, so the shape cannot come back, and
U-7 validates `volatile.json` instead.

Stdlib only. Fixtures are written to temp directories.
"""
import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402
import test_build_split  # noqa: E402  (module import: a TestCase imported by name would run twice)
from test_build_split import Rooted, capture, tmpdir  # noqa: E402
from test_build_t2 import foot_root  # noqa: E402

MEMBER = ("packs", "tools", "skills", "acme-tools-hammerwright")
STAMPED = b"# Sources\n\nLast verified: 2026-09-28\n\nNothing else.\n"


def skill_md(metadata: str) -> bytes:
    body = "# hammerwright\n\nHit the nail.\n\n## Steps\n\nHit it.\n"
    return ("---\nname: acme-tools-hammerwright\ndescription: Hammers nails.\n"
            f"metadata:\n{metadata}---\n\n{body}").encode()


def run_check(root: Path):
    """The real build (write) then --check, as a member author would run them."""
    with Rooted(root, check=False):
        capture(build.main)
    out = io.StringIO()
    with Rooted(root, check=True), redirect_stdout(out):
        rc, probs, _ = capture(build.main)
    return rc, probs


class MetadataStringsOnly(unittest.TestCase):
    """A nested list (the old volatile shape) or a typed scalar under `metadata` fails --check."""

    def root_with(self, metadata: str) -> Path:
        root = foot_root(self, 5000)
        member = root.joinpath(*MEMBER)
        member.joinpath("SKILL.md").write_bytes(skill_md(metadata))
        member.joinpath("SOURCES.md").write_bytes(STAMPED)
        member.joinpath("volatile.json").write_bytes(b"[]\n")
        return root

    def test_string_metadata_is_clean(self):
        rc, probs = run_check(self.root_with('  version: "1.0.0"\n  profile: standalone\n  cadence: "90"\n'))
        self.assertEqual((rc, probs), (0, []))

    def test_nested_volatile_list_fails_check(self):
        # The pre-M3 member shape, verbatim: a nested list of mappings under metadata.volatile.
        rc, probs = run_check(self.root_with(
            '  version: "1.0.0"\n  volatile:\n    - file: SOURCES.md\n      class: calendar\n'
            '      cadence_days: 90\n'))
        self.assertNotEqual(rc, 0)
        self.assertTrue(any("metadata" in p and "volatile" in p and "string" in p for p in probs), probs)

    def test_flow_list_fails_check(self):
        rc, probs = run_check(self.root_with('  version: "1.0.0"\n  volatile: []\n'))
        self.assertNotEqual(rc, 0)
        self.assertTrue(any("metadata.volatile" in p for p in probs), probs)

    def test_member_body_budget_in_frontmatter_fails_check(self):
        # The old nested form fails the string rule; even the flat string pair fails for a member,
        # whose one home for a budget is the registry row.
        for meta in ('  body_budget:\n    tokens: 4000\n    why: test\n',
                     '  body_budget: "4000"\n  body_budget_why: "test"\n'):
            with self.subTest(meta=meta):
                rc, probs = run_check(self.root_with('  version: "1.0.0"\n' + meta))
                self.assertNotEqual(rc, 0)
                self.assertTrue(any("body_budget" in p and "registry" in p for p in probs), probs)

    def test_unquoted_integer_and_boolean_fail_check(self):
        for line in ("  cadence_days: 90\n", "  shipped: true\n", "  ratio: 0.5\n", "  owner: null\n"):
            with self.subTest(line=line):
                rc, probs = run_check(self.root_with('  version: "1.0.0"\n' + line))
                self.assertNotEqual(rc, 0)
                key = line.split(":")[0].strip()
                self.assertTrue(any(f"metadata.{key}" in p and "string" in p for p in probs), probs)


class VolatileJson(unittest.TestCase):
    """U-7 reads `volatile.json` beside SKILL.md: a JSON list of {file, class, cadence_days?}."""

    def check(self, data):
        root = tmpdir(self)
        (root / "references").mkdir()
        (root / "references" / "SOURCES.md").write_bytes(
            b"# Sources\n\nIntro.\n\n## Parity register\n\nLast verified: 2026-09-28\n\n## Other\n\nx\n")
        (root / "notes.md").write_bytes(b"# Notes\n\nNo stamp here.\n")
        if data is not None:
            raw = data if isinstance(data, bytes) else json.dumps(data).encode()
            (root / "volatile.json").write_bytes(raw)
        _, probs, _ = capture(build.validate_volatile, root)
        return probs

    def test_empty_list_passes(self):
        self.assertEqual(self.check([]), [])

    def test_valid_calendar_and_event_driven_pass(self):
        self.assertEqual(self.check([
            {"file": "references/SOURCES.md", "class": "calendar", "cadence_days": 90},
            {"file": "references/SOURCES.md#parity-register", "class": "calendar", "cadence_days": 30},
            {"file": "notes.md", "class": "event-driven"}]), [])

    def test_missing_file_fails(self):
        probs = self.check(None)
        self.assertTrue(any("volatile.json missing" in p for p in probs), probs)

    def test_not_json_fails(self):
        probs = self.check(b"- file: SOURCES.md\n")
        self.assertTrue(any("not valid JSON" in p for p in probs), probs)

    def test_not_a_list_fails(self):
        probs = self.check({"file": "notes.md", "class": "event-driven"})
        self.assertTrue(any("must be a JSON list" in p for p in probs), probs)

    def test_cadence_as_string_fails(self):
        probs = self.check([{"file": "references/SOURCES.md", "class": "calendar", "cadence_days": "90"}])
        self.assertTrue(any("cadence_days" in p and "integer" in p for p in probs), probs)

    def test_cadence_as_boolean_fails(self):
        probs = self.check([{"file": "references/SOURCES.md", "class": "calendar", "cadence_days": True}])
        self.assertTrue(any("cadence_days" in p and "integer" in p for p in probs), probs)

    def test_illegal_class_fails(self):
        probs = self.check([{"file": "notes.md", "class": "weekly"}])
        self.assertTrue(any("'weekly'" in p and "calendar|event-driven" in p for p in probs), probs)

    def test_declared_file_must_exist(self):
        probs = self.check([{"file": "references/GONE.md", "class": "event-driven"}])
        self.assertTrue(any("GONE.md" in p and "does not exist" in p for p in probs), probs)

    def test_event_driven_with_cadence_fails(self):
        probs = self.check([{"file": "notes.md", "class": "event-driven", "cadence_days": 30}])
        self.assertTrue(any("must not carry cadence_days" in p for p in probs), probs)

    def test_calendar_without_stamp_fails(self):
        probs = self.check([{"file": "notes.md", "class": "calendar", "cadence_days": 30}])
        self.assertTrue(any("no dated header stamp" in p for p in probs), probs)

    def test_unknown_key_fails(self):
        probs = self.check([{"file": "notes.md", "class": "event-driven", "owner": "x"}])
        self.assertTrue(any("unknown key" in p and "owner" in p for p in probs), probs)


class FeaturedCopiesVolatileJson(unittest.TestCase):
    """The featured one-skill plugin copies `volatile.json` with its member, and --check
    fails when the copy drifts."""

    def test_featured_copy_carries_volatile_json(self):
        root = test_build_split.FeaturedGenerator.make(self)
        with Rooted(root, check=False):
            rc, probs, _ = capture(build.main)
        self.assertEqual((rc, probs), (0, []))
        copy = root / "featured" / "hammerwright" / "skills" / "acme-tools-hammerwright" / "volatile.json"
        self.assertEqual(copy.read_bytes(), b"[]\n")
        copy.write_bytes(b'[{"file": "SKILL.md", "class": "event-driven"}]\n')
        with Rooted(root, check=True), redirect_stdout(io.StringIO()):
            rc, probs, _ = capture(build.main)
        self.assertNotEqual(rc, 0)
        self.assertTrue(any("volatile.json" in p for p in probs), probs)


if __name__ == "__main__":
    unittest.main()
