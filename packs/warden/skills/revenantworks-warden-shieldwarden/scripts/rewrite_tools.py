#!/usr/bin/env python3
"""rewrite_tools.py: the steps around a history rewrite that a hand-written script skipped.

  python rewrite_tools.py repoint --map <commit-map> <dir> [<dir> ...] [--apply]
  python rewrite_tools.py restore --ref <pre-rewrite ref> --repo <dir> <path> [<path> ...] [--apply]
  python rewrite_tools.py push-size --repo <dir> [--range <upstream>..<branch>] [--limit-mb 100]

repoint (observation 0336): finds every old commit id from filter-repo's commit map (full 40
characters, and the 7-character short form) in the text files under each folder, run records and
briefs included, and with --apply rewrites them to the new ids. Bytes are rewritten in place, so
each file keeps its own line endings; the count replaced must equal the count found, and a second
search must find none, or the run exits 1. A short id two old commits share, and an old id whose
commit the rewrite dropped (new id all zeros), are listed and never guessed.

restore (observation 0360): a rewrite that removes paths from history also removes them from the
working tree when it checks out the new HEAD (filter-branch does). Paths that must stay on disk
(logs, local data) are listed from the pre-rewrite ref; with --apply each missing file is written
back from that ref, and the run counts expected against present. A mismatch exits 1.

push-size (observation 0360): before a batch push, the largest new blob and the total size of new
blobs in the range, so a host's per-file limit (100 MB on GitHub) is caught before the push.

Prints paths, counts and ids only; never file contents. Stdlib only.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
HEX = re.compile(rb"(?<![0-9a-fA-F])[0-9a-f]{7,40}(?![0-9a-fA-F])")
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv"}


def git(repo: str, *args: str, binary: bool = False):
    p = subprocess.run(["git", "-C", repo, *args], capture_output=True, creationflags=NO_WINDOW)
    if p.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {p.stderr.decode(errors='replace').strip()}")
    return p.stdout if binary else p.stdout.decode(errors="replace")


# ---------------------------------------------------------------- repoint

def load_map(path: str) -> tuple[dict[bytes, bytes], dict[bytes, bytes], list[str], list[str]]:
    """full map, short map, ambiguous short ids, dropped old ids."""
    full: dict[bytes, bytes] = {}
    dropped: list[str] = []
    with open(path, "rb") as fh:
        for line in fh:
            parts = line.split()
            if len(parts) != 2 or not re.fullmatch(rb"[0-9a-f]{40}", parts[0]):
                continue  # the "old new" header
            old, new = parts
            if set(new) == {ord("0")}:
                dropped.append(old.decode())
            elif old != new:
                full[old] = new
    short: dict[bytes, bytes] = {}
    seen: dict[bytes, int] = {}
    for old in list(full) + [d.encode() for d in dropped]:
        seen[old[:7]] = seen.get(old[:7], 0) + 1
    ambiguous = sorted(k.decode() for k, n in seen.items() if n > 1)
    for old, new in full.items():
        if seen[old[:7]] == 1:
            short[old[:7]] = new[:7]
    return full, short, ambiguous, dropped


def text_files(root: str):
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            path = os.path.join(base, name)
            try:
                with open(path, "rb") as fh:
                    data = fh.read()
            except OSError:
                continue
            if b"\0" in data[:4096]:
                continue  # binary
            yield path, data


def find_hits(data: bytes, full: dict, short: dict) -> list[tuple[bytes, bytes]]:
    hits = []
    for m in HEX.finditer(data):
        tok = m.group(0)
        if len(tok) == 40 and tok in full:
            hits.append((tok, full[tok]))
        elif len(tok) == 7 and tok in short:
            hits.append((tok, short[tok]))
    return hits


def cmd_repoint(a) -> int:
    full, short, ambiguous, dropped = load_map(a.map)
    print(f"map: {len(full)} rewritten, {len(dropped)} dropped, {len(ambiguous)} ambiguous short ids")
    plan = []
    for root in a.dirs:
        for path, data in text_files(root):
            hits = find_hits(data, full, short)
            drops = [d for d in dropped if d.encode() in data or d[:7].encode() in data]
            amb = [s for s in ambiguous if re.search(rb"(?<![0-9a-f])" + s.encode() + rb"(?![0-9a-f])", data)]
            if hits or drops or amb:
                plan.append((path, data, hits, drops, amb))
    total = sum(len(h) for _, _, h, _, _ in plan)
    for path, _, hits, drops, amb in plan:
        line = f"{path}: {len(hits)} id(s)"
        if drops:
            line += f"; cites a dropped commit: {', '.join(d[:12] for d in drops)} (fix by hand)"
        if amb:
            line += f"; ambiguous short id: {', '.join(amb)} (fix by hand)"
        print(line)
    print(f"found: {total} id(s) in {sum(1 for p in plan if p[2])} file(s)")
    if not a.apply:
        print("dry run: nothing written (add --apply)")
        return 0
    replaced = 0
    for path, data, hits, _, _ in plan:
        if not hits:
            continue
        count = [0]

        def swap(m):
            tok = m.group(0)
            new = full.get(tok) if len(tok) == 40 else short.get(tok) if len(tok) == 7 else None
            if new is None:
                return tok
            count[0] += 1
            return new
        out = HEX.sub(swap, data)
        n = count[0]
        if n != len(hits):
            print(f"STOP: {path}: found {len(hits)}, replaced {n}", file=sys.stderr)
            return 1
        with open(path, "wb") as fh:
            fh.write(out)  # bytes: the file keeps its own line endings
        replaced += n
    left = sum(len(find_hits(d, full, short)) for root in a.dirs for _, d in text_files(root))
    print(f"replaced: {replaced} of {total}; left after a second search: {left}")
    return 0 if replaced == total and left == 0 else 1


# ---------------------------------------------------------------- restore

def cmd_restore(a) -> int:
    listed = git(a.repo, "ls-tree", "-r", "-z", "--name-only", a.ref, "--", *a.paths, binary=True)
    expected = [p.decode() for p in listed.split(b"\0") if p]
    top = git(a.repo, "rev-parse", "--show-toplevel").strip()
    missing = [p for p in expected if not os.path.exists(os.path.join(top, p))]
    print(f"expected from {a.ref}: {len(expected)} file(s); missing on disk: {len(missing)}")
    if not a.apply:
        print("dry run: nothing written (add --apply)")
        return 0
    for p in missing:
        data = git(a.repo, "show", f"{a.ref}:{p}", binary=True)
        dest = os.path.join(top, p)
        os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
        with open(dest, "wb") as fh:
            fh.write(data)
    present = sum(1 for p in expected if os.path.exists(os.path.join(top, p)))
    print(f"restored: {len(missing)}; expected {len(expected)} = present {present}")
    return 0 if present == len(expected) else 1


# ---------------------------------------------------------------- push-size

def cmd_push_size(a) -> int:
    rng = a.range
    if not rng:
        up = git(a.repo, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}").strip()
        rng = f"{up}..HEAD"
    objs = git(a.repo, "rev-list", "--objects", rng)
    ids = "\n".join(line.split(" ", 1)[0] for line in objs.splitlines() if line.strip())
    p = subprocess.run(["git", "-C", a.repo, "cat-file", "--batch-check=%(objecttype) %(objectsize) %(objectname)"],
                       input=(ids + "\n").encode(), capture_output=True, creationflags=NO_WINDOW)
    names = {line.split(" ", 1)[0]: (line.split(" ", 1)[1] if " " in line else "") for line in objs.splitlines()}
    blobs = []
    for line in p.stdout.decode().splitlines():
        kind, size, oid = line.split()
        if kind == "blob":
            blobs.append((int(size), names.get(oid, "")))
    blobs.sort(reverse=True)
    total = sum(s for s, _ in blobs)
    limit = int(a.limit_mb * 1024 * 1024)
    over = [(s, n) for s, n in blobs if s > limit]
    print(f"range {rng}: {len(blobs)} new blob(s), {total / 1048576:.1f} MB in all")
    for s, n in blobs[:5]:
        print(f"  {s / 1048576:8.1f} MB  {n}")
    if over:
        print(f"STOP: {len(over)} blob(s) over {a.limit_mb} MB; the host will refuse this push", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="rewrite_tools.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("repoint")
    r.add_argument("--map", required=True)
    r.add_argument("dirs", nargs="+")
    r.add_argument("--apply", action="store_true")
    s = sub.add_parser("restore")
    s.add_argument("--ref", required=True)
    s.add_argument("--repo", default=".")
    s.add_argument("paths", nargs="+")
    s.add_argument("--apply", action="store_true")
    z = sub.add_parser("push-size")
    z.add_argument("--repo", default=".")
    z.add_argument("--range")
    z.add_argument("--limit-mb", type=float, default=100)
    a = ap.parse_args(argv)
    return {"repoint": cmd_repoint, "restore": cmd_restore, "push-size": cmd_push_size}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
