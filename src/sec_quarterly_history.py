"""Direct quarter-length financial periods; cumulative cash flows stay separate."""

import re
from collections import defaultdict
from collections.abc import Mapping

from src.company_sec_online_preview import (
    ANNUAL_FORMS, REVENUE_CONCEPTS, OPERATING_COMPONENT_CONCEPTS,
    _iso_date, _utc_timestamp, _finite_direct_number,
)
from src.commercial_source_rights import load_source_rights_registry, review_commercial_field_scope
from src.sec_fundamentals_preview import _valid_companyfacts_payload

FIELDS=('revenue','operating_income','cash_from_operations','capital_expenditures')
FORMS=ANNUAL_FORMS | {'10-Q','10-Q/A'}
RIGHTS='approved_field_scope_raw_redistribution_held'
_REVENUES=[('us-gaap',x) for x in ('RevenueFromContractWithCustomerExcludingAssessedTax','Revenues','SalesRevenueNet','SalesRevenueGoodsNet')]


def field_is_permitted(field):
    try:
        return review_commercial_field_scope(load_source_rights_registry(),'sec_companyfacts',[field]).commercial_evidence_ready
    except (ValueError,OSError): return False


def _context(raw, observed):
    start,end,filed=(_iso_date(raw.get(x)) for x in ('start','end','filed'))
    if (start is None or end is None or filed is None or not start<end<=filed<=observed.date()
        or not isinstance(raw.get('form'),str) or raw['form'] not in FORMS
        or not isinstance(raw.get('accn'),str) or not re.fullmatch(r'\d{10}-\d{2}-\d{6}',raw['accn'])):
        return None
    return start,end,filed


def _records(payload, key):
    return payload['facts'].get(key[0],{}).get(key[1],{}).get('units',{}).get('USD',[])


def _direct(payload, field, concepts, context, source, observed_at, permitted):
    if not permitted: return None,'field_scope_unreviewed'
    for taxonomy,concept in concepts:
        rows=[r for r in _records(payload,(taxonomy,concept)) if all(r.get(k)==v for k,v in context.items())]
        if not rows: continue
        if any(not _finite_direct_number(r.get('val')) for r in rows) or len({r['val'] for r in rows})!=1:
            return None,'raw_source_conflict'
        return {'field':field,'taxonomy':taxonomy,'concept':concept,'unit':'USD','value':rows[0]['val'],
                'period_start':context['start'],'period_end':context['end'],'filed':context['filed'],
                'accession':context['accn'],'form':context['form'],'source_ref':source,
                'observed_at':observed_at,'rights_status':RIGHTS},None
    return None,'matching_direct_fact_unavailable'


