"""Session-only Yahoo chart inspection for Personal Research, without data apply.

This exact endpoint is not registered for commercial distribution. It does not
inherit the yfinance registry entry and never establishes a SEC issuer join.
"""

from __future__ import annotations

import hashlib
import math
import re
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, MutableMapping
from urllib.parse import quote
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from src.commercial_source_rights import commercial_mode_enabled
from src.sec_association_receipt import _json_object

MAX_PRICE_BYTES = 2 * 1024 * 1024
SESSION_KEY = "online_company_price_inspection_v1"


def _held(ticker: str, reason: str) -> dict[str, Any]:
    return {"status": "unavailable", "ticker": ticker, "reason": reason, "bars": [], "commercial_eligible": False}


def _scope(workspace_mode: str) -> str | None:
    if workspace_mode != "research":
        return "personal_research_mode_required"
    try:
        return "commercial_rights_unreviewed" if commercial_mode_enabled() else None
    except ValueError:
        return "invalid_commercial_mode_configuration"


def _raw_fetch(url: str) -> tuple[bytes, str]:
    request = Request(url, headers={"User-Agent": "StockResearchCommandCenter/1.0 personal-research", "Accept": "application/json"})
    with urlopen(request, timeout=20) as response:
        return response.read(MAX_PRICE_BYTES + 1), response.geturl()


def _number(value: Any, *, positive: bool = True) -> bool:
    try:
        return type(value) in {int, float} and math.isfinite(value) and abs(value) <= 1e20 and (value > 0 if positive else value >= 0)
    except OverflowError:
        return False


def fetch_online_company_prices(
    ticker: str, *, observed_at: datetime | None = None,
    fetcher: Callable[[str], tuple[bytes, str]] | None = None, workspace_mode: str = "research",
) -> dict[str, Any]:
    ticker = ticker.strip().upper() if isinstance(ticker, str) else ""
    reason = _scope(workspace_mode)
    if reason:
        return _held(ticker, reason)
    if re.fullmatch(r"[A-Z0-9][A-Z0-9.-]{0,19}", ticker) is None:
        return _held(ticker[:24], "invalid_ticker")
    if observed_at is not None and (not isinstance(observed_at, datetime) or observed_at.utcoffset() is None):
        return _held(ticker, "invalid_observation")
    symbol = ticker.replace(".", "-")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol, safe='')}?range=1y&interval=1d&events=div%2Csplits&includeAdjustedClose=true"
    try:
        raw, response_url = (fetcher or _raw_fetch)(url)
    except (OSError, RuntimeError, TimeoutError, ValueError, TypeError):
        return _held(ticker, "price_source_unavailable")
    observed = (observed_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_PRICE_BYTES or response_url != url:
        return _held(ticker, "unverified_price_response")
    try:
        parsed = _json_object(raw, "invalid_price_payload")
        chart = parsed["chart"]
        results = chart["result"]
        if chart.get("error") is not None or not isinstance(results, list) or len(results) != 1:
            return _held(ticker, "price_source_unavailable")
        result = results[0]; meta = result["meta"]
        if meta.get("symbol") != symbol or meta.get("instrumentType") != "EQUITY":
            return _held(ticker, "price_symbol_or_security_type_mismatch")
        if meta.get("currency") != "USD":
            return _held(ticker, "unsupported_price_currency")
        market_zone = ZoneInfo(meta["exchangeTimezoneName"])
        market_today = observed.astimezone(market_zone).date()
        timestamps = result["timestamp"]
        quotes = result["indicators"]["quote"]
        if not isinstance(timestamps, list) or not 1 <= len(timestamps) <= 400 or not isinstance(quotes, list) or len(quotes) != 1:
            return _held(ticker, "invalid_price_schema")
        q = quotes[0]
        if any(not isinstance(q.get(k), list) or len(q[k]) != len(timestamps) for k in ("open", "high", "low", "close", "volume")):
            return _held(ticker, "invalid_price_schema")
        bars = []; dates = set(); missing = 0; excluded = 0; previous = None
        for index, stamp in enumerate(timestamps):
            if type(stamp) is not int or previous is not None and stamp <= previous:
                return _held(ticker, "duplicate_or_unordered_price_timestamp")
            previous = stamp
            instant = datetime.fromtimestamp(stamp, tz=timezone.utc)
            if instant > observed:
                return _held(ticker, "future_price_timestamp")
            day = instant.astimezone(market_zone).date()
            if day in dates:
                return _held(ticker, "duplicate_daily_price")
            dates.add(day)
            if day >= market_today:
                excluded += 1
                continue
            values = {key: q[key][index] for key in ("open", "high", "low", "close", "volume")}
            if all(value is None for value in values.values()):
                missing += 1
                continue
            if any(not _number(value, positive=key != "volume") for key, value in values.items()):
                return _held(ticker, "invalid_raw_price_value")
            if values["high"] < max(values["open"], values["low"], values["close"]) or values["low"] > min(values["open"], values["high"], values["close"]):
                return _held(ticker, "inconsistent_ohlc")
            bars.append({"date": day.isoformat(), **values})
        if not bars:
            return _held(ticker, "no_completed_daily_prices")
        raw_splits = result.get("events", {}).get("splits", {})
        if not isinstance(raw_splits, Mapping) or len(raw_splits) > 64:
            return _held(ticker, "invalid_split_events")
        splits = []
        for event in raw_splits.values():
            if not isinstance(event, Mapping) or type(event.get("date")) is not int or not _number(event.get("numerator")) or not _number(event.get("denominator")):
                return _held(ticker, "invalid_split_events")
            instant = datetime.fromtimestamp(event["date"], tz=timezone.utc)
            if instant > observed:
                return _held(ticker, "future_split_event")
            splits.append({"date": instant.astimezone(market_zone).date().isoformat(), "numerator": event["numerator"], "denominator": event["denominator"]})
        age = (market_today - datetime.fromisoformat(bars[-1]["date"]).date()).days
    except (KeyError, AttributeError, TypeError, ValueError, OverflowError, OSError):
        return _held(ticker, "invalid_price_payload")
    return {
        "status": "inspection_only", "ticker": ticker, "provider_symbol": symbol,
        "currency": "USD", "source_id": "yahoo_chart", "source_url": url,
        "observed_at": observed.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "payload_sha256": hashlib.sha256(raw).hexdigest(), "exchange_timezone": meta["exchangeTimezoneName"],
        "bars": bars, "splits": splits, "last_price_date": bars[-1]["date"],
        "observation_state": "recent_dated_observation" if age <= 7 else "stale_observation",
        "missing_bar_count": missing, "excluded_incomplete_day_count": excluded,
        "adjustment_basis": "provider_close_adjustment_basis_unverified", "issuer_identity_status": "not_reconciled_to_sec",
        "rights_status": "exact_source_unregistered_personal_inspection_only", "commercial_eligible": False,
    }


def get_online_company_prices(
    ticker: str, session_state: MutableMapping[str, Any], *, refresh_requested: bool,
    workspace_mode: str = "research", fetcher=None, observed_at=None,
) -> dict[str, Any]:
    ticker = str(ticker or "").strip().upper()
    reason = _scope(workspace_mode)
    if reason:
        return _held(ticker, reason)
    if not refresh_requested:
        cached = session_state.get(SESSION_KEY)
        if isinstance(cached, Mapping) and cached.get("ticker") == ticker:
            return dict(cached)
        return {"status": "not_requested", "ticker": ticker, "bars": []}
    result = fetch_online_company_prices(ticker, workspace_mode=workspace_mode, fetcher=fetcher, observed_at=observed_at)
    session_state[SESSION_KEY] = result
    return result
