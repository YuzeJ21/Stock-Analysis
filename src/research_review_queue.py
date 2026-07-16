"""Derive a research review queue from change events and append-only outcomes."""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from src.research_change_monitor import ResearchChangeEvent
from src.research_change_monitor import compare_optional_snapshots
from src.research_change_snapshot import load_research_change_snapshot


REVIEW_SCHEMA_VERSION = "research-event-review-v1"
REVIEW_LEDGER_COLUMNS = (
    "schema_version",
    "event_id",
    "profile_key",
    "ticker",
    "review_status",
    "reviewed_at",
    "reviewer",
    "resolution_note",
    "source_ref",
    "prior_snapshot_identity",
    "current_snapshot_identity",
)
OPEN_STATUSES = {"open", "still_blocked", "intentionally_deferred"}
RESOLVED_STATUSES = {"reviewed_no_change", "reviewed_supported", "skipped", "excluded"}
VALID_REVIEW_STATUSES = OPEN_STATUSES | RESOLVED_STATUSES
PRIORITY_BY_SUBTYPE = {
    "input_became_stale": 10,
    "sec_filing_arrived": 20,
    "shares_outstanding_revised": 30,
    "fundamentals_revised": 30,
    "nowcast_consensus_changed": 30,
    "dcf_readiness_changed": 40,
    "fundamentals_readiness_changed": 40,
    "peer_readiness_changed": 40,
    "price_readiness_changed": 40,
    "momentum_readiness_changed": 50,
    "price_history_advanced": 50,
}
MATERIALITY_ORDER = {"high": 0, "medium": 1, "context": 2}


@dataclass(frozen=True)
class ReviewResolution:
    schema_version: str
    event_id: str
    profile_key: str
    ticker: str
    review_status: str
    reviewed_at: str
    reviewer: str
    resolution_note: str
    source_ref: str
    prior_snapshot_identity: str
    current_snapshot_identity: str


@dataclass(frozen=True)
class ResearchReviewItem:
    event: ResearchChangeEvent
    priority: int
    review_status: str
    reviewed_at: str
    resolution_note: str
    wait_condition: str


def _valid_datetime(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"reviewed_at must be an ISO timestamp: {value!r}") from exc


def _validate_resolution(resolution: ReviewResolution) -> None:
    if resolution.schema_version != REVIEW_SCHEMA_VERSION:
        raise ValueError(f"Unsupported research review schema: {resolution.schema_version!r}")
    if resolution.review_status not in VALID_REVIEW_STATUSES - {"open"}:
        raise ValueError(f"Unsupported research review status: {resolution.review_status!r}")
    for field in REVIEW_LEDGER_COLUMNS:
        if not str(getattr(resolution, field) or "").strip():
            raise ValueError(f"{field} is required for a reviewed event outcome")
    _valid_datetime(resolution.reviewed_at)


def append_review_resolution(path: Path | str, resolution: ReviewResolution) -> Path:
    """Append one reviewed outcome without modifying event or readiness artifacts."""

    _validate_resolution(resolution)
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    exists = destination.exists() and destination.stat().st_size > 0
    if exists:
        with destination.open(newline="", encoding="utf-8") as handle:
            header = next(csv.reader(handle), [])
        if header != list(REVIEW_LEDGER_COLUMNS):
            raise ValueError("Research review ledger header does not match the append-only contract.")
    with destination.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_LEDGER_COLUMNS)
        if not exists:
            writer.writeheader()
        writer.writerow(asdict(resolution))
    return destination


def load_review_resolutions(path: Path | str) -> tuple[ReviewResolution, ...]:
    source = Path(path)
    if not source.exists():
        return ()
    try:
        with source.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if tuple(reader.fieldnames or ()) != REVIEW_LEDGER_COLUMNS:
                raise ValueError("Research review ledger header does not match the append-only contract.")
            rows = tuple(ReviewResolution(**{field: str(row.get(field) or "").strip() for field in REVIEW_LEDGER_COLUMNS}) for row in reader)
    except (OSError, UnicodeError, csv.Error) as exc:
        raise ValueError(f"Unable to read research review ledger: {exc}") from exc
    for row in rows:
        _validate_resolution(row)
    return rows


def priority_for_event(event: ResearchChangeEvent) -> int:
    if event.subtype in {"dcf_readiness_changed", "fundamentals_readiness_changed"}:
        if event.prior_value == "true" and event.current_value == "false":
            return 10
    return PRIORITY_BY_SUBTYPE.get(event.subtype, 60)


def _latest_by_event(resolutions: Iterable[ReviewResolution]) -> dict[str, ReviewResolution]:
    latest: dict[str, ReviewResolution] = {}
    for resolution in resolutions:
        current = latest.get(resolution.event_id)
        if current is None or _valid_datetime(resolution.reviewed_at) > _valid_datetime(current.reviewed_at):
            latest[resolution.event_id] = resolution
    return latest


