from __future__ import annotations

import re

import pandas as pd

from src.data_health_proof_ctas import card_sentence, compact_card_fragment, format_missing


READY_STATUSES = {"ready", "current", "fresh", "supported", "copy_only", "copy_only_gate", "ready_for_validate_preview"}
TERMINAL_PROOF_STATUSES = {"supported", "still_blocked", "skipped", "excluded", "stop_rule"}
OPEN_STATUS_PATTERN = re.compile(r"blocked|missing|needs|not_loaded|not_recorded|stale|warning|deferred", re.IGNORECASE)


def _row_by_value(frame: pd.DataFrame | None, column: str, value: str) -> pd.Series:
    if frame is None or frame.empty or column not in frame.columns:
        return pd.Series(dtype=object)
    rows = frame.loc[frame[column].astype(str).eq(value)]
    return rows.iloc[0] if not rows.empty else pd.Series(dtype=object)


def _first_open_checklist_row(checklist: pd.DataFrame | None) -> pd.Series:
    if checklist is None or checklist.empty or "Status" not in checklist.columns:
        return pd.Series(dtype=object)
    statuses = checklist["Status"].fillna("").astype(str).str.lower()
    open_rows = checklist.loc[~statuses.isin(READY_STATUSES)]
    return open_rows.iloc[0] if not open_rows.empty else checklist.iloc[-1]


def _latest_outcome_row(outcome: pd.DataFrame | None, lane: str) -> pd.Series:
    step = "Latest peer ledger outcome" if lane.lower().startswith("peer") else "Latest DCF ledger outcome"
    row = _row_by_value(outcome, "Proof Loop Step", step)
    if not row.empty:
        return row
    if outcome is not None and not outcome.empty:
        return outcome.iloc[-1]
    return pd.Series(dtype=object)


def proof_loop_fit_frame(
    *,
    lane: str,
    operator_summary: pd.DataFrame | None,
    checklist: pd.DataFrame | None,
    outcome: pd.DataFrame | None,
    closeout: pd.DataFrame | None,
) -> pd.DataFrame:
    columns = ["Workflow Step", "Status", "What To Look At", "Next Safe Action", "Boundary"]
    current = _row_by_value(operator_summary, "Question", "What is the current gate?")
    stop = _row_by_value(operator_summary, "Question", "When must I stop?")
    blocker = _first_open_checklist_row(checklist)
    latest = _latest_outcome_row(outcome, lane)
    closeout_row = closeout.iloc[0] if closeout is not None and not closeout.empty else pd.Series(dtype=object)

    current_status = format_missing(current.get("Status"), format_missing(closeout_row.get("Closeout Status"), "not_loaded"))
    current_answer = format_missing(current.get("Answer"), "Open the proof drawer to load current gate details.")
    current_action = format_missing(current.get("Next Safe Action"), "Open proof drawer review details.")
    stop_rule = format_missing(
        stop.get("Answer"),
        format_missing(closeout_row.get("Closeout Boundary"), "Stop if source proof, comparison, or proof-record review is incomplete."),
    )

    blocker_status = format_missing(blocker.get("Status"), "not_loaded")
    blocker_need = format_missing(
        blocker.get("Need Before Proceeding"),
        "Load the checklist before reviewing source, validation, preview, or proof-record gates.",
    )
    blocker_action = format_missing(blocker.get("Next Safest Action"), current_action)
    blocker_boundary = format_missing(blocker.get("Stop Rule"), stop_rule)

    latest_status = format_missing(latest.get("Status"), format_missing(closeout_row.get("Latest Outcome"), "not_recorded"))
    latest_detail = format_missing(latest.get("Detail"), format_missing(closeout_row.get("Evidence Remaining"), "No reviewed ledger outcome loaded."))
    latest_action = format_missing(latest.get("Next Safe Action"), format_missing(closeout_row.get("Next Safest Action"), "make reviewed-batch-proof"))

    closeout_status = format_missing(closeout_row.get("Closeout Status"), "not_loaded")
    closeout_detail = format_missing(closeout_row.get("Evidence Remaining"), latest_detail)
    closeout_action = format_missing(closeout_row.get("Next Safest Action"), latest_action)
    closeout_boundary = format_missing(closeout_row.get("Closeout Boundary"), stop_rule)

    return pd.DataFrame(
        [
            {
                "Workflow Step": "Status",
                "Status": current_status,
                "What To Look At": compact_card_fragment(current_answer, max_chars=220),
                "Next Safe Action": current_action,
                "Boundary": "First-read proof-loop state; no data write or readiness unlock.",
            },
            {
                "Workflow Step": "Blocker",
                "Status": blocker_status,
                "What To Look At": compact_card_fragment(blocker_need, max_chars=220),
                "Next Safe Action": blocker_action,
                "Boundary": blocker_boundary,
            },
            {
                "Workflow Step": "Next Proof Step",
                "Status": latest_status,
                "What To Look At": compact_card_fragment(latest_detail, max_chars=220),
                "Next Safe Action": latest_action,
                "Boundary": "Latest ledger/comparison evidence is proof state only, not advice or a ranking.",
            },
            {
                "Workflow Step": "Evidence",
                "Status": closeout_status,
                "What To Look At": compact_card_fragment(closeout_detail, max_chars=220),
                "Next Safe Action": closeout_action,
                "Boundary": closeout_boundary,
            },
            {
                "Workflow Step": "Stop Rule",
                "Status": "stop_rule",
                "What To Look At": compact_card_fragment(stop_rule, max_chars=260),
                "Next Safe Action": "Keep the lane blocked, skipped, or still_blocked until reviewed proof exists.",
                "Boundary": "Research-only: do not infer missing data or turn proof state into investment advice.",
            },
        ],
        columns=columns,
    )


