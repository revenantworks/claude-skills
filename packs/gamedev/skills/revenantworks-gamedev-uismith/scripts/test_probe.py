#!/usr/bin/env python3
"""Tests for probe.py (uismith's rendered fit probe), for every part that runs without a browser.

Run: python -m unittest discover -s scripts -p "test_*.py"
Stdlib only. Playwright is never imported here: the browser path is driven through a fake
sync API that returns fixture numbers, and the missing-dependency path hides the package.
"""
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import probe  # noqa: E402

HAS_PLAYWRIGHT = importlib.util.find_spec("playwright") is not None


def measure(width=375, scroll=None, elements=(), visible=12):
    """A JS_MEASURE result built from fixture numbers."""
    return {"innerWidth": width, "clientWidth": width, "scrollWidth": width if scroll is None else scroll,
            "visible": visible, "elements": list(elements)}


def el(sel="div", left=0, right=100, in_scroller=False, has_text=False, ox="visible", oy="visible",
       to="clip", sw=100, cw=100, sh=20, ch=20):
    return {"sel": sel, "left": left, "right": right, "in_scroller": in_scroller, "has_text": has_text,
            "overflow_x": ox, "overflow_y": oy, "text_overflow": to, "scroll_w": sw, "client_w": cw,
            "scroll_h": sh, "client_h": ch}


