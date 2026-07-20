import json
import sys
from pathlib import Path

import pandas as pd
import pytest

import src.data_update as data_update

from src.data_update import (
    AlphaVantageDailyPriceSource,
    FMPDailyPriceSource,
    FinnhubDailyPriceSource,
    IBKRDailyPriceSource,
    PriceSourceLadder,
    StooqDailyPriceSource,
    YahooChartDailyPriceSource,
    apply_price_import_merge,
    enrich_price_update_status_frame,
    load_update_tickers,
    main,
    make_price_source,
    preview_price_import_merge,
    refresh_price_update_status_output,
    show_price_update_status,
    update_local_price_data,
    validate_price_imports,
)
from src.commercial_source_rights import build_source_rights_registry
from src.provider_env import reset_provider_environment_cache


class FakePriceSource:
    def __init__(
        self,
        payloads: dict[str, pd.DataFrame | None],
        *,
        source_id: str = "fake_price_source",
    ) -> None:
        self.payloads = payloads
        self.source_id = source_id
        self.calls: list[str] = []

    def fetch_history(self, ticker: str) -> tuple[pd.DataFrame, list[str]]:
        self.calls.append(ticker)
        payload = self.payloads.get(ticker)
        if payload is None:
            return pd.DataFrame(), [f"{ticker}: source unavailable"]
        return payload.copy(), []


class FakeHTTPResponse:
    def __init__(self, payload: str) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return self.payload.encode("utf-8")


class FakeIBKRClient:
    def __init__(self, bars=None, *, connect_error: Exception | None = None) -> None:
        self.bars = bars or []
        self.connect_error = connect_error
        self.calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    def connect(self, *args, **kwargs):
        self.calls.append(("connect", args, kwargs))
        if self.connect_error:
            raise self.connect_error
        return True

    def disconnect(self):
        self.calls.append(("disconnect", (), {}))

    def reqHistoricalData(self, *args, **kwargs):
        self.calls.append(("reqHistoricalData", args, kwargs))
        return list(self.bars)

    def placeOrder(self, *_args, **_kwargs):  # pragma: no cover - guard method for negative assertions
        raise AssertionError("IBKR price provider must never call trading APIs.")

    def cancelOrder(self, *_args, **_kwargs):  # pragma: no cover - guard method for negative assertions
        raise AssertionError("IBKR price provider must never call trading APIs.")


class FakeIBKRBar:
    def __init__(self, date, open, high, low, close, volume) -> None:
        self.date = date
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume


def _commercial_price_registry(
    source_id: str,
    *,
    commercial_use: str = "approved",
    supported_fields: list[str] | None = None,
):
    return build_source_rights_registry(
        [
            {
                "source_id": source_id,
                "display_name": f"{source_id} test source",
                "permitted_use": "reviewed_price_research",
                "commercial_use": commercial_use,
                "redistribution": "derived_data_only",
                "storage_limits": "reviewed rows only",
                "attribution": "durable source reference required",
                "rate_limits": "test fixture only",
                "authentication": "test fixture only",
                "expected_freshness": "fixture timestamp",
                "supported_fields": supported_fields or ["prices"],
                "fallback_priority": 1,
            }
        ]
    )


def test_stooq_source_reports_api_key_page_without_parser_failure():
    def opener(_url: str, timeout: int):
        assert timeout == 20
        return FakeHTTPResponse(
            "Get your apikey:\n"
            "1. Open https://stooq.com/q/d/?s=meta.us&get_apikey\n"
            "2. Enter the captcha code.\n"
        )

    frame, warnings = StooqDailyPriceSource(opener=opener).fetch_history("META")

    assert frame.empty
    assert "requires an API key" in warnings[0]
    assert "Error tokenizing data" not in warnings[0]


def test_stooq_source_passes_configured_api_key_to_download_url(monkeypatch):
    seen: dict[str, str] = {}

    def opener(url: str, timeout: int):
        seen["url"] = url
        return FakeHTTPResponse(
            "Date,Open,High,Low,Close,Volume\n"
            "2026-01-02,100,102,99,101,12345\n"
        )

    monkeypatch.setenv("STOOQ_API_KEY", "abc123")
    frame, warnings = StooqDailyPriceSource(opener=opener).fetch_history("META")

    assert warnings == []
    assert "apikey=abc123" in seen["url"]
    assert frame.iloc[0]["ticker"] == "META"
    assert frame.iloc[0]["adj_close"] == 101


def test_yahoo_chart_source_normalizes_daily_rows():
    def opener(request, timeout: int):
        assert timeout == 20
        assert "query1.finance.yahoo.com" in request.full_url
        return FakeHTTPResponse(
            json.dumps(
                {
                    "chart": {
                        "result": [
                            {
                                "timestamp": [1767312000, 1767398400],
                                "indicators": {
                                    "quote": [
                                        {
                                            "open": [100.0, 101.0],
                                            "high": [102.0, 103.0],
                                            "low": [99.0, 100.0],
                                            "close": [101.0, 102.0],
                                            "volume": [12345, 23456],
                                        }
                                    ],
                                    "adjclose": [{"adjclose": [100.5, 101.5]}],
                                },
                            }
                        ],
                        "error": None,
                    }
                }
            )
        )

    frame, warnings = YahooChartDailyPriceSource(opener=opener).fetch_history("AMD")

    assert len(frame) == 2
    assert list(frame.columns) == ["date", "ticker", "open", "high", "low", "close", "adj_close", "volume"]
    assert frame.iloc[0]["ticker"] == "AMD"
    assert frame.iloc[0]["adj_close"] == 100.5
    assert "unofficial Yahoo chart endpoint" in warnings[0]


def test_yahoo_chart_source_uses_provider_symbol_alias_but_preserves_local_ticker():
    seen: dict[str, str] = {}

    def opener(request, timeout: int):
        assert timeout == 20
        seen["url"] = request.full_url
        return FakeHTTPResponse(
            json.dumps(
                {
                    "chart": {
                        "result": [
                            {
                                "timestamp": [1767312000],
                                "indicators": {
                                    "quote": [
                                        {
                                            "open": [500.0],
                                            "high": [505.0],
                                            "low": [499.0],
                                            "close": [503.0],
                                            "volume": [12345],
                                        }
                                    ],
                                    "adjclose": [{"adjclose": [503.0]}],
                                },
                            }
                        ],
                        "error": None,
                    }
                }
            )
        )

    frame, warnings = YahooChartDailyPriceSource(opener=opener).fetch_history("BRK.B")

    assert "/BRK-B?" in seen["url"]
    assert frame.iloc[0]["ticker"] == "BRK.B"
    assert "provider symbol BRK-B" in warnings[0]


def test_fmp_price_source_normalizes_historical_rows():
    def opener(request, timeout: int):
        assert timeout == 20
        assert "historical-price-full/META" in request.full_url
        assert "apikey=demo" in request.full_url
        return FakeHTTPResponse(
            json.dumps(
                {
                    "historical": [
                        {
                            "date": "2026-01-03",
                            "open": 100.0,
                            "high": 102.0,
                            "low": 99.0,
                            "close": 101.0,
                            "adjClose": 100.5,
                            "volume": 12345,
                        }
                    ]
                }
            )
        )

    frame, warnings = FMPDailyPriceSource(api_key="demo", opener=opener).fetch_history("META")

    assert warnings == [
        "META: prices refreshed from FMP historical price endpoint; treat as research-grade and verify if used for decisions."
    ]
    assert len(frame) == 1
    assert frame.iloc[0]["ticker"] == "META"
    assert frame.iloc[0]["adj_close"] == 100.5


def test_alpha_vantage_price_source_normalizes_daily_adjusted_rows():
    def opener(request, timeout: int):
        assert timeout == 20
        assert "function=TIME_SERIES_DAILY_ADJUSTED" in request.full_url
        assert "symbol=META" in request.full_url
        assert "apikey=demo" in request.full_url
        return FakeHTTPResponse(
            json.dumps(
                {
                    "Time Series (Daily)": {
                        "2026-01-03": {
                            "1. open": "100.0",
                            "2. high": "102.0",
                            "3. low": "99.0",
                            "4. close": "101.0",
                            "5. adjusted close": "100.5",
                            "6. volume": "12345",
                        }
                    }
                }
            )
        )

    frame, warnings = AlphaVantageDailyPriceSource(api_key="demo", opener=opener).fetch_history("META")

    assert warnings == [
        "META: prices refreshed from Alpha Vantage daily adjusted endpoint; treat as research-grade and verify if used for decisions."
    ]
    assert len(frame) == 1
    assert frame.iloc[0]["ticker"] == "META"
    assert frame.iloc[0]["adj_close"] == 100.5


