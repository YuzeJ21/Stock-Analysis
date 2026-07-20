"""Append-only prospective consensus snapshot collection contract."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

from src.commercial_source_rights import (
    SourceRights,
    commercial_mode_enabled,
    load_source_rights_registry,
    review_commercial_field_scope,
)
from src.earnings_nowcast_contract import ConsensusSnapshot, parse_utc_timestamp


SCHEMA_VERSION = "earnings-consensus-prospective-v1"
FIELDS = (
    "schema_version", "snapshot_id", "ticker", "fiscal_period", "snapshot_at", "retrieved_at",
    "source", "source_ref", "revenue_consensus", "eps_consensus", "revenue_currency",
    "revenue_unit_scale", "revenue_basis", "eps_currency", "eps_basis", "eps_share_basis",
    "eps_operations_basis", "split_adjustment_basis", "expected_report_date", "review_state",
    "supersedes_snapshot_id",
)


@dataclass(frozen=True)
class ProspectiveConsensusRecord:
    schema_version: str
    snapshot_id: str
    ticker: str
    fiscal_period: str
    snapshot_at: str
    retrieved_at: str
    source: str
    source_ref: str
    revenue_consensus: str
    eps_consensus: str
    revenue_currency: str
    revenue_unit_scale: str
    revenue_basis: str
    eps_currency: str
    eps_basis: str
    eps_share_basis: str
    eps_operations_basis: str
    split_adjustment_basis: str
    expected_report_date: str
    review_state: str
    supersedes_snapshot_id: str


@dataclass(frozen=True)
class CollectionPreview:
    state: str
    reason: str
    write_allowed: bool
    snapshot_identity: str
    rights_status: str
    commercial_rights_approved: bool
    required_supported_fields: tuple[str, ...]
    missing_supported_fields: tuple[str, ...]
    commercial_evidence_ready: bool
    commercial_write_allowed: bool
    commercial_blockers: tuple[str, ...]


@dataclass(frozen=True)
class BatchCollectionPreview:
    mode: str
    write_performed: bool
    state: str
    review_cutoff: str
    commercial_mode: bool
    ledger_digest: str
    input_digest: str
    preview_receipt: str
    row_count: int
    reviewable_count: int
    technical_write_allowed: bool
    commercial_evidence_ready: bool
    commercial_write_allowed: bool
    technical_blockers: tuple[str, ...]
    commercial_blockers: tuple[str, ...]
    rows: tuple[CollectionPreview, ...]


@dataclass(frozen=True)
class CollectionPlan:
    mode: str
    cadence: str
    as_of: str
    tickers: tuple[str, ...]
    collection_performed: bool
    next_action: str


def snapshot_identity(record: ProspectiveConsensusRecord) -> str:
    payload = {
        field: getattr(record, field)
        for field in FIELDS
        if field not in {"snapshot_id", "supersedes_snapshot_id"}
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _records_digest(records: Sequence[ProspectiveConsensusRecord]) -> str:
    payload = [asdict(record) for record in records]
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _normalized_cutoff(as_of: str) -> str:
    return parse_utc_timestamp(as_of, label="collection cutoff").isoformat()


def _preview_receipt(
    *,
    review_cutoff: str,
    commercial_mode: bool,
    ledger_digest: str,
    input_digest: str,
) -> str:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "review_cutoff": review_cutoff,
        "commercial_mode": commercial_mode,
        "ledger_digest": ledger_digest,
        "input_digest": input_digest,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _read_snapshot_rows(path: Path | str) -> tuple[ProspectiveConsensusRecord, ...]:
    source = Path(path)
    if not source.is_file():
        return ()
    with source.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != FIELDS:
            raise ValueError("Consensus snapshot ledger header does not match the append-only contract.")
        return tuple(
            ProspectiveConsensusRecord(**{field: str(row.get(field) or "").strip() for field in FIELDS})
            for row in reader
        )


def load_snapshots(path: Path | str) -> tuple[ProspectiveConsensusRecord, ...]:
    rows = _read_snapshot_rows(path)
    _validate_ledger_integrity(rows)
    return rows


def load_proposed_snapshots(path: Path | str) -> tuple[ProspectiveConsensusRecord, ...]:
    rows = _read_snapshot_rows(path)
    for row_number, row in enumerate(rows, start=2):
        try:
            _validate(row)
        except ValueError as exc:
            raise ValueError(f"input row {row_number}: {exc}") from exc
    return rows


def _validate(record: ProspectiveConsensusRecord) -> None:
    if record.schema_version != SCHEMA_VERSION:
        raise ValueError(f"schema_version must be {SCHEMA_VERSION}")
    for field in FIELDS:
        if field in {"revenue_consensus", "eps_consensus", "supersedes_snapshot_id"}:
            continue
        if not str(getattr(record, field) or "").strip():
            raise ValueError(f"{field} is required")
    parse_utc_timestamp(record.snapshot_at, label="snapshot_at")
    parse_utc_timestamp(record.retrieved_at, label="retrieved_at")
    if parse_utc_timestamp(record.snapshot_at) > parse_utc_timestamp(record.retrieved_at):
        raise ValueError("snapshot_at cannot be after retrieved_at")
    if not record.revenue_consensus and not record.eps_consensus:
        raise ValueError("at least one consensus metric is required")
    if record.review_state != "reviewed":
        raise ValueError("review_state must be reviewed")
    ConsensusSnapshot(
        ticker=record.ticker,
        fiscal_period=record.fiscal_period,
        snapshot_at=record.snapshot_at,
        revenue_consensus=float(record.revenue_consensus) if record.revenue_consensus else None,
        eps_consensus=float(record.eps_consensus) if record.eps_consensus else None,
        source=record.source,
        retrieved_at=record.retrieved_at,
        source_ref=record.source_ref,
        revenue_currency=record.revenue_currency,
        revenue_unit_scale=float(record.revenue_unit_scale),
        revenue_basis=record.revenue_basis,
        eps_currency=record.eps_currency,
        eps_basis=record.eps_basis,
        eps_share_basis=record.eps_share_basis,
        eps_operations_basis=record.eps_operations_basis,
        split_adjustment_basis=record.split_adjustment_basis,
        expected_report_date=record.expected_report_date,
    )


def _validate_ledger_integrity(rows: Sequence[ProspectiveConsensusRecord]) -> None:
    records = tuple(rows)
    for row_number, row in enumerate(records, start=2):
        try:
            _validate(row)
        except ValueError as exc:
            raise ValueError(f"ledger row {row_number}: {exc}") from exc

    by_id: dict[str, tuple[int, ProspectiveConsensusRecord]] = {}
    identities: dict[str, int] = {}
    for index, row in enumerate(records):
        if row.snapshot_id in by_id:
            prior_index = by_id[row.snapshot_id][0]
            raise ValueError(
                f"ledger row {index + 2}: duplicate snapshot_id {row.snapshot_id} "
                f"already appears at ledger row {prior_index + 2}"
            )
        identity = snapshot_identity(row)
        if identity in identities:
            raise ValueError(
                f"ledger row {index + 2}: duplicate snapshot identity already appears "
                f"at ledger row {identities[identity] + 2}"
            )
        by_id[row.snapshot_id] = (index, row)
        identities[identity] = index

    scopes: dict[tuple[str, str], list[tuple[int, ProspectiveConsensusRecord]]] = {}
    for index, row in enumerate(records):
        scope = (row.ticker.upper(), row.fiscal_period.upper())
        scopes.setdefault(scope, []).append((index, row))

    for scope, scoped_rows in scopes.items():
        scoped_ids = {row.snapshot_id for _, row in scoped_rows}
        children: dict[str, list[str]] = {snapshot_id: [] for snapshot_id in scoped_ids}
        roots: list[str] = []
        for index, row in scoped_rows:
            parent_id = row.supersedes_snapshot_id
            if not parent_id:
                roots.append(row.snapshot_id)
                continue
            parent_entry = by_id.get(parent_id)
            if parent_entry is None:
                raise ValueError(
                    f"ledger row {index + 2}: missing parent snapshot {parent_id}"
                )
            parent_index, parent = parent_entry
            if (parent.ticker.upper(), parent.fiscal_period.upper()) != scope:
                raise ValueError(
                    f"ledger row {index + 2}: revision parent must preserve ticker and fiscal period"
                )
            children[parent_id].append(row.snapshot_id)

        if not roots:
            raise ValueError(
                f"ledger scope {scope[0]} {scope[1]} contains a revision cycle and has no root"
            )
        if len(roots) != 1:
            raise ValueError(
                f"ledger scope {scope[0]} {scope[1]} must contain exactly one root"
            )
        for parent_id, child_ids in children.items():
            if len(child_ids) > 1:
                raise ValueError(
                    f"ledger scope {scope[0]} {scope[1]} contains a revision fork at {parent_id}"
                )

        visited: set[str] = set()
        current_id = roots[0]
        while current_id:
            if current_id in visited:
                raise ValueError(
                    f"ledger scope {scope[0]} {scope[1]} contains a revision cycle"
                )
            visited.add(current_id)
            current_children = children[current_id]
            current_id = current_children[0] if current_children else ""
        if visited != scoped_ids:
            raise ValueError(
                f"ledger scope {scope[0]} {scope[1]} contains a disconnected revision cycle"
            )

        for index, row in scoped_rows:
            if not row.supersedes_snapshot_id:
                continue
            parent_index, parent = by_id[row.supersedes_snapshot_id]
            if parent_index >= index:
                raise ValueError(
                    f"ledger row {index + 2}: revision parent must appear earlier in append order"
                )
            if (
                parse_utc_timestamp(row.snapshot_at) <= parse_utc_timestamp(parent.snapshot_at)
                or parse_utc_timestamp(row.retrieved_at) <= parse_utc_timestamp(parent.retrieved_at)
            ):
                raise ValueError(
                    f"ledger row {index + 2}: revision timestamps must be later than parent"
                )


def _collection_preview(
    state: str,
    reason: str,
    write_allowed: bool,
    proposed: ProspectiveConsensusRecord,
    rights_registry: Mapping[str, SourceRights],
) -> CollectionPreview:
    required_supported_fields = tuple(
        field
        for field in ("revenue_consensus", "eps_consensus")
        if str(getattr(proposed, field) or "").strip()
    )
    commercial_review = review_commercial_field_scope(
        rights_registry,
        proposed.source,
        required_supported_fields,
    )
    commercial_blockers: list[str] = []
    if not commercial_review.commercial_rights_approved:
        commercial_blockers.append(
            f"commercial_rights:{commercial_review.rights_status}"
        )
    commercial_blockers.extend(
        f"registered_consensus_scope_missing:{field}"
        for field in commercial_review.missing_supported_fields
    )
    return CollectionPreview(
        state=state,
        reason=reason,
        write_allowed=write_allowed,
        snapshot_identity=snapshot_identity(proposed),
        rights_status=commercial_review.rights_status,
        commercial_rights_approved=commercial_review.commercial_rights_approved,
        required_supported_fields=commercial_review.required_supported_fields,
        missing_supported_fields=commercial_review.missing_supported_fields,
        commercial_evidence_ready=commercial_review.commercial_evidence_ready,
        commercial_write_allowed=(
            write_allowed and commercial_review.commercial_evidence_ready
        ),
        commercial_blockers=tuple(commercial_blockers),
    )


def preview_collection(
    existing: Sequence[ProspectiveConsensusRecord],
    proposed: ProspectiveConsensusRecord,
    *,
    as_of: str,
    cooldown_hours: int = 0,
    rights_registry: Mapping[str, SourceRights] | None = None,
) -> CollectionPreview:
    rights_registry = rights_registry or load_source_rights_registry()
    try:
        _validate_ledger_integrity(existing)
    except ValueError as exc:
        return _collection_preview(
            "rejected",
            f"existing ledger invalid: {exc}",
            False,
            proposed,
            rights_registry,
        )
    try:
        _validate(proposed)
    except ValueError as exc:
        return _collection_preview("rejected", str(exc), False, proposed, rights_registry)
    boundary = parse_utc_timestamp(as_of, label="collection cutoff")
    if parse_utc_timestamp(proposed.snapshot_at) > boundary or parse_utc_timestamp(proposed.retrieved_at) > boundary:
        return _collection_preview(
            "rejected",
            "snapshot or retrieval timestamp is after the collection cutoff",
            False,
            proposed,
            rights_registry,
        )
    if any(row.snapshot_id == proposed.snapshot_id or snapshot_identity(row) == snapshot_identity(proposed) for row in existing):
        return _collection_preview(
            "duplicate", "identical immutable snapshot already exists", False, proposed, rights_registry
        )
    same_scope = [
        row for row in existing
        if row.ticker.upper() == proposed.ticker.upper() and row.fiscal_period.upper() == proposed.fiscal_period.upper()
    ]
    if same_scope and cooldown_hours:
        latest = max(parse_utc_timestamp(row.retrieved_at) for row in same_scope)
        elapsed = (parse_utc_timestamp(proposed.retrieved_at) - latest).total_seconds() / 3600
        if elapsed < cooldown_hours:
            return _collection_preview(
                "cooldown",
                f"latest snapshot is only {elapsed:.1f} hours old",
                False,
                proposed,
                rights_registry,
            )
    if proposed.supersedes_snapshot_id:
        target = next((row for row in existing if row.snapshot_id == proposed.supersedes_snapshot_id), None)
        if target is None:
            return _collection_preview(
                "rejected", "supersedes_snapshot_id does not exist", False, proposed, rights_registry
            )
        if (target.ticker.upper(), target.fiscal_period.upper()) != (proposed.ticker.upper(), proposed.fiscal_period.upper()):
            return _collection_preview(
                "rejected", "revision must preserve ticker and fiscal period", False, proposed, rights_registry
            )
        if any(
            row.supersedes_snapshot_id == target.snapshot_id for row in existing
        ):
            return _collection_preview(
                "rejected",
                "supersedes_snapshot_id must identify the current leaf snapshot",
                False,
                proposed,
                rights_registry,
            )
        if (
            parse_utc_timestamp(proposed.snapshot_at) <= parse_utc_timestamp(target.snapshot_at)
            or parse_utc_timestamp(proposed.retrieved_at) <= parse_utc_timestamp(target.retrieved_at)
        ):
            return _collection_preview(
                "rejected",
                "revision snapshot and retrieval timestamps must be later than parent",
                False,
                proposed,
                rights_registry,
            )
        return _collection_preview(
            "reviewable_revision",
            "append-only revision preserves the prior snapshot",
            True,
            proposed,
            rights_registry,
        )
    if same_scope:
        return _collection_preview(
            "rejected",
            "later same-period snapshots must identify supersedes_snapshot_id",
            False,
            proposed,
            rights_registry,
        )
    return _collection_preview(
        "reviewable_new", "new reviewed point-in-time snapshot", True, proposed, rights_registry
    )


def preview_collection_batch(
    existing: Sequence[ProspectiveConsensusRecord],
    proposed: Sequence[ProspectiveConsensusRecord],
    *,
    as_of: str,
    cooldown_hours: int = 0,
    commercial_mode: bool | None = None,
    rights_registry: Mapping[str, SourceRights] | None = None,
) -> BatchCollectionPreview:
    rights_registry = rights_registry or load_source_rights_registry()
    commercial_mode = commercial_mode if commercial_mode is not None else commercial_mode_enabled()
    _validate_ledger_integrity(existing)
    review_cutoff = _normalized_cutoff(as_of)
    proposed_rows = tuple(proposed)
    ledger_digest = _records_digest(existing)
    input_digest = _records_digest(proposed_rows)
    receipt = _preview_receipt(
        review_cutoff=review_cutoff,
        commercial_mode=commercial_mode,
        ledger_digest=ledger_digest,
        input_digest=input_digest,
    )
    if not proposed_rows:
        return BatchCollectionPreview(
            mode="preview_only",
            write_performed=False,
            state="empty_batch",
            review_cutoff=review_cutoff,
            commercial_mode=commercial_mode,
            ledger_digest=ledger_digest,
            input_digest=input_digest,
            preview_receipt=receipt,
            row_count=0,
            reviewable_count=0,
            technical_write_allowed=False,
            commercial_evidence_ready=False,
            commercial_write_allowed=False,
            technical_blockers=("batch:empty_input",),
            commercial_blockers=("batch:empty_input",),
            rows=(),
        )

    virtual_ledger = list(existing)
    row_previews: list[CollectionPreview] = []
    technical_blockers: list[str] = []
    commercial_blockers: list[str] = []
    for index, row in enumerate(proposed_rows, start=1):
        row_preview = preview_collection(
            virtual_ledger,
            row,
            as_of=review_cutoff,
            cooldown_hours=cooldown_hours,
            rights_registry=rights_registry,
        )
        row_previews.append(row_preview)
        if row_preview.write_allowed:
            virtual_ledger.append(row)
        else:
            technical_blockers.append(
                f"row_{index}:{row_preview.state}:{row_preview.reason}"
            )
        commercial_blockers.extend(
            f"row_{index}:{blocker}" for blocker in row_preview.commercial_blockers
        )

    technical_write_allowed = not technical_blockers
    commercial_evidence_ready = all(
        row_preview.commercial_evidence_ready for row_preview in row_previews
    )
    return BatchCollectionPreview(
        mode="preview_only",
        write_performed=False,
        state="reviewable_batch" if technical_write_allowed else "rejected_batch",
        review_cutoff=review_cutoff,
        commercial_mode=commercial_mode,
        ledger_digest=ledger_digest,
        input_digest=input_digest,
        preview_receipt=receipt,
        row_count=len(proposed_rows),
        reviewable_count=sum(row_preview.write_allowed for row_preview in row_previews),
        technical_write_allowed=technical_write_allowed,
        commercial_evidence_ready=commercial_evidence_ready,
        commercial_write_allowed=technical_write_allowed and commercial_evidence_ready,
        technical_blockers=tuple(technical_blockers),
        commercial_blockers=tuple(commercial_blockers),
        rows=tuple(row_previews),
    )


def append_reviewed_batch(
    path: Path | str,
    records: Sequence[ProspectiveConsensusRecord],
    *,
    confirm_reviewed: bool,
    commercial_mode: bool | None = None,
    rights_registry: Mapping[str, SourceRights] | None = None,
    review_cutoff: str | None = None,
    preview_receipt: str | None = None,
) -> Path:
    if not confirm_reviewed:
        raise ValueError("confirm_reviewed is required before append")
    if not review_cutoff:
        raise ValueError("review_cutoff is required and must match the reviewed preview")
    if not preview_receipt:
        raise ValueError("preview_receipt is required and must match the reviewed preview")
    destination = Path(path)
    existing = load_snapshots(destination)
    proposed = tuple(records)
    rights_registry = rights_registry or load_source_rights_registry()
    commercial_mode = commercial_mode if commercial_mode is not None else commercial_mode_enabled()
    preview = preview_collection_batch(
        existing,
        proposed,
        as_of=review_cutoff,
        commercial_mode=commercial_mode,
        rights_registry=rights_registry,
    )
    if preview.preview_receipt != preview_receipt:
        raise ValueError("preview receipt mismatch: input, cutoff, ledger, or commercial mode changed")
    if not preview.technical_write_allowed:
        raise ValueError(
            f"{preview.state}: " + "; ".join(preview.technical_blockers)
        )
    if commercial_mode and not preview.commercial_write_allowed:
        raise ValueError(
            "batch_commercial_evidence_review_required: "
            + "; ".join(preview.commercial_blockers)
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    exists = destination.exists() and destination.stat().st_size > 0
    with destination.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        if not exists:
            writer.writeheader()
        writer.writerows(asdict(record) for record in proposed)
    return destination


def append_reviewed_snapshot(
    path: Path | str,
    record: ProspectiveConsensusRecord,
    *,
    confirm_reviewed: bool,
    commercial_mode: bool | None = None,
    rights_registry: Mapping[str, SourceRights] | None = None,
    review_cutoff: str | None = None,
    preview_receipt: str | None = None,
) -> Path:
    return append_reviewed_batch(
        path,
        (record,),
        confirm_reviewed=confirm_reviewed,
        commercial_mode=commercial_mode,
        rights_registry=rights_registry,
        review_cutoff=review_cutoff,
        preview_receipt=preview_receipt,
    )


def collection_plan(*, tickers: Sequence[str], as_of: str, cadence: str) -> CollectionPlan:
    parse_utc_timestamp(as_of, label="plan cutoff")
    if cadence not in {"weekly", "pre_earnings"}:
        raise ValueError("cadence must be weekly or pre_earnings")
    normalized = tuple(sorted({str(ticker).strip().upper() for ticker in tickers if str(ticker).strip()}))
    return CollectionPlan(
        mode="plan_only",
        cadence=cadence,
        as_of=as_of,
        tickers=normalized,
        collection_performed=False,
        next_action="Run a provider probe or reviewed CSV preview at the planned cutoff.",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Plan or inspect append-only prospective consensus collection.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    plan = subparsers.add_parser("plan")
    plan.add_argument("--tickers", default="NVDA,AMD,AVGO,MU,QCOM")
    plan.add_argument("--as-of", default=datetime.now(timezone.utc).isoformat())
    plan.add_argument("--cadence", choices=("weekly", "pre_earnings"), default="weekly")
    status = subparsers.add_parser("status")
    status.add_argument("--ledger", default="data/imports/earnings_nowcast/prospective_consensus.csv")
    preview = subparsers.add_parser("preview")
    preview.add_argument("--input", required=True)
    preview.add_argument("--ledger", default="data/imports/earnings_nowcast/prospective_consensus.csv")
    preview.add_argument("--as-of", required=True)
    record = subparsers.add_parser("record")
    record.add_argument("--input", required=True)
    record.add_argument("--ledger", default="data/imports/earnings_nowcast/prospective_consensus.csv")
    record.add_argument("--as-of", required=True)
    record.add_argument("--preview-receipt", required=True)
    record.add_argument("--confirm-reviewed", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "plan":
        result = collection_plan(
            tickers=tuple(value for value in args.tickers.split(",") if value.strip()),
            as_of=args.as_of,
            cadence=args.cadence,
        )
        print(json.dumps(asdict(result), indent=2, sort_keys=True))
    elif args.command == "status":
        rows = load_snapshots(args.ledger)
        print(json.dumps({"mode": "read_only", "snapshot_count": len(rows), "ledger": args.ledger}, indent=2))
    elif args.command == "preview":
        existing = load_snapshots(args.ledger)
        proposed = load_proposed_snapshots(args.input)
        result = preview_collection_batch(
            existing,
            proposed,
            as_of=args.as_of,
            commercial_mode=commercial_mode_enabled(),
        )
        print(json.dumps(asdict(result), indent=2, sort_keys=True))
    else:
        if not args.confirm_reviewed:
            raise ValueError("record requires --confirm-reviewed after preview and source review")
        append_reviewed_batch(
            args.ledger,
            load_proposed_snapshots(args.input),
            confirm_reviewed=True,
            review_cutoff=args.as_of,
            preview_receipt=args.preview_receipt,
        )
        print(f"Appended reviewed prospective snapshots to {args.ledger}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
