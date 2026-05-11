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
