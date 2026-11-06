"""The Discover price check is a session-only, exchange-bound availability proxy."""

from copy import deepcopy
from datetime import datetime, timedelta
import json

import pytest

from test_online_company_prices import _payload
from test_online_us_universe import E_URL, EXCHANGE, MAP, M_URL, N_BODY, N_URL, OBSERVED, _fetch, _inventory


def _price_fetch(calls, *, symbol="FICT", exchange="NMS", full_exchange="NasdaqGS", payload=None):
    body = _payload() if payload is None else payload
    body["chart"]["result"][0]["meta"].update(
        symbol=symbol, exchangeName=exchange, fullExchangeName=full_exchange,
    )

    def fetch(url):
        calls.append(url)
        return json.dumps(body).encode(), url

    return fetch


def test_completed_price_proxy_counts_only_after_an_explicit_check(monkeypatch):
    from src.online_company_prices import price_source_url
    from src.online_industry_price_coverage import check_industry_price, read_price_coverage

    monkeypatch.delenv("COMMERCIAL_RESEARCH_MODE", raising=False)
    state = {}
    inventory = _inventory()
    calls = []
    assert read_price_coverage(state, inventory) == []
    assert calls == []

    result = check_industry_price(state, inventory, "fict", fetcher=_price_fetch(calls), observed_at=OBSERVED)

    assert result["status"] == "recorded"
    assert read_price_coverage(state, inventory) == [{
        "ticker": "FICT", "sec_cik": "0000001234", "attempted_at": "2026-10-30T22:00:00Z",
        "available": True, "reason": "completed_bar_available", "price_date": "2026-10-29",
    }]
    assert calls == [price_source_url("FICT")]
    assert "volume" not in str(state) and "bars" not in str(state)


def test_venue_mismatch_is_an_attempt_and_cannot_be_retried(monkeypatch):
    from src.online_industry_price_coverage import check_industry_price, read_price_coverage

    monkeypatch.delenv("COMMERCIAL_RESEARCH_MODE", raising=False)
    inventory = _inventory()
    state = {}
    calls = []
    result = check_industry_price(state, inventory, "FICT", fetcher=_price_fetch(calls, exchange="NYQ", full_exchange="NYSE"), observed_at=OBSERVED)
    assert result["status"] == "recorded"
    row, = read_price_coverage(state, inventory)
    assert row["available"] is False and row["reason"] == "price_exchange_mismatch" and "price_date" not in row
    again = check_industry_price(state, inventory, "FICT", fetcher=_price_fetch(calls), observed_at=OBSERVED)
    assert again["reason"] == "price_issuer_already_checked"
    assert len(calls) == 1


def test_stale_invalid_or_ineligible_inventory_routes_never_call_provider(monkeypatch):
    from src.online_industry_price_coverage import check_industry_price

    monkeypatch.delenv("COMMERCIAL_RESEARCH_MODE", raising=False)
    inventory = _inventory()
    broken = deepcopy(inventory)
    broken["rows"][0]["etf"] = []
    state = {}
    for snapshot, ticker, now, reason in (
        (inventory, "FICT", OBSERVED + timedelta(hours=25), "listing_inventory_refresh_required"),
        (inventory, "FICT", OBSERVED - timedelta(seconds=1), "listing_inventory_refresh_required"),
        (broken, "FICT", OBSERVED, "listing_inventory_unverified"),
        (inventory, "FUND", OBSERVED, "price_route_unavailable"),
        (inventory, "TEX", OBSERVED, "price_route_unavailable"),
        (inventory, "FICT.B", OBSERVED, "price_route_unavailable"),
    ):
        result = check_industry_price(state, snapshot, ticker, observed_at=now,
                                      fetcher=lambda _url: pytest.fail("unexpected price request"))
        assert result["reason"] == reason
    assert state == {}


def test_completed_price_must_be_recent_and_is_hidden_after_inventory_change(monkeypatch):
    from src.online_industry_price_coverage import check_industry_price, read_price_coverage
    from src.online_us_universe import load_online_us_universe

    monkeypatch.delenv("COMMERCIAL_RESEARCH_MODE", raising=False)
    inventory = _inventory()
    later = OBSERVED + timedelta(minutes=1)
    another = load_online_us_universe(user_agent="Research", fetcher=_fetch([]), observed_at=later)
    state = {}
    old = _payload()
    chart = old["chart"]["result"][0]
    chart["timestamp"] = [value - 14 * 86400 for value in chart["timestamp"]]
    calls = []

    check_industry_price(state, inventory, "FICT", fetcher=_price_fetch(calls, payload=old), observed_at=OBSERVED)

    assert read_price_coverage(state, inventory)[0]["reason"] == "no_recent_completed_price"
    assert read_price_coverage(state, another) == []
    result = check_industry_price(state, another, "FICT", fetcher=_price_fetch(calls), observed_at=later)
    assert result["reason"] == "price_issuer_already_checked"
    monkeypatch.setenv("COMMERCIAL_RESEARCH_MODE", "1")
    assert read_price_coverage(state, inventory) == []
    assert check_industry_price(state, inventory, "FICT", fetcher=_price_fetch(calls), observed_at=OBSERVED)["status"] == "unavailable"
    assert len(calls) == 1


