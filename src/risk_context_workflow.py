"""Risk-context workflow helpers for Data Health views."""

from __future__ import annotations

import pandas as pd


def split_risk_context_by_price_ready(frame: pd.DataFrame | None, unavailable_statuses: set[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    if frame is None or frame.empty:
        return pd.DataFrame(), pd.DataFrame()
    status_column = next((column for column in ["LiquidityStatus", "CorrelationStatus"] if column in frame.columns), "")
    if not status_column:
        return frame.copy(), pd.DataFrame(columns=frame.columns)
    status = frame[status_column].fillna("").astype(str).str.strip().str.lower()
    unavailable = status.isin({value.lower() for value in unavailable_statuses})
    return frame.loc[~unavailable].copy(), frame.loc[unavailable].copy()


def data_health_risk_context_cards(
    liquidity_frame: pd.DataFrame | None,
    correlation_frame: pd.DataFrame | None,
) -> list[dict[str, object]]:
    liquidity_ready, liquidity_unavailable = split_risk_context_by_price_ready(
        liquidity_frame,
        {"Insufficient Price Data"},
    )
    correlation_ready, correlation_unavailable = split_risk_context_by_price_ready(
        correlation_frame,
        {"Insufficient Data", "Insufficient Overlap"},
    )

    liquidity_total = 0 if liquidity_frame is None else len(liquidity_frame)
    correlation_total = 0 if correlation_frame is None else len(correlation_frame)
    proxy_count = 0
    if liquidity_frame is not None and not liquidity_frame.empty:
        proxy_columns = [column for column in ["LiquidityInputsUsed", "Reason", "LiquidityBlindSpots"] if column in liquidity_frame.columns]
        if proxy_columns:
            proxy_text = liquidity_frame[proxy_columns].fillna("").astype(str).agg(" ".join, axis=1).str.lower()
            proxy_count = int(proxy_text.str.contains("proxy|approximation|close-to-close", regex=True, na=False).sum())
        elif "VolatilityProxy20D" in liquidity_frame.columns:
            proxy_count = int(pd.to_numeric(liquidity_frame["VolatilityProxy20D"], errors="coerce").notna().sum())

    return [
        {
            "kicker": "LIQUIDITY READINESS",
            "title": f"{len(liquidity_ready):,} ready / {liquidity_total:,} rows",
            "body": (
                f"{len(liquidity_unavailable):,} row(s) still need local price and volume history before liquidity context is usable. "
                "Use liquidity rows as review context only; blocked rows stay visible instead of becoming scores."
            ),
            "badges": ["price history", "volume-gated"],
            "command": "make price-worklist TOP_N=25",
        },
        {
            "kicker": "CORRELATION READINESS",
            "title": f"{len(correlation_ready):,} ready / {correlation_total:,} rows",
            "body": (
                f"{len(correlation_unavailable):,} row(s) need enough overlapping local return history before correlation context is shown. "
                "Correlation is a concentration review signal, not a research conclusion."
            ),
            "badges": ["overlap required", "context only"],
            "command": "make research-health-check TOP_N=10",
        },
        {
            "kicker": "PROXY RISK NOTES",
            "title": f"{proxy_count:,} approximation row(s)",
            "body": (
                "When ATR inputs are unavailable, volatility-proxy language must stay labeled as an approximation in reports and dashboard output. "
                "Refresh reports only after the source rows are reviewed."
            ),
            "badges": ["approximation labeled", "no hidden inference"],
            "command": "make stock-report-md TICKER=NVDA",
        },
    ]
