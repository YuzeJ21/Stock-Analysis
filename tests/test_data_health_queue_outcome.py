from __future__ import annotations

import pandas as pd

from src.data_health_queue_outcome import readiness_queue_outcome_summary_cards


def test_readiness_queue_outcome_summary_cards_keep_drawers_optional():
    frame = pd.DataFrame(
        [
            {
                "Lane": "Fundamentals / DCF Proof",
                "Queue State": "Partial",
                "Latest Outcome": "supported",
                "Review Date": "2026-06-15",
                "Batch ID": "RB-FUND",
                "Changed Tickers": "AAA",
                "Changed Readiness Counts": "dcf_ready 26->27",
                "Operator Cue": "Latest reviewed batch outcome is supported; keep source proof visible.",
                "Next Safe Action": "make sec-stage-queue TOP_N=25",
                "Proof Ledger Command": "make reviewed-batch-proof",
            },
            {
                "Lane": "Peer Mapping Proof",
                "Queue State": "Partial",
                "Latest Outcome": "still_blocked",
                "Review Date": "2026-06-15",
                "Batch ID": "RB-PEER",
                "Changed Tickers": "none",
                "Changed Readiness Counts": "none",
                "Operator Cue": "Latest reviewed batch outcome is still blocked.",
                "Next Safe Action": "make peer-mapping-queue TOP_N=25",
                "Proof Ledger Command": "make reviewed-batch-proof",
            },
            {
                "Lane": "Metrics Readiness",
                "Queue State": "Partial",
                "Latest Outcome": "not_recorded",
                "Review Date": "not recorded",
                "Batch ID": "not recorded",
                "Changed Tickers": "not recorded",
                "Changed Readiness Counts": "not recorded",
                "Operator Cue": "No reviewed batch outcome recorded yet.",
                "Next Safe Action": "make metric-readiness-board TOP_N=10",
                "Proof Ledger Command": "make reviewed-batch-proof",
            },
        ]
    )

    cards = readiness_queue_outcome_summary_cards(frame)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert [card["kicker"] for card in cards] == ["QUEUE OUTCOMES", "LATEST LANE OUTCOME"]
    assert cards[0]["title"] == "1 supported / 1 still blocked"
    assert cards[0]["command"] == "make reviewed-batch-proof"
    assert "0 skipped, 0 excluded, and 1 lane(s) without" in rendered
    assert "proof-ledger status, not a security ranking or recommendation" in rendered
    assert "open the lane drawer only when you need" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered


def test_readiness_queue_outcome_summary_cards_empty_state_is_research_only():
    cards = readiness_queue_outcome_summary_cards(pd.DataFrame())
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["title"] == "No queue outcomes available"
    assert cards[0]["command"] == "make readiness-queue TOP_N=10"
    assert "supported, still blocked, skipped, and excluded" in rendered
    assert "research-only" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered
