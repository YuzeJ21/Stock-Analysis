"""Universe scope helpers for readiness-first dashboard views."""

from __future__ import annotations

import pandas as pd


def _safe_int(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _bool_series(frame: pd.DataFrame, column: str) -> pd.Series:
    if frame.empty or column not in frame.columns:
        return pd.Series(False, index=frame.index)
    return frame[column].astype(str).str.strip().str.lower().isin({"true", "1", "yes"})


def universe_scope_counts(summary: dict[str, object], ticker_readiness_frame: pd.DataFrame | None) -> dict[str, int]:
    """Return master, active, and analysis-ready counts without requiring full-table rendering."""

    frame = ticker_readiness_frame if ticker_readiness_frame is not None else pd.DataFrame()
    master = _safe_int(summary.get("master_universe") or summary.get("universe_count"))
    active = _safe_int(summary.get("active_universe"))
    price_ready = _safe_int(summary.get("price_ready"))
    dcf_ready = _safe_int(summary.get("dcf_ready"))
    peer_ready = _safe_int(summary.get("peer_ready"))

    if not frame.empty:
        if not master:
            master = len(frame)
        if not active:
            active = int(_bool_series(frame, "in_active_universe").sum())
        if not price_ready:
            price_ready = int(_bool_series(frame, "price_ready").sum())
        if not dcf_ready:
            dcf_ready = int(_bool_series(frame, "dcf_ready").sum())
        if not peer_ready:
            peer_ready = int(_bool_series(frame, "peer_ready").sum())

    return {
        "master": master,
        "active": active,
        "price_ready": price_ready,
        "dcf_ready": dcf_ready,
        "peer_ready": peer_ready,
    }


def universe_scope_workflow_cards(
    summary: dict[str, object],
    ticker_readiness_frame: pd.DataFrame | None,
) -> list[dict[str, object]]:
    """Return compact cards that explain safe broad-universe review scope."""

    counts = universe_scope_counts(summary, ticker_readiness_frame)
    master = counts["master"]
    active = counts["active"]
    price_ready = counts["price_ready"]
    dcf_ready = counts["dcf_ready"]
    peer_ready = counts["peer_ready"]
    return [
        {
            "kicker": "SCOPE MAP",
            "title": f"{master} master rows; {active} active-review rows",
            "body": (
                f"Price-ready subset: {price_ready}. DCF-ready subset: {dcf_ready}. Peer-ready subset: {peer_ready}. "
                "The master universe is coverage planning, not proof that every analysis surface is ready."
            ),
            "badges": ["master != ready", "active first"],
            "command": "make status-check TOP_N=5",
        },
        {
            "kicker": "SAFE FILTER PATH",
            "title": "Start narrow, then widen only after review",
            "body": (
                "Use Active research only, ticker search, sector/theme filters, ready-only states, and capped row limits before opening broader views. "
                "Single-stock lookup can inspect known master-universe tickers one at a time without forcing full-market analysis."
            ),
            "badges": ["lazy scope", "row-limited"],
            "command": "make readiness-queue TOP_N=10",
        },
        {
            "kicker": "STOP RULE",
            "title": "Do not turn broad coverage into broad conclusions",
            "body": (
                "Keep missing fundamentals, shares, peers, earnings, analyst estimates, valuation inputs, and review metrics blocked until trusted proof gates pass."
            ),
            "badges": ["blocked visible", "research-only"],
            "command": "make data-coverage-proof-queues TOP_N=10",
        },
    ]
