"""Metadata-only exact-filing check; never imports archive monetary values."""
import re
from src.company_sec_online_preview import _iso_date, _utc_timestamp
from src.sec_exact_filing import validated_filing_preview
from src.sec_inline_filing import RIGHTS

CHECK_KEYS = {'source_url','payload_sha256','observed_at','filed','accepted_at','accession',
    'primary_document','sec_cik','form','period_start','period_end','taxonomy','concept','unit',
    'rights_status','reason'}
REASONS = {'matching_direct_native_unit_fact_unavailable','conflicting_direct_facts',
    'exact_direct_fact_rights_held','exact_direct_fact_unusable'}


def validate_check(check, packet):
    if not isinstance(check,dict) or set(check)!=CHECK_KEYS:
        raise ValueError('invalid_operating_income_check')
    if any(not isinstance(value,str) for value in check.values()):
        raise ValueError('invalid_operating_income_check')
    for key in ('sec_cik','accession','form','period_end'):
        if check[key]!=packet[key]:raise ValueError('exact_filing_basis_mismatch')
    if check['filed']!=packet['filing_date']:raise ValueError('exact_filing_basis_mismatch')
    anchors=[r for r in packet['fields'] if r['field']=='revenue']
    if len(anchors)!=1 or any(check[k]!=anchors[0][k] for k in ('period_start','period_end','taxonomy','unit')):
        raise ValueError('exact_filing_basis_mismatch')
    doc=check['primary_document']
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,180}\.(?:htm|html|xhtml)',doc) or '..' in doc:
        raise ValueError('invalid_exact_filing_document')
    url=f'https://www.sec.gov/Archives/edgar/data/{int(packet["sec_cik"])}/{packet["accession"].replace("-","")}/{doc}'
    if (check['source_url']!=url or not re.fullmatch('[0-9a-f]{64}',check['payload_sha256'])
            or check['taxonomy']!='us-gaap' or check['concept']!='OperatingIncomeLoss'
            or check['unit']!='USD' or check['rights_status']!=RIGHTS or check['reason'] not in REASONS):
        raise ValueError('invalid_exact_filing_provenance')
    saved=_utc_timestamp(packet['saved_at']);observed=_utc_timestamp(check['observed_at'])
    accepted=_utc_timestamp(check['accepted_at']);filed=_iso_date(check['filed'])
    if not observed or not accepted or not filed or not accepted<=observed<=saved or not filed<=observed.date() or accepted.date()!=filed:
        raise ValueError('invalid_exact_filing_dates')
    if [g for g in packet['gaps'] if g['field']=='operating_income']!=[dict(field='operating_income',reason=check['reason'])]:
        raise ValueError('exact_filing_gap_mismatch')
    return check


def build_check(preview, packet):
    source=validated_filing_preview(preview,'NEM','annual')
    if source is None or source.get('source_id')!='sec_archive_inline':
        raise ValueError('unqualified_exact_filing')
    annual=next(p for p in source['periods'] if p['kind']=='annual')
    direct=annual['fields'].get('operating_income')
    missing=annual['withheld_fields'].get('operating_income')
    reason=('exact_direct_fact_rights_held' if direct else missing if missing in REASONS
        else 'exact_direct_fact_unusable')
    check={key:source[key] for key in CHECK_KEYS-{'period_start','concept','reason'}}
    check.update(period_start=annual['period_start'],concept='OperatingIncomeLoss',reason=reason)
    return check


def comparable_check(packet):
    # New retrieval time alone is not a changed source or changed finding.
    return {k:v for k,v in packet.get('operating_income_check',{}).items() if k!='observed_at'}
