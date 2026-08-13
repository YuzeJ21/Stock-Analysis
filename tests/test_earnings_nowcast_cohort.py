import csv
import hashlib
import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from src.earnings_nowcast_backtest import (
    BacktestEvent,
    BacktestReport,
    ProbabilityObservation,
    assess_probability_calibration,
    walk_forward_backtest,
)
from src.earnings_nowcast_cohort import build_cohort_readiness
from src.earnings_nowcast_contract import ConsensusSnapshot, QuarterlyActual


FIXTURE_DIR = Path("tests/fixtures/earnings_nowcast_onboarding")


def _backtest_report(
    *,
    valid_event_count: int = 100,
    verdict: str = "passed",
    benchmark_failures: tuple[str, ...] = (),
    leakage_failures: tuple[str, ...] = (),
    failures: tuple[str, ...] = (),
) -> BacktestReport:
    events = tuple(
        BacktestEvent(
            ticker=f"SYN{index:03d}",
            fiscal_period="2026-Q1",
            as_of_timestamp="2026-01-31T23:59:59Z",
            latest_input_timestamp="2026-01-31T23:59:59Z",
            target_reported_at="2026-02-15T21:00:00Z",
            input_source_ids=(
                f"fixture://event/{index}/history",
                f"fixture://event/{index}/consensus",
            ),
            revenue_forecast=102.0 if index % 2 == 0 else 100.0,
            revenue_low=101.0 if index % 2 == 0 else 95.0,
            revenue_high=105.0,
            revenue_actual=101.0,
            eps_forecast=1.02 if index % 2 == 0 else 1.0,
            eps_low=1.01 if index % 2 == 0 else 0.9,
            eps_high=1.1,
            eps_actual=1.01,
            consensus_revenue=99.0 if index % 2 == 0 else 103.0,
            consensus_eps=0.99 if index % 2 == 0 else 1.03,
            prior_year_revenue=90.0,
            prior_year_eps=0.9,
            relative_classification="higher" if index % 2 == 0 else "aligned",
            model_version="synthetic-test-only-v1",
            input_snapshot_hash=hashlib.sha256(
                f"synthetic-test-input/{index}".encode("utf-8")
            ).hexdigest(),
        )
        for index in range(valid_event_count)
    )
    return BacktestReport(
        verdict=verdict,
        event_count=valid_event_count,
        valid_event_count=valid_event_count,
        excluded_count=0,
        exclusion_reasons={},
        excluded_events=(),
        revenue_mae=1.0,
        revenue_median_absolute_error=1.0,
        revenue_wape=1.0 / 101.0,
        eps_mae=0.01,
        eps_median_absolute_error=0.01,
        directional_accuracy=1.0,
        interval_coverage=1.0,
        revenue_interval_coverage=1.0,
        eps_interval_coverage=1.0,
        joint_interval_coverage=1.0,
        benchmark_metrics={
            "consensus_revenue_mae": 2.0,
            "prior_year_revenue_mae": 11.0,
            "consensus_eps_mae": 0.02,
            "prior_year_eps_mae": 0.11,
        },
        benchmark_failures=benchmark_failures,
        leakage_failures=leakage_failures,
        failures=failures,
        events=events,
    )


def _single_metric_backtest_report(metric: str) -> BacktestReport:
    report = _backtest_report()
    if metric == "revenue":
        return replace(
            report,
            eps_mae=None,
            eps_median_absolute_error=None,
            eps_interval_coverage=None,
            joint_interval_coverage=None,
            events=tuple(
                replace(
                    event,
                    eps_forecast=None,
                    eps_low=None,
                    eps_high=None,
                )
                for event in report.events
            ),
        )
    if metric == "eps":
        return replace(
            report,
            revenue_mae=None,
            revenue_median_absolute_error=None,
            revenue_wape=None,
            revenue_interval_coverage=None,
            joint_interval_coverage=None,
            events=tuple(
                replace(
                    event,
                    revenue_forecast=None,
                    revenue_low=None,
                    revenue_high=None,
                )
                for event in report.events
            ),
        )
    raise ValueError(f"Unsupported metric: {metric}")


