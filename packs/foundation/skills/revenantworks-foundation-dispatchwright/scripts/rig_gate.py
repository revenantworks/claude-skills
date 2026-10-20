#!/usr/bin/env python3
"""rig_gate.py -- the rig gate: may one more heavy unit launch on this machine now?

    python rig_gate.py check [--heavy | --light] [--config PATH] [--json]
    python rig_gate.py signals [--config PATH]

pacewright's rig-aware turbo (modes.md, Turbo; owner 2026-10-20, observation 0470) lifts the spend
throttle and never a machine limit. The ledger guard (`dispatch_ledger_guard.py`) runs this check
before every heavy launch in turbo and refuses the launch on exit 1. A heavy launch is a unit that
will run a local suite, build, render, measure or engine run; a light launch passes here at once
(only the guard's writer, all-units and top-tier bounds apply to it).

Exit codes: 0 the launch may go, 1 a bound refuses it (each refusal names the bound and its
number), 2 the config file is unreadable (the guard then refuses: it fails closed).

Signals, each read through a small adapter. A signal whose source is not configured, absent or
unreadable is reported "not measured" and never refuses a launch on its own, so a repo without a
run's own tooling passes with only the process and CPU readings. No adapter raises.

  busy engines   Every headless engine or suite process on the machine, whoever started it, from
                 one process listing (pid, parent, command line). A process under another matching
                 process shares its slot. `engine_pattern` (a regex over the command line; default
                 unittest, pytest, ci_local, warden_suites and `godot ... --headless`). Plus 2 while
                 a self-hosted CI runner job runs (`runner_pattern`, default `Runner.Worker`), plus
                 `busy` from `extra_busy_file` ({"busy": n, "why": ...}: container shards no host
                 process shows). Bound: busy <= B - 2, B = `rig_budget` (default physical cores + 2,
                 taken as logical threads / 2 + 2: 10 on 8 cores / 16 threads; at least 4).
  cpu            Machine busy percent over `cpu_window_s` (default 3 s). Bound: under `cpu_max_pct`
                 (default 85).
  slot registry  `slot_registry`: a folder of `<pid>.json` records ({pid, state, class, worktree})
                 a slot runner writes. Live records (pid alive) are counted by state; reported only.
  check queue    `queue_dir`, the queue runner's folder: `<unit>.json` requests ({unit, worktree,
                 head, priority, queued, [expected_s]}), `runner.json` ({running: [...]}), `PAUSED`,
                 `HOSTED` ({on, why, pid}: a land's branch CI run in flight on the rig's own runner;
                 older than `hosted_max_age_h`, default 8, is a leftover). Expected wait =
                 (each request's expected_s, else `default_check_s` 900, plus half that for each
                 running check) / `check_lanes` (default 3). Bound: wait <= `queue_horizon_min`
                 (default 45), and no heavy launch while HOSTED is on.
  land           `land_flag` ({pid, started}: a land walk runs while the pid lives and the flag is
                 under `land_max_age_h`, default 4); `land_verdict` and `nightly_status`
                 ({verdict: GREEN | RED | ...}). Bound: no walk running, neither verdict RED.
  unlanded       `wip` = {repo, branch_glob (default claude/*), base (default origin/main)}: the
  branches       local branches matching the glob that are not merged into base. Bound: under
                 `wip_limit` (default 6); at the limit the next launch is a join or a land.

The config is `--config`, else RIG_GATE_CONFIG, else ~/.dispatch/rig-gate.json; an absent file is
no config. A config is JSON; every key is optional; paths may start with `~`.

Stdlib only, no window, no network. Part of revenantworks-foundation-dispatchwright.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Optional

WINDOWS = os.name == "nt"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
ENGINE_PATTERN = r"unittest|pytest|ci_local|ci-local|warden_suites|godot.*--headless"
DEFAULTS = {
    "rig_budget": None, "cpu_max_pct": 85, "cpu_window_s": 3.0, "queue_horizon_min": 45,
    "wip_limit": 6, "check_lanes": 3, "default_check_s": 900, "engine_pattern": ENGINE_PATTERN,
    "runner_pattern": r"Runner\.Worker", "land_max_age_h": 4, "hosted_max_age_h": 8,
    "slot_registry": None, "queue_dir": None, "land_flag": None, "land_verdict": None,
    "nightly_status": None, "extra_busy_file": None, "wip": None,
}
NOT_REQUESTS = {"runner.json"}


def default_budget(logical: Optional[int]) -> int:
    """Physical cores + 2, physical taken as logical / 2 (stdlib cannot read cores): 16 -> 10."""
    return max(4, int(logical or 4) // 2 + 2)


def config(d: dict) -> dict:
    cfg = dict(DEFAULTS)
    cfg.update({k: v for k, v in (d or {}).items() if v is not None})
    if not cfg.get("rig_budget"):
        cfg["rig_budget"] = default_budget(os.cpu_count())
    return cfg


def _p(value) -> Optional[Path]:
    return Path(os.path.expanduser(str(value))) if value else None


def _read_json(path: Path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _signal(name, measured, value=None, detail=""):
    return {"name": name, "measured": measured, "value": value, "detail": detail}


# ---- live readers (each replaceable in tests) --------------------------------------------------

Proc = tuple  # (pid, parent pid, command line)


def list_processes() -> list:
    """Every live process with its parent and command line; the one live listing call."""
    if WINDOWS:
        cmd = ["powershell", "-NoProfile", "-NonInteractive", "-Command",
               "[Console]::OutputEncoding = [Text.Encoding]::UTF8; "
               "Get-CimInstance Win32_Process | ForEach-Object { "
               "\"$($_.ProcessId)`t$($_.ParentProcessId)`t$($_.CommandLine)\" }"]
        out = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                             timeout=20, creationflags=NO_WINDOW, stdin=subprocess.DEVNULL).stdout or ""
        rows = [ln.split("\t", 2) for ln in out.splitlines()]
        return [(int(a), int(b), c.strip()) for a, b, c in (r for r in rows if len(r) == 3)
                if a.strip().isdigit() and b.strip().isdigit()]
    out = subprocess.run(["ps", "-eo", "pid=,ppid=,args="], capture_output=True, text=True, timeout=20).stdout
    procs = []
    for raw in out.splitlines():
        parts = raw.split(None, 2)
        if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
            procs.append((int(parts[0]), int(parts[1]), parts[2] if len(parts) == 3 else ""))
    return procs


def _cpu_times():
    try:
        if WINDOWS:
            import ctypes

            class FT(ctypes.Structure):
                _fields_ = [("lo", ctypes.c_uint32), ("hi", ctypes.c_uint32)]

            idle, kern, user = FT(), FT(), FT()
            if not ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kern), ctypes.byref(user)):
                return None
            f = lambda t: (t.hi << 32) | t.lo  # noqa: E731
            return f(idle), f(kern) + f(user)  # kernel time includes idle
        with open("/proc/stat", encoding="ascii") as fh:
            vals = [int(v) for v in fh.readline().split()[1:]]
        return vals[3] + (vals[4] if len(vals) > 4 else 0), sum(vals)
    except (OSError, ValueError, AttributeError, IndexError):
        return None


def cpu_sampler(window: float) -> Callable[[], Optional[float]]:
    def sample() -> Optional[float]:
        a = _cpu_times()
        if a is None:
            return None
        time.sleep(window)
        b = _cpu_times()
        if b is None or b[1] - a[1] <= 0:
            return None
        return max(0.0, min(100.0, 100.0 * (1 - (b[0] - a[0]) / (b[1] - a[1]))))
    return sample


def pid_alive(pid) -> bool:
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    if WINDOWS:
        import ctypes
        k = ctypes.windll.kernel32
        h = k.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return False
        try:
            code = ctypes.c_ulong()
            return bool(k.GetExitCodeProcess(h, ctypes.byref(code))) and code.value == 259  # STILL_ACTIVE
        finally:
            k.CloseHandle(h)
    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True
    except OSError:
        return False


def git_run(args: list, cwd) -> tuple:
    try:
        p = subprocess.run(["git", "-C", str(cwd)] + list(args), capture_output=True, text=True,
                           timeout=30, creationflags=NO_WINDOW, stdin=subprocess.DEVNULL)
        return p.returncode, p.stdout
    except (OSError, subprocess.SubprocessError) as e:
        return 1, str(e)


# ---- adapters -----------------------------------------------------------------------------------

def read_engines(cfg, listing) -> dict:
    try:
        procs = list(listing())
    except Exception as e:  # noqa: BLE001 -- an adapter never raises
        return _signal("busy engines", False, detail=f"no process listing ({type(e).__name__}: {e})")
    try:
        engine = re.compile(cfg["engine_pattern"], re.I)
        runner = re.compile(cfg["runner_pattern"], re.I) if cfg.get("runner_pattern") else None
    except re.error as e:
        return _signal("busy engines", False, detail=f"bad pattern ({e})")
    me = os.path.basename(__file__)
    match = lambda line: bool(line) and me not in line and bool(engine.search(line))  # noqa: E731
    by_pid = {pid: (ppid, line) for pid, ppid, line in procs}

    def under_an_engine(pid, ppid):
        seen = {pid}
        while ppid in by_pid and ppid not in seen:
            seen.add(ppid)
            ppid, line = by_pid[ppid]
            if match(line):
                return True
        return False

    busy = sum(1 for pid, ppid, line in procs if match(line) and not under_an_engine(pid, ppid))
    parts = [f"{busy} engine or suite processes"]
    if runner and any(runner.search(line or "") for _, _, line in procs):
        busy += 2
        parts.append("+2 for a self-hosted runner job")
    extra = _p(cfg.get("extra_busy_file"))
    if extra:
        try:
            d = _read_json(extra)
            n = int(d.get("busy", 0)) if isinstance(d, dict) else 0
            if n > 0:
                busy += n
                parts.append(f"+{n} from {extra.name} ({d.get('why', 'no reason given')})")
        except FileNotFoundError:
            pass
        except Exception as e:  # noqa: BLE001
            parts.append(f"{extra.name} unreadable ({type(e).__name__})")
    return _signal("busy engines", True, busy, "; ".join(parts))


def read_cpu(cfg, cpu) -> dict:
    try:
        pct = cpu()
    except Exception as e:  # noqa: BLE001
        return _signal("cpu", False, detail=f"no reading ({type(e).__name__})")
    if pct is None:
        return _signal("cpu", False, detail="no reading on this platform")
    return _signal("cpu", True, round(float(pct), 1), f"over {cfg['cpu_window_s']} s")


def read_registry(cfg, alive) -> dict:
    folder = _p(cfg.get("slot_registry"))
    if not folder:
        return _signal("slot registry", False, detail="slot_registry not configured")
    if not folder.is_dir():
        return _signal("slot registry", False, detail=f"{folder.name} is not a folder")
    states: dict = {}
    for f in sorted(folder.glob("*.json")):
        try:
            r = _read_json(f)
        except Exception:  # noqa: BLE001
            continue
        if isinstance(r, dict) and alive(r.get("pid")):
            key = f"{r.get('state', '?')}" + (f"/{r['class']}" if r.get("class") else "")
            states[key] = states.get(key, 0) + 1
    return _signal("slot registry", True, states, ", ".join(f"{k} {v}" for k, v in sorted(states.items())) or "no live run")


def read_queue(cfg, now) -> dict:
    folder = _p(cfg.get("queue_dir"))
    if not folder:
        return _signal("check queue", False, detail="queue_dir not configured")
    if not folder.is_dir():
        return _signal("check queue", False, detail=f"{folder.name} is not a folder")
    default = float(cfg["default_check_s"])
    pending, seconds, skipped = 0, 0.0, []
    for f in sorted(folder.glob("*.json")):
        if f.name.lower() in NOT_REQUESTS:
            continue
        try:
            r = _read_json(f)
        except Exception:  # noqa: BLE001
            skipped.append(f.name)
            continue
        if not isinstance(r, dict) or not r.get("unit"):
            skipped.append(f.name)
            continue
        pending += 1
        try:
            seconds += float(r.get("expected_s") or default)
        except (TypeError, ValueError):
            seconds += default
    running = 0
    try:
        state = _read_json(folder / "runner.json")
        running = len(state.get("running") or []) if isinstance(state, dict) else 0
    except Exception:  # noqa: BLE001
        running = 0
    seconds += running * default / 2
    lanes = max(1, int(cfg["check_lanes"]))
    wait_min = seconds / lanes / 60
    hosted = False
    hosted_path = folder / "HOSTED"
    if hosted_path.is_file():
        try:
            h = _read_json(hosted_path)
            young = now - hosted_path.stat().st_mtime <= float(cfg["hosted_max_age_h"]) * 3600
            hosted = bool(isinstance(h, dict) and h.get("on")) and young
        except Exception:  # noqa: BLE001
            hosted = False
    value = {"pending": pending, "running": running, "wait_min": round(wait_min, 1),
             "paused": (folder / "PAUSED").exists(), "hosted": hosted}
    detail = f"{pending} queued, {running} running, {lanes} lanes"
    if skipped:
        detail += f"; skipped unreadable {', '.join(skipped)}"
    return _signal("check queue", True, value, detail)


def read_land(cfg, alive, now) -> dict:
    flag, verdict, nightly = (_p(cfg.get(k)) for k in ("land_flag", "land_verdict", "nightly_status"))
    if not (flag or verdict or nightly):
        return _signal("land", False, detail="land_flag, land_verdict and nightly_status not configured")
    value = {"walk": False, "verdict": None, "main": None}
    notes = []
    if flag:
        try:
            d = _read_json(flag)
            fresh = now - float(d.get("started") or 0) <= float(cfg["land_max_age_h"]) * 3600
            value["walk"] = bool(isinstance(d, dict) and fresh and alive(d.get("pid")))
        except FileNotFoundError:
            pass
        except Exception as e:  # noqa: BLE001
            notes.append(f"land flag unreadable ({type(e).__name__})")
    for key, path in (("verdict", verdict), ("main", nightly)):
        if not path:
            continue
        try:
            d = _read_json(path)
            v = d.get("verdict") if isinstance(d, dict) else None
            value[key] = str(v).upper() if v else None
        except FileNotFoundError:
            pass
        except Exception as e:  # noqa: BLE001
            notes.append(f"{path.name} unreadable ({type(e).__name__})")
    return _signal("land", True, value, "; ".join(notes))


def read_wip(cfg, git) -> dict:
    w = cfg.get("wip")
    if not isinstance(w, dict) or not w.get("repo"):
        return _signal("unlanded branches", False, detail="wip.repo not configured")
    glob, base = w.get("branch_glob") or "claude/*", w.get("base") or "origin/main"
    try:
        code, out = git(["branch", "--list", glob, "--no-merged", base], _p(w["repo"]))
    except Exception as e:  # noqa: BLE001
        return _signal("unlanded branches", False, detail=f"git failed ({type(e).__name__})")
    if code != 0:
        return _signal("unlanded branches", False, detail=f"git exit {code}")
    names = [ln.strip().lstrip("*+ ").strip() for ln in out.splitlines() if ln.strip()]
    return _signal("unlanded branches", True, len(names), f"{glob} not in {base}")


def read_signals(cfg, listing=None, cpu=None, alive=None, git=None, now=None) -> dict:
    listing = listing or list_processes
    cpu = cpu or cpu_sampler(float(cfg["cpu_window_s"]))
    alive = alive or pid_alive
    git = git or git_run
    now = time.time() if now is None else now
    return {"engines": read_engines(cfg, listing), "cpu": read_cpu(cfg, cpu),
            "registry": read_registry(cfg, alive), "queue": read_queue(cfg, now),
            "land": read_land(cfg, alive, now), "wip": read_wip(cfg, git)}


# ---- the bounds ---------------------------------------------------------------------------------

def evaluate(sig: dict, cfg: dict, heavy: bool = True) -> tuple:
    """(ok, lines). Each line names one signal: its reading, `not measured (...)` or `REFUSED ...`."""
    if not heavy:
        return True, ["light launch: the rig gate does not bound it (the ledger guard's writer, "
                      "all-units and top-tier bounds still apply)"]
    lines, refused = [], []

    def note(s, text):
        lines.append(f"{s['name']}: {text}" + (f" ({s['detail']})" if s.get("detail") else ""))

    def refuse(text):
        refused.append(text)
        lines.append(f"REFUSED {text}")

    for key in ("engines", "cpu", "registry", "queue", "land", "wip"):
        s = sig[key]
        if not s["measured"]:
            note(s, "not measured")
            continue
        v = s["value"]
        if key == "engines":
            top = int(cfg["rig_budget"]) - 2
            if v > top:
                refuse(f"busy engines {v} over {top} (rig budget {cfg['rig_budget']} - 2; {s['detail']})")
            else:
                note(s, f"{v} of {top} ok")
        elif key == "cpu":
            if v >= float(cfg["cpu_max_pct"]):
                refuse(f"cpu {v:g}% at or over {cfg['cpu_max_pct']}%")
            else:
                note(s, f"{v:g}% ok")
        elif key == "registry":
            note(s, "read")
        elif key == "queue":
            if v["hosted"]:
                refuse("a branch CI run in flight on the rig's runner (queue HOSTED): no heavy writer "
                       "whose check would join the queue")
            if v["wait_min"] > float(cfg["queue_horizon_min"]):
                refuse(f"queue wait {v['wait_min']:.0f} min over {cfg['queue_horizon_min']} ({s['detail']})")
            elif not v["hosted"]:
                note(s, f"wait {v['wait_min']:.0f} min ok" + (", PAUSED" if v["paused"] else ""))
        elif key == "land":
            hit = False
            if v["walk"]:
                refuse("a land walk running (land flag): no writer launch until it ends")
                hit = True
            if v["verdict"] == "RED":
                refuse("land verdict RED: only its fixer and light lanes launch")
                hit = True
            if v["main"] == "RED":
                refuse("main RED (nightly status): only its fixer and light lanes launch")
                hit = True
            if not hit:
                note(s, f"no walk, land {v['verdict'] or 'none'}, main {v['main'] or 'none'}")
        elif key == "wip":
            limit = int(cfg["wip_limit"])
            if v >= limit:
                refuse(f"unlanded branches {v} at the limit {limit}: the next launch is a join or a land, "
                       "never a build")
            else:
                note(s, f"{v} under {limit} ok")
    return not refused, lines


# ---- command line -------------------------------------------------------------------------------

def config_path(arg: Optional[str]) -> Path:
    if arg:
        return Path(os.path.expanduser(arg))
    env = os.environ.get("RIG_GATE_CONFIG")
    return Path(os.path.expanduser(env)) if env else Path.home() / ".dispatch" / "rig-gate.json"


def main(argv=None, listing=None, cpu=None, alive=None, git=None) -> int:
    p = argparse.ArgumentParser(prog="rig_gate.py", description="May one more heavy unit launch now?")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("check", "signals"):
        s = sub.add_parser(name)
        s.add_argument("--config")
        s.add_argument("--json", action="store_true")
        if name == "check":
            g = s.add_mutually_exclusive_group()
            g.add_argument("--heavy", action="store_true")
            g.add_argument("--light", action="store_true")
    a = p.parse_args(argv)
    path = config_path(a.config)
    raw = {}
    if path.exists():
        try:
            raw = _read_json(path)
            if not isinstance(raw, dict):
                raise ValueError("not a JSON object")
        except Exception as e:  # noqa: BLE001
            print(f"rig_gate: the config {path.name} is unreadable ({type(e).__name__}: {e}); fix it or "
                  "remove it (an absent config is no config)", file=sys.stderr)
            return 2
    cfg = config(raw)
    sig = read_signals(cfg, listing, cpu, alive, git)
    if a.cmd == "signals":
        print(json.dumps(sig, indent=2) if a.json else "\n".join(
            f"{s['name']}: {s['value'] if s['measured'] else 'not measured'}"
            + (f" ({s['detail']})" if s["detail"] else "") for s in sig.values()))
        return 0
    ok, lines = evaluate(sig, cfg, heavy=not a.light)
    if a.json:
        print(json.dumps({"ok": ok, "heavy": not a.light, "lines": lines, "signals": sig}))
    else:
        print("\n".join(lines + [f"rig_gate: {'PASS' if ok else 'REFUSED'}"]))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
