#!/usr/bin/env python3
"""brandscribe tokens_check — optional, standard library only, run (not read).

Three jobs, all offline, all read-only on their inputs:

  contrast FG BG        WCAG 2.x contrast ratio of two hex colours
  check tokens.json     list-shape, name, duplicate, value, alias and usage checks
                        for a Claude Design System tokens file; exit 1 on findings
  convert dtcg.json     turn a W3C DTCG (name-to-value map) file into the list shape,
                        printed to stdout; nothing is written

The skill never requires this script. Without Python, Claude computes the same
figures with its own code tool, or reports them as unmeasured on this surface.
"""
import json
import re
import sys

NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
FUNC_RE = re.compile(r"^(?:rgba?|hsla?|oklch|oklab|lab|lch|hwb)\(([^()]*)\)$", re.IGNORECASE)
ALIAS_RE = re.compile(r"^\{([^{}]+)\}$")


def _hex_to_rgb(value):
    if not isinstance(value, str) or not HEX_RE.match(value):
        raise ValueError("not a hex colour: %r" % (value,))
    h = value[1:]
    if len(h) in (3, 4):
        h = "".join(c * 2 for c in h[:3])
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def _luminance(rgb):
    def chan(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (chan(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg, bg):
    """WCAG 2.x contrast ratio between two hex colours (order-free)."""
    a = _luminance(_hex_to_rgb(fg))
    b = _luminance(_hex_to_rgb(bg))
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def _colour_value_ok(v):
    if isinstance(v, str):
        if HEX_RE.match(v) or ALIAS_RE.match(v):
            return True
        return bool(FUNC_RE.match(v.strip()))
    return False


def _values_of(token):
    v = token.get("value")
    if isinstance(v, dict):
        return list(v.values())
    return [v]


def check_tokens(doc):
    """Return a list of findings (strings) for a Design System tokens document."""
    findings = []
    seen = {}
    families = [k for k, v in doc.items() if isinstance(v, dict) and k not in ("type", "meta")]
    for fam in families:
        body = doc[fam]
        tokens = body.get("tokens")
        if not isinstance(tokens, list):
            findings.append("SHAPE %s: not a {\"tokens\": [...]} list (a DTCG map the page cannot read)" % fam)
            continue
        for t in tokens:
            if not isinstance(t, dict):
                findings.append("SHAPE %s: entry is not an object" % fam)
                continue
            name = t.get("name")
            if not isinstance(name, str) or not NAME_RE.match(name):
                findings.append("NAME %s: %r breaks the name grammar" % (fam, name))
            elif name in seen:
                findings.append("DUPLICATE %s: %r already used in %s" % (fam, name, seen[name]))
            else:
                seen[name] = fam
            if not str(t.get("usage", "")).strip():
                findings.append("USAGE %s: %r has no usage note" % (fam, name))
    for fam in families:
        tokens = doc[fam].get("tokens")
        if not isinstance(tokens, list):
            continue
        for t in tokens:
            if not isinstance(t, dict):
                continue
            name = t.get("name")
            for v in _values_of(t):
                m = ALIAS_RE.match(v) if isinstance(v, str) else None
                if m:
                    target = m.group(1)
                    if target == name or target not in seen:
                        findings.append("ALIAS %s: %r points at %r (missing or itself)" % (fam, name, target))
                elif fam == "color" and not _colour_value_ok(v):
                    findings.append("VALUE color: %r has %r, which the page drops" % (name, v))
    return findings


def _alias_to_list(value):
    if isinstance(value, str):
        m = ALIAS_RE.match(value)
        if m:
            parts = m.group(1).split(".")
            return "{%s}" % "-".join(parts[1:] or parts)
    return value


def dtcg_to_list(src):
    """Convert a DTCG nested map into the Design System list shape (one family per top-level group)."""
    out = {}
    for fam, group in src.items():
        if fam.startswith("$") or not isinstance(group, dict):
            continue
        entries = []

        def walk(node, path):
            if isinstance(node, dict) and "$value" in node:
                entries.append({
                    "name": "-".join(path),
                    "value": _alias_to_list(node["$value"]),
                    "usage": node.get("$description", ""),
                })
                return
            if isinstance(node, dict):
                for k, v in node.items():
                    if not k.startswith("$"):
                        walk(v, path + [k])

        walk(group, [])
        out[fam] = {"tokens": entries}
    return out


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def main(argv):
    if len(argv) >= 3 and argv[0] == "contrast":
        print("%.2f:1" % contrast_ratio(argv[1], argv[2]))
        return 0
    if len(argv) == 2 and argv[0] == "check":
        findings = check_tokens(_load(argv[1]))
        for f in findings:
            print(f)
        print("%d finding(s)" % len(findings))
        return 1 if findings else 0
    if len(argv) == 2 and argv[0] == "convert":
        print(json.dumps(dtcg_to_list(_load(argv[1])), indent=2))
        return 0
    sys.stderr.write(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
