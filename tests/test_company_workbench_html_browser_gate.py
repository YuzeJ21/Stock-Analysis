from __future__ import annotations

import hashlib
import json
import os
import re
import socket
import subprocess
import tempfile
import urllib.error
import urllib.request
from dataclasses import asdict, replace
from html.parser import HTMLParser
from pathlib import Path

import pytest

import src.company_workbench_html_browser_gate as browser_gate
from src.company_workbench_html import (
    CompanyWorkbenchHtmlSnapshot,
    HtmlBriefAnswer,
    HtmlBriefDcfBridge,
    HtmlBriefEvidenceRow,
    HtmlBriefSafeReference,
    HtmlBriefScenario,
    HtmlBriefSection,
    HtmlBriefSensitivity,
    company_workbench_html_bytes,
)
from src.company_workbench_html_browser_gate import (
    REQUIRED_OBSERVATION_KEYS,
    evaluate_html_brief_observation,
    repository_fingerprint,
    run_company_workbench_html_browser_gate,
)


EXACT_CSP = (
    "default-src 'none'; script-src 'none'; connect-src 'none'; img-src 'none'; "
    "style-src 'unsafe-inline'; font-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'"
)

ASSERTION_NAMES = {
    "observation_complete",
    "one_h1",
    "semantic_landmarks",
    "logical_headings",
    "skip_focus",
    "visible_focus",
    "tables_captioned",
    "csp_exact",
    "no_script",
    "no_event_handlers",
    "no_forms",
    "no_iframes",
    "no_remote_requests",
    "research_boundary_visible",
    "blockers_visible",
    "provenance_visible",
    "no_overflow",
    "forced_colors_non_color_cue",
    "reduced_motion_static",
    "print_boundary_visible",
    "print_provenance_visible",
    "no_console_errors",
    "no_page_errors",
    "pdf_in_memory",
    "actual_browser_zoom",
    "one_pager_visible",
    "one_pager_before_overview",
    "one_pager_structure",
    "one_pager_lists",
    "one_pager_state_truth",
    "one_pager_state_role_integrity",
    "one_pager_share_basis_disclosure",
    "one_pager_provenance_caption_visible",
    "one_pager_text_contrast",
    "one_pager_boundary_contrast",
    "one_pager_no_overflow",
    "one_pager_no_descendant_overflow",
    "one_pager_screen_content_visible",
    "one_pager_forced_colors_non_color_cue",
    "one_pager_print_text_contrast",
    "one_pager_print_boundary_contrast",
    "one_pager_print_content_visible",
}

