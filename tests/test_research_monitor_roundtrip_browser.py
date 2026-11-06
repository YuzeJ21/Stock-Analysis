"""Exercise the online company-to-Monitor round trip in a real browser."""

import os
from pathlib import Path
import socket
import subprocess
import sys
from urllib.parse import parse_qs, urlsplit

import pytest

from src.public_performance_gate import _free_port, _wait_for_health, find_chrome_executable
from src.workspace_visual_browser_gate import _contrast_ratio


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
        if ticker in {"NEM", "NVDA"} and expected_cik is None and not refresh_requested:
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

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(socket.socket, "connect", local_connect)
        patch.setattr(dashboard, "search_sec_company_candidates", search)
        patch.setattr(sec_annual_history, "fetch_sec_online_research_view", financial)
        patch.setattr(online_company_prices, "fetch_online_company_prices", prices)
        patch.setattr(online_company_identity, "fetch_sec_company_profile", company_profile)
        patch.setattr(company_workbench_ui, "get_online_peer_valuation", peer_valuation)
        patch.setattr(sec_research_review_ui, "PROJECT_ROOT", root)
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
def test_nem_monitor_reopens_and_reviews_exact_pair(research_browser_server, tmp_path, width, height):
    from src.sec_research_review import capture_review, save_review
    from tests.test_sec_research_review import view

    if (chrome := find_chrome_executable()) is None:
        pytest.skip("Chrome-compatible browser is unavailable")
    playwright = pytest.importorskip("playwright.sync_api")
    before_view, after_view = view(), view()
    for observation in (before_view, after_view):
        observation["approved_direct_fields"].pop()
    after_view["approved_direct_fields"][0]["value"] = 110
    after_view["companyfacts_identity"]["payload_sha256"] = "c" * 64
    before = capture_review(before_view, profile_key="demo", saved_at="2026-11-02T22:00:00Z")
    after = capture_review(after_view, profile_key="demo", saved_at="2026-11-02T22:01:00Z")
    receipt_paths = (save_review(before, tmp_path), save_review(after, tmp_path))
    original_bytes = [path.read_bytes() for path in receipt_paths]
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
            page.goto(research_browser_server + "/?mode=research&page=monitor")
            open_pair = page.get_by_role("button", name="打开这两份证据", exact=True)
            playwright.expect(open_pair).to_be_visible()
            open_pair.click()
            panel = page.locator(".st-key-sec-review-panel")
            playwright.expect(panel.get_by_role("heading", name="已固定的 SEC 证据比较")).to_be_visible()
            assert parse_qs(urlsplit(page.url).query)["sec_pair"] == [token]
            for receipt in (before, after):
                playwright.expect(panel).to_contain_text(receipt["receipt_id"])
            playwright.expect(panel).to_contain_text("100 → 110 USD")
            playwright.expect(panel).to_contain_text("资本支出")
            for label in ("较早证据的来源", "较新证据的来源"):
                panel.get_by_text(label, exact=False).click()
            assert panel.get_by_role("link", name="SEC Companyfacts 原始来源").count() == 2
            assert panel.evaluate("(panel) => panel.scrollWidth <= panel.clientWidth + 1")

            third = capture_review(after_view, profile_key="demo", saved_at="2026-11-02T22:02:00Z")
            save_review(third, tmp_path)
            panel.get_by_role("link", name="返回 Monitor 的这项复核").click()
            playwright.expect(open_pair).to_be_visible()
            assert parse_qs(urlsplit(page.url).query)["sec_pair"] == [token]
            save = page.get_by_role("button", name="保存复核状态")
            for label, reason in (("Reviewed", "Checked the two original observations."),
                                  ("Still open", "Verify the missing capex source.")):
                radio = page.get_by_role("radio", name=label, exact=True)
                page.locator("label").filter(has=radio).click()
                playwright.expect(radio).to_be_checked()
                page.get_by_role("textbox", name="复核原因").fill(reason)
                save.click()
                playwright.expect(page.get_by_text("已保存复核状态。", exact=True)).to_be_visible()
                playwright.expect(page.locator('[data-testid="stText"]').get_by_text(reason, exact=True)).to_be_visible()
            page.reload()
            playwright.expect(page.locator('[data-testid="stText"]').get_by_text(
                "Verify the missing capex source.", exact=True)).to_be_visible()
            playwright.expect(page.get_by_text("资本支出", exact=True)).to_be_visible()
            page.get_by_role("button", name="查看最新证据对", exact=True).click()
            playwright.expect(page.get_by_text("待复核", exact=True)).to_be_visible()
            assert "sec_pair" not in parse_qs(urlsplit(page.url).query)
            assert not errors
            assert not (tmp_path / "provider-calls.txt").exists()
            assert [path.read_bytes() for path in receipt_paths] == original_bytes
        finally:
            browser.close()


@pytest.mark.parametrize(
    ("width", "height", "section_label", "section", "monitor_handoff"),
    [(1280, 900, "估值与同行", "valuation", "navigation"),
     (390, 844, "研究记录", "notes", "receipt")],
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
            page.get_by_role("button", name="更新财报与价格", exact=True).click()
            prices = page.get_by_role("region", name="Daily price history", exact=True)
            playwright.expect(prices).to_contain_text("USD 11")
            original_prices = prices.inner_text()

            selected = page.get_by_role("radio", name=section_label, exact=True)
            page.locator("label").filter(has=selected).click()
            navigation = page.get_by_role("navigation", name="Personal research workflow")
            if monitor_handoff == "navigation":
                page.get_by_role("button", name="更新在线同行估值", exact=True).click()
                evidence = page.get_by_role("region", name="Online peer valuation", exact=True)
                playwright.expect(evidence).to_contain_text("年度 P/E 高于同行参照 20.0%")
                handoff = navigation.get_by_role("link", name="Monitor", exact=True)
            else:
                page.get_by_role("button", name="保存当前 SEC 证据", exact=True).click()
                evidence = page.locator(".st-key-sec-review-panel")
                playwright.expect(evidence.get_by_role("heading", name="已保存证据重放")).to_be_visible()
                download = evidence.get_by_role("button", name="下载当前证据包", exact=True)
                playwright.expect(download).to_be_enabled()
                handoff = page.get_by_role("link", name="在 Monitor 查看待核查事项", exact=True)
            playwright.expect(handoff).to_have_attribute("href", "?mode=research&page=monitor")
            original_brief = brief.inner_text()
            original_evidence = tuple(line for line in evidence.inner_text().splitlines()
                                      if line and line != "已保存本次观察。")
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
            playwright.expect(page.get_by_role("heading", name="Follow-up Queue")).to_be_visible()
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
                playwright.expect(page.get_by_role("heading", name="FICT SEC 证据复核")).to_be_visible()
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
                notes_return = page.get_by_role("link", name="返回 FICT 证据复核", exact=True)
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

            overview = page.get_by_role("radio", name="概览", exact=True)
            page.locator("label").filter(has=overview).click()
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
