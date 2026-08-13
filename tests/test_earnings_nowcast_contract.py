from __future__ import annotations

from dataclasses import fields
from datetime import timezone

import pytest

from src.earnings_nowcast_contract import (
    ConsensusSnapshot,
    EvidenceSignal,
    ForecastSnapshot,
    FreshnessState,
    NowcastState,
    QuarterlyActual,
    SignalDirection,
    SignalReviewState,
    input_snapshot_hash,
    parse_utc_timestamp,
)


def _actual(
    period: str = "2025-Q4",
    *,
    reported_at: str = "2026-01-20T21:00:00Z",
    retrieved_at: str | None = None,
) -> QuarterlyActual:
    return QuarterlyActual(
        ticker=" syn1 ",
        fiscal_period=period,
        period_end_date="2025-12-31",
        reported_at=reported_at,
        revenue_actual=100.0,
        eps_actual=1.0,
        source="synthetic_test_fixture",
        source_ref=f"fixture://actual/{period}",
        retrieved_at=retrieved_at or reported_at,
    )


def _consensus(
    *,
    snapshot_at: str = "2026-01-15T12:00:00Z",
    retrieved_at: str | None = None,
) -> ConsensusSnapshot:
    return ConsensusSnapshot(
        ticker="SYN1",
        fiscal_period="2026-Q1",
        snapshot_at=snapshot_at,
        revenue_consensus=110.0,
        eps_consensus=1.1,
        source="synthetic_test_fixture",
        retrieved_at=retrieved_at or snapshot_at,
    )


def test_contract_normalizes_identity_and_utc_timestamps():
    actual = _actual()

    assert actual.ticker == "SYN1"
    assert actual.fiscal_period == "2025-Q4"
    assert actual.reported_at == "2026-01-20T21:00:00+00:00"
    assert parse_utc_timestamp("2026-01-20T16:00:00-05:00").tzinfo == timezone.utc


def test_contract_rejects_evidence_published_after_cutoff():
    actual = _actual(reported_at="2026-02-01T21:00:00Z")

    with pytest.raises(ValueError, match="quarterly actual timestamp .* after forecast cutoff"):
        actual.available_at("2026-01-31T23:59:59Z")


@pytest.mark.parametrize(
    "evidence",
    [
        _actual(retrieved_at="2026-02-01T00:00:00Z"),
        _consensus(retrieved_at="2026-02-01T00:00:00Z"),
    ],
)
def test_contract_rejects_evidence_retrieved_after_cutoff(evidence):
    with pytest.raises(ValueError, match="retrieval timestamp .* after forecast cutoff"):
        evidence.available_at("2026-01-31T23:59:59Z")


def test_contract_requires_publication_or_snapshot_not_after_retrieval():
    with pytest.raises(ValueError, match="reported_at cannot be after retrieved_at"):
        _actual(
            reported_at="2026-01-20T21:00:00Z",
            retrieved_at="2026-01-20T20:59:59Z",
        )

    with pytest.raises(ValueError, match="snapshot_at cannot be after retrieved_at"):
        _consensus(
            snapshot_at="2026-01-15T12:00:00Z",
            retrieved_at="2026-01-15T11:59:59Z",
        )


def test_contract_rejects_naive_timestamps_and_invalid_periods():
    with pytest.raises(ValueError, match="timezone-aware"):
        _consensus(snapshot_at="2026-01-15T12:00:00")

    with pytest.raises(ValueError, match=r"YYYY-Q\[1-4\]"):
        _actual(period="FY2025")


def test_contract_rejects_non_finite_or_missing_numeric_evidence():
    with pytest.raises(ValueError, match="finite"):
        ConsensusSnapshot(
            ticker="SYN1",
            fiscal_period="2026-Q1",
            snapshot_at="2026-01-15T12:00:00Z",
            revenue_consensus=float("nan"),
            eps_consensus=1.1,
            source="synthetic_test_fixture",
            retrieved_at="2026-01-15T12:01:00Z",
        )

    with pytest.raises(ValueError, match="at least one consensus metric"):
        ConsensusSnapshot(
            ticker="SYN1",
            fiscal_period="2026-Q1",
            snapshot_at="2026-01-15T12:00:00Z",
            revenue_consensus=None,
            eps_consensus=None,
            source="synthetic_test_fixture",
            retrieved_at="2026-01-15T12:01:00Z",
        )


def test_input_snapshot_hash_is_deterministic_and_order_independent():
    actual = _actual()
    consensus = _consensus()

    assert input_snapshot_hash([actual, consensus]) == input_snapshot_hash([consensus, actual])
    assert len(input_snapshot_hash([actual, consensus])) == 64


def test_evidence_signal_is_directional_and_has_no_numeric_impact_field():
    signal = EvidenceSignal(
        signal_id="SIG-1",
        target_ticker="SYN1",
        source_ticker="SYN2",
        fiscal_period="2026-Q1",
        as_of_timestamp="2026-01-31T23:59:59Z",
        signal_type="peer_demand_readthrough",
        direction=SignalDirection.POSITIVE,
        affected_metric="revenue",
        confidence_band="medium",
        evidence_source="synthetic_test_fixture",
        evidence_published_at="2026-01-25T21:00:00Z",
        evidence_excerpt_hash="a" * 64,
        peer_relationship_state="trusted_peer_ready",
        review_state=SignalReviewState.SUPPORTED,
    )

    assert signal.direction == SignalDirection.POSITIVE
    assert "estimated_impact_bps" not in {field.name for field in fields(EvidenceSignal)}
    assert "numeric_adjustment" not in {field.name for field in fields(EvidenceSignal)}


def test_evidence_signal_rejects_publication_after_its_as_of_timestamp():
    with pytest.raises(ValueError, match="evidence signal timestamp .* after forecast cutoff"):
        EvidenceSignal(
            signal_id="SIG-2",
            target_ticker="SYN1",
            source_ticker="SYN2",
            fiscal_period="2026-Q1",
            as_of_timestamp="2026-01-20T00:00:00Z",
            signal_type="peer_demand_readthrough",
            direction="positive",
            affected_metric="revenue",
            confidence_band="medium",
            evidence_source="synthetic_test_fixture",
            evidence_published_at="2026-01-21T00:00:00Z",
            evidence_excerpt_hash="b" * 64,
            peer_relationship_state="trusted_peer_ready",
            review_state="supported",
        )


def test_forecast_snapshot_rejects_invalid_ranges_and_has_no_probability_field():
    with pytest.raises(ValueError, match="revenue range"):
        ForecastSnapshot(
            forecast_id="FC-1",
            ticker="SYN1",
            fiscal_period="2026-Q1",
            as_of_timestamp="2026-01-31T23:59:59Z",
            model_version="deterministic-v1",
            input_snapshot_hash="c" * 64,
            revenue_midpoint=105.0,
            revenue_low=110.0,
            revenue_high=100.0,
            eps_midpoint=1.1,
            eps_low=1.0,
            eps_high=1.2,
            consensus_revenue=104.0,
            consensus_eps=1.0,
            revenue_gap_pct=0.01,
            eps_gap_pct=0.10,
            relative_classification="aligned",
            confidence_band="medium",
            readiness_state=NowcastState.BASELINE_READY,
            freshness_state=FreshnessState.CURRENT,
            source_ids=("fixture://actual/2025-Q4",),
            created_at="2026-01-31T23:59:59Z",
        )

    assert "beat_probability" not in {field.name for field in fields(ForecastSnapshot)}
    assert "miss_probability" not in {field.name for field in fields(ForecastSnapshot)}
