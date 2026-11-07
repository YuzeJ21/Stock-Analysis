"""The composed financial workspace displays evidence without changing its scope."""
from copy import deepcopy

import pytest

from tests.test_company_workbench_sections import financial_view, price_view


def test_financial_chart_and_table_share_annual_periods_and_units_without_mutation():
    from src.company_workbench_presentation import financial_workspace_html
    view = financial_view()
    before = deepcopy(view)
    html = financial_workspace_html('FICT', view, period_kind='annual', metric='revenue')
    assert 'company-analysis-grid' in html
    assert 'aria-label="Annual revenue trend"' in html
    assert 'aria-label="Reported annual financials"' in html
    assert 'USD millions' in html and '2025-12-31' in html
    assert 'SEC Companyfacts' in html and 'Period evidence' in html
    assert 'raw redistribution held' in html
    assert view == before


def test_quarter_cash_gap_is_not_derived_from_cumulative_cash():
    from src.company_workbench_presentation import financial_workspace_html
    from tests.test_sec_quarterly_history import _build
    h = _build()
    view = {'ticker':'FICT', 'status':'inspection_only', 'sec_cik':h['sec_cik'],
            'quarterly_history':h, 'companyfacts_identity':{'status':'source_matched',
                **{key:h[key] for key in ('ticker','sec_cik','source_url','observed_at','payload_sha256')}}}
    html = financial_workspace_html('FICT', view, period_kind='quarterly', metric='cash_from_operations', limit=2)
    assert 'Quarterly operating cash flow trend' in html
    assert 'No directly reported values' in html
    assert 'Gap' in html
    assert 'Cumulative cash flow' in html and 'not single-quarter' in html


@pytest.mark.parametrize('alter', ['other_ticker', 'conflicting_cik', 'unreviewed_rights'])
def test_invalid_or_cross_company_history_cannot_render_a_chart(alter):
    from src.company_workbench_presentation import financial_workspace_html
    view = financial_view()
    if alter == 'other_ticker':
        view['ticker'] = 'OTHER'
    elif alter == 'conflicting_cik':
        view['companyfacts_identity'] = {'sec_cik':'0000009999'}
    else:
        view['annual_history']['periods'][-1]['fields'][0]['rights_status'] = 'unreviewed'
    html = financial_workspace_html('FICT', view)
    assert '<svg' not in html and '<table' not in html
    assert 'needs verification' in html


def test_overview_metrics_keep_price_financial_and_peer_evidence_with_a_separate_eps_gap():
    from src.company_workbench_presentation import workbench_metrics_html
    from src.company_workbench_sections import workbench_projection
    from src.company_answer_summary import build_company_answers
    f, p = financial_view(), price_view()
    peer = {'ticker':'FICT','status':'not_requested'}
    answers = build_company_answers('FICT', workbench_projection('FICT',f,p), f,p,{},peer)
    html = workbench_metrics_html('FICT', answers, peer)
    assert html.count('data-company-answer=') == 4
    assert 'Annual diluted EPS' in html and 'Needs verification' in html
    assert 'Open Valuation &amp; Peers' in html
    assert 'View evidence' in html


def test_eps_card_does_not_reuse_other_security_or_nonfinite_values():
    from src.company_workbench_presentation import workbench_metrics_html
    answers = [dict(key=k,title=k,value='x',context='',evidence=(),links=())
               for k in ('price','financial','valuation')]
    peer = {'ticker':'OTHER','status':'research_comparison','subject':{'ticker':'OTHER','eps':2.0}}
    assert 'USD 2.00' not in workbench_metrics_html('FICT',answers,peer)


def test_changed_accounting_definitions_do_not_form_one_cash_flow_trend():
    from src.company_workbench_presentation import _bars
    rows = [dict(status='available',period_end=day,fields={'cash_from_operations':{
        'value':value,'taxonomy':'us-gaap','concept':concept,'unit':'USD'}})
        for day,value,concept in [('2024-12-31',0,'NetCashProvidedByUsedInOperatingActivities'),
                                 ('2025-12-31',10,'NetCashProvidedByUsedInOperatingActivitiesContinuingOperations')]]
    result = _bars(rows,'cash_from_operations','Cash flow')
    assert '<svg' not in result and 'Different reported definitions' in result


def test_peer_source_observations_remain_in_contextual_evidence():
    from src.online_peer_valuation_ui import online_peer_valuation_html
    view = {'ticker':'FICT','status':'unavailable','reason':'selected_listing_or_cik_unverified',
            'attempted_at':'2026-11-07T12:00:00Z'}
    html = online_peer_valuation_html(view,compact=True)
    assert html.index('Source query attempted') > html.index('<summary>View actual fiscal periods, prices, and sources</summary>')
    assert 'At least 3' in html


def test_commercial_mode_cannot_display_cached_personal_financial_history(monkeypatch):
    from src.company_workbench_presentation import financial_workspace_html
    view=financial_view()
    monkeypatch.setenv('COMMERCIAL_RESEARCH_MODE','1')
    html=financial_workspace_html('FICT',view)
    assert '<svg' not in html and '<table' not in html
    assert 'Personal research observations remain unavailable' in html


def test_cash_flow_table_labels_continuing_scope_even_on_revenue_chart():
    from src.company_workbench_presentation import financial_workspace_html
    from src.sec_annual_history import build_sec_annual_history
    from tests.test_sec_annual_history import _payload, _view
    payload=_payload();facts=payload['facts']['us-gaap']
    original=facts.pop('NetCashProvidedByUsedInOperatingActivities')
    rows=original['units']['USD']
    facts['NetCashProvidedByUsedInOperatingActivities']={'units':{'USD':rows[:-1]}}
    facts['NetCashProvidedByUsedInOperatingActivitiesContinuingOperations']={'units':{'USD':rows[-1:]}}
    view=_view(payload);view['annual_history']=build_sec_annual_history(view,payload)
    html=financial_workspace_html('FICT',view)
    assert 'Operating cash flow · basis varies' in html
    assert 'Continuing operations' in html and 'Total operations' in html
