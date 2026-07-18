from pathlib import Path

from src.earnings_nowcast_cohort import build_cohort_readiness


FIXTURE_DIR = Path("tests/fixtures/earnings_nowcast_onboarding")


def test_cohort_board_keeps_metric_and_evidence_gates_separate():
    rows = build_cohort_readiness(
        FIXTURE_DIR,
        tickers=("SYN1", "MISS"),
        as_of="2026-01-31T23:59:59Z",
    )

    ready, missing = rows
    assert ready.ticker == "SYN1"
    assert ready.latest_actual_period == "2025-Q4"
    assert ready.forecast_period == "2026-Q1"
    assert ready.revenue_history_count == 5
    assert ready.eps_history_count == 5
    assert ready.q4_revenue_count == 2
    assert ready.q4_eps_count == 2
    assert ready.revenue_ready is True
    assert ready.eps_ready is True
    assert ready.consensus_snapshot_count == 1
    assert ready.state == "baseline_ready"
    assert ready.backtest_event_count == 0
    assert ready.calibration_event_count == 0

    assert missing.ticker == "MISS"
    assert missing.state == "blocked"
    assert missing.latest_actual_period == ""
    assert missing.blocker == "quarterly_actuals_missing"
    assert "source-backed quarterly actuals" in missing.next_action


def test_cohort_board_accepts_explicit_evaluation_counts_without_promoting_probability():
    row = build_cohort_readiness(
        FIXTURE_DIR,
        tickers=("SYN1",),
        as_of="2026-01-31T23:59:59Z",
        backtest_counts={"SYN1": 12},
        calibration_counts={"SYN1": 4},
    )[0]

    assert row.backtest_event_count == 12
    assert row.calibration_event_count == 4
    assert row.probability_state == "awaiting_calibration_evidence"
