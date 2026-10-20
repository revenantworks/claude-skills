"""Tests for rig_gate.py: every bound, every adapter's not-measured path, and the command line.

    python -m unittest discover -s scripts -p "test_*.py"

No test lists, samples or signals a live process: the process listing, the CPU sample, the pid
check and git are replaced by plain functions, and every file lives in a temp folder.
"""
import contextlib
import io
import json
import os
import subprocess
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

    def test_a_missing_listing_and_cpu_are_not_measured_never_a_crash_and_refuse_a_heavy_launch(self):
        # RV-SKILLS-WF F2: with neither machine signal measured, a heavy launch has no check left.
        def broken():
            raise OSError("no process listing here")
        sig = rig_gate.read_signals(rig_gate.config({}), listing=broken, cpu=lambda: None,
                                    alive=lambda pid: False, git=lambda a, c: (1, ""), now=time.time())
        ok, lines = rig_gate.evaluate(sig, rig_gate.config({}), heavy=True)
        self.assertFalse(ok, lines)
        text = "\n".join(lines)
        self.assertIn("busy engines: not measured", text)
        self.assertIn("cpu: not measured", text)
        self.assertIn("REFUSED busy engines and cpu both not measured", text)
        ok, _ = rig_gate.evaluate(sig, rig_gate.config({}), heavy=False)
        self.assertTrue(ok)


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


GODOT_EXE = '"C:\\Program Files\\Godot\\Godot_v4.7.2-stable_win64.exe"  --headless -s addons/gut/gut_cmdln.gd -gexit'
CMD_SHIM = "C:\\WINDOWS\\system32\\cmd.exe /c ~/.local/bin/godot.CMD --headless -s addons/gut/gut_cmdln.gd -gexit"
SLOT = "python.exe RUN/suite_slot.py --cwd wt -- godot --headless -s addons/gut/gut_cmdln.gd -gexit"
GIT_BASH = '"C:\\Program Files\\Git\\bin\\bash.exe" -c "timeout 580 godot --headless -s x.gd"'
MSYS_TIMEOUT = '"C:\\Program Files\\Git\\usr\\bin\\timeout.exe" 580 python RUN/suite_slot.py -- godot --headless -gexit'
REAL_SHAPE = [
    # A live turbo listing's shape (paths cut to generic ones): a queue runner, two scope checks,
    # suite_slot waiters and holders, cmd wrappers, the engines, a Git Bash wrapper whose own text
    # carries the engine words, and an orphaned MSYS timeout whose parent bash has exited.
    (10, 1, "python.exe run_queue.py run --parallel 3"),
    (11, 10, "python.exe RUN/scope_check.py --worktree wt-a --base 0f80bf04"),
    (12, 10, "python.exe RUN/scope_check.py --worktree wt-b --base 0f80bf04"),
    (20, 11, SLOT), (21, 20, CMD_SHIM), (22, 21, GODOT_EXE),
    (23, 11, SLOT), (24, 11, SLOT),
    (30, 12, SLOT), (31, 30, CMD_SHIM), (32, 31, GODOT_EXE),
    (40, 1, GIT_BASH), (41, 40, GIT_BASH.replace("bin\\bash", "usr\\bin\\bash")),
    (50, 999, MSYS_TIMEOUT), (51, 50, MSYS_TIMEOUT), (52, 51, SLOT), (53, 52, CMD_SHIM), (54, 53, GODOT_EXE),
    (60, 1, "C:\\Program Files\\Git\\usr\\bin\\timeout.exe 580 python -m unittest discover"),
    (61, 60, "python.exe -m unittest discover -s tools"),
    (62, 61, "python.exe -m unittest a_child_the_suite_started"),
]


class EngineCount(Base):
    """RV-SKILLS-WF F4: an engine counts once, as the process that is the engine; a wrapper whose
    arguments carry the engine words (suite_slot waiting for a slot, cmd, Git Bash, timeout) is no
    engine, and the slot registry's waiting records never count."""

    def test_a_real_turbo_listing_counts_each_engine_once(self):
        sig = rig_gate.read_signals(rig_gate.config({}), listing=lambda: list(REAL_SHAPE), cpu=lambda: 10.0,
                                    alive=lambda p: False, git=lambda a, c: (1, ""), now=time.time())
        self.assertEqual(sig["engines"]["value"], 4, sig["engines"])   # three Godot runs + one unittest

    def test_a_waiting_slot_record_never_counts_and_the_registry_running_count_is_a_floor(self):
        reg = self.path("slots")
        os.makedirs(reg)
        self.write("slots/70.json", {"pid": 70, "state": "waiting"})
        for pid in (80, 81, 82, 83, 84):
            self.write(f"slots/{pid}.json", {"pid": pid, "state": "running"})
        procs = [(70, 1, "godot --headless -s a.gd")]                  # an engine-shaped waiter
        cfg = rig_gate.config({"slot_registry": reg})
        sig = rig_gate.read_signals(cfg, listing=lambda: procs, cpu=lambda: 10.0, alive=lambda p: True,
                                    git=lambda a, c: (1, ""), now=time.time())
        self.assertEqual(sig["engines"]["value"], 5, sig["engines"])   # registry running 5 > listing 0
        self.assertIn("slot registry", sig["engines"]["detail"])


