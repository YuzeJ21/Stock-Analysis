from datetime import date
from pathlib import Path
from types import SimpleNamespace

from src import dashboard
from src import dashboard_navigation as nav
from src.focused_research_cohort import FocusedCohort, FocusedCohortMember, build_focused_cohort


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
        load_calls.clear()
        rendered.clear()


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


def test_research_discover_renders_selector_before_advanced_cohort_context():
    source = dashboard.Path(dashboard.__file__).read_text(encoding="utf-8")
    route_start = source.index("def render_personal_research_route(")
    discover_start = source.index('elif selected_page == "Discover":', route_start)
    discover_end = source.index(
        'elif selected_page == "Company Workbench":',
        discover_start,
    )
    discover = source[discover_start:discover_end]

    heading = discover.index('st.markdown("## Which stock can I review?")')
    selector = discover.index("render_stock_selector(", heading)
    advanced = discover.index(
        'with st.expander("Advanced: cohort readiness context", expanded=False):'
    )
    cohort = discover.index("focused_cohort_cards(cohort)", advanced)
    coverage = discover.index(
        "focused_cohort_coverage_cards(coverage)",
        advanced,
    )

    assert heading < selector < advanced < cohort < coverage


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


def test_research_desk_renders_answers_before_advanced_cohort_context():
    source = dashboard.Path(dashboard.__file__).read_text(encoding="utf-8")
    desk_start = source.index("def render_research_desk(")
    desk_end = source.index("def render_research_monitor(", desk_start)
    desk = source[desk_start:desk_end]

    weekly = desk.index('st.markdown("## Weekly research summary")')
    weekly_cards = desk.index("weekly_summary_cards(weekly_summary)", weekly)
    answers = desk.index("cards = research_desk_cards(", weekly_cards)
    answers_html = desk.index("research_desk_cards_html(cards)", answers)
    discover = desk.index('st.link_button("Open Discover"', answers_html)
    advanced = desk.index('with st.expander("Advanced Evidence", expanded=False):', discover)
    cohort = desk.index("focused_cohort_cards(cohort)", advanced)
    coverage = desk.index("focused_cohort_coverage_cards(coverage)", cohort)
    cohort_frame = desk.index("focused_cohort_frame(cohort)", coverage)
    coverage_frame = desk.index("focused_cohort_coverage_frame(coverage)", cohort_frame)

    assert weekly < weekly_cards < answers < answers_html < discover < advanced
    assert advanced < cohort < coverage < cohort_frame < coverage_frame


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


def test_monitor_renders_change_answer_before_advanced_readiness():
    source = dashboard.Path(dashboard.__file__).read_text(encoding="utf-8")
    monitor_start = source.index("def render_research_monitor(")
    monitor_end = source.index("def render_company_workbench(", monitor_start)
    monitor = source[monitor_start:monitor_end]

    weekly = monitor.index("weekly_summary_cards(weekly_summary)")
    discipline = monitor.index('st.markdown("## Research Discipline Review")', weekly)
    answer = monitor.index('st.markdown("## Research change monitor")', discipline)
    frame = monitor.index("research_monitor_frame(state.get", answer)
    empty = monitor.index("if frame.empty:", frame)
    note = monitor.index("render_context_note(", empty)
    discover = monitor.index('st.link_button("Open Discover"', note)
    cohort = monitor.index("nowcast_cohort = load_dashboard_nowcast_cohort()", discover)
    advanced = monitor.index(
        'with st.expander("Advanced: five-company Earnings Nowcast readiness", expanded=False):',
        cohort,
    )
    readiness_heading = monitor.index('st.markdown("### Earnings evidence readiness")', advanced)
    readiness_cards = monitor.index("cohort_readiness_cards(nowcast_cohort)", readiness_heading)
    readiness_frame = monitor.index("pd.DataFrame([asdict(row) for row in nowcast_cohort])", readiness_cards)

    assert weekly < discipline < answer < frame < empty < note < discover < cohort < advanced
    assert advanced < readiness_heading < readiness_cards < readiness_frame
    assert 'tone="success"' not in monitor[empty:discover]


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


def test_monitor_discipline_empty_state_is_process_only():
    source = dashboard.Path(dashboard.__file__).read_text(encoding="utf-8")
    monitor_start = source.index("def render_research_monitor(")
    monitor_end = source.index("def render_company_workbench(", monitor_start)
    monitor = source[monitor_start:monitor_end]

    assert "No process item is currently due from saved reviewer-authored evidence." in monitor
    assert "This does not claim that no market event, risk, or external research need exists." in monitor


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
    scenario_start = source.index("def scenario_lab_input_from_report(", catalyst_start)

    assert "commercial_mode=True" in source[valuation_start:outcome_start]
    assert "commercial_mode=True" in source[outcome_start:catalyst_start]
    assert "commercial_mode=True" in source[catalyst_start:scenario_start]


def test_company_workbench_uses_one_authoritative_task_arbitration():
    source = Path("src/dashboard.py").read_text(encoding="utf-8")
    workbench_start = source.index('st.markdown("## Research Conclusion")')
    workbench_end = source.index("\n    if public_mode and report_payload", workbench_start)
    composition = source[workbench_start:workbench_end]

    assert "company_next_research_task(" in composition
    assert 'st.markdown("## Next Research Task")' in composition
    assert '"title": str(authoritative_task["title"])' in composition
    assert '"body": str(authoritative_task["body"])' in composition
    assert '"badges": list(authoritative_task["badges"])' in composition
    assert '"state": str(authoritative_task["state"])' in composition
    assert composition.count('"kicker": "ONE NEXT TASK"') == 1


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
    next_task = report.index('st.markdown("## Next Research Task")', conclusion)

    assert selected_answer < what_changed < decision_lab < business_trend < conclusion < next_task
    assert report.count('st.markdown("## Research Decision Lab")') == 1
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


def test_research_primary_sections_follow_route_h1_with_level_two_headings():
    source = dashboard.Path(dashboard.__file__).read_text(encoding="utf-8")
    expected_level_two = (
        "Weekly research summary",
        "Research Discipline Review",
        "Research change monitor",
        "Which stock can I review?",
        "What Changed",
        "Research Decision Lab",
        "Business Trend",
        "Valuation",
        "Forward View",
        "What Remains Withheld",
        "Research Conclusion",
        "Next Research Task",
        "Advanced Evidence",
    )

    for heading in expected_level_two:
        assert f'st.markdown("## {heading}")' in source
        assert f'st.markdown("### {heading}")' not in source
