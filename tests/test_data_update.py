from pathlib import Path

import pandas as pd

from src.data_update import load_update_tickers, update_local_price_data


class FakePriceSource:
    def __init__(self, payloads: dict[str, pd.DataFrame | None]) -> None:
        self.payloads = payloads

    def fetch_history(self, ticker: str) -> tuple[pd.DataFrame, list[str]]:
        payload = self.payloads.get(ticker)
        if payload is None:
            return pd.DataFrame(), [f"{ticker}: source unavailable"]
        return payload.copy(), []


def test_load_update_tickers_collects_universe_holdings_themes_and_benchmarks(tmp_path: Path):
    (tmp_path / "data").mkdir()
    (tmp_path / "config.yaml").write_text(Path("config.yaml").read_text(), encoding="utf-8")
    (tmp_path / "data" / "universe.csv").write_text(
        "Ticker,Theme,SectorETF,DefaultPurpose,MarketCapBucket\n"
        "NVDA,AI Semiconductors,SMH,Momentum Leader,Large\n",
        encoding="utf-8",
    )
    (tmp_path / "data" / "holdings.csv").write_text(
        "Ticker,PrimaryPurpose\n"
        "META,Core Compounder\n",
        encoding="utf-8",
    )
    (tmp_path / "data" / "theme_map.csv").write_text(
        "Theme,ETF,Description\n"
        "Fintech,ARKF,Financial technology\n",
        encoding="utf-8",
    )

    tickers = load_update_tickers(tmp_path)

    assert {"NVDA", "META", "SMH", "ARKF", "SPY", "QQQ"}.issubset(set(tickers))


def test_update_local_price_data_merges_fetched_rows_into_existing_csv(tmp_path: Path):
    (tmp_path / "data").mkdir()
    (tmp_path / "config.yaml").write_text(Path("config.yaml").read_text(), encoding="utf-8")
    (tmp_path / "data" / "prices.csv").write_text(
        "date,ticker,adj_close,volume\n"
        "2026-01-02,SPY,100,1000\n",
        encoding="utf-8",
    )

    source = FakePriceSource(
        {
            "SPY": pd.DataFrame(
                [
                    {
                        "date": pd.Timestamp("2026-01-02"),
                        "ticker": "SPY",
                        "open": 99.0,
                        "high": 101.0,
                        "low": 98.0,
                        "close": 100.0,
                        "adj_close": 100.0,
                        "volume": 1000,
                    },
                    {
                        "date": pd.Timestamp("2026-01-03"),
                        "ticker": "SPY",
                        "open": 100.0,
                        "high": 102.0,
                        "low": 99.0,
                        "close": 101.0,
                        "adj_close": 101.0,
                        "volume": 1100,
                    },
                ]
            ),
            "QQQ": pd.DataFrame(
                [
                    {
                        "date": pd.Timestamp("2026-01-03"),
                        "ticker": "QQQ",
                        "open": 200.0,
                        "high": 202.0,
                        "low": 199.0,
                        "close": 201.0,
                        "adj_close": 201.0,
                        "volume": 2100,
                    }
                ]
            ),
        }
    )

    result = update_local_price_data(tmp_path, source=source, tickers=["SPY", "QQQ"])

    updated = pd.read_csv(result.path)
    assert result.tickers_updated == ["SPY", "QQQ"]
    assert result.rows_written == 3
    assert list(updated.columns) == ["date", "ticker", "open", "high", "low", "close", "adj_close", "volume"]
    assert list(updated["ticker"]) == ["QQQ", "SPY", "SPY"]


def test_update_local_price_data_keeps_existing_csv_when_remote_fetch_returns_nothing(tmp_path: Path):
    (tmp_path / "data").mkdir()
    (tmp_path / "config.yaml").write_text(Path("config.yaml").read_text(), encoding="utf-8")
    (tmp_path / "data" / "prices.csv").write_text(
        "date,ticker,adj_close,volume\n"
        "2026-01-02,SPY,100,1000\n",
        encoding="utf-8",
    )

    source = FakePriceSource({"SPY": None})
    result = update_local_price_data(tmp_path, source=source, tickers=["SPY"])

    preserved = pd.read_csv(result.path)
    assert result.tickers_updated == []
    assert result.tickers_missing == ["SPY"]
    assert any("kept the existing local CSV fallback" in warning for warning in result.warnings)
    assert len(preserved) == 1
    assert preserved.iloc[0]["ticker"] == "SPY"
