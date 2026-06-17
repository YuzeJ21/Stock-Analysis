from __future__ import annotations

import pandas as pd

from src.data_health_proof_ctas import card_sentence, compact_card_fragment, format_missing
from src.readiness_queue_dashboard import build_readiness_queue_outcome_summary_frame


def readiness_queue_outcome_summary_frame(
    queue_frame: pd.DataFrame | None,
    batch_proof_frame: pd.DataFrame | None = None,
) -> pd.DataFrame:
    return build_readiness_queue_outcome_summary_frame(queue_frame, batch_proof_frame)


def readiness_queue_outcome_summary_cards(frame: pd.DataFrame | None) -> list[dict[str, object]]:
    if frame is None or frame.empty:
        return [
            {
                "kicker": "OUTCOME SUMMARY",
                "title": "No queue outcomes available",
                "body": (
                    "Run the readiness queue, then use reviewed batch proof rows to see supported, still blocked, "
                    "skipped, and excluded lane outcomes."
                ),
                "badges": ["ledger first", "research-only"],
                "command": "make readiness-queue TOP_N=10",
            }
        ]
    outcome_counts = frame["Latest Outcome"].fillna("not_recorded").astype(str).str.lower().value_counts().to_dict()
    supported = int(outcome_counts.get("supported", 0))
    still_blocked = int(outcome_counts.get("still_blocked", 0))
    skipped = int(outcome_counts.get("skipped", 0))
    excluded = int(outcome_counts.get("excluded", 0))
    not_recorded = int(outcome_counts.get("not_recorded", 0))
    rows_with_outcomes = frame.loc[~frame["Latest Outcome"].fillna("").astype(str).str.lower().eq("not_recorded")]
    latest_row = rows_with_outcomes.iloc[0] if not rows_with_outcomes.empty else frame.iloc[0]
    latest_lane = format_missing(latest_row.get("Lane"), "Readiness lane")
    latest_outcome = format_missing(latest_row.get("Latest Outcome"), "not_recorded").replace("_", " ")
    latest_date = format_missing(latest_row.get("Review Date"), "not recorded")
    latest_cue = compact_card_fragment(latest_row.get("Operator Cue"), max_chars=190)
    return [
        {
            "kicker": "QUEUE OUTCOMES",
            "title": f"{supported} supported / {still_blocked} still blocked",
            "body": (
                f"{skipped} skipped, {excluded} excluded, and {not_recorded} lane(s) without a reviewed batch outcome. "
                "This is proof-ledger status, not a security ranking or recommendation."
            ),
            "badges": ["durable ledger", "batch outcomes"],
            "command": "make reviewed-batch-proof",
        },
        {
            "kicker": "LATEST LANE OUTCOME",
            "title": f"{latest_lane}: {latest_outcome}",
            "body": (
                f"{card_sentence('Review date', latest_date)} "
                f"{card_sentence('Operator cue', latest_cue)} "
                "Open the lane drawer only when you need blocker examples, packet commands, or proof-record detail."
            ),
            "badges": ["supported/still-blocked/skipped/excluded", "no drawer required"],
            "command": format_missing(latest_row.get("Proof Ledger Command"), "make reviewed-batch-proof"),
        },
    ]
