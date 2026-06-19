from __future__ import annotations

import pandas as pd

from src.dashboard_navigation import dashboard_page_slug
from src.data_health_proof_ctas import card_sentence, compact_card_fragment, format_missing


def metric_readiness_blocker_family(blocker: object) -> str:
    text = str(blocker or "").strip().lower()
    if not text or text == "none":
        return "none"
    if "benchmark" in text or "aligned" in text or "price" in text or "drawdown" in text or "volatility" in text or "sharpe" in text or "sortino" in text or "beta" in text:
        return "benchmark / risk"
    if "fundamental" in text or "revenue" in text or "free cash flow" in text or "fcf" in text:
        return "fundamentals trend"
    if "market cap" in text or "shares outstanding" in text or "valuation" in text or "multiple" in text:
        return "valuation multiples"
    if "peer" in text:
        return "peer dispersion"
    return "other"


def metric_details_requested(query_value: object, session_loaded: object = False) -> bool:
    if bool(session_loaded):
        return True
    if isinstance(query_value, (list, tuple)):
        query_value = query_value[0] if query_value else ""
    raw = str(query_value or "").strip().lower()
    return raw in {"1", "true", "yes", "load", "loaded", "details"}


def progressive_details_requested(query_value: object, session_loaded: object = False) -> bool:
    if bool(session_loaded):
        return True
    if isinstance(query_value, (list, tuple)):
        query_value = query_value[0] if query_value else ""
    raw = str(query_value or "").strip().lower()
    return raw in {"1", "true", "yes", "load", "loaded", "details", "open"}


def detail_selector_requested(query_value: object, session_loaded: object = False, selector_value: object = None) -> bool:
    if progressive_details_requested(query_value, session_loaded):
        return True
    return str(selector_value or "").strip().lower() == "review details"


def drawer_from_query(query_value: object, selected_lane_key: str = "") -> str:
    if isinstance(query_value, (list, tuple)):
        query_value = query_value[0] if query_value else ""
    token = dashboard_page_slug(str(query_value or "").strip())
    aliases = {
        "batch": "batch",
        "batch-execution": "batch",
        "packet": "batch",
        "reviewed-batch": "batch",
        "queue": "queue",
        "readiness-queue": "queue",
        "lane": "queue",
        "source": "queue",
        "source-proof": "queue",
        "metric": "metrics",
        "metrics": "metrics",
        "metric-details": "metrics",
        "proof": "proof",
        "proof-history": "proof",
        "proof-record": "proof",
        "ledger": "proof",
    }
    return aliases.get(token, "")


def drawer_detail_flags(drawer: str, selected_lane_key: str = "") -> dict[str, bool]:
    normalized = drawer_from_query(drawer, selected_lane_key)
    return {
        "queue": False,
        "batch": normalized == "batch" and selected_lane_key not in {"metrics", "proof"},
        "metrics": normalized == "metrics",
        "proof": normalized == "proof",
    }


def deferred_detail_cards(
    *,
    title: str,
    body: str,
    command: str,
    badges: list[str] | None = None,
) -> list[dict[str, object]]:
    return [
        {
            "kicker": "DETAIL MODE",
            "title": title,
            "body": (
                f"{body} This keeps the first viewport focused on readiness status and next action; "
                "switch to Review details when you need row-level proof."
            ),
            "badges": badges or ["progressive loading", "collapsed proof"],
            "command": command,
        }
    ]