SYNTHETIC_STATE_ROLES = (
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


def _literal_state_tokens(
    default: str,
    overrides: dict[str, str] | None = None,
) -> tuple[str, ...]:
    supplied = overrides or {}
    return tuple(
        sorted(f"{role}={supplied.get(role, default)}" for role in SYNTHETIC_STATE_ROLES)
    )


SYNTHETIC_EXPECTED_STATE_ROLE_TOKENS = {
    "complete": _literal_state_tokens(
        "available",
        {
            "answers-still-withheld": "withheld",
            "answers-what-changed": "partial",
        },
    ),
    "partial": _literal_state_tokens(
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
    "stale": _literal_state_tokens(
        "stale",
        {
            "answers-still-withheld": "withheld",
            "answers-what-changed": "partial",
        },
    ),
    "withheld": _literal_state_tokens("withheld"),
}

SYNTHETIC_EXPECTED_SHARE_BASIS_TOKENS = (
    "operating-valuation-base-bridge-share-basis=unverified",
    "scenarios-base-share-basis=unverified",
    "scenarios-bear-share-basis=unverified",
    "scenarios-bull-share-basis=unverified",
)

DEPENDENT_ASSERTIONS = {
    "state": set(),
    "viewport": set(),
    "requested_zoom": {"actual_browser_zoom"},
    "actual_browser_zoom": {"actual_browser_zoom"},
    "h1_count": {"one_h1"},
    "header_count": {"semantic_landmarks"},
    "page_header_count": {"semantic_landmarks"},
    "one_pager_header_count": {"semantic_landmarks"},
    "main_count": {"semantic_landmarks"},
    "footer_count": {"semantic_landmarks"},
    "section_count": {"semantic_landmarks"},
    "heading_levels": {"logical_headings"},
    "skip_target_focused": {"skip_focus"},
    "visible_focus": {"visible_focus"},
    "table_count": {"tables_captioned"},
    "captioned_table_count": {"tables_captioned"},
    "csp": {"csp_exact"},
    "script_count": {"no_script"},
    "event_handler_count": {"no_event_handlers"},
    "form_count": {"no_forms"},
    "iframe_count": {"no_iframes"},
    "remote_request_count": {"no_remote_requests"},
    "boundary_visible": {"research_boundary_visible"},
    "blockers_visible": {"blockers_visible"},
    "provenance_visible": {"provenance_visible"},
    "overflow_px": {"no_overflow"},
    "forced_colors_non_color_cue": {"forced_colors_non_color_cue"},
    "reduced_motion_static": {"reduced_motion_static"},
    "print_boundary_visible": {"print_boundary_visible"},
    "print_provenance_visible": {"print_provenance_visible"},
    "console_errors": {"no_console_errors"},
    "page_errors": {"no_page_errors"},
    "pdf_byte_length": {"pdf_in_memory"},
    "pdf_header": {"pdf_in_memory"},
    "one_pager_visible": {"one_pager_visible"},
    "one_pager_before_overview": {"one_pager_before_overview"},
    "one_pager_heading_count": {"one_pager_structure"},
    "one_pager_section_count": {"one_pager_structure"},
    "one_pager_answer_item_count": {"one_pager_lists"},
    "one_pager_scenario_item_count": {"one_pager_lists"},
    "one_pager_state_tokens": {"one_pager_state_truth"},
    "one_pager_share_basis_tokens": {"one_pager_share_basis_disclosure"},
    "one_pager_state_node_count": {"one_pager_state_role_integrity"},
    "one_pager_state_role_count": {"one_pager_state_role_integrity"},
    "one_pager_unique_state_role_count": {"one_pager_state_role_integrity"},
    "one_pager_provenance_caption_visible": {
        "one_pager_provenance_caption_visible"
    },
    "one_pager_min_text_contrast_ratio": {"one_pager_text_contrast"},
    "one_pager_min_boundary_contrast_ratio": {"one_pager_boundary_contrast"},
    "one_pager_overflow_px": {"one_pager_no_overflow"},
    "one_pager_max_descendant_overflow_px": {
        "one_pager_no_descendant_overflow"
    },
    "one_pager_provenance_visible": {"one_pager_screen_content_visible"},
    "one_pager_blockers_visible": {"one_pager_screen_content_visible"},
    "one_pager_assumptions_visible": {"one_pager_screen_content_visible"},
    "one_pager_handoff_visible": {"one_pager_screen_content_visible"},
    "one_pager_forced_colors_non_color_cue": {
        "one_pager_forced_colors_non_color_cue"
    },
    "one_pager_print_min_text_contrast_ratio": {
        "one_pager_print_text_contrast"
    },
    "one_pager_print_min_boundary_contrast_ratio": {
        "one_pager_print_boundary_contrast"
    },
    "one_pager_print_provenance_visible": {
        "one_pager_print_content_visible"
    },
    "one_pager_print_blockers_visible": {"one_pager_print_content_visible"},
    "one_pager_print_assumptions_visible": {
        "one_pager_print_content_visible"
    },
    "one_pager_print_handoff_visible": {"one_pager_print_content_visible"},
}


def _complete_observation() -> dict[str, object]:
    return {
        "state": "complete",
        "viewport": "1280x720",
        "requested_zoom": 1,
        "actual_browser_zoom": True,
        "h1_count": 1,
        "header_count": 2,
        "page_header_count": 1,
        "one_pager_header_count": 1,
        "main_count": 1,
        "footer_count": 1,
        "section_count": 2,
        "heading_levels": (1, 2, 2),
        "skip_target_focused": True,
        "visible_focus": True,
        "table_count": 1,
        "captioned_table_count": 1,
        "csp": EXACT_CSP,
        "script_count": 0,
        "event_handler_count": 0,
        "form_count": 0,
        "iframe_count": 0,
        "remote_request_count": 0,
        "boundary_visible": True,
        "blockers_visible": True,
        "provenance_visible": True,
        "overflow_px": 0.0,
        "forced_colors_non_color_cue": True,
        "reduced_motion_static": True,
        "print_boundary_visible": True,
        "print_provenance_visible": True,
        "console_errors": (),
        "page_errors": (),
        "pdf_byte_length": 512,
        "pdf_header": "%PDF",
        "one_pager_visible": True,
        "one_pager_before_overview": True,
        "one_pager_heading_count": 8,
        "one_pager_section_count": 7,
        "one_pager_answer_item_count": 4,
        "one_pager_scenario_item_count": 3,
        "one_pager_state_tokens": SYNTHETIC_EXPECTED_STATE_ROLE_TOKENS["complete"],
        "one_pager_share_basis_tokens": SYNTHETIC_EXPECTED_SHARE_BASIS_TOKENS,
        "one_pager_state_node_count": len(SYNTHETIC_STATE_ROLES),
        "one_pager_state_role_count": len(SYNTHETIC_STATE_ROLES),
        "one_pager_unique_state_role_count": len(SYNTHETIC_STATE_ROLES),
        "one_pager_provenance_caption_visible": True,
        "one_pager_min_text_contrast_ratio": 7.0,
        "one_pager_min_boundary_contrast_ratio": 3.5,
        "one_pager_overflow_px": 0.0,
        "one_pager_max_descendant_overflow_px": 0.0,
        "one_pager_provenance_visible": True,
        "one_pager_blockers_visible": True,
        "one_pager_assumptions_visible": True,
        "one_pager_handoff_visible": True,
        "one_pager_forced_colors_non_color_cue": True,
        "one_pager_print_min_text_contrast_ratio": 21.0,
        "one_pager_print_min_boundary_contrast_ratio": 21.0,
        "one_pager_print_provenance_visible": True,
        "one_pager_print_blockers_visible": True,
        "one_pager_print_assumptions_visible": True,
        "one_pager_print_handoff_visible": True,
    }


def _assertion_map(observation: dict[str, object]):
    result = evaluate_html_brief_observation(observation)
    return result, {assertion.name: assertion for assertion in result.assertions}


def _synthetic_snapshot(state: str) -> CompanyWorkbenchHtmlSnapshot:
    normalized = {
        "complete": "available",
        "partial": "partial",
        "stale": "stale",
        "withheld": "withheld",
    }[state]
    blocker = ("Synthetic evidence limitation remains visible.",)
    if state == "complete":
        enterprise_state = equity_state = per_share_state = explicit_state = (
            "available"
        )
        bridge_values = {
            "discounted_explicit_total": 1_000.0,
            "terminal_value": 2_000.0,
            "discounted_terminal_value": 1_500.0,
            "enterprise_value": 2_500.0,
            "cash": 400.0,
            "debt": 200.0,
            "net_debt": -200.0,
            "equity_value": 2_700.0,
            "shares_outstanding": 100.0,
            "scenario_value_per_share": 27.0,
        }
    elif state == "partial":
        enterprise_state = per_share_state = explicit_state = "available"
        equity_state = "partial"
        bridge_values = {
            "discounted_explicit_total": 1_100.0,
            "terminal_value": 2_100.0,
            "discounted_terminal_value": 1_600.0,
            "enterprise_value": 2_700.0,
            "cash": 999_999.0,
            "debt": 999_998.0,
            "net_debt": 999_997.0,
            "equity_value": 999_996.0,
            "shares_outstanding": 100.0,
            "scenario_value_per_share": 27.0,
        }
    elif state == "stale":
        enterprise_state = equity_state = per_share_state = explicit_state = "stale"
        bridge_values = {
            key: 555_555.0
            for key in (
                "discounted_explicit_total",
                "terminal_value",
                "discounted_terminal_value",
                "enterprise_value",
                "cash",
                "debt",
                "net_debt",
                "equity_value",
                "shares_outstanding",
                "scenario_value_per_share",
            )
        }
    else:
        enterprise_state = equity_state = per_share_state = explicit_state = (
            "withheld"
        )
        bridge_values = {
            key: 777_777.0
            for key in (
                "discounted_explicit_total",
                "terminal_value",
                "discounted_terminal_value",
                "enterprise_value",
                "cash",
                "debt",
                "net_debt",
                "equity_value",
                "shares_outstanding",
                "scenario_value_per_share",
            )
        }
    bridge = HtmlBriefDcfBridge(
        state=normalized,
        enterprise_state=enterprise_state,
        equity_state=equity_state,
        per_share_state=per_share_state,
        explicit_total_state=explicit_state,
        projected_fcfs=(),
        discounted_fcfs=(),
        discounted_explicit_total=bridge_values["discounted_explicit_total"],
        terminal_value=bridge_values["terminal_value"],
        discounted_terminal_value=bridge_values["discounted_terminal_value"],
        enterprise_value=bridge_values["enterprise_value"],
        cash=bridge_values["cash"],
        debt=bridge_values["debt"],
        net_debt=bridge_values["net_debt"],
        equity_value=bridge_values["equity_value"],
        shares_outstanding=bridge_values["shares_outstanding"],
        shares_label="Synthetic share basis",
        share_basis_state="unverified",
        scenario_value_per_share=bridge_values["scenario_value_per_share"],
        currency="USD",
        blockers=blocker,
    )
    assumptions = (
        {
            "revenue_growth": 0.08,
            "fcf_margin": 0.22,
            "wacc": 0.09,
            "terminal_growth": 0.025,
            "forecast_years": 5,
        }
        if state == "complete"
        else {
            "revenue_growth": None,
            "fcf_margin": None,
            "wacc": None,
            "terminal_growth": None,
            "forecast_years": None,
        }
    )
    scenarios = tuple(
        HtmlBriefScenario(
            name=name,
            state=normalized,
            modified=name == "Base",
            method_name="Synthetic test method",
            revenue_growth=assumptions["revenue_growth"],
            fcf_margin=assumptions["fcf_margin"],
            wacc=assumptions["wacc"],
            terminal_growth=assumptions["terminal_growth"],
            forecast_years=assumptions["forecast_years"],
            bridge=bridge,
        )
        for name in ("Bear", "Base", "Bull")
    )

    def section(key: str, title: str) -> HtmlBriefSection:
        return HtmlBriefSection(
            key=key,
            title=title,
            state=normalized,
            answer=f"Synthetic {title.lower()} evidence.",
            facts=(("Scope", "Synthetic browser contract"),),
            blockers=blocker,
        )

    decision_lanes = tuple(
        section(key, title)
        for key, title in (
            ("plan", "Research plan"),
            ("evidence", "Evidence review"),
            ("invalidation", "Invalidation evidence"),
            ("review-trigger", "Review trigger"),
        )
    )
    research_sections = tuple(
        section(key, title)
        for key, title in (
            ("business-trend", "Business trend"),
            ("key-drivers", "Key drivers"),
            ("valuation-regime", "Valuation regime"),
            ("risks", "Risks"),
            ("evidence-gaps", "Evidence gaps"),
        )
    )
    evidence = HtmlBriefEvidenceRow(
        section="Synthetic provenance",
        state=normalized,
        source_id="synthetic-test-source",
        source_ref=HtmlBriefSafeReference("Synthetic source", ""),
        as_of="2026-08-15T17:00:00-04:00",
        retrieved_at="2026-08-16T08:30:00-04:00",
        rights_state=normalized,
        field_scope_state=normalized,
        model_identity="synthetic-model",
        input_identity="synthetic-input",
        blockers=blocker,
    )
    answer_states = {
        "Use now": normalized,
        "Still withheld": "withheld",
        "What changed": "partial",
        "Next research task": normalized,
    }
    if state == "withheld":
        answer_states = {label: "withheld" for label in answer_states}
    answers = tuple(
        HtmlBriefAnswer(
            label,
            title,
            body,
            answer_states[label],
            (),
            (),
            blocker,
        )
        for label, title, body in (
            ("Use now", "Evidence ready to inspect", "Review the saved evidence state."),
            ("Still withheld", "Evidence remains withheld", "The named gap remains visible."),
            ("What changed", "Saved evidence delta", "Only the frozen test scope is compared."),
            ("Next research task", "Next evidence task", "Review the synthetic provenance row."),
        )
    )
    snapshot = CompanyWorkbenchHtmlSnapshot(
        ticker="TEST",
        profile_label="Synthetic test profile",
        review_cutoff="2026-08-16T09:00:00-04:00",
        source_as_of="2026-08-15T17:00:00-04:00",
        generated_at="2026-08-16T09:00:00-04:00",
        model_version="synthetic-test-v1",
        freshness_state=normalized,
        rights_state=normalized,
        boundary="Research-only, fail-closed portable evidence brief.",
        answers=answers,
        recency=section("recency", "Recency evidence"),
        readiness_lanes=(section("readiness", "Readiness evidence"),),
        scenarios=scenarios,
        sensitivity=HtmlBriefSensitivity(normalized, (), (), (), blocker),
        research_sections=research_sections,
        decision_lanes=decision_lanes,
        evidence_rows=(evidence,),
        blockers=blocker,
        identity="",
    )
    identity = hashlib.sha256(
        json.dumps(
            asdict(snapshot),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()
    return replace(snapshot, identity=identity)


def _synthetic_brief(state: str) -> bytes:
    return company_workbench_html_bytes(_synthetic_snapshot(state))


class _SummaryContractParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.depth = 0
        self.answer_count = 0
        self.scenario_count = 0
        self.caption_count = 0
        self.state_tokens: list[str] = []
        self.share_basis_tokens: list[str] = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if not self.depth:
            if attributes.get("data-section") != "evidence-one-pager":
                return
            self.depth = 1
        else:
            self.depth += 1
        if attributes.get("data-answer-item") is not None:
            self.answer_count += 1
        if attributes.get("data-scenario-item") is not None:
            self.scenario_count += 1
        if tag == "caption":
            self.caption_count += 1
        if "data-state" in attributes or "data-state-role" in attributes:
            self.state_tokens.append(
                f"{attributes.get('data-state-role', '')}={attributes.get('data-state', '')}"
            )
        if (
            "data-share-basis-role" in attributes
            or "data-share-basis-state" in attributes
        ):
            self.share_basis_tokens.append(
                f"{attributes.get('data-share-basis-role', '')}={attributes.get('data-share-basis-state', '')}"
            )

    def handle_endtag(self, tag):
        if self.depth:
            self.depth -= 1


def _append_test_css(document: bytes, css: str) -> bytes:
    marker = b"</style>"
    assert document.count(marker) == 1
    return document.replace(marker, css.encode("utf-8") + marker, 1)


def _replace_once(document: bytes, old: bytes, new: bytes) -> bytes:
    assert document.count(old) >= 1
    return document.replace(old, new, 1)


def _remove_marked_list_item(document: bytes, marker: bytes) -> bytes:
    marker_start = document.index(marker)
    item_start = document.rfind(b"<li", 0, marker_start)
    assert item_start >= 0
    depth = 0
    for match in re.finditer(rb"<li(?:\s|>)|</li>", document[item_start:]):
        if match.group().startswith(b"<li"):
            depth += 1
            continue
        depth -= 1
        if depth == 0:
            item_end = item_start + match.end()
            return document[:item_start] + document[item_end:]
    raise AssertionError("marked list item did not have a balanced closing tag")


def _move_one_pager_after_overview(document: bytes) -> bytes:
    start = document.index(b'<section class="srcc-one-pager"')
    overview = document.index(b'<section class="srcc-section" data-section="overview">')
    summary = document[start:overview]
    without = document[:start] + document[overview:]
    overview_start = without.index(
        b'<section class="srcc-section" data-section="overview">'
    )
    overview_end = without.index(b"</section>", overview_start) + len(b"</section>")
    return without[:overview_end] + summary + without[overview_end:]


def _run_summary_cell(
    document: bytes,
    *,
    state: str = "complete",
    cells: tuple[tuple[int, int, int], ...] = ((1280, 720, 1),),
):
    results = run_company_workbench_html_browser_gate(
        {state: document},
        repo_root=Path.cwd(),
        cells=cells,
    )
    assert len(results) == 1
    return results[0]


def _wrap_skip_link_in_overflow(document: bytes, overflow: str) -> bytes:
    assert overflow in {"auto", "scroll"}
    rendered = document.decode("utf-8", errors="strict")
    body = '<body class="srcc-html-document">'
    assert rendered.count(body) == 1
    assert rendered.count("</a><header") == 1
    rendered = rendered.replace(
        body,
        body + f'<div class="test-focus-clip test-focus-clip-{overflow}">',
        1,
    ).replace("</a><header", "</a></div><header", 1)
    return _append_test_css(
        rendered.encode("utf-8"),
        f"""
.test-focus-clip {{ position: absolute; inset: .5rem auto auto .5rem; width: 18rem; height: 3rem; overflow: {overflow} !important; }}
.test-focus-clip .srcc-skip-link {{ position: static !important; display: block !important; width: 100% !important; height: 100% !important; outline: none !important; box-shadow: none !important; border: 0 !important; }}
.test-focus-clip .srcc-skip-link:focus-visible {{ outline: 4px solid #d04a00 !important; outline-offset: 8px !important; }}
""",
    )


def _directional_shadow_clipped_at_edge(
    document: bytes,
    *,
    overflow: str,
    edge: str,
) -> bytes:
    assert overflow in {"auto", "scroll"}
    assert edge in {"left", "right"}
    offset = "-16px" if edge == "left" else "16px"
    justify = "flex-start" if edge == "left" else "flex-end"
    wrapped = _wrap_skip_link_in_overflow(document, overflow)
    return _append_test_css(
        wrapped,
        f"""
.test-focus-clip {{ display: flex !important; align-items: stretch !important; justify-content: {justify} !important; }}
.test-focus-clip .srcc-skip-link {{ flex: 0 0 4rem !important; width: 4rem !important; height: 100% !important; outline: none !important; border: 0 !important; box-shadow: none !important; background: #ffffff !important; }}
.test-focus-clip .srcc-skip-link:focus-visible {{ outline: none !important; border: 0 !important; background: #ffffff !important; box-shadow: {offset} 0 0 0 #d04a00 !important; }}
""",
    )


def _static_shadow_with_unsupported_focus_addition(
    document: bytes,
    *,
    added_shadow: str,
) -> bytes:
    return _append_test_css(
        document,
        f"""
.srcc-skip-link {{
    outline: none !important;
    border: 0 !important;
    background: #ffffff !important;
    color: #18222e !important;
    text-decoration: none !important;
    box-shadow: 10px 0 0 0 #d04a00 !important;
}}
.srcc-skip-link:focus-visible {{
    outline: none !important;
    border: 0 !important;
    background: #ffffff !important;
    color: #18222e !important;
    text-decoration: none !important;
    box-shadow: 10px 0 0 0 #d04a00, {added_shadow} !important;
}}
""",
    )


def _failed_assertion_names(result) -> set[str]:
    return {assertion.name for assertion in result.assertions if not assertion.passed}


def test_injected_server_contract_serves_exact_bytes_and_explicit_favicon():
    payload = b"<!doctype html><html><body>exact \xe2\x98\x83 bytes</body></html>"

    with browser_gate._injected_brief_server({"complete": payload}) as origin:
        with urllib.request.urlopen(f"{origin}/complete.html", timeout=2) as response:
            assert response.status == 200
            assert response.headers["Content-Type"] == "text/html; charset=utf-8"
            assert int(response.headers["Content-Length"]) == len(payload)
            assert response.read() == payload
        with urllib.request.urlopen(f"{origin}/favicon.ico", timeout=2) as response:
            assert response.status == 204
            assert response.read() == b""


def test_injected_server_contract_rejects_an_unknown_state_without_writing():
    with browser_gate._injected_brief_server({"complete": b"complete"}) as origin:
        with pytest.raises(urllib.error.HTTPError) as captured:
            urllib.request.urlopen(f"{origin}/unknown.html", timeout=2)

    assert captured.value.code == 404


def test_external_origin_policy_contract_allows_only_the_exact_active_origin():
    active = "http://127.0.0.1:43210"
    expected = {
        "http://127.0.0.1:43210/complete.html": ("allow", False),
        "http://127.0.0.1:43210/favicon.ico": ("allow", False),
        "http://127.0.0.1:43211/complete.html": ("abort", True),
        "http://localhost:43210/complete.html": ("abort", True),
        "https://127.0.0.1:43210/complete.html": ("abort", True),
        "http://[malformed": ("abort", True),
        "data:text/plain,local": ("allow", False),
        "blob:http://127.0.0.1:43210/token": ("allow", False),
        "about:blank": ("allow", False),
    }

    assert {
        url: browser_gate.evaluate_html_brief_request_origin(
            request_url=url,
            active_origin=active,
        )
        for url in expected
    } == expected


def test_synthetic_fixture_contract_has_four_substantive_scope_valid_cases():
    for state in ("complete", "partial", "stale", "withheld"):
        snapshot = _synthetic_snapshot(state)
        identity_payload = json.dumps(
            asdict(replace(snapshot, identity="")),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        assert snapshot.identity == hashlib.sha256(identity_payload).hexdigest()
        assert snapshot.review_cutoff == "2026-08-16T09:00:00-04:00"
        assert tuple(answer.label for answer in snapshot.answers) == (
            "Use now",
            "Still withheld",
            "What changed",
            "Next research task",
        )
        assert {section.key for section in snapshot.decision_lanes} == {
            "plan",
            "evidence",
            "invalidation",
            "review-trigger",
        }
        assert {section.key for section in snapshot.research_sections} == {
            "business-trend",
            "key-drivers",
            "valuation-regime",
            "risks",
            "evidence-gaps",
        }
        assert tuple(scenario.name for scenario in snapshot.scenarios) == (
            "Bear",
            "Base",
            "Bull",
        )
        assert len(snapshot.evidence_rows) == 1
        assert all(
            scenario.bridge.share_basis_state == "unverified"
            for scenario in snapshot.scenarios
        )

        rendered = _synthetic_brief(state).decode("utf-8")
        assert 'data-section="evidence-one-pager"' in rendered
        assert 'data-section="evidence-one-pager-unavailable"' not in rendered
        parser = _SummaryContractParser()
        parser.feed(rendered)
        assert parser.answer_count == 4
        assert parser.scenario_count == 3
        assert parser.caption_count >= 1
        assert tuple(sorted(parser.state_tokens)) == (
            SYNTHETIC_EXPECTED_STATE_ROLE_TOKENS[state]
        )
        assert tuple(sorted(parser.share_basis_tokens)) == (
            SYNTHETIC_EXPECTED_SHARE_BASIS_TOKENS
        )


def test_synthetic_fixture_contract_numeric_layout_and_suppression_are_independent():
    complete = _synthetic_snapshot("complete")
    partial = _synthetic_snapshot("partial")
    stale = _synthetic_snapshot("stale")
    withheld = _synthetic_snapshot("withheld")

    assert all(
        scenario.revenue_growth is not None
        and scenario.bridge.scenario_value_per_share is not None
        for scenario in complete.scenarios
    )
    assert partial.scenarios[1].bridge.enterprise_state == "available"
    assert partial.scenarios[1].bridge.equity_state == "partial"
    assert partial.scenarios[1].bridge.cash == 999_999.0
    partial_rendered = _synthetic_brief("partial").decode("utf-8")
    partial_summary = partial_rendered[
        partial_rendered.index('data-section="evidence-one-pager"') :
        partial_rendered.index('data-section="overview"')
    ]
    assert "999,999" not in partial_summary
    assert all(
        scenario.bridge.scenario_value_per_share is not None
        for scenario in withheld.scenarios
    )
    withheld_rendered = _synthetic_brief("withheld").decode("utf-8")
    withheld_summary = withheld_rendered[
        withheld_rendered.index('data-section="evidence-one-pager"') :
        withheld_rendered.index('data-section="overview"')
    ]
    assert "777,777" not in withheld_summary
    assert all(scenario.bridge.per_share_state == "stale" for scenario in stale.scenarios)
    stale_rendered = _synthetic_brief("stale").decode("utf-8")
    stale_summary = stale_rendered[
        stale_rendered.index('data-section="evidence-one-pager"') :
        stale_rendered.index('data-section="overview"')
    ]
    assert "555,555" not in stale_summary


@pytest.mark.parametrize(
    ("requested_zoom", "geometry", "expected"),
    (
        (
            1,
            {
                "screenshot_width": 1280,
                "screenshot_height": 720,
                "inner_width": 1280,
                "inner_height": 720,
                "visual_viewport_width": 1280,
                "visual_viewport_height": 720,
                "device_pixel_ratio": 1,
                "visual_viewport_scale": 1,
            },
            True,
        ),
        (
            2,
            {
                "screenshot_width": 1280,
                "screenshot_height": 720,
                "inner_width": 640,
                "inner_height": 360,
                "visual_viewport_width": 640,
                "visual_viewport_height": 360,
                "device_pixel_ratio": 2,
                "visual_viewport_scale": 1,
            },
            True,
        ),
        (
            4,
            {
                "screenshot_width": 1440,
                "screenshot_height": 1024,
                "inner_width": 360,
                "inner_height": 256,
                "visual_viewport_width": 360,
                "visual_viewport_height": 256,
                "device_pixel_ratio": 4,
                "visual_viewport_scale": 1,
            },
            True,
        ),
        (
            4,
            {
                "screenshot_width": 1440,
                "screenshot_height": 1024,
                "inner_width": 1440,
                "inner_height": 1024,
                "visual_viewport_width": 1440,
                "visual_viewport_height": 1024,
                "device_pixel_ratio": 1,
                "visual_viewport_scale": 1,
            },
            False,
        ),
    ),
)
def test_zoom_contract_requires_matching_real_chrome_geometry(
    requested_zoom,
    geometry,
    expected,
):
    result = browser_gate.evaluate_html_brief_browser_zoom(
        requested_zoom=requested_zoom,
        declared_width=1280 if requested_zoom != 4 else 1440,
        declared_height=720 if requested_zoom != 4 else 1024,
        **geometry,
    )

    assert result.passed is expected
    assert result.evidence


def test_summary_browser_collector_contract_accepts_the_substantive_baseline():
    result = _run_summary_cell(_synthetic_brief("complete"))

    assert result.zoom == 1
    if not result.passed:
        pytest.fail(
            "\n".join(
                f"{assertion.name}: {assertion.evidence}"
                for assertion in result.assertions
                if not assertion.passed
            ),
            pytrace=False,
        )


def test_summary_browser_collector_wraps_wide_scenario_labels_at_200_percent():
    document = _synthetic_brief("complete")
    assert document.count(b"Revenue growth") == 4
    document = document.replace(
        b"Revenue growth",
        b"Revenue growth expectations through cycle",
    )

    result = _run_summary_cell(
        document,
        cells=((1440, 1024, 2),),
    )

    assert result.passed is True
    assert next(
        assertion
        for assertion in result.assertions
        if assertion.name == "one_pager_no_descendant_overflow"
    ).passed is True


def test_summary_browser_collector_wraps_blockers_with_wider_text_metrics():
    document = _append_test_css(
        _synthetic_brief("complete"),
        ".srcc-one-pager { font-size: 21.1px !important; }",
    )

    result = _run_summary_cell(
        document,
        cells=((1440, 1024, 2),),
    )

    assert result.passed is True
    assert next(
        assertion
        for assertion in result.assertions
        if assertion.name == "one_pager_no_descendant_overflow"
    ).passed is True


@pytest.mark.parametrize(
    ("mutation", "expected_assertion"),
    (
        (
            lambda document: _append_test_css(
                document,
                "body.srcc-html-document .srcc-one-pager { display: none !important; }",
            ),
            "one_pager_visible",
        ),
        (
            lambda document: _move_one_pager_after_overview(document),
            "one_pager_before_overview",
        ),
        (
            lambda document: _replace_once(
                document,
                b"<caption>Portable evidence provenance</caption>",
                b"",
            ),
            "one_pager_provenance_caption_visible",
        ),
        (
            lambda document: _remove_marked_list_item(
                document,
                b' data-answer-item=""',
            ),
            "one_pager_lists",
        ),
        (
            lambda document: _remove_marked_list_item(
                document,
                b' data-scenario-item=""',
            ),
            "one_pager_lists",
        ),
        (
            lambda document: _replace_once(
                document,
                b' data-state-role="answers-use-now"',
                b"",
            ),
            "one_pager_state_role_integrity",
        ),
        (
            lambda document: _replace_once(
                document,
                b'data-state-role="answers-use-now"',
                b'data-state-role="answers-still-withheld"',
            ),
            "one_pager_state_role_integrity",
        ),
        (
            lambda document: _append_test_css(
                document,
                """
body.srcc-html-document .srcc-one-pager { overflow-x: hidden !important; }
body.srcc-html-document .srcc-one-pager [data-section='one-pager-handoff'] {
  width: 100% !important;
  overflow-x: auto !important;
}
body.srcc-html-document .srcc-one-pager [data-section='one-pager-handoff'] p {
  min-width: 2000px !important;
}
""",
            ),
            "one_pager_no_descendant_overflow",
        ),
    ),
)
def test_summary_browser_collector_contract_rejects_scoped_structure_mutations(
    mutation,
    expected_assertion,
):
    result = _run_summary_cell(mutation(_synthetic_brief("complete")))

    assert expected_assertion in _failed_assertion_names(result)


def test_summary_browser_collector_contract_rejects_a_relabelled_case():
    result = _run_summary_cell(_synthetic_brief("complete"), state="partial")

    assert "one_pager_state_truth" in _failed_assertion_names(result)


@pytest.mark.parametrize(
    ("css", "expected_assertion"),
    (
        (
            "body.srcc-html-document .srcc-one-pager p { color: #777 !important; background: #fff !important; }",
            "one_pager_text_contrast",
        ),
        (
            "body.srcc-html-document .srcc-one-pager a { color: #aaa !important; background: #fff !important; }",
            "one_pager_text_contrast",
        ),
        (
            "body.srcc-html-document .srcc-one-pager-grid { background: #0b1b2b !important; }",
            "one_pager_boundary_contrast",
        ),
    ),
)
def test_summary_browser_collector_contract_rejects_scoped_contrast_mutations(
    css,
    expected_assertion,
):
    document = _synthetic_brief("complete")
    if ".srcc-one-pager a" in css:
        document = _replace_once(
            document,
            b"</header><section data-section=\"one-pager-answers\">",
            (
                b'<a href="#evidence-one-pager-title">Summary link contrast</a>'
                b"</header><section data-section=\"one-pager-answers\">"
            ),
        )
    result = _run_summary_cell(_append_test_css(document, css))

    assert expected_assertion in _failed_assertion_names(result)


@pytest.mark.parametrize(
    ("css", "expected_assertions"),
    (
        (
            "@media screen { body.srcc-html-document .srcc-one-pager { opacity: .1 !important; } }",
            {
                "one_pager_visible",
                "one_pager_text_contrast",
                "one_pager_boundary_contrast",
                "one_pager_screen_content_visible",
            },
        ),
        (
            "@media screen { body.srcc-html-document #research-brief-main { opacity: .1 !important; } }",
            {
                "one_pager_visible",
                "one_pager_text_contrast",
                "one_pager_boundary_contrast",
                "one_pager_screen_content_visible",
            },
        ),
        (
            "@media print { body.srcc-html-document .srcc-one-pager { opacity: .1 !important; } }",
            {
                "one_pager_print_text_contrast",
                "one_pager_print_boundary_contrast",
                "one_pager_print_content_visible",
            },
        ),
        (
            "@media print { body.srcc-html-document #research-brief-main { opacity: .1 !important; } }",
            {
                "one_pager_print_text_contrast",
                "one_pager_print_boundary_contrast",
                "one_pager_print_content_visible",
            },
        ),
    ),
)
def test_summary_browser_collector_contract_rejects_root_or_ancestor_opacity(
    css,
    expected_assertions,
):
    result = _run_summary_cell(
        _append_test_css(_synthetic_brief("complete"), css)
    )
    failures = _failed_assertion_names(result)

    assert expected_assertions <= failures, {
        "missing": sorted(expected_assertions - failures),
        "observed_failures": sorted(failures),
        "contrast_evidence": {
            assertion.name: assertion.evidence
            for assertion in result.assertions
            if "contrast" in assertion.name
        },
    }


def test_summary_browser_collector_contract_rejects_fully_clipped_summary_with_outside_blockers():
    document = _append_test_css(
        _synthetic_brief("complete"),
        "body.srcc-html-document .srcc-one-pager { clip-path: inset(50%) !important; }",
    )
    document = _replace_once(
        document,
        b"</main><footer",
        (
            b'</main><div class="srcc-blockers">Outside summary blockers must not count.</div>'
            b"<footer"
        ),
    )

    result = _run_summary_cell(document)
    failures = _failed_assertion_names(result)
    expected = {
        "one_pager_visible",
        "one_pager_text_contrast",
        "one_pager_boundary_contrast",
        "one_pager_screen_content_visible",
        "one_pager_print_text_contrast",
        "one_pager_print_boundary_contrast",
        "one_pager_print_content_visible",
        "one_pager_forced_colors_non_color_cue",
    }

    assert expected <= failures, {
        "missing": sorted(expected - failures),
        "observed_failures": sorted(failures),
    }


def _wrap_one_pager_in_test_scroll(document):
    document = _replace_once(
        document,
        b'<section class="srcc-one-pager"',
        (
            b'<div class="test-scroll"><div class="test-spacer"></div>'
            b'<section class="srcc-one-pager"'
        ),
    )
    return _replace_once(
        document,
        b'<section class="srcc-section" data-section="overview">',
        b'</div><section class="srcc-section" data-section="overview">',
    )


def _with_pointer_transparent_test_cover(document, *, below_fold):
    document = _replace_once(
        document,
        b"</body>",
        b'<div class="test-pointer-transparent-cover" aria-hidden="true"></div></body>',
    )
    margin = ".srcc-one-pager { margin-top: 1000px !important; }" if below_fold else ""
    return _append_test_css(
        document,
        f"""
        @media screen {{
          {margin}
          .test-pointer-transparent-cover {{ position: fixed; inset: 0; background: #fff; z-index: 2147483647; pointer-events: none; }}
        }}
        """,
    )


def _with_pointer_transparent_svg_cover(document):
    document = _replace_once(
        document,
        b"</body>",
        (
            b'<svg class="test-pointer-transparent-svg-cover" aria-hidden="true" '
            b'viewBox="0 0 1 1"><rect width="1" height="1" fill="#fff" /></svg>'
            b"</body>"
        ),
    )
    return _append_test_css(
        document,
        """
        @media screen {
          .test-pointer-transparent-svg-cover { position: fixed; inset: 0; width: 100vw; height: 100vh; z-index: 2147483647; pointer-events: none; }
        }
        """,
    )


def _with_inside_pointer_transparent_cover(document):
    return _append_test_css(
        _replace_once(
            document,
            b'data-section="evidence-one-pager">',
            (
                b'data-section="evidence-one-pager">'
                b'<div class="test-inside-pointer-transparent-cover" '
                b'aria-hidden="true"></div>'
            ),
        ),
        """
        @media screen {
          .test-inside-pointer-transparent-cover { position: fixed; inset: 0; background: #fff; z-index: 2147483647; pointer-events: none; }
        }
        """,
    )


def _with_pointer_transparent_paint_cover(document, declarations):
    document = _replace_once(
        document,
        b"</body>",
        b'<div class="test-pointer-transparent-paint-cover" aria-hidden="true"></div></body>',
    )
    return _append_test_css(
        document,
        f"""
        @media screen {{
          .test-pointer-transparent-paint-cover {{
            position: fixed;
            inset: 0;
            z-index: 2147483647;
            pointer-events: none;
            background: transparent;
            {declarations}
          }}
        }}
        """,
    )


def _with_tiny_outward_real_paint_cover(document, declarations, *, below_fold):
    document = _replace_once(
        document,
        b'data-section="evidence-one-pager">',
        (
            b'data-section="evidence-one-pager">'
            b'<div class="test-tiny-outward-paint-cover" aria-hidden="true"></div>'
        ),
    )
    margin = ".srcc-one-pager { margin-top: 1000px !important; }" if below_fold else ""
    return _append_test_css(
        document,
        f"""
        @media screen {{
          {margin}
          .test-tiny-outward-paint-cover {{
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
            {declarations}
          }}
        }}
        """,
    )


def _with_tiny_outward_required_pseudo_cover(
    document,
    declarations,
    *,
    below_fold,
):
    margin = ".srcc-one-pager { margin-top: 1000px !important; }" if below_fold else ""
    return _append_test_css(
        document,
        f"""
        @media screen {{
          {margin}
          [data-section="one-pager-scenarios"] > ol > li:first-child .srcc-state::after {{
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
            {declarations}
          }}
        }}
        """,
    )


@pytest.mark.parametrize(
    "document",
    (
        _append_test_css(
            _wrap_one_pager_in_test_scroll(_synthetic_brief("complete")),
            """
            @media screen {
              .test-scroll { height: 100px !important; overflow: hidden !important; }
              .test-spacer { height: 1000px !important; }
            }
            """,
        ),
        _append_test_css(
            _wrap_one_pager_in_test_scroll(_synthetic_brief("complete")),
            """
            @media screen {
              .test-scroll { position: relative !important; height: 100px !important; overflow: auto !important; }
              .test-spacer { height: 1000px !important; }
              .test-scroll > .srcc-one-pager { position: absolute !important; top: -10000px !important; left: 0 !important; right: 0 !important; }
            }
            """,
        ),
        _append_test_css(
            _synthetic_brief("complete"),
            """
            @media screen {
              .srcc-one-pager { position: fixed !important; top: -10000px !important; left: 50px !important; width: 1000px !important; }
            }
            """,
        ),
        _with_pointer_transparent_svg_cover(_synthetic_brief("complete")),
        _with_inside_pointer_transparent_cover(_synthetic_brief("complete")),
        _append_test_css(
            _synthetic_brief("complete"),
            """
            @media screen {
              .srcc-one-pager::after { content: ''; position: fixed; inset: 0; background: #fff; z-index: 2147483647; pointer-events: none; }
            }
            """,
        ),
        _append_test_css(
            _synthetic_brief("complete"),
            """
            @media screen {
              body::after { content: ''; position: fixed; left: -100vw; top: 0; width: 100vw; height: 100vh; transform: translateX(100vw); background: #fff; z-index: 2147483647; pointer-events: none; }
            }
            """,
        ),
        _append_test_css(
            _synthetic_brief("complete"),
            """
            @media screen {
              body.srcc-html-document::after { content: ''; position: fixed; inset: 0; background: #fff; z-index: 2147483647; pointer-events: none !important; }
            }
            """,
        ),
        _with_pointer_transparent_test_cover(
            _synthetic_brief("complete"),
            below_fold=False,
        ),
        _with_pointer_transparent_test_cover(
            _synthetic_brief("complete"),
            below_fold=True,
        ),
        _append_test_css(
            _synthetic_brief("complete"),
            "@media screen { .srcc-one-pager { transform: translateX(-10000px) !important; } }",
        ),
        _append_test_css(
            _synthetic_brief("complete"),
            """
            @media screen {
              body::after { content: ''; position: fixed; inset: 0; background: #fff; z-index: 2147483647; pointer-events: auto; }
            }
            """,
        ),
        _append_test_css(
            _synthetic_brief("complete"),
            """
            @media screen {
              .srcc-one-pager { margin-top: 1000px !important; }
              body::after { content: ''; position: fixed; inset: 0; background: #fff; z-index: 2147483647; pointer-events: auto; }
            }
            """,
        ),
        _append_test_css(
            _synthetic_brief("complete"),
            """
            @media screen {
              body::after { content: ''; position: fixed; inset: 0; background: #fff; z-index: 2147483647; pointer-events: none; }
            }
            """,
        ),
        _append_test_css(
            _synthetic_brief("complete"),
            """
            @media screen {
              .srcc-one-pager { margin-top: 1000px !important; }
              body::after { content: ''; position: fixed; inset: 0; background: #fff; z-index: 2147483647; pointer-events: none; }
            }
            """,
        ),
        _append_test_css(
            _synthetic_brief("complete"),
            """
            @media screen {
              body::before { content: ''; position: fixed; inset: 0; background: #fff; z-index: 2147483647; pointer-events: none; }
            }
            """,
        ),
        _append_test_css(
            _synthetic_brief("complete"),
            """
            @media screen {
              .srcc-one-pager { margin-top: 1000px !important; }
              body::before { content: ''; position: fixed; inset: 0; background: #fff; z-index: 2147483647; pointer-events: none; }
            }
            """,
        ),
        _replace_once(
            _synthetic_brief("complete"),
            b"</body>",
            (
                b'<div aria-hidden="true" style="position:fixed;inset:0;'
                b'background:#fff;z-index:2147483647;'
                b'pointer-events:none!important"></div></body>'
            ),
        ),
        _append_test_css(
            _with_pointer_transparent_test_cover(
                _synthetic_brief("complete"),
                below_fold=False,
            ),
            "@media screen { .test-pointer-transparent-cover { background: rgba(255, 255, 255, .5) !important; } }",
        ),
        _append_test_css(
            _with_pointer_transparent_test_cover(
                _synthetic_brief("complete"),
                below_fold=False,
            ),
            "@media screen { .test-pointer-transparent-cover { opacity: .98 !important; } }",
        ),
    ),
    ids=(
        "overflow-hidden-ancestor",
        "unreachable-auto-scroll",
        "fixed-above-document",
        "pointer-transparent-svg-cover",
        "inside-pointer-transparent-element-cover",
        "inside-pointer-transparent-pseudo-cover",
        "transformed-pointer-transparent-pseudo-cover",
        "important-pointer-transparent-pseudo-cover",
        "pointer-transparent-element-cover",
        "scroll-reachable-under-pointer-transparent-element-cover",
        "translated-left-of-document",
        "opaque-fixed-cover",
        "scroll-reachable-under-fixed-cover",
        "pointer-transparent-opaque-cover",
        "scroll-reachable-under-pointer-transparent-cover",
        "pointer-transparent-before-cover",
        "scroll-reachable-under-pointer-transparent-before-cover",
        "inline-important-pointer-transparent-element-cover",
        "translucent-pointer-transparent-element-cover",
        "opacity-pointer-transparent-element-cover",
    ),
)
def test_summary_browser_collector_contract_rejects_unreachable_or_occluded_summary(
    document,
):
    result = _run_summary_cell(document)
    failures = _failed_assertion_names(result)
    expected = {
        "one_pager_visible",
        "one_pager_text_contrast",
        "one_pager_boundary_contrast",
        "one_pager_screen_content_visible",
    }

    assert expected <= failures, {
        "missing": sorted(expected - failures),
        "observed_failures": sorted(failures),
    }


def test_summary_browser_collector_contract_does_not_confirm_non_svg_origin_from_transparent_descendant():
    document = _replace_once(
        _synthetic_brief("complete"),
        b'<body class="srcc-html-document">',
        (
            b'<body class="srcc-html-document">'
            b'<div class="test-behind-paint-origin" aria-hidden="true">'
            b'<span class="test-transparent-probe-child"></span></div>'
        ),
    )
    document = _append_test_css(
        document,
        """
        @media screen {
          .test-behind-paint-origin {
            height: 100vh;
            margin-bottom: -100vh;
            background: #fff;
            pointer-events: none;
          }
          .test-transparent-probe-child {
            position: fixed;
            inset: 0;
            z-index: 2;
            background: transparent;
          }
        }
        """,
    )

    result = _run_summary_cell(document)

    assert _failed_assertion_names(result) == set()


def test_summary_browser_collector_contract_rejects_localized_late_provenance_pseudo_cover():
    document = _append_test_css(
        _synthetic_brief("complete"),
        """
        @media screen {
          [data-section="one-pager-provenance"] { position: relative; }
          [data-section="one-pager-provenance"]::after {
            content: '';
            position: absolute;
            inset: 0;
            z-index: 2147483647;
            pointer-events: none;
            background: #fff;
          }
        }
        """,
    )

    result = _run_summary_cell(document)
    assertions = {assertion.name: assertion for assertion in result.assertions}

    assert assertions["one_pager_visible"].passed is True
    assert assertions["one_pager_provenance_caption_visible"].passed is False
    assert assertions["one_pager_screen_content_visible"].passed is False


def test_summary_browser_collector_contract_rejects_localized_required_node_pseudo_covers():
    document = _append_test_css(
        _synthetic_brief("complete"),
        """
        @media screen {
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
        }
        """,
    )

    result = _run_summary_cell(document)
    assertions = {assertion.name: assertion for assertion in result.assertions}

    assert assertions["one_pager_visible"].passed is True
    assert assertions["one_pager_state_truth"].passed is False
    assert assertions["one_pager_share_basis_disclosure"].passed is False
    assert assertions["one_pager_provenance_caption_visible"].passed is False
    assert assertions["one_pager_screen_content_visible"].passed is False
    assert "(False, False, False, False)" in assertions[
        "one_pager_screen_content_visible"
    ].evidence


def test_summary_browser_collector_contract_rejects_localized_required_leaf_pseudo_covers():
    document = _append_test_css(
        _synthetic_brief("complete"),
        """
        @media screen {
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
          [data-section="one-pager-handoff"] > p,
          [data-share-basis-role="operating-valuation-base-bridge-share-basis"] {
            position: relative;
          }
          [data-section="one-pager-provenance"] caption::after,
          [data-section="one-pager-provenance"] tbody td:nth-child(2)::after,
          [data-section="one-pager-provenance"] .srcc-blockers > li::after,
          [data-section="one-pager-scenarios"] > ol > li:first-child .srcc-state::after,
          [data-section="one-pager-handoff"] > p::after,
          [data-share-basis-role="operating-valuation-base-bridge-share-basis"]::after {
            content: '';
            position: absolute;
            inset: 0;
            z-index: 2147483647;
            pointer-events: none;
            background: #fff;
          }
        }
        """,
    )

    result = _run_summary_cell(document)
    assertions = {assertion.name: assertion for assertion in result.assertions}

    assert assertions["one_pager_visible"].passed is True
    assert assertions["one_pager_state_truth"].passed is False
    assert assertions["one_pager_share_basis_disclosure"].passed is False
    assert assertions["one_pager_provenance_caption_visible"].passed is False
    assert assertions["one_pager_screen_content_visible"].passed is False
    assert "(False, False, False, False)" in assertions[
        "one_pager_screen_content_visible"
    ].evidence


@pytest.mark.parametrize(
    "selector",
    (
        '[data-section="one-pager-provenance"] caption',
        '[data-section="one-pager-scenarios"] > ol > li:first-child .srcc-state',
    ),
    ids=("caption", "state-label"),
)
def test_summary_browser_collector_contract_accepts_tiny_required_leaf_pseudo_decoration(
    selector,
):
    document = _append_test_css(
        _synthetic_brief("complete"),
        f"""
        @media screen {{
          {selector} {{ position: relative !important; }}
          {selector}::after {{
            content: '';
            position: absolute;
            right: 0;
            bottom: 0;
            width: 4px;
            height: 2px;
            z-index: 2147483647;
            pointer-events: none;
            background: #f0f;
          }}
        }}
        """,
    )

    result = _run_summary_cell(document)
    failures = _failed_assertion_names(result)
    expected_green = {
        "one_pager_visible",
        "one_pager_state_truth",
        "one_pager_provenance_caption_visible",
        "one_pager_screen_content_visible",
    }

    assert expected_green.isdisjoint(failures), sorted(failures)


@pytest.mark.parametrize(
    "document",
    (
        _append_test_css(
            _replace_once(
                _synthetic_brief("complete"),
                b"</body>",
                b'<div class="test-layer-cover" aria-hidden="true"></div></body>',
            ),
            """
            @layer adversarial {
              .test-layer-cover { position: fixed; inset: 0; z-index: 2147483647; pointer-events: none !important; background: #f0f; }
            }
            """,
        ),
        _append_test_css(
            _synthetic_brief("complete"),
            """
            @layer adversarial {
              body::after { content: ''; position: fixed; inset: 0; z-index: 2147483647; pointer-events: none !important; background: #f0f; }
            }
            """,
        ),
    ),
    ids=("real", "pseudo"),
)
def test_summary_browser_collector_contract_rejects_layered_important_pointer_transparent_paint(
    document,
):
    result = _run_summary_cell(document)
    failures = _failed_assertion_names(result)
    expected = {
        "one_pager_visible",
        "one_pager_text_contrast",
        "one_pager_boundary_contrast",
        "one_pager_screen_content_visible",
    }

    assert expected <= failures, {
        "missing": sorted(expected - failures),
        "observed_failures": sorted(failures),
    }


@pytest.mark.parametrize(
    "document",
    (
        _with_pointer_transparent_paint_cover(
            _synthetic_brief("complete"),
            "box-shadow: inset 0 0 0 100vmax #fff;",
        ),
        _append_test_css(
            _synthetic_brief("complete"),
            """
            @media screen {
              body::after {
                content: '';
                position: fixed;
                inset: 0;
                z-index: 2147483647;
                pointer-events: none;
                background: transparent;
                box-shadow: inset 0 0 0 100vmax #fff;
              }
            }
            """,
        ),
        _append_test_css(
            _synthetic_brief("complete"),
            """
            @media screen {
              body::after { content: ''; position: fixed; inset: 0; z-index: 2147483647; pointer-events: none; background: transparent; box-shadow: inset 0 0 0 100vmax oklab(.8 0 0); }
            }
            """,
        ),
        _with_pointer_transparent_paint_cover(
            _synthetic_brief("complete"),
            "box-sizing: border-box; border: 100vmax solid #fff;",
        ),
        _with_pointer_transparent_paint_cover(
            _synthetic_brief("complete"),
            "outline: 100vmax solid #fff; outline-offset: -100vmax;",
        ),
        _append_test_css(
            _synthetic_brief("complete"),
            """
            @media screen {
              body::after { content: ''; position: fixed; inset: 0; z-index: 2147483647; pointer-events: none; background: transparent; box-shadow: inset 0 0 0 400px #f0f; }
            }
            """,
        ),
        _append_test_css(
            _synthetic_brief("complete"),
            """
            @media screen {
              body::after { content: ''; position: fixed; inset: 0; box-sizing: border-box; z-index: 2147483647; pointer-events: none; background: transparent; border: 400px solid #f0f; }
            }
            """,
        ),
        _append_test_css(
            _synthetic_brief("complete"),
            """
            @media screen {
              body::after { content: ''; position: fixed; inset: 0; z-index: 2147483647; pointer-events: none; background: transparent; box-shadow: inset 0 0 0 100vmax color(srgb 1 1 1); }
            }
            """,
        ),
        _append_test_css(
            _synthetic_brief("complete"),
            """
            @media screen {
              body::after { content: ''; position: fixed; inset: 0; z-index: 2147483647; pointer-events: none; background: transparent; box-shadow: inset 0 0 0 100vmax color(display-p3 1 1 1); }
            }
            """,
        ),
    ),
    ids=(
        "real-inset-box-shadow",
        "pseudo-inset-box-shadow",
        "css-color-4-oklab-shadow",
        "opaque-border",
        "opaque-outline",
        "fixed-pseudo-400px-inset-shadow",
        "fixed-pseudo-400px-border",
        "css-color-4-srgb-shadow",
        "css-color-4-display-p3-shadow",
    ),
)
def test_summary_browser_collector_contract_rejects_pointer_transparent_material_edge_paint(
    document,
):
    result = _run_summary_cell(document)
    failures = _failed_assertion_names(result)
    expected = {
        "one_pager_visible",
        "one_pager_text_contrast",
        "one_pager_boundary_contrast",
        "one_pager_screen_content_visible",
    }

    assert expected <= failures, {
        "missing": sorted(expected - failures),
        "observed_failures": sorted(failures),
    }


@pytest.mark.parametrize(
    "declarations",
    (
        "box-shadow: 0 0 0 100vmax #fff;",
        "border: 100vmax solid #fff;",
        "outline: 100vmax solid #fff; outline-offset: 0;",
    ),
    ids=("outward-shadow", "outward-border", "outward-outline"),
)
@pytest.mark.parametrize("below_fold", (False, True), ids=("current", "below-fold"))
def test_summary_browser_collector_contract_rejects_tiny_real_outward_paint_footprint(
    declarations,
    below_fold,
):
    result = _run_summary_cell(
        _with_tiny_outward_real_paint_cover(
            _synthetic_brief("complete"),
            declarations,
            below_fold=below_fold,
        )
    )
    failures = _failed_assertion_names(result)
    expected = {
        "one_pager_visible",
        "one_pager_text_contrast",
        "one_pager_boundary_contrast",
        "one_pager_screen_content_visible",
    }

    assert expected <= failures, {
        "missing": sorted(expected - failures),
        "observed_failures": sorted(failures),
    }


@pytest.mark.parametrize(
    "declarations",
    (
        "box-shadow: 0 0 0 100vmax #fff;",
        "border: 100vmax solid #fff;",
        "outline: 100vmax solid #fff; outline-offset: 0;",
    ),
    ids=("outward-shadow", "outward-border", "outward-outline"),
)
@pytest.mark.parametrize("below_fold", (False, True), ids=("current", "below-fold"))
def test_summary_browser_collector_contract_rejects_tiny_required_pseudo_outward_paint_footprint(
    declarations,
    below_fold,
):
    result = _run_summary_cell(
        _with_tiny_outward_required_pseudo_cover(
            _synthetic_brief("complete"),
            declarations,
            below_fold=below_fold,
        )
    )
    failures = _failed_assertion_names(result)
    expected = {
        "one_pager_visible",
        "one_pager_text_contrast",
        "one_pager_boundary_contrast",
        "one_pager_screen_content_visible",
    }

    assert expected <= failures, {
        "missing": sorted(expected - failures),
        "observed_failures": sorted(failures),
    }


def test_summary_browser_collector_contract_accepts_zero_paint_pointer_layers():
    document = _append_test_css(
        _replace_once(
            _synthetic_brief("complete"),
            b"</body>",
            (
                b'<div class="test-zero-paint-layer" aria-hidden="true"></div>'
                b'<div class="test-one-percent-layer" aria-hidden="true"></div>'
                b'<div class="test-transparent-edge-paint-layer" aria-hidden="true"></div>'
                b'<svg class="test-empty-svg-layer" aria-hidden="true"></svg>'
                b"</body>"
            ),
        ),
        """
        @media screen {
          .test-zero-paint-layer {
            position: fixed;
            inset: 0;
            z-index: 2147483647;
            pointer-events: none;
            background: linear-gradient(transparent, transparent);
            box-shadow: 0 0 0 0 rgba(0, 0, 0, 0);
          }
          .test-one-percent-layer {
            position: fixed;
            inset: 0;
            z-index: 2147483646;
            pointer-events: none;
            background: rgba(255, 255, 255, .01);
          }
          .test-transparent-edge-paint-layer {
            position: fixed;
            inset: 0;
            z-index: 2147483646;
            pointer-events: none;
            background: transparent;
            box-shadow: inset 0 0 0 100vmax rgba(0, 0, 0, 0);
            border: 48px solid rgba(0, 0, 0, 0);
            outline: 48px solid rgba(0, 0, 0, 0);
            outline-offset: -48px;
          }
          .test-empty-svg-layer {
            position: fixed;
            inset: 0;
            width: 100vw;
            height: 100vh;
            z-index: 2147483645;
            pointer-events: none;
          }
        }
        """,
    )

    result = _run_summary_cell(document)
    failures = _failed_assertion_names(result)
    expected_green = {
        "one_pager_visible",
        "one_pager_text_contrast",
        "one_pager_boundary_contrast",
        "one_pager_screen_content_visible",
    }

    assert expected_green.isdisjoint(failures), sorted(failures)


def test_summary_browser_collector_contract_accepts_a_small_pointer_decoration():
    document = _append_test_css(
        _replace_once(
            _synthetic_brief("complete"),
            b"</body>",
            b'<div class="test-small-decoration" aria-hidden="true"></div></body>',
        ),
        """
        @media screen {
          .test-small-decoration {
            position: fixed;
            left: 630px;
            top: 430px;
            width: 20px;
            height: 20px;
            z-index: 2147483647;
            pointer-events: none;
            background: transparent;
            box-shadow: inset 0 0 0 100vmax #fff;
          }
        }
        """,
    )

    result = _run_summary_cell(document)
    failures = _failed_assertion_names(result)
    expected_green = {
        "one_pager_visible",
        "one_pager_text_contrast",
        "one_pager_boundary_contrast",
        "one_pager_screen_content_visible",
    }

    assert expected_green.isdisjoint(failures), sorted(failures)


@pytest.mark.parametrize("candidate_type", ("real", "pseudo"))
def test_summary_browser_collector_contract_rejects_full_cover_below_tiny_decoration(
    candidate_type,
):
    document = _synthetic_brief("complete")
    if candidate_type == "real":
        document = _replace_once(
            document,
            b"</body>",
            (
                b'<div class="test-stacked-full-cover" aria-hidden="true"></div>'
                b"</body>"
            ),
        )
        document = _replace_once(
            document,
            b'data-section="evidence-one-pager">',
            (
                b'data-section="evidence-one-pager">'
                b'<div class="test-stacked-tiny-decoration" aria-hidden="true"></div>'
            ),
        )
        css = """
        @media screen {
          .test-stacked-full-cover {
            position: fixed; inset: 0; z-index: 2147483646;
            pointer-events: none; background: #fff;
          }
          .test-stacked-tiny-decoration {
            position: fixed; left: 50vw; top: 50vh; width: 2px; height: 2px;
            transform: translate(-50%, -50%); z-index: 2147483647;
            pointer-events: none; background: #f0f;
          }
        }
        """
    else:
        css = """
        @media screen {
          body::before {
            content: ''; position: fixed; inset: 0; z-index: 2147483646;
            pointer-events: none; background: #fff;
          }
          .srcc-one-pager { position: relative; }
          .srcc-one-pager::after {
            content: ''; position: absolute; left: 0; top: 0;
            width: 2px; height: 2px;
            z-index: 2147483647; pointer-events: none; background: #f0f;
          }
        }
        """
    result = _run_summary_cell(_append_test_css(document, css))
    failures = _failed_assertion_names(result)
    expected = {
        "one_pager_visible",
        "one_pager_text_contrast",
        "one_pager_boundary_contrast",
        "one_pager_screen_content_visible",
    }

    assert expected <= failures, {
        "missing": sorted(expected - failures),
        "observed_failures": sorted(failures),
    }


@pytest.mark.parametrize(
    "declarations",
    (
        "box-shadow: inset 0 0 0 1px #fff;",
        "box-shadow: 10000px 0 0 #fff;",
        "box-sizing: border-box; border: 1px solid #fff;",
        "outline: 1px solid #fff; outline-offset: -1px;",
        "outline: 1px solid #000; outline-offset: -360px;",
        "outline: 400px solid #000; outline-offset: 0;",
        "box-sizing: border-box; border: 100vmax solid color(display-p3 1 1 1 / 0);",
        "outline: 100vmax solid color(display-p3 1 1 1 / 0); outline-offset: -100vmax;",
        "box-sizing: border-box; border: 100vmax solid oklab(.8 0 0 / 0);",
    ),
    ids=(
        "thin-inset-shadow",
        "offscreen-outer-shadow",
        "thin-border",
        "thin-outline",
        "thin-centered-outline",
        "outward-only-outline",
        "transparent-css-color-4-border",
        "transparent-css-color-4-outline",
        "transparent-css-color-4-oklab-border",
    ),
)
def test_summary_browser_collector_contract_accepts_non_occluding_edge_paint(
    declarations,
):
    document = _with_pointer_transparent_paint_cover(
        _synthetic_brief("complete"),
        declarations,
    )

    result = _run_summary_cell(document)
    failures = _failed_assertion_names(result)
    expected_green = {
        "one_pager_visible",
        "one_pager_text_contrast",
        "one_pager_boundary_contrast",
        "one_pager_screen_content_visible",
    }

    assert expected_green.isdisjoint(failures), sorted(failures)


@pytest.mark.parametrize(
    "declarations",
    (
        "box-shadow: 0 0 0 100vmax rgba(255, 255, 255, 0);",
        "border: 100vmax solid rgba(255, 255, 255, 0);",
        "outline: 100vmax solid rgba(255, 255, 255, 0); outline-offset: 0;",
        "box-shadow: 0 0 0 1px #fff;",
        "border: 1px solid #fff;",
        "outline: 1px solid #fff; outline-offset: 0;",
    ),
    ids=(
        "transparent-outward-shadow",
        "transparent-outward-border",
        "transparent-outward-outline",
        "tiny-outward-shadow",
        "tiny-outward-border",
        "tiny-outward-outline",
    ),
)
def test_summary_browser_collector_contract_accepts_non_occluding_tiny_outward_paint(
    declarations,
):
    result = _run_summary_cell(
        _with_tiny_outward_real_paint_cover(
            _synthetic_brief("complete"),
            declarations,
            below_fold=False,
        )
    )
    failures = _failed_assertion_names(result)
    expected_green = {
        "one_pager_visible",
        "one_pager_text_contrast",
        "one_pager_boundary_contrast",
        "one_pager_screen_content_visible",
    }

    assert expected_green.isdisjoint(failures), sorted(failures)


def test_summary_browser_collector_contract_rejects_outward_paint_with_base_off_viewport():
    document = _append_test_css(
        _with_tiny_outward_real_paint_cover(
            _synthetic_brief("complete"),
            "box-shadow: 0 0 0 100vmax #fff;",
            below_fold=False,
        ),
        """
        @media screen {
          .test-tiny-outward-paint-cover {
            left: -3px;
            top: 50vh;
            transform: none;
          }
        }
        """,
    )
    result = _run_summary_cell(document)
    failures = _failed_assertion_names(result)
    expected = {
        "one_pager_visible",
        "one_pager_text_contrast",
        "one_pager_boundary_contrast",
        "one_pager_screen_content_visible",
    }

    assert expected <= failures, {
        "missing": sorted(expected - failures),
        "observed_failures": sorted(failures),
    }


def test_summary_browser_collector_contract_accepts_outward_border_painted_off_summary():
    document = _append_test_css(
        _with_tiny_outward_real_paint_cover(
            _synthetic_brief("complete"),
            "border: 100vmax solid #fff;",
            below_fold=False,
        ),
        """
        @media screen {
          .test-tiny-outward-paint-cover {
            left: calc(100vw - 1px);
            top: calc(100vh - 1px);
            transform: none;
          }
        }
        """,
    )
    result = _run_summary_cell(document)
    failures = _failed_assertion_names(result)
    expected_green = {
        "one_pager_visible",
        "one_pager_text_contrast",
        "one_pager_boundary_contrast",
        "one_pager_screen_content_visible",
    }

    assert expected_green.isdisjoint(failures), sorted(failures)


def test_summary_browser_collector_contract_accepts_scroll_reachable_summary():
    document = _append_test_css(
        _wrap_one_pager_in_test_scroll(_synthetic_brief("complete")),
        """
        @media screen {
          .test-scroll { height: 100px !important; overflow: auto !important; }
          .test-spacer { height: 200px !important; }
        }
        """,
    )

    result = _run_summary_cell(document)
    failures = _failed_assertion_names(result)
    expected_green = {
        "one_pager_visible",
        "one_pager_text_contrast",
        "one_pager_boundary_contrast",
        "one_pager_screen_content_visible",
        "one_pager_forced_colors_non_color_cue",
    }

    assert not expected_green & failures, {
        "unexpected": sorted(expected_green & failures),
        "observed_failures": sorted(failures),
    }


@pytest.mark.parametrize(
    "selector",
    (
        "[data-section='one-pager-provenance']",
        ".srcc-blockers",
        "[data-section='one-pager-scenarios']",
        "[data-section='one-pager-handoff']",
    ),
)
def test_summary_browser_collector_contract_rejects_print_only_hidden_content(
    selector,
):
    document = _append_test_css(
        _synthetic_brief("complete"),
        f"@media print {{ body.srcc-html-document .srcc-one-pager {selector} {{ display: none !important; }} }}",
    )
    result = _run_summary_cell(document)

    assert "one_pager_print_content_visible" in _failed_assertion_names(result)


@pytest.mark.parametrize(
    ("css", "expected_assertion"),
    (
        (
            "@media print { body.srcc-html-document .srcc-one-pager p { color: #bbb !important; background: #fff !important; } }",
            "one_pager_print_text_contrast",
        ),
        (
            "@media print { body.srcc-html-document .srcc-one-pager-grid { background: #fff !important; } body.srcc-html-document .srcc-one-pager-card { border-color: #fff !important; } }",
            "one_pager_print_boundary_contrast",
        ),
    ),
)
def test_summary_browser_collector_contract_rejects_print_only_contrast_loss(
    css,
    expected_assertion,
):
    result = _run_summary_cell(_append_test_css(_synthetic_brief("complete"), css))

    assert expected_assertion in _failed_assertion_names(result)


@pytest.mark.parametrize(
    "selector",
    (
        "body.srcc-html-document .srcc-one-pager",
        (
            "body.srcc-html-document .srcc-one-pager "
            "[data-section='one-pager-provenance']"
        ),
        "body.srcc-html-document .srcc-one-pager .srcc-state",
    ),
    ids=("root", "provenance", "state-labels"),
)
def test_summary_browser_collector_contract_rejects_forced_colors_border_loss(
    selector,
):
    document = _append_test_css(
        _synthetic_brief("complete"),
        f"""
@media (forced-colors: active) {{
  {selector} {{
    border: 0 !important;
    outline: 0 !important;
  }}
}}
""",
    )
    result = _run_summary_cell(document)

    assert "one_pager_forced_colors_non_color_cue" in _failed_assertion_names(result)


def test_summary_browser_collector_contract_rejects_transparent_forced_colors_cues():
    document = _append_test_css(
        _synthetic_brief("complete"),
        """
@media (forced-colors: active) {
  body.srcc-html-document .srcc-one-pager,
  body.srcc-html-document .srcc-one-pager .srcc-state,
  body.srcc-html-document .srcc-one-pager [data-section='one-pager-provenance'] {
    forced-color-adjust: none !important;
    border-color: transparent !important;
    outline-color: transparent !important;
  }
}
""",
    )
    result = _run_summary_cell(document)

    assert "one_pager_forced_colors_non_color_cue" in _failed_assertion_names(result)


def test_summary_browser_collector_contract_rejects_wrong_real_zoom_geometry(
    monkeypatch,
):
    original = browser_gate._chromium_zoom_preferences
    monkeypatch.setattr(
        browser_gate,
        "_chromium_zoom_preferences",
        lambda *, host, zoom: original(host=host, zoom=2),
    )

    result = _run_summary_cell(_synthetic_brief("complete"))

    assert "actual_browser_zoom" in _failed_assertion_names(result)


def test_summary_browser_collector_contract_aborts_external_origin_injection():
    document = _replace_once(
        _synthetic_brief("complete"),
        b"img-src 'none'",
        b"img-src http:",
    )
    document = _replace_once(
        document,
        b"</header><section data-section=\"one-pager-answers\">",
        (
            b'<img src="http://127.0.0.1:9/external.png" alt="external">'
            b"</header><section data-section=\"one-pager-answers\">"
        ),
    )

    result = _run_summary_cell(document)

    assert "no_remote_requests" in _failed_assertion_names(result)


def _run_actual_browser_page(document: bytes, operation):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        executable = browser_gate.find_chrome_executable()
        if executable is None:
            executable = Path(playwright.chromium.executable_path)
        browser = playwright.chromium.launch(
            executable_path=str(executable), headless=True
        )
        try:
            return browser_gate._run_page_in_context(
                browser,
                width=1280,
                height=720,
                operation=lambda page: (
                    page.set_content(document.decode("utf-8"), wait_until="load"),
                    operation(page),
                )[1],
            )
        finally:
            browser.close()


def test_media_css_settlement_proves_each_observed_transition_and_cleans_probe():
    transitions = (
        (
            {"media": "screen", "forced_colors": "active", "reduced_motion": "no-preference"},
            {"media": "screen", "forced_colors": "active", "reduced_motion": "no-preference"},
        ),
        (
            {"media": "screen", "forced_colors": "none", "reduced_motion": "reduce"},
            {"media": "screen", "forced_colors": "none", "reduced_motion": "reduce"},
        ),
        (
            {"media": "print", "forced_colors": "none", "reduced_motion": "reduce"},
            {"media": "print", "forced_colors": "none", "reduced_motion": "reduce"},
        ),
    )

    def observe(page):
        evidence = []
        for requested, expected_computed in transitions:
            evidence.append(
                browser_gate._settle_media_css(
                    page,
                    **requested,
                    viewport="1280x720",
                    boundary_selector=".srcc-boundary, .boundary",
                    provenance_selector=".srcc-advanced-evidence, .advanced-evidence",
                )
            )
            assert not page.evaluate(
                "Boolean(document.querySelector('#srcc-media-settlement-probe, #srcc-media-settlement-style'))"
            )
        return evidence

    evidence = _run_actual_browser_page(_synthetic_brief("complete"), observe)

    assert [item["computed_probe"] for item in evidence] == [
        expected for _, expected in transitions
    ]
    for item, (_, expected) in zip(evidence, transitions):
        for target_name in ("boundary", "provenance"):
            assert {
                key: item["targets"][target_name][key]
                for key in ("media", "forced_colors", "reduced_motion")
            } == expected
    assert [item["match_media"] for item in evidence] == [
        {"print": False, "forced_colors": True, "reduced_motion": False},
        {"print": False, "forced_colors": False, "reduced_motion": True},
        {"print": True, "forced_colors": False, "reduced_motion": True},
    ]
    assert all(item["viewport"] == "1280x720" for item in evidence)
    assert all(item["browser_version"] for item in evidence)


def test_media_css_settlement_timeout_fails_closed_with_diagnostics_and_cleanup():
    sabotaged = _append_test_css(
        _synthetic_brief("complete"),
        """
html body #srcc-media-settlement-probe {
    --srcc-media-type: stale !important;
}
@media print {
    .srcc-boundary {
        opacity: 0 !important;
        transition: none !important;
        animation: none !important;
    }
    .srcc-advanced-evidence {
        visibility: hidden !important;
        transition: none !important;
        animation: none !important;
    }
}
""",
    )

    def observe(page):
        with pytest.raises(RuntimeError) as captured:
            browser_gate._settle_media_css(
                page,
                media="print",
                forced_colors="none",
                reduced_motion="reduce",
                viewport="1280x720",
                boundary_selector=".srcc-boundary, .boundary",
                provenance_selector=".srcc-advanced-evidence, .advanced-evidence",
                timeout_ms=100,
            )
        assert not page.evaluate(
            "Boolean(document.querySelector('#srcc-media-settlement-probe, #srcc-media-settlement-style'))"
        )
        return str(captured.value)

    diagnostic = _run_actual_browser_page(sabotaged, observe)

    assert "HTML brief media/CSS settlement failed" in diagnostic
    assert "expected" in diagnostic
    assert "'media': 'print'" in diagnostic
    assert "'print': True" in diagnostic
    assert "'media': 'stale'" in diagnostic
    assert "boundary" in diagnostic
    assert "'opacity': '0'" in diagnostic
    assert "provenance" in diagnostic
    assert "'visibility': 'hidden'" in diagnostic
    assert "'viewport': '1280x720'" in diagnostic
    assert "browser_version" in diagnostic


def test_evaluator_accepts_the_complete_typed_contract():
    result, assertions = _assertion_map(_complete_observation())

    assert REQUIRED_OBSERVATION_KEYS == tuple(_complete_observation())
    assert set(assertions) == ASSERTION_NAMES
    assert result.state == "complete"
    assert result.viewport == "1280x720"
    assert result.passed
    assert all(assertion.evidence for assertion in result.assertions)


@pytest.mark.parametrize(
    ("assertion_name", "changes"),
    (
        ("actual_browser_zoom", {"requested_zoom": 3}),
        ("actual_browser_zoom", {"actual_browser_zoom": False}),
        ("one_pager_visible", {"one_pager_visible": False}),
        ("one_pager_before_overview", {"one_pager_before_overview": False}),
        ("semantic_landmarks", {"header_count": 1}),
        ("semantic_landmarks", {"header_count": 3}),
        ("semantic_landmarks", {"page_header_count": 0}),
        ("semantic_landmarks", {"page_header_count": 2}),
        ("semantic_landmarks", {"one_pager_header_count": 0}),
        ("semantic_landmarks", {"one_pager_header_count": 2}),
        ("one_pager_structure", {"one_pager_heading_count": 7}),
        ("one_pager_structure", {"one_pager_section_count": 6}),
        ("one_pager_lists", {"one_pager_answer_item_count": 3}),
        ("one_pager_lists", {"one_pager_scenario_item_count": 2}),
        (
            "one_pager_state_truth",
            {"one_pager_state_tokens": ("caller-supplied-pass=true",)},
        ),
        (
            "one_pager_state_role_integrity",
            {"one_pager_state_role_count": len(SYNTHETIC_STATE_ROLES) - 1},
        ),
        (
            "one_pager_state_role_integrity",
            {"one_pager_unique_state_role_count": len(SYNTHETIC_STATE_ROLES) - 1},
        ),
        (
            "one_pager_share_basis_disclosure",
            {
                "one_pager_share_basis_tokens": (
                    "scenarios-base-share-basis=available",
                )
            },
        ),
        (
            "one_pager_provenance_caption_visible",
            {"one_pager_provenance_caption_visible": False},
        ),
        ("one_pager_text_contrast", {"one_pager_min_text_contrast_ratio": 4.49}),
        (
            "one_pager_boundary_contrast",
            {"one_pager_min_boundary_contrast_ratio": 2.99},
        ),
        ("one_pager_no_overflow", {"one_pager_overflow_px": 1.01}),
        (
            "one_pager_no_descendant_overflow",
            {"one_pager_max_descendant_overflow_px": 1.01},
        ),
        (
            "one_pager_screen_content_visible",
            {"one_pager_provenance_visible": False},
        ),
        (
            "one_pager_screen_content_visible",
            {"one_pager_blockers_visible": False},
        ),
        (
            "one_pager_screen_content_visible",
            {"one_pager_assumptions_visible": False},
        ),
        (
            "one_pager_screen_content_visible",
            {"one_pager_handoff_visible": False},
        ),
        (
            "one_pager_forced_colors_non_color_cue",
            {"one_pager_forced_colors_non_color_cue": False},
        ),
        (
            "one_pager_print_text_contrast",
            {"one_pager_print_min_text_contrast_ratio": 4.49},
        ),
        (
            "one_pager_print_boundary_contrast",
            {"one_pager_print_min_boundary_contrast_ratio": 2.99},
        ),
        (
            "one_pager_print_content_visible",
            {"one_pager_print_provenance_visible": False},
        ),
        (
            "one_pager_print_content_visible",
            {"one_pager_print_blockers_visible": False},
        ),
        (
            "one_pager_print_content_visible",
            {"one_pager_print_assumptions_visible": False},
        ),
        (
            "one_pager_print_content_visible",
            {"one_pager_print_handoff_visible": False},
        ),
    ),
)
def test_observation_contract_rejects_each_summary_defect(assertion_name, changes):
    observation = _complete_observation()
    observation.update(changes)

    result, assertions = _assertion_map(observation)

    assert not result.passed
    assert not assertions[assertion_name].passed


@pytest.mark.parametrize("state", ("complete", "partial", "stale", "withheld"))
def test_observation_contract_binds_state_to_independent_literal_role_tokens(state):
    observation = _complete_observation()
    observation.update(
        state=state,
        one_pager_state_tokens=SYNTHETIC_EXPECTED_STATE_ROLE_TOKENS[state],
    )

    result, assertions = _assertion_map(observation)

    assert result.passed
    relabeled = {**observation, "state": "withheld" if state != "withheld" else "complete"}
    _, relabeled_assertions = _assertion_map(relabeled)
    assert relabeled_assertions["one_pager_state_truth"].passed is False


@pytest.mark.parametrize(
    ("key", "wrong_value"),
    (
        ("requested_zoom", 1.0),
        ("actual_browser_zoom", 1),
        ("page_header_count", True),
        ("one_pager_header_count", 1.0),
        ("one_pager_visible", 1),
        ("one_pager_before_overview", "true"),
        ("one_pager_heading_count", 8.0),
        ("one_pager_section_count", True),
        ("one_pager_answer_item_count", 4.0),
        ("one_pager_scenario_item_count", False),
        ("one_pager_state_tokens", list(SYNTHETIC_EXPECTED_STATE_ROLE_TOKENS["complete"])),
        ("one_pager_share_basis_tokens", list(SYNTHETIC_EXPECTED_SHARE_BASIS_TOKENS)),
        ("one_pager_state_node_count", 37.0),
        ("one_pager_state_role_count", True),
        ("one_pager_unique_state_role_count", "37"),
        ("one_pager_provenance_caption_visible", 1),
        ("one_pager_min_text_contrast_ratio", 7),
        ("one_pager_min_boundary_contrast_ratio", 3),
        ("one_pager_overflow_px", 0),
        ("one_pager_max_descendant_overflow_px", 0),
        ("one_pager_provenance_visible", 1),
        ("one_pager_blockers_visible", "true"),
        ("one_pager_assumptions_visible", None),
        ("one_pager_handoff_visible", 1),
        ("one_pager_forced_colors_non_color_cue", 1),
        ("one_pager_print_min_text_contrast_ratio", 21),
        ("one_pager_print_min_boundary_contrast_ratio", 21),
        ("one_pager_print_provenance_visible", 1),
        ("one_pager_print_blockers_visible", "true"),
        ("one_pager_print_assumptions_visible", None),
        ("one_pager_print_handoff_visible", 1),
    ),
)
def test_observation_contract_requires_exact_new_field_types(key, wrong_value):
    observation = _complete_observation()
    observation[key] = wrong_value

    result, assertions = _assertion_map(observation)

    assert not result.passed
    assert assertions["observation_complete"].passed is False


@pytest.mark.parametrize(
    ("assertion_name", "changes"),
    (
        ("one_h1", {"h1_count": 2}),
        ("semantic_landmarks", {"main_count": 0}),
        ("logical_headings", {"heading_levels": (1, 3)}),
        ("skip_focus", {"skip_target_focused": False}),
        ("visible_focus", {"visible_focus": False}),
        ("tables_captioned", {"captioned_table_count": 0}),
        ("csp_exact", {"csp": "default-src 'none'"}),
        ("no_script", {"script_count": 1}),
        ("no_event_handlers", {"event_handler_count": 1}),
        ("no_forms", {"form_count": 1}),
        ("no_iframes", {"iframe_count": 1}),
        ("no_remote_requests", {"remote_request_count": 1}),
        ("research_boundary_visible", {"boundary_visible": False}),
        ("blockers_visible", {"blockers_visible": False}),
        ("provenance_visible", {"provenance_visible": False}),
        ("no_overflow", {"overflow_px": 1.01}),
        ("forced_colors_non_color_cue", {"forced_colors_non_color_cue": False}),
        ("reduced_motion_static", {"reduced_motion_static": False}),
        ("print_boundary_visible", {"print_boundary_visible": False}),
        ("print_provenance_visible", {"print_provenance_visible": False}),
        ("no_console_errors", {"console_errors": ("console failed",)}),
        ("no_page_errors", {"page_errors": ("page failed",)}),
        ("pdf_in_memory", {"pdf_header": "not-pdf"}),
        ("pdf_in_memory", {"pdf_byte_length": 0}),
    ),
)
def test_each_observed_defect_fails_its_named_assertion(assertion_name, changes):
    observation = _complete_observation()
    observation.update(changes)

    result, assertions = _assertion_map(observation)

    assert not result.passed
    assert not assertions[assertion_name].passed


@pytest.mark.parametrize("missing_key", tuple(_complete_observation()))
def test_each_missing_observation_fails_closed(missing_key):
    observation = _complete_observation()
    del observation[missing_key]

    result, assertions = _assertion_map(observation)

    assert not result.passed
    assert not assertions["observation_complete"].passed
    assert all(
        not assertions[name].passed for name in DEPENDENT_ASSERTIONS[missing_key]
    )


@pytest.mark.parametrize(
    ("key", "wrong_value"),
    (
        ("state", 1),
        ("viewport", None),
        ("h1_count", True),
        ("header_count", 1.0),
        ("main_count", "1"),
        ("footer_count", False),
        ("section_count", 2.0),
        ("heading_levels", [1, 2]),
        ("skip_target_focused", 1),
        ("visible_focus", "yes"),
        ("table_count", True),
        ("captioned_table_count", 1.0),
        ("csp", None),
        ("script_count", False),
        ("event_handler_count", 0.0),
        ("form_count", "0"),
        ("iframe_count", None),
        ("remote_request_count", False),
        ("boundary_visible", 1),
        ("blockers_visible", "true"),
        ("provenance_visible", None),
        ("overflow_px", 0),
        ("forced_colors_non_color_cue", 1),
        ("reduced_motion_static", "true"),
        ("print_boundary_visible", 1),
        ("print_provenance_visible", None),
        ("console_errors", []),
        ("page_errors", (1,)),
        ("pdf_byte_length", True),
        ("pdf_header", b"%PDF"),
    ),
)
def test_each_wrong_typed_observation_fails_closed(key, wrong_value):
    observation = _complete_observation()
    observation[key] = wrong_value

    result, assertions = _assertion_map(observation)

    assert not result.passed
    assert not assertions["observation_complete"].passed
    assert all(not assertions[name].passed for name in DEPENDENT_ASSERTIONS[key])


def test_repository_fingerprint_detects_tracked_untracked_delete_and_rename(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    tracked = tmp_path / "tracked.txt"
    tracked.write_text("first", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=tmp_path, check=True)
    initial = repository_fingerprint(tmp_path)

    tracked.write_text("second", encoding="utf-8")
    tracked_changed = repository_fingerprint(tmp_path)
    assert tracked_changed != initial

    untracked = tmp_path / "visible.txt"
    untracked.write_text("one", encoding="utf-8")
    untracked_added = repository_fingerprint(tmp_path)
    assert untracked_added != tracked_changed
    untracked.write_text("two", encoding="utf-8")
    untracked_changed = repository_fingerprint(tmp_path)
    assert untracked_changed != untracked_added

    tracked.unlink()
    deleted = repository_fingerprint(tmp_path)
    assert deleted != untracked_changed

    untracked.rename(tmp_path / "renamed.txt")
    renamed = repository_fingerprint(tmp_path)
    assert renamed != deleted


def test_repository_fingerprint_hashes_link_type_and_target(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "target-a").write_text("same", encoding="utf-8")
    (tmp_path / "target-b").write_text("same", encoding="utf-8")
    link = tmp_path / "visible-link"
    link.symlink_to("target-a")
    before = repository_fingerprint(tmp_path)

    link.unlink()
    link.symlink_to("target-b")

    assert repository_fingerprint(tmp_path) != before


def test_repository_fingerprint_detects_executable_bit_changes(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    executable = tmp_path / "tracked-tool"
    executable.write_bytes(b"same bytes")
    executable.chmod(0o644)
    subprocess.run(["git", "add", "tracked-tool"], cwd=tmp_path, check=True)
    before = repository_fingerprint(tmp_path)

    executable.chmod(0o755)

    assert repository_fingerprint(tmp_path) != before


def _packet_results():
    results = []
    for state in ("complete", "partial", "stale", "withheld"):
        for width, height, zoom in browser_gate.HTML_BRIEF_BROWSER_CELLS:
            observation = _complete_observation()
            observation.update(
                state=state,
                viewport=f"{width}x{height}",
                requested_zoom=zoom,
                actual_browser_zoom=True,
                one_pager_state_tokens=(
                    SYNTHETIC_EXPECTED_STATE_ROLE_TOKENS[state]
                ),
            )
            results.append(evaluate_html_brief_observation(observation))
    return results


def _packet_source_paths(directory: Path) -> dict[str, Path]:
    supplied = {
        "src/company_workbench_html.py": b"renderer source\n",
        "src/company_workbench_html_browser_gate.py": b"gate source\n",
        "tests/test_company_workbench_html_browser_gate.py": b"test source\n",
    }
    paths = {}
    for index, (label, payload) in enumerate(supplied.items()):
        path = directory / f"source-{index}.py"
        path.write_bytes(payload)
        paths[label] = path
    return paths


def test_result_packet_contract_builds_exact_hashed_24_cell_schema(tmp_path):
    from src.company_workbench_html_browser_gate import (
        build_html_brief_browser_result_packet,
    )

    documents = {
        state: _synthetic_brief(state)
        for state in ("complete", "partial", "stale", "withheld")
    }
    source_paths = _packet_source_paths(tmp_path)

    results_payload, source_payload = build_html_brief_browser_result_packet(
        _packet_results(),
        input_documents=documents,
        source_paths=source_paths,
    )

    assert results_payload["schema_version"] == 1
    assert results_payload["verdict"] == "passed"
    assert results_payload["passed_cells"] == 24
    assert results_payload["total_cells"] == 24
    assert len(results_payload["cells"]) == 24
    assert len(
        {
            (cell["state"], cell["viewport"], cell["zoom"])
            for cell in results_payload["cells"]
        }
    ) == 24
    assert {
        item["state"]: item["sha256"]
        for item in results_payload["input_documents"]
    } == {
        state: hashlib.sha256(payload).hexdigest()
        for state, payload in documents.items()
    }
    assert source_payload == {
        "schema_version": 1,
        "sources": [
            {
                "path": label,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            for label, path in sorted(source_paths.items())
        ],
    }
    assert all(
        cell["assertions"]
        and all(
            set(assertion) == {"name", "passed", "evidence"}
            for assertion in cell["assertions"]
        )
        for cell in results_payload["cells"]
    )


def test_result_packet_contract_writes_deterministic_exact_files(tmp_path):
    from src.company_workbench_html_browser_gate import (
        write_html_brief_browser_result_packet,
    )

    documents = {
        state: _synthetic_brief(state)
        for state in ("complete", "partial", "stale", "withheld")
    }
    source_paths = _packet_source_paths(tmp_path)
    with tempfile.TemporaryDirectory(prefix="packet-a-", dir="/tmp") as first_dir:
        first = write_html_brief_browser_result_packet(
            Path(first_dir),
            _packet_results(),
            input_documents=documents,
            source_paths=source_paths,
        )
        first_bytes = {
            path.name: path.read_bytes() for path in first
        }
    with tempfile.TemporaryDirectory(prefix="packet-b-", dir="/tmp") as second_dir:
        second = write_html_brief_browser_result_packet(
            Path(second_dir),
            tuple(reversed(_packet_results())),
            input_documents=dict(reversed(tuple(documents.items()))),
            source_paths=dict(reversed(tuple(source_paths.items()))),
        )
        second_bytes = {
            path.name: path.read_bytes() for path in second
        }

    assert set(first_bytes) == set(second_bytes) == {
        "results.json",
        "source-hashes.json",
    }
    assert first_bytes == second_bytes
    assert all(payload.endswith(b"\n") for payload in first_bytes.values())


def test_result_packet_contract_rejects_outside_tmp_and_nonempty_directory(tmp_path):
    from src.company_workbench_html_browser_gate import (
        write_html_brief_browser_result_packet,
    )

    documents = {
        state: _synthetic_brief(state)
        for state in ("complete", "partial", "stale", "withheld")
    }
    source_paths = _packet_source_paths(tmp_path)
    with pytest.raises(ValueError, match="/tmp"):
        write_html_brief_browser_result_packet(
            Path("/"),
            _packet_results(),
            input_documents=documents,
            source_paths=source_paths,
        )
    missing = Path("/tmp") / "stock-research-packet-missing-contract"
    assert not missing.exists()
    with pytest.raises(ValueError, match="existing"):
        write_html_brief_browser_result_packet(
            missing,
            _packet_results(),
            input_documents=documents,
            source_paths=source_paths,
        )
    with tempfile.TemporaryDirectory(prefix="packet-nonempty-", dir="/tmp") as directory:
        output = Path(directory)
        (output / "already-present").write_text("owned", encoding="utf-8")
        with pytest.raises(ValueError, match="empty"):
            write_html_brief_browser_result_packet(
                output,
                _packet_results(),
                input_documents=documents,
                source_paths=source_paths,
            )
        assert [path.name for path in output.iterdir()] == ["already-present"]


@pytest.mark.parametrize("mutation", ("missing", "duplicate", "unexpected"))
def test_result_packet_contract_rejects_invalid_cell_set_before_write(
    tmp_path,
    mutation,
):
    from src.company_workbench_html_browser_gate import (
        write_html_brief_browser_result_packet,
    )

    results = _packet_results()
    if mutation == "missing":
        results.pop()
    elif mutation == "duplicate":
        results[-1] = results[0]
    else:
        results[-1] = browser_gate.HtmlBriefBrowserResult(
            "unexpected",
            results[-1].viewport,
            results[-1].zoom,
            results[-1].assertions,
        )
    documents = {
        state: _synthetic_brief(state)
        for state in ("complete", "partial", "stale", "withheld")
    }
    source_paths = _packet_source_paths(tmp_path)
    with tempfile.TemporaryDirectory(prefix="packet-invalid-", dir="/tmp") as directory:
        output = Path(directory)
        with pytest.raises(ValueError, match="cell"):
            write_html_brief_browser_result_packet(
                output,
                results,
                input_documents=documents,
                source_paths=source_paths,
            )
        assert list(output.iterdir()) == []


def test_repository_fingerprint_distinguishes_regular_fifo_and_socket():
    if not hasattr(os, "mkfifo") or not hasattr(socket, "AF_UNIX"):
        pytest.skip(
            "FIFO and Unix-domain socket nodes are unavailable on this platform"
        )
    with tempfile.TemporaryDirectory(prefix="hb-", dir="/tmp") as directory:
        repo = Path(directory)
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        special = repo / "node"
        special.write_bytes(b"ordinary")
        subprocess.run(["git", "add", "node"], cwd=repo, check=True)
        regular = repository_fingerprint(repo)

        special.unlink()
        os.mkfifo(special)
        fifo = repository_fingerprint(repo)

        special.unlink()
        unix_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            unix_socket.bind(str(special))
            socket_node = repository_fingerprint(repo)
        finally:
            unix_socket.close()
            if special.exists():
                special.unlink()

    assert regular != fifo
    assert fifo != socket_node


def test_page_context_cleanup_survives_page_close_failure():
    class Page:
        def close(self):
            raise RuntimeError("page close failed")

    class Context:
        def __init__(self):
            self.closed = False

        def new_page(self):
            return Page()

        def close(self):
            self.closed = True

    class Browser:
        def __init__(self):
            self.context = Context()

        def new_context(self, *, viewport):
            assert viewport == {"width": 390, "height": 844}
            return self.context

    browser = Browser()

    with pytest.raises(RuntimeError, match="page close failed"):
        browser_gate._run_page_in_context(
            browser,
            width=390,
            height=844,
            operation=lambda page: "observed",
        )

    assert browser.context.closed


def test_page_context_cleanup_survives_new_page_failure():
    class Context:
        def __init__(self):
            self.closed = False

        def new_page(self):
            raise RuntimeError("new page failed")

        def close(self):
            self.closed = True

    class Browser:
        def __init__(self):
            self.context = Context()

        def new_context(self, *, viewport):
            return self.context

    browser = Browser()

    with pytest.raises(RuntimeError, match="new page failed"):
        browser_gate._run_page_in_context(
            browser,
            width=1280,
            height=720,
            operation=lambda page: "unreachable",
        )

    assert browser.context.closed


def test_actual_browser_matrix_accepts_injected_bytes_without_writing_repo():
    cases = {
        state: _synthetic_brief(state)
        for state in ("complete", "partial", "stale", "withheld")
    }

    results = run_company_workbench_html_browser_gate(cases, repo_root=Path.cwd())

    assert len(results) == 24
    assert {(result.state, result.viewport, result.zoom) for result in results} == {
        (state, f"{width}x{height}", zoom)
        for state in cases
        for width, height, zoom in browser_gate.HTML_BRIEF_BROWSER_CELLS
    }
    assert all(result.passed for result in results), [
        (
            result.state,
            result.viewport,
            result.zoom,
            [a for a in result.assertions if not a.passed],
        )
        for result in results
        if not result.passed
    ]
    output_directory = os.environ.get("HTML_BRIEF_BROWSER_OUTPUT_DIR")
    if output_directory:
        root = Path.cwd()
        packet_paths = browser_gate.write_html_brief_browser_result_packet(
            Path(output_directory),
            results,
            input_documents=cases,
            source_paths={
                label: root / label
                for label in browser_gate.HTML_BRIEF_BROWSER_SOURCE_PATHS
            },
        )
        assert tuple(path.name for path in packet_paths) == (
            "results.json",
            "source-hashes.json",
        )


def test_actual_browser_rejects_opacity_clipping_offscreen_and_print_hiding():
    original = _synthetic_brief("complete")
    cases = {
        "boundary-opacity": _append_test_css(
            original, ".srcc-boundary { opacity: 0 !important; }"
        ),
        "provenance-ancestor-clipped": _append_test_css(
            original,
            ".srcc-html-document main { height: 1px !important; overflow: hidden !important; }",
        ),
        "provenance-offscreen": _append_test_css(
            original,
            ".srcc-advanced-evidence { position: fixed !important; left: -10000px !important; top: 0 !important; }",
        ),
        "print-boundary-opacity": _append_test_css(
            original,
            "@media print { .srcc-boundary { opacity: 0 !important; } }",
        ),
        "print-provenance-offscreen": _append_test_css(
            original,
            "@media print { .srcc-advanced-evidence { position: fixed !important; left: -10000px !important; top: 0 !important; } }",
        ),
    }

    results = run_company_workbench_html_browser_gate(
        cases,
        repo_root=Path.cwd(),
        cells=((1280, 720, 1),),
    )
    failures = {
        (result.state, result.viewport): _failed_assertion_names(result)
        for result in results
    }

    for viewport in ("1280x720",):
        assert "research_boundary_visible" in failures[("boundary-opacity", viewport)]
        assert (
            "provenance_visible" in failures[("provenance-ancestor-clipped", viewport)]
        )
        assert "provenance_visible" in failures[("provenance-offscreen", viewport)]
        assert (
            "print_boundary_visible" in failures[("print-boundary-opacity", viewport)]
        )
        assert (
            "print_provenance_visible"
            in failures[("print-provenance-offscreen", viewport)]
        )


def test_actual_browser_rejects_transparent_clipped_and_offscreen_focus_cues():
    original = _synthetic_brief("complete")
    cases = {
        "focus-transparent": _append_test_css(
            original,
            ".srcc-skip-link:focus-visible { outline-style: none !important; box-shadow: 0 0 0 3px transparent !important; border-style: none !important; }",
        ),
        "focus-clipped": _append_test_css(
            original,
            ".srcc-skip-link:focus-visible { outline-width: 4px !important; outline-offset: 2px !important; clip-path: inset(0) !important; }",
        ),
        "focus-offscreen": _append_test_css(
            original, ".srcc-skip-link:focus-visible { top: -10000px !important; }"
        ),
    }

    results = run_company_workbench_html_browser_gate(
        cases,
        repo_root=Path.cwd(),
        cells=((1280, 720, 1),),
    )

    assert all("visible_focus" in _failed_assertion_names(result) for result in results)


def test_actual_browser_requires_a_focus_specific_change_and_rejects_overflow_clipping():
    original = _synthetic_brief("complete")
    cases = {
        "focus-static-border": _append_test_css(
            original,
            """
.srcc-skip-link { border: 3px solid #18222e !important; background: #ffffff !important; }
.srcc-skip-link:focus-visible { outline: none !important; box-shadow: none !important; }
""",
        ),
        "focus-overflow-auto": _wrap_skip_link_in_overflow(original, "auto"),
        "focus-overflow-scroll": _wrap_skip_link_in_overflow(original, "scroll"),
    }

    results = run_company_workbench_html_browser_gate(
        cases,
        repo_root=Path.cwd(),
        cells=((1280, 720, 1),),
    )

    assert all("visible_focus" in _failed_assertion_names(result) for result in results)


def test_actual_browser_allows_a_visible_focus_specific_inside_cue():
    inside_cue = _append_test_css(
        _synthetic_brief("complete"),
        """
.srcc-skip-link { border: 2px solid #18222e !important; background: #ffffff !important; outline: none !important; }
.srcc-skip-link:focus-visible { background: #ffe680 !important; box-shadow: inset 0 0 0 3px #9d2020 !important; outline: none !important; }
""",
    )

    results = run_company_workbench_html_browser_gate(
        {"complete": inside_cue},
        repo_root=Path.cwd(),
        cells=((1280, 720, 1),),
    )

    assert all(result.passed for result in results), [
        (result.viewport, _failed_assertion_names(result))
        for result in results
        if not result.passed
    ]


def test_actual_browser_rejects_fully_clipped_directional_focus_shadows():
    original = _synthetic_brief("complete")
    cases = {
        f"focus-shadow-{edge}-{overflow}": _directional_shadow_clipped_at_edge(
            original,
            overflow=overflow,
            edge=edge,
        )
        for edge in ("left", "right")
        for overflow in ("auto", "scroll")
    }

    results = run_company_workbench_html_browser_gate(
        cases,
        repo_root=Path.cwd(),
        cells=((1280, 720, 1),),
    )

    assert len(results) == 4
    assert all("visible_focus" in _failed_assertion_names(result) for result in results)


def test_actual_browser_rejects_unchanged_shadow_plus_unsupported_focus_addition():
    original = _synthetic_brief("complete")
    cases = {
        "focus-adds-blurred-shadow": _static_shadow_with_unsupported_focus_addition(
            original,
            added_shadow="0 0 4px 3px #177245",
        ),
        "focus-adds-transparent-shadow": _static_shadow_with_unsupported_focus_addition(
            original,
            added_shadow="0 0 0 3px transparent",
        ),
    }

    results = run_company_workbench_html_browser_gate(
        cases,
        repo_root=Path.cwd(),
        cells=((1280, 720, 1),),
    )

    assert len(results) == 2
    assert all("visible_focus" in _failed_assertion_names(result) for result in results)


def test_make_target_writes_only_a_fresh_tmp_result_packet():
    makefile = Path("Makefile").read_text(encoding="utf-8")
    target = makefile.split("company-workbench-html-browser-check:", 1)[1].split(
        "\n\n", 1
    )[0]

    assert "PYTHONDONTWRITEBYTECODE=1" in target
    assert (
        "python3 -m pytest -q -p no:cacheprovider "
        "tests/test_company_workbench_html_browser_gate.py"
        in target
    )
    assert "tests/test_company_workbench_html_browser_gate.py tests/" not in target
    assert "mktemp -d /tmp/stock-company-workbench-html-browser.XXXXXX" in target
    assert 'HTML_BRIEF_BROWSER_OUTPUT_DIR="$$packet_dir"' in target
    assert 'test -s "$$packet_dir/results.json"' in target
    assert 'test -s "$$packet_dir/source-hashes.json"' in target
    assert 'shasum -a 256 "$$packet"' in target
    assert "rm " not in target
    assert not any(
        option in target
        for option in ("--output", "--screenshot", "--json", "--html", "--pdf")
    )
