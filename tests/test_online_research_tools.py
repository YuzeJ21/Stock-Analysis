"""Constructed observations; no transport or canonical readiness is involved."""
from copy import deepcopy
from datetime import datetime, timezone
import json

import pytest

NOW = datetime(2026, 10, 30, 18, tzinfo=timezone.utc)
CIK = '0000001234'


def financial(payload=None):
    from test_sec_annual_history import _payload, _view
    from test_sec_quarterly_history import _build
    from src.sec_annual_history import build_sec_annual_history
    p = _payload() if payload is None else payload
    view = _view(p)
    view['annual_history'] = build_sec_annual_history(view, p)
    view['quarterly_history'] = _build()
    view['companyfacts_identity'] = dict(status='source_matched', ticker='FICT', sec_cik=CIK,
        source_url=view['source_url'], observed_at=NOW.isoformat(), payload_sha256='a'*64,
        association_observed_at=NOW.isoformat(), association_source_url='https://www.sec.gov/files/company_tickers.json',
        association_payload_sha256='b'*64)
    # The quarterly validator binds this exact source timestamp.
    view['companyfacts_identity']['observed_at'] = view['quarterly_history']['observed_at']
    from src.online_filing_context import build_filing_inventory
    columns = ('form', 'reportDate', 'filingDate', 'accessionNumber', 'acceptanceDateTime', 'primaryDocument')
    rows = [('10-K','2025-12-31','2026-03-01','0000001234-26-000001','2026-03-01T12:00:00Z','annual.htm')]
    rows += [('10-Q', end, filed, f'0000001234-25-00000{i+1}', filed+'T12:00:00Z','quarter.htm')
        for i,(end,filed) in enumerate([('2025-03-31','2025-05-01'),('2025-06-30','2025-08-01'),('2025-09-30','2025-11-01')])]
    profile = dict(cik=1234,tickers=['FICT'],name='Synthetic operating company',sic='3571',entityType='operating',
        fiscalYearEnd='1231',filings={'recent':{key:[r[i] for r in rows] for i,key in enumerate(columns)}})
    receipt = dict(status='ready',source_url=f'https://data.sec.gov/submissions/CIK{CIK}.json',
        observed_at=NOW.isoformat(),payload_sha256='d'*64,payload=profile)
    view['filing_inventory'] = build_filing_inventory(receipt,ticker='FICT',expected_cik=CIK,as_of=NOW)
    return view


def context(view=None, **kwargs):
    from src.online_research_tools import build_online_research_context
    return build_online_research_context(financial() if view is None else view, {},
        ticker='FICT', profile_key='personal', expected_cik=CIK, as_of=NOW, **kwargs)


def metric(c, key, kind='annual', end='2025-12-31'):
    return next(m for m in c['business_trend']['metrics']
                if m['key'] == key and m['period_kind'] == kind and m['period_end'] == end)


def parameters(**kwargs):
    return dict(revenue_growth=.1, fcf_margin=.2, wacc=.1, terminal_growth=.02, forecast_years=5, **kwargs)


def test_real_validators_feed_compatible_growth_margin_and_cash_without_promoting_readiness():
    c = context()
    assert c['schema_version'] == 'online-company-research-v1'
    assert metric(c, 'revenue_yoy')['value'] == pytest.approx(.25)
    assert metric(c, 'operating_margin')['value'] == pytest.approx(20/150)
    assert metric(c, 'operating_margin_change_pp')['value'] == pytest.approx((20/150+5/120)*100)
    cash = metric(c, 'cfo_less_ppe')
    assert cash['value'] == 23 and cash['unit'] == 'USD'
    assert 'not FCFF' in cash['basis']
    assert cash['source_refs'][0]['form']=='10-K' and cash['source_refs'][0]['filed']=='2026-03-01'
    assert c['saved_readiness_promoted'] is False and c['commercial_eligible'] is False
    assert 'dcf_ready' not in json.dumps(c)
    json.dumps(c, allow_nan=False)


def test_direct_quarters_never_subtract_cumulative_cash_as_if_quarter_cash():
    c = context()
    assert metric(c, 'revenue_qoq', 'quarterly', '2025-06-30')['value'] == pytest.approx(.2)
    assert metric(c, 'cfo_less_ppe', 'quarterly', '2025-06-30')['value'] is None
    assert metric(c, 'cfo_less_ppe', 'cumulative', '2025-06-30')['value'] == 33


@pytest.mark.parametrize('concept,capex', [('NetCashProvidedByUsedInOperatingActivities', -7),
    ('NetCashProvidedByUsedInOperatingActivitiesContinuingOperations', 7)])
def test_negative_spending_and_continuing_operations_do_not_become_total_cfo_less_ppe(concept, capex):
    from test_sec_annual_history import _payload
    p = _payload(); facts = p['facts']['us-gaap']
    facts[concept] = facts.pop('NetCashProvidedByUsedInOperatingActivities')
    facts['PaymentsToAcquirePropertyPlantAndEquipment']['units']['USD'][-1]['val'] = capex
    assert metric(context(financial(p)), 'cfo_less_ppe')['value'] is None


def test_invalid_identity_or_history_cannot_become_scenario_base():
    v = financial(); v['companyfacts_identity']['sec_cik'] = '0000009999'
    c = context(v)
    assert c['status'] == 'withheld' and c['scenario_base']['revenue'] is None
    v = financial(); v['annual_history']['periods'][-1]['fields'][0]['value'] = True
    assert context(v)['scenario_base']['revenue'] is None


def test_semantic_revision_excludes_raw_digests_and_retrieval_but_includes_actual_values():
    a = context(); v = financial()
    v['companyfacts_identity']['payload_sha256'] = 'c'*64
    v['quarterly_history']['payload_sha256'] = 'c'*64
    b = context(v)
    assert a['source_revision'] == b['source_revision']
    assert a['source_metadata_revision'] != b['source_metadata_revision']
    v = financial(); row = v['annual_history']['periods'][-1]
    row['revenue'] = 151
    next(f for f in row['fields'] if f['field']=='revenue')['value'] = 151
    assert context(v)['source_revision'] != a['source_revision']


def test_existing_dcf_kernel_uses_hypothetical_margin_and_growth_and_preserves_ev_without_capital(monkeypatch):
    import src.online_research_tools as tools
    from src.valuation import calculate_dcf
    calls = []
    def inspect(source, assumptions):
        calls.append((source, assumptions))
        return calculate_dcf(source, assumptions)
    monkeypatch.setattr(tools, 'calculate_dcf', inspect)
    c = context(); a = tools.run_online_scenario(c, parameters())
    assert a['status']=='calculated' and a['enterprise_value'] > 0
    assert a['equity_value'] is None and a['value_per_assumed_share'] is None
    assert all(source.free_cash_flow is None for source, _ in calls)
    assert all(assumptions.tax_rate is None for _, assumptions in calls)
    b = tools.run_online_scenario(c, {**parameters(), 'fcf_margin':.3})
    d = tools.run_online_scenario(c, {**parameters(), 'revenue_growth':.2})
    assert b['enterprise_value'] > a['enterprise_value'] and d['enterprise_value'] > a['enterprise_value']
    assert a['assumptions']['basis'] == 'user_hypothetical'
    assert any('Normalized growth' in warning for warning in a['assumptions']['kernel_normalization_warnings'])
    assert len(a['projected_fcfs']) == 5 and a['sensitivity']['enterprise_value_grid']


@pytest.mark.parametrize('field,value', [('revenue_growth',float('nan')),('wacc',float('inf')),
    ('forecast_years',True),('forecast_years',2.5),('fcf_margin',.8),('terminal_growth',.1)])
def test_invalid_hypothetical_assumptions_fail_closed(field, value):
    from src.online_research_tools import run_online_scenario
    result = run_online_scenario(context(), {**parameters(), field:value})
    assert result['status']=='invalid' and result['enterprise_value'] is None
    json.dumps(result, allow_nan=False)


def test_per_share_math_requires_explicit_compatible_capital_structure_basis():
    from src.online_research_tools import run_online_scenario
    c = context()
    held = run_online_scenario(c, parameters(), assumed_net_debt=10, assumed_shares=5)
    assert held['enterprise_value'] is not None and held['equity_value'] is None
    result = run_online_scenario(c, parameters(), assumed_net_debt=10, assumed_shares=5,
        capital_structure_basis=dict(currency='USD', share_basis='assumed_common_shares', label='User-entered scenario'))
    assert result['equity_value'] == pytest.approx(result['enterprise_value']-10)
    assert result['value_per_assumed_share'] == pytest.approx(result['equity_value']/5)
    assert result['market_price_comparison'] is None


def test_notes_are_genuine_issuer_scoped_and_missing_process_work_is_actionable():
    from src.company_research_notes import CompanyNotes, CompanyNotesScope
    from src.research_thesis_journal import JOURNAL_SCHEMA_VERSION, JOURNAL_COLUMNS, JournalEntry
    entry = JournalEntry(**{**dict.fromkeys(JOURNAL_COLUMNS,''), 'schema_version':JOURNAL_SCHEMA_VERSION,
        'entry_id':'one','profile_key':'personal','ticker':'FICT','thesis_id':'thesis','entry_type':'thesis',
        'recorded_at':'2026-10-29T12:00:00Z','effective_at':'2026-10-29T12:00:00Z',
        'reviewer':'Owner','summary':'Hypothesis authored by the owner','review_due_date':'2026-11-10'})
    notes = CompanyNotes(CompanyNotesScope('personal','FICT',CIK), (entry,), (), ())
    c = context(notes=notes)
    assert c['notes_summary']['current_thesis'] == entry.summary
    assert c['decision_lab']['status'] == 'process_work_needed'
    assert any(lane['key']=='invalidation' and lane['state']=='missing' for lane in c['decision_lab']['lanes'])
    assert c['forward_view']['user_hypothesis'] == entry.summary
    wrong = CompanyNotes(CompanyNotesScope('personal','FICT','0000009999'), (entry,), (), ())
    assert context(notes=wrong)['notes_summary']['status'] == 'withheld'


def reseal_inventory(inventory):
    from src.online_filing_context import _seal
    inventory['review_triggers'] = [dict(trigger_type='newly_observed_filing',anchor=a)
        for a in inventory['latest'].values() if a]
    inventory['review_triggers'] += [dict(trigger_type='current_report_filing',anchor=a)
        for a in reversed(inventory.get('earnings_reports',[]))]
    return _seal({k:v for k,v in inventory.items() if k not in {'normalized_sha256','packet_digest'}})


def test_later_filing_pending_keeps_history_but_holds_current_scenario_and_existing_peer_verdict():
    from src.online_research_tools import run_online_scenario
    v = financial(); inventory = v['filing_inventory']
    anchor = {**inventory['latest']['annual'], 'period_end':'2026-06-30', 'report_date':'2026-06-30',
        'accession':'0000001234-26-000010','filed':'2026-09-01','accepted_at':'2026-09-01T12:00:00Z',
        'source_url':'https://www.sec.gov/Archives/edgar/data/1234/000000123426000010/annual.htm'}
    inventory['periods']['annual'].append(anchor); inventory['latest']['annual']=anchor
    v['filing_inventory'] = reseal_inventory(inventory)
    c = context(v)
    assert c['filing_coverage']['current']['annual']['status']=='facts_pending'
    assert any(p['period_end']=='2025-12-31' for p in c['business_trend']['periods'])
    assert run_online_scenario(c, parameters())['enterprise_value'] is None


@pytest.mark.parametrize('sic,entity', [('6021','operating'),('6311','operating'),('3571','investment'),('6770','operating')])
def test_financial_sector_and_unsupported_entities_are_excluded_from_operating_company_dcf(sic,entity):
    from src.online_research_tools import run_online_scenario
    v = financial(); v['filing_inventory']['issuer'].update(sic=sic,entity_type=entity)
    v['filing_inventory']=reseal_inventory(v['filing_inventory'])
    assert run_online_scenario(context(v), parameters())['enterprise_value'] is None


def test_observation_outages_are_independent_and_old_annual_status_cannot_be_reused():
    v = financial(); v.update(status='unavailable', reason='annual_source_failed')
    c = context(v)
    assert not any(p['kind']=='annual' for p in c['business_trend']['periods'])
    assert any(p['kind']=='quarterly' for p in c['business_trend']['periods'])
    assert c['scenario_base']['revenue'] is None


def test_view_identity_cannot_be_substituted_even_when_history_is_self_consistent():
    v = financial(); v['ticker']='OTHER'; v['annual_history']['ticker']='OTHER'
    assert context(v)['scenario_base']['revenue'] is None


