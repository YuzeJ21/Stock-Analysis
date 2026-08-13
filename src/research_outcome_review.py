"""Append-only research outcome review for learning from prior thesis work."""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Iterable, Mapping

from src.commercial_source_rights import (
    SourceRights,
    load_source_rights_registry,
    review_commercial_field_scope,
)
from src.earnings_nowcast_contract import parse_utc_timestamp
from src.research_ledger_lock import ledger_write_lock


SCHEMA_VERSION = "research-outcome-review-v1"
OUTCOME_STATES = {"supported", "mixed", "not_supported", "inconclusive"}


@dataclass(frozen=True)
class ResearchOutcome:
    schema_version: str
    outcome_id: str
    profile_key: str
    ticker: str
    thesis_id: str
    original_thesis_entry_id: str
    reviewed_at: str
    observation_start: str
    observation_end: str
    reviewer: str
    outcome_state: str
    summary: str
    source: str
    source_ref: str
    source_published_at: str
    learning: str


FIELDS = tuple(field.name for field in fields(ResearchOutcome))


@dataclass(frozen=True)
class OutcomePreview:
    state: str
    reason: str
    fields: tuple[str, ...]
    write_performed: bool = False


@dataclass(frozen=True)
class OutcomeStatus:
    state: str
    review_count: int
    latest_outcome_state: str
    latest_learning: str
    next_action: str
    commercial_blocker_count: int
    commercial_blockers: tuple[str, ...]


def _validation_error(row: ResearchOutcome, existing: Iterable[ResearchOutcome]) -> str:
    if row.schema_version != SCHEMA_VERSION:
        return f"schema_version must be {SCHEMA_VERSION}"
    for field in FIELDS:
        if not str(getattr(row, field) or "").strip():
            return f"{field} is required"
    if row.outcome_state not in OUTCOME_STATES:
        return "outcome_state is unsupported"
    if any(existing_row.outcome_id == row.outcome_id for existing_row in existing):
        return f"outcome_id already exists: {row.outcome_id}"
    identity = (
        row.profile_key, row.ticker.upper(), row.thesis_id, row.original_thesis_entry_id,
        row.observation_start, row.observation_end, row.source_ref,
    )
    if any(
        (
            existing_row.profile_key, existing_row.ticker.upper(), existing_row.thesis_id,
            existing_row.original_thesis_entry_id, existing_row.observation_start,
            existing_row.observation_end, existing_row.source_ref,
        ) == identity
        for existing_row in existing
    ):
        return "duplicate outcome evidence already exists for this thesis and observation window"
    try:
        reviewed = parse_utc_timestamp(row.reviewed_at, label="reviewed_at")
        start = parse_utc_timestamp(row.observation_start, label="observation_start")
        end = parse_utc_timestamp(row.observation_end, label="observation_end")
        published = parse_utc_timestamp(row.source_published_at, label="source_published_at")
    except ValueError as exc:
        return str(exc)
    if start > end:
        return "observation_start cannot be after observation_end"
    if end > reviewed:
        return "observation_end cannot be after reviewed_at"
    if published > reviewed:
        return "source_published_at cannot be after reviewed_at"
    return ""


def preview_outcome(row: ResearchOutcome, *, existing: Iterable[ResearchOutcome]) -> OutcomePreview:
    reason = _validation_error(row, tuple(existing))
    return OutcomePreview("rejected" if reason else "reviewable", reason, FIELDS)


def load_outcomes(path: Path | str) -> tuple[ResearchOutcome, ...]:
    source = Path(path)
    if not source.is_file():
        return ()
    with source.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != FIELDS:
            raise ValueError("Research outcome ledger header does not match the append-only contract.")
        rows = tuple(ResearchOutcome(**{field: str(row.get(field) or "").strip() for field in FIELDS}) for row in reader)
    validated: list[ResearchOutcome] = []
    for row in rows:
        reason = _validation_error(row, validated)
        if reason:
            raise ValueError(reason)
        validated.append(row)
    return rows


def append_reviewed_outcome(path: Path | str, row: ResearchOutcome, *, confirm_reviewed: bool) -> Path:
    if not confirm_reviewed:
        raise ValueError("confirm_reviewed is required before recording an outcome")
    destination = Path(path)
    with ledger_write_lock(destination):
        existing = load_outcomes(destination)
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


