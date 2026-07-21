from pathlib import Path
from unittest.mock import patch

from src.company_workbench_cash_generation_preview import (
    CashGenerationPreviewMetric,
    CompanyWorkbenchCashGenerationPreview,
)


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


def test_explicit_cash_preview_route_renders_accepted_answer_without_network():
    from src.dashboard_render_smoke import DashboardRenderRoute, render_public_routes

    preview = CompanyWorkbenchCashGenerationPreview(
        ticker="NVDA",
        fiscal_period="2027-Q1",
        status="accepted_for_review",
        message="Accepted SEC evidence supports a cash-generation review preview.",
        operating_margin=CashGenerationPreviewMetric(
            "operating_margin", "preview_available", 0.65595785, "2027-Q1", (), ""
        ),
        free_cash_flow=CashGenerationPreviewMetric(
            "free_cash_flow", "preview_available", 48_587_000_000, "2027-Q1", (), ""
        ),
        fcf_margin=CashGenerationPreviewMetric(
            "fcf_margin", "preview_available", 0.59532439, "2027-Q1", (), ""
        ),
        blockers=(),
        withheld_metrics=(),
        accession="0001045810-26-000052",
        source_url="https://www.sec.gov/Archives/edgar/data/1045810/filing.htm",
        accepted_at="2026-05-20T20:35:52+00:00",
        cutoff="2026-07-21T03:59:59+00:00",
        capex_sign_evidence="explicit_filed_table_outflow",
        components=(),
    )
    route = DashboardRenderRoute(
        name="Company Workbench cash preview",
        query_params=(
            ("mode", "research"),
            ("page", "company-workbench"),
            ("ticker", "NVDA"),
            ("open", "1"),
            ("cash_preview", "1"),
        ),
        required_markers=(
            "Cash-generation review preview",
            "not production evidence",
            "OPERATING MARGIN",
            "FREE CASH FLOW",
            "FCF MARGIN",
            "65.6%",
            "48,587,000,000",
            "59.5%",
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
