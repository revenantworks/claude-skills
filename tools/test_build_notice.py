#!/usr/bin/env python3
"""Unit tests for member NOTICE copies (run 2026-09-28-pack-split, unit NM).

Apache-2.0 section 4(d): a redistribution carries the work's NOTICE. A lone skill folder copied
out of a pack is a redistribution too, so every member folder carries a `NOTICE` beside its
`LICENSE`. The pack NOTICE (`packs/<pack>/NOTICE`) stays the single source; build.py writes each
member copy (the real build) and `--check` fails on a copy missing or drifting, line endings aside.

Run: python3 -m unittest discover -s tools -p "test_*.py"
Stdlib only; every fixture lives in a temp directory.
"""
import unittest
from pathlib import Path

import build
from test_build_shared import MEMBERS, ROSTER, make, member
from test_build_split import Rooted, capture

NOTICE = b"tools (a pack)\nCopyright 2026 Acme\n"


def with_notice(test: unittest.TestCase) -> Path:
    root = make(test)
    (root / "packs" / "tools" / "NOTICE").write_bytes(NOTICE)
    return root


def sync(root: Path, write: bool, report_only: bool = False):
    return capture(build.sync_member_notice, "tools", ROSTER, root, write, report_only)


class MemberNotice(unittest.TestCase):
    def test_check_reports_missing_copies_then_build_writes_them(self):
        root = with_notice(self)
        n, probs, _ = sync(root, write=False)
        self.assertEqual(n, 3)
        self.assertEqual(len(probs), 3, probs)
        self.assertTrue(all("NOTICE" in p and "run tools/build.py" in p for p in probs), probs)
        self.assertFalse((member(root, "hammerwright") / "NOTICE").exists())
        n, probs, _ = sync(root, write=True)
        self.assertEqual((n, probs), (3, []))
        for short in MEMBERS:
            self.assertEqual((member(root, short) / "NOTICE").read_bytes(), NOTICE)
        self.assertEqual(sync(root, write=False)[1], [])

    def test_hand_edit_fails_check_and_build_restores_it(self):
        root = with_notice(self)
        sync(root, write=True)
        copy = member(root, "sawwright") / "NOTICE"
        copy.write_bytes(NOTICE + b"A hand edit.\n")
        _, probs, _ = sync(root, write=False)
        self.assertEqual(len(probs), 1, probs)
        self.assertIn("acme-tools-sawwright/NOTICE", probs[0])
        self.assertIn("drifts", probs[0])
        self.assertEqual(sync(root, write=True)[1], [])
        self.assertEqual(copy.read_bytes(), NOTICE)

    def test_pack_notice_edit_is_drift_in_every_member(self):
        root = with_notice(self)
        sync(root, write=True)
        (root / "packs" / "tools" / "NOTICE").write_bytes(NOTICE.replace(b"2026", b"2027"))
        self.assertEqual(len(sync(root, write=False)[1]), 3)

    def test_line_ending_alone_is_not_drift(self):
        root = with_notice(self)
        sync(root, write=True)
        (member(root, "drillwright") / "NOTICE").write_bytes(NOTICE.replace(b"\n", b"\r\n"))
        self.assertEqual(sync(root, write=False)[1], [])

    def test_report_only_warns_and_writes_nothing(self):
        root = with_notice(self)
        _, probs, warns = sync(root, write=False, report_only=True)
        self.assertEqual(probs, [])
        self.assertEqual(len(warns), 3, warns)
        self.assertFalse((member(root, "hammerwright") / "NOTICE").exists())

    def test_pack_without_notice_is_a_no_op(self):
        n, probs, warns = sync(make(self), write=True)
        self.assertEqual((n, probs, warns), (0, [], []))
        self.assertFalse((member(make(self), "hammerwright") / "NOTICE").exists())

    def test_main_generates_then_check_is_clean(self):
        root = with_notice(self)
        with Rooted(root, check=True):
            rc, probs, _ = capture(build.main)
        self.assertEqual(rc, 1)
        self.assertTrue(any("NOTICE" in p for p in probs), probs)
        with Rooted(root, check=False):
            rc, probs, _ = capture(build.main)
        self.assertEqual((rc, probs), (0, []))
        self.assertEqual((member(root, "hammerwright") / "NOTICE").read_bytes(), NOTICE)
        with Rooted(root, check=True):
            rc, probs, _ = capture(build.main)
        self.assertEqual((rc, probs), (0, []))


class LiveNotice(unittest.TestCase):
    def test_every_live_member_carries_its_pack_notice(self):
        text = build.registry_text()
        total = 0
        for pack in build.registry_packs(text):
            roster = [m for m, _, _ in build.pack_members(text, pack)]
            n, probs, _ = capture(build.sync_member_notice, pack, roster, build.ROOT, False)
            self.assertEqual(probs, [], pack)
            self.assertEqual(n, len(roster), pack)
            total += n
        # The floor is the live roster, read the way build.py's count integrity reads its
        # "folders" figure: member folders on disk under packs/<pack>/skills/. A fixed number
        # (30 at 1.0.0) broke when the 2026-10-08 consolidations met at 28.
        on_disk = sum(len(build._member_dirs(build.PACKS / pack / "skills"))
                      for pack in build.registry_packs(text))
        self.assertGreater(on_disk, 0)
        self.assertEqual(total, on_disk)


if __name__ == "__main__":
    unittest.main()
