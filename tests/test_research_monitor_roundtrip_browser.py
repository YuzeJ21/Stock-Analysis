"""Exercise the online company-to-Monitor round trip in a real browser."""

import os
from pathlib import Path
import re
import socket
import subprocess
import sys
from urllib.parse import parse_qs, urlsplit

import pytest

from src.public_performance_gate import _free_port, _wait_for_health, find_chrome_executable
from src.workspace_visual_browser_gate import _contrast_ratio


def assert_rendered_english(surface):
    rendered = surface.inner_text() + "\n" + surface.aria_snapshot()
    untranslated = [
        line for line in rendered.splitlines()
        if re.search(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\U00020000-\U0003134f]", line)
    ]
    assert not untranslated, "Untranslated visible copy:\n" + "\n".join(untranslated[:12])


def run_browser_fixture(root):
    """Run the dashboard with qualified synthetic observations and disposable receipt storage."""
    from src import company_workbench_ui, dashboard, online_company_identity, online_company_prices
    from src import sec_annual_history, sec_research_review_ui
    from src.online_company_prices import fetch_online_company_prices
    from tests.test_company_workbench_sections import financial_view
    from tests.test_multi_company_sec_review import issuer_view
    from tests.test_online_company_prices import OBSERVED, _fetch
    from tests.test_online_company_search_view import _result

    calls_file = root / "provider-calls.txt"
    fetch_price = _fetch()

    def record(source):
        with calls_file.open("a", encoding="utf-8") as calls:
            calls.write(source + "\n")

    def search(query, *, user_agent):
        record("search")
        assert query == "FICT"
        return {**_result(), "query": query}

    def financial(ticker, *, user_agent):
        record("financial")
        assert ticker == "FICT"
        view = financial_view()
        identity = issuer_view("FICT", "0000001234")["companyfacts_identity"]
        view["companyfacts_identity"] = {
            **identity,
            "observed_at": "2026-10-30T12:00:00Z",
            "source_last_modified": "2026-10-30T10:00:00Z",
            "association_observed_at": "2026-10-30T11:59:00Z",
        }
        return view

    def price_transport(url):
        record("prices")
        assert "/FICT?" in url
        return fetch_price(url)

    def prices(ticker, **kwargs):
        return fetch_online_company_prices(
            ticker, **{**kwargs, "fetcher": price_transport, "observed_at": OBSERVED}
        )

    def company_profile(cik, **_kwargs):
        record("company-profile")
        assert cik == "0000001234"
        return {"status": "unavailable", "reason": "sec_profile_unavailable"}

    def peer_valuation(ticker, state, *, refresh_requested, expected_cik):
        if ticker in {"AMD", "DUK", "NEM", "NVDA"} and expected_cik is None and not refresh_requested:
            return {"status": "not_requested"}
        assert (ticker, expected_cik) == ("FICT", "0000001234")
        if refresh_requested:
            record("peer-valuation")
            state["fixture-peer-valuation"] = {
                "status": "research_comparison", "ticker": ticker,
                "metric": "reported_annual_diluted_pe",
                "subject": {"ticker": ticker, "price_date": "2026-10-30", "multiple": 30},
                "peers": [{"ticker": symbol, "price_date": "2026-10-30"} for symbol in ("FA", "FB", "FC")],
                "peer_count": 3, "peer_median": 25, "premium_fraction": 0.2,
            }
        return state.get("fixture-peer-valuation", {"status": "not_requested"})

    original_connect = socket.socket.connect

    def local_connect(sock, address):
        if isinstance(address, tuple) and address[0] not in {"127.0.0.1", "::1", "localhost"}:
            record("unexpected-external-request")
            raise AssertionError("The browser regression must not access external providers.")
        return original_connect(sock, address)

    # The app subprocess owns this receipt store for its lifetime. A page reload
    # can overlap the teardown of the previous Streamlit session.
    sec_research_review_ui.PROJECT_ROOT = root
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(socket.socket, "connect", local_connect)
        patch.setattr(dashboard, "search_sec_company_candidates", search)
        patch.setattr(sec_annual_history, "fetch_sec_online_research_view", financial)
        patch.setattr(online_company_prices, "fetch_online_company_prices", prices)
        patch.setattr(online_company_identity, "fetch_sec_company_profile", company_profile)
        patch.setattr(company_workbench_ui, "get_online_peer_valuation", peer_valuation)
        if (root / "hierarchy-state.txt").exists():
            from dataclasses import replace
            from src import sec_research_review
            from src.research_decision_lab import ResearchDisciplineRow
            from src.weekly_research_summary import WeeklyResearchSummary

            original_route = dashboard.render_personal_research_route
            original_review_queue = sec_research_review.review_queue

            def hierarchy_route(**kwargs):
                kwargs["state"] = {"queue": (), "events": (), "status": "no_changes"}
                kwargs["context"] = replace(kwargs["context"], freshness_state="stale",
                    freshness_message="Synthetic saved model inputs need a dated review.")
                kwargs["weekly_summary"] = WeeklyResearchSummary(
                    status="no_changes", as_of="2026-11-06T12:00:00Z", cohort_size=1,
                    unique_event_count=0, items=(), message="No saved source change is due.",
                )
                return original_route(**kwargs)

            def discipline(*_args, **_kwargs):
                if (root / "hierarchy-state.txt").read_text() != "follow-up":
                    return ()
                return (ResearchDisciplineRow(
                    cohort_order=0, ticker="FICT", status="ready", due_lanes=("Evidence",),
                    next_process_step="Inspect the saved synthetic evidence.", identity="fixture-fict",
                    attention_state="conflicting_evidence", attention_label="Needs review",
                    attention_reason="The saved synthetic evidence needs review.", attention_source="evidence",
                ),)

            patch.setattr(dashboard, "render_personal_research_route", hierarchy_route)
            patch.setattr(dashboard, "load_dashboard_research_discipline_rows", discipline)
            patch.setattr(sec_research_review, "review_queue", lambda _root, profile_key:
                          original_review_queue(root, profile_key))
        dashboard.main()


