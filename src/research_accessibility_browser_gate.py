"""Read-only direct-browser checks for narrow Personal Research accessibility repairs."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import ipaddress
import json
import math
import os
import platform
import subprocess
import sys
import tempfile
import threading
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping
from urllib.parse import parse_qs, urlparse

from scripts.diff_hygiene import (
    StatusEntry,
    classify_path,
    load_staged_status,
    load_status,
)
from src.paths import resolve_project_root
from src.company_workbench_html_browser_gate import (
    _chromium_zoom_preferences,
    _summary_scope_observation,
    evaluate_html_brief_browser_zoom,
)
from src.public_performance_gate import (
    _git_commit,
    _free_port,
    _horizontal_overflow_pixels,
    _wait_for_health,
    _wait_for_dom_stability,
    _wait_for_visible_text,
    find_chrome_executable,
)


VIEWPORTS: tuple[tuple[int, int], ...] = ((1280, 720), (390, 844))
COMPANY_WORKBENCH_ONE_PAGER_CELLS: tuple[tuple[int, int, int], ...] = (
    (1280, 720, 1),
    (1280, 720, 2),
    (390, 844, 1),
)
DATA_PROFILE_CONTRACT = ("STOCK_RESEARCH_DATA_PROFILE", "demo")
EXPECTED_APP_TITLE = "Stock Research Command Center"
EXPECTED_PROFILE_LABEL = "Demo"
EXPECTED_MAIN_ID = "research-main"
EXPECTED_MAIN_LABEL = "Stock research workspace"
EXPECTED_MAIN_STATUS = "applied"
MAX_SERVER_RUNTIME_LINES = 2_000
MAX_SERVER_RUNTIME_LINE_LENGTH = 4_000
STATE_HARNESS_APP = Path("tests/fixtures/research_state_accessibility_app.py")
STATE_HARNESS_TRANSITIONS: tuple[tuple[str, str], ...] = (
    ("validation_rejected", "Validation rejected"),
    ("preview_ready", "Preview ready"),
    ("draft_changed", "Draft changed"),
    ("save_reloaded", "Record saved"),
    ("save_reload_unverified", "Save verification incomplete"),
)

_ONE_PAGER_REQUIRED_STATE_ROLES = frozenset(
    {
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
    }
)
_ONE_PAGER_ALLOWED_STATES = frozenset(
    {"available", "partial", "withheld", "stale", "not_recorded", "excluded"}
)
_ONE_PAGER_EXPECTED_SHARE_BASIS_TOKENS = (
    "operating-valuation-base-bridge-share-basis=unverified",
    "scenarios-base-share-basis=unverified",
    "scenarios-bear-share-basis=unverified",
    "scenarios-bull-share-basis=unverified",
)


@dataclass(frozen=True)
class ResearchRoute:
    name: str
    route: str
    marker: str
    expected_h1: str
    media_marker_selector: str
    media_next_action_selector: str
    requires_primary_navigation: bool = True
    evidence_route: bool = False


@dataclass
class RuntimeServerEvidence:
    """One bounded in-memory server-output capture attached to a loopback URL."""

    base_url: str
    runtime_messages: deque[str]
    capture_status: str
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _total_line_count: int = field(default=0, repr=False)
    _deprecated_warning_count: int = field(default=0, repr=False)
    _capture_detail: str = field(default="", repr=False)

    def append(self, message: str) -> None:
        normalized = str(message)
        with self._lock:
            self._total_line_count += 1
            if "st.components.v1.html" in normalized.lower():
                self._deprecated_warning_count += 1
            self.runtime_messages.append(
                normalized[:MAX_SERVER_RUNTIME_LINE_LENGTH]
            )

    def mark_capture_failure(self, status: str, detail: str) -> None:
        with self._lock:
            if self.capture_status == "captured_local_server":
                self.capture_status = str(status)
                self._capture_detail = str(detail)

    def snapshot(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(self.runtime_messages)

    @property
    def total_line_count(self) -> int:
        with self._lock:
            return self._total_line_count

    @property
    def truncated_line_count(self) -> int:
        with self._lock:
            return max(0, self._total_line_count - len(self.runtime_messages))

    def deprecated_warning_count(self) -> int:
        with self._lock:
            return self._deprecated_warning_count

    def capture_detail(self) -> str:
        with self._lock:
            return self._capture_detail


RESEARCH_ROUTES: tuple[ResearchRoute, ...] = (
    ResearchRoute(
        "Research Desk",
        "/?mode=research&page=research-desk",
        "What needs my attention today?",
        "Research Desk",
        '.research-desk-brief[aria-label="Today\'s Research Brief"]',
        ".research-desk-brief .public-primary-action",
    ),
    ResearchRoute(
        "Discover",
        "/?mode=research&page=discover",
        "Find a Company",
        "Discover",
        ".selector-result-table.research-discover-result",
        "[data-testid='stTextInput'] input[aria-label='Search saved companies']",
    ),
    ResearchRoute(
        "Company Workbench",
        "/?mode=research&page=company-workbench&ticker=NVDA&open=1",
        "Company Brief",
        "Company Workbench",
        ".company-workbench-primary-brief[aria-label='Company Brief']",
        ".company-workbench-primary-brief .public-primary-action",
    ),
    ResearchRoute(
        "Monitor",
        "/?mode=research&page=monitor",
        "Follow-up Queue",
        "Monitor",
        ".signal-grid.evidence-monitor-grid",
        "[data-sr-region='primary-action']",
    ),
    ResearchRoute(
        "Research Data Health",
        "/?mode=research&page=data-health&ticker=NVDA",
        "Use now for market setup",
        "Data Health",
        ".public-lane-list[aria-label='Coverage by analysis lane']",
        "[data-sr-region='primary-action']",
        evidence_route=True,
    ),
    ResearchRoute(
        "Research Proof History",
        "/?mode=research&page=proof-history&ticker=NVDA",
        "Newest reviewed evidence",
        "Proof History",
        ".public-proof-timeline",
        "[data-sr-region='primary-action']",
        evidence_route=True,
    ),
)

ROUND_TRIP_AWAY_ROUTE_NAMES: dict[str, str] = {
    "Research Desk": "Discover",
    "Discover": "Company Workbench",
    "Company Workbench": "Monitor",
    "Monitor": "Research Data Health",
    "Research Data Health": "Research Proof History",
    "Research Proof History": "Research Desk",
}


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
        and observed["profile_label"] in {"", EXPECTED_PROFILE_LABEL}
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
    allowed_dirty_paths: Iterable[str] = (),
) -> dict[str, object]:
    """Allow generated churn plus an explicit unstaged implementation snapshot."""

    status_entries = tuple(entries)
    staged = tuple(staged_entries)
    allowed = {str(path) for path in allowed_dirty_paths}
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
            and entry.path not in allowed
        }
    )
    allowed_dirty_product_paths = sorted(
        {
            entry.path
            for entry in status_entries
            if classify_path(entry.path) != "generated_csv_churn"
            and entry.path in allowed
            and entry.path not in staged_paths
        }
    )
    passed = not staged_paths and not dirty_product_paths
    return {
        "passed": passed,
        "dirty_product_paths": dirty_product_paths,
        "allowed_dirty_product_paths": allowed_dirty_product_paths,
        "staged_paths": staged_paths,
        "excluded_generated_paths": excluded_generated_paths,
        "detail": (
            f"product tree bounded; {len(allowed_dirty_product_paths)} allowed unstaged "
            f"implementation path(s); {len(excluded_generated_paths)} unstaged generated "
            "artifact(s) classified and excluded"
            if passed
            else (
                f"dirty product/manual paths={dirty_product_paths}; "
                f"staged paths={staged_paths}"
            )
        ),
    }


def _repository_hygiene(
    root: Path,
    *,
    allowed_dirty_paths: Iterable[str] = (),
) -> dict[str, object]:
    try:
        return evaluate_repository_hygiene(
            load_status(root),
            staged_entries=load_staged_status(root),
            allowed_dirty_paths=allowed_dirty_paths,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {
            "passed": False,
            "dirty_product_paths": [],
            "allowed_dirty_product_paths": [],
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
    suffix = " Company Brief"
    ticker_names = [
        name[len("Open ") : -len(suffix)]
        for name in actual
        if name.startswith("Open ")
        and name.endswith(suffix)
        and name[len("Open ") : -len(suffix)].strip()
    ]
    if len(ticker_names) != len(actual):
        return {
            "passed": False,
            "actual_count": len(actual),
            "detail": (
                "every eligible Discover action must use "
                "Open {TICKER} Company Brief"
            ),
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


def evaluate_discover_rows(
    rows: Iterable[dict[str, object]],
) -> dict[str, object]:
    """Require each visible Discover result to answer the three research questions."""

    expected_labels = (
        "Why inspectable",
        "Usable evidence",
        "Main evidence gap",
    )
    expected_label_keys = tuple(label.casefold() for label in expected_labels)
    observed = tuple(rows)
    failures: list[str] = []
    seen_tickers: set[str] = set()
    if not observed:
        failures.append("no visible Discover research rows were rendered")
    for index, row in enumerate(observed, start=1):
        ticker = str(row.get("ticker") or "").strip().upper()
        labels = tuple(str(value or "").strip() for value in row.get("labels", ()))
        label_keys = tuple(label.casefold() for label in labels)
        values = tuple(str(value or "").strip() for value in row.get("values", ()))
        action_name = str(row.get("action_name") or "").strip()
        action_ticker = str(row.get("action_ticker") or "").strip().upper()
        try:
            action_height = float(row.get("action_height", 0))
        except (TypeError, ValueError):
            action_height = 0
        visible = row.get("visible") is True
        if (
            not visible
            or label_keys != expected_label_keys
            or len(values) != 3
            or any(not value for value in values)
        ):
            failures.append(
                f"row {index} must expose three visible non-empty answers"
            )
        if (
            not ticker
            or ticker in seen_tickers
            or action_ticker != ticker
            or action_name != f"Open {ticker} Company Brief"
        ):
            failures.append(
                f"row {index} must expose one unique ticker-bound review action"
            )
        if action_height < 44:
            failures.append(
                f"row {index} review action height={action_height:.1f}px is below 44px"
            )
        if ticker:
            seen_tickers.add(ticker)
    return {
        "passed": not failures,
        "actual_count": len(observed),
        "detail": (
            f"{len(observed)} Discover rows expose three answers and usable actions"
            if not failures
            else "; ".join(failures)
        ),
    }


def evaluate_company_workbench_primary_brief(
    observation: dict[str, object],
    *,
    expected_ticker: str = "NVDA",
) -> dict[str, object]:
    """Require the default Workbench to expose one truthful primary brief only."""

    expected_labels = (
        "Use now",
        "Still withheld",
        "What changed",
        "Next research task",
    )
    failures: list[str] = []

    def number(key: str) -> float:
        try:
            return float(observation.get(key, 0))
        except (TypeError, ValueError):
            return 0.0

    expected_ticker_normalized = expected_ticker.strip().upper()
    expected_display_title = f"{expected_ticker_normalized} Company Brief"
    display_title = str(observation.get("display_title") or "").strip()
    answer_labels = tuple(
        str(value or "").strip()
        for value in observation.get("answer_labels", ())
    )
    answer_texts = tuple(
        str(value or "").strip()
        for value in observation.get("answer_texts", ())
    )
    stop_text = str(observation.get("stop_text") or "").strip()
    stop_tokens = (
        "research-only",
        "not a recommendation",
        "probability",
        "transaction instruction",
        "unsupported current-market conclusion",
    )
    action_href = str(
        observation.get("data_health_action_href") or ""
    ).strip()
    action_query = parse_qs(urlparse(action_href).query)
    action_ticker = str(action_query.get("ticker", [""])[0]).strip().upper()
    action_page = str(action_query.get("page", [""])[0]).strip()
    action_mode = str(action_query.get("mode", [""])[0]).strip()

    if number("brief_count") != 1 or observation.get("brief_visible") is not True:
        failures.append("expected exactly one visible Company Brief")
    if display_title != expected_display_title:
        failures.append(
            f"expected display title {expected_display_title!r}, "
            f"found {display_title or 'missing'!r}"
        )
    normalized_answer_labels = tuple(label.casefold() for label in answer_labels)
    normalized_expected_labels = tuple(label.casefold() for label in expected_labels)
    if (
        normalized_answer_labels != normalized_expected_labels
        or len(answer_texts) != 4
        or any(not value for value in answer_texts)
    ):
        failures.append("expected four labelled non-empty primary answers")
    if number("stop_count") != 1 or observation.get("stop_visible") is not True:
        failures.append("expected one visible research-only stop rule")
    if any(token not in stop_text.casefold() for token in stop_tokens):
        failures.append("research-only stop rule is incomplete")
    if (
        number("data_health_action_count") != 1
        or observation.get("data_health_action_visible") is not True
        or number("data_health_action_height") < 44
        or action_mode != "research"
        or action_page != "data-health"
        or action_ticker != expected_ticker_normalized
    ):
        failures.append("expected one visible 44px ticker-bound Data Health action")
    if (
        number("open_modules_count") != 1
        or observation.get("open_modules_visible") is not True
        or number("open_modules_height") < 44
    ):
        failures.append("expected one visible 44px module-open action")
    if number("secondary_module_count") != 0:
        failures.append("secondary Workbench modules rendered before explicit open")

    return {
        "passed": not failures,
        "detail": (
            "one Company Brief exposes four answers, the stop rule, and two usable actions"
            if not failures
            else "; ".join(failures)
        ),
    }


def evaluate_monitor_rows(
    rows: Iterable[dict[str, object]],
    *,
    primary_columns: Iterable[str],
    primary_table_present: bool,
    advanced_present: bool,
    advanced_identity_count: int,
    expected_discipline_count: int,
    neutral_visible: bool,
    queue_visible: bool = False,
) -> dict[str, object]:
    """Require a filtered process-only Monitor view in saved cohort order."""

    observed = tuple(rows)
    columns = tuple(str(column or "").strip() for column in primary_columns)
    failures: list[str] = []
    if not observed and not neutral_visible and not queue_visible:
        failures.append("no Monitor discipline rows or neutral state were rendered")
    if observed and not primary_table_present:
        failures.append("Monitor rows require one primary discipline table")
    if observed and neutral_visible:
        failures.append("Monitor rows and the all-monitor neutral state cannot both be visible")
    orders: list[int] = []
    for index, row in enumerate(observed, start=1):
        try:
            order = int(row.get("cohort_order", 0))
        except (TypeError, ValueError):
            order = 0
            failures.append(f"Monitor row {index} has an invalid cohort order")
        orders.append(order)
        if (
            not str(row.get("ticker") or "").strip()
            or not str(row.get("attention") or "").strip()
            or not str(row.get("reason") or "").strip()
        ):
            failures.append(
                f"Monitor row {index} must expose ticker, process attention, and reason"
            )
        if str(row.get("attention") or "").strip().casefold() == "monitor":
            failures.append(f"Monitor row {index} must not contain a Monitor label")
    if any(current <= previous for previous, current in zip(orders, orders[1:])):
        failures.append(
            f"Monitor rows do not preserve saved cohort order: {orders}"
        )
    lowered_columns = tuple(column.casefold() for column in columns)
    if primary_table_present and lowered_columns != ("ticker", "process attention", "why"):
        failures.append(f"unexpected primary Monitor columns: {columns}")
    if any(
        forbidden in column
        for column in lowered_columns
        for forbidden in ("rank", "score", "return")
    ):
        failures.append("rank/score/return fields are forbidden in Monitor")
    if advanced_present is not True:
        failures.append(
            "exactly one Advanced discipline evidence container must remain available"
        )
    if type(expected_discipline_count) is not int or expected_discipline_count < 0:
        failures.append("expected saved discipline row count is invalid")
    elif expected_discipline_count < len(observed):
        failures.append(
            "expected saved discipline row count cannot be smaller than the primary rows"
        )
    if (
        type(advanced_identity_count) is not int
        or advanced_identity_count != expected_discipline_count
    ):
        failures.append(
            "Advanced identity evidence must remain separate and complete: "
            f"found {advanced_identity_count!r}, expected {expected_discipline_count!r}"
        )
    return {
        "passed": not failures,
        "actual_count": len(observed),
        "detail": (
            f"{len(observed)} Monitor rows preserve process-only cohort order"
            if not failures
            else "; ".join(failures)
        ),
    }


def evaluate_monitor_brief(
    *,
    kickers: Iterable[str],
    boxes: Iterable[tuple[object, object]],
    viewport_width: int,
) -> dict[str, object]:
    """Require the exact Follow-up Queue sequence and responsive card geometry."""

    expected_kickers = (
        "SINCE LAST REVIEW",
        "NEEDS VERIFICATION",
        "WAITING ON EVIDENCE",
        "SCHEDULED CONTEXT",
        "EVIDENCE FRESHNESS",
    )
    observed_kickers = tuple(str(kicker or "").strip() for kicker in kickers)
    observed_boxes = tuple(boxes)
    failures: list[str] = []
    if observed_kickers != expected_kickers:
        failures.append(f"unexpected Monitor brief kickers: {observed_kickers}")
    if len(observed_boxes) != 5:
        failures.append(f"expected five Follow-up Queue card boxes, found {len(observed_boxes)}")

    def clustered(values: Iterable[float]) -> tuple[float, ...]:
        positions: list[float] = []
        for value in sorted(values):
            if not any(abs(value - position) <= 2 for position in positions):
                positions.append(value)
        return tuple(positions)

    try:
        coordinates = tuple(
            (float(box[0]), float(box[1])) for box in observed_boxes
        )
        if any(
            not math.isfinite(value)
            for coordinate in coordinates
            for value in coordinate
        ):
            raise ValueError("non-finite Monitor brief card coordinate")
        x_positions = clustered(x for x, _ in coordinates)
        y_positions = clustered(y for _, y in coordinates)
        normalized_cells = tuple(
            (
                next(
                    index
                    for index, position in enumerate(x_positions)
                    if abs(x - position) <= 2
                ),
                next(
                    index
                    for index, position in enumerate(y_positions)
                    if abs(y - position) <= 2
                ),
            )
            for x, y in coordinates
        )
    except (IndexError, TypeError, ValueError):
        x_positions = ()
        y_positions = ()
        normalized_cells = ()
        failures.append(
            "Monitor brief card coordinates must be finite numeric x/y pairs"
        )

    if viewport_width > 760:
        if (
            len(x_positions) != 2
            or len(y_positions) != 3
            or normalized_cells
            != ((0, 0), (1, 0), (0, 1), (1, 1), (0, 2))
        ):
            failures.append(
                "desktop Follow-up Queue must use five unique row-major cells in a two-column grid"
            )
    elif (
        len(x_positions) != 1
        or len(y_positions) != 5
        or normalized_cells != ((0, 0), (0, 1), (0, 2), (0, 3), (0, 4))
    ):
        failures.append(
            "phone Follow-up Queue must use one column and five increasing rows"
        )

    return {
        "passed": not failures,
        "actual_count": len(observed_kickers),
        "detail": (
            "five Follow-up Queue cards use the expected responsive geometry"
            if not failures
            else "; ".join(failures)
        ),
    }


def evaluate_research_state_snapshot(
    *,
    static_states: Iterable[dict[str, object]],
    transition_state: str,
    transition_nodes: Iterable[dict[str, object]],
) -> dict[str, object]:
    """Validate one synthetic state-harness snapshot without trusting hidden DOM."""

    expected_static = ("loading", "empty", "withheld", "stale", "failure", "validation")
    expected_transition = {
        "validation_rejected": ("alert", "assertive"),
        "preview_ready": ("status", "polite"),
        "draft_changed": ("status", "polite"),
        "save_reloaded": ("status", "polite"),
        "save_reload_unverified": ("alert", "assertive"),
    }
    states = tuple(static_states)
    nodes = tuple(transition_nodes)
    failures: list[str] = []
    if tuple(str(row.get("state") or "") for row in states) != expected_static:
        failures.append("synthetic harness must expose exactly the six static states")
    for row in states:
        state = str(row.get("state") or "")
        if (
            row.get("visible") is not True
            or str(row.get("role") or "") != "group"
            or str(row.get("live") or "")
        ):
            failures.append(f"static {state or 'unknown'} must be visible and non-live")
        busy = str(row.get("busy") or "")
        if (state == "loading" and busy != "true") or (
            state != "loading" and busy
        ):
            failures.append(f"static {state or 'unknown'} has invalid busy semantics")
    semantics = expected_transition.get(str(transition_state or ""))
    if semantics is None:
        failures.append(f"unknown transition state {transition_state!r}")
    if len(nodes) != 1 or nodes[0].get("visible") is not True:
        failures.append("exactly one visible transition node is required")
    elif semantics is not None:
        node = nodes[0]
        if (
            str(node.get("role") or "") != semantics[0]
            or str(node.get("live") or "") != semantics[1]
            or str(node.get("atomic") or "") != "true"
            or "TEST1" not in str(node.get("text") or "")
        ):
            failures.append("transition role, live policy, atomicity, or text is invalid")
    return {
        "passed": not failures,
        "static_states": states,
        "detail": (
            f"{transition_state} exposes one correct visible live transition"
            if not failures
            else "; ".join(failures)
        ),
    }


def evaluate_research_state_rerender(
    transition_nodes: Iterable[dict[str, object]],
) -> dict[str, object]:
    """Require an unchanged rerender to stay visible without announcing again."""

    nodes = tuple(transition_nodes)
    passed = (
        len(nodes) == 1
        and nodes[0].get("visible") is True
        and str(nodes[0].get("role") or "") == "group"
        and not str(nodes[0].get("live") or "")
        and not str(nodes[0].get("atomic") or "")
        and "TEST1" in str(nodes[0].get("text") or "")
    )
    return _assertion(
        "research_state_rerender_non_live",
        passed,
        (
            "unchanged transition remains visible as one non-live message"
            if passed
            else "unchanged transition must render exactly one visible non-live message"
        ),
    )


def evaluate_repository_snapshot_unchanged(
    *,
    before: str,
    after: str,
) -> dict[str, object]:
    """Reject any repository-status mutation caused by the browser harness."""

    passed = str(before) == str(after)
    return _assertion(
        "repository_snapshot_unchanged",
        passed,
        (
            "repository status remained byte-for-byte unchanged"
            if passed
            else "repository status changed while the browser harness executed"
        ),
    )


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


def _safe_int(value: object) -> int | None:
    """Return one exact integer observation or None for unavailable input."""

    if isinstance(value, bool):
        return None
    try:
        converted = int(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if isinstance(value, float) and not value.is_integer():
        return None
    return converted


def _safe_float(value: object) -> float | None:
    """Return one finite numeric observation or None for unavailable input."""

    if isinstance(value, bool):
        return None
    try:
        converted = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return converted if math.isfinite(converted) else None


def _exact_http_origin(url: object) -> str | None:
    try:
        parsed = urlparse(str(url or ""))
        port = parsed.port
    except ValueError:
        return None
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    default_port = 80 if parsed.scheme == "http" else 443
    display_host = (
        f"[{parsed.hostname.lower()}]"
        if ":" in parsed.hostname
        else parsed.hostname.lower()
    )
    suffix = "" if (port or default_port) == default_port else f":{port}"
    return f"{parsed.scheme}://{display_host}{suffix}"


def evaluate_company_workbench_one_pager_observation(
    observation: Mapping[str, object],
) -> list[dict[str, object]]:
    """Fail closed on the scoped in-app one-pager observation contract."""

    def integer(name: str) -> int | None:
        return _safe_int(observation.get(name))

    def number(name: str) -> float | None:
        return _safe_float(observation.get(name))

    state_tokens_value = observation.get("one_pager_state_tokens", ())
    state_tokens = (
        tuple(state_tokens_value)
        if isinstance(state_tokens_value, (tuple, list))
        and all(isinstance(value, str) for value in state_tokens_value)
        else ()
    )
    parsed_state_tokens: list[tuple[str, str]] = []
    for token in state_tokens:
        role, separator, state = token.partition("=")
        if separator and role and state and "=" not in state:
            parsed_state_tokens.append((role, state))
    state_roles = tuple(role for role, _state in parsed_state_tokens)
    state_values = tuple(state for _role, state in parsed_state_tokens)
    provenance_roles = tuple(
        role for role in state_roles if role.startswith("provenance-row-")
    )
    unexpected_roles = set(state_roles).difference(
        _ONE_PAGER_REQUIRED_STATE_ROLES,
        provenance_roles,
    )
    state_count = integer("one_pager_state_node_count")
    state_role_count = integer("one_pager_state_role_count")
    unique_state_role_count = integer("one_pager_unique_state_role_count")
    state_roles_passed = (
        len(parsed_state_tokens) == len(state_tokens)
        and state_count == len(state_tokens)
        and state_role_count == len(state_tokens)
        and unique_state_role_count == len(set(state_roles)) == len(state_tokens)
        and _ONE_PAGER_REQUIRED_STATE_ROLES.issubset(state_roles)
        and bool(provenance_roles)
        and not unexpected_roles
        and all(state in _ONE_PAGER_ALLOWED_STATES for state in state_values)
        and observation.get("one_pager_state_text_matches") is True
    )

    share_tokens_value = observation.get("one_pager_share_basis_tokens", ())
    share_tokens = (
        tuple(share_tokens_value)
        if isinstance(share_tokens_value, (tuple, list))
        and all(isinstance(value, str) for value in share_tokens_value)
        else ()
    )
    request_urls_value = observation.get("request_urls", ())
    request_urls = (
        tuple(request_urls_value)
        if isinstance(request_urls_value, (tuple, list))
        and all(isinstance(value, str) for value in request_urls_value)
        else ()
    )
    active_origin = _exact_http_origin(observation.get("active_origin"))
    request_origins = tuple(_exact_http_origin(url) for url in request_urls)
    network_passed = (
        observation.get("request_audit_complete") is True
        and active_origin is not None
        and integer("external_request_count") == 0
        and all(origin == active_origin for origin in request_origins)
    )

    overflow_values = (
        number("document_overflow_px"),
        number("one_pager_overflow_px"),
        number("one_pager_max_descendant_overflow_px"),
    )
    contrast_values = (
        number("one_pager_min_text_contrast_ratio"),
        number("one_pager_min_boundary_contrast_ratio"),
    )
    console_errors = observation.get("console_errors")
    page_errors = observation.get("page_errors")
    return [
        _assertion(
            "one_pager_module_gate",
            observation.get("one_pager_absent_before_open") is True,
            f"absent_before_open={observation.get('one_pager_absent_before_open')!r}",
        ),
        _assertion(
            "one_pager_disclosure",
            integer("html_brief_details_count") == 1
            and observation.get("html_brief_details_open") is True,
            (
                f"details_count={observation.get('html_brief_details_count')!r}; "
                f"open={observation.get('html_brief_details_open')!r}"
            ),
        ),
        _assertion(
            "one_pager_unique_visible",
            integer("one_pager_count") == 1
            and integer("one_pager_visible_count") == 1
            and observation.get("one_pager_inside_html_brief") is True,
            (
                f"count={observation.get('one_pager_count')!r}; "
                f"visible_count={observation.get('one_pager_visible_count')!r}; "
                f"inside_html_brief="
                f"{observation.get('one_pager_inside_html_brief')!r}"
            ),
        ),
        _assertion(
            "one_pager_order",
            observation.get("one_pager_before_overview") is True
            and integer("overview_count") == 1,
            (
                f"before_overview={observation.get('one_pager_before_overview')!r}; "
                f"overview_count={observation.get('overview_count')!r}"
            ),
        ),
        _assertion(
            "one_pager_full_report",
            integer("advanced_evidence_count") == 1
            and observation.get("advanced_evidence_after_one_pager") is True
            and observation.get("advanced_evidence_visible") is True,
            (
                f"advanced_count={observation.get('advanced_evidence_count')!r}; "
                f"after={observation.get('advanced_evidence_after_one_pager')!r}; "
                f"visible={observation.get('advanced_evidence_visible')!r}"
            ),
        ),
        _assertion(
            "one_pager_zoom",
            integer("requested_zoom") in {1, 2}
            and observation.get("actual_browser_zoom") is True,
            (
                f"requested_zoom={observation.get('requested_zoom')!r}; "
                f"actual={observation.get('actual_browser_zoom')!r}"
            ),
        ),
        _assertion(
            "one_pager_no_overflow",
            all(value is not None and value <= 1 for value in overflow_values),
            (
                f"document/summary/descendant overflow={overflow_values!r}"
            ),
        ),
        _assertion(
            "one_pager_contrast",
            contrast_values[0] is not None
            and contrast_values[0] >= 4.5
            and contrast_values[1] is not None
            and contrast_values[1] >= 3.0,
            f"text-link/boundary contrast={contrast_values!r}",
        ),
        _assertion(
            "one_pager_lists",
            integer("one_pager_answer_item_count") == 4
            and integer("one_pager_scenario_item_count") == 3,
            (
                f"answers={observation.get('one_pager_answer_item_count')!r}; "
                f"scenarios={observation.get('one_pager_scenario_item_count')!r}"
            ),
        ),
        _assertion(
            "one_pager_state_roles",
            state_roles_passed,
            (
                f"nodes/roles/unique={state_count!r}/{state_role_count!r}/"
                f"{unique_state_role_count!r}; roles={state_roles!r}"
            ),
        ),
        _assertion(
            "one_pager_share_basis",
            tuple(sorted(share_tokens))
            == _ONE_PAGER_EXPECTED_SHARE_BASIS_TOKENS
            and integer("one_pager_share_basis_visible_count") == 4
            and observation.get("one_pager_share_basis_text_matches") is True,
            (
                f"tokens={share_tokens!r}; "
                f"visible={observation.get('one_pager_share_basis_visible_count')!r}"
            ),
        ),
        _assertion(
            "one_pager_content_visible",
            all(
                observation.get(name) is True
                for name in (
                    "one_pager_provenance_caption_visible",
                    "one_pager_provenance_visible",
                    "one_pager_blockers_visible",
                    "one_pager_assumptions_visible",
                    "one_pager_handoff_visible",
                )
            ),
            "provenance/caption/blockers/assumptions/handoff remain visible",
        ),
        _assertion(
            "one_pager_download_target",
            integer("download_button_count") == 1
            and observation.get("download_button_label")
            == "Download HTML Research Brief"
            and observation.get("download_button_visible") is True
            and number("download_button_height") is not None
            and number("download_button_height") >= 44,
            (
                f"count={observation.get('download_button_count')!r}; "
                f"label={observation.get('download_button_label')!r}; "
                f"height={observation.get('download_button_height')!r}"
            ),
        ),
        _assertion(
            "one_pager_runtime",
            isinstance(console_errors, (tuple, list))
            and isinstance(page_errors, (tuple, list))
            and not console_errors
            and not page_errors
            and observation.get("server_runtime_output_status")
            == "captured_local_server"
            and integer("server_deprecated_warning_count") == 0,
            (
                f"console_errors={console_errors!r}; page_errors={page_errors!r}; "
                f"server_status={observation.get('server_runtime_output_status')!r}; "
                f"deprecated_warning_count="
                f"{observation.get('server_deprecated_warning_count')!r}"
            ),
        ),
        _assertion(
            "one_pager_exact_origin_network",
            network_passed,
            (
                f"active_origin={active_origin!r}; requests={request_urls!r}; "
                f"external_count={observation.get('external_request_count')!r}; "
                f"audit_complete={observation.get('request_audit_complete')!r}"
            ),
        ),
    ]


def evaluate_company_workbench_one_pager_payload(
    results: Iterable[Mapping[str, object]],
) -> dict[str, object]:
    """Require the exact bounded Workbench matrix and every scoped assertion."""

    expected = {
        (f"{width}x{height}", zoom)
        for width, height, zoom in COMPANY_WORKBENCH_ONE_PAGER_CELLS
    }
    observed: list[tuple[str, int | None]] = []
    failures: list[str] = []
    for index, result in enumerate(tuple(results), start=1):
        viewport = str(result.get("viewport") or "")
        zoom = _safe_int(result.get("zoom"))
        key = (viewport, zoom)
        observed.append(key)
        observation = result.get("observation")
        assertions = result.get("assertions")
        if not isinstance(observation, Mapping):
            failures.append(f"cell {index} observation is missing")
            continue
        evaluated = evaluate_company_workbench_one_pager_observation(observation)
        if (
            observation.get("viewport") != viewport
            or _safe_int(observation.get("requested_zoom")) != zoom
        ):
            failures.append(f"cell {index} identity does not match its observation")
        if result.get("passed") is not True or not all(
            assertion["passed"] for assertion in evaluated
        ):
            failures.append(f"cell {index} did not pass the scoped observation")
        if not isinstance(assertions, (tuple, list)) or not assertions or not all(
            isinstance(assertion, Mapping) and assertion.get("passed") is True
            for assertion in assertions
        ):
            failures.append(f"cell {index} contains a failed or missing assertion")
    actual = set(observed)
    if len(observed) != len(actual):
        failures.append("duplicate Workbench one-pager cell")
    if actual != expected:
        failures.append(
            f"Workbench one-pager cells mismatch: actual={sorted(actual)!r}; "
            f"expected={sorted(expected)!r}"
        )
    return {
        "passed": not failures,
        "detail": (
            "exact three-cell Workbench one-pager matrix passed"
            if not failures
            else "; ".join(failures)
        ),
    }


def evaluate_forced_colors_observation(
    observation: dict[str, object],
    *,
    primary_route: bool,
) -> list[dict[str, object]]:
    """Fail closed when forced-colors observations lose required affordances."""

    skip_count = _safe_int(observation.get("skip_count"))
    skip_outline_width = _safe_float(observation.get("skip_outline_width_px"))
    current_route_count = _safe_int(observation.get("current_route_count"))
    current_route_border_width = _safe_float(
        observation.get("current_route_border_width_px")
    )
    current_route_outline_width = _safe_float(
        observation.get("current_route_outline_width_px")
    )
    current_route_outline_style = str(
        observation.get("current_route_outline_style") or ""
    ).strip().lower()
    boundary_count = _safe_int(observation.get("boundary_count"))
    boundary_border_width = _safe_float(
        observation.get("boundary_border_width_px")
    )
    route_marker_count = _safe_int(observation.get("route_marker_count"))
    route_next_action_count = _safe_int(
        observation.get("route_next_action_count")
    )
    overflow = _safe_float(observation.get("overflow_px"))
    current_route_passed = (
        current_route_count == 1
        and str(observation.get("current_route_value") or "") == "page"
        and observation.get("current_route_visible") is True
    ) if primary_route else current_route_count == 0
    marker_passed = (
        current_route_border_width is not None
        and current_route_border_width >= 2
        and current_route_outline_style not in {"", "none"}
        and current_route_outline_width is not None
        and current_route_outline_width > 0
        if primary_route
        else True
    )
    return [
        _assertion("forced_colors_media_active", observation.get("media_active") is True, "forced-colors media query active"),
        _assertion("forced_colors_skip_focus", skip_count == 1 and observation.get("skip_focused") is True, f"skip_count={observation.get('skip_count')!r}; skip_focused={observation.get('skip_focused')!r}"),
        _assertion("forced_colors_focus_outline", str(observation.get("skip_outline_style") or "").strip().lower() not in {"", "none"} and skip_outline_width is not None and skip_outline_width > 0, f"skip_outline_style={observation.get('skip_outline_style')!r}; skip_outline_width_px={observation.get('skip_outline_width_px')!r}"),
        _assertion("forced_colors_current_route", current_route_passed, f"current_route_count={observation.get('current_route_count')!r}; current_route_value={observation.get('current_route_value')!r}; current_route_visible={observation.get('current_route_visible')!r}"),
        _assertion("forced_colors_current_route_marker", marker_passed, f"current_route_border_width_px={observation.get('current_route_border_width_px')!r}; current_route_outline_style={observation.get('current_route_outline_style')!r}; current_route_outline_width_px={observation.get('current_route_outline_width_px')!r}"),
        _assertion("forced_colors_boundary", boundary_count == 1 and observation.get("boundary_visible") is True, f"boundary_count={observation.get('boundary_count')!r}; boundary_visible={observation.get('boundary_visible')!r}"),
        _assertion("forced_colors_boundary_border", boundary_border_width is not None and boundary_border_width > 0, f"boundary_border_width_px={observation.get('boundary_border_width_px')!r}"),
        _assertion("forced_colors_required_text", observation.get("heading_visible") is True and observation.get("boundary_text_visible") is True, "heading and research-only text remain visible"),
        _assertion("forced_colors_route_marker", route_marker_count == 1 and observation.get("route_marker_visible") is True, f"route_marker_count={observation.get('route_marker_count')!r}; route_marker_visible={observation.get('route_marker_visible')!r}"),
        _assertion("forced_colors_route_next_action", route_next_action_count == 1 and observation.get("route_next_action_visible") is True, f"route_next_action_count={observation.get('route_next_action_count')!r}; route_next_action_visible={observation.get('route_next_action_visible')!r}"),
        _assertion("forced_colors_no_overflow", overflow is not None and overflow <= 1, f"horizontal overflow={observation.get('overflow_px')!r}px"),
        _assertion("forced_colors_no_traceback", observation.get("traceback_visible") is False, "no traceback rendered"),
    ]


def evaluate_reduced_motion_observation(
    observation: dict[str, object],
) -> list[dict[str, object]]:
    """Fail closed when reduced-motion observations exceed safe thresholds."""

    target_count = _safe_int(observation.get("target_count"))
    animation_duration = _safe_float(
        observation.get("max_animation_duration_ms")
    )
    transition_duration = _safe_float(
        observation.get("max_transition_duration_ms")
    )
    animation_iterations = _safe_float(
        observation.get("max_animation_iterations")
    )
    route_marker_count = _safe_int(observation.get("route_marker_count"))
    route_next_action_count = _safe_int(
        observation.get("route_next_action_count")
    )
    overflow = _safe_float(observation.get("overflow_px"))
    scroll_behavior = str(observation.get("scroll_behavior") or "").strip().lower()
    return [
        _assertion("reduced_motion_media_active", observation.get("media_active") is True, "reduced-motion media query active"),
        _assertion("reduced_motion_targets", target_count is not None and target_count > 0, f"target_count={observation.get('target_count')!r}"),
        _assertion("reduced_motion_animation_duration", animation_duration is not None and animation_duration <= 0.1, f"max animation duration={observation.get('max_animation_duration_ms')!r}ms"),
        _assertion("reduced_motion_transition_duration", transition_duration is not None and transition_duration <= 0.1, f"max transition duration={observation.get('max_transition_duration_ms')!r}ms"),
        _assertion("reduced_motion_animation_iterations", animation_iterations is not None and animation_iterations <= 1, f"max animation iterations={observation.get('max_animation_iterations')!r}"),
        _assertion("reduced_motion_scroll_behavior", bool(scroll_behavior) and scroll_behavior != "smooth", f"scroll behavior={observation.get('scroll_behavior')!r}"),
        _assertion("reduced_motion_required_text", observation.get("heading_visible") is True and observation.get("boundary_visible") is True, "heading and research boundary remain visible"),
        _assertion("reduced_motion_route_marker", route_marker_count == 1 and observation.get("route_marker_visible") is True, f"route_marker_count={observation.get('route_marker_count')!r}; route_marker_visible={observation.get('route_marker_visible')!r}"),
        _assertion("reduced_motion_route_next_action", route_next_action_count == 1 and observation.get("route_next_action_visible") is True, f"route_next_action_count={observation.get('route_next_action_count')!r}; route_next_action_visible={observation.get('route_next_action_visible')!r}"),
        _assertion("reduced_motion_no_overflow", overflow is not None and overflow <= 1, f"horizontal overflow={observation.get('overflow_px')!r}px"),
        _assertion("reduced_motion_no_traceback", observation.get("traceback_visible") is False, "no traceback rendered"),
    ]


def _forced_colors_observation(
    page: Any,
    route: ResearchRoute,
) -> dict[str, object]:
    skip = page.locator("a.public-skip-link[href='#public-page-answer']")
    if skip.count() == 1:
        skip.first.focus()
        page.keyboard.press("Tab")
        page.keyboard.press("Shift+Tab")
    return page.evaluate(
        """