def proof_loop_fit_cards(frame: pd.DataFrame | None, *, lane: str) -> list[dict[str, object]]:
    if frame is None or frame.empty:
        return [
            {
                "kicker": f"{lane.upper()} PROOF LOOP",
                "title": "Proof loop not loaded",
                "body": "Open the proof drawer before reviewing source, validation, comparison, or proof-record gates.",
                "badges": ["blocked visible", "research-only"],
                "command": "make reviewed-batch-proof",
            }
        ]
    status = _row_by_value(frame, "Workflow Step", "Status")
    blocker = _row_by_value(frame, "Workflow Step", "Blocker")
    proof = _row_by_value(frame, "Workflow Step", "Next Proof Step")
    stop = _row_by_value(frame, "Workflow Step", "Stop Rule")
    statuses = frame["Status"].fillna("").astype(str).str.lower()
    open_count = int(
        statuses.map(lambda status: status not in TERMINAL_PROOF_STATUSES and bool(OPEN_STATUS_PATTERN.search(status))).sum()
    )
    return [
        {
            "kicker": f"{lane.upper()} PROOF LOOP",
            "title": f"{format_missing(status.get('Status'), 'not_loaded')}: {open_count} open gate(s)",
            "body": (
                f"{card_sentence('Current', compact_card_fragment(status.get('What To Look At'), max_chars=180))} "
                f"{card_sentence('Blocker', compact_card_fragment(blocker.get('What To Look At'), max_chars=180))} "
                "Use this first before reading detailed source tables."
            ),
            "badges": ["status", "blocker", "proof state"],
            "command": format_missing(status.get("Next Safe Action"), "make reviewed-batch-proof"),
        },
        {
            "kicker": "NEXT PROOF STEP",
            "title": format_missing(proof.get("Status"), "not_recorded"),
            "body": (
                f"{card_sentence('Evidence', compact_card_fragment(proof.get('What To Look At'), max_chars=190))} "
                "Proof states stay supported, candidate_context_only, still_blocked, skipped, or excluded until reviewed evidence is complete."
            ),
            "badges": ["evidence", "copy-only"],
            "command": format_missing(proof.get("Next Safe Action"), "make reviewed-batch-proof"),
        },
        {
            "kicker": "STOP RULE",
            "title": "No inferred inputs",
            "body": compact_card_fragment(stop.get("What To Look At"), max_chars=260),
            "badges": ["research-only", "no advice"],
            "command": format_missing(stop.get("Next Safe Action"), "Keep lane blocked until proof is reviewed."),
        },
    ]
