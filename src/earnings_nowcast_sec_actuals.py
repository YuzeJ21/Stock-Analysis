from __future__ import annotations

import argparse
import csv
import json
import os
import re
import signal
import tempfile
from dataclasses import asdict, dataclass, replace
from datetime import date, datetime, time, timezone
from html.parser import HTMLParser
from math import isfinite
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from src.earnings_nowcast_contract import (
    PRIMARY_SPLIT_BASIS_UNVERIFIED,
    COMPANYFACTS_SPLIT_BASIS_UNVERIFIED,
    QuarterlyActual,
)
from src.earnings_nowcast_onboarding import EVIDENCE_SCHEMA_VERSION, SCHEMAS
from src.providers.sec_companyfacts import (
    fetch_companyfacts,
    load_sec_ticker_map,
    resolve_ticker_to_cik,
)
from src.providers.sec_submissions import (
    FiledExhibit,
    extract_filing_exhibits,
    fetch_sec_filing_document,
    fetch_sec_filing_index,
    fetch_sec_submission,
)


REVENUE_CONCEPTS = (
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "SalesRevenueNet",
)
EPS_CONCEPT = "EarningsPerShareDiluted"
SEC_QUARTERLY_FORMS = frozenset(("10-Q", "10-Q/A"))
_FISCAL_PERIOD_PATTERN = re.compile(r"^(?P<year>\d{4})-Q(?P<quarter>[1-4])$")
REJECTED_AUDIT_STATES = frozenset(
    (
        "ambiguous_concept",
        "ambiguous_fiscal_identity",
        "comparative_period_relabelled",
        "companyfacts_fetch_failed",
        "cumulative_fact_rejected",
        "fiscal_period_conflict",
        "post_cutoff_rejected",
        "period_end_ambiguous",
        "period_end_missing",
        "q4_source_unavailable",
        "quarter_header_missing",
        "ambiguous_period_header",
        "guidance_or_outlook_rejected",
        "gaap_eps_missing",
        "derived_q4_rejected",
        "revenue_scale_missing",
        "split_basis_unverified",
        "ticker_unresolved",
    )
)
_STAGE_OUTPUT_NAMES = frozenset(
    (
        ".sec-cache",
        "consensus_snapshots.csv",
        "quarterly_actuals.csv",
        "sec_actuals_audit.json",
        "sec_actuals_rejected.csv",
        "signals.csv",
    )
)


@dataclass(frozen=True)
class SecDurationFact:
    taxonomy: str
    concept: str
    unit: str
    value: float
    start: str
    end: str
    filed: str
    form: str
    accession: str
    fiscal_year: int
    fiscal_period: str
    frame: str

    @property
    def duration_days(self) -> int:
        return (date.fromisoformat(self.end) - date.fromisoformat(self.start)).days


@dataclass(frozen=True)
class ExtractionAuditRow:
    ticker: str
    state: str
    metric: str
    fiscal_period: str
    source_ref: str
    detail: str
    concept: str = ""
    start: str = ""
    end: str = ""
    frame: str = ""
    accession: str = ""


@dataclass(frozen=True)
class ExtractionResult:
    rows: tuple[QuarterlyActual, ...]
    audit_rows: tuple[ExtractionAuditRow, ...]


@dataclass(frozen=True)
class StageResult:
    requested_tickers: tuple[str, ...]
    accepted_tickers: tuple[str, ...]
    withheld_tickers: tuple[str, ...]
    accepted_row_count: int
    rejected_row_count: int
    quarterly_actuals_path: str
    audit_path: str
    rejected_path: str
    automatic_apply: bool = False


class _StructuredTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[tuple[tuple[tuple[str, ...], ...], str]] = []
        self._page_text: list[str] = []
        self._table_rows: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None
        self._caption: list[str] | None = None
        self._table_depth = 0

    @property
    def page_text(self) -> str:
        return " ".join(self._page_text)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.lower()
        if lowered == "table":
            self._table_depth += 1
            if self._table_depth == 1:
                self._table_rows = []
        elif self._table_depth and lowered == "caption":
            self._caption = []
        elif self._table_depth and lowered == "tr":
            self._row = []
        elif self._table_depth and lowered in {"td", "th"} and self._row is not None:
            self._cell = []

    def handle_data(self, data: str) -> None:
        self._page_text.append(data)
        if self._caption is not None:
            self._caption.append(data)
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered == "caption" and self._caption is not None and self._table_rows is not None:
            caption = " ".join(self._caption).strip()
            if caption:
                self._table_rows.append([caption])
            self._caption = None
        elif lowered in {"td", "th"} and self._cell is not None and self._row is not None:
            self._row.append(" ".join(self._cell).strip())
            self._cell = None
        elif lowered == "tr" and self._row is not None and self._table_rows is not None:
            if self._row:
                self._table_rows.append(self._row)
            self._row = None
        elif lowered == "table" and self._table_depth:
            self._table_depth -= 1
            if self._table_depth == 0 and self._table_rows is not None:
                rows = tuple(tuple(cell for cell in row) for row in self._table_rows)
                self.tables.append((rows, " ".join(cell for row in rows for cell in row)))
                self._table_rows = None


def _normalized_table_text(value: str) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").lower().split())


def _q4_audit(
    ticker: str,
    state: str,
    metric: str,
    fiscal_period: str,
    exhibit: FiledExhibit,
    detail: str,
) -> ExtractionAuditRow:
    return ExtractionAuditRow(
        ticker=str(ticker or "").strip().upper(),
        state=state,
        metric=metric,
        fiscal_period=fiscal_period,
        source_ref=exhibit.source_ref,
        detail=detail,
        concept=exhibit.document_type,
        accession=exhibit.accession,
    )


def _explicit_q4_fiscal_period(document_text: str) -> str | None:
    text = _normalized_table_text(document_text)
    years = {
        match.group(1)
        for pattern in (
            r"(?:fourth quarter|q4)\s+(?:of\s+)?fiscal\s+(20\d{2})",
            r"fiscal\s+(20\d{2}).{0,80}?(?:fourth quarter|q4)",
            r"q4\s+fy\s*(20\d{2})",
        )
        for match in re.finditer(pattern, text)
    }
    if len(years) != 1:
        return None
    return f"{next(iter(years))}-Q4"


def _q4_value_column(rows: tuple[tuple[str, ...], ...], fiscal_period: str) -> int | None:
    fiscal_year = fiscal_period.split("-", 1)[0]
    fiscal_year_short = fiscal_year[-2:]
    columns = {
        index
        for row in rows[:2]
        for index, cell in enumerate(row)
        if re.search(rf"\bq4\s+(?:fy\s*)?(?:{fiscal_year}|{fiscal_year_short})\b", _normalized_table_text(cell))
        or re.search(rf"\bfiscal\s+{fiscal_year}\s+q4\b", _normalized_table_text(cell))
    }
    return next(iter(columns)) if len(columns) == 1 else None


def _has_ambiguous_q4_header(rows: tuple[tuple[str, ...], ...]) -> bool:
    headers = _normalized_table_text(" ".join(cell for row in rows[:2] for cell in row))
    return "q4" in headers


def _dates_in_text(value: str) -> set[str]:
    dates: set[str] = set()
    for raw_date in re.findall(
        r"\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},\s+20\d{2}\b",
        str(value or ""),
        flags=re.IGNORECASE,
    ):
        try:
            dates.add(datetime.strptime(raw_date.title(), "%B %d, %Y").date().isoformat())
        except ValueError:
            continue
    for raw_date in re.findall(r"\b20\d{2}-\d{2}-\d{2}\b", str(value or "")):
        try:
            dates.add(date.fromisoformat(raw_date).isoformat())
        except ValueError:
            continue
    return dates


