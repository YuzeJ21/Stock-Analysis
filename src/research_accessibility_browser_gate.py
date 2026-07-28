"""Read-only direct-browser checks for narrow Personal Research accessibility repairs."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import platform
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qs, urlparse

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


@dataclass(frozen=True)
class ResearchRoute:
    name: str
    route: str
    marker: str


RESEARCH_ROUTES: tuple[ResearchRoute, ...] = (
    ResearchRoute(
        "Research Desk",
        "/?mode=research&page=research-desk",
        "Weekly research summary",
    ),
    ResearchRoute(
        "Discover",
        "/?mode=research&page=discover",
        "Which stock can I review?",
    ),
    ResearchRoute(
        "Company Workbench",
        "/?mode=research&page=company-workbench&ticker=NVDA&open=1",
        "Company Workbench",
    ),
    ResearchRoute(
        "Monitor",
        "/?mode=research&page=monitor",
        "WEEKLY RESEARCH SUMMARY",
    ),
)


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
) -> dict[str, object]:
    """Require a focused skip link to be usable and fully inside the viewport."""

    if not rectangle or viewport_width <= 0:
        return {
            "passed": False,
            "detail": "focused skip geometry or viewport width is unavailable",
        }
    x = float(rectangle.get("x", 0))
    width = float(rectangle.get("width", 0))
    height = float(rectangle.get("height", 0))
    right = x + width
    passed = width > 0 and height > 0 and x >= 0 and right <= float(viewport_width)
    return {
        "passed": passed,
        "detail": (
            f"focused skip geometry x={x:.1f}..{right:.1f} "
            f"{'within' if passed else 'outside'} {viewport_width}px viewport"
        ),
    }


def _assertion(name: str, passed: bool, detail: str) -> dict[str, object]:
    return {"name": name, "passed": bool(passed), "detail": str(detail)}


def _visible_application_focus_order(page: Any) -> list[dict[str, str]]:
    return page.evaluate(
        """
