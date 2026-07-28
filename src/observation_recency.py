"""Read-only evaluation of local market-observation recency."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable, Mapping


CURRENT_MAX_AGE_DAYS = 7


@dataclass(frozen=True)
class ObservationRecency:
    scope: str
    through_date: str
    age_days: int | None
    state: str
    message: str
    excluded_date_count: int = 0


@dataclass(frozen=True)
class ObservationRecencySet:
    selected_ticker: ObservationRecency
    profile_price_lane: ObservationRecency
    benchmarks: tuple[ObservationRecency, ...]
    policy_days: int
    source_path: str
    as_of: str


def _parse_date(value: object) -> date | None:
    if not isinstance(value, str) or len(value) != 10 or value[4] != "-" or value[7] != "-":
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _result(scope: str, dates: list[date], excluded: int, as_of: date) -> ObservationRecency:
    if not dates:
        return ObservationRecency(
            scope,
            "",
            None,
            "unavailable",
            "No valid observation is available on or before the review date.",
            excluded,
        )

    latest = max(dates)
    age_days = (as_of - latest).days
    state = "current" if age_days <= CURRENT_MAX_AGE_DAYS else "stale_review_only"
    message = (
        "Observation is within the seven-calendar-day local review policy."
        if state == "current"
        else "Historical context only; do not use for a current-market interpretation."
    )
    return ObservationRecency(scope, latest.isoformat(), age_days, state, message, excluded)


def _normalize_ticker(value: object) -> str:
    return value.strip().upper() if isinstance(value, str) else ""


def evaluate_observation_rows(
    rows: Iterable[Mapping[str, object]],
    *,
    selected_ticker: str,
    benchmark_tickers: tuple[str, ...] = ("SPY", "QQQ"),
    as_of: date,
    source_path: str = "",
) -> ObservationRecencySet:
    """Evaluate supplied CSV-shaped rows without reading or writing external data."""
    selected_scope = _normalize_ticker(selected_ticker)
    benchmark_scopes = tuple(_normalize_ticker(ticker) for ticker in benchmark_tickers)
    selected_dates: list[date] = []
    selected_excluded = 0
    profile_dates: list[date] = []
    profile_excluded = 0
    benchmark_dates = {scope: [] for scope in benchmark_scopes}
    benchmark_excluded = {scope: 0 for scope in benchmark_scopes}

    for row in rows:
        ticker = _normalize_ticker(row.get("ticker"))
        observation_date = _parse_date(row.get("date"))

        if not ticker:
            profile_excluded += 1
            continue

        is_valid = observation_date is not None and observation_date <= as_of

        if is_valid:
            profile_dates.append(observation_date)
        else:
            profile_excluded += 1

        if ticker == selected_scope:
            if is_valid:
                selected_dates.append(observation_date)
            else:
                selected_excluded += 1

        if ticker in benchmark_dates:
            if is_valid:
                benchmark_dates[ticker].append(observation_date)
            else:
                benchmark_excluded[ticker] += 1

    return ObservationRecencySet(
        selected_ticker=_result(selected_scope, selected_dates, selected_excluded, as_of),
        profile_price_lane=_result("profile_price_lane", profile_dates, profile_excluded, as_of),
        benchmarks=tuple(
            _result(scope, benchmark_dates[scope], benchmark_excluded[scope], as_of)
            for scope in benchmark_scopes
        ),
        policy_days=CURRENT_MAX_AGE_DAYS,
        source_path=source_path,
        as_of=as_of.isoformat(),
    )


def load_observation_recency(
    prices_path: Path,
    *,
    selected_ticker: str,
    benchmark_tickers: tuple[str, ...] = ("SPY", "QQQ"),
    as_of: date,
) -> ObservationRecencySet:
    """Load one selected CSV read-only, failing closed when it cannot be read."""
    source_path = str(prices_path)
    try:
        with prices_path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
    except (OSError, UnicodeError, csv.Error):
        rows = []

    return evaluate_observation_rows(
        rows,
        selected_ticker=selected_ticker,
        benchmark_tickers=benchmark_tickers,
        as_of=as_of,
        source_path=source_path,
    )
