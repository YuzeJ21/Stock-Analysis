from copy import deepcopy

import pytest

SOURCE='https://data.sec.gov/api/xbrl/companyfacts/CIK0000001234.json'
OBSERVED='2026-10-30T18:00:00Z'


def _fact(start,end,value,index):
    return {'start':start,'end':end,'val':value,'filed':['2025-05-01','2025-08-01','2025-11-01'][index],
            'form':'10-Q','accn':f'0000001234-25-00000{index+1}','fy':2025,'fp':f'Q{index+1}'}


def _quarter_payload():
    starts=['2025-01-01','2025-04-01','2025-07-01']; ends=['2025-03-31','2025-06-30','2025-09-30']
    revenue=[_fact(s,e,v,i) for i,(s,e,v) in enumerate(zip(starts,ends,[100,120,130]))]
    revenue += [_fact('2025-01-01',ends[i],v,i) for i,v in [(1,220),(2,350)]]
    facts={'Revenues':{'units':{'USD':revenue}},'OperatingIncomeLoss':{'units':{'USD':[
        _fact(s,e,v,i) for i,(s,e,v) in enumerate(zip(starts,ends,[10,12,13]))]}}}
    for tag,values in [('NetCashProvidedByUsedInOperatingActivities',[20,45,75]),('PaymentsToAcquirePropertyPlantAndEquipment',[5,12,20])]:
        facts[tag]={'units':{'USD':[_fact('2025-01-01',e,v,i) for i,(e,v) in enumerate(zip(ends,values))]}}
    return {'cik':1234,'entityName':'Fictional','facts':{'us-gaap':facts}}


def _build(payload=None,**kwargs):
    from src.sec_quarterly_history import build_sec_quarterly_history
    return build_sec_quarterly_history('FICT',payload or _quarter_payload(),expected_cik='0000001234',
        observed_at=OBSERVED,source_url=SOURCE,payload_sha256='a'*64,**kwargs)


