from copy import deepcopy
from datetime import datetime, timezone
import hashlib

import pytest

OBSERVED = datetime(2026,10,30,21,tzinfo=timezone.utc)
SOURCE = 'https://www.sec.gov/Archives/edgar/data/1234/000000432126000001/fict-20260630.htm'


def _selection(kind='quarterly'):
    end='2025-12-31' if kind=='annual' else '2026-06-30'
    return dict(status='selected',ticker='FICT',sec_cik='0000001234',period_kind=kind,period_end=end,
        form='20-F' if kind=='annual' else '10-Q',filed='2026-08-01',accepted_at='2026-08-01T12:00:00Z',
        accession='0000004321-26-000001',primary_document='fict-20260630.htm',source_url=SOURCE,
        source_receipts=[dict(source_url='https://www.sec.gov/files/company_tickers.json',observed_at='2026-10-30T21:00:00Z',payload_sha256='b'*64),
                         dict(source_url='https://data.sec.gov/submissions/CIK0000001234.json',observed_at='2026-10-30T21:00:00Z',payload_sha256='c'*64)])


def _xml(*,annual=False):
    start,end=('2025-01-01','2025-12-31') if annual else ('2026-04-01','2026-06-30')
    form='20-F' if annual else '10-Q'
    prefix='ifrs' if annual else 'g'
    revenue='RevenueFromContractsWithCustomers' if annual else 'RegulatedAndUnregulatedOperatingRevenue'
    oi='ProfitLossFromOperatingActivities' if annual else 'OperatingIncomeLoss'
    cfo='CashFlowsFromUsedInOperatingActivities' if annual else 'NetCashProvidedByUsedInOperatingActivities'
    capex='PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities' if annual else 'PaymentsToAcquirePropertyPlantAndEquipment'
    currency='TWD' if annual else 'USD'
    cumulative='' if annual else f'<x:context id="cum"><x:entity><x:identifier scheme="http://www.sec.gov/CIK">0000001234</x:identifier></x:entity><x:period><x:startDate>2026-01-01</x:startDate><x:endDate>{end}</x:endDate></x:period></x:context>'
    flow_context='cur' if annual else 'cum'
    return f'''<html xmlns="http://www.w3.org/1999/xhtml" xmlns:x="http://www.xbrl.org/2003/instance" xmlns:ix="http://www.xbrl.org/2013/inlineXBRL" xmlns:ixt="http://www.xbrl.org/inlineXBRL/transformation/2020-02-12" xmlns:dei="http://xbrl.sec.gov/dei/2026" xmlns:g="http://fasb.org/us-gaap/2026" xmlns:ifrs="https://xbrl.ifrs.org/taxonomy/2025-03-27/ifrs-full" xmlns:iso="http://www.xbrl.org/2003/iso4217" xmlns:dim="http://xbrl.org/2006/xbrldi" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <head><x:context id="cur"><x:entity><x:identifier scheme="http://www.sec.gov/CIK">0000001234</x:identifier></x:entity><x:period><x:startDate>{start}</x:startDate><x:endDate>{end}</x:endDate></x:period></x:context>{cumulative}
    <x:unit id="money"><x:measure>iso:{currency}</x:measure></x:unit></head><body>
    <ix:nonNumeric name="dei:EntityCentralIndexKey" contextRef="cur" id="dei-cik">0000001234</ix:nonNumeric>
    <ix:nonNumeric name="dei:DocumentType" contextRef="cur" id="dei-form">{form}</ix:nonNumeric>
    <ix:nonNumeric name="dei:DocumentPeriodEndDate" contextRef="cur" id="dei-end">{end}</ix:nonNumeric>
    <ix:nonNumeric name="dei:AmendmentFlag" contextRef="cur" id="dei-amend">false</ix:nonNumeric>
    <ix:nonFraction name="{prefix}:{revenue}" contextRef="cur" unitRef="money" scale="6" decimals="-6" format="ixt:num-dot-decimal" id="revenue">1,234</ix:nonFraction>
    <ix:nonFraction name="{prefix}:{oi}" contextRef="cur" unitRef="money" scale="3" sign="-" decimals="-1" format="ixt:num-dot-decimal" id="op">12.3</ix:nonFraction>
    <ix:nonFraction name="{prefix}:{cfo}" contextRef="{flow_context}" unitRef="money" scale="6" decimals="-6" format="ixt:num-dot-decimal" id="cfo">500</ix:nonFraction>
    (<ix:nonFraction name="{prefix}:{capex}" contextRef="{flow_context}" unitRef="money" scale="6" decimals="-6" format="ixt:num-dot-decimal" id="capex">200</ix:nonFraction>)
    </body></html>'''


