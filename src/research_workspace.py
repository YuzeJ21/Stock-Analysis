"""Read-only composition helpers for the personal research workspace."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import html
import pandas as pd
from urllib.parse import quote

from src.company_workbench_cash_generation_preview import (
    CompanyWorkbenchCashGenerationPreview,
)
from src.dashboard_visual_system import (
    EvidenceRow,
    SafeRouteAction,
    advanced_detail_marker_html,
    answer_panel_html,
    context_bar_html,
    detail_disclosure_html,
    detail_item_html,
    evidence_rows_html,
    legacy_research_accessibility_css,
    page_title_html,
)
from src.focused_cohort_coverage import FocusedCohortCoverage
from src.focused_research_cohort import FocusedCohort
from src.quarterly_business_trend import QuarterlyTrendPacket
from src.research_decision_lab import ResearchDisciplineRow
from src.weekly_research_summary import WeeklyResearchSummary


RESEARCH_ROUTING_STATES = {"review_now", "monitor", "wait_for_evidence", "excluded"}


@dataclass(frozen=True)
class EvidenceMonitorCard:
    key: str
    kicker: str
    title: str
    body: str
    badges: tuple[str, ...]


@dataclass(frozen=True)
class EvidenceMonitorBrief:
    cards: tuple[EvidenceMonitorCard, ...]
    primary_rows: tuple[ResearchDisciplineRow, ...]
    monitor_count: int


@dataclass(frozen=True)
class MonitorFollowUpPanel:
    key: str
    kicker: str
    title: str
    body: str
    badges: tuple[str, ...]


@dataclass(frozen=True)
class MonitorFollowUpQueue:
    panels: tuple[MonitorFollowUpPanel, ...]
    primary_rows: tuple[ResearchDisciplineRow, ...]
    verification_rows: tuple[ResearchDisciplineRow, ...]
    waiting_rows: tuple[ResearchDisciplineRow, ...]
    scheduled_rows: tuple[ResearchDisciplineRow, ...]
    monitor_count: int
    has_saved_follow_up: bool
    has_readiness_attention: bool
    has_observation_attention: bool
    has_freshness_attention: bool
    freshness_attention_only: bool
    has_attention: bool
    is_empty: bool
    empty_title: str
    empty_boundary: str
    primary_reason: str
    next_action_label: str
    next_action_url: str


@dataclass(frozen=True)
class ResearchDeskBrief:
    question: str
    attention_count: int
    answer: str
    reason: str
    freshness_warning: str
    next_action_label: str
    next_action_url: str
    stop_rule: str


_CURRENT_SAVED_STATES = {"current", "fresh", "ready"}


def saved_readiness_display_label(state: object) -> str:
    """Label readiness as saved-source state rather than current-market truth."""

    normalized = str(state or "").strip().casefold()
    if normalized in _CURRENT_SAVED_STATES:
        return "Current for saved sources"
    return normalized.replace("_", " ").capitalize() or "Check saved readiness"


def _saved_freshness_needs_attention(state: object) -> bool:
    normalized = str(state or "").strip().casefold()
    return normalized not in _CURRENT_SAVED_STATES


def saved_research_item_count(
    summary: WeeklyResearchSummary,
    additional_items: Iterable[object] = (),
) -> int:
    """Return one shared saved-item count without using event cardinality."""

    return max(len(tuple(summary.items or ())), len(tuple(additional_items or ())))


def build_research_desk_brief(
    summary: WeeklyResearchSummary,
    *,
    change_status: str,
    review_items: Iterable[object],
    freshness_state: str,
    freshness_message: str,
    observation_state: str | None = None,
    observation_message: str = "",
) -> ResearchDeskBrief:
    """Compose one read-only answer from already-saved workspace evidence."""

    saved_review_items = tuple(review_items or ())
    attention_count = saved_research_item_count(summary, saved_review_items)
    readiness_attention = _saved_freshness_needs_attention(freshness_state)
    observation_attention = _saved_freshness_needs_attention(observation_state)
    freshness_attention = readiness_attention or observation_attention
    if attention_count:
        noun = "item" if attention_count == 1 else "items"
        answer = f"{attention_count} saved research {noun} need attention."
        reason = (
            summary.items[0].answer
            if summary.items
            else "Saved source-change evidence requires review."
        )
        next_action_label = "Open Monitor"
        next_action_url = "?mode=research&page=monitor"
    else:
        answer = (
            "No saved research item is currently due from the evidence loaded in "
            "this workspace."
        )
        comparable = str(change_status or "").strip() in {
            "changes_detected",
            "no_changes",
        }
        reason = (
            "No unresolved saved source-change item is available."
            if comparable
            else "A comparable saved before-and-after research snapshot is not available yet."
        )
        if freshness_attention:
            if readiness_attention and observation_attention:
                reason = (
                    "No saved research item is due. Saved-readiness and market-observation "
                    "freshness both need Data Health review; neither is a saved research item "
                    "or a live-market alert."
                )
            else:
                condition = (
                    "a separate saved-readiness freshness condition"
                    if readiness_attention
                    else "a separate saved market-observation freshness condition"
                )
                reason = (
                    f"No saved research item is due. {condition.capitalize()} still needs "
                    "Data Health review; it is not a saved research item or a live-market alert."
                )
            next_action_label = "Open Data Health"
            next_action_url = "?mode=research&page=data-health"
        else:
            next_action_label = "Open Discover"
            next_action_url = "?mode=research&page=discover"

    normalized_freshness = str(freshness_state or "").strip().casefold() or "unavailable"
    freshness_body = str(freshness_message or "").strip()
    if normalized_freshness in _CURRENT_SAVED_STATES:
        freshness_warning = freshness_body or "Saved readiness is current for saved sources."
    elif normalized_freshness == "unavailable" and not freshness_body:
        freshness_warning = "Saved readiness is unavailable."
    else:
        freshness_warning = (
            f"Saved readiness is {normalized_freshness}: "
            f"{freshness_body or 'No current saved readiness evidence is available.'}"
        )

    return ResearchDeskBrief(
        question="What needs my attention today?",
        attention_count=attention_count,
        answer=answer,
        reason=reason,
        freshness_warning=freshness_warning,
        next_action_label=next_action_label,
        next_action_url=next_action_url,
        stop_rule=(
            "This brief summarizes saved workspace evidence only. It is not a "
            "market-complete event feed, recommendation, or trade instruction."
        ),
    )


def build_monitor_follow_up_queue(
    summary: WeeklyResearchSummary,
    rows: Iterable[ResearchDisciplineRow],
    *,
    source_change_count: int = 0,
    readiness_state: str,
    readiness_message: str,
    observation_state: str,
    observation_message: str,
) -> MonitorFollowUpQueue:
    """Compose one fail-closed Monitor answer without changing saved evidence."""

    ordered = tuple(rows)
    verification_rows = tuple(
        row for row in ordered if row.attention_label == "Needs review"
    )
    waiting_rows = tuple(
        row
        for row in ordered
        if row.attention_state == "unavailable"
        and row.attention_label != "Needs review"
    )
    scheduled_rows = tuple(
        row for row in ordered if row.attention_label == "Scheduled"
    )
    primary_rows = tuple(row for row in ordered if row.attention_state != "monitor")
    monitor_count = sum(row.attention_state == "monitor" for row in ordered)
    normalized_change_count = max(int(source_change_count), 0)

    normalized_readiness = str(readiness_state or "").strip() or "unavailable"
    normalized_observation = str(observation_state or "").strip() or "unavailable"
    readiness_body = (
        str(readiness_message or "").strip() or "Saved readiness is unavailable."
    )
    observation_body = (
        str(observation_message or "").strip()
        or "Market observation is unavailable."
    )

    recent_title = (
        f"{len(summary.items)} recent item{'s' if len(summary.items) != 1 else ''}; "
        f"{normalized_change_count} unresolved saved "
        f"change{'s' if normalized_change_count != 1 else ''}"
    )
    recent_body = summary.message
    if normalized_change_count:
        recent_body = (
            f"{recent_body} {normalized_change_count} unresolved saved source-change "
            f"item{'s remain' if normalized_change_count != 1 else ' remains'} for review."
        )

    verification_body = (
        verification_rows[0].attention_reason
        if verification_rows
        else "No saved verification task is currently due."
    )
    waiting_body = (
        waiting_rows[0].attention_reason
        if waiting_rows
        else "No saved research-process item is waiting on evidence."
    )
    scheduled_body = (
        scheduled_rows[0].attention_reason
        if scheduled_rows
        else "No saved research-process context is currently scheduled."
    )

    saved_readiness_label = (
        saved_readiness_display_label(normalized_readiness)
        if normalized_readiness.casefold() in _CURRENT_SAVED_STATES
        else normalized_readiness
    )
    panels = (
        MonitorFollowUpPanel(
            "since_last_review",
            "SINCE LAST REVIEW",
            recent_title,
            recent_body,
            (
                summary.status.replace("_", " "),
                "7-day saved window",
                f"{summary.cohort_size} companies",
            ),
        ),
        MonitorFollowUpPanel(
            "needs_verification",
            "NEEDS VERIFICATION",
            f"{len(verification_rows)} needs verification",
            verification_body,
            (
                "saved process evidence",
                "not a company score",
                f"{monitor_count} monitoring",
            ),
        ),
        MonitorFollowUpPanel(
            "waiting_on_evidence",
            "WAITING ON EVIDENCE",
            f"{len(waiting_rows)} waiting on evidence",
            waiting_body,
            ("fail closed", "no inferred evidence"),
        ),
        MonitorFollowUpPanel(
            "scheduled_context",
            "SCHEDULED CONTEXT",
            f"{len(scheduled_rows)} scheduled",
            scheduled_body,
            ("saved process context", "not urgency"),
        ),
        MonitorFollowUpPanel(
            "evidence_freshness",
            "EVIDENCE FRESHNESS",
            f"Readiness {saved_readiness_label}; observation {normalized_observation}",
            f"Saved readiness: {readiness_body} Market observation: {observation_body}",
            (
                f"saved readiness: {saved_readiness_label}",
                f"market observation: {normalized_observation}",
            ),
        ),
    )

    has_readiness_attention = normalized_readiness.casefold() not in _CURRENT_SAVED_STATES
    has_observation_attention = normalized_observation.casefold() not in _CURRENT_SAVED_STATES
    freshness_attention_count = sum(
        (has_readiness_attention, has_observation_attention)
    )
    has_saved_follow_up = bool(
        saved_research_item_count(summary)
        or normalized_change_count
        or primary_rows
    )
    has_freshness_attention = bool(freshness_attention_count)
    has_attention = has_saved_follow_up or has_freshness_attention
    empty_title = (
        "No saved verification, evidence-wait, scheduled, or source-change item "
        "is currently due."
    )
    empty_boundary = (
        "This does not prove that no external event, risk, or research need exists."
    )
    action_ticker = next(
        (
            str(row.ticker or "").strip().upper()
            for row in primary_rows
            if str(row.ticker or "").strip()
        ),
        "",
    )
    if not action_ticker:
        action_ticker = next(
            (
                str(item.ticker or "").strip().upper()
                for item in summary.items
                if str(item.ticker or "").strip()
            ),
            "",
        )
    if primary_rows:
        primary_reason = (
            str(primary_rows[0].attention_reason or "").strip()
            or "Saved process evidence requires review."
        )
    elif summary.items:
        primary_reason = (
            str(summary.items[0].answer or "").strip()
            or "Saved weekly evidence requires review."
        )
    elif normalized_change_count:
        noun = "item" if normalized_change_count == 1 else "items"
        verb = "remains" if normalized_change_count == 1 else "remain"
        primary_reason = (
            f"{normalized_change_count} unresolved saved source-change {noun} "
            f"{verb} for review."
        )
    elif freshness_attention_count:
        primary_reason = panels[4].body
    else:
        primary_reason = empty_boundary
    if has_attention and action_ticker:
        next_action_label = f"Open {action_ticker} Company Workbench"
        next_action_url = (
            f"?mode=research&page=company-workbench&ticker={quote(action_ticker)}&open=1"
        )
    elif has_attention:
        next_action_label = "Open Data Health"
        next_action_url = "?mode=research&page=data-health"
    else:
        next_action_label = "Open Discover"
        next_action_url = "?mode=research&page=discover"
    return MonitorFollowUpQueue(
        panels=panels,
        primary_rows=primary_rows,
        verification_rows=verification_rows,
        waiting_rows=waiting_rows,
        scheduled_rows=scheduled_rows,
        monitor_count=monitor_count,
        has_saved_follow_up=has_saved_follow_up,
        has_readiness_attention=has_readiness_attention,
        has_observation_attention=has_observation_attention,
        has_freshness_attention=has_freshness_attention,
        freshness_attention_only=(has_freshness_attention and not has_saved_follow_up),
        has_attention=has_attention,
        is_empty=not has_attention,
        empty_title=empty_title,
        empty_boundary=empty_boundary,
        primary_reason=primary_reason,
        next_action_label=next_action_label,
        next_action_url=next_action_url,
    )


def monitor_primary_answer(queue: MonitorFollowUpQueue) -> str:
    if queue.is_empty:
        return queue.empty_title
    if queue.freshness_attention_only:
        verb = (
            "both need"
            if queue.has_readiness_attention and queue.has_observation_attention
            else "needs"
        )
        return (
            "No saved research item is due. "
            f"{monitor_freshness_condition_label(queue, sentence_case=True)} "
            f"{verb} Data Health review."
        )
    return "Saved follow-up evidence needs attention."


def monitor_freshness_condition_label(
    queue: MonitorFollowUpQueue,
    *,
    sentence_case: bool = False,
) -> str:
    """Name the exact saved-readiness and/or market-observation condition."""

    if queue.has_readiness_attention and queue.has_observation_attention:
        label = "saved-readiness and market-observation freshness"
        return label.capitalize() if sentence_case else label
    elif queue.has_readiness_attention:
        label = "saved-readiness freshness condition"
    else:
        label = "market-observation freshness condition"
    prefix = "A separate " if sentence_case else ""
    return f"{prefix}{label}"


def build_evidence_monitor_brief(
    summary: WeeklyResearchSummary,
    rows: Iterable[ResearchDisciplineRow],
    *,
    readiness_state: str,
    readiness_message: str,
    observation_state: str,
    observation_message: str,
) -> EvidenceMonitorBrief:
    ordered = tuple(rows)
    primary_rows = tuple(row for row in ordered if row.attention_state != "monitor")
    monitor_count = sum(row.attention_state == "monitor" for row in ordered)
    needs_review = tuple(row for row in ordered if row.attention_label == "Needs review")
    unavailable = tuple(row for row in ordered if row.attention_state == "unavailable")
    scheduled = tuple(row for row in ordered if row.attention_label == "Scheduled")
    first_follow_up = next(
        (
            row
            for row in ordered
            if row.attention_label == "Needs review"
            or row.attention_state == "unavailable"
        ),
        None,
    )

    follow_up_body = (
        first_follow_up.attention_reason
        if first_follow_up is not None
        else "No saved research-process follow-up is currently due."
    )
    scheduled_body = (
        scheduled[0].attention_reason
        if scheduled
        else "No saved research-process context is currently scheduled."
    )
    normalized_readiness = str(readiness_state or "").strip() or "unavailable"
    normalized_observation = str(observation_state or "").strip() or "unavailable"
    readiness_body = (
        str(readiness_message or "").strip() or "Saved readiness is unavailable."
    )
    observation_body = (
        str(observation_message or "").strip() or "Market observation is unavailable."
    )

    cards = (
        EvidenceMonitorCard(
            "weekly",
            "WEEKLY RESEARCH SUMMARY",
            f"{len(summary.items)} traceable item{'s' if len(summary.items) != 1 else ''}",
            summary.message,
            (
                summary.status.replace("_", " "),
                "7-day saved window",
                f"{summary.cohort_size} companies",
            ),
        ),
        EvidenceMonitorCard(
            "follow_up",
            "RESEARCH FOLLOW-UP",
            f"{len(needs_review)} needs review; {len(unavailable)} unavailable",
            follow_up_body,
            ("process timing", "not a company score", f"{monitor_count} monitor"),
        ),
        EvidenceMonitorCard(
            "scheduled",
            "SCHEDULED CONTEXT",
            f"{len(scheduled)} scheduled",
            scheduled_body,
            ("saved process context", "not urgency"),
        ),
        EvidenceMonitorCard(
            "freshness",
            "EVIDENCE FRESHNESS",
            f"Readiness {normalized_readiness}; observation {normalized_observation}",
            f"Saved readiness: {readiness_body} Market observation: {observation_body}",
            (
                f"saved readiness: {normalized_readiness}",
                f"market observation: {normalized_observation}",
            ),
        ),
    )
    return EvidenceMonitorBrief(cards, primary_rows, monitor_count)


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
            "change_context_kind": "none",
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
            "change_context_kind": "snapshot_only",
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
        "change_context_kind": "source_backed",
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


def _brief_text(value: object, fallback: str) -> str:
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return fallback
    cleaned = " ".join(str(value).split())
    return cleaned or fallback


def company_workbench_primary_brief(
    selected_answer_frame: pd.DataFrame,
    change_answer: Mapping[str, object] | None,
    authoritative_task: Mapping[str, object] | None,
) -> dict[str, object]:
    """Compose one fail-closed selected-company answer without changing evidence state."""

    row: Mapping[str, object] = {}
    if isinstance(selected_answer_frame, pd.DataFrame) and not selected_answer_frame.empty:
        row = selected_answer_frame.iloc[0].to_dict()

    raw_ticker = _brief_text(row.get("Ticker"), "")
    ticker = raw_ticker.upper() if raw_ticker else "Selected company"
    use_now = _brief_text(
        row.get("Use Now"),
        "No supported evidence lane is available.",
    )
    blocked = _brief_text(
        row.get("Still Blocked"),
        "Evidence availability is unverified.",
    )
    context_only = _brief_text(
        row.get("Context Only"),
        "No trusted context is available.",
    )

    change = change_answer if isinstance(change_answer, Mapping) else {}
    change_kind = _brief_text(change.get("change_context_kind"), "none")
    if change_kind not in {"none", "snapshot_only", "source_backed"}:
        change_kind = "none"
    change_state = _brief_text(change.get("state"), "monitor")
    if change_state not in RESEARCH_ROUTING_STATES:
        change_state = "monitor"
    what_changed = _brief_text(
        change.get("answer"),
        "No unresolved source-backed change is queued for this company.",
    )

    task = (
        authoritative_task
        if isinstance(authoritative_task, Mapping)
        else _neutral_company_next_research_task()
    )
    task_title = _brief_text(
        task.get("title"),
        _neutral_company_next_research_task()["title"],
    )
    task_body = _brief_text(
        task.get("body"),
        _neutral_company_next_research_task()["body"],
    )
    task_state = _brief_text(task.get("state"), "wait_for_evidence")
    if task_state not in RESEARCH_ROUTING_STATES:
        task_state = "wait_for_evidence"
    raw_badges = task.get("badges", ())
    if not isinstance(raw_badges, Iterable) or isinstance(
        raw_badges, (str, bytes, Mapping)
    ):
        raw_badges = ()
    task_badges = tuple(
        dict.fromkeys(
            _brief_text(value, "")
            for value in raw_badges
            if _brief_text(value, "")
        )
    )
    if not task_badges:
        task_badges = ("monitor", "research-only")

    peer_task = "peer" in " ".join((task_title, *task_badges)).casefold()
    if peer_task:
        task_body = (
            f"{task_body} Use the Data Health peer lane to inspect the exact blocker. "
            "Reviewed source evidence is required; Personal Research does not silently "
            "create peer mappings."
        )
    href = "?mode=research&page=data-health"
    if raw_ticker:
        href += f"&ticker={quote(raw_ticker.upper())}"
    data_health_label = "Open Data Health"
    if peer_task:
        href += "&lane=peers&drawer=proof"
        data_health_label = "Open Data Health · Peers"
    return {
        "ticker": ticker,
        "use_now": use_now,
        "still_withheld": f"Blocked: {blocked} Context only: {context_only}",
        "what_changed": what_changed,
        "change_context_kind": change_kind,
        "change_state": change_state,
        "next_task_title": task_title,
        "next_task_body": task_body,
        "next_task_state": task_state,
        "next_task_badges": task_badges,
        "data_health_href": href,
        "data_health_label": data_health_label,
        "stop_rule": (
            "Research-only: this brief is not a recommendation, probability, transaction "
            "instruction, or unsupported current-market conclusion."
        ),
    }


def company_workbench_evidence_status_html(
    *,
    ticker: str,
    readiness: Mapping[str, object] | None,
    freshness_label: str,
) -> str:
    """Render the selected company's read-only five-lane evidence status rail."""

    def safe_text(value: object, fallback: str) -> str:
        if value is None:
            return fallback
        text = str(value).strip()
        return text or fallback

    safe_ticker = html.escape(safe_text(ticker, "Selected company"))
    safe_freshness = html.escape(safe_text(freshness_label, "Unavailable"))
    is_missing = readiness is None
    safe_readiness = readiness if isinstance(readiness, Mapping) else {}

    lanes = (
        ("fundamentals", "Fundamentals", ("fundamentals_ready",)),
        ("dcf", "DCF", ("dcf_ready",)),
        ("peers", "Peers", ("peer_ready",)),
        ("earnings", "Earnings", ("earnings_available", "earnings_ready")),
        (
            "estimates",
            "Estimates",
            ("analyst_estimates_available", "analyst_estimates_ready"),
        ),
    )

    lane_html: list[str] = []
    for lane_id, label, readiness_keys in lanes:
        if is_missing:
            state = "Unavailable"
        else:
            state = (
                "Reviewable"
                if any(safe_readiness.get(key) is True for key in readiness_keys)
                else "Withheld"
            )
        lane_html.append(
            "<article "
            f"id='{lane_id}' class='company-workbench-evidence-lane' "
            f"data-evidence-lane='{html.escape(lane_id, quote=True)}'>"
            f"<span>{html.escape(label)}</span>"
            f"<strong>{html.escape(state)}</strong>"
            "</article>"
        )

    return (
        "<aside class='company-workbench-evidence-status' "
        "data-sr-region='evidence-status' aria-label='Company evidence status'>"
        "<div class='company-workbench-evidence-heading'>"
        "<h2>Company evidence status</h2>"
        f"<span>{safe_ticker} · {safe_freshness}</span>"
        "</div>"
        "<div class='company-workbench-evidence-lanes'>"
        + "".join(lane_html)
        + "</div>"
        "</aside>"
    )


