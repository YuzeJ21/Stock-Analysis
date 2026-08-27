from __future__ import annotations

import json
import os
import subprocess
import textwrap
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    ("route", "final_selector"),
    (
        ("/?mode=research&page=company-workbench&ticker=AVGO&open=1", ".company-workbench-primary-brief"),
        ("/?mode=public&page=single-stock-report&ticker=AVGO&open=1", ".public-ticker-summary"),
    ),
)
def test_task4_production_report_cold_transition_is_neutral_then_resolved(
    tmp_path, monkeypatch, route, final_selector
):
    """Observe the real report route while a child-only report build is delayed once."""
    from playwright.sync_api import sync_playwright
    from src.research_accessibility_browser_gate import (
        _captured_local_demo_server,
        _repository_content_snapshot,
    )
    from src.workspace_visual_browser_gate import find_chrome_executable

    delay_dir = tmp_path / "delay"
    delay_dir.mkdir()
    (delay_dir / "sitecustomize.py").write_text(textwrap.dedent("""
        import time
        import src.stock_report as _stock_report
        _original = _stock_report.build_stock_report
        _used = False
        def build_stock_report(*args, **kwargs):
            global _used
            if not _used:
                _used = True
                time.sleep(1.0)
            return _original(*args, **kwargs)
        _stock_report.build_stock_report = build_stock_report
    """), encoding="utf-8")
    monkeypatch.setenv("PYTHONPATH", str(delay_dir) + os.pathsep + os.environ.get("PYTHONPATH", ""))
    root = Path(__file__).resolve().parents[1]
    repository_before = _repository_content_snapshot(root)
    original_failure = None
    try:
        with _captured_local_demo_server(root, timeout_seconds=30) as server:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(executable_path=find_chrome_executable(), headless=True)
                try:
                    page = browser.new_page(viewport={"width": 1280, "height": 720})
                    errors = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
                    page.add_init_script("""
              window.__cold = [];
              new MutationObserver(() => { const loader=document.querySelector('.single-stock-loading-state[role="status"][aria-live="polite"][aria-busy="true"]'); const final=document.querySelectorAll(%s); if (loader || final.length) window.__cold.push({kind:loader?'loader':'final', loader:!!loader, final:final.length, text:loader?.innerText||'', contained:!!loader?.closest('[data-sr-region="primary-answer"], .company-workbench-primary-brief')}); }).observe(document,{childList:true,subtree:true});
            """ % json.dumps(final_selector))
                    page.goto(server.base_url + route, wait_until="domcontentloaded")
                    page.wait_for_selector(final_selector, state="visible", timeout=30000)
                    observed = page.evaluate("() => window.__cold")
                    loader = [row for row in observed if row["loader"]]
                    assert observed and observed[0]["kind"] == "loader" and loader[0]["contained"]
                    assert all(row["final"] == 0 for row in loader)
                    assert "No data is being refreshed or changed" in loader[0]["text"]
                    assert "does not state that any analysis section is ready or blocked" in loader[0]["text"].lower()
                    assert page.locator(final_selector).count() == 1
                    resolved_text = page.locator(final_selector).inner_text()
                    resolved_url = page.url
                    assert "AVGO" in resolved_text
                    assert page.locator(".single-stock-loading-state, [aria-busy='true']").count() == 0
                    assert resolved_url == server.base_url + route and "ticker=AVGO" in resolved_url
                    page.wait_for_timeout(500)
                    assert page.locator(final_selector).count() == 1
                    assert page.locator(final_selector).inner_text() == resolved_text
                    assert page.locator(".single-stock-loading-state, [aria-busy='true']").count() == 0
                    assert page.url == resolved_url
                    assert not errors
                finally:
                    browser.close()
    except BaseException as exc:
        original_failure = exc
    finally:
        repository_after = _repository_content_snapshot(root)

    fingerprint_failure = None
    try:
        assert repository_after == repository_before
    except BaseException as exc:
        fingerprint_failure = exc
    if original_failure is not None and fingerprint_failure is not None:
        raise BaseExceptionGroup(
            "cold transition and repository fingerprint both failed",
            (original_failure, fingerprint_failure),
        )
    if original_failure is not None:
        raise original_failure.with_traceback(original_failure.__traceback__)
    if fingerprint_failure is not None:
        raise fingerprint_failure.with_traceback(fingerprint_failure.__traceback__)


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
    assert next(route for route in ROUTE_FIXTURES if route.slug == "monitor").route == (
        "/?mode=research&page=monitor&return_ticker=NVDA"
    )
    assert next(route for route in ROUTE_FIXTURES if route.slug == "single-stock-report").route == (
        "/?mode=public&page=single-stock-report&ticker=AVGO&open=1"
    )
    assert next(route for route in ROUTE_FIXTURES if route.slug == "personal-data-health").route == (
        "/?mode=research&page=data-health&ticker=AVGO&lane=peers&drawer=proof"
    )
    assert {
        route.slug: route.marker
        for route in ROUTE_FIXTURES
        if route.slug in {"public-proof-history", "personal-proof-history"}
    } == {
        "public-proof-history": "Newest reviewed evidence",
        "personal-proof-history": "Newest reviewed evidence",
    }


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


def test_company_workbench_document_contract_rejects_missing_semantics_or_wrong_layout():
    """Catches a rail, title, action, or responsive order drifting from the brief."""

    from src.workspace_visual_browser_gate import (
        evaluate_company_workbench_document_contract,
    )

    desktop = {
        "viewport_width": 1440,
        "zoom": 1,
        "phone_layout": False,
        "h1_count": 1,
        "display_title_count": 1,
        "display_title_text": "AVGO Company Brief",
        "navigation_count": 1,
        "navigation_labelled_count": 1,
        "brief_count": 1,
        "brief_visible_count": 1,
        "brief_labelled_count": 1,
        "aside_count": 1,
        "aside_visible_count": 1,
        "aside_labelled_count": 1,
        "evidence_lane_count": 5,
        "positive_tabindex_count": 0,
        "primary_action_count": 1,
        "primary_action_visible_count": 1,
        "primary_action_width": 180,
        "primary_action_height": 44,
        "module_gate_count": 1,
        "module_gate_visible_count": 1,
        "brief_box": {"left": 16, "right": 1030, "top": 220, "bottom": 620},
        "aside_box": {"left": 1060, "right": 1424, "top": 220, "bottom": 650},
        "module_gate_box": {"left": 16, "right": 1030, "top": 680, "bottom": 724},
        "brief_lane_boxes": (
            {"left": 16, "right": 260, "top": 300, "bottom": 460},
            {"left": 270, "right": 514, "top": 300, "bottom": 460},
            {"left": 524, "right": 768, "top": 300, "bottom": 460},
            {"left": 778, "right": 1030, "top": 300, "bottom": 460},
        ),
    }
    assert evaluate_company_workbench_document_contract(**desktop).passed

    phone = {
        **desktop,
        "viewport_width": 390,
        "phone_layout": True,
        "brief_box": {"left": 12, "right": 378, "top": 340, "bottom": 1040},
        "aside_box": {"left": 12, "right": 378, "top": 1060, "bottom": 1540},
        "module_gate_box": {"left": 12, "right": 378, "top": 1560, "bottom": 1604},
        "brief_lane_boxes": (
            {"left": 12, "right": 378, "top": 430, "bottom": 550},
            {"left": 12, "right": 378, "top": 560, "bottom": 680},
            {"left": 12, "right": 378, "top": 690, "bottom": 810},
            {"left": 12, "right": 378, "top": 820, "bottom": 980},
        ),
    }
    assert evaluate_company_workbench_document_contract(**phone).passed

    zoomed_desktop = {
        **phone,
        "viewport_width": 720,
        "zoom": 2,
        "phone_layout": False,
    }
    assert evaluate_company_workbench_document_contract(**zoomed_desktop).passed

    mutations = (
        {"evidence_lane_count": 4},
        {"display_title_count": 0},
        {"navigation_labelled_count": 0},
        {"brief_labelled_count": 0},
        {"aside_count": 0},
        {"aside_visible_count": 0},
        {"aside_labelled_count": 0},
        {"positive_tabindex_count": 1},
        {"primary_action_height": 43.9},
        {"module_gate_visible_count": 0},
        {"brief_box": {"left": 16, "right": 1200, "top": 220, "bottom": 620}},
    )
    for mutation in mutations:
        assert not evaluate_company_workbench_document_contract(
            **{**desktop, **mutation}
        ).passed

    wrong_reflow = {
        **zoomed_desktop,
        "aside_box": {"left": 12, "right": 708, "top": 900, "bottom": 1540},
    }
    assert not evaluate_company_workbench_document_contract(**wrong_reflow).passed

    overlapping_phone_lanes = {
        **phone,
        "brief_lane_boxes": (
            {"left": 12, "right": 378, "top": 430, "bottom": 550},
            {"left": 12, "right": 378, "top": 540, "bottom": 680},
            {"left": 12, "right": 378, "top": 690, "bottom": 810},
            {"left": 12, "right": 378, "top": 820, "bottom": 980},
        ),
    }
    assert not evaluate_company_workbench_document_contract(
        **overlapping_phone_lanes
    ).passed


