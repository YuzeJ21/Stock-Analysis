from __future__ import annotations

import pandas as pd

from src.data_health_proof_ctas import (
    card_sentence,
    compact_card_fragment,
    data_health_operator_lane_url,
    format_missing,
)


def latest_outcome_for_lane(frame: pd.DataFrame | None, *tokens: str) -> pd.Series:
    if frame is None or frame.empty or "Lane" not in frame.columns:
        return pd.Series(dtype=object)
    lane_text = frame["Lane"].fillna("").astype(str).str.lower()
    mask = pd.Series(False, index=frame.index)
    for token in tokens:
        mask = mask | lane_text.str.contains(token.lower(), regex=False, na=False)
    matches = frame.loc[mask].copy()
    if matches.empty:
        return pd.Series(dtype=object)
    outcome_text = matches.get("Latest Outcome", pd.Series("", index=matches.index)).fillna("").astype(str).str.lower()
    recorded = matches.loc[outcome_text.ne("not_recorded") & outcome_text.ne("")]
    return recorded.iloc[0] if not recorded.empty else matches.iloc[0]


def proof_planner_state_from_frame(frame: pd.DataFrame | None) -> str:
    if frame is None or frame.empty or "Status" not in frame.columns:
        return ""
    statuses = set(frame["Status"].fillna("").astype(str).str.lower().str.strip())
    if any(status in statuses for status in {"blocked_by_stale", "blocked_by_missing", "blocked_by_freshness"}):
        return "blocked_by_freshness"
    if "ready_for_review_fields" in statuses:
        return "ready_for_proof_record_review"
    if "blocked_by_guard" in statuses:
        return "blocked_by_guard"
    if any(status in statuses for status in {"needs_field_fills", "needs_source_fields", "needs_peer_source_proof"}):
        return "needs_source_fields"
    if any(status.startswith("blocked") for status in statuses):
        return "blocked"
    if any(status in statuses for status in {"dry_run_first", "copy_only_gate", "ready", "current", "fresh"}):
        return "ready_to_plan"
    return ""


def proof_planner_outcome_summary_frame(
    readiness_summary: dict[str, object],
    queue_outcome_summary: pd.DataFrame | None = None,
    readiness_freshness: object | None = None,
    dcf_planner_frame: pd.DataFrame | None = None,
    peer_planner_frame: pd.DataFrame | None = None,
) -> pd.DataFrame:
    columns = [
        "Planner Lane",
        "Planner State",
        "Coverage Gap",
        "Latest Outcome",
        "Detail Level",
        "Next Safest Action",
        "Lane URL",
        "Copy Cue",
        "Stop Rule",
    ]
    price_ready = int(readiness_summary.get("price_ready") or 0)
    dcf_ready = int(readiness_summary.get("dcf_ready") or 0)
    peer_ready = int(readiness_summary.get("peer_ready") or 0)
    freshness_status = format_missing(getattr(readiness_freshness, "status", ""), "").lower()
    dcf_gap = max(price_ready - dcf_ready, 0)
    peer_gap = max(price_ready - peer_ready, 0)
    dcf_outcome_row = latest_outcome_for_lane(queue_outcome_summary, "fundamentals", "dcf", "share_count")
    peer_outcome_row = latest_outcome_for_lane(queue_outcome_summary, "peer")

    def _latest(row: pd.Series) -> str:
        if row.empty:
            return "not_recorded"
        return format_missing(row.get("Latest Outcome"), "not_recorded").lower()

    def _summary_state(gap: int, latest: str, planner_frame: pd.DataFrame | None, fallback: str) -> str:
        detail_state = proof_planner_state_from_frame(planner_frame)
        if detail_state:
            return detail_state
        if freshness_status in {"missing", "stale"}:
            return "blocked_by_freshness"
        if latest in {"still_blocked", "skipped", "excluded"}:
            return latest
        if latest == "supported" and gap:
            return "supported_but_more_rows_blocked"
        if gap:
            return fallback
        return "ready_or_no_current_gap"

    dcf_state = _summary_state(dcf_gap, _latest(dcf_outcome_row), dcf_planner_frame, "needs_source_fields")
    peer_state = _summary_state(peer_gap, _latest(peer_outcome_row), peer_planner_frame, "needs_source_fields")
    return pd.DataFrame(
        [
            {
                "Planner Lane": "DCF proof planner",
                "Planner State": dcf_state,
                "Coverage Gap": f"{dcf_gap:,} price-ready row(s) still need trusted DCF inputs",
                "Latest Outcome": _latest(dcf_outcome_row),
                "Detail Level": "planner_loaded" if dcf_planner_frame is not None and not dcf_planner_frame.empty else "summary_only",
                "Next Safest Action": "Open Fundamentals / DCF lane",
                "Lane URL": data_health_operator_lane_url("fundamentals"),
                "Copy Cue": "Use this link to open the DCF planner drawer, then review the capped batch plan before source rows.",
                "Stop Rule": "Stop if source fields, validation, preview, changed counts, source files, or artifact review are missing.",
            },
            {
                "Planner Lane": "Peer proof planner",
                "Planner State": peer_state,
                "Coverage Gap": f"{peer_gap:,} price-ready row(s) still need source-backed peer proof",
                "Latest Outcome": _latest(peer_outcome_row),
                "Detail Level": "planner_loaded" if peer_planner_frame is not None and not peer_planner_frame.empty else "summary_only",
                "Next Safest Action": "Open Peers lane",
                "Lane URL": data_health_operator_lane_url("peers"),
                "Copy Cue": "Use this link to open the peer planner drawer, then review source fields and write-back guard before proof record.",
                "Stop Rule": "Stop if peer source fields, write-back guard, duplicate checks, changed counts, source files, or artifact review are missing.",
            },
        ],
        columns=columns,
    )


