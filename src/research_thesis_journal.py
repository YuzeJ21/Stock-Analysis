"""Append-only, profile-scoped research thesis and evidence journal."""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable


JOURNAL_SCHEMA_VERSION = "research-thesis-journal-v1"
JOURNAL_COLUMNS = (
    "schema_version",
    "entry_id",
    "profile_key",
    "ticker",
    "thesis_id",
    "entry_type",
    "recorded_at",
    "effective_at",
    "reviewer",
    "summary",
    "evidence_direction",
    "source",
    "source_ref",
    "source_published_at",
    "confidence",
    "review_due_date",
    "supersedes_entry_id",
)
ENTRY_TYPES = {"thesis", "evidence", "catalyst", "risk", "invalidation", "confidence", "review"}
EVIDENCE_DIRECTIONS = {"supporting", "conflicting", "context"}
PROVENANCE_REQUIRED_TYPES = {"evidence", "catalyst", "risk", "invalidation"}


@dataclass(frozen=True)
class JournalEntry:
    schema_version: str
    entry_id: str
    profile_key: str
    ticker: str
    thesis_id: str
    entry_type: str
    recorded_at: str
    effective_at: str
    reviewer: str
    summary: str
    evidence_direction: str
    source: str
    source_ref: str
    source_published_at: str
    confidence: str
    review_due_date: str
    supersedes_entry_id: str


@dataclass(frozen=True)
class JournalState:
    profile_key: str
    ticker: str
    as_of: str
    status: str
    entries: tuple[JournalEntry, ...]
    current_thesis: JournalEntry | None
    thesis_revision_count: int
    confidence_history: tuple[tuple[str, float], ...]
    supporting_evidence: tuple[JournalEntry, ...]
    conflicting_evidence: tuple[JournalEntry, ...]
    contextual_evidence: tuple[JournalEntry, ...]
    catalysts: tuple[JournalEntry, ...]
    risks: tuple[JournalEntry, ...]
    invalidation_conditions: tuple[JournalEntry, ...]
    latest_reviewed_at: str
    review_due_date: str
    overdue: bool


