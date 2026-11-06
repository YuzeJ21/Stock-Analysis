"""A bounded Personal Research proxy for dated, completed daily price availability."""

from collections.abc import Mapping, MutableMapping
from datetime import datetime, timedelta, timezone
import re
from urllib.request import Request
from zoneinfo import ZoneInfo

from src.company_sec_online_preview import _iso_date, _utc_timestamp
from src.online_company_identity import _VENUES as PROVIDER_VENUES
from src.online_company_prices import (
    MAX_PRICE_BYTES, _scope, completed_regular_session, fetch_online_company_prices, price_source_url,
)
from src.online_research_history_view import validated_online_price_history
from src.online_sec_receipt import open_exact_source
from src.online_us_universe import VENUES, _alias, _digest, validated_us_universe


SESSION_KEY = "online_industry_price_coverage_v1"
MAX_SESSION_CHECKS = 20
_MARKET_ZONE = ZoneInfo("America/New_York")
_TICKER = re.compile(r"[A-Z0-9][A-Z0-9.-]{0,19}\Z")
_CIK = re.compile(r"[0-9]{10}\Z")
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_SUPPORTED_VENUES = {venue for venue, _ in PROVIDER_VENUES.values()}
_AVAILABLE = "completed_bar_available"
_UNAVAILABLE = {
    "no_recent_completed_price": "A recent completed daily bar could not be established.",
    "price_evidence_unverified": "The provider response could not be verified.",
    "price_exchange_mismatch": "The provider exchange did not match the observed listing venue.",
    "price_source_unavailable": "The provider did not return a usable response.",
    "price_symbol_or_security_type_mismatch": "The provider symbol or equity type did not match.",
    "unsupported_price_currency": "The provider did not report the price in USD.",
}
_ACTION_MESSAGES = {
    "listing_inventory_unverified": "Load a verified listing inventory before checking prices.",
    "listing_inventory_refresh_required": "Load a fresh listing inventory before checking prices.",
    "price_route_unavailable": "Use an issuer's representative ticker with a matching SEC search route and supported listing venue.",
    "price_issuer_already_checked": "This issuer has already been checked in this session.",
    "price_session_limit_reached": "This session has reached the 20-issuer price check limit.",
    "price_session_unverified": "The session's price checks could not be validated.",
}


def _inventory(value):
    try:
        return validated_us_universe(value)
    except (TypeError, ValueError, KeyError, AttributeError, RecursionError):
        return None


def _inventory_fresh(inventory, now):
    try:
        now = now.astimezone(timezone.utc)
        for index, ref in enumerate(inventory["source_receipts"]):
            observed = _utc_timestamp(ref["observed_at"])
            if observed is None or not timedelta(0) <= now - observed <= timedelta(hours=24):
                return False
            if index < 2:
                value = ref["source_created_at"]
                created = datetime.strptime(value, "%Y-%m-%dT%H:%M")
                if created.strftime("%Y-%m-%dT%H:%M") != value:
                    return False
                created = created.replace(tzinfo=_MARKET_ZONE).astimezone(timezone.utc)
                if not timedelta(0) <= now - created <= timedelta(days=7):
                    return False
        return True
    except (TypeError, ValueError, KeyError, OverflowError):
        return False


def _route(inventory, ticker):
    if not isinstance(ticker, str) or _TICKER.fullmatch(ticker) is None:
        return None
    cik = next((row["sec_cik"] for row in inventory["issuer_queue"] if row["ticker"] == ticker), None)
    if cik is None:
        return None
    matches = [row for row in inventory["rows"] if _alias(row["symbol"]) == _alias(ticker)]
    if len(matches) != 1:
        return None
    row, = matches
    if (row["sec_cik"] != cik or row["sec_ticker"] != ticker or row.get("discover_searchable") is not True
        or row["source"] not in {"nasdaq", "other"} or row["etf"] is not False
        or row["association_reason"] != "source_symbol_cik_matched"
        or row["venue"] not in _SUPPORTED_VENUES or VENUES.get(row["venue_code"]) != row["venue"]):
        return None
    return cik, row["venue"]


def _provider_venue(code, full_name):
    venue = PROVIDER_VENUES.get(code) if isinstance(code, str) else None
    if venue is None or (full_name is not None and (not isinstance(full_name, str) or full_name not in venue[1])):
        return None
    return venue[0]


def _recent_market_date(value, observed):
    day = _iso_date(value)
    if day is not None and observed is not None and day.weekday() < 5:
        if 0 <= (observed.astimezone(_MARKET_ZONE).date() - day).days <= 7:
            return day
    return None


