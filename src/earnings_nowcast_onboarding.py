from __future__ import annotations

import argparse
import csv
import json
from dataclasses import fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from src.earnings_nowcast_contract import (
    ConsensusSnapshot,
    EvidenceSignal,
    QuarterlyActual,
    validate_cutoff,
)
from src.earnings_nowcast_readiness import assess_nowcast_readiness, readiness_payload


EVIDENCE_SCHEMA_VERSION = "earnings-nowcast-evidence-v2"


SCHEMAS: dict[str, tuple[str, ...]] = {
    "quarterly_actuals.csv": (
        "schema_version",
        "ticker", "fiscal_period", "period_end_date", "reported_at", "revenue_actual",
        "eps_actual", "source", "source_ref", "retrieved_at",
        "revenue_currency", "revenue_unit_scale", "revenue_basis", "eps_currency",
        "eps_basis", "eps_share_basis", "eps_operations_basis", "split_adjustment_basis",
        "supersedes_source_ref",
    ),
    "consensus_snapshots.csv": (
        "schema_version",
        "ticker", "fiscal_period", "snapshot_at", "revenue_consensus", "eps_consensus",
        "source", "source_ref", "retrieved_at",
        "revenue_currency", "revenue_unit_scale", "revenue_basis", "eps_currency",
        "eps_basis", "eps_share_basis", "eps_operations_basis", "split_adjustment_basis",
        "expected_report_date",
    ),
    "signals.csv": (
        "schema_version",
        "signal_id", "target_ticker", "source_ticker", "fiscal_period", "as_of_timestamp",
        "signal_type", "direction", "affected_metric", "confidence_band", "evidence_source",
        "evidence_source_ref", "evidence_published_at", "evidence_excerpt_hash",
        "peer_relationship_state", "review_state",
    ),
}

IDENTITY_FIELDS: dict[str, tuple[str, ...]] = {
    "quarterly_actuals.csv": ("ticker", "fiscal_period", "source", "source_ref"),
    "consensus_snapshots.csv": ("ticker", "fiscal_period", "snapshot_at", "source", "source_ref"),
    "signals.csv": ("signal_id",),
}


def _optional_float(value: object) -> float | None:
    cleaned = str(value or "").strip()
    return float(cleaned) if cleaned else None


def write_templates(output_dir: Path) -> tuple[Path, ...]:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for filename, fields in SCHEMAS.items():
        path = root / filename
        with path.open("w", newline="", encoding="utf-8") as handle:
            csv.writer(handle).writerow(fields)
        written.append(path)
    return tuple(written)


def _read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [{str(key): str(value or "").strip() for key, value in row.items()} for row in csv.DictReader(handle)]


def _required_reference(row: Mapping[str, str], field: str) -> None:
    if not str(row.get(field, "")).strip():
        raise ValueError(f"{field} is required")


def _actual(row: Mapping[str, str]) -> QuarterlyActual:
    return QuarterlyActual(
        ticker=row.get("ticker", ""),
        fiscal_period=row.get("fiscal_period", ""),
        period_end_date=row.get("period_end_date", ""),
        reported_at=row.get("reported_at", ""),
        revenue_actual=_optional_float(row.get("revenue_actual")),
        eps_actual=_optional_float(row.get("eps_actual")),
        source=row.get("source", ""),
        source_ref=row.get("source_ref", ""),
        retrieved_at=row.get("retrieved_at", ""),
        revenue_currency=row.get("revenue_currency", ""),
        revenue_unit_scale=_optional_float(row.get("revenue_unit_scale")),
        revenue_basis=row.get("revenue_basis", ""),
        eps_currency=row.get("eps_currency", ""),
        eps_basis=row.get("eps_basis", ""),
        eps_share_basis=row.get("eps_share_basis", ""),
        eps_operations_basis=row.get("eps_operations_basis", ""),
        split_adjustment_basis=row.get("split_adjustment_basis", ""),
        supersedes_source_ref=row.get("supersedes_source_ref") or None,
    )


