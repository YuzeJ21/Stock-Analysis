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
