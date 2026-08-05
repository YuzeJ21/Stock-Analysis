from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from streamlit.testing.v1 import AppTest

from src.company_workbench_cash_generation_preview import (
    CashGenerationPreviewMetric,
    CompanyWorkbenchCashGenerationPreview,
)
from src.observation_recency import load_observation_recency


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_APP = PROJECT_ROOT / "src/dashboard.py"


def test_public_routes_render_without_exceptions_and_keep_core_markers():
    from src.dashboard_render_smoke import PUBLIC_RENDER_ROUTES, render_public_routes

    results = render_public_routes(Path("."))

    assert [result.name for result in results] == [
        "Home",
        "Stock Selector",
        "Single-Stock Report",
        "Data Health",
        "Proof History",
    ]
    assert all(result.exceptions == () for result in results)
    assert all(result.missing_markers == () for result in results)
    assert all(result.forbidden_markers == () for result in results)
    assert all(result.expanded_advanced == () for result in results)


def test_company_workbench_renders_independent_observation_states_for_avgo_spy_and_qqq():
    from src.dashboard_render_smoke import DashboardRenderRoute, render_public_routes

    review_date = date(2026, 7, 27)
    observation = load_observation_recency(
        Path("data/prices.csv"),
        selected_ticker="AVGO",
        as_of=review_date,
    )
    route = DashboardRenderRoute(
        name="AVGO Company Workbench observation recency",
        query_params=(
            ("mode", "research"),
            ("page", "company-workbench"),
            ("ticker", "AVGO"),
            ("open", "1"),
        ),
        required_markers=(
            "Company Workbench",
            "profile_price_lane",
            "AVGO",
            "SPY",
            "QQQ",
            "Quant interpretation boundary",
            "Research-only",
        ),
    )

    with patch(
        "src.dashboard.pd.Timestamp.now",
        return_value=datetime(2026, 7, 27, tzinfo=timezone.utc),
    ):
        result = render_public_routes(Path("."), routes=(route,))[0]
        rendered = "\n".join(result.rendered_blocks)

    assert result.exceptions == ()
    assert result.missing_markers == ()
    assert result.forbidden_markers == ()
    assert result.expanded_advanced == ()
    assert "observation-recency-summary" in rendered
    assert rendered.count("<section class='observation-recency-summary") == 1
    assert "provenance_unverified" not in rendered
    for row in (
        observation.selected_ticker,
        observation.profile_price_lane,
        *observation.benchmarks,
    ):
        message = (
            "Historical context only; no current-market claim is made."
            if row.state == "stale_review_only"
            else row.message
        )
        assert (
            f"<small>Scope</small><strong>{row.scope}</strong>"
            f"<small>Through date</small><span>{row.through_date or 'Unavailable'}</span>"
            f"<small>State</small><span>{row.state}</span>"
            f"<p>{message}</p>"
        ) in rendered


def test_research_routes_keep_observation_summary_and_advanced_evidence_responsive():
    import pytest

    from src.public_performance_gate import (
        _local_demo_server,
        _wait_for_dom_stability,
        _wait_for_visible_text,
        find_chrome_executable,
    )

    chrome = find_chrome_executable()
    if chrome is None:
        pytest.skip("Chrome-compatible browser is unavailable")
    playwright = pytest.importorskip("playwright.sync_api")
    routes = (
        ("/?mode=research&page=research-desk", "Weekly research summary", "selected_ticker"),
        ("/?mode=research&page=discover", "Find a Company", "selected_ticker"),
        (
            "/?mode=research&page=company-workbench&ticker=AVGO&open=1",
            "Company Workbench",
            "AVGO",
        ),
        (
            "/?mode=research&page=monitor",
            "Research Discipline Review",
            "selected_ticker",
        ),
    )

    with _local_demo_server(Path("."), timeout_seconds=60) as base_url:
        with playwright.sync_playwright() as runtime:
            browser = runtime.chromium.launch(
                executable_path=str(chrome),
                headless=True,
            )
            try:
                for width, height in ((1280, 720), (390, 844)):
                    for route, marker, selected_scope in routes:
                        context = browser.new_context(
                            viewport={"width": width, "height": height}
                        )
                        page = context.new_page()
                        try:
                            page.goto(
                                f"{base_url}{route}",
                                wait_until="domcontentloaded",
                                timeout=60_000,
                            )
                            _wait_for_visible_text(page, marker, timeout_seconds=60)
                            _wait_for_dom_stability(page, timeout_seconds=60)

                            summaries = page.locator(
                                "section.observation-recency-summary"
                            )
                            advanced = page.locator("details").filter(
                                has_text="Advanced: market observation recency"
                            )
                            assert summaries.count() == 1
                            assert advanced.count() == 1

                            advanced.locator("summary").click()
                            evidence = advanced.locator(
                                "section.observation-recency-evidence"
                            )
                            cards = evidence.locator(
                                "article.observation-recency-item"
                            )
                            assert evidence.count() == 1
                            assert cards.count() == 4
                            assert [
                                cards.nth(index).locator("strong").first.inner_text()
                                for index in range(cards.count())
                            ] == [
                                selected_scope,
                                "profile_price_lane",
                                "SPY",
                                "QQQ",
                            ]

                            if width == 390:
                                assert evidence.evaluate(
                                    "node => node.scrollWidth <= node.clientWidth"
                                )
                                boxes = [
                                    cards.nth(index).bounding_box()
                                    for index in range(cards.count())
                                ]
                                assert all(box is not None for box in boxes)
                                assert len(
                                    {round(box["y"]) for box in boxes if box is not None}
                                ) == 4
                                assert all(
                                    0 <= box["x"]
                                    and box["x"] + box["width"] <= width
                                    for box in boxes
                                    if box is not None
                                )
                        finally:
                            context.close()
            finally:
                browser.close()


