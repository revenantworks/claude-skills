#!/usr/bin/env python3
"""Unit tests for full frontmatter YAML parsing (unit K8e).

build.py parsed the frontmatter as YAML only when the description held ": ", so a plain value
with ": " in any other field (handoffwright and pixelsmith `compatibility:`) passed --check and
broke a strict YAML loader. Every member's frontmatter now parses whole, and a parse error fails.

Run: python -m unittest discover -s tools -p "test_*.py"
Stdlib only (PyYAML is used when installed; the stdlib scan is tested on its own).
"""
import unittest
from pathlib import Path

import build
from test_build_split import Rooted, capture
from test_build_shared import make, member

BAD = b"compatibility: Needs git: the commit step runs it\n"
GOOD = b"compatibility: 'Needs git: the commit step runs it'\n"


def with_field(root: Path, line: bytes) -> None:
    p = member(root, "hammerwright") / "SKILL.md"
    b = p.read_bytes()
    assert b.count(b"license: Apache-2.0\n") == 1
    p.write_bytes(b.replace(b"license: Apache-2.0\n", b"license: Apache-2.0\n" + line))


class FullFrontmatterParse(unittest.TestCase):
    def check(self, root: Path) -> list[str]:
        with Rooted(root, check=False):
            capture(build.main)
        with Rooted(root, check=True):
            _, probs, _ = capture(build.main)
        return [p for p in probs if "YAML" in p]

    def test_unquoted_colon_outside_the_description_fails_check(self):
        root = make(self)
        with_field(root, BAD)
        probs = self.check(root)
        self.assertEqual(len(probs), 1, probs)
        self.assertIn("acme-tools-hammerwright", probs[0])

    def test_quoted_value_passes(self):
        root = make(self)
        with_field(root, GOOD)
        self.assertEqual(self.check(root), [])

    def test_stdlib_scan_catches_the_same_value(self):
        fm = "\nname: x\ndescription: Does x.\n" + BAD.decode()
        self.assertIsNotNone(build.frontmatter_yaml_error(fm))
        self.assertIsNone(build.frontmatter_yaml_error("\nname: x\n" + GOOD.decode()))
        saved = __import__("sys").modules.get("yaml")
        __import__("sys").modules["yaml"] = None  # force the stdlib path
        try:
            self.assertIsNotNone(build.frontmatter_yaml_error(fm))
            self.assertIsNone(build.frontmatter_yaml_error("\nname: x\n" + GOOD.decode()))
            self.assertIsNone(build.frontmatter_yaml_error('\nmetadata:\n  version: "1.0.0"\n'))
        finally:
            if saved is None:
                del __import__("sys").modules["yaml"]
            else:
                __import__("sys").modules["yaml"] = saved

    def test_every_live_member_parses(self):
        for folder in sorted(build.PACKS.glob("*/skills/*")) + sorted(build.FEATURED.glob("*/skills/*")):
            sk = folder / "SKILL.md"
            if sk.is_file():
                fm = sk.read_bytes().decode("utf-8").replace("\r\n", "\n").split("---", 2)[1]
                self.assertIsNone(build.frontmatter_yaml_error(fm), folder.name)


if __name__ == "__main__":
    unittest.main()
