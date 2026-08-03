from __future__ import annotations

from src.reviewed_batch_proof import resolve_readiness_proof_profile

import pandas as pd

from src.data_health_proof_ctas import card_sentence, compact_card_fragment, format_missing


TRUSTED_FUNDAMENTALS_APPLY_DECISIONS = ("apply_reviewed", "skip_reviewed", "still_blocked")


def trusted_fundamentals_evidence_writer_frame(frame: pd.DataFrame | None) -> pd.DataFrame:
    columns = [
        "Dry Run",
        "Selected Ticker",
        "Input Family",
        "Writer Status",
        "Reviewed Source Fields",
        "Proposed Import Row",
        "Missing Fields",
        "Source Guard Status",
        "Validate Command",
        "Preview Command",
        "Apply Boundary",
        "Post-Run Proof Command",
        "Proof Record Dry-Run Command",
        "Stop Rule",
    ]
    if frame is None or frame.empty:
        return pd.DataFrame(
            [
                {
                    "Dry Run": "DRY_RUN=1",
                    "Selected Ticker": "",
                    "Input Family": "",
                    "Writer Status": "blocked_no_source_review_scope",
                    "Reviewed Source Fields": "none",
                    "Proposed Import Row": "blocked until source-review scope exists",
                    "Missing Fields": "selected ticker, input family, reviewed source fields",
                    "Source Guard Status": "blocked_no_source_review_scope",
                    "Validate Command": "make imports-validate",
                    "Preview Command": "make imports-preview",
                    "Apply Boundary": "Do not apply imports without reviewed source proof.",
                    "Post-Run Proof Command": f"make readiness-snapshot PROFILE={resolve_readiness_proof_profile()} && make dcf-readiness && make reviewed-batch-compare PROFILE={resolve_readiness_proof_profile()} LANE=fundamentals BATCH_ID=<reviewed_batch_id> REVIEW_DATE=<yyyy-mm-dd>",
                    "Proof Record Dry-Run Command": "Finish source review before proof-record dry run.",
                    "Stop Rule": "Run the trusted fundamentals source-review drawer before building an evidence writer packet.",
                }
            ],
            columns=columns,
        )
    row = frame.iloc[0]
    ticker = format_missing(row.get("Selected Tickers"), "").split(",", 1)[0].strip().upper()
    family = format_missing(row.get("Top Blocker Family"), "trusted fundamentals")
    missing = format_missing(row.get("Missing Source-Review Fields"), "reviewed source fields")
    guard_status = format_missing(row.get("Source Guard Status"), "blocked")
    import_row = format_missing(row.get("Import Row Scaffold"), "blocked until reviewed fields are complete")
    ready = guard_status == "ready_for_guard" and bool(import_row) and not import_row.lower().startswith("blocked")
    reviewed_fields = (
        f"source guard reviewed for {ticker}; import row preview built from reviewed source fields"
        if ready
        else f"missing reviewed fields: {missing}"
    )
    return pd.DataFrame(
        [
            {
                "Dry Run": "DRY_RUN=1",
                "Selected Ticker": ticker,
                "Input Family": family,
                "Writer Status": "preview_packet_ready" if ready else "blocked_by_placeholders",
                "Reviewed Source Fields": reviewed_fields,
                "Proposed Import Row": import_row if ready else "blocked until reviewed source fields pass the source guard",
                "Missing Fields": "-" if ready else missing,
                "Source Guard Status": guard_status,
                "Validate Command": "make imports-validate",
                "Preview Command": "make imports-preview",
                "Apply Boundary": format_missing(row.get("Apply Boundary"), "Do not apply rows without reviewed source proof."),
                "Post-Run Proof Command": format_missing(row.get("Post-Run Proof"), f"make readiness-snapshot PROFILE={resolve_readiness_proof_profile()} && make dcf-readiness && make reviewed-batch-compare PROFILE={resolve_readiness_proof_profile()} LANE=fundamentals BATCH_ID=<reviewed_batch_id> REVIEW_DATE=<yyyy-mm-dd>"),
                "Proof Record Dry-Run Command": format_missing(
                    row.get("Proof Record Dry-Run Boundary"),
                    "Finish source review before proof-record dry run.",
                ),
                "Stop Rule": format_missing(row.get("Stop Rule"), "Stop if source proof is missing."),
            }
        ],
        columns=columns,
    )


def trusted_fundamentals_evidence_writer_cards(frame: pd.DataFrame | None) -> list[dict[str, object]]:
    writer = trusted_fundamentals_evidence_writer_frame(frame)
    row = writer.iloc[0]
    status = format_missing(row.get("Writer Status"), "blocked")
    ready = status == "preview_packet_ready"
    title = "Preview packet ready" if ready else "Preview packet blocked"
    body = (
        f"{card_sentence('Ticker', row.get('Selected Ticker'))} "
        f"{card_sentence('Family', row.get('Input Family'))} "
        f"{card_sentence('Missing fields', compact_card_fragment(row.get('Missing Fields'), max_chars=160))} "
        f"{card_sentence('Apply boundary', compact_card_fragment(row.get('Apply Boundary'), max_chars=170))} "
        "Dry-run only; this does not write canonical fundamentals."
    )
    command = (
        format_missing(row.get("Proposed Import Row"), "blocked until reviewed source fields pass the source guard")
        if ready
        else format_missing(row.get("Validate Command"), "make imports-validate")
    )
    return [
        {
            "kicker": "EVIDENCE WRITER PREVIEW",
            "title": title,
            "body": body,
            "badges": [status.replace("_", " "), "dry-run only"],
            "command": command,
        }
    ]


def review_placeholder(value: object) -> bool:
    text = format_missing(value, "").strip()
    if not text:
        return True
    lowered = text.lower()
    return (lowered.startswith("<") and lowered.endswith(">")) or lowered in {"-", "not reviewed", "not_run"}


