from copy import deepcopy
import hashlib
import pytest
from test_sec_inline_filing import _selection

BASIS='<p>The consolidated financial statements of the Group are prepared in accordance with Indian GAAP.</p>'
URL='https://www.sec.gov/Archives/edgar/data/1103838/000000432126000001/fict-20260630.htm'

def selection():
 s=_selection('annual');s.update(ticker='IBN',sec_cik='0001103838',period_end='2026-03-31',source_url=URL,adapter='ibn_html_bank');s['source_receipts'][1]['source_url']='https://data.sec.gov/submissions/CIK0001103838.json';return s

def html():
 header='<tr><td></td><td colspan="3">March 31, 2026</td><td colspan="3">March 31, 2025</td><td colspan="3">March 31, 2024</td></tr>'
 def row(label,values):return '<tr><td>'+label+'</td>'+''.join('<td colspan="3">'+v+'</td>' for v in values)+'</tr>'
 income=''.join(row(label,values) for label,values in [('Interest earned',['100','90','80']),('Other income',['20','19','18']),('TOTAL INCOME',['120','109','98']),('Interest expended',['30','29','28']),('Consolidated profit/(loss) for the year attributable to the Group',['15','14','13'])])
 cash=row('Net cash flow from/(used in) operating activities ((i)+(ii)+(iii))',['50','40','30'])+row('Purchase of fixed assets',['(4)','(3)','(2)'])
 return '<html><body><p>FORM 20-F</p><p>ICICI BANK LIMITED</p><p>For the fiscal year ended March 31, 2026.</p>'+BASIS+'<p>ICICI Bank Limited and subsidiaries</p><p>Consolidated Profit and Loss Account</p><a name="f_003"></a><table><tr><td colspan="10">(Rs. in thousands, except per share data)</td></tr><tr><td colspan="10">Year ended</td></tr>'+header+income+'</table><p>ICICI Bank Limited and subsidiaries</p><p>Consolidated Cash Flow Statement</p><a name="f_004"></a><table><tr><td colspan="10">(Rs. in thousands)</td></tr><tr><td colspan="10">Year ended</td></tr>'+header+cash+'</table></body></html>'

def extract(text=None):
 from src.sec_html_bank import extract_bank_html
 raw=(text or html()).encode();r=dict(status='ready',source_url=URL,observed_at='2026-10-30T21:00:00Z',payload_sha256=hashlib.sha256(raw).hexdigest())
 return extract_bank_html(raw,selection(),r)

def test_direct_bank_definitions_and_signed_cashflows_are_not_generic_revenue_or_fcf():
 from src.sec_html_bank import validated_bank_html
 p=extract();assert p['status']=='inspection_only';assert validated_bank_html(p,'IBN','annual') is not None
 assert p['accounting_basis']=='Indian GAAP' and p['unit']=='INR' and len(p['periods'])==3
 fields=p['periods'][0]['fields'];assert fields['total_income']['value']==120000
 assert fields['cash_from_operations']['value']==50000 and fields['fixed_asset_purchases']['value']==-4000
 assert fields['profit_attributable_to_group']['value']==15000
 assert fields['cash_from_operations']['source_ref']==URL+'#f_004'
 assert set(p['withheld_fields'])>={'revenue','operating_income','net_interest_income','free_cash_flow','valuation'}
 assert p['periods'][0]['period_start']=='2025-04-01' and p['periods'][2]['period_end']=='2024-03-31'
 assert p['financial_coverage_promoted'] is False

@pytest.mark.parametrize('problem',['issuer','period','unit','basis','standalone','rowspan','nested','duplicate_anchor','duplicate_statement','currency_column'])
def test_ambiguous_or_wrong_statement_identity_context_is_held(problem):
 t=html()
 if problem=='issuer':t=t.replace('ICICI BANK LIMITED','OTHER BANK LIMITED')
 elif problem=='period':t=t.replace('For the fiscal year ended March 31, 2026.','For the fiscal year ended March 31, 2025.')
 elif problem=='unit':t=t.replace('Rs. in thousands)','US$ in millions)')
 elif problem=='basis':t=t.replace('Indian GAAP','IFRS')
 elif problem=='standalone':t=t.replace('ICICI Bank Limited and subsidiaries','ICICI Bank Limited standalone')
 elif problem=='rowspan':t=t.replace('<td colspan="3">50','<td rowspan="2" colspan="3">50')
 elif problem=='nested':t=t.replace('<td colspan="3">50','<td colspan="3"><table><tr><td>50</td></tr></table>')
 elif problem=='duplicate_anchor':t=t.replace('</body>','<a name="f_003"></a></body>')
 elif problem=='duplicate_statement':t=t.replace('</body>',t[t.index('<p>ICICI Bank Limited and subsidiaries'):t.index('<p>ICICI Bank Limited and subsidiaries',t.index('<p>ICICI Bank Limited and subsidiaries')+1)].replace('f_003','f_005')+'</body>')
 else:t=t.replace('March 31, 2025','March 31, 2026',1)
 assert extract(t)['status']=='withheld'

def test_conflicting_or_missing_numeric_row_is_withheld_without_inventing_sibling_fields():
 t=html().replace('<td colspan="3">50</td>','<td colspan="3">nil</td>')
 p=extract(t);assert p['status']=='inspection_only'
 assert 'cash_from_operations' not in p['periods'][0]['fields']
 assert p['periods'][0]['fields']['fixed_asset_purchases']['value']==-4000

