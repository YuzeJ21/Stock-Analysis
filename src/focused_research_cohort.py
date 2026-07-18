"""Deterministic, read-only focused cohort selection for personal research."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import pandas as pd


ELIGIBLE_ASSET_TYPES = {"company", "adr"}
LANE_COLUMNS = (
    ("price", "price_ready"),
    ("momentum", "momentum_ready"),
    ("fundamentals", "fundamentals_ready"),
    ("dcf", "dcf_ready"),
    ("peers", "peer_ready"),
)


@dataclass(frozen=True)
class FocusedCohortMember:
    ticker: str
    company_name: str
    sector: str
    industry: str
    cohort_rationale: str
    usable_lanes: tuple[str, ...]
    blocked_lanes: tuple[str, ...]
    freshness_state: str
    last_review_date: str
    next_review_reason: str


@dataclass(frozen=True)
class FocusedCohort:
    status: str
    requested_size: int
    minimum_size: int
    eligible_count: int
    members: tuple[FocusedCohortMember, ...]
    message: str


def _text(value: object) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def _truthy(value: object) -> bool:
    return _text(value).lower() in {"true", "1", "yes", "y"}


def _explicit_false(value: object) -> bool:
    return _text(value).lower() in {"false", "0", "no", "n"}


def _ticker(value: object) -> str:
    return _text(value).upper()


def _normalized_frame(frame: pd.DataFrame | None) -> pd.DataFrame:
    if frame is None or frame.empty or "ticker" not in frame.columns:
        return pd.DataFrame()
    result = frame.copy()
    result.columns = [str(column).strip().lower() for column in result.columns]
    result["ticker"] = result["ticker"].map(_ticker)
    result = result[result["ticker"].ne("")].copy()
    return result


def _blocked_lanes(row: pd.Series) -> tuple[str, ...]:
    explicit = _text(row.get("blocked_features"))
    if explicit:
        values = [part.strip().lower() for part in explicit.split(",") if part.strip()]
        values = ["peers" if value == "peer" else value for value in values]
        return tuple(dict.fromkeys(values))
    return tuple(lane for lane, column in LANE_COLUMNS if not _truthy(row.get(column)))


def _usable_lanes(row: pd.Series) -> tuple[str, ...]:
    return tuple(lane for lane, column in LANE_COLUMNS if _truthy(row.get(column)))


def _rationale(row: pd.Series) -> str:
    if _truthy(row.get("in_active_universe")) and _truthy(row.get("dcf_ready")):
        return "Active research company with source-backed valuation inputs."
    if _truthy(row.get("dcf_ready")) and _truthy(row.get("peer_ready")):
        return "Company with source-backed valuation and trusted peer context."
    if _truthy(row.get("dcf_ready")):
        return "Company with source-backed valuation inputs."
    if _truthy(row.get("fundamentals_ready")):
        return "Company with source-backed fundamentals and price evidence."
    return "Operating company with reviewable price evidence; deeper lanes remain gated."


def _priority(row: pd.Series) -> tuple[int, int, int, int, int, str]:
    return (
        0 if _truthy(row.get("in_active_universe")) else 1,
        0 if _truthy(row.get("dcf_ready")) else 1,
        0 if _truthy(row.get("fundamentals_ready")) else 1,
        0 if _truthy(row.get("peer_ready")) else 1,
        0 if _truthy(row.get("momentum_ready")) else 1,
        _ticker(row.get("ticker")),
    )


def build_focused_cohort(
    ticker_readiness: pd.DataFrame | None,
    universe_master: pd.DataFrame | None,
    *,
    target_size: int = 25,
    minimum_size: int = 25,
    profile_freshness: str = "stale_or_unknown",
    last_review_dates: Mapping[str, str] | None = None,
) -> FocusedCohort:
    """Select a stable company cohort from existing readiness evidence only."""

    if target_size <= 0 or target_size > 50:
        raise ValueError("target_size must be between 1 and 50")
    if minimum_size <= 0 or minimum_size > target_size:
        raise ValueError("minimum_size must be between 1 and target_size")

    readiness = _normalized_frame(ticker_readiness)
    universe = _normalized_frame(universe_master)
    if readiness.empty or universe.empty:
        return FocusedCohort(
            status="unavailable",
            requested_size=target_size,
            minimum_size=minimum_size,
            eligible_count=0,
            members=(),
            message="Focused cohort inputs are unavailable.",
        )

    readiness = readiness.copy()
    readiness["_priority"] = readiness.apply(_priority, axis=1)
    readiness["_updated"] = readiness.get("updated_at", pd.Series("", index=readiness.index)).map(_text)
    readiness = readiness.sort_values(["_priority", "_updated"], ascending=[True, False]).drop_duplicates("ticker", keep="first")
    universe = universe.drop_duplicates("ticker", keep="last")
    universe_columns = [column for column in ("ticker", "asset_type", "is_active_listing", "sector", "industry", "name") if column in universe.columns]
    merged = readiness.merge(universe[universe_columns], on="ticker", how="inner", suffixes=("", "_universe"))
    eligible = merged[
        merged["asset_type"].map(lambda value: _text(value).lower() in ELIGIBLE_ASSET_TYPES)
        & ~merged["is_active_listing"].map(_explicit_false)
        & merged["price_ready"].map(_truthy)
    ].copy()
    eligible["_priority"] = eligible.apply(_priority, axis=1)
    eligible = eligible.sort_values("_priority").reset_index(drop=True)

    reviews = {_ticker(key): _text(value) for key, value in (last_review_dates or {}).items()}
    members: list[FocusedCohortMember] = []
    for _, row in eligible.head(target_size).iterrows():
        ticker = _ticker(row.get("ticker"))
        blocked = _blocked_lanes(row)
        company_name = _text(row.get("name")) or _text(row.get("name_universe")) or ticker
        members.append(
            FocusedCohortMember(
                ticker=ticker,
                company_name=company_name,
                sector=_text(row.get("sector")) or _text(row.get("sector_universe")),
                industry=_text(row.get("industry")) or _text(row.get("industry_universe")),
                cohort_rationale=_rationale(row),
                usable_lanes=_usable_lanes(row),
                blocked_lanes=blocked,
                freshness_state=_text(profile_freshness) or "stale_or_unknown",
                last_review_date=reviews.get(ticker, ""),
                next_review_reason=(
                    f"Review source evidence for {blocked[0]}."
                    if blocked
                    else "Review the latest comparable company evidence."
                ),
            )
        )

    status = "ready" if len(members) >= minimum_size else "awaiting_reviewed_source"
    message = (
        f"Focused cohort contains {len(members)} of {target_size} requested operating companies."
        if status == "ready"
        else f"Only {len(members)} eligible operating companies are currently reviewable; do not pad the cohort."
    )
    return FocusedCohort(
        status=status,
        requested_size=target_size,
        minimum_size=minimum_size,
        eligible_count=len(eligible),
        members=tuple(members),
        message=message,
    )


def focused_cohort_frame(cohort: FocusedCohort) -> pd.DataFrame:
    rows = [
        {
            "Ticker": member.ticker,
            "Company": member.company_name,
            "Sector": member.sector,
            "Industry": member.industry,
            "Usable now": ", ".join(member.usable_lanes) or "none",
            "Still gated": ", ".join(member.blocked_lanes) or "none",
            "Freshness": member.freshness_state.replace("_", " "),
            "Last review": member.last_review_date or "not recorded",
            "Next review reason": member.next_review_reason,
            "Cohort rationale": member.cohort_rationale,
        }
        for member in cohort.members
    ]
    return pd.DataFrame(
        rows,
        columns=[
            "Ticker",
            "Company",
            "Sector",
            "Industry",
            "Usable now",
            "Still gated",
            "Freshness",
            "Last review",
            "Next review reason",
            "Cohort rationale",
        ],
    )
