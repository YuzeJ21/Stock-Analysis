from __future__ import annotations

import json
import importlib
import os
import re
import shutil
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from time import sleep
from typing import Any, Callable, Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

from src.commercial_source_rights import (
    SourceRights,
    commercial_eligibility,
    commercial_mode_enabled,
    load_source_rights_registry,
    review_commercial_field_scope,
)
from src.config import AppConfig
from src.paths import format_path_context, resolve_data_dir, resolve_outputs_dir, resolve_project_root
from src.price_lineage_temporal import review_daily_price_retrieval
from src.provider_env import load_provider_environment
from src.providers.alternative_fundamentals import ALPHA_VANTAGE_API_KEY_ENV, FMP_API_KEY_ENV, FINNHUB_API_KEY_ENV


PRICE_COLUMNS = ["date", "ticker", "open", "high", "low", "close", "adj_close", "volume"]
PRICE_IMPORT_REQUIRED_COLUMNS = ["date", "ticker", "open", "high", "low", "close", "volume"]
PRICE_IMPORT_OPTIONAL_COLUMNS = [
    "adjusted_close",
    "adj_close",
    "source",
    "source_ref",
    "retrieved_at",
    "as_of_date",
    "notes",
]
PRICE_IMPORT_OUTPUT_COLUMNS = [
    "date",
    "ticker",
    "open",
    "high",
    "low",
    "close",
    "adj_close",
    "volume",
    "source",
    "source_ref",
    "retrieved_at",
    "as_of_date",
    "notes",
]
PRICE_STATUS_COLUMNS = [
    "run_timestamp",
    "ticker",
    "requested_start",
    "requested_end",
    "provider",
    "status",
    "rows_fetched",
    "rows_merged",
    "error_category",
    "error_message",
    "fallback_used",
    "recommended_action",
    "focus_command",
    "example_command",
    "target_file",
]
MIN_PRICE_READY_ROWS = 5
IBKR_HOST_ENV = "IBKR_HOST"
IBKR_PORT_ENV = "IBKR_PORT"
IBKR_CLIENT_ID_ENV = "IBKR_CLIENT_ID"
DEFAULT_IBKR_HOST = "127.0.0.1"
DEFAULT_IBKR_PORT = 7497
DEFAULT_IBKR_CLIENT_ID = 27


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


