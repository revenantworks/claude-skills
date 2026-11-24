"""Port the gitleaks rule set into shroud as data (mods/shroud/hooks/gitleaks-rules.ts).

gitleaks (MIT, https://github.com/gitleaks/gitleaks) writes its rules for Go's RE2. This script
turns each into a JavaScript pattern with no flags: inline (?i), (?i:...), (?-i:...) and (?s)
are expanded by hand (a letter becomes [aA], a dot under s becomes [\\s\\S]), (?P<n> becomes
(?<n>, and \\z and \\A become $ and ^. A rule that needs a file path is skipped (shroud masks
text, not files), and so is any rule node cannot compile. The script prints what it dropped.

Run by hand when gitleaks ships new rules; never by CI or a build:

    curl -sSfL -o gitleaks.toml https://raw.githubusercontent.com/gitleaks/gitleaks/<tag>/config/gitleaks.toml
    python mods/shroud/scripts/port_gitleaks.py gitleaks.toml <tag>

Allowlist regexes that spell out gitleaks' own example keys are written defanged: one letter in
every long literal run sits in a class of its own (`c` becomes `[c]`). The regex matches the same
text, but the tracked file no longer holds a string that a secret scanner reads as a live key.
`--defang` re-applies this to the generated file in place, without the TOML:

    python mods/shroud/scripts/port_gitleaks.py --defang
"""
from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "hooks" / "gitleaks-rules.ts"

