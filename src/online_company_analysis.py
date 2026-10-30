"""Descriptive annual research from approved direct SEC facts, without saved inputs.

No ratio, forecast, free-cash-flow value, ranking, or valuation is produced.
Each observation retains the fields that support it; absent evidence is withheld.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from datetime import date, datetime, timedelta
from html import escape
from typing import Any, Mapping

from src.company_sec_online_preview import (
    ANNUAL_FORMS, OPERATING_COMPONENT_CONCEPTS, REVENUE_CONCEPTS,
)


def _date(value: object) -> date | None:
    try:
        return date.fromisoformat(value) if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) else None
    except ValueError:
        return None


def _observed(value: object) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else None
    except ValueError:
        return None
    return parsed if parsed is not None and parsed.utcoffset() == timedelta(0) else None


def _number(value: object) -> bool:
    try:
        return type(value) in {int, float} and math.isfinite(value) and abs(value) <= 1e20
    except OverflowError:
        return False


def build_online_company_analysis(view: Mapping[str, Any]) -> dict[str, Any]:
    """Assess generic annual capabilities; never infer a missing field or identity."""
    empty = {"status": "withheld", "findings": [], "lanes": [], "derived_numeric_values": {}}
    if not isinstance(view, Mapping):
        return empty
    if view.get("status") == "not_requested":
        return {**empty, "status": "not_requested"}
    ticker, cik = view.get("ticker"), view.get("sec_cik")
    source = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    end, filed, observed = _date(view.get("period_end")), _date(view.get("filing_date")), _observed(view.get("retrieved_at_utc"))
    fields = view.get("approved_direct_fields")
    if (
        view.get("status") != "inspection_only" or view.get("safe_to_apply") is not False
        or not isinstance(ticker, str) or re.fullmatch(r"[A-Z0-9][A-Z0-9.-]{0,19}", ticker) is None
        or not isinstance(cik, str) or re.fullmatch(r"\d{10}", cik) is None
        or view.get("source_url") != source or not isinstance(view.get("annual_form"), str)
        or view["annual_form"] not in ANNUAL_FORMS
        or not isinstance(view.get("accession"), str)
        or re.fullmatch(r"\d{10}-\d{2}-\d{6}", view["accession"]) is None
        or end is None or filed is None or observed is None or not end <= filed <= observed.date()
        or not isinstance(fields, list) or len(fields) > 32
        or any(not isinstance(row, Mapping) for row in fields)
    ):
        return empty
    counts = Counter(str(row.get("field")) for row in fields)

    def eligible(row: Mapping[str, Any], start: str | None = None) -> bool:
        name = row.get("field")
        if not all(isinstance(row.get(key), str) for key in ("field", "taxonomy", "concept")):
            return False
        concepts = REVENUE_CONCEPTS if name == "revenue" else OPERATING_COMPONENT_CONCEPTS.get(name, frozenset())
        begin = _date(row.get("period_start"))
        return bool(
            counts[str(name)] == 1 and (row.get("taxonomy"), row.get("concept")) in concepts
            and row.get("rights_status") == "approved_field_scope_raw_redistribution_held"
            and row.get("unit") == "USD" and _number(row.get("value"))
            and row.get("source_ref") == source and row.get("accession") == view["accession"]
            and row.get("period_end") == view["period_end"]
            and row.get("observed_at_utc") == view["retrieved_at_utc"]
            and begin is not None and 300 <= (end - begin).days <= 430
            and (start is None or row.get("period_start") == start)
            and (name != "capital_expenditures" or row["value"] >= 0)
        )

    revenue = next((row for row in fields if row.get("field") == "revenue" and eligible(row)), None)
    if revenue is None:
        return empty
    approved = {
        str(row["field"]): row for row in fields
        if eligible(row, str(revenue["period_start"]))
    }
    from src.online_history_contract import validated_annual_history
    history = validated_annual_history(view)
    has_history = bool(history and any(x["status"] == "comparable" for x in history["comparisons"]))
    findings = [{
        "key": "revenue_anchor", "title": "Historical revenue comparison available" if has_history else "Revenue available; growth history incomplete",
        "detail": "Comparable direct annual revenues and their observed filing history appear below. Percentage growth retains its own field-scope gate." if has_history else "Annual revenue is available for this period. A growth conclusion needs a separately validated prior year.",
        "source_fields": ["revenue"],
    }]
    operating = approved.get("operating_income")
    cash, capex = approved.get("cash_from_operations"), approved.get("capital_expenditures")
    if operating is not None:
        findings.append({
            "key": "operating_result",
            "title": "Operating profit reported" if operating["value"] > 0 else "Operating loss reported" if operating["value"] < 0 else "Operating result was zero",
            "detail": "This describes the filed operating result for the selected annual period; net income, margins and valuation require their own evidence.",
            "source_fields": ["operating_income"],
        })
    if cash is not None:
        continuing = cash["concept"] == "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"
        scope = "Continuing operating activities" if continuing else "Operating activities"
        title = (
            f"{scope} generated cash" if cash["value"] > 0
            else f"{scope} used cash" if cash["value"] < 0
            else "Continuing operating cash flow was zero" if continuing
            else "Operating cash flow was zero"
        )
        contrast = bool(not continuing and operating is not None and operating["value"] > 0 and cash["value"] < 0)
        if continuing:
            detail = "This figure covers continuing operations only. It does not establish total operating cash flow or a comparable cash-flow/PP&E-spending relationship."
        elif contrast:
            detail = "Operating profit and operating cash outflow coexist in this period. Review working-capital movements and non-cash adjustments in the filing before explaining the difference."
        elif cash["value"] < 0:
            detail = "Operating activities used cash during this annual period. Review the cash-flow reconciliation and working-capital movements before assigning a cause."
        elif cash["value"] == 0:
            detail = "The filing reports no net operating cash flow for this annual period. This is a reported zero, not a missing input."
        else:
            detail = "Cash flow and accounting profit answer different questions; a cash inflow alone does not establish earnings quality or future cash generation."
        findings.append({
            "key": "operating_cash", "title": title, "detail": detail,
            "source_fields": ["cash_from_operations"] + (["operating_income"] if contrast else []),
        })
    cash_spend_comparable = bool(
        cash is not None and capex is not None
        and cash["concept"] == "NetCashProvidedByUsedInOperatingActivities"
        and capex["concept"] == "PaymentsToAcquirePropertyPlantAndEquipment"
    )
    if cash_spend_comparable:
        title = (
            "Operating cash outflow alongside PP&E spending" if cash["value"] < 0
            else "Operating cash flow exceeds reported PP&E spending" if cash["value"] > capex["value"]
            else "Reported PP&E spending exceeds operating cash flow" if cash["value"] < capex["value"]
            else "Operating cash flow equals reported PP&E spending"
        )
        findings.append({
            "key": "cash_spend_relation", "title": title,
            "detail": "This compares two direct amounts from the same annual period and filing. It is not issuer-defined free cash flow; acquisitions, other investment and financing needs are outside this comparison.",
            "source_fields": ["cash_from_operations", "capital_expenditures"],
        })
    lanes = [
        {"key": key, "label": label, "status": "available" if available else "withheld", "reason": reason}
        for key, label, available, reason in (
            ("operating", "Operating result", operating is not None, "Requires matching approved operating income."),
            ("cash", "Operating cash flow", cash is not None, "Requires matching approved operating cash flow."),
            ("investment", "Cash flow / PP&E spending", cash_spend_comparable, "Requires total operating cash flow and PP&E spending with aligned source, period and component definitions."),
            ("growth", "Percentage growth", False, "Comparable annual revenue direction appears in historical review when supported; a numeric growth rate requires registered derived-field scope."),
            ("prices", "Price input for valuation", False, "Personal price history is inspected separately; issuer identity, adjustment basis and commercial scope must be reviewed before reuse."),
            ("valuation", "Valuation and scenarios", False, "Requires price, share basis, approved cash-flow definitions and explicit assumptions."),
            ("peers", "Peer comparison", False, "Requires reviewed relationships and comparable peer periods and definitions."),
            ("forecasts", "Forecasts and consensus", False, "Requires permitted point-in-time consensus and validated historical inputs."),
        )
    ]
    return {
        "status": "inspection_only", "ticker": ticker, "period_start": revenue["period_start"],
        "period_end": view["period_end"], "filing_date": view["filing_date"],
        "accession": view["accession"], "source_url": source,
        "findings": findings, "lanes": lanes, "derived_numeric_values": {},
    }


def online_company_analysis_html(analysis: Mapping[str, Any]) -> str:
    if analysis.get("status") == "not_requested":
        return ""
    if analysis.get("status") != "inspection_only":
        return '<section class="online-financial-review"><h3>Online financial review</h3><p>Withheld: a validated annual revenue anchor and compatible direct facts are required. Missing or unsupported reporting definitions stay unavailable.</p></section>'
    field_labels = {
        "revenue": "Revenue", "operating_income": "Operating income",
        "cash_from_operations": "Operating cash flow", "capital_expenditures": "PP&E spending",
    }
    findings = "".join(
        f'<article><h4>{escape(row["title"])}</h4><p>{escape(row["detail"])}</p>'
        f'<small>Evidence: {escape(", ".join(field_labels[key] for key in row["source_fields"]))}</small></article>'
        for row in analysis["findings"]
    )
    lanes = "".join(
        f'<div><strong>{escape(row["label"])}</strong><span>{"Available for this period" if row["status"] == "available" else "Withheld · " + escape(row["reason"])}</span></div>'
        for row in analysis["lanes"]
    )
    return (
        '<style>.online-financial-review{border:1px solid #d9e0dc;border-radius:8px;padding:16px;overflow-wrap:anywhere;min-width:0}'
        '.online-financial-findings{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,28rem),1fr));gap:16px}'
        '.online-financial-findings article{padding:12px;border:1px solid #d9e0dc;border-radius:8px;background:#fff}'
        '.online-financial-review article,.online-financial-review details{min-width:0}.online-financial-review h4{font-size:1rem;margin:0 0 8px}'
        '.online-financial-review p{line-height:1.5}.online-financial-review small{color:#52615c}'
        '.online-financial-lanes>div{display:grid;gap:4px;padding:10px 0;border-bottom:1px solid #d9e0dc}'
        '.online-financial-lanes span{font-size:.85rem}</style>'
        '<section class="online-financial-review" aria-label="Online financial review">'
        '<h3>Online financial review</h3>'
        f'<p>{escape(analysis["ticker"])} · annual period {escape(analysis["period_start"])} to {escape(analysis["period_end"])} · filed {escape(analysis["filing_date"])}.</p>'
        f'<div class="online-financial-findings">{findings}</div>'
        '<details><summary>Available analysis and remaining inputs</summary>'
        f'<div class="online-financial-lanes">{lanes}</div></details>'
        '<p>Descriptive filing research only. No score, forecast, valuation or derived numeric field is generated. Exact field evidence follows below.</p></section>'
    )
