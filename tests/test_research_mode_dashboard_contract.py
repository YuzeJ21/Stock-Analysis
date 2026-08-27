from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

from src import dashboard
from src import dashboard_navigation as nav
from src import dashboard_visual_system as visual
from src import research_workspace
from src.catalyst_evidence_timeline import CatalystEvent, append_reviewed_event
from src.daily_research_queue import (
    DailyQueueEvidence,
    compare_daily_queues,
    evaluate_daily_queue,
)
from src.daily_research_queue_adapter import DailyQueueBuildStatus
from src.focused_research_cohort import FocusedCohort, FocusedCohortMember, build_focused_cohort
from src.research_decision_lab import ResearchDisciplineRow
from src.weekly_research_summary import WeeklyResearchSummary, WeeklySummaryItem


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


def test_dashboard_resolves_raw_route_before_loading_workspace_state():
    """Catches data/bootstrap work running before a disallowed route is canonicalized."""

    source = Path("src/dashboard.py").read_text(encoding="utf-8")
    main_start = source.index("def main()")
    route_resolution = source.index("resolve_workspace_route(", main_start)
    redirect_write = source.index("if route_resolution.redirected:", route_resolution)
    data_profile = source.index("data_profile = resolve_data_profile", main_start)
    bootstrap = source.index("render_public_route_bootstrap", main_start)

    assert route_resolution < redirect_write < data_profile < bootstrap


def test_personal_research_routes_do_not_render_ambiguous_freshness_label():
    source = Path("src/dashboard.py").read_text(encoding="utf-8")
    assert "<small>Freshness</small>" not in source
    assert "Saved readiness" in source
    assert "load_observation_recency" in source


def test_research_workflow_navigation_rendering_scopes_primary_and_secondary_routes(monkeypatch):
    rendered: list[str] = []
    monkeypatch.setattr(dashboard.st, "markdown", lambda html, **kwargs: rendered.append(html))

    for selected_page in nav.RESEARCH_PATH_PAGE_TITLES:
        dashboard.render_research_workflow_navigation(selected_page, ticker="AVGO")

    assert len(rendered) == len(nav.RESEARCH_PATH_PAGE_TITLES)
    assert all("Personal research workflow" in html for html in rendered)
    assert all(html.count("aria-current='page'") == 1 for html in rendered)

    rendered.clear()
    for selected_page in ("Data Health", "Proof History"):
        dashboard.render_research_workflow_navigation(selected_page, ticker="AVGO")

    assert len(rendered) == 2
    assert all("Personal research workflow" in html for html in rendered)
    assert all(html.count("aria-current='page'") == 1 for html in rendered)
    assert "Advanced Evidence · Data Health" in rendered[0]
    assert "Advanced Evidence · Proof History" in rendered[1]


def test_research_workflow_navigation_preserves_monitor_return_context_and_marks_evidence_location():
    """Catches a detour that drops the selected company or leaves evidence routes unlocated."""

    active = research_workspace.research_workflow_navigation_html(
        active_page="Monitor", ticker="BRK/B"
    )

    assert "page=monitor&amp;return_ticker=BRK%2FB" in active
    assert "page=company-workbench&amp;ticker=BRK%2FB&amp;open=1" in active
    assert active.count("aria-current='page'") == 1

    for page in ("Data Health", "Proof History"):
        evidence = research_workspace.research_workflow_navigation_html(
            active_page=page, ticker="AVGO"
        )
        assert f"Advanced Evidence · {page}" in evidence
        assert evidence.count("aria-current='page'") == 1


def test_research_workflow_navigation_keeps_canonical_routes_modes_and_tickerless_workbench_gate():
    """Catches document-layout work changing the single navigation's real route behavior."""

    active = research_workspace.research_workflow_navigation_html(
        active_page="Company Workbench",
        ticker="AVGO",
    )
    tickerless = research_workspace.research_workflow_navigation_html(
        active_page="Discover",
    )

    assert active.count("<nav class='research-workflow-navigation'") == 1
    assert active.count("aria-current='page'") == 1
    assert "Company Workbench</a>" in active
    for label, href in (
        ("Research Desk", "?mode=research&amp;page=research-desk"),
        ("Discover", "?mode=research&amp;page=discover"),
        (
            "Company Workbench",
            "?mode=research&amp;page=company-workbench&amp;ticker=AVGO&amp;open=1",
        ),
        ("Monitor", "?mode=research&amp;page=monitor&amp;return_ticker=AVGO"),
    ):
        assert label in active
        assert f"href='{href}'" in active
    assert "?mode=public" in active
    assert "?mode=operator" in active
    assert "aria-disabled='true'" in tickerless
    assert "Choose a company in Discover first" in tickerless
    assert "Company Workbench<span" in tickerless
    assert "page=company-workbench" not in tickerless


def test_public_and_research_use_route_state_without_sidebar_navigation_controls():
    source = Path("src/dashboard.py").read_text(encoding="utf-8")
    main_start = source.index("def main()")
    main = source[main_start:]
    operator_branch = main.index("if operator_mode:")
    public_research_branch = main.index(
        "    else:\n        selected_page = initial_page",
        operator_branch,
    )
    sidebar = main.index("with st.sidebar:", operator_branch)

    assert operator_branch < sidebar < public_research_branch
    assert "selected_page = initial_page" in main[public_research_branch:]
    assert "dashboard-workspace-mode" in main[operator_branch:public_research_branch]
    assert "Choose your path" in main[operator_branch:public_research_branch]


def test_research_main_shell_keeps_one_workflow_nav_without_operator_readiness_chrome():
    source = Path("src/dashboard.py").read_text(encoding="utf-8")
    main_start = source.index("def main()")
    output_frames = source.index(
        "output_frames = dashboard_output_frames_for_page(content_page)",
        main_start,
    )
    public_branch = source.index("if public_demo_mode:", output_frames)
    shared_else = source.index("    else:", public_branch)
    dispatch = source.index(
        "if selected_page in PUBLIC_PATH_PAGE_TITLES and operator_mode:",
        shared_else,
    )
    shell = source[shared_else:dispatch]
    research_branch = shell.index("if research_mode:")
    operator_else = shell.index("else:", research_branch)
    research_shell = shell[research_branch:operator_else]
    operator_shell = shell[operator_else:]

    assert "navigation_ticker = monitor_return_ticker if selected_page == \"Monitor\" else ticker" in research_shell
    assert "render_research_workflow_navigation(selected_page, ticker=navigation_ticker)" in research_shell
    assert "render_public_workflow_skip_target()" in research_shell
    assert "render_research_workspace_styles()" in research_shell
    assert "render_app_header(" not in research_shell
    assert "render_profile_trust_strip(" not in research_shell
    assert "render_app_header(" in operator_shell
    assert "render_profile_trust_strip(" in operator_shell


def test_public_shell_has_one_workflow_nav_and_url_only_workspace_mode_disclosure():
    rendered = dashboard.public_app_shell_html("Home")

    assert rendered.count("aria-label='Public workflow'") == 1
    assert rendered.count("aria-label='Workspace mode'") == 1
    assert "?mode=research&amp;page=research-desk" in rendered
    assert "?mode=operator" in rendered
    assert "dashboard-workspace-mode" not in rendered


