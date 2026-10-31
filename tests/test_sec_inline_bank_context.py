from copy import deepcopy
import hashlib
import pytest
from test_sec_inline_filing import _selection,_xml,SOURCE


def bank_input():
 selection=_selection();selection['bank_scope']={'sec_cik':'0000001234','sic':'6022','source_receipt':deepcopy(selection['source_receipts'][1])}
 xml=_xml().replace('g:RegulatedAndUnregulatedOperatingRevenue','g:InterestIncomeExpenseNet').replace('id="revenue">1,234','id="interest">50')
 xml=xml.replace('</body>', '<ix:nonFraction name="g:NoninterestIncome" contextRef="cur" unitRef="money" scale="6" decimals="-6" format="ixt:num-dot-decimal" id="noninterest">20</ix:nonFraction></body>')
 return xml,selection


def extract(xml=None,selection=None):
 from src.sec_inline_filing import extract_inline_filing
 text,sel=bank_input();raw=(xml or text).encode();return extract_inline_filing(raw,selection or sel,dict(status='ready',source_url=SOURCE,observed_at='2026-10-30T21:00:00Z',payload_sha256=hashlib.sha256(raw).hexdigest()))


def test_bank_income_anchor_does_not_invent_revenue():
 from src.sec_exact_filing import validated_filing_preview
 p=extract();assert p['status']=='inspection_only'
 assert p['source_id']=='sec_archive_inline_bank' and p['schema_version']=='sec-exact-bank-context-v1'
 r=p['periods'][0];assert r['fields']['net_interest_income']['value']==50000000
 assert r['fields']['noninterest_income']['value']==20000000
 assert 'revenue' not in r['fields'] and 'revenue' in r['withheld_fields']
 assert p['readiness_promoted'] is False and p['commercial_eligible'] is False
 assert validated_filing_preview(p,'FICT','quarterly')==p

@pytest.mark.parametrize('change',['cik','sic','receipt','currency','duration'])
def test_bank_classification_identity_units_and_period_cannot_be_inferred(change):
 xml,sel=bank_input()
 if change=='cik':sel['bank_scope']['sec_cik']='0000009999'
 elif change=='sic':sel['bank_scope']['sic']='3571'
 elif change=='receipt':sel['bank_scope']['source_receipt']['payload_sha256']='f'*64
 elif change=='currency':xml=xml.replace('iso:USD','iso:TWD')
 else:xml=xml.replace('2026-04-01','2026-06-01')
 assert extract(xml,sel)['status']=='withheld'


def test_unclassified_filing_cannot_use_bank_fallback():
 xml,sel=bank_input();sel.pop('bank_scope');assert extract(xml,sel)['status']=='withheld'


def test_conflicting_bank_facts_are_held_without_summing():
 xml,sel=bank_input();xml=xml.replace('</body>', '<ix:nonFraction name="g:InterestIncomeExpenseNet" contextRef="cur" unitRef="money" scale="6" decimals="-6" id="conflict">60</ix:nonFraction></body>')
 p=extract(xml,sel);assert p['status']=='inspection_only'
 row=p['periods'][0];assert 'net_interest_income' not in row['fields']
 assert row['withheld_fields']['net_interest_income']=='conflicting_direct_facts'
 assert row['fields']['noninterest_income']['value']==20000000


def test_bank_cache_rechecks_numeric_proof_and_classification():
 from src.sec_exact_filing import validated_filing_preview,_digest
 p=extract();assert p['status']=='inspection_only'
 p['periods'][0]['fields']['net_interest_income']['value']=51
 p['packet_digest']=_digest({k:v for k,v in p.items()if k!='packet_digest'})
 assert validated_filing_preview(p,'FICT','quarterly') is None


def test_bank_view_explains_income_components_instead_of_reporting_generic_revenue():
 from src.sec_exact_filing_view import filing_preview_html
 p=extract();html=filing_preview_html(p,'FICT','quarterly')
 assert 'Net interest income' in html and 'Noninterest income' in html
 assert 'not combined into revenue' in html


def test_selection_binds_bank_sic_to_same_submissions_identity():
 from src.sec_exact_filing import select_sec_filing
 s=_selection();row={'accessionNumber':s['accession'],'reportDate':s['period_end'],'filingDate':s['filed'],'acceptanceDateTime':s['accepted_at'],'form':s['form'],'primaryDocument':s['primary_document'],'isInlineXBRL':1,'isXBRL':1}
 ref={'status':'ready',**s['source_receipts'][1],'payload':{'cik':1234,'sic':'6022','filings':{'recent':{k:[v]for k,v in row.items()}}}}
 p=select_sec_filing('FICT','0000001234',ref,period_kind='quarterly')
 assert p['bank_scope']['sic']=='6022'
 assert p['bank_scope']['source_receipt']==s['source_receipts'][1]

@pytest.mark.parametrize('field,bad',[('sic',[]),('sign',[]),('transformation',[])])
def test_malformed_bank_cache_metadata_is_held_without_throwing(field,bad):
 from src.sec_exact_filing import validated_filing_preview,_digest
 p=extract()
 if field=='sic':p['bank_scope']['sic']=bad
 else:p['periods'][0]['fields']['net_interest_income'][field]=bad
 p['packet_digest']=_digest({k:v for k,v in p.items()if k!='packet_digest'})
 assert validated_filing_preview(p,'FICT','quarterly') is None
