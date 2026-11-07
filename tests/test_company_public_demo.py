"""Verify the public company demo file and its offline browser controls."""

from base64 import b64encode
from contextlib import contextmanager
from hashlib import sha256
from html.parser import HTMLParser
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest


class _Document(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.elements = []
        self.scripts = []
        self.links = []
        self.script = None
        self.link = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))
        if tag == "script":
            self.script = ""
        if tag == "a":
            self.link = (dict(attrs).get("href"), [])

    def handle_data(self, data):
        if self.script is not None:
            self.script += data
        if self.link is not None:
            self.link[1].append(data)

    def handle_endtag(self, tag):
        if tag == "script":
            self.scripts.append(self.script)
            self.script = None
        if tag == "a" and self.link is not None:
            href, content = self.link
            self.links.append((href, " ".join("".join(content).split())))
            self.link = None


def test_demo_is_a_self_contained_explicit_cli_output(tmp_path):
    from scripts.build_company_demo import build_demo_html

    project = Path(__file__).resolve().parents[1]
    command = [sys.executable, "-m", "scripts.build_company_demo"]
    env = {**os.environ, "PYTHONPATH": str(project), "PYTHONDONTWRITEBYTECODE": "1"}
    without_output = subprocess.run(command, cwd=tmp_path, env=env, capture_output=True)
    assert without_output.returncode != 0
    assert not list(tmp_path.iterdir())

    path = tmp_path / "demo.html"
    subprocess.run([*command, "--output", str(path)], cwd=tmp_path, env=env, check=True)
    html = path.read_text(encoding="utf-8")
    assert list(tmp_path.iterdir()) == [path]
    assert html == build_demo_html()
    document = _Document(html)
    source = (project / "scripts" / "company_demo_interactions.js").read_text(encoding="utf-8")
    assert document.scripts == [source]
    policy, = [attrs["content"] for tag, attrs in document.elements
               if tag == "meta" and attrs.get("http-equiv") == "Content-Security-Policy"]
    digest = b64encode(sha256(source.encode("utf-8")).digest()).decode("ascii")
    directives = {part.strip().partition(" ")[0]: part.strip().partition(" ")[2]
                  for part in policy.split(";") if part.strip()}
    assert directives["default-src"] == directives["base-uri"] == directives["form-action"] == "'none'"
    assert directives["script-src"] == f"'sha256-{digest}'"
    assert "synthetic" in html.lower() and "fictional" in html.lower()
    metadata = {attrs.get("name") or attrs.get("property"): attrs.get("content")
                for tag, attrs in document.elements if tag == "meta"}
    assert "Stock Research Command Center" in metadata["og:title"]
    assert metadata["og:description"] == metadata["description"]
    ids = [attrs["id"] for _, attrs in document.elements if "id" in attrs]
    assert len(ids) == len(set(ids))
    assert not any(tag in {"img", "iframe", "object"} for tag, _ in document.elements)
    assert not any({"src", "srcset", "action"}.intersection(attrs) for _, attrs in document.elements)
    assert not any(name.startswith("on") for _, attrs in document.elements for name in attrs)
    anchor_hrefs = [attrs["href"] for tag, attrs in document.elements if tag == "a"]
    assert anchor_hrefs.count("./amd.html") == 1
    assert all(href == "./amd.html" or (href.startswith("#") and href[1:] in ids)
               for href in anchor_hrefs)
    assert all(attrs.get("rel") in {"canonical", "alternate"} for tag, attrs in document.elements if tag == "link")
    assert {attrs["data-demo-page"] for _, attrs in document.elements if "data-demo-page" in attrs} == {
        "discover", "overview", "financials", "valuation", "notes", "sources", "monitor",
    }
    assert {attrs["data-company-answer"] for _, attrs in document.elements if "data-company-answer" in attrs} == {
        "price", "financial", "valuation",
    }


def test_company_sections_keep_workflow_entries_and_named_tools_separate():
    from scripts.build_company_demo import build_demo_html

    html = build_demo_html()
    document = _Document(html)
    section_links = [(attrs["data-demo-section"], attrs["href"])
                     for tag, attrs in document.elements if tag == "a" and "data-demo-section" in attrs]
    assert section_links == [(name, f"#{name}") for name in (
        "overview", "financials", "valuation", "notes", "sources",
    )]
    assert [attrs["data-demo-workflow"] for tag, attrs in document.elements
            if tag == "a" and "data-demo-workflow" in attrs] == ["discover", "monitor"]
    assert {attrs.get("aria-label") for tag, attrs in document.elements if tag == "nav"} == {
        "Company sections", "Research workflow",
    }
    for title in ("Overview", "Financial Trends", "Valuation &amp; Peers", "Research Notes", "Data Sources",
                  "Business Trend", "Cash flow", "Scenario Lab", "Sensitivity analysis", "Valuation methods",
                  "Peer Read-Through", "Forward View", "Catalysts", "Research Decision Lab", "Research brief"):
        assert title in html
    assert "Reported cash flow is unavailable" in html
    assert "10% cash-flow margin is an assumption" in html