def metric_detail_load_status(
    selected_lane_key: str,
    freshness_status: object | None,
    requested: bool,
) -> dict[str, str]:
    if selected_lane_key != "metrics":
        return {
            "status": "not_selected",
            "title": "Metrics lane not selected",
            "body": "Metric-readiness details stay unloaded until the operator opens the Metrics lane.",
            "next_action": "Open the Metrics lane.",
        }
    if freshness_status is None:
        freshness_status = type("FreshnessFallback", (), {
            "status": "unknown",
            "message": "Readiness freshness has not been checked.",
            "refresh_command": "make readiness",
        })()
    if getattr(freshness_status, "status", "") in {"missing", "stale"}:
        return {
            "status": "blocked_by_snapshot_gate",
            "title": "Refresh readiness before metric details",
            "body": getattr(freshness_status, "message", "") or "Readiness artifacts are not current enough for row-level metric counts.",
            "next_action": getattr(freshness_status, "refresh_command", "") or "make readiness",
        }
    if not requested:
        return {
            "status": "needs_request",
            "title": "Metric details are not loaded yet",
            "body": (
                "The first metrics view is intentionally lightweight. Load SPY/QQQ row-level details only when "
                "you need blocker-family proof."
            ),
            "next_action": "Switch Metric detail level to Review details.",
        }
    return {
        "status": "ready_to_load",
        "title": "Metric details loaded",
        "body": "SPY/QQQ metric-readiness rows are loaded from cached local readiness inputs for this session.",
        "next_action": "Open the Metrics evidence drawer.",
    }


def metric_detail_load_cards(load_status: dict[str, str]) -> list[dict[str, object]]:
    status = load_status.get("status", "needs_request")
    if status == "blocked_by_snapshot_gate":
        return [
            {
                "kicker": "METRIC DETAIL GATE",
                "title": load_status.get("title", "Refresh readiness first"),
                "body": (
                    f"{load_status.get('body', 'Readiness artifacts need refresh.')} "
                    "Metric details stay blocked so stale row counts do not look current."
                ),
                "badges": ["snapshot gate", "no stale counts"],
                "command": load_status.get("next_action", "make readiness"),
            }
        ]
    if status == "ready_to_load":
        return [
            {
                "kicker": "METRIC DETAIL STATUS",
                "title": "SPY / QQQ queue loaded",
                "body": (
                    "Row-level blocker families are available in the evidence drawer. Keep Sharpe, Sortino, beta, "
                    "drawdown, valuation, trend, and peer dispersion as review metrics only."
                ),
                "badges": ["cached", "review-only"],
                "command": "make metric-readiness-board TOP_N=10",
            }
        ]
    return [
        {
            "kicker": "METRIC DETAIL STATUS",
            "title": load_status.get("title", "Metric details are not loaded yet"),
            "body": (
                f"{load_status.get('body', 'Load details only when needed.')} "
                "This keeps the Data Health first viewport fast and avoids opening raw metric rows by default."
            ),
            "badges": ["progressive loading", "collapsed detail"],
            "command": "make metric-readiness-board TOP_N=10",
        }
    ]


def proof_detail_load_status(
    selected_lane_key: str,
    freshness_status: object | None,
    *,
    requested: bool,
    loaded: bool,
    decision_queue_status: object | None = None,
) -> dict[str, str]:
    if selected_lane_key != "proof":
        return {
            "status": "not_selected",
            "title": "Proof lane not selected",
            "body": "Proof ledgers, packet scaffolds, and snapshot comparison stay unloaded until the operator opens Proof History.",
            "next_action": "Open the Proof History lane.",
        }
    if freshness_status is None:
        freshness_status = type("FreshnessFallback", (), {
            "status": "unknown",
            "message": "Readiness freshness has not been checked.",
            "refresh_command": "make readiness",
        })()
    if getattr(freshness_status, "status", "") in {"missing", "stale"}:
        return {
            "status": "blocked_by_snapshot_gate",
            "title": "Refresh readiness before proof details",
            "body": getattr(freshness_status, "message", "") or "Readiness artifacts are not current enough for proof-ledger review.",
            "next_action": getattr(freshness_status, "refresh_command", "") or "make readiness",
        }
    if not requested:
        return {
            "status": "deferred",
            "title": "Proof details are deferred",
            "body": (
                "The proof lane shell is loaded. Reviewed proof rows, batch packet scaffolds, and snapshot comparison "
                "stay collapsed until Review details is opened."
            ),
            "next_action": "Switch Proof detail level to Review details.",
        }
    decision_status = str(getattr(decision_queue_status, "status", "") or "")
    if not loaded:
        return {
            "status": "loading",
            "title": "Proof details are loading",
            "body": (
                "The proof lane is building reviewed proof ledgers, packet scaffolds, and snapshot comparison. "
                "Keep proof rows collapsed until the loaded state appears."
            ),
            "next_action": "Wait for proof detail cards, then open the reviewed proof drawers.",
        }
    if decision_status in {"missing", "stale"}:
        return {
            "status": "loaded_with_warning",
            "title": "Proof details loaded with a source warning",
            "body": (
                "Reviewed batch proof and snapshot comparison are loaded, but the decision proof queue needs refresh "
                "before decision-proof rows can be used."
            ),
            "next_action": getattr(decision_queue_status, "refresh_command", "") or "make decision-proof-queue",
        }
    return {
        "status": "loaded",
        "title": "Proof details loaded",
        "body": "Reviewed proof ledgers, batch proof scaffolds, and snapshot comparison are available in collapsed proof drawers.",
        "next_action": "Open reviewed batch proof drawer.",
    }


