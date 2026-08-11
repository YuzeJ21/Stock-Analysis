from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


def test_route_fixtures_cover_the_literal_workspace_matrix_in_declared_order():
    from src.workspace_visual_browser_gate import ROUTE_FIXTURES

    assert tuple(route.slug for route in ROUTE_FIXTURES) == (
        "research-desk",
        "discover",
        "company-workbench",
        "monitor",
        "public-home",
        "stock-selector",
        "single-stock-report",
        "public-data-health",
        "public-proof-history",
        "personal-data-health",
        "personal-proof-history",
        "operator-overview",
        "market-direction",
        "universe-manager",
        "monthly-picks",
    )
    assert next(route for route in ROUTE_FIXTURES if route.slug == "company-workbench").route == (
        "/?mode=research&page=company-workbench&ticker=AVGO"
    )
    assert next(route for route in ROUTE_FIXTURES if route.slug == "single-stock-report").route == (
        "/?mode=public&page=single-stock-report&ticker=AVGO&open=1"
    )


def test_default_viewports_are_the_literal_desktop_and_phone_contract():
    from src.workspace_visual_browser_gate import VIEWPORTS

    assert VIEWPORTS == ((1280, 720), (1440, 1024), (390, 844))


def test_pure_browser_evaluators_use_one_pixel_tolerance_and_44_pixel_targets():
    from src.workspace_visual_browser_gate import (
        evaluate_control_target,
        evaluate_horizontal_bounds,
        evaluate_skip_focus,
        evaluate_scroll_width,
        evaluate_text_clipping,
    )

    assert evaluate_horizontal_bounds(left=-1, right=390, client_width=390).passed
    assert evaluate_scroll_width(scroll_width=391, client_width=390).passed
    assert not evaluate_horizontal_bounds(left=-1.1, right=390, client_width=390).passed
    assert not evaluate_scroll_width(scroll_width=391.1, client_width=390).passed
    assert not evaluate_control_target(width=43, height=44).passed
    assert evaluate_control_target(width=44, height=44).passed
    assert not evaluate_text_clipping(
        overflow="hidden",
        text_overflow="ellipsis",
        line_clamp="1",
    ).passed
    assert evaluate_text_clipping(
        overflow="visible",
        text_overflow="clip",
        line_clamp="none",
    ).passed
    assert evaluate_skip_focus(
        skip_count=1,
        focused=True,
        route_preserved=True,
        fragment="public-page-answer",
        active_id="public-page-answer",
    ).passed
    assert not evaluate_skip_focus(
        skip_count=1,
        focused=False,
        route_preserved=True,
        fragment="",
        active_id="research-main",
    ).passed


@pytest.mark.parametrize(
    ("slug", "expected_h1", "expected_kind"),
    (
        ("operator-overview", "Overview", "operator"),
        ("market-direction", "Market Direction", "compatibility"),
        ("universe-manager", "Universe Manager", "operator"),
        ("monthly-picks", "Monthly Picks", "compatibility"),
    ),
)
def test_operator_route_contract_rejects_shell_chrome_target_and_sentiment_breaks(
    slug,
    expected_h1,
    expected_kind,
):
    from src.workspace_visual_browser_gate import evaluate_operator_route_contract

    valid = {
        "slug": slug,
        "expected_h1": expected_h1,
        "expected_kind": expected_kind,
        "h1_count": 1,
        "h1_text": (expected_h1,),
        "shell_count": 1,
        "warning_count": 1,
        "warning_kind": expected_kind,
        "warning_before_detail": True,
        "detail_count": 1,
        "stop_rule_count": 0,
        "topbar_nav_count": 0,
        "status_region_count": 1,
        "status_region_labelled": True,
        "profile_trust_count": 1,
        "profile_trust_display": "grid",
        "profile_trust_item_count": 5,
        "profile_trust_overlap_count": 0,
        "shortcut_count": 1,
        "shortcut_visible_count": 1,
        "shortcut_width": 44,
        "shortcut_height": 44,
        "non_neutral_analytic_count": 0,
    }
    assert evaluate_operator_route_contract(**valid).passed

    broken_cases = (
        {"h1_count": 0, "h1_text": ()},
        {"h1_count": 2, "h1_text": (expected_h1, expected_h1)},
        {"shell_count": 2},
        {"warning_count": 0},
        {"warning_kind": "operator" if expected_kind == "compatibility" else "compatibility"},
        {"warning_before_detail": False},
        {"detail_count": 0},
        {"stop_rule_count": 1},
        {"topbar_nav_count": 1},
        {"status_region_count": 0},
        {"status_region_labelled": False},
        {"profile_trust_count": 0},
        {"profile_trust_display": "block"},
        {"profile_trust_item_count": 4},
        {"profile_trust_overlap_count": 1},
        {"shortcut_count": 0, "shortcut_visible_count": 0},
        {"shortcut_width": 43},
        {"shortcut_height": 43},
        {"non_neutral_analytic_count": 1},
    )
    for broken in broken_cases:
        assert not evaluate_operator_route_contract(**{**valid, **broken}).passed


