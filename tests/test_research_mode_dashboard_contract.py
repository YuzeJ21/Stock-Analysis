from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

from src import dashboard
from src import dashboard_navigation as nav
from src.catalyst_evidence_timeline import CatalystEvent, append_reviewed_event
from src.daily_research_queue import (
    DailyQueueEvidence,
    compare_daily_queues,
    evaluate_daily_queue,
)
from src.daily_research_queue_adapter import DailyQueueBuildStatus
from src.focused_research_cohort import FocusedCohort, FocusedCohortMember, build_focused_cohort
from src.research_decision_lab import ResearchDisciplineRow
from src.weekly_research_summary import WeeklyResearchSummary


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

    assert rendered == []


def test_personal_research_route_loads_once_from_selected_profile_and_passes_one_result(
    monkeypatch,
):
    context = SimpleNamespace(data_dir=Path("/selected-profile/data"))
    recency = object()
    review_date = date(2026, 7, 27)
    load_calls: list[tuple[Path, str, date]] = []
    rendered: list[tuple[str, object]] = []
    daily_queue_calls: list[object] = []
    queue_status = object()

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
        lambda *args, **kwargs: rendered.append(("Discover", kwargs["observation_recency"])),
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
        lambda status: daily_queue_calls.append(status),
        raising=False,
    )
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
        assert daily_queue_calls == ([queue_status] if selected_page == "Discover" else [])
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

    assert "Legacy research utility — not part of Personal Research Mode" in shell
    assert "recommendations, company ranking for action, position sizing, transaction direction" in shell
    assert 'st.expander("Advanced: legacy compatibility output", expanded=False)' in monthly
    assert "_render_monthly_picks_legacy_output(catalog)" in monthly
    assert 'st.expander("Advanced: legacy compatibility output", expanded=False)' in output
    assert "_render_legacy_output_tab(title, output_frames, show_reason_details)" in output


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
    monkeypatch.setattr(dashboard, "render_research_workspace_header", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        dashboard,
        "load_dashboard_daily_research_queue",
        lambda *args, **kwargs: object(),
        raising=False,
    )
    monkeypatch.setattr(
        dashboard,
        "render_daily_research_queue",
        lambda status: calls.append("strict eligibility"),
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

    assert "## Find a Company" in headings
    assert calls[:2] == ["strict eligibility", "saved browsing"]
    assert calls[2:] == ["advanced"]


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
    brief_html = desk.index("research_desk_brief_html(brief)", brief)
    advanced = desk.index('with st.expander("Advanced Evidence", expanded=False):', brief_html)
    weekly_cards = desk.index("weekly_summary_cards(weekly_summary)", advanced)
    cohort = desk.index("focused_cohort_cards(cohort)", weekly_cards)
    coverage = desk.index("focused_cohort_coverage_cards(coverage)", cohort)
    cohort_frame = desk.index("focused_cohort_frame(cohort)", coverage)
    coverage_frame = desk.index("focused_cohort_coverage_frame(coverage)", cohort_frame)
    change_detail = desk.index('render_research_change_route_summary("Research Desk", state)', coverage_frame)

    assert brief < brief_html < advanced < weekly_cards
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
    source = dashboard.Path(dashboard.__file__).read_text(encoding="utf-8")
    start = source.index("def render_research_workspace_styles()")
    end = source.index("\ndef render_research_workspace_header(", start)
    styles = source[start:end]

    normal_styles = styles.index("st.markdown(")
    preferences = styles.index("research_accessibility_media_preferences_css()")
    assert normal_styles < preferences
    assert "unsafe_allow_html=True" in styles[preferences:]


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
    assert actions == [("Open Discover", "?mode=research&page=discover")]
    copy = " ".join(rendered)
    assert "does not prove that no external event" in copy
    assert "Evidence Monitor Brief" not in copy
    assert "Research Discipline Review" not in copy
    assert "Research change monitor" not in copy
    assert "Advanced: Monitor evidence" in expanders


def test_monitor_actionable_state_renders_five_panels_without_duplicate_return_action(
    monkeypatch,
):
    cards: list[tuple[list[dict[str, object]], str]] = []
    actions: list[tuple[str, str]] = []
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

    monkeypatch.setattr(dashboard, "render_research_workspace_header", lambda *args, **kwargs: None)
    monkeypatch.setattr(dashboard, "load_dashboard_research_discipline_rows", lambda *args, **kwargs: (row,))
    monkeypatch.setattr(dashboard, "load_dashboard_nowcast_cohort", lambda: ())
    monkeypatch.setattr(dashboard, "cohort_readiness_cards", lambda rows: [])
    monkeypatch.setattr(dashboard, "render_research_change_route_summary", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        dashboard,
        "render_signal_cards",
        lambda values, **kwargs: cards.append((values, str(kwargs.get("variant") or ""))),
    )
    monkeypatch.setattr(dashboard.st, "markdown", lambda *args, **kwargs: None)
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
            status="no_changes",
            as_of="2026-08-04T00:00:00+00:00",
            cohort_size=1,
            unique_event_count=0,
            items=(),
            message="No traceable cohort evidence change requires review this week.",
        ),
        object(),
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

    assert "queue.empty_title" in monitor
    assert "queue.empty_boundary" in monitor
    assert "research-monitor-neutral" in monitor
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
        return_link = branch.index("research_evidence_return_link(", header)
        button = branch.index("st.link_button(", return_link)
        purpose = branch.index('st.caption(return_link["purpose"])', button)
        content = branch.index(renderer, purpose)
        assert header < return_link < button < purpose < content


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
    brief = report.index('st.expander("HTML Research Brief", expanded=False)', module_gate)
    detail_gate = report.index("if public_mode and report_payload", brief)

    assert research_block < primary_brief < module_gate < brief < detail_gate
    assert report.count('st.expander("HTML Research Brief", expanded=False)') == 1
    assert report.count('"Download HTML Research Brief"') == 1
    assert 'unsafe_allow_javascript=False' in report[brief:detail_gate]
    assert 'on_click="ignore"' in report[brief:detail_gate]
    assert 'key=f"company-workbench-html:{selected_context.profile_key}:{ticker}"' in report[brief:detail_gate]


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


def test_skip_link_renders_in_first_sidebar_bucket_before_page_answer():
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
    skip_call = main.index("render_public_workflow_skip_link(")
    sidebar_entrypoint = main.index("with st.sidebar:")
    sidebar_header = main.index("render_sidebar_nav_header()")
    answer_target = main.index("render_public_workflow_skip_target()")
    dispatch = main.index("if research_mode and render_personal_research_route(")

    assert "st_api=st.sidebar" in main[skip_call:sidebar_entrypoint]
    assert skip_call < sidebar_entrypoint < sidebar_header < answer_target < dispatch
    assert main.count("render_public_workflow_skip_link(") == 1


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
        "Find a Company",
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
