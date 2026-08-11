"""Deterministic browser evidence for the calm institutional workspace shell."""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

from src.paths import resolve_project_root
from src.public_performance_gate import (
    _wait_for_dom_stability,
    _wait_for_visible_text,
    find_chrome_executable,
)
from src.research_accessibility_browser_gate import _captured_local_demo_server


VIEWPORTS: tuple[tuple[int, int], ...] = ((1280, 720), (1440, 1024), (390, 844))
ZOOMS: tuple[int, ...] = (1, 2)


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
        "/?mode=research&page=monitor",
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
        "Latest evidence",
        "What evidence changed a readiness state?",
        "public",
    ),
    WorkspaceVisualRoute(
        "personal-data-health",
        "Personal Data Health",
        "/?mode=research&page=data-health&ticker=AVGO",
        "Price / setup",
        "Data Health",
        "research",
    ),
    WorkspaceVisualRoute(
        "personal-proof-history",
        "Personal Proof History",
        "/?mode=research&page=proof-history&ticker=AVGO",
        "Latest evidence",
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


def evaluate_control_target(*, width: float, height: float) -> BrowserEvaluation:
    passed = width >= 44 and height >= 44
    return BrowserEvaluation(passed, f"control target {width:.1f}x{height:.1f}")


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
    passed = (
        active
        and str(focus_outline_style).casefold() not in {"", "none"}
        and focus_outline_width >= 3
        and state_count >= 1
        and max(state_border_width, state_outline_width) >= 1
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
        action_index = focused_roles.index("primary-action")
    except ValueError:
        action_index = -1
    tab_order_passed = (
        bool(focused_roles)
        and focused_roles[0] == "skip"
        and action_index > 1
        and set(focused_roles[1:action_index]) == {"navigation"}
        and focused_roles[action_index + 1 : action_index + 2] == ("advanced-detail",)
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


def evaluate_personal_route_hierarchy(
    *,
    slug: str,
    region_counts: dict[str, int],
    region_order: tuple[str, ...],
    primary_action_focusable_count: int,
    legacy_pre_answer_action_count: int,
) -> BrowserEvaluation:
    """Require one answer-first hierarchy for a modernized personal route."""

    if slug not in {"discover", "company-workbench", "monitor"}:
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
    supporting_count_passed = supporting_count in {0, 1}
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
    passed = (
        required_counts_passed
        and supporting_count_passed
        and required_order_passed
        and supporting_order_passed
        and primary_action_focusable_count == 1
        and legacy_pre_answer_action_count == 0
    )
    return BrowserEvaluation(
        passed,
        (
            f"route={slug}; counts={region_counts!r}; order={region_order!r}; "
            f"supporting_count={supporting_count}; "
            f"primary_action_focusable_count={primary_action_focusable_count}; "
            f"legacy_pre_answer_action_count={legacy_pre_answer_action_count}"
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
  const discoverAction = [...document.querySelectorAll("[data-testid='stTextInput']")]
    .find((node) => node.innerText.includes("Search saved companies"))
    ?.querySelector("input") || null;
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
    "[data-sr-region='primary-action'], [data-sr-region='stop-rule']"
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
    "nav a, [data-sr-region='primary-action'], [data-testid='stLinkButton'] a[kind='primary'], " +
    "[data-testid='stButton'] button[kind='primary']"
  );
  if (discoverAction && visible(discoverAction)) {
    controls.push(boxFor(discoverAction, "primary-action"));
  }
  const main = document.querySelector("[role='main']") || document.querySelector("[data-testid='stMain']");
  const doc = document.documentElement;
  const body = document.body;
  const regions = boxes("[data-sr-region]");
  if (discoverAction && visible(discoverAction)) {
    regions.push(boxFor(discoverAction, "primary-action"));
  }
  const publicNavs = [...document.querySelectorAll("nav[aria-label='Public workflow']")];
  const researchNavs = [...document.querySelectorAll("nav[aria-label='Personal research workflow']")];
  const operatorRadios = [...document.querySelectorAll("[data-testid='stSidebar'] [role='radiogroup']")];
  const legacyPreAnswerActions = [
    ...document.querySelectorAll(".research-workspace-action")
  ].filter(visible);
  const regionCounts = {};
  for (const region of document.querySelectorAll("[data-sr-region]")) {
    const name = region.getAttribute("data-sr-region");
    regionCounts[name] = (regionCounts[name] || 0) + 1;
  }
  if (discoverAction && visible(discoverAction)) {
    regionCounts["primary-action"] = (regionCounts["primary-action"] || 0) + 1;
  }
  const regionNodes = [...document.querySelectorAll("[data-sr-region]")]
    .map((node) => ({node, name: node.getAttribute("data-sr-region")}));
  if (discoverAction && visible(discoverAction)) {
    regionNodes.push({node: discoverAction, name: "primary-action"});
  }
  regionNodes.sort((left, right) => {
    if (left.node === right.node) return 0;
    return left.node.compareDocumentPosition(right.node) & Node.DOCUMENT_POSITION_FOLLOWING
      ? -1
      : 1;
  });
  const primaryActionNodes = [
    ...document.querySelectorAll("[data-sr-region='primary-action']"),
    ...(discoverAction && visible(discoverAction) ? [discoverAction] : []),
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
    h1_count: document.querySelectorAll("[role='main'] h1").length,
    h1_text: [...document.querySelectorAll("[role='main'] h1")].map((node) => node.textContent.trim()),
    public_nav_count: publicNavs.length,
    public_nav_visible_count: publicNavs.filter(visible).length,
    research_nav_count: researchNavs.length,
    research_nav_visible_count: researchNavs.filter(visible).length,
    research_current_count: document.querySelectorAll("nav[aria-label='Personal research workflow'] [aria-current='page']").length,
    operator_radio_count: operatorRadios.length,
    operator_radio_visible_count: operatorRadios.filter(visible).length,
    skip_count: document.querySelectorAll("a.public-skip-link[href='#public-page-answer']").length,
    skip_in_sidebar_count: document.querySelectorAll("[data-testid='stSidebar'] a.public-skip-link[href='#public-page-answer']").length,
    skip_in_main_count: document.querySelectorAll("[role='main'] a.public-skip-link[href='#public-page-answer']").length,
    traceback_visible: body.innerText.includes("Traceback (most recent call last)"),
    spinner_count: document.querySelectorAll("[data-testid='stSpinner']").length,
    positive_tabindex_count: [...document.querySelectorAll("[tabindex]")]
      .filter((node) => node.tabIndex > 0).length,
    region_order: regionNodes.map((entry) => entry.name),
    primary_action_focusable_count: primaryActionFocusableCount,
    legacy_pre_answer_action_count: legacyPreAnswerActions.length,
    overflow_nodes: overflowNodes,
  };
}
"""
    )


def _focus_sequence_observation(page: Any) -> dict[str, object]:
    page.evaluate(
        "() => document.activeElement instanceof HTMLElement && document.activeElement.blur()"
    )
    focused_roles: list[str] = []
    outline_widths: list[float] = []
    for _ in range(20):
        page.keyboard.press("Tab")
        observed = page.evaluate(
            """
() => {
  const element = document.activeElement;
  let role = "other";
  if (element.matches("a.public-skip-link")) role = "skip";
  else if (element.closest("nav[aria-label='Personal research workflow']")) role = "navigation";
  else if (element.matches("[data-sr-region='primary-action']")) role = "primary-action";
  else if (element.matches("summary")) role = "advanced-detail";
  const style = getComputedStyle(element);
  return {
    role,
    outline_width: Number.parseFloat(style.outlineWidth) || 0,
  };
}
"""
        )
        focused_roles.append(str(observed.get("role") or "other"))
        outline_widths.append(float(observed.get("outline_width") or 0))
        if observed.get("role") == "advanced-detail":
            break
    return {
        "focused_roles": focused_roles,
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
                "passed": observation.get("research_current_count") == 0,
                "detail": f"current core item count={observation.get('research_current_count')}",
            }
        )
    if route.slug in {"research-desk", "discover", "company-workbench", "monitor"}:
        required = ("primary-answer", "primary-action", "stop-rule")
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
            if observed_width >= 1280:
                hierarchy_passed = all(
                    name in boxes
                    and float(boxes[name].get("bottom") or 0) <= observed_height + 1
                    for name in required
                )
                detail = (
                    "answer, action, and stop rule fully inside the observed desktop viewport "
                    f"{observed_width:.0f}x{observed_height:.0f}"
                )
            else:
                hierarchy_passed = all(
                    name in boxes
                    and float(boxes[name].get("top") or observed_height + 2)
                    <= observed_height + 1
                    for name in required
                )
                detail = (
                    "answer, action, and stop-rule starts inside the observed phone viewport "
                    f"{observed_width:.0f}x{observed_height:.0f}"
                )
            checks.append(
                {"name": "initial_viewport_hierarchy", "passed": hierarchy_passed, "detail": detail}
            )
    if route.slug in {"research-desk", "discover", "company-workbench", "monitor"}:
        checks.append(
            {
                "name": "one_stop_rule",
                "passed": region_counts.get("stop-rule") == 1,
                "detail": f"stop-rule count={region_counts.get('stop-rule', 0)}",
            }
        )
    if route.slug in {"discover", "company-workbench", "monitor"}:
        add(
            "personal_route_answer_hierarchy",
            evaluate_personal_route_hierarchy(
                slug=route.slug,
                region_counts={str(name): int(count) for name, count in region_counts.items()},
                region_order=tuple(
                    str(value) for value in observation.get("region_order") or ()
                ),
                primary_action_focusable_count=int(
                    observation.get("primary_action_focusable_count") or 0
                ),
                legacy_pre_answer_action_count=int(
                    observation.get("legacy_pre_answer_action_count") or 0
                ),
            ),
        )
    if route.slug == "research-desk":
        for media_mode in ("normal", "forced-colors"):
            sequence = focus_sequences.get(media_mode) or {}
            add(
                f"natural_focus_sequence_{media_mode}",
                evaluate_focus_sequence(
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
    checks.extend(
        (
            {
                "name": "no_console_or_page_errors",
                "passed": not console_errors,
                "detail": "no console/page errors" if not console_errors else "; ".join(console_errors),
            },
            {
                "name": "no_traceback_or_loading_capture",
                "passed": observation.get("traceback_visible") is False and observation.get("spinner_count") == 0,
                "detail": f"traceback={observation.get('traceback_visible')}; spinners={observation.get('spinner_count')}",
            },
        )
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
        return {
            "route": route.slug,
            "viewport": f"{viewport[0]}x{viewport[1]}",
            "zoom": zoom,
            "passed": False,
            "screenshot": "",
            "checks": [],
            "error": "Chrome-compatible browser runtime is unavailable.",
            "log": "Chrome-compatible browser runtime is unavailable.",
        }
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {
            "route": route.slug,
            "viewport": f"{viewport[0]}x{viewport[1]}",
            "zoom": zoom,
            "passed": False,
            "screenshot": "",
            "checks": [],
            "error": "Playwright browser runtime is unavailable.",
            "log": "Playwright browser runtime is unavailable.",
        }

    console_errors: list[str] = []
    server_log = ""
    try:
        with _captured_local_demo_server(
            root,
            timeout_seconds=max(5.0, timeout_seconds),
        ) as server:
            host = str(urlsplit(server.base_url).hostname or "")
            if host not in {"127.0.0.1", "localhost"}:
                raise RuntimeError(f"browser zoom profile requires a local host, got {host!r}")
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

                        page.emulate_media(
                            reduced_motion="no-preference",
                            forced_colors="none",
                        )
                        load_route()
                        observation = _browser_observation(page)
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
                        if route.slug == "research-desk":
                            focus_sequences["normal"] = _focus_sequence_observation(page)
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
                        if route.slug == "research-desk":
                            load_route()
                            focus_sequences["forced-colors"] = _focus_sequence_observation(page)
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
                    finally:
                        context.close()
            server_log = "\n".join(server.snapshot())
    except Exception as exc:
        return {
            "route": route.slug,
            "viewport": f"{viewport[0]}x{viewport[1]}",
            "zoom": zoom,
            "passed": False,
            "screenshot": screenshot_name if (output_dir / screenshot_name).exists() else "",
            "checks": [],
            "error": f"{type(exc).__name__}: {exc}",
            "log": server_log,
        }
    return {
        "route": route.slug,
        "viewport": f"{viewport[0]}x{viewport[1]}",
        "zoom": zoom,
        "passed": bool(checks) and all(bool(check["passed"]) for check in checks),
        "screenshot": screenshot_name,
        "checks": checks,
        "log": server_log,
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
                    result = {
                        "route": route.slug,
                        "viewport": f"{viewport[0]}x{viewport[1]}",
                        "zoom": zoom,
                        "passed": False,
                        "screenshot": "",
                        "checks": [],
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                log = str(result.pop("log", "") or "").strip()
                logs.append(
                    f"[{route.slug} {viewport[0]}x{viewport[1]} zoom={zoom}]\n"
                    + (log or "No server warnings or errors captured.")
                )
                results.append(result)
    failures = [
        f"{result['route']} {result['viewport']} zoom={result['zoom']}"
        for result in results
        if not result.get("passed")
    ]
    payload = {
        "verdict": "passed" if results and not failures else "failed",
        "commit": _git_commit(root),
        "environment": f"{platform.system()} {platform.machine()}",
        "routes": [route.slug for route in selected_routes],
        "viewports": [f"{width}x{height}" for width, height in selected_viewports],
        "zooms": list(selected_zooms),
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
