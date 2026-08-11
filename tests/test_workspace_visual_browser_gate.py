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
