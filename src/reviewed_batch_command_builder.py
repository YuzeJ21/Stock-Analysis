"""Reviewed batch proof command-builder helpers.

These helpers keep reviewed-batch proof recording logic out of the Streamlit
dashboard. They only build copy-ready command text and field-status rows; they
do not refresh data, apply imports, or record proof rows.
"""

from __future__ import annotations

import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from src.reviewed_batch_proof import BATCH_OUTCOMES, BATCH_PROOF_COLUMNS


@dataclass(frozen=True)
class OutcomeRequiredField:
    field: str
    label: str
    requirement: str
    source: str


@dataclass(frozen=True)
class ProofRecordCommandField:
    field: str
    argument: str
    packet_label: str
    fallback: str


REVIEWED_BATCH_OUTCOME_REQUIRED_FIELDS: tuple[OutcomeRequiredField, ...] = (
    OutcomeRequiredField(
        "validation_result",
        "Validation Result",
        "Copy the validator status or not_applicable_read_only only after the lane gate is reviewed.",
        "validate gate output",
    ),
    OutcomeRequiredField(
        "preview_result",
        "Preview Result",
        "Copy the preview and rejected-row review result before recording any outcome.",
        "preview and rejected-row review",
    ),
    OutcomeRequiredField(
        "apply_result",
        "Apply Result",
        "Record applied, skipped, or not_applicable_read_only; never leave the apply decision implicit.",
        "apply decision",
    ),
    OutcomeRequiredField(
        "changed_readiness_counts",
        "Changed Readiness Counts",
        "Copy the before/after readiness count delta from the reviewed batch comparison.",
        "make reviewed-batch-compare",
    ),
    OutcomeRequiredField(
        "changed_tickers",
        "Changed Tickers",
        "Copy changed ticker evidence or record none after comparing snapshots.",
        "make reviewed-batch-compare",
    ),
    OutcomeRequiredField(
        "source_files",
        "Source Files",
        "List the reviewed source files or read-only console output used as proof.",
        "reviewed source files",
    ),
    OutcomeRequiredField(
        "generated_artifacts_reviewed",
        "Generated Artifacts Review",
        "Classify kept evidence versus excluded generated churn before staging.",
        "artifact hygiene review",
    ),
)


PROOF_RECORD_COMMAND_FIELDS: tuple[ProofRecordCommandField, ...] = (
    ProofRecordCommandField("batch_id", "BATCH_ID", "Batch ID", "latest_batch"),
    ProofRecordCommandField("reviewer", "REVIEWER", "Reviewer", "local reviewer"),
    ProofRecordCommandField("lane", "LANE", "Lane", "reviewed_lane"),
    ProofRecordCommandField("scope", "SCOPE", "Scope", "reviewed batch scope"),
    ProofRecordCommandField("tickers", "TICKERS", "", "-"),
    ProofRecordCommandField("review_date", "REVIEW_DATE", "Review Date", "<yyyy-mm-dd>"),
    ProofRecordCommandField("final_outcome", "FINAL_OUTCOME", "Allowed Outcome", "<supported|still_blocked|skipped|excluded>"),
    ProofRecordCommandField("command_run", "COMMAND_RUN", "Dry Run Command", "<exact reviewed command>"),
    ProofRecordCommandField("validation_result", "VALIDATION_RESULT", "Validation Result", "<pass/fail/not_applicable>"),
    ProofRecordCommandField("preview_result", "PREVIEW_RESULT", "Preview Result", "<reviewed/no unexpected rows/not_applicable>"),
    ProofRecordCommandField("apply_result", "APPLY_RESULT", "Apply Result", "<not_run/applied/skipped/not_applicable>"),
    ProofRecordCommandField("pre_run_readiness_snapshot", "PRE_RUN_READINESS_SNAPSHOT", "Pre Run Readiness Snapshot", "not recorded"),
    ProofRecordCommandField("post_run_readiness_snapshot", "POST_RUN_READINESS_SNAPSHOT", "Post Run Readiness Snapshot", "not recorded"),
    ProofRecordCommandField("changed_readiness_counts", "CHANGED_READINESS_COUNTS", "Changed Readiness Counts", "<from reviewed-batch-compare>"),
    ProofRecordCommandField("changed_tickers", "CHANGED_TICKERS", "Changed Tickers", "<from reviewed-batch-compare>"),
    ProofRecordCommandField("source_files", "SOURCE_FILES", "Source Files", "<reviewed source files>"),
    ProofRecordCommandField("generated_artifacts_reviewed", "GENERATED_ARTIFACTS_REVIEWED", "Generated Artifacts Review", "<kept evidence or excluded churn>"),
    ProofRecordCommandField("notes", "NOTES", "Notes", "<review notes>"),
)


