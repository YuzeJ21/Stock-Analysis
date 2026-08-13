from __future__ import annotations

from dataclasses import replace

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


def test_walk_forward_event_cutoff_includes_consensus_retrieval_time():
    snapshot = replace(
        _consensus()[0],
        snapshot_at="2026-01-31T23:58:59Z",
        retrieved_at="2026-01-31T23:59:59Z",
    )

    report = walk_forward_backtest(_history_with_target(), [snapshot], NowcastConfig())

    assert report.valid_event_count == 1
    assert report.events[0].as_of_timestamp == "2026-01-31T23:59:59+00:00"
    assert report.events[0].latest_input_timestamp == "2026-01-31T23:59:59+00:00"


def test_walk_forward_event_carries_exact_forecast_binding_metadata():
    config = NowcastConfig(model_version="deterministic-test-v2")

    report = walk_forward_backtest(_history_with_target(), _consensus(), config)

    event = report.events[0]
    assert event.model_version == "deterministic-test-v2"
    assert len(event.input_snapshot_hash or "") == 64
    assert set(event.input_snapshot_hash or "") <= set("0123456789abcdef")


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"model_version": None}, "model_version is required"),
        ({"input_snapshot_hash": None}, "input_snapshot_hash must be"),
    ],
)
def test_report_binding_requires_explicit_event_metadata(changes, message):
    report = walk_forward_backtest(_history_with_target(), _consensus(), NowcastConfig())
    incomplete = replace(
        report,
        events=(replace(report.events[0], **changes),),
    )

    with pytest.raises(ValueError, match=message):
        assess_probability_calibration((), backtest_report=incomplete)


def test_walk_forward_reports_errors_benchmarks_and_interval_coverage():
    report = walk_forward_backtest(_history_with_target(), _consensus(), NowcastConfig())

    assert report.verdict == "insufficient"
    assert report.revenue_mae is not None
    assert report.revenue_wape is not None
    assert report.eps_mae is not None
    assert report.interval_coverage in {0.0, 1.0}
    assert report.revenue_interval_coverage in {0.0, 1.0}
    assert report.eps_interval_coverage in {0.0, 1.0}
    assert report.joint_interval_coverage in {0.0, 1.0}
    assert set(report.benchmark_metrics) >= {
        "consensus_revenue_mae",
        "prior_year_revenue_mae",
        "consensus_eps_mae",
        "prior_year_eps_mae",
    }
    assert any(failure.startswith("minimum_backtest_events") for failure in report.failures)


def test_probability_is_withheld_below_100_out_of_sample_events():
    observations = [ProbabilityObservation(probability=0.6, outcome=index % 2 == 0) for index in range(99)]

    status = assess_probability_calibration(observations)

    assert status.state == NowcastState.BACKTEST_INSUFFICIENT
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
    assert status.state == NowcastState.BACKTEST_INSUFFICIENT
    assert "no_probability_evidence" in status.failed_gates
    assert status.observations == ()
    assert status.outcome_definition is None
    assert status.evidence_digest is None


def test_invalid_probability_is_rejected():
    with pytest.raises(ValueError, match="between 0 and 1"):
        ProbabilityObservation(probability=1.1, outcome=True)


def test_probability_observation_requires_a_boolean_outcome():
    with pytest.raises(ValueError, match="outcome must be Boolean"):
        ProbabilityObservation(probability=0.1, outcome="false")


def test_identityless_probability_observations_remain_standalone_calibration_evidence():
    observations = tuple(
        ProbabilityObservation(
            probability=0.9 if index % 2 == 0 else 0.1,
            outcome=index % 2 == 0,
        )
        for index in range(100)
    )

    status = assess_probability_calibration(observations)

    assert status.probability_available is True
    assert status.observations == observations
    assert status.outcome_definition is None
    assert status.evidence_digest is None


def test_bound_probability_observations_are_canonical_immutable_evidence():
    observations = tuple(
        ProbabilityObservation(
            probability=0.9 if index % 2 == 0 else 0.1,
            outcome=index % 2 == 0,
            ticker=f"syn{index:03d}",
            fiscal_period="2026-q1",
            as_of_timestamp="2026-01-31T18:59:59-05:00",
            outcome_definition="revenue_actual_strictly_above_consensus",
        )
        for index in reversed(range(100))
    )

    status = assess_probability_calibration(observations)
    reordered = assess_probability_calibration(tuple(reversed(observations)))

    assert status.observations[0].ticker == "SYN000"
    assert status.observations[0].fiscal_period == "2026-Q1"
    assert status.observations[0].as_of_timestamp == "2026-01-31T23:59:59+00:00"
    assert status.outcome_definition == "revenue_actual_strictly_above_consensus"
    assert len(status.evidence_digest or "") == 64
    assert status.evidence_digest == reordered.evidence_digest
    assert status.observations == reordered.observations


def test_calibration_assessment_can_bind_exact_backtest_event_evidence():
    report = walk_forward_backtest(_history_with_target(), _consensus(), NowcastConfig())
    event = report.events[0]
    observations = (
        ProbabilityObservation(
            probability=0.9,
            outcome=bool(event.revenue_actual > event.consensus_revenue),
            ticker=event.ticker,
            fiscal_period=event.fiscal_period,
            as_of_timestamp=event.as_of_timestamp,
            outcome_definition="revenue_actual_strictly_above_consensus",
        ),
    )

    standalone = assess_probability_calibration(observations)
    bound = assess_probability_calibration(observations, backtest_report=report)

    assert standalone.backtest_evidence_digest is None
    assert len(bound.backtest_evidence_digest or "") == 64
    assert bound.observations == standalone.observations
    assert bound.brier_score == standalone.brier_score


def test_backtest_binding_normalizes_equivalent_chronology_representations():
    report = walk_forward_backtest(_history_with_target(), _consensus(), NowcastConfig())
    event = report.events[0]
    observations = (
        ProbabilityObservation(
            probability=0.9,
            outcome=bool(event.revenue_actual > event.consensus_revenue),
            ticker=event.ticker,
            fiscal_period=event.fiscal_period,
            as_of_timestamp=event.as_of_timestamp,
            outcome_definition="revenue_actual_strictly_above_consensus",
        ),
    )
    equivalent = replace(
        report,
        events=(
            replace(
                event,
                as_of_timestamp="2026-01-31T18:59:59-05:00",
                latest_input_timestamp="2026-01-31T18:59:59-05:00",
                target_reported_at="2026-04-20T17:00:00-04:00",
            ),
        ),
    )

    original = assess_probability_calibration(observations, backtest_report=report)
    normalized = assess_probability_calibration(observations, backtest_report=equivalent)

    assert normalized.backtest_evidence_digest == original.backtest_evidence_digest


def test_backtest_binding_includes_the_exact_report_package():
    report = walk_forward_backtest(_history_with_target(), _consensus(), NowcastConfig())
    event = report.events[0]
    observations = (
        ProbabilityObservation(
            probability=0.9,
            outcome=bool(event.revenue_actual > event.consensus_revenue),
            ticker=event.ticker,
            fiscal_period=event.fiscal_period,
            as_of_timestamp=event.as_of_timestamp,
            outcome_definition="revenue_actual_strictly_above_consensus",
        ),
    )
    relabelled = replace(
        report,
        excluded_count=1,
        exclusion_reasons={"synthetic_test_exclusion": 1},
        excluded_events=("synthetic test exclusion",),
    )

    original = assess_probability_calibration(observations, backtest_report=report)
    changed = assess_probability_calibration(observations, backtest_report=relabelled)

    assert changed.backtest_evidence_digest != original.backtest_evidence_digest


def test_partially_bound_probability_observation_is_rejected():
    with pytest.raises(ValueError, match="bound observation fields must be provided together"):
        ProbabilityObservation(
            probability=0.9,
            outcome=True,
            ticker="SYN1",
        )


def test_bound_probability_observation_identities_must_be_unique():
    observation = ProbabilityObservation(
        probability=0.9,
        outcome=True,
        ticker="SYN1",
        fiscal_period="2026-Q1",
        as_of_timestamp="2026-01-31T23:59:59Z",
        outcome_definition="revenue_actual_strictly_above_consensus",
    )

    with pytest.raises(ValueError, match="identities must be unique"):
        assess_probability_calibration((observation, observation))


def test_bound_probability_observations_require_one_outcome_definition():
    revenue = ProbabilityObservation(
        probability=0.9,
        outcome=True,
        ticker="SYN1",
        fiscal_period="2026-Q1",
        as_of_timestamp="2026-01-31T23:59:59Z",
        outcome_definition="revenue_actual_strictly_above_consensus",
    )
    eps = ProbabilityObservation(
        probability=0.1,
        outcome=False,
        ticker="SYN2",
        fiscal_period="2026-Q1",
        as_of_timestamp="2026-01-31T23:59:59Z",
        outcome_definition="eps_actual_strictly_above_consensus",
    )

    with pytest.raises(ValueError, match="one outcome definition"):
        assess_probability_calibration((revenue, eps))


