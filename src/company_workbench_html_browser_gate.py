"""Fail-closed, no-write browser checks for injected offline research-brief bytes."""

from __future__ import annotations

import hashlib
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from src.public_performance_gate import find_chrome_executable


EXACT_HTML_BRIEF_CSP = (
    "default-src 'none'; script-src 'none'; connect-src 'none'; img-src 'none'; "
    "style-src 'unsafe-inline'; font-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'"
)

REQUIRED_OBSERVATION_KEYS = (
    "state",
    "viewport",
    "h1_count",
    "header_count",
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
)

_OBSERVATION_TYPES: Mapping[str, object] = {
    "state": str,
    "viewport": str,
    "h1_count": int,
    "header_count": int,
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
}


@dataclass(frozen=True)
class HtmlBriefBrowserAssertion:
    name: str
    passed: bool
    evidence: str


@dataclass(frozen=True)
class HtmlBriefBrowserResult:
    state: str
    viewport: str
    assertions: tuple[HtmlBriefBrowserAssertion, ...]

    @property
    def passed(self) -> bool:
        return bool(self.assertions) and all(
            assertion.passed for assertion in self.assertions
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
                ("header_count", "main_count", "footer_count", "section_count"),
                lambda: (
                    value("header_count")
                    == value("main_count")
                    == value("footer_count")
                    == 1
                    and value("section_count") >= 1
                ),
            ),
            "header/main/footer must each occur once and at least one section must exist",
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
            f"static={observation.get('reduced_motion_static')!r}",
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
    )
    state = observation.get("state") if valid["state"] else "<invalid>"
    viewport = observation.get("viewport") if valid["viewport"] else "<invalid>"
    return HtmlBriefBrowserResult(state, viewport, assertions)


def repository_fingerprint(repo_root: Path) -> str:
    """Hash every tracked and visible untracked path, type, and byte payload."""
    root = Path(repo_root).resolve()
    listed = subprocess.check_output(
        ["git", "ls-files", "-co", "--exclude-standard", "-z"], cwd=root
    )
    relative_paths = sorted(set(path for path in listed.split(b"\0") if path))
    digest = hashlib.sha256()
    for relative_bytes in relative_paths:
        path = root / os.fsdecode(relative_bytes)
        if path.is_symlink():
            kind, payload = b"symlink", os.fsencode(os.readlink(path))
        elif path.is_file():
            kind, payload = b"file", path.read_bytes()
        elif path.is_dir():
            kind, payload = b"directory", b""
        else:
            kind, payload = b"missing", b""
        for field in (relative_bytes, kind, payload):
            digest.update(len(field).to_bytes(8, "big"))
            digest.update(field)
    return digest.hexdigest()


def _visible(page, selector: str) -> bool:
    return bool(
        page.evaluate(
            """selector => { const node = document.querySelector(selector); if (!node) return false; const style = getComputedStyle(node); const rect = node.getBoundingClientRect(); return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0; }""",
            selector,
        )
    )