def _replace_first_backtest_event(
    report: BacktestReport,
    **changes,
) -> BacktestReport:
    return replace(
        report,
        events=(replace(report.events[0], **changes), *report.events[1:]),
    )


def _mutate_prior_year_revenue_with_recomputed_benchmark(
    report: BacktestReport,
) -> BacktestReport:
    changed = _replace_first_backtest_event(report, prior_year_revenue=91.0)
    return replace(
        changed,
        benchmark_metrics={
            **changed.benchmark_metrics,
            "prior_year_revenue_mae": 10.99,
        },
    )


def _mutate_classification_with_recomputed_summary(
    report: BacktestReport,
) -> BacktestReport:
    changed = _replace_first_backtest_event(
        report,
        revenue_low=95.0,
        relative_classification="aligned",
    )
    return replace(changed, directional_accuracy=0.99)


def _bound_calibration_status(
    report: BacktestReport | None = None,
    *,
    fixed_probability: float | None = None,
    invert_outcomes: bool = False,
    identity_prefix: str | None = None,
    as_of_timestamp: str | None = None,
    metric: str = "revenue",
):
    report = report or _backtest_report()
    observations = []
    for event in report.events:
        if metric == "revenue":
            outcome = bool(event.revenue_actual > event.consensus_revenue)
        else:
            outcome = bool(event.eps_actual > event.consensus_eps)
        if invert_outcomes:
            outcome = not outcome
        observations.append(
            ProbabilityObservation(
                probability=(
                    fixed_probability
                    if fixed_probability is not None
                    else 0.9
                    if outcome
                    else 0.1
                ),
                outcome=outcome,
                ticker=(
                    f"{identity_prefix}{event.ticker}"
                    if identity_prefix is not None
                    else event.ticker
                ),
                fiscal_period=event.fiscal_period,
                as_of_timestamp=as_of_timestamp or event.as_of_timestamp,
                outcome_definition=f"{metric}_actual_strictly_above_consensus",
            )
        )
    return assess_probability_calibration(observations, backtest_report=report)


def _reassess_with_true_probability(
    status,
    probability: float,
    report: BacktestReport,
):
    return assess_probability_calibration(
        tuple(
            replace(
                observation,
                probability=probability if observation.outcome else 0.1,
            )
            for observation in status.observations
        ),
        backtest_report=report,
    )


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


def test_raw_calibration_event_count_never_establishes_calibrated_probability_state():
    row = build_cohort_readiness(
        FIXTURE_DIR,
        tickers=("SYN1",),
        as_of="2026-01-31T23:59:59Z",
        calibration_counts={"SYN1": 100},
    )[0]

    assert row.calibration_event_count == 100
    assert row.probability_state == "awaiting_calibration_evidence"


def test_verified_calibration_status_without_backtest_report_fails_closed():
    status = assess_probability_calibration(
        [
            ProbabilityObservation(
                probability=0.9 if index % 2 == 0 else 0.1,
                outcome=index % 2 == 0,
            )
            for index in range(100)
        ]
    )

    row = build_cohort_readiness(
        FIXTURE_DIR,
        tickers=("SYN1",),
        as_of="2026-01-31T23:59:59Z",
        calibration_counts={"SYN1": 100},
        calibration_statuses={"SYN1": status},
    )[0]

    assert status.probability_available is True
    assert row.calibration_event_count == 100
    assert row.probability_state == "awaiting_calibration_evidence"


@pytest.mark.parametrize("metric", ["revenue", "eps"])
def test_paired_verified_calibration_and_backtest_reports_can_establish_calibrated_state(
    metric,
):
    report = _backtest_report()
    status = _bound_calibration_status(report, metric=metric)

    row = build_cohort_readiness(
        FIXTURE_DIR,
        tickers=("SYN1",),
        as_of="2026-01-31T23:59:59Z",
        calibration_counts={"SYN1": 100},
        calibration_statuses={"SYN1": status},
        calibration_backtests={"SYN1": report},
    )[0]

    assert row.backtest_event_count == 100
    assert row.calibration_event_count == 100
    assert len(status.backtest_evidence_digest or "") == 64
    assert row.probability_state == "calibrated"


