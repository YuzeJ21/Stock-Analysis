"""Constructed SEC evidence; no live financial observations are distributed."""
import base64
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json

import pytest


NOW = datetime(2026, 11, 7, 15, tzinfo=timezone.utc)
STAMP = '2026-11-07T15:00:00Z'
SCOPE = {
    'MRVL': dict(cik='0001835632', accession='0001835632-26-000011', start='2025-02-02',
                 end='2026-01-31', filed='2026-03-11', document='mrvl-20260131.htm'),
    'AVGO': dict(cik='0001730168', accession='0001730168-25-000121', start='2024-11-04',
                 end='2025-11-02', filed='2025-12-18', document='avgo-20251102.htm'),
}
CONCEPTS = {
    'EarningsPerShareDiluted': ('USD/shares', 1.25), 'NetIncomeLoss': ('USD', 100),
    'NetCashProvidedByUsedInOperatingActivities': ('USD', 180),
    'PaymentsToAcquirePropertyPlantAndEquipment': ('USD', 20),
    'ShareBasedCompensation': ('USD', 30), 'AmortizationOfIntangibleAssets': ('USD', 40),
    'GainLossOnSaleOfBusiness': ('USD', 70),
}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def receipt(url, body):
    return dict(status='ready', source_url=url, observed_at=STAMP,
                payload=body, payload_sha256=hashlib.sha256(json.dumps(body).encode()).hexdigest())


def raw_facts():
    s = SCOPE['MRVL']
    fields = {name: {'units': {unit: [dict(val=value, start=s['start'], end=s['end'],
        accn=s['accession'], form='10-K', filed=s['filed'], fp='FY', fy=2026)]}}
        for name, (unit, value) in CONCEPTS.items()}
    return receipt('https://data.sec.gov/api/xbrl/companyfacts/CIK0001835632.json',
                   dict(cik=1835632, facts={'us-gaap': fields}))


def raw_profile(ticker):
    s = SCOPE[ticker]
    row = dict(form='10-K', reportDate=s['end'], filingDate=s['filed'],
        accessionNumber=s['accession'], primaryDocument=s['document'],
        acceptanceDateTime=s['filed']+'T12:00:00Z', isInlineXBRL=1, isXBRL=1)
    return receipt(f'https://data.sec.gov/submissions/CIK{s["cik"]}.json',
        dict(cik=int(s['cik']), tickers=[ticker], filings={'recent': {k: [v] for k, v in row.items()}}))


def document(ticker, *, business=None, cik=None, form='10-K', end=None):
    s = SCOPE[ticker]
    business = business if business is not None else (
        'Companies that compete directly with our businesses include Broadcom.' if ticker == 'MRVL' else
        'We have two reportable segments: semiconductor solutions and infrastructure software.')
    body = f'''<html xmlns="http://www.w3.org/1999/xhtml"
        xmlns:ix="http://www.xbrl.org/2013/inlineXBRL"
        xmlns:xbrli="http://www.xbrl.org/2003/instance"
        xmlns:dei="http://xbrl.sec.gov/dei/2025"><head/><body>
        <xbrli:context id="annual"><xbrli:entity><xbrli:identifier scheme="http://www.sec.gov/CIK">{cik or s['cik']}</xbrli:identifier></xbrli:entity>
        <xbrli:period><xbrli:startDate>{s['start']}</xbrli:startDate><xbrli:endDate>{end or s['end']}</xbrli:endDate></xbrli:period></xbrli:context>
        <ix:nonNumeric name="dei:EntityCentralIndexKey" contextRef="annual">{cik or s['cik']}</ix:nonNumeric>
        <ix:nonNumeric name="dei:DocumentType" contextRef="annual">{form}</ix:nonNumeric>
        <ix:nonNumeric name="dei:DocumentPeriodEndDate" contextRef="annual">{end or s['end']}</ix:nonNumeric>
        <h2>Competition and Business</h2><p>{business}</p></body></html>'''.encode()
    return dict(status='ready', source_url=f'https://www.sec.gov/Archives/edgar/data/{int(s["cik"])}/{s["accession"].replace("-", "")}/{s["document"]}',
        observed_at=STAMP, payload_sha256=hashlib.sha256(body).hexdigest(),
        payload_raw_base64=base64.b64encode(body).decode())