def test_finnhub_price_source_normalizes_daily_candle_rows():
    def opener(request, timeout: int):
        assert timeout == 20
        assert "stock/candle" in request.full_url
        assert "symbol=META" in request.full_url
        assert "resolution=D" in request.full_url
        assert "token=demo" in request.full_url
        return FakeHTTPResponse(
            json.dumps(
                {
                    "s": "ok",
                    "t": [1767398400],
                    "o": [100.0],
                    "h": [102.0],
                    "l": [99.0],
                    "c": [101.0],
                    "v": [12345],
                }
            )
        )

    frame, warnings = FinnhubDailyPriceSource(api_key="demo", opener=opener).fetch_history("META")

    assert warnings == [
        "META: prices refreshed from Finnhub daily candle endpoint; treat as research-grade and verify if used for decisions."
    ]
    assert len(frame) == 1
    assert frame.iloc[0]["ticker"] == "META"
    assert frame.iloc[0]["adj_close"] == 101.0


def test_ibkr_price_source_normalizes_read_only_daily_bars():
    client = FakeIBKRClient(
        bars=[
            FakeIBKRBar("2026-01-02", 100.0, 102.0, 99.0, 101.0, 12345),
            FakeIBKRBar("2026-01-03", 101.0, 103.0, 100.0, 102.0, 23456),
        ]
    )

    source = IBKRDailyPriceSource(
        host="127.0.0.1",
        port=7497,
        client_id=42,
        ib_factory=lambda: client,
        contract_factory=lambda symbol, exchange, currency: {
            "symbol": symbol,
            "exchange": exchange,
            "currency": currency,
        },
    )

    frame, warnings = source.fetch_history("msft")

    assert len(frame) == 2
    assert list(frame.columns) == ["date", "ticker", "open", "high", "low", "close", "adj_close", "volume"]
    assert frame.iloc[0]["ticker"] == "MSFT"
    assert frame.iloc[0]["adj_close"] == 101.0
    assert client.calls[0] == (
        "connect",
        ("127.0.0.1", 7497),
        {"clientId": 42, "timeout": 4, "readonly": True},
    )
    historical_call = [call for call in client.calls if call[0] == "reqHistoricalData"][0]
    assert historical_call[2]["barSizeSetting"] == "1 day"
    assert historical_call[2]["whatToShow"] == "TRADES"
    assert historical_call[2]["keepUpToDate"] is False
    assert [call[0] for call in client.calls] == ["connect", "reqHistoricalData", "disconnect"]
    assert "IBKR historical daily bars" in warnings[0]
    assert "read-only market data" in warnings[0]


def test_ibkr_price_source_reports_dependency_or_gateway_unavailable():
    missing_dependency = IBKRDailyPriceSource(ib_factory=None, module_loader=lambda _name: (_ for _ in ()).throw(ImportError("No module named ib_insync")))
    frame, warnings = missing_dependency.fetch_history("MSFT")

    assert frame.empty
    assert "ib_insync is not installed" in warnings[0]

    client = FakeIBKRClient(connect_error=ConnectionRefusedError("gateway down"))
    source = IBKRDailyPriceSource(ib_factory=lambda: client, contract_factory=lambda *_args: object())
    frame, warnings = source.fetch_history("MSFT")

    assert frame.empty
    assert "IBKR Gateway/TWS is unavailable" in warnings[0]


def test_ibkr_price_source_exposes_no_trading_methods():
    source = IBKRDailyPriceSource(ib_factory=lambda: FakeIBKRClient(), contract_factory=lambda *_args: object())

    for forbidden in ("place_order", "placeOrder", "cancel_order", "cancelOrder", "submit_order", "get_account"):
        assert not hasattr(source, forbidden)


def test_price_source_ladder_tries_stooq_after_yahoo_has_no_rows():
    yahoo = FakePriceSource({"META": None}, source_id="yahoo")
    stooq = FakePriceSource(
        {
            "META": pd.DataFrame(
                [
                    {
                        "date": pd.Timestamp("2026-01-03"),
                        "ticker": "META",
                        "open": 100.0,
                        "high": 102.0,
                        "low": 99.0,
                        "close": 101.0,
                        "adj_close": 101.0,
                        "volume": 12345,
                    }
                ]
            )
        },
        source_id="stooq",
    )

    frame, warnings = PriceSourceLadder([("yahoo", yahoo), ("stooq", stooq)]).fetch_history("META")

    assert yahoo.calls == ["META"]
    assert stooq.calls == ["META"]
    assert not frame.empty
    assert frame.iloc[0]["ticker"] == "META"
    assert "source ladder resolved price rows from stooq after yahoo failed" in warnings[-1]


def test_update_local_price_data_records_auto_price_ladder_provider(tmp_path: Path):
    (tmp_path / "data").mkdir()
    (tmp_path / "config.yaml").write_text(Path("config.yaml").read_text(), encoding="utf-8")
    yahoo = FakePriceSource({"META": None}, source_id="yahoo")
    stooq = FakePriceSource(
        {
            "META": pd.DataFrame(
                [
                    {
                        "date": pd.Timestamp("2026-01-03"),
                        "ticker": "META",
                        "open": 100.0,
                        "high": 102.0,
                        "low": 99.0,
                        "close": 101.0,
                        "adj_close": 101.0,
                        "volume": 12345,
                    }
                ]
            )
        },
        source_id="stooq",
    )
    source = PriceSourceLadder([("yahoo", yahoo), ("stooq", stooq)])

    result = update_local_price_data(tmp_path, source=source, tickers=["META"])

    status = pd.read_csv(result.status_path)
    assert result.tickers_updated == ["META"]
    assert status.iloc[0]["provider"] == "stooq"
    assert any("source ladder resolved price rows from stooq" in warning for warning in result.warnings)


