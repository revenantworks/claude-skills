#!/usr/bin/env python3
"""gatewarden drift: a live config against its tracked copy, and who owns what is installed.

Run, never read into context. Stdlib only. Read-only: it hashes, it never copies.

    drift.py --pair LIVE TRACKED [--pair LIVE TRACKED ...] [--json OUT]
    drift.py --pairs PAIRS.json [--json OUT]        ({"pairs": [{"live": ..., "tracked": ...}]})
    drift.py --inventory DIR [--inventory DIR ...] [--json OUT]

A pair whose live side is a junction or symlink into the tracked side cannot drift: it is
reported `linked`. Otherwise every file under both sides is hashed (SHA-256) and each
relative path is `same`, `differs`, `only-live` or `only-tracked`. Inventory lists each
entry of a folder (a skills or hooks folder): a link into a git repo names that repo as its
owner; a plain copy has `owner: none` unless a pair covers it. File contents never print.
Exit codes: 0 no drift, 1 drift or ownerless entries, 2 input error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from warden_fs import header, link_kind, norm, redact, write_json  # noqa: E402

SKIP = {".git", "__pycache__", ".DS_Store"}


def files(root: Path) -> dict[str, str]:
    out = {}
    if root.is_file():
        return {root.name: sha(root)}
    for dp, dns, fns in os.walk(root, followlinks=False):
        dns[:] = [d for d in dns if d not in SKIP and not link_kind(Path(dp) / d)]
        for fn in fns:
            if fn in SKIP:
                continue
            p = Path(dp) / fn
            out[p.relative_to(root).as_posix()] = sha(p)
    return out


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk.replace(b"\r\n", b"\n"))
    return h.hexdigest()


def resolved(p: Path) -> str:
    try:
        return norm(os.path.realpath(p)).casefold() if os.name == "nt" else norm(os.path.realpath(p))
    except OSError:
        return ""


def compare(live: Path, tracked: Path) -> dict:
    row = {"live": redact(str(live)), "tracked": redact(str(tracked))}
    if not live.exists() or not tracked.exists():
        row.update(state="missing", detail="live" if not live.exists() else "tracked")
        return row
    if link_kind(live) and resolved(live) == resolved(tracked):
        row.update(state="linked", detail=f"{link_kind(live)} into the tracked copy: cannot drift")
        return row
    a, b = files(live), files(tracked)
    diffs = []
    for rel in sorted(set(a) | set(b)):
        if rel not in b:
            diffs.append({"file": rel, "state": "only-live"})
        elif rel not in a:
            diffs.append({"file": rel, "state": "only-tracked"})
        elif a[rel] != b[rel]:
            diffs.append({"file": rel, "state": "differs"})
    row.update(state="drift" if diffs else "same", files=len(set(a) | set(b)), diffs=diffs)
    return row


def owner_repo(p: Path) -> str | None:
    cur = Path(os.path.realpath(p))
    for parent in [cur, *cur.parents]:
        if (parent / ".git").exists():
            return redact(str(parent))
    return None


def inventory(folder: Path, tracked_live: set[str]) -> list[dict]:
    out = []
    for e in sorted(folder.iterdir()):
        lk = link_kind(e)
        if lk:
            out.append({"entry": redact(str(e)), "kind": lk, "target": redact(os.path.realpath(e)),
                        "owner": owner_repo(e) or "none"})
        else:
            paired = resolved(e) in tracked_live
            out.append({"entry": redact(str(e)), "kind": "copy", "target": None,
                        "owner": "paired (see pairs)" if paired else "none"})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pair", nargs=2, action="append", metavar=("LIVE", "TRACKED"), default=[])
    ap.add_argument("--pairs")
    ap.add_argument("--inventory", action="append", default=[])
    ap.add_argument("--json", dest="out", default="-")
    a = ap.parse_args(argv)
    pairs = [(Path(os.path.expanduser(l)), Path(os.path.expanduser(t))) for l, t in a.pair]
    if a.pairs:
        try:
            data = json.loads(Path(a.pairs).read_text(encoding="utf-8"))
            pairs += [(Path(os.path.expanduser(p["live"])), Path(os.path.expanduser(p["tracked"])))
                      for p in data["pairs"]]
        except (OSError, ValueError, KeyError, TypeError) as e:
            print(f"error: pairs file: {type(e).__name__}", file=sys.stderr)
            return 2
    if not pairs and not a.inventory:
        print("error: give --pair, --pairs or --inventory", file=sys.stderr)
        return 2
    rows = [compare(l, t) for l, t in pairs]
    live_set = {resolved(l) for l, _ in pairs}
    inv = []
    for d in a.inventory:
        p = Path(os.path.expanduser(d))
        if not p.is_dir():
            print(f"error: inventory folder not found: {redact(str(p))}", file=sys.stderr)
            return 2
        inv += inventory(p, live_set)
    out = header("drift")
    out.update({"pairs": rows, "inventory": inv})
    write_json(out, a.out)
    bad = any(r["state"] in ("drift", "missing") for r in rows) or any(i["owner"] == "none" for i in inv)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