def test_research_routes_render_without_exceptions_and_keep_answer_first_markers():
    from src.dashboard_render_smoke import RESEARCH_RENDER_ROUTES, render_public_routes

    assert [route.name for route in RESEARCH_RENDER_ROUTES] == [
        "Research Desk",
        "Discover",
        "Company Workbench",
        "Monitor",
        "Research Data Health",
        "Research Proof History",
    ]
    discover_route = next(
        route for route in RESEARCH_RENDER_ROUTES if route.name == "Discover"
    )
    assert "Find a Company" in discover_route.required_markers
    assert "Screen eligibility — when supported" in discover_route.required_markers
    assert "Browse saved companies" in discover_route.required_markers
    results = render_public_routes(Path("."), routes=RESEARCH_RENDER_ROUTES)

    assert all(result.exceptions == () for result in results)
    assert all(result.missing_markers == () for result in results)
    assert all(result.forbidden_markers == () for result in results)
    assert all(result.expanded_advanced == () for result in results)
    primary_routes = {
        "Research Desk",
        "Discover",
        "Company Workbench",
        "Monitor",
    }
    assert all(
        "profile_price_lane" in "\n".join(result.rendered_blocks)
        for result in results
        if result.name in primary_routes
    )


def test_fixed_semantic_main_bridge_html_renders_once_across_all_workspaces(
    tmp_path,
    monkeypatch,
):
    from src.accessibility_bridge import SEMANTIC_MAIN_BRIDGE_HTML
    from src.dashboard_render_smoke import RESEARCH_RENDER_ROUTES

    monkeypatch.chdir(tmp_path)
    cases = [
        ("Public Home", {"mode": "public"}),
        ("Operator Home", {"mode": "operator"}),
        *(
            (route.name, dict(route.query_params))
            for route in RESEARCH_RENDER_ROUTES
        ),
    ]

    for name, query_params in cases:
        app = AppTest.from_file(DASHBOARD_APP, default_timeout=120)
        app.query_params.update(query_params)
        app.run(timeout=120)

        bridge_elements = [
            html
            for html in app.get("html")
            if html.proto.body == SEMANTIC_MAIN_BRIDGE_HTML.strip()
        ]
        assert not app.exception, name
        assert len(bridge_elements) == 1, name
        assert bridge_elements[0].proto.unsafe_allow_javascript is True, name


def test_research_route_renders_one_fragment_skip_link_and_one_existing_answer_target():
    from src.dashboard_render_smoke import DashboardRenderRoute, render_public_routes

    route = DashboardRenderRoute(
        name="Research skip focus",
        query_params=(
            ("mode", "research"),
            ("page", "company-workbench"),
            ("ticker", "AVGO"),
            ("open", "1"),
        ),
        required_markers=("Company Workbench",),
    )

    result = render_public_routes(Path("."), routes=(route,))[0]
    rendered = "\n".join(result.rendered_blocks)

    assert result.exceptions == ()
    assert rendered.count("class='public-skip-link'") == 1
    assert rendered.count("href='#public-page-answer'") == 1
    assert rendered.count("id='public-page-answer'") == 1


