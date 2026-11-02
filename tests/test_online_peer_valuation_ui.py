from copy import deepcopy
from datetime import timedelta

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


def _peer_button(at):return next(b for b in at.button if b.label=='更新在线同行估值')


@pytest.mark.parametrize('sources',[False,True])
def test_listing_recovery_discloses_original_dates_and_latest_failure(sources):
    from src.online_peer_valuation_ui import online_peer_valuation_html
    from test_online_peer_sources import get
    deps,_=source_dependencies();state={};get(state,refresh=True,dependencies=deps)
    deps['classification']=lambda **kw:{'status':'withheld','reason':'classification_source_unavailable','source_attempts':[dict(source_url='https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt',observed_at='2026-11-01T04:05:00Z',status='unavailable',reason='directory_incomplete',byte_count=130,payload_sha256='c'*64)]}
    view=get(state,refresh=True,dependencies=deps,as_of=NOW+timedelta(minutes=5))
    html=online_peer_valuation_html(view,sources_only=sources)
    assert '本会话' in html and '24 小时' in html and '未续期' in html
    assert '2026-11-01T04:00:00Z' in html and '2026-11-01T04:05:00Z' in html
    assert '2026-10-30T15:41' in html and '130' in html and 'c'*64 in html
    assert '目录内容不完整' in html and 'https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt' in html


def test_workbench_discloses_recent_listing_policy_before_the_action(monkeypatch):
    _setup(monkeypatch);at=AppTest.from_function(_app).run();at.radio[0].set_value('valuation').run()
    assert not at.exception
    assert any('24 小时' in c.value and '上市' in c.value for c in at.caption)


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
    assert '盈利变化背景' in html and '年度 EPS 同比 +25.0%' in html
    assert '同一年度申报' in html and '0.8 USD/shares' in html and '1 USD/shares' in html
    assert '2024-01-01' in html and '2024-12-31' in html and '2025-12-31' in html
    assert '未按增长调整' in html and '不代表未来增长' in html
    assert 'CIK0000001001.json' in html and '0000001001-26-000001' in html


@pytest.mark.parametrize('prior,phrase',[(0,'基期 EPS 为零或负值'),(-1,'基期 EPS 为零或负值'),(None,'同一申报缺少相邻上年度 EPS')])
def test_missing_or_nonpositive_growth_has_a_plain_reason_without_erasing_pe(prior,phrase):
    from src.online_peer_valuation_ui import online_peer_valuation_html
    v=build(collection() if prior is None else earnings_collection(prior))
    html=online_peer_valuation_html(v)
    assert '年度 P/E 高于同行参照 20.0%' in html
    assert phrase in html and 'EPS 同比暂不计算' in html
    assert '年度 EPS 同比 +25.0%' not in html


def test_reported_earnings_decline_and_actual_extended_price_range_are_visible():
    from src.online_peer_valuation_ui import online_peer_valuation_html
    from test_peer_price_coverage import two_year_prices
    html=online_peer_valuation_html(build(two_year_prices(earnings_collection(2))))
    assert '年度 EPS 同比 -50.0%' in html
    assert '价格与拆股观察请求 2y' in html and '2024-11-01 → 2026-10-30' in html
    assert '请求范围不保证历史完整' in html


def test_excluded_loss_observations_include_earnings_context_without_median_membership():
    from src.online_peer_valuation_ui import online_peer_valuation_html
    c=earnings_collection(); row=c['issuers'][1]
    row['facts']['payload']['facts']['us-gaap']['EarningsPerShareDiluted']['units']['USD/shares'][0]['val']=-.2
    from test_online_peer_valuation import digest
    row['facts']['normalized_sha256']=digest(row['facts']['payload'])
    html=online_peer_valuation_html(build(c),sources_only=True)
    assert '年度 EPS 同比 -125.0%' in html and '不参与 P/E 或参照中位数' in html
    assert 'data-label="公司">FA</td>' in html


def test_compositor_reuses_new_context_across_source_and_valuation_without_a_second_fetch(monkeypatch):
    calls,_=_setup(monkeypatch,earnings_collection())
    at=AppTest.from_function(_app).run();at.radio[0].set_value('valuation').run();_peer_button(at).click().run(timeout=30)
    assert '年度 EPS 同比 +25.0%' in _text(at) and not at.exception
    before=list(calls);at.radio[0].set_value('sources').run()
    assert '年度 EPS 同比 +25.0%' in _text(at) and calls==before and not at.exception
