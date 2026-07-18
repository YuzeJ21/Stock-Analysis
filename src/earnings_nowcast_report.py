from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import asdict, fields, is_dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

from src.earnings_nowcast_backtest import assess_probability_calibration, walk_forward_backtest
from src.earnings_nowcast_contract import ConsensusSnapshot, EvidenceSignal, QuarterlyActual, parse_utc_timestamp
from src.earnings_nowcast_model import NowcastConfig, build_baseline_nowcast
from src.earnings_nowcast_readiness import assess_nowcast_readiness, readiness_payload
from src.earnings_nowcast_signals import review_evidence_signals, signal_context_payload


FIXTURE_RELATIVE_PATH = Path("tests/fixtures/earnings_nowcast")


def _optional_float(value: str | None) -> float | None:
    cleaned = str(value or "").strip()
    return float(cleaned) if cleaned else None


def _synthetic_default(row: dict[str, str], field: str, default: str) -> str:
    value = str(row.get(field, "")).strip()
    if value:
        return value
    if row.get("source", "").strip() == "synthetic_test_fixture":
        return default
    return value


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Nowcast input file is unavailable: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _load_actuals(path: Path) -> list[QuarterlyActual]:
    return [
        QuarterlyActual(
            ticker=row["ticker"],
            fiscal_period=row["fiscal_period"],
            period_end_date=row["period_end_date"],
            reported_at=row["reported_at"],
            revenue_actual=_optional_float(row.get("revenue_actual")),
            eps_actual=_optional_float(row.get("eps_actual")),
            source=row["source"],
            source_ref=row["source_ref"],
            retrieved_at=row["retrieved_at"],
            revenue_currency=_synthetic_default(row, "revenue_currency", "USD"),
            revenue_unit_scale=_optional_float(_synthetic_default(row, "revenue_unit_scale", "1")),
            revenue_basis=_synthetic_default(row, "revenue_basis", "reported"),
            eps_currency=_synthetic_default(row, "eps_currency", "USD"),
            eps_basis=_synthetic_default(row, "eps_basis", "gaap"),
            eps_share_basis=_synthetic_default(row, "eps_share_basis", "diluted"),
            eps_operations_basis=_synthetic_default(row, "eps_operations_basis", "reported"),
            split_adjustment_basis=_synthetic_default(row, "split_adjustment_basis", "as_reported"),
            supersedes_source_ref=row.get("supersedes_source_ref") or None,
        )
        for row in _read_csv(path)
    ]


def _load_consensus(path: Path) -> list[ConsensusSnapshot]:
    return [
        ConsensusSnapshot(
            ticker=row["ticker"],
            fiscal_period=row["fiscal_period"],
            snapshot_at=row["snapshot_at"],
            revenue_consensus=_optional_float(row.get("revenue_consensus")),
            eps_consensus=_optional_float(row.get("eps_consensus")),
            source=row["source"],
            retrieved_at=row["retrieved_at"],
            source_ref=row.get("source_ref") or None,
            revenue_currency=_synthetic_default(row, "revenue_currency", "USD"),
            revenue_unit_scale=_optional_float(_synthetic_default(row, "revenue_unit_scale", "1")),
            revenue_basis=_synthetic_default(row, "revenue_basis", "reported"),
            eps_currency=_synthetic_default(row, "eps_currency", "USD"),
            eps_basis=_synthetic_default(row, "eps_basis", "gaap"),
            eps_share_basis=_synthetic_default(row, "eps_share_basis", "diluted"),
            eps_operations_basis=_synthetic_default(row, "eps_operations_basis", "reported"),
            split_adjustment_basis=_synthetic_default(row, "split_adjustment_basis", "as_reported"),
            expected_report_date=row.get("expected_report_date") or None,
        )
        for row in _read_csv(path)
    ]


