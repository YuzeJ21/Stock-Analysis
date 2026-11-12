"""Strict entity/context/unit-bound Inline XBRL inspection, no financial derivation."""
from collections import defaultdict
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from io import BytesIO
import hashlib
import re
import xml.etree.ElementTree as ET

from src.company_sec_online_preview import _iso_date, _utc_timestamp
from src.sec_exact_filing import RIGHTS, SCHEMA, SOURCE_ID, MAX_FILING_BYTES, _digest, BANK_SCHEMA, BANK_SOURCE_ID, valid_bank_scope

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

BANK_FIELDS=FIELDS+('net_interest_income','noninterest_income')
BANK_CATALOG={'us-gaap':{**CATALOG['us-gaap'],
 'net_interest_income':('InterestIncomeExpenseNet',),
 'noninterest_income':('NoninterestIncome',)}}


_HTML = '{http://www.w3.org/1999/xhtml}'
NEE_CAPITAL_PURCHASE_SCHEMA = 'sec-nee-capital-purchases-v1'
_NEE_SOURCE = 'https://www.sec.gov/Archives/edgar/data/753308/000075330826000081/nee-20260930.htm'
_NEE_NAMESPACE = 'http://www.nexteraenergy.com/20260930'
_NEE_START, _NEE_END = '2026-01-01', '2026-09-30'
_NEE_TOTAL = 'reported_capital_investment_total'
NEE_CAPITAL_PURCHASE_FIELDS = {
    _NEE_TOTAL: ('f-2280', 'issuer-extension', 'CapitalExpendituresIndependentPowerInvestmentsAndNuclearFuelPurchases',
                 'Capital expenditures, independent power and other investments and nuclear fuel purchases'),
    'fpl_capital_expenditures': ('f-347', 'issuer-extension', 'CapitalExpendituresOfFPL', 'Capital expenditures of FPL'),
    'neer_independent_power_and_other_investments': ('f-349', 'issuer-extension', 'IndependentPowerInvestments',
                                                    'Independent power and other investments of NEER'),
    'nuclear_fuel_purchases': ('f-351', 'us-gaap', 'PaymentsForProceedsFromNuclearFuel', 'Nuclear fuel purchases'),
    'other_capital_expenditures': ('f-353', 'issuer-extension', 'ProceedsPaymentsFromOtherCapitalExpenditures',
                                   'Other capital expenditures'),
}
_NEE_EVIDENCE = dict(status='inspection_only', schema_version=NEE_CAPITAL_PURCHASE_SCHEMA, period_kind='cumulative',
                     period_start=_NEE_START, period_end=_NEE_END, unit='USD',
                     capital_expenditures_equivalent=False, cash_generation_eligible=False)


def valid_numeric_proof(field):
    if not isinstance(field,dict) or not isinstance(field.get('raw_text'),str):return False
    if type(field.get('scale')) is not int or not isinstance(field.get('sign'),str) or field.get('sign') not in {'','-'} or not isinstance(field.get('decimals'),str):return False
    transformation=field.get('transformation')
    if transformation is not None and (not isinstance(transformation,str) or transformation not in {'num-dot-decimal','fixed-zero'}):return False
    node=ET.Element('number',dict(scale=str(field['scale']),sign=field['sign'],decimals=field['decimals']))
    node.text=field['raw_text']
    if transformation is not None:node.set('format','ixt:'+transformation)
    proof,_=_number(node,{'ixt':'http://www.xbrl.org/inlineXBRL/transformation/2020-02-12'})
    return proof is not None and all(field.get(k)==v for k,v in proof.items())


