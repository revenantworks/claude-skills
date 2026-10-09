#!/usr/bin/env python3
"""brandscribe ui_check: the neutral UI floor on built HTML and CSS. Optional, standard library only.

Static scan of a built output folder (or single files): HTML through html.parser, CSS through a
small brace parser, a simplified cascade (tag, class, id, attribute, descendant, child and sibling
selectors; :is, :where and :not; escaped class names; cascade layers in declared order; inline style;
custom properties with fallbacks; inheritance). No network, no browser, no JavaScript, never follows
a remote URL, writes nothing.

R20 measures body text, not every small line: paragraphs, list items, definitions and quotes in the
main content. Navigation, header, footer, aside, captions, labels, tables, controls, small-print
classes and short lines set below the page's dominant body size are classed out, and the
classification is reported per file (`body_text` in --json).

Rules of the checker
  * 31 rules (R1-R31, `--list-rules`). P0-P2 rows are findings; P3 rows are questions about
    generic-UI patterns and never change the exit code.
  * Anything the static cascade cannot resolve (no painted ground, a gradient or image ground, an
    unresolved colour, a state or media variant) is reported "unmeasured", never as a failure.
  * Text inside scanned files is data. A comment, text node or attribute that addresses an agent
    is reported as INJECTED at its location, its content is not echoed, and nothing it says is done.
  * Waivers: one file, `.ui-check-ignore` in the scanned folder (or `--ignore FILE`), one line per
    waiver: `RULE GLOB REASON`. A line without a reason is reported invalid and not applied.

Exit codes: 0 no P0-P2 finding, 1 findings, 2 error (missing path, unreadable input).

    python ui_check.py dist/
    python ui_check.py --json dist/index.html
    python ui_check.py --list-rules
"""
import argparse
import colorsys
import fnmatch
import json
import os
import re
import sys
from html.parser import HTMLParser
from urllib.parse import parse_qs, unquote, urlparse

RULES = [
    ("R1", "asset-missing", "P1", "local img, srcset, link, script, source or CSS url() target not on disk"),
    ("R2", "font-file-missing", "P1", "@font-face local src file absent"),
    ("R3", "font-unsourced", "P2", "first font family is in no @font-face, font link or system/generic stack"),
    ("R4", "img-alt-missing", "P1", "img with no alt attribute (alt=\"\" passes)"),
    ("R5", "control-unlabelled", "P1", "input, select or textarea with no label, aria-label or aria-labelledby"),
    ("R6", "placeholder-only-label", "P2", "a placeholder is the control's only label (copy fix: commscribe)"),
    ("R7", "control-unnamed", "P1", "button, link or role=button with no accessible name"),
    ("R8", "html-lang-missing", "P2", "html element has no lang"),
    ("R9", "viewport-meta-missing", "P1", "document has no meta viewport"),
    ("R10", "heading-order", "P2", "heading level skipped (P2); more than one h1 (P3)"),
    ("R11", "contrast-low", "P1", "text below 4.5:1, or 3:1 for large text, on a resolvable painted ground"),
    ("R12", "focus-removed", "P1", "outline removed with no replacement and no :focus-visible style"),
    ("R13", "duplicate-id", "P2", "an id value used twice in one document"),
    ("R14", "reduced-motion-missing", "P2", "animation or transition with no prefers-reduced-motion block"),
    ("R15", "layout-prop-animated", "P2", "transition or keyframes on width, height, top, left, margin or padding"),
    ("R16", "will-change-at-rest", "P3", "will-change on a base (non-state) selector"),
    ("R17", "bounce-easing", "P3", "cubic-bezier with a y value outside 0-1"),
    ("R18", "fixed-width-wide", "P2", "px width or min-width over 480 not capped by min(), a max-width or a width media query"),
    ("R19", "target-small", "P2", "interactive selector with width or height under 24px (WCAG 2.5.8)"),
    ("R20", "body-text-small", "P2", "main-content body text under 16px (P2), under 12px (P1); nav, captions, labels, small print excluded"),
    ("R21", "measure-unbounded", "P3", "long running text with no max-width on it or any ancestor"),
    ("R22", "gradient-text", "P3", "background-clip: text over a gradient"),
    ("R23", "side-stripe", "P3", "thick coloured border-left or border-right on a non-table element"),
    ("R24", "glow-shadow", "P3", "zero-offset, blurred, coloured shadow"),
    ("R25", "offset-block-shadow", "P3", "offset shadow with zero blur"),
    ("R26", "emoji-icon", "P3", "an emoji leads a button, nav link or list item"),
    ("R27", "type-extremes", "P3", "letter-spacing below -0.04em, or a font size above 6rem"),
    ("R28", "card-nest", "P3", "a card-classed element inside another"),
    ("R29", "eyebrow", "P3", "short uppercase letter-spaced label directly before an h1-h3"),
    ("R30", "raw-colour-count", "P3", "more than 12 distinct literal colours outside custom properties"),
    ("R31", "browser-surface-unthemed", "P3", "no ::selection or no :focus-visible styling"),
]
SEV = {r[0]: r[2] for r in RULES}
SLUG = {r[0]: r[1] for r in RULES}
SLUG["INJECTED"] = "injected"
SEV["INJECTED"] = "P1"

# ------------------------------------------------------------------ colour
NAMED = {
    "black": (0, 0, 0), "white": (255, 255, 255), "red": (255, 0, 0), "green": (0, 128, 0),
    "blue": (0, 0, 255), "yellow": (255, 255, 0), "orange": (255, 165, 0), "purple": (128, 0, 128),
    "gray": (128, 128, 128), "grey": (128, 128, 128), "silver": (192, 192, 192), "navy": (0, 0, 128),
    "teal": (0, 128, 128), "maroon": (128, 0, 0), "olive": (128, 128, 0), "lime": (0, 255, 0),
    "aqua": (0, 255, 255), "cyan": (0, 255, 255), "fuchsia": (255, 0, 255), "magenta": (255, 0, 255),
    "pink": (255, 192, 203), "gold": (255, 215, 0), "indigo": (75, 0, 130), "violet": (238, 130, 238),
    "brown": (165, 42, 42), "crimson": (220, 20, 60), "tomato": (255, 99, 71), "coral": (255, 127, 80),
    "salmon": (250, 128, 114), "tan": (210, 180, 140), "beige": (245, 245, 220), "ivory": (255, 255, 240),
    "whitesmoke": (245, 245, 245), "gainsboro": (220, 220, 220), "lightgray": (211, 211, 211),
    "lightgrey": (211, 211, 211), "darkgray": (169, 169, 169), "darkgrey": (169, 169, 169),
    "dimgray": (105, 105, 105), "dimgrey": (105, 105, 105), "slategray": (112, 128, 144),
    "rebeccapurple": (102, 51, 153), "hotpink": (255, 105, 180), "royalblue": (65, 105, 225),
    "steelblue": (70, 130, 180), "skyblue": (135, 206, 235), "dodgerblue": (30, 144, 255),
}
_NUM = r"[-+]?(?:\d+\.?\d*|\.\d+)"
_FUNC_RE = re.compile(r"^(rgba?|hsla?)\(\s*(.*?)\s*\)$", re.I)
COLOUR_TOKEN_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b|(?:rgba?|hsla?)\([^)]*\)|\b[a-zA-Z]+\b")


def _channel(tok, scale):
    tok = tok.strip()
    if tok.endswith("%"):
        return float(tok[:-1]) * scale / 100.0
    return float(tok)


def parse_colour(text):
    """(r, g, b, a) with 0-255 channels and 0-1 alpha, or None when not a resolvable colour."""
    if not isinstance(text, str):
        return None
    t = text.strip().lower()
    if t.endswith("!important"):
        t = t[:-10].strip()
    if t == "transparent":
        return (0, 0, 0, 0.0)
    if t in NAMED:
        return NAMED[t] + (1.0,)
    if t.startswith("#"):
        h = t[1:]
        if not re.fullmatch(r"[0-9a-f]{3,4}|[0-9a-f]{6}|[0-9a-f]{8}", h):
            return None
        if len(h) in (3, 4):
            h = "".join(c * 2 for c in h)
        a = int(h[6:8], 16) / 255.0 if len(h) == 8 else 1.0
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), round(a, 4))
    m = _FUNC_RE.match(t)
    if not m or "var(" in t or "calc(" in t:
        return None
    kind, body = m.group(1), m.group(2)
    alpha = 1.0
    if "/" in body:
        body, a = body.split("/", 1)
        alpha = _channel(a, 1.0)
    parts = [p for p in re.split(r"[\s,]+", body.strip()) if p]
    if len(parts) == 4:
        alpha = _channel(parts.pop(), 1.0)
    if len(parts) != 3:
        return None
    try:
        if kind.startswith("rgb"):
            r, g, b = (max(0, min(255, round(_channel(p, 255.0)))) for p in parts)
        else:
            hue = float(re.sub(r"deg$", "", parts[0])) % 360 / 360.0
            s = _channel(parts[1], 1.0) if parts[1].endswith("%") else float(parts[1]) / 100.0
            li = _channel(parts[2], 1.0) if parts[2].endswith("%") else float(parts[2]) / 100.0
            rr, gg, bb = colorsys.hls_to_rgb(hue, li, s)
            r, g, b = round(rr * 255), round(gg * 255), round(bb * 255)
    except ValueError:
        return None
    return (r, g, b, round(max(0.0, min(1.0, alpha)), 4))