def _browser_observation(
    page,
    *,
    state: str,
    viewport: str,
    remote_requests: list[str],
    console_errors: list[str],
    page_errors: list[str],
) -> dict[str, object]:
    structural = page.evaluate(
        """() => { const all = [...document.querySelectorAll('*')]; const headings = [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')]; return { h1_count: document.querySelectorAll('h1').length, header_count: document.querySelectorAll('header').length, main_count: document.querySelectorAll('main').length, footer_count: document.querySelectorAll('footer').length, section_count: document.querySelectorAll('section').length, heading_levels: headings.map(node => Number(node.tagName.slice(1))), table_count: document.querySelectorAll('table').length, captioned_table_count: [...document.querySelectorAll('table')].filter(table => table.querySelector(':scope > caption')).length, csp: document.querySelector('meta[http-equiv="Content-Security-Policy"]')?.getAttribute('content') || '', script_count: document.querySelectorAll('script').length, event_handler_count: all.reduce((count, node) => count + [...node.attributes].filter(attr => attr.name.toLowerCase().startsWith('on')).length, 0), form_count: document.querySelectorAll('form').length, iframe_count: document.querySelectorAll('iframe').length, overflow_px: Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth) }; }"""
    )
    page.keyboard.press("Tab")
    visible_focus = bool(
        page.evaluate(
            """() => { const node = document.activeElement; if (!node || !node.matches('a[href="#research-brief-main"]')) return false; const style = getComputedStyle(node); return parseFloat(style.outlineWidth || '0') > 0 && style.outlineStyle !== 'none'; }"""
        )
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
    page.emulate_media(
        media="screen", forced_colors="active", reduced_motion="no-preference"
    )
    forced_colors_non_color_cue = bool(
        page.evaluate(
            """() => { const nodes = [document.querySelector('.srcc-boundary, .boundary'), document.querySelector('.srcc-state, .state')]; return nodes.every(node => { if (!node) return false; const style = getComputedStyle(node); return parseFloat(style.borderInlineStartWidth || '0') > 0 && style.borderInlineStartStyle !== 'none' && node.innerText.trim().length > 0; }); }"""
        )
    )
    page.emulate_media(media="screen", forced_colors="none", reduced_motion="reduce")
    page.wait_for_timeout(25)
    reduced_motion_static = bool(
        page.evaluate(
            """() => { const seconds = value => Math.max(...value.split(',').map(raw => { const text = raw.trim(); if (text.endsWith('ms')) return parseFloat(text) / 1000; if (text.endsWith('s')) return parseFloat(text); return 0; })); return document.getAnimations().length === 0 && [...document.querySelectorAll('*')].every(node => { const style = getComputedStyle(node); return seconds(style.animationDuration) <= 0.001 && seconds(style.transitionDuration) <= 0.001 && style.scrollBehavior !== 'smooth'; }); }"""
        )
    )
    page.emulate_media(media="print", forced_colors="none", reduced_motion="reduce")
    print_boundary_visible, print_provenance_visible = (
        _visible(page, boundary_selector),
        _visible(page, provenance_selector),
    )
    pdf_bytes = page.pdf()
    return {
        "state": state,
        "viewport": viewport,
        "h1_count": int(structural["h1_count"]),
        "header_count": int(structural["header_count"]),
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
        "print_boundary_visible": print_boundary_visible,
        "print_provenance_visible": print_provenance_visible,
        "console_errors": tuple(console_errors),
        "page_errors": tuple(page_errors),
        "pdf_byte_length": len(pdf_bytes),
        "pdf_header": pdf_bytes[:4].decode("ascii", errors="replace"),
    }


def run_company_workbench_html_browser_gate(
    cases: Mapping[str, bytes],
    *,
    repo_root: Path,
    chrome_executable: Path | None = None,
) -> tuple[HtmlBriefBrowserResult, ...]:
    """Run the browser matrix on exact injected bytes and prove the repository was unchanged."""
    if not cases:
        raise ValueError("At least one injected HTML document is required")
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
            browser = playwright.chromium.launch(
                executable_path=str(executable), headless=True
            )
            try:
                for state, document_bytes in cases.items():
                    if type(state) is not str or type(document_bytes) is not bytes:
                        raise TypeError(
                            "Browser gate cases must map string states to exact bytes"
                        )
                    document = document_bytes.decode("utf-8", errors="strict")
                    if document.encode("utf-8") != document_bytes:
                        raise ValueError(
                            "Injected HTML failed the strict UTF-8 byte roundtrip"
                        )
                    for width, height in ((1280, 720), (390, 844), (640, 900)):
                        viewport = f"{width}x{height}"
                        context = browser.new_context(
                            viewport={"width": width, "height": height}
                        )
                        page = context.new_page()
                        remote_requests: list[str] = []
                        console_errors: list[str] = []
                        page_errors: list[str] = []

                        def observe_request(request):
                            if request.url.startswith(("http://", "https://")):
                                remote_requests.append(request.url)

                        def intercept(route, request):
                            if request.url.startswith(("http://", "https://")):
                                route.abort()
                            else:
                                route.continue_()

                        page.route("**/*", intercept)
                        page.on("request", observe_request)
                        page.on(
                            "console",
                            lambda message: (
                                console_errors.append(message.text)
                                if message.type == "error"
                                else None
                            ),
                        )
                        page.on(
                            "pageerror", lambda error: page_errors.append(str(error))
                        )
                        try:
                            page.set_content(document, wait_until="load")
                            observation = _browser_observation(
                                page,
                                state=state,
                                viewport=viewport,
                                remote_requests=remote_requests,
                                console_errors=console_errors,
                                page_errors=page_errors,
                            )
                            results.append(evaluate_html_brief_observation(observation))
                        finally:
                            page.close()
                            context.close()
            finally:
                browser.close()
    finally:
        after = repository_fingerprint(root)
        if after != before:
            raise RuntimeError(
                "HTML research brief browser gate changed the repository fingerprint"
            )
    return tuple(results)
