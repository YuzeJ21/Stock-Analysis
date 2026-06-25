from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SEC_SUBMISSIONS_URL_TEMPLATE = "https://data.sec.gov/submissions/CIK{cik}.json"
SEC_SUBMISSIONS_METADATA_BOUNDARY = (
    "SEC submissions metadata supports ticker/entity/SIC/filing-recency evidence only; "
    "it does not unlock fundamentals, share count, DCF, valuation, earnings, or analyst estimates."
)


def normalize_cik(cik: str | int) -> str:
    text = str(cik).upper().replace("CIK", "").strip()
    digits = "".join(character for character in text if character.isdigit())
    if not digits:
        raise ValueError("SEC CIK is required for SEC submissions metadata.")
    return digits.zfill(10)


def sec_submission_url(cik: str | int) -> str:
    return SEC_SUBMISSIONS_URL_TEMPLATE.format(cik=normalize_cik(cik))


def _require_user_agent(user_agent: str | None = None) -> str:
    resolved = (user_agent or os.environ.get("SEC_USER_AGENT", "")).strip()
    if not resolved:
        raise ValueError(
            "SEC requests require an identifying User-Agent. Pass --sec-user-agent "
            "or set SEC_USER_AGENT in the environment."
        )
    return resolved


def _submissions_cache_path(cache_dir: Path, cik: str) -> Path:
    path = cache_dir / "submissions"
    path.mkdir(parents=True, exist_ok=True)
    return path / f"CIK{cik}.json"


def read_cached_sec_submission(cik: str | int, *, cache_dir: str | Path = "data/cache/sec") -> dict[str, Any] | None:
    cache_path = _submissions_cache_path(Path(cache_dir), normalize_cik(cik))
    if not cache_path.exists():
        return None
    payload = json.loads(cache_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def _fetch_json(url: str, user_agent: str, sleep_seconds: float = 0.2) -> Any:
    request = Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"SEC submissions request failed with HTTP {exc.code} for {url}") from exc
    except URLError as exc:
        raise RuntimeError(f"SEC submissions request failed for {url}: {exc.reason}") from exc
    time.sleep(max(0.0, sleep_seconds))
    return payload


def fetch_sec_submission(
    cik: str | int,
    user_agent: str | None = None,
    *,
    cache: bool = True,
    refresh: bool = False,
    cache_dir: str | Path = "data/cache/sec",
    sleep_seconds: float = 0.2,
    fetcher: Callable[[str, str, float], Any] | None = None,
) -> dict[str, Any]:
    resolved_user_agent = _require_user_agent(user_agent)
    normalized_cik = normalize_cik(cik)
    cache_root = Path(cache_dir)
    cache_path = _submissions_cache_path(cache_root, normalized_cik)
    if cache and cache_path.exists() and not refresh:
        return json.loads(cache_path.read_text(encoding="utf-8"))

    payload = (fetcher or _fetch_json)(sec_submission_url(normalized_cik), resolved_user_agent, sleep_seconds)
    if not isinstance(payload, dict):
        raise RuntimeError(f"SEC submissions metadata for CIK {normalized_cik} was not a JSON object.")
    if cache:
        cache_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def _string_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value).strip() for value in values if str(value).strip()]


def _joined(values: Any) -> str | None:
    items = _string_list(values)
    return ", ".join(items) if items else None


def _latest_recent_filing(recent: dict[str, Any]) -> dict[str, str | None]:
    forms = _string_list(recent.get("form"))
    filing_dates = _string_list(recent.get("filingDate"))
    report_dates = _string_list(recent.get("reportDate"))
    accessions = _string_list(recent.get("accessionNumber"))
    filing_count = max(len(forms), len(filing_dates), len(report_dates), len(accessions), 0)
    if filing_count == 0:
        return {
            "form": None,
            "filing_date": None,
            "report_date": None,
            "accession": None,
            "filing_count": 0,
        }

    def value_at(values: list[str], index: int) -> str | None:
        return values[index] if index < len(values) else None

    latest_index = max(
        range(filing_count),
        key=lambda index: (value_at(filing_dates, index) or "", -index),
    )
    return {
        "form": value_at(forms, latest_index),
        "filing_date": value_at(filing_dates, latest_index),
        "report_date": value_at(report_dates, latest_index),
        "accession": value_at(accessions, latest_index),
        "filing_count": filing_count,
    }