def packet():
    from src.mrvl_earnings_review import normalize_review_facts, normalize_review_profile, seal_review_packet
    return seal_review_packet(dict(schema_version='mrvl-earnings-review-v1', ticker='MRVL',
        sec_cik='0001835632', observed_at=STAMP, facts=normalize_review_facts(raw_facts()),
        profiles={t: normalize_review_profile(raw_profile(t)) for t in SCOPE},
        documents={t: document(t) for t in SCOPE}))


def seal(p):
    from src.mrvl_earnings_review import seal_review_packet
    return seal_review_packet(p)


def build(p=None, **kwargs):
    from src.mrvl_earnings_review import build_mrvl_earnings_review
    return build_mrvl_earnings_review(packet() if p is None else p, as_of=NOW, **kwargs)


def rewrite_facts(p, mutate):
    from src.mrvl_earnings_review import normalize_review_facts
    r=raw_facts(); mutate(r['payload']['facts']['us-gaap'])
    # Fixtures simulate a distinct genuine source receipt, not altered cache data.
    r['payload_sha256']=digest(r['payload'])
    p['facts']=normalize_review_facts(r)
    return seal(p)


def test_exact_annual_review_retains_all_seven_values_and_research_relationship():
    p=packet(); before=deepcopy(p); result=build(p)
    assert result['status']=='inspection_only' and result['quality']['status']=='inspection_only'
    assert {r['concept']:r['value'] for r in result['quality']['fields']} == {
        'EarningsPerShareDiluted':1.25, 'NetIncomeLoss':100,
        'NetCashProvidedByUsedInOperatingActivities':180,
        'PaymentsToAcquirePropertyPlantAndEquipment':20, 'ShareBasedCompensation':30,
        'AmortizationOfIntangibleAssets':40, 'GainLossOnSaleOfBusiness':70}
    assert all(r['status']=='available' and r['period_start']=='2025-02-02' and
        r['period_end']=='2026-01-31' and r['accession']=='0001835632-26-000011'
        for r in result['quality']['fields'])
    peer=result['peer_context']
    assert peer['relationship_supported'] is True and peer['business_mix_difference'] is True
    assert peer['period_end_gap_days']==90 and peer['fiscal_window_days']==35
    assert peer['numerical_admission']=='not_granted' and peer['reason']=='peer_fiscal_window_differs'
    assert 'adjusted_after_tax_reconciliation_unresolved' in result['quality']['gaps']
    assert not {'adjusted_eps','free_cash_flow','multiple','peer_ready','recommendation'} & set(result)
    assert p==before and len(result['source_refs'])==5
    assert all('payload' not in r and 'payload_raw_base64' not in r for r in result['source_refs'])


@pytest.mark.parametrize('change', ['cik','expected_cik','schema','ticker','digest','stale','future','facts_url','normalized_digest','facts_cik'])
def test_cached_or_routed_source_changes_withhold_review(change):
    p=packet(); kwargs={}
    if change=='cik':p['sec_cik']='0001730168'
    elif change=='expected_cik':kwargs['expected_cik']='0001730168'
    elif change=='schema':p['schema_version']='unknown'
    elif change=='ticker':p['ticker']='AVGO'
    elif change=='digest':p['facts']['payload']['facts']['us-gaap']['NetIncomeLoss']['units']['USD'][0]['val']=999
    elif change=='stale':p['observed_at']='2026-11-06T14:59:59Z'
    elif change=='future':p['facts']['observed_at']='2026-11-07T15:00:01Z'
    elif change=='facts_url':p['facts']['source_url']='https://example.com/facts'
    elif change=='normalized_digest':p['facts']['normalized_sha256']='0'*64
    elif change=='facts_cik':p['facts']['payload']['cik']=1730168;p['facts']['normalized_sha256']=digest(p['facts']['payload'])
    if change!='digest':p=seal(p)
    result=build(p,**kwargs)
    assert result['status']=='withheld' and all(r['value'] is None for r in result['quality']['fields'])