def test_mobile_navigation_discoverability_requires_every_primary_link_inside_the_phone_view():
    from src.workspace_visual_browser_gate import evaluate_mobile_navigation_discoverability

    assert evaluate_mobile_navigation_discoverability(
        phone_media_matches=False,
        expected_total=5,
        total=0,
        visible=0,
        fully_visible=0,
        scroll_width=0,
        client_width=0,
    ).passed
    assert evaluate_mobile_navigation_discoverability(
        phone_media_matches=True,
        expected_total=5,
        total=5,
        visible=5,
        fully_visible=5,
        scroll_width=350,
        client_width=350,
    ).passed
    for mutation in (
        {"total": 4},
        {"visible": 4},
        {"fully_visible": 4},
        {"scroll_width": 351.1},
    ):
        values = {
            "phone_media_matches": True,
            "expected_total": 5,
            "total": 5,
            "visible": 5,
            "fully_visible": 5,
            "scroll_width": 350,
            "client_width": 350,
            **mutation,
        }
        assert not evaluate_mobile_navigation_discoverability(**values).passed


def test_proof_history_initial_tree_is_bounded_and_truthfully_summarized():
    from src.workspace_visual_browser_gate import evaluate_proof_history_initial_tree

    assert evaluate_proof_history_initial_tree(
        record_count=20,
        summary="Showing 20 of 1343 reviewed records in newest-first order.",
    ).passed
    assert evaluate_proof_history_initial_tree(
        record_count=5,
        summary="Showing 5 of 5 reviewed records in newest-first order.",
    ).passed
    assert not evaluate_proof_history_initial_tree(
        record_count=5,
        summary="Showing 5 of 1343 reviewed records in newest-first order.",
    ).passed
    assert not evaluate_proof_history_initial_tree(
        record_count=20,
        summary="Showing 20 of 5 reviewed records in newest-first order.",
    ).passed
    assert not evaluate_proof_history_initial_tree(
        record_count=1343,
        summary="Showing every record.",
    ).passed
    assert not evaluate_proof_history_initial_tree(
        record_count=20,
        summary="Showing 20 records.",
    ).passed


def test_browser_evaluation_wires_phone_navigation_and_proof_tree_contracts():
    from pathlib import Path

    source = Path("src/workspace_visual_browser_gate.py").read_text(encoding="utf-8")
    evaluation = source[source.index("def _evaluate_observation(") : source.index("def _chromium_zoom_preferences(")]

    assert "evaluate_mobile_navigation_discoverability(" in evaluation
    assert '"mobile_navigation_discoverability"' in evaluation
    assert "evaluate_proof_history_initial_tree(" in evaluation
    assert '"proof_history_initial_tree"' in evaluation


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
    assert ".public-app-nav a" in script
    assert ".research-workflow-routes .research-workflow-link" in script
    assert ".research-workflow-routes .research-workflow-disabled" in script
    assert "public_nav_link_fully_visible_count" in script
    assert "research_nav_link_fully_visible_count" in script
    assert "proof_timeline_record_count" in script
    assert "public-proof-timeline-summary" in script


