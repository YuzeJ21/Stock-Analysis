"""Fail-closed, no-write browser checks for injected offline research-brief bytes."""

from __future__ import annotations

import hashlib
import json
import math
import os
import stat
import subprocess
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import Callable, Iterable, Iterator, Mapping
from urllib.parse import quote, unquote, urlsplit

from src.public_performance_gate import find_chrome_executable


EXACT_HTML_BRIEF_CSP = (
    "default-src 'none'; script-src 'none'; connect-src 'none'; img-src 'none'; "
    "style-src 'unsafe-inline'; font-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'"
)

REQUIRED_OBSERVATION_KEYS = (
    "state",
    "viewport",
    "requested_zoom",
    "actual_browser_zoom",
    "h1_count",
    "header_count",
    "page_header_count",
    "one_pager_header_count",
    "main_count",
    "footer_count",
    "section_count",
    "heading_levels",
    "skip_target_focused",
    "visible_focus",
    "table_count",
    "captioned_table_count",
    "csp",
    "script_count",
    "event_handler_count",
    "form_count",
    "iframe_count",
    "remote_request_count",
    "boundary_visible",
    "blockers_visible",
    "provenance_visible",
    "overflow_px",
    "forced_colors_non_color_cue",
    "reduced_motion_static",
    "print_boundary_visible",
    "print_provenance_visible",
    "console_errors",
    "page_errors",
    "pdf_byte_length",
    "pdf_header",
    "one_pager_visible",
    "one_pager_before_overview",
    "one_pager_heading_count",
    "one_pager_section_count",
    "one_pager_answer_item_count",
    "one_pager_scenario_item_count",
    "one_pager_state_tokens",
    "one_pager_share_basis_tokens",
    "one_pager_state_node_count",
    "one_pager_state_role_count",
    "one_pager_unique_state_role_count",
    "one_pager_provenance_caption_visible",
    "one_pager_min_text_contrast_ratio",
    "one_pager_min_boundary_contrast_ratio",
    "one_pager_overflow_px",
    "one_pager_max_descendant_overflow_px",
    "one_pager_provenance_visible",
    "one_pager_blockers_visible",
    "one_pager_assumptions_visible",
    "one_pager_handoff_visible",
    "one_pager_forced_colors_non_color_cue",
    "one_pager_print_min_text_contrast_ratio",
    "one_pager_print_min_boundary_contrast_ratio",
    "one_pager_print_provenance_visible",
    "one_pager_print_blockers_visible",
    "one_pager_print_assumptions_visible",
    "one_pager_print_handoff_visible",
)

_OBSERVATION_TYPES: Mapping[str, object] = {
    "state": str,
    "viewport": str,
    "requested_zoom": int,
    "actual_browser_zoom": bool,
    "h1_count": int,
    "header_count": int,
    "page_header_count": int,
    "one_pager_header_count": int,
    "main_count": int,
    "footer_count": int,
    "section_count": int,
    "heading_levels": (tuple, int),
    "skip_target_focused": bool,
    "visible_focus": bool,
    "table_count": int,
    "captioned_table_count": int,
    "csp": str,
    "script_count": int,
    "event_handler_count": int,
    "form_count": int,
    "iframe_count": int,
    "remote_request_count": int,
    "boundary_visible": bool,
    "blockers_visible": bool,
    "provenance_visible": bool,
    "overflow_px": float,
    "forced_colors_non_color_cue": bool,
    "reduced_motion_static": bool,
    "print_boundary_visible": bool,
    "print_provenance_visible": bool,
    "console_errors": (tuple, str),
    "page_errors": (tuple, str),
    "pdf_byte_length": int,
    "pdf_header": str,
    "one_pager_visible": bool,
    "one_pager_before_overview": bool,
    "one_pager_heading_count": int,
    "one_pager_section_count": int,
    "one_pager_answer_item_count": int,
    "one_pager_scenario_item_count": int,
    "one_pager_state_tokens": (tuple, str),
    "one_pager_share_basis_tokens": (tuple, str),
    "one_pager_state_node_count": int,
    "one_pager_state_role_count": int,
    "one_pager_unique_state_role_count": int,
    "one_pager_provenance_caption_visible": bool,
    "one_pager_min_text_contrast_ratio": float,
    "one_pager_min_boundary_contrast_ratio": float,
    "one_pager_overflow_px": float,
    "one_pager_max_descendant_overflow_px": float,
    "one_pager_provenance_visible": bool,
    "one_pager_blockers_visible": bool,
    "one_pager_assumptions_visible": bool,
    "one_pager_handoff_visible": bool,
    "one_pager_forced_colors_non_color_cue": bool,
    "one_pager_print_min_text_contrast_ratio": float,
    "one_pager_print_min_boundary_contrast_ratio": float,
    "one_pager_print_provenance_visible": bool,
    "one_pager_print_blockers_visible": bool,
    "one_pager_print_assumptions_visible": bool,
    "one_pager_print_handoff_visible": bool,
}

