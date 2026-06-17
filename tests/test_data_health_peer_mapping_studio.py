from __future__ import annotations

import pandas as pd

from src import data_health_peer_mapping_studio as peer_mapping_studio


def test_peer_mapping_studio_summary_cards_are_actionable():
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
            {"ticker": "NVDA", "dcf_ready": True, "in_active_universe": True},
        ]
    )

    cards = peer_mapping_studio.peer_mapping_studio_summary_cards(peer_readiness, readiness)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert "dcf peer blockers" in rendered
    assert "2 tickers" in rendered
    assert "missing mappings" in rendered
    assert "active-universe affected: 0" in rendered
    assert "peer fundamentals" in rendered
    assert "valuation blocked" in rendered
    assert "make peer-mapping-queue top_n=25" in rendered
    assert "make templates" in rendered
    assert "make imports-validate" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_peer_mapping_studio_summary_cards_empty_state_uses_readiness_proof_copy():
    cards = peer_mapping_studio.peer_mapping_studio_summary_cards(None)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["title"] == "Peer readiness not ready yet"
    assert "build peer readiness proof" in rendered
    assert "refresh peer readiness proof" not in rendered
    assert "generate peer readiness" not in rendered
    assert cards[0]["command"] == "make readiness"
