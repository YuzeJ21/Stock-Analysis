from pathlib import Path


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
