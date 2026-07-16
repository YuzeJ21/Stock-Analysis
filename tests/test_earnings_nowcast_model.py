from __future__ import annotations

from dataclasses import replace

import pytest

from src.earnings_nowcast_contract import ConsensusSnapshot, NowcastState, QuarterlyActual
from src import earnings_nowcast_model
from src.earnings_nowcast_model import NowcastConfig, build_baseline_nowcast, classify_consensus_gap


CUTOFF = "2026-01-31T23:59:59Z"


def _actuals(*, eps_values: tuple[float | None, ...] = (0.8, 0.9, 1.0, 1.1, 1.2)) -> list[QuarterlyActual]:
    rows = (
        ("2024-Q4", "2024-12-31", "2025-02-01T21:00:00Z", 90.0),
        ("2025-Q1", "2025-03-31", "2025-05-01T21:00:00Z", 92.0),
        ("2025-Q2", "2025-06-30", "2025-08-01T21:00:00Z", 95.0),
        ("2025-Q3", "2025-09-30", "2025-11-01T21:00:00Z", 98.0),
        ("2025-Q4", "2025-12-31", "2026-01-15T21:00:00Z", 101.0),
    )
    return [
        QuarterlyActual(
            ticker="SYN1",
            fiscal_period=period,
            period_end_date=period_end,
            reported_at=reported_at,
            revenue_actual=revenue,
            eps_actual=eps,
            source="synthetic_test_fixture",
            source_ref=f"fixture://actual/{period}",
            retrieved_at=reported_at,
        )
        for (period, period_end, reported_at, revenue), eps in zip(rows, eps_values, strict=True)
    ]


def _consensus(*, revenue: float | None = 104.0, eps: float | None = 1.25) -> ConsensusSnapshot:
    return ConsensusSnapshot(
        ticker="SYN1",
        fiscal_period="2026-Q1",
        snapshot_at="2026-01-20T12:00:00Z",
        revenue_consensus=revenue,
        eps_consensus=eps,
        source="synthetic_test_fixture",
        retrieved_at="2026-01-20T12:01:00Z",
    )


def test_identical_inputs_produce_identical_forecast_and_hash():
    config = NowcastConfig()
    first = build_baseline_nowcast(_actuals(), _consensus(), CUTOFF, config)
    second = build_baseline_nowcast(list(reversed(_actuals())), _consensus(), CUTOFF, config)

    assert first == second
    assert first.input_snapshot_hash == second.input_snapshot_hash
    assert first.readiness_state == NowcastState.BASELINE_READY


def test_forecast_ranges_are_ordered_and_respect_minimum_widths():
    config = NowcastConfig(minimum_revenue_half_width_pct=0.05, minimum_eps_half_width=0.10)
    result = build_baseline_nowcast(_actuals(), _consensus(), CUTOFF, config)

    assert result.revenue_low < result.revenue_midpoint < result.revenue_high
    assert result.eps_low < result.eps_midpoint < result.eps_high
    assert result.revenue_high - result.revenue_midpoint >= result.revenue_midpoint * 0.05 - 1e-9
    assert result.eps_high - result.eps_midpoint >= 0.10 - 1e-9


def test_classification_uses_range_overlap_and_tolerance():
    assert classify_consensus_gap(105.0, 100.0, 110.0, tolerance_pct=0.02) == "aligned"
    assert classify_consensus_gap(90.0, 110.0, 120.0, tolerance_pct=0.02) == "higher"
    assert classify_consensus_gap(130.0, 100.0, 110.0, tolerance_pct=0.02) == "lower"


def test_forecast_stores_gap_and_primary_consensus_classification():
    result = build_baseline_nowcast(_actuals(), _consensus(revenue=80.0, eps=0.5), CUTOFF, NowcastConfig())

    assert result.revenue_gap_pct is not None and result.revenue_gap_pct > 0
    assert result.eps_gap_pct is not None and result.eps_gap_pct > 0
    assert result.relative_classification == "higher"