def test_amd_case_uses_dated_filing_metrics_and_withholds_market_data():
    from scripts.build_amd_demo import build_amd_demo_html

    html = build_amd_demo_html()
    document = _Document(html)
    for text in ("Advanced Micro Devices", "Sep 26, 2026", "Nov 4, 2026", "+44.7%", "21.2%",
                 "13.7%", "+7.4 pp", "Peer comparison withheld", "View why",
                 "What drove the quarter", "63.9%", "47.0%", "Quarterly trends", "Q4 FY2025",
                 "Q1 FY2026", "Q2 FY2026", "130.3", "Cash generation", "Nine months ended",
                 "4.678", "3.437", "Sample Monitor follow-up"):
        assert text in html
    assert not document.scripts
    assert "Synthetic data" not in html and "13,377" not in html and "9,246" not in html
    assert {attrs["href"] for tag, attrs in document.elements if tag == "a" and attrs["href"].startswith("https:")} == {
        "https://www.sec.gov/Archives/edgar/data/2488/000000248826000014/q42025991.htm",
        "https://www.sec.gov/Archives/edgar/data/2488/000000248826000076/amd-20260328.htm",
        "https://www.sec.gov/Archives/edgar/data/2488/000000248826000123/amd-20260627.htm",
        "https://www.sec.gov/Archives/edgar/data/2488/000000248826000191/amd-20260926.htm",
    }
    ids = {attrs["id"] for _, attrs in document.elements if "id" in attrs}
    assert all(attrs["href"][1:] in ids for tag, attrs in document.elements
               if tag == "a" and attrs["href"].startswith("#"))
    assert any(tag == "a" and attrs["href"] == "./#notes" for tag, attrs in document.elements)
    assert [text for href, text in document.links if href == "./#valuation"] == [
        "Explore advanced research tools",
    ]
    assert [text for href, text in document.links if href == "./#monitor"] == [
        "Try the fictional evidence review",
    ]


@contextmanager
def _browser(tmp_path, viewport, *, javascript=True, html=None):
    from scripts.build_company_demo import build_demo_html
    from src.public_performance_gate import find_chrome_executable

    playwright = pytest.importorskip("playwright.sync_api")
    if (chrome := find_chrome_executable()) is None:
        pytest.skip("Chrome-compatible browser is unavailable")
    path = tmp_path / "demo.html"
    path.write_text(build_demo_html() if html is None else html, encoding="utf-8")

    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(executable_path=str(chrome), headless=True)
        try:
            page = browser.new_page(viewport=viewport, java_script_enabled=javascript)
            requests, errors = [], []
            page.route("http*://**", lambda route: (requests.append(route.request.url), route.abort()))
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
            page.goto(path.as_uri())
            yield page, playwright.expect
            assert not requests and not errors, (requests, errors)
        finally:
            browser.close()


def _viewport_fits(page, viewport):
    assert page.locator("html").evaluate("e => e.scrollWidth") == viewport["width"]


def _open_native_detail(panel, title, expect):
    summary = panel.locator("summary").filter(has_text=re.compile(rf"^\s*{re.escape(title)}\s*$"))
    expect(summary).to_be_visible()
    detail = summary.locator("..")
    expect(detail).not_to_have_attribute("open", "")
    summary.press("Enter")
    expect(detail).to_have_attribute("open", "")
    return detail


@pytest.mark.parametrize("viewport", [{"width": 1280, "height": 900}, {"width": 390, "height": 844}], ids=["desktop", "phone"])
def test_shared_demo_style_preserves_dated_amd_case_layout_and_source_holds(tmp_path, viewport):
    from scripts.build_amd_demo import build_amd_demo_html

    with _browser(tmp_path, viewport, javascript=False, html=build_amd_demo_html()) as (page, expect):
        expect(page.get_by_role("heading", name="Advanced Micro Devices", exact=True)).to_be_visible()
        valuation = page.locator("#peer-valuation")
        expect(valuation).to_contain_text("Peer comparison withheld")
        _open_native_detail(valuation, "View why", expect)
        expect(valuation).to_contain_text("at least three eligible peers")
        page.get_by_role("navigation").get_by_role("link", name="Cash flow", exact=True).press("Enter")
        cash = page.locator("#cash-generation")
        expect(cash).to_contain_text("Nine months ended")
        expect(cash).to_contain_text("4.678")
        expect(cash).to_contain_text("3.437")
        _viewport_fits(page, viewport)