def test_browser_observation_requires_a_labelled_semantic_workbench_aside():
    """Prevents a labelled generic section from masquerading as the required aside."""

    from src import workspace_visual_browser_gate as gate

    captured: list[str] = []

    class CapturingPage:
        def evaluate(self, script):
            captured.append(script)
            return {}

    assert gate._browser_observation(CapturingPage()) == {}
    script = captured[0]
    assert 'aside.company-workbench-evidence-status[aria-label]' in script
    assert 'querySelectorAll(\n+    ".company-workbench-evidence-status"\n+  )' not in script


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
        visible_region_counts=counts,
        visible_region_order=ordered,
        primary_action_focusable_count=1,
        legacy_pre_answer_action_count=0,
    ).passed
    assert not evaluate_personal_route_hierarchy(
        slug=slug,
        region_counts=counts,
        region_order=ordered,
        visible_region_counts=counts,
        visible_region_order=ordered,
        primary_action_focusable_count=0,
        legacy_pre_answer_action_count=0,
    ).passed
    assert not evaluate_personal_route_hierarchy(
        slug=slug,
        region_counts={**counts, "primary-answer": 2},
        region_order=ordered + ("primary-answer",),
        visible_region_counts=counts,
        visible_region_order=ordered,
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
        visible_region_counts=counts,
        visible_region_order=ordered,
        primary_action_focusable_count=1,
        legacy_pre_answer_action_count=0,
    ).passed
    assert not evaluate_personal_route_hierarchy(
        slug=slug,
        region_counts=counts,
        region_order=ordered,
        visible_region_counts=counts,
        visible_region_order=ordered,
        primary_action_focusable_count=1,
        legacy_pre_answer_action_count=1,
    ).passed
    assert not evaluate_personal_route_hierarchy(
        slug=slug,
        region_counts=counts,
        region_order=ordered,
        visible_region_counts={
            **counts,
            "primary-answer": 0,
            "stop-rule": 0,
        },
        visible_region_order=tuple(
            name for name in ordered if name not in {"primary-answer", "stop-rule"}
        ),
        primary_action_focusable_count=1,
        legacy_pre_answer_action_count=0,
    ).passed
    assert not evaluate_personal_route_hierarchy(
        slug=slug,
        region_counts=counts,
        region_order=ordered,
        visible_region_counts=counts,
        visible_region_order=(
            "workflow-nav",
            "context",
            "page-title",
            "primary-action",
            "primary-answer",
            "stop-rule",
            "supporting-evidence",
            "advanced-detail",
        ),
        primary_action_focusable_count=1,
        legacy_pre_answer_action_count=0,
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


def test_output_directory_must_resolve_under_tmp_and_be_empty():
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
        prepare_output_dir(Path("/") / "outside-tmp-contract")


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


def _valid_discover_evidence_access_layout() -> dict[str, object]:
    links = (
        {
            "label": "Open AMD Company Brief",
            "href": "?mode=research&page=company-workbench&ticker=AMD&open=1",
            "visible": True,
            "focusable": True,
            "left": 280,
            "right": 500,
            "width": 220,
            "height": 44,
            "top": 500,
            "clipped": False,
        },
        {
            "label": "Open AVGO Company Brief",
            "href": "?mode=research&page=company-workbench&ticker=AVGO&open=1",
            "visible": True,
            "focusable": True,
            "left": 510,
            "right": 730,
            "width": 220,
            "height": 44,
            "top": 500,
            "clipped": False,
        },
        {
            "label": "Open COHR Company Brief",
            "href": "?mode=research&page=company-workbench&ticker=COHR&open=1",
            "visible": True,
            "focusable": True,
            "left": 740,
            "right": 960,
            "width": 220,
            "height": 44,
            "top": 500,
            "clipped": False,
        },
        {
            "label": "Open NVDA Company Brief",
            "href": "?mode=research&page=company-workbench&ticker=NVDA&open=1",
            "visible": True,
            "focusable": True,
            "left": 970,
            "right": 1190,
            "width": 220,
            "height": 44,
            "top": 500,
            "clipped": False,
        },
    )
    return {
        "primary_answer_count": 1,
        "quick_links": links,
        "native_search_count": 1,
        "stop_rule_count": 1,
        "supporting_evidence_count": 1,
        "advanced_detail_count": 1,
        "dom_order": (
            "primary-answer",
            "quick-links",
            "native-search",
            "stop-rule",
            "supporting-evidence",
            "advanced-detail",
        ),
        "client_width": 1280,
        "location_path": "/",
        "location_search": "?mode=research&page=discover",
        "current_page_count": 1,
        "current_page_label": "Discover",
    }


def test_discover_evidence_access_layout_accepts_the_exact_secondary_link_contract():
    """Catches the Discover-only gate rejecting approved secondary evidence actions."""

    from src.workspace_visual_browser_gate import (
        evaluate_discover_evidence_access_layout,
    )

    assert evaluate_discover_evidence_access_layout(
        **_valid_discover_evidence_access_layout()
    ).passed


@pytest.mark.parametrize(
    "mutation",
    (
        {"primary_answer_count": 2},
        {"native_search_count": 0},
        {"stop_rule_count": 0},
        {"supporting_evidence_count": 0},
        {"advanced_detail_count": 0},
        {
            "dom_order": (
                "primary-answer",
                "native-search",
                "quick-links",
                "stop-rule",
                "supporting-evidence",
                "advanced-detail",
            )
        },
        {"location_search": "?mode=research&page=monitor"},
        {"current_page_count": 0},
        {"current_page_label": "Research Desk"},
    ),
)
def test_discover_evidence_access_layout_rejects_hierarchy_overflow_or_route_drift(mutation):
    from src.workspace_visual_browser_gate import (
        evaluate_discover_evidence_access_layout,
    )

    assert not evaluate_discover_evidence_access_layout(
        **{**_valid_discover_evidence_access_layout(), **mutation}
    ).passed


def test_discover_evidence_access_layout_rejects_link_regressions():
    from src.workspace_visual_browser_gate import (
        evaluate_discover_evidence_access_layout,
    )

    valid = _valid_discover_evidence_access_layout()
    links = tuple(dict(link) for link in valid["quick_links"])
    mutations = (
        {"quick_links": links[:3]},
        {"quick_links": (links[1], links[0], links[2], links[3])},
        {"quick_links": (links[0], links[1], links[2], dict(links[2]))},
        {
            "quick_links": (
                {**links[0], "href": "?mode=research&page=monitor&ticker=AMD&open=1"},
                *links[1:],
            )
        },
        {"quick_links": ({**links[0], "visible": False}, *links[1:])},
        {"quick_links": ({**links[0], "focusable": False}, *links[1:])},
        {"quick_links": ({**links[0], "width": 43}, *links[1:])},
        {"quick_links": ({**links[0], "height": 43}, *links[1:])},
        {"quick_links": ({**links[0], "left": -2}, *links[1:])},
        {"quick_links": ({**links[0], "clipped": True}, *links[1:])},
    )
    for mutation in mutations:
        assert not evaluate_discover_evidence_access_layout(
            **{**valid, **mutation}
        ).passed


def _valid_discover_focus_sequence() -> dict[str, object]:
    labels = (
        "",
        "Research Desk",
        "Discover",
        "Company Workbench",
        "Monitor",
        "Data Health",
        "Proof History",
        "Open AACI Company Brief",
        "Open ACIC Company Brief",
        "Open AMD Company Brief",
        "Open AVGO Company Brief",
        "Browse all saved companies",
        "Search saved companies",
        "Advanced: cohort readiness context",
    )
    return {
        "focused_roles": (
            "skip",
            "navigation",
            "navigation",
            "navigation",
            "navigation",
            "navigation",
            "navigation",
            "evidence-path",
            "evidence-path",
            "evidence-path",
            "evidence-path",
            "browse-navigation",
            "primary-action",
            "advanced-detail",
        ),
        "focused_labels": labels,
        "outline_widths": (3,) * len(labels),
        "positive_tabindex_count": 0,
    }


def test_discover_focus_sequence_requires_the_complete_evidence_search_order():
    from src.workspace_visual_browser_gate import evaluate_discover_focus_sequence

    valid = _valid_discover_focus_sequence()
    assert evaluate_discover_focus_sequence(**valid).passed
    for mutation in (
        {"focused_roles": valid["focused_roles"][1:]},
        {
            "focused_roles": (
                *valid["focused_roles"][:7],
                *reversed(valid["focused_roles"][7:11]),
                *valid["focused_roles"][11:],
            ),
            "focused_labels": (
                *valid["focused_labels"][:7],
                *reversed(valid["focused_labels"][7:11]),
                *valid["focused_labels"][11:],
            ),
        },
        {
            "focused_labels": (
                *valid["focused_labels"][:7],
                "Open ACIC Company Brief",
                "Open AACI Company Brief",
                *valid["focused_labels"][9:],
            )
        },
        {
            "focused_roles": (
                *valid["focused_roles"][:11],
                "primary-action",
                "browse-navigation",
                "advanced-detail",
            )
        },
        {"positive_tabindex_count": 1},
        {"outline_widths": (*valid["outline_widths"][:9], 2, *valid["outline_widths"][10:])},
    ):
        assert not evaluate_discover_focus_sequence(**{**valid, **mutation}).passed


@pytest.mark.parametrize(
    ("viewport_height", "primary_top", "evidence_top"),
    ((720, 230, 500), (844, 300, 780)),
)
def test_discover_initial_viewport_requires_answer_and_evidence_starts_on_screen(
    viewport_height, primary_top, evidence_top
):
    from src.workspace_visual_browser_gate import (
        evaluate_discover_initial_viewport_hierarchy,
    )

    valid = {
        "primary_answer_box": {"top": primary_top, "bottom": primary_top + 260},
        "quick_links": tuple(
            {**link, "top": evidence_top}
            for link in _valid_discover_evidence_access_layout()["quick_links"]
        ),
        "viewport_height": viewport_height,
    }
    assert evaluate_discover_initial_viewport_hierarchy(**valid).passed
    assert not evaluate_discover_initial_viewport_hierarchy(
        **{**valid, "primary_answer_box": {"top": -2, "bottom": 100}}
    ).passed
    assert not evaluate_discover_initial_viewport_hierarchy(
        **{
            **valid,
            "quick_links": ({**valid["quick_links"][0], "top": viewport_height + 2},),
        }
    ).passed
    assert not evaluate_discover_initial_viewport_hierarchy(
        **{**valid, "quick_links": valid["quick_links"][:3]}
    ).passed


@pytest.mark.parametrize("link_index", (1, 2, 3))
def test_discover_initial_viewport_rejects_any_later_evidence_link_below_fold(
    link_index,
):
    from src.workspace_visual_browser_gate import (
        evaluate_discover_initial_viewport_hierarchy,
    )

    quick_links = [
        {**link, "top": 500}
        for link in _valid_discover_evidence_access_layout()["quick_links"]
    ]
    quick_links[link_index] = {**quick_links[link_index], "top": 722}

    assert not evaluate_discover_initial_viewport_hierarchy(
        primary_answer_box={"top": 230, "bottom": 490},
        quick_links=tuple(quick_links),
        viewport_height=720,
    ).passed


def _evaluate_personal_observation_checks(
    slug: str,
    contract: dict[str, object] | None = None,
):
    from src import workspace_visual_browser_gate as gate

    route = gate.parse_routes(slug)[0]
    order = (
        "workflow-nav",
        "context",
        "page-title",
        "primary-answer",
        "primary-action",
        "stop-rule",
        "supporting-evidence",
        "advanced-detail",
    )
    counts = {name: 1 for name in order}
    observation = {
        "client_width": 1280,
        "client_height": 720,
        "document_scroll_width": 1280,
        "body_scroll_width": 1280,
        "main_scroll_width": 1280,
        "main_client_width": 1280,
        "inner_width": 1280,
        "inner_height": 720,
        "visual_viewport_width": 1280,
        "visual_viewport_height": 720,
        "screenshot_width": 1280,
        "screenshot_height": 720,
        "device_pixel_ratio": 1,
        "visual_viewport_scale": 1,
        "scroll_x": 0,
        "scroll_y": 0,
        "document_scroll_left": 0,
        "document_scroll_top": 0,
        "main_scroll_left": 0,
        "main_scroll_top": 0,
        "public_app_nav_scroll_left": 0,
        "research_workflow_nav_scroll_left": 0,
        "research_workflow_nav_scroll_top": 0,
        "regions": (
            {"name": "primary-answer", "left": 280, "right": 1220, "top": 230, "bottom": 490},
            {"name": "primary-action", "left": 280, "right": 1220, "top": 620, "bottom": 664},
            {"name": "stop-rule", "left": 280, "right": 1220, "top": 675, "bottom": 776},
        ),
        "region_counts": counts,
        "visible_region_counts": counts,
        "region_order": order,
        "visible_region_order": order,
        "primary_action_focusable_count": 1,
        "legacy_pre_answer_action_count": 0,
        "h1_count": 1,
        "h1_text": (route.expected_h1,),
        "public_nav_count": 0,
        "public_nav_visible_count": 0,
        "research_nav_count": 1,
        "research_nav_visible_count": 1,
        "operator_radio_count": 0,
        "operator_radio_visible_count": 0,
        "research_nav_link_count": 4,
        "research_nav_link_visible_count": 4,
        "research_nav_link_fully_visible_count": 4,
        "research_nav_scroll_width": 200,
        "research_nav_client_width": 200,
        "skip_count": 1,
        "skip_in_main_count": 1,
        "skip_in_sidebar_count": 0,
        "stop_rule_count": 1,
        "positive_tabindex_count": 0,
        "phone_media_matches": False,
        "app_state": "notRunning",
        "traceback_visible": False,
        "spinner_count": 0,
    }
    if contract is not None:
        observation["discover_evidence_access"] = dict(contract)
    focus = (
        _valid_discover_focus_sequence()
        if slug == "discover"
        else {
            "focused_roles": (
                "skip",
                "navigation",
                "navigation",
                "primary-action",
                "advanced-detail",
            ),
            "focused_labels": ("", "One", "Two", "Act", "Advanced"),
            "outline_widths": (3, 3, 3, 3, 3),
            "positive_tabindex_count": 0,
        }
    )
    return gate._evaluate_observation(
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
            "max_animation_duration_ms": 0,
            "max_transition_duration_ms": 0,
            "max_animation_iterations": 1,
            "smooth_scroll_count": 0,
        },
        forced_colors={
            "active": True,
            "focus_outline_style": "solid",
            "focus_outline_width": 3,
            "state_count": 1,
            "state_border_width": 1,
            "state_outline_width": 3,
        },
        focus_sequences={"normal": focus, "forced-colors": dict(focus)},
    )


