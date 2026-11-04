"""Session-only view model for SEC company search candidates."""

from __future__ import annotations

import html
import re
from datetime import datetime, timedelta
from typing import Any, Mapping


ONLINE_COMPANY_SESSION_KEY = "online_company_search_v1"
SEC_ASSOCIATION_URL = "https://www.sec.gov/files/company_tickers_exchange.json"
_TICKER = re.compile(r"[A-Z0-9][A-Z0-9.$-]{0,20}\Z")
_CIK = re.compile(r"\d{10}\Z")
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")


def _valid_observation(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.utcoffset() == timedelta(0) and value.endswith("Z")


def _trusted_result(result: object) -> Mapping[str, Any] | None:
    if not isinstance(result, Mapping):
        return None
    if (
        result.get("status") != "ready"
        or result.get("source_url") != SEC_ASSOCIATION_URL
        or not _valid_observation(result.get("observed_at"))
        or not isinstance(result.get("payload_sha256"), str)
        or _DIGEST.fullmatch(result["payload_sha256"]) is None
    ):
        return None
    candidates = result.get("candidates")
    if not isinstance(candidates, list) or len(candidates) > 20:
        return None
    return result


def online_company_candidate_for_route(
    ticker: str, session_state: Mapping[str, Any]
) -> dict[str, Any] | None:
    normalized = str(ticker or "").strip().upper()
    if _TICKER.fullmatch(normalized) is None or not isinstance(session_state, Mapping):
        return None
    result = _trusted_result(session_state.get(ONLINE_COMPANY_SESSION_KEY))
    if result is None:
        return None
    matches = [
        candidate for candidate in result["candidates"]
        if isinstance(candidate, Mapping) and candidate.get("ticker") == normalized
    ]
    if len(matches) != 1:
        return None
    candidate = matches[0]
    cik = candidate.get("cik")
    if (
        candidate.get("ambiguous") is not False
        or not isinstance(cik, str)
        or _CIK.fullmatch(cik) is None
        or not isinstance(candidate.get("title"), str)
        or not candidate["title"].strip()
    ):
        return None
    return {
        "ticker": normalized,
        "cik": cik,
        "title": candidate["title"],
        "exchange": str(candidate.get("exchange") or ""),
        "observed_at": result["observed_at"],
        "source_last_modified": result.get("source_last_modified"),
        "source_url": SEC_ASSOCIATION_URL,
        "payload_sha256": result["payload_sha256"],
    }


def online_company_results_html(
    result: Mapping[str, Any] | None, *, saved_tickers: set[str] | tuple[str, ...]
) -> str:
    if result is None:
        return (
            "<section class='selector-result-table online-company-results' aria-label='SEC online company results'>"
            "<p>Search the SEC company association directory by ticker or name. "
            "Results are online candidates; saved research is shown separately below.</p></section>"
        )
    if not isinstance(result, Mapping) or result.get("status") != "ready":
        reason = str(result.get("reason") or "source_unavailable") if isinstance(result, Mapping) else "source_unavailable"
        messages = {
            "sec_user_agent_required": "Set SEC_USER_AGENT to an identifying name and contact before searching SEC online.",
            "invalid_query": "Enter a ticker or company name to search SEC online.",
            "source_unavailable": "SEC online company search is unavailable. No local row has been substituted for a live result.",
        }
        message = messages.get(reason, messages["source_unavailable"])
        return f"<section class='selector-result-table online-company-results' role='status'><p>{html.escape(message)}</p></section>"
    trusted = _trusted_result(result)
    if trusted is None:
        return (
            "<section class='selector-result-table online-company-results' role='status'>"
            "<p>SEC online response could not be verified. No company result is shown.</p></section>"
        )
    saved = {str(value).strip().upper() for value in saved_tickers}
    rows: list[str] = []
    for candidate in trusted["candidates"]:
        if not isinstance(candidate, Mapping):
            continue
        ticker = candidate.get("ticker")
        cik = candidate.get("cik")
        title = candidate.get("title")
        if (
            not isinstance(ticker, str) or _TICKER.fullmatch(ticker) is None
            or not isinstance(cik, str) or _CIK.fullmatch(cik) is None
            or not isinstance(title, str) or not title.strip()
        ):
            continue
        label = (
            "Local ticker row exists; research evidence unverified"
            if ticker in saved else "No local ticker row"
        )
        ambiguous = candidate.get("ambiguous") is True
        identity = (
            f"<strong>{html.escape(ticker)}</strong> · {html.escape(title[:140])}"
            f"<span> SEC CIK {html.escape(cik)}"
            + (f" · {html.escape(str(candidate.get('exchange') or '')[:50])}" if candidate.get("exchange") else "")
            + "</span>"
        )
        if ambiguous:
            action = "<span>Ambiguous SEC association — review identity before opening.</span>"
        else:
            href = html.escape(
                f"?mode=research&page=company-workbench&ticker={ticker}&online=1", quote=True
            )
            action = f"<a class='selector-action-link' href='{href}' target='_self'>Open company evidence</a>"
        rows.append(
            "<div class='selector-result-row online-company-result'>"
            f"<div class='selector-result-identity'>{identity}</div>"
            f"<div class='selector-result-summary'>{html.escape(label)}</div>"
            f"<div class='selector-actions'>{action}</div></div>"
        )
    if not rows:
        rows.append("<p>No SEC association matched this exact online search.</p>")
    meta = (
        "<p class='online-company-source-meta'>SEC ticker association candidates · "
        f"observed {html.escape(str(trusted['observed_at']))} · "
        f"source last modified {html.escape(str(trusted.get('source_last_modified') or 'unavailable'))} · "
        f"SHA-256 {html.escape(str(trusted['payload_sha256'])[:16])}… "
        f"<a href='{html.escape(SEC_ASSOCIATION_URL, quote=True)}' target='_blank' rel='noopener noreferrer'>SEC source</a>. "
        "Directory identity rights require review before distribution.</p>"
    )
    boundary = (
        "<p class='sec-annual-boundary'>A SEC ticker association does not establish U.S. issuer domicile, "
        "security type, active listing, point-in-time coverage, financial coverage, or analysis eligibility.</p>"
    )
    return (
        "<section class='selector-result-table online-company-results' aria-label='SEC online company results'>"
        f"<h3>Online SEC matches for {html.escape(str(trusted.get('query') or '')[:80])}</h3>"
        "<p>Results are limited to 20; refine broad searches.</p>"
        + "".join(rows) + meta + boundary + "</section>"
    )