def test_actual_peer_collection_is_revalidated_and_pending_or_price_changes_hold_its_current_verdict():
    from test_online_peer_valuation import collection, NOW as PEER_NOW
    from src.online_research_tools import build_online_research_context
    from src.online_filing_context import build_filing_inventory
    peers = collection(); v = financial(); cik='0000001001'
    def rebind(value):
        if isinstance(value, dict):
            return {k: rebind(val) for k,val in value.items()}
        if isinstance(value, list):
            return [rebind(val) for val in value]
        if isinstance(value,str):
            return value.replace(CIK,cik).replace('1234/','1001/').replace(NOW.isoformat(),PEER_NOW.isoformat()).replace('2026-10-30T18:00:00Z',PEER_NOW.isoformat()).replace('2026-10-30T12:00:00Z',PEER_NOW.isoformat())
        return value
    v=rebind(v)
    # The online peer source's annual accession/date must match the financial context.
    for period in v['annual_history']['periods']:
        period['filed']='2026-02-01'
    profile=deepcopy(peers['issuers'][0]['profile'])
    recent=profile['payload']['filings']['recent']; recent['acceptanceDateTime']=['2026-02-01T12:00:00Z']
    v['filing_inventory']=build_filing_inventory(profile,ticker='FICT',expected_cik=cik,as_of=PEER_NOW)
    prices=peers['issuers'][0]['prices']
    def build(fin=v, p=prices):
        return build_online_research_context(fin,p,peers,ticker='FICT',profile_key='personal',expected_cik=cik,as_of=PEER_NOW)
    c=build()
    assert c['peer_read_through']['status']=='research_comparison'
    assert c['peer_read_through']['peer_count']==3
    assert '"payload":' not in json.dumps(c)
    serialized_close=deepcopy(prices)
    serialized_close['bars'][-1]['close'] += .0000006
    assert build(p=serialized_close)['peer_read_through']['status']=='research_comparison'
    changed_close=deepcopy(prices)
    changed_close['bars'][-1]['close'] += .01
    assert build(p=changed_close)['peer_read_through']['reason']=='peer_subject_price_differs_from_current_prices'
    peers['issuers'][1]['facts']['payload_sha256']='e'*64
    metadata_refresh=build()
    assert metadata_refresh['source_revision']==c['source_revision']
    assert metadata_refresh['source_metadata_revision']!=c['source_metadata_revision']
    different=deepcopy(prices); different['bars'][-1]['date']='2026-10-29'; different['last_price_date']='2026-10-29'
    held=build(p=different)
    assert held['peer_read_through']['status']=='withheld'
    assert 'price_date' in held['peer_read_through']['reason']
    assert held['source_revision'] != c['source_revision']
    newer=deepcopy(v); inventory=newer['filing_inventory']; anchor=inventory['latest']['annual']
    revised={**anchor,'accession':'0000001001-26-000002','form':'10-K/A','amendment':True,
        'filed':'2026-10-30','accepted_at':'2026-10-30T12:00:00Z',
        'source_url':'https://www.sec.gov/Archives/edgar/data/1001/000000100126000002/annual.htm'}
    inventory['periods']['annual'].append(revised);inventory['latest']['annual']=revised
    newer['filing_inventory']=reseal_inventory(inventory)
    assert build(fin=newer)['peer_read_through']['reason']=='latest_annual_filing_not_corroborated'
    # Once revised revenue facts arrive, an independently stale EPS collection
    # from the original filing must still not regain its old verdict.
    row=newer['annual_history']['periods'][-1]
    row.update(accession=revised['accession'],form='10-K/A',filed='2026-10-30')
    for field in row['fields']:
        field['accession']=revised['accession']
    updated=build(fin=newer)
    assert updated['filing_coverage']['current']['annual']['status']=='corroborated'
    assert updated['peer_read_through']['status']=='withheld'
    assert updated['peer_read_through']['reason']=='peer_subject_filing_version_differs_from_current_financials'


def test_refreshing_observation_metadata_alone_keeps_semantic_revision_and_scenario_current():
    from src.online_research_tools import run_online_scenario, build_online_research_context
    a=context(); scenario=run_online_scenario(a,parameters())
    v=financial()
    def update(value):
        if isinstance(value,dict):
            return {k:update(val) for k,val in value.items()}
        if isinstance(value,list):
            return [update(val) for val in value]
        if isinstance(value,str):
            return value.replace('2026-10-30T12:00:00Z','2026-10-30T13:00:00Z')
        return value
    v=update(v)
    b=context(v,scenario=scenario)
    assert b['source_revision']==a['source_revision']
    assert b['source_metadata_revision'] != a['source_metadata_revision']
    assert b['scenario'] is not None and b['assumptions']
    assert b['decision_lab']['hypothetical_assumptions']['status']=='documented'
    different=build_online_research_context(v,{},ticker='FICT',profile_key='other',expected_cik=CIK,as_of=NOW,scenario=scenario)
    assert different['scenario'] is None


