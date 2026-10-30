"""Bounded annual history from one live Companyfacts response, entirely in memory."""

from __future__ import annotations

from collections import defaultdict
import re
from datetime import datetime, timezone
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


def fetch_sec_online_research_view(ticker: str, *, user_agent: str, ticker_map_receipt=None, source_fetcher=None, observed_at=None) -> dict[str, Any]:
    """Fetch Companyfacts once for independent annual and direct quarterly views."""
    from src.sec_fundamentals_preview import build_sec_fundamentals_preview
    from src.online_sec_receipt import fetch_sec_json_receipt
    from src.sec_quarterly_history import build_sec_quarterly_history

    captured = {}
    def fetch(url, agent, sleep):
        receipt=fetch_sec_json_receipt(url,user_agent=agent,fetcher=source_fetcher,observed_at=observed_at)
        if receipt['status']!='ready': raise RuntimeError('SEC facts receipt unavailable')
        captured['receipt']=receipt
        return receipt['payload']
    def fetch_map(url,agent,sleep):
        receipt=ticker_map_receipt if ticker_map_receipt is not None else fetch_sec_json_receipt(url,user_agent=agent,fetcher=source_fetcher,observed_at=observed_at)
        if not isinstance(receipt,Mapping) or receipt.get('status')!='ready' or receipt.get('source_url')!=url:
            raise RuntimeError('SEC ticker map receipt unavailable')
        payload=receipt.get('payload')
        if not isinstance(payload,Mapping) or not 1<=len(payload)<=100000: raise ValueError('Invalid SEC ticker map')
        aliases={ticker,ticker.replace('.','-'),ticker.replace('-','.')}
        ciks=set()
        for row in payload.values():
            if not isinstance(row,Mapping) or row.get('ticker') not in aliases: continue
            raw=row.get('cik_str')
            if type(raw) not in {int,str} or not re.fullmatch(r'\d{1,10}',str(raw)) or int(raw)==0:
                raise ValueError('Invalid mapped CIK')
            ciks.add(str(int(raw)).zfill(10))
        if len(ciks)>1: raise ValueError('Ambiguous SEC ticker association')
        captured['expected_cik']=next(iter(ciks)) if ciks else None
        captured['map_receipt']=receipt
        return payload
    options={}
    if observed_at is not None:
        if not isinstance(observed_at,datetime) or observed_at.utcoffset() is None: raise ValueError('Invalid SEC observation')
        options['retrieval_timestamp']=observed_at.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    preview = build_sec_fundamentals_preview(
        ticker, canonical_path=None, staged_path=None, user_agent=user_agent,
        companyfacts_fetcher=fetch, ticker_map_fetcher=fetch_map, **options,
    )
    view = present_company_sec_annual_preview(ticker, preview)
    receipt=captured.get('receipt'); cik=captured.get('expected_cik')
    if receipt and cik:
        payload=receipt['payload']; raw_cik=payload.get('cik')
        if type(raw_cik) not in {int,str} or not re.fullmatch(r'\d{1,10}',str(raw_cik)) or str(int(raw_cik)).zfill(10)!=cik:
            return {**view,'companyfacts_identity':{'status':'withheld','reason':'companyfacts_identity_mismatch'}}
        identity={k:receipt[k] for k in ('source_url','observed_at','source_last_modified','payload_sha256')}
        mapping=captured['map_receipt']
        identity.update(status='source_matched',ticker=ticker,sec_cik=cik,
                        association_source_url=mapping['source_url'],association_payload_sha256=mapping['payload_sha256'],
                        association_observed_at=mapping['observed_at'])
        view['companyfacts_identity']=identity
        if view['status']=='inspection_only':
            view['annual_history']=build_sec_annual_history(view,payload)
        anchor=next(((f['taxonomy'],f['concept']) for f in view.get('approved_direct_fields',[]) if f['field']=='revenue'),None)
        view['quarterly_history']=build_sec_quarterly_history(ticker,payload,expected_cik=cik,
            observed_at=receipt['observed_at'],source_url=receipt['source_url'],payload_sha256=receipt['payload_sha256'],anchor_concept=anchor)
        view['reported_period_anchors']=view['quarterly_history'].get('reported_period_anchors',{})
    return view