def company_workbench_primary_brief_html(brief: Mapping[str, object]) -> str:
    """Render one escaped Company Brief region from the pure composition contract."""

    safe = brief if isinstance(brief, Mapping) else {}

    def escaped(key: str, fallback: str) -> str:
        return html.escape(_brief_text(safe.get(key), fallback))

    def raw(key: str, fallback: str) -> str:
        return _brief_text(safe.get(key), fallback)

    href = html.escape(
        _brief_text(safe.get("data_health_href"), "?mode=research&page=data-health"),
        quote=True,
    )
    raw_change_kind = raw("change_context_kind", "none")
    if raw_change_kind not in {"none", "snapshot_only", "source_backed"}:
        raw_change_kind = "none"
    change_kind = html.escape(raw_change_kind).replace("_", " ")
    change_summary = {
        "none": "No source-backed change is queued.",
        "snapshot_only": "Snapshot-only change context is available.",
        "source_backed": "Source-backed change context is available.",
    }[raw_change_kind]
    change_state = escaped("change_state", "monitor").replace("_", " ")
    task_state = escaped("next_task_state", "wait for evidence").replace("_", " ")
    return (
        "<section class='company-workbench-primary-brief' data-sr-region='primary-answer' "
        "aria-label='Company Brief'>"
        "<div class='company-workbench-primary-heading'>"
        f"<h2>{escaped('ticker', 'Selected company')} Company Brief</h2>"
        "</div>"
        "<div class='company-workbench-primary-grid'>"
        "<article class='company-workbench-primary-answer use-now' data-workbench-lane='usable'>"
        "<span>Use now</span>"
        f"<p>{escaped('use_now', 'No supported evidence lane is available.')}</p>"
        "</article>"
        "<article class='company-workbench-primary-answer withheld' data-workbench-lane='withheld'>"
        "<span>Still withheld</span>"
        f"<p>{escaped('still_withheld', 'Evidence availability is unverified.')}</p>"
        "</article>"
        "<article class='company-workbench-primary-answer changed' data-workbench-lane='change'>"
        "<span>What changed</span>"
        f"<p>{change_summary}</p>"
        f"<small>{change_kind} · {change_state}</small>"
        "</article>"
        "<article class='company-workbench-primary-answer next-task' data-workbench-lane='next-task'>"
        "<span>Next research task</span>"
        f"<strong>{escaped('next_task_title', 'Wait for reviewed evidence or choose another company')}</strong>"
        f"<small>{task_state}</small>"
        f"<a class='public-primary-action' data-sr-region='primary-action' href='{href}' target='_self'>{escaped('data_health_label', 'Open Data Health')}</a>"
        "</article>"
        "</div>"
        "<p class='company-workbench-primary-stop research-workspace-boundary' data-sr-region='stop-rule'>"
        f"{escaped('stop_rule', 'Research-only: do not infer a recommendation or unsupported conclusion.')}"
        "</p>"
        "</section>"
    )