def test_discover_replaces_named_fold_and_focus_checks_without_omitting_them():
    checks = _evaluate_personal_observation_checks(
        "discover",
        _valid_discover_evidence_access_layout(),
    )
    by_name = {str(check["name"]): check for check in checks}

    assert by_name["discover_evidence_access_layout"]["passed"] is True
    assert by_name["initial_viewport_hierarchy"]["passed"] is True
    assert by_name["natural_focus_sequence_normal"]["passed"] is True
    assert by_name["natural_focus_sequence_forced-colors"]["passed"] is True
    assert "discover" in by_name["initial_viewport_hierarchy"]["detail"].lower()
    assert "evidence-path" in by_name["natural_focus_sequence_normal"]["detail"]
    assert by_name["unique_shared_regions"]["passed"] is True
    assert by_name["personal_route_answer_hierarchy"]["passed"] is True
    assert by_name["single_navigation_authority"]["passed"] is True


@pytest.mark.parametrize("slug", ("research-desk", "company-workbench", "monitor"))
def test_other_personal_routes_retain_the_generic_named_fold_and_focus_checks(slug):
    checks = _evaluate_personal_observation_checks(slug)
    by_name = {str(check["name"]): check for check in checks}

    assert by_name["initial_viewport_hierarchy"]["passed"] is False
    assert "require_complete=True" in by_name["initial_viewport_hierarchy"]["detail"]
    assert by_name["natural_focus_sequence_normal"]["passed"] is True
    assert by_name["natural_focus_sequence_forced-colors"]["passed"] is True
    assert "evidence-path" not in by_name["natural_focus_sequence_normal"]["detail"]


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


def test_research_desk_uses_the_same_complete_answer_hierarchy_contract():
    from src.workspace_visual_browser_gate import evaluate_personal_route_hierarchy

    order = (
        "workflow-nav",
        "context",
        "page-title",
        "primary-answer",
        "primary-action",
        "stop-rule",
        "supporting-evidence",
        "advanced-detail",
    )
    counts = {name: 1 for name in order}

    assert evaluate_personal_route_hierarchy(
        slug="research-desk",
        region_counts=counts,
        region_order=order,
        visible_region_counts=counts,
        visible_region_order=order,
        primary_action_focusable_count=1,
        legacy_pre_answer_action_count=0,
    ).passed
    assert not evaluate_personal_route_hierarchy(
        slug="research-desk",
        region_counts={**counts, "primary-answer": 2},
        region_order=order + ("primary-answer",),
        visible_region_counts=counts,
        visible_region_order=order,
        primary_action_focusable_count=1,
        legacy_pre_answer_action_count=0,
    ).passed
    assert not evaluate_personal_route_hierarchy(
        slug="research-desk",
        region_counts=counts,
        region_order=order,
        visible_region_counts={**counts, "supporting-evidence": 0},
        visible_region_order=tuple(
            name for name in order if name != "supporting-evidence"
        ),
        primary_action_focusable_count=1,
        legacy_pre_answer_action_count=0,
    ).passed


def test_public_home_phone_geometry_requires_complete_stop_at_100_and_ordered_reflow_at_200():
    from src.workspace_visual_browser_gate import evaluate_public_home_geometry

    zoom_100 = {
        "viewport_width": 390,
        "viewport_height": 844,
        "zoom": 1,
        "phone_layout": True,
        "action_left": 12,
        "action_right": 378,
        "action_top": 520,
        "action_bottom": 620,
        "stop_top": 630,
        "stop_bottom": 830,
        "metrics_top": 840,
        "metrics_bottom": 1040,
        "metrics_left": 12,
        "metrics_right": 378,
    }
    assert evaluate_public_home_geometry(**zoom_100).passed
    assert not evaluate_public_home_geometry(
        **{**zoom_100, "stop_bottom": 850, "metrics_top": 860}
    ).passed

    zoom_200 = {
        "viewport_width": 195,
        "viewport_height": 422,
        "zoom": 2,
        "phone_layout": True,
        "action_left": 6,
        "action_right": 189,
        "action_top": 120,
        "action_bottom": 210,
        "stop_top": 220,
        "stop_bottom": 410,
        "metrics_top": 420,
        "metrics_bottom": 600,
        "metrics_left": 6,
        "metrics_right": 189,
    }
    assert evaluate_public_home_geometry(
        **{**zoom_200, "stop_bottom": 430, "metrics_top": 440}
    ).passed
    assert not evaluate_public_home_geometry(
        **{**zoom_200, "metrics_top": 200, "metrics_bottom": 410}
    ).passed