def test_browser_observation_collects_operator_semantics_and_shortcut_geometry():
    from src import workspace_visual_browser_gate as gate

    captured: list[str] = []

    class CapturingPage:
        def evaluate(self, script):
            captured.append(script)
            return {}

    assert gate._browser_observation(CapturingPage()) == {}
    script = captured[0]
    assert ".sr-operator-route-shell" in script
    assert ".sr-operator-warning" in script
    assert ".command-topbar[role='region'][aria-label]" in script
    assert "nav.command-topbar" in script
    assert ".command-top-link" in script
    assert ".profile-trust-strip.compact" in script
    assert "[data-sr-role='analytic']" in script
    assert "[data-sr-role='legacy']" in script


@pytest.mark.parametrize(
    "slug",
    ("operator-overview", "market-direction", "universe-manager", "monthly-picks"),
)
def test_operator_routes_run_the_strict_operator_contract_inside_browser_evaluation(slug):
    from src import workspace_visual_browser_gate as gate

    route = next(route for route in gate.ROUTE_FIXTURES if route.slug == slug)
    expected_kind = (
        "compatibility"
        if slug in {"market-direction", "monthly-picks"}
        else "operator"
    )
    observation = {
        "client_width": 1280,
        "client_height": 720,
        "document_scroll_width": 1280,
        "body_scroll_width": 1280,
        "main_scroll_width": 1280,
        "main_client_width": 1280,
        "regions": (),
        "region_counts": {},
        "text_nodes": (),
        "controls": (),
        "inner_width": 1280,
        "inner_height": 720,
        "device_pixel_ratio": 1,
        "visual_viewport_scale": 1,
        "visual_viewport_width": 1280,
        "visual_viewport_height": 720,
        "screenshot_width": 1280,
        "screenshot_height": 720,
        "scroll_x": 0,
        "scroll_y": 0,
        "document_scroll_left": 0,
        "document_scroll_top": 0,
        "main_scroll_left": 0,
        "main_scroll_top": 0,
        "public_app_nav_scroll_left": 0,
        "research_workflow_nav_scroll_left": 0,
        "research_workflow_nav_scroll_top": 0,
        "h1_count": 1,
        "h1_text": (route.expected_h1,),
        "public_nav_count": 0,
        "public_nav_visible_count": 0,
        "research_nav_count": 0,
        "research_nav_visible_count": 0,
        "operator_radio_count": 2,
        "operator_radio_visible_count": 2,
        "skip_count": 1,
        "skip_in_sidebar_count": 1,
        "skip_in_main_count": 0,
        "traceback_visible": False,
        "spinner_count": 0,
        "positive_tabindex_count": 0,
        "operator_shell_count": 1,
        "operator_warning_count": 1,
        "operator_warning_kind": expected_kind,
        "operator_warning_before_detail": True,
        "operator_detail_count": 1,
        "stop_rule_count": 0,
        "command_topbar_nav_count": 0,
        "command_status_region_count": 1,
        "command_status_region_labelled": True,
        "profile_trust_count": 1,
        "profile_trust_display": "grid",
        "profile_trust_item_count": 5,
        "profile_trust_overlap_count": 0,
        "command_top_link_count": 1,
        "command_top_link_visible_count": 1,
        "command_top_link_width": 44,
        "command_top_link_height": 44,
        "non_neutral_analytic_count": 0,
    }
    checks = gate._evaluate_observation(
        observation,
        route=route,
        viewport=(1280, 720),
        zoom=1,
        console_errors=(),
        skip_focus={
            "skip_count": 1,
            "focused": True,
            "route_preserved": True,
            "fragment": "public-page-answer",
            "active_id": "public-page-answer",
        },
        reduced_motion={
            "active": True,
            "target_count": 1,
            "max_animation_duration_ms": 0.01,
            "max_transition_duration_ms": 0.01,
            "max_animation_iterations": 1,
            "smooth_scroll_count": 0,
        },
        forced_colors={
            "active": True,
            "focus_outline_style": "solid",
            "focus_outline_width": 3,
            "state_count": 0,
            "state_border_width": 0,
            "state_outline_width": 0,
        },
        focus_sequences={},
    )

    strict = next(check for check in checks if check["name"] == "operator_route_contract")
    assert strict["passed"] is True

    observation["command_topbar_nav_count"] = 1
    checks = gate._evaluate_observation(
        observation,
        route=route,
        viewport=(1280, 720),
        zoom=1,
        console_errors=(),
        skip_focus={
            "skip_count": 1,
            "focused": True,
            "route_preserved": True,
            "fragment": "public-page-answer",
            "active_id": "public-page-answer",
        },
        reduced_motion={
            "active": True,
            "target_count": 1,
            "max_animation_duration_ms": 0.01,
            "max_transition_duration_ms": 0.01,
            "max_animation_iterations": 1,
            "smooth_scroll_count": 0,
        },
        forced_colors={
            "active": True,
            "focus_outline_style": "solid",
            "focus_outline_width": 3,
            "state_count": 0,
            "state_border_width": 0,
            "state_outline_width": 0,
        },
        focus_sequences={},
    )
    strict = next(check for check in checks if check["name"] == "operator_route_contract")
    assert strict["passed"] is False


