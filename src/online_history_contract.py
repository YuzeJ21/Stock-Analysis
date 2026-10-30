"""Validate source-bound annual history at the display boundary."""

import re
from collections import Counter
from typing import Any, Mapping

from src.company_sec_online_preview import (
    ANNUAL_FORMS, REVENUE_CONCEPTS, OPERATING_COMPONENT_CONCEPTS,
    _iso_date, _utc_timestamp, _finite_direct_number,
)


def compare_annual_periods(periods):
    comparisons = []
    for prior, current in zip(periods, periods[1:]):
        first, last = _iso_date(prior["period_end"]), _iso_date(current["period_end"])
        pstart, cstart = _iso_date(prior["period_start"]), _iso_date(current["period_start"])
        comparable = (
            prior["status"] == current["status"] == "available"
            and 300 <= (last - first).days <= 430 and (cstart - first).days == 1
            and abs((last - cstart).days - (first - pstart).days) <= 14
        )
        direction = None
        if comparable:
            direction = "increased" if current["revenue"] > prior["revenue"] else "decreased" if current["revenue"] < prior["revenue"] else "unchanged"
        comparisons.append({
            "from_period": prior["period_end"], "to_period": current["period_end"],
            "status": "comparable" if comparable else "withheld", "direction": direction,
            "growth_rate": None, "growth_rate_status": "registered_derived_field_scope_required",
            "reason": None if comparable else "annual_period_or_source_gap",
        })
    return comparisons


def validated_annual_history(view: Mapping[str, Any]) -> dict[str, Any] | None:
    history = view.get("annual_history")
    if not isinstance(history, Mapping) or history.get("status") != "inspection_only":
        return None
    if any(history.get(h) != view.get(v) for h, v in (
        ("ticker", "ticker"), ("sec_cik", "sec_cik"), ("source_url", "source_url"), ("observed_at", "retrieved_at_utc"),
    )) or history.get("history_basis") != "latest_reported_as_observed_not_point_in_time" or history.get("unit") != "USD":
        return None
    cik = view.get("sec_cik")
    if not isinstance(cik, str) or re.fullmatch(r"\d{10}", cik) is None or view.get("source_url") != f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json":
        return None
    observed = _utc_timestamp(history.get("observed_at")); latest = _iso_date(view.get("period_end"))
    periods = history.get("periods")
    if observed is None or latest is None or not isinstance(periods, list) or not 1 <= len(periods) <= 6:
        return None
    concept = (history.get("taxonomy"), history.get("concept"))
    if not all(isinstance(x, str) for x in concept) or concept not in REVENUE_CONCEPTS:
        return None
    previous = None
    for row in periods:
        if not isinstance(row, Mapping): return None
        start, end, filed = _iso_date(row.get("period_start")), _iso_date(row.get("period_end")), _iso_date(row.get("filed"))
        if end is None or filed is None or not end <= filed <= observed.date() or end > latest or previous is not None and end <= previous:
            return None
        previous = end
        if row.get("status") == "withheld":
            if row.get("period_start") is not None and start is None: return None
            if row.get("revenue") is not None or row.get("fields") != [] or not isinstance(row.get("reason"), str) or row["reason"] not in {"ambiguous_filing_context", "annual_evidence_unavailable"}: return None
            continue
        if start is None or not 300 <= (end-start).days <= 430: return None
        fields = row.get("fields")
        if row.get("status") != "available" or not isinstance(fields, list) or not 1 <= len(fields) <= 6:
            return None
        if not isinstance(row.get("form"), str) or row["form"] not in ANNUAL_FORMS or not isinstance(row.get("accession"), str) or re.fullmatch(r"\d{10}-\d{2}-\d{6}", row["accession"]) is None:
            return None
        if any(not isinstance(f, Mapping) for f in fields): return None
        counts = Counter(str(f.get("field")) for f in fields)
        revenue = None
        for field in fields:
            name = field.get("field")
            if not isinstance(name, str) or counts[name] != 1: return None
            accepted = REVENUE_CONCEPTS if name == "revenue" else OPERATING_COMPONENT_CONCEPTS.get(name, frozenset())
            field_concept = (field.get("taxonomy"), field.get("concept"))
            if not all(isinstance(x, str) for x in field_concept) or field_concept not in accepted:
                return None
            if field.get("rights_status") != "approved_field_scope_raw_redistribution_held" or field.get("unit") != "USD" or not _finite_direct_number(field.get("value")):
                return None
            if any(field.get(k) != val for k, val in (
                ("source_ref", history["source_url"]), ("observed_at_utc", history["observed_at"]),
                ("accession", row["accession"]), ("period_start", row["period_start"]), ("period_end", row["period_end"]),
            )): return None
            if name == "revenue":
                if field_concept != concept: return None
                revenue = field["value"]
        if revenue is None or not _finite_direct_number(row.get("revenue")) or row["revenue"] != revenue:
            return None
    return {**history, "comparisons": compare_annual_periods(periods)}
