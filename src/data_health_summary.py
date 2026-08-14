from __future__ import annotations

import os

import pandas as pd


def bool_series(frame: pd.DataFrame | None, column: str) -> pd.Series:
    if frame is None or frame.empty or column not in frame.columns:
        return pd.Series(dtype=bool)
    values = frame[column]
    if pd.api.types.is_bool_dtype(values):
        return values.fillna(False).astype(bool)
    return values.fillna("").astype(str).str.strip().str.lower().isin({"true", "1", "yes", "y"})


def ticker_set_from_bool(frame: pd.DataFrame | None, column: str) -> set[str]:
    if frame is None or frame.empty or "ticker" not in frame.columns:
        return set()
    mask = bool_series(frame, column)
    if mask.empty:
        return set()
    return set(frame.loc[mask, "ticker"].dropna().astype(str).str.upper().str.strip())


def dashboard_readiness_summary(
    coverage_frame: pd.DataFrame | None,
    dcf_readiness_frame: pd.DataFrame | None,
    earnings_readiness_frame: pd.DataFrame | None,
    analyst_readiness_frame: pd.DataFrame | None,
    ticker_readiness_frame: pd.DataFrame | None = None,
) -> dict[str, object]:
    ticker_columns = (
        set(ticker_readiness_frame.columns)
        if ticker_readiness_frame is not None and not ticker_readiness_frame.empty
        else set()
    )
    coverage_columns = (
        set(coverage_frame.columns)
        if coverage_frame is not None and not coverage_frame.empty
        else set()
    )
    count_evidence_keys: set[str] = set()
    if ticker_columns:
        if "price_ready" in ticker_columns:
            count_evidence_keys.add("price_ready")
        if "fundamentals_ready" in ticker_columns:
            count_evidence_keys.add("fundamentals_ready")
        if "peer_ready" in ticker_columns:
            count_evidence_keys.add("peer_ready")
    else:
        if coverage_columns.intersection({"has_prices", "price_ready"}):
            count_evidence_keys.add("price_ready")
        if "peer_ready" in coverage_columns:
            count_evidence_keys.add("peer_ready")
    if "dcf_ready" in ticker_columns or (
        dcf_readiness_frame is not None
        and not dcf_readiness_frame.empty
        and "is_dcf_ready" in dcf_readiness_frame.columns
    ):
        count_evidence_keys.add("dcf_ready")
    if "overall_readiness_state" in ticker_columns:
        count_evidence_keys.update({"blocked", "blocked_by_data"})
    universe_count = 0 if coverage_frame is None or coverage_frame.empty else len(coverage_frame)
    master_count = 0 if ticker_readiness_frame is None or ticker_readiness_frame.empty else int(bool_series(ticker_readiness_frame, "in_master_universe").sum())
    active_count = 0 if ticker_readiness_frame is None or ticker_readiness_frame.empty else int(bool_series(ticker_readiness_frame, "in_active_universe").sum())
    if ticker_readiness_frame is not None and not ticker_readiness_frame.empty:
        universe_count = master_count
        price_ready = int(bool_series(ticker_readiness_frame, "price_ready").sum())
        momentum_ready = int(bool_series(ticker_readiness_frame, "momentum_ready").sum())
        peer_ready = int(bool_series(ticker_readiness_frame, "peer_ready").sum())
    else:
        price_ready = len(ticker_set_from_bool(coverage_frame, "has_prices"))
        if not price_ready:
            price_ready = len(ticker_set_from_bool(coverage_frame, "price_ready"))
        momentum_ready = len(ticker_set_from_bool(coverage_frame, "usable_for_momentum"))
        if not momentum_ready:
            momentum_ready = len(ticker_set_from_bool(coverage_frame, "momentum_ready"))
        peer_ready = len(ticker_set_from_bool(coverage_frame, "peer_ready"))
    liquidity_ready = int(bool_series(ticker_readiness_frame, "liquidity_ready").sum()) if ticker_readiness_frame is not None else 0
    correlation_ready = int(bool_series(ticker_readiness_frame, "correlation_ready").sum()) if ticker_readiness_frame is not None else 0
    market_direction_ready = int(bool_series(ticker_readiness_frame, "market_direction_ready").sum()) if ticker_readiness_frame is not None else 0
    fundamentals_ready = int(bool_series(ticker_readiness_frame, "fundamentals_ready").sum()) if ticker_readiness_frame is not None else 0
    blocked_by_data = 0
    partial_count = 0
    excluded_count = 0
    if ticker_readiness_frame is not None and not ticker_readiness_frame.empty and "overall_readiness_state" in ticker_readiness_frame.columns:
        state_series = ticker_readiness_frame["overall_readiness_state"].fillna("").astype(str).str.lower()
        blocked_by_data = int(state_series.eq("blocked").sum())
        partial_count = int(state_series.eq("partial").sum())
        excluded_count = int(state_series.eq("excluded").sum())
    if ticker_readiness_frame is not None and not ticker_readiness_frame.empty and "dcf_ready" in ticker_readiness_frame.columns:
        dcf_ready = int(bool_series(ticker_readiness_frame, "dcf_ready").sum())
    else:
        dcf_ready = int(bool_series(dcf_readiness_frame, "is_dcf_ready").sum()) if dcf_readiness_frame is not None else 0
    dcf_excluded = 0
    if ticker_readiness_frame is not None and not ticker_readiness_frame.empty and "excluded_features" in ticker_readiness_frame.columns:
        dcf_excluded = int(
            ticker_readiness_frame["excluded_features"]
            .fillna("")
            .astype(str)
            .str.contains(r"\bdcf\b", case=False, na=False)
            .sum()
        )
    elif dcf_readiness_frame is not None and not dcf_readiness_frame.empty and "asset_type" in dcf_readiness_frame.columns:
        dcf_excluded = int(dcf_readiness_frame["asset_type"].fillna("company").astype(str).str.lower().ne("company").sum())
    if earnings_readiness_frame is not None:
        earnings_ready = int(bool_series(earnings_readiness_frame, "has_trusted_earnings").sum())
    elif ticker_readiness_frame is not None:
        earnings_ready = int(bool_series(ticker_readiness_frame, "earnings_ready").sum())
    else:
        earnings_ready = 0
    if analyst_readiness_frame is not None:
        analyst_ready = int(bool_series(analyst_readiness_frame, "has_trusted_analyst_estimates").sum())
    elif ticker_readiness_frame is not None:
        analyst_ready = int(bool_series(ticker_readiness_frame, "analyst_estimates_ready").sum())
    else:
        analyst_ready = 0
    updated_at = ""
    if ticker_readiness_frame is not None and not ticker_readiness_frame.empty and "updated_at" in ticker_readiness_frame.columns:
        updated_values = ticker_readiness_frame["updated_at"].dropna().astype(str).str.strip()
        if not updated_values.empty:
            updated_at = str(updated_values.max())
    missing_credentials = [
        name
        for name in ("STOOQ_API_KEY", "SEC_USER_AGENT")
        if not os.environ.get(name, "").strip()
    ]
    configured_credentials = [
        name
        for name in ("STOOQ_API_KEY", "SEC_USER_AGENT")
        if os.environ.get(name, "").strip()
    ]
    return {
        "universe_count": universe_count,
        "master_count": master_count or universe_count,
        "master_universe": master_count or universe_count,
        "active_count": active_count or universe_count,
        "active_universe": active_count or universe_count,
        "price_ready": price_ready,
        "momentum_ready": momentum_ready,
        "market_direction_ready": market_direction_ready,
        "liquidity_ready": liquidity_ready,
        "correlation_ready": correlation_ready,
        "fundamentals_ready": fundamentals_ready,
        "dcf_ready": dcf_ready,
        "dcf_excluded": dcf_excluded,
        "peer_ready": peer_ready,
        "earnings_ready": earnings_ready,
        "analyst_ready": analyst_ready,
        "analyst_estimates_ready": analyst_ready,
        "blocked_by_data": blocked_by_data,
        "blocked": blocked_by_data,
        "partial": partial_count,
        "excluded_count": excluded_count or dcf_excluded,
        "missing_credentials": missing_credentials,
        "configured_credentials": configured_credentials,
        "_count_evidence_keys": sorted(count_evidence_keys),
        "updated_at": updated_at,
        "manual_import_paths": [
            "Price import file folder: data/staged/prices/ -> make import-prices",
            "Fundamentals import file folder: data/staged/fundamentals/ -> make import-fundamentals",
            "Earnings import file folder: data/staged/earnings/ -> make import-earnings",
            "Analyst estimates import file folder: data/staged/analyst_estimates/ -> make import-analyst-estimates",
        ],
    }


def market_wide_readiness_summary(
    ticker_readiness_frame: pd.DataFrame | None,
    coverage_frame: pd.DataFrame | None = None,
    decisions_frame: pd.DataFrame | None = None,
) -> dict[str, object]:
    summary = dashboard_readiness_summary(
        coverage_frame,
        None,
        None,
        None,
        ticker_readiness_frame,
    )
    decisions = (
        {}
        if decisions_frame is None or decisions_frame.empty or "decision_bucket" not in decisions_frame.columns
        else {
            str(bucket): int(count)
            for bucket, count in decisions_frame["decision_bucket"].fillna("Not available").astype(str).value_counts().items()
        }
    )
    summary["decision_buckets"] = decisions
    return summary