def test_runtime_capture_requires_an_idle_streamlit_app_and_no_visible_loading():
    from src.workspace_visual_browser_gate import evaluate_runtime_capture

    assert evaluate_runtime_capture(
        app_state="notRunning",
        traceback_visible=False,
        spinner_count=0,
        console_errors=(),
    ).passed
    for broken in (
        {"app_state": "running"},
        {"traceback_visible": True},
        {"spinner_count": 1},
        {"console_errors": ("pageerror: boom",)},
    ):
        assert not evaluate_runtime_capture(
            **{
                "app_state": "notRunning",
                "traceback_visible": False,
                "spinner_count": 0,
                "console_errors": (),
                **broken,
            }
        ).passed


def test_task4_resolved_report_state_requires_one_completed_brief_and_no_busy_loading_state():
    """Catches a stable Company Workbench retaining cold-report busy markup."""

    from src.workspace_visual_browser_gate import evaluate_resolved_report_state

    assert evaluate_resolved_report_state(
        company_brief_count=1,
        primary_answer_count=4,
        evidence_lane_count=5,
        busy_loading_count=0,
    ).passed
    baseline = {
        "company_brief_count": 1,
        "primary_answer_count": 4,
        "evidence_lane_count": 5,
        "busy_loading_count": 0,
    }
    for changed in (
        {"company_brief_count": 0},
        {"company_brief_count": 2},
        {"primary_answer_count": 3},
        {"evidence_lane_count": 4},
        {"busy_loading_count": 1},
    ):
        assert not evaluate_resolved_report_state(**{**baseline, **changed}).passed


def test_task4_advanced_evidence_rail_contrast_rejects_dark_text_on_the_desktop_nav_background():
    """Catches the evidence current-location cue becoming unreadable on the dark rail."""

    from src.workspace_visual_browser_gate import (
        evaluate_advanced_evidence_rail_contrast,
    )

    assert evaluate_advanced_evidence_rail_contrast(
        marker_count=1,
        label_color="rgb(203, 213, 225)",
        current_color="rgb(248, 250, 252)",
        navigation_background="rgb(11, 27, 43)",
    ).passed
    assert not evaluate_advanced_evidence_rail_contrast(
        marker_count=1,
        label_color="rgb(82, 97, 92)",
        current_color="rgb(15, 76, 58)",
        navigation_background="rgb(11, 27, 43)",
    ).passed


def test_task4_phone_advanced_evidence_cue_requires_its_own_row_without_overlapping_primary_navigation():
    """Catches the secondary location cue sharing a phone-grid cell with a primary route."""

    from src.workspace_visual_browser_gate import (
        evaluate_advanced_evidence_navigation_layout,
    )

    passing = evaluate_advanced_evidence_navigation_layout(
        phone_layout=True,
        marker_count=1,
        primary_link_count=4,
        marker_box={"left": 16, "right": 374, "top": 140, "bottom": 194},
        primary_link_boxes=(
            {"left": 16, "right": 103, "top": 78, "bottom": 128},
            {"left": 107, "right": 194, "top": 78, "bottom": 128},
            {"left": 198, "right": 285, "top": 78, "bottom": 128},
            {"left": 289, "right": 374, "top": 78, "bottom": 128},
        ),
        workspace_mode_box={"left": 16, "right": 374, "top": 206, "bottom": 294},
        routes_scroll_width=358,
        routes_client_width=358,
    )

    assert passing.passed
    assert not evaluate_advanced_evidence_navigation_layout(
        phone_layout=True,
        marker_count=1,
        primary_link_count=4,
        marker_box={"left": 16, "right": 103, "top": 112, "bottom": 194},
        primary_link_boxes=(
            {"left": 16, "right": 103, "top": 78, "bottom": 128},
            {"left": 107, "right": 194, "top": 78, "bottom": 128},
            {"left": 198, "right": 285, "top": 78, "bottom": 128},
            {"left": 289, "right": 374, "top": 78, "bottom": 128},
        ),
        workspace_mode_box={"left": 16, "right": 374, "top": 206, "bottom": 294},
        routes_scroll_width=358,
        routes_client_width=358,
    ).passed


def _run_fake_matrix_cell_with_requests(
    monkeypatch,
    tmp_path,
    *,
    request_urls=(),
    late_request_url=None,
    screenshot_error=None,
    close_error=None,
    lifecycle_events=None,
):
    import contextlib
    from types import SimpleNamespace

    import playwright.sync_api

    from src import workspace_visual_browser_gate as gate

    class FakeRequest:
        def __init__(self, url):
            self.url = url
            self.method = "GET"
            self.resource_type = "fetch"

    class FakePage:
        def __init__(self):
            self.handlers = {}
            self.navigation_count = 0

        def on(self, event, callback):
            self.handlers.setdefault(event, []).append(callback)

        def _emit_request(self, url):
            for callback in self.handlers.get("request", ()):
                callback(FakeRequest(url))

        def goto(self, url, **kwargs):
            self.navigation_count += 1
            self._emit_request(url)
            if self.navigation_count == 1:
                for request_url in request_urls:
                    self._emit_request(request_url)

        def wait_for_function(self, expression, **kwargs):
            return None

        def emulate_media(self, **kwargs):
            return None

        def screenshot(self, **kwargs):
            if screenshot_error is not None:
                if isinstance(screenshot_error, BaseException):
                    raise screenshot_error
                raise RuntimeError(screenshot_error)
            image = bytearray(b"\x89PNG\r\n\x1a\n" + (b"\x00" * 16))
            image[16:20] = (1280).to_bytes(4, "big")
            image[20:24] = (720).to_bytes(4, "big")
            return bytes(image)

    page = FakePage()

    class FakeBrowserContext:
        pages = [page]

        def close(self):
            if lifecycle_events is not None:
                lifecycle_events.append("close")
            if late_request_url is not None:
                page._emit_request(late_request_url)
            if close_error is not None:
                raise close_error

    class FakeChromium:
        def launch_persistent_context(self, **kwargs):
            return FakeBrowserContext()

    class FakePlaywright:
        chromium = FakeChromium()

    class FakePlaywrightManager:
        def __enter__(self):
            return FakePlaywright()

        def __exit__(self, exc_type, exc, traceback):
            return False

    @contextlib.contextmanager
    def fake_server(*args, **kwargs):
        yield SimpleNamespace(
            base_url="http://127.0.0.1:43123",
            snapshot=lambda: (),
        )

    monkeypatch.setattr(gate, "find_chrome_executable", lambda: "/bin/sh")
    monkeypatch.setattr(gate, "_captured_local_demo_server", fake_server)
    monkeypatch.setattr(
        playwright.sync_api,
        "sync_playwright",
        lambda: FakePlaywrightManager(),
    )
    monkeypatch.setattr(gate, "_wait_for_visible_text", lambda *args, **kwargs: None)
    monkeypatch.setattr(gate, "_wait_for_dom_stability", lambda *args, **kwargs: None)
    monkeypatch.setattr(gate, "_reset_initial_scroll", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        gate,
        "_browser_observation",
        lambda *args, **kwargs: {
            "app_state": "notRunning",
            "traceback_visible": False,
            "spinner_count": 0,
        },
    )
    monkeypatch.setattr(gate, "_skip_focus_observation", lambda *args, **kwargs: {})
    monkeypatch.setattr(gate, "_reduced_motion_observation", lambda *args, **kwargs: {})
    monkeypatch.setattr(gate, "_forced_colors_observation", lambda *args, **kwargs: {})
    monkeypatch.setattr(
        gate,
        "_runtime_observation",
        lambda *args, **kwargs: {
            "app_state": "notRunning",
            "traceback_visible": False,
            "spinner_count": 0,
        },
    )
    monkeypatch.setattr(
        gate,
        "_evaluate_observation",
        lambda *args, **kwargs: [
            {"name": "geometry", "passed": True, "detail": "fixture geometry"},
            {
                "name": "idle_runtime_without_errors",
                "passed": True,
                "detail": "fixture runtime",
            },
        ],
    )
    if lifecycle_events is not None:
        original_runtime_capture_payload = gate.runtime_capture_payload

        def observed_runtime_capture_payload(*args, **kwargs):
            lifecycle_events.append("serialize")
            return original_runtime_capture_payload(*args, **kwargs)

        monkeypatch.setattr(
            gate,
            "runtime_capture_payload",
            observed_runtime_capture_payload,
        )
    route = next(route for route in gate.ROUTE_FIXTURES if route.slug == "operator-overview")
    return gate._run_matrix_cell(
        root=tmp_path,
        route=route,
        viewport=(1280, 720),
        zoom=1,
        output_dir=tmp_path,
        timeout_seconds=5,
    )


