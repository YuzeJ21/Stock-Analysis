"""Pure helpers for the cross-page readiness-first research loop."""

from __future__ import annotations

import html

import pandas as pd

from src.data_health_console import DATA_HEALTH_OPERATOR_LANES


def _format_missing(value: object, fallback: str = "Not available") -> str:
    if value is None:
        return fallback
    try:
        if pd.isna(value):
            return fallback
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null", "<na>"}:
        return fallback
    return text


def _first_meaningful_text(*values: object, fallback: str = "Not available") -> str:
    for value in values:
        text = _format_missing(value, "")
        if text and text.lower() not in {"not available", "nan", "none", "null"}:
            return text
    return fallback


def _friendly_card_copy(text: object) -> str:
    normalized = _format_missing(text, "")
    replacements = {
        "import draft": "import file",
        "Import draft": "Import file",
        "staged flow": "import file flow",
        "Staged flow": "Import file flow",
    }
    for old, new in replacements.items():
        normalized = normalized.replace(old, new)
    return normalized


def research_loop_strip_html(
    *,
    current_step: str,
    previous_proof: str,
    next_action: str,
    stop_rule: str,
    current_note: str = "",
    proof_note: str = "",
    action_note: str = "",
    stop_note: str = "",
    current_href: str = "",
    proof_href: str = "",
    action_href: str = "",
    stop_href: str = "",
) -> str:
    """Compact cross-page orientation strip for the readiness-first research loop."""

    items = [
        ("Current step", current_step, current_note, "", current_href),
        ("Previous proof", previous_proof, proof_note, "", proof_href),
        ("Next safe action", next_action, action_note, "action", action_href),
        ("Stop rule", stop_rule, stop_note, "stop", stop_href),
    ]
    item_html = []
    for label, value, note, class_name, href in items:
        note_html = f"<div class='research-loop-note'>{html.escape(note)}</div>" if note else ""
        class_attr = f"research-loop-item {class_name}".strip()
        if href:
            safe_href = html.escape(href, quote=True)
            value_html = (
                "<div class='research-loop-value'>"
                f"<a class='research-loop-link' href='{safe_href}'>{html.escape(value)}</a>"
                "</div>"
            )
        else:
            value_html = f"<div class='research-loop-value'>{html.escape(value)}</div>"
        item_html.append(
            f"<div class='{class_attr}'>"
            f"<div class='research-loop-label'>{html.escape(label)}</div>"
            f"{value_html}"
            f"{note_html}"
            "</div>"
        )
    return "<div class='research-loop-strip'>" + "".join(item_html) + "</div>"


def home_research_loop_context(summary: dict[str, object], freshness: object) -> dict[str, str]:
    dcf_ready = int(summary.get("dcf_ready") or 0)
    peer_ready = int(summary.get("peer_ready") or 0)
    current_state = f"{int(summary.get('price_ready') or 0):,} price-ready / {dcf_ready:,} DCF-ready / {peer_ready:,} peer-ready"
    freshness_status = getattr(freshness, "status", "")
    proof_state = "Saved readiness snapshot is current" if freshness_status == "current" else "Saved readiness snapshot needs refresh"
    proof_note = "Use this snapshot before opening ticker pages." if freshness_status == "current" else str(getattr(freshness, "refresh_command", "make readiness"))
    next_action = "Open a Single-Stock Report"
    if dcf_ready <= 0:
        next_action = "Open Data Health source-proof lanes"
    return {
        "current_step": "Home readiness snapshot",
        "current_note": current_state,
        "current_href": "?mode=public",
        "previous_proof": proof_state,
        "proof_note": proof_note,
        "proof_href": "?mode=public&page=data-health&drawer=proof",
        "next_action": next_action,
        "action_href": "?mode=public&page=single-stock",
        "action_note": "Review one ticker, then route locked fields to Data Health.",
        "stop_rule": "Do not infer missing inputs",
        "stop_note": "Blocked, partial, and excluded states stay visible until source proof changes readiness.",
        "stop_href": "?mode=public&page=data-health&drawer=proof",
    }