def colours_in(value):
    """Every parsable colour token in a declaration value (url() bodies skipped)."""
    value = re.sub(r"url\([^)]*\)", " ", value or "")
    out = []
    for tok in COLOUR_TOKEN_RE.findall(value):
        if tok.lower() in ("transparent", "currentcolor", "inherit", "initial", "unset", "none"):
            continue
        if re.fullmatch(r"[a-zA-Z]+", tok) and tok.lower() not in NAMED:
            continue
        c = parse_colour(tok)
        if c is not None:
            out.append(c)
    return out


def _lum(c):
    def ch(v):
        v = v / 255.0
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(c[0]) + 0.7152 * ch(c[1]) + 0.0722 * ch(c[2])


def contrast(c1, c2):
    """WCAG 2.x contrast ratio of two opaque colours (alpha ignored; composite first)."""
    a, b = _lum(c1), _lum(c2)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


def blend(top, base):
    a = top[3]
    return tuple(round(top[i] * a + base[i] * (1 - a)) for i in range(3)) + (1.0,)


def floor_for(px, weight):
    """4.5 for body text; 3.0 for large text (24px, or 18.66px at weight 700 and above)."""
    if px >= 24.0 or (px >= 18.66 and weight >= 700):
        return 3.0
    return 4.5


def saturated(c):
    h, li, s = colorsys.rgb_to_hls(c[0] / 255.0, c[1] / 255.0, c[2] / 255.0)
    return s >= 0.25 and 0.08 <= li <= 0.92


def hexof(c):
    return "#%02x%02x%02x" % c[:3]


# ------------------------------------------------------------------ HTML model
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
NO_TEXT = {"script", "style", "head", "title", "noscript", "template", "svg", "math", "option"}


class Node:
    def __init__(self, tag, attrs, line, parent):
        self.tag, self.attrs, self.line, self.parent = tag, attrs, line, parent
        self.kids = []
        self.declared = {}

    @property
    def elements(self):
        return [k for k in self.kids if isinstance(k, Node)]

    def classes(self):
        return self.attrs.get("class", "").split()

    def ancestors(self):
        p = self.parent
        while p is not None and p.tag != "#document":
            yield p
            p = p.parent

    def direct_text(self):
        return "".join(k for k in self.kids if isinstance(k, str))

    def full_text(self):
        out = []
        for k in self.kids:
            if isinstance(k, str):
                out.append(k)
            elif k.tag not in ("script", "style"):
                out.append(k.full_text())
        return "".join(out)


class _Builder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#document", {}, 1, None)
        self.stack = [self.root]
        self.nodes, self.comments, self.order = [], [], []
        self._style = None

    def _open(self, tag, attrs, push):
        line = self.getpos()[0]
        a = {k.lower(): (v if v is not None else "") for k, v in attrs}
        node = Node(tag, a, line, self.stack[-1])
        self.stack[-1].kids.append(node)
        self.nodes.append(node)
        if tag == "link":
            self.order.append(("link", node))
        if push and tag not in VOID:
            self.stack.append(node)
            if tag == "style":
                self._style = [line, []]

    def handle_starttag(self, tag, attrs):
        self._open(tag, attrs, True)

    def handle_startendtag(self, tag, attrs):
        self._open(tag, attrs, False)

    def handle_endtag(self, tag):
        if tag == "style" and self._style is not None:
            self.order.append(("style", (self._style[0], "".join(self._style[1]))))
            self._style = None
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        if self._style is not None:
            self._style[1].append(data)
            return
        self.stack[-1].kids.append(data)

    def handle_comment(self, data):
        self.comments.append((self.getpos()[0], data))


# ------------------------------------------------------------------ CSS model
class Rule:
    def __init__(self, kind, prelude, decls, ctx, sheet, line):
        self.kind, self.prelude, self.decls, self.ctx, self.sheet, self.line = kind, prelude, decls, ctx, sheet, line
        self.selectors = [s.strip() for s in _split_top(prelude, ",")] if kind == "style" else []

    def get(self, prop):
        for p, v, _ln, _imp in reversed(self.decls):
            if p == prop:
                return v
        return None


class Sheet:
    def __init__(self, path, base_dir, line0, text, inline=False):
        self.path, self.base_dir, self.line0, self.inline = path, base_dir, line0, inline
        self.rules, self.comments, self.imports, self.at_preludes = [], [], [], []
        self.layer_names = []  # cascade layers in the order this sheet first names them
        clean, comments = _strip_comments(text)
        self.comments = [(line0 + ln, body) for ln, body in comments]
        self._text = clean
        if inline:
            self.rules.append(Rule("style", "*", _decls(self, clean, 0, len(clean)), (), self, line0))
        else:
            _parse_block(self, clean, 0, len(clean), ())

    def line_at(self, pos):
        return self.line0 + self._text.count("\n", 0, pos)


def _split_top(text, sep):
    out, depth, q, cur = [], 0, None, []
    for c in text:
        if q:
            if c == q:
                q = None
        elif c in "\"'":
            q = c
        elif c in "([":
            depth += 1
        elif c in ")]":
            depth -= 1
        elif c == sep and depth == 0:
            out.append("".join(cur))
            cur = []
            continue
        cur.append(c)
    out.append("".join(cur))
    return out


def _strip_comments(text):
    comments, out, i = [], [], 0
    while True:
        j = text.find("/*", i)
        if j < 0:
            out.append(text[i:])
            break
        k = text.find("*/", j + 2)
        k = len(text) if k < 0 else k
        out.append(text[i:j])
        comments.append((text.count("\n", 0, j), text[j + 2:k]))
        out.append(re.sub(r"[^\n]", " ", text[j:k + 2]))
        i = k + 2
    return "".join(out), comments


def _match_brace(text, i, end):
    depth, q = 0, None
    while i < end:
        c = text[i]
        if q:
            if c == "\\":
                i += 2
                continue
            if c == q:
                q = None
        elif c in "\"'":
            q = c
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return end


def _decls(sheet, text, start, end):
    out, pos = [], start
    for seg in _split_top(text[start:end], ";"):
        seg_start = pos
        pos += len(seg) + 1
        if "{" in seg or ":" not in seg:
            continue
        prop, _, value = seg.partition(":")
        prop = prop.strip().lower()
        if not prop or not re.fullmatch(r"-?-?[a-z][\w-]*|--[\w-]+", prop):
            continue
        value = value.strip()
        imp = bool(re.search(r"!\s*important\s*$", value, re.I))
        value = re.sub(r"!\s*important\s*$", "", value, flags=re.I).strip()
        lead = len(seg) - len(seg.lstrip())
        out.append((prop, value, sheet.line_at(seg_start + lead), imp))
    return out


def _parse_block(sheet, text, start, end, ctx, in_keyframes=False):
    i = start
    while i < end:
        while i < end and (text[i].isspace() or text[i] == ";"):
            i += 1
        if i >= end:
            break
        j, q, paren = i, None, 0
        while j < end:
            c = text[j]
            if q:
                if c == q:
                    q = None
            elif c in "\"'":
                q = c
            elif c == "(":
                paren += 1
            elif c == ")":
                paren -= 1
            elif paren == 0 and c in "{;}":
                break
            j += 1
        prelude = text[i:j].strip()
        line = sheet.line_at(i)
        if j >= end or text[j] == "}":
            i = j + 1
            continue
        if text[j] == ";":
            if prelude.lower().startswith("@import"):
                sheet.imports.append((prelude, line))
            elif re.match(r"@layer\b", prelude, re.I):
                parent = _layer_of(ctx)
                for name in _split_top(prelude[6:], ","):
                    if name.strip():
                        sheet.layer_names.append((parent + "." if parent else "") + name.strip().lower())
            i = j + 1
            continue
        k = _match_brace(text, j, end)
        low = prelude.lower()
        if in_keyframes:
            sheet.rules.append(Rule("keyframe", prelude, _decls(sheet, text, j + 1, k), ctx, sheet, line))
        elif low.startswith("@"):
            m = re.match(r"@([-\w]+)", low)
            name = m.group(1) if m else ""
            sheet.at_preludes.append((low, line))
            if name == "layer":
                sheet.layer_names.append(_layer_of(ctx + (low,)))
            if name in ("media", "supports", "layer", "container", "document", "-moz-document", "scope"):
                _parse_block(sheet, text, j + 1, k, ctx + (low,))
            elif name.endswith("keyframes"):
                _parse_block(sheet, text, j + 1, k, ctx + (low,), in_keyframes=True)
            elif name == "font-face":
                sheet.rules.append(Rule("font-face", prelude, _decls(sheet, text, j + 1, k), ctx, sheet, line))
        else:
            sheet.rules.append(Rule("style", prelude, _decls(sheet, text, j + 1, k), ctx, sheet, line))
        i = k + 1


