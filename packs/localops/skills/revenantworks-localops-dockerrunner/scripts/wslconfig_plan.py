#!/usr/bin/env python3
"""Write a complete proposed .wslconfig BESIDE the original, never over it.

Doctrine: references/wslconfig.md. The skill never edits .wslconfig in place. This script reads
the current file (or none), changes only the keys asked for, keeps every other line, comment and
the file's own line ending, re-parses its own output to prove the change (plan -> validate), and
writes `<file>.proposed`. It prints JSON with the diff and ONE PowerShell line the user runs to
back up the original, copy the proposal in, and restart WSL.

Usage:
  python scripts/wslconfig_plan.py [--memory-gb N] [--swap-gb N]
         [--auto-memory-reclaim gradual|dropCache|disabled] [--sparse-vhd true|false]
         [--source PATH] [--out PATH] [--total-ram-gb N] [--dry-run]
  python scripts/wslconfig_plan.py --selftest

With no --memory-gb, it proposes about a third of installed RAM (the user's default rule),
labelled PROPOSED. Stdlib only. Exit 0 on a written or dry-run plan, 2 on a refused one.
"""
import argparse
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

GIB = 1024 ** 3
KEYS = {  # key -> section, as Microsoft's .wslconfig reference places them
    "memory": "wsl2", "swap": "wsl2",
    "autoMemoryReclaim": "experimental", "sparseVhd": "experimental",
}


def total_ram() -> int | None:
    if os.name != "nt":
        return None
    try:
        import ctypes
        kb = ctypes.c_ulonglong(0)
        if ctypes.windll.kernel32.GetPhysicallyInstalledSystemMemory(ctypes.byref(kb)):
            return int(kb.value) * 1024
    except Exception:
        pass
    return None


def newline_of(raw: bytes) -> bytes:
    return b"\r\n" if b"\r\n" in raw else b"\n"


def plan(text: str, changes: dict[str, str], nl: str) -> str:
    """Apply key=value changes section-aware; keep every other line byte-for-byte."""
    lines = text.split(nl) if text else []
    trailing = bool(lines) and lines[-1] == ""
    if trailing:
        lines = lines[:-1]
    pending = dict(changes)
    section = None
    out: list[str] = []
    section_end: dict[str, int] = {}

    for ln in lines:
        s = ln.split("#", 1)[0].strip()
        m = re.match(r"^\[(.+)\]$", s)
        if m:
            section = m.group(1).strip().lower()
            out.append(ln)
            section_end[section] = len(out)
            continue
        if section and "=" in s:
            key = s.split("=", 1)[0].strip()
            hit = next((k for k in pending if k.lower() == key.lower() and KEYS[k] == section), None)
            if hit:
                out.append(f"{key}={pending.pop(hit)}")
                section_end[section] = len(out)
                continue
        out.append(ln)
        if section and s:
            section_end[section] = len(out)

    for sec in ("wsl2", "experimental"):
        adds = [f"{k}={v}" for k, v in pending.items() if KEYS[k] == sec]
        if not adds:
            continue
        if sec in section_end:
            at = section_end[sec]
            out[at:at] = adds
            for s2, pos in section_end.items():
                if pos >= at and s2 != sec:
                    section_end[s2] = pos + len(adds)
            section_end[sec] = at + len(adds)
        else:
            if out and out[-1].strip():
                out.append("")
            out.append(f"[{sec}]")
            out.extend(adds)
            section_end[sec] = len(out)
    return nl.join(out) + (nl if trailing or not text else "")


def parse(text: str) -> dict[str, dict[str, str]]:
    sections: dict[str, dict[str, str]] = {}
    cur = None
    for ln in text.splitlines():
        s = ln.split("#", 1)[0].strip()
        if not s:
            continue
        m = re.match(r"^\[(.+)\]$", s)
        if m:
            cur = m.group(1).strip().lower()
            sections.setdefault(cur, {})
        elif "=" in s and cur:
            k, v = s.split("=", 1)
            sections[cur][k.strip().lower()] = v.strip()
    return sections


def validate(before: str, after: str, changes: dict[str, str]) -> list[str]:
    """Errors, specific enough to act on. Empty list = the plan does exactly what was asked."""
    errs = []
    got = parse(after)
    for k, v in changes.items():
        have = got.get(KEYS[k], {}).get(k.lower())
        if have != v:
            errs.append(f"{KEYS[k]}.{k}: expected {v!r}, the proposal has {have!r}")
    old = parse(before)
    for sec, kv in old.items():
        for k, v in kv.items():
            if any(k == c.lower() and KEYS[c] == sec for c in changes):
                continue
            if got.get(sec, {}).get(k) != v:
                errs.append(f"untouched key {sec}.{k} changed: {v!r} -> {got.get(sec, {}).get(k)!r}")
    return errs


