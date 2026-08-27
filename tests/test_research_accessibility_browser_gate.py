from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import subprocess

import pytest


_ONE_PAGER_REQUIRED_STATE_ROLES = (
    "answers-next-research-task",
    "answers-still-withheld",
    "answers-use-now",
    "answers-what-changed",
    "break-case-decision-invalidation",
    "break-case-research-risks",
    "header-freshness-state",
    "header-rights-state",
    "operating-valuation-base-bridge-cash",
    "operating-valuation-base-bridge-debt",
    "operating-valuation-base-bridge-discounted-explicit-total",
    "operating-valuation-base-bridge-discounted-terminal-value",
    "operating-valuation-base-bridge-enterprise-value",
    "operating-valuation-base-bridge-equity-value",
    "operating-valuation-base-bridge-net-debt",
    "operating-valuation-base-bridge-supplied-shares",
    "operating-valuation-base-bridge-supplied-value-per-share",
    "operating-valuation-base-bridge-terminal-value",
    "operating-valuation-research-business-trend",
    "operating-valuation-research-key-drivers",
    "operating-valuation-research-valuation-regime",
    "provenance-freshness-state",
    "provenance-rights-state",
    "questions-answer-next-research-task",
    "questions-decision-review-trigger",
    "questions-research-evidence-gaps",
    "research-case-decision-evidence",
    "research-case-decision-plan",
    "research-case-research-business-trend",
    "research-case-research-key-drivers",
    "scenarios-base",
    "scenarios-base-value-per-share",
    "scenarios-bear",
    "scenarios-bear-value-per-share",
    "scenarios-bull",
    "scenarios-bull-value-per-share",
)

_ONE_PAGER_SHARE_BASIS_TOKENS = (
    "operating-valuation-base-bridge-share-basis=unverified",
    "scenarios-base-share-basis=unverified",
    "scenarios-bear-share-basis=unverified",
    "scenarios-bull-share-basis=unverified",
)


def _passing_one_pager_observation(
    *,
    width: int = 1280,
    height: int = 720,
    zoom: int = 1,
) -> dict[str, object]:
    state_tokens = tuple(
        sorted(
            [f"{role}=partial" for role in _ONE_PAGER_REQUIRED_STATE_ROLES]
            + ["provenance-row-1-saved-evidence-demo-source=partial"]
        )
    )
    return {
        "viewport": f"{width}x{height}",
        "requested_zoom": zoom,
        "actual_browser_zoom": True,
        "one_pager_absent_before_open": True,
        "html_brief_details_count": 1,
        "html_brief_details_open": True,
        "one_pager_count": 1,
        "one_pager_visible_count": 1,
        "one_pager_inside_html_brief": True,
        "one_pager_before_overview": True,
        "overview_count": 1,
        "advanced_evidence_count": 1,
        "advanced_evidence_after_one_pager": True,
        "advanced_evidence_visible": True,
        "document_overflow_px": 0.0,
        "one_pager_overflow_px": 0.0,
        "one_pager_max_descendant_overflow_px": 0.0,
        "one_pager_min_text_contrast_ratio": 7.0,
        "one_pager_min_boundary_contrast_ratio": 3.2,
        "one_pager_answer_item_count": 4,
        "one_pager_scenario_item_count": 3,
        "one_pager_state_tokens": state_tokens,
        "one_pager_state_node_count": len(state_tokens),
        "one_pager_state_role_count": len(state_tokens),
        "one_pager_unique_state_role_count": len(state_tokens),
        "one_pager_state_text_matches": True,
        "one_pager_share_basis_tokens": _ONE_PAGER_SHARE_BASIS_TOKENS,
        "one_pager_share_basis_visible_count": 4,
        "one_pager_share_basis_text_matches": True,
        "one_pager_provenance_caption_visible": True,
        "one_pager_provenance_visible": True,
        "one_pager_blockers_visible": True,
        "one_pager_assumptions_visible": True,
        "one_pager_handoff_visible": True,
        "download_button_count": 1,
        "download_button_label": "Download HTML Research Brief",
        "download_button_visible": True,
        "download_button_height": 44.0,
        "console_errors": (),
        "page_errors": (),
        "server_runtime_output_status": "captured_local_server",
        "server_deprecated_warning_count": 0,
        "active_origin": "http://127.0.0.1:43123",
        "request_urls": (
            "http://127.0.0.1:43123/?mode=research&page=company-workbench&ticker=NVDA&open=1",
        ),
        "external_request_count": 0,
        "request_audit_complete": True,
    }


def test_forced_colors_observation_fails_closed_for_each_required_signal():
    from src.research_accessibility_browser_gate import (
        evaluate_forced_colors_observation,
    )

    passing = {
        "media_active": True,
        "skip_count": 1,
        "skip_focused": True,
        "skip_outline_style": "solid",
        "skip_outline_width_px": 3.0,
        "current_route_count": 1,
        "current_route_value": "page",
        "current_route_visible": True,
        "current_route_border_width_px": 2.0,
        "current_route_outline_style": "solid",
        "current_route_outline_width_px": 1.0,
        "boundary_count": 1,
        "boundary_visible": True,
        "boundary_border_width_px": 1.0,
        "heading_visible": True,
        "boundary_text_visible": True,
        "route_marker_count": 1,
        "route_marker_visible": True,
        "route_next_action_count": 1,
        "route_next_action_visible": True,
        "overflow_px": 0.0,
        "traceback_visible": False,
    }
    assertions = evaluate_forced_colors_observation(passing, primary_route=True)
    assert assertions and all(item["passed"] for item in assertions)

    mutations = (
        ("forced_colors_media_active", {"media_active": False}),
        ("forced_colors_skip_focus", {"skip_focused": False}),
        ("forced_colors_focus_outline", {"skip_outline_width_px": 0.0}),
        ("forced_colors_current_route", {"current_route_value": ""}),
        ("forced_colors_current_route", {"current_route_visible": False}),
        ("forced_colors_current_route_marker", {"current_route_border_width_px": 1.0}),
        ("forced_colors_current_route_marker", {"current_route_outline_style": "none"}),
        ("forced_colors_current_route_marker", {"current_route_outline_width_px": 0.0}),
        ("forced_colors_boundary", {"boundary_visible": False}),
        ("forced_colors_boundary_border", {"boundary_border_width_px": 0.0}),
        ("forced_colors_required_text", {"heading_visible": False}),
        ("forced_colors_route_marker", {"route_marker_count": 0}),
        ("forced_colors_route_marker", {"route_marker_visible": False}),
        ("forced_colors_route_next_action", {"route_next_action_count": 2}),
        ("forced_colors_route_next_action", {"route_next_action_visible": False}),
        ("forced_colors_no_overflow", {"overflow_px": 2.0}),
        ("forced_colors_no_traceback", {"traceback_visible": True}),
    )
    for name, changed in mutations:
        failed = evaluate_forced_colors_observation(
            {**passing, **changed},
            primary_route=True,
        )
        assert next(item for item in failed if item["name"] == name)["passed"] is False

    secondary = evaluate_forced_colors_observation(
        {
            **passing,
            "current_route_count": 0,
            "current_route_value": "",
            "current_route_visible": False,
            "current_route_border_width_px": 0.0,
            "current_route_outline_style": "none",
            "current_route_outline_width_px": 0.0,
        },
        primary_route=False,
    )
    assert all(item["passed"] for item in secondary)


def test_forced_colors_active_route_marker_rejects_generic_one_pixel_border():
    from src.research_accessibility_browser_gate import (
        evaluate_forced_colors_observation,
    )

    observation = {
        "media_active": True,
        "skip_count": 1,
        "skip_focused": True,
        "skip_outline_style": "solid",
        "skip_outline_width_px": 3.0,
        "current_route_count": 1,
        "current_route_value": "page",
        "current_route_visible": True,
        "current_route_border_width_px": 1.0,
        "current_route_outline_style": "none",
        "current_route_outline_width_px": 0.0,
        "current_route_marker_width_px": 1.0,
        "boundary_count": 1,
        "boundary_visible": True,
        "boundary_border_width_px": 1.0,
        "heading_visible": True,
        "boundary_text_visible": True,
        "route_marker_count": 1,
        "route_marker_visible": True,
        "route_next_action_count": 1,
        "route_next_action_visible": True,
        "overflow_px": 0.0,
        "traceback_visible": False,
    }

    assertions = evaluate_forced_colors_observation(
        observation,
        primary_route=True,
    )

    marker = next(
        item
        for item in assertions
        if item["name"] == "forced_colors_current_route_marker"
    )
    assert marker["passed"] is False


def test_forced_colors_observation_fails_closed_on_missing_or_malformed_numbers():
    from src.research_accessibility_browser_gate import (
        evaluate_forced_colors_observation,
    )

    missing = evaluate_forced_colors_observation({}, primary_route=True)
    assert missing and all(item["passed"] is False for item in missing)

    numeric_mutations = (
        ("forced_colors_skip_focus", "skip_count"),
        ("forced_colors_focus_outline", "skip_outline_width_px"),
        ("forced_colors_current_route", "current_route_count"),
        ("forced_colors_current_route_marker", "current_route_border_width_px"),
        ("forced_colors_current_route_marker", "current_route_outline_width_px"),
        ("forced_colors_boundary", "boundary_count"),
        ("forced_colors_boundary_border", "boundary_border_width_px"),
        ("forced_colors_route_marker", "route_marker_count"),
        ("forced_colors_route_next_action", "route_next_action_count"),
        ("forced_colors_no_overflow", "overflow_px"),
    )
    for assertion_name, field_name in numeric_mutations:
        failed = evaluate_forced_colors_observation(
            {field_name: "not-a-number"},
            primary_route=True,
        )
        assertion = next(
            item for item in failed if item["name"] == assertion_name
        )
        assert assertion["passed"] is False
        assert "not-a-number" in assertion["detail"]


def test_reduced_motion_observation_fails_closed_for_each_required_signal():
    from src.research_accessibility_browser_gate import (
        evaluate_reduced_motion_observation,
    )

    passing = {
        "media_active": True,
        "target_count": 3,
        "max_animation_duration_ms": 0.01,
        "max_transition_duration_ms": 0.01,
        "max_animation_iterations": 1.0,
        "scroll_behavior": "auto",
        "heading_visible": True,
        "boundary_visible": True,
        "route_marker_count": 1,
        "route_marker_visible": True,
        "route_next_action_count": 1,
        "route_next_action_visible": True,
        "overflow_px": 0.0,
        "traceback_visible": False,
    }
    assertions = evaluate_reduced_motion_observation(passing)
    assert assertions and all(item["passed"] for item in assertions)

    mutations = (
        ("reduced_motion_media_active", {"media_active": False}),
        ("reduced_motion_targets", {"target_count": 0}),
        ("reduced_motion_animation_duration", {"max_animation_duration_ms": 250.0}),
        ("reduced_motion_transition_duration", {"max_transition_duration_ms": 250.0}),
        ("reduced_motion_animation_iterations", {"max_animation_iterations": 2.0}),
        ("reduced_motion_scroll_behavior", {"scroll_behavior": "smooth"}),
        ("reduced_motion_required_text", {"boundary_visible": False}),
        ("reduced_motion_route_marker", {"route_marker_count": 0}),
        ("reduced_motion_route_marker", {"route_marker_visible": False}),
        ("reduced_motion_route_next_action", {"route_next_action_count": 2}),
        ("reduced_motion_route_next_action", {"route_next_action_visible": False}),
        ("reduced_motion_no_overflow", {"overflow_px": 2.0}),
        ("reduced_motion_no_traceback", {"traceback_visible": True}),
    )
    for name, changed in mutations:
        failed = evaluate_reduced_motion_observation({**passing, **changed})
        assert next(item for item in failed if item["name"] == name)["passed"] is False


def test_reduced_motion_observation_fails_closed_on_missing_or_malformed_numbers():
    from src.research_accessibility_browser_gate import (
        evaluate_reduced_motion_observation,
    )

    missing = evaluate_reduced_motion_observation({})
    assert missing and all(item["passed"] is False for item in missing)

    numeric_mutations = (
        ("reduced_motion_targets", "target_count"),
        ("reduced_motion_animation_duration", "max_animation_duration_ms"),
        ("reduced_motion_transition_duration", "max_transition_duration_ms"),
        ("reduced_motion_animation_iterations", "max_animation_iterations"),
        ("reduced_motion_route_marker", "route_marker_count"),
        ("reduced_motion_route_next_action", "route_next_action_count"),
        ("reduced_motion_no_overflow", "overflow_px"),
    )
    for assertion_name, field_name in numeric_mutations:
        failed = evaluate_reduced_motion_observation(
            {field_name: "not-a-number"}
        )
        assertion = next(
            item for item in failed if item["name"] == assertion_name
        )
        assert assertion["passed"] is False
        assert "not-a-number" in assertion["detail"]


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
        (
            route.route,
            route.marker,
            route.expected_h1,
            route.requires_primary_navigation,
        )
        for route in RESEARCH_ROUTES
    ] == [
        (
            "/?mode=research&page=research-desk",
            "What needs my attention today?",
            "Research Desk",
            True,
        ),
        (
            "/?mode=research&page=discover",
            "Find a Company",
            "Discover",
            True,
        ),
        (
            "/?mode=research&page=company-workbench&ticker=NVDA&open=1",
            "Company Brief",
            "Company Workbench",
            True,
        ),
        (
            "/?mode=research&page=monitor",
            "Follow-up Queue",
            "Monitor",
            True,
        ),
        (
            "/?mode=research&page=data-health&ticker=NVDA",
            "Use now for market setup",
            "Data Health",
            True,
        ),
        (
            "/?mode=research&page=proof-history&ticker=NVDA",
            "Newest reviewed evidence",
            "Proof History",
            True,
        ),
    ]
    assert [route.evidence_route for route in RESEARCH_ROUTES] == [
        False,
        False,
        False,
        False,
        True,
        True,
    ]
    assert RESEARCH_ROUTES[0].media_marker_selector == (
        '.research-desk-brief[aria-label="Today\'s Research Brief"]'
    )
    assert RESEARCH_ROUTES[0].media_next_action_selector == (
        ".research-desk-brief .public-primary-action"
    )
    assert [
        route.media_next_action_selector for route in RESEARCH_ROUTES
    ] == [
        ".research-desk-brief .public-primary-action",
        "[data-testid='stTextInput'] input[aria-label='Search saved companies']",
        ".company-workbench-primary-brief .public-primary-action",
        "[data-sr-region='primary-action']",
        "[data-sr-region='primary-action']",
        "[data-sr-region='primary-action']",
    ]


def test_task4_discover_evidence_access_requires_live_counts_alphabetical_briefs_and_filter_order():
    """Catches Discover moving evidence access below filters or back to a ranking-like list."""

    from src.research_accessibility_browser_gate import (
        evaluate_discover_evidence_access,
    )

    passing = evaluate_discover_evidence_access(
        primary_answer=(
            "8 saved companies are available for evidence review; "
            "0 currently pass the strict screen."
        ),
        quick_links=(
            ("Open AMD Company Brief", "?mode=research&page=company-workbench&ticker=AMD&open=1"),
            ("Open AVGO Company Brief", "?mode=research&page=company-workbench&ticker=AVGO&open=1"),
            ("Open COHR Company Brief", "?mode=research&page=company-workbench&ticker=COHR&open=1"),
            ("Open NVDA Company Brief", "?mode=research&page=company-workbench&ticker=NVDA&open=1"),
        ),
        primary_before_quick_links=True,
        quick_links_before_advanced_filters=True,
    )

    assert passing["passed"] is True
    assert "four alphabetical Company Brief" in str(passing["detail"])

    baseline = {
        "primary_answer": (
            "8 saved companies are available for evidence review; "
            "0 currently pass the strict screen."
        ),
        "quick_links": (
            ("Open AMD Company Brief", "?mode=research&page=company-workbench&ticker=AMD&open=1"),
            ("Open AVGO Company Brief", "?mode=research&page=company-workbench&ticker=AVGO&open=1"),
            ("Open COHR Company Brief", "?mode=research&page=company-workbench&ticker=COHR&open=1"),
            ("Open NVDA Company Brief", "?mode=research&page=company-workbench&ticker=NVDA&open=1"),
        ),
        "primary_before_quick_links": True,
        "quick_links_before_advanced_filters": True,
    }
    for changed in (
        {"primary_answer": "8 saved companies are available for evidence review."},
        {
            "primary_answer": (
                "8 saved companies are available for evidence review; "
                "1 currently pass the strict screen."
            )
        },
        {"quick_links": passing["quick_links"][:3]},
        {
            "quick_links": (
                passing["quick_links"][1],
                passing["quick_links"][0],
                *passing["quick_links"][2:],
            )
        },
        {"primary_before_quick_links": False},
        {"quick_links_before_advanced_filters": False},
    ):
        result = evaluate_discover_evidence_access(**{**baseline, **changed})
        assert result["passed"] is False


def test_task4_monitor_return_context_requires_one_return_without_changing_monitor_counts():
    """Catches return context filtering Monitor or rendering a duplicated return action."""

    from src.research_accessibility_browser_gate import (
        evaluate_monitor_return_context,
    )

    passing = evaluate_monitor_return_context(
        baseline_counts={"cards": 5, "rows": 2, "advanced_identities": 5},
        context_counts={"cards": 5, "rows": 2, "advanced_identities": 5},
        return_action_count=1,
        return_action_label="Return to NVDA Company Workbench",
        return_action_href=(
            "?mode=research&page=company-workbench&ticker=NVDA&open=1"
        ),
        clarification=(
            "Monitor remains focused-cohort-wide; NVDA is only the return destination "
            "and does not filter these follow-up items."
        ),
    )

    assert passing["passed"] is True
    assert "unchanged" in str(passing["detail"])

    baseline = {
        "baseline_counts": {"cards": 5, "rows": 2, "advanced_identities": 5},
        "context_counts": {"cards": 5, "rows": 2, "advanced_identities": 5},
        "return_action_count": 1,
        "return_action_label": "Return to NVDA Company Workbench",
        "return_action_href": (
            "?mode=research&page=company-workbench&ticker=NVDA&open=1"
        ),
        "clarification": (
            "Monitor remains focused-cohort-wide; NVDA is only the return destination "
            "and does not filter these follow-up items."
        ),
    }
    for changed in (
        {"context_counts": {"cards": 4, "rows": 2, "advanced_identities": 5}},
        {"return_action_count": 2},
        {"return_action_label": "Return to Company Workbench"},
        {"return_action_href": "?mode=research&page=monitor&ticker=NVDA"},
        {"clarification": "NVDA filters this Monitor."},
    ):
        result = evaluate_monitor_return_context(**{**baseline, **changed})
        assert result["passed"] is False


def test_task4_advanced_evidence_location_requires_one_truthful_secondary_current_marker():
    """Catches an evidence page losing or duplicating its sole current-location cue."""

    from src.research_accessibility_browser_gate import (
        evaluate_evidence_navigation_location,
    )

    for label in ("Data Health", "Proof History"):
        assert evaluate_evidence_navigation_location(
            navigation_count=1,
            core_current_count=0,
            secondary_current_count=1,
            secondary_current_text=f"Advanced Evidence · {label}",
            expected_label=label,
            phase="initial",
        )["passed"] is True

    assert evaluate_evidence_navigation_location(
        navigation_count=1,
        core_current_count=0,
        secondary_current_count=2,
        secondary_current_text="Advanced Evidence · Data Health",
        expected_label="Data Health",
        phase="initial",
    )["passed"] is False


def test_company_workbench_primary_brief_contract_fails_closed_per_requirement():
    from src.research_accessibility_browser_gate import (
        evaluate_company_workbench_primary_brief,
    )

    passing = {
        "brief_count": 1,
        "brief_visible": True,
        "display_title": "NVDA Company Brief",
        "answer_labels": (
            "Use now",
            "Still withheld",
            "What changed",
            "Next research task",
        ),
        "answer_texts": (
            "Saved evidence can be reviewed.",
            "Consensus remains withheld.",
            "No queued change.",
            "Review source gaps.",
        ),
        "stop_count": 1,
        "stop_visible": True,
        "stop_text": (
            "Research-only: this brief is not a recommendation, probability, "
            "transaction instruction, or unsupported current-market conclusion."
        ),
        "data_health_action_count": 1,
        "data_health_action_visible": True,
        "data_health_action_height": 44.0,
        "data_health_action_href": (
            "?mode=research&page=data-health&ticker=NVDA"
        ),
        "open_modules_count": 1,
        "open_modules_visible": True,
        "open_modules_height": 44.0,
        "secondary_module_count": 0,
    }

    assert evaluate_company_workbench_primary_brief(passing)["passed"] is True

    rendered_uppercase = {
        **passing,
        "answer_labels": tuple(
            label.upper() for label in passing["answer_labels"]
        ),
    }
    assert (
        evaluate_company_workbench_primary_brief(rendered_uppercase)["passed"]
        is True
    )

    mutations = (
        {"brief_count": 2},
        {"brief_visible": False},
        {"display_title": ""},
        {"display_title": "NVDA"},
        {"display_title": "AVGO Company Brief"},
        {"display_title": "NVDA COMPANY BRIEF"},
        {"answer_labels": ("Use now", "Still withheld")},
        {"answer_texts": ("Saved evidence can be reviewed.", "", "No queued change.", "Review source gaps.")},
        {"stop_count": 0},
        {"stop_text": "Research-only."},
        {"data_health_action_count": 0},
        {"data_health_action_height": 43.9},
        {"data_health_action_href": "?mode=research&page=data-health&ticker=AVGO"},
        {"open_modules_count": 0},
        {"open_modules_visible": False},
        {"open_modules_height": 43.9},
        {"secondary_module_count": 1},
    )
    for mutation in mutations:
        result = evaluate_company_workbench_primary_brief(
            {**passing, **mutation}
        )
        assert result["passed"] is False
        assert result["detail"]


def test_company_workbench_primary_answer_text_accepts_one_direct_paragraph_or_strong_only():
    from src.research_accessibility_browser_gate import (
        _company_workbench_primary_answer_text,
    )

    class FakeBodyLocator:
        def __init__(self, texts):
            self._texts = tuple(texts)

        def count(self):
            return len(self._texts)

        @property
        def first(self):
            return self

        def inner_text(self):
            return self._texts[0]

    class FakeAnswer:
        def __init__(self, texts):
            self._texts = texts

        def locator(self, selector):
            assert selector == ":scope > p, :scope > strong"
            return FakeBodyLocator(self._texts)

    assert (
        _company_workbench_primary_answer_text(
            FakeAnswer(("  Saved evidence can be reviewed.  ",))
        )
        == "Saved evidence can be reviewed."
    )
    assert _company_workbench_primary_answer_text(FakeAnswer(())) == ""
    assert (
        _company_workbench_primary_answer_text(
            FakeAnswer(("first body", "ambiguous second body"))
        )
        == ""
    )


def test_company_workbench_display_title_collector_requires_one_semantic_h2():
    from src.research_accessibility_browser_gate import (
        _company_workbench_display_title,
    )

    selector = ".company-workbench-primary-heading h2"
    observed_selectors: list[str] = []

    class FakeTitleLocator:
        def __init__(self, texts):
            self._texts = tuple(texts)

        def count(self):
            return len(self._texts)

        @property
        def first(self):
            return self

        def inner_text(self):
            return self._texts[0]

    class FakePrimary:
        def __init__(self, texts):
            self._texts = tuple(texts)

        def locator(self, requested_selector):
            observed_selectors.append(requested_selector)
            return FakeTitleLocator(self._texts)

    assert (
        _company_workbench_display_title(
            FakePrimary(("  NVDA Company Brief  ",)), brief_count=1
        )
        == "NVDA Company Brief"
    )
    assert observed_selectors == [selector]
    assert _company_workbench_display_title(FakePrimary(()), brief_count=1) == ""
    assert (
        _company_workbench_display_title(
            FakePrimary(("NVDA Company Brief", "duplicate")), brief_count=1
        )
        == ""
    )
    assert (
        _company_workbench_display_title(
            FakePrimary(("NVDA Company Brief",)), brief_count=2
        )
        == ""
    )


def test_company_workbench_module_open_browser_check_supports_pointer_and_keyboard_activation():
    from src import research_accessibility_browser_gate as browser_gate

    source = browser_gate.Path(browser_gate.__file__).read_text(encoding="utf-8")
    helper_start = source.index("def _open_company_workbench_modules(")
    helper_end = source.index("\n\ndef ", helper_start + 1)
    helper = source[helper_start:helper_end]

    assert "button.first.click()" in helper
    assert 'button.first.press("Enter")' in helper
    assert "activation_attempts" in helper


def test_one_pager_collector_contract_accepts_substantive_observation():
    from src.research_accessibility_browser_gate import (
        evaluate_company_workbench_one_pager_observation,
    )

    assertions = evaluate_company_workbench_one_pager_observation(
        _passing_one_pager_observation()
    )

    assert assertions
    assert all(assertion["passed"] for assertion in assertions)


def test_one_pager_collector_contract_rejects_missing_duplicate_hidden_order_and_full_report():
    from src.research_accessibility_browser_gate import (
        evaluate_company_workbench_one_pager_observation,
    )

    mutations = (
        ("one_pager_unique_visible", {"one_pager_count": 0}),
        ("one_pager_unique_visible", {"one_pager_count": 2}),
        ("one_pager_unique_visible", {"one_pager_visible_count": 0}),
        ("one_pager_unique_visible", {"one_pager_inside_html_brief": False}),
        ("one_pager_order", {"one_pager_before_overview": False}),
        ("one_pager_order", {"overview_count": 0}),
        ("one_pager_full_report", {"advanced_evidence_count": 0}),
        ("one_pager_full_report", {"advanced_evidence_after_one_pager": False}),
        ("one_pager_full_report", {"advanced_evidence_visible": False}),
    )
    for assertion_name, mutation in mutations:
        assertions = evaluate_company_workbench_one_pager_observation(
            {**_passing_one_pager_observation(), **mutation}
        )
        assert next(
            assertion
            for assertion in assertions
            if assertion["name"] == assertion_name
        )["passed"] is False