REQUIRED_PROOF_RECORD_FIELDS: tuple[str, ...] = (
    "batch_id",
    "lane",
    "review_date",
    "final_outcome",
    "command_run",
    "validation_result",
    "preview_result",
    "apply_result",
    "changed_readiness_counts",
    "changed_tickers",
    "source_files",
    "generated_artifacts_reviewed",
)

VISIBLE_MANUAL_PROOF_FIELDS: tuple[str, ...] = ("reviewer", "notes")


PROOF_COMPLETION_ACTIONS: dict[str, str] = {
    "batch_id": "Regenerate or review the latest reviewed batch packet so the batch id is explicit.",
    "lane": "Confirm the selected readiness lane from the reviewed batch packet.",
    "review_date": "Fill REVIEW_DATE with the local review date in yyyy-mm-dd format.",
    "final_outcome": "Set FINAL_OUTCOME to supported, still_blocked, skipped, or excluded.",
    "command_run": "Paste the exact reviewed command that was run or reviewed.",
    "validation_result": "Copy the validator result, or record not_applicable_read_only for read-only lanes.",
    "preview_result": "Copy the preview and rejected-row review result before recording proof.",
    "apply_result": "Record applied, skipped, or not_applicable_read_only after the apply gate is reviewed.",
    "changed_readiness_counts": "Run make readiness-snapshot and make reviewed-batch-compare, then copy the count delta or none.",
    "changed_tickers": "Run make reviewed-batch-compare, then copy changed tickers or none.",
    "source_files": "List reviewed source files or read-only command output used as proof.",
    "generated_artifacts_reviewed": "Classify generated artifacts as kept evidence or excluded churn before recording proof.",
}


def is_placeholder_value(value: object) -> bool:
    text = str(value or "").strip()
    lowered = text.lower()
    if not text or lowered in {"-", "na", "n/a", "none", "not available", "unknown"}:
        return True
    if lowered.startswith("<") and lowered.endswith(">"):
        return True
    if "<" in lowered and ">" in lowered:
        return True
    return "|" in lowered and any(token in lowered for token in ("supported", "still_blocked", "skipped", "excluded"))


def shell_assignment(name: str, value: object) -> str:
    return f"{name}={shlex.quote(str(value or '').strip())}"


def _is_reviewed_no_change_value(field: str, value: str, source_status: str) -> bool:
    return (
        field in {"changed_readiness_counts", "changed_tickers"}
        and value.strip().lower().startswith("none")
        and source_status in {"filled_from_review", "filled_from_comparison"}
    )


