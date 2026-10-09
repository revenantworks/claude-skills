#!/usr/bin/env python3
"""gatewarden drive rules: a scan_tree.py JSON against the owner's written drive layout rules.

Run, never read into context. Stdlib only (PyYAML is used for a .yml rules file only if
it is already installed; JSON always works). Read-only.

    drive_rules.py SCAN.json [--rules RULES.json] [--json OUT]

Built-in checks always run (a repo nested in another repo, a link whose target is gone).

Rule kinds (schema in references/drive-rules.md). Patterns are fnmatch globs on the
path RELATIVE to the scan root, forward slashes:
  repo_roots   {"allow": ["github/*/*"]}           a git repo anywhere else is a finding
  forbidden    {"pattern": "**/node_modules"}       any folder matching is a finding
  frozen       {"path": "backups", "since": "YYYY-MM-DD"}   newer content inside is a finding
  size_cap     {"path": "inbox", "max_bytes": 1e9}  a folder over its cap is a finding
  no_links     {"path": "repos"}                    a junction or symlink under it is a finding
Exit codes: 0 no findings, 1 findings, 2 input error. The rule names and paths are data.
"""
from __future__ import annotations

import argparse
import calendar
import fnmatch
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from warden_fs import header, write_json  # noqa: E402

KINDS = {"repo_roots", "forbidden", "frozen", "size_cap", "no_links"}


def load_rules(path: str) -> list[dict]:
    text = Path(path).read_text(encoding="utf-8")
    if path.endswith((".yml", ".yaml")):
        try:
            import yaml  # optional, never installed by this skill
        except ModuleNotFoundError:
            raise ValueError("a .yml rules file needs PyYAML; write the rules as JSON instead")
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    rules = data.get("rules") if isinstance(data, dict) else None
    if not isinstance(rules, list):
        raise ValueError("rules file needs a top-level 'rules' list")
    for i, r in enumerate(rules):
        if not isinstance(r, dict) or r.get("kind") not in KINDS or not r.get("name"):
            raise ValueError(f"rule {i}: needs 'name' and a 'kind' in {sorted(KINDS)}")
    return rules


def rel(path: str, root: str) -> str:
    p, r = path.replace("\\", "/"), root.replace("\\", "/").rstrip("/")
    if p.casefold() == r.casefold():
        return ""
    if p.casefold().startswith(r.casefold() + "/"):
        return p[len(r) + 1:]
    return p


def match(relpath: str, pattern: str) -> bool:
    pat = pattern.strip("/")
    if fnmatch.fnmatch(relpath, pat):
        return True
    if pat.startswith("**/"):
        tail = pat[3:]
        return fnmatch.fnmatch(relpath, tail) or fnmatch.fnmatch(relpath, "*/" + tail)
    return False


def walk(tree: dict):
    yield tree
    for c in tree.get("children", []) or []:
        yield from walk(c)


def check(scan: dict, rules: list[dict]) -> list[dict]:
    root = scan.get("root", "")
    nodes = list(walk(scan.get("tree", {})))
    findings = []
    for r in rules:
        k, name = r["kind"], r["name"]
        if k == "repo_roots":
            allow = r.get("allow", [])
            for repo in scan.get("repos", []):
                rp = rel(repo, root)
                if rp and not any(match(rp, a) for a in allow):
                    findings.append({"rule": name, "path": repo, "detail": "git repo outside the allowed roots"})
        elif k == "forbidden":
            for n in nodes:
                rp = rel(n.get("path", ""), root)
                if rp and match(rp, r.get("pattern", "")):
                    findings.append({"rule": name, "path": n["path"], "detail": "matches a forbidden pattern"})
        elif k == "frozen":
            since = calendar.timegm(time.strptime(r["since"], "%Y-%m-%d"))
            for n in nodes:
                if rel(n.get("path", ""), root) == r.get("path", "").strip("/") and n.get("newest", 0) > since + 86400:
                    when = time.strftime("%Y-%m-%d", time.gmtime(n["newest"]))
                    findings.append({"rule": name, "path": n["path"], "detail": f"content changed {when}, frozen since {r['since']}"})
        elif k == "size_cap":
            cap = float(r.get("max_bytes", 0))
            for n in nodes:
                if rel(n.get("path", ""), root) == r.get("path", "").strip("/") and n.get("bytes", 0) > cap:
                    findings.append({"rule": name, "path": n["path"], "detail": f"{n['bytes']} bytes over cap {int(cap)}"})
        elif k == "no_links":
            base = r.get("path", "").strip("/")
            for ln in scan.get("links", []):
                rp = rel(ln.get("path", ""), root)
                if rp == base or rp.startswith(base + "/") or base == "":
                    findings.append({"rule": name, "path": ln["path"], "detail": f"{ln.get('kind')} link under a no-links folder"})
    return findings


def builtin(scan: dict) -> list[dict]:
    """Checks that hold on any machine, with no owner rule: nested repos and dead links."""
    out = []
    repos = sorted(scan.get("repos", []), key=len)
    for i, outer in enumerate(repos):
        for inner in repos[i + 1:]:
            if inner.casefold().startswith(outer.casefold().rstrip("/") + "/"):
                out.append({"rule": "builtin:nested-repo", "path": inner, "detail": f"repo inside repo {outer}"})
    for ln in scan.get("links", []):
        if ln.get("target_exists") is False:
            out.append({"rule": "builtin:dead-link", "path": ln.get("path"), "detail": f"{ln.get('kind')} target missing"})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("scan")
    ap.add_argument("--rules", help="owner rules file; without it only the built-in checks run")
    ap.add_argument("--json", dest="out", default="-")
    a = ap.parse_args(argv)
    try:
        scan = json.loads(Path(a.scan).read_text(encoding="utf-8"))
        rules = load_rules(a.rules) if a.rules else []
    except (OSError, ValueError, KeyError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    if scan.get("source") != "stdlib":
        print("note: imported scans carry no repos or links; repo_roots, no_links and the built-in "
              "checks need a stdlib scan", file=sys.stderr)
    findings = builtin(scan) + check(scan, rules)
    out = header("drive_rules")
    out.update({"root": scan.get("root"), "rules": len(rules), "findings": findings})
    write_json(out, a.out)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
