"""Bounded annual history from one live Companyfacts response, entirely in memory."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping

from src.company_sec_online_preview import ANNUAL_FORMS, REVENUE_CONCEPTS, present_company_sec_annual_preview
from src.online_company_analysis import _date, _observed, build_online_company_analysis
from src.sec_fundamentals_preview import _valid_companyfacts_payload
from src.online_history_contract import compare_annual_periods


def build_sec_annual_history(
    view: Mapping[str, Any], payload: Mapping[str, Any], *, max_periods: int = 6,
) -> dict[str, Any]:
    """Use one concept, latest publication per period; this is not PIT history."""
    from src.sec_fundamentals_preview import build_sec_fundamentals_preview

    held = {"status": "withheld", "periods": [], "comparisons": []}
    if type(max_periods) is not int or max_periods < 1:
        return held
    if build_online_company_analysis(view)["status"] != "inspection_only" or not _valid_companyfacts_payload(payload):
        return held
    cik = str(payload.get("cik", ""))
    if not cik.isdigit() or str(int(cik)).zfill(10) != view["sec_cik"]:
        return held
    revenue = next(x for x in view["approved_direct_fields"] if x["field"] == "revenue")
    taxonomy, concept = revenue["taxonomy"], revenue["concept"]
    observed = _observed(view["retrieved_at_utc"])
    records = payload["facts"].get(taxonomy, {}).get(concept, {}).get("units", {}).get("USD", [])
    groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for raw in records:
        start, end, filed = _date(raw.get("start")), _date(raw.get("end")), _date(raw.get("filed"))
        if (
            start is not None and end is not None and filed is not None
            and 300 <= (end - start).days <= 430 and end <= filed <= observed.date()
            and end <= _date(view["period_end"])
            and isinstance(raw.get("form"), str) and raw["form"] in ANNUAL_FORMS
            and isinstance(raw.get("accn"), str)
        ):
            groups[raw["end"]].append(raw)
    periods = []
    for end, candidates in sorted(groups.items())[-min(max_periods, 6):]:
        starts = {r["start"] for r in candidates}
        start = next(iter(starts)) if len(starts) == 1 else None
        latest_date = max(raw["filed"] for raw in candidates)
        contexts = {(r["accn"], r["form"]) for r in candidates if r["filed"] == latest_date}
        row = {"period_start": start, "period_end": end, "filed": latest_date,
               "status": "withheld", "revenue": None, "fields": [], "reason": "annual_evidence_unavailable"}
        if len(contexts) != 1 or len(starts) != 1:
            row["reason"] = "ambiguous_filing_context"
            periods.append(row)
            continue
        accession, form = next(iter(contexts))
        filtered: dict[str, Any] = {"cik": payload["cik"], "entityName": payload.get("entityName"), "facts": {}}
        for tax, concepts in payload["facts"].items():
            selected = {}
            for name, fact in concepts.items():
                # A trend never silently stitches alternative revenue definitions.
                if tax == taxonomy and name != concept and (tax, name) in REVENUE_CONCEPTS:
                    continue
                units = {}
                for unit, items in fact["units"].items():
                    matching = [r for r in items if r.get("accn") == accession and r.get("form") == form
                                and r.get("filed") == latest_date and r.get("end") == end
                                and r.get("start") in (None, start)]
                    if matching:
                        units[unit] = matching
                if units:
                    selected[name] = {"units": units}
            if selected:
                filtered["facts"][tax] = selected
        preview = build_sec_fundamentals_preview(
            view["ticker"], canonical_path=None, staged_path=None,
            retrieval_timestamp=view["retrieved_at_utc"], user_agent="in-memory-replay",
            ticker_map_fetcher=lambda *_: {"0": {"ticker": view["ticker"], "cik_str": int(cik)}},
            companyfacts_fetcher=lambda *_: filtered,
        )
        period_view = present_company_sec_annual_preview(view["ticker"], preview)
        direct = [r for r in period_view.get("approved_direct_fields", []) if r["field"] in {
            "revenue", "operating_income", "cash_from_operations", "capital_expenditures"
        }]
        anchor = next((r for r in direct if r["field"] == "revenue" and r["concept"] == concept and r["taxonomy"] == taxonomy), None)
        if anchor is not None:
            row.update({"status": "available", "revenue": anchor["value"], "fields": direct,
                        "accession": accession, "form": form, "reason": None})
        periods.append(row)
    comparisons = compare_annual_periods(periods)
    return {
        "status": "inspection_only" if periods else "withheld", "ticker": view["ticker"],
        "sec_cik": view["sec_cik"], "source_url": view["source_url"],
        "observed_at": view["retrieved_at_utc"], "taxonomy": taxonomy, "concept": concept, "unit": "USD",
        "history_basis": "latest_reported_as_observed_not_point_in_time",
        "periods": periods, "comparisons": comparisons,
    }


def fetch_sec_online_research_view(ticker: str, *, user_agent: str) -> dict[str, Any]:
    """Fetch Companyfacts once for both the selected annual view and its history."""
    from src.providers.sec_companyfacts import _fetch_json
    from src.sec_fundamentals_preview import build_sec_fundamentals_preview

    captured = {}
    def fetch(url, agent, sleep):
        captured["payload"] = _fetch_json(url, agent, sleep)
        return captured["payload"]
    preview = build_sec_fundamentals_preview(
        ticker, canonical_path=None, staged_path=None, user_agent=user_agent,
        companyfacts_fetcher=fetch,
    )
    view = present_company_sec_annual_preview(ticker, preview)
    if view["status"] == "inspection_only" and "payload" in captured:
        view["annual_history"] = build_sec_annual_history(view, captured["payload"])
    return view
