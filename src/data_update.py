from __future__ import annotations

from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path
from typing import Protocol
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

import pandas as pd

from src.config import AppConfig


PRICE_COLUMNS = ["date", "ticker", "open", "high", "low", "close", "adj_close", "volume"]


def _normalize_columns(columns: list[str]) -> list[str]:
    return [
        column.strip()
        .replace("%", "pct")
        .replace("/", "_")
        .replace(" ", "_")
        .replace("-", "_")
        .lower()
        for column in columns
    ]


def _normalize_ticker_series(series: pd.Series) -> pd.Series:
    return series.astype("string").str.upper().str.strip()


def _stooq_symbol(ticker: str) -> str:
    return f"{ticker.lower()}.us"


class PriceHistorySource(Protocol):
    def fetch_history(self, ticker: str) -> tuple[pd.DataFrame, list[str]]:
        ...


@dataclass
class PriceUpdateResult:
    path: Path
    tickers_requested: list[str]
    tickers_updated: list[str] = field(default_factory=list)
    tickers_missing: list[str] = field(default_factory=list)
    rows_written: int = 0
    warnings: list[str] = field(default_factory=list)


class StooqDailyPriceSource:
    def __init__(self, base_url: str = "https://stooq.com/q/d/l/") -> None:
        self.base_url = base_url

    def fetch_history(self, ticker: str) -> tuple[pd.DataFrame, list[str]]:
        symbol = _stooq_symbol(ticker)
        url = f"{self.base_url}?{urlencode({'s': symbol, 'i': 'd'})}"
        try:
            with urlopen(url, timeout=20) as response:
                payload = response.read().decode("utf-8")
        except URLError as exc:
            return pd.DataFrame(columns=PRICE_COLUMNS), [f"{ticker}: update failed from Stooq ({exc})"]

        if not payload.strip() or "No data" in payload:
            return pd.DataFrame(columns=PRICE_COLUMNS), [f"{ticker}: free daily data source returned no rows."]

        frame = pd.read_csv(StringIO(payload))
        frame.columns = _normalize_columns(list(frame.columns))
        required = {"date", "open", "high", "low", "close", "volume"}
        missing = required - set(frame.columns)
        if missing:
            return pd.DataFrame(columns=PRICE_COLUMNS), [f"{ticker}: source response is missing columns {sorted(missing)}."]

        frame["date"] = pd.to_datetime(frame["date"], errors="coerce", format="mixed")
        frame = frame.loc[frame["date"].notna()].copy()
        if frame.empty:
            return pd.DataFrame(columns=PRICE_COLUMNS), [f"{ticker}: source rows had no valid dates."]

        for numeric_column in ("open", "high", "low", "close", "volume"):
            frame[numeric_column] = pd.to_numeric(frame[numeric_column], errors="coerce")
        frame = frame.loc[frame["close"].notna() & frame["close"].gt(0) & frame["volume"].notna() & frame["volume"].ge(0)].copy()
        if frame.empty:
            return pd.DataFrame(columns=PRICE_COLUMNS), [f"{ticker}: source rows were invalid after normalization."]

        frame["ticker"] = ticker.upper()
        frame["adj_close"] = frame["close"]
        return frame[PRICE_COLUMNS].copy(), []


