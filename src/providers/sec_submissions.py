from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.parse import urljoin
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SEC_SUBMISSIONS_URL_TEMPLATE = "https://data.sec.gov/submissions/CIK{cik}.json"
SEC_FILING_DOCUMENT_URL_TEMPLATE = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{primary_document}"
SEC_FILING_INDEX_URL_TEMPLATE = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession_path}/{accession}-index.html"
SEC_SUBMISSIONS_METADATA_BOUNDARY = (
    "SEC submissions metadata supports ticker/entity/SIC/filing-recency evidence only; "
    "it does not unlock fundamentals, share count, DCF, valuation, earnings, or analyst estimates."
)
SEC_FILING_SHARE_COUNT_BOUNDARY = (
    "SEC filing-document evidence can support a reviewed shares_outstanding row only when an explicit "
    "dei:EntityCommonStockSharesOutstanding inline XBRL fact is present; it does not unlock DCF unless "
    "it is validated, previewed, applied, and rebuilt into readiness."
)
SHARE_COUNT_FACT_NAME = "dei:EntityCommonStockSharesOutstanding"
SHARE_COUNT_FILING_FORMS = ("10-K", "10-K/A", "10-Q", "10-Q/A", "20-F", "20-F/A", "40-F", "40-F/A")


@dataclass(frozen=True)
class FiledExhibit:
    document_type: str
    document_name: str
    source_ref: str
    cik: str = ""
    accession: str = ""


def normalize_cik(cik: str | int) -> str:
    text = str(cik).upper().replace("CIK", "").strip()
    digits = "".join(character for character in text if character.isdigit())
    if not digits:
        raise ValueError("SEC CIK is required for SEC submissions metadata.")
    return digits.zfill(10)


def sec_submission_url(cik: str | int) -> str:
    return SEC_SUBMISSIONS_URL_TEMPLATE.format(cik=normalize_cik(cik))


def _accession_no_dashes(accession: str) -> str:
    return str(accession or "").replace("-", "").strip()


def sec_filing_document_url(cik: str | int, accession: str, primary_document: str) -> str:
    normalized_cik = normalize_cik(cik).lstrip("0")
    accession_text = _accession_no_dashes(accession)
    document = str(primary_document or "").strip()
    if not accession_text or not document:
        raise ValueError("SEC filing document URL requires an accession and primary document.")
    return SEC_FILING_DOCUMENT_URL_TEMPLATE.format(
        cik=normalized_cik,
        accession=accession_text,
        primary_document=document,
    )


def sec_filing_index_url(cik: str | int, accession: str) -> str:
    normalized_cik = normalize_cik(cik).lstrip("0")
    accession_text = _accession_no_dashes(accession)
    accession_display = str(accession or "").strip()
    if not accession_text or not accession_display:
        raise ValueError("SEC filing index URL requires an accession.")
    return SEC_FILING_INDEX_URL_TEMPLATE.format(
        cik=normalized_cik,
        accession_path=accession_text,
        accession=accession_display,
    )


class _FilingIndexParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[tuple[str, str]]] = []
        self._row: list[tuple[str, str]] | None = None
        self._cell_text: list[str] | None = None
        self._cell_href = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "tr":
            self._row = []
        elif tag.lower() in {"td", "th"} and self._row is not None:
            self._cell_text = []
            self._cell_href = ""
        elif tag.lower() == "a" and self._cell_text is not None:
            self._cell_href = dict(attrs).get("href") or ""

    def handle_data(self, data: str) -> None:
        if self._cell_text is not None:
            self._cell_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered in {"td", "th"} and self._row is not None and self._cell_text is not None:
            self._row.append((" ".join(self._cell_text).strip(), self._cell_href))
            self._cell_text = None
            self._cell_href = ""
        elif lowered == "tr" and self._row is not None:
            if self._row:
                self.rows.append(self._row)
            self._row = None


