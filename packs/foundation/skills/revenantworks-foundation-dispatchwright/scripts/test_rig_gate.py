"""Tests for rig_gate.py: every bound, every adapter's not-measured path, and the command line.

    python -m unittest discover -s scripts -p "test_*.py"

No test lists, samples or signals a live process: the process listing, the CPU sample, the pid
check and git are replaced by plain functions, and every file lives in a temp folder.
"""
import contextlib
import io
import json
import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import rig_gate  # noqa: E402

GODOT = "godot --headless -s addons/gut/gut_cmdln.gd -gexit"


def listing(n_engines, extra=()):
    """A process listing with n headless engine runs under one shell, plus extra command lines."""
    procs = [(100, 1, "bash")]
    procs += [(200 + i, 100, GODOT) for i in range(n_engines)]
    procs += [(900 + i, 1, line) for i, line in enumerate(extra)]
    return lambda: procs


def readings(cfg, engines=0, cpu=20.0, extra=(), alive=lambda pid: False, git=None, now=None):
    return rig_gate.read_signals(cfg, listing=listing(engines, extra), cpu=lambda: cpu, alive=alive,
                                 git=git or (lambda args, cwd: (1, "")), now=now or time.time())


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="rig-gate-")
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))

    def path(self, *parts):
        return os.path.join(self.tmp, *parts)

    def write(self, rel, data):
        p = self.path(rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(data if isinstance(data, str) else json.dumps(data))
        return p

    def verdict(self, cfg, heavy=True, **kw):
        sig = readings(cfg, **kw)
        return rig_gate.evaluate(sig, cfg, heavy=heavy)


class NoConfig(Base):
    def test_a_repo_without_run_tools_passes_with_signals_not_measured(self):
        ok, lines = self.verdict(rig_gate.config({}), engines=2)
        self.assertTrue(ok, lines)
        text = "\n".join(lines)
        for name in ("check queue", "land", "unlanded branches"):
            self.assertIn(f"{name}: not measured", text)

    def test_a_missing_listing_and_cpu_are_not_measured_never_a_crash(self):
        def broken():
            raise OSError("no process listing here")
        sig = rig_gate.read_signals(rig_gate.config({}), listing=broken, cpu=lambda: None,
                                    alive=lambda pid: False, git=lambda a, c: (1, ""), now=time.time())
        ok, lines = rig_gate.evaluate(sig, rig_gate.config({}), heavy=True)
        self.assertTrue(ok, lines)
        self.assertIn("busy engines: not measured", "\n".join(lines))
        self.assertIn("cpu: not measured", "\n".join(lines))


class Engines(Base):
    def test_busy_over_budget_minus_two_refuses_a_heavy_launch(self):
        cfg = rig_gate.config({"rig_budget": 10})
        ok, lines = self.verdict(cfg, engines=9)
        self.assertFalse(ok)
        self.assertIn("busy engines 9 over 8", "\n".join(lines))
        ok, _ = self.verdict(cfg, engines=8)
        self.assertTrue(ok)

    def test_a_self_hosted_runner_job_counts_two(self):
        cfg = rig_gate.config({"rig_budget": 10})
        ok, lines = self.verdict(cfg, engines=7, extra=["actions-runner/bin/Runner.Worker spawnclient 1 2"])
        self.assertFalse(ok, lines)

    def test_a_light_launch_passes_a_full_rig(self):
        cfg = rig_gate.config({"rig_budget": 10})
        ok, lines = self.verdict(cfg, heavy=False, engines=14, cpu=99.0)
        self.assertTrue(ok, lines)

    def test_the_default_budget_is_derived_from_the_cores(self):
        self.assertEqual(rig_gate.default_budget(16), 10)
        self.assertEqual(rig_gate.default_budget(4), 4)


class Cpu(Base):
    def test_cpu_at_the_limit_refuses(self):
        cfg = rig_gate.config({})
        ok, lines = self.verdict(cfg, cpu=85.0)
        self.assertFalse(ok)
        self.assertIn("cpu 85% at or over 85%", "\n".join(lines))
        ok, _ = self.verdict(cfg, cpu=84.0)
        self.assertTrue(ok)


class Queue(Base):
    def cfg(self, **extra):
        d = {"queue_dir": self.path("queue"), "check_lanes": 3, "default_check_s": 900}
        d.update(extra)
        os.makedirs(self.path("queue"), exist_ok=True)
        return rig_gate.config(d)

    def test_queue_wait_over_the_horizon_refuses(self):
        cfg = self.cfg()
        for i in range(4):
            self.write(f"queue/U{i}.json", {"unit": f"U{i}", "queued": 1})
        ok, lines = self.verdict(cfg)
        self.assertTrue(ok, lines)          # 4 x 900 s / 3 lanes = 20 min
        for i in range(4, 12):
            self.write(f"queue/U{i}.json", {"unit": f"U{i}", "queued": 1})
        ok, lines = self.verdict(cfg)       # 12 x 900 s / 3 lanes = 60 min
        self.assertFalse(ok)
        self.assertIn("queue wait 60 min over 45", "\n".join(lines))

    def test_a_request_carries_its_own_expected_seconds(self):
        cfg = self.cfg()
        self.write("queue/BIG.json", {"unit": "BIG", "expected_s": 9000})
        ok, lines = self.verdict(cfg)
        self.assertFalse(ok, lines)

    def test_a_hosted_run_in_flight_refuses_a_heavy_launch(self):
        cfg = self.cfg()
        self.write("queue/HOSTED", {"on": True, "why": "land branch run", "pid": 1, "at": time.time()})
        ok, lines = self.verdict(cfg)
        self.assertFalse(ok)
        self.assertIn("branch CI run in flight", "\n".join(lines))

    def test_runner_state_and_verdicts_are_not_requests(self):
        cfg = self.cfg()
        self.write("queue/runner.json", {"pid": 5, "running": [{"unit": "A"}]})
        self.write("queue/verdicts/A.json", {"verdict": "GREEN"})
        sig = readings(cfg)
        self.assertEqual(sig["queue"]["value"]["pending"], 0)
        self.assertEqual(sig["queue"]["value"]["running"], 1)

    def test_an_unreadable_request_is_skipped_and_named(self):
        cfg = self.cfg()
        self.write("queue/BAD.json", "{not json")
        sig = readings(cfg)
        self.assertTrue(sig["queue"]["measured"])
        self.assertIn("BAD.json", sig["queue"]["detail"])


class Land(Base):
    def test_a_live_land_flag_refuses(self):
        flag = self.write("land-running.json", {"pid": 4242, "started": time.time() - 60})
        cfg = rig_gate.config({"land_flag": flag})
        ok, lines = self.verdict(cfg, alive=lambda pid: pid == 4242)
        self.assertFalse(ok)
        self.assertIn("land walk running", "\n".join(lines))
        ok, _ = self.verdict(cfg, alive=lambda pid: False)       # a dead land holds nothing
        self.assertTrue(ok)

    def test_an_old_land_flag_is_ignored(self):
        flag = self.write("land-running.json", {"pid": 4242, "started": time.time() - 5 * 3600})
        ok, _ = self.verdict(rig_gate.config({"land_flag": flag}), alive=lambda pid: True)
        self.assertTrue(ok)

    def test_a_red_land_verdict_or_red_main_refuses(self):
        red = self.write("land.json", {"verdict": "RED"})
        ok, lines = self.verdict(rig_gate.config({"land_verdict": red}))
        self.assertFalse(ok)
        self.assertIn("land verdict RED", "\n".join(lines))
        nightly = self.write("STATUS-main.json", {"verdict": "RED"})
        ok, lines = self.verdict(rig_gate.config({"nightly_status": nightly}))
        self.assertFalse(ok)
        self.assertIn("main RED", "\n".join(lines))
        green = self.write("land2.json", {"verdict": "GREEN"})
        ok, _ = self.verdict(rig_gate.config({"land_verdict": green}))
        self.assertTrue(ok)


class Wip(Base):
    def test_unlanded_branches_at_the_limit_refuse_a_build(self):
        cfg = rig_gate.config({"wip": {"repo": self.tmp, "branch_glob": "claude/*", "base": "origin/main"}})
        six = "\n".join(f"  claude/b{i}" for i in range(6))
        ok, lines = self.verdict(cfg, git=lambda args, cwd: (0, six))
        self.assertFalse(ok)
        self.assertIn("unlanded branches 6 at the limit 6", "\n".join(lines))
        five = "\n".join(f"  claude/b{i}" for i in range(5))
        ok, _ = self.verdict(cfg, git=lambda args, cwd: (0, five))
        self.assertTrue(ok)

    def test_a_git_failure_is_not_measured(self):
        cfg = rig_gate.config({"wip": {"repo": self.tmp}})
        sig = readings(cfg, git=lambda args, cwd: (128, "fatal: not a git repository"))
        self.assertFalse(sig["wip"]["measured"])


class CommandLine(Base):
    def run_main(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = rig_gate.main(argv, listing=listing(0), cpu=lambda: 10.0, alive=lambda p: False,
                                 git=lambda a, c: (1, ""))
        return code, out.getvalue(), err.getvalue()

    def test_pass_and_refuse_exit_codes_and_json(self):
        cfg = self.write("cfg.json", {"rig_budget": 10})
        code, out, _ = self.run_main(["check", "--heavy", "--config", cfg, "--json"])
        self.assertEqual(code, 0, out)
        self.assertTrue(json.loads(out)["ok"])
        red = self.write("land.json", {"verdict": "RED"})
        cfg2 = self.write("cfg2.json", {"land_verdict": red})
        code, out, _ = self.run_main(["check", "--heavy", "--config", cfg2])
        self.assertEqual(code, 1, out)
        self.assertIn("REFUSED", out)

    def test_a_broken_config_is_exit_two(self):
        cfg = self.write("cfg.json", "{not json")
        code, _, err = self.run_main(["check", "--heavy", "--config", cfg])
        self.assertEqual(code, 2)
        self.assertIn("config", err)

    def test_an_absent_default_config_is_no_config(self):
        code, out, _ = self.run_main(["check", "--heavy", "--config", self.path("absent.json")])
        self.assertEqual(code, 0, out)


if __name__ == "__main__":
    unittest.main()
