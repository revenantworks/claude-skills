"""Tests for comfy_client.py fetch scope (stdlib unittest; run from this folder or by discover).

K7-5-10: fetch with no --out once wrote server outputs into the current folder, which may be a
repo. It now refuses before any network call.
"""
import argparse
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comfy_client  # noqa: E402


class FetchNeedsOut(unittest.TestCase):
    def test_fetch_without_out_refuses_and_calls_nothing(self):
        called = []
        orig = comfy_client.call
        comfy_client.call = lambda *a, **k: called.append(a) or {}
        try:
            res = comfy_client.run(argparse.Namespace(cmd="fetch", target="abc", out=None))
        finally:
            comfy_client.call = orig
        self.assertIn("error", res)
        self.assertIn("--out", res["error"])
        self.assertEqual(called, [])


if __name__ == "__main__":
    unittest.main()
