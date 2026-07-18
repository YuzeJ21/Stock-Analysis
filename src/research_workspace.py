"""Read-only composition helpers for the personal research workspace."""

from __future__ import annotations

import html
import pandas as pd
from urllib.parse import quote

from src.focused_cohort_coverage import FocusedCohortCoverage
from src.focused_research_cohort import FocusedCohort
from src.quarterly_business_trend import QuarterlyTrendPacket
from src.weekly_research_summary import WeeklyResearchSummary


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
            "title": "What Changed",
            "contents": ["Source-backed evidence changes", "Previous state", "Current state", "Review task"],
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
            "title": "What Remains Withheld",
            "contents": ["Missing periods", "Blocked inputs", "Candidate context", "Source wait conditions"],
            "expanded": True,
        },
        {
            "title": "Research Conclusion",
            "contents": ["Usable evidence", "Uncertainty", "Routing state", "Next research action"],
            "expanded": True,
        },
        {
            "title": "Next Research Task",
            "contents": ["One evidence review action", "Wait condition when unavailable"],
            "expanded": True,
        },
        {
            "title": "Advanced Evidence",
            "contents": ["Provenance", "Freshness Timeline", "Data Health", "Proof History", "Raw evidence"],
            "expanded": False,
        },
    ]


def company_change_answer(ticker: str, review_items) -> dict[str, object]:
    symbol = str(ticker or "").strip().upper()
    matching = [item for item in tuple(review_items or ()) if str(item.event.ticker or "").strip().upper() == symbol]
    source_refs = tuple(
        dict.fromkeys(
            str(getattr(item.event, "source_ref", "") or "").strip()
            for item in matching
            if str(getattr(item.event, "source_ref", "") or "").strip()
        )
    )
    count = len({str(getattr(item.event, "event_id", "") or id(item)) for item in matching})
    if not count:
        return {
            "state": "monitor",
            "answer": "No unresolved source-backed change is queued for this company.",
            "next_task": "Continue the current review or wait for changed source evidence.",
            "source_refs": (),
        }
    first_task = str(getattr(matching[0].event, "suggested_research_task", "") or "Review the changed evidence.")
    return {
        "state": "review_now",
        "answer": (
            "1 unresolved source-backed change needs review."
            if count == 1
            else f"{count} unresolved source-backed changes need review."
        ),
        "next_task": first_task,
        "source_refs": source_refs,
    }


def focused_cohort_cards(cohort: FocusedCohort) -> list[dict[str, object]]:
    return [
        {
            "kicker": "FOCUSED COHORT",
            "title": f"{len(cohort.members)} of {cohort.requested_size} requested companies",
            "body": cohort.message,
            "state": cohort.status,
            "badges": [cohort.status.replace("_", " "), "evidence availability"],
            "command": "",
        },
        {
            "kicker": "SELECTION BOUNDARY",
            "title": "Reviewability, not expected return",
            "body": "Operating-company and price readiness establish eligibility; deeper source-backed lanes improve review order without creating a recommendation.",
            "state": "research_only",
            "badges": ["deterministic", "no recommendation score"],
            "command": "",
        },
    ]


def focused_cohort_coverage_cards(coverage: FocusedCohortCoverage) -> list[dict[str, object]]:
    usable = sum(row.state == "usable_now" for row in coverage.rows)
    candidate = sum(row.state == "candidate_context_only" for row in coverage.rows)
    gated = sum(row.state in {"partial", "candidate_context_only", "blocked"} for row in coverage.rows)
    excluded = sum(row.state == "excluded" for row in coverage.rows)
    return [
        {
            "kicker": "COHORT COVERAGE",
            "title": f"{usable} usable lane{'s' if usable != 1 else ''}",
            "body": coverage.message,
            "state": coverage.status,
            "badges": [f"{coverage.company_count} companies", "saved evidence only"],
            "command": "",
        },
        {
            "kicker": "WITHHELD OR CONTEXT ONLY",
            "title": f"{gated} gated lane{'s' if gated != 1 else ''}",
            "body": (
                f"{candidate} lane{'s are' if candidate != 1 else ' is'} candidate context only; "
                f"{excluded} lane{'s are' if excluded != 1 else ' is'} excluded as not applicable. "
                "Research-only states remain separate from supported evidence."
            ),
            "state": "wait_for_evidence" if gated else "monitor",
            "badges": ["candidate context separated", "no inferred coverage"],
            "command": "",
        },
    ]


