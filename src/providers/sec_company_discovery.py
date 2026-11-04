"""Read-only, source-bound SEC ticker/CIK candidate search.

``fetcher(url, user_agent)`` must return ``(raw_bytes, headers_mapping)``.
The default fetcher makes one bounded SEC request. No result is persisted.
Candidates are search associations, not verified security identities, listing
states, issuer domicile, financial coverage, or analysis eligibility.
"""

from __future__ import annotations

import hashlib
import os
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Callable, Mapping
from urllib.request import Request, urlopen

from src.sec_association_receipt import _json_object, _rows


SEC_COMPANY_DIRECTORY_URL = "https://www.sec.gov/files/company_tickers_exchange.json"
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
_MAX_QUERY_LENGTH = 120
_MAX_RESULTS = 20
_PARSER_REASONS = frozenset({
    "json_duplicate_key", "sec_map_schema_invalid", "sec_map_row_invalid",
})


def _fetch_raw(url: str, user_agent: str) -> tuple[bytes, Mapping[str, str]]:
    request = Request(
        url,
        headers={"User-Agent": user_agent, "Accept": "application/json"},
    )
    with urlopen(request, timeout=30) as response:
        if response.geturl() != url:
            raise RuntimeError("SEC directory response redirected")
        return response.read(MAX_RESPONSE_BYTES + 1), dict(response.headers.items())


def _unavailable(
    query: str,
    reason: str,
    observed_at: str | None = None,
    payload_sha256: str | None = None,
    source_last_modified: str | None = None,
) -> dict[str, Any]:
    return {
        "status": "unavailable",
        "query": query,
        "candidates": [],
        "source_url": SEC_COMPANY_DIRECTORY_URL,
        "observed_at": observed_at,
        "source_last_modified": source_last_modified,
        "payload_sha256": payload_sha256,
        "reason": reason,
    }


def _utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _modified_at(headers: Mapping[str, str], observed_at: datetime) -> str | None:
    values = [
        value for key, value in headers.items()
        if isinstance(key, str) and key.casefold() == "last-modified"
    ]
    if not values:
        return None
    if len(values) != 1 or not isinstance(values[0], str):
        raise ValueError("invalid_last_modified")
    try:
        modified = parsedate_to_datetime(values[0])
    except (TypeError, ValueError, IndexError) as exc:
        raise ValueError("invalid_last_modified") from exc
    if modified.tzinfo is None or modified > observed_at:
        raise ValueError("invalid_last_modified")
    return _utc_iso(modified)


def _candidates(rows: list[dict[str, object]], query: str, limit: int) -> list[dict[str, object]]:
    distinct_ciks: dict[str, set[int]] = defaultdict(set)
    for row in rows:
        distinct_ciks[str(row["ticker"])].add(int(row["cik"]))
    matched = [
        row for row in rows
        if query in str(row["ticker"]).casefold()
        or query in str(row["name"]).casefold()
    ]
    seen: set[tuple[str, int]] = set()
    found: list[dict[str, object]] = []
    for row in matched:
        ticker, cik = str(row["ticker"]), int(row["cik"])
        key = ticker, cik
        if key in seen:
            continue
        seen.add(key)
        candidate: dict[str, object] = {
            "ticker": ticker,
            "cik": str(cik).zfill(10),
            "title": str(row["name"]),
            "ambiguous": len(distinct_ciks[ticker]) > 1,
        }
        if row["exchange"]:
            candidate["exchange"] = str(row["exchange"])
        found.append(candidate)

    def rank(candidate: dict[str, object]) -> tuple[int, str, str]:
        ticker = str(candidate["ticker"])
        title = str(candidate["title"])
        if ticker.casefold() == query:
            priority = 0
        elif ticker.casefold().startswith(query):
            priority = 1
        elif title.casefold().startswith(query):
            priority = 2
        else:
            priority = 3
        return priority, ticker, str(candidate["cik"])

    found.sort(key=rank)
    return found[:limit]


def search_sec_company_candidates(
    query: str,
    *,
    user_agent: str | None,
    fetcher: Callable[[str, str], tuple[bytes, Mapping[str, str]]] | None = None,
    observed_at: datetime | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Search official SEC ticker associations on request, entirely in memory.

    ``fetcher`` is injectable for deterministic testing and must return raw
    bytes and an HTTP-like string header mapping. ``source_last_modified`` is
    optional; ``observed_at`` is the UTC fetch observation. Each candidate
    retains its CIK so callers can independently verify later SEC facts.
    """

    cleaned_query = query.strip() if isinstance(query, str) else ""
    if (
        not cleaned_query or len(cleaned_query) > _MAX_QUERY_LENGTH
        or any(unicodedata.category(char) in {"Cc", "Cf"} for char in cleaned_query)
    ):
        return _unavailable(cleaned_query, "invalid_query")
    if user_agent is not None and not isinstance(user_agent, str):
        return _unavailable(cleaned_query, "sec_user_agent_required")
    agent = (user_agent or os.getenv("SEC_USER_AGENT", "")).strip()
    if not agent or any(char in agent for char in "\r\n"):
        return _unavailable(cleaned_query, "sec_user_agent_required")
    if type(limit) is not int or limit <= 0:
        return _unavailable(cleaned_query, "invalid_limit")
    if observed_at is not None and (
        not isinstance(observed_at, datetime) or observed_at.tzinfo is None
        or observed_at.utcoffset() is None
    ):
        return _unavailable(cleaned_query, "invalid_observed_at")

    try:
        response = (fetcher or _fetch_raw)(SEC_COMPANY_DIRECTORY_URL, agent)
    except (OSError, RuntimeError, TimeoutError, ValueError):
        return _unavailable(cleaned_query, "sec_fetch_unavailable")
    observed = observed_at or datetime.now(timezone.utc)
    observed_iso = _utc_iso(observed)
    if (
        not isinstance(response, tuple) or len(response) != 2
        or not isinstance(response[0], bytes)
        or not isinstance(response[1], Mapping)
    ):
        return _unavailable(cleaned_query, "invalid_response", observed_iso)
    raw, headers = response
    if len(raw) == 0 or len(raw) > MAX_RESPONSE_BYTES:
        return _unavailable(cleaned_query, "invalid_response_size", observed_iso)
    digest = hashlib.sha256(raw).hexdigest()
    try:
        modified_iso = _modified_at(headers, observed)
    except ValueError:
        return _unavailable(cleaned_query, "invalid_last_modified", observed_iso, digest)
    try:
        rows = _rows(_json_object(raw, "sec_map_schema_invalid"))
    except (ValueError, RecursionError) as exc:
        reason = str(exc) if str(exc) in _PARSER_REASONS else "sec_map_schema_invalid"
        return _unavailable(cleaned_query, reason, observed_iso, digest, modified_iso)
    if any(int(row["cik"]) > 9_999_999_999 for row in rows):
        return _unavailable(cleaned_query, "sec_map_row_invalid", observed_iso, digest, modified_iso)
    return {
        "status": "ready",
        "query": cleaned_query,
        "candidates": _candidates(rows, cleaned_query.casefold(), min(limit, _MAX_RESULTS)),
        "source_url": SEC_COMPANY_DIRECTORY_URL,
        "observed_at": observed_iso,
        "source_last_modified": modified_iso,
        "payload_sha256": digest,
    }
