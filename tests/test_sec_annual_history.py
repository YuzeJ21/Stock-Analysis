from copy import deepcopy

import pytest

from src.company_sec_online_preview import present_company_sec_annual_preview
from src.sec_fundamentals_preview import build_sec_fundamentals_preview


def _payload():
    facts = {}
    for concept, values in {
        "Revenues": [100, 120, 150], "OperatingIncomeLoss": [10, -5, 20],
        "NetCashProvidedByUsedInOperatingActivities": [20, 10, 30],
        "PaymentsToAcquirePropertyPlantAndEquipment": [5, 6, 7],
    }.items():
        facts[concept] = {"units": {"USD": [
            {"start": f"{year}-01-01", "end": f"{year}-12-31", "val": value,
             "filed": "2026-03-01", "form": "10-K", "accn": "0000001234-26-000001", "fy": 2025, "fp": "FY"}
            for year, value in zip([2023, 2024, 2025], values)
        ]}}
    return {"cik": 1234, "entityName": "Fictional Company", "facts": {"us-gaap": facts}}


def _view(payload=None):
    payload = _payload() if payload is None else payload
    preview = build_sec_fundamentals_preview(
        "FICT", canonical_path=None, staged_path=None,
        retrieval_timestamp="2026-10-30T12:00:00Z", user_agent="Research contact@example.com",
        ticker_map_fetcher=lambda *_: {"0": {"ticker": "FICT", "cik_str": 1234, "title": "Fictional"}},
        companyfacts_fetcher=lambda *_: payload,
    )
    return present_company_sec_annual_preview("FICT", preview)


def test_history_inspects_six_year_generic_path_without_network_or_csv(tmp_path, monkeypatch):
    from src.sec_annual_history import build_sec_annual_history
    import pandas as pd

    payload = _payload(); view = _view(payload)
    monkeypatch.setattr(pd, "read_csv", lambda *a, **kw: pytest.fail("history read a CSV"))
    history = build_sec_annual_history(view, payload)
    assert history["status"] == "inspection_only"
    assert [r["period_end"] for r in history["periods"]] == ["2023-12-31", "2024-12-31", "2025-12-31"]
    assert [r["revenue"] for r in history["periods"]] == [100, 120, 150]
    assert all(r["filed"] == "2026-03-01" for r in history["periods"])
    assert [r["direction"] for r in history["comparisons"]] == ["increased", "increased"]
    assert all(r["growth_rate"] is None for r in history["comparisons"])
    assert history["history_basis"] == "latest_reported_as_observed_not_point_in_time"
    assert not list(tmp_path.iterdir())


def test_conflicting_historical_fact_is_withheld_and_breaks_growth_comparison():
    from src.sec_annual_history import build_sec_annual_history

    payload = _payload(); records = payload["facts"]["us-gaap"]["Revenues"]["units"]["USD"]
    records.append({**records[1], "val": 999})
    result = build_sec_annual_history(_view(), payload)
    assert result["periods"][1]["status"] == "withheld"
    assert result["periods"][1]["revenue"] is None
    assert all(x["status"] == "withheld" for x in result["comparisons"])


def test_restatement_uses_latest_publication_without_claiming_historical_knowledge():
    from src.sec_annual_history import build_sec_annual_history

    payload = _payload(); records = payload["facts"]["us-gaap"]["Revenues"]["units"]["USD"]
    records.append({**records[1], "val": 110, "filed": "2025-03-01", "accn": "0000001234-25-000001"})
    result = build_sec_annual_history(_view(), payload)
    assert result["periods"][1]["revenue"] == 120
    assert result["periods"][1]["filed"] == "2026-03-01"
    assert "not_point_in_time" in result["history_basis"]


def test_two_latest_filing_contexts_are_not_arbitrarily_selected():
    from src.sec_annual_history import build_sec_annual_history

    payload = _payload(); records = payload["facts"]["us-gaap"]["Revenues"]["units"]["USD"]
    records.append({**records[1], "accn": "0000001234-26-000002", "val": 130})
    result = build_sec_annual_history(_view(), payload)
    assert result["periods"][1]["reason"] == "ambiguous_filing_context"