def build_sec_submission_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    recent = payload.get("filings", {}).get("recent", {})
    latest = _latest_recent_filing(recent if isinstance(recent, dict) else {})
    return {
        "source": "sec_submissions_metadata",
        "source_usage": "metadata_evidence_only",
        "sec_cik": normalize_cik(payload.get("cik", "")),
        "sec_entity_name": str(payload.get("name") or payload.get("entityName") or "").strip() or None,
        "sec_sic": str(payload.get("sic") or "").strip() or None,
        "sec_sic_description": str(payload.get("sicDescription") or "").strip() or None,
        "sec_fiscal_year_end": str(payload.get("fiscalYearEnd") or "").strip() or None,
        "sec_tickers": _joined(payload.get("tickers")),
        "sec_exchanges": _joined(payload.get("exchanges")),
        "sec_latest_form": latest["form"],
        "sec_latest_filing_date": latest["filing_date"],
        "sec_latest_report_date": latest["report_date"],
        "sec_latest_accession": latest["accession"],
        "sec_recent_filing_count": latest["filing_count"],
    }


def _empty_packet(
    *,
    ticker: str,
    status: str,
    reason_code: str,
    detail: str,
    cik: str | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "reason_code": reason_code,
        "detail": detail,
        "ticker": ticker,
        "sec_cik": cik,
        "source": "sec_submissions_metadata",
        "source_usage": "metadata_evidence_only",
        "proof_boundary": SEC_SUBMISSIONS_METADATA_BOUNDARY,
    }


def _ticker_matches_submission(ticker: str, metadata: dict[str, Any]) -> str:
    submission_tickers = {
        value.strip().upper()
        for value in str(metadata.get("sec_tickers") or "").split(",")
        if value.strip()
    }
    return "matched_sec_submission_tickers" if ticker in submission_tickers else "ticker_not_listed_in_sec_submission"


def build_sec_submission_metadata_packet(
    ticker: str,
    *,
    ticker_map: dict[str, dict[str, Any]],
    cache_dir: str | Path = "data/cache/sec",
    user_agent: str | None = None,
    allow_network: bool = False,
    fetcher: Callable[[str, str, float], Any] | None = None,
) -> dict[str, Any]:
    ticker_text = str(ticker or "").upper().strip()
    if not ticker_text:
        return _empty_packet(
            ticker="",
            status="unavailable",
            reason_code="missing_ticker",
            detail="Ticker is required for SEC submissions metadata.",
        )

    ticker_entry = ticker_map.get(ticker_text, {}) if isinstance(ticker_map, dict) else {}
    cik_value = ticker_entry.get("cik") or ticker_entry.get("cik_str") or ticker_entry.get("cikStr")
    if cik_value in (None, ""):
        return _empty_packet(
            ticker=ticker_text,
            status="unavailable",
            reason_code="ticker_not_found_in_sec_ticker_map",
            detail=f"{ticker_text} was not found in the SEC ticker map.",
        )

    cik = normalize_cik(cik_value)
    payload = read_cached_sec_submission(cik, cache_dir=cache_dir)
    source_detail = "cached SEC submissions metadata"
    if payload is None and allow_network:
        try:
            payload = fetch_sec_submission(cik, user_agent=user_agent, cache_dir=cache_dir, fetcher=fetcher)
            source_detail = "live SEC submissions metadata"
        except Exception as exc:
            return _empty_packet(
                ticker=ticker_text,
                status="unavailable",
                reason_code="request_failed",
                detail=f"SEC submissions metadata request failed for {ticker_text}: {exc}",
                cik=cik,
            )
    if payload is None:
        return _empty_packet(
            ticker=ticker_text,
            status="unavailable",
            reason_code="cached_submission_missing",
            detail=f"No cached SEC submissions metadata found for {ticker_text} CIK {cik}; remote retry disabled.",
            cik=cik,
        )

    metadata = build_sec_submission_metadata(payload)
    metadata.update(
        {
            "status": "available",
            "reason_code": "ok",
            "detail": f"Loaded {source_detail} for {ticker_text} CIK {cik}.",
            "ticker": ticker_text,
            "ticker_validation": _ticker_matches_submission(ticker_text, metadata),
            "proof_boundary": SEC_SUBMISSIONS_METADATA_BOUNDARY,
        }
    )
    return metadata
