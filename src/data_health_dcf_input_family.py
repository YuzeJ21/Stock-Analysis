from __future__ import annotations

import pandas as pd

from src.data_health_proof_ctas import card_sentence, compact_card_fragment, format_missing
from src.dcf_input_proof_queue import DcfInputProofRow


def dcf_input_family_options(frame: pd.DataFrame | None) -> list[str]:
    if frame is None or frame.empty or "Missing Input Family" not in frame.columns:
        return ["All families"]
    families = frame["Missing Input Family"].fillna("").astype(str).str.strip()
    counts = families.loc[families.ne("")].value_counts()
    if counts.empty:
        return ["All families"]
    return ["All families"] + [f"{family} ({count})" for family, count in counts.items()]


def dcf_input_family_key(selection: object) -> str:
    text = format_missing(selection, "All families")
    if text == "All families":
        return ""
    return text.split(" (", 1)[0].strip()


def filter_dcf_input_queue_by_family(frame: pd.DataFrame | None, selection: object) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame() if frame is None else frame.copy()
    family = dcf_input_family_key(selection)
    if not family or "Missing Input Family" not in frame.columns:
        return frame.copy()
    mask = frame["Missing Input Family"].fillna("").astype(str).str.strip().eq(family)
    return frame.loc[mask].copy()


def dcf_input_rows_from_frame(frame: pd.DataFrame | None) -> list[DcfInputProofRow]:
    if frame is None or frame.empty:
        return []
    rows = []
    for _, item in frame.iterrows():
        rows.append(
            DcfInputProofRow(
                priority=int(item.get("Priority", len(rows) + 1) or len(rows) + 1),
                ticker=format_missing(item.get("Ticker"), ""),
                scope=format_missing(item.get("Scope"), ""),
                missing_input_family=format_missing(item.get("Missing Input Family"), ""),
                missing_dcf_fields=format_missing(item.get("Missing DCF Fields"), ""),
                ready_dcf_inputs=format_missing(item.get("Ready DCF Inputs"), ""),
                dcf_input_status=format_missing(item.get("DCF Input Status"), ""),
                source_mode=format_missing(item.get("Source Mode"), ""),
                next_safe_command=format_missing(item.get("Next Proof Command"), ""),
                proof_packet_command=format_missing(item.get("Proof Packet Command"), ""),
                validation_sequence=format_missing(item.get("Validation Sequence"), ""),
                proof_after_update=format_missing(item.get("Proof After Update"), ""),
                stop_rule=format_missing(item.get("Stop Rule"), ""),
                source_note=format_missing(item.get("Source Note"), ""),
            )
        )
    return rows


def dcf_input_family_filter_cards(
    full_frame: pd.DataFrame | None,
    filtered_frame: pd.DataFrame | None,
    selection: object,
) -> list[dict[str, object]]:
    if full_frame is None or full_frame.empty:
        return [
            {
                "kicker": "DCF FILTER",
                "title": "No proof-family rows loaded",
                "body": "Run the DCF input proof queue before filtering by missing input family.",
                "badges": ["read-only", "blocked visible"],
                "command": "make dcf-input-proof-queue TOP_N=10",
            }
        ]
    family = dcf_input_family_key(selection) or "all families"
    filtered_count = 0 if filtered_frame is None else len(filtered_frame)
    total_count = len(full_frame)
    if filtered_frame is None or filtered_frame.empty:
        next_command = "make dcf-input-proof-queue TOP_N=10"
        first_ticker = "No ticker"
        first_stop = "No rows match this family filter."
    else:
        first = filtered_frame.iloc[0]
        next_command = format_missing(first.get("Next Proof Command"), "make dcf-input-proof-queue TOP_N=10")
        first_ticker = format_missing(first.get("Ticker"), "Ticker")
        first_stop = compact_card_fragment(first.get("Stop Rule"), max_chars=170)
    return [
        {
            "kicker": "DCF FILTER",
            "title": f"{family}: {filtered_count:,} of {total_count:,}",
            "body": (
                f"Showing {filtered_count:,} row(s) for {family}. "
                f"{card_sentence('First ticker', first_ticker)} "
                f"{card_sentence('Stop rule', first_stop)} "
                "Switch families to triage one proof lane at a time."
            ),
            "badges": ["family filter", "proof first"],
            "command": next_command,
        }
    ]