def trusted_fundamentals_apply_decision_gate_frame(
    writer_frame: pd.DataFrame | None,
    *,
    validation_result: object = "<reviewed_validation_result>",
    preview_result: object = "<reviewed_preview_result>",
    rejected_row_review: object = "<reviewed_rejected_row_review>",
    apply_decision: object = "<apply_reviewed|skip_reviewed|still_blocked>",
    changed_readiness_proof: object = "<run_post_run_readiness_proof>",
    generated_artifacts_reviewed: object = "<reviewed_or_excluded_generated_artifacts>",
) -> pd.DataFrame:
    columns = [
        "Selected Ticker",
        "Input Family",
        "Writer Preview Status",
        "Validation Result",
        "Preview Result",
        "Rejected-Row Review",
        "Apply Decision Options",
        "Apply Decision",
        "Gate Status",
        "Changed Readiness Proof Requirement",
        "Generated Artifact Review Requirement",
        "Proof Record Dry-Run Command",
        "Stop Rule",
        "Next Safe Action",
    ]
    writer = trusted_fundamentals_evidence_writer_frame(writer_frame)
    row = writer.iloc[0]
    writer_status = format_missing(row.get("Writer Status"), "blocked")
    decision = format_missing(apply_decision, "")
    review_missing = [
        label
        for label, value in [
            ("validation_result", validation_result),
            ("preview_result", preview_result),
            ("rejected_row_review", rejected_row_review),
        ]
        if review_placeholder(value)
    ]
    if writer_status != "preview_packet_ready":
        gate_status = "blocked_by_writer_preview"
        next_action = "Finish reviewed source fields and source guard before apply/skip review."
    elif review_missing:
        gate_status = "not_ready_missing_review_results"
        next_action = "Run and review imports-validate, imports-preview, and rejected-row reports before choosing apply/skip/still_blocked."
    elif review_placeholder(decision):
        gate_status = "proof_blocked_missing_apply_decision"
        next_action = "Choose apply_reviewed, skip_reviewed, or still_blocked after review results are filled."
    elif decision not in TRUSTED_FUNDAMENTALS_APPLY_DECISIONS:
        gate_status = "invalid_apply_decision"
        next_action = "Use only apply_reviewed, skip_reviewed, or still_blocked."
    elif decision == "apply_reviewed":
        gate_status = "ready_for_reviewed_apply"
        next_action = "Proceed only with reviewed apply boundary, then rebuild readiness and record proof after artifact review."
    elif decision == "skip_reviewed":
        gate_status = "skip_reviewed_ready"
        next_action = "Record reviewed skip after readiness proof and generated-artifact review; do not write canonical fundamentals."
    else:
        gate_status = "still_blocked_ready"
        next_action = "Record still_blocked after proof shows trusted fundamentals remain unavailable."

    proof_command = format_missing(row.get("Proof Record Dry-Run Command"), "DRY_RUN=1 make reviewed-batch-proof-record ...")
    if gate_status in {"blocked_by_writer_preview", "not_ready_missing_review_results", "proof_blocked_missing_apply_decision", "invalid_apply_decision"}:
        proof_command = "blocked until validation, preview, rejected-row review, and apply decision are reviewed"
    return pd.DataFrame(
        [
            {
                "Selected Ticker": format_missing(row.get("Selected Ticker"), ""),
                "Input Family": format_missing(row.get("Input Family"), ""),
                "Writer Preview Status": writer_status,
                "Validation Result": format_missing(validation_result, ""),
                "Preview Result": format_missing(preview_result, ""),
                "Rejected-Row Review": format_missing(rejected_row_review, ""),
                "Apply Decision Options": ", ".join(TRUSTED_FUNDAMENTALS_APPLY_DECISIONS),
                "Apply Decision": decision,
                "Gate Status": gate_status,
                "Changed Readiness Proof Requirement": format_missing(
                    changed_readiness_proof,
                    "Run post-run readiness proof before supported, skipped, or still-blocked outcome.",
                ),
                "Generated Artifact Review Requirement": format_missing(
                    generated_artifacts_reviewed,
                    "Review generated artifacts; exclude broad CSV/JSON churn unless intentionally selected evidence.",
                ),
                "Proof Record Dry-Run Command": proof_command,
                "Stop Rule": format_missing(
                    row.get("Stop Rule"),
                    "Stop if validation, preview, rejected-row review, apply decision, readiness proof, or artifact review is missing.",
                ),
                "Next Safe Action": next_action,
            }
        ],
        columns=columns,
    )


def trusted_fundamentals_apply_decision_gate_cards(writer_frame: pd.DataFrame | None) -> list[dict[str, object]]:
    gate = trusted_fundamentals_apply_decision_gate_frame(writer_frame)
    row = gate.iloc[0]
    status = format_missing(row.get("Gate Status"), "blocked")
    ready = status in {"ready_for_reviewed_apply", "skip_reviewed_ready", "still_blocked_ready"}
    title = "Apply decision gate ready" if ready else "Apply decision gate blocked"
    return [
        {
            "kicker": "APPLY / SKIP GATE",
            "title": title,
            "body": (
                f"{card_sentence('Writer', row.get('Writer Preview Status'))} "
                f"{card_sentence('Decision options', row.get('Apply Decision Options'))} "
                f"{card_sentence('Next action', compact_card_fragment(row.get('Next Safe Action'), max_chars=190))} "
                "No canonical fundamentals write happens from this drawer."
            ),
            "badges": [status.replace("_", " "), "reviewed decision"],
            "command": format_missing(row.get("Proof Record Dry-Run Command"), "blocked until reviewed decision gate is complete"),
        }
    ]
