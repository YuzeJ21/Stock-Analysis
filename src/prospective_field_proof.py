"""Strict, append-only records for prospective per-field review proof."""

from __future__ import annotations

import csv
import fcntl
import hashlib
import io
import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import BinaryIO, Mapping, Sequence

from src.commercial_source_rights import (
    SourceRights,
    commercial_mode_enabled,
    load_source_rights_registry,
    review_commercial_field_scope,
)
from src.earnings_nowcast_contract import parse_utc_timestamp


SCHEMA_VERSION = "prospective-field-proof-v1"
FIELDS = (
    "schema_version",
    "proof_id",
    "ticker",
    "field_key",
    "readiness_contract_version",
    "observed_at",
    "retrieved_at",
    "source_id",
    "source_ref",
    "source_status",
    "rights_status",
    "rights_decision_ref",
    "payload_status",
    "payload_sha256",
    "reviewer_id",
    "reviewer_decision",
    "reviewed_at",
    "supersedes_proof_id",
)

_SOURCE_STATUSES = frozenset({"identified", "unavailable", "disputed"})
_RIGHTS_STATUSES = frozenset({"approved", "unverified", "restricted", "not_applicable"})
_PAYLOAD_STATUSES = frozenset({"reviewed", "unavailable", "rejected"})
_REVIEWER_DECISIONS = frozenset({"accepted", "rejected", "needs_follow_up"})
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PLACEHOLDERS = frozenset({"-", "na", "n/a", "not available", "unknown", "none"})
_BASE_REQUIRED_FIELDS = frozenset(
    {
        "schema_version",
        "proof_id",
        "ticker",
        "field_key",
        "readiness_contract_version",
        "observed_at",
        "retrieved_at",
        "source_status",
        "rights_status",
        "payload_status",
        "reviewer_decision",
        "reviewed_at",
    }
)
_OPTIONAL_EVIDENCE_FIELDS = (
    "source_id",
    "source_ref",
    "rights_decision_ref",
    "payload_sha256",
    "reviewer_id",
)


@dataclass(frozen=True)
class ProspectiveFieldProofRecord:
    schema_version: str
    proof_id: str
    ticker: str
    field_key: str
    readiness_contract_version: str
    observed_at: str
    retrieved_at: str
    source_id: str
    source_ref: str
    source_status: str
    rights_status: str
    rights_decision_ref: str
    payload_status: str
    payload_sha256: str
    reviewer_id: str
    reviewer_decision: str
    reviewed_at: str
    supersedes_proof_id: str


@dataclass(frozen=True)
class FieldProofPreview:
    state: str
    reason: str
    technical_write_eligible: bool
    proof_identity: str
    rights_status: str
    commercial_rights_approved: bool
    required_supported_fields: tuple[str, ...]
    missing_supported_fields: tuple[str, ...]
    commercial_evidence_eligible: bool
    technical_blockers: tuple[str, ...]
    commercial_blockers: tuple[str, ...]


@dataclass(frozen=True)
class BatchFieldProofPreview:
    mode: str
    write_performed: bool
    state: str
    review_cutoff: str
    commercial_mode: bool
    ledger_digest: str
    input_digest: str
    source_rights_registry_digest: str
    preview_receipt: str
    row_count: int
    reviewable_count: int
    technical_write_eligible: bool
    commercial_evidence_eligible: bool
    technical_blockers: tuple[str, ...]
    commercial_blockers: tuple[str, ...]
    rows: tuple[FieldProofPreview, ...]


def _text(value: object) -> str:
    return str(value or "").strip()


def _normalized_ticker(value: object) -> str:
    return _text(value).upper()


def _normalized_field_key(value: object) -> str:
    return _text(value).lower()


def _is_placeholder(value: object) -> bool:
    text = _text(value)
    lowered = text.lower()
    return (
        not text
        or lowered in _PLACEHOLDERS
        or (lowered.startswith("<") and lowered.endswith(">"))
    )


def _canonical_value(record: ProspectiveFieldProofRecord, field: str) -> str:
    value = getattr(record, field)
    if field == "ticker":
        return _normalized_ticker(value)
    if field == "field_key":
        return _normalized_field_key(value)
    return _text(value)