def test_research_skip_link_is_first_in_streamlit_sidebar_dom_bucket():
    app = AppTest.from_file(DASHBOARD_APP, default_timeout=120)
    app.query_params.update({"mode": "research", "page": "research-desk"})
    app.run(timeout=120)

    assert not app.exception
    sidebar_markdown = [item.value for item in app.sidebar.markdown]
    main_markdown = [item.value for item in app.main.markdown]

    assert "class='public-skip-link'" in sidebar_markdown[0]
    assert not any("class='public-skip-link'" in value for value in main_markdown)


def test_public_skip_link_stays_in_first_sidebar_dom_bucket_and_renders_once():
    app = AppTest.from_file(DASHBOARD_APP, default_timeout=120)
    app.query_params.update({"mode": "public"})
    app.run(timeout=120)

    assert not app.exception
    sidebar_markdown = [item.value for item in app.sidebar.markdown]
    main_markdown = [item.value for item in app.main.markdown]
    rendered = sidebar_markdown + main_markdown

    assert "class='public-skip-link'" in sidebar_markdown[0]
    assert not any("class='public-skip-link'" in value for value in main_markdown)
    assert sum("class='public-skip-link'" in value for value in rendered) == 1


def test_focused_skip_link_is_a_visible_horizontal_banner_in_public_and_research():
    import pytest

    from src.public_performance_gate import (
        _local_demo_server,
        _wait_for_dom_stability,
        _wait_for_visible_text,
        find_chrome_executable,
    )

    chrome = find_chrome_executable()
    if chrome is None:
        pytest.skip("Chrome-compatible browser is unavailable")
    playwright = pytest.importorskip("playwright.sync_api")
    cases = (
        ("/?mode=public", "What is this product and where do I start?"),
        ("/?mode=research&page=research-desk", "Weekly research summary"),
    )

    with _local_demo_server(Path("."), timeout_seconds=60) as base_url:
        with playwright.sync_playwright() as runtime:
            browser = runtime.chromium.launch(
                executable_path=str(chrome),
                headless=True,
            )
            try:
                for width, height in ((1280, 720), (390, 844)):
                    for route, marker in cases:
                        context = browser.new_context(
                            viewport={"width": width, "height": height}
                        )
                        page = context.new_page()
                        try:
                            page.goto(
                                f"{base_url}{route}",
                                wait_until="domcontentloaded",
                                timeout=60_000,
                            )
                            _wait_for_visible_text(
                                page,
                                marker,
                                timeout_seconds=60,
                            )
                            _wait_for_dom_stability(page, timeout_seconds=60)
                            page.evaluate(
                                "document.activeElement && document.activeElement.blur()"
                            )
                            page.keyboard.press("Tab")

                            skip_links = page.locator(
                                "a.public-skip-link[href='#public-page-answer']"
                            )
                            active = page.evaluate(
                                """
                                () => {
                                  const element = document.activeElement;
                                  const rect = element.getBoundingClientRect();
                                  return {
                                    label: element.getAttribute("aria-label"),
                                    href: element.getAttribute("href"),
                                    left: rect.left,
                                    top: rect.top,
                                    right: rect.right,
                                    bottom: rect.bottom,
                                    width: rect.width,
                                    height: rect.height
                                  };
                                }
                                """
                            )

                            assert skip_links.count() == 1
                            assert active["label"] == "Skip to page answer"
                            assert active["href"] == "#public-page-answer"
                            assert 0 <= active["left"] < active["right"] <= width
                            assert 0 <= active["top"] < active["bottom"] <= height
                            assert active["width"] >= 120
                            assert 36 <= active["height"] <= 64
                            assert active["width"] >= active["height"] * 2
                        finally:
                            context.close()
            finally:
                browser.close()