def test_personal_research_route_loads_once_from_selected_profile_and_passes_one_result(
    monkeypatch,
):
    context = SimpleNamespace(data_dir=Path("/selected-profile/data"))
    recency = object()
    review_date = date(2026, 7, 27)
    load_calls: list[tuple[Path, str, date]] = []
    rendered: list[tuple[str, object]] = []
    daily_queue_calls: list[object] = []
    queue_status = SimpleNamespace(result=SimpleNamespace(eligible=()))

    def load_recency(path, *, selected_ticker, as_of):
        load_calls.append((path, selected_ticker, as_of))
        return recency

    monkeypatch.setattr(dashboard, "load_observation_recency", load_recency)
    monkeypatch.setattr(
        dashboard,
        "render_research_desk",
        lambda *args: rendered.append(("Research Desk", args[-1])),
    )
    monkeypatch.setattr(
        dashboard,
        "render_research_workspace_header",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        dashboard,
        "render_company_workbench",
        lambda *args: rendered.append(("Company Workbench", args[-1])),
    )
    monkeypatch.setattr(
        dashboard,
        "render_research_monitor",
        lambda *args: rendered.append(("Monitor", args[-1])),
    )
    monkeypatch.setattr(dashboard, "dashboard_output_frames_for_page", lambda page: {})
    monkeypatch.setattr(dashboard, "render_stock_selector", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        dashboard,
        "load_dashboard_daily_research_queue",
        lambda *args, **kwargs: queue_status,
        raising=False,
    )
    monkeypatch.setattr(
        dashboard,
        "render_daily_research_queue",
        lambda status, **kwargs: daily_queue_calls.append(status),
        raising=False,
    )
    monkeypatch.setattr(
        dashboard,
        "render_daily_research_queue_details",
        lambda *args, **kwargs: None,
        raising=False,
    )
    monkeypatch.setattr(
        dashboard,
        "observation_recency_summary_html",
        lambda value, **kwargs: rendered.append(("Discover", value)) or "",
    )
    monkeypatch.setattr(dashboard, "observation_recency_evidence_html", lambda value: "")
    monkeypatch.setattr(dashboard, "render_signal_cards", lambda *args, **kwargs: None)
    monkeypatch.setattr(dashboard, "focused_cohort_cards", lambda cohort: [])
    monkeypatch.setattr(dashboard, "focused_cohort_coverage_cards", lambda coverage: [])
    monkeypatch.setattr(dashboard.st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(dashboard.st, "caption", lambda *args, **kwargs: None)

    class Expander:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(dashboard.st, "expander", lambda *args, **kwargs: Expander())

    for selected_page in ("Research Desk", "Discover", "Company Workbench", "Monitor"):
        assert dashboard.render_personal_research_route(
            selected_page=selected_page,
            provider=object(),
            context=context,
            state={},
            cohort=SimpleNamespace(members=()),
            coverage=object(),
            weekly_summary=object(),
            ticker="AVGO",
            review_date=review_date,
        )
        assert load_calls == [(context.data_dir / "prices.csv", "AVGO", review_date)]
        assert rendered == [(selected_page, recency)]
        assert daily_queue_calls == []
        load_calls.clear()
        rendered.clear()
        daily_queue_calls.clear()


def test_dashboard_quarantines_legacy_deep_links_outside_operator_mode():
    for page in nav.LEGACY_RESEARCH_UTILITY_PAGES:
        assert dashboard.workspace_default_page(
            page,
            mode=nav.RESEARCH_MODE,
            has_explicit_page_query=True,
        ) == "Research Desk"
        assert dashboard.workspace_default_page(
            page,
            mode=nav.PUBLIC_DEMO_MODE,
            has_explicit_page_query=True,
        ) == "Home"
        assert dashboard.workspace_default_page(
            page,
            mode=nav.OPERATOR_DEMO_MODE,
            has_explicit_page_query=True,
        ) == page


def test_legacy_renderers_use_one_collapsed_compatibility_boundary():
    source = Path(dashboard.__file__).read_text(encoding="utf-8")
    shell_start = source.index("def render_legacy_research_utility_shell(")
    shell_end = source.index("\ndef render_monthly_picks(", shell_start)
    shell = source[shell_start:shell_end]
    monthly_start = source.index("def render_monthly_picks(")
    monthly_end = source.index("\ndef _render_monthly_picks_legacy_output(", monthly_start)
    monthly = source[monthly_start:monthly_end]
    output_start = source.index("def render_output_tab(")
    output_end = source.index("\ndef _render_legacy_output_tab(", output_start)
    output = source[output_start:output_end]

    assert "Legacy research utility — not part of Personal Research Mode" not in shell
    assert "render_context_note(" not in shell
    assert 'st.expander("Advanced: legacy compatibility output", expanded=False)' in monthly
    assert "_render_monthly_picks_legacy_output(catalog)" in monthly
    assert 'st.expander("Advanced: legacy compatibility output", expanded=False)' in output
    assert "_render_legacy_output_tab(title, output_frames, show_reason_details)" in output


def test_every_operator_allowed_title_has_one_escaped_route_shell_warning():
    operator_allowed_titles = (
        "Home",
        "Stock Selector",
        "Single-Stock Report",
        "Data Health",
        "Proof History",
        "Overview",
        "Monthly Picks",
        "Market Direction",
        "Momentum Leaders",
        "Portfolio Review",
        "Value / Re-rating",
        "Final Watchlist",
        "Universe Manager",
    )
    expected_operator_titles = tuple(
        dict.fromkeys((*nav.PUBLIC_PATH_PAGE_TITLES, *dashboard.ADVANCED_PAGE_TITLES))
    )
    assert operator_allowed_titles == expected_operator_titles
    assert set(operator_allowed_titles).isdisjoint(nav.RESEARCH_PATH_PAGE_TITLES)
    compatibility_titles = {
        "Monthly Picks",
        "Market Direction",
        "Momentum Leaders",
        "Portfolio Review",
        "Value / Re-rating",
        "Final Watchlist",
    }

    for title in operator_allowed_titles:
        rendered = dashboard.operator_route_shell_html(title)
        expected_kind = "compatibility" if title in compatibility_titles else "operator"

        assert rendered.count("<h1") == 1
        assert f"<h1>{title}</h1>" in rendered
        assert rendered.count("class='sr-operator-warning'") == 1
        assert f"data-sr-operator-kind='{expected_kind}'" in rendered
        assert "data-sr-region='stop-rule'" not in rendered
        assert "Stop rule" not in rendered

    escaped = dashboard.operator_route_shell_html('<Overview & "ops">')
    assert '<Overview & "ops">' not in escaped
    assert '&lt;Overview &amp; "ops"&gt;' in escaped


def test_operator_common_shell_precedes_all_route_detail_without_changing_sidebar_keys():
    source = Path(dashboard.__file__).read_text(encoding="utf-8")
    main = source[source.index("def main() -> None:") :]

    operator_branch = main.index("if operator_mode:")
    workspace_radio = main.index('key="dashboard-workspace-mode"', operator_branch)
    path_key = main.index('path_state_key = "dashboard-path-selection"', workspace_radio)
    path_widget = main.index('path_widget_key = f"{path_state_key}-{dashboard_page_slug(route_signature)}"', path_key)
    header = main.index("render_app_header(", path_widget)
    skip_target = main.index("render_public_workflow_skip_target()", header)
    route_shell = main.index("render_operator_route_shell(selected_page)", skip_target)
    first_route_summary = main.index("if selected_page in PUBLIC_PATH_PAGE_TITLES and operator_mode:", route_shell)
    dispatch = main.index("if research_mode and render_personal_research_route(", first_route_summary)

    assert operator_branch < workspace_radio < path_key < path_widget < header
    assert header < skip_target < route_shell < first_route_summary < dispatch
    assert main.count("render_operator_route_shell(selected_page)") == 1


def test_decision_lab_and_company_workbench_do_not_consume_legacy_utility_outputs():
    dashboard_source = Path(dashboard.__file__).read_text(encoding="utf-8")
    workbench_start = dashboard_source.index("def render_company_workbench(")
    workbench_end = dashboard_source.index("\ndef main()", workbench_start)
    workbench = dashboard_source[workbench_start:workbench_end]
    lab_source = (Path(dashboard.__file__).parent / "research_decision_lab.py").read_text(encoding="utf-8")

    forbidden = (
        "portfolio_review",
        "monthly_picks",
        "final_watchlist",
        "momentum_leaders",
        "undervalued_candidates",
    )
    for token in forbidden:
        assert token not in lab_source
        assert token not in workbench


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
    assert "Open NVDA review" in public_html
    assert "Open NVDA Company Brief" in research_html
    assert "High review priority" not in research_html


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


def test_research_discover_separates_strict_eligibility_from_saved_company_browsing(
    monkeypatch,
):
    calls: list[str] = []
    headings: list[str] = []
    context = SimpleNamespace(data_dir=Path("/selected-profile/data"))

    class Expander:
        def __enter__(self):
            calls.append("advanced")
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(dashboard, "load_observation_recency", lambda *args, **kwargs: object())
    monkeypatch.setattr(dashboard, "observation_recency_summary_html", lambda *args, **kwargs: "")
    monkeypatch.setattr(dashboard, "observation_recency_evidence_html", lambda *args, **kwargs: "")
    monkeypatch.setattr(dashboard, "render_research_workspace_header", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        dashboard,
        "load_dashboard_daily_research_queue",
        lambda *args, **kwargs: SimpleNamespace(result=SimpleNamespace(eligible=())),
        raising=False,
    )
    monkeypatch.setattr(
        dashboard,
        "render_daily_research_queue",
        lambda status, **kwargs: calls.append("strict eligibility"),
        raising=False,
    )
    monkeypatch.setattr(
        dashboard,
        "render_daily_research_queue_details",
        lambda *args, **kwargs: None,
        raising=False,
    )
    monkeypatch.setattr(
        dashboard,
        "render_stock_selector",
        lambda *args, **kwargs: calls.append("saved browsing"),
    )
    monkeypatch.setattr(
        dashboard,
        "dashboard_output_frames_for_page",
        lambda page: pytest.fail(
            "Research Discover must not load legacy selector outputs"
        ),
    )
    monkeypatch.setattr(dashboard, "render_signal_cards", lambda *args, **kwargs: None)
    monkeypatch.setattr(dashboard, "focused_cohort_cards", lambda cohort: [])
    monkeypatch.setattr(dashboard, "focused_cohort_coverage_cards", lambda coverage: [])
    monkeypatch.setattr(
        dashboard.st,
        "markdown",
        lambda value, **kwargs: headings.append(value),
    )
    monkeypatch.setattr(dashboard.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(dashboard.st, "expander", lambda *args, **kwargs: Expander())

    dashboard.render_personal_research_route(
        selected_page="Discover",
        provider=object(),
        context=context,
        state={},
        cohort=SimpleNamespace(members=()),
        coverage=object(),
        weekly_summary=object(),
        ticker="ALFA",
        review_date=date(2026, 7, 31),
    )

    assert all(value != "## Find a Company" for value in headings)
    assert all("Browse saved companies" not in value for value in headings)
    assert calls == ["saved browsing", "advanced"]


def test_discover_evidence_access_first_keeps_strict_queue_in_advanced_context(monkeypatch):
    events: list[tuple[str, object]] = []
    context = SimpleNamespace(data_dir=Path("/selected-profile/data"))
    tickers = ("NVDA", "AMD", "AVGO", "COHR", "TSLA", "XOM", "PLTR", "ZZZ")
    readiness = dashboard.pd.DataFrame(
        {"ticker": tickers, "asset_type": ["company"] * len(tickers)}
    )
    strict_status = DailyQueueBuildStatus(
        result=evaluate_daily_queue(()),
        considered_count=0,
        readiness_row_count=len(tickers),
        price_row_count=0,
        valuation_observation_count=0,
        blocker_counts=(),
        message="No strict-screen matches.",
    )

    class ContextManager:
        def __init__(self, label: str):
            self.label = label

        def __enter__(self):
            events.append(("expander", self.label))
            return self

        def __exit__(self, *args):
            return False

    selector_counts: list[int] = []
    original_selector = dashboard.render_stock_selector

    def render_selector(*args, **kwargs):
        selector_counts.append(kwargs["strict_eligible_count"])
        return original_selector(*args, **kwargs)

    monkeypatch.setattr(dashboard, "load_observation_recency", lambda *args, **kwargs: None)
    monkeypatch.setattr(dashboard, "render_research_workspace_header", lambda *args, **kwargs: None)
    monkeypatch.setattr(dashboard, "load_dashboard_daily_research_queue", lambda *args, **kwargs: strict_status)
    monkeypatch.setattr(dashboard, "load_ticker_readiness_report", lambda: (readiness, None))
    monkeypatch.setattr(dashboard, "load_dcf_readiness", lambda: (dashboard.pd.DataFrame(), None))
    monkeypatch.setattr(
        dashboard,
        "load_optional_context_readiness",
        lambda: {
            "earnings_readiness": (dashboard.pd.DataFrame(), None),
            "analyst_estimates_readiness": (dashboard.pd.DataFrame(), None),
        },
    )
    monkeypatch.setattr(dashboard, "load_output", lambda *args, **kwargs: (dashboard.pd.DataFrame(), None))
    monkeypatch.setattr(dashboard, "dashboard_readiness_summary", lambda *args, **kwargs: {})
    monkeypatch.setattr(
        dashboard,
        "stock_selector_saved_filter_presets",
        lambda: ({"label": "All", "state": "All", "readiness": "All", "detail": "All", "theme": "All", "search": ""},),
    )
    monkeypatch.setattr(dashboard, "render_stock_selector", render_selector)
    monkeypatch.setattr(dashboard, "focused_cohort_cards", lambda *args, **kwargs: [])
    monkeypatch.setattr(dashboard, "focused_cohort_coverage_cards", lambda *args, **kwargs: [])
    monkeypatch.setattr(dashboard, "render_signal_cards", lambda *args, **kwargs: None)
    monkeypatch.setattr(dashboard.st, "session_state", {})
    monkeypatch.setattr(
        dashboard.st,
        "markdown",
        lambda value, **kwargs: events.append(("markdown", value)),
    )
    monkeypatch.setattr(
        dashboard.st,
        "text_input",
        lambda label, **kwargs: events.append(("text_input", label)) or "",
    )
    monkeypatch.setattr(dashboard.st, "expander", lambda label, **kwargs: ContextManager(label))
    monkeypatch.setattr(dashboard.st, "form", lambda label, **kwargs: ContextManager(label))
    monkeypatch.setattr(dashboard.st, "columns", lambda widths: [dashboard.st] * len(widths))
    monkeypatch.setattr(dashboard.st, "selectbox", lambda label, options, **kwargs: options[0])
    monkeypatch.setattr(dashboard.st, "form_submit_button", lambda *args, **kwargs: False)
    monkeypatch.setattr(dashboard.st, "dataframe", lambda *args, **kwargs: None)
    monkeypatch.setattr(dashboard.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        dashboard,
        "render_notice_card",
        lambda title, body, *args, **kwargs: events.append(("notice", f"{title} {body}")),
    )

    dashboard.render_personal_research_route(
        selected_page="Discover",
        provider=object(),
        context=context,
        state={},
        cohort=SimpleNamespace(members=tuple(SimpleNamespace(ticker=ticker) for ticker in tickers)),
        coverage=object(),
        weekly_summary=object(),
        ticker="AMD",
        review_date=date(2026, 8, 26),
    )

    primary_index = next(
        index
        for index, event in enumerate(events)
        if event[0] == "markdown" and "8 saved companies are available" in event[1]
    )
    search_index = events.index(("text_input", "Search saved companies"))
    assert "0 currently pass the strict screen" in events[primary_index][1]
    assert primary_index < search_index
    assert all(
        ticker in " ".join(event[1] for event in events if event[0] == "markdown")
        for ticker in ("AMD", "AVGO", "COHR", "NVDA")
    )
    advanced_index = events.index(("expander", "Advanced: cohort readiness context"))
    strict_detail_index = next(
        index
        for index, event in enumerate(events)
        if event[0] == "notice" and "No company currently has complete evidence" in event[1]
    )
    assert advanced_index < strict_detail_index
    assert selector_counts == [0]


def test_discover_route_owns_one_boundary_and_places_recency_after_saved_browser(
    monkeypatch,
):
    calls: list[tuple[str, object]] = []
    recency = object()
    context = SimpleNamespace(data_dir=Path("/selected-profile/data"))

    class Expander:
        def __enter__(self):
            calls.append(("advanced-body", None))
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(dashboard, "load_observation_recency", lambda *args, **kwargs: recency)
    monkeypatch.setattr(
        dashboard,
        "render_research_workspace_header",
        lambda *args, **kwargs: calls.append(("header", kwargs)),
    )
    monkeypatch.setattr(
        dashboard,
        "load_dashboard_daily_research_queue",
        lambda *args, **kwargs: SimpleNamespace(result=SimpleNamespace(eligible=())),
    )
    monkeypatch.setattr(dashboard, "render_daily_research_queue", lambda *args, **kwargs: calls.append(("strict", kwargs)))
    monkeypatch.setattr(
        dashboard,
        "render_daily_research_queue_details",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(dashboard, "render_stock_selector", lambda *args, **kwargs: calls.append(("saved", kwargs)))
    monkeypatch.setattr(
        dashboard,
        "observation_recency_summary_html",
        lambda value, **kwargs: calls.append(("recency", value)) or "",
    )
    monkeypatch.setattr(dashboard, "observation_recency_evidence_html", lambda value: "")
    monkeypatch.setattr(dashboard, "render_signal_cards", lambda *args, **kwargs: None)
    monkeypatch.setattr(dashboard, "focused_cohort_cards", lambda cohort: [])
    monkeypatch.setattr(dashboard, "focused_cohort_coverage_cards", lambda coverage: [])
    monkeypatch.setattr(dashboard.st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(dashboard.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(dashboard.st, "expander", lambda *args, **kwargs: Expander())

    dashboard.render_personal_research_route(
        selected_page="Discover",
        provider=object(),
        context=context,
        state={},
        cohort=SimpleNamespace(members=()),
        coverage=object(),
        weekly_summary=object(),
        ticker="AVGO",
        review_date=date(2026, 8, 11),
    )

    header_kwargs = next(value for name, value in calls if name == "header")
    assert header_kwargs["include_boundary"] is False
    assert header_kwargs["compact"] is True
    assert header_kwargs.get("observation_recency") is None
    assert "strict" not in [name for name, _ in calls]
    assert [name for name, _ in calls].index("saved") < [name for name, _ in calls].index(
        "recency"
    )
    saved_kwargs = next(value for name, value in calls if name == "saved")
    assert saved_kwargs["research_boundary"] == dashboard.QUEUE_BOUNDARY


def test_daily_queue_renderer_is_ticker_bound_and_keeps_blockers_in_advanced(
    monkeypatch,
):
    rendered: list[str] = []
    links: list[tuple[str, str]] = []
    tables: list[object] = []

    class Expander:
        def __enter__(self):
            rendered.append("advanced opened")
            return self

        def __exit__(self, *args):
            return False

    evidence = DailyQueueEvidence(
        ticker="ALFA",
        company_name="Alpha Company",
        observation_through_date="2026-07-30",
        momentum_ready=True,
        current_market_eligible=True,
        price_provenance_eligible=True,
        price_rights_eligible=True,
        price_field_scope_eligible=True,
        close=120.0,
        sma_50=110.0,
        sma_200=100.0,
        return_3m=0.1,
        return_6m=0.2,
        relative_return_vs_spy=0.04,
        valuation_state="ready",
        valuation_freshness_state="current",
        valuation_commercial_eligible=True,
        valuation_metric="price_to_fcf_per_share",
        valuation_percentile=30.0,
        free_cash_flow=100.0,
        revenue_growth=0.05,
        debt_to_equity=0.5,
        fundamentals_provenance_eligible=True,
        fundamentals_rights_eligible=True,
        fundamentals_field_scope_eligible=True,
    )
    result = evaluate_daily_queue((evidence,))
    status = DailyQueueBuildStatus(
        result=result,
        considered_count=1,
        readiness_row_count=1,
        price_row_count=440,
        valuation_observation_count=8,
        blocker_counts=(),
        message="Evaluated one record.",
    )
    monkeypatch.setattr(
        dashboard,
        "render_signal_cards",
        lambda cards, **kwargs: rendered.extend(
            str(value) for card in cards for value in card.values()
        ),
    )
    monkeypatch.setattr(dashboard.st, "markdown", lambda value, **kwargs: rendered.append(value))
    monkeypatch.setattr(dashboard.st, "caption", lambda value, **kwargs: rendered.append(value))
    monkeypatch.setattr(dashboard.st, "dataframe", lambda frame, **kwargs: tables.append(frame))
    monkeypatch.setattr(dashboard.st, "expander", lambda *args, **kwargs: Expander())
    monkeypatch.setattr(
        dashboard.st,
        "link_button",
        lambda label, url, **kwargs: links.append((label, url)),
    )

    dashboard.render_daily_research_queue(status)

    combined = " ".join(rendered).lower()
    assert "screen eligibility — when supported" in combined
    assert "research-only" in combined
    assert links == [
        (
            "Open ALFA Company Brief",
            "?mode=research&page=company-workbench&ticker=ALFA",
        )
    ]
    assert len(tables) == 2
    assert tables[0]["Ticker"].tolist() == ["ALFA"]
    assert "advanced opened" in rendered
    for prohibited in ("buy", "sell", "target price", "expected return", "position size"):
        assert prohibited not in combined


def test_empty_strict_screen_preserves_saved_browsing_boundary(monkeypatch):
    rendered: list[str] = []

    class Expander:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    status = DailyQueueBuildStatus(
        result=evaluate_daily_queue(()),
        considered_count=0,
        readiness_row_count=0,
        price_row_count=0,
        valuation_observation_count=0,
        blocker_counts=(("current_market_evidence", 1),),
        message="No eligible records.",
    )
    monkeypatch.setattr(
        dashboard.st,
        "markdown",
        lambda value, **kwargs: rendered.append(value),
    )
    monkeypatch.setattr(
        dashboard.st,
        "caption",
        lambda value, **kwargs: rendered.append(value),
    )
    monkeypatch.setattr(dashboard, "render_signal_cards", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        dashboard,
        "render_notice_card",
        lambda title, body, *args, **kwargs: rendered.extend([title, body]),
    )
    monkeypatch.setattr(
        dashboard.st,
        "expander",
        lambda *args, **kwargs: Expander(),
    )
    monkeypatch.setattr(dashboard.st, "dataframe", lambda *args, **kwargs: None)

    dashboard.render_daily_research_queue(status)

    copy = " ".join(rendered)
    assert "Screen eligibility — when supported" in copy
    assert "No company currently has complete evidence for the strict screen" in copy
    assert "This does not prevent browsing saved companies" in copy
    assert "thresholds were not relaxed" in copy.lower()
    primary_answer = next(
        value for value in rendered if "data-sr-region='primary-answer'" in value
    )
    assert "Check saved-company browsing separately below" in primary_answer
    assert "strict eligibility is unchanged" in primary_answer
    assert "companies remain inspectable" not in primary_answer.lower()
    assert "id='saved-company-browser'" in dashboard.discover_browse_result_summary_html(
        2, 4
    )
    jump = dashboard.discover_saved_browser_jump_html()
    assert "href='#saved-company-browser'" in jump
    assert "Browse saved companies" in jump
    selector_source = Path(dashboard.__file__).read_text(encoding="utf-8")
    assert "discover_saved_browser_jump_html()" in selector_source


def test_company_workbench_anchors_answer_before_collapsed_navigation_and_passes_target_to_report():
    source = dashboard.Path(dashboard.__file__).read_text(encoding="utf-8")
    workbench_start = source.index("def render_company_workbench(")
    workbench_end = source.index("\ndef main()", workbench_start)
    workbench = source[workbench_start:workbench_end]

    header = workbench.index("render_research_workspace_header(")
    target = workbench.index("selected_answer_target = st.empty()", header)
    review = workbench.index('with st.expander("Review path", expanded=False):', target)
    advanced = workbench.index('with st.expander("Advanced: selected-company lane coverage", expanded=False):', review)
    report = workbench.index("render_single_stock_report(", advanced)

    assert header < target < review < advanced < report
    assert "compact=True" in workbench[header:target]
    assert "selected_answer_target=selected_answer_target" in workbench[report:]
    assert 'st.markdown("### Selected Company")' not in workbench


def test_company_workbench_loads_cash_preview_only_for_explicit_flag():
    source = dashboard.Path(dashboard.__file__).read_text(encoding="utf-8")
    workbench_start = source.index("def render_company_workbench(")
    workbench_end = source.index("\ndef main()", workbench_start)
    workbench = source[workbench_start:workbench_end]

    assert 'company_workbench_cash_preview_requested(st.query_params.get("cash_preview"))' in source
    assert "load_company_workbench_cash_generation_preview(ticker)" in source
    gate = workbench.index(
        'company_workbench_cash_preview_requested(st.query_params.get("cash_preview"))'
    )
    load = workbench.index(
        "load_company_workbench_cash_generation_preview(ticker)",
        gate,
    )
    report = workbench.index("render_single_stock_report(", load)
    canonical = workbench.index("load_dashboard_quarterly_trend(ticker)", report)

    assert gate < load < report < canonical
    assert workbench.index("cash_generation_preview = None") < gate
    assert "cash_generation_preview=cash_generation_preview" in workbench[report:]


def test_cash_preview_renders_after_business_trend_answer_and_before_advanced_lineage():
    source = dashboard.Path(dashboard.__file__).read_text(encoding="utf-8")
    report_start = source.index("def render_single_stock_report(")
    report_end = source.index("\ndef render_data_health(", report_start)
    report = source[report_start:report_end]

    business = report.index('st.markdown("## Business Trend")')
    canonical = report.index("quarterly_trend_cards(trend_packet)", business)
    preview = report.index(
        "cash_generation_preview_cards(cash_generation_preview)",
        canonical,
    )
    advanced = report.index(
        'st.expander("Advanced: cash-generation preview evidence", expanded=False)',
        preview,
    )
    rows = report.index("cash_generation_preview_rows(cash_generation_preview)", advanced)
    canonical_advanced = report.index(
        'st.expander("Advanced: quarterly trend evidence", expanded=False)',
        rows,
    )

    assert business < canonical < preview < advanced < rows < canonical_advanced


def test_default_research_navigation_never_enables_cash_preview():
    source = dashboard.Path(dashboard.__file__).read_text(encoding="utf-8")

    assert "cash_preview=1" not in source
    assert "ticker=NVDA&open=1&cash_preview=1" not in source
    assert "ticker=AMD&open=1&cash_preview=1" not in source


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


def test_dashboard_loads_saved_focused_cohort_coverage_without_refreshing(tmp_path, monkeypatch):
    import pandas as pd

    data_dir = tmp_path / "data"
    (data_dir / "reports").mkdir(parents=True)
    (data_dir / "earnings_nowcast").mkdir(parents=True)
    readiness = pd.DataFrame(
        [{"ticker": "AAA", "price_ready": True, "fundamentals_ready": True, "dcf_ready": True, "peer_ready": False}]
    )
    universe = pd.DataFrame(
        [{"ticker": "AAA", "name": "Alpha", "asset_type": "company", "is_active_listing": True}]
    )
    fundamentals = pd.DataFrame(
        [
            {
                "ticker": "AAA",
                "source": "sec_companyfacts",
                "source_ref": "sec:AAA:10-Q",
                "free_cash_flow": 10,
                "cash": 20,
                "debt": 5,
                "shares_outstanding": 100,
            }
        ]
    )
    prices = pd.DataFrame(
        [{"date": "2026-07-15", "ticker": "AAA", "close": 100, "adj_close": 100}]
    )
    readiness.to_csv(data_dir / "reports" / "ticker_readiness_report.csv", index=False)
    universe.to_csv(data_dir / "universe_master.csv", index=False)
    fundamentals.to_csv(data_dir / "fundamentals.csv", index=False)
    prices.to_csv(data_dir / "prices.csv", index=False)
    quarterly_rows = []
    for period, revenue, eps in (
        ("2024-Q1", 100.0, 1.0),
        ("2024-Q4", 130.0, 1.3),
        ("2025-Q1", 150.0, 1.5),
    ):
        quarterly_rows.append(
            {
                "ticker": "AAA",
                "fiscal_period": period,
                "period_end_date": f"{period[:4]}-{int(period[-1]) * 3:02d}-28",
                "reported_at": "2026-05-01T00:00:00Z",
                "revenue_actual": revenue,
                "eps_actual": eps,
                "source": "sec_companyfacts",
                "source_ref": f"sec:AAA:{period}",
                "retrieved_at": "2026-05-02T00:00:00Z",
                "revenue_currency": "USD",
                "revenue_unit_scale": 1.0,
                "revenue_basis": "gaap",
                "eps_currency": "USD",
                "eps_basis": "gaap",
                "eps_share_basis": "diluted",
                "eps_operations_basis": "continuing",
                "split_adjustment_basis": "as_reported",
            }
        )
    pd.DataFrame(quarterly_rows).to_csv(
        data_dir / "earnings_nowcast" / "quarterly_actuals.csv", index=False
    )
    cohort = build_focused_cohort(readiness, universe, target_size=1, minimum_size=1)
    monkeypatch.setattr(dashboard, "DATA_DIR", data_dir)
    real_read_csv = pd.read_csv
    price_read_nrows: list[object] = []

    def tracked_read_csv(path, *args, **kwargs):
        if dashboard.Path(path) == data_dir / "prices.csv":
            price_read_nrows.append(kwargs.get("nrows"))
        return real_read_csv(path, *args, **kwargs)

    monkeypatch.setattr(dashboard.pd, "read_csv", tracked_read_csv)

    coverage = dashboard.load_dashboard_focused_cohort_coverage(cohort)

    states = {row.lane: row.state for row in coverage.rows}
    assert states["adjusted_daily_price_history"] == "blocked"
    assert states["free_cash_flow"] == "blocked"
    assert states["shares_outstanding"] == "usable_now"
    assert states["trusted_peers"] == "blocked"
    assert states["quarterly_revenue"] == "usable_now"
    assert states["quarterly_eps"] == "blocked"
    fcf = next(row for row in coverage.rows if row.lane == "free_cash_flow")
    assert "registered field scope" in fcf.evidence
    assert "free_cash_flow" in fcf.evidence
    eps = next(row for row in coverage.rows if row.lane == "quarterly_eps")
    assert "eps" in eps.evidence
    price = next(row for row in coverage.rows if row.lane == "adjusted_daily_price_history")
    assert "provenance" in price.evidence.lower()
    assert price_read_nrows == [0]


def test_dashboard_blocks_partially_rejected_canonical_quarterly_ledger(tmp_path, monkeypatch):
    import pandas as pd

    data_dir = tmp_path / "data"
    (data_dir / "reports").mkdir(parents=True)
    (data_dir / "earnings_nowcast").mkdir(parents=True)
    readiness = pd.DataFrame(
        [
            {
                "ticker": "AAA",
                "price_ready": True,
                "fundamentals_ready": True,
                "dcf_ready": False,
                "peer_ready": False,
            }
        ]
    )
    universe = pd.DataFrame(
        [{"ticker": "AAA", "name": "Alpha", "asset_type": "company", "is_active_listing": True}]
    )
    readiness.to_csv(data_dir / "reports" / "ticker_readiness_report.csv", index=False)
    universe.to_csv(data_dir / "universe_master.csv", index=False)
    base = {
        "ticker": "AAA",
        "fiscal_period": "2025-Q1",
        "period_end_date": "2025-03-31",
        "reported_at": "2025-05-01T00:00:00Z",
        "revenue_actual": 100.0,
        "eps_actual": 1.0,
        "source": "sec_companyfacts",
        "source_ref": "sec:AAA:2025-Q1",
        "retrieved_at": "2025-05-02T00:00:00Z",
        "revenue_currency": "USD",
        "revenue_unit_scale": 1.0,
        "revenue_basis": "gaap",
        "eps_currency": "USD",
        "eps_basis": "gaap",
        "eps_share_basis": "diluted",
        "eps_operations_basis": "continuing",
        "split_adjustment_basis": "as_reported",
        "supersedes_source_ref": "",
    }
    pd.DataFrame(
        [base, {**base, "fiscal_period": "2025-FY", "source_ref": "sec:AAA:invalid"}]
    ).to_csv(data_dir / "earnings_nowcast" / "quarterly_actuals.csv", index=False)
    cohort = build_focused_cohort(readiness, universe, target_size=1, minimum_size=1)
    monkeypatch.setattr(dashboard, "DATA_DIR", data_dir)

    packet = dashboard.load_dashboard_quarterly_trend("AAA")
    coverage = dashboard.load_dashboard_focused_cohort_coverage(cohort)
    states = {row.lane: row.state for row in coverage.rows}

    assert packet.status == "blocked"
    assert packet.available_periods == ()
    assert packet.canonical_rejected_rows[0]["row_number"] == 3
    assert states["quarterly_revenue"] == "blocked"
    assert states["quarterly_eps"] == "blocked"


def test_research_desk_renders_one_brief_before_advanced_supporting_evidence():
    source = dashboard.Path(dashboard.__file__).read_text(encoding="utf-8")
    desk_start = source.index("def render_research_desk(")
    desk_end = source.index("def render_research_monitor(", desk_start)
    desk = source[desk_start:desk_end]

    brief = desk.index("brief = build_research_desk_brief(")
    brief_html = desk.index("research_desk_brief_html(", brief)
    advanced_region = desk.index("research_advanced_detail_marker_html()", brief_html)
    advanced = desk.index('with st.expander("Advanced Evidence", expanded=False):', advanced_region)
    weekly_cards = desk.index("weekly_summary_cards(weekly_summary)", advanced)
    cohort = desk.index("focused_cohort_cards(cohort)", weekly_cards)
    coverage = desk.index("focused_cohort_coverage_cards(coverage)", cohort)
    cohort_frame = desk.index("focused_cohort_frame(cohort)", coverage)
    coverage_frame = desk.index("focused_cohort_coverage_frame(coverage)", cohort_frame)
    change_detail = desk.index('render_research_change_route_summary("Research Desk", state)', coverage_frame)

    assert brief < brief_html < advanced_region < advanced < weekly_cards
    assert weekly_cards < cohort < coverage < cohort_frame < coverage_frame < change_detail
    assert "research_desk_cards(" not in desk
    assert "research_desk_cards_html(" not in desk
    assert 'st.link_button("Open Discover"' not in desk


def test_research_workspace_phone_styles_compact_profile_and_hide_only_duplicate_freshness():
    source = dashboard.Path(dashboard.__file__).read_text(encoding="utf-8")
    start = source.index("def render_research_workspace_styles()")
    end = source.index("\ndef render_research_workspace_header(", start)
    styles = source[start:end]

    assert ".profile-trust-strip.compact" in styles
    assert "grid-template-columns: repeat(3, minmax(0, 1fr));" in styles
    assert ".research-workspace-freshness { display: none; }" in styles
    assert ".research-workspace-action" in styles
    assert ".research-workspace-header.compact { padding: .35rem .9rem; margin-bottom: .15rem; }" in styles
    assert ".research-workspace-header.compact h1 { padding: 0; }" in styles
    assert ".research-workspace-header.compact .research-workspace-heading p" in styles
    assert "font-size: .9rem; line-height: 1.35;" in styles
    assert ".research-workspace-header.compact .research-workspace-boundary" in styles
    assert "font-size: .85rem; line-height: 1.35; margin-top: .25rem;" in styles
    assert ".public-ticker-summary.research" in styles
    assert "grid-template-columns: 8rem minmax(0, 1fr) minmax(0, 1fr) minmax(12rem, 0.8fr);" in styles
    assert ".public-ticker-summary.research .public-ticker-action" in styles
    assert "display: grid;" in styles
    assert "@media (max-width: 640px)" in styles


def test_research_workspace_styles_inject_media_preferences_after_normal_styles():
    rendered: list[tuple[str, dict[str, object]]] = []

    def capture(html: str, **kwargs: object) -> None:
        rendered.append((html, kwargs))

    original_markdown = dashboard.st.markdown
    dashboard.st.markdown = capture
    try:
        dashboard.render_research_workspace_styles()
    finally:
        dashboard.st.markdown = original_markdown

    assert len(rendered) == 2
    assert rendered[0][0].startswith("\n        <style>")
    assert rendered[1] == (
        visual.render_stylesheet(visual.legacy_research_accessibility_css()),
        {"unsafe_allow_html": True},
    )


def test_company_workbench_keeps_review_path_and_lane_coverage_after_anchored_answer():
    source = dashboard.Path(dashboard.__file__).read_text(encoding="utf-8")
    start = source.index("def render_company_workbench(")
    end = source.index("\ndef main()", start)
    workbench = source[start:end]

    selected_answer = workbench.index("selected_answer_target = st.empty()")
    review = workbench.index('with st.expander("Review path", expanded=False):', selected_answer)
    path = workbench.index('st.caption(" -> ".join(section_names[:-1]))', review)
    coverage = workbench.index('with st.expander("Advanced: selected-company lane coverage", expanded=False):', path)
    report = workbench.index("render_single_stock_report(", coverage)

    assert selected_answer < review < path < coverage < report
    assert 'st.caption("Review path: "' not in workbench


def test_company_workbench_uses_composed_forward_view_and_keeps_details_advanced():
    source = dashboard.Path(dashboard.__file__).read_text(encoding="utf-8")
    render_start = source.index("def render_single_stock_report(")
    render_end = source.index("\ndef render_data_health(", render_start)
    render = source[render_start:render_end]

    assert "build_forward_view(" in render
    assert "forward_view_cards(forward_view_packet)" in render
    assert 'st.expander("Advanced: Forward View evidence", expanded=False)' in render
    assert "forward_view_rows(forward_view_packet)" in render
    assert "load_dashboard_nowcast_packet(" in render
    assert "fiscal_period" in render


def test_dashboard_nowcast_loader_passes_exact_report_period_and_rejects_synthetic(monkeypatch):
    calls = []

    def fake_builder(root, **kwargs):
        calls.append((root, kwargs))
        return {"evidence_scope": "source_backed_preview_only", "fiscal_period": kwargs["fiscal_period"]}

    monkeypatch.setattr(dashboard, "build_nowcast_packet", fake_builder)
    report = {
        "generated_at": "2026-07-17T00:00:00Z",
        "earnings_summary": {"fiscal_period": "2026-Q3"},
    }

    packet = dashboard.load_dashboard_nowcast_packet(report, ticker="AAA")

    assert packet["fiscal_period"] == "2026-Q3"
    assert calls[0][1] == {
        "ticker": "AAA",
        "fiscal_period": "2026-Q3",
        "as_of_timestamp": "2026-07-17T00:00:00Z",
    }
    assert dashboard.load_dashboard_nowcast_packet({"earnings_summary": {}}, ticker="AAA") is None

    monkeypatch.setattr(
        dashboard,
        "build_nowcast_packet",
        lambda *args, **kwargs: {"evidence_scope": "synthetic_test_evidence_only"},
    )
    assert dashboard.load_dashboard_nowcast_packet(report, ticker="AAA") is None


def test_monitor_and_workbench_integrate_new_evidence_layers_without_new_routes():
    source = dashboard.Path(dashboard.__file__).read_text(encoding="utf-8")
    monitor_start = source.index("def render_research_monitor(")
    monitor_end = source.index("def render_company_workbench(", monitor_start)
    monitor = source[monitor_start:monitor_end]
    report_start = source.index("def render_single_stock_report(")
    report_end = source.index("\ndef render_data_health(", report_start)
    report = source[report_start:report_end]

    assert "cohort_readiness_cards(nowcast_cohort)" in monitor
    assert 'st.expander("Advanced: five-company Earnings Nowcast readiness", expanded=False)' in monitor
    assert "valuation_regime_cards(valuation_regime)" in report
    assert "catalyst_timeline_cards(catalyst_timeline)" in report
    assert "outcome_status_cards(outcome_status)" in report
    assert dashboard.workspace_path_options("Research Desk", nav.RESEARCH_MODE) == nav.RESEARCH_PATH_PAGE_TITLES


def test_monitor_renders_one_follow_up_queue_and_one_empty_return_action(monkeypatch):
    rendered: list[str] = []
    actions: list[tuple[str, str]] = []
    cards: list[tuple[list[dict[str, object]], str]] = []
    expanders: list[str] = []

    class Expander:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(dashboard, "render_research_workspace_header", lambda *args, **kwargs: None)
    monkeypatch.setattr(dashboard, "load_dashboard_research_discipline_rows", lambda *args, **kwargs: ())
    monkeypatch.setattr(dashboard, "load_dashboard_nowcast_cohort", lambda: ())
    monkeypatch.setattr(dashboard, "cohort_readiness_cards", lambda rows: [])
    monkeypatch.setattr(dashboard, "render_research_change_route_summary", lambda *args, **kwargs: None)
    monkeypatch.setattr(dashboard, "observation_recency_summary_html", lambda *args, **kwargs: "")
    monkeypatch.setattr(dashboard, "observation_recency_evidence_html", lambda *args, **kwargs: "")
    monkeypatch.setattr(
        dashboard,
        "render_signal_cards",
        lambda values, **kwargs: cards.append((values, str(kwargs.get("variant") or ""))),
    )
    monkeypatch.setattr(dashboard.st, "markdown", lambda value, **kwargs: rendered.append(value))
    monkeypatch.setattr(dashboard.st, "caption", lambda value, **kwargs: rendered.append(value))
    monkeypatch.setattr(dashboard.st, "dataframe", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        dashboard.st,
        "link_button",
        lambda label, url, **kwargs: actions.append((label, url)),
    )
    monkeypatch.setattr(
        dashboard.st,
        "expander",
        lambda label, **kwargs: expanders.append(label) or Expander(),
    )

    dashboard.render_research_monitor(
        {"queue": ()},
        SimpleNamespace(
            freshness_state="current",
            freshness_message="Saved readiness is current.",
        ),
        WeeklyResearchSummary(
            status="no_changes",
            as_of="2026-08-04T00:00:00+00:00",
            cohort_size=0,
            unique_event_count=0,
            items=(),
            message="No traceable cohort evidence change requires review this week.",
        ),
        object(),
        SimpleNamespace(
            profile_price_lane=SimpleNamespace(
                state="current",
                message="Market observation is current.",
            )
        ),
    )

    headings = [value for value in rendered if value.startswith("## ")]
    assert headings == ["## Follow-up Queue"]
    assert all(variant != "evidence-monitor" for _, variant in cards)
    assert actions == []
    copy = " ".join(rendered)
    assert "No saved verification, evidence-wait, scheduled, or source-change item is currently due." in copy
    assert "Open Discover" in copy
    assert "saved follow-up item(s)" not in copy
    assert "does not prove that no external event" in copy
    assert "Evidence Monitor Brief" not in copy
    assert "Research Discipline Review" not in copy
    assert "Research change monitor" not in copy
    assert "Advanced: Monitor evidence" in expanders
    assert copy.count("data-sr-region='primary-answer'") == 1
    assert copy.count("data-sr-region='primary-action'") == 1
    assert copy.count("data-sr-region='stop-rule'") == 1


def test_monitor_return_context_renders_once_without_changing_monitor_scope(monkeypatch):
    """Catches return context being treated as a Monitor filter rather than a detour action."""

    class Expander:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    rendered: list[str] = []
    actions: list[tuple[str, str]] = []
    cards: list[tuple[object, str]] = []
    frames: list[list[dict[str, object]]] = []
    monkeypatch.setattr(dashboard, "render_research_workspace_header", lambda *args, **kwargs: None)
    monkeypatch.setattr(dashboard, "load_dashboard_research_discipline_rows", lambda *args, **kwargs: ())
    monkeypatch.setattr(dashboard, "load_dashboard_nowcast_cohort", lambda: ())
    monkeypatch.setattr(dashboard, "cohort_readiness_cards", lambda rows: [])
    monkeypatch.setattr(dashboard, "render_signal_cards", lambda values, **kwargs: cards.append((values, str(kwargs.get("variant") or ""))))
    monkeypatch.setattr(dashboard.st, "markdown", lambda value, **kwargs: rendered.append(value))
    monkeypatch.setattr(dashboard.st, "caption", lambda value, **kwargs: rendered.append(value))
    monkeypatch.setattr(dashboard.st, "link_button", lambda label, url, **kwargs: actions.append((label, url)))
    monkeypatch.setattr(dashboard.st, "dataframe", lambda frame, **kwargs: frames.append(frame.to_dict("records")))
    monkeypatch.setattr(dashboard.st, "expander", lambda *args, **kwargs: Expander())

    args = (
        {"queue": ()},
        SimpleNamespace(freshness_state="current", freshness_message="Saved readiness is current."),
        WeeklyResearchSummary(
            status="no_changes",
            as_of="2026-08-04T00:00:00+00:00",
            cohort_size=0,
            unique_event_count=0,
            items=(),
            message="No traceable cohort evidence change requires review this week.",
        ),
        object(),
    )

    dashboard.render_research_monitor(*args)
    without_context = (list(rendered), list(cards), list(frames), list(actions))
    rendered.clear()
    cards.clear()
    frames.clear()
    actions.clear()

    dashboard.render_research_monitor(*args, return_ticker="NVDA")
    with_context = (list(rendered), list(cards), list(frames), list(actions))

    assert with_context[1:3] == without_context[1:3]
    assert with_context[3] == [("Return to NVDA Company Workbench", "?mode=research&page=company-workbench&ticker=NVDA&open=1")]
    context_copy = " ".join(with_context[0])
    assert context_copy.count("Monitor remains focused-cohort-wide; NVDA is only the return destination and does not filter these follow-up items.") == 1
    assert [value for value in with_context[0] if "return destination" not in value] == without_context[0]


def test_monitor_freshness_only_attention_is_nonnumeric_and_routes_to_data_health(
    monkeypatch,
):
    rendered: list[str] = []
    cards: list[object] = []

    class Expander:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(dashboard, "render_research_workspace_header", lambda *args, **kwargs: None)
    monkeypatch.setattr(dashboard, "load_dashboard_research_discipline_rows", lambda *args, **kwargs: ())
    monkeypatch.setattr(dashboard, "load_dashboard_nowcast_cohort", lambda: ())
    monkeypatch.setattr(dashboard, "cohort_readiness_cards", lambda rows: [])
    monkeypatch.setattr(dashboard, "render_research_change_route_summary", lambda *args, **kwargs: None)
    monkeypatch.setattr(dashboard, "observation_recency_summary_html", lambda *args, **kwargs: "")
    monkeypatch.setattr(dashboard, "observation_recency_evidence_html", lambda *args, **kwargs: "")
    monkeypatch.setattr(
        dashboard,
        "render_signal_cards",
        lambda values, **kwargs: cards.extend(values),
    )
    monkeypatch.setattr(dashboard.st, "markdown", lambda value, **kwargs: rendered.append(value))
    monkeypatch.setattr(dashboard.st, "caption", lambda value, **kwargs: rendered.append(value))
    monkeypatch.setattr(dashboard.st, "dataframe", lambda *args, **kwargs: None)
    monkeypatch.setattr(dashboard.st, "expander", lambda *args, **kwargs: Expander())

    dashboard.render_research_monitor(
        {"queue": ()},
        SimpleNamespace(
            freshness_state="current",
            freshness_message="Saved readiness is current for saved sources.",
        ),
        WeeklyResearchSummary(
            status="no_changes",
            as_of="2026-08-04T00:00:00+00:00",
            cohort_size=0,
            unique_event_count=0,
            items=(),
            message="No traceable cohort evidence change requires review this week.",
        ),
        object(),
        SimpleNamespace(
            profile_price_lane=SimpleNamespace(
                state="stale",
                message="Saved market observation ends before the review date.",
            )
        ),
    )

    copy = " ".join(rendered)
    assert (
        "No saved research item is due. A separate market-observation freshness condition needs Data Health review."
        in copy
    )
    assert "Saved follow-up evidence needs attention." not in copy
    assert "Saved follow-up evidence" not in copy
    assert "Market-observation freshness condition" in copy
    assert "saved-source freshness condition" not in copy.lower()
    assert "1 saved follow-up item" not in copy
    assert "Open Data Health" in copy
    assert len(cards) == 5
    assert {str(card.get("key") or "") for card in cards} == {
        "since_last_review",
        "needs_verification",
        "waiting_on_evidence",
        "scheduled_context",
        "evidence_freshness",
    }


def test_direct_tickerless_company_workbench_fails_closed_without_report_or_default_ticker(
    monkeypatch,
):
    rendered: list[str] = []
    monkeypatch.setattr(
        dashboard,
        "st",
        SimpleNamespace(
            query_params={},
            markdown=lambda value, **kwargs: rendered.append(value),
        ),
    )
    monkeypatch.setattr(dashboard, "render_research_workspace_header", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        dashboard,
        "render_single_stock_report",
        lambda *args, **kwargs: pytest.fail("tickerless Workbench must not render a saved report"),
    )
    monkeypatch.setattr(
        dashboard,
        "load_company_workbench_cash_generation_preview",
        lambda ticker: pytest.fail(f"tickerless Workbench must not load preview for {ticker!r}"),
    )

    dashboard.render_company_workbench(
        object(),
        SimpleNamespace(),
        {},
        object(),
    )

    copy = " ".join(rendered)
    assert "Choose a company in Discover first" in copy
    assert "?mode=research&amp;page=discover" in copy
    assert copy.count("data-sr-region='primary-answer'") == 1
    assert copy.count("data-sr-region='primary-action'") == 1
    assert copy.count("data-sr-region='stop-rule'") == 1


def test_direct_unregistered_company_workbench_fails_closed_without_saved_ticker_fallback(
    monkeypatch,
):
    rendered: list[str] = []
    monkeypatch.setattr(
        dashboard,
        "st",
        SimpleNamespace(
            query_params={"ticker": "NOTREAL"},
            markdown=lambda value, **kwargs: rendered.append(value),
        ),
    )
    monkeypatch.setattr(dashboard, "render_research_workspace_header", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        dashboard,
        "render_single_stock_report",
        lambda *args, **kwargs: pytest.fail("unregistered Workbench ticker must not render"),
    )

    dashboard.render_company_workbench(
        SimpleNamespace(list_local_tickers=lambda: ["AVGO"]),
        SimpleNamespace(),
        {},
        object(),
    )

    copy = " ".join(rendered)
    assert "No registered saved company matches NOTREAL" in copy
    assert copy.count("data-sr-region='primary-answer'") == 1
    assert copy.count("data-sr-region='primary-action'") == 1
    assert copy.count("data-sr-region='stop-rule'") == 1


def test_direct_registered_company_workbench_without_open_preserves_query_and_renders_report(
    monkeypatch,
):
    reports: list[dict[str, object]] = []
    query = {"ticker": "AVGO", "cash_preview": "0"}

    class Expander:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    target = SimpleNamespace(markdown=lambda *args, **kwargs: None)
    monkeypatch.setattr(
        dashboard,
        "st",
        SimpleNamespace(
            query_params=query,
            markdown=lambda *args, **kwargs: None,
            empty=lambda: target,
            container=lambda *args, **kwargs: Expander(),
            columns=lambda *args, **kwargs: (Expander(), Expander()),
            expander=lambda *args, **kwargs: Expander(),
            caption=lambda *args, **kwargs: None,
        ),
    )
    monkeypatch.setattr(dashboard, "render_research_workspace_header", lambda *args, **kwargs: None)
    monkeypatch.setattr(dashboard, "render_signal_cards", lambda *args, **kwargs: None)
    monkeypatch.setattr(dashboard, "focused_ticker_coverage_cards", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        dashboard,
        "load_company_workbench_cash_generation_preview",
        lambda ticker: pytest.fail("cash_preview=0 must not load the preview"),
    )
    monkeypatch.setattr(dashboard, "load_dashboard_quarterly_trend", lambda ticker: None)
    monkeypatch.setattr(dashboard, "render_research_change_route_summary", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        dashboard,
        "render_single_stock_report",
        lambda *args, **kwargs: reports.append(kwargs),
    )

    dashboard.render_company_workbench(
        SimpleNamespace(list_local_tickers=lambda: ["AVGO"]),
        SimpleNamespace(),
        {},
        object(),
    )

    assert query == {"ticker": "AVGO", "cash_preview": "0"}
    assert len(reports) == 1
    assert reports[0]["research_mode"] is True
    assert reports[0]["selected_answer_target"] is target
    assert reports[0]["selected_detail_target"] is target
    assert reports[0]["selected_evidence_target"] is target


def test_registered_company_workbench_renders_one_document_overview_with_evidence_placeholder(
    monkeypatch,
):
    """Catches a Workbench overview rendered outside its document grid or without its evidence rail."""

    calls: list[tuple[str, object, object]] = []
    contexts: list[str] = []

    class RecordedContext:
        def __init__(self, name: str):
            self.name = name

        def __enter__(self):
            contexts.append(self.name)
            return self

        def __exit__(self, *args):
            contexts.pop()
            return False

    class RecordingStreamlit:
        query_params = {"ticker": "AVGO", "cash_preview": "0"}

        def container(self, *args, **kwargs):
            calls.append(("container", kwargs.get("key"), contexts[-1] if contexts else None))
            return RecordedContext("document")

        def columns(self, spec):
            calls.append(("columns", spec, contexts[-1] if contexts else None))
            return (RecordedContext("overview"), RecordedContext("evidence"))

        def empty(self):
            calls.append(("empty", None, contexts[-1] if contexts else None))
            return SimpleNamespace()

        def markdown(self, value, **kwargs):
            calls.append(("markdown", value, contexts[-1] if contexts else None))

        def expander(self, label, **kwargs):
            calls.append(("expander", label, contexts[-1] if contexts else None))
            return RecordedContext(f"expander:{label}")

        def caption(self, value, **kwargs):
            calls.append(("caption", value, contexts[-1] if contexts else None))

    monkeypatch.setattr(dashboard, "st", RecordingStreamlit())
    monkeypatch.setattr(dashboard, "render_research_workspace_header", lambda *args, **kwargs: None)
    monkeypatch.setattr(dashboard, "render_signal_cards", lambda *args, **kwargs: None)
    monkeypatch.setattr(dashboard, "focused_ticker_coverage_cards", lambda *args, **kwargs: [])
    monkeypatch.setattr(dashboard, "load_dashboard_quarterly_trend", lambda ticker: None)
    monkeypatch.setattr(dashboard, "render_research_change_route_summary", lambda *args, **kwargs: None)
    monkeypatch.setattr(dashboard, "render_single_stock_report", lambda *args, **kwargs: None)

    dashboard.render_company_workbench(
        SimpleNamespace(list_local_tickers=lambda: ["AVGO"]),
        SimpleNamespace(),
        {},
        object(),
    )

    assert [call for call in calls if call[0] == "container"] == [
        ("container", "company-workbench-document", None)
    ]
    assert [call for call in calls if call[0] == "columns"] == [
        ("columns", [3, 1], "document")
    ]
    assert [call for call in calls if call == ("empty", None, "evidence")] == [
        ("empty", None, "evidence")
    ]
    assert ("empty", None, "overview") in calls
    assert any(
        call[0] == "markdown" and "sr-evidence-timeline" in str(call[1]) and call[2] == "overview"
        for call in calls
    )
    assert ("expander", "Review path", "overview") in calls
    assert ("expander", "Advanced: selected-company lane coverage", "overview") in calls


def test_research_workbench_report_is_internally_open_without_changing_public_open_semantics():
    source = Path(dashboard.__file__).read_text(encoding="utf-8")
    start = source.index("def render_single_stock_report(")
    end = source.index("\ndef render_data_health(", start)
    report = source[start:end]

    public_query = 'query_open_review = single_stock_query_open(st.query_params.get("open"))'
    assert public_query in report
    assert report.index(public_query) < report.index("if research_mode:") < report.index(
        "compact_public_open_report ="
    )


def test_dashboard_keeps_authoring_call_scoped_to_the_selected_profile_and_ticker():
    import ast

    tree = ast.parse(Path(dashboard.__file__).read_text(encoding="utf-8"))
    report = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "render_single_stock_report"
    )
    calls = [
        node
        for node in ast.walk(report)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "render_research_record_authoring"
    ]

    assert len(calls) == 1
    keywords = {keyword.arg: ast.unparse(keyword.value) for keyword in calls[0].keywords}
    assert keywords == {
        "st_api": "st",
        "profile_key": "selected_context.profile_key",
        "ticker": "ticker",
        "paths": (
            "AuthoringPaths(journal=DATA_DIR / 'research_thesis_journal.csv', "
            "catalysts=DATA_DIR / 'catalyst_evidence.csv', "
            "outcomes=DATA_DIR / 'research_outcome_reviews.csv')"
        ),
    }


def test_monitor_actionable_state_renders_five_panels_without_duplicate_return_action(
    monkeypatch,
):
    cards: list[tuple[list[dict[str, object]], str]] = []
    actions: list[tuple[str, str]] = []
    headers: list[dict[str, object]] = []
    rendered: list[str] = []
    row = ResearchDisciplineRow(
        cohort_order=0,
        ticker="AAA",
        status="ready",
        due_lanes=("Evidence",),
        next_process_step="Verify conflicting evidence.",
        identity="identity-aaa",
        attention_state="conflicting_evidence",
        attention_label="Needs review",
        attention_reason="Conflicting saved evidence needs review.",
        attention_source="evidence",
    )

    class Expander:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(
        dashboard,
        "render_research_workspace_header",
        lambda *args, **kwargs: headers.append(kwargs),
    )
    monkeypatch.setattr(dashboard, "load_dashboard_research_discipline_rows", lambda *args, **kwargs: (row,))
    monkeypatch.setattr(dashboard, "load_dashboard_nowcast_cohort", lambda: ())
    monkeypatch.setattr(dashboard, "cohort_readiness_cards", lambda rows: [])
    monkeypatch.setattr(dashboard, "render_research_change_route_summary", lambda *args, **kwargs: None)
    monkeypatch.setattr(dashboard, "observation_recency_summary_html", lambda *args, **kwargs: "")
    monkeypatch.setattr(dashboard, "observation_recency_evidence_html", lambda *args, **kwargs: "")
    monkeypatch.setattr(
        dashboard,
        "research_monitor_frame",
        lambda *args, **kwargs: __import__("pandas").DataFrame(
            ({"Change": "one"}, {"Change": "two"})
        ),
    )
    monkeypatch.setattr(
        dashboard,
        "render_signal_cards",
        lambda values, **kwargs: cards.append((values, str(kwargs.get("variant") or ""))),
    )
    monkeypatch.setattr(dashboard.st, "markdown", lambda value, **kwargs: rendered.append(value))
    monkeypatch.setattr(dashboard.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(dashboard.st, "dataframe", lambda *args, **kwargs: None)
    monkeypatch.setattr(dashboard.st, "link_button", lambda label, url, **kwargs: actions.append((label, url)))
    monkeypatch.setattr(dashboard.st, "expander", lambda *args, **kwargs: Expander())

    dashboard.render_research_monitor(
        {"queue": ()},
        SimpleNamespace(
            freshness_state="current",
            freshness_message="Saved readiness is current.",
        ),
        WeeklyResearchSummary(
            status="review_required",
            as_of="2026-08-04T00:00:00+00:00",
            cohort_size=1,
            unique_event_count=1,
            items=(
                WeeklySummaryItem(
                    "new_evidence",
                    "AAA",
                    "AAA has reviewed source evidence.",
                    "review_now",
                    "source:aaa",
                    "2026-08-04T00:00:00+00:00",
                ),
            ),
            message="One traceable cohort evidence change requires review this week.",
        ),
        object(),
        SimpleNamespace(
            profile_price_lane=SimpleNamespace(
                state="current",
                message="Market observation is current.",
            )
        ),
    )

    primary_cards = next(values for values, variant in cards if variant == "evidence-monitor")
    assert [card["key"] for card in primary_cards] == [
        "since_last_review",
        "needs_verification",
        "waiting_on_evidence",
        "scheduled_context",
        "evidence_freshness",
    ]
    assert actions == []
    copy = " ".join(rendered)
    assert "Saved follow-up evidence needs attention." in copy
    assert "4 saved follow-up" not in copy
    assert "saved follow-up item(s)" not in copy
    assert headers == [
        {
            "primary_action": (
                "Review unresolved evidence changes; otherwise wait for new source evidence"
            ),
            "compact": True,
            "include_boundary": False,
        }
    ]


def test_discover_supporting_region_is_owned_by_selector_after_action_and_stop():
    source = Path(dashboard.__file__).read_text(encoding="utf-8")
    selector_start = source.index("def render_stock_selector(")
    selector_end = source.index("\ndef price_refresh_operator_plan_cards", selector_start)
    selector = source[selector_start:selector_end]
    route_start = source.index("def render_personal_research_route(")
    route_end = source.index("\ndef main()", route_start)
    route = source[route_start:route_end]

    search = selector.index("search = st.text_input(")
    stop = selector.index("stop_rule_html(", search)
    supporting = selector.index('title="Browse saved companies"', stop)
    filters = selector.index("open_change_counts:", supporting)

    assert search < stop < supporting < filters
    assert 'title="Browse saved companies"' not in route


def test_discover_search_omits_redundant_help_focus_stop_while_public_keeps_help():
    source = Path(dashboard.__file__).read_text(encoding="utf-8")
    selector_start = source.index("def render_stock_selector(")
    selector_end = source.index("\ndef price_refresh_operator_plan_cards", selector_start)
    selector = source[selector_start:selector_end]
    search_start = selector.index("search = st.text_input(")
    search_end = selector.index(").strip()", search_start)
    search_call = selector[search_start:search_end]

    assert '"Search saved companies" if research_discover else "Search this review queue"' in search_call
    assert 'value=str(current_filter_values.get("search") or "")' in search_call
    assert 'placeholder="Search ticker, theme, blocker, or proof step"' in search_call
    assert 'key="stock-selector-search"' in search_call
    assert "None\n            if research_discover" in search_call
    assert "Search readiness-backed rows before opening one saved report." in search_call
    assert "Search alphabetical saved-company evidence paths." not in search_call
    assert "stock_selector_current_filter_values(saved_presets, st.session_state)" in selector
    assert "Search and filters apply only to the readiness-backed saved-company set." in selector
    assert "They do not change strict screen eligibility or create a ranking." in selector


def test_stock_selector_search_widget_behavior_removes_only_discover_help(monkeypatch):
    class SearchCaptured(RuntimeError):
        pass

    nonempty = dashboard.pd.DataFrame({"Ticker": ["NVDA"]})
    captured: list[tuple[tuple[object, ...], dict[str, object]]] = []

    monkeypatch.setattr(dashboard, "load_ticker_readiness_report", lambda: (nonempty, None))
    monkeypatch.setattr(dashboard, "load_dcf_readiness", lambda: (nonempty, None))
    monkeypatch.setattr(
        dashboard,
        "load_optional_context_readiness",
        lambda: {
            "earnings_readiness": (nonempty, None),
            "analyst_estimates_readiness": (nonempty, None),
        },
    )
    monkeypatch.setattr(
        dashboard,
        "stock_selector_source_frames",
        lambda *args, **kwargs: (nonempty, None, nonempty, None),
    )
    monkeypatch.setattr(dashboard, "load_output", lambda *args, **kwargs: (nonempty, None))
    monkeypatch.setattr(dashboard, "dashboard_readiness_summary", lambda *args, **kwargs: {})
    monkeypatch.setattr(
        dashboard,
        "discover_saved_company_browse_frame",
        lambda *args, **kwargs: nonempty,
    )
    monkeypatch.setattr(dashboard, "stock_selector_queue_frame", lambda *args, **kwargs: nonempty)
    monkeypatch.setattr(dashboard, "filter_selector_to_tickers", lambda frame, tickers: frame)
    monkeypatch.setattr(
        dashboard,
        "stock_selector_saved_queue_notice_visible",
        lambda **kwargs: False,
    )
    monkeypatch.setattr(dashboard.st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        dashboard,
        "stock_selector_saved_filter_presets",
        lambda: [{"label": "All"}],
    )

    def current_values(presets, session_state):
        assert presets == [{"label": "All"}]
        assert session_state is dashboard.st.session_state
        return {"search": "peer"}

    def capture_text_input(*args, **kwargs):
        captured.append((args, kwargs))
        raise SearchCaptured

    monkeypatch.setattr(dashboard, "stock_selector_current_filter_values", current_values)
    monkeypatch.setattr(dashboard.st, "text_input", capture_text_input)

    with pytest.raises(SearchCaptured):
        dashboard.render_stock_selector(
            {},
            public_mode=True,
            target_mode=dashboard.RESEARCH_MODE,
            target_page="company-workbench",
            allowed_tickers=("NVDA",),
            research_boundary=dashboard.QUEUE_BOUNDARY,
        )
    with pytest.raises(SearchCaptured):
        dashboard.render_stock_selector(
            {},
            public_mode=True,
            target_mode=dashboard.PUBLIC_DEMO_MODE,
            target_page="single-stock-report",
        )

    assert captured == [
        (
            ("Search saved companies",),
            {
                "value": "peer",
                "placeholder": "Search ticker, theme, blocker, or proof step",
                "help": None,
                "key": "stock-selector-search",
            },
        ),
        (
            ("Search this review queue",),
            {
                "value": "peer",
                "placeholder": "Search ticker, theme, blocker, or proof step",
                "help": "Search readiness-backed rows before opening one saved report.",
                "key": "stock-selector-search",
            },
        ),
    ]


def test_monitor_follow_up_grid_is_two_columns_then_one_column_on_phone():
    source = dashboard.Path(dashboard.__file__).read_text(encoding="utf-8")
    assert '"evidence-monitor": "signal-grid evidence-monitor-grid"' in source
    assert ".signal-grid.evidence-monitor-grid {" in source
    assert "grid-template-columns: repeat(2, minmax(0, 1fr));" in source
    phone = source[source.index("@media (max-width: 760px)") :]
    assert ".signal-grid.evidence-monitor-grid" in phone
    assert "grid-template-columns: 1fr;" in phone


def test_monitor_discipline_rows_preserve_focused_cohort_order_without_rank(tmp_path, monkeypatch):
    members = tuple(
        FocusedCohortMember(
            ticker=ticker,
            company_name=f"{ticker} Company",
            sector="Technology",
            industry="Semiconductors",
            cohort_rationale="Saved readiness-backed review scope.",
            usable_lanes=("price",),
            blocked_lanes=("dcf",),
            freshness_state="current",
            last_review_date="",
            next_review_reason="Review saved evidence.",
        )
        for ticker in ("BBB", "AAA")
    )
    cohort = FocusedCohort(
        status="ready",
        requested_size=2,
        minimum_size=2,
        eligible_count=2,
        members=members,
        message="Two saved companies.",
    )
    context = dashboard.build_profile_context(project_root=tmp_path)
    monkeypatch.setattr(dashboard, "load_journal_entries", lambda path: ())
    monkeypatch.setattr(dashboard, "load_outcomes", lambda path: ())

    rows = dashboard.load_dashboard_research_discipline_rows(context, cohort, ())

    assert [row.ticker for row in rows] == ["BBB", "AAA"]
    assert "rank" not in str(rows).lower()
    assert all(row.due_lanes == ("Plan", "Evidence") for row in rows)


def test_monitor_discipline_failure_is_isolated_to_one_focused_ticker(tmp_path, monkeypatch):
    members = tuple(
        FocusedCohortMember(
            ticker=ticker,
            company_name=ticker,
            sector="Technology",
            industry="Semiconductors",
            cohort_rationale="Saved readiness-backed review scope.",
            usable_lanes=("price",),
            blocked_lanes=("dcf",),
            freshness_state="current",
            last_review_date="",
            next_review_reason="Review saved evidence.",
        )
        for ticker in ("BBB", "AAA")
    )
    cohort = FocusedCohort("ready", 2, 2, 2, members, "Two saved companies.")
    context = dashboard.build_profile_context(project_root=tmp_path)
    real_derive = dashboard.derive_journal_state

    def derive_with_one_invalid_ticker(entries, *, profile_key, ticker, as_of):
        if ticker == "BBB":
            raise ValueError("BBB journal row is invalid")
        return real_derive(entries, profile_key=profile_key, ticker=ticker, as_of=as_of)

    monkeypatch.setattr(dashboard, "load_journal_entries", lambda path: ())
    monkeypatch.setattr(dashboard, "load_outcomes", lambda path: ())
    monkeypatch.setattr(dashboard, "derive_journal_state", derive_with_one_invalid_ticker)

    rows = dashboard.load_dashboard_research_discipline_rows(context, cohort, ())

    assert [(row.ticker, row.status) for row in rows] == [
        ("BBB", "unavailable"),
        ("AAA", "process_work_needed"),
    ]
    assert rows[1].due_lanes == ("Plan", "Evidence")


def test_empty_catalyst_and_outcome_ledgers_do_not_create_attention(tmp_path, monkeypatch):
    member = FocusedCohortMember(
        ticker="ALFA",
        company_name="ALFA",
        sector="Technology",
        industry="Semiconductors",
        cohort_rationale="Saved readiness-backed review scope.",
        usable_lanes=("price",),
        blocked_lanes=("dcf",),
        freshness_state="current",
        last_review_date="",
        next_review_reason="Review saved evidence.",
    )
    cohort = FocusedCohort("ready", 1, 1, 1, (member,), "One saved company.")
    context = dashboard.build_profile_context(project_root=tmp_path)
    monkeypatch.setattr(dashboard, "DATA_DIR", tmp_path)

    rows = dashboard.load_dashboard_research_discipline_rows(
        context,
        cohort,
        (),
        as_of="2026-07-28T12:00:00Z",
    )

    assert rows[0].attention_state == "monitor"
    assert "catalyst" not in rows[0].attention_reason.lower()
    assert "outcome" not in rows[0].attention_reason.lower()


def test_monitor_uses_one_scoped_upcoming_catalyst_without_cross_ticker_state(
    tmp_path, monkeypatch
):
    members = tuple(
        FocusedCohortMember(
            ticker=ticker,
            company_name=ticker,
            sector="Technology",
            industry="Semiconductors",
            cohort_rationale="Saved readiness-backed review scope.",
            usable_lanes=("price",),
            blocked_lanes=("dcf",),
            freshness_state="current",
            last_review_date="",
            next_review_reason="Review saved evidence.",
        )
        for ticker in ("BBB", "AAA")
    )
    cohort = FocusedCohort("ready", 2, 2, 2, members, "Two saved companies.")
    context = dashboard.build_profile_context(project_root=tmp_path)
    monkeypatch.setattr(dashboard, "DATA_DIR", tmp_path)
    append_reviewed_event(
        tmp_path / "catalyst_evidence.csv",
        CatalystEvent(
            "catalyst-evidence-v1",
            "event-bbb",
            context.profile_key,
            "BBB",
            "earnings",
            "Synthetic scheduled evidence",
            "2026-08-20T21:00:00Z",
            "2026-07-20T09:00:00Z",
            "2026-07-20T10:00:00Z",
            "fixture",
            "fixture:event-bbb",
            "candidate_context_only",
            "fixture-reviewer",
            "Synthetic context only.",
        ),
        confirm_reviewed=True,
    )

    rows = dashboard.load_dashboard_research_discipline_rows(
        context,
        cohort,
        (),
        as_of="2026-07-28T12:00:00Z",
    )

    assert [row.ticker for row in rows] == ["BBB", "AAA"]
    assert rows[0].attention_state == "scheduled_catalyst"
    assert rows[0].attention_label == "Scheduled"
    assert "2026-08-20T21:00:00Z" in rows[0].attention_reason
    assert "urgent" not in rows[0].attention_reason.lower()
    assert "price" not in rows[0].attention_reason.lower()
    assert rows[1].attention_state == "monitor"


def test_malformed_shared_catalyst_ledger_fails_attention_closed(tmp_path, monkeypatch):
    member = FocusedCohortMember(
        ticker="ALFA",
        company_name="ALFA",
        sector="Technology",
        industry="Semiconductors",
        cohort_rationale="Saved readiness-backed review scope.",
        usable_lanes=("price",),
        blocked_lanes=("dcf",),
        freshness_state="current",
        last_review_date="",
        next_review_reason="Review saved evidence.",
    )
    cohort = FocusedCohort("ready", 1, 1, 1, (member,), "One saved company.")
    context = dashboard.build_profile_context(project_root=tmp_path)
    monkeypatch.setattr(dashboard, "DATA_DIR", tmp_path)
    (tmp_path / "catalyst_evidence.csv").write_text("bad,header\n1,2\n", encoding="utf-8")

    rows = dashboard.load_dashboard_research_discipline_rows(
        context,
        cohort,
        (),
        as_of="2026-07-28T12:00:00Z",
    )

    assert rows[0].attention_state == "unavailable"
    assert rows[0].attention_source == "catalyst"


def test_research_discipline_table_is_semantic_ordered_and_primary_answer_only():
    rows = (
        SimpleNamespace(
            cohort_order=1,
            ticker="BBB",
            attention_label="Scheduled",
            attention_reason="Reviewed catalyst <context> is scheduled.",
            attention_source="catalyst",
            identity="hidden-identity-bbb",
        ),
        SimpleNamespace(
            cohort_order=2,
            ticker="AAA",
            attention_label="Monitor",
            attention_reason="No saved research-process transition is due.",
            attention_source="decision_lab",
            identity="hidden-identity-aaa",
        ),
    )

    rendered = dashboard.research_discipline_table_html(rows)

    assert rendered.index("data-cohort-order='1'") < rendered.index(
        "data-cohort-order='2'"
    )
    assert rendered.count("class='research-discipline-row'") == 2
    assert "<th scope='col'>Ticker</th>" in rendered
    assert "<th scope='col'>Process attention</th>" in rendered
    assert "<th scope='col'>Why</th>" in rendered
    assert "Reviewed catalyst &lt;context&gt; is scheduled." in rendered
    assert "hidden-identity" not in rendered
    assert "attention_source" not in rendered
    assert "rank" not in rendered.lower()
    assert "score" not in rendered.lower()
    assert "return" not in rendered.lower()


def test_research_discipline_identity_table_keeps_technical_fields_in_advanced():
    rows = (
        SimpleNamespace(
            cohort_order=1,
            ticker="BBB",
            attention_source="catalyst<context>",
            identity="decision-lab-<bbb>",
        ),
        SimpleNamespace(
            cohort_order=2,
            ticker="AAA",
            attention_source="decision_lab",
            identity="decision-lab-aaa",
        ),
    )

    rendered = dashboard.research_discipline_identity_table_html(rows)

    assert rendered.count("class='research-discipline-identity-row'") == 2
    assert "<th scope='col'>Attention source</th>" in rendered
    assert "<th scope='col'>Decision Lab identity</th>" in rendered
    assert "catalyst&lt;context&gt;" in rendered
    assert "decision-lab-&lt;bbb&gt;" in rendered
    assert rendered.index("data-cohort-order='1'") < rendered.index(
        "data-cohort-order='2'"
    )


def test_monitor_discipline_empty_state_is_process_only():
    source = dashboard.Path(dashboard.__file__).read_text(encoding="utf-8")
    monitor_start = source.index("def render_research_monitor(")
    monitor_end = source.index("def render_company_workbench(", monitor_start)
    monitor = source[monitor_start:monitor_end]

    assert "monitor_primary_answer(queue)" in monitor
    assert "queue.empty_boundary" in monitor
    assert "answer_panel_html(" in monitor
    assert "data-sr-region='primary-answer'" not in monitor
    removed_helper = "research_discipline_" + "summary_cards"
    assert removed_helper not in monitor
    assert '"Process attention"' in Path("src/research_decision_lab.py").read_text(encoding="utf-8")


def test_research_evidence_detours_offer_return_before_evidence_content():
    source = dashboard.Path(dashboard.__file__).read_text(encoding="utf-8")
    data_start = source.index('elif content_page == "Data Health":')
    data_end = source.index('elif content_page == PROOF_HISTORY_PATH_TITLE:', data_start)
    data = source[data_start:data_end]
    proof_start = data_end
    proof_end = source.index('elif content_page == "Universe Manager":', proof_start)
    proof = source[proof_start:proof_end]

    for branch, renderer in ((data, "render_data_health("), (proof, "render_proof_history(")):
        header = branch.index("render_research_workspace_header(")
        boundary_delegation = branch.index("include_boundary=False", header)
        content = branch.index(renderer, boundary_delegation)
        assert header < boundary_delegation < content
        assert "st.link_button(" not in branch[header:content]

    public = dashboard.evidence_route_answer_html(
        "Data Health",
        workspace_mode=dashboard.PUBLIC_DEMO_MODE,
        ticker="AVGO",
    )
    personal = dashboard.evidence_route_answer_html(
        "Data Health",
        workspace_mode=dashboard.RESEARCH_MODE,
        ticker="AVGO",
    )
    assert "?mode=public&amp;page=single-stock-report&amp;ticker=AVGO&amp;open=1" in public
    assert "?mode=research&amp;page=company-workbench&amp;ticker=AVGO&amp;open=1" in personal


def test_dashboard_theme_keeps_primary_link_button_contrast_accessible():
    source = dashboard.Path(dashboard.__file__).read_text(encoding="utf-8")

    assert '[data-testid="stLinkButton"] a[kind="primary"] {' in source
    assert '[data-testid="stLinkButton"] a[kind="primary"] * {' in source
    primary_link_start = source.index('[data-testid="stLinkButton"] a[kind="primary"] {')
    primary_link_theme = source[
        primary_link_start : source.index("}", primary_link_start) + 1
    ]
    assert "background: #0b3b36 !important;" in primary_link_theme
    assert "border-color: #0b3b36 !important;" in primary_link_theme
    assert "color: #ffffff !important;" in primary_link_theme


def test_new_evidence_loaders_fail_closed_on_invalid_local_ledgers(tmp_path, monkeypatch):
    from types import SimpleNamespace

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "historical_valuation_observations.csv").write_text("ticker,numerator\nNVDA,nope\n", encoding="utf-8")
    (data_dir / "research_outcome_reviews.csv").write_text("bad,header\n1,2\n", encoding="utf-8")
    (data_dir / "catalyst_evidence.csv").write_text("bad,header\n1,2\n", encoding="utf-8")
    monkeypatch.setattr(dashboard, "DATA_DIR", data_dir)
    context = SimpleNamespace(profile_key="default")

    valuation = dashboard.load_dashboard_valuation_regime("NVDA", as_of="2026-07-18T05:00:00Z")
    outcome = dashboard.load_dashboard_outcome_status(context, ticker="NVDA")
    catalyst = dashboard.load_dashboard_catalyst_timeline(
        context,
        ticker="NVDA",
        as_of="2026-07-18T05:00:00Z",
    )

    assert valuation.state == "insufficient_history"
    assert outcome.state == "not_started"
    assert catalyst.state == "blocked"


def test_optional_dashboard_evidence_loaders_enable_commercial_composition():
    source = dashboard.Path(dashboard.__file__).read_text(encoding="utf-8")
    valuation_start = source.index("def load_dashboard_valuation_regime(")
    outcome_start = source.index("def load_dashboard_outcome_status(", valuation_start)
    catalyst_start = source.index("def load_dashboard_catalyst_timeline(", outcome_start)
    scenario_start = source.index("def scenario_lab_status_cards(", catalyst_start)

    assert "commercial_mode=True" in source[valuation_start:outcome_start]
    assert "commercial_mode=True" in source[outcome_start:catalyst_start]
    assert "commercial_mode=True" in source[catalyst_start:scenario_start]


def test_company_workbench_prepares_one_current_scenario_session_before_research_composition():
    source = Path("src/dashboard.py").read_text(encoding="utf-8")
    report_start = source.index("def render_single_stock_report(")
    report_end = source.index("\ndef render_data_health(", report_start)
    report = source[report_start:report_end]

    context = report.index("selected_context =")
    preparation = report.index("scenario_session = run_scenario_lab_from_state(", context)
    research_composition = report.index("if research_mode:", preparation)
    detailed_controls = report.index("render_scenario_lab(scenario_session)", research_composition)

    assert context < preparation < research_composition < detailed_controls
    assert report.count("run_scenario_lab_from_state(") == 1
    assert source.count("run_scenario_lab(") == 0


def test_company_workbench_uses_one_authoritative_task_arbitration():
    source = Path("src/dashboard.py").read_text(encoding="utf-8")
    report_start = source.index("def render_single_stock_report(")
    report_end = source.index("\ndef render_data_health(", report_start)
    report = source[report_start:report_end]

    arbitration = report.index("authoritative_task = company_next_research_task(")
    brief = report.index("primary_brief = company_workbench_primary_brief(", arbitration)
    final_summary = report.index("primary_brief=primary_brief", brief)
    html_snapshot = report.index("authoritative_task=authoritative_task", final_summary)

    assert arbitration < brief < final_summary < html_snapshot
    assert report.count("company_next_research_task(") == 1
    assert report.count("company_workbench_primary_brief(") == 1


def test_company_workbench_html_brief_is_research_only_and_follows_the_module_gate():
    """Catches exposing the portable brief before the user opens detailed modules."""

    source = Path("src/dashboard.py").read_text(encoding="utf-8")
    report_start = source.index("def render_single_stock_report(")
    report_end = source.index("\ndef render_data_health(", report_start)
    report = source[report_start:report_end]

    research_block = report.index("if research_mode:")
    primary_brief = report.index("primary_brief = company_workbench_primary_brief(", research_block)
    module_gate = report.index(
        "if research_mode and not single_stock_detail_sections_visible(ticker):",
        primary_brief,
    )
    constructor = report.index("CompanyWorkbenchHtmlInputs(", module_gate)
    brief = report.index('st.expander("HTML Research Brief", expanded=False)', module_gate)
    detail_gate = report.index("if public_mode and report_payload", brief)

    assert research_block < primary_brief < module_gate < constructor < brief < detail_gate
    assert report.count("CompanyWorkbenchHtmlInputs(") == 1
    assert report.count('st.expander("HTML Research Brief", expanded=False)') == 1
    assert report.count('"Download HTML Research Brief"') == 1
    assert 'unsafe_allow_javascript=False' in report[brief:detail_gate]
    assert 'on_click="ignore"' in report[brief:detail_gate]
    assert 'key=f"company-workbench-html:{selected_context.profile_key}:{ticker}"' in report[brief:detail_gate]


def test_company_workbench_module_gate_uses_primary_button_and_preserves_open_semantics(
    monkeypatch,
):
    """Catches an enabled module gate inheriting the low-contrast secondary style."""

    calls: list[tuple[str, dict[str, object]]] = []
    reruns: list[bool] = []
    session_state: dict[str, object] = {}
    clicked = False

    def button(label: str, **kwargs: object) -> bool:
        calls.append((label, kwargs))
        return clicked

    monkeypatch.setattr(
        dashboard,
        "st",
        SimpleNamespace(
            button=button,
            session_state=session_state,
            rerun=lambda: reruns.append(True),
        ),
    )

    dashboard.render_company_workbench_module_gate("aapl")

    assert calls == [
        (
            "Open evidence and analysis modules",
            {
                "key": "single-stock-detail-sections:AAPL:research-open",
                "type": "primary",
            },
        )
    ]
    assert session_state == {}
    assert reruns == []

    clicked = True
    dashboard.render_company_workbench_module_gate("aapl")

    assert session_state == {"single-stock-detail-sections:AAPL": True}
    assert reruns == [True]


def test_company_workbench_change_badge_uses_explicit_change_context_kind():
    source = Path("src/dashboard.py").read_text(encoding="utf-8")
    change_start = source.index('change_answer = company_change_answer(ticker, research_review_items)')
    change_end = source.index('st.markdown("## Business Trend")', change_start)
    composition = source[change_start:change_end]

    assert 'change_answer["change_context_kind"]' in composition
    assert '"source-backed change"' in composition
    assert '"snapshot evidence only"' in composition
    assert '"no queued change"' in composition
    assert '"source-backed only"' not in composition


def test_company_workbench_places_one_decision_lab_after_what_changed_before_business_trend():
    source = Path("src/dashboard.py").read_text(encoding="utf-8")
    report_start = source.index("def render_single_stock_report(")
    report_end = source.index("\ndef render_data_health(", report_start)
    report = source[report_start:report_end]

    selected_answer = report.index("render_single_stock_public_summary(")
    what_changed = report.index('st.markdown("## What Changed")', selected_answer)
    decision_lab = report.index('st.markdown("## Research Decision Lab")', what_changed)
    business_trend = report.index('st.markdown("## Business Trend")', decision_lab)
    conclusion = report.index('st.markdown("## Research Conclusion")', business_trend)

    assert selected_answer < what_changed < decision_lab < business_trend < conclusion
    assert report.count('st.markdown("## Research Decision Lab")') == 1
    assert report.count('st.markdown("## Next Research Task")') == 0
    assert 'st.expander("Advanced: Decision Lab evidence", expanded=False)' in report
    assert "decision_lab_state.identity" in report


def test_skip_link_renders_in_mode_appropriate_first_focus_bucket_before_page_answer():
    source = dashboard.Path(dashboard.__file__).read_text(encoding="utf-8")

    href = dashboard.public_workflow_skip_href(
        "Company Workbench",
        {
            "mode": "research",
            "page": "company-workbench",
            "ticker": "AVGO",
            "open": "1",
        },
        mode=nav.RESEARCH_MODE,
    )
    assert href == "#public-page-answer"

    main = source[source.index("def main()"):]
    public_research_skip = main.index("render_public_workflow_skip_link(")
    operator_branch = main.index("if operator_mode:")
    sidebar_entrypoint = main.index("with st.sidebar:")
    sidebar_header = main.index("render_sidebar_nav_header()")
    answer_target = main.index("render_public_workflow_skip_target()")
    dispatch = main.index("if research_mode and render_personal_research_route(")

    assert public_research_skip < operator_branch < sidebar_entrypoint < sidebar_header
    assert "st_api=st.sidebar" in main[operator_branch:sidebar_entrypoint]
    assert "st_api=st.sidebar" not in main[public_research_skip:operator_branch]
    assert sidebar_header < answer_target < dispatch
    assert main.count("render_public_workflow_skip_link(") == 2


def test_semantic_main_bridge_runs_once_immediately_after_theme_before_route_content():
    source = dashboard.Path(dashboard.__file__).read_text(encoding="utf-8")
    main_start = source.index("def main() -> None:")
    main_end = source.index('\n\nif __name__ == "__main__":', main_start)
    main = source[main_start:main_end]

    bridge_call = "render_semantic_main_bridge()"
    assert (
        source.count(
            "from src.accessibility_bridge import render_semantic_main_bridge"
        )
        == 1
    )
    assert main.count(bridge_call) == 1

    theme = main.index("apply_dashboard_theme()")
    bridge = main.index(bridge_call)
    first_route_content = min(
        main.index("render_public_route_bootstrap("),
        main.index("render_public_workflow_skip_link("),
        main.index("with st.sidebar:"),
        main.index("render_public_app_shell("),
        main.index("render_personal_research_route("),
    )

    assert theme < bridge < first_route_content
    assert (
        main[theme:bridge].strip()
        == "apply_dashboard_theme()"
    )


def test_research_primary_sections_follow_route_h1_with_level_two_headings():
    source = dashboard.Path(dashboard.__file__).read_text(encoding="utf-8")
    expected_level_two = (
        "Follow-up Queue",
        "What Changed",
        "Research Decision Lab",
        "Business Trend",
        "Valuation",
        "Forward View",
        "What Remains Withheld",
        "Research Conclusion",
        "Advanced Evidence",
    )

    for heading in expected_level_two:
        assert f'st.markdown("## {heading}")' in source
        assert f'st.markdown("### {heading}")' not in source
    assert 'question="Find a Company · Screen eligibility — when supported"' in source


def test_company_workbench_primary_actions_use_explicit_44px_browser_targets():
    source = dashboard.Path(dashboard.__file__).read_text(encoding="utf-8")
    styles_start = source.index("def render_research_workspace_styles()")
    styles_end = source.index("\ndef render_research_workspace_header(", styles_start)
    styles = source[styles_start:styles_end]

    data_health_start = styles.index(
        ".company-workbench-primary-answer .public-primary-action {"
    )
    data_health_end = styles.index("}", data_health_start)
    data_health_rule = styles[data_health_start:data_health_end]

    assert "display: inline-flex;" in data_health_rule
    assert "align-items: center;" in data_health_rule
    assert "min-height: 44px;" in data_health_rule
    assert (
        'div[data-testid="stButton"] > button {\n'
        "            min-height: 44px;\n"
        "        }"
    ) in styles


def test_company_workbench_html_brief_download_target_is_a_keyed_44px_control():
    """Catches a sub-44px brief download target or a rule leaking into other routes."""

    source = dashboard.Path(dashboard.__file__).read_text(encoding="utf-8")
    styles_start = source.index("def render_research_workspace_styles()")
    styles_end = source.index("\ndef render_research_workspace_header(", styles_start)
    styles = source[styles_start:styles_end]

    selector = '[class*="st-key-company-workbench-html-"] [data-testid="stDownloadButton"] button'
    assert styles.count('[data-testid="stDownloadButton"]') == 1
    download_start = styles.index(selector)
    download_end = styles.index("}", download_start)
    download_rule = styles[download_start:download_end]

    assert "min-height: 44px;" in download_rule


def test_company_workbench_uses_two_mobile_lanes_then_one_at_two_hundred_percent():
    source = dashboard.Path(dashboard.__file__).read_text(encoding="utf-8")
    styles_start = source.index("def render_research_workspace_styles()")
    styles_end = source.index("\ndef render_research_workspace_header(", styles_start)
    styles = source[styles_start:styles_end]

    mobile = styles[styles.index("@media (max-width: 640px)") :]
    assert "grid-template-columns: repeat(2, minmax(0, 1fr));" in mobile
    narrow = styles[styles.index("@media (max-width: 260px)") :]
    assert ".company-workbench-primary-grid { grid-template-columns: 1fr; }" in narrow


def test_public_evidence_routes_receive_explicit_mode_and_personal_headers_defer_boundary():
    source = Path(dashboard.__file__).read_text(encoding="utf-8")
    main = source[source.index("def main()") :]
    data_health = main[main.index('elif content_page == "Data Health":') :]
    proof_history = main[main.index("elif content_page == PROOF_HISTORY_PATH_TITLE:") :]

    assert 'render_research_workspace_header(\n                "Data Health"' in data_health
    assert 'render_research_workspace_header(\n                "Proof History"' in proof_history
    assert "compact=True" in data_health[: data_health.index("render_data_health(")]
    assert "compact=True" in proof_history[: proof_history.index("render_proof_history(")]
    assert "include_boundary=False" in data_health[: data_health.index("render_data_health(")]
    assert "include_boundary=False" in proof_history[: proof_history.index("render_proof_history(")]
    assert "workspace_mode=mode" in data_health[: data_health.index('elif content_page == PROOF_HISTORY_PATH_TITLE:')]
    assert "workspace_mode=mode" in proof_history
    assert "public_mode=not operator_mode" in data_health
    assert "public_mode=not operator_mode" in proof_history


def test_public_and_evidence_route_renderers_adopt_one_shared_hierarchy_without_touching_workbench():
    source = Path(dashboard.__file__).read_text(encoding="utf-8")
    data_health_start = source.index("def render_data_health(")
    data_health_end = source.index("\ndef render_research_workspace_styles(", data_health_start)
    data_health = source[data_health_start:data_health_end]
    proof_start = source.index("def render_proof_history(")
    proof_end = source.index("\ndef data_health_latest_reviewed_batch_packet_frame", proof_start)
    proof = source[proof_start:proof_end]
    report_start = source.index("def render_single_stock_report(")
    report_end = source.index("\ndef render_data_health(", report_start)
    report = source[report_start:report_end]

    coverage_summary_index = data_health.index("render_data_health_coverage_summary(")
    assert data_health.index("evidence_route_answer_html(") < coverage_summary_index
    assert data_health.index("supporting_detail_html(") < coverage_summary_index
    assert data_health.index("advanced_detail_marker_html()") < data_health.index(
        'st.expander("Advanced: how readiness works", expanded=False)'
    )
    assert proof.index("evidence_route_answer_html(") < proof.index(
        "proof_history_public_timeline_html(proof_timeline, batch_proof_frame)"
    )
    assert proof.index("advanced_detail_marker_html()") < proof.index(
        'st.expander("Advanced: proof ledger details", expanded=False)'
    )
    assert 'key="single-stock-public-ticker"' in report
    assert 'key="single-stock-report-button"' in report
    assert "selected_answer_target=selected_answer_target" in report
    assert "selected_detail_target=selected_detail_target" in report
