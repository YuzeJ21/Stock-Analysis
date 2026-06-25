"""Pure reviewed-batch execution console helpers for Data Health.

The Streamlit dashboard should render cards and frames, while this module owns
the copy-only batch workflow decisions: lane routing, snapshot gates, apply
guards, execution cards, and checklist rows.
"""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

from src.data_health_console import DATA_HEALTH_BATCH_LANES, DATA_HEALTH_OPERATOR_LANES


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


def batch_lane_for_operator(selected_lane_key: str) -> str:
    return DATA_HEALTH_BATCH_LANES.get(str(selected_lane_key or "").strip().lower(), "prices")


def batch_source_requirement(lane: str) -> str:
    lane = str(lane or "").strip().lower()
    if lane == "prices":
        return "Requires local price files or reviewed free-provider rows; start with a dry-run and keep price imports validate -> preview -> apply."
    if lane == "fundamentals":
        return "Requires trusted SEC-stageable or manually reviewed fundamentals rows; DCF stays blocked until required rows pass validate -> preview -> apply."
    if lane == "peers":
        return "Requires source-backed peer mappings plus trusted peer price, fundamentals, or market-context inputs; sector fallback is context only."
    if lane == "metrics":
        return "Read-only metric triage; missing SPY/QQQ, price, fundamentals, market-cap, or peer inputs must route back to the source lane."
    if lane == "optional_context":
        return "Manual/trusted-local only; earnings and analyst-estimate context stays locked until reviewed local rows exist."
    return "Requires current readiness artifacts and reviewed local source proof before any supported outcome."


def batch_gate_summary(preflight: Any) -> str:
    blockers = [item for item in preflight.do_not_proceed_if if "dry-run scope is not reviewed" not in str(item)]
    if preflight.status == "ready_for_dry_run":
        return "Snapshot and freshness gates are ready. Generate the packet, review the dry-run scope, then keep validate and preview ahead of any apply step."
    first_blocker = blockers[0] if blockers else "preflight gate is not ready"
    return f"Preflight is blocked: {first_blocker}. Fix this before treating changed readiness counts as proof."


def reviewed_batch_preflight_cards(preflight: Any) -> list[dict[str, object]]:
    top_n_match = re.search(r"\bTOP_N=(\d+)", str(preflight.packet_command or ""))
    top_n = top_n_match.group(1) if top_n_match else "10"
    if preflight.status != "ready_for_dry_run":
        body = (
            "Preflight found a missing gate before a reviewed batch. "
            f"First blocker: {_compact_fragment(preflight.do_not_proceed_if[0], max_chars=180)}. "
            "Fix snapshot/freshness before using changed counts in the proof ledger."
        )
        badges = [preflight.status, preflight.freshness_status]
    else:
        body = (
            "Current readiness and prior snapshot are present. Start with the packet and dry-run command, then compare "
            "readiness before recording a supported, candidate-context-only, still-blocked, skipped, or excluded proof row."
        )
        badges = ["ready", "dry-run first"]
    return [
        {
            "kicker": "BATCH PREFLIGHT",
            "title": "Snapshot and freshness gate",
            "body": body,
            "badges": badges,
            "command": f"make reviewed-batch-preflight LANE={preflight.lane} TOP_N={top_n}",
        }
    ]


def reviewed_batch_preflight_frame(preflight: Any) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Status": preflight.status,
                "Lane": preflight.lane_scope,
                "Batch ID": preflight.batch_id,
                "Current Report Exists": "Yes" if preflight.current_report_exists else "No",
                "Prior Snapshot Exists": "Yes" if preflight.prior_snapshot_exists else "No",
                "Freshness": f"{preflight.freshness_status}: {preflight.freshness_message}",
                "Packet Command": preflight.packet_command,
                "Snapshot Command": preflight.snapshot_command,
                "Dry Run Command": preflight.dry_run_command,
                "Comparison Command": preflight.comparison_command,
                "Proof Record Command": preflight.proof_record_command,
                "Post-run Hygiene": "; ".join(preflight.post_run_hygiene),
                "Do Not Proceed If": "; ".join(preflight.do_not_proceed_if),
            }
        ]
    )


