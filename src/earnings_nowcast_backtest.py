from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import Mapping, Sequence

from src.earnings_nowcast_contract import (
    ConsensusSnapshot,
    NowcastState,
    QuarterlyActual,
    eps_split_basis_verified,
    parse_utc_timestamp,
)
from src.earnings_nowcast_model import NowcastConfig, build_baseline_nowcast


@dataclass(frozen=True)
class BacktestEvent:
    ticker: str
    fiscal_period: str
    as_of_timestamp: str
    latest_input_timestamp: str
    target_reported_at: str
    input_source_ids: tuple[str, ...]
    revenue_forecast: float | None
    revenue_low: float | None
    revenue_high: float | None
    revenue_actual: float | None
    eps_forecast: float | None
    eps_low: float | None
    eps_high: float | None
    eps_actual: float | None
    consensus_revenue: float | None
    consensus_eps: float | None
    prior_year_revenue: float | None
    prior_year_eps: float | None
    relative_classification: str


@dataclass(frozen=True)
class BacktestReport:
    verdict: str
    event_count: int
    valid_event_count: int
    excluded_count: int
    exclusion_reasons: Mapping[str, int]
    excluded_events: tuple[str, ...]
    revenue_mae: float | None
    revenue_median_absolute_error: float | None
    revenue_wape: float | None
    eps_mae: float | None
    eps_median_absolute_error: float | None
    directional_accuracy: float | None
    interval_coverage: float | None
    revenue_interval_coverage: float | None
    eps_interval_coverage: float | None
    joint_interval_coverage: float | None
    benchmark_metrics: Mapping[str, float]
    benchmark_failures: tuple[str, ...]
    leakage_failures: tuple[str, ...]
    failures: tuple[str, ...]
    events: tuple[BacktestEvent, ...]


@dataclass(frozen=True)
class ProbabilityObservation:
    probability: float
    outcome: bool

    def __post_init__(self) -> None:
        if isinstance(self.probability, bool) or not math.isfinite(float(self.probability)):
            raise ValueError("probability must be finite and between 0 and 1")
        if not 0 <= float(self.probability) <= 1:
            raise ValueError("probability must be between 0 and 1")
        object.__setattr__(self, "probability", float(self.probability))
        object.__setattr__(self, "outcome", bool(self.outcome))


@dataclass(frozen=True)
class CalibrationPolicy:
    minimum_events: int = 100
    maximum_brier_score: float = 0.25
    minimum_bin_size: int = 10

    def __post_init__(self) -> None:
        if self.minimum_events < 1 or self.minimum_bin_size < 1:
            raise ValueError("calibration event and bin minimums must be positive")
        if not 0 < self.maximum_brier_score <= 1:
            raise ValueError("maximum_brier_score must be in (0, 1]")


@dataclass(frozen=True)
class CalibrationStatus:
    state: NowcastState
    probability_available: bool
    event_count: int
    brier_score: float | None
    benchmark_brier_score: float | None
    calibration_error: float | None
    calibration_bins: tuple["CalibrationBin", ...]
    failed_gates: tuple[str, ...]
    failed_gate_details: Mapping[str, str]


@dataclass(frozen=True)
class CalibrationBin:
    lower_bound: float
    upper_bound: float
    event_count: int
    mean_probability: float
    outcome_rate: float
    meets_minimum_size: bool