def test_bound_calibration_without_report_binding_remains_non_promotable():
    report = _backtest_report()
    bound_observations = _bound_calibration_status(report).observations
    standalone = assess_probability_calibration(bound_observations)

    row = build_cohort_readiness(
        FIXTURE_DIR,
        tickers=("SYN1",),
        as_of="2026-01-31T23:59:59Z",
        calibration_statuses={"SYN1": standalone},
        calibration_backtests={"SYN1": report},
    )[0]

    assert standalone.probability_available is True
    assert standalone.backtest_evidence_digest is None
    assert row.probability_state == "awaiting_calibration_evidence"


@pytest.mark.parametrize(
    "mutate_report",
    [
        pytest.param(
            lambda report: _replace_first_backtest_event(
                report,
                latest_input_timestamp="2026-01-31T23:58:59Z",
            ),
            id="latest-input-timestamp",
        ),
        pytest.param(
            lambda report: _replace_first_backtest_event(
                report,
                target_reported_at="2026-02-16T21:00:00Z",
            ),
            id="target-reported-at",
        ),
        pytest.param(
            lambda report: _replace_first_backtest_event(
                report,
                input_source_ids=(
                    "fixture://event/000/relabeled-history",
                    report.events[0].input_source_ids[1],
                ),
            ),
            id="source-id-relabel",
        ),
        pytest.param(
            lambda report: _replace_first_backtest_event(
                report,
                input_source_ids=tuple(reversed(report.events[0].input_source_ids)),
            ),
            id="source-id-order",
        ),
        pytest.param(
            lambda report: _replace_first_backtest_event(
                report,
                model_version="synthetic-test-only-v2",
            ),
            id="model-version",
        ),
        pytest.param(
            lambda report: _replace_first_backtest_event(
                report,
                input_snapshot_hash="f" * 64,
            ),
            id="input-snapshot-hash",
        ),
        pytest.param(
            _mutate_prior_year_revenue_with_recomputed_benchmark,
            id="numeric-field-with-recomputed-benchmark",
        ),
        pytest.param(
            _mutate_classification_with_recomputed_summary,
            id="classification-with-recomputed-summary",
        ),
    ],
)
def test_post_assessment_event_mutation_requires_fresh_report_pairing(mutate_report):
    report = _backtest_report()
    status = _bound_calibration_status(report)
    changed = mutate_report(report)

    stale_row = build_cohort_readiness(
        FIXTURE_DIR,
        tickers=("SYN1",),
        as_of="2026-01-31T23:59:59Z",
        calibration_statuses={"SYN1": status},
        calibration_backtests={"SYN1": changed},
    )[0]
    refreshed_status = _bound_calibration_status(changed)
    refreshed_row = build_cohort_readiness(
        FIXTURE_DIR,
        tickers=("SYN1",),
        as_of="2026-01-31T23:59:59Z",
        calibration_statuses={"SYN1": refreshed_status},
        calibration_backtests={"SYN1": changed},
    )[0]

    assert status.backtest_evidence_digest != refreshed_status.backtest_evidence_digest
    assert stale_row.probability_state == "awaiting_calibration_evidence"
    assert refreshed_row.probability_state == "calibrated"


def test_post_assessment_report_package_relabel_requires_fresh_pairing():
    report = replace(
        _backtest_report(),
        excluded_count=1,
        exclusion_reasons={"synthetic_test_exclusion": 1},
        excluded_events=("synthetic test exclusion A",),
    )
    status = _bound_calibration_status(report)
    relabelled = replace(
        report,
        excluded_events=("synthetic test exclusion B",),
    )

    stale_row = build_cohort_readiness(
        FIXTURE_DIR,
        tickers=("SYN1",),
        as_of="2026-01-31T23:59:59Z",
        calibration_statuses={"SYN1": status},
        calibration_backtests={"SYN1": relabelled},
    )[0]
    refreshed_status = _bound_calibration_status(relabelled)
    refreshed_row = build_cohort_readiness(
        FIXTURE_DIR,
        tickers=("SYN1",),
        as_of="2026-01-31T23:59:59Z",
        calibration_statuses={"SYN1": refreshed_status},
        calibration_backtests={"SYN1": relabelled},
    )[0]

    assert status.backtest_evidence_digest != refreshed_status.backtest_evidence_digest
    assert stale_row.probability_state == "awaiting_calibration_evidence"
    assert refreshed_row.probability_state == "calibrated"


