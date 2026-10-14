#!/usr/bin/env python3
"""gatewarden map: a junction-aware space scan of one folder or drive. Read-only.

Run, never read into context. Stdlib only.

    scan_tree.py PATH --json OUT [--depth 3] [--top 25] [--max-seconds 600]
    scan_tree.py PATH --from-wiztree CSV --json OUT     (import a WizTree export)
    scan_tree.py PATH --from-dust JSON --json OUT       (import `dust -j` output)
    scan_tree.py --status DIR                           (age and totals of saved scans)

Rules it keeps: it never follows a junction or a symlink (each is listed once, as a
link, with its target); it never writes anywhere but OUT; every printed path is
redacted (home -> ~). Sizes are logical bytes; a WizTree import carries allocated bytes.
Exit codes: 0 ok (unreadable folders are listed under errors), 1 partial (time limit), 2 input error.
"""
from __future__ import annotations

import argparse
import csv
import heapq
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from warden_fs import header, human, is_repo, link_kind, link_target, norm, redact, write_json  # noqa: E402


class Scan:
    def __init__(self, depth: int, top: int, max_seconds: float):
        self.depth, self.top, self.deadline = depth, top, time.monotonic() + max_seconds
        self.files_heap: list[tuple[int, str]] = []
        self.links: list[dict] = []
        self.repos: list[str] = []
        self.errors: list[dict] = []
        self.partial = False
        self.visited: set[tuple[int, int]] = set()

    def node(self, path: str, level: int) -> dict:
        n = {"name": os.path.basename(path.rstrip("/\\")) or path, "path": redact(path),
             "kind": "repo" if is_repo(path) else "dir", "bytes": 0, "files": 0, "newest": 0.0,
             "children": []}
        if n["kind"] == "repo":
            self.repos.append(redact(path))
        try:
            st = os.stat(path, follow_symlinks=False)
            key = (st.st_dev, st.st_ino)
            if st.st_ino and key in self.visited:
                return n
            self.visited.add(key)
        except OSError:
            pass
        if time.monotonic() > self.deadline:
            self.partial = True
            return n
        try:
            it = os.scandir(path)
        except OSError as e:
            self.errors.append({"path": redact(path), "reason": type(e).__name__})
            return n
        with it:
            for e in it:
                lk = link_kind(e)
                if lk:
                    tgt = link_target(e.path)
                    self.links.append({"path": redact(e.path), "kind": lk,
                                       "target": redact(tgt) if tgt else None,
                                       "target_exists": os.path.exists(e.path)})
                    if level < self.depth:
                        n["children"].append({"name": e.name, "path": redact(e.path), "kind": "link",
                                              "link": lk, "bytes": 0, "files": 0})
                    continue
                try:
                    if e.is_dir(follow_symlinks=False):
                        child = self.node(e.path, level + 1)
                        n["bytes"] += child["bytes"]
                        n["files"] += child["files"]
                        n["newest"] = max(n["newest"], child["newest"])
                        if level < self.depth:
                            n["children"].append(child)
                    else:
                        st = e.stat(follow_symlinks=False)
                        n["bytes"] += st.st_size
                        n["files"] += 1
                        n["newest"] = max(n["newest"], st.st_mtime)
                        item = (st.st_size, e.path)
                        if len(self.files_heap) < self.top:
                            heapq.heappush(self.files_heap, item)
                        elif st.st_size > self.files_heap[0][0]:
                            heapq.heapreplace(self.files_heap, item)
                except OSError as err:
                    self.errors.append({"path": redact(e.path), "reason": type(err).__name__})
        n["children"].sort(key=lambda c: c["bytes"], reverse=True)
        if not n["children"]:
            del n["children"]
        return n


def top_dirs(tree: dict, limit: int) -> list[dict]:
    out = []

    def walk(n):
        for c in n.get("children", []):
            if c["kind"] in ("dir", "repo"):
                out.append({"path": c["path"], "bytes": c["bytes"], "kind": c["kind"]})
                walk(c)
    walk(tree)
    return sorted(out, key=lambda d: d["bytes"], reverse=True)[:limit]


def totals(tree: dict, links: int, errors: int) -> dict:
    return {"bytes": tree["bytes"], "files": tree["files"], "links": links, "errors": errors}