def single_stock_research_loop_context(ticker: str, report_payload: dict[str, object] | None = None) -> dict[str, str]:
    ticker_label = _format_missing(ticker, "selected ticker").upper()
    if report_payload:
        readiness = report_payload.get("valuation_readiness", {})
        mode = _first_meaningful_text(
            report_payload.get("analysis_mode"),
            report_payload.get("mode"),
            report_payload.get("decision_subtype"),
            fallback="local report",
        )
        dcf_state = _format_missing(readiness.get("status") if isinstance(readiness, dict) else "", "")
        next_action = f"Open Data Health if {ticker_label} has locked fields"
        if dcf_state.lower() in {"ready", "excluded"}:
            next_action = "Read Best Review Path before detailed tabs"
        proof_note = "At A Glance and Reader Guide summarize ready, blocked, excluded, and monitor-only sections."
        return {
            "current_step": f"{ticker_label} report review",
            "current_note": f"Mode: {_format_missing(mode, 'local report')}",
            "current_href": "?mode=public&page=single-stock",
            "previous_proof": "Local readiness row and report payload",
            "proof_note": proof_note,
            "proof_href": "?mode=operator&page=data-health&lane=proof&drawer=proof",
            "next_action": next_action,
            "action_href": "?mode=operator&page=data-health&lane=fundamentals&drawer=queue"
            if "Data Health" in next_action
            else "",
            "action_note": "If a field is locked, continue in Data Health before trusting deeper analysis.",
            "stop_rule": "Do not read locked sections as conclusions",
            "stop_note": "Valuation, peers, metrics, earnings, and estimates stay withheld until trusted inputs exist.",
            "stop_href": "?mode=operator&page=data-health&lane=proof&drawer=proof",
        }
    return {
        "current_step": "Single-Stock Report",
        "current_note": f"Selected ticker: {ticker_label}",
        "current_href": "?mode=public&page=single-stock",
        "previous_proof": "Home readiness snapshot",
        "proof_note": "Use saved readiness counts to understand whether this ticker can support deeper review.",
        "proof_href": "?mode=public",
        "next_action": "Show Local Report",
        "action_href": "",
        "action_note": "Read At A Glance first; then use Data Health for any locked input.",
        "stop_rule": "No report, no interpretation",
        "stop_note": "Do not use optional online lookup or missing local rows as proof.",
        "stop_href": "?mode=public&page=data-health&drawer=proof",
    }


def data_health_research_loop_action_href(selected_lane_key: str, next_action: str, public_mode: bool) -> str:
    if public_mode:
        return "?mode=public&page=data-health&drawer=proof"
    next_text = str(next_action or "").lower()
    if next_text.startswith("make "):
        return ""
    if selected_lane_key == "metrics":
        return "?mode=operator&page=data-health&lane=metrics&drawer=metrics"
    if selected_lane_key == "proof":
        return "?mode=operator&page=data-health&lane=proof&drawer=proof"
    if selected_lane_key in DATA_HEALTH_OPERATOR_LANES:
        return f"?mode=operator&page=data-health&lane={selected_lane_key}&drawer=batch"
    return "?mode=operator&page=data-health"


def data_health_research_loop_context(
    *,
    selected_lane_key: str,
    readiness_freshness: object,
    next_action: str,
    public_mode: bool,
) -> dict[str, str]:
    lane_label = DATA_HEALTH_OPERATOR_LANES.get(selected_lane_key, DATA_HEALTH_OPERATOR_LANES["prices"])
    if public_mode:
        lane_label = "Public readiness summary"
    elif selected_lane_key != "proof":
        lane_label = f"{lane_label} ROUTE MAP; artifact hygiene before staging"
    freshness_status = getattr(readiness_freshness, "status", "")
    proof_state = "Readiness snapshot is current" if freshness_status == "current" else "Readiness snapshot needs refresh"
    current_href = (
        "?mode=public&page=data-health"
        if public_mode
        else f"?mode=operator&page=data-health&lane={selected_lane_key}"
    )
    proof_href = (
        "?mode=public&page=data-health&drawer=proof"
        if public_mode
        else "?mode=operator&page=data-health&lane=proof&drawer=proof"
    )
    current_step = "Proof lane shell" if selected_lane_key == "proof" else "Data Health source-proof lane"
    return {
        "current_step": current_step,
        "current_note": lane_label,
        "current_href": current_href,
        "previous_proof": proof_state,
        "proof_note": str(getattr(readiness_freshness, "message", "")),
        "proof_href": proof_href,
        "next_action": _friendly_card_copy(next_action),
        "action_href": data_health_research_loop_action_href(selected_lane_key, next_action, public_mode),
        "action_note": "Commands stay copy-only and collapsed; validate and preview before any reviewed apply step.",
        "stop_rule": "Stop before apply without reviewed proof",
        "stop_note": "Missing source rows, stale snapshots, rejected rows, or placeholder fields keep the lane blocked.",
        "stop_href": proof_href,
    }
