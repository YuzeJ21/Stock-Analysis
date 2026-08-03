from __future__ import annotations

import pandas as pd
from src.profile_context import active_readiness_inspection_route


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


def _bool_series(frame: pd.DataFrame | None, column: str) -> pd.Series:
    if frame is None or frame.empty or column not in frame.columns:
        return pd.Series(dtype=bool)
    values = frame[column]
    if pd.api.types.is_bool_dtype(values):
        return values.fillna(False).astype(bool)
    return values.fillna("").astype(str).str.strip().str.lower().isin({"true", "1", "yes", "y"})


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


def peer_readiness_product_cards(
    peer_readiness_frame: pd.DataFrame | None,
    peer_mapping_queue_frame: pd.DataFrame | None = None,
    peer_unlock_worklist_frame: pd.DataFrame | None = None,
) -> list[dict[str, object]]:
    inspection_command, inspection_note = active_readiness_inspection_route()
    if peer_readiness_frame is None or peer_readiness_frame.empty:
        return [
            {
                "kicker": "PEER READINESS",
                "title": "Peer readiness not ready yet",
                "body": f"Inspect peer readiness before reviewing peer trend, peer valuation, or source-backed peer blockers. {inspection_note}",
                "badges": ["blocked"],
                "command": inspection_command,
            }
        ]

    frame = peer_readiness_frame.copy()
    for column in [
        "peer_count",
        "ready_peer_count",
        "peer_price_ready_count",
        "peer_momentum_ready_count",
        "peer_fundamentals_ready_count",
        "peer_valuation_ready_count",
    ]:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0).astype(int)
    peer_ready = _bool_series(frame, "peer_ready")
    trend_ready = _bool_series(frame, "peer_trend_comparison_ready")
    valuation_ready = _bool_series(frame, "peer_valuation_comparison_ready")
    dcf_ready = _bool_series(frame, "peer_dcf_comparison_ready")
    blocker_counts = {}
    if "peer_blocker_type" in frame.columns:
        blocker_counts = {
            str(key): int(value)
            for key, value in frame.loc[~peer_ready, "peer_blocker_type"].fillna("peer_blocked").astype(str).value_counts().items()
            if str(key).strip()
        }
    top_blocker = next(iter(blocker_counts), "peer_blocked")
    queue_rows = 0 if peer_mapping_queue_frame is None else int(len(peer_mapping_queue_frame))
    next_ticker = "Not available"
    next_reason = "Build the prioritized peer worklist before choosing the next peer target."
    if peer_unlock_worklist_frame is not None and not peer_unlock_worklist_frame.empty and "ticker" in peer_unlock_worklist_frame.columns:
        worklist = peer_unlock_worklist_frame.copy()
        worklist["ticker"] = worklist["ticker"].astype(str).str.upper().str.strip()
        if "priority" in worklist.columns:
            worklist["priority"] = pd.to_numeric(worklist["priority"], errors="coerce").fillna(999).astype(int)
        scope_text = worklist.get("workflow_scope", pd.Series("", index=worklist.index)).fillna("").astype(str).str.lower()
        workflow_text = worklist.get("workflow_group", pd.Series("", index=worklist.index)).fillna("").astype(str).str.lower()
        active_flag = _bool_series(worklist, "in_active_universe") if "in_active_universe" in worklist.columns else pd.Series(False, index=worklist.index)
        dcf_flag = _bool_series(worklist, "dcf_ready") if "dcf_ready" in worklist.columns else pd.Series(False, index=worklist.index)
        worklist["_scope_rank"] = (~(active_flag | scope_text.str.contains("active", na=False))).astype(int)
        worklist["_dcf_rank"] = (~(dcf_flag | workflow_text.str.contains("dcf_ready|peer_valuation_unlock", regex=True, na=False))).astype(int)
        sort_columns = [column for column in ["_scope_rank", "_dcf_rank", "priority", "ticker"] if column in worklist.columns]
        worklist = worklist.sort_values(sort_columns, kind="stable") if sort_columns else worklist
        next_row = worklist.iloc[0]
        next_ticker = _format_missing(next_row.get("ticker"), "Ticker")
        next_reason = _compact_reason(
            next_row.get("next_action_summary") or next_row.get("next_peer_action") or next_row.get("missing_peer_reason"),
            max_sentences=1,
            max_chars=180,
        )
    elif "peer_ready" in frame.columns:
        candidates = frame.loc[~peer_ready].copy()
        if "peer_blocker_type" in candidates.columns:
            candidates = candidates.sort_values(["peer_blocker_type", "ticker"], kind="stable")
        if not candidates.empty:
            next_ticker = _format_missing(candidates.iloc[0].get("ticker"), "Ticker")
            next_reason = _compact_reason(candidates.iloc[0].get("next_peer_action") or candidates.iloc[0].get("missing_peer_reason"), max_sentences=1, max_chars=140)
    return [
        {
            "kicker": "PEER READY",
            "title": f"{int(peer_ready.sum())}/{len(frame)} ready",
            "body": (
                f"Trend-ready peers: {int(trend_ready.sum())}. Valuation comparison ready: {int(valuation_ready.sum())}. "
                f"DCF peer comparison ready: {int(dcf_ready.sum())}. {inspection_note}"
            ),
            "badges": ["peer workflow", "data-honest"],
            "command": inspection_command,
        },
        {
            "kicker": "TOP PEER BLOCKER",
            "title": top_blocker.replace("_", " "),
            "body": ", ".join(f"{key.replace('_', ' ')}: {value}" for key, value in list(blocker_counts.items())[:3]) or "No peer blockers reported.",
            "badges": ["specific blockers"],
            "command": "make peer-mapping-queue TOP_N=25",
        },
        {
            "kicker": "NEXT PEER TARGET",
            "title": next_ticker,
            "body": next_reason,
            "badges": ["manual research", "source-backed peers"],
            "command": f"make focus-peers TICKER={next_ticker}" if next_ticker != "Not available" else "make peer-mapping-queue TOP_N=25",
        },
        {
            "kicker": "PEER QUEUE",
            "title": f"{queue_rows} queued",
            "body": "Use capped peer worklists and import-file validation before relying on peer-relative context.",
            "badges": ["TOP_N safe", "preview first"],
            "command": "make peer-mapping-queue TOP_N=25",
        },
    ]
