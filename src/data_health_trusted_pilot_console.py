"""Pure trusted-data pilot console helpers for Data Health.

The dashboard should render frames and cards, while this module owns the
read-only pilot workflow copy: candidate ranking, lane groups, packet commands,
source-proof boundaries, and still-blocked/skip wording.
"""

from __future__ import annotations

from src.reviewed_batch_proof import resolve_readiness_proof_profile

from pathlib import Path

import pandas as pd

from src.trusted_data_pilot import (
    build_trusted_data_pilot_candidates,
    pilot_evidence_expectation,
    pilot_evidence_row_template,
    pilot_lane_label,
    pilot_lane_runbook,
    pilot_lane_summary_rows,
    pilot_local_file_status,
    pilot_operator_decision,
    pilot_quick_path_lines,
    pilot_rank_reason,
    pilot_review_path,
    pilot_selection_brief,
    pilot_skip_condition,
    pilot_trusted_row_path,
    plain_pilot_input_copy,
)


def _format_missing(value: object, fallback: str = "Not available") -> str:
    if value is None:
        return fallback
    try:
        if pd.isna(value):
            return fallback
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null", "<na>"}:
        return fallback
    return text


def _compact_fragment(
    value: object,
    fallback: str = "Not available",
    *,
    max_chars: int = 180,
    max_sentences: int = 1,
) -> str:
    text = _format_missing(value, fallback).replace("\n", " ").strip()
    if text == fallback:
        return text
    sentences = [part.strip() for part in text.split(". ") if part.strip()]
    compact = ". ".join(sentences[:max_sentences]) if sentences else text
    if compact and not compact.endswith((".", "?", "!")):
        compact += "."
    if len(compact) > max_chars:
        compact = compact[: max(0, max_chars - 1)].rstrip() + "..."
    if compact.endswith("..."):
        return compact
    return compact.rstrip(" .;:")


def _card_sentence(label: str, fragment: str) -> str:
    clean_label = label.strip().rstrip(":")
    clean_fragment = _format_missing(fragment, "Not available").strip()
    terminal = "" if clean_fragment.endswith((".", "?", "!", "...")) else "."
    return f"{clean_label}: {clean_fragment}{terminal}"


def _lane_usage_answer(status: object) -> str:
    normalized = _format_missing(status, "review_only").strip().lower()
    if normalized == "safe_to_batch_dry_run":
        return "Usable now: dry-run planning only; no rows are applied from this lane card."
    if normalized == "locked":
        return "Blocked by source proof: keep locked until trusted rows exist."
    return "Context only: review rows describe source work, not analysis-ready proof."


def trusted_pilot_cards(readiness_summary: dict[str, object]) -> list[dict[str, object]]:
    price_ready = int(readiness_summary.get("price_ready") or 0)
    fundamentals_ready = int(readiness_summary.get("fundamentals_ready") or 0)
    dcf_ready = int(readiness_summary.get("dcf_ready") or 0)
    peer_ready = int(readiness_summary.get("peer_ready") or 0)
    earnings_ready = int(readiness_summary.get("earnings_ready") or 0)
    estimates_ready = int(readiness_summary.get("analyst_estimates_ready") or readiness_summary.get("analyst_ready") or 0)
    depth_gap = max(price_ready - min(fundamentals_ready, dcf_ready), 0)
    peer_gap = max(dcf_ready - peer_ready, 0)

    return [
        {
            "kicker": "PILOT STEP 1",
            "title": "Check the status gate first",
            "body": (
                f"{depth_gap:,} price-ready company row(s) still need trusted fundamentals or DCF inputs, and "
                f"{peer_gap:,} DCF-ready row(s) still need source-backed peer context. Start with project status so exhausted source-proof queues "
                "route to provider setup instead of reopening stale candidate loops. Open the ranked pilot only when status shows executable company candidates."
            ),
            "badges": ["status gate", "read-only"],
            "command": "make project-status",
        },
        {
            "kicker": "PILOT STEP 2",
            "title": "Inspect one proof packet",
            "body": (
                "When project status shows executable company candidates, use the first shortlisted ticker packet to see the current report, missing input, review lane, trusted input target, and rebuild proof. "
                "It explains the baseline, source proof, validation, rejected-row check, rebuild, and stop rule before any conclusion changes."
            ),
            "badges": ["one company", "no fake rows"],
            "command": "make trusted-data-pilot-packet TICKER=<ticker>",
        },
        {
            "kicker": "PILOT STEP 3",
            "title": "Run the selected proof loop",
            "body": (
                f"Optional context remains locked at {earnings_ready:,} earnings-ready and {estimates_ready:,} estimate-ready row(s) until trusted CSV rows exist. "
                "Use the pilot loop only for selected company names with source proof; only the rebuilt readiness and stock report can prove the lane changed. "
                "Read the outcome as Supported, Still blocked, or Skip; a still-blocked or skipped ticker is useful proof, not a failure."
            ),
            "badges": ["supported / blocked / skip", "trusted CSVs"],
            "command": "make trusted-data-pilot TICKERS=<chosen names> TOP_N=10",
        },
    ]


