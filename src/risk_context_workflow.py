"""Risk-context workflow helpers for Data Health views."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.paths import resolve_outputs_dir, resolve_project_root


def split_risk_context_by_price_ready(frame: pd.DataFrame | None, unavailable_statuses: set[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    if frame is None or frame.empty:
        return pd.DataFrame(), pd.DataFrame()
    status_column = next((column for column in ["LiquidityStatus", "CorrelationStatus"] if column in frame.columns), "")
    if not status_column:
        return frame.copy(), pd.DataFrame(columns=frame.columns)
    status = frame[status_column].fillna("").astype(str).str.strip().str.lower()
    unavailable = status.isin({value.lower() for value in unavailable_statuses})
    return frame.loc[~unavailable].copy(), frame.loc[unavailable].copy()


def _ticker_examples(frame: pd.DataFrame, *, limit: int = 5) -> str:
    if frame.empty or "Ticker" not in frame.columns or limit <= 0:
        return "-"
    tickers = frame["Ticker"].dropna().astype(str).str.upper().str.strip()
    examples = [ticker for ticker in tickers if ticker]
    return ", ".join(examples[:limit]) if examples else "-"


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
    liquidity_examples = _ticker_examples(liquidity_unavailable)
    correlation_examples = _ticker_examples(correlation_unavailable)
    liquidity_example_sentence = f" Examples: {liquidity_examples}." if liquidity_examples != "-" else ""
    correlation_example_sentence = f" Examples: {correlation_examples}." if correlation_examples != "-" else ""

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
                f"{liquidity_example_sentence}"
            ),
            "badges": ["price history", "volume-gated"],
            "command": "make price-history-proof-queue TOP_N=25",
        },
        {
            "kicker": "CORRELATION READINESS",
            "title": f"{len(correlation_ready):,} ready / {correlation_total:,} rows",
            "body": (
                f"{len(correlation_unavailable):,} row(s) need enough overlapping local return history before correlation context is shown. "
                "Correlation is a concentration review signal, not a research conclusion."
                f"{correlation_example_sentence}"
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


def risk_context_summary_lines(
    liquidity_frame: pd.DataFrame | None,
    correlation_frame: pd.DataFrame | None,
) -> list[str]:
    """Return terminal-safe risk-context summary lines from current local outputs."""

    cards = data_health_risk_context_cards(liquidity_frame, correlation_frame)
    lines = [
        "Risk Context Summary",
        "Read-only: this command does not refresh, import, apply, stage, or infer data.",
        (
            "Choose scope first: run make universe-scope TOP_N=10 before treating liquidity, correlation, "
            "or proxy-risk rows as usable context; risk context does not unlock missing fundamentals, peers, "
            "earnings, or estimates. If short price-history blockers remain, use the price-history proof queue "
            "before any capped provider refresh."
        ),
    ]
    for card in cards:
        lines.append(
            f"- {card['kicker'].title()}: {card['title']} | {card['body']} | next: {card['command']}"
        )
    return lines


def _read_optional_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print read-only liquidity/correlation risk-context readiness.")
    parser.add_argument("--root", default=".", help="Project root")
    args = parser.parse_args(argv)

    root = resolve_project_root(args.root)
    outputs = resolve_outputs_dir(None, root)
    liquidity = _read_optional_csv(outputs / "liquidity_risk.csv")
    correlation = _read_optional_csv(outputs / "correlation_risk.csv")
    for line in risk_context_summary_lines(liquidity, correlation):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