({primaryRoute, markerSelector, nextActionSelector}) => {
  const visible = (node) => {
    if (!node) return false;
    const box = node.getBoundingClientRect();
    const style = getComputedStyle(node);
    return box.width > 0 && box.height > 0 &&
      style.display !== "none" && style.visibility !== "hidden";
  };
  const width = (style, names) => Math.max(
    ...names.map((name) => Number.parseFloat(style[name]) || 0)
  );
  const skips = [...document.querySelectorAll(
    "a.public-skip-link[href='#public-page-answer']"
  )];
  const currents = [...document.querySelectorAll(
    ".research-workflow-link[aria-current='page']"
  )];
  const boundaries = [...document.querySelectorAll(
    ".research-workspace-boundary"
  )];
  const routeMarkers = [...document.querySelectorAll(markerSelector)];
  const routeNextActions = [...document.querySelectorAll(nextActionSelector)];
  const skipStyle = skips.length === 1 ? getComputedStyle(skips[0]) : null;
  const currentStyle = currents.length === 1 ? getComputedStyle(currents[0]) : null;
  const boundaryStyle = boundaries.length === 1 ? getComputedStyle(boundaries[0]) : null;
  const heading = document.querySelector("[role='main'] h1");
  return {
    media_active: matchMedia("(forced-colors: active)").matches,
    skip_count: skips.length,
    skip_focused: skips.length === 1 && document.activeElement === skips[0],
    skip_outline_style: skipStyle ? skipStyle.outlineStyle : "",
    skip_outline_width_px: skipStyle ? Number.parseFloat(skipStyle.outlineWidth) || 0 : 0,
    current_route_count: currents.length,
    current_route_value: currents.length === 1 ? currents[0].getAttribute("aria-current") || "" : "",
    current_route_visible: currents.length === 1 && visible(currents[0]),
    current_route_border_width_px: currentStyle ? width(currentStyle, ["borderTopWidth", "borderRightWidth", "borderBottomWidth", "borderLeftWidth"]) : 0,
    current_route_outline_style: currentStyle ? currentStyle.outlineStyle : "",
    current_route_outline_width_px: currentStyle ? Number.parseFloat(currentStyle.outlineWidth) || 0 : 0,
    boundary_count: boundaries.length,
    boundary_visible: boundaries.length === 1 && visible(boundaries[0]),
    boundary_border_width_px: boundaryStyle ? width(boundaryStyle, ["borderTopWidth", "borderRightWidth", "borderBottomWidth", "borderLeftWidth"]) : 0,
    heading_visible: visible(heading),
    boundary_text_visible: boundaries.length === 1 && visible(boundaries[0]) && boundaries[0].innerText.includes("Research-only"),
    route_marker_count: routeMarkers.length,
    route_marker_visible: routeMarkers.length === 1 && visible(routeMarkers[0]),
    route_next_action_count: routeNextActions.length,
    route_next_action_visible: routeNextActions.length === 1 && visible(routeNextActions[0]),
    overflow_px: Math.max(0, document.documentElement.scrollWidth - window.innerWidth),
    traceback_visible: document.body.innerText.includes("Traceback (most recent call last)"),
    primary_route: primaryRoute,
  };
}
""",
        {
            "primaryRoute": route.requires_primary_navigation,
            "markerSelector": route.media_marker_selector,
            "nextActionSelector": route.media_next_action_selector,
        },
    )


def _reduced_motion_observation(
    page: Any,
    route: ResearchRoute,
) -> dict[str, object]:
    return page.evaluate(
        """
