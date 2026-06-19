import pandas as pd

from src.data_health_proof_loop_fit import proof_loop_fit_cards, proof_loop_fit_frame


def test_proof_loop_fit_summarizes_status_blocker_evidence_and_stop_rule():
    operator = pd.DataFrame(
        [
            {
                "Question": "What is the current gate?",
                "Status": "needs_field_fills",
                "Answer": "Current gate: fill reviewed source fields. Need: source_file_or_url.",
                "Next Safe Action": "make dcf-input-source-review FAMILY=shares_outstanding TOP_N=10",
                "Boundary": "No canonical fundamentals write before source proof.",
            },
            {
                "Question": "When must I stop?",
                "Status": "stop_rule",
                "Answer": "Stop before proof record if source files or generated-artifact review is missing.",
                "Next Safe Action": "Keep lane still_blocked.",
                "Boundary": "Research-only boundary.",
            },
        ]
    )
    checklist = pd.DataFrame(
        [
            {
                "Checklist Item": "3. Fill source-review fields",
                "Status": "needs_field_fills",
                "Need Before Proceeding": "source_file_or_url, reviewer, review_date",
                "Next Safest Action": "make dcf-input-source-review FAMILY=shares_outstanding TOP_N=10",
                "Stop Rule": "Stop if source proof is missing.",
            }
        ]
    )
    outcome = pd.DataFrame(
        [
            {
                "Proof Loop Step": "Latest DCF ledger outcome",
                "Status": "still_blocked",
                "Detail": "RB-SHARECOUNT remains still_blocked after review.",
                "Next Safe Action": "make reviewed-batch-proof",
            }
        ]
    )
    closeout = pd.DataFrame(
        [
            {
                "Closeout Status": "still_blocked",
                "Latest Outcome": "still_blocked",
                "Evidence Remaining": "Source review intake still missing source_file_or_url.",
                "Next Safest Action": "make dcf-input-source-review FAMILY=shares_outstanding TOP_N=10",
                "Closeout Boundary": "Closeout describes proof state only.",
            }
        ]
    )

    frame = proof_loop_fit_frame(
        lane="DCF",
        operator_summary=operator,
        checklist=checklist,
        outcome=outcome,
        closeout=closeout,
    )
    cards = proof_loop_fit_cards(frame, lane="DCF")
    rendered = " ".join(frame.astype(str).to_numpy().flatten().tolist() + [str(value) for card in cards for value in card.values()]).lower()

    assert frame["Workflow Step"].tolist() == ["Status", "Blocker", "Next Proof Step", "Evidence", "Stop Rule"]
    assert frame.iloc[0]["Status"] == "needs_field_fills"
    assert frame.iloc[1]["What To Look At"] == "source_file_or_url, reviewer, review_date"
    assert frame.iloc[2]["Status"] == "still_blocked"
    assert cards[0]["title"] == "needs_field_fills: 2 open gate(s)"
    assert "use this first before reading detailed source tables" in rendered
    assert "supported, still_blocked, skipped, or excluded" in rendered
    assert "research-only" in rendered
    assert "buy now" not in rendered
    assert "sell now" not in rendered
    assert "broker" not in rendered


def test_proof_loop_fit_uses_peer_ledger_step_and_empty_fallbacks():
    frame = proof_loop_fit_frame(
        lane="Peer",
        operator_summary=pd.DataFrame(),
        checklist=pd.DataFrame(),
        outcome=pd.DataFrame(
            [
                {
                    "Proof Loop Step": "Latest peer ledger outcome",
                    "Status": "not_recorded",
                    "Detail": "No peer reviewed batch proof row recorded yet.",
                    "Next Safe Action": "make reviewed-batch-proof",
                }
            ]
        ),
        closeout=pd.DataFrame(),
    )
    cards = proof_loop_fit_cards(frame, lane="Peer")
    rendered = " ".join(str(value) for card in cards for value in card.values()).lower()

    assert frame.iloc[2]["Status"] == "not_recorded"
    assert frame.iloc[4]["Status"] == "stop_rule"
    assert cards[0]["kicker"] == "PEER PROOF LOOP"
    assert "proof-loop state" in frame.iloc[0]["Boundary"].lower()
    assert "no inferred inputs" in rendered
    assert "buy now" not in rendered
    assert "sell now" not in rendered
