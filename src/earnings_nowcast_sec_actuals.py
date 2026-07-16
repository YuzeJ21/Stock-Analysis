from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from math import isfinite
from typing import Mapping

from src.earnings_nowcast_contract import QuarterlyActual


REVENUE_CONCEPTS = (
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "SalesRevenueNet",
)
EPS_CONCEPT = "EarningsPerShareDiluted"
SEC_QUARTERLY_FORMS = frozenset(("10-Q", "10-Q/A"))


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


@dataclass(frozen=True)
class ExtractionResult:
    rows: tuple[QuarterlyActual, ...]
    audit_rows: tuple[ExtractionAuditRow, ...]


def _required_text(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


def _finite_json_number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    normalized = float(value)
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
) -> ExtractionAuditRow:
    return ExtractionAuditRow(
        ticker=ticker,
        state=state,
        metric=metric,
        fiscal_period=fiscal_period,
        source_ref=source_ref,
        detail=detail,
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
                )
            )
    return ExtractionResult(rows=tuple(rows), audit_rows=tuple(audit_rows))
