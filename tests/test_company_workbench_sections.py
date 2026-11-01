"""The integrated page must not equate inspected facts with model eligibility."""
from copy import deepcopy

import pytest

from tests.test_sec_annual_history import _view, _payload
from tests.test_online_company_prices import _fetch, OBSERVED


def financial_view():
    from src.sec_annual_history import build_sec_annual_history
    view = _view()
    view['annual_history'] = build_sec_annual_history(view, _payload())
    return view


def price_view():
    from src.online_company_prices import fetch_online_company_prices
    return fetch_online_company_prices('FICT', observed_at=OBSERVED, fetcher=_fetch())


def test_reported_facts_and_prices_do_not_promote_saved_models_or_mutate_inputs():
    from src.company_workbench_sections import workbench_projection, workbench_header_html
    view, prices = financial_view(), price_view()
    before = deepcopy((view, prices))
    result = workbench_projection('FICT', view, prices, expected_cik='0000001234')
    assert result['annual_count'] == 3
    assert result['price_count'] == 3
    assert result['facts']['revenue']['value'] == 150
    assert result['period_end'] == '2025-12-31'
    assert result['model_eligibility'] == 'independent'
    assert result['readiness_promoted'] is False
    assert (view, prices) == before
    rendered = workbench_header_html('FICT', result, saved_scope=True)
    assert rendered.count('<h1') == 1
    assert 'FICT Company Brief' in rendered
    assert '模型资格独立' in rendered


def test_foreign_or_missing_source_does_not_turn_into_zero_or_reuse_another_ticker():
    from src.company_workbench_sections import workbench_projection
    result = workbench_projection('OTHER', financial_view(), price_view())
    assert result['facts'] == {}
    assert result['annual_count'] == result['price_count'] == 0


def test_known_cik_conflict_withholds_the_bundle():
    from src.company_workbench_sections import workbench_projection
    result = workbench_projection('FICT', financial_view(), price_view(), expected_cik='0000009999')
    assert result['identity_conflict'] is True
    assert result['facts'] == {}
    assert result['price_count'] == 0


def test_unavailable_financial_source_preserves_independently_valid_price_history():
    from src.company_workbench_sections import workbench_projection
    result = workbench_projection('FICT', {'ticker':'FICT','status':'unavailable'}, price_view())
    assert result['annual_count'] == 0
    assert result['price_count'] == 3
    assert result['facts'] == {}


@pytest.mark.parametrize('change', [{'rights_status':'unreviewed'}, {'unit':'EUR'}, {'value':True}, {'value':float('nan')}])
def test_corrupt_cached_financial_field_is_not_counted(change):
    from src.company_workbench_sections import workbench_projection
    view = financial_view()
    view['annual_history']['periods'][-1]['fields'][0].update(change)
    assert workbench_projection('FICT',view,price_view())['annual_count'] == 0


def test_zero_is_a_reported_value_and_missing_component_stays_absent():
    from src.company_workbench_sections import workbench_projection
    view = financial_view()
    last=view['annual_history']['periods'][-1]
    next(f for f in last['fields'] if f['field']=='operating_income')['value']=0
    last['fields']=[f for f in last['fields'] if f['field']!='cash_from_operations']
    facts=workbench_projection('FICT',view,price_view())['facts']
    assert facts['operating_income']['value']==0
    assert 'cash_from_operations' not in facts


def test_invalid_price_cache_cannot_claim_loaded_price_history():
    from src.company_workbench_sections import workbench_projection
    prices=price_view();prices['bars'][-1]['close']=True
    assert workbench_projection('FICT',financial_view(),prices)['price_count']==0


def test_unknown_section_recovers_to_overview_and_exact_section_order_is_visible():
    from src.company_workbench_sections import section_key, SECTIONS
    assert section_key('not-a-section')=='overview'
    assert section_key('financials')=='financials'
    assert [label for key,label in SECTIONS]==['概览','财务趋势','估值与同行','研究记录','数据来源']


def test_direct_quarter_coverage_survives_unsupported_annual_without_inventing_quarter_cash():
    from src.company_workbench_sections import workbench_projection
    from tests.test_sec_quarterly_history import _build
    history=_build()
    view={'ticker':'FICT','status':'unavailable','sec_cik':'0000001234','quarterly_history':history,
          'companyfacts_identity':{'status':'source_matched',**{k:history[k] for k in ('ticker','sec_cik','source_url','observed_at','payload_sha256')}}}
    result=workbench_projection('FICT',view,{'ticker':'FICT','status':'unavailable'})
    assert result['annual_count']==0
    assert result['quarter_count']==3
    assert result['period_kind']=='quarterly'
    assert result['period_end']=='2025-09-30'
    assert result['facts']['revenue']['value']==130
    assert 'cash_from_operations' not in result['facts']


def test_conflicting_cached_identity_cannot_hide_behind_matching_top_level_cik():
    from src.company_workbench_sections import workbench_projection
    view=financial_view();view['companyfacts_identity']={'sec_cik':'0000009999'}
    result=workbench_projection('FICT',view,price_view(),expected_cik='0000001234')
    assert result['identity_conflict'] is True
    assert result['facts']=={}
    assert result['price_count']==0


def test_commercial_mode_cannot_reuse_personal_inspection_cache(monkeypatch):
    from src.company_workbench_sections import workbench_projection
    view,prices=financial_view(),price_view()
    monkeypatch.setenv('COMMERCIAL_RESEARCH_MODE','1')
    result=workbench_projection('FICT',view,prices)
    assert result['annual_count']==result['price_count']==0
    assert result['facts']=={}


def test_failed_source_attempt_is_not_presented_as_not_requested():
    from src.company_workbench_sections import workbench_projection,workbench_header_html
    unavailable={'ticker':'FICT','status':'unavailable','reason':'source_timeout'}
    projection=workbench_projection('FICT',unavailable,unavailable)
    rendered=workbench_header_html('FICT',projection,True)
    assert '尚未请求在线数据' not in rendered
    assert '暂无通过核对的在线数据' in rendered