def test_blocked_eps_never_renders_a_numeric_eps_forecast():
    result = build_baseline_nowcast(
        _actuals(eps_values=(0.8, -2.0, 3.5, -4.0, 6.0)),
        _consensus(),
        CUTOFF,
        NowcastConfig(),
    )

    assert result.revenue_midpoint is not None
    assert result.eps_midpoint is None
    assert result.eps_low is None
    assert result.eps_high is None
    assert result.eps_gap_pct is None


def test_missing_prior_year_target_quarter_is_withheld_as_a_continuity_gap():
    rows = [row for row in _actuals() if row.fiscal_period != "2025-Q1"]

    with pytest.raises(ValueError, match="quarter_history_gap"):
        build_baseline_nowcast(rows, _consensus(), CUTOFF, NowcastConfig(minimum_history_quarters=4))


def test_missing_q4_never_passes_q3_to_q1_into_sequential_growth(monkeypatch: pytest.MonkeyPatch):
    rows = [row for row in _actuals() if row.fiscal_period != "2025-Q4"]
    rows.append(
        QuarterlyActual(
            ticker="SYN1",
            fiscal_period="2026-Q1",
            period_end_date="2026-03-31",
            reported_at="2026-01-16T21:00:00Z",
            revenue_actual=104.0,
            eps_actual=1.3,
            source="synthetic_test_fixture",
            source_ref="fixture://actual/2026-Q1",
            retrieved_at="2026-01-16T21:01:00Z",
        )
    )
    sequential_inputs: list[list[float]] = []

    def capture_sequential_growth(values: list[float]) -> list[float]:
        sequential_inputs.append(values)
        return [0.01]

    monkeypatch.setattr(earnings_nowcast_model, "_sequential_growth", capture_sequential_growth)

    with pytest.raises(ValueError, match="quarter_history_gap"):
        build_baseline_nowcast(rows, replace(_consensus(), fiscal_period="2026-Q2"), CUTOFF)

    assert sequential_inputs == []


def test_post_cutoff_actual_fails_closed():
    rows = _actuals()
    rows.append(
        QuarterlyActual(
            ticker="SYN1",
            fiscal_period="2026-Q1",
            period_end_date="2026-03-31",
            reported_at="2026-04-20T21:00:00Z",
            revenue_actual=110.0,
            eps_actual=1.3,
            source="synthetic_test_fixture",
            source_ref="fixture://actual/2026-Q1",
            retrieved_at="2026-04-20T21:01:00Z",
        )
    )

    with pytest.raises(ValueError, match="Nowcast is blocked: post_cutoff_evidence"):
        build_baseline_nowcast(rows, _consensus(), CUTOFF, NowcastConfig())


def test_config_rejects_weights_that_do_not_sum_to_one():
    with pytest.raises(ValueError, match="weights must sum to 1"):
        NowcastConfig(recent_growth_weight=0.8, seasonal_growth_weight=0.8)


def test_exact_duplicate_quarter_does_not_change_forecast():
    rows = _actuals()
    duplicate = replace(rows[-1], source="second_source", source_ref="fixture://duplicate/2025-Q4")

    baseline = build_baseline_nowcast(rows, _consensus(), CUTOFF)
    with_duplicate = build_baseline_nowcast([*rows, duplicate], _consensus(), CUTOFF)

    assert with_duplicate.revenue_midpoint == baseline.revenue_midpoint
    assert with_duplicate.eps_midpoint == baseline.eps_midpoint


def test_forecast_exposes_independent_metric_classifications():
    result = build_baseline_nowcast(_actuals(), _consensus(revenue=80.0, eps=5.0), CUTOFF)

    assert result.revenue_classification == "higher"
    assert result.eps_classification == "lower"


def test_forecast_records_expected_report_date_and_horizon():
    consensus = replace(_consensus(), expected_report_date="2026-02-15")

    result = build_baseline_nowcast(_actuals(), consensus, CUTOFF)

    assert result.expected_report_date == "2026-02-15"
    assert result.forecast_horizon_days == 15