def _consensus(row: Mapping[str, str]) -> ConsensusSnapshot:
    _required_reference(row, "source_ref")
    return ConsensusSnapshot(
        ticker=row.get("ticker", ""),
        fiscal_period=row.get("fiscal_period", ""),
        snapshot_at=row.get("snapshot_at", ""),
        revenue_consensus=_optional_float(row.get("revenue_consensus")),
        eps_consensus=_optional_float(row.get("eps_consensus")),
        source=row.get("source", ""),
        retrieved_at=row.get("retrieved_at", ""),
        source_ref=row.get("source_ref", ""),
        revenue_currency=row.get("revenue_currency", ""),
        revenue_unit_scale=_optional_float(row.get("revenue_unit_scale")),
        revenue_basis=row.get("revenue_basis", ""),
        eps_currency=row.get("eps_currency", ""),
        eps_basis=row.get("eps_basis", ""),
        eps_share_basis=row.get("eps_share_basis", ""),
        eps_operations_basis=row.get("eps_operations_basis", ""),
        split_adjustment_basis=row.get("split_adjustment_basis", ""),
        expected_report_date=row.get("expected_report_date") or None,
    )


def _signal(row: Mapping[str, str]) -> EvidenceSignal:
    _required_reference(row, "evidence_source_ref")
    allowed = {field.name for field in fields(EvidenceSignal)}
    return EvidenceSignal(**{key: value for key, value in row.items() if key in allowed})


LOADERS: dict[str, Callable[[Mapping[str, str]], object]] = {
    "quarterly_actuals.csv": _actual,
    "consensus_snapshots.csv": _consensus,
    "signals.csv": _signal,
}


def _cutoff_timestamp(filename: str, row: Mapping[str, str]) -> tuple[str, str] | None:
    if filename == "quarterly_actuals.csv":
        return "quarterly actual", row.get("reported_at", "")
    if filename == "consensus_snapshots.csv":
        return "consensus snapshot", row.get("snapshot_at", "")
    if filename == "signals.csv":
        return "evidence signal", row.get("evidence_published_at", "")
    return None


def validate_onboarding(input_dir: Path, *, cutoff: str | None = None) -> dict[str, Any]:
    root = Path(input_dir)
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for filename in SCHEMAS:
        path = root / filename
        if filename == "signals.csv" and not path.exists():
            continue
        if filename in {"quarterly_actuals.csv", "consensus_snapshots.csv"} and not path.exists():
            rejected.append(
                {
                    "file": filename,
                    "row_number": 0,
                    "row": {},
                    "reasons": f"required input file is unavailable: {path}",
                }
            )
            continue
        header: tuple[str, ...] = ()
        if path.exists():
            with path.open(newline="", encoding="utf-8") as handle:
                header = tuple(csv.DictReader(handle).fieldnames or ())
        missing_columns = tuple(field for field in SCHEMAS[filename] if field not in header)
        rows = _read_rows(path)
        if missing_columns and not rows:
            rejected.append(
                {
                    "file": filename,
                    "row_number": 0,
                    "row": {},
                    "reasons": f"missing required columns: {', '.join(missing_columns)}",
                }
            )
            continue
        for row_number, row in enumerate(rows, start=2):
            reasons: list[str] = []
            value: object | None = None
            if missing_columns:
                reasons.append(f"missing required columns: {', '.join(missing_columns)}")
            if row.get("schema_version") != EVIDENCE_SCHEMA_VERSION:
                reasons.append(f"schema_version must be {EVIDENCE_SCHEMA_VERSION}")
            try:
                value = LOADERS[filename](row)
            except (TypeError, ValueError) as exc:
                reasons.append(str(exc))
            if cutoff:
                timestamp = _cutoff_timestamp(filename, row)
                if timestamp:
                    try:
                        validate_cutoff(timestamp[1], cutoff, label=timestamp[0])
                    except ValueError as exc:
                        reasons.append(str(exc))
            item = {"file": filename, "row_number": row_number, "row": dict(row)}
            if reasons:
                rejected.append({**item, "reasons": " | ".join(dict.fromkeys(reasons))})
            else:
                accepted.append({**item, "value": value})
    return {
        "schema_version": "earnings-nowcast-onboarding-v1",
        "mode": "validate_only",
        "valid": not rejected,
        "accepted_count": len(accepted),
        "rejected_count": len(rejected),
        "rejected_rows": rejected,
        "accepted_rows": accepted,
        "apply_performed": False,
    }


