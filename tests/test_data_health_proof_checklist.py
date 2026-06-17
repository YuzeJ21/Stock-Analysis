from __future__ import annotations

import pandas as pd

from src.data_health_proof_checklist import (
    proof_checklist_summary_cards,
    proof_checklist_summary_frame,
)


def test_proof_checklist_summary_surfaces_dcf_and_peer_before_drawers():
    readiness = {"price_ready": 100, "dcf_ready": 20, "peer_ready": 5}
    outcomes = pd.DataFrame(
        [
            {
                "Lane": "Fundamentals / DCF Proof",
                "Latest Outcome": "still_blocked",
                "Review Date": "2026-06-17",
                "Operator Cue": "DCF source fields are still missing.",
            },
            {
                "Lane": "Peer Mapping Proof",
                "Latest Outcome": "not_recorded",
                "Review Date": "not recorded",
                "Operator Cue": "No peer proof recorded yet.",
            },
        ]
    )

    frame = proof_checklist_summary_frame(readiness, outcomes)
    cards = proof_checklist_summary_cards(readiness, outcomes)
    rendered = " ".join(
        frame.astype(str).to_numpy().flatten().tolist()
        + [str(value) for card in cards for value in card.values()]
    ).lower()

    assert frame["Proof Lane"].tolist() == ["DCF proof checklist", "Peer proof checklist"]
    assert frame.iloc[0]["Checklist Status"] == "still_blocked"
    assert frame.iloc[0]["Coverage Gap"] == "80 price-ready row(s) still need trusted DCF inputs"
    assert frame.iloc[1]["Checklist Status"] == "needs_peer_source_proof"
    assert frame.iloc[1]["Coverage Gap"] == "95 price-ready row(s) still need source-backed peer proof"
    assert cards[0]["title"] == "2 lane(s) need proof work"
    assert cards[1]["title"] == "still blocked"
    assert cards[1]["command"] == "Open Fundamentals / DCF lane drawer"
    assert "before opening detailed drawers" in rendered
    assert "finish source fields" in rendered
    assert "finish peer source fields" in rendered
    assert "data-readiness evidence, not analysis or recommendation output" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered
    assert "order" not in rendered


def test_proof_checklist_summary_marks_supported_with_remaining_gap():
    readiness = {"price_ready": 100, "dcf_ready": 20, "peer_ready": 100}
    outcomes = pd.DataFrame(
        [
            {"Lane": "DCF Proof", "Latest Outcome": "supported"},
            {"Lane": "Peer Mapping Proof", "Latest Outcome": "supported"},
        ]
    )

    frame = proof_checklist_summary_frame(readiness, outcomes)
    cards = proof_checklist_summary_cards(readiness, outcomes)
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert frame.iloc[0]["Checklist Status"] == "supported_but_more_rows_blocked"
    assert frame.iloc[1]["Checklist Status"] == "ready_or_no_current_gap"
    assert cards[0]["title"] == "1 lane(s) need proof work"
    assert "recommendation" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered
