"""Append-only prospective consensus snapshot collection contract."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

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


@dataclass(frozen=True)
class CollectionPlan:
    mode: str
    cadence: str
    as_of: str
    tickers: tuple[str, ...]
    collection_performed: bool
    next_action: str


def snapshot_identity(record: ProspectiveConsensusRecord) -> str:
    parts = (
        record.ticker.upper(), record.fiscal_period.upper(), record.snapshot_at,
        record.source, record.source_ref, record.revenue_consensus, record.eps_consensus,
    )
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


def load_snapshots(path: Path | str) -> tuple[ProspectiveConsensusRecord, ...]:
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


def preview_collection(
    existing: Sequence[ProspectiveConsensusRecord],
    proposed: ProspectiveConsensusRecord,
    *,
    as_of: str,
    cooldown_hours: int = 0,
) -> CollectionPreview:
    try:
        _validate(proposed)
    except ValueError as exc:
        return CollectionPreview("rejected", str(exc), False, snapshot_identity(proposed))
    boundary = parse_utc_timestamp(as_of, label="collection cutoff")
    if parse_utc_timestamp(proposed.snapshot_at) > boundary or parse_utc_timestamp(proposed.retrieved_at) > boundary:
        return CollectionPreview("rejected", "snapshot or retrieval timestamp is after the collection cutoff", False, snapshot_identity(proposed))
    if any(row.snapshot_id == proposed.snapshot_id or snapshot_identity(row) == snapshot_identity(proposed) for row in existing):
        return CollectionPreview("duplicate", "identical immutable snapshot already exists", False, snapshot_identity(proposed))
    same_scope = [
        row for row in existing
        if row.ticker.upper() == proposed.ticker.upper() and row.fiscal_period.upper() == proposed.fiscal_period.upper()
    ]
    if same_scope and cooldown_hours:
        latest = max(parse_utc_timestamp(row.retrieved_at) for row in same_scope)
        elapsed = (parse_utc_timestamp(proposed.retrieved_at) - latest).total_seconds() / 3600
        if elapsed < cooldown_hours:
            return CollectionPreview("cooldown", f"latest snapshot is only {elapsed:.1f} hours old", False, snapshot_identity(proposed))
    if proposed.supersedes_snapshot_id:
        target = next((row for row in existing if row.snapshot_id == proposed.supersedes_snapshot_id), None)
        if target is None:
            return CollectionPreview("rejected", "supersedes_snapshot_id does not exist", False, snapshot_identity(proposed))
        if (target.ticker.upper(), target.fiscal_period.upper()) != (proposed.ticker.upper(), proposed.fiscal_period.upper()):
            return CollectionPreview("rejected", "revision must preserve ticker and fiscal period", False, snapshot_identity(proposed))
        return CollectionPreview("reviewable_revision", "append-only revision preserves the prior snapshot", True, snapshot_identity(proposed))
    if same_scope:
        return CollectionPreview("rejected", "later same-period snapshots must identify supersedes_snapshot_id", False, snapshot_identity(proposed))
    return CollectionPreview("reviewable_new", "new reviewed point-in-time snapshot", True, snapshot_identity(proposed))


def append_reviewed_snapshot(
    path: Path | str,
    record: ProspectiveConsensusRecord,
    *,
    confirm_reviewed: bool,
) -> Path:
    if not confirm_reviewed:
        raise ValueError("confirm_reviewed is required before append")
    destination = Path(path)
    existing = load_snapshots(destination)
    preview = preview_collection(existing, record, as_of=record.retrieved_at)
    if not preview.write_allowed:
        raise ValueError(preview.state + ": " + preview.reason)
    destination.parent.mkdir(parents=True, exist_ok=True)
    exists = destination.exists() and destination.stat().st_size > 0
    with destination.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        if not exists:
            writer.writeheader()
        writer.writerow(asdict(record))
    return destination


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
        proposed = load_snapshots(args.input)
        results = [asdict(preview_collection(existing, row, as_of=args.as_of)) for row in proposed]
        print(json.dumps({"mode": "preview_only", "write_performed": False, "rows": results}, indent=2, sort_keys=True))
    else:
        if not args.confirm_reviewed:
            raise ValueError("record requires --confirm-reviewed after preview and source review")
        for row in load_snapshots(args.input):
            append_reviewed_snapshot(args.ledger, row, confirm_reviewed=True)
        print(f"Appended reviewed prospective snapshots to {args.ledger}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