def test_make_price_source_auto_builds_stooq_then_yahoo_ladder(tmp_path: Path, monkeypatch):
    for key in ("FMP_API_KEY", "ALPHA_VANTAGE_API_KEY", "FINNHUB_API_KEY", "IBKR_HOST", "IBKR_PORT", "IBKR_CLIENT_ID"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.chdir(tmp_path)
    reset_provider_environment_cache()

    source = make_price_source("auto")

    assert isinstance(source, PriceSourceLadder)
    assert source.provider_names == ["stooq", "yahoo"]


def test_make_price_source_auto_adds_configured_keyed_price_fallbacks(monkeypatch):
    reset_provider_environment_cache()
    monkeypatch.delenv("IBKR_HOST", raising=False)
    monkeypatch.delenv("IBKR_PORT", raising=False)
    monkeypatch.delenv("IBKR_CLIENT_ID", raising=False)
    monkeypatch.setenv("FMP_API_KEY", "fmp-demo")
    monkeypatch.setenv("ALPHA_VANTAGE_API_KEY", "alpha-demo")
    monkeypatch.setenv("FINNHUB_API_KEY", "finnhub-demo")

    source = make_price_source("auto")

    assert isinstance(source, PriceSourceLadder)
    assert source.provider_names == ["stooq", "yahoo", "fmp", "alpha_vantage", "finnhub"]


def test_make_price_source_auto_adds_configured_ibkr_before_keyed_price_fallbacks(monkeypatch):
    reset_provider_environment_cache()
    monkeypatch.setenv("IBKR_HOST", "127.0.0.1")
    monkeypatch.setenv("IBKR_PORT", "7497")
    monkeypatch.setenv("IBKR_CLIENT_ID", "42")
    monkeypatch.setenv("FMP_API_KEY", "fmp-demo")

    source = make_price_source("auto")

    assert isinstance(source, PriceSourceLadder)
    assert source.provider_names == ["stooq", "yahoo", "ibkr", "fmp"]


def test_price_sources_expose_exact_source_ids():
    assert StooqDailyPriceSource.source_id == "stooq"
    assert YahooChartDailyPriceSource.source_id == "yahoo"
    assert FMPDailyPriceSource.source_id == "fmp"
    assert AlphaVantageDailyPriceSource.source_id == "alpha_vantage"
    assert FinnhubDailyPriceSource.source_id == "finnhub"
    assert IBKRDailyPriceSource.source_id == "ibkr"


def test_price_source_ladder_rejects_label_that_does_not_match_exact_source_id():
    source = FakePriceSource({}, source_id="stooq")

    with pytest.raises(ValueError, match="price source label/source_id mismatch"):
        PriceSourceLadder([("yahoo", source)])


def test_make_price_source_blocks_unapproved_exact_provider_in_commercial_mode():
    registry = _commercial_price_registry("stooq", commercial_use="unverified")

    with pytest.raises(RuntimeError, match="commercial_price_source_review_required.*stooq"):
        make_price_source("stooq", commercial_mode=True, rights_registry=registry)


def test_make_price_source_blocks_provider_without_registered_price_scope():
    registry = _commercial_price_registry("stooq", supported_fields=["revenue"])

    with pytest.raises(RuntimeError, match="commercial_price_scope_review_required.*stooq"):
        make_price_source("stooq", commercial_mode=True, rights_registry=registry)


def test_make_price_source_commercial_auto_keeps_only_independently_eligible_legs(monkeypatch):
    for key in ("FMP_API_KEY", "ALPHA_VANTAGE_API_KEY", "FINNHUB_API_KEY", "IBKR_HOST", "IBKR_PORT", "IBKR_CLIENT_ID"):
        monkeypatch.delenv(key, raising=False)
    reset_provider_environment_cache()
    registry = _commercial_price_registry("stooq")

    source = make_price_source("auto", commercial_mode=True, rights_registry=registry)

    assert isinstance(source, PriceSourceLadder)
    assert source.provider_names == ["stooq"]
    assert source.source_ids == ("stooq",)


def test_make_price_source_commercial_auto_fails_when_no_leg_is_eligible(monkeypatch):
    for key in ("FMP_API_KEY", "ALPHA_VANTAGE_API_KEY", "FINNHUB_API_KEY", "IBKR_HOST", "IBKR_PORT", "IBKR_CLIENT_ID"):
        monkeypatch.delenv(key, raising=False)
    reset_provider_environment_cache()
    registry = _commercial_price_registry("unrelated_source")

    with pytest.raises(RuntimeError, match="commercial_price_source_review_required.*stooq.*yahoo"):
        make_price_source("auto", commercial_mode=True, rights_registry=registry)


def test_commercial_price_update_blocks_missing_identity_before_fetch_or_output(tmp_path: Path):
    class MissingIdentitySource:
        def __init__(self) -> None:
            self.calls = 0

        def fetch_history(self, _ticker: str):
            self.calls += 1
            return pd.DataFrame(), []

    source = MissingIdentitySource()

    with pytest.raises(RuntimeError, match="commercial_price_source_id_required"):
        update_local_price_data(
            tmp_path,
            source=source,
            tickers=["META"],
            commercial_mode=True,
            rights_registry=_commercial_price_registry("approved_prices"),
        )

    assert source.calls == 0
    assert not (tmp_path / "data" / "prices.csv").exists()
    assert not (tmp_path / "outputs" / "price_update_status.csv").exists()


def test_commercial_price_update_blocks_unapproved_source_before_fetch_or_output(tmp_path: Path):
    source = FakePriceSource({"META": None}, source_id="unverified_prices")

    with pytest.raises(RuntimeError, match="commercial_price_source_review_required.*unverified_prices"):
        update_local_price_data(
            tmp_path,
            source=source,
            tickers=["META"],
            commercial_mode=True,
            rights_registry=_commercial_price_registry(
                "unverified_prices", commercial_use="unverified"
            ),
        )

    assert source.calls == []
    assert not (tmp_path / "data" / "prices.csv").exists()
    assert not (tmp_path / "outputs" / "price_update_status.csv").exists()


def test_commercial_price_update_allows_approved_scoped_source(tmp_path: Path):
    (tmp_path / "data").mkdir()
    (tmp_path / "config.yaml").write_text(Path("config.yaml").read_text(), encoding="utf-8")
    source = FakePriceSource(
        {
            "META": pd.DataFrame(
                [
                    {
                        "date": pd.Timestamp("2026-01-03"),
                        "ticker": "META",
                        "open": 100.0,
                        "high": 102.0,
                        "low": 99.0,
                        "close": 101.0,
                        "adj_close": 101.0,
                        "volume": 12345,
                    }
                ]
            )
        },
        source_id="approved_prices",
    )

    result = update_local_price_data(
        tmp_path,
        source=source,
        tickers=["META"],
        commercial_mode=True,
        rights_registry=_commercial_price_registry("approved_prices"),
    )

    assert result.tickers_updated == ["META"]
    assert result.path.exists()
    assert result.status_path is not None and result.status_path.exists()


def test_commercial_price_update_blocks_changed_identity_before_mutation(tmp_path: Path):
    (tmp_path / "data").mkdir()
    (tmp_path / "config.yaml").write_text(Path("config.yaml").read_text(), encoding="utf-8")

    class ChangedIdentitySource(FakePriceSource):
        def fetch_history(self, ticker: str):
            frame, warnings = super().fetch_history(ticker)
            self.source_id = "unreviewed_after_fetch"
            return frame, warnings

    source = ChangedIdentitySource(
        {
            "META": pd.DataFrame(
                [
                    {
                        "date": pd.Timestamp("2026-01-03"),
                        "ticker": "META",
                        "open": 100.0,
                        "high": 102.0,
                        "low": 99.0,
                        "close": 101.0,
                        "adj_close": 101.0,
                        "volume": 12345,
                    }
                ]
            )
        },
        source_id="approved_prices",
    )

    with pytest.raises(RuntimeError, match="commercial_price_source_changed"):
        update_local_price_data(
            tmp_path,
            source=source,
            tickers=["META"],
            commercial_mode=True,
            rights_registry=_commercial_price_registry("approved_prices"),
        )

    assert not (tmp_path / "data" / "prices.csv").exists()
    assert not (tmp_path / "outputs" / "price_update_status.csv").exists()


def test_price_refresh_cli_accepts_direct_finnhub_provider(tmp_path: Path, monkeypatch):
    (tmp_path / "data").mkdir()
    (tmp_path / "outputs").mkdir()
    (tmp_path / "config.yaml").write_text(Path("config.yaml").read_text(), encoding="utf-8")
    seen: dict[str, object] = {}

    def fake_update_local_price_data(**kwargs):
        seen["source"] = kwargs["source"]
        seen["tickers"] = kwargs["tickers"]
        return type(
            "Result",
            (),
            {
                "path": tmp_path / "data" / "prices.csv",
                "tickers_requested": ["META"],
                "tickers_updated": [],
                "tickers_missing": ["META"],
                "tickers_skipped_fresh": [],
                "chunks_processed": 0,
                "rows_written": 0,
                "status_path": tmp_path / "outputs" / "price_update_status.csv",
                "warnings": [],
            },
        )()

    monkeypatch.setattr("src.data_update.update_local_price_data", fake_update_local_price_data)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "data_update",
            "--project-root",
            str(tmp_path),
            "--tickers",
            "META",
            "--provider",
            "finnhub",
        ],
    )

    main()

    assert isinstance(seen["source"], FinnhubDailyPriceSource)
    assert seen["tickers"] == ["META"]


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


def test_update_local_price_data_processes_chunks_and_max_tickers(tmp_path: Path):
    (tmp_path / "data").mkdir()
    (tmp_path / "config.yaml").write_text(Path("config.yaml").read_text(), encoding="utf-8")

    source = FakePriceSource(
        {
            "AAA": pd.DataFrame(
                [
                    {
                        "date": pd.Timestamp("2026-01-03"),
                        "ticker": "AAA",
                        "open": 10.0,
                        "high": 11.0,
                        "low": 9.0,
                        "close": 10.5,
                        "adj_close": 10.5,
                        "volume": 1000,
                    }
                ]
            ),
            "BBB": pd.DataFrame(
                [
                    {
                        "date": pd.Timestamp("2026-01-03"),
                        "ticker": "BBB",
                        "open": 20.0,
                        "high": 21.0,
                        "low": 19.0,
                        "close": 20.5,
                        "adj_close": 20.5,
                        "volume": 1200,
                    }
                ]
            ),
            "CCC": pd.DataFrame(
                [
                    {
                        "date": pd.Timestamp("2026-01-03"),
                        "ticker": "CCC",
                        "open": 30.0,
                        "high": 31.0,
                        "low": 29.0,
                        "close": 30.5,
                        "adj_close": 30.5,
                        "volume": 1400,
                    }
                ]
            ),
        }
    )

    result = update_local_price_data(
        tmp_path,
        source=source,
        tickers=["AAA", "BBB", "CCC"],
        chunk_size=2,
        max_tickers=2,
    )

    assert result.chunks_processed == 1
    assert result.tickers_updated == ["AAA", "BBB"]
    assert source.calls == ["AAA", "BBB"]


