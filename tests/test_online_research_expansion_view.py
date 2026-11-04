import pytest

from test_sec_quarterly_history import _build, _wrapped
from test_online_company_identity import _inputs
from test_online_research_coverage import _observation


def _views():
    from src.online_research_coverage import summarize_online_research_coverage
    from src.online_company_identity import build_price_filing_association
    from src.online_research_expansion_view import quarterly_history_html,price_filing_association_html,coverage_study_html
    i,prices,profile=_inputs()
    return (quarterly_history_html(_wrapped(_build())),
            price_filing_association_html(build_price_filing_association('FICT',i,prices,profile)),
            coverage_study_html(summarize_online_research_coverage([_observation()],['FICT','MISSING'])))


def test_quarter_view_distinguishes_reported_quarters_from_cumulative_cash_and_no_derived_q4():
    quarter,identity,coverage=_views()
    assert 'Reported quarterly financials' in quarter
    assert 'Cumulative cash flow' in quarter and '2025-01-01 to 2025-06-30' in quarter
    assert 'not point-in-time' in quarter and 'No missing quarter is inferred' in quarter
    assert '2025-12-31' not in quarter
    assert 'Listing association matched' in identity and 'vendor issuer identifier' in identity
    assert 'not a market-wide' in coverage and '2 requested' in coverage
    assert 'MISSING' in coverage


def test_malformed_quarter_evidence_is_withheld_before_rendering():
    from src.online_research_expansion_view import quarterly_history_html
    view=_wrapped(_build()); view['quarterly_history']['periods'][0]['fields']['revenue']['value']=True
    html=quarterly_history_html(view)
    assert '<svg' not in html and '<article' not in html


def test_tampered_identity_and_coverage_counters_cannot_be_presented_as_verified():
    from src.online_company_identity import build_price_filing_association
    from src.online_research_coverage import summarize_online_research_coverage
    from src.online_research_expansion_view import price_filing_association_html,coverage_study_html
    i,prices,p=_inputs(); link=build_price_filing_association('FICT',i,prices,p)
    link['sec_cik']='0000009999'
    assert 'Listing association matched' not in price_filing_association_html(link)
    coverage=summarize_online_research_coverage([_observation()],['FICT'])
    coverage['counts']['quarterly_revenue']=999
    assert '999' not in coverage_study_html(coverage)


def test_quarter_revenue_definition_is_visible_beside_customer_contract_values():
    from test_sec_quarterly_history import _quarter_payload
    from src.online_research_expansion_view import quarterly_history_html
    p=_quarter_payload(); p['facts']['us-gaap']['RevenueFromContractWithCustomerExcludingAssessedTax']=p['facts']['us-gaap'].pop('Revenues')
    html=quarterly_history_html(_wrapped(_build(p)))
    assert 'Revenue · customer contracts, excluding assessed tax' in html


def test_component_revision_hold_and_publication_date_are_visible_without_the_old_value():
    from test_sec_quarterly_history import _quarter_payload
    from src.online_research_expansion_view import quarterly_history_html
    p=_quarter_payload(); rows=p['facts']['us-gaap']['OperatingIncomeLoss']['units']['USD']
    rows.append({**rows[-1],'val':999,'filed':'2026-03-01','accn':'0000001234-26-000003'})
    html=quarterly_history_html(_wrapped(_build(p)))
    assert '<dt>Operating income</dt><dd>Withheld</dd>' in html
    assert 'Revision context holds' in html and '2026-03-01' in html


