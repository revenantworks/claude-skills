#!/usr/bin/env python3
"""suite_slot: run one test suite under a machine-wide suite cap, at low priority.

    python scripts/suite_slot.py [--cap N] [--cwd DIR] -- <command> [args...]
    python scripts/suite_slot.py report [--log FILE]

Optional helper for dispatchwright's suite cap (owner ruling 2026-10-16, observation 0446):
one cap of suite processes on the whole machine, across every session and thread, and every
background suite at below-normal priority with no window. It admits a suite when fewer than 2
suites run (nothing starves), or when fewer than the hard cap run AND the machine's CPU over a
3 s sample is under the CPU target; then it starts the command at below-normal priority
(Windows) or nice 10 (elsewhere), with no new window, relays its output and returns its exit
code. With no CPU reading, the hard cap alone decides.

The hard cap: --cap if given, else `~/.dispatch/suite-cap.json` {"cap": N, "until": ISO-8601
UTC, "cpu_target": P} while unexpired, else 4. A missing, expired or malformed file, or a cap
under 1, means 4. The CPU target is that file's "cpu_target" (1-100), else 75 (owner
2026-10-16: "maybe just like 75% of CPU"). Both are re-read on every poll, so a change reaches
runs already waiting.

A suite process is one whose command line runs unittest, pytest, a ci_local runner,
warden_suites, or a headless Godot. A suite process holds one slot, and so does its whole tree:
a suite process with a suite process above it (a wrapper such as ci_stamp over ci_local, or
ci_local over unittest, even through a plain shell) shares that ancestor's slot. Separate suites
each count, so a plain runner that fans out N headless Godots uses N slots. Counting live
processes needs no lock file and cannot leak a slot when a run dies. The count is best effort:
two runners that check in the same instant can both start.

Each run appends one row to `~/.dispatch/suite-perf.jsonl`: start (UTC), repo folder name,
command head (paths cut to their last part), cap, suites running at start, CPU at start and
the CPU target, other runs queued, logical CPUs, wait and run seconds, exit code, tests ran
(from `Ran N tests` in the relayed output), the machine's CPU percent over the run (average and
peak, sampled every 5 s), and through one windowless typeperf process (Windows only; null
elsewhere) disk busy, queue, read and write MB/s, memory committed and pages/s, processor
queue (each average and peak) and available memory (minimum). No path or later argument is
logged. `report` summarises that log per cap and CPU target (runs, median wait_s, run_s,
cpu_avg, disk_busy_avg, mem_avail_mb_min and seconds per test) so both can be dialled in.

Stdlib only. Exit code: the command's, or 2 on a usage error (report: 0, or 2 on no log).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import statistics
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Callable, Iterable, Optional, Tuple, Union

SUITE = re.compile(r"unittest|pytest|ci_local|ci-local|warden_suites|godot.*--headless", re.I)
SELF = "suite_slot.py"
WINDOWS = os.name == "nt"
POLL_SECONDS = 15
DEFAULT_CAP = 4
DEFAULT_CPU_TARGET = 75
MIN_ADMIT = 2
CPU_WINDOW = 3.0
DISPATCH = Path.home() / ".dispatch"
CAP_FILE = DISPATCH / "suite-cap.json"
PERF_LOG = DISPATCH / "suite-perf.jsonl"


def parse_args(argv: list[str]) -> argparse.Namespace:
    """--cap and --cwd, then the command after `--` (or every token when there is no `--`).

    `cap` is the explicit --cap or the default (for display); `cap_override` is the explicit
    one only, None when the cap file or the default decides."""
    ap = argparse.ArgumentParser(prog="suite_slot.py",
                                 description="Run a suite under a machine-wide suite cap.")
    ap.add_argument("--cap", type=int, default=None,
                    help=f"suite processes allowed at once (default: the cap file, else {DEFAULT_CAP})")
    ap.add_argument("--cwd", default=None, help="folder to run the command in")
    if "--" in argv:
        i = argv.index("--")
        a = ap.parse_args(argv[:i])
        cmd = argv[i + 1:]
    else:
        ap.add_argument("cmd", nargs=argparse.REMAINDER)
        a = ap.parse_args(argv)
        cmd = a.cmd
    if not cmd:
        ap.error("no command (put it after --)")
    if a.cap is not None and a.cap < 1:
        ap.error("--cap must be 1 or more")
    a.cmd = cmd
    a.cap_override = a.cap
    a.cap = DEFAULT_CAP if a.cap is None else a.cap
    return a


def current_cap(override: Optional[int] = None, path: Path = CAP_FILE,
                now: Optional[dt.datetime] = None) -> int:
    """--cap, else the cap file's cap while unexpired, else DEFAULT_CAP."""
    if override:
        return override
    now = now or dt.datetime.now(dt.timezone.utc)
    try:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        until = dt.datetime.fromisoformat(str(d["until"]).replace("Z", "+00:00"))
        if until.tzinfo is None:
            until = until.replace(tzinfo=dt.timezone.utc)
        cap = d["cap"]
        if until > now and isinstance(cap, int) and not isinstance(cap, bool) and cap >= 1:
            return cap
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        pass
    return DEFAULT_CAP