def reviewed_batch_snapshot_gate_cards(preflight: Any) -> list[dict[str, object]]:
    if not preflight.current_report_exists:
        return [
            {
                "kicker": "SNAPSHOT GATE",
                "title": "Build current readiness first",
                "body": (
                    "The current readiness report is missing, so a baseline snapshot would not prove anything yet. "
                    "Run readiness before packet, dry-run, capped execution, comparison, or proof-record work."
                ),
                "badges": ["missing current", "stop"],
                "command": "make readiness",
            }
        ]
    if not preflight.prior_snapshot_exists:
        return [
            {
                "kicker": "SNAPSHOT GATE",
                "title": "Save baseline snapshot first",
                "body": (
                    "Prior readiness snapshot is missing. Run this copy-only snapshot before the reviewed packet or dry run "
                    "so later comparison can prove changed readiness counts instead of guessing."
                ),
                "badges": ["missing baseline", "snapshot first"],
                "command": preflight.snapshot_command,
            }
        ]
    return [
        {
            "kicker": "SNAPSHOT GATE",
            "title": "Baseline snapshot ready",
            "body": (
                "Prior and current readiness artifacts are present. Keep source proof, validation, preview/apply decision, "
                "and artifact classification visible before recording a supported outcome."
            ),
            "badges": ["ready", "compare later"],
            "command": preflight.comparison_command,
        }
    ]


def reviewed_batch_snapshot_gate_frame(preflight: Any) -> pd.DataFrame:
    if not preflight.current_report_exists:
        status = "missing_current_report"
        next_step = "Run make readiness before saving a baseline snapshot."
        command = "make readiness"
        stop_if = "current readiness report is unavailable"
    elif not preflight.prior_snapshot_exists:
        status = "missing_prior_snapshot"
        next_step = "Run make readiness-snapshot before the packet or dry-run command."
        command = preflight.snapshot_command
        stop_if = "baseline snapshot is missing"
    else:
        status = "snapshot_ready"
        next_step = "Continue to reviewed packet and dry-run, then compare before recording proof."
        command = preflight.comparison_command
        stop_if = "source proof or reviewed artifact classification is incomplete"
    return pd.DataFrame(
        [
            {
                "Gate": "Baseline readiness snapshot",
                "Status": status,
                "Current Report": "Yes" if preflight.current_report_exists else "No",
                "Prior Snapshot": "Yes" if preflight.prior_snapshot_exists else "No",
                "Next Step": next_step,
                "Copy Command": command,
                "Stop If": stop_if,
            }
        ]
    )


def reviewed_batch_apply_guard_steps(preflight: Any) -> dict[str, str]:
    lane = str(preflight.lane or "").strip().lower()
    if lane == "metrics":
        return {
            "mode": "read_only",
            "validate": "not_applicable_read_only_metric_review",
            "preview": "review metric blocker families and missing source lanes",
            "apply": "not_applicable; route fixes back to prices, fundamentals, market cap, or peer-input lanes",
            "rejected": "not_applicable_read_only_metric_review",
            "proof": "supported is not available from metric review alone",
        }
    if lane == "prices":
        return {
            "mode": "mutating_price_lane",
            "validate": "make price-validate",
            "preview": "make price-preview",
            "apply": "make price-apply only for reviewed trusted rows",
            "rejected": "data/rejected/price_import_rejected.csv",
            "proof": "supported only after price validation, preview, rejected-row review, apply decision, and rebuilt readiness",
        }
    return {
        "mode": "mutating_import_lane",
        "validate": "make imports-validate",
        "preview": "make imports-preview",
        "apply": "make imports-apply only for reviewed trusted rows",
        "rejected": "data/rejected/fundamentals_import_rejected.csv or data/rejected/peers_import_rejected.csv",
        "proof": "supported only after source proof, validation, preview, rejected-row review, apply decision, and rebuilt readiness",
    }