@pytest.mark.parametrize('problem',['amount','period','unit','label','position','issuer','rights'])
def test_cached_bank_packet_rechecks_component_definitions_not_just_digest(problem):
 from src.sec_html_bank import validated_bank_html
 from src.sec_exact_filing import _digest
 p=deepcopy(extract());f=p['periods'][0]['fields']['cash_from_operations']
 if problem=='amount':f['value']=999
 elif problem=='period':p['periods'][0]['period_end']='2025-03-31'
 elif problem=='unit':p['unit']='USD'
 elif problem=='label':f['label']='Revenue'
 elif problem=='position':f['column_span']=[-1,4]
 elif problem=='issuer':p['sec_cik']='0000001234'
 else:p['rights_status']='approved'
 p['packet_digest']=_digest({k:v for k,v in p.items() if k!='packet_digest'})
 assert validated_bank_html(p,'IBN','annual') is None

@pytest.mark.parametrize('style',['display:none','opacity:0','visibility:hidden'])
def test_hidden_numeric_source_cell_does_not_become_visible_evidence(style):
 t=html().replace('>50</td>',f'><span style="{style}">50</span></td>')
 p=extract(t)
 assert p['status']=='inspection_only' and 'cash_from_operations' not in p['periods'][0]['fields']

def test_exact_source_api_dispatches_only_qualified_ibn_annual_and_caches_by_company():
 import json
 from datetime import datetime,timezone
 from src.sec_exact_filing import get_company_filing_preview
 from test_sec_exact_filing import _submission
 body=_submission();body['cik']=1103838;r=body['filings']['recent'];r.update(form=['20-F'],reportDate=['2026-03-31'],isInlineXBRL=[0],isXBRL=[0])
 calls=[]
 def fetch(url,agent):
  calls.append(url)
  if url.endswith('company_tickers.json'):raw=json.dumps({'0':{'ticker':'IBN','cik_str':1103838,'title':'ICICI BANK LIMITED'}}).encode()
  elif '/submissions/' in url:raw=json.dumps(body).encode()
  else:raw=html().encode()
  return raw,{},url
 state={};p=get_company_filing_preview('IBN',state,period_kind='annual',refresh_requested=True,user_agent='Synthetic',fetcher=fetch,observed_at=datetime(2026,10,30,21,tzinfo=timezone.utc))
 assert p['status']=='inspection_only' and p['periods'][0]['fields']['cash_from_operations']['value']==50000
 assert len(calls)==3
 assert get_company_filing_preview('IBN',state,period_kind='annual',refresh_requested=False,user_agent='Synthetic')['status']=='inspection_only'
 assert get_company_filing_preview('OTHER',state,period_kind='annual',refresh_requested=False,user_agent='Synthetic')['status']=='not_requested'
 assert len(calls)==3

def test_cover_ads_disclosure_is_an_independent_as_filed_observation():
 t=html().replace(BASIS,BASIS+'<p>Securities registered or to be registered pursuant to Section 12(b) of the Act:</p><table><tr><td>Title of each class</td><td>Trading Symbol(s)</td><td>Name of each exchange on which registered</td></tr><tr><td>Equity Shares and American Depositary Shares</td><td>IBN</td><td>The New York Stock Exchange</td></tr></table><p>Not for trading, but only in connection with the registration of American Depositary Shares.</p>')
 p=extract(t);assert p['status']=='inspection_only'
 assert p['registration_observation']['declared_type']=='depositary_receipt'
 assert p['registration_observation']['as_of']=='2026-08-01'
 assert p['registration_observation']['current_legal_type_established'] is False
 assert extract()['registration_observation']['status']=='withheld'

@pytest.mark.parametrize('cell',['50<sup>1</sup>','50<sub>1</sub>','50<small>1</small>','50<a href="#note">1</a>'])
def test_annotated_financial_amounts_are_held_instead_of_joining_footnote_digits(cell):
 p=extract(html().replace('>50</td>','>'+cell+'</td>'))
 assert p['status']=='inspection_only' and 'cash_from_operations' not in p['periods'][0]['fields']
 assert p['periods'][0]['fields']['fixed_asset_purchases']['value']==-4000

def test_multiple_numeric_tokens_inside_one_year_span_are_not_concatenated():
 p=extract(html().replace('<td colspan="3">50</td>','<td>50</td><td></td><td>1</td>'))
 assert p['status']=='inspection_only' and 'cash_from_operations' not in p['periods'][0]['fields']

@pytest.mark.parametrize('placement',['before_dates','after_dates'])
def test_contradictory_column_currency_holds_the_statement_packet(placement):
 t=html();row='<tr><td></td><td colspan="3">USD</td><td colspan="3">INR</td><td colspan="3">INR</td></tr>'
 if placement=='before_dates':t=t.replace('<tr><td></td><td colspan="3">March 31, 2026',row+'<tr><td></td><td colspan="3">March 31, 2026',1)
 else:t=t.replace('<tr><td>Interest earned',row+'<tr><td>Interest earned',1)
 assert extract(t)['status']=='withheld'

@pytest.mark.parametrize('basis',[
 '<p>Previous statements used Indian GAAP. Current consolidated statements are prepared in accordance with IFRS.</p>',
 BASIS+'<p>Current consolidated financial statements are prepared in accordance with IFRS.</p>',
 '<p>Previously, the consolidated financial statements of the Group are prepared in accordance with Indian GAAP.</p>',
 '<p>Indian GAAP</p>',
 '<p>The consolidated financial statements of the Group are prepared in accordance with Indian GAAP in prior years.</p>',
 BASIS+'<p>Current consolidated financial statements are not prepared in accordance with Indian GAAP.</p>',
])
def test_basis_requires_affirmative_current_consolidated_evidence_without_contradiction(basis):
 assert extract(html().replace(BASIS,basis))['status']=='withheld'
