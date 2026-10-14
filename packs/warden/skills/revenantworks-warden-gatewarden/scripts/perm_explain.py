#!/usr/bin/env python3
"""perm_explain.py: say which permission rule decides one tool call, from which
file, and why; and name the bypass shape when a deny looks like it should match
but does not. Stdlib only.

  python perm_explain.py --tool Bash --input "git -C . push" [--settings F ...] [--project DIR] [--json]

Walk: every file's deny rules, then ask, then allow; first match wins; a deny in
any file beats an allow in any other. A Bash or PowerShell line is split into its
parts and each is decided; one deny denies the line, and an allow needs every
part allowed. Env values are never read into the output.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import perm_common as pc  # noqa: E402

GIT_OPT = re.compile(r"^(git(?:\.exe)?)\s+((?:-C\s+\S+|-c\s+\S+|--[\w-]+(?:=\S+)?|-[a-zA-Z])\s+)+(.*)$")
SHELL_C = re.compile(r"""(?i)^(?:\S*[\\/])?(?:sh|bash|zsh|dash|pwsh|powershell|cmd)(?:\.exe)?\s+(?:-c|-command|/c)\s+(['"]?)(.*)\1\s*$""")


def bypasses(tool: str, part: str, files: list[dict]) -> list[dict]:
    found = []
    variants = []
    first = part.split()[0] if part.split() else ""
    if re.search(r"[\\/]", first):
        base = re.split(r"[\\/]", first)[-1]
        base = re.sub(r"(?i)\.exe$", "", base)
        variants.append(("absolute-path", " ".join([base] + part.split()[1:])))
    m = GIT_OPT.match(part)
    if m:
        variants.append(("git-global-option", f"git {m.group(3)}"))
    m = SHELL_C.match(part)
    if m:
        variants.append(("shell-wrapper", m.group(2)))
    for shape, variant in variants:
        for f in files:
            for r in f["rules"]["deny"]:
                rt, spec = pc.parse_rule(r)
                if pc.tool_family_match(rt, tool) and pc.spec_matches(tool, spec, variant):
                    found.append({"shape": shape, "rule": r, "file": f["path"],
                                  "note": f"`{part}` runs what `{variant}` runs, but the rule matches text, not intent"})
    return found


def main(argv) -> int:
    ap = argparse.ArgumentParser(prog="perm_explain.py")
    ap.add_argument("--tool", required=True)
    ap.add_argument("--input", required=True, help="the command, path or URL the call carries")
    ap.add_argument("--settings", action="append")
    ap.add_argument("--project")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    pairs = [("given", p) for p in a.settings if os.path.isfile(p)] if a.settings else pc.discover(a.project or os.getcwd())
    files = []
    for _, path in pairs:
        info = pc.load(path)
        if info["data"]:
            files.append({"path": path, "rules": pc.rules_of(info["data"])})
    walk, bys = [], []
    for part in pc.split_command(a.tool, a.input):
        d = pc.decide(a.tool, part, files)
        d["segment"] = part
        walk.append(d)
        if d["decision"] != "deny":
            bys += bypasses(a.tool, part, files)
    kinds = [w["decision"] for w in walk]
    if "deny" in kinds:
        decision = "deny"
    elif "ask" in kinds:
        decision = "ask"
    elif kinds and all(k == "allow" for k in kinds):
        decision = "allow"
    else:
        decision = "default"
    decider = next((w for w in walk if w["decision"] == decision), {"rule": None, "file": None})
    result = {"tool": a.tool, "decision": decision, "rule": decider["rule"], "file": decider["file"],
              "walk": walk, "bypass": bys,
              "note": "models the documented rule order; the harness is the authority. "
                      "'default' means no rule matched and the permission mode decides."}
    if a.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"{decision.upper()}  by {result['rule'] or 'no rule'}"
              + (f"  ({os.path.basename(result['file'])})" if result["file"] else ""))
        for w in walk:
            print(f"  part `{w['segment']}` -> {w['decision']} {w['rule'] or ''}")
        for b in bys:
            print(f"  BYPASS {b['shape']}: deny {b['rule']} does not match. {b['note']}")
        print(f"  {result['note']}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except SystemExit:
        raise
    except Exception as exc:
        print(f"perm_explain crashed: {type(exc).__name__}", file=sys.stderr)
        sys.exit(4)