def _parse_timestamp(field: str, value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO-8601 timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone: {value!r}")
    return parsed


def _parse_date(field: str, value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO date: {value!r}") from exc


def _confidence_value(value: str) -> float | None:
    if not str(value or "").strip():
        return None
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ValueError("confidence must be a decimal from 0 through 1") from exc
    if not 0 <= parsed <= 1:
        raise ValueError("confidence must be a decimal from 0 through 1")
    return parsed


def validate_journal_entry(entry: JournalEntry, *, existing_entries: Iterable[JournalEntry]) -> None:
    """Validate one prospective entry against immutable existing history."""

    if entry.schema_version != JOURNAL_SCHEMA_VERSION:
        raise ValueError(f"Unsupported journal schema: {entry.schema_version!r}")
    required = (
        "entry_id",
        "profile_key",
        "ticker",
        "thesis_id",
        "entry_type",
        "recorded_at",
        "effective_at",
        "reviewer",
        "summary",
    )
    for field in required:
        if not str(getattr(entry, field) or "").strip():
            raise ValueError(f"{field} is required")
    if entry.entry_type not in ENTRY_TYPES:
        raise ValueError(f"Unsupported entry_type: {entry.entry_type!r}")
    if entry.evidence_direction and entry.evidence_direction not in EVIDENCE_DIRECTIONS:
        raise ValueError(f"Unsupported evidence_direction: {entry.evidence_direction!r}")
    if entry.entry_type == "evidence" and entry.evidence_direction not in EVIDENCE_DIRECTIONS:
        raise ValueError("evidence_direction is required for evidence entries")
    if entry.entry_type in PROVENANCE_REQUIRED_TYPES and not all(
        str(value or "").strip() for value in (entry.source, entry.source_ref, entry.source_published_at)
    ):
        raise ValueError(f"{entry.entry_type} entries require source, source_ref, and source_published_at")

    recorded_at = _parse_timestamp("recorded_at", entry.recorded_at)
    effective_at = _parse_timestamp("effective_at", entry.effective_at)
    if effective_at > recorded_at:
        raise ValueError("effective_at cannot be after recorded_at")
    if entry.source_published_at:
        source_published_at = _parse_timestamp("source_published_at", entry.source_published_at)
        if source_published_at > recorded_at:
            raise ValueError("source_published_at cannot be after recorded_at")
    if entry.review_due_date:
        _parse_date("review_due_date", entry.review_due_date)
    _confidence_value(entry.confidence)

    existing = tuple(existing_entries)
    if any(row.entry_id == entry.entry_id for row in existing):
        raise ValueError(f"entry_id already exists: {entry.entry_id}")
    target = next((row for row in existing if row.entry_id == entry.supersedes_entry_id), None)
    if entry.supersedes_entry_id:
        if target is None:
            raise ValueError("supersedes_entry_id must reference an existing thesis entry")
        if entry.entry_type != "thesis" or target.entry_type != "thesis":
            raise ValueError("only thesis entries may supersede prior thesis entries")
        if (target.profile_key, target.ticker, target.thesis_id) != (
            entry.profile_key,
            entry.ticker,
            entry.thesis_id,
        ):
            raise ValueError("a thesis revision must supersede an entry for the same profile, ticker, and thesis")
    elif entry.entry_type == "thesis" and any(
        row.entry_type == "thesis"
        and (row.profile_key, row.ticker, row.thesis_id) == (entry.profile_key, entry.ticker, entry.thesis_id)
        for row in existing
    ):
        raise ValueError("a later thesis entry must name supersedes_entry_id")


def load_journal_entries(path: Path | str) -> tuple[JournalEntry, ...]:
    source = Path(path)
    if not source.exists():
        return ()
    try:
        with source.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if tuple(reader.fieldnames or ()) != JOURNAL_COLUMNS:
                raise ValueError("Research thesis journal header does not match the append-only contract.")
            rows = tuple(
                JournalEntry(**{field: str(row.get(field) or "").strip() for field in JOURNAL_COLUMNS})
                for row in reader
            )
    except (OSError, UnicodeError, csv.Error) as exc:
        raise ValueError(f"Unable to read research thesis journal: {exc}") from exc
    validated: list[JournalEntry] = []
    for row in rows:
        validate_journal_entry(row, existing_entries=validated)
        validated.append(row)
    return rows


def append_journal_entry(path: Path | str, entry: JournalEntry) -> Path:
    """Append one reviewed entry without modifying source or readiness data."""

    destination = Path(path)
    existing = load_journal_entries(destination)
    validate_journal_entry(entry, existing_entries=existing)
    destination.parent.mkdir(parents=True, exist_ok=True)
    exists = destination.exists() and destination.stat().st_size > 0
    with destination.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=JOURNAL_COLUMNS)
        if not exists:
            writer.writeheader()
        writer.writerow(asdict(entry))
    return destination


def derive_journal_state(
    entries: Iterable[JournalEntry],
    *,
    profile_key: str,
    ticker: str,
    as_of: str,
) -> JournalState:
    """Derive a selected-profile ticker answer without rewriting journal history."""

    as_of_dt = _parse_timestamp("as_of", as_of)
    normalized_ticker = str(ticker or "").strip().upper()
    scoped = tuple(
        sorted(
            (
                row
                for row in entries
                if row.profile_key == profile_key and row.ticker.strip().upper() == normalized_ticker
            ),
            key=lambda row: (_parse_timestamp("recorded_at", row.recorded_at), row.entry_id),
        )
    )
    theses = tuple(row for row in scoped if row.entry_type == "thesis")
    superseded_ids = {row.supersedes_entry_id for row in theses if row.supersedes_entry_id}
    active_theses = tuple(row for row in theses if row.entry_id not in superseded_ids)
    if len(active_theses) > 1:
        raise ValueError("Journal contains more than one active thesis for the selected ticker.")
    current_thesis = active_theses[0] if active_theses else None
    confidence_history = tuple(
        (row.recorded_at, value)
        for row in scoped
        if (value := _confidence_value(row.confidence)) is not None
    )
    invalidations = tuple(row for row in scoped if row.entry_type == "invalidation")
    due_date = ""
    for row in reversed(scoped):
        if row.review_due_date:
            due_date = row.review_due_date
            break
    overdue = bool(due_date and _parse_date("review_due_date", due_date) < as_of_dt.date())
    if current_thesis is None:
        status = "not_started"
    elif not invalidations:
        status = "incomplete"
    elif overdue:
        status = "overdue"
    else:
        status = "current"
    return JournalState(
        profile_key=profile_key,
        ticker=normalized_ticker,
        as_of=as_of,
        status=status,
        entries=scoped,
        current_thesis=current_thesis,
        thesis_revision_count=max(len(theses) - 1, 0),
        confidence_history=confidence_history,
        supporting_evidence=tuple(
            row for row in scoped if row.entry_type == "evidence" and row.evidence_direction == "supporting"
        ),
        conflicting_evidence=tuple(
            row for row in scoped if row.entry_type == "evidence" and row.evidence_direction == "conflicting"
        ),
        contextual_evidence=tuple(
            row for row in scoped if row.entry_type == "evidence" and row.evidence_direction == "context"
        ),
        catalysts=tuple(row for row in scoped if row.entry_type == "catalyst"),
        risks=tuple(row for row in scoped if row.entry_type == "risk"),
        invalidation_conditions=invalidations,
        latest_reviewed_at=scoped[-1].recorded_at if scoped else "",
        review_due_date=due_date,
        overdue=overdue,
    )
