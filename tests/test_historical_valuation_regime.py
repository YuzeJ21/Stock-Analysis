from dataclasses import replace

from src.historical_valuation_regime import ValuationObservation, build_valuation_regime
from src.commercial_source_rights import SourceRights


def _registry(*supported_fields: str):
    return {
        "reviewed_local_evidence": SourceRights(
            "reviewed_local_evidence", "Reviewed", "evidence", "approved",
            "derived_only", "reviewed", "required", "n/a", "none", "reviewed",
            supported_fields, 1,
        )
    }


def _observation(index: int, **overrides) -> ValuationObservation:
    month = index + 1
    values = {
        "ticker": "NVDA",
        "metric": "price_to_fcf_per_share",
        "numerator": 20.0 + index,
        "denominator": 1.0,
        "numerator_as_of": f"2025-{month:02d}-28T21:00:00Z",
        "denominator_period_end": "2024-12-31",
        "denominator_available_at": "2025-01-20T21:00:00Z",
        "definition_id": "trailing_fcf_per_share_v1",
        "source": "reviewed_local_evidence",
        "source_ref": f"evidence://valuation/{index}",
        "retrieved_at": f"2025-{month:02d}-28T21:01:00Z",
    }
    values.update(overrides)
    return ValuationObservation(**values)


def test_regime_uses_only_aligned_point_in_time_observations():
    packet = build_valuation_regime(
        tuple(_observation(index) for index in range(8)),
        ticker="NVDA",
        metric="price_to_fcf_per_share",
        as_of="2025-09-01T00:00:00Z",
    )

    assert packet.state == "ready"
    assert packet.observation_count == 8
    assert packet.latest_multiple == 27.0
    assert packet.percentile_rank == 100.0
    assert packet.segment_count == 1
    assert "descriptive" in packet.boundary


def test_regime_rejects_current_denominator_backfilled_over_older_prices():
    invalid = _observation(
        0,
        numerator_as_of="2024-12-31T21:00:00Z",
        denominator_available_at="2025-01-20T21:00:00Z",
    )
    packet = build_valuation_regime(
        (invalid,),
        ticker="NVDA",
        metric="price_to_fcf_per_share",
        as_of="2025-09-01T00:00:00Z",
    )

    assert packet.state == "insufficient_history"
    assert packet.observation_count == 0
    assert packet.rejected_count == 1
    assert "not public at the price timestamp" in packet.rejected_reasons[0]


def test_definition_change_splits_history_and_does_not_mix_regimes():
    rows = tuple(_observation(index) for index in range(4)) + tuple(
        replace(
            _observation(index + 4),
            definition_id="forward_fcf_per_share_v2",
            denominator_period_end="2025-03-31",
            denominator_available_at="2025-04-20T21:00:00Z",
        )
        for index in range(4)
    )
    packet = build_valuation_regime(
        rows,
        ticker="NVDA",
        metric="price_to_fcf_per_share",
        as_of="2025-09-01T00:00:00Z",
    )

    assert packet.segment_count == 2
    assert packet.state == "insufficient_history"
    assert packet.observation_count == 4
    assert packet.definition_id == "forward_fcf_per_share_v2"


def test_commercial_valuation_requires_exact_source_lane_scope():
    rows = tuple(_observation(index) for index in range(8))

    blocked = build_valuation_regime(
        rows,
        ticker="NVDA",
        metric="price_to_fcf_per_share",
        as_of="2025-09-01T00:00:00Z",
        commercial_mode=True,
        rights_registry=_registry("revenue"),
    )
    ready = build_valuation_regime(
        rows,
        ticker="NVDA",
        metric="price_to_fcf_per_share",
        as_of="2025-09-01T00:00:00Z",
        commercial_mode=True,
        rights_registry=_registry("valuation_history"),
    )

    assert blocked.state == "commercial_evidence_blocked"
    assert blocked.observation_count == 0
    assert blocked.commercial_blocker_count == 8
    assert "valuation_history" in blocked.commercial_blockers[0]
    assert ready.state == "ready"
    assert ready.observation_count == 8
