import json
from copy import deepcopy
from datetime import datetime, timezone

import pytest

OBSERVED = datetime(2026, 10, 30, 18, tzinfo=timezone.utc)


def _payload():
    return {"chart": {"error": None, "result": [{
        "meta": {"symbol": "FICT", "currency": "USD", "instrumentType": "EQUITY", "exchangeTimezoneName": "America/New_York"},
        "timestamp": [int(datetime(2026, 10, d, 14, tzinfo=timezone.utc).timestamp()) for d in [27, 28, 29, 30]],
        "indicators": {"quote": [{"open": [10]*4, "high": [12]*4, "low": [9]*4, "close": [11]*4, "volume": [100]*4}]},
        "events": {"splits": {}},
    }]}}


def _fetch(payload=None):
    payload = _payload() if payload is None else payload
    return lambda url: (json.dumps(payload).encode(), url)


def test_personal_price_history_is_dated_with_adjustment_hold_and_excludes_observation_day(tmp_path, monkeypatch):
    from src.online_company_prices import fetch_online_company_prices
    monkeypatch.chdir(tmp_path)
    result = fetch_online_company_prices("FICT", observed_at=OBSERVED, fetcher=_fetch())
    assert result["status"] == "inspection_only"
    assert len(result["bars"]) == 3
    assert result["last_price_date"] == "2026-10-29"
    assert result["bars"][-1]["close"] == 11
    assert result["adjustment_basis"] == "provider_close_adjustment_basis_unverified"
    assert result["issuer_identity_status"] == "not_reconciled_to_sec"
    assert result["rights_status"] == "exact_source_unregistered_personal_inspection_only"
    assert result["commercial_eligible"] is False
    assert len(result["payload_sha256"]) == 64
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("change", ["symbol", "currency", "type", "timezone", "duplicate", "future", "length", "boolean", "string", "negative", "ohlc"])
def test_invalid_price_identity_or_rows_are_withheld(change):
    from src.online_company_prices import fetch_online_company_prices
    payload = _payload(); r = payload["chart"]["result"][0]; q = r["indicators"]["quote"][0]
    if change == "symbol": r["meta"]["symbol"] = "OTHER"
    elif change == "currency": r["meta"]["currency"] = "CAD"
    elif change == "type": r["meta"]["instrumentType"] = "ETF"
    elif change == "timezone": r["meta"]["exchangeTimezoneName"] = "invalid/zone"
    elif change == "duplicate": r["timestamp"][1] = r["timestamp"][0]
    elif change == "future": r["timestamp"][-1] += 86400
    elif change == "length": q["close"].pop()
    elif change == "boolean": q["close"][0] = True
    elif change == "string": q["close"][0] = "11"
    elif change == "negative": q["close"][0] = -1
    else: q["high"][0] = 8
    result = fetch_online_company_prices("FICT", observed_at=OBSERVED, fetcher=_fetch(payload))
    assert result["status"] == "unavailable"
    assert result["bars"] == []


def test_missing_bar_is_recorded_without_inventing_a_price():
    from src.online_company_prices import fetch_online_company_prices
    payload = _payload(); q = payload["chart"]["result"][0]["indicators"]["quote"][0]
    for values in q.values(): values[0] = None
    result = fetch_online_company_prices("FICT", observed_at=OBSERVED, fetcher=_fetch(payload))
    assert result["status"] == "inspection_only"
    assert len(result["bars"]) == 2
    assert result["missing_bar_count"] == 1


def test_class_share_alias_is_explicit_and_response_must_match_provider_symbol():
    from src.online_company_prices import fetch_online_company_prices
    payload = _payload(); payload["chart"]["result"][0]["meta"]["symbol"] = "BRK-B"
    result = fetch_online_company_prices("BRK.B", observed_at=OBSERVED, fetcher=_fetch(payload))
    assert result["ticker"] == "BRK.B" and result["provider_symbol"] == "BRK-B"


def test_source_failure_redirect_and_oversize_responses_are_withheld():
    from src.online_company_prices import fetch_online_company_prices, MAX_PRICE_BYTES
    def fail(_): raise OSError("private network diagnostic")
    for fetcher in [fail, lambda url: (b'{}', 'https://example.invalid/'), lambda url: (b'x'*(MAX_PRICE_BYTES+1), url)]:
        result = fetch_online_company_prices("FICT", observed_at=OBSERVED, fetcher=fetcher)
        assert result["status"] == "unavailable" and result["bars"] == []
        assert "private network diagnostic" not in str(result)


def test_session_fetch_is_explicit_ticker_scoped_and_commercial_mode_blocks_reuse(monkeypatch):
    from src.online_company_prices import get_online_company_prices
    calls = []; session = {}
    def fetcher(url): calls.append(url); return _fetch()(url)
    monkeypatch.delenv("COMMERCIAL_RESEARCH_MODE", raising=False)
    get_online_company_prices("FICT", session, refresh_requested=False, fetcher=fetcher, observed_at=OBSERVED)
    assert not calls
    ready = get_online_company_prices("FICT", session, refresh_requested=True, fetcher=fetcher, observed_at=OBSERVED)
    assert ready["status"] == "inspection_only"
    get_online_company_prices("FICT", session, refresh_requested=False, fetcher=fetcher, observed_at=OBSERVED)
    assert len(calls) == 1
    assert get_online_company_prices("OTHER", session, refresh_requested=False)["status"] == "not_requested"
    monkeypatch.setenv("COMMERCIAL_RESEARCH_MODE", "1")
    assert get_online_company_prices("FICT", session, refresh_requested=False)["reason"] == "commercial_rights_unreviewed"
    assert len(calls) == 1


def test_public_mode_cannot_activate_personal_price_inspection():
    from src.online_company_prices import get_online_company_prices
    result = get_online_company_prices("FICT", {}, refresh_requested=True, workspace_mode="public", fetcher=lambda _: pytest.fail("public fetch"))
    assert result["status"] == "unavailable"
