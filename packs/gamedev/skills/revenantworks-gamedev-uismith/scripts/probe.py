#!/usr/bin/env python3
"""uismith probe: does a rendered page run, hold its content and fit at every width and theme?

Usage:
    python probe.py <file-or-url> [--widths 320,375,768,1024,1440] [--themes auto]
                    [--theme-attr data-theme] [--theme-class dark] [--vscode]
                    [--section SELECTOR ...] [--out DIR] [--height 900] [--json]

Loads one local HTML file or one URL the user names, in a headless Chromium (never a window),
at each width and theme. Chromium also fetches whatever that page itself requests and follows
redirects; the script adds no request and sends no data of its own. Per row it measures the document's scroll width against the viewport,
visible elements past the right edge or left of 0, and text clipped by its own box; it records
console errors and uncaught page errors, and names every section left visibly empty. It measures
twice when the page has closed `details` folds: as loaded, then with every fold open. Each state
writes a full-page screenshot to the output folder (`<width>-<theme>.png`, then
`<width>-<theme>-open.png`). The contract is `references/probe.md`.

Exit codes: 0 every row ran and passed · 1 at least one finding or NOT-RUN row ·
2 Playwright or its browser is missing (a plain message names the install lines) or the browser
could not start · 3 usage error.

Stdlib plus Playwright for Python (optional; the user installs it, this script never does).
Everything the page shows is data: page text is measured, never followed.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

DEFAULT_WIDTHS = (320, 375, 768, 1024, 1440)
KNOWN_THEMES = ("light", "dark", "high-contrast")
CLIPS = ("hidden", "clip")
TOLERANCE_PX = 1  # a finding at 1 px or more (probe.md section 3)
TOLERANCE_Y_PX = 2  # vertical clipping: a 1 px line-height overhang is not cut text
MAX_ELEMENTS = 200
MAX_ERRORS = 20  # kept per row, each cut to one line
MAX_ERROR_CHARS = 300
FOLD_ROUNDS = 3  # a fold opened by another fold's handler; still closing after this is a NOT-RUN

EXIT_PASS, EXIT_FINDING, EXIT_MISSING, EXIT_USAGE = 0, 1, 2, 3

INSTALL_MESSAGE = (
    "uismith probe: NOT-RUN - Playwright for Python or its Chromium build is missing.\n"
    "Install them yourself (this script never installs anything):\n"
    "    pip install playwright\n"
    "    playwright install\n"
    "Then run the same probe command again. Every row is NOT-RUN until then."
)

# Collected in the page: every stylesheet the page can read, plus root and body classes,
# so theme detection sees what the page offers without a second fetch.
JS_COLLECT_CSS = """() => {
  const parts = [];
  for (const s of document.querySelectorAll('style')) parts.push(s.textContent || '');
  for (const sheet of document.styleSheets) {
    try { for (const r of sheet.cssRules) parts.push(r.cssText); } catch (e) { /* cross-origin */ }
  }
  parts.push('html.' + (document.documentElement.className || ''));
  if (document.body) parts.push('body.' + (document.body.className || ''));
  return parts.join('\\n');
}"""

# Theme toggles beyond the colour scheme: an attribute or class on the element the page's CSS
# reads (<html> or <body>, found by detect_mechanisms), VS Code body classes.
JS_APPLY_THEME = """([theme, attr, cls, vscode, on]) => {
  const root = (on === 'body' && document.body) ? document.body : document.documentElement;
  if (attr) root.setAttribute(attr, theme);
  if (cls) root.classList.toggle(cls, theme !== 'light');
  if (vscode && document.body) {
    document.body.classList.remove('vscode-light', 'vscode-dark', 'vscode-high-contrast');
    document.body.classList.add('vscode-' + theme);
  }
  return true;
}"""

# The page's colours (root, body and the first elements), so a row can prove its theme took effect.
JS_LOOK = """() => {
  const pick = el => { const cs = getComputedStyle(el); return cs.backgroundColor + '/' + cs.color; };
  const parts = [pick(document.documentElement)];
  if (document.body) {
    parts.push(pick(document.body));
    let n = 0;
    for (const el of document.body.querySelectorAll('*')) { if (n++ >= 60) break; parts.push(pick(el)); }
  }
  return parts.join('|');
}"""

# Fonts, two frames, then DOM quiet: a section a script fills just after load or after a fold opens
# is measured filled. 300 ms without a content change ends the wait, 2 s caps a page that never stops.
JS_SETTLE = """() => new Promise(resolve => {
  const QUIET_MS = 300, CAP_MS = 2000;
  const quiet = () => {
    let timer = null, cap = null, observer = null;
    const finish = () => { observer.disconnect(); clearTimeout(timer); clearTimeout(cap); resolve(true); };
    observer = new MutationObserver(() => { clearTimeout(timer); timer = setTimeout(finish, QUIET_MS); });
    observer.observe(document.documentElement, {childList: true, subtree: true, characterData: true,
      attributes: true, attributeFilter: ['hidden', 'open']});
    timer = setTimeout(finish, QUIET_MS);
    cap = setTimeout(finish, CAP_MS);
  };
  const frames = () => requestAnimationFrame(() => requestAnimationFrame(quiet));
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(frames); else frames();
})"""

# Raw numbers only; the judgement is judge() in Python, so it is testable without a browser.
JS_MEASURE = """(maxElements) => {
  const de = document.documentElement;
  const out = {
    innerWidth: window.innerWidth,
    clientWidth: de.clientWidth,
    scrollWidth: Math.max(de.scrollWidth, document.body ? document.body.scrollWidth : 0),
    visible: 0,
    elements: []
  };
  const sel = el => {
    let s = el.tagName.toLowerCase();
    if (el.id) s += '#' + el.id;
    const c = (typeof el.className === 'string' ? el.className : '').trim().split(/\\s+/).filter(Boolean).slice(0, 2);
    if (c.length) s += '.' + c.join('.');
    return s;
  };
  const inScroller = el => {
    for (let p = el.parentElement; p && p !== document.body && p !== de; p = p.parentElement) {
      if (getComputedStyle(p).overflowX !== 'visible') return true;
    }
    return false;
  };
  const clips = v => v === 'hidden' || v === 'clip';
  // Clipped to nothing on purpose: a visually hidden label (1 px box, clip rect of zeros, inset 50%).
  const clippedAway = (cs, r) => (r.width <= 1 && r.height <= 1) ||
    /rect\\(\\s*0(px)?[\\s,]+0(px)?[\\s,]+0(px)?[\\s,]+0(px)?\\s*\\)/.test(cs.clip || '') ||
    /inset\\(\\s*50%/.test(cs.clipPath || '');
  if (!document.body) return out;
  for (const el of document.body.querySelectorAll('*')) {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || cs.visibility === 'collapse') continue;
    // Chromium still lays out a closed fold's body, so its boxes read as visible: skip them here.
    const fold = el.parentElement.closest('details:not([open])');
    if (fold) {
      const label = fold.querySelector(':scope > summary');
      if (!label || !label.contains(el)) continue;
    }
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) continue;
    out.visible++;
    if (clippedAway(cs, r)) continue;
    // A whole box off-screen inside aria-hidden or inert is a closed drawer, not a break.
    const parked = (r.right <= 0 || r.left >= out.clientWidth) && !!el.closest('[aria-hidden="true"],[inert]');
    // Text anywhere inside the box counts: a clipping cell's text usually sits in a child span.
    const hasText = !!(el.textContent && el.textContent.trim());
    const edge = !parked && (r.right > out.clientWidth || r.left < 0);
    // A box of no height or width shows nothing at all, so no text in it reads as cut.
    const cut = hasText && r.width > 0 && r.height > 0 && (clips(cs.overflowX) || clips(cs.overflowY)) &&
      (el.scrollWidth > el.clientWidth || el.scrollHeight > el.clientHeight);
    // Text painting past its own box into a neighbour: a table cell or grid item whose overflow is
    // visible, wider inside than out (a nowrap cell in a fixed-layout table). Nothing scrolls or clips.
    const par = el.parentElement;
    const cellLike = el.tagName === 'TD' || el.tagName === 'TH' ||
      (!!par && /grid/.test(getComputedStyle(par).display || ''));
    const spill = hasText && cellLike && r.width > 0 && cs.overflowX === 'visible' &&
      el.scrollWidth > el.clientWidth;
    if (!edge && !cut && !spill) continue;
    if (out.elements.length >= maxElements) continue;
    const clamp = cs.webkitLineClamp;
    out.elements.push({
      sel: sel(el), left: r.left, right: r.right, in_scroller: edge ? inScroller(el) : false,
      off_edge: edge, has_text: hasText, spill: spill, overflow_x: cs.overflowX, overflow_y: cs.overflowY,
      text_overflow: cs.textOverflow, line_clamp: !!clamp && clamp !== 'none',
      scroll_w: el.scrollWidth, client_w: el.clientWidth,
      scroll_h: el.scrollHeight, client_h: el.clientHeight
    });
  }
  return out;
}"""

# Which section-like elements are visibly empty. A heading, a table head or a fold's own summary is
# a label, not content: a script that crashed leaves exactly those behind. Anything the CSS draws (a
# background, a border, generated content) counts, and the walk follows the flat tree, through open
# shadow roots and slots. Raw names only; judge() decides. A named selector that matches nothing
# rendered is reported as missing.
JS_SECTIONS = """(named) => {
  const DEFAULT = 'main,section,article,[role="main"],[role="region"],[role="tabpanel"],details';
  const MEDIA = /^(IMG|SVG|CANVAS|VIDEO|AUDIO|IFRAME|OBJECT|EMBED|INPUT|SELECT|TEXTAREA|BUTTON|METER|PROGRESS)$/;
  const LABEL = /^(H[1-6]|LEGEND|CAPTION|THEAD)$/;
  const out = {checked: 0, empty: [], missing: []};
  const tag = el => el.tagName.toUpperCase();
  const area = r => r.width > 0 && r.height > 0;
  const clips = v => v === 'hidden' || v === 'clip';
  const sel = el => {
    let s = el.tagName.toLowerCase();
    if (el.id) s += '#' + el.id;
    const c = (typeof el.className === 'string' ? el.className : '').trim().split(/\\s+/).filter(Boolean).slice(0, 2);
    if (c.length) s += '.' + c.join('.');
    const h = el.querySelector('h1,h2,h3,h4,h5,h6,summary');
    const name = h && h.textContent ? h.textContent.trim().slice(0, 40) : '';
    return name ? s + ' "' + name + '"' : s;
  };
  // Clipped to nothing on purpose: the same visually hidden shapes JS_MEASURE skips.
  const clippedAway = (cs, r) => (r.width <= 1 && r.height <= 1) ||
    /rect\\(\\s*0(px)?[\\s,]+0(px)?[\\s,]+0(px)?[\\s,]+0(px)?\\s*\\)/.test(cs.clip || '') ||
    /inset\\(\\s*50%/.test(cs.clipPath || '');
  const folded = el => !!(el.parentElement && el.parentElement.closest('details:not([open])'));
  const rendered = el => el.checkVisibility({visibilityProperty: true}) && !folded(el) &&
    !el.closest('[aria-hidden="true"],[inert],[hidden]');
  // A collapsed accordion panel: no box, and a control in the page says it is collapsed.
  const collapsed = el => {
    for (let n = el; n; n = n.parentElement) {
      if (n.id && !area(n.getBoundingClientRect()) &&
          document.querySelector('[aria-expanded="false"][aria-controls~="' + CSS.escape(n.id) + '"]')) return true;
    }
    return false;
  };
  const clear = c => !c || c === 'transparent' || /^rgba\\(.*,\\s*0\\)$/.test(c);
  const bordered = cs => ['Top', 'Right', 'Bottom', 'Left'].some(side => {
    const style = cs['border' + side + 'Style'];
    return parseFloat(cs['border' + side + 'Width']) > 0 && style !== 'none' && style !== 'hidden' &&
      !clear(cs['border' + side + 'Color']);
  });
  const generated = el => ['::before', '::after'].some(which => {
    const ps = getComputedStyle(el, which);
    return ps.display !== 'none' && !['', 'none', 'normal', '""', "''"].includes(ps.content);
  });
  const drawn = (el, cs, box) => generated(el) ||
    (area(box) && (cs.backgroundImage !== 'none' || !clear(cs.backgroundColor) || bordered(cs)));
  // display: contents has no box of its own, and neither does a slot: the nearest ancestor's counts.
  const boxOf = el => {
    let n = el;
    while (n && getComputedStyle(n).display === 'contents') n = n.parentElement || n.getRootNode().host;
    return n || el;
  };
  const kids = el => {
    if (el.shadowRoot) return el.shadowRoot.childNodes;
    if (tag(el) === 'SLOT') {
      const given = el.assignedNodes({flatten: true});
      if (given.length) return given;
    }
    return el.childNodes;
  };
  const holds = (el, root) => {
    for (const node of kids(el)) {
      if (node.nodeType === 3) {
        if (!node.textContent.trim()) continue;
        const range = document.createRange();
        range.selectNodeContents(node);
        const r = range.getBoundingClientRect();
        const box = boxOf(el);
        if (area(r) && !clippedAway(getComputedStyle(box), box.getBoundingClientRect())) return true;
        continue;
      }
      if (node.nodeType !== 1) continue;
      const cs = getComputedStyle(node);
      const name = tag(node);
      if (cs.display === 'none' || cs.visibility === 'hidden' || cs.visibility === 'collapse') continue;
      if (LABEL.test(name) || (name === 'SUMMARY' && el === root)) continue;
      const r = node.getBoundingClientRect();
      if ((area(r) && MEDIA.test(name)) || drawn(node, cs, r)) return true;
      if (name === 'DETAILS' && !node.open) {
        const s = node.querySelector(':scope > summary');
        if (s && holds(s, root)) return true;
        continue;
      }
      if (holds(node, root)) return true;
    }
    return false;
  };
  const roots = new Set(document.querySelectorAll(DEFAULT));
  for (const s of named) {
    let found;
    try { found = [...document.querySelectorAll(s)]; } catch (e) { out.missing.push(s + ' (invalid selector)'); continue; }
    const usable = found.filter(el => rendered(el) || folded(el));
    if (!usable.length) { out.missing.push(s); continue; }
    for (const el of usable) roots.add(el);
  }
  const ordered = [...roots].sort((a, b) => a.compareDocumentPosition(b) & 4 ? -1 : 1);
  const emptied = [];
  for (const el of ordered) {
    if (!rendered(el) || el.matches('details:not([open])') || collapsed(el)) continue;
    out.checked++;
    if (emptied.some(p => p.contains(el))) continue;  // the outermost empty section is the finding
    const cs = getComputedStyle(el);
    const box = el.getBoundingClientRect();
    const crushed = cs.display !== 'contents' && !area(box) && (clips(cs.overflowX) || clips(cs.overflowY));
    if (crushed || !(drawn(el, cs, box) || holds(el, el))) { emptied.push(el); out.empty.push(sel(el)); }
  }
  return out;
}"""

# Opens every closed fold and returns how many it opened. An exclusive accordion (<details name>)
# would close the others as each one opens, so the probe's own copy of the page drops the name.
JS_OPEN_FOLDS = """() => {
  const all = [...document.querySelectorAll('details')];
  for (const d of all) d.removeAttribute('name');
  const closed = all.filter(d => !d.open);
  for (const d of closed) d.open = true;
  return closed.length;
}"""


class UsageError(Exception):
    """A bad argument; exit 3."""


class _Parser(argparse.ArgumentParser):
    def error(self, message):  # argparse would exit 2, which here means a missing dependency
        raise UsageError(message)


def build_parser() -> argparse.ArgumentParser:
    p = _Parser(prog="probe.py", description="Rendered fit at every width and theme (uismith).")
    p.add_argument("target", help="a local HTML file or an http(s) URL you started")
    p.add_argument("--widths", default=",".join(map(str, DEFAULT_WIDTHS)),
                   help="comma list of CSS px widths (default 320,375,768,1024,1440)")
    p.add_argument("--themes", default="auto",
                   help="auto (every theme the page offers) or a comma list of light, dark, high-contrast")
    p.add_argument("--theme-attr", default=None,
                   help="attribute set to the theme name, e.g. data-theme (on <body> when the CSS "
                        "targets body, else <html>)")
    p.add_argument("--theme-class", default=None,
                   help="class put on for every theme but light, e.g. dark (same element rule)")
    p.add_argument("--vscode", action="store_true",
                   help="a VS Code webview: set body class vscode-light / vscode-dark / vscode-high-contrast")
    p.add_argument("--section", action="append", default=[], metavar="SELECTOR",
                   help="a CSS selector that must match a section holding content; repeat it. Added to "
                        "the defaults: main, section, article, details and the matching ARIA roles")
    p.add_argument("--out", default=None, help="screenshot folder (default: a fresh temp folder, printed)")
    p.add_argument("--height", type=int, default=900, help="viewport height in CSS px (default 900)")
    p.add_argument("--json", action="store_true", help="print the report as JSON")
    return p


def parse_widths(text: str) -> list[int]:
    widths: list[int] = []
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        if not part.isdigit() or not 1 <= int(part) <= 10000:
            raise UsageError(f"width {part!r} is not a whole number of CSS px between 1 and 10000")
        if int(part) not in widths:
            widths.append(int(part))
    if not widths:
        raise UsageError("no widths given")
    return widths


def parse_themes(text: str) -> list[str] | None:
    """None means auto (decided from what the page offers)."""
    if text.strip().lower() == "auto":
        return None
    themes = [t.strip().lower() for t in text.split(",") if t.strip()]
    bad = [t for t in themes if t not in KNOWN_THEMES]
    if bad or not themes:
        raise UsageError(f"theme(s) {bad or text!r} not one of auto, {', '.join(KNOWN_THEMES)}")
    return list(dict.fromkeys(themes))


def parse_target(text: str) -> tuple[str, Path | None]:
    """Return (url, local path or None). A path must exist; a URL must be http(s) or file."""
    if re.match(r"^https?://", text, re.I):
        return text, None
    if text.lower().startswith("file://"):
        return text, None
    path = Path(text).expanduser()
    if not path.is_file():
        raise UsageError(f"{text!r} is neither an http(s) URL nor an existing file")
    path = path.resolve()
    return path.as_uri(), path


def default_out_dir() -> Path:
    """A fresh folder under the system temp directory; never inside the target's folder."""
    return Path(tempfile.mkdtemp(prefix="uismith-probe-"))


def detect_mechanisms(css_text: str) -> dict:
    """What theme mechanisms the page source shows (probe.md section 2)."""
    mech = {"media": bool(re.search(r"prefers-color-scheme\s*:\s*(dark|light)", css_text, re.I)),
            "attr": None, "class": None, "on": "html",
            "vscode": bool(re.search(r"vscode-(dark|light|high-contrast)|--vscode-", css_text))}
    m = re.search(r"(html|:root|body)?\[\s*(data-[\w-]+)\s*=\s*['\"]?(?:dark|light)\b", css_text, re.I)
    if m:
        mech["attr"] = m.group(2)
        mech["on"] = "body" if (m.group(1) or "").lower() == "body" else "html"
    c = re.search(r"(html|:root|body)\.dark\b", css_text)
    if c:
        mech["class"] = "dark"
        mech["on"] = "body" if c.group(1) == "body" else mech["on"] if m else "html"
    return mech


def themes_for(mech: dict, requested: list[str] | None) -> tuple[list[str], str]:
    """The theme list and a one-line note on how it was chosen."""
    if requested is not None:
        return requested, "themes as requested"
    if mech.get("vscode"):
        return ["light", "dark", "high-contrast"], "VS Code theme classes found: light, dark, high-contrast"
    found = [k for k in ("media", "attr", "class") if mech.get(k)]
    if found:
        return ["light", "dark"], "theme mechanism found (" + ", ".join(found) + "): light and dark"
    return ["light"], "one theme found: the source shows no theme mechanism, so light only"


def judge(m: dict, tol: int = TOLERANCE_PX) -> dict:
    """The overflow judgement from the raw numbers JS_MEASURE returns (probe.md section 3)."""
    vw = m["clientWidth"]
    res = {"viewport": vw, "doc_width": m["scrollWidth"], "page_over": 0,
           "past_right": [], "off_left": [], "clipped": [], "truncated": [], "spills": []}
    if m["scrollWidth"] - vw >= tol:
        res["page_over"] = m["scrollWidth"] - vw
    for e in m.get("elements", []):
        if e.get("off_edge", True) and not e.get("in_scroller"):
            over = e["right"] - vw
            if over >= tol:
                res["past_right"].append({"sel": e["sel"], "px": round(over)})
            if -e["left"] >= tol:
                res["off_left"].append({"sel": e["sel"], "px": round(-e["left"])})
        if e.get("has_text"):
            cut_x = e.get("overflow_x") in CLIPS and e["scroll_w"] - e["client_w"] >= tol
            cut_y = e.get("overflow_y") in CLIPS and e["scroll_h"] - e["client_h"] >= max(tol, TOLERANCE_Y_PX)
            if cut_x or cut_y:
                row = {"sel": e["sel"], "px": max(e["scroll_w"] - e["client_w"], e["scroll_h"] - e["client_h"])}
                ellipsis = (e.get("text_overflow") == "ellipsis" and cut_x and not cut_y) or \
                    (e.get("line_clamp") and cut_y and not cut_x)
                res["truncated" if ellipsis else "clipped"].append(row)
        if e.get("has_text") and e.get("spill") and e.get("overflow_x") == "visible" \
                and e["scroll_w"] - e["client_w"] >= tol:
            res["spills"].append({"sel": e["sel"], "px": round(e["scroll_w"] - e["client_w"])})
    sections = m.get("sections") or {}
    res["sections_checked"] = sections.get("checked", 0)
    res["empty_sections"] = list(sections.get("empty", []))
    res["missing_sections"] = list(sections.get("missing", []))
    res["console_errors"] = list(m.get("console_errors", []))
    res["page_errors"] = list(m.get("page_errors", []))
    res["finding"] = bool(res["page_over"] or res["past_right"] or res["off_left"] or res["clipped"]
                          or res["spills"]
                          or res["empty_sections"] or res["missing_sections"]
                          or res["console_errors"] or res["page_errors"])
    return res


def evidence_problem(m: dict, width: int, status: int | None, url: str, shot: Path | None) -> str | None:
    """None when the row's evidence holds (probe.md section 4), else the reason."""
    if url.startswith("chrome-error://"):
        return "the browser showed an error page"
    if status is not None and status >= 400:
        return f"the server answered HTTP {status}"
    if m.get("innerWidth") != width:
        return f"the viewport is {m.get('innerWidth')} px, not the intended {width} px"
    if not m.get("visible"):
        return "blank page: no visible element was painted"
    if shot is not None and (not shot.is_file() or shot.stat().st_size == 0):
        return "no screenshot was written"
    return None


def exit_code(rows: list[dict]) -> int:
    return EXIT_PASS if rows and all(r["status"] == "pass" for r in rows) else EXIT_FINDING


def _names(items: list[dict]) -> str:
    if not items:
        return "-"
    shown = ", ".join(f"{i['sel']} ({i['px']} px)" for i in items[:3])
    return shown + (f" +{len(items) - 3} more" if len(items) > 3 else "")


def _plain(items: list[str]) -> str:
    if not items:
        return "-"
    shown = ", ".join(items[:3])
    return shown + (f" +{len(items) - 3} more" if len(items) > 3 else "")


def _spilled(j: dict) -> list[dict]:
    # Spills share the Clipped column, each named as a spill (probe.md section 3).
    return [{"sel": s["sel"] + " spills", "px": s["px"]} for s in j.get("spills", [])]


def _state_cells(state: str, j: dict, screenshot: str) -> str:
    sections = _plain(j["empty_sections"] + [f"{s} (missing)" for s in j["missing_sections"]])
    errors = _plain([f"page: {e}" for e in j["page_errors"]] + [f"console: {e}" for e in j["console_errors"]])
    return (f"{state} | {j['doc_width']} / {j['viewport']} | {_names(j['past_right'])} | "
            f"{_names(j['off_left'])} | {_names(j['clipped'] + _spilled(j))} | {_names(j['truncated'])} | "
            f"{sections} | {errors} | {'FINDING' if j['finding'] else 'PASS'} | {screenshot} |")


def bare_url(url):
    """A report names the request, never its query, its fragment or a local folder."""
    if not url:
        return url
    url = url.split("?")[0].split("#")[0]
    return url.rsplit("/", 1)[-1] if url.startswith("file:") else url


def _sections_checked(row):
    """Sections read in either state: a page whose only sections sit in closed folds still counts."""
    opened = (row.get("folds_open") or {}).get("result") or {}
    return row["result"]["sections_checked"] or opened.get("sections_checked")


def format_report(target: str, note: str, out_dir: Path, rows: list[dict]) -> str:
    lines = [f"uismith probe: {target}", f"Themes: {note}", f"Screenshots: {out_dir}", ""]
    for theme in dict.fromkeys(r["theme"] for r in rows):
        lines += [f"Theme: {theme}", "",
                  "| Width | State | Page / viewport | Past right | Off left | Clipped | Truncated | "
                  "Empty sections | Errors | Status | Screenshot |",
                  "|---|---|---|---|---|---|---|---|---|---|---|"]
        for r in (r for r in rows if r["theme"] == theme):
            if r["status"] == "not-run":
                lines.append(f"| {r['width']} | - | - | - | - | - | - | - | - | NOT-RUN: {r['reason']} | - |")
                continue
            lines.append(f"| {r['width']} | " + _state_cells("as loaded", r["result"], r["screenshot"]))
            opened = r.get("folds_open")
            if opened:
                state = f"{opened['folds']} folds open"
                lines.append(f"| {r['width']} | " + _state_cells(state, opened["result"], opened["screenshot"]))
        lines.append("")
    ran = [r for r in rows if r["status"] != "not-run"]
    if ran and not any(_sections_checked(r) for r in ran):
        lines += ["Sections: none found to check, so an empty region was not ruled out. "
                  "Name the page's own with --section.", ""]
    verdict = {EXIT_PASS: "PASS", EXIT_FINDING: "FINDINGS or NOT-RUN rows"}[exit_code(rows)]
    if exit_code(rows) == EXIT_PASS and not any(_sections_checked(r) for r in ran):
        verdict = "PASS (empty sections not checked)"
    lines.append(f"Verdict: {verdict}. Interaction states (open menus, inactive tabs, errors after submit) "
                 "are not probed.")
    return "\n".join(lines)


def load_playwright():
    """The Playwright sync API, or None when the package is missing."""
    try:
        from playwright import sync_api  # noqa: WPS433 (optional dependency)
    except ImportError:
        return None
    return sync_api


def _browser_missing(err: Exception) -> bool:
    text = str(err)
    return "Executable doesn't exist" in text or "playwright install" in text


def _first_line(err: Exception) -> str:
    return (str(err).strip().splitlines() or [type(err).__name__])[0]


def _start_message(err: Exception) -> str:
    if _browser_missing(err):
        return INSTALL_MESSAGE
    return (f"uismith probe: NOT-RUN - the browser could not start: {_first_line(err)}\n"
            "Every row is NOT-RUN. Fix the browser start, then run the same probe command again.")


def _one_line(text: str) -> str:
    return " ".join(str(text).split())[:MAX_ERROR_CHARS]


def _watch_errors(page) -> dict:
    """Listen before the page loads: a script that throws during load is the case that matters."""
    seen: dict = {"console": [], "page": []}

    def on_console(msg):
        if msg.type == "error" and len(seen["console"]) < MAX_ERRORS:
            url = bare_url((getattr(msg, "location", None) or {}).get("url"))  # says which request failed
            seen["console"].append(_one_line(msg.text) + (f" ({_one_line(url)})" if url else ""))

    def on_page_error(err):
        if len(seen["page"]) < MAX_ERRORS:
            seen["page"].append(_one_line(getattr(err, "message", err)))

    page.on("console", on_console)
    page.on("pageerror", on_page_error)
    return seen


def _measure(page, opts: dict) -> dict:
    page.evaluate(JS_SETTLE)
    m = page.evaluate(JS_MEASURE, MAX_ELEMENTS)
    m["sections"] = page.evaluate(JS_SECTIONS, opts.get("sections", []))
    return m


def _open_folds(page) -> tuple[int, bool]:
    """(folds opened, whether they stayed open). A fold can reveal another, so it takes rounds."""
    opened = 0
    for _ in range(FOLD_ROUNDS):
        n = page.evaluate(JS_OPEN_FOLDS)
        if not n:
            return opened, True
        opened += n
        page.evaluate(JS_SETTLE)
    return opened, page.evaluate(JS_OPEN_FOLDS) == 0


def _probe_row(browser, url: str, width: int, height: int, theme: str, opts: dict, shot: Path,
               ref_look: str | None) -> dict:
    kw = {"viewport": {"width": width, "height": height}, "color_scheme": "light" if theme == "light" else "dark"}
    if theme == "high-contrast" and not opts["vscode"]:
        kw["forced_colors"] = "active"  # outside VS Code, high contrast is the forced-colours mode
    ctx = browser.new_context(**kw)
    try:
        page = ctx.new_page()
        seen = _watch_errors(page)
        resp = page.goto(url, wait_until="load", timeout=30000)
        if url.lower().startswith(("http://", "https://")):
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:  # a page that never goes quiet is still measured
                pass
        if opts["attr"] or opts["class"] or opts["vscode"]:
            page.evaluate(JS_APPLY_THEME, [theme, opts["attr"], opts["class"], opts["vscode"], opts["on"]])
        m = _measure(page, opts)
        look = page.evaluate(JS_LOOK)
        page.screenshot(path=str(shot), full_page=True)
        status = resp.status if resp is not None else None
        problem = evidence_problem(m, width, status, page.url, shot)
        if problem is None and theme != "light" and (ref_look is None or look == ref_look):
            problem = (f"the {theme} theme did not take effect: the page's colours match light"
                       if ref_look is not None else f"the {theme} theme could not be checked: no light reference")
        got = {"m": m, "look": look, "problem": problem, "open": None}
        if problem is not None:
            return got
        counts = len(seen["console"]), len(seen["page"])
        m["console_errors"], m["page_errors"] = list(seen["console"]), list(seen["page"])
        folds, stayed = _open_folds(page)
        if not folds:
            return got
        open_shot = shot.with_name(f"{shot.stem}-open{shot.suffix}")
        opened = _measure(page, opts)
        page.screenshot(path=str(open_shot), full_page=True)
        got["problem"] = evidence_problem(opened, width, status, page.url, open_shot) if stayed else \
            "the closed folds would not stay open, so the page was not measured with them open"
        opened["console_errors"], opened["page_errors"] = seen["console"][counts[0]:], seen["page"][counts[1]:]
        got["open"] = {"m": opened, "folds": folds, "screenshot": str(open_shot)}
        return got
    finally:
        ctx.close()


def _attempt(browser, url, width, height, theme, opts, shot, ref_look) -> dict:
    try:
        return _probe_row(browser, url, width, height, theme, opts, shot, ref_look)
    except Exception as err:
        return {"problem": f"the page did not load: {_first_line(err)}"}


def run(args, sync_api, url: str, out_dir: Path) -> tuple[int, str]:
    widths, requested = parse_widths(args.widths), parse_themes(args.themes)
    try:
        manager = sync_api.sync_playwright()
        pw = manager.__enter__()
    except Exception as err:  # the driver itself did not start
        return EXIT_MISSING, _start_message(err)
    try:
        try:
            browser = pw.chromium.launch(headless=True)  # never a window
        except Exception as err:
            return EXIT_MISSING, _start_message(err)
        try:
            base_look = None  # the page as loaded in a light context: the reference when no light row ran
            ctx = browser.new_context(viewport={"width": widths[0], "height": args.height}, color_scheme="light")
            try:
                page = ctx.new_page()
                page.goto(url, wait_until="load", timeout=30000)
                mech = detect_mechanisms(page.evaluate(JS_COLLECT_CSS))
                base_look = page.evaluate(JS_LOOK)
            except Exception:  # the rows below report the load failure per width
                mech = detect_mechanisms("")
            finally:
                ctx.close()
            opts = {"attr": args.theme_attr or mech["attr"], "class": args.theme_class or mech["class"],
                    "vscode": args.vscode or mech["vscode"], "on": mech["on"], "sections": args.section}
            themes, note = themes_for({**mech, "vscode": opts["vscode"]}, requested)
            rows, light_look = [], {}
            for theme in themes:
                for width in widths:
                    shot = out_dir / f"{width}-{theme}.png"
                    row = {"width": width, "theme": theme, "screenshot": str(shot)}
                    ref = light_look.get(width, base_look)
                    got = _attempt(browser, url, width, args.height, theme, opts, shot, ref)
                    if got["problem"]:  # one retry, then NOT-RUN (probe.md section 4)
                        got = _attempt(browser, url, width, args.height, theme, opts, shot, ref)
                    if got["problem"]:
                        row.update(status="not-run", reason=got["problem"])
                    else:
                        if theme == "light":
                            light_look[width] = got["look"]
                        res = judge(got["m"])
                        row["result"] = res
                        found = res["finding"]
                        if got.get("open"):
                            opened = judge(got["open"]["m"])
                            row["folds_open"] = {"folds": got["open"]["folds"], "result": opened,
                                                 "screenshot": got["open"]["screenshot"]}
                            found = found or opened["finding"]
                        row["status"] = "finding" if found else "pass"
                    rows.append(row)
        finally:
            browser.close()
    finally:
        manager.__exit__(None, None, None)
    code = exit_code(rows)
    if args.json:
        return code, json.dumps({"target": args.target, "themes": note, "out": str(out_dir),
                                 "rows": rows, "exit": code}, indent=2)
    return code, format_report(args.target, note, out_dir, rows)


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        parse_widths(args.widths)
        parse_themes(args.themes)
        url, _ = parse_target(args.target)
        if args.height < 1:
            raise UsageError("height must be at least 1 CSS px")
    except UsageError as err:
        print(f"uismith probe: usage error - {err}", file=sys.stderr)
        return EXIT_USAGE
    sync_api = load_playwright()
    if sync_api is None:
        print(INSTALL_MESSAGE, file=sys.stderr)
        return EXIT_MISSING
    out_dir = Path(args.out) if args.out else default_out_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    code, text = run(args, sync_api, url, out_dir)
    print(text, file=sys.stderr if code == EXIT_MISSING else sys.stdout)
    return code


if __name__ == "__main__":
    sys.exit(main())
