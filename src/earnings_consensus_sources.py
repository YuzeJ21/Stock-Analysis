"""Fail-closed source activation contract for Earnings Nowcast consensus evidence."""

from __future__ import annotations

import argparse
import csv
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping, Sequence

from src.commercial_source_rights import (
    SourceRights,
    load_source_rights_registry,
    review_commercial_field_scope,
)
from src.earnings_nowcast_contract import ConsensusSnapshot, parse_utc_timestamp


PROVIDER_ORDER = ("alpha_vantage", "fmp", "finnhub", "reviewed_csv")
KEYS = {
    "alpha_vantage": "ALPHA_VANTAGE_API_KEY",
    "fmp": "FMP_API_KEY",
    "finnhub": "FINNHUB_API_KEY",
}
HISTORICAL_REQUIRED = (
    "ticker", "fiscal_period", "snapshot_at", "retrieved_at", "source_ref",
    "revenue_currency", "revenue_unit_scale", "revenue_basis", "eps_currency",
    "eps_basis", "eps_share_basis", "eps_operations_basis", "split_adjustment_basis",
)


@dataclass(frozen=True)
class ConsensusSourceStatus:
    provider: str
    status: str
    reason: str
    source_usage: str
    auto_apply: bool = False


@dataclass(frozen=True)
class SourceCommercialReview:
    row_number: int
    required_supported_fields: tuple[str, ...]
    missing_supported_fields: tuple[str, ...]
    commercial_evidence_ready: bool
    commercial_blockers: tuple[str, ...]


@dataclass(frozen=True)
class SourceValidationResult:
    provider: str
    review_cutoff: str
    state: str
    accepted_count: int
    rejected_count: int
    historical_snapshot_count: int
    candidate_context_count: int
    rejected_rows: tuple[dict[str, object], ...]
    rights_status: str
    commercial_rights_approved: bool
    commercial_ready_count: int
    commercial_review_required_count: int
    commercial_evidence_ready: bool
    commercial_blockers: tuple[str, ...]
    commercial_review_rows: tuple[SourceCommercialReview, ...]
    auto_apply: bool = False


def load_source_review_csv(path: Path | str) -> tuple[dict[str, object], ...]:
    """Load supplied consensus source rows without normalizing or writing evidence."""

    review_path = Path(path)
    try:
        with review_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, strict=True)
            if reader.fieldnames is None:
                raise ValueError("consensus source review CSV must contain a header row")
            fieldnames = tuple(str(field or "") for field in reader.fieldnames)
            if (
                any(not field.strip() for field in fieldnames)
                or len(set(fieldnames)) != len(fieldnames)
            ):
                raise ValueError(
                    "consensus source review CSV headers must be non-blank unique column names"
                )
            rows: list[dict[str, object]] = []
            for row_number, row in enumerate(reader, start=1):
                if None in row:
                    raise ValueError(
                        f"consensus source review CSV row {row_number} has more values than the header"
                    )
                rows.append({str(key): value for key, value in row.items()})
            return tuple(rows)
    except ValueError:
        raise
    except (OSError, UnicodeError, csv.Error) as exc:
        raise ValueError(
            f"cannot read consensus source review CSV: {review_path}"
        ) from exc


def _joined(values: Sequence[object]) -> str:
    return ",".join(str(value) for value in values) if values else "none"


def render_source_validation_result(result: SourceValidationResult) -> str:
    """Render a complete source review without converting it into activation."""

    lines = [
        "Consensus Source Review",
        "Read-only: this command does not fetch, normalize, record, apply, rebuild readiness, or write artifacts.",
        f"provider: {result.provider or '-'}",
        f"review_cutoff: {result.review_cutoff}",
        f"state: {result.state}",
        f"accepted_count: {result.accepted_count}",
        f"rejected_count: {result.rejected_count}",
        f"historical_snapshot_count: {result.historical_snapshot_count}",
        f"candidate_context_count: {result.candidate_context_count}",
        f"rights_status: {result.rights_status}",
        f"commercial_rights_approved: {str(result.commercial_rights_approved).lower()}",
        f"commercial_ready_count: {result.commercial_ready_count}",
        f"commercial_review_required_count: {result.commercial_review_required_count}",
        f"commercial_evidence_ready: {str(result.commercial_evidence_ready).lower()}",
        f"commercial_blockers: {_joined(result.commercial_blockers)}",
        "rejected_rows:",
    ]
    if result.rejected_rows:
        lines.extend(
            f"- row {row['row_number']}: {row['reason']}"
            for row in result.rejected_rows
        )
    else:
        lines.append("- none")
    lines.append("commercial_review_rows:")
    if result.commercial_review_rows:
        lines.extend(
            "- row "
            f"{row.row_number}: required={_joined(row.required_supported_fields)}; "
            f"missing={_joined(row.missing_supported_fields)}; "
            f"ready={str(row.commercial_evidence_ready).lower()}; "
            f"blockers={_joined(row.commercial_blockers)}"
            for row in result.commercial_review_rows
        )
    else:
        lines.append("- none")
    lines.extend(
        [
            f"auto_apply: {str(result.auto_apply).lower()}",
            "next_gate: collection preview remains a separate reviewed gate after the payload and evidence are accepted.",
            "Boundary: reviewability is not collection, activation, readiness, backtesting, calibration, or investment advice.",
        ]
    )
    return "\n".join(lines)


