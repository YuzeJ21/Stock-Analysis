import pandas as pd

from src.data_health_proof_outcome import proof_outcome_cards_from_frame


def test_proof_outcome_cards_focus_first_blocking_gate():
    outcome = pd.DataFrame(
        [
            {
                "Proof Loop Step": "Source review intake",
                "Status": "needs_field_fills",
                "Detail": "source proof missing",
                "Next Safe Action": "make dcf-input-source-review TOP_N=10",
            },
            {
                "Proof Loop Step": "Before / after readiness comparison",
                "Status": "ready",
                "Detail": "comparison ready",
                "Next Safe Action": "make reviewed-batch-compare LANE=fundamentals",
            },
            {
                "Proof Loop Step": "Latest DCF ledger outcome",
                "Status": "not_recorded",
                "Detail": "no proof row",
                "Next Safe Action": "make reviewed-batch-proof",
            },
        ]
    )

    cards = proof_outcome_cards_from_frame(
        outcome,
        kicker="DCF PROOF OUTCOME",
        empty_title="No proof-loop status loaded",
        empty_body="Open the DCF source-review drawer before recording an outcome.",
        empty_badges=["readiness first"],
        empty_command="make dcf-input-proof-queue TOP_N=10",
        latest_title_prefix="Latest ledger outcome",
        decision_sentence="Use this summary to decide whether the proof loop is ready, still blocked, skipped, or only scaffolded.",
        badges=["proof loop", "no inferred inputs"],
        fallback_command="make reviewed-batch-proof",
    )
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert cards[0]["title"] == "Latest ledger outcome: not_recorded"
    assert cards[0]["command"] == "make dcf-input-source-review TOP_N=10"
    assert "next proof gate: source review intake" in rendered
    assert "no inferred inputs" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered


def test_proof_outcome_cards_use_latest_when_no_blocker_exists():
    outcome = pd.DataFrame(
        [
            {
                "Proof Loop Step": "Before / after readiness comparison",
                "Status": "ready",
                "Detail": "comparison ready",
                "Next Safe Action": "make reviewed-batch-compare LANE=peers",
            },
            {
                "Proof Loop Step": "Latest peer ledger outcome",
                "Status": "supported",
                "Detail": "proof row supported",
                "Next Safe Action": "make reviewed-batch-proof",
            },
        ]
    )

    cards = proof_outcome_cards_from_frame(
        outcome,
        kicker="PEER PROOF OUTCOME",
        empty_title="No proof-loop status loaded",
        empty_body="Open peer source review before recording peer mapping outcomes.",
        empty_badges=["readiness first"],
        empty_command="make peer-mapping-source-review TOP_N=10",
        latest_title_prefix="Latest ledger outcome",
        decision_sentence="Use this summary to decide whether peer mapping is supported, still blocked, skipped, or only scaffolded.",
        badges=["proof loop", "no inferred peers"],
        fallback_command="make reviewed-batch-proof",
    )

    assert cards[0]["title"] == "Latest ledger outcome: supported"
    assert cards[0]["command"] == "make reviewed-batch-proof"


def test_proof_outcome_cards_empty_state_is_copy_only():
    cards = proof_outcome_cards_from_frame(
        None,
        kicker="PEER PROOF OUTCOME",
        empty_title="No proof-loop status loaded",
        empty_body="Open peer source review before recording peer mapping outcomes.",
        empty_badges=["readiness first", "blocked visible"],
        empty_command="make peer-mapping-source-review TOP_N=10",
        latest_title_prefix="Latest ledger outcome",
        decision_sentence="Use this summary to decide whether peer mapping is supported.",
        badges=["proof loop"],
        fallback_command="make reviewed-batch-proof",
    )

    assert cards == [
        {
            "kicker": "PEER PROOF OUTCOME",
            "title": "No proof-loop status loaded",
            "body": "Open peer source review before recording peer mapping outcomes.",
            "badges": ["readiness first", "blocked visible"],
            "command": "make peer-mapping-source-review TOP_N=10",
        }
    ]