def test_one_pager_collector_contract_rejects_zoom_overflow_state_share_target_runtime_and_requests():
    from src.research_accessibility_browser_gate import (
        evaluate_company_workbench_one_pager_observation,
    )

    passing = _passing_one_pager_observation()
    state_tokens = tuple(passing["one_pager_state_tokens"])
    mutations = (
        ("one_pager_module_gate", {"one_pager_absent_before_open": False}),
        ("one_pager_disclosure", {"html_brief_details_count": 2}),
        ("one_pager_disclosure", {"html_brief_details_open": False}),
        ("one_pager_zoom", {"actual_browser_zoom": False}),
        ("one_pager_no_overflow", {"document_overflow_px": 2.0}),
        ("one_pager_no_overflow", {"one_pager_overflow_px": 2.0}),
        (
            "one_pager_no_overflow",
            {"one_pager_max_descendant_overflow_px": 2.0},
        ),
        ("one_pager_contrast", {"one_pager_min_text_contrast_ratio": 4.49}),
        (
            "one_pager_contrast",
            {"one_pager_min_boundary_contrast_ratio": 2.99},
        ),
        ("one_pager_lists", {"one_pager_answer_item_count": 3}),
        ("one_pager_lists", {"one_pager_scenario_item_count": 2}),
        (
            "one_pager_state_roles",
            {
                "one_pager_state_tokens": state_tokens[1:],
                "one_pager_state_node_count": len(state_tokens) - 1,
                "one_pager_state_role_count": len(state_tokens) - 1,
                "one_pager_unique_state_role_count": len(state_tokens) - 1,
            },
        ),
        (
            "one_pager_state_roles",
            {
                "one_pager_state_tokens": state_tokens + (state_tokens[0],),
                "one_pager_state_node_count": len(state_tokens) + 1,
                "one_pager_state_role_count": len(state_tokens) + 1,
            },
        ),
        ("one_pager_state_roles", {"one_pager_state_text_matches": False}),
        (
            "one_pager_share_basis",
            {
                "one_pager_share_basis_tokens": _ONE_PAGER_SHARE_BASIS_TOKENS[:-1],
                "one_pager_share_basis_visible_count": 3,
            },
        ),
        (
            "one_pager_share_basis",
            {"one_pager_share_basis_text_matches": False},
        ),
        (
            "one_pager_content_visible",
            {"one_pager_provenance_caption_visible": False},
        ),
        ("one_pager_content_visible", {"one_pager_blockers_visible": False}),
        ("one_pager_content_visible", {"one_pager_assumptions_visible": False}),
        ("one_pager_content_visible", {"one_pager_handoff_visible": False}),
        ("one_pager_download_target", {"download_button_count": 0}),
        (
            "one_pager_download_target",
            {"download_button_label": "Download report"},
        ),
        ("one_pager_download_target", {"download_button_height": 43.9}),
        ("one_pager_runtime", {"console_errors": ("console error",)}),
        ("one_pager_runtime", {"page_errors": ("page error",)}),
        (
            "one_pager_runtime",
            {"server_runtime_output_status": "unverified"},
        ),
        ("one_pager_runtime", {"server_deprecated_warning_count": 1}),
        (
            "one_pager_exact_origin_network",
            {
                "request_urls": ("https://example.com/escaped",),
                "external_request_count": 1,
            },
        ),
        (
            "one_pager_exact_origin_network",
            {"request_audit_complete": False},
        ),
    )
    for assertion_name, mutation in mutations:
        assertions = evaluate_company_workbench_one_pager_observation(
            {**passing, **mutation}
        )
        assert next(
            assertion
            for assertion in assertions
            if assertion["name"] == assertion_name
        )["passed"] is False


def _passing_one_pager_payload_results() -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for width, height, zoom in (
        (1280, 720, 1),
        (1280, 720, 2),
        (390, 844, 1),
    ):
        results.append(
            {
                "viewport": f"{width}x{height}",
                "zoom": zoom,
                "passed": True,
                "assertions": (
                    {
                        "name": "one_pager_unique_visible",
                        "passed": True,
                        "detail": "one visible summary",
                    },
                ),
                "observation": _passing_one_pager_observation(
                    width=width,
                    height=height,
                    zoom=zoom,
                ),
            }
        )
    return results


def test_one_pager_payload_contract_accepts_exact_three_cell_slice():
    from src.research_accessibility_browser_gate import (
        COMPANY_WORKBENCH_ONE_PAGER_CELLS,
        evaluate_company_workbench_one_pager_payload,
    )

    assert COMPANY_WORKBENCH_ONE_PAGER_CELLS == (
        (1280, 720, 1),
        (1280, 720, 2),
        (390, 844, 1),
    )
    evaluated = evaluate_company_workbench_one_pager_payload(
        _passing_one_pager_payload_results()
    )

    assert evaluated["passed"] is True
    assert evaluated["detail"]


def test_one_pager_payload_contract_rejects_missing_duplicate_zoom_overflow_request_or_assertion():
    from src.research_accessibility_browser_gate import (
        evaluate_company_workbench_one_pager_payload,
    )

    mutations = []
    missing = _passing_one_pager_payload_results()
    missing.pop()
    mutations.append(missing)
    duplicate = _passing_one_pager_payload_results()
    duplicate.append(deepcopy(duplicate[0]))
    mutations.append(duplicate)
    false_zoom = _passing_one_pager_payload_results()
    false_zoom[1]["observation"]["actual_browser_zoom"] = False
    mutations.append(false_zoom)
    overflow = _passing_one_pager_payload_results()
    overflow[2]["observation"]["one_pager_max_descendant_overflow_px"] = 2.0
    mutations.append(overflow)
    external_request = _passing_one_pager_payload_results()
    external_request[0]["observation"].update(
        {
            "request_urls": ("http://example.com/escaped",),
            "external_request_count": 1,
        }
    )
    mutations.append(external_request)
    failed_assertion = _passing_one_pager_payload_results()
    failed_assertion[0]["assertions"][0]["passed"] = False
    mutations.append(failed_assertion)

    for results in mutations:
        evaluated = evaluate_company_workbench_one_pager_payload(results)
        assert evaluated["passed"] is False
        assert evaluated["detail"]


def test_actual_company_workbench_one_pager_in_app_contract():
    import src.research_accessibility_browser_gate as gate
    from playwright.sync_api import sync_playwright

    repository_root = Path.cwd()
    repository_before = gate._repository_content_snapshot(repository_root)
    chrome = gate.find_chrome_executable()
    assert chrome is not None
    with gate._captured_local_demo_server(
        repository_root,
        timeout_seconds=45,
    ) as server:
        with sync_playwright() as playwright:
            result = gate._measure_company_workbench_one_pager_cell(
                playwright.chromium,
                chrome_executable=Path(chrome),
                base_url=server.base_url,
                cell=(1280, 720, 1),
                timeout_seconds=45,
                server_deprecated_warning_count=(
                    server.deprecated_warning_count
                ),
                server_runtime_output_status=server.capture_status,
            )
    repository_after = gate._repository_content_snapshot(repository_root)
    observation = result["observation"]
    assert repository_after == repository_before
    assert (
        observation["one_pager_min_text_contrast_ratio"] >= 4.5
        and observation["download_button_height"] >= 44
        and observation["one_pager_state_text_matches"] is True
    ), {
        "contrast": observation.get("one_pager_min_text_contrast_ratio"),
        "download_height": observation.get("download_button_height"),
        "state_text_matches": observation.get("one_pager_state_text_matches"),
    }


def _ready_authoring_error_observation() -> dict[str, object]:
    return {
        "ready": True,
        "field_count": 1,
        "described_by": "research-authoring-demo-nvda-thesis-thesis-id-error",
        "linked_error_count": 1,
        "linked_error_owned": True,
        "linked_error_visible": True,
        "linked_error_inner_text": "thesis_id is required",
        "linked_error_text_content": "thesis_id is required",
        "linked_error_outer_html": (
            '<p data-research-authoring-error-owned="true">'
            "thesis_id is required</p>"
        ),
        "alert_count": 1,
        "alert_texts": ["Validation rejected\nthesis_id is required"],
        "active_label": "Thesis Id",
    }


def test_authoring_error_observation_timeout_fails_closed_after_late_ready_snapshot():
    import src.research_accessibility_browser_gate as gate

    class TimeoutPage:
        def wait_for_function(self, *args, **kwargs):
            raise TimeoutError("synthetic wait timeout")

        def evaluate(self, *args, **kwargs):
            return _ready_authoring_error_observation()

    observed = gate._wait_for_authoring_error_observation(
        TimeoutPage(),
        field_label="Thesis Id",
        expected_message="thesis_id is required",
        timeout_seconds=0.01,
    )

    assert observed["ready"] is False
    assert observed["linked_error_inner_text"] == "thesis_id is required"
    assert "TimeoutError: synthetic wait timeout" in observed["wait_error"]


def test_authoring_error_observation_evaluation_error_fails_closed():
    import src.research_accessibility_browser_gate as gate

    class EvaluationErrorPage:
        def wait_for_function(self, *args, **kwargs):
            return None

        def evaluate(self, *args, **kwargs):
            raise RuntimeError("synthetic observation failure")

    observed = gate._wait_for_authoring_error_observation(
        EvaluationErrorPage(),
        field_label="Thesis Id",
        expected_message="thesis_id is required",
        timeout_seconds=0.01,
    )

    assert observed["ready"] is False
    assert observed["wait_error"] == ""
    assert "RuntimeError: synthetic observation failure" in observed[
        "evaluation_error"
    ]


def test_actual_phone_authoring_association_waits_for_linked_error_text():
    import src.research_accessibility_browser_gate as gate
    from playwright.sync_api import sync_playwright

    class SemanticWaitPage:
        def __init__(self, page):
            self._page = page
            self.semantic_wait_calls = 0

        def __getattr__(self, name):
            return getattr(self._page, name)

        def wait_for_function(self, expression, *args, **kwargs):
            self.semantic_wait_calls += 1
            self._page.wait_for_function(
                """
() => window.__authoringLinkedTextDelayProbe?.triggered === true
""",
                timeout=10_000,
            )
            self._page.evaluate(
                """
() => window.dispatchEvent(
  new Event('research-authoring-semantic-wait-started')
)
"""
            )
            return self._page.wait_for_function(expression, *args, **kwargs)

    chrome = gate.find_chrome_executable()
    assert chrome is not None
    workbench = next(
        route for route in gate.RESEARCH_ROUTES if route.name == "Company Workbench"
    )
    with gate._captured_local_demo_server(Path.cwd(), timeout_seconds=45) as server:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path=str(chrome),
                headless=True,
            )
            context = browser.new_context(viewport={"width": 390, "height": 844})
            page = context.new_page()
            try:
                page.goto(
                    f"{server.base_url.rstrip('/')}{workbench.route}",
                    wait_until="domcontentloaded",
                    timeout=45_000,
                )
                gate._wait_for_visible_text(
                    page,
                    workbench.marker,
                    timeout_seconds=45,
                )
                gate._wait_for_dom_stability(page, timeout_seconds=45)
                gate._wait_for_route_heading(
                    page,
                    workbench,
                    timeout_seconds=45,
                )
                assert gate._open_company_workbench_modules(
                    page,
                    timeout_seconds=45,
                )["passed"] is True
                page.evaluate(
                    """
() => {
  const probe = {
    triggered: false,
    cleared_text: null,
    restored_text: null,
    release_count: 0,
  };
  window.__authoringLinkedTextDelayProbe = probe;
  const observer = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      for (const added of mutation.addedNodes) {
        if (!(added instanceof Element)) continue;
        const candidate = added.matches(
          '[data-research-authoring-error-owned="true"]'
        )
          ? added
          : added.querySelector(
              '[data-research-authoring-error-owned="true"]'
            );
        if (!candidate || !candidate.id.endsWith('thesis-thesis-id-error')) {
          continue;
        }
        const originalText = candidate.textContent;
        probe.triggered = true;
        candidate.textContent = '';
        probe.cleared_text = candidate.textContent;
        observer.disconnect();
        window.addEventListener(
          'research-authoring-semantic-wait-started',
          () => {
            if (candidate.isConnected) candidate.textContent = originalText;
            probe.restored_text = candidate.textContent;
            probe.release_count += 1;
          },
          {once: true}
        );
        return;
      }
    }
  });
  observer.observe(document.documentElement, {childList: true, subtree: true});
}
"""
                )

                semantic_page = SemanticWaitPage(page)
                assertions = gate._authoring_error_assertions(semantic_page)
                probe = page.evaluate("window.__authoringLinkedTextDelayProbe")
            finally:
                context.close()
                browser.close()

    association = next(
        assertion
        for assertion in assertions
        if assertion["name"] == "authoring_field_error_association"
    )
    assert probe["triggered"] is True
    assert probe["cleared_text"] == ""
    assert probe["restored_text"] == "thesis_id is required"
    assert probe["release_count"] == 1
    assert semantic_page.semantic_wait_calls == 2
    assert association["passed"] is True, {
        "association": association,
        "probe": probe,
    }
    assert all(assertion["passed"] for assertion in assertions), assertions