def reviewed_batch_apply_guard_cards(preflight: Any) -> list[dict[str, object]]:
    steps = reviewed_batch_apply_guard_steps(preflight)
    if steps["mode"] == "read_only":
        return [
            {
                "kicker": "APPLY GUARD",
                "title": "Read-only lane: no apply step",
                "body": (
                    "Metric readiness review does not apply rows. It can only point to blocked source lanes; any fix must go through that lane's validate, preview, rejected-row review, apply decision, and proof path."
                ),
                "badges": ["read-only", "route to source lane"],
                "command": preflight.dry_run_command,
            }
        ]
    return [
        {
            "kicker": "APPLY GUARD",
            "title": "Validate and preview before apply",
            "body": (
                f"Stop at {steps['validate']} and {steps['preview']} until source proof and rejected-row reports are reviewed. "
                f"{steps['proof']}; otherwise record still_blocked, skipped, or excluded."
            ),
            "badges": ["validate", "preview", "rejected rows", "manual apply"],
            "command": f"{steps['validate']} && {steps['preview']}",
        }
    ]


def reviewed_batch_apply_guard_frame(preflight: Any) -> pd.DataFrame:
    steps = reviewed_batch_apply_guard_steps(preflight)
    rows = [
        {
            "Gate": "Validate",
            "Status": "required" if steps["mode"] != "read_only" else "not_applicable_read_only",
            "Copy Command": steps["validate"],
            "Stop If": "validation fails or source proof is missing",
        },
        {
            "Gate": "Preview",
            "Status": "required" if steps["mode"] != "read_only" else "source_lane_review",
            "Copy Command": steps["preview"],
            "Stop If": "preview shows unexpected rows",
        },
        {
            "Gate": "Rejected-row review",
            "Status": "required" if steps["mode"] != "read_only" else "not_applicable_read_only",
            "Copy Command": steps["rejected"],
            "Stop If": "rejected rows are unresolved or unexplained",
        },
        {
            "Gate": "Apply decision",
            "Status": "manual_review" if steps["mode"] != "read_only" else "not_applicable_read_only",
            "Copy Command": steps["apply"],
            "Stop If": "reviewer cannot identify changed source files and rollback path",
        },
        {
            "Gate": "Supported outcome",
            "Status": "blocked_until_proven",
            "Copy Command": preflight.proof_record_command,
            "Stop If": steps["proof"],
        },
    ]
    return pd.DataFrame(rows)


def reviewed_batch_loop_card(preflight: Any, freshness: Any) -> dict[str, object]:
    if freshness.status in {"missing", "stale"}:
        title = "Refresh source artifacts first"
        command = freshness.refresh_command
        gate_note = f"Freshness gate is {freshness.status}: {freshness.message}"
        badges = [freshness.status, "refresh first"]
    elif not preflight.current_report_exists:
        title = "Build current readiness first"
        command = "make readiness"
        gate_note = "Current readiness report is missing, so changed-count proof cannot start yet."
        badges = ["missing current", "stop"]
    elif not preflight.prior_snapshot_exists:
        title = "Save the baseline snapshot first"
        command = preflight.snapshot_command
        gate_note = "Prior readiness snapshot is missing, so before/after comparison would be current-only."
        badges = ["snapshot first", "compare later"]
    else:
        title = "Run the reviewed batch loop"
        command = preflight.packet_command
        gate_note = "Snapshot and freshness gates are ready; begin with the reviewed packet and dry-run scope."
        badges = ["ready", "dry-run first"]
    return {
        "kicker": "BATCH LOOP",
        "title": title,
        "body": (
            "Operator sequence: snapshot -> reviewed packet/dry run -> validate/preview/apply gate -> "
            "proof-record command -> before/after comparison. "
            f"{gate_note} Commands are copy-only from the dashboard; supported outcomes require reviewed source files and generated-artifact classification."
        ),
        "badges": badges,
        "command": command,
    }


