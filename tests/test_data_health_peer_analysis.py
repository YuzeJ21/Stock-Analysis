from __future__ import annotations

import pandas as pd

from src import data_health_peer_analysis as peer_analysis


def test_peer_analysis_boundary_cards_explain_trend_vs_valuation_boundaries():
    peer_readiness = pd.DataFrame(
        [
            {
                "ticker": "A",
                "peer_ready": False,
                "peer_blocker_type": "missing_peer_mapping",
                "peer_trend_comparison_ready": False,
                "peer_valuation_comparison_ready": False,
            },
            {
                "ticker": "META",
                "peer_ready": False,
                "peer_blocker_type": "peer_fundamentals_missing",
                "peer_trend_comparison_ready": True,
                "peer_valuation_comparison_ready": False,
            },
            {
                "ticker": "COHR",
                "peer_ready": False,
                "peer_blocker_type": "peer_price_missing",
                "peer_trend_comparison_ready": False,
                "peer_valuation_comparison_ready": False,
            },
            {
                "ticker": "NVDA",
                "peer_ready": True,
                "peer_blocker_type": "",
                "peer_trend_comparison_ready": True,
                "peer_valuation_comparison_ready": True,
            },
        ]
    )
    readiness = pd.DataFrame(
        [
            {"ticker": "A", "dcf_ready": True, "in_active_universe": False},
            {"ticker": "META", "dcf_ready": True, "in_active_universe": True},
            {"ticker": "COHR", "dcf_ready": False, "in_active_universe": True},
            {"ticker": "NVDA", "dcf_ready": True, "in_active_universe": True},
        ]
    )

    cards = peer_analysis.peer_analysis_boundary_cards(peer_readiness, readiness)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == [
        "WHAT PEERS CAN SUPPORT NOW",
        "WHAT IS STILL LOCKED",
        "DCF-READY BUT PEER-BLOCKED",
        "COPY NEXT",
        "PEER PROOF LADDER",
        "TRUSTED INPUT PATH",
    ]
    assert "2 trend-ready / 1 valuation-ready" in rendered
    assert "peer valuation is separate" in rendered
    assert "3 peer valuation row(s) locked" in rendered
    assert "missing mappings: 1" in rendered
    assert "peer price gaps: 1" in rendered
    assert "peer fundamentals gaps: 1" in rendered
    assert "2 company row(s)" in rendered
    assert "1 active-universe row(s) can have standalone dcf reviewed" in rendered
    assert "peer-relative valuation stays withheld" in rendered
    assert "trend-ready does not mean valuation-ready" in rendered
    assert "validate and preview trusted rows, apply only reviewed rows" in rendered
    assert "data/imports/peers.csv" in rendered
    assert "make focus-peers ticker=meta" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trading" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_peer_analysis_boundary_cards_handle_missing_report_without_fake_peer_counts():
    cards = peer_analysis.peer_analysis_boundary_cards(None)
    body = str(cards[0]["body"]).lower()

    assert len(cards) == 1
    assert cards[0]["title"] == "Peer readiness not loaded"
    assert cards[0]["command"] == "make readiness-preview TOP_N=20"
    assert "does not refresh or persist saved readiness" in body
    assert "missing peer output means peer analysis stays locked" in body
    assert "inspect peer readiness" in body
    assert "copy-only command" not in body
    assert "make " not in body


def test_peer_function_quality_frame_explains_trend_vs_valuation_and_provenance():
    peer_readiness = pd.DataFrame(
        [
            {
                "ticker": "A",
                "peer_ready": False,
                "peer_blocker_type": "missing_peer_mapping",
                "peer_trend_comparison_ready": False,
                "peer_valuation_comparison_ready": False,
                "peer_dcf_comparison_ready": False,
            },
            {
                "ticker": "META",
                "peer_ready": False,
                "peer_blocker_type": "peer_fundamentals_missing",
                "peer_trend_comparison_ready": True,
                "peer_valuation_comparison_ready": False,
                "peer_dcf_comparison_ready": False,
            },
            {
                "ticker": "NVDA",
                "peer_ready": True,
                "peer_blocker_type": "",
                "peer_trend_comparison_ready": True,
                "peer_valuation_comparison_ready": True,
                "peer_dcf_comparison_ready": True,
            },
            {
                "ticker": "COHR",
                "peer_ready": False,
                "peer_blocker_type": "peer_price_missing",
                "peer_trend_comparison_ready": False,
                "peer_valuation_comparison_ready": False,
                "peer_dcf_comparison_ready": False,
            },
        ]
    )
    worklist = pd.DataFrame([{"ticker": "A"}, {"ticker": "META"}])

    frame = peer_analysis.peer_function_quality_frame(peer_readiness, worklist)
    rendered = " ".join(frame.astype(str).to_numpy().flatten()).lower()

    assert list(frame.columns) == [
        "Peer Area",
        "Current Coverage",
        "Supported Today",
        "Not Supported Yet",
        "Methodology / Provenance",
        "Next Step",
    ]
    assert "source-backed mappings" in rendered
    assert "1 ticker(s) missing mappings; 2 unlock row(s) queued" in rendered
    assert "data/imports/peers.csv" in rendered
    assert "peer-selection rules stay in this repository" in rendered
    assert "peer trend comparison" in rendered
    assert "2 ticker(s) trend-ready" in rendered
    assert "peer-relative valuation or quality conclusions" in rendered
    assert "peer valuation comparison" in rendered
    assert "1 ticker(s) valuation-ready; 3 still blocked" in rendered
    assert "withheld, not inferred" in rendered
    assert "peer dcf comparison" in rendered
    assert "1 ticker(s) dcf-peer-ready" in rendered
    assert "peer data follow-through" in rendered
    assert "1 price-gap ticker(s); 1 fundamentals-gap ticker(s)" in rendered
    assert "sector or industry fallback" in rendered
    assert "dependencies" in rendered