@pytest.mark.parametrize('change',['accession','form','filed','start','end','unit','missing','conflict','nonfinite','boolean','quarter','continuing'])
def test_each_bad_observation_leaves_its_own_gap_without_zero_or_other_substitution(change):
    def mutate(facts):
        field=facts['NetCashProvidedByUsedInOperatingActivities']; row=field['units']['USD'][0]
        if change=='accession':row['accn']='0001835632-26-000099'
        elif change=='form':row['form']='10-K/A'
        elif change=='filed':row['filed']='2026-03-12'
        elif change=='start':row['start']='2025-02-03'
        elif change=='end':row['end']='2026-01-30'
        elif change=='unit':field['units']={'EUR':[row]}
        elif change=='missing':del facts['NetCashProvidedByUsedInOperatingActivities']
        elif change=='conflict':field['units']['USD'].append({**row,'val':181})
        elif change=='nonfinite':row['val']=float('nan')
        elif change=='boolean':row['val']=True
        elif change=='quarter':row['start']='2025-11-02';row['fp']='Q4'
        elif change=='continuing':facts['NetCashProvidedByUsedInOperatingActivitiesContinuingOperations']=facts.pop('NetCashProvidedByUsedInOperatingActivities')
    p=packet()
    if change=='nonfinite':
        # A number overflow in a decoded source remains an individual field gap.
        r=raw_facts(); mutate(r['payload']['facts']['us-gaap'])
        from src.mrvl_earnings_review import normalize_review_facts
        p['facts']=normalize_review_facts(r)
        result=build(seal(p))
        assert result['quality']['status']=='partial'
        assert sum(row['status']=='available' for row in result['quality']['fields'])==6
        assert next(row for row in result['quality']['fields'] if row['field']=='cash_from_operations')['value'] is None
        return
    result=build(rewrite_facts(p,mutate)); rows=result['quality']['fields']
    held=next(r for r in rows if r['field']=='cash_from_operations')
    assert held['status']=='withheld' and held['value'] is None and held['reason']
    assert sum(r['status']=='available' for r in rows)==6


def test_reported_losses_and_negative_cash_flow_are_preserved():
    def mutate(facts):
        for name,unit in [('NetIncomeLoss','USD'),('EarningsPerShareDiluted','USD/shares'),('NetCashProvidedByUsedInOperatingActivities','USD')]:
            facts[name]['units'][unit][0]['val']=-3
    result=build(rewrite_facts(packet(),mutate))
    assert [r['value'] for r in result['quality']['fields'][:3]]==[-3,-3,-3]


@pytest.mark.parametrize('ticker',['MRVL','AVGO'])
@pytest.mark.parametrize('change',['new_annual','amendment','wrong_filed','wrong_accession','wrong_document','issuer','ticker','ambiguous','malformed'])
def test_unsupported_latest_annual_never_falls_back_to_the_named_old_version(ticker,change):
    from src.mrvl_earnings_review import normalize_review_profile
    p=packet(); r=raw_profile(ticker); body=r['payload']; recent=body['filings']['recent']
    if change in {'new_annual','amendment','ambiguous'}:
        row={k:v[0] for k,v in recent.items()}
        row.update(form='10-K/A' if change=='amendment' else '10-K', accessionNumber='0000000001-26-000099',
            filingDate='2026-10-01',acceptanceDateTime='2026-10-01T12:00:00Z')
        if change=='new_annual':row['reportDate']='2026-09-01'
        if change=='ambiguous':row['filingDate']=recent['filingDate'][0];row['acceptanceDateTime']=recent['acceptanceDateTime'][0]
        for k,v in row.items():recent[k].append(v)
    elif change=='wrong_filed':recent['filingDate'][0]='2026-04-01'
    elif change=='wrong_accession':recent['accessionNumber'][0]='0000000001-26-000099'
    elif change=='wrong_document':recent['primaryDocument'][0]='other.htm'
    elif change=='issuer':body['cik']=1
    elif change=='ticker':body['tickers']=['OTHER']
    elif change=='malformed':recent['filingDate']=[]
    r['payload_sha256']=digest(body);p['profiles'][ticker]=normalize_review_profile(r)
    result=build(seal(p));assert result['peer_context']['status']=='withheld'
    if ticker=='MRVL':assert result['quality']['status']=='withheld'
    else:assert result['quality']['status']=='inspection_only'