def test_authoring_composer_renders_once_only_in_closed_research_company_workbench():
    workbench = AppTest.from_file(DASHBOARD_APP, default_timeout=120)
    workbench.query_params.update(
        {"mode": "research", "page": "company-workbench", "ticker": "NVDA", "open": "1"}
    )
    workbench.run(timeout=120)

    assert not workbench.exception
    composer_expanders = [
        item for item in workbench.expander if item.label == "Add a reviewed research record"
    ]
    assert len(composer_expanders) == 1
    assert not composer_expanders[0].proto.expanded
    assert not any(
        item.proto.expanded for item in workbench.expander if item.label.startswith("Advanced:")
    )

    public_report = AppTest.from_file(DASHBOARD_APP, default_timeout=120)
    public_report.query_params.update(
        {"mode": "public", "page": "single-stock-report", "ticker": "NVDA", "open": "1"}
    )
    public_report.run(timeout=120)

    assert not public_report.exception
    assert not any(item.label == "Add a reviewed research record" for item in public_report.expander)

    operator_report = AppTest.from_file(DASHBOARD_APP, default_timeout=120)
    operator_report.query_params.update(
        {"mode": "operator", "page": "single-stock-report", "ticker": "NVDA", "open": "1"}
    )
    operator_report.run(timeout=120)

    assert not operator_report.exception
    assert not any(item.label == "Add a reviewed research record" for item in operator_report.expander)


def _html_brief_app(*, mode: str = "research", ticker: str = "NVDA", open_report: bool = True) -> AppTest:
    app = AppTest.from_file(DASHBOARD_APP, default_timeout=120)
    query = {"mode": mode, "page": "company-workbench", "ticker": ticker}
    if open_report:
        query["open"] = "1"
    app.query_params.update(query)
    return app.run(timeout=120)


def test_company_workbench_html_brief_is_one_collapsed_research_only_in_memory_surface():
    """Catches a missing, duplicated, expanded, or non-research HTML brief surface."""

    workbench = _html_brief_app()

    assert not workbench.exception
    expanders = [item for item in workbench.expander if item.label == "HTML Research Brief"]
    buttons = [
        item
        for item in workbench.get("download_button")
        if item.label == "Download HTML Research Brief"
    ]
    fragments = [
        item.proto.body
        for item in workbench.get("html")
        if "class=\"srcc-html-brief\"" in item.proto.body
    ]
    assert len(expanders) == 1
    assert expanders[0].proto.expanded is False
    assert len(buttons) == 1
    assert len(fragments) == 1
    assert fragments[0].startswith("<style>")
    assert '<article class="srcc-html-brief"' in fragments[0]
    assert "<script" not in fragments[0].lower()
    assert "file://" not in fragments[0].lower()
    assert "/Users/" not in fragments[0]

    for mode in ("public", "operator"):
        other = AppTest.from_file(DASHBOARD_APP, default_timeout=120)
        other.query_params.update(
            {"mode": mode, "page": "single-stock-report", "ticker": "NVDA", "open": "1"}
        )
        other.run(timeout=120)
        assert not other.exception
        assert not any(item.label == "HTML Research Brief" for item in other.expander)
        assert not any(
            item.label == "Download HTML Research Brief"
            for item in other.get("download_button")
        )

    closed = _html_brief_app(open_report=False)
    assert not closed.exception
    assert not any(item.label == "HTML Research Brief" for item in closed.expander)


@pytest.mark.parametrize(
    ("ticker", "bridge_class", "bridge_text"),
    (
        ("NVDA", "srcc-state-available", "State: complete"),
        ("AAME", "srcc-state-partial", "State: partial"),
        ("SPY", "srcc-state-withheld", "State: withheld"),
    ),
)
def test_company_workbench_html_brief_renders_complete_partial_and_withheld_bridges(
    ticker, bridge_class, bridge_text
):
    """Catches collapsing an independently gated DCF bridge into a generic state."""

    app = _html_brief_app(ticker=ticker)
    fragments = [
        item.proto.body
        for item in app.get("html")
        if "class=\"srcc-html-brief\"" in item.proto.body
    ]

    assert not app.exception
    assert len(fragments) == 1
    bridge = fragments[0].split('data-section="dcf-bridge"', 1)[1].split(
        "</section>", 1
    )[0]
    assert bridge_class in bridge
    assert bridge_text in bridge