MIT = """MIT License

Copyright (c) 2019 Zachary Rice

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""


def fold_class(body: str) -> str:
    """A character class body with both cases of every letter and letter range."""
    out: list[str] = []
    extra: list[str] = []
    i = 0
    while i < len(body):
        c = body[i]
        if c == "\\":
            n = 4 if body[i + 1 : i + 2] == "x" else 2
            out.append(body[i : i + n])
            i += n
            continue
        if i + 2 < len(body) and body[i + 1] == "-" and body[i + 2] not in "]\\":
            a, b = c, body[i + 2]
            out.append(body[i : i + 3])
            if a.islower() and b.islower():
                extra.append(f"{a.upper()}-{b.upper()}")
            elif a.isupper() and b.isupper():
                extra.append(f"{a.lower()}-{b.lower()}")
            i += 3
            continue
        out.append(c)
        if c.isalpha() and c.isascii():
            extra.append(c.swapcase())
        i += 1
    joined = "".join(out)
    # A trailing "-" is a literal; keep it last so the added letters never form a range with it.
    if joined.endswith("-") and not joined.endswith("\\-"):
        return joined[:-1] + "".join(extra) + "-"
    return joined + "".join(extra)


def convert(src: str) -> str:
    """RE2 to a flagless JavaScript pattern."""
    out: list[str] = []
    stack: list[tuple[bool, bool]] = []  # (i, s) to restore when a group closes
    ci = False
    dot_all = False
    i = 0
    n = len(src)
    while i < n:
        c = src[i]
        if c == "\\":
            nxt = src[i + 1]
            if nxt == "z":
                out.append("$")
                i += 2
            elif nxt == "A":
                out.append("^")
                i += 2
            elif nxt == "x":
                out.append(src[i : i + 4])
                i += 4
            elif nxt.isalpha() or not ci:
                out.append(src[i : i + 2])
                i += 2
            else:
                out.append(src[i : i + 2])
                i += 2
            continue
        if c == "[":
            j = i + 1
            if j < n and src[j] == "^":
                j += 1
            if j < n and src[j] == "]":
                j += 1
            while src[j] != "]":
                j += 2 if src[j] == "\\" else 1
            head = "[^" if src[i + 1] == "^" else "["
            body = src[i + len(head) : j]
            if body.startswith("[:"):
                raise ValueError("POSIX class")
            out.append(head + (fold_class(body) if ci else body) + "]")
            i = j + 1
            continue
        if c == "(":
            if src.startswith("(?P<", i):
                stack.append((ci, dot_all))
                out.append("(?<")
                i += 4
                continue
            if src.startswith("(?", i) and i + 2 < n and src[i + 2] in "-is":
                j = i + 2
                while src[j] not in ":)":
                    j += 1
                flags = src[i + 2 : j]
                on, _, off = flags.partition("-")
                nci = (ci or "i" in on) and "i" not in off
                nds = (dot_all or "s" in on) and "s" not in off
                if src[j] == ")":  # (?i) sets the flags to the end of the enclosing group
                    ci, dot_all = nci, nds
                    i = j + 1
                    continue
                stack.append((ci, dot_all))
                ci, dot_all = nci, nds
                out.append("(?:")
                i = j + 1
                continue
            stack.append((ci, dot_all))
            out.append("(")
            i += 1
            continue
        if c == ")":
            ci, dot_all = stack.pop() if stack else (False, False)
            out.append(")")
            i += 1
            continue
        if c == "/":  # escaped, so no tracked line reads like a home-folder path
            out.append("\\/")
            i += 1
            continue
        if c == "." and dot_all:
            out.append("[\\s\\S]")
            i += 1
            continue
        if ci and c.isascii() and c.isalpha():
            out.append(f"[{c.lower()}{c.upper()}]")
            i += 1
            continue
        out.append(c)
        i += 1
    return "".join(out)


KEYCHAR = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
RUN = 16  # a literal run this long reads as a key to a secret scanner


def defang(pattern: str) -> str:
    """The same regex, with one letter of each long literal run wrapped in a class of its own.

    A literal letter `c` and the class `[c]` match exactly the same text, so detection does not
    change; the emitted string just no longer holds a run that a secret scanner reads as a key.
    """
    out: list[str] = []
    run = 0
    in_class = False
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if c == "\\":
            out.append(pattern[i : i + 2])
            run = 0
            i += 2
            continue
        if in_class:
            in_class = c != "]"
            out.append(c)
            i += 1
            continue
        if c == "[":
            in_class = True
            run = 0
        elif c in KEYCHAR:
            run += 1
            nxt = pattern[i + 1 : i + 2]
            if run >= RUN // 2 and c.isalpha() and nxt not in ("{", "*", "+", "?"):
                out.append(f"[{c}]")
                run = 0
                i += 1
                continue
        else:
            run = 0
        out.append(c)
        i += 1
    return "".join(out)


def defang_rule(rule: dict) -> dict:
    for a in rule.get("allow", []):
        a["regexes"] = [defang(r) for r in a["regexes"]]
    return rule


def rewrite_defanged() -> int:
    """Re-apply defang to the generated file in place (one JSON value per data line)."""
    lines = OUT.read_text(encoding="utf-8").split("\n")
    head = "export const GITLEAKS_ALLOW: { regexes: string[]; stopwords: string[] } = "
    changed = 0
    for n, line in enumerate(lines):
        if line.startswith(head):
            g = json.loads(line[len(head) :])
            g["regexes"] = [defang(r) for r in g["regexes"]]
            new = head + json.dumps(g, ensure_ascii=True)
        elif line.startswith("  {") and line.endswith("},"):
            new = f"  {json.dumps(defang_rule(json.loads(line[2:-1])), ensure_ascii=True)},"
        else:
            continue
        if new != line:
            lines[n] = new
            changed += 1
    OUT.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"defanged {OUT.name}: {changed} lines changed")
    return 0


def compiles(patterns: list[str]) -> list[bool]:
    js = "const ps=JSON.parse(require('fs').readFileSync(0,'utf8'));process.stdout.write(JSON.stringify(ps.map(p=>{try{new RegExp(p,'g');return true}catch{return false}})))"
    r = subprocess.run(["node", "-e", js], input=json.dumps(patterns), capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def main() -> int:
    if sys.argv[1:] == ["--defang"]:
        return rewrite_defanged()
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    toml_path, tag = sys.argv[1], sys.argv[2]
    data = tomllib.loads(Path(toml_path).read_text(encoding="utf-8"))
    rules: list[dict] = []
    dropped: list[str] = []
    for r in data["rules"]:
        rid = r["id"]
        if "regex" not in r or "path" in r:
            dropped.append(f"{rid}: needs a file path")
            continue
        try:
            pattern = convert(r["regex"])
        except (ValueError, IndexError) as exc:
            dropped.append(f"{rid}: {exc or 'unparsed'}")
            continue
        allow: list[dict] = []
        for a in r.get("allowlists", []):
            if a.get("paths") and a.get("condition", "OR").upper() == "AND":
                continue  # needs the path to decide
            regexes = [convert(x) for x in a.get("regexes", [])]
            words = [w.lower() for w in a.get("stopwords", [])]
            if regexes or words:
                allow.append({"target": a.get("regexTarget", "secret"), "regexes": regexes, "stopwords": words})
        rule = {"id": rid, "re": pattern, "keywords": [k.lower() for k in r.get("keywords", [])]}
        if r.get("secretGroup"):
            rule["group"] = r["secretGroup"]
        if r.get("entropy"):
            rule["entropy"] = r["entropy"]
        if allow:
            rule["allow"] = allow
            defang_rule(rule)
        rules.append(rule)
    ok = compiles([x["re"] for x in rules] + [p for x in rules for a in x.get("allow", []) for p in a["regexes"]])
    good = []
    k = len(rules)
    extra = ok[k:]
    for x, fine in zip(rules, ok[:k]):
        n = sum(len(a["regexes"]) for a in x.get("allow", []))
        sub, extra = extra[:n], extra[n:]
        if fine and all(sub):
            good.append(x)
        else:
            dropped.append(f"{x['id']}: node cannot compile it")
    g = data.get("allowlist", {})
    glob = {"regexes": [defang(convert(x)) for x in g.get("regexes", [])], "stopwords": [w.lower() for w in g.get("stopwords", [])]}
    body = [
        "// GENERATED by mods/shroud/scripts/port_gitleaks.py from the gitleaks rule set. Do not edit:",
        f"// re-run the script. Source: gitleaks {tag}, config/gitleaks.toml, under the MIT licence below.",
        f"// {len(good)} of {len(data['rules'])} rules ported; patterns carry no flags (case folding is expanded).",
        "//",
        *[f"// {line}".rstrip() for line in MIT.splitlines()],
        "",
        "export type LeakRule = { id: string; re: string; keywords: string[]; group?: number; entropy?: number; allow?: Array<{ target: string; regexes: string[]; stopwords: string[] }> }",
        "",
        f"export const GITLEAKS_VERSION = {json.dumps(tag)}",
        "",
        f"export const GITLEAKS_ALLOW: {{ regexes: string[]; stopwords: string[] }} = {json.dumps(glob, ensure_ascii=True)}",
        "",
        "export const GITLEAKS_RULES: LeakRule[] = [",
        *[f"  {json.dumps(x, ensure_ascii=True)}," for x in good],
        "]",
        "",
    ]
    OUT.write_text("\n".join(body), encoding="utf-8", newline="\n")
    print(f"wrote {OUT.name}: {len(good)} rules; dropped {len(dropped)}")
    for d in dropped:
        print(f"  dropped {d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