def _q4_period_end_dates(
    matching_tables: Sequence[tuple[tuple[tuple[str, ...], ...], int]],
) -> set[str]:
    period_ends: set[str] = set()
    for rows, value_column in matching_tables:
        for row in rows:
            if len(row) <= value_column:
                continue
            label = _normalized_table_text(row[0])
            value = row[value_column]
            value_text = _normalized_table_text(value)
            if not any(
                marker in label or marker in value_text
                for marker in ("period ended", "quarter ended", "three months ended")
            ):
                continue
            period_ends.update(_dates_in_text(value))
    return period_ends


def _table_number(value: str, *, scale_required: bool) -> tuple[float, float] | None:
    text = _normalized_table_text(value)
    if any(word in text for word in ("expected", "approximately", "outlook", "guidance")):
        return None
    match = re.search(r"(?P<negative>\()?\s*\$?\s*(?P<number>\d[\d,]*(?:\.\d+)?)", text)
    if not match:
        return None
    try:
        value_number = float(match.group("number").replace(",", ""))
    except ValueError:
        return None
    if match.group("negative"):
        value_number = -value_number
    if "billion" in text:
        return value_number, 1_000_000_000.0
    if "million" in text:
        return value_number, 1_000_000.0
    return (value_number, 1.0) if not scale_required else None


def _table_level_scale(rows: tuple[tuple[str, ...], ...]) -> tuple[float | None, bool]:
    header_text = _normalized_table_text(" ".join(cell for row in rows[:2] for cell in row))
    scales = {
        {"thousand": 1_000.0, "million": 1_000_000.0, "billion": 1_000_000_000.0}[match.group(1).rstrip("s")]
        for pattern in (
            r"\b(?:dollars?|amounts?|figures?)\b.{0,30}?\b(thousands?|millions?|billions?)\b",
            r"\(\s*in\s+(thousands?|millions?|billions?)\s*\)",
        )
        for match in re.finditer(pattern, header_text)
    }
    if len(scales) != 1:
        return None, bool(scales)
    return next(iter(scales)), False


def _derived_q4_context(text: str) -> bool:
    normalized = _normalized_table_text(text)
    annual_pattern = r"\b(?:annual|full[- ]year)\b"
    subtraction_pattern = r"\b(?:less|minus|subtract(?:ing|ed)?|deduct(?:ing|ed)?)\b"
    short_period_pattern = r"\b(?:nine|9)[- ]months?\b|\b(?:the\s+)?first\s+(?:three|3)\s+quarters?\b"
    direct_arithmetic = any(
        re.search(pattern, normalized)
        for pattern in (
            rf"{annual_pattern}.{{0,80}}{subtraction_pattern}.{{0,80}}(?:{short_period_pattern})",
            rf"(?:{short_period_pattern}).{{0,80}}{subtraction_pattern}.{{0,80}}{annual_pattern}",
        )
    )
    if direct_arithmetic:
        return True

    for match in re.finditer(
        r"\b(?:comput(?:e|ed|ing)|calculat(?:e|ed|ing)|deriv(?:e|ed|ing)|subtract(?:ing|ed)|deduct(?:ing|ed))\b",
        normalized,
    ):
        context = normalized[max(0, match.start() - 120) : match.end() + 120]
        if (
            re.search(annual_pattern, context)
            and re.search(subtraction_pattern, context)
            and re.search(short_period_pattern, context)
        ):
            return True
    return False


def _q4_metric_values(
    rows: tuple[tuple[str, ...], ...],
    value_column: int = 1,
) -> tuple[float | None, float | None, bool, bool, bool]:
    revenue: float | None = None
    eps: float | None = None
    non_gaap_eps_present = False
    derived = False
    revenue_scale_missing = False
    table_scale, table_scale_ambiguous = _table_level_scale(rows)
    for row in rows:
        if len(row) <= value_column:
            continue
        label = _normalized_table_text(row[0])
        value = row[value_column]
        if any(word in label for word in ("less", "minus", "subtract", "derived", "calculated")):
            derived = True
            continue
        if label in {"revenue", "total revenue", "net revenue"}:
            parsed = _table_number(value, scale_required=False)
            if parsed is not None:
                raw_value, value_scale = parsed
                if table_scale_ambiguous:
                    revenue_scale_missing = True
                elif value_scale != 1.0 and table_scale is not None and value_scale != table_scale:
                    revenue_scale_missing = True
                elif value_scale != 1.0:
                    revenue = raw_value * value_scale
                elif table_scale is not None:
                    revenue = raw_value * table_scale
                else:
                    revenue_scale_missing = True
        elif "non-gaap" in label and "earnings per share" in label:
            non_gaap_eps_present = True
        elif label in {
            "gaap diluted earnings per share",
            "diluted gaap earnings per share",
            "gaap diluted eps",
        }:
            parsed = _table_number(value, scale_required=False)
            if parsed is not None:
                eps = parsed[0]
    return revenue, eps, non_gaap_eps_present, derived, revenue_scale_missing


def _merge_q4_metric_values(
    candidates: Sequence[tuple[float | None, float | None]],
) -> tuple[float | None, float | None] | None:
    revenue_values = {revenue for revenue, _eps in candidates if revenue is not None}
    eps_values = {eps for _revenue, eps in candidates if eps is not None}
    if len(revenue_values) > 1 or len(eps_values) > 1:
        return None
    return (
        next(iter(revenue_values)) if revenue_values else None,
        next(iter(eps_values)) if eps_values else None,
    )


def _split_adjustment_basis(document_text: str) -> str:
    text = _normalized_table_text(document_text)
    match = re.search(
        r"(?:retrospectively|retroactively) adjusted[^.]{0,160}?split[^.]{0,160}?effective\s+([a-z]+\s+\d{1,2},\s+20\d{2})",
        text,
    )
    if not match:
        return PRIMARY_SPLIT_BASIS_UNVERIFIED
    try:
        effective_date = datetime.strptime(match.group(1), "%B %d, %Y").date()
    except ValueError:
        return PRIMARY_SPLIT_BASIS_UNVERIFIED
    return f"split_adjusted_{effective_date.isoformat().replace('-', '_')}"