def valid_nee_capital_purchase_evidence(evidence, *, source_url):
    """Verify the filed nine-month investment disclosure without admitting a PP&E measure."""
    if (source_url != _NEE_SOURCE or not isinstance(evidence, Mapping) or set(evidence) != {*_NEE_EVIDENCE, 'fields'}
            or any(evidence[key] != value for key, value in _NEE_EVIDENCE.items())
            or any(evidence[key] is not False for key in ('capital_expenditures_equivalent', 'cash_generation_eligible'))):
        return False
    fields = evidence['fields']
    if not isinstance(fields, Mapping) or set(fields) != set(NEE_CAPITAL_PURCHASE_FIELDS):
        return False
    for key, (fact_id, taxonomy, concept, label) in NEE_CAPITAL_PURCHASE_FIELDS.items():
        field = fields[key]
        total = key == _NEE_TOTAL
        if (not isinstance(field, Mapping) or not valid_numeric_proof(dict(field)) or type(field.get('value')) is not int
                or field['value'] <= 0 or field.get('field') != key or field.get('label') != label
                or field.get('taxonomy') != taxonomy or field.get('concept') != concept
                or field.get('namespace_uri') != (_NEE_NAMESPACE if taxonomy == 'issuer-extension' else 'http://fasb.org/us-gaap/2026')
                or field.get('source_ref') != source_url + '#' + fact_id or field.get('fact_id') != fact_id
                or field.get('rights_status') != RIGHTS or field.get('unit') != 'USD' or field.get('unit_id') != 'usd'
                or field.get('context_id') != 'c-1' or field.get('period_start') != _NEE_START or field.get('period_end') != _NEE_END
                or field.get('scale') != 6 or field.get('decimals') != '-6' or field.get('sign') != ''
                or field.get('presentation') != ('reported_total' if total else 'cash_outflow')
                or field.get('statement') != ('segment_disclosure' if total else 'consolidated_cash_flows')):
            return False
        raw = field['raw_text']
        if field.get('presentation_evidence') != (raw if total else '(' + raw + ')'):
            return False
    return fields[_NEE_TOTAL]['value'] == sum(field['value'] for key, field in fields.items() if key != _NEE_TOTAL)


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
    # Registry 5 retains the existing English date and dot-decimal transformations.
    if uri == 'http://www.xbrl.org/inlineXBRL/transformation/2022-02-16':
        return name if name in {'date-monthname-day-year-en', 'num-dot-decimal'} else 'unsupported'
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


def _visible_text(node):
    return ' '.join(''.join(node.itertext()).split())


def _positioned_cells(row):
    offset, result = 0, []
    for cell in row:
        span = cell.get('colspan', '1')
        if (cell.tag not in {_HTML + 'td', _HTML + 'th'} or cell.get('rowspan', '1') != '1'
                or not re.fullmatch(r'[1-9][0-9]?', span) or offset + int(span) > 64):
            return []
        result.append((cell, offset, offset + int(span)))
        offset += int(span)
    return result


def _plain_header(row, label, start, end):
    from src.sec_html_bank import _hidden

    return not _hidden(row.attrib) and any((lo, hi) == (start, end) and _visible_text(cell) == label
               and not any(_hidden(node.attrib) for node in cell.iter())
               for cell, lo, hi in _positioned_cells(row))


def _preceding_label(rows, pattern):
    from src.sec_html_bank import _hidden

    for row in reversed(rows):
        for cell in row:
            label = _visible_text(cell)
            if pattern.fullmatch(label):
                return None if _hidden(row.attrib) or any(_hidden(node.attrib) for node in cell.iter()) else label
    return None


def _nee_cash_statement(table, rows, parents):
    wrapper = parents.get(table)
    scope = parents.get(wrapper)
    if scope is None:
        return False
    siblings = list(scope)
    index = siblings.index(wrapper)
    headings = siblings[max(index - 4, 0):index]
    from src.sec_html_bank import _hidden

    if ([_visible_text(node) for node in headings] != ['NEXTERA ENERGY, INC.',
            'CONDENSED CONSOLIDATED STATEMENTS OF CASH FLOWS', '(millions)', '(unaudited)']
            or any(_hidden(child.attrib) for node in headings for child in node.iter())):
        return False
    return (any(_plain_header(row, 'Nine Months Ended September 30,', 6, 15) for row in rows[:4])
            and any(_plain_header(row, '2026', 6, 9) and _plain_header(row, '2025', 12, 15) for row in rows[:4]))


