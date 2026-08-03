from __future__ import annotations

import pandas as pd
from src.profile_context import READINESS_PREVIEW_COMMAND, READINESS_PREVIEW_NOTE

from src.data_health_summary import bool_series


def peer_mapping_studio_summary_cards(
    peer_readiness_frame: pd.DataFrame | None,
    ticker_readiness_frame: pd.DataFrame | None = None,
) -> list[dict[str, object]]:
    if peer_readiness_frame is None or peer_readiness_frame.empty:
        return [
            {
                "kicker": "PEER STUDIO",
                "title": "Peer readiness not ready yet",
                "body": f"Inspect peer readiness before using the mapping studio. {READINESS_PREVIEW_NOTE}",
                "badges": ["blocked"],
                "command": READINESS_PREVIEW_COMMAND,
            }
        ]

    frame = peer_readiness_frame.copy()
    if "ticker" in frame.columns:
        frame["ticker"] = frame["ticker"].astype(str).str.upper().str.strip()
    if ticker_readiness_frame is not None and not ticker_readiness_frame.empty and "ticker" in ticker_readiness_frame.columns:
        readiness_columns = [
            column
            for column in ["ticker", "dcf_ready", "in_active_universe"]
            if column in ticker_readiness_frame.columns
        ]
        readiness = ticker_readiness_frame[readiness_columns].copy()
        readiness["ticker"] = readiness["ticker"].astype(str).str.upper().str.strip()
        frame = frame.merge(readiness, on="ticker", how="left", suffixes=("", "_ticker"))

    peer_ready = bool_series(frame, "peer_ready")
    dcf_ready = bool_series(frame, "dcf_ready")
    blocker = frame.get("peer_blocker_type", pd.Series("", index=frame.index)).fillna("").astype(str)
    missing_mapping = blocker.eq("missing_peer_mapping")
    peer_price_missing = blocker.eq("peer_price_missing")
    peer_fundamentals_missing = blocker.eq("peer_fundamentals_missing")
    valuation_blocked = blocker.eq("peer_valuation_blocked") | (~bool_series(frame, "peer_valuation_comparison_ready") & ~peer_ready)
    trend_ready = bool_series(frame, "peer_trend_comparison_ready")
    active = bool_series(frame, "in_active_universe")

    return [
        {
            "kicker": "DCF PEER BLOCKERS",
            "title": f"{int((dcf_ready & ~peer_ready).sum())} tickers",
            "body": "DCF-ready names that still need source-backed peer mappings or peer metric follow-through.",
            "badges": ["dcf-ready", "peer-blocked"],
            "command": "make peer-mapping-queue TOP_N=25",
        },
        {
            "kicker": "MISSING MAPPINGS",
            "title": f"{int(missing_mapping.sum())} tickers",
            "body": f"Active-universe affected: {int((missing_mapping & active).sum())}. Add transparent mappings through peer import files and preview before apply.",
            "badges": ["manual peers", "source-backed"],
            "command": "make templates",
        },
        {
            "kicker": "PEER PRICE GAPS",
            "title": f"{int(peer_price_missing.sum())} tickers",
            "body": "Mapped peers exist, but at least one peer lacks enough price rows for trend comparison.",
            "badges": ["prices", "follow-through"],
            "command": "make price-history-proof-queue TOP_N=25",
        },
        {
            "kicker": "PEER FUNDAMENTALS",
            "title": f"{int(peer_fundamentals_missing.sum())} tickers",
            "body": "Mapped peers exist, but peer fundamentals are not ready for valuation comparison.",
            "badges": ["fundamentals", "valuation-blocked"],
            "command": "make sec-stage-queue TOP_N=25",
        },
        {
            "kicker": "TREND POSSIBLE",
            "title": f"{int(trend_ready.sum())} tickers",
            "body": "Peer trend comparison can be reviewed before peer valuation is fully unlocked.",
            "badges": ["trend ready", "not valuation"],
            "command": READINESS_PREVIEW_COMMAND,
        },
        {
            "kicker": "VALUATION BLOCKED",
            "title": f"{int(valuation_blocked.sum())} tickers",
            "body": "Do not show peer valuation conclusions until peer fundamentals and valuation metrics are present.",
            "badges": ["data-honest", "blocked"],
            "command": "make imports-validate",
        },
    ]