def _load_signals(path: Path) -> list[EvidenceSignal]:
    allowed = {field.name for field in fields(EvidenceSignal)}
    return [EvidenceSignal(**{key: value for key, value in row.items() if key in allowed}) for row in _read_csv(path)]


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value


def _latest_consensus(
    rows: Iterable[ConsensusSnapshot],
    ticker: str,
    cutoff: str,
    *,
    fiscal_period: str | None = None,
) -> ConsensusSnapshot:
    matching = [
        row
        for row in rows
        if row.ticker == ticker
        and (fiscal_period is None or row.fiscal_period == fiscal_period)
        and parse_utc_timestamp(row.snapshot_at) <= parse_utc_timestamp(cutoff)
    ]
    if not matching:
        period_note = f" for {fiscal_period}" if fiscal_period else ""
        raise ValueError(f"No point-in-time consensus snapshot exists for {ticker}{period_note} at or before {cutoff}")
    return max(matching, key=lambda row: parse_utc_timestamp(row.snapshot_at))


def build_nowcast_packet(
    input_root: Path,
    *,
    ticker: str,
    as_of_timestamp: str,
    fiscal_period: str | None = None,
) -> dict[str, object]:
    root = Path(input_root)
    if not root.is_dir():
        raise FileNotFoundError(f"Nowcast input directory is unavailable: {root}")
    normalized_ticker = str(ticker or "").strip().upper()
    normalized_period = str(fiscal_period or "").strip().upper() or None
    raw_consensus = [
        row
        for row in _read_csv(root / "consensus_snapshots.csv")
        if str(row.get("ticker") or "").strip().upper() == normalized_ticker
    ]
    synthetic_only = bool(raw_consensus) and all(
        str(row.get("source") or "").strip() == "synthetic_test_fixture"
        for row in raw_consensus
    )
    if normalized_period is None and not synthetic_only:
        raise ValueError("fiscal_period is required for real-company nowcast evidence")
    actuals = _load_actuals(root / "quarterly_actuals.csv")
    consensus_rows = _load_consensus(root / "consensus_snapshots.csv")
    signals = _load_signals(root / "signals.csv")
    selected_consensus = _latest_consensus(
        (row for row in consensus_rows if row.ticker == normalized_ticker),
        normalized_ticker,
        as_of_timestamp,
        fiscal_period=normalized_period,
    )
    selected_actuals = [row for row in actuals if row.ticker == normalized_ticker]
    selected_signals = [row for row in signals if row.target_ticker == normalized_ticker]
    readiness = assess_nowcast_readiness(
        ticker=normalized_ticker,
        fiscal_period=selected_consensus.fiscal_period,
        as_of_timestamp=as_of_timestamp,
        actuals=selected_actuals,
        consensus=[selected_consensus],
    )
    forecast = build_baseline_nowcast(selected_actuals, selected_consensus, as_of_timestamp, NowcastConfig())
    trusted_peer_ids = {
        signal.signal_id
        for signal in selected_signals
        if signal.peer_relationship_state == "trusted" and signal.review_state.value == "supported"
    }
    signal_review = review_evidence_signals(selected_signals, as_of_timestamp, trusted_peer_ids=trusted_peer_ids)
    backtest = walk_forward_backtest(selected_actuals, [selected_consensus], NowcastConfig())
    calibration = assess_probability_calibration([])
    synthetic = all(row.source == "synthetic_test_fixture" for row in [*selected_actuals, selected_consensus])
    evidence_scope = "synthetic_test_evidence_only" if synthetic else "source_backed_preview_only"

    return {
        "schema_version": "earnings-nowcast-pilot-v1",
        "evidence_scope": evidence_scope,
        "ticker": normalized_ticker,
        "fiscal_period": selected_consensus.fiscal_period,
        "as_of_timestamp": readiness.as_of_timestamp,
        "readiness": readiness_payload(readiness),
        "forecast": _jsonable(forecast),
        "signals": signal_context_payload(signal_review),
        "backtest": _jsonable(backtest),
        "calibration": _jsonable(calibration),
        "metric_definitions": {
            "revenue": {
                "currency": selected_consensus.revenue_currency,
                "unit_scale": selected_consensus.revenue_unit_scale,
                "basis": selected_consensus.revenue_basis,
            },
            "eps": {
                "currency": selected_consensus.eps_currency,
                "basis": selected_consensus.eps_basis,
                "share_basis": selected_consensus.eps_share_basis,
                "operations_basis": selected_consensus.eps_operations_basis,
                "split_adjustment_basis": selected_consensus.split_adjustment_basis,
            },
        },
        "boundaries": {
            "research_only": True,
            "investment_advice": "not_provided",
            "public_boundary": (
                "Research-only synthetic test evidence; this is not investment advice."
                if synthetic
                else "Research-only source-backed preview; validation does not apply or publish data."
            ),
            "post_earnings_price_reaction": "not_predicted",
            "numeric_signal_adjustments": "not_permitted",
            "numerical_surprise_probability": "withheld_until_calibrated",
            "synthetic_notice": (
                "Synthetic test evidence only; not real company or data-freshness proof."
                if synthetic
                else "not_applicable"
            ),
        },
    }