def test_browser_zoom_evaluator_requires_real_layout_and_device_scale_change():
    from src.workspace_visual_browser_gate import evaluate_browser_zoom

    assert evaluate_browser_zoom(
        requested_zoom=1,
        declared_width=1280,
        declared_height=720,
        screenshot_width=1280,
        screenshot_height=720,
        inner_width=1280,
        inner_height=720,
        visual_viewport_width=1280,
        visual_viewport_height=720,
        device_pixel_ratio=1,
        visual_viewport_scale=1,
    ).passed
    assert not evaluate_browser_zoom(
        requested_zoom=1,
        declared_width=1280,
        declared_height=720,
        screenshot_width=1280,
        screenshot_height=633,
        inner_width=1280,
        inner_height=633,
        visual_viewport_width=1280,
        visual_viewport_height=633,
        device_pixel_ratio=1,
        visual_viewport_scale=1,
    ).passed
    assert evaluate_browser_zoom(
        requested_zoom=2,
        declared_width=1280,
        declared_height=720,
        screenshot_width=1280,
        screenshot_height=720,
        inner_width=640,
        inner_height=360,
        visual_viewport_width=640,
        visual_viewport_height=360,
        device_pixel_ratio=2,
        visual_viewport_scale=1,
    ).passed
    assert not evaluate_browser_zoom(
        requested_zoom=2,
        declared_width=1280,
        declared_height=720,
        screenshot_width=640,
        screenshot_height=316,
        inner_width=1280,
        inner_height=633,
        visual_viewport_width=1280,
        visual_viewport_height=633,
        device_pixel_ratio=1,
        visual_viewport_scale=1,
    ).passed


@pytest.mark.parametrize(
    ("mode", "counts"),
    (
        ("public", (1, 1, 0, 0, 0, 0)),
        ("research", (0, 0, 1, 1, 0, 0)),
        ("operator", (0, 0, 0, 0, 2, 2)),
    ),
)
def test_navigation_authority_evaluator_requires_exact_mutually_exclusive_counts(
    mode, counts
):
    from src.workspace_visual_browser_gate import evaluate_navigation_authority

    assert evaluate_navigation_authority(
        mode=mode,
        public_total=counts[0],
        public_visible=counts[1],
        research_total=counts[2],
        research_visible=counts[3],
        operator_radio_total=counts[4],
        operator_radio_visible=counts[5],
    ).passed
    assert not evaluate_navigation_authority(
        mode=mode,
        public_total=counts[0],
        public_visible=counts[1],
        research_total=counts[2] + 1,
        research_visible=counts[3],
        operator_radio_total=counts[4],
        operator_radio_visible=counts[5],
    ).passed