() => {
  const selector = [
    "a[href]",
    "button",
    "input",
    "select",
    "textarea",
    "summary",
    "[tabindex]"
  ].join(",");
  const visible = (element) => {
    const style = getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    return style.display !== "none" &&
      style.visibility !== "hidden" &&
      rect.width > 0 &&
      rect.height > 0 &&
      !element.disabled &&
      element.tabIndex >= 0;
  };
  return Array.from(document.querySelectorAll(selector))
    .filter((element) => element.closest('[data-testid="stApp"]'))
    .filter((element) => !element.closest('[data-testid="stHeader"]'))
    .filter((element) => !element.closest('[data-testid="stToolbar"]'))
    .filter(visible)
    .map((element) => ({
      text: (element.getAttribute("aria-label") || element.textContent || "").trim(),
      href: element.getAttribute("href") || "",
      tag: element.tagName.toLowerCase()
    }));
}
"""
    )


def _skip_link_assertions(page: Any) -> list[dict[str, object]]:
    skip_links = page.locator("a.public-skip-link[href='#public-page-answer']")
    count = skip_links.count()
    order = _visible_application_focus_order(page)
    first_is_skip = bool(order) and order[0].get("href") == "#public-page-answer"
    results = [
        _assertion(
            "skip_link_first_application_focus",
            count == 1 and first_is_skip,
            (
                "one skip link is first in application focus order"
                if count == 1 and first_is_skip
                else f"skip_count={count}; first_focus={order[0] if order else 'none'}"
            ),
        )
    ]
    if count != 1:
        results.append(
            _assertion(
                "skip_link_activation",
                False,
                f"expected one skip link before activation, found {count}",
            )
        )
        return results

    skip_links.first.focus()
    geometry = evaluate_skip_geometry(
        skip_links.first.bounding_box(),
        viewport_width=int(page.evaluate("window.innerWidth")),
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
    link_names = [
        text.strip()
        for text in navigation.first.locator("a.research-workflow-link").all_inner_texts()
    ]
    current = navigation.first.locator("a[aria-current='page']").all_inner_texts()
    expected = ["Research Desk", "Discover"]
    if route.name == "Company Workbench":
        expected.append("Company Workbench")
    expected.append("Monitor")
    passed = link_names == expected and current == [route.name]
    return _assertion(
        "labelled_workflow_navigation",
        passed,
        (
            f"visible route sequence {link_names} with current {current}"
            if passed
            else f"expected={expected}; actual={link_names}; current={current}"
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


def _authoring_error_assertion(page: Any) -> dict[str, object]:
    composer = page.locator("details").filter(
        has=page.get_by_text("Add a reviewed research record", exact=True)
    )
    if composer.count() != 1:
        return _assertion(
            "authoring_field_error_association",
            False,
            f"expected one authoring disclosure, found {composer.count()}",
        )
    composer.locator("summary").click()
    validate = page.get_by_role("button", name="Validate and preview", exact=True)
    if validate.count() != 1:
        return _assertion(
            "authoring_field_error_association",
            False,
            f"expected one validation button, found {validate.count()}",
        )
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
    return _assertion(
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
    try:
        page.goto(
            f"{base_url.rstrip('/')}{route.route}",
            wait_until="domcontentloaded",
            timeout=int(timeout_seconds * 1000),
        )
        _wait_for_visible_text(page, route.marker, timeout_seconds=timeout_seconds)
        _wait_for_dom_stability(page, timeout_seconds=timeout_seconds)

        body = page.locator("body").inner_text()
        traceback = "Traceback (most recent call last)" in body
        assertions.append(
            _assertion(
                "no_traceback",
                not traceback,
                "no traceback rendered" if not traceback else "traceback rendered",
            )
        )
        overflow = _horizontal_overflow_pixels(page)
        assertions.append(
            _assertion(
                "no_horizontal_overflow",
                overflow <= 1,
                f"horizontal overflow={overflow}px",
            )
        )
        assertions.extend(_skip_link_assertions(page))
        assertions.append(_navigation_assertion(page, route))
        assertions.append(_summary_focus_assertion(page))
        if route.name == "Discover":
            assertions.append(_discover_action_assertion(page))
        if route.name == "Company Workbench":
            assertions.append(_authoring_error_assertion(page))
    except Exception as exc:
        assertions.append(
            _assertion(
                "route_execution",
                False,
                f"{type(exc).__name__}: {exc}",
            )
        )
    finally:
        context.close()

    return {
        "route": route.name,
        "viewport": f"{width}x{height}",
        "passed": bool(assertions) and all(
            bool(assertion["passed"]) for assertion in assertions
        ),
        "assertions": assertions,
    }


def _failed_payload(root: Path, failure: str) -> dict[str, object]:
    return {
        "verdict": "failed",
        "commit": _git_commit(root),
        "environment": f"{platform.system()} {platform.machine()}",
        "data_profile": DATA_PROFILE_CONTRACT[1],
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
    chrome = chrome_executable or find_chrome_executable()
    if chrome is None or not Path(chrome).is_file() or not os.access(chrome, os.X_OK):
        return _failed_payload(
            root,
            "Required Chrome-compatible browser runtime is unavailable; gate failed closed.",
        )
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return _failed_payload(
            root,
            "Required Playwright browser runtime is unavailable; gate failed closed.",
        )

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path=str(chrome),
                headless=True,
            )
            try:
                server_context = (
                    contextlib.nullcontext(base_url)
                    if base_url
                    else _local_demo_server(
                        root,
                        timeout_seconds=max(5.0, timeout_seconds),
                    )
                )
                with server_context as active_url:
                    results = [
                        _measure_route(
                            browser,
                            base_url=active_url,
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
            root,
            f"Browser gate could not execute and failed closed: {type(exc).__name__}: {exc}",
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
