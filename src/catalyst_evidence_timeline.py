"""Source-backed catalyst evidence timeline for research context only."""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass, fields
from datetime import timedelta
from pathlib import Path
from typing import Iterable

from src.earnings_nowcast_contract import parse_utc_timestamp


SCHEMA_VERSION = "catalyst-evidence-v1"
EVENT_TYPES = {"earnings", "product", "regulatory", "customer", "industry", "capital_allocation", "management", "macro"}
EVIDENCE_STATES = {"supported", "candidate_context_only", "still_blocked", "skipped", "excluded"}


@dataclass(frozen=True)
class CatalystEvent:
    schema_version: str
    event_id: str
    profile_key: str
    ticker: str
    event_type: str
    title: str
    effective_at: str
    published_at: str
    retrieved_at: str
    source: str
    source_ref: str
    evidence_state: str
    reviewer: str
    summary: str


FIELDS = tuple(field.name for field in fields(CatalystEvent))


@dataclass(frozen=True)
class EventPreview:
    state: str
    reason: str
    write_performed: bool = False


@dataclass(frozen=True)
class CatalystTimeline:
    ticker: str
    state: str
    upcoming: tuple[CatalystEvent, ...]
    recent: tuple[CatalystEvent, ...]
    rejected_count: int
    boundary: str


def _validation_error(row: CatalystEvent, existing: Iterable[CatalystEvent] = ()) -> str:
    if row.schema_version != SCHEMA_VERSION:
        return f"schema_version must be {SCHEMA_VERSION}"
    for field in FIELDS:
        if not str(getattr(row, field) or "").strip():
            return f"{field} is required"
    if row.event_type not in EVENT_TYPES:
        return "event_type is unsupported"
    if row.evidence_state not in EVIDENCE_STATES:
        return "evidence_state is unsupported"
    if any(existing_row.event_id == row.event_id for existing_row in existing):
        return f"event_id already exists: {row.event_id}"
    identity = (
        row.profile_key, row.ticker.upper(), row.event_type, row.effective_at,
        row.source, row.source_ref,
    )
    if any(
        (
            existing_row.profile_key, existing_row.ticker.upper(), existing_row.event_type,
            existing_row.effective_at, existing_row.source, existing_row.source_ref,
        ) == identity
        for existing_row in existing
    ):
        return "duplicate catalyst evidence already exists for this event and source"
    try:
        published = parse_utc_timestamp(row.published_at, label="published_at")
        retrieved = parse_utc_timestamp(row.retrieved_at, label="retrieved_at")
        parse_utc_timestamp(row.effective_at, label="effective_at")
    except ValueError as exc:
        return str(exc)
    if published > retrieved:
        return "published_at cannot be after retrieved_at"
    return ""


def preview_event(row: CatalystEvent, *, existing: Iterable[CatalystEvent]) -> EventPreview:
    reason = _validation_error(row, tuple(existing))
    if reason:
        return EventPreview("rejected", reason)
    return EventPreview(row.evidence_state, "reviewed event is eligible for append")


def load_catalyst_events(path: Path | str) -> tuple[CatalystEvent, ...]:
    source = Path(path)
    if not source.is_file():
        return ()
    with source.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != FIELDS:
            raise ValueError("Catalyst ledger header does not match the append-only contract.")
        rows = tuple(CatalystEvent(**{field: str(row.get(field) or "").strip() for field in FIELDS}) for row in reader)
    validated: list[CatalystEvent] = []
    for row in rows:
        reason = _validation_error(row, validated)
        if reason:
            raise ValueError(reason)
        validated.append(row)
    return rows


def append_reviewed_event(path: Path | str, row: CatalystEvent, *, confirm_reviewed: bool) -> Path:
    if not confirm_reviewed:
        raise ValueError("confirm_reviewed is required before recording a catalyst event")
    destination = Path(path)
    existing = load_catalyst_events(destination)
    reason = _validation_error(row, existing)
    if reason:
        raise ValueError(reason)
    destination.parent.mkdir(parents=True, exist_ok=True)
    exists = destination.exists() and destination.stat().st_size > 0
    with destination.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        if not exists:
            writer.writeheader()
        writer.writerow(asdict(row))
    return destination


