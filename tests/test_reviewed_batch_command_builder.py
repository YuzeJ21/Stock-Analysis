from pathlib import Path

from src.reviewed_batch_command_builder import (
    build_proof_ledger_preview_row,
    build_proof_ledger_preview_rows,
    build_proof_ledger_preview_summary,
    build_proof_completion_rows,
    build_outcome_recorder_rows,
    build_proof_record_command_parts,
    build_proof_record_command_summary,
    is_placeholder_value,
    proof_record_validation_status,
    validate_proof_record_command_parts,
)
from src.reviewed_batch_proof import BATCH_PROOF_COLUMNS


def test_outcome_recorder_rows_keep_placeholders_missing_and_source_ready():
    rows = build_outcome_recorder_rows(
        {
            "Validation Result": "<pass/fail/not_applicable>",
            "Preview Result": "<reviewed/not_run>",
            "Apply Result": "<applied/not_run/skipped>",
            "Changed Readiness Counts": "<from reviewed-batch-compare>",
            "Changed Tickers": "<from reviewed-batch-compare>",
            "Source Files": "metric queue output",
            "Generated Artifacts Review": "<kept evidence or excluded churn>",
        },
        packet_missing=False,
        comparison_status="ok",
        comparison_changed_counts="metric_state (blocked: 2->1)",
        comparison_changed_tickers=("AAA",),
        comparison_blocking_message="",
    )

    statuses = {row["Field"]: row["Status"] for row in rows}

    assert statuses["validation_result"] == "missing_from_record"
    assert statuses["preview_result"] == "missing_from_record"
    assert statuses["apply_result"] == "missing_from_record"
    assert statuses["changed_readiness_counts"] == "missing_from_record"
    assert statuses["changed_tickers"] == "missing_from_record"
    assert statuses["source_files"] == "ready"
    assert statuses["generated_artifacts_reviewed"] == "missing_from_record"
    assert rows[3]["Copy From"] == "metric_state (blocked: 2->1)"


def test_proof_record_command_summary_fills_comparison_and_quotes_placeholders():
    outcome_rows = build_outcome_recorder_rows(
        {
            "Validation Result": "passed",
            "Preview Result": "reviewed 1 row",
            "Apply Result": "skipped",
            "Changed Readiness Counts": "<from reviewed-batch-compare>",
            "Changed Tickers": "<from reviewed-batch-compare>",
            "Source Files": "data/imports/prices.csv",
            "Generated Artifacts Review": "excluded generated CSV churn",
        },
        packet_missing=False,
        comparison_status="ok",
        comparison_changed_counts="price_ready (not_ready: 1->0)",
        comparison_changed_tickers=("AAA",),
        comparison_blocking_message="",
    )
    parts = build_proof_record_command_parts(
        {
            "Batch ID": "RB-1",
            "Lane": "Prices",
            "Scope": "AAA",
            "Dry Run Command": "make price-refresh-loop DRY_RUN=1 TOP_N=1",
            "Allowed Outcome": "skipped",
            "Validation Result": "passed",
            "Preview Result": "reviewed 1 row",
            "Apply Result": "skipped",
            "Source Files": "data/imports/prices.csv",
            "Generated Artifacts Review": "excluded generated CSV churn",
        },
        proposed_tickers=("AAA",),
        comparison_status="ok",
        comparison_before_path=Path("data/reports/ticker_readiness_report.previous.csv"),
        comparison_after_path=Path("data/reports/ticker_readiness_report.csv"),
        comparison_changed_counts="price_ready (not_ready: 1->0)",
        comparison_changed_tickers=("AAA",),
        outcome_rows=outcome_rows,
    )
    summary = build_proof_record_command_summary(parts)
    command = summary["Copy Command"]

    assert summary["Command Status"] == "needs_field_fills"
    assert "BATCH_ID=RB-1" in command
    assert "TICKERS=AAA" in command
    assert "VALIDATION_RESULT=passed" in command
    assert "CHANGED_READINESS_COUNTS='price_ready (not_ready: 1->0)'" in command
    assert "PRE_RUN_READINESS_SNAPSHOT=data/reports/ticker_readiness_report.previous.csv" in command
    assert "REVIEW_DATE='<yyyy-mm-dd>'" in command
    assert "review_date" in summary["Fields To Fill"]
    assert "notes" not in summary["Fields To Fill"]
    assert summary["Manual Fields"] == "reviewer, notes"


