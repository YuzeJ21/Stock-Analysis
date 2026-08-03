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


def _stock_report_md_command(ticker: object, fallback: str = "TICKER") -> str:
    ticker_text = _format_missing(ticker, fallback).upper()
    return f"make stock-report-md TICKER={ticker_text}"


def _compact_reason(value: object, max_sentences: int = 2, max_chars: int = 260) -> str:
    text = _format_missing(value)
    if text == "Not available":
        return text
    sentences = [part.strip() for part in text.replace("\n", " ").split(". ") if part.strip()]
    compact = ". ".join(sentences[:max_sentences])
    if compact and not compact.endswith((".", "?", "!")):
        compact += "."
    if len(compact) > max_chars:
        compact = compact[: max_chars - 1].rstrip() + "..."
    return compact


def peer_unlock_operator_cards(
    peer_unlock_worklist_frame: pd.DataFrame | None,
    ticker_readiness_frame: pd.DataFrame | None = None,
) -> list[dict[str, object]]:
    inspection_command, inspection_note = active_readiness_inspection_route()
    if peer_unlock_worklist_frame is None or peer_unlock_worklist_frame.empty:
        return [
            {
                "kicker": "PEER UNLOCK QUEUE",
                "title": "Peer unlock queue not ready yet",
                "body": f"Inspect the missing peer unlock queue before editing trusted peer rows. {inspection_note}",
                "badges": ["blocked"],
                "command": inspection_command,
            }
        ]

    frame = peer_unlock_worklist_frame.copy()
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
            for column in ["ticker", "asset_type", "in_active_universe", "dcf_ready", "peer_ready"]
            if column in ticker_readiness_frame.columns
        ]
        readiness = ticker_readiness_frame[readiness_columns].copy()
        readiness["ticker"] = readiness["ticker"].astype(str).str.upper().str.strip()
        frame = frame.merge(readiness, on="ticker", how="left", suffixes=("", "_readiness"))
    if "priority" in frame.columns:
        frame["priority"] = pd.to_numeric(frame["priority"], errors="coerce").fillna(999).astype(int)
    else:
        frame["priority"] = 999
    if "workflow_group" not in frame.columns:
        frame["workflow_group"] = "peer_workflow"
    if "workflow_scope" not in frame.columns:
        frame["workflow_scope"] = "unknown_scope"
    asset_type = frame.get("asset_type", pd.Series("", index=frame.index)).fillna("").astype(str).str.lower()
    monitor_proxy = asset_type.isin({"etf", "index_proxy", "fund"}) | asset_type.str.contains("etf|index|fund", na=False)
    if monitor_proxy.any():
        frame.loc[monitor_proxy, "workflow_group"] = "monitor_proxy_context"
        frame.loc[monitor_proxy, "workflow_scope"] = "active_universe"
        frame.loc[monitor_proxy, "next_action_summary"] = (
            "ETF/index/fund rows use stock-report monitoring context; do not treat fallback sector or peer context as trusted peer data."
        )
        frame.loc[monitor_proxy, "next_input_file"] = frame.loc[monitor_proxy, "ticker"].apply(
            lambda ticker: f"outputs/stock_reports/{str(ticker).strip().lower()}.md"
        )
        frame.loc[monitor_proxy, "validation_sequence"] = frame.loc[monitor_proxy, "ticker"].apply(
            lambda ticker: f"{_stock_report_md_command(ticker)} -> review source readiness and DCF exclusion"
        )
        frame.loc[monitor_proxy, "focus_command"] = frame.loc[monitor_proxy, "ticker"].apply(_stock_report_md_command)
        frame.loc[monitor_proxy, "copy_only_note"] = "Copy command only; review monitor context without peer valuation conclusions."
    workflow_counts = frame.get("workflow_group", pd.Series("peer_workflow", index=frame.index)).fillna("peer_workflow").astype(str).value_counts()
    scope_counts = frame.get("workflow_scope", pd.Series("unknown_scope", index=frame.index)).fillna("unknown_scope").astype(str).value_counts()
    priority_counts = frame["priority"].value_counts().sort_index()
    scope_text = frame.get("workflow_scope", pd.Series("", index=frame.index)).fillna("").astype(str).str.lower()
    workflow_text = frame.get("workflow_group", pd.Series("", index=frame.index)).fillna("").astype(str).str.lower()
    active_flag = bool_series(frame, "in_active_universe") if "in_active_universe" in frame.columns else pd.Series(False, index=frame.index)
    dcf_flag = bool_series(frame, "dcf_ready") if "dcf_ready" in frame.columns else pd.Series(False, index=frame.index)
    peer_ready_flag = bool_series(frame, "peer_ready") if "peer_ready" in frame.columns else pd.Series(False, index=frame.index)
    active_rank_flag = active_flag | scope_text.str.contains("active", na=False)
    dcf_rank_flag = dcf_flag | workflow_text.str.contains("dcf_ready|peer_valuation_unlock", regex=True, na=False)
    active_queue_count = int(active_rank_flag.sum())
    dcf_ready_peer_blocked_count = int((dcf_rank_flag & ~peer_ready_flag).sum())
    ordered = frame.loc[~monitor_proxy].copy()
    if ordered.empty:
        ordered = frame.copy()
    ordered_scope_text = ordered.get("workflow_scope", pd.Series("", index=ordered.index)).fillna("").astype(str).str.lower()
    ordered_workflow_text = ordered.get("workflow_group", pd.Series("", index=ordered.index)).fillna("").astype(str).str.lower()
    ordered_active_flag = bool_series(ordered, "in_active_universe") if "in_active_universe" in ordered.columns else pd.Series(False, index=ordered.index)
    ordered_dcf_flag = bool_series(ordered, "dcf_ready") if "dcf_ready" in ordered.columns else pd.Series(False, index=ordered.index)
    ordered = ordered.assign(
        _scope_rank=(~(ordered_active_flag | ordered_scope_text.str.contains("active", na=False))).astype(int),
        _dcf_rank=(~(ordered_dcf_flag | ordered_workflow_text.str.contains("dcf_ready|peer_valuation_unlock", regex=True, na=False))).astype(int),
    )
    ordered = ordered.sort_values(
        [
            "_scope_rank",
            "_dcf_rank",
            "priority",
            "workflow_scope",
            "workflow_group",
            "ticker",
        ],
        ascending=[True, True, True, True, True, True],
        kind="stable",
    )
    top_row = ordered.iloc[0]
    top_ticker = _format_missing(top_row.get("ticker"), "Ticker")
    top_summary = _compact_reason(top_row.get("next_action_summary") or top_row.get("next_peer_action"), max_sentences=1, max_chars=180)
    input_file = _format_missing(top_row.get("next_input_file"), "data/imports/peers.csv")
    validation = _format_missing(
        top_row.get("validation_sequence"),
        "make templates -> make imports-validate IMPORT_TICKERS=<ticker> -> "
        "make imports-preview IMPORT_TICKERS=<ticker> -> make imports-apply IMPORT_TICKERS=<ticker>",
    )
    peer_schema = (
        "ticker, peer_ticker, peer_group, sector, industry, peer_role, relationship_rationale, "
        "comparability_basis, valuation_anchor_eligible, source, as_of_date"
    )
    priority_text = ", ".join(f"P{int(key)}: {int(value)}" for key, value in priority_counts.head(4).items())
    workflow_text = ", ".join(f"{str(key).replace('_', ' ')}: {int(value)}" for key, value in workflow_counts.head(3).items())
    scope_text = ", ".join(f"{str(key).replace('_', ' ')}: {int(value)}" for key, value in scope_counts.head(3).items())
    cards = [
        {
            "kicker": "PEER UNLOCK QUEUE",
            "title": priority_text or f"{len(frame)} queued",
            "body": (
                f"{len(frame)} peer unlock row(s). Active-universe queue: {active_queue_count}. "
                f"DCF-ready but peer-blocked: {dcf_ready_peer_blocked_count}. Scope mix: {scope_text or 'not available'}."
            ),
            "badges": ["priority grouped", "row-limited"],
            "command": "make peer-mapping-queue TOP_N=25",
        },
        {
            "kicker": "NEXT PEER ROW",
            "title": top_ticker,
            "body": f"{top_summary} Input file: {input_file}. Schema fields: {peer_schema}. Validate with: {validation}.",
            "badges": ["source-backed", "preview before apply"],
            "command": str(top_row.get("focus_command") or f"make focus-peers TICKER={top_ticker}"),
        },
        {
            "kicker": "WORKFLOW GROUPS",
            "title": "What kind of peer data?",
            "body": (
                f"{workflow_text or 'No workflow grouping is available yet.'} "
                "Peer trend can use mapped peer price history; peer valuation waits for source-backed peer mappings and peer valuation inputs."
            ),
            "badges": ["mapping vs metrics", "no fallback peers"],
            "command": "make templates",
        },
    ]
    if monitor_proxy.any():
        monitor_row = frame.loc[monitor_proxy].sort_values(["priority", "ticker"], kind="stable").iloc[0]
        monitor_ticker = _format_missing(monitor_row.get("ticker"), "Ticker")
        cards.append(
            {
                "kicker": "MONITOR PROXIES",
                "title": f"{int(monitor_proxy.sum())} ETF/index/fund row(s)",
                "body": "These rows stay in stock-report monitoring context; peer valuation remains excluded unless trusted company-peer inputs exist.",
                "badges": ["monitor context", "dcf excluded"],
                "command": f"make stock-report-md TICKER={monitor_ticker}",
            }
        )
    return cards
