"""Read-only Earnings Nowcast cohort readiness summary."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping, Sequence

from src.earnings_nowcast_contract import ConsensusSnapshot, QuarterlyActual
from src.earnings_nowcast_onboarding import validate_onboarding
from src.earnings_nowcast_readiness import (
    COMPANYFACTS_SPLIT_BASIS_UNVERIFIED,
    assess_nowcast_readiness,
)


@dataclass(frozen=True)
class CohortReadinessRow:
    ticker: str
    latest_actual_period: str
    forecast_period: str
    revenue_history_count: int
    eps_history_count: int
    q4_revenue_count: int
    q4_eps_count: int
    revenue_ready: bool
    eps_ready: bool
    q4_ready: bool
    split_basis_ready: bool
    consensus_snapshot_count: int
    backtest_event_count: int
    calibration_event_count: int
    probability_state: str
    state: str
    blocker: str
    next_action: str


def _period_key(period: str) -> tuple[int, int]:
    year, quarter = period.split("-Q", 1)
    return int(year), int(quarter)


def _next_period(period: str) -> str:
    year, quarter = _period_key(period)
    return f"{year + 1}-Q1" if quarter == 4 else f"{year}-Q{quarter + 1}"


def _accepted_values(input_dir: Path, as_of: str) -> tuple[tuple[QuarterlyActual, ...], tuple[ConsensusSnapshot, ...]]:
    validation = validate_onboarding(input_dir, cutoff=as_of)
    values = tuple(item["value"] for item in validation["accepted_rows"])
    return (
        tuple(value for value in values if isinstance(value, QuarterlyActual)),
        tuple(value for value in values if isinstance(value, ConsensusSnapshot)),
    )


def build_cohort_readiness(
    input_dir: Path | str,
    *,
    tickers: Sequence[str],
    as_of: str,
    backtest_counts: Mapping[str, int] | None = None,
    calibration_counts: Mapping[str, int] | None = None,
) -> tuple[CohortReadinessRow, ...]:
    actuals, consensus = _accepted_values(Path(input_dir), as_of)
    backtests = {str(key).upper(): int(value) for key, value in (backtest_counts or {}).items()}
    calibrations = {str(key).upper(): int(value) for key, value in (calibration_counts or {}).items()}
    output: list[CohortReadinessRow] = []
    for requested in tickers:
        ticker = str(requested or "").strip().upper()
        ticker_actuals = tuple(row for row in actuals if row.ticker == ticker)
        if not ticker_actuals:
            output.append(
                CohortReadinessRow(
                    ticker=ticker,
                    latest_actual_period="",
                    forecast_period="",
                    revenue_history_count=0,
                    eps_history_count=0,
                    q4_revenue_count=0,
                    q4_eps_count=0,
                    revenue_ready=False,
                    eps_ready=False,
                    q4_ready=False,
                    split_basis_ready=False,
                    consensus_snapshot_count=0,
                    backtest_event_count=backtests.get(ticker, 0),
                    calibration_event_count=calibrations.get(ticker, 0),
                    probability_state="awaiting_calibration_evidence",
                    state="blocked",
                    blocker="quarterly_actuals_missing",
                    next_action="Add source-backed quarterly actuals through validate and preview.",
                )
            )
            continue
        periods = sorted({row.fiscal_period for row in ticker_actuals}, key=_period_key)
        latest = periods[-1]
        forecast_period = _next_period(latest)
        ticker_consensus = tuple(
            row for row in consensus if row.ticker == ticker and row.fiscal_period == forecast_period
        )
        readiness = assess_nowcast_readiness(
            ticker=ticker,
            fiscal_period=forecast_period,
            as_of_timestamp=as_of,
            actuals=ticker_actuals,
            consensus=ticker_consensus,
        )
        revenue_count = len({row.fiscal_period for row in ticker_actuals if row.revenue_actual is not None})
        eps_count = len({row.fiscal_period for row in ticker_actuals if row.eps_actual is not None})
        q4_revenue = len({row.fiscal_period for row in ticker_actuals if row.fiscal_period.endswith("Q4") and row.revenue_actual is not None})
        q4_eps = len({row.fiscal_period for row in ticker_actuals if row.fiscal_period.endswith("Q4") and row.eps_actual is not None})
        split_ready = bool(
            any(row.eps_actual is not None for row in ticker_actuals)
            and all(
                row.split_adjustment_basis != COMPANYFACTS_SPLIT_BASIS_UNVERIFIED
                for row in ticker_actuals
                if row.eps_actual is not None
            )
        )
        blockers = tuple(readiness.missing_evidence)
        output.append(
            CohortReadinessRow(
                ticker=ticker,
                latest_actual_period=latest,
                forecast_period=forecast_period,
                revenue_history_count=revenue_count,
                eps_history_count=eps_count,
                q4_revenue_count=q4_revenue,
                q4_eps_count=q4_eps,
                revenue_ready=readiness.revenue_ready,
                eps_ready=readiness.eps_ready,
                q4_ready=q4_revenue > 0 and q4_eps > 0,
                split_basis_ready=split_ready,
                consensus_snapshot_count=len(ticker_consensus),
                backtest_event_count=backtests.get(ticker, 0),
                calibration_event_count=calibrations.get(ticker, 0),
                probability_state=(
                    "calibrated" if calibrations.get(ticker, 0) >= 100 else "awaiting_calibration_evidence"
                ),
                state=readiness.state.value,
                blocker=", ".join(blockers),
                next_action=readiness.next_action,
            )
        )
    return tuple(output)


def cohort_readiness_cards(rows: Sequence[CohortReadinessRow]) -> list[dict[str, object]]:
    ready_revenue = sum(row.revenue_ready for row in rows)
    ready_eps = sum(row.eps_ready for row in rows)
    consensus = sum(row.consensus_snapshot_count > 0 for row in rows)
    return [
        {
            "kicker": "EARNINGS EVIDENCE",
            "title": f"{ready_revenue}/{len(rows)} Revenue baselines ready; {ready_eps}/{len(rows)} EPS baselines ready",
            "body": (
                f"{consensus}/{len(rows)} companies have an exact-period point-in-time consensus snapshot. "
                "Revenue and EPS gates are independent; numerical probability remains separate."
            ),
            "badges": ["read-only", "five-company cohort", "research-only"],
            "command": "",
        }
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print a read-only Earnings Nowcast cohort readiness board.")
    parser.add_argument("--input-dir", default="data/imports/earnings_nowcast")
    parser.add_argument("--tickers", default="NVDA,AMD,AVGO,MU,QCOM")
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    rows = build_cohort_readiness(
        args.input_dir,
        tickers=tuple(value.strip() for value in args.tickers.split(",") if value.strip()),
        as_of=args.as_of,
    )
    if args.json:
        print(json.dumps([asdict(row) for row in rows], indent=2, sort_keys=True))
        return 0
    print("Ticker | State | Latest actual | Forecast period | Revenue | EPS | Consensus | Probability | Next action")
    print("--- | --- | --- | --- | --- | --- | --- | --- | ---")
    for row in rows:
        print(
            f"{row.ticker} | {row.state} | {row.latest_actual_period or '-'} | {row.forecast_period or '-'} | "
            f"{'ready' if row.revenue_ready else 'withheld'} | {'ready' if row.eps_ready else 'withheld'} | "
            f"{row.consensus_snapshot_count} snapshot(s) | {row.probability_state} | {row.next_action}"
        )
    print("Boundary: this board reports evidence readiness only; it creates no forecast, probability, or recommendation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
