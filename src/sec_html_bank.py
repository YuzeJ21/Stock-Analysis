"""Narrow consolidated Indian-GAAP annual HTML evidence; no generic table guessing."""
from html.parser import HTMLParser
from decimal import Decimal,InvalidOperation
from datetime import date,timedelta
from collections.abc import Mapping
import hashlib,re
from src.sec_exact_filing import RIGHTS,MAX_FILING_BYTES,_digest,_reference_valid,MAP_URL
from src.company_sec_online_preview import _iso_date,_utc_timestamp

SOURCE_ID='sec_archive_html_bank'
SCHEMA='sec-html-bank-v1'
CIK='0001103838'
CAPTIONS={'income':'Consolidated Profit and Loss Account','cash':'Consolidated Cash Flow Statement'}
DEFINITIONS={
 'interest_earned':('income','Interest earned','Interest earned · gross'),
 'other_income':('income','Other income','Other income'),
 'total_income':('income','TOTAL INCOME','Total income · before interest expense'),
 'interest_expended':('income','Interest expended','Interest expended'),
 'profit_attributable_to_group':('income','Consolidated profit/(loss) for the year attributable to the Group','Profit attributable to the Group'),
 'cash_from_operations':('cash','Net cash flow from/(used in) operating activities ((i)+(ii)+(iii))','Net operating cash flow'),
 'fixed_asset_purchases':('cash','Purchase of fixed assets','Fixed-asset purchases · signed cash flow')}
WITHHELD={k:'not_a_direct_equivalent_in_selected_consolidated_statements' for k in ('revenue','operating_income','net_interest_income','free_cash_flow','valuation')}

def _norm(s):return ' '.join(s.split())
def _hidden(attrs):
 style=re.sub(r'\s+','',attrs.get('style','').lower())
 return ('hidden' in attrs or attrs.get('aria-hidden')=='true'
         or any(v in style for v in ('display:none','visibility:hidden','visibility:collapse'))
         or re.search(r'(?:^|;)opacity:0(?:\.0*)?(?:;|!important|$)',style) is not None)

class _Tables(HTMLParser):
 def __init__(self):
  super().__init__(convert_charrefs=True);self.tables=[];self.table=None;self.depth=0;self.row=None;self.cell=None;self.p=None;self.context=[];self.anchor=None;self.anchors=set();self.all_text=[];self.elements=0;self.table_count=0;self.stack=[]
 def handle_starttag(self,tag,attrs):
  self.elements+=1
  if self.elements>350000:raise ValueError('html_element_limit')
  a=dict(attrs);hidden=_hidden(a) or tag in {'script','style','template'} or any(h for _,h in self.stack)
  if tag not in {'br','hr','img','meta','link','input','wbr','source','area','base','col','embed','param'}:self.stack.append((tag,hidden))
  for ident in {a[k] for k in ('name','id') if a.get(k)}:
   if tag=='a' or 'id' in a:
    if ident in self.anchors:raise ValueError('duplicate_document_anchor')
    self.anchors.add(ident)
    if not self.depth and not hidden:self.anchor=ident
  if tag=='table':
   self.table_count+=1;self.depth+=1
   if self.depth==1:self.table=dict(index=self.table_count-1,context=self.context[-4:],anchor=self.anchor,rows=[],bad=hidden)
   else:self.table['bad']=True
  elif self.depth==1:
   if tag=='tr':
    if self.row is not None:self.table['bad']=True
    self.row=[]
   elif tag in {'td','th'}:
    if self.cell is not None or self.row is None:self.table['bad']=True
    try:span=int(a.get('colspan','1'));rowspan=int(a.get('rowspan','1'))
    except ValueError:span=0;rowspan=0
    if not 1<=span<=64 or rowspan!=1:self.table['bad']=True
    self.cell=dict(text='',span=span,bad=hidden or not 1<=span<=64 or rowspan!=1)
   elif self.cell is not None and hidden:self.cell['bad']=True
  elif not self.depth and tag=='p':self.p=[]
 def handle_data(self,data):
  visible=not any(h for _,h in self.stack)
  if visible:self.all_text.append(data)
  if self.depth==1 and self.cell is not None:self.cell['text']+=data
  elif not self.depth and self.p is not None and visible:self.p.append(data)
 def handle_endtag(self,tag):
  if tag=='table':
   if self.depth==1:
    if self.row is not None or self.cell is not None:self.table['bad']=True
    self.tables.append(self.table);self.table=None
   self.depth=max(0,self.depth-1)
  elif self.depth==1:
   if tag in {'td','th'} and self.cell is not None:
    self.cell['text']=_norm(self.cell['text']);self.row.append(self.cell);self.cell=None
   elif tag=='tr' and self.row is not None:
    if self.cell is not None:self.table['bad']=True
    self.table['rows'].append(self.row);self.row=None
    if len(self.table['rows'])>2000:self.table['bad']=True
  elif not self.depth and tag=='p' and self.p is not None:
   text=_norm(''.join(self.p));self.p=None
   if text:self.context.append(text)
  for i in range(len(self.stack)-1,-1,-1):
   if self.stack[i][0]==tag:del self.stack[i:];break

