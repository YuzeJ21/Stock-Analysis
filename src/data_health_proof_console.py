"""Pure reviewed-batch proof console helpers for Data Health.

The dashboard owns Streamlit layout and file loading. This module owns the
proof-row, command-builder, completion-checklist, and ledger-preview cards and
frames so the proof workflow can be tested without rendering the dashboard.
"""

from __future__ import annotations

from src.reviewed_batch_proof import resolve_readiness_proof_profile

from typing import Any

import pandas as pd

from src.reviewed_batch_command_builder import (
    build_outcome_recorder_rows,
    build_proof_completion_rows,
    build_proof_ledger_preview_rows,
    build_proof_ledger_preview_summary,
    build_proof_record_command_parts,
    build_proof_record_command_summary,
    validate_proof_record_command_parts,
)


PROOF_OUTCOME_OPTIONS = (
    "auto_supported, human_reviewed_supported, candidate_context_only, still_blocked, skipped, or excluded"
)


def _format_missing(value: object, fallback: str = "Not available") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null", "nat"}:
        return fallback
    return text


def _compact_fragment(value: object, fallback: str = "Not available", *, max_chars: int = 180) -> str:
    text = _format_missing(value, fallback=fallback).replace("\n", " ").strip()
    if len(text) > max_chars:
        return text[: max(0, max_chars - 1)].rstrip() + "..."
    if text.endswith("..."):
        return text
    return text.rstrip(" .;:")


def _card_sentence(label: str, value: object) -> str:
    text = _format_missing(value, fallback="")
    return f"{label}: {text}." if text else ""


def packet_values(packet_frame: pd.DataFrame | None) -> dict[str, str]:
    if packet_frame is None or packet_frame.empty:
        return {}
    first = packet_frame.iloc[0]
    return {str(column): str(first.get(column, "") or "").strip() for column in packet_frame.columns}


def packet_tickers(packet_frame: pd.DataFrame | None) -> list[str]:
    if packet_frame is None or packet_frame.empty or "Proposed Ticker" not in packet_frame.columns:
        return []
    proposed = packet_frame.get("Proposed Ticker", pd.Series(dtype=object)).fillna("").astype(str)
    return [ticker for ticker in dict.fromkeys(proposed.str.strip()) if ticker]


def humanize_proof_fields(fields_to_fill: str) -> str:
    fields = [field.strip().replace("_", " ") for field in str(fields_to_fill or "").split(",") if field.strip()]
    if not fields:
        return "no required fields"
    return ", ".join(fields[:8]) + (f" +{len(fields) - 8} more" if len(fields) > 8 else "")


def latest_batch_packet_summary(
    packet_frame: pd.DataFrame | None,
    *,
    profile: str | None = None,
) -> dict[str, str]:
    selected_profile = resolve_readiness_proof_profile(profile)
    if packet_frame is None or packet_frame.empty:
        return {
            "state": "missing",
            "batch_id": "No packet",
            "lane": "No reviewed batch packet",
            "scope": "Run a reviewed batch packet before recording proof.",
            "freshness": "unknown",
            "row_count": "0",
            "dry_run_command": "DRY_RUN=1 make reviewed-batch LANE=prices TOP_N=10",
            "comparison_command": f"make reviewed-batch-compare PROFILE={selected_profile} LANE=prices BATCH_ID=<reviewed_batch_id> REVIEW_DATE=<yyyy-mm-dd>",
            "proof_record_command": "make reviewed-batch-proof-record",
            "source_files": "not available",
            "generated_artifacts_reviewed": "not available",
            "allowed_outcome": "auto_supported|human_reviewed_supported|candidate_context_only|still_blocked|skipped|excluded",
        }
    first = packet_frame.iloc[0]
    proposed = packet_frame.get("Proposed Ticker", pd.Series(dtype=object)).fillna("").astype(str)
    unique_tickers = [ticker for ticker in dict.fromkeys(proposed.str.strip()) if ticker]
    return {
        "state": "present",
        "batch_id": _format_missing(first.get("Batch ID"), "latest packet"),
        "lane": _format_missing(first.get("Lane"), "Reviewed batch"),
        "scope": _compact_fragment(_format_missing(first.get("Scope"), "reviewed scope"), max_chars=180),
        "freshness": _compact_fragment(_format_missing(first.get("Freshness"), "freshness unknown"), max_chars=150),
        "row_count": str(len(packet_frame)),
        "ticker_count": str(len(unique_tickers)),
        "dry_run_command": _format_missing(first.get("Dry Run Command"), "DRY_RUN=1 make reviewed-batch LANE=prices TOP_N=10"),
        "comparison_command": _format_missing(first.get("Comparison Command"), f"make reviewed-batch-compare PROFILE={selected_profile} LANE=prices BATCH_ID=<reviewed_batch_id> REVIEW_DATE=<yyyy-mm-dd>"),
        "proof_record_command": _format_missing(first.get("Proof Record Scaffold"), "make reviewed-batch-proof-record"),
        "source_files": _compact_fragment(_format_missing(first.get("Source Files"), "review source files"), max_chars=170),
        "generated_artifacts_reviewed": _compact_fragment(
            _format_missing(first.get("Generated Artifacts Review"), "classify generated artifacts before staging"),
            max_chars=170,
        ),
        "allowed_outcome": _format_missing(
            first.get("Allowed Outcome"),
            "auto_supported|human_reviewed_supported|candidate_context_only|still_blocked|skipped|excluded",
        ),
    }


