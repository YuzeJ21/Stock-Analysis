from __future__ import annotations

from dataclasses import replace

import pytest

from src.earnings_nowcast_contract import ConsensusSnapshot, FreshnessState, NowcastState, QuarterlyActual
from src.earnings_nowcast_readiness import assess_nowcast_readiness, readiness_payload


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


def _consensus(
    *,
    period: str = "2026-Q1",
    snapshot_at: str = "2026-01-20T12:00:00Z",
    revenue: float | None = 104.0,
    eps: float | None = 1.2,
) -> ConsensusSnapshot:
    return ConsensusSnapshot(
        ticker="SYN1",
        fiscal_period=period,
        snapshot_at=snapshot_at,
        revenue_consensus=revenue,
        eps_consensus=eps,
        source="synthetic_test_fixture",
        retrieved_at=snapshot_at,
    )


def test_generic_optional_context_does_not_unlock_nowcast():
    result = assess_nowcast_readiness(
        ticker="SYN1",
        fiscal_period="2026-Q1",
        as_of_timestamp=CUTOFF,
        actuals=[],
        consensus=[],
    )

    assert result.state == NowcastState.BLOCKED
    assert "quarterly_actual_history" in result.missing_evidence
    assert "point_in_time_consensus" in result.missing_evidence
    assert result.revenue_ready is False
    assert result.eps_ready is False


def test_source_backed_history_and_exact_period_consensus_unlock_baseline():
    result = assess_nowcast_readiness(
        ticker="syn1",
        fiscal_period="2026-Q1",
        as_of_timestamp=CUTOFF,
        actuals=_actuals(),
        consensus=[_consensus()],
    )

    assert result.state == NowcastState.BASELINE_READY
    assert result.revenue_ready is True
    assert result.eps_ready is True
    assert result.consensus_ready is True
    assert result.freshness_state == FreshnessState.CURRENT
    assert len(result.source_ids) == 6
    assert result.missing_evidence == ()


def test_revenue_can_be_ready_while_unstable_eps_is_withheld():
    result = assess_nowcast_readiness(
        ticker="SYN1",
        fiscal_period="2026-Q1",
        as_of_timestamp=CUTOFF,
        actuals=_actuals(eps_values=(0.8, -2.0, 3.5, -4.0, 6.0)),
        consensus=[_consensus()],
    )

    assert result.state == NowcastState.BASELINE_READY
    assert result.revenue_ready is True
    assert result.eps_ready is False
    assert "stable_eps_history" in result.missing_evidence


def test_metric_requires_matching_consensus_value():
    result = assess_nowcast_readiness(
        ticker="SYN1",
        fiscal_period="2026-Q1",
        as_of_timestamp=CUTOFF,
        actuals=_actuals(),
        consensus=[_consensus(eps=None)],
    )

    assert result.revenue_ready is True
    assert result.eps_ready is False
    assert "eps_consensus" in result.missing_evidence


def test_mismatched_period_consensus_does_not_unlock_target_period():
    result = assess_nowcast_readiness(
        ticker="SYN1",
        fiscal_period="2026-Q1",
        as_of_timestamp=CUTOFF,
        actuals=_actuals(),
        consensus=[_consensus(period="2026-Q2")],
    )

    assert result.state == NowcastState.BLOCKED
    assert "point_in_time_consensus" in result.missing_evidence


def test_post_cutoff_evidence_fails_closed_even_when_earlier_rows_exist():
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

    result = assess_nowcast_readiness(
        ticker="SYN1",
        fiscal_period="2026-Q1",
        as_of_timestamp=CUTOFF,
        actuals=rows,
        consensus=[_consensus()],
    )

    assert result.state == NowcastState.BLOCKED
    assert "post_cutoff_evidence" in result.missing_evidence


def test_old_consensus_is_stale_and_blocks_current_nowcast():
    result = assess_nowcast_readiness(
        ticker="SYN1",
        fiscal_period="2026-Q1",
        as_of_timestamp=CUTOFF,
        actuals=_actuals(),
        consensus=[_consensus(snapshot_at="2025-08-01T12:00:00Z")],
        current_after_days=45,
        stale_after_days=90,
    )

    assert result.state == NowcastState.BLOCKED
    assert result.freshness_state == FreshnessState.STALE_OR_UNKNOWN
    assert "current_consensus" in result.missing_evidence


def test_non_company_instrument_is_excluded():
    result = assess_nowcast_readiness(
        ticker="SYN1",
        fiscal_period="2026-Q1",
        as_of_timestamp=CUTOFF,
        actuals=_actuals(),
        consensus=[_consensus()],
        asset_type="etf",
    )

    assert result.state == NowcastState.EXCLUDED
    assert result.next_action == "No company earnings nowcast applies to this instrument."


def test_readiness_payload_contains_no_forecast_or_probability_values():
    payload = readiness_payload(
        assess_nowcast_readiness(
            ticker="SYN1",
            fiscal_period="2026-Q1",
            as_of_timestamp=CUTOFF,
            actuals=_actuals(),
            consensus=[_consensus()],
        )
    )

    assert payload["state"] == "baseline_ready"
    assert "revenue_midpoint" not in payload
    assert "eps_midpoint" not in payload
    assert "beat_probability" not in payload