def _amount(text):
 raw=re.sub(r'\s+','',text)
 if re.fullmatch(r'\((?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?\)',raw):raw='-'+raw[1:-1]
 if not re.fullmatch(r'-?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?',raw):return None
 try:
  n=Decimal(raw.replace(',',''))*1000
  if not n.is_finite() or abs(n)>Decimal('1e20'):return None
  return int(n) if n==n.to_integral_value() else float(n)
 except (ValueError,InvalidOperation,OverflowError):return None

def _grid(table,end):
 if table['bad'] or not 1<=len(table['rows'])<=500 or not isinstance(table['anchor'],str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.-]{0,127}',table['anchor']):raise ValueError('unsupported_statement_structure')
 rows=[];headers=[]
 for i,row in enumerate(table['rows']):
  cells=[];column=0
  for cell in row:
   cells.append({**cell,'start':column,'end':column+cell['span']});column+=cell['span']
  if column>64:raise ValueError('statement_column_limit')
  dates=[c for c in cells if re.fullmatch(r'March 31, \d{4}',c['text'])]
  if dates:headers.append((i,cells,dates,column))
  rows.append((cells,column))
 if len(headers)!=1:raise ValueError('ambiguous_annual_header')
 _,header,dates,width=headers[0];year=int(end[:4])
 if (len(dates)!=3 or [c['text'] for c in dates]!=[f'March 31, {year-n}' for n in range(3)] or any(c['bad'] for c in header)
     or not any('Year ended' in ' '.join(c['text'] for c in row) for row in table['rows'][:headers[0][0]+1])):raise ValueError('unverified_annual_columns')
 return rows,dates,width

def _registration(parser,document,selection):
 held=dict(status='withheld',reason='qualified_cover_security_disclosure_unavailable',current_legal_type_established=False)
 tables=[t for t in parser.tables if t['index']<20 and not t['bad'] and len(t['rows'])<50
         and 'Title of each class' in ' '.join(c['text'] for r in t['rows'] for c in r)]
 if len(tables)!=1:return held
 table=tables[0];text=' '.join(c['text'] for r in table['rows'] for c in r)
 prefix=document[:20000]
 if (not all(s in text for s in ('American Depositary Shares','IBN','The New York Stock Exchange','Trading Symbol'))
     or 'Not for trading, but only in connection with the registration of American Depositary Shares' not in prefix):return held
 return dict(status='observed_as_filed',declared_type='depositary_receipt',label='American Depositary Shares',as_of=selection['filed'],current_legal_type_established=False,source_ref=selection['source_url'],table_index=table['index'],raw_cover_table=text,underlying_note='Not for trading, but only in connection with the registration of American Depositary Shares')