def company_workbench_detail_disclosure_html(brief: Mapping[str, object]) -> str:
    """Render exact Company Brief prose after supporting change evidence."""

    safe = brief if isinstance(brief, Mapping) else {}

    def raw(key: str, fallback: str) -> str:
        return _brief_text(safe.get(key), fallback)

    return detail_disclosure_html(
        "Full Company Brief evidence",
        (
            detail_item_html(
                label="Use now",
                body=raw("use_now", "No supported evidence lane is available."),
            ),
            detail_item_html(
                label="Still withheld",
                body=raw("still_withheld", "Evidence availability is unverified."),
            ),
            detail_item_html(
                label="What changed",
                body=raw(
                    "what_changed",
                    "No unresolved source-backed change is queued for this company.",
                ),
            ),
            detail_item_html(
                label="Next research task detail",
                body=raw("next_task_body", "No executable company task is available."),
            ),
        ),
    ).value


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


def validated_research_return_ticker(
    value: object,
    registered_tickers: Iterable[object],
) -> str:
    """Return a registered Monitor destination, or no context when validation fails."""

    requested = str(value or "").strip().upper()
    registered = {
        str(ticker or "").strip().upper()
        for ticker in registered_tickers
        if str(ticker or "").strip()
    }
    return requested if requested and requested in registered else ""