def trusted_pilot_preview_frame(
    fundamentals_peer_worklist_frame: pd.DataFrame | None,
    peer_unlock_worklist_frame: pd.DataFrame | None,
    ticker_readiness_frame: pd.DataFrame | None,
    *,
    root: Path,
    limit: int = 5,
) -> pd.DataFrame:
    fundamentals_rows = [] if fundamentals_peer_worklist_frame is None else fundamentals_peer_worklist_frame.to_dict("records")
    peer_rows = [] if peer_unlock_worklist_frame is None else peer_unlock_worklist_frame.to_dict("records")
    readiness_rows = [] if ticker_readiness_frame is None else ticker_readiness_frame.to_dict("records")
    candidates = build_trusted_data_pilot_candidates(
        fundamentals_rows,
        peer_rows,
        readiness_rows,
        top_n=max(limit, 0),
    )
    rows = [
        {
            "Ticker": candidate.ticker,
            "Pilot Lane": pilot_lane_label(candidate.lane),
            "Scope": "Active universe" if candidate.active_universe else "Master universe",
            "Rank Reason": plain_pilot_input_copy(pilot_rank_reason(candidate)),
            "Missing Input": plain_pilot_input_copy(candidate.missing_input),
            "Review Decision": pilot_operator_decision(candidate),
            "Review Path": pilot_review_path(candidate.validation_path),
            "Trusted Input Target": pilot_trusted_row_path(candidate),
            "Local File Status": pilot_local_file_status(candidate, root=root),
            "Skip If": pilot_skip_condition(candidate),
            "Packet Command": f"make trusted-data-pilot-packet TICKER={candidate.ticker}",
            "Next Command": candidate.next_command,
            "Proof After Data Changes": candidate.proof_after_unlock,
            "Evidence Expectation": pilot_evidence_expectation(candidate),
            "Evidence Row": pilot_evidence_row_template(candidate),
        }
        for candidate in candidates[: max(limit, 0)]
    ]
    return pd.DataFrame(rows)


def trusted_pilot_lane_board_frame(
    fundamentals_peer_worklist_frame: pd.DataFrame | None,
    peer_unlock_worklist_frame: pd.DataFrame | None,
    ticker_readiness_frame: pd.DataFrame | None,
    *,
    limit: int = 10,
) -> pd.DataFrame:
    fundamentals_rows = [] if fundamentals_peer_worklist_frame is None else fundamentals_peer_worklist_frame.to_dict("records")
    peer_rows = [] if peer_unlock_worklist_frame is None else peer_unlock_worklist_frame.to_dict("records")
    readiness_rows = [] if ticker_readiness_frame is None else ticker_readiness_frame.to_dict("records")
    candidates = build_trusted_data_pilot_candidates(
        fundamentals_rows,
        peer_rows,
        readiness_rows,
        top_n=max(limit, 0),
    )
    rows = []
    for row in pilot_lane_summary_rows(candidates):
        lane = str(row.get("lane", ""))
        runbook = pilot_lane_runbook(lane)
        rows.append(
            {
                "Lane": row["lane_label"],
                "Candidates": row["candidate_count"],
                "Tickers": row["tickers"],
                "Current Blocker Theme": plain_pilot_input_copy(row["blocker_theme"]),
                "Status": row["status"],
                "Next Safe Command": row["next_safe_command"],
                "What Proves It": row["what_proves_lane"],
                "Rows / Files Needed": row["needed_rows_files"],
                "Rejected-Row Reports": row["rejected_row_reports"],
                "Readiness Proof": row["readiness_proof_command"],
                "Still Blocked When": row["remains_blocked_when"],
                "Locked / Manual Note": row["locked_manual_note"],
                "Ordered Steps": " ".join(f"{index}. {step}" for index, step in enumerate(runbook.ordered_steps, start=1)),
            }
        )
    return pd.DataFrame(rows)