def cpu_target(path: Path = CAP_FILE) -> int:
    """CPU percent under which another suite may start: the cap file's "cpu_target", else 75.

    Read whether or not the file's cap has expired; outside 1-100 or malformed means 75."""
    try:
        t = json.loads(Path(path).read_text(encoding="utf-8")).get("cpu_target", DEFAULT_CPU_TARGET)
        if isinstance(t, (int, float)) and not isinstance(t, bool) and 1 <= t <= 100:
            return int(t)
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return DEFAULT_CPU_TARGET


def admit(n: int, cap: int, cpu: Optional[float], target: int) -> bool:
    """Start a suite? Always below MIN_ADMIT running (nothing starves); else under the hard cap
    while the machine's CPU is under the target (no CPU reading: the cap alone decides)."""
    return n < MIN_ADMIT or (n < cap and (cpu is None or cpu < target))


def is_suite(cmdline: str) -> bool:
    """True for a suite process's command line; never for this runner's own."""
    return bool(cmdline) and SELF not in cmdline and bool(SUITE.search(cmdline))


def count_suites(cmdlines: Iterable[str]) -> int:
    return sum(1 for line in cmdlines if is_suite(line))


Proc = Tuple[Optional[int], Optional[int], str]  # (pid, parent pid, command line)


def count_slots(procs: Iterable[Union[Proc, str]]) -> int:
    """Suite slots in use: suite processes with no suite process among their ancestors.

    A bare string is a command line with no known parent, so it counts on its own."""
    rows = [(None, None, p) if isinstance(p, str) else p for p in procs]
    by_pid = {pid: (ppid, line) for pid, ppid, line in rows if pid is not None}

    def under_a_suite(pid: Optional[int], ppid: Optional[int]) -> bool:
        seen = {pid}  # a parent loop back to the process itself ends the walk
        while ppid is not None and ppid in by_pid and ppid not in seen:
            seen.add(ppid)
            ppid, line = by_pid[ppid]
            if is_suite(line):
                return True
        return False

    return sum(1 for pid, ppid, line in rows if is_suite(line) and not under_a_suite(pid, ppid))


def parse_listing(text: str) -> list[Proc]:
    """`pid<TAB>ppid<TAB>command line` lines; a malformed line is skipped."""
    procs: list[Proc] = []
    for raw in text.splitlines():
        parts = raw.split("\t", 2)
        if len(parts) == 3 and parts[0].strip().isdigit() and parts[1].strip().isdigit():
            procs.append((int(parts[0]), int(parts[1]), parts[2].strip()))
    return procs


def list_processes() -> list[Proc]:
    """Every live process with its parent and command line (the only live listing call).

    Every process, not just python and godot, so a plain shell between a wrapper and its
    suite child does not break the parent chain."""
    if WINDOWS:
        cmd = ["powershell", "-NoProfile", "-NonInteractive", "-Command",
               "Get-CimInstance Win32_Process | ForEach-Object { "
               "\"$($_.ProcessId)`t$($_.ParentProcessId)`t$($_.CommandLine)\" }"]
        kw = {"creationflags": subprocess.CREATE_NO_WINDOW}
        out = subprocess.run(cmd, capture_output=True, text=True, **kw).stdout
        return parse_listing(out)
    out = subprocess.run(["ps", "-eo", "pid=,ppid=,args="], capture_output=True, text=True).stdout
    procs: list[Proc] = []
    for raw in out.splitlines():
        parts = raw.split(None, 2)
        if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
            procs.append((int(parts[0]), int(parts[1]), parts[2] if len(parts) == 3 else ""))
    return procs


def running_suites(listing: Callable[[], list] = list_processes) -> int:
    return count_slots(listing())


# ---- CPU sampling -------------------------------------------------------------------------

