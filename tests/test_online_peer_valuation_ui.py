from copy import deepcopy
from datetime import timedelta
import re

import pytest
from streamlit.testing.v1 import AppTest

from test_online_peer_valuation import build,collection,NOW
from test_online_peer_sources import source_dependencies


@pytest.mark.parametrize('sources_only',[False,True])
def test_peer_valuation_renders_english_with_method_and_source_boundaries(sources_only):
    from src.online_peer_valuation_ui import online_peer_valuation_html
    html=online_peer_valuation_html(build(),sources_only=sources_only)
    assert not re.search(r'[\u3400-\u9fff]',html)
    assert 'annual diluted p/e' in html.lower()
    assert 'USD/shares' in html and '2025-12-31' in html
    assert 'personal research' in html.lower()


def test_unknown_peer_reason_uses_clear_english_withheld_fallback():
    from src.online_peer_valuation_ui import _reason
    assert _reason('new_unknown_reason') == 'Source, identity, or field evidence could not be verified. This input is withheld.'


def test_online_answer_leads_with_metric_qualified_difference_and_actual_source_dates():
    from src.online_peer_valuation_ui import online_peer_valuation_html
    view=build();before=deepcopy(view);html=online_peer_valuation_html(view)
    assert 'Annual P/E is 20.0% above the industry reference median' in html and '30.0×' in html and '25.0×' in html
    assert 'not TTM or forecast' in html and '35 days' in html and 'automatically screened' in html
    assert '2026-10-30' in html and '2025-01-01' in html and '2025-12-31' in html
    summary = html.split('View actual fiscal periods, prices, and sources', 1)[0]
    assert 'Same-day close ÷ reported annual diluted EPS' in summary
    assert 'Selected company 30.0× ÷ reference median 25.0× − 1' in summary
    assert all(peer['ticker'] in summary for peer in view['peers'])
    assert 'EarningsPerShareDiluted' in html and 'USD/shares' in html and '2026-02-01' in html
    assert 'not an undervalued or overvalued conclusion' in html and '<h1' not in html
    assert 'SEC EPS fact' in html and 'https://data.sec.gov/' in html and view==before


@pytest.mark.parametrize('price,phrase',[(20,'20.0% below the industry reference median'),(25,'Annual P/E equals the industry reference median')])
def test_lower_and_equal_comparisons_use_plain_qualified_language(price,phrase):
    from src.online_peer_valuation_ui import online_peer_valuation_html
    from test_online_peer_valuation import rehash_vendor
    c=collection();r=c['issuers'][0];r['vendor']['payload']['info']['regularMarketPrice']=price
    r['prices']['bars'][-1]['close']=price;rehash_vendor(r)
    assert phrase in online_peer_valuation_html(build(c))


def test_thin_group_keeps_count_reasons_and_source_links_without_a_premium():
    from src.online_peer_valuation_ui import online_peer_valuation_html
    c=collection();c['issuers'][1]['facts']['payload']['facts']['us-gaap']['EarningsPerShareDiluted']['units']['USD/shares'][0]['val']=-1
    html=online_peer_valuation_html(build(c))
    assert 'Relative valuation withheld' in html and '2 companies' in html and 'At least 3' in html
    assert 'FA' in html and 'negative' in html and '20.0%' not in html
    summary = html.split('View actual fiscal periods, prices, and sources', 1)[0]
    assert 'Excluded reference companies and reasons (1)' in summary and 'FA' in summary
    assert 'How the difference is calculated' not in summary


def test_blocked_subject_does_not_present_unassessed_references_as_zero_results():
    from src.online_peer_valuation_ui import online_peer_valuation_html
    c=collection();c['issuers'][0]['facts']['payload']['facts']['us-gaap']['EarningsPerShareDiluted']['units']['USD/shares'][0]['val']=-1
    view=build(c);assert view['subject'] is None
    html=online_peer_valuation_html(view)
    assert '<dd>Not assessed</dd>' in html
    assert '<dd>0 companies</dd>' not in html and 'Currently 0 qualify' not in html