def test_company_workbench_html_brief_renders_the_prepared_modified_session_result():
    """Catches ignoring the prepared session result or recalculating from canonical report state."""

    app = AppTest.from_string(
        """
from pathlib import Path
import streamlit as st
from src.dashboard import (
    build_profile_context,
    build_provider,
    build_stock_report,
    render_single_stock_report,
)
from src.scenario_lab_session import scenario_lab_widget_keys

context = build_profile_context(project_root=Path('.'))
provider = build_provider('local', base_dir=Path('.'))
report = build_stock_report('NVDA', provider).to_dict()
report['asset_type'] = 'company'
report['valuation_snapshot']['source_metadata'] = [{
    'source': 'synthetic-test-only-reviewed-source',
    'source_ref': 'https://example.com/nvda-source',
    'as_of_date': '2026-06-30',
}]
st.session_state['single_stock_report_payload'] = report
st.session_state['single_stock_report_ticker'] = 'NVDA'
st.session_state['single_stock_report_provider'] = 'local'
keys = scenario_lab_widget_keys(context.profile_key, 'NVDA')
st.session_state[keys['wacc']] = 0.15
render_single_stock_report(
    None,
    False,
    public_mode=True,
    profile_context=context,
    research_mode=True,
)
""",
        default_timeout=120,
    )
    app.query_params.update({"ticker": "NVDA", "open": "1"})
    app.run(timeout=120)

    fragments = [
        item.proto.body
        for item in app.get("html")
        if "class=\"srcc-html-brief\"" in item.proto.body
    ]
    assert not app.exception
    assert len(fragments) == 1
    base_row = fragments[0].split('<th scope="row">Base</th>', 1)[1].split(
        "</tr>", 1
    )[0]
    assert "15.0%" in base_row
    assert "9.0%" not in base_row


def test_company_workbench_download_button_receives_the_pure_spec_exactly():
    """Catches changing bytes, MIME, filename, key, or click behavior at the Streamlit boundary."""

    import streamlit as st
    from src.company_workbench_html import company_workbench_html_download_spec

    captured_snapshots = []
    captured_downloads = []
    from src import company_workbench_html as html_brief

    real_builder = html_brief.build_company_workbench_html_snapshot
    real_download = st.download_button

    def capture_builder(inputs):
        snapshot = real_builder(inputs)
        captured_snapshots.append(snapshot)
        return snapshot

    def capture_download(*args, **kwargs):
        captured_downloads.append((args, kwargs))
        return real_download(*args, **kwargs)

    with patch.object(html_brief, "build_company_workbench_html_snapshot", side_effect=capture_builder), patch.object(
        st, "download_button", side_effect=capture_download
    ):
        app = _html_brief_app()

    assert not app.exception
    assert len(captured_snapshots) == 1
    assert len(captured_downloads) == 1
    expected = company_workbench_html_download_spec(captured_snapshots[0])
    args, kwargs = captured_downloads[0]
    assert args == ("Download HTML Research Brief",)
    assert kwargs["data"] == expected.data
    assert kwargs["file_name"] == expected.file_name
    assert kwargs["mime"] == expected.mime
    assert kwargs["key"] == "company-workbench-html:default:NVDA"
    assert kwargs["on_click"] == "ignore"


@pytest.mark.parametrize(
    "target",
    (
        "src.data_update.refresh_price_update_status_output",
        "src.readiness_engine.build_ticker_readiness_report",
        "src.stock_report.build_stock_report_markdown",
        "pathlib.Path.write_text",
        "src.research_thesis_journal.append_journal_entry",
        "src.catalyst_evidence_timeline.append_reviewed_event",
        "requests.sessions.Session.request",
        "src.providers.yfinance_provider.YFinanceProvider.__init__",
    ),
)
def test_company_workbench_html_brief_does_not_enter_mutating_or_external_paths(target):
    """Catches an ordinary preview that refreshes, writes, records, or contacts a provider."""

    with patch(target, side_effect=AssertionError(f"ordinary HTML brief called {target}")):
        app = _html_brief_app()

    assert not app.exception
    assert any(item.label == "HTML Research Brief" for item in app.expander)


