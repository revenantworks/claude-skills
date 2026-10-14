"""Install the Revenantworks dash extension into VS Code without the marketplace.

Copies the extension files from this folder into
~/.vscode/extensions/revenantworks.dash-<version>, and into the matching
~/.vscode-insiders/extensions folder when VS Code Insiders is installed. Older copies of
this extension, and of the mods status bar it replaced, are removed so only one loads.

A removed extension must also leave VS Code's registry (extensions.json): a folder deleted
while its entry stays makes VS Code report an invalid extension. So the old status bar is
uninstalled through the VS Code command line (`code --uninstall-extension`) when it is on
PATH, and any entry still pointing at a removed folder is then dropped from extensions.json
(an atomic rewrite, only when something changed). Then reload the VS Code window.

Usage:
  python mods/vscode/install.py            # install
  python mods/vscode/install.py --dry-run  # print what it would do, write nothing
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
FILES = ("package.json", "extension.js", "logic.js")
PUBLISHER = "revenantworks"
NAME = "dash"
PREFIX = f"{PUBLISHER}.{NAME}-"
# The extension's id before 2026-10-08; it is uninstalled on install.
LEGACY_IDS = ("revenantworks.mods-statusbar",)
LEGACY = tuple(f"{i}-" for i in LEGACY_IDS)
# Each extensions folder and the command line that owns it.
CLI = {".vscode": "code", ".vscode-insiders": "code-insiders"}

Runner = Callable[[list[str]], int]


def targets(home: Path) -> list[Path]:
    """Every VS Code extensions folder to install into: stable always, Insiders when present."""
    out = [home / ".vscode" / "extensions"]
    if (home / ".vscode-insiders").is_dir():
        out.append(home / ".vscode-insiders" / "extensions")
    return out


def run_quiet(argv: list[str]) -> int:
    """Run a command with no window and no prompt; any failure is a non-zero code."""
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        return subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True, timeout=120, creationflags=flags).returncode
    except (OSError, subprocess.SubprocessError):
        return 1


def uninstall_legacy(ext_dir: Path, which: Callable[[str], str | None] = shutil.which, runner: Runner = run_quiet, dry_run: bool = False) -> list[str]:
    """Uninstall each legacy id present in ext_dir through VS Code's command line, when it is on PATH."""
    name = CLI.get(ext_dir.parent.name, "code")
    cli = which(name)
    done: list[str] = []
    for ext_id in LEGACY_IDS:
        if not any(p.is_dir() for p in ext_dir.glob(f"{ext_id}-*")):
            continue
        if cli is None:
            print(f"{name} is not on PATH: removing {ext_id} by hand")
            continue
        print(f"uninstall {ext_id} ({name} --uninstall-extension)")
        if dry_run or runner([cli, "--uninstall-extension", ext_id]) == 0:
            done.append(ext_id)
    return done


def _entry_dir(ext_dir: Path, entry: dict) -> Path | None:
    rel = entry.get("relativeLocation")
    if isinstance(rel, str) and rel:
        return ext_dir / rel
    loc = entry.get("location")
    if isinstance(loc, dict) and isinstance(loc.get("fsPath"), str):
        return Path(loc["fsPath"])
    if isinstance(loc, dict) and isinstance(loc.get("path"), str):
        p = loc["path"]
        return Path(p[1:] if len(p) > 2 and p[0] == "/" and p[2] == ":" else p)
    return None


def prune_registry(ext_dir: Path, dry_run: bool = False) -> list[str]:
    """Drop extensions.json entries for this extension or its legacy ids whose folder is gone.

    Every other entry is kept as it was. A file that is not a JSON list is left alone.
    """
    reg = ext_dir / "extensions.json"
    try:
        entries = json.loads(reg.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(entries, list):
        return []
    ours = {i.lower() for i in (*LEGACY_IDS, f"{PUBLISHER}.{NAME}")}
    keep: list = []
    dropped: list[str] = []
    for e in entries:
        ident = e.get("identifier", {}).get("id", "") if isinstance(e, dict) and isinstance(e.get("identifier"), dict) else ""
        where = _entry_dir(ext_dir, e) if isinstance(e, dict) else None
        if isinstance(ident, str) and ident.lower() in ours and (where is None or not where.is_dir()):
            dropped.append(f"{ident} {e.get('version', '')}".strip())
            continue
        keep.append(e)
    for d in dropped:
        print(f"unregister {d} from {reg}")
    if dropped and not dry_run:
        tmp = reg.with_name(reg.name + ".dash-tmp")
        tmp.write_text(json.dumps(keep, separators=(",", ":")), encoding="utf-8")
        os.replace(tmp, reg)
    return dropped


def _would_remove(ext_dir: Path, dest: Path) -> list[Path]:
    if not ext_dir.is_dir():
        return []
    return sorted(p for pre in (PREFIX, *LEGACY) for p in ext_dir.glob(f"{pre}*") if p.is_dir() and p != dest)


def install(home: Path, dry_run: bool = False, which: Callable[[str], str | None] = shutil.which, runner: Runner = run_quiet) -> list[Path]:
    version = json.loads((HERE / "package.json").read_text(encoding="utf-8"))["version"]
    written: list[Path] = []
    for ext_dir in targets(home):
        dest = ext_dir / f"{PREFIX}{version}"
        if ext_dir.is_dir():
            uninstall_legacy(ext_dir, which, runner, dry_run)
        old = _would_remove(ext_dir, dest)
        for p in old:
            print(f"remove {p}")
            if not dry_run:
                shutil.rmtree(p)
        print(f"install {dest}")
        if not dry_run:
            dest.mkdir(parents=True, exist_ok=True)
            for name in FILES:
                shutil.copyfile(HERE / name, dest / name)
        if ext_dir.is_dir() and not dry_run:
            prune_registry(ext_dir)
        elif ext_dir.is_dir():
            # A dry run removed nothing, so name the entries the real run would drop.
            gone = {p.name for p in old}
            for e in json.loads((ext_dir / "extensions.json").read_text(encoding="utf-8")) if (ext_dir / "extensions.json").is_file() else []:
                if isinstance(e, dict) and e.get("relativeLocation") in gone:
                    print(f"unregister {e.get('identifier', {}).get('id', '')} {e.get('version', '')}".strip())
        written.append(dest)
    return written


def main(argv: list[str]) -> int:
    dry = "--dry-run" in argv
    install(Path.home(), dry_run=dry)
    print("Done (dry run, nothing written)." if dry else "Done. Now reload the window in VS Code (Ctrl+Shift+P, then 'Developer: Reload Window').")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
