"""Opt-in, read-only checks against an already running local research workspace.

Run explicitly with STOCK_LIVE_WORKBENCH_BASE_URL=http://127.0.0.1:8530.
Live observations and screenshots are written outside the repository only.
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from urllib.parse import urlencode, urlsplit

import pytest

from src.public_performance_gate import find_chrome_executable


_SECTIONS = {
    "overview": "Overview", "financials": "Financial Trends", "valuation": "Valuation & Peers",
    "notes": "Research Notes", "sources": "Data Sources",
}
_CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\U00020000-\U0003134f]")


@pytest.fixture
def live_workbench():
    value = os.environ.get("STOCK_LIVE_WORKBENCH_BASE_URL")
    if not value:
        pytest.skip("Set STOCK_LIVE_WORKBENCH_BASE_URL to opt in to live local observations")
    parsed = urlsplit(value)
    if (parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
            or parsed.username or parsed.password or parsed.path not in {"", "/"}
            or parsed.query or parsed.fragment):
        pytest.fail("STOCK_LIVE_WORKBENCH_BASE_URL must be a plain localhost HTTP origin")
    output = Path(os.environ.get("STOCK_LIVE_WORKBENCH_OUTPUT_DIR", "/tmp/stock-clean-live-browser")).resolve()
    project = Path(__file__).resolve().parents[1]
    if output == project or project in output.parents:
        pytest.fail("Live browser output must stay outside the repository")
    output.mkdir(parents=True, exist_ok=True)
    return value.rstrip("/"), output


def _select_section(page, expect, section):
    radio = page.get_by_role("radio", name=_SECTIONS[section], exact=True)
    page.locator("label").filter(has=radio).click()
    expect(page.locator("[data-company-section]")).to_have_attribute("data-company-section", section)
    expect(radio).to_be_checked()
    expect(page.get_by_role("region", name="Company Brief", exact=True).locator("h1")).to_be_visible()
    page.get_by_test_id("stStatusWidget").wait_for(state="hidden", timeout=240_000)


def _layout_observation(page):
    return page.evaluate("""() => {
      const labels = [...document.querySelectorAll('.st-key-company-section-navigation label')]
        .filter(e=>e.querySelector('input[type="radio"]'));
      const group=document.querySelector('.st-key-company-section-navigation [role="radiogroup"]');
      const groupBounds=group.getBoundingClientRect();
      return {
        viewport: {width:innerWidth, height:innerHeight},
        document_width:document.documentElement.scrollWidth,
        body_width:document.body.scrollWidth,
        app_width:document.querySelector('.stApp')?.scrollWidth,
        h1_count:[...document.querySelectorAll('h1')].filter(e=>e.getClientRects().length).length,
        navigation:labels.map(e=>({label:e.innerText.trim(),height:e.getBoundingClientRect().height,
          left:e.getBoundingClientRect().left,right:e.getBoundingClientRect().right})),
        navigation_container:{left:groupBounds.left,right:groupBounds.right,
          client_width:group.clientWidth,scroll_width:group.scrollWidth,overflow_x:getComputedStyle(group).overflowX},
        overflowing_elements:[...document.querySelectorAll('.st-key-company-workbench-layout *')]
          .filter(e=>e.getClientRects().length && e.getBoundingClientRect().right>innerWidth+1)
          .slice(0,12).map(e=>({tag:e.tagName,class:e.className,right:e.getBoundingClientRect().right}))
      };
    }""")


def _open_details(scope, name):
    summary = scope.locator("summary").filter(has_text=re.compile(rf"^{re.escape(name)}"))
    if not summary.count():
        return None
    summary = summary.first
    detail = summary.locator("..")
    if detail.get_attribute("open") is None:
        summary.click()
    return detail


@pytest.mark.parametrize("ticker", ["AMD", "QCOM"])
def test_live_company_workbench_desktop_then_phone(live_workbench, ticker):
    base, output = live_workbench
    chrome = find_chrome_executable()
    if chrome is None:
        pytest.skip("Chrome-compatible browser is unavailable")
    playwright = pytest.importorskip("playwright.sync_api")
    report = {"ticker": ticker, "started_at": datetime.now(timezone.utc).isoformat(),
              "base_url": base, "failures": [], "page_errors": [], "screenshots": []}
    failures = report["failures"]

    def check(passed, message):
        if not passed:
            failures.append(message)

    def screenshot(page, label):
        path = output / f"{ticker.lower()}-{label}.png"
        page.screenshot(path=str(path), full_page=True, animations="disabled")
        report["screenshots"].append(str(path))

    def check_surface(page, label, width):
        layout = _layout_observation(page)
        report[label] = layout
        check(layout["viewport"]["width"] == width, f"{label}: viewport did not resize to {width}")
        check(all(layout[key] <= width + 1 for key in ("document_width", "body_width", "app_width")),
              f"{label}: horizontal page overflow: {layout}")
        check(layout["h1_count"] == 1, f"{label}: expected one visible H1")
        check([row["label"] for row in layout["navigation"]] == list(_SECTIONS.values()),
              f"{label}: missing or reordered company navigation")
        check(all(row["height"] >= 44 for row in layout["navigation"]), f"{label}: company navigation is under 44px")
        if not all(row["left"] >= -1 and row["right"] <= width + 1 for row in layout["navigation"]):
            group = layout["navigation_container"]
            check(group["overflow_x"] in {"auto", "scroll"} and group["scroll_width"] > group["client_width"]
                  and group["left"] >= -1 and group["right"] <= width + 1,
                  f"{label}: offscreen company controls lack a contained navigation scroller")
        text = page.locator(".st-key-company-workbench-layout").inner_text()
        check(not _CJK.search(text), f"{label}: rendered Chinese copy")
        check(not page.get_by_test_id("stException").count(), f"{label}: Streamlit exception")

    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(executable_path=str(chrome), headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, color_scheme="light")
        page.set_default_timeout(30_000)
        page.on("pageerror", lambda error: report["page_errors"].append(str(error)))
        try:
            route = base + "/?" + urlencode({"mode": "research", "page": "company-workbench",
                                              "ticker": ticker, "open": "1"})
            page.goto(route, wait_until="domcontentloaded", timeout=60_000)
            brief = page.get_by_role("region", name="Company Brief", exact=True)
            playwright.expect(brief.get_by_role("heading", name=f"{ticker} Company Brief", exact=True)).to_be_visible()
            page.get_by_role("button", name="Refresh financials and prices", exact=True).click()
            playwright.expect(brief.locator(".company-answer")).to_have_count(4, timeout=240_000)
            playwright.expect(page.locator(".company-analysis-grid, .company-analysis-gap").first).to_be_visible(timeout=240_000)
            _select_section(page, playwright.expect, "valuation")
            page.get_by_role("button", name="Refresh peer valuation", exact=True).click()
            peers = page.get_by_role("region", name="Online peer valuation", exact=True)
            playwright.expect(peers).to_be_visible(timeout=240_000)
            page.get_by_test_id("stStatusWidget").wait_for(state="hidden", timeout=240_000)
            report["peer_result"] = peers.inner_text()
            disclosure = _open_details(peers, "View actual fiscal periods, prices, and sources")
            check(disclosure is not None, "Valuation source disclosure is missing")
            if disclosure is not None:
                report["source_disclosure"] = disclosure.inner_text()
                check("personal research inspection only" in disclosure.inner_text(), "Source rights disclosure is missing")
                check(bool(disclosure.get_by_role("link").count()), "Source disclosure has no source links")
            excluded = _open_details(peers, "Excluded reference companies and reasons")
            if excluded is not None:
                reasons = excluded.locator("li > details > summary").all_inner_texts()
                report["excluded_reasons"] = reasons
                check(bool(reasons) and all(":" in reason for reason in reasons), "Excluded peer reasons are missing")
            else:
                report["excluded_reasons"] = []
                check("references have not been assessed" in peers.inner_text(),
                      "Neither excluded reasons nor explicit unassessed-peer gap is shown")

            _select_section(page, playwright.expect, "overview")
            playwright.expect(brief.locator(".company-answer")).to_have_count(4)
            report["summary_cards"] = brief.locator(".company-answer").all_inner_texts()
            price = brief.locator('[data-company-answer="price"]')
            price_text = price.inner_text()
            check(bool(re.search(r"\d{4}-\d{2}-\d{2}", price_text)) or "verification" in price_text.lower(),
                  "Latest close has neither a trading date nor an explicit verification gap")
            chart = page.locator(".company-analysis-grid svg[role=img]")
            table = page.locator(".company-analysis-grid table")
            gap = page.locator(".company-analysis-gap")
            check(bool(chart.count() and table.count()) or bool(gap.count()),
                  "Overview has neither chart/table composition nor an explicit financial gap")
            report["financial_chart"] = chart.get_attribute("aria-label") if chart.count() else None
            report["financial_table"] = table.inner_text() if table.count() else None
            report["financial_gap"] = gap.inner_text() if gap.count() else None
            evidence = _open_details(page.locator(".company-analysis-grid"), "Period evidence and gaps") if table.count() else None
            if evidence is not None:
                check("Observed" in evidence.inner_text() and "millions" in page.locator(".company-analysis-grid").inner_text(),
                      "Financial evidence lacks observation date or units")
            check_surface(page, "desktop", 1440)
            brief.scroll_into_view_if_needed()
            screenshot(page, "desktop-overview")

            # Resize this same page/session; do not reload or fetch the evidence again.
            page.set_viewport_size({"width": 390, "height": 844})
            playwright.expect(brief.locator(".company-answer")).to_have_count(4)
            page.get_by_test_id("stMain").evaluate("element => { element.scrollTop = 0; }")
            report["phone_first_view"] = page.evaluate("""() => {
              const bounds=e=>{const r=e.getBoundingClientRect();return {top:r.top,bottom:r.bottom,height:r.height}};
              return Object.fromEntries(['price','valuation'].map(key=>{
                const card=document.querySelector(`[data-company-answer="${key}"]`);
                return [key,{card:bounds(card),value:bounds(card.querySelector('.company-answer-value')),
                  context:bounds(card.querySelector('.company-answer-context')),text:card.innerText}];
              }));
            }""")
            check_surface(page, "phone", 390)
            screenshot(page, "phone-overview")
            if chart.count():
                chart.scroll_into_view_if_needed()
                screenshot(page, "phone-financial-chart")
                table.scroll_into_view_if_needed()
                screenshot(page, "phone-financial-table")
            report["phone_sections"] = {}
            for section in ("financials", "valuation", "notes", "sources", "overview"):
                _select_section(page, playwright.expect, section)
                check_surface(page, f"phone_{section}", 390)
                report["phone_sections"][section] = page.locator("[data-company-section]").get_attribute("data-company-section")
                if section == "sources":
                    sources = page.get_by_role("region", name="Online peer valuation sources", exact=True)
                    check(bool(sources.count()), "Data Sources lacks the refreshed peer source context")
                    if sources.count():
                        source_text = sources.inner_text()
                        check("personal research inspection only" in source_text, "Phone Data Sources lacks rights disclosure")
                        check(bool(sources.get_by_role("link").count()), "Phone Data Sources lacks original source links")
                        screenshot(page, "phone-data-sources")
            check(brief.locator(".company-answer").all_inner_texts() == report["summary_cards"],
                  "Section navigation changed the loaded summary observations")
            check(not report["page_errors"], f"Browser exceptions: {report['page_errors']}")
            assert not failures, "\n".join(failures)
            report["passed"] = True
        except Exception as error:
            report["passed"] = False
            report["exception"] = str(error)
            screenshot(page, "failure")
            raise
        finally:
            report["finished_at"] = datetime.now(timezone.utc).isoformat()
            (output / f"{ticker.lower()}-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
            browser.close()