def test_duplicate_fiscal_period_does_not_satisfy_minimum_history():
    rows = _actuals()[:4]
    rows.append(replace(rows[-1], source_ref="fixture://duplicate/2025-Q3"))

    result = assess_nowcast_readiness(
        ticker="SYN1",
        fiscal_period="2026-Q1",
        as_of_timestamp=CUTOFF,
        actuals=rows,
        consensus=[_consensus()],
    )

    assert result.revenue_ready is False
    assert result.eps_ready is False
    assert "quarterly_actual_history" in result.missing_evidence


def test_conflicting_quarterly_revenue_blocks_only_revenue():
    rows = _actuals()
    rows.append(
        replace(
            rows[-1],
            revenue_actual=999.0,
            eps_actual=None,
            source="second_source",
            source_ref="fixture://conflict/2025-Q4",
        )
    )

    result = assess_nowcast_readiness(
        ticker="SYN1",
        fiscal_period="2026-Q1",
        as_of_timestamp=CUTOFF,
        actuals=rows,
        consensus=[_consensus()],
    )

    assert result.revenue_ready is False
    assert result.eps_ready is True
    assert "conflicting_quarterly_revenue" in result.missing_evidence
    assert "fixture://actual/2025-Q4" in result.conflict_source_ids
    assert "fixture://conflict/2025-Q4" in result.conflict_source_ids


def test_explicit_pre_cutoff_revision_supersedes_prior_value():
    rows = _actuals()
    rows.append(
        replace(
            rows[-1],
            reported_at="2026-01-16T21:00:00Z",
            retrieved_at="2026-01-16T21:01:00Z",
            revenue_actual=102.0,
            eps_actual=1.25,
            source_ref="fixture://revision/2025-Q4",
            supersedes_source_ref=rows[-1].source_ref,
        )
    )

    result = assess_nowcast_readiness(
        ticker="SYN1",
        fiscal_period="2026-Q1",
        as_of_timestamp=CUTOFF,
        actuals=rows,
        consensus=[_consensus()],
    )

    assert result.revenue_ready is True
    assert result.eps_ready is True
    assert "conflicting_quarterly_actuals" not in result.missing_evidence


def test_revision_cannot_hide_a_second_unresolved_conflicting_source():
    rows = _actuals()
    original = rows[-1]
    rows.append(replace(original, revenue_actual=109.0, source_ref="fixture://conflict/one"))
    rows.append(
        replace(
            original,
            reported_at="2026-01-17T21:00:00Z",
            retrieved_at="2026-01-17T21:01:00Z",
            revenue_actual=110.0,
            source_ref="fixture://revision/latest",
            supersedes_source_ref=original.source_ref,
        )
    )

    result = assess_nowcast_readiness(
        ticker="SYN1",
        fiscal_period="2026-Q1",
        as_of_timestamp=CUTOFF,
        actuals=rows,
        consensus=[_consensus()],
    )

    assert result.revenue_ready is False
    assert "conflicting_quarterly_revenue" in result.missing_evidence
    assert "fixture://conflict/one" in result.conflict_source_ids


def test_incompatible_revenue_currency_withholds_only_revenue():
    rows = [replace(row, revenue_currency="EUR") for row in _actuals()]

    result = assess_nowcast_readiness(
        ticker="SYN1",
        fiscal_period="2026-Q1",
        as_of_timestamp=CUTOFF,
        actuals=rows,
        consensus=[_consensus()],
    )

    assert result.revenue_ready is False
    assert result.eps_ready is True
    assert "incompatible_revenue_definition" in result.missing_evidence


@pytest.mark.parametrize(
    ("field", "value", "ready_metric", "blocked_metric", "reason"),
    [
        ("revenue_unit_scale", 1_000_000.0, "eps_ready", "revenue_ready", "incompatible_revenue_definition"),
        ("eps_basis", "adjusted", "revenue_ready", "eps_ready", "incompatible_eps_definition"),
        ("eps_share_basis", "basic", "revenue_ready", "eps_ready", "incompatible_eps_definition"),
        ("split_adjustment_basis", "split_adjusted", "revenue_ready", "eps_ready", "incompatible_eps_definition"),
    ],
)
def test_incompatible_metric_definitions_fail_only_the_affected_metric(
    field: str,
    value: object,
    ready_metric: str,
    blocked_metric: str,
    reason: str,
):
    rows = [replace(row, **{field: value}) for row in _actuals()]

    result = assess_nowcast_readiness(
        ticker="SYN1",
        fiscal_period="2026-Q1",
        as_of_timestamp=CUTOFF,
        actuals=rows,
        consensus=[_consensus()],
    )

    assert getattr(result, ready_metric) is True
    assert getattr(result, blocked_metric) is False
    assert reason in result.missing_evidence