def build_fixture_walkthrough(input_root: Path, *, as_of_timestamp: str) -> dict[str, object]:
    """Build synthetic reviewer scenarios without representing them as company evidence."""
    root = Path(input_root)
    actuals = _load_actuals(root / "quarterly_actuals.csv")
    consensus_rows = _load_consensus(root / "consensus_snapshots.csv")
    signals = _load_signals(root / "signals.csv")

    baseline = build_nowcast_packet(root, ticker="SYN1", as_of_timestamp=as_of_timestamp)

    syn2_actuals = [row for row in actuals if row.ticker == "SYN2"]
    unstable_syn2 = [
        replace(row, eps_actual=(abs(float(row.eps_actual or 1.0)) * (-1 if index % 2 else 1)))
        for index, row in enumerate(syn2_actuals)
    ]
    syn2_consensus = [row for row in consensus_rows if row.ticker == "SYN2"]
    syn2_readiness = assess_nowcast_readiness(
        ticker="SYN2",
        fiscal_period=syn2_consensus[0].fiscal_period,
        as_of_timestamp=as_of_timestamp,
        actuals=unstable_syn2,
        consensus=syn2_consensus,
    )

    candidate_signals = [row for row in signals if row.review_state.value == "candidate_context_only"]
    candidate_review = review_evidence_signals(candidate_signals, as_of_timestamp, trusted_peer_ids=set())

    syn4_consensus = next(row for row in consensus_rows if row.ticker == "SYN4")
    post_cutoff_consensus = replace(
        syn4_consensus,
        snapshot_at="2026-02-01T12:00:00+00:00",
        retrieved_at="2026-02-01T12:01:00+00:00",
    )
    post_cutoff = assess_nowcast_readiness(
        ticker="SYN4",
        fiscal_period=post_cutoff_consensus.fiscal_period,
        as_of_timestamp=as_of_timestamp,
        actuals=[row for row in actuals if row.ticker == "SYN4"],
        consensus=[post_cutoff_consensus],
    )
    excluded = assess_nowcast_readiness(
        ticker="SYN5",
        fiscal_period="2026-Q1",
        as_of_timestamp=as_of_timestamp,
        actuals=[],
        consensus=[],
        asset_type="etf",
    )

    syn5_actuals = [row for row in actuals if row.ticker == "SYN5"]
    syn5_target = QuarterlyActual(
        ticker="SYN5",
        fiscal_period="2026-Q1",
        period_end_date="2026-03-31",
        reported_at="2026-04-20T21:00:00Z",
        revenue_actual=560.0,
        eps_actual=5.0,
        source="synthetic_test_fixture",
        source_ref="fixture://actual/SYN5/2026-Q1",
        retrieved_at="2026-04-20T21:00:00Z",
    )
    backtest = walk_forward_backtest(
        [*syn5_actuals, syn5_target],
        [row for row in consensus_rows if row.ticker == "SYN5"],
        NowcastConfig(),
    )
    calibration = assess_probability_calibration([])

    scenarios = [
        {
            "scenario": "baseline_ready",
            "ticker": "SYN1",
            "state": baseline["readiness"]["state"],
            "test_only": True,
        },
        {
            "scenario": "revenue_ready_eps_withheld",
            "ticker": "SYN2",
            "state": syn2_readiness.state.value,
            "revenue_ready": syn2_readiness.revenue_ready,
            "eps_ready": syn2_readiness.eps_ready,
            "test_only": True,
        },
        {
            "scenario": "candidate_peer_only",
            "ticker": "SYN3",
            "state": candidate_review.state.value,
            "candidate_context_only": len(candidate_review.candidate_context_only),
            "test_only": True,
        },
        {
            "scenario": "post_cutoff_blocked",
            "ticker": "SYN4",
            "state": post_cutoff.state.value,
            "missing_evidence": list(post_cutoff.missing_evidence),
            "test_only": True,
        },
        {
            "scenario": "excluded_non_company",
            "ticker": "SYN5",
            "state": excluded.state.value,
            "test_only": True,
        },
        {
            "scenario": "backtest_insufficient_uncalibrated",
            "ticker": "SYN5-BACKTEST",
            "state": calibration.state.value,
            "valid_event_count": backtest.valid_event_count,
            "probability_available": calibration.probability_available,
            "test_only": True,
        },
    ]
    return {
        "schema_version": "earnings-nowcast-fixture-walkthrough-v1",
        "evidence_scope": "synthetic_test_evidence_only",
        "scenarios": scenarios,
        "boundary": "Workflow test evidence only; not real-company coverage, freshness, or predictive validation.",
    }


