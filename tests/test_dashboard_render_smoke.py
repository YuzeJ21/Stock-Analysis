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
