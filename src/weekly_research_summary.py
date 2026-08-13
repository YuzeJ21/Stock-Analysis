"""Traceable, recommendation-free weekly summaries for a focused cohort."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable, Mapping

from src.earnings_nowcast_contract import parse_utc_timestamp
from src.focused_research_cohort import FocusedCohort


CATEGORY_ORDER = {
    "newly_blocked": 0,
    "invalidation_condition": 1,
    "requires_review": 2,
    "new_evidence": 3,
    "newly_usable": 4,
    "stale_review": 5,
    "waiting": 6,
}


@dataclass(frozen=True)
class WeeklySummaryItem:
    category: str
    ticker: str
    answer: str
    state: str
    source_ref: str
    effective_at: str


@dataclass(frozen=True)
class WeeklyResearchSummary:
    status: str
    as_of: str
    cohort_size: int
    unique_event_count: int
    items: tuple[WeeklySummaryItem, ...]
    message: str


def _text(value: object) -> str:
    return str(value or "").strip()


def _truthy(value: object) -> bool:
    return _text(value).lower() in {"true", "1", "yes", "y"}


def _event_item(category: str, review_item, answer: str, state: str) -> WeeklySummaryItem:
    event = review_item.event
    return WeeklySummaryItem(
        category=category,
        ticker=_text(event.ticker).upper(),
        answer=answer,
        state=state,
        source_ref=_text(getattr(event, "source_ref", "")) or f"event:{_text(getattr(event, 'event_id', 'unknown'))}",
        effective_at=_text(getattr(event, "source_published_at", "")) or _text(getattr(event, "detected_at", "")),
    )


def build_weekly_research_summary(
    cohort: FocusedCohort,
    review_items: Iterable[object],
    *,
    journal_rows: Iterable[Mapping[str, object]] = (),
    as_of: str,
    window_days: int = 7,
) -> WeeklyResearchSummary:
    boundary = parse_utc_timestamp(as_of)
    window_start = boundary - timedelta(days=max(window_days, 0))
    cohort_tickers = {member.ticker for member in cohort.members}
    seen: set[str] = set()
    eligible_events: list[object] = []
    for item in review_items:
        event = item.event
        ticker = _text(getattr(event, "ticker", "")).upper()
        if ticker not in cohort_tickers:
            continue
        event_id = _text(getattr(event, "event_id", "")) or "\x1f".join(
            _text(getattr(event, field, ""))
            for field in ("ticker", "family", "subtype", "prior_value", "current_value", "source_ref", "detected_at")
        )
        if event_id in seen:
            continue
        detected_text = _text(getattr(event, "detected_at", ""))
        try:
            detected = parse_utc_timestamp(detected_text)
        except ValueError:
            continue
        if detected < window_start or detected > boundary:
            continue
        seen.add(event_id)
        eligible_events.append(item)

    items: list[WeeklySummaryItem] = []
    for review_item in eligible_events:
        event = review_item.event
        ticker = _text(event.ticker).upper()
        evidence_status = _text(getattr(event, "evidence_status", ""))
        review_status = _text(getattr(review_item, "review_status", "")) or "open"
        if evidence_status == "source_backed":
            items.append(
                _event_item(
                    "new_evidence",
                    review_item,
                    f"{ticker}: {_text(event.subtype).replace('_', ' ')} is supported by changed source evidence.",
                    "review_now",
                )
            )
        if review_status == "open":
            items.append(
                _event_item(
                    "requires_review",
                    review_item,
                    _text(getattr(event, "suggested_research_task", "")) or f"{ticker}: Review the changed evidence.",
                    "review_now",
                )
            )
        prior = _text(getattr(event, "prior_value", "")).lower()
        current = _text(getattr(event, "current_value", "")).lower()
        if _text(getattr(event, "family", "")) == "readiness" and prior == "false" and current == "true":
            items.append(
                _event_item(
                    "newly_usable",
                    review_item,
                    f"{ticker}: {_text(event.subtype).replace('_', ' ')} now has source-backed readiness.",
                    "review_now",
                )
            )
        if _text(getattr(event, "family", "")) == "readiness" and prior == "true" and current == "false":
            items.append(
                _event_item(
                    "newly_blocked",
                    review_item,
                    f"{ticker}: {_text(event.subtype).replace('_', ' ')} is no longer ready; review the changed source state.",
                    "wait_for_evidence",
                )
            )
        if review_status in {"still_blocked", "intentionally_deferred"}:
            items.append(
                _event_item(
                    "waiting",
                    review_item,
                    _text(getattr(review_item, "wait_condition", "")) or "Wait for changed source evidence.",
                    "wait_for_evidence" if review_status == "still_blocked" else "monitor",
                )
            )

    as_of_date = boundary.date()
    for row in journal_rows:
        ticker = _text(row.get("ticker")).upper()
        if ticker not in cohort_tickers:
            continue
        source_ref = _text(row.get("source_ref"))
        review_due = _text(row.get("review_due_date"))
        if review_due:
            try:
                due_date = date.fromisoformat(review_due)
            except ValueError:
                due_date = as_of_date
            if due_date < as_of_date:
                items.append(
                    WeeklySummaryItem(
                        "stale_review",
                        ticker,
                        f"{ticker}: Reviewer-authored research review was due on {review_due}.",
                        "review_now",
                        source_ref or f"journal:{ticker}",
                        review_due,
                    )
                )
        if _truthy(row.get("invalidation_triggered")) and _text(row.get("invalidation_condition")):
            items.append(
                WeeklySummaryItem(
                    "invalidation_condition",
                    ticker,
                    _text(row.get("invalidation_condition")),
                    "review_now",
                    source_ref or f"journal:{ticker}",
                    _text(row.get("triggered_at")) or as_of,
                )
            )

    items.sort(key=lambda item: (CATEGORY_ORDER.get(item.category, 99), item.ticker, item.source_ref, item.answer))
    status = "review_required" if items else "no_changes"
    message = (
        f"{len(items)} traceable cohort research item(s) require review or monitoring."
        if items
        else "No traceable cohort evidence change requires review this week."
    )
    return WeeklyResearchSummary(
        status=status,
        as_of=boundary.isoformat(),
        cohort_size=len(cohort.members),
        unique_event_count=len(eligible_events),
        items=tuple(items),
        message=message,
    )


def weekly_summary_rows(summary: WeeklyResearchSummary) -> list[dict[str, str]]:
    return [
        {
            "Category": item.category.replace("_", " ").title(),
            "Ticker": item.ticker,
            "Answer": item.answer,
            "State": item.state.replace("_", " "),
            "Source reference": item.source_ref,
            "Effective at": item.effective_at,
        }
        for item in summary.items
    ]
