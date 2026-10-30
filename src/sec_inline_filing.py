"""Strict entity/context/unit-bound Inline XBRL inspection, no financial derivation."""
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from io import BytesIO
import hashlib
import re
import xml.etree.ElementTree as ET

from src.company_sec_online_preview import _iso_date, _utc_timestamp
from src.sec_exact_filing import RIGHTS, SCHEMA, SOURCE_ID, MAX_FILING_BYTES, _digest

X='http://www.xbrl.org/2003/instance'
IX='http://www.xbrl.org/2013/inlineXBRL'
XSI='http://www.w3.org/2001/XMLSchema-instance'
ISO='http://www.xbrl.org/2003/iso4217'
FIELDS=('revenue','operating_income','cash_from_operations','capital_expenditures')
MAX_ELEMENTS=350000
CATALOG={
 'us-gaap':{
  'revenue':('Revenues','RegulatedAndUnregulatedOperatingRevenue','RevenuesNetOfInterestExpense','RevenueFromContractWithCustomerExcludingAssessedTax','RevenueFromContractWithCustomerIncludingAssessedTax','SalesRevenueNet','SalesRevenueGoodsNet'),
  'operating_income':('OperatingIncomeLoss',),
  'cash_from_operations':('NetCashProvidedByUsedInOperatingActivities','NetCashProvidedByUsedInOperatingActivitiesContinuingOperations'),
  'capital_expenditures':('PaymentsToAcquirePropertyPlantAndEquipment','PaymentsToAcquireProductiveAssets')},
 'ifrs-full':{
  'revenue':('Revenue','RevenueFromContractsWithCustomers'),
  'operating_income':('ProfitLossFromOperatingActivities',),
  'cash_from_operations':('CashFlowsFromUsedInOperatingActivities','CashFlowsFromUsedInOperatingActivitiesContinuingOperations'),
  'capital_expenditures':('PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities',)}}


def _qname(value,namespaces):
    if not isinstance(value,str) or value.count(':')!=1:return None,None
    prefix,name=value.split(':')
    return namespaces.get(prefix),name


def _taxonomy(uri):
    if isinstance(uri,str) and re.fullmatch(r'https?://fasb.org/us-gaap/\d{4}',uri):return 'us-gaap'
    if isinstance(uri,str) and re.fullmatch(r'https?://xbrl.ifrs.org/taxonomy/\d{4}-\d{2}-\d{2}/ifrs-full',uri):return 'ifrs-full'
    return None


def _transform(value,namespaces):
    if value is None:return None
    uri,name=_qname(value,namespaces)
    if uri not in {'http://www.xbrl.org/inlineXBRL/transformation/2020-02-12','http://www.xbrl.org/inlineXBRL/transformation/2015-02-26'}:return 'unsupported'
    return name


def _date_fact(node,namespaces):
    text=' '.join(''.join(node.itertext()).split());fmt=_transform(node.get('format'),namespaces)
    if fmt is None:return _iso_date(text)
    if fmt!='date-monthname-day-year-en':return None
    months={m:i+1 for i,m in enumerate(('January','February','March','April','May','June','July','August','September','October','November','December'))}
    match=re.fullmatch(r'([A-Za-z]+) (\d{1,2}), (\d{4})',text)
    if not match or match[1] not in months:return None
    return _iso_date(f'{match[3]}-{months[match[1]]:02d}-{int(match[2]):02d}')


def _number(node,namespaces):
    raw=''.join(node.itertext()).strip();fmt=_transform(node.get('format'),namespaces)
    if (node.get(f'{{{XSI}}}nil') not in {None,'false','0'} or node.get('continuedAt') is not None
        or node.get('target') not in {None,''} or node.get('tupleRef') is not None
        or any(n.tag not in {f'{{http://www.w3.org/1999/xhtml}}{tag}' for tag in ('span','b','strong','i','em','u','font','small')}
               for n in node.iter() if n is not node)
        or len(raw)>100):return None,'unsupported_or_nil_numeric_fact'
    scale=node.get('scale','0');sign=node.get('sign','');decimals=node.get('decimals')
    if (not re.fullmatch(r'-?\d{1,2}',scale) or not -12<=int(scale)<=12 or sign not in {'','-'}
        or decimals is None or not re.fullmatch(r'(?:INF|-?\d{1,2})',decimals)):
        return None,'invalid_numeric_attributes'
    if fmt=='fixed-zero':clean='0'
    elif fmt in {None,'num-dot-decimal'}:
        clean=raw.replace(',','') if fmt else raw
        if not re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)',clean):return None,'unsupported_numeric_text'
        if fmt and not re.fullmatch(r'(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|\.\d+',raw):return None,'unsupported_numeric_text'
    else:return None,'unsupported_numeric_transformation'
    try:
        amount=Decimal(clean)*(Decimal(10)**int(scale))
        if sign=='-':amount=-amount
        if not amount.is_finite() or abs(amount)>Decimal('1e20'):return None,'nonfinite_or_unbounded_value'
        value=int(amount) if amount==amount.to_integral_value() else float(amount)
    except (InvalidOperation,ValueError,OverflowError):return None,'invalid_numeric_value'
    return dict(value=value,raw_text=raw,scale=int(scale),sign=sign,decimals=decimals,transformation=fmt),None