def from_wiztree(csv_path: str, root: str, depth: int, top: int) -> dict:
    """WizTree /export CSV: a banner line, then a header with 'File Name', 'Size', 'Allocated'."""
    with open(csv_path, encoding="utf-8-sig", errors="replace", newline="") as f:
        lines = f.read().splitlines()
    start = next((i for i, ln in enumerate(lines) if "File Name" in ln), None)
    if start is None:
        raise ValueError("no 'File Name' header row: not a WizTree export")
    rows = csv.DictReader(lines[start:])
    base = norm(root).rstrip("/")
    nodes: dict[str, dict] = {}
    files: list[tuple[int, str]] = []
    for r in rows:
        name = r.get("File Name") or ""
        size = int(float(r.get("Size") or 0))
        alloc = int(float(r.get("Allocated") or size))
        p = norm(name)
        rel = p[len(base):].strip("/") if p.casefold().startswith(base.casefold()) else None
        if rel is None:
            continue
        if name.endswith(("\\", "/")):
            lvl = 0 if not rel else rel.count("/") + 1
            if lvl <= depth:
                nodes[rel] = {"name": rel.rsplit("/", 1)[-1] or base, "path": redact(p), "kind": "dir",
                              "bytes": size, "allocated": alloc, "files": int(r.get("Files") or 0),
                              "children": []}
        else:
            files.append((size, p))
    tree = nodes.get("") or {"name": base, "path": redact(base), "kind": "dir", "bytes": 0, "files": 0,
                             "children": []}
    for rel, n in sorted(nodes.items(), key=lambda kv: kv[0].count("/")):
        if rel:
            parent = nodes.get(rel.rsplit("/", 1)[0] if "/" in rel else "", tree)
            parent["children"].append(n)
    for n in [tree, *nodes.values()]:
        n["children"].sort(key=lambda c: c["bytes"], reverse=True)
    files.sort(reverse=True)
    return {"tree": tree, "top_files": [{"path": redact(p), "bytes": s} for s, p in files[:top]]}


def _dust_size(v) -> int:
    if isinstance(v, (int, float)):
        return int(v)
    m = re.match(r"^\s*([\d.]+)\s*([KMGTP]?)i?B?\s*$", str(v), re.I)
    if not m:
        return 0
    mult = {"": 1, "K": 1024, "M": 1024 ** 2, "G": 1024 ** 3, "T": 1024 ** 4, "P": 1024 ** 5}
    return int(float(m.group(1)) * mult[m.group(2).upper()])


def from_dust(json_path: str) -> dict:
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))

    def conv(d):
        n = {"name": os.path.basename(str(d.get("name", "")).rstrip("/\\")) or str(d.get("name", "")),
             "path": redact(str(d.get("name", ""))), "kind": "dir", "bytes": _dust_size(d.get("size", 0)),
             "files": 0}
        kids = [conv(c) for c in d.get("children", []) or []]
        if kids:
            n["children"] = sorted(kids, key=lambda c: c["bytes"], reverse=True)
        return n
    return {"tree": conv(data), "top_files": []}


def status(folder: str) -> int:
    rows = []
    for p in sorted(Path(folder).glob("*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(d, dict) or d.get("tool") != "warden.scan_tree":
            continue
        rows.append((p.name, d.get("generated", "?"), d.get("root", "?"), d.get("totals", {})))
    if not rows:
        print("no gatewarden map scans in that folder")
        return 1
    for name, gen, root, t in rows:
        print(f"{name}  {gen}  {root}  {human(t.get('bytes', 0))}  files={t.get('files', 0)}  "
              f"links={t.get('links', 0)}  partial={t.get('partial', False)}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("path", nargs="?")
    ap.add_argument("--json", dest="out", default="-")
    ap.add_argument("--depth", type=int, default=3)
    ap.add_argument("--top", type=int, default=25)
    ap.add_argument("--max-seconds", type=float, default=600)
    ap.add_argument("--from-wiztree")
    ap.add_argument("--from-dust")
    ap.add_argument("--status")
    a = ap.parse_args(argv)
    if a.status:
        return status(a.status)
    if not a.path or not os.path.isdir(a.path):
        print("error: PATH must be an existing folder", file=sys.stderr)
        return 2
    root = os.path.abspath(a.path)
    out = header("scan_tree")
    out.update({"root": redact(root), "depth": a.depth})
    if a.from_wiztree or a.from_dust:
        try:
            got = from_wiztree(a.from_wiztree, root, a.depth, a.top) if a.from_wiztree else from_dust(a.from_dust)
        except (OSError, ValueError, KeyError) as e:
            print(f"error: import failed: {type(e).__name__}: {e}", file=sys.stderr)
            return 2
        tree = got["tree"]
        out.update({"source": "wiztree" if a.from_wiztree else "dust",
                    "totals": {**totals(tree, 0, 0), "partial": False},
                    "top_dirs": top_dirs(tree, a.top), "top_files": got["top_files"],
                    "links": [], "repos": [], "errors": [], "tree": tree,
                    "note": "imported sizes; links and repos are not in this source — run a stdlib scan "
                            "of the folders that matter for those"})
        write_json(out, a.out)
        return 0
    s = Scan(a.depth, a.top, a.max_seconds)
    tree = s.node(root, 0)
    tree["kind"] = "repo" if is_repo(root) else "dir"
    out.update({"source": "stdlib", "totals": {**totals(tree, len(s.links), len(s.errors)), "partial": s.partial},
                "top_dirs": top_dirs(tree, a.top),
                "top_files": [{"path": redact(p), "bytes": b} for b, p in sorted(s.files_heap, reverse=True)],
                "links": s.links, "repos": s.repos, "errors": s.errors[:200], "tree": tree})
    write_json(out, a.out)
    if a.out and a.out != "-":
        print(f"scanned {out['root']}: {human(tree['bytes'])} in {tree['files']} files, "
              f"{len(s.links)} links (not followed), {len(s.repos)} repos, {len(s.errors)} unreadable"
              + (", PARTIAL (time limit)" if s.partial else ""))
    return 1 if s.partial else 0


if __name__ == "__main__":
    sys.exit(main())