def _valid_receipt(source, ticker, day, attempted):
    if not isinstance(source, Mapping) or set(source) != {
        "source_url", "observed_at", "payload_sha256", "exchange_code", "full_exchange_name",
    }:
        return False
    observed = _utc_timestamp(source["observed_at"])
    digest = source["payload_sha256"]
    return (source["source_url"] == price_source_url(_alias(ticker))
        and isinstance(digest, str) and _SHA.fullmatch(digest) is not None
        and observed is not None and timedelta(0) <= observed - attempted <= timedelta(minutes=1)
        and _recent_market_date(day, observed) is not None
        and _provider_venue(source["exchange_code"], source["full_exchange_name"]) is not None)


def _attempts(state):
    if not isinstance(state, Mapping):
        return None
    packets = state.get(SESSION_KEY, [])
    if not isinstance(packets, list) or len(packets) > MAX_SESSION_CHECKS:
        return None
    seen = set()
    for packet in packets:
        if not isinstance(packet, Mapping) or set(packet) != {"inventory_fingerprint", "attempt", "source", "digest"}:
            return None
        fingerprint, attempt, source = (packet[key] for key in ("inventory_fingerprint", "attempt", "source"))
        if not isinstance(fingerprint, str) or _SHA.fullmatch(fingerprint) is None or not isinstance(attempt, Mapping):
            return None
        available = attempt.get("available")
        keys = {"ticker", "sec_cik", "attempted_at", "available", "reason"}
        if type(available) is not bool or set(attempt) != (keys | {"price_date"} if available else keys):
            return None
        ticker, cik, reason = (attempt[key] for key in ("ticker", "sec_cik", "reason"))
        attempted = _utc_timestamp(attempt["attempted_at"])
        if (not isinstance(ticker, str) or _TICKER.fullmatch(ticker) is None or not isinstance(cik, str)
            or _CIK.fullmatch(cik) is None or int(cik) == 0 or cik in seen or attempted is None):
            return None
        if available:
            if reason != _AVAILABLE or not _valid_receipt(source, ticker, attempt["price_date"], attempted):
                return None
        elif source is not None or not isinstance(reason, str) or reason not in _UNAVAILABLE:
            return None
        if packet["digest"] != _digest({k: packet[k] for k in ("inventory_fingerprint", "attempt", "source")}):
            return None
        seen.add(cik)
    return packets


def _fetch_exact(url):
    request = Request(url, headers={"User-Agent": "StockResearchCommandCenter/1.0 personal-research", "Accept": "application/json"})
    with open_exact_source(request, timeout=20) as response:
        return response.read(MAX_PRICE_BYTES + 1), response.geturl()


def _price_evidence(result, ticker, venue, attempted):
    if result.get("status") != "inspection_only":
        reason = result.get("reason")
        if reason == "no_completed_daily_prices":
            reason = "no_recent_completed_price"
        return (reason if reason in _UNAVAILABLE else "price_evidence_unverified"), None
    prices = validated_online_price_history(result, ticker=ticker)
    if (prices is None or prices.get("instrument_type") != "EQUITY"
        or prices.get("exchange_timezone") != _MARKET_ZONE.key):
        return "price_evidence_unverified", None
    if _provider_venue(prices.get("exchange_code"), prices.get("full_exchange_name")) != venue:
        return "price_exchange_mismatch", None
    observed = _utc_timestamp(prices["observed_at"])
    day = _recent_market_date(prices["last_price_date"], observed)
    if day is None:
        return "no_recent_completed_price", None
    if day == observed.astimezone(_MARKET_ZONE).date():
        session = completed_regular_session(prices.get("completed_regular_session"), _MARKET_ZONE, observed)
        if session is None or session.date() != day:
            return "no_recent_completed_price", None
    receipt = {key: prices.get(key) for key in ("source_url", "observed_at", "payload_sha256", "exchange_code", "full_exchange_name")}
    if not _valid_receipt(receipt, ticker, prices["last_price_date"], attempted):
        return "price_evidence_unverified", None
    return _AVAILABLE, receipt


