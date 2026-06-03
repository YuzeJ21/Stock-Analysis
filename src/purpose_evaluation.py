from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from src.loader import normalize_columns
from src.paths import resolve_data_dir, resolve_outputs_dir, resolve_project_root


PURPOSE_EVALUATION_SUMMARY_CSV = "purpose_evaluation_summary.csv"

PURPOSE_EVALUATION_COLUMNS = [
    "purpose_family",
    "decision_bucket",
    "total_count",
    "active_universe_count",
    "research_now_count",
    "monitor_count",
    "blocked_count",
    "purpose_review_needed_count",
    "data_unlock_first_count",
    "peer_limited_count",
    "fundamentals_limited_count",
    "optional_context_locked_count",
    "top_primary_blocker",
    "top_unlock_command",
    "top_next_research_question",
    "sample_tickers",
    "Reason",
]

PURPOSE_EVALUATION_DRILLDOWN_COLUMNS = [
    "priority",
    "ticker",
    "is_active_universe",
    "purpose_family",
    "decision_bucket",
    "decision_subtype",
    "primary_blocker",
    "purpose_status",
    "purpose_alignment",
    "supported_analysis",
    "unsupported_analysis",
    "next_research_question",
    "risk_watchpoint",
    "invalidation_condition",
    "confidence_explanation",
    "data_confidence",
    "readiness_score",
    "peer_trend_status",
    "peer_valuation_status",
    "exact_command",
    "unlock_command",
    "source_freshness_note",
    "copy_only_note",
    "Reason",
]


def text_value(value: Any, fallback: str = "") -> str:
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


def purpose_family_label(asset_type: object, purpose_text: object = "", alignment_text: object = "") -> str:
    asset_kind = text_value(asset_type).lower()
    if asset_kind in {"etf", "index_proxy", "fund"}:
        return "ETF / Hedge"
    combined = " ".join(
        part.lower()
        for part in [asset_kind, text_value(purpose_text), text_value(alignment_text)]
        if part
    )
    if any(token in combined for token in ["etf", "index proxy", "index_proxy", "hedge", "defensive"]):
        return "ETF / Hedge"
    if "momentum" in combined:
        return "Momentum"
    if "pullback" in combined:
        return "Pullback"
    if "compounder" in combined or "core" in combined:
        return "Compounder"
    if any(token in combined for token in ["re-rating", "undervalued", "value"]):
        return "Re-rating"
    if "speculative" in combined or "optionality" in combined:
        return "Speculative"
    if "broken" in combined or "avoid" in combined:
        return "Broken / Avoid"
    return "General"


def purpose_status_label(alignment_text: object, decision_bucket: object) -> str:
    alignment = text_value(alignment_text).lower()
    bucket = text_value(decision_bucket).lower()
    if "needs review" in alignment:
        return "Purpose review needed"
    if any(token in alignment for token in ["cannot be checked", "not testable", "is blocked"]):
        return "Purpose locked by data"
    if "monitor" in bucket:
        return "Monitor context"
    if "blocked" in bucket:
        return "Data unlock first"
    return "Purpose supported by current local data"


def purpose_unlock_command(
    ticker: object,
    primary_blocker: object,
    exact_command: object = "",
    asset_type: object = "",
    decision_bucket: object = "",
    decision_subtype: object = "",
) -> str:
    symbol = text_value(ticker).upper()
    blocker = text_value(primary_blocker).lower().replace(" ", "_")
    asset_kind = text_value(asset_type).lower()
    bucket = text_value(decision_bucket).lower()
    subtype = text_value(decision_subtype).lower()
    if not symbol:
        return text_value(exact_command, "make project-status")
    fallback = text_value(exact_command, f"make stock-report TICKER={symbol}")
    if "monitor" in bucket or "market proxy" in subtype or asset_kind in {"etf", "index_proxy", "fund"}:
        return fallback
    if blocker == "price":
        return f"make focus-price TICKER={symbol}"
    if blocker in {"fundamentals", "dcf"}:
        return f"make focus-fundamentals TICKER={symbol}"
    if blocker in {"peer", "peers"}:
        return f"make focus-peers TICKER={symbol}"
    if blocker in {"earnings", "analyst_estimates"}:
        return "make templates"
    return fallback


