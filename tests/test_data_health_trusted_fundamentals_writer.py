import pandas as pd

from src.data_health_trusted_fundamentals_writer import (
    trusted_fundamentals_apply_decision_gate_cards,
    trusted_fundamentals_apply_decision_gate_frame,
    trusted_fundamentals_evidence_writer_cards,
    trusted_fundamentals_evidence_writer_frame,
)


def _source_review_frame(**overrides: object) -> pd.DataFrame:
    row: dict[str, object] = {
        "Selected Tickers": "AACB",
        "Top Blocker Family": "fundamentals_bundle_plus_shares",
        "Missing Source-Review Fields": "source_file_or_url, source_as_of_date, revenue, free_cash_flow",
        "Source Guard Status": "needs_field_fills",
        "Import Row Scaffold": "blocked until source-review fields and guard status are ready",
        "Apply Boundary": "Do not apply imports while evidence fields are missing.",
        "Post-Run Proof": "make dcf-readiness && make readiness && make stock-report-md TICKER=AACB",
        "Proof Record Dry-Run Boundary": "Finish evidence intake and source guard before proof-record dry run.",
        "Stop Rule": "Stop if trusted source rows do not prove required DCF fields.",
    }
    row.update(overrides)
    return pd.DataFrame([row])


def test_evidence_writer_blocks_placeholder_source_review_fields():
    writer = trusted_fundamentals_evidence_writer_frame(_source_review_frame())
    cards = trusted_fundamentals_evidence_writer_cards(_source_review_frame())
    rendered = " ".join(
        writer.astype(str).to_numpy().flatten().tolist()
        + [str(value) for card in cards for value in card.values()]
    ).lower()

    assert writer.iloc[0]["Dry Run"] == "DRY_RUN=1"
    assert writer.iloc[0]["Writer Status"] == "blocked_by_placeholders"
    assert writer.iloc[0]["Proposed Import Row"] == "blocked until reviewed source fields pass the source guard"
    assert "source_file_or_url" in writer.iloc[0]["Missing Fields"]
    assert cards[0]["title"] == "Preview packet blocked"
    assert "dry-run only" in rendered
    assert "canonical fundamentals" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
    assert "broker" not in rendered


def test_evidence_writer_ready_state_still_keeps_apply_gated():
    source_review = _source_review_frame(
        **{
            "Missing Source-Review Fields": "-",
            "Source Guard Status": "ready_for_guard",
            "Import Row Scaffold": "AACB,<reviewed_period>,100,20,0.20,1000,https://www.sec.gov/example,2026-06-01",
            "Apply Boundary": "Run make imports-apply only after source guard, validate, preview, and rejected-row review are complete.",
            "Proof Record Dry-Run Boundary": "DRY_RUN=1 make reviewed-batch-proof-record BATCH_ID=RB-FUND-AACB FINAL_OUTCOME=<supported|still_blocked|skipped|excluded>",
        }
    )

    writer = trusted_fundamentals_evidence_writer_frame(source_review)
    gate = trusted_fundamentals_apply_decision_gate_frame(
        source_review,
        validation_result="passed",
        preview_result="reviewed",
        rejected_row_review="reviewed_no_rejected_rows",
        apply_decision="still_blocked",
        changed_readiness_proof="make readiness",
        generated_artifacts_reviewed="excluded broad CSV churn",
    )
    rendered = " ".join(writer.astype(str).to_numpy().flatten().tolist() + gate.astype(str).to_numpy().flatten().tolist()).lower()

    assert writer.iloc[0]["Writer Status"] == "preview_packet_ready"
    assert writer.iloc[0]["Missing Fields"] == "-"
    assert writer.iloc[0]["Proposed Import Row"].startswith("AACB,<reviewed_period>")
    assert gate.iloc[0]["Gate Status"] == "still_blocked_ready"
    assert gate.iloc[0]["Proof Record Dry-Run Command"].startswith("DRY_RUN=1 make reviewed-batch-proof-record")
    assert "make imports-apply only after source guard" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered


def test_apply_decision_gate_rejects_invalid_outcome_before_proof_record():
    source_review = _source_review_frame(
        **{
            "Missing Source-Review Fields": "-",
            "Source Guard Status": "ready_for_guard",
            "Import Row Scaffold": "AACB,<reviewed_period>,100,20,0.20,1000,source,2026-06-01",
            "Proof Record Dry-Run Boundary": "DRY_RUN=1 make reviewed-batch-proof-record BATCH_ID=RB-FUND-AACB",
        }
    )

    gate = trusted_fundamentals_apply_decision_gate_frame(
        source_review,
        validation_result="passed",
        preview_result="reviewed",
        rejected_row_review="reviewed_no_rejected_rows",
        apply_decision="approved",
    )
    cards = trusted_fundamentals_apply_decision_gate_cards(source_review)
    rendered = " ".join(
        gate.astype(str).to_numpy().flatten().tolist()
        + [str(value) for card in cards for value in card.values()]
    ).lower()

    assert gate.iloc[0]["Gate Status"] == "invalid_apply_decision"
    assert gate.iloc[0]["Proof Record Dry-Run Command"] == "blocked until validation, preview, rejected-row review, and apply decision are reviewed"
    assert "apply_reviewed, skip_reviewed, still_blocked" in rendered
    assert "no canonical fundamentals write" in rendered
    assert "buy" not in rendered
    assert "sell" not in rendered