def extract_bank_html(raw,selection,receipt):
 held=dict(status='withheld',ticker=selection.get('ticker'),period_kind=selection.get('period_kind'),reason='bank_html_evidence_unavailable')
 try:
  if (selection.get('status')!='selected' or selection.get('sec_cik')!=CIK or selection.get('ticker')!='IBN' or selection.get('period_kind')!='annual'
      or selection.get('form') not in {'20-F','20-F/A'} or receipt.get('status')!='ready' or receipt.get('source_url')!=selection.get('source_url')
      or not isinstance(raw,bytes) or not 0<len(raw)<=MAX_FILING_BYTES or b'\0' in raw or b'<!entity' in raw.lower()
      or receipt.get('payload_sha256')!=hashlib.sha256(raw).hexdigest()):return held
  text=raw.decode('utf-8-sig');parser=_Tables();parser.feed(text);parser.close();document=_norm(' '.join(parser.all_text))
  end=selection['period_end'];year=int(end[:4])
  if (not _iso_date(end) or end[4:]!='-03-31' or 'ICICI BANK LIMITED' not in document[:20000]
      or f'For the fiscal year ended March 31, {year}.' not in document[:20000]
      or 'FORM '+selection['form'] not in document[:20000] or 'Indian GAAP' not in document):return {**held,'reason':'bank_identity_period_or_basis_unverified'}
  selected={}
  for kind,caption in CAPTIONS.items():
   candidates=[t for t in parser.tables if t['context'][-2:]==['ICICI Bank Limited and subsidiaries',caption]]
   if len(candidates)!=1:raise ValueError('ambiguous_consolidated_statement')
   table=candidates[0];unit='(Rs. in thousands, except per share data)' if kind=='income' else '(Rs. in thousands)'
   if table['rows'][0][-1]['text']!=unit or any(c['bad'] for c in table['rows'][0]):raise ValueError('statement_currency_or_scale_unverified')
   rows,dates,width=_grid(table,end);selected[kind]=(table,rows,dates,width)
  periods=[]
  for y in range(3):
   fields={};gaps={}
   for field,(kind,label,display) in DEFINITIONS.items():
    table,rows,dates,width=selected[kind];column=dates[y];matches=[(i,cells) for i,(cells,w) in enumerate(rows) if cells and cells[0]['text'].casefold()==label.casefold()]
    if len(matches)!=1:gaps[field]='direct_row_missing_or_ambiguous';continue
    i,cells=matches[0]
    if sum(c['span'] for c in cells)!=width:gaps[field]='row_column_alignment_unverified';continue
    values=[c for c in cells if c['end']>column['start'] and c['start']<column['end']]
    if any(c['bad'] or c['start']<column['start'] or c['end']>column['end'] for c in values):gaps[field]='unsupported_or_cross_column_cell';continue
    raw_text=' '.join(c['text'] for c in values).strip();amount=_amount(raw_text)
    if amount is None:gaps[field]='direct_numeric_cell_unavailable';continue
    fields[field]=dict(field=field,label=label,definition=display,value=amount,raw_text=raw_text,unit='INR',scale=1000,table_index=table['index'],row_index=i,column_span=[column['start'],column['end']],anchor=table['anchor'],source_ref=selection['source_url']+'#'+table['anchor'],rights_status=RIGHTS)
   periods.append(dict(period_start=f'{year-y-1}-04-01',period_end=f'{year-y}-03-31',fields=fields,withheld_fields=gaps))
  keys=('ticker','sec_cik','period_kind','period_end','form','filed','accepted_at','accession','primary_document','source_url')
  result={k:selection[k] for k in keys};result.update(status='inspection_only',schema_version=SCHEMA,source_id=SOURCE_ID,accounting_basis='Indian GAAP',unit='INR',source_scale='thousands',rights_status=RIGHTS,commercial_eligible=False,readiness_promoted=False,financial_coverage_promoted=False,periods=periods,withheld_fields=WITHHELD.copy(),observed_at=receipt['observed_at'],payload_sha256=receipt['payload_sha256'],source_receipts=[*selection['source_receipts'],{k:receipt[k] for k in ('source_url','observed_at','payload_sha256')}])
  result['registration_observation']=_registration(parser,document,selection)
  result['packet_digest']=_digest({k:v for k,v in result.items() if k!='packet_digest'})
  return result if validated_bank_html(result,'IBN','annual') is not None else {**held,'reason':'bank_packet_validation_failed'}
 except ValueError as error:
  reason=str(error)
  return {**held,'reason':reason if re.fullmatch(r'[a-z_]{1,160}',reason) else 'bank_html_evidence_unavailable'}
 except (TypeError,KeyError,IndexError,AttributeError,RecursionError):return held

