from __future__ import annotations

import pandas as pd

from src import data_health_peer_unlock as peer_unlock


def test_peer_unlock_operator_cards_group_priorities_scope_and_next_input():
    worklist = pd.DataFrame(
        [
            {
                "ticker": "A",
                "priority": 1,
                "workflow_group": "dcf_ready_peer_mapping",
                "workflow_scope": "master_universe",
                "next_action_summary": "Add at least two trusted, source-backed peer rows; fallback sector/industry context is not trusted peer data.",
                "next_input_file": "data/imports/peers.csv",
                "validation_sequence": "make templates -> make imports-validate -> make imports-preview -> make imports-apply",
                "focus_command": "make focus-peers TICKER=A",
            },
            {
                "ticker": "META",
                "priority": 1,
                "workflow_group": "dcf_ready_peer_mapping",
                "workflow_scope": "active_universe",
                "next_action_summary": "Add source-backed peers for active universe DCF workflow.",
                "next_input_file": "data/imports/peers.csv",
                "validation_sequence": "make templates -> make imports-validate -> make imports-preview -> make imports-apply",
                "focus_command": "make focus-peers TICKER=META",
            },
            {
                "ticker": "APLD",
                "priority": 3,
                "workflow_group": "peer_mapping_after_price",
                "workflow_scope": "master_universe",
                "next_action_summary": "Add prices first, then peer mappings.",
                "next_input_file": "data/imports/peers.csv",
                "validation_sequence": "make templates -> make imports-validate",
                "focus_command": "make focus-peers TICKER=APLD",
            },
        ]
    )

    cards = peer_unlock.peer_unlock_operator_cards(worklist)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert "p1: 2" in rendered
    assert "p3: 1" in rendered
    assert "active universe: 1" in rendered
    assert "master universe: 2" in rendered
    assert "active-universe queue: 1" in rendered
    assert "dcf-ready but peer-blocked: 2" in rendered
    assert "meta" in rendered
    assert "data/imports/peers.csv" in rendered
    assert "schema fields: ticker, peer_ticker, peer_group, sector, industry, source, as_of_date" in rendered
    assert "make imports-preview" in rendered
    assert "dcf ready peer mapping" in rendered
    assert "peer trend can use mapped peer price history" in rendered
    assert "peer valuation waits for source-backed peer mappings and peer valuation inputs" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_peer_unlock_operator_cards_keep_etf_rows_in_monitor_context():
    worklist = pd.DataFrame(
        [
            {
                "ticker": "QQQ",
                "priority": 1,
                "workflow_group": "dcf_ready_peer_mapping",
                "workflow_scope": "active_universe",
                "next_action_summary": "Add source-backed peers for QQQ.",
                "next_input_file": "data/imports/peers.csv",
                "validation_sequence": "make templates -> make imports-validate",
                "focus_command": "make focus-peers TICKER=QQQ",
            },
            {
                "ticker": "COHR",
                "priority": 1,
                "workflow_group": "dcf_ready_peer_mapping",
                "workflow_scope": "active_universe",
                "next_action_summary": "Add source-backed peers for COHR.",
                "next_input_file": "data/imports/peers.csv",
                "validation_sequence": "make templates -> make imports-validate -> make imports-preview -> make imports-apply",
                "focus_command": "make focus-peers TICKER=COHR",
            },
        ]
    )
    readiness = pd.DataFrame(
        [
            {"ticker": "QQQ", "asset_type": "etf", "in_active_universe": True},
            {"ticker": "COHR", "asset_type": "company", "in_active_universe": True, "dcf_ready": True, "peer_ready": False},
        ]
    )

    cards = peer_unlock.peer_unlock_operator_cards(worklist, readiness)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert "cohr" in rendered
    assert "active-universe queue: 2" in rendered
    assert "dcf-ready but peer-blocked: 1" in rendered
    assert "make focus-peers ticker=cohr" in rendered
    assert "monitor proxy context" in rendered
    assert "make stock-report-md ticker=qqq" in rendered
    assert "make focus-peers ticker=qqq" not in rendered
    assert "ticker=<ticker>" not in rendered
    assert "peer valuation remains excluded" in rendered
    assert "broker" not in rendered
    assert "order" not in rendered
    assert "trade" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_peer_unlock_operator_cards_empty_state_uses_readiness_proof_copy():
    cards = peer_unlock.peer_unlock_operator_cards(None)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["title"] == "Peer unlock queue not ready yet"
    assert "build the peer unlock queue" in rendered
    assert "refresh the peer unlock queue" not in rendered
    assert "outputs/peer_unlock_worklist.csv" not in rendered
    assert cards[0]["command"] == "make readiness"
