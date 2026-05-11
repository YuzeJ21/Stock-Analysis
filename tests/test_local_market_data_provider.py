from pathlib import Path

import pandas as pd
import pytest

from src.providers.local_market_data import LocalCSVMarketDataProvider


def test_local_provider_returns_quote_for_known_ticker(tmp_path: Path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "prices.csv").write_text(
        "date,ticker,adj_close,volume\n"
        "2026-01-02,SPY,100,1000\n"
        "2026-01-03,SPY,101,1200\n",
        encoding="utf-8",
    )
    provider = LocalCSVMarketDataProvider(base_dir=tmp_path)

    quote = provider.get_quote("SPY")

    assert quote.ticker == "SPY"
    assert quote.price == 101.0
    assert quote.previous_close == 100.0
    assert quote.source.provider == "local:prices.csv"


def test_local_provider_handles_missing_ticker_gracefully(tmp_path: Path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "prices.csv").write_text(
        "date,ticker,adj_close,volume\n"
        "2026-01-02,SPY,100,1000\n",
        encoding="utf-8",
    )
    provider = LocalCSVMarketDataProvider(base_dir=tmp_path)

    with pytest.raises(LookupError, match="No local price rows were found for AAPL"):
        provider.get_quote("AAPL")


def test_local_provider_handles_sparse_csv_with_missing_optional_fields(tmp_path: Path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "prices.csv").write_text(
        "date,ticker,adj_close,volume\n"
        "2026-01-02,NVDA,900,2000\n",
        encoding="utf-8",
    )
    provider = LocalCSVMarketDataProvider(base_dir=tmp_path)

    quote = provider.get_quote("NVDA")
    history = provider.get_price_history("NVDA", period="1y", interval="1d")

    assert quote.open is None
    assert quote.day_high is None
    assert quote.day_low is None
    assert list(history.columns) == ["date", "open", "high", "low", "close", "volume"]


def test_local_provider_returns_short_history_without_fabricating_lookback(tmp_path: Path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "prices.csv").write_text(
        "date,ticker,adj_close,volume\n"
        "2026-05-01,QQQ,100,1000\n"
        "2026-05-02,QQQ,101,1000\n"
        "2026-05-03,QQQ,102,1000\n",
        encoding="utf-8",
    )
    provider = LocalCSVMarketDataProvider(base_dir=tmp_path)

    history = provider.get_price_history("QQQ", period="1y", interval="1d")

    assert len(history) == 3
    assert history["close"].iloc[-1] == 102


def test_local_provider_date_parsing_is_consistent(tmp_path: Path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "prices.csv").write_text(
        "Date,Ticker,Adj Close,Volume\n"
        "2026-01-02,SPY,100,1000\n"
        "2026/01/03,SPY,101,1001\n",
        encoding="utf-8",
    )
    provider = LocalCSVMarketDataProvider(base_dir=tmp_path)

    history = provider.get_price_history("SPY", period="1y", interval="1d")

    assert len(history) == 2
    assert pd.api.types.is_datetime64_any_dtype(history["date"])


def test_local_provider_loads_fundamentals_fixture_when_available(tmp_path: Path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "prices.csv").write_text(
        "date,ticker,adj_close,volume\n"
        "2026-01-02,NVDA,150,1000\n",
        encoding="utf-8",
    )
    (tmp_path / "data" / "fundamentals.csv").write_text(
        "ticker,revenue,eps,free_cash_flow,pe_ratio,profit_margin\n"
        "NVDA,1000,4.5,250,30,0.35\n",
        encoding="utf-8",
    )
    provider = LocalCSVMarketDataProvider(base_dir=tmp_path)

    financials = provider.get_financials("NVDA")

    assert financials.revenue == 1000.0
    assert financials.eps == 4.5
    assert financials.free_cash_flow == 250.0
    assert financials.trailing_pe == 30.0


def test_local_provider_loads_earnings_fixture_when_available(tmp_path: Path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "prices.csv").write_text(
        "date,ticker,adj_close,volume\n"
        "2026-01-02,NVDA,150,1000\n",
        encoding="utf-8",
    )
    (tmp_path / "data" / "earnings.csv").write_text(
        "ticker,next_earnings_date,last_earnings_date,eps_estimate,eps_actual,surprise_pct\n"
        "NVDA,2026-05-30,2026-02-25,1.2,1.3,0.08\n",
        encoding="utf-8",
    )
    provider = LocalCSVMarketDataProvider(base_dir=tmp_path)

    earnings = provider.get_earnings("NVDA")

    assert earnings.next_earnings_date == "2026-05-30"
    assert earnings.eps_estimate == 1.2
    assert earnings.surprise_pct == 0.08


def test_local_provider_loads_analyst_estimate_fixture_when_available(tmp_path: Path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "prices.csv").write_text(
        "date,ticker,adj_close,volume\n"
        "2026-01-02,NVDA,150,1000\n",
        encoding="utf-8",
    )
    (tmp_path / "data" / "analyst_estimates.csv").write_text(
        "ticker,current_quarter_eps,next_quarter_eps,target_mean_price,recommendation\n"
        "NVDA,1.2,1.4,220,hold\n",
        encoding="utf-8",
    )
    provider = LocalCSVMarketDataProvider(base_dir=tmp_path)

    estimates = provider.get_analyst_estimates("NVDA")

    assert estimates.current_quarter_eps == 1.2
    assert estimates.next_quarter_eps == 1.4
    assert estimates.target_mean_price == 220.0
    assert estimates.recommendation == "hold"


def test_local_provider_handles_missing_optional_dataset_files(tmp_path: Path):
    provider = LocalCSVMarketDataProvider(base_dir=tmp_path)

    financials = provider.get_financials("NVDA")
    earnings = provider.get_earnings("NVDA")
    estimates = provider.get_analyst_estimates("NVDA")

    assert financials.revenue is None
    assert "No local earnings dataset" in earnings.notes[0]
    assert "No local analyst-estimate dataset" in estimates.notes[0]


def test_local_provider_surfaces_existing_screener_context(tmp_path: Path):
    (tmp_path / "data").mkdir()
    (tmp_path / "outputs").mkdir()
    (tmp_path / "data" / "prices.csv").write_text(
        "date,ticker,adj_close,volume\n"
        "2026-01-02,NVDA,150,1000\n",
        encoding="utf-8",
    )
    (tmp_path / "outputs" / "final_watchlist.csv").write_text(
        "Ticker,FinalState,Reason\n"
        "NVDA,Watch,Fixture row\n",
        encoding="utf-8",
    )
    provider = LocalCSVMarketDataProvider(base_dir=tmp_path)

    context = provider.get_screener_context("NVDA")

    assert context["final_watchlist"]["finalstate"] == "Watch"
    assert context["final_watchlist"]["reason"] == "Fixture row"