@pytest.fixture
def research_browser_server(tmp_path):
    app_path = tmp_path / "research_app.py"
    app_path.write_text(
        "from pathlib import Path\n"
        "from tests.test_research_monitor_roundtrip_browser import run_browser_fixture\n"
        "run_browser_fixture(Path(__file__).parent)\n",
        encoding="utf-8",
    )
    project_root = Path(__file__).resolve().parents[1]
    port = _free_port()
    url = f"http://127.0.0.1:{port}"
    env = {
        **os.environ,
        "PYTHONPATH": str(project_root),
        "PYTHONDONTWRITEBYTECODE": "1",
        "STOCK_RESEARCH_DATA_PROFILE": "demo",
        "SEC_USER_AGENT": "Synthetic test research contact@example.com",
    }
    env.pop("COMMERCIAL_RESEARCH_MODE", None)
    with (tmp_path / "streamlit.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            [
                sys.executable, "-m", "streamlit", "run", str(app_path),
                "--server.address", "127.0.0.1", "--server.port", str(port),
                "--server.headless", "true", "--server.fileWatcherType", "none",
                "--browser.gatherUsageStats", "false",
            ],
            cwd=project_root, env=env, stdout=log, stderr=subprocess.STDOUT,
        )
        try:
            _wait_for_health(url, timeout_seconds=20)
            yield url
        finally:
            process.terminate()
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


