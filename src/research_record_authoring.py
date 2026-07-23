"""Pure preview composition for reviewed research-record authoring."""

from __future__ import annotations

import csv
import hashlib
import hmac
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from src.catalyst_evidence_timeline import (
    CatalystEvent,
    append_reviewed_event,
    load_catalyst_events,
    preview_event,
)
from src.research_outcome_review import (
    ResearchOutcome,
    append_reviewed_outcome,
    load_outcomes,
    preview_outcome,
)
from src.research_thesis_journal import (
    JOURNAL_SCHEMA_VERSION,
    JournalEntry,
    append_journal_entry,
    load_journal_entries,
    validate_journal_entry,
)
from src.research_ledger_lock import ledger_write_lock, resolve_ledger_path


RECORD_KINDS = ("thesis", "evidence", "catalyst", "outcome")


@dataclass(frozen=True)
class AuthoringPaths:
    journal: Path
    catalysts: Path
    outcomes: Path

    def all(self) -> tuple[Path, Path, Path]:
        return (self.journal, self.catalysts, self.outcomes)


@dataclass(frozen=True)
class AuthoringDraft:
    record_kind: str
    profile_key: str
    ticker: str
    fields: tuple[tuple[str, str], ...]

    def field_map(self) -> Mapping[str, str]:
        return MappingProxyType(dict(self.fields))


@dataclass(frozen=True)
class AuthoringPreview:
    state: str
    reason: str
    record_kind: str
    profile_key: str
    ticker: str
    destination_label: str
    previewed_at: str
    persisted_fields: tuple[tuple[str, str], ...]
    receipt: str
    draft_digest: str
    ledger_fingerprint: str
    record: JournalEntry | CatalystEvent | ResearchOutcome | None
    write_performed: bool = False


@dataclass(frozen=True)
class AuthoringSaveResult:
    state: str
    reason: str
    record_kind: str
    record_id: str
    destination_label: str
    write_performed: bool


def build_authoring_draft(
    record_kind: str,
    *,
    profile_key: str,
    ticker: str,
    fields: Mapping[str, object],
) -> AuthoringDraft:
    kind = str(record_kind or "").strip().lower()
    if kind not in RECORD_KINDS:
        raise ValueError(f"Unsupported record kind: {record_kind!r}")
    profile = str(profile_key or "").strip()
    symbol = str(ticker or "").strip().upper()
    if not profile:
        raise ValueError("profile_key is required")
    if not symbol:
        raise ValueError("ticker is required")
    normalized = tuple(sorted((str(key), str(value or "").strip()) for key, value in fields.items()))
    return AuthoringDraft(kind, profile, symbol, normalized)


