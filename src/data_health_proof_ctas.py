from __future__ import annotations

import re

import pandas as pd

from src.data_health_console import data_health_operator_lane_from_query


def format_missing(value: object, fallback: str = "Not available") -> str:
    if value is None:
        return fallback
    try:
        if pd.isna(value):
            return fallback
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return fallback
    return text


def compact_card_fragment(
    value: object,
    fallback: str = "Not available",
    *,
    max_sentences: int = 1,
    max_chars: int = 180,
) -> str:
    text = format_missing(value, fallback)
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
    if parts:
        text = " ".join(parts[:max(1, max_sentences)])
    if len(text) > max_chars:
        text = text[: max(0, max_chars - 3)].rstrip() + "..."
    return text


def card_sentence(label: str, fragment: str) -> str:
    clean_label = str(label).strip()
    clean_fragment = format_missing(fragment)
    terminal = "" if clean_fragment.endswith((".", "?", "!", "...")) else "."
    return f"{clean_label}: {clean_fragment}{terminal}"


def data_health_operator_lane_url(lane_key: str) -> str:
    lane = data_health_operator_lane_from_query(lane_key)
    return f"?mode=operator&page=data-health&lane={lane}"


def data_health_dcf_input_proof_queue_dashboard_cards(frame: pd.DataFrame | None) -> list[dict[str, object]]:
    """Return the compact lane-level DCF proof queue summary before raw rows."""

    if frame is None or frame.empty:
        return [
            {
                "kicker": "DCF INPUT QUEUE",
                "title": "Refresh the DCF proof queue",
                "body": (
                    "No DCF input proof rows are loaded for this lane. Build the queue after readiness artifacts are current; "
                    "do not treat missing DCF fields as resolved without source proof. Open operator details for the copy-only command."
                ),
                "badges": ["blocked visible", "readiness first"],
                "command": "make dcf-input-proof-queue TOP_N=10",
            }
        ]
    work = frame.copy()
    family_summary = "no family counts loaded"
    if "Missing Input Family" in work.columns:
        families = work["Missing Input Family"].fillna("").astype(str).str.strip()
        family_counts = families.loc[families.ne("")].value_counts()
        if not family_counts.empty:
            family_summary = "; ".join(f"{family}: {count}" for family, count in family_counts.head(4).items())
    top = work.iloc[0]
    ticker = format_missing(top.get("Ticker"), "TICKER")
    family = format_missing(top.get("Missing Input Family"), "DCF input")
    next_command = format_missing(top.get("Next Proof Command"), "make dcf-input-proof-queue TOP_N=10")
    packet_command = format_missing(top.get("Proof Packet Command"), "DRY_RUN=1 make fundamentals-batch-proof TOP_N=10")
    stop_rule = compact_card_fragment(top.get("Stop Rule"), max_chars=190)
    source_mode = compact_card_fragment(top.get("Source Mode"), fallback="source proof required", max_chars=120)
    missing_fields = compact_card_fragment(top.get("Missing DCF Fields"), fallback=family, max_chars=120)
    return [
        {
            "kicker": "DCF INPUT QUEUE",
            "title": f"{len(work):,} queued DCF input row(s)",
            "body": (
                f"{card_sentence('Top input families', family_summary)} "
                "Start with one input family; keep DCF valuation blocked until source proof exists."
            ),
            "badges": ["source proof first", "blocked visible"],
            "command": "make dcf-input-proof-queue TOP_N=10",
        },
        {
            "kicker": "NEXT PROOF COMMAND",
            "title": f"{ticker} / {family}",
            "body": (
                f"{card_sentence('Missing fields', missing_fields)} "
                f"{card_sentence('Source path', source_mode)} "
                "Use this command to inspect proof; do not edit trusted rows from the summary card."
            ),
            "badges": ["next safe action", "read-only"],
            "command": next_command,
        },
        {
            "kicker": "PROOF PACKET",
            "title": "Preview a capped reviewed run",
            "body": (
                "Use the copyable packet command on this card. "
                "Gate: validate, preview, rejected-row review, then reviewed apply decision before any local row changes."
            ),
            "badges": ["dry-run first", "preview before apply"],
            "command": packet_command,
        },
        {
            "kicker": "STOP RULE",
            "title": "Do not proceed without source proof",
            "body": (
                f"{card_sentence('Stop if', stop_rule)} "
                "Missing prices, fundamentals, market cap, peers, or valuation inputs stay blocked; never infer them."
            ),
            "badges": ["no fabrication", "research-only"],
            "command": "Open the Fundamentals / DCF evidence drawer for reviewed source fields.",
        },
    ]


def data_health_lane_auto_context_cards(
    selected_lane_key: str,
    readiness_freshness: object | None = None,
) -> list[dict[str, object]]:
    lane = data_health_operator_lane_from_query(selected_lane_key)
    freshness_status = format_missing(getattr(readiness_freshness, "status", ""), "").lower()
    if lane in {"fundamentals", "peers"} and freshness_status in {"missing", "stale"}:
        lane_label = "DCF" if lane == "fundamentals" else "peer"
        refresh_command = format_missing(getattr(readiness_freshness, "refresh_command", ""), "make readiness")
        freshness_message = compact_card_fragment(getattr(readiness_freshness, "message", ""), max_chars=170)
        return [
            {
                "kicker": "FRESHNESS GATE",
                "title": f"Refresh readiness before {lane_label} proof planning",
                "body": (
                    f"{card_sentence('Freshness', freshness_message)} "
                    f"Do not use stale readiness artifacts as {lane_label} proof. Refresh first, then reopen this lane for planner context."
                ),
                "badges": ["refresh first", "blocked visible"],
                "command": refresh_command,
            }
        ]
    if lane == "fundamentals":
        return [
            {
                "kicker": "YOU CAME HERE FOR",
                "title": "DCF proof planning",
                "body": (
                    "Start with the DCF Proof Batch Planner inside the evidence drawer. "
                    "Review one missing input family, source route, packet preview, validation gate, proof record, and stop rule before touching source rows."
                ),
                "badges": ["planner context", "source-backed only"],
                "command": data_health_operator_lane_url("fundamentals"),
            }
        ]
    if lane == "peers":
        return [
            {
                "kicker": "YOU CAME HERE FOR",
                "title": "Peer proof planning",
                "body": (
                    "Start with the Peer Proof Batch Planner inside the evidence drawer. "
                    "Review source fields, write-back guard, duplicate checks, validation gates, proof record, and stop rule before peer rows change."
                ),
                "badges": ["planner context", "no inferred peers"],
                "command": data_health_operator_lane_url("peers"),
            }
        ]
    return []