@pytest.mark.parametrize(
    ("report_metric", "calibration_metric"),
    [("revenue", "eps"), ("eps", "revenue")],
)
def test_declared_calibration_metric_must_be_modeled_in_paired_backtest(
    report_metric,
    calibration_metric,
):
    report = _single_metric_backtest_report(report_metric)
    status = _bound_calibration_status(report, metric=calibration_metric)

    row = build_cohort_readiness(
        FIXTURE_DIR,
        tickers=("SYN1",),
        as_of="2026-01-31T23:59:59Z",
        calibration_statuses={"SYN1": status},
        calibration_backtests={"SYN1": report},
    )[0]

    assert row.probability_state == "awaiting_calibration_evidence"


@pytest.mark.parametrize("metric", ["revenue", "eps"])
def test_single_metric_backtest_can_calibrate_its_matching_outcome(metric):
    report = _single_metric_backtest_report(metric)
    status = _bound_calibration_status(report, metric=metric)

    row = build_cohort_readiness(
        FIXTURE_DIR,
        tickers=("SYN1",),
        as_of="2026-01-31T23:59:59Z",
        calibration_statuses={"SYN1": status},
        calibration_backtests={"SYN1": report},
    )[0]

    assert row.probability_state == "calibrated"


def test_backtest_event_classification_must_match_forecast_interval_and_consensus():
    report = _backtest_report()
    contradictory = replace(
        report,
        directional_accuracy=0.5,
        events=tuple(
            replace(event, relative_classification="aligned")
            for event in report.events
        ),
    )
    status = _bound_calibration_status(contradictory)

    row = build_cohort_readiness(
        FIXTURE_DIR,
        tickers=("SYN1",),
        as_of="2026-01-31T23:59:59Z",
        calibration_statuses={"SYN1": status},
        calibration_backtests={"SYN1": contradictory},
    )[0]

    assert row.probability_state == "awaiting_calibration_evidence"


def test_identityless_calibration_status_cannot_pair_with_same_count_backtest():
    status = assess_probability_calibration(
        [
            ProbabilityObservation(
                probability=0.9 if index % 2 == 0 else 0.1,
                outcome=index % 2 == 0,
            )
            for index in range(100)
        ]
    )

    row = build_cohort_readiness(
        FIXTURE_DIR,
        tickers=("SYN1",),
        as_of="2026-01-31T23:59:59Z",
        calibration_statuses={"SYN1": status},
        calibration_backtests={"SYN1": _backtest_report()},
    )[0]

    assert status.probability_available is True
    assert status.evidence_digest is None
    assert row.probability_state == "awaiting_calibration_evidence"


def test_mathematically_impossible_brier_summary_fails_closed():
    report = _backtest_report()
    status = replace(_bound_calibration_status(report), brier_score=0.001)

    row = build_cohort_readiness(
        FIXTURE_DIR,
        tickers=("SYN1",),
        as_of="2026-01-31T23:59:59Z",
        calibration_statuses={"SYN1": status},
        calibration_backtests={"SYN1": report},
    )[0]

    assert row.probability_state == "awaiting_calibration_evidence"


