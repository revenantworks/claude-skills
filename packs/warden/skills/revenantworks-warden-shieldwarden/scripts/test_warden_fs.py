"""Tests for warden_fs.py, the pack-shared path helpers (packs/warden/shared/). Stdlib unittest.

    python -m unittest discover -s scripts -p "test_*.py"
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from warden_fs import looks_secret, redact  # noqa: E402

FAKE_KEY = "sk-" + "live" + "A1b2C3d4E5f6G7h8I9j0K1l2"  # built at runtime: a secret shape, not a secret


class RedactTests(unittest.TestCase):
    def test_home_and_secret_segments(self):
        home = str(Path.home())
        self.assertTrue(redact(os.path.join(home, "docs", "x.txt")).startswith("~/"))
        self.assertIn("<redacted>", redact("/srv/" + FAKE_KEY + "/f"))
        self.assertTrue(looks_secret(FAKE_KEY))
        self.assertFalse(looks_secret("node_modules"))


if __name__ == "__main__":
    unittest.main()
