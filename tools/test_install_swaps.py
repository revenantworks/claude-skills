#!/usr/bin/env python3
"""apply-install-swaps NOTICE tests (run 2026-09-28-pack-split, units NT and NM).

Apache-2.0 section 4(d): a redistribution of a work that carries a NOTICE file must carry
that NOTICE too. Every install zip apply-install-swaps writes is a redistribution, so the
NOTICE travels beside the LICENSE: the swaps dir's NOTICE when it holds one, else the
member's own NOTICE copy (build.py writes it from the pack NOTICE, unit NM).

Run: python3 -m unittest discover -s tools -p "test_*.py"
Stdlib only. The end-to-end case runs against a temporary tree, never the live one.
"""
import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("apply_install_swaps", HERE / "apply-install-swaps.py")
swaps = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(swaps)

SKILL = "---\nname: demo\nversion: 1.2.3\nmetadata:\n  brand: neutral\n---\nbody\n"


def _w(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))
    return path


class Overlay(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.tmp = Path(self._td.name)
        self.work = self.tmp / "work"
        _w(self.work / "SKILL.md", SKILL)
        _w(self.work / "LICENSE", "neutral licence\n")
        _w(self.work / "NOTICE", "pack notice\n")       # the member copy build.py writes
        self.sw = self.tmp / "swaps"
        self.sw.mkdir()

    def tearDown(self):
        self._td.cleanup()

    def test_swaps_notice_overlays_and_is_reported(self):
        _w(self.sw / "NOTICE", "my notice\n")
        notes = swaps.apply_global_overrides(self.work, self.sw)
        self.assertIn("NOTICE", notes)
        self.assertEqual((self.work / "NOTICE").read_text(encoding="utf-8"), "my notice\n")

    def test_licence_swap_keeps_the_member_notice_beside_it(self):
        _w(self.sw / "LICENSE", "my licence\n")
        notes = swaps.apply_global_overrides(self.work, self.sw)
        self.assertEqual(notes, ["LICENSE"])
        self.assertEqual((self.work / "NOTICE").read_text(encoding="utf-8"), "pack notice\n")

    def test_member_notice_alone_is_not_a_change(self):
        _w(self.sw / "LICENSE", "neutral licence\n")
        self.assertEqual(swaps.apply_global_overrides(self.work, self.sw), [])

    def test_same_swaps_notice_is_not_a_change(self):
        _w(self.sw / "NOTICE", "pack notice\n")
        self.assertEqual(swaps.apply_global_overrides(self.work, self.sw), [])

    def test_swaps_notice_beats_the_member_notice(self):
        _w(self.sw / "LICENSE", "my licence\n")
        _w(self.sw / "NOTICE", "my notice\n")
        swaps.apply_global_overrides(self.work, self.sw)
        self.assertEqual((self.work / "NOTICE").read_text(encoding="utf-8"), "my notice\n")


class TokenLineEndings(unittest.TestCase):
    """The brand-token swap writes bytes and keeps each SKILL.md's own line endings."""

    def run_token(self, skill: bytes) -> tuple[list[str], bytes]:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            (tmp / "work").mkdir()
            (tmp / "work" / "SKILL.md").write_bytes(skill)
            _w(tmp / "swaps" / "brand-token.txt", "mine\n")
            notes = swaps.apply_global_overrides(tmp / "work", tmp / "swaps")
            return notes, (tmp / "work" / "SKILL.md").read_bytes()

    def test_lf_file_stays_lf(self):
        notes, out = self.run_token(SKILL.encode("utf-8"))
        self.assertEqual(notes, ["token -> mine"])
        self.assertEqual(out, SKILL.replace("brand: neutral", "brand: mine").encode("utf-8"))

    def test_crlf_file_stays_crlf(self):
        src = SKILL.replace("\n", "\r\n").encode("utf-8")
        notes, out = self.run_token(src)
        self.assertEqual(notes, ["token -> mine"])
        self.assertEqual(out, src.replace(b"brand: neutral", b"brand: mine"))

    def test_same_token_is_no_change(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            (tmp / "work").mkdir()
            (tmp / "work" / "SKILL.md").write_bytes(SKILL.replace("\n", "\r\n").encode("utf-8"))
            _w(tmp / "swaps" / "brand-token.txt", "neutral\n")
            self.assertEqual(swaps.apply_global_overrides(tmp / "work", tmp / "swaps"), [])


class LiveTargets(unittest.TestCase):
    def test_every_member_carries_a_notice(self):
        found = swaps.members()
        self.assertGreaterEqual(len(found), 1)
        for m in found:
            self.assertTrue((m / "NOTICE").is_file(), m.name)


class EndToEnd(unittest.TestCase):
    def test_every_install_zip_carries_a_notice(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            packs = tmp / "packs"
            for pack, member in (("alpha", "rw-alpha-one"), ("beta", "rw-beta-two")):
                _w(packs / pack / "skills" / member / "NOTICE", f"{pack} notice\n")
                _w(packs / pack / "skills" / member / "SKILL.md", SKILL)
                _w(packs / pack / "skills" / member / "LICENSE", "neutral licence\n")
            sw = tmp / "swaps"
            _w(sw / "LICENSE", "my licence\n")
            old = (swaps.PACKS, swaps.OUT, sys.argv)
            swaps.PACKS, swaps.OUT, sys.argv = packs, tmp / "out", ["apply-install-swaps.py", str(sw)]
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    rc = swaps.main()
            finally:
                swaps.PACKS, swaps.OUT, sys.argv = old
            self.assertEqual(rc, 0)
            zips = sorted((tmp / "out").glob("*+install.zip"))
            self.assertEqual(len(zips), 2)
            for z in zips:
                member = z.name.split("-1.2.3")[0]
                pack = member.split("-")[1]
                with zipfile.ZipFile(z) as zf:
                    self.assertEqual(zf.read(f"{member}/LICENSE").decode("utf-8"), "my licence\n")
                    self.assertEqual(zf.read(f"{member}/NOTICE").decode("utf-8"), f"{pack} notice\n")

    def test_a_notice_only_swaps_dir_builds(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            packs = tmp / "packs"
            _w(packs / "alpha" / "skills" / "rw-alpha-one" / "NOTICE", "alpha notice\n")
            _w(packs / "alpha" / "skills" / "rw-alpha-one" / "SKILL.md", SKILL)
            _w(packs / "alpha" / "skills" / "rw-alpha-one" / "LICENSE", "neutral licence\n")
            sw = tmp / "swaps"
            _w(sw / "NOTICE", "my notice\n")
            old = (swaps.PACKS, swaps.OUT, sys.argv)
            swaps.PACKS, swaps.OUT, sys.argv = packs, tmp / "out", ["apply-install-swaps.py", str(sw)]
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    rc = swaps.main()
            finally:
                swaps.PACKS, swaps.OUT, sys.argv = old
            self.assertEqual(rc, 0)
            (z,) = sorted((tmp / "out").glob("*+install.zip"))
            with zipfile.ZipFile(z) as zf:
                self.assertEqual(zf.read("rw-alpha-one/NOTICE").decode("utf-8"), "my notice\n")


if __name__ == "__main__":
    unittest.main()
