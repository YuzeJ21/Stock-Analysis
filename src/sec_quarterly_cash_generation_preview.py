"""Read-only live preview for one exact SEC quarterly cash-generation filing."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.commercial_source_rights import load_source_rights_registry
from src.providers.sec_companyfacts import SECUserAgentError, _require_user_agent
from src.sec_quarterly_cash_generation_pilot import (
    SecQuarterlyPilotPreview,
    extract_sec_quarterly_cash_generation,
    preview_sec_quarterly_cash_generation,
)


COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
FILING_URL = (
    "https://www.sec.gov/Archives/edgar/data/{cik_number}/{accession_path}/"
    "{primary_document}"
)


class SecQuarterlyPreviewFetchError(RuntimeError):
    pass


def _fetch_bytes(url: str, user_agent: str) -> bytes:
    request = Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "application/json,text/html",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            return response.read()
    except HTTPError as exc:
        raise SecQuarterlyPreviewFetchError(
            f"SEC preview request failed with HTTP {exc.code}"
        ) from exc
    except URLError as exc:
        raise SecQuarterlyPreviewFetchError("SEC preview request failed") from exc


def fetch_sec_quarterly_pilot_payloads(
    *,
    cik: str,
    accession: str,
    primary_document: str,
    user_agent: str | None = None,
    fetcher: Callable[[str, str], bytes] | None = None,
) -> dict[str, Any]:
    """Fetch three exact SEC payloads in memory without a cache or file output."""

    resolved_user_agent = _require_user_agent(user_agent)
    normalized_cik = str(cik or "").strip().zfill(10)
    accession_path = str(accession or "").strip().replace("-", "")
    document = str(primary_document or "").strip()
    if not normalized_cik.isdigit() or not accession_path.isdigit() or not document:
        raise ValueError("exact CIK, accession, and primary document are required")
    urls = (
        COMPANYFACTS_URL.format(cik=normalized_cik),
        SUBMISSIONS_URL.format(cik=normalized_cik),
        FILING_URL.format(
            cik_number=int(normalized_cik),
            accession_path=accession_path,
            primary_document=document,
        ),
    )
    retrieve = fetcher or _fetch_bytes
    raw_companyfacts = retrieve(urls[0], resolved_user_agent)
    raw_submissions = retrieve(urls[1], resolved_user_agent)
    raw_filing = retrieve(urls[2], resolved_user_agent)
    try:
        return {
            "companyfacts": json.loads(raw_companyfacts.decode("utf-8")),
            "submissions": json.loads(raw_submissions.decode("utf-8")),
            "filing_html": raw_filing.decode("utf-8"),
        }
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SecQuarterlyPreviewFetchError("SEC preview payload was malformed") from exc


def render_sec_quarterly_pilot_preview(preview: SecQuarterlyPilotPreview) -> str:
    extraction = preview.extraction
    company = "NVIDIA" if extraction.ticker == "NVDA" else extraction.ticker
    fiscal_year, quarter = extraction.fiscal_period.split("-Q")
    lines = [
        "SEC quarterly cash-generation preview",
        f"status: {preview.status}",
        f"company: {company} Q{quarter} FY{fiscal_year}",
        f"accession: {extraction.accession}",
        f"accepted at: {extraction.accepted_at or 'unavailable'}",
        f"source: {extraction.source_url or 'unavailable'}",
    ]
    values = {row.metric: row for row in extraction.observations}
    revenue = extraction.revenue_actuals[0] if extraction.revenue_actuals else None
    if revenue is not None:
        lines.append(f"revenue: {revenue.revenue_actual} {revenue.revenue_currency}")
    for metric, label in (
        ("operating_income", "operating income"),
        ("cash_from_operations", "cash from operations"),
        ("capital_expenditures", "capital expenditures"),
    ):
        row = values.get(metric)
        if row is not None:
            lines.append(f"{label}: {row.value} {row.currency}")
    lines.extend(
        [
            f"capex sign evidence: {extraction.capex_sign_evidence}",
            "blockers: " + (", ".join(preview.blockers) if preview.blockers else "none"),
            "production activation: false",
            "readiness promotions: none",
            "generated artifacts: none",
        ]
    )
    return "\n".join(lines)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Preview one exact SEC quarterly cash-generation filing without writes."
    )
    parser.add_argument("--ticker", default="NVDA")
    parser.add_argument("--cik", default="0001045810")
    parser.add_argument("--fiscal-period", default="2027-Q1")
    parser.add_argument("--period-start", default="2026-01-26")
    parser.add_argument("--period-end", default="2026-04-26")
    parser.add_argument("--accession", default="0001045810-26-000052")
    parser.add_argument("--primary-document", default="nvda-20260426.htm")
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--sec-user-agent")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        payloads = fetch_sec_quarterly_pilot_payloads(
            cik=args.cik,
            accession=args.accession,
            primary_document=args.primary_document,
            user_agent=args.sec_user_agent,
        )
        retrieved_at = datetime.now(timezone.utc).isoformat()
        extraction = extract_sec_quarterly_cash_generation(
            ticker=args.ticker,
            cik=args.cik,
            fiscal_period=args.fiscal_period,
            period_start_date=args.period_start,
            period_end_date=args.period_end,
            accession=args.accession,
            primary_document=args.primary_document,
            companyfacts_payload=payloads["companyfacts"],
            submissions_payload=payloads["submissions"],
            filing_html=payloads["filing_html"],
            retrieved_at=retrieved_at,
            as_of=args.as_of,
        )
        preview = preview_sec_quarterly_cash_generation(
            extraction=extraction,
            rights_registry=load_source_rights_registry(),
            as_of=args.as_of,
        )
        print(render_sec_quarterly_pilot_preview(preview))
        return 0 if preview.status == "accepted_for_review" else 2
    except (SECUserAgentError, SecQuarterlyPreviewFetchError, ValueError) as exc:
        print("SEC quarterly cash-generation preview")
        print("status: blocked")
        print(f"blockers: {exc}")
        print("production activation: false")
        print("readiness promotions: none")
        print("generated artifacts: none")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
