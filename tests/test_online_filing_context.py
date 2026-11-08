"""Constructed filing lifecycle and standard annual inspection evidence."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json

import pytest

from src.online_filing_context import (
    build_filing_inventory, validated_filing_inventory,
    corroborate_online_financials, build_online_earnings_components,
)

NOW = datetime(2026, 11, 8, 12, tzinfo=timezone.utc)
CIK = '0000001234'
PROFILE = f'https://data.sec.gov/submissions/CIK{CIK}.json'
FACTS = f'https://data.sec.gov/api/xbrl/companyfacts/CIK{CIK}.json'


def _filing(end='2025-12-31', filed='2026-03-01', accession='0000001234-26-000001', form='10-K', **changes):
    return dict(accessionNumber=accession, form=form, reportDate=end, filingDate=filed,
                acceptanceDateTime=filed+'T12:00:00Z', primaryDocument='report.htm', **changes)


def _profile(rows=None):
    rows = [_filing()] if rows is None else rows
    columns = ('accessionNumber','form','reportDate','filingDate','acceptanceDateTime','primaryDocument')
    if any('items' in r for r in rows):
        columns += ('items',)
        rows = [{**r, 'items': r.get('items', '')} for r in rows]
    return dict(cik=1234, tickers=['FICT'], name='Fictional Company', sic='3571', entityType='operating',
                fiscalYearEnd='1231', filings={'recent':{key:[r[key] for r in rows] for key in columns}})


def _receipt(payload, url=PROFILE):
    return dict(status='ready', payload=payload, source_url=url, observed_at='2026-11-08T12:00:00Z',
                source_last_modified=None, payload_sha256=hashlib.sha256(json.dumps(payload).encode()).hexdigest())


def _inventory(rows=None):
    return build_filing_inventory(_receipt(_profile(rows)), ticker='FICT', expected_cik=CIK, as_of=NOW)


def _financial():
    from test_sec_annual_history import _payload, _view
    from src.sec_annual_history import build_sec_annual_history
    from src.sec_quarterly_history import build_sec_quarterly_history
    payload = _payload()
    view = _view(payload)
    # Use one explicit current observation for all source-bound validators.
    view['retrieved_at_utc'] = '2026-11-08T12:00:00Z'
    for field in view['approved_direct_fields']:
        field['observed_at_utc'] = view['retrieved_at_utc']
    view['companyfacts_identity'] = dict(status='source_matched', ticker='FICT', sec_cik=CIK,
        source_url=FACTS, observed_at=view['retrieved_at_utc'], payload_sha256='a'*64,
        association_source_url='https://www.sec.gov/files/company_tickers.json',
        association_payload_sha256='b'*64, association_observed_at=view['retrieved_at_utc'])
    view['annual_history'] = build_sec_annual_history(view, payload)
    view['quarterly_history'] = build_sec_quarterly_history('FICT',payload,expected_cik=CIK,
        observed_at=view['retrieved_at_utc'],source_url=FACTS,payload_sha256='a'*64)
    return view


def _facts():
    concepts = {'NetIncomeLoss':10, 'EarningsPerShareDiluted':1, 'ShareBasedCompensation':3,
                'AmortizationOfIntangibleAssets':2, 'GainLossOnSaleOfBusiness':4}
    return dict(cik=1234, facts={'us-gaap':{name:{'units':{'USD/shares' if name=='EarningsPerShareDiluted' else 'USD':[
        dict(start='2025-01-01',end='2025-12-31',filed='2026-03-01',form='10-K',
             accn='0000001234-26-000001',val=value,fp='FY',fy=2025)]}} for name,value in concepts.items()}})


def test_inventory_retains_period_versions_and_selects_report_period_before_filing_recency():
    rows = [_filing(), _filing('2024-12-31','2026-10-01','0000001234-26-000010','10-K/A'),
            _filing('2026-06-30','2026-08-01','0000001234-26-000020','10-Q')]
    before = deepcopy(rows)
    inventory = _inventory(rows)
    assert inventory['status'] == 'inspection_only'
    assert inventory['schema_version'] == 'online-filing-inventory-v1'
    assert inventory['latest']['annual']['period_end'] == '2025-12-31'
    assert inventory['latest']['quarterly']['period_end'] == '2026-06-30'
    assert len(inventory['periods']['annual']) == 2
    assert inventory['issuer'] == dict(name='Fictional Company',sic='3571',entity_type='operating',fiscal_year_end='1231')
    assert inventory['source_receipt']['payload_sha256'] != inventory['normalized_sha256']
    assert inventory['saved_readiness_promoted'] is False and inventory['commercial_eligible'] is False
    assert rows == before
    assert validated_filing_inventory(json.loads(json.dumps(inventory)),ticker='FICT',expected_cik=CIK,as_of=NOW) == inventory


def test_same_period_latest_amendment_is_current_without_replacing_other_periods():
    inventory = _inventory([_filing(),_filing(filed='2026-10-01',accession='0000001234-26-000010',form='10-K/A')])
    assert inventory['latest']['annual']['amendment'] is True
    assert inventory['latest']['annual']['accession'] == '0000001234-26-000010'
    assert len(inventory['periods']['annual']) == 2


@pytest.mark.parametrize('change', ['cik','source','digest','date','acceptance','document','schema','form_type'])
def test_invalid_profile_identity_metadata_and_paths_fail_closed(change):
    receipt = _receipt(_profile())
    recent = receipt['payload']['filings']['recent']
    if change=='cik': receipt['payload']['cik']=9999
    elif change=='source': receipt['source_url']=PROFILE+'?other=1'
    elif change=='digest': receipt['payload_sha256']='bad'
    elif change=='date': recent['reportDate']=['2026-12-31']
    elif change=='acceptance': recent['acceptanceDateTime']=['2026-03-01T12:00:00']
    elif change=='document': recent['primaryDocument']=['../outside.htm']
    elif change=='schema': recent['reportDate']=[]
    else: recent['form']=[{'form':'10-K'}]
    assert build_filing_inventory(receipt,ticker='FICT',expected_cik=CIK,as_of=NOW)['status']=='withheld'


@pytest.mark.parametrize('age_seconds', [-1,86401])
def test_inventory_freshness_and_historical_replay_are_explicit(age_seconds):
    receipt = _receipt(_profile())
    receipt['observed_at']=(NOW-timedelta(seconds=age_seconds)).strftime('%Y-%m-%dT%H:%M:%SZ')
    assert build_filing_inventory(receipt,ticker='FICT',expected_cik=CIK,as_of=NOW)['status']=='withheld'
    inventory = _inventory()
    later = NOW+timedelta(days=2)
    assert validated_filing_inventory(inventory,ticker='FICT',expected_cik=CIK,as_of=later) is None
    assert validated_filing_inventory(inventory,ticker='FICT',expected_cik=CIK,as_of=later,allow_historical=True)


@pytest.mark.parametrize('change', ['identity','period','source_path','promotion','seal','normalized_digest'])
def test_cached_inventory_rejects_tamper_even_when_structural_content_is_resealed(change):
    inventory = _inventory()
    if change=='identity': inventory['ticker']='OTHER'
    elif change=='period': inventory['periods']['annual'][0]['period_end']='2027-01-01'
    elif change=='source_path': inventory['periods']['annual'][0]['source_url']='https://example.com/report.htm'
    elif change=='promotion': inventory['commercial_eligible']=True
    elif change=='seal': inventory['packet_digest']='0'*64
    else: inventory['normalized_sha256']='0'*64
    if change not in {'seal','normalized_digest'}:
        inventory['packet_digest']=hashlib.sha256(json.dumps({k:v for k,v in inventory.items() if k!='packet_digest'},sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    assert validated_filing_inventory(inventory,ticker='FICT',expected_cik=CIK,as_of=NOW) is None


def test_comparative_annual_facts_can_use_later_known_primary_filing():
    inventory = _inventory([_filing(),_filing('2024-12-31','2025-03-01','0000001234-25-000001')])
    financial = _financial(); before = deepcopy(financial)
    coverage = corroborate_online_financials(financial,inventory,as_of=NOW)
    assert coverage['current']['annual']['status']=='corroborated'
    assert coverage['periods']['annual']['2024-12-31']['status']=='corroborated'
    assert coverage['periods']['annual']['2024-12-31']['reason']=='comparative_fact_in_later_known_filing'
    assert financial==before


def test_old_period_amendment_holds_only_that_period():
    inventory = _inventory([_filing(),_filing('2024-12-31','2026-10-01','0000001234-26-000010','10-K/A')])
    coverage = corroborate_online_financials(_financial(),inventory,as_of=NOW)
    assert coverage['current']['annual']['status']=='corroborated'
    assert coverage['periods']['annual']['2024-12-31']['status']=='amendment_unresolved'


def test_new_report_without_structured_facts_is_pending_despite_fresh_download():
    inventory = _inventory([_filing(),_filing('2026-06-30','2026-08-01','0000001234-26-000020','10-Q')])
    coverage = corroborate_online_financials(_financial(),inventory,as_of=NOW)
    assert coverage['current']['quarterly']['status']=='facts_pending'
    assert coverage['current']['quarterly']['anchor']['period_end']=='2026-06-30'
    assert coverage['current']['annual']['status']=='corroborated'


def test_current_amendment_does_not_restore_old_primary_facts():
    inventory = _inventory([_filing(),_filing(filed='2026-10-01',accession='0000001234-26-000010',form='10-K/A')])
    assert corroborate_online_financials(_financial(),inventory,as_of=NOW)['current']['annual']['status']=='amendment_unresolved'


def test_invalid_or_stale_financial_identity_withholds_corroboration():
    financial = _financial(); financial['companyfacts_identity']['sec_cik']='0000009999'
    assert corroborate_online_financials(financial,_inventory(),as_of=NOW)['current']['annual']['status']=='withheld'
    financial = _financial(); financial['companyfacts_identity']['observed_at']='2026-11-06T12:00:00Z'
    assert corroborate_online_financials(financial,_inventory(),as_of=NOW)['current']['annual']['status']=='withheld'
    assert corroborate_online_financials(_financial(),{'status':'withheld'},as_of=NOW)['current']['annual']['status']=='withheld'


def test_generic_annual_components_remain_separate_personal_inspection():
    receipt = _receipt(_facts(),FACTS); before=deepcopy(receipt)
    result = build_online_earnings_components(receipt,_inventory(),ticker='FICT',expected_cik=CIK,as_of=NOW)
    assert result['status']=='inspection_only'
    assert set(result['fields'])=={'net_income','diluted_eps','stock_based_compensation','intangible_amortization','disposal_gain'}
    assert result['fields']['net_income']['value']==10
    assert result['fields']['diluted_eps']['unit']=='USD/shares'
    assert result['withheld_fields']=={}
    assert result['commercial_eligible'] is False and result['saved_readiness_promoted'] is False
    assert all(f['rights_status']=='personal_inspection_only' for f in result['fields'].values())
    assert receipt==before


@pytest.mark.parametrize('change', ['version','duration','unit','conflict','concept','nonfinite','period_start'])
def test_annual_component_conflicts_withhold_individual_fields(change):
    payload=_facts(); fact=payload['facts']['us-gaap']['NetIncomeLoss']; row=fact['units']['USD'][0]
    if change=='version': row['accn']='0000001234-25-000001'
    elif change=='duration': row['start']='2025-10-01'
    elif change=='unit': fact['units']['EUR']=fact['units'].pop('USD')
    elif change=='conflict': fact['units']['USD'].append({**row,'val':999})
    elif change=='concept': payload['facts']['us-gaap']['ProfitLoss']=deepcopy(fact)
    elif change=='nonfinite': row['val']=float('inf')
    else: row['start']='2025-01-02'
    result=build_online_earnings_components(_receipt(payload,FACTS),_inventory(),ticker='FICT',expected_cik=CIK,as_of=NOW)
    assert 'net_income' not in result['fields']
    assert 'net_income' in result['withheld_fields']
    assert result['fields']['diluted_eps']['value']==1
    json.dumps(result,allow_nan=False)


def test_new_annual_components_never_substitute_older_accession():
    inventory=_inventory([_filing(),_filing(filed='2026-10-01',accession='0000001234-26-000010',form='10-K/A')])
    result=build_online_earnings_components(_receipt(_facts(),FACTS),inventory,ticker='FICT',expected_cik=CIK,as_of=NOW)
    assert result['fields']=={}
    assert len(result['withheld_fields'])==5


def test_earnings_reports_are_review_triggers_without_financial_period_invention():
    inventory=_inventory([_filing(),_filing('2026-10-31','2026-11-01','0000001234-26-000031','8-K',items='2.02')])
    assert inventory['latest']['annual']['period_end']=='2025-12-31'
    assert inventory['latest']['quarterly'] is None
    assert any(t['trigger_type']=='reported_earnings_filing' for t in inventory['review_triggers'])


def test_older_period_ambiguous_versions_do_not_hold_current_annual():
    inventory = _inventory([_filing(),
        _filing('2024-12-31','2026-10-01','0000001234-26-000010','10-K/A'),
        _filing('2024-12-31','2026-10-01','0000001234-26-000011','10-K/A')])
    coverage = corroborate_online_financials(_financial(),inventory,as_of=NOW)
    assert inventory['status']=='inspection_only'
    assert coverage['current']['annual']['status']=='corroborated'
    assert coverage['periods']['annual']['2024-12-31']['status']=='withheld'
    assert coverage['periods']['annual']['2024-12-31']['reason']=='ambiguous_filing_version'


def test_utc_acceptance_can_be_day_after_us_filing_date():
    row = _filing()
    row['acceptanceDateTime']='2026-03-02T00:30:00Z'
    assert _inventory([row])['status']=='inspection_only'


def test_newer_revision_of_comparative_source_does_not_corroborate_old_source():
    inventory = _inventory([_filing(),
        _filing(filed='2026-10-01',accession='0000001234-26-000010',form='10-K/A'),
        _filing('2024-12-31','2025-03-01','0000001234-25-000001')])
    coverage = corroborate_online_financials(_financial(),inventory,as_of=NOW)
    assert coverage['periods']['annual']['2024-12-31']['status']!='corroborated'


def test_quarterly_primary_facts_match_current_quarter_inventory():
    from test_sec_quarterly_history import _quarter_payload as quarter_payload
    from src.sec_quarterly_history import build_sec_quarterly_history
    financial=_financial()
    payload=quarter_payload()
    financial['quarterly_history']=build_sec_quarterly_history('FICT',payload,expected_cik=CIK,
        observed_at=financial['retrieved_at_utc'],source_url=FACTS,payload_sha256='a'*64)
    latest=financial['quarterly_history']['periods'][-1]
    inventory=_inventory([_filing(),_filing(latest['period_end'],latest['filed'],latest['accession'],latest['form'])])
    coverage=corroborate_online_financials(financial,inventory,as_of=NOW)
    assert coverage['current']['quarterly']['status']=='corroborated'


def test_comparative_period_need_not_be_listed_in_recent_submissions():
    coverage=corroborate_online_financials(_financial(),_inventory(),as_of=NOW)
    assert coverage['periods']['annual']['2023-12-31']['status']=='corroborated'
    assert coverage['periods']['annual']['2023-12-31']['reason']=='comparative_fact_in_later_known_filing'


def test_current_annual_fallback_uses_validated_field_duration():
    financial=_financial(); financial.pop('annual_history')
    assert corroborate_online_financials(financial,_inventory(),as_of=NOW)['current']['annual']['status']=='corroborated'


def test_validator_rejects_bad_source_path_after_both_seals_are_recomputed():
    inventory=_inventory()
    for anchor in (inventory['periods']['annual'][0],inventory['latest']['annual']):
        anchor['primary_document']='../../report.htm'
        anchor['source_url']='https://www.sec.gov/Archives/edgar/data/1234/000000123426000001/../../report.htm'
    for trigger in inventory['review_triggers']:
        trigger['anchor']=deepcopy(inventory['latest']['annual'])
    normalized={k:inventory[k] for k in ('issuer','latest','periods','earnings_reports','review_triggers')}
    inventory['normalized_sha256']=hashlib.sha256(json.dumps(normalized,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    inventory['packet_digest']=hashlib.sha256(json.dumps({k:v for k,v in inventory.items() if k!='packet_digest'},sort_keys=True,separators=(',',':')).encode()).hexdigest()
    assert validated_filing_inventory(inventory,ticker='FICT',expected_cik=CIK,as_of=NOW) is None


def test_annual_inspection_supports_standard_ifrs_without_company_policy():
    payload=dict(cik=1234,facts={'ifrs-full':{}})
    for name,value in {'ProfitLoss':10,'DilutedEarningsLossPerShare':1,'SharebasedPaymentExpense':3,'AmortisationOfIntangibleAssets':2}.items():
        unit='EUR/shares' if name=='DilutedEarningsLossPerShare' else 'EUR'
        payload['facts']['ifrs-full'][name]={'units':{unit:[dict(start='2025-01-01',end='2025-12-31',
            filed='2026-03-01',form='20-F',accn='0000001234-26-000001',val=value)]}}
    result=build_online_earnings_components(_receipt(payload,FACTS),_inventory([_filing(form='20-F')]),ticker='FICT',expected_cik=CIK,as_of=NOW)
    assert result['currency']=='EUR'
    assert result['fields']['net_income']['taxonomy']=='ifrs-full'
    assert result['fields']['diluted_eps']['value']==1
    assert result['withheld_fields']['disposal_gain']=='matching_current_annual_fact_unavailable'


def test_all_fields_hold_when_annual_durations_are_ambiguous():
    payload=_facts()
    payload['facts']['us-gaap'].pop('GainLossOnSaleOfBusiness')
    for name in ('NetIncomeLoss','ShareBasedCompensation'):
        payload['facts']['us-gaap'][name]['units']['USD'][0]['start']='2025-01-02'
    result=build_online_earnings_components(_receipt(payload,FACTS),_inventory(),ticker='FICT',expected_cik=CIK,as_of=NOW)
    assert result['status']=='withheld'
    assert result['fields']=={}
    assert result['period_start'] is None


def test_newer_unknown_annual_fact_version_cannot_leave_exact_older_field_current():
    payload=_facts(); rows=payload['facts']['us-gaap']['NetIncomeLoss']['units']['USD']
    rows.append({**rows[0],'accn':'0000001234-26-000999','filed':'2026-10-01','val':999})
    result=build_online_earnings_components(_receipt(payload,FACTS),_inventory(),ticker='FICT',expected_cik=CIK,as_of=NOW)
    assert 'net_income' not in result['fields']
    assert result['withheld_fields']['net_income']=='newer_or_unresolved_annual_fact_version'
    assert result['fields']['diluted_eps']['value']==1


def test_commercial_mode_cannot_unlock_generic_observations(monkeypatch):
    monkeypatch.setenv('COMMERCIAL_RESEARCH_MODE','1')
    assert _inventory()['status']=='withheld'
    assert build_online_earnings_components(_receipt(_facts(),FACTS),_inventory(),ticker='FICT',expected_cik=CIK,as_of=NOW)['status']=='withheld'


def test_current_report_missing_event_date_does_not_hold_financial_inventory():
    inventory=_inventory([_filing(),_filing('','2026-11-01','0000001234-26-000031','6-K')])
    assert inventory['status']=='inspection_only'
    assert inventory['latest']['annual']['period_end']=='2025-12-31'
    assert inventory['latest']['quarterly'] is None
    assert inventory['earnings_reports'][0]['report_date'] is None
    assert inventory['review_triggers'][-1]['trigger_type']=='current_report_filing'
    assert validated_filing_inventory(inventory,ticker='FICT',expected_cik=CIK,as_of=NOW)


def test_sec_acceptance_precedes_official_filing_date_across_weekend():
    row=_filing('2025-12-31','2026-03-02')
    row['acceptanceDateTime']='2026-02-27T23:44:31Z'
    assert _inventory([row])['status']=='inspection_only'
