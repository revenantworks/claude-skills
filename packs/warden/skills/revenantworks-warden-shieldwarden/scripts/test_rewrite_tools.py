#!/usr/bin/env python3
"""Tests for rewrite_tools.py (stdlib unittest). Run from scripts/: python -m unittest test_rewrite_tools"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL = HERE / "rewrite_tools.py"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

OLD_A, NEW_A = "a" * 40, "1" * 40
OLD_B, NEW_B = "b" * 40, "2" * 40
OLD_C = "c" * 40                      # dropped by the rewrite
OLD_D, OLD_E = "d" * 7 + "e" * 33, "d" * 7 + "f" * 33   # share a short id


def run(*args):
    return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True,
                          creationflags=NO_WINDOW)


def git(cwd, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t", "-c", "commit.gpgsign=false",
                           "-c", "core.hooksPath=", *args], cwd=cwd, capture_output=True, text=True,
                          check=True, creationflags=NO_WINDOW).stdout.strip()


class RepointTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="rw-repoint-"))
        self.map = self.tmp / "commit-map.txt"
        self.map.write_text("old new\n" + "\n".join(
            [f"{OLD_A} {NEW_A}", f"{OLD_B} {NEW_B}", f"{OLD_C} {'0' * 40}", f"{OLD_D} {'3' * 40}",
             f"{OLD_E} {'4' * 40}"]) + "\n")
        self.runs = self.tmp / "runs"
        self.runs.mkdir()
        (self.runs / "ledger.md").write_bytes(f"row done at {OLD_A[:7]}\r\nland {OLD_B}\r\n".encode())
        (self.runs / "brief.md").write_bytes(f"confirm {OLD_A}\nnot an id: {OLD_A[:7]}9\n".encode())
        (self.runs / "odd.md").write_bytes(f"dropped {OLD_C[:7]}; shared {OLD_D[:7]}\n".encode())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_dry_run_counts_and_writes_nothing(self):
        before = (self.runs / "ledger.md").read_bytes()
        p = run("repoint", "--map", str(self.map), str(self.runs))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("found: 3 id(s) in 2 file(s)", p.stdout)
        self.assertIn("dropped commit", p.stdout)
        self.assertIn("ambiguous short id: ddddddd", p.stdout)
        self.assertEqual((self.runs / "ledger.md").read_bytes(), before)

    def test_apply_rewrites_ids_and_keeps_line_endings(self):
        p = run("repoint", "--map", str(self.map), str(self.runs), "--apply")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("replaced: 3 of 3; left after a second search: 0", p.stdout)
        self.assertEqual((self.runs / "ledger.md").read_bytes(),
                         f"row done at {NEW_A[:7]}\r\nland {NEW_B}\r\n".encode())
        self.assertEqual((self.runs / "brief.md").read_bytes(),
                         f"confirm {NEW_A}\nnot an id: {OLD_A[:7]}9\n".encode())
        # Never guessed: the dropped and the ambiguous ids stay as written.
        self.assertEqual((self.runs / "odd.md").read_bytes(),
                         f"dropped {OLD_C[:7]}; shared {OLD_D[:7]}\n".encode())


class RestoreAndSizeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="rw-restore-"))
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-b", "main")
        (self.repo / "logs").mkdir()
        for i in range(3):
            (self.repo / "logs" / f"run{i}.log").write_text(f"log {i}\n")
        (self.repo / "keep.txt").write_text("keep\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-m", "with logs")
        git(self.repo, "tag", "pre-rewrite")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_restore_brings_back_stripped_files_and_counts(self):
        # The rewrite's checkout removed the stripped files from disk (observation 0360).
        git(self.repo, "rm", "-r", "-q", "logs")
        git(self.repo, "commit", "-m", "strip logs")
        self.assertFalse((self.repo / "logs" / "run0.log").exists())
        p = run("restore", "--ref", "pre-rewrite", "--repo", str(self.repo), "logs")
        self.assertIn("expected from pre-rewrite: 3 file(s); missing on disk: 3", p.stdout)
        self.assertFalse((self.repo / "logs" / "run0.log").exists())
        p = run("restore", "--ref", "pre-rewrite", "--repo", str(self.repo), "logs", "--apply")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("expected 3 = present 3", p.stdout)
        self.assertEqual((self.repo / "logs" / "run2.log").read_text(), "log 2\n")

    def test_push_size_stops_over_the_limit(self):
        base = git(self.repo, "rev-parse", "HEAD")
        (self.repo / "big.bin").write_bytes(os.urandom(4096))
        git(self.repo, "add", "big.bin")
        git(self.repo, "commit", "-m", "big")
        p = run("push-size", "--repo", str(self.repo), "--range", f"{base}..HEAD", "--limit-mb", "0.001")
        self.assertEqual(p.returncode, 1)
        self.assertIn("big.bin", p.stdout)
        p = run("push-size", "--repo", str(self.repo), "--range", f"{base}..HEAD", "--limit-mb", "1")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("1 new blob(s)", p.stdout)


if __name__ == "__main__":
    unittest.main()