@pytest.mark.parametrize(
    "mutate_status",
    [
        pytest.param(
            lambda report, status: replace(status, evidence_digest="0" * 64),
            id="mutated-evidence-digest",
        ),
        pytest.param(
            lambda report, status: replace(
                status,
                backtest_evidence_digest="0" * 64,
            ),
            id="mutated-backtest-evidence-digest",
        ),
        pytest.param(
            lambda report, status: _bound_calibration_status(
                report,
                identity_prefix="UNRELATED-",
            ),
            id="unrelated-identities-with-same-count",
        ),
        pytest.param(
            lambda report, status: _bound_calibration_status(
                report,
                as_of_timestamp="2026-01-31T23:58:59Z",
            ),
            id="mismatched-event-cutoff-with-same-count",
        ),
        pytest.param(
            lambda report, status: _bound_calibration_status(
                report,
                invert_outcomes=True,
            ),
            id="outcomes-contradict-matched-events",
        ),
        pytest.param(
            lambda report, status: replace(
                status,
                observations=(
                    status.observations[0],
                    status.observations[0],
                    *status.observations[2:],
                ),
            ),
            id="duplicate-observation-identity",
        ),
        pytest.param(
            lambda report, status: replace(
                status,
                observations=tuple(
                    replace(
                        observation,
                        probability=0.8 if observation.outcome else 0.1,
                    )
                    for observation in status.observations
                ),
            ),
            id="changed-probabilities-with-stale-summary-and-digest",
        ),
        pytest.param(
            lambda report, status: replace(
                status,
                observations=_reassess_with_true_probability(
                    status,
                    0.8,
                    report,
                ).observations,
                evidence_digest=_reassess_with_true_probability(
                    status,
                    0.8,
                    report,
                ).evidence_digest,
            ),
            id="changed-probabilities-with-only-refreshed-digest",
        ),
    ],
)
def test_calibration_evidence_must_match_exact_backtest_cohort(mutate_status):
    report = _backtest_report()
    status = _bound_calibration_status(report)

    row = build_cohort_readiness(
        FIXTURE_DIR,
        tickers=("SYN1",),
        as_of="2026-01-31T23:59:59Z",
        calibration_statuses={"SYN1": mutate_status(report, status)},
        calibration_backtests={"SYN1": report},
    )[0]

    assert row.probability_state == "awaiting_calibration_evidence"


def test_reassessed_probability_evidence_can_pair_after_digest_and_metrics_refresh():
    report = _backtest_report()
    original = _bound_calibration_status(report)
    reassessed = _reassess_with_true_probability(original, 0.8, report)

    row = build_cohort_readiness(
        FIXTURE_DIR,
        tickers=("SYN1",),
        as_of="2026-01-31T23:59:59Z",
        calibration_statuses={"SYN1": reassessed},
        calibration_backtests={"SYN1": report},
    )[0]

    assert reassessed.brier_score != original.brier_score
    assert reassessed.evidence_digest != original.evidence_digest
    assert row.probability_state == "calibrated"


def test_real_walk_forward_report_can_establish_calibrated_state():
    quarter_rows = (
        ("2024-Q1", "2024-03-31", "2024-04-20T21:00:00Z", 80.0, 0.60),
        ("2024-Q2", "2024-06-30", "2024-07-20T21:00:00Z", 84.0, 0.65),
        ("2024-Q3", "2024-09-30", "2024-10-20T21:00:00Z", 88.0, 0.70),
        ("2024-Q4", "2024-12-31", "2025-01-20T21:00:00Z", 92.0, 0.75),
        ("2025-Q1", "2025-03-31", "2025-04-20T21:00:00Z", 96.0, 0.80),
        ("2025-Q2", "2025-06-30", "2025-07-20T21:00:00Z", 100.0, 0.85),
        ("2025-Q3", "2025-09-30", "2025-10-20T21:00:00Z", 104.0, 0.90),
        ("2025-Q4", "2025-12-31", "2026-01-20T21:00:00Z", 108.0, 0.95),
        ("2026-Q1", "2026-03-31", "2026-04-20T21:00:00Z", 112.0, 1.00),
    )
    actuals = []
    snapshots = []
    for index in range(100):
        ticker = f"BT{index:03d}"
        actuals.extend(
            QuarterlyActual(
                ticker=ticker,
                fiscal_period=period,
                period_end_date=period_end,
                reported_at=reported_at,
                revenue_actual=revenue,
                eps_actual=eps,
                source="synthetic_test_fixture",
                source_ref=f"fixture://actual/{ticker}/{period}",
                retrieved_at=reported_at,
            )
            for period, period_end, reported_at, revenue, eps in quarter_rows
        )
        snapshots.append(
            ConsensusSnapshot(
                ticker=ticker,
                fiscal_period="2026-Q1",
                snapshot_at="2026-01-31T23:59:59Z",
                revenue_consensus=110.0 if index % 2 == 0 else 114.0,
                eps_consensus=0.98,
                source="synthetic_test_fixture",
                source_ref=f"fixture://consensus/{ticker}/2026-Q1",
                retrieved_at="2026-01-31T23:59:59Z",
            )
        )
    report = walk_forward_backtest(
        actuals,
        snapshots,
        minimum_backtest_events=100,
    )
    status = _bound_calibration_status(report)

    row = build_cohort_readiness(
        FIXTURE_DIR,
        tickers=("SYN1",),
        as_of="2026-01-31T23:59:59Z",
        calibration_statuses={"SYN1": status},
        calibration_backtests={"SYN1": report},
    )[0]

    assert report.verdict == "passed"
    assert report.event_count == 100
    assert len({observation.event_identity for observation in status.observations}) == 100
    assert {event.relative_classification for event in report.events} == {"aligned"}
    assert row.probability_state == "calibrated"


