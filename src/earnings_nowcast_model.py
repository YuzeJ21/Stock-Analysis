from __future__ import annotations

import math
import statistics
from dataclasses import asdict, dataclass
from typing import Sequence

from src.earnings_nowcast_contract import ConsensusSnapshot, ForecastSnapshot, QuarterlyActual, input_snapshot_hash
from src.earnings_nowcast_readiness import assess_nowcast_readiness


@dataclass(frozen=True)
class NowcastConfig:
    model_version: str = "deterministic-v1"
    minimum_history_quarters: int = 5
    recent_growth_weight: float = 0.5
    seasonal_growth_weight: float = 0.5
    minimum_revenue_half_width_pct: float = 0.05
    minimum_eps_half_width: float = 0.10
    aligned_tolerance_pct: float = 0.02

    def __post_init__(self) -> None:
        if self.minimum_history_quarters < 4:
            raise ValueError("minimum_history_quarters must be at least 4")
        if not math.isclose(self.recent_growth_weight + self.seasonal_growth_weight, 1.0, abs_tol=1e-9):
            raise ValueError("recent and seasonal weights must sum to 1")
        if self.recent_growth_weight < 0 or self.seasonal_growth_weight < 0:
            raise ValueError("forecast weights must be non-negative")
        if self.minimum_revenue_half_width_pct <= 0:
            raise ValueError("minimum_revenue_half_width_pct must be positive")
        if self.minimum_eps_half_width <= 0:
            raise ValueError("minimum_eps_half_width must be positive")
        if self.aligned_tolerance_pct < 0:
            raise ValueError("aligned_tolerance_pct must be non-negative")


def _period_parts(period: str) -> tuple[int, int]:
    year, quarter = period.split("-Q", 1)
    return int(year), int(quarter)


def _prior_year_period(period: str) -> str:
    year, quarter = _period_parts(period)
    return f"{year - 1}-Q{quarter}"


def _median(values: Sequence[float]) -> float:
    if not values:
        raise ValueError("Forecast input series is empty")
    return float(statistics.median(values))


def _dispersion(values: Sequence[float]) -> float:
    return float(statistics.pstdev(values)) if len(values) > 1 else 0.0


def _sequential_growth(values: Sequence[float]) -> list[float]:
    return [current / previous - 1 for previous, current in zip(values, values[1:]) if previous != 0]


def _sequential_change(values: Sequence[float]) -> list[float]:
    return [current - previous for previous, current in zip(values, values[1:])]


def _year_over_year_growth(rows: Sequence[QuarterlyActual], metric: str) -> list[float]:
    lookup = {row.fiscal_period: getattr(row, metric) for row in rows if getattr(row, metric) is not None}
    values: list[float] = []
    for period, current in lookup.items():
        year, quarter = _period_parts(period)
        previous = lookup.get(f"{year - 1}-Q{quarter}")
        if previous not in {None, 0}:
            values.append(float(current) / float(previous) - 1)
    return values


def _year_over_year_change(rows: Sequence[QuarterlyActual], metric: str) -> list[float]:
    lookup = {row.fiscal_period: getattr(row, metric) for row in rows if getattr(row, metric) is not None}
    values: list[float] = []
    for period, current in lookup.items():
        year, quarter = _period_parts(period)
        previous = lookup.get(f"{year - 1}-Q{quarter}")
        if previous is not None:
            values.append(float(current) - float(previous))
    return values


def classify_consensus_gap(consensus: float, forecast_low: float, forecast_high: float, *, tolerance_pct: float) -> str:
    tolerance = abs(consensus) * tolerance_pct
    if forecast_low > consensus + tolerance:
        return "higher"
    if forecast_high < consensus - tolerance:
        return "lower"
    return "aligned"


def _gap(midpoint: float | None, consensus: float | None) -> float | None:
    if midpoint is None or consensus in {None, 0}:
        return None
    return (midpoint - float(consensus)) / abs(float(consensus))


def _revenue_forecast(
    rows: Sequence[QuarterlyActual],
    target_period: str,
    config: NowcastConfig,
) -> tuple[float, float, float]:
    values = [float(row.revenue_actual) for row in rows if row.revenue_actual is not None]
    prior_year = next(
        (float(row.revenue_actual) for row in rows if row.fiscal_period == _prior_year_period(target_period) and row.revenue_actual is not None),
        None,
    )
    if prior_year is None:
        raise ValueError("Missing prior-year target quarter revenue; seasonality cannot be inferred")
    sequential = _sequential_growth(values)
    seasonal = _year_over_year_growth(rows, "revenue_actual")
    recent_growth = _median(sequential[-4:])
    seasonal_growth = _median(seasonal) if seasonal else recent_growth
    recent_estimate = values[-1] * (1 + recent_growth)
    seasonal_estimate = prior_year * (1 + seasonal_growth)
    midpoint = (
        config.recent_growth_weight * recent_estimate
        + config.seasonal_growth_weight * seasonal_estimate
    )
    half_width = max(
        abs(midpoint) * config.minimum_revenue_half_width_pct,
        abs(midpoint) * _dispersion([*sequential, *seasonal]),
    )
    return midpoint, midpoint - half_width, midpoint + half_width