def _ensure_price_aliases(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = frame.copy()
    if "adjusted_close" in normalized.columns and "adj_close" not in normalized.columns:
        normalized["adj_close"] = normalized["adjusted_close"]
    if "adj_close" in normalized.columns and "close" not in normalized.columns:
        normalized["close"] = normalized["adj_close"]
    if "close" in normalized.columns and "adj_close" not in normalized.columns:
        normalized["adj_close"] = normalized["close"]
    return normalized


def _normalize_ticker_series(series: pd.Series) -> pd.Series:
    return series.astype("string").str.upper().str.strip()


def _stooq_symbol(ticker: str) -> str:
    return f"{ticker.lower()}.us"


def _yahoo_chart_symbol(ticker: str) -> str:
    return str(ticker or "").upper().strip().replace(".", "-")


def _coerce_int(value: int | str | None, default: int) -> int:
    try:
        if value is None or str(value).strip() == "":
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _ibkr_auto_configured() -> bool:
    return all(
        str(os.environ.get(key, "")).strip()
        for key in (IBKR_HOST_ENV, IBKR_PORT_ENV, IBKR_CLIENT_ID_ENV)
    )


def _ibkr_bars_to_price_frame(ticker: str, bars: Any) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for bar in list(bars or []):
        rows.append(
            {
                "date": getattr(bar, "date", None),
                "ticker": ticker,
                "open": getattr(bar, "open", None),
                "high": getattr(bar, "high", None),
                "low": getattr(bar, "low", None),
                "close": getattr(bar, "close", None),
                "adj_close": getattr(bar, "close", None),
                "volume": getattr(bar, "volume", None),
            }
        )
    frame = pd.DataFrame(rows, columns=PRICE_COLUMNS)
    if frame.empty:
        return pd.DataFrame(columns=PRICE_COLUMNS)
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce", format="mixed")
    for numeric_column in ("open", "high", "low", "close", "adj_close", "volume"):
        frame[numeric_column] = pd.to_numeric(frame[numeric_column], errors="coerce")
    frame = frame.loc[
        frame["date"].notna()
        & frame["close"].notna()
        & frame["close"].gt(0)
        & frame["volume"].notna()
        & frame["volume"].ge(0)
    ].copy()
    if frame.empty:
        return pd.DataFrame(columns=PRICE_COLUMNS)
    frame["ticker"] = ticker
    frame = frame.sort_values("date")
    return frame[PRICE_COLUMNS].copy()


class PriceHistorySource(Protocol):
    source_id: str

    def fetch_history(self, ticker: str) -> tuple[pd.DataFrame, list[str]]:
        ...


@dataclass
class PriceUpdateResult:
    path: Path
    tickers_requested: list[str]
    tickers_updated: list[str] = field(default_factory=list)
    tickers_missing: list[str] = field(default_factory=list)
    tickers_skipped_fresh: list[str] = field(default_factory=list)
    rows_written: int = 0
    chunks_processed: int = 0
    warnings: list[str] = field(default_factory=list)
    status_path: Path | None = None
    status_rows: list[dict[str, Any]] = field(default_factory=list)


class StooqDailyPriceSource:
    source_id = "stooq"

    def __init__(
        self,
        base_url: str = "https://stooq.com/q/d/l/",
        api_key: str | None = None,
        opener: Callable[..., Any] = urlopen,
    ) -> None:
        self.base_url = base_url
        self.api_key = api_key if api_key is not None else os.environ.get("STOOQ_API_KEY", "")
        self.opener = opener

    def fetch_history(self, ticker: str) -> tuple[pd.DataFrame, list[str]]:
        symbol = _stooq_symbol(ticker)
        params = {"s": symbol, "i": "d"}
        if self.api_key:
            params["apikey"] = self.api_key
        url = f"{self.base_url}?{urlencode(params)}"
        try:
            with self.opener(url, timeout=20) as response:
                payload = response.read().decode("utf-8")
        except URLError as exc:
            return pd.DataFrame(columns=PRICE_COLUMNS), [f"{ticker}: update failed from Stooq ({exc})"]

        if not payload.strip() or "No data" in payload:
            return pd.DataFrame(columns=PRICE_COLUMNS), [f"{ticker}: free daily data source returned no rows."]
        first_line = payload.lstrip().splitlines()[0].strip().lower()
        if "," not in first_line or "get your apikey" in payload.lower():
            return (
                pd.DataFrame(columns=PRICE_COLUMNS),
                [
                    f"{ticker}: Stooq CSV download requires an API key in this environment. "
                    "Set STOOQ_API_KEY or place verified CSVs in data/staged/prices/ and run make import-prices."
                ],
            )

        try:
            frame = pd.read_csv(StringIO(payload))
        except pd.errors.ParserError as exc:
            return pd.DataFrame(columns=PRICE_COLUMNS), [f"{ticker}: source response could not be parsed as CSV ({exc})"]
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


class YahooChartDailyPriceSource:
    """Unofficial research-grade daily OHLCV source using Yahoo's chart endpoint."""

    source_id = "yahoo"

    def __init__(
        self,
        base_url: str = "https://query1.finance.yahoo.com/v8/finance/chart",
        range_days: int = 900,
        opener: Callable[..., Any] = urlopen,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.range_days = range_days
        self.opener = opener

    def fetch_history(self, ticker: str) -> tuple[pd.DataFrame, list[str]]:
        ticker = ticker.upper().strip()
        symbol = _yahoo_chart_symbol(ticker)
        period2 = int(time.time())
        period1 = period2 - max(self.range_days, 1) * 86_400
        params = {
            "period1": period1,
            "period2": period2,
            "interval": "1d",
            "events": "history",
            "includeAdjustedClose": "true",
        }
        url = f"{self.base_url}/{symbol}?{urlencode(params)}"
        request = Request(url, headers={"User-Agent": "stock-research-command-center/1.0"})
        try:
            with self.opener(request, timeout=20) as response:
                payload = response.read().decode("utf-8")
        except (HTTPError, URLError) as exc:
            suffix = f" for {symbol}" if symbol != ticker else ""
            return pd.DataFrame(columns=PRICE_COLUMNS), [f"{ticker}: update failed from Yahoo chart endpoint{suffix} ({exc})"]

        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError as exc:
            return pd.DataFrame(columns=PRICE_COLUMNS), [f"{ticker}: Yahoo chart response could not be parsed as JSON ({exc})"]

        chart = parsed.get("chart", {}) if isinstance(parsed, dict) else {}
        error = chart.get("error")
        if error:
            description = error.get("description") if isinstance(error, dict) else str(error)
            suffix = f" for {symbol}" if symbol != ticker else ""
            return pd.DataFrame(columns=PRICE_COLUMNS), [f"{ticker}: Yahoo chart endpoint returned an error{suffix} ({description})"]
        results = chart.get("result") or []
        if not results:
            suffix = f" for {symbol}" if symbol != ticker else ""
            return pd.DataFrame(columns=PRICE_COLUMNS), [f"{ticker}: Yahoo chart endpoint returned no rows{suffix}."]

        result = results[0]
        timestamps = result.get("timestamp") or []
        indicators = result.get("indicators", {}) or {}
        quotes = indicators.get("quote") or []
        if not timestamps or not quotes:
            suffix = f" for {symbol}" if symbol != ticker else ""
            return pd.DataFrame(columns=PRICE_COLUMNS), [f"{ticker}: Yahoo chart endpoint returned no OHLCV rows{suffix}."]
        quote = quotes[0]
        adjclose_rows = indicators.get("adjclose") or []
        adjclose = adjclose_rows[0].get("adjclose", []) if adjclose_rows else []
        dates = pd.to_datetime(timestamps, unit="s", utc=True, errors="coerce").tz_convert(None).normalize()
        frame = pd.DataFrame(
            {
                "date": dates,
                "ticker": ticker,
                "open": quote.get("open", []),
                "high": quote.get("high", []),
                "low": quote.get("low", []),
                "close": quote.get("close", []),
                "adj_close": adjclose if adjclose and len(adjclose) == len(timestamps) else quote.get("close", []),
                "volume": quote.get("volume", []),
            }
        )
        for numeric_column in ("open", "high", "low", "close", "adj_close", "volume"):
            frame[numeric_column] = pd.to_numeric(frame[numeric_column], errors="coerce")
        frame = frame.loc[
            frame["date"].notna()
            & frame["close"].notna()
            & frame["close"].gt(0)
            & frame["volume"].notna()
            & frame["volume"].ge(0)
        ].copy()
        if frame.empty:
            return pd.DataFrame(columns=PRICE_COLUMNS), [f"{ticker}: Yahoo chart rows were invalid after normalization."]
        alias_note = f" via provider symbol {symbol}" if symbol != ticker else ""
        return frame[PRICE_COLUMNS].copy(), [
            f"{ticker}: prices refreshed from unofficial Yahoo chart endpoint{alias_note}; treat as research-grade and verify if used for decisions."
        ]


class FMPDailyPriceSource:
    """Research-grade daily OHLCV fallback using FMP's historical price endpoint."""

    source_id = "fmp"

    def __init__(
        self,
        base_url: str = "https://financialmodelingprep.com/api/v3/historical-price-full",
        api_key: str | None = None,
        range_days: int = 900,
        opener: Callable[..., Any] = urlopen,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key if api_key is not None else os.environ.get(FMP_API_KEY_ENV, "")
        self.range_days = range_days
        self.opener = opener

    def fetch_history(self, ticker: str) -> tuple[pd.DataFrame, list[str]]:
        ticker = ticker.upper().strip()
        resolved_key = str(self.api_key or "").strip()
        if not resolved_key:
            return pd.DataFrame(columns=PRICE_COLUMNS), [f"{ticker}: {FMP_API_KEY_ENV} is not configured for FMP price fallback."]

        symbol = _yahoo_chart_symbol(ticker)
        params = {"timeseries": max(self.range_days, 1), "apikey": resolved_key}
        url = f"{self.base_url}/{symbol}?{urlencode(params)}"
        request = Request(url, headers={"Accept": "application/json", "User-Agent": "stock-research-command-center/1.0"})
        try:
            with self.opener(request, timeout=20) as response:
                payload = response.read().decode("utf-8")
        except (HTTPError, URLError) as exc:
            suffix = f" for {symbol}" if symbol != ticker else ""
            return pd.DataFrame(columns=PRICE_COLUMNS), [f"{ticker}: update failed from FMP historical price endpoint{suffix} ({exc})"]

        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError as exc:
            return pd.DataFrame(columns=PRICE_COLUMNS), [f"{ticker}: FMP historical price response could not be parsed as JSON ({exc})"]

        historical = parsed.get("historical") if isinstance(parsed, dict) else None
        if not isinstance(historical, list) or not historical:
            suffix = f" for {symbol}" if symbol != ticker else ""
            return pd.DataFrame(columns=PRICE_COLUMNS), [f"{ticker}: FMP historical price endpoint returned no rows{suffix}."]

        frame = pd.DataFrame(historical)
        frame.columns = _normalize_columns(list(frame.columns))
        if "adjclose" in frame.columns and "adj_close" not in frame.columns:
            frame["adj_close"] = frame["adjclose"]
        frame = _ensure_price_aliases(frame)
        required = {"date", "open", "high", "low", "close", "volume"}
        missing = required - set(frame.columns)
        if missing:
            return pd.DataFrame(columns=PRICE_COLUMNS), [f"{ticker}: FMP historical price response is missing columns {sorted(missing)}."]

        frame["date"] = pd.to_datetime(frame["date"], errors="coerce", format="mixed")
        for numeric_column in ("open", "high", "low", "close", "adj_close", "volume"):
            frame[numeric_column] = pd.to_numeric(frame[numeric_column], errors="coerce")
        frame = frame.loc[
            frame["date"].notna()
            & frame["close"].notna()
            & frame["close"].gt(0)
            & frame["volume"].notna()
            & frame["volume"].ge(0)
        ].copy()
        if frame.empty:
            return pd.DataFrame(columns=PRICE_COLUMNS), [f"{ticker}: FMP historical price rows were invalid after normalization."]

        frame["ticker"] = ticker
        frame = frame.sort_values("date")
        return frame[PRICE_COLUMNS].copy(), [
            f"{ticker}: prices refreshed from FMP historical price endpoint; treat as research-grade and verify if used for decisions."
        ]


class AlphaVantageDailyPriceSource:
    """Research-grade daily OHLCV fallback using Alpha Vantage daily adjusted prices."""

    source_id = "alpha_vantage"

    def __init__(
        self,
        base_url: str = "https://www.alphavantage.co/query",
        api_key: str | None = None,
        opener: Callable[..., Any] = urlopen,
    ) -> None:
        self.base_url = base_url
        self.api_key = api_key if api_key is not None else os.environ.get(ALPHA_VANTAGE_API_KEY_ENV, "")
        self.opener = opener

    def fetch_history(self, ticker: str) -> tuple[pd.DataFrame, list[str]]:
        ticker = ticker.upper().strip()
        resolved_key = str(self.api_key or "").strip()
        if not resolved_key:
            return (
                pd.DataFrame(columns=PRICE_COLUMNS),
                [f"{ticker}: {ALPHA_VANTAGE_API_KEY_ENV} is not configured for Alpha Vantage price fallback."],
            )

        symbol = _yahoo_chart_symbol(ticker)
        params = {
            "function": "TIME_SERIES_DAILY_ADJUSTED",
            "symbol": symbol,
            "outputsize": "compact",
            "apikey": resolved_key,
        }
        url = f"{self.base_url}?{urlencode(params)}"
        request = Request(url, headers={"Accept": "application/json", "User-Agent": "stock-research-command-center/1.0"})
        try:
            with self.opener(request, timeout=20) as response:
                payload = response.read().decode("utf-8")
        except (HTTPError, URLError) as exc:
            suffix = f" for {symbol}" if symbol != ticker else ""
            return pd.DataFrame(columns=PRICE_COLUMNS), [f"{ticker}: update failed from Alpha Vantage daily adjusted endpoint{suffix} ({exc})"]

        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError as exc:
            return pd.DataFrame(columns=PRICE_COLUMNS), [f"{ticker}: Alpha Vantage daily adjusted response could not be parsed as JSON ({exc})"]

        if not isinstance(parsed, dict) or "Note" in parsed or "Information" in parsed:
            return pd.DataFrame(columns=PRICE_COLUMNS), [f"{ticker}: Alpha Vantage daily adjusted endpoint returned no usable rows."]
        series = parsed.get("Time Series (Daily)")
        if not isinstance(series, dict) or not series:
            suffix = f" for {symbol}" if symbol != ticker else ""
            return pd.DataFrame(columns=PRICE_COLUMNS), [f"{ticker}: Alpha Vantage daily adjusted endpoint returned no rows{suffix}."]

        rows = []
        for date_text, values in series.items():
            if not isinstance(values, dict):
                continue
            rows.append(
                {
                    "date": date_text,
                    "ticker": ticker,
                    "open": values.get("1. open"),
                    "high": values.get("2. high"),
                    "low": values.get("3. low"),
                    "close": values.get("4. close"),
                    "adj_close": values.get("5. adjusted close") or values.get("4. close"),
                    "volume": values.get("6. volume"),
                }
            )
        frame = pd.DataFrame(rows, columns=PRICE_COLUMNS)
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce", format="mixed")
        for numeric_column in ("open", "high", "low", "close", "adj_close", "volume"):
            frame[numeric_column] = pd.to_numeric(frame[numeric_column], errors="coerce")
        frame = frame.loc[
            frame["date"].notna()
            & frame["close"].notna()
            & frame["close"].gt(0)
            & frame["volume"].notna()
            & frame["volume"].ge(0)
        ].copy()
        if frame.empty:
            return pd.DataFrame(columns=PRICE_COLUMNS), [f"{ticker}: Alpha Vantage daily adjusted rows were invalid after normalization."]

        frame = frame.sort_values("date")
        return frame[PRICE_COLUMNS].copy(), [
            f"{ticker}: prices refreshed from Alpha Vantage daily adjusted endpoint; treat as research-grade and verify if used for decisions."
        ]


class FinnhubDailyPriceSource:
    """Research-grade daily OHLCV fallback using Finnhub's stock candle endpoint."""

    source_id = "finnhub"

    def __init__(
        self,
        base_url: str = "https://finnhub.io/api/v1/stock/candle",
        api_key: str | None = None,
        range_days: int = 900,
        opener: Callable[..., Any] = urlopen,
    ) -> None:
        self.base_url = base_url
        self.api_key = api_key if api_key is not None else os.environ.get(FINNHUB_API_KEY_ENV, "")
        self.range_days = range_days
        self.opener = opener

    def fetch_history(self, ticker: str) -> tuple[pd.DataFrame, list[str]]:
        ticker = ticker.upper().strip()
        resolved_key = str(self.api_key or "").strip()
        if not resolved_key:
            return pd.DataFrame(columns=PRICE_COLUMNS), [f"{ticker}: {FINNHUB_API_KEY_ENV} is not configured for Finnhub price fallback."]

        period2 = int(time.time())
        period1 = period2 - max(self.range_days, 1) * 86_400
        params = {
            "symbol": ticker,
            "resolution": "D",
            "from": period1,
            "to": period2,
            "token": resolved_key,
        }
        url = f"{self.base_url}?{urlencode(params)}"
        request = Request(url, headers={"Accept": "application/json", "User-Agent": "stock-research-command-center/1.0"})
        try:
            with self.opener(request, timeout=20) as response:
                payload = response.read().decode("utf-8")
        except (HTTPError, URLError) as exc:
            return pd.DataFrame(columns=PRICE_COLUMNS), [f"{ticker}: update failed from Finnhub daily candle endpoint ({exc})"]

        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError as exc:
            return pd.DataFrame(columns=PRICE_COLUMNS), [f"{ticker}: Finnhub daily candle response could not be parsed as JSON ({exc})"]

        if not isinstance(parsed, dict):
            return pd.DataFrame(columns=PRICE_COLUMNS), [f"{ticker}: Finnhub daily candle endpoint returned an invalid payload."]
        status = str(parsed.get("s", "")).strip().lower()
        if status != "ok":
            detail = str(parsed.get("error") or parsed.get("s") or "no rows").strip()
            return pd.DataFrame(columns=PRICE_COLUMNS), [f"{ticker}: Finnhub daily candle endpoint returned no rows ({detail})."]

        timestamps = parsed.get("t") or []
        columns = {
            "open": parsed.get("o") or [],
            "high": parsed.get("h") or [],
            "low": parsed.get("l") or [],
            "close": parsed.get("c") or [],
            "volume": parsed.get("v") or [],
        }
        expected_length = len(timestamps)
        if not expected_length or any(len(values) != expected_length for values in columns.values()):
            return pd.DataFrame(columns=PRICE_COLUMNS), [f"{ticker}: Finnhub daily candle endpoint returned incomplete OHLCV rows."]

        dates = pd.to_datetime(timestamps, unit="s", utc=True, errors="coerce").tz_convert(None).normalize()
        frame = pd.DataFrame(
            {
                "date": dates,
                "ticker": ticker,
                "open": columns["open"],
                "high": columns["high"],
                "low": columns["low"],
                "close": columns["close"],
                "adj_close": columns["close"],
                "volume": columns["volume"],
            }
        )
        for numeric_column in ("open", "high", "low", "close", "adj_close", "volume"):
            frame[numeric_column] = pd.to_numeric(frame[numeric_column], errors="coerce")
        frame = frame.loc[
            frame["date"].notna()
            & frame["close"].notna()
            & frame["close"].gt(0)
            & frame["volume"].notna()
            & frame["volume"].ge(0)
        ].copy()
        if frame.empty:
            return pd.DataFrame(columns=PRICE_COLUMNS), [f"{ticker}: Finnhub daily candle rows were invalid after normalization."]
        frame = frame.sort_values("date")
        return frame[PRICE_COLUMNS].copy(), [
            f"{ticker}: prices refreshed from Finnhub daily candle endpoint; treat as research-grade and verify if used for decisions."
        ]


class IBKRDailyPriceSource:
    """Read-only daily OHLCV source using IBKR Gateway/TWS historical bars."""

    source_id = "ibkr"
    provider_name = "ibkr"

    def __init__(
        self,
        *,
        host: str | None = None,
        port: int | str | None = None,
        client_id: int | str | None = None,
        range_days: int = 900,
        timeout: int = 4,
        ib_factory: Callable[[], Any] | None = None,
        contract_factory: Callable[[str, str, str], Any] | None = None,
        module_loader: Callable[[str], Any] = importlib.import_module,
    ) -> None:
        self.host = str(host or os.environ.get(IBKR_HOST_ENV) or DEFAULT_IBKR_HOST).strip()
        self.port = _coerce_int(port if port is not None else os.environ.get(IBKR_PORT_ENV), DEFAULT_IBKR_PORT)
        self.client_id = _coerce_int(
            client_id if client_id is not None else os.environ.get(IBKR_CLIENT_ID_ENV),
            DEFAULT_IBKR_CLIENT_ID,
        )
        self.range_days = range_days
        self.timeout = timeout
        self.ib_factory = ib_factory
        self.contract_factory = contract_factory
        self.module_loader = module_loader

    def _load_ibkr_runtime(self) -> tuple[Callable[[], Any], Callable[[str, str, str], Any]] | tuple[None, None]:
        if self.ib_factory is not None and self.contract_factory is not None:
            return self.ib_factory, self.contract_factory
        try:
            module = self.module_loader("ib_insync")
        except ImportError:
            return None, None
        ib_factory = self.ib_factory or getattr(module, "IB")
        contract_factory = self.contract_factory or getattr(module, "Stock")
        return ib_factory, contract_factory

    def fetch_history(self, ticker: str) -> tuple[pd.DataFrame, list[str]]:
        ticker = ticker.upper().strip()
        ib_factory, contract_factory = self._load_ibkr_runtime()
        if ib_factory is None or contract_factory is None:
            return (
                pd.DataFrame(columns=PRICE_COLUMNS),
                [
                    f"{ticker}: ib_insync is not installed for IBKR read-only daily price refresh. "
                    "Install the optional IBKR dependency and run IBKR Gateway/TWS before using PROVIDER=ibkr."
                ],
            )

        client = ib_factory()
        connected = False
        try:
            client.connect(self.host, self.port, clientId=self.client_id, timeout=self.timeout, readonly=True)
            connected = True
            contract = contract_factory(ticker, "SMART", "USD")
            bars = client.reqHistoricalData(
                contract,
                endDateTime="",
                durationStr=f"{max(self.range_days, 1)} D",
                barSizeSetting="1 day",
                whatToShow="TRADES",
                useRTH=True,
                formatDate=1,
                keepUpToDate=False,
            )
        except TypeError as exc:
            if "readonly" not in str(exc):
                return pd.DataFrame(columns=PRICE_COLUMNS), [f"{ticker}: IBKR historical daily bars request failed ({exc})"]
            try:
                client.connect(self.host, self.port, clientId=self.client_id, timeout=self.timeout)
                connected = True
                contract = contract_factory(ticker, "SMART", "USD")
                bars = client.reqHistoricalData(
                    contract,
                    endDateTime="",
                    durationStr=f"{max(self.range_days, 1)} D",
                    barSizeSetting="1 day",
                    whatToShow="TRADES",
                    useRTH=True,
                    formatDate=1,
                    keepUpToDate=False,
                )
            except Exception as fallback_exc:
                return (
                    pd.DataFrame(columns=PRICE_COLUMNS),
                    [f"{ticker}: IBKR Gateway/TWS is unavailable for read-only daily bars ({fallback_exc})"],
                )
        except Exception as exc:
            return (
                pd.DataFrame(columns=PRICE_COLUMNS),
                [f"{ticker}: IBKR Gateway/TWS is unavailable for read-only daily bars ({exc})"],
            )
        finally:
            if connected and hasattr(client, "disconnect"):
                try:
                    client.disconnect()
                except Exception:
                    pass

        frame = _ibkr_bars_to_price_frame(ticker, bars)
        if frame.empty:
            return pd.DataFrame(columns=PRICE_COLUMNS), [f"{ticker}: IBKR historical daily bars returned no valid OHLCV rows."]
        return frame, [
            f"{ticker}: prices refreshed from IBKR historical daily bars as read-only market data; "
            "validate exchange subscriptions and provenance before applying."
        ]


class PriceSourceLadder:
    source_id = "price_source_ladder"

    def __init__(self, sources: list[tuple[str, PriceHistorySource]]) -> None:
        if not sources:
            raise ValueError("PriceSourceLadder requires at least one source.")
        for label, source in sources:
            exact_source_id = _price_source_id(source)
            if label != exact_source_id:
                raise ValueError(
                    "price source label/source_id mismatch: "
                    f"label={label!r}, source_id={exact_source_id!r}"
                )
        self.sources = sources
        self.provider_names = [name for name, _source in sources]
        self.source_ids = tuple(self.provider_names)
        self.provider_name = "auto"
        self.last_provider_name = self.provider_name
        self.last_source_id = ""

    def fetch_history(self, ticker: str) -> tuple[pd.DataFrame, list[str]]:
        warnings: list[str] = []
        self.last_provider_name = f"auto:{','.join(self.provider_names)}"
        self.last_source_id = ""
        for index, (provider_name, source) in enumerate(self.sources):
            try:
                frame, provider_warnings = source.fetch_history(ticker)
            except Exception as exc:  # pragma: no cover - defensive provider boundary
                frame = pd.DataFrame(columns=PRICE_COLUMNS)
                provider_warnings = [f"{ticker}: update failed from {provider_name} ({exc})"]
            warnings.extend(provider_warnings)
            if not frame.empty:
                self.last_provider_name = provider_name
                self.last_source_id = _price_source_id(source)
                if index > 0:
                    warnings.append(
                        f"{ticker}: source ladder resolved price rows from {provider_name} after "
                        f"{', '.join(self.provider_names[:index])} failed."
                    )
                return frame, warnings
        return pd.DataFrame(columns=PRICE_COLUMNS), warnings


def _price_source_status_name(source: PriceHistorySource) -> str:
    last_provider = str(getattr(source, "last_provider_name", "") or "").strip()
    if last_provider:
        return last_provider
    provider_name = str(getattr(source, "provider_name", "") or "").strip()
    if provider_name:
        return provider_name
    return source.__class__.__name__


def _price_source_id(source: PriceHistorySource) -> str:
    source_id = str(getattr(source, "source_id", "") or "").strip()
    if not source_id:
        raise RuntimeError("commercial_price_source_id_required: exact source_id is missing")
    return source_id


def _require_commercial_price_source(
    registry: Mapping[str, SourceRights],
    source_id: str,
) -> None:
    review = review_commercial_field_scope(registry, source_id, ("prices",))
    if not review.commercial_rights_approved:
        raise RuntimeError(
            "commercial_price_source_review_required: "
            f"source_id={source_id}, rights_status={review.rights_status}"
        )
    if review.missing_supported_fields:
        raise RuntimeError(
            "commercial_price_scope_review_required: "
            f"source_id={source_id}, missing_supported_fields="
            f"{','.join(review.missing_supported_fields)}"
        )


def _commercial_price_source_is_allowed(
    registry: Mapping[str, SourceRights],
    source_id: str,
) -> bool:
    return review_commercial_field_scope(
        registry, source_id, ("prices",)
    ).commercial_evidence_ready


def _reachable_price_source_ids(source: PriceHistorySource) -> tuple[str, ...]:
    if isinstance(source, PriceSourceLadder):
        return source.source_ids
    return (_price_source_id(source),)


def _selected_price_source_id(source: PriceHistorySource) -> str:
    if isinstance(source, PriceSourceLadder):
        selected = str(source.last_source_id or "").strip()
        if not selected:
            raise RuntimeError(
                "commercial_price_source_id_required: ladder selected source_id is missing"
            )
        return selected
    return _price_source_id(source)


def make_price_source(
    provider: str,
    *,
    commercial_mode: bool | None = None,
    rights_registry: Mapping[str, SourceRights] | None = None,
) -> PriceHistorySource:
    load_provider_environment()
    normalized = str(provider or "auto").strip().lower()
    commercial = commercial_mode_enabled() if commercial_mode is None else commercial_mode
    registry = rights_registry
    if commercial and registry is None:
        registry = load_source_rights_registry()

    exact_provider_ids = {
        "stooq": "stooq",
        "yahoo": "yahoo",
        "fmp": "fmp",
        "financial_modeling_prep": "fmp",
        "alpha_vantage": "alpha_vantage",
        "alphavantage": "alpha_vantage",
        "finnhub": "finnhub",
        "ibkr": "ibkr",
    }
    if commercial and normalized not in {"auto", "ladder", "source_ladder"}:
        exact_source_id = exact_provider_ids.get(normalized)
        if exact_source_id is not None:
            assert registry is not None
            _require_commercial_price_source(registry, exact_source_id)

    if normalized in {"auto", "ladder", "source_ladder"}:
        source_factories: list[tuple[str, bool, Callable[[], PriceHistorySource]]] = [
            ("stooq", True, StooqDailyPriceSource),
            ("yahoo", True, YahooChartDailyPriceSource),
            ("ibkr", _ibkr_auto_configured(), IBKRDailyPriceSource),
            ("fmp", bool(os.environ.get(FMP_API_KEY_ENV, "").strip()), FMPDailyPriceSource),
            (
                "alpha_vantage",
                bool(os.environ.get(ALPHA_VANTAGE_API_KEY_ENV, "").strip()),
                AlphaVantageDailyPriceSource,
            ),
            (
                "finnhub",
                bool(os.environ.get(FINNHUB_API_KEY_ENV, "").strip()),
                FinnhubDailyPriceSource,
            ),
        ]
        configured_factories = [item for item in source_factories if item[1]]
        if commercial:
            assert registry is not None
            allowed_factories = [
                item
                for item in configured_factories
                if _commercial_price_source_is_allowed(registry, item[0])
            ]
            if not allowed_factories:
                configured_ids = ",".join(item[0] for item in configured_factories)
                raise RuntimeError(
                    "commercial_price_source_review_required: no configured automatic "
                    f"price source has approved rights and prices scope; sources={configured_ids}"
                )
            configured_factories = allowed_factories
        return PriceSourceLadder(
            [(source_id, factory()) for source_id, _configured, factory in configured_factories]
        )
    if normalized == "stooq":
        return StooqDailyPriceSource()
    if normalized == "yahoo":
        return YahooChartDailyPriceSource()
    if normalized in {"fmp", "financial_modeling_prep"}:
        return FMPDailyPriceSource()
    if normalized in {"alpha_vantage", "alphavantage"}:
        return AlphaVantageDailyPriceSource()
    if normalized == "finnhub":
        return FinnhubDailyPriceSource()
    if normalized == "ibkr":
        return IBKRDailyPriceSource()
    raise ValueError(f"Unsupported price provider: {provider}")


def _read_csv_if_present(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    frame = pd.read_csv(path)
    frame.columns = _normalize_columns(list(frame.columns))
    frame = _ensure_price_aliases(frame)
    return frame


def load_update_tickers(
    base_dir: Path,
    config: AppConfig | None = None,
    universe_file: Path | None = None,
    data_dir: Path | None = None,
) -> list[str]:
    config = config or AppConfig.load(base_dir / "config.yaml")
    data_dir = data_dir or (base_dir / "data")
    universe = _read_csv_if_present(universe_file or (data_dir / "universe.csv"))
    holdings = _read_csv_if_present(data_dir / "holdings.csv")
    theme_map = _read_csv_if_present(data_dir / "theme_map.csv")

    tickers: set[str] = set()
    if "ticker" in universe.columns:
        tickers.update(_normalize_ticker_series(universe["ticker"]).dropna().tolist())
    if "ticker" in holdings.columns:
        tickers.update(_normalize_ticker_series(holdings["ticker"]).dropna().tolist())
    for universe_etf_column in ("sector_etf", "sectoretf"):
        if universe_etf_column in universe.columns:
            tickers.update(_normalize_ticker_series(universe[universe_etf_column]).dropna().tolist())
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


def _chunked(items: list[str], chunk_size: int) -> list[list[str]]:
    if chunk_size <= 0:
        return [items]
    return [items[index : index + chunk_size] for index in range(0, len(items), chunk_size)]


def _ordered_normalized_tickers(tickers: list[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for ticker in tickers:
        normalized = _normalize_ticker_series(pd.Series([ticker])).dropna().tolist()
        if not normalized:
            continue
        value = normalized[0]
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def _fresh_tickers(existing: pd.DataFrame, freshness_days: int) -> set[str]:
    if existing.empty or "ticker" not in existing.columns or "date" not in existing.columns:
        return set()
    cutoff = pd.Timestamp.now(tz="UTC").tz_localize(None).normalize() - pd.Timedelta(days=freshness_days)
    latest_by_ticker = existing.groupby("ticker")["date"].max()
    return {
        ticker
        for ticker, latest_date in latest_by_ticker.items()
        if pd.notna(latest_date) and latest_date >= cutoff
    }


def _tickers_without_local_prices(tickers: list[str], existing: pd.DataFrame) -> list[str]:
    if existing.empty or "ticker" not in existing.columns:
        return tickers
    existing_tickers = set(existing["ticker"].dropna().astype(str).str.upper().str.strip())
    return [ticker for ticker in tickers if ticker not in existing_tickers]


def _latest_price_date(existing: pd.DataFrame, ticker: str) -> str:
    if existing.empty or "ticker" not in existing.columns or "date" not in existing.columns:
        return ""
    rows = existing.loc[existing["ticker"].astype(str).str.upper().str.strip() == ticker]
    if rows.empty:
        return ""
    latest = rows["date"].max()
    if pd.isna(latest):
        return ""
    return pd.Timestamp(latest).date().isoformat()


def _next_requested_start(existing: pd.DataFrame, ticker: str) -> str:
    latest = _latest_price_date(existing, ticker)
    if not latest:
        return ""
    next_date = pd.Timestamp(latest) + pd.Timedelta(days=1)
    return next_date.date().isoformat()


def _categorize_price_error(messages: list[str]) -> tuple[str, str]:
    message = " | ".join(str(item) for item in messages if str(item).strip())
    lowered = message.lower()
    if not message:
        return "failed", ""
    if "tokenizing" in lowered or "parser" in lowered or "parse" in lowered:
        return "parse_error", message
    if "url" in lowered or "timed out" in lowered or "network" in lowered or "connection" in lowered:
        return "network_error", message
    if "no data" in lowered or "no rows" in lowered:
        return "no_rows", message
    if "unavailable" in lowered or "source" in lowered:
        return "source_unavailable", message
    return "failed", message


def _normalized_error_message(status: str, ticker: str, error_message: object) -> str:
    message = " ".join(str(error_message or "").split()).strip()
    if not message:
        return ""
    message = message.replace(
        "Set STOOQ_API_KEY or use the manual price import draft workflow.",
        "Set STOOQ_API_KEY or use verified local price import files.",
    )

    if status != "parse_error":
        return message

    lowered = message.lower()
    if "error tokenizing data" in lowered:
        detail = message
        if ": update failed" in detail:
            detail = detail.split(": update failed", 1)[1].strip()
        if detail.startswith("(") and detail.endswith(")"):
            detail = detail[1:-1].strip()
        if detail.lower().startswith("error tokenizing data."):
            detail = detail[len("Error tokenizing data.") :].strip()
        if detail.lower().startswith("c error:"):
            detail = detail[len("C error:") :].strip()
        if detail:
            return f"{ticker}: provider rows could not be parsed cleanly ({detail})"
        return f"{ticker}: provider rows could not be parsed cleanly"

    return message


def _price_recommended_action(status: str, ticker: str, has_local_data: bool) -> str:
    normalize_action = (
        f"Run make focus-price TICKER={ticker} first. For batch planning, preview make price-refresh-loop DRY_RUN=1; "
        f"if you choose to refresh this ticker, run make price-refresh TICKERS={ticker} PROVIDER=auto so Stooq, "
        "Yahoo, optional IBKR read-only, and configured FMP/Alpha Vantage/Finnhub fallbacks are tried automatically; only if every provider path "
        "fails, normalize verified downloaded OHLCV files into data/imports/prices.csv."
    )
    if status == "fetched":
        return "No action needed; remote rows were merged into local prices."
    if status == "insufficient_history":
        return normalize_action
    if status == "skipped_fresh":
        return "Leave unchanged because local data exists and is fresh."
    if status == "no_rows":
        return normalize_action
    if status == "parse_error":
        return normalize_action
    if status == "network_error":
        return normalize_action
    if status == "source_unavailable":
        return normalize_action
    if has_local_data:
        return (
            f"Leave unchanged because local data exists; for fresher rows, run make price-refresh TICKERS={ticker} "
            "PROVIDER=auto before using the manual price import file workflow."
        )
    return normalize_action


def _price_focus_command(status: str, ticker: str) -> str:
    if status in {"fetched", "skipped_fresh"} or not ticker:
        return ""
    return f"make focus-price TICKER={ticker}"


def _price_example_command(status: str, ticker: str) -> str:
    if status in {"fetched", "skipped_fresh"} or not ticker:
        return ""
    return f"make price-normalize INPUT=data/raw/prices/{ticker}.csv TICKER={ticker} SOURCE=yahoo_manual"


def _price_target_file(status: str) -> str:
    if status in {"fetched", "skipped_fresh"}:
        return "data/prices.csv"
    return "data/imports/prices.csv"


def _valid_price_row_count(frame: pd.DataFrame, ticker: str) -> int:
    if frame.empty or "ticker" not in frame.columns:
        return 0
    rows = frame.loc[frame["ticker"].astype(str).str.upper().str.strip() == ticker].copy()
    if rows.empty:
        return 0
    rows["date"] = pd.to_datetime(rows.get("date"), errors="coerce", format="mixed")
    rows["close"] = pd.to_numeric(rows.get("close"), errors="coerce")
    rows = rows.loc[rows["date"].notna() & rows["close"].notna() & rows["close"].gt(0)]
    return int(len(rows))


def _projected_price_row_count(existing: pd.DataFrame, fetched: pd.DataFrame, ticker: str) -> int:
    projected = pd.concat([existing, fetched], ignore_index=True)
    if {"date", "ticker"}.issubset(projected.columns):
        projected = projected.drop_duplicates(subset=["date", "ticker"], keep="last")
    return _valid_price_row_count(projected, ticker)


def _recommended_action_needs_refresh(status: str, recommended_action: str, ticker: str) -> bool:
    if not recommended_action.strip():
        return True
    normalized_action = recommended_action.strip().lower()
    if status in {"fetched", "skipped_fresh"}:
        return False
    if normalized_action in {
        "retry later or use the manual price import draft workflow in data/imports/prices.csv.",
        "retry later or use the manual price import file workflow in data/imports/prices.csv.",
        "use the manual price import draft workflow in data/imports/prices.csv.",
        "use the manual price import file workflow in data/imports/prices.csv.",
        "use the manual price import draft workflow.",
        "use the manual price import file workflow.",
    }:
        return True
    if "ohlcv rows into data/imports/prices.csv" in normalized_action:
        return True
    if "free refresh path fails" in normalized_action:
        return True
    if ticker and "make focus-price" not in normalized_action:
        return True
    if ticker and f"make price-refresh tickers={ticker.lower()}" not in normalized_action:
        return True
    if ticker and "provider=auto" not in normalized_action:
        return True
    if "configured fmp/alpha vantage" not in normalized_action:
        return True
    if "every provider path fails" not in normalized_action:
        return True
    return False


def _example_command_needs_refresh(status: str, example_command: str, ticker: str) -> bool:
    text = str(example_command or "").strip()
    if not text:
        return True
    expected = _price_example_command(status, ticker)
    if not expected:
        return False
    if text in {"make onboarding", "make status"}:
        return True
    if re.fullmatch(r"python3 -m src\.data_update --tickers .+", text):
        return True
    return text != expected


def _error_message_needs_refresh(status: str, error_message: str, ticker: str) -> bool:
    normalized = str(error_message or "").strip()
    if not normalized:
        return False
    if "set stooq_api_key or use the manual price import draft workflow" in normalized.lower():
        return True
    if status != "parse_error":
        return "\n" in normalized
    lowered = normalized.lower()
    if "\n" in normalized:
        return True
    if "error tokenizing data" in lowered:
        return True
    if ": update failed" in lowered:
        return True
    if ticker and ticker not in normalized:
        return True
    return False


def enrich_price_update_status_frame(frame: pd.DataFrame) -> pd.DataFrame:
    enriched = frame.copy()
    if "ticker" not in enriched.columns or "status" not in enriched.columns:
        return enriched
    if "recommended_action" not in enriched.columns:
        enriched["recommended_action"] = ""
    if "focus_command" not in enriched.columns:
        enriched["focus_command"] = ""
    if "example_command" not in enriched.columns:
        enriched["example_command"] = ""
    if "target_file" not in enriched.columns:
        enriched["target_file"] = ""

    for index, row in enriched.iterrows():
        status = str(row.get("status", "")).strip().lower()
        ticker = str(row.get("ticker", "")).strip().upper()
        error_message = str(row.get("error_message", "")).strip()
        recommended_action = str(row.get("recommended_action", "")).strip()
        rows_merged = pd.to_numeric(pd.Series([row.get("rows_merged")]), errors="coerce").fillna(0).iloc[0]
        has_local_data = bool(str(row.get("requested_start", "")).strip()) or bool(rows_merged)
        if _error_message_needs_refresh(status, error_message, ticker):
            enriched.at[index, "error_message"] = _normalized_error_message(status, ticker, error_message)
        if _recommended_action_needs_refresh(status, recommended_action, ticker):
            enriched.at[index, "recommended_action"] = _price_recommended_action(status, ticker, has_local_data)
        if not str(row.get("focus_command", "")).strip():
            enriched.at[index, "focus_command"] = _price_focus_command(status, ticker)
        if _example_command_needs_refresh(status, str(row.get("example_command", "")).strip(), ticker):
            enriched.at[index, "example_command"] = _price_example_command(status, ticker)
        if not str(row.get("target_file", "")).strip():
            enriched.at[index, "target_file"] = _price_target_file(status)
    return enriched


def _price_status_row(
    *,
    run_timestamp: str,
    ticker: str,
    requested_start: str,
    requested_end: str,
    provider: str,
    status: str,
    rows_fetched: int = 0,
    rows_merged: int = 0,
    error_message: str = "",
    fallback_used: bool = False,
    has_local_data: bool = False,
) -> dict[str, Any]:
    return {
        "run_timestamp": run_timestamp,
        "ticker": ticker,
        "requested_start": requested_start,
        "requested_end": requested_end,
        "provider": provider,
        "status": status,
        "rows_fetched": rows_fetched,
        "rows_merged": rows_merged,
        "error_category": "" if status in {"fetched", "skipped_fresh"} else status,
        "error_message": _normalized_error_message(status, ticker, error_message),
        "fallback_used": fallback_used,
        "recommended_action": _price_recommended_action(status, ticker, has_local_data),
        "focus_command": _price_focus_command(status, ticker),
        "example_command": _price_example_command(status, ticker),
        "target_file": _price_target_file(status),
    }


def write_price_update_status(rows: list[dict[str, Any]], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "price_update_status.csv"
    pd.DataFrame(rows, columns=PRICE_STATUS_COLUMNS).to_csv(path, index=False)
    return path


def refresh_price_update_status_output(
    base_dir: Path | str | None = None,
    *,
    output_dir: Path | str | None = None,
) -> Path | None:
    root = resolve_project_root(base_dir)
    output_path = resolve_outputs_dir(output_dir, root)
    path = output_path / "price_update_status.csv"
    if not path.exists():
        return None
    frame = pd.read_csv(path)
    enriched = enrich_price_update_status_frame(frame)
    enriched.to_csv(path, index=False)
    return path


def update_local_price_data(
    base_dir: Path | None = None,
    source: PriceHistorySource | None = None,
    tickers: list[str] | None = None,
    *,
    data_dir: Path | None = None,
    output_dir: Path | None = None,
    chunk_size: int = 50,
    max_tickers: int | None = None,
    refresh: bool = False,
    freshness_days: int = 1,
    universe_file: Path | None = None,
    missing_only: bool = False,
    retry_attempts: int = 1,
    retry_backoff_seconds: float = 0.25,
    progress_callback: Callable[[dict[str, object]], None] | None = None,
    commercial_mode: bool | None = None,
    rights_registry: Mapping[str, SourceRights] | None = None,
) -> PriceUpdateResult:
    base_dir = resolve_project_root(base_dir)
    data_dir = resolve_data_dir(data_dir, base_dir)
    output_dir = resolve_outputs_dir(output_dir, base_dir)
    commercial = commercial_mode_enabled() if commercial_mode is None else commercial_mode
    registry = rights_registry
    if commercial and registry is None:
        registry = load_source_rights_registry()
    source = source or make_price_source(
        "auto", commercial_mode=commercial, rights_registry=registry
    )
    reviewed_source_ids: tuple[str, ...] = ()
    if commercial:
        assert registry is not None
        reviewed_source_ids = _reachable_price_source_ids(source)
        for source_id in reviewed_source_ids:
            _require_commercial_price_source(registry, source_id)

    config = AppConfig.load(base_dir / "config.yaml")
    prices_path = data_dir / "prices.csv"
    provider_name = _price_source_status_name(source)
    run_timestamp = datetime.now(timezone.utc).isoformat()
    requested_end = pd.Timestamp.now(tz="UTC").date().isoformat()
    tickers = tickers or load_update_tickers(base_dir, config, universe_file=universe_file, data_dir=data_dir)
    tickers = _ordered_normalized_tickers(tickers)

    existing = _load_existing_prices(prices_path)
    if missing_only:
        tickers = _tickers_without_local_prices(tickers, existing)
    if max_tickers is not None and max_tickers > 0:
        tickers = tickers[:max_tickers]

    warnings: list[str] = []
    updated: list[str] = []
    missing: list[str] = []
    skipped_fresh: list[str] = []
    combined = existing.copy()
    existing_tickers = set(existing["ticker"].dropna().astype(str).str.upper().str.strip()) if "ticker" in existing.columns else set()
    status_rows: list[dict[str, Any]] = []
    tickers_to_fetch = tickers
    if not refresh:
        fresh_ticker_set = _fresh_tickers(existing, freshness_days)
        skipped_fresh = [ticker for ticker in tickers if ticker in fresh_ticker_set]
        tickers_to_fetch = [ticker for ticker in tickers if ticker not in fresh_ticker_set]
        for ticker in skipped_fresh:
            status_rows.append(
                _price_status_row(
                    run_timestamp=run_timestamp,
                    ticker=ticker,
                    requested_start=_next_requested_start(existing, ticker),
                    requested_end=requested_end,
                    provider=provider_name,
                    status="skipped_fresh",
                    rows_fetched=0,
                    rows_merged=0,
                    fallback_used=False,
                    has_local_data=True,
                )
            )
        if skipped_fresh:
            warnings.append(
                f"Skipped {len(skipped_fresh)} ticker(s) that already have price data within the last {freshness_days} day(s)."
            )

    if not tickers_to_fetch:
        status_path = write_price_update_status(status_rows, output_dir)
        no_rows_warning = (
            "No tickers matched the missing-only price refresh filter; kept the existing local CSV fallback."
            if missing_only and not tickers
            else "No remote price rows were added; kept the existing local CSV fallback."
        )
        return PriceUpdateResult(
            path=prices_path,
            tickers_requested=tickers,
            tickers_updated=[],
            tickers_missing=missing,
            tickers_skipped_fresh=skipped_fresh,
            rows_written=len(existing),
            chunks_processed=0,
            warnings=warnings + [no_rows_warning],
            status_path=status_path,
            status_rows=status_rows,
        )

    chunks = _chunked(tickers_to_fetch, chunk_size)
    processed_chunks = 0
    for chunk_index, chunk in enumerate(chunks, start=1):
        fetched_frames: list[pd.DataFrame] = []
        for ticker in chunk:
            last_warning_count = len(warnings)
            frame = pd.DataFrame(columns=PRICE_COLUMNS)
            fetch_warnings: list[str] = []
            for attempt in range(retry_attempts + 1):
                try:
                    frame, fetch_warnings = source.fetch_history(ticker)
                except Exception as exc:  # pragma: no cover - defensive runtime path
                    fetch_warnings = [f"{ticker}: update failed ({exc})"]
                    frame = pd.DataFrame(columns=PRICE_COLUMNS)
                if commercial:
                    assert registry is not None
                    if frame.empty and not isinstance(source, PriceSourceLadder):
                        current_source_id = _price_source_id(source)
                        if current_source_id not in reviewed_source_ids:
                            raise RuntimeError(
                                "commercial_price_source_changed: "
                                f"reviewed={','.join(reviewed_source_ids)}, selected={current_source_id}"
                            )
                    if not frame.empty:
                        selected_source_id = _selected_price_source_id(source)
                        if selected_source_id not in reviewed_source_ids:
                            raise RuntimeError(
                                "commercial_price_source_changed: "
                                f"reviewed={','.join(reviewed_source_ids)}, selected={selected_source_id}"
                            )
                        _require_commercial_price_source(registry, selected_source_id)
                if frame.empty and attempt < retry_attempts:
                    sleep(retry_backoff_seconds * (attempt + 1))
                    continue
                warnings.extend(fetch_warnings)
                break
            provider_name = _price_source_status_name(source)
            if frame.empty:
                missing.append(ticker)
                status, message = _categorize_price_error(fetch_warnings)
                status_rows.append(
                    _price_status_row(
                        run_timestamp=run_timestamp,
                        ticker=ticker,
                        requested_start=_next_requested_start(existing, ticker),
                        requested_end=requested_end,
                        provider=provider_name,
                        status=status,
                        rows_fetched=0,
                        rows_merged=0,
                        error_message=message,
                        fallback_used=ticker in existing_tickers,
                        has_local_data=ticker in existing_tickers,
                    )
                )
                continue
            fetched_frames.append(frame)
            updated.append(ticker)
            provider_name = _price_source_status_name(source)
            projected_rows = _projected_price_row_count(combined, frame, ticker)
            status = "fetched" if projected_rows >= MIN_PRICE_READY_ROWS else "insufficient_history"
            status_rows.append(
                _price_status_row(
                    run_timestamp=run_timestamp,
                    ticker=ticker,
                    requested_start=_next_requested_start(existing, ticker),
                    requested_end=requested_end,
                    provider=provider_name,
                    status=status,
                    rows_fetched=len(frame),
                    rows_merged=projected_rows,
                    fallback_used=False,
                    has_local_data=True,
                )
            )

            if progress_callback is not None:
                progress_callback(
                    {
                        "event": "ticker_complete",
                        "ticker": ticker,
                        "chunk_index": chunk_index,
                        "chunks_total": len(chunks),
                        "warnings_added": len(warnings) - last_warning_count,
                    }
                )

        if fetched_frames:
            combined = pd.concat([combined, *fetched_frames], ignore_index=True)
            combined = (
                combined.drop_duplicates(subset=["date", "ticker"], keep="last")
                .sort_values(["ticker", "date"])
                .reset_index(drop=True)
            )
            combined.to_csv(prices_path, index=False)
        processed_chunks += 1
        if progress_callback is not None:
            progress_callback(
                {
                    "event": "chunk_complete",
                    "chunk_index": chunk_index,
                    "chunks_total": len(chunks),
                    "tickers_in_chunk": len(chunk),
                    "updated_so_far": len(updated),
                    "missing_so_far": len(missing),
                }
            )

    if not updated:
        status_path = write_price_update_status(status_rows, output_dir)
        return PriceUpdateResult(
            path=prices_path,
            tickers_requested=tickers,
            tickers_updated=[],
            tickers_missing=missing,
            tickers_skipped_fresh=skipped_fresh,
            rows_written=len(existing),
            chunks_processed=processed_chunks,
            warnings=warnings + ["No remote price rows were added; kept the existing local CSV fallback."],
            status_path=status_path,
            status_rows=status_rows,
        )

    status_path = write_price_update_status(status_rows, output_dir)
    return PriceUpdateResult(
        path=prices_path,
        tickers_requested=tickers,
        tickers_updated=updated,
        tickers_missing=missing,
        tickers_skipped_fresh=skipped_fresh,
        rows_written=len(combined),
        chunks_processed=processed_chunks,
        warnings=warnings,
        status_path=status_path,
        status_rows=status_rows,
    )


def _resolve_import_dir(data_dir: Path, import_dir: Path | None = None) -> Path:
    return import_dir or (data_dir / "imports")


def _read_price_import(path: Path) -> tuple[pd.DataFrame, list[str]]:
    if not path.exists():
        return pd.DataFrame(), ["Staged price import file is not present."]
    frame = pd.read_csv(path)
    frame.columns = _normalize_columns(list(frame.columns))
    frame = _ensure_price_aliases(frame)
    return frame, []


def _serialize_price_date(value: Any) -> str:
    if pd.isna(value):
        return ""
    timestamp = pd.to_datetime(value, errors="coerce")
    if pd.isna(timestamp):
        return ""
    return timestamp.date().isoformat()


def _price_temporal_summary(
    frame: pd.DataFrame,
    *,
    review_cutoff: str | None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    if frame.empty:
        return frame.copy(), {
            "price_temporal_status": "no_valid_rows",
            "price_temporal_complete_rows": 0,
            "price_temporal_review_required_rows": 0,
            "price_temporal_invalid_rows": 0,
            "price_temporal_blocker_counts": {},
            "price_review_cutoff": "",
        }

    reviewed = frame.copy()
    blocker_counts: dict[str, int] = {}
    complete_rows = 0
    invalid_rows = 0
    normalized_cutoff = ""
    for index, row in reviewed.iterrows():
        temporal = review_daily_price_retrieval(
            row.get("date"),
            row.get("retrieved_at"),
            review_cutoff=review_cutoff,
        )
        if temporal.review_cutoff:
            normalized_cutoff = temporal.review_cutoff
        if not temporal.blockers:
            complete_rows += 1
            reviewed.at[index, "retrieved_at"] = temporal.retrieved_at
            continue
        reviewed.at[index, "retrieved_at"] = temporal.retrieved_at
        if temporal.blockers != ("missing_retrieved_at",):
            invalid_rows += 1
        for blocker in temporal.blockers:
            blocker_counts[blocker] = blocker_counts.get(blocker, 0) + 1

    required_rows = len(reviewed) - complete_rows
    return reviewed, {
        "price_temporal_status": (
            "temporal_complete" if required_rows == 0 else "temporal_review_required"
        ),
        "price_temporal_complete_rows": complete_rows,
        "price_temporal_review_required_rows": required_rows,
        "price_temporal_invalid_rows": invalid_rows,
        "price_temporal_blocker_counts": dict(sorted(blocker_counts.items())),
        "price_review_cutoff": normalized_cutoff,
    }


def _price_lineage_summary(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {
            "lineage_status": "no_valid_rows",
            "lineage_complete_rows": 0,
            "lineage_review_required_rows": 0,
            "lineage_missing_fields": [],
        }

    present: dict[str, pd.Series] = {}
    for field in ("source", "source_ref", "retrieved_at"):
        if field not in frame.columns:
            present[field] = pd.Series(False, index=frame.index, dtype=bool)
            continue
        values = frame[field].astype("string").str.strip()
        present[field] = values.notna() & values.ne("")

    complete_mask = present["source"] & present["source_ref"] & present["retrieved_at"]
    complete_rows = int(complete_mask.sum())
    missing_fields = sorted(field for field, field_present in present.items() if not bool(field_present.all()))
    return {
        "lineage_status": "lineage_complete" if complete_rows == len(frame) else "lineage_review_required",
        "lineage_complete_rows": complete_rows,
        "lineage_review_required_rows": len(frame) - complete_rows,
        "lineage_missing_fields": missing_fields,
    }


def _price_source_evidence_summary(
    frame: pd.DataFrame,
    rights_registry: Mapping[str, SourceRights],
) -> dict[str, Any]:
    if frame.empty:
        return {
            "commercial_rights_status": "no_valid_rows",
            "rights_approved_rows": 0,
            "rights_review_required_rows": 0,
            "rights_status_counts": {},
            "price_scope_status": "no_valid_rows",
            "price_scope_complete_rows": 0,
            "price_scope_review_required_rows": 0,
            "source_review_rows": [],
            "commercial_evidence_warnings": [],
        }

    if "source" in frame.columns:
        source_ids = frame["source"].astype("string").fillna("").str.strip()
    else:
        source_ids = pd.Series("", index=frame.index, dtype="string")

    rights_approved_rows = 0
    price_scope_complete_rows = 0
    rights_status_counts: dict[str, int] = {}
    source_review_rows: list[dict[str, Any]] = []
    for source_id in sorted(source_ids.unique().tolist()):
        row_count = int(source_ids.eq(source_id).sum())
        rights = commercial_eligibility(rights_registry, source_id)
        rights_status_counts[rights.status] = rights_status_counts.get(rights.status, 0) + row_count
        rights_approved_rows += row_count if rights.allowed else 0
        rights_record = rights_registry.get(source_id)
        price_scope_complete = bool(
            rights_record is not None and "prices" in rights_record.supported_fields
        )
        price_scope_complete_rows += row_count if price_scope_complete else 0
        blockers: list[str] = []
        if not rights.allowed:
            blockers.append(f"commercial_rights:{rights.status}")
        if not price_scope_complete:
            blockers.append("registered_price_scope_incomplete")
        source_review_rows.append(
            {
                "source_id": source_id or "<missing>",
                "row_count": row_count,
                "rights_status": rights.status,
                "commercial_rights_approved": rights.allowed,
                "price_scope_complete": price_scope_complete,
                "blockers": blockers,
            }
        )

    valid_rows = len(frame)
    rights_review_required_rows = valid_rows - rights_approved_rows
    price_scope_review_required_rows = valid_rows - price_scope_complete_rows
    if rights_approved_rows == valid_rows:
        commercial_rights_status = "rights_approved"
    elif rights_approved_rows == 0:
        commercial_rights_status = "rights_review_required"
    else:
        commercial_rights_status = "mixed_rights"
    if price_scope_complete_rows == valid_rows:
        price_scope_status = "price_scope_complete"
    elif price_scope_complete_rows == 0:
        price_scope_status = "price_scope_review_required"
    else:
        price_scope_status = "mixed_price_scope"

    commercial_evidence_warnings: list[str] = []
    if rights_review_required_rows:
        commercial_evidence_warnings.append(
            "Commercial rights review required for "
            f"{rights_review_required_rows} valid staged price row(s)."
        )
    if price_scope_review_required_rows:
        commercial_evidence_warnings.append(
            "Registered prices scope review required for "
            f"{price_scope_review_required_rows} valid staged price row(s)."
        )
    return {
        "commercial_rights_status": commercial_rights_status,
        "rights_approved_rows": rights_approved_rows,
        "rights_review_required_rows": rights_review_required_rows,
        "rights_status_counts": dict(sorted(rights_status_counts.items())),
        "price_scope_status": price_scope_status,
        "price_scope_complete_rows": price_scope_complete_rows,
        "price_scope_review_required_rows": price_scope_review_required_rows,
        "source_review_rows": source_review_rows,
        "commercial_evidence_warnings": commercial_evidence_warnings,
    }


def _normalize_price_import_frame(
    frame: pd.DataFrame,
    *,
    review_cutoff: str | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    warnings: list[str] = []
    unknown_columns = sorted(set(frame.columns) - set(PRICE_IMPORT_REQUIRED_COLUMNS) - set(PRICE_IMPORT_OPTIONAL_COLUMNS) - {"adj_close"})
    if unknown_columns:
        warnings.append(f"Unknown columns detected and ignored: {', '.join(unknown_columns)}.")

    missing_required = sorted(set(PRICE_IMPORT_REQUIRED_COLUMNS) - set(frame.columns))
    if missing_required:
        return (
            pd.DataFrame(columns=PRICE_IMPORT_OUTPUT_COLUMNS),
            {
                "status": "invalid",
                "missing_required_columns": missing_required,
                "unknown_columns": unknown_columns,
                "warnings": warnings,
                "row_count": len(frame),
                "valid_rows": 0,
                "skipped_rows": len(frame),
                "duplicate_rows": 0,
                "affected_tickers": [],
                **_price_lineage_summary(pd.DataFrame()),
                **_price_temporal_summary(
                    pd.DataFrame(), review_cutoff=review_cutoff
                )[1],
            },
        )

    normalized = frame.copy()
    normalized["ticker"] = _normalize_ticker_series(normalized["ticker"])
    normalized["date"] = pd.to_datetime(normalized["date"], errors="coerce", format="mixed")
    for text_column in ("source", "source_ref"):
        if text_column in normalized.columns:
            normalized[text_column] = normalized[text_column].astype("string").str.strip()
    if "retrieved_at" in normalized.columns:
        normalized["retrieved_at"] = normalized["retrieved_at"].astype("string").fillna("").str.strip()
    if "as_of_date" in normalized.columns:
        normalized["as_of_date"] = pd.to_datetime(normalized["as_of_date"], errors="coerce", format="mixed")
    for numeric_column in ("open", "high", "low", "close", "adj_close", "volume"):
        if numeric_column in normalized.columns:
            before = normalized[numeric_column].notna().sum()
            normalized[numeric_column] = pd.to_numeric(normalized[numeric_column], errors="coerce")
            after = normalized[numeric_column].notna().sum()
            if after < before:
                warnings.append(f"{numeric_column}: {before - after} rows could not be parsed as numeric values.")

    if "adj_close" not in normalized.columns:
        normalized["adj_close"] = normalized["close"]

    valid_mask = pd.Series(True, index=normalized.index)
    valid_mask &= normalized["date"].notna()
    valid_mask &= normalized["ticker"].notna() & normalized["ticker"].astype(str).str.strip().ne("")
    for required_numeric in ("open", "high", "low", "close", "volume"):
        valid_mask &= normalized[required_numeric].notna()
    valid_mask &= normalized["close"].gt(0)
    valid_mask &= normalized["volume"].ge(0)
    valid_mask &= normalized["high"].ge(normalized["low"])
    skipped_invalid = int((~valid_mask).sum())
    if skipped_invalid:
        warnings.append(f"Skipped {skipped_invalid} invalid price import file row(s).")

    valid = normalized.loc[valid_mask].copy()
    if valid.empty:
        return (
            pd.DataFrame(columns=PRICE_IMPORT_OUTPUT_COLUMNS),
            {
                "status": "invalid",
                "missing_required_columns": [],
                "unknown_columns": unknown_columns,
                "warnings": warnings,
                "row_count": len(frame),
                "valid_rows": 0,
                "skipped_rows": skipped_invalid,
                "duplicate_rows": 0,
                "affected_tickers": [],
                **_price_lineage_summary(pd.DataFrame()),
                **_price_temporal_summary(
                    pd.DataFrame(), review_cutoff=review_cutoff
                )[1],
            },
        )

    duplicate_rows = int(valid.duplicated(subset=["date", "ticker"], keep="last").sum())
    if duplicate_rows:
        warnings.append(f"Deduplicated {duplicate_rows} duplicate date+ticker staged row(s), keeping the last row.")
    valid = valid.drop_duplicates(subset=["date", "ticker"], keep="last").copy()

    valid, temporal_summary = _price_temporal_summary(
        valid,
        review_cutoff=review_cutoff,
    )

    valid["date"] = valid["date"].apply(_serialize_price_date)
    if "as_of_date" in valid.columns:
        valid["as_of_date"] = valid["as_of_date"].apply(_serialize_price_date)
    output_columns = ["date", "ticker", "open", "high", "low", "close", "adj_close", "volume"]
    for optional_column in ("source", "source_ref", "retrieved_at", "as_of_date", "notes"):
        if optional_column in valid.columns:
            output_columns.append(optional_column)
    valid = valid.reindex(columns=output_columns)

    lineage_summary = _price_lineage_summary(valid)
    if lineage_summary["lineage_review_required_rows"]:
        warnings.append(
            "Price lineage review required for "
            f"{lineage_summary['lineage_review_required_rows']} valid row(s); missing or invalid fields: "
            + ", ".join(lineage_summary["lineage_missing_fields"])
            + "."
        )
    status = "valid_with_warnings" if warnings else "valid"
    return (
        valid,
        {
            "status": status,
            "missing_required_columns": [],
            "unknown_columns": unknown_columns,
            "warnings": warnings,
            "row_count": len(frame),
            "valid_rows": len(valid),
            "skipped_rows": skipped_invalid + duplicate_rows,
            "duplicate_rows": duplicate_rows,
            "affected_tickers": sorted(valid["ticker"].dropna().unique().tolist()),
            **lineage_summary,
            **temporal_summary,
        },
    )


def validate_price_imports(
    base_dir: Path | None = None,
    *,
    data_dir: Path | None = None,
    import_dir: Path | None = None,
    rights_registry: Mapping[str, SourceRights] | None = None,
    review_cutoff: str | None = None,
) -> dict[str, Any]:
    base_dir = resolve_project_root(base_dir)
    data_dir = resolve_data_dir(data_dir, base_dir)
    import_dir = _resolve_import_dir(data_dir, import_dir)
    rights_registry = rights_registry if rights_registry is not None else load_source_rights_registry()
    staged_path = import_dir / "prices.csv"
    if not staged_path.exists():
        return {
            "status": "no_staged_file",
            "staged_path": str(staged_path),
            "canonical_path": str(data_dir / "prices.csv"),
            "row_count": 0,
            "valid_rows": 0,
            "skipped_rows": 0,
            "duplicate_rows": 0,
            "affected_tickers": [],
            "missing_required_columns": PRICE_IMPORT_REQUIRED_COLUMNS,
            "unknown_columns": [],
            "warnings": ["No price import file found at data/imports/prices.csv."],
            **_price_lineage_summary(pd.DataFrame()),
            **_price_temporal_summary(pd.DataFrame(), review_cutoff=review_cutoff)[1],
            **_price_source_evidence_summary(pd.DataFrame(), rights_registry),
        }
    staged_frame, read_warnings = _read_price_import(staged_path)
    valid_frame, summary = _normalize_price_import_frame(
        staged_frame,
        review_cutoff=review_cutoff,
    )
    return {
        **summary,
        **_price_source_evidence_summary(valid_frame, rights_registry),
        "staged_path": str(staged_path),
        "canonical_path": str(data_dir / "prices.csv"),
        "warnings": read_warnings + summary["warnings"],
        "valid_frame": valid_frame,
    }


def _load_canonical_price_frame(path: Path) -> pd.DataFrame:
    frame = _read_csv_if_present(path)
    if frame.empty:
        return pd.DataFrame(columns=PRICE_COLUMNS)
    if "ticker" in frame.columns:
        frame["ticker"] = _normalize_ticker_series(frame["ticker"])
    if "date" in frame.columns:
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce", format="mixed").apply(_serialize_price_date)
    return frame


def _price_key_series(frame: pd.DataFrame) -> pd.Series:
    return frame[["date", "ticker"]].astype(str).agg("||".join, axis=1)


def preview_price_import_merge(
    base_dir: Path | None = None,
    *,
    data_dir: Path | None = None,
    import_dir: Path | None = None,
    rights_registry: Mapping[str, SourceRights] | None = None,
    review_cutoff: str | None = None,
) -> dict[str, Any]:
    preview, _ = _prepare_price_import_merge(
        base_dir,
        data_dir=data_dir,
        import_dir=import_dir,
        rights_registry=rights_registry,
        review_cutoff=review_cutoff,
    )
    return preview


def _prepare_price_import_merge(
    base_dir: Path | None = None,
    *,
    data_dir: Path | None = None,
    import_dir: Path | None = None,
    rights_registry: Mapping[str, SourceRights] | None = None,
    review_cutoff: str | None = None,
) -> tuple[dict[str, Any], pd.DataFrame]:
    base_dir = resolve_project_root(base_dir)
    data_dir = resolve_data_dir(data_dir, base_dir)
    validation = validate_price_imports(
        base_dir,
        data_dir=data_dir,
        import_dir=import_dir,
        rights_registry=rights_registry,
        review_cutoff=review_cutoff,
    )
    valid_frame = validation.pop("valid_frame", pd.DataFrame())
    if validation["status"] == "no_staged_file":
        return ({**validation, "new_rows": 0, "updated_rows": 0, "unchanged_rows": 0, "skipped_rows": 0}, valid_frame)
    if validation["status"] == "invalid":
        return ({**validation, "new_rows": 0, "updated_rows": 0, "unchanged_rows": 0}, valid_frame)

    canonical = _load_canonical_price_frame(Path(validation["canonical_path"]))
    canonical_keys = _price_key_series(canonical) if not canonical.empty and {"date", "ticker"}.issubset(canonical.columns) else pd.Series(dtype="object")
    canonical_lookup = canonical.assign(_merge_key=canonical_keys).set_index("_merge_key") if not canonical.empty else pd.DataFrame()
    staged_keys = _price_key_series(valid_frame)
    new_rows = 0
    updated_rows = 0
    unchanged_rows = 0
    overwrite_keys: list[str] = []
    new_keys: list[str] = []
    compare_columns = [column for column in PRICE_IMPORT_OUTPUT_COLUMNS if column not in {"date", "ticker"} and column in valid_frame.columns]
    for _, staged_row in valid_frame.assign(_merge_key=staged_keys).iterrows():
        merge_key = staged_row["_merge_key"]
        key_text = f"date={staged_row['date']}, ticker={staged_row['ticker']}"
        if canonical_lookup.empty or merge_key not in canonical_lookup.index:
            new_rows += 1
            new_keys.append(key_text)
            continue
        canonical_row = canonical_lookup.loc[merge_key]
        if isinstance(canonical_row, pd.DataFrame):
            canonical_row = canonical_row.iloc[-1]
        changed = False
        for column in compare_columns:
            left = staged_row.get(column)
            right = canonical_row.get(column)
            if pd.isna(left) and pd.isna(right):
                continue
            if str(left) != str(right):
                changed = True
                break
        if changed:
            updated_rows += 1
            overwrite_keys.append(key_text)
        else:
            unchanged_rows += 1

    return (
        {
            **validation,
            "new_rows": new_rows,
            "updated_rows": updated_rows,
            "unchanged_rows": unchanged_rows,
            "overwrite_keys": overwrite_keys,
            "new_keys": new_keys,
        },
        valid_frame,
    )


def _backup_price_file(path: Path, data_dir: Path) -> str | None:
    if not path.exists():
        return None
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = data_dir / "backups" / timestamp
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / path.name
    shutil.copy2(path, backup_path)
    return str(backup_path)


def _atomic_write_price_frame(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", newline="", encoding="utf-8") as handle:
            frame.to_csv(handle, index=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def apply_price_import_merge(
    base_dir: Path | None = None,
    *,
    data_dir: Path | None = None,
    import_dir: Path | None = None,
    backup: bool = True,
    commercial_mode: bool | None = None,
    rights_registry: Mapping[str, SourceRights] | None = None,
    review_cutoff: str | None = None,
) -> dict[str, Any]:
    base_dir = resolve_project_root(base_dir)
    data_dir = resolve_data_dir(data_dir, base_dir)
    commercial_mode = commercial_mode if commercial_mode is not None else commercial_mode_enabled()
    preview, staged = _prepare_price_import_merge(
        base_dir,
        data_dir=data_dir,
        import_dir=import_dir,
        rights_registry=rights_registry,
        review_cutoff=review_cutoff,
    )
    if preview["status"] in {"no_staged_file", "invalid"}:
        return {
            **preview,
            "applied": False,
            "apply_status": "technical_validation_required",
            "apply_blockers": [],
            "backup_path": None,
        }

    apply_blockers: list[str] = []
    if preview["price_temporal_invalid_rows"]:
        apply_blockers.append("price_temporal_review_required")
    if commercial_mode:
        if preview["lineage_status"] != "lineage_complete":
            apply_blockers.append("price_lineage_review_required")
        if (
            preview["price_temporal_status"] != "temporal_complete"
            and "price_temporal_review_required" not in apply_blockers
        ):
            apply_blockers.append("price_temporal_review_required")
        if preview["commercial_rights_status"] != "rights_approved":
            apply_blockers.append("commercial_rights_review_required")
        if preview["price_scope_status"] != "price_scope_complete":
            apply_blockers.append("registered_price_scope_review_required")
    if apply_blockers:
        return {
            **preview,
            "applied": False,
            "apply_status": (
                "technical_temporal_validation_required"
                if preview["price_temporal_invalid_rows"]
                else "commercial_evidence_review_required"
            ),
            "apply_blockers": apply_blockers,
            "backup_path": None,
        }

    canonical_path = Path(preview["canonical_path"])
    canonical = _load_canonical_price_frame(canonical_path)
    output_columns = list(canonical.columns)
    for column in PRICE_IMPORT_OUTPUT_COLUMNS:
        if column in staged.columns and column not in output_columns:
            output_columns.append(column)
    if not output_columns:
        output_columns = PRICE_IMPORT_OUTPUT_COLUMNS
    canonical = canonical.reindex(columns=output_columns)
    staged = staged.reindex(columns=output_columns)

    backup_path = _backup_price_file(canonical_path, data_dir) if backup and (preview["new_rows"] or preview["updated_rows"]) else None
    if canonical.empty:
        merged = staged.copy()
    else:
        canonical_indexed = canonical.set_index(["date", "ticker"], drop=False).astype(object)
        staged_indexed = staged.set_index(["date", "ticker"], drop=False).astype(object)
        overlapping = canonical_indexed.index.intersection(staged_indexed.index)
        update_columns = [column for column in staged_indexed.columns if column not in {"date", "ticker"}]
        if len(overlapping) and update_columns:
            canonical_indexed.loc[overlapping, update_columns] = staged_indexed.loc[overlapping, update_columns]
        new_rows = staged_indexed.loc[~staged_indexed.index.isin(canonical_indexed.index)]
        merged = pd.concat([canonical_indexed, new_rows], axis=0).reset_index(drop=True)
    if {"ticker", "date"}.issubset(merged.columns):
        merged = merged.sort_values(["ticker", "date"]).reset_index(drop=True)
    _atomic_write_price_frame(merged, canonical_path)
    return {
        **preview,
        "applied": True,
        "apply_status": "applied",
        "apply_blockers": [],
        "backup_path": backup_path,
        "rows_written": len(merged),
    }


def _print_price_import_summary(summary: dict[str, Any]) -> None:
    printable = {key: value for key, value in summary.items() if key != "valid_frame"}
    for key, value in printable.items():
        print(f"{key}: {value}")


def show_price_update_status(
    base_dir: Path | None = None,
    *,
    output_dir: Path | None = None,
    tickers: list[str] | None = None,
    top_n: int | None = None,
) -> dict[str, Any]:
    base_dir = resolve_project_root(base_dir)
    output_dir = resolve_outputs_dir(output_dir, base_dir)
    path = output_dir / "price_update_status.csv"
    if not path.exists():
        return {
            "status": "missing_file",
            "path": str(path),
            "rows": [],
            "warnings": [
                "Price update status has not been generated yet. Start with make status, then follow the printed price focus or runbook path. For downloaded files, use make price-normalize, then run make price-validate, make price-preview, and make price-apply."
            ],
        }
    frame = pd.read_csv(path)
    frame = enrich_price_update_status_frame(frame)
    if tickers and "ticker" in frame.columns:
        allowed = {str(ticker).upper().strip() for ticker in tickers if str(ticker).strip()}
        frame = frame[frame["ticker"].astype(str).str.upper().isin(allowed)]
    if top_n is not None:
        frame = frame.head(max(top_n, 0))
    return {
        "status": "available",
        "path": str(path),
        "rows": frame.to_dict(orient="records"),
        "warnings": [],
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Update local CSV price history from a free daily source.")
    parser.add_argument("--project-root", help="Project root for config.yaml and default data directory.")
    parser.add_argument("--data-dir", help="Optional data directory. Relative paths resolve from project root.")
    parser.add_argument("--output-dir", help="Optional output directory. Relative paths resolve from project root.")
    parser.add_argument("--tickers", help="Comma-separated ticker list for targeted updates.")
    parser.add_argument("--max-tickers", type=int, help="Limit the number of tickers updated for broad-universe refreshes.")
    parser.add_argument("--chunk-size", type=int, default=50, help="Tickers per chunk during updates.")
    parser.add_argument("--refresh", action="store_true", help="Refresh even if local ticker data already looks fresh.")
    parser.add_argument("--missing-only", action="store_true", help="For broad refreshes, select tickers without local price coverage before applying --max-tickers.")
    parser.add_argument("--freshness-days", type=int, default=1, help="Skip tickers updated within this many days unless --refresh is used.")
    parser.add_argument("--universe-file", help="Alternate universe file to derive tickers from.")
    parser.add_argument(
        "--provider",
        choices=["auto", "stooq", "yahoo", "ibkr", "fmp", "alpha_vantage", "finnhub"],
        default="auto",
        help=(
            "Remote price provider. Auto tries Stooq, Yahoo, configured IBKR read-only daily bars, "
            "then configured FMP/Alpha Vantage/Finnhub fallbacks; "
            "remote providers are research-grade and should be reviewed."
        ),
    )
    parser.add_argument("--validate-price-imports", action="store_true", help="Validate data/imports/prices.csv without mutating data/prices.csv.")
    parser.add_argument("--preview-price-import-merge", action="store_true", help="Preview price import file changes without mutating data/prices.csv.")
    parser.add_argument("--apply-price-import-merge", action="store_true", help="Apply price import file rows into data/prices.csv with a backup.")
    parser.add_argument("--review-cutoff", help="Explicit timezone-aware cutoff for staged price retrieval review.")
    parser.add_argument("--price-status", action="store_true", help="Display outputs/price_update_status.csv if present.")
    parser.add_argument("--top-n", type=int, help="Optional cap for human-readable price status rows.")
    parser.add_argument("--json", action="store_true", help="Print JSON for import/status commands.")
    args = parser.parse_args()
    if args.top_n is not None and args.top_n <= 0:
        parser.error("--top-n must be a positive integer")
    if args.max_tickers is not None and args.max_tickers <= 0:
        parser.error("--max-tickers must be a positive integer")

    explicit_tickers = [ticker.strip() for ticker in args.tickers.split(",") if ticker.strip()] if args.tickers else None
    project_root = resolve_project_root(args.project_root)
    data_dir = resolve_data_dir(args.data_dir, project_root)
    output_dir = resolve_outputs_dir(args.output_dir, project_root)

    if args.validate_price_imports:
        summary = validate_price_imports(
            project_root,
            data_dir=data_dir,
            review_cutoff=args.review_cutoff,
        )
        if args.json:
            print(json.dumps({key: value for key, value in summary.items() if key != "valid_frame"}, indent=2))
        else:
            print(format_path_context(project_root, data_dir, output_dir))
            _print_price_import_summary(summary)
        return

    if args.preview_price_import_merge:
        summary = preview_price_import_merge(
            project_root,
            data_dir=data_dir,
            review_cutoff=args.review_cutoff,
        )
        if args.json:
            print(json.dumps(summary, indent=2))
        else:
            print(format_path_context(project_root, data_dir, output_dir))
            _print_price_import_summary(summary)
        return

    if args.apply_price_import_merge:
        summary = apply_price_import_merge(
            project_root,
            data_dir=data_dir,
            review_cutoff=args.review_cutoff,
        )
        if args.json:
            print(json.dumps(summary, indent=2))
        else:
            print(format_path_context(project_root, data_dir, output_dir))
            _print_price_import_summary(summary)
        return

    if args.price_status:
        summary = show_price_update_status(project_root, output_dir=output_dir, tickers=explicit_tickers, top_n=args.top_n)
        if args.json:
            print(json.dumps(summary, indent=2))
        else:
            print(format_path_context(project_root, data_dir, output_dir))
            print("Price status summary:")
            print(f"status: {summary['status']}")
            print(f"path: {summary['path']}")
            rows = summary.get("rows", [])
            if rows:
                frame = pd.DataFrame(rows)
                display_columns = [
                    column
                    for column in [
                        "ticker",
                        "status",
                        "rows_fetched",
                        "rows_merged",
                        "recommended_action",
                        "focus_command",
                        "example_command",
                    ]
                    if column in frame.columns
                ]
                print(frame[display_columns].to_string(index=False))
            for warning in summary.get("warnings", []):
                print(f"warning: {warning}")
        return

    def print_progress(event: dict[str, object]) -> None:
        if event.get("event") == "chunk_complete":
            print(
                "Chunk "
                f"{event['chunk_index']}/{event['chunks_total']} complete: "
                f"updated={event['updated_so_far']} missing={event['missing_so_far']}"
            )

    result = update_local_price_data(
        base_dir=project_root,
        source=make_price_source(args.provider),
        data_dir=data_dir,
        output_dir=output_dir,
        tickers=explicit_tickers,
        max_tickers=args.max_tickers,
        chunk_size=args.chunk_size,
        refresh=args.refresh,
        freshness_days=args.freshness_days,
        universe_file=Path(args.universe_file) if args.universe_file else None,
        missing_only=args.missing_only,
        progress_callback=print_progress,
    )
    print(format_path_context(project_root, data_dir, None))
    print(f"Updated local price file: {result.path}")
    print(f"Tickers requested: {len(result.tickers_requested)}")
    print(f"Tickers updated: {len(result.tickers_updated)}")
    print(f"Chunks processed: {result.chunks_processed}")
    print(f"Rows written: {result.rows_written}")
    if result.status_path is not None:
        print(f"Price update status: {result.status_path}")
    if result.tickers_skipped_fresh:
        print("Tickers skipped as fresh:")
        for ticker in result.tickers_skipped_fresh:
            print(f"- {ticker}")
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