def reviewed_batch_outcome_recorder_frame(packet_frame: pd.DataFrame | None, comparison: Any) -> pd.DataFrame:
    selected_profile = resolve_readiness_proof_profile(getattr(comparison, "profile", None))
    rows = build_outcome_recorder_rows(
        packet_values(packet_frame),
        profile=selected_profile,
        packet_missing=packet_frame is None or packet_frame.empty,
        comparison_status=comparison.status,
        comparison_changed_counts=comparison.changed_readiness_counts,
        comparison_changed_tickers=comparison.changed_tickers,
        comparison_blocking_message=comparison.blocking_message,
    )
    for row in rows:
        row["Current Value"] = _compact_fragment(row["Current Value"], max_chars=190)
        row["Copy From"] = _compact_fragment(row["Copy From"], max_chars=190)
    return pd.DataFrame(rows)


def reviewed_batch_outcome_recorder_cards(packet_frame: pd.DataFrame | None, comparison: Any) -> list[dict[str, object]]:
    frame = reviewed_batch_outcome_recorder_frame(packet_frame, comparison)
    missing_frame = frame[frame["Status"].astype(str).str.contains("missing|blocked", case=False, na=False)]
    missing_fields = [str(field) for field in missing_frame["Field"].tolist() if field != "reviewed_batch_packet"]
    summary = latest_batch_packet_summary(packet_frame, profile=getattr(comparison, "profile", None))
    if packet_frame is None or packet_frame.empty:
        return [
            {
                "kicker": "OUTCOME RECORDER",
                "title": "Proof row blocked: packet missing",
                "body": f"Generate or review the latest batch packet before recording {PROOF_OUTCOME_OPTIONS}.",
                "badges": ["blocked", "packet first"],
                "command": summary["dry_run_command"],
            }
        ]
    if missing_fields:
        visible_missing = ", ".join(missing_fields[:5])
        overflow = f" +{len(missing_fields) - 5} more" if len(missing_fields) > 5 else ""
        return [
            {
                "kicker": "OUTCOME RECORDER",
                "title": f"{len(missing_fields)} proof field(s) still missing",
                "body": (
                    f"Missing before proof row record: {visible_missing}{overflow}. "
                    "Keep the outcome open until validation, preview, apply decision, changed readiness proof, source files, and generated-artifact review are recorded."
                ),
                "badges": ["review required", "no implicit outcome"],
                "command": summary["proof_record_command"],
            }
        ]
    return [
        {
            "kicker": "OUTCOME RECORDER",
            "title": "Proof row fields ready to record",
            "body": (
                f"Required proof-row fields have reviewed values. Record only {PROOF_OUTCOME_OPTIONS}; "
                "auto_supported means deterministic gates passed, human_reviewed_supported means reviewed evidence passed, and this remains data-readiness proof, not a research recommendation."
            ),
            "badges": ["ready_to_record", "research-only"],
            "command": summary["proof_record_command"],
        }
    ]


