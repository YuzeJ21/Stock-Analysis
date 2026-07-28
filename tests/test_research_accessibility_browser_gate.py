from __future__ import annotations

from pathlib import Path


def test_accessibility_browser_gate_covers_both_viewports_and_all_six_research_routes():
    from src.research_accessibility_browser_gate import RESEARCH_ROUTES, VIEWPORTS

    assert VIEWPORTS == ((1280, 720), (390, 844))
    assert [route.name for route in RESEARCH_ROUTES] == [
        "Research Desk",
        "Discover",
        "Company Workbench",
        "Monitor",
        "Research Data Health",
        "Research Proof History",
    ]
    assert [
        (route.route, route.marker, route.requires_primary_navigation)
        for route in RESEARCH_ROUTES
    ] == [
        ("/?mode=research&page=research-desk", "Weekly research summary", True),
        ("/?mode=research&page=discover", "Which stock can I review?", True),
        (
            "/?mode=research&page=company-workbench&ticker=NVDA&open=1",
            "Company Workbench",
            True,
        ),
        ("/?mode=research&page=monitor", "WEEKLY RESEARCH SUMMARY", True),
        (
            "/?mode=research&page=data-health&ticker=NVDA",
            "Data Health",
            False,
        ),
        (
            "/?mode=research&page=proof-history&ticker=NVDA",
            "Proof History",
            False,
        ),
    ]


def test_semantic_main_landmark_contract_requires_exact_unique_dom_state():
    from src.research_accessibility_browser_gate import (
        evaluate_semantic_main_landmark,
    )

    passed = evaluate_semantic_main_landmark(
        main_count=1,
        main_role="main",
        main_id="research-main",
        main_label="Stock research workspace",
        answer_count=1,
        h1_count=1,
        bridge_status="applied",
        phase="initial",
    )
    duplicate = evaluate_semantic_main_landmark(
        main_count=2,
        main_role="main",
        main_id="research-main",
        main_label="Stock research workspace",
        answer_count=1,
        h1_count=1,
        bridge_status="ambiguous",
        phase="rerender",
    )

    assert all(assertion["passed"] for assertion in passed)
    assert [assertion["name"] for assertion in passed] == [
        "semantic_main_initial_unique",
        "semantic_main_initial_metadata",
        "semantic_main_initial_answer",
        "semantic_main_initial_h1",
        "semantic_main_initial_bridge_status",
    ]
    assert all(assertion["passed"] is False for assertion in duplicate)


def test_skip_target_containment_requires_the_focused_target_inside_unique_main():
    from src.research_accessibility_browser_gate import (
        evaluate_skip_target_containment,
    )

    passed = evaluate_skip_target_containment(
        main_count=1,
        target_count=1,
        active_id="public-page-answer",
        target_inside_main=True,
    )
    outside = evaluate_skip_target_containment(
        main_count=1,
        target_count=1,
        active_id="public-page-answer",
        target_inside_main=False,
    )
    duplicate_main = evaluate_skip_target_containment(
        main_count=2,
        target_count=1,
        active_id="public-page-answer",
        target_inside_main=True,
    )

    assert passed["passed"] is True
    assert outside["passed"] is False
    assert duplicate_main["passed"] is False


def test_browser_error_contract_rejects_console_and_page_errors():
    from src.research_accessibility_browser_gate import evaluate_browser_errors

    assert evaluate_browser_errors([])["passed"] is True
    failed = evaluate_browser_errors(
        ["console error: bridge failed", "page error: unhandled exception"]
    )
    assert failed["passed"] is False
    assert "bridge failed" in str(failed["detail"])
    assert "unhandled exception" in str(failed["detail"])


def test_browser_measurement_collects_errors_and_rechecks_landmark_after_rerender():
    source = Path("src/research_accessibility_browser_gate.py").read_text(
        encoding="utf-8"
    )
    measurement = source[source.index("def _measure_route(") :]
    measurement = measurement[: measurement.index("\ndef _failed_payload(")]

    assert 'page.on("console"' in measurement
    assert 'page.on("pageerror"' in measurement
    assert '_semantic_main_assertions(page, phase="initial")' in measurement
    assert '_semantic_main_assertions(page, phase="rerender")' in measurement
    assert "_rerender_route(" in measurement


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
        {"x": 16, "y": 8, "width": 174, "height": 44},
        viewport_width=390,
        viewport_height=844,
    ) == {
        "passed": True,
        "detail": (
            "focused skip geometry x=16.0..190.0, y=8.0..52.0 "
            "within 390x844 viewport"
        ),
    }
    assert evaluate_skip_geometry(
        {"x": -320, "y": 8, "width": 174, "height": 44},
        viewport_width=390,
        viewport_height=844,
    )["passed"] is False
    assert evaluate_skip_geometry(
        {"x": 350, "y": 8, "width": 174, "height": 44},
        viewport_width=390,
        viewport_height=844,
    )["passed"] is False
    assert evaluate_skip_geometry(
        {"x": 16, "y": 8, "width": 0, "height": 44},
        viewport_width=390,
        viewport_height=844,
    )["passed"] is False
    assert evaluate_skip_geometry(
        {"x": 16, "y": -1, "width": 174, "height": 44},
        viewport_width=390,
        viewport_height=844,
    )["passed"] is False
    assert evaluate_skip_geometry(
        {"x": 16, "y": 820, "width": 174, "height": 44},
        viewport_width=390,
        viewport_height=844,
    )["passed"] is False