def proof_detail_load_cards(load_status: dict[str, str]) -> list[dict[str, object]]:
    status = load_status.get("status", "deferred")
    if status == "blocked_by_snapshot_gate":
        return [
            {
                "kicker": "PROOF DETAIL GATE",
                "title": load_status.get("title", "Refresh readiness first"),
                "body": (
                    f"{load_status.get('body', 'Readiness artifacts need refresh.')} "
                    "Proof details stay blocked so stale snapshot counts do not look reviewed."
                ),
                "badges": ["snapshot gate", "no stale proof"],
                "command": load_status.get("next_action", "make readiness"),
            }
        ]
    if status == "loading":
        return [
            {
                "kicker": "PROOF DETAIL STATUS",
                "title": load_status.get("title", "Proof details are loading"),
                "body": (
                    f"{load_status.get('body', 'Proof detail rows are loading.')} "
                    "This is still read-only and does not record a proof row."
                ),
                "badges": ["loading", "collapsed proof"],
                "command": "Review details is selected; wait for loaded proof state.",
            }
        ]
    if status in {"loaded", "loaded_with_warning"}:
        warning_suffix = (
            " Resolve the source warning before using decision-proof rows."
            if status == "loaded_with_warning"
            else ""
        )
        return [
            {
                "kicker": "PROOF DETAIL STATUS",
                "title": load_status.get("title", "Proof details loaded"),
                "body": (
                    f"{load_status.get('body', 'Proof detail rows are loaded.')}{warning_suffix} "
                    "Record supported, still_blocked, skipped, or excluded only after reviewed evidence is complete."
                ),
                "badges": ["loaded", "proof ledger"],
                "command": load_status.get("next_action", "Open reviewed batch proof drawer."),
            }
        ]
    return [
        {
            "kicker": "PROOF DETAIL STATUS",
            "title": load_status.get("title", "Proof details are deferred"),
            "body": (
                f"{load_status.get('body', 'Proof details load only when needed.')} "
                "This keeps the proof lane fast and prevents raw ledgers from looking like first-read status."
            ),
            "badges": ["progressive loading", "collapsed proof"],
            "command": load_status.get("next_action", "Switch Proof detail level to Review details."),
        }
    ]


