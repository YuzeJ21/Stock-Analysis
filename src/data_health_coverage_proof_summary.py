from __future__ import annotations

import pandas as pd

from src.data_health_proof_ctas import card_sentence, compact_card_fragment, format_missing


def fundamentals_peer_metrics_queue_cards(frame: pd.DataFrame | None, *, limit: int = 3) -> list[dict[str, object]]:
    """Return compact next-layer readiness cards after broad price coverage."""

    if frame is None or frame.empty:
        return [
            {
                "kicker": "READINESS QUEUE",
                "title": "Run readiness before queue review",
                "body": (
                    "The next layer needs saved readiness artifacts before it can summarize fundamentals, peer, optional, "
                    "and metric blockers."
                ),
                "badges": ["read-only", "blocked visible"],
                "command": "make readiness-queue TOP_N=10",
            }
        ]

    work = frame.copy()
    work["_blocked_partial"] = (
        pd.to_numeric(work.get("Blocked", 0), errors="coerce").fillna(0)
        + pd.to_numeric(work.get("Partial", 0), errors="coerce").fillna(0)
    )
    work = work.sort_values(["_blocked_partial", "Lane"], ascending=[False, True])
    cards: list[dict[str, object]] = [
        {
            "kicker": "NEXT READINESS LAYER",
            "title": "What can I use by lane?",
            "body": (
                "One answer per lane: use ready rows, treat partial rows as limited context, and keep blocked rows out "
                "of analysis until source proof clears. Detail stays in collapsed evidence drawers."
            ),
            "badges": ["after price coverage", "readiness first"],
            "command": "make readiness-queue TOP_N=10",
        }
    ]
    for _, row in work.head(max(limit, 0)).iterrows():
        lane = format_missing(row.get("Lane"), "Readiness lane")
        state = _public_status_label(row.get("State"))
        blocked_partial = int(row.get("_blocked_partial", 0) or 0)
        ready = int(pd.to_numeric(pd.Series([row.get("Ready", 0)]), errors="coerce").fillna(0).iloc[0])
        total = int(pd.to_numeric(pd.Series([row.get("Total", 0)]), errors="coerce").fillna(0).iloc[0])
        missing = compact_card_fragment(row.get("Missing Input Families"), max_chars=150)
        proof_gate = compact_card_fragment(row.get("Proof Gate"), max_chars=170)
        source_mode = format_missing(row.get("Source Mode"), "local readiness")
        command = format_missing(row.get("Next Safe Command"), "make readiness-queue TOP_N=10")
        usable_answer = _lane_usable_answer(state, ready=ready, total=total, blocked_partial=blocked_partial)
        cards.append(
            {
                "kicker": "QUEUE LANE",
                "title": lane,
                "body": (
                    f"{card_sentence('Usable now', usable_answer)} "
                    f"{card_sentence('Blocked by', missing)} "
                    f"{card_sentence('Proof gate', proof_gate)} "
                    "Next: Open the evidence drawer for copy-only commands and row detail."
                ),
                "badges": [state, source_mode],
                "command": command,
            }
        )
    return cards


def data_coverage_proof_queue_cards(frame: pd.DataFrame | None, *, limit: int = 3) -> list[dict[str, object]]:
    """Return compact proof-queue cards before raw source-proof rows."""

    if frame is None or frame.empty:
        return [
            {
                "kicker": "PROOF QUEUES",
                "title": "Run readiness before proof queue review",
                "body": "DCF, shares, fundamentals, peer mapping, and peer valuation proof queues need saved readiness artifacts.",
                "badges": ["read-only", "blocked visible"],
                "command": "make data-coverage-proof-queues TOP_N=10",
            }
        ]

    work = frame.copy()
    work["_queued"] = pd.to_numeric(work.get("Queued Rows", 0), errors="coerce").fillna(0)
    work = work.sort_values(["_queued", "Queue"], ascending=[False, True])
    cards: list[dict[str, object]] = [
        {
            "kicker": "DATA COVERAGE PROOF",
            "title": "Proof queues before row work",
            "body": (
                "Open the exact DCF input, shares-outstanding, trusted fundamentals, peer mapping, or peer valuation "
                "proof queue before touching raw CSV rows."
            ),
            "badges": ["source proof first", "copy-only commands"],
            "command": "make data-coverage-proof-queues TOP_N=10",
        }
    ]
    for _, row in work.head(max(limit, 0)).iterrows():
        queue = format_missing(row.get("Queue"), "Proof queue")
        state = _public_status_label(row.get("State"))
        queued = int(row.get("_queued", 0) or 0)
        blockers = compact_card_fragment(row.get("Top Blockers"), max_chars=150)
        stop_rule = compact_card_fragment(row.get("Stop Rule"), max_chars=170)
        command = format_missing(row.get("Next Safe Command"), "make data-coverage-proof-queues TOP_N=10")
        cards.append(
            {
                "kicker": "PROOF QUEUE",
                "title": queue,
                "body": (
                    f"{queued:,} queued row(s). "
                    f"{card_sentence('Top blockers', blockers)} "
                    f"{card_sentence('Stop rule', stop_rule)}"
                ),
                "badges": [state, "read-only"],
                "command": command,
            }
        )
    return cards


def _public_status_label(value: object, fallback: str = "Not available") -> str:
    text = format_missing(value, fallback=fallback)
    return text.replace("_", " ").replace("-", " ").title()


def _lane_usable_answer(state: str, *, ready: int, total: int, blocked_partial: int) -> str:
    normalized = str(state or "").strip().lower()
    if normalized == "ready" or (total > 0 and ready >= total and blocked_partial == 0):
        return "usable now with current local proof"
    if ready > 0 or normalized == "partial":
        return "partly usable; ready rows can support research context, locked fields stay blocked"
    return "not usable yet; wait for source proof or a reviewed exclusion"