def test_update_local_price_data_applies_missing_only_before_max_tickers(tmp_path: Path):
    (tmp_path / "data").mkdir()
    (tmp_path / "config.yaml").write_text(Path("config.yaml").read_text(), encoding="utf-8")
    (tmp_path / "data" / "prices.csv").write_text(
        "date,ticker,adj_close,volume\n"
        "2026-01-02,AAA,10,1000\n",
        encoding="utf-8",
    )

    source = FakePriceSource(
        {
            "BBB": pd.DataFrame(
                [
                    {
                        "date": pd.Timestamp("2026-01-03"),
                        "ticker": "BBB",
                        "open": 20.0,
                        "high": 21.0,
                        "low": 19.0,
                        "close": 20.5,
                        "adj_close": 20.5,
                        "volume": 1200,
                    }
                ]
            ),
            "CCC": pd.DataFrame(
                [
                    {
                        "date": pd.Timestamp("2026-01-03"),
                        "ticker": "CCC",
                        "open": 30.0,
                        "high": 31.0,
                        "low": 29.0,
                        "close": 30.5,
                        "adj_close": 30.5,
                        "volume": 1400,
                    }
                ]
            ),
        }
    )

    result = update_local_price_data(
        tmp_path,
        source=source,
        tickers=["AAA", "BBB", "CCC"],
        max_tickers=1,
        missing_only=True,
    )

    assert result.tickers_requested == ["BBB"]
    assert result.tickers_updated == ["BBB"]
    assert source.calls == ["BBB"]


def test_update_local_price_data_skips_fresh_tickers_unless_refresh_requested(tmp_path: Path):
    (tmp_path / "data").mkdir()
    (tmp_path / "config.yaml").write_text(Path("config.yaml").read_text(), encoding="utf-8")
    fresh_date = pd.Timestamp.now(tz="UTC").tz_localize(None).normalize().date().isoformat()
    (tmp_path / "data" / "prices.csv").write_text(
        "date,ticker,adj_close,volume\n"
        f"{fresh_date},SPY,100,1000\n",
        encoding="utf-8",
    )
    source = FakePriceSource({"SPY": None})

    result = update_local_price_data(tmp_path, source=source, tickers=["SPY"], freshness_days=1)

    assert result.tickers_skipped_fresh == ["SPY"]
    assert source.calls == []


def test_show_price_update_status_missing_file_uses_status_flow_guidance(tmp_path: Path):
    (tmp_path / "data").mkdir()
    (tmp_path / "outputs").mkdir()
    (tmp_path / "config.yaml").write_text(Path("config.yaml").read_text(), encoding="utf-8")

    payload = show_price_update_status(tmp_path)

    assert payload["status"] == "missing_file"
    assert "make status" in payload["warnings"][0]
    assert "make price-normalize" in payload["warnings"][0]
    assert "make price-validate" in payload["warnings"][0]
    assert "make price-preview" in payload["warnings"][0]
    assert "make price-apply" in payload["warnings"][0]


def test_show_price_update_status_enriches_legacy_rows_with_commands(tmp_path: Path):
    (tmp_path / "data").mkdir()
    (tmp_path / "outputs").mkdir()
    (tmp_path / "config.yaml").write_text(Path("config.yaml").read_text(), encoding="utf-8")
    pd.DataFrame(
        [
            {
                "run_timestamp": "2026-05-21T00:00:00+00:00",
                "ticker": "AMD",
                "requested_start": "",
                "requested_end": "2026-05-21",
                "provider": "FakePriceSource",
                "status": "parse_error",
                "rows_fetched": 0,
                "rows_merged": 0,
                "error_category": "parse_error",
                "error_message": "AMD: parse failed",
                "fallback_used": True,
                "recommended_action": "Run make focus-price TICKER=AMD first. For batch planning, preview make price-refresh-loop DRY_RUN=1; if you choose to refresh this ticker, run make price-refresh TICKERS=AMD PROVIDER=auto so Yahoo and Stooq are tried automatically; only if both provider paths fail, normalize verified downloaded OHLCV files into data/imports/prices.csv.",
            }
        ]
    ).to_csv(tmp_path / "outputs" / "price_update_status.csv", index=False)

    payload = show_price_update_status(tmp_path)

    assert payload["status"] == "available"
    row = payload["rows"][0]
    assert row["recommended_action"].startswith("Run make focus-price TICKER=AMD")
    assert "PROVIDER=auto" in row["recommended_action"]
    assert "configured FMP/Alpha Vantage/Finnhub" in row["recommended_action"]
    assert "only if every provider path fails" in row["recommended_action"]
    assert "free refresh path fails" not in row["recommended_action"]
    assert row["focus_command"] == "make focus-price TICKER=AMD"
    assert row["example_command"] == "make price-normalize INPUT=data/raw/prices/AMD.csv TICKER=AMD SOURCE=yahoo_manual"
    assert row["target_file"] == "data/imports/prices.csv"


def test_show_price_update_status_respects_top_n(tmp_path: Path):
    (tmp_path / "data").mkdir()
    (tmp_path / "outputs").mkdir()
    (tmp_path / "config.yaml").write_text(Path("config.yaml").read_text(), encoding="utf-8")
    pd.DataFrame(
        [
            {
                "run_timestamp": "2026-05-21T00:00:00+00:00",
                "ticker": "AMD",
                "requested_start": "",
                "requested_end": "2026-05-21",
                "provider": "FakePriceSource",
                "status": "parse_error",
                "rows_fetched": 0,
                "rows_merged": 0,
                "error_category": "parse_error",
                "error_message": "AMD: parse failed",
                "fallback_used": True,
                "recommended_action": "Run make focus-price TICKER=AMD first. For batch planning, preview make price-refresh-loop DRY_RUN=1; if you choose to refresh this ticker, run make price-refresh TICKERS=AMD; if the free refresh path fails, normalize verified downloaded OHLCV files into data/imports/prices.csv.",
            },
            {
                "run_timestamp": "2026-05-21T00:00:00+00:00",
                "ticker": "NVDA",
                "requested_start": "",
                "requested_end": "2026-05-21",
                "provider": "FakePriceSource",
                "status": "source_unavailable",
                "rows_fetched": 0,
                "rows_merged": 0,
                "error_category": "source_unavailable",
                "error_message": "NVDA: unavailable",
                "fallback_used": True,
                "recommended_action": "Run make focus-price TICKER=NVDA first. For batch planning, preview make price-refresh-loop DRY_RUN=1; if you choose to refresh this ticker, run make price-refresh TICKERS=NVDA; if the free refresh path fails, normalize verified downloaded OHLCV files into data/imports/prices.csv.",
            },
        ]
    ).to_csv(tmp_path / "outputs" / "price_update_status.csv", index=False)

    payload = show_price_update_status(tmp_path, top_n=1)

    assert payload["status"] == "available"
    assert len(payload["rows"]) == 1
    assert payload["rows"][0]["ticker"] == "AMD"


def test_show_price_update_status_respects_ticker_filter(tmp_path: Path):
    (tmp_path / "data").mkdir()
    (tmp_path / "outputs").mkdir()
    (tmp_path / "config.yaml").write_text(Path("config.yaml").read_text(), encoding="utf-8")
    pd.DataFrame(
        [
            {
                "run_timestamp": "2026-05-21T00:00:00+00:00",
                "ticker": "AMD",
                "requested_start": "",
                "requested_end": "2026-05-21",
                "provider": "FakePriceSource",
                "status": "parse_error",
                "rows_fetched": 0,
                "rows_merged": 0,
                "error_category": "parse_error",
                "error_message": "AMD: parse failed",
                "fallback_used": True,
                "recommended_action": "Run make focus-price TICKER=AMD first. For batch planning, preview make price-refresh-loop DRY_RUN=1; if you choose to refresh this ticker, run make price-refresh TICKERS=AMD; if the free refresh path fails, normalize verified downloaded OHLCV files into data/imports/prices.csv.",
            },
            {
                "run_timestamp": "2026-05-21T00:00:00+00:00",
                "ticker": "NVDA",
                "requested_start": "",
                "requested_end": "2026-05-21",
                "provider": "FakePriceSource",
                "status": "source_unavailable",
                "rows_fetched": 0,
                "rows_merged": 0,
                "error_category": "source_unavailable",
                "error_message": "NVDA: unavailable",
                "fallback_used": True,
                "recommended_action": "Run make focus-price TICKER=NVDA first. For batch planning, preview make price-refresh-loop DRY_RUN=1; if you choose to refresh this ticker, run make price-refresh TICKERS=NVDA; if the free refresh path fails, normalize verified downloaded OHLCV files into data/imports/prices.csv.",
            },
        ]
    ).to_csv(tmp_path / "outputs" / "price_update_status.csv", index=False)

    payload = show_price_update_status(tmp_path, tickers=["nvda"])

    assert payload["status"] == "available"
    assert len(payload["rows"]) == 1
    assert payload["rows"][0]["ticker"] == "NVDA"