# ------------------------------------------------------------------ selectors and cascade
STATE_RE = re.compile(r":(hover|focus|focus-visible|focus-within|active|visited|target|checked|disabled|"
                      r"enabled|invalid|valid|placeholder-shown|indeterminate|user-invalid|autofill|open)\b")
_ATTR_RE = re.compile(r"\[\s*([\w-]+)\s*(?:([~|^$*]?=)\s*(\"[^\"]*\"|'[^']*'|[^\]\s]+)\s*[iIsS]?)?\s*\]")
_IDENT_RE = re.compile(r"(?:[\w-]|\\[0-9a-fA-F]{1,6}\s?|\\.)+")
_NAME_RE = re.compile(r"[\w-]+")
# Logical pseudo-classes resolved at rest: is/where/matches/any match when an argument matches
# (forgiving: an unparsable argument is dropped), not matches when none does (strict: an
# unparsable argument makes the whole selector unmeasured).
LOGICAL = {"is", "where", "matches", "-webkit-any", "-moz-any", "not"}


def _unescape(text):
    def one(m):
        body = m.group(0)[1:]
        if re.fullmatch(r"[0-9a-fA-F]{1,6}\s?", body):
            try:
                return chr(int(body.strip(), 16))
            except (ValueError, OverflowError):
                return ""
        return body
    return re.sub(r"\\(?:[0-9a-fA-F]{1,6}\s?|.)", one, text)


def _close(text, i, open_c, close_c):
    """Index just past the bracket closing text[i], respecting quotes and escapes; -1 when unclosed."""
    depth, q = 0, None
    while i < len(text):
        c = text[i]
        if c == "\\":
            i += 2
            continue
        if q:
            if c == q:
                q = None
        elif c in "\"'":
            q = c
        elif c == open_c:
            depth += 1
        elif c == close_c:
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return -1


def _compound(text):
    c = {"tag": None, "ids": [], "classes": [], "attrs": [], "logic": []}
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch == "*":
            i += 1
        elif ch in "#.":
            m = _IDENT_RE.match(text, i + 1)
            if not m:
                return None
            (c["ids"] if ch == "#" else c["classes"]).append(_unescape(m.group(0)))
            i = m.end()
        elif ch == "[":
            j = _close(text, i, "[", "]")
            a = _ATTR_RE.fullmatch(text[i:j]) if j > 0 else None
            if not a:
                return None
            val = a.group(3)
            if val and val[0] in "\"'":
                val = val[1:-1]
            c["attrs"].append((a.group(1).lower(), a.group(2), val))
            i = j
        elif ch == ":":
            if text.startswith("::", i):
                return None  # pseudo-elements are not the element's own text
            m = _NAME_RE.match(text, i + 1)
            if not m:
                return None
            name, i, arg = m.group(0).lower(), m.end(), None
            if i < n and text[i] == "(":
                j = _close(text, i, "(", ")")
                if j < 0:
                    return None
                arg, i = text[i + 1:j - 1], j
            if name == "root" and arg is None:
                c["tag"] = "html"
                continue
            if name not in LOGICAL or arg is None:
                return None  # state and structural pseudo-classes: not at rest / unsupported
            chains = [parse_selector(part) for part in _split_top(arg, ",")]
            if name == "not" and any(x is None for x in chains):
                return None
            chains = [x for x in chains if x]
            if not chains:
                return None
            c["logic"].append((name, chains))
        else:
            m = _IDENT_RE.match(text, i)
            if not m or i:
                return None
            c["tag"] = _unescape(m.group(0)).lower()
            i = m.end()
    return c


def parse_selector(sel):
    """[(combinator, compound), ...] left to right, or None when it does not apply at rest."""
    tokens, buf, depth, q, i = [], [], 0, None, 0
    s = (sel or "").strip()
    while i < len(s):
        c = s[i]
        if c == "\\":
            buf.append(s[i:i + 2])
            i += 2
            continue
        if q:
            q = None if c == q else q
        elif c in "\"'":
            q = c
        elif c in "([":
            depth += 1
        elif c in ")]":
            depth -= 1
        elif depth == 0 and (c.isspace() or c in ">+~"):
            if buf:
                tokens.append("".join(buf))
                buf = []
            if c in ">+~":
                tokens.append(c)
            i += 1
            continue
        buf.append(c)
        i += 1
    if buf:
        tokens.append("".join(buf))
    chain, comb = [], None
    for tok in tokens:
        if tok in (">", "+", "~"):
            comb = tok
            continue
        comp = _compound(tok)
        if comp is None:
            return None
        chain.append((comb if chain else None, comp))
        comb = " "
    return chain or None


def _spec(chain):
    a = b = t = 0
    for _, c in chain:
        a += len(c["ids"])
        b += len(c["classes"]) + len(c["attrs"])
        t += 1 if c["tag"] else 0
        for name, chains in c.get("logic", ()):
            if name == "where":
                continue
            best = max(_spec(x) for x in chains)
            a, b, t = a + best[0], b + best[1], t + best[2]
    return (a, b, t)


def _match_compound(node, c):
    if c["tag"] and node.tag != c["tag"]:
        return False
    for name, chains in c.get("logic", ()):
        if any(_matches(node, x) for x in chains) == (name == "not"):
            return False
    if any(node.attrs.get("id") != i for i in c["ids"]):
        return False
    cls = node.classes()
    if any(k not in cls for k in c["classes"]):
        return False
    for name, op, val in c["attrs"]:
        if name not in node.attrs:
            return False
        have = node.attrs[name]
        if op == "=" and have != val:
            return False
        if op == "~=" and val not in have.split():
            return False
        if op == "^=" and not have.startswith(val):
            return False
        if op == "$=" and not have.endswith(val):
            return False
        if op == "*=" and val not in have:
            return False
        if op == "|=" and not (have == val or have.startswith(val + "-")):
            return False
    return True


def _prev_siblings(node):
    if node.parent is None:
        return []
    els = node.parent.elements
    idx = els.index(node)
    return list(reversed(els[:idx]))


def _matches(node, chain, idx=None):
    idx = len(chain) - 1 if idx is None else idx
    comb, comp = chain[idx]
    if not _match_compound(node, comp):
        return False
    if idx == 0:
        return True
    if comb == " ":
        return any(_matches(p, chain, idx - 1) for p in node.ancestors())
    if comb == ">":
        p = node.parent
        return p is not None and p.tag != "#document" and _matches(p, chain, idx - 1)
    sibs = _prev_siblings(node)
    if comb == "+":
        return bool(sibs) and _matches(sibs[0], chain, idx - 1)
    return any(_matches(s, chain, idx - 1) for s in sibs)


INHERITED = {"color", "font-size", "font-weight", "font-family", "letter-spacing", "text-transform",
             "visibility", "color-scheme"}


def _layer_of(ctx):
    """Dotted cascade-layer name of a rule context, or None when the rule is unlayered."""
    names = [c[6:].strip() or "<anonymous>" for c in ctx if c.startswith("@layer")]
    return ".".join(names) if names else None


def _at_rest(ctx):
    """A rule applies at rest when every wrapper is a cascade layer (media, supports, container: variants)."""
    return all(c.startswith("@layer") for c in ctx)


def _apply_cascade(doc):
    """Winning declarations per node: importance, inline, layer order, specificity, source order.

    Normal declarations: an unlayered rule beats every layered one and a later layer beats an
    earlier one, whatever the specificity. Important declarations reverse the layer order.
    """
    entries, order, rank = [], 0, {}
    for sheet in doc.sheets:
        for name in getattr(sheet, "layer_names", ()):
            rank.setdefault(name, len(rank))
    for sheet in doc.sheets:
        if sheet.inline:
            continue
        for rule in sheet.rules:
            if rule.kind != "style" or not _at_rest(rule.ctx):
                continue
            layer = _layer_of(rule.ctx)
            if layer is not None:
                rank.setdefault(layer, len(rank))
            for sel in rule.selectors:
                chain = parse_selector(sel)
                if chain:
                    entries.append((chain, _spec(chain), rule, layer))
    top = len(rank) + 1
    for node in doc.nodes:
        won = {}
        for chain, spec, rule, layer in entries:
            if not _matches(node, chain):
                continue
            for prop, val, _ln, imp in rule.decls:
                order += 1
                if imp:
                    lk = -rank[layer] if layer is not None else -top
                else:
                    lk = rank[layer] if layer is not None else top
                key = (imp, 0, lk, spec, order)
                if prop not in won or key > won[prop][0]:
                    won[prop] = (key, val)
        style = doc.inline_sheets.get(id(node))
        if style is not None:
            for prop, val, _ln, imp in style.rules[0].decls:
                order += 1
                key = (imp, 1, 0, (0, 0, 0), order)
                if prop not in won or key > won[prop][0]:
                    won[prop] = (key, val)
        node.declared = won