def extract_filing_exhibits(index_html: str, *, cik: str, accession: str) -> tuple[FiledExhibit, ...]:
    parser = _FilingIndexParser()
    parser.feed(index_html or "")
    base_url = sec_filing_index_url(cik, accession)
    exhibits: list[FiledExhibit] = []
    seen: set[tuple[str, str]] = set()
    for row in parser.rows:
        document_type = next(
            (text.upper() for text, _href in row if re.fullmatch(r"EX-99(?:\.\d+)?", text.upper())),
            "",
        )
        if not document_type:
            continue
        document_name = next((href or text for text, href in row if href or text.lower().endswith((".htm", ".html"))), "")
        if not document_name:
            continue
        source_ref = urljoin(base_url, document_name)
        key = (document_type, source_ref)
        if key in seen:
            continue
        seen.add(key)
        exhibits.append(
            FiledExhibit(
                document_type=document_type,
                document_name=document_name,
                source_ref=source_ref,
                cik=normalize_cik(cik),
                accession=str(accession).strip(),
            )
        )
    return tuple(exhibits)


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


def _filing_document_cache_path(cache_dir: Path, cik: str, accession: str, primary_document: str) -> Path:
    path = cache_dir / "filing_documents" / f"CIK{normalize_cik(cik)}" / _accession_no_dashes(accession)
    path.mkdir(parents=True, exist_ok=True)
    return path / str(primary_document).strip()


def _filing_index_cache_path(cache_dir: Path, cik: str, accession: str) -> Path:
    path = cache_dir / "filing_indexes" / f"CIK{normalize_cik(cik)}" / _accession_no_dashes(accession)
    path.mkdir(parents=True, exist_ok=True)
    return path / "index.html"


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


