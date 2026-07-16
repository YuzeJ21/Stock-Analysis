"""Append-only, profile-scoped research thesis and evidence journal."""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
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


def _next_research_action(state: JournalState) -> str:
    if state.status == "not_started":
        return "Record a reviewed hypothesis with an explicit review date."
    if state.status == "incomplete":
        return "Record at least one source-backed invalidation condition."
    if state.status == "overdue":
        return "Review the recorded hypothesis and its conflicting evidence before relying on it."
    if state.conflicting_evidence:
        return "Review the latest conflicting evidence against the current hypothesis."
    return "Revisit this journal when source evidence changes or the review date arrives."


def render_journal_state(state: JournalState) -> str:
    """Render a plain-language, research-only selected-ticker journal answer."""

    lines = [
        "Research Thesis and Evidence Journal",
        f"Profile: {state.profile_key}",
        f"Ticker: {state.ticker}",
        f"Status: {state.status}",
    ]
    if state.current_thesis is None:
        lines.append("No reviewed thesis is recorded for this profile and ticker.")
    else:
        lines.extend(
            [
                f"Current hypothesis: {state.current_thesis.summary}",
                f"Thesis revisions: {state.thesis_revision_count}",
                (
                    "Evidence: "
                    f"{len(state.supporting_evidence)} supporting, "
                    f"{len(state.conflicting_evidence)} conflicting, "
                    f"{len(state.contextual_evidence)} contextual"
                ),
                f"Catalysts: {len(state.catalysts)} | Risks: {len(state.risks)}",
                f"Invalidation conditions: {len(state.invalidation_conditions)}",
            ]
        )
        if state.confidence_history:
            lines.append(f"Latest documented confidence: {state.confidence_history[-1][1]:.2f}")
        if state.latest_reviewed_at:
            lines.append(f"Latest review: {state.latest_reviewed_at}")
        if state.review_due_date:
            lines.append(f"Next review due: {state.review_due_date}")
    lines.append(f"Next research action: {_next_research_action(state)}")
    lines.append("Boundary: confidence describes the documented research hypothesis only.")
    return "\n".join(lines)


def preview_journal_entry(entry: JournalEntry, *, existing_entries: Iterable[JournalEntry]) -> str:
    """Validate and render one prospective row without writing it."""

    validate_journal_entry(entry, existing_entries=existing_entries)
    lines = ["Research Thesis Journal Entry", "Preview only: no file was changed."]
    lines.extend(f"{field}: {getattr(entry, field)}" for field in JOURNAL_COLUMNS)
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Review an append-only research thesis journal.")
    parser.add_argument("--ledger", default="data/research_thesis_journal.csv")
    parser.add_argument("--ticker")
    parser.add_argument("--profile-key", default="default")
    parser.add_argument("--as-of")
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--record", action="store_true")
    parser.add_argument("--confirm-reviewed", action="store_true")
    for field in JOURNAL_COLUMNS:
        if field in {"profile_key", "ticker"}:
            continue
        parser.add_argument("--" + field.replace("_", "-"), dest=field)
    return parser.parse_args(argv)


def _entry_from_args(args: argparse.Namespace) -> JournalEntry:
    values = {field: str(getattr(args, field, "") or "").strip() for field in JOURNAL_COLUMNS}
    values["profile_key"] = str(args.profile_key or "").strip()
    return JournalEntry(**values)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.preview or args.record:
        entry = _entry_from_args(args)
        existing = load_journal_entries(args.ledger)
        if args.preview:
            print(preview_journal_entry(entry, existing_entries=existing))
            return 0
        if not args.confirm_reviewed:
            raise ValueError("Recording requires --confirm-reviewed after preview and source review.")
        append_journal_entry(args.ledger, entry)
        print(f"Appended reviewed thesis journal entry: {entry.entry_id} -> {args.ledger}")
        return 0
    if not str(args.ticker or "").strip():
        raise ValueError("--ticker is required to read the research thesis journal")
    as_of = args.as_of or datetime.now(UTC).isoformat().replace("+00:00", "Z")
    state = derive_journal_state(
        load_journal_entries(args.ledger),
        profile_key=args.profile_key,
        ticker=args.ticker,
        as_of=as_of,
    )
    print(render_journal_state(state))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