def test_amended_annual_gap_and_other_metric_absence_are_visible():
    from src.online_peer_valuation_ui import online_peer_valuation_html
    v=build();v.update(status='withheld',reason='latest_annual_eps_missing_including_amendment',subject=None,peer_median=None,premium_fraction=None)
    html=online_peer_valuation_html(v)
    assert 'amended filing' in html and 'diluted EPS' in html
    for metric in ('P/S','P/FCF','EV/EBITDA'):assert metric in html


def test_sources_only_disclosure_retains_field_receipts_and_never_renders_script_links():
    from src.online_peer_valuation_ui import online_peer_valuation_html
    v=build();v['subject']['filing_ref']='javascript:alert(1)';v['excluded']=[dict(ticker='<script>bad</script>',reason='provider_industry_differs')]
    html=online_peer_valuation_html(v,sources_only=True)
    assert 'Online peer valuation sources' in html and 'EarningsPerShareDiluted' in html
    assert '2026-02-01' in html and 'b'*64 in html and 'normalized' in html.lower()
    assert 'javascript:' not in html and '<script>' not in html
    assert 'Commercial use' in html and 'Source rights' in html


def test_supported_source_panel_does_not_claim_its_financial_evidence_failed():
    from src.online_peer_valuation_ui import online_peer_valuation_html
    html=online_peer_valuation_html(build(),sources_only=True)
    assert 'Qualified reported annual P/E industry references are available' in html


def test_missing_amended_eps_keeps_the_exact_filing_metadata_trace_visible():
    from src.online_peer_valuation_ui import online_peer_valuation_html
    c=collection();recent=c['issuers'][0]['profile']['payload']['filings']['recent']
    for k,v in dict(form='10-K/A',reportDate='2025-12-31',filingDate='2026-03-01',accessionNumber='0000001001-26-000099',primaryDocument='amend.htm').items():recent[k].append(v)
    html=online_peer_valuation_html(build(c),sources_only=True)
    assert '0000001001-26-000099' in html and '/amend.htm' in html
    assert 'filing metadata' in html and 'EPS fact' in html


def test_excluded_loss_source_and_value_are_visible_but_not_a_valuation_input():
    from src.online_peer_valuation_ui import online_peer_valuation_html
    c=collection();c['issuers'][1]['facts']['payload']['facts']['us-gaap']['EarningsPerShareDiluted']['units']['USD/shares'][0]['val']=-1
    html=online_peer_valuation_html(build(c),sources_only=True)
    assert 'excluded from P/E and the reference median' in html
    assert 'CIK0000001002.json' in html and '-1 USD/shares' in html
    assert '2025-01-01' in html and '2026-02-01' in html and '0000001002-26-000001' in html


def _app():
    import streamlit as st
    from src.company_workbench_ui import render_integrated_company
    ticker=st.query_params.get('ticker','FICT')
    candidate={'cik':'0000001001','title':'Synthetic online company'} if st.query_params.get('online')=='1' else None
    render_integrated_company(st,ticker,profile_scope='synthetic',saved_available=True,online_candidate=candidate,
                              render_saved=lambda section:st.markdown('SAVED-'+section),
                              render_sources=lambda bundle:st.markdown('EXISTING-SOURCES'))


def _setup(monkeypatch, evidence=None):
    import src.online_peer_sources as sources
    from test_integrated_company_workbench import _sources
    other_calls=_sources(monkeypatch)
    dependencies,calls=source_dependencies(evidence)
    for name,key in [('fetch_classification','classification'),('observe_vendor','vendor'),('observe_industry','industry'),('fetch_sec_json_receipt','sec'),('fetch_online_company_prices','prices')]:
        monkeypatch.setattr(sources,name,dependencies[key])
    monkeypatch.setattr(sources,'_now',lambda value=None:NOW if value is None else value)
    return calls,other_calls


