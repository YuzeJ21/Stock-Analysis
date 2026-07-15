from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

from src.earnings_nowcast_backtest import assess_probability_calibration, walk_forward_backtest
from src.earnings_nowcast_contract import ConsensusSnapshot, EvidenceSignal, QuarterlyActual
from src.earnings_nowcast_model import NowcastConfig, build_baseline_nowcast
from src.earnings_nowcast_readiness import assess_nowcast_readiness, readiness_payload
from src.earnings_nowcast_signals import review_evidence_signals, signal_context_payload


FIXTURE_RELATIVE_PATH = Path("tests/fixtures/earnings_nowcast")


def _optional_float(value: str | None) -> float | None:
    cleaned = str(value or "").strip()
    return float(cleaned) if cleaned else None


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
        )
        for row in _read_csv(path)
    ]


def _load_signals(path: Path) -> list[EvidenceSignal]:
    return [EvidenceSignal(**row) for row in _read_csv(path)]


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


def _latest_consensus(rows: Iterable[ConsensusSnapshot], ticker: str) -> ConsensusSnapshot:
    matching = [row for row in rows if row.ticker == ticker]
    if not matching:
        raise ValueError(f"No point-in-time consensus snapshot exists for {ticker}")
    return max(matching, key=lambda row: row.snapshot_at)


def build_nowcast_packet(
    input_root: Path,
    *,
    ticker: str,
    as_of_timestamp: str,
) -> dict[str, object]:
    root = Path(input_root)
    if not root.is_dir():
        raise FileNotFoundError(f"Nowcast input directory is unavailable: {root}")
    normalized_ticker = str(ticker or "").strip().upper()
    actuals = _load_actuals(root / "quarterly_actuals.csv")
    consensus_rows = _load_consensus(root / "consensus_snapshots.csv")
    signals = _load_signals(root / "signals.csv")
    selected_consensus = _latest_consensus(
        (row for row in consensus_rows if row.ticker == normalized_ticker),
        normalized_ticker,
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

    return {
        "schema_version": "earnings-nowcast-pilot-v1",
        "evidence_scope": "synthetic_test_evidence_only",
        "ticker": normalized_ticker,
        "fiscal_period": selected_consensus.fiscal_period,
        "as_of_timestamp": readiness.as_of_timestamp,
        "readiness": readiness_payload(readiness),
        "forecast": _jsonable(forecast),
        "signals": signal_context_payload(signal_review),
        "backtest": _jsonable(backtest),
        "calibration": _jsonable(calibration),
        "boundaries": {
            "research_only": True,
            "investment_advice": "not_provided",
            "public_boundary": "Research-only synthetic test evidence; this is not investment advice.",
            "post_earnings_price_reaction": "not_predicted",
            "numeric_signal_adjustments": "not_permitted",
            "numerical_surprise_probability": "withheld_until_calibrated",
            "synthetic_notice": "Synthetic test evidence only; not real company or data-freshness proof.",
        },
    }


def render_nowcast_packet(packet: dict[str, object]) -> str:
    return json.dumps(packet, sort_keys=True, indent=2, ensure_ascii=True) + "\n"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a read-only earnings nowcast pilot packet.")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--as-of", required=True, dest="as_of_timestamp")
    parser.add_argument("--fixture", action="store_true")
    parser.add_argument("--actuals", type=Path)
    parser.add_argument("--consensus", type=Path)
    parser.add_argument("--signals", type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
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
        packet = build_nowcast_packet(input_root, ticker=args.ticker, as_of_timestamp=args.as_of_timestamp)
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