({markerSelector, nextActionSelector}) => {
  const app = document.querySelector(".stApp");
  const visible = (node) => {
    if (!node) return false;
    const box = node.getBoundingClientRect();
    const style = getComputedStyle(node);
    return box.width > 0 && box.height > 0 &&
      style.display !== "none" && style.visibility !== "hidden";
  };
  const toMilliseconds = (value) => value.split(",").map((part) => {
    const token = part.trim();
    const amount = Number.parseFloat(token);
    if (!Number.isFinite(amount)) return Number.MAX_SAFE_INTEGER;
    if (token.endsWith("ms")) return amount;
    if (token.endsWith("s")) return amount * 1000;
    return Number.MAX_SAFE_INTEGER;
  });
  const toIterations = (value) => value.split(",").map((part) => {
    const token = part.trim();
    if (token === "infinite") return Number.MAX_SAFE_INTEGER;
    const amount = Number.parseFloat(token);
    return Number.isFinite(amount) ? amount : Number.MAX_SAFE_INTEGER;
  });
  const targets = [...new Set([
    app,
    ...document.querySelectorAll(".research-workflow-link"),
    ...document.querySelectorAll(".research-workspace-boundary"),
    ...document.querySelectorAll(".research-state-message"),
  ].filter(Boolean))];
  const styles = targets.map((node) => getComputedStyle(node));
  const animationDurations = styles.flatMap((style) => toMilliseconds(style.animationDuration));
  const transitionDurations = styles.flatMap((style) => toMilliseconds(style.transitionDuration));
  const iterations = styles.flatMap((style) => toIterations(style.animationIterationCount));
  const boundary = document.querySelector(".research-workspace-boundary");
  const heading = document.querySelector("[role='main'] h1");
  const routeMarkers = [...document.querySelectorAll(markerSelector)];
  const routeNextActions = [...document.querySelectorAll(nextActionSelector)];
  return {
    media_active: matchMedia("(prefers-reduced-motion: reduce)").matches,
    target_count: targets.length,
    max_animation_duration_ms: animationDurations.length ? Math.max(...animationDurations) : Number.MAX_SAFE_INTEGER,
    max_transition_duration_ms: transitionDurations.length ? Math.max(...transitionDurations) : Number.MAX_SAFE_INTEGER,
    max_animation_iterations: iterations.length ? Math.max(...iterations) : Number.MAX_SAFE_INTEGER,
    scroll_behavior: app ? getComputedStyle(app).scrollBehavior : "",
    heading_visible: visible(heading),
    boundary_visible: visible(boundary),
    route_marker_count: routeMarkers.length,
    route_marker_visible: routeMarkers.length === 1 && visible(routeMarkers[0]),
    route_next_action_count: routeNextActions.length,
    route_next_action_visible: routeNextActions.length === 1 && visible(routeNextActions[0]),
    overflow_px: Math.max(0, document.documentElement.scrollWidth - window.innerWidth),
    traceback_visible: document.body.innerText.includes("Traceback (most recent call last)"),
  };
}
""",
        {
            "markerSelector": route.media_marker_selector,
            "nextActionSelector": route.media_next_action_selector,
        },
    )


def _media_preference_assertions(
    page: Any,
    route: ResearchRoute,
) -> list[dict[str, object]]:
    assertions: list[dict[str, object]] = []

    def restore() -> None:
        try:
            page.emulate_media(
                forced_colors="none",
                reduced_motion="no-preference",
            )
        except Exception as exc:
            assertions.append(
                _assertion(
                    "media_preferences_restore",
                    False,
                    f"{type(exc).__name__}: {exc}",
                )
            )

    try:
        page.emulate_media(
            forced_colors="active",
            reduced_motion="no-preference",
        )
        assertions.extend(
            evaluate_forced_colors_observation(
                _forced_colors_observation(page, route),
                primary_route=not route.evidence_route,
            )
        )
    except Exception as exc:
        assertions.append(
            _assertion(
                "forced_colors_execution",
                False,
                f"{type(exc).__name__}: {exc}",
            )
        )
    finally:
        restore()

    try:
        page.emulate_media(forced_colors="none", reduced_motion="reduce")
        assertions.extend(
            evaluate_reduced_motion_observation(
                _reduced_motion_observation(page, route)
            )
        )
    except Exception as exc:
        assertions.append(
            _assertion(
                "reduced_motion_execution",
                False,
                f"{type(exc).__name__}: {exc}",
            )
        )
    finally:
        restore()
    return assertions


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


def evaluate_bridge_transport(
    *,
    runtime_messages: Iterable[str],
    bridge_iframe_count: int,
    bridge_focusable_count: int,
    bridge_heights: Iterable[float],
    server_deprecated_warning_count: int = 0,
) -> dict[str, object]:
    """Require the fixed accessibility bridges to have no legacy transport or box."""

    observed_messages = tuple(
        str(message).strip()
        for message in runtime_messages
        if str(message).strip()
    )
    browser_warning_count = sum(
        "st.components.v1.html" in message.lower()
        for message in observed_messages
    )
    valid_server_warning_count = (
        type(server_deprecated_warning_count) is int
        and server_deprecated_warning_count >= 0
    )
    deprecated_warning_count = (
        browser_warning_count + server_deprecated_warning_count
        if valid_server_warning_count
        else -1
    )
    iframe_count = (
        bridge_iframe_count
        if type(bridge_iframe_count) is int and bridge_iframe_count >= 0
        else -1
    )
    focusable_count = (
        bridge_focusable_count
        if type(bridge_focusable_count) is int and bridge_focusable_count >= 0
        else -1
    )
    try:
        heights = tuple(float(height) for height in bridge_heights)
    except (TypeError, ValueError):
        heights = ()
    valid_heights = bool(heights) and all(
        math.isfinite(height) and height >= 0 for height in heights
    )
    bridge_height: float | int = max(heights) if valid_heights else -1
    if bridge_height == 0:
        bridge_height = 0

    fields: dict[str, object] = {
        "deprecated_component_warning_count": deprecated_warning_count,
        "bridge_iframe_count": iframe_count,
        "bridge_focusable_count": focusable_count,
        "bridge_height": bridge_height,
    }
    assertions = [
        _assertion(
            "deprecated_component_warning_count",
            deprecated_warning_count == 0,
            f"deprecated st.components.v1.html warning count={deprecated_warning_count}",
        ),
        _assertion(
            "bridge_iframe_count",
            iframe_count == 0,
            f"accessibility bridge iframe count={iframe_count}",
        ),
        _assertion(
            "bridge_focusable_count",
            focusable_count == 0,
            f"accessibility bridge focusable descendant count={focusable_count}",
        ),
        _assertion(
            "bridge_height",
            bridge_height == 0,
            f"maximum accessibility bridge height={bridge_height}px",
        ),
    ]
    return {
        **fields,
        "passed": all(assertion["passed"] for assertion in assertions),
        "assertions": assertions,
    }


def evaluate_server_runtime_output(
    *,
    capture_status: str,
    runtime_messages: Iterable[str],
    deprecated_component_warning_count: int | None = None,
) -> dict[str, object]:
    """Require owned local server output and reject deprecated transport warnings."""

    status = str(capture_status or "").strip()
    if status != "captured_local_server":
        return {
            "passed": False,
            "capture_status": status or "unavailable",
            "deprecated_component_warning_count": None,
            "detail": (
                "server stdout/stderr capture unavailable; strict deprecation "
                "evidence failed closed"
            ),
        }
    observed = tuple(
        str(message).strip()
        for message in runtime_messages
        if str(message).strip()
    )
    if deprecated_component_warning_count is None:
        warning_count = sum(
            "st.components.v1.html" in message.lower()
            for message in observed
        )
    elif (
        type(deprecated_component_warning_count) is int
        and deprecated_component_warning_count >= 0
    ):
        warning_count = deprecated_component_warning_count
    else:
        warning_count = -1
    return {
        "passed": warning_count == 0,
        "capture_status": status,
        "deprecated_component_warning_count": warning_count,
        "detail": (
            "captured local server stdout/stderr contains no deprecated "
            "st.components.v1.html warning"
            if warning_count == 0
            else (
                "captured local server stdout/stderr deprecated "
                f"st.components.v1.html warning count={warning_count}"
            )
        ),
    }


@contextlib.contextmanager
def _captured_local_streamlit_server(
    root: Path,
    *,
    app_path: Path,
    timeout_seconds: float,
    demo_profile: bool,
    reader_name: str,
):
    """Run one local Streamlit app with bounded in-memory runtime output."""

    selected_port = _free_port()
    base_url = f"http://127.0.0.1:{selected_port}"
    env = os.environ.copy()
    if demo_profile:
        env["STOCK_RESEARCH_DATA_PROFILE"] = "demo"
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(app_path),
            "--server.headless",
            "true",
            "--server.fileWatcherType",
            "none",
            "--client.toolbarMode",
            "viewer",
            "--browser.gatherUsageStats",
            "false",
            "--server.port",
            str(selected_port),
        ],
        cwd=root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        start_new_session=True,
    )
    evidence = RuntimeServerEvidence(
        base_url=base_url,
        runtime_messages=deque(maxlen=MAX_SERVER_RUNTIME_LINES),
        capture_status="captured_local_server",
    )

    def collect_runtime_output() -> None:
        if process.stdout is None:
            evidence.mark_capture_failure(
                "failed_reader_unavailable",
                "server stdout pipe was unavailable",
            )
            return
        try:
            for line in process.stdout:
                normalized = str(line).strip()
                if normalized:
                    evidence.append(normalized)
        except Exception as exc:
            evidence.mark_capture_failure(
                "failed_reader_exception",
                (
                    "server stdout/stderr reader failed: "
                    f"{type(exc).__name__}: {exc}"
                )
            )

    reader = threading.Thread(
        target=collect_runtime_output,
        name=reader_name,
        daemon=True,
    )
    reader.start()
    try:
        _wait_for_health(base_url, timeout_seconds=timeout_seconds)
        yield evidence
    finally:
        process.terminate()
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:  # pragma: no cover - defensive cleanup
            process.kill()
            process.wait(timeout=5)
        reader.join(timeout=5)
        reader_stopped = not reader.is_alive()
        if not reader_stopped:
            evidence.mark_capture_failure(
                "incomplete_reader_shutdown",
                "server stdout/stderr reader did not stop within 5 seconds",
            )
        else:
            close_stdout = getattr(process.stdout, "close", None)
            if callable(close_stdout):
                close_stdout()


@contextlib.contextmanager
def _captured_local_demo_server(
    root: Path,
    *,
    timeout_seconds: float,
):
    """Run the demo dashboard under the bounded local-server contract."""

    with _captured_local_streamlit_server(
        root,
        app_path=Path("src/dashboard.py"),
        timeout_seconds=timeout_seconds,
        demo_profile=True,
        reader_name="research-accessibility-server-output",
    ) as evidence:
        yield evidence


@contextlib.contextmanager
def _captured_local_state_harness_server(
    root: Path,
    *,
    timeout_seconds: float,
):
    """Run the synthetic state harness without production data or ledgers."""

    with _captured_local_streamlit_server(
        root,
        app_path=STATE_HARNESS_APP,
        timeout_seconds=timeout_seconds,
        demo_profile=False,
        reader_name="research-state-accessibility-server-output",
    ) as evidence:
        yield evidence


def evaluate_exact_route_url(
    *,
    actual_url: str,
    expected_url: str,
    phase: str,
) -> dict[str, object]:
    """Require an exact route URL, including query order and empty fragment."""

    phase_name = str(phase or "snapshot").strip().lower().replace(" ", "_")
    passed = bool(expected_url) and actual_url == expected_url
    return _assertion(
        f"exact_route_url_{phase_name}",
        passed,
        (
            f"exact route URL retained: {expected_url}"
            if passed
            else f"expected route URL={expected_url!r}; actual={actual_url!r}"
        ),
    )


def evaluate_same_document_streamlit_rerun(
    *,
    trigger_count: int,
    trigger_activated: bool,
    initial_observer_available: bool,
    token_before: str,
    token_after: str,
    same_document: bool,
    top_level_navigation_count: int,
    initial_script_state: str,
    script_states: Iterable[str],
    final_script_state: str,
    observer_liveness_proved: bool,
    active_target: bool,
    bridge_status: str | None,
    route_before: str,
    route_after: str,
) -> list[dict[str, object]]:
    """Require one real Streamlit rerun without replacing the top document."""

    observed_script_states = tuple(
        str(state or "").strip() for state in script_states
    )
    try:
        running_index = observed_script_states.index("running")
    except ValueError:
        running_index = -1
    completed_index = (
        observed_script_states.index("notRunning", running_index + 1)
        if running_index >= 0
        and "notRunning" in observed_script_states[running_index + 1 :]
        else -1
    )
    cycle_completed = (
        running_index >= 1
        and completed_index > running_index
        and final_script_state == "notRunning"
    )
    return [
        _assertion(
            "streamlit_rerun_trigger_available",
            trigger_count == 1,
            f"Public visitor mode workspace radio count={trigger_count}",
        ),
        _assertion(
            "streamlit_rerun_trigger_activated",
            trigger_activated,
            f"controlled native radio activation completed={trigger_activated}",
        ),
        _assertion(
            "streamlit_rerun_initial_observer_available",
            initial_observer_available,
            f"initial semantic-main observer available={initial_observer_available}",
        ),
        _assertion(
            "streamlit_rerun_initial_script_idle",
            initial_script_state == "notRunning",
            f"initial Streamlit script state={initial_script_state!r}",
        ),
        _assertion(
            "streamlit_rerun_cycle_completed",
            cycle_completed,
            (
                f"Streamlit script states={list(observed_script_states)}; "
                f"final={final_script_state!r}"
            ),
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
            "streamlit_rerun_observer_live",
            observer_liveness_proved,
            (
                "semantic-main observer restored applied status after the "
                f"inert mutation probe={observer_liveness_proved}"
            ),
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
            trigger_activated=False,
            initial_observer_available=False,
            token_before="",
            token_after="",
            same_document=False,
            top_level_navigation_count=len(top_level_navigations),
            initial_script_state="",
            script_states=(),
            final_script_state="",
            observer_liveness_proved=False,
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
  const scriptStateAttribute = "data-test-script-state";
  const app = document.querySelector('[data-testid="stApp"]');
  const initialScriptState = app
    ? app.getAttribute(scriptStateAttribute)
    : "";
  const scriptStates = initialScriptState ? [initialScriptState] : [];
  const appendScriptState = (state) => {
    if (state && scriptStates[scriptStates.length - 1] !== state) {
      scriptStates.push(state);
    }
  };
  const scriptStateObserver = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      const target = mutation.target;
      if (
        mutation.type === "attributes" &&
        target instanceof Element &&
        target.matches('[data-testid="stApp"]')
      ) {
        appendScriptState(mutation.oldValue);
        appendScriptState(target.getAttribute(scriptStateAttribute));
      }
    }
  });
  scriptStateObserver.observe(document.documentElement, {
    attributes: true,
    attributeFilter: [scriptStateAttribute],
    attributeOldValue: true,
    subtree: true
  });
  window[probeKey] = {
    token,
    document: document,
    observer: window.__stockResearchMainObserver,
    target: window.__stockResearchMainTarget,
    route,
    scriptStates,
    scriptStateObserver
  };
  return {
    token,
    initial_observer_available: Boolean(window[probeKey].observer),
    initial_script_state: initialScriptState,
    route
  };
}
"""
    )
    top_level_navigations.clear()
    trigger_activated = bool(
        trigger.evaluate(
            """
element => {
  if (
    !(element instanceof HTMLInputElement) ||
    element.type !== "radio" ||
    element.disabled ||
    element.checked
  ) {
    return false;
  }
  element.click();
  return element.checked && element.isConnected;
}
"""
        )
    )
    if trigger_activated:
        page.wait_for_function(
            """
() => {
  const probe = window.__a11ySameDocumentRerunProbe;
  const app = document.querySelector('[data-testid="stApp"]');
  if (!probe || !app) return false;
  const states = probe.scriptStates;
  const runningIndex = states.indexOf("running");
  const completedIndex = states.indexOf("notRunning", runningIndex + 1);
  return (
    runningIndex >= 1 &&
    completedIndex > runningIndex &&
    app.getAttribute("data-test-script-state") === "notRunning"
  );
}
""",
            timeout=int(timeout_seconds * 1000),
        )
    observer_probe_started = bool(
        page.evaluate(
            """
() => {
  const probe = window.__a11ySameDocumentRerunProbe;
  const target = document.querySelector('[data-testid="stMain"]');
  if (
    !probe ||
    !target ||
    !target.isConnected ||
    window.__stockResearchMainTarget !== target ||
    !window.__stockResearchMainObserver
  ) {
    return false;
  }
  const observerProbeNode = document.createElement("span");
  observerProbeNode.hidden = true;
  observerProbeNode.setAttribute("aria-hidden", "true");
  observerProbeNode.setAttribute(
    "data-a11y-main-observer-probe",
    probe.token
  );
  probe.observerProbeNode = observerProbeNode;
  document.documentElement.setAttribute(
    "data-research-main-bridge-status",
    "observer-probe-pending"
  );
  target.appendChild(observerProbeNode);
  return observerProbeNode.isConnected;
}
"""
        )
    )
    if observer_probe_started:
        page.wait_for_function(
            """
() => {
  const probe = window.__a11ySameDocumentRerunProbe;
  const target = document.querySelector('[data-testid="stMain"]');
  return Boolean(
    probe &&
    probe.observerProbeNode &&
    probe.observerProbeNode.isConnected &&
    window.__stockResearchMainObserver &&
    target &&
    target.isConnected &&
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
  const app = document.querySelector('[data-testid="stApp"]');
  const finalScriptState = app
    ? app.getAttribute("data-test-script-state")
    : "";
  if (
    probe &&
    finalScriptState &&
    probe.scriptStates[probe.scriptStates.length - 1] !== finalScriptState
  ) {
    probe.scriptStates.push(finalScriptState);
  }
  const scriptStates = probe ? [...probe.scriptStates] : [];
  if (probe && probe.scriptStateObserver) {
    probe.scriptStateObserver.disconnect();
  }
  const observerLivenessProved = Boolean(
    probe &&
    probe.observerProbeNode &&
    probe.observerProbeNode.isConnected &&
    window.__stockResearchMainObserver &&
    target &&
    target.isConnected &&
    window.__stockResearchMainTarget === target &&
    document.documentElement.getAttribute(
      "data-research-main-bridge-status"
    ) === "applied"
  );
  if (
    probe &&
    probe.observerProbeNode &&
    probe.observerProbeNode.isConnected
  ) {
    probe.observerProbeNode.remove();
  }
  return {
    token: probe ? probe.token : "",
    same_document: Boolean(probe && probe.document === document),
    script_states: scriptStates,
    final_script_state: finalScriptState,
    observer_liveness_proved: observerLivenessProved,
    active_target: Boolean(
      probe &&
      target &&
      target.isConnected &&
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
        trigger_activated=trigger_activated,
        initial_observer_available=bool(
            before.get("initial_observer_available")
        ),
        token_before=str(before.get("token") or ""),
        token_after=str(after.get("token") or ""),
        same_document=bool(after.get("same_document")),
        top_level_navigation_count=len(top_level_navigations),
        initial_script_state=str(before.get("initial_script_state") or ""),
        script_states=tuple(after.get("script_states") or ()),
        final_script_state=str(after.get("final_script_state") or ""),
        observer_liveness_proved=bool(
            after.get("observer_liveness_proved")
        ),
        active_target=bool(after.get("active_target")),
        bridge_status=str(after.get("bridge_status") or ""),
        route_before=str(before.get("route") or ""),
        route_after=str(after.get("route") or ""),
    )


def evaluate_evidence_navigation(
    *,
    navigation_count: int,
    current_count: int,
    phase: str,
) -> dict[str, object]:
    """Require evidence routes to retain one workflow nav without a false current core item."""

    phase_name = str(phase or "snapshot").strip().lower().replace(" ", "_")
    return _assertion(
        f"evidence_workflow_navigation_{phase_name}",
        navigation_count == 1 and current_count == 0,
        (
            f"labelled workflow navigation count={navigation_count}; "
            f"current core item count={current_count}"
        ),
    )


def _evidence_navigation_assertion(
    page: Any,
    *,
    phase: str,
) -> dict[str, object]:
    navigation = page.locator("nav[aria-label='Personal research workflow']")
    return evaluate_evidence_navigation(
        navigation_count=navigation.count(),
        current_count=navigation.locator("[aria-current='page']").count(),
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
}
"""
    )
    page.locator("body").focus()
    page.keyboard.press("Tab")
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
    if "ticker=" in route.route:
        expected.append("Company Workbench")
    expected.append("Monitor")
    expected_current = [] if route.evidence_route else [route.name]
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
    link_geometry = []
    for index, label in enumerate(link_names):
        rectangle = links.nth(index).bounding_box()
        if viewport[0] <= 390 and rectangle:
            y = float(rectangle.get("y", 0))
            height = float(rectangle.get("height", 0))
            bottom = y + height
            passed = height >= 44 and bottom > 0 and y < viewport[1]
            link_geometry.append(
                {
                    "passed": passed,
                    "detail": (
                        f"{label} horizontal-strip geometry height={height:.1f}px "
                        f"{'meets' if passed else 'fails'} 44.0px height and vertical viewport contract"
                    ),
                }
            )
        else:
            link_geometry.append(
                evaluate_viewport_geometry(
                    rectangle,
                    viewport=viewport,
                    expected_min_height=44,
                    label=label,
                )
            )
    geometry_passed = bool(navigation_geometry["passed"]) and all(
        bool(result["passed"]) for result in link_geometry
    )
    passed = (
        link_names == expected
        and current == expected_current
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
                f"expected={expected}; actual={link_names}; expected_current={expected_current}; current={current}; "
                f"{geometry_detail}"
            )
        ),
    )


