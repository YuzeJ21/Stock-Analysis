import re
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


def test_operator_peer_lane_uses_the_same_saved_counts_as_personal_data_health():
    """Catches Operator dropping saved peer coverage and rendering false zeroes."""

    from src.dashboard_render_smoke import DashboardRenderRoute, render_public_routes

    routes = (
        DashboardRenderRoute(
            name="Operator peer lane saved-count parity",
            query_params=(
                ("mode", "operator"),
                ("page", "data-health"),
                ("lane", "peers"),
                ("drawer", "proof"),
            ),
            required_markers=("Selected Lane Answer", "Peers"),
        ),
        DashboardRenderRoute(
            name="Personal peer lane saved-count authority",
            query_params=(
                ("mode", "research"),
                ("page", "data-health"),
                ("ticker", "AVGO"),
                ("lane", "peers"),
                ("drawer", "proof"),
            ),
            required_markers=("Selected Lane Answer", "Peers"),
        ),
    )

    operator_result, personal_result = render_public_routes(Path("."), routes=routes)
    operator_rendered = "\n".join(operator_result.rendered_blocks)
    personal_rendered = "\n".join(personal_result.rendered_blocks)
    peer_count_pattern = re.compile(r"([1-9][0-9,]*) tickers have mapped peer trend context")
    locked_count_pattern = re.compile(r"([1-9][0-9,]*) locked input rows? remain visible")
    operator_peer_count = peer_count_pattern.search(operator_rendered)
    personal_peer_count = peer_count_pattern.search(personal_rendered)
    operator_count = locked_count_pattern.search(operator_rendered)
    personal_count = locked_count_pattern.search(personal_rendered)

    for result in (operator_result, personal_result):
        assert result.exceptions == ()
        assert result.missing_markers == ()
        assert result.forbidden_markers == ()
    assert operator_peer_count is not None
    assert personal_peer_count is not None
    assert operator_peer_count.group(1) == personal_peer_count.group(1)
    assert operator_count is not None
    assert personal_count is not None
    assert operator_count.group(1) == personal_count.group(1)
    assert "0 tickers have mapped peer trend context" not in operator_rendered
    assert "trusted peer context" not in operator_rendered.lower()
    assert "0 locked input row(s)" not in operator_rendered


def test_public_peer_lane_arrival_renders_the_promised_selected_answer():
    """Catches a Public peer handoff landing on only generic Data Health content."""

    from src.dashboard_render_smoke import DashboardRenderRoute, render_public_routes

    route = DashboardRenderRoute(
        name="Public peer lane arrival",
        query_params=(
            ("mode", "public"),
            ("page", "data-health"),
            ("ticker", "AVGO"),
            ("lane", "peers"),
            ("drawer", "proof"),
        ),
        required_markers=("Selected Lane Answer", "9 tickers have mapped peer trend context"),
    )

    result = render_public_routes(Path("."), routes=(route,))[0]
    rendered = "\n".join(result.rendered_blocks)

    assert result.exceptions == ()
    assert result.missing_markers == ()
    assert (
        rendered.index("data-sr-region='primary-answer'")
        < rendered.index("Selected Lane Answer")
        < rendered.index("data-sr-region='primary-action'")
    )
    assert rendered.index("Selected Lane Answer") < rendered.index("Optional inputs")


def test_personal_data_health_uses_personal_labels_and_selected_lane_first():
    """Catches the shared read-only implementation leaking Public presentation."""

    from src.dashboard_render_smoke import DashboardRenderRoute, render_public_routes

    route = DashboardRenderRoute(
        name="Personal peer lane presentation",
        query_params=(
            ("mode", "research"),
            ("page", "data-health"),
            ("ticker", "AVGO"),
            ("lane", "peers"),
            ("drawer", "proof"),
        ),
        required_markers=("Selected Lane Answer", "translated for the saved research workflow"),
    )

    result = render_public_routes(Path("."), routes=(route,))[0]
    rendered = "\n".join(result.rendered_blocks)

    assert result.exceptions == ()
    assert result.missing_markers == ()
    assert (
        rendered.index("data-sr-region='primary-answer'")
        < rendered.index("Selected Lane Answer")
        < rendered.index("data-sr-region='primary-action'")
    )
    assert rendered.index("Selected Lane Answer") < rendered.index("Optional inputs")
    for public_only in (
        "public review",
        "Public evidence drawer",
        "translated for the public workflow",
        "Public mode keeps the story readable",
        "Public path options",
        "Visitors should",
        "the public page",
        "Public mode shows the product concept",
    ):
        assert public_only not in rendered


