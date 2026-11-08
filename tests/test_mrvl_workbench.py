"""The MRVL explanation uses the real refresh and compositor, with synthetic HTTP."""
from copy import deepcopy
import json

from streamlit.testing.v1 import AppTest


def install_sources(monkeypatch, *, failure=None, calls=None):
    from src import company_workbench_ui, online_sec_receipt, sec_exact_filing
    from tests.test_mrvl_earnings_sources import _facts_payload, _sources, MRVL_FACTS, AVGO_DOCUMENT
    sources = _sources()
    sources[MRVL_FACTS] = _facts_payload()
    sources['https://www.sec.gov/files/company_tickers.json'] = {'0': {'ticker':'MRVL', 'cik_str':1835632}}
    calls = [] if calls is None else calls
    def fetch(url, _agent):
        calls.append(url)
        if failure == 'peer_document' and url == AVGO_DOCUMENT:
            raise OSError('Synthetic unavailable document')
        body = sources[url]
        return (json.dumps(body).encode() if isinstance(body, dict) else body), {}, url
    monkeypatch.setattr(online_sec_receipt, '_fetch_raw', fetch)
    monkeypatch.setattr(sec_exact_filing, '_fetch_html', fetch)
    monkeypatch.setattr(company_workbench_ui, 'get_online_company_prices',
        lambda ticker,*args,**kwargs:dict(ticker=ticker,status='unavailable',reason='price_source_unavailable'))
    monkeypatch.setattr(company_workbench_ui, 'get_price_filing_association',
        lambda *args,**kwargs:dict(status='withheld',reason='price_evidence_unavailable'))
    monkeypatch.setattr(company_workbench_ui, 'get_online_peer_valuation',
        lambda ticker,*args,**kwargs:dict(ticker=ticker,status='withheld',reason='listing_classification_unavailable',
                                        subject=None,peers=[],excluded=[],peer_count=0))
    monkeypatch.setenv('SEC_USER_AGENT', 'Synthetic researcher contact@example.com')
    monkeypatch.delenv('COMMERCIAL_RESEARCH_MODE', raising=False)
    return calls


def app():
    import streamlit as st
    from src.company_workbench_ui import render_integrated_company
    render_integrated_company(st,'MRVL',profile_scope='constructed',saved_available=False,
        online_candidate=dict(cik='0001835632',title='Constructed MRVL case'),
        render_saved=lambda section:st.error('A saved model must not be loaded'),
        render_sources=lambda bundle:st.caption('Existing source panels remain available'))


def rendered(at):
    return '\n'.join(str(item.value) for item in at.markdown)


def load_review(monkeypatch, *, failure=None):
    calls = install_sources(monkeypatch, failure=failure)
    at = AppTest.from_function(app, default_timeout=30)
    at.query_params.update(section='valuation',ticker='MRVL',online='1')
    at.run()
    assert calls == [] and not at.exception
    at.button(key='company-refresh-all').click().run()
    assert not at.exception and len(calls) == 6
    return at, calls


def test_price_and_listing_failure_does_not_hide_loaded_annual_quality_or_peer_context(monkeypatch):
    at, calls = load_review(monkeypatch)
    assert 'mrvl-earnings-caution' in rendered(at)
    assert rendered(at).index('mrvl-earnings-caution') < rendered(at).index('aria-label="Online peer valuation"')
    assert 'Earnings quality behind annual P/E' in rendered(at)
    assert 'business-sale gain' in rendered(at) and 'direct competitor' in rendered(at)
    assert '90 days' in rendered(at) and '35-day' in rendered(at)
    assert 'Relative valuation withheld' in rendered(at)
    assert 'Saved Valuation & Scenarios' not in rendered(at)


def test_sources_and_overview_reuse_the_loaded_packet_without_refetch_or_cluttering_first_screen(monkeypatch):
    at, calls = load_review(monkeypatch); before = list(calls)
    at.radio[0].set_value('sources').run()
    assert not at.exception and 'MRVL earnings review sources' in rendered(at)
    assert 'GainLossOnSaleOfBusiness' in rendered(at) and calls == before
    at.radio[0].set_value('overview').run()
    assert not at.exception and 'Earnings quality behind annual P/E' not in rendered(at)
    at.radio[0].set_value('valuation').run()
    assert 'business-sale gain' in rendered(at) and calls == before


def test_peer_document_failure_preserves_quality_and_displays_named_relationship_gap(monkeypatch):
    at, calls = load_review(monkeypatch, failure='peer_document')
    assert 'business-sale gain' in rendered(at)
    assert 'AVGO comparison context remains incomplete' in rendered(at)
    assert 'direct competitor' not in rendered(at) and 'Synthetic unavailable document' not in rendered(at)


def test_presentation_does_not_mutate_financial_fields_or_saved_eligibility(monkeypatch):
    from src.company_sec_online_preview import SESSION_KEY
    at, calls = load_review(monkeypatch)
    snapshot = deepcopy(at.session_state[SESSION_KEY])
    at.radio[0].set_value('sources').run()
    assert not at.exception and at.session_state[SESSION_KEY] == snapshot