def build_catalyst_timeline(
    rows: Iterable[CatalystEvent],
    *,
    profile_key: str,
    ticker: str,
    as_of: str,
    recent_days: int = 90,
) -> CatalystTimeline:
    cutoff = parse_utc_timestamp(as_of, label="timeline cutoff")
    accepted: list[CatalystEvent] = []
    rejected = 0
    for row in rows:
        if row.profile_key != profile_key or row.ticker.upper() != ticker.upper():
            continue
        reason = _validation_error(row)
        if reason or parse_utc_timestamp(row.published_at) > cutoff or parse_utc_timestamp(row.retrieved_at) > cutoff:
            rejected += 1
            continue
        accepted.append(row)
    upcoming = tuple(sorted((row for row in accepted if parse_utc_timestamp(row.effective_at) >= cutoff), key=lambda row: parse_utc_timestamp(row.effective_at)))
    recent_boundary = cutoff - timedelta(days=recent_days)
    recent = tuple(sorted((row for row in accepted if recent_boundary <= parse_utc_timestamp(row.effective_at) < cutoff), key=lambda row: parse_utc_timestamp(row.effective_at), reverse=True))
    visible = (*upcoming, *recent)
    state = "supported" if any(row.evidence_state == "supported" for row in visible) else "candidate_context_only" if visible else "blocked"
    return CatalystTimeline(
        ticker=ticker.upper(),
        state=state,
        upcoming=upcoming,
        recent=recent,
        rejected_count=rejected,
        boundary="Catalyst evidence is research context only and cannot change forecasts, valuation inputs, readiness, or recommendations.",
    )


def catalyst_timeline_cards(packet: CatalystTimeline) -> list[dict[str, object]]:
    if packet.state == "blocked":
        title = "No cutoff-safe catalyst evidence is available"
        body = "Add a reviewed source reference and publication, retrieval, and effective timestamps before showing an event."
    else:
        title = f"{len(packet.upcoming)} upcoming and {len(packet.recent)} recent reviewed event(s)"
        body = packet.boundary
    return [{
        "kicker": "CATALYST EVIDENCE",
        "title": title,
        "body": body,
        "badges": [packet.state.replace("_", " "), "source-backed only", "context only"],
        "command": "",
    }]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read a source-backed catalyst evidence timeline.")
    parser.add_argument("--ledger", default="data/catalyst_evidence.csv")
    parser.add_argument("--profile-key", default="default")
    parser.add_argument("--ticker")
    parser.add_argument("--as-of")
    parser.add_argument("--preview-input")
    parser.add_argument("--record-input")
    parser.add_argument("--confirm-reviewed", action="store_true")
    args = parser.parse_args(argv)
    if args.preview_input or args.record_input:
        input_path = args.preview_input or args.record_input
        existing = load_catalyst_events(args.ledger)
        candidates = load_catalyst_events(input_path)
        if args.preview_input:
            for row in candidates:
                preview = preview_event(row, existing=existing)
                print(f"{row.event_id}: {preview.state} {preview.reason}".rstrip())
            print("Preview only: no file was changed.")
            return 0
        if not args.confirm_reviewed:
            raise ValueError("record requires --confirm-reviewed after preview and source review")
        for row in candidates:
            append_reviewed_event(args.ledger, row, confirm_reviewed=True)
        print(f"Appended reviewed catalyst events to {args.ledger}")
        return 0
    if not args.ticker or not args.as_of:
        raise ValueError("--ticker and --as-of are required for status")
    packet = build_catalyst_timeline(load_catalyst_events(args.ledger), profile_key=args.profile_key, ticker=args.ticker, as_of=args.as_of)
    print(f"Catalyst evidence timeline\nTicker: {packet.ticker}\nState: {packet.state}\nUpcoming: {len(packet.upcoming)}\nRecent: {len(packet.recent)}")
    print(packet.boundary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