def metric_readiness_queue_cards(frame: pd.DataFrame | None) -> list[dict[str, object]]:
    if frame is None or frame.empty:
        return [
            {
                "kicker": "METRIC QUEUE",
                "title": "No queue rows",
                "body": "Run the capped metric-readiness queue after local provider data exists. This view is a readiness summary, not a security ranking.",
                "badges": ["SPY", "QQQ", "readiness-only"],
                "command": "make metric-readiness TOP_N=10 BENCHMARK=SPY",
            }
        ]

    states = frame.get("Overall State", pd.Series(index=frame.index, dtype=object)).astype(str).str.lower()
    partial_or_blocked = int(states.isin({"partial", "blocked"}).sum())
    ready = int(states.eq("ready").sum())
    excluded = int(states.eq("excluded").sum())
    benchmarks = ", ".join(dict.fromkeys(frame.get("Benchmark", pd.Series(index=frame.index, dtype=object)).dropna().astype(str).tolist())) or "SPY, QQQ"
    freshness_values = frame.get("Freshness", pd.Series(index=frame.index, dtype=object)).dropna().astype(str).str.lower()
    freshness = "unknown" if freshness_values.empty else ", ".join(dict.fromkeys(freshness_values.tolist()))

    family_counts = (
        frame.get("Blocker Family", pd.Series(index=frame.index, dtype=object))
        .fillna("none")
        .astype(str)
        .str.lower()
        .value_counts()
    )
    top_family = "none" if family_counts.empty else str(family_counts.index[0])
    top_family_count = 0 if family_counts.empty else int(family_counts.iloc[0])
    top_blockers = frame.get("Top Blocker", pd.Series(index=frame.index, dtype=object)).fillna("").astype(str)
    blocker_rows = frame.loc[top_blockers.str.lower().ne("none")]
    first_blocker = "none"
    first_next_check = "make metric-readiness TOP_N=10 BENCHMARK=SPY"
    if not blocker_rows.empty:
        first = blocker_rows.iloc[0]
        first_blocker = compact_card_fragment(first.get("Top Blocker"), max_chars=150)
        first_next_check = format_missing(first.get("Next Check"), first_next_check)

    return [
        {
            "kicker": "SPY / QQQ METRIC QUEUE",
            "title": f"{len(frame):,} rows across {benchmarks}",
            "body": (
                f"{ready:,} ready row(s), {partial_or_blocked:,} partial or blocked row(s), and {excluded:,} excluded row(s). "
                "This summarizes review-metric coverage across benchmarks without opening single-stock reports."
            ),
            "badges": ["readiness queue", "not ranking", freshness],
            "command": "make metric-readiness TOP_N=10 BENCHMARK=SPY",
        },
        {
            "kicker": "TOP BLOCKER FAMILY",
            "title": top_family.title(),
            "body": (
                f"{top_family_count:,} queue row(s) currently point to this blocker family. "
                "Use the family as an operator triage cue; do not read it as relative attractiveness."
            ),
            "badges": ["family triage", "coverage work"],
            "command": "make metric-readiness TOP_N=10 BENCHMARK=QQQ",
        },
        {
            "kicker": "FIRST NEXT CHECK",
            "title": "Exact blocker shown",
            "body": f"{card_sentence('Blocker', first_blocker)} Next check: {first_next_check}. Partial metrics withhold values until their row gate is ready.",
            "badges": ["blocked visible", "no inferred values"],
            "command": first_next_check,
        },
    ]