def _personal_navigation_authority_assertions(page: Any) -> list[dict[str, object]]:
    """Confirm Personal routes do not revive removed native sidebar controls."""

    sidebar = page.locator('[data-testid="stSidebar"]')
    route_control_count = sidebar.locator(
        '[role="radiogroup"], [data-testid="stSelectbox"]'
    ).count()
    navigation_count = page.locator(
        "nav[aria-label='Personal research workflow']"
    ).count()
    return [
        _assertion(
            "personal_native_sidebar_route_controls_absent",
            route_control_count == 0,
            f"native sidebar route control count={route_control_count}",
        ),
        _assertion(
            "personal_navigation_authority_unique",
            navigation_count == 1,
            f"Personal workflow navigation count={navigation_count}",
        ),
    ]


def _discover_action_assertion(page: Any) -> dict[str, object]:
    links = page.locator("a.selector-action-link")
    names = [name.strip() for name in links.all_inner_texts()]
    evaluated = evaluate_discover_action_names(names)
    href_matches = True
    for index, name in enumerate(names):
        href = links.nth(index).get_attribute("href") or ""
        ticker = parse_qs(urlparse(href).query).get("ticker", [""])[0].strip().upper()
        if not ticker or name != f"Open {ticker} Company Brief":
            href_matches = False
            break
    passed = bool(evaluated["passed"]) and href_matches
    detail = str(evaluated["detail"])
    if evaluated["passed"] and not href_matches:
        detail = "an eligible Discover action name does not match its ticker route"
    return _assertion("discover_action_names", passed, detail)