_SYNTHETIC_STATE_ROLES = (
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
    "provenance-row-1-synthetic-provenance-synthetic-test-source",
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


def _synthetic_state_tokens(
    default: str,
    overrides: Mapping[str, str] | None = None,
) -> tuple[str, ...]:
    supplied = overrides or {}
    return tuple(
        sorted(
            f"{role}={supplied.get(role, default)}"
            for role in _SYNTHETIC_STATE_ROLES
        )
    )


SYNTHETIC_EXPECTED_STATE_ROLE_TOKENS: Mapping[str, tuple[str, ...]] = {
    "complete": _synthetic_state_tokens(
        "available",
        {
            "answers-still-withheld": "withheld",
            "answers-what-changed": "partial",
        },
    ),
    "partial": _synthetic_state_tokens(
        "partial",
        {
            "answers-still-withheld": "withheld",
            "answers-what-changed": "partial",
            "scenarios-bear-value-per-share": "available",
            "scenarios-base-value-per-share": "available",
            "scenarios-bull-value-per-share": "available",
            "operating-valuation-base-bridge-discounted-explicit-total": "available",
            "operating-valuation-base-bridge-terminal-value": "available",
            "operating-valuation-base-bridge-discounted-terminal-value": "available",
            "operating-valuation-base-bridge-enterprise-value": "available",
            "operating-valuation-base-bridge-supplied-shares": "available",
            "operating-valuation-base-bridge-supplied-value-per-share": "available",
        },
    ),
    "stale": _synthetic_state_tokens(
        "stale",
        {
            "answers-still-withheld": "withheld",
            "answers-what-changed": "partial",
        },
    ),
    "withheld": _synthetic_state_tokens("withheld"),
}

SYNTHETIC_EXPECTED_SHARE_BASIS_TOKENS = (
    "operating-valuation-base-bridge-share-basis=unverified",
    "scenarios-base-share-basis=unverified",
    "scenarios-bear-share-basis=unverified",
    "scenarios-bull-share-basis=unverified",
)

HTML_BRIEF_BROWSER_CELLS = (
    (1280, 720, 1),
    (1280, 720, 2),
    (1440, 1024, 1),
    (1440, 1024, 2),
    (1440, 1024, 4),
    (390, 844, 1),
)
HTML_BRIEF_BROWSER_STATES = ("complete", "partial", "stale", "withheld")
HTML_BRIEF_BROWSER_SOURCE_PATHS = (
    "src/company_workbench_html.py",
    "src/company_workbench_html_browser_gate.py",
    "tests/test_company_workbench_html_browser_gate.py",
)


@dataclass(frozen=True)
class HtmlBriefBrowserAssertion:
    name: str
    passed: bool
    evidence: str


@dataclass(frozen=True)
class HtmlBriefBrowserResult:
    state: str
    viewport: str
    zoom: int
    assertions: tuple[HtmlBriefBrowserAssertion, ...]

    @property
    def passed(self) -> bool:
        return bool(self.assertions) and all(
            assertion.passed for assertion in self.assertions
        )


def build_html_brief_browser_result_packet(
    results: Iterable[HtmlBriefBrowserResult],
    *,
    input_documents: Mapping[str, bytes],
    source_paths: Mapping[str, Path],
) -> tuple[dict[str, object], dict[str, object]]:
    """Build deterministic standalone browser results and source-hash payloads."""

    observed_results = tuple(results)
    expected_cells = tuple(
        (state, f"{width}x{height}", zoom)
        for state in HTML_BRIEF_BROWSER_STATES
        for width, height, zoom in HTML_BRIEF_BROWSER_CELLS
    )
    expected_cell_set = set(expected_cells)
    observed_cells = tuple(
        (result.state, result.viewport, result.zoom)
        for result in observed_results
    )
    if (
        len(observed_cells) != len(set(observed_cells))
        or set(observed_cells) != expected_cell_set
    ):
        raise ValueError(
            "HTML brief browser result cell set is missing, duplicate, or unexpected"
        )
    if set(input_documents) != set(HTML_BRIEF_BROWSER_STATES):
        raise ValueError("HTML brief input document states do not match the cell set")
    if any(type(payload) is not bytes for payload in input_documents.values()):
        raise TypeError("HTML brief input documents must contain exact bytes")
    if set(source_paths) != set(HTML_BRIEF_BROWSER_SOURCE_PATHS):
        raise ValueError("HTML brief packet source paths are incomplete or unexpected")

    source_records: list[dict[str, str]] = []
    for label, supplied_path in sorted(source_paths.items()):
        path = Path(supplied_path)
        if not path.is_file():
            raise ValueError(f"HTML brief packet source path is not a file: {label}")
        source_records.append(
            {
                "path": label,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )

    cell_order = {cell: index for index, cell in enumerate(expected_cells)}
    cell_records: list[dict[str, object]] = []
    for result in sorted(
        observed_results,
        key=lambda item: cell_order[(item.state, item.viewport, item.zoom)],
    ):
        assertion_names = tuple(assertion.name for assertion in result.assertions)
        if not assertion_names or len(assertion_names) != len(set(assertion_names)):
            raise ValueError(
                "HTML brief browser result cell assertions are missing or duplicate"
            )
        cell_records.append(
            {
                "state": result.state,
                "viewport": result.viewport,
                "zoom": result.zoom,
                "passed": result.passed,
                "assertions": [
                    {
                        "name": assertion.name,
                        "passed": assertion.passed,
                        "evidence": assertion.evidence,
                    }
                    for assertion in result.assertions
                ],
            }
        )
    passed_cells = sum(1 for record in cell_records if record["passed"])
    results_payload: dict[str, object] = {
        "schema_version": 1,
        "verdict": (
            "passed" if passed_cells == len(expected_cells) else "failed"
        ),
        "passed_cells": passed_cells,
        "total_cells": len(expected_cells),
        "cells": cell_records,
        "input_documents": [
            {
                "state": state,
                "sha256": hashlib.sha256(input_documents[state]).hexdigest(),
            }
            for state in HTML_BRIEF_BROWSER_STATES
        ],
    }
    source_payload: dict[str, object] = {
        "schema_version": 1,
        "sources": source_records,
    }
    return results_payload, source_payload


def _deterministic_json_bytes(payload: Mapping[str, object]) -> bytes:
    return (
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")


def write_html_brief_browser_result_packet(
    output_directory: Path | str,
    results: Iterable[HtmlBriefBrowserResult],
    *,
    input_documents: Mapping[str, bytes],
    source_paths: Mapping[str, Path],
) -> tuple[Path, Path]:
    """Write exactly two deterministic files to one fresh empty /tmp directory."""

    supplied = Path(output_directory)
    if not supplied.exists() or not supplied.is_dir():
        raise ValueError("HTML brief packet output must be an existing directory")
    resolved = supplied.resolve(strict=True)
    temporary_root = Path("/tmp").resolve(strict=True)
    if resolved == temporary_root or temporary_root not in resolved.parents:
        raise ValueError("HTML brief packet output must resolve under /tmp")
    if any(resolved.iterdir()):
        raise ValueError("HTML brief packet output directory must be empty")
    results_payload, source_payload = build_html_brief_browser_result_packet(
        results,
        input_documents=input_documents,
        source_paths=source_paths,
    )
    targets = (
        (resolved / "results.json", _deterministic_json_bytes(results_payload)),
        (
            resolved / "source-hashes.json",
            _deterministic_json_bytes(source_payload),
        ),
    )
    created: list[Path] = []
    try:
        for path, payload in targets:
            with path.open("xb") as handle:
                handle.write(payload)
            created.append(path)
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        raise
    return tuple(path for path, _payload in targets)


@contextmanager
def _injected_brief_server(cases: Mapping[str, bytes]) -> Iterator[str]:
    """Serve exact supplied HTML bytes from memory on one temporary loopback origin."""

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            path = unquote(urlsplit(self.path).path)
            if path == "/favicon.ico":
                self.send_response(204)
                self.end_headers()
                return
            state = path.strip("/").removesuffix(".html")
            payload = cases.get(state)
            if payload is None:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _normalized_http_origin(url: str) -> str | None:
    try:
        parsed = urlsplit(str(url))
        if parsed.scheme not in {"http", "https"}:
            return None
        if not parsed.hostname or parsed.username is not None or parsed.password is not None:
            return ""
        port = parsed.port
    except (TypeError, ValueError):
        return ""
    normalized_port = port or (443 if parsed.scheme == "https" else 80)
    host = parsed.hostname.lower()
    display_host = f"[{host}]" if ":" in host else host
    return f"{parsed.scheme}://{display_host}:{normalized_port}"


def evaluate_html_brief_request_origin(
    *,
    request_url: str,
    active_origin: str,
) -> tuple[str, bool]:
    """Allow non-HTTP URLs and the exact active origin; abort every other HTTP URL."""

    request_origin = _normalized_http_origin(request_url)
    if request_origin is None:
        return ("allow", False)
    expected_origin = _normalized_http_origin(active_origin)
    if request_origin and expected_origin and request_origin == expected_origin:
        return ("allow", False)
    return ("abort", True)


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


def evaluate_html_brief_browser_zoom(
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
) -> HtmlBriefBrowserAssertion:
    """Require real Chrome layout and device-scale geometry at 100/200/400 percent."""

    expected_inner_width = declared_width / requested_zoom if requested_zoom > 0 else 0
    expected_inner_height = declared_height / requested_zoom if requested_zoom > 0 else 0
    width_ratio = declared_width / inner_width if inner_width > 0 else 0
    height_ratio = declared_height / inner_height if inner_height > 0 else 0
    passed = (
        requested_zoom in (1, 2, 4)
        and abs(screenshot_width - declared_width) <= 1
        and abs(screenshot_height - declared_height) <= 1
        and abs(inner_width - expected_inner_width) <= 1
        and abs(inner_height - expected_inner_height) <= 1
        and abs(visual_viewport_width - inner_width) <= 1
        and abs(visual_viewport_height - inner_height) <= 1
        and abs(width_ratio - requested_zoom) <= 0.08
        and abs(height_ratio - requested_zoom) <= 0.08
        and abs(device_pixel_ratio - requested_zoom) <= 0.08
        and abs(visual_viewport_scale - 1) <= 0.01
    )
    return HtmlBriefBrowserAssertion(
        "actual_browser_zoom",
        passed,
        (
            f"requested={requested_zoom * 100}%; "
            f"declared={declared_width:.0f}x{declared_height:.0f}; "
            f"screenshot={screenshot_width:.0f}x{screenshot_height:.0f}; "
            f"inner={inner_width:.0f}x{inner_height:.0f}; "
            f"visual={visual_viewport_width:.0f}x{visual_viewport_height:.0f}; "
            f"layout_ratio={width_ratio:.3f}x{height_ratio:.3f}; "
            f"device_pixel_ratio={device_pixel_ratio:.3f}; "
            f"visual_viewport_scale={visual_viewport_scale:.3f}"
        ),
    )


def _has_exact_type(value: object, requirement: object) -> bool:
    if isinstance(requirement, tuple):
        container_type, item_type = requirement
        return type(value) is container_type and all(
            type(item) is item_type for item in value
        )
    return type(value) is requirement


def evaluate_html_brief_observation(
    observation: Mapping[str, object],
) -> HtmlBriefBrowserResult:
    """Evaluate a typed browser observation without permissive defaults."""
    valid = {
        key: key in observation
        and _has_exact_type(observation[key], _OBSERVATION_TYPES[key])
        for key in REQUIRED_OBSERVATION_KEYS
    }
    missing = tuple(key for key in REQUIRED_OBSERVATION_KEYS if key not in observation)
    wrong = tuple(
        key
        for key in REQUIRED_OBSERVATION_KEYS
        if key in observation and not valid[key]
    )

    def passes(keys: tuple[str, ...], predicate) -> bool:
        return all(valid[key] for key in keys) and bool(predicate())

    def value(key: str):
        return observation[key]

    def record(name: str, passed: bool, evidence: str) -> HtmlBriefBrowserAssertion:
        return HtmlBriefBrowserAssertion(name, bool(passed), evidence)

    heading_ok = passes(
        ("heading_levels",),
        lambda: (
            bool(value("heading_levels"))
            and value("heading_levels")[0] == 1
            and all(1 <= level <= 6 for level in value("heading_levels"))
            and all(
                current - previous <= 1
                for previous, current in zip(
                    value("heading_levels"), value("heading_levels")[1:]
                )
            )
        ),
    )
    assertions = (
        record(
            "observation_complete",
            not missing and not wrong,
            f"missing={missing or 'none'}; wrong_type={wrong or 'none'}",
        ),
        record(
            "one_h1",
            passes(("h1_count",), lambda: value("h1_count") == 1),
            f"h1_count={observation.get('h1_count')!r}",
        ),
        record(
            "semantic_landmarks",
            passes(
                (
                    "header_count",
                    "page_header_count",
                    "one_pager_header_count",
                    "main_count",
                    "footer_count",
                    "section_count",
                ),
                lambda: (
                    value("header_count") == 2
                    and value("page_header_count") == 1
                    and value("one_pager_header_count") == 1
                    and value("main_count") == value("footer_count") == 1
                    and value("section_count") >= 1
                ),
            ),
            (
                "document must contain two headers: one direct page header and one "
                "direct one-pager header; main/footer must each occur once"
            ),
        ),
        record(
            "logical_headings",
            heading_ok,
            f"heading_levels={observation.get('heading_levels')!r}",
        ),
        record(
            "skip_focus",
            passes(("skip_target_focused",), lambda: value("skip_target_focused")),
            f"focused={observation.get('skip_target_focused')!r}",
        ),
        record(
            "visible_focus",
            passes(("visible_focus",), lambda: value("visible_focus")),
            f"visible={observation.get('visible_focus')!r}",
        ),
        record(
            "tables_captioned",
            passes(
                ("table_count", "captioned_table_count"),
                lambda: (
                    value("table_count") > 0
                    and value("captioned_table_count") == value("table_count")
                ),
            ),
            f"tables={observation.get('table_count')!r}; captioned={observation.get('captioned_table_count')!r}",
        ),
        record(
            "csp_exact",
            passes(("csp",), lambda: value("csp") == EXACT_HTML_BRIEF_CSP),
            f"csp={observation.get('csp')!r}",
        ),
        record(
            "no_script",
            passes(("script_count",), lambda: value("script_count") == 0),
            f"script_count={observation.get('script_count')!r}",
        ),
        record(
            "no_event_handlers",
            passes(("event_handler_count",), lambda: value("event_handler_count") == 0),
            f"event_handler_count={observation.get('event_handler_count')!r}",
        ),
        record(
            "no_forms",
            passes(("form_count",), lambda: value("form_count") == 0),
            f"form_count={observation.get('form_count')!r}",
        ),
        record(
            "no_iframes",
            passes(("iframe_count",), lambda: value("iframe_count") == 0),
            f"iframe_count={observation.get('iframe_count')!r}",
        ),
        record(
            "no_remote_requests",
            passes(
                ("remote_request_count",), lambda: value("remote_request_count") == 0
            ),
            f"remote_request_count={observation.get('remote_request_count')!r}",
        ),
        record(
            "research_boundary_visible",
            passes(("boundary_visible",), lambda: value("boundary_visible")),
            f"visible={observation.get('boundary_visible')!r}",
        ),
        record(
            "blockers_visible",
            passes(("blockers_visible",), lambda: value("blockers_visible")),
            f"visible={observation.get('blockers_visible')!r}",
        ),
        record(
            "provenance_visible",
            passes(("provenance_visible",), lambda: value("provenance_visible")),
            f"visible={observation.get('provenance_visible')!r}",
        ),
        record(
            "no_overflow",
            passes(("overflow_px",), lambda: value("overflow_px") <= 1.0),
            f"overflow_px={observation.get('overflow_px')!r}",
        ),
        record(
            "forced_colors_non_color_cue",
            passes(
                ("forced_colors_non_color_cue",),
                lambda: value("forced_colors_non_color_cue"),
            ),
            f"present={observation.get('forced_colors_non_color_cue')!r}",
        ),
        record(
            "reduced_motion_static",
            passes(("reduced_motion_static",), lambda: value("reduced_motion_static")),
            str(
                observation.get("reduced_motion_evidence")
                or f"static={observation.get('reduced_motion_static')!r}"
            ),
        ),
        record(
            "print_boundary_visible",
            passes(
                ("print_boundary_visible",), lambda: value("print_boundary_visible")
            ),
            f"visible={observation.get('print_boundary_visible')!r}",
        ),
        record(
            "print_provenance_visible",
            passes(
                ("print_provenance_visible",), lambda: value("print_provenance_visible")
            ),
            f"visible={observation.get('print_provenance_visible')!r}",
        ),
        record(
            "no_console_errors",
            passes(("console_errors",), lambda: not value("console_errors")),
            f"errors={observation.get('console_errors')!r}",
        ),
        record(
            "no_page_errors",
            passes(("page_errors",), lambda: not value("page_errors")),
            f"errors={observation.get('page_errors')!r}",
        ),
        record(
            "pdf_in_memory",
            passes(
                ("pdf_byte_length", "pdf_header"),
                lambda: value("pdf_byte_length") > 4 and value("pdf_header") == "%PDF",
            ),
            f"byte_length={observation.get('pdf_byte_length')!r}; header={observation.get('pdf_header')!r}",
        ),
        record(
            "actual_browser_zoom",
            passes(
                ("requested_zoom", "actual_browser_zoom"),
                lambda: value("requested_zoom") in (1, 2, 4)
                and value("actual_browser_zoom"),
            ),
            str(
                observation.get("actual_browser_zoom_evidence")
                or (
                    f"requested_zoom={observation.get('requested_zoom')!r}; "
                    f"actual={observation.get('actual_browser_zoom')!r}"
                )
            ),
        ),
        record(
            "one_pager_visible",
            passes(("one_pager_visible",), lambda: value("one_pager_visible")),
            f"visible={observation.get('one_pager_visible')!r}",
        ),
        record(
            "one_pager_before_overview",
            passes(
                ("one_pager_before_overview",),
                lambda: value("one_pager_before_overview"),
            ),
            f"before_overview={observation.get('one_pager_before_overview')!r}",
        ),
        record(
            "one_pager_structure",
            passes(
                ("one_pager_heading_count", "one_pager_section_count"),
                lambda: value("one_pager_heading_count") == 8
                and value("one_pager_section_count") == 7,
            ),
            (
                f"headings={observation.get('one_pager_heading_count')!r}; "
                f"sections={observation.get('one_pager_section_count')!r}"
            ),
        ),
        record(
            "one_pager_lists",
            passes(
                (
                    "one_pager_answer_item_count",
                    "one_pager_scenario_item_count",
                ),
                lambda: value("one_pager_answer_item_count") == 4
                and value("one_pager_scenario_item_count") == 3,
            ),
            (
                f"answers={observation.get('one_pager_answer_item_count')!r}; "
                f"scenarios={observation.get('one_pager_scenario_item_count')!r}"
            ),
        ),
        record(
            "one_pager_state_truth",
            passes(
                ("state", "one_pager_state_tokens"),
                lambda: value("state") in SYNTHETIC_EXPECTED_STATE_ROLE_TOKENS
                and value("one_pager_state_tokens")
                == SYNTHETIC_EXPECTED_STATE_ROLE_TOKENS[value("state")],
            ),
            (
                f"case={observation.get('state')!r}; "
                f"tokens={observation.get('one_pager_state_tokens')!r}"
            ),
        ),
        record(
            "one_pager_state_role_integrity",
            passes(
                (
                    "one_pager_state_node_count",
                    "one_pager_state_role_count",
                    "one_pager_unique_state_role_count",
                ),
                lambda: value("one_pager_state_node_count")
                == value("one_pager_state_role_count")
                == value("one_pager_unique_state_role_count")
                == len(_SYNTHETIC_STATE_ROLES),
            ),
            (
                f"state_nodes={observation.get('one_pager_state_node_count')!r}; "
                f"paired_roles={observation.get('one_pager_state_role_count')!r}; "
                f"unique_roles={observation.get('one_pager_unique_state_role_count')!r}"
            ),
        ),
        record(
            "one_pager_share_basis_disclosure",
            passes(
                ("one_pager_share_basis_tokens",),
                lambda: value("one_pager_share_basis_tokens")
                == SYNTHETIC_EXPECTED_SHARE_BASIS_TOKENS,
            ),
            f"tokens={observation.get('one_pager_share_basis_tokens')!r}",
        ),
        record(
            "one_pager_provenance_caption_visible",
            passes(
                ("one_pager_provenance_caption_visible",),
                lambda: value("one_pager_provenance_caption_visible"),
            ),
            (
                "visible="
                f"{observation.get('one_pager_provenance_caption_visible')!r}"
            ),
        ),
        record(
            "one_pager_text_contrast",
            passes(
                ("one_pager_min_text_contrast_ratio",),
                lambda: value("one_pager_min_text_contrast_ratio") >= 4.5,
            ),
            f"minimum={observation.get('one_pager_min_text_contrast_ratio')!r}",
        ),
        record(
            "one_pager_boundary_contrast",
            passes(
                ("one_pager_min_boundary_contrast_ratio",),
                lambda: value("one_pager_min_boundary_contrast_ratio") >= 3.0,
            ),
            str(
                observation.get("one_pager_boundary_contrast_evidence")
                or (
                    "minimum="
                    f"{observation.get('one_pager_min_boundary_contrast_ratio')!r}"
                )
            ),
        ),
        record(
            "one_pager_no_overflow",
            passes(
                ("one_pager_overflow_px",),
                lambda: value("one_pager_overflow_px") <= 1.0,
            ),
            f"overflow_px={observation.get('one_pager_overflow_px')!r}",
        ),
        record(
            "one_pager_no_descendant_overflow",
            passes(
                ("one_pager_max_descendant_overflow_px",),
                lambda: value("one_pager_max_descendant_overflow_px") <= 1.0,
            ),
            (
                "max_descendant_overflow_px="
                f"{observation.get('one_pager_max_descendant_overflow_px')!r}"
            ),
        ),
        record(
            "one_pager_screen_content_visible",
            passes(
                (
                    "one_pager_provenance_visible",
                    "one_pager_blockers_visible",
                    "one_pager_assumptions_visible",
                    "one_pager_handoff_visible",
                ),
                lambda: all(
                    value(key)
                    for key in (
                        "one_pager_provenance_visible",
                        "one_pager_blockers_visible",
                        "one_pager_assumptions_visible",
                        "one_pager_handoff_visible",
                    )
                ),
            ),
            (
                "provenance/blockers/assumptions/handoff="
                f"{tuple(observation.get(key) for key in ('one_pager_provenance_visible', 'one_pager_blockers_visible', 'one_pager_assumptions_visible', 'one_pager_handoff_visible'))!r}"
            ),
        ),
        record(
            "one_pager_forced_colors_non_color_cue",
            passes(
                ("one_pager_forced_colors_non_color_cue",),
                lambda: value("one_pager_forced_colors_non_color_cue"),
            ),
            (
                "present="
                f"{observation.get('one_pager_forced_colors_non_color_cue')!r}"
            ),
        ),
        record(
            "one_pager_print_text_contrast",
            passes(
                ("one_pager_print_min_text_contrast_ratio",),
                lambda: value("one_pager_print_min_text_contrast_ratio") >= 4.5,
            ),
            (
                "minimum="
                f"{observation.get('one_pager_print_min_text_contrast_ratio')!r}"
            ),
        ),
        record(
            "one_pager_print_boundary_contrast",
            passes(
                ("one_pager_print_min_boundary_contrast_ratio",),
                lambda: value("one_pager_print_min_boundary_contrast_ratio") >= 3.0,
            ),
            str(
                observation.get("one_pager_print_boundary_contrast_evidence")
                or (
                    "minimum="
                    f"{observation.get('one_pager_print_min_boundary_contrast_ratio')!r}"
                )
            ),
        ),
        record(
            "one_pager_print_content_visible",
            passes(
                (
                    "one_pager_print_provenance_visible",
                    "one_pager_print_blockers_visible",
                    "one_pager_print_assumptions_visible",
                    "one_pager_print_handoff_visible",
                ),
                lambda: all(
                    value(key)
                    for key in (
                        "one_pager_print_provenance_visible",
                        "one_pager_print_blockers_visible",
                        "one_pager_print_assumptions_visible",
                        "one_pager_print_handoff_visible",
                    )
                ),
            ),
            (
                "provenance/blockers/assumptions/handoff="
                f"{tuple(observation.get(key) for key in ('one_pager_print_provenance_visible', 'one_pager_print_blockers_visible', 'one_pager_print_assumptions_visible', 'one_pager_print_handoff_visible'))!r}"
            ),
        ),
    )
    state = observation.get("state") if valid["state"] else "<invalid>"
    viewport = observation.get("viewport") if valid["viewport"] else "<invalid>"
    zoom = observation.get("requested_zoom") if valid["requested_zoom"] else 0
    return HtmlBriefBrowserResult(state, viewport, zoom, assertions)


def repository_fingerprint(repo_root: Path) -> str:
    """Hash every tracked and visible untracked path, type, and byte payload."""
    root = Path(repo_root).resolve()
    listed = subprocess.check_output(
        ["git", "ls-files", "-co", "--exclude-standard", "-z"], cwd=root
    )
    staged = subprocess.check_output(["git", "ls-files", "--stage", "-z"], cwd=root)
    index_entries: dict[bytes, list[bytes]] = {}
    for entry in (item for item in staged.split(b"\0") if item):
        metadata, relative_bytes = entry.split(b"\t", 1)
        index_entries.setdefault(relative_bytes, []).append(metadata)
    relative_paths = sorted(set(path for path in listed.split(b"\0") if path))
    digest = hashlib.sha256()
    for relative_bytes in relative_paths:
        path = root / os.fsdecode(relative_bytes)
        entries = tuple(sorted(index_entries.get(relative_bytes, ())))
        try:
            path_stat = path.lstat()
        except FileNotFoundError:
            path_stat = None
        if path_stat is None:
            kind, mode, payload = b"missing", b"", b""
        else:
            mode = f"{stat.S_IFMT(path_stat.st_mode):o}:{stat.S_IMODE(path_stat.st_mode):o}".encode()
            if stat.S_ISLNK(path_stat.st_mode):
                kind, payload = b"symlink", os.fsencode(os.readlink(path))
            elif stat.S_ISREG(path_stat.st_mode):
                kind, payload = b"regular", path.read_bytes()
            elif stat.S_ISDIR(path_stat.st_mode):
                is_gitlink = any(entry.startswith(b"160000 ") for entry in entries)
                kind = b"gitlink" if is_gitlink else b"directory"
                if is_gitlink:
                    try:
                        working_identity = subprocess.check_output(
                            ["git", "rev-parse", "HEAD"],
                            cwd=path,
                            stderr=subprocess.DEVNULL,
                        ).strip()
                    except (OSError, subprocess.CalledProcessError):
                        working_identity = b"unavailable"
                    payload = working_identity
                else:
                    payload = b""
            elif stat.S_ISFIFO(path_stat.st_mode):
                kind, payload = b"fifo", b""
            elif stat.S_ISSOCK(path_stat.st_mode):
                kind, payload = b"socket", b""
            elif stat.S_ISCHR(path_stat.st_mode):
                kind, payload = b"character-device", str(path_stat.st_rdev).encode()
            elif stat.S_ISBLK(path_stat.st_mode):
                kind, payload = b"block-device", str(path_stat.st_rdev).encode()
            else:
                kind, payload = b"unknown", b""
        index_payload = b"\0".join(entries)
        for field in (relative_bytes, kind, mode, index_payload, payload):
            digest.update(len(field).to_bytes(8, "big"))
            digest.update(field)
    return digest.hexdigest()


def _visible(page, selector: str, *, scroll_vertical: bool = True) -> bool:
    if scroll_vertical:
        expected_scroll_y = page.evaluate(
            """selector => {
                const node = document.querySelector(selector);
                if (!node) return null;
                delete document.documentElement.__srccVisibleSettlement;
                const initial = node.getBoundingClientRect();
                const requested = Math.max(
                    0,
                    window.scrollY + initial.top -
                        (window.innerHeight - initial.height) / 2
                );
                const maximum = Math.max(
                    0,
                    document.documentElement.scrollHeight - window.innerHeight
                );
                const expected = Math.min(requested, maximum);
                window.scrollTo(window.scrollX, expected);
                return expected;
            }""",
            selector,
        )
        if expected_scroll_y is None:
            return False
        try:
            page.wait_for_function(
                """({selector, expected}) => {
                    const node = document.querySelector(selector);
                    if (!node) return false;
                    void node.offsetWidth;
                    const rect = node.getBoundingClientRect();
                    const scrollSettled = Math.abs(window.scrollY - expected) <= 1;
                    const intersectsViewport = rect.right > 0 &&
                        rect.left < window.innerWidth &&
                        rect.bottom > 0 &&
                        rect.top < window.innerHeight;
                    if (!scrollSettled || !intersectsViewport) {
                        delete document.documentElement.__srccVisibleSettlement;
                        return false;
                    }
                    const fingerprint = JSON.stringify([
                        window.scrollX,
                        window.scrollY,
                        rect.left,
                        rect.right,
                        rect.top,
                        rect.bottom,
                    ]);
                    const previous = document.documentElement.__srccVisibleSettlement;
                    if (!previous || previous.fingerprint !== fingerprint) {
                        document.documentElement.__srccVisibleSettlement = {
                            fingerprint,
                            stableFrames: 0,
                        };
                        return false;
                    }
                    previous.stableFrames += 1;
                    return previous.stableFrames >= 2;
                }""",
                arg={"selector": selector, "expected": expected_scroll_y},
                polling="raf",
                timeout=2_000,
            )
        except Exception:
            return False
        finally:
            page.evaluate(
                "delete document.documentElement.__srccVisibleSettlement"
            )
    return bool(
        page.evaluate(
            """selector => {
                const node = document.querySelector(selector);
                if (!node) return false;
                let rect = node.getBoundingClientRect();
                let left = Math.max(0, rect.left);
                let right = Math.min(window.innerWidth, rect.right);
                let top = Math.max(0, rect.top);
                let bottom = Math.min(window.innerHeight, rect.bottom);
                for (let current = node; current instanceof Element; current = current.parentElement) {
                    const style = getComputedStyle(current);
                    const opacity = Number.parseFloat(style.opacity || '1');
                    if (style.display === 'none' || style.visibility === 'hidden' || style.visibility === 'collapse' ||
                        style.contentVisibility === 'hidden' || !Number.isFinite(opacity) || opacity <= 0.01) return false;
                    if (current !== node) {
                        const ancestor = current.getBoundingClientRect();
                        if (['hidden', 'clip', 'scroll', 'auto'].includes(style.overflowX)) {
                            left = Math.max(left, ancestor.left);
                            right = Math.min(right, ancestor.right);
                        }
                        if (['hidden', 'clip', 'scroll', 'auto'].includes(style.overflowY)) {
                            top = Math.max(top, ancestor.top);
                            bottom = Math.min(bottom, ancestor.bottom);
                        }
                    }
                }
                if (right - left <= 1 || bottom - top <= 1) return false;
                const points = [
                    [(left + right) / 2, (top + bottom) / 2],
                    [left + 1, top + 1],
                    [right - 1, bottom - 1],
                ];
                return points.some(([x, y]) => document.elementsFromPoint(x, y).some(
                    candidate => candidate === node || node.contains(candidate)
                ));
            }""",
            selector,
        )
    )


def _run_page_in_context(
    browser,
    *,
    width: int,
    height: int,
    operation: Callable[[object], object],
):
    """Run one page operation while closing context even if page setup/close fails."""
    context = browser.new_context(viewport={"width": width, "height": height})
    try:
        page = context.new_page()
        try:
            return operation(page)
        finally:
            page.close()
    finally:
        context.close()


def _focus_cue_state(page) -> Mapping[str, object]:
    return page.evaluate(
        """() => {
            const node = document.querySelector('a[href="#research-brief-main"]');
            if (!node) return {};
            const style = getComputedStyle(node);
            const sides = ['Top', 'Right', 'Bottom', 'Left'];
            return {
                outline: [style.outlineWidth, style.outlineStyle, style.outlineColor, style.outlineOffset],
                shadow: style.boxShadow,
                borders: sides.map(side => [style[`border${side}Width`], style[`border${side}Style`], style[`border${side}Color`]]),
                background: [style.backgroundColor, style.backgroundImage],
                foreground: [style.color, style.textDecorationLine, style.textDecorationColor],
            };
        }"""
    )


def _focus_cue_is_visible(
    page,
    *,
    before: Mapping[str, object],
    after: Mapping[str, object],
) -> bool:
    return bool(
        page.evaluate(
            r"""({before, after}) => {
                const node = document.activeElement;
                if (!node || !node.matches('a[href="#research-brief-main"]') || !node.matches(':focus-visible')) return false;
                const changed = key => JSON.stringify(before[key]) !== JSON.stringify(after[key]);
                const visibleColor = color => {
                    const normalized = String(color || '').replaceAll(' ', '').toLowerCase();
                    if (!normalized || normalized === 'transparent') return false;
                    const rgba = normalized.match(/^rgba\([^,]+,[^,]+,[^,]+,([^\)]+)\)$/);
                    return !rgba || Number.parseFloat(rgba[1]) > 0.01;
                };
                const outlineWidth = Number.parseFloat(after.outline?.[0] || '0');
                const outlineOffset = Number.parseFloat(after.outline?.[3] || '0');
                const outlineVisible = outlineWidth >= 1 &&
                    !['none', 'hidden'].includes(after.outline?.[1]) && visibleColor(after.outline?.[2]);
                const outlineChanged = changed('outline') && outlineVisible;
                const splitShadows = value => {
                    const parts = [];
                    let depth = 0;
                    let start = 0;
                    for (let index = 0; index < value.length; index += 1) {
                        if (value[index] === '(') depth += 1;
                        if (value[index] === ')') depth = Math.max(0, depth - 1);
                        if (value[index] === ',' && depth === 0) {
                            parts.push(value.slice(start, index).trim());
                            start = index + 1;
                        }
                    }
                    parts.push(value.slice(start).trim());
                    return parts.filter(Boolean);
                };
                const parseShadow = part => {
                    const color = part.match(/rgba?\([^\)]+\)/)?.[0] || '';
                    const lengths = (part.replace(color, '').match(/-?\d+(?:\.\d+)?px/g) || [])
                        .map(length => Number.parseFloat(length));
                    if (!color || lengths.length < 2 || lengths.length > 4 || lengths.some(length => !Number.isFinite(length))) return null;
                    const [offsetX, offsetY, blur = 0, spread = 0] = lengths;
                    if (blur < 0 || ![offsetX, offsetY, blur, spread].some(length => Math.abs(length) >= 1)) return null;
                    return {
                        inset: /\binset\b/.test(part),
                        offsetX,
                        offsetY,
                        blur,
                        spread,
                        color: color.replaceAll(' ', '').toLowerCase(),
                        visible: visibleColor(color),
                    };
                };
                const beforeShadows = splitShadows(String(before.shadow || 'none')).map(parseShadow).filter(Boolean);
                const afterShadows = splitShadows(String(after.shadow || 'none')).map(parseShadow).filter(Boolean);
                const matchedBefore = beforeShadows.map(() => false);
                const sameShadow = (left, right) => left.inset === right.inset &&
                    left.offsetX === right.offsetX && left.offsetY === right.offsetY &&
                    left.blur === right.blur && left.spread === right.spread &&
                    left.color === right.color;
                const focusSpecificShadows = afterShadows.filter(shadow => {
                    const matchIndex = beforeShadows.findIndex(
                        (candidate, index) => !matchedBefore[index] && sameShadow(candidate, shadow)
                    );
                    if (matchIndex >= 0) {
                        matchedBefore[matchIndex] = true;
                        return false;
                    }
                    return shadow.visible;
                });
                const insetShadowChanged = focusSpecificShadows.some(shadow => shadow.inset);
                const borderChanged = changed('borders') && (after.borders || []).some(border =>
                    Number.parseFloat(border[0] || '0') >= 1 &&
                    !['none', 'hidden'].includes(border[1]) && visibleColor(border[2])
                );
                const backgroundChanged = changed('background') &&
                    (visibleColor(after.background?.[0]) || after.background?.[1] !== 'none');
                const foregroundChanged = changed('foreground') && visibleColor(after.foreground?.[0]);
                const outlineInside = outlineChanged && outlineOffset <= -outlineWidth;
                const insideCue = borderChanged || backgroundChanged || foregroundChanged || insetShadowChanged || outlineInside;
                // Outward blurred shadows have renderer-dependent soft bounds. Fail closed
                // instead of using a symmetric approximation that can invent visible pixels.
                const outwardShadows = focusSpecificShadows.filter(shadow => !shadow.inset && shadow.blur === 0);
                const outwardCue = (outlineChanged && !outlineInside) || outwardShadows.length > 0;
                if (!insideCue && !outwardCue) return false;
                if (insideCue) return true;

                const outlineExtent = outlineChanged ? outlineWidth + Math.max(0, outlineOffset) : 0;
                const nodeRect = node.getBoundingClientRect();
                const clipBounds = {left: 0, right: window.innerWidth, top: 0, bottom: window.innerHeight};
                for (let current = node; current instanceof Element; current = current.parentElement) {
                    const style = getComputedStyle(current);
                    if (style.clipPath !== 'none' || style.clip !== 'auto') return false;
                    if (current !== node) {
                        const ancestor = current.getBoundingClientRect();
                        const clipLeft = ancestor.left + current.clientLeft;
                        const clipTop = ancestor.top + current.clientTop;
                        const clipRight = clipLeft + current.clientWidth;
                        const clipBottom = clipTop + current.clientHeight;
                        if (['hidden', 'clip', 'auto', 'scroll'].includes(style.overflowX)) {
                            clipBounds.left = Math.max(clipBounds.left, clipLeft);
                            clipBounds.right = Math.min(clipBounds.right, clipRight);
                        }
                        if (['hidden', 'clip', 'auto', 'scroll'].includes(style.overflowY)) {
                            clipBounds.top = Math.max(clipBounds.top, clipTop);
                            clipBounds.bottom = Math.min(clipBounds.bottom, clipBottom);
                        }
                    }
                }
                const visibleOutsideNode = (region, gap = 0) => {
                    const left = Math.max(region.left, clipBounds.left);
                    const right = Math.min(region.right, clipBounds.right);
                    const top = Math.max(region.top, clipBounds.top);
                    const bottom = Math.min(region.bottom, clipBounds.bottom);
                    if (right - left <= 1 || bottom - top <= 1) return false;
                    return left < nodeRect.left - gap - 0.5 || right > nodeRect.right + gap + 0.5 ||
                        top < nodeRect.top - gap - 0.5 || bottom > nodeRect.bottom + gap + 0.5;
                };
                if (outlineChanged && !outlineInside && outlineExtent >= 1 && visibleOutsideNode({
                    left: nodeRect.left - outlineExtent,
                    right: nodeRect.right + outlineExtent,
                    top: nodeRect.top - outlineExtent,
                    bottom: nodeRect.bottom + outlineExtent,
                }, Math.max(0, outlineOffset))) return true;
                return outwardShadows.some(shadow => visibleOutsideNode({
                    left: nodeRect.left + shadow.offsetX - shadow.spread,
                    right: nodeRect.right + shadow.offsetX + shadow.spread,
                    top: nodeRect.top + shadow.offsetY - shadow.spread,
                    bottom: nodeRect.bottom + shadow.offsetY + shadow.spread,
                }));
            }""",
            {"before": before, "after": after},
        )
    )


_MEDIA_SETTLEMENT_PROBE_ID = "srcc-media-settlement-probe"
_MEDIA_SETTLEMENT_STYLE_ID = "srcc-media-settlement-style"


def _media_css_evidence(
    page,
    *,
    viewport: str,
    boundary_selector: str,
    provenance_selector: str,
) -> dict[str, object]:
    evidence = page.evaluate(
        """({probeId, boundarySelector, provenanceSelector}) => {
            const probe = document.getElementById(probeId);
            const targetState = selector => {
                const node = document.querySelector(selector);
                if (!node) return {
                    present: false,
                    display: '',
                    visibility: '',
                    opacity: '',
                    media: '',
                    forced_colors: '',
                    reduced_motion: '',
                };
                const style = getComputedStyle(node);
                return {
                    present: true,
                    display: style.display,
                    visibility: style.visibility,
                    opacity: style.opacity,
                    media: style.getPropertyValue('--srcc-target-media-type').trim(),
                    forced_colors: style.getPropertyValue('--srcc-target-forced-colors').trim(),
                    reduced_motion: style.getPropertyValue('--srcc-target-reduced-motion').trim(),
                };
            };
            void document.documentElement.offsetWidth;
            let computedProbe = {media: '', forced_colors: '', reduced_motion: ''};
            if (probe) {
                void probe.offsetWidth;
                const style = getComputedStyle(probe);
                computedProbe = {
                    media: style.getPropertyValue('--srcc-media-type').trim(),
                    forced_colors: style.getPropertyValue('--srcc-forced-colors').trim(),
                    reduced_motion: style.getPropertyValue('--srcc-reduced-motion').trim(),
                };
            }
            return {
                match_media: {
                    print: matchMedia('print').matches,
                    forced_colors: matchMedia('(forced-colors: active)').matches,
                    reduced_motion: matchMedia('(prefers-reduced-motion: reduce)').matches,
                },
                computed_probe: computedProbe,
                targets: {
                    boundary: targetState(boundarySelector),
                    provenance: targetState(provenanceSelector),
                },
                actual_viewport: `${window.innerWidth}x${window.innerHeight}`,
            };
        }""",
        {
            "probeId": _MEDIA_SETTLEMENT_PROBE_ID,
            "boundarySelector": boundary_selector,
            "provenanceSelector": provenance_selector,
        },
    )
    browser = getattr(getattr(page, "context", None), "browser", None)
    browser_version = getattr(browser, "version", "") if browser is not None else ""
    if callable(browser_version):
        browser_version = browser_version()
    return {
        **dict(evidence),
        "viewport": viewport,
        "browser_version": str(browser_version or "unavailable"),
    }


def _settle_media_css(
    page,
    *,
    media: str,
    forced_colors: str,
    reduced_motion: str,
    viewport: str,
    boundary_selector: str,
    provenance_selector: str,
    timeout_ms: int = 2_000,
    operation: Callable[[object], object] | None = None,
) -> object:
    """Emulate media and wait until both media queries and CSS cascade agree."""
    expected = {
        "media": media,
        "forced_colors": forced_colors,
        "reduced_motion": reduced_motion,
    }
    if media not in {"screen", "print"}:
        raise ValueError(f"Unsupported media settlement target: {media!r}")
    if forced_colors not in {"active", "none"}:
        raise ValueError(
            f"Unsupported forced-colors settlement target: {forced_colors!r}"
        )
    if reduced_motion not in {"reduce", "no-preference"}:
        raise ValueError(
            f"Unsupported reduced-motion settlement target: {reduced_motion!r}"
        )
    if type(timeout_ms) is not int or timeout_ms <= 0:
        raise ValueError("Media settlement timeout must be a positive integer")

    page.evaluate(
        """({probeId, styleId, boundarySelector, provenanceSelector}) => {
            document.getElementById(probeId)?.remove();
            document.getElementById(styleId)?.remove();
            const style = document.createElement('style');
            style.id = styleId;
            const targetSelectors = `${boundarySelector}, ${provenanceSelector}`;
            style.textContent = `
                #${probeId} {
                    --srcc-media-type: screen !important;
                    --srcc-forced-colors: none !important;
                    --srcc-reduced-motion: no-preference !important;
                    position: fixed !important;
                    inset: 0 auto auto 0 !important;
                    width: 1px !important;
                    height: 1px !important;
                    opacity: 0 !important;
                    pointer-events: none !important;
                    contain: strict !important;
                    z-index: -2147483648 !important;
                }
                ${targetSelectors} {
                    --srcc-target-media-type: screen !important;
                    --srcc-target-forced-colors: none !important;
                    --srcc-target-reduced-motion: no-preference !important;
                }
                @media print {
                    #${probeId} { --srcc-media-type: print !important; }
                    ${targetSelectors} { --srcc-target-media-type: print !important; }
                }
                @media (forced-colors: active) {
                    #${probeId} { --srcc-forced-colors: active !important; }
                    ${targetSelectors} { --srcc-target-forced-colors: active !important; }
                }
                @media (prefers-reduced-motion: reduce) {
                    #${probeId} { --srcc-reduced-motion: reduce !important; }
                    ${targetSelectors} { --srcc-target-reduced-motion: reduce !important; }
                }
            `;
            (document.head || document.documentElement).append(style);
            const probe = document.createElement('div');
            probe.id = probeId;
            probe.setAttribute('aria-hidden', 'true');
            (document.body || document.documentElement).append(probe);
            void probe.offsetWidth;
            getComputedStyle(probe).getPropertyValue('--srcc-media-type');
        }""",
        {
            "probeId": _MEDIA_SETTLEMENT_PROBE_ID,
            "styleId": _MEDIA_SETTLEMENT_STYLE_ID,
            "boundarySelector": boundary_selector,
            "provenanceSelector": provenance_selector,
        },
    )
    try:
        page.emulate_media(
            media=media,
            forced_colors=forced_colors,
            reduced_motion=reduced_motion,
        )
        try:
            page.wait_for_function(
                """({probeId, expected, boundarySelector, provenanceSelector}) => {
                    const probe = document.getElementById(probeId);
                    if (!probe) return false;
                    void document.documentElement.offsetWidth;
                    void probe.offsetWidth;
                    const style = getComputedStyle(probe);
                    const computed = {
                        media: style.getPropertyValue('--srcc-media-type').trim(),
                        forced_colors: style.getPropertyValue('--srcc-forced-colors').trim(),
                        reduced_motion: style.getPropertyValue('--srcc-reduced-motion').trim(),
                    };
                    const queries = {
                        media: expected.media === 'print' ? matchMedia('print').matches : matchMedia('screen').matches,
                        forced_colors: matchMedia('(forced-colors: active)').matches === (expected.forced_colors === 'active'),
                        reduced_motion: matchMedia('(prefers-reduced-motion: reduce)').matches === (expected.reduced_motion === 'reduce'),
                    };
                    const targets = [
                        document.querySelector(boundarySelector),
                        document.querySelector(provenanceSelector),
                    ];
                    const targetsSettled = targets.every(node => {
                        if (!node) return false;
                        void node.offsetWidth;
                        const targetStyle = getComputedStyle(node);
                        return targetStyle.getPropertyValue('--srcc-target-media-type').trim() === expected.media &&
                            targetStyle.getPropertyValue('--srcc-target-forced-colors').trim() === expected.forced_colors &&
                            targetStyle.getPropertyValue('--srcc-target-reduced-motion').trim() === expected.reduced_motion;
                    });
                    const mediaSettled = queries.media && queries.forced_colors && queries.reduced_motion &&
                        computed.media === expected.media &&
                        computed.forced_colors === expected.forced_colors &&
                        computed.reduced_motion === expected.reduced_motion && targetsSettled;
                    if (!mediaSettled) {
                        delete probe.__srccMediaSettlement;
                        return false;
                    }
                    const renderedState = targets.map(node => {
                        const lineage = [];
                        for (let current = node; current instanceof Element; current = current.parentElement) {
                            void current.offsetWidth;
                            const currentStyle = getComputedStyle(current);
                            const rect = current.getBoundingClientRect();
                            lineage.push({
                                display: currentStyle.display,
                                visibility: currentStyle.visibility,
                                opacity: currentStyle.opacity,
                                content_visibility: currentStyle.contentVisibility,
                                overflow_x: currentStyle.overflowX,
                                overflow_y: currentStyle.overflowY,
                                clip: currentStyle.clip,
                                clip_path: currentStyle.clipPath,
                                position: currentStyle.position,
                                left: currentStyle.left,
                                top: currentStyle.top,
                                rect: [rect.left, rect.right, rect.top, rect.bottom],
                            });
                        }
                        return lineage;
                    });
                    const fingerprint = JSON.stringify(renderedState);
                    const previous = probe.__srccMediaSettlement;
                    if (!previous || previous.fingerprint !== fingerprint) {
                        probe.__srccMediaSettlement = {fingerprint, stableFrames: 0};
                        return false;
                    }
                    previous.stableFrames += 1;
                    return previous.stableFrames >= 2;
                }""",
                arg={
                    "probeId": _MEDIA_SETTLEMENT_PROBE_ID,
                    "expected": expected,
                    "boundarySelector": boundary_selector,
                    "provenanceSelector": provenance_selector,
                },
                polling="raf",
                timeout=timeout_ms,
            )
        except Exception as exc:
            try:
                observed = _media_css_evidence(
                    page,
                    viewport=viewport,
                    boundary_selector=boundary_selector,
                    provenance_selector=provenance_selector,
                )
            except Exception as diagnostic_exc:  # pragma: no cover - crashed page
                observed = {"diagnostic_error": repr(diagnostic_exc)}
            raise RuntimeError(
                "HTML brief media/CSS settlement failed; "
                f"expected={expected!r}; observed={observed!r}"
            ) from exc
        evidence = _media_css_evidence(
            page,
            viewport=viewport,
            boundary_selector=boundary_selector,
            provenance_selector=provenance_selector,
        )
        if operation is None:
            return evidence
        return operation(page)
    finally:
        page.evaluate(
            """({probeId, styleId}) => {
                document.getElementById(probeId)?.remove();
                document.getElementById(styleId)?.remove();
            }""",
            {
                "probeId": _MEDIA_SETTLEMENT_PROBE_ID,
                "styleId": _MEDIA_SETTLEMENT_STYLE_ID,
            },
        )


def _summary_scope_observation(page) -> dict[str, object]:
    """Collect one-pager-only semantics, visibility, contrast, and overflow."""

    return page.evaluate(
        r"""() => {
            const onePager = document.querySelector('[data-section="evidence-one-pager"]');
            const overview = document.querySelector('[data-section="overview"]');
            const materialPaintSelector = [
                '[data-section="one-pager-provenance"]',
                '[data-section="one-pager-provenance"] caption',
                '[data-section="one-pager-provenance"] tbody',
                '.srcc-blockers',
                '[data-section="one-pager-scenarios"] > ol > li',
                '[data-section="one-pager-scenarios"] > ol > li > p',
                '[data-section="one-pager-scenarios"] .srcc-state',
                '[data-section="one-pager-handoff"]',
                '[data-state][data-state-role]',
                '[data-state][data-state-role] .srcc-state',
                '[data-share-basis-role][data-share-basis-state]',
            ].join(',');
            let materialPaintCandidates = null;
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
                const strictCurrentHitTest = () => {
                    const currentRect = node.getBoundingClientRect();
                    let currentLeft = currentRect.left;
                    let currentRight = currentRect.right;
                    let currentTop = currentRect.top;
                    let currentBottom = currentRect.bottom;
                    for (let current = node.parentElement;
                        current instanceof Element;
                        current = current.parentElement) {
                        const style = getComputedStyle(current);
                        const ancestorRect = current.getBoundingClientRect();
                        if (['auto', 'clip', 'hidden', 'scroll'].includes(style.overflowX)) {
                            currentLeft = Math.max(
                                currentLeft,
                                ancestorRect.left + current.clientLeft
                            );
                            currentRight = Math.min(
                                currentRight,
                                ancestorRect.left + current.clientLeft + current.clientWidth
                            );
                        }
                        if (['auto', 'clip', 'hidden', 'scroll'].includes(style.overflowY)) {
                            currentTop = Math.max(
                                currentTop,
                                ancestorRect.top + current.clientTop
                            );
                            currentBottom = Math.min(
                                currentBottom,
                                ancestorRect.top + current.clientTop + current.clientHeight
                            );
                        }
                        if (currentRight - currentLeft <= 1 ||
                            currentBottom - currentTop <= 1) return false;
                    }
                    const viewportLeft = Math.max(0, currentLeft);
                    const viewportRight = Math.min(window.innerWidth, currentRight);
                    const viewportTop = Math.max(0, currentTop);
                    const viewportBottom = Math.min(window.innerHeight, currentBottom);
                    if (viewportRight - viewportLeft <= 1 ||
                        viewportBottom - viewportTop <= 1) return false;
                    const points = [
                        [(viewportLeft + viewportRight) / 2, (viewportTop + viewportBottom) / 2],
                        [viewportLeft + 0.5, viewportTop + 0.5],
                        [viewportRight - 0.5, viewportTop + 0.5],
                        [viewportLeft + 0.5, viewportBottom - 0.5],
                        [viewportRight - 0.5, viewportBottom - 0.5],
                    ];
                    const pointKeys = new Set(points.map(([x, y]) => `${x}:${y}`));
                    for (const descendant of node.querySelectorAll('*')) {
                        if (points.length >= 37) break;
                        const descendantRect = descendant.getBoundingClientRect();
                        const descendantLeft = Math.max(viewportLeft, descendantRect.left);
                        const descendantRight = Math.min(viewportRight, descendantRect.right);
                        const descendantTop = Math.max(viewportTop, descendantRect.top);
                        const descendantBottom = Math.min(viewportBottom, descendantRect.bottom);
                        if (descendantRight - descendantLeft <= 1 ||
                            descendantBottom - descendantTop <= 1) continue;
                        const x = (descendantLeft + descendantRight) / 2;
                        const y = (descendantTop + descendantBottom) / 2;
                        const key = `${x}:${y}`;
                        if (pointKeys.has(key)) continue;
                        pointKeys.add(key);
                        points.push([x, y]);
                    }
                    const isRelatedHit = hit => hit && (
                        hit === node || node.contains(hit)
                    );
                    const pointHits = () => points.map(([x, y]) =>
                        document.elementFromPoint(x, y)
                    );
                    const ordinaryHits = pointHits();
                    const ordinaryHit = ordinaryHits.some(isRelatedHit);
                    const needsMaterialPaintProbe = node === onePager ||
                        node.matches(materialPaintSelector);
                    if (!ordinaryHit || !needsMaterialPaintProbe) return ordinaryHit;
                    const relatedIndexes = ordinaryHits.flatMap((hit, index) =>
                        isRelatedHit(hit) ? [index] : []
                    );
                    const descendantIndexes = relatedIndexes.filter(index =>
                        ordinaryHits[index] !== node
                    );
                    const evidenceIndexes = descendantIndexes.length > 0
                        ? descendantIndexes
                        : relatedIndexes;
                    const colorAlpha = value => {
                        const normalized = String(value || '').trim().toLowerCase();
                        if (!normalized || ['none', 'transparent'].includes(normalized)) {
                            return 0;
                        }
                        const alphaValue = token => {
                            const trimmed = token.trim();
                            const parsed = Number.parseFloat(trimmed);
                            if (!Number.isFinite(parsed)) return 1;
                            return trimmed.endsWith('%') ? parsed / 100 : parsed;
                        };
                        const functional = normalized.match(
                            /^(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch|color)\((.*)\)$/
                        );
                        if (!functional) return 1;
                        const body = functional[1];
                        const slash = body.lastIndexOf('/');
                        if (slash >= 0) return alphaValue(body.slice(slash + 1));
                        if (body.includes(',')) {
                            const components = body.split(',');
                            return components.length === 4
                                ? alphaValue(components[3])
                                : 1;
                        }
                        return 1;
                    };
                    const cssColors = value => String(value || '').match(
                        /(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch|color)\([^)]*\)|transparent/gi
                    ) || [];
                    const imageHasMaterialPaint = value => {
                        if (!value || value === 'none') return false;
                        const colors = cssColors(value);
                        if (colors.length === 0) return true;
                        return colors.some(color =>
                            color.toLowerCase() !== 'transparent' &&
                            colorAlpha(color) > 0.01
                        );
                    };
                    const splitCssLayers = value => {
                        const layers = [];
                        let depth = 0;
                        let start = 0;
                        for (let index = 0; index < value.length; index += 1) {
                            if (value[index] === '(') depth += 1;
                            else if (value[index] === ')') depth = Math.max(0, depth - 1);
                            else if (value[index] === ',' && depth === 0) {
                                layers.push(value.slice(start, index));
                                start = index + 1;
                            }
                        }
                        layers.push(value.slice(start));
                        return layers;
                    };
                    const cssLength = (value, basis) => {
                        const text = String(value || '').trim().toLowerCase();
                        const parsed = Number.parseFloat(text);
                        if (!Number.isFinite(parsed)) return Number.NaN;
                        if (text.endsWith('%')) return basis * parsed / 100;
                        if (text.endsWith('vw')) return window.innerWidth * parsed / 100;
                        if (text.endsWith('vh')) return window.innerHeight * parsed / 100;
                        if (text.endsWith('vmin')) {
                            return Math.min(window.innerWidth, window.innerHeight) * parsed / 100;
                        }
                        if (text.endsWith('vmax')) {
                            return Math.max(window.innerWidth, window.innerHeight) * parsed / 100;
                        }
                        return parsed;
                    };
                    const paintRect = (origin, style, pseudo) => {
                        const originRect = origin.getBoundingClientRect();
                        if (!pseudo) return originRect;
                        const fixed = style.position === 'fixed';
                        const container = fixed
                            ? {
                                left: 0,
                                top: 0,
                                right: window.innerWidth,
                                bottom: window.innerHeight,
                                width: window.innerWidth,
                                height: window.innerHeight,
                            }
                            : originRect;
                        const axis = (start, end, size, containerStart, extent) => {
                            const startValue = cssLength(start, extent);
                            const endValue = cssLength(end, extent);
                            let sizeValue = cssLength(size, extent);
                            if (!Number.isFinite(sizeValue) &&
                                Number.isFinite(startValue) &&
                                Number.isFinite(endValue)) {
                                sizeValue = Math.max(0, extent - startValue - endValue);
                            }
                            if (!Number.isFinite(sizeValue)) sizeValue = extent;
                            const position = Number.isFinite(startValue)
                                ? containerStart + startValue
                                : Number.isFinite(endValue)
                                    ? containerStart + extent - endValue - sizeValue
                                    : containerStart;
                            return [position, sizeValue];
                        };
                        let [left, width] = axis(
                            style.left, style.right, style.width,
                            container.left, container.width
                        );
                        let [top, height] = axis(
                            style.top, style.bottom, style.height,
                            container.top, container.height
                        );
                        if (style.boxSizing === 'content-box') {
                            width += ['Left', 'Right'].reduce(
                                (total, side) => total +
                                    (Number.parseFloat(
                                        style[`border${side}Width`] || '0'
                                    ) || 0) +
                                    (Number.parseFloat(
                                        style[`padding${side}`] || '0'
                                    ) || 0),
                                0
                            );
                            height += ['Top', 'Bottom'].reduce(
                                (total, side) => total +
                                    (Number.parseFloat(
                                        style[`border${side}Width`] || '0'
                                    ) || 0) +
                                    (Number.parseFloat(
                                        style[`padding${side}`] || '0'
                                    ) || 0),
                                0
                            );
                        }
                        if (style.transform && style.transform !== 'none') {
                            try {
                                const matrix = new DOMMatrixReadOnly(style.transform);
                                left += matrix.m41;
                                top += matrix.m42;
                            } catch (_error) {
                                return originRect;
                            }
                        }
                        return {
                            left,
                            right: left + width,
                            top,
                            bottom: top + height,
                            width,
                            height,
                        };
                    };
                    const materialColor = value => {
                        const colors = cssColors(value);
                        return colors.length === 0 || colors.some(color =>
                            color.toLowerCase() !== 'transparent' &&
                            colorAlpha(color) > 0.01
                        );
                    };
                    const shadowLayers = style => {
                        const value = style.boxShadow;
                        if (!value || value === 'none') return [];
                        return splitCssLayers(String(value)).map(layer => {
                            const lengths = layer.replace(
                                /(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch|color)\([^)]*\)|transparent/gi,
                                ''
                            ).match(/-?(?:\d+\.?\d*|\.\d+)(?:[a-z%]+)?/gi) || [];
                            const parsed = lengths.map(length =>
                                Number.parseFloat(length)
                            );
                            return {
                                inset: /\binset\b/i.test(layer),
                                material: materialColor(layer),
                                offsetX: parsed[0] || 0,
                                offsetY: parsed[1] || 0,
                                blur: Math.max(0, parsed[2] || 0),
                                spread: parsed[3] || 0,
                            };
                        });
                    };
                    const materialBorderWidth = (style, side) => {
                        const width = Number.parseFloat(
                            style[`border${side}Width`] || '0'
                        );
                        return width > 0.01 &&
                            !['none', 'hidden'].includes(style[`border${side}Style`]) &&
                            colorAlpha(style[`border${side}Color`]) > 0.01
                            ? width
                            : 0;
                    };
                    const materialOutline = style => {
                        const width = Number.parseFloat(style.outlineWidth || '0');
                        return {
                            width: width > 0.01 &&
                                !['none', 'hidden'].includes(style.outlineStyle) &&
                                colorAlpha(style.outlineColor) > 0.01
                                ? width
                                : 0,
                            offset: Number.parseFloat(style.outlineOffset || '0') || 0,
                        };
                    };
                    const shadowHasMaterialPaint = (origin, style, pseudo) => {
                        const rect = paintRect(origin, style, pseudo);
                        const minimumExtent = Math.max(
                            1,
                            Math.min(
                                Math.max(0, rect.width),
                                Math.max(0, rect.height)
                            ) / 2
                        );
                        return shadowLayers(style).some(layer =>
                            layer.material && (
                                !layer.inset ||
                                layer.blur + Math.max(0, layer.spread) >=
                                    minimumExtent - 1
                            )
                        );
                    };
                    const edgeHasMaterialPaint = style =>
                        ['Left', 'Right', 'Top', 'Bottom'].some(side =>
                            materialBorderWidth(style, side) > 0
                        ) || materialOutline(style).width > 0;
                    const svgHasMaterialPaint = origin => origin.matches('svg') &&
                        [...origin.querySelectorAll('*')].some(descendant => {
                            const style = getComputedStyle(descendant);
                            const opacity = Number.parseFloat(style.opacity || '1');
                            const fillOpacity = Number.parseFloat(
                                style.fillOpacity || '1'
                            );
                            const strokeOpacity = Number.parseFloat(
                                style.strokeOpacity || '1'
                            );
                            return Number.isFinite(opacity) && opacity > 0.01 && (
                                Number.isFinite(fillOpacity) && fillOpacity > 0.01 &&
                                    colorAlpha(style.fill) > 0.01 ||
                                Number.isFinite(strokeOpacity) && strokeOpacity > 0.01 &&
                                    colorAlpha(style.stroke) > 0.01
                            );
                        });
                    const hasMaterialPaint = (origin, style, pseudo = false) => {
                        const opacity = Number.parseFloat(style.opacity || '1');
                        return Number.isFinite(opacity) && opacity > 0.01 && (
                            colorAlpha(style.backgroundColor) > 0.01 ||
                            imageHasMaterialPaint(style.backgroundImage) ||
                            shadowHasMaterialPaint(origin, style, pseudo) ||
                            edgeHasMaterialPaint(style) ||
                            (!pseudo && (
                                origin.matches('img, video, canvas') ||
                                svgHasMaterialPaint(origin)
                            ))
                        );
                    };
                    const containsPoint = (rect, [x, y]) =>
                        rect && rect.right > rect.left && rect.bottom > rect.top &&
                        x >= rect.left && x <= rect.right &&
                        y >= rect.top && y <= rect.bottom;
                    const expandedRect = (rect, left, right, top, bottom) => ({
                        left: rect.left - left,
                        right: rect.right + right,
                        top: rect.top - top,
                        bottom: rect.bottom + bottom,
                    });
                    const materialPaintCoverage = (origin, style, pseudo) => {
                        const rect = paintRect(origin, style, pseudo);
                        const shadows = shadowLayers(style);
                        const minimumExtent = Math.max(
                            1,
                            Math.min(
                                Math.max(0, rect.width),
                                Math.max(0, rect.height)
                            ) / 2
                        );
                        const insetShadowFills = shadows.some(layer =>
                            layer.material && layer.inset &&
                            layer.blur + Math.max(0, layer.spread) >=
                                minimumExtent - 1
                        );
                        const baseFills = colorAlpha(style.backgroundColor) > 0.01 ||
                            imageHasMaterialPaint(style.backgroundImage) ||
                            insetShadowFills ||
                            (!pseudo && (
                                origin.matches('img, video, canvas') ||
                                svgHasMaterialPaint(origin)
                            ));
                        const borders = {
                            left: materialBorderWidth(style, 'Left'),
                            right: materialBorderWidth(style, 'Right'),
                            top: materialBorderWidth(style, 'Top'),
                            bottom: materialBorderWidth(style, 'Bottom'),
                        };
                        const borderFills = rect.width > 1 && rect.height > 1 && (
                            borders.left + borders.right >= rect.width - 1 ||
                            borders.top + borders.bottom >= rect.height - 1
                        );
                        const borderInner = {
                            left: rect.left + borders.left,
                            right: rect.right - borders.right,
                            top: rect.top + borders.top,
                            bottom: rect.bottom - borders.bottom,
                        };
                        const outline = materialOutline(style);
                        const outlineInset = Math.max(0, -outline.offset);
                        const outlineFills = rect.width > 1 && rect.height > 1 &&
                            outline.width > 0 &&
                            outlineInset >= Math.min(rect.width, rect.height) / 2 - 1 &&
                            outlineInset - outline.width <= 1;
                        const outlineInner = expandedRect(
                            rect,
                            outline.offset,
                            outline.offset,
                            outline.offset,
                            outline.offset
                        );
                        const outlineOuter = expandedRect(
                            outlineInner,
                            outline.width,
                            outline.width,
                            outline.width,
                            outline.width
                        );
                        const outerShadows = shadows.filter(layer =>
                            layer.material && !layer.inset
                        );
                        return new Set(points.flatMap((point, index) => {
                            const inBase = containsPoint(rect, point);
                            const inBorder = containsPoint(rect, point) &&
                                !containsPoint(borderInner, point);
                            const inOutline = outline.width > 0 &&
                                containsPoint(outlineOuter, point) &&
                                !containsPoint(outlineInner, point);
                            const inOuterShadow = outerShadows.some(layer => {
                                const extent = Math.max(
                                    0,
                                    layer.spread + layer.blur * 2
                                );
                                const shadowRect = expandedRect(
                                    {
                                        left: rect.left + layer.offsetX,
                                        right: rect.right + layer.offsetX,
                                        top: rect.top + layer.offsetY,
                                        bottom: rect.bottom + layer.offsetY,
                                    },
                                    extent,
                                    extent,
                                    extent,
                                    extent
                                );
                                return containsPoint(shadowRect, point) && !inBase;
                            });
                            return baseFills && inBase ||
                                borderFills && inBase ||
                                outlineFills && inBase ||
                                inBorder || inOutline || inOuterShadow
                                ? [index]
                                : [];
                        }));
                    };
                    const paintVisible = origin => {
                        let opacity = 1;
                        for (let current = origin;
                            current instanceof Element;
                            current = current.parentElement) {
                            const style = getComputedStyle(current);
                            const currentOpacity = Number.parseFloat(style.opacity || '1');
                            if (style.display === 'none' || style.visibility !== 'visible' ||
                                style.contentVisibility === 'hidden' ||
                                !Number.isFinite(currentOpacity)) return false;
                            opacity *= currentOpacity;
                        }
                        return opacity > 0.01;
                    };
                    if (materialPaintCandidates === null) {
                        const real = [];
                        const pseudo = [];
                        for (const origin of document.querySelectorAll('*')) {
                            if (!paintVisible(origin)) continue;
                            const style = getComputedStyle(origin);
                            if (style.pointerEvents === 'none' &&
                                hasMaterialPaint(origin, style)) real.push(origin);
                            for (const pseudoName of ['::before', '::after']) {
                                const pseudoStyle = getComputedStyle(
                                    origin, pseudoName
                                );
                                if (pseudoStyle.pointerEvents !== 'none' ||
                                    ['none', 'normal'].includes(pseudoStyle.content) ||
                                    !hasMaterialPaint(
                                        origin, pseudoStyle, true
                                    )) continue;
                                pseudo.push([origin, pseudoName]);
                            }
                        }
                        materialPaintCandidates = {real, pseudo};
                    }
                    const realCandidates = materialPaintCandidates.real.flatMap(origin => {
                        const style = getComputedStyle(origin);
                        const coverage = materialPaintCoverage(origin, style, false);
                        return coverage.size > 0
                            ? [{origin, coverage}]
                            : [];
                    });
                    const pseudoCandidates = materialPaintCandidates.pseudo.flatMap(
                        ([origin, pseudo]) => {
                            const style = getComputedStyle(origin, pseudo);
                            const coverage = materialPaintCoverage(
                                origin, style, true
                            );
                            return coverage.size > 0
                                ? [{origin, pseudo, coverage}]
                                : [];
                        }
                    );
                    if (realCandidates.length === 0 && pseudoCandidates.length === 0) {
                        return true;
                    }
                    const attributeOriginals = [];
                    const inlineStyleOriginals = [];
                    const rememberedInlineStyles = new Set();
                    const rememberInlineStyle = candidate => {
                        if (rememberedInlineStyles.has(candidate)) return;
                        rememberedInlineStyles.add(candidate);
                        inlineStyleOriginals.push([
                            candidate,
                            candidate.hasAttribute('style'),
                            candidate.getAttribute('style'),
                        ]);
                    };
                    const restoreInlineStyle = candidate => {
                        const original = inlineStyleOriginals.find(
                            ([element]) => element === candidate
                        );
                        if (!original) return;
                        const [, hadStyle, value] = original;
                        if (hadStyle) candidate.setAttribute('style', value);
                        else candidate.removeAttribute('style');
                    };
                    const forceInlinePointerEvents = (candidate, value) => {
                        rememberInlineStyle(candidate);
                        const rawStyle = candidate.getAttribute('style') || '';
                        const separator = rawStyle.trim() &&
                            !rawStyle.trimEnd().endsWith(';') ? ';' : '';
                        candidate.setAttribute(
                            'style',
                            `${rawStyle}${separator}pointer-events:${value}!important;`
                        );
                    };
                    const forceInlineProbeGeometry = candidate => {
                        rememberInlineStyle(candidate);
                        const rawStyle = candidate.getAttribute('style') || '';
                        const separator = rawStyle.trim() &&
                            !rawStyle.trimEnd().endsWith(';') ? ';' : '';
                        candidate.setAttribute(
                            'style',
                            `${rawStyle}${separator}` +
                            'pointer-events:auto!important;' +
                            'position:fixed!important;inset:0!important;' +
                            'width:auto!important;height:auto!important;' +
                            'margin:0!important;transform:none!important;' +
                            'box-sizing:border-box!important;border:0!important;' +
                            'outline:0!important;box-shadow:none!important;' +
                            'clip:auto!important;clip-path:none!important;'
                        );
                    };
                    let probeStyle = null;
                    try {
                        const pseudoOrigins = new Set();
                        const pseudoAttributes = [];
                        const pseudoProbes = [];
                        for (const candidate of pseudoCandidates) {
                            const {origin, pseudo} = candidate;
                            const attribute = pseudo === '::before'
                                ? 'data-srcc-pointer-probe-before'
                                : 'data-srcc-pointer-probe-after';
                            attributeOriginals.push([
                                origin,
                                attribute,
                                origin.hasAttribute(attribute),
                                origin.getAttribute(attribute),
                            ]);
                            pseudoAttributes.push([origin, attribute]);
                            pseudoProbes.push([candidate, origin, attribute]);
                            origin.setAttribute(attribute, 'suppressed');
                            if (!pseudoOrigins.has(origin)) {
                                pseudoOrigins.add(origin);
                                forceInlinePointerEvents(origin, 'none');
                            }
                        }
                        if (realCandidates.length > 0 || pseudoCandidates.length > 0) {
                            const boosted = (attribute, value) => Array.from(
                                {length: 8},
                                (_, index) => `:is(
                                    #srcc-pointer-probe-${index},
                                    [${attribute}="${value}"]
                                )`
                            ).join('');
                            probeStyle = document.createElement('style');
                            probeStyle.textContent = `
                                @layer srccPointerPaintProbe {
                                    ${boosted('data-srcc-pointer-probe-real', 'active')} {
                                        pointer-events: auto !important;
                                    }
                                    ${boosted('data-srcc-pointer-probe-before', 'suppressed')},
                                    ${boosted('data-srcc-pointer-probe-after', 'suppressed')},
                                    ${boosted('data-srcc-pointer-probe-before', 'active')},
                                    ${boosted('data-srcc-pointer-probe-after', 'active')} {
                                        pointer-events: none !important;
                                    }
                                    ${boosted('data-srcc-pointer-probe-before', 'active')}::before,
                                    ${boosted('data-srcc-pointer-probe-after', 'active')}::after {
                                        pointer-events: auto !important;
                                        position: fixed !important;
                                        inset: 0 !important;
                                        width: auto !important;
                                        height: auto !important;
                                        margin: 0 !important;
                                        transform: none !important;
                                        box-sizing: border-box !important;
                                        border: 0 !important;
                                        outline: 0 !important;
                                        box-shadow: none !important;
                                        clip: auto !important;
                                        clip-path: none !important;
                                    }
                                }
                            `;
                            document.head.insertBefore(
                                probeStyle, document.head.firstChild
                            );
                        }
                        const suppressedHits = pointHits();
                        const confirmedPseudoCandidates = new Set();
                        for (const [candidate, origin, attribute] of pseudoProbes) {
                            origin.setAttribute(attribute, 'active');
                            const candidateHits = pointHits();
                            if ([...candidate.coverage].some(index =>
                                candidateHits[index] === candidate.origin &&
                                candidateHits[index] !== suppressedHits[index]
                            )) confirmedPseudoCandidates.add(candidate);
                            origin.setAttribute(attribute, 'suppressed');
                        }
                        const pseudoCovered = points.map((_, index) =>
                            pseudoCandidates.some(candidate =>
                                confirmedPseudoCandidates.has(candidate) &&
                                candidate.coverage.has(index)
                            )
                        );
                        for (const [origin, attribute] of pseudoAttributes) {
                            origin.setAttribute(attribute, 'inactive');
                        }
                        for (const origin of pseudoOrigins) restoreInlineStyle(origin);
                        const confirmedRealCandidates = new Set();
                        for (const candidate of realCandidates) {
                            const {origin} = candidate;
                            const attribute = 'data-srcc-pointer-probe-real';
                            attributeOriginals.push([
                                origin,
                                attribute,
                                origin.hasAttribute(attribute),
                                origin.getAttribute(attribute),
                            ]);
                            origin.setAttribute(attribute, 'active');
                            forceInlineProbeGeometry(origin);
                            const candidateHits = pointHits();
                            if ([...candidate.coverage].some(index =>
                                candidateHits[index] &&
                                (candidateHits[index] === origin ||
                                    origin.matches('svg') &&
                                    origin.contains(candidateHits[index])) &&
                                candidateHits[index] !== ordinaryHits[index]
                            )) confirmedRealCandidates.add(candidate);
                            restoreInlineStyle(origin);
                            origin.setAttribute(attribute, 'inactive');
                        }
                        const realCovered = points.map((_, index) =>
                            realCandidates.some(candidate =>
                                confirmedRealCandidates.has(candidate) &&
                                candidate.coverage.has(index)
                            )
                        );
                        const visibleEvidenceCount = evidenceIndexes.filter(index =>
                            !pseudoCovered[index] &&
                            !realCovered[index] &&
                            isRelatedHit(ordinaryHits[index])
                        ).length;
                        return visibleEvidenceCount * 2 > evidenceIndexes.length;
                    } finally {
                        probeStyle?.remove();
                        for (const [origin, attribute, hadAttribute, value] of
                            attributeOriginals.reverse()) {
                            if (hadAttribute) origin.setAttribute(attribute, value);
                            else origin.removeAttribute(attribute);
                        }
                        for (const [candidate, hadStyle, value] of
                            inlineStyleOriginals.reverse()) {
                            if (hadStyle) candidate.setAttribute('style', value);
                            else candidate.removeAttribute('style');
                        }
                    }
                };
                if (hitTestEligible) return strictCurrentHitTest();
                const scrollPositions = [];
                const remembered = new Set();
                const remember = element => {
                    if (!(element instanceof Element) || remembered.has(element)) return;
                    remembered.add(element);
                    scrollPositions.push([element, element.scrollLeft, element.scrollTop]);
                };
                for (let current = node.parentElement;
                    current instanceof Element;
                    current = current.parentElement) remember(current);
                remember(scrollingElement);
                const originalWindowScroll = [window.scrollX, window.scrollY];
                try {
                    for (let current = node.parentElement;
                        current instanceof Element;
                        current = current.parentElement) {
                        const style = getComputedStyle(current);
                        const targetRect = node.getBoundingClientRect();
                        const ancestorRect = current.getBoundingClientRect();
                        const ancestorLeft = ancestorRect.left + current.clientLeft;
                        const ancestorRight = ancestorLeft + current.clientWidth;
                        const ancestorTop = ancestorRect.top + current.clientTop;
                        const ancestorBottom = ancestorTop + current.clientHeight;
                        if (['auto', 'scroll'].includes(style.overflowX) &&
                            current.scrollWidth > current.clientWidth + 1) {
                            if (targetRect.left < ancestorLeft) {
                                current.scrollLeft += targetRect.left - ancestorLeft;
                            } else if (targetRect.right > ancestorRight) {
                                current.scrollLeft += targetRect.right - ancestorRight;
                            }
                        }
                        if (['auto', 'scroll'].includes(style.overflowY) &&
                            current.scrollHeight > current.clientHeight + 1) {
                            if (targetRect.top < ancestorTop) {
                                current.scrollTop += targetRect.top - ancestorTop;
                            } else if (targetRect.bottom > ancestorBottom) {
                                current.scrollTop += targetRect.bottom - ancestorBottom;
                            }
                        }
                    }
                    const targetRect = node.getBoundingClientRect();
                    if (targetRect.left < 0) {
                        scrollingElement.scrollLeft += targetRect.left;
                    } else if (targetRect.right > window.innerWidth) {
                        scrollingElement.scrollLeft += targetRect.right - window.innerWidth;
                    }
                    if (targetRect.top < 0) {
                        scrollingElement.scrollTop += targetRect.top;
                    } else if (targetRect.bottom > window.innerHeight) {
                        scrollingElement.scrollTop += targetRect.bottom - window.innerHeight;
                    }
                    return strictCurrentHitTest();
                } finally {
                    for (const [element, scrollLeft, scrollTop] of
                        [...scrollPositions].reverse()) {
                        element.scrollLeft = scrollLeft;
                        element.scrollTop = scrollTop;
                    }
                    window.scrollTo({
                        left: originalWindowScroll[0],
                        top: originalWindowScroll[1],
                        behavior: 'instant',
                    });
                }
            };
            const color = value => {
                const values = String(value || '').match(/[0-9.]+/g) || [];
                if (values.length < 3) return null;
                const parsed = values.slice(0, 4).map(Number);
                if (parsed.some(item => !Number.isFinite(item))) return null;
                return [parsed[0], parsed[1], parsed[2], parsed.length > 3 ? parsed[3] : 1];
            };
            const background = node => {
                for (let current = node; current instanceof Element; current = current.parentElement) {
                    const parsed = color(getComputedStyle(current).backgroundColor);
                    if (parsed && parsed[3] >= 0.99) return parsed;
                }
                return [255, 255, 255, 1];
            };
            const channel = value => {
                const normalized = value / 255;
                return normalized <= 0.04045
                    ? normalized / 12.92
                    : Math.pow((normalized + 0.055) / 1.055, 2.4);
            };
            const luminance = parsed => 0.2126 * channel(parsed[0]) +
                0.7152 * channel(parsed[1]) + 0.0722 * channel(parsed[2]);
            const contrastRatio = (left, right) => {
                if (!left || !right) return 0;
                const foreground = left[3] < 1
                    ? [
                        left[0] * left[3] + right[0] * (1 - left[3]),
                        left[1] * left[3] + right[1] * (1 - left[3]),
                        left[2] * left[3] + right[2] * (1 - left[3]),
                        1,
                    ]
                    : left;
                const first = luminance(foreground);
                const second = luminance(right);
                return (Math.max(first, second) + 0.05) / (Math.min(first, second) + 0.05);
            };
            const hasDirectText = node => [...node.childNodes].some(
                child => child.nodeType === Node.TEXT_NODE && String(child.textContent || '').trim()
            );
            const minimumTextContrast = root => {
                if (!root || !visible(root)) return -1;
                const ratios = [root, ...root.querySelectorAll('*')]
                    .filter(node => visible(node) && (hasDirectText(node) || node.matches('a')) && String(node.innerText || '').trim())
                    .map(node => contrastRatio(color(getComputedStyle(node).color), background(node)))
                    .filter(value => Number.isFinite(value) && value > 0);
                return ratios.length ? Math.min(...ratios) : -1;
            };
            const minimumBoundaryContrast = root => {
                if (!root || !visible(root)) {
                    return {ratio: -1, sample: {kind: 'missing-or-hidden-root'}};
                }
                const ratios = [];
                for (const grid of root.querySelectorAll('.srcc-one-pager-grid')) {
                    if (!visible(grid)) continue;
                    const gridColor = color(getComputedStyle(grid).backgroundColor);
                    for (const child of grid.children) {
                        if (!visible(child)) continue;
                        const childBackground = background(child);
                        ratios.push({
                            ratio: contrastRatio(gridColor, childBackground),
                            kind: 'grid-separator',
                            tag: child.tagName,
                            class_name: String(child.className || ''),
                            boundary: gridColor,
                            adjacent: childBackground,
                        });
                    }
                }
                for (const node of [root, ...root.querySelectorAll('*')]) {
                    if (!visible(node)) continue;
                    const style = getComputedStyle(node);
                    const adjacent = background(node);
                    for (const side of ['Top', 'Right', 'Bottom', 'Left']) {
                        if (Number.parseFloat(style[`border${side}Width`] || '0') < 1 ||
                            ['none', 'hidden'].includes(style[`border${side}Style`])) continue;
                        const boundary = color(style[`border${side}Color`]);
                        if (boundary && boundary[3] > 0.01) {
                            ratios.push({
                                ratio: contrastRatio(boundary, adjacent),
                                kind: `border-${side.toLowerCase()}`,
                                tag: node.tagName,
                                class_name: String(node.className || ''),
                                role: String(node.dataset?.stateRole || ''),
                                boundary,
                                adjacent,
                            });
                        }
                    }
                }
                const usable = ratios
                    .filter(item => Number.isFinite(item.ratio) && item.ratio > 0)
                    .sort((left, right) => left.ratio - right.ratio);
                return usable.length
                    ? {ratio: usable[0].ratio, sample: usable[0]}
                    : {ratio: -1, sample: {kind: 'no-boundaries'}};
            };
            const summaryTitle = onePager?.querySelector(':scope > header > h2, :scope > header > h3, :scope > header > h4, :scope > header > h5, :scope > header > h6');
            const sections = onePager
                ? [...onePager.children].filter(node =>
                    node.matches('section, aside') &&
                    node.querySelector(':scope > h2, :scope > h3, :scope > h4, :scope > h5, :scope > h6')
                )
                : [];
            const headings = [
                ...(summaryTitle ? [summaryTitle] : []),
                ...sections.map(node => node.querySelector(':scope > h2, :scope > h3, :scope > h4, :scope > h5, :scope > h6')),
            ].filter(Boolean);
            const stateNodes = onePager ? [...onePager.querySelectorAll('[data-state]')] : [];
            const stateRoleNodes = onePager
                ? [...onePager.querySelectorAll('[data-state][data-state-role]')]
                : [];
            const visibleStateRoleNodes = stateRoleNodes.filter(node => {
                const stateText = node.querySelector('.srcc-state');
                return visible(node) && visible(stateText);
            });
            const stateRoles = stateRoleNodes
                .map(node => String(node.dataset.stateRole || '').trim().toLowerCase())
                .filter(Boolean);
            const scenarios = onePager
                ? [...onePager.querySelectorAll('[data-section="one-pager-scenarios"] > ol > li')]
                : [];
            const provenance = onePager?.querySelector('[data-section="one-pager-provenance"]');
            const provenanceCaption = provenance?.querySelector('caption');
            const provenanceRows = provenance
                ? [...provenance.querySelectorAll('tbody')].filter(visible)
                : [];
            const onePagerVisible = visible(onePager);
            const boundaryContrast = minimumBoundaryContrast(onePager);
            return {
                one_pager_visible: onePagerVisible,
                page_header_count: document.querySelectorAll('body > header').length,
                one_pager_header_count: onePager
                    ? onePager.querySelectorAll(':scope > header').length
                    : 0,
                one_pager_before_overview: Boolean(
                    onePager && overview &&
                    (onePager.compareDocumentPosition(overview) & Node.DOCUMENT_POSITION_FOLLOWING)
                ),
                one_pager_heading_count: headings.length,
                one_pager_section_count: sections.length,
                one_pager_answer_item_count: onePager
                    ? onePager.querySelectorAll('[data-section="one-pager-answers"] > ol > li').length
                    : 0,
                one_pager_scenario_item_count: scenarios.length,
                one_pager_state_tokens: onePager
                    ? visibleStateRoleNodes
                        .map(node => `${String(node.dataset.stateRole || '').trim().toLowerCase()}=${String(node.dataset.state || '').trim().toLowerCase()}`)
                        .filter(token => !token.startsWith('=') && !token.endsWith('='))
                        .sort()
                    : [],
                one_pager_share_basis_tokens: onePager
                    ? [...onePager.querySelectorAll('[data-share-basis-role][data-share-basis-state]')]
                        .filter(visible)
                        .map(node => `${String(node.dataset.shareBasisRole || '').trim().toLowerCase()}=${String(node.dataset.shareBasisState || '').trim().toLowerCase()}`)
                        .filter(token => !token.startsWith('=') && !token.endsWith('='))
                        .sort()
                    : [],
                one_pager_state_node_count: stateNodes.length,
                one_pager_state_role_count: stateRoleNodes.length,
                one_pager_unique_state_role_count: new Set(stateRoles).size,
                one_pager_provenance_caption_visible: onePagerVisible &&
                    visible(provenanceCaption),
                one_pager_min_text_contrast_ratio: minimumTextContrast(onePager),
                one_pager_min_boundary_contrast_ratio: boundaryContrast.ratio,
                one_pager_boundary_contrast_sample: JSON.stringify(boundaryContrast.sample),
                one_pager_overflow_px: onePager
                    ? Math.max(0, onePager.scrollWidth - onePager.clientWidth)
                    : -1,
                one_pager_max_descendant_overflow_px: onePager
                    ? Math.max(
                        0,
                        ...[...onePager.querySelectorAll('*')]
                            .filter(visible)
                            .map(node => Math.max(0, node.scrollWidth - node.clientWidth))
                    )
                    : -1,
                one_pager_provenance_visible: onePagerVisible &&
                    visible(provenanceCaption) && provenanceRows.length > 0,
                one_pager_blockers_visible: onePagerVisible && onePager
                    ? [...onePager.querySelectorAll('.srcc-blockers')].some(visible)
                    : false,
                one_pager_assumptions_visible: onePagerVisible &&
                    scenarios.length === 3 && scenarios.every(node => {
                    const state = node.querySelector('.srcc-state');
                    const assumption = node.querySelector(':scope > p');
                    return visible(node) && visible(state) && visible(assumption) &&
                        String(state.innerText || '').trim().length > 0 &&
                        String(assumption.innerText || '').trim().length > 0;
                }),
                one_pager_handoff_visible: onePagerVisible && visible(
                    onePager?.querySelector('[data-section="one-pager-handoff"]')
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


def _summary_forced_colors_cues(page) -> bool:
    summary = _summary_scope_observation(page)
    state_count = int(summary["one_pager_state_node_count"])
    if not (
        summary["one_pager_visible"] is True
        and summary["one_pager_provenance_visible"] is True
        and state_count > 0
        and state_count == int(summary["one_pager_state_role_count"])
        and state_count == len(summary["one_pager_state_tokens"])
    ):
        return False
    return bool(
        page.evaluate(
            r"""() => {
                const root = document.querySelector(
                    '[data-section="evidence-one-pager"]'
                );
                const colorAlpha = value => {
                    const normalized = String(value || '').trim().toLowerCase();
                    if (!normalized || ['none', 'transparent'].includes(normalized)) {
                        return 0;
                    }
                    const alphaValue = token => {
                        const trimmed = token.trim();
                        const parsed = Number.parseFloat(trimmed);
                        if (!Number.isFinite(parsed)) return 1;
                        return trimmed.endsWith('%') ? parsed / 100 : parsed;
                    };
                    const functional = normalized.match(
                        /^(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch|color)\((.*)\)$/
                    );
                    if (!functional) return 1;
                    const body = functional[1];
                    const slash = body.lastIndexOf('/');
                    if (slash >= 0) return alphaValue(body.slice(slash + 1));
                    if (body.includes(',')) {
                        const components = body.split(',');
                        return components.length === 4
                            ? alphaValue(components[3])
                            : 1;
                    }
                    return 1;
                };
                const hasOwnCue = node => {
                    if (!(node instanceof Element)) return false;
                    const style = getComputedStyle(node);
                    const outline = Number.parseFloat(
                        style.outlineWidth || '0'
                    ) >= 1 && !['none', 'hidden'].includes(style.outlineStyle) &&
                        colorAlpha(style.outlineColor) > 0.01;
                    const border = ['Top', 'Right', 'Bottom', 'Left'].some(side =>
                        Number.parseFloat(style[`border${side}Width`] || '0') >= 1 &&
                        !['none', 'hidden'].includes(
                            style[`border${side}Style`]
                        ) && colorAlpha(style[`border${side}Color`]) > 0.01
                    );
                    return outline || border;
                };
                if (!root) return false;
                const provenance = root.querySelector(
                    '[data-section="one-pager-provenance"]'
                );
                const states = [...root.querySelectorAll('[data-state]')];
                return states.length > 0 && states.every(node => {
                    const stateText = node.querySelector('.srcc-state');
                    return stateText instanceof Element &&
                        String(stateText.innerText || '').trim().length > 0 &&
                        hasOwnCue(stateText);
                }) && hasOwnCue(root) && hasOwnCue(provenance);
            }"""
        )
    )


def _browser_observation(
    page,
    *,
    state: str,
    viewport: str,
    requested_zoom: int,
    declared_width: int,
    declared_height: int,
    remote_requests: list[str],
    console_errors: list[str],
    page_errors: list[str],
) -> dict[str, object]:
    structural = page.evaluate(
        """() => { const all = [...document.querySelectorAll('*')]; const headings = [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')]; return { h1_count: document.querySelectorAll('h1').length, header_count: document.querySelectorAll('header').length, main_count: document.querySelectorAll('main').length, footer_count: document.querySelectorAll('footer').length, section_count: document.querySelectorAll('section').length, heading_levels: headings.map(node => Number(node.tagName.slice(1))), table_count: document.querySelectorAll('table').length, captioned_table_count: [...document.querySelectorAll('table')].filter(table => table.querySelector(':scope > caption')).length, csp: document.querySelector('meta[http-equiv="Content-Security-Policy"]')?.getAttribute('content') || '', script_count: document.querySelectorAll('script').length, event_handler_count: all.reduce((count, node) => count + [...node.attributes].filter(attr => attr.name.toLowerCase().startsWith('on')).length, 0), form_count: document.querySelectorAll('form').length, iframe_count: document.querySelectorAll('iframe').length, overflow_px: Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth) }; }"""
    )
    summary_screen = _summary_scope_observation(page)
    screenshot_bytes = page.screenshot(full_page=False, scale="device")
    if screenshot_bytes[:8] != b"\x89PNG\r\n\x1a\n" or len(screenshot_bytes) < 24:
        raise RuntimeError("HTML brief browser screenshot did not produce a PNG")
    screenshot_width = int.from_bytes(screenshot_bytes[16:20], "big")
    screenshot_height = int.from_bytes(screenshot_bytes[20:24], "big")
    zoom_evaluation = evaluate_html_brief_browser_zoom(
        requested_zoom=requested_zoom,
        declared_width=float(declared_width),
        declared_height=float(declared_height),
        screenshot_width=float(screenshot_width),
        screenshot_height=float(screenshot_height),
        inner_width=float(summary_screen["inner_width"]),
        inner_height=float(summary_screen["inner_height"]),
        visual_viewport_width=float(summary_screen["visual_viewport_width"]),
        visual_viewport_height=float(summary_screen["visual_viewport_height"]),
        device_pixel_ratio=float(summary_screen["device_pixel_ratio"]),
        visual_viewport_scale=float(summary_screen["visual_viewport_scale"]),
    )
    focus_before = _focus_cue_state(page)
    page.keyboard.press("Tab")
    rendered_focus = _visible(
        page, 'a[href="#research-brief-main"]', scroll_vertical=False
    )
    focus_after = _focus_cue_state(page)
    visible_focus = rendered_focus and _focus_cue_is_visible(
        page, before=focus_before, after=focus_after
    )
    page.keyboard.press("Enter")
    page.wait_for_timeout(25)
    skip_target_focused = bool(
        page.evaluate(
            "document.activeElement?.id === 'research-brief-main' && location.hash === '#research-brief-main'"
        )
    )
    boundary_selector = ".srcc-boundary, .boundary"
    blocker_selector = ".srcc-blockers, .blockers"
    provenance_selector = ".srcc-advanced-evidence, .advanced-evidence, [data-section='advanced-evidence']"
    boundary_visible, blockers_visible, provenance_visible = (
        _visible(page, boundary_selector),
        _visible(page, blocker_selector),
        _visible(page, provenance_selector),
    )
    forced_colors_non_color_cue = bool(
        _settle_media_css(
            page,
            media="screen",
            forced_colors="active",
            reduced_motion="no-preference",
            viewport=viewport,
            boundary_selector=boundary_selector,
            provenance_selector=provenance_selector,
            operation=lambda settled_page: settled_page.evaluate(
                """() => { const nodes = [document.querySelector('.srcc-boundary, .boundary'), document.querySelector('.srcc-state, .state')]; return nodes.every(node => { if (!node) return false; const style = getComputedStyle(node); return parseFloat(style.borderInlineStartWidth || '0') > 0 && style.borderInlineStartStyle !== 'none' && node.innerText.trim().length > 0; }); }"""
            ),
        )
    )
    one_pager_forced_colors_non_color_cue = bool(
        _settle_media_css(
            page,
            media="screen",
            forced_colors="active",
            reduced_motion="no-preference",
            viewport=viewport,
            boundary_selector='[data-section="evidence-one-pager"]',
            provenance_selector=(
                '[data-section="evidence-one-pager"] '
                '[data-section="one-pager-provenance"]'
            ),
            operation=_summary_forced_colors_cues,
        )
    )
    _settle_media_css(
        page,
        media="screen",
        forced_colors="none",
        reduced_motion="reduce",
        viewport=viewport,
        boundary_selector=boundary_selector,
        provenance_selector=provenance_selector,
    )
    reduced_motion_evidence = page.evaluate(
        """() => { const seconds = value => Math.max(...value.split(',').map(raw => { const text = raw.trim(); if (text.endsWith('ms')) return parseFloat(text) / 1000; if (text.endsWith('s')) return parseFloat(text); return 0; })); const offenders = [...document.querySelectorAll('*')].map(node => { const style = getComputedStyle(node); return {tag: node.tagName, class_name: node.className || '', animation: seconds(style.animationDuration), transition: seconds(style.transitionDuration), scroll: style.scrollBehavior}; }).filter(item => item.animation > 0.001 || item.transition > 0.001 || item.scroll === 'smooth'); const animations = document.getAnimations(); const longAnimations = animations.filter(animation => { const timing = animation.effect?.getComputedTiming?.() || {}; return !Number.isFinite(Number(timing.endTime)) || Number(timing.endTime) > 1; }); return { animation_count: animations.length, long_animation_count: longAnimations.length, animation_sample: animations.slice(0, 3).map(animation => { const timing = animation.effect?.getComputedTiming?.() || {}; return {play_state: animation.playState, current_time: animation.currentTime, target: animation.effect?.target?.tagName || '', target_class: animation.effect?.target?.className || '', duration: timing.duration, end_time: timing.endTime}; }), offenders: offenders.slice(0, 12) }; }"""
    )
    reduced_motion_static = bool(
        reduced_motion_evidence["long_animation_count"] == 0
        and not reduced_motion_evidence["offenders"]
    )
    (
        print_boundary_visible,
        print_provenance_visible,
        summary_print,
        pdf_bytes,
    ) = _settle_media_css(
        page,
        media="print",
        forced_colors="none",
        reduced_motion="reduce",
        viewport=viewport,
        boundary_selector=boundary_selector,
        provenance_selector=provenance_selector,
        operation=lambda settled_page: (
            _visible(settled_page, boundary_selector),
            _visible(settled_page, provenance_selector),
            _summary_scope_observation(settled_page),
            settled_page.pdf(),
        ),
    )
    return {
        "state": state,
        "viewport": viewport,
        "requested_zoom": requested_zoom,
        "actual_browser_zoom": zoom_evaluation.passed,
        "actual_browser_zoom_evidence": zoom_evaluation.evidence,
        "h1_count": int(structural["h1_count"]),
        "header_count": int(structural["header_count"]),
        "page_header_count": int(summary_screen["page_header_count"]),
        "one_pager_header_count": int(summary_screen["one_pager_header_count"]),
        "main_count": int(structural["main_count"]),
        "footer_count": int(structural["footer_count"]),
        "section_count": int(structural["section_count"]),
        "heading_levels": tuple(int(level) for level in structural["heading_levels"]),
        "skip_target_focused": skip_target_focused,
        "visible_focus": visible_focus,
        "table_count": int(structural["table_count"]),
        "captioned_table_count": int(structural["captioned_table_count"]),
        "csp": str(structural["csp"]),
        "script_count": int(structural["script_count"]),
        "event_handler_count": int(structural["event_handler_count"]),
        "form_count": int(structural["form_count"]),
        "iframe_count": int(structural["iframe_count"]),
        "remote_request_count": len(remote_requests),
        "boundary_visible": boundary_visible,
        "blockers_visible": blockers_visible,
        "provenance_visible": provenance_visible,
        "overflow_px": float(structural["overflow_px"]),
        "forced_colors_non_color_cue": forced_colors_non_color_cue,
        "reduced_motion_static": reduced_motion_static,
        "reduced_motion_evidence": repr(reduced_motion_evidence),
        "print_boundary_visible": print_boundary_visible,
        "print_provenance_visible": print_provenance_visible,
        "console_errors": tuple(console_errors),
        "page_errors": tuple(page_errors),
        "pdf_byte_length": len(pdf_bytes),
        "pdf_header": pdf_bytes[:4].decode("ascii", errors="replace"),
        "one_pager_visible": bool(summary_screen["one_pager_visible"]),
        "one_pager_before_overview": bool(
            summary_screen["one_pager_before_overview"]
        ),
        "one_pager_heading_count": int(summary_screen["one_pager_heading_count"]),
        "one_pager_section_count": int(summary_screen["one_pager_section_count"]),
        "one_pager_answer_item_count": int(
            summary_screen["one_pager_answer_item_count"]
        ),
        "one_pager_scenario_item_count": int(
            summary_screen["one_pager_scenario_item_count"]
        ),
        "one_pager_state_tokens": tuple(summary_screen["one_pager_state_tokens"]),
        "one_pager_share_basis_tokens": tuple(
            summary_screen["one_pager_share_basis_tokens"]
        ),
        "one_pager_state_node_count": int(
            summary_screen["one_pager_state_node_count"]
        ),
        "one_pager_state_role_count": int(
            summary_screen["one_pager_state_role_count"]
        ),
        "one_pager_unique_state_role_count": int(
            summary_screen["one_pager_unique_state_role_count"]
        ),
        "one_pager_provenance_caption_visible": bool(
            summary_screen["one_pager_provenance_caption_visible"]
        ),
        "one_pager_min_text_contrast_ratio": float(
            summary_screen["one_pager_min_text_contrast_ratio"]
        ),
        "one_pager_min_boundary_contrast_ratio": float(
            summary_screen["one_pager_min_boundary_contrast_ratio"]
        ),
        "one_pager_boundary_contrast_evidence": (
            f"minimum={summary_screen['one_pager_min_boundary_contrast_ratio']!r}; "
            f"sample={summary_screen['one_pager_boundary_contrast_sample']}"
        ),
        "one_pager_overflow_px": float(summary_screen["one_pager_overflow_px"]),
        "one_pager_max_descendant_overflow_px": float(
            summary_screen["one_pager_max_descendant_overflow_px"]
        ),
        "one_pager_provenance_visible": bool(
            summary_screen["one_pager_provenance_visible"]
        ),
        "one_pager_blockers_visible": bool(
            summary_screen["one_pager_blockers_visible"]
        ),
        "one_pager_assumptions_visible": bool(
            summary_screen["one_pager_assumptions_visible"]
        ),
        "one_pager_handoff_visible": bool(
            summary_screen["one_pager_handoff_visible"]
        ),
        "one_pager_forced_colors_non_color_cue": (
            one_pager_forced_colors_non_color_cue
        ),
        "one_pager_print_min_text_contrast_ratio": float(
            summary_print["one_pager_min_text_contrast_ratio"]
        ),
        "one_pager_print_min_boundary_contrast_ratio": float(
            summary_print["one_pager_min_boundary_contrast_ratio"]
        ),
        "one_pager_print_boundary_contrast_evidence": (
            f"minimum={summary_print['one_pager_min_boundary_contrast_ratio']!r}; "
            f"sample={summary_print['one_pager_boundary_contrast_sample']}"
        ),
        "one_pager_print_provenance_visible": bool(
            summary_print["one_pager_provenance_visible"]
        ),
        "one_pager_print_blockers_visible": bool(
            summary_print["one_pager_blockers_visible"]
        ),
        "one_pager_print_assumptions_visible": bool(
            summary_print["one_pager_assumptions_visible"]
        ),
        "one_pager_print_handoff_visible": bool(
            summary_print["one_pager_handoff_visible"]
        ),
    }


def run_company_workbench_html_browser_gate(
    cases: Mapping[str, bytes],
    *,
    repo_root: Path,
    chrome_executable: Path | None = None,
    cells: tuple[tuple[int, int, int], ...] = HTML_BRIEF_BROWSER_CELLS,
) -> tuple[HtmlBriefBrowserResult, ...]:
    """Run the browser matrix on exact injected bytes and prove the repository was unchanged."""
    if not cases:
        raise ValueError("At least one injected HTML document is required")
    if not cells:
        raise ValueError("At least one HTML brief browser cell is required")
    normalized_cells: list[tuple[int, int, int]] = []
    for cell in cells:
        if (
            type(cell) is not tuple
            or len(cell) != 3
            or any(type(value) is not int for value in cell)
        ):
            raise TypeError("HTML brief browser cells must be (width, height, zoom) tuples")
        if cell not in HTML_BRIEF_BROWSER_CELLS:
            raise ValueError(f"Unsupported HTML brief browser cell: {cell!r}")
        normalized_cells.append(cell)
    if len(set(normalized_cells)) != len(normalized_cells):
        raise ValueError("HTML brief browser cells must be unique")
    normalized_cases: dict[str, bytes] = {}
    for state, document_bytes in cases.items():
        if type(state) is not str or type(document_bytes) is not bytes:
            raise TypeError("Browser gate cases must map string states to exact bytes")
        document = document_bytes.decode("utf-8", errors="strict")
        if document.encode("utf-8") != document_bytes:
            raise ValueError("Injected HTML failed the strict UTF-8 byte roundtrip")
        normalized_cases[state] = document_bytes
    root = Path(repo_root).resolve()
    before = repository_fingerprint(root)
    results: list[HtmlBriefBrowserResult] = []
    try:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:  # pragma: no cover - environment contract
            raise RuntimeError(
                "Playwright is required for the HTML research brief browser gate"
            ) from exc
        with _injected_brief_server(normalized_cases) as active_origin:
            host = str(urlsplit(active_origin).hostname or "")
            if host != "127.0.0.1":
                raise RuntimeError(
                    f"Injected HTML browser server is not exact loopback: {active_origin!r}"
                )
            with sync_playwright() as playwright:
                executable = (
                    Path(chrome_executable)
                    if chrome_executable is not None
                    else find_chrome_executable()
                )
                if executable is None:
                    reported = Path(playwright.chromium.executable_path)
                    executable = (
                        reported
                        if reported.is_file() and os.access(reported, os.X_OK)
                        else None
                    )
                if (
                    executable is None
                    or not executable.is_file()
                    or not os.access(executable, os.X_OK)
                ):
                    raise RuntimeError(
                        "No executable Chrome-compatible browser is available"
                    )
                for state in normalized_cases:
                    for width, height, zoom in normalized_cells:
                        viewport = f"{width}x{height}"
                        remote_requests: list[str] = []
                        request_audit: list[str] = []
                        console_errors: list[str] = []
                        page_errors: list[str] = []
                        with tempfile.TemporaryDirectory(
                            prefix="stock-company-workbench-html-zoom-",
                            dir="/tmp",
                        ) as profile_directory:
                            profile = Path(profile_directory)
                            preferences = profile / "Default" / "Preferences"
                            preferences.parent.mkdir(parents=True)
                            preferences.write_text(
                                json.dumps(
                                    _chromium_zoom_preferences(host=host, zoom=zoom),
                                    sort_keys=True,
                                ),
                                encoding="utf-8",
                            )
                            context = playwright.chromium.launch_persistent_context(
                                user_data_dir=profile,
                                executable_path=str(executable),
                                headless=True,
                                viewport={"width": width, "height": height},
                                screen={"width": width, "height": height},
                            )
                            try:
                                page = (
                                    context.pages[0]
                                    if context.pages
                                    else context.new_page()
                                )

                                def intercept(route, request):
                                    request_url = str(request.url)
                                    action, external = evaluate_html_brief_request_origin(
                                        request_url=request_url,
                                        active_origin=active_origin,
                                    )
                                    request_audit.append(request_url)
                                    if external:
                                        remote_requests.append(request_url)
                                    if action == "abort":
                                        route.abort()
                                    else:
                                        route.continue_()

                                page.route("**/*", intercept)
                                page.on(
                                    "console",
                                    lambda message: (
                                        console_errors.append(message.text)
                                        if message.type == "error"
                                        else None
                                    ),
                                )
                                page.on(
                                    "pageerror",
                                    lambda error: page_errors.append(str(error)),
                                )
                                page.goto(
                                    f"{active_origin}/{quote(state, safe='')}.html",
                                    wait_until="load",
                                    timeout=30_000,
                                )
                                observation = _browser_observation(
                                    page,
                                    state=state,
                                    viewport=viewport,
                                    requested_zoom=zoom,
                                    declared_width=width,
                                    declared_height=height,
                                    remote_requests=remote_requests,
                                    console_errors=console_errors,
                                    page_errors=page_errors,
                                )
                                observation["request_audit"] = tuple(request_audit)
                                results.append(
                                    evaluate_html_brief_observation(observation)
                                )
                            finally:
                                context.close()
    finally:
        after = repository_fingerprint(root)
        if after != before:
            raise RuntimeError(
                "HTML research brief browser gate changed the repository fingerprint"
            )
    return tuple(results)
