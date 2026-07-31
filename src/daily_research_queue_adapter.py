"""Read-only selected-profile adapter for the daily research queue."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date
import math
from pathlib import Path
from typing import Iterable, Mapping

import pandas as pd

from src.commercial_source_rights import (
    SourceRights,
    load_source_rights_registry,
    review_commercial_field_scope,
)
from src.config import AppConfig
from src.daily_research_queue import (
    DailyQueueEvidence,
    DailyQueuePolicy,
    DailyQueueResult,
    evaluate_daily_queue,
)
from src.historical_valuation_regime import (
    ValuationObservation,
    build_valuation_regime,
    load_valuation_observations,
)
from src.indicators import compute_return, relative_strength, sma
from src.observation_recency import CURRENT_MAX_AGE_DAYS


PRICE_SCOPE = ("prices",)
FUNDAMENTAL_SCOPE = ("free_cash_flow", "revenue_growth", "debt_to_equity")


@dataclass(frozen=True)
class DailyQueueBuildStatus:
    result: DailyQueueResult
    considered_count: int
    readiness_row_count: int
    price_row_count: int
    valuation_observation_count: int
    blocker_counts: tuple[tuple[str, int], ...]
    message: str


def _text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def _ticker(value: object) -> str:
    return _text(value).upper()


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not pd.isna(value):
        return bool(value)
    return _text(value).lower() in {"1", "true", "yes", "ready"}


def _numeric(value: object) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def _optional_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except (
        FileNotFoundError,
        OSError,
        UnicodeError,
        pd.errors.ParserError,
        pd.errors.EmptyDataError,
    ):
        return pd.DataFrame()


def _normalized(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = frame.copy()
    normalized.columns = [
        str(column).strip().lower().replace(" ", "_").replace("-", "_")
        for column in normalized.columns
    ]
    if "ticker" in normalized.columns:
        normalized["ticker"] = normalized["ticker"].map(_ticker)
    return normalized


def _latest_valid_date(frame: pd.DataFrame, *, as_of: date) -> str:
    if frame.empty or "date" not in frame.columns:
        return ""
    valid: list[date] = []
    for value in frame["date"]:
        try:
            parsed = date.fromisoformat(_text(value))
        except ValueError:
            continue
        if parsed <= as_of:
            valid.append(parsed)
    return max(valid).isoformat() if valid else ""


def _is_current(through_date: str, *, as_of: date) -> bool:
    try:
        observed = date.fromisoformat(through_date)
    except ValueError:
        return False
    return 0 <= (as_of - observed).days <= CURRENT_MAX_AGE_DAYS


def _price_evidence_states(
    ticker_prices: pd.DataFrame,
    spy_prices: pd.DataFrame,
    *,
    registry: Mapping[str, SourceRights],
) -> tuple[bool, bool, bool]:
    scoped = pd.concat((ticker_prices, spy_prices), ignore_index=True)
    lineage_fields = {"source", "source_ref", "retrieved_at"}
    if scoped.empty or not lineage_fields.issubset(scoped.columns):
        return False, False, False
    provenance = all(
        _text(row.get(field))
        for _, row in scoped.iterrows()
        for field in lineage_fields
    )
    if not provenance:
        return False, False, False
    sources = tuple(sorted({_text(value) for value in scoped["source"] if _text(value)}))
    if not sources:
        return provenance, False, False
    reviews = [
        review_commercial_field_scope(registry, source, PRICE_SCOPE)
        for source in sources
    ]
    return (
        provenance,
        all(review.commercial_rights_approved for review in reviews),
        all(not review.missing_supported_fields for review in reviews),
    )


def _fundamental_evidence_states(
    row: pd.Series | None,
    *,
    registry: Mapping[str, SourceRights],
) -> tuple[bool, bool, bool]:
    if row is None:
        return False, False, False
    provenance = all(
        _text(row.get(field))
        for field in ("source", "source_ref", "retrieved_at")
    )
    source = _text(row.get("source"))
    if not source:
        return provenance, False, False
    review = review_commercial_field_scope(registry, source, FUNDAMENTAL_SCOPE)
    return (
        provenance,
        review.commercial_rights_approved,
        not review.missing_supported_fields,
    )


def _row_by_ticker(frame: pd.DataFrame, ticker: str) -> pd.Series | None:
    if frame.empty or "ticker" not in frame.columns:
        return None
    rows = frame.loc[frame["ticker"].map(_ticker).eq(ticker)]
    if len(rows) != 1:
        return None
    return rows.iloc[0]


def _indicator_lookup(
    prices: pd.DataFrame,
    universe: pd.DataFrame,
    theme_map: pd.DataFrame,
    config: AppConfig,
) -> dict[str, pd.Series]:
    del universe, theme_map
    if prices.empty or not {"ticker", "date", "close"}.issubset(prices.columns):
        return {}
    frame = prices.loc[:, ["ticker", "date", "close"]].copy()
    frame["ticker"] = frame["ticker"].map(_ticker)
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    frame = frame.dropna(subset=["ticker", "date", "close"]).sort_values(
        ["ticker", "date"]
    )
    if frame.empty:
        return {}
    grouped = {
        ticker: ticker_frame.set_index("date")["close"]
        for ticker, ticker_frame in frame.groupby("ticker", sort=False)
    }
    spy = grouped.get("SPY", pd.Series(dtype=float))
    lookbacks = config.returns.get("lookbacks", {})
    one_month = int(lookbacks.get("one_month", 21))
    three_month = int(lookbacks.get("three_month", 63))
    six_month = int(lookbacks.get("six_month", 126))
    sma_windows = sorted(
        int(value) for value in config.moving_averages.get("sma", [50, 200])
    )
    medium_sma = sma_windows[0] if sma_windows else 50
    long_sma = sma_windows[1] if len(sma_windows) > 1 else 200
    result: dict[str, pd.Series] = {}
    for ticker, close in grouped.items():
        medium = sma(close, medium_sma, min_periods=medium_sma).iloc[-1]
        long = sma(close, long_sma, min_periods=long_sma).iloc[-1]
        result[ticker] = pd.Series(
            {
                "ticker": ticker,
                "close": close.iloc[-1],
                "sma_50": medium,
                "sma_200": long,
                "return_3m": compute_return(close, three_month),
                "return_6m": compute_return(close, six_month),
                "relative_return_vs_spy": relative_strength(
                    close,
                    spy,
                    one_month,
                ),
            }
        )
    return result


def _valuation_by_ticker(
    observations: Iterable[ValuationObservation],
) -> dict[str, tuple[ValuationObservation, ...]]:
    grouped: dict[str, list[ValuationObservation]] = {}
    for row in observations:
        ticker = _ticker(row.ticker)
        if ticker:
            grouped.setdefault(ticker, []).append(row)
    return {ticker: tuple(rows) for ticker, rows in grouped.items()}


def build_daily_research_queue(
    *,
    readiness: pd.DataFrame,
    prices: pd.DataFrame,
    fundamentals: pd.DataFrame,
    universe: pd.DataFrame,
    theme_map: pd.DataFrame,
    valuation_observations: Iterable[ValuationObservation],
    config: AppConfig,
    rights_registry: Mapping[str, SourceRights],
    as_of: date,
    policy: DailyQueuePolicy | None = None,
) -> DailyQueueBuildStatus:
    """Build a queue entirely in memory from explicit selected-profile inputs."""

    readiness_frame = _normalized(readiness)
    price_frame = _normalized(prices)
    fundamental_frame = _normalized(fundamentals)
    universe_frame = _normalized(universe)
    theme_frame = _normalized(theme_map)
    selected = (
        readiness_frame.loc[
            readiness_frame.get("momentum_ready", pd.Series(False, index=readiness_frame.index)).map(_truthy)
        ]
        if "ticker" in readiness_frame.columns
        else pd.DataFrame()
    )
    selected_tickers = tuple(sorted({_ticker(value) for value in selected.get("ticker", ()) if _ticker(value)}))
    price_groups = (
        {
            ticker: ticker_frame.copy()
            for ticker, ticker_frame in price_frame.groupby("ticker", sort=False)
            if ticker
        }
        if not price_frame.empty and "ticker" in price_frame.columns
        else {}
    )
    indicator_rows = _indicator_lookup(
        price_frame,
        universe_frame,
        theme_frame,
        config,
    )
    valuations = tuple(valuation_observations)
    valuations_by_ticker = _valuation_by_ticker(valuations)
    through_dates = {
        ticker: _latest_valid_date(ticker_frame, as_of=as_of)
        for ticker, ticker_frame in price_groups.items()
    }
    profile_through = max(through_dates.values(), default="")
    spy_through = through_dates.get("SPY", "")
    profile_current = _is_current(profile_through, as_of=as_of)
    spy_current = _is_current(spy_through, as_of=as_of)
    maximum_debt = float(
        (policy or DailyQueuePolicy()).maximum_debt_to_equity
        if policy is not None
        else config.value_rules.get("max_debt_to_equity_for_quality_value", 2.0)
    )
    resolved_policy = policy or DailyQueuePolicy(maximum_debt_to_equity=maximum_debt)
    cutoff = f"{as_of.isoformat()}T23:59:59+00:00"
    evidence: list[DailyQueueEvidence] = []
    for ticker in selected_tickers:
        readiness_row = _row_by_ticker(selected, ticker)
        indicator = indicator_rows.get(ticker)
        fundamental = _row_by_ticker(fundamental_frame, ticker)
        ticker_through = through_dates.get(ticker, "")
        price_provenance, price_rights, price_scope = _price_evidence_states(
            price_groups.get(ticker, pd.DataFrame()),
            price_groups.get("SPY", pd.DataFrame()),
            registry=rights_registry,
        )
        fundamental_provenance, fundamental_rights, fundamental_scope = (
            _fundamental_evidence_states(fundamental, registry=rights_registry)
        )
        valuation = build_valuation_regime(
            valuations_by_ticker.get(ticker, ()),
            ticker=ticker,
            metric="price_to_fcf_per_share",
            as_of=cutoff,
            commercial_mode=True,
            rights_registry=rights_registry,
        )
        evidence.append(
            DailyQueueEvidence(
                ticker=ticker,
                company_name=(
                    _text(readiness_row.get("name"))
                    or _text(readiness_row.get("company_name"))
                    or ticker
                )
                if readiness_row is not None
                else ticker,
                observation_through_date=ticker_through,
                momentum_ready=True,
                current_market_eligible=(
                    profile_current
                    and spy_current
                    and _is_current(ticker_through, as_of=as_of)
                ),
                price_provenance_eligible=price_provenance,
                price_rights_eligible=price_rights,
                price_field_scope_eligible=price_scope,
                close=_numeric(indicator.get("close")) if indicator is not None else None,
                sma_50=_numeric(indicator.get("sma_50")) if indicator is not None else None,
                sma_200=_numeric(indicator.get("sma_200")) if indicator is not None else None,
                return_3m=_numeric(indicator.get("return_3m")) if indicator is not None else None,
                return_6m=_numeric(indicator.get("return_6m")) if indicator is not None else None,
                relative_return_vs_spy=(
                    _numeric(indicator.get("relative_return_vs_spy"))
                    if indicator is not None
                    else None
                ),
                valuation_state=valuation.state,
                valuation_freshness_state=valuation.freshness_state,
                valuation_commercial_eligible=(
                    valuation.state == "ready"
                    and valuation.commercial_blocker_count == 0
                ),
                valuation_metric=valuation.metric,
                valuation_percentile=valuation.percentile_rank,
                free_cash_flow=(
                    _numeric(fundamental.get("free_cash_flow"))
                    if fundamental is not None
                    else None
                ),
                revenue_growth=(
                    _numeric(fundamental.get("revenue_growth"))
                    if fundamental is not None
                    else None
                ),
                debt_to_equity=(
                    _numeric(fundamental.get("debt_to_equity"))
                    if fundamental is not None
                    else None
                ),
                fundamentals_provenance_eligible=fundamental_provenance,
                fundamentals_rights_eligible=fundamental_rights,
                fundamentals_field_scope_eligible=fundamental_scope,
            )
        )
    result = evaluate_daily_queue(evidence, policy=resolved_policy)
    blocker_counts = Counter(
        blocker
        for item in result.withheld
        for blocker in item.blockers
    )
    return DailyQueueBuildStatus(
        result=result,
        considered_count=len(selected_tickers),
        readiness_row_count=len(readiness_frame),
        price_row_count=len(price_frame),
        valuation_observation_count=len(valuations),
        blocker_counts=tuple(sorted(blocker_counts.items())),
        message=(
            f"Evaluated {len(selected_tickers)} momentum-ready company record(s); "
            f"{len(result.eligible)} pass every daily queue gate."
        ),
    )


def build_daily_research_queue_from_files(
    *,
    project_root: Path | str,
    data_dir: Path | str,
    as_of: date,
    rights_registry_path: Path | str | None = None,
    policy: DailyQueuePolicy | None = None,
) -> DailyQueueBuildStatus:
    """Load one explicit local profile read-only and return fail-closed status."""

    root = Path(project_root)
    selected_data_dir = Path(data_dir)
    try:
        config = AppConfig.load(root / "config.yaml")
    except (OSError, UnicodeError, ValueError):
        config = AppConfig(raw={})
    try:
        registry = load_source_rights_registry(
            rights_registry_path or (root / "config" / "source_rights.yml")
        )
    except (OSError, UnicodeError, ValueError):
        registry = {}
    try:
        valuation_rows = load_valuation_observations(
            selected_data_dir / "historical_valuation_observations.csv"
        )
    except (OSError, UnicodeError, ValueError):
        valuation_rows = ()
    return build_daily_research_queue(
        readiness=_optional_csv(
            selected_data_dir / "reports" / "ticker_readiness_report.csv"
        ),
        prices=_optional_csv(selected_data_dir / "prices.csv"),
        fundamentals=_optional_csv(selected_data_dir / "fundamentals.csv"),
        universe=_optional_csv(selected_data_dir / "universe.csv"),
        theme_map=_optional_csv(selected_data_dir / "theme_map.csv"),
        valuation_observations=valuation_rows,
        config=config,
        rights_registry=registry,
        as_of=as_of,
        policy=policy,
    )
