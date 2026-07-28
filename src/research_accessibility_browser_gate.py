"""Read-only direct-browser checks for narrow Personal Research accessibility repairs."""

from __future__ import annotations

import argparse
import contextlib
import ipaddress
import json
import os
import platform
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qs, urlparse

from scripts.diff_hygiene import (
    StatusEntry,
    classify_path,
    load_staged_status,
    load_status,
)
from src.paths import resolve_project_root
from src.public_performance_gate import (
    _git_commit,
    _horizontal_overflow_pixels,
    _local_demo_server,
    _wait_for_dom_stability,
    _wait_for_visible_text,
    find_chrome_executable,
)


VIEWPORTS: tuple[tuple[int, int], ...] = ((1280, 720), (390, 844))
DATA_PROFILE_CONTRACT = ("STOCK_RESEARCH_DATA_PROFILE", "demo")
EXPECTED_APP_TITLE = "Stock Research Command Center"
EXPECTED_PROFILE_LABEL = "Demo"
EXPECTED_MAIN_ID = "research-main"
EXPECTED_MAIN_LABEL = "Stock research workspace"
EXPECTED_MAIN_STATUS = "applied"


@dataclass(frozen=True)
class ResearchRoute:
    name: str
    route: str
    marker: str
    expected_h1: str
    requires_primary_navigation: bool = True


RESEARCH_ROUTES: tuple[ResearchRoute, ...] = (
    ResearchRoute(
        "Research Desk",
        "/?mode=research&page=research-desk",
        "Weekly research summary",
        "Research Desk",
    ),
    ResearchRoute(
        "Discover",
        "/?mode=research&page=discover",
        "Which stock can I review?",
        "Discover",
    ),
    ResearchRoute(
        "Company Workbench",
        "/?mode=research&page=company-workbench&ticker=NVDA&open=1",
        "Company Workbench",
        "Company Workbench",
    ),
    ResearchRoute(
        "Monitor",
        "/?mode=research&page=monitor",
        "WEEKLY RESEARCH SUMMARY",
        "Monitor",
    ),
    ResearchRoute(
        "Research Data Health",
        "/?mode=research&page=data-health&ticker=NVDA",
        "Data Health",
        "Data Health",
        requires_primary_navigation=False,
    ),
    ResearchRoute(
        "Research Proof History",
        "/?mode=research&page=proof-history&ticker=NVDA",
        "Proof History",
        "Proof History",
        requires_primary_navigation=False,
    ),
)