def _resolution_matches_event(resolution: ReviewResolution, event: ResearchChangeEvent) -> bool:
    return (
        resolution.profile_key == event.profile_key
        and resolution.ticker == event.ticker
        and resolution.prior_snapshot_identity == event.prior_snapshot_identity
        and resolution.current_snapshot_identity == event.current_snapshot_identity
    )


def _timestamp_sort_value(value: str) -> float:
    try:
        return -datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def build_research_review_queue(
    events: Iterable[ResearchChangeEvent],
    *,
    resolutions: Iterable[ReviewResolution],
) -> tuple[ResearchReviewItem, ...]:
    latest = _latest_by_event(resolutions)
    queue: list[ResearchReviewItem] = []
    for event in events:
        resolution = latest.get(event.event_id)
        if resolution is not None and not _resolution_matches_event(resolution, event):
            resolution = None
        status = resolution.review_status if resolution else "open"
        if status in RESOLVED_STATUSES:
            continue
        wait_condition = ""
        if status == "still_blocked":
            wait_condition = "Reviewed evidence remains blocked; wait for new source evidence."
        elif status == "intentionally_deferred":
            wait_condition = "Review is intentionally deferred until the recorded condition changes."
        queue.append(
            ResearchReviewItem(
                event=event,
                priority=priority_for_event(event),
                review_status=status,
                reviewed_at=resolution.reviewed_at if resolution else "",
                resolution_note=resolution.resolution_note if resolution else "",
                wait_condition=wait_condition,
            )
        )
    return tuple(
        sorted(
            queue,
            key=lambda item: (
                item.priority,
                MATERIALITY_ORDER.get(item.event.materiality, 3),
                _timestamp_sort_value(item.event.source_published_at),
                _timestamp_sort_value(item.event.detected_at),
                item.event.ticker,
                item.event.event_id,
            ),
        )
    )


def render_research_review_queue(items: Iterable[ResearchReviewItem]) -> str:
    rows = tuple(items)
    if not rows:
        return "Research Review Queue\nOpen items: 0\nNo unresolved evidence-backed changes."
    lines = ["Research Review Queue", f"Open items: {len(rows)}"]
    lines.extend(
        (
            f"- P{item.priority} | {item.event.ticker} | {item.event.subtype} | "
            f"{item.review_status} | {item.event.suggested_research_task}"
            + (f" Wait: {item.wait_condition}" if item.wait_condition else "")
        )
        for item in rows
    )
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Review unresolved research changes without mutating readiness.")
    parser.add_argument("--before")
    parser.add_argument("--after")
    parser.add_argument("--top-n", type=int, default=25)
    parser.add_argument("--ledger", default="data/reviewed_research_events.csv")
    parser.add_argument("--record", action="store_true")
    parser.add_argument("--event-id")
    parser.add_argument("--profile-key")
    parser.add_argument("--ticker")
    parser.add_argument("--status")
    parser.add_argument("--reviewed-at")
    parser.add_argument("--reviewer")
    parser.add_argument("--resolution-note")
    parser.add_argument("--source-ref")
    parser.add_argument("--prior-snapshot-identity")
    parser.add_argument("--current-snapshot-identity")
    return parser.parse_args(argv)


def _record_from_args(args: argparse.Namespace) -> ReviewResolution:
    values = {
        "event_id": args.event_id,
        "profile_key": args.profile_key,
        "ticker": args.ticker,
        "review_status": args.status,
        "reviewed_at": args.reviewed_at,
        "reviewer": args.reviewer,
        "resolution_note": args.resolution_note,
        "source_ref": args.source_ref,
        "prior_snapshot_identity": args.prior_snapshot_identity,
        "current_snapshot_identity": args.current_snapshot_identity,
    }
    missing = [field for field, value in values.items() if not str(value or "").strip()]
    if missing:
        raise ValueError("Recording a research event review requires: " + ", ".join(missing))
    return ReviewResolution(schema_version=REVIEW_SCHEMA_VERSION, **values)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.record:
        destination = append_review_resolution(args.ledger, _record_from_args(args))
        print(f"Appended reviewed research event outcome: {destination}")
        return 0
    if not args.after:
        raise ValueError("--after is required to build the research review queue")
    before_path = Path(args.before) if args.before else None
    after_path = Path(args.after)
    before = load_research_change_snapshot(before_path) if before_path and before_path.is_file() else None
    if not after_path.is_file():
        raise ValueError(f"Current research change snapshot is missing: {after_path}")
    result = compare_optional_snapshots(before, load_research_change_snapshot(after_path))
    queue = build_research_review_queue(
        result.events,
        resolutions=load_review_resolutions(args.ledger),
    )[: max(args.top_n, 0)]
    print(f"Change status: {result.status}")
    print(render_research_review_queue(queue))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
