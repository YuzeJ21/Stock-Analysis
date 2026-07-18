"""Fail-closed source activation contract for Earnings Nowcast consensus evidence."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping, Sequence

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
class SourceValidationResult:
    provider: str
    state: str
    accepted_count: int
    rejected_count: int
    historical_snapshot_count: int
    candidate_context_count: int
    rejected_rows: tuple[dict[str, object], ...]
    rights_status: str
    auto_apply: bool = False


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
    rights_status: str,
) -> SourceValidationResult:
    accepted = 0
    historical = 0
    candidate = 0
    rejected: list[dict[str, object]] = []
    for index, row in enumerate(rows, start=1):
        scope = str(row.get("history_scope") or "").strip().lower()
        required = ("ticker", "fiscal_period", "snapshot_at", "retrieved_at", "source_ref")
        if scope == "point_in_time":
            required = HISTORICAL_REQUIRED
        missing = [field for field in required if not str(row.get(field) or "").strip()]
        reasons: list[str] = []
        if missing:
            reasons.append("missing required fields: " + ", ".join(missing))
        for timestamp in ("snapshot_at", "retrieved_at"):
            if str(row.get(timestamp) or "").strip():
                try:
                    parse_utc_timestamp(row[timestamp], label=timestamp)
                except ValueError as exc:
                    reasons.append(str(exc))
        if not reasons:
            try:
                ConsensusSnapshot(
                    ticker=row.get("ticker"),
                    fiscal_period=row.get("fiscal_period"),
                    snapshot_at=row.get("snapshot_at"),
                    revenue_consensus=float(row["revenue_consensus"]) if str(row.get("revenue_consensus") or "").strip() else None,
                    eps_consensus=float(row["eps_consensus"]) if str(row.get("eps_consensus") or "").strip() else None,
                    source=provider,
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
        if rights_status not in {"research_review_only", "reviewed_local_evidence", "approved_for_project_use"}:
            reasons.append("source rights are unverified")
        if reasons:
            rejected.append({"row_number": index, "reason": " | ".join(reasons)})
            continue
        accepted += 1
        if scope == "point_in_time":
            historical += 1
        else:
            candidate += 1
    state = "historical_evidence_ready" if historical else "candidate_context_only" if candidate else "still_blocked"
    return SourceValidationResult(
        provider=str(provider).strip().lower(),
        state=state,
        accepted_count=accepted,
        rejected_count=len(rejected),
        historical_snapshot_count=historical,
        candidate_context_count=candidate,
        rejected_rows=tuple(rejected),
        rights_status=rights_status,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Report fail-closed Earnings consensus source activation state.")
    parser.add_argument("--reviewed-csv")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
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