def test_media_style_evaluators_require_computed_affordances_not_only_active_media():
    from src.workspace_visual_browser_gate import (
        evaluate_forced_colors_styles,
        evaluate_reduced_motion_styles,
    )

    assert evaluate_forced_colors_styles(
        active=True,
        focus_outline_style="solid",
        focus_outline_width=3,
        state_count=1,
        state_border_width=2,
        state_outline_width=1,
    ).passed
    assert evaluate_forced_colors_styles(
        active=True,
        focus_outline_style="solid",
        focus_outline_width=3,
        state_count=0,
        state_border_width=0,
        state_outline_width=0,
    ).passed
    assert not evaluate_forced_colors_styles(
        active=True,
        focus_outline_style="solid",
        focus_outline_width=3,
        state_count=1,
        state_border_width=2,
        state_outline_width=0,
    ).passed
    assert not evaluate_forced_colors_styles(
        active=True,
        focus_outline_style="none",
        focus_outline_width=0,
        state_count=1,
        state_border_width=0,
        state_outline_width=0,
    ).passed
    assert evaluate_reduced_motion_styles(
        active=True,
        target_count=1,
        max_animation_duration_ms=0.01,
        max_transition_duration_ms=0.01,
        max_animation_iterations=1,
        smooth_scroll_count=0,
    ).passed
    assert not evaluate_reduced_motion_styles(
        active=True,
        target_count=1,
        max_animation_duration_ms=300,
        max_transition_duration_ms=300,
        max_animation_iterations=1,
        smooth_scroll_count=0,
    ).passed


def test_focus_sequence_evaluator_requires_natural_dom_and_physical_tab_order():
    from src.workspace_visual_browser_gate import evaluate_focus_sequence

    region_order = (
        "workflow-nav",
        "primary-answer",
        "primary-action",
        "stop-rule",
        "supporting-evidence",
        "advanced-detail",
    )
    assert evaluate_focus_sequence(
        focused_roles=("skip", "navigation", "navigation", "primary-action", "advanced-detail"),
        region_order=region_order,
        outline_widths=(3, 3, 3, 3, 3),
        positive_tabindex_count=0,
    ).passed
    assert not evaluate_focus_sequence(
        focused_roles=("skip", "primary-action", "navigation", "advanced-detail"),
        region_order=region_order,
        outline_widths=(3, 3, 3, 3),
        positive_tabindex_count=0,
    ).passed


@pytest.mark.parametrize("slug", ("discover", "company-workbench", "monitor"))
def test_personal_route_hierarchy_evaluator_requires_one_ordered_answer_contract(slug):
    from src.workspace_visual_browser_gate import evaluate_personal_route_hierarchy

    ordered = (
        "workflow-nav",
        "context",
        "page-title",
        "primary-answer",
        "primary-action",
        "stop-rule",
        "supporting-evidence",
        "advanced-detail",
    )
    counts = {name: ordered.count(name) for name in ordered}

    assert evaluate_personal_route_hierarchy(
        slug=slug,
        region_counts=counts,
        region_order=ordered,
        primary_action_focusable_count=1,
        legacy_pre_answer_action_count=0,
    ).passed
    assert not evaluate_personal_route_hierarchy(
        slug=slug,
        region_counts=counts,
        region_order=ordered,
        primary_action_focusable_count=0,
        legacy_pre_answer_action_count=0,
    ).passed
    assert not evaluate_personal_route_hierarchy(
        slug=slug,
        region_counts={**counts, "primary-answer": 2},
        region_order=ordered + ("primary-answer",),
        primary_action_focusable_count=1,
        legacy_pre_answer_action_count=0,
    ).passed
    assert not evaluate_personal_route_hierarchy(
        slug=slug,
        region_counts=counts,
        region_order=(
            "workflow-nav",
            "context",
            "page-title",
            "primary-answer",
            "supporting-evidence",
            "primary-action",
            "stop-rule",
            "advanced-detail",
        ),
        primary_action_focusable_count=1,
        legacy_pre_answer_action_count=0,
    ).passed
    assert not evaluate_personal_route_hierarchy(
        slug=slug,
        region_counts=counts,
        region_order=ordered,
        primary_action_focusable_count=1,
        legacy_pre_answer_action_count=1,
    ).passed