def test_proof_record_validation_ready_when_required_fields_are_real():
    outcome_rows = build_outcome_recorder_rows(
        {
            "Validation Result": "passed",
            "Preview Result": "reviewed 1 row",
            "Apply Result": "skipped",
            "Changed Readiness Counts": "price_ready (not_ready: 1->0)",
            "Changed Tickers": "AAA",
            "Source Files": "data/imports/prices.csv",
            "Generated Artifacts Review": "excluded generated CSV churn",
        },
        packet_missing=False,
        comparison_status="ok",
        comparison_changed_counts="price_ready (not_ready: 1->0)",
        comparison_changed_tickers=("AAA",),
        comparison_blocking_message="",
    )
    parts = build_proof_record_command_parts(
        {
            "Batch ID": "RB-2",
            "Lane": "Prices",
            "Scope": "AAA",
            "Review Date": "2026-06-14",
            "Dry Run Command": "make price-refresh-loop DRY_RUN=1 TOP_N=1",
            "Allowed Outcome": "skipped",
            "Validation Result": "passed",
            "Preview Result": "reviewed 1 row",
            "Apply Result": "skipped",
            "Changed Readiness Counts": "price_ready (not_ready: 1->0)",
            "Changed Tickers": "AAA",
            "Source Files": "data/imports/prices.csv",
            "Generated Artifacts Review": "excluded generated CSV churn",
        },
        proposed_tickers=("AAA",),
        comparison_status="ok",
        comparison_before_path=Path("data/reports/ticker_readiness_report.previous.csv"),
        comparison_after_path=Path("data/reports/ticker_readiness_report.csv"),
        comparison_changed_counts="price_ready (not_ready: 1->0)",
        comparison_changed_tickers=("AAA",),
        outcome_rows=outcome_rows,
    )
    validation_rows = validate_proof_record_command_parts(parts)
    summary = build_proof_record_command_summary(parts)

    assert proof_record_validation_status(validation_rows) == "ready_to_record"
    assert summary["Command Status"] == "ready_to_record"
    assert summary["Fields To Fill"] == ""


def test_proof_record_validation_accepts_reviewed_none_for_no_change_fields():
    outcome_rows = build_outcome_recorder_rows(
        {
            "Validation Result": "not_applicable_read_only_metric_review",
            "Preview Result": "reviewed metric blocker families",
            "Apply Result": "not_applicable_read_only_metric_review",
            "Changed Readiness Counts": "none; no readiness counts changed",
            "Changed Tickers": "none",
            "Source Files": "metric queue output",
            "Generated Artifacts Review": "excluded generated CSV churn",
        },
        packet_missing=False,
        comparison_status="ok",
        comparison_changed_counts="none",
        comparison_changed_tickers=(),
        comparison_blocking_message="",
    )
    parts = build_proof_record_command_parts(
        {
            "Batch ID": "RB-8",
            "Lane": "Metric Readiness Review",
            "Scope": "AAA",
            "Review Date": "2026-06-14",
            "Dry Run Command": "make metric-readiness-board TOP_N=1",
            "Allowed Outcome": "still_blocked",
            "Validation Result": "not_applicable_read_only_metric_review",
            "Preview Result": "reviewed metric blocker families",
            "Apply Result": "not_applicable_read_only_metric_review",
            "Changed Readiness Counts": "none; no readiness counts changed",
            "Changed Tickers": "none",
            "Source Files": "metric queue output",
            "Generated Artifacts Review": "excluded generated CSV churn",
        },
        proposed_tickers=("AAA",),
        comparison_status="ok",
        comparison_before_path=Path("data/reports/ticker_readiness_report.previous.csv"),
        comparison_after_path=Path("data/reports/ticker_readiness_report.csv"),
        comparison_changed_counts="none",
        comparison_changed_tickers=(),
        outcome_rows=outcome_rows,
    )

    assert proof_record_validation_status(validate_proof_record_command_parts(parts)) == "ready_to_record"