@pytest.mark.parametrize("viewport", [{"width": 1280, "height": 900}, {"width": 390, "height": 844}], ids=["desktop", "phone"])
def test_guided_demo_search_peer_withholding_and_follow_up_offline(tmp_path, viewport):
    with _browser(tmp_path, viewport) as (page, expect):
        panels = page.locator("[data-demo-page]:visible")
        discover = page.locator('[data-demo-page="discover"]')
        query = page.locator("[data-demo-query]")
        status = page.locator("[data-demo-search-status]")
        result = page.locator("[data-demo-result]")
        expect(panels).to_have_count(1)
        expect(discover).to_be_visible()
        company_heading = page.locator("[data-demo-company-heading]")
        expect(company_heading).to_be_hidden()
        _viewport_fits(page, viewport)

        query.fill("no-such-company")
        query.press("Enter")
        expect(status).to_have_text("No fictional company matches that search.")
        expect(result).to_be_hidden()
        query.fill("  fIcT  ")
        query.press("Enter")
        expect(result).to_contain_text("Fogline Photonics")
        expect(result).to_be_visible()
        page.locator('[data-demo-search] button[type="reset"]').press("Enter")
        expect(query).to_have_value("")
        expect(query).to_be_focused()
        expect(result).to_be_hidden()
        expect(status).to_be_empty()

        query.fill("fogline photonics")
        query.press("Enter")
        result.get_by_role("link").first.press("Enter")
        overview = page.locator('[data-demo-page="overview"]')
        expect(overview.locator("[data-demo-title]")).to_be_focused()
        expect(overview.locator("[data-demo-title]")).to_be_in_viewport()
        expect(company_heading).to_be_visible()
        expect(overview.get_by_role("img", name="Reported annual revenue")).to_be_visible()
        expect(overview.get_by_role("table")).to_contain_text("120M")
        nav = page.get_by_role("navigation")
        nav.locator('[data-demo-go="financials"]').press("Enter")
        financials = page.locator('[data-demo-page="financials"]')
        expect(financials.locator("[data-demo-title]")).to_be_focused()
        expect(financials.locator("[data-demo-title]")).to_be_in_viewport()
        expect(financials).to_contain_text("2025")
        expect(financials).to_contain_text("2024")
        trend = _open_native_detail(financials, "Business Trend", expect)
        expect(trend.get_by_role("row").filter(has_text="Q4 FY2025")).to_contain_text("26M")
        expect(financials.get_by_role("img", name="Fictional quarterly operating margin")).to_be_visible()
        expect(financials).to_contain_text("Reported cash flow is unavailable")
        expect(financials).to_contain_text("FY2023 growth is unavailable")
        _viewport_fits(page, viewport)

        nav.locator('[data-demo-go="overview"]').press("Enter")
        callout = overview.locator("[data-demo-peer-callout]")
        expect(callout).to_be_visible()
        expect(callout).to_contain_text("20.0% above peers", use_inner_text=True)
        expect(callout).to_contain_text("24.0×", use_inner_text=True)
        expect(callout).to_contain_text("20.0×", use_inner_text=True)
        expect(callout).to_contain_text("3 eligible · 1 excluded", use_inner_text=True)
        view_why = callout.get_by_role("link", name="View why", exact=True)
        expect(view_why).to_have_count(1)
        view_why.press("Enter")
        valuation = page.locator('[data-demo-page="valuation"]')
        evidence = valuation.locator(".peer-evidence:visible")
        expect(valuation).to_be_visible()
        expect(evidence).to_have_attribute("open", "")
        expect(evidence.locator("summary")).to_be_focused()

        nav.locator('[data-demo-go="financials"]').press("Enter")
        expect(financials.locator("[data-demo-title]")).to_be_focused()
        nav.locator('[data-demo-go="valuation"]').press("Enter")
        expect(valuation.locator("[data-demo-title]")).to_be_focused()
        available = valuation.get_by_role("radio", name="3 eligible peers", exact=True)
        withheld = valuation.get_by_role("radio", name="2 eligible peers", exact=True)
        comparison = valuation.locator('[data-company-answer="valuation"]:visible')
        expect(comparison).to_contain_text("20.0×")
        expect(comparison).to_contain_text("3 eligible peers · comparison available")
        available.press("ArrowRight")
        expect(withheld).to_be_checked()
        expect(comparison).to_contain_text("24.0×")
        expect(comparison).to_contain_text("2 eligible peers · 3 required")
        expect(comparison).not_to_contain_text("20.0×")
        peer_c = valuation.get_by_role("row").filter(has_text="Peer C")
        expect(peer_c).to_contain_text("Excluded · different close date")
        evidence.locator("summary").press("Enter")
        expect(evidence).to_have_attribute("open", "")
        expect(evidence).to_contain_text("Oct 29, 2026")
        expect(evidence).to_contain_text(re.compile(r"same[- ]day", re.IGNORECASE))
        evidence.locator("summary").press("Enter")
        expect(evidence).not_to_have_attribute("open", "")
        nav.locator('[data-demo-go="overview"]').press("Enter")
        expect(callout).to_contain_text("Peer comparison withheld", use_inner_text=True)
        expect(callout).to_contain_text("24.0×", use_inner_text=True)
        expect(callout).not_to_contain_text("20.0×", use_inner_text=True)
        expect(callout).to_contain_text("2 eligible · 2 excluded", use_inner_text=True)
        expect(view_why).to_have_count(1)
        _viewport_fits(page, viewport)
        view_why.press("Enter")
        expect(withheld).to_be_checked()
        expect(evidence).to_have_attribute("open", "")
        expect(evidence.locator("summary")).to_be_focused()
        expect(evidence).to_contain_text("Oct 29, 2026")
        read_through = _open_native_detail(valuation, "Peer Read-Through", expect)
        expect(read_through).to_contain_text("USD 50M to USD 59M")
        scenario = _open_native_detail(valuation, "Scenario Lab", expect)
        wacc = scenario.get_by_role("slider", name="Scenario WACC", exact=True)
        baseline = scenario.locator("[data-demo-scenario-baseline]")
        scenario_value = scenario.locator("[data-demo-scenario-value]")
        expect(wacc).to_have_attribute("type", "range")
        expect(wacc).to_have_value("9")
        expect(baseline).to_be_visible()
        expect(scenario_value).to_be_visible()
        original_baseline = baseline.inner_text()
        assert original_baseline.strip()
        expect(scenario_value).to_have_text(original_baseline)
        wacc.press("ArrowRight")
        expect(wacc).to_have_value("10")
        expect(scenario_value).to_have_text("USD 217.9M")
        expect(baseline).to_have_text(original_baseline)
        expect(withheld).to_be_checked()
        sensitivity = _open_native_detail(valuation, "Sensitivity analysis", expect)
        expect(sensitivity.get_by_role("row").filter(has_text="10%")).to_contain_text("USD 217.9M")
        methods = _open_native_detail(valuation, "Valuation methods", expect)
        expect(methods).to_contain_text("A DCF per-share result is unavailable")
        _viewport_fits(page, viewport)
        page.get_by_role("link", name="Skip to demo content").press("Enter")
        expect(page).to_have_url(re.compile(r"#demo-main$"))
        expect(page.locator("#demo-main")).to_be_focused()
        expect(valuation).to_be_visible()

        nav.locator('[data-demo-go="monitor"]').press("Enter")
        expect(company_heading).to_be_hidden()
        expect(page.locator("[data-demo-monitor-empty]")).to_be_visible()
        nav.locator('[data-demo-go="notes"]').press("Enter")
        notes = page.locator('[data-demo-page="notes"]')
        expect(notes.locator("[data-demo-title]")).to_be_focused()
        for title in ("Forward View", "Catalysts", "Research Decision Lab", "Research brief"):
            _open_native_detail(notes, title, expect)
        _viewport_fits(page, viewport)
        note = "<b>Check the fiscal-year comparison</b>"
        notes.locator("[data-demo-note-input]").fill(note)
        nav.locator('[data-demo-go="sources"]').press("Enter")
        sources = page.locator('[data-demo-page="sources"]')
        expect(sources.locator("[data-demo-title]")).to_be_focused()
        expect(sources).to_contain_text("No cumulative cash flow is treated as a quarter")
        expect(sources).to_contain_text("FICT-FY25-01 and FICT-FY25-02")
        expect(company_heading).to_be_visible()
        _viewport_fits(page, viewport)
        nav.locator('[data-demo-go="valuation"]').press("Enter")
        expect(wacc).to_have_value("10")
        expect(withheld).to_be_checked()
        nav.locator('[data-demo-go="notes"]').press("Enter")
        expect(notes.locator("[data-demo-title]")).to_be_focused()
        expect(notes.locator("[data-demo-note-input]")).to_have_value(note)
        notes.locator("[data-demo-pin]").press("Enter")
        expect(notes.locator("[data-demo-pin-status]")).to_have_text("Follow-up added for this page.")
        nav.locator('[data-demo-go="monitor"]').press("Enter")
        monitor = page.locator('[data-demo-page="monitor"]')
        expect(monitor.locator("[data-demo-title]")).to_be_focused()
        expect(nav.locator('[data-demo-go="monitor"]')).to_have_attribute("aria-current", "page")
        expect(monitor.locator("[data-demo-monitor-item]")).to_contain_text("Fogline Photonics · FICT")
        expect(monitor.locator("[data-demo-monitor-note]")).to_have_text(note)
        expect(monitor.locator("[data-demo-monitor-note] b")).to_have_count(0)
        expect(monitor.locator("[data-demo-monitor-empty]")).to_be_hidden()
        _viewport_fits(page, viewport)

        monitor.locator('[data-demo-go="notes"]:visible').press("Enter")
        expect(notes.locator("[data-demo-title]")).to_be_focused()
        expect(notes.locator("[data-demo-note-input]")).to_have_value(note)
        page.go_back()
        expect(monitor).to_be_visible()
        expect(monitor.locator("[data-demo-monitor-note]")).to_have_text(note)
        nav.locator('[data-demo-go="valuation"]').press("Enter")
        expect(withheld).to_be_checked()
        expect(comparison).not_to_contain_text("20.0×")
        nav.locator('[data-demo-go="discover"]').press("Enter")
        expect(query).to_have_value("fogline photonics")
        expect(result).to_be_visible()
        nav.locator('[data-demo-go="monitor"]').press("Enter")
        expect(monitor.locator("[data-demo-monitor-note]")).to_have_text(note)
        page.reload()
        expect(panels).to_have_count(1)
        expect(monitor).to_be_visible()
        expect(page.locator("[data-demo-monitor-empty]")).to_be_visible()


