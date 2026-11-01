from copy import deepcopy

import pytest
from streamlit.testing.v1 import AppTest

from test_online_peer_valuation import build,collection,NOW
from test_online_peer_sources import source_dependencies


def test_online_answer_leads_with_metric_qualified_difference_and_actual_source_dates():
    from src.online_peer_valuation_ui import online_peer_valuation_html
    view=build();before=deepcopy(view);html=online_peer_valuation_html(view)
    assert '年度 P/E 高于同行参照 20.0%' in html and '30.0×' in html and '25.0×' in html
    assert '非 TTM' in html and '35 天' in html and '自动筛选' in html
    assert '2026-10-30' in html and '2025-01-01' in html and '2025-12-31' in html
    assert 'EarningsPerShareDiluted' in html and 'USD/shares' in html and '2026-02-01' in html
    assert '不是低估或高估结论' in html and '<h1' not in html
    assert 'SEC 收益' in html and 'https://data.sec.gov/' in html and view==before


@pytest.mark.parametrize('price,phrase',[(20,'低于同行参照 20.0%'),(25,'等于同行参照中位数')])
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
    assert '暂不判断相对贵便宜' in html and '2 家' in html and '至少 3 家' in html
    assert 'FA' in html and '负值' in html and '20.0%' not in html


def test_amended_annual_gap_and_other_metric_absence_are_visible():
    from src.online_peer_valuation_ui import online_peer_valuation_html
    v=build();v.update(status='withheld',reason='latest_annual_eps_missing_including_amendment',subject=None,peer_median=None,premium_fraction=None)
    html=online_peer_valuation_html(v)
    assert '修订' in html and '稀释每股收益' in html
    for metric in ('P/S','P/FCF','EV/EBITDA'):assert metric in html


def test_sources_only_disclosure_retains_field_receipts_and_never_renders_script_links():
    from src.online_peer_valuation_ui import online_peer_valuation_html
    v=build();v['subject']['filing_ref']='javascript:alert(1)';v['excluded']=[dict(ticker='<script>bad</script>',reason='provider_industry_differs')]
    html=online_peer_valuation_html(v,sources_only=True)
    assert '在线同行估值来源' in html and 'EarningsPerShareDiluted' in html
    assert '2026-02-01' in html and 'b'*64 in html and 'normalized' in html
    assert 'javascript:' not in html and '<script>' not in html
    assert '商业' in html and '权限' in html


def test_supported_source_panel_does_not_claim_its_financial_evidence_failed():
    from src.online_peer_valuation_ui import online_peer_valuation_html
    html=online_peer_valuation_html(build(),sources_only=True)
    assert '已取得通过规则核对的年度 P/E' in html


def test_missing_amended_eps_keeps_the_exact_filing_metadata_trace_visible():
    from src.online_peer_valuation_ui import online_peer_valuation_html
    c=collection();recent=c['issuers'][0]['profile']['payload']['filings']['recent']
    for k,v in dict(form='10-K/A',reportDate='2025-12-31',filingDate='2026-03-01',accessionNumber='0000001001-26-000099',primaryDocument='amend.htm').items():recent[k].append(v)
    html=online_peer_valuation_html(build(c),sources_only=True)
    assert '0000001001-26-000099' in html and '/amend.htm' in html
    assert '申报元数据' in html and '收益字段' in html


def test_excluded_loss_source_and_value_are_visible_but_not_a_valuation_input():
    from src.online_peer_valuation_ui import online_peer_valuation_html
    c=collection();c['issuers'][1]['facts']['payload']['facts']['us-gaap']['EarningsPerShareDiluted']['units']['USD/shares'][0]['val']=-1
    html=online_peer_valuation_html(build(c),sources_only=True)
    assert '不参与 P/E 或参照中位数' in html
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


def _setup(monkeypatch):
    import src.online_peer_sources as sources
    from test_integrated_company_workbench import _sources
    other_calls=_sources(monkeypatch)
    dependencies,calls=source_dependencies()
    for name,key in [('fetch_classification','classification'),('observe_vendor','vendor'),('observe_industry','industry'),('fetch_sec_json_receipt','sec'),('fetch_online_company_prices','prices')]:
        monkeypatch.setattr(sources,name,dependencies[key])
    monkeypatch.setattr(sources,'_now',lambda value=None:NOW if value is None else value)
    return calls,other_calls


def _text(at):return '\n'.join(m.value for m in at.markdown)


def _peer_button(at):return next(b for b in at.button if b.label=='更新在线同行估值')


def test_real_compositor_fetches_only_on_peer_action_and_reuses_sources_across_panes(monkeypatch):
    calls,other=_setup(monkeypatch);at=AppTest.from_function(_app).run()
    at.radio[0].set_value('valuation').run()
    assert not at.exception and not calls
    _peer_button(at).click().run(timeout=30)
    assert not at.exception and '高于同行参照 20.0%' in _text(at)
    assert 'SAVED-valuation' in _text(at)
    assert any(e.label=='已保存的估值与情景分析' for e in at.expander)
    before=list(calls)
    at.radio[0].set_value('sources').run()
    assert '在线同行估值来源' in _text(at) and 'EXISTING-SOURCES' in _text(at)
    at.radio[0].set_value('financials').run();at.radio[0].set_value('valuation').run()
    assert calls==before and other=={'financial':0,'prices':0} and not at.exception


def test_online_candidate_uses_same_comparison_without_loading_saved_same_symbol_tools(monkeypatch):
    calls,other=_setup(monkeypatch);at=AppTest.from_function(_app);at.query_params['online']='1';at.run()
    at.radio[0].set_value('valuation').run();_peer_button(at).click().run(timeout=30)
    assert '高于同行参照 20.0%' in _text(at) and 'SAVED-' not in _text(at)
    assert not at.exception and calls


def test_switching_company_cannot_display_the_previous_company_comparison(monkeypatch):
    _setup(monkeypatch);at=AppTest.from_function(_app).run()
    at.radio[0].set_value('valuation').run();_peer_button(at).click().run(timeout=30)
    assert '高于同行参照 20.0%' in _text(at)
    at.query_params['ticker']='OTHER';at.run();at.radio[0].set_value('valuation').run()
    assert '高于同行参照 20.0%' not in _text(at) and not at.exception


def test_failed_retry_replaces_the_visible_success_and_preserves_saved_tools(monkeypatch):
    import src.online_peer_sources as sources
    _setup(monkeypatch);at=AppTest.from_function(_app).run()
    at.radio[0].set_value('valuation').run();_peer_button(at).click().run(timeout=30)
    monkeypatch.setattr(sources,'observe_vendor',lambda *a,**kw:(_ for _ in ()).throw(OSError('private exception')))
    _peer_button(at).click().run(timeout=30)
    assert '高于同行参照 20.0%' not in _text(at) and '暂不判断相对贵便宜' in _text(at)
    assert 'SAVED-valuation' in _text(at) and 'private exception' not in _text(at) and not at.exception
