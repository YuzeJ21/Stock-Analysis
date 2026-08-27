"""Deterministic browser evidence for the calm institutional workspace shell."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, urlsplit

from src.paths import resolve_project_root
from src.public_performance_gate import (
    _wait_for_dom_stability,
    _wait_for_visible_text,
    find_chrome_executable,
)
from src.research_accessibility_browser_gate import _captured_local_demo_server


VIEWPORTS: tuple[tuple[int, int], ...] = ((1280, 720), (1440, 1024), (390, 844))
ZOOMS: tuple[int, ...] = (1, 2)
PERSONAL_FOCUS_ROUTE_SLUGS: frozenset[str] = frozenset(
    {"research-desk", "discover", "company-workbench", "monitor"}
)
MAX_EXTERNAL_HTTP_URL_EVIDENCE = 16


@dataclass(frozen=True)
class WorkspaceVisualRoute:
    slug: str
    name: str
    route: str
    marker: str
    expected_h1: str
    mode: str


@dataclass(frozen=True)
class BrowserEvaluation:
    passed: bool
    detail: str


ROUTE_FIXTURES: tuple[WorkspaceVisualRoute, ...] = (
    WorkspaceVisualRoute(
        "research-desk",
        "Research Desk",
        "/?mode=research&page=research-desk",
        "What needs my attention today?",
        "Research Desk",
        "research",
    ),
    WorkspaceVisualRoute(
        "discover",
        "Discover",
        "/?mode=research&page=discover",
        "Find a Company",
        "Discover",
        "research",
    ),
    WorkspaceVisualRoute(
        "company-workbench",
        "AVGO Company Workbench",
        "/?mode=research&page=company-workbench&ticker=AVGO",
        "Company Brief",
        "Company Workbench",
        "research",
    ),
    WorkspaceVisualRoute(
        "monitor",
        "Monitor",
        "/?mode=research&page=monitor&return_ticker=NVDA",
        "Follow-up Queue",
        "Monitor",
        "research",
    ),
    WorkspaceVisualRoute(
        "public-home",
        "Public Home",
        "/?mode=public",
        "What is this product and where do I start?",
        "What is this product and where do I start?",
        "public",
    ),
    WorkspaceVisualRoute(
        "stock-selector",
        "Stock Selector",
        "/?mode=public&page=stock-selector",
        "Which stock can I review?",
        "Which stock can I review?",
        "public",
    ),
    WorkspaceVisualRoute(
        "single-stock-report",
        "AVGO Single-Stock Report",
        "/?mode=public&page=single-stock-report&ticker=AVGO&open=1",
        "What can I use for this ticker right now?",
        "What can I use for this ticker right now?",
        "public",
    ),
    WorkspaceVisualRoute(
        "public-data-health",
        "Public Data Health",
        "/?mode=public&page=data-health&ticker=AVGO",
        "Price / setup",
        "What can I use and what stays unavailable?",
        "public",
    ),
    WorkspaceVisualRoute(
        "public-proof-history",
        "Public Proof History",
        "/?mode=public&page=proof-history&ticker=AVGO",
        "Newest reviewed evidence",
        "What evidence changed a readiness state?",
        "public",
    ),
    WorkspaceVisualRoute(
        "personal-data-health",
        "Personal Data Health",
        "/?mode=research&page=data-health&ticker=AVGO&lane=peers&drawer=proof",
        "Selected Lane Answer",
        "Data Health",
        "research",
    ),
    WorkspaceVisualRoute(
        "personal-proof-history",
        "Personal Proof History",
        "/?mode=research&page=proof-history&ticker=AVGO",
        "Newest reviewed evidence",
        "Proof History",
        "research",
    ),
    WorkspaceVisualRoute(
        "operator-overview",
        "Operator Overview",
        "/?mode=operator&page=overview",
        "Overview",
        "Overview",
        "operator",
    ),
    WorkspaceVisualRoute(
        "market-direction",
        "Market Direction",
        "/?mode=operator&page=market-direction",
        "Market Direction",
        "Market Direction",
        "operator",
    ),
    WorkspaceVisualRoute(
        "universe-manager",
        "Universe Manager",
        "/?mode=operator&page=universe-manager",
        "Universe Manager",
        "Universe Manager",
        "operator",
    ),
    WorkspaceVisualRoute(
        "monthly-picks",
        "Monthly Picks",
        "/?mode=operator&page=monthly-picks",
        "Monthly Picks",
        "Monthly Picks",
        "operator",
    ),
)

_ROUTES_BY_SLUG = {route.slug: route for route in ROUTE_FIXTURES}


def evaluate_horizontal_bounds(*, left: float, right: float, client_width: float) -> BrowserEvaluation:
    passed = left >= -1 and right <= client_width + 1
    return BrowserEvaluation(
        passed,
        f"horizontal bounds {left:.1f}..{right:.1f} within client width {client_width:.1f}",
    )


def evaluate_scroll_width(*, scroll_width: float, client_width: float) -> BrowserEvaluation:
    passed = scroll_width <= client_width + 1
    return BrowserEvaluation(
        passed,
        f"scroll width {scroll_width:.1f} versus client width {client_width:.1f}",
    )


def evaluate_mobile_navigation_discoverability(
    *,
    phone_media_matches: bool,
    expected_total: int,
    total: int,
    visible: int,
    fully_visible: int,
    scroll_width: float,
    client_width: float,
) -> BrowserEvaluation:
    """Require every primary destination to be visible without a hidden phone scroller."""

    if not phone_media_matches:
        return BrowserEvaluation(True, "desktop navigation is outside the phone-wrap contract")
    passed = (
        expected_total > 0
        and total == expected_total
        and visible == expected_total
        and fully_visible == expected_total
        and client_width > 0
        and scroll_width <= client_width + 1
    )
    return BrowserEvaluation(
        passed,
        (
            f"phone links total={total}/{expected_total}; visible={visible}; "
            f"fully_visible={fully_visible}; scroll={scroll_width:.1f}/{client_width:.1f}"
        ),
    )


def evaluate_proof_history_initial_tree(
    *,
    record_count: int,
    summary: str,
) -> BrowserEvaluation:
    """Require a bounded, explicitly newest-first initial proof-history tree."""

    normalized = " ".join(str(summary or "").split()).casefold()
    match = re.search(
        r"\bshowing\s+(\d+)\s+of\s+(\d+)\s+reviewed records in newest-first order\b",
        normalized,
    )
    shown = int(match.group(1)) if match else -1
    total = int(match.group(2)) if match else -1
    passed = (
        match is not None
        and total >= 1
        and shown == record_count
        and record_count == min(20, total)
    )
    return BrowserEvaluation(
        passed,
        f"initial proof records={record_count}; summary={normalized!r}",
    )


def evaluate_control_target(*, width: float, height: float) -> BrowserEvaluation:
    passed = width >= 44 and height >= 44
    return BrowserEvaluation(passed, f"control target {width:.1f}x{height:.1f}")


def evaluate_company_workbench_document_contract(
    *,
    viewport_width: float,
    zoom: int,
    phone_layout: bool,
    h1_count: int,
    display_title_count: int,
    display_title_text: str,
    navigation_count: int,
    navigation_labelled_count: int,
    brief_count: int,
    brief_visible_count: int,
    brief_labelled_count: int,
    aside_count: int,
    aside_visible_count: int,
    aside_labelled_count: int,
    evidence_lane_count: int,
    positive_tabindex_count: int,
    primary_action_count: int,
    primary_action_visible_count: int,
    primary_action_width: float,
    primary_action_height: float,
    module_gate_count: int,
    module_gate_visible_count: int,
    brief_box: dict[str, object],
    aside_box: dict[str, object],
    module_gate_box: dict[str, object],
    brief_lane_boxes: tuple[dict[str, object], ...],
) -> BrowserEvaluation:
    """Require the Workbench's document/aside hierarchy across reflow states."""

    def coordinates(box: dict[str, object]) -> tuple[float, float, float, float] | None:
        try:
            left = float(box.get("left", math.nan))
            right = float(box.get("right", math.nan))
            top = float(box.get("top", math.nan))
            bottom = float(box.get("bottom", math.nan))
        except (TypeError, ValueError):
            return None
        values = (left, right, top, bottom)
        if not all(math.isfinite(value) for value in values):
            return None
        if right <= left or bottom <= top:
            return None
        return values

    brief = coordinates(brief_box)
    aside = coordinates(aside_box)
    module_gate = coordinates(module_gate_box)
    action_target = evaluate_control_target(
        width=primary_action_width,
        height=primary_action_height,
    )
    semantic_structure = (
        h1_count == 1
        and display_title_count == 1
        and str(display_title_text or "").strip().endswith(" Company Brief")
        and navigation_count == 1
        and navigation_labelled_count == 1
        and brief_count == 1
        and brief_visible_count == 1
        and brief_labelled_count == 1
        and aside_count == 1
        and aside_visible_count == 1
        and aside_labelled_count == 1
        and evidence_lane_count == 5
        and positive_tabindex_count == 0
        and primary_action_count == 1
        and primary_action_visible_count == 1
        and action_target.passed
        and module_gate_count == 1
        and module_gate_visible_count == 1
    )

    reflowed = zoom == 2 or viewport_width < 1100
    geometry_passed = False
    if brief is not None and aside is not None and module_gate is not None:
        brief_left, brief_right, brief_top, brief_bottom = brief
        aside_left, aside_right, aside_top, aside_bottom = aside
        _gate_left, _gate_right, gate_top, _gate_bottom = module_gate
        if reflowed:
            geometry_passed = (
                brief_bottom <= aside_top + 1
                and aside_bottom <= gate_top + 1
            )
        else:
            vertical_overlap = min(brief_bottom, aside_bottom) - max(
                brief_top, aside_top
            )
            geometry_passed = (
                brief_right <= aside_left + 1
                and vertical_overlap > 1
                and max(brief_bottom, aside_bottom) <= gate_top + 1
            )

    phone_lanes_passed = True
    if phone_layout:
        lanes = tuple(coordinates(dict(box)) for box in brief_lane_boxes)
        if brief is None or len(lanes) != 4 or any(lane is None for lane in lanes):
            phone_lanes_passed = False
        else:
            assert all(lane is not None for lane in lanes)
            normalized_lanes = tuple(lane for lane in lanes if lane is not None)
            brief_left, brief_right, _brief_top, _brief_bottom = brief
            phone_lanes_passed = all(
                previous[3] <= current[2] + 1
                for previous, current in zip(
                    normalized_lanes, normalized_lanes[1:]
                )
            ) and all(
                lane[0] >= brief_left - 1 and lane[1] <= brief_right + 1
                for lane in normalized_lanes
            )

    passed = semantic_structure and geometry_passed and phone_lanes_passed
    return BrowserEvaluation(
        passed,
        (
            f"viewport_width={viewport_width:.1f}; zoom={zoom}; phone={phone_layout}; "
            f"h1={h1_count}; display_title={display_title_count}/{display_title_text!r}; "
            f"navigation={navigation_labelled_count}/{navigation_count}; "
            f"brief={brief_visible_count}/{brief_count} labelled={brief_labelled_count}; "
            f"aside={aside_visible_count}/{aside_count} labelled={aside_labelled_count} "
            f"lanes={evidence_lane_count}; positive_tabindex={positive_tabindex_count}; "
            f"primary_action={primary_action_visible_count}/{primary_action_count} "
            f"{primary_action_width:.1f}x{primary_action_height:.1f}; "
            f"module_gate={module_gate_visible_count}/{module_gate_count}; "
            f"reflowed={reflowed}; geometry={geometry_passed}; "
            f"phone_lanes={phone_lanes_passed}"
        ),
    )


def evaluate_runtime_capture(
    *,
    app_state: str,
    traceback_visible: bool,
    spinner_count: int,
    console_errors: tuple[str, ...],
) -> BrowserEvaluation:
    """Require a completed Streamlit render with no captured runtime failure."""

    passed = (
        app_state == "notRunning"
        and traceback_visible is False
        and spinner_count == 0
        and not console_errors
    )
    return BrowserEvaluation(
        passed,
        (
            f"app_state={app_state!r}; traceback={traceback_visible}; "
            f"spinners={spinner_count}; console_errors={list(console_errors)!r}"
        ),
    )


def evaluate_resolved_report_state(
    *,
    company_brief_count: int,
    primary_answer_count: int,
    evidence_lane_count: int,
    busy_loading_count: int,
) -> BrowserEvaluation:
    """Require the stable Workbench to replace the temporary busy report state."""

    passed = (
        company_brief_count == 1
        and primary_answer_count == 4
        and evidence_lane_count == 5
        and busy_loading_count == 0
    )
    return BrowserEvaluation(
        passed,
        (
            "one completed Company Brief is stable with no aria-busy loading state"
            if passed
            else (
                f"company_brief_count={company_brief_count}; "
                f"primary_answer_count={primary_answer_count}; "
                f"evidence_lane_count={evidence_lane_count}; "
                f"busy_loading_count={busy_loading_count}"
            )
        ),
    )