def test_proof_record_validation_rejects_invalid_outcome():
    parts = build_proof_record_command_parts(
        {
            "Batch ID": "RB-3",
            "Lane": "Prices",
            "Review Date": "2026-06-14",
            "Dry Run Command": "make price-refresh-loop DRY_RUN=1 TOP_N=1",
            "Allowed Outcome": "supported|still_blocked|skipped|excluded",
            "Validation Result": "passed",
            "Preview Result": "reviewed 1 row",
            "Apply Result": "skipped",
            "Changed Readiness Counts": "none",
            "Changed Tickers": "none",
            "Source Files": "data/imports/prices.csv",
            "Generated Artifacts Review": "excluded generated CSV churn",
        },
        proposed_tickers=("AAA",),
        comparison_status="ok",
        comparison_before_path=Path("data/reports/ticker_readiness_report.previous.csv"),
        comparison_after_path=Path("data/reports/ticker_readiness_report.csv"),
        comparison_changed_counts="none",
        comparison_changed_tickers=(),
        outcome_rows=(),
    )
    validation_rows = validate_proof_record_command_parts(parts)
    final_outcome = [row for row in validation_rows if row["Field"] == "final_outcome"][0]

    assert final_outcome["Validation Status"] == "invalid_outcome"
    assert proof_record_validation_status(validation_rows) == "invalid_outcome"


def test_proof_record_validation_prioritizes_snapshot_blockers():
    outcome_rows = build_outcome_recorder_rows(
        {
            "Validation Result": "passed",
            "Preview Result": "reviewed 1 row",
            "Apply Result": "skipped",
            "Changed Readiness Counts": "none",
            "Changed Tickers": "none",
            "Source Files": "data/imports/prices.csv",
            "Generated Artifacts Review": "excluded generated CSV churn",
        },
        packet_missing=False,
        comparison_status="missing_before",
        comparison_changed_counts="not available",
        comparison_changed_tickers=(),
        comparison_blocking_message="Missing prior readiness snapshot.",
    )
    parts = build_proof_record_command_parts(
        {
            "Batch ID": "RB-4",
            "Lane": "Prices",
            "Review Date": "2026-06-14",
            "Dry Run Command": "make price-refresh-loop DRY_RUN=1 TOP_N=1",
            "Allowed Outcome": "skipped",
            "Validation Result": "passed",
            "Preview Result": "reviewed 1 row",
            "Apply Result": "skipped",
            "Changed Readiness Counts": "none",
            "Changed Tickers": "none",
            "Source Files": "data/imports/prices.csv",
            "Generated Artifacts Review": "excluded generated CSV churn",
        },
        proposed_tickers=("AAA",),
        comparison_status="missing_before",
        comparison_before_path=Path("data/reports/ticker_readiness_report.previous.csv"),
        comparison_after_path=Path("data/reports/ticker_readiness_report.csv"),
        comparison_changed_counts="not available",
        comparison_changed_tickers=(),
        outcome_rows=outcome_rows,
    )
    validation_rows = validate_proof_record_command_parts(parts)

    assert proof_record_validation_status(validation_rows) == "blocked_by_snapshot_gate"


def test_placeholder_detection_is_conservative_for_outcome_choices():
    assert is_placeholder_value("<supported|still_blocked|skipped|excluded>")
    assert is_placeholder_value("supported|still_blocked|skipped|excluded")
    assert is_placeholder_value("")
    assert not is_placeholder_value("still_blocked")
    assert not is_placeholder_value("not_applicable_read_only_metric_review")


