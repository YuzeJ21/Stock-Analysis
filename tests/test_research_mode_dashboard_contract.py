from src import dashboard
from src import dashboard_navigation as nav


def test_dashboard_defaults_local_use_to_research_desk_and_preserves_explicit_modes():
    assert dashboard.dashboard_mode_from_query("") == nav.RESEARCH_MODE
    assert dashboard.workspace_default_page(
        "Home",
        mode=nav.RESEARCH_MODE,
        has_explicit_page_query=False,
    ) == "Research Desk"
    assert dashboard.workspace_default_page(
        "Home",
        mode=nav.PUBLIC_DEMO_MODE,
        has_explicit_page_query=False,
    ) == "Home"
    assert dashboard.workspace_default_page(
        "Data Health",
        mode=nav.OPERATOR_DEMO_MODE,
        has_explicit_page_query=True,
    ) == "Data Health"


def test_dashboard_research_paths_map_to_existing_renderers_without_changing_public_flow():
    assert dashboard.dashboard_page_from_query("research-desk") == "Research Desk"
    assert dashboard.dashboard_page_from_query("discover") == "Discover"
    assert dashboard.dashboard_page_from_query("company-workbench") == "Company Workbench"
    assert dashboard.dashboard_page_from_query("monitor") == "Monitor"
    assert dashboard.workspace_path_options("Research Desk", nav.RESEARCH_MODE) == nav.RESEARCH_PATH_PAGE_TITLES
    assert dashboard.workspace_path_options("Data Health", nav.RESEARCH_MODE) == nav.RESEARCH_PATH_PAGE_TITLES + [
        "Data Health"
    ]
    assert dashboard.workspace_path_options("Home", nav.PUBLIC_DEMO_MODE) == nav.PUBLIC_PATH_PAGE_TITLES
    assert dashboard.workspace_content_page("Discover", nav.RESEARCH_MODE) == "Stock Selector"
    assert dashboard.workspace_content_page("Company Workbench", nav.RESEARCH_MODE) == "Single-Stock Report"
    assert dashboard.workspace_content_page("Research Desk", nav.RESEARCH_MODE) == "Research Desk"
    assert dashboard.workspace_content_page("Monitor", nav.RESEARCH_MODE) == "Monitor"


def test_research_pages_are_not_classified_as_operator_advanced_pages():
    assert all(page in dashboard.USER_PAGE_TITLES for page in nav.RESEARCH_PATH_PAGE_TITLES)
    assert all(page not in dashboard.ADVANCED_PAGE_TITLES for page in nav.RESEARCH_PATH_PAGE_TITLES)
    assert dashboard.workspace_path_label("Company Workbench", nav.RESEARCH_MODE) == "Company Workbench"


def test_research_selector_links_open_company_workbench_without_changing_public_default():
    import pandas as pd

    frame = pd.DataFrame(
        [
            {
                "Ticker": "NVDA",
                "Sector / Theme": "Semiconductors",
                "Supported Now": "Price trend and source-backed fundamentals",
                "Readiness": "partial",
            }
        ]
    )

    public_html = dashboard.stock_selector_result_table_html(frame, total_count=1)
    research_html = dashboard.stock_selector_result_table_html(
        frame,
        total_count=1,
        target_mode="research",
        target_page="company-workbench",
    )

    assert "?mode=public&amp;page=single-stock-report&amp;ticker=NVDA&amp;open=1" in public_html
    assert "?mode=research&amp;page=company-workbench&amp;ticker=NVDA&amp;open=1" in research_html


def test_research_header_keeps_data_health_inside_the_same_workspace():
    research_html = dashboard.command_center_header_html(
        {"master_universe": 10, "price_ready": 8, "dcf_ready": 2, "peer_ready": 1},
        tickers=10,
        final_count=0,
        latest_price="2026-07-16",
        compact=True,
        current_page="Research Desk",
        current_mode="research",
    )
    public_html = dashboard.command_center_header_html(
        {},
        tickers=0,
        final_count=0,
        latest_price="Unavailable",
        compact=True,
    )

    assert "?mode=research&page=data-health" in research_html
    assert "?mode=public&page=data-health" in public_html


def test_research_discover_can_limit_selector_rows_to_the_focused_cohort():
    import pandas as pd

    frame = pd.DataFrame(
        [
            {"Ticker": "AAA", "Readiness": "ready"},
            {"Ticker": "BBB", "Readiness": "partial"},
            {"Ticker": "OUT", "Readiness": "ready"},
        ]
    )

    filtered = dashboard.filter_selector_to_tickers(frame, ("BBB", "AAA", "MISSING"))

    assert filtered["Ticker"].tolist() == ["AAA", "BBB"]
    assert dashboard.filter_selector_to_tickers(frame, None).equals(frame)
    assert dashboard.filter_selector_to_tickers(frame, ()).empty


def test_research_workbench_data_health_handoff_stays_in_research_mode():
    import pandas as pd

    frame = pd.DataFrame(
        [
            {
                "Ticker": "NVDA",
                "Use Now": "Price and valuation evidence.",
                "Still Blocked": "Optional context.",
                "Context Only": "Candidate context only.",
                "Next Safe Action": "Open Data Health.",
                "Review Boundary": "Research-only.",
            }
        ]
    )

    rendered = dashboard.single_stock_public_summary_html(frame, target_mode="research")

    assert "?mode=research&amp;page=data-health&amp;ticker=NVDA" in rendered