def test_monitor_renders_evidence_brief_before_filtered_discipline_without_ranking():
    from src.dashboard_render_smoke import DashboardRenderRoute, render_public_routes

    route = DashboardRenderRoute(
        name="Monitor Research Discipline Review",
        query_params=(("mode", "research"), ("page", "monitor")),
        required_markers=(
            "Evidence Monitor Brief",
            "WEEKLY RESEARCH SUMMARY",
            "RESEARCH FOLLOW-UP",
            "SCHEDULED CONTEXT",
            "EVIDENCE FRESHNESS",
            "Research Discipline Review",
            "Research change monitor",
            "Advanced: Research Discipline evidence",
            "Research-only",
        ),
    )

    result = render_public_routes(Path("."), routes=(route,))[0]
    rendered = "\n".join(result.rendered_blocks)

    assert result.exceptions == ()
    assert rendered.index("Evidence Monitor Brief") < rendered.index("WEEKLY RESEARCH SUMMARY")
    assert rendered.index("WEEKLY RESEARCH SUMMARY") < rendered.index("RESEARCH FOLLOW-UP")
    assert rendered.index("RESEARCH FOLLOW-UP") < rendered.index("SCHEDULED CONTEXT")
    assert rendered.index("SCHEDULED CONTEXT") < rendered.index("EVIDENCE FRESHNESS")
    assert rendered.index("EVIDENCE FRESHNESS") < rendered.index("Research Discipline Review")
    assert rendered.index("Research Discipline Review") < rendered.index("Research change monitor")
    assert "company rank" not in rendered.lower()
    assert "expected return" not in rendered.lower()


def test_avgo_company_workbench_renders_one_authoritative_peer_task():
    from src.dashboard_render_smoke import DashboardRenderRoute, render_public_routes

    route = DashboardRenderRoute(
        name="AVGO Company Workbench task arbitration",
        query_params=(
            ("mode", "research"),
            ("page", "company-workbench"),
            ("ticker", "AVGO"),
            ("open", "1"),
        ),
        required_markers=("Company Workbench", "Research-only"),
    )

    result = render_public_routes(Path("."), routes=(route,))[0]
    rendered = "\n".join(result.rendered_blocks)
    task_blocks = tuple(block for block in result.rendered_blocks if "ONE NEXT TASK" in block)
    change_blocks = tuple(block for block in result.rendered_blocks if "EVIDENCE CHANGE" in block)

    assert result.exceptions == ()
    assert len(change_blocks) == 1
    assert "No unresolved source-backed change is queued for this company." in change_blocks[0]
    assert "no queued change" in change_blocks[0]
    assert "snapshot evidence only" not in change_blocks[0]
    assert len(task_blocks) == 1
    assert task_blocks[0].count("ONE NEXT TASK") == 1
    assert "<div class='signal-title'>Add peer mappings</div>" in task_blocks[0]
    assert rendered.count("FORWARD-VIEW LANE UNBLOCK") == 1
    assert "NEXT RESEARCH TASK" not in rendered


def test_avgo_company_workbench_renders_one_selected_answer_with_ticker_handoff():
    from src.dashboard_render_smoke import DashboardRenderRoute, render_public_routes

    route = DashboardRenderRoute(
        name="AVGO Company Workbench answer handoff",
        query_params=(
            ("mode", "research"),
            ("page", "company-workbench"),
            ("ticker", "AVGO"),
            ("open", "1"),
        ),
        required_markers=("Company Workbench", "Open Data Health", "Research-only"),
    )

    result = render_public_routes(Path("."), routes=(route,))[0]
    rendered = "\n".join(result.rendered_blocks)

    assert result.exceptions == ()
    assert rendered.count("aria-label='Selected ticker answer'") == 1
    assert "?mode=research&amp;page=data-health&amp;ticker=AVGO" in rendered


def test_avgo_company_workbench_renders_one_six_lane_decision_lab_after_selected_answer():
    from src.dashboard_render_smoke import DashboardRenderRoute, render_public_routes

    route = DashboardRenderRoute(
        name="AVGO Company Workbench Decision Lab",
        query_params=(
            ("mode", "research"),
            ("page", "company-workbench"),
            ("ticker", "AVGO"),
            ("open", "1"),
        ),
        required_markers=(
            "Use now",
            "What Changed",
            "Research Decision Lab",
            "PLAN",
            "EVIDENCE",
            "INVALIDATION",
            "SCENARIO",
            "REVIEW TRIGGER",
            "LEARNING",
            "NEXT PROCESS STEP",
            "Research Conclusion",
            "Next Research Task",
        ),
    )

    result = render_public_routes(Path("."), routes=(route,))[0]
    rendered = "\n".join(result.rendered_blocks)

    assert result.exceptions == ()
    assert result.missing_markers == ()
    assert result.expanded_advanced == ()
    assert rendered.count("Research Decision Lab") == 1
    assert rendered.count("NEXT PROCESS STEP") == 1
    assert rendered.index("Use now") < rendered.index("Research Decision Lab")
    assert rendered.index("Research Decision Lab") < rendered.index("Research Conclusion")