@pytest.mark.parametrize(
    ("raw", "parser_name"),
    (
        ("research-desk,research-desk", "parse_routes"),
        ("research-desk,not-a-route", "parse_routes"),
        ("1280x720,1280x720", "parse_viewports"),
        ("1280x720,800x600", "parse_viewports"),
        ("1,1", "parse_zooms"),
        ("1,1.5", "parse_zooms"),
        ("", "parse_routes"),
    ),
)
def test_cli_delimited_arguments_reject_unknown_empty_or_duplicate_values(raw, parser_name):
    from src import workspace_visual_browser_gate as gate

    with pytest.raises(ValueError):
        getattr(gate, parser_name)(raw)


def test_cli_delimited_arguments_preserve_declared_order():
    from src.workspace_visual_browser_gate import parse_routes, parse_viewports, parse_zooms

    assert tuple(route.slug for route in parse_routes("monitor,research-desk")) == (
        "monitor",
        "research-desk",
    )
    assert parse_viewports("390x844,1280x720") == ((390, 844), (1280, 720))
    assert parse_zooms("2,1") == (2, 1)


def test_output_directory_must_resolve_under_tmp_and_be_empty(tmp_path):
    from src.workspace_visual_browser_gate import prepare_output_dir

    output_dir = Path("/tmp") / "workspace-visual-browser-gate-test-empty"
    if output_dir.exists():
        output_dir.rmdir()
    assert prepare_output_dir(output_dir) == output_dir.resolve()
    assert output_dir.is_dir()
    (output_dir / "existing.txt").write_text("occupied", encoding="utf-8")
    with pytest.raises(ValueError):
        prepare_output_dir(output_dir)
    (output_dir / "existing.txt").unlink()
    output_dir.rmdir()

    with pytest.raises(ValueError):
        prepare_output_dir(tmp_path / "outside-tmp-contract")


def test_gate_builds_matrix_in_order_and_writes_only_declared_artifacts(tmp_path):
    from src.workspace_visual_browser_gate import run_workspace_visual_browser_gate

    output_dir = Path("/tmp") / "workspace-visual-browser-gate-test-matrix"
    if output_dir.exists():
        for child in output_dir.iterdir():
            child.unlink()
        output_dir.rmdir()
    calls: list[tuple[str, tuple[int, int], int]] = []

    def fake_cell(*, root, route, viewport, zoom, output_dir, timeout_seconds):
        del root, timeout_seconds
        calls.append((route.slug, viewport, zoom))
        screenshot = output_dir / f"{route.slug}-{viewport[0]}x{viewport[1]}-zoom-{zoom}.png"
        screenshot.write_bytes(b"png")
        return {
            "route": route.slug,
            "viewport": f"{viewport[0]}x{viewport[1]}",
            "zoom": zoom,
            "passed": True,
            "screenshot": screenshot.name,
            "checks": [],
        }

    payload = run_workspace_visual_browser_gate(
        Path("."),
        routes="monitor,research-desk",
        viewports="390x844,1280x720",
        zooms="2,1",
        output_dir=output_dir,
        cell_runner=fake_cell,
    )

    assert calls == [
        ("monitor", (390, 844), 2),
        ("monitor", (390, 844), 1),
        ("monitor", (1280, 720), 2),
        ("monitor", (1280, 720), 1),
        ("research-desk", (390, 844), 2),
        ("research-desk", (390, 844), 1),
        ("research-desk", (1280, 720), 2),
        ("research-desk", (1280, 720), 1),
    ]
    assert payload["verdict"] == "passed"
    assert json.loads((output_dir / "results.json").read_text(encoding="utf-8"))["verdict"] == "passed"
    assert (output_dir / "browser.log").is_file()
    assert {path.suffix for path in output_dir.iterdir()} <= {".png", ".json", ".log"}

    for child in output_dir.iterdir():
        child.unlink()
    output_dir.rmdir()


