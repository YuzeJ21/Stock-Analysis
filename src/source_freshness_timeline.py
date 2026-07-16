"""Read-only source chronology for a selected stock-report payload."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class FreshnessTimelineEvent:
    event_id: str
    ticker: str
    profile_key: str
    lane: str
    event_type: str
    timestamp_kind: str
    timestamp: str | None
    source: str
    source_ref: str
    freshness_state: str
    note: str


@dataclass(frozen=True)
class FreshnessTimeline:
    ticker: str
    profile_key: str
    timeline_identity: str
    events: tuple[FreshnessTimelineEvent, ...]
    latest_known_timestamp: str | None
    unknown_timestamp_count: int
    stale_or_unknown_count: int


def _normalized_timestamp(value: object) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _freshness_state(value: object, *, timestamp: str | None) -> str:
    if timestamp is None:
        return "missing_timestamp"
    text = str(value or "").strip().lower()
    if "stale" in text or "expired" in text or "old" in text:
        return "stale"
    if text in {"current", "fresh", "ready", "available"}:
        return "current"
    return "unknown"


def _event(
    *,
    ticker: str,
    profile_key: str,
    lane: str,
    event_type: str,
    timestamp_kind: str,
    timestamp: object,
    source: object,
    source_ref: object = "",
    freshness: object = "",
    note: object = "",
) -> FreshnessTimelineEvent:
    normalized_timestamp = _normalized_timestamp(timestamp)
    payload = {
        "ticker": ticker,
        "profile_key": profile_key,
        "lane": lane,
        "event_type": event_type,
        "timestamp_kind": timestamp_kind,
        "timestamp": normalized_timestamp,
        "source": str(source or "").strip(),
        "source_ref": str(source_ref or "").strip(),
        "freshness_state": _freshness_state(freshness, timestamp=normalized_timestamp),
        "note": str(note or "").strip(),
    }
    event_id = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return FreshnessTimelineEvent(event_id=event_id, **payload)


def _source_lane(provider: str) -> str:
    lowered = provider.lower()
    if any(token in lowered for token in ("price", "stooq", "yahoo", "market")):
        return "price"
    if any(token in lowered for token in ("sec", "fundamental", "filing")):
        return "fundamentals"
    if "peer" in lowered:
        return "peers"
    if any(token in lowered for token in ("earnings", "estimate", "consensus")):
        return "optional_context"
    return "source"


def _notes_text(value: object) -> str:
    if isinstance(value, (list, tuple)):
        return " | ".join(str(item).strip() for item in value if str(item).strip())
    return str(value or "").strip()


def build_source_freshness_timeline(
    report_payload: dict[str, object],
    *,
    profile_key: str,
) -> FreshnessTimeline:
    """Build a deterministic chronology without substituting missing timestamps."""

    ticker = str(report_payload.get("ticker") or "").strip().upper()
    events: list[FreshnessTimelineEvent] = []

    generated_at = report_payload.get("generated_at")
    if generated_at:
        events.append(
            _event(
                ticker=ticker,
                profile_key=profile_key,
                lane="report",
                event_type="report_assembled",
                timestamp_kind="report_generated",
                timestamp=generated_at,
                source="stock_report",
                freshness="current",
                note="Report assembly time; not source publication or freshness proof.",
            )
        )

    price = report_payload.get("price_snapshot", {}) or {}
    if price.get("market_time"):
        events.append(
            _event(
                ticker=ticker,
                profile_key=profile_key,
                lane="price",
                event_type="price_observed",
                timestamp_kind="market_observed",
                timestamp=price.get("market_time"),
                source="price_snapshot",
                freshness="current",
                note="Market observation time supplied by the selected report.",
            )
        )

    financials = report_payload.get("financial_summary", {}) or {}
    if financials.get("as_of_date"):
        events.append(
            _event(
                ticker=ticker,
                profile_key=profile_key,
                lane="fundamentals",
                event_type="financial_period_effective",
                timestamp_kind="financial_effective",
                timestamp=financials.get("as_of_date"),
                source="financial_summary",
                source_ref=financials.get("reporting_period"),
                freshness="unknown",
                note="Financial effective date; publication time is not inferred.",
            )
        )

    for row in report_payload.get("data_freshness", []) or []:
        if not isinstance(row, dict):
            continue
        provider = str(row.get("provider") or "").strip() or "unknown_source"
        events.append(
            _event(
                ticker=ticker,
                profile_key=profile_key,
                lane=_source_lane(provider),
                event_type="source_retrieved",
                timestamp_kind="source_retrieved",
                timestamp=row.get("retrieved_at"),
                source=provider,
                source_ref=row.get("source_ref"),
                freshness=row.get("freshness"),
                note=_notes_text(row.get("notes")),
            )
        )

    deduplicated = {event.event_id: event for event in events}
    ordered = tuple(
        sorted(
            deduplicated.values(),
            key=lambda event: (event.timestamp is not None, event.timestamp or "", event.event_id),
            reverse=True,
        )
    )
    identity_payload = {
        "ticker": ticker,
        "profile_key": profile_key,
        "event_ids": [event.event_id for event in ordered],
    }
    timeline_identity = hashlib.sha256(
        json.dumps(identity_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    known = [event.timestamp for event in ordered if event.timestamp is not None]
    unknown_count = sum(event.timestamp is None for event in ordered)
    stale_or_unknown_count = sum(
        event.freshness_state in {"stale", "unknown", "missing_timestamp"} for event in ordered
    )
    return FreshnessTimeline(
        ticker=ticker,
        profile_key=profile_key,
        timeline_identity=timeline_identity,
        events=ordered,
        latest_known_timestamp=max(known) if known else None,
        unknown_timestamp_count=unknown_count,
        stale_or_unknown_count=stale_or_unknown_count,
    )


def timeline_rows(timeline: FreshnessTimeline) -> list[dict[str, Any]]:
    """Return display-safe event rows while preserving immutable event fields."""

    return [asdict(event) for event in timeline.events]