def _discover_rows_assertion(page: Any) -> dict[str, object]:
    rows = page.locator(
        ".research-discover-result .selector-result-row"
    )
    observed: list[dict[str, object]] = []
    for index in range(rows.count()):
        row = rows.nth(index)
        ticker = row.locator(".selector-result-ticker").inner_text().strip()
        labels = tuple(
            text.strip()
            for text in row.locator(
                ".research-discover-answer-label"
            ).all_inner_texts()
        )
        values = tuple(
            text.strip()
            for text in row.locator(
                ".research-discover-answer-value"
            ).all_inner_texts()
        )
        action = row.locator("a.selector-action-link")
        href = action.get_attribute("href") or ""
        action_ticker = (
            parse_qs(urlparse(href).query)
            .get("ticker", [""])[0]
            .strip()
            .upper()
        )
        geometry = action.bounding_box() or {}
        observed.append(
            {
                "ticker": ticker,
                "labels": labels,
                "values": values,
                "action_name": action.inner_text().strip(),
                "action_ticker": action_ticker,
                "action_height": geometry.get("height", 0),
                "visible": row.is_visible() and action.is_visible(),
            }
        )
    evaluated = evaluate_discover_rows(observed)
    return _assertion(
        "discover_three_question_rows",
        bool(evaluated["passed"]),
        str(evaluated["detail"]),
    )


def _monitor_brief_assertion(
    page: Any,
    viewport_width: int,
) -> dict[str, object]:
    grid = page.locator(".signal-grid.evidence-monitor-grid")
    neutral = page.locator(".follow-up-queue-empty:visible")
    if grid.count() == 0 and neutral.count() == 1:
        boundary = "does not prove that no external event, risk, or research need exists"
        actions = page.get_by_role("link", name="Open Discover", exact=True)
        neutral_text = neutral.inner_text().casefold()
        action_box = actions.first.bounding_box() if actions.count() == 1 else None
        passed = (
            boundary in neutral_text
            and actions.count() == 1
            and action_box is not None
            and float(action_box.get("height") or 0) >= 44
        )
        return _assertion(
            "monitor_brief_geometry",
            passed,
            (
                "one fail-closed Follow-up Queue empty state exposes one usable Discover action"
                if passed
                else "Follow-up Queue empty state must expose the external-event boundary and one 44px Discover action"
            ),
        )
    if grid.count() != 1:
        return _assertion(
            "monitor_brief_geometry",
            False,
            f"expected one Follow-up Queue grid or one empty state, found {grid.count()} grids",
        )
    cards = grid.locator(".signal-card:visible")
    kickers: list[str] = []
    boxes: list[tuple[object, object]] = []
    content_failures: list[str] = []
    for index in range(cards.count()):
        card = cards.nth(index)
        kicker = card.locator(".signal-kicker").inner_text().strip()
        title = card.locator(".signal-title").inner_text().strip()
        body = card.locator(".signal-body").inner_text().strip()
        badges = tuple(
            text.strip() for text in card.locator(".tiny-badge").all_inner_texts()
        )
        geometry = card.bounding_box() or {}
        kickers.append(kicker)
        boxes.append((geometry.get("x"), geometry.get("y")))
        if not title or not body or not badges or any(not badge for badge in badges):
            content_failures.append(
                f"Follow-up Queue card {index + 1} must expose a title, body, and badges"
            )
    evaluated = evaluate_monitor_brief(
        kickers=kickers,
        boxes=boxes,
        viewport_width=viewport_width,
    )
    details = tuple(content_failures) + (() if evaluated["passed"] else (str(evaluated["detail"]),))
    return _assertion(
        "monitor_brief_geometry",
        not details,
        (
            str(evaluated["detail"])
            if not details
            else "; ".join(details)
        ),
    )


def _monitor_rows_assertion(page: Any) -> dict[str, object]:
    table = page.locator("table.research-discipline-table")
    if table.count() > 1:
        return _assertion(
            "monitor_process_rows",
            False,
            f"expected zero or one primary Research Discipline table, found {table.count()}",
        )
    columns = (
        tuple(text.strip() for text in table.locator("thead th").all_inner_texts())
        if table.count() == 1
        else ()
    )
    rows = table.locator("tbody tr.research-discipline-row") if table.count() == 1 else None
    observed: list[dict[str, object]] = []
    for index in range(rows.count() if rows is not None else 0):
        assert rows is not None
        row = rows.nth(index)
        cells = tuple(text.strip() for text in row.locator("td").all_inner_texts())
        observed.append(
            {
                "cohort_order": row.get_attribute("data-cohort-order"),
                "ticker": row.locator("th[scope='row']").inner_text().strip(),
                "attention": cells[0] if len(cells) > 0 else "",
                "reason": cells[1] if len(cells) > 1 else "",
            }
        )
    neutral = page.locator(".research-monitor-neutral:visible")
    if neutral.count() > 1:
        return _assertion(
            "monitor_process_rows",
            False,
            f"expected at most one Monitor neutral state, found {neutral.count()}",
        )
    monitor_badges = page.locator(
        ".signal-grid.evidence-monitor-grid .tiny-badge"
    ).all_inner_texts()
    collapsed_monitor_counts: list[int] = []
    for badge in monitor_badges:
        parts = str(badge or "").strip().casefold().split()
        if len(parts) != 2 or parts[1] != "monitoring":
            continue
        try:
            collapsed_monitor_counts.append(int(parts[0]))
        except ValueError:
            continue
    if not collapsed_monitor_counts and neutral.count() == 1:
        try:
            collapsed_monitor_counts.append(
                int(neutral.get_attribute("data-monitor-count") or "")
            )
        except ValueError:
            pass
    if len(collapsed_monitor_counts) != 1:
        return _assertion(
            "monitor_process_rows",
            False,
            "expected one rendered monitoring count in the Follow-up Queue, "
            f"found {len(collapsed_monitor_counts)}",
        )
    expected_discipline_count = len(observed) + collapsed_monitor_counts[0]
    advanced = page.locator("details").filter(
        has=page.get_by_text(
            "Advanced: Monitor evidence",
            exact=True,
        )
    )
    advanced_count = 0
    if advanced.count() == 1:
        advanced.locator("summary").click()
        identity_rows = advanced.locator(
            "tr.research-discipline-identity-row"
        )
        if identity_rows.count():
            identity_rows.first.wait_for(state="visible", timeout=10_000)
        for index in range(identity_rows.count()):
            identity_row = identity_rows.nth(index)
            ticker = identity_row.locator("th[scope='row']").inner_text().strip()
            cells = tuple(
                text.strip() for text in identity_row.locator("td").all_inner_texts()
            )
            if ticker and len(cells) >= 2 and all(cells):
                advanced_count += 1
    evaluated = evaluate_monitor_rows(
        observed,
        primary_columns=columns,
        primary_table_present=table.count() == 1,
        advanced_present=advanced.count() == 1,
        advanced_identity_count=advanced_count,
        expected_discipline_count=expected_discipline_count,
        neutral_visible=neutral.count() == 1,
        queue_visible=page.locator(".signal-grid.evidence-monitor-grid:visible").count()
        == 1,
    )
    return _assertion(
        "monitor_process_rows",
        bool(evaluated["passed"]),
        str(evaluated["detail"]),
    )


def _company_workbench_primary_answer_text(answer: Any) -> str:
    """Read one direct answer body while rejecting missing or ambiguous markup."""

    body = answer.locator(":scope > p, :scope > strong")
    return body.first.inner_text().strip() if body.count() == 1 else ""


def _company_workbench_display_title(primary: Any, *, brief_count: int) -> str:
    """Read the one semantic Company Brief H2 without legacy decoration fallback."""

    title = primary.locator(".company-workbench-primary-heading h2")
    if brief_count != 1 or title.count() != 1:
        return ""
    return title.first.inner_text().strip()