def proof_planner_outcome_summary_cards(
    readiness_summary: dict[str, object],
    queue_outcome_summary: pd.DataFrame | None = None,
    readiness_freshness: object | None = None,
    dcf_planner_frame: pd.DataFrame | None = None,
    peer_planner_frame: pd.DataFrame | None = None,
) -> list[dict[str, object]]:
    frame = proof_planner_outcome_summary_frame(
        readiness_summary,
        queue_outcome_summary,
        readiness_freshness,
        dcf_planner_frame,
        peer_planner_frame,
    )
    if frame.empty:
        return [
            {
                "kicker": "PROOF PLANNERS",
                "title": "Planner summary unavailable",
                "body": "Refresh readiness before relying on DCF or peer planner status.",
                "badges": ["readiness first", "blocked visible"],
                "command": "make readiness",
            }
        ]
    ready_states = {"ready_or_no_current_gap", "ready_to_plan", "ready_for_proof_record_review", "supported"}
    blocking = frame.loc[~frame["Planner State"].fillna("").astype(str).str.lower().isin(ready_states)]
    first = blocking.iloc[0] if not blocking.empty else frame.iloc[0]
    state_pairs = "; ".join(
        f"{row['Planner Lane']}: {str(row['Planner State']).replace('_', ' ')}" for _, row in frame.iterrows()
    )
    cards = [
        {
            "kicker": "PROOF PLANNER OUTCOMES",
            "title": f"{len(blocking)} planner lane(s) need review",
            "body": (
                f"{compact_card_fragment(state_pairs, max_chars=220)}. "
                "Summary uses readiness counts and proof-ledger outcomes first; lane links open the detailed planners only when needed."
            ),
            "badges": ["summary first", "drawers lazy"],
            "command": "make readiness-queue TOP_N=10",
        },
        {
            "kicker": str(first.get("Planner Lane", "Planner lane")).upper(),
            "title": str(first.get("Planner State", "not_recorded")).replace("_", " "),
            "body": (
                f"{card_sentence('Gap', first.get('Coverage Gap'))} "
                f"{card_sentence('Latest outcome', first.get('Latest Outcome'))} "
                f"{card_sentence('Open', first.get('Lane URL'))} "
                f"{card_sentence('Stop rule', compact_card_fragment(first.get('Stop Rule'), max_chars=180))}"
            ),
            "badges": ["finish planner", "source-backed only"],
            "command": str(first.get("Lane URL", "Open Data Health lane")),
        },
        {
            "kicker": "LANE JUMP CUE",
            "title": str(first.get("Next Safest Action", "Open Data Health lane")),
            "body": (
                f"{card_sentence('Copy cue', compact_card_fragment(first.get('Copy Cue'), max_chars=190))} "
                "Commands and proof tables remain collapsed inside the selected lane."
            ),
            "badges": ["jump to lane", "details collapsed"],
            "command": str(first.get("Lane URL", "Open Data Health lane")),
        },
    ]
    stale_blockers = frame.loc[frame["Planner State"].fillna("").astype(str).str.lower().eq("blocked_by_freshness")]
    if not stale_blockers.empty:
        refresh_command = format_missing(getattr(readiness_freshness, "refresh_command", ""), "make readiness")
        freshness_message = compact_card_fragment(getattr(readiness_freshness, "message", ""), max_chars=180)
        cards.insert(
            0,
            {
                "kicker": "FRESHNESS GATE",
                "title": "Refresh readiness before proof planning",
                "body": (
                    f"{card_sentence('Freshness', freshness_message)} "
                    "Refresh before DCF or peer proof planning; stale readiness rows are not proof. Open operator details for read-only proof steps."
                ),
                "badges": ["blocked by freshness", "refresh first"],
                "command": refresh_command,
            },
        )
    return cards