def test_matrix_cell_suppresses_only_close_time_target_closed_after_evaluation(
    monkeypatch,
    tmp_path,
):
    from playwright.sync_api import Error as PlaywrightError

    TargetClosedError = type("TargetClosedError", (PlaywrightError,), {})
    lifecycle_events = []
    result = _run_fake_matrix_cell_with_requests(
        monkeypatch,
        tmp_path,
        close_error=TargetClosedError("already closed during context.close"),
        lifecycle_events=lifecycle_events,
    )

    assert result["passed"] is True
    assert "error" not in result
    assert lifecycle_events == ["close", "serialize"]


def test_matrix_cell_keeps_non_target_close_and_preclose_target_closed_fail_closed(
    monkeypatch,
    tmp_path,
):
    from playwright.sync_api import Error as PlaywrightError

    TargetClosedError = type("TargetClosedError", (PlaywrightError,), {})
    non_target = _run_fake_matrix_cell_with_requests(
        monkeypatch,
        tmp_path / "non-target",
        close_error=PlaywrightError("context close failed"),
    )
    during_screenshot = _run_fake_matrix_cell_with_requests(
        monkeypatch,
        tmp_path / "screenshot",
        screenshot_error=TargetClosedError("target closed during screenshot"),
    )

    assert non_target["passed"] is False
    assert "Error: context close failed" in non_target["error"]
    assert during_screenshot["passed"] is False
    assert "TargetClosedError: target closed during screenshot" in during_screenshot["error"]


def test_matrix_cell_fails_closed_for_external_http_requests_and_late_egress(
    monkeypatch,
    tmp_path,
):
    from src.workspace_visual_browser_gate import evaluate_http_network_capture

    assert evaluate_http_network_capture(
        {
            "http_request_count": 0,
            "external_http_request_count": 0,
            "external_origin_count": 0,
            "external_urls": [],
            "external_urls_truncated": 0,
        }
    ).passed

    external = _run_fake_matrix_cell_with_requests(
        monkeypatch,
        tmp_path,
        request_urls=(
            "https://data.streamlit.io/metrics.json",
            "https://webhooks.fivetran.com/webhooks/secret-id",
            "http://127.0.0.1.evil.test:43123/spoof",
            "http://[broken",
            "http://127.0.0.1:43124/other-server",
        ),
    )
    assert external["passed"] is False
    external_check = next(
        check for check in external["checks"] if check["name"] == "no_external_http_requests"
    )
    assert external_check["passed"] is False
    assert external["network"]["http_request_count"] == 8
    assert external["network"]["external_http_request_count"] == 5
    assert external["network"]["external_origin_count"] == 5
    assert len(external["network"]["external_urls"]) == 5
    assert any("data.streamlit.io" in url for url in external["network"]["external_urls"])
    assert any("webhooks.fivetran.com" in url for url in external["network"]["external_urls"])
    assert all("secret-id" not in url for url in external["network"]["external_urls"])

    bounded = _run_fake_matrix_cell_with_requests(
        monkeypatch,
        tmp_path,
        request_urls=tuple(
            f"https://external-{index}.example/secret/{index}" for index in range(20)
        )
        + ("https://external-0.example/another-secret",),
    )
    assert bounded["passed"] is False
    assert bounded["network"]["http_request_count"] == 24
    assert bounded["network"]["external_http_request_count"] == 21
    assert bounded["network"]["external_origin_count"] == 20
    assert len(bounded["network"]["external_urls"]) == 16
    assert bounded["network"]["external_urls_truncated"] == 4
    assert all("secret" not in url for url in bounded["network"]["external_urls"])

    exact_origin = _run_fake_matrix_cell_with_requests(
        monkeypatch,
        tmp_path,
        request_urls=("http://127.0.0.1:43123/static/app.js",),
    )
    assert exact_origin["passed"] is True
    assert any(
        check["name"] == "no_external_http_requests" and check["passed"] is True
        for check in exact_origin["checks"]
    )
    assert exact_origin["network"] == {
        "http_request_count": 4,
        "external_http_request_count": 0,
        "external_origin_count": 0,
        "external_urls": [],
        "external_urls_truncated": 0,
    }

    non_http = _run_fake_matrix_cell_with_requests(
        monkeypatch,
        tmp_path,
        request_urls=(
            "data:text/plain,ok",
            "blob:http://127.0.0.1:43123/id",
            "about:blank",
            "chrome-extension://fixture/page.html",
        ),
    )
    assert non_http["passed"] is True
    assert non_http["network"]["http_request_count"] == 3
    assert non_http["network"]["external_http_request_count"] == 0

    late = _run_fake_matrix_cell_with_requests(
        monkeypatch,
        tmp_path,
        late_request_url="https://data.streamlit.io/late.json",
    )
    assert late["passed"] is False
    assert late["network"]["external_http_request_count"] == 1
    assert any("data.streamlit.io" in url for url in late["network"]["external_urls"])

    failed = _run_fake_matrix_cell_with_requests(
        monkeypatch,
        tmp_path,
        request_urls=("https://data.streamlit.io/before-failure.json",),
        screenshot_error="fixture screenshot failure",
    )
    assert failed["passed"] is False
    assert failed["network"]["external_http_request_count"] == 1
    assert any(
        check["name"] == "no_external_http_requests" and check["passed"] is False
        for check in failed["checks"]
    )
    assert "data.streamlit.io" in failed["log"]
    assert "fixture screenshot failure" in failed["log"]


def test_structured_geometry_keeps_literal_regions_controls_and_scroll_widths():
    from src.workspace_visual_browser_gate import structured_geometry

    observation = {
        "client_width": 390,
        "client_height": 844,
        "document_scroll_width": 390,
        "body_scroll_width": 390,
        "main_scroll_width": 390,
        "main_client_width": 390,
        "regions": (
            {
                "name": "primary-answer",
                "left": 12,
                "right": 378,
                "top": 220,
                "bottom": 360,
                "width": 366,
                "height": 140,
            },
        ),
        "controls": (
            {
                "name": "primary-action",
                "left": 12,
                "right": 120,
                "top": 372,
                "bottom": 416,
                "width": 108,
                "height": 44,
            },
        ),
        "scroll_x": 0,
        "scroll_y": 0,
        "document_scroll_left": 0,
        "document_scroll_top": 0,
        "main_scroll_left": 0,
        "main_scroll_top": 0,
        "public_app_nav_scroll_left": 0,
        "research_workflow_nav_scroll_left": 0,
        "research_workflow_nav_scroll_top": 0,
        "visual_viewport_width": 390,
        "visual_viewport_height": 844,
        "screenshot_width": 390,
        "screenshot_height": 844,
    }

    assert structured_geometry(observation) == {
        "viewport": {
            "client_width": 390.0,
            "client_height": 844.0,
            "visual_width": 390.0,
            "visual_height": 844.0,
            "screenshot_width": 390.0,
            "screenshot_height": 844.0,
        },
        "scroll_widths": {
            "document": 390.0,
            "body": 390.0,
            "main": 390.0,
            "main_client": 390.0,
        },
        "scroll_origins": {
            "window": [0.0, 0.0],
            "document": [0.0, 0.0],
            "main": [0.0, 0.0],
            "public_workflow": [0.0],
            "personal_workflow": [0.0, 0.0],
        },
        "regions": [dict(observation["regions"][0])],
        "controls": [dict(observation["controls"][0])],
    }


