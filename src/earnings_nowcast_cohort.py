"""Read-only Earnings Nowcast cohort readiness summary."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from dataclasses import asdict, dataclass
from numbers import Integral, Real
from pathlib import Path
from typing import Mapping, Sequence

from src.earnings_nowcast_backtest import (
    BacktestEvent,
    BacktestReport,
    CalibrationPolicy,
    CalibrationStatus,
    ProbabilityObservation,
    _backtest_report_evidence_digest,
    assess_probability_calibration,
)
from src.earnings_nowcast_contract import (
    ConsensusSnapshot,
    NowcastState,
    QuarterlyActual,
    eps_split_basis_verified,
    parse_utc_timestamp,
)
from src.earnings_nowcast_model import NowcastConfig, classify_consensus_gap
from src.earnings_nowcast_onboarding import validate_onboarding
from src.earnings_nowcast_readiness import assess_nowcast_readiness


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


def _finite_real(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, Real):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _positive_integer(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, Integral) or int(value) < 1:
        return None
    return int(value)


def _nonnegative_integer(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, Integral) or int(value) < 0:
        return None
    return int(value)


def _mean(values: Sequence[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _median(values: Sequence[float]) -> float | None:
    return float(statistics.median(values)) if values else None


def _same_optional_metric(reported: object, expected: float | None) -> bool:
    if expected is None:
        return reported is None
    value = _finite_real(reported)
    return value is not None and math.isclose(
        value,
        expected,
        rel_tol=1e-9,
        abs_tol=1e-12,
    )


def _sha256_hexdigest(value: object) -> bool:
    return bool(
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _direction(actual: float, consensus: float) -> str:
    tolerance = abs(consensus) * NowcastConfig().aligned_tolerance_pct
    if actual > consensus + tolerance:
        return "higher"
    if actual < consensus - tolerance:
        return "lower"
    return "aligned"


def _calibration_status_semantics_verified(status: object) -> bool:
    if not isinstance(status, CalibrationStatus):
        return False
    policy = CalibrationPolicy()
    if not isinstance(status.observations, tuple) or not status.observations:
        return False
    expected = assess_probability_calibration(status.observations, policy)
    return bool(
        expected.state == NowcastState.CALIBRATED
        and expected.probability_available is True
        and status.state == expected.state
        and status.probability_available is expected.probability_available
        and status.event_count == expected.event_count
        and _same_optional_metric(status.brier_score, expected.brier_score)
        and _same_optional_metric(
            status.benchmark_brier_score,
            expected.benchmark_brier_score,
        )
        and _same_optional_metric(status.calibration_error, expected.calibration_error)
        and status.calibration_bins == expected.calibration_bins
        and status.failed_gates == expected.failed_gates
        and status.failed_gate_details == expected.failed_gate_details
        and status.observations == expected.observations
        and status.outcome_definition == expected.outcome_definition
        and status.evidence_digest == expected.evidence_digest
        and (
            status.backtest_evidence_digest is None
            or _sha256_hexdigest(status.backtest_evidence_digest)
        )
    )


def _verified_calibration_status(status: object) -> bool:
    try:
        return _calibration_status_semantics_verified(status)
    except Exception:
        # Treat malformed calibration evidence as unavailable authorization.
        return False


def _calibration_backtest_semantics_verified(report: object, status: object) -> bool:
    policy = CalibrationPolicy()
    if not isinstance(report, BacktestReport) or not isinstance(status, CalibrationStatus):
        return False
    if not _calibration_status_semantics_verified(status):
        return False
    event_count = _positive_integer(report.event_count)
    valid_event_count = _positive_integer(report.valid_event_count)
    status_event_count = _positive_integer(status.event_count)
    excluded_count = _nonnegative_integer(report.excluded_count)
    if (
        report.verdict != "passed"
        or report.leakage_failures != ()
        or report.benchmark_failures != ()
        or report.failures != ()
        or event_count is None
        or valid_event_count is None
        or status_event_count is None
        or excluded_count is None
        or valid_event_count < policy.minimum_events
        or event_count != valid_event_count
        or valid_event_count != status_event_count
        or not _sha256_hexdigest(status.evidence_digest)
        or not _sha256_hexdigest(status.backtest_evidence_digest)
        or status.outcome_definition not in {
            "revenue_actual_strictly_above_consensus",
            "eps_actual_strictly_above_consensus",
        }
        or len(status.observations) != valid_event_count
        or not isinstance(report.events, tuple)
        or len(report.events) != valid_event_count
        or not all(isinstance(event, BacktestEvent) for event in report.events)
        or not isinstance(report.exclusion_reasons, Mapping)
        or not isinstance(report.excluded_events, tuple)
        or len(report.excluded_events) != excluded_count
        or any(not isinstance(detail, str) or not detail.strip() for detail in report.excluded_events)
    ):
        return False
    exclusion_reason_count = 0
    for reason, count in report.exclusion_reasons.items():
        normalized_count = _positive_integer(count)
        if not isinstance(reason, str) or not reason.strip() or normalized_count is None:
            return False
        exclusion_reason_count += normalized_count
    if exclusion_reason_count != excluded_count:
        return False

    identities: set[tuple[str, str]] = set()
    events_by_identity: dict[tuple[str, str, str], BacktestEvent] = {}
    revenue_errors: list[float] = []
    eps_errors: list[float] = []
    revenue_actual_total = 0.0
    interval_hits: list[float] = []
    revenue_interval_hits: list[float] = []
    eps_interval_hits: list[float] = []
    joint_interval_hits: list[float] = []
    directions: list[float] = []
    consensus_revenue_errors: list[float] = []
    prior_year_revenue_errors: list[float] = []
    consensus_eps_errors: list[float] = []
    prior_year_eps_errors: list[float] = []
    aligned_tolerance_pct = NowcastConfig().aligned_tolerance_pct
    metric_names = (
        "revenue_forecast",
        "revenue_low",
        "revenue_high",
        "revenue_actual",
        "eps_forecast",
        "eps_low",
        "eps_high",
        "eps_actual",
        "consensus_revenue",
        "consensus_eps",
        "prior_year_revenue",
        "prior_year_eps",
    )
    for event in report.events:
        ticker = event.ticker.strip().upper() if isinstance(event.ticker, str) else ""
        fiscal_period = (
            event.fiscal_period.strip().upper()
            if isinstance(event.fiscal_period, str)
            else ""
        )
        identity = (ticker, fiscal_period)
        if not ticker or not fiscal_period or identity in identities:
            return False
        identities.add(identity)
        latest_input = parse_utc_timestamp(event.latest_input_timestamp)
        as_of = parse_utc_timestamp(event.as_of_timestamp)
        target_reported = parse_utc_timestamp(event.target_reported_at)
        if not latest_input <= as_of < target_reported:
            return False
        events_by_identity[(ticker, fiscal_period, as_of.isoformat())] = event
        if (
            not isinstance(event.input_source_ids, tuple)
            or not event.input_source_ids
            or any(not isinstance(item, str) or not item.strip() for item in event.input_source_ids)
            or len(set(event.input_source_ids)) != len(event.input_source_ids)
        ):
            return False
        if (
            not isinstance(event.model_version, str)
            or not event.model_version.strip()
            or not _sha256_hexdigest(event.input_snapshot_hash)
        ):
            return False
        metrics: dict[str, float | None] = {}
        for name in metric_names:
            raw_value = getattr(event, name)
            value = _finite_real(raw_value)
            if raw_value is not None and value is None:
                return False
            metrics[name] = value
        revenue_forecast = metrics["revenue_forecast"]
        revenue_low = metrics["revenue_low"]
        revenue_high = metrics["revenue_high"]
        revenue_actual = metrics["revenue_actual"]
        eps_forecast = metrics["eps_forecast"]
        eps_low = metrics["eps_low"]
        eps_high = metrics["eps_high"]
        eps_actual = metrics["eps_actual"]
        consensus_revenue = metrics["consensus_revenue"]
        consensus_eps = metrics["consensus_eps"]
        prior_year_revenue = metrics["prior_year_revenue"]
        prior_year_eps = metrics["prior_year_eps"]
        if revenue_forecast is None:
            if revenue_low is not None or revenue_high is not None:
                return False
        elif (
            revenue_low is None
            or revenue_high is None
            or not revenue_low <= revenue_forecast <= revenue_high
        ):
            return False
        if eps_forecast is None:
            if eps_low is not None or eps_high is not None:
                return False
        elif eps_low is None or eps_high is None or not eps_low <= eps_forecast <= eps_high:
            return False
        revenue_modeled = revenue_forecast is not None and revenue_actual is not None
        eps_modeled = eps_forecast is not None and eps_actual is not None
        if not revenue_modeled and not eps_modeled:
            return False
        if revenue_modeled and consensus_revenue is None:
            return False
        if eps_modeled and consensus_eps is None:
            return False
        if not isinstance(event.relative_classification, str) or event.relative_classification not in {
            "higher",
            "aligned",
            "lower",
            "withheld",
        }:
            return False
        revenue_classification = (
            classify_consensus_gap(
                consensus_revenue,
                revenue_low,
                revenue_high,
                tolerance_pct=aligned_tolerance_pct,
            )
            if revenue_forecast is not None and consensus_revenue is not None
            else None
        )
        eps_classification = (
            classify_consensus_gap(
                consensus_eps,
                eps_low,
                eps_high,
                tolerance_pct=aligned_tolerance_pct,
            )
            if eps_forecast is not None and consensus_eps is not None
            else None
        )
        if event.relative_classification != (
            revenue_classification or eps_classification or "withheld"
        ):
            return False

        if revenue_modeled:
            revenue_errors.append(abs(revenue_forecast - revenue_actual))
            revenue_actual_total += abs(revenue_actual)
        if eps_modeled:
            eps_errors.append(abs(eps_forecast - eps_actual))
        revenue_hit: float | None = None
        eps_hit: float | None = None
        if revenue_actual is not None and revenue_low is not None and revenue_high is not None:
            revenue_hit = float(revenue_low <= revenue_actual <= revenue_high)
            revenue_interval_hits.append(revenue_hit)
            interval_hits.append(revenue_hit)
        if eps_actual is not None and eps_low is not None and eps_high is not None:
            eps_hit = float(eps_low <= eps_actual <= eps_high)
            eps_interval_hits.append(eps_hit)
            interval_hits.append(eps_hit)
        if revenue_hit is not None and eps_hit is not None:
            joint_interval_hits.append(float(bool(revenue_hit) and bool(eps_hit)))
        if revenue_actual is not None and consensus_revenue is not None:
            directions.append(
                float(event.relative_classification == _direction(revenue_actual, consensus_revenue))
            )
            consensus_revenue_errors.append(abs(consensus_revenue - revenue_actual))
        if prior_year_revenue is not None and revenue_actual is not None:
            prior_year_revenue_errors.append(abs(prior_year_revenue - revenue_actual))
        if consensus_eps is not None and eps_actual is not None:
            consensus_eps_errors.append(abs(consensus_eps - eps_actual))
        if prior_year_eps is not None and eps_actual is not None:
            prior_year_eps_errors.append(abs(prior_year_eps - eps_actual))

    observations_by_identity: dict[
        tuple[str, str, str], ProbabilityObservation
    ] = {}
    for observation in status.observations:
        if not isinstance(observation, ProbabilityObservation):
            return False
        identity = observation.event_identity
        if (
            identity is None
            or identity in observations_by_identity
            or observation.outcome_definition != status.outcome_definition
        ):
            return False
        observations_by_identity[identity] = observation
    if set(observations_by_identity) != set(events_by_identity):
        return False
    for identity, observation in observations_by_identity.items():
        event = events_by_identity[identity]
        if status.outcome_definition == "revenue_actual_strictly_above_consensus":
            actual = _finite_real(event.revenue_actual)
            consensus = _finite_real(event.consensus_revenue)
        else:
            actual = _finite_real(event.eps_actual)
            consensus = _finite_real(event.consensus_eps)
        if actual is None or consensus is None:
            return False
        # Beat is deliberately strict: an outcome is true only when the
        # comparable reported actual is above the same event's consensus.
        if observation.outcome is not (actual > consensus):
            return False

    revenue_mae = _mean(revenue_errors)
    eps_mae = _mean(eps_errors)
    expected_metrics = {
        "revenue_mae": revenue_mae,
        "revenue_median_absolute_error": _median(revenue_errors),
        "revenue_wape": (
            sum(revenue_errors) / revenue_actual_total
            if revenue_errors and revenue_actual_total
            else None
        ),
        "eps_mae": eps_mae,
        "eps_median_absolute_error": _median(eps_errors),
        "directional_accuracy": _mean(directions),
        "interval_coverage": _mean(interval_hits),
        "revenue_interval_coverage": _mean(revenue_interval_hits),
        "eps_interval_coverage": _mean(eps_interval_hits),
        "joint_interval_coverage": _mean(joint_interval_hits),
    }
    if not all(
        _same_optional_metric(getattr(report, name), expected)
        for name, expected in expected_metrics.items()
    ):
        return False

    expected_benchmarks = {
        name: value
        for name, values in (
            ("consensus_revenue_mae", consensus_revenue_errors),
            ("prior_year_revenue_mae", prior_year_revenue_errors),
            ("consensus_eps_mae", consensus_eps_errors),
            ("prior_year_eps_mae", prior_year_eps_errors),
        )
        if (value := _mean(values)) is not None
    }
    if not isinstance(report.benchmark_metrics, Mapping):
        return False
    if set(report.benchmark_metrics) != set(expected_benchmarks):
        return False
    for name, expected in expected_benchmarks.items():
        reported = _finite_real(report.benchmark_metrics[name])
        if reported is None or not math.isclose(
            reported,
            expected,
            rel_tol=1e-9,
            abs_tol=1e-12,
        ):
            return False
    if revenue_mae is not None:
        benchmark = expected_benchmarks.get("consensus_revenue_mae")
        if benchmark is None or revenue_mae >= benchmark:
            return False
    if eps_mae is not None:
        benchmark = expected_benchmarks.get("consensus_eps_mae")
        if benchmark is None or eps_mae >= benchmark:
            return False
    if status.outcome_definition == "revenue_actual_strictly_above_consensus":
        declared_mae = revenue_mae
        declared_benchmark = expected_benchmarks.get("consensus_revenue_mae")
    else:
        declared_mae = eps_mae
        declared_benchmark = expected_benchmarks.get("consensus_eps_mae")
    return bool(
        status.backtest_evidence_digest
        == _backtest_report_evidence_digest(report)
        and declared_mae is not None
        and declared_benchmark is not None
        and declared_mae < declared_benchmark
    )


def _verified_calibration_backtest(report: object, status: object) -> bool:
    try:
        return _calibration_backtest_semantics_verified(report, status)
    except Exception:
        # Calibration evidence is an authorization gate. Malformed evidence must
        # be withheld rather than escaping verification with an exception.
        return False


def _accepted_values(
    input_dir: Path,
    as_of: str,
) -> tuple[tuple[QuarterlyActual, ...], tuple[ConsensusSnapshot, ...], frozenset[str]]:
    validation = validate_onboarding(input_dir, cutoff=as_of)
    values = tuple(item["value"] for item in validation["accepted_rows"])
    post_cutoff_tickers = frozenset(
        str(item.get("row", {}).get("ticker") or "").strip().upper()
        for item in validation["rejected_rows"]
        if "after forecast cutoff" in str(item.get("reasons") or "")
    )
    return (
        tuple(value for value in values if isinstance(value, QuarterlyActual)),
        tuple(value for value in values if isinstance(value, ConsensusSnapshot)),
        post_cutoff_tickers,
    )


def build_cohort_readiness(
    input_dir: Path | str,
    *,
    tickers: Sequence[str],
    as_of: str,
    backtest_counts: Mapping[str, int] | None = None,
    calibration_counts: Mapping[str, int] | None = None,
    calibration_statuses: Mapping[str, CalibrationStatus] | None = None,
    calibration_backtests: Mapping[str, BacktestReport] | None = None,
) -> tuple[CohortReadinessRow, ...]:
    actuals, consensus, post_cutoff_tickers = _accepted_values(Path(input_dir), as_of)
    backtests = {str(key).upper(): int(value) for key, value in (backtest_counts or {}).items()}
    calibrations = {str(key).upper(): int(value) for key, value in (calibration_counts or {}).items()}
    calibration_evidence = {
        str(key).upper(): value for key, value in (calibration_statuses or {}).items()
    }
    calibration_backtest_evidence = {
        str(key).upper(): value for key, value in (calibration_backtests or {}).items()
    }
    output: list[CohortReadinessRow] = []
    for requested in tickers:
        ticker = str(requested or "").strip().upper()
        calibration_status = calibration_evidence.get(ticker)
        calibration_backtest = calibration_backtest_evidence.get(ticker)
        backtest_count = backtests.get(
            ticker,
            (
                calibration_backtest.valid_event_count
                if isinstance(calibration_backtest, BacktestReport)
                else 0
            ),
        )
        calibration_count = calibrations.get(
            ticker,
            calibration_status.event_count if isinstance(calibration_status, CalibrationStatus) else 0,
        )
        ticker_actuals = tuple(row for row in actuals if row.ticker == ticker)
        post_cutoff_evidence = ticker in post_cutoff_tickers
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
                    backtest_event_count=backtest_count,
                    calibration_event_count=calibration_count,
                    probability_state="awaiting_calibration_evidence",
                    state="blocked",
                    blocker=(
                        "post_cutoff_evidence, quarterly_actuals_missing"
                        if post_cutoff_evidence
                        else "quarterly_actuals_missing"
                    ),
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
                eps_split_basis_verified(row.split_adjustment_basis)
                for row in ticker_actuals
                if row.eps_actual is not None
            )
        )
        blockers = (
            ("post_cutoff_evidence", *readiness.missing_evidence)
            if post_cutoff_evidence
            else tuple(readiness.missing_evidence)
        )
        probability_calibrated = _verified_calibration_status(
            calibration_status
        ) and _verified_calibration_backtest(
            calibration_backtest,
            calibration_status,
        )
        probability_calibrated = bool(
            probability_calibrated
            and isinstance(calibration_status, CalibrationStatus)
            and isinstance(calibration_backtest, BacktestReport)
            and calibration_count == calibration_status.event_count
            and backtest_count == calibration_backtest.valid_event_count
        )
        output.append(
            CohortReadinessRow(
                ticker=ticker,
                latest_actual_period=latest,
                forecast_period=forecast_period,
                revenue_history_count=revenue_count,
                eps_history_count=eps_count,
                q4_revenue_count=q4_revenue,
                q4_eps_count=q4_eps,
                revenue_ready=readiness.revenue_ready and not post_cutoff_evidence,
                eps_ready=readiness.eps_ready and not post_cutoff_evidence,
                q4_ready=q4_revenue > 0 and q4_eps > 0,
                split_basis_ready=split_ready,
                consensus_snapshot_count=len(ticker_consensus),
                backtest_event_count=backtest_count,
                calibration_event_count=calibration_count,
                probability_state=("calibrated" if probability_calibrated else "awaiting_calibration_evidence"),
                state="blocked" if post_cutoff_evidence else readiness.state.value,
                blocker=", ".join(blockers),
                next_action=(
                    "Use only evidence published or snapshotted and retrieved at or before the cutoff."
                    if post_cutoff_evidence
                    else readiness.next_action
                ),
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
