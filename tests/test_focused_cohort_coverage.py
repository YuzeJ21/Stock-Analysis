import pandas as pd
import pytest

from src.commercial_source_rights import build_source_rights_registry
from src.focused_cohort_coverage import (
    COHORT_COVERAGE_LANES,
    build_focused_cohort_coverage,
    derive_cohort_evidence,
    focused_cohort_coverage_frame,
)
from src.focused_research_cohort import build_focused_cohort
from src.quarterly_business_trend import build_quarterly_trend_packet
from src.earnings_nowcast_contract import QuarterlyActual


def _actual(period: str, revenue: float, eps: float) -> QuarterlyActual:
    year, quarter = period.split("-Q")
    return QuarterlyActual(
        ticker="AAA",
        fiscal_period=period,
        period_end_date=f"{year}-{int(quarter) * 3:02d}-28",
        reported_at=f"{int(year) + (1 if quarter == '4' else 0)}-02-01T00:00:00Z",
        revenue_actual=revenue,
        eps_actual=eps,
        source="reviewed_fixture",
        source_ref=f"fixture:{period}",
        retrieved_at="2026-07-17T00:00:00Z",
        revenue_currency="USD",
        revenue_unit_scale=1.0,
        revenue_basis="gaap",
        eps_currency="USD",
        eps_basis="gaap_diluted",
        eps_share_basis="diluted",
        eps_operations_basis="continuing",
        split_adjustment_basis="as_reported",
    )


def _cohort():
    readiness = pd.DataFrame(
        [
            {
                "ticker": "AAA",
                "price_ready": True,
                "fundamentals_ready": True,
                "dcf_ready": True,
                "peer_ready": False,
            }
        ]
    )
    universe = pd.DataFrame(
        [
            {
                "ticker": "AAA",
                "name": "Alpha Co",
                "asset_type": "company",
                "is_active_listing": True,
            }
        ]
    )
    return build_focused_cohort(readiness, universe, target_size=1, minimum_size=1), readiness


def _rights_registry(*supported_fields: str):
    return build_source_rights_registry(
        [
            {
                "source_id": "licensed_source",
                "display_name": "Licensed fixture source",
                "permitted_use": "reviewed_research",
                "commercial_use": "approved",
                "redistribution": "derived_data_only",
                "storage_limits": "reviewed rows only",
                "attribution": "source reference required",
                "rate_limits": "fixture only",
                "authentication": "fixture only",
                "expected_freshness": "fixture timestamp",
                "supported_fields": list(supported_fields),
                "fallback_priority": 1,
            }
        ]
    )


def test_coverage_matrix_reports_each_required_lane_without_padding_missing_evidence():
    cohort, readiness = _cohort()
    actuals = (
        _actual("2024-Q1", 100, 1.0),
        _actual("2024-Q4", 130, 1.3),
        _actual("2025-Q1", 150, 1.5),
    )
    packet = build_quarterly_trend_packet("AAA", actuals)

    coverage = build_focused_cohort_coverage(
        cohort,
        readiness,
        quarterly_packets={"AAA": packet},
        evidence_by_ticker={
            "AAA": {
                "margin_state": "partial",
                "free_cash_flow_state": "blocked",
                "cash_debt_state": "usable_now",
                "shares_state": "usable_now",
                "trusted_peers_state": "candidate_context_only",
                "filing_dates_state": "usable_now",
                "earnings_dates_state": "blocked",
                "point_in_time_consensus_state": "blocked",
            }
        },
    )

    assert coverage.status == "partial"
    assert coverage.company_count == 1
    assert tuple(item.lane for item in coverage.rows) == COHORT_COVERAGE_LANES
    states = {item.lane: item.state for item in coverage.rows}
    assert states == {
        "adjusted_daily_price_history": "usable_now",
        "quarterly_revenue": "usable_now",
        "quarterly_eps": "usable_now",
        "margins": "partial",
        "free_cash_flow": "blocked",
        "cash_and_debt": "usable_now",
        "shares_outstanding": "usable_now",
        "trusted_peers": "candidate_context_only",
        "filing_dates": "usable_now",
        "earnings_dates": "blocked",
        "point_in_time_consensus": "blocked",
    }


def test_missing_evidence_is_blocked_and_non_company_is_excluded():
    cohort, readiness = _cohort()
    coverage = build_focused_cohort_coverage(cohort, readiness)
    states = {item.lane: item.state for item in coverage.rows}
    assert states["adjusted_daily_price_history"] == "usable_now"
    assert states["quarterly_revenue"] == "blocked"
    assert states["trusted_peers"] == "blocked"

    excluded = build_focused_cohort_coverage(
        cohort,
        readiness,
        evidence_by_ticker={"AAA": {"asset_type": "etf"}},
    )
    assert {item.state for item in excluded.rows} == {"excluded"}