def build_sec_quarterly_history(ticker,payload,*,expected_cik,observed_at,source_url,payload_sha256,anchor_concept=None,max_periods=12):
    held={'status':'withheld','ticker':ticker,'periods':[],'reason':'quarterly_source_unavailable'}
    observed=_utc_timestamp(observed_at)
    if (not isinstance(ticker,str) or not re.fullmatch(r'[A-Z0-9][A-Z0-9.-]{0,19}',ticker)
        or not isinstance(expected_cik,str) or not re.fullmatch(r'\d{10}',expected_cik) or int(expected_cik)==0
        or source_url!=f'https://data.sec.gov/api/xbrl/companyfacts/CIK{expected_cik}.json'
        or observed is None or not isinstance(payload_sha256,str) or not re.fullmatch(r'[0-9a-f]{64}',payload_sha256)
        or type(max_periods) is not int or max_periods<1 or not _valid_companyfacts_payload(payload)):
        return held
    raw_cik=payload.get('cik')
    if type(raw_cik) not in {int,str} or not re.fullmatch(r'\d{1,10}',str(raw_cik)) or str(int(raw_cik)).zfill(10)!=expected_cik:
        return {**held,'reason':'companyfacts_identity_mismatch'}
    permitted={f:field_is_permitted(f) for f in FIELDS}
    if not permitted['revenue']: return {**held,'reason':'field_scope_unreviewed'}
    if anchor_concept is not None and (not isinstance(anchor_concept,tuple) or not all(isinstance(v,str) for v in anchor_concept) or anchor_concept not in REVENUE_CONCEPTS): return held
    candidates=[]
    for key in ([anchor_concept] if anchor_concept else _REVENUES):
        quarter_rows=[r for r in _records(payload,key) if (c:=_context(r,observed)) and 70<=(c[1]-c[0]).days<=105]
        if quarter_rows: candidates.append((key,quarter_rows))
    if not candidates: return {**held,'reason':'supported_direct_quarter_revenue_unavailable'}
    # Pin one reported revenue definition across history; never stitch definitions.
    newest=max(max(r['end'] for r in rows) for _,rows in candidates)
    key,quarter_rows=next((k,rows) for k,rows in candidates if max(r['end'] for r in rows)==newest)
    groups=defaultdict(list)
    for raw in quarter_rows: groups[raw['end']].append(raw)
    periods=[]
    for end,rows in sorted(groups.items())[-min(max_periods,12):]:
        filed=max(r['filed'] for r in rows)
        contexts={(r['start'],r['accn'],r['form']) for r in rows if r['filed']==filed}
        starts={r['start'] for r in rows}
        row={'period_end':end,'period_start':next(iter(starts)) if len(starts)==1 else None,'filed':filed,
             'status':'withheld','fields':{},'cumulative_fields':{},'cumulative_anchor':None,
             'withheld_fields':{f:'quarter_revenue_withheld' for f in FIELDS},'reason':'ambiguous_quarter_context'}
        if len(contexts)!=1 or len(starts)!=1:
            periods.append(row); continue
        start,accession,form=next(iter(contexts))
        context={'start':start,'end':end,'filed':filed,'accn':accession,'form':form}
        anchor,reason=_direct(payload,'revenue',[key],context,source_url,observed_at,True)
        if anchor is None:
            row['reason']=reason; periods.append(row); continue
        row.update(status='available',reason=None,accession=accession,form=form,fields={'revenue':anchor},withheld_fields={})
        cumulative=[r for r in _records(payload,key) if r.get('end')==end and r.get('accn')==accession
                    and r.get('form')==form and r.get('filed')==filed
                    and (c:=_context(r,observed)) and 105<(c[1]-c[0]).days<=320 and c[0]<_iso_date(start)]
        cumulative_starts={r['start'] for r in cumulative}
        cumulative_context=None
        if len(cumulative_starts)==1:
            cumulative_context={**context,'start':next(iter(cumulative_starts))}
            row['cumulative_anchor'],_=_direct(payload,'revenue',[key],cumulative_context,source_url,observed_at,True)
            if row['cumulative_anchor'] is None: cumulative_context=None
        for field in FIELDS[1:]:
            concepts=sorted(OPERATING_COMPONENT_CONCEPTS[field],key=lambda k:('ContinuingOperations' in k[1],k[1]))
            direct,reason=_direct(payload,field,concepts,context,source_url,observed_at,permitted[field])
            if direct is not None: row['fields'][field]=direct
            else: row['withheld_fields'][field]=reason
            if field in {'cash_from_operations','capital_expenditures'} and cumulative_context:
                cumulative_field,_=_direct(payload,field,concepts,cumulative_context,source_url,observed_at,permitted[field])
                if cumulative_field:
                    row['cumulative_fields'][field]=cumulative_field
                    if direct is None and reason=='matching_direct_fact_unavailable':
                        row['withheld_fields'][field]='only_cumulative_fact_available'
        periods.append(row)
    return {'status':'inspection_only','ticker':ticker,'sec_cik':expected_cik,'source_url':source_url,
            'observed_at':observed_at,'payload_sha256':payload_sha256,'taxonomy':key[0],'concept':key[1],
            'unit':'USD','history_basis':'latest_reported_as_observed_not_point_in_time','periods':periods}


