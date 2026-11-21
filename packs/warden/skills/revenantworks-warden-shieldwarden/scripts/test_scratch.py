"""Tests for _scratch.py, the pack-shared test-folder removal (packs/warden/shared/). Stdlib unittest.

    python -m unittest discover -s scripts -p "test_*.py"
"""
from __future__ import annotations

import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from _scratch import force_rmtree  # noqa: E402


class ForceRmtree(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix="wscratch-"))
        self.addCleanup(force_rmtree, self.base)

    def test_read_only_files_like_git_objects_are_removed(self):
        """Git writes object files read-only; plain rmtree cannot delete them on Windows."""
        repo = self.base / "repo"
        obj = repo / ".git" / "objects" / "ab" / "cdef"
        obj.parent.mkdir(parents=True)
        obj.write_bytes(b"x")
        os.chmod(obj, stat.S_IREAD)
        force_rmtree(repo)
        self.assertFalse(repo.exists())

    def test_accepts_str_and_path(self):
        for name in ("a", "b"):
            (self.base / name / "f").parent.mkdir(parents=True)
            (self.base / name / "f").write_text("x")
        force_rmtree(str(self.base / "a"))
        force_rmtree(self.base / "b")
        self.assertEqual(list(self.base.iterdir()), [])

    def test_never_raises_on_nothing(self):
        force_rmtree(None)
        force_rmtree("")
        force_rmtree(self.base / "missing")


if __name__ == "__main__":
    unittest.main()
