#!/usr/bin/env python3
"""Name-leak check: fail when a tracked file contains a banned term.

The banned list never lives in this repo and is never uploaded: it is the warden pack's
private names list on this machine, resolved in this order:
    1. --list PATH
    2. the WARDEN_NAMES_FILE environment variable
    3. ~/.warden/wordlist.txt (Windows: %USERPROFILE%/.warden/wordlist.txt), when it exists
It runs locally before a push (RUNBOOK.md); CI does not run it.

List format, one term per line:
    term            whole-word match (default; see --mode)
    sub:term        substring match for this term only
    word:term       whole-word match for this term only
    Name==>repl     shieldwarden's rewrite form; the replacement is ignored here
    # comment       ignored, as are blank lines
Matching is case-insensitive. A multi-word term matches across any run of spaces.
"Whole word" means no letter directly before or after: digits, `_`, `-` and
punctuation all count as edges, so a name inside `name_notes` or `name2026` hits.

Output never echoes a banned term or the line that holds it: each hit prints
`path:line: list entry #<n> [mode]`, where n is the line's place among the list's terms.

Exit codes: 0 clean, 1 hit(s), 2 refused (a named list that is missing, or a list
inside a git work tree), 3 NOT-RUN (no list anywhere, or a list with no terms). A
NOT-RUN prints the setup command and never reads as a pass.
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ENV_VAR = "WARDEN_NAMES_FILE"
DEFAULT = Path("~") / ".warden" / "wordlist.txt"
SETUP = "python packs/warden/shared/scripts/warden_private.py setup names"
NOT_RUN = 3
LETTER = r"[^\W\d_]"


def mask(index):
    return f"list entry #{index}"


def load_terms(path, default_mode):
    terms = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        mode = default_mode
        for prefix, m in (("sub:", "substring"), ("word:", "word")):
            if line.lower().startswith(prefix):
                line, mode = line[len(prefix):].strip(), m
                break
        line = line.split("==>", 1)[0].strip()
        if line:
            terms.append((line, mode))
    return terms


def compile_term(term, mode):
    body = r"\s+".join(re.escape(part) for part in term.split())
    if mode == "word":
        body = rf"(?<!{LETTER}){body}(?!{LETTER})"
    return re.compile(body, re.IGNORECASE)


def git_work_tree(path):
    """The work tree holding `path`, found by a `.git` entry (folder or worktree file) above it."""
    p = path.resolve()
    for d in [p] + list(p.parents):
        if (d / ".git").exists():
            return d
    return None


def resolve_list(flag):
    """--list > WARDEN_NAMES_FILE > ~/.warden/wordlist.txt. Returns (path or None, source)."""
    if flag:
        return Path(flag).expanduser(), "--list"
    if os.environ.get(ENV_VAR, "").strip():
        return Path(os.environ[ENV_VAR].strip()).expanduser(), ENV_VAR
    default = DEFAULT.expanduser()
    return (default, "default") if default.is_file() else (None, None)


def tracked_files(root):
    out = subprocess.run(["git", "-C", str(root), "ls-files", "-z"],
                         capture_output=True, check=True).stdout
    return [p for p in out.decode("utf-8", errors="replace").split("\0") if p]


def scan(root, patterns):
    hits = []
    for rel in tracked_files(root):
        path = root / rel
        try:
            data = path.read_bytes()
        except OSError:
            continue  # tracked but deleted in the working tree
        if b"\0" in data[:8192]:
            continue  # binary
        text = data.decode("utf-8", errors="replace")
        for n, line in enumerate(text.splitlines(), 1):
            for index, (_term, mode, rx) in enumerate(patterns, 1):
                if rx.search(line):
                    hits.append(f"{rel}:{n}: {mask(index)} [{mode}]")
    return hits


def main(argv=None):
    ap = argparse.ArgumentParser(description="Fail on banned names in tracked files.")
    ap.add_argument("--list", help=f"names list outside every repo (default: ${ENV_VAR}, else ~/.warden/wordlist.txt)")
    ap.add_argument("--root", default=".", help="repo to scan (default: current directory)")
    ap.add_argument("--mode", choices=("word", "substring"), default="word",
                    help="default match mode for unprefixed terms (default: word)")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    lst, source = resolve_list(args.list)
    if lst is None:
        print(f"name-leak: NOT-RUN: no list (no --list, no {ENV_VAR}, no ~/.warden/wordlist.txt); "
              f"run setup: {SETUP}")
        return NOT_RUN
    if not lst.is_file():
        print(f"name-leak: ERROR: the list named by {source} is not found", file=sys.stderr)
        return 2
    lst = lst.resolve()
    if lst == root or root in lst.parents or git_work_tree(lst.parent) is not None:
        print("name-leak: ERROR: the list file sits inside a git work tree; keep it outside every repo",
              file=sys.stderr)
        return 2

    terms = load_terms(lst, args.mode)
    if not terms:
        print("name-leak: NOT-RUN: the list has no terms; add them in your own editor")
        return NOT_RUN

    patterns = [(t, m, compile_term(t, m)) for t, m in terms]
    hits = scan(root, patterns)
    if hits:
        print("\n".join(hits))
        print(f"name-leak: FAIL: {len(hits)} hit(s) for {len(terms)} term(s)", file=sys.stderr)
        return 1
    print(f"name-leak: OK: {len(terms)} term(s), no hits in tracked files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