def _company_workbench_primary_brief_assertion(page: Any) -> dict[str, object]:
    brief = page.locator(
        ".company-workbench-primary-brief[aria-label='Company Brief']"
    )
    brief_count = brief.count()
    primary = brief.first if brief_count else brief
    answer_nodes = primary.locator(".company-workbench-primary-answer")
    stop = primary.locator(".company-workbench-primary-stop")
    data_health_action = primary.locator("a.public-primary-action")
    open_modules = page.get_by_role(
        "button",
        name="Open evidence and analysis modules",
        exact=True,
    )
    data_health_box = (
        data_health_action.first.bounding_box()
        if data_health_action.count() == 1
        else None
    )
    open_modules_box = (
        open_modules.first.bounding_box()
        if open_modules.count() == 1
        else None
    )
    answer_labels: list[str] = []
    answer_texts: list[str] = []
    for index in range(answer_nodes.count()):
        answer = answer_nodes.nth(index)
        label = answer.locator("span").first
        answer_labels.append(
            label.inner_text().strip() if label.count() == 1 else ""
        )
        answer_texts.append(_company_workbench_primary_answer_text(answer))
    secondary_module_count = sum(
        page.get_by_role("heading", level=2, name=heading, exact=True).count()
        for heading in (
            "Research Decision Lab",
            "Business Trend",
            "Forward View",
            "Research Conclusion",
        )
    )
    secondary_module_count += page.locator("details").filter(
        has=page.get_by_text("Add a reviewed research record", exact=True)
    ).count()
    secondary_module_count += page.locator("details").filter(
        has=page.get_by_text("HTML Research Brief", exact=True)
    ).count()
    evaluated = evaluate_company_workbench_primary_brief(
        {
            "brief_count": brief_count,
            "brief_visible": brief_count == 1 and primary.is_visible(),
            "display_title": _company_workbench_display_title(
                primary,
                brief_count=brief_count,
            ),
            "answer_labels": tuple(answer_labels),
            "answer_texts": tuple(answer_texts),
            "stop_count": stop.count(),
            "stop_visible": stop.count() == 1 and stop.first.is_visible(),
            "stop_text": stop.first.inner_text().strip() if stop.count() == 1 else "",
            "data_health_action_count": data_health_action.count(),
            "data_health_action_visible": (
                data_health_action.count() == 1
                and data_health_action.first.is_visible()
            ),
            "data_health_action_height": (data_health_box or {}).get("height", 0),
            "data_health_action_href": (
                data_health_action.first.get_attribute("href") or ""
                if data_health_action.count() == 1
                else ""
            ),
            "open_modules_count": open_modules.count(),
            "open_modules_visible": (
                open_modules.count() == 1 and open_modules.first.is_visible()
            ),
            "open_modules_height": (open_modules_box or {}).get("height", 0),
            "secondary_module_count": secondary_module_count,
        }
    )
    detail = str(evaluated["detail"])
    if not evaluated["passed"]:
        detail += (
            f"; observed labels={answer_labels!r}; "
            f"data_health_height={(data_health_box or {}).get('height', 0)!r}; "
            f"module_open_height={(open_modules_box or {}).get('height', 0)!r}"
        )
    return _assertion(
        "company_workbench_primary_brief",
        bool(evaluated["passed"]),
        detail,
    )


def _open_company_workbench_modules(
    page: Any,
    *,
    timeout_seconds: float,
) -> dict[str, object]:
    button = page.get_by_role(
        "button",
        name="Open evidence and analysis modules",
        exact=True,
    )
    if button.count() != 1 or not button.first.is_visible():
        return _assertion(
            "company_workbench_module_open",
            False,
            f"expected one visible module-open action, found {button.count()}",
        )
    button.first.scroll_into_view_if_needed()
    button.first.click()
    activation_attempts = 1
    pointer_wait_seconds = min(12.0, max(2.0, timeout_seconds / 4))
    try:
        _wait_for_visible_text(
            page,
            "Research Decision Lab",
            timeout_seconds=pointer_wait_seconds,
        )
    except TimeoutError:
        if button.count() == 1 and button.first.is_visible():
            activation_attempts += 1
            button.first.focus()
            button.first.press("Enter")
        try:
            _wait_for_visible_text(
                page,
                "Research Decision Lab",
                timeout_seconds=max(2.0, timeout_seconds - pointer_wait_seconds),
            )
        except TimeoutError:
            body_text = page.locator("body").inner_text(timeout=2_000)
            script_state = page.locator('[data-testid="stApp"]').get_attribute(
                "data-test-script-state"
            )
            return _assertion(
                "company_workbench_module_open",
                False,
                (
                    "module-open actions did not restore Research Decision Lab; "
                    f"activation_attempts={activation_attempts}; "
                    f"button_remaining={button.count()}; "
                    f"script_state={script_state!r}; "
                    f"body_has_company_brief={'Company Brief' in body_text}"
                ),
            )
    _wait_for_dom_stability(page, timeout_seconds=timeout_seconds)
    decision_lab = page.get_by_role(
        "heading",
        level=2,
        name="Research Decision Lab",
        exact=True,
    )
    composer = page.locator("details").filter(
        has=page.get_by_text("Add a reviewed research record", exact=True)
    )
    passed = decision_lab.count() == 1 and composer.count() == 1
    return _assertion(
        "company_workbench_module_open",
        passed,
        (
            "explicit action restored secondary analysis and authoring; "
            f"activation_attempts={activation_attempts}"
            if passed
            else (
                f"decision_lab_count={decision_lab.count()}; "
                f"authoring_count={composer.count()}"
            )
        ),
    )


def _open_company_workbench_html_brief(
    page: Any,
    *,
    timeout_seconds: float,
) -> dict[str, object]:
    """Open the one native HTML Research Brief disclosure after module activation."""

    details = page.locator("details").filter(
        has=page.get_by_text("HTML Research Brief", exact=True)
    )
    if details.count() != 1:
        return _assertion(
            "company_workbench_html_brief_open",
            False,
            f"expected one HTML Research Brief disclosure, found {details.count()}",
        )
    summary = details.first.locator(":scope > summary")
    if (
        summary.count() != 1
        or summary.first.inner_text().strip() != "HTML Research Brief"
        or not summary.first.is_visible()
    ):
        return _assertion(
            "company_workbench_html_brief_open",
            False,
            "HTML Research Brief must expose one visible native summary control",
        )
    if details.first.get_attribute("open") is None:
        summary.first.click()
    one_pager = details.first.locator('[data-section="evidence-one-pager"]')
    try:
        one_pager.first.wait_for(
            state="visible",
            timeout=int(timeout_seconds * 1000),
        )
        _wait_for_dom_stability(page, timeout_seconds=timeout_seconds)
    except Exception as exc:
        return _assertion(
            "company_workbench_html_brief_open",
            False,
            f"HTML Research Brief did not expose its one-pager: {type(exc).__name__}: {exc}",
        )
    passed = (
        details.first.get_attribute("open") is not None
        and one_pager.count() == 1
        and one_pager.first.is_visible()
    )
    return _assertion(
        "company_workbench_html_brief_open",
        passed,
        (
            "native HTML Research Brief summary opened one visible one-pager"
            if passed
            else (
                f"details_open={details.first.get_attribute('open') is not None}; "
                f"one_pager_count={one_pager.count()}"
            )
        ),
    )


def _company_workbench_one_pager_dom_observation(page: Any) -> dict[str, object]:
    """Collect summary-scoped evidence from the opened in-app HTML fragment."""

    summary = _summary_scope_observation(page)
    scoped = page.evaluate(
        r"""() => {
            const visible = node => {
                if (!(node instanceof Element)) return false;
                const rect = node.getBoundingClientRect();
                if (rect.width <= 1 || rect.height <= 1 || node.getClientRects().length === 0) return false;
                let left = rect.left;
                let right = rect.right;
                let top = rect.top;
                let bottom = rect.bottom;
                let cumulativeOpacity = 1;
                let hitTestEligible = true;
                let documentScrollEligible = true;
                for (let current = node; current instanceof Element; current = current.parentElement) {
                    const style = getComputedStyle(current);
                    const opacity = Number.parseFloat(style.opacity || '1');
                    if (style.display === 'none' || style.visibility === 'hidden' ||
                        style.visibility === 'collapse' || style.contentVisibility === 'hidden' ||
                        !Number.isFinite(opacity) || style.clipPath !== 'none' ||
                        style.clip !== 'auto') return false;
                    cumulativeOpacity *= opacity;
                    if (style.position === 'fixed') documentScrollEligible = false;
                    if (current !== node) {
                        const ancestorRect = current.getBoundingClientRect();
                        const constrain = (
                            start, end, ancestorStart, ancestorEnd,
                            overflow, scrollSize, clientSize, scrollOffset
                        ) => {
                            if (!['auto', 'clip', 'hidden', 'scroll'].includes(overflow)) {
                                return [start, end];
                            }
                            const clippedStart = Math.max(start, ancestorStart);
                            const clippedEnd = Math.min(end, ancestorEnd);
                            if (clippedEnd - clippedStart > 1) {
                                return [clippedStart, clippedEnd];
                            }
                            const scrollReachable = ['auto', 'scroll'].includes(overflow) &&
                                scrollSize > clientSize + 1;
                            if (!scrollReachable) return null;
                            const contentStart = start - ancestorStart + scrollOffset;
                            const contentEnd = end - ancestorStart + scrollOffset;
                            if (Math.min(contentEnd, scrollSize) -
                                Math.max(contentStart, 0) <= 1) return null;
                            hitTestEligible = false;
                            return [ancestorStart, ancestorEnd];
                        };
                        if (['auto', 'clip', 'hidden', 'scroll'].includes(style.overflowX)) {
                            const constrained = constrain(
                                left,
                                right,
                                ancestorRect.left + current.clientLeft,
                                ancestorRect.left + current.clientLeft + current.clientWidth,
                                style.overflowX,
                                current.scrollWidth,
                                current.clientWidth,
                                current.scrollLeft
                            );
                            if (!constrained) return false;
                            [left, right] = constrained;
                        }
                        if (['auto', 'clip', 'hidden', 'scroll'].includes(style.overflowY)) {
                            const constrained = constrain(
                                top,
                                bottom,
                                ancestorRect.top + current.clientTop,
                                ancestorRect.top + current.clientTop + current.clientHeight,
                                style.overflowY,
                                current.scrollHeight,
                                current.clientHeight,
                                current.scrollTop
                            );
                            if (!constrained) return false;
                            [top, bottom] = constrained;
                        }
                        if (right - left <= 1 || bottom - top <= 1) return false;
                    }
                }
                if (Math.abs(cumulativeOpacity - 1) > 0.001) return false;
                const scrollingElement = document.scrollingElement || document.documentElement;
                const constrainToDocument = (
                    start, end, viewportSize, scrollOffset, scrollSize
                ) => {
                    const clippedStart = Math.max(0, start);
                    const clippedEnd = Math.min(viewportSize, end);
                    if (clippedEnd - clippedStart > 1) {
                        return [clippedStart, clippedEnd];
                    }
                    if (!documentScrollEligible) return null;
                    const contentStart = start + scrollOffset;
                    const contentEnd = end + scrollOffset;
                    if (Math.min(contentEnd, scrollSize) -
                        Math.max(contentStart, 0) <= 1) return null;
                    hitTestEligible = false;
                    return [0, viewportSize];
                };
                const horizontal = constrainToDocument(
                    left,
                    right,
                    window.innerWidth,
                    window.scrollX,
                    scrollingElement.scrollWidth
                );
                const vertical = constrainToDocument(
                    top,
                    bottom,
                    window.innerHeight,
                    window.scrollY,
                    scrollingElement.scrollHeight
                );
                if (!horizontal || !vertical) return false;
                const [viewportLeft, viewportRight] = horizontal;
                const [viewportTop, viewportBottom] = vertical;
                if (hitTestEligible && viewportRight - viewportLeft > 1 && viewportBottom - viewportTop > 1) {
                    const points = [
                        [(viewportLeft + viewportRight) / 2, (viewportTop + viewportBottom) / 2],
                        [viewportLeft + 0.5, viewportTop + 0.5],
                        [viewportRight - 0.5, viewportTop + 0.5],
                        [viewportLeft + 0.5, viewportBottom - 0.5],
                        [viewportRight - 0.5, viewportBottom - 0.5],
                    ];
                    if (!points.some(([x, y]) => {
                        const hit = document.elementFromPoint(x, y);
                        return hit && (
                            hit === node || node.contains(hit)
                        );
                    })) return false;
                }
                return true;
            };
            const detailsNodes = [...document.querySelectorAll('details')].filter(node =>
                String(node.querySelector(':scope > summary')?.innerText || '').trim() === 'HTML Research Brief'
            );
            const details = detailsNodes.length === 1 ? detailsNodes[0] : null;
            const allOnePagers = [...document.querySelectorAll('[data-section="evidence-one-pager"]')];
            const onePager = allOnePagers.length === 1 ? allOnePagers[0] : null;
            const surface = onePager?.closest('.srcc-html-brief');
            const overviewNodes = surface
                ? [...surface.querySelectorAll('[data-section="overview"]')]
                : [];
            const advancedNodes = surface
                ? [...surface.querySelectorAll('[data-section="advanced-evidence"]')]
                : [];
            const overview = overviewNodes.length === 1 ? overviewNodes[0] : null;
            const advanced = advancedNodes.length === 1 ? advancedNodes[0] : null;
            const stateNodes = onePager ? [...onePager.querySelectorAll('[data-state]')] : [];
            const labels = {
                available: 'state: complete',
                partial: 'state: partial',
                withheld: 'state: withheld',
                stale: 'state: stale',
                not_recorded: 'state: not recorded',
                excluded: 'state: excluded',
            };
            const onePagerVisible = visible(onePager);
            const stateTextMatches = onePagerVisible &&
                stateNodes.length > 0 && stateNodes.every(node => {
                const expected = labels[String(node.dataset.state || '').trim().toLowerCase()];
                const direct = [...node.children].find(child => child.matches('.srcc-state'));
                const stateText = direct || node.querySelector('.srcc-state');
                return Boolean(expected) && visible(stateText) &&
                    String(stateText.innerText || '').trim().toLowerCase() === expected;
            });
            const shareBasisNodes = onePager
                ? [...onePager.querySelectorAll('[data-share-basis-role][data-share-basis-state]')]
                : [];
            const shareBasisVisible = onePagerVisible
                ? shareBasisNodes.filter(visible)
                : [];
            const shareBasisTextMatches = shareBasisNodes.length > 0 && shareBasisNodes.every(node =>
                String(node.innerText || '').trim().toLowerCase() ===
                    `share basis state: ${String(node.dataset.shareBasisState || '').trim().toLowerCase()}`
            );
            return {
                html_brief_details_count: detailsNodes.length,
                html_brief_details_open: Boolean(details?.open),
                one_pager_count: allOnePagers.length,
                one_pager_visible_count: allOnePagers.filter(visible).length,
                one_pager_inside_html_brief: Boolean(details && onePager && details.contains(onePager)),
                overview_count: overviewNodes.length,
                advanced_evidence_count: advancedNodes.length,
                advanced_evidence_after_one_pager: Boolean(
                    onePager && advanced &&
                    (onePager.compareDocumentPosition(advanced) & Node.DOCUMENT_POSITION_FOLLOWING)
                ),
                advanced_evidence_visible: visible(advanced),
                one_pager_state_text_matches: stateTextMatches,
                one_pager_share_basis_visible_count: shareBasisVisible.length,
                one_pager_share_basis_text_matches: shareBasisTextMatches,
                document_overflow_px: Math.max(
                    0,
                    document.documentElement.scrollWidth - window.innerWidth
                ),
                inner_width: window.innerWidth,
                inner_height: window.innerHeight,
                device_pixel_ratio: window.devicePixelRatio,
                visual_viewport_width: window.visualViewport?.width || 0,
                visual_viewport_height: window.visualViewport?.height || 0,
                visual_viewport_scale: window.visualViewport?.scale || 0,
            };
        }"""
    )
    return {**summary, **scoped}