def _tree(raw):
    if not isinstance(raw,bytes) or not 0<len(raw)<=MAX_FILING_BYTES or b'<!doctype' in raw.lower() or b'<!entity' in raw.lower():raise ValueError('unsafe_or_unbounded_filing_xml')
    # The validated subset is UTF-8; reject encodings that hide markup from the byte guards.
    if b'\x00' in raw:raise ValueError('unsupported_filing_encoding')
    try:text=raw.decode('utf-8-sig')
    except UnicodeDecodeError as error:raise ValueError('unsupported_filing_encoding') from error
    declaration=re.match(r'\s*<\?xml\b[^?]*\bencoding\s*=\s*[\'"]([^\'"]+)[\'"]',text,re.I)
    if declaration and declaration[1].lower() not in {'utf-8','utf8','us-ascii','ascii'}:raise ValueError('unsupported_filing_encoding')
    namespaces={};ids=set();count=0
    parser=ET.iterparse(BytesIO(raw),events=('start-ns','start','end'))
    for event,node in parser:
        if event=='start-ns':
            prefix,uri=node
            if prefix in namespaces and namespaces[prefix]!=uri:raise ValueError('ambiguous_namespace_binding')
            namespaces[prefix]=uri
        elif event=='start':
            count+=1
            if count>MAX_ELEMENTS:raise ValueError('filing_element_limit')
            identity=node.get('id')
            if identity:
                if identity in ids:raise ValueError('duplicate_document_id')
                ids.add(identity)
    return parser.root,namespaces