def proof_record_command_parts(packet_frame: pd.DataFrame | None, comparison: Any, outcome_frame: pd.DataFrame) -> list[dict[str, str]]:
    return build_proof_record_command_parts(
        packet_values(packet_frame),
        proposed_tickers=packet_tickers(packet_frame),
        comparison_status=comparison.status,
        comparison_before_path=comparison.before_path,
        comparison_after_path=comparison.after_path,
        comparison_changed_counts=comparison.changed_readiness_counts,
        comparison_changed_tickers=comparison.changed_tickers,
        outcome_rows=outcome_frame.to_dict(orient="records"),
    )


def reviewed_batch_proof_record_command_frame(packet_frame: pd.DataFrame | None, comparison: Any) -> pd.DataFrame:
    outcome_frame = reviewed_batch_outcome_recorder_frame(packet_frame, comparison)
    rows = proof_record_command_parts(packet_frame, comparison, outcome_frame)
    summary = build_proof_record_command_summary(rows)
    return pd.DataFrame(
        [
            {
                "Command Status": summary["Command Status"],
                "Copy Command": summary["Copy Command"],
                "Fields To Fill": summary["Fields To Fill"],
                "Manual Fields": summary["Manual Fields"],
                "Research Guardrail": summary["Research Guardrail"],
            }
        ]
    )


def reviewed_batch_proof_record_command_arguments_frame(packet_frame: pd.DataFrame | None, comparison: Any) -> pd.DataFrame:
    outcome_frame = reviewed_batch_outcome_recorder_frame(packet_frame, comparison)
    return pd.DataFrame(proof_record_command_parts(packet_frame, comparison, outcome_frame))


def reviewed_batch_proof_record_validation_frame(packet_frame: pd.DataFrame | None, comparison: Any) -> pd.DataFrame:
    outcome_frame = reviewed_batch_outcome_recorder_frame(packet_frame, comparison)
    command_parts = proof_record_command_parts(packet_frame, comparison, outcome_frame)
    return pd.DataFrame(validate_proof_record_command_parts(command_parts))


def reviewed_batch_proof_completion_frame(packet_frame: pd.DataFrame | None, comparison: Any) -> pd.DataFrame:
    command_frame = reviewed_batch_proof_record_command_frame(packet_frame, comparison)
    validation_frame = reviewed_batch_proof_record_validation_frame(packet_frame, comparison)
    status = (
        str(command_frame.iloc[0].get("Command Status", "needs_field_fills"))
        if not command_frame.empty
        else "needs_field_fills"
    )
    rows = build_proof_completion_rows(
        validation_frame.to_dict(orient="records"),
        command_status=status,
        profile=getattr(comparison, "profile", None),
    )
    for row in rows:
        row["Current Value"] = _compact_fragment(row["Current Value"], max_chars=180)
        row["Next Safest Action"] = _compact_fragment(row["Next Safest Action"], max_chars=220)
    return pd.DataFrame(rows)


def reviewed_batch_proof_ledger_preview_frame(packet_frame: pd.DataFrame | None, comparison: Any) -> pd.DataFrame:
    outcome_frame = reviewed_batch_outcome_recorder_frame(packet_frame, comparison)
    command_parts = proof_record_command_parts(packet_frame, comparison, outcome_frame)
    validation_rows = validate_proof_record_command_parts(command_parts)
    summary = build_proof_record_command_summary(command_parts)
    rows = build_proof_ledger_preview_rows(
        command_parts,
        validation_rows,
        command_status=summary["Command Status"],
    )
    for row in rows:
        row["Preview Value"] = _compact_fragment(row["Preview Value"], max_chars=180)
        row["Copy Boundary"] = _compact_fragment(row["Copy Boundary"], max_chars=180)
    return pd.DataFrame(rows)