@pytest.mark.parametrize("width,height", [(1280, 900), (390, 844)], ids=["desktop", "phone"])
def test_research_pages_start_with_company_search_and_keep_diagnostics_folded(
    research_browser_server, tmp_path, width, height,
):
    """Exercise the actual page composition without providers or canonical writes."""
    from src.sec_research_review import capture_review, save_review
    from tests.test_multi_company_sec_review import issuer_view

    if (chrome := find_chrome_executable()) is None:
        pytest.skip("Chrome-compatible browser is unavailable")
    playwright = pytest.importorskip("playwright.sync_api")
    state_file = tmp_path / "hierarchy-state.txt"
    state_file.write_text("empty")
    paths = [save_review(capture_review(issuer_view(), profile_key="demo",
        saved_at=f"2026-11-06T12:0{index}:00Z"), tmp_path) for index in range(2)]
    original_receipts = {path: path.read_bytes() for path in paths}

    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(executable_path=str(chrome), headless=True)
        try:
            page = browser.new_page(viewport={"width": width, "height": height})
            page.set_default_timeout(15_000)
            blocked, errors = [], []

            def local_only(route):
                if route.request.url.startswith(research_browser_server + "/"):
                    route.continue_()
                else:
                    blocked.append(route.request.url)
                    route.abort()

            page.route("**/*", local_only)
            page.on("pageerror", lambda error: errors.append(str(error)))

            def calls():
                path = tmp_path / "provider-calls.txt"
                return path.read_text().splitlines() if path.exists() else []

            def check_surface(label):
                assert_rendered_english(page.locator("body"))
                assert page.locator("html").evaluate("node => node.scrollWidth") == width
                assert not page.get_by_test_id("stException").count()
                page.screenshot(path=str(tmp_path / f"hierarchy-{label}-{width}.png"), full_page=True)

            def closed_details(label):
                summary = page.locator("details > summary").filter(has_text=label)
                playwright.expect(summary).to_have_count(1)
                playwright.expect(summary.locator("..")).not_to_have_attribute("open", "")
                return summary

            page.goto(research_browser_server + "/?mode=research&page=research-desk")
            query = page.get_by_role("textbox", name="Company name or ticker", exact=True)
            submit = page.get_by_role("button", name="Search company", exact=True)
            playwright.expect(query).to_be_visible()
            for control in (query, submit):
                box = control.bounding_box()
                assert box and 0 <= box["y"] and box["y"] + box["height"] <= height
            workspace = closed_details("Workspace details")
            workspace.focus()
            page.keyboard.press("Enter")
            playwright.expect(workspace.locator("..")).to_contain_text("Saved readiness")
            playwright.expect(workspace.locator("..")).to_contain_text("Personal research")
            page.keyboard.press("Enter")
            closed_details("Workspace data details")
            playwright.expect(page.get_by_role("link", name="Open AMD saved evidence", exact=True)).to_have_count(1)
            assert calls() == []
            check_surface("desk")
            query.fill("FICT")
            submit.click()
            result = page.get_by_role("region", name="SEC online company results", exact=True)
            playwright.expect(result).to_contain_text("FICT")
            playwright.expect(result.get_by_role("link", name="Open company evidence", exact=True)).to_have_attribute(
                "href", "?mode=research&page=company-workbench&ticker=FICT&online=1")
            assert calls() == ["search"]

            page.goto(research_browser_server + "/?mode=research&page=discover")
            playwright.expect(page.get_by_role("tab", name="Find company online", exact=True)).to_have_attribute("aria-selected", "true")
            playwright.expect(page.get_by_role("textbox", name="Company name or ticker", exact=True)).to_be_visible()
            coverage = closed_details("Coverage studies")
            check_surface("discover")
            page.get_by_role("tab", name="Saved companies", exact=True).click()
            playwright.expect(page.get_by_role("textbox", name="Search saved companies", exact=True)).to_be_visible()
            coverage.focus()
            page.keyboard.press("Enter")
            playwright.expect(coverage.locator("..").get_by_role("tab")).to_have_count(4)
            for tab in coverage.locator("..").get_by_role("tab").all():
                tab.click()
            assert calls() == ["search"]
            check_surface("coverage")

            page.goto(research_browser_server + "/?mode=research&page=monitor&return_ticker=AMD")
            playwright.expect(page.get_by_role("heading", name="Monitor", exact=True)).to_be_visible()
            playwright.expect(page.get_by_role("heading", name="AMD SEC evidence review", exact=True)).to_be_visible()
            playwright.expect(page.get_by_role("heading", name="Follow-up Queue", exact=True)).to_have_count(0)
            playwright.expect(page.get_by_text("No saved process follow-up is due.", exact=True)).to_be_visible()
            freshness = page.locator(".research-monitor-freshness")
            playwright.expect(freshness).to_have_count(1)
            playwright.expect(freshness).to_be_visible()
            playwright.expect(freshness.get_by_role("link", name="Review data dates", exact=True)).to_have_attribute(
                "href", "?mode=research&page=data-health")
            assert freshness.evaluate("node => !node.closest('details')")
            assert "data-sr-region='primary-answer'" not in freshness.evaluate("node => node.outerHTML")
            closed_details("Advanced: Monitor evidence")
            closed_details("Advanced: five-company Earnings Nowcast readiness")
            playwright.expect(page.locator("details > summary").filter(has_text=re.compile(r"^Advanced Evidence$"))).to_have_count(0)
            check_surface("monitor-saved-only")
            state_file.write_text("follow-up")
            page.reload()
            playwright.expect(page.get_by_role("heading", name="Follow-up Queue", exact=True)).to_be_visible()
            playwright.expect(page.locator(".research-discipline-table")).to_contain_text("FICT")
            playwright.expect(page.get_by_role("heading", name="AMD SEC evidence review", exact=True)).to_be_visible()
            check_surface("monitor-follow-up")
            assert calls() == ["search"]
            assert not errors and not blocked
            assert {path: path.read_bytes() for path in paths} == original_receipts
        finally:
            browser.close()