def validated_bank_html(p,ticker,period_kind):
 if not isinstance(p,Mapping) or ticker!='IBN' or period_kind!='annual':return None
 try:
  if (p.get('schema_version')!=SCHEMA or p.get('source_id')!=SOURCE_ID or p.get('status')!='inspection_only' or p.get('ticker')!=ticker or p.get('sec_cik')!=CIK or p.get('period_kind')!=period_kind
      or p.get('accounting_basis')!='Indian GAAP' or p.get('unit')!='INR' or p.get('source_scale')!='thousands' or p.get('rights_status')!=RIGHTS
      or any(p.get(k) is not False for k in ('commercial_eligible','readiness_promoted','financial_coverage_promoted')) or p.get('withheld_fields')!=WITHHELD):return None
  acc=p['accession'];doc=p['primary_document']
  if not isinstance(acc,str) or not re.fullmatch(r'\d{10}-\d{2}-\d{6}',acc) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,180}\.(?:htm|html|xhtml)',doc) or '..' in doc:return None
  url=f'https://www.sec.gov/Archives/edgar/data/{int(CIK)}/{acc.replace("-","")}/{doc}'
  refs=p['source_receipts'];urls=[MAP_URL,f'https://data.sec.gov/submissions/CIK{CIK}.json',url]
  if p['source_url']!=url or len(refs)!=3 or any(not _reference_valid(r,u) for r,u in zip(refs,urls)):return None
  times=[_utc_timestamp(r['observed_at']) for r in refs]
  if not times[0]<=times[1]<=times[2] or times[-1]-times[0]>timedelta(hours=24) or p['observed_at']!=refs[-1]['observed_at'] or p['payload_sha256']!=refs[-1]['payload_sha256']:return None
  end=_iso_date(p['period_end']);filed=_iso_date(p['filed']);accepted=_utc_timestamp(p['accepted_at'])
  if (not end or end.strftime('%m-%d')!='03-31' or not filed or not accepted or not end<=filed<=times[-1].date() or not end<=accepted.date()<=times[-1].date() or accepted>times[-1] or p['form'] not in {'20-F','20-F/A'} or len(p['periods'])!=3):return None
  for y,row in enumerate(p['periods']):
   if row['period_start']!=f'{end.year-y-1}-04-01' or row['period_end']!=f'{end.year-y}-03-31' or set(row['fields'])|set(row['withheld_fields'])!=set(DEFINITIONS) or set(row['fields'])&set(row['withheld_fields']):return None
   if any(not isinstance(v,str) or not v for v in row['withheld_fields'].values()):return None
   for name,f in row['fields'].items():
    span=f['column_span'];anchor=f['anchor']
    if (f['field']!=name or f['label']!=DEFINITIONS[name][1] or f['definition']!=DEFINITIONS[name][2] or f['unit']!='INR' or f['scale']!=1000 or f['rights_status']!=RIGHTS
        or type(f['value']) not in {int,float} or f['value']!=_amount(f['raw_text']) or type(f['table_index']) is not int or not 0<=f['table_index']<=10000 or type(f['row_index']) is not int or not 0<=f['row_index']<500
        or not isinstance(span,list) or len(span)!=2 or any(type(n) is not int for n in span) or not 0<=span[0]<span[1]<=64
        or not isinstance(anchor,str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.-]{0,127}',anchor) or f['source_ref']!=url+'#'+anchor):return None
  if p['packet_digest']!=_digest({k:v for k,v in p.items() if k!='packet_digest'}):return None
  r=p['registration_observation']
  if r.get('current_legal_type_established') is not False:return None
  if r.get('status')=='observed_as_filed':
   if (r.get('declared_type')!='depositary_receipt' or r.get('label')!='American Depositary Shares' or r.get('as_of')!=p['filed'] or r.get('source_ref')!=url
       or type(r.get('table_index')) is not int or not 0<=r['table_index']<20
       or not isinstance(r.get('raw_cover_table'),str) or len(r['raw_cover_table'])>10000
       or not all(s in r['raw_cover_table'] for s in ('American Depositary Shares','IBN','The New York Stock Exchange','Trading Symbol'))
       or r.get('underlying_note')!='Not for trading, but only in connection with the registration of American Depositary Shares'):return None
  elif r!=dict(status='withheld',reason='qualified_cover_security_disclosure_unavailable',current_legal_type_established=False):return None
  return dict(p)
 except (KeyError,TypeError,ValueError,AttributeError,RecursionError):return None