def validated_quarterly_history(view):
    """Reject malformed cached evidence before any field is displayed or counted."""
    h=view.get('quarterly_history'); identity=view.get('companyfacts_identity')
    if not isinstance(h,Mapping) or not isinstance(identity,Mapping) or h.get('status')!='inspection_only': return None
    if identity.get('status')!='source_matched' or h.get('ticker')!=view.get('ticker'): return None
    if any(h.get(k)!=identity.get(k) for k in ('ticker','sec_cik','source_url','observed_at','payload_sha256')): return None
    cik=h.get('sec_cik'); observed=_utc_timestamp(h.get('observed_at'))
    if (not isinstance(cik,str) or not re.fullmatch(r'\d{10}',cik) or int(cik)==0
        or h.get('source_url')!=f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json'
        or observed is None or not isinstance(h.get('payload_sha256'),str) or not re.fullmatch(r'[0-9a-f]{64}',h['payload_sha256'])
        or h.get('unit')!='USD' or h.get('history_basis')!='latest_reported_as_observed_not_point_in_time'):
        return None
    key=(h.get('taxonomy'),h.get('concept'))
    if not all(isinstance(v,str) for v in key) or key not in REVENUE_CONCEPTS: return None
    periods=h.get('periods')
    if not isinstance(periods,list) or not 1<=len(periods)<=12: return None
    previous=None
    def valid_field(field,name,row,*,cumulative=False):
        if not isinstance(field,Mapping) or field.get('field')!=name or field.get('unit')!='USD': return False
        concept=(field.get('taxonomy'),field.get('concept'))
        accepted={key} if name=='revenue' else OPERATING_COMPONENT_CONCEPTS.get(name,frozenset())
        if not all(isinstance(v,str) for v in concept) or concept not in accepted: return False
        if field.get('rights_status')!=RIGHTS or not _finite_direct_number(field.get('value')): return False
        if any(field.get(k)!=v for k,v in (
            ('source_ref',h['source_url']),('observed_at',h['observed_at']),('period_end',row['period_end']),
            ('filed',row['filed']),('accession',row['accession']),('form',row['form']))): return False
        start=_iso_date(field.get('period_start')); end=_iso_date(row['period_end'])
        if start is None: return False
        if cumulative:
            return start<_iso_date(row['period_start']) and 105<(end-start).days<=320
        return field.get('period_start')==row['period_start']
    for row in periods:
        if not isinstance(row,Mapping): return None
        start,end,filed=(_iso_date(row.get(k)) for k in ('period_start','period_end','filed'))
        if end is None or filed is None or not end<=filed<=observed.date() or previous is not None and end<=previous: return None
        previous=end
        if row.get('status')=='withheld':
            if row.get('period_start') is not None and (start is None or not 70<=(end-start).days<=105): return None
            if row.get('fields')!={} or row.get('cumulative_fields')!={} or row.get('cumulative_anchor') is not None: return None
            if not isinstance(row.get('reason'),str) or row['reason'] not in {'ambiguous_quarter_context','raw_source_conflict','matching_direct_fact_unavailable'}: return None
            continue
        if (row.get('status')!='available' or start is None or not 70<=(end-start).days<=105
            or not isinstance(row.get('accession'),str) or not re.fullmatch(r'\d{10}-\d{2}-\d{6}',row['accession'])
            or not isinstance(row.get('form'),str) or row['form'] not in FORMS): return None
        fields=row.get('fields'); withheld=row.get('withheld_fields'); cumulative=row.get('cumulative_fields')
        if not all(isinstance(v,Mapping) for v in (fields,withheld,cumulative)): return None
        if ('revenue' not in fields or set(fields)|set(withheld)!=set(FIELDS) or set(fields)&set(withheld)
            or not set(cumulative)<={'cash_from_operations','capital_expenditures'}): return None
        if any(not valid_field(f,name,row) for name,f in fields.items()): return None
        if any(not isinstance(reason,str) or reason not in {'field_scope_unreviewed','raw_source_conflict','matching_direct_fact_unavailable','only_cumulative_fact_available'} for reason in withheld.values()): return None
        anchor=row.get('cumulative_anchor')
        if cumulative or anchor is not None:
            if not valid_field(anchor,'revenue',row,cumulative=True): return None
            if any(not valid_field(f,name,row,cumulative=True) or f['period_start']!=anchor['period_start'] for name,f in cumulative.items()): return None
        if any(withheld.get(name)=='only_cumulative_fact_available' and name not in cumulative for name in FIELDS): return None
    return dict(h)