def test_proof_completion_rows_translate_missing_fields_to_next_actions():
    validation_rows = [
        {
            "Field": "review_date",
            "Validation Status": "missing_required",
            "Command Value": "<yyyy-mm-dd>",
            "Reason": "Required proof field still contains a placeholder or missing value.",
        },
        {
            "Field": "validation_result",
            "Validation Status": "missing_required",
            "Command Value": "<pass/fail/not_applicable>",
            "Reason": "Required proof field still contains a placeholder or missing value.",
        },
    ]

    rows = build_proof_completion_rows(validation_rows, command_status="needs_field_fills")

    assert rows[0]["Field"] == "review_date"
    assert rows[0]["Status"] == "missing_required"
    assert "yyyy-mm-dd" in rows[0]["Next Safest Action"]
    assert rows[1]["Field"] == "validation_result"
    assert "validator result" in rows[1]["Next Safest Action"]


def test_proof_completion_rows_prioritize_snapshot_and_invalid_outcome_actions():
    validation_rows = [
        {
            "Field": "final_outcome",
            "Validation Status": "invalid_outcome",
            "Command Value": "maybe_supported",
            "Reason": "FINAL_OUTCOME must be exactly one of supported, still_blocked, skipped, or excluded.",
        },
        {
            "Field": "changed_tickers",
            "Validation Status": "blocked_by_snapshot_gate",
            "Command Value": "none",
            "Reason": "Snapshot comparison is required before this proof field can be trusted.",
        },
    ]

    rows = build_proof_completion_rows(validation_rows, command_status="invalid_outcome")

    assert rows[0]["Field"] == "final_outcome"
    assert rows[0]["Next Safest Action"] == "Set FINAL_OUTCOME exactly to supported, still_blocked, skipped, or excluded."
    assert rows[1]["Field"] == "changed_tickers"
    assert "make readiness-snapshot" in rows[1]["Next Safest Action"]


def test_proof_completion_rows_show_ready_record_step():
    rows = build_proof_completion_rows(
        [
            {
                "Field": "final_outcome",
                "Validation Status": "ready",
                "Command Value": "still_blocked",
                "Reason": "Reviewed value is present.",
            }
        ],
        command_status="ready_to_record",
    )

    assert rows == [
        {
            "Step": "Record proof row",
            "Field": "proof_record_command",
            "Status": "ready_to_record",
            "Current Value": "required fields ready",
            "Next Safest Action": "Copy the reviewed proof-record command only after the operator has checked the source files and generated-artifact classification.",
        }
    ]


def test_proof_ledger_preview_row_matches_ledger_schema():
    outcome_rows = build_outcome_recorder_rows(
        {
            "Validation Result": "not_applicable_read_only_metric_review",
            "Preview Result": "reviewed metric blocker families",
            "Apply Result": "not_applicable_read_only_metric_review",
            "Changed Readiness Counts": "none",
            "Changed Tickers": "none",
            "Source Files": "metric queue output",
            "Generated Artifacts Review": "excluded generated CSV churn",
        },
        packet_missing=False,
        comparison_status="ok",
        comparison_changed_counts="none",
        comparison_changed_tickers=(),
        comparison_blocking_message="",
    )
    parts = build_proof_record_command_parts(
        {
            "Batch ID": "RB-9",
            "Lane": "Metric Readiness Review",
            "Scope": "AAA",
            "Review Date": "2026-06-14",
            "Dry Run Command": "make metric-readiness-board TOP_N=1",
            "Allowed Outcome": "still_blocked",
            "Validation Result": "not_applicable_read_only_metric_review",
            "Preview Result": "reviewed metric blocker families",
            "Apply Result": "not_applicable_read_only_metric_review",
            "Changed Readiness Counts": "none",
            "Changed Tickers": "none",
            "Source Files": "metric queue output",
            "Generated Artifacts Review": "excluded generated CSV churn",
        },
        proposed_tickers=("AAA",),
        comparison_status="ok",
        comparison_before_path=Path("data/reports/ticker_readiness_report.previous.csv"),
        comparison_after_path=Path("data/reports/ticker_readiness_report.csv"),
        comparison_changed_counts="none",
        comparison_changed_tickers=(),
        outcome_rows=outcome_rows,
    )

    preview = build_proof_ledger_preview_row(parts)

    assert tuple(preview) == BATCH_PROOF_COLUMNS
    assert preview["batch_id"] == "RB-9"
    assert preview["final_outcome"] == "still_blocked"
    assert preview["source_files"] == "metric queue output"
    assert preview["generated_artifacts_reviewed"] == "excluded generated CSV churn"


