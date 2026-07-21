"""Read-only composition helpers for the personal research workspace."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
import html
import pandas as pd
from urllib.parse import quote

from src.company_workbench_cash_generation_preview import (
    CompanyWorkbenchCashGenerationPreview,
)
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
    eligible = [
        item
        for item in matching
        if str(getattr(item.event, "evidence_status", "") or "").strip() == "source_backed"
    ]
    source_refs = tuple(
        dict.fromkeys(
            str(getattr(item.event, "source_ref", "") or "").strip()
            for item in eligible
            if str(getattr(item.event, "source_ref", "") or "").strip()
        )
    )
    count = len({str(getattr(item.event, "event_id", "") or id(item)) for item in eligible})
    if not matching:
        return {
            "state": "monitor",
            "answer": "No unresolved source-backed change is queued for this company.",
            "next_task": "Continue the current review or wait for changed source evidence.",
            "source_refs": (),
            "source_backed_eligible": False,
        }
    if not count:
        snapshot_item = matching[0]
        snapshot_status = str(getattr(snapshot_item, "review_status", "") or "").strip()
        snapshot_state = {
            "open": "review_now",
            "still_blocked": "wait_for_evidence",
            "intentionally_deferred": "monitor",
        }.get(snapshot_status, "monitor")
        snapshot_task = str(getattr(snapshot_item.event, "suggested_research_task", "") or "").strip()
        if snapshot_status == "still_blocked":
            snapshot_task = str(getattr(snapshot_item, "wait_condition", "") or "").strip() or (
                "Reviewed evidence remains blocked; wait for new source evidence."
            )
        elif snapshot_status == "intentionally_deferred":
            snapshot_task = str(getattr(snapshot_item, "wait_condition", "") or "").strip() or (
                "Review is intentionally deferred until the recorded condition changes."
            )
        return {
            "state": snapshot_state,
            "answer": "Snapshot-only change context is visible but cannot outrank a source-backed research priority.",
            "next_task": snapshot_task or "Continue the current review or wait for changed source evidence.",
            "source_refs": (),
            "source_backed_eligible": False,
        }

    first = eligible[0]
    review_status = str(getattr(first, "review_status", "") or "").strip()
    state = {
        "open": "review_now",
        "still_blocked": "wait_for_evidence",
        "intentionally_deferred": "monitor",
    }.get(review_status, "monitor")
    first_task = str(getattr(first.event, "suggested_research_task", "") or "Review the changed evidence.").strip()
    if review_status == "still_blocked":
        first_task = str(getattr(first, "wait_condition", "") or "").strip() or (
            "Reviewed evidence remains blocked; wait for new source evidence."
        )
    elif review_status == "intentionally_deferred":
        first_task = str(getattr(first, "wait_condition", "") or "").strip() or (
            "Review is intentionally deferred until the recorded condition changes."
        )
    return {
        "state": state,
        "answer": (
            "1 unresolved source-backed change needs review."
            if count == 1
            else f"{count} unresolved source-backed changes need review."
        ),
        "next_task": first_task,
        "source_refs": source_refs,
        "source_backed_eligible": True,
    }


def _neutral_company_next_research_task() -> dict[str, object]:
    return {
        "title": "Wait for reviewed evidence or choose another company",
        "body": "No source-backed change or executable company task is available. Do not infer one from missing data.",
        "state": "wait_for_evidence",
        "badges": ["monitor", "research-only"],
    }


def company_next_research_task(
    change_answer: Mapping[str, object] | None,
    conclusion_cards: Iterable[Mapping[str, object]] | None,
) -> dict[str, object]:
    if not isinstance(change_answer, Mapping):
        return _neutral_company_next_research_task()
    if (
        not isinstance(conclusion_cards, Iterable)
        or isinstance(conclusion_cards, (str, bytes, Mapping))
    ):
        return _neutral_company_next_research_task()
    try:
        raw_cards = tuple(conclusion_cards)
    except TypeError:
        return _neutral_company_next_research_task()

    cards: list[tuple[Mapping[str, object], tuple[object, ...]]] = []
    for raw_card in raw_cards:
        if not isinstance(raw_card, Mapping):
            return _neutral_company_next_research_task()
        raw_badges = raw_card.get("badges", ())
        if (
            not isinstance(raw_badges, Iterable)
            or isinstance(raw_badges, (str, bytes, Mapping))
        ):
            return _neutral_company_next_research_task()
        try:
            badges = tuple(raw_badges)
        except TypeError:
            return _neutral_company_next_research_task()
        cards.append((raw_card, badges))

    change_state = str(change_answer.get("state") or "").strip()
    change_title = str(change_answer.get("next_task") or "").strip()
    if (
        change_answer.get("source_backed_eligible") is True
        and change_state in RESEARCH_ROUTING_STATES
        and change_title
    ):
        body = {
            "review_now": "Complete this source-backed evidence review before starting another research task.",
            "wait_for_evidence": "This source-backed change remains blocked; preserve its recorded wait condition.",
            "monitor": "This source-backed change is intentionally deferred; preserve its recorded wait condition.",
        }.get(change_state, "Preserve this source-backed change routing state before starting another research task.")
        return {
            "title": change_title,
            "body": body,
            "state": change_state,
            "badges": ["source-backed change", "research-only"],
        }

    for card, raw_badges in cards:
        title = str(card.get("title") or "").strip()
        if not title:
            continue
        badges = [str(value).strip() for value in raw_badges if str(value).strip()]
        return {
            "title": title,
            "body": str(card.get("body") or "").strip(),
            "state": (
                str(card.get("state") or "").strip()
                if str(card.get("state") or "").strip() in RESEARCH_ROUTING_STATES
                else "wait_for_evidence"
            ),
            "badges": list(dict.fromkeys([*badges, "research-only"])),
        }

    return _neutral_company_next_research_task()


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
    metrics = (
        ("Revenue", packet.revenue, False),
        ("EPS", packet.eps, False),
        ("Operating margin", packet.operating_margin, True),
        ("Free cash flow", packet.free_cash_flow, False),
        ("FCF margin", packet.fcf_margin, True),
    )
    for label, trend, is_percent in metrics:
        change_parts = []
        if trend.sequential_change_pct is not None:
            change_parts.append(f"sequential {trend.sequential_change_pct:+.1f}%")
        if trend.year_over_year_change_pct is not None:
            change_parts.append(f"year over year {trend.year_over_year_change_pct:+.1f}%")
        boundary = "; ".join((*trend.missing_comparisons, trend.withheld_reason)).strip("; ")
        if trend.latest_value is None:
            title = "Withheld"
        elif is_percent:
            title = f"{trend.latest_value * 100:.1f}%"
        else:
            title = f"{trend.latest_value:g}"
        cards.append(
            {
                "kicker": label.upper(),
                "title": title,
                "body": ", ".join(change_parts) if change_parts else boundary or "Comparable change is withheld.",
                "state": trend.status,
                "badges": [trend.status, trend.latest_fiscal_period or "no period"],
                "command": "",
            }
        )
    return cards


def _cash_preview_display_value(metric: str, value: float | None) -> str:
    if value is None:
        return "Withheld"
    if metric in {"operating_margin", "fcf_margin"}:
        return f"{value * 100.0:.1f}%"
    return f"{value:,.0f}"


def cash_generation_preview_cards(
    preview: CompanyWorkbenchCashGenerationPreview,
) -> list[dict[str, object]]:
    """Return answer-first preview cards without technical lineage."""

    cards: list[dict[str, object]] = [
        {
            "kicker": "CASH-GENERATION REVIEW PREVIEW",
            "title": "Cash-generation review preview — not production evidence",
            "body": (
                f"{preview.message} Production activation is false; readiness "
                "promotions are none; no persistence or readiness rebuild occurs."
            ),
            "state": "preview_only" if preview.status == "accepted_for_review" else "withheld",
            "badges": ["preview only", "not production evidence"],
            "command": "",
        }
    ]
    for label, metric in (
        ("OPERATING MARGIN", preview.operating_margin),
        ("FREE CASH FLOW", preview.free_cash_flow),
        ("FCF MARGIN", preview.fcf_margin),
    ):
        cards.append(
            {
                "kicker": label,
                "title": _cash_preview_display_value(metric.metric, metric.value),
                "body": (
                    f"{metric.fiscal_period} accepted packet preview."
                    if metric.value is not None
                    else metric.withheld_reason
                    or "Complete compatible evidence is required."
                ),
                "state": metric.status,
                "badges": ["preview only", metric.status.replace("_", " ")],
                "command": "",
            }
        )
    return cards


def cash_generation_preview_rows(
    preview: CompanyWorkbenchCashGenerationPreview,
) -> list[dict[str, object]]:
    """Return technical preview lineage for the collapsed Advanced surface."""

    def evidence_row(
        evidence: str,
        value: object,
        *,
        definition: str = "",
        source_ref: str = "",
        published_at: str = "",
        retrieved_at: str = "",
    ) -> dict[str, object]:
        return {
            "Evidence": evidence,
            "Value": value,
            "Definition": definition,
            "Source Reference": source_ref,
            "Published At": published_at,
            "Retrieved At": retrieved_at,
        }

    rows = [
        evidence_row("Accession", preview.accession, source_ref=preview.source_url),
        evidence_row("Source", preview.source_url, source_ref=preview.source_url),
        evidence_row("Accepted at", preview.accepted_at, published_at=preview.accepted_at),
        evidence_row("Cutoff", preview.cutoff),
        evidence_row("Capex sign", preview.capex_sign_evidence),
        evidence_row(
            "Boundary",
            "production activation false; readiness promotions none; no persistence; no readiness rebuild",
        ),
    ]
    rows.extend(
        evidence_row("Blocker", blocker)
        for blocker in preview.blockers
    )
    rows.extend(
        evidence_row(
            "Component",
            f"{component.metric}: {component.value:g} {component.currency}",
            definition=(
                f"{component.accounting_basis}; {component.duration_basis}; "
                f"{component.fiscal_period}; {component.q4_evidence_state}"
            ),
            source_ref=component.source_ref,
            published_at=component.published_at,
            retrieved_at=component.retrieved_at,
        )
        for component in preview.components
    )
    return rows


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


def _quoted_ticker(ticker: str) -> str:
    return quote(str(ticker or "").strip().upper(), safe="")


def advanced_evidence_links(ticker: str) -> list[dict[str, str]]:
    symbol = _quoted_ticker(ticker)
    suffix = f"&ticker={symbol}" if symbol else ""
    return [
        {
            "label": "Open Data Health",
            "href": f"?mode=research&page=data-health{suffix}",
            "purpose": "Inspect blocked inputs and source-proof paths.",
        },
        {
            "label": "Open Proof History",
            "href": f"?mode=research&page=proof-history{suffix}",
            "purpose": "Review evidence that changed a readiness state.",
        },
    ]


def research_evidence_return_link(ticker: str) -> dict[str, str]:
    symbol = _quoted_ticker(ticker)
    if symbol:
        return {
            "label": "Return to Company Workbench",
            "href": f"?mode=research&page=company-workbench&ticker={symbol}&open=1",
            "purpose": "Continue the selected-company review without changing evidence state.",
        }
    return {
        "label": "Return to Research Desk",
        "href": "?mode=research&page=research-desk",
        "purpose": "Return to the primary research workflow without changing evidence state.",
    }


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
        f"<div class='research-workspace-meta-item research-workspace-freshness'><dt>Freshness</dt><dd>{html.escape(str(freshness or 'Check saved readiness'))}</dd></div>"
        f"<div class='research-workspace-meta-item research-workspace-action'><dt>Next action</dt><dd>{html.escape(str(primary_action or 'Review source-backed evidence'))}</dd></div>"
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
