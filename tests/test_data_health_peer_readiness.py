from __future__ import annotations

import pandas as pd

from src import data_health_peer_readiness as peer_readiness


def test_peer_readiness_product_cards_empty_state_keeps_command_out_of_body():
    cards = peer_readiness.peer_readiness_product_cards(None)
    body = str(cards[0]["body"]).lower()

    assert cards[0]["title"] == "Peer readiness not ready yet"
    assert cards[0]["command"] == "make readiness"
    assert "open operator details" in body
    assert "copy-only command" not in body
    assert "make " not in body


def test_peer_readiness_product_cards_surface_specific_peer_blockers():
    peer_frame = pd.DataFrame(
        [
            {
                "ticker": "NVDA",
                "peer_ready": True,
                "peer_trend_comparison_ready": True,
                "peer_valuation_comparison_ready": False,
                "peer_dcf_comparison_ready": False,
                "peer_blocker_type": "peer_valuation_blocked",
                "peer_count": 2,
                "ready_peer_count": 2,
                "next_peer_action": "Import DCF-ready fundamentals for mapped peers: AMD.",
            },
            {
                "ticker": "META",
                "peer_ready": False,
                "peer_trend_comparison_ready": False,
                "peer_valuation_comparison_ready": False,
                "peer_dcf_comparison_ready": False,
                "peer_blocker_type": "missing_peer_mapping",
                "peer_count": 0,
                "ready_peer_count": 0,
                "next_peer_action": "Add at least 2 source-backed peer mappings for META in data/imports/peers.csv.",
            },
        ]
    )
    queue = pd.DataFrame({"ticker": ["META"], "priority": [1]})

    cards = peer_readiness.peer_readiness_product_cards(peer_frame, queue)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert "1/2 ready" in rendered
    assert "missing peer mapping" in rendered
    assert "make focus-peers ticker=meta" in rendered
    assert "make peer-mapping-queue top_n=25" in rendered
    assert "import-file validation" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_peer_readiness_product_cards_prioritize_peer_unlock_worklist_active_scope():
    peer_frame = pd.DataFrame(
        [
            {
                "ticker": "A",
                "peer_ready": False,
                "peer_trend_comparison_ready": False,
                "peer_valuation_comparison_ready": False,
                "peer_dcf_comparison_ready": False,
                "peer_blocker_type": "missing_peer_mapping",
                "next_peer_action": "Add at least 2 source-backed peer mappings for A in data/imports/peers.csv.",
            },
            {
                "ticker": "COHR",
                "peer_ready": False,
                "peer_trend_comparison_ready": False,
                "peer_valuation_comparison_ready": False,
                "peer_dcf_comparison_ready": False,
                "peer_blocker_type": "missing_peer_mapping",
                "next_peer_action": "Add at least 2 source-backed peer mappings for COHR in data/imports/peers.csv.",
            },
        ]
    )
    worklist = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "A",
                "workflow_scope": "master_universe",
                "next_action_summary": "Broad master-universe peer mapping follow-up.",
            },
            {
                "priority": 1,
                "ticker": "COHR",
                "workflow_scope": "active_universe",
                "next_action_summary": "Add active source-backed peer mappings first.",
            },
        ]
    )

    cards = peer_readiness.peer_readiness_product_cards(peer_frame, pd.DataFrame({"ticker": ["A", "COHR"]}), worklist)
    next_card = next(card for card in cards if card["kicker"] == "NEXT PEER TARGET")
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert next_card["title"] == "COHR"
    assert next_card["command"] == "make focus-peers TICKER=COHR"
    assert "active source-backed peer mappings first" in rendered
    assert "broad master-universe peer mapping follow-up" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_peer_readiness_product_cards_prioritize_active_dcf_workflow_before_broad_priority():
    peer_frame = pd.DataFrame(
        [
            {
                "ticker": "AAPL",
                "peer_ready": False,
                "peer_trend_comparison_ready": True,
                "peer_valuation_comparison_ready": False,
                "peer_dcf_comparison_ready": False,
                "peer_blocker_type": "peer_fundamentals_missing",
                "next_peer_action": "Add broad peer fundamentals.",
            },
            {
                "ticker": "CRDO",
                "peer_ready": False,
                "peer_trend_comparison_ready": True,
                "peer_valuation_comparison_ready": False,
                "peer_dcf_comparison_ready": False,
                "peer_blocker_type": "peer_fundamentals_missing",
                "next_peer_action": "Add active peer fundamentals.",
            },
        ]
    )
    worklist = pd.DataFrame(
        [
            {
                "priority": 1,
                "ticker": "AAPL",
                "workflow_group": "peer_valuation_unlock",
                "workflow_scope": "master_universe",
                "next_action_summary": "Broad master-universe peer fundamentals follow-up.",
            },
            {
                "priority": 2,
                "ticker": "CRDO",
                "workflow_group": "peer_valuation_unlock",
                "workflow_scope": "active_universe",
                "next_action_summary": "Active DCF-ready peer valuation follow-up.",
            },
        ]
    )

    cards = peer_readiness.peer_readiness_product_cards(peer_frame, pd.DataFrame({"ticker": ["AAPL", "CRDO"]}), worklist)
    next_card = next(card for card in cards if card["kicker"] == "NEXT PEER TARGET")
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert next_card["title"] == "CRDO"
    assert next_card["command"] == "make focus-peers TICKER=CRDO"
    assert "active dcf-ready peer valuation follow-up" in rendered
    assert "broad master-universe peer fundamentals follow-up" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