def test_full_matrix_coverage_is_ordered_and_requires_all_ninety_cells():
    from src.workspace_visual_browser_gate import (
        ROUTE_FIXTURES,
        VIEWPORTS,
        ZOOMS,
        evaluate_full_matrix_coverage,
    )

    results = [
        {
            "route": route.slug,
            "viewport": f"{width}x{height}",
            "zoom": zoom,
            "passed": True,
        }
        for route in ROUTE_FIXTURES
        for width, height in VIEWPORTS
        for zoom in ZOOMS
    ]
    coverage = evaluate_full_matrix_coverage(results)
    assert coverage == {
        "full_matrix": True,
        "expected_cells": 90,
        "observed_cells": 90,
        "missing_cells": [],
        "unexpected_cells": [],
        "ordered": True,
    }
    assert not evaluate_full_matrix_coverage(results[:-1])["full_matrix"]
    assert not evaluate_full_matrix_coverage(list(reversed(results)))["full_matrix"]


def test_results_bind_the_worktree_snapshot_and_per_cell_runtime_geometry():
    from src.workspace_visual_browser_gate import run_workspace_visual_browser_gate

    output_dir = Path("/tmp") / "workspace-visual-browser-gate-test-attribution"
    if output_dir.exists():
        for child in output_dir.iterdir():
            child.unlink()
        output_dir.rmdir()

    def fake_cell(*, root, route, viewport, zoom, output_dir, timeout_seconds):
        del root, timeout_seconds
        screenshot = output_dir / f"{route.slug}-{viewport[0]}x{viewport[1]}-zoom-{zoom}.png"
        screenshot.write_bytes(b"png")
        return {
            "route": route.slug,
            "viewport": f"{viewport[0]}x{viewport[1]}",
            "zoom": zoom,
            "passed": True,
            "screenshot": screenshot.name,
            "checks": [],
            "geometry": {"regions": [], "controls": []},
            "runtime": {
                "app_state": "notRunning",
                "traceback_visible": False,
                "spinner_count": 0,
                "console_errors": [],
            },
            "log": "Browser console/page errors: none.",
        }

    payload = run_workspace_visual_browser_gate(
        Path("."),
        routes="research-desk",
        viewports="390x844",
        zooms="1",
        output_dir=output_dir,
        cell_runner=fake_cell,
    )

    assert payload["source_snapshot"]["scope"] == "bounded_worktree"
    assert payload["source_snapshot"]["commit"]
    assert isinstance(payload["source_snapshot"]["changes"], list)
    assert payload["coverage"]["expected_cells"] == 90
    assert payload["coverage"]["observed_cells"] == 1
    assert payload["coverage"]["full_matrix"] is False
    assert payload["results"][0]["geometry"] == {"regions": [], "controls": []}
    assert payload["results"][0]["runtime"]["app_state"] == "notRunning"
    assert "Browser console/page errors: none." in (
        output_dir / "browser.log"
    ).read_text(encoding="utf-8")

    for child in output_dir.iterdir():
        child.unlink()
    output_dir.rmdir()


def test_matrix_fails_closed_when_the_source_snapshot_changes_during_capture(monkeypatch):
    import src.workspace_visual_browser_gate as gate

    output_dir = Path("/tmp/workspace-visual-browser-gate-test-source-drift")
    if output_dir.exists():
        for child in output_dir.iterdir():
            child.unlink()
        output_dir.rmdir()
    before = {
        "scope": "bounded_worktree",
        "commit": "a" * 40,
        "state": "working_tree",
        "changes": [{"path": "README.md", "state": "M", "sha256": "1" * 64}],
    }
    after = {
        **before,
        "changes": [{"path": "README.md", "state": "M", "sha256": "2" * 64}],
    }
    snapshots = iter((before, after))
    monkeypatch.setattr(gate, "_source_snapshot", lambda root: next(snapshots))

    def fake_cell(*, root, route, viewport, zoom, output_dir, timeout_seconds):
        del root, output_dir, timeout_seconds
        return {
            "route": route.slug,
            "viewport": f"{viewport[0]}x{viewport[1]}",
            "zoom": zoom,
            "passed": True,
            "screenshot": "capture.png",
            "checks": [],
            "geometry": {"regions": [], "controls": []},
            "runtime": {
                "app_state": "notRunning",
                "traceback_visible": False,
                "spinner_count": 0,
                "console_errors": [],
            },
            "log": "Browser console/page errors: none.",
        }

    payload = gate.run_workspace_visual_browser_gate(
        Path("."),
        routes="research-desk",
        viewports="390x844",
        zooms="1",
        output_dir=output_dir,
        cell_runner=fake_cell,
    )

    assert payload["verdict"] == "failed"
    assert payload["source_snapshot"] == before
    assert payload["source_snapshot_after"] == after
    assert payload["source_snapshot_stable"] is False
    assert "source snapshot changed during matrix capture" in payload["failures"]

    for child in output_dir.iterdir():
        child.unlink()
    output_dir.rmdir()


def test_matrix_fails_closed_when_source_attribution_is_unknown(monkeypatch):
    import src.workspace_visual_browser_gate as gate

    output_dir = Path("/tmp/workspace-visual-browser-gate-test-source-unknown")
    if output_dir.exists():
        for child in output_dir.iterdir():
            child.unlink()
        output_dir.rmdir()
    unknown = {
        "scope": "bounded_worktree",
        "commit": "unknown",
        "state": "unknown",
        "changes": [],
    }
    monkeypatch.setattr(gate, "_source_snapshot", lambda root: unknown)

    def fake_cell(*, root, route, viewport, zoom, output_dir, timeout_seconds):
        del root, output_dir, timeout_seconds
        return {
            "route": route.slug,
            "viewport": f"{viewport[0]}x{viewport[1]}",
            "zoom": zoom,
            "passed": True,
            "screenshot": "capture.png",
            "checks": [],
            "geometry": {"regions": [], "controls": []},
            "runtime": {"console_errors": []},
            "log": "Browser console/page errors: none.",
        }

    payload = gate.run_workspace_visual_browser_gate(
        Path("."),
        routes="research-desk",
        viewports="390x844",
        zooms="1",
        output_dir=output_dir,
        cell_runner=fake_cell,
    )

    assert payload["verdict"] == "failed"
    assert payload["source_snapshot_valid"] is False
    assert "source snapshot unavailable for matrix attribution" in payload["failures"]

    for child in output_dir.iterdir():
        child.unlink()
    output_dir.rmdir()


def test_runner_exception_keeps_structured_failure_and_truthful_browser_log(monkeypatch):
    import src.workspace_visual_browser_gate as gate

    output_dir = Path("/tmp/workspace-visual-browser-gate-test-runner-error")
    if output_dir.exists():
        for child in output_dir.iterdir():
            child.unlink()
        output_dir.rmdir()
    snapshot = {
        "scope": "bounded_worktree",
        "commit": "a" * 40,
        "state": "exact_head",
        "changes": [],
    }
    monkeypatch.setattr(gate, "_source_snapshot", lambda root: snapshot)

    def raising_cell(**kwargs):
        del kwargs
        raise RuntimeError("diagnostic sentinel")

    payload = gate.run_workspace_visual_browser_gate(
        Path("."),
        routes="research-desk",
        viewports="390x844",
        zooms="1",
        output_dir=output_dir,
        cell_runner=raising_cell,
    )

    result = payload["results"][0]
    assert result["passed"] is False
    assert result["geometry"]["regions"] == []
    assert result["geometry"]["controls"] == []
    assert result["runtime"]["console_errors"] == []
    log = (output_dir / "browser.log").read_text(encoding="utf-8")
    assert "Cell execution failed: RuntimeError: diagnostic sentinel" in log
    assert "No server warnings or errors captured." not in log

    for child in output_dir.iterdir():
        child.unlink()
    output_dir.rmdir()