def research_monitor_return_link(ticker: str) -> dict[str, str]:
    """Build the selected-company return action without changing Monitor scope."""

    symbol = _quoted_ticker(ticker)
    label_ticker = str(ticker or "").strip().upper()
    return {
        "label": f"Return to {label_ticker} Company Workbench",
        "href": f"?mode=research&page=company-workbench&ticker={symbol}&open=1",
        "purpose": "Return to the selected company; this context does not filter Monitor.",
    }


def research_workflow_navigation_html(*, active_page: str, ticker: str = "") -> str:
    """Render the deterministic Personal Research route sequence."""

    active_slug = str(active_page or "").strip().lower().replace(" ", "-")
    symbol = _quoted_ticker(ticker)
    routes = [
        ("Research Desk", "research-desk", "?mode=research&page=research-desk"),
        ("Discover", "discover", "?mode=research&page=discover"),
    ]
    routes.append(
        (
            "Company Workbench",
            "company-workbench",
            f"?mode=research&page=company-workbench&ticker={symbol}&open=1"
            if symbol
            else "",
        )
    )
    monitor_href = "?mode=research&page=monitor"
    if symbol:
        monitor_href = f"{monitor_href}&return_ticker={symbol}"
    routes.append(("Monitor", "monitor", monitor_href))
    links: list[str] = []
    for label, slug, href in routes:
        if not href:
            links.append(
                "<span class='research-workflow-disabled' aria-disabled='true' "
                "title='Choose a company in Discover first'>Company Workbench"
                "<span class='sr-visually-hidden'> — Choose a company in Discover first</span></span>"
            )
            continue
        current = (
            " aria-current='page'"
            if active_slug == slug and active_slug not in {"data-health", "proof-history"}
            else ""
        )
        links.append(
            "<a class='research-workflow-link' "
            f"href='{html.escape(href, quote=True)}' target='_self'{current}>"
            f"{html.escape(label)}</a>"
        )
    evidence_label = {
        "data-health": "Data Health",
        "proof-history": "Proof History",
    }.get(active_slug, "")
    evidence_current = (
        "<div class='research-workflow-evidence-current'>"
        "<span>Advanced Evidence</span>"
        f"<strong aria-current='page'>Advanced Evidence · {html.escape(evidence_label)}</strong>"
        "</div>"
        if evidence_label
        else ""
    )
    return (
        "<nav class='research-workflow-navigation' data-sr-region='workflow-nav' aria-label='Personal research workflow'>"
        "<a class='research-workspace-brand' href='?mode=research&amp;page=research-desk' target='_self'>"
        "<span>Readiness-first</span><strong>Stock Research Command Center</strong></a>"
        f"<div class='research-workflow-routes'>{''.join(links)}{evidence_current}</div>"
        "<div class='research-workspace-mode' role='group' aria-label='Workspace mode'>"
        "<span>Workspace mode</span>"
        "<a href='?mode=public' target='_self'>Public</a>"
        "<a href='?mode=operator' target='_self'>Operator</a>"
        "</div></nav>"
    )