def _resolve(node, value, depth=0):
    if value is None or "var(" not in value or depth > 8:
        return value

    def sub(m):
        name, fallback = m.group(1), m.group(2)
        got = computed(node, name, depth + 1)
        if got is None:
            return fallback.strip() if fallback is not None else "var(" + name + ")"
        return got
    out = re.sub(r"var\(\s*(--[\w-]+)\s*(?:,\s*([^()]*(?:\([^()]*\)[^()]*)*))?\)", sub, value)
    return out if out == value else _resolve(node, out, depth + 1)


def computed(node, prop, depth=0):
    n = node
    inherit = prop in INHERITED or prop.startswith("--")
    while n is not None and n.tag != "#document":
        got = n.declared.get(prop)
        if got is not None and got[1].lower() not in ("inherit", "unset"):
            return _resolve(n, got[1], depth)
        if not inherit:
            return None
        n = n.parent
    return None


def _own(node, *props):
    """The winning value among props declared on the node itself (resolved), or None."""
    best = None
    for p in props:
        got = node.declared.get(p)
        if got is not None and (best is None or got[0] > best[0]):
            best = (got[0], got[1])
    return _resolve(node, best[1]) if best else None


UA_EM = {"h1": 2.0, "h2": 1.5, "h3": 1.17, "h5": 0.83, "h6": 0.67, "small": 0.83}
BOLD = {"h1", "h2", "h3", "h4", "h5", "h6", "b", "strong", "th"}
KEYWORD_PX = {"xx-small": 9, "x-small": 10, "small": 13, "medium": 16, "large": 18, "x-large": 24,
              "xx-large": 32}


def length_px(value, parent_px=16.0, root_px=16.0, pick="min"):
    """A CSS length in px, or None. clamp/min/max pick their smallest (or largest) argument."""
    if value is None:
        return None
    v = value.strip().lower()
    m = re.match(r"(clamp|min|max)\((.*)\)$", v)
    if m:
        vals = [length_px(a, parent_px, root_px, pick) for a in _split_top(m.group(2), ",")]
        vals = [x for x in vals if x is not None]
        if not vals:
            return None
        return min(vals) if pick == "min" else max(vals)
    if v in KEYWORD_PX:
        return float(KEYWORD_PX[v])
    m = re.fullmatch(r"(%s)(px|rem|em|%%|pt)?" % _NUM, v)
    if not m:
        return None
    n, unit = float(m.group(1)), m.group(2)
    if unit is None:
        return n if n == 0 else None
    return {"px": n, "rem": n * root_px, "em": n * parent_px, "%": n * parent_px / 100.0,
            "pt": n * 4.0 / 3.0}[unit]


def font_px(node, root_px):
    if node is None or node.tag == "#document":
        return 16.0
    parent = font_px(node.parent, root_px)
    own = _own(node, "font-size")
    if own is not None:
        px = length_px(own, parent, root_px)
        if px is not None:
            return px
    return parent * UA_EM.get(node.tag, 1.0)


def font_weight(node):
    if node is None or node.tag == "#document":
        return 400
    own = _own(node, "font-weight")
    if own is not None:
        w = own.strip().lower()
        if w.isdigit():
            return int(w)
        if w in ("bold", "bolder"):
            return 700
        if w in ("normal", "lighter"):
            return 400
    if node.tag in BOLD:
        return 700
    return font_weight(node.parent)


# ------------------------------------------------------------------ documents and groups
INJECT_RE = re.compile(
    r"\b(?:ignore|disregard|forget)\b.{0,40}\b(?:previous|prior|above|earlier|all)\b.{0,20}\b(?:instructions?|rules|prompts?)\b"
    r"|\b(?:note|message|instructions?)\s+(?:to|for)\s+(?:the\s+)?(?:ai|assistant|agent|claude|model|llm)\b"
    r"|^\s*(?:assistant|claude|ai agent|ai|system)\s*[:,]"
    r"|\byou\s+are\s+now\b|\bsystem\s+prompt\b"
    r"|\b(?:say|report|state)\s+(?:that\s+)?(?:this|the)\s+(?:page|site|file)\s+(?:passes|is\s+(?:fine|clean))",
    re.I | re.S)


class Doc:
    def __init__(self, path, root):
        self.path, self.root = path, root
        self.sheets, self.inline_sheets, self.links = [], {}, []


class Report:
    def __init__(self):
        self.findings, self.unmeasured, self.pairs = [], [], []
        self.waived, self.invalid_ignores, self.body_text = [], [], []
        self.files = 0
        self._seen = set()
        self._unm = {}

    def add(self, rule, path, root, line, msg, sev=None):
        rel = _rel(path, root)
        key = (rule, rel, line, msg)
        if key in self._seen:
            return
        self._seen.add(key)
        self.findings.append({"rule": rule, "slug": SLUG[rule], "sev": sev or SEV[rule],
                              "file": rel, "line": line, "msg": msg, "_root": root})

    def unmeasure(self, path, root, line, reason):
        rel = _rel(path, root)
        key = (rel, reason)
        if key in self._unm:
            self._unm[key]["count"] += 1
            return
        row = {"file": rel, "line": line, "reason": reason, "count": 1}
        self._unm[key] = row
        self.unmeasured.append(row)

    def to_json(self):
        clean = [{k: v for k, v in f.items() if k != "_root"} for f in self.findings]
        return {"findings": [f for f in clean if f["sev"] != "P3"],
                "questions": [f for f in clean if f["sev"] == "P3"],
                "unmeasured": self.unmeasured, "pairs": self.pairs, "body_text": self.body_text,
                "waived": self.waived,
                "invalid_ignores": self.invalid_ignores, "files": self.files, "rules": len(RULES)}

    def blocking(self):
        return [f for f in self.findings if f["sev"] != "P3"]


def _rel(path, root):
    try:
        return os.path.relpath(path, root).replace(os.sep, "/")
    except ValueError:
        return path.replace(os.sep, "/")


def _read(path):
    with open(path, "rb") as fh:
        return fh.read().decode("utf-8", errors="replace")


def _local_target(url, base_dir, root):
    """Absolute local path for a local reference, or None when remote, inline or templated."""
    url = (url or "").strip()
    if not url or url.startswith(("#", "data:", "mailto:", "tel:", "javascript:", "//", "about:", "blob:")):
        return None
    if any(t in url for t in ("{{", "${", "<%", "{%")):
        return None
    p = urlparse(url)
    if p.scheme or p.netloc:
        return None
    path = unquote(p.path)
    if not path:
        return None
    if path.startswith("/"):
        return os.path.normpath(os.path.join(root, path.lstrip("/")))
    return os.path.normpath(os.path.join(base_dir, path))


URL_RE = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.I)


