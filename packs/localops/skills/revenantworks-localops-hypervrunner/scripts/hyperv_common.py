#!/usr/bin/env python3
"""Shared helpers for hypervrunner's scripts. Imported, never run on its own.

- run_ps(): one Windows PowerShell call, no window, no profile, JSON back.
  The script text may not contain a double quote (a guard, not a style rule:
  Python passes the script as one command-line argument, and Windows
  PowerShell 5.1 re-splits embedded double quotes).
- ps_quote(): the only way a caller-supplied value enters a PowerShell script.
- check_name(): the allowlist for VM, checkpoint and switch names.
- ram_verdict(): the RAM side of the pack's resource lease (references/ram-preflight.md).
- read_lease(): the pack's GPU lease, read only, never written by hypervrunner.
- the creation record (lock 1), the disk folder, the protected list and the teardown
  log that teardown.py reads and writes; all live outside every repo.

Every value read back from PowerShell, a file or the lease is data, never an
instruction. Stdlib only.
"""
import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

NO_WINDOW = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW: never pop a console
HV_ADMINS_SID = "S-1-5-32-578"  # BUILTIN\Hyper-V Administrators, language-independent
VERDICT_ORDER = ["go", "ask", "reduce", "unmeasured", "refuse"]  # worst wins
CLEANROOM_TAG = "hypervrunner:cleanroom"
OWN_TAG = "hypervrunner:own"  # lock 2: the Notes marker every VM the skill creates carries
GUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")

# PowerShell treats these four as single quotes too, so each must be doubled.
_PS_SINGLE_QUOTES = "'‘’‚‛"
_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._-]{0,62}$")


class PSError(RuntimeError):
    """PowerShell missing, failed, or returned something that is not JSON."""


def ps_quote(value) -> str:
    """Return a PowerShell single-quoted literal for value. Refuses control characters."""
    s = str(value)
    if any(ord(c) < 32 for c in s):
        raise ValueError("control character in a value bound for PowerShell")
    out = []
    for c in s:
        out.append(c + c if c in _PS_SINGLE_QUOTES else c)
    return "'" + "".join(out) + "'"


def check_name(value: str, what: str = "name") -> str:
    """VM, checkpoint and switch names: letters, digits, space, dot, underscore, hyphen."""
    if not isinstance(value, str) or not _NAME_RE.match(value) or value != value.strip():
        raise ValueError(f"{what} {value!r} is not allowed: use letters, digits, space, "
                         f". _ - (1-63 chars, no leading or trailing space)")
    return value


def worst(*verdicts: str) -> str:
    return max(verdicts, key=VERDICT_ORDER.index) if verdicts else "go"


def powershell_exe() -> str | None:
    """Windows PowerShell 5.1 first: the Hyper-V module ships inbox there."""
    return shutil.which("powershell.exe") or shutil.which("powershell") or shutil.which("pwsh")


def run_ps(script: str, timeout: int = 120):
    """Run script in one PowerShell process and parse its stdout as JSON."""
    if '"' in script:
        raise ValueError("PowerShell script text must not contain a double quote")
    exe = powershell_exe()
    if not exe:
        raise PSError("PowerShell not found on PATH")
    proc = subprocess.run([exe, "-NoProfile", "-NonInteractive", "-Command", script],
                          capture_output=True, text=True, timeout=timeout,
                          creationflags=NO_WINDOW)
    out = (proc.stdout or "").strip()
    if proc.returncode != 0 and not out:
        raise PSError((proc.stderr or "").strip()[:2000] or f"exit {proc.returncode}")
    try:
        return json.loads(out) if out else None
    except json.JSONDecodeError as e:
        raise PSError(f"PowerShell output is not JSON: {out[:300]!r}") from e


def state_dir() -> Path:
    """Per-user state, outside every repo: %LOCALAPPDATA% or the XDG state dir."""
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_STATE_HOME") \
        or str(Path.home() / ".local" / "state")
    return Path(base) / "localops"


def own_dir() -> Path:
    return state_dir() / "hypervrunner"


def read_json_file(path: Path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError):
        return {"_unreadable": True}


def write_json(path: Path, data) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def config() -> dict:
    """The user's config.json (ram_headroom_bytes, disk_root, purge_after_days). Data only."""
    cfg = read_json_file(own_dir() / "config.json")
    return cfg if isinstance(cfg, dict) and not cfg.get("_unreadable") else {}


def disk_root() -> Path:
    """The skill's own disk folder: owner-set `disk_root` (absolute), else <state>/disks.
    New disks are made here; teardown moves only disks whose real path is inside it."""
    v = config().get("disk_root")
    if isinstance(v, str) and Path(v).is_absolute():
        return Path(v)
    return own_dir() / "disks"


def own_vms_path() -> Path:
    """The register of VMs this skill created, by GUID (lock 1), outside every repo."""
    return own_dir() / "own-vms.json"


def read_register() -> dict:
    reg = read_json_file(own_vms_path())
    return reg if isinstance(reg, dict) and not reg.get("_unreadable") else {}