def _company_workbench_one_pager_observation(
    page: Any,
    *,
    width: int,
    height: int,
    requested_zoom: int,
    absent_before_open: bool,
    active_origin: str,
    request_urls: Iterable[str],
    external_request_count: int,
    console_errors: Iterable[str],
    page_errors: Iterable[str],
    server_runtime_output_status: str,
    server_deprecated_warning_count: int,
) -> dict[str, object]:
    observed = _company_workbench_one_pager_dom_observation(page)
    screenshot = page.screenshot(full_page=False, scale="device")
    if screenshot[:8] != b"\x89PNG\r\n\x1a\n" or len(screenshot) < 24:
        raise RuntimeError("Workbench one-pager screenshot did not produce a PNG")
    screenshot_width = int.from_bytes(screenshot[16:20], "big")
    screenshot_height = int.from_bytes(screenshot[20:24], "big")
    zoom_assertion = evaluate_html_brief_browser_zoom(
        requested_zoom=requested_zoom,
        declared_width=float(width),
        declared_height=float(height),
        screenshot_width=float(screenshot_width),
        screenshot_height=float(screenshot_height),
        inner_width=float(observed["inner_width"]),
        inner_height=float(observed["inner_height"]),
        visual_viewport_width=float(observed["visual_viewport_width"]),
        visual_viewport_height=float(observed["visual_viewport_height"]),
        device_pixel_ratio=float(observed["device_pixel_ratio"]),
        visual_viewport_scale=float(observed["visual_viewport_scale"]),
    )
    details = page.locator("details").filter(
        has=page.get_by_text("HTML Research Brief", exact=True)
    )
    download = details.first.get_by_role(
        "button",
        name="Download HTML Research Brief",
        exact=True,
    ) if details.count() == 1 else page.locator("button[data-never-match]")
    download_box = (
        download.first.bounding_box()
        if download.count() == 1 and download.first.is_visible()
        else None
    )
    return {
        **observed,
        "viewport": f"{width}x{height}",
        "requested_zoom": requested_zoom,
        "actual_browser_zoom": zoom_assertion.passed,
        "actual_browser_zoom_evidence": zoom_assertion.evidence,
        "one_pager_absent_before_open": absent_before_open,
        "one_pager_state_tokens": tuple(observed["one_pager_state_tokens"]),
        "one_pager_share_basis_tokens": tuple(
            observed["one_pager_share_basis_tokens"]
        ),
        "download_button_count": download.count(),
        "download_button_label": (
            download.first.inner_text().strip() if download.count() == 1 else ""
        ),
        "download_button_visible": (
            download.count() == 1 and download.first.is_visible()
        ),
        "download_button_height": (download_box or {}).get("height", 0),
        "console_errors": tuple(console_errors),
        "page_errors": tuple(page_errors),
        "server_runtime_output_status": server_runtime_output_status,
        "server_deprecated_warning_count": server_deprecated_warning_count,
        "active_origin": active_origin,
        "request_urls": tuple(request_urls),
        "external_request_count": external_request_count,
        "request_audit_complete": True,
    }


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
            for value in page.locator(
                ".research-workspace-brand strong, .sidebar-nav-title"
            ).all_text_contents()
            if value.strip()
        ]
        profile_labels = [
            value.strip()
            for value in page.locator(
                ".sr-context-bar .sr-context-item:first-child dd, "
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
        if not captions and len(profile_labels) == 1:
            captions = [f"Data profile: {profile_labels[0]}"]
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


def _bridge_transport_observation(
    page: Any,
    *,
    runtime_messages: Iterable[str],
    server_deprecated_warning_count: int = 0,
) -> dict[str, object]:
    """Measure only the two fixed accessibility-script transports in the live DOM."""

    observed = page.evaluate(
        """
() => {
  const bridgeNeedles = [
    "__stockResearchMainObserver",
    "data-research-authoring-error-owned"
  ];
  const containsBridge = (value) =>
    bridgeNeedles.some((needle) => String(value || "").includes(needle));
  const htmlBridges = Array.from(
    document.querySelectorAll('[data-testid="stHtml"]')
  ).filter((node) => containsBridge(node.innerHTML));
  const bridgeIframes = Array.from(document.querySelectorAll("iframe")).filter(
    (frame) => {
      let content = frame.getAttribute("srcdoc") || "";
      try {
        content += frame.contentDocument?.documentElement?.innerHTML || "";
      } catch (error) {
        return containsBridge(content);
      }
      return containsBridge(content);
    }
  );
  const focusableSelector = [
    "a[href]",
    "area[href]",
    "button",
    "input",
    "select",
    "textarea",
    "object",
    "embed",
    '[contenteditable="true"]',
    '[tabindex]:not([tabindex="-1"])'
  ].join(",");
  return {
    bridge_iframe_count: bridgeIframes.length,
    bridge_focusable_count: htmlBridges.reduce(
      (count, bridge) => count + bridge.querySelectorAll(focusableSelector).length,
      0
    ),
    bridge_heights: htmlBridges.map(
      (bridge) => bridge.getBoundingClientRect().height
    ),
    rendered_text: document.body.innerText
  };
}
"""
    )
    return evaluate_bridge_transport(
        runtime_messages=(
            *runtime_messages,
            str(observed.get("rendered_text", "")),
        ),
        bridge_iframe_count=observed.get("bridge_iframe_count", -1),
        bridge_focusable_count=observed.get("bridge_focusable_count", -1),
        bridge_heights=observed.get("bridge_heights", ()),
        server_deprecated_warning_count=server_deprecated_warning_count,
    )


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


def _route_transition_target(route: ResearchRoute) -> ResearchRoute:
    """Resolve one explicit, deterministic, non-self route transition."""

    away_name = ROUND_TRIP_AWAY_ROUTE_NAMES.get(route.name, "")
    matches = tuple(
        candidate for candidate in RESEARCH_ROUTES
        if candidate.name == away_name
    )
    if not away_name or len(matches) != 1 or matches[0] == route:
        raise ValueError(
            f"invalid route-transition mapping for {route.name!r}: {away_name!r}"
        )
    return matches[0]


def _navigate_and_verify_route(
    page: Any,
    *,
    base_url: str,
    route: ResearchRoute,
    phase: str,
    timeout_seconds: float,
) -> list[dict[str, object]]:
    """Navigate, settle the exact route content, then reject late URL drift."""

    expected_url = f"{base_url.rstrip('/')}{route.route}"
    page.goto(
        expected_url,
        wait_until="domcontentloaded",
        timeout=int(timeout_seconds * 1000),
    )
    _wait_for_visible_text(
        page,
        route.marker,
        timeout_seconds=timeout_seconds,
    )
    _wait_for_dom_stability(page, timeout_seconds=timeout_seconds)
    _wait_for_route_heading(page, route, timeout_seconds=timeout_seconds)
    return [
        evaluate_exact_route_url(
            actual_url=page.url,
            expected_url=expected_url,
            phase=phase,
        )
    ]


def _measure_route(
    browser: Any,
    *,
    base_url: str,
    route: ResearchRoute,
    viewport: tuple[int, int],
    timeout_seconds: float,
    server_deprecated_warning_count: int | Callable[[], int] = 0,
    server_runtime_output_status: str = "unverified",
) -> dict[str, object]:
    width, height = viewport
    context = browser.new_context(viewport={"width": width, "height": height})
    page = context.new_page()
    assertions: list[dict[str, object]] = []
    browser_errors: list[str] = []
    runtime_messages: list[str] = []
    bridge_transport = evaluate_bridge_transport(
        runtime_messages=(),
        bridge_iframe_count=-1,
        bridge_focusable_count=-1,
        bridge_heights=(),
    )

    def capture_console_message(message: Any) -> None:
        message_type = str(message.type).lower()
        detail = f"console {message_type}: {message.text}"
        runtime_messages.append(detail)
        if message_type == "error":
            browser_errors.append(detail)

    def capture_page_error(error: Any) -> None:
        detail = f"page error: {error}"
        runtime_messages.append(detail)
        browser_errors.append(detail)

    page.on("console", capture_console_message)
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
        if route.evidence_route:
            assertions.append(
                _evidence_navigation_assertion(page, phase="initial")
            )
        assertions.extend(_skip_link_assertions(page))
        if route.requires_primary_navigation and not route.evidence_route:
            assertions.append(_summary_focus_assertion(page))
        if route.name == "Discover":
            assertions.append(_discover_action_assertion(page))
            assertions.append(_discover_rows_assertion(page))
        if route.name == "Monitor":
            assertions.append(_monitor_brief_assertion(page, viewport[0]))
            assertions.append(_monitor_rows_assertion(page))
        if route.name == "Company Workbench":
            assertions.append(_company_workbench_primary_brief_assertion(page))

        assertions.extend(_media_preference_assertions(page, route))
        assertions.extend(_personal_navigation_authority_assertions(page))
        _wait_for_visible_text(page, route.marker, timeout_seconds=timeout_seconds)
        _wait_for_dom_stability(page, timeout_seconds=timeout_seconds)
        _wait_for_route_heading(page, route, timeout_seconds=timeout_seconds)
        assertions.extend(
            _semantic_main_assertions(page, phase="navigation_authority")
        )
        assertions.extend(
            _runtime_dom_assertions(page, phase="navigation_authority")
        )
        if route.evidence_route:
            assertions.append(
                _evidence_navigation_assertion(page, phase="navigation_authority")
            )
        if route.name == "Company Workbench":
            assertions.append(_company_workbench_primary_brief_assertion(page))
            module_open = _open_company_workbench_modules(
                page,
                timeout_seconds=timeout_seconds,
            )
            assertions.append(module_open)
            if module_open["passed"]:
                assertions.extend(_authoring_error_assertions(page))

        away_route = _route_transition_target(route)
        assertions.extend(
            _navigate_and_verify_route(
                page,
                base_url=base_url,
                route=away_route,
                phase="route_away",
                timeout_seconds=timeout_seconds,
            )
        )
        assertions.extend(
            _semantic_main_assertions(page, phase="route_away")
        )
        assertions.extend(
            _runtime_dom_assertions(page, phase="route_away")
        )
        if away_route.requires_primary_navigation:
            assertions.append(_navigation_assertion(page, away_route))
        if away_route.evidence_route:
            assertions.append(
                _evidence_navigation_assertion(page, phase="route_away")
            )

        assertions.extend(
            _navigate_and_verify_route(
                page,
                base_url=base_url,
                route=route,
                phase="route_return",
                timeout_seconds=timeout_seconds,
            )
        )
        assertions.extend(
            _semantic_main_assertions(page, phase="route_return")
        )
        assertions.extend(
            _runtime_dom_assertions(page, phase="route_return")
        )
        if route.requires_primary_navigation:
            assertions.append(_navigation_assertion(page, route))
        if route.evidence_route:
            assertions.append(
                _evidence_navigation_assertion(page, phase="route_return")
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
        server_warning_count = (
            server_deprecated_warning_count()
            if callable(server_deprecated_warning_count)
            else server_deprecated_warning_count
        )
        try:
            bridge_transport = _bridge_transport_observation(
                page,
                runtime_messages=runtime_messages,
                server_deprecated_warning_count=server_warning_count,
            )
        except Exception as exc:
            bridge_transport = evaluate_bridge_transport(
                runtime_messages=runtime_messages,
                bridge_iframe_count=-1,
                bridge_focusable_count=-1,
                bridge_heights=(),
                server_deprecated_warning_count=server_warning_count,
            )
            assertions.append(
                _assertion(
                    "bridge_transport_observation",
                    False,
                    f"{type(exc).__name__}: {exc}",
                )
            )
        assertions.extend(bridge_transport["assertions"])
        assertions.append(evaluate_browser_errors(browser_errors))
        context.close()

    return {
        "route": route.name,
        "viewport": f"{width}x{height}",
        "deprecated_component_warning_count": bridge_transport[
            "deprecated_component_warning_count"
        ],
        "bridge_iframe_count": bridge_transport["bridge_iframe_count"],
        "bridge_focusable_count": bridge_transport["bridge_focusable_count"],
        "bridge_height": bridge_transport["bridge_height"],
        "server_runtime_output_status": server_runtime_output_status,
        "passed": bool(assertions) and all(
            bool(assertion["passed"]) for assertion in assertions
        ),
        "assertions": assertions,
    }


def _measure_company_workbench_one_pager_cell(
    chromium: Any,
    *,
    chrome_executable: Path,
    base_url: str,
    cell: tuple[int, int, int],
    timeout_seconds: float,
    server_deprecated_warning_count: int | Callable[[], int],
    server_runtime_output_status: str,
) -> dict[str, object]:
    """Measure one isolated Workbench viewport/zoom cell after explicit open."""

    width, height, zoom = cell
    viewport = f"{width}x{height}"
    active_origin = _exact_http_origin(base_url)
    hostname = str(urlparse(base_url).hostname or "")
    request_urls: list[str] = []
    external_requests: list[str] = []
    console_errors: list[str] = []
    page_errors: list[str] = []
    assertions: list[dict[str, object]] = []
    observation: dict[str, object] = {
        "viewport": viewport,
        "requested_zoom": zoom,
        "active_origin": active_origin or "",
        "request_urls": (),
        "external_request_count": 0,
        "request_audit_complete": False,
    }
    if active_origin is None or not hostname:
        assertions.append(
            _assertion(
                "company_workbench_one_pager_origin",
                False,
                f"invalid active origin: {base_url!r}",
            )
        )
        return {
            "viewport": viewport,
            "zoom": zoom,
            "passed": False,
            "assertions": assertions,
            "observation": observation,
        }

    with tempfile.TemporaryDirectory(
        prefix="stock-research-workbench-one-pager-zoom-",
        dir="/tmp",
    ) as profile_directory:
        profile = Path(profile_directory)
        preferences = profile / "Default" / "Preferences"
        preferences.parent.mkdir(parents=True)
        preferences.write_text(
            json.dumps(
                _chromium_zoom_preferences(host=hostname, zoom=zoom),
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        context = chromium.launch_persistent_context(
            user_data_dir=profile,
            executable_path=str(chrome_executable),
            headless=True,
            viewport={"width": width, "height": height},
            screen={"width": width, "height": height},
            service_workers="block",
        )

        def intercept(route: Any, request: Any) -> None:
            request_url = str(request.url)
            parsed = urlparse(request_url)
            if parsed.scheme in {"http", "https"}:
                request_urls.append(request_url)
                if _exact_http_origin(request_url) != active_origin:
                    external_requests.append(request_url)
                    route.abort()
                    return
            route.continue_()

        context.route("**/*", intercept)
        page = context.pages[0] if context.pages else context.new_page()

        def capture_console_message(message: Any) -> None:
            if str(message.type).lower() == "error":
                console_errors.append(f"console error: {message.text}")

        def capture_page_error(error: Any) -> None:
            page_errors.append(f"page error: {error}")

        page.on("console", capture_console_message)
        page.on("pageerror", capture_page_error)
        try:
            route = next(
                route
                for route in RESEARCH_ROUTES
                if route.name == "Company Workbench"
            )
            expected_url = f"{base_url.rstrip('/')}{route.route}"
            page.goto(
                expected_url,
                wait_until="domcontentloaded",
                timeout=int(timeout_seconds * 1000),
            )
            _wait_for_visible_text(
                page,
                route.marker,
                timeout_seconds=timeout_seconds,
            )
            _wait_for_dom_stability(page, timeout_seconds=timeout_seconds)
            _wait_for_route_heading(
                page,
                route,
                timeout_seconds=timeout_seconds,
            )
            assertions.append(
                evaluate_exact_route_url(
                    actual_url=page.url,
                    expected_url=expected_url,
                    phase=f"one_pager_{viewport}_{zoom}",
                )
            )
            assertions.append(_company_workbench_primary_brief_assertion(page))
            absent_before_open = (
                page.locator('[data-section="evidence-one-pager"]').count() == 0
            )
            module_open = _open_company_workbench_modules(
                page,
                timeout_seconds=timeout_seconds,
            )
            assertions.append(module_open)
            if module_open["passed"]:
                html_brief_open = _open_company_workbench_html_brief(
                    page,
                    timeout_seconds=timeout_seconds,
                )
                assertions.append(html_brief_open)
                if html_brief_open["passed"]:
                    warning_count = (
                        server_deprecated_warning_count()
                        if callable(server_deprecated_warning_count)
                        else server_deprecated_warning_count
                    )
                    observation = _company_workbench_one_pager_observation(
                        page,
                        width=width,
                        height=height,
                        requested_zoom=zoom,
                        absent_before_open=absent_before_open,
                        active_origin=active_origin,
                        request_urls=request_urls,
                        external_request_count=len(external_requests),
                        console_errors=console_errors,
                        page_errors=page_errors,
                        server_runtime_output_status=server_runtime_output_status,
                        server_deprecated_warning_count=warning_count,
                    )
                    assertions.extend(
                        evaluate_company_workbench_one_pager_observation(
                            observation
                        )
                    )
        except Exception as exc:
            assertions.append(
                _assertion(
                    "company_workbench_one_pager_execution",
                    False,
                    f"{type(exc).__name__}: {exc}",
                )
            )
        finally:
            context.close()
    return {
        "viewport": viewport,
        "zoom": zoom,
        "passed": bool(assertions)
        and all(bool(assertion["passed"]) for assertion in assertions),
        "assertions": assertions,
        "observation": observation,
    }


def _repository_content_snapshot(root: Path) -> str:
    """Hash status plus every dirty/untracked path's current content."""

    def git_bytes(*args: str) -> bytes:
        return subprocess.run(
            ["git", *args],
            cwd=root,
            check=True,
            capture_output=True,
        ).stdout

    status = git_bytes(
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
    )
    dirty_path_bytes = b"".join(
        (
            git_bytes("diff", "--name-only", "-z", "--"),
            git_bytes("diff", "--cached", "--name-only", "-z", "--"),
            git_bytes("ls-files", "--others", "--exclude-standard", "-z"),
        )
    )
    relative_paths = sorted(
        {
            raw.decode("utf-8", errors="surrogateescape")
            for raw in dirty_path_bytes.split(b"\0")
            if raw
        }
    )
    digest = hashlib.sha256()
    digest.update(b"status\0")
    digest.update(status)
    for relative_path in relative_paths:
        encoded_path = relative_path.encode("utf-8", errors="surrogateescape")
        path = root / relative_path
        digest.update(b"\0path\0")
        digest.update(encoded_path)
        try:
            if path.is_symlink():
                digest.update(b"\0symlink\0")
                digest.update(
                    os.readlink(path).encode(
                        "utf-8",
                        errors="surrogateescape",
                    )
                )
            elif path.is_file():
                digest.update(b"\0file\0")
                digest.update(path.read_bytes())
            elif path.exists():
                digest.update(b"\0non-file\0")
            else:
                digest.update(b"\0missing\0")
        except OSError as exc:
            digest.update(b"\0unreadable\0")
            digest.update(type(exc).__name__.encode("ascii", errors="ignore"))
    return digest.hexdigest()


def _repository_status_snapshot(root: Path) -> str:
    """Compatibility alias for callers outside the gate."""

    return _repository_content_snapshot(root)


def _state_harness_static_observations(page: Any) -> tuple[dict[str, object], ...]:
    states = page.locator("[data-research-static-state]")
    observed: list[dict[str, object]] = []
    for index in range(states.count()):
        node = states.nth(index)
        observed.append(
            {
                "state": node.get_attribute("data-research-static-state"),
                "visible": node.is_visible(),
                "role": node.get_attribute("role"),
                "live": node.get_attribute("aria-live"),
                "busy": node.get_attribute("aria-busy"),
            }
        )
    return tuple(observed)


def _state_harness_transition_observations(
    page: Any,
) -> tuple[dict[str, object], ...]:
    nodes = page.locator(".research-state-message")
    observed: list[dict[str, object]] = []
    for index in range(nodes.count()):
        node = nodes.nth(index)
        observed.append(
            {
                "visible": node.is_visible(),
                "role": node.get_attribute("role"),
                "live": node.get_attribute("aria-live"),
                "atomic": node.get_attribute("aria-atomic"),
                "text": node.inner_text().strip(),
            }
        )
    return tuple(observed)


def _measure_state_harness(
    browser: Any,
    *,
    base_url: str,
    viewport: tuple[int, int],
    timeout_seconds: float,
) -> dict[str, object]:
    width, height = viewport
    context = browser.new_context(viewport={"width": width, "height": height})
    page = context.new_page()
    assertions: list[dict[str, object]] = []
    browser_errors: list[str] = []

    def capture_console_message(message: Any) -> None:
        if str(message.type).lower() == "error":
            browser_errors.append(f"console error: {message.text}")

    def capture_page_error(error: Any) -> None:
        browser_errors.append(f"page error: {error}")

    page.on("console", capture_console_message)
    page.on("pageerror", capture_page_error)
    try:
        page.goto(
            base_url,
            wait_until="domcontentloaded",
            timeout=int(timeout_seconds * 1000),
        )
        page.get_by_role(
            "heading",
            level=1,
            name="Synthetic research-state accessibility harness",
            exact=True,
        ).wait_for(
            state="visible",
            timeout=int(timeout_seconds * 1000),
        )
        _wait_for_dom_stability(page, timeout_seconds=timeout_seconds)
        static_states = _state_harness_static_observations(page)
        for state, title in STATE_HARNESS_TRANSITIONS:
            button = page.get_by_role("button", name=title, exact=True)
            button.click()
            page.locator(
                ".research-state-message[aria-live]"
            ).wait_for(
                state="visible",
                timeout=int(timeout_seconds * 1000),
            )
            _wait_for_dom_stability(page, timeout_seconds=timeout_seconds)
            live = evaluate_research_state_snapshot(
                static_states=static_states,
                transition_state=state,
                transition_nodes=_state_harness_transition_observations(page),
            )
            assertions.append(
                _assertion(
                    f"state_{state}_live",
                    bool(live["passed"]),
                    str(live["detail"]),
                )
            )

            button = page.get_by_role("button", name=title, exact=True)
            button.click()
            page.locator(
                ".research-state-message[role='group']"
            ).wait_for(
                state="visible",
                timeout=int(timeout_seconds * 1000),
            )
            _wait_for_dom_stability(page, timeout_seconds=timeout_seconds)
            rerender = evaluate_research_state_rerender(
                _state_harness_transition_observations(page)
            )
            assertions.append(
                _assertion(
                    f"state_{state}_deduplicated",
                    bool(rerender["passed"]),
                    str(rerender["detail"]),
                )
            )
        assertions.extend(_runtime_dom_assertions(page, phase="state_harness"))
    except Exception as exc:
        assertions.append(
            _assertion(
                "state_harness_execution",
                False,
                f"{type(exc).__name__}: {exc}",
            )
        )
    finally:
        assertions.append(evaluate_browser_errors(browser_errors))
        context.close()
    return {
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
            "allowed_dirty_product_paths": [],
            "staged_paths": [],
            "excluded_generated_paths": [],
            "detail": "repository hygiene not verified",
        },
        "viewports": [f"{width}x{height}" for width, height in VIEWPORTS],
        "routes": [route.name for route in RESEARCH_ROUTES],
        "results": [],
        "company_workbench_one_pager": [],
        "state_harness": {
            "passed": False,
            "results": [],
            "repository_snapshot": {
                "passed": False,
                "detail": "state harness did not execute",
            },
            "server_runtime_output": {
                "passed": False,
                "capture_status": "unverified",
                "deprecated_component_warning_count": None,
                "detail": "state harness server output not verified",
            },
        },
        "server_runtime_output": {
            "passed": False,
            "capture_status": "unverified",
            "deprecated_component_warning_count": None,
            "detail": "server stdout/stderr capture not verified",
        },
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
    allowed_dirty_paths: Iterable[str] = (),
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

    repository_hygiene = _repository_hygiene(
        root,
        allowed_dirty_paths=allowed_dirty_paths,
    )
    if not repository_hygiene["passed"]:
        return _failed_payload(
            "Repository contains staged or dirty non-generated implementation evidence; "
            "gate failed closed.",
            repository_hygiene=repository_hygiene,
        )

    identity: dict[str, object] | None = None
    server_evidence = RuntimeServerEvidence(
        base_url=normalized_base_url,
        runtime_messages=deque(maxlen=MAX_SERVER_RUNTIME_LINES),
        capture_status=(
            "unavailable_external_base_url"
            if normalized_base_url
            else "unverified"
        ),
    )
    state_server_evidence = RuntimeServerEvidence(
        base_url="",
        runtime_messages=deque(maxlen=MAX_SERVER_RUNTIME_LINES),
        capture_status="unverified",
    )
    state_results: list[dict[str, object]] = []
    one_pager_results: list[dict[str, object]] = []
    state_repository_snapshot = _assertion(
        "repository_snapshot_unchanged",
        False,
        "state harness repository snapshot not executed",
    )
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path=str(chrome),
                headless=True,
            )
            try:
                server_context = (
                    contextlib.nullcontext(server_evidence)
                    if normalized_base_url
                    else _captured_local_demo_server(
                        root,
                        timeout_seconds=max(5.0, timeout_seconds),
                    )
                )
                with server_context as active_server:
                    server_evidence = active_server
                    verified_active_url = validated_loopback_base_url(
                        active_server.base_url
                    )
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
                            server_deprecated_warning_count=(
                                active_server.deprecated_warning_count
                            ),
                            server_runtime_output_status=(
                                active_server.capture_status
                            ),
                        )
                        for viewport in VIEWPORTS
                        for route in RESEARCH_ROUTES
                    ]
                    one_pager_results = [
                        _measure_company_workbench_one_pager_cell(
                            playwright.chromium,
                            chrome_executable=Path(chrome),
                            base_url=verified_active_url,
                            cell=cell,
                            timeout_seconds=max(5.0, timeout_seconds),
                            server_deprecated_warning_count=(
                                active_server.deprecated_warning_count
                            ),
                            server_runtime_output_status=(
                                active_server.capture_status
                            ),
                        )
                        for cell in COMPANY_WORKBENCH_ONE_PAGER_CELLS
                    ]
                repository_before_state_harness = _repository_status_snapshot(root)
                with _captured_local_state_harness_server(
                    root,
                    timeout_seconds=max(5.0, timeout_seconds),
                ) as active_state_server:
                    state_server_evidence = active_state_server
                    state_results = [
                        _measure_state_harness(
                            browser,
                            base_url=active_state_server.base_url,
                            viewport=viewport,
                            timeout_seconds=max(5.0, timeout_seconds),
                        )
                        for viewport in VIEWPORTS
                    ]
                repository_after_state_harness = _repository_status_snapshot(root)
                state_repository_snapshot = evaluate_repository_snapshot_unchanged(
                    before=repository_before_state_harness,
                    after=repository_after_state_harness,
                )
            finally:
                browser.close()
    except Exception as exc:
        return _failed_payload(
            f"Browser gate could not execute and failed closed: {type(exc).__name__}: {exc}",
            repository_hygiene=repository_hygiene,
        )

    server_runtime_output = evaluate_server_runtime_output(
        capture_status=server_evidence.capture_status,
        runtime_messages=server_evidence.snapshot(),
        deprecated_component_warning_count=(
            server_evidence.deprecated_warning_count()
        ),
    )
    state_server_runtime_output = evaluate_server_runtime_output(
        capture_status=state_server_evidence.capture_status,
        runtime_messages=state_server_evidence.snapshot(),
        deprecated_component_warning_count=(
            state_server_evidence.deprecated_warning_count()
        ),
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
    failures.extend(
        (
            f"Research state harness {result['viewport']}: "
            + "; ".join(
                str(assertion["detail"])
                for assertion in result["assertions"]
                if not assertion["passed"]
            )
        )
        for result in state_results
        if not result["passed"]
    )
    failures.extend(
        (
            f"Company Workbench one-pager {result['viewport']}@{result['zoom']}: "
            + "; ".join(
                str(assertion["detail"])
                for assertion in result["assertions"]
                if not assertion["passed"]
            )
        )
        for result in one_pager_results
        if not result["passed"]
    )
    one_pager_payload = evaluate_company_workbench_one_pager_payload(
        one_pager_results
    )
    if not one_pager_payload["passed"]:
        failures.append(str(one_pager_payload["detail"]))
    if not server_runtime_output["passed"]:
        failures.append(str(server_runtime_output["detail"]))
    if not state_server_runtime_output["passed"]:
        failures.append(str(state_server_runtime_output["detail"]))
    if not state_repository_snapshot["passed"]:
        failures.append(str(state_repository_snapshot["detail"]))
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
        "company_workbench_one_pager": one_pager_results,
        "state_harness": {
            "passed": (
                bool(state_results)
                and all(result["passed"] for result in state_results)
                and bool(state_repository_snapshot["passed"])
                and bool(state_server_runtime_output["passed"])
            ),
            "results": state_results,
            "repository_snapshot": state_repository_snapshot,
            "server_runtime_output": state_server_runtime_output,
        },
        "server_runtime_output": server_runtime_output,
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
    parser.add_argument("--allow-dirty-path", action="append", default=[])
    args = parser.parse_args()
    payload = run_research_accessibility_browser_gate(
        args.root,
        base_url=args.base_url,
        chrome_executable=Path(args.chrome) if args.chrome else None,
        timeout_seconds=max(5.0, args.timeout_seconds),
        allowed_dirty_paths=tuple(args.allow_dirty_path),
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["verdict"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