@pytest.mark.parametrize('bad',[None, [], 'bad', {'status':'inspection_only','annual_history':[]}])
def test_malformed_sources_remain_json_safe_gaps(bad):
    from src.online_research_tools import build_online_research_context
    c=build_online_research_context(bad,bad,bad,bad,ticker='FICT',profile_key='personal',expected_cik=CIK,as_of=NOW)
    assert c['status']=='withheld'
    json.dumps(c,allow_nan=False)


def test_normalized_context_never_carries_transport_archive_keys_from_optional_inputs():
    v=financial();v['earnings_components']=dict(ticker='FICT',sec_cik=CIK,status='withheld',
        raw_payload={'facts':'archive'},html='<html>archive</html>',response_body='archive')
    result=context(v)
    assert not {'raw_payload','html','response_body'} & set(result['earnings_components'])


def test_ordinary_rebuild_uses_stable_source_observed_time_and_keeps_scenario_draft_distinct():
    from datetime import timedelta
    from src.online_research_tools import build_online_research_context
    v=financial()
    a=context(v)
    b=build_online_research_context(v,{},ticker='FICT',profile_key='personal',expected_cik=CIK,
        as_of=NOW+timedelta(minutes=10))
    assert a['observed_at']==b['observed_at']
    assert a['source_revision']==b['source_revision']
    assert a['source_metadata_revision']==b['source_metadata_revision']


def test_online_scenario_documentation_does_not_display_a_saved_readiness_block():
    from src.online_research_tools import run_online_scenario
    c=context(); result=run_online_scenario(c,parameters())
    updated=context(scenario=result)
    lane=next(l for l in updated['decision_lab']['lanes'] if l['key']=='scenario')
    assert lane['state']=='hypothetical_documented'
    assert 'hypothetical' in lane['answer'].lower()
    assert 'saved' in lane['evidence'].lower()


def test_foreign_validated_currency_stays_native_and_interim_cash_is_not_a_direct_quarter():
    from test_sec_industry_financials import _foreign
    from src.online_research_tools import run_online_scenario
    v=financial(); v.pop('annual_history'); v.pop('quarterly_history');v['status']='unavailable'
    v['foreign_financials']=_foreign()
    inventory=v['filing_inventory']; anchor=inventory['latest']['annual']
    anchor['form']='20-F';inventory['periods']['annual']=[anchor]
    inventory['periods']['quarterly']=[]; inventory['latest']['quarterly']=None
    inventory['earnings_reports']=[dict(accession='0000001234-26-000002',form='6-K',period_end=None,
        report_date='2026-08-01',filed='2026-08-01',accepted_at='2026-08-01T12:00:00Z',
        primary_document='quarter.htm',source_url='https://www.sec.gov/Archives/edgar/data/1234/000000123426000002/quarter.htm',
        amendment=False)]
    v['filing_inventory']=reseal_inventory(inventory)
    c=context(v)
    assert metric(c,'cfo_less_ppe')['value']==15
    assert metric(c,'cfo_less_ppe')['unit']=='EUR'
    assert metric(c,'cfo_less_ppe','quarterly','2026-06-30')['value'] is None
    assert metric(c,'cfo_less_ppe','interim','2026-06-30')['value']==9
    s=run_online_scenario(c,parameters(),assumed_net_debt=3,assumed_shares=2,
        capital_structure_basis={'currency':'USD','share_basis':'assumed_common_shares','label':'User'})
    assert s['currency']=='EUR' and s['enterprise_value'] is not None and s['equity_value'] is None