def reviewed_batch_execution_cards(selected_lane_key: str, preflight: Any, freshness: Any) -> list[dict[str, object]]:
    batch_lane = batch_lane_for_operator(selected_lane_key)
    lane_label = DATA_HEALTH_OPERATOR_LANES.get(selected_lane_key, preflight.lane_scope)
    next_command = preflight.packet_command if preflight.status == "ready_for_dry_run" else preflight.snapshot_command
    if freshness.status in {"missing", "stale"}:
        next_command = freshness.refresh_command
    next_title = "Generate reviewed packet" if preflight.status == "ready_for_dry_run" else "Fix preflight gate"
    return [
        {
            "kicker": "BATCH LANE",
            "title": lane_label,
            "body": (
                f"Selected reviewed-batch lane: {batch_lane}. Scope is capped by TOP_N and optional ticker filters; "
                "this is a data-readiness queue, not a security ranking."
            ),
            "badges": [batch_lane, "capped scope"],
            "command": "",
        },
        reviewed_batch_loop_card(preflight, freshness),
        reviewed_batch_snapshot_gate_cards(preflight)[0],
        reviewed_batch_apply_guard_cards(preflight)[0],
        {
            "kicker": "SOURCE GATE",
            "title": "Freshness before commands",
            "body": f"{freshness.status}: {freshness.message} {batch_source_requirement(batch_lane)}",
            "badges": [freshness.status, "source proof first"],
            "command": freshness.refresh_command if freshness.status in {"missing", "stale"} else "",
        },
        {
            "kicker": "NEXT BATCH ACTION",
            "title": next_title,
            "body": (
                f"{batch_gate_summary(preflight)} "
                "Full dry-run, capped execution, proof, rollback, and artifact hygiene details stay in the review drawer."
            ),
            "badges": [preflight.status, "copy-only"],
            "command": next_command,
        },
    ]


def reviewed_batch_operator_flow_cards(
    selected_lane_key: str,
    preflight: Any,
    freshness: Any,
    loop: Any | None = None,
) -> list[dict[str, object]]:
    batch_lane = batch_lane_for_operator(selected_lane_key)
    lane_label = DATA_HEALTH_OPERATOR_LANES.get(selected_lane_key, preflight.lane_scope)
    apply_steps = reviewed_batch_apply_guard_steps(preflight)
    loop_status = loop.status if loop is not None else preflight.status
    loop_badge = preflight.status if loop_status == "blocked_missing_lane" else loop_status
    freshness_blocked = freshness.status in {"missing", "stale"}
    snapshot_blocked = not preflight.current_report_exists or not preflight.prior_snapshot_exists
    if freshness_blocked:
        next_title = "Refresh readiness artifacts"
        next_command = freshness.refresh_command
        next_body = f"{freshness.status}: {_compact_fragment(freshness.message, max_chars=150)}"
        next_badges = [freshness.status, "refresh first"]
    elif snapshot_blocked:
        next_title = "Capture snapshot gate"
        next_command = preflight.snapshot_command if preflight.current_report_exists else "make readiness"
        next_body = batch_gate_summary(preflight)
        next_badges = [preflight.status, "snapshot first"]
    else:
        next_title = "Packet, then dry run"
        next_command = preflight.packet_command
        next_body = (
            "Generate the reviewed packet, then inspect the capped dry-run scope before any lane work. "
            f"Dry-run command: {preflight.dry_run_command}"
        )
        next_badges = [preflight.status, "dry-run first"]
    apply_body = (
        "Read-only metric lane routes blockers back to prices, fundamentals, market cap, or peers."
        if apply_steps["mode"] == "read_only"
        else "Mutating lanes stay validate -> preview -> explicit apply; rejected-row reports must be reviewed first."
    )
    proof_record_command = f"DRY_RUN=1 {preflight.proof_record_command}"
    return [
        {
            "kicker": "LANE",
            "title": lane_label,
            "body": (
                f"Selected lane: {batch_lane}. Keep scope capped by TOP_N or explicit tickers; "
                "treat this as readiness operations, not a security ranking."
            ),
            "badges": [batch_lane, "capped"],
            "command": f"make coverage-expansion-loop LANE={batch_lane} TOP_N=10",
        },
        {
            "kicker": "SOURCE GATE",
            "title": "Freshness and source proof first",
            "body": f"{batch_source_requirement(batch_lane)} {_compact_fragment(freshness.message, max_chars=150)}",
            "badges": [freshness.status, loop_badge],
            "command": freshness.refresh_command if freshness_blocked else "",
        },
        {
            "kicker": "NEXT STEP",
            "title": next_title,
            "body": next_body,
            "badges": next_badges,
            "command": next_command,
        },
        {
            "kicker": "PROOF BOUNDARY",
            "title": "Compare before recording",
            "body": (
                f"{apply_body} After reviewed work, compare before/after readiness before claiming supported, "
                "candidate_context_only, still_blocked, skipped, or excluded."
            ),
            "badges": [apply_steps["mode"], "ledger proof"],
            "command": preflight.comparison_command,
        },
        {
            "kicker": "OUTCOME RECORD",
            "title": "Dry-run proof row last",
            "body": (
                "Use the proof-record dry run only after packet review, capped preview, source review, validation or "
                "read-only metric review, and before/after comparison are complete. If required fields still contain "
                "placeholders, keep the outcome unfinished. Record supported, candidate_context_only, still_blocked, "
                "skipped, or excluded only after proof."
            ),
            "badges": ["dry-run proof", "manual review"],
            "command": proof_record_command,
        },
    ]