def reviewed_batch_proof_ledger_preview_cards(packet_frame: pd.DataFrame | None, comparison: Any) -> list[dict[str, object]]:
    outcome_frame = reviewed_batch_outcome_recorder_frame(packet_frame, comparison)
    command_parts = proof_record_command_parts(packet_frame, comparison, outcome_frame)
    validation_rows = validate_proof_record_command_parts(command_parts)
    command_summary = build_proof_record_command_summary(command_parts)
    ledger_summary = build_proof_ledger_preview_summary(command_parts, validation_rows)
    if ledger_summary["Command Status"] == "ready_to_record":
        title = "Ledger row preview ready after final review"
        body = (
            f"{ledger_summary['Column Count']} ledger columns are populated for "
            f"{ledger_summary['Batch ID']} / {ledger_summary['Lane']}. "
            "Copy the command only after source files and generated artifacts are reviewed."
        )
        badges = ["preview", "final review"]
    else:
        title = "Ledger row preview is not record-ready"
        fields = humanize_proof_fields(ledger_summary["Fields To Resolve"])
        body = (
            f"Preview shows the exact row shape, but still needs: {_compact_fragment(fields, max_chars=170)}. "
            "Do not record until these fields are resolved."
        )
        badges = [ledger_summary["Command Status"].replace("_", " "), "preview only"]
    return [
        {
            "kicker": "LEDGER ROW PREVIEW",
            "title": title,
            "body": body,
            "badges": badges,
            "command": command_summary["Copy Command"],
        }
    ]


def reviewed_batch_proof_record_command_cards(packet_frame: pd.DataFrame | None, comparison: Any) -> list[dict[str, object]]:
    command_frame = reviewed_batch_proof_record_command_frame(packet_frame, comparison)
    first = command_frame.iloc[0] if not command_frame.empty else pd.Series(dtype=object)
    status = str(first.get("Command Status", "needs_field_fills"))
    fields_to_fill = str(first.get("Fields To Fill", "") or "").strip()
    manual_fields = str(first.get("Manual Fields", "") or "").strip()
    manual_copy = humanize_proof_fields(manual_fields)
    if status == "ready_to_record":
        title = "Proof-record command ready"
        body = (
            f"Required proof fields are valid. Manual fields still visible: {manual_copy}. "
            "Record only the reviewed data-readiness outcome."
        )
        badges = ["ready to record", "reviewed values"]
    elif status == "blocked_by_snapshot_gate":
        title = "Proof-record command blocked by snapshot gate"
        body = (
            "Run the required readiness snapshot and comparison before recording changed readiness proof. "
            f"Still blocked: {_compact_fragment(humanize_proof_fields(fields_to_fill), max_chars=190)}."
        )
        badges = ["snapshot gate", "blocked"]
    elif status == "invalid_outcome":
        title = "Proof-record command has invalid outcome"
        body = (
            "Set final outcome to exactly supported, candidate_context_only, still_blocked, skipped, or excluded before recording proof. "
            f"Also check: {_compact_fragment(humanize_proof_fields(fields_to_fill), max_chars=190)}."
        )
        badges = ["invalid outcome", "review required"]
    else:
        title = "Proof-record command needs field fills"
        body = (
            f"Fill or confirm: {_compact_fragment(humanize_proof_fields(fields_to_fill), max_chars=190)}. "
            f"Manual fields visible: {manual_copy}. "
            "The command keeps unresolved values as placeholders so no proof row is recorded by accident."
        )
        badges = ["needs fields", "placeholders visible"]
    return [
        {
            "kicker": "PROOF COMMAND BUILDER",
            "title": title,
            "body": body,
            "badges": badges,
            "command": str(first.get("Copy Command", "make reviewed-batch-proof-record")),
        }
    ]


def reviewed_batch_proof_completion_cards(packet_frame: pd.DataFrame | None, comparison: Any) -> list[dict[str, object]]:
    command_frame = reviewed_batch_proof_record_command_frame(packet_frame, comparison)
    completion_frame = reviewed_batch_proof_completion_frame(packet_frame, comparison)
    first = command_frame.iloc[0] if not command_frame.empty else pd.Series(dtype=object)
    status = str(first.get("Command Status", "needs_field_fills"))
    command = str(first.get("Copy Command", "make reviewed-batch-proof-record"))
    if status == "ready_to_record":
        title = "Proof can be recorded after final review"
        body = "Required proof fields are ready. Check source files and generated-artifact classification, then copy the reviewed command."
        badges = ["ready to record", "final review"]
    else:
        blocked_count = len(completion_frame)
        next_action = (
            str(completion_frame.iloc[0].get("Next Safest Action", "Fill the missing reviewed proof fields."))
            if not completion_frame.empty
            else "Fill the missing reviewed proof fields."
        )
        title = f"{blocked_count} proof item(s) to finish"
        body = f"Start here: {next_action} Details stay below so the operator does not need to read the full validation table first."
        badges = [status.replace("_", " "), "finish checklist"]
    return [
        {
            "kicker": "FINISH THIS PROOF",
            "title": title,
            "body": body,
            "badges": badges,
            "command": command,
        }
    ]