class Arguments(unittest.TestCase):
    def test_defaults(self):
        a = probe.build_parser().parse_args(["page.html"])
        self.assertEqual(probe.parse_widths(a.widths), [320, 375, 768, 1024, 1440])
        self.assertIsNone(probe.parse_themes(a.themes))
        self.assertEqual((a.height, a.json, a.vscode, a.out), (900, False, False, None))

    def test_widths_parse_dedupe_and_reject(self):
        self.assertEqual(probe.parse_widths("320, 768,320"), [320, 768])
        for bad in ("", "abc", "0", "-5", "320,12.5", "20000"):
            with self.subTest(bad=bad), self.assertRaises(probe.UsageError):
                probe.parse_widths(bad)

    def test_themes_parse(self):
        self.assertIsNone(probe.parse_themes("AUTO"))
        self.assertEqual(probe.parse_themes("dark,light,dark"), ["dark", "light"])
        self.assertEqual(probe.parse_themes("high-contrast"), ["high-contrast"])
        with self.assertRaises(probe.UsageError):
            probe.parse_themes("sepia")

    def test_target_url_file_and_missing(self):
        self.assertEqual(probe.parse_target("http://localhost:5173/"), ("http://localhost:5173/", None))
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "page.html"
            f.write_text("<p>hi</p>", encoding="utf-8")
            url, path = probe.parse_target(str(f))
            self.assertTrue(url.startswith("file:"))
            self.assertEqual(path, f.resolve())
            with self.assertRaises(probe.UsageError):
                probe.parse_target(str(Path(d) / "nope.html"))

    def test_default_out_dir_is_fresh_and_outside_the_target_folder(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = probe.default_out_dir(), probe.default_out_dir()
            try:
                self.assertNotEqual(a, b)
                self.assertNotIn(Path(d).resolve(), a.resolve().parents)
                self.assertTrue(a.name.startswith("uismith-probe-"))
            finally:
                a.rmdir()
                b.rmdir()

    def test_usage_error_exits_3_not_2(self):
        err = io.StringIO()
        with redirect_stderr(err):
            self.assertEqual(probe.main(["missing-file.html"]), 3)
            self.assertEqual(probe.main(["--bogus"]), 3)
        self.assertIn("usage error", err.getvalue())


class Themes(unittest.TestCase):
    def test_media_query(self):
        mech = probe.detect_mechanisms("@media (prefers-color-scheme: dark) { body { background: #000 } }")
        self.assertTrue(mech["media"])
        self.assertEqual(probe.themes_for(mech, None)[0], ["light", "dark"])

    def test_attribute_and_class_toggles(self):
        self.assertEqual(probe.detect_mechanisms(':root[data-theme="dark"] { --bg: #111 }')["attr"], "data-theme")
        self.assertEqual(probe.detect_mechanisms("[data-mode=light] body {}")["attr"], "data-mode")
        self.assertEqual(probe.detect_mechanisms("html.dark .card { color: white }")["class"], "dark")

    def test_vscode_classes_give_three_themes(self):
        mech = probe.detect_mechanisms("body.vscode-high-contrast a { outline: 1px solid }")
        self.assertTrue(mech["vscode"])
        self.assertEqual(probe.themes_for(mech, None)[0], ["light", "dark", "high-contrast"])
        self.assertTrue(probe.detect_mechanisms("color: var(--vscode-foreground)")["vscode"])

    def test_no_mechanism_means_light_only_and_says_so(self):
        themes, note = probe.themes_for(probe.detect_mechanisms("body { color: #222 } .darkness {}"), None)
        self.assertEqual(themes, ["light"])
        self.assertIn("one theme found", note)

    def test_requested_themes_win(self):
        self.assertEqual(probe.themes_for(probe.detect_mechanisms(""), ["dark"])[0], ["dark"])


class Judgement(unittest.TestCase):
    def test_clean_page_passes(self):
        res = probe.judge(measure(elements=[el(right=375)]))
        self.assertFalse(res["finding"])
        self.assertEqual(res["page_over"], 0)

    def test_page_wider_by_one_px_is_a_finding_half_a_px_is_not(self):
        self.assertEqual(probe.judge(measure(scroll=376))["page_over"], 1)
        self.assertTrue(probe.judge(measure(scroll=376))["finding"])
        self.assertFalse(probe.judge(measure(scroll=375.5))["finding"])

    def test_past_right_edge_named_with_pixels(self):
        res = probe.judge(measure(scroll=467, elements=[el("table.data", right=467.4)]))
        self.assertEqual(res["past_right"], [{"sel": "table.data", "px": 92}])
        self.assertEqual(res["page_over"], 92)

    def test_inside_a_sideways_scroller_is_skipped(self):
        res = probe.judge(measure(elements=[el("td", right=900, in_scroller=True)]))
        self.assertEqual(res["past_right"], [])
        self.assertFalse(res["finding"])

    def test_off_the_left_edge(self):
        res = probe.judge(measure(elements=[el("nav", left=-40, right=200)]))
        self.assertEqual(res["off_left"], [{"sel": "nav", "px": 40}])
        self.assertTrue(res["finding"])

    def test_clipped_text_is_a_finding(self):
        res = probe.judge(measure(elements=[el("td.name", has_text=True, ox="hidden", sw=180, cw=120)]))
        self.assertEqual(res["clipped"], [{"sel": "td.name", "px": 60}])
        self.assertTrue(res["finding"])

    def test_vertical_clip_counts(self):
        res = probe.judge(measure(elements=[el("p", has_text=True, oy="clip", sh=60, ch=40)]))
        self.assertEqual(res["clipped"][0]["px"], 20)

    def test_ellipsis_is_truncated_not_a_finding(self):
        res = probe.judge(measure(elements=[el("span.title", has_text=True, ox="hidden", to="ellipsis",
                                               sw=300, cw=200)]))
        self.assertEqual(res["truncated"], [{"sel": "span.title", "px": 100}])
        self.assertEqual(res["clipped"], [])
        self.assertFalse(res["finding"])

    def test_overflow_without_clipping_or_text_is_not_clipped_text(self):
        res = probe.judge(measure(elements=[el("div", has_text=True, ox="visible", sw=300, cw=200),
                                            el("img", has_text=False, ox="hidden", sw=300, cw=200)]))
        self.assertEqual(res["clipped"], [])


class Evidence(unittest.TestCase):
    def test_good_row(self):
        self.assertIsNone(probe.evidence_problem(measure(width=320), 320, 200, "http://x/", None))

    def test_each_failure(self):
        cases = [
            (measure(width=320), 320, None, "chrome-error://chromewebdata/", "error page"),
            (measure(width=320), 320, 404, "http://x/", "HTTP 404"),
            (measure(width=980), 320, 200, "http://x/", "not the intended 320"),
            (measure(width=320, visible=0), 320, 200, "http://x/", "blank page"),
        ]
        for m, w, status, url, want in cases:
            with self.subTest(want=want):
                self.assertIn(want, probe.evidence_problem(m, w, status, url, None))

    def test_missing_screenshot(self):
        with tempfile.TemporaryDirectory() as d:
            shot = Path(d) / "320-light.png"
            self.assertIn("screenshot", probe.evidence_problem(measure(width=320), 320, 200, "file:///p", shot))
            shot.write_bytes(b"png")
            self.assertIsNone(probe.evidence_problem(measure(width=320), 320, 200, "file:///p", shot))


class ExitAndReport(unittest.TestCase):
    def test_exit_codes(self):
        self.assertEqual(probe.exit_code([{"status": "pass"}, {"status": "pass"}]), 0)
        self.assertEqual(probe.exit_code([{"status": "pass"}, {"status": "finding"}]), 1)
        self.assertEqual(probe.exit_code([{"status": "pass"}, {"status": "not-run"}]), 1)
        self.assertEqual(probe.exit_code([]), 1)

    def test_report_names_not_run_and_screenshots(self):
        rows = [{"width": 320, "theme": "dark", "status": "not-run", "reason": "blank page", "screenshot": "s"},
                {"width": 768, "theme": "dark", "status": "pass", "screenshot": "768-dark.png",
                 "result": probe.judge(measure(width=768))}]
        text = probe.format_report("page.html", "note", Path("out"), rows)
        self.assertIn("NOT-RUN: blank page", text)
        self.assertIn("768-dark.png", text)
        self.assertIn("Theme: dark", text)
        self.assertIn("FINDINGS or NOT-RUN", text)


class MissingDependency(unittest.TestCase):
    def _page(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        f = Path(d.name) / "page.html"
        f.write_text("<p>hi</p>", encoding="utf-8")
        return f

    def test_no_playwright_exits_2_with_install_lines(self):
        f = self._page()
        err = io.StringIO()
        with unittest.mock.patch.dict(sys.modules, {"playwright": None, "playwright.sync_api": None}), \
                redirect_stderr(err):
            self.assertEqual(probe.main([str(f)]), 2)
        self.assertIn("pip install playwright", err.getvalue())
        self.assertIn("playwright install", err.getvalue())
        self.assertIn("NOT-RUN", err.getvalue())

    def test_no_browser_build_exits_2(self):
        class FakePW:
            chromium = SimpleNamespace(launch=unittest.mock.Mock(
                side_effect=Exception("Executable doesn't exist at /x/chrome; run playwright install")))

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        api = SimpleNamespace(sync_playwright=FakePW)
        args = probe.build_parser().parse_args([str(self._page())])
        code, text = probe.run(args, api, "file:///page.html", Path(tempfile.gettempdir()))
        self.assertEqual(code, 2)
        self.assertIn("pip install playwright", text)
        self.assertEqual(FakePW.chromium.launch.call_args.kwargs, {"headless": True})

    @unittest.skipIf(HAS_PLAYWRIGHT, "Playwright is installed here; the real missing path cannot run")
    def test_cli_exit_2_when_playwright_absent(self):
        r = subprocess.run([sys.executable, str(HERE / "probe.py"), str(self._page())],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("pip install playwright", r.stderr)
        self.assertEqual(r.stdout, "")


class FakeBrowserRun(unittest.TestCase):
    """The orchestration (themes x widths, retry, NOT-RUN, report, exit) with a fake browser."""

    @staticmethod
    def _default_look(ctx, applied):
        """The page's colours: they follow the colour scheme, forced colours and the last toggle."""
        return f"{ctx.get('color_scheme')}/{ctx.get('forced_colors')}/{applied[0] if applied else None}"

    def _api(self, css, measures, look=None, failing_gotos=0):
        calls = {"contexts": [], "launch": None, "theme": [], "gotos": 0}
        look = look or self._default_look

        class Page:
            def __init__(self, ctx):
                self.ctx, self.url, self.applied = ctx, "file:///page.html", None

            def goto(self, url, **kw):
                calls["gotos"] += 1
                if calls["gotos"] <= failing_gotos + 1 and calls["gotos"] > 1:  # detection load succeeds
                    raise Exception("net::ERR_ABORTED at file:///page.html\nCall log: ...")
                return SimpleNamespace(status=200)

            def wait_for_load_state(self, *a, **kw):
                pass

            def evaluate(self, js, arg=None):
                if js is probe.JS_COLLECT_CSS:
                    return css
                if js is probe.JS_APPLY_THEME:
                    calls["theme"].append(arg)
                    self.applied = arg
                    return True
                if js is probe.JS_MEASURE:
                    return measures(self.ctx["viewport"]["width"], self.ctx.get("color_scheme"))
                if js is getattr(probe, "JS_LOOK", object()):
                    return look(self.ctx, self.applied)
                return True

            def screenshot(self, path, full_page):
                assert full_page
                Path(path).write_bytes(b"png")

        class Ctx(dict):
            def new_page(self):
                return Page(self)

            def close(self):
                pass

        class Browser:
            def new_context(self, **kw):
                calls["contexts"].append(kw)
                return Ctx(kw)

            def close(self):
                pass

        class PW:
            chromium = SimpleNamespace(launch=lambda **kw: calls.__setitem__("launch", kw) or Browser())

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        return SimpleNamespace(sync_playwright=PW), calls

    def _run(self, argv, api):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "page.html"
            f.write_text("<p>hi</p>", encoding="utf-8")
            args = probe.build_parser().parse_args([str(f), *argv])
            return probe.run(args, api, f.as_uri(), Path(d))

    def test_dark_theme_overflow_at_320_is_a_finding(self):
        def measures(w, scheme):
            if w == 320 and scheme == "dark":
                return measure(width=320, scroll=412, elements=[el("table.data", right=412)])
            return measure(width=w)
        api, calls = self._api("@media (prefers-color-scheme: dark) {}", measures)
        code, text = self._run(["--widths", "320,768", "--json"], api)
        rep = json.loads(text)
        self.assertEqual(code, 1)
        self.assertEqual(calls["launch"], {"headless": True})
        self.assertEqual([(r["theme"], r["width"], r["status"]) for r in rep["rows"]],
                         [("light", 320, "pass"), ("light", 768, "pass"),
                          ("dark", 320, "finding"), ("dark", 768, "pass")])
        self.assertTrue(rep["rows"][2]["screenshot"].endswith("320-dark.png"))
        self.assertEqual(rep["rows"][2]["result"]["past_right"], [{"sel": "table.data", "px": 92}])

    def test_clean_page_light_only_passes(self):
        api, calls = self._api("body { color: #222 }", lambda w, s: measure(width=w))
        code, text = self._run(["--widths", "375"], api)
        self.assertEqual(code, 0)
        self.assertIn("one theme found", text)
        self.assertEqual(calls["theme"], [])

    def test_blank_twice_is_not_run_after_one_retry(self):
        api, calls = self._api("", lambda w, s: measure(width=w, visible=0))
        code, text = self._run(["--widths", "375", "--json"], api)
        row = json.loads(text)["rows"][0]
        self.assertEqual((code, row["status"]), (1, "not-run"))
        self.assertIn("blank page", row["reason"])
        self.assertEqual(len(calls["contexts"]), 3)  # detection + first try + one retry

    def test_vscode_flag_sets_body_classes(self):
        api, calls = self._api("", lambda w, s: measure(width=w))
        code, _ = self._run(["--widths", "375", "--vscode"], api)
        self.assertEqual(code, 0)
        self.assertEqual([a[0] for a in calls["theme"]], ["light", "dark", "high-contrast"])
        self.assertTrue(all(a[3] for a in calls["theme"]))

    # R3-03: the toggle goes where the page's CSS reads it, and a theme that did not take is NOT-RUN.
    def test_body_class_theme_is_set_on_body(self):
        def look(ctx, applied):  # this page only changes when the class lands on <body>
            on_body = bool(applied) and len(applied) > 4 and applied[4] == "body"
            return "dark" if on_body and applied[0] != "light" else "light"
        api, calls = self._api("body.dark { background: #000 }", lambda w, s: measure(width=w), look=look)
        code, text = self._run(["--widths", "375", "--json"], api)
        rows = json.loads(text)["rows"]
        self.assertEqual([(r["theme"], r["status"]) for r in rows], [("light", "pass"), ("dark", "pass")])
        self.assertEqual(code, 0)
        self.assertTrue(calls["theme"] and all(a[4] == "body" for a in calls["theme"]))

    def test_theme_that_does_not_take_effect_is_not_run(self):
        api, _ = self._api("html.dark .card { color: white }", lambda w, s: measure(width=w),
                           look=lambda ctx, applied: "rgb(255, 255, 255)/rgb(0, 0, 0)")
        code, text = self._run(["--widths", "320,768", "--json"], api)
        rows = json.loads(text)["rows"]
        self.assertEqual(code, 1)
        self.assertEqual([r["status"] for r in rows if r["theme"] == "light"], ["pass", "pass"])
        dark = [r for r in rows if r["theme"] == "dark"]
        self.assertEqual([r["status"] for r in dark], ["not-run", "not-run"])
        self.assertIn("did not take effect", dark[0]["reason"])

    # R3-05: a browser that cannot start is exit 2 with a plain line; a load exception gets its retry.
    def test_browser_that_cannot_start_exits_2_not_a_traceback(self):
        api, _ = self._api("", lambda w, s: measure(width=w))
        api.sync_playwright.chromium = SimpleNamespace(launch=unittest.mock.Mock(
            side_effect=Exception("Host system is missing dependencies to run browsers.\nlibnss3")))
        code, text = self._run(["--widths", "375"], api)
        self.assertEqual(code, 2)
        self.assertIn("could not start: Host system is missing dependencies", text)
        self.assertNotIn("libnss3", text)

    def test_driver_that_cannot_start_exits_2(self):
        class Broken:
            def __enter__(self):
                raise Exception("Connection closed while reading from the driver")

            def __exit__(self, *exc):
                return False
        code, text = self._run(["--widths", "375"], SimpleNamespace(sync_playwright=Broken))
        self.assertEqual(code, 2)
        self.assertIn("could not start", text)

    def test_load_exception_is_retried_once(self):
        api, calls = self._api("", lambda w, s: measure(width=w), failing_gotos=1)
        code, text = self._run(["--widths", "375", "--json"], api)
        self.assertEqual((code, json.loads(text)["rows"][0]["status"]), (0, "pass"))
        self.assertEqual(calls["gotos"], 3)  # detection + failed try + retry

    # R3-06: high contrast outside VS Code is forced colours, not just the dark scheme.
    def test_high_contrast_without_vscode_forces_colours(self):
        api, calls = self._api("", lambda w, s: measure(width=w))
        code, _ = self._run(["--widths", "375", "--themes", "high-contrast"], api)
        self.assertEqual(code, 0)
        self.assertEqual([c.get("forced_colors") for c in calls["contexts"][1:]], ["active"])


class ThemeTarget(unittest.TestCase):
    """R3-03: detection records the element the theme selector sits on."""

    def test_selector_target(self):
        self.assertEqual(probe.detect_mechanisms("body.dark .x { color: #fff }").get("on"), "body")
        self.assertEqual(probe.detect_mechanisms("html.dark .x { color: #fff }").get("on"), "html")
        self.assertEqual(probe.detect_mechanisms('body[data-theme="dark"] { --bg: #111 }').get("on"), "body")
        self.assertEqual(probe.detect_mechanisms(':root[data-theme="dark"] { --bg: #111 }').get("on"), "html")


class VerticalTolerance(unittest.TestCase):
    """R3-07: a 1 px vertical overhang from line height is not clipped text; 2 px is."""

    def test_one_px_vertical_overhang(self):
        self.assertEqual(probe.judge(measure(elements=[el("p", has_text=True, oy="hidden", sh=21, ch=20)]))
                         ["clipped"], [])
        self.assertEqual(len(probe.judge(measure(elements=[el("p", has_text=True, oy="hidden", sh=22, ch=20)]))
                             ["clipped"]), 1)


# A minimal DOM stand-in, so JS_MEASURE itself runs (under Node) on fixture boxes.
NODE = shutil.which("node")
DOM_HARNESS = r"""
const spec = JSON.parse(require('fs').readFileSync(process.argv[2], 'utf8'));
const DEF = {display: 'block', visibility: 'visible', overflowX: 'visible', overflowY: 'visible',
  textOverflow: 'clip', webkitLineClamp: 'none', clipPath: 'none', clip: 'auto',
  backgroundColor: 'rgba(0, 0, 0, 0)', color: 'rgb(0, 0, 0)'};
const matches = (n, sel) => sel.split(',').some(p => {
  const m = p.trim().match(/^\[([\w-]+)(?:="([^"]*)")?\]$/);
  const a = n.attrs || {};
  return !!m && (m[1] in a) && (m[2] === undefined || a[m[1]] === m[2]);
});
const proto = {
  closest(sel) { for (let n = this; n; n = n.parentElement) if (matches(n, sel)) return n; return null; },
  get textContent() { return (this.own || '') + this.kids.map(k => k.textContent).join(''); }
};
const node = (o) => Object.assign(Object.create(proto), {kids: [], attrs: {}, _cs: {}, className: '', id: ''}, o);
const de = node({tagName: 'HTML', clientWidth: spec.width, scrollWidth: spec.width, parentElement: null});
const els = [];
const body = node({tagName: 'BODY', scrollWidth: spec.width, parentElement: de, querySelectorAll: () => els});
for (const s of spec.elements) {
  const e = node({tagName: s.tag.toUpperCase(), id: s.id || '', className: s.cls || '', _cs: s.cs || {},
    attrs: s.attrs || {}, own: s.text || '', scrollWidth: s.sw || 0, clientWidth: s.cw || 0,
    scrollHeight: s.sh || 0, clientHeight: s.ch || 0,
    childNodes: s.text ? [{nodeType: 3, textContent: s.text}] : [],
    getBoundingClientRect() { const [l, t, w, h] = s.rect; return {left: l, top: t, width: w, height: h, right: l + w, bottom: t + h}; }});
  e.parentElement = s.parent == null ? body : els[s.parent];
  e.parentElement.kids.push(e);
  els.push(e);
}
globalThis.window = {innerWidth: spec.width};
globalThis.document = {documentElement: de, body};
globalThis.getComputedStyle = el => Object.assign({}, DEF, el._cs);
"""


def run_measure(width, elements):
    """Run the real JS_MEASURE source on fixture boxes under Node and return its numbers."""
    with tempfile.TemporaryDirectory() as d:
        h, s = Path(d) / "harness.js", Path(d) / "spec.json"
        h.write_text(DOM_HARNESS + "const fn = (" + probe.JS_MEASURE + ");\n"
                     "console.log(JSON.stringify(fn(200)));\n", encoding="utf-8")
        s.write_text(json.dumps({"width": width, "elements": elements}), encoding="utf-8")
        r = subprocess.run([NODE, str(h), str(s)], capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            raise AssertionError(r.stderr)
        return json.loads(r.stdout)


@unittest.skipIf(NODE is None, "Node is not installed; the in-page measure cannot run without a JS engine")
class InPageMeasure(unittest.TestCase):
    """JS_MEASURE on fixture boxes (R3-01, R3-07): the part the fake browser cannot see."""

    def test_text_in_a_child_of_a_clipping_box_is_clipped(self):
        m = run_measure(375, [
            {"tag": "td", "cls": "name", "rect": [0, 0, 120, 20], "sw": 180, "cw": 120, "sh": 20, "ch": 20,
             "cs": {"overflowX": "hidden"}},
            {"tag": "span", "text": "A very long customer name", "parent": 0, "rect": [0, 0, 180, 20],
             "cs": {"display": "inline"}},
        ])
        self.assertEqual(probe.judge(m)["clipped"], [{"sel": "td.name", "px": 60}])

    def test_own_text_in_a_clipping_box_is_still_clipped(self):
        m = run_measure(375, [{"tag": "p", "text": "Long label", "rect": [0, 0, 100, 20], "sw": 140, "cw": 100,
                               "sh": 20, "ch": 20, "cs": {"overflowX": "hidden"}}])
        self.assertEqual(probe.judge(m)["clipped"], [{"sel": "p", "px": 40}])

    def test_line_clamped_box_is_truncated_not_clipped(self):
        m = run_measure(375, [{"tag": "p", "cls": "blurb", "text": "Many lines", "rect": [0, 0, 300, 60],
                               "sw": 300, "cw": 300, "sh": 90, "ch": 60,
                               "cs": {"overflowY": "hidden", "webkitLineClamp": "3"}}])
        res = probe.judge(m)
        self.assertEqual((res["clipped"], res["truncated"]), ([], [{"sel": "p.blurb", "px": 30}]))

    def test_visually_hidden_and_hidden_off_canvas_are_not_findings(self):
        m = run_measure(375, [
            {"tag": "span", "cls": "sr-only", "text": "Skip to content", "rect": [0, 0, 1, 1], "sw": 110,
             "cw": 1, "sh": 20, "ch": 1, "cs": {"overflowX": "hidden", "overflowY": "hidden",
                                                "clip": "rect(0px, 0px, 0px, 0px)"}},
            {"tag": "nav", "cls": "drawer", "attrs": {"aria-hidden": "true"}, "rect": [-300, 0, 300, 800]},
            {"tag": "a", "text": "Menu link", "parent": 1, "rect": [-280, 10, 100, 20]},
        ])
        self.assertFalse(probe.judge(m)["finding"], probe.judge(m))

    def test_visible_element_off_the_left_still_counts(self):
        m = run_measure(375, [{"tag": "nav", "rect": [-40, 0, 240, 50]}])
        self.assertEqual(probe.judge(m)["off_left"], [{"sel": "nav", "px": 40}])


if __name__ == "__main__":
    unittest.main()