CI_LOCAL = "python.exe tools/ci_local_evolution_v2.py --shards 6"


def sharded_walk(base, shards, parent=1):
    """A ci_local walk that Popens `godot --headless` once per shard through the godot.cmd shim
    (do_gut_sharded), not through suite_slot: ci_local -> cmd shim -> Godot, per shard."""
    procs = [(base, parent, CI_LOCAL)]
    for i in range(shards):
        shim, exe = base + 1 + 2 * i, base + 2 + 2 * i
        procs += [(shim, base, CMD_SHIM), (exe, shim, GODOT_EXE)]
    return procs


class LeafEngines(Base):
    """RV-SKILLS2-WF F2: busy engines counts the leaf engines (an engine with no engine below it),
    and a headless Godot always counts, even under a suite engine, so a 6-shard ci_local walk is 6."""

    def engines(self, procs):
        sig = rig_gate.read_signals(rig_gate.config({}), listing=lambda: list(procs), cpu=lambda: 10.0,
                                    alive=lambda p: False, git=lambda a, c: (1, ""), now=time.time())
        return sig["engines"]

    def test_a_ci_local_parent_with_n_godot_shards_counts_n(self):
        for n in (1, 2, 6):
            with self.subTest(shards=n):
                e = self.engines(sharded_walk(100, n))
                self.assertEqual(e["value"], n, e)

    def test_the_reviews_listing_reads_seven(self):
        # One 6-shard walk plus one suite_slot Godot: 7 Godot processes, read as 2 before the fix.
        procs = sharded_walk(100, 6) + [(200, 1, SLOT), (201, 200, CMD_SHIM), (202, 201, GODOT_EXE)]
        self.assertEqual(self.engines(procs)["value"], 7)

    def test_two_sharded_walks_and_a_slot_unit_count_every_godot(self):
        procs = (sharded_walk(100, 6) + sharded_walk(300, 6)
                 + [(500, 1, SLOT), (501, 500, CMD_SHIM), (502, 501, GODOT_EXE)])
        self.assertEqual(self.engines(procs)["value"], 13)

    def test_a_walk_with_no_engine_child_yet_counts_itself(self):
        self.assertEqual(self.engines([(100, 1, CI_LOCAL)])["value"], 1)

    def test_a_suite_chain_still_counts_once(self):
        # ci_stamp over ci_local over unittest: one suite, its leaf counts.
        procs = [(10, 1, "python.exe tools/ci_local.py --skip warden-suites"),
                 (11, 10, "python.exe -m unittest discover -s tools")]
        self.assertEqual(self.engines(procs)["value"], 1)

    def test_a_headless_godot_under_a_headless_godot_counts_both(self):
        procs = [(10, 1, GODOT_EXE), (11, 10, GODOT_EXE.replace("gut_cmdln.gd", "child.gd"))]
        self.assertEqual(self.engines(procs)["value"], 2)


class ListingFailures(Base):
    """RV-SKILLS-WF F2: a failed, empty or timed-out listing is "not measured", never a measured 0."""

    def run_stub(self, code=0, out="", raise_=None):
        def run(cmd, **kw):
            if raise_ is not None:
                raise raise_
            return subprocess.CompletedProcess(cmd, code, stdout=out, stderr="")
        return run

    def engines_with(self, run):
        return rig_gate.read_engines(rig_gate.config({}), lambda: rig_gate.list_processes(run=run))

    def test_a_non_zero_exit_is_not_measured(self):
        s = self.engines_with(self.run_stub(code=1, out=""))
        self.assertFalse(s["measured"], s)
        self.assertIn("exit 1", s["detail"])

    def test_an_empty_listing_is_not_measured(self):
        s = self.engines_with(self.run_stub(code=0, out="\n"))
        self.assertFalse(s["measured"], s)
        self.assertIn("empty", s["detail"])

    def test_a_timed_out_listing_is_not_measured(self):
        s = self.engines_with(self.run_stub(raise_=subprocess.TimeoutExpired("ps", 4)))
        self.assertFalse(s["measured"], s)

    def test_a_good_listing_is_measured(self):
        out = "1\t0\tSystem\n200\t1\tgodot --headless -s a.gd\n" if rig_gate.WINDOWS else \
            "1 0 init\n200 1 godot --headless -s a.gd\n"
        s = self.engines_with(self.run_stub(code=0, out=out))
        self.assertTrue(s["measured"], s)
        self.assertEqual(s["value"], 1)

    def test_engines_unmeasured_with_cpu_measured_still_passes(self):
        def broken():
            raise OSError("no listing")
        cfg = rig_gate.config({})
        sig = rig_gate.read_signals(cfg, listing=broken, cpu=lambda: 20.0, alive=lambda p: False,
                                    git=lambda a, c: (1, ""), now=time.time())
        ok, lines = rig_gate.evaluate(sig, cfg, heavy=True)
        self.assertTrue(ok, lines)
        self.assertIn("busy engines: not measured", "\n".join(lines))


