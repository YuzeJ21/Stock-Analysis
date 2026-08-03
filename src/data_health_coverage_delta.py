from __future__ import annotations

import re

import pandas as pd


READINESS_PROGRESS_FEATURES = [
    ("price_ready", "Price"),
    ("momentum_ready", "Momentum"),
    ("market_direction_ready", "Market direction"),
    ("liquidity_ready", "Liquidity"),
    ("correlation_ready", "Correlation"),
    ("fundamentals_ready", "Fundamentals"),
    ("dcf_ready", "DCF"),
    ("peer_ready", "Peers"),
    ("earnings_ready", "Earnings"),
    ("analyst_estimates_ready", "Analyst estimates"),
]


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


def _case_column(frame: pd.DataFrame | None, *candidates: str) -> str | None:
    if frame is None or frame.empty:
        return None
    by_lower = {str(column).strip().lower(): str(column) for column in frame.columns}
    for candidate in candidates:
        column = by_lower.get(candidate.strip().lower())
        if column is not None:
            return column
    return None


def _bool_series(frame: pd.DataFrame | None, column: str) -> pd.Series:
    if frame is None or frame.empty or column not in frame.columns:
        return pd.Series(dtype=bool)
    values = frame[column]
    if pd.api.types.is_bool_dtype(values):
        return values.fillna(False).astype(bool)
    return values.fillna("").astype(str).str.strip().str.lower().isin({"true", "1", "yes", "y"})


def _frame_bool_series(frame: pd.DataFrame, column: str) -> pd.Series:
    values = _bool_series(frame, column)
    if values.empty:
        return pd.Series(False, index=frame.index)
    return values.reindex(frame.index, fill_value=False)


def build_readiness_change_frame(
    current_frame: pd.DataFrame | None,
    previous_frame: pd.DataFrame | None = None,
) -> pd.DataFrame:
    columns = [
        "feature",
        "current_ready",
        "previous_ready",
        "delta_ready",
        "current_blocked",
        "newly_ready_tickers",
    ]
    if current_frame is None or current_frame.empty:
        return pd.DataFrame(columns=columns)

    current = current_frame.copy()
    previous = previous_frame.copy() if previous_frame is not None else pd.DataFrame()
    if "ticker" in current.columns:
        current["ticker"] = current["ticker"].astype(str).str.upper().str.strip()
    if not previous.empty and "ticker" in previous.columns:
        previous["ticker"] = previous["ticker"].astype(str).str.upper().str.strip()

    rows: list[dict[str, object]] = []
    for column, label in READINESS_PROGRESS_FEATURES:
        current_ready = _frame_bool_series(current, column)
        current_ready_count = int(current_ready.sum())
        previous_ready_count: int | None = None
        delta_ready: int | None = None
        newly_ready = ""
        if not previous.empty and column in previous.columns:
            previous_ready = _frame_bool_series(previous, column)
            previous_ready_count = int(previous_ready.sum())
            delta_ready = current_ready_count - previous_ready_count
            if "ticker" in current.columns and "ticker" in previous.columns:
                previous_ready_tickers = set(
                    previous.loc[previous_ready, "ticker"].dropna().astype(str).str.upper().str.strip()
                )
                current_ready_tickers = current.loc[current_ready, "ticker"].dropna().astype(str).str.upper().str.strip()
                newly_ready = ", ".join([ticker for ticker in current_ready_tickers if ticker not in previous_ready_tickers][:8])

        blocked_count = 0
        blocker_name = column.removesuffix("_ready")
        if "blocked_features" in current.columns:
            blocked_count = int(
                current["blocked_features"]
                .fillna("")
                .astype(str)
                .str.contains(rf"(?:^|,\s*){re.escape(blocker_name)}(?:$|,)", case=False, regex=True)
                .sum()
            )
        rows.append(
            {
                "feature": label,
                "current_ready": current_ready_count,
                "previous_ready": previous_ready_count,
                "delta_ready": delta_ready,
                "current_blocked": blocked_count,
                "newly_ready_tickers": newly_ready,
            }
        )
    return pd.DataFrame(rows, columns=columns)


def _latest_batch_proof_by_lane(batch_proof_frame: pd.DataFrame | None) -> dict[str, pd.Series]:
    if batch_proof_frame is None or batch_proof_frame.empty:
        return {}
    lane_col = _case_column(batch_proof_frame, "lane", "Lane")
    if lane_col is None:
        return {}
    review_col = _case_column(batch_proof_frame, "review_date", "Review Date")
    batch_col = _case_column(batch_proof_frame, "batch_id", "Batch ID")
    work = batch_proof_frame.copy()
    sort_cols = [col for col in (review_col, batch_col) if col is not None]
    if sort_cols:
        work = work.sort_values(sort_cols, ascending=[False] * len(sort_cols), kind="stable")
    latest: dict[str, pd.Series] = {}
    for _, row in work.iterrows():
        lane = _format_missing(row.get(lane_col), "").lower().strip()
        if lane and lane not in latest:
            latest[lane] = row
    return latest