def extract_explicit_q4_actual(
    ticker: str,
    exhibit: FiledExhibit,
    document_text: str,
    *,
    fiscal_period: str,
    filed_at: str,
    retrieved_at: str,
    cutoff: str | None = None,
) -> ExtractionResult:
    normalized_ticker = str(ticker or "").strip().upper()
    parser = _StructuredTableParser()
    parser.feed(document_text or "")
    audit_rows: list[ExtractionAuditRow] = []
    if not re.fullmatch(r"20\d{2}-Q4", fiscal_period or ""):
        return ExtractionResult(
            rows=(),
            audit_rows=(
                _q4_audit(normalized_ticker, "ambiguous_period_header", "quarterly_actual", "", exhibit, "fiscal period is not an explicit Q4 identity"),
            ),
        )
    explicit_period = _explicit_q4_fiscal_period(parser.page_text)
    if explicit_period is not None and explicit_period != fiscal_period:
        return ExtractionResult(
            rows=(),
            audit_rows=(
                _q4_audit(normalized_ticker, "ambiguous_period_header", "quarterly_actual", fiscal_period, exhibit, "document does not state one matching fiscal Q4 identity"),
            ),
        )
    matching_tables = [
        (rows, value_column)
        for rows, _table_text in parser.tables
        if (value_column := _q4_value_column(rows, fiscal_period)) is not None
    ]
    if not matching_tables:
        state = "ambiguous_period_header" if any(_has_ambiguous_q4_header(rows) for rows, _text in parser.tables) else "quarter_header_missing"
        audit_rows.append(
            _q4_audit(normalized_ticker, state, "quarterly_actual", fiscal_period, exhibit, "no structured table has an unambiguous matching Q4 header")
        )
        if _derived_q4_context(parser.page_text) or any(_q4_metric_values(rows)[3] for rows, _text in parser.tables):
            audit_rows.append(
                _q4_audit(normalized_ticker, "derived_q4_rejected", "quarterly_actual", fiscal_period, exhibit, "Q4 table labels a metric as derived or arithmetic")
            )
        return ExtractionResult(
            rows=(),
            audit_rows=tuple(audit_rows),
        )
    if _derived_q4_context(parser.page_text):
        return ExtractionResult(
            rows=(),
            audit_rows=(
                _q4_audit(normalized_ticker, "derived_q4_rejected", "quarterly_actual", fiscal_period, exhibit, "Q4 exhibit context states the selected result was derived from annual and nine-month values"),
            ),
        )
    candidates: list[tuple[float | None, float | None]] = []
    accepted_period_end_dates: set[str] = set()
    for rows, value_column in matching_tables:
        table_text = _normalized_table_text(" ".join(cell for row in rows for cell in row))
        revenue, eps, non_gaap_eps_present, derived, revenue_scale_missing = _q4_metric_values(rows, value_column)
        table_period_end_dates = _q4_period_end_dates(((rows, value_column),))
        if any(word in table_text for word in ("outlook", "expected", "approximately", "guidance")):
            audit_rows.append(
                _q4_audit(normalized_ticker, "guidance_or_outlook_rejected", "quarterly_actual", fiscal_period, exhibit, "Q4 table contains guidance or outlook language")
            )
            if non_gaap_eps_present and eps is None:
                audit_rows.append(
                    _q4_audit(normalized_ticker, "gaap_eps_missing", "eps", fiscal_period, exhibit, "non-GAAP EPS is not accepted without an explicit GAAP diluted EPS label")
                )
            continue
        if derived:
            audit_rows.append(
                _q4_audit(normalized_ticker, "derived_q4_rejected", "quarterly_actual", fiscal_period, exhibit, "Q4 table labels a metric as derived or arithmetic")
            )
            continue
        if revenue_scale_missing:
            audit_rows.append(
                _q4_audit(normalized_ticker, "revenue_scale_missing", "revenue", fiscal_period, exhibit, "Revenue lacks one unambiguous dollar scale in the selected Q4 table context")
            )
        if non_gaap_eps_present and eps is None:
            audit_rows.append(
                _q4_audit(normalized_ticker, "gaap_eps_missing", "eps", fiscal_period, exhibit, "non-GAAP EPS is not accepted without an explicit GAAP diluted EPS label")
            )
        if revenue is not None and len(table_period_end_dates) != 1:
            audit_rows.append(
                _q4_audit(
                    normalized_ticker,
                    "period_end_missing" if not table_period_end_dates else "period_end_ambiguous",
                    "revenue",
                    fiscal_period,
                    exhibit,
                    "Revenue table does not state one explicit period-end date for the Q4 value column",
                )
            )
            revenue = None
        if eps is not None and len(table_period_end_dates) != 1:
            audit_rows.append(
                _q4_audit(
                    normalized_ticker,
                    "period_end_missing" if not table_period_end_dates else "period_end_ambiguous",
                    "eps",
                    fiscal_period,
                    exhibit,
                    "EPS table does not state one explicit period-end date for the Q4 value column",
                )
            )
            eps = None
        if revenue is not None or eps is not None:
            candidates.append((revenue, eps))
            accepted_period_end_dates.update(table_period_end_dates)
    if not candidates:
        if not audit_rows:
            audit_rows.append(
                _q4_audit(normalized_ticker, "ambiguous_concept", "quarterly_actual", fiscal_period, exhibit, "explicit Revenue and GAAP diluted EPS labels were not found in a Q4 table")
            )
        return ExtractionResult(rows=(), audit_rows=tuple(audit_rows))
    resolved_metrics = _merge_q4_metric_values(candidates)
    if resolved_metrics is None:
        audit_rows.append(
            _q4_audit(normalized_ticker, "ambiguous_concept", "quarterly_actual", fiscal_period, exhibit, "multiple Q4 result tables disagree")
        )
        return ExtractionResult(rows=(), audit_rows=tuple(audit_rows))
    period_end_dates = accepted_period_end_dates
    if len(period_end_dates) != 1:
        state = "period_end_missing" if not period_end_dates else "period_end_ambiguous"
        detail = (
            "selected Q4 result table does not state an explicit period-end date"
            if not period_end_dates
            else "selected Q4 result table states multiple period-end dates for the Q4 value column"
        )
        audit_rows.append(
            _q4_audit(
                normalized_ticker,
                state,
                "quarterly_actual",
                fiscal_period,
                exhibit,
                detail,
            )
        )
        return ExtractionResult(rows=(), audit_rows=tuple(audit_rows))
    reported_at = datetime.fromisoformat(filed_at.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat()
    if cutoff is not None:
        cutoff_timestamp = datetime.fromisoformat(cutoff.replace("Z", "+00:00"))
        if cutoff_timestamp.tzinfo is None:
            raise ValueError("cutoff must be timezone-aware")
        if datetime.fromisoformat(reported_at) > cutoff_timestamp.astimezone(timezone.utc):
            audit_rows.append(
                _q4_audit(normalized_ticker, "post_cutoff_rejected", "quarterly_actual", fiscal_period, exhibit, f"reported_at={reported_at} is after cutoff={cutoff_timestamp.astimezone(timezone.utc).isoformat()}")
            )
            return ExtractionResult(rows=(), audit_rows=tuple(audit_rows))
    revenue, eps = resolved_metrics
    resolved_period_end = next(iter(period_end_dates))
    row = QuarterlyActual(
        ticker=normalized_ticker,
        fiscal_period=fiscal_period,
        period_end_date=resolved_period_end,
        reported_at=reported_at,
        revenue_actual=revenue,
        eps_actual=eps,
        source="sec_filed_exhibit",
        source_ref=exhibit.source_ref,
        retrieved_at=retrieved_at,
        split_adjustment_basis=_split_adjustment_basis(parser.page_text),
    )
    for metric, value in (("revenue", revenue), ("eps", eps)):
        if value is not None:
            audit_rows.append(
                _q4_audit(normalized_ticker, "accepted_explicit_q4", metric, fiscal_period, exhibit, f"explicit Q4 {metric} in SEC-filed {exhibit.document_type} table")
            )
    if revenue is None or eps is None:
        audit_rows.append(
            _q4_audit(normalized_ticker, "metric_partial", "quarterly_actual", fiscal_period, exhibit, "only one source-backed Q4 metric is available")
        )
    return ExtractionResult(rows=(row,), audit_rows=tuple(audit_rows))


def _required_text(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


def _finite_json_number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        normalized = float(value)
    except OverflowError:
        return None
    return normalized if isfinite(normalized) else None


def _integral_fiscal_year(value: object) -> int | None:
    normalized = _finite_json_number(value)
    if normalized is None or not normalized.is_integer():
        return None
    return int(normalized)


def _normalized_fact(
    taxonomy: str,
    concept: str,
    unit: str,
    item: object,
) -> SecDurationFact | None:
    if not isinstance(item, Mapping):
        return None
    form = _required_text(item.get("form"))
    start = _required_text(item.get("start"))
    end = _required_text(item.get("end"))
    filed = _required_text(item.get("filed"))
    accession = _required_text(item.get("accn"))
    fiscal_period = _required_text(item.get("fp"))
    try:
        value = _finite_json_number(item.get("val"))
        fiscal_year = _integral_fiscal_year(item.get("fy"))
        if form not in SEC_QUARTERLY_FORMS or not all((start, end, filed, accession, fiscal_period)):
            return None
        if value is None or fiscal_year is None:
            return None
        date.fromisoformat(start)
        date.fromisoformat(end)
        date.fromisoformat(filed)
    except (TypeError, ValueError):
        return None
    return SecDurationFact(
        taxonomy=taxonomy,
        concept=concept,
        unit=unit,
        value=value,
        start=start,
        end=end,
        filed=filed,
        form=form,
        accession=accession,
        fiscal_year=fiscal_year,
        fiscal_period=fiscal_period,
        frame=str(item.get("frame") or "").strip(),
    )


def normalize_sec_duration_facts(payload: Mapping[str, object]) -> tuple[SecDurationFact, ...]:
    facts_root = payload.get("facts") if isinstance(payload, Mapping) else None
    if not isinstance(facts_root, Mapping):
        return ()
    facts: list[SecDurationFact] = []
    for taxonomy, taxonomy_facts in facts_root.items():
        if not isinstance(taxonomy_facts, Mapping):
            continue
        for concept, concept_data in taxonomy_facts.items():
            if not isinstance(concept_data, Mapping):
                continue
            units = concept_data.get("units")
            if not isinstance(units, Mapping):
                continue
            for unit, items in units.items():
                if not isinstance(items, list):
                    continue
                for item in items:
                    fact = _normalized_fact(str(taxonomy), str(concept), str(unit), item)
                    if fact is not None:
                        facts.append(fact)
    return tuple(
        sorted(
            facts,
            key=lambda fact: (
                fact.taxonomy,
                fact.concept,
                fact.unit,
                fact.accession,
                fact.fiscal_year,
                fact.fiscal_period,
                fact.end,
                fact.start,
                fact.filed,
                fact.value,
                fact.frame,
            ),
        )
    )


def _metric_for(fact: SecDurationFact) -> str | None:
    if fact.taxonomy != "us-gaap":
        return None
    if fact.concept in REVENUE_CONCEPTS:
        return "revenue"
    if fact.concept == EPS_CONCEPT:
        return "eps"
    return None


def _source_ref(cik: object, accession: str) -> str:
    cik_digits = "".join(character for character in str(cik or "") if character.isdigit()).lstrip("0") or "0"
    accession_path = accession.replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{cik_digits}/{accession_path}/"


def _reported_at(filed: str) -> str:
    return datetime.combine(date.fromisoformat(filed), time(23, 59, 59), tzinfo=timezone.utc).isoformat()


def _audit(
    ticker: str,
    state: str,
    metric: str,
    fiscal_period: str,
    source_ref: str,
    detail: str,
    fact: SecDurationFact | None = None,
) -> ExtractionAuditRow:
    return ExtractionAuditRow(
        ticker=ticker,
        state=state,
        metric=metric,
        fiscal_period=fiscal_period,
        source_ref=source_ref,
        detail=detail,
        concept=fact.concept if fact else "",
        start=fact.start if fact else "",
        end=fact.end if fact else "",
        frame=fact.frame if fact else "",
        accession=fact.accession if fact else "",
    )


def _choose_metric(
    facts: list[SecDurationFact],
    metric: str,
    ticker: str,
    fiscal_period: str,
    source_ref: str,
    audit_rows: list[ExtractionAuditRow],
) -> float | None:
    if not facts:
        return None
    frames = {fact.frame for fact in facts if fact.frame}
    values = {fact.value for fact in facts}
    if len(frames) > 1 or len(values) > 1:
        audit_rows.append(
            _audit(
                ticker,
                "ambiguous_concept",
                metric,
                fiscal_period,
                source_ref,
                "conflicting concepts, values, or SEC frames for one quarter",
                facts[0],
            )
        )
        return None
    if metric == "revenue":
        concept_rank = {concept: index for index, concept in enumerate(REVENUE_CONCEPTS)}
        facts.sort(key=lambda fact: (concept_rank[fact.concept], fact.unit, fact.frame))
    return facts[0].value


def extract_q1_q3_lineage(
    ticker: str,
    payload: Mapping[str, object],
    *,
    cutoff: str,
    retrieved_at: str,
) -> ExtractionResult:
    normalized_ticker = str(ticker or "").strip().upper()
    cutoff_timestamp = datetime.fromisoformat(cutoff.replace("Z", "+00:00"))
    if cutoff_timestamp.tzinfo is None:
        raise ValueError("cutoff must be timezone-aware")
    cutoff_timestamp = cutoff_timestamp.astimezone(timezone.utc)
    facts = normalize_sec_duration_facts(payload)
    audit_rows: list[ExtractionAuditRow] = []
    quarter_facts: list[SecDurationFact] = []
    for fact in facts:
        metric = _metric_for(fact)
        if metric is None:
            continue
        source_ref = _source_ref(payload.get("cik"), fact.accession)
        fiscal_period = f"{fact.fiscal_year}-{fact.fiscal_period}"
        if not 60 <= fact.duration_days <= 120:
            audit_rows.append(
                _audit(
                    normalized_ticker,
                    "cumulative_fact_rejected",
                    metric,
                    fiscal_period,
                    source_ref,
                    f"duration_days={fact.duration_days} is outside the 60-120 day quarter range",
                    fact,
                )
            )
            continue
        if fact.fiscal_period not in {"Q1", "Q2", "Q3"}:
            continue
        quarter_facts.append(fact)

    latest_end_by_filing: dict[tuple[str, int, str], str] = {}
    for fact in quarter_facts:
        key = (fact.accession, fact.fiscal_year, fact.fiscal_period)
        latest_end_by_filing[key] = max(latest_end_by_filing.get(key, fact.end), fact.end)

    current_facts: list[SecDurationFact] = []
    comparative_facts: list[SecDurationFact] = []
    for fact in quarter_facts:
        key = (fact.accession, fact.fiscal_year, fact.fiscal_period)
        metric = _metric_for(fact)
        assert metric is not None
        source_ref = _source_ref(payload.get("cik"), fact.accession)
        fiscal_period = f"{fact.fiscal_year}-{fact.fiscal_period}"
        if fact.end != latest_end_by_filing[key]:
            comparative_facts.append(fact)
            continue
        current_facts.append(fact)

    identities_by_end: dict[str, set[str]] = {}
    ends_by_identity: dict[str, set[str]] = {}
    for fact in current_facts:
        identity = f"{fact.fiscal_year}-{fact.fiscal_period}"
        identities_by_end.setdefault(fact.end, set()).add(identity)
        ends_by_identity.setdefault(identity, set()).add(fact.end)
    conflicting_ends = {end for end, identities in identities_by_end.items() if len(identities) > 1}
    conflicting_identities = {
        identity for identity, period_ends in ends_by_identity.items() if len(period_ends) > 1
    }
    for fact in current_facts:
        identity = f"{fact.fiscal_year}-{fact.fiscal_period}"
        if fact.end not in conflicting_ends and identity not in conflicting_identities:
            continue
        metric = _metric_for(fact)
        assert metric is not None
        detail = (
            "multiple current-quarter filings assign different fiscal identities to one period end"
            if fact.end in conflicting_ends
            else "one fiscal identity maps to multiple current-quarter period ends"
        )
        audit_rows.append(
            _audit(
                normalized_ticker,
                "fiscal_period_conflict",
                metric,
                identity,
                _source_ref(payload.get("cik"), fact.accession),
                detail,
                fact,
            )
        )

    facts_by_identity: list[tuple[SecDurationFact, str]] = []
    comparative_signatures: set[tuple[str, str, str, str, int, str]] = set()
    for fact in current_facts:
        identity = f"{fact.fiscal_year}-{fact.fiscal_period}"
        if fact.end not in conflicting_ends and identity not in conflicting_identities:
            facts_by_identity.append((fact, identity))
    for fact in comparative_facts:
        metric = _metric_for(fact)
        assert metric is not None
        source_ref = _source_ref(payload.get("cik"), fact.accession)
        identity = identities_by_end.get(fact.end, set())
        canonical_identity = next(iter(identity)) if len(identity) == 1 else None
        if (
            canonical_identity is not None
            and fact.end not in conflicting_ends
            and canonical_identity not in conflicting_identities
        ):
            facts_by_identity.append((fact, canonical_identity))
            comparative_signatures.add(
                (fact.accession, fact.start, fact.end, fact.filed, fact.fiscal_year, fact.fiscal_period)
            )
            continue
        audit_rows.append(
            _audit(
                normalized_ticker,
                "comparative_period_relabelled",
                metric,
                f"{fact.fiscal_year}-{fact.fiscal_period}",
                source_ref,
                "comparative period has no uniquely established original fiscal identity",
                fact,
            )
        )

    by_signature: dict[tuple[str, str, str, str, int, str], list[SecDurationFact]] = {}
    identity_by_signature: dict[tuple[str, str, str, str, int, str], str] = {}
    for fact, fiscal_period in facts_by_identity:
        signature = (fact.accession, fact.start, fact.end, fact.filed, fact.fiscal_year, fact.fiscal_period)
        by_signature.setdefault(signature, []).append(fact)
        identity_by_signature[signature] = fiscal_period

    rows: list[QuarterlyActual] = []
    for signature, signature_facts in sorted(by_signature.items(), key=lambda item: (item[0][2], item[0][3], item[0][0])):
        accession, start, end, filed, fiscal_year, fiscal_quarter = signature
        fiscal_period = identity_by_signature[signature]
        source_ref = _source_ref(payload.get("cik"), accession)
        revenue = _choose_metric(
            [fact for fact in signature_facts if _metric_for(fact) == "revenue"],
            "revenue",
            normalized_ticker,
            fiscal_period,
            source_ref,
            audit_rows,
        )
        eps = _choose_metric(
            [fact for fact in signature_facts if _metric_for(fact) == "eps"],
            "eps",
            normalized_ticker,
            fiscal_period,
            source_ref,
            audit_rows,
        )
        if revenue is None and eps is None:
            continue
        reported_at = _reported_at(filed)
        if datetime.fromisoformat(reported_at).astimezone(timezone.utc) > cutoff_timestamp:
            audit_rows.append(
                _audit(
                    normalized_ticker,
                    "post_cutoff_rejected",
                    "quarterly_actual",
                    fiscal_period,
                    source_ref,
                    f"reported_at={reported_at} is after cutoff={cutoff_timestamp.isoformat()}",
                    signature_facts[0],
                )
            )
            continue
        rows.append(
            QuarterlyActual(
                ticker=normalized_ticker,
                fiscal_period=fiscal_period,
                period_end_date=end,
                reported_at=reported_at,
                revenue_actual=revenue,
                eps_actual=eps,
                source="sec_companyfacts",
                source_ref=source_ref,
                retrieved_at=retrieved_at,
                split_adjustment_basis=(
                    COMPANYFACTS_SPLIT_BASIS_UNVERIFIED if eps is not None else "as_reported"
                ),
            )
        )
        accepted_state = "accepted_revision" if signature in comparative_signatures else "accepted_explicit_quarter"
        accepted_detail = (
            "comparative presentation inherits a uniquely established fiscal identity"
            if accepted_state == "accepted_revision"
            else "is a uniquely aligned current-quarter SEC duration fact"
        )
        for metric, value in (("revenue", revenue), ("eps", eps)):
            if value is not None:
                audit_rows.append(
                    _audit(
                        normalized_ticker,
                        accepted_state,
                        metric,
                        fiscal_period,
                        source_ref,
                        f"{metric} {accepted_detail}",
                        signature_facts[0],
                    )
                )
        if eps is not None:
            audit_rows.append(
                _audit(
                    normalized_ticker,
                    "split_basis_unverified",
                    "eps",
                    fiscal_period,
                    source_ref,
                    "SEC Companyfacts does not prove whether comparative diluted EPS is on a split-comparable basis",
                    signature_facts[0],
                )
            )
        if revenue is None or eps is None:
            audit_rows.append(
                _audit(
                    normalized_ticker,
                    "metric_partial",
                    "quarterly_actual",
                    fiscal_period,
                    source_ref,
                    "only one source-backed metric is available for the quarter",
                    signature_facts[0],
                )
            )
    return ExtractionResult(rows=tuple(rows), audit_rows=tuple(audit_rows))


def _same_actual_presentation(left: QuarterlyActual, right: QuarterlyActual) -> bool:
    return (
        left.period_end_date,
        left.revenue_actual,
        left.eps_actual,
        left.revenue_currency,
        left.revenue_unit_scale,
        left.revenue_basis,
        left.eps_currency,
        left.eps_basis,
        left.eps_share_basis,
        left.eps_operations_basis,
        left.split_adjustment_basis,
    ) == (
        right.period_end_date,
        right.revenue_actual,
        right.eps_actual,
        right.revenue_currency,
        right.revenue_unit_scale,
        right.revenue_basis,
        right.eps_currency,
        right.eps_basis,
        right.eps_share_basis,
        right.eps_operations_basis,
        right.split_adjustment_basis,
    )


def link_quarter_revisions(rows: Sequence[QuarterlyActual]) -> tuple[QuarterlyActual, ...]:
    linked: list[QuarterlyActual] = []
    for row in sorted(rows, key=lambda item: (item.ticker, item.fiscal_period, item.reported_at, item.source, item.source_ref)):
        family_rows = [
            prior
            for prior in linked
            if prior.ticker == row.ticker
            and prior.fiscal_period == row.fiscal_period
            and prior.period_end_date == row.period_end_date
            and prior.source == row.source
            and prior.reported_at < row.reported_at
        ]
        if family_rows and _same_actual_presentation(family_rows[-1], row):
            continue
        if family_rows:
            linked.append(replace(row, supersedes_source_ref=family_rows[-1].source_ref))
        else:
            linked.append(row)
    return tuple(linked)


def _actual_csv_row(row: QuarterlyActual) -> dict[str, object]:
    return {"schema_version": EVIDENCE_SCHEMA_VERSION, **asdict(row)}


def _cached_sec_ticker_map(cache_dir: Path) -> dict[str, dict[str, Any]]:
    """Read the standard SEC ticker cache without falling back to the network."""
    cache_path = cache_dir / "company_tickers.json"
    if not cache_path.exists():
        raise RuntimeError(f"SEC network access is disabled and ticker-map cache is missing: {cache_path}")
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"SEC network access is disabled and ticker-map cache is unreadable: {cache_path}") from exc
    rows = payload.values() if isinstance(payload, dict) else payload if isinstance(payload, list) else ()
    ticker_map: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        ticker = str(row.get("ticker") or "").strip().upper()
        cik_value = row.get("cik_str") or row.get("cik") or row.get("cikStr")
        if not ticker or cik_value in (None, ""):
            continue
        cik_text = str(cik_value).strip()
        cik = str(int(cik_text)).zfill(10) if cik_text.isdigit() else cik_text.zfill(10)
        ticker_map[ticker] = {
            "ticker": ticker,
            "cik": cik,
            "title": row.get("title") or row.get("name"),
            "exchange": row.get("exchange"),
        }
    if not ticker_map:
        raise RuntimeError(f"SEC network access is disabled and ticker-map cache has no usable rows: {cache_path}")
    return ticker_map


def _network_disabled_fetcher(*_args: object, **_kwargs: object) -> Any:
    raise RuntimeError("SEC network access is disabled; provide cached evidence or rerun without --no-network")


def _rejected_audit_rows(results: Mapping[str, ExtractionResult]) -> list[ExtractionAuditRow]:
    return [
        audit_row
        for ticker in sorted(results)
        for audit_row in results[ticker].audit_rows
        if audit_row.state in REJECTED_AUDIT_STATES
    ]


def _is_within(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


def _has_generated_stage_marker(root: Path) -> bool:
    audit_path = root / "sec_actuals_audit.json"
    if not audit_path.is_file():
        return False
    try:
        payload = json.loads(audit_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return (
        isinstance(payload, Mapping)
        and payload.get("mode") == "preview_only"
        and payload.get("automatic_apply") is False
    )


def _validated_stage_output_dir(output_dir: Path | str) -> Path:
    root = Path(output_dir).expanduser().resolve(strict=False)
    project_root = Path(__file__).resolve().parents[1]
    canonical_data = (project_root / "data").resolve(strict=False)
    if _is_within(root, canonical_data):
        raise ValueError(
            "SEC actuals staging requires a generated temporary/review directory outside canonical data and imports"
        )

    temporary_root = Path(tempfile.gettempdir()).resolve(strict=False)
    review_named = any(
        marker in part.lower()
        for part in root.parts
        for marker in ("generated", "review", "sec-actuals", "sec_actuals", "stage", "staging")
    )
    allowed_location = _is_within(root, temporary_root) or review_named
    if not allowed_location:
        raise ValueError(
            "SEC actuals staging requires a generated temporary/review directory"
        )

    if root.exists():
        if not root.is_dir():
            raise ValueError("SEC actuals staging output must be a directory")
        entries = {path.name for path in root.iterdir()}
        generated_stage = (
            not entries
            or entries <= {".sec-cache"}
            or (_has_generated_stage_marker(root) and entries <= _STAGE_OUTPUT_NAMES)
        )
        if not generated_stage:
            raise ValueError(
                "SEC actuals staging refuses an existing non-generated evidence directory; use a new generated temporary/review directory"
            )
    return root


def _stage_identity_conflicts(
    rows: Sequence[QuarterlyActual],
) -> tuple[set[tuple[str, str, str]], list[ExtractionAuditRow]]:
    period_ends_by_identity: dict[tuple[str, str], set[str]] = {}
    identities_by_period_end: dict[tuple[str, str], set[str]] = {}
    for row in rows:
        period_ends_by_identity.setdefault((row.ticker, row.fiscal_period), set()).add(
            row.period_end_date
        )
        identities_by_period_end.setdefault((row.ticker, row.period_end_date), set()).add(
            row.fiscal_period
        )
    conflicting_identities = {
        identity
        for identity, period_ends in period_ends_by_identity.items()
        if len(period_ends) > 1
    }
    conflicting_period_ends = {
        period_end
        for period_end, identities in identities_by_period_end.items()
        if len(identities) > 1
    }
    conflicts = {
        (row.ticker, row.fiscal_period, row.period_end_date)
        for row in rows
        if (row.ticker, row.fiscal_period) in conflicting_identities
        or (row.ticker, row.period_end_date) in conflicting_period_ends
    }
    audit_rows = [
        ExtractionAuditRow(
            ticker=row.ticker,
            state="fiscal_period_conflict",
            metric="quarterly_actual",
            fiscal_period=row.fiscal_period,
            source_ref=row.source_ref,
            detail=(
                "one period end maps to multiple fiscal identities at the staging boundary"
                if (row.ticker, row.period_end_date) in conflicting_period_ends
                else "one fiscal identity maps to multiple period ends at the staging boundary"
            ),
            end=row.period_end_date,
        )
        for row in rows
        if (row.ticker, row.fiscal_period, row.period_end_date) in conflicts
    ]
    return conflicts, audit_rows


def write_sec_actuals_stage(output_dir: Path, results: Mapping[str, ExtractionResult]) -> StageResult:
    root = _validated_stage_output_dir(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    requested_tickers = tuple(sorted({str(ticker).strip().upper() for ticker in results if str(ticker).strip()}))
    extracted_rows = [row for ticker in requested_tickers for row in results[ticker].rows]
    conflicting_rows, conflict_audit_rows = _stage_identity_conflicts(extracted_rows)
    linked_rows = link_quarter_revisions(
        [
            row
            for row in extracted_rows
            if (row.ticker, row.fiscal_period, row.period_end_date) not in conflicting_rows
        ]
    )
    accepted_tickers = tuple(sorted({row.ticker for row in linked_rows}))
    withheld_tickers = tuple(ticker for ticker in requested_tickers if ticker not in accepted_tickers)
    rejected_rows = _rejected_audit_rows(results) + conflict_audit_rows
    all_audit_rows = [
        audit_row
        for ticker in requested_tickers
        for audit_row in results[ticker].audit_rows
    ] + conflict_audit_rows

    quarterly_actuals_path = root / "quarterly_actuals.csv"
    with quarterly_actuals_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SCHEMAS["quarterly_actuals.csv"])
        writer.writeheader()
        writer.writerows(_actual_csv_row(row) for row in linked_rows)
    for filename in ("consensus_snapshots.csv", "signals.csv"):
        with (root / filename).open("w", newline="", encoding="utf-8") as handle:
            csv.writer(handle).writerow(SCHEMAS[filename])

    audit_path = root / "sec_actuals_audit.json"
    audit_payload = {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "mode": "preview_only",
        "automatic_apply": False,
        "requested_tickers": requested_tickers,
        "accepted_tickers": accepted_tickers,
        "withheld_tickers": withheld_tickers,
        "accepted_row_count": len(linked_rows),
        "rejected_row_count": len(rejected_rows),
        "audit_rows": [asdict(row) for row in all_audit_rows],
    }
    audit_path.write_text(json.dumps(audit_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    rejected_path = root / "sec_actuals_rejected.csv"
    rejected_fields = (
        "ticker",
        "state",
        "reason_code",
        "metric",
        "fiscal_period",
        "source_ref",
        "detail",
        "concept",
        "start",
        "end",
        "frame",
        "accession",
    )
    with rejected_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rejected_fields)
        writer.writeheader()
        writer.writerows({"reason_code": row.state, **asdict(row)} for row in rejected_rows)

    return StageResult(
        requested_tickers=requested_tickers,
        accepted_tickers=accepted_tickers,
        withheld_tickers=withheld_tickers,
        accepted_row_count=len(linked_rows),
        rejected_row_count=len(rejected_rows),
        quarterly_actuals_path=str(quarterly_actuals_path),
        audit_path=str(audit_path),
        rejected_path=str(rejected_path),
    )


def _recent_q4_candidate_filings(payload: Mapping[str, Any]) -> tuple[tuple[str, str, str], ...]:
    recent = payload.get("filings", {}).get("recent", {}) if isinstance(payload.get("filings"), Mapping) else {}
    if not isinstance(recent, Mapping):
        return ()
    forms = recent.get("form") if isinstance(recent.get("form"), list) else []
    filing_dates = recent.get("filingDate") if isinstance(recent.get("filingDate"), list) else []
    report_dates = recent.get("reportDate") if isinstance(recent.get("reportDate"), list) else []
    accessions = recent.get("accessionNumber") if isinstance(recent.get("accessionNumber"), list) else []
    candidates: list[tuple[str, str, str]] = []
    for index, form in enumerate(forms):
        if str(form or "").strip().upper() not in {"8-K", "8-K/A"}:
            continue
        accession = str(accessions[index] if index < len(accessions) else "").strip()
        filed_date = str(filing_dates[index] if index < len(filing_dates) else "").strip()
        report_date = str(report_dates[index] if index < len(report_dates) else "").strip()
        if accession and filed_date:
            candidates.append((accession, filed_date, report_date))
    return tuple(candidates)


def _q4_source_unavailable(
    ticker: str,
    source_ref: str,
    detail: str,
    accession: str = "",
) -> ExtractionAuditRow:
    return ExtractionAuditRow(
        ticker=ticker,
        state="q4_source_unavailable",
        metric="quarterly_actual",
        fiscal_period="",
        source_ref=source_ref,
        detail=detail,
        accession=accession,
    )


def _combine_q4_results(
    ticker: str,
    q4_results: Sequence[ExtractionResult],
) -> ExtractionResult:
    audit_rows = [audit_row for result in q4_results for audit_row in result.audit_rows]
    rows = [row for result in q4_results for row in result.rows]
    by_period: dict[str, list[QuarterlyActual]] = {}
    for row in rows:
        by_period.setdefault(row.fiscal_period, []).append(row)
    accepted_rows: list[QuarterlyActual] = []
    for fiscal_period, period_rows in sorted(by_period.items()):
        source_refs = {row.source_ref for row in period_rows}
        if len(source_refs) > 1:
            audit_rows.append(
                ExtractionAuditRow(
                    ticker=ticker,
                    state="ambiguous_concept",
                    metric="quarterly_actual",
                    fiscal_period=fiscal_period,
                    source_ref="",
                    detail="Q4 metrics span multiple SEC-filed exhibits; per-metric provenance cannot be represented",
                )
            )
            continue
        resolved_metrics = _merge_q4_metric_values(
            [(row.revenue_actual, row.eps_actual) for row in period_rows]
        )
        if resolved_metrics is None:
            audit_rows.append(
                ExtractionAuditRow(
                    ticker=ticker,
                    state="ambiguous_concept",
                    metric="quarterly_actual",
                    fiscal_period=fiscal_period,
                    source_ref=period_rows[0].source_ref,
                    detail="multiple SEC-filed Q4 exhibits disagree",
                )
            )
            continue
        canonical_row = sorted(period_rows, key=lambda row: row.source_ref)[0]
        accepted_rows.append(
            replace(
                canonical_row,
                revenue_actual=resolved_metrics[0],
                eps_actual=resolved_metrics[1],
            )
        )
    return ExtractionResult(rows=tuple(accepted_rows), audit_rows=tuple(audit_rows))


def _date_only_filing_availability(filed_date: str, cutoff: str) -> tuple[str | None, str | None]:
    """Treat date-only SEC metadata as available at 23:59:59 UTC and fail closed before then."""
    filing_day = date.fromisoformat(filed_date)
    cutoff_timestamp = datetime.fromisoformat(cutoff.replace("Z", "+00:00"))
    if cutoff_timestamp.tzinfo is None:
        raise ValueError("cutoff must be timezone-aware")
    conservative_available_at = datetime.fromisoformat(f"{filing_day.isoformat()}T23:59:59+00:00")
    normalized_cutoff = cutoff_timestamp.astimezone(timezone.utc)
    if conservative_available_at > normalized_cutoff:
        return None, (
            f"date-only filed metadata={filing_day.isoformat()} is treated as available at "
            f"{conservative_available_at.isoformat()}, after cutoff={normalized_cutoff.isoformat()}"
        )
    return conservative_available_at.isoformat(), None


def stage_sec_quarterly_actuals(
    tickers: Sequence[str],
    *,
    output_dir: Path,
    cutoff: str,
    user_agent: str | None,
    retrieved_at: str | None = None,
    cache_dir: Path | str | None = None,
    refresh: bool = False,
    allow_network: bool = True,
    sleep_seconds: float = 0.2,
    ticker_map: Mapping[str, Mapping[str, Any]] | None = None,
    ticker_map_loader: Callable[..., Mapping[str, Mapping[str, Any]]] = load_sec_ticker_map,
    ticker_map_fetcher: Callable[[str, str, float], Any] | None = None,
    companyfacts_loader: Callable[..., Mapping[str, Any]] = fetch_companyfacts,
    companyfacts_fetcher: Callable[[str, str, float], Any] | None = None,
    submissions_loader: Callable[..., Mapping[str, Any]] = fetch_sec_submission,
    submissions_fetcher: Callable[[str, str, float], Any] | None = None,
    filing_index_loader: Callable[..., str] = fetch_sec_filing_index,
    filing_index_fetcher: Callable[[str, str, float], str] | None = None,
    exhibit_document_loader: Callable[..., str] = fetch_sec_filing_document,
    exhibit_document_fetcher: Callable[[str, str, float], str] | None = None,
) -> StageResult:
    resolved_output_dir = _validated_stage_output_dir(output_dir)
    requested_tickers = tuple(sorted({str(ticker).strip().upper() for ticker in tickers if str(ticker).strip()}))
    resolved_cache_dir = Path(cache_dir) if cache_dir is not None else resolved_output_dir / ".sec-cache"
    provider_refresh = refresh if allow_network else False
    provider_cache = not allow_network
    if ticker_map is None:
        if allow_network:
            resolved_ticker_map = ticker_map_loader(
                cache_dir=resolved_cache_dir,
                user_agent=user_agent,
                refresh=provider_refresh,
                sleep_seconds=sleep_seconds,
                fetcher=ticker_map_fetcher,
            )
        else:
            resolved_ticker_map = _cached_sec_ticker_map(resolved_cache_dir)
    else:
        resolved_ticker_map = ticker_map
    resolved_retrieved_at = retrieved_at or datetime.now(timezone.utc).isoformat()
    results: dict[str, ExtractionResult] = {}
    for ticker in requested_tickers:
        cik = resolve_ticker_to_cik(ticker, dict(resolved_ticker_map))
        if cik is None:
            results[ticker] = ExtractionResult(
                rows=(),
                audit_rows=(
                    _audit(ticker, "ticker_unresolved", "quarterly_actual", "", "", "no SEC CIK mapping was found"),
                ),
            )
            continue
        try:
            payload = companyfacts_loader(
                cik,
                user_agent,
                cache=provider_cache,
                refresh=provider_refresh,
                cache_dir=resolved_cache_dir,
                sleep_seconds=sleep_seconds,
                fetcher=companyfacts_fetcher if allow_network else _network_disabled_fetcher,
            )
        except RuntimeError as exc:
            results[ticker] = ExtractionResult(
                rows=(),
                audit_rows=(
                    _audit(ticker, "companyfacts_fetch_failed", "quarterly_actual", "", "", str(exc)),
                ),
            )
            continue
        q1_q3_result = extract_q1_q3_lineage(
            ticker,
            payload,
            cutoff=cutoff,
            retrieved_at=resolved_retrieved_at,
        )
        try:
            submissions_payload = submissions_loader(
                cik,
                user_agent,
                cache=provider_cache,
                refresh=provider_refresh,
                cache_dir=resolved_cache_dir,
                sleep_seconds=sleep_seconds,
                fetcher=submissions_fetcher if allow_network else _network_disabled_fetcher,
            )
        except RuntimeError as exc:
            results[ticker] = ExtractionResult(
                rows=q1_q3_result.rows,
                audit_rows=q1_q3_result.audit_rows
                + (_q4_source_unavailable(ticker, "", f"SEC submissions lookup failed: {exc}"),),
            )
            continue
        q4_candidates = _recent_q4_candidate_filings(submissions_payload)
        q4_results: list[ExtractionResult] = []
        if not q4_candidates:
            q4_results.append(
                ExtractionResult(
                    rows=(),
                    audit_rows=(
                        _q4_source_unavailable(
                            ticker,
                            "",
                            "no eligible 8-K or 8-K/A Q4 candidate filing was found",
                        ),
                    ),
                )
            )
        for accession, filed_date, _report_date in q4_candidates:
            filed_at, cutoff_detail = _date_only_filing_availability(filed_date, cutoff)
            if filed_at is None:
                q4_results.append(
                    ExtractionResult(
                        rows=(),
                        audit_rows=(
                            ExtractionAuditRow(
                                ticker=ticker,
                                state="post_cutoff_rejected",
                                metric="quarterly_actual",
                                fiscal_period="",
                                source_ref="",
                                detail=cutoff_detail or "date-only filing metadata is unavailable at the requested cutoff",
                                accession=accession,
                            ),
                        ),
                    )
                )
                continue
            try:
                index_html = filing_index_loader(
                    cik,
                    accession,
                    user_agent,
                    cache=provider_cache,
                    refresh=provider_refresh,
                    cache_dir=resolved_cache_dir,
                    sleep_seconds=sleep_seconds,
                    fetcher=filing_index_fetcher if allow_network else _network_disabled_fetcher,
                )
            except RuntimeError as exc:
                q4_results.append(
                    ExtractionResult(
                        rows=(),
                        audit_rows=(_q4_source_unavailable(ticker, "", f"filing index lookup failed: {exc}", accession),),
                    )
                )
                continue
            exhibits = extract_filing_exhibits(index_html, cik=cik, accession=accession)
            if not exhibits:
                q4_results.append(
                    ExtractionResult(
                        rows=(),
                        audit_rows=(_q4_source_unavailable(ticker, "", "no EX-99 result exhibit was found", accession),),
                    )
                )
                continue
            for exhibit in exhibits:
                try:
                    document_text = exhibit_document_loader(
                        cik,
                        accession,
                        exhibit.document_name,
                        user_agent,
                        cache=provider_cache,
                        refresh=provider_refresh,
                        cache_dir=resolved_cache_dir,
                        sleep_seconds=sleep_seconds,
                        fetcher=exhibit_document_fetcher if allow_network else _network_disabled_fetcher,
                    )
                except RuntimeError as exc:
                    q4_results.append(
                        ExtractionResult(
                            rows=(),
                            audit_rows=(_q4_source_unavailable(ticker, exhibit.source_ref, f"exhibit lookup failed: {exc}", accession),),
                        )
                    )
                    continue
                fiscal_period = _explicit_q4_fiscal_period(document_text)
                if fiscal_period is None:
                    q4_results.append(
                        ExtractionResult(
                            rows=(),
                            audit_rows=(
                                _q4_audit(
                                    ticker,
                                    "ambiguous_period_header",
                                    "quarterly_actual",
                                    "",
                                    exhibit,
                                    "document does not state one explicit fiscal Q4 identity",
                                ),
                            ),
                        )
                    )
                    continue
                q4_results.append(
                    extract_explicit_q4_actual(
                        ticker,
                        exhibit,
                        document_text,
                        fiscal_period=fiscal_period,
                        filed_at=filed_at,
                        retrieved_at=resolved_retrieved_at,
                        cutoff=cutoff,
                    )
                )
        q4_result = _combine_q4_results(ticker, q4_results)
        results[ticker] = ExtractionResult(
            rows=q1_q3_result.rows + q4_result.rows,
            audit_rows=q1_q3_result.audit_rows + q4_result.audit_rows,
        )
    return write_sec_actuals_stage(resolved_output_dir, results)


def _continuity_gaps(rows: Sequence[Mapping[str, str]]) -> list[dict[str, object]]:
    periods = sorted(
        {
            (int(match.group("year")), int(match.group("quarter")))
            for row in rows
            if (match := _FISCAL_PERIOD_PATTERN.match(str(row.get("fiscal_period") or "")))
        }
    )
    gaps: list[dict[str, object]] = []
    for prior, current in zip(periods, periods[1:]):
        prior_index = prior[0] * 4 + prior[1] - 1
        current_index = current[0] * 4 + current[1] - 1
        if current_index <= prior_index + 1:
            continue
        missing = []
        for index in range(prior_index + 1, current_index):
            year, quarter_offset = divmod(index, 4)
            missing.append(f"{year}-Q{quarter_offset + 1}")
        gaps.append(
            {
                "after_fiscal_period": f"{prior[0]}-Q{prior[1]}",
                "before_fiscal_period": f"{current[0]}-Q{current[1]}",
                "missing_fiscal_periods": missing,
            }
        )
    return gaps


def build_sec_actuals_stage_summary(result: StageResult) -> dict[str, object]:
    with Path(result.quarterly_actuals_path).open(newline="", encoding="utf-8") as handle:
        accepted_rows = list(csv.DictReader(handle))
    with Path(result.rejected_path).open(newline="", encoding="utf-8") as handle:
        rejected_rows = list(csv.DictReader(handle))
    ticker_summaries: dict[str, dict[str, object]] = {}
    for ticker in result.requested_tickers:
        ticker_accepted = [row for row in accepted_rows if row.get("ticker") == ticker]
        ticker_rejected = [row for row in rejected_rows if row.get("ticker") == ticker]
        source_refs = sorted(
            {
                str(row.get("source_ref") or "")
                for row in ticker_accepted + ticker_rejected
                if str(row.get("source_ref") or "")
            }
        )
        metrics = {}
        for metric, value_field in (("revenue", "revenue_actual"), ("eps", "eps_actual")):
            metric_accepted = [
                row for row in ticker_accepted if str(row.get(value_field) or "").strip()
            ]
            metrics[metric] = {
                "accepted_rows": metric_accepted,
                "missing_q4": not any(
                    str(row.get("fiscal_period") or "").endswith("-Q4")
                    for row in metric_accepted
                ),
                "continuity_gaps": _continuity_gaps(metric_accepted),
            }
        ticker_summaries[ticker] = {
            "accepted_rows": ticker_accepted,
            "rejected_rows": ticker_rejected,
            "metrics": metrics,
            "source_refs": source_refs,
        }
    return {
        "automatic_apply": False,
        "requested_tickers": list(result.requested_tickers),
        "accepted_tickers": list(result.accepted_tickers),
        "withheld_tickers": list(result.withheld_tickers),
        "accepted_row_count": result.accepted_row_count,
        "rejected_row_count": result.rejected_row_count,
        "paths": {
            "quarterly_actuals": result.quarterly_actuals_path,
            "audit": result.audit_path,
            "rejected_rows": result.rejected_path,
        },
        "tickers": ticker_summaries,
    }


def main(
    argv: Sequence[str] | None = None,
    *,
    stage_runner: Callable[..., StageResult] = stage_sec_quarterly_actuals,
) -> None:
    parser = argparse.ArgumentParser(description="Stage SEC quarterly actual evidence to an explicit output directory.")
    parser.add_argument("--tickers", required=True, help="Comma-separated ticker list.")
    parser.add_argument("--output-dir", required=True, help="Generated staging directory; no canonical data is changed.")
    parser.add_argument("--cutoff", required=True, help="Timezone-aware evidence cutoff timestamp.")
    parser.add_argument("--sec-user-agent", default=os.environ.get("SEC_USER_AGENT"), help="Identifying SEC User-Agent.")
    parser.add_argument("--no-network", action="store_true", help="Use cached SEC evidence only.")
    parser.add_argument("--sec-refresh", action="store_true", help="Refresh SEC caches before staging.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable staging summary.")
    parser.add_argument(
        "--max-runtime-seconds",
        type=float,
        default=None,
        help="Fail closed if staging exceeds this many seconds.",
    )
    args = parser.parse_args(argv)
    if args.no_network and args.sec_refresh:
        parser.error("--sec-refresh cannot be combined with --no-network")
    try:
        output_dir = _validated_stage_output_dir(args.output_dir)
    except ValueError as exc:
        parser.error(str(exc))
    tickers = [ticker.strip() for ticker in args.tickers.split(",") if ticker.strip()]
    previous_handler = None
    if args.max_runtime_seconds is not None:
        if args.max_runtime_seconds <= 0:
            parser.error("--max-runtime-seconds must be greater than zero")

        def _stage_timeout(_signum, _frame):
            raise TimeoutError(f"SEC actuals staging exceeded max runtime of {args.max_runtime_seconds:g} seconds")

        previous_handler = signal.getsignal(signal.SIGALRM)
        signal.signal(signal.SIGALRM, _stage_timeout)
        signal.setitimer(signal.ITIMER_REAL, args.max_runtime_seconds)
    try:
        result = stage_runner(
            tickers,
            output_dir=output_dir,
            cutoff=args.cutoff,
            user_agent=args.sec_user_agent,
            refresh=args.sec_refresh,
            allow_network=not args.no_network,
        )
    except TimeoutError as exc:
        parser.error(f"environment_limited: {exc}")
    finally:
        if args.max_runtime_seconds is not None:
            signal.setitimer(signal.ITIMER_REAL, 0.0)
            signal.signal(signal.SIGALRM, previous_handler)
    summary = build_sec_actuals_stage_summary(result)
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
        return
    print(f"automatic_apply: {str(summary['automatic_apply']).lower()}")
    print(f"accepted_row_count: {summary['accepted_row_count']}")
    print(f"rejected_row_count: {summary['rejected_row_count']}")
    for ticker, ticker_summary in summary["tickers"].items():
        print(
            f"{ticker}: accepted_rows={len(ticker_summary['accepted_rows'])} "
            f"rejected_rows={len(ticker_summary['rejected_rows'])} "
            f"revenue_missing_q4={str(ticker_summary['metrics']['revenue']['missing_q4']).lower()} "
            f"eps_missing_q4={str(ticker_summary['metrics']['eps']['missing_q4']).lower()}"
        )


if __name__ == "__main__":
    main()
