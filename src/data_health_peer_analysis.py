from __future__ import annotations

import pandas as pd
from src.profile_context import active_readiness_inspection_route

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
    inspection_command, inspection_note = active_readiness_inspection_route()
    if peer_readiness_frame is None or peer_readiness_frame.empty:
        return [
            {
                "kicker": "PEER ANALYSIS",
                "title": "Peer readiness not loaded",
                "body": f"Inspect peer readiness before interpreting peer trend or peer valuation context. Missing peer output means peer analysis stays locked. {inspection_note}",
                "badges": ["readiness first", "no inferred peers"],
                "command": inspection_command,
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
                "Peer valuation is separate and needs source-backed mappings plus peer valuation inputs. "
                f"{inspection_note}"
            ),
            "badges": ["trend before valuation", "module-gated"],
            "command": inspection_command,
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


def peer_function_quality_frame(
    peer_readiness_frame: pd.DataFrame | None,
    peer_unlock_worklist_frame: pd.DataFrame | None = None,
) -> pd.DataFrame:
    if peer_readiness_frame is None or peer_readiness_frame.empty:
        return pd.DataFrame(
            [
                {
                    "Peer Area": "Peer workflow",
                    "Current Coverage": "Peer readiness not ready yet",
                    "Supported Today": "Nothing yet; run readiness before interpreting peer context.",
                    "Not Supported Yet": "Peer trend or valuation comparison.",
                    "Methodology / Provenance": "Project peer readiness checks after make readiness.",
                    "Next Step": "make readiness",
                }
            ]
        )

    frame = peer_readiness_frame.copy()
    peer_ready = bool_series(frame, "peer_ready")
    trend_ready = bool_series(frame, "peer_trend_comparison_ready")
    valuation_ready = bool_series(frame, "peer_valuation_comparison_ready")
    dcf_comparison_ready = bool_series(frame, "peer_dcf_comparison_ready")
    blocker = frame.get("peer_blocker_type", pd.Series("", index=frame.index)).fillna("").astype(str)
    missing_mapping = int(blocker.eq("missing_peer_mapping").sum())
    peer_price_missing = int(blocker.eq("peer_price_missing").sum())
    peer_fundamentals_missing = int(blocker.eq("peer_fundamentals_missing").sum())
    valuation_blocked = int((~valuation_ready & ~peer_ready).sum())
    queued = 0 if peer_unlock_worklist_frame is None else int(len(peer_unlock_worklist_frame))

    return pd.DataFrame(
        [
            {
                "Peer Area": "Source-backed mappings",
                "Current Coverage": f"{missing_mapping} ticker(s) missing mappings; {queued} unlock row(s) queued",
                "Supported Today": "Prioritizing which manual peer rows to add to data/imports/peers.csv.",
                "Not Supported Yet": "Trusted peer comparison until relationships are source-backed or clearly marked as fallback context.",
                "Methodology / Provenance": "Project peer readiness and peer unlock worklist generation; peer-selection rules stay in this repository.",
                "Next Step": "make peer-mapping-queue TOP_N=25",
            },
            {
                "Peer Area": "Peer trend comparison",
                "Current Coverage": f"{int(trend_ready.sum())} ticker(s) trend-ready",
                "Supported Today": "Relative price or momentum context when mapped peers have enough local price rows.",
                "Not Supported Yet": "Peer-relative valuation or quality conclusions.",
                "Methodology / Provenance": "Project price/momentum readiness checks for mapped peers.",
                "Next Step": "make readiness",
            },
            {
                "Peer Area": "Peer valuation comparison",
                "Current Coverage": f"{int(valuation_ready.sum())} ticker(s) valuation-ready; {valuation_blocked} still blocked",
                "Supported Today": "Peer-relative valuation only after peer mappings and peer valuation inputs are ready.",
                "Not Supported Yet": "Valuation conclusions when peer fundamentals, peer metrics, or mapped peer inputs are missing.",
                "Methodology / Provenance": "Project peer valuation readiness gates; missing peer inputs are withheld, not inferred.",
                "Next Step": "make imports-validate",
            },
            {
                "Peer Area": "Peer DCF comparison",
                "Current Coverage": f"{int(dcf_comparison_ready.sum())} ticker(s) DCF-peer-ready",
                "Supported Today": "DCF peer context when both subject and mapped peer valuation inputs pass readiness.",
                "Not Supported Yet": "Using DCF-ready subject companies as if peer-relative valuation is ready.",
                "Methodology / Provenance": "Project DCF and peer readiness intersection checks.",
                "Next Step": "make dcf-readiness",
            },
            {
                "Peer Area": "Peer data follow-through",
                "Current Coverage": f"{peer_price_missing} price-gap ticker(s); {peer_fundamentals_missing} fundamentals-gap ticker(s)",
                "Supported Today": "Finding whether peer blockers are price rows, fundamentals rows, or peer metrics.",
                "Not Supported Yet": "Treating sector or industry fallback as trusted manual peer valuation.",
                "Methodology / Provenance": "Project blocker classification with explicit fallback labeling.",
                "Next Step": "make price-history-proof-queue TOP_N=25",
            },
            {
                "Peer Area": "Dependencies",
                "Current Coverage": "Support layer only.",
                "Supported Today": "Data handling, table display, tests, and optional development review.",
                "Not Supported Yet": "Replacing source-backed peer mappings or project peer-readiness rules.",
                "Methodology / Provenance": "Standard libraries and optional provider adapters support data handling; peer rules run from this repository.",
                "Next Step": "make project-status",
            },
        ]
    )