def test_price_status_cli_uses_read_only_summary_wording(tmp_path: Path, capsys):
    (tmp_path / "data").mkdir()
    (tmp_path / "outputs").mkdir()
    (tmp_path / "config.yaml").write_text(Path("config.yaml").read_text(), encoding="utf-8")
    pd.DataFrame(
        [
            {
                "run_timestamp": "2026-05-21T00:00:00+00:00",
                "ticker": "AMD",
                "requested_start": "",
                "requested_end": "2026-05-21",
                "provider": "FakePriceSource",
                "status": "parse_error",
                "rows_fetched": 0,
                "rows_merged": 0,
                "error_category": "parse_error",
                "error_message": "AMD: parse failed",
                "fallback_used": True,
                "recommended_action": "Run make focus-price TICKER=AMD first. For batch planning, preview make price-refresh-loop DRY_RUN=1; if you choose to refresh this ticker, run make price-refresh TICKERS=AMD; if the free refresh path fails, normalize verified downloaded OHLCV files into data/imports/prices.csv.",
            }
        ]
    ).to_csv(tmp_path / "outputs" / "price_update_status.csv", index=False)

    argv_before = sys.argv[:]
    sys.argv = ["python", "--project-root", str(tmp_path), "--price-status", "--top-n", "1"]
    try:
        main()
        output = capsys.readouterr().out.lower()
    finally:
        sys.argv = argv_before

    assert "price status summary:" in output
    assert "status: available" in output


def test_enrich_price_update_status_frame_refreshes_stale_price_actions():
    frame = pd.DataFrame(
        [
            {
                "ticker": "QQQ",
                "status": "parse_error",
                "requested_start": "2026-03-15",
                "rows_merged": 0,
                "recommended_action": "Retry later or use the manual price import draft workflow in data/imports/prices.csv.",
            }
        ]
    )

    enriched = enrich_price_update_status_frame(frame)

    assert enriched.iloc[0]["recommended_action"].startswith("Run make focus-price TICKER=QQQ")
    assert "normalize verified downloaded OHLCV files into data/imports/prices.csv" in enriched.iloc[0]["recommended_action"]


def test_enrich_price_update_status_frame_refreshes_legacy_raw_price_action_text():
    frame = pd.DataFrame(
        [
            {
                "ticker": "QQQ",
                "status": "parse_error",
                "requested_start": "2026-03-15",
                "rows_merged": 0,
                "recommended_action": "Run make focus-price TICKER=QQQ, or run python3 -m src.data_update --tickers QQQ and normalize verified downloaded OHLCV files into data/imports/prices.csv.",
            }
        ]
    )

    enriched = enrich_price_update_status_frame(frame)

    assert "make price-refresh TICKERS=QQQ" in enriched.iloc[0]["recommended_action"]
    assert "python3 -m src.data_update --tickers QQQ" not in enriched.iloc[0]["recommended_action"]


def test_enrich_price_update_status_frame_normalizes_parse_error_messages():
    frame = pd.DataFrame(
        [
            {
                "ticker": "META",
                "status": "parse_error",
                "error_message": "META: update failed (Error tokenizing data. C error: Expected 1 fields in line 6, saw 2\n)",
                "recommended_action": "Run make focus-price TICKER=META first. For batch planning, preview make price-refresh-loop DRY_RUN=1; if you choose to refresh this ticker, run make price-refresh TICKERS=META; if the free refresh path fails, normalize verified downloaded OHLCV files into data/imports/prices.csv.",
            }
        ]
    )

    enriched = enrich_price_update_status_frame(frame)

    assert enriched.iloc[0]["error_message"] == "META: provider rows could not be parsed cleanly (Expected 1 fields in line 6, saw 2)"
    assert "normalize verified downloaded OHLCV files into data/imports/prices.csv" in enriched.iloc[0]["recommended_action"]


def test_enrich_price_update_status_frame_refreshes_stale_example_command():
    frame = pd.DataFrame(
        [
            {
                "ticker": "AMD",
                "status": "parse_error",
                "requested_start": "",
                "rows_merged": 0,
                "recommended_action": "Run make focus-price TICKER=AMD first. For batch planning, preview make price-refresh-loop DRY_RUN=1; if you choose to refresh this ticker, run make price-refresh TICKERS=AMD; if the free refresh path fails, normalize verified downloaded OHLCV files into data/imports/prices.csv.",
                "example_command": "make onboarding",
            }
        ]
    )

    enriched = enrich_price_update_status_frame(frame)

    assert enriched.iloc[0]["example_command"] == "make price-normalize INPUT=data/raw/prices/AMD.csv TICKER=AMD SOURCE=yahoo_manual"


def test_enrich_price_update_status_frame_refreshes_legacy_raw_price_command():
    frame = pd.DataFrame(
        [
            {
                "ticker": "AMD",
                "status": "parse_error",
                "requested_start": "",
                "rows_merged": 0,
                "recommended_action": "Run make focus-price TICKER=AMD first. For batch planning, preview make price-refresh-loop DRY_RUN=1; if you choose to refresh this ticker, run make price-refresh TICKERS=AMD; if the free refresh path fails, normalize verified downloaded OHLCV files into data/imports/prices.csv.",
                "example_command": "python3 -m src.data_update --tickers AMD",
            }
        ]
    )

    enriched = enrich_price_update_status_frame(frame)

    assert enriched.iloc[0]["example_command"] == "make price-normalize INPUT=data/raw/prices/AMD.csv TICKER=AMD SOURCE=yahoo_manual"


def test_refresh_price_update_status_output_rewrites_legacy_file(tmp_path: Path):
    (tmp_path / "outputs").mkdir()
    path = tmp_path / "outputs" / "price_update_status.csv"
    pd.DataFrame(
        [
            {
                "run_timestamp": "2026-05-21T00:00:00+00:00",
                "ticker": "AMD",
                "requested_start": "",
                "requested_end": "2026-05-21",
                "provider": "FakePriceSource",
                "status": "parse_error",
                "rows_fetched": 0,
                "rows_merged": 0,
                "error_category": "parse_error",
                "error_message": "AMD: parse failed",
                "fallback_used": True,
                "recommended_action": "Retry later or use the manual price import draft workflow in data/imports/prices.csv.",
            }
        ]
    ).to_csv(path, index=False)

    written_path = refresh_price_update_status_output(tmp_path)

    assert written_path == path
    refreshed = pd.read_csv(path)
    assert refreshed.iloc[0]["focus_command"] == "make focus-price TICKER=AMD"
    assert refreshed.iloc[0]["example_command"] == "make price-normalize INPUT=data/raw/prices/AMD.csv TICKER=AMD SOURCE=yahoo_manual"
    assert refreshed.iloc[0]["target_file"] == "data/imports/prices.csv"
    assert refreshed.iloc[0]["recommended_action"].startswith("Run make focus-price TICKER=AMD")


def test_refresh_price_update_status_output_rewrites_legacy_parse_error_message(tmp_path: Path):
    (tmp_path / "outputs").mkdir()
    path = tmp_path / "outputs" / "price_update_status.csv"
    pd.DataFrame(
        [
            {
                "run_timestamp": "2026-05-21T00:00:00+00:00",
                "ticker": "META",
                "requested_start": "",
                "requested_end": "2026-05-21",
                "provider": "FakePriceSource",
                "status": "parse_error",
                "rows_fetched": 0,
                "rows_merged": 0,
                "error_category": "parse_error",
                "error_message": "META: update failed (Error tokenizing data. C error: Expected 1 fields in line 6, saw 2\n)",
                "fallback_used": True,
                "recommended_action": "Retry later or use the manual price import draft workflow in data/imports/prices.csv.",
            }
        ]
    ).to_csv(path, index=False)

    refresh_price_update_status_output(tmp_path)

    refreshed = pd.read_csv(path)
    assert refreshed.iloc[0]["error_message"] == "META: provider rows could not be parsed cleanly (Expected 1 fields in line 6, saw 2)"
    assert "normalize verified downloaded OHLCV files into data/imports/prices.csv" in refreshed.iloc[0]["recommended_action"]