def derive_outcome_status(
    rows: Iterable[ResearchOutcome], *, profile_key: str, ticker: str,
    commercial_mode: bool = False,
    rights_registry: Mapping[str, SourceRights] | None = None,
) -> OutcomeStatus:
    scoped = sorted(
        (row for row in rows if row.profile_key == profile_key and row.ticker.upper() == ticker.upper()),
        key=lambda row: parse_utc_timestamp(row.reviewed_at),
    )
    if not scoped:
        return OutcomeStatus("not_started", 0, "", "", "Record an outcome only after the observation window closes and evidence is reviewed.", 0, ())
    commercial_blockers: list[str] = []
    if commercial_mode:
        registry = rights_registry if rights_registry is not None else load_source_rights_registry()
        for row in scoped:
            review = review_commercial_field_scope(
                registry, row.source, ("research_outcomes",)
            )
            if not review.commercial_evidence_ready:
                missing = ", ".join(review.missing_supported_fields) or "research_outcomes"
                commercial_blockers.append(
                    f"{row.outcome_id}: exact source {row.source or '-'} is {review.rights_status}; "
                    f"registered scope missing: {missing}"
                )
    if commercial_blockers:
        return OutcomeStatus(
            "commercial_evidence_blocked", 0, "", "",
            "Review exact-source rights and registered research_outcomes scope before using this learning record.",
            len(commercial_blockers), tuple(commercial_blockers),
        )
    latest = scoped[-1]
    return OutcomeStatus(
        "reviewed",
        len(scoped),
        latest.outcome_state,
        latest.learning,
        "Use the recorded learning when the thesis is next reviewed.",
        0,
        (),
    )


def outcome_status_cards(status: OutcomeStatus) -> list[dict[str, object]]:
    if status.state == "not_started":
        title = "No research outcome review is due yet"
        body = status.next_action
    elif status.state == "commercial_evidence_blocked":
        title = "Research outcome commercial evidence is blocked"
        body = (
            f"{status.commercial_blocker_count} outcome row(s) lack approved exact-source "
            "rights or registered research-outcomes scope."
        )
    else:
        title = f"Latest reviewed outcome: {status.latest_outcome_state.replace('_', ' ')}"
        body = f"{status.review_count} reviewed learning record(s). Latest learning: {status.latest_learning}"
    return [{
        "kicker": "RESEARCH LEARNING",
        "title": title,
        "body": body,
        "badges": [status.state.replace("_", " "), "append-only", "no performance scoring"],
        "command": "",
    }]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read an append-only research outcome review ledger.")
    parser.add_argument("--ledger", default="data/research_outcome_reviews.csv")
    parser.add_argument("--profile-key", default="default")
    parser.add_argument("--ticker")
    parser.add_argument("--preview-input")
    parser.add_argument("--record-input")
    parser.add_argument("--confirm-reviewed", action="store_true")
    args = parser.parse_args(argv)
    if args.preview_input or args.record_input:
        input_path = args.preview_input or args.record_input
        existing = load_outcomes(args.ledger)
        candidates = load_outcomes(input_path)
        if args.preview_input:
            for row in candidates:
                preview = preview_outcome(row, existing=existing)
                print(f"{row.outcome_id}: {preview.state} {preview.reason}".rstrip())
            print("Preview only: no file was changed.")
            return 0
        if not args.confirm_reviewed:
            raise ValueError("record requires --confirm-reviewed after preview and source review")
        for row in candidates:
            append_reviewed_outcome(args.ledger, row, confirm_reviewed=True)
        print(f"Appended reviewed research outcomes to {args.ledger}")
        return 0
    if not args.ticker:
        raise ValueError("--ticker is required for status")
    status = derive_outcome_status(load_outcomes(args.ledger), profile_key=args.profile_key, ticker=args.ticker)
    print(f"Research outcome review\nTicker: {args.ticker.upper()}\nState: {status.state}\nReviews: {status.review_count}\nNext: {status.next_action}")
    print("Boundary: this is a research-process learning record, not return attribution, skill scoring, or investment advice.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