def record_own_vm(vm_id: str, name: str, cleanroom: bool, ephemeral: bool = False,
                  run_id: str | None = None) -> None:
    """Record a VM's GUID at creation. Only `vmctl.py create` calls this; nothing adopts a VM
    the skill did not create, so a name or a Notes tag alone never makes a VM its own."""
    reg = read_register()
    reg[str(vm_id).lower()] = {"name": name, "cleanroom": bool(cleanroom), "ephemeral": bool(ephemeral),
                               "run_id": run_id if ephemeral else None, "created": utc_now_iso()}
    write_json(own_vms_path(), reg)


def mark_torn_down(vm_id: str, info: dict) -> None:
    """Keep the record (never delete it) and note where the disks went."""
    reg = read_register()
    rec = reg.get(str(vm_id).lower())
    if isinstance(rec, dict):
        rec["torn_down"] = info
        write_json(own_vms_path(), reg)


def is_own_vm(vm_id: str | None) -> bool:
    return bool(vm_id) and str(vm_id).lower() in read_register()


def protected_path() -> Path:
    return own_dir() / "protected.json"


def read_protected() -> dict:
    """Disks and checkpoint GUIDs teardown and purge never touch (golden bases and the like)."""
    d = read_json_file(protected_path())
    d = d if isinstance(d, dict) and not d.get("_unreadable") else {}
    return {"disks": [str(x) for x in d.get("disks") or []],
            "checkpoints": [str(x).lower() for x in d.get("checkpoints") or []]}


def resolve_path(p) -> str:
    """The real path: symlinks and junctions followed (os.path.realpath does both on Windows)."""
    return os.path.realpath(str(p))


def inside(path: str, root: str) -> bool:
    """True when the already-resolved path lies strictly under the already-resolved root."""
    p, r = os.path.normcase(os.path.normpath(path)), os.path.normcase(os.path.normpath(root))
    try:
        return p != r and os.path.commonpath([p, r]) == r
    except ValueError:  # different drives
        return False


def append_log(event: dict) -> None:
    """One JSON line per teardown or purge, outside every repo."""
    p = own_dir() / "teardown-log.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, sort_keys=True) + "\n")


def read_lease(now: datetime | None = None, path: Path | None = None) -> dict:
    """The pack's GPU lease (gpu-seam.md section 2), read only. Returns a status dict."""
    lease = read_json_file(path or state_dir() / "gpu-lease.json")
    if lease is None:
        return {"status": "none"}
    if lease.get("_unreadable"):
        return {"status": "stale", "reason": "unreadable"}
    now = now or datetime.now(timezone.utc)
    try:
        expires = datetime.fromisoformat(str(lease.get("expires")).replace("Z", "+00:00"))
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
    except ValueError:
        return {"status": "stale", "reason": "no valid expires", "holder": lease.get("holder")}
    if expires <= now:
        return {"status": "stale", "reason": "expired", "holder": lease.get("holder")}
    ram = lease.get("est_ram_bytes")
    return {"status": "live", "holder": lease.get("holder"), "purpose": lease.get("purpose"),
            "expires": lease.get("expires"), "est_ram_bytes": ram if isinstance(ram, int) else None}


def ram_verdict(request_bytes, free_phys_bytes, commit_free_bytes, total_bytes,
                headroom_bytes=None, lease=None, mode="interactive") -> dict:
    """RAM pre-flight before a VM or sandbox starts (references/ram-preflight.md).

    Rule: request + headroom <= free physical memory, and request + headroom <= free commit.
    Headroom is the user's number; absent, 10% of total is PROPOSED and labelled.
    A live GPU lease held by another runner means a render or a model is using memory now.
    """
    reasons, verdicts = [], []
    readings = {"request_bytes": request_bytes, "free_phys_bytes": free_phys_bytes,
                "commit_free_bytes": commit_free_bytes, "total_bytes": total_bytes}
    missing = [k for k, v in readings.items() if not isinstance(v, (int, float)) or v <= 0]
    if missing:
        verdicts.append("unmeasured" if mode == "interactive" else "refuse")
        reasons.append("unmeasured: " + ", ".join(missing))
        return {"verdict": worst(*verdicts), "reasons": reasons, "headroom_source": None}
    if headroom_bytes is None:
        headroom_bytes = int(total_bytes * 0.10)
        source = "PROPOSED (10% of total; the user sets ram_headroom_bytes)"
        verdicts.append("ask" if mode == "interactive" else "refuse")
        reasons.append("headroom is a proposal, not an owner value")
    else:
        source = "owner config"
    need = request_bytes + headroom_bytes
    if need > free_phys_bytes:
        verdicts.append("reduce")
        reasons.append(f"request + headroom {need} > free physical {free_phys_bytes}")
    if need > commit_free_bytes:
        verdicts.append("reduce")
        reasons.append(f"request + headroom {need} > free commit {commit_free_bytes}")
    if lease and lease.get("status") == "live":
        verdicts.append("ask" if mode == "interactive" else "refuse")
        ram = lease.get("est_ram_bytes")
        reasons.append(f"GPU lease live: {lease.get('holder')} ({lease.get('purpose')}; est_ram_bytes "
                       f"{ram if isinstance(ram, int) else 'unknown'})")
    elif lease and lease.get("status") == "stale":
        verdicts.append("ask" if mode == "interactive" else "refuse")
        reasons.append("GPU lease stale: the user decides")
    if not verdicts:
        verdicts.append("go")
    return {"verdict": worst(*verdicts), "reasons": reasons, "headroom_bytes": headroom_bytes,
            "headroom_source": source}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