class Checker:
    def __init__(self, report):
        self.rep = report
        self.sheet_cache = {}

    # ---------------- loading
    def load_sheet(self, path, root, seen=None):
        path = os.path.normpath(path)
        if path in self.sheet_cache:
            return self.sheet_cache[path]
        sheet = Sheet(path, os.path.dirname(path), 1, _read(path))
        sheet.root = root
        self.sheet_cache[path] = sheet
        return sheet

    def sheets_with_imports(self, sheet, root, out, seen):
        if id(sheet) in seen:
            return
        seen.add(id(sheet))
        for prelude, _line in sheet.imports:
            m = URL_RE.search(prelude) or re.search(r"@import\s+(['\"])(.*?)\1", prelude)
            target = _local_target(m.group(2), sheet.base_dir, root) if m else None
            if target and os.path.isfile(target):
                self.sheets_with_imports(self.load_sheet(target, root), root, out, seen)
        out.append(sheet)

    def load_doc(self, path, root):
        b = _Builder()
        b.feed(_read(path))
        b.close()
        doc = Doc(path, root)
        doc.nodes, doc.comments, doc.tree = b.nodes, b.comments, b.root
        base = os.path.dirname(path)
        seen = set()
        for kind, item in b.order:
            if kind == "style":
                line0, text = item
                s = Sheet(path, base, line0, text)
                s.root = root
                self.sheets_with_imports(s, root, doc.sheets, seen)
            else:
                rel = item.attrs.get("rel", "").lower()
                href = item.attrs.get("href", "")
                doc.links.append(item)
                if "stylesheet" in rel:
                    target = _local_target(href, base, root)
                    if target and os.path.isfile(target):
                        self.sheets_with_imports(self.load_sheet(target, root), root, doc.sheets, seen)
        for node in doc.nodes:
            if "style" in node.attrs and node.attrs["style"].strip():
                s = Sheet(path, base, node.line, node.attrs["style"], inline=True)
                s.root = root
                s.rules[0].selectors = [node.tag + "".join("." + c for c in node.classes())]
                doc.inline_sheets[id(node)] = s
                doc.sheets.append(s)
        _apply_cascade(doc)
        return doc

    # ---------------- runs
    def run(self, roots):
        docs, css_files = [], []
        for root, files in roots:
            for f in files:
                low = f.lower()
                if low.endswith((".html", ".htm")):
                    docs.append(self.load_doc(f, root))
                elif low.endswith(".css"):
                    css_files.append((f, root))
                self.rep.files += 1
        linked = set()
        for doc in docs:
            for s in doc.sheets:
                linked.add(os.path.normpath(s.path))
        self.linked = linked
        groups = [(d.sheets, d) for d in docs]
        for f, root in css_files:
            if os.path.normpath(f) in linked:
                continue
            out = []
            self.sheets_with_imports(self.load_sheet(f, root), root, out, set())
            groups.append((out, None))
        for doc in docs:
            self.html_rules(doc)
        done = set()
        for sheets, doc in groups:
            for s in sheets:
                if id(s) not in done:
                    done.add(id(s))
                    self.sheet_rules(s)
            self.group_rules(sheets, doc)

    # ---------------- HTML rules
    def html_rules(self, doc):
        rep, p, root = self.rep, doc.path, doc.root
        base = os.path.dirname(p)
        for line, body in doc.comments:
            if INJECT_RE.search(body):
                rep.add("INJECTED", p, root, line, "HTML comment addresses an agent; reported as data, not followed")
        html = [n for n in doc.nodes if n.tag == "html"]
        if html and not html[0].attrs.get("lang", "").strip():
            rep.add("R8", p, root, html[0].line, "html element has no lang attribute")
        if html or any(n.tag == "head" for n in doc.nodes):
            if not any(n.tag == "meta" and n.attrs.get("name", "").lower() == "viewport" for n in doc.nodes):
                rep.add("R9", p, root, 1, "no <meta name=\"viewport\">")
        labels_for = {n.attrs.get("for") for n in doc.nodes if n.tag == "label" and n.attrs.get("for")}
        ids, h1s, prev_level = {}, 0, None
        for n in doc.nodes:
            a = n.attrs
            # R1 local assets
            refs = []
            if n.tag in ("img", "source", "script", "video", "audio", "iframe", "embed", "track"):
                refs += [a.get("src")]
            if n.tag in ("img", "source") and a.get("srcset"):
                refs += [part.strip().split()[0] for part in a["srcset"].split(",") if part.strip()]
            if n.tag == "video":
                refs.append(a.get("poster"))
            if n.tag == "link" and a.get("href"):
                rel = a.get("rel", "").lower()
                if not any(r in rel for r in ("preconnect", "dns-prefetch", "canonical", "alternate", "next", "prev")):
                    refs.append(a.get("href"))
            for ref in refs:
                target = _local_target(ref, base, root)
                if target and not os.path.exists(target):
                    rep.add("R1", p, root, n.line, "local asset not found: %s" % ref)
            # R4
            if n.tag == "img" and "alt" not in a and a.get("aria-hidden") != "true" \
                    and a.get("role") not in ("presentation", "none"):
                rep.add("R4", p, root, n.line, "img has no alt attribute (use alt=\"\" when decorative)")
            # R5 / R6
            if n.tag in ("input", "select", "textarea"):
                t = a.get("type", "text").lower()
                if n.tag != "input" or t not in ("hidden", "submit", "button", "reset", "image"):
                    named = (a.get("id") and a.get("id") in labels_for) or any(x.tag == "label" for x in n.ancestors()) \
                        or a.get("aria-label", "").strip() or a.get("aria-labelledby", "").strip() \
                        or a.get("title", "").strip()
                    if not named:
                        if a.get("placeholder", "").strip():
                            rep.add("R6", p, root, n.line, "%s labelled only by its placeholder" % n.tag)
                        else:
                            rep.add("R5", p, root, n.line, "%s has no label" % n.tag)
            # R7
            interactive = n.tag == "button" or (n.tag == "a" and "href" in a) or a.get("role") in ("button", "link")
            if interactive and a.get("aria-hidden") != "true" and "hidden" not in a:
                name = a.get("aria-label", "").strip() or a.get("aria-labelledby", "").strip() \
                    or a.get("title", "").strip() or n.full_text().strip() \
                    or any(x.tag == "img" and x.attrs.get("alt", "").strip() for x in _descendants(n))
                if not name:
                    rep.add("R7", p, root, n.line, "%s has no accessible name" % n.tag)
            # R10
            if re.fullmatch(r"h[1-6]", n.tag):
                level = int(n.tag[1])
                if prev_level is not None and level > prev_level + 1:
                    rep.add("R10", p, root, n.line, "heading level skipped: h%d then h%d" % (prev_level, level))
                prev_level = level
                if level == 1:
                    h1s += 1
                    if h1s == 2:
                        rep.add("R10", p, root, n.line, "more than one h1", sev="P3")
            # R13
            if a.get("id"):
                if a["id"] in ids:
                    rep.add("R13", p, root, n.line, "id \"%s\" also used on line %d" % (a["id"], ids[a["id"]]))
                else:
                    ids[a["id"]] = n.line
            # INJECTED in data-bearing attributes and text
            for attr in ("alt", "title", "aria-label", "content", "placeholder"):
                if a.get(attr) and INJECT_RE.search(a[attr]):
                    rep.add("INJECTED", p, root, n.line, "%s attribute addresses an agent; reported as data" % attr)
            if not any(x.tag in ("script", "style") for x in [n] + list(n.ancestors())):
                txt = n.direct_text()
                if txt.strip() and INJECT_RE.search(txt.strip()):
                    rep.add("INJECTED", p, root, n.line, "text addresses an agent; reported as data, not followed")
        self.contrast_rule(doc)
        self.layout_rules(doc)
        self.body_text_rule(doc)

    def body_text_rule(self, doc):
        """R20 on the document's body text, measured per element through the cascade.

        Candidates: p, li, dd and blockquote with text (innermost only). Classed out and counted:
        landmarks and roles that hold no running text (nav, header, footer, aside), captions,
        labels, tables, controls, small-print classes, anything outside <main> when the page has
        one, link-only list items, and short lines (under 25 words) set below the dominant body
        size. The dominant size is the one carrying the most body characters.
        """
        rep, p, root = self.rep, doc.path, doc.root
        html = [n for n in doc.nodes if n.tag == "html"]
        root_px = font_px(html[0], 16.0) if html else 16.0
        has_main = any(_is_main(n) for n in doc.nodes)
        cands, out = [], {}
        for n in doc.nodes:
            if n.tag not in BODY_TAGS or any(d.tag in BODY_TAGS for d in _descendants(n)):
                continue
            chain = [n] + list(n.ancestors())
            if any(x.tag in NO_TEXT or "hidden" in x.attrs or (_own(x, "display") or "").strip() == "none"
                   for x in chain):
                continue
            text = " ".join(n.full_text().split())
            if not re.search(r"\w", text):
                continue
            words = len(text.split())
            role = _body_role(n, chain, has_main)
            if not role and n.tag in ("li", "dd") and words < SHORT_ITEM_WORDS:
                role = "short list item"
            if role:
                out[role] = out.get(role, 0) + 1
                continue
            px = round(font_px(n, root_px), 2)
            reduced = words < SMALL_PRINT_WORDS and _reduced_by_class(n, px, root_px)
            cands.append((n, text, px, reduced))
        # Short lines a class or inline style sets below their surroundings are small print, unless
        # they are most of the page's text elements: then the reduced size is the body size.
        kept = sum(1 for c in cands if not c[3])
        small_ok = kept * 3 >= len(cands) - kept
        body = []
        for n, text, px, reduced in cands:
            if reduced and small_ok:
                out["small print"] = out.get("small print", 0) + 1
            else:
                body.append((n, text, px))
        weight = {}
        for _n, text, px in body:
            weight[px] = weight.get(px, 0) + len(text)
        dominant = max(weight, key=lambda k: (weight[k], k)) if weight else None
        body = [(n, px) for n, _t, px in body]
        sizes = {}
        for _n, px in body:
            sizes["%gpx" % px] = sizes.get("%gpx" % px, 0) + 1
        rep.body_text.append({"file": _rel(p, root), "measured": len(body), "dominant_px": dominant,
                              "sizes": sizes, "classed_out": dict(sorted(out.items()))})
        small = {}
        for n, px in body:
            if px < 16:
                small.setdefault(px, []).append(n)
        for px, nodes in sorted(small.items()):
            rep.add("R20", p, root, nodes[0].line, "body text at %gpx is under the 16px floor (%d of %d body "
                    "element(s), first a <%s>)" % (px, len(nodes), len(body), nodes[0].tag),
                    sev="P1" if px < 12 else "P2")

    def contrast_rule(self, doc):
        rep, p, root = self.rep, doc.path, doc.root
        html = [n for n in doc.nodes if n.tag == "html"]
        root_px = font_px(html[0], 16.0) if html else 16.0
        for n in doc.nodes:
            if n.tag in NO_TEXT or "hidden" in n.attrs:
                continue
            chain = [n] + list(n.ancestors())
            if any(x.tag in NO_TEXT or "hidden" in x.attrs or (_own(x, "display") or "").strip() == "none"
                   for x in chain):
                continue
            text = n.direct_text().strip()
            if not re.search(r"\w", text):
                continue
            fg_raw = computed(n, "color")
            fg = parse_colour(fg_raw) if fg_raw else None
            if fg_raw is None:
                rep.unmeasure(p, root, n.line, "text colour unset (browser default)")
                continue
            if fg is None:
                rep.unmeasure(p, root, n.line, "text colour unresolved")
                continue
            if fg[3] == 0:
                rep.unmeasure(p, root, n.line, "transparent text (clipped background)")
                continue
            ground, why = _ground(n)
            if ground is None:
                rep.unmeasure(p, root, n.line, why)
                continue
            if fg[3] < 1:
                fg = blend(fg, ground)
            ratio = contrast(fg, ground)
            px, weight = font_px(n, root_px), font_weight(n)
            need = floor_for(px, weight)
            rep.pairs.append({"file": _rel(p, root), "line": n.line, "fg": hexof(fg), "bg": hexof(ground),
                              "ratio": round(ratio, 2), "floor": need})
            if ratio < need:
                rep.add("R11", p, root, n.line, "%s on %s is %.2f:1, floor %.1f:1 (%gpx, weight %d)"
                        % (hexof(fg), hexof(ground), ratio, need, round(px, 2), weight))

    def layout_rules(self, doc):
        rep, p, root = self.rep, doc.path, doc.root
        flagged_measure = False
        for n in doc.nodes:
            cls = n.classes()
            # R21
            if not flagged_measure and n.tag == "p" and len(n.full_text().strip()) >= 320:
                bounded = False
                for x in [n] + list(n.ancestors()):
                    for prop in ("max-width", "width", "max-inline-size", "inline-size"):
                        v = _own(x, prop)
                        if v and re.search(r"\d", v) and "%" not in v and "vw" not in v:
                            bounded = True
                if not bounded:
                    rep.add("R21", p, root, n.line, "long running text with no max-width on it or any ancestor")
                    flagged_measure = True
            # R26
            if n.tag in ("button", "li") or (n.tag == "a" and any(x.tag == "nav" for x in n.ancestors())):
                t = n.full_text().strip()
                if t and _is_emoji(t[0]):
                    rep.add("R26", p, root, n.line, "an emoji leads this %s: is it carrying the meaning?" % n.tag)
            # R28
            if any(_card(c) for c in cls) and any(any(_card(c) for c in x.classes()) for x in n.ancestors()):
                rep.add("R28", p, root, n.line, "a card inside a card: does the nesting earn its border?")
            # R29
            if n.tag in ("h1", "h2", "h3"):
                sibs = _prev_siblings(n)
                if sibs:
                    e = sibs[0]
                    t = e.full_text().strip()
                    if t and len(t) <= 40 and len(t.split()) <= 6 and re.search(r"[A-Za-z]", t):
                        upper = (computed(e, "text-transform") or "").strip().lower() == "uppercase" or \
                            (sum(c.isalpha() for c in t) >= 2 and t.upper() == t)
                        ls = length_px(computed(e, "letter-spacing"), font_px(e, 16.0))
                        if upper and ls is not None and ls > 0:
                            rep.add("R29", p, root, e.line, "eyebrow label before the %s: does it add information?" % n.tag)

    # ---------------- per-sheet rules
    def sheet_rules(self, s):
        rep, p, root = self.rep, s.path, s.root
        for line, body in s.comments:
            if INJECT_RE.search(body):
                rep.add("INJECTED", p, root, line, "CSS comment addresses an agent; reported as data, not followed")
        for prelude, line in s.imports:
            m = URL_RE.search(prelude) or re.search(r"@import\s+(['\"])(.*?)\1", prelude)
            if m:
                target = _local_target(m.group(2), s.base_dir, root)
                if target and not os.path.exists(target):
                    rep.add("R1", p, root, line, "imported stylesheet not found: %s" % m.group(2))
        for r in s.rules:
            subjects = [_subject(sel) for sel in r.selectors]
            for prop, val, line, _imp in r.decls:
                for m in URL_RE.finditer(val):
                    target = _local_target(m.group(2), s.base_dir, root)
                    if target and not os.path.exists(target):
                        if r.kind == "font-face":
                            rep.add("R2", p, root, line, "font file missing: %s" % m.group(2))
                        else:
                            rep.add("R1", p, root, line, "local asset not found: %s" % m.group(2))
                if prop.startswith("--"):
                    if "cubic-bezier" in val:
                        self._bezier(p, root, line, val)
                    continue
                low = val.lower()
                # R15
                if prop in ("transition", "transition-property") and r.kind == "style":
                    for item in _split_top(low, ","):
                        words = item.split()
                        if words and _layout_prop(words[0]):
                            rep.add("R15", p, root, line, "transition on %s: animate transform or opacity" % words[0])
                if r.kind == "keyframe" and _layout_prop(prop):
                    rep.add("R15", p, root, line, "keyframes animate %s: animate transform or opacity" % prop)
                # R16
                if prop == "will-change" and r.kind == "style" and low not in ("auto", "") and \
                        not all(STATE_RE.search(sel) for sel in r.selectors):
                    rep.add("R16", p, root, line, "will-change at rest: set it on the state that animates")
                # R17
                if "cubic-bezier" in low:
                    self._bezier(p, root, line, low)
                # R18
                if prop in ("width", "min-width") and r.kind == "style":
                    px = _fixed_px(low)
                    if px is not None and px > 480 and not _width_covered(r, s):
                        rep.add("R18", p, root, line, "%s: %gpx with no max-width, min() cap or width media "
                                "query overflows small screens" % (prop, px))
                # R19
                if prop in ("width", "height") and r.kind == "style" and any(_interactive(sj) for sj in subjects):
                    px = length_px(low)
                    floor_v = length_px(r.get("min-" + prop) or "")
                    if px is not None and 0 < px < 24 and (floor_v is None or floor_v < 24) \
                            and not any(d[0].startswith("padding") for d in r.decls):
                        rep.add("R19", p, root, line, "interactive target %s %gpx is under 24px" % (prop, px))
                # R20 here only for a stylesheet no scanned page links; pages are measured per element
                if prop == "font-size" and r.kind == "style" and not s.inline \
                        and os.path.normpath(s.path) not in getattr(self, "linked", ()) \
                        and any(sj[0] in ("body", "p", "li") for sj in subjects):
                    px = length_px(low)
                    if px is not None and px < 16:
                        rep.add("R20", p, root, line, "body text at %gpx is under the 16px floor" % px,
                                sev="P1" if px < 12 else "P2")
                # R22
                if prop in ("background-clip", "-webkit-background-clip") and low == "text":
                    if "gradient(" in (r.get("background") or "") + (r.get("background-image") or ""):
                        rep.add("R22", p, root, line, "gradient text: does the gradient carry meaning, and is it legible?")
                # R23
                if prop in ("border-left", "border-right", "border-inline-start", "border-inline-end") \
                        and r.kind == "style" and not any(sj[0] in ("td", "th", "tr", "table", "thead", "tbody") for sj in subjects):
                    self._stripe(p, root, line, low, s)
                # R24 / R25
                if prop in ("box-shadow", "text-shadow") and low != "none":
                    self._shadow(p, root, line, low, prop, s)
                # R27
                if prop == "letter-spacing":
                    m = re.fullmatch(r"(%s)em" % _NUM, low.strip())
                    if m and float(m.group(1)) < -0.04:
                        rep.add("R27", p, root, line, "letter-spacing %s is tighter than -0.04em" % low)
                if prop == "font-size":
                    px = length_px(low, pick="max")
                    if px is not None and px > 96:
                        rep.add("R27", p, root, line, "display size %gpx is above 6rem" % px)

    def _bezier(self, p, root, line, val):
        for m in re.finditer(r"cubic-bezier\(([^)]*)\)", val):
            try:
                nums = [float(x) for x in m.group(1).split(",")]
            except ValueError:
                continue
            if len(nums) == 4 and not (0 <= nums[1] <= 1 and 0 <= nums[3] <= 1):
                self.rep.add("R17", p, root, line, "overshooting easing %s: is the bounce intended?" % m.group(0))

    def _var_colour(self, s, value):
        def sub(m):
            for rule in s.rules:
                if rule.kind == "style" and any(sel in (":root", "html") for sel in rule.selectors):
                    v = rule.get(m.group(1))
                    if v:
                        return v
            return m.group(0)
        return re.sub(r"var\(\s*(--[\w-]+)\s*(?:,[^)]*)?\)", sub, value)

    def _stripe(self, p, root, line, val, s):
        val = self._var_colour(s, val)
        widths = [length_px(t) for t in val.split()]
        widths = [w for w in widths if w is not None]
        width = widths[0] if widths else (3.0 if "medium" in val else 5.0 if "thick" in val else None)
        cols = colours_in(val)
        if width and width > 1 and cols and saturated(cols[0]) and cols[0][3] > 0:
            self.rep.add("R23", p, root, line, "%gpx coloured side stripe: does it mark a real state?" % width)

    def _shadow(self, p, root, line, val, prop, s):
        val = self._var_colour(s, val)
        for layer in _split_top(val, ","):
            if "inset" in layer.split():
                continue
            body = re.sub(r"(?:rgba?|hsla?)\([^)]*\)|#[0-9a-fA-F]{3,8}\b", " ", layer)
            lens = [length_px(t) for t in body.split() if re.match(r"-?[\d.]", t)]
            if len(lens) < 2 or any(x is None for x in lens):
                continue
            cols = colours_in(layer)
            blur = lens[2] if len(lens) >= 3 else 0.0
            if lens[0] == 0 and lens[1] == 0 and blur > 0 and cols and saturated(cols[0]):
                self.rep.add("R24", p, root, line, "zero-offset coloured glow (%s): is light really coming from inside?" % prop)
            elif (lens[0] != 0 or lens[1] != 0) and blur == 0 and prop == "box-shadow":
                self.rep.add("R25", p, root, line, "hard offset shadow with no blur: is that the chosen style?")

    # ---------------- per-group rules
    def group_rules(self, sheets, doc):
        rep = self.rep
        style_rules = [r for s in sheets for r in s.rules if r.kind == "style" and not s.inline]
        if not sheets:
            return
        first = sheets[0]
        loc_path = doc.path if doc else first.path
        root = doc.root if doc else first.root
        # R3
        families = set()
        for s in sheets:
            for r in s.rules:
                if r.kind == "font-face" and r.get("font-family"):
                    families.add(_family(r.get("font-family")))
            for prelude, _ln in s.imports:
                families |= _google_families(prelude)
        if doc:
            for link in doc.links:
                families |= _google_families(link.attrs.get("href", ""))
        for s in sheets:
            for r in s.rules:
                if r.kind != "style":
                    continue
                v = r.get("font-family")
                if not v or v.strip().lower().startswith(("var(", "inherit", "initial", "unset")):
                    continue
                first_family = _family(_split_top(v, ",")[0])
                if first_family and first_family not in families and first_family not in SYSTEM_FONTS:
                    line = next(ln for pr, vv, ln, _i in r.decls if pr == "font-family")
                    rep.add("R3", s.path, s.root, line, "font \"%s\" has no @font-face or font link" % first_family)
        # R12
        fv_styled = any(":focus-visible" in sel and ":not(:focus-visible)" not in sel and
                        any(_focus_style(pr, vv) for pr, vv, _l, _i in r.decls)
                        for r in style_rules for sel in r.selectors)
        for s in sheets:
            for r in s.rules:
                if r.kind != "style":
                    continue
                for prop, val, line, _imp in r.decls:
                    v = val.strip().lower()
                    removed = (prop == "outline" and v in ("none", "0", "0px", "0 none")) or \
                        (prop == "outline-style" and v == "none") or (prop == "outline-width" and v in ("0", "0px"))
                    if not removed or any(":not(:focus-visible)" in sel for sel in r.selectors):
                        continue
                    replaced = any(_focus_style(pr, vv) for pr, vv, _l, _i in r.decls if pr != prop)
                    if not replaced and not fv_styled:
                        rep.add("R12", s.path, s.root, line, "focus outline removed with no replacement or :focus-visible style")
        # R14
        motion = None
        reduced = False
        for s in sheets:
            if any("prefers-reduced-motion" in pr for pr, _ln in s.at_preludes):
                reduced = True
            for r in s.rules:
                if r.kind == "keyframe" and motion is None:
                    motion = (s, r.line)
                for prop, val, line, _imp in r.decls:
                    if prop in ("animation", "animation-name", "transition", "transition-property") and \
                            val.strip().lower() not in ("none", "0s", "all 0s", "unset", "initial") and motion is None \
                            and not any("prefers-reduced-motion" in c for c in r.ctx):
                        motion = (s, line)
        if motion and not reduced:
            rep.add("R14", motion[0].path, motion[0].root, motion[1], "motion with no prefers-reduced-motion block")
        # R30
        literal = set()
        for s in sheets:
            for r in s.rules:
                for prop, val, _l, _i in r.decls:
                    if not prop.startswith("--"):
                        literal |= {c[:3] + (c[3],) for c in colours_in(val) if c[3] > 0}
        if len(literal) > 12:
            rep.add("R30", loc_path, root, 1, "%d distinct literal colours: are they a system or an accident?" % len(literal))
        # R31
        if style_rules:
            sels = [sel for r in style_rules for sel in r.selectors]
            missing = []
            if not any("::selection" in sel for sel in sels):
                missing.append("::selection")
            if not any(":focus-visible" in sel and ":not(:focus-visible)" not in sel for sel in sels):
                missing.append(":focus-visible")
            if missing:
                rep.add("R31", loc_path, root, 1, "browser-default surfaces left unthemed: %s" % ", ".join(missing))