def check_industry_price(state, inventory, ticker, *, observed_at=None, fetcher=None, workspace_mode="research"):
    """Make a single provider request for an explicitly selected, eligible issuer."""
    reason = _scope(workspace_mode)
    if reason:
        return {"status": "unavailable", "reason": reason}
    checked = _inventory(inventory)
    if checked is None:
        return {"status": "unavailable", "reason": "listing_inventory_unverified"}
    now = observed_at if observed_at is not None else datetime.now(timezone.utc)
    if not isinstance(now, datetime) or now.utcoffset() is None or not _inventory_fresh(checked, now):
        return {"status": "unavailable", "reason": "listing_inventory_refresh_required"}
    packets = _attempts(state)
    if packets is None or not isinstance(state, MutableMapping):
        return {"status": "unavailable", "reason": "price_session_unverified"}
    ticker = ticker.strip().upper() if isinstance(ticker, str) else ""
    route = _route(checked, ticker)
    if route is None:
        return {"status": "unavailable", "reason": "price_route_unavailable"}
    cik, venue = route
    if any(packet["attempt"]["sec_cik"] == cik for packet in packets):
        return {"status": "unavailable", "reason": "price_issuer_already_checked"}
    if len(packets) >= MAX_SESSION_CHECKS:
        return {"status": "unavailable", "reason": "price_session_limit_reached"}
    attempted = now.astimezone(timezone.utc).replace(microsecond=0)
    try:
        result = fetch_online_company_prices(ticker, observed_at=observed_at, fetcher=fetcher or _fetch_exact,
            workspace_mode=workspace_mode, include_verified_session_close=True)
        reason, source = _price_evidence(result, ticker, venue, attempted)
    except (TypeError, ValueError, KeyError, AttributeError, OverflowError, RecursionError):
        reason, source = "price_evidence_unverified", None
    attempt = {"ticker": ticker, "sec_cik": cik, "attempted_at": attempted.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "available": source is not None, "reason": reason}
    if source is not None:
        attempt["price_date"] = result["last_price_date"]
    packet = {"inventory_fingerprint": checked["inventory_fingerprint"], "attempt": attempt, "source": source}
    state[SESSION_KEY] = [*packets, {**packet, "digest": _digest(packet)}]
    return {"status": "recorded", "attempt": dict(attempt)}


def read_price_coverage(state, inventory):
    """Read matching dated availability only. Stale inventories cannot initiate a check."""
    if _scope("research"):
        return []
    packets = _attempts(state)
    if not packets:
        return []
    checked = _inventory(inventory)
    if checked is None:
        return []
    rows = []
    for packet in packets:
        if packet["inventory_fingerprint"] != checked["inventory_fingerprint"]:
            continue
        attempt = packet["attempt"]
        route = _route(checked, attempt["ticker"])
        if (route is None or route[0] != attempt["sec_cik"]
            or not _inventory_fresh(checked, _utc_timestamp(attempt["attempted_at"]))):
            return []
        source = packet["source"]
        if source is not None and _provider_venue(source["exchange_code"], source["full_exchange_name"]) != route[1]:
            return []
        rows.append(dict(attempt))
    return rows


def render_industry_price_control(st, inventory):
    """Render an explicit one-ticker check. Ordinary rerenders only read session state."""
    if _scope("research"):
        return
    st.caption("Price availability uses a Yahoo Finance ticker and exchange match as a proxy. "
        "The SEC search supplies the issuer ID. Nasdaq, NYSE and NYSE American only. Check each issuer once, up to 20 issuers per session. "
        "Personal inspection only. Commercial and redistribution rights are unreviewed.")
    checked = _inventory(inventory)
    if checked is None or not _inventory_fresh(checked, datetime.now(timezone.utc)):
        st.caption(_ACTION_MESSAGES["listing_inventory_refresh_required"])
        return
    packets = _attempts(st.session_state)
    if packets is None or len(packets) >= MAX_SESSION_CHECKS:
        reason = "price_session_unverified" if packets is None else "price_session_limit_reached"
        st.caption(_ACTION_MESSAGES[reason])
        return
    with st.form("industry-price-check-form"):
        ticker = st.text_input("Representative issuer ticker", max_chars=20, key="industry-price-check-ticker")
        requested = st.form_submit_button("Check one issuer’s price")
    if requested:
        with st.spinner("Checking for a completed daily price…"):
            result = check_industry_price(st.session_state, checked, ticker)
        if result["status"] != "recorded":
            st.caption(_ACTION_MESSAGES.get(result["reason"], "The price check is unavailable."))
        else:
            attempt = result["attempt"]
            detail = f"Completed daily bar dated {attempt['price_date']}." if attempt["available"] else _UNAVAILABLE[attempt["reason"]]
            st.caption(f"{attempt['ticker']} · {detail}")
