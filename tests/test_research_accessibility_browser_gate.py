from __future__ import annotations

from pathlib import Path


def test_accessibility_browser_gate_covers_both_viewports_and_research_routes():
    from src.research_accessibility_browser_gate import RESEARCH_ROUTES, VIEWPORTS

    assert VIEWPORTS == ((1280, 720), (390, 844))
    assert [route.name for route in RESEARCH_ROUTES] == [
        "Research Desk",
        "Discover",
        "Company Workbench",
        "Monitor",
    ]
    assert RESEARCH_ROUTES[2].route.endswith(
        "page=company-workbench&ticker=NVDA&open=1"
    )


def test_discover_action_contract_uses_every_actual_row_and_fails_when_empty():
    from src.research_accessibility_browser_gate import (
        evaluate_discover_action_names,
    )

    passed = evaluate_discover_action_names(
        ["Open NVDA review", "Open AVGO review", "Open BRK.B review"]
    )
    empty = evaluate_discover_action_names([])
    duplicate = evaluate_discover_action_names(
        ["Open NVDA review", "Open NVDA review"]
    )

    assert passed == {
        "passed": True,
        "actual_count": 3,
        "detail": "3 eligible Discover actions have unique ticker-specific names",
    }
    assert empty["passed"] is False
    assert empty["actual_count"] == 0
    assert "no eligible Discover actions" in str(empty["detail"])
    assert duplicate["passed"] is False
    assert "unique" in str(duplicate["detail"])


def test_gate_fails_closed_when_explicit_browser_runtime_is_missing(tmp_path):
    from src.research_accessibility_browser_gate import (
        run_research_accessibility_browser_gate,
    )

    payload = run_research_accessibility_browser_gate(
        tmp_path,
        chrome_executable=tmp_path / "missing-chrome",
    )

    assert payload["verdict"] == "failed"
    assert payload["results"] == []
    assert "browser runtime" in " ".join(payload["failures"]).lower()


def test_focused_skip_geometry_must_be_fully_inside_the_horizontal_viewport():
    from src.research_accessibility_browser_gate import evaluate_skip_geometry

    assert evaluate_skip_geometry(
        {"x": 16, "width": 174, "height": 44},
        viewport_width=390,
    ) == {
        "passed": True,
        "detail": "focused skip geometry x=16.0..190.0 within 390px viewport",
    }
    assert evaluate_skip_geometry(
        {"x": -320, "width": 174, "height": 44},
        viewport_width=390,
    )["passed"] is False
    assert evaluate_skip_geometry(
        {"x": 350, "width": 174, "height": 44},
        viewport_width=390,
    )["passed"] is False
    assert evaluate_skip_geometry(
        {"x": 16, "width": 0, "height": 44},
        viewport_width=390,
    )["passed"] is False


def test_makefile_exposes_non_writing_browser_gate():
    makefile = Path("Makefile").read_text(encoding="utf-8")

    assert "research-accessibility-browser-check:" in makefile
    assert "python3 -m src.research_accessibility_browser_gate" in makefile


def test_browser_gate_source_has_no_artifact_writer_or_screenshot_capture():
    source = Path("src/research_accessibility_browser_gate.py").read_text(
        encoding="utf-8"
    )
    lowered = source.lower()

    for forbidden in (
        "write_text(",
        "write_bytes(",
        "json.dump(",
        ".screenshot(",
        "page.screenshot",
    ):
        assert forbidden not in lowered
    assert "STOCK_RESEARCH_DATA_PROFILE" in source
    assert '"demo"' in source
