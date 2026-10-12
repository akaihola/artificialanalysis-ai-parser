"""Browser tests for intelligence-vs-cost.html, in Chromium and Firefox.

The tests serve the repository with http.server on a free port and replace models.json
with the small fixture below, except for one smoke test that loads the real file.

    uv run --with "$(grep -E '^playwright[=<>~!]' "$UV_CONSTRAINT")" \
        python3 -m unittest discover -s tests -v

Without Playwright installed the tests are skipped.
"""
import functools
import http.server
import json
import re
import struct
import threading
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # the parser tests still run
    sync_playwright = None

ROOT = Path(__file__).resolve().parents[1]
DESKTOP = {"width": 1440, "height": 900}
MOBILE = {"width": 390, "height": 844}
EFFORT_ORDER = {"none": 0, "minimal": 10, "low": 20, "medium": 30, "default": 35, "high": 40, "xhigh": 50, "max": 60}
DEFAULT_FAMILIES = {"gpt-6-astra", "gpt-6-1-sol", "gpt-6-luna", "claude-opus-5-5",
                    "claude-fable-5-1", "claude-haiku-5-5", "gemini-4-argon", "grok-4-7"}


def livebench(source, coding=(2, 2), agentic=(3, 3)):
    subtasks = {}
    if coding:
        subtasks["livebench_coding"] = {"completed": coding[0], "expected": coding[1]}
    if agentic:
        subtasks["livebench_agentic_coding"] = {"completed": agentic[0], "expected": agentic[1]}
    return {"source_model": source, "release": "2026_06_25", "subtasks": subtasks}


def variant(slug, family, family_name, lab, lab_name, effort, score, cost, time, *,
            speed=100.0, released="2026-09-01", **extra):
    """One models.json row. SciCode is the intelligence score minus 10."""
    return {
        "name": f"{family_name} ({effort})", "creator": lab_name, "provider": lab_name, "slug": slug,
        "family": family, "family_name": family_name, "lab": lab, "lab_name": lab_name,
        "released": released, "effort": effort, "effort_order": EFFORT_ORDER[effort],
        "intelligence_index": score, "coding_index": score - 10, "math_index": None,
        "terminalbench_v4_0": None, "cost_per_task": cost, "e2e_response_time_s": time,
        "output_tokens_per_second": speed, "reasoning": effort != "none", "open_weights": False,
        "deprecated": False, "livebench_coding": None, "livebench_agentic_coding": None,
        "livebench": None, **extra,
    }


ANTHROPIC = ("anthropic", "Anthropic")
OPENAI = ("openai", "OpenAI")
# Eight default families plus a Medium-tier extra, two Notable families, an open-weights
# OpenAI family, a lab without a logo, a deprecated family and two unplottable rows.
MODELS = [
    variant("claude-opus-5-5-high", "claude-opus-5-5", "Claude Opus 5.5", *ANTHROPIC, "high", 56, 2.0, 300,
            speed=90.0, released="2026-09-22"),
    variant("claude-opus-5-5", "claude-opus-5-5", "Claude Opus 5.5", *ANTHROPIC, "max", 58, 6.0, 600,
            speed=96.0, released="2026-09-22"),
    variant("claude-fable-5-1", "claude-fable-5-1", "Claude Fable 5.1", *ANTHROPIC, "default", 54, 4.0, 200,
            released="2026-08-01"),
    variant("claude-sonnet-5-5", "claude-sonnet-5-5", "Claude Sonnet 5.5", *ANTHROPIC, "high", 52, 1.0, 100,
            released="2026-09-10"),
    variant("claude-haiku-5-5-non-reasoning", "claude-haiku-5-5", "Claude Haiku 5.5", *ANTHROPIC, "none",
            30, 0.004, 5),
    variant("claude-haiku-5-5", "claude-haiku-5-5", "Claude Haiku 5.5", *ANTHROPIC, "low", 40, 0.2, 20),
    variant("claude-sonnet-5-high", "claude-sonnet-5", "Claude Sonnet 5", *ANTHROPIC, "high", 44, 0.9, 110,
            released="2026-03-01", deprecated=True),
    variant("claude-sonnet-5", "claude-sonnet-5", "Claude Sonnet 5", *ANTHROPIC, "max", 49, 2.5, 250,
            released="2026-03-01", deprecated=True),
    variant("gpt-6-astra-medium", "gpt-6-astra", "GPT-6 Astra", *OPENAI, "medium", 50, 1.5, 150,
            livebench_coding=70.0, livebench=livebench("gpt-6-astra-medium", coding=(1, 2), agentic=None)),
    variant("gpt-6-astra", "gpt-6-astra", "GPT-6 Astra", *OPENAI, "max", 57, 3.0, 400,
            livebench_coding=80.5, livebench_agentic_coding=57.3, livebench=livebench("gpt-6-astra-max")),
    variant("gpt-6-1-sol-xhigh", "gpt-6-1-sol", "GPT-6.1 Sol", *OPENAI, "xhigh", 53, 0.8, 120,
            released="2026-09-15"),
    variant("gpt-6-luna", "gpt-6-luna", "GPT-6 Luna", *OPENAI, "low", 45, 0.05, None, speed=None),
    variant("gpt-oss-120b", "gpt-oss-120b", "gpt-oss-120B", *OPENAI, "high", 35, 0.02, 10, open_weights=True),
    variant("gpt-oss-120b-low", "gpt-oss-120b", "gpt-oss-120B", *OPENAI, "low", 30, 0.0085, 8,
            open_weights=True),
    variant("gemini-4-argon", "gemini-4-argon", "Gemini 4 Argon", "google", "Google", "default", 55, 1.2, 90),
    variant("grok-4-7", "grok-4-7", "Grok 4.7", "xai", "xAI", "default", 48, 0.6, 60),
    variant("deepseek-v4-pro", "deepseek-v4-pro", "DeepSeek V4 Pro", "deepseek", "DeepSeek", "default",
            47, 0.1, 80, open_weights=True, livebench_coding=60.0, livebench=livebench("deepseek-v4-pro", agentic=None)),
    variant("kimi-k3", "kimi-k3", "Kimi K3", "kimi", "Kimi", "default", 46, 0.3, 70, open_weights=True,
            livebench_coding=65.0, livebench=livebench("kimi-k3", agentic=None)),
    variant("mistral-large-4", "mistral-large-4", "Mistral Large 4", "mistral", "Mistral", "none", 38, 0.15, 15),
    variant("free-model", "free-model", "Free Model", "acme", "Acme", "none", 20, 0, 1),
    variant("no-cost-model", "no-cost-model", "No Cost Model", "acme", "Acme", "none", 25, None, 2),
]
# Visible by default: the default families without the Non-reasoning variant.
DEFAULT_POINTS = {"claude-opus-5-5-high", "claude-opus-5-5", "claude-fable-5-1", "claude-haiku-5-5",
                  "gpt-6-astra-medium", "gpt-6-astra", "gpt-6-1-sol-xhigh", "gpt-6-luna",
                  "gemini-4-argon", "grok-4-7"}
DEFAULT_PARETO = {"gpt-6-luna", "grok-4-7", "gpt-6-1-sol-xhigh", "gemini-4-argon",
                  "claude-opus-5-5-high", "gpt-6-astra", "claude-opus-5-5"}


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


_server = None
_playwright = None


def setUpModule():
    global _server, _playwright
    if sync_playwright is None:
        return
    handler = functools.partial(QuietHandler, directory=str(ROOT))
    _server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=_server.serve_forever, daemon=True).start()
    _playwright = sync_playwright().start()


def tearDownModule():
    if _playwright:
        _playwright.stop()
    if _server:
        _server.shutdown()
        _server.server_close()


def query(page):
    """The page URL's query as {key: value}."""
    return {k: v[0] for k, v in parse_qs(urlsplit(page.url).query, keep_blank_values=True).items()}