def test_make_target_requires_and_forwards_all_visual_gate_arguments():
    missing = subprocess.run(
        ["make", "--no-print-directory", "-n", "workspace-visual-browser-check"],
        cwd=Path("."),
        capture_output=True,
        text=True,
    )
    assert missing.returncode != 0
    assert "ROUTES is required" in (missing.stdout + missing.stderr)

    dry_run = subprocess.run(
        [
            "make",
            "--no-print-directory",
            "-n",
            "workspace-visual-browser-check",
            "ROUTES=research-desk",
            "VIEWPORTS=390x844",
            "ZOOMS=1,2",
            "OUTPUT_DIR=/tmp/workspace-visual-browser-gate-make",
        ],
        cwd=Path("."),
        capture_output=True,
        text=True,
        check=True,
    )
    command = dry_run.stdout
    assert "python3 -m src.workspace_visual_browser_gate" in command
    assert '--routes "research-desk"' in command
    assert '--viewports "390x844"' in command
    assert '--zooms "1,2"' in command
    assert '--output-dir "/tmp/workspace-visual-browser-gate-make"' in command


@pytest.mark.parametrize(
    "slug",
    (
        "public-home",
        "stock-selector",
        "single-stock-report",
        "public-data-health",
        "public-proof-history",
        "personal-data-health",
        "personal-proof-history",
    ),
)
def test_task4_route_hierarchy_rejects_duplicate_reordered_or_nonfocusable_regions(slug):
    from src.workspace_visual_browser_gate import evaluate_task4_route_hierarchy

    leading = (
        ("workflow-nav", "context")
        if slug.startswith("personal-")
        else ("context", "workflow-nav")
    )
    order = leading + (
        "page-title",
        "primary-answer",
        "primary-action",
        "stop-rule",
        "supporting-evidence",
        "advanced-detail",
    )
    counts = {name: 1 for name in order}

    assert evaluate_task4_route_hierarchy(
        slug=slug,
        region_counts=counts,
        region_order=order,
        visible_region_counts=counts,
        visible_region_order=order,
        primary_action_focusable_count=1,
        legacy_pre_answer_action_count=0,
    ).passed
    assert not evaluate_task4_route_hierarchy(
        slug=slug,
        region_counts={**counts, "stop-rule": 2},
        region_order=order + ("stop-rule",),
        visible_region_counts=counts,
        visible_region_order=order,
        primary_action_focusable_count=1,
        legacy_pre_answer_action_count=0,
    ).passed
    assert not evaluate_task4_route_hierarchy(
        slug=slug,
        region_counts=counts,
        region_order=leading + (
            "page-title",
            "primary-answer",
            "primary-action",
            "supporting-evidence",
            "stop-rule",
            "advanced-detail",
        ),
        visible_region_counts=counts,
        visible_region_order=order,
        primary_action_focusable_count=1,
        legacy_pre_answer_action_count=0,
    ).passed
    assert not evaluate_task4_route_hierarchy(
        slug=slug,
        region_counts=counts,
        region_order=order,
        visible_region_counts=counts,
        visible_region_order=order,
        primary_action_focusable_count=0,
        legacy_pre_answer_action_count=0,
    ).passed
    assert not evaluate_task4_route_hierarchy(
        slug=slug,
        region_counts=counts,
        region_order=order,
        visible_region_counts=counts,
        visible_region_order=order,
        primary_action_focusable_count=1,
        legacy_pre_answer_action_count=1,
    ).passed
    assert not evaluate_task4_route_hierarchy(
        slug=slug,
        region_counts=counts,
        region_order=order,
        visible_region_counts={**counts, "stop-rule": 0},
        visible_region_order=tuple(name for name in order if name != "stop-rule"),
        primary_action_focusable_count=1,
        legacy_pre_answer_action_count=0,
    ).passed


