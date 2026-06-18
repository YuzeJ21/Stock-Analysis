import pandas as pd

from src.data_health_proof_closeout import proof_closeout_cards_from_frame, proof_closeout_frame_from_outcome


def test_proof_closeout_frame_keeps_open_gates_visible_before_closeout():
    outcome = pd.DataFrame(
        [
            {
                "Proof Loop Step": "Source review intake",
                "Status": "blocked_missing_source",
                "Detail": "source_file_or_url is missing",
                "Next Safe Action": "make dcf-input-source-review TOP_N=10",
            },
            {
                "Proof Loop Step": "Before / after readiness comparison",
                "Status": "ready",
                "Detail": "changed readiness counts reviewed",
                "Next Safe Action": "make readiness",
            },
            {
                "Proof Loop Step": "Latest DCF ledger outcome",
                "Status": "still_blocked",
                "Detail": "latest reviewed outcome remains blocked",
                "Next Safe Action": "make reviewed-batch-proof",
            },
        ]
    )

    frame = proof_closeout_frame_from_outcome(
        outcome,
        latest_step="Latest DCF ledger outcome",
        empty_evidence="Open the DCF proof outcome loop before closeout.",
        empty_action="make dcf-input-proof-queue TOP_N=10",
        empty_boundary="Do not close without proof.",
        fallback_action="make dcf-input-proof-queue TOP_N=10",
        complete_action="make reviewed-batch-proof",
        record_action="DRY_RUN=1 make reviewed-batch-proof-record ...",
        record_evidence="Record a reviewed ledger outcome after source review.",
        boundary="Closeout is proof state only, not investment advice.",
    )
    cards = proof_closeout_cards_from_frame(
        frame,
        kicker="DCF CLOSEOUT",
        empty_title="DCF closeout is not loaded",
        empty_body="Open the DCF proof outcome loop.",
        empty_badges=["blocked visible"],
        empty_command="make dcf-input-proof-queue TOP_N=10",
        fallback_command="make reviewed-batch-proof",
    )
    rendered = " ".join(
        frame.astype(str).to_numpy().flatten().tolist()
        + [str(value) for card in cards for value in card.values()]
    ).lower()

    assert frame.iloc[0]["Closeout Status"] == "still_blocked"
    assert frame.iloc[0]["Latest Outcome"] == "still_blocked"
    assert frame.iloc[0]["Comparison Status"] == "ready"
    assert "source review intake" in frame.iloc[0]["Evidence Remaining"].lower()
    assert frame.iloc[0]["Next Safest Action"] == "make dcf-input-source-review TOP_N=10"
    assert cards[0]["title"] == "Closeout status: still_blocked"
    assert "proof state only" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered


def test_proof_closeout_frame_uses_record_gate_when_no_final_outcome_exists():
    outcome = pd.DataFrame(
        [
            {
                "Proof Loop Step": "Before / after readiness comparison",
                "Status": "ready",
                "Detail": "comparison reviewed",
                "Next Safe Action": "make readiness",
            },
            {
                "Proof Loop Step": "Latest peer ledger outcome",
                "Status": "not_recorded",
                "Detail": "no reviewed proof row yet",
                "Next Safe Action": "DRY_RUN=1 make reviewed-batch-proof-record ...",
            },
        ]
    )

    frame = proof_closeout_frame_from_outcome(
        outcome,
        latest_step="Latest peer ledger outcome",
        empty_evidence="Open the peer proof outcome loop before closeout.",
        empty_action="make peer-mapping-source-review TOP_N=10",
        empty_boundary="Do not close without proof.",
        fallback_action="make peer-mapping-source-review TOP_N=10",
        complete_action="make reviewed-batch-proof",
        record_action="DRY_RUN=1 make reviewed-batch-proof-record ...",
        record_evidence="Record a reviewed ledger outcome after peer source files are reviewed.",
        boundary="Closeout is peer-readiness proof state only.",
    )

    assert frame.iloc[0]["Closeout Status"] == "not_recorded"
    assert frame.iloc[0]["Evidence Remaining"] == "Record a reviewed ledger outcome after peer source files are reviewed."
    assert frame.iloc[0]["Next Safest Action"] == "DRY_RUN=1 make reviewed-batch-proof-record ..."


def test_proof_closeout_frame_uses_empty_fallbacks():
    frame = proof_closeout_frame_from_outcome(
        None,
        latest_step="Latest peer ledger outcome",
        empty_evidence="Open the peer proof outcome loop before closeout.",
        empty_action="make peer-mapping-source-review TOP_N=10",
        empty_boundary="Do not close without proof.",
        fallback_action="make peer-mapping-source-review TOP_N=10",
        complete_action="make reviewed-batch-proof",
        record_action="DRY_RUN=1 make reviewed-batch-proof-record ...",
        record_evidence="Record a reviewed ledger outcome.",
        boundary="Closeout is proof state only.",
    )

    assert frame.iloc[0]["Closeout Status"] == "not_loaded"
    assert frame.iloc[0]["Latest Outcome"] == "not_recorded"
    assert frame.iloc[0]["Next Safest Action"] == "make peer-mapping-source-review TOP_N=10"