def test_native_sections_and_peer_controls_remain_usable_without_scripts(tmp_path):
    viewport = {"width": 390, "height": 844}
    with _browser(tmp_path, viewport, javascript=False) as (page, expect):
        callout = page.locator("[data-demo-peer-callout]")
        expect(callout).to_contain_text("20.0×", use_inner_text=True)
        callout.get_by_role("link", name="View why", exact=True).press("Enter")
        expect(page).to_have_url(re.compile(r"#valuation$"))
        valuation = page.locator('[data-demo-page="valuation"]')
        expect(valuation).to_be_visible()
        valuation.get_by_role("radio", name="3 eligible peers", exact=True).press("ArrowRight")
        expect(valuation.get_by_role("radio", name="2 eligible peers", exact=True)).to_be_checked()
        expect(callout).to_contain_text("Peer comparison withheld", use_inner_text=True)
        expect(callout).not_to_contain_text("20.0×", use_inner_text=True)
        scenario = _open_native_detail(valuation, "Scenario Lab", expect)
        expect(scenario.locator("[data-demo-scenario-baseline]")).to_be_visible()
        expect(scenario.get_by_role("slider", name="Scenario WACC")).to_be_hidden()
        expect(scenario).to_contain_text("The interactive slider requires scripts.")
        monitor = page.locator('[data-demo-page="monitor"]')
        monitor.get_by_role("link", name="Review saved evidence", exact=True).press("Enter")
        expect(page).to_have_url(re.compile(r"#demo-evidence-pair$"))
        pair = page.get_by_role("region", name="Saved evidence comparison", exact=True)
        expect(pair).to_contain_text("FICT-FY25-01")
        expect(pair).to_contain_text("FICT-FY25-02")
        expect(monitor.get_by_role("button", name="Save disposition", exact=True)).to_be_hidden()
        _viewport_fits(page, viewport)


