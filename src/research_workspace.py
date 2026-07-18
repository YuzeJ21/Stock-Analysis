"""Read-only composition helpers for the personal research workspace."""

from __future__ import annotations

import html
import pandas as pd
from urllib.parse import quote


RESEARCH_ROUTING_STATES = {"review_now", "monitor", "wait_for_evidence", "excluded"}


def research_desk_cards(*, change_status: str, review_items, readiness_summary: dict[str, object]):
    items = tuple(review_items or ())
    total = int(readiness_summary.get("master_universe") or readiness_summary.get("universe_count") or 0)
    price_ready = int(readiness_summary.get("price_ready") or 0)
    dcf_ready = int(readiness_summary.get("dcf_ready") or 0)
    peer_ready = int(readiness_summary.get("peer_ready") or 0)
    change_count = len(items)
    comparable = str(change_status or "").strip() in {"changes_detected", "no_changes"}
    changed_answer = (
        f"{change_count} unresolved evidence change{'s' if change_count != 1 else ''} need review."
        if change_count
        else "No unresolved evidence-backed change is available for review."
        if comparable
        else "A comparable before-and-after research snapshot is not available yet."
    )
    attention_answer = (
        f"{change_count} queued evidence item{'s' if change_count != 1 else ''} need attention."
        if change_count
        else "No company is currently queued from verified change evidence."
    )
    blocked_count = max(total - dcf_ready, 0) if total else 0
    blocked_answer = (
        f"{blocked_count} of {total} tracked rows do not have a source-backed DCF-ready path; "
        f"{max(total - peer_ready, 0)} still lack trusted peer readiness."
        if total
        else "Readiness totals are unavailable; blocked or stale states remain withheld."
    )
    next_answer = (
        "Review the queued evidence changes first, then open Discover for the next company."
        if change_count
        else "Open Discover to choose a readiness-backed company for review."
    )
    return [
        {
            "question": "What changed?",
            "answer": changed_answer,
            "routing_state": "review_now" if change_count else "monitor",
        },
        {
            "question": "Which companies need attention?",
            "answer": attention_answer,
            "routing_state": "review_now" if change_count else "monitor",
        },
        {
            "question": "What is blocked or stale?",
            "answer": blocked_answer,
            "routing_state": "wait_for_evidence" if blocked_count else "monitor",
        },
        {
            "question": "What should I review next?",
            "answer": next_answer,
            "routing_state": "review_now" if change_count else "monitor",
        },
    ]


def company_workbench_section_contract() -> list[dict[str, object]]:
    return [
        {
            "title": "Selected Company",
            "contents": ["Ticker and entity", "Research state", "Data confidence", "Freshness"],
            "expanded": True,
        },
        {
            "title": "Business Trend",
            "contents": ["Financial trend", "Price trend", "Evidence window", "Unavailable inputs"],
            "expanded": True,
        },
        {
            "title": "Valuation",
            "contents": ["Source-backed range", "Assumptions", "Sensitivity", "Withheld state"],
            "expanded": True,
        },
        {
            "title": "Forward View",
            "contents": ["Scenarios", "Peer context", "Earnings outlook", "Catalysts and risks"],
            "expanded": True,
        },
        {
            "title": "Research Conclusion",
            "contents": ["Usable evidence", "Uncertainty", "Routing state", "Next research action"],
            "expanded": True,
        },
        {
            "title": "Advanced Evidence",
            "contents": ["Provenance", "Freshness Timeline", "Data Health", "Proof History", "Raw evidence"],
            "expanded": False,
        },
    ]


def research_monitor_frame(review_items) -> pd.DataFrame:
    rows: list[dict[str, str]] = []
    state_map = {
        "open": "review_now",
        "still_blocked": "wait_for_evidence",
        "intentionally_deferred": "monitor",
        "excluded": "excluded",
    }
    for item in tuple(review_items or ()):
        event = item.event
        rows.append(
            {
                "Ticker": str(event.ticker or "").upper(),
                "Change": str(event.subtype or "").replace("_", " ").title(),
                "Evidence": str(event.evidence_status or "").replace("_", " "),
                "Review state": state_map.get(str(item.review_status or ""), "monitor"),
                "Detected": str(event.detected_at or ""),
                "Next research task": str(event.suggested_research_task or item.wait_condition or ""),
            }
        )
    return pd.DataFrame(
        rows,
        columns=["Ticker", "Change", "Evidence", "Review state", "Detected", "Next research task"],
    )


def advanced_evidence_links(ticker: str) -> list[dict[str, str]]:
    symbol = quote(str(ticker or "").strip().upper())
    suffix = f"&ticker={symbol}" if symbol else ""
    return [
        {
            "label": "Open Data Health",
            "href": f"?mode=operator&page=data-health{suffix}",
            "purpose": "Inspect blocked inputs and source-proof paths.",
        },
        {
            "label": "Open Proof History",
            "href": f"?mode=public&page=proof-history{suffix}",
            "purpose": "Review evidence that changed a readiness state.",
        },
    ]


def research_workspace_header_html(
    page_title: str,
    *,
    ticker: str = "",
    profile_label: str,
    freshness: str,
    primary_action: str,
) -> str:
    scope = str(ticker or "Focused research scope").strip().upper() if ticker else "Focused research scope"
    return (
        "<section class='research-workspace-header' aria-label='Personal research workspace'>"
        "<div class='research-workspace-heading'>"
        "<span>Personal research mode</span>"
        f"<h1>{html.escape(str(page_title or 'Research Desk'))}</h1>"
        f"<p>{html.escape(scope)} · {html.escape(str(profile_label or 'Local research'))}</p>"
        "</div>"
        "<dl class='research-workspace-meta'>"
        f"<div><dt>Freshness</dt><dd>{html.escape(str(freshness or 'Check saved readiness'))}</dd></div>"
        f"<div><dt>Next action</dt><dd>{html.escape(str(primary_action or 'Review source-backed evidence'))}</dd></div>"
        "</dl>"
        "<p class='research-workspace-boundary'>Research-only. Not investment advice; no trade instruction is produced.</p>"
        "</section>"
    )


def research_desk_cards_html(cards) -> str:
    rendered = "".join(
        "<article class='research-desk-answer'>"
        f"<span>{html.escape(str(card.get('routing_state') or 'monitor').replace('_', ' '))}</span>"
        f"<h2>{html.escape(str(card.get('question') or 'Research question'))}</h2>"
        f"<p>{html.escape(str(card.get('answer') or 'No verified answer is available.'))}</p>"
        "</article>"
        for card in cards
    )
    return f"<section class='research-desk-grid' aria-label='Research Desk answers'>{rendered}</section>"


def advanced_evidence_links_html(ticker: str) -> str:
    rendered = "".join(
        "<a class='research-evidence-link' "
        f"href='{html.escape(link['href'], quote=True)}' target='_self'>"
        f"<strong>{html.escape(link['label'])}</strong>"
        f"<span>{html.escape(link['purpose'])}</span>"
        "</a>"
        for link in advanced_evidence_links(ticker)
    )
    return f"<div class='research-evidence-links'>{rendered}</div>"
