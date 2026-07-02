"""Pure helpers for the Data Health operator console.

This module keeps lane, detail-mode, and compact HTML decisions out of the
Streamlit rendering layer. It is intentionally read-only and does not load,
refresh, import, or infer market data.
"""

from __future__ import annotations

import html


DATA_HEALTH_OPERATOR_LANES = {
    "prices": "Prices",
    "fundamentals": "Fundamentals / DCF",
    "peers": "Peers",
    "metrics": "Metrics",
    "optional": "Optional Context",
    "proof": "Proof History",
}

DATA_HEALTH_BATCH_LANES = {
    "prices": "prices",
    "fundamentals": "fundamentals",
    "peers": "peers",
    "metrics": "metrics",
    "optional": "optional_context",
}


def _format_missing(value: object, fallback: str = "Not available") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null", "nat"}:
        return fallback
    return text


def _compact_fragment(value: object, fallback: str = "Not available", *, max_chars: int = 88) -> str:
    text = _format_missing(value, fallback=fallback).replace("\n", " ").strip()
    if len(text) <= max_chars:
        return text
    return text[: max(0, max_chars - 1)].rstrip() + "..."


def data_health_operator_lane_from_query(value: object) -> str:
    if isinstance(value, (list, tuple)):
        value = value[0] if value else ""
    raw = str(value or "prices").strip().lower().replace("_", "-")
    aliases = {
        "price": "prices",
        "peer": "peers",
        "fundamentals-dcf": "fundamentals",
        "dcf": "fundamentals",
        "fundamentals / dcf": "fundamentals",
        "optional-context": "optional",
        "proof-history": "proof",
        "history": "proof",
    }
    lane = aliases.get(raw, raw)
    return lane if lane in DATA_HEALTH_OPERATOR_LANES else "prices"


def data_health_operator_queue_header_html() -> str:
    return (
        "<div class='ops-queue-header'>"
        "<div class='ops-queue-title'>Operator Queue</div>"
        "<div class='ops-queue-caption'>Choose one readiness lane. Evidence and commands stay collapsed until needed.</div>"
        "</div>"
    )


def data_health_operator_lane_nav_html(selected_lane_key: str) -> str:
    links: list[str] = []
    for lane_key, label in DATA_HEALTH_OPERATOR_LANES.items():
        active_class = " active" if lane_key == selected_lane_key else ""
        href = f"?mode=operator&page=data-health&lane={lane_key}"
        links.append(
            f"<a class='ops-lane-link{active_class}' href='{html.escape(href)}' target='_self'>{html.escape(label)}</a>"
        )
    return "<div class='ops-lane-nav'>" + "".join(links) + "</div>"


def data_health_detail_mode_label(enabled: bool) -> str:
    return "Review details" if enabled else "Fast view"


def data_health_selected_detail_mode(
    selected_lane_key: str,
    *,
    batch_details_requested: bool,
    metric_details_requested: bool,
    proof_details_requested: bool,
) -> str:
    if selected_lane_key == "metrics":
        return data_health_detail_mode_label(metric_details_requested)
    if selected_lane_key == "proof":
        return data_health_detail_mode_label(proof_details_requested)
    if selected_lane_key in DATA_HEALTH_BATCH_LANES:
        return data_health_detail_mode_label(batch_details_requested)
    return "Fast view"


def data_health_current_mode_next_action(
    selected_lane_key: str,
    *,
    batch_details_requested: bool,
    metric_detail_status: dict[str, str],
    proof_details_requested: bool,
    readiness_freshness: object,
    batch_preflight: object,
    source_gate_next_action: str = "",
) -> str:
    freshness_status = str(getattr(readiness_freshness, "status", "") or "")
    if freshness_status in {"missing", "stale"}:
        return str(getattr(readiness_freshness, "refresh_command", "") or "make readiness")
    if source_gate_next_action and selected_lane_key in DATA_HEALTH_BATCH_LANES:
        return source_gate_next_action
    if selected_lane_key == "metrics":
        return metric_detail_status.get("next_action") or "Open Metrics review details."
    if selected_lane_key == "proof":
        return "Review proof ledgers and snapshot comparison." if proof_details_requested else "Open Proof review details."
    if selected_lane_key in DATA_HEALTH_BATCH_LANES:
        if not batch_details_requested:
            return "Open Batch execution review details."
        return str(getattr(batch_preflight, "packet_command", "") or "Build reviewed batch packet.")
    return "Choose a readiness lane."


def data_health_current_mode_strip_html(
    *,
    selected_lane_key: str,
    queue_details_requested: bool,
    batch_details_requested: bool,
    metric_details_requested: bool,
    proof_details_requested: bool,
    readiness_freshness: object,
    batch_preflight: object,
    metric_detail_status: dict[str, str],
    source_gate_next_action: str = "",
) -> str:
    lane_label = DATA_HEALTH_OPERATOR_LANES.get(selected_lane_key, "Prices")
    selected_detail = data_health_selected_detail_mode(
        selected_lane_key,
        batch_details_requested=batch_details_requested,
        metric_details_requested=metric_details_requested,
        proof_details_requested=proof_details_requested,
    )
    queue_detail = data_health_detail_mode_label(queue_details_requested)
    freshness_status = getattr(readiness_freshness, "status", "unknown") or "unknown"
    freshness_value = str(freshness_status).replace("_", " ").title()
    freshness_message = _compact_fragment(getattr(readiness_freshness, "message", "Not available"), max_chars=88)
    next_action = data_health_current_mode_next_action(
        selected_lane_key,
        batch_details_requested=batch_details_requested,
        metric_detail_status=metric_detail_status,
        proof_details_requested=proof_details_requested,
        readiness_freshness=readiness_freshness,
        batch_preflight=batch_preflight,
        source_gate_next_action=source_gate_next_action,
    )
    items = [
        ("Lane", lane_label, "Active readiness workflow."),
        ("Lane detail", selected_detail, "Fast view keeps proof tables collapsed."),
        ("Queue detail", queue_detail, "Controls broad lane rows and drilldowns."),
        ("Freshness", freshness_value, freshness_message),
        (
            "Detail boundary",
            "Review drawers stay collapsed",
            "Queue drawers, route maps, proof ledgers, raw tables, provider setup details, and generated-artifact lists stay collapsed until opened.",
        ),
        ("Next safe action", next_action, "Copy-only; research readiness, not a recommendation."),
    ]
    blocks = []
    for label, value, note in items:
        action_class = " action" if label == "Next safe action" else ""
        blocks.append(
            f"<div class='ops-mode-item{action_class}'>"
            f"<div class='ops-mode-label'>{html.escape(label)}</div>"
            f"<div class='ops-mode-value'>{html.escape(_format_missing(value))}</div>"
            f"<div class='ops-mode-note'>{html.escape(_format_missing(note))}</div>"
            "</div>"
        )
    return "<div class='ops-mode-strip'>" + "".join(blocks) + "</div>"