@pytest.mark.parametrize('ticker',['MRVL','AVGO'])
@pytest.mark.parametrize('change',['digest','url','issuer','form','end','unavailable','unrelated_text','metadata_context'])
def test_annual_document_proof_is_required_without_erasing_independent_numeric_evidence(ticker,change):
    p=packet()
    if change=='issuer':p['documents'][ticker]=document(ticker,cik='0000000001')
    elif change=='form':p['documents'][ticker]=document(ticker,form='10-Q')
    elif change=='end':p['documents'][ticker]=document(ticker,end='2025-01-01')
    elif change=='unavailable':p['documents'][ticker]={'status':'unavailable','reason':'sec_document_unavailable'}
    elif change=='unrelated_text':p['documents'][ticker]=document(ticker,business='Broadcom acquired assets. Semiconductor and infrastructure are markets.')
    elif change=='digest':p['documents'][ticker]['payload_sha256']='0'*64
    elif change=='url':p['documents'][ticker]['source_url']='https://example.com/annual.htm'
    elif change=='metadata_context':
        raw=base64.b64decode(p['documents'][ticker]['payload_raw_base64']).replace(b'contextRef="annual"',b'contextRef="missing"')
        p['documents'][ticker]['payload_raw_base64']=base64.b64encode(raw).decode();p['documents'][ticker]['payload_sha256']=hashlib.sha256(raw).hexdigest()
    result=build(seal(p))
    assert result['peer_context']['status']=='withheld' and result['peer_context']['numerical_admission']=='not_granted'
    assert result['quality']['status']=='inspection_only'


@pytest.mark.parametrize('mode',['1','bad'])
def test_mode_guard_blocks_all_research_receipts(monkeypatch,mode):
    monkeypatch.setenv('COMMERCIAL_RESEARCH_MODE',mode)
    assert build()['status']=='withheld'


def financial_view(p):
    return dict(ticker='MRVL',sec_cik='0001835632',mrvl_earnings_review=p,
        companyfacts_identity=dict(status='source_matched',ticker='MRVL',sec_cik='0001835632',
            source_url=p['facts']['source_url'],observed_at=p['facts']['observed_at'],payload_sha256=p['facts']['payload_sha256']))


@pytest.mark.parametrize('change',['none','cik','ticker','digest','time','url','missing','status'])
def test_financial_view_binds_the_exact_companyfacts_observation(change):
    from src.mrvl_earnings_review import validated_mrvl_review
    view=financial_view(packet()); identity=view['companyfacts_identity']
    if change=='cik':identity['sec_cik']='0001730168'
    elif change=='ticker':view['ticker']='AVGO'
    elif change=='digest':identity['payload_sha256']='0'*64
    elif change=='time':identity['observed_at']='2026-11-07T14:00:00Z'
    elif change=='url':identity['source_url']='https://example.com/facts'
    elif change=='missing':del view['companyfacts_identity']
    elif change=='status':identity['status']='withheld'
    result=validated_mrvl_review(view,expected_cik='0001835632',as_of=NOW)
    assert result['status']==('inspection_only' if change=='none' else 'withheld')


def test_normalized_subset_digest_never_relabels_the_original_http_digest():
    from src.mrvl_earnings_review import normalize_review_facts
    raw=raw_facts(); original=deepcopy(raw); raw['payload']['facts']['custom']={'Other':{'units':{}}}
    normalized=normalize_review_facts(raw)
    assert normalized['payload_sha256']==original['payload_sha256']
    assert normalized['normalized_sha256']==digest(normalized['payload'])
    assert normalized['payload_sha256']!=normalized['normalized_sha256']
    assert 'custom' not in normalized['payload']['facts']


def test_missing_numeric_fields_keep_independent_verified_relationship_visible():
    result=build(rewrite_facts(packet(),lambda facts: facts.clear()))
    assert result['status']=='inspection_only' and result['quality']['status']=='withheld'
    assert result['peer_context']['status']=='research_context'
    assert result['peer_context']['period_end_gap_days']==90


@pytest.mark.parametrize('shape',[None, [], 'invalid'])
def test_resealed_malformed_normalized_facts_are_withheld_without_exceptions(shape):
    p=packet(); p['facts']['payload']['facts']=shape
    p['facts']['normalized_sha256']=digest(p['facts']['payload'])
    assert build(seal(p))['status']=='withheld'


def test_dei_metadata_without_an_identified_context_cannot_claim_document_identity():
    p=packet(); d=p['documents']['MRVL']
    raw=base64.b64decode(d['payload_raw_base64']).replace(b' id="annual"',b'').replace(b' contextRef="annual"',b'')
    d.update(payload_sha256=hashlib.sha256(raw).hexdigest(),payload_raw_base64=base64.b64encode(raw).decode())
    result=build(seal(p))
    assert result['peer_context']['status']=='withheld'
    assert result['quality']['status']=='inspection_only'