def test_candidate_context_cannot_be_promoted_to_usable_and_invalid_states_fail():
    cohort, readiness = _cohort()
    coverage = build_focused_cohort_coverage(
        cohort,
        readiness,
        evidence_by_ticker={"AAA": {"trusted_peers_state": "candidate_context_only"}},
    )
    peer = next(item for item in coverage.rows if item.lane == "trusted_peers")
    assert peer.state == "candidate_context_only"
    assert "not trusted" in peer.boundary.lower()

    with pytest.raises(ValueError, match="unsupported coverage state"):
        build_focused_cohort_coverage(
            cohort,
            readiness,
            evidence_by_ticker={"AAA": {"margin_state": "ready_enough"}},
        )


def test_coverage_frame_is_stable_and_contains_no_recommendation_language():
    cohort, readiness = _cohort()
    coverage = build_focused_cohort_coverage(cohort, readiness)
    frame = focused_cohort_coverage_frame(coverage)

    assert frame.columns.tolist() == ["Ticker", "Company", "Lane", "State", "Evidence", "Boundary"]
    assert len(frame) == len(COHORT_COVERAGE_LANES)
    rendered = frame.to_string(index=False).lower()
    for prohibited in ("buy", "sell", "winner", "expected return", "recommendation score"):
        assert prohibited not in rendered


def test_coverage_rejects_cohorts_over_commercial_beta_cap():
    cohort, readiness = _cohort()
    oversized = cohort.__class__(
        status="ready",
        requested_size=50,
        minimum_size=1,
        eligible_count=51,
        members=cohort.members * 51,
        message="invalid",
    )
    with pytest.raises(ValueError, match="cannot exceed 50"):
        build_focused_cohort_coverage(oversized, readiness)


def test_derive_cohort_evidence_requires_values_and_source_provenance():
    fundamentals = pd.DataFrame(
        [
            {
                "ticker": "AAA",
                "source": "sec_companyfacts",
                "free_cash_flow": 10.0,
                "operating_margin": 0.2,
                "cash": 50.0,
                "debt": 20.0,
                "shares_outstanding": 100.0,
                "sec_filed_date": "2026-05-01",
            },
            {
                "ticker": "BBB",
                "source": "",
                "free_cash_flow": 99.0,
                "cash": 10.0,
                "debt": 2.0,
                "shares_outstanding": 200.0,
            },
        ]
    )
    readiness = pd.DataFrame(
        [
            {"ticker": "AAA", "peer_ready": True},
            {"ticker": "BBB", "peer_ready": False},
        ]
    )
    universe = pd.DataFrame(
        [
            {"ticker": "AAA", "asset_type": "company"},
            {"ticker": "BBB", "asset_type": "company"},
        ]
    )
    consensus = pd.DataFrame(
        [
            {
                "ticker": "AAA",
                "fiscal_period": "2026-Q2",
                "source": "licensed_consensus",
                "source_ref": "consensus:AAA:2026-Q2",
                "snapshot_at": "2026-07-01T00:00:00Z",
                "revenue_consensus": 100.0,
            }
        ]
    )
    earnings = pd.DataFrame(
        [
            {
                "ticker": "AAA",
                "source": "sec_companyfacts",
                "source_ref": "earnings:AAA",
                "next_earnings_date": "2026-08-15",
            }
        ]
    )

    evidence = derive_cohort_evidence(
        ("AAA", "BBB"),
        fundamentals=fundamentals,
        readiness=readiness,
        universe=universe,
        consensus=consensus,
        earnings=earnings,
        as_of="2026-07-17T00:00:00Z",
    )

    assert evidence["AAA"]["free_cash_flow_state"] == "usable_now"
    assert evidence["AAA"]["margin_state"] == "usable_now"
    assert evidence["AAA"]["cash_debt_state"] == "usable_now"
    assert evidence["AAA"]["shares_state"] == "usable_now"
    assert evidence["AAA"]["trusted_peers_state"] == "usable_now"
    assert evidence["AAA"]["filing_dates_state"] == "usable_now"
    assert evidence["AAA"]["point_in_time_consensus_state"] == "usable_now"
    assert evidence["AAA"]["earnings_dates_state"] == "usable_now"
    assert evidence["BBB"]["free_cash_flow_state"] == "blocked"
    assert evidence["BBB"]["shares_state"] == "blocked"


def test_consensus_after_cutoff_and_unverified_commercial_sources_fail_closed():
    consensus = pd.DataFrame(
        [
            {
                "ticker": "AAA",
                "fiscal_period": "2026-Q2",
                "source": "yfinance",
                "source_ref": "provider:AAA",
                "snapshot_at": "2026-07-18T00:00:00Z",
            }
        ]
    )
    fundamentals = pd.DataFrame(
        [{"ticker": "AAA", "source": "yfinance", "source_ref": "provider:AAA", "shares_outstanding": 100}]
    )

    cutoff = derive_cohort_evidence(
        ("AAA",),
        consensus=consensus,
        as_of="2026-07-17T00:00:00Z",
    )
    commercial = derive_cohort_evidence(
        ("AAA",),
        fundamentals=fundamentals,
        consensus=consensus.assign(snapshot_at="2026-07-16T00:00:00Z"),
        as_of="2026-07-17T00:00:00Z",
        commercial_mode=True,
    )

    assert cutoff["AAA"]["point_in_time_consensus_state"] == "blocked"
    assert commercial["AAA"]["shares_state"] == "blocked"
    assert commercial["AAA"]["point_in_time_consensus_state"] == "blocked"