def test_browser_gate_resets_and_rejects_nonzero_initial_scroll_before_capture():
    from src.workspace_visual_browser_gate import evaluate_initial_scroll

    zero = {
        "window_scroll_x": 0,
        "window_scroll_y": 0,
        "document_scroll_left": 0,
        "document_scroll_top": 0,
        "main_scroll_left": 0,
        "main_scroll_top": 0,
        "public_app_nav_scroll_left": 0,
        "research_workflow_nav_scroll_left": 0,
        "research_workflow_nav_scroll_top": 0,
    }
    assert evaluate_initial_scroll(**zero).passed
    for carrier in zero:
        assert not evaluate_initial_scroll(**{**zero, carrier: 24}).passed

    source = Path("src/workspace_visual_browser_gate.py").read_text(encoding="utf-8")
    load_index = source.index("load_route()", source.index("def _run_matrix_cell("))
    reset_index = source.index("_reset_initial_scroll(page)", load_index)
    observation_index = source.index("observation = _browser_observation(page)", reset_index)
    screenshot_index = source.index("screenshot_bytes = page.screenshot(", observation_index)
    assert load_index < reset_index < observation_index < screenshot_index
    assert "scroll_x: window.scrollX" in source
    assert "scroll_y: window.scrollY" in source
    assert "document_scroll_left: document.scrollingElement" in source
    assert "document_scroll_top: document.scrollingElement" in source
    assert "main_scroll_left: main ? main.scrollLeft" in source
    assert "main_scroll_top: main ? main.scrollTop" in source
    assert "public_app_nav_scroll_left: publicAppNav ? publicAppNav.scrollLeft" in source
    assert "research_workflow_nav_scroll_left: researchWorkflowNav ? researchWorkflowNav.scrollLeft" in source
    assert "research_workflow_nav_scroll_top: researchWorkflowNav ? researchWorkflowNav.scrollTop" in source
    assert "document.scrollingElement.scrollTo" in source
    assert "main.scrollTo" in source
    assert "publicAppNav.scrollTo" in source
    assert "researchWorkflowNav.scrollTo" in source

    runner = source[source.index("def _run_matrix_cell(") : source.index("def run_workspace_visual_browser_gate(")]
    focus_index = runner.index('focus_sequences["normal"] = _focus_sequence_observation(page)')
    reload_index = runner.index("load_route()", focus_index)
    focus_reset_index = runner.index("_reset_initial_scroll(page)", reload_index)
    skip_index = runner.index("skip_focus = _skip_focus_observation(page)", focus_reset_index)
    assert focus_index < reload_index < focus_reset_index < skip_index


def test_initial_viewport_hierarchy_rejects_regions_above_or_below_the_viewport():
    from src.workspace_visual_browser_gate import evaluate_initial_viewport_hierarchy

    visible = {
        "primary-answer": {"top": 180, "bottom": 340},
        "primary-action": {"top": 360, "bottom": 404},
        "stop-rule": {"top": 420, "bottom": 480},
    }
    assert evaluate_initial_viewport_hierarchy(
        region_boxes=visible,
        viewport_height=844,
        require_complete=False,
    ).passed
    assert not evaluate_initial_viewport_hierarchy(
        region_boxes={**visible, "primary-answer": {"top": -24, "bottom": 140}},
        viewport_height=844,
        require_complete=False,
    ).passed
    assert not evaluate_initial_viewport_hierarchy(
        region_boxes={**visible, "stop-rule": {"top": 780, "bottom": 880}},
        viewport_height=844,
        require_complete=True,
    ).passed


@pytest.mark.parametrize(
    "slug",
    (
        "public-home",
        "stock-selector",
        "single-stock-report",
        "public-data-health",
        "public-proof-history",
        "personal-data-health",
        "personal-proof-history",
    ),
)
def test_task4_focus_sequence_requires_primary_action_order_and_visible_outline(slug):
    from src.workspace_visual_browser_gate import evaluate_task4_focus_sequence

    leading = (
        ("workflow-nav", "context")
        if slug.startswith("personal-")
        else ("context", "workflow-nav")
    )
    regions = leading + (
        "page-title",
        "primary-answer",
        "primary-action",
        "stop-rule",
        "supporting-evidence",
        "advanced-detail",
    )
    valid = {
        "slug": slug,
        "focused_roles": ("skip", "navigation", "navigation", "primary-action", "advanced-detail"),
        "region_order": regions,
        "outline_widths": (3, 3, 3, 3, 3),
        "positive_tabindex_count": 0,
    }
    assert evaluate_task4_focus_sequence(**valid).passed
    assert not evaluate_task4_focus_sequence(
        **{**valid, "positive_tabindex_count": 1}
    ).passed
    assert not evaluate_task4_focus_sequence(
        **{**valid, "focused_roles": ("skip", "primary-action", "navigation", "advanced-detail")}
    ).passed
    assert not evaluate_task4_focus_sequence(
        **{**valid, "outline_widths": (3, 3, 3, 0, 3)}
    ).passed