@pytest.mark.parametrize("width,height", [(1280, 900), (390, 844)], ids=["desktop", "phone"])
def test_workbench_sections_and_source_failures_remain_english_without_refetch(
    research_browser_server, tmp_path, width, height,
):
    if (chrome := find_chrome_executable()) is None:
        pytest.skip("Chrome-compatible browser is unavailable")
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(executable_path=str(chrome), headless=True)
        try:
            page = browser.new_page(viewport={"width": width, "height": height})
            page.set_default_timeout(15_000)
            page.route("**/*", lambda route: route.continue_()
                       if route.request.url.startswith(research_browser_server + "/") else route.abort())
            page_errors = []
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            page.goto(f"{research_browser_server}/?mode=research&page=company-workbench&ticker=FICT&online=1")
            refresh = page.get_by_role("button", name="Refresh financials and prices", exact=True)
            playwright.expect(refresh).to_be_visible()
            playwright.expect(page.get_by_role("region", name="Company research summary")).to_have_count(0)
            playwright.expect(page.get_by_text("Refresh financials and prices to load company observations.", exact=True)).to_have_count(1)
            assert_rendered_english(page.locator("body"))
            page.screenshot(path=str(tmp_path / f"english-initial-{width}.png"))
            refresh.click()
            page.get_by_text("Price history", exact=True).click()
            playwright.expect(page.get_by_role("region", name="Daily price history")).to_contain_text("USD 11")
            original_calls = (tmp_path / "provider-calls.txt").read_text().splitlines()
            assert original_calls == ["search", "financial", "prices", "company-profile"]
            for title in ("Overview", "Financial Trends", "Valuation & Peers", "Research Notes", "Data Sources"):
                radio = page.get_by_role("radio", name=title, exact=True)
                page.locator("label").filter(has=radio).click()
                body = page.locator(".st-key-company-section-body")
                playwright.expect(body.get_by_role("heading", name=title, exact=True)).to_be_visible()
                cards = page.locator('[data-company-answer]')
                if title == "Overview":
                    playwright.expect(cards).to_have_count(3)
                else:
                    playwright.expect(cards).to_have_count(0)
                    playwright.expect(page.get_by_label("Loaded company observations", exact=True)).to_be_visible()
                for summary in page.locator(
                    ".st-key-company-section-body details > summary, .company-integrated-header details > summary"
                ).all():
                    if summary.locator("..").get_attribute("open") is None:
                        summary.click()
                assert_rendered_english(page.locator("body"))
                if title == "Financial Trends":
                    for period in ("Quarterly", "Annual"):
                        period_radio = page.get_by_role("radio", name=period, exact=True)
                        page.locator("label").filter(has=period_radio).click()
                        playwright.expect(period_radio).to_be_checked()
                        assert_rendered_english(page.locator("body"))
                if title == "Data Sources":
                    playwright.expect(body).to_contain_text(
                        re.compile(r"unavailable|could not|not available", re.IGNORECASE),
                    )
                assert page.locator("html").evaluate("node => node.scrollWidth") == width
                assert body.evaluate("node => node.scrollWidth <= node.clientWidth + 1")
                filename = title.replace(" & ", "-").replace(" ", "-").lower()
                page.screenshot(path=str(tmp_path / f"english-{filename}-{width}.png"), full_page=True)
            assert (tmp_path / "provider-calls.txt").read_text().splitlines() == original_calls
            assert not page_errors
            assert not page.get_by_test_id("stException").count()
        finally:
            browser.close()