def _contrast_ratio(foreground: str, background: str) -> float | None:
    """Return WCAG contrast for browser-computed opaque rgb colors."""

    def luminance(value: str) -> float | None:
        match = re.fullmatch(
            r"rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)",
            str(value or "").strip(),
        )
        if match is None:
            return None
        channels = tuple(int(channel) for channel in match.groups())
        if any(channel < 0 or channel > 255 for channel in channels):
            return None
        linear = tuple(
            channel / 255 / 12.92
            if channel / 255 <= 0.04045
            else ((channel / 255 + 0.055) / 1.055) ** 2.4
            for channel in channels
        )
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    foreground_luminance = luminance(foreground)
    background_luminance = luminance(background)
    if foreground_luminance is None or background_luminance is None:
        return None
    lighter, darker = sorted((foreground_luminance, background_luminance), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def evaluate_advanced_evidence_rail_contrast(
    *,
    marker_count: int,
    label_color: str,
    current_color: str,
    navigation_background: str,
) -> BrowserEvaluation:
    """Require the desktop Advanced Evidence cue to remain readable on the nav rail."""

    label_ratio = _contrast_ratio(label_color, navigation_background)
    current_ratio = _contrast_ratio(current_color, navigation_background)
    passed = (
        marker_count == 1
        and label_ratio is not None
        and current_ratio is not None
        and label_ratio >= 4.5
        and current_ratio >= 4.5
    )
    return BrowserEvaluation(
        passed,
        (
            "one Advanced Evidence marker has readable label and current-location text on the desktop nav rail"
            if passed
            else (
                f"marker_count={marker_count}; label_color={label_color!r}; "
                f"current_color={current_color!r}; navigation_background={navigation_background!r}; "
                f"label_contrast={label_ratio!r}; current_contrast={current_ratio!r}"
            )
        ),
    )


def evaluate_advanced_evidence_navigation_layout(
    *,
    phone_layout: bool,
    marker_count: int,
    primary_link_count: int,
    marker_box: dict[str, object],
    primary_link_boxes: tuple[dict[str, object], ...],
    workspace_mode_box: dict[str, object],
    routes_scroll_width: float,
    routes_client_width: float,
) -> BrowserEvaluation:
    """Require the phone evidence cue to occupy a full row between route links and mode."""

    if not phone_layout:
        return BrowserEvaluation(True, "desktop layout is outside the phone cue-row contract")

    def coordinates(box: dict[str, object]) -> tuple[float, float, float, float] | None:
        try:
            values = tuple(float(box[key]) for key in ("left", "right", "top", "bottom"))
        except (KeyError, TypeError, ValueError):
            return None
        left, right, top, bottom = values
        if right <= left or bottom <= top:
            return None
        return values

    marker = coordinates(marker_box)
    primary = tuple(coordinates(box) for box in primary_link_boxes)
    mode = coordinates(workspace_mode_box)
    primary_valid = len(primary) == primary_link_count and all(box is not None for box in primary)
    no_overflow = routes_scroll_width <= routes_client_width + 1
    positioned = False
    if marker is not None and mode is not None and primary_valid:
        primary_boxes = tuple(box for box in primary if box is not None)
        primary_left = min(box[0] for box in primary_boxes)
        primary_right = max(box[1] for box in primary_boxes)
        primary_bottom = max(box[3] for box in primary_boxes)
        marker_left, marker_right, marker_top, marker_bottom = marker
        positioned = (
            marker_left <= primary_left + 1
            and marker_right >= primary_right - 1
            and marker_top >= primary_bottom + 1
            and marker_bottom <= mode[2] + 1
            and marker_bottom - marker_top >= 44
        )
    passed = marker_count == 1 and primary_link_count == 4 and primary_valid and no_overflow and positioned
    return BrowserEvaluation(
        passed,
        (
            "one Advanced Evidence cue occupies its own full phone row with no route-grid overflow"
            if passed
            else (
                f"marker_count={marker_count}; primary_link_count={primary_link_count}; "
                f"primary_valid={primary_valid}; positioned={positioned}; "
                f"routes_scroll_width={routes_scroll_width}; routes_client_width={routes_client_width}"
            )
        ),
    )


def _http_scheme(url: str) -> str | None:
    value = str(url or "").strip()
    lowered = value.lower()
    if not lowered.startswith(("http:", "https:")):
        return None
    try:
        scheme = urlsplit(value).scheme.lower()
    except ValueError:
        return "https" if lowered.startswith("https:") else "http"
    return scheme if scheme in {"http", "https"} else None


def _canonical_http_origin(url: str) -> tuple[str, str, int] | None:
    try:
        parsed = urlsplit(str(url or "").strip())
        scheme = parsed.scheme.lower()
        host = parsed.hostname
        if scheme not in {"http", "https"} or not host:
            return None
        port = parsed.port
    except (TypeError, ValueError):
        return None
    return (scheme, host.casefold(), port or (443 if scheme == "https" else 80))


def _redacted_http_url(url: str) -> str:
    origin = _canonical_http_origin(str(url or ""))
    if origin is None:
        return "<malformed-http-url>"
    scheme, host, port = origin
    host_display = f"[{host}]" if ":" in host else host
    default_port = 443 if scheme == "https" else 80
    port_suffix = "" if port == default_port else f":{port}"
    return f"{scheme}://{host_display}{port_suffix}"


def _new_http_network_capture() -> dict[str, object]:
    return {
        "http_request_count": 0,
        "external_http_request_count": 0,
        "external_urls": [],
        "_external_origins_seen": set(),
    }


def _record_http_request(
    capture: dict[str, object],
    *,
    url: str,
    expected_origin: tuple[str, str, int],
) -> None:
    if _http_scheme(url) is None:
        return
    capture["http_request_count"] = int(capture["http_request_count"]) + 1
    if _canonical_http_origin(url) == expected_origin:
        return
    capture["external_http_request_count"] = (
        int(capture["external_http_request_count"]) + 1
    )
    origin_evidence = _redacted_http_url(url)
    seen = capture["_external_origins_seen"]
    if not isinstance(seen, set) or origin_evidence in seen:
        return
    seen.add(origin_evidence)
    evidence = capture["external_urls"]
    if isinstance(evidence, list) and len(evidence) < MAX_EXTERNAL_HTTP_URL_EVIDENCE:
        evidence.append(origin_evidence)


def http_network_capture_payload(capture: dict[str, object]) -> dict[str, object]:
    external_urls = [str(value) for value in capture.get("external_urls") or ()]
    external_count = int(capture.get("external_http_request_count") or 0)
    seen = capture.get("_external_origins_seen")
    external_origin_count = (
        len(seen)
        if isinstance(seen, set)
        else int(capture.get("external_origin_count") or len(external_urls))
    )
    return {
        "http_request_count": int(capture.get("http_request_count") or 0),
        "external_http_request_count": external_count,
        "external_origin_count": external_origin_count,
        "external_urls": external_urls,
        "external_urls_truncated": max(
            0, external_origin_count - len(external_urls)
        ),
    }


def evaluate_http_network_capture(network: dict[str, object]) -> BrowserEvaluation:
    external_count = int(network.get("external_http_request_count") or 0)
    external_urls = [str(value) for value in network.get("external_urls") or ()]
    truncated = int(network.get("external_urls_truncated") or 0)
    return BrowserEvaluation(
        external_count == 0,
        (
            f"http_requests={int(network.get('http_request_count') or 0)}; "
            f"external_http_requests={external_count}; "
            f"external_origins={int(network.get('external_origin_count') or 0)}; "
            f"external_urls={external_urls!r}; truncated={truncated}"
        ),
    )


def evaluate_operator_route_contract(
    *,
    slug: str,
    expected_h1: str,
    expected_kind: str,
    h1_count: int,
    h1_text: tuple[str, ...],
    shell_count: int,
    warning_count: int,
    warning_kind: str,
    warning_before_detail: bool,
    detail_count: int,
    stop_rule_count: int,
    topbar_nav_count: int,
    status_region_count: int,
    status_region_labelled: bool,
    profile_trust_count: int,
    profile_trust_display: str,
    profile_trust_item_count: int,
    profile_trust_overlap_count: int,
    shortcut_count: int,
    shortcut_visible_count: int,
    shortcut_width: float,
    shortcut_height: float,
    non_neutral_analytic_count: int,
) -> BrowserEvaluation:
    """Enforce the compact Operator shell without interpreting analytic sentiment."""

    target = evaluate_control_target(width=shortcut_width, height=shortcut_height)
    passed = (
        h1_count == 1
        and h1_text == (expected_h1,)
        and shell_count == 1
        and warning_count == 1
        and warning_kind == expected_kind
        and warning_before_detail
        and detail_count >= 1
        and stop_rule_count == 0
        and topbar_nav_count == 0
        and status_region_count == 1
        and status_region_labelled
        and profile_trust_count == 1
        and profile_trust_display == "grid"
        and profile_trust_item_count == 5
        and profile_trust_overlap_count == 0
        and shortcut_count == 1
        and shortcut_visible_count == 1
        and target.passed
        and non_neutral_analytic_count == 0
    )
    return BrowserEvaluation(
        passed,
        (
            f"route={slug}; h1={h1_text!r} ({h1_count}); shell={shell_count}; "
            f"warning={warning_count}/{warning_kind!r} expected={expected_kind!r}; "
            f"warning_before_detail={warning_before_detail}; details={detail_count}; "
            f"stop_rules={stop_rule_count}; topbar_nav={topbar_nav_count}; "
            f"status_region={status_region_count} labelled={status_region_labelled}; "
            f"profile_trust={profile_trust_count} display={profile_trust_display!r} "
            f"items={profile_trust_item_count} overlaps={profile_trust_overlap_count}; "
            f"shortcut={shortcut_visible_count}/{shortcut_count} {shortcut_width:.1f}x{shortcut_height:.1f}; "
            f"non_neutral_analytic={non_neutral_analytic_count}"
        ),
    )


def evaluate_text_clipping(
    *,
    overflow: str,
    text_overflow: str,
    line_clamp: str,
) -> BrowserEvaluation:
    normalized_overflow = str(overflow or "").strip().casefold()
    normalized_text = str(text_overflow or "").strip().casefold()
    normalized_clamp = str(line_clamp or "").strip().casefold()
    clipped = (
        normalized_overflow in {"hidden", "clip"}
        or normalized_text == "ellipsis"
        or normalized_clamp not in {"", "none", "normal", "0"}
    )
    return BrowserEvaluation(
        not clipped,
        f"overflow={normalized_overflow or 'unset'}; text-overflow={normalized_text or 'unset'}; line-clamp={normalized_clamp or 'unset'}",
    )


def evaluate_skip_focus(
    *,
    skip_count: int,
    focused: bool,
    route_preserved: bool,
    fragment: str,
    active_id: str,
) -> BrowserEvaluation:
    passed = (
        skip_count == 1
        and focused
        and route_preserved
        and fragment == "public-page-answer"
        and active_id == "public-page-answer"
    )
    return BrowserEvaluation(
        passed,
        (
            f"skip_count={skip_count}; focused={focused}; route_preserved={route_preserved}; "
            f"fragment={fragment!r}; active_id={active_id!r}"
        ),
    )


def evaluate_browser_zoom(
    *,
    requested_zoom: int,
    declared_width: float,
    declared_height: float,
    screenshot_width: float,
    screenshot_height: float,
    inner_width: float,
    inner_height: float,
    visual_viewport_width: float,
    visual_viewport_height: float,
    device_pixel_ratio: float,
    visual_viewport_scale: float,
) -> BrowserEvaluation:
    expected_inner_width = declared_width / requested_zoom if requested_zoom > 0 else 0
    expected_inner_height = declared_height / requested_zoom if requested_zoom > 0 else 0
    layout_width_ratio = declared_width / inner_width if inner_width > 0 else 0
    layout_height_ratio = declared_height / inner_height if inner_height > 0 else 0
    passed = (
        requested_zoom in ZOOMS
        and abs(screenshot_width - declared_width) <= 1
        and abs(screenshot_height - declared_height) <= 1
        and abs(inner_width - expected_inner_width) <= 1
        and abs(inner_height - expected_inner_height) <= 1
        and abs(visual_viewport_width - inner_width) <= 1
        and abs(visual_viewport_height - inner_height) <= 1
        and abs(layout_width_ratio - requested_zoom) <= 0.08
        and abs(layout_height_ratio - requested_zoom) <= 0.08
        and abs(device_pixel_ratio - requested_zoom) <= 0.08
        and abs(visual_viewport_scale - 1) <= 0.01
    )
    return BrowserEvaluation(
        passed,
        (
            f"requested={requested_zoom * 100}%; declared={declared_width:.0f}x{declared_height:.0f}; "
            f"screenshot={screenshot_width:.0f}x{screenshot_height:.0f}; "
            f"inner={inner_width:.0f}x{inner_height:.0f}; "
            f"visual={visual_viewport_width:.0f}x{visual_viewport_height:.0f}; "
            f"layout_ratio={layout_width_ratio:.3f}x{layout_height_ratio:.3f}; "
            f"device_pixel_ratio={device_pixel_ratio:.3f}; "
            f"visual_viewport_scale={visual_viewport_scale:.3f}"
        ),
    )


def evaluate_navigation_authority(
    *,
    mode: str,
    public_total: int,
    public_visible: int,
    research_total: int,
    research_visible: int,
    operator_radio_total: int,
    operator_radio_visible: int,
) -> BrowserEvaluation:
    expected = {
        "public": (1, 1, 0, 0, 0, 0),
        "research": (0, 0, 1, 1, 0, 0),
        "operator": (0, 0, 0, 0, 2, 2),
    }
    observed = (
        public_total,
        public_visible,
        research_total,
        research_visible,
        operator_radio_total,
        operator_radio_visible,
    )
    passed = mode in expected and observed == expected[mode]
    return BrowserEvaluation(
        passed,
        (
            f"mode={mode}; public={public_visible}/{public_total}; "
            f"research={research_visible}/{research_total}; "
            f"operator radios={operator_radio_visible}/{operator_radio_total}"
        ),
    )


def evaluate_forced_colors_styles(
    *,
    active: bool,
    focus_outline_style: str,
    focus_outline_width: float,
    state_count: int,
    state_border_width: float,
    state_outline_width: float,
) -> BrowserEvaluation:
    state_affordance_passed = (
        state_count == 0
        or (
            state_count >= 1
            and state_border_width >= 1
            and state_outline_width >= 1
        )
    )
    passed = (
        active
        and str(focus_outline_style).casefold() not in {"", "none"}
        and focus_outline_width >= 3
        and state_affordance_passed
    )
    return BrowserEvaluation(
        passed,
        (
            f"active={active}; focus={focus_outline_width:.1f}px {focus_outline_style}; "
            f"states={state_count}; state border={state_border_width:.1f}px; "
            f"state outline={state_outline_width:.1f}px"
        ),
    )


def evaluate_reduced_motion_styles(
    *,
    active: bool,
    target_count: int,
    max_animation_duration_ms: float,
    max_transition_duration_ms: float,
    max_animation_iterations: float,
    smooth_scroll_count: int,
) -> BrowserEvaluation:
    passed = (
        active
        and target_count >= 1
        and max_animation_duration_ms <= 0.1
        and max_transition_duration_ms <= 0.1
        and max_animation_iterations <= 1
        and smooth_scroll_count == 0
    )
    return BrowserEvaluation(
        passed,
        (
            f"active={active}; targets={target_count}; animation={max_animation_duration_ms:.3f}ms; "
            f"transition={max_transition_duration_ms:.3f}ms; iterations={max_animation_iterations:.1f}; "
            f"smooth_scroll={smooth_scroll_count}"
        ),
    )


def evaluate_focus_sequence(
    *,
    focused_roles: tuple[str, ...],
    region_order: tuple[str, ...],
    outline_widths: tuple[float, ...],
    positive_tabindex_count: int,
) -> BrowserEvaluation:
    required_regions = (
        "workflow-nav",
        "primary-answer",
        "primary-action",
        "stop-rule",
        "supporting-evidence",
        "advanced-detail",
    )
    try:
        navigation_index = focused_roles.index("navigation", 1)
        action_index = focused_roles.index("primary-action", navigation_index + 1)
        advanced_index = focused_roles.index("advanced-detail", action_index + 1)
    except ValueError:
        navigation_index = -1
        action_index = -1
        advanced_index = -1
    tab_order_passed = (
        bool(focused_roles)
        and focused_roles[0] == "skip"
        and 0 < navigation_index < action_index < advanced_index
        and all(role == "navigation" for role in focused_roles[1:action_index])
        and "navigation" not in focused_roles[action_index + 1 : advanced_index]
    )
    try:
        region_indexes = tuple(region_order.index(name) for name in required_regions)
        region_order_passed = all(
            left < right for left, right in zip(region_indexes, region_indexes[1:])
        )
    except ValueError:
        region_order_passed = False
    passed = (
        positive_tabindex_count == 0
        and tab_order_passed
        and region_order_passed
        and len(outline_widths) >= len(focused_roles)
        and all(width >= 3 for width in outline_widths[: len(focused_roles)])
    )
    return BrowserEvaluation(
        passed,
        (
            f"positive_tabindex={positive_tabindex_count}; focused={focused_roles!r}; "
            f"regions={region_order!r}; outlines={outline_widths!r}"
        ),
    )


def evaluate_discover_evidence_access_layout(
    *,
    primary_answer_count: int,
    quick_links: tuple[dict[str, object], ...],
    native_search_count: int,
    stop_rule_count: int,
    supporting_evidence_count: int,
    advanced_detail_count: int,
    dom_order: tuple[str, ...],
    client_width: float,
    location_path: str,
    location_search: str,
    current_page_count: int,
    current_page_label: str,
) -> BrowserEvaluation:
    """Require exact Discover evidence routes around the shared global checks."""

    expected_dom_order = (
        "primary-answer",
        "quick-links",
        "native-search",
        "stop-rule",
        "supporting-evidence",
        "advanced-detail",
    )

    def discover_route_matches(path: object, search: object) -> bool:
        parsed = urlsplit(str(search or ""))
        return (
            str(path or "") == "/"
            and not parsed.scheme
            and not parsed.netloc
            and not parsed.path
            and not parsed.fragment
            and parse_qs(parsed.query, keep_blank_values=True)
            == {"mode": ["research"], "page": ["discover"]}
        )

    observed_links = tuple(dict(link) for link in quick_links)
    tickers: list[str] = []
    links_are_bound = len(observed_links) == 4
    links_are_usable = len(observed_links) == 4
    for link in observed_links:
        label = str(link.get("label") or "").strip()
        href = str(link.get("href") or "").strip()
        label_match = re.fullmatch(
            r"Open ([A-Z0-9][A-Z0-9./-]*) Company Brief",
            label,
        )
        ticker = label_match.group(1) if label_match else ""
        parsed = urlsplit(href)
        query = parse_qs(parsed.query, keep_blank_values=True)
        if (
            not ticker
            or parsed.scheme
            or parsed.netloc
            or parsed.path not in {"", "/"}
            or parsed.fragment
            or query
            != {
                "mode": ["research"],
                "page": ["company-workbench"],
                "ticker": [ticker],
                "open": ["1"],
            }
        ):
            links_are_bound = False
        tickers.append(ticker)
        links_are_usable = links_are_usable and (
            link.get("visible") is True
            and link.get("focusable") is True
            and float(link.get("width") or 0) >= 44
            and float(link.get("height") or 0) >= 44
            and float(link.get("left") or 0) >= -1
            and float(link.get("right") or 0) <= client_width + 1
            and link.get("clipped") is False
        )
    links_are_unique_and_alphabetical = (
        len(tickers) == 4
        and all(tickers)
        and len(set(tickers)) == 4
        and tickers == sorted(tickers, key=str.casefold)
    )

    route_is_stable = discover_route_matches(location_path, location_search)
    current_location_is_stable = (
        current_page_count == 1
        and str(current_page_label or "").strip() == "Discover"
    )
    structure_is_exact = (
        primary_answer_count == 1
        and native_search_count == 1
        and stop_rule_count == 1
        and supporting_evidence_count == 1
        and advanced_detail_count == 1
        and dom_order == expected_dom_order
    )

    passed = (
        links_are_bound
        and links_are_usable
        and links_are_unique_and_alphabetical
        and structure_is_exact
        and route_is_stable
        and current_location_is_stable
    )
    return BrowserEvaluation(
        passed,
        (
            f"quick_link_count={len(observed_links)}; tickers={tickers!r}; "
            f"links_bound={links_are_bound}; links_usable={links_are_usable}; "
            f"unique_alphabetical={links_are_unique_and_alphabetical}; "
            f"structure_exact={structure_is_exact}; dom_order={dom_order!r}; "
            f"route_stable={route_is_stable}; "
            f"current_location_stable={current_location_is_stable}"
        ),
    )


def evaluate_discover_initial_viewport_hierarchy(
    *,
    primary_answer_box: dict[str, object],
    quick_links: tuple[dict[str, object], ...],
    viewport_height: float,
) -> BrowserEvaluation:
    """Require the Discover answer and all four evidence paths to begin in view."""

    primary_top_raw = primary_answer_box.get("top")
    evidence_top_raw = tuple(dict(link).get("top") for link in quick_links)
    coordinates_present = all(
        isinstance(value, (int, float)) and math.isfinite(float(value))
        for value in (primary_top_raw, *evidence_top_raw, viewport_height)
    )
    primary_top = float(primary_top_raw or 0)
    evidence_tops = tuple(float(value or 0) for value in evidence_top_raw)
    passed = (
        len(quick_links) == 4
        and coordinates_present
        and viewport_height > 0
        and -1 <= primary_top <= viewport_height + 1
        and all(-1 <= top <= viewport_height + 1 for top in evidence_tops)
        and all(primary_top <= top for top in evidence_tops)
    )
    return BrowserEvaluation(
        passed,
        (
            f"discover primary_answer_top={primary_top:.1f}; "
            f"evidence_tops={evidence_tops!r}; "
            f"viewport_height={viewport_height:.1f}; "
            f"coordinates_present={coordinates_present}"
        ),
    )


def evaluate_discover_focus_sequence(
    *,
    focused_roles: tuple[str, ...],
    focused_labels: tuple[str, ...],
    outline_widths: tuple[float, ...],
    positive_tabindex_count: int,
) -> BrowserEvaluation:
    """Require Discover's full keyboard path through evidence and native search."""

    evidence_indexes = tuple(
        index for index, role in enumerate(focused_roles) if role == "evidence-path"
    )
    evidence_labels = tuple(
        focused_labels[index]
        for index in evidence_indexes
        if index < len(focused_labels)
    )
    tickers: list[str] = []
    for label in evidence_labels:
        match = re.fullmatch(
            r"Open ([A-Z0-9][A-Z0-9./-]*) Company Brief",
            str(label or "").strip(),
        )
        tickers.append(match.group(1) if match else "")
    ordered_evidence = (
        len(evidence_indexes) == 4
        and evidence_indexes == tuple(range(evidence_indexes[0], evidence_indexes[0] + 4))
        if evidence_indexes
        else False
    )
    evidence_start = evidence_indexes[0] if evidence_indexes else -1
    leading_roles = focused_roles[1:evidence_start] if evidence_start > 0 else ()
    expected_tail = (
        "browse-navigation",
        "primary-action",
        "advanced-detail",
    )
    passed = (
        positive_tabindex_count == 0
        and len(focused_roles) == len(focused_labels) == len(outline_widths)
        and bool(focused_roles)
        and focused_roles[0] == "skip"
        and bool(leading_roles)
        and all(role == "navigation" for role in leading_roles)
        and ordered_evidence
        and focused_roles[evidence_indexes[-1] + 1 :] == expected_tail
        and len(tickers) == 4
        and all(tickers)
        and len(set(tickers)) == 4
        and tickers == sorted(tickers, key=str.casefold)
        and all(width >= 3 for width in outline_widths)
    )
    return BrowserEvaluation(
        passed,
        (
            f"Discover focus positive_tabindex={positive_tabindex_count}; "
            f"roles={focused_roles!r}; evidence-path labels={evidence_labels!r}; "
            f"tickers={tickers!r}; outlines={outline_widths!r}"
        ),
    )


def evaluate_task4_focus_sequence(
    *,
    slug: str,
    focused_roles: tuple[str, ...],
    region_order: tuple[str, ...],
    outline_widths: tuple[float, ...],
    positive_tabindex_count: int,
) -> BrowserEvaluation:
    """Require natural focus order and visible focus across every Task 4 route."""

    supported = {
        "public-home",
        "stock-selector",
        "single-stock-report",
        "public-data-health",
        "public-proof-history",
        "personal-data-health",
        "personal-proof-history",
    }
    if slug not in supported:
        return BrowserEvaluation(False, f"unsupported Task 4 route {slug!r}")
    leading = (
        ("workflow-nav", "context")
        if slug.startswith("personal-")
        else ("context", "workflow-nav")
    )
    required_regions = leading + (
        "page-title",
        "primary-answer",
        "primary-action",
        "stop-rule",
        "supporting-evidence",
        "advanced-detail",
    )
    try:
        region_indexes = tuple(region_order.index(name) for name in required_regions)
        region_order_passed = all(
            left < right for left, right in zip(region_indexes, region_indexes[1:])
        )
    except ValueError:
        region_order_passed = False
    try:
        action_index = focused_roles.index("primary-action")
        advanced_index = focused_roles.index("advanced-detail", action_index + 1)
    except ValueError:
        action_index = -1
        advanced_index = -1
    navigation_before_action = (
        action_index > 1 and "navigation" in focused_roles[1:action_index]
    )
    navigation_after_action = (
        "navigation" in focused_roles[action_index + 1 : advanced_index]
        if action_index >= 0 and advanced_index >= 0
        else True
    )
    passed = (
        positive_tabindex_count == 0
        and bool(focused_roles)
        and focused_roles[0] == "skip"
        and navigation_before_action
        and not navigation_after_action
        and advanced_index > action_index
        and region_order_passed
        and len(outline_widths) >= len(focused_roles)
        and all(width >= 3 for width in outline_widths[: len(focused_roles)])
    )
    return BrowserEvaluation(
        passed,
        (
            f"route={slug}; positive_tabindex={positive_tabindex_count}; "
            f"focused={focused_roles!r}; regions={region_order!r}; outlines={outline_widths!r}"
        ),
    )


def evaluate_personal_route_hierarchy(
    *,
    slug: str,
    region_counts: dict[str, int],
    region_order: tuple[str, ...],
    visible_region_counts: dict[str, int],
    visible_region_order: tuple[str, ...],
    primary_action_focusable_count: int,
    legacy_pre_answer_action_count: int,
) -> BrowserEvaluation:
    """Require one answer-first hierarchy for a modernized personal route."""

    if slug not in {"research-desk", "discover", "company-workbench", "monitor"}:
        return BrowserEvaluation(False, f"unsupported personal route {slug!r}")
    required = (
        "workflow-nav",
        "context",
        "page-title",
        "primary-answer",
        "primary-action",
        "stop-rule",
        "advanced-detail",
    )
    required_counts_passed = all(int(region_counts.get(name, 0)) == 1 for name in required)
    supporting_count = int(region_counts.get("supporting-evidence", 0))
    supporting_count_passed = (
        supporting_count == 1 if slug == "research-desk" else supporting_count in {0, 1}
    )
    try:
        indexes = {name: region_order.index(name) for name in required}
        required_order_passed = all(
            indexes[left] < indexes[right]
            for left, right in zip(required, required[1:])
        )
        supporting_order_passed = (
            supporting_count == 0
            or indexes["stop-rule"]
            < region_order.index("supporting-evidence")
            < indexes["advanced-detail"]
        )
    except ValueError:
        required_order_passed = False
        supporting_order_passed = False
    visible_required_counts_passed = all(
        int(visible_region_counts.get(name, 0)) == 1 for name in required
    )
    visible_supporting_count = int(
        visible_region_counts.get("supporting-evidence", 0)
    )
    visible_supporting_count_passed = visible_supporting_count == supporting_count
    try:
        visible_indexes = {
            name: visible_region_order.index(name) for name in required
        }
        visible_required_order_passed = all(
            visible_indexes[left] < visible_indexes[right]
            for left, right in zip(required, required[1:])
        )
        visible_supporting_order_passed = (
            visible_supporting_count == 0
            or visible_indexes["stop-rule"]
            < visible_region_order.index("supporting-evidence")
            < visible_indexes["advanced-detail"]
        )
    except ValueError:
        visible_required_order_passed = False
        visible_supporting_order_passed = False
    passed = (
        required_counts_passed
        and supporting_count_passed
        and required_order_passed
        and supporting_order_passed
        and visible_required_counts_passed
        and visible_supporting_count_passed
        and visible_required_order_passed
        and visible_supporting_order_passed
        and primary_action_focusable_count == 1
        and legacy_pre_answer_action_count == 0
    )
    return BrowserEvaluation(
        passed,
        (
            f"route={slug}; counts={region_counts!r}; order={region_order!r}; "
            f"visible_counts={visible_region_counts!r}; visible_order={visible_region_order!r}; "
            f"supporting_count={supporting_count}; visible_supporting_count={visible_supporting_count}; "
            f"primary_action_focusable_count={primary_action_focusable_count}; "
            f"legacy_pre_answer_action_count={legacy_pre_answer_action_count}"
        ),
    )


def evaluate_task4_route_hierarchy(
    *,
    slug: str,
    region_counts: dict[str, int],
    region_order: tuple[str, ...],
    visible_region_counts: dict[str, int],
    visible_region_order: tuple[str, ...],
    primary_action_focusable_count: int,
    legacy_pre_answer_action_count: int,
) -> BrowserEvaluation:
    """Require one ordered shared-region contract on Task 4 routes."""

    supported = {
        "public-home",
        "stock-selector",
        "single-stock-report",
        "public-data-health",
        "public-proof-history",
        "personal-data-health",
        "personal-proof-history",
    }
    if slug not in supported:
        return BrowserEvaluation(False, f"unsupported Task 4 route {slug!r}")
    leading = (
        ("workflow-nav", "context")
        if slug.startswith("personal-")
        else ("context", "workflow-nav")
    )
    required = leading + (
        "page-title",
        "primary-answer",
        "primary-action",
        "stop-rule",
        "supporting-evidence",
        "advanced-detail",
    )
    exact_counts = all(int(region_counts.get(name, 0)) == 1 for name in required)
    visible_exact_counts = all(
        int(visible_region_counts.get(name, 0)) == 1 for name in required
    )

    def ordered(sequence: tuple[str, ...]) -> bool:
        try:
            indexes = tuple(sequence.index(name) for name in required)
        except ValueError:
            return False
        return all(left < right for left, right in zip(indexes, indexes[1:]))

    raw_ordered = ordered(region_order)
    visible_ordered = ordered(visible_region_order)
    passed = (
        exact_counts
        and visible_exact_counts
        and raw_ordered
        and visible_ordered
        and primary_action_focusable_count == 1
        and legacy_pre_answer_action_count == 0
    )
    return BrowserEvaluation(
        passed,
        (
            f"route={slug}; counts={region_counts!r}; order={region_order!r}; "
            f"visible_counts={visible_region_counts!r}; visible_order={visible_region_order!r}; "
            f"primary_action_focusable_count={primary_action_focusable_count}; "
            f"legacy_pre_answer_action_count={legacy_pre_answer_action_count}"
        ),
    )


def evaluate_initial_scroll(
    *,
    window_scroll_x: float,
    window_scroll_y: float,
    document_scroll_left: float,
    document_scroll_top: float,
    main_scroll_left: float,
    main_scroll_top: float,
    public_app_nav_scroll_left: float,
    research_workflow_nav_scroll_left: float,
    research_workflow_nav_scroll_top: float,
) -> BrowserEvaluation:
    """Require an unscrolled initial viewport before geometry and screenshot proof."""

    values = {
        "window": (window_scroll_x, window_scroll_y),
        "document": (document_scroll_left, document_scroll_top),
        "main": (main_scroll_left, main_scroll_top),
        "public-app-nav": (public_app_nav_scroll_left,),
        "research-workflow-nav": (
            research_workflow_nav_scroll_left,
            research_workflow_nav_scroll_top,
        ),
    }
    passed = all(abs(value) <= 1 for pair in values.values() for value in pair)
    return BrowserEvaluation(passed, f"scroll origins={values!r}")


def evaluate_initial_viewport_hierarchy(
    *,
    region_boxes: dict[str, dict[str, object]],
    viewport_height: float,
    require_complete: bool,
) -> BrowserEvaluation:
    """Require critical route regions to begin on-screen at the true scroll origin."""

    required = ("primary-answer", "primary-action", "stop-rule")
    missing = tuple(name for name in required if name not in region_boxes)
    if missing:
        return BrowserEvaluation(False, f"missing critical regions={missing!r}")
    tops = {
        name: float(region_boxes[name].get("top") or 0)
        for name in required
    }
    bottoms = {
        name: float(region_boxes[name].get("bottom") or 0)
        for name in required
    }
    starts_visible = all(-1 <= top <= viewport_height + 1 for top in tops.values())
    complete = (
        all(bottom <= viewport_height + 1 for bottom in bottoms.values())
        if require_complete
        else True
    )
    return BrowserEvaluation(
        starts_visible and complete,
        (
            f"viewport_height={viewport_height:.0f}; require_complete={require_complete}; "
            f"tops={tops!r}; bottoms={bottoms!r}"
        ),
    )


def evaluate_public_home_geometry(
    *,
    viewport_width: float,
    viewport_height: float,
    zoom: int,
    phone_layout: bool,
    action_left: float,
    action_right: float,
    action_top: float,
    action_bottom: float,
    stop_top: float,
    stop_bottom: float,
    metrics_top: float,
    metrics_bottom: float,
    metrics_left: float,
    metrics_right: float,
) -> BrowserEvaluation:
    """Verify the desktop grid exception without changing phone source order."""

    if not phone_layout:
        columns_separate = (
            action_right <= metrics_left + 1
            or metrics_right <= action_left + 1
        )
        passed = (
            abs(action_top - metrics_top) <= 8
            and max(action_bottom, metrics_bottom) <= stop_top + 1
            and columns_separate
        )
        expected = "desktop separate action/metrics columns before stop"
    else:
        passed = (
            action_bottom <= stop_top + 1
            and stop_bottom <= metrics_top + 1
            and (zoom != 1 or stop_bottom <= viewport_height + 1)
        )
        expected = "phone action before complete stop before metrics"
    return BrowserEvaluation(
        passed,
        (
            f"{expected}; viewport={viewport_width:.0f}x{viewport_height:.0f}; zoom={zoom}; "
            f"phone_layout={phone_layout}; action={action_left:.1f}..{action_right:.1f} x "
            f"{action_top:.1f}..{action_bottom:.1f}; stop_top={stop_top:.1f}; "
            f"metrics={metrics_left:.1f}..{metrics_right:.1f} x {metrics_top:.1f}..{metrics_bottom:.1f}"
        ),
    )


def _parse_unique(raw: str, *, allowed: tuple[str, ...], label: str) -> tuple[str, ...]:
    values = tuple(value.strip() for value in str(raw or "").split(",") if value.strip())
    if not values:
        raise ValueError(f"{label} requires at least one value")
    if len(values) != len(set(values)):
        raise ValueError(f"{label} cannot contain duplicate values")
    unknown = tuple(value for value in values if value not in allowed)
    if unknown:
        raise ValueError(f"unknown {label}: {', '.join(unknown)}")
    return values


def parse_routes(raw: str) -> tuple[WorkspaceVisualRoute, ...]:
    slugs = _parse_unique(raw, allowed=tuple(_ROUTES_BY_SLUG), label="route")
    return tuple(_ROUTES_BY_SLUG[slug] for slug in slugs)


def parse_viewports(raw: str) -> tuple[tuple[int, int], ...]:
    allowed = tuple(f"{width}x{height}" for width, height in VIEWPORTS)
    values = _parse_unique(raw, allowed=allowed, label="viewport")
    return tuple(tuple(int(part) for part in value.split("x", 1)) for value in values)  # type: ignore[return-value]


def parse_zooms(raw: str) -> tuple[int, ...]:
    values = _parse_unique(raw, allowed=tuple(str(value) for value in ZOOMS), label="zoom")
    return tuple(int(value) for value in values)


def prepare_output_dir(output_dir: Path | str) -> Path:
    requested = Path(output_dir).expanduser()
    resolved = requested.resolve()
    tmp_root = Path("/tmp").resolve()
    try:
        resolved.relative_to(tmp_root)
    except ValueError as exc:
        raise ValueError("output directory must resolve under /tmp") from exc
    if resolved.exists():
        if not resolved.is_dir():
            raise ValueError("output directory must be a directory")
        if any(resolved.iterdir()):
            raise ValueError("output directory must not already contain files")
    else:
        resolved.mkdir(parents=True)
    return resolved


def structured_geometry(observation: dict[str, object]) -> dict[str, object]:
    """Return literal, machine-readable geometry without recomputing UI meaning."""

    def number(key: str) -> float:
        return float(observation.get(key) or 0)

    return {
        "viewport": {
            "client_width": number("client_width"),
            "client_height": number("client_height"),
            "visual_width": number("visual_viewport_width"),
            "visual_height": number("visual_viewport_height"),
            "screenshot_width": number("screenshot_width"),
            "screenshot_height": number("screenshot_height"),
        },
        "scroll_widths": {
            "document": number("document_scroll_width"),
            "body": number("body_scroll_width"),
            "main": number("main_scroll_width"),
            "main_client": number("main_client_width"),
        },
        "scroll_origins": {
            "window": [number("scroll_x"), number("scroll_y")],
            "document": [
                number("document_scroll_left"),
                number("document_scroll_top"),
            ],
            "main": [number("main_scroll_left"), number("main_scroll_top")],
            "public_workflow": [number("public_app_nav_scroll_left")],
            "personal_workflow": [
                number("research_workflow_nav_scroll_left"),
                number("research_workflow_nav_scroll_top"),
            ],
        },
        "regions": [dict(row) for row in observation.get("regions") or ()],
        "controls": [dict(row) for row in observation.get("controls") or ()],
    }


def _cell_identity(result: dict[str, object]) -> tuple[str, str, int]:
    return (
        str(result.get("route") or ""),
        str(result.get("viewport") or ""),
        int(result.get("zoom") or 0),
    )


def evaluate_full_matrix_coverage(
    results: list[dict[str, object]],
) -> dict[str, object]:
    """Characterize exact ordered coverage of the specification's 90 cells."""

    expected = [
        (route.slug, f"{width}x{height}", zoom)
        for route in ROUTE_FIXTURES
        for width, height in VIEWPORTS
        for zoom in ZOOMS
    ]
    observed = [_cell_identity(result) for result in results]
    expected_set = set(expected)
    observed_set = set(observed)

    def label(cell: tuple[str, str, int]) -> str:
        return f"{cell[0]} {cell[1]} zoom={cell[2]}"

    missing = [label(cell) for cell in expected if cell not in observed_set]
    unexpected = [label(cell) for cell in observed if cell not in expected_set]
    ordered = observed == expected
    full_matrix = (
        ordered
        and len(observed) == len(expected)
        and not missing
        and not unexpected
    )
    return {
        "full_matrix": full_matrix,
        "expected_cells": len(expected),
        "observed_cells": len(observed),
        "missing_cells": missing,
        "unexpected_cells": unexpected,
        "ordered": ordered,
    }


def _source_snapshot(root: Path) -> dict[str, object]:
    """Bind browser evidence to HEAD plus the bounded set of worktree changes."""

    changes: dict[str, str] = {}
    try:
        tracked = subprocess.check_output(
            ["git", "diff", "--name-status", "--no-renames", "HEAD", "--"],
            cwd=root,
            text=True,
            stderr=subprocess.DEVNULL,
        )
        for line in tracked.splitlines():
            state, separator, relative = line.partition("\t")
            if separator and relative:
                changes[relative] = state.strip() or "M"
        untracked = subprocess.check_output(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=root,
            text=True,
            stderr=subprocess.DEVNULL,
        )
        for relative in untracked.splitlines():
            if relative:
                changes.setdefault(relative, "?")
    except (OSError, subprocess.CalledProcessError):
        return {
            "scope": "bounded_worktree",
            "commit": _git_commit(root),
            "state": "unknown",
            "changes": [],
        }

    entries: list[dict[str, str]] = []
    for relative, state in sorted(changes.items()):
        path = root / relative
        if path.is_symlink():
            digest = hashlib.sha256(os.readlink(path).encode("utf-8")).hexdigest()
        elif path.is_file():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        else:
            digest = "missing"
        entries.append({"path": relative, "state": state, "sha256": digest})
    return {
        "scope": "bounded_worktree",
        "commit": _git_commit(root),
        "state": "working_tree" if entries else "exact_head",
        "changes": entries,
    }


def evaluate_source_snapshot(snapshot: dict[str, object]) -> BrowserEvaluation:
    """Require attributable HEAD identity and complete per-change digests."""

    commit = str(snapshot.get("commit") or "")
    state = str(snapshot.get("state") or "")
    changes = snapshot.get("changes")
    commit_valid = len(commit) == 40 and all(
        character in "0123456789abcdefABCDEF" for character in commit
    )
    changes_valid = isinstance(changes, list)
    if changes_valid:
        for entry in changes:
            if not isinstance(entry, dict):
                changes_valid = False
                break
            digest = str(entry.get("sha256") or "")
            digest_valid = digest == "missing" or (
                len(digest) == 64
                and all(
                    character in "0123456789abcdefABCDEF" for character in digest
                )
            )
            if not str(entry.get("path") or "") or not str(entry.get("state") or "") or not digest_valid:
                changes_valid = False
                break
    state_matches_changes = (
        (state == "exact_head" and changes == [])
        or (state == "working_tree" and isinstance(changes, list) and bool(changes))
    )
    passed = (
        snapshot.get("scope") == "bounded_worktree"
        and state in {"exact_head", "working_tree"}
        and commit_valid
        and changes_valid
        and state_matches_changes
    )
    return BrowserEvaluation(
        passed,
        (
            f"scope={snapshot.get('scope')!r}; state={state!r}; "
            f"commit_valid={commit_valid}; change_digests_valid={changes_valid}; "
            f"state_matches_changes={state_matches_changes}"
        ),
    )


def _git_commit(root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def apply_final_runtime_observation(
    observation: dict[str, object],
    final_runtime: dict[str, object],
) -> dict[str, object]:
    """Preserve initial geometry while replacing the final runtime-only fields."""

    merged = dict(observation)
    for field in ("app_state", "traceback_visible", "spinner_count"):
        merged[field] = final_runtime.get(field)
    return merged


def runtime_capture_payload(
    observation: dict[str, object],
    console_errors: tuple[str, ...],
) -> dict[str, object]:
    return {
        "app_state": str(observation.get("app_state") or ""),
        "traceback_visible": observation.get("traceback_visible") is True,
        "spinner_count": int(observation.get("spinner_count") or 0),
        "console_errors": list(console_errors),
    }


def finalize_runtime_check(
    checks: list[dict[str, object]],
    runtime: dict[str, object],
) -> list[dict[str, object]]:
    """Bind the runtime check to the same post-context payload that is serialized."""

    evaluation = evaluate_runtime_capture(
        app_state=str(runtime.get("app_state") or ""),
        traceback_visible=runtime.get("traceback_visible") is True,
        spinner_count=int(runtime.get("spinner_count") or 0),
        console_errors=tuple(
            str(value) for value in runtime.get("console_errors") or ()
        ),
    )
    final_check = {
        "name": "idle_runtime_without_errors",
        "passed": evaluation.passed,
        "detail": evaluation.detail,
    }
    replaced = False
    finalized: list[dict[str, object]] = []
    for check in checks:
        if check.get("name") == "idle_runtime_without_errors":
            finalized.append(final_check)
            replaced = True
        else:
            finalized.append(check)
    if not replaced:
        finalized.append(final_check)
    return finalized


def finalize_http_network_check(
    checks: list[dict[str, object]],
    network: dict[str, object],
) -> list[dict[str, object]]:
    """Bind network truth to the post-context request capture."""

    evaluation = evaluate_http_network_capture(network)
    final_check = {
        "name": "no_external_http_requests",
        "passed": evaluation.passed,
        "detail": evaluation.detail,
    }
    finalized = [
        check
        for check in checks
        if check.get("name") != "no_external_http_requests"
    ]
    finalized.append(final_check)
    return finalized


def _http_network_log(network: dict[str, object]) -> str:
    evaluation = evaluate_http_network_capture(network)
    return "Browser HTTP request evidence: " + evaluation.detail


def _runtime_observation(page: Any) -> dict[str, object]:
    return page.evaluate(
        """
() => ({
  app_state: document.querySelector('[data-testid="stApp"]')
    ?.getAttribute("data-test-script-state") || "",
  traceback_visible: document.body.innerText.includes("Traceback (most recent call last)"),
  spinner_count: document.querySelectorAll("[data-testid='stSpinner']").length,
})
"""
    )


def _browser_observation(page: Any) -> dict[str, object]:
    return page.evaluate(
        """
() => {
  const visible = (node) => {
    if (!node) return false;
    const box = node.getBoundingClientRect();
    const style = getComputedStyle(node);
    return box.width > 0 && box.height > 0 &&
      style.display !== "none" && style.visibility !== "hidden";
  };
  const boxes = (selector) => [...document.querySelectorAll(selector)]
    .filter(visible)
    .map((node) => {
      const box = node.getBoundingClientRect();
      return {
        name: node.getAttribute("data-sr-region") || node.textContent.trim().slice(0, 60),
        left: box.left,
        right: box.right,
        top: box.top,
        bottom: box.bottom,
        width: box.width,
        height: box.height,
      };
    });
  const nativePrimaryAction = [...document.querySelectorAll("[data-testid='stTextInput']")]
    .find((node) =>
      node.innerText.includes("Search saved companies") ||
      node.innerText.includes("Search this review queue")
    )
    ?.querySelector("input") || null;
  const homeActionArea = document.querySelector(".public-home-primary");
  const boxFor = (node, name) => {
    const box = node.getBoundingClientRect();
    return {
      name,
      left: box.left,
      right: box.right,
      top: box.top,
      bottom: box.bottom,
      width: box.width,
      height: box.height,
    };
  };
  const textNodes = [...document.querySelectorAll(
    "h1, nav a, nav [aria-disabled='true'], label, .sr-status-chip, " +
    ".command-top-link, [data-sr-region='primary-action'], [data-sr-region='stop-rule']"
  )].filter(visible).map((node) => {
    const style = getComputedStyle(node);
    return {
      text: node.textContent.trim().slice(0, 80),
      overflow: style.overflow,
      text_overflow: style.textOverflow,
      line_clamp: style.webkitLineClamp,
    };
  });
  const controls = boxes(
    "nav a, .command-top-link, [data-sr-region='primary-action'], [data-testid='stLinkButton'] a[kind='primary'], " +
    "[data-testid='stButton'] button[kind='primary'], " +
    "[data-testid='stSidebar'] [role='radiogroup'] label"
  );
  if (nativePrimaryAction && visible(nativePrimaryAction)) {
    controls.push(boxFor(nativePrimaryAction, "primary-action"));
  }
  const main = document.querySelector("[data-testid='stMain']") || document.querySelector("[role='main']");
  const publicAppNav = document.querySelector(".public-app-nav");
  const researchWorkflowNav = document.querySelector(".research-workflow-navigation");
  const doc = document.documentElement;
  const body = document.body;
  const navigationLinkMetrics = (nav, links) => {
    const navBox = nav ? nav.getBoundingClientRect() : null;
    const visibleLinks = links.filter(visible);
    const fullyVisibleLinks = visibleLinks.filter((node) => {
      const box = node.getBoundingClientRect();
      return Boolean(
        navBox &&
        box.left >= Math.max(0, navBox.left) - 1 &&
        box.right <= Math.min(doc.clientWidth, navBox.right) + 1
      );
    });
    return {
      total: links.length,
      visible: visibleLinks.length,
      fully_visible: fullyVisibleLinks.length,
      scroll_width: nav ? nav.scrollWidth : 0,
      client_width: nav ? nav.clientWidth : 0,
    };
  };
  const publicNavLinkMetrics = navigationLinkMetrics(
    publicAppNav,
    [...document.querySelectorAll(".public-app-nav a")]
  );
  const researchNavLinkMetrics = navigationLinkMetrics(
    researchWorkflowNav,
    [...document.querySelectorAll(
      ".research-workflow-routes .research-workflow-link, " +
      ".research-workflow-routes .research-workflow-disabled"
    )]
  );
  const proofTimelineRecords = [...document.querySelectorAll(".public-proof-timeline .sr-timeline-record")];
  const proofTimelineSummary = document.querySelector(".public-proof-timeline-summary");
  const regions = boxes("[data-sr-region]");
  if (nativePrimaryAction && visible(nativePrimaryAction)) {
    regions.push(boxFor(nativePrimaryAction, "primary-action"));
  }
  const publicNavs = [...document.querySelectorAll("nav[aria-label='Public workflow']")];
  const researchNavs = [...document.querySelectorAll("nav[aria-label='Personal research workflow']")];
  const workbenchNavigationShells = [...document.querySelectorAll(".research-workflow-navigation")];
  const workbenchBriefs = [...document.querySelectorAll(".company-workbench-primary-brief")];
  const visibleWorkbenchBriefs = workbenchBriefs.filter(visible);
  const firstWorkbenchBrief = visibleWorkbenchBriefs[0] || null;
  const workbenchDisplayTitles = [...document.querySelectorAll(
    ".company-workbench-primary-heading h2"
  )].filter(visible);
  const workbenchAsides = [...document.querySelectorAll(
    "aside.company-workbench-evidence-status[aria-label]"
  )];
  const visibleWorkbenchAsides = workbenchAsides.filter(visible);
  const firstWorkbenchAside = visibleWorkbenchAsides[0] || null;
  const workbenchEvidenceLanes = firstWorkbenchAside
    ? [...firstWorkbenchAside.querySelectorAll(".company-workbench-evidence-lane")].filter(visible)
    : [];
  const workbenchPrimaryActions = firstWorkbenchBrief
    ? [...firstWorkbenchBrief.querySelectorAll("a.public-primary-action")].filter(visible)
    : [];
  const workbenchModuleGates = [...document.querySelectorAll("button")]
    .filter((node) => node.textContent.trim() === "Open evidence and analysis modules")
    .filter(visible);
  const firstWorkbenchPrimaryActionBox = workbenchPrimaryActions[0]
    ? workbenchPrimaryActions[0].getBoundingClientRect()
    : null;
  const workbenchBriefLaneBoxes = firstWorkbenchBrief
    ? [...firstWorkbenchBrief.querySelectorAll(".company-workbench-primary-answer")]
      .filter(visible)
      .map((node) => boxFor(node, node.getAttribute("data-workbench-lane") || "lane"))
    : [];
  const evidenceCurrentMarkers = [...document.querySelectorAll(
    ".research-workflow-evidence-current"
  )].filter(visible);
  const evidenceCurrent = evidenceCurrentMarkers[0] || null;
  const evidenceLabel = evidenceCurrent?.querySelector("span") || null;
  const evidenceCurrentText = evidenceCurrent?.querySelector("strong[aria-current='page']") || null;
  const evidenceNavigation = evidenceCurrent?.closest(".research-workflow-navigation") || null;
  const researchRouteGrid = document.querySelector(".research-workflow-routes");
  const primaryResearchLinks = [...document.querySelectorAll(
    ".research-workflow-routes .research-workflow-link"
  )].filter(visible);
  const workspaceMode = document.querySelector(".research-workspace-mode");
  const operatorRadios = [...document.querySelectorAll("[data-testid='stSidebar'] [role='radiogroup']")];
  const operatorShells = [...document.querySelectorAll("[role='main'] .sr-operator-route-shell")];
  const operatorWarnings = [...document.querySelectorAll("[role='main'] .sr-operator-warning")];
  const operatorDetails = [...document.querySelectorAll(
    "[role='main'] .section-shell, [role='main'] .signal-card, " +
    "[role='main'] .notice-card, [role='main'] [data-testid='stDataFrame']"
  )].filter(visible);
  const commandTopbarNavs = [...document.querySelectorAll("nav.command-topbar")];
  const commandStatusRegions = [...document.querySelectorAll(
    ".command-topbar[role='region'][aria-label]"
  )];
  const commandTopLinks = [...document.querySelectorAll(".command-top-link")];
  const visibleCommandTopLinks = commandTopLinks.filter(visible);
  const firstCommandTopLink = visibleCommandTopLinks[0] || null;
  const firstCommandTopLinkBox = firstCommandTopLink
    ? firstCommandTopLink.getBoundingClientRect()
    : null;
  const profileTrustStrips = [...document.querySelectorAll(".profile-trust-strip.compact")];
  const visibleProfileTrustStrips = profileTrustStrips.filter(visible);
  const firstProfileTrust = visibleProfileTrustStrips[0] || null;
  const profileTrustItems = firstProfileTrust
    ? [...firstProfileTrust.children].filter(visible)
    : [];
  const profileTrustBoxes = profileTrustItems.map((node) => node.getBoundingClientRect());
  let profileTrustOverlapCount = 0;
  for (let leftIndex = 0; leftIndex < profileTrustBoxes.length; leftIndex += 1) {
    for (let rightIndex = leftIndex + 1; rightIndex < profileTrustBoxes.length; rightIndex += 1) {
      const left = profileTrustBoxes[leftIndex];
      const right = profileTrustBoxes[rightIndex];
      const horizontalOverlap = Math.min(left.right, right.right) - Math.max(left.left, right.left);
      const verticalOverlap = Math.min(left.bottom, right.bottom) - Math.max(left.top, right.top);
      if (horizontalOverlap > 1 && verticalOverlap > 1) profileTrustOverlapCount += 1;
    }
  }
  const analyticStates = [...document.querySelectorAll(
    "[data-sr-role='analytic'], [data-sr-role='legacy']"
  )];
  const nonNeutralAnalyticStates = analyticStates.filter(
    (node) => node.getAttribute("data-sr-semantic") !== "neutral"
  );
  const firstOperatorWarning = operatorWarnings.find(visible) || null;
  const firstOperatorDetail = operatorDetails[0] || null;
  const operatorWarningBeforeDetail = Boolean(
    firstOperatorWarning &&
    firstOperatorDetail &&
    (firstOperatorWarning.compareDocumentPosition(firstOperatorDetail) & Node.DOCUMENT_POSITION_FOLLOWING)
  );
  const legacyPreAnswerActions = [
    ...document.querySelectorAll(".research-workspace-action")
  ].filter(visible);
  const regionCounts = {};
  const visibleRegionCounts = {};
  for (const region of document.querySelectorAll("[data-sr-region]")) {
    const name = region.getAttribute("data-sr-region");
    regionCounts[name] = (regionCounts[name] || 0) + 1;
    if (visible(region)) {
      visibleRegionCounts[name] = (visibleRegionCounts[name] || 0) + 1;
    }
  }
  if (nativePrimaryAction) {
    regionCounts["primary-action"] = (regionCounts["primary-action"] || 0) + 1;
  }
  if (nativePrimaryAction && visible(nativePrimaryAction)) {
    visibleRegionCounts["primary-action"] = (visibleRegionCounts["primary-action"] || 0) + 1;
  }
  const regionNodes = [...document.querySelectorAll("[data-sr-region]")]
    .map((node) => ({node, name: node.getAttribute("data-sr-region")}));
  if (nativePrimaryAction) {
    regionNodes.push({node: nativePrimaryAction, name: "primary-action"});
  }
  regionNodes.sort((left, right) => {
    if (left.node === right.node) return 0;
    return left.node.compareDocumentPosition(right.node) & Node.DOCUMENT_POSITION_FOLLOWING
      ? -1
      : 1;
  });
  const visibleRegionNodes = regionNodes.filter((entry) => visible(entry.node));
  const primaryActionNodes = [
    ...document.querySelectorAll("[data-sr-region='primary-action']"),
    ...(nativePrimaryAction && visible(nativePrimaryAction) ? [nativePrimaryAction] : []),
  ];
  const primaryActionFocusableCount = primaryActionNodes.filter((node) => {
    if (!visible(node) || node.matches("[disabled], [aria-disabled='true']")) return false;
    if (node.tabIndex < 0) return false;
    return node.matches("a[href], button, input, select, textarea, summary");
  }).length;
  const overflowNodes = [...document.querySelectorAll("[role='main'] *")]
    .filter(visible)
    .map((node) => {
      const box = node.getBoundingClientRect();
      return {
        tag: node.tagName.toLowerCase(),
        class_name: String(node.className || "").slice(0, 120),
        test_id: node.getAttribute("data-testid") || "",
        left: box.left,
        right: box.right,
        width: box.width,
        client_width: node.clientWidth,
        scroll_width: node.scrollWidth,
      };
    })
    .filter((row) => row.right > doc.clientWidth + 1 || row.scroll_width > row.client_width + 1)
    .slice(0, 12);
  return {
    client_width: doc.clientWidth,
    client_height: doc.clientHeight,
    document_scroll_width: doc.scrollWidth,
    body_scroll_width: body.scrollWidth,
    main_scroll_width: main ? main.scrollWidth : null,
    main_client_width: main ? main.clientWidth : null,
    regions,
    region_counts: regionCounts,
    text_nodes: textNodes,
    controls,
    inner_width: window.innerWidth,
    inner_height: window.innerHeight,
    outer_width: window.outerWidth,
    outer_height: window.outerHeight,
    device_pixel_ratio: window.devicePixelRatio,
    visual_viewport_scale: window.visualViewport ? window.visualViewport.scale : null,
    visual_viewport_width: window.visualViewport ? window.visualViewport.width : null,
    visual_viewport_height: window.visualViewport ? window.visualViewport.height : null,
    scroll_x: window.scrollX,
    scroll_y: window.scrollY,
    document_scroll_left: document.scrollingElement ? document.scrollingElement.scrollLeft : 0,
    document_scroll_top: document.scrollingElement ? document.scrollingElement.scrollTop : 0,
    main_scroll_left: main ? main.scrollLeft : 0,
    main_scroll_top: main ? main.scrollTop : 0,
    public_app_nav_scroll_left: publicAppNav ? publicAppNav.scrollLeft : 0,
    research_workflow_nav_scroll_left: researchWorkflowNav ? researchWorkflowNav.scrollLeft : 0,
    research_workflow_nav_scroll_top: researchWorkflowNav ? researchWorkflowNav.scrollTop : 0,
    public_nav_link_count: publicNavLinkMetrics.total,
    public_nav_link_visible_count: publicNavLinkMetrics.visible,
    public_nav_link_fully_visible_count: publicNavLinkMetrics.fully_visible,
    public_nav_scroll_width: publicNavLinkMetrics.scroll_width,
    public_nav_client_width: publicNavLinkMetrics.client_width,
    research_nav_link_count: researchNavLinkMetrics.total,
    research_nav_link_visible_count: researchNavLinkMetrics.visible,
    research_nav_link_fully_visible_count: researchNavLinkMetrics.fully_visible,
    research_nav_scroll_width: researchNavLinkMetrics.scroll_width,
    research_nav_client_width: researchNavLinkMetrics.client_width,
    proof_timeline_record_count: proofTimelineRecords.length,
    proof_timeline_summary: proofTimelineSummary ? proofTimelineSummary.textContent.trim() : "",
    app_state: document.querySelector('[data-testid="stApp"]')
      ?.getAttribute("data-test-script-state") || "",
    home_action_area: homeActionArea && visible(homeActionArea)
      ? boxFor(homeActionArea, "home-action-area")
      : null,
    phone_media_matches: matchMedia("(max-width: 640px)").matches,
    h1_count: document.querySelectorAll("[role='main'] h1").length,
    h1_text: [...document.querySelectorAll("[role='main'] h1")].map((node) => node.textContent.trim()),
    public_nav_count: publicNavs.length,
    public_nav_visible_count: publicNavs.filter(visible).length,
    research_nav_count: researchNavs.length,
    research_nav_visible_count: researchNavs.filter(visible).length,
    workbench_navigation_count: workbenchNavigationShells.length,
    workbench_navigation_labelled_count: workbenchNavigationShells.filter(
      (node) => Boolean(node.getAttribute("aria-label")?.trim())
    ).length,
    workbench_brief_count: workbenchBriefs.length,
    workbench_brief_visible_count: visibleWorkbenchBriefs.length,
    workbench_brief_labelled_count: workbenchBriefs.filter(
      (node) => Boolean(node.getAttribute("aria-label")?.trim())
    ).length,
    workbench_display_title_count: workbenchDisplayTitles.length,
    workbench_display_title_text: workbenchDisplayTitles.length === 1
      ? workbenchDisplayTitles[0].textContent.trim()
      : "",
    workbench_aside_count: workbenchAsides.length,
    workbench_aside_visible_count: visibleWorkbenchAsides.length,
    workbench_aside_labelled_count: workbenchAsides.filter(
      (node) => Boolean(node.getAttribute("aria-label")?.trim())
    ).length,
    workbench_evidence_lane_count: workbenchEvidenceLanes.length,
    workbench_primary_answer_count: firstWorkbenchBrief
      ? [...firstWorkbenchBrief.querySelectorAll(".company-workbench-primary-answer")].filter(visible).length
      : 0,
    workbench_busy_loading_count: document.querySelectorAll("[aria-busy='true']").length,
    evidence_current_marker_count: evidenceCurrentMarkers.length,
    evidence_current_label_color: evidenceLabel ? getComputedStyle(evidenceLabel).color : "",
    evidence_current_text_color: evidenceCurrentText ? getComputedStyle(evidenceCurrentText).color : "",
    evidence_navigation_background: evidenceNavigation ? getComputedStyle(evidenceNavigation).backgroundColor : "",
    evidence_current_box: evidenceCurrent ? boxFor(evidenceCurrent, "advanced-evidence-current") : {},
    primary_research_link_boxes: primaryResearchLinks.map((node) => boxFor(node, "research-workflow-link")),
    workspace_mode_box: workspaceMode ? boxFor(workspaceMode, "workspace-mode") : {},
    research_route_grid_scroll_width: researchRouteGrid ? researchRouteGrid.scrollWidth : 0,
    research_route_grid_client_width: researchRouteGrid ? researchRouteGrid.clientWidth : 0,
    workbench_primary_action_count: firstWorkbenchBrief
      ? firstWorkbenchBrief.querySelectorAll("a.public-primary-action").length
      : 0,
    workbench_primary_action_visible_count: workbenchPrimaryActions.length,
    workbench_primary_action_width: firstWorkbenchPrimaryActionBox
      ? firstWorkbenchPrimaryActionBox.width
      : 0,
    workbench_primary_action_height: firstWorkbenchPrimaryActionBox
      ? firstWorkbenchPrimaryActionBox.height
      : 0,
    workbench_module_gate_count: [...document.querySelectorAll("button")]
      .filter((node) => node.textContent.trim() === "Open evidence and analysis modules").length,
    workbench_module_gate_visible_count: workbenchModuleGates.length,
    workbench_brief_box: firstWorkbenchBrief
      ? boxFor(firstWorkbenchBrief, "company-brief")
      : null,
    workbench_aside_box: firstWorkbenchAside
      ? boxFor(firstWorkbenchAside, "company-evidence-status")
      : null,
    workbench_module_gate_box: workbenchModuleGates[0]
      ? boxFor(workbenchModuleGates[0], "module-gate")
      : null,
    workbench_brief_lane_boxes: workbenchBriefLaneBoxes,
    research_current_count: document.querySelectorAll("nav[aria-label='Personal research workflow'] [aria-current='page']").length,
    research_core_current_count: document.querySelectorAll("nav[aria-label='Personal research workflow'] .research-workflow-link[aria-current='page']").length,
    operator_radio_count: operatorRadios.length,
    operator_radio_visible_count: operatorRadios.filter(visible).length,
    operator_shell_count: operatorShells.length,
    operator_warning_count: operatorWarnings.length,
    operator_warning_kind: firstOperatorWarning
      ? firstOperatorWarning.getAttribute("data-sr-operator-kind") || ""
      : "",
    operator_warning_before_detail: operatorWarningBeforeDetail,
    operator_detail_count: operatorDetails.length,
    stop_rule_count: document.querySelectorAll("[role='main'] [data-sr-region='stop-rule']").length,
    command_topbar_nav_count: commandTopbarNavs.length,
    command_status_region_count: commandStatusRegions.length,
    command_status_region_labelled: commandStatusRegions.length === 1 &&
      Boolean(commandStatusRegions[0].getAttribute("aria-label")?.trim()),
    profile_trust_count: profileTrustStrips.length,
    profile_trust_display: firstProfileTrust
      ? getComputedStyle(firstProfileTrust).display
      : "",
    profile_trust_item_count: profileTrustItems.length,
    profile_trust_overlap_count: profileTrustOverlapCount,
    command_top_link_count: commandTopLinks.length,
    command_top_link_visible_count: visibleCommandTopLinks.length,
    command_top_link_width: firstCommandTopLinkBox ? firstCommandTopLinkBox.width : 0,
    command_top_link_height: firstCommandTopLinkBox ? firstCommandTopLinkBox.height : 0,
    non_neutral_analytic_count: nonNeutralAnalyticStates.length,
    skip_count: document.querySelectorAll("a.public-skip-link[href='#public-page-answer']").length,
    skip_in_sidebar_count: document.querySelectorAll("[data-testid='stSidebar'] a.public-skip-link[href='#public-page-answer']").length,
    skip_in_main_count: document.querySelectorAll("[role='main'] a.public-skip-link[href='#public-page-answer']").length,
    traceback_visible: body.innerText.includes("Traceback (most recent call last)"),
    spinner_count: document.querySelectorAll("[data-testid='stSpinner']").length,
    positive_tabindex_count: [...document.querySelectorAll("[tabindex]")]
      .filter((node) => node.tabIndex > 0).length,
    region_order: regionNodes.map((entry) => entry.name),
    visible_region_counts: visibleRegionCounts,
    visible_region_order: visibleRegionNodes.map((entry) => entry.name),
    primary_action_focusable_count: primaryActionFocusableCount,
    legacy_pre_answer_action_count: legacyPreAnswerActions.length,
    overflow_nodes: overflowNodes,
  };
}
"""
    )


def _discover_evidence_access_observation(page: Any) -> dict[str, object]:
    """Capture the exact visible Discover evidence-link and search hierarchy."""

    return page.evaluate(
        """
() => {
  const visible = (node) => {
    if (!node) return false;
    const box = node.getBoundingClientRect();
    const style = getComputedStyle(node);
    return box.width > 0 && box.height > 0 &&
      style.display !== "none" && style.visibility !== "hidden";
  };
  const focusable = (node) => Boolean(
    visible(node) &&
    node.tabIndex >= 0 &&
    !node.matches("[disabled], [aria-disabled='true']") &&
    node.matches("a[href], button, input, select, textarea, summary")
  );
  const clipped = (node) => {
    const style = getComputedStyle(node);
    const overflowClips = [style.overflow, style.overflowX, style.overflowY]
      .some((value) => ["hidden", "clip"].includes(String(value).toLowerCase()));
    const clamp = String(style.webkitLineClamp || "").toLowerCase();
    return overflowClips && (
      node.scrollWidth > node.clientWidth + 1 ||
      node.scrollHeight > node.clientHeight + 1 ||
      String(style.textOverflow).toLowerCase() === "ellipsis" ||
      !["", "none", "0"].includes(clamp)
    );
  };
  const byRegion = (name) => [...document.querySelectorAll(
    `[data-sr-region='${name}']`
  )].filter(visible);
  const primaryAnswers = byRegion("primary-answer");
  const quickSections = [...document.querySelectorAll(
    ".discover-quick-company-links"
  )].filter(visible);
  const quickLinks = [...document.querySelectorAll(
    ".discover-quick-company-links a[href]"
  )].filter(visible);
  const nativeSearches = [...document.querySelectorAll(
    "[data-testid='stTextInput'] input"
  )].filter((node) => {
    const wrapper = node.closest("[data-testid='stTextInput']");
    return visible(node) && Boolean(
      wrapper && wrapper.innerText.includes("Search saved companies")
    );
  });
  const stopRules = byRegion("stop-rule");
  const supportingEvidence = byRegion("supporting-evidence");
  const advancedDetails = byRegion("advanced-detail");
  const milestones = [
    ...primaryAnswers.map((node) => ({node, name: "primary-answer"})),
    ...quickSections.map((node) => ({node, name: "quick-links"})),
    ...nativeSearches.map((node) => ({node, name: "native-search"})),
    ...stopRules.map((node) => ({node, name: "stop-rule"})),
    ...supportingEvidence.map((node) => ({node, name: "supporting-evidence"})),
    ...advancedDetails.map((node) => ({node, name: "advanced-detail"})),
  ];
  milestones.sort((left, right) => {
    if (left.node === right.node) return 0;
    return left.node.compareDocumentPosition(right.node) & Node.DOCUMENT_POSITION_FOLLOWING
      ? -1
      : 1;
  });
  const currentPages = [...document.querySelectorAll(
    "nav[aria-label='Personal research workflow'] [aria-current='page']"
  )];
  const doc = document.documentElement;
  return {
    primary_answer_count: primaryAnswers.length,
    quick_links: quickLinks.map((node) => {
      const box = node.getBoundingClientRect();
      return {
        label: node.textContent.trim(),
        href: node.getAttribute("href") || "",
        visible: visible(node),
        focusable: focusable(node),
        left: box.left,
        right: box.right,
        top: box.top,
        width: box.width,
        height: box.height,
        clipped: clipped(node),
      };
    }),
    native_search_count: nativeSearches.length,
    stop_rule_count: stopRules.length,
    supporting_evidence_count: supportingEvidence.length,
    advanced_detail_count: advancedDetails.length,
    dom_order: milestones.map((entry) => entry.name),
    client_width: doc.clientWidth,
    location_path: window.location.pathname,
    location_search: window.location.search,
    current_page_count: currentPages.length,
    current_page_label: currentPages.length === 1
      ? currentPages[0].textContent.trim()
      : "",
  };
}
"""
    )


def _reset_initial_scroll(page: Any) -> None:
    page.evaluate(
        """async () => {
          window.scrollTo({left: 0, top: 0, behavior: "auto"});
          if (document.scrollingElement) {
            document.scrollingElement.scrollTo({left: 0, top: 0, behavior: "auto"});
          }
          const main = document.querySelector("[data-testid='stMain']") || document.querySelector("[role='main']");
          if (main) main.scrollTo({left: 0, top: 0, behavior: "auto"});
          const publicAppNav = document.querySelector(".public-app-nav");
          if (publicAppNav) publicAppNav.scrollTo({left: 0, top: 0, behavior: "auto"});
          const researchWorkflowNav = document.querySelector(".research-workflow-navigation");
          if (researchWorkflowNav) researchWorkflowNav.scrollTo({left: 0, top: 0, behavior: "auto"});
          await new Promise((resolve) => window.requestAnimationFrame(() => resolve()));
        }"""
    )


def _focus_sequence_observation(page: Any) -> dict[str, object]:
    page.evaluate(
        "() => document.activeElement instanceof HTMLElement && document.activeElement.blur()"
    )
    focused_roles: list[str] = []
    focused_labels: list[str] = []
    outline_widths: list[float] = []
    for _ in range(20):
        page.keyboard.press("Tab")
        observed = page.evaluate(
            """
() => {
  const element = document.activeElement;
  const selectorSearch = element.matches("[data-testid='stTextInput'] input") &&
    (() => {
      const wrapper = element.closest("[data-testid='stTextInput']");
      const label = wrapper ? wrapper.innerText : "";
      return label.includes("Search saved companies") || label.includes("Search this review queue");
    })();
  let role = "other";
  if (element.matches("a.public-skip-link")) role = "skip";
  else if (element.matches("[data-sr-region='primary-action']")) role = "primary-action";
  else if (element.matches(".discover-quick-company-links a[href]")) role = "evidence-path";
  else if (element.matches("a[href='#saved-company-browser']")) role = "browse-navigation";
  else if (selectorSearch) role = "primary-action";
  else if (
    element.closest("nav[aria-label='Personal research workflow']") ||
    element.closest(".public-app-shell")
  ) role = "navigation";
  else if (element.matches("summary")) role = "advanced-detail";
  const style = getComputedStyle(element);
  return {
    role,
    label: element.textContent.trim(),
    outline_width: Number.parseFloat(style.outlineWidth) || 0,
  };
}
"""
        )
        focused_roles.append(str(observed.get("role") or "other"))
        focused_labels.append(str(observed.get("label") or ""))
        outline_widths.append(float(observed.get("outline_width") or 0))
        if observed.get("role") == "advanced-detail":
            break
    return {
        "focused_roles": focused_roles,
        "focused_labels": focused_labels,
        "outline_widths": outline_widths,
    }


def _reduced_motion_observation(page: Any) -> dict[str, object]:
    return page.evaluate(
        """
() => {
  const visible = (node) => {
    const box = node.getBoundingClientRect();
    const style = getComputedStyle(node);
    return box.width > 0 && box.height > 0 &&
      style.display !== "none" && style.visibility !== "hidden";
  };
  const milliseconds = (raw) => String(raw || "").split(",").map((part) => {
    const value = Number.parseFloat(part) || 0;
    return part.trim().endsWith("ms") ? value : value * 1000;
  });
  const iterations = (raw) => String(raw || "").split(",").map((part) =>
    part.trim() === "infinite" ? Number.POSITIVE_INFINITY : Number.parseFloat(part) || 0
  );
  const targets = [...document.querySelectorAll(
    ".stApp, .stApp a, .stApp button, .stApp summary, .stApp [role='radio'], " +
    ".stApp [data-sr-semantic], .stApp [data-sr-region]"
  )].filter(visible);
  const styles = targets.map((node) => getComputedStyle(node));
  return {
    active: matchMedia("(prefers-reduced-motion: reduce)").matches,
    target_count: targets.length,
    max_animation_duration_ms: Math.max(0, ...styles.flatMap((style) => milliseconds(style.animationDuration))),
    max_transition_duration_ms: Math.max(0, ...styles.flatMap((style) => milliseconds(style.transitionDuration))),
    max_animation_iterations: Math.max(0, ...styles.flatMap((style) => iterations(style.animationIterationCount))),
    smooth_scroll_count: styles.filter((style) => style.scrollBehavior === "smooth").length,
  };
}
"""
    )


def _forced_colors_observation(page: Any) -> dict[str, object]:
    page.evaluate(
        "() => document.activeElement instanceof HTMLElement && document.activeElement.blur()"
    )
    page.keyboard.press("Tab")
    return page.evaluate(
        """
() => {
  const visible = (node) => {
    const box = node.getBoundingClientRect();
    const style = getComputedStyle(node);
    return box.width > 0 && box.height > 0 &&
      style.display !== "none" && style.visibility !== "hidden";
  };
  const active = document.activeElement;
  const focusStyle = getComputedStyle(active);
  const states = [...document.querySelectorAll(
    ".public-app-nav a[aria-current='page'], " +
    ".research-workflow-link[aria-current='page'], " +
    "[data-testid='stSidebar'] [role='radiogroup'] label:has(input:checked)"
  )].filter(visible);
  const stateStyles = states.map((node) => getComputedStyle(node));
  const borderWidth = (style) => Math.max(
    Number.parseFloat(style.borderTopWidth) || 0,
    Number.parseFloat(style.borderRightWidth) || 0,
    Number.parseFloat(style.borderBottomWidth) || 0,
    Number.parseFloat(style.borderLeftWidth) || 0
  );
  return {
    active: matchMedia("(forced-colors: active)").matches,
    focus_outline_style: focusStyle.outlineStyle,
    focus_outline_width: Number.parseFloat(focusStyle.outlineWidth) || 0,
    state_count: states.length,
    state_border_width: Math.max(0, ...stateStyles.map(borderWidth)),
    state_outline_width: Math.max(
      0,
      ...stateStyles.map((style) => Number.parseFloat(style.outlineWidth) || 0)
    ),
  };
}
"""
    )


def _skip_focus_observation(page: Any) -> dict[str, object]:
    before = urlsplit(page.url)
    page.evaluate(
        "() => document.activeElement instanceof HTMLElement && document.activeElement.blur()"
    )
    page.keyboard.press("Tab")
    skip = page.locator("a.public-skip-link[href='#public-page-answer']")
    skip_count = skip.count()
    focused = bool(
        skip_count == 1
        and skip.first.evaluate("element => document.activeElement === element")
    )
    if focused:
        page.keyboard.press("Enter")
        page.wait_for_timeout(150)
    after = urlsplit(page.url)
    return {
        "skip_count": skip_count,
        "focused": focused,
        "route_preserved": (
            before.scheme,
            before.netloc,
            before.path,
            before.query,
        )
        == (
            after.scheme,
            after.netloc,
            after.path,
            after.query,
        ),
        "fragment": after.fragment,
        "active_id": str(
            page.evaluate("document.activeElement && document.activeElement.id") or ""
        ),
    }


def _evaluate_observation(
    observation: dict[str, object],
    *,
    route: WorkspaceVisualRoute,
    viewport: tuple[int, int],
    zoom: int,
    console_errors: tuple[str, ...],
    skip_focus: dict[str, object],
    reduced_motion: dict[str, object],
    forced_colors: dict[str, object],
    focus_sequences: dict[str, dict[str, object]],
) -> list[dict[str, object]]:
    checks: list[dict[str, object]] = []

    def add(name: str, result: BrowserEvaluation) -> None:
        checks.append({"name": name, "passed": result.passed, "detail": result.detail})

    add(
        "initial_scroll_origin",
        evaluate_initial_scroll(
            window_scroll_x=float(observation.get("scroll_x") or 0),
            window_scroll_y=float(observation.get("scroll_y") or 0),
            document_scroll_left=float(observation.get("document_scroll_left") or 0),
            document_scroll_top=float(observation.get("document_scroll_top") or 0),
            main_scroll_left=float(observation.get("main_scroll_left") or 0),
            main_scroll_top=float(observation.get("main_scroll_top") or 0),
            public_app_nav_scroll_left=float(
                observation.get("public_app_nav_scroll_left") or 0
            ),
            research_workflow_nav_scroll_left=float(
                observation.get("research_workflow_nav_scroll_left") or 0
            ),
            research_workflow_nav_scroll_top=float(
                observation.get("research_workflow_nav_scroll_top") or 0
            ),
        ),
    )
    client_width = float(observation.get("client_width") or 0)
    for index, region in enumerate(observation.get("regions") or (), start=1):
        add(
            f"region_bounds_{index}_{region.get('name', 'unknown')}",
            evaluate_horizontal_bounds(
                left=float(region.get("left") or 0),
                right=float(region.get("right") or 0),
                client_width=client_width,
            ),
        )
    add(
        "document_scroll_width",
        evaluate_scroll_width(
            scroll_width=float(observation.get("document_scroll_width") or 0),
            client_width=client_width,
        ),
    )
    add(
        "body_scroll_width",
        evaluate_scroll_width(
            scroll_width=float(observation.get("body_scroll_width") or 0),
            client_width=client_width,
        ),
    )
    main_scroll = evaluate_scroll_width(
        scroll_width=float(observation.get("main_scroll_width") or 0),
        client_width=float(observation.get("main_client_width") or client_width),
    )
    if not main_scroll.passed and observation.get("overflow_nodes"):
        main_scroll = BrowserEvaluation(
            False,
            f"{main_scroll.detail}; overflow nodes={observation.get('overflow_nodes')!r}",
        )
    add("main_scroll_width", main_scroll)
    for index, text_node in enumerate(observation.get("text_nodes") or (), start=1):
        add(
            f"text_not_clipped_{index}",
            evaluate_text_clipping(
                overflow=str(text_node.get("overflow") or ""),
                text_overflow=str(text_node.get("text_overflow") or ""),
                line_clamp=str(text_node.get("line_clamp") or ""),
            ),
        )
    for index, control in enumerate(observation.get("controls") or (), start=1):
        add(
            f"control_target_{index}",
            evaluate_control_target(
                width=float(control.get("width") or 0),
                height=float(control.get("height") or 0),
            ),
        )

    region_counts = dict(observation.get("region_counts") or {})
    duplicates = sorted(name for name, count in region_counts.items() if int(count) > 1)
    checks.append(
        {
            "name": "unique_shared_regions",
            "passed": not duplicates,
            "detail": "shared region hooks are unique" if not duplicates else f"duplicate regions: {duplicates}",
        }
    )
    if route.slug == "discover":
        discover = dict(observation.get("discover_evidence_access") or {})
        discover_evaluation = evaluate_discover_evidence_access_layout(
            primary_answer_count=int(discover.get("primary_answer_count") or 0),
            quick_links=tuple(
                dict(link) for link in discover.get("quick_links") or ()
            ),
            native_search_count=int(discover.get("native_search_count") or 0),
            stop_rule_count=int(discover.get("stop_rule_count") or 0),
            supporting_evidence_count=int(
                discover.get("supporting_evidence_count") or 0
            ),
            advanced_detail_count=int(discover.get("advanced_detail_count") or 0),
            dom_order=tuple(str(value) for value in discover.get("dom_order") or ()),
            client_width=float(discover.get("client_width") or 0),
            location_path=str(discover.get("location_path") or ""),
            location_search=str(discover.get("location_search") or ""),
            current_page_count=int(discover.get("current_page_count") or 0),
            current_page_label=str(discover.get("current_page_label") or ""),
        )
        add("discover_evidence_access_layout", discover_evaluation)
    h1_text = tuple(str(value) for value in observation.get("h1_text") or ())
    checks.append(
        {
            "name": "single_route_h1",
            "passed": observation.get("h1_count") == 1 and route.expected_h1 in h1_text,
            "detail": f"h1={h1_text!r}; expected={route.expected_h1!r}",
        }
    )
    add(
        "single_navigation_authority",
        evaluate_navigation_authority(
            mode=route.mode,
            public_total=int(observation.get("public_nav_count") or 0),
            public_visible=int(observation.get("public_nav_visible_count") or 0),
            research_total=int(observation.get("research_nav_count") or 0),
            research_visible=int(observation.get("research_nav_visible_count") or 0),
            operator_radio_total=int(observation.get("operator_radio_count") or 0),
            operator_radio_visible=int(observation.get("operator_radio_visible_count") or 0),
        ),
    )
    if route.mode in {"public", "research"}:
        prefix = "public" if route.mode == "public" else "research"
        add(
            "mobile_navigation_discoverability",
            evaluate_mobile_navigation_discoverability(
                phone_media_matches=bool(observation.get("phone_media_matches")),
                expected_total=5 if route.mode == "public" else 4,
                total=int(observation.get(f"{prefix}_nav_link_count") or 0),
                visible=int(observation.get(f"{prefix}_nav_link_visible_count") or 0),
                fully_visible=int(
                    observation.get(f"{prefix}_nav_link_fully_visible_count") or 0
                ),
                scroll_width=float(observation.get(f"{prefix}_nav_scroll_width") or 0),
                client_width=float(observation.get(f"{prefix}_nav_client_width") or 0),
            ),
        )
    if route.slug in {"public-proof-history", "personal-proof-history"}:
        add(
            "proof_history_initial_tree",
            evaluate_proof_history_initial_tree(
                record_count=int(observation.get("proof_timeline_record_count") or 0),
                summary=str(observation.get("proof_timeline_summary") or ""),
            ),
        )
    if route.mode == "operator":
        expected_kind = (
            "compatibility"
            if route.slug in {"market-direction", "monthly-picks"}
            else "operator"
        )
        add(
            "operator_route_contract",
            evaluate_operator_route_contract(
                slug=route.slug,
                expected_h1=route.expected_h1,
                expected_kind=expected_kind,
                h1_count=int(observation.get("h1_count") or 0),
                h1_text=h1_text,
                shell_count=int(observation.get("operator_shell_count") or 0),
                warning_count=int(observation.get("operator_warning_count") or 0),
                warning_kind=str(observation.get("operator_warning_kind") or ""),
                warning_before_detail=(
                    observation.get("operator_warning_before_detail") is True
                ),
                detail_count=int(observation.get("operator_detail_count") or 0),
                stop_rule_count=int(observation.get("stop_rule_count") or 0),
                topbar_nav_count=int(observation.get("command_topbar_nav_count") or 0),
                status_region_count=int(
                    observation.get("command_status_region_count") or 0
                ),
                status_region_labelled=(
                    observation.get("command_status_region_labelled") is True
                ),
                profile_trust_count=int(
                    observation.get("profile_trust_count") or 0
                ),
                profile_trust_display=str(
                    observation.get("profile_trust_display") or ""
                ),
                profile_trust_item_count=int(
                    observation.get("profile_trust_item_count") or 0
                ),
                profile_trust_overlap_count=int(
                    observation.get("profile_trust_overlap_count") or 0
                ),
                shortcut_count=int(observation.get("command_top_link_count") or 0),
                shortcut_visible_count=int(
                    observation.get("command_top_link_visible_count") or 0
                ),
                shortcut_width=float(
                    observation.get("command_top_link_width") or 0
                ),
                shortcut_height=float(
                    observation.get("command_top_link_height") or 0
                ),
                non_neutral_analytic_count=int(
                    observation.get("non_neutral_analytic_count") or 0
                ),
            ),
        )
    expected_skip_placement = (
        observation.get("skip_count") == 1
        and (
            observation.get("skip_in_sidebar_count") == 1
            if route.mode == "operator"
            else observation.get("skip_in_main_count") == 1
        )
    )
    checks.append(
        {
            "name": "mode_correct_skip_link",
            "passed": expected_skip_placement,
            "detail": (
                f"total={observation.get('skip_count')}; main={observation.get('skip_in_main_count')}; "
                f"sidebar={observation.get('skip_in_sidebar_count')}"
            ),
        }
    )
    add(
        "skip_link_focus_and_activation",
        evaluate_skip_focus(
            skip_count=int(skip_focus.get("skip_count") or 0),
            focused=skip_focus.get("focused") is True,
            route_preserved=skip_focus.get("route_preserved") is True,
            fragment=str(skip_focus.get("fragment") or ""),
            active_id=str(skip_focus.get("active_id") or ""),
        ),
    )
    if route.slug in {"personal-data-health", "personal-proof-history"}:
        checks.append(
            {
                "name": "evidence_nav_has_no_false_current_core_item",
                "passed": observation.get("research_core_current_count") == 0,
                "detail": f"current core item count={observation.get('research_core_current_count')}",
            }
        )
        add(
            "advanced_evidence_rail_contrast",
            evaluate_advanced_evidence_rail_contrast(
                marker_count=int(
                    observation.get("evidence_current_marker_count") or 0
                ),
                label_color=str(
                    observation.get("evidence_current_label_color") or ""
                ),
                current_color=str(
                    observation.get("evidence_current_text_color") or ""
                ),
                navigation_background=str(
                    observation.get("evidence_navigation_background") or ""
                ),
            ),
        )
        add(
            "advanced_evidence_phone_row",
            evaluate_advanced_evidence_navigation_layout(
                phone_layout=observation.get("phone_media_matches") is True,
                marker_count=int(
                    observation.get("evidence_current_marker_count") or 0
                ),
                primary_link_count=len(
                    observation.get("primary_research_link_boxes") or ()
                ),
                marker_box=dict(observation.get("evidence_current_box") or {}),
                primary_link_boxes=tuple(
                    dict(box)
                    for box in observation.get("primary_research_link_boxes") or ()
                ),
                workspace_mode_box=dict(
                    observation.get("workspace_mode_box") or {}
                ),
                routes_scroll_width=float(
                    observation.get("research_route_grid_scroll_width") or 0
                ),
                routes_client_width=float(
                    observation.get("research_route_grid_client_width") or 0
                ),
            ),
        )
    first_view_routes = {
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
    }
    if route.slug in first_view_routes:
        boxes = {
            str(row.get("name")): row for row in observation.get("regions") or ()
        }
        if zoom == 1:
            observed_width = float(
                observation.get("visual_viewport_width")
                or observation.get("client_width")
                or 0
            )
            observed_height = float(
                observation.get("visual_viewport_height")
                or observation.get("client_height")
                or 0
            )
            if route.slug == "discover":
                add(
                    "initial_viewport_hierarchy",
                    evaluate_discover_initial_viewport_hierarchy(
                        primary_answer_box=dict(boxes.get("primary-answer") or {}),
                        quick_links=tuple(
                            dict(link) for link in discover.get("quick_links") or ()
                        ),
                        viewport_height=observed_height,
                    ),
                )
            else:
                add(
                    "initial_viewport_hierarchy",
                    evaluate_initial_viewport_hierarchy(
                        region_boxes=boxes,
                        viewport_height=observed_height,
                        require_complete=observed_width >= 1280,
                    ),
                )
    if route.slug in {"research-desk", "discover", "company-workbench", "monitor"}:
        checks.append(
            {
                "name": "one_stop_rule",
                "passed": region_counts.get("stop-rule") == 1,
                "detail": f"stop-rule count={region_counts.get('stop-rule', 0)}",
            }
        )
    if route.slug in {"research-desk", "discover", "company-workbench", "monitor"}:
        add(
            "personal_route_answer_hierarchy",
            evaluate_personal_route_hierarchy(
                slug=route.slug,
                region_counts={str(name): int(count) for name, count in region_counts.items()},
                region_order=tuple(
                    str(value) for value in observation.get("region_order") or ()
                ),
                visible_region_counts={
                    str(name): int(count)
                    for name, count in dict(
                        observation.get("visible_region_counts") or {}
                    ).items()
                },
                visible_region_order=tuple(
                    str(value)
                    for value in observation.get("visible_region_order") or ()
                ),
                primary_action_focusable_count=int(
                    observation.get("primary_action_focusable_count") or 0
                ),
                legacy_pre_answer_action_count=int(
                    observation.get("legacy_pre_answer_action_count") or 0
                ),
            ),
        )
    if route.slug == "company-workbench":
        add(
            "company_workbench_document_contract",
            evaluate_company_workbench_document_contract(
                viewport_width=float(
                    observation.get("visual_viewport_width")
                    or observation.get("client_width")
                    or 0
                ),
                zoom=zoom,
                phone_layout=observation.get("phone_media_matches") is True,
                h1_count=int(observation.get("h1_count") or 0),
                display_title_count=int(
                    observation.get("workbench_display_title_count") or 0
                ),
                display_title_text=str(
                    observation.get("workbench_display_title_text") or ""
                ),
                navigation_count=int(
                    observation.get("workbench_navigation_count") or 0
                ),
                navigation_labelled_count=int(
                    observation.get("workbench_navigation_labelled_count") or 0
                ),
                brief_count=int(observation.get("workbench_brief_count") or 0),
                brief_visible_count=int(
                    observation.get("workbench_brief_visible_count") or 0
                ),
                brief_labelled_count=int(
                    observation.get("workbench_brief_labelled_count") or 0
                ),
                aside_count=int(observation.get("workbench_aside_count") or 0),
                aside_visible_count=int(
                    observation.get("workbench_aside_visible_count") or 0
                ),
                aside_labelled_count=int(
                    observation.get("workbench_aside_labelled_count") or 0
                ),
                evidence_lane_count=int(
                    observation.get("workbench_evidence_lane_count") or 0
                ),
                positive_tabindex_count=int(
                    observation.get("positive_tabindex_count") or 0
                ),
                primary_action_count=int(
                    observation.get("workbench_primary_action_count") or 0
                ),
                primary_action_visible_count=int(
                    observation.get("workbench_primary_action_visible_count") or 0
                ),
                primary_action_width=float(
                    observation.get("workbench_primary_action_width") or 0
                ),
                primary_action_height=float(
                    observation.get("workbench_primary_action_height") or 0
                ),
                module_gate_count=int(
                    observation.get("workbench_module_gate_count") or 0
                ),
                module_gate_visible_count=int(
                    observation.get("workbench_module_gate_visible_count") or 0
                ),
                brief_box=dict(observation.get("workbench_brief_box") or {}),
                aside_box=dict(observation.get("workbench_aside_box") or {}),
                module_gate_box=dict(
                    observation.get("workbench_module_gate_box") or {}
                ),
                brief_lane_boxes=tuple(
                    dict(row)
                    for row in observation.get("workbench_brief_lane_boxes") or ()
                ),
            ),
        )
        add(
            "resolved_report_state",
            evaluate_resolved_report_state(
                company_brief_count=int(
                    observation.get("workbench_brief_visible_count") or 0
                ),
                primary_answer_count=int(
                    observation.get("workbench_primary_answer_count") or 0
                ),
                evidence_lane_count=int(
                    observation.get("workbench_evidence_lane_count") or 0
                ),
                busy_loading_count=int(
                    observation.get("workbench_busy_loading_count") or 0
                ),
            ),
        )
    if route.slug in {
        "public-home",
        "stock-selector",
        "single-stock-report",
        "public-data-health",
        "public-proof-history",
        "personal-data-health",
        "personal-proof-history",
    }:
        add(
            "task4_route_answer_hierarchy",
            evaluate_task4_route_hierarchy(
                slug=route.slug,
                region_counts={str(name): int(count) for name, count in region_counts.items()},
                region_order=tuple(
                    str(value) for value in observation.get("region_order") or ()
                ),
                visible_region_counts={
                    str(name): int(count)
                    for name, count in dict(
                        observation.get("visible_region_counts") or {}
                    ).items()
                },
                visible_region_order=tuple(
                    str(value)
                    for value in observation.get("visible_region_order") or ()
                ),
                primary_action_focusable_count=int(
                    observation.get("primary_action_focusable_count") or 0
                ),
                legacy_pre_answer_action_count=int(
                    observation.get("legacy_pre_answer_action_count") or 0
                ),
            ),
        )
    if route.slug == "public-home":
        boxes = {
            str(row.get("name")): row for row in observation.get("regions") or ()
        }
        home_action_area = dict(observation.get("home_action_area") or {})
        if home_action_area and all(
            name in boxes
            for name in ("primary-action", "stop-rule", "supporting-evidence")
        ):
            add(
                "public_home_responsive_geometry",
                evaluate_public_home_geometry(
                    viewport_width=float(
                        observation.get("visual_viewport_width")
                        or observation.get("client_width")
                        or 0
                    ),
                    viewport_height=float(
                        observation.get("visual_viewport_height")
                        or observation.get("client_height")
                        or 0
                    ),
                    zoom=zoom,
                    phone_layout=observation.get("phone_media_matches") is True,
                    action_left=float(home_action_area.get("left") or 0),
                    action_right=float(home_action_area.get("right") or 0),
                    action_top=float(home_action_area.get("top") or 0),
                    action_bottom=float(home_action_area.get("bottom") or 0),
                    stop_top=float(boxes["stop-rule"].get("top") or 0),
                    stop_bottom=float(boxes["stop-rule"].get("bottom") or 0),
                    metrics_top=float(boxes["supporting-evidence"].get("top") or 0),
                    metrics_bottom=float(boxes["supporting-evidence"].get("bottom") or 0),
                    metrics_left=float(boxes["supporting-evidence"].get("left") or 0),
                    metrics_right=float(boxes["supporting-evidence"].get("right") or 0),
                ),
            )
        else:
            checks.append(
                {
                    "name": "public_home_responsive_geometry",
                    "passed": False,
                    "detail": f"missing Home geometry regions: {tuple(boxes)!r}",
                }
            )
    if route.slug in PERSONAL_FOCUS_ROUTE_SLUGS:
        for media_mode in ("normal", "forced-colors"):
            sequence = focus_sequences.get(media_mode) or {}
            if route.slug == "discover":
                evaluation = evaluate_discover_focus_sequence(
                    focused_roles=tuple(
                        str(value) for value in sequence.get("focused_roles") or ()
                    ),
                    focused_labels=tuple(
                        str(value) for value in sequence.get("focused_labels") or ()
                    ),
                    outline_widths=tuple(
                        float(value) for value in sequence.get("outline_widths") or ()
                    ),
                    positive_tabindex_count=int(
                        observation.get("positive_tabindex_count") or 0
                    ),
                )
            else:
                evaluation = evaluate_focus_sequence(
                    focused_roles=tuple(
                        str(value) for value in sequence.get("focused_roles") or ()
                    ),
                    region_order=tuple(
                        str(value) for value in observation.get("region_order") or ()
                    ),
                    outline_widths=tuple(
                        float(value) for value in sequence.get("outline_widths") or ()
                    ),
                    positive_tabindex_count=int(
                        observation.get("positive_tabindex_count") or 0
                    ),
                )
            add(
                f"natural_focus_sequence_{media_mode}",
                evaluation,
            )
    elif route.slug in {
        "public-home",
        "stock-selector",
        "single-stock-report",
        "public-data-health",
        "public-proof-history",
        "personal-data-health",
        "personal-proof-history",
    }:
        for media_mode in ("normal", "forced-colors"):
            sequence = focus_sequences.get(media_mode) or {}
            add(
                f"task4_natural_focus_sequence_{media_mode}",
                evaluate_task4_focus_sequence(
                    slug=route.slug,
                    focused_roles=tuple(
                        str(value) for value in sequence.get("focused_roles") or ()
                    ),
                    region_order=tuple(
                        str(value)
                        for value in observation.get("visible_region_order") or ()
                    ),
                    outline_widths=tuple(
                        float(value)
                        for value in sequence.get("outline_widths") or ()
                    ),
                    positive_tabindex_count=int(
                        observation.get("positive_tabindex_count") or 0
                    ),
                ),
            )
    add(
        "actual_browser_zoom_and_reflow",
        evaluate_browser_zoom(
            requested_zoom=zoom,
            declared_width=float(viewport[0]),
            declared_height=float(viewport[1]),
            screenshot_width=float(observation.get("screenshot_width") or 0),
            screenshot_height=float(observation.get("screenshot_height") or 0),
            inner_width=float(observation.get("inner_width") or 0),
            inner_height=float(observation.get("inner_height") or 0),
            visual_viewport_width=float(
                observation.get("visual_viewport_width") or 0
            ),
            visual_viewport_height=float(
                observation.get("visual_viewport_height") or 0
            ),
            device_pixel_ratio=float(observation.get("device_pixel_ratio") or 0),
            visual_viewport_scale=float(
                observation.get("visual_viewport_scale") or 0
            ),
        ),
    )
    add(
        "computed_reduced_motion_styles",
        evaluate_reduced_motion_styles(
            active=reduced_motion.get("active") is True,
            target_count=int(reduced_motion.get("target_count") or 0),
            max_animation_duration_ms=float(
                reduced_motion.get("max_animation_duration_ms") or 0
            ),
            max_transition_duration_ms=float(
                reduced_motion.get("max_transition_duration_ms") or 0
            ),
            max_animation_iterations=float(
                reduced_motion.get("max_animation_iterations") or 0
            ),
            smooth_scroll_count=int(reduced_motion.get("smooth_scroll_count") or 0),
        ),
    )
    add(
        "computed_forced_colors_styles",
        evaluate_forced_colors_styles(
            active=forced_colors.get("active") is True,
            focus_outline_style=str(
                forced_colors.get("focus_outline_style") or ""
            ),
            focus_outline_width=float(
                forced_colors.get("focus_outline_width") or 0
            ),
            state_count=int(forced_colors.get("state_count") or 0),
            state_border_width=float(
                forced_colors.get("state_border_width") or 0
            ),
            state_outline_width=float(
                forced_colors.get("state_outline_width") or 0
            ),
        ),
    )
    add(
        "idle_runtime_without_errors",
        evaluate_runtime_capture(
            app_state=str(observation.get("app_state") or ""),
            traceback_visible=observation.get("traceback_visible") is True,
            spinner_count=int(observation.get("spinner_count") or 0),
            console_errors=console_errors,
        ),
    )
    return checks


def _chromium_zoom_preferences(*, host: str, zoom: int) -> dict[str, object]:
    zoom_level = math.log(float(zoom), 1.2) if zoom > 0 else 0.0
    return {
        "partition": {
            "per_host_zoom_levels": {
                "x": {
                    host: {
                        "last_modified": "13300000000000000",
                        "zoom_level": zoom_level,
                    }
                }
            }
        }
    }


def _failed_cell_result(
    *,
    route: WorkspaceVisualRoute,
    viewport: tuple[int, int],
    zoom: int,
    error: str,
    screenshot: str = "",
    observation: dict[str, object] | None = None,
    console_errors: tuple[str, ...] = (),
    network_capture: dict[str, object] | None = None,
    server_log: str = "",
) -> dict[str, object]:
    captured = observation or {}
    network = http_network_capture_payload(
        network_capture or _new_http_network_capture()
    )
    network_evaluation = evaluate_http_network_capture(network)
    browser_diagnostics = (
        "Browser console/page errors:\n" + "\n".join(console_errors)
        if console_errors
        else "Browser console/page diagnostics before failure: none captured."
    )
    return {
        "route": route.slug,
        "viewport": f"{viewport[0]}x{viewport[1]}",
        "zoom": zoom,
        "passed": False,
        "screenshot": screenshot,
        "checks": [
            {
                "name": "cell_execution",
                "passed": False,
                "detail": error,
            },
            {
                "name": "no_external_http_requests",
                "passed": network_evaluation.passed,
                "detail": network_evaluation.detail,
            },
        ],
        "geometry": structured_geometry(captured),
        "runtime": runtime_capture_payload(captured, console_errors),
        "network": network,
        "error": error,
        "log": "\n".join(
            part
            for part in (
                server_log.strip(),
                browser_diagnostics,
                _http_network_log(network),
                f"Cell execution failed: {error}",
            )
            if part
        ),
    }


def _close_browser_context(
    context: Any,
    *,
    evaluation_complete: bool,
    playwright_error_type: type[Exception],
) -> None:
    """Close before result serialization, tolerating only completed-target teardown."""

    try:
        context.close()
    except playwright_error_type as exc:
        if evaluation_complete and type(exc).__name__ == "TargetClosedError":
            return
        raise


def _run_matrix_cell(
    *,
    root: Path,
    route: WorkspaceVisualRoute,
    viewport: tuple[int, int],
    zoom: int,
    output_dir: Path,
    timeout_seconds: float,
    ) -> dict[str, object]:
    screenshot_name = f"{route.slug}-{viewport[0]}x{viewport[1]}-zoom-{zoom}.png"
    chrome = find_chrome_executable()
    if chrome is None or not Path(chrome).is_file() or not os.access(chrome, os.X_OK):
        return _failed_cell_result(
            route=route,
            viewport=viewport,
            zoom=zoom,
            error="Chrome-compatible browser runtime is unavailable.",
        )
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError:
        return _failed_cell_result(
            route=route,
            viewport=viewport,
            zoom=zoom,
            error="Playwright browser runtime is unavailable.",
        )

    console_errors: list[str] = []
    network_capture = _new_http_network_capture()
    server_log = ""
    observation: dict[str, object] = {}
    evaluation_complete = False
    server: Any | None = None
    try:
        with _captured_local_demo_server(
            root,
            timeout_seconds=max(5.0, timeout_seconds),
        ) as server:
            host = str(urlsplit(server.base_url).hostname or "")
            if host not in {"127.0.0.1", "localhost"}:
                raise RuntimeError(f"browser zoom profile requires a local host, got {host!r}")
            expected_origin = _canonical_http_origin(server.base_url)
            if expected_origin is None:
                raise RuntimeError(
                    f"browser request capture requires a valid HTTP origin, got {server.base_url!r}"
                )
            with tempfile.TemporaryDirectory(
                prefix="stock-research-workspace-zoom-",
                dir="/tmp",
            ) as profile_directory:
                profile = Path(profile_directory)
                preferences_path = profile / "Default" / "Preferences"
                preferences_path.parent.mkdir(parents=True)
                preferences_path.write_text(
                    json.dumps(_chromium_zoom_preferences(host=host, zoom=zoom)),
                    encoding="utf-8",
                )
                with sync_playwright() as playwright:
                    context = playwright.chromium.launch_persistent_context(
                        user_data_dir=profile,
                        executable_path=str(chrome),
                        headless=True,
                        viewport={"width": viewport[0], "height": viewport[1]},
                        screen={"width": viewport[0], "height": viewport[1]},
                    )
                    page = context.pages[0] if context.pages else context.new_page()

                    def capture_request(request: Any) -> None:
                        try:
                            request_url = str(request.url)
                        except Exception:
                            request_url = "http://[unavailable-request-url"
                        _record_http_request(
                            network_capture,
                            url=request_url,
                            expected_origin=expected_origin,
                        )

                    page.on("request", capture_request)
                    page.on(
                        "console",
                        lambda message: console_errors.append(f"console {message.type}: {message.text}")
                        if message.type == "error"
                        else None,
                    )
                    page.on("pageerror", lambda error: console_errors.append(f"pageerror: {error}"))
                    try:
                        route_url = f"{server.base_url.rstrip('/')}{route.route}"

                        def load_route() -> None:
                            page.goto(
                                route_url,
                                wait_until="domcontentloaded",
                                timeout=int(max(5.0, timeout_seconds) * 1000),
                            )
                            _wait_for_visible_text(
                                page,
                                route.marker,
                                timeout_seconds=max(5.0, timeout_seconds),
                            )
                            _wait_for_dom_stability(
                                page,
                                timeout_seconds=max(5.0, timeout_seconds),
                            )
                            page.wait_for_function(
                                """() => {
                                  const app = document.querySelector('[data-testid="stApp"]');
                                  return app && app.getAttribute("data-test-script-state") === "notRunning";
                                }""",
                                timeout=int(max(5.0, timeout_seconds) * 1000),
                            )

                        page.emulate_media(
                            reduced_motion="no-preference",
                            forced_colors="none",
                        )
                        load_route()
                        _reset_initial_scroll(page)
                        observation = _browser_observation(page)
                        if route.slug == "discover":
                            observation["discover_evidence_access"] = (
                                _discover_evidence_access_observation(page)
                            )
                        screenshot_bytes = page.screenshot(
                            path=output_dir / screenshot_name,
                            full_page=False,
                            scale="device",
                        )
                        if screenshot_bytes[:8] != b"\x89PNG\r\n\x1a\n":
                            raise RuntimeError("browser screenshot did not produce a PNG")
                        observation["screenshot_width"] = int.from_bytes(
                            screenshot_bytes[16:20], "big"
                        )
                        observation["screenshot_height"] = int.from_bytes(
                            screenshot_bytes[20:24], "big"
                        )
                        focus_sequences: dict[str, dict[str, object]] = {}
                        focus_route_slugs = PERSONAL_FOCUS_ROUTE_SLUGS | {
                            "public-home",
                            "stock-selector",
                            "single-stock-report",
                            "public-data-health",
                            "public-proof-history",
                            "personal-data-health",
                            "personal-proof-history",
                        }
                        if route.slug in focus_route_slugs:
                            focus_sequences["normal"] = _focus_sequence_observation(page)
                            load_route()
                            _reset_initial_scroll(page)
                        skip_focus = _skip_focus_observation(page)

                        page.emulate_media(
                            reduced_motion="reduce",
                            forced_colors="none",
                        )
                        load_route()
                        reduced_motion = _reduced_motion_observation(page)

                        page.emulate_media(
                            reduced_motion="no-preference",
                            forced_colors="active",
                        )
                        load_route()
                        forced_colors = _forced_colors_observation(page)
                        if route.slug in focus_route_slugs:
                            load_route()
                            focus_sequences["forced-colors"] = _focus_sequence_observation(page)
                        observation = apply_final_runtime_observation(
                            observation,
                            _runtime_observation(page),
                        )
                        checks = _evaluate_observation(
                            observation,
                            route=route,
                            viewport=viewport,
                            zoom=zoom,
                            console_errors=tuple(console_errors),
                            skip_focus=skip_focus,
                            reduced_motion=reduced_motion,
                            forced_colors=forced_colors,
                            focus_sequences=focus_sequences,
                        )
                        evaluation_complete = True
                    finally:
                        _close_browser_context(
                            context,
                            evaluation_complete=evaluation_complete,
                            playwright_error_type=PlaywrightError,
                        )
            server_log = "\n".join(server.snapshot())
    except Exception as exc:
        if server is not None:
            try:
                server_log = "\n".join(server.snapshot())
            except Exception as snapshot_exc:  # pragma: no cover - defensive diagnostics
                server_log = (
                    f"Server diagnostics unavailable: {type(snapshot_exc).__name__}: "
                    f"{snapshot_exc}"
                )
        return _failed_cell_result(
            route=route,
            viewport=viewport,
            zoom=zoom,
            error=f"{type(exc).__name__}: {exc}",
            screenshot=(
                screenshot_name if (output_dir / screenshot_name).exists() else ""
            ),
            observation=observation,
            console_errors=tuple(console_errors),
            network_capture=network_capture,
            server_log=server_log,
        )
    runtime = runtime_capture_payload(observation, tuple(console_errors))
    checks = finalize_runtime_check(checks, runtime)
    network = http_network_capture_payload(network_capture)
    checks = finalize_http_network_check(checks, network)
    browser_log = (
        "Browser console/page errors: none."
        if not console_errors
        else "Browser console/page errors:\n" + "\n".join(console_errors)
    )
    return {
        "route": route.slug,
        "viewport": f"{viewport[0]}x{viewport[1]}",
        "zoom": zoom,
        "passed": bool(checks) and all(bool(check["passed"]) for check in checks),
        "screenshot": screenshot_name,
        "checks": checks,
        "geometry": structured_geometry(observation),
        "runtime": runtime,
        "network": network,
        "log": "\n".join(
            part
            for part in (server_log, browser_log, _http_network_log(network))
            if part
        ),
    }


def run_workspace_visual_browser_gate(
    base_dir: Path | str,
    *,
    routes: str,
    viewports: str,
    zooms: str,
    output_dir: Path | str,
    timeout_seconds: float = 45.0,
    cell_runner: Callable[..., dict[str, object]] | None = None,
) -> dict[str, object]:
    root = resolve_project_root(base_dir)
    selected_routes = parse_routes(routes)
    selected_viewports = parse_viewports(viewports)
    selected_zooms = parse_zooms(zooms)
    destination = prepare_output_dir(output_dir)
    runner = cell_runner or _run_matrix_cell
    source_snapshot = _source_snapshot(root)
    results: list[dict[str, object]] = []
    logs: list[str] = []
    for route in selected_routes:
        for viewport in selected_viewports:
            for zoom in selected_zooms:
                try:
                    result = runner(
                        root=root,
                        route=route,
                        viewport=viewport,
                        zoom=zoom,
                        output_dir=destination,
                        timeout_seconds=max(5.0, timeout_seconds),
                    )
                except Exception as exc:
                    result = _failed_cell_result(
                        route=route,
                        viewport=viewport,
                        zoom=zoom,
                        error=f"{type(exc).__name__}: {exc}",
                    )
                log = str(result.pop("log", "") or "").strip()
                if not log:
                    error = str(result.get("error") or "").strip()
                    log = (
                        f"Cell execution failed: "
                        f"{error or 'failed cell did not provide diagnostics'}"
                        if not result.get("passed")
                        else "No browser/server diagnostics were emitted for this cell."
                    )
                logs.append(
                    f"[{route.slug} {viewport[0]}x{viewport[1]} zoom={zoom}]\n"
                    + log
                )
                results.append(result)
    failures = [
        f"{result['route']} {result['viewport']} zoom={result['zoom']}"
        for result in results
        if not result.get("passed")
    ]
    source_snapshot_after = _source_snapshot(root)
    source_before_validation = evaluate_source_snapshot(source_snapshot)
    source_after_validation = evaluate_source_snapshot(source_snapshot_after)
    source_snapshot_valid = (
        source_before_validation.passed and source_after_validation.passed
    )
    source_snapshot_stable = source_snapshot == source_snapshot_after
    if not source_snapshot_valid:
        failures.append("source snapshot unavailable for matrix attribution")
        logs.append(
            "[matrix source snapshot]\n"
            "Source snapshot attribution is unavailable; evidence is invalid.\n"
            f"Before: {source_before_validation.detail}\n"
            f"After: {source_after_validation.detail}"
        )
    if not source_snapshot_stable:
        failures.append("source snapshot changed during matrix capture")
        logs.append(
            "[matrix source snapshot]\n"
            "Source snapshot changed during matrix capture; evidence attribution is invalid."
        )
    payload = {
        "verdict": "passed" if results and not failures else "failed",
        "commit": str(source_snapshot.get("commit") or _git_commit(root)),
        "environment": f"{platform.system()} {platform.machine()}",
        "routes": [route.slug for route in selected_routes],
        "viewports": [f"{width}x{height}" for width, height in selected_viewports],
        "zooms": list(selected_zooms),
        "coverage": evaluate_full_matrix_coverage(results),
        "source_snapshot": source_snapshot,
        "source_snapshot_after": source_snapshot_after,
        "source_snapshot_valid": source_snapshot_valid,
        "source_snapshot_validation": {
            "before": source_before_validation.detail,
            "after": source_after_validation.detail,
        },
        "source_snapshot_stable": source_snapshot_stable,
        "results": results,
        "failures": failures,
        "boundary": (
            "Read-only browser engineering evidence only; not WCAG conformance, "
            "screen-reader, independent-human, hosted, source-rights, or market validation."
        ),
    }
    (destination / "results.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (destination / "browser.log").write_text("\n\n".join(logs) + "\n", encoding="utf-8")
    return payload


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the deterministic workspace visual browser matrix."
    )
    parser.add_argument("--routes", required=True)
    parser.add_argument("--viewports", required=True)
    parser.add_argument("--zooms", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--root", default=".")
    parser.add_argument("--timeout-seconds", type=float, default=45.0)
    return parser


def main() -> int:
    parser = build_argument_parser()
    args = parser.parse_args()
    try:
        payload = run_workspace_visual_browser_gate(
            args.root,
            routes=args.routes,
            viewports=args.viewports,
            zooms=args.zooms,
            output_dir=args.output_dir,
            timeout_seconds=max(5.0, args.timeout_seconds),
        )
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["verdict"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
