from __future__ import annotations

import pandas as pd

from src.data_health_proof_planner import (
    proof_planner_outcome_summary_cards,
    proof_planner_outcome_summary_frame,
)
from src.reviewed_batch import FreshnessStatus


def _render_cards(cards: list[dict[str, object]]) -> str:
    return " ".join(str(value) for card in cards for value in card.values()).lower()


def test_proof_planner_outcome_summary_stays_summary_first():
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

    frame = proof_planner_outcome_summary_frame(readiness, outcomes)
    cards = proof_planner_outcome_summary_cards(readiness, outcomes)
    rendered = " ".join(
        frame.astype(str).to_numpy().flatten().tolist()
        + [str(value) for card in cards for value in card.values()]
    ).lower()

    assert frame["Planner Lane"].tolist() == ["DCF proof planner", "Peer proof planner"]
    assert frame.iloc[0]["Planner State"] == "still_blocked"
    assert frame.iloc[0]["Lane URL"] == "?mode=operator&page=data-health&lane=fundamentals"
    assert frame.iloc[1]["Planner State"] == "needs_source_fields"
    assert cards[0]["title"] == "2 planner lane(s) need review"
    assert cards[1]["command"] == "?mode=operator&page=data-health&lane=fundamentals"
    assert "lane links open the detailed planners only when needed" in rendered
    assert "commands and proof tables remain collapsed" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered


def test_proof_planner_outcome_summary_uses_loaded_planner_and_freshness_cta():
    readiness = {"price_ready": 100, "dcf_ready": 20, "peer_ready": 5}
    dcf_planner = pd.DataFrame([{"Step": "5. Record proof only after review", "Status": "ready_for_review_fields"}])
    freshness = FreshnessStatus("stale", "Readiness artifacts are stale.", refresh_command="make readiness")

    frame = proof_planner_outcome_summary_frame(
        readiness,
        pd.DataFrame(),
        freshness,
        dcf_planner_frame=dcf_planner,
    )
    cards = proof_planner_outcome_summary_cards(readiness, pd.DataFrame(), freshness)
    rendered = _render_cards(cards)

    assert frame.iloc[0]["Planner State"] == "ready_for_proof_record_review"
    assert frame.iloc[0]["Detail Level"] == "planner_loaded"
    assert frame.iloc[1]["Planner State"] == "blocked_by_freshness"
    assert cards[0]["title"] == "Refresh readiness before proof planning"
    assert cards[0]["command"] == "make readiness"
    assert "stale readiness rows are not proof" in rendered
    assert "open operator details" in str(cards[0]["body"]).lower()
    assert "make " not in str(cards[0]["body"]).lower()
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered
