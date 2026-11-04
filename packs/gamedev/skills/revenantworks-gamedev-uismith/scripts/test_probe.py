#!/usr/bin/env python3
"""Tests for probe.py (uismith's rendered fit probe), for every part that runs without a browser.

Run: python -m unittest discover -s scripts -p "test_*.py"
Stdlib only. The browser path is driven through a fake sync API that returns fixture numbers, and
the missing-dependency path hides the package. Playwright is imported only by RealBrowser, which
loads small real pages and skips where the package or its Chromium build is absent.
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

    def _api(self, css, measures, look=None, failing_gotos=0, sections=None, folds=(), load_errors=(),
             open_measures=None, open_errors=()):
        """folds: what each JS_OPEN_FOLDS call returns in turn, then 0. load_errors and open_errors
        are (kind, text) pairs fired during the load and while the folds open."""
        calls = {"contexts": [], "launch": None, "theme": [], "gotos": 0, "shots": [], "sections": []}
        look = look or self._default_look

        class Page:
            def __init__(self, ctx):
                self.ctx, self.url, self.applied = ctx, "file:///page.html", None
                self.handlers, self.folds, self.opened = {}, list(folds), False

            def on(self, event, handler):
                self.handlers[event] = handler

            def _fire(self, errors):
                for kind, text in errors:
                    if kind == "page":
                        self.handlers["pageerror"](SimpleNamespace(message=text))
                    else:
                        self.handlers["console"](SimpleNamespace(type=kind, text=text, location={}))

            def goto(self, url, **kw):
                calls["gotos"] += 1
                if calls["gotos"] <= failing_gotos + 1 and calls["gotos"] > 1:  # detection load succeeds
                    raise Exception("net::ERR_ABORTED at file:///page.html\nCall log: ...")
                if self.handlers:
                    self._fire(load_errors)
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
                    fn = open_measures if self.opened and open_measures else measures
                    return fn(self.ctx["viewport"]["width"], self.ctx.get("color_scheme"))
                if js is probe.JS_SECTIONS:
                    calls["sections"].append(arg)
                    return sections(self.opened) if sections else {"checked": 1, "empty": [], "missing": []}
                if js is probe.JS_OPEN_FOLDS:
                    n = self.folds.pop(0) if self.folds else 0
                    if n:
                        self.opened = True
                        self._fire(open_errors)
                    return n
                if js is getattr(probe, "JS_LOOK", object()):
                    return look(self.ctx, self.applied)
                return True

            def screenshot(self, path, full_page):
                assert full_page
                calls["shots"].append(Path(path).name)
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

    # A page that throws, a section left empty, a fold hiding overflow: each passed before.
    def test_page_error_is_a_finding_though_the_page_fits(self):
        api, _ = self._api("", lambda w, s: measure(width=w),
                           load_errors=[("page", "TypeError: x is\n  null"), ("log", "fine")])
        code, text = self._run(["--widths", "375", "--json"], api)
        row = json.loads(text)["rows"][0]
        self.assertEqual((code, row["status"]), (1, "finding"))
        self.assertEqual(row["result"]["page_errors"], ["TypeError: x is null"])
        self.assertEqual(row["result"]["console_errors"], [])

    def test_console_error_is_a_finding_and_other_levels_are_not(self):
        api, _ = self._api("", lambda w, s: measure(width=w), load_errors=[("error", "boom")])
        code, text = self._run(["--widths", "375", "--json"], api)
        self.assertEqual((code, json.loads(text)["rows"][0]["result"]["console_errors"]), (1, ["boom"]))
        api, _ = self._api("", lambda w, s: measure(width=w), load_errors=[("warning", "w"), ("info", "i")])
        self.assertEqual(self._run(["--widths", "375"], api)[0], 0)

    def test_error_text_is_capped(self):
        api, _ = self._api("", lambda w, s: measure(width=w), load_errors=[("error", "x" * 900)] * 40)
        rep = json.loads(self._run(["--widths", "375", "--json"], api)[1])
        errors = rep["rows"][0]["result"]["console_errors"]
        self.assertEqual(len(errors), probe.MAX_ERRORS)
        self.assertEqual(len(errors[0]), probe.MAX_ERROR_CHARS)

    def test_empty_and_missing_sections_are_findings(self):
        api, calls = self._api("", lambda w, s: measure(width=w), sections=lambda opened: {
            "checked": 3, "empty": ['section#trends "Trends"'], "missing": ["#detail"]})
        code, text = self._run(["--widths", "375", "--section", "#detail"], api)
        self.assertEqual(code, 1)
        self.assertIn('section#trends "Trends"', text)
        self.assertIn("#detail (missing)", text)
        self.assertEqual(calls["sections"][0], ["#detail"])

    def test_a_page_with_no_sections_says_the_check_saw_nothing(self):
        api, _ = self._api("", lambda w, s: measure(width=w),
                           sections=lambda opened: {"checked": 0, "empty": [], "missing": []})
        code, text = self._run(["--widths", "375"], api)
        self.assertEqual(code, 0)
        self.assertIn("not ruled out", text)
        self.assertIn("Verdict: PASS (empty sections not checked).", text)

    def test_a_page_with_sections_says_a_plain_pass(self):
        api, _ = self._api("", lambda w, s: measure(width=w))
        self.assertIn("Verdict: PASS. ", self._run(["--widths", "375"], api)[1])

    def test_no_folds_measures_once(self):
        api, calls = self._api("", lambda w, s: measure(width=w))
        code, text = self._run(["--widths", "375", "--json"], api)
        self.assertEqual(code, 0)
        self.assertNotIn("folds_open", json.loads(text)["rows"][0])
        self.assertEqual(calls["shots"], ["375-light.png"])

    def test_overflow_only_with_folds_open_is_a_finding_and_both_states_report(self):
        api, calls = self._api("", lambda w, s: measure(width=w), folds=[2],
                               open_measures=lambda w, s: measure(width=w, scroll=467,
                                                                  elements=[el("table.wide", right=467)]))
        code, text = self._run(["--widths", "375", "--json"], api)
        row = json.loads(text)["rows"][0]
        self.assertEqual((code, row["status"]), (1, "finding"))
        self.assertFalse(row["result"]["finding"])
        self.assertEqual(row["folds_open"]["folds"], 2)
        self.assertEqual(row["folds_open"]["result"]["past_right"], [{"sel": "table.wide", "px": 92}])
        self.assertEqual(calls["shots"], ["375-light.png", "375-light-open.png"])
        api, _ = self._api("", lambda w, s: measure(width=w), folds=[2],
                           open_measures=lambda w, s: measure(width=w, scroll=467))
        _, md = self._run(["--widths", "375"], api)
        self.assertIn("| 375 | as loaded | 375 / 375", md)
        self.assertIn("| 375 | 2 folds open | 467 / 375", md)

    def test_an_error_thrown_while_opening_is_charged_to_the_open_state(self):
        api, _ = self._api("", lambda w, s: measure(width=w), folds=[1], open_errors=[("page", "lazy fold died")])
        code, text = self._run(["--widths", "375", "--json"], api)
        row = json.loads(text)["rows"][0]
        self.assertEqual((code, row["result"]["page_errors"]), (1, []))
        self.assertEqual(row["folds_open"]["result"]["page_errors"], ["lazy fold died"])

    def test_a_fold_opened_by_a_fold_takes_another_round(self):
        api, _ = self._api("", lambda w, s: measure(width=w), folds=[2, 1])
        code, text = self._run(["--widths", "375", "--json"], api)
        self.assertEqual((code, json.loads(text)["rows"][0]["folds_open"]["folds"]), (0, 3))

    def test_folds_that_will_not_stay_open_are_not_run_never_a_pass(self):
        api, _ = self._api("", lambda w, s: measure(width=w), folds=[1] * 40)
        code, text = self._run(["--widths", "375", "--json"], api)
        row = json.loads(text)["rows"][0]
        self.assertEqual((code, row["status"]), (1, "not-run"))
        self.assertIn("would not stay open", row["reason"])


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


CLEAN = "<!doctype html><title>t</title><main><section><h2>A</h2><p>Text here.</p></section></main>"


@unittest.skipUnless(HAS_PLAYWRIGHT, "Playwright is not installed; the real page path cannot run")
class RealBrowser(unittest.TestCase):
    """Small real pages in headless Chromium: the in-page checks no fake can prove."""

    @classmethod
    def setUpClass(cls):
        cls.api = probe.load_playwright()
        try:
            with cls.api.sync_playwright() as pw:
                pw.chromium.launch(headless=True).close()
        except Exception as err:
            raise unittest.SkipTest(f"Chromium did not start: {str(err).splitlines()[0]}")

    def _probe(self, html, *argv, width="375"):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "page.html"
            f.write_text(html, encoding="utf-8")
            args = probe.build_parser().parse_args([str(f), "--widths", width, "--json", *argv])
            code, text = probe.run(args, self.api, f.as_uri(), Path(d))
        return code, json.loads(text)["rows"][0]

    def test_clean_page_passes(self):
        code, row = self._probe(CLEAN)
        self.assertEqual((code, row["status"]), (0, "pass"), row)
        self.assertEqual(row["result"]["sections_checked"], 2)
        self.assertNotIn("folds_open", row)

    def test_a_script_that_throws_fails_a_page_that_fits(self):
        code, row = self._probe(CLEAN + "<script>const x = null; x.do;</script>")
        self.assertEqual(code, 1)
        self.assertEqual(len(row["result"]["page_errors"]), 1)
        self.assertIn("null", row["result"]["page_errors"][0])

    def test_console_error_fails_console_log_does_not(self):
        code, row = self._probe(CLEAN + "<script>console.error('bad thing')</script>")
        self.assertEqual((code, len(row["result"]["console_errors"])), (1, 1))
        self.assertTrue(row["result"]["console_errors"][0].startswith("bad thing"))
        self.assertEqual(self._probe(CLEAN + "<script>console.log('ok');console.warn('w')</script>")[0], 0)

    def test_sections_a_crash_leaves_blank_are_named(self):
        code, row = self._probe("<!doctype html><title>t</title><p>Intro</p>"
                                "<section id=a></section>"
                                "<section id=b><h2>Trends</h2><div></div></section>"
                                "<section id=c><table><thead><tr><th>Name</th></tr></thead><tbody></tbody></table></section>"
                                "<section id=d><p> </p></section>")
        self.assertEqual(code, 1)
        self.assertEqual(row["result"]["empty_sections"],
                         ["section#a", 'section#b "Trends"', "section#c", "section#d"])

    def test_only_the_outermost_empty_section_is_named(self):
        _, row = self._probe("<!doctype html><title>t</title><main id=m><section id=a></section></main><p>x</p>")
        self.assertEqual(row["result"]["empty_sections"], ["main#m"])

    def test_visually_hidden_text_does_not_count_as_content(self):
        hidden = "position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0)"
        _, row = self._probe(f"<!doctype html><title>t</title><p>x</p><section id=a><span style='{hidden}'>label</span></section>")
        self.assertEqual(row["result"]["empty_sections"], ["section#a"])

    def test_what_is_not_an_empty_section(self):
        cases = {
            "image": "<section><img alt=x width=20 height=20 src='data:image/gif;base64,R0lGODlhAQABAAAAACw='></section>",
            "svg": "<section><svg width=20 height=20></svg></section>",
            "canvas": "<section><canvas width=20 height=20></canvas></section>",
            "control": "<section><button>Retry</button></section>",
            "background": "<section style='height:40px;background-image:linear-gradient(red,blue)'></section>",
            "hidden attr": "<section hidden></section><p>x</p>",
            "display none": "<section style='display:none'></section><p>x</p>",
            "aria-hidden": "<section aria-hidden=true style='height:4px'></section><p>x</p>",
            "absolute child": "<section style='position:relative'><p style='position:absolute'>x</p></section>",
            "only a closed fold": "<section><details><summary>More</summary>Body</details></section>",
            "display contents": "<section><div style='display:contents'>Text here</div></section>",
            "contents root": "<p>x</p><section style='display:contents'><span style='display:contents'>Text</span></section>",
            "CSS bar": "<section><div style='height:8px;background:#07c'></div></section>",
            "painted root": "<section style='height:8px;background:#07c'></section>",
            "bordered box": "<section><div style='height:8px;border:1px solid #333'></div></section>",
            "bordered root": "<section style='height:8px;border:1px solid #333'></section>",
            "pseudo icon": "<style>.i::before{content:'*'}</style><section><span class=i></span></section>",
            "pseudo root": "<style>.i::before{content:'*'}</style><section class=i></section>",
            "shadow DOM": "<section><x-a></x-a></section><script>customElements.define('x-a',class extends "
                          "HTMLElement{constructor(){super();this.attachShadow({mode:'open'}).innerHTML="
                          "'<p>Inside</p>'}})</script>",
            "slotted": "<section><x-b>Given</x-b></section><script>customElements.define('x-b',class extends "
                       "HTMLElement{constructor(){super();this.attachShadow({mode:'open'}).innerHTML="
                       "'<div><slot></slot></div>'}})</script>",
            "slot fallback": "<section><x-c></x-c></section><script>customElements.define('x-c',class extends "
                             "HTMLElement{constructor(){super();this.attachShadow({mode:'open'}).innerHTML="
                             "'<slot>Fallback</slot>'}})</script>",
            "filled just after load": "<section id=s></section><script>setTimeout(()=>{s.textContent='Late'},"
                                      "200)</script>",
            "fold filled after opening": "<p>x</p><details id=f><summary>S</summary><div id=b></div></details>"
                                         "<script>f.addEventListener('toggle',()=>{setTimeout(()=>{"
                                         "b.textContent='Late'},300)})</script>",
            "collapsed accordion": "<button aria-expanded=false aria-controls=p>Open</button>"
                                   "<section id=p style='max-height:0;overflow:hidden'><p>Body</p></section>",
            "empty collapsed accordion": "<button aria-expanded=false aria-controls=p>Open</button>"
                                         "<section id=p style='max-height:0;overflow:hidden'></section>",
            "hidden by CSS override": "<p>x</p><section hidden style='display:block;height:4px'></section>",
            "inert": "<p>x</p><section inert style='height:4px'></section>",
        }
        for name, body in cases.items():
            with self.subTest(name):
                code, row = self._probe("<!doctype html><title>t</title>" + body)
                self.assertEqual(row["result"]["empty_sections"], [])
                opened = row.get("folds_open")
                self.assertEqual(opened["result"]["empty_sections"] if opened else [], [])
                self.assertEqual(code, 0, row)

    def test_a_filled_look_is_not_faked_by_transparent_css(self):
        cases = {
            "transparent background": "<section id=a style='height:8px;background:transparent'></section>",
            "transparent border": "<section id=a style='height:8px;border:1px solid transparent'></section>",
            "empty pseudo": "<style>#a::before{content:''}</style><section id=a></section>",
            "nothing slotted": "<section id=a><x-d></x-d></section><script>customElements.define('x-d',class "
                               "extends HTMLElement{constructor(){super();this.attachShadow({mode:'open'})"
                               ".innerHTML='<slot></slot>'}})</script>",
        }
        for name, body in cases.items():
            with self.subTest(name):
                _, row = self._probe("<!doctype html><title>t</title><p>x</p>" + body)
                self.assertEqual(row["result"]["empty_sections"], ["section#a"])

    def test_a_console_error_names_the_url_that_failed(self):
        _, row = self._probe(CLEAN + "<img alt=x src='no-such-file.png'>")
        self.assertIn("no-such-file.png", row["result"]["console_errors"][0])

    def test_a_panel_nobody_says_is_collapsed_stays_empty(self):
        _, row = self._probe("<!doctype html><title>t</title><button aria-expanded=true aria-controls=p>x</button>"
                             "<section id=p style='max-height:0;overflow:hidden'><p>Body</p></section>")
        self.assertEqual(row["result"]["empty_sections"], ["section#p"])

    def test_crushed_section_with_text_is_empty(self):
        _, row = self._probe("<!doctype html><title>t</title><p>x</p>"
                             "<section id=a style='height:0;overflow:hidden'><p>gone</p></section>")
        self.assertEqual(row["result"]["empty_sections"], ["section#a"])

    def test_named_sections(self):
        page = "<!doctype html><title>t</title><div id=full>x</div><div id=blank></div><div id=off hidden>y</div>"
        code, row = self._probe(page, "--section", "#full", "--section", "#blank", "--section", "#nope",
                                "--section", "#off", "--section", "[[bad")
        self.assertEqual(code, 1)
        self.assertEqual(row["result"]["empty_sections"], ["div#blank"])
        self.assertEqual(row["result"]["missing_sections"], ["#nope", "#off", "[[bad (invalid selector)"])
        self.assertEqual(self._probe(page, "--section", "#full")[0], 0)

    def test_overflow_inside_a_closed_fold_is_found_with_the_folds_open(self):
        wide = "<div id=wide style='width:900px'>wide</div>"
        code, row = self._probe(f"<!doctype html><title>t</title><main><p>x</p><details><summary>More</summary>{wide}</details></main>")
        self.assertEqual((code, row["status"]), (1, "finding"))
        self.assertFalse(row["result"]["finding"], row["result"])
        self.assertEqual(row["folds_open"]["folds"], 1)
        self.assertEqual(row["folds_open"]["result"]["past_right"][0]["sel"], "div#wide")

    def test_an_empty_fold_is_found_with_the_folds_open(self):
        code, row = self._probe("<!doctype html><title>t</title><p>x</p><details id=f><summary>More</summary></details>")
        self.assertEqual(code, 1)
        self.assertEqual(row["result"]["empty_sections"], [])
        self.assertEqual(row["folds_open"]["result"]["empty_sections"], ['details#f "More"'])

    def test_every_fold_of_an_exclusive_accordion_and_nested_folds_open(self):
        wide = "<div id=wide style='width:900px'>wide</div>"
        code, row = self._probe("<!doctype html><title>t</title><p>x</p>"
                                "<details name=g><summary>A</summary>a</details>"
                                f"<details name=g><summary>B</summary><details><summary>C</summary>{wide}</details></details>")
        self.assertEqual(code, 1)
        self.assertEqual(row["folds_open"]["folds"], 3)
        self.assertEqual(row["folds_open"]["result"]["past_right"][0]["sel"], "div#wide")

    def test_a_fold_that_closes_itself_is_not_run(self):
        code, row = self._probe("<!doctype html><title>t</title><p>x</p>"
                                "<details id=f><summary>S</summary>b</details><script>"
                                "f.addEventListener('toggle', () => { f.open = false; });</script>")
        self.assertEqual((code, row["status"]), (1, "not-run"))
        self.assertIn("would not stay open", row["reason"])

    def test_an_error_thrown_by_opening_a_fold_is_found(self):
        code, row = self._probe("<!doctype html><title>t</title><p>x</p>"
                                "<details id=f><summary>S</summary>b</details><script>"
                                "f.addEventListener('toggle', () => { throw new Error('lazy fold died'); });</script>")
        self.assertEqual(code, 1)
        self.assertEqual(row["result"]["page_errors"], [])
        self.assertIn("lazy fold died", row["folds_open"]["result"]["page_errors"][0])

    def test_a_hidden_tab_is_not_measured_as_the_reference_says(self):
        code, row = self._probe("<!doctype html><title>t</title><section><p>x</p></section>"
                                "<div role=tabpanel hidden><div style='width:900px'>wide</div></div>")
        self.assertEqual((code, row["status"]), (0, "pass"))


class ReportWording(unittest.TestCase):
    def test_a_url_loses_its_query_and_a_local_folder(self):
        self.assertEqual("https://a.test/x.png", probe.bare_url("https://a.test/x.png?token=abc#top"))
        self.assertEqual("page.html", probe.bare_url("file:///site/page.html"))
        self.assertIsNone(probe.bare_url(None))

    def test_sections_read_only_with_folds_open_still_count(self):
        row = {"result": {"sections_checked": 0}, "folds_open": {"result": {"sections_checked": 1}}}
        self.assertTrue(probe._sections_checked(row))
        self.assertFalse(probe._sections_checked({"result": {"sections_checked": 0}}))


if __name__ == "__main__":
    unittest.main()