def test_failed_calibration_status_keeps_probability_awaiting_despite_event_count():
    status = assess_probability_calibration(
        [
            ProbabilityObservation(probability=0.6, outcome=index % 2 == 0)
            for index in range(100)
        ]
    )

    row = build_cohort_readiness(
        FIXTURE_DIR,
        tickers=("SYN1",),
        as_of="2026-01-31T23:59:59Z",
        calibration_counts={"SYN1": 100},
        calibration_statuses={"SYN1": status},
        calibration_backtests={"SYN1": _backtest_report()},
    )[0]

    assert status.failed_gates
    assert status.probability_available is False
    assert row.calibration_event_count == 100
    assert row.probability_state == "awaiting_calibration_evidence"


def test_unrecognized_calibration_evidence_fails_closed_without_losing_count_display():
    row = build_cohort_readiness(
        FIXTURE_DIR,
        tickers=("SYN1",),
        as_of="2026-01-31T23:59:59Z",
        calibration_counts={"SYN1": 100},
        calibration_statuses={"SYN1": object()},
    )[0]

    assert row.calibration_event_count == 100
    assert row.probability_state == "awaiting_calibration_evidence"


@pytest.mark.parametrize(
    "mutate",
    [
        lambda status: replace(status, event_count=99),
        lambda status: replace(status, brier_score=0.50),
        lambda status: replace(status, benchmark_brier_score=0.005),
        lambda status: replace(
            status,
            calibration_bins=(
                replace(status.calibration_bins[0], meets_minimum_size=False),
                *status.calibration_bins[1:],
            ),
        ),
        lambda status: replace(status, failed_gates=("point_in_time_leakage",)),
        lambda status: replace(status, probability_available=False),
    ],
)
def test_internally_inconsistent_calibration_status_fails_closed(mutate):
    verified = assess_probability_calibration(
        [
            ProbabilityObservation(
                probability=0.9 if index % 2 == 0 else 0.1,
                outcome=index % 2 == 0,
            )
            for index in range(100)
        ]
    )

    row = build_cohort_readiness(
        FIXTURE_DIR,
        tickers=("SYN1",),
        as_of="2026-01-31T23:59:59Z",
        calibration_counts={"SYN1": 100},
        calibration_statuses={"SYN1": mutate(verified)},
        calibration_backtests={"SYN1": _backtest_report()},
    )[0]

    assert row.calibration_event_count == 100
    assert row.probability_state == "awaiting_calibration_evidence"