class FlakyPriceSource(FakePriceSource):
    def __init__(self, payloads: dict[str, pd.DataFrame | None]) -> None:
        super().__init__(payloads)
        self.fail_once = {"BBB"}

    def fetch_history(self, ticker: str) -> tuple[pd.DataFrame, list[str]]:
        self.calls.append(ticker)
        if ticker in self.fail_once:
            self.fail_once.remove(ticker)
            raise RuntimeError("temporary failure")
        return super().fetch_history(ticker)


def test_update_local_price_data_retries_and_continues_when_one_ticker_fails(tmp_path: Path):
    (tmp_path / "data").mkdir()
    (tmp_path / "config.yaml").write_text(Path("config.yaml").read_text(), encoding="utf-8")
    source = FlakyPriceSource(
        {
            "AAA": pd.DataFrame(
                [
                    {
                        "date": pd.Timestamp("2026-01-03"),
                        "ticker": "AAA",
                        "open": 10.0,
                        "high": 11.0,
                        "low": 9.0,
                        "close": 10.5,
                        "adj_close": 10.5,
                        "volume": 1000,
                    }
                ]
            ),
            "BBB": pd.DataFrame(
                [
                    {
                        "date": pd.Timestamp("2026-01-03"),
                        "ticker": "BBB",
                        "open": 20.0,
                        "high": 21.0,
                        "low": 19.0,
                        "close": 20.5,
                        "adj_close": 20.5,
                        "volume": 1200,
                    }
                ]
            ),
        }
    )

    result = update_local_price_data(tmp_path, source=source, tickers=["AAA", "BBB"], retry_attempts=1)

    assert set(result.tickers_updated) == {"AAA", "BBB"}
    assert source.calls.count("BBB") >= 2


def test_update_local_price_data_marks_fetched_rows_still_insufficient_when_history_remains_short(tmp_path: Path):
    (tmp_path / "data").mkdir()
    (tmp_path / "outputs").mkdir()
    (tmp_path / "config.yaml").write_text(Path("config.yaml").read_text(), encoding="utf-8")
    (tmp_path / "data" / "prices.csv").write_text(
        "date,ticker,open,high,low,close,adj_close,volume\n"
        "2026-06-08,CGCT,12.16,11.9,11.9,11.9,11.9,33924\n",
        encoding="utf-8",
    )
    source = FakePriceSource(
        {
            "CGCT": pd.DataFrame(
                [
                    {
                        "date": pd.Timestamp("2026-06-09"),
                        "ticker": "CGCT",
                        "open": 11.9,
                        "high": 12.0,
                        "low": 11.8,
                        "close": 11.95,
                        "adj_close": 11.95,
                        "volume": 25000,
                    }
                ]
            )
        }
    )

    result = update_local_price_data(tmp_path, source=source, tickers=["CGCT"], refresh=True)

    status = pd.read_csv(result.status_path)
    assert status.iloc[0]["status"] == "insufficient_history"
    assert status.iloc[0]["rows_fetched"] == 1
    assert status.iloc[0]["rows_merged"] == 2
    assert "normalize verified downloaded OHLCV files" in status.iloc[0]["recommended_action"]
    assert status.iloc[0]["focus_command"] == "make focus-price TICKER=CGCT"


def test_update_local_price_data_writes_status_when_remote_parse_errors(tmp_path: Path):
    (tmp_path / "data").mkdir()
    (tmp_path / "outputs").mkdir()
    (tmp_path / "config.yaml").write_text(Path("config.yaml").read_text(), encoding="utf-8")
    (tmp_path / "data" / "prices.csv").write_text(
        "date,ticker,adj_close,volume\n2026-01-02,SPY,100,1000\n",
        encoding="utf-8",
    )
    source = FakePriceSource({"SPY": pd.DataFrame()})

    def fetch_history(_ticker: str):
        return pd.DataFrame(), ["SPY: update failed (Error tokenizing data)"]

    source.fetch_history = fetch_history
    result = update_local_price_data(tmp_path, source=source, tickers=["SPY"])

    status = pd.read_csv(result.status_path)
    assert status.iloc[0]["status"] == "parse_error"
    assert status.iloc[0]["fallback_used"] in {True, "True", "true"}
    assert "normalize verified downloaded ohlcv files into data/imports/prices.csv" in status.iloc[0]["recommended_action"].lower()
    assert status.iloc[0]["focus_command"] == "make focus-price TICKER=SPY"
    assert status.iloc[0]["example_command"] == "make price-normalize INPUT=data/raw/prices/SPY.csv TICKER=SPY SOURCE=yahoo_manual"
    assert status.iloc[0]["target_file"] == "data/imports/prices.csv"


def _write_price_import_fixture(root: Path) -> None:
    data_dir = root / "data"
    import_dir = data_dir / "imports"
    data_dir.mkdir()
    import_dir.mkdir(parents=True)
    (root / "config.yaml").write_text(Path("config.yaml").read_text(), encoding="utf-8")
    (data_dir / "prices.csv").write_text(
        "date,ticker,open,high,low,close,adj_close,volume,source\n"
        "2026-01-02,NVDA,99,101,98,100,100,1000,canonical\n"
        "2026-01-02,MSFT,199,201,198,200,200,2000,canonical\n",
        encoding="utf-8",
    )
    (import_dir / "prices.csv").write_text(
        "date,ticker,open,high,low,close,volume,adjusted_close,source,source_ref,retrieved_at,as_of_date,notes,extra\n"
        "2026-01-02,nvda,100,103,99,102,1500,102,manual,https://example.test/NVDA/2026-01-02,2026-01-03T23:00:00Z,2026-01-03,updated,row-extra\n"
        "2026-01-03,NVDA,102,104,101,103,1600,103,manual,https://example.test/NVDA/2026-01-03,2026-01-04T23:00:00Z,2026-01-03,new,row-extra\n"
        "2026-01-02,NVDA,100,103,99,102,1500,102,manual,https://example.test/NVDA/2026-01-02,2026-01-03T23:00:00Z,2026-01-03,duplicate,row-extra\n"
        "2026-01-04,BAD,10,9,11,10,100,10,manual,https://example.test/BAD/2026-01-04,2026-01-05T23:00:00Z,2026-01-03,bad-high-low,row-extra\n",
        encoding="utf-8",
    )


def _price_rights_registry():
    return build_source_rights_registry(
        [
            {
                "source_id": "approved_prices",
                "display_name": "Approved Prices",
                "permitted_use": "reviewed_price_research",
                "commercial_use": "approved",
                "redistribution": "derived_data_only",
                "storage_limits": "reviewed rows only",
                "attribution": "durable source reference required",
                "rate_limits": "manual reviewed export",
                "authentication": "reviewed account",
                "expected_freshness": "payload timestamp",
                "supported_fields": ["prices"],
                "fallback_priority": 1,
            },
            {
                "source_id": "approved_fundamentals",
                "display_name": "Approved Fundamentals",
                "permitted_use": "reviewed_fundamentals_research",
                "commercial_use": "approved",
                "redistribution": "derived_data_only",
                "storage_limits": "reviewed rows only",
                "attribution": "durable source reference required",
                "rate_limits": "manual reviewed export",
                "authentication": "reviewed account",
                "expected_freshness": "filing driven",
                "supported_fields": ["revenue"],
                "fallback_priority": 2,
            },
            {
                "source_id": "unverified_prices",
                "display_name": "Unverified Prices",
                "permitted_use": "research_only",
                "commercial_use": "unverified",
                "redistribution": "not_permitted",
                "storage_limits": "local research only",
                "attribution": "source attribution required",
                "rate_limits": "manual reviewed export",
                "authentication": "none",
                "expected_freshness": "not guaranteed",
                "supported_fields": ["prices"],
                "fallback_priority": 90,
            },
        ]
    )


