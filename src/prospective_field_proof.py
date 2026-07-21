"""Strict, append-only records for prospective per-field review proof."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

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
    for field in FIELDS:
        if field == "supersedes_proof_id":
            continue
        if _is_placeholder(getattr(record, field)):
            raise ValueError(f"{field} is required and cannot be a placeholder")

    if record.source_status not in _SOURCE_STATUSES:
        raise ValueError("source_status is not an allowed value")
    if record.rights_status not in _RIGHTS_STATUSES:
        raise ValueError("rights_status is not an allowed value")
    if record.payload_status not in _PAYLOAD_STATUSES:
        raise ValueError("payload_status is not an allowed value")
    if record.reviewer_decision not in _REVIEWER_DECISIONS:
        raise ValueError("reviewer_decision is not an allowed value")
    if not _SHA256.fullmatch(record.payload_sha256):
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
        if _is_placeholder(record.source_ref):
            raise ValueError("accepted records require a non-placeholder source_ref")
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
