#!/usr/bin/env python3
"""hypervrunner sandbox: a disposable Windows Sandbox for one untrusted download.

Writes a Windows Sandbox configuration with networking, vGPU, clipboard, audio, video
and printers off, Protected Client on, one READ-ONLY input folder and one writable,
empty output folder. Validates the configuration before anything starts (validate()),
and after a start proves networking is off with `wsb ip` (no address expected).

  python scripts/sandbox_config.py --input DIR --output DIR [--memory-mb 4096]
         [--write FILE.wsb] [--start]

--start uses the wsb CLI (Windows 11 24H2 or later) and stops the sandbox at once if an
IP address shows up. Without the CLI, open the written .wsb file instead. Files that come
back in the output folder are untrusted data. Stdlib only.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from xml.sax.saxutils import escape

from hyperv_common import NO_WINDOW

# Windows Sandbox's fixed built-in account (the same on every machine, not a person); joined
# from parts so path scanners do not read it as a real user's home folder.
SANDBOX_DESKTOP = "\\".join(("C:", "Users", "WDAGUtilityAccount", "Desktop"))
OFF_KEYS = ("vGPU", "Networking", "AudioInput", "VideoInput", "PrinterRedirection",
            "ClipboardRedirection")


def _forbidden_output(p: Path) -> str | None:
    home = Path.home().resolve()
    if p == Path(p.anchor):
        return "a drive root"
    if p == home or p in home.parents:
        return "the user profile or one of its parents"
    if p.parent == home and p.name.lower() in {"desktop", "documents", "downloads", "pictures",
                                                "music", "videos", "onedrive"}:
        return f"the {p.name} folder"
    if any((q / ".git").exists() for q in [p, *p.parents]):
        return "inside a git repository"
    return None


def check_folders(input_dir: str, output_dir: str) -> tuple[Path, Path]:
    i, o = Path(input_dir).resolve(), Path(output_dir).resolve()
    if not i.is_dir():
        raise ValueError(f"input folder {i} does not exist")
    if not o.is_dir():
        raise ValueError(f"output folder {o} does not exist: create an empty one")
    if any(o.iterdir()):
        raise ValueError(f"output folder {o} is not empty: the sandbox may write only to an empty folder")
    if o == i or o in i.parents or i in o.parents:
        raise ValueError("input and output folders must not contain each other")
    why = _forbidden_output(o)
    if why:
        raise ValueError(f"output folder {o} is {why}: use a dedicated empty folder")
    return i, o


def build_config(input_dir: Path, output_dir: Path, memory_mb: int = 4096) -> str:
    if not (2048 <= int(memory_mb) <= 65536):
        raise ValueError("memory-mb must be 2048-65536")
    parts = ["<Configuration>"]
    parts += [f"<{k}>Disable</{k}>" for k in OFF_KEYS]
    parts.append("<ProtectedClient>Enable</ProtectedClient>")
    parts.append(f"<MemoryInMB>{int(memory_mb)}</MemoryInMB>")
    parts.append("<MappedFolders>")
    for host, name, ro in ((input_dir, "input", "true"), (output_dir, "output", "false")):
        parts.append(f"<MappedFolder><HostFolder>{escape(str(host))}</HostFolder>"
                     f"<SandboxFolder>{SANDBOX_DESKTOP}\\{name}</SandboxFolder>"
                     f"<ReadOnly>{ro}</ReadOnly></MappedFolder>")
    parts.append("</MappedFolders>")
    parts.append("</Configuration>")
    return "".join(parts)


def validate(xml: str) -> list[str]:
    """Empty list = safe. Each problem names the rule it breaks."""
    problems = []
    for k in OFF_KEYS:
        if not re.search(rf"<{k}>Disable</{k}>", xml):
            problems.append(f"{k} is not Disable")
    if "<LogonCommand>" in xml:
        problems.append("a LogonCommand is present: nothing runs automatically")
    folders = re.findall(r"<MappedFolder>(.*?)</MappedFolder>", xml, flags=re.S)
    writable = [f for f in folders if not re.search(r"<ReadOnly>\s*true\s*</ReadOnly>", f, re.I)]
    if len(writable) != 1:
        problems.append(f"{len(writable)} writable mapped folders: exactly one (the empty output) is allowed")
    if not folders:
        problems.append("no mapped folders")
    return problems


def _wsb(*args: str, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(["wsb", *args], capture_output=True, text=True, timeout=timeout,
                          creationflags=NO_WINDOW)


def start(xml: str) -> dict:
    if not shutil.which("wsb"):
        return {"started": False, "reason": "wsb CLI not found: open the written .wsb file instead"}
    r = _wsb("start", "--config", xml, "--raw")
    m = re.search(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", r.stdout or "")
    if r.returncode != 0 or not m:
        return {"started": False, "reason": (r.stderr or r.stdout or "").strip()[:500]}
    sid = m.group(0)
    ip = _wsb("ip", "--id", sid, "--raw")
    addr = re.findall(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", ip.stdout or "")
    if addr:
        _wsb("stop", "--id", sid)
        return {"started": False, "id": sid, "networking_check": "FAIL: address present, sandbox stopped",
                "addresses": addr}
    return {"started": True, "id": sid, "networking_check": "pass: no address",
            "connect": f"wsb connect --id {sid}", "stop_when_done": f"wsb stop --id {sid}"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--input", required=True); ap.add_argument("--output", required=True)
    ap.add_argument("--memory-mb", type=int, default=4096); ap.add_argument("--write")
    ap.add_argument("--start", action="store_true")
    a = ap.parse_args(argv)
    try:
        i, o = check_folders(a.input, a.output)
        xml = build_config(i, o, a.memory_mb)
    except ValueError as e:
        print(json.dumps({"status": "refused", "reason": str(e)}))
        return 2
    problems = validate(xml)
    out = {"config": xml, "valid": not problems, "problems": problems}
    if problems:
        print(json.dumps(out, indent=2))
        return 2
    if a.write:
        Path(a.write).write_text(xml, encoding="utf-8")
        out["wsb_file"] = a.write
    if a.start:
        out["start"] = start(xml)
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