def test_price_import_validation_valid_fixture_and_duplicates(tmp_path: Path):
    _write_price_import_fixture(tmp_path)

    summary = validate_price_imports(
        tmp_path,
        review_cutoff="2026-01-05T00:00:00Z",
    )

    assert summary["status"] == "valid_with_warnings"
    assert summary["valid_rows"] == 2
    assert summary["duplicate_rows"] == 1
    assert summary["affected_tickers"] == ["NVDA"]
    assert "extra" in summary["unknown_columns"]
    assert "price import draft" not in " ".join(summary["warnings"]).lower()
    assert "invalid price import file row" in " ".join(summary["warnings"]).lower()
    assert summary["lineage_status"] == "lineage_complete"
    assert summary["lineage_complete_rows"] == 2
    assert summary["lineage_review_required_rows"] == 0
    assert summary["lineage_missing_fields"] == []
    assert set(summary["valid_frame"]["source_ref"]) == {
        "https://example.test/NVDA/2026-01-02",
        "https://example.test/NVDA/2026-01-03",
    }
    assert set(summary["valid_frame"]["retrieved_at"]) == {
        "2026-01-03T23:00:00+00:00",
        "2026-01-04T23:00:00+00:00",
    }
    assert summary["commercial_rights_status"] == "rights_review_required"
    assert summary["rights_approved_rows"] == 0
    assert summary["rights_review_required_rows"] == 2
    assert summary["rights_status_counts"] == {"unknown_source": 2}
    assert summary["price_scope_status"] == "price_scope_review_required"
    assert summary["price_scope_complete_rows"] == 0
    assert summary["price_scope_review_required_rows"] == 2
    assert summary["source_review_rows"] == [
        {
            "source_id": "manual",
            "row_count": 2,
            "rights_status": "unknown_source",
            "commercial_rights_approved": False,
            "price_scope_complete": False,
            "blockers": ["commercial_rights:unknown_source", "registered_price_scope_incomplete"],
        }
    ]


def test_price_import_validation_keeps_technical_validity_independent_from_lineage(tmp_path: Path):
    data_dir = tmp_path / "data"
    import_dir = data_dir / "imports"
    import_dir.mkdir(parents=True)
    (tmp_path / "config.yaml").write_text(Path("config.yaml").read_text(), encoding="utf-8")
    (import_dir / "prices.csv").write_text(
        "date,ticker,open,high,low,close,volume,adjusted_close,source,source_ref,retrieved_at\n"
        "2026-01-02,NVDA,100,103,99,102,1500,102,manual,,not-a-timestamp\n",
        encoding="utf-8",
    )

    summary = validate_price_imports(tmp_path)

    assert summary["status"] == "valid_with_warnings"
    assert summary["valid_rows"] == 1
    assert summary["lineage_status"] == "lineage_review_required"
    assert summary["lineage_complete_rows"] == 0
    assert summary["lineage_review_required_rows"] == 1
    assert summary["lineage_missing_fields"] == ["retrieved_at", "source_ref"]
    assert summary["valid_frame"].iloc[0]["source"] == "manual"
    assert pd.isna(summary["valid_frame"].iloc[0]["source_ref"])
    assert summary["valid_frame"].iloc[0]["retrieved_at"] == ""
    assert "lineage review" in " ".join(summary["warnings"]).lower()


def test_price_import_validation_keeps_rights_and_scope_independent(tmp_path: Path):
    data_dir = tmp_path / "data"
    import_dir = data_dir / "imports"
    import_dir.mkdir(parents=True)
    (tmp_path / "config.yaml").write_text(Path("config.yaml").read_text(), encoding="utf-8")
    (import_dir / "prices.csv").write_text(
        "date,ticker,open,high,low,close,volume,source,source_ref,retrieved_at\n"
        "2026-01-02,NVDA,100,103,99,102,1500,approved_prices,https://example.test/approved,2026-01-03T23:00:00Z\n"
        "2026-01-02,MSFT,200,203,199,202,2500,unverified_prices,https://example.test/unverified,2026-01-03T23:00:00Z\n"
        "2026-01-02,META,300,303,299,302,3500,approved_fundamentals,https://example.test/fundamentals,2026-01-03T23:00:00Z\n"
        "2026-01-02,GOOG,400,403,399,402,4500,,https://example.test/missing,2026-01-03T23:00:00Z\n"
        "2026-01-02,BAD,10,9,11,10,100,approved_prices,https://example.test/invalid,2026-01-03T23:00:00Z\n",
        encoding="utf-8",
    )

    summary = validate_price_imports(tmp_path, rights_registry=_price_rights_registry())

    assert summary["status"] == "valid_with_warnings"
    assert summary["valid_rows"] == 4
    assert summary["commercial_rights_status"] == "mixed_rights"
    assert summary["rights_approved_rows"] == 2
    assert summary["rights_review_required_rows"] == 2
    assert summary["rights_status_counts"] == {
        "approved": 2,
        "commercial_rights_unverified": 1,
        "unknown_source": 1,
    }
    assert summary["price_scope_status"] == "mixed_price_scope"
    assert summary["price_scope_complete_rows"] == 2
    assert summary["price_scope_review_required_rows"] == 2
    assert [row["source_id"] for row in summary["source_review_rows"]] == [
        "<missing>",
        "approved_fundamentals",
        "approved_prices",
        "unverified_prices",
    ]
    assert summary["source_review_rows"][0]["rights_status"] == "unknown_source"
    assert summary["source_review_rows"][0]["price_scope_complete"] is False
    assert summary["source_review_rows"][1]["commercial_rights_approved"] is True
    assert summary["source_review_rows"][1]["price_scope_complete"] is False
    assert summary["source_review_rows"][2]["blockers"] == []
    assert summary["source_review_rows"][3]["blockers"] == [
        "commercial_rights:commercial_rights_unverified"
    ]
    assert "BAD" not in {row["ticker"] for row in summary["valid_frame"].to_dict(orient="records")}


def test_price_import_validation_keeps_yfinance_technical_status_valid(tmp_path: Path):
    import_dir = tmp_path / "data" / "imports"
    import_dir.mkdir(parents=True)
    (tmp_path / "config.yaml").write_text(Path("config.yaml").read_text(), encoding="utf-8")
    (import_dir / "prices.csv").write_text(
        "date,ticker,open,high,low,close,volume,source,source_ref,retrieved_at\n"
        "2026-01-02,NVDA,100,103,99,102,1500,yfinance,https://example.test/yfinance,2026-01-03T23:00:00Z\n",
        encoding="utf-8",
    )

    summary = validate_price_imports(tmp_path)

    assert summary["status"] == "valid"
    assert summary["warnings"] == []
    assert summary["lineage_status"] == "lineage_complete"
    assert summary["commercial_rights_status"] == "rights_review_required"
    assert summary["rights_status_counts"] == {"commercial_rights_unverified": 1}
    assert summary["price_scope_status"] == "price_scope_complete"
    assert summary["commercial_evidence_warnings"] == [
        "Commercial rights review required for 1 valid staged price row(s)."
    ]


def test_price_import_preview_inherits_injected_rights_and_scope_review(tmp_path: Path):
    _write_price_import_fixture(tmp_path)
    staged_path = tmp_path / "data" / "imports" / "prices.csv"
    staged = pd.read_csv(staged_path)
    staged.loc[:, "source"] = "approved_prices"
    staged.to_csv(staged_path, index=False)

    preview = preview_price_import_merge(tmp_path, rights_registry=_price_rights_registry())

    assert preview["new_rows"] == 1
    assert preview["updated_rows"] == 1
    assert preview["commercial_rights_status"] == "rights_approved"
    assert preview["rights_approved_rows"] == 2
    assert preview["rights_review_required_rows"] == 0
    assert preview["price_scope_status"] == "price_scope_complete"
    assert preview["price_scope_complete_rows"] == 2
    assert preview["price_scope_review_required_rows"] == 0


def test_price_import_validation_missing_file_uses_plain_import_file_language(tmp_path: Path):
    (tmp_path / "data" / "imports").mkdir(parents=True)
    (tmp_path / "config.yaml").write_text(Path("config.yaml").read_text(), encoding="utf-8")

    summary = validate_price_imports(tmp_path)

    rendered = " ".join(summary["warnings"]).lower()
    assert summary["status"] == "no_staged_file"
    assert "price import file" in rendered
    assert "import draft" not in rendered


def test_price_import_validation_rejects_missing_required_columns(tmp_path: Path):
    data_dir = tmp_path / "data"
    import_dir = data_dir / "imports"
    import_dir.mkdir(parents=True)
    (tmp_path / "config.yaml").write_text(Path("config.yaml").read_text(), encoding="utf-8")
    (import_dir / "prices.csv").write_text("date,ticker,close\n2026-01-01,NVDA,100\n", encoding="utf-8")

    summary = validate_price_imports(tmp_path)

    assert summary["status"] == "invalid"
    assert {"open", "high", "low", "volume"}.issubset(set(summary["missing_required_columns"]))


