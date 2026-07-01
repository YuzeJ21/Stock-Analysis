"""Universe scope helpers for readiness-first dashboard views."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.loader import normalize_columns
from src.paths import resolve_data_dir, resolve_project_root


UNIVERSE_SCOPE_REVIEW_COLUMNS = [
    "scope",
    "matching_rows",
    "what_it_answers",
    "copy_only_command",
    "scope_boundary",
    "stop_rule",
]


def _safe_int(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _bool_series(frame: pd.DataFrame, column: str) -> pd.Series:
    if frame.empty or column not in frame.columns:
        return pd.Series(False, index=frame.index)
    return frame[column].astype(str).str.strip().str.lower().isin({"true", "1", "yes"})


def _text_series(frame: pd.DataFrame, column: str) -> pd.Series:
    if frame.empty or column not in frame.columns:
        return pd.Series("", index=frame.index)
    return frame[column].fillna("").astype(str).str.strip()


def _split_tickers(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip().upper() for part in value.split(",") if part.strip()]


def _read_readiness_frame(root: Path) -> pd.DataFrame:
    data_dir = resolve_data_dir(None, root)
    path = data_dir / "reports" / "ticker_readiness_report.csv"
    if not path.exists():
        return pd.DataFrame()
    frame = pd.read_csv(path)
    frame.columns = normalize_columns(list(frame.columns))
    if "ticker" in frame.columns:
        frame["ticker"] = frame["ticker"].astype("string").str.upper().str.strip()
    return frame


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


def universe_scope_risk_handoff_cards(
    summary: dict[str, object],
    ticker_readiness_frame: pd.DataFrame | None,
) -> list[dict[str, object]]:
    """Return cards that keep risk context behind an explicit scope choice."""

    counts = universe_scope_counts(summary, ticker_readiness_frame)
    master = counts["master"]
    active = counts["active"]
    price_ready = counts["price_ready"]
    dcf_ready = counts["dcf_ready"]
    peer_ready = counts["peer_ready"]
    return [
        {
            "kicker": "SCOPE BEFORE RISK",
            "title": "Choose the review set first",
            "body": (
                f"Start with {active} active-review rows before the {master}-row master universe. "
                "Then narrow by ticker, sector, theme, or ready-only state before opening liquidity or correlation context."
            ),
            "badges": ["scope first", "row-limited"],
            "command": "make universe-scope TOP_N=10",
        },
        {
            "kicker": "RISK CONTEXT BOUNDARY",
            "title": f"{price_ready} price-ready rows feed risk context",
            "body": (
                "Review liquidity and correlation after scope selection. Risk context is not a research conclusion, "
                "and it does not unlock DCF, peers, earnings, analyst estimates, valuation inputs, or recommendations."
            ),
            "badges": ["context only", "price-history gated"],
            "command": "make risk-context",
        },
        {
            "kicker": "NEXT SAFE REVIEW",
            "title": f"{dcf_ready} DCF-ready; {peer_ready} peer-ready",
            "body": (
                "Blocked rows route back to price history or source proof, not broad conclusions. "
                "Use the coverage frontier to decide whether the next executable lane is data proof, provider setup, or workflow evidence."
            ),
            "badges": ["blocked stays visible", "proof-gated"],
            "command": "make coverage-frontier TOP_N=10",
        },
    ]


def universe_scope_review_plan(
    summary: dict[str, object],
    ticker_readiness_frame: pd.DataFrame | None,
    *,
    tickers: str | None = None,
    sector: str | None = None,
    theme: str | None = None,
    top_n: int = 10,
) -> pd.DataFrame:
    """Return copy-only scope rows for lazy universe review."""

    frame = ticker_readiness_frame if ticker_readiness_frame is not None else pd.DataFrame()
    counts = universe_scope_counts(summary, frame)
    ticker_list = _split_tickers(tickers)
    ticker_text = ",".join(ticker_list) if ticker_list else "<ticker-list>"
    active_rows = int(_bool_series(frame, "in_active_universe").sum()) if not frame.empty else counts["active"]

    ticker_rows = 0
    if ticker_list and not frame.empty and "ticker" in frame.columns:
        ticker_rows = int(frame["ticker"].isin(ticker_list).sum())
    elif ticker_list:
        ticker_rows = len(ticker_list)

    sector_text = str(sector or "").strip()
    theme_text = str(theme or "").strip()
    sector_theme_rows = 0
    if not frame.empty and (sector_text or theme_text):
        mask = pd.Series(False, index=frame.index)
        if sector_text:
            mask = mask | _text_series(frame, "sector").str.contains(sector_text, case=False, regex=False, na=False)
        if theme_text:
            mask = mask | _text_series(frame, "theme").str.contains(theme_text, case=False, regex=False, na=False)
        sector_theme_rows = int(mask.sum())

    ready_mask = pd.Series(False, index=frame.index)
    for column in ("price_ready", "dcf_ready", "peer_ready"):
        ready_mask = ready_mask | _bool_series(frame, column)
    ready_rows = int(ready_mask.sum()) if not frame.empty else max(counts["price_ready"], counts["dcf_ready"], counts["peer_ready"])

    missing_mask = pd.Series(False, index=frame.index)
    for column in ("blocked_features", "missing_data", "missing_data_summary"):
        missing_mask = missing_mask | _text_series(frame, column).ne("")
    missing_rows = int(missing_mask.sum()) if not frame.empty else 0

    boundary = "copy-only; does not refresh, import, apply, or infer missing values"
    stop_rule = "Stop at the selected scope; widen only after readiness and proof gates are reviewed."
    rows = [
        {
            "scope": "active_universe",
            "matching_rows": active_rows,
            "what_it_answers": "Which focused demo/research rows should be reviewed before broad universe rows?",
            "copy_only_command": f"make readiness-queue TOP_N={top_n}",
            "scope_boundary": boundary,
            "stop_rule": "Use active rows first; do not read master-universe coverage as analysis readiness.",
        },
        {
            "scope": "ticker_list",
            "matching_rows": ticker_rows,
            "what_it_answers": "Can named tickers be inspected one at a time without forcing full-market analysis?",
            "copy_only_command": f"make status-check TICKERS={ticker_text} TOP_N={top_n}",
            "scope_boundary": boundary,
            "stop_rule": "Use single-stock reports or focused status before opening broad tables.",
        },
        {
            "scope": "sector_theme",
            "matching_rows": sector_theme_rows,
            "what_it_answers": "Which sector/theme slice should be scanned before widening the universe?",
            "copy_only_command": f"make status-check TOP_N={top_n}",
            "scope_boundary": f"{boundary}; use dashboard sector/theme filters for row selection",
            "stop_rule": "Keep sector/theme rows as scan context until ticker-level proof exists.",
        },
        {
            "scope": "ready_only",
            "matching_rows": ready_rows,
            "what_it_answers": "Which rows have at least one ready analysis layer to review now?",
            "copy_only_command": f"make trusted-data-pilot-candidates TOP_N={top_n}",
            "scope_boundary": boundary,
            "stop_rule": "Ready price or DCF subsets do not unlock blocked peer, earnings, or estimate lanes.",
        },
        {
            "scope": "missing_data",
            "matching_rows": missing_rows,
            "what_it_answers": "Which rows should route back to source proof instead of analysis?",
            "copy_only_command": f"make coverage-frontier TOP_N={top_n}",
            "scope_boundary": boundary,
            "stop_rule": stop_rule,
        },
    ]
    return pd.DataFrame(rows, columns=UNIVERSE_SCOPE_REVIEW_COLUMNS)


def _print_plan(plan: pd.DataFrame) -> None:
    print("Universe Scope Runbook")
    print("Read-only: this command does not refresh, import, apply, stage, or infer data.")
    if plan.empty:
        print("No scope rows available. Run make readiness before relying on counts.")
        return
    active_rows = plan[plan["scope"].eq("active_universe")]
    recommended = active_rows.iloc[0] if not active_rows.empty and _safe_int(active_rows.iloc[0]["matching_rows"]) else plan.iloc[0]
    print(
        f"Recommended first scope: {recommended['scope']} | {recommended['matching_rows']} row(s) | "
        f"{recommended['copy_only_command']}"
    )
    print("Boundary: do not treat master-universe coverage as analysis readiness; widen only after proof gates.")
    for row in plan.to_dict("records"):
        print(
            f"- {row['scope']}: {row['matching_rows']} row(s) | {row['what_it_answers']} | "
            f"{row['copy_only_command']} | boundary: {row['scope_boundary']} | stop: {row['stop_rule']}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print the read-only universe scope runbook.")
    parser.add_argument("--root", default=".", help="Project root")
    parser.add_argument("--tickers", default="", help="Comma-separated ticker list for ticker-list scope")
    parser.add_argument("--sector", default="", help="Sector text to count for sector/theme scope")
    parser.add_argument("--theme", default="", help="Theme text to count for sector/theme scope")
    parser.add_argument("--top-n", type=int, default=10, help="Row limit used in copy-only commands")
    args = parser.parse_args(argv)

    root = resolve_project_root(args.root)
    frame = _read_readiness_frame(root)
    plan = universe_scope_review_plan(
        {},
        frame,
        tickers=args.tickers,
        sector=args.sector,
        theme=args.theme,
        top_n=args.top_n,
    )
    _print_plan(plan)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