@pytest.mark.parametrize("change", ["currency", "gap", "overlap", "concept"])
def test_incomparable_prior_periods_do_not_create_growth_direction(change):
    from src.sec_annual_history import build_sec_annual_history

    payload = _payload(); facts = payload["facts"]["us-gaap"]; records = facts["Revenues"]["units"]["USD"]
    if change == "currency":
        facts["Revenues"]["units"]["EUR"] = [records.pop(1)]
    elif change == "gap": records.pop(1)
    elif change == "overlap": records[1]["start"] = "2023-12-01"
    else: facts["SalesRevenueNet"] = {"units": {"USD": [records.pop(1)]}}
    result = build_sec_annual_history(_view(), payload)
    assert not any(x["status"] == "comparable" for x in result["comparisons"])


def test_wrong_issuer_and_unreviewed_anchor_withhold_history():
    from src.sec_annual_history import build_sec_annual_history

    p = _payload(); p["cik"] = 9999
    assert build_sec_annual_history(_view(), p)["status"] == "withheld"
    view = _view(); view["approved_direct_fields"][0]["rights_status"] = "unreviewed"
    assert build_sec_annual_history(view, _payload())["status"] == "withheld"


def test_history_is_bounded_to_six_periods_and_never_changes_source_payload():
    from src.sec_annual_history import build_sec_annual_history

    p = _payload(); before = deepcopy(p)
    result = build_sec_annual_history(_view(), p, max_periods=2)
    assert len(result["periods"]) == 2
    assert p == before


def test_explicit_action_reuses_one_facts_response_and_rerenders_reuse_history(monkeypatch):
    import json
    from src.company_sec_online_preview import get_company_sec_annual_preview
    from src import online_sec_receipt

    calls = []
    def fetch(url, *_args):
        calls.append(url)
        payload=_payload() if 'companyfacts/' in url else {"0": {"ticker": "FICT", "cik_str": 1234}}
        return json.dumps(payload).encode(),{},url
    monkeypatch.setattr(online_sec_receipt, "_fetch_raw", fetch)
    session = {}
    view = get_company_sec_annual_preview("FICT", session, refresh_requested=True, user_agent="Research contact")
    assert len(view["annual_history"]["periods"]) == 3
    assert len(calls) == 2

    cached = get_company_sec_annual_preview("FICT", session, refresh_requested=False, user_agent="Research contact")
    assert cached["annual_history"] == view["annual_history"]
    assert len(calls) == 2


def test_reporting_hole_is_not_adjacent_even_if_both_durations_are_annual():
    from src.online_history_contract import compare_annual_periods
    result = compare_annual_periods([
        {"period_start": "2024-01-01", "period_end": "2024-12-31", "status": "available", "revenue": 100},
        {"period_start": "2025-02-01", "period_end": "2026-01-31", "status": "available", "revenue": 120},
    ])
    assert result[0]["status"] == "withheld"


def test_competing_starts_emit_one_withheld_year_and_preserve_valid_siblings():
    from src.sec_annual_history import build_sec_annual_history
    from src.online_history_contract import validated_annual_history
    p = _payload(); records = p["facts"]["us-gaap"]["Revenues"]["units"]["USD"]
    records.append({**records[1], "start": "2024-01-02"})
    view = _view(); view["annual_history"] = build_sec_annual_history(view, p)
    h = validated_annual_history(view)
    assert h is not None
    assert len(h["periods"]) == 3
    assert [r["status"] for r in h["periods"]] == ["available", "withheld", "available"]


def test_history_does_not_retain_a_preview_builder_replaced_during_import(monkeypatch):
    """A temporary preview adapter must not become a permanent history dependency."""
    import importlib
    from src import sec_annual_history, sec_fundamentals_preview

    def temporary_builder(*_args, **_kwargs):
        pytest.fail("history retained a revoked preview adapter")

    try:
        with monkeypatch.context() as patch:
            patch.setattr(sec_fundamentals_preview, "build_sec_fundamentals_preview", temporary_builder)
            importlib.reload(sec_annual_history)
        result = sec_annual_history.build_sec_annual_history(_view(), _payload())
        assert [row["revenue"] for row in result["periods"]] == [100, 120, 150]
    finally:
        importlib.reload(sec_annual_history)