def _text(at):return '\n'.join(m.value for m in at.markdown)


def _peer_button(at):return next(b for b in at.button if b.label=='Refresh peer valuation')


@pytest.mark.parametrize('sources',[False,True])
def test_listing_recovery_discloses_original_dates_and_latest_failure(sources):
    from src.online_peer_valuation_ui import online_peer_valuation_html
    from test_online_peer_sources import get
    deps,_=source_dependencies();state={};get(state,refresh=True,dependencies=deps)
    deps['classification']=lambda **kw:{'status':'withheld','reason':'classification_source_unavailable','source_attempts':[dict(source_url='https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt',observed_at='2026-11-01T04:05:00Z',status='unavailable',reason='directory_incomplete',byte_count=130,payload_sha256='c'*64)]}
    view=get(state,refresh=True,dependencies=deps,as_of=NOW+timedelta(minutes=5))
    html=online_peer_valuation_html(view,sources_only=sources)
    assert 'this session' in html and '24 hours' in html and 'original dates' in html
    assert '2026-11-01T04:00:00Z' in html and '2026-11-01T04:05:00Z' in html
    assert '2026-10-30T15:41' in html and '130' in html and 'c'*64 in html
    assert 'Directory content is incomplete' in html and 'https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt' in html


def test_workbench_discloses_recent_listing_policy_before_the_action(monkeypatch):
    _setup(monkeypatch);at=AppTest.from_function(_app).run();at.radio[0].set_value('valuation').run()
    assert not at.exception
    assert any('24 hours' in c.value and 'listing' in c.value.lower() for c in at.caption)


def test_real_compositor_fetches_only_on_peer_action_and_reuses_sources_across_panes(monkeypatch):
    calls,other=_setup(monkeypatch);at=AppTest.from_function(_app).run()
    at.radio[0].set_value('valuation').run()
    assert not at.exception and not calls
    _peer_button(at).click().run(timeout=30)
    assert not at.exception and '20.0% above the industry reference median' in _text(at)
    assert 'SAVED-valuation' in _text(at)
    assert not any(e.label=='Saved Valuation & Scenarios' for e in at.expander)
    before=list(calls)
    at.radio[0].set_value('sources').run()
    assert 'Online peer valuation sources' in _text(at) and 'EXISTING-SOURCES' in _text(at)
    at.radio[0].set_value('financials').run();at.radio[0].set_value('valuation').run()
    assert calls==before and other=={'financial':0,'prices':0} and not at.exception


def test_online_candidate_uses_same_comparison_without_loading_saved_same_symbol_tools(monkeypatch):
    calls,other=_setup(monkeypatch);at=AppTest.from_function(_app);at.query_params['online']='1';at.run()
    at.radio[0].set_value('valuation').run();_peer_button(at).click().run(timeout=30)
    assert '20.0% above the industry reference median' in _text(at) and 'SAVED-' not in _text(at)
    assert not at.exception and calls


def test_switching_company_cannot_display_the_previous_company_comparison(monkeypatch):
    _setup(monkeypatch);at=AppTest.from_function(_app).run()
    at.radio[0].set_value('valuation').run();_peer_button(at).click().run(timeout=30)
    assert '20.0% above the industry reference median' in _text(at)
    at.query_params['ticker']='OTHER';at.run();at.radio[0].set_value('valuation').run()
    assert '20.0% above the industry reference median' not in _text(at) and not at.exception


def test_failed_retry_replaces_the_visible_success_and_preserves_saved_tools(monkeypatch):
    import src.online_peer_sources as sources
    _setup(monkeypatch);at=AppTest.from_function(_app).run()
    at.radio[0].set_value('valuation').run();_peer_button(at).click().run(timeout=30)
    monkeypatch.setattr(sources,'observe_vendor',lambda *a,**kw:(_ for _ in ()).throw(OSError('private exception')))
    _peer_button(at).click().run(timeout=30)
    assert '20.0% above the industry reference median' not in _text(at) and 'Relative valuation withheld' in _text(at)
    assert 'SAVED-valuation' in _text(at) and 'private exception' not in _text(at) and not at.exception


