"""Exercise the online company-to-Monitor round trip in a real browser."""

import os
from pathlib import Path
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
        assert query in {"Fictional", "FICT"}
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
        assert (ticker, expected_cik) == ("FICT", "0000001234")
        if refresh_requested:
            record("peer-valuation")
            state["fixture-peer-valuation"] = {
                "status": "research_comparison", "ticker": ticker, "metric": "reported_annual_diluted_pe",
                "subject": {"ticker": ticker, "price_date": "2026-10-30", "multiple": 30},
                "peers": [{"ticker": symbol, "price_date": "2026-10-30"} for symbol in ("FA", "FB", "FC")],
                "peer_count": 3, "peer_median": 25, "premium_fraction": 0.2,
            }
        return state.get("fixture-peer-valuation", {"status": "not_requested"})

    with pytest.MonkeyPatch.context() as patch:
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


@pytest.mark.parametrize(
    ("width", "height", "monitor_action"),
    [(1280, 720, "workflow"), (390, 844, "receipt")],
    ids=["desktop-workflow-rail", "phone-receipt-handoff"],
)
def test_online_research_round_trip_keeps_live_evidence(
    research_browser_server, tmp_path, width, height, monitor_action,
):
    chrome = find_chrome_executable()
    if chrome is None:
        pytest.skip("Chrome-compatible browser is unavailable")
    playwright = pytest.importorskip("playwright.sync_api")

    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(executable_path=str(chrome), headless=True)
        try:
            page = browser.new_page(
                viewport={"width": width, "height": height},
                color_scheme="dark" if width <= 640 else None,
            )
            page.set_default_timeout(15_000)
            # UI resources and evidence providers in this test must remain local.
            page.route("**/*", lambda route: (
                route.continue_() if route.request.url.startswith(research_browser_server + "/")
                else route.abort()
            ))
            documents = []
            streams = []

            def record_document(request):
                if request.is_navigation_request() and request.resource_type == "document":
                    documents.append(request.url)

            page.on("request", record_document)
            page.on("websocket", lambda socket: streams.append(socket.url))

            page.goto(f"{research_browser_server}/?mode=research&page=discover")
            page.get_by_role("textbox", name="Search SEC companies online").fill("Fictional")
            page.get_by_role("button", name="Search SEC now").click()
            playwright.expect(page.get_by_text("No local ticker row", exact=True)).to_be_visible()
            page.get_by_text("Open company evidence", exact=True).click()

            brief = page.get_by_role("region", name="Company Brief")
            playwright.expect(brief.get_by_role("heading", name="FICT Company Brief")).to_be_visible()
            assert len(documents) == len(streams) == 1, "Discover opened a new research session"
            calls = tmp_path / "provider-calls.txt"
            assert calls.read_text().splitlines() == ["search"]

            page.get_by_role("button", name="更新财报与价格").click()
            playwright.expect(brief).to_contain_text("3 个年度")
            playwright.expect(brief).to_contain_text("3 个日线观察")
            loaded_brief = brief.inner_text()
            price_history = page.get_by_role("region", name="Daily price history", exact=True)
            playwright.expect(price_history).to_contain_text("USD 11")
            original_price_history = price_history.inner_text()

            notes = page.get_by_role("radio", name="研究记录", exact=True)
            page.locator("label").filter(has=notes).click()
            save = page.get_by_role("button", name="保存当前 SEC 证据")
            save.click()
            playwright.expect(page.get_by_role("heading", name="已保存证据重放")).to_be_visible()
            save.click()
            unchanged = page.get_by_text("未变化 · 已保存的字段数值与口径一致。", exact=True)
            playwright.expect(unchanged).to_be_visible()
            receipts_before = {path: path.read_bytes() for path in tmp_path.rglob("*.json")}
            assert len(receipts_before) == 2
            assert calls.read_text().splitlines() == ["search", "financial", "prices", "company-profile"]

            if monitor_action == "workflow":
                selected_section = page.get_by_role("radio", name="财务趋势", exact=True)
                page.locator("label").filter(has=selected_section).click()
                playwright.expect(page.get_by_role("heading", name="财务趋势", exact=True)).to_be_visible()
                return_section = "financials"
                return_action = "Return to FICT Company Workbench"
                navigation = page.get_by_role("navigation", name="Personal research workflow")
                navigation.get_by_text("Monitor", exact=True).click()
            else:
                selected_section = notes
                return_section = "notes"
                return_action = "返回 FICT 证据复核"
                page.get_by_text("在 Monitor 查看待核查事项", exact=True).click()
            playwright.expect(page.get_by_role("heading", name="Follow-up Queue")).to_be_visible(timeout=15_000)
            playwright.expect(page.get_by_role("heading", name="FICT SEC 证据复核")).to_be_visible()
            assert len(documents) == len(streams) == 1, "Monitor opened a new research session"
            if width <= 640:
                return_label = "Return to FICT Company Workbench"
                monitor_return = page.get_by_role("button", name=return_label, exact=True)
                foreground, background = monitor_return.get_by_text(return_label, exact=True).evaluate(
                    """label => [
                        getComputedStyle(label).color,
                        getComputedStyle(label.closest('button')).backgroundColor,
                    ]"""
                )
                contrast = _contrast_ratio(foreground, background)
                assert contrast is not None and contrast >= 4.5, (
                    f"Return action contrast {contrast!r} for {foreground} on {background}"
                )
            page.get_by_text(return_action, exact=True).click()

            playwright.expect(brief.get_by_role("heading", name="FICT Company Brief")).to_be_visible(timeout=15_000)
            playwright.expect(selected_section).to_be_checked()
            assert brief.inner_text() == loaded_brief
            expected_route = {
                "mode": ["research"], "page": ["company-workbench"], "ticker": ["FICT"],
                "online": ["1"], "section": [return_section],
            }
            actual_route = parse_qs(urlsplit(page.url).query)
            assert {key: actual_route.get(key) for key in expected_route} == expected_route
            if monitor_action == "workflow":
                page.locator("label").filter(has=notes).click()
            playwright.expect(unchanged).to_be_visible()
            playwright.expect(save).to_be_enabled()
            overview = page.get_by_role("radio", name="概览", exact=True)
            page.locator("label").filter(has=overview).click()
            playwright.expect(price_history).to_contain_text("USD 11")
            assert price_history.inner_text() == original_price_history
            assert len(documents) == len(streams) == 1, "Returning opened a new research session"
            assert calls.read_text().splitlines() == ["search", "financial", "prices", "company-profile"]
            assert {path: path.read_bytes() for path in tmp_path.rglob("*.json")} == receipts_before

            valuation = page.get_by_role("radio", name="估值与同行", exact=True)
            page.locator("label").filter(has=valuation).click()
            page.get_by_role("button", name="更新在线同行估值").click()
            card = page.get_by_role("region", name="Online peer valuation", exact=True)
            headline = card.get_by_role("heading", name="年度 P/E 高于同行参照 20.0%")
            playwright.expect(headline).to_be_visible()
            page.locator('[data-testid="stMain"]').evaluate('(main) => { main.scrollTop = 0; window.scrollTo(0, 0); }')
            key_facts = card.locator(".peer-comparison-stats > div")
            playwright.expect(key_facts.nth(0)).to_contain_text("2026-10-30")
            playwright.expect(key_facts.nth(1)).to_contain_text("3 家")
            answers = brief.get_by_role("region", name="公司研究摘要")
            valuation_answer = answers.locator('[data-company-answer="valuation"]')
            playwright.expect(valuation_answer).to_contain_text("年度 P/E 高于同行参照 20.0%")
            playwright.expect(valuation_answer).to_contain_text("2026-10-30 收盘 · 3 家合格")
            for field in answers.locator("[data-company-answer]").all():
                box = field.bounding_box()
                assert box and 0 <= box["y"] and box["y"] + box["height"] <= height, box
            valuation_summary = valuation_answer.inner_text()
            valuation_evidence = card.inner_text()
            navigation = page.get_by_role("navigation", name="Personal research workflow")
            navigation.get_by_role("link", name="Monitor", exact=True).click()
            playwright.expect(page.get_by_role("heading", name="Follow-up Queue")).to_be_visible()
            navigation.get_by_role("link", name="Company Workbench", exact=True).click()
            playwright.expect(valuation).to_be_checked()
            assert valuation_answer.inner_text() == valuation_summary
            assert card.inner_text() == valuation_evidence
            assert len(documents) == len(streams) == 1
            assert calls.read_text().splitlines() == [
                "search", "financial", "prices", "company-profile", "peer-valuation",
            ]
        finally:
            browser.close()