def test_mrvl_financial_action_attaches_independent_review_once_and_cached_reads_do_not_fetch(monkeypatch):
    from test_mrvl_earnings_sources import _facts_payload, _sources, MRVL_FACTS
    from src.company_sec_online_preview import get_company_sec_annual_preview
    from src import online_sec_receipt, sec_exact_filing
    import json

    monkeypatch.delenv('COMMERCIAL_RESEARCH_MODE', raising=False)
    sources = _sources()
    sources[MRVL_FACTS] = _facts_payload()
    sources['https://www.sec.gov/files/company_tickers.json'] = {'0': {'ticker': 'MRVL', 'cik_str': 1835632}}
    calls = []
    def fetch(url, _agent):
        calls.append(url)
        body = sources[url]
        return json.dumps(body).encode() if isinstance(body, dict) else body, {}, url
    monkeypatch.setattr(online_sec_receipt, '_fetch_raw', fetch)
    monkeypatch.setattr(sec_exact_filing, '_fetch_html', fetch)
    session = {}
    view = get_company_sec_annual_preview('MRVL', session, refresh_requested=True, user_agent='Research contact')
    assert view['mrvl_earnings_review']['facts']['status'] == 'ready'
    assert view['annual_history']['periods'][0]['revenue'] == 1000
    assert {row['field'] for row in view['approved_direct_fields']} == {
        'revenue', 'filing_dates', 'operating_income', 'cash_from_operations', 'capital_expenditures',
    }
    assert len(calls) == 6
    assert calls.count(MRVL_FACTS) == 1
    before = list(calls)
    cached = get_company_sec_annual_preview('MRVL', session, refresh_requested=False, user_agent='Research contact')
    assert cached['mrvl_earnings_review'] == view['mrvl_earnings_review']
    assert cached['approved_direct_fields'] == view['approved_direct_fields']
    assert calls == before


def test_mrvl_failed_peer_document_retains_annual_history_and_approved_scope(monkeypatch):
    from test_mrvl_earnings_sources import _facts_payload, _sources, NOW, MRVL_FACTS, AVGO_DOCUMENT
    from src.sec_annual_history import fetch_sec_online_research_view
    import json

    monkeypatch.delenv('COMMERCIAL_RESEARCH_MODE', raising=False)
    sources = _sources()
    sources[MRVL_FACTS] = _facts_payload()
    sources['https://www.sec.gov/files/company_tickers.json'] = {'0': {'ticker': 'MRVL', 'cik_str': 1835632}}
    calls = []
    def fetch(url, _agent):
        calls.append(url)
        if url == AVGO_DOCUMENT:
            raise OSError('private unreachable host detail')
        body = sources[url]
        return json.dumps(body).encode() if isinstance(body, dict) else body, {}, url
    view = fetch_sec_online_research_view('MRVL', user_agent='Research contact', source_fetcher=fetch, observed_at=NOW)
    review = view['mrvl_earnings_review']
    assert len(calls) == 6
    assert review['facts']['status'] == review['documents']['MRVL']['status'] == 'ready'
    assert review['documents']['AVGO']['status'] == 'unavailable'
    assert view['status'] == 'inspection_only'
    assert view['annual_history']['periods'][0]['revenue'] == 1000
    assert {row['field'] for row in view['approved_direct_fields']} == {
        'revenue', 'filing_dates', 'operating_income', 'cash_from_operations', 'capital_expenditures',
    }
    assert 'private unreachable host detail' not in json.dumps(view)


@pytest.mark.parametrize('change', ['wrong_cik', 'non_mrvl', 'commercial', 'invalid_mode'])
def test_financial_identity_and_mode_guards_prevent_mrvl_source_requests(monkeypatch, change):
    from test_mrvl_earnings_sources import _facts_payload, NOW, MRVL_FACTS
    from src.sec_annual_history import fetch_sec_online_research_view
    import json

    monkeypatch.delenv('COMMERCIAL_RESEARCH_MODE', raising=False)
    ticker, cik = ('FICT', 1234) if change == 'non_mrvl' else ('MRVL', 1835632)
    if change in {'commercial', 'invalid_mode'}:
        monkeypatch.setenv('COMMERCIAL_RESEARCH_MODE', '1' if change == 'commercial' else 'invalid')
    payload = _payload() if ticker == 'FICT' else _facts_payload()
    if change == 'wrong_cik': payload['cik'] = 9999
    calls = []
    def fetch(url, _agent):
        calls.append(url)
        body = payload if 'companyfacts/' in url else {'0': {'ticker': ticker, 'cik_str': cik}}
        return json.dumps(body).encode(), {}, url
    view = fetch_sec_online_research_view(ticker, user_agent='Research contact', source_fetcher=fetch, observed_at=NOW)
    assert len(calls) == 2
    assert not any('/submissions/' in url or '/Archives/' in url for url in calls)
    if change in {'wrong_cik', 'non_mrvl'}:
        assert 'mrvl_earnings_review' not in view
    else:
        assert view['mrvl_earnings_review']['reason']