def test_public_home_geometry_requires_desktop_grid_and_phone_source_order():
    from src.workspace_visual_browser_gate import evaluate_public_home_geometry

    assert evaluate_public_home_geometry(
        viewport_width=1280,
        viewport_height=720,
        zoom=1,
        phone_layout=False,
        action_left=20,
        action_right=600,
        action_top=220,
        action_bottom=360,
        stop_top=480,
        stop_bottom=540,
        metrics_top=220,
        metrics_bottom=450,
        metrics_left=640,
        metrics_right=1260,
    ).passed
    assert not evaluate_public_home_geometry(
        viewport_width=1280,
        viewport_height=720,
        zoom=1,
        phone_layout=False,
        action_left=20,
        action_right=600,
        action_top=220,
        action_bottom=360,
        stop_top=220,
        stop_bottom=280,
        metrics_top=300,
        metrics_bottom=450,
        metrics_left=640,
        metrics_right=1260,
    ).passed


def test_public_home_geometry_observes_the_grid_area_not_the_inner_action_link():
    from src.workspace_visual_browser_gate import evaluate_public_home_geometry

    source = Path("src/workspace_visual_browser_gate.py").read_text(encoding="utf-8")

    assert 'const homeActionArea = document.querySelector(".public-home-primary")' in source
    assert "home_action_area: homeActionArea && visible(homeActionArea)" in source

    runner = source[
        source.index("if route.slug == \"public-home\":") :
        source.index("if route.slug == \"research-desk\":")
    ]
    assert 'observation.get("home_action_area")' in runner
    assert 'action_left=float(home_action_area.get("left") or 0)' in runner
    assert 'action_right=float(home_action_area.get("right") or 0)' in runner
    assert 'action_top=float(home_action_area.get("top") or 0)' in runner
    assert 'action_bottom=float(home_action_area.get("bottom") or 0)' in runner
    assert not evaluate_public_home_geometry(
        viewport_width=1280,
        viewport_height=720,
        zoom=1,
        phone_layout=False,
        action_left=20,
        action_right=760,
        action_top=220,
        action_bottom=360,
        stop_top=480,
        stop_bottom=540,
        metrics_left=640,
        metrics_right=1260,
        metrics_top=220,
        metrics_bottom=450,
    ).passed
    assert evaluate_public_home_geometry(
        viewport_width=390,
        viewport_height=844,
        zoom=1,
        phone_layout=True,
        action_left=12,
        action_right=378,
        action_top=220,
        action_bottom=360,
        stop_top=372,
        stop_bottom=430,
        metrics_top=442,
        metrics_bottom=700,
        metrics_left=12,
        metrics_right=378,
    ).passed
    assert evaluate_public_home_geometry(
        viewport_width=640,
        viewport_height=844,
        zoom=1,
        phone_layout=True,
        action_left=12,
        action_right=628,
        action_top=220,
        action_bottom=360,
        stop_top=372,
        stop_bottom=430,
        metrics_top=442,
        metrics_bottom=700,
        metrics_left=12,
        metrics_right=628,
    ).passed
    assert not evaluate_public_home_geometry(
        viewport_width=390,
        viewport_height=844,
        zoom=1,
        phone_layout=True,
        action_left=12,
        action_right=378,
        action_top=680,
        action_bottom=760,
        stop_top=780,
        stop_bottom=860,
        metrics_top=872,
        metrics_bottom=1100,
        metrics_left=12,
        metrics_right=378,
    ).passed
    assert not evaluate_public_home_geometry(
        viewport_width=390,
        viewport_height=844,
        zoom=1,
        phone_layout=True,
        action_left=12,
        action_right=378,
        action_top=220,
        action_bottom=360,
        stop_top=620,
        stop_bottom=680,
        metrics_top=372,
        metrics_bottom=600,
        metrics_left=12,
        metrics_right=378,
    ).passed


def test_browser_observation_recognizes_public_selector_native_search_as_primary_action():
    source = Path("src/workspace_visual_browser_gate.py").read_text(encoding="utf-8")

    assert 'node.innerText.includes("Search saved companies")' in source
    assert 'node.innerText.includes("Search this review queue")' in source
    assert 'element.matches("[data-testid=\'stTextInput\'] input")' in source
    assert "visible_region_counts" in source
    assert 'matchMedia("(max-width: 640px)").matches' in source
