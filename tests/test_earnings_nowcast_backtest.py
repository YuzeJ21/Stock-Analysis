from __future__ import annotations

import pytest

from src.earnings_nowcast_backtest import (
    CalibrationPolicy,
    ProbabilityObservation,
    assess_probability_calibration,
    walk_forward_backtest,
)
from src.earnings_nowcast_contract import ConsensusSnapshot, NowcastState, QuarterlyActual
from src.earnings_nowcast_model import NowcastConfig


def _actual(period: str, end: str, reported: str, revenue: float, eps: float) -> QuarterlyActual:
    return QuarterlyActual(
        ticker="SYN1",
        fiscal_period=period,
        period_end_date=end,
        reported_at=reported,
        revenue_actual=revenue,
        eps_actual=eps,
        source="synthetic_test_fixture",
        source_ref=f"fixture://actual/{period}",
        retrieved_at=reported,
    )


def _history_with_target() -> list[QuarterlyActual]:
    return [
        _actual("2024-Q1", "2024-03-31", "2024-04-20T21:00:00Z", 80.0, 0.60),
        _actual("2024-Q2", "2024-06-30", "2024-07-20T21:00:00Z", 84.0, 0.65),
        _actual("2024-Q3", "2024-09-30", "2024-10-20T21:00:00Z", 88.0, 0.70),
        _actual("2024-Q4", "2024-12-31", "2025-01-20T21:00:00Z", 92.0, 0.75),
        _actual("2025-Q1", "2025-03-31", "2025-04-20T21:00:00Z", 96.0, 0.80),
        _actual("2025-Q2", "2025-06-30", "2025-07-20T21:00:00Z", 100.0, 0.85),
        _actual("2025-Q3", "2025-09-30", "2025-10-20T21:00:00Z", 104.0, 0.90),
        _actual("2025-Q4", "2025-12-31", "2026-01-20T21:00:00Z", 108.0, 0.95),
        _actual("2026-Q1", "2026-03-31", "2026-04-20T21:00:00Z", 112.0, 1.00),
    ]


def _consensus() -> list[ConsensusSnapshot]:
    return [
        ConsensusSnapshot(
            ticker="SYN1",
            fiscal_period="2026-Q1",
            snapshot_at="2026-01-31T23:59:59Z",
            revenue_consensus=110.0,
            eps_consensus=0.98,
            source="synthetic_test_fixture",
            retrieved_at="2026-01-31T23:59:59Z",
        ),
        ConsensusSnapshot(
            ticker="SYN1",
            fiscal_period="2026-Q1",
            snapshot_at="2026-04-21T00:00:00Z",
            revenue_consensus=112.0,
            eps_consensus=1.00,
            source="synthetic_test_fixture",
            retrieved_at="2026-04-21T00:00:00Z",
        ),
    ]


def test_walk_forward_never_uses_target_actual_or_later_consensus():
    report = walk_forward_backtest(_history_with_target(), _consensus(), NowcastConfig())

    assert report.leakage_failures == ()
    assert report.event_count == 1
    assert all(event.latest_input_timestamp <= event.as_of_timestamp for event in report.events)
    assert report.events[0].target_reported_at > report.events[0].as_of_timestamp
    assert "fixture://actual/2026-Q1" not in report.events[0].input_source_ids


def test_walk_forward_reports_errors_benchmarks_and_interval_coverage():
    report = walk_forward_backtest(_history_with_target(), _consensus(), NowcastConfig())

    assert report.verdict == "passed"
    assert report.revenue_mae is not None
    assert report.revenue_wape is not None
    assert report.eps_mae is not None
    assert report.interval_coverage in {0.0, 1.0}
    assert set(report.benchmark_metrics) >= {"consensus_revenue_mae", "prior_year_revenue_mae"}


def test_probability_is_withheld_below_100_out_of_sample_events():
    observations = [ProbabilityObservation(probability=0.6, outcome=index % 2 == 0) for index in range(99)]

    status = assess_probability_calibration(observations)

    assert status.state == NowcastState.BACKTEST_READY
    assert status.probability_available is False
    assert "minimum_100_events" in status.failed_gates


def test_probability_gate_requires_benchmark_improvement_and_populated_bins():
    observations = [ProbabilityObservation(probability=0.9 if index % 2 == 0 else 0.1, outcome=index % 2 == 0) for index in range(100)]

    status = assess_probability_calibration(
        observations,
        CalibrationPolicy(minimum_events=100, maximum_brier_score=0.25, minimum_bin_size=10),
    )

    assert status.state == NowcastState.CALIBRATED
    assert status.probability_available is True
    assert status.brier_score == pytest.approx(0.01)
    assert status.benchmark_brier_score == pytest.approx(0.25)
    assert status.failed_gates == ()


def test_empty_probability_evidence_fails_closed():
    status = assess_probability_calibration([])

    assert status.probability_available is False
    assert "no_probability_evidence" in status.failed_gates


def test_invalid_probability_is_rejected():
    with pytest.raises(ValueError, match="between 0 and 1"):
        ProbabilityObservation(probability=1.1, outcome=True)


def test_empty_backtest_evidence_fails_closed():
    report = walk_forward_backtest([], [], NowcastConfig())

    assert report.verdict == "failed"
    assert "No valid out-of-sample events" in report.failures
