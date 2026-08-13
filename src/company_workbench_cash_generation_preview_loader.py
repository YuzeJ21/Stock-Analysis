"""Bounded live loader for explicit reviewed Workbench preview filings."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Mapping

from src.commercial_source_rights import load_source_rights_registry
from src.company_workbench_cash_generation_preview import (
    CompanyWorkbenchCashGenerationPreview,
    blocked_company_workbench_cash_generation_preview,
    compose_company_workbench_cash_generation_preview,
)
from src.providers.sec_companyfacts import SECUserAgentError
from src.sec_quarterly_cash_generation_pilot import (
    extract_sec_quarterly_cash_generation,
    preview_sec_quarterly_cash_generation,
)
from src.sec_quarterly_cash_generation_preview import (
    SecQuarterlyPreviewFetchError,
    fetch_sec_quarterly_pilot_payloads,
)


@dataclass(frozen=True)
class CashGenerationPreviewFiling:
    ticker: str
    cik: str
    fiscal_period: str
    period_start: str
    period_end: str
    accession: str
    primary_document: str
    as_of: str


CASH_GENERATION_PREVIEW_FILINGS: Mapping[str, CashGenerationPreviewFiling] = (
    MappingProxyType({
        "NVDA": CashGenerationPreviewFiling(
            ticker="NVDA",
            cik="0001045810",
            fiscal_period="2027-Q1",
            period_start="2026-01-26",
            period_end="2026-04-26",
            accession="0001045810-26-000052",
            primary_document="nvda-20260426.htm",
            as_of="2026-07-20T23:59:59-04:00",
        ),
        "AMD": CashGenerationPreviewFiling(
            ticker="AMD",
            cik="0000002488",
            fiscal_period="2026-Q1",
            period_start="2025-12-28",
            period_end="2026-03-28",
            accession="0000002488-26-000076",
            primary_document="amd-20260328.htm",
            as_of="2026-07-20T23:59:59-04:00",
        ),
    })
)


def load_company_workbench_cash_generation_preview(
    ticker: str,
    *,
    user_agent: str | None = None,
    fetcher=None,
    retrieved_at: str | None = None,
) -> CompanyWorkbenchCashGenerationPreview:
    """Load one exact filing in memory or return a fully withheld preview."""

    symbol = str(ticker or "").strip().upper()
    filing = CASH_GENERATION_PREVIEW_FILINGS.get(symbol)
    if filing is None:
        return blocked_company_workbench_cash_generation_preview(
            symbol,
            blockers=(f"unsupported_preview_ticker:{symbol or 'missing'}",),
        )
    try:
        payloads = fetch_sec_quarterly_pilot_payloads(
            cik=filing.cik,
            accession=filing.accession,
            primary_document=filing.primary_document,
            user_agent=user_agent,
            fetcher=fetcher,
        )
        extraction = extract_sec_quarterly_cash_generation(
            ticker=filing.ticker,
            cik=filing.cik,
            fiscal_period=filing.fiscal_period,
            period_start_date=filing.period_start,
            period_end_date=filing.period_end,
            accession=filing.accession,
            primary_document=filing.primary_document,
            companyfacts_payload=payloads["companyfacts"],
            submissions_payload=payloads["submissions"],
            filing_html=payloads["filing_html"],
            retrieved_at=(
                retrieved_at
                or datetime.now(timezone.utc).isoformat()
            ),
            as_of=filing.as_of,
        )
        pilot = preview_sec_quarterly_cash_generation(
            extraction=extraction,
            rights_registry=load_source_rights_registry(),
            as_of=filing.as_of,
        )
        return compose_company_workbench_cash_generation_preview(
            pilot,
            selected_ticker=symbol,
            as_of=filing.as_of,
        )
    except (
        SECUserAgentError,
        SecQuarterlyPreviewFetchError,
        TypeError,
        ValueError,
    ) as exc:
        return blocked_company_workbench_cash_generation_preview(
            symbol,
            fiscal_period=filing.fiscal_period,
            as_of=filing.as_of,
            blockers=(f"preview_load_blocked:{type(exc).__name__}",),
            accession=filing.accession,
        )
