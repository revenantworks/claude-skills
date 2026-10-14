#!/usr/bin/env python3
"""uismith probe: does a rendered page fit at every width in every theme it offers?

Usage:
    python probe.py <file-or-url> [--widths 320,375,768,1024,1440] [--themes auto]
                    [--theme-attr data-theme] [--theme-class dark] [--vscode]
                    [--out DIR] [--height 900] [--json]

Loads one local HTML file or one URL the user names, in a headless Chromium (never a window),
at each width and theme. Chromium also fetches whatever that page itself requests and follows
redirects; the script adds no request and sends no data of its own. Per row it measures the document's scroll width against the viewport,
visible elements past the right edge or left of 0, and text clipped by its own box, and writes a
full-page screenshot `<width>-<theme>.png` to the output folder. The contract is
`references/probe.md`.

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

JS_SETTLE = """() => new Promise(resolve => {
  const done = () => requestAnimationFrame(() => requestAnimationFrame(() => resolve(true)));
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(done); else done();
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
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) continue;
    out.visible++;
    if (clippedAway(cs, r)) continue;
    // A whole box off-screen inside aria-hidden or inert is a closed drawer, not a break.
    const parked = (r.right <= 0 || r.left >= out.clientWidth) && !!el.closest('[aria-hidden="true"],[inert]');
    // Text anywhere inside the box counts: a clipping cell's text usually sits in a child span.
    const hasText = !!(el.textContent && el.textContent.trim());
    const edge = !parked && (r.right > out.clientWidth || r.left < 0);
    const cut = hasText && (clips(cs.overflowX) || clips(cs.overflowY)) &&
      (el.scrollWidth > el.clientWidth || el.scrollHeight > el.clientHeight);
    if (!edge && !cut) continue;
    if (out.elements.length >= maxElements) continue;
    const clamp = cs.webkitLineClamp;
    out.elements.push({
      sel: sel(el), left: r.left, right: r.right, in_scroller: edge ? inScroller(el) : false,
      off_edge: edge, has_text: hasText, overflow_x: cs.overflowX, overflow_y: cs.overflowY,
      text_overflow: cs.textOverflow, line_clamp: !!clamp && clamp !== 'none',
      scroll_w: el.scrollWidth, client_w: el.clientWidth,
      scroll_h: el.scrollHeight, client_h: el.clientHeight
    });
  }
  return out;
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
           "past_right": [], "off_left": [], "clipped": [], "truncated": []}
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
    res["finding"] = bool(res["page_over"] or res["past_right"] or res["off_left"] or res["clipped"])
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


def format_report(target: str, note: str, out_dir: Path, rows: list[dict]) -> str:
    lines = [f"uismith probe: {target}", f"Themes: {note}", f"Screenshots: {out_dir}", ""]
    for theme in dict.fromkeys(r["theme"] for r in rows):
        lines += [f"Theme: {theme}", "",
                  "| Width | Page / viewport | Past right | Off left | Clipped | Truncated | Status | Screenshot |",
                  "|---|---|---|---|---|---|---|---|"]
        for r in (r for r in rows if r["theme"] == theme):
            if r["status"] == "not-run":
                lines.append(f"| {r['width']} | - | - | - | - | - | NOT-RUN: {r['reason']} | - |")
                continue
            j = r["result"]
            lines.append(f"| {r['width']} | {j['doc_width']} / {j['viewport']} | {_names(j['past_right'])} | "
                         f"{_names(j['off_left'])} | {_names(j['clipped'])} | {_names(j['truncated'])} | "
                         f"{r['status'].upper()} | {r['screenshot']} |")
        lines.append("")
    verdict = {EXIT_PASS: "PASS", EXIT_FINDING: "FINDINGS or NOT-RUN rows"}[exit_code(rows)]
    lines.append(f"Verdict: {verdict}. Interaction states (open menus, errors after submit) are not probed.")
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


def _probe_row(browser, url: str, width: int, height: int, theme: str, opts: dict, shot: Path,
               ref_look: str | None) -> dict:
    kw = {"viewport": {"width": width, "height": height}, "color_scheme": "light" if theme == "light" else "dark"}
    if theme == "high-contrast" and not opts["vscode"]:
        kw["forced_colors"] = "active"  # outside VS Code, high contrast is the forced-colours mode
    ctx = browser.new_context(**kw)
    try:
        page = ctx.new_page()
        resp = page.goto(url, wait_until="load", timeout=30000)
        if url.lower().startswith(("http://", "https://")):
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:  # a page that never goes quiet is still measured
                pass
        if opts["attr"] or opts["class"] or opts["vscode"]:
            page.evaluate(JS_APPLY_THEME, [theme, opts["attr"], opts["class"], opts["vscode"], opts["on"]])
        page.evaluate(JS_SETTLE)
        m = page.evaluate(JS_MEASURE, MAX_ELEMENTS)
        look = page.evaluate(JS_LOOK)
        page.screenshot(path=str(shot), full_page=True)
        status = resp.status if resp is not None else None
        problem = evidence_problem(m, width, status, page.url, shot)
        if problem is None and theme != "light" and (ref_look is None or look == ref_look):
            problem = (f"the {theme} theme did not take effect: the page's colours match light"
                       if ref_look is not None else f"the {theme} theme could not be checked: no light reference")
        return {"m": m, "look": look, "problem": problem}
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
                    "vscode": args.vscode or mech["vscode"], "on": mech["on"]}
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
                        row.update(status="finding" if res["finding"] else "pass", result=res)
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