def consensus_source_statuses(
    *,
    env: Mapping[str, str] | None = None,
    generic_csv: Path | str | None = None,
) -> tuple[ConsensusSourceStatus, ...]:
    values = env if env is not None else os.environ
    rows: list[ConsensusSourceStatus] = []
    for provider in PROVIDER_ORDER[:-1]:
        key = KEYS[provider]
        configured = bool(str(values.get(key, "")).strip())
        rows.append(
            ConsensusSourceStatus(
                provider,
                "configured_unverified" if configured else "external_key_required",
                "Provider key is configured; payload rights and point-in-time history still require validation."
                if configured
                else f"{key} is not configured.",
                "probe_only",
            )
        )
    path = Path(generic_csv) if generic_csv else None
    rows.append(
        ConsensusSourceStatus(
            "reviewed_csv",
            "reviewed_csv_available" if path and path.is_file() else "external_data_required",
            f"Reviewed local CSV is available at {path}." if path and path.is_file() else "No reviewed consensus CSV was supplied.",
            "reviewed_point_in_time_evidence",
        )
    )
    return tuple(rows)


def validate_source_rows(
    provider: str,
    rows: Sequence[Mapping[str, object]],
    *,
    as_of: object,
    rights_registry: Mapping[str, SourceRights] | None = None,
) -> SourceValidationResult:
    cutoff = parse_utc_timestamp(as_of, label="review cutoff")
    review_cutoff = cutoff.isoformat().replace("+00:00", "Z")
    source_id = str(provider).strip().lower()
    registry = load_source_rights_registry() if rights_registry is None else rights_registry
    source_review = review_commercial_field_scope(registry, source_id, ())
    accepted = 0
    historical = 0
    candidate = 0
    rejected: list[dict[str, object]] = []
    commercial_reviews: list[SourceCommercialReview] = []
    for index, row in enumerate(rows, start=1):
        scope = str(row.get("history_scope") or "").strip().lower()
        required = ("ticker", "fiscal_period", "snapshot_at", "retrieved_at", "source_ref")
        if scope == "point_in_time":
            required = HISTORICAL_REQUIRED
        missing = [field for field in required if not str(row.get(field) or "").strip()]
        reasons: list[str] = []
        if scope not in {"current_only", "point_in_time"}:
            reasons.append("history_scope must be current_only or point_in_time")
        if missing:
            reasons.append("missing required fields: " + ", ".join(missing))
        parsed_timestamps = {}
        for timestamp in ("snapshot_at", "retrieved_at"):
            if str(row.get(timestamp) or "").strip():
                try:
                    parsed_timestamps[timestamp] = parse_utc_timestamp(
                        row[timestamp], label=timestamp
                    )
                except ValueError as exc:
                    reasons.append(str(exc))
        snapshot_at = parsed_timestamps.get("snapshot_at")
        retrieved_at = parsed_timestamps.get("retrieved_at")
        if (
            snapshot_at is not None
            and retrieved_at is not None
            and snapshot_at > retrieved_at
        ):
            reasons.append("snapshot_at cannot be after retrieved_at")
        for field, timestamp in parsed_timestamps.items():
            if timestamp > cutoff:
                reasons.append(f"{field} is after review cutoff")
        if not reasons:
            try:
                ConsensusSnapshot(
                    ticker=row.get("ticker"),
                    fiscal_period=row.get("fiscal_period"),
                    snapshot_at=row.get("snapshot_at"),
                    revenue_consensus=float(row["revenue_consensus"]) if str(row.get("revenue_consensus") or "").strip() else None,
                    eps_consensus=float(row["eps_consensus"]) if str(row.get("eps_consensus") or "").strip() else None,
                    source=source_id,
                    retrieved_at=row.get("retrieved_at"),
                    source_ref=row.get("source_ref"),
                    revenue_currency=row.get("revenue_currency") or "USD",
                    revenue_unit_scale=float(row.get("revenue_unit_scale") or 1),
                    revenue_basis=row.get("revenue_basis") or "reported",
                    eps_currency=row.get("eps_currency") or "USD",
                    eps_basis=row.get("eps_basis") or "gaap",
                    eps_share_basis=row.get("eps_share_basis") or "diluted",
                    eps_operations_basis=row.get("eps_operations_basis") or "reported",
                    split_adjustment_basis=row.get("split_adjustment_basis") or "as_reported",
                    expected_report_date=row.get("expected_report_date") or None,
                )
            except (TypeError, ValueError) as exc:
                reasons.append(str(exc))
        if reasons:
            rejected.append({"row_number": index, "reason": " | ".join(reasons)})
            continue
        accepted += 1
        required_supported_fields = tuple(
            field
            for field in ("revenue_consensus", "eps_consensus")
            if str(row.get(field) or "").strip()
        )
        commercial_review = review_commercial_field_scope(
            registry,
            source_id,
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
        commercial_reviews.append(
            SourceCommercialReview(
                row_number=index,
                required_supported_fields=commercial_review.required_supported_fields,
                missing_supported_fields=commercial_review.missing_supported_fields,
                commercial_evidence_ready=commercial_review.commercial_evidence_ready,
                commercial_blockers=tuple(commercial_blockers),
            )
        )
        if scope == "point_in_time":
            historical += 1
        else:
            candidate += 1
    state = (
        "historical_evidence_reviewable"
        if historical
        else "candidate_context_only"
        if candidate
        else "still_blocked"
    )
    commercial_ready_count = sum(
        review.commercial_evidence_ready for review in commercial_reviews
    )
    aggregate_blockers: list[str] = []
    if not source_review.commercial_rights_approved:
        aggregate_blockers.append(
            f"commercial_rights:{source_review.rights_status}"
        )
    for review in commercial_reviews:
        for blocker in review.commercial_blockers:
            if blocker not in aggregate_blockers:
                aggregate_blockers.append(blocker)
    return SourceValidationResult(
        provider=source_id,
        review_cutoff=review_cutoff,
        state=state,
        accepted_count=accepted,
        rejected_count=len(rejected),
        historical_snapshot_count=historical,
        candidate_context_count=candidate,
        rejected_rows=tuple(rejected),
        rights_status=source_review.rights_status,
        commercial_rights_approved=source_review.commercial_rights_approved,
        commercial_ready_count=commercial_ready_count,
        commercial_review_required_count=accepted - commercial_ready_count,
        commercial_evidence_ready=bool(commercial_reviews)
        and commercial_ready_count == accepted,
        commercial_blockers=tuple(aggregate_blockers),
        commercial_review_rows=tuple(commercial_reviews),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Report fail-closed Earnings consensus source activation state.")
    parser.add_argument("--reviewed-csv")
    parser.add_argument("--review-csv", type=Path)
    parser.add_argument("--provider")
    parser.add_argument("--as-of")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.review_csv is not None:
        if args.reviewed_csv is not None:
            parser.error("--review-csv cannot be combined with --reviewed-csv")
        if not str(args.provider or "").strip():
            parser.error("--provider is required with --review-csv")
        if not str(args.as_of or "").strip():
            parser.error("--as-of is required with --review-csv")
        try:
            result = validate_source_rows(
                args.provider,
                load_source_review_csv(args.review_csv),
                as_of=args.as_of,
            )
        except ValueError as exc:
            parser.error(str(exc))
        if args.json:
            print(json.dumps(asdict(result), indent=2, sort_keys=True))
        else:
            print(render_source_validation_result(result))
        return 0
    if args.provider is not None or args.as_of is not None:
        parser.error("--provider and --as-of require --review-csv")
    statuses = consensus_source_statuses(generic_csv=args.reviewed_csv)
    if args.json:
        print(json.dumps([asdict(row) for row in statuses], indent=2, sort_keys=True))
    else:
        print("Provider | Status | Usage | Reason")
        print("--- | --- | --- | ---")
        for row in statuses:
            print(f"{row.provider} | {row.status} | {row.source_usage} | {row.reason}")
        print("Boundary: configured access is not historical evidence; every payload still requires rights, provenance, and comparability review.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