def reviewed_batch_proof_loop_cards(packet_frame: pd.DataFrame | None, comparison: Any) -> list[dict[str, object]]:
    selected_profile = resolve_readiness_proof_profile(getattr(comparison, "profile", None))
    summary = latest_batch_packet_summary(packet_frame, profile=selected_profile)
    if comparison.status == "ok":
        comparison_title = f"{comparison.changed_count:,} changed ticker(s)"
        comparison_body = (
            f"{_card_sentence('Changed counts', _compact_fragment(comparison.changed_readiness_counts, max_chars=190))} "
            "Use this as readiness proof only after source review and generated-artifact classification."
        )
        comparison_command = summary["comparison_command"]
        comparison_badges = [comparison.freshness_status, "read-only compare"]
    else:
        comparison_title = "Comparison blocked"
        comparison_body = (
            f"{comparison.blocking_message} Keep the proof row open until saved before/after readiness snapshots exist."
        )
        comparison_command = f"make readiness-snapshot PROFILE={selected_profile}"
        comparison_badges = [comparison.status, "snapshot first"]
    return [
        {
            "kicker": "LATEST PACKET",
            "title": f"{summary['lane']}: {summary['batch_id']}",
            "body": (
                f"Scope: {summary['scope']}. Rows: {summary['row_count']}; tickers: {summary.get('ticker_count', '0')}. "
                f"Freshness: {summary['freshness']}. The packet is copy-only evidence, not an analysis result."
            ),
            "badges": [summary["state"], "packet"],
            "command": summary["dry_run_command"],
        },
        {
            "kicker": "COMPARISON STATUS",
            "title": comparison_title,
            "body": comparison_body,
            "badges": comparison_badges,
            "command": comparison_command,
        },
        {
            "kicker": "PROOF RECORD",
            "title": "Outcome scaffold ready",
            "body": (
                f"Record {PROOF_OUTCOME_OPTIONS} only after validation, preview/apply decision, "
                f"readiness comparison, source files ({summary['source_files']}), and artifact review ({summary['generated_artifacts_reviewed']}). "
                "auto_supported is deterministic gate proof; human_reviewed_supported is reviewed evidence proof."
            ),
            "badges": ["review required", "durable ledger"],
            "command": summary["proof_record_command"],
        },
    ]


def reviewed_batch_proof_loop_frame(packet_frame: pd.DataFrame | None, comparison: Any) -> pd.DataFrame:
    selected_profile = resolve_readiness_proof_profile(getattr(comparison, "profile", None))
    summary = latest_batch_packet_summary(packet_frame, profile=selected_profile)
    return pd.DataFrame(
        [
            {
                "Loop Step": "1. Latest packet",
                "Status": summary["state"],
                "What To Review": f"{summary['lane']} / {summary['scope']}",
                "Copy Command": summary["dry_run_command"],
                "Stop If": "packet is missing, stale, or scope is not reviewed",
            },
            {
                "Loop Step": "2. Before/after comparison",
                "Status": comparison.status,
                "What To Review": (
                    comparison.changed_readiness_counts
                    if comparison.status == "ok"
                    else comparison.blocking_message
                ),
                "Copy Command": summary["comparison_command"] if comparison.status == "ok" else f"make readiness-snapshot PROFILE={selected_profile}",
                "Stop If": "saved readiness snapshots are missing or source files changed without refresh",
            },
            {
                "Loop Step": "3. Proof record scaffold",
                "Status": "review_required",
                "What To Review": f"source files: {summary['source_files']}; artifacts: {summary['generated_artifacts_reviewed']}",
                "Copy Command": summary["proof_record_command"],
                "Stop If": "source proof, validation, preview/apply decision, or generated-artifact classification is incomplete",
            },
        ]
    )