SYSTEM_FONTS = {
    "serif", "sans-serif", "monospace", "cursive", "fantasy", "system-ui", "ui-serif", "ui-sans-serif",
    "ui-monospace", "ui-rounded", "emoji", "math", "fangsong", "-apple-system", "blinkmacsystemfont",
    "segoe ui", "roboto", "helvetica neue", "helvetica", "arial", "georgia", "times new roman", "times",
    "verdana", "tahoma", "trebuchet ms", "courier new", "courier", "consolas", "menlo", "monaco",
    "sf mono", "sf pro text", "sf pro display", "lucida grande", "lucida console", "noto sans",
    "noto serif", "liberation mono", "dejavu sans", "dejavu sans mono", "cambria", "calibri",
    "palatino", "garamond", "segoe ui emoji", "apple color emoji", "noto color emoji",
    "segoe ui symbol", "cascadia code", "cascadia mono", "ubuntu", "cantarell", "oxygen",
}


def _family(text):
    return (text or "").strip().strip("\"'").strip().lower()


def _google_families(text):
    if "fonts.googleapis.com" not in (text or ""):
        return set()
    m = URL_RE.search(text)
    url = m.group(2) if m else re.sub(r"^@import\s+", "", text).strip("\"' ;")
    q = parse_qs(urlparse(url).query)
    out = set()
    for fam in q.get("family", []):
        for part in fam.split("|"):
            out.add(part.split(":")[0].replace("+", " ").strip().lower())
    return out