def test_research_render_smoke_output_names_the_contract_and_failures():
    from src.dashboard_render_smoke import DashboardRenderResult, render_dashboard_smoke

    rendered = render_dashboard_smoke(
        [
            DashboardRenderResult(
                name="Company Workbench",
                exceptions=(),
                missing_markers=(),
                forbidden_markers=("ArrowInvalid",),
                expanded_advanced=("Advanced Evidence",),
            )
        ],
        contract_name="Research dashboard render smoke",
    )

    assert rendered.startswith("Research dashboard render smoke")
    assert "forbidden markers: ArrowInvalid" in rendered
    assert "expanded advanced sections: Advanced Evidence" in rendered


def test_explicit_amd_cash_preview_route_renders_accepted_answer_without_network():
    from src.dashboard_render_smoke import DashboardRenderRoute, render_public_routes

    preview = CompanyWorkbenchCashGenerationPreview(
        ticker="AMD",
        fiscal_period="2026-Q1",
        status="accepted_for_review",
        message="Accepted SEC evidence supports a cash-generation review preview.",
        operating_margin=CashGenerationPreviewMetric(
            "operating_margin", "preview_available", 1_476_000_000 / 10_253_000_000,
            "2026-Q1", (), ""
        ),
        free_cash_flow=CashGenerationPreviewMetric(
            "free_cash_flow", "preview_available", 2_566_000_000, "2026-Q1", (), ""
        ),
        fcf_margin=CashGenerationPreviewMetric(
            "fcf_margin", "preview_available", 2_566_000_000 / 10_253_000_000,
            "2026-Q1", (), ""
        ),
        blockers=(),
        withheld_metrics=(),
        accession="0000002488-26-000076",
        source_url="https://www.sec.gov/Archives/edgar/data/2488/000000248826000076/amd-20260328.htm",
        accepted_at="2026-05-05T22:06:27+00:00",
        cutoff="2026-07-21T03:59:59+00:00",
        capex_sign_evidence="explicit_filed_table_outflow",
        components=(),
    )
    route = DashboardRenderRoute(
        name="AMD Company Workbench cash preview",
        query_params=(
            ("mode", "research"),
            ("page", "company-workbench"),
            ("ticker", "AMD"),
            ("open", "1"),
            ("cash_preview", "1"),
        ),
        required_markers=(
            "Cash-generation review preview",
            "not production evidence",
            "14.4%",
            "2,566,000,000",
            "25.0%",
        ),
    )

    with patch(
        "src.company_workbench_cash_generation_preview_loader."
        "load_company_workbench_cash_generation_preview",
        return_value=preview,
    ):
        result = render_public_routes(Path("."), routes=(route,))[0]

    assert result.exceptions == ()
    assert result.missing_markers == ()
    assert result.forbidden_markers == ()
    assert result.expanded_advanced == ()


def test_normal_company_workbench_route_never_loads_cash_preview():
    from src.dashboard_render_smoke import DashboardRenderRoute, render_public_routes

    route = DashboardRenderRoute(
        name="Normal Company Workbench",
        query_params=(
            ("mode", "research"),
            ("page", "company-workbench"),
            ("ticker", "NVDA"),
            ("open", "1"),
        ),
        required_markers=("Company Workbench", "Business Trend", "Research-only"),
    )

    with patch(
        "src.company_workbench_cash_generation_preview_loader."
        "load_company_workbench_cash_generation_preview",
        side_effect=AssertionError("normal Workbench must not load SEC preview"),
    ):
        result = render_public_routes(Path("."), routes=(route,))[0]

    assert result.exceptions == ()
    assert result.missing_markers == ()


def test_normal_amd_company_workbench_route_never_loads_cash_preview():
    from src.dashboard_render_smoke import DashboardRenderRoute, render_public_routes

    route = DashboardRenderRoute(
        name="Normal AMD Company Workbench",
        query_params=(
            ("mode", "research"),
            ("page", "company-workbench"),
            ("ticker", "AMD"),
            ("open", "1"),
        ),
        required_markers=("Company Workbench", "Business Trend", "Research-only"),
    )
    with patch(
        "src.company_workbench_cash_generation_preview_loader."
        "load_company_workbench_cash_generation_preview",
        side_effect=AssertionError("normal AMD Workbench must not load cash preview"),
    ):
        result = render_public_routes(Path("."), routes=(route,))[0]
    assert result.exceptions == ()
    assert result.missing_markers == ()