def reviewed_batch_execution_frame(preflight: Any) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Step": "1. Reviewed packet", "Command": preflight.packet_command, "Gate": "Copy-only packet before any lane work."},
            {"Step": "2. Snapshot", "Command": preflight.snapshot_command, "Gate": "Required before changed readiness counts can be trusted."},
            {"Step": "3. Dry run", "Command": preflight.dry_run_command, "Gate": "Review scope, source notes, and expected artifacts first."},
            {"Step": "4. Capped execution", "Command": preflight.capped_execution_command, "Gate": "Run only after dry-run review; mutating lanes still require validate -> preview -> apply."},
            {"Step": "5. Validate", "Command": "make imports-validate or lane-specific validator", "Gate": "Stop when validation fails."},
            {"Step": "6. Preview", "Command": "make imports-preview or lane-specific preview", "Gate": "Stop when preview or rejected-row reports are unresolved."},
            {"Step": "7. Apply", "Command": "make imports-apply only for reviewed trusted rows", "Gate": "Manual reviewed step; not a dashboard action."},
            {"Step": "8. Proof", "Command": preflight.comparison_command, "Gate": "Record supported, candidate_context_only, still_blocked, skipped, or excluded only after proof."},
            {"Step": "9. Ledger", "Command": preflight.proof_record_command, "Gate": "Durable record after source files and generated churn are classified."},
            {"Step": "10. Hygiene", "Command": " && ".join(preflight.post_run_hygiene[:2]), "Gate": "Classify generated CSV/JSON churn before any public commit."},
            {"Step": "Rollback", "Command": "restore reviewed standard local CSVs from git/backups, then rerun make readiness", "Gate": "Use if applied local rows are wrong or source proof fails."},
        ]
    )


