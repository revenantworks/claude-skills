"""Tests for workflow_guard.py (stdlib unittest; run from this folder or by discover).

The guard's own --selftest covers classification, budgets, rewrites and the recipe
check; these tests run it and add the crash-size config (audit C-4): the crash
reference is read from gpu-config.json "comfy" -> "crash_size", and the built-in
figure is a labelled proposal, never an owner value.
"""
import copy
import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import workflow_guard as wg  # noqa: E402


def wan(w, h, n, decode="VAEDecodeTiled"):
    return {
        "1": {"class_type": "Wan22ImageToVideoLatent", "inputs": {"width": w, "height": h, "length": n,
                                                                    "batch_size": 1, "vae": ["2", 0]}},
        "2": {"class_type": "VAELoader", "inputs": {"vae_name": "v.safetensors"}},
        "3": {"class_type": "KSampler", "inputs": {"latent_image": ["1", 0], "steps": 20}},
        "4": {"class_type": decode, "inputs": {"samples": ["3", 0], "vae": ["2", 0]}},
        "8": {"class_type": "CreateVideo", "inputs": {"images": ["4", 0], "fps": 24}},
        "9": {"class_type": "SaveVideo", "inputs": {"video": ["8", 0], "filename_prefix": "wan"}},
    }


OWNER = {"comfy": {"image_pixels_max": 1048576, "video_pixel_frames_max": 50_000_000,
                   "audio_seconds_max": 120, "max_run_minutes": 30}}


class SelftestTest(unittest.TestCase):
    def test_selftest_passes(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(wg.selftest(), 0)
        self.assertIn("selftest: ok", buf.getvalue())


class CrashSizeTest(unittest.TestCase):
    def test_default_crash_size_is_a_labelled_proposal(self):
        lim = wg.limits_from({})
        self.assertEqual(lim["crash_size"]["value"], 1024 * 1024 * 121)
        self.assertTrue(lim["crash_size"]["source"].startswith("PROPOSED"))
        self.assertIn("reported case", lim["crash_size"]["source"])

    def test_owner_crash_size_object_is_read(self):
        cfg = copy.deepcopy(OWNER)
        cfg["comfy"]["crash_size"] = {"width": 832, "height": 480, "frames": 81}
        lim = wg.limits_from(cfg)
        self.assertEqual(lim["crash_size"]["value"], 832 * 480 * 81)
        self.assertTrue(lim["crash_size"]["source"].startswith("owner"))

    def test_owner_crash_size_integer_is_read(self):
        cfg = copy.deepcopy(OWNER)
        cfg["comfy"]["crash_size"] = 40_000_000
        self.assertEqual(wg.limits_from(cfg)["crash_size"]["value"], 40_000_000)

    def test_bad_crash_size_falls_back_to_the_proposal(self):
        for bad in (0, -5, True, "big", {"width": 832}, {"width": 0, "height": 480, "frames": 81}):
            cfg = copy.deepcopy(OWNER)
            cfg["comfy"]["crash_size"] = bad
            lim = wg.limits_from(cfg)
            self.assertTrue(lim["crash_size"]["source"].startswith("PROPOSED"), bad)

    def test_crash_ratio_uses_the_configured_size(self):
        cfg = copy.deepcopy(OWNER)
        cfg["comfy"]["crash_size"] = {"width": 832, "height": 480, "frames": 81}
        res = wg.judge(wan(832, 480, 81), "unattended", cfg)
        self.assertEqual(res["jobs"][0]["crash_ratio"], 1.0)
        self.assertEqual(res["verdict"], "refuse")
        self.assertTrue(any("crash size" in r for r in res["reasons"]))

    def test_proposed_video_budget_is_half_the_configured_crash(self):
        cfg = {"comfy": {"crash_size": 40_000_000}}
        lim = wg.limits_from(cfg)
        self.assertEqual(lim["video_pixel_frames_max"]["value"], 20_000_000)
        self.assertTrue(lim["video_pixel_frames_max"]["source"].startswith("PROPOSED"))

    def test_owner_set_crash_size_does_not_change_a_small_go(self):
        cfg = copy.deepcopy(OWNER)
        cfg["comfy"]["crash_size"] = 200_000_000
        self.assertEqual(wg.judge(wan(832, 480, 33), "unattended", cfg)["verdict"], "go")

    def test_unset_crash_size_does_not_gate_an_owner_budget(self):
        # The crash size is a reference, not a budget: leaving it unset never refuses on its own.
        self.assertEqual(wg.judge(wan(832, 480, 33), "unattended", OWNER)["verdict"], "go")


if __name__ == "__main__":
    unittest.main()