def test_empty_backtest_evidence_fails_closed():
    report = walk_forward_backtest([], [], NowcastConfig())

    assert report.verdict == "failed"
    assert "No valid out-of-sample events" in report.failures


def test_backtest_reports_silent_missing_consensus_exclusions_by_reason():
    report = walk_forward_backtest(_history_with_target(), _consensus(), NowcastConfig())

    assert report.valid_event_count == 1
    assert report.excluded_count == 8
    assert report.exclusion_reasons["no_pre_report_consensus_snapshot"] == 8
    assert len(report.excluded_events) == 8


def test_backtest_reports_model_validation_exclusions_separately():
    target = _actual("2024-Q1", "2024-03-31", "2024-04-20T21:00:00Z", 80.0, 0.60)
    snapshot = ConsensusSnapshot(
        ticker="SYN1",
        fiscal_period="2024-Q1",
        snapshot_at="2024-04-01T12:00:00Z",
        revenue_consensus=79.0,
        eps_consensus=0.58,
        source="synthetic_test_fixture",
        retrieved_at="2024-04-01T12:00:00Z",
    )

    report = walk_forward_backtest([target], [snapshot], NowcastConfig())

    assert report.event_count == 0
    assert report.exclusion_reasons["model_input_validation_failed"] == 1
    assert "quarterly_actual_history" in report.excluded_events[0]


def test_calibration_reports_each_bin_and_human_readable_failed_gate_details():
    observations = [ProbabilityObservation(probability=0.6, outcome=index % 2 == 0) for index in range(20)]

    status = assess_probability_calibration(observations)

    assert status.calibration_bins[0].event_count == 20
    assert status.calibration_bins[0].meets_minimum_size is True
    assert status.failed_gate_details["minimum_100_events"].startswith("20 valid events")
    assert status.failed_gate_details["must_improve_constant_rate_benchmark"]


def test_post_report_retrieval_is_reported_as_leakage_and_excluded():
    snapshots = [
        replace(
            _consensus()[0],
            retrieved_at="2026-04-21T00:00:00Z",
        )
    ]

    report = walk_forward_backtest(_history_with_target(), snapshots, NowcastConfig())

    assert report.verdict == "failed"
    assert report.valid_event_count == 0
    assert report.leakage_failures
    assert "retrieved after target report" in report.leakage_failures[0]


def test_conflicting_same_timestamp_consensus_revisions_are_excluded():
    original = _consensus()[0]
    conflicting = replace(original, source_ref="fixture://revision", revenue_consensus=999.0)

    report = walk_forward_backtest(
        _history_with_target(),
        [original, conflicting],
        NowcastConfig(),
    )

    assert report.valid_event_count == 0
    assert report.exclusion_reasons["ambiguous_consensus_revision"] == 1


def test_stale_consensus_snapshot_is_excluded_by_explicit_age_policy():
    stale = replace(
        _consensus()[0],
        snapshot_at="2025-12-01T00:00:00Z",
        retrieved_at="2025-12-01T00:01:00Z",
    )

    report = walk_forward_backtest(
        _history_with_target(),
        [stale],
        NowcastConfig(),
        maximum_snapshot_age_days=90,
    )

    assert report.valid_event_count == 0
    assert report.exclusion_reasons["stale_consensus_snapshot"] == 1


def test_benchmark_non_improvement_is_an_explicit_failed_gate():
    perfect_consensus = replace(_consensus()[0], revenue_consensus=112.0, eps_consensus=1.0)

    report = walk_forward_backtest(
        _history_with_target(),
        [perfect_consensus],
        NowcastConfig(),
        minimum_backtest_events=1,
    )

    assert report.verdict == "failed"
    assert "revenue_model_did_not_improve_consensus" in report.benchmark_failures
    assert "eps_model_did_not_improve_consensus" in report.benchmark_failures


def test_backtest_withholds_unverified_target_and_prior_year_eps_outcomes():
    rows = _history_with_target()
    rows[-1] = replace(
        rows[-1], split_adjustment_basis="companyfacts_split_basis_unverified"
    )
    rows[4] = replace(
        rows[4], split_adjustment_basis="companyfacts_split_basis_unverified"
    )

    report = walk_forward_backtest(rows, _consensus(), NowcastConfig())
    event = report.events[0]

    assert event.revenue_actual == 112.0
    assert event.eps_actual is None
    assert event.prior_year_eps is None
    assert report.revenue_mae is not None
    assert report.eps_mae is None
    assert "consensus_eps_mae" not in report.benchmark_metrics
    assert "prior_year_eps_mae" not in report.benchmark_metrics


