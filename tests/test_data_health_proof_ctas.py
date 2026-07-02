from __future__ import annotations

import pandas as pd

from src.data_health_proof_ctas import (
    data_health_dcf_input_proof_queue_dashboard_cards,
    data_health_lane_auto_context_cards,
)
from src.reviewed_batch import FreshnessStatus


def _render_cards(cards: list[dict[str, object]]) -> str:
    return " ".join(str(value) for card in cards for value in card.values()).lower()


def test_dcf_input_proof_queue_dashboard_cards_show_packet_and_stop_rule():
    frame = pd.DataFrame(
        [
            {
                "Ticker": "META",
                "Missing Input Family": "shares_outstanding",
                "Source Mode": "SEC-stageable or trusted-local",
                "Next Proof Command": "make share-count-proof-queue TICKERS=META",
                "Proof Packet Command": "DRY_RUN=1 make reviewed-batch LANE=share_count TICKERS=META",
                "Stop Rule": "Stop if shares_outstanding is unavailable from SEC/manual source proof.",
            },
            {
                "Ticker": "ACHV",
                "Missing Input Family": "fcf_margin",
                "Source Mode": "SEC-stageable or trusted-local",
                "Next Proof Command": "make focus-fundamentals TICKER=ACHV",
                "Proof Packet Command": "DRY_RUN=1 make fundamentals-batch-proof TICKERS=ACHV",
                "Stop Rule": "Stop if trusted source rows do not prove the required FCF margin field.",
            },
        ]
    )

    cards = data_health_dcf_input_proof_queue_dashboard_cards(frame)
    rendered = _render_cards(cards)

    assert [card["kicker"] for card in cards] == [
        "DCF INPUT QUEUE",
        "NEXT PROOF COMMAND",
        "PROOF PACKET",
        "STOP RULE",
    ]
    assert cards[0]["title"] == "2 queued DCF input row(s)"
    assert cards[1]["command"] == "make share-count-proof-queue TICKERS=META"
    assert cards[2]["command"] == "DRY_RUN=1 make reviewed-batch LANE=share_count TICKERS=META"
    assert "top input families: shares_outstanding: 1; fcf_margin: 1" in rendered
    assert "meta / shares_outstanding" in rendered
    assert "missing fields: shares_outstanding" in rendered
    assert "dry_run=1 make reviewed-batch lane=share_count tickers=meta" in rendered
    assert "use the copyable packet command on this card" in rendered
    assert "gate: validate, preview, rejected-row review" in rendered
    assert "stop if shares_outstanding is unavailable" in rendered
    assert "never infer" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered


def test_dcf_input_proof_queue_empty_state_keeps_command_out_of_body():
    cards = data_health_dcf_input_proof_queue_dashboard_cards(None)
    body = str(cards[0]["body"]).lower()

    assert cards[0]["title"] == "Refresh the DCF proof queue"
    assert cards[0]["command"] == "make dcf-input-proof-queue TOP_N=10"
    assert "open operator details" in body
    assert "copy-only command" not in body
    assert "make " not in body


def test_lane_auto_context_cards_use_refresh_gate_when_stale():
    freshness = FreshnessStatus("stale", "Readiness artifacts are stale.", refresh_command="make readiness")

    dcf_cards = data_health_lane_auto_context_cards("dcf", freshness)
    peer_cards = data_health_lane_auto_context_cards("peer", freshness)
    rendered = _render_cards(dcf_cards + peer_cards)

    assert dcf_cards[0]["title"] == "Refresh readiness before DCF proof planning"
    assert peer_cards[0]["title"] == "Refresh readiness before peer proof planning"
    assert "do not use stale readiness artifacts as dcf proof" in rendered
    assert "do not use stale readiness artifacts as peer proof" in rendered
    assert "dcf proof batch planner" not in rendered
    assert "peer proof batch planner" not in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered
