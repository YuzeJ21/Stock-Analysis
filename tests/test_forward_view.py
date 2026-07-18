from types import SimpleNamespace

from src.forward_view import build_forward_view, forward_view_cards, forward_view_rows
from src.quarterly_business_trend import build_quarterly_trend_packet
from src.earnings_nowcast_contract import QuarterlyActual


def _actual(period: str, revenue: float, eps: float) -> QuarterlyActual:
    return QuarterlyActual(
        ticker="AAA",
        fiscal_period=period,
        period_end_date=f"{period[:4]}-{int(period[-1]) * 3:02d}-28",
        reported_at=f"{period[:4]}-12-31T00:00:00Z",
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


def _ready_trend():
    return build_quarterly_trend_packet(
        "AAA",
        (
            _actual("2024-Q1", 100, 1.0),
            _actual("2024-Q4", 130, 1.3),
            _actual("2025-Q1", 150, 1.5),
        ),
    )


def _report():
    return {
        "ticker": "AAA",
        "generated_at": "2026-07-17T00:00:00Z",
        "valuation_readiness": {"dcf_ready": True, "peer_ready": True},
        "valuation_snapshot": {
            "status": "calculated",
            "source_metadata": [
                {"source": "sec_companyfacts", "source_ref": "sec:AAA", "as_of_date": "2026-06-30"}
            ],
            "scenarios": [
                {"name": "bear", "dcf_result": {"status": "calculated", "fair_value_per_share": 70.0}, "assumptions": {"wacc": 0.11}},
                {"name": "base", "dcf_result": {"status": "calculated", "fair_value_per_share": 90.0}, "assumptions": {"wacc": 0.09}},
                {"name": "bull", "dcf_result": {"status": "calculated", "fair_value_per_share": 115.0}, "assumptions": {"wacc": 0.08}},
            ],
        },
    }


def _entry(summary: str):
    return SimpleNamespace(summary=summary, source="reviewed_journal", source_ref=f"journal:{summary}")


def test_forward_view_composes_verified_trend_scenarios_peers_and_reviewed_thesis():
    journal = SimpleNamespace(
        catalysts=(_entry("Product cycle"),),
        risks=(_entry("Customer concentration"),),
        invalidation_conditions=(_entry("Revenue contracts year over year"),),
    )
    peer_map = SimpleNamespace(status="ready", trusted_count=2, candidate_count=1, reviewable_count=1, boundary="Context only")

    packet = build_forward_view(
        _report(),
        _ready_trend(),
        journal_state=journal,
        peer_map=peer_map,
        nowcast_packet=None,
        freshness_state="current",
    )

    assert packet.status == "partial"
    assert packet.historical_trend.state == "usable_now"
    assert packet.valuation_scenarios.state == "usable_now"
    assert [row["name"] for row in packet.valuation_scenarios.details] == ["bear", "base", "bull"]
    assert packet.peer_context.state == "usable_now"
    assert packet.thesis_context.state == "usable_now"
    assert packet.earnings_outlook.state == "blocked"
    assert "earnings_outlook" in packet.withheld_fields
    assert packet.next_research_task == "Add exact-period point-in-time consensus before reviewing an Earnings Outlook range."


def test_forward_view_fails_closed_when_provenance_or_inputs_are_missing():
    report = _report()
    report["valuation_snapshot"]["source_metadata"] = []

    packet = build_forward_view(report, build_quarterly_trend_packet("AAA", []), freshness_state="stale")

    assert packet.historical_trend.state == "blocked"
    assert packet.valuation_scenarios.state == "blocked"
    assert packet.peer_context.state == "blocked"
    assert packet.thesis_context.state == "blocked"
    assert packet.source_cutoff == "2026-07-17T00:00:00Z"
    assert "stale" in packet.boundary.lower()
    rendered = str(forward_view_cards(packet)).lower()
    assert "fair value" not in rendered
    assert "probability" not in rendered


def test_candidate_peer_context_never_becomes_trusted_or_changes_scenarios():
    peer_map = SimpleNamespace(status="candidate_context_only", trusted_count=0, candidate_count=3, reviewable_count=0, boundary="Candidates only")
    packet = build_forward_view(_report(), _ready_trend(), peer_map=peer_map)

    assert packet.peer_context.state == "candidate_context_only"
    assert "not trusted" in packet.peer_context.boundary.lower()
    assert len(packet.valuation_scenarios.details) == 3


def test_nowcast_probability_stays_withheld_until_calibrated():
    uncalibrated = {
        "readiness": {"state": "baseline_ready"},
        "forecast": {"revenue_low": 100, "revenue_high": 110, "eps_low": 1.0, "eps_high": 1.2},
        "calibration": {"eligible": False},
    }
    packet = build_forward_view(_report(), _ready_trend(), nowcast_packet=uncalibrated)

    assert packet.earnings_outlook.state == "usable_now"
    assert "probability withheld" in packet.earnings_outlook.boundary.lower()
    assert all("probability" not in str(detail).lower() for detail in packet.earnings_outlook.details)


def test_forward_view_rows_keep_technical_details_separate_and_research_only():
    packet = build_forward_view(_report(), _ready_trend())
    rows = forward_view_rows(packet)
    cards = forward_view_cards(packet)

    assert [row["Section"] for row in rows] == [
        "Historical Trend",
        "Valuation Scenarios",
        "Trusted Peer Context",
        "Reviewer Thesis Context",
        "Earnings Outlook",
    ]
    assert cards[-1]["kicker"] == "NEXT RESEARCH TASK"
    rendered = str(cards).lower()
    for prohibited in ("buy now", "sell now", "position size", "will rise", "recommendation score"):
        assert prohibited not in rendered