@pytest.mark.parametrize("width,height", [(1280, 900), (390, 844)], ids=["desktop", "phone"])
@pytest.mark.parametrize("ticker", ["NEM", "AMD", "DUK"])
def test_monitor_reopens_and_reviews_exact_issuer_pair(research_browser_server, tmp_path, width, height, ticker):
    from src.sec_research_review import capture_review, save_review
    from tests.test_multi_company_sec_review import issuer_view
    from tests.test_sec_research_review import view

    if (chrome := find_chrome_executable()) is None:
        pytest.skip("Chrome-compatible browser is unavailable")
    playwright = pytest.importorskip("playwright.sync_api")
    nem_before, nem_after = view(), view()
    for observation in (nem_before, nem_after):
        observation["approved_direct_fields"].pop(1)
    nem_after["approved_direct_fields"][0]["value"] = 110
    nem_after["companyfacts_identity"]["payload_sha256"] = "c" * 64
    duk_before, duk_after = (issuer_view("DUK", "0001326160") for _ in range(2))
    duk_after["companyfacts_identity"]["association_payload_sha256"] = "d" * 64
    observations = {
        "NEM": (nem_before, nem_after),
        "AMD": (issuer_view(), issuer_view()),
        "DUK": (duk_before, duk_after),
    }
    receipts = {
        symbol: tuple(capture_review(observation, profile_key="demo", saved_at=f"2026-11-02T22:0{index}:00Z")
                      for index, observation in enumerate(pair))
        for symbol, pair in observations.items()
    }
    receipt_paths = [save_review(receipt, tmp_path) for pair in receipts.values() for receipt in pair]
    original_bytes = {path: path.read_bytes() for path in receipt_paths}
    before, after = receipts[ticker]
    other_receipts = [receipt for symbol, pair in receipts.items() if symbol != ticker for receipt in pair]
    token = before["receipt_id"] + "." + after["receipt_id"]

    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(executable_path=str(chrome), headless=True)
        try:
            page = browser.new_page(viewport={"width": width, "height": height},
                                    color_scheme="dark" if width < 640 else "light")
            page.set_default_timeout(15_000)
            page.route("**/*", lambda route: route.continue_()
                       if route.request.url.startswith(research_browser_server + "/") else route.abort())
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))

            def wait_for_query(**expected):
                def matches(url):
                    query = parse_qs(urlsplit(url).query)
                    return all(query.get(key) == ([value] if value is not None else None)
                               for key, value in expected.items())
                page.wait_for_url(matches)

            monitor_url = research_browser_server + "/?mode=research&page=monitor"
            page.goto(monitor_url if width >= 640 else f"{monitor_url}&return_ticker={ticker}")
            company_selector = page.get_by_test_id("stSelectbox").filter(has_text="Select a company to review")
            playwright.expect(page.get_by_text("Saved companies 3", exact=False)).to_be_visible()
            playwright.expect(company_selector).to_be_visible()
            if width >= 640:
                company_selector.get_by_role("combobox").press("ArrowDown")
                for symbol in observations:
                    playwright.expect(page.get_by_role("option", name=re.compile(rf"^{symbol} · "))).to_be_visible()
                page.get_by_role("option", name=re.compile(rf"^{ticker} · ")).click()
            issuer_heading = page.get_by_role("heading", name=f"{ticker} SEC evidence review", exact=True)
            playwright.expect(issuer_heading).to_be_visible()
            open_pair = page.get_by_role("button", name="Open this evidence pair", exact=True)
            playwright.expect(open_pair).to_be_visible()
            open_pair.click()
            panel = page.locator(".st-key-sec-review-panel")
            pinned_heading = panel.get_by_role("heading", name="Pinned SEC evidence comparison")
            playwright.expect(pinned_heading).to_be_visible()
            wait_for_query(page="company-workbench", section="notes", ticker=ticker, sec_pair=token)
            for receipt in (before, after):
                playwright.expect(panel).to_contain_text(receipt["receipt_id"])
            for receipt in other_receipts:
                playwright.expect(panel).not_to_contain_text(receipt["receipt_id"])
            if ticker == "NEM":
                playwright.expect(panel).to_contain_text("100 → 110 USD")
                playwright.expect(panel).to_contain_text("Operating income")
            elif ticker == "DUK":
                playwright.expect(panel).to_contain_text("Source review changed, financial values unchanged")
            else:
                playwright.expect(panel).to_contain_text("No change")
            for label in ("Earlier evidence source", "Later evidence source"):
                panel.get_by_text(label, exact=False).click()
            sources = panel.get_by_role("link", name="SEC Companyfacts source")
            playwright.expect(sources).to_have_count(2)
            for index in range(2):
                playwright.expect(sources.nth(index)).to_have_attribute("href", before["source_url"])
            assert_rendered_english(page.locator("body"))
            assert panel.evaluate("(panel) => panel.scrollWidth <= panel.clientWidth + 1")
            page.screenshot(path=str(tmp_path / f"{ticker.lower()}-pinned-pair-{width}.png"), full_page=True)

            third = capture_review(observations[ticker][1], profile_key="demo", saved_at="2026-11-02T22:02:00Z")
            third_path = save_review(third, tmp_path)
            original_bytes[third_path] = third_path.read_bytes()
            panel.get_by_role("link", name="Return to this review in Monitor").click()
            playwright.expect(open_pair).to_be_visible()
            playwright.expect(issuer_heading).to_be_visible()
            playwright.expect(company_selector).to_have_count(0)
            wait_for_query(page="monitor", sec_pair=token, sec_ticker=ticker if ticker != "NEM" else None)
            open_pair.click()
            playwright.expect(pinned_heading).to_be_visible()
            for receipt in (before, after):
                playwright.expect(panel).to_contain_text(receipt["receipt_id"])
            playwright.expect(panel).not_to_contain_text(third["receipt_id"])
            panel.get_by_role("link", name="Return to this review in Monitor").click()
            playwright.expect(issuer_heading).to_be_visible()
            save = page.get_by_role("button", name="Save review status")
            reason_input = page.get_by_role("textbox", name="Review reason")
            page.locator("label").filter(has=page.get_by_role("radio", name="Reviewed", exact=True)).click()
            reason_input.fill("   ")
            save.click()
            playwright.expect(page.get_by_text("Choose a review status and enter a reason.", exact=True)).to_be_visible()
            playwright.expect(page.get_by_text("Pending review", exact=True)).to_be_visible()
            assert_rendered_english(page.locator("body"))
            assert not list((tmp_path / "outputs" / "local" / "sec-review-dispositions").rglob("*.json"))
            still_open_reason = f"Revisit the original {ticker} evidence pair."
            for label, reason in (("Reviewed", f"Checked both saved {ticker} observations."),
                                  ("Still open", still_open_reason)):
                radio = page.get_by_role("radio", name=label, exact=True)
                page.locator("label").filter(has=radio).click()
                playwright.expect(radio).to_be_checked()
                reason_input.fill(f"  {reason}  ")
                save.click()
                playwright.expect(page.get_by_text("Review status saved.", exact=True)).to_be_visible()
                saved_reason = page.get_by_test_id("stText").get_by_text(reason, exact=True)
                playwright.expect(saved_reason).to_be_visible()
                assert saved_reason.text_content() == reason
                assert_rendered_english(page.locator("body"))
            page.screenshot(path=str(tmp_path / f"{ticker.lower()}-monitor-disposition-{width}.png"), full_page=True)
            page.reload()
            playwright.expect(issuer_heading).to_be_visible()
            playwright.expect(page.get_by_test_id("stText").get_by_text(still_open_reason, exact=True)).to_be_visible()
            playwright.expect(page.get_by_role("radio", name="Still open", exact=True)).to_be_checked()
            if ticker == "NEM":
                playwright.expect(page.get_by_text("Operating income", exact=True)).to_be_visible()
            page.get_by_role("button", name="View latest evidence pair", exact=True).click()
            playwright.expect(page.get_by_text("Pending review", exact=True)).to_be_visible()
            playwright.expect(issuer_heading).to_be_visible()
            playwright.expect(company_selector).to_be_visible()
            playwright.expect(reason_input).to_have_value("")
            playwright.expect(page.get_by_role("radio", name="Still open", exact=True)).not_to_be_checked()
            playwright.expect(page.get_by_test_id("stText").get_by_text(still_open_reason, exact=True)).to_have_count(0)
            wait_for_query(page="monitor", sec_pair=None, sec_ticker=None)
            open_pair.click()
            playwright.expect(pinned_heading).to_be_visible()
            wait_for_query(page="company-workbench", section="notes", ticker=ticker,
                           sec_pair=after["receipt_id"] + "." + third["receipt_id"])
            if ticker != "NEM":
                wrong_marker = "&sec_ticker=AMD" if ticker == "DUK" else ""
                page.goto(f"{monitor_url}&sec_pair={token}{wrong_marker}")
                playwright.expect(page.get_by_text("This saved evidence pair is unavailable.", exact=False)).to_be_visible()
                playwright.expect(open_pair).to_have_count(0)
                playwright.expect(save).to_have_count(0)
            assert not errors
            assert not (tmp_path / "provider-calls.txt").exists()
            assert {path: path.read_bytes() for path in original_bytes} == original_bytes
        finally:
            browser.close()