def latest_filing_document(payload: dict[str, Any], *, preferred_forms: Iterable[str] | None = None) -> dict[str, Any]:
    recent = payload.get("filings", {}).get("recent", {})
    recent = recent if isinstance(recent, dict) else {}
    forms = _string_list(recent.get("form"))
    filing_dates = _string_list(recent.get("filingDate"))
    report_dates = _string_list(recent.get("reportDate"))
    accessions = _string_list(recent.get("accessionNumber"))
    primary_documents = _string_list(recent.get("primaryDocument"))
    filing_count = max(len(forms), len(filing_dates), len(report_dates), len(accessions), len(primary_documents), 0)
    if filing_count == 0:
        return {"status": "unavailable", "reason_code": "no_recent_filings", "detail": "No recent SEC filings were listed."}

    def value_at(values: list[str], index: int) -> str | None:
        return values[index] if index < len(values) else None

    preferred = {form.upper().strip() for form in preferred_forms or () if str(form).strip()}
    candidate_indexes = [
        index
        for index in range(filing_count)
        if value_at(accessions, index) and value_at(primary_documents, index)
    ]
    if preferred:
        candidate_indexes = [
            index
            for index in candidate_indexes
            if (value_at(forms, index) or "").upper().strip() in preferred
        ]
    if not candidate_indexes:
        return {
            "status": "unavailable",
            "reason_code": "primary_document_missing",
            "detail": (
                "Recent SEC filings did not include a primary document and accession pair"
                + (" for share-count-capable annual or quarterly forms." if preferred else ".")
            ),
        }

    latest_index = max(candidate_indexes, key=lambda index: (value_at(filing_dates, index) or "", -index))
    cik = normalize_cik(payload.get("cik", ""))
    accession = value_at(accessions, latest_index) or ""
    primary_document = value_at(primary_documents, latest_index) or ""
    return {
        "status": "available",
        "source": "sec_submissions_metadata",
        "source_usage": "filing_document_locator",
        "sec_cik": cik,
        "sec_entity_name": str(payload.get("name") or payload.get("entityName") or "").strip() or None,
        "form": value_at(forms, latest_index),
        "filing_date": value_at(filing_dates, latest_index),
        "report_date": value_at(report_dates, latest_index),
        "accession": accession,
        "primary_document": primary_document,
        "document_url": sec_filing_document_url(cik, accession, primary_document),
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


def read_cached_sec_filing_document(
    cik: str | int,
    accession: str,
    primary_document: str,
    *,
    cache_dir: str | Path = "data/cache/sec",
) -> str | None:
    cache_path = _filing_document_cache_path(Path(cache_dir), normalize_cik(cik), accession, primary_document)
    if not cache_path.exists():
        return None
    return cache_path.read_text(encoding="utf-8", errors="replace")


def _fetch_text(url: str, user_agent: str, sleep_seconds: float = 0.2) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            text = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        raise RuntimeError(f"SEC filing document request failed with HTTP {exc.code} for {url}") from exc
    except URLError as exc:
        raise RuntimeError(f"SEC filing document request failed for {url}: {exc.reason}") from exc
    time.sleep(max(0.0, sleep_seconds))
    return text


def fetch_sec_filing_document(
    cik: str | int,
    accession: str,
    primary_document: str,
    user_agent: str | None = None,
    *,
    cache: bool = True,
    refresh: bool = False,
    cache_dir: str | Path = "data/cache/sec",
    sleep_seconds: float = 0.2,
    fetcher: Callable[[str, str, float], str] | None = None,
) -> str:
    resolved_user_agent = _require_user_agent(user_agent)
    normalized_cik = normalize_cik(cik)
    cache_root = Path(cache_dir)
    cache_path = _filing_document_cache_path(cache_root, normalized_cik, accession, primary_document)
    if cache and cache_path.exists() and not refresh:
        return cache_path.read_text(encoding="utf-8", errors="replace")

    text = (fetcher or _fetch_text)(
        sec_filing_document_url(normalized_cik, accession, primary_document),
        resolved_user_agent,
        sleep_seconds,
    )
    if cache:
        cache_path.write_text(text, encoding="utf-8")
    return text


def fetch_sec_filing_index(
    cik: str | int,
    accession: str,
    user_agent: str | None = None,
    *,
    cache: bool = True,
    refresh: bool = False,
    cache_dir: str | Path = "data/cache/sec",
    sleep_seconds: float = 0.2,
    fetcher: Callable[[str, str, float], str] | None = None,
) -> str:
    resolved_user_agent = _require_user_agent(user_agent)
    normalized_cik = normalize_cik(cik)
    cache_path = _filing_index_cache_path(Path(cache_dir), normalized_cik, accession)
    if cache and cache_path.exists() and not refresh:
        return cache_path.read_text(encoding="utf-8", errors="replace")
    text = (fetcher or _fetch_text)(sec_filing_index_url(normalized_cik, accession), resolved_user_agent, sleep_seconds)
    if cache:
        cache_path.write_text(text, encoding="utf-8")
    return text


_IX_NON_FRACTION_RE = re.compile(
    r"<ix:(?:nonfraction|nonFraction)\b(?P<attrs>[^>]*)>(?P<value>.*?)</ix:(?:nonfraction|nonFraction)>",
    flags=re.IGNORECASE | re.DOTALL,
)
_ATTR_RE = re.compile(r"""([A-Za-z_:][\w:.-]*)\s*=\s*["']([^"']*)["']""")
_TAG_RE = re.compile(r"<[^>]+>")


def _parse_attrs(text: str) -> dict[str, str]:
    return {key: value for key, value in _ATTR_RE.findall(text or "")}


def _clean_fact_number(value: str) -> float | None:
    text = _TAG_RE.sub("", value or "")
    text = text.replace(",", "").replace("\u00a0", " ").strip()
    if not text:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _scaled_share_value(value: float, scale: str | None) -> int | float:
    try:
        scale_int = int(str(scale or "0").strip())
    except ValueError:
        scale_int = 0
    scaled = value * (10**scale_int)
    return int(scaled) if float(scaled).is_integer() else scaled


def extract_share_count_from_inline_xbrl(document_text: str) -> dict[str, Any]:
    for match in _IX_NON_FRACTION_RE.finditer(document_text or ""):
        attrs = _parse_attrs(match.group("attrs"))
        if attrs.get("name") != SHARE_COUNT_FACT_NAME:
            continue
        numeric_value = _clean_fact_number(match.group("value"))
        if numeric_value is None:
            continue
        scale = attrs.get("scale")
        return {
            "status": "available",
            "source": "sec_filing_document",
            "source_usage": "share_count_evidence_only",
            "shares_outstanding": _scaled_share_value(numeric_value, scale),
            "sec_fact_name": SHARE_COUNT_FACT_NAME,
            "sec_fact_context": attrs.get("contextRef"),
            "sec_fact_unit": attrs.get("unitRef"),
            "sec_fact_scale": scale,
            "proof_boundary": SEC_FILING_SHARE_COUNT_BOUNDARY,
        }
    return {
        "status": "unavailable",
        "reason_code": "explicit_share_count_fact_missing",
        "detail": f"No explicit {SHARE_COUNT_FACT_NAME} inline XBRL fact was found in the filing document.",
        "source": "sec_filing_document",
        "source_usage": "share_count_evidence_only",
        "proof_boundary": SEC_FILING_SHARE_COUNT_BOUNDARY,
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


def _ticker_lookup_candidates(ticker: str) -> list[str]:
    ticker_text = str(ticker or "").upper().strip()
    if not ticker_text:
        return []
    candidates = [ticker_text]
    if "." in ticker_text:
        candidates.append(ticker_text.replace(".", "-"))
    if "-" in ticker_text:
        candidates.append(ticker_text.replace("-", "."))
    deduped: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in deduped:
            deduped.append(candidate)
    return deduped


def _ticker_map_entry(ticker: str, ticker_map: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(ticker_map, dict):
        return {}
    for candidate in _ticker_lookup_candidates(ticker):
        entry = ticker_map.get(candidate, {})
        if entry:
            return entry
    return {}


def _ticker_matches_submission(ticker: str, metadata: dict[str, Any]) -> str:
    submission_tickers = {
        value.strip().upper()
        for value in str(metadata.get("sec_tickers") or "").split(",")
        if value.strip()
    }
    return (
        "matched_sec_submission_tickers"
        if any(candidate in submission_tickers for candidate in _ticker_lookup_candidates(ticker))
        else "ticker_not_listed_in_sec_submission"
    )


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

    ticker_entry = _ticker_map_entry(ticker_text, ticker_map)
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


def build_sec_filing_share_count_evidence(
    ticker: str,
    *,
    ticker_map: dict[str, dict[str, Any]],
    cache_dir: str | Path = "data/cache/sec",
    user_agent: str | None = None,
    allow_network: bool = False,
    submission_fetcher: Callable[[str, str, float], Any] | None = None,
    document_fetcher: Callable[[str, str, float], str] | None = None,
) -> dict[str, Any]:
    ticker_text = str(ticker or "").upper().strip()
    if not ticker_text:
        return {
            "status": "unavailable",
            "reason_code": "missing_ticker",
            "detail": "Ticker is required for SEC filing-document share-count evidence.",
            "source": "sec_filing_document",
            "source_usage": "share_count_evidence_only",
            "proof_boundary": SEC_FILING_SHARE_COUNT_BOUNDARY,
        }

    ticker_entry = _ticker_map_entry(ticker_text, ticker_map)
    cik_value = ticker_entry.get("cik") or ticker_entry.get("cik_str") or ticker_entry.get("cikStr")
    if cik_value in (None, ""):
        return {
            "status": "unavailable",
            "reason_code": "ticker_not_found_in_sec_ticker_map",
            "detail": f"{ticker_text} was not found in the SEC ticker map.",
            "ticker": ticker_text,
            "source": "sec_filing_document",
            "source_usage": "share_count_evidence_only",
            "proof_boundary": SEC_FILING_SHARE_COUNT_BOUNDARY,
        }

    cik = normalize_cik(cik_value)
    payload = read_cached_sec_submission(cik, cache_dir=cache_dir)
    if payload is None and allow_network:
        try:
            payload = fetch_sec_submission(
                cik,
                user_agent=user_agent,
                cache_dir=cache_dir,
                fetcher=submission_fetcher,
            )
        except Exception as exc:
            return {
                "status": "unavailable",
                "reason_code": "submission_request_failed",
                "detail": f"SEC submissions metadata request failed for {ticker_text}: {exc}",
                "ticker": ticker_text,
                "sec_cik": cik,
                "source": "sec_filing_document",
                "source_usage": "share_count_evidence_only",
                "proof_boundary": SEC_FILING_SHARE_COUNT_BOUNDARY,
            }
    if payload is None:
        return {
            "status": "unavailable",
            "reason_code": "cached_submission_missing",
            "detail": f"No cached SEC submissions metadata found for {ticker_text} CIK {cik}; remote retry disabled.",
            "ticker": ticker_text,
            "sec_cik": cik,
            "source": "sec_filing_document",
            "source_usage": "share_count_evidence_only",
            "proof_boundary": SEC_FILING_SHARE_COUNT_BOUNDARY,
        }

    filing = latest_filing_document(payload, preferred_forms=SHARE_COUNT_FILING_FORMS)
    if filing.get("status") != "available":
        return {
            **filing,
            "ticker": ticker_text,
            "sec_cik": cik,
            "source": "sec_filing_document",
            "source_usage": "share_count_evidence_only",
            "proof_boundary": SEC_FILING_SHARE_COUNT_BOUNDARY,
        }

    accession = str(filing.get("accession") or "")
    primary_document = str(filing.get("primary_document") or "")
    document_text = read_cached_sec_filing_document(cik, accession, primary_document, cache_dir=cache_dir)
    if document_text is None and allow_network:
        try:
            document_text = fetch_sec_filing_document(
                cik,
                accession,
                primary_document,
                user_agent=user_agent,
                cache_dir=cache_dir,
                fetcher=document_fetcher,
            )
        except Exception as exc:
            return {
                "status": "unavailable",
                "reason_code": "filing_document_request_failed",
                "detail": f"SEC filing document request failed for {ticker_text}: {exc}",
                "ticker": ticker_text,
                "sec_cik": cik,
                "source": "sec_filing_document",
                "source_usage": "share_count_evidence_only",
                "proof_boundary": SEC_FILING_SHARE_COUNT_BOUNDARY,
            }
    if document_text is None:
        return {
            "status": "unavailable",
            "reason_code": "cached_filing_document_missing",
            "detail": (
                f"No cached SEC filing document found for {ticker_text} CIK {cik} "
                f"accession {accession}; remote retry disabled."
            ),
            "ticker": ticker_text,
            "sec_cik": cik,
            "sec_form": filing.get("form"),
            "sec_filed_date": filing.get("filing_date"),
            "sec_accession": accession,
            "sec_primary_document": primary_document,
            "source": "sec_filing_document",
            "source_usage": "share_count_evidence_only",
            "proof_boundary": SEC_FILING_SHARE_COUNT_BOUNDARY,
        }

    evidence = extract_share_count_from_inline_xbrl(document_text)
    evidence.update(
        {
            "ticker": ticker_text,
            "sec_cik": cik,
            "sec_entity_name": filing.get("sec_entity_name"),
            "sec_form": filing.get("form"),
            "sec_filed_date": filing.get("filing_date"),
            "as_of_date": filing.get("report_date") or filing.get("filing_date"),
            "sec_accession": accession,
            "sec_primary_document": primary_document,
            "sec_document_url": filing.get("document_url"),
        }
    )
    return evidence
