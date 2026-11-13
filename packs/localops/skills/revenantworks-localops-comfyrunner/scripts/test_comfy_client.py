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


class NodesAllSavesTheWholeInfo(unittest.TestCase):
    def test_all_saves_every_class_from_one_call(self):
        import json
        import tempfile
        called = []
        orig = comfy_client.call
        comfy_client.call = lambda a, path, *r, **k: called.append(path) or {"KSampler": {}, "ZImageLoader": {}}
        try:
            with tempfile.TemporaryDirectory() as td:
                f = Path(td) / "info.json"
                res = comfy_client.run(argparse.Namespace(cmd="nodes", target=None, all=True, save_info=str(f)))
                self.assertEqual(json.loads(f.read_text(encoding="utf-8")).keys(), {"KSampler", "ZImageLoader"})
        finally:
            comfy_client.call = orig
        self.assertEqual(called, ["/object_info"])
        self.assertEqual(res["classes_saved"], 2)

    def test_all_without_save_info_refuses_and_calls_nothing(self):
        called = []
        orig = comfy_client.call
        comfy_client.call = lambda *a, **k: called.append(a) or {}
        try:
            res = comfy_client.run(argparse.Namespace(cmd="nodes", target=None, all=True, save_info=None))
        finally:
            comfy_client.call = orig
        self.assertIn("--save-info", res["error"])
        self.assertEqual(called, [])


if __name__ == "__main__":
    unittest.main()