def _row_key(row: Mapping[str, str], fields: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(str(row.get(field, "")).strip() for field in fields)


def preview_onboarding(
    input_dir: Path,
    *,
    existing_dir: Path | None = None,
    cutoff: str | None = None,
) -> dict[str, Any]:
    validation = validate_onboarding(input_dir, cutoff=cutoff)
    existing_root = Path(existing_dir) if existing_dir else None
    duplicates: list[dict[str, Any]] = []
    revisions: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    new_rows: list[dict[str, Any]] = []
    accepted_files = {item["file"] for item in validation["accepted_rows"]}
    packet_blockers: list[str] = []
    if not validation["accepted_rows"]:
        packet_blockers.append("no_source_backed_rows")
    else:
        if "quarterly_actuals.csv" not in accepted_files:
            packet_blockers.append("quarterly_actuals_missing")
        if "consensus_snapshots.csv" not in accepted_files:
            packet_blockers.append("point_in_time_consensus_missing")
    for item in validation["accepted_rows"]:
        filename = item["file"]
        row = item["row"]
        existing_rows = _read_rows(existing_root / filename) if existing_root else []
        if row in existing_rows:
            duplicates.append({"file": filename, "row": row})
            continue
        if filename == "quarterly_actuals.csv":
            same_period = [
                candidate
                for candidate in existing_rows
                if candidate.get("ticker", "").strip().upper() == row.get("ticker", "").strip().upper()
                and candidate.get("fiscal_period", "").strip().upper() == row.get("fiscal_period", "").strip().upper()
            ]
            supersedes = row.get("supersedes_source_ref", "").strip()
            if supersedes and any(candidate.get("source_ref", "").strip() == supersedes for candidate in same_period):
                prior = next(candidate for candidate in same_period if candidate.get("source_ref", "").strip() == supersedes)
                revisions.append({"file": filename, "row": row, "revision_of": prior})
                continue
            metric_fields = (
                "revenue_actual", "eps_actual", "revenue_currency", "revenue_unit_scale",
                "revenue_basis", "eps_currency", "eps_basis", "eps_share_basis",
                "eps_operations_basis", "split_adjustment_basis",
            )
            conflicting = next(
                (candidate for candidate in same_period if any(candidate.get(field, "") != row.get(field, "") for field in metric_fields)),
                None,
            )
            if conflicting is not None:
                conflicts.append({"file": filename, "row": row, "conflicts_with": conflicting})
                continue
        identity_fields = IDENTITY_FIELDS[filename]
        identity = _row_key(row, identity_fields)
        prior = next((candidate for candidate in existing_rows if _row_key(candidate, identity_fields) == identity), None)
        if prior:
            revisions.append({"file": filename, "row": row, "revision_of": prior})
        else:
            new_rows.append({"file": filename, "row": row})
    return {
        **{key: value for key, value in validation.items() if key != "accepted_rows"},
        "mode": "preview_only",
        "new_count": len(new_rows),
        "revision_count": len(revisions),
        "conflict_count": len(conflicts),
        "duplicate_count": len(duplicates),
        "ready_for_packet": bool(validation["valid"] and not conflicts and not packet_blockers),
        "packet_blockers": packet_blockers,
        "new_rows": new_rows,
        "revision_rows": revisions,
        "conflict_rows": conflicts,
        "duplicate_rows": duplicates,
        "apply_performed": False,
    }


def onboarding_readiness(input_dir: Path, *, ticker: str, cutoff: str | None = None) -> dict[str, Any]:
    cutoff = cutoff or datetime.now(timezone.utc).isoformat()
    validation = validate_onboarding(input_dir, cutoff=cutoff)
    if validation["rejected_count"]:
        return {
            "ticker": str(ticker).strip().upper(),
            "state": "blocked",
            "missing_evidence": ["invalid_onboarding_rows"],
            "validation": {"valid": False, "rejected_count": validation["rejected_count"]},
        }
    actuals = [item["value"] for item in validation["accepted_rows"] if item["file"] == "quarterly_actuals.csv"]
    consensus = [item["value"] for item in validation["accepted_rows"] if item["file"] == "consensus_snapshots.csv"]
    matching = [row for row in consensus if row.ticker == str(ticker).strip().upper()]
    if not matching:
        return {
            "ticker": str(ticker).strip().upper(),
            "state": "blocked",
            "missing_evidence": ["point_in_time_consensus"],
            "validation": {"valid": validation["valid"], "rejected_count": validation["rejected_count"]},
        }
    selected = max(matching, key=lambda row: row.snapshot_at)
    result = assess_nowcast_readiness(
        ticker=ticker,
        fiscal_period=selected.fiscal_period,
        as_of_timestamp=cutoff,
        actuals=actuals,
        consensus=matching,
    )
    return {**readiness_payload(result), "validation": {"valid": validation["valid"], "rejected_count": validation["rejected_count"]}}


def prospective_collection_plan(output_dir: Path) -> dict[str, Any]:
    root = Path(output_dir)
    return {
        "schema_version": "earnings-nowcast-prospective-plan-v1",
        "state": "awaiting_point_in_time_consensus",
        "output_dir": str(root),
        "append_only": True,
        "automatic_apply": False,
        "scheduler_ready": True,
        "recommended_cadence": "weekly_and_pre_earnings",
        "template_command": f"make earnings-nowcast-templates OUTPUT_DIR={root}",
        "validation_command": f"make earnings-nowcast-validate INPUT_DIR={root} AS_OF=<forecast-cutoff>",
        "boundary": (
            "Prospective collection accumulates future point-in-time snapshots; it does not "
            "recreate historical consensus or unlock probability calibration."
        ),
    }


def _jsonable(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key != "accepted_rows"}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only Earnings Nowcast evidence onboarding.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    templates = subparsers.add_parser("templates")
    templates.add_argument("--output-dir", type=Path, required=True)
    for name in ("validate", "preview"):
        command = subparsers.add_parser(name)
        command.add_argument("--input-dir", type=Path, required=True)
        command.add_argument("--cutoff")
        if name == "preview":
            command.add_argument("--existing-dir", type=Path)
    readiness = subparsers.add_parser("readiness")
    readiness.add_argument("--input-dir", type=Path, required=True)
    readiness.add_argument("--ticker", required=True)
    readiness.add_argument("--cutoff")
    prospective = subparsers.add_parser("prospective-plan")
    prospective.add_argument("--output-dir", type=Path, required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "templates":
        print(json.dumps({"written": [str(path) for path in write_templates(args.output_dir)]}, indent=2))
        return 0
    if args.command == "prospective-plan":
        print(json.dumps(prospective_collection_plan(args.output_dir), indent=2, sort_keys=True))
        return 0
    if args.command == "validate":
        result = validate_onboarding(args.input_dir, cutoff=args.cutoff)
    elif args.command == "preview":
        result = preview_onboarding(args.input_dir, existing_dir=args.existing_dir, cutoff=args.cutoff)
    else:
        result = onboarding_readiness(args.input_dir, ticker=args.ticker, cutoff=args.cutoff)
    print(json.dumps(_jsonable(result), indent=2, sort_keys=True, default=str))
    return 0 if result.get("valid", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
