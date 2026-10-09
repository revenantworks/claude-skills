#!/usr/bin/env python3
"""warden_private.py: the warden pack's private files, kept on this machine only (stdlib only).

Nothing user-specific ships in a skill package. A user's private lists live in one per-user
folder outside every repo, the same on Windows, macOS and Linux:

    ~/.warden/                      (Windows: %USERPROFILE%\\.warden\\)
        wordlist.txt                names list: shieldwarden's owner-name rule, a repo's name-leak check
        aliases.txt                 identity values: shieldwarden's banned values (class:label = value)

Every script resolves a file in one order, and the first hit wins:
    1. the explicit flag (--names-file, --values, --list)
    2. one environment variable per file (WARDEN_NAMES_FILE, WARDEN_IDENTITY_VALUES_FILE)
    3. the default path above, when it exists
    4. none: the caller reports NOT-RUN with the setup command, never a pass that reads as clean
A file inside a git work tree is refused, whichever way it was named.

This module never prints an entry. Output names the file (home shortened to ~), its source and
an entry count.

Commands
  where [KIND]              status of each private file: source, state, entry count
  setup KIND [--path P]     create the folder and a template holding comment lines only;
                            never overwrites. With --path, prints the one command that sets
                            the environment variable for that location.
  adopt KIND SOURCE         move an existing file (an old in-repo values file) to the default
                            path; refuses when the default already exists. Prints no contents.
KIND: names | identity-values

Exit codes: 0 done · 3 NOT-RUN (no file, refused, or bad input) · 4 crashed (type only).
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

FOLDER_NAME = ".warden"

TEMPLATES = {
    "names": (
        "# warden names list: one entry per line. Lines starting with # are ignored.\n"
        "# Read by shieldwarden (the user-name rule) and by a repo's name-leak check.\n"
        "# Keep this file outside every git repo. Fill it in your own editor; never paste\n"
        "# an entry into a chat.\n"
        "#\n"
        "# Forms:\n"
        "#   Name                   whole-word match; a rewrite replaces it with \"the user\"\n"
        "#   Name==>replacement     a rewrite uses this replacement instead\n"
        "#   sub:term               name-leak only: match the term inside longer words too\n"
    ),
    "identity-values": (
        "# shieldwarden identity values file: one `class:label = value` per line. Lines starting\n"
        "# with # are ignored. Every key must also be listed in the policy's values_keys.\n"
        "# Keep this file outside every git repo. Fill it in your own editor; never paste\n"
        "# a value into a chat.\n"
        "#\n"
        "# Form:\n"
        "#   real-name:owner = <the value>\n"
    ),
}
KINDS = {
    "names": ("wordlist.txt", "WARDEN_NAMES_FILE"),
    "identity-values": ("aliases.txt", "WARDEN_IDENTITY_VALUES_FILE"),
}


class Resolved:
    """Where a private file came from. `path` is None when nothing was found."""

    def __init__(self, kind: str, path: Path | None, source: str | None, problem: str | None):
        self.kind, self.path, self.source, self.problem = kind, path, source, problem

    @property
    def ok(self) -> bool:
        return self.path is not None and self.problem is None


def default_folder() -> Path:
    return Path.home() / FOLDER_NAME


def default_path(kind: str) -> Path:
    return default_folder() / KINDS[kind][0]


def env_var(kind: str) -> str:
    return KINDS[kind][1]


def git_work_tree(path: Path) -> Path | None:
    """The work tree holding `path`, found by a `.git` entry (folder or worktree file) above it."""
    p = path.resolve()
    for d in [p] + list(p.parents):
        if (d / ".git").exists():
            return d
    return None


def setup_command(kind: str) -> str:
    return f"python scripts/warden_private.py setup {kind}"


def resolve(kind: str, flag: str | None = None) -> Resolved:
    """Flag > environment variable > default path if it exists > none (with the setup command)."""
    var = env_var(kind)
    if flag:
        named, source = Path(flag).expanduser(), "flag"
    elif os.environ.get(var, "").strip():
        named, source = Path(os.environ[var].strip()).expanduser(), "env"
    elif default_path(kind).is_file():
        named, source = default_path(kind), "default"
    else:
        return Resolved(kind, None, None, f"no {kind} file; run setup: {setup_command(kind)}")
    if not named.is_file():
        return Resolved(kind, named, source, f"the {kind} file named by the {source} is not found")
    if git_work_tree(named) is not None:
        return Resolved(kind, named, source,
                        f"the {kind} file sits inside a git work tree; keep it outside every repo "
                        f"(default {short(default_path(kind))})")
    return Resolved(kind, named, source, None)


def short(path: Path) -> str:
    """The path with the home folder shown as ~, so a user name never reaches the output."""
    s, home = str(path), str(Path.home())
    if home and len(home) > 3 and s.lower().startswith(home.lower()):
        return "~" + s[len(home):]
    return s


def entry_count(path: Path) -> int:
    n = 0
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            n += 1
    return n


def env_command(kind: str, path: Path) -> str:
    """One command that sets the variable for the user; a path under home is written via the home variable."""
    var, s = env_var(kind), short(path)
    if os.name == "nt":
        val = "$env:USERPROFILE" + s[1:] if s.startswith("~") else s
        return f"[Environment]::SetEnvironmentVariable('{var}', \"{val}\", 'User')"
    val = "$HOME" + s[1:] if s.startswith("~") else s
    return f"echo 'export {var}=\"{val}\"' >> ~/.profile"


# ---------------------------------------------------------------- commands

def cmd_where(kinds: list[str]) -> int:
    worst = 0
    for kind in kinds:
        r = resolve(kind)
        if r.ok:
            print(f"{kind}: {short(r.path)} ({r.source}), {entry_count(r.path)} entr(y/ies)")
        else:
            print(f"{kind}: NOT-RUN - {r.problem}")
            worst = 3
    return worst


def cmd_setup(kind: str, where: str | None) -> int:
    target = Path(where).expanduser() if where else default_path(kind)
    target = target if target.is_absolute() else Path.cwd() / target
    parent = target.parent
    if git_work_tree(parent) is not None:
        print(f"setup: NOT-RUN - {short(target)} sits inside a git work tree; choose a folder outside every repo")
        return 3
    if target.exists():
        print(f"setup: {short(target)} already exists; left unchanged ({entry_count(target)} entr(y/ies))")
    else:
        parent.mkdir(parents=True, exist_ok=True)
        target.write_text(TEMPLATES[kind], encoding="utf-8")
        print(f"setup: wrote {short(target)} (comment lines only). Open it in your editor and add your entries.")
    if where:
        print(f"setup: point the scripts at it with one command, then open a new terminal:\n  {env_command(kind, target)}")
    return 0


def cmd_adopt(kind: str, source: str) -> int:
    src = Path(source).expanduser()
    dst = default_path(kind)
    if not src.is_file():
        print("adopt: NOT-RUN - source file not found")
        return 3
    if dst.exists():
        print(f"adopt: NOT-RUN - {short(dst)} already exists; merge by hand in your editor, then delete the old file")
        return 3
    if git_work_tree(dst.parent) is not None:
        print(f"adopt: NOT-RUN - {short(dst)} sits inside a git work tree")
        return 3
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    print(f"adopt: moved to {short(dst)} ({entry_count(dst)} entr(y/ies)). "
          "Remove its .gitignore line and any values_file field from the policy.")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="warden_private.py", description=__doc__.split("\n", 1)[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("where")
    w.add_argument("kind", nargs="?", choices=sorted(KINDS))
    s = sub.add_parser("setup")
    s.add_argument("kind", choices=sorted(KINDS))
    s.add_argument("--path", help="another location, outside every repo")
    a = sub.add_parser("adopt")
    a.add_argument("kind", choices=sorted(KINDS))
    a.add_argument("source")
    try:
        args = ap.parse_args(argv)
    except SystemExit as e:
        return 3 if e.code not in (0, None) else 0
    if args.cmd == "where":
        return cmd_where([args.kind] if args.kind else sorted(KINDS))
    if args.cmd == "setup":
        return cmd_setup(args.kind, args.path)
    return cmd_adopt(args.kind, args.source)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # never the message: it may carry a path or a value
        print(f"warden_private: CRASHED ({type(e).__name__})")
        sys.exit(4)