def _delta_lane_aliases(feature: str) -> tuple[str, ...]:
    key = feature.lower()
    if key == "price":
        return ("prices", "price")
    if key in {"fundamentals", "dcf"}:
        return ("fundamentals", "fundamentals_dcf", "share_count")
    if key == "peers":
        return ("peers", "peer_mapping", "peer_valuation_inputs")
    if key == "earnings":
        return ("earnings", "optional_context")
    if key == "analyst estimates":
        return ("analyst_estimates", "optional_context")
    if key == "momentum":
        return ("prices", "price")
    return (key.replace(" ", "_"),)


def readiness_delta_board_frame(
    current_frame: pd.DataFrame | None,
    previous_frame: pd.DataFrame | None = None,
    batch_proof_frame: pd.DataFrame | None = None,
) -> pd.DataFrame:
    columns = [
        "Lane",
        "Current Ready",
        "Previous Ready",
        "Delta Ready",
        "Still Blocked",
        "Newly Ready Tickers",
        "Latest Batch Outcome",
        "Generated Artifacts Reviewed",
        "Next Safe Action",
    ]
    if current_frame is None or current_frame.empty:
        return pd.DataFrame(columns=columns)
    change_frame = build_readiness_change_frame(current_frame, previous_frame)
    latest_by_lane = _latest_batch_proof_by_lane(batch_proof_frame)
    rows: list[dict[str, object]] = []
    for row in change_frame.itertuples(index=False):
        feature = str(row.feature)
        latest = pd.Series(dtype=object)
        for lane in _delta_lane_aliases(feature):
            if lane in latest_by_lane:
                latest = latest_by_lane[lane]
                break
        latest_frame = pd.DataFrame([latest.to_dict()]) if not latest.empty else None
        outcome_col = _case_column(latest_frame, "final_outcome", "Final Outcome")
        artifacts_col = _case_column(latest_frame, "generated_artifacts_reviewed", "Generated Artifacts Reviewed")
        delta = row.delta_ready
        if pd.isna(delta):
            delta_label = "not available"
            action = "make readiness-snapshot PROFILE=<default|demo|local>"
        else:
            delta_value = int(delta)
            delta_label = f"{'+' if delta_value >= 0 else ''}{delta_value}"
            action = "make reviewed-batch-compare PROFILE=<default|demo|local> LANE=<lane> BATCH_ID=<reviewed_batch_id> REVIEW_DATE=<yyyy-mm-dd>" if delta_value else "keep lane blocked until source proof changes"
        rows.append(
            {
                "Lane": feature,
                "Current Ready": int(row.current_ready),
                "Previous Ready": "not available" if pd.isna(row.previous_ready) else int(row.previous_ready),
                "Delta Ready": delta_label,
                "Still Blocked": int(row.current_blocked),
                "Newly Ready Tickers": _format_missing(row.newly_ready_tickers, "none"),
                "Latest Batch Outcome": _format_missing(latest.get(outcome_col), "not recorded") if outcome_col else "not recorded",
                "Generated Artifacts Reviewed": _format_missing(latest.get(artifacts_col), "not recorded") if artifacts_col else "not recorded",
                "Next Safe Action": action,
            }
        )
    return pd.DataFrame(rows, columns=columns)


def readiness_delta_board_cards(
    current_frame: pd.DataFrame | None,
    previous_frame: pd.DataFrame | None = None,
    batch_proof_frame: pd.DataFrame | None = None,
) -> list[dict[str, object]]:
    if current_frame is None or current_frame.empty:
        return [
            {
                "kicker": "COVERAGE DELTA",
                "title": "Current readiness report missing",
                "body": "Refresh readiness before comparing prior and current coverage. Open operator details for read-only proof steps.",
                "badges": ["blocked", "read-only"],
                "command": "make readiness-preview TOP_N=20",
            }
        ]
    board = readiness_delta_board_frame(current_frame, previous_frame, batch_proof_frame)
    has_previous = previous_frame is not None and not previous_frame.empty
    if not has_previous:
        return [
            {
                "kicker": "COVERAGE DELTA",
                "title": "Current-only baseline",
                "body": (
                    "No prior readiness snapshot is available, so the board will not invent before/after changes. "
                    "Run a snapshot before the next reviewed batch, then rebuild readiness to compare real deltas."
                ),
                "badges": ["no prior snapshot", "no fabricated deltas"],
                "command": "make readiness-snapshot PROFILE=<default|demo|local>",
            }
        ]
    deltas = []
    for _, row in board.iterrows():
        delta_text = str(row.get("Delta Ready", ""))
        lane = str(row.get("Lane", ""))
        if delta_text not in {"", "not available", "+0", "0"}:
            deltas.append(f"{lane} {delta_text}")
    artifacts = board["Generated Artifacts Reviewed"].fillna("").astype(str)
    artifact_ready_mask = artifacts.str.strip().ne("") & (~artifacts.str.lower().isin({"not recorded", "nan", "none"}))
    artifact_ready = int(artifact_ready_mask.sum())
    return [
        {
            "kicker": "COVERAGE DELTA",
            "title": ", ".join(deltas[:3]) if deltas else "No ready-count change",
            "body": (
                f"{artifact_ready} lane(s) have generated-artifact review recorded. "
                "Use this board as data-readiness proof only; changed counts are not recommendations."
            ),
            "badges": ["previous vs current", "proof ledger aware"],
            "command": "make reviewed-batch-compare PROFILE=<default|demo|local> LANE=<lane> BATCH_ID=<reviewed_batch_id> REVIEW_DATE=<yyyy-mm-dd>",
        }
    ]
