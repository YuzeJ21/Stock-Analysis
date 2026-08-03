from __future__ import annotations

import pandas as pd

from src.data_health_proof_ctas import card_sentence, compact_card_fragment, format_missing
from src.data_health_proof_planner import latest_outcome_for_lane


def proof_checklist_summary_frame(
    readiness_summary: dict[str, object],
    queue_outcome_summary: pd.DataFrame | None = None,
) -> pd.DataFrame:
    columns = [
        "Proof Lane",
        "Checklist Status",
        "Coverage Gap",
        "Latest Outcome",
        "Need Before Proceeding",
        "Next Drawer",
        "Stop Rule",
    ]
    price_ready = int(readiness_summary.get("price_ready") or 0)
    dcf_ready = int(readiness_summary.get("dcf_ready") or 0)
    peer_ready = int(readiness_summary.get("peer_ready") or 0)
    dcf_gap = max(price_ready - dcf_ready, 0)
    peer_gap = max(price_ready - peer_ready, 0)
    dcf_outcome = latest_outcome_for_lane(queue_outcome_summary, "fundamentals", "dcf", "share_count")
    peer_outcome = latest_outcome_for_lane(queue_outcome_summary, "peer")

    def _outcome(row: pd.Series) -> str:
        if row.empty:
            return "not_recorded"
        return format_missing(row.get("Latest Outcome"), "not_recorded").lower()

    dcf_status = "needs_source_fields" if dcf_gap else "ready_or_no_current_gap"
    peer_status = "needs_peer_source_proof" if peer_gap else "ready_or_no_current_gap"
    latest_dcf = _outcome(dcf_outcome)
    latest_peer = _outcome(peer_outcome)
    if latest_dcf in {"still_blocked", "skipped", "excluded"}:
        dcf_status = latest_dcf
    elif latest_dcf == "supported" and dcf_gap:
        dcf_status = "supported_but_more_rows_blocked"
    if latest_peer in {"still_blocked", "skipped", "excluded"}:
        peer_status = latest_peer
    elif latest_peer == "supported" and peer_gap:
        peer_status = "supported_but_more_rows_blocked"

    return pd.DataFrame(
        [
            {
                "Proof Lane": "DCF proof checklist",
                "Checklist Status": dcf_status,
                "Coverage Gap": f"{dcf_gap:,} price-ready row(s) still need trusted DCF inputs",
                "Latest Outcome": latest_dcf,
                "Need Before Proceeding": (
                    "Finish source fields, import guard, validate/preview/apply decision, rebuilt readiness, "
                    "changed counts, source files, and artifact review before calling DCF proof supported."
                ),
                "Next Drawer": "Open Fundamentals / DCF lane drawer",
                "Stop Rule": "Stop if revenue, free cash flow or FCF margin, shares outstanding, source files, or generated-artifact review are missing.",
            },
            {
                "Proof Lane": "Peer proof checklist",
                "Checklist Status": peer_status,
                "Coverage Gap": f"{peer_gap:,} price-ready row(s) still need source-backed peer proof",
                "Latest Outcome": latest_peer,
                "Need Before Proceeding": (
                    "Finish peer source fields, write-back guard, validate/preview/apply decision, rebuilt peer queue, "
                    "proof record fields, and artifact review before calling peer proof supported."
                ),
                "Next Drawer": "Open Peers lane drawer",
                "Stop Rule": "Stop if source-backed peer relationship, duplicate checks, source files, or generated-artifact review are missing.",
            },
        ],
        columns=columns,
    )


def proof_checklist_summary_cards(
    readiness_summary: dict[str, object],
    queue_outcome_summary: pd.DataFrame | None = None,
) -> list[dict[str, object]]:
    frame = proof_checklist_summary_frame(readiness_summary, queue_outcome_summary)
    if frame.empty:
        return [
            {
                "kicker": "PROOF CHECKLISTS",
                "title": "Proof checklist summary unavailable",
                "body": "Refresh readiness before relying on DCF or peer proof checklist status.",
                "badges": ["readiness first", "blocked visible"],
                "command": "make readiness-preview TOP_N=20",
            }
        ]
    blocking = frame.loc[~frame["Checklist Status"].astype(str).str.lower().isin({"ready_or_no_current_gap", "supported"})]
    first = blocking.iloc[0] if not blocking.empty else frame.iloc[0]
    return [
        {
            "kicker": "PROOF CHECKLISTS",
            "title": f"{len(blocking)} lane(s) need proof work",
            "body": (
                "DCF and peer proof status is summarized here before opening detailed drawers. "
                "This is data-readiness evidence, not analysis or recommendation output."
            ),
            "badges": ["drawer preview", "no inferred inputs"],
            "command": "make readiness-queue TOP_N=10",
        },
        {
            "kicker": str(first.get("Proof Lane", "Proof lane")).upper(),
            "title": str(first.get("Checklist Status", "not_recorded")).replace("_", " "),
            "body": (
                f"{card_sentence('Gap', first.get('Coverage Gap'))} "
                f"{card_sentence('Latest outcome', first.get('Latest Outcome'))} "
                f"{card_sentence('Needed', compact_card_fragment(first.get('Need Before Proceeding'), max_chars=190))}"
            ),
            "badges": ["finish proof", "source-backed only"],
            "command": str(first.get("Next Drawer", "Open Data Health lane drawer")),
        },
    ]