def test_same_annual_fact_in_another_currency_cannot_be_silently_ignored():
    def mutate(facts):
        units=facts['NetIncomeLoss']['units']; units['EUR']=[{**units['USD'][0],'val':110}]
    result=build(rewrite_facts(packet(),mutate))
    row=next(r for r in result['quality']['fields'] if r['field']=='net_income')
    assert row['value'] is None and row['reason']=='review_conflicting_annual_units'


@pytest.mark.parametrize('component',['profile','document'])
@pytest.mark.parametrize('stamp',['2026-11-06T14:59:59Z','2026-11-07T15:00:01Z'])
def test_stale_or_future_independent_receipts_cannot_support_peer_context(component,stamp):
    p=packet(); p['profiles' if component=='profile' else 'documents']['AVGO']['observed_at']=stamp
    result=build(seal(p))
    assert result['quality']['status']=='inspection_only' and result['peer_context']['status']=='withheld'


@pytest.mark.parametrize('change',['nonfinite','bounds'])
def test_unusable_individual_numbers_never_enter_quality_flags(change):
    if change=='nonfinite':
        p=packet(); p['facts']['payload']['facts']['us-gaap']['NetIncomeLoss']['units']['USD'][0]['val']=float('inf')
        assert build(seal(p))['status']=='withheld'
    else:
        def mutate(facts):facts['NetIncomeLoss']['units']['USD'][0]['val']=10**30
        result=build(rewrite_facts(packet(),mutate))
        row=next(r for r in result['quality']['fields'] if r['field']=='net_income')
        assert row['value'] is None and row['reason']=='review_fact_nonfinite_or_invalid'


@pytest.mark.parametrize('ticker,business',[
    ('MRVL','We do not compete directly with Broadcom.'),
    ('MRVL','It is false that companies that compete directly with our businesses include Broadcom.'),
    ('MRVL','Companies that compete directly with our businesses include firms other than Broadcom.'),
    ('MRVL','Companies that compete directly with our businesses include firms, excluding Broadcom.'),
    ('MRVL','Companies that compete directly with our businesses include companies but not Broadcom.'),
    ('MRVL','Broadcom acquired a business. Other companies compete directly in this market.'),
    ('AVGO','We do not have two reportable segments: semiconductor solutions and infrastructure software.'),
    ('AVGO','It is false that we have two reportable segments: semiconductor solutions and infrastructure software.'),
])
def test_negated_excluded_or_incidental_company_text_never_proves_relationship(ticker,business):
    p=packet(); p['documents'][ticker]=document(ticker,business=business)
    result=build(seal(p))
    assert result['peer_context']['status']=='withheld'
    assert result['peer_context']['relationship_supported'] is False
    assert result['quality']['status']=='inspection_only'


@pytest.mark.parametrize('ticker',['MRVL','AVGO'])
@pytest.mark.parametrize('wrapper',[
    '<span style="display: none">{}</span>',
    '<span style="DISPLAY : none !important">{}</span>',
    '<span style="visibility: hidden">{}</span>',
    '<span style="opacity: 0">{}</span>',
    '<span style="opacity: 0.0">{}</span>',
    '<span hidden="hidden">{}</span>',
    '<span aria-hidden="true">{}</span>',
    '<div style="display:none"><p>{}</p></div>',
    '<script>{}</script>',
    '<style>{}</style>',
    '<head>{}</head>',
    '<ix:hidden>{}</ix:hidden>',
])
def test_hidden_annual_words_cannot_prove_either_business_relationship(ticker,wrapper):
    business=('Companies that compete directly with our businesses include Broadcom.' if ticker=='MRVL' else
              'We have two reportable segments: semiconductor solutions and infrastructure software.')
    p=packet();p['documents'][ticker]=document(ticker,business=wrapper.format(business))
    result=build(seal(p))
    assert result['peer_context']['status']=='withheld'
    assert result['quality']['status']=='inspection_only'


def test_hidden_company_name_is_not_a_visible_direct_competitor():
    p=packet();p['documents']['MRVL']=document('MRVL',business=
        'Companies that compete directly with our businesses include <span style="display:none">Broadcom</span> Synthetic Co.')
    assert build(seal(p))['peer_context']['status']=='withheld'


def test_source_style_affirmative_list_accepts_limited_to_qualifier_and_inline_visible_text():
    p=packet();p['documents']['MRVL']=document('MRVL',business=
        'Companies that compete directly with our businesses include, but are not limited to, <b>Broadcom</b> and Synthetic Co.')
    result=build(seal(p))
    assert result['peer_context']['relationship_supported'] is True
    assert result['peer_context']['period_end_gap_days']==90