def validated_loopback_base_url(base_url: str) -> str | None:
    """Return one normalized loopback root URL or fail closed."""

    try:
        parsed = urlparse(str(base_url or "").strip())
        port = parsed.port
    except ValueError:
        return None
    if (
        parsed.scheme != "http"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        return None
    hostname = parsed.hostname.lower()
    if hostname != "localhost":
        try:
            if not ipaddress.ip_address(hostname).is_loopback:
                return None
        except ValueError:
            return None
    display_host = f"[{hostname}]" if ":" in hostname else hostname
    port_suffix = f":{port}" if port is not None else ""
    return f"http://{display_host}{port_suffix}"


def evaluate_demo_app_identity(
    *,
    page_title: str,
    brand_text: str,
    profile_label: str,
    profile_caption: str,
) -> dict[str, object]:
    """Require the expected app shell and the rendered demo data profile."""

    observed = {
        "page_title": str(page_title or "").strip(),
        "brand_text": str(brand_text or "").strip(),
        "profile_label": str(profile_label or "").strip(),
        "profile_caption": str(profile_caption or "").strip(),
    }
    passed = (
        observed["page_title"] == EXPECTED_APP_TITLE
        and observed["brand_text"] == EXPECTED_APP_TITLE
        and observed["profile_label"] == EXPECTED_PROFILE_LABEL
        and observed["profile_caption"].lower() == "data profile: demo"
    )
    return {
        "passed": passed,
        "detail": (
            "rendered Stock Research Command Center demo profile identity verified"
            if passed
            else f"rendered app/profile identity mismatch: {observed}"
        ),
    }


def evaluate_repository_hygiene(
    entries: Iterable[StatusEntry],
    *,
    staged_entries: Iterable[StatusEntry],
) -> dict[str, object]:
    """Allow only unstaged generated churn classified by the hygiene contract."""

    status_entries = tuple(entries)
    staged = tuple(staged_entries)
    staged_paths = sorted({entry.path for entry in staged})
    excluded_generated_paths = sorted(
        {
            entry.path
            for entry in status_entries
            if classify_path(entry.path) == "generated_csv_churn"
            and entry.path not in staged_paths
        }
    )
    dirty_product_paths = sorted(
        {
            entry.path
            for entry in status_entries
            if classify_path(entry.path) != "generated_csv_churn"
        }
    )
    passed = not staged_paths and not dirty_product_paths
    return {
        "passed": passed,
        "dirty_product_paths": dirty_product_paths,
        "staged_paths": staged_paths,
        "excluded_generated_paths": excluded_generated_paths,
        "detail": (
            f"product tree clean; {len(excluded_generated_paths)} unstaged generated "
            "artifact(s) classified and excluded"
            if passed
            else (
                f"dirty product/manual paths={dirty_product_paths}; "
                f"staged paths={staged_paths}"
            )
        ),
    }


def _repository_hygiene(root: Path) -> dict[str, object]:
    try:
        return evaluate_repository_hygiene(
            load_status(root),
            staged_entries=load_staged_status(root),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {
            "passed": False,
            "dirty_product_paths": [],
            "staged_paths": [],
            "excluded_generated_paths": [],
            "detail": (
                "repository hygiene could not be verified and failed closed: "
                f"{type(exc).__name__}: {exc}"
            ),
        }


def evaluate_discover_action_names(names: Iterable[str]) -> dict[str, object]:
    """Evaluate exactly the eligible Discover actions rendered by the browser."""

    actual = [str(name).strip() for name in names]
    if not actual:
        return {
            "passed": False,
            "actual_count": 0,
            "detail": "no eligible Discover actions were rendered",
        }
    ticker_names = [
        name[len("Open ") : -len(" review")]
        for name in actual
        if name.startswith("Open ")
        and name.endswith(" review")
        and name[len("Open ") : -len(" review")].strip()
    ]
    if len(ticker_names) != len(actual):
        return {
            "passed": False,
            "actual_count": len(actual),
            "detail": "every eligible Discover action must use Open {TICKER} review",
        }
    if len(set(ticker_names)) != len(ticker_names):
        return {
            "passed": False,
            "actual_count": len(actual),
            "detail": "eligible Discover action names are not unique",
        }
    return {
        "passed": True,
        "actual_count": len(actual),
        "detail": (
            f"{len(actual)} eligible Discover actions have unique "
            "ticker-specific names"
        ),
    }


def evaluate_skip_geometry(
    rectangle: dict[str, float] | None,
    *,
    viewport_width: int,
    viewport_height: int,
) -> dict[str, object]:
    """Require a focused skip link to be usable and fully inside the viewport."""

    if not rectangle or viewport_width <= 0 or viewport_height <= 0:
        return {
            "passed": False,
            "detail": "focused skip geometry or viewport bounds are unavailable",
        }
    x = float(rectangle.get("x", 0))
    y = float(rectangle.get("y", 0))
    width = float(rectangle.get("width", 0))
    height = float(rectangle.get("height", 0))
    right = x + width
    bottom = y + height
    passed = (
        width > 0
        and height > 0
        and x >= 0
        and y >= 0
        and right <= float(viewport_width)
        and bottom <= float(viewport_height)
    )
    return {
        "passed": passed,
        "detail": (
            f"focused skip geometry x={x:.1f}..{right:.1f}, "
            f"y={y:.1f}..{bottom:.1f} "
            f"{'within' if passed else 'outside'} "
            f"{viewport_width}x{viewport_height} viewport"
        ),
    }


def evaluate_viewport_geometry(
    rectangle: dict[str, float] | None,
    *,
    viewport: tuple[int, int],
    expected_min_height: float,
    label: str,
) -> dict[str, object]:
    """Require usable geometry inside the horizontal viewport and on screen."""

    viewport_width, viewport_height = viewport
    if (
        not rectangle
        or viewport_width <= 0
        or viewport_height <= 0
        or expected_min_height <= 0
    ):
        return {
            "passed": False,
            "detail": f"{label} geometry or viewport contract is unavailable",
        }
    x = float(rectangle.get("x", 0))
    y = float(rectangle.get("y", 0))
    width = float(rectangle.get("width", 0))
    height = float(rectangle.get("height", 0))
    right = x + width
    bottom = y + height
    passed = (
        width > 0
        and height >= expected_min_height
        and x >= 0
        and right <= float(viewport_width)
        and bottom > 0
        and y < float(viewport_height)
    )
    return {
        "passed": passed,
        "detail": (
            f"{label} geometry x={x:.1f}..{right:.1f}, "
            f"y={y:.1f}..{bottom:.1f}, height={height:.1f}px "
            f"{'meets' if passed else 'fails'} viewport and "
            f"{expected_min_height:.1f}px height contract"
        ),
    }


def _assertion(name: str, passed: bool, detail: str) -> dict[str, object]:
    return {"name": name, "passed": bool(passed), "detail": str(detail)}


def evaluate_semantic_main_landmark(
    *,
    main_count: int,
    main_role: str | None,
    main_id: str | None,
    main_label: str | None,
    answer_count: int,
    h1_count: int,
    bridge_status: str | None,
    phase: str,
) -> list[dict[str, object]]:
    """Require the complete semantic-main contract for one DOM snapshot."""

    phase_name = str(phase or "snapshot").strip().lower().replace(" ", "_")
    unique = main_count == 1
    return [
        _assertion(
            f"semantic_main_{phase_name}_unique",
            unique,
            f"role-based main count={main_count}",
        ),
        _assertion(
            f"semantic_main_{phase_name}_metadata",
            (
                unique
                and main_role == "main"
                and main_id == EXPECTED_MAIN_ID
                and main_label == EXPECTED_MAIN_LABEL
            ),
            (
                f"role={main_role!r}; id={main_id!r}; "
                f"aria-label={main_label!r}"
            ),
        ),
        _assertion(
            f"semantic_main_{phase_name}_answer",
            unique and answer_count == 1,
            f"#public-page-answer descendants={answer_count}",
        ),
        _assertion(
            f"semantic_main_{phase_name}_h1",
            unique and h1_count == 1,
            f"level-one heading descendants={h1_count}",
        ),
        _assertion(
            f"semantic_main_{phase_name}_bridge_status",
            unique and bridge_status == EXPECTED_MAIN_STATUS,
            f"bridge status={bridge_status!r}",
        ),
    ]


def evaluate_skip_target_containment(
    *,
    main_count: int,
    target_count: int,
    active_id: str | None,
    target_inside_main: bool,
) -> dict[str, object]:
    """Require the activated skip target to be focused inside the unique main."""

    passed = (
        main_count == 1
        and target_count == 1
        and active_id == "public-page-answer"
        and target_inside_main
    )
    return _assertion(
        "skip_target_inside_semantic_main",
        passed,
        (
            f"main_count={main_count}; target_count={target_count}; "
            f"active_id={active_id!r}; inside_main={target_inside_main}"
        ),
    )


def evaluate_browser_errors(errors: Iterable[str]) -> dict[str, object]:
    """Reject any browser console error or uncaught page error."""

    observed = [str(error).strip() for error in errors if str(error).strip()]
    return _assertion(
        "no_browser_errors",
        not observed,
        "no console or page errors" if not observed else "; ".join(observed),
    )


def evaluate_same_document_streamlit_rerun(
    *,
    trigger_count: int,
    initial_observer_available: bool,
    token_before: str,
    token_after: str,
    same_document: bool,
    top_level_navigation_count: int,
    observer_replaced: bool,
    active_target: bool,
    bridge_status: str | None,
    route_before: str,
    route_after: str,
) -> list[dict[str, object]]:
    """Require one real Streamlit rerun without replacing the top document."""

    return [
        _assertion(
            "streamlit_rerun_trigger_available",
            trigger_count == 1,
            f"Public visitor mode workspace radio count={trigger_count}",
        ),
        _assertion(
            "streamlit_rerun_initial_observer_available",
            initial_observer_available,
            f"initial semantic-main observer available={initial_observer_available}",
        ),
        _assertion(
            "streamlit_rerun_same_document",
            (
                bool(token_before)
                and token_before == token_after
                and same_document
            ),
            (
                f"probe token preserved={bool(token_before) and token_before == token_after}; "
                f"document retained={same_document}"
            ),
        ),
        _assertion(
            "streamlit_rerun_no_top_level_navigation",
            top_level_navigation_count == 0,
            f"top-level frame navigations={top_level_navigation_count}",
        ),
        _assertion(
            "streamlit_rerun_observer_replaced",
            observer_replaced,
            f"semantic-main observer replaced={observer_replaced}",
        ),
        _assertion(
            "streamlit_rerun_active_target",
            active_target,
            f"bridge target is current stMain={active_target}",
        ),
        _assertion(
            "streamlit_rerun_bridge_status",
            bridge_status == EXPECTED_MAIN_STATUS,
            f"bridge status={bridge_status!r}",
        ),
        _assertion(
            "streamlit_rerun_route_preserved",
            bool(route_before) and route_before == route_after,
            f"route before={route_before!r}; after={route_after!r}",
        ),
    ]


def _same_document_streamlit_rerun_assertions(
    page: Any,
    *,
    timeout_seconds: float,
) -> list[dict[str, object]]:
    top_level_navigations: list[str] = []

    def capture_top_level_navigation(frame: Any) -> None:
        if frame == page.main_frame:
            top_level_navigations.append("top-level")

    page.on("framenavigated", capture_top_level_navigation)
    trigger = page.get_by_role(
        "radio",
        name="Public visitor mode",
        exact=True,
    )
    trigger_count = trigger.count()
    if trigger_count != 1:
        return evaluate_same_document_streamlit_rerun(
            trigger_count=trigger_count,
            initial_observer_available=False,
            token_before="",
            token_after="",
            same_document=False,
            top_level_navigation_count=len(top_level_navigations),
            observer_replaced=False,
            active_target=False,
            bridge_status=None,
            route_before="",
            route_after="",
        )

    before = page.evaluate(
        """
() => {
  const probeKey = "__a11ySameDocumentRerunProbe";
  const token = `${Date.now()}-${Math.random()}`;
  const route = `${location.pathname}${location.search}`;
  window[probeKey] = {
    token,
    document: document,
    observer: window.__stockResearchMainObserver,
    target: window.__stockResearchMainTarget,
    route
  };
  return {
    token,
    initial_observer_available: Boolean(window[probeKey].observer),
    route
  };
}
"""
    )
    top_level_navigations.clear()
    trigger.check(force=True)
    page.wait_for_function(
        """
() => {
  const probe = window.__a11ySameDocumentRerunProbe;
  const target = document.querySelector('[data-testid="stMain"]');
  return Boolean(
    probe &&
    probe.document === document &&
    probe.route === `${location.pathname}${location.search}` &&
    window.__stockResearchMainObserver &&
    window.__stockResearchMainObserver !== probe.observer &&
    window.__stockResearchMainTarget === target &&
    document.documentElement.getAttribute(
      "data-research-main-bridge-status"
    ) === "applied"
  );
}
""",
        timeout=int(timeout_seconds * 1000),
    )
    after = page.evaluate(
        """
() => {
  const probe = window.__a11ySameDocumentRerunProbe;
  const target = document.querySelector('[data-testid="stMain"]');
  return {
    token: probe ? probe.token : "",
    same_document: Boolean(probe && probe.document === document),
    observer_replaced: Boolean(
      probe &&
      window.__stockResearchMainObserver &&
      window.__stockResearchMainObserver !== probe.observer
    ),
    active_target: Boolean(
      probe &&
      window.__stockResearchMainTarget === target
    ),
    bridge_status: document.documentElement.getAttribute(
      "data-research-main-bridge-status"
    ),
    route: `${location.pathname}${location.search}`
  };
}
"""
    )
    return evaluate_same_document_streamlit_rerun(
        trigger_count=trigger_count,
        initial_observer_available=bool(
            before.get("initial_observer_available")
        ),
        token_before=str(before.get("token") or ""),
        token_after=str(after.get("token") or ""),
        same_document=bool(after.get("same_document")),
        top_level_navigation_count=len(top_level_navigations),
        observer_replaced=bool(after.get("observer_replaced")),
        active_target=bool(after.get("active_target")),
        bridge_status=str(after.get("bridge_status") or ""),
        route_before=str(before.get("route") or ""),
        route_after=str(after.get("route") or ""),
    )


def evaluate_secondary_navigation_absence(
    *,
    navigation_count: int,
    phase: str,
) -> dict[str, object]:
    """Require secondary evidence routes to omit the primary workflow nav."""

    phase_name = str(phase or "snapshot").strip().lower().replace(" ", "_")
    return _assertion(
        f"secondary_workflow_navigation_absent_{phase_name}",
        navigation_count == 0,
        f"labelled primary workflow navigation count={navigation_count}",
    )


def _secondary_navigation_absence_assertion(
    page: Any,
    *,
    phase: str,
) -> dict[str, object]:
    navigation_count = page.locator(
        "nav[aria-label='Personal research workflow']"
    ).count()
    return evaluate_secondary_navigation_absence(
        navigation_count=navigation_count,
        phase=phase,
    )


def _semantic_main_assertions(
    page: Any,
    *,
    phase: str,
) -> list[dict[str, object]]:
    mains = page.get_by_role("main")
    main_count = mains.count()
    main = mains.first if main_count == 1 else None
    return evaluate_semantic_main_landmark(
        main_count=main_count,
        main_role=main.get_attribute("role") if main is not None else None,
        main_id=main.get_attribute("id") if main is not None else None,
        main_label=main.get_attribute("aria-label") if main is not None else None,
        answer_count=(
            main.locator("#public-page-answer").count() if main is not None else 0
        ),
        h1_count=(
            main.get_by_role("heading", level=1).count() if main is not None else 0
        ),
        bridge_status=page.locator("html").get_attribute(
            "data-research-main-bridge-status"
        ),
        phase=phase,
    )


def _skip_link_assertions(page: Any) -> list[dict[str, object]]:
    skip_links = page.locator("a.public-skip-link[href='#public-page-answer']")
    count = skip_links.count()
    if count != 1:
        return [
            _assertion(
                "skip_link_first_physical_tab",
                False,
                f"expected one skip link before keyboard traversal, found {count}",
            )
        ]

    page.evaluate(
        """
() => {
  if (document.activeElement && document.activeElement !== document.body) {
    document.activeElement.blur();
  }
  document.body.setAttribute("tabindex", "-1");
  document.body.focus({preventScroll: true});
}
"""
    )
    page.keyboard.press("Tab")
    page.evaluate("document.body.removeAttribute('tabindex')")
    active_is_skip = bool(
        skip_links.first.evaluate("element => document.activeElement === element")
    )
    active_description = page.evaluate(
        """
() => {
  const active = document.activeElement;
  if (!active) return "none";
  return active.getAttribute("aria-label") ||
    active.textContent.trim() ||
    active.tagName.toLowerCase();
}
"""
    )
    results = [
        _assertion(
            "skip_link_first_physical_tab",
            active_is_skip,
            (
                "one physical Tab focused the sole skip link"
                if active_is_skip
                else f"one physical Tab focused {active_description!r}"
            ),
        )
    ]
    if not active_is_skip:
        results.extend(
            (
                _assertion(
                    "skip_link_focused_geometry",
                    False,
                    "skip link was not keyboard-focused; geometry not credited",
                ),
                _assertion(
                    "skip_link_activation",
                    False,
                    "skip link was not keyboard-focused; Enter was not sent",
                ),
                _assertion(
                    "skip_target_inside_semantic_main",
                    False,
                    "skip link was not keyboard-focused; containment not credited",
                ),
            )
        )
        return results

    geometry = evaluate_skip_geometry(
        skip_links.first.bounding_box(),
        viewport_width=int(page.evaluate("window.innerWidth")),
        viewport_height=int(page.evaluate("window.innerHeight")),
    )
    results.append(
        _assertion(
            "skip_link_focused_geometry",
            bool(geometry["passed"]),
            str(geometry["detail"]),
        )
    )
    before = urlparse(page.url)
    page.keyboard.press("Enter")
    page.wait_for_timeout(150)
    after = urlparse(page.url)
    active_id = page.evaluate("document.activeElement && document.activeElement.id")
    preserved = (
        before.scheme,
        before.netloc,
        before.path,
        before.query,
    ) == (
        after.scheme,
        after.netloc,
        after.path,
        after.query,
    )
    passed = (
        preserved
        and after.fragment == "public-page-answer"
        and active_id == "public-page-answer"
    )
    results.append(
        _assertion(
            "skip_link_activation",
            passed,
            (
                "activation preserved route and focused #public-page-answer"
                if passed
                else (
                    f"preserved_route={preserved}; fragment={after.fragment!r}; "
                    f"active_id={active_id!r}"
                )
            ),
        )
    )
    mains = page.get_by_role("main")
    main_count = mains.count()
    targets = page.locator("#public-page-answer")
    target_count = targets.count()
    target_inside_main = (
        main_count == 1
        and target_count == 1
        and mains.first.locator("#public-page-answer").count() == 1
    )
    results.append(
        evaluate_skip_target_containment(
            main_count=main_count,
            target_count=target_count,
            active_id=active_id,
            target_inside_main=target_inside_main,
        )
    )
    return results


def _navigation_assertion(page: Any, route: ResearchRoute) -> dict[str, object]:
    navigation = page.locator("nav[aria-label='Personal research workflow']")
    count = navigation.count()
    if count != 1 or not navigation.first.is_visible():
        return _assertion(
            "labelled_workflow_navigation",
            False,
            f"expected one visible labelled navigation, found {count}",
        )
    links = navigation.first.locator("a.research-workflow-link")
    link_names = [
        text.strip()
        for text in links.all_inner_texts()
    ]
    current = navigation.first.locator("a[aria-current='page']").all_inner_texts()
    expected = ["Research Desk", "Discover"]
    if route.name == "Company Workbench":
        expected.append("Company Workbench")
    expected.append("Monitor")
    viewport = (
        int(page.evaluate("window.innerWidth")),
        int(page.evaluate("window.innerHeight")),
    )
    navigation_geometry = evaluate_viewport_geometry(
        navigation.first.bounding_box(),
        viewport=viewport,
        expected_min_height=1,
        label="workflow navigation",
    )
    link_geometry = [
        evaluate_viewport_geometry(
            links.nth(index).bounding_box(),
            viewport=viewport,
            expected_min_height=44,
            label=label,
        )
        for index, label in enumerate(link_names)
    ]
    geometry_passed = bool(navigation_geometry["passed"]) and all(
        bool(result["passed"]) for result in link_geometry
    )
    passed = (
        link_names == expected
        and current == [route.name]
        and geometry_passed
    )
    geometry_detail = "; ".join(
        [
            str(navigation_geometry["detail"]),
            *(str(result["detail"]) for result in link_geometry),
        ]
    )
    return _assertion(
        "labelled_workflow_navigation",
        passed,
        (
            f"visible route sequence {link_names} with current {current}; {geometry_detail}"
            if passed
            else (
                f"expected={expected}; actual={link_names}; current={current}; "
                f"{geometry_detail}"
            )
        ),
    )


def _discover_action_assertion(page: Any) -> dict[str, object]:
    links = page.locator("a.selector-action-link")
    names = [name.strip() for name in links.all_inner_texts()]
    evaluated = evaluate_discover_action_names(names)
    href_matches = True
    for index, name in enumerate(names):
        href = links.nth(index).get_attribute("href") or ""
        ticker = parse_qs(urlparse(href).query).get("ticker", [""])[0].strip().upper()
        if not ticker or name != f"Open {ticker} review":
            href_matches = False
            break
    passed = bool(evaluated["passed"]) and href_matches
    detail = str(evaluated["detail"])
    if evaluated["passed"] and not href_matches:
        detail = "an eligible Discover action name does not match its ticker route"
    return _assertion("discover_action_names", passed, detail)


def _summary_focus_assertion(page: Any) -> dict[str, object]:
    summaries = page.locator("summary:visible")
    count = summaries.count()
    if count < 1:
        return _assertion(
            "summary_focus_outline",
            False,
            "no visible disclosure summary was available for the direct focus retest",
        )
    summary = summaries.first
    summary.focus()
    style = summary.evaluate(
        """
element => {
  const computed = getComputedStyle(element);
  return {
    style: computed.outlineStyle,
    width: computed.outlineWidth,
    color: computed.outlineColor
  };
}
"""
    )
    passed = style["style"] != "none" and style["width"] not in ("0px", "0")
    return _assertion(
        "summary_focus_outline",
        passed,
        f"focused summary outline={style}",
    )


def _authoring_error_assertions(page: Any) -> list[dict[str, object]]:
    composer = page.locator("details").filter(
        has=page.get_by_text("Add a reviewed research record", exact=True)
    )
    if composer.count() != 1:
        return [
            _assertion(
                "authoring_field_error_association",
                False,
                f"expected one authoring disclosure, found {composer.count()}",
            )
        ]
    composer.locator("summary").click()
    validate = page.get_by_role("button", name="Validate and preview", exact=True)
    if validate.count() != 1:
        return [
            _assertion(
                "authoring_field_error_association",
                False,
                f"expected one validation button, found {validate.count()}",
            )
        ]
    validate.click()
    page.locator(
        '[aria-label="Thesis Id"][aria-invalid="true"]'
    ).wait_for(state="attached", timeout=10_000)
    field = page.locator('[aria-label="Thesis Id"][aria-invalid="true"]')
    described_by = field.get_attribute("aria-describedby") or ""
    error = page.locator(f"#{described_by}") if described_by else page.locator(
        "#__missing-authoring-error"
    )
    global_alerts = page.get_by_role("alert").filter(
        has_text="thesis_id is required"
    )
    active_label = page.evaluate(
        "document.activeElement && document.activeElement.getAttribute('aria-label')"
    )
    passed = (
        field.count() == 1
        and bool(described_by)
        and error.count() == 1
        and error.first.inner_text().strip() == "thesis_id is required"
        and global_alerts.count() == 1
        and active_label == "Thesis Id"
    )
    first_result = _assertion(
        "authoring_field_error_association",
        passed,
        (
            "one Thesis Id field is invalid, described, focused, and retains one alert"
            if passed
            else (
                f"field_count={field.count()}; described_by={described_by!r}; "
                f"error_count={error.count()}; alert_count={global_alerts.count()}; "
                f"active_label={active_label!r}"
            )
        ),
    )
    if not passed:
        return [first_result]

    field.fill("thesis-browser-regression")
    field.press("Tab")
    try:
        error.first.wait_for(state="detached", timeout=10_000)
        _wait_for_dom_stability(page, timeout_seconds=10)
    except Exception as exc:
        return [
            first_result,
            _assertion(
                "authoring_field_error_cleanup_transition",
                False,
                f"old Thesis Id error did not clear after draft change: {type(exc).__name__}: {exc}",
            ),
        ]

    thesis_after_change = page.get_by_label("Thesis Id", exact=True)
    stale_thesis_clean = (
        thesis_after_change.get_attribute("aria-invalid") is None
        and thesis_after_change.get_attribute("aria-describedby") is None
        and page.locator(f"#{described_by}").count() == 0
    )
    validate = page.get_by_role("button", name="Validate and preview", exact=True)
    validate.click()
    effective = page.locator('[aria-label="Effective At"][aria-invalid="true"]')
    try:
        effective.wait_for(state="attached", timeout=10_000)
    except Exception as exc:
        return [
            first_result,
            _assertion(
                "authoring_field_error_cleanup_transition",
                False,
                (
                    f"Effective At did not receive the next required error: "
                    f"{type(exc).__name__}: {exc}"
                ),
            ),
        ]
    effective_described_by = effective.get_attribute("aria-describedby") or ""
    effective_error = (
        page.locator(f"#{effective_described_by}")
        if effective_described_by
        else page.locator("#__missing-effective-at-error")
    )
    effective_alerts = page.get_by_role("alert").filter(
        has_text="effective_at is required"
    )
    active_label = page.evaluate(
        "document.activeElement && document.activeElement.getAttribute('aria-label')"
    )
    thesis_after_validation = page.get_by_label("Thesis Id", exact=True)
    passed_transition = (
        stale_thesis_clean
        and thesis_after_validation.get_attribute("aria-invalid") is None
        and thesis_after_validation.get_attribute("aria-describedby") is None
        and effective.count() == 1
        and bool(effective_described_by)
        and effective_error.count() == 1
        and effective_error.first.inner_text().strip() == "effective_at is required"
        and effective_alerts.count() == 1
        and active_label == "Effective At"
    )
    return [
        first_result,
        _assertion(
            "authoring_field_error_cleanup_transition",
            passed_transition,
            (
                "draft change cleared the bridge-owned Thesis Id state and the next "
                "validation bound only Effective At"
                if passed_transition
                else (
                    f"stale_thesis_clean={stale_thesis_clean}; "
                    f"effective_count={effective.count()}; "
                    f"effective_described_by={effective_described_by!r}; "
                    f"effective_error_count={effective_error.count()}; "
                    f"alert_count={effective_alerts.count()}; "
                    f"active_label={active_label!r}"
                )
            ),
        ),
    ]


def _demo_app_identity_assertion(
    browser: Any,
    *,
    base_url: str,
    timeout_seconds: float,
) -> dict[str, object]:
    context = browser.new_context(viewport={"width": 1280, "height": 720})
    page = context.new_page()
    try:
        route = RESEARCH_ROUTES[0]
        page.goto(
            f"{base_url.rstrip('/')}{route.route}",
            wait_until="domcontentloaded",
            timeout=int(timeout_seconds * 1000),
        )
        _wait_for_visible_text(page, route.marker, timeout_seconds=timeout_seconds)
        _wait_for_dom_stability(page, timeout_seconds=timeout_seconds)
        brands = [
            value.strip()
            for value in page.locator(".sidebar-nav-title").all_text_contents()
            if value.strip()
        ]
        profile_labels = [
            value.strip()
            for value in page.locator(
                "section[aria-label='Selected data profile and saved readiness'] strong"
            ).all_text_contents()
            if value.strip()
        ]
        captions = [
            value.strip()
            for value in page.locator(
                '[data-testid="stSidebar"] [data-testid="stCaptionContainer"]'
            ).all_text_contents()
            if value.strip().lower().startswith("data profile:")
        ]
        return evaluate_demo_app_identity(
            page_title=page.title(),
            brand_text=brands[0] if len(brands) == 1 else "",
            profile_label=profile_labels[0] if len(profile_labels) == 1 else "",
            profile_caption=captions[0] if len(captions) == 1 else "",
        )
    except Exception as exc:
        return {
            "passed": False,
            "detail": (
                "rendered app/profile identity could not be verified: "
                f"{type(exc).__name__}: {exc}"
            ),
        }
    finally:
        context.close()


def _runtime_dom_assertions(
    page: Any,
    *,
    phase: str,
) -> list[dict[str, object]]:
    body = page.locator("body").inner_text()
    traceback = "Traceback (most recent call last)" in body
    suffix = "" if phase == "initial" else f"_{phase}"
    overflow = _horizontal_overflow_pixels(page)
    return [
        _assertion(
            f"no_traceback{suffix}",
            not traceback,
            "no traceback rendered" if not traceback else "traceback rendered",
        ),
        _assertion(
            f"no_horizontal_overflow{suffix}",
            overflow <= 1,
            f"horizontal overflow={overflow}px",
        ),
    ]


def _wait_for_route_heading(
    page: Any,
    route: ResearchRoute,
    *,
    timeout_seconds: float,
) -> None:
    page.get_by_role("main").get_by_role(
        "heading",
        level=1,
        name=route.expected_h1,
        exact=True,
    ).wait_for(
        state="visible",
        timeout=int(timeout_seconds * 1000),
    )


def _measure_route(
    browser: Any,
    *,
    base_url: str,
    route: ResearchRoute,
    viewport: tuple[int, int],
    timeout_seconds: float,
) -> dict[str, object]:
    width, height = viewport
    context = browser.new_context(viewport={"width": width, "height": height})
    page = context.new_page()
    assertions: list[dict[str, object]] = []
    browser_errors: list[str] = []

    def capture_console_error(message: Any) -> None:
        if str(message.type).lower() == "error":
            browser_errors.append(f"console error: {message.text}")

    def capture_page_error(error: Any) -> None:
        browser_errors.append(f"page error: {error}")

    page.on("console", capture_console_error)
    page.on("pageerror", capture_page_error)
    try:
        page.goto(
            f"{base_url.rstrip('/')}{route.route}",
            wait_until="domcontentloaded",
            timeout=int(timeout_seconds * 1000),
        )
        _wait_for_visible_text(page, route.marker, timeout_seconds=timeout_seconds)
        _wait_for_dom_stability(page, timeout_seconds=timeout_seconds)
        _wait_for_route_heading(page, route, timeout_seconds=timeout_seconds)

        assertions.extend(_semantic_main_assertions(page, phase="initial"))
        assertions.extend(_runtime_dom_assertions(page, phase="initial"))
        if route.requires_primary_navigation:
            assertions.append(_navigation_assertion(page, route))
        else:
            assertions.append(
                _secondary_navigation_absence_assertion(page, phase="initial")
            )
        assertions.extend(_skip_link_assertions(page))
        if route.requires_primary_navigation:
            assertions.append(_summary_focus_assertion(page))
        if route.name == "Discover":
            assertions.append(_discover_action_assertion(page))
        if route.name == "Company Workbench":
            assertions.extend(_authoring_error_assertions(page))

        assertions.extend(
            _same_document_streamlit_rerun_assertions(
                page,
                timeout_seconds=timeout_seconds,
            )
        )
        _wait_for_visible_text(page, route.marker, timeout_seconds=timeout_seconds)
        _wait_for_dom_stability(page, timeout_seconds=timeout_seconds)
        _wait_for_route_heading(page, route, timeout_seconds=timeout_seconds)
        assertions.extend(
            _semantic_main_assertions(page, phase="streamlit_rerun")
        )
        assertions.extend(
            _runtime_dom_assertions(page, phase="streamlit_rerun")
        )
        if not route.requires_primary_navigation:
            assertions.append(
                _secondary_navigation_absence_assertion(page, phase="streamlit_rerun")
            )
    except Exception as exc:
        assertions.append(
            _assertion(
                "route_execution",
                False,
                f"{type(exc).__name__}: {exc}",
            )
        )
    finally:
        assertions.append(evaluate_browser_errors(browser_errors))
        context.close()

    return {
        "route": route.name,
        "viewport": f"{width}x{height}",
        "passed": bool(assertions) and all(
            bool(assertion["passed"]) for assertion in assertions
        ),
        "assertions": assertions,
    }


def _failed_payload(
    failure: str,
    *,
    repository_hygiene: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "verdict": "failed",
        "commit": "",
        "environment": f"{platform.system()} {platform.machine()}",
        "data_profile": "unverified",
        "repository_hygiene": repository_hygiene or {
            "passed": False,
            "dirty_product_paths": [],
            "staged_paths": [],
            "excluded_generated_paths": [],
            "detail": "repository hygiene not verified",
        },
        "viewports": [f"{width}x{height}" for width, height in VIEWPORTS],
        "routes": [route.name for route in RESEARCH_ROUTES],
        "results": [],
        "failures": [failure],
        "boundary": (
            "Read-only engineering evidence only; not WCAG conformance, "
            "screen-reader, independent-human, hosted, or market validation."
        ),
    }


def run_research_accessibility_browser_gate(
    base_dir: Path | str,
    *,
    base_url: str = "",
    chrome_executable: Path | None = None,
    timeout_seconds: float = 45.0,
) -> dict[str, object]:
    """Run deterministic read-only accessibility retests at both viewports."""

    root = resolve_project_root(base_dir)
    normalized_base_url = ""
    if base_url:
        normalized_base_url = validated_loopback_base_url(base_url) or ""
        if not normalized_base_url:
            return _failed_payload(
                "Explicit BASE_URL must be an HTTP loopback root URL; gate failed closed."
            )
    chrome = chrome_executable or find_chrome_executable()
    if chrome is None or not Path(chrome).is_file() or not os.access(chrome, os.X_OK):
        return _failed_payload(
            "Required Chrome-compatible browser runtime is unavailable; gate failed closed.",
        )
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return _failed_payload(
            "Required Playwright browser runtime is unavailable; gate failed closed.",
        )

    repository_hygiene = _repository_hygiene(root)
    if not repository_hygiene["passed"]:
        return _failed_payload(
            "Repository contains staged or dirty non-generated implementation evidence; "
            "gate failed closed.",
            repository_hygiene=repository_hygiene,
        )

    identity: dict[str, object] | None = None
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path=str(chrome),
                headless=True,
            )
            try:
                server_context = (
                    contextlib.nullcontext(normalized_base_url)
                    if normalized_base_url
                    else _local_demo_server(
                        root,
                        timeout_seconds=max(5.0, timeout_seconds),
                    )
                )
                with server_context as active_url:
                    verified_active_url = validated_loopback_base_url(active_url)
                    if not verified_active_url:
                        return _failed_payload(
                            "Active dashboard URL was not loopback; gate failed closed.",
                            repository_hygiene=repository_hygiene,
                        )
                    identity = _demo_app_identity_assertion(
                        browser,
                        base_url=verified_active_url,
                        timeout_seconds=max(5.0, timeout_seconds),
                    )
                    if not identity["passed"]:
                        return _failed_payload(
                            str(identity["detail"]),
                            repository_hygiene=repository_hygiene,
                        )
                    results = [
                        _measure_route(
                            browser,
                            base_url=verified_active_url,
                            route=route,
                            viewport=viewport,
                            timeout_seconds=max(5.0, timeout_seconds),
                        )
                        for viewport in VIEWPORTS
                        for route in RESEARCH_ROUTES
                    ]
            finally:
                browser.close()
    except Exception as exc:
        return _failed_payload(
            f"Browser gate could not execute and failed closed: {type(exc).__name__}: {exc}",
            repository_hygiene=repository_hygiene,
        )

    failures = [
        (
            f"{result['route']} {result['viewport']}: "
            + "; ".join(
                str(assertion["detail"])
                for assertion in result["assertions"]
                if not assertion["passed"]
            )
        )
        for result in results
        if not result["passed"]
    ]
    return {
        "verdict": "passed" if not failures else "failed",
        "commit": _git_commit(root),
        "environment": (
            f"{platform.system()} {platform.machine()} | Chrome: {Path(chrome)}"
        ),
        "data_profile": DATA_PROFILE_CONTRACT[1],
        "app_identity": identity,
        "repository_hygiene": repository_hygiene,
        "viewports": [f"{width}x{height}" for width, height in VIEWPORTS],
        "routes": [route.name for route in RESEARCH_ROUTES],
        "results": results,
        "failures": failures,
        "boundary": (
            "Read-only engineering evidence only; not WCAG conformance, "
            "screen-reader, independent-human, hosted, or market validation."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the read-only Personal Research accessibility browser gate."
    )
    parser.add_argument("--root", default=".")
    parser.add_argument("--base-url", default="")
    parser.add_argument("--chrome", default="")
    parser.add_argument("--timeout-seconds", type=float, default=45.0)
    args = parser.parse_args()
    payload = run_research_accessibility_browser_gate(
        args.root,
        base_url=args.base_url,
        chrome_executable=Path(args.chrome) if args.chrome else None,
        timeout_seconds=max(5.0, args.timeout_seconds),
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["verdict"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