def test_direct_quarters_and_cumulative_cash_are_kept_separate_without_derivation(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    result=_build()
    assert result['status']=='inspection_only'
    assert [p['fields']['revenue']['value'] for p in result['periods']]==[100,120,130]
    assert result['periods'][0]['fields']['cash_from_operations']['value']==20
    second=result['periods'][1]
    assert 'cash_from_operations' not in second['fields']
    assert second['withheld_fields']['cash_from_operations']=='only_cumulative_fact_available'
    assert second['cumulative_fields']['cash_from_operations']['value']==45
    assert second['cumulative_fields']['cash_from_operations']['period_start']=='2025-01-01'
    assert all(p.get('derived_values') in (None,{}) for p in result['periods'])
    assert result['history_basis']=='latest_reported_as_observed_not_point_in_time'
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('bad_value',[True,'120',float('nan'),float('inf')])
def test_bad_raw_quarter_value_cannot_be_replaced_by_an_older_success(bad_value):
    p=_quarter_payload(); rows=p['facts']['us-gaap']['Revenues']['units']['USD']
    rows.append({**rows[1],'val':bad_value,'filed':'2026-03-01','accn':'0000001234-26-000001'})
    second=_build(p)['periods'][1]
    assert second['status']=='withheld'
    assert not second['fields']


def test_conflicting_same_context_and_competing_starts_withhold_only_that_quarter():
    p=_quarter_payload(); rows=p['facts']['us-gaap']['Revenues']['units']['USD']
    rows.append({**rows[1],'val':999})
    assert [x['status'] for x in _build(p)['periods']]==['available','withheld','available']
    p=_quarter_payload(); rows=p['facts']['us-gaap']['Revenues']['units']['USD']
    rows.append({**rows[1],'start':'2025-04-02'})
    result=_build(p)
    assert len(result['periods'])==3 and result['periods'][1]['reason']=='ambiguous_quarter_context'


def test_latest_restatement_is_labelled_and_components_cannot_cross_accessions():
    p=_quarter_payload(); rows=p['facts']['us-gaap']['Revenues']['units']['USD']
    rows.append({**rows[1],'val':125,'filed':'2026-03-01','accn':'0000001234-26-000001'})
    second=_build(p)['periods'][1]
    assert second['fields']['revenue']['value']==125
    assert second['fields']['revenue']['filed']=='2026-03-01'
    assert 'operating_income' not in second['fields']
    assert not second['cumulative_fields']


def test_currency_identity_rights_and_unsupported_concepts_do_not_create_quarters(monkeypatch):
    p=_quarter_payload(); p['cik']=9999
    assert _build(p)['status']=='withheld'
    p=_quarter_payload(); p['facts']['us-gaap']['Revenues']['units']['EUR']=p['facts']['us-gaap']['Revenues']['units'].pop('USD')
    assert _build(p)['status']=='withheld'
    p=_quarter_payload(); p['facts']['us-gaap']['CustomRevenue']=p['facts']['us-gaap'].pop('Revenues')
    assert _build(p)['status']=='withheld'
    from src import sec_quarterly_history
    monkeypatch.setattr(sec_quarterly_history,'field_is_permitted',lambda _:False)
    assert _build()['status']=='withheld'


def test_no_missing_q4_is_invented_and_input_payload_is_unchanged():
    p=_quarter_payload(); before=deepcopy(p)
    result=_build(p,max_periods=2)
    assert [r['period_end'] for r in result['periods']]==['2025-06-30','2025-09-30']
    assert p==before


def _wrapped(history):
    return {'ticker':'FICT','quarterly_history':history,'companyfacts_identity':{
        'status':'source_matched','ticker':'FICT','sec_cik':'0000001234','source_url':SOURCE,
        'observed_at':OBSERVED,'payload_sha256':'a'*64}}


@pytest.mark.parametrize('change',['value','period','identity','digest','cumulative_start','extra_field','withheld_reason','row_reason'])
def test_display_boundary_rejects_malformed_or_cross_source_quarter_evidence(change):
    from src.sec_quarterly_history import validated_quarterly_history
    view=_wrapped(_build())
    assert validated_quarterly_history(view) is not None
    h=view['quarterly_history']; field=h['periods'][0]['fields']['revenue']
    if change=='value': field['value']=True
    elif change=='period': field['period_start']='2025-02-01'
    elif change=='identity': h['sec_cik']='0000009999'
    elif change=='digest': h['payload_sha256']='b'*64
    elif change=='cumulative_start': h['periods'][1]['cumulative_fields']['cash_from_operations']['period_start']='2025-04-01'
    elif change=='extra_field': h['periods'][0]['fields']['free_cash_flow']={'value':15}
    elif change=='withheld_reason': h['periods'][1]['withheld_fields']['cash_from_operations']={'bad':'reason'}
    else:
        h['periods'][0].update(status='withheld',fields={},cumulative_fields={},cumulative_anchor=None,reason={'bad':'reason'})
    assert validated_quarterly_history(view) is None


def test_shared_fetch_keeps_quarterly_evidence_when_annual_anchor_is_unsupported(monkeypatch):
    import json
    from src import online_sec_receipt
    from src.company_sec_online_preview import get_company_sec_annual_preview
    calls=[]
    def fetch(url,agent):
        calls.append(url)
        body={'0':{'ticker':'FICT','cik_str':1234,'title':'Fictional'}} if 'company_tickers.json' in url else _quarter_payload()
        return json.dumps(body).encode(),{},url
    monkeypatch.setattr(online_sec_receipt,'_fetch_raw',fetch)
    session={}
    result=get_company_sec_annual_preview('FICT',session,refresh_requested=True,user_agent='Research contact')
    assert result['status']=='unavailable'
    assert result['quarterly_history']['periods'][1]['fields']['revenue']['value']==120
    assert result['companyfacts_identity']['sec_cik']=='0000001234'
    assert len(calls)==2
    cached=get_company_sec_annual_preview('FICT',session,refresh_requested=False,user_agent='Research contact')
    assert cached['quarterly_history']['periods'][1]['cumulative_fields']['cash_from_operations']['value']==45
    assert len(calls)==2


def test_malformed_optional_anchor_and_unbounded_cik_are_withheld_without_crashing():
    assert _build(anchor_concept=['us-gaap','Revenues'])['status']=='withheld'
    p=_quarter_payload(); p['cik']='1'*5000
    assert _build(p)['status']=='withheld'


def test_newer_supported_quarter_definition_is_not_hidden_by_an_old_annual_concept():
    p=_quarter_payload()
    p['facts']['us-gaap']['RevenueFromContractWithCustomerExcludingAssessedTax']={'units':{'USD':[
        {'start':'2026-07-01','end':'2026-09-30','filed':'2026-10-20','form':'10-Q','accn':'0000001234-26-000002','val':200}]}}
    h=_build(p,anchor_concept=('us-gaap','Revenues'))
    assert h['periods'][-1]['period_end']=='2026-09-30'
    assert h['concept']=='RevenueFromContractWithCustomerExcludingAssessedTax'


def test_latest_reported_quarter_gap_is_visible_instead_of_substituting_a_decade_old_concept():
    p=_quarter_payload()
    p['facts']['us-gaap']['UnsupportedIndustryRevenue']={'units':{'USD':[
        {'start':'2026-07-01','end':'2026-09-30','filed':'2026-10-20','form':'10-Q','accn':'0000001234-26-000002','val':200}]}}
    h=_build(p)
    assert h['periods'][-1]['period_end']=='2026-09-30'
    assert h['periods'][-1]['status']=='withheld'
    assert h['periods'][-1]['reason']=='latest_reported_quarter_revenue_unavailable'