def test_checked_registry_does_not_reuse_sec_revenue_permission_for_unrelated_fields():
    fundamentals = pd.DataFrame(
        [
            {
                "ticker": "AAA",
                "source": "sec_companyfacts",
                "source_ref": "sec:AAA:10-Q",
                "operating_margin": 0.2,
                "free_cash_flow": 10.0,
                "cash": 50.0,
                "debt": 20.0,
                "shares_outstanding": 100.0,
                "sec_filed_date": "2026-05-01",
            }
        ]
    )

    evidence = derive_cohort_evidence(
        ("AAA",), fundamentals=fundamentals, commercial_mode=True
    )["AAA"]

    assert evidence["margin_state"] == "blocked"
    assert evidence["free_cash_flow_state"] == "blocked"
    assert evidence["cash_debt_state"] == "blocked"
    assert evidence["shares_state"] == "usable_now"
    assert evidence["filing_dates_state"] == "usable_now"
    assert "operating_margin" in evidence["margin_evidence"]
    assert "free_cash_flow" in evidence["free_cash_flow_evidence"]


def test_commercial_cash_and_debt_scope_remain_independent():
    fundamentals = pd.DataFrame(
        [
            {
                "ticker": "AAA",
                "source": "licensed_source",
                "source_ref": "licensed:AAA",
                "cash": 50.0,
                "debt": 20.0,
            }
        ]
    )

    cash_only = derive_cohort_evidence(
        ("AAA",),
        fundamentals=fundamentals,
        commercial_mode=True,
        rights_registry=_rights_registry("cash"),
    )["AAA"]
    both = derive_cohort_evidence(
        ("AAA",),
        fundamentals=fundamentals,
        commercial_mode=True,
        rights_registry=_rights_registry("cash", "debt"),
    )["AAA"]

    assert cash_only["cash_debt_state"] == "partial"
    assert "debt" in cash_only["cash_debt_evidence"]
    assert both["cash_debt_state"] == "usable_now"


def test_commercial_earnings_consensus_and_peer_fields_require_own_scope():
    readiness = pd.DataFrame([{"ticker": "AAA", "peer_ready": True}])
    earnings = pd.DataFrame(
        [
            {
                "ticker": "AAA",
                "source": "licensed_source",
                "source_ref": "licensed:earnings:AAA",
                "next_earnings_date": "2026-08-15",
            }
        ]
    )
    consensus = pd.DataFrame(
        [
            {
                "ticker": "AAA",
                "fiscal_period": "2026-Q2",
                "source": "licensed_source",
                "source_ref": "licensed:consensus:AAA",
                "snapshot_at": "2026-07-16T00:00:00Z",
                "revenue_consensus": 100.0,
                "eps_consensus": 1.0,
            }
        ]
    )
    peers = pd.DataFrame(
        [
            {
                "ticker": "AAA",
                "peer_ticker": "BBB",
                "source": "licensed_source",
                "source_ref": "licensed:peer:AAA:BBB",
            }
        ]
    )

    evidence = derive_cohort_evidence(
        ("AAA",),
        readiness=readiness,
        earnings=earnings,
        consensus=consensus,
        peers=peers,
        as_of="2026-07-17T00:00:00Z",
        commercial_mode=True,
        rights_registry=_rights_registry("revenue_consensus"),
    )["AAA"]

    assert evidence["earnings_dates_state"] == "blocked"
    assert evidence["point_in_time_consensus_state"] == "blocked"
    assert "eps_consensus" in evidence["point_in_time_consensus_evidence"]
    assert evidence["trusted_peers_state"] == "blocked"
    assert "trusted_peers" in evidence["trusted_peers_evidence"]


def test_commercial_consensus_requires_a_populated_metric_not_only_a_date():
    consensus = pd.DataFrame(
        [
            {
                "ticker": "AAA",
                "fiscal_period": "2026-Q2",
                "source": "licensed_source",
                "source_ref": "licensed:consensus:AAA",
                "snapshot_at": "2026-07-16T00:00:00Z",
            }
        ]
    )

    evidence = derive_cohort_evidence(
        ("AAA",),
        consensus=consensus,
        as_of="2026-07-17T00:00:00Z",
        commercial_mode=True,
        rights_registry=_rights_registry("revenue_consensus", "eps_consensus"),
    )["AAA"]

    assert evidence["point_in_time_consensus_state"] == "blocked"
    assert "value" in evidence["point_in_time_consensus_evidence"].lower()


def test_candidate_peer_rows_remain_candidate_context_only():
    candidates = pd.DataFrame(
        [
            {"ticker": "AAA", "peer_ticker": "BBB", "candidate_state": "candidate_context_only"},
            {"ticker": "AAA", "peer_ticker": "CCC", "candidate_state": "candidate_context_only"},
        ]
    )
    evidence = derive_cohort_evidence(("AAA",), peer_candidates=candidates)

    assert evidence["AAA"]["trusted_peers_state"] == "candidate_context_only"
    assert "not trusted" in evidence["AAA"]["trusted_peers_evidence"].lower()
