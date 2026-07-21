from pathlib import Path

from src import dashboard
from src import dashboard_navigation as nav
from src.focused_research_cohort import build_focused_cohort


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


def test_research_discover_renders_selector_before_advanced_cohort_context():
    source = dashboard.Path(dashboard.__file__).read_text(encoding="utf-8")
    discover_start = source.index('elif research_mode and selected_page == "Discover":')
    discover_end = source.index(
        'elif research_mode and selected_page == "Company Workbench":',
        discover_start,
    )
    discover = source[discover_start:discover_end]

    heading = discover.index('st.markdown("### Which stock can I review?")')
    selector = discover.index("render_stock_selector(", heading)
    advanced = discover.index(
        'with st.expander("Advanced: cohort readiness context", expanded=False):'
    )
    cohort = discover.index("focused_cohort_cards(focused_cohort)", advanced)
    coverage = discover.index(
        "focused_cohort_coverage_cards(focused_cohort_coverage)",
        advanced,
    )

    assert heading < selector < advanced < cohort < coverage


def test_company_workbench_keeps_lane_coverage_collapsed_before_report_answer():
    source = dashboard.Path(dashboard.__file__).read_text(encoding="utf-8")
    workbench_start = source.index("def render_company_workbench(")
    workbench_end = source.index("\ndef main()", workbench_start)
    workbench = source[workbench_start:workbench_end]

    selected = workbench.index('st.markdown("### Selected Company")')
    advanced = workbench.index(
        'with st.expander("Advanced: selected-company lane coverage", expanded=False):'
    )
    coverage = workbench.index("focused_ticker_coverage_cards(coverage, ticker)", advanced)
    report = workbench.index("render_single_stock_report(", coverage)

    assert selected < advanced < coverage < report


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

    business = report.index('st.markdown("### Business Trend")')
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

    weekly = desk.index('st.markdown("### Weekly research summary")')
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
    assert "@media (max-width: 640px)" in styles


def test_company_workbench_keeps_selected_company_before_collapsed_review_path_and_details():
    source = dashboard.Path(dashboard.__file__).read_text(encoding="utf-8")
    start = source.index("def render_company_workbench(")
    end = source.index("\ndef main()", start)
    workbench = source[start:end]

    selected = workbench.index('st.markdown("### Selected Company")')
    review = workbench.index('with st.expander("Review path", expanded=False):', selected)
    path = workbench.index('st.caption(" -> ".join(section_names[:-1]))', review)
    coverage = workbench.index('with st.expander("Advanced: selected-company lane coverage", expanded=False):', path)
    report = workbench.index("render_single_stock_report(", coverage)

    assert selected < review < path < coverage < report
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
    answer = monitor.index('st.markdown("### Research change monitor")', weekly)
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

    assert weekly < answer < frame < empty < note < discover < cohort < advanced
    assert advanced < readiness_heading < readiness_cards < readiness_frame
    assert 'tone="success"' not in monitor[empty:discover]


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


def test_dashboard_theme_keeps_primary_link_button_text_white():
    source = dashboard.Path(dashboard.__file__).read_text(encoding="utf-8")

    assert '[data-testid="stLinkButton"] a[kind="primary"],' in source
    assert '[data-testid="stLinkButton"] a[kind="primary"] * {' in source
    assert "color: #ffffff !important;" in source[source.index('[data-testid="stLinkButton"] a[kind="primary"],'):]


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
    workbench_start = source.index('st.markdown("### Research Conclusion")')
    workbench_end = source.index("\n    if public_mode and report_payload", workbench_start)
    composition = source[workbench_start:workbench_end]

    assert "company_next_research_task(" in composition
    assert 'st.markdown("### Next Research Task")' in composition
    assert '"title": str(authoritative_task["title"])' in composition
    assert '"body": str(authoritative_task["body"])' in composition
    assert '"badges": list(authoritative_task["badges"])' in composition
    assert '"state": str(authoritative_task["state"])' in composition
    assert composition.count('"kicker": "ONE NEXT TASK"') == 1