def purpose_drilldown_priority(row: pd.Series) -> int:
    active_rank = 0 if bool(row.get("in_active_universe")) else 10
    bucket = text_value(row.get("decision_bucket")).lower()
    blocker = text_value(row.get("primary_blocker")).lower()
    if bucket == "research now" and blocker in {"peers", "peer"}:
        return active_rank + 1
    if bucket == "research now":
        return active_rank + 2
    if bucket == "monitor":
        return active_rank + 3
    if blocker in {"fundamentals", "dcf"}:
        return active_rank + 4
    if blocker == "price":
        return active_rank + 5
    if bucket == "blocked by data":
        return active_rank + 6
    return active_rank + 9


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    frame = pd.read_csv(path)
    frame.columns = normalize_columns(list(frame.columns))
    if "ticker" in frame.columns:
        frame["ticker"] = frame["ticker"].astype("string").str.upper().str.strip()
    return frame


def _bool_series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(False, index=frame.index)
    values = frame[column]
    if pd.api.types.is_bool_dtype(values):
        return values.fillna(False).astype(bool)
    return values.fillna("").astype(str).str.strip().str.lower().isin({"true", "1", "yes", "y"})


def _contains(frame: pd.DataFrame, column: str, pattern: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(False, index=frame.index)
    return frame[column].fillna("").astype(str).str.contains(pattern, case=False, na=False, regex=True)


def _mode_text(values: pd.Series, fallback: str = "none") -> str:
    clean = values.fillna("").astype(str).str.strip()
    clean = clean[~clean.str.lower().isin({"", "nan", "none", "null", "<na>"})]
    if clean.empty:
        return fallback
    return str(clean.value_counts().index[0])


def _first_text(values: pd.Series, fallback: str = "Not available") -> str:
    for value in values.fillna("").astype(str):
        text = text_value(value)
        if text:
            return text
    return fallback


def _first_row_text(row: pd.Series, *columns: str, fallback: str = "") -> str:
    for column in columns:
        text = text_value(row.get(column))
        if text:
            return text
    return fallback


def _sample_tickers(values: pd.Series, limit: int = 8) -> str:
    tickers = [text_value(value).upper() for value in values if text_value(value)]
    return ", ".join(list(dict.fromkeys(tickers).keys())[:limit])


def _summary_next_research_question(group: pd.DataFrame, purpose_family: object, decision_bucket: object) -> str:
    family = text_value(purpose_family).lower()
    bucket = text_value(decision_bucket).lower()
    asset_types = group.get("asset_type", pd.Series("", index=group.index)).fillna("").astype(str).str.lower()
    subtypes = group.get("decision_subtype", pd.Series("", index=group.index)).fillna("").astype(str).str.lower()
    if (
        "monitor" in bucket
        or "etf" in family
        or "hedge" in family
        or asset_types.isin({"etf", "index_proxy", "fund"}).any()
        or subtypes.str.contains("market proxy", na=False).any()
    ):
        return "What market, theme, liquidity, or risk signal should this proxy monitor, and what would invalidate that proxy role?"
    return _first_text(group["next_research_question"], "Open a ticker report for the next research question.")


def _drilldown_is_monitor(row: pd.Series) -> bool:
    asset_type = text_value(row.get("asset_type")).lower()
    family = text_value(row.get("purpose_family")).lower()
    bucket = text_value(row.get("decision_bucket")).lower()
    subtype = text_value(row.get("decision_subtype")).lower()
    return (
        "monitor" in bucket
        or "market proxy" in subtype
        or asset_type in {"etf", "index_proxy", "fund"}
        or any(token in family for token in ["etf", "hedge", "fund", "index"])
    )


def _drilldown_supported_analysis(row: pd.Series) -> str:
    supported = _first_row_text(row, "supported_analysis", "supporting_features", "feature_summary", "ready_features")
    if supported:
        return f"Supported analysis: {supported}."
    return f"Supported analysis is limited to the current {text_value(row.get('decision_bucket'), 'local')} readiness state."


def _drilldown_unsupported_analysis(row: pd.Series) -> str:
    if _drilldown_is_monitor(row):
        return "Unsupported analysis: operating-company DCF and peer valuation are excluded for ETF/index/fund monitor context."
    unsupported = _first_row_text(row, "unsupported_analysis", "missing_data", "blocked_features", "excluded_features")
    if unsupported:
        return f"Unsupported analysis: {unsupported}."
    return "Unsupported analysis remains withheld when fundamentals, peers, earnings, or analyst estimates are unavailable."


def _drilldown_next_question(row: pd.Series) -> str:
    ticker = text_value(row.get("ticker"), "TICKER").upper()
    blocker = text_value(row.get("primary_blocker")).lower().replace(" ", "_")
    if _drilldown_is_monitor(row):
        return f"What market, theme, liquidity, or risk signal should {ticker} monitor, and what would invalidate that proxy role?"
    if blocker in {"peer", "peers"}:
        return f"Which source-backed peers should be added for {ticker} before peer-relative valuation is reviewed?"
    if blocker in {"fundamentals", "dcf"}:
        return f"Which trusted fundamentals or DCF inputs are still missing for {ticker}?"
    if blocker == "price":
        return f"Which local price coverage gap must be repaired for {ticker} before setup analysis is reviewed?"
    if blocker in {"earnings", "analyst_estimates", "analyst"}:
        return f"Is trusted local earnings or analyst-estimate context available for {ticker}, or should optional context stay locked?"
    return f"Which trusted local input or review step is needed next for {ticker}?"


def _drilldown_risk_watchpoint(row: pd.Series) -> str:
    blocker = text_value(row.get("primary_blocker"), "missing local data")
    if _drilldown_is_monitor(row):
        return "Risk watchpoint: monitor liquidity, correlation, theme exposure, and whether the proxy still matches its intended role."
    if blocker in {"peer", "peers"}:
        return "Risk watchpoint: peer-relative context is incomplete, so valuation comparison and opportunity-cost analysis remain withheld."
    if blocker in {"fundamentals", "dcf"}:
        return "Risk watchpoint: valuation interpretation is blocked until trusted fundamentals and DCF inputs are complete."
    if blocker == "price":
        return "Risk watchpoint: setup, momentum, liquidity, and risk analysis are blocked until local price coverage is sufficient."
    return f"Risk watchpoint: conclusions are limited by {blocker}."


def _drilldown_invalidation_condition(row: pd.Series) -> str:
    blocker = text_value(row.get("primary_blocker"), "required readiness checks")
    if _drilldown_is_monitor(row):
        return "Invalidate market-proxy usefulness if liquidity, correlation, or theme trend no longer supports the intended monitoring role."
    return f"Invalidate this research brief if local readiness no longer supports the stated purpose or if {blocker} remains unresolved for the intended analysis."


def _drilldown_confidence_explanation(row: pd.Series) -> str:
    confidence = text_value(row.get("data_confidence"), "limited")
    score = text_value(row.get("readiness_score"))
    if _drilldown_is_monitor(row):
        score_text = f" Readiness score: {score}." if score else ""
        return (
            f"Confidence is {confidence} because only ready local monitor inputs are used. "
            "Operating-company DCF and peer valuation are excluded, not treated as failed monitor inputs."
            f"{score_text}"
        )
    blocker = text_value(row.get("primary_blocker"), "none")
    score_text = f" Readiness score: {score}." if score else ""
    return f"Confidence is {confidence} because only ready local inputs are used. Limiting factor: {blocker}.{score_text}"


def _fill_drilldown_text(frame: pd.DataFrame, column: str, builder: Any) -> None:
    current = frame[column].fillna("").astype(str).str.strip()
    missing = current.eq("") | current.str.lower().isin({"nan", "none", "null", "<na>", "not available"})
    if missing.any():
        frame.loc[missing, column] = frame.loc[missing].apply(builder, axis=1)


def enrich_purpose_evaluation_rows(decisions: pd.DataFrame, readiness: pd.DataFrame | None = None) -> pd.DataFrame:
    return enrich_purpose_evaluation_rows_with_purpose(decisions, readiness)


def enrich_purpose_evaluation_rows_with_purpose(
    decisions: pd.DataFrame,
    readiness: pd.DataFrame | None = None,
    purpose_classification: pd.DataFrame | None = None,
) -> pd.DataFrame:
    if decisions is None or decisions.empty:
        return pd.DataFrame()
    frame = decisions.copy()
    frame.columns = normalize_columns(list(frame.columns))
    if "ticker" not in frame.columns:
        return pd.DataFrame()
    frame["ticker"] = frame["ticker"].astype("string").str.upper().str.strip()
    for column in [
        "asset_type",
        "purpose_thesis",
        "purpose_alignment",
        "decision_bucket",
        "primary_blocker",
        "exact_command",
        "next_research_question",
        "review_priority_reason",
        "blocked_features",
        "missing_data",
    ]:
        if column not in frame.columns:
            frame[column] = ""

    if readiness is not None and not readiness.empty:
        ready = readiness.copy()
        ready.columns = normalize_columns(list(ready.columns))
        if "ticker" in ready.columns:
            ready["ticker"] = ready["ticker"].astype("string").str.upper().str.strip()
            active_cols = ["ticker"]
            for column in ("in_active_universe", "overall_readiness_state", "updated_at", "ready_features", "partial_features"):
                if column in ready.columns:
                    active_cols.append(column)
            frame = frame.merge(ready[active_cols].drop_duplicates("ticker"), on="ticker", how="left")
    if purpose_classification is not None and not purpose_classification.empty:
        purpose = purpose_classification.copy()
        purpose.columns = normalize_columns(list(purpose.columns))
        if "ticker" not in purpose.columns:
            purpose = pd.DataFrame()
    if purpose_classification is not None and not purpose_classification.empty and not purpose.empty:
        purpose["ticker"] = purpose["ticker"].astype("string").str.upper().str.strip()
        purpose_cols = ["ticker"]
        for column in ("finalprimarypurpose", "declaredprimarypurpose", "defaultpurpose"):
            if column in purpose.columns:
                purpose_cols.append(column)
        frame = frame.merge(purpose[purpose_cols].drop_duplicates("ticker"), on="ticker", how="left")
    if "in_active_universe" not in frame.columns:
        frame["in_active_universe"] = False

    frame["purpose_family"] = frame.apply(
        lambda row: purpose_family_label(
            row.get("asset_type"),
            text_value(row.get("purpose_thesis"))
            or text_value(row.get("finalprimarypurpose"))
            or text_value(row.get("declaredprimarypurpose"))
            or text_value(row.get("defaultpurpose")),
            row.get("purpose_alignment"),
        ),
        axis=1,
    )
    frame["purpose_status"] = frame.apply(
        lambda row: purpose_status_label(row.get("purpose_alignment"), row.get("decision_bucket")),
        axis=1,
    )
    frame["unlock_command"] = frame.apply(
        lambda row: purpose_unlock_command(
            row.get("ticker"),
            row.get("primary_blocker"),
            row.get("exact_command"),
            row.get("asset_type"),
            row.get("decision_bucket"),
            row.get("decision_subtype"),
        ),
        axis=1,
    )
    return frame


def build_purpose_evaluation_drilldown(
    decisions: pd.DataFrame | None,
    readiness: pd.DataFrame | None = None,
    purpose_classification: pd.DataFrame | None = None,
    peer_readiness: pd.DataFrame | None = None,
    *,
    active_only: bool = True,
    purpose_family: str = "All",
    decision_bucket: str = "All",
    primary_blocker: str = "All",
    limit: int = 25,
) -> pd.DataFrame:
    if decisions is None or decisions.empty:
        return pd.DataFrame(columns=PURPOSE_EVALUATION_DRILLDOWN_COLUMNS)
    frame = enrich_purpose_evaluation_rows_with_purpose(decisions, readiness, purpose_classification)
    if frame.empty:
        return pd.DataFrame(columns=PURPOSE_EVALUATION_DRILLDOWN_COLUMNS)

    if peer_readiness is not None and not peer_readiness.empty:
        peers = peer_readiness.copy()
        peers.columns = normalize_columns(list(peers.columns))
        if "ticker" in peers.columns:
            peers["ticker"] = peers["ticker"].astype("string").str.upper().str.strip()
            peer_cols = ["ticker"]
            for column in ("peer_trend_comparison_ready", "peer_valuation_comparison_ready"):
                if column in peers.columns:
                    peer_cols.append(column)
            frame = frame.merge(peers[peer_cols].drop_duplicates("ticker"), on="ticker", how="left")

    if active_only:
        frame = frame.loc[_bool_series(frame, "in_active_universe")].copy()
    if purpose_family != "All":
        frame = frame.loc[frame["purpose_family"].fillna("").astype(str).eq(purpose_family)].copy()
    if decision_bucket != "All":
        frame = frame.loc[frame["decision_bucket"].fillna("").astype(str).eq(decision_bucket)].copy()
    if primary_blocker != "All":
        frame = frame.loc[frame["primary_blocker"].fillna("").astype(str).eq(primary_blocker)].copy()
    if frame.empty:
        return pd.DataFrame(columns=PURPOSE_EVALUATION_DRILLDOWN_COLUMNS)

    for column in [
        "decision_subtype",
        "purpose_alignment",
        "supported_analysis",
        "supporting_features",
        "feature_summary",
        "ready_features",
        "unsupported_analysis",
        "next_research_question",
        "risk_watchpoint",
        "invalidation_condition",
        "confidence_explanation",
        "data_confidence",
        "readiness_score",
        "overall_readiness_state",
        "updated_at",
        "missing_data",
        "blocked_features",
        "excluded_features",
        "Reason",
    ]:
        if column not in frame.columns:
            frame[column] = ""
    for column in ("peer_trend_comparison_ready", "peer_valuation_comparison_ready"):
        if column not in frame.columns:
            frame[column] = False

    frame["priority"] = frame.apply(purpose_drilldown_priority, axis=1)
    frame["exact_command"] = frame["ticker"].apply(lambda ticker: f"make stock-report TICKER={ticker}")
    frame["unlock_command"] = frame.apply(
        lambda row: purpose_unlock_command(
            row.get("ticker"),
            row.get("primary_blocker"),
            row.get("exact_command"),
            row.get("asset_type"),
            row.get("decision_bucket"),
            row.get("decision_subtype"),
        ),
        axis=1,
    )
    _fill_drilldown_text(frame, "purpose_alignment", lambda row: f"{text_value(row.get('purpose_status'), 'Purpose status')} for current local data.")
    _fill_drilldown_text(frame, "supported_analysis", _drilldown_supported_analysis)
    _fill_drilldown_text(frame, "unsupported_analysis", _drilldown_unsupported_analysis)
    _fill_drilldown_text(frame, "next_research_question", _drilldown_next_question)
    _fill_drilldown_text(frame, "risk_watchpoint", _drilldown_risk_watchpoint)
    _fill_drilldown_text(frame, "invalidation_condition", _drilldown_invalidation_condition)
    _fill_drilldown_text(frame, "confidence_explanation", _drilldown_confidence_explanation)
    frame["peer_trend_status"] = frame["peer_trend_comparison_ready"].apply(
        lambda value: "peer trend possible" if str(value).strip().lower() in {"true", "1", "yes"} else "peer trend blocked"
    )
    frame["peer_valuation_status"] = frame["peer_valuation_comparison_ready"].apply(
        lambda value: "peer valuation ready" if str(value).strip().lower() in {"true", "1", "yes"} else "peer valuation blocked"
    )
    frame["source_freshness_note"] = frame.apply(
        lambda row: (
            f"Readiness state {text_value(row.get('overall_readiness_state'), 'unknown')} "
            f"from local CSV outputs updated {text_value(row.get('updated_at'), 'not available')}."
        ),
        axis=1,
    )
    frame["copy_only_note"] = "Copy-only command; the dashboard does not execute imports, refreshes, or external account actions."
    frame["Reason"] = frame.apply(
        lambda row: text_value(
            row.get("Reason"),
            f"{text_value(row.get('purpose_family'), 'Purpose')} / {text_value(row.get('decision_bucket'), 'decision')} drilldown is based on current local readiness and decision outputs.",
        ),
        axis=1,
    )
    frame["is_active_universe"] = _bool_series(frame, "in_active_universe")

    return frame.sort_values(["priority", "ticker"], kind="stable")[
        PURPOSE_EVALUATION_DRILLDOWN_COLUMNS
    ].head(limit).reset_index(drop=True)


def build_purpose_evaluation_summary(
    decisions: pd.DataFrame | None,
    readiness: pd.DataFrame | None = None,
    purpose_classification: pd.DataFrame | None = None,
) -> pd.DataFrame:
    if decisions is None or decisions.empty:
        return pd.DataFrame(columns=PURPOSE_EVALUATION_COLUMNS)
    frame = enrich_purpose_evaluation_rows_with_purpose(decisions, readiness, purpose_classification)
    if frame.empty:
        return pd.DataFrame(columns=PURPOSE_EVALUATION_COLUMNS)

    grouped_rows: list[dict[str, Any]] = []
    for (purpose_family, decision_bucket), group in frame.groupby(["purpose_family", "decision_bucket"], dropna=False):
        active_count = int(_bool_series(group, "in_active_universe").sum())
        review_count = int(_contains(group, "purpose_status", "review needed").sum())
        data_unlock_count = int(_contains(group, "purpose_status", "locked by data|data unlock first").sum())
        peer_limited_count = int(
            (
                _contains(group, "primary_blocker", r"^peers?$")
                | _contains(group, "review_priority_reason", "peer-relative|peer-limited")
                | _contains(group, "blocked_features", "peer")
                | _contains(group, "missing_data", "peer")
            ).sum()
        )
        fundamentals_limited_count = int(
            (
                _contains(group, "primary_blocker", "fundamentals|dcf")
                | _contains(group, "blocked_features", "fundamentals|dcf")
                | _contains(group, "missing_data", "fundamental|free_cash_flow|dcf")
            ).sum()
        )
        optional_context_count = int(
            (
                _contains(group, "primary_blocker", "earnings|analyst")
                | _contains(group, "blocked_features", "earnings|analyst")
                | _contains(group, "missing_data", "earnings|analyst")
            ).sum()
        )
        grouped_rows.append(
            {
                "purpose_family": text_value(purpose_family, "General"),
                "decision_bucket": text_value(decision_bucket, "Unknown"),
                "total_count": int(len(group)),
                "active_universe_count": active_count,
                "research_now_count": int((group["decision_bucket"] == "Research Now").sum()),
                "monitor_count": int((group["decision_bucket"] == "Monitor").sum()),
                "blocked_count": int((group["decision_bucket"] == "Blocked by Data").sum()),
                "purpose_review_needed_count": review_count,
                "data_unlock_first_count": data_unlock_count,
                "peer_limited_count": peer_limited_count,
                "fundamentals_limited_count": fundamentals_limited_count,
                "optional_context_locked_count": optional_context_count,
                "top_primary_blocker": _mode_text(group["primary_blocker"]),
                "top_unlock_command": _first_text(group["unlock_command"], "make project-status"),
                "top_next_research_question": _summary_next_research_question(group, purpose_family, decision_bucket),
                "sample_tickers": _sample_tickers(group["ticker"]),
                "Reason": (
                    f"{text_value(purpose_family, 'General')} / {text_value(decision_bucket, 'Unknown')} "
                    "summarizes current local decision and readiness rows; blocked context remains an input-unlock checklist."
                ),
            }
        )

    summary = pd.DataFrame(grouped_rows, columns=PURPOSE_EVALUATION_COLUMNS)
    return summary.sort_values(
        by=["active_universe_count", "research_now_count", "monitor_count", "total_count", "purpose_family", "decision_bucket"],
        ascending=[False, False, False, False, True, True],
    ).reset_index(drop=True)


def write_purpose_evaluation_summary(
    project_root: Path | str | None = None,
    *,
    data_dir: Path | str | None = None,
    output_dir: Path | str | None = None,
) -> pd.DataFrame:
    root = resolve_project_root(project_root)
    data_path = resolve_data_dir(data_dir, root)
    output_path = resolve_outputs_dir(output_dir, root)
    decisions = _read_csv(output_path / "research_decisions.csv")
    readiness = _read_csv(data_path / "reports" / "ticker_readiness_report.csv")
    purpose_classification = _read_csv(output_path / "purpose_classification.csv")
    summary = build_purpose_evaluation_summary(decisions, readiness, purpose_classification)
    output_path.mkdir(parents=True, exist_ok=True)
    summary.to_csv(output_path / PURPOSE_EVALUATION_SUMMARY_CSV, index=False)
    return summary