def test_failed_cell_with_empty_log_never_gets_a_success_diagnostic(monkeypatch):
    import src.workspace_visual_browser_gate as gate

    output_dir = Path("/tmp/workspace-visual-browser-gate-test-empty-failure-log")
    if output_dir.exists():
        for child in output_dir.iterdir():
            child.unlink()
        output_dir.rmdir()
    snapshot = {
        "scope": "bounded_worktree",
        "commit": "a" * 40,
        "state": "exact_head",
        "changes": [],
    }
    monkeypatch.setattr(gate, "_source_snapshot", lambda root: snapshot)

    def failed_cell(*, route, viewport, zoom, **kwargs):
        del kwargs
        return {
            "route": route.slug,
            "viewport": f"{viewport[0]}x{viewport[1]}",
            "zoom": zoom,
            "passed": False,
            "screenshot": "",
            "checks": [],
            "geometry": {"regions": [], "controls": []},
            "runtime": {"console_errors": []},
            "log": "",
        }

    gate.run_workspace_visual_browser_gate(
        Path("."),
        routes="research-desk",
        viewports="390x844",
        zooms="1",
        output_dir=output_dir,
        cell_runner=failed_cell,
    )

    log = (output_dir / "browser.log").read_text(encoding="utf-8")
    assert "Cell execution failed: failed cell did not provide diagnostics" in log
    assert "No server warnings or errors captured." not in log

    for child in output_dir.iterdir():
        child.unlink()
    output_dir.rmdir()


def test_personal_focus_sequence_allows_intervening_native_controls():
    from src.workspace_visual_browser_gate import evaluate_focus_sequence

    result = evaluate_focus_sequence(
        focused_roles=(
            "skip",
            "navigation",
            "navigation",
            "primary-action",
            "other",
            "advanced-detail",
        ),
        region_order=(
            "workflow-nav",
            "primary-answer",
            "primary-action",
            "stop-rule",
            "supporting-evidence",
            "advanced-detail",
        ),
        outline_widths=(3, 3, 3, 3, 3, 3),
        positive_tabindex_count=0,
    )

    assert result.passed
    assert not evaluate_focus_sequence(
        focused_roles=(
            "skip",
            "navigation",
            "other",
            "primary-action",
            "advanced-detail",
        ),
        region_order=(
            "workflow-nav",
            "primary-answer",
            "primary-action",
            "stop-rule",
            "supporting-evidence",
            "advanced-detail",
        ),
        outline_widths=(3, 3, 3, 3, 3),
        positive_tabindex_count=0,
    ).passed


def test_discover_saved_browser_jump_is_classified_as_in_page_navigation():
    from src.workspace_visual_browser_gate import evaluate_focus_sequence

    source = Path("src/workspace_visual_browser_gate.py").read_text(encoding="utf-8")

    assert "a[href='#saved-company-browser']" in source
    assert "role = \"navigation\"" in source
    assert not evaluate_focus_sequence(
        focused_roles=(
            "skip",
            "navigation",
            "primary-action-help",
            "primary-action",
            "advanced-detail",
        ),
        region_order=(
            "workflow-nav",
            "primary-answer",
            "primary-action",
            "stop-rule",
            "supporting-evidence",
            "advanced-detail",
        ),
        outline_widths=(3, 3, 3, 3, 3),
        positive_tabindex_count=0,
    ).passed
    assert not evaluate_focus_sequence(
        focused_roles=(
            "skip",
            "navigation",
            "primary-action",
            "navigation",
            "advanced-detail",
        ),
        region_order=(
            "workflow-nav",
            "primary-answer",
            "primary-action",
            "stop-rule",
            "supporting-evidence",
            "advanced-detail",
        ),
        outline_widths=(3, 3, 3, 3, 3),
        positive_tabindex_count=0,
    ).passed


def test_source_snapshot_state_matches_the_presence_of_worktree_changes():
    from src.workspace_visual_browser_gate import evaluate_source_snapshot

    commit = "a" * 40
    change = {"path": "README.md", "state": "M", "sha256": "1" * 64}
    assert evaluate_source_snapshot(
        {
            "scope": "bounded_worktree",
            "commit": commit,
            "state": "exact_head",
            "changes": [],
        }
    ).passed
    assert evaluate_source_snapshot(
        {
            "scope": "bounded_worktree",
            "commit": commit,
            "state": "working_tree",
            "changes": [change],
        }
    ).passed
    assert not evaluate_source_snapshot(
        {
            "scope": "bounded_worktree",
            "commit": commit,
            "state": "working_tree",
            "changes": [],
        }
    ).passed
    assert not evaluate_source_snapshot(
        {
            "scope": "bounded_worktree",
            "commit": commit,
            "state": "exact_head",
            "changes": [change],
        }
    ).passed


def test_focus_capture_covers_every_primary_personal_route_and_operator_controls():
    from src.workspace_visual_browser_gate import (
        PERSONAL_FOCUS_ROUTE_SLUGS,
        evaluate_control_target,
    )

    assert PERSONAL_FOCUS_ROUTE_SLUGS == {
        "research-desk",
        "discover",
        "company-workbench",
        "monitor",
    }
    source = Path("src/workspace_visual_browser_gate.py").read_text(encoding="utf-8")
    assert "[data-testid='stSidebar'] [role='radiogroup'] label" in source
    assert not evaluate_control_target(width=43, height=44).passed


def test_final_runtime_resample_overrides_initial_state_before_evaluation_and_result():
    from src.workspace_visual_browser_gate import (
        apply_final_runtime_observation,
        evaluate_runtime_capture,
        runtime_capture_payload,
    )

    initial = {
        "app_state": "notRunning",
        "traceback_visible": False,
        "spinner_count": 0,
        "regions": [{"name": "primary-answer", "left": 0, "right": 390}],
    }
    final = {
        "app_state": "running",
        "traceback_visible": True,
        "spinner_count": 2,
    }
    merged = apply_final_runtime_observation(initial, final)
    serialized = runtime_capture_payload(merged, ("console error: sentinel",))

    assert merged["regions"] == initial["regions"]
    assert serialized == {
        "app_state": "running",
        "traceback_visible": True,
        "spinner_count": 2,
        "console_errors": ["console error: sentinel"],
    }
    assert not evaluate_runtime_capture(
        app_state=serialized["app_state"],
        traceback_visible=serialized["traceback_visible"],
        spinner_count=serialized["spinner_count"],
        console_errors=tuple(serialized["console_errors"]),
    ).passed

    source = Path("src/workspace_visual_browser_gate.py").read_text(encoding="utf-8")
    runner = source[source.index("def _run_matrix_cell(") : source.index("def run_workspace_visual_browser_gate(")]
    final_focus = runner.index('focus_sequences["forced-colors"] = _focus_sequence_observation(page)')
    resample = runner.index("apply_final_runtime_observation(", final_focus)
    evaluation = runner.index("checks = _evaluate_observation(", resample)
    assert final_focus < resample < evaluation


def test_late_console_error_rebuilds_the_final_runtime_check_and_forces_failure():
    from src.workspace_visual_browser_gate import (
        finalize_runtime_check,
        runtime_capture_payload,
    )

    checks = [
        {"name": "geometry", "passed": True, "detail": "stable"},
        {
            "name": "idle_runtime_without_errors",
            "passed": True,
            "detail": "initial capture was idle",
        },
    ]
    observation = {
        "app_state": "notRunning",
        "traceback_visible": False,
        "spinner_count": 0,
    }
    console_errors: list[str] = []
    assert runtime_capture_payload(observation, tuple(console_errors))["console_errors"] == []
    console_errors.append("console error: late sentinel")
    final_runtime = runtime_capture_payload(observation, tuple(console_errors))
    finalized = finalize_runtime_check(checks, final_runtime)
    idle = next(
        check for check in finalized if check["name"] == "idle_runtime_without_errors"
    )

    assert final_runtime["console_errors"] == ["console error: late sentinel"]
    assert idle["passed"] is False
    assert "late sentinel" in idle["detail"]
    assert not all(bool(check["passed"]) for check in finalized)