@pytest.mark.parametrize(
    "mutate",
    [
        pytest.param(
            lambda status: replace(status, brier_score="not-a-number"),
            id="nonnumeric-brier-score",
        ),
        pytest.param(
            lambda status: replace(status, calibration_error=0.50),
            id="inconsistent-calibration-error",
        ),
        pytest.param(
            lambda status: replace(status, benchmark_brier_score=0.20),
            id="inconsistent-constant-rate-benchmark",
        ),
        pytest.param(
            lambda status: replace(
                status,
                calibration_bins=(
                    replace(status.calibration_bins[0], mean_probability="not-a-number"),
                    *status.calibration_bins[1:],
                ),
            ),
            id="nonnumeric-bin-field",
        ),
        pytest.param(
            lambda status: replace(
                status,
                calibration_error=0.30,
                calibration_bins=(
                    replace(status.calibration_bins[0], mean_probability=0.50),
                    *status.calibration_bins[1:],
                ),
            ),
            id="mean-probability-outside-declared-bin",
        ),
        pytest.param(
            lambda status: replace(
                status,
                benchmark_brier_score=0.505 * 0.495,
                calibration_error=0.095,
                calibration_bins=(
                    replace(status.calibration_bins[0], outcome_rate=0.01),
                    *status.calibration_bins[1:],
                ),
            ),
            id="fractional-boolean-outcome-count",
        ),
    ],
)
def test_calibration_status_semantic_contradictions_fail_closed_without_exceptions(mutate):
    verified = assess_probability_calibration(
        [
            ProbabilityObservation(
                probability=0.9 if index % 2 == 0 else 0.1,
                outcome=index % 2 == 0,
            )
            for index in range(100)
        ]
    )

    row = build_cohort_readiness(
        FIXTURE_DIR,
        tickers=("SYN1",),
        as_of="2026-01-31T23:59:59Z",
        calibration_statuses={"SYN1": mutate(verified)},
        calibration_backtests={"SYN1": _backtest_report()},
    )[0]

    assert row.probability_state == "awaiting_calibration_evidence"


@pytest.mark.parametrize(
    "report",
    [
        _backtest_report(leakage_failures=("post_cutoff_evidence",)),
        _backtest_report(benchmark_failures=("revenue_model_did_not_improve_consensus",)),
        _backtest_report(failures=("Point-in-time leakage detected",)),
        _backtest_report(verdict="failed"),
    ],
)
def test_failed_or_leaky_backtest_report_cannot_promote_probability_state(report):
    status = _bound_calibration_status(report)

    row = build_cohort_readiness(
        FIXTURE_DIR,
        tickers=("SYN1",),
        as_of="2026-01-31T23:59:59Z",
        calibration_statuses={"SYN1": status},
        calibration_backtests={"SYN1": report},
    )[0]

    assert row.probability_state == "awaiting_calibration_evidence"


def test_calibration_and_backtest_event_count_mismatch_fails_closed():
    status = _bound_calibration_status()

    row = build_cohort_readiness(
        FIXTURE_DIR,
        tickers=("SYN1",),
        as_of="2026-01-31T23:59:59Z",
        calibration_statuses={"SYN1": status},
        calibration_backtests={"SYN1": _backtest_report(valid_event_count=101)},
    )[0]

    assert row.probability_state == "awaiting_calibration_evidence"


@pytest.mark.parametrize(
    "counts",
    [
        {"calibration_counts": {"SYN1": 99}},
        {"backtest_counts": {"SYN1": 99}},
    ],
)
def test_explicit_raw_count_mismatch_with_verified_evidence_fails_closed(counts):
    status = _bound_calibration_status()

    row = build_cohort_readiness(
        FIXTURE_DIR,
        tickers=("SYN1",),
        as_of="2026-01-31T23:59:59Z",
        calibration_statuses={"SYN1": status},
        calibration_backtests={"SYN1": _backtest_report()},
        **counts,
    )[0]

    assert row.probability_state == "awaiting_calibration_evidence"


@pytest.mark.parametrize(
    "mutate_report",
    [
        lambda report: replace(report, events=()),
        lambda report: replace(
            report,
            events=(report.events[0], report.events[0], *report.events[2:]),
        ),
        lambda report: replace(
            report,
            events=(
                replace(report.events[0], latest_input_timestamp="2026-02-01T00:00:00Z"),
                *report.events[1:],
            ),
        ),
        lambda report: replace(
            report,
            events=(
                replace(report.events[0], target_reported_at="2026-01-31T23:59:59Z"),
                *report.events[1:],
            ),
        ),
    ],
)
def test_structurally_inconsistent_backtest_report_fails_closed(mutate_report):
    status = _bound_calibration_status()

    row = build_cohort_readiness(
        FIXTURE_DIR,
        tickers=("SYN1",),
        as_of="2026-01-31T23:59:59Z",
        calibration_statuses={"SYN1": status},
        calibration_backtests={"SYN1": mutate_report(_backtest_report())},
    )[0]

    assert row.probability_state == "awaiting_calibration_evidence"