def earnings_collection(value=.8):
    from test_online_peer_valuation import digest
    c=collection()
    for row in c['issuers']:
        rows=row['facts']['payload']['facts']['us-gaap']['EarningsPerShareDiluted']['units']['USD/shares']
        rows.append({**rows[0],'start':'2024-01-01','end':'2024-12-31','val':value})
        row['facts']['normalized_sha256']=digest(row['facts']['payload'])
    return c


@pytest.mark.parametrize('sources_only',[False,True])
def test_reported_earnings_context_has_exact_values_periods_and_source_without_growth_adjusted_claim(sources_only):
    from src.online_peer_valuation_ui import online_peer_valuation_html
    html=online_peer_valuation_html(build(earnings_collection()),sources_only=sources_only)
    assert 'Earnings change context' in html and 'Annual EPS YoY +25.0%' in html
    assert 'same annual filing' in html and '0.8 USD/shares' in html and '1 USD/shares' in html
    assert '2024-01-01' in html and '2024-12-31' in html and '2025-12-31' in html
    assert 'not adjusted for growth' in html and 'does not predict future growth' in html
    assert 'CIK0000001001.json' in html and '0000001001-26-000001' in html


@pytest.mark.parametrize('prior,phrase',[(0,'Prior-year EPS is zero or negative'),(-1,'Prior-year EPS is zero or negative'),(None,'The same filing lacks adjacent prior-year EPS')])
def test_missing_or_nonpositive_growth_has_a_plain_reason_without_erasing_pe(prior,phrase):
    from src.online_peer_valuation_ui import online_peer_valuation_html
    v=build(collection() if prior is None else earnings_collection(prior))
    html=online_peer_valuation_html(v)
    assert 'Annual P/E is 20.0% above the industry reference median' in html
    assert phrase in html and 'EPS YoY withheld' in html
    assert 'Annual EPS YoY +25.0%' not in html


def test_reported_earnings_decline_and_actual_extended_price_range_are_visible():
    from src.online_peer_valuation_ui import online_peer_valuation_html
    from test_peer_price_coverage import two_year_prices
    html=online_peer_valuation_html(build(two_year_prices(earnings_collection(2))))
    assert 'Annual EPS YoY -50.0%' in html
    assert 'Requested price and split history 2y' in html and '2024-11-01 → 2026-10-30' in html
    assert 'requested range does not prove complete history' in html


def test_excluded_loss_observations_include_earnings_context_without_median_membership():
    from src.online_peer_valuation_ui import online_peer_valuation_html
    c=earnings_collection(); row=c['issuers'][1]
    row['facts']['payload']['facts']['us-gaap']['EarningsPerShareDiluted']['units']['USD/shares'][0]['val']=-.2
    from test_online_peer_valuation import digest
    row['facts']['normalized_sha256']=digest(row['facts']['payload'])
    html=online_peer_valuation_html(build(c),sources_only=True)
    assert 'Annual EPS YoY -125.0%' in html and 'excluded from P/E and the reference median' in html
    assert 'data-label="Company">FA</td>' in html


def test_compositor_reuses_new_context_across_source_and_valuation_without_a_second_fetch(monkeypatch):
    calls,_=_setup(monkeypatch,earnings_collection())
    at=AppTest.from_function(_app).run();at.radio[0].set_value('valuation').run();_peer_button(at).click().run(timeout=30)
    assert 'Annual EPS YoY +25.0%' in _text(at) and not at.exception
    before=list(calls);at.radio[0].set_value('sources').run()
    assert 'Annual EPS YoY +25.0%' in _text(at) and calls==before and not at.exception