def _stable_digest(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(encoded).hexdigest()


def authoring_draft_digest(draft: AuthoringDraft) -> str:
    return _stable_digest(asdict(draft))


def _ledger_fingerprint(path: Path) -> str:
    payload = b"missing\0" if not path.exists() else b"present\0" + path.read_bytes()
    return hashlib.sha256(payload).hexdigest()


def _destination(draft: AuthoringDraft, paths: AuthoringPaths) -> Path:
    if draft.record_kind in {"thesis", "evidence"}:
        return paths.journal
    if draft.record_kind == "catalyst":
        return paths.catalysts
    return paths.outcomes


def _record_id(record: JournalEntry | CatalystEvent | ResearchOutcome) -> str:
    if isinstance(record, JournalEntry):
        return record.entry_id
    if isinstance(record, CatalystEvent):
        return record.event_id
    return record.outcome_id


def _scoped_theses(paths: AuthoringPaths, draft: AuthoringDraft) -> tuple[JournalEntry, ...]:
    return tuple(
        row
        for row in load_journal_entries(paths.journal)
        if row.entry_type == "thesis"
        and row.profile_key == draft.profile_key
        and row.ticker.upper() == draft.ticker
    )


def _build_record(
    draft: AuthoringDraft,
    *,
    previewed_at: str,
    generated_id: str,
    paths: AuthoringPaths,
) -> JournalEntry | CatalystEvent | ResearchOutcome:
    values = dict(draft.fields)
    if draft.record_kind in {"thesis", "evidence"}:
        if draft.record_kind == "evidence" and not any(
            row.thesis_id == values.get("thesis_id") for row in _scoped_theses(paths, draft)
        ):
            raise ValueError("thesis_id must reference an existing thesis in this profile and ticker")
        return JournalEntry(
            schema_version=JOURNAL_SCHEMA_VERSION,
            entry_id=generated_id,
            profile_key=draft.profile_key,
            ticker=draft.ticker,
            thesis_id=values.get("thesis_id", ""),
            entry_type=draft.record_kind,
            recorded_at=previewed_at,
            effective_at=values.get("effective_at", ""),
            reviewer=values.get("reviewer", ""),
            summary=values.get("summary", ""),
            evidence_direction=values.get("evidence_direction", ""),
            source=values.get("source", ""),
            source_ref=values.get("source_ref", ""),
            source_published_at=values.get("source_published_at", ""),
            confidence=values.get("confidence", ""),
            review_due_date=values.get("review_due_date", ""),
            supersedes_entry_id=values.get("supersedes_entry_id", ""),
        )
    if draft.record_kind == "catalyst":
        return CatalystEvent(
            schema_version="catalyst-evidence-v1",
            event_id=generated_id,
            profile_key=draft.profile_key,
            ticker=draft.ticker,
            **values,
        )
    theses = _scoped_theses(paths, draft)
    if not any(
        row.thesis_id == values.get("thesis_id")
        and row.entry_id == values.get("original_thesis_entry_id")
        for row in theses
    ):
        raise ValueError("outcome must reference an existing thesis entry in this profile and ticker")
    return ResearchOutcome(
        schema_version="research-outcome-review-v1",
        outcome_id=generated_id,
        profile_key=draft.profile_key,
        ticker=draft.ticker,
        **values,
    )


def preview_authoring_record(
    draft: AuthoringDraft,
    *,
    paths: AuthoringPaths,
    previewed_at: str,
    generated_id: str,
) -> AuthoringPreview:
    destination = _destination(draft, paths)
    draft_digest = authoring_draft_digest(draft)
    ledger_fingerprint = ""
    try:
        ledger_fingerprint = _ledger_fingerprint(destination)
        record = _build_record(draft, previewed_at=previewed_at, generated_id=generated_id, paths=paths)
        if isinstance(record, JournalEntry):
            validate_journal_entry(record, existing_entries=load_journal_entries(paths.journal))
        elif isinstance(record, CatalystEvent):
            event_preview = preview_event(record, existing=load_catalyst_events(paths.catalysts))
            if event_preview.state == "rejected":
                raise ValueError(event_preview.reason)
        else:
            outcome_preview = preview_outcome(record, existing=load_outcomes(paths.outcomes))
            if outcome_preview.state == "rejected":
                raise ValueError(outcome_preview.reason)
    except (OSError, UnicodeError, csv.Error, ValueError) as exc:
        return AuthoringPreview(
            "rejected",
            str(exc),
            draft.record_kind,
            draft.profile_key,
            draft.ticker,
            destination.name,
            previewed_at,
            (),
            "",
            draft_digest,
            ledger_fingerprint,
            None,
        )
    persisted = tuple((key, str(value)) for key, value in asdict(record).items())
    receipt = _stable_digest(
        {
            "draft": draft_digest,
            "ledger": ledger_fingerprint,
            "record": persisted,
            "previewed_at": previewed_at,
            "destination_label": destination.name,
            "destination": str(resolve_ledger_path(destination)),
        }
    )
    return AuthoringPreview(
        "reviewable",
        "",
        draft.record_kind,
        draft.profile_key,
        draft.ticker,
        destination.name,
        previewed_at,
        persisted,
        receipt,
        draft_digest,
        ledger_fingerprint,
        record,
    )


def confirm_authoring_preview(
    preview: AuthoringPreview,
    *,
    current_draft: AuthoringDraft,
    paths: AuthoringPaths,
    active_profile_key: str,
    active_ticker: str,
    active_kind: str,
    confirm_reviewed: bool,
) -> AuthoringSaveResult:
    def rejected(state: str, reason: str) -> AuthoringSaveResult:
        return AuthoringSaveResult(
            state,
            reason,
            preview.record_kind,
            "",
            preview.destination_label,
            False,
        )
    if not confirm_reviewed:
        return rejected("confirmation_required", "Review and confirm the exact preview before saving.")
    if preview.state != "reviewable" or preview.record is None or not preview.receipt:
        return rejected("rejected", "Only a valid preview can be confirmed.")
    active = (
        str(active_profile_key or "").strip(),
        str(active_ticker or "").strip().upper(),
        str(active_kind or "").strip().lower(),
    )
    if active != (preview.profile_key, preview.ticker, preview.record_kind):
        return rejected("preview_stale", "Selected profile, ticker, or record type changed; preview again.")
    if not hmac.compare_digest(_stable_digest(asdict(current_draft)), preview.draft_digest):
        return rejected("preview_stale", "Draft changed after preview; preview again.")
    destination = _destination(current_draft, paths)
    result: AuthoringSaveResult | None = None
    append_completed = False
    persisted_record: JournalEntry | CatalystEvent | ResearchOutcome | None = None
    try:
        with ledger_write_lock(destination):
            if not hmac.compare_digest(_ledger_fingerprint(destination), preview.ledger_fingerprint):
                result = rejected("preview_stale", "Ledger changed after preview; reload and preview again.")
            else:
                refreshed = preview_authoring_record(
                    current_draft,
                    paths=paths,
                    previewed_at=preview.previewed_at,
                    generated_id=_record_id(preview.record),
                )
                if (
                    refreshed.state != "reviewable"
                    or not hmac.compare_digest(refreshed.receipt, preview.receipt)
                    or refreshed.persisted_fields != preview.persisted_fields
                    or refreshed.destination_label != preview.destination_label
                ):
                    result = rejected("preview_stale", "Record no longer matches the validated preview; preview again.")
                elif not hmac.compare_digest(_ledger_fingerprint(destination), refreshed.ledger_fingerprint):
                    result = rejected("preview_stale", "Ledger changed during preview revalidation; preview again.")
                else:
                    refreshed_record = refreshed.record
                    if refreshed_record is None:
                        result = rejected(
                            "preview_stale",
                            "Record no longer matches the validated preview; preview again.",
                        )
                    else:
                        try:
                            if isinstance(refreshed_record, JournalEntry):
                                append_journal_entry(paths.journal, refreshed_record)
                            elif isinstance(refreshed_record, CatalystEvent):
                                append_reviewed_event(
                                    paths.catalysts, refreshed_record, confirm_reviewed=True
                                )
                            else:
                                append_reviewed_outcome(
                                    paths.outcomes, refreshed_record, confirm_reviewed=True
                                )
                        except (OSError, UnicodeError, csv.Error, ValueError) as exc:
                            try:
                                ledger_changed = not hmac.compare_digest(
                                    _ledger_fingerprint(destination),
                                    refreshed.ledger_fingerprint,
                                )
                            except (OSError, UnicodeError, csv.Error):
                                ledger_changed = True
                            if ledger_changed:
                                result = AuthoringSaveResult(
                                    "save_pending_reload",
                                    "Save completion could not be verified; reloading the ledger once before retry.",
                                    preview.record_kind,
                                    _record_id(refreshed_record),
                                    destination.name,
                                    False,
                                )
                            else:
                                result = rejected("save_failed", f"Record was not saved: {exc}")
                        else:
                            persisted_record = refreshed_record
                            append_completed = True
    except OSError as exc:
        if result is not None and result.state == "save_pending_reload":
            return result
        if append_completed:
            return AuthoringSaveResult(
                "save_pending_reload",
                "Save completion could not be verified; reloading the ledger once before retry.",
                preview.record_kind,
                _record_id(persisted_record) if persisted_record is not None else "",
                destination.name,
                False,
            )
        return rejected("save_failed", f"Record was not saved: {exc}")
    if result is not None:
        return result
    if not append_completed:
        return rejected("save_failed", "Record was not saved before confirmation completed.")
    return AuthoringSaveResult(
        "saved",
        "Saved append-only reviewed record.",
        preview.record_kind,
        _record_id(persisted_record) if persisted_record is not None else "",
        destination.name,
        True,
    )
