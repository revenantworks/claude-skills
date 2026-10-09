#!/usr/bin/env python3
"""Tests for pixel_post.py (pixelsmith's diffusion-contract post-process).

Run: python -m unittest discover -s scripts -p "test_*.py"
Stdlib only; fixtures live in a temp directory.
"""
import json
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pixel_post as pp  # noqa: E402

SPEC = ("```spec\nnative: 4x4 px\npalette: [#28283c, #dcc878]  # dark to light\ncount: 2\n"
        "terrains: {grass: 45}\nkey_colour: #ff00ff\n```\n")
DARK, LIGHT, KEY = (40, 40, 60), (220, 200, 120), (255, 0, 255)


def candidate(factor: int = 2):
    """An 8x8 render of a 4x4 sprite at factor 2, with one-off colour noise on half the pixels."""
    cells = [KEY, LIGHT, LIGHT, KEY, LIGHT, DARK, DARK, LIGHT, LIGHT, DARK, DARK, LIGHT, KEY, LIGHT, LIGHT, KEY]
    w = h = 4 * factor
    px = []
    for y in range(h):
        for x in range(w):
            c = cells[(y // factor) * 4 + x // factor]
            px.append((min(c[0] + 3, 255), c[1], c[2], 255) if (x + y) % 2 else c + (255,))
    return w, h, px


class PixelPost(unittest.TestCase):
    def test_selftest(self):
        with unittest.mock.patch("builtins.print"):
            self.assertEqual(pp.selftest(), 0)

    def test_png_round_trip(self):
        w, h, px = candidate()
        self.assertEqual(pp.read_png(pp.write_png(w, h, px)), (w, h, px))

    def test_process_downscales_snaps_and_keys_out(self):
        w, h, px = candidate()
        cw, ch, out, screen = pp.process(w, h, px, pp.parse_spec(SPEC), 2)
        self.assertEqual((cw, ch), (4, 4))
        self.assertTrue(set(p[:3] for p in out if p[3] == 255) <= {DARK, LIGHT})
        self.assertEqual(screen["keyed_out_pixels"], 4)
        self.assertTrue(screen["survives"], screen)

    def test_wrong_factor_fails_the_size_screen(self):
        w, h, px = candidate()
        _, _, _, screen = pp.process(w, h, px, pp.parse_spec(SPEC), 4)
        self.assertIn("size", screen["failed_on"])

    def test_cli_writes_one_png_and_one_json_record(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            w, h, px = candidate()
            (d / "cand.png").write_bytes(pp.write_png(w, h, px))
            (d / "spec.txt").write_text(SPEC, encoding="utf-8")
            r = subprocess.run([sys.executable, str(HERE / "pixel_post.py"), str(d / "cand.png"), "--spec",
                                str(d / "spec.txt"), "--factor", "2", "--out", str(d / "out.png")],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            rec = json.loads(r.stdout)
            self.assertTrue((d / "out.png").is_file())
            self.assertEqual(pp.read_png((d / "out.png").read_bytes())[:2], (4, 4))
            self.assertIsInstance(rec, dict)

    def _cli(self, d, out, *extra):
        return subprocess.run([sys.executable, str(HERE / "pixel_post.py"), str(d / "cand.png"), "--spec",
                               str(d / "spec.txt"), "--factor", "2", "--out", str(out), *extra],
                              capture_output=True, text=True)

    def _inputs(self, d):
        w, h, px = candidate()
        (d / "cand.png").write_bytes(pp.write_png(w, h, px))
        (d / "spec.txt").write_text(SPEC, encoding="utf-8")

    def test_cli_refuses_to_write_over_an_input_even_with_force(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            self._inputs(d)
            before = (d / "cand.png").read_bytes()
            for extra in ((), ("--force",)):
                r = self._cli(d, d / "cand.png", *extra)
                self.assertEqual(r.returncode, 2, r.stderr)
                self.assertEqual((d / "cand.png").read_bytes(), before)
            self.assertEqual(self._cli(d, d / "spec.txt", "--force").returncode, 2)

    def test_cli_refuses_an_existing_out_unless_forced(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            self._inputs(d)
            (d / "out.png").write_bytes(b"keep")
            r = self._cli(d, d / "out.png")
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertEqual((d / "out.png").read_bytes(), b"keep")
            r = self._cli(d, d / "out.png", "--force")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(pp.read_png((d / "out.png").read_bytes())[:2], (4, 4))


if __name__ == "__main__":
    unittest.main()