def build_changes(a, ram: int | None) -> tuple[dict[str, str], list[str], list[str]]:
    changes, notes, refusals = {}, [], []
    if a.memory_gb is not None:
        mem = a.memory_gb
        notes.append(f"memory {mem} GB: owner-given")
    elif ram:
        mem = max(1, int(ram / GIB / 3))
        notes.append(f"memory {mem} GB: PROPOSED, about a third of {ram / GIB:.0f} GiB installed RAM "
                     "(the user's default rule); confirm or pass --memory-gb")
    else:
        mem = None
        refusals.append("installed RAM unmeasured: pass --memory-gb or --total-ram-gb")
    if mem is not None:
        if mem < 1:
            refusals.append("memory below 1 GB: WSL would not start")
        elif ram and mem * GIB > ram:
            refusals.append(f"memory {mem} GB is above installed RAM ({ram / GIB:.0f} GiB)")
        else:
            changes["memory"] = f"{int(mem) if float(mem).is_integer() else mem}GB"
    if a.swap_gb is not None:
        changes["swap"] = f"{int(a.swap_gb) if float(a.swap_gb).is_integer() else a.swap_gb}GB"
    if a.auto_memory_reclaim:
        changes["autoMemoryReclaim"] = a.auto_memory_reclaim
    if a.sparse_vhd:
        changes["sparseVhd"] = a.sparse_vhd
    return changes, notes, refusals


def owner_command(src: Path, out: Path, exists: bool) -> str:
    stamp = date.today().strftime("%Y%m%d")
    parts = []
    if exists:
        parts.append(f'Copy-Item -LiteralPath "{src}" -Destination "{src}.bak-{stamp}" -Force')
    parts.append(f'Copy-Item -LiteralPath "{out}" -Destination "{src}" -Force')
    parts.append("wsl --shutdown")
    return "; ".join(parts)


def selftest() -> int:
    t = "[wsl2]\r\nswap=2GB # keep\r\nprocessors=8\r\n"
    after = plan(t, {"memory": "10GB"}, "\r\n")
    assert "memory=10GB" in after and "processors=8" in after and after.endswith("\r\n")
    assert validate(t, after, {"memory": "10GB"}) == []
    fresh = plan("", {"memory": "8GB", "sparseVhd": "true"}, "\n")
    assert parse(fresh) == {"wsl2": {"memory": "8GB"}, "experimental": {"sparsevhd": "true"}}
    print("selftest: ok (4 assertions)")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Write a proposed .wslconfig beside the original.")
    p.add_argument("--memory-gb", type=float)
    p.add_argument("--swap-gb", type=float)
    p.add_argument("--auto-memory-reclaim", choices=("gradual", "dropCache", "disabled"))
    p.add_argument("--sparse-vhd", choices=("true", "false"))
    p.add_argument("--source", help="the .wslconfig to read (default: the user profile's)")
    p.add_argument("--out", help="where to write the proposal (default: <source>.proposed)")
    p.add_argument("--total-ram-gb", type=float, help="override the RAM reading (tests, or no Windows)")
    p.add_argument("--dry-run", action="store_true", help="print the plan; write nothing")
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()
    if a.selftest:
        return selftest()

    src = Path(a.source) if a.source else Path(os.environ.get("USERPROFILE") or Path.home()) / ".wslconfig"
    out = Path(a.out) if a.out else src.with_name(src.name + ".proposed")
    exists = src.is_file()
    raw = src.read_bytes() if exists else b""
    nl = newline_of(raw) if raw else (b"\r\n" if os.name == "nt" else b"\n")
    before = raw.decode("utf-8-sig")
    ram = int(a.total_ram_gb * GIB) if a.total_ram_gb else total_ram()

    changes, notes, refusals = build_changes(a, ram)
    if not changes and not refusals:
        refusals.append("nothing to change: pass at least one key")
    if refusals:
        print(json.dumps({"status": "refused", "reasons": refusals, "notes": notes}, indent=2))
        return 2
    after = plan(before, changes, nl.decode())
    errs = validate(before, after, changes)
    if errs:  # the feedback loop: never write a proposal that fails its own read-back
        print(json.dumps({"status": "refused", "reasons": errs}, indent=2))
        return 2
    old = parse(before)
    diff = [{"key": f"{KEYS[k]}.{k}", "from": old.get(KEYS[k], {}).get(k.lower()), "to": v}
            for k, v in changes.items()]
    result = {"status": "dry-run" if a.dry_run else "written", "source": str(src), "source_exists": exists,
              "proposal": str(out), "diff": diff, "notes": notes,
              "owner_command": owner_command(src, out, exists),
              "warning": "wsl --shutdown stops every WSL distro and Docker Desktop's engine, so running "
                         "containers stop. Wait until `wsl --list --running` shows none, then start "
                         "Docker Desktop. The change applies only after that restart."}
    if not a.dry_run:
        out.write_bytes(after.encode("utf-8"))
        if out.read_bytes().decode("utf-8") != after:
            print(json.dumps({"status": "refused", "reasons": ["read-back of the written proposal differs"]}))
            return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