def _eps_forecast(
    rows: Sequence[QuarterlyActual],
    target_period: str,
    config: NowcastConfig,
) -> tuple[float, float, float]:
    values = [float(row.eps_actual) for row in rows if row.eps_actual is not None]
    prior_year = next(
        (float(row.eps_actual) for row in rows if row.fiscal_period == _prior_year_period(target_period) and row.eps_actual is not None),
        None,
    )
    if prior_year is None:
        raise ValueError("Missing prior-year target quarter EPS; seasonality cannot be inferred")
    sequential = _sequential_change(values)
    seasonal = _year_over_year_change(rows, "eps_actual")
    recent_change = _median(sequential[-4:])
    seasonal_change = _median(seasonal) if seasonal else recent_change
    recent_estimate = values[-1] + recent_change
    seasonal_estimate = prior_year + seasonal_change
    midpoint = (
        config.recent_growth_weight * recent_estimate
        + config.seasonal_growth_weight * seasonal_estimate
    )
    half_width = max(config.minimum_eps_half_width, _dispersion([*sequential, *seasonal]))
    return midpoint, midpoint - half_width, midpoint + half_width


def build_baseline_nowcast(
    actuals: Sequence[QuarterlyActual],
    consensus: ConsensusSnapshot,
    cutoff: str,
    config: NowcastConfig | None = None,
    *,
    asset_type: str = "company",
) -> ForecastSnapshot:
    config = config or NowcastConfig()
    rows = sorted(
        (row for row in actuals if row.ticker == consensus.ticker),
        key=lambda row: (row.period_end_date, row.reported_at, row.source_ref),
    )
    readiness = assess_nowcast_readiness(
        ticker=consensus.ticker,
        fiscal_period=consensus.fiscal_period,
        as_of_timestamp=cutoff,
        actuals=rows,
        consensus=[consensus],
        asset_type=asset_type,
        minimum_history_quarters=config.minimum_history_quarters,
    )
    if readiness.state.value in {"blocked", "excluded"}:
        missing = ", ".join(readiness.missing_evidence) or readiness.state.value
        raise ValueError(f"Nowcast is blocked: {missing}")

    revenue_midpoint = revenue_low = revenue_high = None
    if readiness.revenue_ready:
        revenue_midpoint, revenue_low, revenue_high = _revenue_forecast(rows, consensus.fiscal_period, config)

    eps_midpoint = eps_low = eps_high = None
    if readiness.eps_ready:
        eps_midpoint, eps_low, eps_high = _eps_forecast(rows, consensus.fiscal_period, config)

    revenue_classification = (
        classify_consensus_gap(
            float(consensus.revenue_consensus),
            float(revenue_low),
            float(revenue_high),
            tolerance_pct=config.aligned_tolerance_pct,
        )
        if revenue_midpoint is not None and consensus.revenue_consensus is not None
        else None
    )
    eps_classification = (
        classify_consensus_gap(
            float(consensus.eps_consensus),
            float(eps_low),
            float(eps_high),
            tolerance_pct=config.aligned_tolerance_pct,
        )
        if eps_midpoint is not None and consensus.eps_consensus is not None
        else None
    )
    primary_classification = revenue_classification or eps_classification or "withheld"

    digest = input_snapshot_hash([*rows, consensus, asdict(config)])
    return ForecastSnapshot(
        forecast_id=f"NOWCAST-{consensus.ticker}-{consensus.fiscal_period}-{digest[:12]}",
        ticker=consensus.ticker,
        fiscal_period=consensus.fiscal_period,
        as_of_timestamp=cutoff,
        model_version=config.model_version,
        input_snapshot_hash=digest,
        revenue_midpoint=revenue_midpoint,
        revenue_low=revenue_low,
        revenue_high=revenue_high,
        eps_midpoint=eps_midpoint,
        eps_low=eps_low,
        eps_high=eps_high,
        consensus_revenue=consensus.revenue_consensus,
        consensus_eps=consensus.eps_consensus,
        revenue_gap_pct=_gap(revenue_midpoint, consensus.revenue_consensus),
        eps_gap_pct=_gap(eps_midpoint, consensus.eps_consensus),
        relative_classification=primary_classification,
        confidence_band="medium" if readiness.revenue_ready and readiness.eps_ready else "low",
        readiness_state=readiness.state,
        freshness_state=readiness.freshness_state,
        source_ids=readiness.source_ids,
        created_at=cutoff,
    )
