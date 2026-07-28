from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from src.company_workbench_cash_generation_preview import (
    CashGenerationPreviewMetric,
    CompanyWorkbenchCashGenerationPreview,
)
from src.observation_recency import load_observation_recency


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
        required_markers=("Company Workbench", "profile_price_lane", "AVGO", "SPY", "QQQ", "Research-only"),
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
    for row in (observation.selected_ticker, *observation.benchmarks):
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
    app = AppTest.from_file("src/dashboard.py", default_timeout=120)
    app.query_params.update({"mode": "research", "page": "research-desk"})
    app.run(timeout=120)

    assert not app.exception
    sidebar_markdown = [item.value for item in app.sidebar.markdown]
    main_markdown = [item.value for item in app.main.markdown]

    assert "class='public-skip-link'" in sidebar_markdown[0]
    assert not any("class='public-skip-link'" in value for value in main_markdown)


def test_authoring_composer_renders_once_only_in_closed_research_company_workbench():
    workbench = AppTest.from_file("src/dashboard.py", default_timeout=120)
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

    public_report = AppTest.from_file("src/dashboard.py", default_timeout=120)
    public_report.query_params.update(
        {"mode": "public", "page": "single-stock-report", "ticker": "NVDA", "open": "1"}
    )
    public_report.run(timeout=120)

    assert not public_report.exception
    assert not any(item.label == "Add a reviewed research record" for item in public_report.expander)

    operator_report = AppTest.from_file("src/dashboard.py", default_timeout=120)
    operator_report.query_params.update(
        {"mode": "operator", "page": "single-stock-report", "ticker": "NVDA", "open": "1"}
    )
    operator_report.run(timeout=120)

    assert not operator_report.exception
    assert not any(item.label == "Add a reviewed research record" for item in operator_report.expander)


def test_monitor_renders_research_discipline_after_weekly_summary_without_ranking():
    from src.dashboard_render_smoke import DashboardRenderRoute, render_public_routes

    route = DashboardRenderRoute(
        name="Monitor Research Discipline Review",
        query_params=(("mode", "research"), ("page", "monitor")),
        required_markers=(
            "WEEKLY RESEARCH SUMMARY",
            "Research Discipline Review",
            "Research change monitor",
            "Advanced: Research Discipline evidence",
            "Research-only",
        ),
    )

    result = render_public_routes(Path("."), routes=(route,))[0]
    rendered = "\n".join(result.rendered_blocks)

    assert result.exceptions == ()
    assert rendered.index("WEEKLY RESEARCH SUMMARY") < rendered.index("Research Discipline Review")
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