def _mean(values: Sequence[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _median(values: Sequence[float]) -> float | None:
    return float(statistics.median(values)) if values else None


def _prior_year(period: str) -> str:
    year, quarter = period.split("-Q", 1)
    return f"{int(year) - 1}-Q{quarter}"


def _direction(actual: float, consensus: float, tolerance_pct: float) -> str:
    tolerance = abs(consensus) * tolerance_pct
    if actual > consensus + tolerance:
        return "higher"
    if actual < consensus - tolerance:
        return "lower"
    return "aligned"


def walk_forward_backtest(
    actuals: Sequence[QuarterlyActual],
    consensus_snapshots: Sequence[ConsensusSnapshot],
    config: NowcastConfig | None = None,
    *,
    minimum_backtest_events: int = 20,
    maximum_snapshot_age_days: int = 90,
) -> BacktestReport:
    config = config or NowcastConfig()
    if maximum_snapshot_age_days < 1:
        raise ValueError("maximum_snapshot_age_days must be positive")
    actual_lookup = {(row.ticker, row.fiscal_period): row for row in actuals}
    events: list[BacktestEvent] = []
    failures: list[str] = []
    leakage_failures: list[str] = []
    excluded_count = 0
    exclusion_reasons: dict[str, int] = {}
    excluded_events: list[str] = []

    def exclude(reason: str, detail: str) -> None:
        nonlocal excluded_count
        excluded_count += 1
        exclusion_reasons[reason] = exclusion_reasons.get(reason, 0) + 1
        excluded_events.append(detail)

    targets = sorted(actuals, key=lambda row: (row.reported_at, row.ticker, row.fiscal_period))
    for target in targets:
        target_eps_actual = (
            target.eps_actual
            if eps_split_basis_verified(target.split_adjustment_basis)
            else None
        )
        if target.revenue_actual is None and target_eps_actual is None:
            exclude(
                "no_comparable_target_actual",
                f"{target.ticker} {target.fiscal_period}: no target metric has verified comparable evidence",
            )
            continue
        matching_snapshots = [
            row
            for row in consensus_snapshots
            if row.ticker == target.ticker
            and row.fiscal_period == target.fiscal_period
            and parse_utc_timestamp(row.snapshot_at) < parse_utc_timestamp(target.reported_at)
        ]
        eligible_snapshots: list[ConsensusSnapshot] = []
        for row in matching_snapshots:
            if parse_utc_timestamp(row.retrieved_at) >= parse_utc_timestamp(target.reported_at):
                leakage_failures.append(
                    f"{target.ticker} {target.fiscal_period}: consensus retrieved after target report"
                )
                continue
            eligible_snapshots.append(row)
        if not eligible_snapshots:
            exclude(
                "no_pre_report_consensus_snapshot",
                f"{target.ticker} {target.fiscal_period}: no consensus snapshot before reported_at",
            )
            continue
        latest_timestamp = max(parse_utc_timestamp(row.snapshot_at) for row in eligible_snapshots)
        latest_snapshots = [
            row for row in eligible_snapshots if parse_utc_timestamp(row.snapshot_at) == latest_timestamp
        ]
        definitions = {
            (
                row.revenue_consensus,
                row.eps_consensus,
                row.revenue_currency,
                row.revenue_unit_scale,
                row.revenue_basis,
                row.eps_currency,
                row.eps_basis,
                row.eps_share_basis,
                row.eps_operations_basis,
                row.split_adjustment_basis,
            )
            for row in latest_snapshots
        }
        if len(definitions) > 1:
            exclude(
                "ambiguous_consensus_revision",
                f"{target.ticker} {target.fiscal_period}: conflicting consensus rows share the latest timestamp",
            )
            continue
        snapshot = sorted(latest_snapshots, key=lambda row: row.source_ref or row.source)[0]
        snapshot_age = parse_utc_timestamp(target.reported_at) - parse_utc_timestamp(snapshot.snapshot_at)
        if snapshot_age.days > maximum_snapshot_age_days:
            exclude(
                "stale_consensus_snapshot",
                f"{target.ticker} {target.fiscal_period}: latest consensus is {snapshot_age.days} days before reported_at",
            )
            continue
        cutoff = snapshot.snapshot_at
        history = [
            row
            for row in actuals
            if row.ticker == target.ticker
            and row.fiscal_period != target.fiscal_period
            and parse_utc_timestamp(row.reported_at) <= parse_utc_timestamp(cutoff)
        ]
        try:
            forecast = build_baseline_nowcast(history, snapshot, cutoff, config)
        except ValueError as exc:
            exclude(
                "model_input_validation_failed",
                f"{target.ticker} {target.fiscal_period}: {exc}",
            )
            failures.append(f"{target.ticker} {target.fiscal_period}: {exc}")
            continue

        input_timestamps = [snapshot.snapshot_at, *(row.reported_at for row in history)]
        latest_input = max(input_timestamps, key=parse_utc_timestamp)
        if parse_utc_timestamp(latest_input) > parse_utc_timestamp(cutoff):
            leakage_failures.append(f"{target.ticker} {target.fiscal_period}: input after cutoff")
        prior = actual_lookup.get((target.ticker, _prior_year(target.fiscal_period)))
        prior_year_eps = (
            prior.eps_actual
            if prior is not None
            and eps_split_basis_verified(prior.split_adjustment_basis)
            else None
        )
        consensus_eps = (
            snapshot.eps_consensus
            if eps_split_basis_verified(snapshot.split_adjustment_basis)
            else None
        )
        events.append(
            BacktestEvent(
                ticker=target.ticker,
                fiscal_period=target.fiscal_period,
                as_of_timestamp=cutoff,
                latest_input_timestamp=latest_input,
                target_reported_at=target.reported_at,
                input_source_ids=forecast.source_ids,
                revenue_forecast=forecast.revenue_midpoint,
                revenue_low=forecast.revenue_low,
                revenue_high=forecast.revenue_high,
                revenue_actual=target.revenue_actual,
                eps_forecast=forecast.eps_midpoint,
                eps_low=forecast.eps_low,
                eps_high=forecast.eps_high,
                eps_actual=target_eps_actual,
                consensus_revenue=snapshot.revenue_consensus,
                consensus_eps=consensus_eps,
                prior_year_revenue=prior.revenue_actual if prior else None,
                prior_year_eps=prior_year_eps,
                relative_classification=forecast.relative_classification,
            )
        )

    revenue_errors = [abs(event.revenue_forecast - event.revenue_actual) for event in events if event.revenue_forecast is not None and event.revenue_actual is not None]
    eps_errors = [abs(event.eps_forecast - event.eps_actual) for event in events if event.eps_forecast is not None and event.eps_actual is not None]
    revenue_actual_total = sum(abs(event.revenue_actual) for event in events if event.revenue_forecast is not None and event.revenue_actual is not None)
    interval_hits: list[float] = []
    revenue_interval_hits: list[float] = []
    eps_interval_hits: list[float] = []
    joint_interval_hits: list[float] = []
    directions: list[float] = []
    consensus_revenue_errors: list[float] = []
    prior_year_revenue_errors: list[float] = []
    consensus_eps_errors: list[float] = []
    prior_year_eps_errors: list[float] = []
    for event in events:
        revenue_hit: float | None = None
        eps_hit: float | None = None
        if event.revenue_actual is not None and event.revenue_low is not None and event.revenue_high is not None:
            revenue_hit = float(event.revenue_low <= event.revenue_actual <= event.revenue_high)
            revenue_interval_hits.append(revenue_hit)
            interval_hits.append(revenue_hit)
        if event.eps_actual is not None and event.eps_low is not None and event.eps_high is not None:
            eps_hit = float(event.eps_low <= event.eps_actual <= event.eps_high)
            eps_interval_hits.append(eps_hit)
            interval_hits.append(eps_hit)
        if revenue_hit is not None and eps_hit is not None:
            joint_interval_hits.append(float(bool(revenue_hit) and bool(eps_hit)))
        if event.revenue_actual is not None and event.consensus_revenue is not None:
            directions.append(float(event.relative_classification == _direction(event.revenue_actual, event.consensus_revenue, config.aligned_tolerance_pct)))
            consensus_revenue_errors.append(abs(event.consensus_revenue - event.revenue_actual))
        if event.prior_year_revenue is not None and event.revenue_actual is not None:
            prior_year_revenue_errors.append(abs(event.prior_year_revenue - event.revenue_actual))
        if event.consensus_eps is not None and event.eps_actual is not None:
            consensus_eps_errors.append(abs(event.consensus_eps - event.eps_actual))
        if event.prior_year_eps is not None and event.eps_actual is not None:
            prior_year_eps_errors.append(abs(event.prior_year_eps - event.eps_actual))

    benchmarks: dict[str, float] = {}
    for name, values in (
        ("consensus_revenue_mae", consensus_revenue_errors),
        ("prior_year_revenue_mae", prior_year_revenue_errors),
        ("consensus_eps_mae", consensus_eps_errors),
        ("prior_year_eps_mae", prior_year_eps_errors),
    ):
        value = _mean(values)
        if value is not None:
            benchmarks[name] = value

    revenue_mae = _mean(revenue_errors)
    eps_mae = _mean(eps_errors)
    benchmark_failures: list[str] = []
    if revenue_mae is not None and "consensus_revenue_mae" in benchmarks:
        if revenue_mae >= benchmarks["consensus_revenue_mae"]:
            benchmark_failures.append("revenue_model_did_not_improve_consensus")
    if eps_mae is not None and "consensus_eps_mae" in benchmarks:
        if eps_mae >= benchmarks["consensus_eps_mae"]:
            benchmark_failures.append("eps_model_did_not_improve_consensus")

    if not events:
        failures.insert(0, "No valid out-of-sample events")
    elif len(events) < minimum_backtest_events:
        failures.append(
            f"minimum_backtest_events: {len(events)} valid events; at least {minimum_backtest_events} required"
        )
    if leakage_failures:
        failures.append("Point-in-time leakage detected")
    if len(events) >= minimum_backtest_events and benchmark_failures:
        failures.extend(benchmark_failures)
    if not events or leakage_failures or (len(events) >= minimum_backtest_events and benchmark_failures):
        verdict = "failed"
    elif len(events) < minimum_backtest_events:
        verdict = "insufficient"
    else:
        verdict = "passed"
    return BacktestReport(
        verdict=verdict,
        event_count=len(events),
        valid_event_count=len(events),
        excluded_count=excluded_count,
        exclusion_reasons=exclusion_reasons,
        excluded_events=tuple(excluded_events),
        revenue_mae=revenue_mae,
        revenue_median_absolute_error=_median(revenue_errors),
        revenue_wape=(sum(revenue_errors) / revenue_actual_total if revenue_errors and revenue_actual_total else None),
        eps_mae=eps_mae,
        eps_median_absolute_error=_median(eps_errors),
        directional_accuracy=_mean(directions),
        interval_coverage=_mean(interval_hits),
        revenue_interval_coverage=_mean(revenue_interval_hits),
        eps_interval_coverage=_mean(eps_interval_hits),
        joint_interval_coverage=_mean(joint_interval_hits),
        benchmark_metrics=benchmarks,
        benchmark_failures=tuple(benchmark_failures),
        leakage_failures=tuple(leakage_failures),
        failures=tuple(failures),
        events=tuple(events),
    )


def assess_probability_calibration(
    observations: Sequence[ProbabilityObservation],
    policy: CalibrationPolicy | None = None,
) -> CalibrationStatus:
    policy = policy or CalibrationPolicy()
    if not observations:
        return CalibrationStatus(
            state=NowcastState.BACKTEST_INSUFFICIENT,
            probability_available=False,
            event_count=0,
            brier_score=None,
            benchmark_brier_score=None,
            calibration_error=None,
            calibration_bins=(),
            failed_gates=("no_probability_evidence", "minimum_100_events"),
            failed_gate_details={
                "no_probability_evidence": "No valid out-of-sample probability observations are available.",
                "minimum_100_events": f"0 valid events; at least {policy.minimum_events} are required.",
            },
        )

    probabilities = [row.probability for row in observations]
    outcomes = [1.0 if row.outcome else 0.0 for row in observations]
    brier = sum((probability - outcome) ** 2 for probability, outcome in zip(probabilities, outcomes, strict=True)) / len(observations)
    base_rate = sum(outcomes) / len(outcomes)
    benchmark = sum((base_rate - outcome) ** 2 for outcome in outcomes) / len(outcomes)
    bins: dict[int, list[tuple[float, float]]] = {}
    for probability, outcome in zip(probabilities, outcomes, strict=True):
        index = min(int(probability * 10), 9)
        bins.setdefault(index, []).append((probability, outcome))
    bin_sizes_valid = all(len(rows) >= policy.minimum_bin_size for rows in bins.values())
    calibration_bins = tuple(
        CalibrationBin(
            lower_bound=index / 10,
            upper_bound=(index + 1) / 10,
            event_count=len(rows),
            mean_probability=sum(probability for probability, _ in rows) / len(rows),
            outcome_rate=sum(outcome for _, outcome in rows) / len(rows),
            meets_minimum_size=len(rows) >= policy.minimum_bin_size,
        )
        for index, rows in sorted(bins.items())
    )
    calibration_error = sum(
        len(rows) / len(observations)
        * abs(sum(probability for probability, _ in rows) / len(rows) - sum(outcome for _, outcome in rows) / len(rows))
        for rows in bins.values()
    )

    failed: list[str] = []
    if len(observations) < policy.minimum_events:
        failed.append("minimum_100_events")
    if brier > policy.maximum_brier_score:
        failed.append("maximum_brier_score")
    if not bin_sizes_valid:
        failed.append("minimum_calibration_bin_size")
    if brier >= benchmark:
        failed.append("must_improve_constant_rate_benchmark")
    details = {
        "minimum_100_events": f"{len(observations)} valid events; at least {policy.minimum_events} are required.",
        "maximum_brier_score": f"Brier score {brier:.6f} exceeds the maximum {policy.maximum_brier_score:.6f}.",
        "minimum_calibration_bin_size": f"Every populated calibration bin must contain at least {policy.minimum_bin_size} events.",
        "must_improve_constant_rate_benchmark": f"Brier score {brier:.6f} must be lower than constant-rate benchmark {benchmark:.6f}.",
    }
    available = not failed
    return CalibrationStatus(
        state=(
            NowcastState.CALIBRATED
            if available
            else NowcastState.BACKTEST_INSUFFICIENT
            if len(observations) < policy.minimum_events
            else NowcastState.BACKTEST_READY
        ),
        probability_available=available,
        event_count=len(observations),
        brier_score=brier,
        benchmark_brier_score=benchmark,
        calibration_error=calibration_error,
        calibration_bins=calibration_bins,
        failed_gates=tuple(failed),
        failed_gate_details={gate: details[gate] for gate in failed},
    )