@pytest.mark.parametrize("viewport", [{"width": 1280, "height": 900}, {"width": 390, "height": 844}], ids=["desktop", "phone"])
def test_monitor_reopens_exact_fictional_pair_and_records_a_disposition(tmp_path, viewport):
    with _browser(tmp_path, viewport) as (page, expect):
        nav = page.get_by_role("navigation", name="Research workflow")
        nav.get_by_role("link", name="Monitor", exact=True).press("Enter")
        item = page.get_by_role("region", name="Sample evidence follow-up", exact=True)
        pair = page.get_by_role("region", name="Saved evidence comparison", exact=True)
        review = item.get_by_role("link", name="Review saved evidence", exact=True)
        expect(item).to_contain_text("Pending review")
        expect(item).to_contain_text("Fictional sample")
        expect(review).to_have_attribute("href", "#demo-evidence-pair")
        review.press("Enter")
        expect(page).to_have_url(re.compile(r"#demo-evidence-pair$"))
        expect(pair.get_by_role("heading", name="Saved evidence comparison", exact=True)).to_be_focused()
        observations = pair.locator("[data-demo-evidence-observation]")
        expect(observations).to_have_count(2)
        expect(observations.nth(0)).to_contain_text("FICT-FY25-01")
        expect(observations.nth(1)).to_contain_text("FICT-FY25-02")
        for observation in observations.all():
            expect(observation).to_contain_text("Jan 1–Dec 31, 2025")
            expect(observation).to_contain_text("Fictional FY2025 annual statement")
            expect(observation).to_contain_text("USD 120M revenue")
        expect(observations.nth(0)).to_contain_text("Operating income line pending")
        expect(observations.nth(1)).to_contain_text("USD 17M operating income")
        expect(observations.nth(0)).to_be_in_viewport(ratio=1)
        expect(observations.nth(1)).to_be_in_viewport(ratio=1)
        original_observations = observations.all_inner_texts()
        _viewport_fits(page, viewport)

        back = pair.get_by_role("link", name="Back to Monitor", exact=True)
        back.press("Enter")
        expect(item).to_be_visible()
        detail = _open_native_detail(item, "Record a disposition", expect)
        still_open = detail.get_by_role("radio", name="Still open", exact=True)
        reviewed = detail.get_by_role("radio", name="Reviewed", exact=True)
        reason = detail.get_by_role("textbox", name="Reason", exact=True)
        save = detail.get_by_role("button", name="Save disposition", exact=True)
        status = item.locator("[data-demo-review-status]")
        saved_reason = item.locator("[data-demo-review-reason]")

        still_open.press("Space")
        expect(still_open).to_be_checked()
        reason.fill("   ")
        save.press("Enter")
        expect(detail.get_by_role("status")).to_have_text("Enter a reason first.")
        expect(reason).to_be_focused()
        expect(status).to_have_text("Pending review")
        expect(saved_reason).to_be_hidden()
        reason.fill("  Check the source line again.  ")
        save.press("Enter")
        expect(status).to_have_text("Still open")
        expect(saved_reason).to_have_text("Check the source line again.")
        assert saved_reason.text_content() == "Check the source line again."
        expect(reason).to_have_value("Check the source line again.")
        expect(page.locator("[data-demo-monitor-empty]")).to_be_visible()
        _viewport_fits(page, viewport)

        review.press("Enter")
        expect(pair.locator("[data-demo-review-status]")).to_have_text("Still open")
        expect(pair.locator("[data-demo-review-reason]")).to_have_text("Check the source line again.")
        assert observations.all_inner_texts() == original_observations
        back.press("Enter")
        reviewed.press("Space")
        expect(reviewed).to_be_checked()
        reason.fill("   ")
        save.press("Enter")
        expect(detail.get_by_role("status")).to_have_text("Enter a reason first.")
        expect(status).to_have_text("Still open")
        expect(saved_reason).to_have_text("Check the source line again.")
        literal_reason = "<b>Operating income line verified</b>"
        reason.fill(f"  {literal_reason}  ")
        save.press("Enter")
        expect(status).to_have_text("Reviewed")
        expect(saved_reason).to_have_text(literal_reason)
        assert saved_reason.text_content() == literal_reason
        expect(saved_reason.locator("b")).to_have_count(0)
        review.press("Enter")
        expect(pair.locator("[data-demo-review-status]")).to_have_text("Reviewed")
        expect(pair.locator("[data-demo-review-reason]")).to_have_text(literal_reason)
        assert observations.all_inner_texts() == original_observations

        page.reload()
        expect(pair).to_be_visible()
        expect(pair.locator("[data-demo-review-status]")).to_have_text("Pending review")
        expect(pair.locator("[data-demo-review-reason]")).to_be_hidden()
        assert observations.all_inner_texts() == original_observations