def test_outcomes_and_catalyst_records_require_the_same_issuer_scope_and_real_record_validation():
    from test_research_outcome_review import _outcome
    from test_catalyst_evidence_timeline import _event
    from src.company_research_notes import CompanyNotes, CompanyNotesScope
    scope=CompanyNotesScope('personal','FICT',CIK)
    outcome=_outcome(profile_key='personal',ticker='FICT')
    event=_event(profile_key='personal',ticker='FICT')
    c=context(notes=CompanyNotes(scope,(),(event,),(outcome,)))
    assert c['notes_summary']['outcome_count']==1
    assert next(l for l in c['decision_lab']['lanes'] if l['key']=='learning')['state']=='reviewed'
    assert c['forward_view']['user_catalysts'][0]['event_id']==event.event_id
    wrong=_event(profile_key='personal',ticker='OTHER')
    assert context(notes=CompanyNotes(scope,(),(wrong,),()))['notes_summary']['status']=='withheld'


def test_missing_contrary_evidence_is_explicit_research_work_not_invented_from_observed_metrics():
    c=context()
    assert c['decision_lab']['contrary_evidence']['status']=='not_started'
    assert 'contrary' in c['decision_lab']['contrary_evidence']['next_step'].lower()
    assert c['forward_view']['contrary_evidence']==[]


def financial_with_components():
    from test_online_filing_context import _facts
    from src.online_filing_context import build_online_earnings_components
    v=financial(); identity=v['companyfacts_identity']
    receipt={**identity,'status':'ready','payload':_facts()}
    v['earnings_components']=build_online_earnings_components(receipt,v['filing_inventory'],
        ticker='FICT',expected_cik=CIK,as_of=NOW)
    return v


def test_current_annual_components_retain_exact_current_anchor_and_personal_rights():
    c=context(financial_with_components())
    assert c['earnings_components']['status']=='inspection_only'
    assert c['earnings_components']['fields']['net_income']['value']==10
    assert c['earnings_components']['rights_status']=='personal_inspection_only'


def test_earnings_components_expire_and_never_restore_original_version_after_amendment():
    from datetime import timedelta
    from src.online_research_tools import build_online_research_context
    v=financial_with_components()
    stale=build_online_research_context(v,{},ticker='FICT',profile_key='personal',expected_cik=CIK,
        as_of=NOW+timedelta(hours=25))
    assert stale['earnings_components']['status']=='withheld'
    assert stale['earnings_components']['fields']=={}
    inventory=v['filing_inventory'];anchor=inventory['latest']['annual']
    revised={**anchor,'accession':'0000001234-26-000010','form':'10-K/A','amendment':True,
        'filed':'2026-10-01','accepted_at':'2026-10-01T12:00:00Z',
        'source_url':'https://www.sec.gov/Archives/edgar/data/1234/000000123426000010/annual.htm'}
    inventory['latest']['annual']=revised;inventory['periods']['annual'].append(revised)
    v['filing_inventory']=reseal_inventory(inventory)
    held=context(v)['earnings_components']
    assert held['status']=='withheld' and held['fields']=={}


@pytest.mark.parametrize('change',['schema','rights','promotion','currency','digest','concept','period','source','field_rights','accession'])
def test_malformed_annual_component_cache_fails_closed(change):
    v=financial_with_components();component=v['earnings_components'];field=component['fields']['net_income']
    if change=='schema':component['schema_version']='other'
    elif change=='rights':component['rights_status']='approved'
    elif change=='promotion':component['saved_readiness_promoted']=True
    elif change=='currency':component['currency']='EUR'
    elif change=='digest':component['source_receipts'][0]['payload_sha256']='f'*64
    elif change=='concept':field['concept']='MadeUpIncome'
    elif change=='period':field['period_start']='2024-01-01'
    elif change=='source':field['source_ref']='https://example.invalid/facts'
    elif change=='field_rights':field['rights_status']='approved'
    else:field['accession']='0000001234-26-000099'
    result=context(v)['earnings_components']
    assert result['status']=='withheld' and result['fields']=={}


@pytest.mark.parametrize('conflict',['expected_cik','financial_view_cik'])
def test_valid_earnings_source_packet_cannot_bypass_outer_company_identity_conflict(conflict):
    from src.online_research_tools import build_online_research_context
    v=financial_with_components()
    expected=CIK
    if conflict=='expected_cik':expected='0000009999'
    else:v['sec_cik']='0000009999'
    result=build_online_research_context(v,{},ticker='FICT',profile_key='personal',expected_cik=expected,as_of=NOW)
    assert result['status']=='withheld'
    assert result['earnings_components']['status']=='withheld'
    assert result['earnings_components']['fields']=={}