def _read_csv_if_present(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    frame = pd.read_csv(path)
    frame.columns = _normalize_columns(list(frame.columns))
    return frame


def load_update_tickers(base_dir: Path, config: AppConfig | None = None) -> list[str]:
    config = config or AppConfig.load(base_dir / "config.yaml")
    universe = _read_csv_if_present(base_dir / "data" / "universe.csv")
    holdings = _read_csv_if_present(base_dir / "data" / "holdings.csv")
    theme_map = _read_csv_if_present(base_dir / "data" / "theme_map.csv")

    tickers: set[str] = set()
    if "ticker" in universe.columns:
        tickers.update(_normalize_ticker_series(universe["ticker"]).dropna().tolist())
    if "ticker" in holdings.columns:
        tickers.update(_normalize_ticker_series(holdings["ticker"]).dropna().tolist())
    if "sector_etf" in universe.columns:
        tickers.update(_normalize_ticker_series(universe["sector_etf"]).dropna().tolist())
    if "etf" in theme_map.columns:
        tickers.update(_normalize_ticker_series(theme_map["etf"]).dropna().tolist())

    for benchmark_group in config.benchmarks.values():
        tickers.update(str(ticker).upper().strip() for ticker in benchmark_group if str(ticker).strip())
    return sorted(ticker for ticker in tickers if ticker)


def _load_existing_prices(path: Path) -> pd.DataFrame:
    frame = _read_csv_if_present(path)
    if frame.empty:
        return pd.DataFrame(columns=PRICE_COLUMNS)

    if "adj_close" in frame.columns and "close" not in frame.columns:
        frame["close"] = frame["adj_close"]
    if "close" in frame.columns and "adj_close" not in frame.columns:
        frame["adj_close"] = frame["close"]
    for optional_column in ("open", "high", "low"):
        if optional_column not in frame.columns:
            frame[optional_column] = pd.NA

    if "ticker" in frame.columns:
        frame["ticker"] = _normalize_ticker_series(frame["ticker"])
    if "date" in frame.columns:
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce", format="mixed")
    for numeric_column in ("open", "high", "low", "close", "adj_close", "volume"):
        if numeric_column in frame.columns:
            frame[numeric_column] = pd.to_numeric(frame[numeric_column], errors="coerce")

    frame = frame.loc[frame.get("date", pd.Series(dtype="datetime64[ns]")).notna()].copy()
    if frame.empty:
        return pd.DataFrame(columns=PRICE_COLUMNS)
    return frame[PRICE_COLUMNS].copy()


def update_local_price_data(
    base_dir: Path | None = None,
    source: PriceHistorySource | None = None,
    tickers: list[str] | None = None,
) -> PriceUpdateResult:
    base_dir = base_dir or Path(__file__).resolve().parent.parent
    config = AppConfig.load(base_dir / "config.yaml")
    prices_path = base_dir / "data" / "prices.csv"
    source = source or StooqDailyPriceSource()
    tickers = tickers or load_update_tickers(base_dir, config)

    existing = _load_existing_prices(prices_path)
    fetched_frames: list[pd.DataFrame] = []
    warnings: list[str] = []
    updated: list[str] = []
    missing: list[str] = []

    for ticker in tickers:
        frame, fetch_warnings = source.fetch_history(ticker)
        warnings.extend(fetch_warnings)
        if frame.empty:
            missing.append(ticker)
            continue
        fetched_frames.append(frame)
        updated.append(ticker)

    if not fetched_frames:
        return PriceUpdateResult(
            path=prices_path,
            tickers_requested=tickers,
            tickers_updated=[],
            tickers_missing=missing,
            rows_written=len(existing),
            warnings=warnings + ["No remote price rows were added; kept the existing local CSV fallback."],
        )

    combined = pd.concat([existing, *fetched_frames], ignore_index=True)
    combined = combined.drop_duplicates(subset=["date", "ticker"], keep="last").sort_values(["ticker", "date"]).reset_index(drop=True)
    combined.to_csv(prices_path, index=False)

    return PriceUpdateResult(
        path=prices_path,
        tickers_requested=tickers,
        tickers_updated=updated,
        tickers_missing=missing,
        rows_written=len(combined),
        warnings=warnings,
    )


def main() -> None:
    result = update_local_price_data()
    print(f"Updated local price file: {result.path}")
    print(f"Tickers requested: {len(result.tickers_requested)}")
    print(f"Tickers updated: {len(result.tickers_updated)}")
    print(f"Rows written: {result.rows_written}")
    if result.tickers_missing:
        print("Tickers without remote rows:")
        for ticker in result.tickers_missing:
            print(f"- {ticker}")
    if result.warnings:
        print("Warnings:")
        for warning in result.warnings:
            print(f"- {warning}")


if __name__ == "__main__":
    main()