@pytest.mark.parametrize(
    ("width", "height", "section_label", "section", "monitor_handoff"),
    [(1280, 900, "Valuation & Peers", "valuation", "navigation"),
     (390, 844, "Research Notes", "notes", "receipt")],
    ids=["desktop-valuation", "phone-sec-receipt"],
)
def test_online_research_round_trip_keeps_section_and_evidence(
    research_browser_server, tmp_path, width, height, section_label, section, monitor_handoff,
):
    if (chrome := find_chrome_executable()) is None:
        pytest.skip("Chrome-compatible browser is unavailable")
    playwright = pytest.importorskip("playwright.sync_api")

    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(executable_path=str(chrome), headless=True)
        try:
            page = browser.new_page(
                viewport={"width": width, "height": height},
                color_scheme="dark" if width <= 640 else "light",
            )
            page.set_default_timeout(15_000)
            page.route("**/*", lambda route: (
                route.continue_() if route.request.url.startswith(research_browser_server + "/")
                else route.abort()
            ))
            documents, streams, errors = [], [], []

            def record_document(request):
                if request.is_navigation_request() and request.resource_type == "document":
                    documents.append(request.url)

            page.on("request", record_document)
            page.on("websocket", lambda socket: streams.append(socket.url))
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(f"{research_browser_server}/?mode=research&page=company-workbench&ticker=FICT&online=1")
            brief = page.get_by_role("region", name="Company Brief", exact=True)
            playwright.expect(brief.get_by_role("heading", name="FICT Company Brief")).to_be_visible()
            page.get_by_role("button", name="Refresh financials and prices", exact=True).click()
            page.get_by_text("Price history", exact=True).click()
            prices = page.get_by_role("region", name="Daily price history", exact=True)
            playwright.expect(prices).to_contain_text("USD 11")
            assert_rendered_english(brief)
            original_prices = prices.inner_text()

            selected = page.get_by_role("radio", name=section_label, exact=True)
            page.locator("label").filter(has=selected).click()
            navigation = page.get_by_role("navigation", name="Personal research workflow")
            if monitor_handoff == "navigation":
                page.get_by_role("button", name="Refresh peer valuation", exact=True).click()
                evidence = page.get_by_role("region", name="Online peer valuation", exact=True)
                playwright.expect(evidence).to_contain_text("Annual P/E is 20.0% above the industry reference median")
                handoff = navigation.get_by_role("link", name="Monitor", exact=True)
            else:
                page.get_by_role("button", name="Save current SEC evidence", exact=True).click()
                evidence = page.locator(".st-key-sec-review-panel")
                playwright.expect(evidence.get_by_role("heading", name="Replay saved evidence")).to_be_visible()
                download = evidence.get_by_role("button", name="Download current evidence package", exact=True)
                playwright.expect(download).to_be_enabled()
                handoff = page.get_by_role("link", name="View review items in Monitor", exact=True)
            playwright.expect(handoff).to_have_attribute("href", "?mode=research&page=monitor")
            original_brief = brief.inner_text()
            original_evidence = tuple(line for line in evidence.inner_text().splitlines()
                                      if line and line != "Observation saved.")
            original_receipts = {path: path.read_bytes() for path in tmp_path.rglob("*.json")}
            if monitor_handoff == "receipt":
                assert original_receipts
            provider_calls = tmp_path / "provider-calls.txt"
            before = provider_calls.read_text().splitlines()
            expected_calls = ["search", "financial", "prices", "company-profile"]
            if monitor_handoff == "navigation":
                expected_calls.append("peer-valuation")
            assert before == expected_calls
            assert len(documents) == len(streams) == 1

            handoff.click()
            playwright.expect(page.get_by_role("heading", name="Monitor", exact=True)).to_be_visible()
            assert len(documents) == len(streams) == 1, "Opening Monitor replaced the research session"
            assert parse_qs(urlsplit(page.url).query) == {
                "mode": ["research"], "page": ["monitor"], "return_ticker": ["FICT"], "return_online": ["1"],
            }
            return_label = "Return to FICT Company Workbench"
            return_button = page.get_by_role("button", name=return_label, exact=True)
            return_link = navigation.get_by_role("link", name="Company Workbench", exact=True)
            playwright.expect(return_link).to_have_attribute(
                "href", "?mode=research&page=company-workbench",
            )
            if monitor_handoff == "navigation":
                return_button.click()
            else:
                playwright.expect(page.get_by_role("heading", name="FICT SEC evidence review")).to_be_visible()
                foreground, background = return_button.get_by_text(return_label, exact=True).evaluate(
                    """label => [
                        getComputedStyle(label).color,
                        getComputedStyle(label.closest('button')).backgroundColor,
                    ]"""
                )
                contrast = _contrast_ratio(foreground, background)
                assert contrast is not None and contrast >= 4.5, (
                    f"Return action contrast {contrast!r} for {foreground} on {background}"
                )
                return_link.press("Enter")
            playwright.expect(brief.get_by_role("heading", name="FICT Company Brief")).to_be_visible()
            playwright.expect(selected).to_be_checked()
            assert brief.inner_text() == original_brief
            if monitor_handoff == "receipt":
                playwright.expect(download).to_be_enabled()
            assert tuple(line for line in evidence.inner_text().splitlines() if line) == original_evidence
            assert {path: path.read_bytes() for path in tmp_path.rglob("*.json")} == original_receipts
            if monitor_handoff == "receipt":
                handoff.click()
                notes_return = page.get_by_role("link", name="Return to FICT evidence review", exact=True)
                playwright.expect(notes_return).to_have_attribute("href", "?mode=research&page=company-workbench")
                notes_return.click()
                playwright.expect(brief.get_by_role("heading", name="FICT Company Brief")).to_be_visible()
                playwright.expect(selected).to_be_checked()
                playwright.expect(download).to_be_enabled()
                assert tuple(line for line in evidence.inner_text().splitlines() if line) == original_evidence
            expected_route = {"page": ["company-workbench"], "ticker": ["FICT"],
                              "online": ["1"], "section": [section]}
            route = parse_qs(urlsplit(page.url).query)
            assert {key: route.get(key) for key in expected_route} == expected_route

            overview = page.get_by_role("radio", name="Overview", exact=True)
            page.locator("label").filter(has=overview).click()
            page.get_by_text("Price history", exact=True).click()
            playwright.expect(prices).to_be_visible()
            assert prices.inner_text() == original_prices
            assert len(documents) == len(streams) == 1, "Returning replaced the research session"
            assert provider_calls.read_text().splitlines() == before
            assert not errors
            assert not page.get_by_test_id("stException").count()
            if monitor_handoff == "navigation":
                page.goto(f"{research_browser_server}/?mode=research&page=monitor&return_ticker=NVDA")
                saved_return = page.get_by_role("link", name="Return to NVDA Company Workbench", exact=True)
                playwright.expect(saved_return).to_have_attribute("target", "_self")
                saved_return.click()
                playwright.expect(brief.get_by_role("heading", name="NVDA Company Brief")).to_be_visible()
                assert len(page.context.pages) == 1
                saved_route = parse_qs(urlsplit(page.url).query)
                assert saved_route == {
                    "mode": ["research"], "page": ["company-workbench"], "ticker": ["NVDA"], "open": ["1"],
                }
                assert provider_calls.read_text().splitlines() == before
                assert not errors
                assert not page.get_by_test_id("stException").count()
        finally:
            browser.close()