def test_explicit_base_url_accepts_only_loopback_root_urls():
    from src.research_accessibility_browser_gate import validated_loopback_base_url

    assert validated_loopback_base_url("http://127.0.0.1:8501") == (
        "http://127.0.0.1:8501"
    )
    assert validated_loopback_base_url("http://localhost:8501/") == (
        "http://localhost:8501"
    )
    assert validated_loopback_base_url("http://[::1]:8501") == (
        "http://[::1]:8501"
    )
    for invalid in (
        "https://example.com",
        "http://0.0.0.0:8501",
        "http://127.0.0.1:8501/unrelated",
        "http://127.0.0.1:8501?mode=research",
        "file:///tmp/dashboard.html",
    ):
        assert validated_loopback_base_url(invalid) is None


def test_gate_rejects_non_loopback_before_browser_discovery(tmp_path):
    from src.research_accessibility_browser_gate import (
        run_research_accessibility_browser_gate,
    )

    payload = run_research_accessibility_browser_gate(
        tmp_path,
        base_url="https://example.com",
        chrome_executable=tmp_path / "missing-chrome",
    )

    assert payload["verdict"] == "failed"
    assert payload["commit"] == ""
    assert payload["data_profile"] == "unverified"
    assert "loopback" in " ".join(payload["failures"]).lower()


def test_demo_identity_requires_product_title_brand_and_demo_profile():
    from src.research_accessibility_browser_gate import evaluate_demo_app_identity

    passed = evaluate_demo_app_identity(
        page_title="Stock Research Command Center",
        brand_text="Stock Research Command Center",
        profile_label="Demo",
        profile_caption="Data profile: demo",
    )
    wrong_profile = evaluate_demo_app_identity(
        page_title="Stock Research Command Center",
        brand_text="Stock Research Command Center",
        profile_label="Local Research",
        profile_caption="Data profile: local",
    )
    wrong_app = evaluate_demo_app_identity(
        page_title="Another dashboard",
        brand_text="Another dashboard",
        profile_label="Demo",
        profile_caption="Data profile: demo",
    )

    assert passed["passed"] is True
    assert wrong_profile["passed"] is False
    assert wrong_app["passed"] is False


def test_repository_hygiene_allows_only_unstaged_generated_churn():
    from scripts.diff_hygiene import StatusEntry
    from src.research_accessibility_browser_gate import evaluate_repository_hygiene

    generated = StatusEntry("M", "data/reports/ticker_readiness_report.csv")
    product = StatusEntry("M", "src/dashboard.py")

    clean_product = evaluate_repository_hygiene([generated], staged_entries=[])
    dirty_product = evaluate_repository_hygiene(
        [generated, product], staged_entries=[]
    )
    staged_generated = evaluate_repository_hygiene(
        [generated], staged_entries=[generated]
    )

    assert clean_product["passed"] is True
    assert clean_product["excluded_generated_paths"] == [
        "data/reports/ticker_readiness_report.csv"
    ]
    assert clean_product["dirty_product_paths"] == []
    assert dirty_product["passed"] is False
    assert dirty_product["dirty_product_paths"] == ["src/dashboard.py"]
    assert staged_generated["passed"] is False
    assert staged_generated["staged_paths"] == [
        "data/reports/ticker_readiness_report.csv"
    ]


def test_viewport_geometry_rejects_off_canvas_zero_size_and_short_route_links():
    from src.research_accessibility_browser_gate import evaluate_viewport_geometry

    viewport = (390, 844)
    assert evaluate_viewport_geometry(
        {"x": 8, "y": 120, "width": 120, "height": 44},
        viewport=viewport,
        expected_min_height=44,
        label="Discover",
    )["passed"] is True
    for rectangle in (
        {"x": -180, "y": 120, "width": 120, "height": 44},
        {"x": 400, "y": 120, "width": 120, "height": 44},
        {"x": 8, "y": 120, "width": 0, "height": 44},
        {"x": 8, "y": 120, "width": 120, "height": 0},
        {"x": 8, "y": 120, "width": 120, "height": 43},
    ):
        assert evaluate_viewport_geometry(
            rectangle,
            viewport=viewport,
            expected_min_height=44,
            label="Discover",
        )["passed"] is False


def test_skip_gate_uses_one_physical_tab_instead_of_dom_order_or_focus_substitution():
    source = Path("src/research_accessibility_browser_gate.py").read_text(
        encoding="utf-8"
    )

    assert 'page.keyboard.press("Tab")' in source
    assert "_visible_application_focus_order" not in source
    assert "skip_links.first.focus()" not in source
    assert "document.activeElement === element" in source


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