def build_outcome_recorder_rows(
    packet_values: Mapping[str, str],
    *,
    packet_missing: bool,
    comparison_status: str,
    comparison_changed_counts: str,
    comparison_changed_tickers: Sequence[str],
    comparison_blocking_message: str,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in REVIEWED_BATCH_OUTCOME_REQUIRED_FIELDS:
        value = str(packet_values.get(item.label, "") or "").strip()
        display_value = value if value else "not recorded"
        status = "ready"
        next_step = "Reviewed value is present."
        copy_from = item.source
        if item.field in {"changed_readiness_counts", "changed_tickers"} and comparison_status != "ok":
            status = "blocked_by_snapshot_gate"
            display_value = display_value if value else "comparison not available"
            next_step = comparison_blocking_message or "Run the snapshot comparison before recording readiness proof."
            copy_from = "make readiness-snapshot, then make reviewed-batch-compare"
        elif item.field in {"changed_readiness_counts", "changed_tickers"} and value.lower().startswith("none"):
            next_step = "Reviewed no-change value is present."
        elif is_placeholder_value(value):
            status = "missing_from_record"
            next_step = item.requirement
            if item.field == "changed_readiness_counts" and comparison_status == "ok":
                copy_from = comparison_changed_counts or "none"
            elif item.field == "changed_tickers" and comparison_status == "ok":
                copy_from = ", ".join(comparison_changed_tickers) if comparison_changed_tickers else "none from comparison"
        rows.append(
            {
                "Field": item.field,
                "Label": item.label,
                "Status": status,
                "Current Value": display_value,
                "Required Before Record": next_step,
                "Copy From": copy_from,
            }
        )
    if packet_missing:
        rows.insert(
            0,
            {
                "Field": "reviewed_batch_packet",
                "Label": "Reviewed Batch Packet",
                "Status": "blocked_missing_packet",
                "Current Value": "not available",
                "Required Before Record": "Generate or review a packet before opening a proof row.",
                "Copy From": "DRY_RUN=1 make reviewed-batch LANE=prices TOP_N=10",
            },
        )
    return rows


def build_proof_record_command_parts(
    packet_values: Mapping[str, str],
    *,
    proposed_tickers: Sequence[str],
    comparison_status: str,
    comparison_before_path: Path | str,
    comparison_after_path: Path | str,
    comparison_changed_counts: str,
    comparison_changed_tickers: Sequence[str],
    outcome_rows: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    outcome_by_field = {str(row.get("Field", "")): str(row.get("Status", "")) for row in outcome_rows}
    values: dict[str, str] = {}
    for item in PROOF_RECORD_COMMAND_FIELDS:
        packet_value = str(packet_values.get(item.packet_label, "") or "").strip() if item.packet_label else ""
        values[item.field] = packet_value or item.fallback
    unique_tickers = [ticker for ticker in dict.fromkeys(str(t).strip() for t in proposed_tickers) if ticker]
    if unique_tickers:
        values["tickers"] = ",".join(unique_tickers)
    if comparison_status == "ok":
        values["pre_run_readiness_snapshot"] = str(comparison_before_path)
        values["post_run_readiness_snapshot"] = str(comparison_after_path)
        if is_placeholder_value(values["changed_readiness_counts"]):
            values["changed_readiness_counts"] = comparison_changed_counts or "none"
        if is_placeholder_value(values["changed_tickers"]):
            values["changed_tickers"] = ", ".join(comparison_changed_tickers) if comparison_changed_tickers else "none"
    rows: list[dict[str, str]] = []
    for item in PROOF_RECORD_COMMAND_FIELDS:
        value = values[item.field]
        status = outcome_by_field.get(item.field, "manual_fill")
        if item.field in {"batch_id", "lane", "scope", "tickers", "command_run"} and not is_placeholder_value(value):
            status = "filled_from_packet"
        elif item.field in {"pre_run_readiness_snapshot", "post_run_readiness_snapshot"} and comparison_status == "ok":
            status = "filled_from_comparison"
        elif item.field in {"reviewer", "notes"}:
            status = "manual_fill"
        elif status == "ready":
            status = "filled_from_review"
        elif status in {"missing_from_record", "blocked_by_snapshot_gate"}:
            status = status
        elif not is_placeholder_value(value):
            status = "filled_from_review"
        elif is_placeholder_value(value):
            status = "manual_fill"
        rows.append(
            {
                "Field": item.field,
                "Argument": item.argument,
                "Status": status,
                "Command Value": value,
            }
        )
    return rows


def build_proof_record_command_summary(command_parts: Sequence[Mapping[str, str]]) -> dict[str, str]:
    assignments = [shell_assignment(str(row.get("Argument", "")), row.get("Command Value", "")) for row in command_parts]
    validation_rows = validate_proof_record_command_parts(command_parts)
    status = proof_record_validation_status(validation_rows)
    fields_to_fill = [row["Field"] for row in validation_rows if row["Validation Status"] != "ready"]
    manual_fields = [
        str(row.get("Field", ""))
        for row in command_parts
        if str(row.get("Field", "")) in VISIBLE_MANUAL_PROOF_FIELDS and str(row.get("Status", "")) == "manual_fill"
    ]
    return {
        "Command Status": status,
        "Copy Command": "make reviewed-batch-proof-record " + " ".join(assignments),
        "Fields To Fill": ", ".join(fields_to_fill),
        "Manual Fields": ", ".join(manual_fields),
        "Research Guardrail": "Records data-readiness proof only; no recommendation, broker, order routing, or auto-trading action.",
    }


def validate_proof_record_command_parts(command_parts: Sequence[Mapping[str, str]]) -> list[dict[str, str]]:
    by_field = {str(row.get("Field", "")): row for row in command_parts}
    rows: list[dict[str, str]] = []
    for field in REQUIRED_PROOF_RECORD_FIELDS:
        part = by_field.get(field, {})
        value = str(part.get("Command Value", "") or "").strip()
        source_status = str(part.get("Status", "") or "").strip()
        validation_status = "ready"
        reason = "Reviewed value is present."
        if field == "final_outcome":
            if value not in BATCH_OUTCOMES:
                validation_status = "invalid_outcome"
                reason = "FINAL_OUTCOME must be exactly one of supported, still_blocked, skipped, or excluded."
        elif source_status == "blocked_by_snapshot_gate":
            validation_status = "blocked_by_snapshot_gate"
            reason = "Snapshot comparison is required before this proof field can be trusted."
        elif source_status in {"missing_from_record", "manual_fill"} or (
            is_placeholder_value(value) and not _is_reviewed_no_change_value(field, value, source_status)
        ):
            validation_status = "missing_required"
            reason = "Required proof field still contains a placeholder or missing value."
        rows.append(
            {
                "Field": field,
                "Validation Status": validation_status,
                "Command Value": value if value else "not recorded",
                "Reason": reason,
            }
        )
    return rows


def proof_record_validation_status(validation_rows: Sequence[Mapping[str, str]]) -> str:
    statuses = {str(row.get("Validation Status", "")) for row in validation_rows}
    if "blocked_by_snapshot_gate" in statuses:
        return "blocked_by_snapshot_gate"
    if "invalid_outcome" in statuses:
        return "invalid_outcome"
    if "missing_required" in statuses:
        return "needs_field_fills"
    return "ready_to_record"


def build_proof_completion_rows(
    validation_rows: Sequence[Mapping[str, str]],
    *,
    command_status: str | None = None,
) -> list[dict[str, str]]:
    status = command_status or proof_record_validation_status(validation_rows)
    blocked_rows = [row for row in validation_rows if str(row.get("Validation Status", "")) != "ready"]
    if not blocked_rows:
        return [
            {
                "Step": "Record proof row",
                "Field": "proof_record_command",
                "Status": status,
                "Current Value": "required fields ready",
                "Next Safest Action": "Copy the reviewed proof-record command only after the operator has checked the source files and generated-artifact classification.",
            }
        ]
    rows: list[dict[str, str]] = []
    for row in blocked_rows:
        field = str(row.get("Field", "") or "").strip()
        validation_status = str(row.get("Validation Status", "") or "").strip()
        value = str(row.get("Command Value", "") or "").strip()
        action = PROOF_COMPLETION_ACTIONS.get(field, "Fill this reviewed proof field before recording the batch outcome.")
        if validation_status == "blocked_by_snapshot_gate":
            action = "Run make readiness-snapshot, then make reviewed-batch-compare before copying changed readiness proof."
        elif validation_status == "invalid_outcome":
            action = "Set FINAL_OUTCOME exactly to supported, still_blocked, skipped, or excluded."
        rows.append(
            {
                "Step": f"Fill {field}",
                "Field": field,
                "Status": validation_status,
                "Current Value": value if value else "not recorded",
                "Next Safest Action": action,
            }
        )
    return rows


def build_proof_ledger_preview_row(command_parts: Sequence[Mapping[str, str]]) -> dict[str, str]:
    by_field = {
        str(row.get("Field", "") or "").strip(): str(row.get("Command Value", "") or "").strip()
        for row in command_parts
    }
    return {column: by_field.get(column, "") for column in BATCH_PROOF_COLUMNS}


def build_proof_ledger_preview_rows(
    command_parts: Sequence[Mapping[str, str]],
    validation_rows: Sequence[Mapping[str, str]],
    *,
    command_status: str | None = None,
) -> list[dict[str, str]]:
    status = command_status or proof_record_validation_status(validation_rows)
    ledger_row = build_proof_ledger_preview_row(command_parts)
    validation_by_field = {
        str(row.get("Field", "") or "").strip(): str(row.get("Validation Status", "") or "").strip()
        for row in validation_rows
    }
    command_status_by_field = {
        str(row.get("Field", "") or "").strip(): str(row.get("Status", "") or "").strip()
        for row in command_parts
    }
    copy_boundary = (
        "Preview only; copy command only after final source/artifact review."
        if status == "ready_to_record"
        else "Preview only; do not record until missing or blocked fields are resolved."
    )
    rows: list[dict[str, str]] = []
    for column in BATCH_PROOF_COLUMNS:
        field_status = validation_by_field.get(column) or command_status_by_field.get(column) or "manual_review"
        rows.append(
            {
                "Ledger Column": column,
                "Preview Value": ledger_row[column] or "not recorded",
                "Record Readiness": field_status,
                "Copy Boundary": copy_boundary,
            }
        )
    return rows


def build_proof_ledger_preview_summary(
    command_parts: Sequence[Mapping[str, str]],
    validation_rows: Sequence[Mapping[str, str]],
) -> dict[str, str]:
    status = proof_record_validation_status(validation_rows)
    ledger_row = build_proof_ledger_preview_row(command_parts)
    blocked_fields = [
        str(row.get("Field", ""))
        for row in validation_rows
        if str(row.get("Validation Status", "")) != "ready"
    ]
    if status == "ready_to_record":
        preview_status = "ready_after_final_review"
        boundary = "Copy the proof-record command only after confirming source files and generated-artifact review."
    else:
        preview_status = "preview_only_not_record_ready"
        boundary = "Do not record this row yet; resolve missing, invalid, or snapshot-blocked fields first."
    return {
        "Command Status": status,
        "Ledger Preview Status": preview_status,
        "Batch ID": ledger_row.get("batch_id", ""),
        "Lane": ledger_row.get("lane", ""),
        "Final Outcome": ledger_row.get("final_outcome", ""),
        "Fields To Resolve": ", ".join(blocked_fields),
        "Column Count": str(len(BATCH_PROOF_COLUMNS)),
        "Copy Boundary": boundary,
        "Research Guardrail": "Preview records data-readiness proof only; no recommendation, broker, order routing, or auto-trading action.",
    }