def _extract(xml=None,kind='quarterly'):
    from src.sec_inline_filing import extract_inline_filing
    raw=(xml or _xml(annual=kind=='annual')).encode()
    receipt=dict(status='ready',source_url=SOURCE,observed_at='2026-10-30T21:00:00Z',payload_sha256=hashlib.sha256(raw).hexdigest(),source_last_modified=None)
    return extract_inline_filing(raw,_selection(kind),receipt)


def test_exact_direct_and_cumulative_fields_preserve_scale_sign_and_source_identity():
    from src.sec_exact_filing import validated_filing_preview
    packet=_extract()
    assert packet['status']=='inspection_only'
    quarter=packet['periods'][0]
    assert quarter['kind']=='quarterly'
    assert quarter['fields']['revenue']['value']==1234000000
    assert quarter['fields']['operating_income']['value']==-12300
    assert 'cash_from_operations' not in quarter['fields']
    cumulative=next(r for r in packet['periods'] if r['kind']=='cumulative')
    assert cumulative['fields']['cash_from_operations']['value']==500000000
    assert cumulative['fields']['capital_expenditures']['value']==200000000
    assert cumulative['period_start']=='2026-01-01'
    field=quarter['fields']['revenue']
    assert field['source_ref']==SOURCE+'#revenue'
    assert field['context_id']=='cur' and field['unit']=='USD' and field['scale']==6
    assert field['rights_status']=='unregistered_sec_archive_personal_inspection_only'
    assert packet['commercial_eligible'] is False and packet['readiness_promoted'] is False
    assert validated_filing_preview(packet,'FICT','quarterly') is not None


def test_foreign_customer_contract_revenue_retains_native_currency_and_definition():
    p=_extract(kind='annual')
    assert p['unit']=='TWD' and p['periods'][0]['kind']=='annual'
    assert p['periods'][0]['fields']['revenue']['concept']=='RevenueFromContractsWithCustomers'
    assert p['periods'][0]['fields']['revenue']['value']==1234000000


@pytest.mark.parametrize('problem',['wrong_cik','dimension','scenario','false_taxonomy','false_currency_namespace'])
def test_wrong_entity_dimension_or_namespace_never_produces_company_amounts(problem):
    xml=_xml()
    if problem=='wrong_cik':xml=xml.replace('0000001234</x:identifier>','0000009999</x:identifier>')
    elif problem=='dimension':xml=xml.replace('</x:entity>','<x:segment><dim:explicitMember dimension="dei:LegalEntityAxis">g:Subsidiary</dim:explicitMember></x:segment></x:entity>')
    elif problem=='scenario':xml=xml.replace('</x:context>','<x:scenario><dim:explicitMember dimension="g:Scenario">g:Forecast</dim:explicitMember></x:scenario></x:context>')
    elif problem=='false_taxonomy':xml=xml.replace('http://fasb.org/us-gaap/2026','https://example.invalid/us-gaap/2026')
    else:xml=xml.replace('http://www.xbrl.org/2003/iso4217','https://example.invalid/currency')
    p=_extract(xml)
    assert not any(r.get('fields') for r in p.get('periods',[]))


