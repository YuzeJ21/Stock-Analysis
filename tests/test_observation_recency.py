from datetime import date
from pathlib import Path

from src.observation_recency import evaluate_observation_rows, load_observation_recency


def test_observation_recency_keeps_scopes_independent_and_excludes_bad_dates():
    result = evaluate_observation_rows(
        [
            {"ticker": "AVGO", "date": "2026-07-20"},
            {"ticker": "AVGO", "date": "2026-08-01"},
            {"ticker": "SPY", "date": "2026-07-19"},
            {"ticker": "QQQ", "date": "not-a-date"},
        ],
        selected_ticker="AVGO",
        as_of=date(2026, 7, 27),
    )

    assert (result.selected_ticker.state, result.selected_ticker.age_days) == ("current", 7)
    assert result.selected_ticker.excluded_date_count == 1
    assert result.benchmarks[0].state == "stale_review_only"
    assert result.benchmarks[1].state == "unavailable"
    assert result.profile_price_lane.through_date == "2026-07-20"


def test_observation_recency_uses_the_seven_day_policy_boundary():
    result = evaluate_observation_rows(
        [
            {"ticker": "AVGO", "date": "2026-07-20"},
            {"ticker": "SPY", "date": "2026-07-19"},
        ],
        selected_ticker="avgo",
        benchmark_tickers=("spy",),
        as_of=date(2026, 7, 27),
    )

    assert (result.selected_ticker.state, result.selected_ticker.age_days) == ("current", 7)
    assert (result.benchmarks[0].state, result.benchmarks[0].age_days) == ("stale_review_only", 8)


def test_missing_file_returns_unavailable_results_without_fallback(tmp_path: Path):
    prices_path = tmp_path / "missing-prices.csv"

    result = load_observation_recency(
        prices_path,
        selected_ticker="AVGO",
        as_of=date(2026, 7, 27),
    )

    assert result.source_path == str(prices_path)
    assert result.as_of == "2026-07-27"
    assert result.selected_ticker.state == "unavailable"
    assert result.profile_price_lane.state == "unavailable"
    assert [row.state for row in result.benchmarks] == ["unavailable", "unavailable"]


def test_missing_benchmark_does_not_change_selected_ticker_result():
    result = evaluate_observation_rows(
        [
            {"ticker": "avgo", "date": "2026-07-25"},
            {"ticker": "SPY", "date": "2026-07-26"},
        ],
        selected_ticker="AVGO",
        benchmark_tickers=("SPY", "QQQ"),
        as_of=date(2026, 7, 27),
    )

    assert result.selected_ticker.scope == "AVGO"
    assert (result.selected_ticker.through_date, result.selected_ticker.state) == ("2026-07-25", "current")
    assert [(row.scope, row.state) for row in result.benchmarks] == [
        ("SPY", "current"),
        ("QQQ", "unavailable"),
    ]


def test_rows_without_a_usable_ticker_are_excluded_from_every_scope():
    result = evaluate_observation_rows(
        [
            {"ticker": "", "date": "2026-07-27"},
            {"date": "2026-07-27"},
        ],
        selected_ticker="",
        benchmark_tickers=("",),
        as_of=date(2026, 7, 27),
    )

    assert result.selected_ticker.state == "unavailable"
    assert result.profile_price_lane.state == "unavailable"
    assert result.profile_price_lane.excluded_date_count == 2
    assert result.benchmarks[0].state == "unavailable"


def test_existing_profile_prices_are_stale_or_unavailable_without_writes():
    project_root = Path(__file__).resolve().parents[1]

    result = load_observation_recency(
        project_root / "data" / "prices.csv",
        selected_ticker="AVGO",
        as_of=date(2026, 7, 27),
    )

    assert result.selected_ticker.state in {"stale_review_only", "unavailable"}
    assert {row.scope: row.state for row in result.benchmarks}["SPY"] == "stale_review_only"
    assert {row.scope: row.state for row in result.benchmarks}["QQQ"] == "stale_review_only"