def test_backtest_excludes_eps_only_target_when_split_basis_is_unverified():
    rows = _history_with_target()
    rows[-1] = replace(
        rows[-1],
        revenue_actual=None,
        split_adjustment_basis="companyfacts_split_basis_unverified",
    )

    report = walk_forward_backtest(rows, _consensus(), NowcastConfig())

    assert report.event_count == 0
    assert report.exclusion_reasons["no_comparable_target_actual"] == 1


def test_identical_target_duplicates_produce_one_fiscal_period_event():
    rows = _history_with_target()
    rows.append(replace(rows[-1]))

    report = walk_forward_backtest(rows, [_consensus()[0]], NowcastConfig())

    assert report.event_count == 1
    assert tuple(event.fiscal_period for event in report.events) == ("2026-Q1",)


@pytest.mark.parametrize(
    ("conflicting_field", "conflicting_value", "expected_revenue", "expected_eps"),
    [
        ("revenue_actual", 999.0, None, 1.0),
        ("eps_actual", 9.99, 112.0, None),
    ],
)
def test_conflicting_target_metric_is_excluded_independently(
    conflicting_field,
    conflicting_value,
    expected_revenue,
    expected_eps,
):
    rows = _history_with_target()
    target = rows[-1]
    other_field = "eps_actual" if conflicting_field == "revenue_actual" else "revenue_actual"
    conflict = replace(
        target,
        **{
            conflicting_field: conflicting_value,
            other_field: None,
            "source_ref": f"fixture://conflict/{conflicting_field}",
        },
    )

    report = walk_forward_backtest([*rows, conflict], [_consensus()[0]], NowcastConfig())

    assert report.event_count == 1
    assert report.events[0].revenue_actual == expected_revenue
    assert report.events[0].eps_actual == expected_eps


def test_explicit_target_revision_chains_select_each_metric_canonically():
    rows = _history_with_target()
    target = rows[-1]
    revenue_revision = replace(
        target,
        revenue_actual=120.0,
        eps_actual=None,
        source_ref="fixture://revision/2026-Q1/revenue",
        retrieved_at="2026-04-20T22:00:00Z",
        supersedes_source_ref=target.source_ref,
    )
    eps_revision = replace(
        target,
        revenue_actual=None,
        eps_actual=1.2,
        source_ref="fixture://revision/2026-Q1/eps",
        retrieved_at="2026-04-20T23:00:00Z",
        supersedes_source_ref=target.source_ref,
    )

    report = walk_forward_backtest(
        [*rows, revenue_revision, eps_revision],
        [_consensus()[0]],
        NowcastConfig(),
    )

    assert report.event_count == 1
    assert report.events[0].revenue_actual == 120.0
    assert report.events[0].eps_actual == 1.2


def test_prior_year_benchmarks_use_canonical_revisions_in_any_input_order():
    rows = _history_with_target()
    prior = rows[4]
    revision = replace(
        prior,
        revenue_actual=125.0,
        eps_actual=1.25,
        source_ref="fixture://revision/2025-Q1",
        reported_at="2025-04-21T21:00:00Z",
        retrieved_at="2025-04-21T21:01:00Z",
        supersedes_source_ref=prior.source_ref,
    )

    appended = walk_forward_backtest([*rows, revision], [_consensus()[0]], NowcastConfig())
    prepended = walk_forward_backtest([revision, *rows], [_consensus()[0]], NowcastConfig())

    assert appended.events[0].prior_year_revenue == 125.0
    assert appended.events[0].prior_year_eps == 1.25
    assert prepended.events[0].prior_year_revenue == 125.0
    assert prepended.events[0].prior_year_eps == 1.25


def test_prior_year_benchmark_excludes_revision_reported_after_event_cutoff():
    rows = _history_with_target()
    prior = rows[4]
    future_revision = replace(
        prior,
        revenue_actual=125.0,
        eps_actual=1.25,
        source_ref="fixture://revision/2025-Q1/future",
        reported_at="2026-02-01T21:00:00Z",
        retrieved_at="2026-02-01T21:01:00Z",
        supersedes_source_ref=prior.source_ref,
    )

    report = walk_forward_backtest(
        [*rows, future_revision],
        [_consensus()[0]],
        NowcastConfig(),
    )

    assert report.events[0].as_of_timestamp == "2026-01-31T23:59:59+00:00"
    assert report.events[0].prior_year_revenue == 96.0
    assert report.events[0].prior_year_eps == 0.8
    assert report.leakage_failures == ()