class Budget(Base):
    """RV-SKILLS-WF F1: the gate answers inside the guard's budget (6 s), so the hook's own
    registered timeout never kills the guard (a killed hook does not block)."""

    def test_every_subprocess_timeout_fits_inside_the_gate_budget(self):
        self.assertLessEqual(rig_gate.GATE_BUDGET_S, 6)
        self.assertLess(rig_gate.LISTING_TIMEOUT_S, rig_gate.GATE_BUDGET_S - 1)
        self.assertLess(rig_gate.GIT_TIMEOUT_S, rig_gate.GATE_BUDGET_S - 1)
        self.assertLess(rig_gate.CPU_WINDOW_MAX_S, rig_gate.GATE_BUDGET_S - 1)
        self.assertLessEqual(rig_gate.config({"cpu_window_s": 30})["cpu_window_s"], rig_gate.CPU_WINDOW_MAX_S)

    def test_the_slow_reads_run_at_once(self):
        def slow(value):
            def f(*a, **k):
                time.sleep(1.2)
                return value
            return f
        cfg = rig_gate.config({"wip": {"repo": self.tmp, "verified_file": self.write("v.json", [])}})
        t0 = time.monotonic()
        rig_gate.read_signals(cfg, listing=slow([(1, 0, "init")]), cpu=slow(10.0), alive=lambda p: False,
                              git=slow((0, "")), now=time.time())
        self.assertLess(time.monotonic() - t0, 2.3)


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

    def test_a_running_check_counts_once_not_as_a_request_too(self):
        # RV-SKILLS-WF F5: run_queue keeps a running check's request file; 3 running + 5 queued is
        # (5 x 900 + 3 x 450) / 3 lanes = 32.5 min, not 47.5.
        cfg = self.cfg()
        running = {f"R{i}": "a" * 40 for i in range(3)}
        for u in list(running) + [f"Q{i}" for i in range(5)]:
            self.write(f"queue/{u}.json", {"unit": u, "queued": 1})
        self.write("queue/runner.json", {"pid": 5, "running": running})
        sig = readings(cfg)
        self.assertEqual(sig["queue"]["value"]["pending"], 5, sig["queue"])
        self.assertEqual(sig["queue"]["value"]["running"], 3)
        self.assertAlmostEqual(sig["queue"]["value"]["wait_min"], 32.5, places=1)
        ok, lines = rig_gate.evaluate(sig, cfg)
        self.assertTrue(ok, lines)

    def test_a_running_list_of_units_is_read_the_same_way(self):
        cfg = self.cfg()
        self.write("queue/A.json", {"unit": "A"})
        self.write("queue/runner.json", {"running": [{"unit": "A"}]})
        self.assertEqual(readings(cfg)["queue"]["value"]["pending"], 0)

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
    """RV-SKILLS-WF F7, F8: the bound counts verified branches not merged into base (a GREEN queue
    verdict on the branch tip, or a name in wip.verified_file), any branch name, and refuses builds
    only: at the limit a join or a land still launches."""

    def cfg(self, verified=None, glob=None):
        os.makedirs(self.path("queue", "verdicts"), exist_ok=True)
        wip = {"repo": self.tmp, "base": "origin/main"}
        if glob:
            wip["branch_glob"] = glob
        if verified is not None:
            wip["verified_file"] = self.write("verified.json", verified)
        return rig_gate.config({"queue_dir": self.path("queue"), "wip": wip})

    def green(self, unit, head, **extra):
        self.write(f"queue/verdicts/{unit}.json", dict({"unit": unit, "head": head, "verdict": "GREEN"}, **extra))

    @staticmethod
    def sha(i):
        return (format(i, "x") * 40)[:40]

    def refs(self, names):
        out = "\n".join(f"{n}\t{self.sha(i)}" for i, n in enumerate(names, 1))
        return lambda args, cwd: (0, out)

    def test_six_verified_unlanded_branches_refuse_a_build_and_pass_a_join_or_land(self):
        cfg = self.cfg()
        names = ["e10", "aud4", "claude/x", "fx", "sky1", "sky2"]
        for i, n in enumerate(names, 1):
            self.green(f"U{i}", self.sha(i))
        sig = readings(cfg, git=self.refs(names))
        self.assertEqual(sig["wip"]["value"], 6, sig["wip"])
        ok, lines = rig_gate.evaluate(sig, cfg, heavy=True, kind="build")
        self.assertFalse(ok)
        self.assertIn("unlanded branches 6 at the limit 6", "\n".join(lines))
        for kind in ("join", "land"):
            ok, lines = rig_gate.evaluate(sig, cfg, heavy=True, kind=kind)
            self.assertTrue(ok, (kind, lines))

    def test_unverified_branches_do_not_count(self):
        cfg = self.cfg()
        names = [f"claude/b{i}" for i in range(1, 9)]          # 8 unmerged branches, running units' work
        self.green("U1", self.sha(1))                           # only b1's tip has a GREEN verdict
        self.green("U2", "f" * 40)                              # a GREEN head that is no branch tip
        self.write("queue/verdicts/U3.json", {"unit": "U3", "head": self.sha(3), "verdict": "RED"})
        self.green("U4", self.sha(4), superseded_by="a" * 40)   # a stale verdict for an older head
        sig = readings(cfg, git=self.refs(names))
        self.assertEqual(sig["wip"]["value"], 1, sig["wip"])

    def test_a_verified_file_names_branches_too(self):
        cfg = self.cfg(verified={"branches": ["e10", "gone"]})
        sig = readings(cfg, git=self.refs(["e10", "aud4"]))
        self.assertEqual(sig["wip"]["value"], 1, sig["wip"])

    def test_the_listing_is_one_no_merged_call_over_every_branch_name(self):
        seen = []

        def git(args, cwd):
            seen.append(list(args))
            return 0, ""
        readings(self.cfg(), git=git)
        self.assertEqual(len(seen), 1, seen)
        self.assertIn("--no-merged=origin/main", seen[0])
        self.assertNotIn("claude/*", " ".join(seen[0]))

    def test_a_branch_glob_still_narrows_the_set_when_given(self):
        cfg = self.cfg(glob="claude/*")
        self.green("U1", self.sha(1))
        self.green("U2", self.sha(2))
        sig = readings(cfg, git=self.refs(["e10", "claude/b2"]))
        self.assertEqual(sig["wip"]["value"], 1, sig["wip"])

    def test_no_verified_source_is_not_measured(self):
        cfg = rig_gate.config({"wip": {"repo": self.tmp}})
        sig = readings(cfg, git=self.refs(["claude/b1"]))
        self.assertFalse(sig["wip"]["measured"])
        self.assertIn("verified", sig["wip"]["detail"])

    def test_a_git_failure_is_not_measured(self):
        sig = readings(self.cfg(), git=lambda args, cwd: (128, "fatal: not a git repository"))
        self.assertFalse(sig["wip"]["measured"])