def cpu_times() -> Optional[Tuple[int, int]]:
    """(idle, total) CPU time counters for the machine, or None where none can be read."""
    try:
        if WINDOWS:
            import ctypes

            class FT(ctypes.Structure):
                _fields_ = [("lo", ctypes.c_uint32), ("hi", ctypes.c_uint32)]

            idle, kern, user = FT(), FT(), FT()
            if not ctypes.windll.kernel32.GetSystemTimes(
                    ctypes.byref(idle), ctypes.byref(kern), ctypes.byref(user)):
                return None
            f = lambda t: (t.hi << 32) | t.lo  # noqa: E731
            return f(idle), f(kern) + f(user)  # kernel time includes idle
        with open("/proc/stat", encoding="ascii") as fh:
            vals = [int(v) for v in fh.readline().split()[1:]]
        return vals[3] + (vals[4] if len(vals) > 4 else 0), sum(vals)
    except (OSError, ValueError, AttributeError, IndexError):
        return None


def busy_percent(a: Tuple[int, int], b: Tuple[int, int]) -> Optional[float]:
    """CPU busy percent between two (idle, total) readings; None when no time passed."""
    d_idle, d_total = b[0] - a[0], b[1] - a[1]
    if d_total <= 0:
        return None
    return max(0.0, min(100.0, 100.0 * (1 - d_idle / d_total)))


def cpu_now(window: float = CPU_WINDOW, read: Callable = cpu_times,
            sleep: Callable[[float], None] = time.sleep) -> Optional[float]:
    """The machine's CPU busy percent over `window` seconds, or None with no reading."""
    a = read()
    if a is None:
        return None
    sleep(window)
    b = read()
    return None if b is None else busy_percent(a, b)


class CpuSampler(threading.Thread):
    def __init__(self, every: float = 5.0, read: Callable = cpu_times):
        super().__init__(daemon=True)
        self.every, self.read, self.samples, self.stop = every, read, [], threading.Event()

    def run(self) -> None:
        prev = self.read()
        while prev is not None and not self.stop.wait(self.every):
            cur = self.read()
            if cur is None:
                return
            pct = busy_percent(prev, cur)
            if pct is not None:
                self.samples.append(pct)
            prev = cur


COUNTERS = {  # name in the perf row -> Windows counter (typeperf, one process, every 5 s)
    "disk_idle": r"\PhysicalDisk(_Total)\% Idle Time",
    "disk_queue": r"\PhysicalDisk(_Total)\Avg. Disk Queue Length",
    "disk_read_mbs": r"\PhysicalDisk(_Total)\Disk Read Bytes/sec",
    "disk_write_mbs": r"\PhysicalDisk(_Total)\Disk Write Bytes/sec",
    "mem_avail_mb": r"\Memory\Available MBytes",
    "mem_commit_pct": r"\Memory\% Committed Bytes In Use",
    "mem_pages_s": r"\Memory\Pages/sec",
    "cpu_queue": r"\System\Processor Queue Length",
}
RIG_KEYS = ("disk_busy_avg", "disk_busy_peak", "disk_queue_avg", "disk_queue_peak",
            "disk_read_mbs_avg", "disk_read_mbs_peak", "disk_write_mbs_avg", "disk_write_mbs_peak",
            "mem_commit_pct_avg", "mem_commit_pct_peak", "mem_pages_s_avg", "mem_pages_s_peak",
            "cpu_queue_avg", "cpu_queue_peak", "mem_avail_mb_min")


def parse_typeperf(line: str, names: list[str]) -> Optional[dict]:
    """One typeperf CSV data line -> {name: float}; the header, a blank line, a status line
    or a row with a blank or non-numeric cell -> None."""
    cells = [c.strip('"') for c in line.strip().split('","')]
    if len(cells) != len(names) + 1:
        return None
    out = {}
    for name, cell in zip(names, cells[1:]):
        try:
            out[name] = float(cell)
        except ValueError:
            return None
    return out