def _nee_purchase_presentation(node, label, total, raw_text, parents):
    from src.sec_html_bank import _hidden

    ancestors = [node]
    while ancestors[-1] in parents:
        ancestors.append(parents[ancestors[-1]])
    if any(element.tag == f'{{{IX}}}hidden' or _hidden(element.attrib) for element in ancestors):
        return None
    path = {element.tag: element for element in ancestors[1:]}
    table, row, cell = (path.get(_HTML + name) for name in ('table', 'tr', 'td'))
    if table is None or row is None or cell is None or parents.get(cell) != row:
        return None
    rows = list(table.iter(_HTML + 'tr'))
    if row not in rows or len(rows) > 100 or len([part for part in ancestors if part.tag == _HTML + 'table']) != 1:
        return None
    prior = rows[:rows.index(row)]
    if (not _plain_header(row, label, 0, 3)
            or any(_hidden(child.attrib) for child in cell.iter())):
        return None
    span = (28, 29) if total else (6, 8)
    if not any(part is cell and (start, stop) == span for part, start, stop in _positioned_cells(row)):
        return None
    if total:
        # The segment table has a three-month section before this nine-month row.
        duration = re.compile(r'(?:Three|Six|Nine|Twelve) Months Ended [A-Za-z]+ [0-9]{1,2}, [0-9]{4}')
        if (_preceding_label(prior, duration) != 'Nine Months Ended September 30, 2026'
                or not any(_plain_header(head, 'TotalConsolidated', 27, 30) or _plain_header(head, 'Total Consolidated', 27, 30)
                           for head in prior[:5])
                or not any(_plain_header(head, '(millions)', 3, 30) for head in prior[:5])):
            return None
        expected = raw_text
    else:
        investing = re.compile(r'CASH FLOWS FROM [A-Z ]+ ACTIVITIES')
        if (_preceding_label(prior, investing) != 'CASH FLOWS FROM INVESTING ACTIVITIES'
                or not _nee_cash_statement(table, rows, parents)):
            return None
        expected = '(' + raw_text + ')'
    return (expected, table) if _visible_text(cell) == expected else None


def _nee_capital_purchases(root, namespaces, contexts, units, selection):
    if (any(selection.get(key) != value for key, value in {'ticker': 'NEE', 'sec_cik': '0000753308',
            'accession': '0000753308-26-000081', 'form': '10-Q', 'period_kind': 'quarterly',
            'period_end': _NEE_END, 'source_url': _NEE_SOURCE}.items())
            or contexts.get('c-1') != {'start': _NEE_START, 'end': _NEE_END} or units.get('usd') != 'USD'):
        return None
    accepted = {_NEE_NAMESPACE, 'http://fasb.org/us-gaap/2026'}
    nodes = defaultdict(list)
    for node in root.iter(f'{{{IX}}}nonFraction'):
        uri, concept = _qname(node.get('name'), namespaces)
        if uri in accepted and node.get('contextRef') == 'c-1':
            nodes[(uri, concept)].append(node)
    parents = {child: parent for parent in root.iter() for child in parent}
    fields = {}
    cash_table = None
    for key, (fact_id, taxonomy, concept, label) in NEE_CAPITAL_PURCHASE_FIELDS.items():
        uri = _NEE_NAMESPACE if taxonomy == 'issuer-extension' else 'http://fasb.org/us-gaap/2026'
        matches = nodes[(uri, concept)]
        if len(matches) != 1 or matches[0].get('id') != fact_id or matches[0].get('unitRef') != 'usd':
            return None
        node = matches[0]
        number, _ = _number(node, namespaces)
        total = key == _NEE_TOTAL
        presentation = _nee_purchase_presentation(node, label, total, number['raw_text'], parents) if number else None
        if presentation is None:
            return None
        literal, table = presentation
        if not total:
            if cash_table is not None and cash_table is not table:
                return None
            cash_table = table
        fields[key] = dict(field=key, label=label, taxonomy=taxonomy, concept=concept, namespace_uri=uri,
                           unit='USD', unit_id='usd', context_id='c-1', period_start=_NEE_START, period_end=_NEE_END,
                           fact_id=fact_id, source_ref=_NEE_SOURCE + '#' + fact_id, rights_status=RIGHTS,
                           presentation='reported_total' if total else 'cash_outflow', presentation_evidence=literal,
                           statement='segment_disclosure' if total else 'consolidated_cash_flows', **number)
    evidence = dict(_NEE_EVIDENCE, fields=fields)
    return evidence if valid_nee_capital_purchase_evidence(evidence, source_url=_NEE_SOURCE) else None