class Fixer(Base):
    """RV-SKILLS-WF F6: a red land's own fixer passes the red-verdict bound; nothing else does, and
    a land walk in flight still holds it."""

    def test_red_land_passes_its_fixer_and_refuses_any_other_heavy_row(self):
        red = self.write("land.json", {"verdict": "RED"})
        cfg = rig_gate.config({"land_verdict": red})
        sig = readings(cfg)
        ok, lines = rig_gate.evaluate(sig, cfg, heavy=True, fixer_of="LAND31")
        self.assertTrue(ok, lines)
        self.assertIn("fixer of LAND31", "\n".join(lines))
        ok, lines = rig_gate.evaluate(sig, cfg, heavy=True)
        self.assertFalse(ok)

    def test_red_main_passes_its_fixer(self):
        nightly = self.write("STATUS-main.json", {"verdict": "RED"})
        cfg = rig_gate.config({"nightly_status": nightly})
        ok, lines = rig_gate.evaluate(readings(cfg), cfg, heavy=True, fixer_of="main")
        self.assertTrue(ok, lines)

    def test_a_land_walk_still_holds_the_fixer(self):
        flag = self.write("land-running.json", {"pid": 4242, "started": time.time() - 60})
        cfg = rig_gate.config({"land_flag": flag})
        ok, _ = rig_gate.evaluate(readings(cfg, alive=lambda pid: pid == 4242), cfg, heavy=True, fixer_of="LAND31")
        self.assertFalse(ok)


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

    def test_kind_and_fixer_flags_reach_the_bounds(self):
        red = self.write("land.json", {"verdict": "RED"})
        cfg = self.write("cfg.json", {"land_verdict": red})
        code, out, _ = self.run_main(["check", "--heavy", "--config", cfg, "--fixer-of", "LAND31"])
        self.assertEqual(code, 0, out)
        code, out, _ = self.run_main(["check", "--heavy", "--config", cfg, "--kind", "join"])
        self.assertEqual(code, 1, out)

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