def test_price_checks_have_a_global_twenty_issuer_session_limit(monkeypatch):
    from src.online_industry_price_coverage import check_industry_price, read_price_coverage

    monkeypatch.delenv("COMMERCIAL_RESEARCH_MODE", raising=False)
    tickers = [f"ZZA{index:02}" for index in range(21)]
    directory_lines = "".join(f"{ticker}|Company {ticker}|Q|N|N|100|N|N\n" for ticker in tickers)
    listings = N_BODY.replace("File Creation Time", directory_lines + "File Creation Time")
    mapping = dict(MAP)
    exchange = deepcopy(EXCHANGE)
    for index, ticker in enumerate(tickers):
        cik = 8000 + index
        mapping[str(cik)] = {"ticker": ticker, "cik_str": cik, "title": ticker}
        exchange["data"].append([cik, ticker, ticker, "Nasdaq"])

    def fetch(url, agent):
        if url == N_URL:
            return listings.encode(), {}, url
        if url in {M_URL, E_URL}:
            return json.dumps(mapping if url == M_URL else exchange).encode(), {}, url
        return _fetch([])(url, agent)

    inventory = _inventory(fetcher=fetch)
    state = {}
    calls = []
    for ticker in tickers[:20]:
        result = check_industry_price(state, inventory, ticker, fetcher=_price_fetch(calls, symbol=ticker), observed_at=OBSERVED)
        assert result["status"] == "recorded"
    result = check_industry_price(state, inventory, tickers[-1], fetcher=_price_fetch(calls, symbol=tickers[-1]), observed_at=OBSERVED)
    assert result["reason"] == "price_session_limit_reached"
    assert len(calls) == len(read_price_coverage(state, inventory)) == 20


def test_same_day_price_requires_completed_session_and_receipt_remains_valid(monkeypatch):
    from src.online_industry_price_coverage import SESSION_KEY, check_industry_price, read_price_coverage

    monkeypatch.delenv("COMMERCIAL_RESEARCH_MODE", raising=False)
    inventory = _inventory()
    state = {}
    payload = _payload()
    chart = payload["chart"]["result"][0]
    close_time = int(OBSERVED.replace(hour=20).timestamp())
    chart["meta"].update(currentTradingPeriod={"regular": {"start": chart["timestamp"][-1], "end": close_time}},
                         regularMarketTime=close_time, regularMarketPrice=11)
    result = check_industry_price(state, inventory, "FICT", fetcher=_price_fetch([], payload=payload), observed_at=OBSERVED)
    assert result["attempt"]["price_date"] == "2026-10-30"
    assert read_price_coverage(state, inventory) == [result["attempt"]]

    state[SESSION_KEY][0]["attempt"]["price_date"] = "2026-10-29"
    assert read_price_coverage(state, inventory) == []
    held = check_industry_price(state, inventory, "BANK", observed_at=OBSERVED,
                               fetcher=lambda _url: pytest.fail("tampered state fetched prices"))
    assert held["reason"] == "price_session_unverified"


def test_inventory_association_without_discover_search_route_is_withheld(monkeypatch):
    from src.online_industry_price_coverage import check_industry_price

    monkeypatch.delenv("COMMERCIAL_RESEARCH_MODE", raising=False)
    exchange = deepcopy(EXCHANGE)
    exchange["data"] = [row for row in exchange["data"] if row[2] != "FICT"]

    def fetch(url, agent):
        if url == E_URL:
            return json.dumps(exchange).encode(), {}, url
        return _fetch([])(url, agent)

    inventory = _inventory(fetcher=fetch)
    assert any(row["ticker"] == "FICT" for row in inventory["issuer_queue"])
    result = check_industry_price({}, inventory, "FICT", observed_at=OBSERVED,
                                  fetcher=lambda _url: pytest.fail("unsupported search route fetched prices"))
    assert result["reason"] == "price_route_unavailable"


def _price_form_app():
    import streamlit as st
    from src.online_industry_price_coverage import read_price_coverage, render_industry_price_control
    from test_online_us_universe import _inventory

    inventory = _inventory()
    render_industry_price_control(st, inventory)
    st.write(f"Price observations recorded: {len(read_price_coverage(st.session_state, inventory))}")


def test_price_form_fetches_once_on_submit_and_keeps_result_on_rerun(monkeypatch):
    from streamlit.testing.v1 import AppTest
    from src import online_industry_price_coverage as price

    class FixedClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls.fromtimestamp(OBSERVED.timestamp(), tz)

    monkeypatch.delenv("COMMERCIAL_RESEARCH_MODE", raising=False)
    monkeypatch.setattr(price, "datetime", FixedClock)
    calls = []
    monkeypatch.setattr(price, "_fetch_exact", _price_fetch(calls))
    fetch = price.fetch_online_company_prices
    monkeypatch.setattr(price, "fetch_online_company_prices", lambda ticker, **kwargs: fetch(ticker, **{**kwargs, "observed_at": OBSERVED}))
    app = AppTest.from_function(_price_form_app).run()
    assert not app.exception and calls == []
    app.text_input[0].set_value("FICT").run()
    assert calls == []
    app.button[0].click().run()
    assert not app.exception and len(calls) == 1
    assert any("Price observations recorded: 1" in item.value for item in app.markdown)
    app.run()
    assert not app.exception and len(calls) == 1