@pytest.mark.parametrize("mode", ("public", "research"))
def test_explicit_prices_lane_arrival_names_the_selected_lane(mode):
    """Catches the default lane being visually anonymous when explicitly requested."""

    from src.dashboard_render_smoke import DashboardRenderRoute, render_public_routes

    route = DashboardRenderRoute(
        name=f"{mode} prices lane arrival",
        query_params=(
            ("mode", mode),
            ("page", "data-health"),
            ("ticker", "AVGO"),
            ("lane", "prices"),
            ("drawer", "proof"),
        ),
        required_markers=("Selected Lane Answer — Prices",),
    )

    result = render_public_routes(Path("."), routes=(route,))[0]
    rendered = "\n".join(result.rendered_blocks)

    assert result.exceptions == ()
    assert result.missing_markers == ()
    assert rendered.index("Selected Lane Answer — Prices") < rendered.index("data-sr-region='primary-action'")


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
            "Company Brief",
            "Open evidence and analysis modules",
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
        (
            "/?mode=research&page=research-desk",
            "What needs my attention today?",
            "selected_ticker",
            "Advanced Evidence",
            True,
        ),
        (
            "/?mode=research&page=discover",
            "Find a Company",
            "selected_ticker",
            "Advanced: cohort readiness context",
            False,
        ),
        (
            "/?mode=research&page=company-workbench&ticker=AVGO&open=1",
            "Company Workbench",
            "AVGO",
            "Advanced: selected-company lane coverage",
            False,
        ),
        (
            "/?mode=research&page=monitor",
            "Follow-up Queue",
            "selected_ticker",
            "Advanced: Monitor evidence",
            False,
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
                    for route, marker, selected_scope, drawer_label, nested_recency in routes:
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

                            drawer_summary = page.locator("details > summary").filter(
                                has_text=drawer_label
                            )
                            assert drawer_summary.count() == 1
                            drawer_summary.click()
                            advanced = drawer_summary.locator("..")
                            if nested_recency:
                                recency_summary = advanced.locator(
                                    "details > summary"
                                ).filter(has_text="Advanced: market observation recency")
                                assert recency_summary.count() == 1
                                recency_summary.click()
                            summaries = advanced.locator(
                                "section.observation-recency-summary"
                            )
                            assert summaries.count() == 1
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
    proof_route = next(
        route for route in RESEARCH_RENDER_ROUTES if route.name == "Research Proof History"
    )
    assert "Newest reviewed evidence" in proof_route.required_markers
    assert "Latest evidence" not in proof_route.required_markers
    desk_route = next(
        route for route in RESEARCH_RENDER_ROUTES if route.name == "Research Desk"
    )
    assert "Today's Research Brief" in desk_route.required_markers
    assert "What needs my attention today?" in desk_route.required_markers
    assert "Open Data Health" in desk_route.required_markers
    assert "Open Discover" not in desk_route.required_markers
    assert "Weekly research summary" not in desk_route.required_markers
    assert "What should I review next?" not in desk_route.required_markers
    discover_route = next(
        route for route in RESEARCH_RENDER_ROUTES if route.name == "Discover"
    )
    assert "Find a Company" in discover_route.required_markers
    assert "Screen eligibility — when supported" in discover_route.required_markers
    assert "Browse saved companies" in discover_route.required_markers
    data_health_route = next(
        route for route in RESEARCH_RENDER_ROUTES if route.name == "Research Data Health"
    )
    assert ("lane", "peers") in data_health_route.query_params
    assert ("drawer", "proof") in data_health_route.query_params
    assert "Selected Lane Answer" in data_health_route.required_markers
    workbench_route = next(
        route for route in RESEARCH_RENDER_ROUTES if route.name == "Company Workbench"
    )
    for marker in (
        "Company Brief",
        "Use now",
        "Still withheld",
        "What changed",
        "Next research task",
        "Open evidence and analysis modules",
    ):
        assert marker in workbench_route.required_markers
    evidence_contracts = {
        "Research Data Health": "What can I use and what stays unavailable?",
        "Research Proof History": "What evidence changed a readiness state?",
    }
    expected_evidence_regions = (
        "workflow-nav",
        "context",
        "page-title",
        "primary-answer",
        "primary-action",
        "stop-rule",
        "supporting-evidence",
        "advanced-detail",
    )
    for evidence_name, question in evidence_contracts.items():
        route = next(
            route for route in RESEARCH_RENDER_ROUTES if route.name == evidence_name
        )
        assert question in route.required_markers
        assert "Return to Company Workbench" in route.required_markers
        assert "Research-only" in route.required_markers
        assert (
            "Continue the selected-company review without changing evidence state."
            not in route.required_markers
        )
        assert route.required_regions == expected_evidence_regions
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
    workbench = next(result for result in results if result.name == "Company Workbench")
    workbench_blocks = "\n".join(workbench.rendered_blocks)
    assert "Open evidence and analysis modules" in workbench_blocks
    for gated_heading in (
        "## Research Decision Lab",
        "## Business Trend",
        "## Valuation",
        "## Forward View",
        "## What Remains Withheld",
        "## Research Conclusion",
    ):
        assert gated_heading not in workbench_blocks
    assert "HTML Research Brief" not in workbench_blocks
    for retained_detail in (
        "Full Company Brief evidence",
        "What changed",
        "No unresolved source-backed change is queued for this company.",
        "Research-only: this brief is not a recommendation",
    ):
        assert retained_detail in workbench_blocks
    for evidence_name in ("Research Data Health", "Research Proof History"):
        evidence_blocks = "\n".join(
            next(result for result in results if result.name == evidence_name).rendered_blocks
        )
        assert evidence_blocks.count("Return to Company Workbench") == 1
        assert "Continue the selected-company review without changing evidence state." not in evidence_blocks
        assert "?mode=public&page=single-stock-report" not in evidence_blocks


def test_company_workbench_opens_secondary_modules_only_after_explicit_action():
    app = AppTest.from_file(str(DASHBOARD_APP), default_timeout=120)
    app.query_params.update(
        {
            "mode": "research",
            "page": "company-workbench",
            "ticker": "NVDA",
            "open": "1",
        }
    )
    app.run(timeout=120)

    assert not app.exception
    assert [button.label for button in app.button] == [
        "Open evidence and analysis modules"
    ]

    app.button[0].click().run(timeout=120)

    rendered = "\n".join(
        str(getattr(item, "value", ""))
        for collection in ("markdown", "caption", "header", "subheader")
        for item in getattr(app, collection)
    )
    assert not app.exception
    headings = (
        "## Research Decision Lab",
        "## Business Trend",
        "## Valuation",
        "## Forward View",
        "## What Remains Withheld",
        "## Research Conclusion",
    )
    assert all(heading in rendered for heading in headings)
    assert [rendered.index(heading) for heading in headings] == sorted(
        rendered.index(heading) for heading in headings
    )
    assert [item.label for item in app.expander].count("HTML Research Brief") == 1
    assert "This brief is a snapshot of current saved evidence" in rendered
    assert rendered.count("aria-label='Company Brief'") == 1
    assert "Open evidence and analysis modules" not in [
        button.label for button in app.button
    ]


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
    assert "tabindex='1'" not in rendered
    assert rendered.count("id='public-page-answer'") == 1


def test_research_desk_render_smoke_requires_each_shared_region_once():
    from src.dashboard_render_smoke import RESEARCH_RENDER_ROUTES, render_public_routes

    route = next(route for route in RESEARCH_RENDER_ROUTES if route.name == "Research Desk")
    result = render_public_routes(Path("."), routes=(route,))[0]
    rendered = "\n".join(result.rendered_blocks)

    assert result.exceptions == ()
    assert result.missing_regions == ()
    for region in route.required_regions:
        assert rendered.count(f"data-sr-region='{region}'") == 1


def test_research_skip_link_is_first_in_main_and_sidebar_has_no_navigation_controls():
    app = AppTest.from_file(DASHBOARD_APP, default_timeout=120)
    app.query_params.update({"mode": "research", "page": "research-desk"})
    app.run(timeout=120)

    assert not app.exception
    sidebar_markdown = [item.value for item in app.sidebar.markdown]
    main_markdown = [item.value for item in app.main.markdown]

    assert "class='public-skip-link'" in main_markdown[0]
    assert not any("class='public-skip-link'" in value for value in sidebar_markdown)
    assert not app.sidebar.radio
    assert not app.sidebar.selectbox


def test_public_skip_link_stays_in_first_main_bucket_without_sidebar_controls_and_renders_once():
    app = AppTest.from_file(DASHBOARD_APP, default_timeout=120)
    app.query_params.update({"mode": "public"})
    app.run(timeout=120)

    assert not app.exception
    sidebar_markdown = [item.value for item in app.sidebar.markdown]
    main_markdown = [item.value for item in app.main.markdown]
    rendered = sidebar_markdown + main_markdown

    assert "class='public-skip-link'" in main_markdown[0]
    assert not any("class='public-skip-link'" in value for value in sidebar_markdown)
    assert not app.sidebar.radio
    assert not app.sidebar.selectbox
    assert sum("class='public-skip-link'" in value for value in rendered) == 1


def test_operator_skip_link_stays_first_in_sidebar_before_native_route_controls():
    app = AppTest.from_file(DASHBOARD_APP, default_timeout=120)
    app.query_params.update({"mode": "operator", "page": "overview"})
    app.run(timeout=120)

    assert not app.exception
    sidebar_markdown = [item.value for item in app.sidebar.markdown]
    main_markdown = [item.value for item in app.main.markdown]

    assert "class='public-skip-link'" in sidebar_markdown[0]
    assert not any("class='public-skip-link'" in value for value in main_markdown)
    assert app.sidebar.radio


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
        ("/?mode=research&page=research-desk", "What needs my attention today?"),
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
                            page.locator("body").focus()
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


def test_research_desk_uses_natural_multi_tab_order_in_normal_and_forced_colors():
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

    with _local_demo_server(Path("."), timeout_seconds=60) as base_url:
        with playwright.sync_playwright() as runtime:
            browser = runtime.chromium.launch(
                executable_path=str(chrome),
                headless=True,
            )
            try:
                for forced_colors in ("none", "active"):
                    context = browser.new_context(viewport={"width": 1280, "height": 720})
                    page = context.new_page()
                    try:
                        page.emulate_media(forced_colors=forced_colors)
                        page.goto(
                            f"{base_url}/?mode=research&page=research-desk",
                            wait_until="domcontentloaded",
                            timeout=60_000,
                        )
                        _wait_for_visible_text(
                            page,
                            "What needs my attention today?",
                            timeout_seconds=60,
                        )
                        _wait_for_dom_stability(page, timeout_seconds=60)

                        sequence_contract = page.evaluate(
                            """
                            () => {
                              const selectors = [
                                "[data-sr-region='workflow-nav']",
                                "[data-sr-region='primary-answer']",
                                "[data-sr-region='primary-action']",
                                "[data-sr-region='stop-rule']",
                                "[data-sr-region='supporting-evidence']",
                                "[data-sr-region='advanced-detail']"
                              ];
                              const nodes = selectors.map((selector) => document.querySelector(selector));
                              return {
                                positiveTabindexCount: [...document.querySelectorAll("[tabindex]")]
                                  .filter((node) => node.tabIndex > 0).length,
                                skipTabindex: document.querySelector("a.public-skip-link")
                                  ?.getAttribute("tabindex") ?? null,
                                ordered: nodes.every(Boolean) && nodes.slice(0, -1).every(
                                  (node, index) => Boolean(
                                    node.compareDocumentPosition(nodes[index + 1]) &
                                    Node.DOCUMENT_POSITION_FOLLOWING
                                  )
                                )
                              };
                            }
                            """
                        )
                        assert sequence_contract == {
                            "positiveTabindexCount": 0,
                            "skipTabindex": None,
                            "ordered": True,
                        }

                        page.locator("body").focus()
                        roles = []
                        outlines = []
                        for _ in range(20):
                            page.keyboard.press("Tab")
                            observed = page.evaluate(
                                """
                                () => {
                                  const element = document.activeElement;
                                  let role = "other";
                                  if (element.matches("a.public-skip-link")) role = "skip";
                                  else if (element.closest("nav[aria-label='Personal research workflow']")) role = "navigation";
                                  else if (element.matches("[data-sr-region='primary-action']")) role = "primary-action";
                                  else if (element.matches("summary")) role = "advanced-detail";
                                  const style = getComputedStyle(element);
                                  return {
                                    role,
                                    outlineStyle: style.outlineStyle,
                                    outlineWidth: Number.parseFloat(style.outlineWidth) || 0
                                  };
                                }
                                """
                            )
                            roles.append(observed["role"])
                            outlines.append(
                                (observed["outlineStyle"], observed["outlineWidth"])
                            )
                            if observed["role"] == "advanced-detail":
                                break

                        action_index = roles.index("primary-action")
                        assert roles[0] == "skip"
                        assert action_index > 1
                        assert set(roles[1:action_index]) == {"navigation"}
                        assert roles[action_index + 1] == "advanced-detail"
                        assert all(style not in {"", "none"} for style, _ in outlines)
                        assert all(width >= 3 for _, width in outlines)
                    finally:
                        context.close()
            finally:
                browser.close()


def test_authoring_composer_renders_once_only_after_workbench_modules_open():
    workbench = AppTest.from_file(DASHBOARD_APP, default_timeout=120)
    workbench.query_params.update(
        {"mode": "research", "page": "company-workbench", "ticker": "NVDA", "open": "1"}
    )
    workbench.run(timeout=120)

    assert not workbench.exception
    assert not any(
        item.label == "Add a reviewed research record" for item in workbench.expander
    )
    open_button = next(
        item
        for item in workbench.button
        if item.label == "Open evidence and analysis modules"
    )
    open_button.click().run(timeout=120)

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


def test_company_workbench_single_stock_report_projects_complete_readiness_to_the_selected_evidence_target():
    """Catches the Workbench rail losing the report's authoritative five-lane readiness map."""

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

context = build_profile_context(project_root=Path('.'))
provider = build_provider('local', base_dir=Path('.'))
report = build_stock_report('NVDA', provider).to_dict()
report['readiness'] = {
    'fundamentals_ready': True,
    'dcf_ready': True,
    'peer_ready': True,
    'earnings_available': True,
    'analyst_estimates_available': True,
}
report['valuation_readiness'] = {'dcf_ready': True}
st.session_state['single_stock_report_payload'] = report
st.session_state['single_stock_report_ticker'] = 'NVDA'
st.session_state['single_stock_report_provider'] = 'local'
evidence_target = st.empty()
render_single_stock_report(
    None,
    False,
    public_mode=True,
    profile_context=context,
    research_mode=True,
    selected_evidence_target=evidence_target,
)
""",
        default_timeout=120,
    )
    app.query_params.update({"ticker": "NVDA", "open": "1"})
    app.run(timeout=120)

    rails = [
        str(item.value)
        for item in app.markdown
        if "company-workbench-evidence-status" in str(item.value)
    ]
    assert not app.exception
    assert len(rails) == 1
    assert rails[0].count("Reviewable") == 5
    assert "Withheld" not in rails[0]
    assert "Unavailable" not in rails[0]


def test_company_workbench_single_stock_report_projects_an_unavailable_evidence_rail_when_report_build_fails():
    """Catches a missing payload leaving the existing Workbench evidence target blank."""

    app = AppTest.from_string(
        """
from types import SimpleNamespace
import streamlit as st
from src import dashboard

build_calls = []
def unavailable_report(*args, **kwargs):
    build_calls.append((args, kwargs))
    raise RuntimeError('controlled unavailable report')

dashboard.build_provider = lambda *args, **kwargs: SimpleNamespace()
dashboard.build_stock_report = unavailable_report
provider = SimpleNamespace(
    list_local_tickers=lambda: ['AVGO'],
    get_ticker_dataset_coverage=lambda ticker: [],
    get_peer_summary=lambda ticker: {
        'peer_dataset_present': False,
        'peer_count': 0,
        'candidate_peer_count': 0,
        'peer_fundamentals_available': 0,
        'peer_market_context_available': 0,
    },
)
evidence_target = st.empty()
dashboard.render_single_stock_report(
    provider,
    False,
    public_mode=True,
    selected_evidence_target=evidence_target,
)
st.caption(f'controlled builder calls: {len(build_calls)}')
""",
        default_timeout=120,
    )
    app.query_params.update({"ticker": "AVGO", "open": "1"})
    app.run(timeout=120)

    rails = [
        str(item.value)
        for item in app.markdown
        if "company-workbench-evidence-status" in str(item.value)
    ]
    assert not app.exception
    assert len(rails) == 1
    assert rails[0].count("Unavailable") == 6
    assert "controlled builder calls: 1" in [item.value for item in app.caption]


def _html_brief_app(*, mode: str = "research", ticker: str = "NVDA", open_report: bool = True) -> AppTest:
    app = AppTest.from_file(DASHBOARD_APP, default_timeout=120)
    query = {"mode": mode, "page": "company-workbench", "ticker": ticker}
    if open_report:
        query["open"] = "1"
    app.query_params.update(query)
    app.run(timeout=120)
    if mode == "research" and open_report:
        open_button = next(
            item
            for item in app.button
            if item.label == "Open evidence and analysis modules"
        )
        open_button.click().run(timeout=120)
    return app


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
    next(
        item
        for item in app.button
        if item.label == "Open evidence and analysis modules"
    ).click().run(timeout=120)

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
    html_downloads = [
        item
        for item in captured_downloads
        if item[0] == ("Download HTML Research Brief",)
    ]
    assert len(html_downloads) == 1
    expected = company_workbench_html_download_spec(captured_snapshots[0])
    args, kwargs = html_downloads[0]
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


def test_monitor_renders_one_follow_up_queue_without_competing_primary_summaries():
    from src.dashboard_render_smoke import DashboardRenderRoute, render_public_routes

    route = DashboardRenderRoute(
        name="Monitor Follow-up Queue",
        query_params=(("mode", "research"), ("page", "monitor")),
        required_markers=(
            "Follow-up Queue",
            "SINCE LAST REVIEW",
            "NEEDS VERIFICATION",
            "WAITING ON EVIDENCE",
            "SCHEDULED CONTEXT",
            "EVIDENCE FRESHNESS",
            "Advanced: Monitor evidence",
            "Research-only",
        ),
    )

    result = render_public_routes(Path("."), routes=(route,))[0]
    rendered = "\n".join(result.rendered_blocks)

    assert result.exceptions == ()
    assert rendered.index("Follow-up Queue") < rendered.index("SINCE LAST REVIEW")
    assert rendered.index("SINCE LAST REVIEW") < rendered.index("NEEDS VERIFICATION")
    assert rendered.index("NEEDS VERIFICATION") < rendered.index("WAITING ON EVIDENCE")
    assert rendered.index("WAITING ON EVIDENCE") < rendered.index("SCHEDULED CONTEXT")
    assert rendered.index("SCHEDULED CONTEXT") < rendered.index("EVIDENCE FRESHNESS")
    assert "Evidence Monitor Brief" not in rendered
    assert "Research Discipline Review" not in rendered
    assert "Research change monitor" not in rendered
    assert "company rank" not in rendered.lower()
    assert "expected return" not in rendered.lower()


def test_operator_personal_deep_link_renders_populated_operator_home():
    from src.dashboard_render_smoke import DashboardRenderRoute, render_public_routes

    route = DashboardRenderRoute(
        name="Operator rejects Discover deep link",
        query_params=(
            ("mode", "operator"),
            ("page", "discover"),
            ("ticker", "AVGO"),
            ("open", "1"),
        ),
        required_markers=(
            "Operator workspace",
            "Current local readiness for the next research review.",
            "Research Workflow",
            "What To Do Next",
            "Where To Go",
        ),
    )

    result = render_public_routes(Path("."), routes=(route,))[0]
    rendered = "\n".join(result.rendered_blocks)

    assert result.passed
    assert "<h1>Home</h1>" in rendered
    assert "<h1>Discover</h1>" not in rendered


def test_avgo_company_workbench_renders_one_authoritative_peer_task():
    from src.dashboard_render_smoke import _rendered_blocks

    app = _html_brief_app(ticker="AVGO")
    blocks = _rendered_blocks(app)
    rendered = "\n".join(blocks)
    primary_briefs = tuple(block for block in blocks if "aria-label='Company Brief'" in block)
    change_blocks = tuple(block for block in blocks if "EVIDENCE CHANGE" in block)

    assert not app.exception
    assert len(change_blocks) == 1
    assert "No unresolved source-backed change is queued for this company." in change_blocks[0]
    assert "no queued change" in change_blocks[0]
    assert "snapshot evidence only" not in change_blocks[0]
    assert len(primary_briefs) == 1
    assert primary_briefs[0].count("<strong>Add peer mappings</strong>") == 1
    assert rendered.count("FORWARD-VIEW LANE UNBLOCK") == 1
    assert "ONE NEXT TASK" not in rendered
    assert "NEXT RESEARCH TASK" not in rendered


def test_avgo_company_workbench_renders_one_selected_answer_with_ticker_handoff():
    from src.dashboard_render_smoke import _rendered_blocks

    app = _html_brief_app(ticker="AVGO")
    rendered = "\n".join(_rendered_blocks(app))

    assert not app.exception
    assert rendered.count("aria-label='Company Brief'") == 1
    assert "?mode=research&amp;page=data-health&amp;ticker=AVGO" in rendered


def test_avgo_company_workbench_renders_one_six_lane_decision_lab_after_selected_answer():
    from src.dashboard_render_smoke import _rendered_blocks

    app = _html_brief_app(ticker="AVGO")
    rendered = "\n".join(_rendered_blocks(app))

    assert not app.exception
    for marker in (
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
        "Next research task",
    ):
        assert marker in rendered
    assert not any(
        item.proto.expanded
        for item in app.expander
        if item.label.startswith("Advanced")
    )
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
        app = AppTest.from_file(DASHBOARD_APP, default_timeout=120)
        app.query_params.update(dict(route.query_params))
        app.run(timeout=120)
        next(
            item
            for item in app.button
            if item.label == "Open evidence and analysis modules"
        ).click().run(timeout=120)

    rendered = "\n".join(
        str(getattr(item, "value", ""))
        for collection in ("markdown", "caption", "header", "subheader")
        for item in getattr(app, collection)
    )
    assert not app.exception
    for marker in route.required_markers:
        assert marker in rendered
    assert not any(
        item.proto.expanded
        for item in app.expander
        if item.label.startswith("Advanced")
    )


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
        required_markers=(
            "Company Workbench",
            "Company Brief",
            "Open evidence and analysis modules",
            "Research-only",
        ),
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
