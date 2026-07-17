from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict, dataclass, replace
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from math import isfinite
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from src.earnings_nowcast_contract import QuarterlyActual
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
REJECTED_AUDIT_STATES = frozenset(
    (
        "ambiguous_concept",
        "ambiguous_fiscal_identity",
        "comparative_period_relabelled",
        "companyfacts_fetch_failed",
        "cumulative_fact_rejected",
        "fiscal_period_conflict",
        "post_cutoff_rejected",
        "q4_source_unavailable",
        "quarter_header_missing",
        "ambiguous_period_header",
        "guidance_or_outlook_rejected",
        "gaap_eps_missing",
        "derived_q4_rejected",
        "ticker_unresolved",
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
        elif self._table_depth and lowered == "tr":
            self._row = []
        elif self._table_depth and lowered in {"td", "th"} and self._row is not None:
            self._cell = []

    def handle_data(self, data: str) -> None:
        self._page_text.append(data)
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered in {"td", "th"} and self._cell is not None and self._row is not None:
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


def _q4_metric_values(
    rows: tuple[tuple[str, ...], ...],
    value_column: int = 1,
) -> tuple[float | None, float | None, bool, bool]:
    revenue: float | None = None
    eps: float | None = None
    non_gaap_eps_present = False
    derived = False
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
                raw_value, scale = parsed
                revenue = raw_value * scale
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
    return revenue, eps, non_gaap_eps_present, derived


def _split_adjustment_basis(document_text: str) -> str:
    text = _normalized_table_text(document_text)
    match = re.search(
        r"(?:retrospectively|retroactively) adjusted[^.]{0,160}?split[^.]{0,160}?effective\s+([a-z]+\s+\d{1,2},\s+20\d{2})",
        text,
    )
    if not match:
        return "as_reported"
    try:
        effective_date = datetime.strptime(match.group(1), "%B %d, %Y").date()
    except ValueError:
        return "as_reported"
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
    period_end_date: str | None = None,
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
        if any(_q4_metric_values(rows)[3] for rows, _text in parser.tables):
            audit_rows.append(
                _q4_audit(normalized_ticker, "derived_q4_rejected", "quarterly_actual", fiscal_period, exhibit, "Q4 table labels a metric as derived or arithmetic")
            )
        return ExtractionResult(
            rows=(),
            audit_rows=tuple(audit_rows),
        )
    candidates: list[tuple[float | None, float | None]] = []
    for rows, value_column in matching_tables:
        table_text = _normalized_table_text(" ".join(cell for row in rows for cell in row))
        revenue, eps, non_gaap_eps_present, derived = _q4_metric_values(rows, value_column)
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
        if non_gaap_eps_present and eps is None:
            audit_rows.append(
                _q4_audit(normalized_ticker, "gaap_eps_missing", "eps", fiscal_period, exhibit, "non-GAAP EPS is not accepted without an explicit GAAP diluted EPS label")
            )
        if revenue is not None or eps is not None:
            candidates.append((revenue, eps))
    presentations = set(candidates)
    if len(presentations) > 1:
        audit_rows.append(
            _q4_audit(normalized_ticker, "ambiguous_concept", "quarterly_actual", fiscal_period, exhibit, "multiple Q4 result tables disagree")
        )
        return ExtractionResult(rows=(), audit_rows=tuple(audit_rows))
    if not candidates:
        if not audit_rows:
            audit_rows.append(
                _q4_audit(normalized_ticker, "ambiguous_concept", "quarterly_actual", fiscal_period, exhibit, "explicit Revenue and GAAP diluted EPS labels were not found in a Q4 table")
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
    revenue, eps = candidates[0]
    resolved_period_end = period_end_date or reported_at[:10]
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
    return datetime.combine(date.fromisoformat(filed), datetime.min.time(), tzinfo=timezone.utc).isoformat()


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
    for fact in current_facts:
        identities_by_end.setdefault(fact.end, set()).add(f"{fact.fiscal_year}-{fact.fiscal_period}")
    conflicting_ends = {end for end, identities in identities_by_end.items() if len(identities) > 1}
    for fact in current_facts:
        if fact.end not in conflicting_ends:
            continue
        metric = _metric_for(fact)
        assert metric is not None
        audit_rows.append(
            _audit(
                normalized_ticker,
                "fiscal_period_conflict",
                metric,
                f"{fact.fiscal_year}-{fact.fiscal_period}",
                _source_ref(payload.get("cik"), fact.accession),
                "multiple current-quarter filings assign different fiscal identities to one period end",
                fact,
            )
        )

    facts_by_identity: list[tuple[SecDurationFact, str]] = []
    comparative_signatures: set[tuple[str, str, str, str, int, str]] = set()
    for fact in current_facts:
        if fact.end not in conflicting_ends:
            facts_by_identity.append((fact, f"{fact.fiscal_year}-{fact.fiscal_period}"))
    for fact in comparative_facts:
        metric = _metric_for(fact)
        assert metric is not None
        source_ref = _source_ref(payload.get("cik"), fact.accession)
        identity = identities_by_end.get(fact.end, set())
        if len(identity) == 1 and fact.end not in conflicting_ends:
            facts_by_identity.append((fact, next(iter(identity))))
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
            and prior.source == row.source
            and prior.reported_at < row.reported_at
        ]
        if any(_same_actual_presentation(prior, row) for prior in family_rows):
            continue
        if family_rows:
            linked.append(replace(row, supersedes_source_ref=family_rows[-1].source_ref))
        else:
            linked.append(row)
    return tuple(linked)


def _actual_csv_row(row: QuarterlyActual) -> dict[str, object]:
    return {"schema_version": EVIDENCE_SCHEMA_VERSION, **asdict(row)}


def _rejected_audit_rows(results: Mapping[str, ExtractionResult]) -> list[ExtractionAuditRow]:
    return [
        audit_row
        for ticker in sorted(results)
        for audit_row in results[ticker].audit_rows
        if audit_row.state in REJECTED_AUDIT_STATES
    ]


def write_sec_actuals_stage(output_dir: Path, results: Mapping[str, ExtractionResult]) -> StageResult:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    requested_tickers = tuple(sorted({str(ticker).strip().upper() for ticker in results if str(ticker).strip()}))
    linked_rows = link_quarter_revisions(
        [row for ticker in requested_tickers for row in results[ticker].rows]
    )
    accepted_tickers = tuple(sorted({row.ticker for row in linked_rows}))
    withheld_tickers = tuple(ticker for ticker in requested_tickers if ticker not in accepted_tickers)
    rejected_rows = _rejected_audit_rows(results)

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
        "audit_rows": [asdict(row) for ticker in requested_tickers for row in results[ticker].audit_rows],
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
        presentations = {
            (row.revenue_actual, row.eps_actual, row.split_adjustment_basis, row.period_end_date)
            for row in period_rows
        }
        if len(presentations) > 1:
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
        accepted_rows.append(sorted(period_rows, key=lambda row: row.source_ref)[0])
    return ExtractionResult(rows=tuple(accepted_rows), audit_rows=tuple(audit_rows))


def stage_sec_quarterly_actuals(
    tickers: Sequence[str],
    *,
    output_dir: Path,
    cutoff: str,
    user_agent: str | None,
    retrieved_at: str | None = None,
    cache_dir: Path | str | None = None,
    refresh: bool = False,
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
    requested_tickers = tuple(sorted({str(ticker).strip().upper() for ticker in tickers if str(ticker).strip()}))
    if ticker_map is None:
        resolved_cache_dir = Path(cache_dir) if cache_dir is not None else Path(output_dir) / ".sec-cache"
        resolved_ticker_map = ticker_map_loader(
            cache_dir=resolved_cache_dir,
            user_agent=user_agent,
            refresh=refresh,
            sleep_seconds=sleep_seconds,
            fetcher=ticker_map_fetcher,
        )
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
                cache=False,
                refresh=refresh,
                cache_dir=cache_dir or Path(output_dir) / ".sec-cache",
                sleep_seconds=sleep_seconds,
                fetcher=companyfacts_fetcher,
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
                cache=False,
                refresh=refresh,
                cache_dir=cache_dir or Path(output_dir) / ".sec-cache",
                sleep_seconds=sleep_seconds,
                fetcher=submissions_fetcher,
            )
        except RuntimeError as exc:
            results[ticker] = ExtractionResult(
                rows=q1_q3_result.rows,
                audit_rows=q1_q3_result.audit_rows
                + (_q4_source_unavailable(ticker, "", f"SEC submissions lookup failed: {exc}"),),
            )
            continue
        q4_results: list[ExtractionResult] = []
        for accession, filed_date, report_date in _recent_q4_candidate_filings(submissions_payload):
            try:
                index_html = filing_index_loader(
                    cik,
                    accession,
                    user_agent,
                    cache=False,
                    refresh=refresh,
                    cache_dir=cache_dir or Path(output_dir) / ".sec-cache",
                    sleep_seconds=sleep_seconds,
                    fetcher=filing_index_fetcher,
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
                        cache=False,
                        refresh=refresh,
                        cache_dir=cache_dir or Path(output_dir) / ".sec-cache",
                        sleep_seconds=sleep_seconds,
                        fetcher=exhibit_document_fetcher,
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
                        filed_at=f"{filed_date}T00:00:00Z",
                        retrieved_at=resolved_retrieved_at,
                        cutoff=cutoff,
                        period_end_date=report_date or None,
                    )
                )
        q4_result = _combine_q4_results(ticker, q4_results)
        results[ticker] = ExtractionResult(
            rows=q1_q3_result.rows + q4_result.rows,
            audit_rows=q1_q3_result.audit_rows + q4_result.audit_rows,
        )
    return write_sec_actuals_stage(output_dir, results)