def summarise_rig(rows: list[dict]) -> dict:
    """Counter rows -> avg and peak per counter (disk busy = 100 - idle, bytes as MB/s),
    available memory as its minimum, and the sample count; None where nothing was read."""
    def col(k: str, f: Callable[[float], float] = lambda v: v) -> list[float]:
        return [f(r[k]) for r in rows if k in r]

    out: dict = {}
    for key, vals in (
            ("disk_busy", col("disk_idle", lambda v: max(0.0, min(100.0, 100.0 - v)))),
            ("disk_queue", col("disk_queue")),
            ("disk_read_mbs", col("disk_read_mbs", lambda v: v / 1048576)),
            ("disk_write_mbs", col("disk_write_mbs", lambda v: v / 1048576)),
            ("mem_commit_pct", col("mem_commit_pct")),
            ("mem_pages_s", col("mem_pages_s")),
            ("cpu_queue", col("cpu_queue"))):
        out[f"{key}_avg"] = round(sum(vals) / len(vals), 1) if vals else None
        out[f"{key}_peak"] = round(max(vals), 1) if vals else None
    avail = col("mem_avail_mb")
    out["mem_avail_mb_min"] = round(min(avail)) if avail else None
    out["samples"] = len(rows)
    return out


class RigSampler(threading.Thread):
    """Disk, memory and scheduler counters every 5 s through one typeperf process with no
    window. Windows only: elsewhere, or with typeperf absent, it reads nothing and logs null."""

    def __init__(self, every: int = 5):
        super().__init__(daemon=True)
        self.names, self.rows = list(COUNTERS), []
        self.p = None
        if WINDOWS:
            try:
                self.p = subprocess.Popen(
                    ["typeperf", *COUNTERS.values(), "-si", str(every)],
                    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                    text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            except OSError:
                self.p = None

    def run(self) -> None:
        if not self.p:
            return
        for line in self.p.stdout:
            r = parse_typeperf(line, self.names)
            if r:
                self.rows.append(r)

    def close(self) -> None:
        if self.p:
            try:
                self.p.kill()
            except OSError:
                pass

    def summary(self) -> dict:
        return summarise_rig(list(self.rows))


def waiting_runs() -> Optional[int]:
    """Other suite_slot runs alive on the machine (this one excluded), or None unread."""
    try:
        n = sum(1 for _, _, line in list_processes()
                if SELF in line and "python" in line.lower())
    except OSError:
        return None
    return max(0, n - 1)


RAN = re.compile(rb"Ran (\d+) tests?\b")


class TestCounter:
    """Sums `Ran N tests` lines in relayed output; a line split across chunks still counts."""

    def __init__(self) -> None:
        self.total, self.carry = 0, b""

    def feed(self, chunk: bytes) -> None:
        data = self.carry + chunk
        lines = data.split(b"\n")
        self.carry = lines.pop()[-4096:]
        self.total += sum(int(m) for line in lines for m in RAN.findall(line))

    def done(self) -> int:
        self.feed(b"\n")
        return self.total


def secs_per_test(row: dict) -> Optional[float]:
    """Seconds per test for one perf row, or None without a run time and a test count."""
    run_s, ran = row.get("run_s"), row.get("tests_ran")
    if isinstance(run_s, (int, float)) and isinstance(ran, int) and ran > 0:
        return run_s / ran
    return None


# ---- the perf log -------------------------------------------------------------------------

def _leaf(token: str) -> str:
    return re.split(r"[\\/]", token.rstrip("\\/"))[-1] if re.search(r"[\\/]", token) else token


def perf_row(cmd: list[str], cwd: Optional[str], cap: int, suites_at_start: int, t_ask: float,
             t_start: float, t_end: float, rc: int, samples: list[float],
             cpu_at_start: Optional[float] = None, target: int = DEFAULT_CPU_TARGET,
             rig: Optional[dict] = None, queued_at_start: Optional[int] = None,
             tests_ran: Optional[int] = None) -> dict:
    """One suite-perf.jsonl row. Paths are cut to their last part; nothing past cmd[:3].

    `rig` is summarise_rig's output; without it every rig counter is null."""
    head = " ".join(_leaf(c) for c in cmd[:3])[:80]
    rig = rig if rig is not None else summarise_rig([])
    return {"start": dt.datetime.fromtimestamp(t_start, dt.timezone.utc).isoformat(timespec="seconds"),
            "repo": _leaf(cwd) if cwd else Path.cwd().name, "cmd": head, "cap": cap,
            "suites_at_start": suites_at_start,
            "cpu_at_start": None if cpu_at_start is None else round(cpu_at_start, 1),
            "cpu_target": target, "wait_s": round(t_start - t_ask),
            "run_s": round(t_end - t_start), "exit": rc,
            "cpu_avg": round(sum(samples) / len(samples), 1) if samples else None,
            "cpu_peak": round(max(samples), 1) if samples else None,
            "logical_cpus": os.cpu_count(), "queued_at_start": queued_at_start,
            "tests_ran": tests_ran or None,
            **{k: rig.get(k) for k in RIG_KEYS}, "samples": rig.get("samples", 0)}


def append_row(row: dict, path: Path = PERF_LOG) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")
    except OSError:
        pass  # the log is best effort; it never fails a run


def summarise(lines: Iterable[str]) -> list[dict]:
    """Per (cap, cpu_target): runs and the medians of wait_s, run_s, cpu_avg, disk_busy_avg,
    mem_avail_mb_min and seconds per test (None when no row has a reading).

    A row from before the CPU target has cpu_target None. A malformed line or one with no
    integer cap is skipped."""
    by_cap: dict[tuple, list[dict]] = {}
    for line in lines:
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict) and isinstance(row.get("cap"), int):
            t = row.get("cpu_target")
            key = (row["cap"], t if isinstance(t, int) and not isinstance(t, bool) else None)
            by_cap.setdefault(key, []).append(row)

    def num(v) -> bool:
        return isinstance(v, (int, float)) and not isinstance(v, bool)

    def med(vals: list) -> Optional[float]:
        vals = [v for v in vals if num(v)]
        return round(statistics.median(vals), 2) if vals else None

    order = lambda kv: (kv[0][0], -1 if kv[0][1] is None else kv[0][1])  # noqa: E731
    return [{"cap": cap, "cpu_target": target, "runs": len(rows),
             **{k: med([r.get(k) for r in rows]) for k in REPORT_KEYS[:-1]},
             "s_per_test": med([secs_per_test(r) for r in rows])}
            for (cap, target), rows in sorted(by_cap.items(), key=order)]