def test_proof_ledger_preview_rows_keep_copy_boundary_until_ready():
    parts = build_proof_record_command_parts(
        {
            "Batch ID": "RB-10",
            "Lane": "Metric Readiness Review",
            "Dry Run Command": "make metric-readiness-board TOP_N=1",
            "Allowed Outcome": "supported|still_blocked|skipped|excluded",
            "Validation Result": "<pass/fail/not_applicable>",
            "Preview Result": "<reviewed rows>",
            "Apply Result": "<not_run/applied/skipped>",
            "Changed Readiness Counts": "<from reviewed-batch-compare>",
            "Changed Tickers": "<from reviewed-batch-compare>",
            "Source Files": "metric queue output",
            "Generated Artifacts Review": "<kept evidence or excluded churn>",
        },
        proposed_tickers=("AAA",),
        comparison_status="missing_before",
        comparison_before_path=Path("data/reports/ticker_readiness_report.previous.csv"),
        comparison_after_path=Path("data/reports/ticker_readiness_report.csv"),
        comparison_changed_counts="not available",
        comparison_changed_tickers=(),
        outcome_rows=(),
    )
    validation_rows = validate_proof_record_command_parts(parts)

    rows = build_proof_ledger_preview_rows(parts, validation_rows)
    summary = build_proof_ledger_preview_summary(parts, validation_rows)
    final_outcome = [row for row in rows if row["Ledger Column"] == "final_outcome"][0]

    assert summary["Ledger Preview Status"] == "preview_only_not_record_ready"
    assert "do not record" in summary["Copy Boundary"].lower()
    assert final_outcome["Record Readiness"] == "invalid_outcome"
    assert "do not record" in final_outcome["Copy Boundary"].lower()


def test_proof_ledger_preview_summary_allows_ready_after_final_review():
    outcome_rows = build_outcome_recorder_rows(
        {
            "Validation Result": "not_applicable_read_only_metric_review",
            "Preview Result": "reviewed metric blocker families",
            "Apply Result": "not_applicable_read_only_metric_review",
            "Changed Readiness Counts": "none",
            "Changed Tickers": "none",
            "Source Files": "metric queue output",
            "Generated Artifacts Review": "excluded generated CSV churn",
        },
        packet_missing=False,
        comparison_status="ok",
        comparison_changed_counts="none",
        comparison_changed_tickers=(),
        comparison_blocking_message="",
    )
    parts = build_proof_record_command_parts(
        {
            "Batch ID": "RB-11",
            "Lane": "Metric Readiness Review",
            "Scope": "AAA",
            "Review Date": "2026-06-14",
            "Dry Run Command": "make metric-readiness-board TOP_N=1",
            "Allowed Outcome": "still_blocked",
            "Validation Result": "not_applicable_read_only_metric_review",
            "Preview Result": "reviewed metric blocker families",
            "Apply Result": "not_applicable_read_only_metric_review",
            "Changed Readiness Counts": "none",
            "Changed Tickers": "none",
            "Source Files": "metric queue output",
            "Generated Artifacts Review": "excluded generated CSV churn",
        },
        proposed_tickers=("AAA",),
        comparison_status="ok",
        comparison_before_path=Path("data/reports/ticker_readiness_report.previous.csv"),
        comparison_after_path=Path("data/reports/ticker_readiness_report.csv"),
        comparison_changed_counts="none",
        comparison_changed_tickers=(),
        outcome_rows=outcome_rows,
    )
    validation_rows = validate_proof_record_command_parts(parts)

    rows = build_proof_ledger_preview_rows(parts, validation_rows)
    summary = build_proof_ledger_preview_summary(parts, validation_rows)

    assert summary["Ledger Preview Status"] == "ready_after_final_review"
    assert summary["Column Count"] == str(len(BATCH_PROOF_COLUMNS))
    assert summary["Fields To Resolve"] == ""
    assert set(row["Copy Boundary"] for row in rows) == {
        "Preview only; copy command only after final source/artifact review."
    }
    assert "recommendation" in summary["Research Guardrail"]