def extract_inline_filing(raw,selection,receipt):
    held=dict(status='withheld',ticker=selection.get('ticker'),period_kind=selection.get('period_kind'),reason='inline_filing_unavailable',periods=[])
    if (selection.get('status')!='selected' or receipt.get('status')!='ready'
        or receipt.get('source_url')!=selection.get('source_url') or not isinstance(raw,bytes)
        or receipt.get('payload_sha256')!=hashlib.sha256(raw).hexdigest()):return held
    bank='bank_scope' in selection
    if bank and not valid_bank_scope(selection['bank_scope'],selection.get('sec_cik'),selection.get('source_receipts')):return {**held,'reason':'bank_classification_unverified'}
    catalog,field_names=(BANK_CATALOG,BANK_FIELDS) if bank else (CATALOG,FIELDS)
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
        if not context or tax not in catalog or not any(name in concepts for concepts in catalog[tax].values()):continue
        days=(_iso_date(end)-_iso_date(context['start'])).days
        target='annual' if kind=='annual' and 300<=days<=430 else 'quarterly' if kind=='quarterly' and 70<=days<=105 else 'cumulative' if kind=='quarterly' and 105<days<=320 else None
        if not target:continue
        facts.append(dict(node=node,taxonomy=tax,namespace_uri=uri,concept=name,context=context,kind=target,unit=units.get(node.get('unitRef'))))
    primary=[f for f in facts if f['kind']==kind and f['concept'] in catalog[f['taxonomy']]['revenue']]
    if bank and not primary:primary=[f for f in facts if f['kind']==kind and f['concept']=='InterestIncomeExpenseNet']
    taxonomies={f['taxonomy'] for f in primary}
    if len(taxonomies)!=1:return {**held,'reason':'ambiguous_or_missing_reporting_taxonomy'}
    tax=next(iter(taxonomies));primary=[f for f in primary if f['taxonomy']==tax]
    if any(f['unit'] is None for f in primary):return {**held,'reason':'unresolved_reporting_unit'}
    native={f['unit'] for f in primary}-{'USD'}
    if len(native)>1:return {**held,'reason':'ambiguous_reporting_currency'}
    unit=next(iter(native)) if native else 'USD'
    if bank and unit!='USD':return {**held,'reason':'bank_native_usd_required'}
    periods=[]
    for target in (kind,'cumulative') if kind=='quarterly' else (kind,):
        eligible=[f for f in facts if f['taxonomy']==tax and f['kind']==target and f['unit']==unit]
        if not eligible and target=='cumulative':continue
        starts={f['context']['start'] for f in eligible}
        if len(starts)!=1:
            if target==kind:return {**held,'reason':'ambiguous_filing_period_start'}
            continue
        start=next(iter(starts));fields={};holds={}
        for field in field_names:
            candidates=[]
            for concept in catalog[tax][field]:
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
    result.update(status='inspection_only',schema_version=BANK_SCHEMA if bank else SCHEMA,source_id=BANK_SOURCE_ID if bank else SOURCE_ID,rights_status=RIGHTS,
        commercial_eligible=False,readiness_promoted=False,taxonomy=tax,unit=unit,periods=periods,
        observed_at=receipt['observed_at'],payload_sha256=receipt['payload_sha256'],
        source_receipts=[*selection['source_receipts'],{k:receipt[k] for k in ('source_url','observed_at','payload_sha256')}])
    capital_purchases = _nee_capital_purchases(root, namespaces, contexts, units, selection)
    if capital_purchases:
        result['capital_purchase_evidence'] = capital_purchases
    result['packet_digest']=_digest(result)
    return result