@pytest.mark.parametrize(
    "mutate_report",
    [
        pytest.param(
            lambda report: replace(report, benchmark_metrics={}),
            id="empty-benchmark-metrics",
        ),
        pytest.param(
            lambda report: replace(
                report,
                revenue_mae=999.0,
                benchmark_metrics={
                    **report.benchmark_metrics,
                    "consensus_revenue_mae": 1.0,
                },
            ),
            id="contradictory-model-mae-999-versus-consensus-1",
        ),
        pytest.param(
            lambda report: replace(
                report,
                revenue_mae=2.0,
                revenue_median_absolute_error=2.0,
                revenue_wape=2.0 / 101.0,
                events=tuple(
                    replace(event, revenue_forecast=103.0)
                    for event in report.events
                ),
            ),
            id="event-derived-model-does-not-improve-consensus",
        ),
        pytest.param(
            lambda report: replace(report, valid_event_count="not-a-number"),
            id="nonnumeric-report-count",
        ),
        pytest.param(
            lambda report: replace(
                report,
                events=(
                    replace(report.events[0], revenue_forecast="not-a-number"),
                    *report.events[1:],
                ),
            ),
            id="nonnumeric-event-metric",
        ),
    ],
)
def test_backtest_metric_and_benchmark_contradictions_fail_closed_without_exceptions(
    mutate_report,
):
    status = _bound_calibration_status()

    row = build_cohort_readiness(
        FIXTURE_DIR,
        tickers=("SYN1",),
        as_of="2026-01-31T23:59:59Z",
        calibration_statuses={"SYN1": status},
        calibration_backtests={"SYN1": mutate_report(_backtest_report())},
    )[0]

    assert row.probability_state == "awaiting_calibration_evidence"


def test_cohort_cannot_ignore_post_cutoff_retrieval_rejected_by_onboarding(tmp_path):
    input_dir = tmp_path / "earnings_nowcast"
    shutil.copytree(FIXTURE_DIR, input_dir)
    actuals_path = input_dir / "quarterly_actuals.csv"
    with actuals_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    base = next(row for row in rows if row["ticker"] == "SYN1" and row["fiscal_period"] == "2025-Q4")
    rows.append(
        {
            **base,
            "source_ref": "fixture://actual/SYN1/2025-Q4/post-cutoff-retrieval",
            "retrieved_at": "2026-02-01T00:00:00Z",
        }
    )
    with actuals_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    row = build_cohort_readiness(
        input_dir,
        tickers=("SYN1",),
        as_of="2026-01-31T23:59:59Z",
    )[0]

    assert row.state == "blocked"
    assert row.revenue_ready is False
    assert row.eps_ready is False
    assert "post_cutoff_evidence" in row.blocker


@pytest.mark.parametrize(
    ("filename", "identity_field", "identity_value"),
    [
        ("quarterly_actuals.csv", "fiscal_period", "2025-Q4"),
        ("consensus_snapshots.csv", "fiscal_period", "2026-Q1"),
    ],
)
def test_malformed_row_cannot_hide_post_cutoff_retrieval_from_cohort(
    tmp_path,
    filename,
    identity_field,
    identity_value,
):
    input_dir = tmp_path / "earnings_nowcast"
    shutil.copytree(FIXTURE_DIR, input_dir)
    path = input_dir / filename
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    base = next(
        row
        for row in rows
        if row["ticker"] == "SYN1" and row[identity_field] == identity_value
    )
    rows.append(
        {
            **base,
            "source_ref": f"fixture://malformed/{filename}",
            "retrieved_at": "2026-02-01T00:00:00Z",
            "revenue_unit_scale": "not-a-number",
        }
    )
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    row = build_cohort_readiness(
        input_dir,
        tickers=("SYN1",),
        as_of="2026-01-31T23:59:59Z",
    )[0]

    assert row.state == "blocked"
    assert row.revenue_ready is False
    assert row.eps_ready is False
    assert "post_cutoff_evidence" in row.blocker