def trusted_pilot_lane_cards(lane_frame: pd.DataFrame | None, *, limit: int = 3) -> list[dict[str, object]]:
    if lane_frame is None or lane_frame.empty:
        return [
            {
                "kicker": "LANE BOARD",
                "title": "Lane groups need current readiness rows",
                "body": "Run project-status first. If source-proof queues are exhausted, use provider setup instead of reopening stale pilot candidates.",
                "badges": ["read-only", "no fake rows"],
                "command": "make project-status",
            }
        ]
    cards: list[dict[str, object]] = []
    priority = {"review_only": 0, "safe_to_batch_dry_run": 1, "locked": 2}
    sorted_frame = lane_frame.copy()
    sorted_frame["_priority"] = sorted_frame["Status"].map(lambda value: priority.get(str(value), 9))
    sorted_frame["_count"] = pd.to_numeric(sorted_frame["Candidates"], errors="coerce").fillna(0).astype(int)
    sorted_frame = sorted_frame.sort_values(["_priority", "_count", "Lane"], ascending=[True, False, True])
    for _, row in sorted_frame.head(max(limit, 0)).iterrows():
        lane = _format_missing(row.get("Lane"), "Trusted-data lane")
        status = _format_missing(row.get("Status"), "review_only")
        count = _format_missing(row.get("Candidates"), "0")
        tickers = _format_missing(row.get("Tickers"), "-")
        blocker = _compact_fragment(row.get("Current Blocker Theme"), max_chars=180)
        proof = _compact_fragment(row.get("What Proves It"), max_chars=190)
        command = _format_missing(row.get("Next Safe Command"), "make trusted-data-pilot-candidates TOP_N=10")
        manual = _compact_fragment(row.get("Locked / Manual Note"), max_chars=150)
        usage_answer = _lane_usage_answer(status)
        body = (
            f"{usage_answer} "
            f"{count} candidate(s) in this lane; tickers: {tickers}. "
            f"{_card_sentence('Blocker theme', blocker)} "
            f"{_card_sentence('Proof', proof)} "
            f"Next safe command: {command}. "
            "Rows are not applied from this board; validate, preview, rejected-row checks, and rebuilt readiness must prove any change."
        )
        if manual:
            body = f"{body} {_card_sentence('Locked/manual lane', manual)}"
        cards.append(
            {
                "kicker": "LANE GROUP",
                "title": lane,
                "body": body,
                "badges": [status, "copy-only"],
                "command": command,
            }
        )
    return cards


def trusted_pilot_selection_note(
    fundamentals_peer_worklist_frame: pd.DataFrame | None,
    peer_unlock_worklist_frame: pd.DataFrame | None,
    ticker_readiness_frame: pd.DataFrame | None,
    *,
    limit: int = 10,
) -> str:
    fundamentals_rows = [] if fundamentals_peer_worklist_frame is None else fundamentals_peer_worklist_frame.to_dict("records")
    peer_rows = [] if peer_unlock_worklist_frame is None else peer_unlock_worklist_frame.to_dict("records")
    readiness_rows = [] if ticker_readiness_frame is None else ticker_readiness_frame.to_dict("records")
    candidates = build_trusted_data_pilot_candidates(
        fundamentals_rows,
        peer_rows,
        readiness_rows,
        top_n=max(limit, 0),
    )
    brief = pilot_selection_brief(candidates)
    quick_path = pilot_quick_path_lines(candidates)
    return " ".join([*brief, "Quick path:", *quick_path])


def trusted_pilot_preview_cards(preview_frame: pd.DataFrame | None, *, limit: int = 3) -> list[dict[str, object]]:
    if preview_frame is None or preview_frame.empty:
        return []
    cards: list[dict[str, object]] = []
    for _, row in preview_frame.head(max(limit, 0)).iterrows():
        ticker = _format_missing(row.get("Ticker"), "Ticker")
        lane = _format_missing(row.get("Pilot Lane"), "Trusted-data proof path")
        scope = _format_missing(row.get("Scope"), "Current queue")
        rank_reason = _compact_fragment(row.get("Rank Reason"), max_chars=170)
        missing_input = _compact_fragment(plain_pilot_input_copy(row.get("Missing Input")), max_chars=190)
        review_decision = _compact_fragment(row.get("Review Decision") or row.get("Operator Decision"), max_chars=170)
        trusted_target = _compact_fragment(row.get("Trusted Input Target") or row.get("Trusted Row Target"), max_chars=170)
        skip_if = _compact_fragment(row.get("Skip If"), max_chars=150)
        review_path = _compact_fragment(row.get("Review Path"), max_chars=165)
        proof = _compact_fragment(
            row.get("Proof After Data Changes") or row.get("Proof After Unlock"),
            f"make readiness-snapshot PROFILE={resolve_readiness_proof_profile()} && make reviewed-batch-compare PROFILE={resolve_readiness_proof_profile()} LANE=<lane> BATCH_ID=<reviewed_batch_id> REVIEW_DATE=<yyyy-mm-dd> && make stock-report-md TICKER=<ticker>",
            max_chars=175,
        )
        lane_command = _format_missing(row.get("Next Command"), "make trusted-data-pilot-candidates TOP_N=10")
        command = _format_missing(row.get("Packet Command"), f"make trusted-data-pilot-packet TICKER={ticker}")
        cards.append(
            {
                "kicker": "PILOT CANDIDATE",
                "title": f"{ticker}: {lane}",
                "body": (
                    f"{_card_sentence('Why this is next', rank_reason)} "
                    f"{_card_sentence('Missing input', missing_input)} "
                    f"Start with: {command}. "
                    f"Review lane: {review_path}; then run {lane_command}. "
                    f"{_card_sentence('Trusted input target', trusted_target)} "
                    f"{_card_sentence('Decision', review_decision)} "
                    f"{_card_sentence('Stop rule', skip_if)} "
                    f"{_card_sentence('Proof after data changes', proof)} "
                    "Outcome: Supported only after rebuilt readiness and the regenerated report prove it; Still blocked or Skip should stay visible when source proof is missing."
                ),
                "badges": [scope, "read-only"],
                "command": command,
            }
        )
    return cards