def _focus_style(prop, val):
    v = val.strip().lower()
    if prop in ("box-shadow", "border", "border-color", "border-bottom", "text-decoration", "background",
                "background-color") and v not in ("none", "0", "transparent"):
        return True
    return prop in ("outline", "outline-style", "outline-color", "outline-width") and v not in ("none", "0", "0px")


BODY_TAGS = {"p", "li", "dd", "blockquote"}
OUT_TAGS = {"nav": "nav", "header": "header", "footer": "footer", "aside": "aside", "figcaption": "caption",
            "caption": "caption", "label": "label", "legend": "label", "small": "small print",
            "button": "control", "summary": "control", "select": "control", "table": "table", "form": "form"}
OUT_ROLES = {"navigation": "nav", "menu": "nav", "menubar": "nav", "tablist": "nav", "banner": "header",
             "contentinfo": "footer", "complementary": "aside", "toolbar": "control", "dialog": "dialog"}
SMALL_CLASS_RE = re.compile(r"(^|[-_])(captions?|footnotes?|fine-?print|small|legal|disclaimer|meta|byline|"
                            r"labels?|badges?|chips?|eyebrow|kicker|breadcrumbs?|copyright|credits?)([-_]|$)", re.I)


SHORT_ITEM_WORDS = 10   # a list item under this is a label (names, tags, figures), not running text
SMALL_PRINT_WORDS = 40  # a reduced line at or over this is a paragraph, measured as body text


def _reduced_by_class(node, px, root_px):
    """True when the node's own font-size comes from a class, id, attribute or inline style and sets
    it below the size it would inherit (a deliberate small-print line, not a tag-wide body size)."""
    got = node.declared.get("font-size")
    if got is None:
        return False
    key = got[0]
    inline, spec = key[1] == 1, key[3]
    return bool(inline or spec[0] or spec[1]) and px < font_px(node.parent, root_px) - 0.25


def _is_main(node):
    return node.tag == "main" or node.attrs.get("role", "").lower() == "main"


def _body_role(node, chain, has_main):
    """Why a text element is not body text, or None when it is."""
    for x in chain:
        if x.tag in OUT_TAGS:
            return OUT_TAGS[x.tag]
        role = x.attrs.get("role", "").lower()
        if role in OUT_ROLES:
            return OUT_ROLES[role]
    if any(SMALL_CLASS_RE.search(c) for x in chain for c in x.classes()):
        return "small print"
    if has_main and not any(_is_main(x) for x in chain):
        return "outside main"
    els = node.elements
    if not node.direct_text().strip() and len(els) == 1 and els[0].tag in ("a", "button"):
        return "link only"
    return None