def reviewed_batch_execution_checklist_frame(
    selected_lane_key: str,
    preflight: Any,
    freshness: Any,
    loop: Any | None = None,
) -> pd.DataFrame:
    batch_lane = batch_lane_for_operator(selected_lane_key)
    lane_label = DATA_HEALTH_OPERATOR_LANES.get(selected_lane_key, preflight.lane_scope)
    freshness_ready = freshness.status == "current"
    preflight_ready = preflight.status == "ready_for_dry_run"
    snapshot_ready = preflight.prior_snapshot_exists and preflight.current_report_exists
    source_warning = batch_source_requirement(batch_lane)
    loop_status = loop.status if loop is not None else preflight.status
    apply_steps = reviewed_batch_apply_guard_steps(preflight)
    validation_command = (
        f"{apply_steps['validate']} && {apply_steps['preview']}"
        if apply_steps["mode"] != "read_only"
        else apply_steps["preview"]
    )
    first_blocker = preflight.do_not_proceed_if[0] if preflight.do_not_proceed_if else "source proof, validation, preview, and artifact review are required"
    return pd.DataFrame(
        [
            {
                "Step": "1. Choose lane",
                "Status": f"selected: {lane_label}",
                "Operator Decision": f"Scope is {batch_lane}; keep it capped and readiness-first.",
                "Copy-Only Command": f"make coverage-expansion-loop LANE={batch_lane} TOP_N=10",
                "Stop If": "selected lane is not in the coverage planner",
            },
            {
                "Step": "2. Source and freshness warnings",
                "Status": freshness.status,
                "Operator Decision": f"{freshness.message} {source_warning}",
                "Copy-Only Command": freshness.refresh_command if not freshness_ready else "",
                "Stop If": "readiness artifacts are missing or stale",
            },
            {
                "Step": "3. Reviewed packet",
                "Status": "ready" if preflight.current_report_exists and freshness_ready else "blocked",
                "Operator Decision": "Generate the packet before dry-run or source-row review.",
                "Copy-Only Command": preflight.packet_command,
                "Stop If": "current readiness report is missing or stale",
            },
            {
                "Step": "4. Preview capped batch",
                "Status": "ready after packet review" if preflight_ready else "waiting on preflight",
                "Operator Decision": "Review planned scope, source notes, and expected artifacts before any execution command.",
                "Copy-Only Command": preflight.dry_run_command,
                "Stop If": first_blocker,
            },
            {
                "Step": "5. Validate / preview / apply gate",
                "Status": apply_steps["mode"],
                "Operator Decision": "Mutating lanes stay validate -> preview -> explicit apply; metrics remain read-only.",
                "Copy-Only Command": validation_command,
                "Stop If": apply_steps["proof"],
            },
            {
                "Step": "6. Compare before / after",
                "Status": "ready after reviewed run" if snapshot_ready else "blocked until snapshot exists",
                "Operator Decision": "Use changed readiness counts and changed tickers as proof, not intuition.",
                "Copy-Only Command": preflight.comparison_command,
                "Stop If": "prior snapshot or current readiness report is missing",
            },
            {
                "Step": "7. Record proof outcome",
                "Status": "dry-run first",
                "Operator Decision": "Record supported, candidate_context_only, still_blocked, skipped, or excluded only after reviewed source and comparison proof.",
                "Copy-Only Command": f"DRY_RUN=1 {preflight.proof_record_command}",
                "Stop If": "required proof fields still contain placeholders",
            },
            {
                "Step": "8. Artifact hygiene",
                "Status": loop_status,
                "Operator Decision": "Classify generated CSV/JSON churn before staging; keep broad refresh artifacts local by default.",
                "Copy-Only Command": "make diff-hygiene",
                "Stop If": "generated artifacts are dirty and not intentionally reviewed evidence",
            },
        ]
    )


def reviewed_batch_sequence_cards(preflight: Any) -> list[dict[str, object]]:
    return [
        {
            "kicker": "PACKET",
            "title": "Create reviewed proof packet",
            "body": "Copy-only packet with lane, scope, source/freshness status, proof fields, do-not-proceed conditions, rollback, and generated-artifact hygiene.",
            "badges": ["packet first", "no data change"],
            "command": preflight.packet_command,
        },
        {
            "kicker": "DRY RUN",
            "title": "Preview capped scope",
            "body": "Review planned rows, source notes, expected artifacts, and stale-readiness warnings before any execution command.",
            "badges": ["dry-run first", "capped"],
            "command": preflight.dry_run_command,
        },
        {
            "kicker": "MUTATION GATE",
            "title": "Validate -> preview -> apply",
            "body": "Mutating source lanes must pass validation, preview, rejected-row review, and explicit apply. Metrics remain read-only and route back to source lanes.",
            "badges": ["review required", "manual apply"],
            "command": "make imports-validate && make imports-preview",
        },
        {
            "kicker": "PROOF",
            "title": "Compare, record, rollback if needed",
            "body": "After reviewed work, rebuild readiness, compare before/after counts, record supported/candidate_context_only/still_blocked/skipped/excluded, and restore standard local CSVs if source proof fails.",
            "badges": ["proof ledger", "rollback ready"],
            "command": preflight.comparison_command,
        },
    ]