def extract_inline_filing(raw,selection,receipt):
    held=dict(status='withheld',ticker=selection.get('ticker'),period_kind=selection.get('period_kind'),reason='inline_filing_unavailable',periods=[])
    if (selection.get('status')!='selected' or receipt.get('status')!='ready'
        or receipt.get('source_url')!=selection.get('source_url') or not isinstance(raw,bytes)
        or receipt.get('payload_sha256')!=hashlib.sha256(raw).hexdigest()):return held
    try:root,namespaces=_tree(raw)
    except (ET.ParseError,ValueError,TypeError,RecursionError) as error:return {**held,'reason':str(error) if isinstance(error,ValueError) and not isinstance(error,ET.ParseError) else 'invalid_filing_xml'}
    cik=selection['sec_cik'];end=selection['period_end'];kind=selection['period_kind']
    contexts={};units={}
    for node in root.iter(f'{{{X}}}context'):
        entity=node.find(f'{{{X}}}entity');period=node.find(f'{{{X}}}period')
        if (entity is None or period is None or len(node)!=2 or len(entity)!=1 or len(period)!=2
            or sum(child.tag==f'{{{X}}}entity' for child in node)!=1
            or sum(child.tag==f'{{{X}}}period' for child in node)!=1
            or {child.tag for child in period}!={f'{{{X}}}startDate',f'{{{X}}}endDate'}):continue
        ident=entity.find(f'{{{X}}}identifier');start=period.find(f'{{{X}}}startDate');finish=period.find(f'{{{X}}}endDate')
        if (ident is None or ident.get('scheme')!='http://www.sec.gov/CIK' or not isinstance(ident.text,str)
            or not re.fullmatch(r'\d{1,10}',ident.text.strip()) or str(int(ident.text)).zfill(10)!=cik
            or start is None or finish is None or _iso_date(start.text) is None or _iso_date(finish.text) is None):continue
        if finish.text==end and _iso_date(start.text)<_iso_date(end):contexts[node.get('id')]=dict(start=start.text,end=finish.text)
    for node in root.iter(f'{{{X}}}unit'):
        if len(node)!=1 or node[0].tag!=f'{{{X}}}measure':continue
        uri,currency=_qname((node[0].text or '').strip(),namespaces)
        if uri==ISO and currency and re.fullmatch(r'[A-Z]{3}',currency):units[node.get('id')]=currency
    dei=defaultdict(list)
    for node in root.iter(f'{{{IX}}}nonNumeric'):
        uri,name=_qname(node.get('name'),namespaces)
        if (not uri or not re.fullmatch(r'https?://xbrl.sec.gov/dei/\d{4}',uri)
            or node.get('contextRef') not in contexts):continue
        if name in {'EntityCentralIndexKey','DocumentType','DocumentPeriodEndDate','AmendmentFlag'}:
            if node.get(f'{{{XSI}}}nil') not in {None,'false','0'} or node.get('continuedAt') is not None:
                return {**held,'reason':'unusable_filing_identity_fact'}
            dei[name].append(node)
    def texts(name):return {' '.join(''.join(n.itertext()).split()) for n in dei[name]}
    declared_ciks=texts('EntityCentralIndexKey');declared_forms=texts('DocumentType');amend=texts('AmendmentFlag')
    dates={_date_fact(n,namespaces) for n in dei['DocumentPeriodEndDate']}
    amendment=selection['form'].endswith('/A');base_form=selection['form'].removesuffix('/A')
    if (not declared_ciks or any(not re.fullmatch(r'\d{1,10}',v) or str(int(v)).zfill(10)!=cik for v in declared_ciks)
        or len(declared_forms)!=1 or not declared_forms<={selection['form'],base_form}
        or dates!={_iso_date(end)} or {v.lower() for v in amend}!={str(amendment).lower()}):return {**held,'reason':'filing_dei_identity_or_period_mismatch'}
    facts=[]
    for node in root.iter(f'{{{IX}}}nonFraction'):
        context=contexts.get(node.get('contextRef'));uri,name=_qname(node.get('name'),namespaces);tax=_taxonomy(uri)
        if not context or not tax or not any(name in concepts for concepts in CATALOG[tax].values()):continue
        days=(_iso_date(end)-_iso_date(context['start'])).days
        target='annual' if kind=='annual' and 300<=days<=430 else 'quarterly' if kind=='quarterly' and 70<=days<=105 else 'cumulative' if kind=='quarterly' and 105<days<=320 else None
        if not target:continue
        facts.append(dict(node=node,taxonomy=tax,namespace_uri=uri,concept=name,context=context,kind=target,unit=units.get(node.get('unitRef'))))
    primary=[f for f in facts if f['kind']==kind and f['concept'] in CATALOG[f['taxonomy']]['revenue']]
    taxonomies={f['taxonomy'] for f in primary}
    if len(taxonomies)!=1:return {**held,'reason':'ambiguous_or_missing_reporting_taxonomy'}
    tax=next(iter(taxonomies));primary=[f for f in primary if f['taxonomy']==tax]
    if any(f['unit'] is None for f in primary):return {**held,'reason':'unresolved_reporting_unit'}
    native={f['unit'] for f in primary}-{'USD'}
    if len(native)>1:return {**held,'reason':'ambiguous_reporting_currency'}
    unit=next(iter(native)) if native else 'USD'
    periods=[]
    for target in (kind,'cumulative') if kind=='quarterly' else (kind,):
        eligible=[f for f in facts if f['taxonomy']==tax and f['kind']==target and f['unit']==unit]
        if not eligible and target=='cumulative':continue
        starts={f['context']['start'] for f in eligible}
        if len(starts)!=1:
            if target==kind:return {**held,'reason':'ambiguous_filing_period_start'}
            continue
        start=next(iter(starts));fields={};holds={}
        for field in FIELDS:
            candidates=[]
            for concept in CATALOG[tax][field]:
                candidates=[f for f in eligible if f['concept']==concept]
                if candidates:break
            if not candidates:holds[field]='matching_direct_native_unit_fact_unavailable';continue
            numbers=[_number(f['node'],namespaces) for f in candidates]
            if any(n is None for n,_ in numbers):holds[field]=next(reason for n,reason in numbers if n is None);continue
            if len({n['value'] for n,_ in numbers})!=1:holds[field]='conflicting_direct_facts';continue
            candidate=candidates[0];node=candidate['node'];identity=node.get('id','')
            if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.-]{0,127}',identity):holds[field]='source_fact_id_unavailable';continue
            fields[field]=dict(field=field,taxonomy=tax,concept=candidate['concept'],namespace_uri=candidate['namespace_uri'],
                unit=unit,unit_id=node.get('unitRef'),context_id=node.get('contextRef'),period_start=start,period_end=end,
                fact_id=identity,source_ref=selection['source_url']+'#'+identity,rights_status=RIGHTS,
                **numbers[0][0])
        periods.append(dict(kind=target,period_start=start,period_end=end,fields=fields,withheld_fields=holds))
    result={k:v for k,v in selection.items() if k not in {'status','source_receipts'}}
    result.update(status='inspection_only',schema_version=SCHEMA,source_id=SOURCE_ID,rights_status=RIGHTS,
        commercial_eligible=False,readiness_promoted=False,taxonomy=tax,unit=unit,periods=periods,
        observed_at=receipt['observed_at'],payload_sha256=receipt['payload_sha256'],
        source_receipts=[*selection['source_receipts'],{k:receipt[k] for k in ('source_url','observed_at','payload_sha256')}])
    result['packet_digest']=_digest(result)
    return result