def metric_readiness_family_summary_frame(frame: pd.DataFrame | None) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame(
            columns=[
                "Blocker Family",
                "Queue Rows",
                "Benchmarks",
                "Ready Rows",
                "Partial Rows",
                "Blocked Rows",
                "Excluded Rows",
                "First Next Check",
                "Guardrail",
            ]
        )
    work = frame.copy()
    work["Blocker Family"] = (
        work.get("Blocker Family", pd.Series(index=work.index, dtype=object))
        .fillna("none")
        .astype(str)
        .str.strip()
        .replace("", "none")
    )
    state_series = work.get("Overall State", pd.Series(index=work.index, dtype=object)).fillna("").astype(str).str.lower()
    rows: list[dict[str, object]] = []
    for family, group in work.groupby("Blocker Family", dropna=False):
        group_states = state_series.loc[group.index]
        blockers = group.get("Top Blocker", pd.Series(index=group.index, dtype=object)).fillna("").astype(str)
        actionable_group = group.loc[blockers.str.lower().ne("none")]
        first_next_check = "make metric-readiness-board TOP_N=10"
        if not actionable_group.empty:
            first_next_check = format_missing(actionable_group.iloc[0].get("Next Check"), first_next_check)
        rows.append(
            {
                "Blocker Family": str(family),
                "Queue Rows": int(len(group)),
                "Benchmarks": ", ".join(
                    dict.fromkeys(
                        group.get("Benchmark", pd.Series(index=group.index, dtype=object))
                        .dropna()
                        .astype(str)
                        .tolist()
                    )
                ),
                "Ready Rows": int(group_states.eq("ready").sum()),
                "Partial Rows": int(group_states.eq("partial").sum()),
                "Blocked Rows": int(group_states.eq("blocked").sum()),
                "Excluded Rows": int(group_states.eq("excluded").sum()),
                "First Next Check": first_next_check,
                "Guardrail": "readiness triage only; not a ranking or recommendation",
            }
        )
    summary = pd.DataFrame(rows)
    if summary.empty:
        return summary
    family_order = {
        "benchmark / risk": 0,
        "fundamentals trend": 1,
        "valuation multiples": 2,
        "peer dispersion": 3,
        "other": 4,
        "none": 5,
    }
    summary["_sort_family"] = summary["Blocker Family"].astype(str).map(lambda value: family_order.get(value.lower(), 4))
    summary = summary.sort_values(["Queue Rows", "_sort_family", "Blocker Family"], ascending=[False, True, True])
    return summary.drop(columns=["_sort_family"]).reset_index(drop=True)


def metric_readiness_family_summary_cards(frame: pd.DataFrame | None) -> list[dict[str, object]]:
    summary = metric_readiness_family_summary_frame(frame)
    if summary.empty:
        return [
            {
                "kicker": "BLOCKER SUMMARY",
                "title": "No metric blockers",
                "body": (
                    "No SPY/QQQ metric-readiness rows are available yet. Run the metric-readiness board after local price "
                    "and readiness artifacts exist."
                ),
                "badges": ["readiness-only", "not ranking"],
                "command": "make metric-readiness-board TOP_N=10",
            }
        ]
    actionable = summary.loc[summary["Blocker Family"].astype(str).str.lower().ne("none")]
    top = actionable.iloc[0] if not actionable.empty else summary.iloc[0]
    partial_blocked = int(top.get("Partial Rows", 0) or 0) + int(top.get("Blocked Rows", 0) or 0)
    families = summary["Blocker Family"].astype(str).tolist()
    family_text = ", ".join(families[:4]) + ("..." if len(families) > 4 else "")
    return [
        {
            "kicker": "METRIC BLOCKER SUMMARY",
            "title": f"{len(summary):,} blocker families",
            "body": (
                f"SPY/QQQ metric-readiness rows currently group into: {family_text}. "
                "Use this as coverage triage before opening row-level proof."
            ),
            "badges": ["SPY/QQQ", "family view", "not ranking"],
            "command": "make metric-readiness-board TOP_N=10",
        },
        {
            "kicker": "TOP FAMILY",
            "title": str(top.get("Blocker Family", "none")).title(),
            "body": (
                f"{int(top.get('Queue Rows', 0) or 0):,} row(s), {partial_blocked:,} partial or blocked, "
                f"benchmarks: {format_missing(top.get('Benchmarks'), 'SPY, QQQ')}. "
                "Rows with missing inputs stay blocked instead of inferred."
            ),
            "badges": ["blocked visible", "review metric only"],
            "command": str(top.get("First Next Check") or "make metric-readiness-board TOP_N=10"),
        },
        {
            "kicker": "NEXT REVIEW",
            "title": "Open row proof only when needed",
            "body": (
                "Open the evidence drawer for the first copy-only check and row-level proof. "
                "Sharpe, Sortino, beta, drawdown, trend, multiples, and peer dispersion remain review metrics only."
            ),
            "badges": ["copy-only", "no advice"],
            "command": str(top.get("First Next Check") or "make metric-readiness-board TOP_N=10"),
        },
    ]