def test_expansion_sections_survive_real_streamlit_composition_and_reflow(tmp_path):
    from playwright.sync_api import sync_playwright
    from src.public_performance_gate import _local_demo_server
    from src.online_company_analysis import online_company_analysis_html,build_online_company_analysis
    from test_sec_annual_history import _view
    from src.online_research_history_view import online_price_history_html
    _,prices,_=_inputs()
    quarter,identity,coverage=_views()
    html=online_company_analysis_html(build_online_company_analysis(_view()))+quarter+online_price_history_html(prices)+identity+coverage
    (tmp_path/'src').mkdir()
    (tmp_path/'src/dashboard.py').write_text('import streamlit as st\nst.markdown('+repr(html)+',unsafe_allow_html=True)\n')
    with _local_demo_server(tmp_path,timeout_seconds=30) as base:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            page=browser.new_page()
            page.goto(base,wait_until='domcontentloaded')
            page.get_by_role('region',name='Reported quarterly financials',exact=True).wait_for(timeout=15000)
            for width,height in [(1280,900),(390,844),(195,422)]:
                page.set_viewport_size({'width':width,'height':height})
                for region in ['Reported quarterly financials','Price and filing identity','Cross-industry coverage']:
                    assert page.get_by_role('region',name=region,exact=True).count()==1
                sizes=page.evaluate("() => [...document.querySelectorAll('.online-quarterly,.online-quarterly article,.online-identity,.online-coverage,.online-coverage article')].map(x=>[x.clientWidth,x.scrollWidth])")
                assert all(a==b for a,b in sizes)
            browser.close()


def test_candidate_cik_mismatch_removes_quarter_and_identity_evidence_from_session(monkeypatch):
    from types import SimpleNamespace
    from src import dashboard
    from src.company_sec_online_preview import SESSION_KEY
    from test_online_company_identity import _identity
    class Box:
        def __enter__(self): return self
        def __exit__(self,*a): return False
        def markdown(self,*a,**kw): pass
    view=_wrapped(_build()); view.update(status='unavailable',safe_to_apply=False)
    view['companyfacts_identity']=_identity()
    state={SESSION_KEY:{'ticker':'FICT','view':view}}
    monkeypatch.setattr(dashboard,'st',SimpleNamespace(session_state=state,container=lambda **kw:Box(),empty=Box,button=lambda *a,**kw:False))
    monkeypatch.setattr(dashboard,'get_company_sec_annual_preview',lambda *a,**kw:view)
    dashboard.render_company_sec_annual_check('FICT',expected_cik='0000009999')
    assert 'companyfacts_identity' not in state[SESSION_KEY]['view']
    assert 'quarterly_history' not in state[SESSION_KEY]['view']


def test_explicit_sec_action_can_complete_identity_after_prices_were_loaded_first(monkeypatch):
    from types import SimpleNamespace
    from src import dashboard
    from src.company_sec_online_preview import SESSION_KEY as FINANCIAL_KEY
    from src.online_company_prices import SESSION_KEY as PRICE_KEY
    from src.online_company_identity import get_price_filing_association
    from test_online_company_identity import _profile_fetch
    from test_online_company_prices import OBSERVED
    class Box:
        def __enter__(self): return self
        def __exit__(self,*a): return False
    i,prices,p=_inputs(); state={FINANCIAL_KEY:{'ticker':'FICT','view':{'companyfacts_identity':i}},PRICE_KEY:prices}
    calls=[]; rendered=[]
    def fetch(url,agent): calls.append(url); return _profile_fetch()(url,agent)
    monkeypatch.setattr(dashboard,'st',SimpleNamespace(session_state=state,container=lambda **kw:Box(),button=lambda *a,**kw:False,markdown=lambda value,**kw:rendered.append(value)))
    monkeypatch.setattr(dashboard,'get_price_filing_association',lambda *a,**kw:get_price_filing_association(*a,**kw,fetcher=fetch,observed_at=OBSERVED))
    dashboard.render_company_online_prices('FICT',sec_refresh_requested=True)
    assert len(calls)==1 and 'Listing association matched' in ''.join(rendered)
    dashboard.render_company_online_prices('FICT',sec_refresh_requested=False)
    assert len(calls)==1


@pytest.mark.parametrize('concept,label', [
    ('RevenuesNetOfInterestExpense','Revenue · net of interest expense'),
    ('RegulatedAndUnregulatedOperatingRevenue','Revenue · regulated and unregulated operations'),
    ('RevenueFromContractWithCustomerIncludingAssessedTax','Revenue · customer contracts, including assessed tax'),
])
def test_bank_and_utility_source_definition_is_visible_next_to_values(concept,label):
    from test_sec_quarterly_history import _quarter_payload
    from src.online_research_expansion_view import quarterly_history_html
    p=_quarter_payload(); p['facts']['us-gaap'][concept]=p['facts']['us-gaap'].pop('Revenues')
    assert label in quarterly_history_html(_wrapped(_build(p)))