@pytest.mark.parametrize('problem',['scale','format','nil','nan','conflict','continued'])
def test_bad_or_conflicting_revenue_is_held_without_borrowing_another_number(problem):
    xml=_xml()
    if problem=='scale':xml=xml.replace('scale="6" decimals="-6" format="ixt:num-dot-decimal" id="revenue"','scale="bad" decimals="-6" format="ixt:num-dot-decimal" id="revenue"')
    elif problem=='format':xml=xml.replace('format="ixt:num-dot-decimal" id="revenue"','format="ixt:unknown-number" id="revenue"')
    elif problem=='nil':xml=xml.replace('id="revenue"','id="revenue" xsi:nil="true"')
    elif problem=='nan':xml=xml.replace('>1,234</ix:nonFraction>','>NaN</ix:nonFraction>')
    elif problem=='continued':xml=xml.replace('id="revenue"','id="revenue" continuedAt="missing"')
    else:
        fact='<ix:nonFraction name="g:RegulatedAndUnregulatedOperatingRevenue" contextRef="cur" unitRef="money" scale="6" decimals="-6" format="ixt:num-dot-decimal" id="conflict">9,999</ix:nonFraction>'
        xml=xml.replace('</body>',fact+'</body>')
    p=_extract(xml)
    q=next(r for r in p['periods'] if r['kind']=='quarterly')
    assert 'revenue' not in q['fields'] and q['withheld_fields']['revenue']
    assert q['fields']['operating_income']['value']==-12300


def test_duplicate_ids_and_dtd_are_held_without_extracting_any_fact():
    for xml in [_xml().replace('id="op"','id="revenue"'),'<!DOCTYPE html [<!ENTITY injected "1234">]>'+_xml()]:
        assert _extract(xml)['status']=='withheld'


def test_native_currency_is_not_replaced_by_convenience_usd_or_ambiguous_native_unit():
    xml=_xml(annual=True)
    usd='<x:unit id="usd"><x:measure>iso:USD</x:measure></x:unit>'
    dup='<ix:nonFraction name="ifrs:RevenueFromContractsWithCustomers" contextRef="cur" unitRef="usd" scale="6" decimals="-6" format="ixt:num-dot-decimal" id="translated">35</ix:nonFraction>'
    p=_extract(xml.replace('</head>',usd+'</head>').replace('</body>',dup+'</body>'),kind='annual')
    assert p['unit']=='TWD' and p['periods'][0]['fields']['revenue']['value']==1234000000
    xml=xml.replace('</head>',usd.replace('USD','EUR')+'</head>').replace('</body>',dup+'</body>')
    assert _extract(xml,kind='annual')['status']=='withheld'


def test_cached_packet_requires_unchanged_amount_and_correct_company_period():
    from src.sec_exact_filing import validated_filing_preview
    packet=_extract();modified=deepcopy(packet);modified['periods'][0]['fields']['revenue']['value']=999
    assert validated_filing_preview(modified,'FICT','quarterly') is None
    assert validated_filing_preview(packet,'OTHER','quarterly') is None
    assert validated_filing_preview(packet,'FICT','annual') is None


@pytest.mark.parametrize('problem',['duplicate_period_end','duplicate_entity','nil_dei','continued_dei'])
def test_ambiguous_period_structure_or_unusable_dei_cannot_bind_the_filing(problem):
    xml=_xml()
    if problem=='duplicate_period_end':xml=xml.replace('<x:endDate>2026-06-30</x:endDate>','<x:endDate>2026-06-30</x:endDate><x:endDate>2026-09-30</x:endDate>',1)
    elif problem=='duplicate_entity':xml=xml.replace('</x:entity>','</x:entity><x:entity><x:identifier scheme="http://www.sec.gov/CIK">0000009999</x:identifier></x:entity>',1)
    elif problem=='nil_dei':xml=xml.replace('id="dei-cik"','id="dei-cik" xsi:nil="true"')
    else:xml=xml.replace('id="dei-cik"','id="dei-cik" continuedAt="outside"')
    assert _extract(xml)['status']=='withheld'
