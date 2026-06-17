from __future__ import annotations

import pandas as pd

from src.data_health_summary import bool_series


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


def peer_analysis_boundary_cards(
    peer_readiness_frame: pd.DataFrame | None,
    ticker_readiness_frame: pd.DataFrame | None = None,
) -> list[dict[str, object]]:
    if peer_readiness_frame is None or peer_readiness_frame.empty:
        return [
            {
                "kicker": "PEER ANALYSIS",
                "title": "Peer readiness not loaded",
                "body": "Run make readiness before interpreting peer trend or peer valuation context. Missing peer output means peer analysis stays locked.",
                "badges": ["readiness first", "no inferred peers"],
                "command": "make readiness",
            }
        ]

    frame = peer_readiness_frame.copy()
    if "ticker" in frame.columns:
        frame["ticker"] = frame["ticker"].astype(str).str.upper().str.strip()
    if (
        ticker_readiness_frame is not None
        and not ticker_readiness_frame.empty
        and "ticker" in frame.columns
        and "ticker" in ticker_readiness_frame.columns
    ):
        readiness_columns = [
            column
            for column in ["ticker", "dcf_ready", "in_active_universe"]
            if column in ticker_readiness_frame.columns
        ]
        readiness = ticker_readiness_frame[readiness_columns].copy()
        readiness["ticker"] = readiness["ticker"].astype(str).str.upper().str.strip()
        frame = frame.merge(readiness, on="ticker", how="left", suffixes=("", "_ticker"))

    peer_ready = bool_series(frame, "peer_ready")
    trend_ready = bool_series(frame, "peer_trend_comparison_ready")
    valuation_ready = bool_series(frame, "peer_valuation_comparison_ready")
    dcf_ready = bool_series(frame, "dcf_ready")
    active = bool_series(frame, "in_active_universe")
    blocker = frame.get("peer_blocker_type", pd.Series("", index=frame.index)).fillna("").astype(str)
    missing_mapping = blocker.eq("missing_peer_mapping")
    price_gap = blocker.eq("peer_price_missing")
    fundamentals_gap = blocker.eq("peer_fundamentals_missing")
    valuation_locked = ~valuation_ready
    dcf_ready_peer_blocked = dcf_ready & ~peer_ready
    active_dcf_peer_blocked = active & dcf_ready_peer_blocked
    next_ticker = "Not available"
    if "ticker" in frame.columns:
        candidates = frame.loc[active_dcf_peer_blocked].copy()
        if candidates.empty:
            candidates = frame.loc[dcf_ready_peer_blocked].copy()
        if candidates.empty:
            candidates = frame.loc[~peer_ready].copy()
        if not candidates.empty:
            next_ticker = _format_missing(candidates.sort_values("ticker", kind="stable").iloc[0].get("ticker"), "Not available")
    peer_focus_command = f"make focus-peers TICKER={next_ticker}" if next_ticker != "Not available" else "make peer-mapping-queue TOP_N=25"

    return [
        {
            "kicker": "WHAT PEERS CAN SUPPORT NOW",
            "title": f"{int(trend_ready.sum())} trend-ready / {int(valuation_ready.sum())} valuation-ready",
            "body": (
                "Peer trend context can be reviewed when mapped peers have enough price history. "
                "Peer valuation is separate and needs source-backed mappings plus peer valuation inputs."
            ),
            "badges": ["trend before valuation", "module-gated"],
            "command": "make readiness",
        },
        {
            "kicker": "WHAT IS STILL LOCKED",
            "title": f"{int(valuation_locked.sum())} peer valuation row(s) locked",
            "body": (
                f"Missing mappings: {int(missing_mapping.sum())}. Peer price gaps: {int(price_gap.sum())}. "
                f"Peer fundamentals gaps: {int(fundamentals_gap.sum())}. Locked peer valuation is not a company conclusion."
            ),
            "badges": ["specific blockers", "no inference"],
            "command": "make peer-mapping-queue TOP_N=25",
        },
        {
            "kicker": "DCF-READY BUT PEER-BLOCKED",
            "title": f"{int(dcf_ready_peer_blocked.sum())} company row(s)",
            "body": (
                f"{int(active_dcf_peer_blocked.sum())} active-universe row(s) can have standalone DCF reviewed while peer-relative valuation stays withheld."
            ),
            "badges": ["standalone DCF ok", "peer valuation withheld"],
            "command": peer_focus_command,
        },
        {
            "kicker": "COPY NEXT",
            "title": "Prove peers before relative valuation",
            "body": (
                "Inspect the next peer-limited ticker first. "
                "Peer trend can be reviewed only from mapped peer price history; peer-relative valuation, premium/discount, "
                "and peer DCF comparison stay locked until source-backed mappings plus peer valuation inputs pass readiness."
            ),
            "badges": ["copy-only", "trend is not valuation"],
            "command": peer_focus_command,
        },
        {
            "kicker": "PEER PROOF LADDER",
            "title": "Mapping -> trend -> valuation proof",
            "body": (
                "Use this sequence before reading peer-relative output: source-backed peer mappings in data/imports/peers.csv, "
                "then mapped peer price history for trend context, then peer fundamentals and valuation inputs for peer valuation. "
                "Trend-ready does not mean valuation-ready. Exact commands are copyable from this card and the peer queue; "
                "validate and preview trusted rows, apply only reviewed rows, then rebuild readiness before reading peer valuation."
            ),
            "badges": ["method proof", "trend before valuation"],
            "command": peer_focus_command,
        },
        {
            "kicker": "TRUSTED INPUT PATH",
            "title": "data/imports/peers.csv",
            "body": (
                "Add only source-backed peer mappings, then run make imports-validate, make imports-preview, "
                "and make imports-apply. Rebuild with make readiness and make peer-mapping-queue TOP_N=25 before reading peer valuation. "
                "Sector or industry fallback is context, not trusted peer valuation data."
            ),
            "badges": ["source-backed only", "preview first"],
            "command": "make templates",
        },
    ]