def render_nowcast_packet(packet: dict[str, object]) -> str:
    return json.dumps(packet, sort_keys=True, indent=2, ensure_ascii=True) + "\n"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a read-only earnings nowcast pilot packet.")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--ticker")
    parser.add_argument("--fiscal-period")
    parser.add_argument("--as-of", required=True, dest="as_of_timestamp")
    parser.add_argument("--fixture", action="store_true")
    parser.add_argument("--walkthrough", action="store_true")
    parser.add_argument("--actuals", type=Path)
    parser.add_argument("--consensus", type=Path)
    parser.add_argument("--signals", type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.walkthrough and not args.fixture:
        print("The reviewer walkthrough is available only with --fixture.", file=sys.stderr)
        return 2
    if not args.walkthrough and not args.ticker:
        print("--ticker is required unless --walkthrough is selected.", file=sys.stderr)
        return 2
    if any((args.actuals, args.consensus, args.signals)):
        if not all((args.actuals, args.consensus, args.signals)):
            print("Explicit inputs require --actuals, --consensus, and --signals together.", file=sys.stderr)
            return 2
        input_root = args.root / ".nowcast-explicit-inputs"
        paths = (args.actuals, args.consensus, args.signals)
        if len({path.parent.resolve() for path in paths}) != 1:
            print("Explicit nowcast inputs must share one directory.", file=sys.stderr)
            return 2
        input_root = args.actuals.parent
    else:
        input_root = args.root / (FIXTURE_RELATIVE_PATH if args.fixture else Path("data/earnings_nowcast"))
    try:
        packet = (
            build_fixture_walkthrough(input_root, as_of_timestamp=args.as_of_timestamp)
            if args.walkthrough
            else build_nowcast_packet(
                input_root,
                ticker=args.ticker,
                fiscal_period=args.fiscal_period,
                as_of_timestamp=args.as_of_timestamp,
            )
        )
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"Invalid nowcast evidence: {exc}", file=sys.stderr)
        return 1
    print(render_nowcast_packet(packet), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
