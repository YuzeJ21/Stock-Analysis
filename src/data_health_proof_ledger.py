from __future__ import annotations

import pandas as pd


DCF_PROOF_LANES = {"fundamentals", "fundamentals_dcf", "share_count"}
PEER_PROOF_LANES = {"peers", "peer_mapping", "peer_valuation_inputs"}


def case_column(frame: pd.DataFrame | None, *candidates: str) -> str | None:
    if frame is None or frame.empty:
        return None
    def _key(value: object) -> str:
        return str(value).strip().lower().replace(" ", "_")

    by_lower = {_key(column): str(column) for column in frame.columns}
    for candidate in candidates:
        column = by_lower.get(_key(candidate))
        if column is not None:
            return column
    return None


def latest_proof_row_for_lanes(batch_proof_frame: pd.DataFrame | None, lanes: set[str]) -> pd.Series:
    if batch_proof_frame is None or batch_proof_frame.empty:
        return pd.Series(dtype=object)
    lane_col = case_column(batch_proof_frame, "lane", "Lane")
    if lane_col is None:
        return pd.Series(dtype=object)
    normalized_lanes = batch_proof_frame[lane_col].fillna("").astype(str).str.lower().str.strip()
    matches = batch_proof_frame.loc[normalized_lanes.isin(lanes)]
    if matches.empty:
        return pd.Series(dtype=object)
    review_col = case_column(matches, "review_date", "Review Date")
    batch_col = case_column(matches, "batch_id", "Batch ID")
    sort_cols = [col for col in (review_col, batch_col) if col is not None]
    return matches.sort_values(sort_cols, ascending=[False] * len(sort_cols)).iloc[0] if sort_cols else matches.iloc[0]


def latest_dcf_proof_row(batch_proof_frame: pd.DataFrame | None) -> pd.Series:
    return latest_proof_row_for_lanes(batch_proof_frame, DCF_PROOF_LANES)


def latest_peer_proof_row(batch_proof_frame: pd.DataFrame | None) -> pd.Series:
    return latest_proof_row_for_lanes(batch_proof_frame, PEER_PROOF_LANES)


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


def _compact_fragment(value: object, fallback: str = "Not available", *, max_chars: int = 130) -> str:
    text = _format_missing(value, fallback).replace("\n", " ").strip()
    if len(text) > max_chars:
        text = text[: max_chars - 1].rstrip() + "..."
    if text.endswith("..."):
        return text
    return text.rstrip(" .;:")


def latest_proof_status_detail(
    batch_proof_frame: pd.DataFrame | None,
    latest: pd.Series | None,
    *,
    empty_detail: str,
) -> tuple[str, str, str]:
    latest_status = "not_recorded"
    latest_detail = empty_detail
    latest_command = "make reviewed-batch-proof"
    if latest is None or latest.empty:
        return latest_status, latest_detail, latest_command

    outcome_col = case_column(batch_proof_frame, "final_outcome", "Final Outcome")
    batch_col = case_column(batch_proof_frame, "batch_id", "Batch ID")
    date_col = case_column(batch_proof_frame, "review_date", "Review Date")
    changed_col = case_column(batch_proof_frame, "changed_readiness_counts", "Changed Readiness Counts")
    latest_status = _format_missing(latest.get(outcome_col), "not_recorded").lower() if outcome_col else "not_recorded"
    latest_detail = (
        f"Batch {_format_missing(latest.get(batch_col), 'not recorded')} on "
        f"{_format_missing(latest.get(date_col), 'not recorded')}; "
        f"{_compact_fragment(latest.get(changed_col), fallback='changed counts not recorded', max_chars=130)}"
    )
    return latest_status, latest_detail, latest_command