def research_accessibility_media_preferences_css() -> str:
    """Return Research-only media preference fallbacks without changing data."""

    return legacy_research_accessibility_css()


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
        label_ticker = str(ticker or "").strip().upper()
        return {
            "label": f"Return to {label_ticker} Company Workbench",
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
    compact: bool = False,
    include_boundary: bool = True,
) -> str:
    scope = str(ticker or "Focused research scope").strip().upper() if ticker else "Focused research scope"
    header_class = "research-workspace-header compact" if compact else "research-workspace-header"
    meta_html = "" if compact else (
        "<dl class='research-workspace-meta'>"
        f"<div class='research-workspace-meta-item research-workspace-freshness'><dt>Saved readiness</dt><dd>{html.escape(str(freshness or 'Check saved readiness'))}</dd></div>"
        f"<div class='research-workspace-meta-item research-workspace-action'><dt>Next action</dt><dd>{html.escape(str(primary_action or 'Review source-backed evidence'))}</dd></div>"
        "</dl>"
    )
    boundary_html = (
        "<p class='research-workspace-boundary' data-sr-region='stop-rule'>"
        "Research-only. Not investment advice; no trade instruction is produced.</p>"
        if include_boundary
        else ""
    )
    context = context_bar_html(
        (
            ("Data profile", str(profile_label or "Local research")),
            ("Saved readiness", str(freshness or "Check saved readiness")),
            ("Mode", "Personal research"),
        )
    ).value
    title = page_title_html(
        title=str(page_title or "Research Desk"),
        purpose=f"{scope} · {str(profile_label or 'Local research')}",
    ).value
    return (
        f"<section class='{header_class}' aria-label='Personal research workspace'>"
        f"{context}{title}"
        f"{meta_html}"
        f"{boundary_html}"
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


def research_desk_brief_html(
    brief: ResearchDeskBrief,
    *,
    freshness_state: str = "unavailable",
) -> str:
    """Render the Desk contract as one answer-first, keyboard-accessible block."""

    answer = answer_panel_html(
        question=brief.question,
        answer=brief.answer,
        reason=brief.reason,
        action=SafeRouteAction(
            label=brief.next_action_label,
            href=brief.next_action_url,
        ),
        stop_rule=f"Research-only. {brief.stop_rule}",
    ).value
    evidence = evidence_rows_html(
        (
            EvidenceRow(
                lane="Freshness · Saved readiness",
                role="freshness",
                state=freshness_state,
                count_or_cutoff=brief.freshness_warning,
                reason=brief.reason,
                display_label=saved_readiness_display_label(freshness_state),
            ),
        )
    ).value
    return (
        "<section class='research-desk-brief' aria-label=\"Today's Research Brief\">"
        f"{answer}{evidence}</section>"
    )


def research_advanced_detail_marker_html() -> str:
    """Expose one stable hook immediately before the existing advanced expander."""

    return advanced_detail_marker_html().value


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
