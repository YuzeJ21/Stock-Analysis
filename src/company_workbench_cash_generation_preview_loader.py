"""Bounded live loader for the explicit NVIDIA Workbench preview route."""

from __future__ import annotations

from datetime import datetime, timezone

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


PREVIEW_TICKER = "NVDA"
PREVIEW_CIK = "0001045810"
PREVIEW_FISCAL_PERIOD = "2027-Q1"
PREVIEW_PERIOD_START = "2026-01-26"
PREVIEW_PERIOD_END = "2026-04-26"
PREVIEW_ACCESSION = "0001045810-26-000052"
PREVIEW_PRIMARY_DOCUMENT = "nvda-20260426.htm"
PREVIEW_AS_OF = "2026-07-20T23:59:59-04:00"


def load_company_workbench_cash_generation_preview(
    ticker: str,
    *,
    user_agent: str | None = None,
    fetcher=None,
    retrieved_at: str | None = None,
) -> CompanyWorkbenchCashGenerationPreview:
    """Load one exact filing in memory or return a fully withheld preview."""

    symbol = str(ticker or "").strip().upper()
    if symbol != PREVIEW_TICKER:
        return blocked_company_workbench_cash_generation_preview(
            symbol,
            fiscal_period=PREVIEW_FISCAL_PERIOD,
            as_of=PREVIEW_AS_OF,
            blockers=(f"unsupported_preview_ticker:{symbol or 'missing'}",),
            accession=PREVIEW_ACCESSION,
        )
    try:
        payloads = fetch_sec_quarterly_pilot_payloads(
            cik=PREVIEW_CIK,
            accession=PREVIEW_ACCESSION,
            primary_document=PREVIEW_PRIMARY_DOCUMENT,
            user_agent=user_agent,
            fetcher=fetcher,
        )
        extraction = extract_sec_quarterly_cash_generation(
            ticker=PREVIEW_TICKER,
            cik=PREVIEW_CIK,
            fiscal_period=PREVIEW_FISCAL_PERIOD,
            period_start_date=PREVIEW_PERIOD_START,
            period_end_date=PREVIEW_PERIOD_END,
            accession=PREVIEW_ACCESSION,
            primary_document=PREVIEW_PRIMARY_DOCUMENT,
            companyfacts_payload=payloads["companyfacts"],
            submissions_payload=payloads["submissions"],
            filing_html=payloads["filing_html"],
            retrieved_at=(
                retrieved_at
                or datetime.now(timezone.utc).isoformat()
            ),
            as_of=PREVIEW_AS_OF,
        )
        pilot = preview_sec_quarterly_cash_generation(
            extraction=extraction,
            rights_registry=load_source_rights_registry(),
            as_of=PREVIEW_AS_OF,
        )
        return compose_company_workbench_cash_generation_preview(
            pilot,
            selected_ticker=symbol,
            as_of=PREVIEW_AS_OF,
        )
    except (
        SECUserAgentError,
        SecQuarterlyPreviewFetchError,
        TypeError,
        ValueError,
    ) as exc:
        return blocked_company_workbench_cash_generation_preview(
            symbol,
            fiscal_period=PREVIEW_FISCAL_PERIOD,
            as_of=PREVIEW_AS_OF,
            blockers=(f"preview_load_blocked:{type(exc).__name__}",),
            accession=PREVIEW_ACCESSION,
        )