def focused_ticker_coverage_cards(
    coverage: FocusedCohortCoverage,
    ticker: str,
) -> list[dict[str, object]]:
    symbol = str(ticker or "").strip().upper()
    rows = tuple(row for row in coverage.rows if row.ticker == symbol)
    usable = sum(row.state == "usable_now" for row in rows)
    partial = sum(row.state in {"partial", "candidate_context_only"} for row in rows)
    blocked = sum(row.state == "blocked" for row in rows)
    excluded = sum(row.state == "excluded" for row in rows)
    return [
        {
            "kicker": f"{symbol or 'SELECTED COMPANY'} COVERAGE",
            "title": f"{usable} usable lane{'s' if usable != 1 else ''}",
            "body": "Saved source evidence supports these lanes now; each remains research context only.",
            "state": "ready" if usable and not (partial or blocked) else "partial" if rows else "blocked",
            "badges": ["source-backed only", "no inferred inputs"],
            "command": "",
        },
        {
            "kicker": "GATED OR NOT APPLICABLE",
            "title": f"{blocked} blocked lane{'s' if blocked != 1 else ''}",
            "body": (
                f"{partial} partial or candidate-context lane(s); {excluded} excluded lane(s). "
                "Open Advanced Evidence only when the exact lane proof is needed."
            ),
            "state": "wait_for_evidence" if blocked or partial else "monitor",
            "badges": ["blocked stays blocked", "research-only"],
            "command": "",
        },
    ]


def quarterly_trend_cards(packet: QuarterlyTrendPacket) -> list[dict[str, object]]:
    cards: list[dict[str, object]] = [
        {
            "kicker": "QUARTERLY BUSINESS TREND",
            "title": packet.latest_fiscal_period or "Quarterly evidence unavailable",
            "body": packet.message,
            "state": packet.status,
            "badges": [packet.status, packet.source_confidence.replace("_", " ")],
            "command": "",
        }
    ]
    for label, trend in (("Revenue", packet.revenue), ("EPS", packet.eps)):
        change_parts = []
        if trend.sequential_change_pct is not None:
            change_parts.append(f"sequential {trend.sequential_change_pct:+.1f}%")
        if trend.year_over_year_change_pct is not None:
            change_parts.append(f"year over year {trend.year_over_year_change_pct:+.1f}%")
        boundary = "; ".join((*trend.missing_comparisons, trend.withheld_reason)).strip("; ")
        cards.append(
            {
                "kicker": label.upper(),
                "title": str(trend.latest_value) if trend.latest_value is not None else "Withheld",
                "body": ", ".join(change_parts) if change_parts else boundary or "Comparable change is withheld.",
                "state": trend.status,
                "badges": [trend.status, trend.latest_fiscal_period or "no period"],
                "command": "",
            }
        )
    return cards


def weekly_summary_cards(summary: WeeklyResearchSummary) -> list[dict[str, object]]:
    cards: list[dict[str, object]] = [
        {
            "kicker": "WEEKLY RESEARCH SUMMARY",
            "title": f"{len(summary.items)} traceable item{'s' if len(summary.items) != 1 else ''}",
            "body": summary.message,
            "state": "review_now" if summary.items else "monitor",
            "badges": [summary.status.replace("_", " "), f"{summary.cohort_size} companies"],
            "command": "",
        }
    ]
    cards.extend(
        {
            "kicker": item.category.replace("_", " ").upper(),
            "title": item.ticker,
            "body": item.answer,
            "state": item.state,
            "badges": [item.state.replace("_", " "), "traceable"],
            "command": "",
        }
        for item in summary.items[:5]
    )
    return cards


def research_monitor_frame(review_items) -> pd.DataFrame:
    rows: list[dict[str, str]] = []
    seen_event_ids: set[str] = set()
    state_map = {
        "open": "review_now",
        "still_blocked": "wait_for_evidence",
        "intentionally_deferred": "monitor",
        "excluded": "excluded",
    }
    for item in tuple(review_items or ()):
        event = item.event
        event_id = str(getattr(event, "event_id", "") or "").strip()
        deduplication_key = event_id or "\x1f".join(
            str(getattr(event, field, "") or "")
            for field in ("ticker", "family", "subtype", "prior_value", "current_value", "source_ref", "detected_at")
        )
        if deduplication_key in seen_event_ids:
            continue
        seen_event_ids.add(deduplication_key)
        rows.append(
            {
                "Ticker": str(event.ticker or "").upper(),
                "Change": str(event.subtype or "").replace("_", " ").title(),
                "Previous state": str(getattr(event, "prior_value", "") or ""),
                "Current state": str(getattr(event, "current_value", "") or ""),
                "Evidence": str(event.evidence_status or "").replace("_", " "),
                "Affected section": str(getattr(event, "family", "") or "").replace("_", " ").title(),
                "Review state": state_map.get(str(item.review_status or ""), "monitor"),
                "Effective date": str(getattr(event, "source_published_at", "") or ""),
                "Detected": str(event.detected_at or ""),
                "Next research task": str(event.suggested_research_task or item.wait_condition or ""),
                "Wait condition": str(item.wait_condition or ""),
            }
        )
    return pd.DataFrame(
        rows,
        columns=[
            "Ticker",
            "Change",
            "Previous state",
            "Current state",
            "Evidence",
            "Affected section",
            "Review state",
            "Effective date",
            "Detected",
            "Next research task",
            "Wait condition",
        ],
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
