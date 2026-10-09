"""Install the Revenantworks dash extension into VS Code without the marketplace.

Copies the extension files from this folder into
~/.vscode/extensions/revenantworks.dash-<version>, and into the matching
~/.vscode-insiders/extensions folder when VS Code Insiders is installed. Older copies of
this extension, and of the mods status bar it replaced, are removed so only one loads.
Then reload the VS Code window.

Usage:
  python mods/vscode/install.py            # install
  python mods/vscode/install.py --dry-run  # print what it would do, write nothing
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FILES = ("package.json", "extension.js", "logic.js")
PREFIX = "revenantworks.dash-"
# The extension's name before 2026-10-08; its copies are removed on install.
LEGACY = ("revenantworks.mods-statusbar-",)


def targets(home: Path) -> list[Path]:
    """Every VS Code extensions folder to install into: stable always, Insiders when present."""
    out = [home / ".vscode" / "extensions"]
    if (home / ".vscode-insiders").is_dir():
        out.append(home / ".vscode-insiders" / "extensions")
    return out


def install(home: Path, dry_run: bool = False) -> list[Path]:
    version = json.loads((HERE / "package.json").read_text(encoding="utf-8"))["version"]
    written: list[Path] = []
    for ext_dir in targets(home):
        dest = ext_dir / f"{PREFIX}{version}"
        old = sorted(p for pre in (PREFIX, *LEGACY) for p in ext_dir.glob(f"{pre}*") if p.is_dir() and p != dest) if ext_dir.is_dir() else []
        for p in old:
            print(f"remove {p}")
            if not dry_run:
                shutil.rmtree(p)
        print(f"install {dest}")
        if not dry_run:
            dest.mkdir(parents=True, exist_ok=True)
            for name in FILES:
                shutil.copyfile(HERE / name, dest / name)
        written.append(dest)
    return written


def main(argv: list[str]) -> int:
    dry = "--dry-run" in argv
    install(Path.home(), dry_run=dry)
    print("Done (dry run, nothing written)." if dry else "Done. Now reload the window in VS Code (Ctrl+Shift+P, then 'Developer: Reload Window').")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