@pytest.mark.parametrize(
    "mutation_css",
    (
        '[data-section="evidence-one-pager"] { clip-path: inset(50%) !important; }',
        '[data-section="evidence-one-pager"] { position: fixed !important; top: -10000px !important; left: 50px !important; width: 1000px !important; }',
        "body::after { content: ''; position: fixed; inset: 0; background: #fff; z-index: 2147483647; pointer-events: auto; }",
        """
        [data-section="evidence-one-pager"] { margin-top: 1000px !important; }
        body::after { content: ''; position: fixed; inset: 0; background: #fff; z-index: 2147483647; pointer-events: auto; }
        """,
        "body::after { content: ''; position: fixed; inset: 0; background: #fff; z-index: 2147483647; pointer-events: none; }",
        """
        [data-section="evidence-one-pager"] { margin-top: 1000px !important; }
        body::after { content: ''; position: fixed; inset: 0; background: #fff; z-index: 2147483647; pointer-events: none; }
        """,
        ".test-pointer-transparent-cover { position: fixed; inset: 0; background: #fff; z-index: 2147483647; pointer-events: none; }",
        """
        [data-section="evidence-one-pager"] { margin-top: 1000px !important; }
        .test-pointer-transparent-cover { position: fixed; inset: 0; background: #fff; z-index: 2147483647; pointer-events: none; }
        """,
        "body::before { content: ''; position: fixed; inset: 0; background: #fff; z-index: 2147483647; pointer-events: none; }",
        """
        [data-section="evidence-one-pager"] { margin-top: 1000px !important; }
        body::before { content: ''; position: fixed; inset: 0; background: #fff; z-index: 2147483647; pointer-events: none; }
        """,
        "body::after { content: ''; position: fixed; left: -100vw; top: 0; width: 100vw; height: 100vh; transform: translateX(100vw); background: #fff; z-index: 2147483647; pointer-events: none; }",
        "body.srcc-pointer-cover-origin::after { content: ''; position: fixed; inset: 0; background: #fff; z-index: 2147483647; pointer-events: none !important; }",
        ".test-inside-pointer-transparent-cover { display: block !important; position: fixed; inset: 0; background: #fff; z-index: 2147483647; pointer-events: none; }",
        "[data-section=\"evidence-one-pager\"]::after { content: ''; position: fixed; inset: 0; background: #fff; z-index: 2147483647; pointer-events: none; }",
        ".test-pointer-transparent-svg-cover { display: block !important; position: fixed; inset: 0; width: 100vw; height: 100vh; z-index: 2147483647; pointer-events: none; }",
        ".test-inline-style-cover { display: block !important; }",
        ".test-pointer-transparent-cover { position: fixed; inset: 0; background: rgba(255, 255, 255, .98); z-index: 2147483647; pointer-events: none; }",
        ".test-pointer-transparent-cover { position: fixed; inset: 0; background: transparent; box-shadow: inset 0 0 0 100vmax #fff; z-index: 2147483647; pointer-events: none; }",
        "body::after { content: ''; position: fixed; inset: 0; background: transparent; box-shadow: inset 0 0 0 100vmax #fff; z-index: 2147483647; pointer-events: none; }",
        """
        /* tiny-outward-real-cover-current */
        .test-tiny-outward-paint-cover {
          display: block !important;
          position: fixed;
          left: 50vw;
          top: 50vh;
          width: 2px;
          height: 2px;
          box-sizing: border-box;
          transform: translate(-50%, -50%);
          z-index: 2147483647;
          pointer-events: none;
          background: transparent;
          box-shadow: 0 0 0 100vmax #fff;
        }
        """,
        """
        /* tiny-outward-real-cover-below-fold */
        [data-section="evidence-one-pager"] { margin-top: 1000px !important; }
        .test-tiny-outward-paint-cover {
          display: block !important;
          position: fixed;
          left: 50vw;
          top: 50vh;
          width: 2px;
          height: 2px;
          box-sizing: border-box;
          transform: translate(-50%, -50%);
          z-index: 2147483647;
          pointer-events: none;
          background: transparent;
          border: 100vmax solid #fff;
        }
        """,
        """
        /* tiny-outward-required-pseudo-cover-current */
        [data-section="one-pager-scenarios"] > ol > li:first-child .srcc-state::after {
          content: '';
          position: fixed;
          left: 50vw;
          top: 50vh;
          width: 2px;
          height: 2px;
          box-sizing: border-box;
          transform: translate(-50%, -50%);
          z-index: 2147483647;
          pointer-events: none;
          background: transparent;
          outline: 100vmax solid #fff;
          outline-offset: 0;
        }
        """,
        """
        /* tiny-outward-required-pseudo-cover-below-fold */
        [data-section="evidence-one-pager"] { margin-top: 1000px !important; }
        [data-section="one-pager-scenarios"] > ol > li:first-child .srcc-state::after {
          content: '';
          position: fixed;
          left: 50vw;
          top: 50vh;
          width: 2px;
          height: 2px;
          box-sizing: border-box;
          transform: translate(-50%, -50%);
          z-index: 2147483647;
          pointer-events: none;
          background: transparent;
          box-shadow: 0 0 0 100vmax #fff;
        }
        """,
        """
        /* stacked-real-cover-below-tiny-decoration */
        .test-pointer-transparent-cover {
          position: fixed; inset: 0; z-index: 2147483646;
          pointer-events: none; background: #fff;
        }
        .test-tiny-outward-paint-cover {
          display: block !important; position: fixed;
          left: 50vw; top: 50vh; width: 2px; height: 2px;
          transform: translate(-50%, -50%); z-index: 2147483647;
          pointer-events: none; background: #f0f;
        }
        """,
        """
        /* stacked-pseudo-cover-below-tiny-decoration */
        body::before {
          content: ''; position: fixed; inset: 0; z-index: 2147483646;
          pointer-events: none; background: #fff;
        }
        [data-section="evidence-one-pager"] { position: relative; }
        [data-section="evidence-one-pager"]::after {
          content: ''; position: absolute; left: 0; top: 0;
          width: 2px; height: 2px;
          z-index: 2147483647; pointer-events: none; background: #f0f;
        }
        """,
        """
        /* localized-required-node-covers */
        [data-section="evidence-one-pager"] .srcc-blockers {
          display: none !important;
        }
        [data-section="one-pager-provenance"] .srcc-blockers {
          display: block !important;
        }
        [data-section="one-pager-provenance"],
        [data-section="one-pager-scenarios"],
        [data-section="one-pager-handoff"] {
          position: relative;
        }
        [data-section="one-pager-provenance"]::after,
        [data-section="one-pager-scenarios"]::after,
        [data-section="one-pager-handoff"]::after {
          content: '';
          position: absolute;
          inset: 0;
          z-index: 2147483647;
          pointer-events: none;
          background: #fff;
        }
        """,
        """
        /* localized-required-leaf-covers */
        [data-section="evidence-one-pager"] .srcc-blockers {
          display: none !important;
        }
        [data-section="one-pager-provenance"] .srcc-blockers {
          display: block !important;
        }
        [data-section="one-pager-provenance"] caption,
        [data-section="one-pager-provenance"] tbody td:nth-child(2),
        [data-section="one-pager-provenance"] .srcc-blockers > li,
        [data-section="one-pager-scenarios"] > ol > li:first-child .srcc-state,
        [data-section="one-pager-scenarios"] [data-share-basis-role],
        [data-section="one-pager-handoff"] > p {
          position: relative;
        }
        [data-section="one-pager-provenance"] caption::after,
        [data-section="one-pager-provenance"] tbody td:nth-child(2)::after,
        [data-section="one-pager-provenance"] .srcc-blockers > li::after,
        [data-section="one-pager-scenarios"] > ol > li:first-child .srcc-state::after,
        [data-section="one-pager-scenarios"] [data-share-basis-role]::after,
        [data-section="one-pager-handoff"] > p::after {
          content: '';
          position: absolute;
          inset: 0;
          z-index: 2147483647;
          pointer-events: none;
          background: #fff;
        }
        """,
        """
        /* layered-important-real-cover */
        @layer adversarial {
          .test-layer-cover { position: fixed; inset: 0; z-index: 2147483647; pointer-events: none !important; background: #f0f; }
        }
        """,
        """
        /* layered-important-pseudo-cover */
        @layer adversarial {
          body::after { content: ''; position: fixed; inset: 0; z-index: 2147483647; pointer-events: none !important; background: #f0f; }
        }
        """,
        """
        /* oklab-pointer-transparent-cover */
        body::after { content: ''; position: fixed; inset: 0; z-index: 2147483647; pointer-events: none; background: transparent; box-shadow: inset 0 0 0 100vmax oklab(.8 0 0); }
        """,
        """
        /* tiny-required-state-decoration */
        [data-section="one-pager-scenarios"] > ol > li:first-child .srcc-state {
          position: relative !important;
        }
        [data-section="one-pager-scenarios"] > ol > li:first-child .srcc-state::after {
          content: '';
          position: absolute;
          right: 0;
          bottom: 0;
          width: 4px;
          height: 2px;
          z-index: 2147483647;
          pointer-events: none;
          background: #f0f;
        }
        """,
    ),
    ids=(
        "clip-path",
        "fixed-above-document",
        "opaque-fixed-cover",
        "scroll-reachable-under-fixed-cover",
        "pointer-transparent-opaque-cover",
        "scroll-reachable-under-pointer-transparent-cover",
        "pointer-transparent-element-cover",
        "scroll-reachable-under-pointer-transparent-element-cover",
        "pointer-transparent-before-cover",
        "scroll-reachable-under-pointer-transparent-before-cover",
        "transformed-pointer-transparent-pseudo-cover",
        "important-pointer-transparent-pseudo-cover",
        "inside-pointer-transparent-element-cover",
        "inside-pointer-transparent-pseudo-cover",
        "pointer-transparent-svg-cover",
        "pointer-transparent-inline-style-restoration",
        "translucent-pointer-transparent-element-cover",
        "pointer-transparent-inset-box-shadow-cover",
        "pointer-transparent-inset-box-shadow-pseudo-cover",
        "tiny-outward-real-cover-current",
        "tiny-outward-real-cover-below-fold",
        "tiny-outward-required-pseudo-cover-current",
        "tiny-outward-required-pseudo-cover-below-fold",
        "stacked-real-cover-below-tiny-decoration",
        "stacked-pseudo-cover-below-tiny-decoration",
        "localized-required-node-covers",
        "localized-required-leaf-covers",
        "layered-important-real-cover",
        "layered-important-pseudo-cover",
        "oklab-pointer-transparent-cover",
        "tiny-required-state-decoration",
    ),
)
def test_actual_company_workbench_one_pager_collector_rejects_hidden_summary_with_outside_blockers(
    mutation_css,
):
    import src.research_accessibility_browser_gate as gate
    from playwright.sync_api import sync_playwright

    chrome = gate.find_chrome_executable()
    assert chrome is not None
    external_requests = []
    with gate._captured_local_demo_server(
        Path.cwd(),
        timeout_seconds=45,
    ) as server:
        active_origin = gate._exact_http_origin(server.base_url)
        assert active_origin is not None
        hostname = gate.urlparse(server.base_url).hostname
        assert hostname
        with gate.tempfile.TemporaryDirectory(
            prefix="stock-research-workbench-one-pager-clipped-",
            dir="/tmp",
        ) as profile_directory:
            preferences = Path(profile_directory) / "Default" / "Preferences"
            preferences.parent.mkdir(parents=True)
            preferences.write_text(
                gate.json.dumps(
                    gate._chromium_zoom_preferences(host=hostname, zoom=1),
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
            with sync_playwright() as playwright:
                context = playwright.chromium.launch_persistent_context(
                    user_data_dir=profile_directory,
                    executable_path=str(chrome),
                    headless=True,
                    viewport={"width": 1280, "height": 720},
                    screen={"width": 1280, "height": 720},
                    service_workers="block",
                )

                def intercept(route, request):
                    request_origin = gate._exact_http_origin(str(request.url))
                    if request_origin is not None and request_origin != active_origin:
                        external_requests.append(str(request.url))
                        route.abort()
                    else:
                        route.continue_()

                context.route("**/*", intercept)
                page = context.pages[0] if context.pages else context.new_page()
                try:
                    workbench = next(
                        route
                        for route in gate.RESEARCH_ROUTES
                        if route.name == "Company Workbench"
                    )
                    page.goto(
                        f"{server.base_url.rstrip('/')}{workbench.route}",
                        wait_until="domcontentloaded",
                        timeout=45_000,
                    )
                    gate._wait_for_visible_text(
                        page,
                        workbench.marker,
                        timeout_seconds=45,
                    )
                    gate._wait_for_dom_stability(page, timeout_seconds=45)
                    gate._wait_for_route_heading(
                        page,
                        workbench,
                        timeout_seconds=45,
                    )
                    assert gate._open_company_workbench_modules(
                        page,
                        timeout_seconds=45,
                    )["passed"] is True
                    assert gate._open_company_workbench_html_brief(
                        page,
                        timeout_seconds=45,
                    )["passed"] is True
                    page.evaluate(
                        """css => {
                            const style = document.createElement('style');
                            style.textContent = css;
                            document.head.appendChild(style);
                            document.body.classList.add('srcc-pointer-cover-origin');
                            const outside = document.createElement('div');
                            outside.className = 'srcc-blockers';
                            outside.textContent = 'Outside summary blockers must not count.';
                            document.body.appendChild(outside);
                            const cover = document.createElement('div');
                            cover.className = 'test-pointer-transparent-cover';
                            cover.setAttribute('aria-hidden', 'true');
                            document.body.appendChild(cover);
                            const layerCover = document.createElement('div');
                            layerCover.className = 'test-layer-cover';
                            layerCover.setAttribute('aria-hidden', 'true');
                            document.body.appendChild(layerCover);
                            const onePager = document.querySelector(
                                '[data-section="evidence-one-pager"]'
                            );
                            const insideCover = document.createElement('div');
                            insideCover.className = 'test-inside-pointer-transparent-cover';
                            insideCover.setAttribute('aria-hidden', 'true');
                            insideCover.style.display = 'none';
                            onePager.prepend(insideCover);
                            const outwardPaintCover = document.createElement('div');
                            outwardPaintCover.className = 'test-tiny-outward-paint-cover';
                            outwardPaintCover.setAttribute('aria-hidden', 'true');
                            outwardPaintCover.style.display = 'none';
                            onePager.prepend(outwardPaintCover);
                            const svgCover = document.createElementNS(
                                'http://www.w3.org/2000/svg', 'svg'
                            );
                            svgCover.setAttribute('class', 'test-pointer-transparent-svg-cover');
                            svgCover.setAttribute('aria-hidden', 'true');
                            svgCover.setAttribute('viewBox', '0 0 1 1');
                            svgCover.style.display = 'none';
                            const rect = document.createElementNS(
                                'http://www.w3.org/2000/svg', 'rect'
                            );
                            rect.setAttribute('width', '1');
                            rect.setAttribute('height', '1');
                            rect.setAttribute('fill', '#fff');
                            svgCover.appendChild(rect);
                            document.body.appendChild(svgCover);
                            const inlineCover = document.createElement('div');
                            inlineCover.className = 'test-inline-style-cover';
                            inlineCover.setAttribute('aria-hidden', 'true');
                            inlineCover.setAttribute(
                                'data-srcc-pointer-probe-real', 'preserve'
                            );
                            inlineCover.setAttribute(
                                'style',
                                'display:none; pointer-events:none!important; POSITION:fixed; inset:0; background:#fff; z-index:2147483647'
                            );
                            document.body.appendChild(inlineCover);
                        }""",
                        mutation_css,
                    )
                    page.evaluate(
                        "() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))"
                    )
                    scroll_state_script = """() => ({
                        window: [window.scrollX, window.scrollY],
                        nodes: [...document.querySelectorAll('*')]
                            .map((node, index) => [
                                index,
                                node.scrollLeft,
                                node.scrollTop,
                                node.scrollWidth,
                                node.scrollHeight,
                                node.clientWidth,
                                node.clientHeight,
                            ])
                            .filter(([, left, top, width, height, clientWidth, clientHeight]) =>
                                left || top || width > clientWidth || height > clientHeight
                            ),
                    })"""
                    scroll_state_before = page.evaluate(scroll_state_script)
                    probe_state_script = """() => ({
                        active: [
                            document.activeElement?.tagName || '',
                            document.activeElement?.id || '',
                            document.activeElement?.className || '',
                        ],
                        style_count: document.querySelectorAll('style').length,
                        candidate_styles: [...document.querySelectorAll(
                                '.test-pointer-transparent-cover, ' +
                                '.test-layer-cover, ' +
                                '.test-inside-pointer-transparent-cover, ' +
                                '.test-pointer-transparent-svg-cover, ' +
                                '.test-inline-style-cover, ' +
                                '.test-tiny-outward-paint-cover, ' +
                                '[data-section="evidence-one-pager"], ' +
                                '[data-section="one-pager-provenance"], ' +
                                '[data-section="one-pager-provenance"] caption, ' +
                                '[data-section="one-pager-provenance"] tbody td, ' +
                                '[data-section="one-pager-provenance"] .srcc-blockers > li, ' +
                                '[data-section="one-pager-scenarios"], ' +
                                '[data-section="one-pager-scenarios"] .srcc-state, ' +
                                '[data-section="one-pager-scenarios"] [data-share-basis-role], ' +
                                '[data-section="one-pager-handoff"], ' +
                                '[data-section="one-pager-handoff"] > p'
                        )].map(node => [
                            node.className?.baseVal || node.className || '',
                            node.hasAttribute('style'),
                            node.getAttribute('style'),
                        ]),
                        probe_attributes: [...document.querySelectorAll('*')]
                            .filter(node => [...node.attributes].some(attribute =>
                                attribute.name.startsWith('data-srcc-pointer-probe-')
                            ))
                            .map(node => [...node.attributes]
                                .filter(attribute => attribute.name.startsWith(
                                    'data-srcc-pointer-probe-'
                                ))
                                .map(attribute => [attribute.name, attribute.value])
                            ),
                    })"""
                    probe_state_before = page.evaluate(probe_state_script)
                    outside_visible = page.locator(
                        "body > .srcc-blockers:visible"
                    ).count()
                    observation = gate._company_workbench_one_pager_dom_observation(
                        page
                    )
                    scroll_state_after = page.evaluate(scroll_state_script)
                    probe_state_after = page.evaluate(probe_state_script)
                finally:
                    context.close()

    assert external_requests == []
    assert outside_visible == 1
    assert scroll_state_after == scroll_state_before
    assert probe_state_after == probe_state_before, {
        "style_differences": [
            (before, after)
            for before, after in zip(
                probe_state_before["candidate_styles"],
                probe_state_after["candidate_styles"],
                strict=True,
            )
            if before != after
        ],
        "other_before": {
            key: value
            for key, value in probe_state_before.items()
            if key != "candidate_styles"
        },
        "other_after": {
            key: value
            for key, value in probe_state_after.items()
            if key != "candidate_styles"
        },
    }
    if "tiny-required-state-decoration" in mutation_css:
        assert (
            observation["one_pager_visible"] is True
            and observation["one_pager_visible_count"] == 1
            and observation["one_pager_provenance_visible"] is True
            and observation["one_pager_blockers_visible"] is True
            and observation["one_pager_assumptions_visible"] is True
            and observation["one_pager_handoff_visible"] is True
            and observation["one_pager_state_text_matches"] is True
            and observation["one_pager_share_basis_visible_count"] == 4
            and observation["advanced_evidence_count"] == 1
            and observation["advanced_evidence_after_one_pager"] is True
        ), observation
    elif "localized-required-" in mutation_css:
        assert (
            observation["one_pager_visible"] is True
            and observation["one_pager_visible_count"] == 1
            and observation["one_pager_provenance_visible"] is False
            and observation["one_pager_blockers_visible"] is False
            and observation["one_pager_assumptions_visible"] is False
            and observation["one_pager_handoff_visible"] is False
            and observation["one_pager_state_text_matches"] is False
            and observation["one_pager_share_basis_visible_count"] == 1
            and observation["advanced_evidence_count"] == 1
            and observation["advanced_evidence_after_one_pager"] is True
        ), observation
    else:
        assert (
            observation["one_pager_visible"] is False
            and observation["one_pager_visible_count"] == 0
            and observation["one_pager_min_text_contrast_ratio"] < 0
            and observation["one_pager_min_boundary_contrast_ratio"] < 0
            and observation["one_pager_provenance_visible"] is False
            and observation["one_pager_blockers_visible"] is False
            and observation["one_pager_assumptions_visible"] is False
            and observation["one_pager_handoff_visible"] is False
            and observation["one_pager_state_text_matches"] is False
            and observation["one_pager_share_basis_visible_count"] == 0
            and observation["advanced_evidence_count"] == 1
            and observation["advanced_evidence_after_one_pager"] is True
        ), observation


def test_proof_history_media_marker_selects_the_rendered_public_timeline():
    from src.dashboard import proof_history_public_timeline_html
    from src.research_accessibility_browser_gate import RESEARCH_ROUTES

    proof_route = next(
        route for route in RESEARCH_ROUTES if route.name == "Research Proof History"
    )
    rendered = proof_history_public_timeline_html(None, None)
    marker_class = proof_route.media_marker_selector.removeprefix(".")

    assert proof_route.media_marker_selector.startswith(".")
    assert f"class='{marker_class}'" in rendered


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


def test_bridge_transport_contract_exposes_zero_footprint_result_fields():
    from src.research_accessibility_browser_gate import evaluate_bridge_transport

    passed = evaluate_bridge_transport(
        runtime_messages=("console info: Streamlit app ready",),
        bridge_iframe_count=0,
        bridge_focusable_count=0,
        bridge_heights=(0.0, 0.0),
    )

    assert passed["passed"] is True
    assert passed["deprecated_component_warning_count"] == 0
    assert passed["bridge_iframe_count"] == 0
    assert passed["bridge_focusable_count"] == 0
    assert passed["bridge_height"] == 0
    assert all(assertion["passed"] for assertion in passed["assertions"])


def test_bridge_transport_contract_fails_closed_for_each_legacy_or_visible_signal():
    from src.research_accessibility_browser_gate import evaluate_bridge_transport

    cases = (
        (
            {"runtime_messages": ("st.components.v1.html is deprecated",)},
            "deprecated_component_warning_count",
        ),
        ({"bridge_iframe_count": 1}, "bridge_iframe_count"),
        ({"bridge_focusable_count": 1}, "bridge_focusable_count"),
        ({"bridge_heights": (0.0, 1.25)}, "bridge_height"),
    )
    defaults = {
        "runtime_messages": (),
        "bridge_iframe_count": 0,
        "bridge_focusable_count": 0,
        "bridge_heights": (0.0,),
    }

    for changed, failed_field in cases:
        failed = evaluate_bridge_transport(**{**defaults, **changed})
        assert failed["passed"] is False
        assert failed[failed_field] > 0
        assert next(
            assertion
            for assertion in failed["assertions"]
            if assertion["name"] == failed_field
        )["passed"] is False


def test_bridge_transport_contract_rejects_non_integer_dom_counts_without_coercion():
    from src.research_accessibility_browser_gate import evaluate_bridge_transport

    defaults = {
        "runtime_messages": (),
        "bridge_iframe_count": 0,
        "bridge_focusable_count": 0,
        "bridge_heights": (0.0,),
    }
    for field in ("bridge_iframe_count", "bridge_focusable_count"):
        for malformed in (False, True, 0.5, -1, "0"):
            failed = evaluate_bridge_transport(
                **{**defaults, field: malformed}
            )
            assert failed["passed"] is False
            assert failed[field] == -1


def test_server_runtime_output_contract_fails_on_warning_or_unavailable_capture():
    from src.research_accessibility_browser_gate import (
        evaluate_server_runtime_output,
    )

    clean = evaluate_server_runtime_output(
        capture_status="captured_local_server",
        runtime_messages=("Streamlit server started",),
    )
    warned = evaluate_server_runtime_output(
        capture_status="captured_local_server",
        runtime_messages=("st.components.v1.html is deprecated",),
    )
    external = evaluate_server_runtime_output(
        capture_status="unavailable_external_base_url",
        runtime_messages=(),
    )

    assert clean["passed"] is True
    assert clean["deprecated_component_warning_count"] == 0
    assert warned["passed"] is False
    assert warned["deprecated_component_warning_count"] == 1
    assert external["passed"] is False
    assert external["deprecated_component_warning_count"] is None
    assert "unavailable" in str(external["detail"]).lower()


def test_local_server_context_captures_bounded_stdout_and_stderr(monkeypatch, tmp_path):
    import src.research_accessibility_browser_gate as gate

    class FakeOutput:
        def __init__(self):
            self.close_calls = 0

        def __iter__(self):
            return iter(
                (
                    "server ready\n",
                    "st.components.v1.html is deprecated\n",
                )
            )

        def close(self):
            self.close_calls += 1

    class FakeProcess:
        def __init__(self):
            self.stdout = FakeOutput()

        def terminate(self):
            return None

        def wait(self, timeout):
            return 0

        def kill(self):
            return None

    monkeypatch.setattr(gate, "_free_port", lambda: 43123)
    monkeypatch.setattr(gate, "_wait_for_health", lambda *args, **kwargs: None)
    process = FakeProcess()
    monkeypatch.setattr(gate.subprocess, "Popen", lambda *args, **kwargs: process)

    with gate._captured_local_demo_server(
        tmp_path,
        timeout_seconds=5,
    ) as server:
        assert server.base_url == "http://127.0.0.1:43123"

    assert tuple(server.runtime_messages) == (
        "server ready",
        "st.components.v1.html is deprecated",
    )
    assert server.capture_status == "captured_local_server"
    assert process.stdout.close_calls == 1


def test_local_server_launchers_disable_streamlit_usage_telemetry_once(
    monkeypatch,
    tmp_path,
):
    import src.research_accessibility_browser_gate as gate

    launched_commands = []

    class FakeOutput:
        def __iter__(self):
            return iter(())

        def close(self):
            return None

    class FakeProcess:
        def __init__(self):
            self.stdout = FakeOutput()

        def terminate(self):
            return None

        def wait(self, timeout):
            return 0

        def kill(self):
            return None

    def fake_popen(command, **kwargs):
        launched_commands.append(tuple(command))
        return FakeProcess()

    monkeypatch.setattr(gate, "_free_port", lambda: 43123)
    monkeypatch.setattr(gate, "_wait_for_health", lambda *args, **kwargs: None)
    monkeypatch.setattr(gate.subprocess, "Popen", fake_popen)

    with gate._captured_local_demo_server(tmp_path, timeout_seconds=5):
        pass
    with gate._captured_local_state_harness_server(tmp_path, timeout_seconds=5):
        pass

    assert len(launched_commands) == 2
    for command in launched_commands:
        assert command.count("--browser.gatherUsageStats") == 1
        option_index = command.index("--browser.gatherUsageStats")
        assert command[option_index + 1] == "false"


def test_bounded_server_capture_retains_warning_count_after_early_line_eviction():
    from collections import deque

    from src.research_accessibility_browser_gate import (
        MAX_SERVER_RUNTIME_LINES,
        RuntimeServerEvidence,
        evaluate_server_runtime_output,
    )

    server = RuntimeServerEvidence(
        base_url="http://127.0.0.1:43123",
        runtime_messages=deque(maxlen=MAX_SERVER_RUNTIME_LINES),
        capture_status="captured_local_server",
    )
    server.append("st.components.v1.html is deprecated")
    for index in range(MAX_SERVER_RUNTIME_LINES + 1):
        server.append(f"clean server line {index}")

    assert all(
        "st.components.v1.html" not in line
        for line in server.snapshot()
    )
    assert server.total_line_count == MAX_SERVER_RUNTIME_LINES + 2
    assert server.truncated_line_count == 2
    evidence = evaluate_server_runtime_output(
        capture_status=server.capture_status,
        runtime_messages=server.snapshot(),
        deprecated_component_warning_count=server.deprecated_warning_count(),
    )
    assert evidence["passed"] is False
    assert evidence["deprecated_component_warning_count"] == 1


def test_server_warning_count_inspects_full_line_before_storage_truncation():
    from collections import deque

    from src.research_accessibility_browser_gate import (
        MAX_SERVER_RUNTIME_LINE_LENGTH,
        MAX_SERVER_RUNTIME_LINES,
        RuntimeServerEvidence,
    )

    server = RuntimeServerEvidence(
        base_url="http://127.0.0.1:43123",
        runtime_messages=deque(maxlen=MAX_SERVER_RUNTIME_LINES),
        capture_status="captured_local_server",
    )
    server.append(
        ("x" * MAX_SERVER_RUNTIME_LINE_LENGTH)
        + " st.components.v1.html is deprecated"
    )

    assert len(server.snapshot()[0]) == MAX_SERVER_RUNTIME_LINE_LENGTH
    assert "st.components.v1.html" not in server.snapshot()[0]
    assert server.deprecated_warning_count() == 1


def test_server_reader_exception_marks_capture_failed_closed(monkeypatch, tmp_path):
    import src.research_accessibility_browser_gate as gate

    class ExplodingOutput:
        def __init__(self):
            self.close_calls = 0

        def __iter__(self):
            raise UnicodeDecodeError("utf-8", b"x", 0, 1, "invalid")

        def close(self):
            self.close_calls += 1

    class FakeProcess:
        def __init__(self):
            self.stdout = ExplodingOutput()

        def terminate(self):
            return None

        def wait(self, timeout):
            return 0

        def kill(self):
            return None

    monkeypatch.setattr(gate, "_free_port", lambda: 43123)
    monkeypatch.setattr(gate, "_wait_for_health", lambda *args, **kwargs: None)
    process = FakeProcess()
    monkeypatch.setattr(gate.subprocess, "Popen", lambda *args, **kwargs: process)

    with gate._captured_local_demo_server(
        tmp_path,
        timeout_seconds=5,
    ) as server:
        pass

    assert server.capture_status == "failed_reader_exception"
    assert process.stdout.close_calls == 1
    assert gate.evaluate_server_runtime_output(
        capture_status=server.capture_status,
        runtime_messages=server.snapshot(),
        deprecated_component_warning_count=server.deprecated_warning_count(),
    )["passed"] is False


def test_server_reader_join_timeout_marks_capture_incomplete(monkeypatch, tmp_path):
    import src.research_accessibility_browser_gate as gate

    class FakeOutput:
        def __init__(self):
            self.close_calls = 0

        def close(self):
            self.close_calls += 1

    class FakeProcess:
        def __init__(self):
            self.stdout = FakeOutput()

        def terminate(self):
            return None

        def wait(self, timeout):
            return 0

        def kill(self):
            return None

    class NeverFinishesThread:
        def __init__(self, **kwargs):
            self.target = kwargs["target"]

        def start(self):
            return None

        def join(self, timeout):
            assert timeout == 5

        def is_alive(self):
            return True

    monkeypatch.setattr(gate, "_free_port", lambda: 43123)
    monkeypatch.setattr(gate, "_wait_for_health", lambda *args, **kwargs: None)
    process = FakeProcess()
    monkeypatch.setattr(gate.subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(gate.threading, "Thread", NeverFinishesThread)

    with gate._captured_local_demo_server(
        tmp_path,
        timeout_seconds=5,
    ) as server:
        pass

    assert server.capture_status == "incomplete_reader_shutdown"
    assert process.stdout.close_calls == 0
    assert gate.evaluate_server_runtime_output(
        capture_status=server.capture_status,
        runtime_messages=server.snapshot(),
        deprecated_component_warning_count=server.deprecated_warning_count(),
    )["passed"] is False


def test_bridge_transport_observation_measures_only_fixed_accessibility_bridges():
    from src.research_accessibility_browser_gate import (
        _bridge_transport_observation,
    )

    class FakePage:
        def evaluate(self, script):
            assert '[data-testid="stHtml"]' in script
            assert "__stockResearchMainObserver" in script
            assert "data-research-authoring-error-owned" in script
            assert "iframe" in script
            assert "getBoundingClientRect" in script
            assert "tabindex" in script
            return {
                "bridge_iframe_count": 0,
                "bridge_focusable_count": 0,
                "bridge_heights": [0, 0],
            }

    observed = _bridge_transport_observation(
        FakePage(),
        runtime_messages=("console info: ready",),
    )

    assert observed["passed"] is True
    assert observed["deprecated_component_warning_count"] == 0
    assert observed["bridge_iframe_count"] == 0
    assert observed["bridge_focusable_count"] == 0
    assert observed["bridge_height"] == 0


def test_route_result_includes_fail_closed_bridge_transport_fields(monkeypatch):
    import src.research_accessibility_browser_gate as gate

    class FakePage:
        url = "http://127.0.0.1:8501/?mode=research&page=data-health&ticker=NVDA"

        def on(self, event, handler):
            assert event in {"console", "pageerror"}

        def goto(self, url, *, wait_until, timeout):
            self.url = url

    class FakeContext:
        def __init__(self):
            self.page = FakePage()

        def new_page(self):
            return self.page

        def close(self):
            return None

    class FakeBrowser:
        def new_context(self, *, viewport):
            assert viewport == {"width": 390, "height": 844}
            return FakeContext()

    monkeypatch.setattr(gate, "_wait_for_visible_text", lambda *args, **kwargs: None)
    monkeypatch.setattr(gate, "_wait_for_dom_stability", lambda *args, **kwargs: None)
    monkeypatch.setattr(gate, "_wait_for_route_heading", lambda *args, **kwargs: None)
    monkeypatch.setattr(gate, "_semantic_main_assertions", lambda *args, **kwargs: [])
    monkeypatch.setattr(gate, "_runtime_dom_assertions", lambda *args, **kwargs: [])
    monkeypatch.setattr(gate, "_skip_link_assertions", lambda *args, **kwargs: [])
    monkeypatch.setattr(gate, "_media_preference_assertions", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        gate, "_personal_navigation_authority_assertions", lambda *args, **kwargs: []
    )
    monkeypatch.setattr(
        gate,
        "_evidence_navigation_assertion",
        lambda *args, **kwargs: {
            "name": "evidence_navigation",
            "passed": True,
            "detail": "present without a false core current item",
        },
    )
    monkeypatch.setattr(gate, "_navigation_assertion", lambda *args, **kwargs: {
        "name": "navigation",
        "passed": True,
        "detail": "present",
    })
    monkeypatch.setattr(gate, "_navigate_and_verify_route", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        gate,
        "_bridge_transport_observation",
        lambda page, *, runtime_messages, server_deprecated_warning_count=0: (
            gate.evaluate_bridge_transport(
                runtime_messages=runtime_messages,
                bridge_iframe_count=0,
                bridge_focusable_count=0,
                bridge_heights=(0,),
                server_deprecated_warning_count=server_deprecated_warning_count,
            )
        ),
    )

    result = gate._measure_route(
        FakeBrowser(),
        base_url="http://127.0.0.1:8501",
        route=gate.RESEARCH_ROUTES[4],
        viewport=(390, 844),
        timeout_seconds=5,
    )
    warned = gate._measure_route(
        FakeBrowser(),
        base_url="http://127.0.0.1:8501",
        route=gate.RESEARCH_ROUTES[4],
        viewport=(390, 844),
        timeout_seconds=5,
        server_deprecated_warning_count=1,
        server_runtime_output_status="captured_local_server",
    )

    assert result["passed"] is True
    assert result["deprecated_component_warning_count"] == 0
    assert result["bridge_iframe_count"] == 0
    assert result["bridge_focusable_count"] == 0
    assert result["bridge_height"] == 0
    assert warned["passed"] is False
    assert warned["deprecated_component_warning_count"] == 1
    assert warned["server_runtime_output_status"] == "captured_local_server"


def test_same_document_streamlit_rerun_contract_fails_closed_for_each_gap():
    from src.research_accessibility_browser_gate import (
        evaluate_same_document_streamlit_rerun,
    )

    passing_values = {
        "trigger_count": 1,
        "trigger_activated": True,
        "initial_observer_available": True,
        "token_before": "probe-1",
        "token_after": "probe-1",
        "same_document": True,
        "top_level_navigation_count": 0,
        "initial_script_state": "notRunning",
        "script_states": ("notRunning", "running", "notRunning"),
        "final_script_state": "notRunning",
        "observer_liveness_proved": True,
        "active_target": True,
        "bridge_status": "applied",
        "route_before": "/?mode=research&page=data-health&ticker=NVDA",
        "route_after": "/?mode=research&page=data-health&ticker=NVDA",
    }
    passed = evaluate_same_document_streamlit_rerun(**passing_values)

    assert all(assertion["passed"] for assertion in passed)
    assert [assertion["name"] for assertion in passed] == [
        "streamlit_rerun_trigger_available",
        "streamlit_rerun_trigger_activated",
        "streamlit_rerun_initial_observer_available",
        "streamlit_rerun_initial_script_idle",
        "streamlit_rerun_cycle_completed",
        "streamlit_rerun_same_document",
        "streamlit_rerun_no_top_level_navigation",
        "streamlit_rerun_observer_live",
        "streamlit_rerun_active_target",
        "streamlit_rerun_bridge_status",
        "streamlit_rerun_route_preserved",
    ]

    for assertion_name, changed in (
        ("streamlit_rerun_trigger_available", {"trigger_count": 0}),
        ("streamlit_rerun_trigger_activated", {"trigger_activated": False}),
        (
            "streamlit_rerun_initial_observer_available",
            {"initial_observer_available": False},
        ),
        (
            "streamlit_rerun_initial_script_idle",
            {"initial_script_state": "running"},
        ),
        (
            "streamlit_rerun_cycle_completed",
            {
                "script_states": ("notRunning", "rerunRequested", "notRunning"),
            },
        ),
        (
            "streamlit_rerun_cycle_completed",
            {
                "script_states": ("notRunning", "running"),
                "final_script_state": "running",
            },
        ),
        (
            "streamlit_rerun_same_document",
            {"token_after": "new-document", "same_document": False},
        ),
        (
            "streamlit_rerun_no_top_level_navigation",
            {"top_level_navigation_count": 1},
        ),
        (
            "streamlit_rerun_observer_live",
            {"observer_liveness_proved": False},
        ),
        ("streamlit_rerun_active_target", {"active_target": False}),
        ("streamlit_rerun_bridge_status", {"bridge_status": "missing"}),
        (
            "streamlit_rerun_route_preserved",
            {"route_after": "/?mode=research&page=discover"},
        ),
    ):
        failed_values = {**passing_values, **changed}
        failed = evaluate_same_document_streamlit_rerun(**failed_values)
        assert next(
            assertion
            for assertion in failed
            if assertion["name"] == assertion_name
        )["passed"] is False


def test_media_preference_assertions_emulate_both_modes_and_restore_each(monkeypatch):
    import src.research_accessibility_browser_gate as gate

    class FakePage:
        def __init__(self):
            self.calls = []

        def emulate_media(self, **kwargs):
            self.calls.append(kwargs)

    page = FakePage()
    monkeypatch.setattr(gate, "_forced_colors_observation", lambda page, route: {})
    monkeypatch.setattr(gate, "_reduced_motion_observation", lambda page, route: {})
    monkeypatch.setattr(gate, "evaluate_forced_colors_observation", lambda observation, *, primary_route: [{"name": "forced", "passed": True, "detail": "ok"}])
    monkeypatch.setattr(gate, "evaluate_reduced_motion_observation", lambda observation: [{"name": "motion", "passed": True, "detail": "ok"}])

    assertions = gate._media_preference_assertions(page, gate.RESEARCH_ROUTES[0])

    assert all(item["passed"] for item in assertions)
    assert page.calls == [
        {"forced_colors": "active", "reduced_motion": "no-preference"},
        {"forced_colors": "none", "reduced_motion": "no-preference"},
        {"forced_colors": "none", "reduced_motion": "reduce"},
        {"forced_colors": "none", "reduced_motion": "no-preference"},
    ]


def test_media_preference_assertions_restore_and_continue_after_probe_failure(monkeypatch):
    import src.research_accessibility_browser_gate as gate

    class FakePage:
        def __init__(self):
            self.calls = []

        def emulate_media(self, **kwargs):
            self.calls.append(kwargs)

    def fail_forced(page, route):
        raise RuntimeError("forced probe")

    page = FakePage()
    monkeypatch.setattr(gate, "_forced_colors_observation", fail_forced)
    monkeypatch.setattr(gate, "_reduced_motion_observation", lambda page, route: {})
    monkeypatch.setattr(gate, "evaluate_reduced_motion_observation", lambda observation: [{"name": "motion", "passed": True, "detail": "ok"}])

    assertions = gate._media_preference_assertions(page, gate.RESEARCH_ROUTES[0])

    forced = next(item for item in assertions if item["name"] == "forced_colors_execution")
    assert forced["passed"] is False
    assert "RuntimeError: forced probe" in forced["detail"]
    assert next(item for item in assertions if item["name"] == "motion")["passed"] is True
    assert page.calls == [
        {"forced_colors": "active", "reduced_motion": "no-preference"},
        {"forced_colors": "none", "reduced_motion": "no-preference"},
        {"forced_colors": "none", "reduced_motion": "reduce"},
        {"forced_colors": "none", "reduced_motion": "no-preference"},
    ]


def test_media_preference_assertions_report_each_restore_failure(monkeypatch):
    import src.research_accessibility_browser_gate as gate

    class FakePage:
        def __init__(self):
            self.calls = []

        def emulate_media(self, **kwargs):
            self.calls.append(kwargs)
            if kwargs == {"forced_colors": "none", "reduced_motion": "no-preference"}:
                raise RuntimeError("restore failed")

    page = FakePage()
    monkeypatch.setattr(gate, "_forced_colors_observation", lambda page, route: {})
    monkeypatch.setattr(gate, "_reduced_motion_observation", lambda page, route: {})
    monkeypatch.setattr(gate, "evaluate_forced_colors_observation", lambda observation, *, primary_route: [{"name": "forced", "passed": True, "detail": "ok"}])
    monkeypatch.setattr(gate, "evaluate_reduced_motion_observation", lambda observation: [{"name": "motion", "passed": True, "detail": "ok"}])

    assertions = gate._media_preference_assertions(page, gate.RESEARCH_ROUTES[0])

    restores = [item for item in assertions if item["name"] == "media_preferences_restore"]
    assert len(restores) == 2
    assert all(item["passed"] is False for item in restores)
    assert all("RuntimeError: restore failed" in item["detail"] for item in restores)


def test_same_document_rerun_helper_uses_real_workspace_widget_event():
    from src.research_accessibility_browser_gate import (
        _same_document_streamlit_rerun_assertions,
    )

    class FakeRadio:
        def __init__(self, page):
            self.page = page

        def count(self):
            return 1

        def evaluate(self, script):
            assert "element.click()" in script
            assert "element.checked" in script
            self.page.used_dom_click = True
            self.page.rerun_triggered = True
            if self.page.simulate_top_navigation:
                self.page.frame_handler(self.page.main_frame)
            return True

    class FakePage:
        def __init__(self, *, simulate_top_navigation=False):
            self.main_frame = object()
            self.simulate_top_navigation = simulate_top_navigation
            self.frame_handler = None
            self.used_dom_click = False
            self.rerun_triggered = False
            self.evaluate_calls = 0
            self.wait_calls = 0

        def on(self, event, handler):
            assert event == "framenavigated"
            self.frame_handler = handler

        def get_by_role(self, role, *, name, exact):
            assert (role, name, exact) == (
                "radio",
                "Public visitor mode",
                True,
            )
            return FakeRadio(self)

        def evaluate(self, script):
            assert "__a11ySameDocumentRerunProbe" in script
            assert "__stockResearchMainObserver" in script
            self.evaluate_calls += 1
            if self.evaluate_calls == 1:
                assert "document: document" in script
                assert "data-test-script-state" in script
                assert "MutationObserver" in script
                return {
                    "token": "probe-1",
                    "initial_observer_available": True,
                    "initial_script_state": "notRunning",
                    "route": "/?mode=research&page=data-health&ticker=NVDA",
                }
            if self.evaluate_calls == 2:
                assert "__stockResearchMainTarget" in script
                assert "observer-probe-pending" in script
                assert "appendChild" in script
                return True
            assert "__stockResearchMainTarget" in script
            assert "scriptStateObserver.disconnect()" in script
            assert "observerProbeNode.remove()" in script
            return {
                "token": "probe-1",
                "same_document": True,
                "script_states": ["notRunning", "running", "notRunning"],
                "final_script_state": "notRunning",
                "observer_liveness_proved": self.rerun_triggered,
                "active_target": True,
                "bridge_status": "applied",
                "route": "/?mode=research&page=data-health&ticker=NVDA",
            }

        def wait_for_function(self, script, *, timeout):
            assert self.rerun_triggered is True
            assert "__a11ySameDocumentRerunProbe" in script
            self.wait_calls += 1
            if self.wait_calls == 1:
                assert 'states.indexOf("running")' in script
                assert 'states.indexOf("notRunning", runningIndex + 1)' in script
            else:
                assert "observerProbeNode" in script
                assert "data-research-main-bridge-status" in script
                assert '"applied"' in script
            assert timeout == 5_000

    page = FakePage()
    passed = _same_document_streamlit_rerun_assertions(
        page,
        timeout_seconds=5,
    )
    navigated_page = FakePage(simulate_top_navigation=True)
    failed = _same_document_streamlit_rerun_assertions(
        navigated_page,
        timeout_seconds=5,
    )

    assert page.used_dom_click is True
    assert page.wait_calls == 2
    assert all(assertion["passed"] for assertion in passed)
    assert next(
        assertion
        for assertion in failed
        if assertion["name"] == "streamlit_rerun_no_top_level_navigation"
    )["passed"] is False


def test_evidence_navigation_contract_requires_one_nav_and_no_false_core_current_item():
    from src.research_accessibility_browser_gate import (
        evaluate_evidence_navigation,
    )

    correct = evaluate_evidence_navigation(
        navigation_count=1,
        current_count=0,
        phase="initial",
    )
    false_current = evaluate_evidence_navigation(
        navigation_count=1,
        current_count=1,
        phase="rerender",
    )

    assert correct == {
        "name": "evidence_workflow_navigation_initial",
        "passed": True,
        "detail": "labelled workflow navigation count=1; current core item count=0",
    }
    assert false_current["passed"] is False


def test_route_transition_target_is_deterministic_and_never_self():
    from src.research_accessibility_browser_gate import (
        RESEARCH_ROUTES,
        ROUND_TRIP_AWAY_ROUTE_NAMES,
        _route_transition_target,
    )

    assert ROUND_TRIP_AWAY_ROUTE_NAMES == {
        "Research Desk": "Discover",
        "Discover": "Company Workbench",
        "Company Workbench": "Monitor",
        "Monitor": "Research Data Health",
        "Research Data Health": "Research Proof History",
        "Research Proof History": "Research Desk",
    }
    assert [
        _route_transition_target(route).name
        for route in RESEARCH_ROUTES
    ] == [
        "Discover",
        "Company Workbench",
        "Monitor",
        "Research Data Health",
        "Research Proof History",
        "Research Desk",
    ]
    assert all(
        _route_transition_target(route) != route
        for route in RESEARCH_ROUTES
    )


def test_exact_route_url_contract_rejects_fragment_or_query_drift():
    from src.research_accessibility_browser_gate import evaluate_exact_route_url

    expected = (
        "http://127.0.0.1:8501/"
        "?mode=research&page=company-workbench&ticker=NVDA&open=1"
    )
    passed = evaluate_exact_route_url(
        actual_url=expected,
        expected_url=expected,
        phase="route_return",
    )
    fragment = evaluate_exact_route_url(
        actual_url=f"{expected}#public-page-answer",
        expected_url=expected,
        phase="route_return",
    )
    query_drift = evaluate_exact_route_url(
        actual_url=expected.replace("open=1", "open=0"),
        expected_url=expected,
        phase="route_return",
    )

    assert passed["passed"] is True
    assert passed["name"] == "exact_route_url_route_return"
    assert fragment["passed"] is False
    assert query_drift["passed"] is False


def test_route_transition_verifies_url_after_late_render_mutation(monkeypatch):
    import src.research_accessibility_browser_gate as gate

    expected = "http://127.0.0.1:8501/?mode=research&page=research-desk"
    events = []

    class FakePage:
        url = ""

        def goto(self, url, *, wait_until, timeout):
            assert wait_until == "domcontentloaded"
            assert timeout == 5_000
            self.url = url
            events.append("goto")

    def late_stability_drift(page, *, timeout_seconds):
        assert timeout_seconds == 5
        events.append("stability")
        page.url = f"{page.url}#late-render-drift"

    monkeypatch.setattr(
        gate,
        "_wait_for_visible_text",
        lambda page, marker, *, timeout_seconds: events.append("marker"),
    )
    monkeypatch.setattr(gate, "_wait_for_dom_stability", late_stability_drift)
    monkeypatch.setattr(
        gate,
        "_wait_for_route_heading",
        lambda page, route, *, timeout_seconds: events.append("h1"),
    )
    monkeypatch.setattr(gate, "_semantic_main_assertions", lambda page, *, phase: [])
    monkeypatch.setattr(gate, "_runtime_dom_assertions", lambda page, *, phase: [])
    monkeypatch.setattr(
        gate,
        "_navigation_assertion",
        lambda page, route: {
            "name": "labelled_workflow_navigation",
            "passed": True,
            "detail": "fake navigation",
        },
    )

    assertions = gate._navigate_and_verify_route(
        FakePage(),
        base_url="http://127.0.0.1:8501",
        route=gate.RESEARCH_ROUTES[0],
        phase="route_away",
        timeout_seconds=5,
    )

    assert events == ["goto", "marker", "stability", "h1"]
    assert next(
        assertion
        for assertion in assertions
        if assertion["name"] == "exact_route_url_route_away"
    )["passed"] is False
    assert expected in str(assertions[0]["detail"])


def test_discover_action_contract_uses_every_actual_row_and_fails_when_empty():
    from src.research_accessibility_browser_gate import (
        evaluate_discover_action_names,
    )

    passed = evaluate_discover_action_names(
        [
            "Open NVDA Company Brief",
            "Open AVGO Company Brief",
            "Open BRK.B Company Brief",
        ]
    )
    empty = evaluate_discover_action_names([])
    duplicate = evaluate_discover_action_names(
        ["Open NVDA Company Brief", "Open NVDA Company Brief"]
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


def test_discover_row_contract_requires_three_visible_answers_and_ticker_action():
    from src.research_accessibility_browser_gate import evaluate_discover_rows

    passed = evaluate_discover_rows(
        (
            {
                "ticker": "NVDA",
                "labels": (
                    "WHY INSPECTABLE",
                    "USABLE EVIDENCE",
                    "MAIN EVIDENCE GAP",
                ),
                "values": (
                    "Saved readiness supports review.",
                    "SEC quarterly actuals.",
                    "Point-in-time consensus is missing.",
                ),
                "action_name": "Open NVDA Company Brief",
                "action_ticker": "NVDA",
                "action_height": 44.0,
                "visible": True,
            },
            {
                "ticker": "AVGO",
                "labels": (
                    "Why inspectable",
                    "Usable evidence",
                    "Main evidence gap",
                ),
                "values": (
                    "Saved readiness supports review.",
                    "Historical valuation context.",
                    "No principal blocker is recorded.",
                ),
                "action_name": "Open AVGO Company Brief",
                "action_ticker": "AVGO",
                "action_height": 48.0,
                "visible": True,
            },
        )
    )
    missing_answer = evaluate_discover_rows(
        (
            {
                "ticker": "NVDA",
                "labels": ("Why inspectable", "Usable evidence"),
                "values": ("Saved readiness supports review.", ""),
                "action_name": "Open NVDA Company Brief",
                "action_ticker": "NVDA",
                "action_height": 44.0,
                "visible": True,
            },
        )
    )

    assert passed["passed"] is True
    assert passed["actual_count"] == 2
    assert missing_answer["passed"] is False
    assert "three visible non-empty answers" in str(missing_answer["detail"])


def test_monitor_row_contract_accepts_filtered_order_and_rejects_monitor_or_rank_fields():
    from src.research_accessibility_browser_gate import evaluate_monitor_rows

    passed = evaluate_monitor_rows(
        (
            {
                "cohort_order": 1,
                "ticker": "BBB",
                "attention": "Needs review",
                "reason": "Conflicting saved evidence needs review.",
            },
            {
                "cohort_order": 4,
                "ticker": "EEE",
                "attention": "Scheduled",
                "reason": "Reviewer-authored review is scheduled.",
            },
        ),
        primary_columns=("TICKER", "PROCESS ATTENTION", "WHY"),
        primary_table_present=True,
        advanced_present=True,
        advanced_identity_count=5,
        expected_discipline_count=5,
        neutral_visible=False,
    )
    all_monitor = evaluate_monitor_rows(
        (),
        primary_columns=(),
        primary_table_present=False,
        advanced_present=True,
        advanced_identity_count=5,
        expected_discipline_count=5,
        neutral_visible=True,
    )
    leaked_monitor = evaluate_monitor_rows(
        ({"cohort_order": 0, "ticker": "AAA", "attention": "Monitor", "reason": "Wait."},),
        primary_columns=("Ticker", "Process attention", "Why"),
        primary_table_present=True,
        advanced_present=True,
        advanced_identity_count=5,
        expected_discipline_count=5,
        neutral_visible=False,
    )
    ranked = evaluate_monitor_rows(
        ({"cohort_order": 2, "ticker": "CCC", "attention": "Scheduled", "reason": "Saved review."},),
        primary_columns=("Ticker", "Process attention", "Return score"),
        primary_table_present=True,
        advanced_present=True,
        advanced_identity_count=5,
        expected_discipline_count=5,
        neutral_visible=False,
    )

    assert passed["passed"] is True
    assert all_monitor["passed"] is True
    assert leaked_monitor["passed"] is False
    assert "monitor row" in str(leaked_monitor["detail"]).lower()
    assert ranked["passed"] is False
    assert "rank/score/return" in str(ranked["detail"])


def test_monitor_row_contract_rejects_incomplete_advanced_identities_for_hidden_rows():
    from src.research_accessibility_browser_gate import evaluate_monitor_rows

    mixed = evaluate_monitor_rows(
        (
            {
                "cohort_order": 1,
                "ticker": "BBB",
                "attention": "Needs review",
                "reason": "Conflicting saved evidence needs review.",
            },
            {
                "cohort_order": 4,
                "ticker": "EEE",
                "attention": "Scheduled",
                "reason": "Reviewer-authored review is scheduled.",
            },
        ),
        primary_columns=("Ticker", "Process attention", "Why"),
        primary_table_present=True,
        advanced_present=True,
        advanced_identity_count=2,
        expected_discipline_count=5,
        neutral_visible=False,
    )
    all_monitor = evaluate_monitor_rows(
        (),
        primary_columns=(),
        primary_table_present=False,
        advanced_present=True,
        advanced_identity_count=4,
        expected_discipline_count=5,
        neutral_visible=True,
    )

    assert mixed["passed"] is False
    assert "expected 5" in str(mixed["detail"])
    assert all_monitor["passed"] is False
    assert "expected 5" in str(all_monitor["detail"])


def test_monitor_row_contract_requires_advanced_container_for_true_empty_state():
    from src.research_accessibility_browser_gate import evaluate_monitor_rows

    valid_empty = evaluate_monitor_rows(
        (),
        primary_columns=(),
        primary_table_present=False,
        advanced_present=True,
        advanced_identity_count=0,
        expected_discipline_count=0,
        neutral_visible=True,
    )
    missing_advanced = evaluate_monitor_rows(
        (),
        primary_columns=(),
        primary_table_present=False,
        advanced_present=False,
        advanced_identity_count=0,
        expected_discipline_count=0,
        neutral_visible=True,
    )

    assert valid_empty["passed"] is True
    assert missing_advanced["passed"] is False
    assert "Advanced discipline evidence container" in str(
        missing_advanced["detail"]
    )


def test_monitor_row_contract_allows_actionable_queue_without_process_rows():
    from src.research_accessibility_browser_gate import evaluate_monitor_rows

    freshness_only = evaluate_monitor_rows(
        (),
        primary_columns=(),
        primary_table_present=False,
        advanced_present=True,
        advanced_identity_count=5,
        expected_discipline_count=5,
        neutral_visible=False,
        queue_visible=True,
    )

    assert freshness_only["passed"] is True


def test_monitor_row_contract_rejects_wrong_columns_on_empty_primary_table():
    from src.research_accessibility_browser_gate import evaluate_monitor_rows

    valid_empty_table = evaluate_monitor_rows(
        (),
        primary_columns=("Ticker", "Process attention", "Why"),
        primary_table_present=True,
        advanced_present=True,
        advanced_identity_count=5,
        expected_discipline_count=5,
        neutral_visible=True,
    )
    wrong_empty_table = evaluate_monitor_rows(
        (),
        primary_columns=("Ticker", "Process attention", "Confidence"),
        primary_table_present=True,
        advanced_present=True,
        advanced_identity_count=5,
        expected_discipline_count=5,
        neutral_visible=True,
    )

    assert valid_empty_table["passed"] is True
    assert wrong_empty_table["passed"] is False
    assert "unexpected primary Monitor columns" in str(wrong_empty_table["detail"])


def test_monitor_follow_up_geometry_requires_two_columns_on_desktop_and_one_on_phone():
    from src.research_accessibility_browser_gate import evaluate_monitor_brief

    desktop = evaluate_monitor_brief(
        kickers=(
            "SINCE LAST REVIEW",
            "NEEDS VERIFICATION",
            "WAITING ON EVIDENCE",
            "SCHEDULED CONTEXT",
            "EVIDENCE FRESHNESS",
        ),
        boxes=((0, 0), (500, 0), (0, 180), (500, 180), (0, 360)),
        viewport_width=1280,
    )
    phone = evaluate_monitor_brief(
        kickers=(
            "SINCE LAST REVIEW",
            "NEEDS VERIFICATION",
            "WAITING ON EVIDENCE",
            "SCHEDULED CONTEXT",
            "EVIDENCE FRESHNESS",
        ),
        boxes=((0, 0), (0, 180), (0, 360), (0, 540), (0, 720)),
        viewport_width=390,
    )
    wrong_phone = evaluate_monitor_brief(
        kickers=(
            "SINCE LAST REVIEW",
            "NEEDS VERIFICATION",
            "WAITING ON EVIDENCE",
            "SCHEDULED CONTEXT",
            "EVIDENCE FRESHNESS",
        ),
        boxes=((0, 0), (180, 0), (0, 180), (180, 180), (0, 360)),
        viewport_width=390,
    )
    assert desktop["passed"] is True
    assert phone["passed"] is True
    assert wrong_phone["passed"] is False


def test_monitor_brief_geometry_rejects_overlapping_or_missing_desktop_cells():
    from src.research_accessibility_browser_gate import evaluate_monitor_brief

    kickers = (
        "SINCE LAST REVIEW",
        "NEEDS VERIFICATION",
        "WAITING ON EVIDENCE",
        "SCHEDULED CONTEXT",
        "EVIDENCE FRESHNESS",
    )
    overlapping_pairs = evaluate_monitor_brief(
        kickers=kickers,
        boxes=((0, 0), (0, 0), (500, 180), (500, 180), (0, 360)),
        viewport_width=1280,
    )
    missing_cell = evaluate_monitor_brief(
        kickers=kickers,
        boxes=((0, 0), (500, 0), (0, 180), (0, 180), (0, 360)),
        viewport_width=1280,
    )

    assert overlapping_pairs["passed"] is False
    assert missing_cell["passed"] is False


def test_monitor_brief_geometry_rejects_non_finite_coordinates():
    from src.research_accessibility_browser_gate import evaluate_monitor_brief

    for coordinate in (float("nan"), float("inf"), float("-inf")):
        evaluated = evaluate_monitor_brief(
            kickers=(
                "SINCE LAST REVIEW",
                "NEEDS VERIFICATION",
                "WAITING ON EVIDENCE",
                "SCHEDULED CONTEXT",
                "EVIDENCE FRESHNESS",
            ),
            boxes=((coordinate, 0), (500, 0), (0, 180), (500, 180), (0, 360)),
            viewport_width=1280,
        )

        assert evaluated["passed"] is False
        assert "finite" in str(evaluated["detail"]).lower()


def test_state_harness_snapshot_rejects_hidden_duplicate_or_wrong_live_semantics():
    from src.research_accessibility_browser_gate import (
        evaluate_research_state_snapshot,
    )

    passed = evaluate_research_state_snapshot(
        static_states=(
            {"state": "loading", "visible": True, "role": "group", "live": "", "busy": "true"},
            {"state": "empty", "visible": True, "role": "group", "live": "", "busy": ""},
            {"state": "withheld", "visible": True, "role": "group", "live": "", "busy": ""},
            {"state": "stale", "visible": True, "role": "group", "live": "", "busy": ""},
            {"state": "failure", "visible": True, "role": "group", "live": "", "busy": ""},
            {"state": "validation", "visible": True, "role": "group", "live": "", "busy": ""},
        ),
        transition_state="preview_ready",
        transition_nodes=(
            {
                "visible": True,
                "role": "status",
                "live": "polite",
                "atomic": "true",
                "text": "Preview ready TEST1",
            },
        ),
    )
    duplicate = evaluate_research_state_snapshot(
        static_states=passed["static_states"],
        transition_state="preview_ready",
        transition_nodes=(
            {
                "visible": True,
                "role": "status",
                "live": "polite",
                "atomic": "true",
                "text": "Preview ready TEST1",
            },
            {
                "visible": False,
                "role": "status",
                "live": "polite",
                "atomic": "true",
                "text": "Hidden duplicate TEST1",
            },
        ),
    )

    assert passed["passed"] is True
    assert duplicate["passed"] is False
    assert "exactly one visible transition node" in str(duplicate["detail"])


def test_state_harness_rerender_requires_one_visible_non_live_message():
    from src.research_accessibility_browser_gate import (
        evaluate_research_state_rerender,
    )

    passed = evaluate_research_state_rerender(
        (
            {
                "visible": True,
                "role": "group",
                "live": "",
                "atomic": "",
                "text": "Preview ready TEST1",
            },
        )
    )
    repeated_live = evaluate_research_state_rerender(
        (
            {
                "visible": True,
                "role": "status",
                "live": "polite",
                "atomic": "true",
                "text": "Preview ready TEST1",
            },
        )
    )

    assert passed["passed"] is True
    assert repeated_live["passed"] is False
    assert "non-live" in str(repeated_live["detail"])


def test_repository_snapshot_contract_rejects_any_harness_write():
    from src.research_accessibility_browser_gate import (
        evaluate_repository_snapshot_unchanged,
    )

    assert evaluate_repository_snapshot_unchanged(
        before="M data/generated.csv\0",
        after="M data/generated.csv\0",
    )["passed"] is True
    changed = evaluate_repository_snapshot_unchanged(
        before="M data/generated.csv\0",
        after="M data/generated.csv\0?? evidence.json\0",
    )
    assert changed["passed"] is False
    assert "repository status changed" in str(changed["detail"])


def test_repository_snapshot_detects_content_change_in_already_dirty_file(tmp_path):
    from src.research_accessibility_browser_gate import (
        _repository_content_snapshot,
    )

    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    tracked = tmp_path / "tracked.csv"
    tracked.write_text("version,1\n", encoding="utf-8")
    subprocess.run(["git", "add", "--", "tracked.csv"], cwd=tmp_path, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ],
        cwd=tmp_path,
        check=True,
    )
    tracked.write_text("version,2\n", encoding="utf-8")
    before = _repository_content_snapshot(tmp_path)
    status_before = subprocess.run(
        ["git", "status", "--porcelain=v1"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout

    tracked.write_text("version,3\n", encoding="utf-8")
    after = _repository_content_snapshot(tmp_path)
    status_after = subprocess.run(
        ["git", "status", "--porcelain=v1"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout

    assert status_before == status_after == " M tracked.csv\n"
    assert before != after


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
    compact_research_shell = evaluate_demo_app_identity(
        page_title="Stock Research Command Center",
        brand_text="Stock Research Command Center",
        profile_label="",
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
    assert compact_research_shell["passed"] is True
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


def test_repository_hygiene_can_snapshot_an_exact_unstaged_implementation_allowlist():
    from scripts.diff_hygiene import StatusEntry
    from src.research_accessibility_browser_gate import evaluate_repository_hygiene

    dashboard = StatusEntry("M", "src/dashboard.py")
    unrelated = StatusEntry("?", "notes.txt")

    allowed = evaluate_repository_hygiene(
        [dashboard],
        staged_entries=[],
        allowed_dirty_paths=("src/dashboard.py",),
    )
    still_blocked = evaluate_repository_hygiene(
        [dashboard, unrelated],
        staged_entries=[],
        allowed_dirty_paths=("src/dashboard.py",),
    )

    assert allowed["passed"] is True
    assert allowed["allowed_dirty_product_paths"] == ["src/dashboard.py"]
    assert still_blocked["passed"] is False
    assert still_blocked["dirty_product_paths"] == ["notes.txt"]


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
