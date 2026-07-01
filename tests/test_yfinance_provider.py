import builtins
import sys
from types import SimpleNamespace

import pandas as pd
import pytest

from src.providers.yfinance_provider import YFinanceProvider, build_yfinance_fundamentals_rows


def test_yfinance_provider_fails_gracefully_when_dependency_is_missing(monkeypatch: pytest.MonkeyPatch):
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "yfinance":
            raise ImportError("missing yfinance")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(RuntimeError, match="yfinance is not installed"):
        YFinanceProvider()


def test_yfinance_fundamentals_rows_normalize_epoch_most_recent_quarter(monkeypatch: pytest.MonkeyPatch):
    class FakeTicker:
        info = {
            "mostRecentQuarter": 1722384000,
            "totalRevenue": 294839648,
            "sharesOutstanding": 51191848,
        }

    monkeypatch.setitem(sys.modules, "yfinance", SimpleNamespace(Ticker=lambda _ticker: FakeTicker()))

    result = build_yfinance_fundamentals_rows(["ABVE"])

    assert result["rows"][0]["as_of_date"] == "2024-07-31"


def test_yfinance_earnings_dates_normalize_epoch_timestamps(monkeypatch: pytest.MonkeyPatch):
    class FakeTicker:
        info = {"earningsTimestampStart": 1785441600}
        calendar = pd.DataFrame()

        def get_earnings_dates(self, limit=4):
            assert limit == 4
            return pd.DataFrame()

    monkeypatch.setitem(sys.modules, "yfinance", SimpleNamespace(Ticker=lambda _ticker: FakeTicker()))

    summary = YFinanceProvider().get_earnings("AAPL")

    assert summary.next_earnings_date == "2026-07-30"


def test_yfinance_earnings_suppresses_upstream_console_noise(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]):
    class FakeTicker:
        info = {}
        calendar = pd.DataFrame()

        def get_earnings_dates(self, limit=4):
            print("AACB: No earnings dates found, symbol may be delisted")
            return pd.DataFrame()

    monkeypatch.setitem(sys.modules, "yfinance", SimpleNamespace(Ticker=lambda _ticker: FakeTicker()))

    summary = YFinanceProvider().get_earnings("AACB")

    captured = capsys.readouterr()
    assert "No earnings dates found" not in captured.out
    assert "No earnings dates found" not in captured.err
    assert summary.ticker == "AACB"