def _fixed_px(value):
    """A width in px for R18, or None when relative or capped (min() with a relative argument)."""
    v = (value or "").strip().lower()
    m = re.match(r"min\((.*)\)$", v)
    if m and any(re.search(r"%|vw|vi\b|vmin|cq|auto|fit-content|max-content|stretch", a)
                 for a in _split_top(m.group(1), ",")):
        return None
    return length_px(v)


def _width_covered(rule, sheet):
    """True when a max-width or a width media query keeps a wide fixed width off small screens."""
    if rule.get("max-width") is not None or rule.get("max-inline-size") is not None:
        return True
    if any(c.startswith("@media") and "width" in c for c in rule.ctx):
        return True
    sels = set(rule.selectors)
    for other in sheet.rules:
        if other is rule or other.kind != "style" or not sels & set(other.selectors):
            continue
        if other.get("max-width") is not None or other.get("max-inline-size") is not None:
            return True
        narrow = any(c.startswith("@media") and ("max-width" in c or "width <" in c) for c in other.ctx)
        if narrow and (other.get("width") is not None or other.get("min-width") is not None):
            return True
    return False


def _layout_prop(name):
    return name in ("width", "height", "top", "left", "right", "bottom", "inset", "min-width", "max-width",
                    "min-height", "max-height") or name.startswith(("margin", "padding"))


def _subject(sel):
    """(tag, classes, attrs-text) of a selector's last compound, from the raw text."""
    last = re.split(r"[\s>+~]+", sel.strip())[-1] if sel.strip() else ""
    tag = re.match(r"[a-zA-Z][\w-]*", last)
    return (tag.group(0).lower() if tag else "", re.findall(r"\.([\w-]+)", last), last)


def _interactive(sj):
    tag, classes, raw = sj
    if "checkbox" in raw or "radio" in raw:
        return False
    if tag in ("a", "button", "input", "select", "textarea", "summary"):
        return True
    if re.search(r"role\s*=\s*['\"]?(button|link|tab|switch|menuitem)", raw):
        return True
    return any(re.search(r"(^|[-_])(btn|button|toggle|chip)([-_]|$)", c) for c in classes)


def _card(cls):
    return re.search(r"(^|[-_])card$", cls) is not None


def _is_emoji(ch):
    cp = ord(ch)
    return 0x1F000 <= cp <= 0x1FAFF or 0x2600 <= cp <= 0x27BF or 0x2300 <= cp <= 0x23FF or \
        0x2B00 <= cp <= 0x2BFF or cp in (0x3030, 0x303D, 0x3297, 0x3299)


def _descendants(node):
    for k in node.elements:
        yield k
        yield from _descendants(k)


def _ground(node):
    layers = []
    for x in [node] + list(node.ancestors()):
        val = _own(x, "background-color", "background")
        if not val:
            continue
        low = val.lower()
        if "gradient(" in low or "url(" in low:
            return None, "image or gradient ground"
        fn = re.search(r"\b(color-mix|light-dark|color|oklch|oklab|lch|lab|hwb)\(", low)
        if fn or re.search(r"\b(?:rgba?|hsla?)\(\s*from\b", low):
            return None, "ground colour unresolved (%s)" % (fn.group(1) if fn else "relative colour")
        cols = colours_in(low) if not parse_colour(low) else [parse_colour(low)]
        if not cols:
            if low.strip() in ("none", "transparent", "initial", "unset", "inherit"):
                continue
            return None, "ground colour unresolved"
        c = cols[0]
        if c[3] >= 1:
            base = c
            for layer in reversed(layers):
                base = blend(layer, base)
            return base, None
        if c[3] > 0:
            layers.append(c)
    return None, "no painted ground"


# ------------------------------------------------------------------ waivers, entry points
def _load_ignores(path, report):
    rows = []
    if not path or not os.path.isfile(path):
        return rows
    for i, raw in enumerate(_read(path).splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 2)
        if len(parts) < 3 or not parts[2].strip():
            report.invalid_ignores.append("line %d: %s (no reason; not applied)" % (i, line))
            continue
        rows.append((parts[0].upper(), parts[1], parts[2].strip()))
    return rows


def _collect(paths):
    roots = []
    for raw in paths:
        p = os.path.abspath(raw)
        if os.path.isdir(p):
            files = []
            for dirpath, dirnames, filenames in os.walk(p):
                dirnames[:] = sorted(d for d in dirnames if d not in (".git", "node_modules", "__pycache__"))
                for f in sorted(filenames):
                    if f.lower().endswith((".html", ".htm", ".css")):
                        files.append(os.path.join(dirpath, f))
            roots.append((p, files))
        elif os.path.isfile(p):
            roots.append((os.path.dirname(p), [p]))
        else:
            raise FileNotFoundError(raw)
    return roots


def check(paths, ignore=None):
    """Scan paths (folders or files); returns a Report. Raises FileNotFoundError on a missing path."""
    rep = Report()
    roots = _collect(paths)
    Checker(rep).run(roots)
    waivers = {}
    for root, _files in roots:
        rows = _load_ignores(os.path.join(root, ".ui-check-ignore"), rep)
        if ignore:
            rows += _load_ignores(ignore, rep)
        waivers[root] = rows
    kept = []
    for f in rep.findings:
        hit = next((w for w in waivers.get(f["_root"], []) if w[0] == f["rule"] and fnmatch.fnmatch(f["file"], w[1])), None)
        if hit:
            rep.waived.append({"rule": f["rule"], "file": f["file"], "line": f["line"], "reason": hit[2]})
        else:
            kept.append(f)
    order = {r[0]: i for i, r in enumerate(RULES)}
    kept.sort(key=lambda f: (f["sev"], order.get(f["rule"], -1), f["file"], f["line"]))
    rep.findings = kept
    return rep


def _text(rep):
    out = ["ui_check: %d file(s), %d rules" % (rep.files, len(RULES))]
    rows = rep.blocking()
    qs = [f for f in rep.findings if f["sev"] == "P3"]
    for f in rows:
        out.append("%s  %-8s %-24s %s:%d  %s" % (f["sev"], f["rule"], f["slug"], f["file"], f["line"], f["msg"]))
    if qs:
        out.append("questions (P3, never block):")
        for f in qs:
            out.append("%s  %-8s %-24s %s:%d  %s" % (f["sev"], f["rule"], f["slug"], f["file"], f["line"], f["msg"]))
    if rep.unmeasured:
        out.append("unmeasured (not failures):")
        for u in rep.unmeasured:
            out.append("  %s:%d  %s (x%d)" % (u["file"], u["line"], u["reason"], u["count"]))
    if rep.body_text:
        out.append("body text (what R20 measured; the rest was classed out):")
        for b in rep.body_text:
            dom = "%gpx" % b["dominant_px"] if b["dominant_px"] is not None else "none"
            sizes = ", ".join("%s x%d" % kv for kv in b["sizes"].items()) or "none"
            gone = ", ".join("%s %d" % kv for kv in b["classed_out"].items()) or "none"
            out.append("  %s: %d measured, dominant %s (%s); classed out: %s"
                       % (b["file"], b["measured"], dom, sizes, gone))
    for w in rep.waived:
        out.append("waived  %s %s:%d  %s" % (w["rule"], w["file"], w["line"], w["reason"]))
    for bad in rep.invalid_ignores:
        out.append("invalid ignore %s" % bad)
    counts = {}
    for f in rows:
        counts[f["sev"]] = counts.get(f["sev"], 0) + 1
    summary = ", ".join("%s %d" % (k, counts[k]) for k in sorted(counts))
    out.append("result: %s; %d question(s), %d unmeasured, %d waived"
               % ("FINDINGS (%s)" % summary if rows else "CLEAN", len(qs), len(rep.unmeasured), len(rep.waived)))
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Neutral UI floor on built HTML and CSS (static, stdlib only).")
    ap.add_argument("paths", nargs="*", help="built output folders or files")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--ignore", help="waiver file (RULE GLOB REASON per line)")
    ap.add_argument("--list-rules", action="store_true", help="print the 31 rules and exit")
    args = ap.parse_args(argv)
    if args.list_rules:
        for rid, slug, sev, summary in RULES:
            print("%-4s %s  %-24s %s" % (rid, sev, slug, summary))
        return 0
    if not args.paths:
        ap.print_usage(sys.stderr)
        return 2
    try:
        rep = check(args.paths, args.ignore)
    except (FileNotFoundError, OSError) as exc:
        print("ui_check: error: cannot read %s" % exc, file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(rep.to_json(), indent=2))
    else:
        print(_text(rep))
    return 1 if rep.blocking() else 0


if __name__ == "__main__":
    sys.exit(main())