REPORT_KEYS = ("wait_s", "run_s", "cpu_avg", "disk_busy_avg", "mem_avail_mb_min", "s_per_test")


def format_report(summary: list[dict]) -> str:
    if not summary:
        return "suite_slot report: no runs logged"
    show = lambda v: "-" if v is None else f"{v:g}"  # noqa: E731
    out = ["cap | cpu_target | runs | " + " | ".join(f"median {k}" for k in REPORT_KEYS)]
    out += [" | ".join([str(s["cap"]), show(s["cpu_target"]), str(s["runs"])]
                       + [show(s[k]) for k in REPORT_KEYS]) for s in summary]
    return "\n".join(out)


def report(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="suite_slot.py report",
                                 description="Summarise the suite-perf log per cap.")
    ap.add_argument("--log", default=str(PERF_LOG), help="the perf log (default ~/.dispatch/suite-perf.jsonl)")
    a = ap.parse_args(argv)
    try:
        lines = Path(a.log).read_text(encoding="utf-8").splitlines()
    except OSError:
        print("suite_slot report: no perf log yet", file=sys.stderr)
        return 2
    print(format_report(summarise(lines)))
    return 0


# ---- run ----------------------------------------------------------------------------------

def child_options() -> dict:
    if WINDOWS:
        # CREATE_NO_WINDOW gives the child its own hidden console, so its output is relayed.
        return {"creationflags": subprocess.BELOW_NORMAL_PRIORITY_CLASS | subprocess.CREATE_NO_WINDOW}
    return {"preexec_fn": lambda: os.nice(10)}


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["report"]:
        return report(argv[1:])
    a = parse_args(argv)
    t_ask = time.time()
    waited = 0
    while True:
        n, cap, target = running_suites(), current_cap(a.cap_override), cpu_target()
        cpu = cpu_now()
        if admit(n, cap, cpu, target):
            break
        if waited % 60 == 0:
            shown = "?" if cpu is None else f"{cpu:.0f}"
            print(f"suite_slot: {n} suites, cap {cap}, cpu {shown}% / target {target}%; waiting",
                  flush=True)
        time.sleep(POLL_SECONDS)
        waited += POLL_SECONDS
    t_start = time.time()
    sampler, rig = CpuSampler(), RigSampler()
    sampler.start()
    rig.start()
    queued = waiting_runs()
    counter = TestCounter()
    p = subprocess.Popen(a.cmd, cwd=a.cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, **child_options())
    for chunk in iter(lambda: p.stdout.read1(65536), b""):
        sys.stdout.buffer.write(chunk)
        sys.stdout.flush()
        counter.feed(chunk)
    rc = p.wait()
    t_end = time.time()
    sampler.stop.set()
    rig.close()
    rig.join(timeout=2)
    append_row(perf_row(a.cmd, a.cwd, cap, n, t_ask, t_start, t_end, rc, sampler.samples,
                        cpu, target, rig.summary(), queued, counter.done()))
    return rc


if __name__ == "__main__":
    sys.exit(main())
