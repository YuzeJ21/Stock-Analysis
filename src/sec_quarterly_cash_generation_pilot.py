"""Read-only SEC evidence parsing for one exact quarterly cash-generation pilot."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date
from html.parser import HTMLParser
from typing import Any, Mapping

from src.commercial_source_rights import SourceRights
from src.earnings_nowcast_contract import QuarterlyActual, parse_utc_timestamp
from src.quarterly_cash_generation import QuarterlyBusinessObservation
from src.quarterly_cash_generation_adapter import (
    QuarterlyAdapterAcceptance,
    assess_quarterly_cash_generation_adapter,
)


SOURCE_ID = "sec_companyfacts"
REVENUE_CONCEPTS = (
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "SalesRevenueNet",
    "SalesRevenueGoodsNet",
)
OPERATING_INCOME_CONCEPTS = ("OperatingIncomeLoss",)
CASH_FROM_OPERATIONS_CONCEPTS = (
    "NetCashProvidedByUsedInOperatingActivities",
    "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
)
CAPEX_CONCEPTS = (
    "PaymentsToAcquireProductiveAssets",
    "PaymentsToAcquirePropertyPlantAndEquipment",
)


@dataclass(frozen=True)
class SecQuarterlyPilotExtraction:
    ticker: str
    cik: str
    fiscal_period: str
    period_start_date: str
    period_end_date: str
    accession: str
    filing_date: str
    accepted_at: str
    source_url: str
    observations: tuple[QuarterlyBusinessObservation, ...]
    revenue_actuals: tuple[QuarterlyActual, ...]
    capex_sign_evidence: str
    blockers: tuple[str, ...]


@dataclass(frozen=True)
class SecQuarterlyPilotPreview:
    extraction: SecQuarterlyPilotExtraction
    acceptance: QuarterlyAdapterAcceptance | None
    status: str
    blockers: tuple[str, ...]
    production_activation: bool = False
    readiness_promotions: tuple[str, ...] = ()


@dataclass(frozen=True)
class _SelectedFact:
    concept: str
    value: float
    filed: str


@dataclass
class _InlineFact:
    concept: str
    context_ref: str
    scale: int
    fact_id: str
    event_index: int
    end_event_index: int = 0
    text_parts: list[str] = field(default_factory=list)


@dataclass
class _InlineRow:
    events: list[object] = field(default_factory=list)
    facts: list[_InlineFact] = field(default_factory=list)


class _InlineFilingParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.contexts: dict[str, tuple[str, str]] = {}
        self.rows: list[_InlineRow] = []
        self._context_id: str | None = None
        self._context_start = ""
        self._context_end = ""
        self._context_field: str | None = None
        self._row: _InlineRow | None = None
        self._fact: _InlineFact | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized = tag.lower()
        attributes = {key.lower(): str(value or "") for key, value in attrs}
        if normalized == "xbrli:context":
            self._context_id = attributes.get("id") or None
            self._context_start = ""
            self._context_end = ""
        elif normalized == "xbrli:startdate" and self._context_id:
            self._context_field = "start"
        elif normalized == "xbrli:enddate" and self._context_id:
            self._context_field = "end"
        elif normalized == "tr":
            self._row = _InlineRow()
        elif normalized == "ix:nonfraction" and self._row is not None:
            concept = attributes.get("name", "").split(":")[-1]
            try:
                scale = int(attributes.get("scale", "0"))
            except ValueError:
                scale = 0
            self._fact = _InlineFact(
                concept=concept,
                context_ref=attributes.get("contextref", ""),
                scale=scale,
                fact_id=attributes.get("id", ""),
                event_index=len(self._row.events),
            )
            self._row.events.append(self._fact)
            self._row.facts.append(self._fact)

    def handle_data(self, data: str) -> None:
        if self._context_field == "start":
            self._context_start += data
        elif self._context_field == "end":
            self._context_end += data
        if self._row is not None:
            self._row.events.append(data)
        if self._fact is not None:
            self._fact.text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.lower()
        if normalized in {"xbrli:startdate", "xbrli:enddate"}:
            self._context_field = None
        elif normalized == "xbrli:context":
            if self._context_id:
                self.contexts[self._context_id] = (
                    self._context_start.strip(),
                    self._context_end.strip(),
                )
            self._context_id = None
        elif normalized == "ix:nonfraction" and self._row is not None and self._fact is not None:
            self._fact.end_event_index = len(self._row.events)
            self._fact = None
        elif normalized == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None


def _quarter_number(fiscal_period: str) -> int:
    return int(fiscal_period[-1])


def _select_companyfact(
    payload: Mapping[str, Any],
    concepts: tuple[str, ...],
    *,
    accession: str,
    start: str,
    end: str,
    fiscal_period: str,
) -> tuple[_SelectedFact | None, str | None]:
    fiscal_year = int(fiscal_period[:4])
    fiscal_quarter = f"Q{_quarter_number(fiscal_period)}"
    facts = payload.get("facts", {}).get("us-gaap", {})
    for concept in concepts:
        rows = facts.get(concept, {}).get("units", {}).get("USD", ())
        matching = [
            row
            for row in rows
            if row.get("accn") == accession
            and row.get("start") == start
            and row.get("end") == end
            and row.get("form") in {"10-Q", "10-Q/A"}
            and row.get("fy") == fiscal_year
            and row.get("fp") == fiscal_quarter
        ]
        values = {float(row["val"]) for row in matching if row.get("val") is not None}
        if len(values) > 1:
            return None, "ambiguous"
        if len(values) == 1:
            chosen = matching[0]
            return (
                _SelectedFact(
                    concept=concept,
                    value=next(iter(values)),
                    filed=str(chosen.get("filed") or ""),
                ),
                None,
            )
    return None, "missing"


def _submission_for_accession(
    payload: Mapping[str, Any], accession: str
) -> dict[str, str] | None:
    recent = payload.get("filings", {}).get("recent", {})
    accessions = recent.get("accessionNumber", ())
    try:
        index = list(accessions).index(accession)
    except ValueError:
        return None
    fields = ("filingDate", "acceptanceDateTime", "form", "primaryDocument")
    try:
        return {field: str(recent[field][index]) for field in fields}
    except (KeyError, IndexError, TypeError):
        return None


def _displayed_value(fact: _InlineFact) -> float | None:
    cleaned = "".join(fact.text_parts).strip().replace(",", "").replace("$", "")
    try:
        return float(cleaned) * (10**fact.scale)
    except ValueError:
        return None


def _nearest_text(events: list[object], start: int, step: int) -> str:
    index = start
    while 0 <= index < len(events):
        value = events[index]
        if isinstance(value, str) and value.strip():
            return value.strip()
        index += step
    return ""


def _match_inline_fact(
    parser: _InlineFilingParser,
    selected: _SelectedFact,
    *,
    start: str,
    end: str,
    require_outflow: bool = False,
) -> _InlineFact | None:
    matches: list[_InlineFact] = []
    for row in parser.rows:
        for fact in row.facts:
            context = parser.contexts.get(fact.context_ref)
            displayed = _displayed_value(fact)
            if (
                fact.concept != selected.concept
                or context != (start, end)
                or displayed is None
                or not math.isclose(abs(displayed), abs(selected.value), abs_tol=0.5)
            ):
                continue
            if require_outflow:
                before = _nearest_text(row.events, fact.event_index - 1, -1)
                after = _nearest_text(row.events, fact.end_event_index, 1)
                if before != "(" or after != ")":
                    continue
            matches.append(fact)
    unique = {fact.fact_id: fact for fact in matches if fact.fact_id}
    return next(iter(unique.values())) if len(unique) == 1 else None


def _blocked_extraction(
    *,
    ticker: str,
    cik: str,
    fiscal_period: str,
    period_start_date: str,
    period_end_date: str,
    accession: str,
    blockers: list[str],
) -> SecQuarterlyPilotExtraction:
    return SecQuarterlyPilotExtraction(
        ticker=ticker,
        cik=cik,
        fiscal_period=fiscal_period,
        period_start_date=period_start_date,
        period_end_date=period_end_date,
        accession=accession,
        filing_date="",
        accepted_at="",
        source_url="",
        observations=(),
        revenue_actuals=(),
        capex_sign_evidence="blocked",
        blockers=tuple(dict.fromkeys(blockers)),
    )


def extract_sec_quarterly_cash_generation(
    *,
    ticker: str,
    cik: str,
    fiscal_period: str,
    period_start_date: str,
    period_end_date: str,
    accession: str,
    companyfacts_payload: Mapping[str, Any],
    submissions_payload: Mapping[str, Any],
    filing_html: str,
    retrieved_at: str,
    as_of: str,
) -> SecQuarterlyPilotExtraction:
    """Build one exact-quarter in-memory evidence batch or deterministic blockers."""

    symbol = str(ticker or "").strip().upper()
    normalized_cik = str(cik or "").strip().zfill(10)
    normalized_period = str(fiscal_period or "").strip().upper()
    blockers: list[str] = []
    try:
        period_start = date.fromisoformat(period_start_date)
        period_end = date.fromisoformat(period_end_date)
        retrieved = parse_utc_timestamp(retrieved_at, label="retrieved_at")
        cutoff = parse_utc_timestamp(as_of, label="as_of")
    except ValueError:
        blockers.append("request:identity_or_time_invalid")
        return _blocked_extraction(
            ticker=symbol,
            cik=normalized_cik,
            fiscal_period=normalized_period,
            period_start_date=period_start_date,
            period_end_date=period_end_date,
            accession=accession,
            blockers=blockers,
        )

    if normalized_period.endswith("-Q4") and not 70 <= (period_end - period_start).days <= 100:
        blockers.append("q4_explicit_three_month_filing_required")
    try:
        companyfacts_cik = str(int(companyfacts_payload.get("cik", ""))).zfill(10)
    except (TypeError, ValueError):
        companyfacts_cik = ""
    if companyfacts_cik != normalized_cik:
        blockers.append("companyfacts:cik_mismatch")
    if blockers:
        return _blocked_extraction(
            ticker=symbol,
            cik=normalized_cik,
            fiscal_period=normalized_period,
            period_start_date=period_start_date,
            period_end_date=period_end_date,
            accession=accession,
            blockers=blockers,
        )

    submission = _submission_for_accession(submissions_payload, accession)
    if submission is None:
        blockers.append("submissions:accession_missing")
        return _blocked_extraction(
            ticker=symbol,
            cik=normalized_cik,
            fiscal_period=normalized_period,
            period_start_date=period_start_date,
            period_end_date=period_end_date,
            accession=accession,
            blockers=blockers,
        )
    try:
        accepted = parse_utc_timestamp(
            submission["acceptanceDateTime"], label="acceptanceDateTime"
        )
    except ValueError:
        blockers.append("submissions:acceptance_time_invalid")
        return _blocked_extraction(
            ticker=symbol,
            cik=normalized_cik,
            fiscal_period=normalized_period,
            period_start_date=period_start_date,
            period_end_date=period_end_date,
            accession=accession,
            blockers=blockers,
        )
    if accepted > cutoff:
        blockers.append("acceptance_after_cutoff")
    if submission["form"] not in {"10-Q", "10-Q/A"}:
        blockers.append("submissions:form_not_quarterly")

    raw_selections = {
        "revenue": _select_companyfact(
            companyfacts_payload,
            REVENUE_CONCEPTS,
            accession=accession,
            start=period_start_date,
            end=period_end_date,
            fiscal_period=normalized_period,
        ),
        "operating_income": _select_companyfact(
            companyfacts_payload,
            OPERATING_INCOME_CONCEPTS,
            accession=accession,
            start=period_start_date,
            end=period_end_date,
            fiscal_period=normalized_period,
        ),
        "cash_from_operations": _select_companyfact(
            companyfacts_payload,
            CASH_FROM_OPERATIONS_CONCEPTS,
            accession=accession,
            start=period_start_date,
            end=period_end_date,
            fiscal_period=normalized_period,
        ),
        "capital_expenditures": _select_companyfact(
            companyfacts_payload,
            CAPEX_CONCEPTS,
            accession=accession,
            start=period_start_date,
            end=period_end_date,
            fiscal_period=normalized_period,
        ),
    }
    selections = {metric: selection[0] for metric, selection in raw_selections.items()}
    for metric, (selected, state) in raw_selections.items():
        if selected is None:
            blockers.append(f"{metric}:fact_{state}")

    parser = _InlineFilingParser()
    parser.feed(filing_html)
    inline: dict[str, _InlineFact] = {}
    for metric, selected in selections.items():
        if selected is None:
            continue
        matched = _match_inline_fact(
            parser,
            selected,
            start=period_start_date,
            end=period_end_date,
        )
        if matched is None:
            blockers.append(f"{metric}:inline_fact_missing")
        elif metric == "capital_expenditures" and _match_inline_fact(
            parser,
            selected,
            start=period_start_date,
            end=period_end_date,
            require_outflow=True,
        ) is None:
            blockers.append("capital_expenditures:explicit_outflow_evidence_missing")
        else:
            inline[metric] = matched

    if blockers:
        return _blocked_extraction(
            ticker=symbol,
            cik=normalized_cik,
            fiscal_period=normalized_period,
            period_start_date=period_start_date,
            period_end_date=period_end_date,
            accession=accession,
            blockers=blockers,
        )

    accession_path = accession.replace("-", "")
    source_url = (
        "https://www.sec.gov/Archives/edgar/data/"
        f"{int(normalized_cik)}/{accession_path}/{submission['primaryDocument']}"
    )
    accepted_at = accepted.isoformat()
    retrieved_at_utc = retrieved.isoformat()
    observations = tuple(
        QuarterlyBusinessObservation(
            ticker=symbol,
            fiscal_period=normalized_period,
            period_end_date=period_end_date,
            metric=metric,
            value=(-abs(selected.value) if metric == "capital_expenditures" else selected.value),
            currency="USD",
            unit_scale=1.0,
            accounting_basis="reported",
            duration_basis="three_months",
            source=SOURCE_ID,
            source_ref=f"{source_url}#{inline[metric].fact_id}",
            published_at=accepted_at,
            retrieved_at=retrieved_at_utc,
            q4_evidence_state="not_q4",
        )
        for metric in (
            "operating_income",
            "cash_from_operations",
            "capital_expenditures",
        )
        if (selected := selections[metric]) is not None
    )
    revenue = selections["revenue"]
    assert revenue is not None
    revenue_actuals = (
        QuarterlyActual(
            ticker=symbol,
            fiscal_period=normalized_period,
            period_end_date=period_end_date,
            reported_at=accepted_at,
            revenue_actual=revenue.value,
            eps_actual=None,
            source=SOURCE_ID,
            source_ref=f"{source_url}#{inline['revenue'].fact_id}",
            retrieved_at=retrieved_at_utc,
            revenue_currency="USD",
            revenue_unit_scale=1.0,
            revenue_basis="reported",
            split_adjustment_basis="primary_split_basis_unverified",
        ),
    )
    return SecQuarterlyPilotExtraction(
        ticker=symbol,
        cik=normalized_cik,
        fiscal_period=normalized_period,
        period_start_date=period_start_date,
        period_end_date=period_end_date,
        accession=accession,
        filing_date=submission["filingDate"],
        accepted_at=accepted_at,
        source_url=source_url,
        observations=observations,
        revenue_actuals=revenue_actuals,
        capex_sign_evidence="explicit_filed_table_outflow",
        blockers=(),
    )


def preview_sec_quarterly_cash_generation(
    *,
    extraction: SecQuarterlyPilotExtraction,
    rights_registry: Mapping[str, SourceRights],
    as_of: str | None = None,
) -> SecQuarterlyPilotPreview:
    if extraction.blockers:
        return SecQuarterlyPilotPreview(
            extraction=extraction,
            acceptance=None,
            status="blocked",
            blockers=extraction.blockers,
        )
    acceptance = assess_quarterly_cash_generation_adapter(
        extraction.ticker,
        SOURCE_ID,
        extraction.observations,
        extraction.revenue_actuals,
        rights_registry=rights_registry,
        as_of=as_of,
    )
    return SecQuarterlyPilotPreview(
        extraction=extraction,
        acceptance=acceptance,
        status=acceptance.status,
        blockers=acceptance.blockers,
    )