class PageTests(unittest.TestCase):
    """Every test runs once per browser through the subclasses at the bottom."""

    browser_name = ""

    @classmethod
    def setUpClass(cls):
        assert _playwright is not None and _server is not None
        cls.browser = getattr(_playwright, cls.browser_name).launch()
        cls.base = f"http://127.0.0.1:{_server.server_address[1]}/intelligence-vs-cost.html"

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()

    # ---------- Helpers ----------
    def open(self, search="", *, models=MODELS, viewport=DESKTOP, color_scheme="dark", has_touch=False):
        """A fresh context and page, loaded and drawn. Console errors fail the test.

        `models` is the models.json fixture, None for the real file, or an HTTP error status.
        With an error status, only page errors (uncaught exceptions) fail the test.
        """
        context = self.browser.new_context(viewport=viewport, color_scheme=color_scheme, has_touch=has_touch)
        self.addCleanup(context.close)
        context.set_default_timeout(5000)
        # The page loads DM Sans from Google Fonts; the tests use the fallback font offline.
        context.route(re.compile(r"^https://fonts\.(googleapis|gstatic)\.com/"),
                      lambda route: route.fulfill(status=200, content_type="text/css", body=""))
        failing = isinstance(models, int)
        if failing:
            context.route("**/models.json", lambda route: route.fulfill(status=models, body="Not found"))
        elif models is not None:
            body = json.dumps(models)
            context.route("**/models.json",
                          lambda route: route.fulfill(status=200, content_type="application/json", body=body))
        page = context.new_page()
        errors = []
        page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}")
                if m.type == "error" and not failing else None)
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
        self.addCleanup(lambda: self.assertEqual(errors, [], "console errors"))
        page.goto(self.base + search)
        if failing:
            page.wait_for_selector("#empty-state:not([hidden])")
        else:
            self.ready(page)
        return page

    @staticmethod
    def ready(page):
        page.wait_for_function("() => window.__chart && window.__chart.state.data")
        # Let the ResizeObserver redraw at the measured size.
        page.evaluate("() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))")

    @staticmethod
    def settle(page):
        """Wait out the pointerover a browser sends for the new node under a resting cursor after a redraw."""
        page.evaluate("() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))")
        page.wait_for_timeout(100)

    @staticmethod
    def state(page, expr):
        return page.evaluate(f"() => __chart.state.{expr}")

    @staticmethod
    def points(page):
        return set(page.eval_on_selector_all("#chart [data-id]", "els => els.map((e) => e.dataset.id)"))

    @staticmethod
    def rows(page, selector=".model-row"):
        """Sidebar rows as (family, pressed) in sidebar order."""
        return page.eval_on_selector_all(
            selector, "els => els.map((e) => [e.dataset.family, e.getAttribute('aria-pressed') === 'true'])")

    @staticmethod
    def texts(page, selector):
        return page.eval_on_selector_all(selector, "els => els.map((e) => e.textContent.trim())")

    @staticmethod
    def ticks(page):
        """Axis tick labels: (Y ticks, X ticks)."""
        y = page.eval_on_selector_all('#chart g[transform^="translate(0 "] text', "els => els.map((e) => e.textContent)")
        x = page.eval_on_selector_all('#chart g[transform] > line[y2="5"] + text', "els => els.map((e) => e.textContent)")
        return y, x

    @staticmethod
    def svg_texts(page):
        return page.eval_on_selector_all("#chart text", "els => els.map((e) => e.textContent)")

    @staticmethod
    def set_slider(page, value):
        """Move the slider like a short drag: input, then change when released."""
        page.eval_on_selector("#time-slider", """(el, v) => {
            el.value = v; el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true })); }""", value)

    @staticmethod
    def tooltip_rows(page):
        """Single-variant tooltip rows as (label, value, note)."""
        return page.eval_on_selector_all("#tooltip .tooltip-value", """els => els.map((e) => [
            e.querySelector('span').textContent, e.querySelector('b').firstChild.textContent,
            e.querySelector('small')?.textContent ?? null])""")

    @staticmethod
    def table(page):
        """Table view body as {"Name (effort)": [[cell text, note or None], ...]}."""
        return page.evaluate("""() => Object.fromEntries([...document.querySelectorAll('#data-table tbody tr')]
            .map((tr) => [tr.querySelector('th .table-model').textContent.trim() + ' (' + tr.querySelector('td.effort').textContent + ')',
                [...tr.querySelectorAll('td')].map((td) => [td.firstChild?.textContent ?? '',
                  td.querySelector('small')?.textContent ?? null])]))""")

    # ---------- Load ----------
    def test_default_render(self):
        page = self.open()
        self.assertEqual(page.title(), "Intelligence vs cost")
        self.assertEqual(page.text_content("#chart-title"), "Cost vs intelligence")
        self.assertEqual(query(page), {})
        self.assertEqual(self.points(page), DEFAULT_POINTS)
        self.assertEqual(page.text_content("#model-count"), "8")
        self.assertEqual(page.text_content(".side-heading h2"), "Models 8")
        self.assertEqual({f for f, on in self.rows(page) if on}, DEFAULT_FAMILIES)
        self.assertEqual(self.texts(page, "#metric-tabs button"),
                         ["Intelligence", "Coding (SciCode)", "Math (AIME 2025)", "Terminal-Bench v4.0",
                          "LiveBench Coding", "LiveBench Agentic Coding"])
        self.assertEqual(page.get_attribute('#metric-tabs [data-key="intelligence_index"]', "aria-current"), "true")
        texts = self.svg_texts(page)
        self.assertIn("Intelligence index", texts)
        self.assertIn("Cost per task (USD, log scale)", texts)
        self.assertNotRegex(page.inner_html("#chart"), r"NaN|Infinity")
        # One label per visible family, with lab logos or a monogram.
        self.assertEqual(set(page.eval_on_selector_all(".series-label", "els => els.map((e) => e.dataset.label)")),
                         DEFAULT_FAMILIES)
        self.assertEqual(page.locator('.series-label[data-label="claude-opus-5-5"] use').get_attribute("href"),
                         "#logo-anthropic")
        # Families without a positive cost are not plottable and never listed.
        page.click("#show-all")
        page.click("#open-weights")
        listed = {f for f, _ in self.rows(page)}
        self.assertIn("gpt-oss-120b", listed)
        self.assertFalse({"free-model", "no-cost-model"} & listed)
        self.assertTrue(page.is_hidden("#empty-state"))
        self.assertTrue(page.is_hidden("#tooltip"))

    def test_real_models_json_smoke(self):
        page = self.open(models=None)
        # The count matches the selected rows, whatever the curated defaults found in the data.
        self.assertEqual(page.text_content("#model-count"), str(len([f for f, on in self.rows(page) if on])))
        self.assertGreater(int(page.text_content("#model-count")), 4)
        self.assertGreater(len(self.points(page)), 8)
        self.assertGreater(page.locator(".series-label").count(), 0)
        for tab in self.texts(page, "#metric-tabs button"):
            page.click(f'#metric-tabs button:text-is("{tab}")')
            chart = page.inner_html("#chart")
            self.assertNotRegex(chart, r"NaN|Infinity|undefined")
            if page.is_hidden("#empty-state"):
                self.assertGreater(len(self.points(page)), 2, tab)
            else:
                page.click("#empty-action")
                self.assertGreater(len(self.points(page)), 0, tab)
        page.click("#table-button")
        self.assertGreater(page.locator("#data-table tbody tr").count(), 2)

    def test_desktop_layout_fits_the_window(self):
        for viewport in ({"width": 901, "height": 700}, {"width": 1024, "height": 768},
                         {"width": 1280, "height": 800}, DESKTOP):
            page = self.open(viewport=viewport)
            self.assertFalse(self.state(page, "compact"))
            box = page.evaluate("""() => ({ scroll: document.documentElement.scrollWidth, inner: innerWidth,
                sidebar: document.getElementById('sidebar').getBoundingClientRect().right,
                settings: document.getElementById('settings-button').getBoundingClientRect().right })""")
            self.assertLessEqual(box["scroll"], box["inner"], viewport)
            self.assertLessEqual(box["sidebar"], box["inner"], viewport)
            self.assertLessEqual(box["settings"], box["inner"], viewport)
            # The plan toggles stay on one line each.
            heights = page.eval_on_selector_all("#plan-sections button", "els => els.map((e) => e.offsetHeight)")
            self.assertTrue(all(h < 20 for h in heights), (viewport, heights))
            page.context.close()

    # ---------- Header and toolbar ----------
    def test_benchmark_tabs_change_title_and_url(self):
        page = self.open()
        page.click('#metric-tabs [data-key="coding_index"]')
        self.assertEqual(page.text_content("#chart-title"), "Cost vs SciCode")
        self.assertIn("SciCode score", self.svg_texts(page))
        self.assertNotIn("Intelligence index", self.svg_texts(page))
        self.assertEqual(query(page), {"metric": "coding_index"})
        self.assertEqual(page.get_attribute('#metric-tabs [data-key="coding_index"]', "aria-current"), "true")
        self.assertEqual(page.get_attribute('#metric-tabs [data-key="intelligence_index"]', "aria-current"), "false")
        # The label anchor and crosshair follow the benchmark: SciCode is the score minus 10.
        page.hover('#chart [data-id="claude-opus-5-5"]')
        self.assertEqual(self.tooltip_rows(page)[0][:2], ["SciCode score", "48"])

        # LiveBench Coding: only two default variants have data, so the empty state offers more.
        page.click('#metric-tabs [data-key="livebench_coding"]')
        self.assertEqual(query(page), {"metric": "livebench_coding"})
        self.assertTrue(page.is_visible("#empty-state"))
        # One family with two variants: the title counts families, the hint counts points.
        self.assertEqual(page.text_content("#empty-title"), "Only 1 selected model has LiveBench Coding data")
        self.assertEqual(page.text_content("#empty-text"), "The chart needs at least 3 points with data.")
        self.assertEqual(page.text_content("#empty-action"), "Show models with LiveBench Coding data")
        page.click("#empty-action")
        self.assertTrue(page.is_hidden("#empty-state"))
        self.assertEqual(self.points(page), {"gpt-6-astra-medium", "gpt-6-astra", "deepseek-v4-pro", "kimi-k3"})
        self.assertIn("LiveBench Coding score", self.svg_texts(page))
        self.assertEqual(set(query(page)["models"].split(",")), DEFAULT_FAMILIES | {"deepseek-v4-pro", "kimi-k3"})
        # LiveBench provenance under the score.
        page.hover('#chart [data-id="gpt-6-astra"]')
        self.assertEqual(self.tooltip_rows(page)[0],
                         ["LiveBench Coding score", "80.5", "2026_06_25 · gpt-6-astra-max · 2/2 subtasks"])
        page.hover('#chart [data-id="gpt-6-astra-medium"]')
        self.assertEqual(self.tooltip_rows(page)[0][2], "2026_06_25 · gpt-6-astra-medium · 1/2 subtasks")

        page.click('#metric-tabs [data-key="intelligence_index"]')
        self.assertEqual(page.text_content("#chart-title"), "Cost vs intelligence")
        self.assertNotIn("metric", query(page))

    def test_plan_selectors_change_effective_cost(self):
        page = self.open("?models=claude-opus-5-5,gpt-6-astra,gpt-oss-120b,grok-4-7")
        page.click("#table-button")
        api = self.table(page)
        self.assertEqual(api["Claude Opus 5.5 (max)"][-3], ["$6.00", None])
        self.assertEqual(self.texts(page, "#data-table thead th")[-3], "Cost per task")

        page.click('#plan-sections [data-plan="claude-max-20x"]')
        self.assertEqual(query(page)["claude_plan"], "claude-max-20x")
        self.assertEqual(page.get_attribute('[data-plan="claude-max-20x"]', "aria-pressed"), "true")
        self.assertEqual(self.texts(page, "#data-table thead th")[-3], "Effective cost per task")
        table = self.table(page)
        # Max 20x: $200 a month for $4,000 of API usage, so 1/20 of the API cost.
        self.assertEqual(table["Claude Opus 5.5 (max)"][-3], ["$0.30", "API $6.00"])
        self.assertEqual(table["Claude Opus 5.5 (high)"][-3], ["$0.10", "API $2.00"])
        self.assertEqual(table["GPT-6 Astra (max)"][-3], ["$3.00", None])
        self.assertEqual(table["Grok 4.7 (Default)"][-3], ["$0.60", None])

        page.click('#plan-sections [data-plan="chatgpt-plus"]')
        self.assertEqual(query(page)["codex_plan"], "chatgpt-plus")
        table = self.table(page)
        # Plus: $20 for $100 of usage. gpt-oss is open weights and keeps the API price.
        self.assertEqual(table["GPT-6 Astra (max)"][-3], ["$0.60", "API $3.00"])
        self.assertEqual(table["gpt-oss-120B (high)"][-3], ["$0.02", None])
        self.assertEqual(table["gpt-oss-120B (low)"][-3], ["$0.0085", None])
        self.assertEqual(table["Grok 4.7 (Default)"][-3], ["$0.60", None])

        page.click("#table-button")
        self.assertIn("Effective cost per task (USD, log scale)", self.svg_texts(page))
        page.hover('#chart [data-id="claude-opus-5-5"]')
        rows = self.tooltip_rows(page)
        self.assertEqual(rows[1][:2], ["Cost per task (Claude Max 20x)", "$0.30"])
        self.assertEqual(rows[2][:2], ["API cost per task", "$6.00"])
        page.hover('#chart [data-id="grok-4-7"]')
        self.assertEqual([r[0] for r in self.tooltip_rows(page)],
                         ["Intelligence index", "Cost per task", "Response time", "Output speed"])

        page.click('#plan-sections [data-plan="claude-api"]')
        page.click('#plan-sections [data-plan="chatgpt-api"]')
        self.assertFalse({"claude_plan", "codex_plan"} & query(page).keys())
        self.assertIn("Cost per task (USD, log scale)", self.svg_texts(page))

    def test_speed_slider_hides_models_into_ghost_dots(self):
        page = self.open()
        self.assertEqual(page.text_content("#time-readout"), "No limit")
        before = self.ticks(page)
        # The slider runs from 5 s to 600 s on a log scale; step 125 of 200 is 100 s.
        self.set_slider(page, 125)
        self.assertEqual(page.text_content("#time-readout"), "≤ 100 s · 6 hidden")
        self.assertEqual(page.get_attribute("#time-slider", "aria-valuetext"), "≤ 100 s · 6 hidden")
        self.assertEqual(query(page), {"max_response_time": "100"})
        # GPT-6 Luna has no measured response time and stays.
        self.assertEqual(self.points(page), {"gpt-6-luna", "claude-haiku-5-5", "grok-4-7", "gemini-4-argon"})
        ghosts = page.locator("#chart .ghosts circle")
        self.assertEqual(ghosts.count(), 6)
        self.assertEqual(page.get_attribute("#chart .ghosts", "pointer-events"), "none")
        self.assertEqual(page.get_attribute("#chart .ghosts", "opacity"), ".15")
        # Ghosts get no label and no line; the Pareto line uses the remaining variants.
        self.assertEqual(set(page.eval_on_selector_all(".series-label", "els => els.map((e) => e.dataset.label)")),
                         {"gpt-6-luna", "claude-haiku-5-5", "grok-4-7", "gemini-4-argon"})
        self.assertEqual(page.locator('#chart g[data-family="claude-opus-5-5"]').count(), 0)
        pareto = page.get_attribute('#chart path[stroke-dasharray="6 5"]', "d")
        self.assertEqual(pareto.count("L"), 2)  # Luna, Grok, Gemini
        # The axes stay still while the slider moves.
        self.assertEqual(self.ticks(page), before)

        self.set_slider(page, 200)
        self.assertEqual(page.text_content("#time-readout"), "No limit")
        self.assertEqual(query(page), {})
        self.assertEqual(page.locator("#chart .ghosts").count(), 0)
        self.assertEqual(self.points(page), DEFAULT_POINTS)

    def test_pareto_line_toggle(self):
        page = self.open()
        self.assertEqual(page.get_attribute("#pareto-toggle", "aria-pressed"), "true")
        self.assertEqual(page.locator('#chart path[stroke-dasharray="6 5"]').count(), 1)
        on_front = page.eval_on_selector_all('#chart [data-id] circle:last-child[stroke-width="1.5"]',
                                             "els => els.map((e) => e.parentElement.dataset.id)")
        self.assertEqual(set(on_front), DEFAULT_PARETO)
        # Sidebar rows show whether their family reaches the line.
        rows = dict(page.eval_on_selector_all(".model-row[aria-pressed=true]",
                                              "els => els.map((e) => [e.dataset.family, e.className])"))
        self.assertIn("on-frontier", rows["claude-opus-5-5"])
        self.assertIn("off-frontier", rows["claude-fable-5-1"])

        page.click("#pareto-toggle")
        self.assertEqual(query(page), {"frontier": "false"})
        self.assertEqual(page.get_attribute("#pareto-toggle", "aria-pressed"), "false")
        self.assertEqual(page.locator('#chart path[stroke-dasharray="6 5"]').count(), 0)
        self.assertEqual(page.locator(".model-row.on-frontier, .model-row.off-frontier").count(), 0)
        page.click("#pareto-toggle")
        self.assertEqual(query(page), {})
        self.assertEqual(page.locator('#chart path[stroke-dasharray="6 5"]').count(), 1)

    def test_log_and_linear_scale(self):
        page = self.open()
        self.assertEqual(page.get_attribute("#scale-log", "aria-pressed"), "true")
        self.assertEqual(self.ticks(page)[1], ["$0.05", "$0.1", "$0.2", "$0.5", "$1", "$2", "$5"])
        page.click("#scale-linear")
        self.assertEqual(query(page), {"linear": "true"})
        self.assertEqual(page.get_attribute("#scale-linear", "aria-pressed"), "true")
        self.assertEqual(page.get_attribute("#scale-log", "aria-pressed"), "false")
        self.assertIn("Cost per task (USD)", self.svg_texts(page))
        self.assertEqual(self.ticks(page)[1], ["$0", "$2", "$4", "$6"])
        page.click("#scale-log")
        self.assertEqual(query(page), {})
        self.assertIn("Cost per task (USD, log scale)", self.svg_texts(page))

    def test_zoom_y_needs_the_pareto_line(self):
        page = self.open()
        self.assertTrue(page.is_enabled("#zoom-toggle"))
        self.assertEqual(self.ticks(page)[0], ["20", "30", "40", "50", "60"])
        page.click("#zoom-toggle")
        self.assertEqual(page.get_attribute("#zoom-toggle", "aria-pressed"), "true")
        # Fitted to the Pareto variants (45 to 58), without the default 30/50 clamps.
        self.assertEqual(self.ticks(page)[0], ["40", "45", "50", "55", "60"])
        self.assertEqual(page.locator("#plot-clip").count(), 1)
        self.assertEqual(query(page), {})  # session only

        page.click("#pareto-toggle")
        self.assertTrue(page.is_disabled("#zoom-toggle"))
        self.assertEqual(page.get_attribute("#zoom-toggle", "aria-pressed"), "false")
        self.assertEqual(self.ticks(page)[0], ["20", "30", "40", "50", "60"])

    def test_show_deprecated(self):
        page = self.open("?models=claude-opus-5-5,claude-sonnet-5,grok-4-7")
        self.assertEqual(page.get_attribute("#deprecated-toggle", "aria-pressed"), "false")
        self.assertEqual(self.points(page), {"claude-opus-5-5-high", "claude-opus-5-5", "grok-4-7"})
        self.assertNotIn("claude-sonnet-5", [f for f, _ in self.rows(page)])
        page.fill("#model-search", "sonnet")
        self.assertEqual([f for f, _ in self.rows(page)], ["claude-sonnet-5-5"])
        page.fill("#model-search", "")

        page.click("#deprecated-toggle")
        self.assertEqual(query(page)["deprecated"], "true")
        self.assertEqual(page.get_attribute("#deprecated-toggle", "aria-pressed"), "true")
        self.assertTrue({"claude-sonnet-5-high", "claude-sonnet-5"} <= self.points(page))
        # Drawn dashed and listed in the sidebar (Other, because it is selected).
        self.assertEqual(page.get_attribute('#chart g[data-family="claude-sonnet-5"] > path', "stroke-dasharray"), "5 5")
        self.assertIsNone(page.get_attribute('#chart g[data-family="claude-opus-5-5"] > path', "stroke-dasharray"))
        self.assertIn(["claude-sonnet-5", True], self.rows(page, '.model-section[aria-label="Other"] .model-row'))
        page.fill("#model-search", "sonnet")
        self.assertEqual({f for f, _ in self.rows(page)}, {"claude-sonnet-5-5", "claude-sonnet-5"})
        page.fill("#model-search", "")

        page.click("#deprecated-toggle")
        self.assertNotIn("deprecated", query(page))
        self.assertNotIn("claude-sonnet-5", self.points(page))

        # A selection of only hidden deprecated families says so and offers to show them.
        page = self.open("?models=claude-sonnet-5")
        self.assertEqual(page.text_content("#empty-title"), "The selected models are deprecated")
        self.assertTrue(page.is_hidden("#empty-text"))
        self.assertEqual(page.text_content("#model-count"), "0")
        self.assertEqual(self.texts(page, "#effort-buttons button"), [])
        page.click("#empty-action:text-is('Show deprecated')")
        self.assertEqual(page.get_attribute("#deprecated-toggle", "aria-pressed"), "true")
        self.assertEqual(page.text_content("#empty-title"), "Only 1 selected model has Intelligence data")
        self.assertEqual(page.text_content("#model-count"), "1")
        # The count matches the listed families while deprecated ones are hidden.
        page = self.open("?models=claude-opus-5-5,claude-sonnet-5")
        self.assertEqual(page.text_content("#model-count"), "1")
        self.assertEqual({f for f, on in self.rows(page) if on}, {"claude-opus-5-5"})

    def test_empty_state_names_the_filter(self):
        # The reasoning filter hides both Opus variants and Astra's max: Opus has data.
        page = self.open("?models=claude-opus-5-5,gpt-6-astra&hide-reasoning=high,max")
        self.assertEqual(page.text_content("#empty-title"), "Hidden reasoning levels leave 1 point")
        self.assertEqual(page.text_content("#empty-text"),
                         "3 more Intelligence points are at hidden reasoning levels. The chart needs at least 3.")
        page.click("#empty-action:text-is('Show all reasoning levels')")
        self.assertTrue(page.is_hidden("#empty-state"))
        self.assertEqual(self.points(page), {"claude-opus-5-5-high", "claude-opus-5-5", "gpt-6-astra-medium", "gpt-6-astra"})
        self.assertEqual(query(page), {"models": "claude-opus-5-5,gpt-6-astra", "hide-reasoning": ""})

        # Hidden deprecated Sonnet 5 holds the other points.
        page = self.open("?models=claude-sonnet-5,grok-4-7")
        self.assertEqual(page.text_content("#empty-title"), "Hidden deprecated models leave 1 point")
        self.assertEqual(page.text_content("#empty-text"),
                         "2 more Intelligence points are from deprecated models. The chart needs at least 3.")
        page.click("#empty-action:text-is('Show deprecated')")
        self.assertEqual(self.points(page), {"claude-sonnet-5-high", "claude-sonnet-5", "grok-4-7"})

        # Too little data even at every level: a family whose data is at a hidden level still counts.
        page = self.open("?models=gpt-6-astra&metric=livebench_agentic_coding&hide-reasoning=max")
        self.assertEqual(page.text_content("#empty-title"), "Only 1 selected model has LiveBench Agentic Coding data")
        self.assertEqual(page.text_content("#empty-action"), "Show models with LiveBench Agentic Coding data")

    def test_empty_state_lifts_combined_filters_without_changing_families(self):
        # Without its high variant, deprecated Sonnet 5 adds one point at a hidden level.
        one_sonnet = [m for m in MODELS if m["slug"] != "claude-sonnet-5-high"]
        for selected, excluded, models, shown, hidden, expected in [
            ("claude-sonnet-5,grok-4-7", "max", MODELS, "1 point", "2 more Intelligence points are",
             {"claude-sonnet-5-high", "claude-sonnet-5", "grok-4-7"}),
            ("claude-sonnet-5,claude-opus-5-5", "high,max", MODELS, "no points", "4 more Intelligence points are",
             {"claude-sonnet-5-high", "claude-sonnet-5", "claude-opus-5-5-high", "claude-opus-5-5"}),
            ("claude-sonnet-5,gpt-oss-120b", "max", one_sonnet, "2 points", "1 more Intelligence point is",
             {"claude-sonnet-5", "gpt-oss-120b", "gpt-oss-120b-low"}),
        ]:
            with self.subTest(selected=selected):
                page = self.open(f"?models={selected}&hide-reasoning={excluded}", models=models)
                self.assertEqual(page.text_content("#empty-title"),
                                 f"Hidden reasoning levels and deprecated models leave {shown}")
                self.assertEqual(page.text_content("#empty-text"),
                                 f"{hidden} hidden by these filters. The chart needs at least 3.")
                page.click("#empty-action:text-is('Show all reasoning levels and deprecated models')")
                self.assertTrue(page.is_hidden("#empty-state"))
                self.assertEqual(self.points(page), expected)
                self.assertEqual(self.state(page, "selected"), selected.split(","))
                self.assertEqual(self.state(page, "excluded"), [])
                self.assertTrue(self.state(page, "deprecated"))
                self.assertEqual(query(page), {"models": selected, "hide-reasoning": "", "deprecated": "true"})

    def test_defaults_missing_from_the_data(self):
        page = self.open(models=[m for m in MODELS if m["family"] != "gpt-6-luna"])
        self.assertEqual(page.text_content("#model-count"), "7")
        self.assertEqual(len([f for f, on in self.rows(page) if on]), 7)
        page.click('.model-row[data-family="grok-4-7"]')
        page.click("#reset-selection")
        self.assertEqual(set(self.state(page, "selected")), DEFAULT_FAMILIES - {"gpt-6-luna"})
        self.assertEqual(query(page), {})
        page.click('.model-row[data-family="grok-4-7"]', button="right")
        page.click('#context-menu button:text-is("Clear model selection")')
        page.click('.model-row[data-family="grok-4-7"]', button="right")
        page.click('#context-menu button:text-is("Reset model selection")')
        self.assertEqual(page.text_content("#model-count"), "7")
        self.assertEqual(query(page), {})

    # ---------- Sidebar ----------
    def test_search(self):
        page = self.open()
        page.keyboard.press("/")
        self.assertEqual(page.evaluate("document.activeElement.id"), "model-search")
        page.keyboard.type("gem")
        self.assertEqual(self.texts(page, ".model-section h3"), ["Results"])
        self.assertEqual(self.rows(page), [["gemini-4-argon", True]])
        self.assertTrue(page.is_hidden("#search-kbd"))
        self.assertTrue(page.is_visible("#search-clear"))
        self.assertTrue(page.is_hidden("#browse-options"))
        self.assertNotIn("gem", page.url)  # search text is not stored

        page.keyboard.press("Escape")
        self.assertEqual(page.input_value("#model-search"), "")
        self.assertEqual(self.texts(page, ".model-section h3"), ["Frontier", "Notable"])
        self.assertTrue(page.is_visible("#search-kbd"))

        # Lab names match too; Other families are searchable without "Show all models".
        page.fill("#model-search", "anthropic")
        self.assertEqual({f for f, _ in self.rows(page)},
                         {"claude-opus-5-5", "claude-fable-5-1", "claude-sonnet-5-5", "claude-haiku-5-5"})
        page.fill("#model-search", "mistral")
        page.click('.model-row[data-family="mistral-large-4"]')
        self.assertIn("mistral-large-4", query(page)["models"].split(","))

        page.fill("#model-search", "zzz")
        self.assertEqual(self.rows(page), [])
        self.assertTrue(page.is_visible("#search-note"))
        self.assertEqual(page.text_content("#search-note"), "No models match “zzz”.")
        page.click("#search-clear")
        self.assertEqual(page.input_value("#model-search"), "")
        self.assertEqual(page.evaluate("document.activeElement.id"), "model-search")
        self.assertTrue(page.is_hidden("#search-note"))
        # A selected Other family stays listed.
        self.assertIn(["mistral-large-4", True], self.rows(page, '.model-section[aria-label="Other"] .model-row'))

    def test_reasoning_toggles(self):
        page = self.open()
        buttons = page.eval_on_selector_all("#effort-buttons button",
                                            "els => els.map((e) => [e.textContent, e.getAttribute('aria-pressed')])")
        self.assertEqual(buttons, [["none", "false"], ["low", "true"], ["medium", "true"], ["default", "true"],
                                   ["high", "true"], ["xhigh", "true"], ["max", "true"]])
        page.click('#effort-buttons [data-key="max"]')
        self.assertEqual(query(page), {"hide-reasoning": "none,max"})
        self.assertEqual(self.points(page), DEFAULT_POINTS - {"claude-opus-5-5", "gpt-6-astra"})
        page.click('#effort-buttons [data-key="none"]')
        self.assertEqual(query(page), {"hide-reasoning": "max"})
        self.assertIn("claude-haiku-5-5-non-reasoning", self.points(page))
        page.click('#effort-buttons [data-key="max"]')
        self.assertEqual(query(page), {"hide-reasoning": ""})
        page.click('#effort-buttons [data-key="none"]')
        self.assertEqual(query(page), {})
        # Levels come from the selected families only.
        page.click('.model-row[data-family="claude-haiku-5-5"]')
        self.assertNotIn("none", self.texts(page, "#effort-buttons button"))
        enabled = page.locator('#effort-buttons [aria-pressed="true"]')
        while enabled.count():
            enabled.first.click()
        self.assertEqual(page.text_content("#empty-title"), "No reasoning levels enabled")
        self.assertEqual(self.points(page), set())
        # "Reset filters" restores the default selection and reasoning levels, not chart options.
        page.click("#scale-linear")
        self.assertTrue(page.is_hidden("#empty-text"))
        page.click("#empty-action:text-is('Reset filters')")
        self.assertEqual(self.points(page), DEFAULT_POINTS)
        self.assertEqual(query(page), {"linear": "true"})

    def test_tier_and_all_toggles(self):
        page = self.open()
        tiers = lambda: dict(page.eval_on_selector_all(
            ".model-section [data-set]", "els => els.map((e) => [e.dataset.set, e.getAttribute('aria-pressed')])"))
        self.assertEqual(tiers(), {"Small": "true", "Medium": "false", "Large": "true", "notable": "false"})
        page.click('[data-set="Medium"]')
        self.assertEqual(tiers()["Medium"], "true")
        self.assertEqual(page.text_content("#model-count"), "9")
        self.assertIn("claude-sonnet-5-5", query(page)["models"].split(","))
        page.click('[data-set="Medium"]')
        self.assertEqual(tiers()["Medium"], "false")
        self.assertFalse({"gpt-6-1-sol", "claude-sonnet-5-5"} & set(query(page)["models"].split(",")))
        page.click('[data-set="Large"]')
        self.assertEqual(set(query(page)["models"].split(",")), {"gpt-6-luna", "claude-haiku-5-5"})
        page.click('[data-set="notable"]')
        self.assertEqual(tiers()["notable"], "true")
        self.assertIn(["kimi-k3", True], self.rows(page, '.model-section[aria-label="Notable"] .model-row'))
        self.assertIn(["deepseek-v4-pro", True], self.rows(page, '.model-section[aria-label="Notable"] .model-row'))
        page.click('[data-set="notable"]')
        self.assertEqual(set(query(page)["models"].split(",")), {"gpt-6-luna", "claude-haiku-5-5"})
        page.click("#reset-selection")
        self.assertEqual(query(page), {})
        self.assertEqual(page.text_content("#model-count"), "8")

    def test_show_all_models(self):
        page = self.open()
        self.assertEqual(self.texts(page, ".model-section h3"), ["Frontier", "Notable"])
        self.assertTrue(page.is_hidden("#open-weights"))
        page.click("#show-all")
        self.assertEqual(page.text_content("#show-all"), "Hide other models")
        self.assertEqual(page.get_attribute("#show-all", "aria-expanded"), "true")
        other = '.model-section[aria-label="Other"] .model-row'
        # Open weights and deprecated families stay out of the list.
        self.assertEqual(self.rows(page, other), [["mistral-large-4", False]])
        self.assertEqual(page.text_content(f"{other} .lab-monogram"), "M")
        page.click("#open-weights")
        self.assertEqual(page.get_attribute("#open-weights", "aria-pressed"), "true")
        self.assertEqual(self.rows(page, other), [["gpt-oss-120b", False], ["mistral-large-4", False]])
        page.click(f'{other}[data-family="gpt-oss-120b"]')
        self.assertTrue({"gpt-oss-120b", "gpt-oss-120b-low"} <= self.points(page))
        page.click("#show-all")
        self.assertEqual(page.text_content("#show-all"), "Show all models")
        self.assertEqual(self.rows(page, other), [["gpt-oss-120b", True]])

    def test_context_menu_lab_show_only_and_hide(self):
        page = self.open()
        page.click('.model-row[data-family="claude-opus-5-5"]', button="right")
        self.assertTrue(page.is_visible("#context-menu"))
        self.assertEqual(page.text_content(".context-menu-title"), "Claude Opus 5.5")
        self.assertEqual(self.texts(page, "#context-menu button"), [
            "Hide this family", "Show only this family", "Show all except this family", "Highlight this family",
            "Show all Anthropic", "Hide Anthropic", "Show only Anthropic", "Show all except Anthropic",
            "Show all listed models", "Reset model selection", "Clear model selection"])
        page.click('#context-menu button:text-is("Show only Anthropic")')
        self.assertTrue(page.is_hidden("#context-menu"))
        anthropic = {"claude-opus-5-5", "claude-fable-5-1", "claude-sonnet-5-5", "claude-haiku-5-5"}
        self.assertEqual(set(query(page)["models"].split(",")), anthropic)
        self.assertEqual({p.split("-")[0] for p in self.points(page)}, {"claude"})

        # The same menu on a chart point.
        page.click('#chart [data-id="claude-sonnet-5-5"]', button="right")
        self.assertEqual(page.text_content(".context-menu-title"), "Claude Sonnet 5.5")
        page.click('#context-menu button:text-is("Hide Anthropic")')
        self.assertEqual(query(page)["models"], "")
        self.assertEqual(page.text_content("#empty-title"), "No models selected")
        self.assertEqual(self.points(page), set())

        page.click('.model-row[data-family="grok-4-7"]', button="right")
        page.click('#context-menu button:text-is("Reset model selection")')
        self.assertEqual(query(page), {})
        # The chart background has the list actions only.
        page.click("#chart", button="right", position={"x": 120, "y": 60})
        self.assertEqual(page.text_content(".context-menu-title"), "Chart")
        self.assertEqual(self.texts(page, "#context-menu button"),
                         ["Show all listed models", "Reset model selection", "Clear model selection"])
        page.keyboard.press("Escape")
        self.assertTrue(page.is_hidden("#context-menu"))

    @staticmethod
    def keyboard_menu(page, selector, x=0, y=0):
        """Open the context menu on an element as the keyboard does (Shift+F10)."""
        page.keyboard.press("Shift")
        page.eval_on_selector(selector, """(el, [x, y]) => el.dispatchEvent(new MouseEvent('contextmenu',
            { bubbles: true, cancelable: true, clientX: x, clientY: y }))""", [x, y])

    def test_context_menu_keyboard(self):
        page = self.open()
        labels = page.eval_on_selector_all(".series-label", "els => els.map((e) => e.dataset.label)")
        first = f'.series-label[data-label="{labels[0]}"]'
        page.focus(first)
        self.keyboard_menu(page, first)
        self.assertTrue(page.is_visible("#context-menu"))
        active = lambda: page.evaluate("document.activeElement.textContent")
        page.keyboard.press("ArrowDown")
        self.assertEqual(active(), "Show only this family")
        page.keyboard.press("End")
        self.assertEqual(active(), "Clear model selection")
        page.keyboard.press("Home")
        self.assertEqual(active(), "Hide this family")
        # Tab closes the menu and moves on from the label that opened it.
        page.keyboard.press("Tab")
        self.assertTrue(page.is_hidden("#context-menu"))
        self.assertEqual(page.evaluate("document.activeElement.dataset.label"), labels[1])
        # A key press that gives a position opens the menu there.
        self.keyboard_menu(page, first, 500, 300)
        self.assertEqual(page.eval_on_selector("#context-menu", "e => [e.offsetLeft, e.offsetTop]"), [500, 300])
        page.keyboard.press("Escape")

        # When the action removes the origin, focus goes to the first remaining point...
        page.focus('#chart [data-id="grok-4-7"]')
        self.keyboard_menu(page, '#chart [data-id="grok-4-7"]')
        page.keyboard.press("Enter")  # Hide this family
        self.assertNotIn("grok-4-7", self.state(page, "selected"))
        self.assertTrue(page.evaluate("document.activeElement.matches('#chart [data-id]')"))
        # ...or to the chart heading when no point is left.
        page.focus('#chart [data-id="claude-opus-5-5"]')
        self.keyboard_menu(page, '#chart [data-id="claude-opus-5-5"]')
        page.keyboard.press("ArrowDown")
        page.keyboard.press("Enter")  # Show only this family: two points, so the chart is empty
        self.assertTrue(page.is_visible("#empty-state"))
        self.assertEqual(page.evaluate("document.activeElement.id"), "chart-title")
        # A sidebar row that disappears hands focus to the first row.
        page.click("#show-all")
        page.focus('.model-row[data-family="mistral-large-4"]')
        self.keyboard_menu(page, '.model-row[data-family="mistral-large-4"]')
        page.keyboard.press("ArrowDown")
        page.keyboard.press("Enter")  # Show only this family
        page.click("#show-all")  # the Other list keeps only the selected mistral row
        self.keyboard_menu(page, '.model-row[data-family="mistral-large-4"]')
        page.keyboard.press("Enter")  # Hide this family: the row leaves the list
        self.assertEqual(page.locator('.model-row[data-family="mistral-large-4"]').count(), 0)
        self.assertEqual(page.evaluate("document.activeElement.dataset.family"), self.rows(page)[0][0])

    def test_zoom_y_leaves_out_points_outside_the_range(self):
        low = variant("gemini-4-argon-low", "gemini-4-argon", "Gemini 4 Argon", "google", "Google", "low", 35, 2.0, 30)
        page = self.open(models=MODELS + [low])
        self.assertIn("gemini-4-argon-low", self.points(page))
        page.click('#chart [data-id="gemini-4-argon-low"]')
        page.click("#zoom-toggle")
        self.assertEqual(self.ticks(page)[0], ["40", "45", "50", "55", "60"])
        # The clipped point cannot be focused or pinned; its family line still runs towards it.
        self.assertNotIn("gemini-4-argon-low", self.points(page))
        self.assertEqual(page.get_attribute('#chart g[data-family="gemini-4-argon"] > path', "d").count("L"), 1)
        self.assertTrue(page.is_hidden("#tooltip"))
        self.assertEqual(page.locator('#chart g[aria-hidden="true"] line').count(), 0)
        page.click("#zoom-toggle")
        self.assertIn("gemini-4-argon-low", self.points(page))
        self.assertEqual(page.text_content("#tooltip p"), "low · Pinned")

    def test_controls_after_models_json_fails(self):
        page = self.open(models=404)
        self.assertEqual(page.text_content("#empty-title"), "Could not load models.json")
        for selector in ('#metric-tabs [data-key="coding_index"]', "#zoom-toggle", "#pareto-toggle", "#scale-linear",
                         "#deprecated-toggle", "#reset-selection", "#table-button", "#table-button", "#theme-toggle",
                         "#show-all"):
            page.click(selector)
        page.fill("#model-search", "gem")
        self.set_slider(page, 50)
        page.eval_on_selector("#chart", """(e) => e.dispatchEvent(new MouseEvent('contextmenu',
            { bubbles: true, cancelable: true, clientX: 300, clientY: 300 }))""")
        page.keyboard.press("Escape")
        page.keyboard.press("/")
        self.assertEqual(page.text_content("#empty-title"), "Could not load models.json")
        self.assertTrue(page.is_hidden("#context-menu"))

    # ---------- Chart ----------
    def test_long_labels_fit_the_chart(self):
        long = [variant("nemotron-nano", "nemotron-nano", "NVIDIA Nemotron 3 Nano 30B A3B Reasoning", "nvidia",
                        "NVIDIA", "default", 47, 0.08, 40),
                variant("gpt-instant", "gpt-instant", "GPT-5.5 Instant (June 2026) Extended Preview", *OPENAI,
                        "none", 41, 0.07, 9)]
        page = self.open("?models=nemotron-nano,gpt-instant,grok-4-7&hide-reasoning=", models=MODELS + long)
        right = page.eval_on_selector("#chart", "e => e.getBoundingClientRect().right")
        labels = {row[0]: row[1:] for row in page.eval_on_selector_all(".series-label", """els => els.map((g) => {
            const t = g.querySelector('text');
            return [g.dataset.label, t.textContent, t.getAttribute('x'), t.getBoundingClientRect().right,
                    g.querySelector('title')?.textContent ?? null, g.querySelectorAll('use').length]; })""")}
        self.assertEqual(set(labels), {"nemotron-nano", "gpt-instant", "grok-4-7"})
        for family, (text, x, text_right, title, logos) in labels.items():
            self.assertLessEqual(text_right, right + 0.5, family)
        # Cut with an ellipsis, with the full name as the title. A lab without a logo has no mark.
        text, x, _, title, logos = labels["nemotron-nano"]
        self.assertTrue(text.endswith("…") and "NVIDIA Nemotron".startswith(text[:15]), text)
        self.assertEqual([x, title, logos], ["27", "NVIDIA Nemotron 3 Nano 30B A3B Reasoning", 0])
        self.assertTrue(labels["gpt-instant"][0].endswith("…"))
        self.assertEqual(labels["gpt-instant"][1:2] + labels["gpt-instant"][3:], ["53", "GPT-5.5 Instant (June 2026) Extended Preview", 1])
        self.assertEqual(labels["grok-4-7"][0:2] + labels["grok-4-7"][3:], ["Grok 4.7", "53", None, 1])

    def test_hover_tooltip_rows(self):
        page = self.open()
        page.hover('#chart [data-id="claude-opus-5-5"]')
        self.assertTrue(page.is_visible("#tooltip"))
        self.assertEqual(page.text_content("#tooltip .tooltip-head strong"), "Claude Opus 5.5")
        self.assertEqual(page.text_content("#tooltip p"), "max")
        self.assertEqual(self.tooltip_rows(page), [
            ["Intelligence index", "58", None], ["Cost per task", "$6.00", None],
            ["Response time", "600 s", None], ["Output speed", "96 tok/s", None]])
        self.assertEqual(page.get_attribute("#tooltip a", "href"), "https://artificialanalysis.ai/models/claude-opus-5-5")
        self.assertEqual(page.text_content("#tooltip a"), "Artificial Analysis")
        # Crosshair labels at the axes.
        overlay = page.eval_on_selector_all('#chart g[aria-hidden="true"] text', "els => els.map((e) => e.textContent)")
        self.assertEqual(overlay, ["58", "$6.00"])

        page.hover('#chart [data-id="gpt-6-luna"]')
        self.assertEqual(self.tooltip_rows(page), [
            ["Intelligence index", "45", None], ["Cost per task", "$0.05", None],
            ["Response time", "—", None], ["Output speed", "—", None]])
        page.mouse.move(5, 5)
        self.assertTrue(page.is_hidden("#tooltip"))

    def test_pin_and_compare(self):
        page = self.open()
        page.click('#chart [data-id="claude-opus-5-5"]')
        self.assertEqual(self.state(page, "pinned"), "claude-opus-5-5")
        self.assertEqual(page.get_attribute('#chart [data-id="claude-opus-5-5"]', "aria-pressed"), "true")
        page.mouse.move(5, 5)
        self.assertEqual(page.text_content("#tooltip p"), "max · Pinned")

        page.hover('#chart [data-id="grok-4-7"]')
        self.assertIn("comparing", page.get_attribute("#tooltip", "class"))
        self.assertEqual(page.text_content("#tooltip .tooltip-head strong"), "Grok 4.7")
        self.assertEqual(page.text_content(".comparison-reference"), "vs Claude Opus 5.5 · max")
        self.assertEqual(self.texts(page, ".comparison-table thead th"), ["Metric", "Selected", "Hovered", "Multiplier"])
        compare = lambda: page.eval_on_selector_all(
            ".comparison-table tbody tr:not(.comparison-note)", "els => els.map((r) => [...r.children].map((c) => c.textContent))")
        self.assertEqual(compare(), [
            ["Intelligence index", "58", "48", "0.828×"],
            ["Cost per task", "$6.00", "$0.60", "0.1×"],
            ["Response time", "600 s", "60 s", "0.1×"],
            ["Output speed", "96 tok/s", "100 tok/s", "1.04×"]])
        # Both crosshairs: the pinned one solid, the hovered one dashed.
        self.assertEqual(page.locator('#chart g[aria-hidden="true"] line').count(), 4)

        page.hover('#chart [data-id="gpt-6-luna"]')
        self.assertEqual(compare()[2], ["Response time", "600 s", "—", "—"])
        # With a plan, the comparison adds the API cost.
        page.click('#plan-sections [data-plan="claude-max-5x"]')
        page.hover('#chart [data-id="grok-4-7"]')
        self.assertEqual(compare()[1:3], [["Cost per task", "$1.20", "$0.60", "0.5×"],
                                          ["API cost per task", "$6.00", "$0.60", "0.1×"]])

        page.mouse.move(5, 5)
        self.assertNotIn("comparing", page.get_attribute("#tooltip", "class"))
        page.click('#tooltip button[data-key="close"]')
        self.assertIsNone(self.state(page, "pinned"))
        self.assertTrue(page.is_hidden("#tooltip"))
        # Clicking a pinned point again unpins it.
        page.click('#chart [data-id="grok-4-7"]')
        page.click('#chart [data-id="grok-4-7"]')
        self.assertIsNone(self.state(page, "pinned"))

    def test_keyboard_focus_wins_over_a_resting_mouse(self):
        page = self.open()
        chart = page.locator("#chart").bounding_box()
        page.mouse.move(chart["x"] + 200, chart["y"] + 60)  # the plot background
        page.focus('#chart [data-id="claude-opus-5-5-high"]')
        self.settle(page)
        self.assertEqual(self.state(page, "hovered"), "claude-opus-5-5-high")
        self.assertEqual(page.text_content("#tooltip p"), "high")
        page.keyboard.press("Tab")
        self.settle(page)
        self.assertEqual(self.state(page, "hovered"), "claude-opus-5-5")
        # Enter pins, and the next focused point is compared with the pinned one.
        page.keyboard.press("Enter")
        page.keyboard.press("Tab")
        self.settle(page)
        self.assertEqual(self.state(page, "hovered"), "gemini-4-argon")
        self.assertIn("comparing", page.get_attribute("#tooltip", "class"))
        # A label's focus emphasis survives too.
        page.focus('.series-label[data-label="grok-4-7"]')
        self.settle(page)
        self.assertEqual(self.state(page, "labelHover"), "grok-4-7")

        # The mouse resting on another point does not take over from the focused one.
        page = self.open()
        page.hover('#chart [data-id="gpt-6-luna"]')
        page.focus('#chart [data-id="claude-opus-5-5"]')
        self.settle(page)
        self.assertEqual(self.state(page, "hovered"), "claude-opus-5-5")
        self.assertEqual(page.text_content("#tooltip .tooltip-head strong"), "Claude Opus 5.5")

    def test_escape_and_unpin_clear_hover_under_a_resting_mouse(self):
        page = self.open()
        page.click('#chart [data-id="claude-opus-5-5"]')
        self.settle(page)
        page.keyboard.press("Escape")
        self.settle(page)
        self.assertEqual([self.state(page, "pinned"), self.state(page, "hovered")], [None, None])
        self.assertTrue(page.is_hidden("#tooltip"))
        # Clicking the pinned point unpins it and leaves no hover behind.
        page.click('#chart [data-id="grok-4-7"]')
        self.assertEqual(self.state(page, "pinned"), "grok-4-7")
        page.click('#chart [data-id="grok-4-7"]')
        self.settle(page)
        self.assertEqual([self.state(page, "pinned"), self.state(page, "hovered")], [None, None])
        self.assertTrue(page.is_hidden("#tooltip"))
        # Label hover ends with Escape too.
        page.hover('.series-label[data-label="grok-4-7"]')
        self.assertEqual(self.state(page, "labelHover"), "grok-4-7")
        page.keyboard.press("Escape")
        self.settle(page)
        self.assertIsNone(self.state(page, "labelHover"))
        # In fallback full screen, the second Escape leaves it while the mouse rests on a point.
        page.evaluate("Object.defineProperty(document, 'fullscreenEnabled', { value: false, configurable: true })")
        page.click("#fullscreen-button")
        page.hover('#chart [data-id="gemini-4-argon"]')
        self.assertEqual(self.state(page, "hovered"), "gemini-4-argon")
        page.keyboard.press("Escape")
        self.settle(page)
        self.assertIsNone(self.state(page, "hovered"))
        self.assertTrue(self.state(page, "fallbackFullscreen"))
        page.keyboard.press("Escape")
        self.assertFalse(self.state(page, "fallbackFullscreen"))

    def test_context_menu_and_hover(self):
        page = self.open()
        # Hover keeps working while the menu is open.
        page.click('.model-row[data-family="grok-4-7"]', button="right")
        page.hover('#chart [data-id="gemini-4-argon"]')
        self.assertEqual(self.state(page, "hovered"), "gemini-4-argon")
        page.hover('.model-row[data-family="gpt-6-1-sol"]')
        self.assertEqual(self.state(page, "focusFamily"), "gpt-6-1-sol")
        self.assertTrue(page.is_visible("#context-menu"))
        page.keyboard.press("Escape")
        page.mouse.move(5, 5)
        # Closing a menu opened on a point focuses the point, which shows its details.
        page.click('#chart [data-id="grok-4-7"]', button="right")
        self.assertIsNone(self.state(page, "hovered"))
        page.keyboard.press("Escape")
        self.assertTrue(page.is_hidden("#context-menu"))
        self.assertEqual(page.evaluate("document.activeElement.dataset.id"), "grok-4-7")
        self.assertEqual(self.state(page, "hovered"), "grok-4-7")
        self.assertEqual(page.text_content("#tooltip .tooltip-head strong"), "Grok 4.7")

    def test_row_focus_survives_the_mouse_over_a_heading(self):
        page = self.open()
        page.focus("#model-search")
        # Tab to the row, so that it matches :focus-visible.
        for _ in range(40):
            page.keyboard.press("Tab")
            if page.evaluate("document.activeElement.dataset.family") == "gpt-6-1-sol":
                break
        self.assertEqual(self.state(page, "focusFamily"), "gpt-6-1-sol")
        page.hover('.model-section[aria-label="Notable"] h3')
        self.assertEqual(self.state(page, "focusFamily"), "gpt-6-1-sol")
        # A row under the mouse takes over, and leaving it hands back to the focused row.
        page.hover('.model-row[data-family="grok-4-7"]')
        self.assertEqual(self.state(page, "focusFamily"), "grok-4-7")
        page.hover('.model-section[aria-label="Notable"] h3')
        self.assertIsNone(self.state(page, "focusFamily"))

    def test_touch_taps_on_the_desktop_layout(self):
        page = self.open(viewport={"width": 1280, "height": 800}, has_touch=True)
        self.assertFalse(self.state(page, "compact"))
        page.tap('#chart [data-id="claude-opus-5-5"]')
        self.assertEqual(self.state(page, "pinned"), "claude-opus-5-5")
        self.assertEqual(page.text_content("#tooltip p"), "max · Pinned")
        page.tap('.series-label[data-label="grok-4-7"]')
        self.assertEqual(self.state(page, "highlights"), ["grok-4-7"])
        self.assertEqual(page.get_attribute('.series-label[data-label="grok-4-7"]', "aria-pressed"), "true")

    def test_long_press_without_a_click_then_menu_tap(self):
        page = self.open(viewport=MOBILE, has_touch=True)
        page.tap("#sheet-toggle")
        row = page.locator('.model-row[data-family="grok-4-7"]')
        box = row.bounding_box()
        point = {"pointerType": "touch", "isPrimary": True, "bubbles": True,
                 "clientX": box["x"] + 20, "clientY": box["y"] + box["height"] / 2}
        # A long press that ends with no click, as in Chrome on Android.
        row.dispatch_event("pointerdown", point)
        page.wait_for_selector("#context-menu:not([hidden])")
        page.evaluate("(p) => window.dispatchEvent(new PointerEvent('pointercancel', p))", point)
        page.tap('#context-menu button:text-is("Highlight this family")')
        self.assertTrue(page.is_hidden("#context-menu"))
        self.assertEqual(self.state(page, "highlights"), ["grok-4-7"])

    def test_escape_priority_chain(self):
        page = self.open()
        page.click('#chart [data-id="claude-opus-5-5"]')
        page.click('.series-label[data-label="grok-4-7"]')
        self.assertEqual(self.state(page, "highlights"), ["grok-4-7"])
        page.fill("#model-search", "gem")
        page.evaluate("Object.defineProperty(document, 'fullscreenEnabled', { value: false, configurable: true })")
        page.click("#fullscreen-button")
        self.assertTrue(self.state(page, "fallbackFullscreen"))
        self.assertEqual(page.get_attribute("#fullscreen-button", "aria-pressed"), "true")
        page.click('.model-row[data-family="gemini-4-argon"]', button="right")
        self.assertTrue(page.is_visible("#context-menu"))

        def snapshot():
            return [page.is_visible("#context-menu"), page.is_visible("#help-popover"),
                    self.state(page, "query"), self.state(page, "pinned"),
                    self.state(page, "highlights"), self.state(page, "fallbackFullscreen")]

        page.keyboard.press("Escape")
        self.assertEqual(snapshot(), [False, False, "gem", "claude-opus-5-5", ["grok-4-7"], True])
        self.assertEqual(page.evaluate("document.activeElement.dataset.family"), "gemini-4-argon")
        page.click("#help-button")
        self.assertTrue(page.is_visible("#help-popover"))
        page.keyboard.press("Escape")
        self.assertEqual(snapshot(), [False, False, "gem", "claude-opus-5-5", ["grok-4-7"], True])
        self.assertEqual(page.evaluate("document.activeElement.id"), "help-button")
        page.keyboard.press("Escape")
        self.assertEqual(snapshot(), [False, False, "", "claude-opus-5-5", ["grok-4-7"], True])
        self.assertEqual(page.input_value("#model-search"), "")
        page.keyboard.press("Escape")
        self.assertEqual(snapshot(), [False, False, "", None, [], True])
        self.assertTrue(page.is_hidden("#tooltip"))
        page.keyboard.press("Escape")
        self.assertEqual(snapshot(), [False, False, "", None, [], False])
        self.assertFalse(page.evaluate("document.getElementById('app').classList.contains('fullscreen-fallback')"))
        page.keyboard.press("Escape")
        self.assertEqual(snapshot(), [False, False, "", None, [], False])

    def test_help_popover(self):
        page = self.open()
        page.focus("#help-button")
        page.keyboard.press("Enter")
        self.assertTrue(page.is_visible("#help-popover"))
        self.assertIsNone(page.get_attribute("#help-popover", "role"))
        self.assertEqual(page.get_attribute("#help-button", "aria-expanded"), "true")
        text = " ".join(page.text_content("#help-popover").split())
        self.assertIn("On a touch screen, tap near a variant to pin it", text)
        self.assertIn("each tenfold step in cost takes the same width", text)
        self.assertIn("scores higher than every visible variant that costs less, and no variant at the same cost"
                      " scores higher. When variants tie on both cost and score, one of them is on the line.", text)
        self.assertIn("Deprecated models are hidden unless Show deprecated is on", text)
        # Focus moving on inside the popover keeps it open; leaving it closes it.
        page.keyboard.press("Tab")
        self.assertTrue(page.is_visible("#help-popover"))
        page.focus("#theme-toggle")
        self.assertTrue(page.is_hidden("#help-popover"))
        self.assertEqual(page.get_attribute("#help-button", "aria-expanded"), "false")

    def test_table_view(self):
        page = self.open()
        page.click("#table-button")
        self.assertEqual(page.get_attribute("#table-button", "aria-pressed"), "true")
        self.assertTrue(page.is_hidden("#chart-wrap"))
        self.assertTrue(page.is_visible("#table-view"))
        self.assertTrue(page.is_disabled("#png-button"))
        self.assertEqual(self.texts(page, "#data-table thead th"), [
            "Model", "Reasoning", "Intelligence", "Coding (SciCode)", "Math (AIME 2025)", "Terminal-Bench v4.0",
            "LiveBench Coding", "LiveBench Agentic Coding", "Cost per task", "Response time", "Pareto"])
        self.assertEqual(page.text_content("#table-caption"), "10 variants, highest Intelligence index first.")
        table = self.table(page)
        self.assertEqual(list(table), [
            "Claude Opus 5.5 (max)", "GPT-6 Astra (max)", "Claude Opus 5.5 (high)", "Gemini 4 Argon (Default)",
            "Claude Fable 5.1 (Default)", "GPT-6.1 Sol (xhigh)", "GPT-6 Astra (medium)", "Grok 4.7 (Default)",
            "GPT-6 Luna (low)", "Claude Haiku 5.5 (low)"])
        self.assertEqual({name for name, cells in table.items() if cells[-1][0] == "Yes"},
                         {"Claude Opus 5.5 (max)", "GPT-6 Astra (max)", "Claude Opus 5.5 (high)",
                          "Gemini 4 Argon (Default)", "GPT-6.1 Sol (xhigh)", "Grok 4.7 (Default)", "GPT-6 Luna (low)"})
        self.assertEqual(table["GPT-6 Astra (max)"][1:8], [
            ["57", None], ["47", None], ["—", None], ["—", None], ["80.5", "2/2 subtasks"], ["57.3", "3/3 subtasks"],
            ["$3.00", None]])
        self.assertEqual(table["GPT-6 Luna (low)"][-2], ["—", None])
        # The lab is text under the model name; LiveBench cells name their source model.
        self.assertEqual(page.text_content("#data-table tbody tr:first-child th small"), "Anthropic")
        astra = page.locator("#data-table tbody tr", has_text="GPT-6 Astra").first
        self.assertEqual(astra.locator("td").nth(5).locator("small").all_text_contents(),
                         ["2/2 subtasks", "gpt-6-astra-max"])

        # Sidebar filters, the speed limit and the benchmark apply.
        page.click('.model-row[data-family="claude-opus-5-5"]')
        self.assertEqual(len(self.table(page)), 8)
        self.set_slider(page, 125)
        self.assertEqual(page.text_content("#table-caption"),
                         "4 variants, highest Intelligence index first. 4 hidden by the response time limit.")
        self.set_slider(page, 200)
        page.click('#metric-tabs [data-key="livebench_coding"]')
        self.assertEqual(list(self.table(page)), ["GPT-6 Astra (max)", "GPT-6 Astra (medium)"])
        self.assertEqual(page.text_content("#table-caption"),
                         "2 variants, highest LiveBench Coding score first. LiveBench release 2026_06_25.")
        self.assertEqual(page.get_attribute("#data-table thead th:nth-child(7)", "aria-sort"), "descending")
        page.click('#metric-tabs [data-key="math_index"]')
        self.assertEqual(page.text_content("#table-caption"), "None of the selected variants has Math (AIME 2025) data.")

        page.click("#table-button")
        self.assertTrue(page.is_visible("#chart-wrap"))
        self.assertTrue(page.is_hidden("#table-view"))

    def test_png_export(self):
        page = self.open("?metric=coding_index")
        with page.expect_download() as info:
            page.click("#png-button")
        download = info.value
        self.assertEqual(download.suggested_filename, "intelligence-vs-cost-coding-index.png")
        data = Path(download.path()).read_bytes()
        self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
        width, height = struct.unpack(">II", data[16:24])
        box = page.evaluate("(() => { const b = document.getElementById('chart').viewBox.baseVal; return [b.width, b.height]; })()")
        # Twice the chart size, with a 44 px title band on top.
        self.assertEqual([width, height], [2 * box[0], 2 * (box[1] + 44)])
        self.assertEqual(page.get_attribute("#png-button", "title"), "Download PNG")
        self.assertTrue(page.is_enabled("#png-button"))

    def test_resize_across_the_breakpoint(self):
        page = self.open()
        page.click('#chart [data-id="grok-4-7"]')
        chart_width = "document.getElementById('chart').viewBox.baseVal.width"
        page.set_viewport_size(MOBILE)
        page.wait_for_function(f"__chart.state.compact && {chart_width} < {MOBILE['width']}")
        self.assertEqual(page.locator(".series-label").count(), 0)
        self.assertEqual(page.locator("#chart-legend button").count(), 8)
        self.assertTrue(page.is_hidden("#sidebar"))
        self.assertTrue(page.is_hidden("#png-button"))
        self.assertEqual(self.state(page, "pinned"), "grok-4-7")
        self.assertEqual(page.eval_on_selector("#tooltip", "e => getComputedStyle(e).position"), "sticky")
        page.click("#sheet-toggle")
        self.assertTrue(page.is_visible("#sidebar"))
        self.assertTrue(page.evaluate("document.getElementById('app-header').inert"))

        page.set_viewport_size(DESKTOP)
        page.wait_for_function(f"!__chart.state.compact && {chart_width} > 1000")
        self.assertEqual(page.locator(".series-label").count(), 8)
        self.assertTrue(page.is_hidden("#chart-legend"))
        self.assertTrue(page.is_visible("#sidebar"))
        self.assertFalse(self.state(page, "sheetOpen"))
        self.assertFalse(page.evaluate("document.getElementById('app-header').inert"))
        self.assertEqual(page.eval_on_selector("#tooltip", "e => getComputedStyle(e).position"), "absolute")
        self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), DESKTOP["width"])

    def test_theme_follows_system_and_persists(self):
        page = self.open(color_scheme="light")
        html = lambda: page.get_attribute("html", "data-theme")
        background = lambda: page.get_attribute("#chart > rect", "fill")
        meta = lambda: page.get_attribute('meta[name="theme-color"]', "content")
        self.assertEqual(html(), "light")
        self.assertEqual(background(), "#fff")
        self.assertEqual(meta(), "#ffffff")
        page.emulate_media(color_scheme="dark")
        page.wait_for_function("document.documentElement.dataset.theme === 'dark'")
        self.assertEqual(background(), "#000")
        self.assertEqual(meta(), "#000000")
        self.assertEqual(page.get_attribute("#theme-toggle", "aria-label"), "Switch to light mode")

        page.click("#theme-toggle")
        self.assertEqual(html(), "light")
        self.assertEqual(background(), "#fff")
        self.assertEqual(page.evaluate("localStorage.getItem('theme')"), "light")
        # A stored choice wins over the system setting, also after a reload.
        page.emulate_media(color_scheme="dark")
        page.wait_for_timeout(100)
        self.assertEqual(html(), "light")
        page.reload()
        self.ready(page)
        self.assertEqual(html(), "light")
        self.assertEqual(background(), "#fff")
        self.assertEqual(meta(), "#ffffff")
        self.assertNotIn("theme", page.url)

    def test_url_round_trip_through_reload(self):
        search = ("?ref=x&metric=coding_index&models=claude-opus-5-5,gpt-6-astra,grok-4-7,claude-sonnet-5"
                  "&hide-reasoning=none,medium&frontier=false&linear=true&labels=false&claude_plan=claude-max-5x"
                  "&codex_plan=chatgpt-pro&max_response_time=250&deprecated=true")
        page = self.open(search)

        def check():
            self.assertEqual(urlsplit(page.url).query, search[1:])
            self.assertEqual(page.get_attribute('#metric-tabs [data-key="coding_index"]', "aria-current"), "true")
            self.assertEqual(page.text_content("#model-count"), "4")
            self.assertEqual({f for f, on in self.rows(page) if on},
                             {"claude-opus-5-5", "gpt-6-astra", "grok-4-7", "claude-sonnet-5"})
            efforts = dict(page.eval_on_selector_all(
                "#effort-buttons button", "els => els.map((e) => [e.dataset.key, e.getAttribute('aria-pressed')])"))
            self.assertEqual(efforts["medium"], "false")
            self.assertEqual(efforts["max"], "true")
            for selector, pressed in [("#pareto-toggle", "false"), ("#scale-linear", "true"),
                                      ("#deprecated-toggle", "true"), ('[data-plan="claude-max-5x"]', "true"),
                                      ('[data-plan="chatgpt-pro"]', "true")]:
                self.assertEqual(page.get_attribute(selector, "aria-pressed"), pressed, selector)
            self.assertEqual(page.locator(".series-label").count(), 0)
            self.assertEqual(page.text_content("#time-readout"), "≤ 250 s · 3 hidden")
            self.assertEqual(self.points(page), {"claude-sonnet-5-high", "claude-sonnet-5", "grok-4-7"})

        check()
        page.reload()
        self.ready(page)
        check()

        # State changed through the controls survives a reload too.
        page.click('#metric-tabs [data-key="intelligence_index"]')
        page.click("#pareto-toggle")
        page.click("#scale-log")
        page.click('.model-row[data-family="grok-4-7"]')
        page.click('#plan-sections [data-plan="chatgpt-plus"]')
        url = page.url
        self.assertEqual(urlsplit(url).query,
                         "ref=x&models=claude-opus-5-5,gpt-6-astra,claude-sonnet-5&hide-reasoning=none,medium"
                         "&labels=false&claude_plan=claude-max-5x&codex_plan=chatgpt-plus&max_response_time=250"
                         "&deprecated=true")
        page.reload()
        self.ready(page)
        self.assertEqual(page.url, url)
        self.assertEqual(page.get_attribute("#pareto-toggle", "aria-pressed"), "true")
        self.assertEqual(page.get_attribute('[data-plan="chatgpt-plus"]', "aria-pressed"), "true")

    @staticmethod
    def touch_state(page):
        """A change and its undo: the page then writes its state to the URL."""
        page.click("#scale-linear")
        page.click("#scale-log")

    def test_unknown_url_values_fall_back_to_defaults(self):
        # The address bar keeps the link as typed until the user changes something.
        page = self.open("?models=old-model,another-old-one")
        self.assertEqual(set(self.state(page, "selected")), DEFAULT_FAMILIES)
        self.assertEqual(query(page), {"models": "old-model,another-old-one"})
        self.assertEqual(self.points(page), DEFAULT_POINTS)
        self.touch_state(page)
        self.assertEqual(query(page), {})

        page = self.open("?models=old-model,grok-4-7,grok-4-7")
        self.assertEqual(self.state(page, "selected"), ["grok-4-7"])
        self.assertEqual(page.text_content("#empty-title"), "Only 1 selected model has Intelligence data")
        self.touch_state(page)
        self.assertEqual(query(page), {"models": "grok-4-7"})

        page = self.open("?models=")
        self.assertEqual(self.state(page, "selected"), [])
        self.assertEqual(page.text_content("#empty-title"), "No models selected")
        self.assertEqual(query(page), {"models": ""})
        page.click('#metric-tabs [data-key="coding_index"]')
        page.click('.model-row[data-family="grok-4-7"]', button="right")
        page.click('#context-menu button:text-is("Highlight this family")')
        page.fill("#model-search", "gem")
        page.click("#empty-action:text-is('Reset filters')")
        self.assertEqual(set(self.state(page, "selected")), DEFAULT_FAMILIES)
        self.assertEqual([self.state(page, "query"), self.state(page, "highlights")], ["", []])
        self.assertEqual(query(page), {"metric": "coding_index"})

        # As in slopalytics: a boolean is true only for "true", and a list keeps its known
        # names, so an unknown reasoning level shows every level.
        page = self.open("?metric=coding_index_v2&claude_plan=max-100x&max_response_time=-5&frontier=maybe"
                         "&linear=1&hide-reasoning=ultra")
        self.assertEqual(self.state(page, "metric"), "intelligence_index")
        self.assertEqual(self.state(page, "plans"), {"claude": "claude-api", "codex": "chatgpt-api"})
        self.assertEqual(self.state(page, "excluded"), [])
        self.assertFalse(self.state(page, "frontier"))
        self.assertFalse(self.state(page, "linear"))
        self.assertIn("claude-haiku-5-5-non-reasoning", self.points(page))
        self.assertEqual(page.text_content("#time-readout"), "No limit")
        self.touch_state(page)
        self.assertEqual(query(page), {"frontier": "false", "hide-reasoning": ""})
        # Known values are read in any case. A fractional limit snaps to whole seconds.
        page = self.open("?frontier=FALSE&hide-reasoning=ultra,max&labels=0&max_response_time=12.5")
        self.assertEqual(self.state(page, "excluded"), ["max"])
        self.assertFalse(self.state(page, "labels"))
        self.assertEqual(self.state(page, "maxTime"), 13)
        self.assertTrue(page.text_content("#time-readout").startswith("≤ 13 s · "))
        self.touch_state(page)
        self.assertEqual(query(page), {"frontier": "false", "hide-reasoning": "max", "labels": "false",
                                       "max_response_time": "13"})

    def test_url_keeps_parameter_order(self):
        search = "?models=bogus,gpt-6-astra,grok-4-7&frontier=TRUE&ref=1"
        page = self.open(search)
        self.assertEqual(urlsplit(page.url).query, search[1:])
        page.click("#scale-linear")
        # Existing keys stay in place, defaults drop out, new keys go last.
        self.assertEqual(urlsplit(page.url).query, "models=gpt-6-astra,grok-4-7&ref=1&linear=true")
        page = self.open("?labels=false")
        page.click('.model-row[data-family="claude-sonnet-5-5"]')
        self.assertTrue(urlsplit(page.url).query.startswith("labels=false&models=gpt-6-astra,"), page.url)

    def test_slider_drag_writes_the_url_once(self):
        page = self.open()
        page.evaluate("""() => { window.__writes = 0; const replace = history.replaceState.bind(history);
            history.replaceState = (...args) => { window.__writes++; return replace(...args); }; }""")
        # Safari allows 100 replaceState calls in 10 seconds; a drag sends more input events.
        page.eval_on_selector("#time-slider", """(el) => { for (let v = 199; v >= 100; v--) {
            el.value = v; el.dispatchEvent(new Event('input', { bubbles: true })); } }""")
        self.assertEqual(page.evaluate("window.__writes"), 0)
        page.wait_for_function("window.__writes === 1")
        self.assertEqual(query(page), {"max_response_time": str(self.state(page, "maxTime"))})
        # Releasing the slider writes at once.
        self.set_slider(page, 125)
        self.assertEqual(query(page), {"max_response_time": "100"})
        self.assertEqual(page.evaluate("window.__writes"), 2)

    # ---------- Mobile ----------
    def test_mobile_escape_closes_sheet_before_clearing_focused_search(self):
        page = self.open(viewport=MOBILE, has_touch=True)
        page.tap("#sheet-toggle")
        page.fill("#model-search", "opus")
        self.assertEqual(page.evaluate("document.activeElement.id"), "model-search")
        page.keyboard.press("Escape")
        self.assertTrue(page.is_hidden("#sidebar"))
        self.assertFalse(self.state(page, "sheetOpen"))
        self.assertEqual(self.state(page, "query"), "opus")
        self.assertEqual(page.input_value("#model-search"), "opus")
        self.assertEqual(page.evaluate("document.activeElement.id"), "sheet-toggle")
        page.keyboard.press("Escape")
        self.assertTrue(page.is_hidden("#sidebar"))
        self.assertEqual(self.state(page, "query"), "")
        self.assertEqual(page.input_value("#model-search"), "")

    def test_mobile_sheet_and_tap_to_pin(self):
        page = self.open(viewport=MOBILE, has_touch=True)
        self.assertTrue(self.state(page, "compact"))
        self.assertTrue(page.is_hidden("#sidebar"))
        self.assertEqual(" ".join(page.text_content("#sheet-toggle").split()), "Models 8")
        self.assertEqual(page.locator(".series-label").count(), 0)
        self.assertEqual(page.locator("#chart-legend button").count(), 8)

        page.tap("#sheet-toggle")
        self.assertTrue(page.is_visible("#sidebar"))
        self.assertEqual(page.get_attribute("#sheet-toggle", "aria-expanded"), "true")
        self.assertEqual(page.get_attribute("#sidebar", "role"), "dialog")
        # Focus moves into the modal sheet; the slider is a touch-sized target.
        self.assertEqual(page.evaluate("document.activeElement.id"), "sheet-done")
        self.assertGreaterEqual(page.eval_on_selector("#time-slider", "e => e.offsetHeight"), 32)
        self.assertTrue(page.is_visible('#plan-sections [data-plan="claude-max-20x"]'))
        self.assertTrue(page.is_visible("#time-slider"))
        page.tap('.model-row[data-family="grok-4-7"]')
        self.assertEqual(" ".join(page.text_content("#sheet-toggle").split()), "Models 7")
        page.tap('.model-row[data-family="grok-4-7"]')
        page.keyboard.press("Escape")
        self.assertTrue(page.is_hidden("#sidebar"))
        page.tap("#sheet-toggle")
        page.tap("#sheet-done")
        self.assertTrue(page.is_hidden("#sidebar"))
        self.assertEqual(page.get_attribute("#sheet-toggle", "aria-expanded"), "false")
        page.keyboard.press("/")
        self.assertTrue(page.is_visible("#sidebar"))
        self.assertEqual(page.evaluate("document.activeElement.id"), "model-search")
        page.keyboard.press("Escape")
        self.assertTrue(page.is_hidden("#sidebar"))
        self.assertEqual(page.evaluate("document.activeElement.id"), "sheet-toggle")

        # A legend tap highlights the family, a second tap clears it.
        page.tap('#chart-legend [data-family="grok-4-7"]')
        self.assertEqual(self.state(page, "highlights"), ["grok-4-7"])
        page.tap('#chart-legend [data-family="grok-4-7"]')
        self.assertEqual(self.state(page, "highlights"), [])

        # A tap pins the nearest point within 40 px; points ignore the pointer.
        box = page.locator('#chart [data-id="gpt-6-luna"] circle:last-child').bounding_box()
        x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        page.touchscreen.tap(x + 8, y - 8)
        self.assertEqual(self.state(page, "pinned"), "gpt-6-luna")
        self.assertTrue(page.is_visible("#tooltip"))
        self.assertEqual(page.text_content("#tooltip p"), "low · Pinned")
        self.assertEqual(page.eval_on_selector("#tooltip", "e => getComputedStyle(e).position"), "sticky")
        # Taps on the card stay on the card.
        self.assertEqual(page.eval_on_selector("#tooltip", "e => getComputedStyle(e).pointerEvents"), "auto")
        chart = page.locator("#chart").bounding_box()
        page.touchscreen.tap(chart["x"] + chart["width"] - 20, chart["y"] + chart["height"] - 20)
        self.assertIsNone(self.state(page, "pinned"))
        self.assertTrue(page.is_hidden("#tooltip"))

    def test_mobile_legend_follows_emphasis(self):
        page = self.open(viewport=MOBILE, has_touch=True)
        dimmed = lambda: {f for f, dim in page.eval_on_selector_all(
            "#chart-legend button", "els => els.map((e) => [e.dataset.family, e.classList.contains('dim')])") if dim}
        # The Pareto line is on, but nothing is emphasised, so nothing is dimmed.
        self.assertEqual(dimmed(), set())
        page.tap('#chart-legend [data-family="grok-4-7"]')
        self.assertEqual(dimmed(), DEFAULT_FAMILIES - {"grok-4-7"})
        page.tap('#chart-legend [data-family="grok-4-7"]')
        self.assertEqual(dimmed(), set())
        # A pinned point dims the other families.
        box = page.locator('#chart [data-id="gpt-6-luna"] circle:last-child').bounding_box()
        page.touchscreen.tap(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        self.assertEqual(dimmed(), DEFAULT_FAMILIES - {"gpt-6-luna"})

    def test_mobile_card_and_table(self):
        page = self.open("?codex_plan=chatgpt-plus", viewport=MOBILE, has_touch=True)
        box = page.locator('#chart [data-id="gpt-6-luna"] circle:last-child').bounding_box()
        page.touchscreen.tap(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        # The plan-qualified cost label spans both card columns.
        wide = page.eval_on_selector_all("#tooltip .tooltip-value.wide", """els => els.map((e) =>
            [e.querySelector('span').textContent, getComputedStyle(e).gridColumnEnd])""")
        self.assertEqual(wide, [["Cost per task (ChatGPT Plus)", "-1"]])
        # The table scrolls inside itself: its header row and model column stay in view.
        page.tap("#table-button")
        self.assertEqual(page.eval_on_selector("#table-view", "e => getComputedStyle(e).overflowY"), "auto")
        page.eval_on_selector("#table-view", "e => { e.scrollLeft = 300; }")
        view = page.locator("#table-view").bounding_box()
        name = page.locator("#data-table tbody th").first.bounding_box()
        self.assertGreater(page.eval_on_selector("#table-view", "e => e.scrollLeft"), 0)
        self.assertAlmostEqual(name["x"], view["x"], delta=1)

    def test_compact_ticks_do_not_collide(self):
        # Plans spread the costs over four decades.
        page = self.open("?hide-reasoning=&claude_plan=claude-max-20x&codex_plan=chatgpt-pro",
                         viewport=MOBILE, has_touch=True)
        boxes = page.eval_on_selector_all('#chart g[transform] > line[y2="5"] + text', """els => els.map((e) => {
            const r = e.getBoundingClientRect(); return [r.left, r.right]; })""")
        self.assertGreater(len(boxes), 2)
        for a, b in zip(boxes, boxes[1:]):
            self.assertGreaterEqual(b[0] - a[1], 2, boxes)

    def test_default_ticks_match_slopalytics(self):
        # Slopalytics' default cost range, $0.0047 to $7.63: its own ticks fit on a phone and
        # on the narrow desktop layout, with measured label widths.
        costs = {"gpt-6-luna": 0.0047, "claude-opus-5-5": 7.63}
        models = [{**m, "cost_per_task": costs.get(m["slug"], m["cost_per_task"])} for m in MODELS]
        for viewport, ticks in ((MOBILE, ["$0.01", "$0.03", "$0.1", "$0.3", "$1", "$3"]),
                                ({"width": 1100, "height": 800},
                                 ["$0.005", "$0.01", "$0.02", "$0.05", "$0.1", "$0.2", "$0.5", "$1", "$2", "$5"])):
            page = self.open(models=models, viewport=viewport, has_touch=viewport is MOBILE)
            self.assertEqual(self.ticks(page)[1], ticks, viewport)

    def test_mobile_header(self):
        page = self.open("?metric=livebench_agentic_coding", viewport=MOBILE, has_touch=True)
        # A shared link shows its benchmark tab, scrolled into view.
        tab = page.locator('#metric-tabs [data-key="livebench_agentic_coding"]').bounding_box()
        self.assertGreaterEqual(tab["x"], 0)
        self.assertLessEqual(tab["x"] + tab["width"], MOBILE["width"])
        self.assertGreater(page.eval_on_selector("#metric-tabs", "e => e.scrollLeft"), 0)
        self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), MOBILE["width"])
        # Header icons keep 32 px touch targets.
        for button in ("#theme-toggle", "#table-button", "#help-button"):
            self.assertEqual(page.eval_on_selector(button, "e => e.offsetWidth"), 32, button)

    def test_tab_bar_fades_where_it_overflows(self):
        def fades(page):
            return page.eval_on_selector("#metric-tabs", """t => [t.classList.contains('fade-start'),
                t.classList.contains('fade-end'), getComputedStyle(t).maskImage !== 'none']""")

        page = self.open(viewport={"width": 1024, "height": 768})
        self.assertEqual(fades(page), [False, True, True])
        page.eval_on_selector("#metric-tabs", "t => { t.scrollLeft = t.scrollWidth; }")
        page.wait_for_function("document.getElementById('metric-tabs').classList.contains('fade-start')")
        self.assertEqual(fades(page), [True, False, True])
        # A shared link's tab scrolls to 16 px from the bar's start, clear of the fade.
        page = self.open("?metric=terminalbench_v4_0", viewport=MOBILE, has_touch=True)
        self.assertEqual(fades(page), [True, True, True])
        inset = page.evaluate("""() => document.querySelector('#metric-tabs [aria-current="true"]').getBoundingClientRect().left
            - document.getElementById('metric-tabs').getBoundingClientRect().left""")
        self.assertAlmostEqual(inset, 16, delta=1)

    # ---------- Pure helpers ----------
    def test_cost_formatter(self):
        page = self.open()
        cases = [[6, False, "$6.00"], [1234.5, False, "$1,234.50"], [0.1234, False, "$0.123"],
                 [0.01, False, "$0.01"], [0.0085, False, "$0.0085"], [0.0012345, False, "$0.0012"],
                 [0.004, False, "$0.004"], [0.00999, False, "$0.01"], [None, False, "—"],
                 [1500, True, "$1.5k"], [2000, True, "$2k"], [0.5, True, "$0.5"], [5, True, "$5"],
                 [0.005, True, "$0.005"], [0, True, "$0"]]
        got = page.evaluate("(cases) => cases.map(([v, short]) => __chart.fmtCost(v, short))", cases)
        self.assertEqual(got, [c[2] for c in cases])
        self.assertEqual(page.evaluate("[__chart.fmtMult(48, 58), __chart.fmtMult(1, 0), __chart.fmtMult(null, 2)]"),
                         ["0.828×", "—", "—"])
        self.assertEqual(page.evaluate("[__chart.fmtSeconds(5.04), __chart.fmtSeconds(600), __chart.fmtSpeed(96.4)]"),
                         ["5.0 s", "600 s", "96 tok/s"])

    def test_ticks(self):
        page = self.open()
        self.assertEqual(page.evaluate("__chart.niceTicks(0, 63)"), [0, 20, 40, 60])
        self.assertEqual(page.evaluate("__chart.niceTicks(0, 45)"), [0, 10, 20, 30, 40])
        self.assertEqual(page.evaluate("__chart.niceTicks(20, 60)"), [20, 30, 40, 50, 60])
        self.assertEqual(page.evaluate("__chart.niceTicks(40, 60)"), [40, 45, 50, 55, 60])
        self.assertEqual(page.evaluate("__chart.niceTicks(0, 0.35)"), [0, 0.1, 0.2, 0.3])
        self.assertEqual(page.evaluate("__chart.logTicks(0.035, 6.48)"), [0.05, 0.1, 0.2, 0.5, 1, 2, 5])
        self.assertEqual(page.evaluate("__chart.logTicks(0.035, 6.48, true)"), [0.1, 0.3, 1, 3])
        self.assertEqual(page.evaluate("__chart.logTicks(1, 10)"), [1, 1.5, 2, 3, 5, 7, 10])
        # Too little room for [1, 3] per decade: one tick per decade, then every second decade.
        fit = ("(w) => __chart.fitLogTicks(0.0002, 1.3, true, __chart.logScale([0.0002, 1.3], [40, 40 + w]),"
               " (text) => text.length * 7.2)")
        self.assertEqual(page.evaluate(f"({fit})(600)"), [0.0003, 0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1])
        self.assertEqual(page.evaluate(f"({fit})(304)"), [0.001, 0.01, 0.1, 1])
        self.assertEqual(page.evaluate(f"({fit})(150)"), [0.01, 1])
        self.assertEqual(page.evaluate("__chart.yDomain([45, 58])"), [20, 60])
        self.assertEqual(page.evaluate("__chart.yDomain([45, 58], true)"), [40, 60])

    def test_pareto_set(self):
        page = self.open()
        front = page.evaluate("""() => __chart.paretoSet([
            { id: 'a', x: 1, y: 1 }, { id: 'b', x: 2, y: 3 }, { id: 'c', x: 2, y: 2 }, { id: 'd', x: 3, y: 3 },
            { id: 'e', x: 0.5, y: 0.5 }, { id: 'f', x: 4, y: 5 }, { id: 'g', x: null, y: 9 },
            { id: 'h', x: 2, y: 3 }]).map((r) => r.id)""")
        # c is beaten at the same cost, d ties b at a higher cost, g has no cost, and of the
        # identical b and h only the first is kept.
        self.assertEqual(front, ["e", "a", "b", "f"])
        self.assertEqual(page.evaluate("__chart.paretoSet([])"), [])

    def test_effort_ordering(self):
        page = self.open()
        rows = page.evaluate("""() => {
            const row = (slug, effort, extra = {}) => ({ slug, family: 'fam', family_name: 'Fam', lab: 'acme',
                cost_per_task: 1, intelligence_index: 50, effort, ...extra });
            const data = __chart.normalise([row('m-max', 'max', { effort_order: 60 }), row('m-none', 'none'),
                row('m-high', 'high'), row('m-default', undefined, { reasoning: true }),
                row('m-minimal', 'minimal'), row('m-xhigh', 'xhigh'), row('m-low', 'low'), row('m-medium', 'medium')]);
            const fam = data.families.get('fam');
            const state = { ...__chart.state, data, selected: ['fam'], deprecated: false };
            return [fam.variants.map((v) => v.effort), __chart.effortLevels(data, state).map((l) => l.label)];
        }""")
        order = ["none", "minimal", "low", "medium", "default", "high", "xhigh", "max"]
        self.assertEqual(rows, [order, order])
        # Without an effort field: reasoning models get "default", the rest "none".
        efforts = page.evaluate("""() => __chart.normalise([
            { slug: 'r', cost_per_task: 1, reasoning: true }, { slug: 'n', cost_per_task: 1 }]).variants
            .map((v) => [v.id, v.effort, v.effortOrder])""")
        self.assertEqual(efforts, [["n", "none", 0], ["r", "default", 35]])

    def test_url_codec(self):
        page = self.open()
        result = page.evaluate("""() => {
            const known = { families: new Set(__chart.state.data.families.keys()),
                            efforts: new Set(Object.keys(__chart.CONFIG.efforts)) };
            const defaults = __chart.decodeUrl('', known);
            const custom = { ...defaults, metric: 'livebench_coding', selected: ['grok-4-7', 'kimi-k3'],
                excluded: [], frontier: false, linear: true, labels: false,
                plans: { claude: 'claude-max-20x', codex: 'chatgpt-api' }, maxTime: 90, deprecated: true };
            const encoded = __chart.encodeUrl(custom, '?keep=1&metric=x&models=y');
            const decoded = __chart.decodeUrl(encoded, known);
            return { empty: __chart.encodeUrl(defaults), encoded, same: JSON.stringify(decoded) === JSON.stringify(custom),
                     reordered: __chart.encodeUrl({ ...defaults, selected: [...defaults.selected].reverse() }) };
        }""")
        self.assertEqual(result["empty"], "")
        self.assertEqual(result["encoded"],
                         "?keep=1&metric=livebench_coding&models=grok-4-7,kimi-k3&hide-reasoning=&frontier=false"
                         "&linear=true&labels=false&claude_plan=claude-max-20x&max_response_time=90&deprecated=true")
        self.assertTrue(result["same"])
        self.assertEqual(result["reordered"], "")


@unittest.skipIf(sync_playwright is None, "playwright is not installed")
class ChromiumTests(PageTests):
    browser_name = "chromium"


@unittest.skipIf(sync_playwright is None, "playwright is not installed")
class FirefoxTests(PageTests):
    browser_name = "firefox"


# The shared base class runs only through the browser subclasses above.
del PageTests


if __name__ == "__main__":
    unittest.main()