def field_proof_identity(record: ProspectiveFieldProofRecord) -> str:
    """Return the deterministic identity for the record's reviewed semantics."""

    payload = {
        field: _canonical_value(record, field)
        for field in FIELDS
        if field not in {"proof_id", "supersedes_proof_id"}
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _read_rows(path: Path | str, *, missing_ok: bool) -> tuple[ProspectiveFieldProofRecord, ...]:
    source = Path(path)
    if not source.exists():
        if missing_ok:
            return ()
        raise ValueError(f"field proof input does not exist: {source}")
    if not source.is_file():
        raise ValueError(f"field proof path is not a regular file: {source}")
    with source.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != FIELDS:
            raise ValueError("Field proof ledger header does not match the append-only contract.")
        records = []
        for row_number, row in enumerate(reader, start=2):
            if row.get(None) is not None:
                raise ValueError(f"field proof row {row_number}: contains surplus cells")
            records.append(
                ProspectiveFieldProofRecord(
                    **{field: _text(row.get(field)) for field in FIELDS}
                )
            )
        if missing_ok and not records:
            raise ValueError("Field proof ledger must contain at least one data row.")
        return tuple(records)


def load_field_proofs(path: Path | str) -> tuple[ProspectiveFieldProofRecord, ...]:
    """Load a ledger, treating only a missing ledger as an empty state."""

    records = _read_rows(path, missing_ok=True)
    validate_field_proof_ledger(records)
    return records


def load_proposed_field_proofs(path: Path | str) -> tuple[ProspectiveFieldProofRecord, ...]:
    """Load rows proposed for review without assigning them ledger lineage."""

    records = _read_rows(path, missing_ok=False)
    for row_number, record in enumerate(records, start=2):
        try:
            _validate_record(record)
        except ValueError as exc:
            raise ValueError(f"input row {row_number}: {exc}") from exc
    return records


def _validate_record(record: ProspectiveFieldProofRecord) -> None:
    if _text(record.schema_version) != SCHEMA_VERSION:
        raise ValueError(f"schema_version must be {SCHEMA_VERSION}")
    for field in _BASE_REQUIRED_FIELDS:
        if _is_placeholder(getattr(record, field)):
            raise ValueError(f"{field} is required and cannot be a placeholder")
    for field in _OPTIONAL_EVIDENCE_FIELDS:
        value = _text(getattr(record, field))
        if value and _is_placeholder(value):
            raise ValueError(f"{field} cannot be a placeholder when provided")

    if record.source_status not in _SOURCE_STATUSES:
        raise ValueError("source_status is not an allowed value")
    if record.rights_status not in _RIGHTS_STATUSES:
        raise ValueError("rights_status is not an allowed value")
    if record.payload_status not in _PAYLOAD_STATUSES:
        raise ValueError("payload_status is not an allowed value")
    if record.reviewer_decision not in _REVIEWER_DECISIONS:
        raise ValueError("reviewer_decision is not an allowed value")
    if record.source_status == "identified":
        for field in ("source_id", "source_ref"):
            if _is_placeholder(getattr(record, field)):
                raise ValueError(
                    f"source_status=identified requires a non-placeholder {field}"
                )
    if record.payload_status == "reviewed" and _is_placeholder(record.payload_sha256):
        raise ValueError(
            "payload_status=reviewed requires a lowercase SHA-256 payload_sha256"
        )
    if _text(record.payload_sha256) and not _SHA256.fullmatch(record.payload_sha256):
        raise ValueError("payload_sha256 must be a lowercase SHA-256 digest")

    observed_at = parse_utc_timestamp(record.observed_at, label="observed_at")
    retrieved_at = parse_utc_timestamp(record.retrieved_at, label="retrieved_at")
    reviewed_at = parse_utc_timestamp(record.reviewed_at, label="reviewed_at")
    if observed_at > retrieved_at:
        raise ValueError("observed_at cannot be after retrieved_at")
    if retrieved_at > reviewed_at:
        raise ValueError("retrieved_at cannot be after reviewed_at")

    if record.reviewer_decision == "accepted":
        if record.source_status != "identified":
            raise ValueError("accepted records require source_status=identified")
        if record.payload_status != "reviewed":
            raise ValueError("accepted records require payload_status=reviewed")
        if _is_placeholder(record.source_id):
            raise ValueError("accepted records require a non-placeholder source_id")
        if _is_placeholder(record.source_ref):
            raise ValueError("accepted records require a non-placeholder source_ref")
        if not _SHA256.fullmatch(record.payload_sha256):
            raise ValueError("accepted records require a lowercase SHA-256 payload_sha256")
        if _is_placeholder(record.reviewer_id):
            raise ValueError("accepted records require a non-placeholder reviewer_id")

    if record.proof_id != field_proof_identity(record):
        raise ValueError("proof_id must equal semantic identity")


def _scope(record: ProspectiveFieldProofRecord) -> tuple[str, str, str]:
    return (
        _normalized_ticker(record.ticker),
        _normalized_field_key(record.field_key),
        _text(record.readiness_contract_version),
    )


def validate_field_proof_ledger(records: Sequence[ProspectiveFieldProofRecord]) -> None:
    """Fail closed unless every normalized scope is one append-only revision chain."""

    rows = tuple(records)
    for index, record in enumerate(rows, start=2):
        try:
            _validate_record(record)
        except ValueError as exc:
            raise ValueError(f"ledger row {index}: {exc}") from exc

    by_id: dict[str, tuple[int, ProspectiveFieldProofRecord]] = {}
    identities: dict[str, int] = {}
    for index, record in enumerate(rows):
        row_number = index + 2
        if record.proof_id in by_id:
            prior = by_id[record.proof_id][0] + 2
            raise ValueError(
                f"ledger row {row_number}: duplicate proof_id {record.proof_id} "
                f"already appears at ledger row {prior}"
            )
        identity = field_proof_identity(record)
        if identity in identities:
            prior = identities[identity] + 2
            raise ValueError(
                f"ledger row {row_number}: duplicate proof identity already appears "
                f"at ledger row {prior}"
            )
        by_id[record.proof_id] = (index, record)
        identities[identity] = index

    scopes: dict[tuple[str, str, str], list[tuple[int, ProspectiveFieldProofRecord]]] = {}
    for index, record in enumerate(rows):
        scopes.setdefault(_scope(record), []).append((index, record))

    for scope, scoped_rows in scopes.items():
        scoped_ids = {record.proof_id for _, record in scoped_rows}
        children: dict[str, list[str]] = {proof_id: [] for proof_id in scoped_ids}
        roots: list[str] = []
        for index, record in scoped_rows:
            parent_id = record.supersedes_proof_id
            if not parent_id:
                roots.append(record.proof_id)
                continue
            parent_entry = by_id.get(parent_id)
            if parent_entry is None:
                raise ValueError(f"ledger row {index + 2}: missing parent proof {parent_id}")
            _, parent = parent_entry
            if _scope(parent) != scope:
                raise ValueError(
                    f"ledger row {index + 2}: revision parent must preserve normalized scope"
                )
            children[parent_id].append(record.proof_id)

        if not roots:
            raise ValueError(
                f"ledger scope {' '.join(scope)} contains a revision cycle and has no root"
            )
        if len(roots) != 1:
            raise ValueError(f"ledger scope {' '.join(scope)} must contain exactly one root")

        for parent_id, child_ids in children.items():
            if len(child_ids) > 1:
                raise ValueError(
                    f"ledger scope {' '.join(scope)} contains a revision fork at {parent_id}; "
                    "a revision must supersede the current leaf"
                )

        visited: set[str] = set()
        current_id = roots[0]
        while current_id:
            if current_id in visited:
                raise ValueError(f"ledger scope {' '.join(scope)} contains a revision cycle")
            visited.add(current_id)
            child_ids = children[current_id]
            current_id = child_ids[0] if child_ids else ""
        if visited != scoped_ids:
            raise ValueError(
                f"ledger scope {' '.join(scope)} contains a disconnected revision cycle"
            )

        for index, record in scoped_rows:
            if not record.supersedes_proof_id:
                continue
            parent_index, parent = by_id[record.supersedes_proof_id]
            if parent_index >= index:
                raise ValueError(
                    f"ledger row {index + 2}: revision parent must appear earlier in append order"
                )
            if parse_utc_timestamp(record.reviewed_at, label="reviewed_at") <= parse_utc_timestamp(
                parent.reviewed_at, label="reviewed_at"
            ):
                raise ValueError(
                    f"ledger row {index + 2}: reviewed_at must be strictly later than parent"
                )


def _normalized_cutoff(as_of: str) -> str:
    return parse_utc_timestamp(as_of, label="field proof review cutoff").isoformat()


def _records_digest(records: Sequence[ProspectiveFieldProofRecord]) -> str:
    payload = [asdict(record) for record in records]
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _source_rights_registry_digest(
    rights_registry: Mapping[str, SourceRights],
) -> str:
    payload = [
        {"lookup_key": source_id, "rights": asdict(rights_registry[source_id])}
        for source_id in sorted(rights_registry)
    ]
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _preview_receipt(
    *,
    review_cutoff: str,
    commercial_mode: bool,
    ledger_digest: str,
    input_digest: str,
    source_rights_registry_digest: str,
) -> str:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "review_cutoff": review_cutoff,
        "commercial_mode": commercial_mode,
        "ledger_digest": ledger_digest,
        "input_digest": input_digest,
        "source_rights_registry_digest": source_rights_registry_digest,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _record_is_at_or_before_cutoff(
    record: ProspectiveFieldProofRecord, review_cutoff: str
) -> bool:
    boundary = parse_utc_timestamp(review_cutoff, label="field proof review cutoff")
    return all(
        parse_utc_timestamp(getattr(record, field), label=field) <= boundary
        for field in ("observed_at", "retrieved_at", "reviewed_at")
    )


def _commercial_preview(
    proposed: ProspectiveFieldProofRecord,
    rights_registry: Mapping[str, SourceRights],
) -> tuple[str, bool, tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    required_fields = (_normalized_field_key(proposed.field_key),)
    commercial_review = review_commercial_field_scope(
        rights_registry,
        _text(proposed.source_id),
        required_fields,
    )
    blockers: list[str] = []
    if proposed.reviewer_decision != "accepted":
        blockers.append(f"reviewer_decision:{proposed.reviewer_decision}")
    if proposed.source_status != "identified":
        blockers.append(f"source_status:{proposed.source_status}")
    if proposed.payload_status != "reviewed":
        blockers.append(f"payload_status:{proposed.payload_status}")
    if proposed.rights_status != "approved":
        blockers.append(f"record_rights_status:{proposed.rights_status}")
    if _is_placeholder(proposed.rights_decision_ref):
        blockers.append("rights_decision_ref_required")
    if not commercial_review.commercial_rights_approved:
        blockers.append(f"commercial_rights:{commercial_review.rights_status}")
    blockers.extend(
        f"registered_field_scope_missing:{field}"
        for field in commercial_review.missing_supported_fields
    )
    return (
        commercial_review.rights_status,
        commercial_review.commercial_rights_approved,
        commercial_review.required_supported_fields,
        commercial_review.missing_supported_fields,
        tuple(blockers),
    )


def preview_field_proof_batch(
    existing: Sequence[ProspectiveFieldProofRecord],
    proposed: Sequence[ProspectiveFieldProofRecord],
    *,
    as_of: str,
    commercial_mode: bool | None = None,
    rights_registry: Mapping[str, SourceRights] | None = None,
) -> BatchFieldProofPreview:
    """Preview technical recording and commercial eligibility without writing."""

    current = tuple(existing)
    validate_field_proof_ledger(current)
    review_cutoff = _normalized_cutoff(as_of)
    for row_number, record in enumerate(current, start=2):
        if not _record_is_at_or_before_cutoff(record, review_cutoff):
            raise ValueError(
                f"ledger row {row_number}: proof timestamps must be at or before review cutoff"
            )

    resolved_registry = (
        load_source_rights_registry() if rights_registry is None else rights_registry
    )
    resolved_commercial_mode = (
        commercial_mode_enabled() if commercial_mode is None else commercial_mode
    )
    proposed_rows = tuple(proposed)
    ledger_digest = _records_digest(current)
    input_digest = _records_digest(proposed_rows)
    registry_digest = _source_rights_registry_digest(resolved_registry)
    preview_receipt = _preview_receipt(
        review_cutoff=review_cutoff,
        commercial_mode=resolved_commercial_mode,
        ledger_digest=ledger_digest,
        input_digest=input_digest,
        source_rights_registry_digest=registry_digest,
    )
    virtual_ledger = list(current)
    row_previews: list[FieldProofPreview] = []
    technical_blockers: list[str] = []
    commercial_blockers: list[str] = []

    for index, record in enumerate(proposed_rows, start=1):
        row_technical_blockers: list[str] = []
        try:
            validate_field_proof_ledger((*virtual_ledger, record))
        except ValueError as exc:
            row_technical_blockers.append(str(exc))
        if not row_technical_blockers and not _record_is_at_or_before_cutoff(
            record, review_cutoff
        ):
            row_technical_blockers.append(
                "proof timestamps must be at or before review cutoff"
            )

        technical_write_eligible = not row_technical_blockers
        if technical_write_eligible:
            virtual_ledger.append(record)
            state = "reviewable_revision" if record.supersedes_proof_id else "reviewable_new"
            reason = "append-only field proof passes the technical contract"
        else:
            state = "rejected"
            reason = row_technical_blockers[0]

        (
            rights_status,
            commercial_rights_approved,
            required_supported_fields,
            missing_supported_fields,
            row_commercial_blockers,
        ) = _commercial_preview(record, resolved_registry)
        row_preview = FieldProofPreview(
            state=state,
            reason=reason,
            technical_write_eligible=technical_write_eligible,
            proof_identity=field_proof_identity(record),
            rights_status=rights_status,
            commercial_rights_approved=commercial_rights_approved,
            required_supported_fields=required_supported_fields,
            missing_supported_fields=missing_supported_fields,
            commercial_evidence_eligible=not row_commercial_blockers,
            technical_blockers=tuple(row_technical_blockers),
            commercial_blockers=row_commercial_blockers,
        )
        row_previews.append(row_preview)
        technical_blockers.extend(
            f"row_{index}:{blocker}" for blocker in row_technical_blockers
        )
        commercial_blockers.extend(
            f"row_{index}:{blocker}" for blocker in row_commercial_blockers
        )

    technical_write_eligible = bool(row_previews) and not technical_blockers
    commercial_evidence_eligible = bool(row_previews) and not commercial_blockers
    if not row_previews:
        technical_blockers.append("batch:empty_input")
        commercial_blockers.append("batch:empty_input")

    return BatchFieldProofPreview(
        mode="preview_only",
        write_performed=False,
        state=(
            "empty_batch"
            if not row_previews
            else "reviewable_batch"
            if technical_write_eligible
            else "rejected_batch"
        ),
        review_cutoff=review_cutoff,
        commercial_mode=resolved_commercial_mode,
        ledger_digest=ledger_digest,
        input_digest=input_digest,
        source_rights_registry_digest=registry_digest,
        preview_receipt=preview_receipt,
        row_count=len(row_previews),
        reviewable_count=sum(row.technical_write_eligible for row in row_previews),
        technical_write_eligible=technical_write_eligible,
        commercial_evidence_eligible=commercial_evidence_eligible,
        technical_blockers=tuple(technical_blockers),
        commercial_blockers=tuple(commercial_blockers),
        rows=tuple(row_previews),
    )


def _validate_append_preview(
    existing: Sequence[ProspectiveFieldProofRecord],
    proposed: Sequence[ProspectiveFieldProofRecord],
    *,
    review_cutoff: str,
    commercial_mode: bool,
    rights_registry: Mapping[str, SourceRights],
    expected_receipt: str,
) -> None:
    preview = preview_field_proof_batch(
        existing,
        proposed,
        as_of=review_cutoff,
        commercial_mode=commercial_mode,
        rights_registry=rights_registry,
    )
    if preview.preview_receipt != expected_receipt:
        raise ValueError(
            "preview receipt mismatch: input, cutoff, ledger, commercial mode, "
            "or source-rights registry changed"
        )
    if not preview.technical_write_eligible:
        raise ValueError(f"{preview.state}: " + "; ".join(preview.technical_blockers))
    if commercial_mode and not preview.commercial_evidence_eligible:
        raise ValueError(
            "batch_commercial_evidence_review_required: "
            + "; ".join(preview.commercial_blockers)
        )


def _encode_append_payload(
    records: Sequence[ProspectiveFieldProofRecord],
    *,
    include_header: bool,
    leading_newline: bool,
) -> bytes:
    buffer = io.StringIO(newline="")
    if leading_newline:
        buffer.write("\n")
    writer = csv.DictWriter(buffer, fieldnames=FIELDS)
    if include_header:
        writer.writeheader()
    writer.writerows(asdict(record) for record in records)
    return buffer.getvalue().encode("utf-8")


def _open_new_ledger_exclusive(destination: Path) -> BinaryIO:
    return destination.open("x+b", buffering=0)


def _remove_exclusively_created_ledger(
    destination: Path, *, created_stat: os.stat_result
) -> None:
    try:
        current_stat = os.stat(destination, follow_symlinks=False)
    except OSError:
        return
    if (current_stat.st_dev, current_stat.st_ino) != (
        created_stat.st_dev,
        created_stat.st_ino,
    ):
        return
    try:
        destination.unlink()
    except OSError:
        pass


def _write_append_payload(handle: BinaryIO, payload: bytes) -> None:
    written = handle.write(payload)
    if written != len(payload):
        raise OSError(
            f"short field proof ledger write: wrote {written} of {len(payload)} bytes"
        )


def _flush_and_fsync(handle: BinaryIO) -> None:
    handle.flush()
    os.fsync(handle.fileno())


def _append_payload_with_rollback(
    handle: BinaryIO, payload: bytes, *, original_size: int
) -> None:
    handle.seek(original_size)
    try:
        _write_append_payload(handle, payload)
        _flush_and_fsync(handle)
    except BaseException:
        handle.seek(original_size)
        handle.truncate()
        _flush_and_fsync(handle)
        raise


def _existing_ledger_needs_delimiter(handle: BinaryIO, *, original_size: int) -> bool:
    if original_size == 0:
        return False
    handle.seek(-1, os.SEEK_END)
    return handle.read(1) not in {b"\n", b"\r"}


def append_reviewed_field_proof_batch(
    path: Path | str,
    records: Sequence[ProspectiveFieldProofRecord],
    *,
    confirm_reviewed: bool,
    commercial_mode: bool | None = None,
    rights_registry: Mapping[str, SourceRights] | None = None,
    review_cutoff: str | None = None,
    preview_receipt: str | None = None,
) -> Path:
    """Revalidate an exact reviewed preview and append the whole batch once."""

    if not confirm_reviewed:
        raise ValueError("confirm_reviewed is required before append")
    if not review_cutoff:
        raise ValueError("review_cutoff is required and must match the reviewed preview")
    if not preview_receipt:
        raise ValueError("preview_receipt is required and must match the reviewed preview")

    destination = Path(path)
    proposed = tuple(records)
    resolved_registry = (
        load_source_rights_registry() if rights_registry is None else rights_registry
    )
    resolved_commercial_mode = (
        commercial_mode_enabled() if commercial_mode is None else commercial_mode
    )
    if destination.exists():
        if not destination.is_file():
            raise ValueError(f"field proof path is not a regular file: {destination}")
        with destination.open("r+b", buffering=0) as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                existing = load_field_proofs(destination)
                _validate_append_preview(
                    existing,
                    proposed,
                    review_cutoff=review_cutoff,
                    commercial_mode=resolved_commercial_mode,
                    rights_registry=resolved_registry,
                    expected_receipt=preview_receipt,
                )
                original_size = handle.seek(0, os.SEEK_END)
                payload = _encode_append_payload(
                    proposed,
                    include_header=False,
                    leading_newline=_existing_ledger_needs_delimiter(
                        handle, original_size=original_size
                    ),
                )
                _append_payload_with_rollback(
                    handle, payload, original_size=original_size
                )
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return destination

    _validate_append_preview(
        (),
        proposed,
        review_cutoff=review_cutoff,
        commercial_mode=resolved_commercial_mode,
        rights_registry=resolved_registry,
        expected_receipt=preview_receipt,
    )
    payload = _encode_append_payload(
        proposed,
        include_header=True,
        leading_newline=False,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        handle = _open_new_ledger_exclusive(destination)
    except FileExistsError as exc:
        raise ValueError(
            "preview receipt mismatch: field proof ledger was created concurrently; "
            "a new preview is required"
        ) from exc
    created_stat = os.fstat(handle.fileno())
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            _append_payload_with_rollback(handle, payload, original_size=0)
        except BaseException:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
            raise
        else:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    except BaseException:
        try:
            handle.close()
        except OSError:
            pass
        _remove_exclusively_created_ledger(destination, created_stat=created_stat)
        raise
    else:
        handle.close()
    return destination