def test_preview_price_import_merge_reports_new_updated_and_skipped(tmp_path: Path):
    _write_price_import_fixture(tmp_path)

    preview = preview_price_import_merge(tmp_path)

    assert preview["new_rows"] == 1
    assert preview["updated_rows"] == 1
    assert preview["skipped_rows"] == 2
    assert preview["unchanged_rows"] == 0
    assert preview["lineage_status"] == "lineage_complete"
    assert preview["lineage_complete_rows"] == 2
    assert preview["lineage_review_required_rows"] == 0
    assert preview["commercial_rights_status"] == "rights_review_required"
    assert preview["price_scope_status"] == "price_scope_review_required"


def test_commercial_price_apply_blocks_before_backup_or_canonical_write(tmp_path: Path):
    _write_price_import_fixture(tmp_path)
    canonical_path = tmp_path / "data" / "prices.csv"
    before = canonical_path.read_bytes()

    result = apply_price_import_merge(
        tmp_path,
        commercial_mode=True,
        review_cutoff="2026-01-05T00:00:00Z",
    )

    assert result["applied"] is False
    assert result["apply_status"] == "commercial_evidence_review_required"
    assert result["apply_blockers"] == [
        "commercial_rights_review_required",
        "registered_price_scope_review_required",
    ]
    assert result["backup_path"] is None
    assert canonical_path.read_bytes() == before
    assert not (tmp_path / "data" / "backups").exists()


def test_commercial_price_apply_blocks_incomplete_lineage_independently(tmp_path: Path):
    _write_price_import_fixture(tmp_path)
    staged_path = tmp_path / "data" / "imports" / "prices.csv"
    staged = pd.read_csv(staged_path)
    staged.loc[:, "source"] = "approved_prices"
    staged.loc[staged["ticker"].astype(str).str.upper() == "NVDA", "source_ref"] = ""
    staged.to_csv(staged_path, index=False)

    result = apply_price_import_merge(
        tmp_path,
        commercial_mode=True,
        rights_registry=_price_rights_registry(),
        review_cutoff="2026-01-05T00:00:00Z",
    )

    assert result["applied"] is False
    assert result["apply_blockers"] == ["price_lineage_review_required"]
    assert result["commercial_rights_status"] == "rights_approved"
    assert result["price_scope_status"] == "price_scope_complete"


def test_commercial_price_apply_blocks_missing_registered_price_scope(tmp_path: Path):
    _write_price_import_fixture(tmp_path)
    staged_path = tmp_path / "data" / "imports" / "prices.csv"
    staged = pd.read_csv(staged_path)
    staged.loc[:, "source"] = "approved_fundamentals"
    staged.to_csv(staged_path, index=False)

    result = apply_price_import_merge(
        tmp_path,
        commercial_mode=True,
        rights_registry=_price_rights_registry(),
        review_cutoff="2026-01-05T00:00:00Z",
    )

    assert result["applied"] is False
    assert result["apply_blockers"] == ["registered_price_scope_review_required"]
    assert result["commercial_rights_status"] == "rights_approved"
    assert result["price_scope_status"] == "price_scope_review_required"


def test_commercial_price_apply_allows_complete_approved_batch(tmp_path: Path):
    _write_price_import_fixture(tmp_path)
    staged_path = tmp_path / "data" / "imports" / "prices.csv"
    staged = pd.read_csv(staged_path)
    staged.loc[:, "source"] = "approved_prices"
    staged.to_csv(staged_path, index=False)

    result = apply_price_import_merge(
        tmp_path,
        commercial_mode=True,
        rights_registry=_price_rights_registry(),
        review_cutoff="2026-01-05T00:00:00Z",
    )

    assert result["applied"] is True
    assert result["apply_status"] == "applied"
    assert result["apply_blockers"] == []
    assert result["backup_path"] is not None
    assert result["commercial_rights_status"] == "rights_approved"
    assert result["price_scope_status"] == "price_scope_complete"


@pytest.mark.parametrize(
    ("retrieved_at", "cutoff", "blocker"),
    [
        ("2026-01-03T23:00:00", "2026-01-05T00:00:00Z", "retrieved_at_timezone_required"),
        ("2026-01-02T23:59:59Z", "2026-01-05T00:00:00Z", "retrieved_before_observation_available"),
        ("2026-01-05T00:00:01Z", "2026-01-05T00:00:00Z", "retrieved_after_review_cutoff"),
    ],
)
def test_staged_price_preview_and_apply_share_temporal_blockers_without_mutation(
    tmp_path: Path,
    retrieved_at: str,
    cutoff: str,
    blocker: str,
):
    _write_price_import_fixture(tmp_path)
    staged_path = tmp_path / "data" / "imports" / "prices.csv"
    staged = pd.read_csv(staged_path)
    staged.loc[:, "source"] = "approved_prices"
    staged.loc[:, "retrieved_at"] = retrieved_at
    staged.to_csv(staged_path, index=False)
    canonical_path = tmp_path / "data" / "prices.csv"
    before = canonical_path.read_bytes()

    preview = preview_price_import_merge(
        tmp_path,
        rights_registry=_price_rights_registry(),
        review_cutoff=cutoff,
    )
    result = apply_price_import_merge(
        tmp_path,
        commercial_mode=True,
        rights_registry=_price_rights_registry(),
        review_cutoff=cutoff,
    )

    assert preview["price_temporal_status"] == "temporal_review_required"
    assert blocker in preview["price_temporal_blocker_counts"]
    assert result["applied"] is False
    assert result["apply_blockers"][0] == "price_temporal_review_required"
    assert canonical_path.read_bytes() == before
    assert not (tmp_path / "data" / "backups").exists()


def test_price_apply_uses_one_validated_staged_frame_and_atomic_replace(tmp_path: Path, monkeypatch):
    _write_price_import_fixture(tmp_path)
    staged_path = tmp_path / "data" / "imports" / "prices.csv"
    staged = pd.read_csv(staged_path)
    staged.loc[:, "source"] = "approved_prices"
    staged.to_csv(staged_path, index=False)
    read_calls = 0
    replace_calls: list[tuple[Path, Path]] = []
    original_read = data_update._read_price_import
    original_replace = data_update.os.replace

    def _read_once(path: Path):
        nonlocal read_calls
        read_calls += 1
        return original_read(path)

    def _replace(source: Path, destination: Path):
        replace_calls.append((Path(source), Path(destination)))
        return original_replace(source, destination)

    monkeypatch.setattr(data_update, "_read_price_import", _read_once)
    monkeypatch.setattr(data_update.os, "replace", _replace)

    result = apply_price_import_merge(
        tmp_path,
        commercial_mode=True,
        rights_registry=_price_rights_registry(),
        review_cutoff="2026-01-05T00:00:00Z",
    )

    assert result["applied"] is True
    assert read_calls == 1
    assert len(replace_calls) == 1
    temporary, destination = replace_calls[0]
    assert temporary.parent == destination.parent
    assert destination == tmp_path / "data" / "prices.csv"


def test_apply_price_import_merge_backs_up_and_never_deletes_rows(tmp_path: Path):
    _write_price_import_fixture(tmp_path)

    result = apply_price_import_merge(
        tmp_path,
        commercial_mode=False,
        review_cutoff="2026-01-05T00:00:00Z",
    )
    prices = pd.read_csv(tmp_path / "data" / "prices.csv")

    assert result["applied"] is True
    assert result["backup_path"] is not None
    assert Path(result["backup_path"]).exists()
    assert len(prices) == 3
    assert set(prices["ticker"]) == {"NVDA", "MSFT"}
    updated = prices.loc[(prices["ticker"] == "NVDA") & (prices["date"] == "2026-01-02")].iloc[0]
    assert updated["close"] == 102
    assert updated["source_ref"] == "https://example.test/NVDA/2026-01-02"
    assert updated["retrieved_at"] == "2026-01-03T23:00:00+00:00"
    new_row = prices.loc[(prices["ticker"] == "NVDA") & (prices["date"] == "2026-01-03")].iloc[0]
    assert new_row["source_ref"] == "https://example.test/NVDA/2026-01-03"
    assert new_row["retrieved_at"] == "2026-01-04T23:00:00+00:00"
    msft = prices.loc[prices["ticker"] == "MSFT"].iloc[0]
    assert pd.isna(msft["source_ref"])
    assert pd.isna(msft["retrieved_at"])
