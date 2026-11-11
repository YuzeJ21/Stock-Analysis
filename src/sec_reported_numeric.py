"""Typed historical SEC numeric literals; never a source-body exception."""
from __future__ import annotations

from collections.abc import Mapping
import math
import re

from src.company_sec_online_preview import _iso_date, _utc_timestamp
from src.sec_exact_filing import RIGHTS, SOURCE_ID, BANK_SOURCE_ID
from src.sec_inline_filing import CATALOG, BANK_CATALOG, _taxonomy, valid_numeric_proof

SCHEMA = 'sec-reported-numeric-v1'
_KEYS = frozenset(('field', 'taxonomy', 'concept', 'namespace_uri', 'unit', 'unit_id', 'context_id',
    'period_start', 'period_end', 'fact_id', 'source_ref', 'rights_status', 'value', 'scale', 'sign',
    'decimals', 'transformation', 'reported_text', 'reported_numeric_schema', 'accession', 'form',
    'filed', 'accepted_at', 'primary_document', 'source_url', 'ticker', 'sec_cik', 'source_id',
    'observed_at', 'payload_sha256'))
_ID = re.compile(r'[A-Za-z_][A-Za-z0-9_.-]{0,127}\Z')
_NUMERIC = re.compile(r'[+-]?(?:\d[\d,]*(?:\.\d*)?|\.\d+)\Z', re.ASCII)
_ZERO = re.compile(r'[+-]?0+(?:\.0+)?\Z', re.ASCII)


def valid_reported_numeric(field, *, context, row, field_name, cumulative=False):
    """Recompute a complete literal proof bound to its typed historical row.

    This check has no clock or transport. A historical observation remains tied
    to its original observation dates and cannot become a current source approval.
    """
    try:
        if (not isinstance(field, dict) or set(field) != _KEYS
                or not isinstance(context, Mapping) or not isinstance(row, Mapping)
                or type(cumulative) is not bool or field.get('reported_numeric_schema') != SCHEMA
                or field.get('unit') != row.get('currency') or field.get('rights_status') != RIGHTS
                or field.get('field') != field_name
                or any(field.get(k) != context.get(k) for k in ('ticker', 'sec_cik'))):
            return False
        annual = row.get('kind') == 'annual'
        if annual:
            if (cumulative or field.get('taxonomy') != 'ifrs-full' or field.get('source_id') != SOURCE_ID
                    or not isinstance(field.get('unit'), str) or not re.fullmatch(r'[A-Z]{3}', field['unit'])
                    or field['unit'] == 'USD' or field.get('form') not in {'20-F', '20-F/A'}):
                return False
        elif row.get('kind') != 'quarterly' or field.get('unit') != 'USD' or field.get('form') not in {'10-Q', '10-Q/A'}:
            return False
        cik = field['sec_cik']; ticker = field['ticker']
        if (not isinstance(cik, str) or not re.fullmatch(r'\d{10}', cik, re.ASCII) or int(cik) == 0
                or not isinstance(ticker, str) or not re.fullmatch(r'[A-Z0-9][A-Z0-9.-]{0,19}', ticker)):
            return False
        bank = field['source_id'] == BANK_SOURCE_ID
        if field['source_id'] not in {SOURCE_ID, BANK_SOURCE_ID}:
            return False
        catalog = BANK_CATALOG if bank else CATALOG
        taxonomy = field['taxonomy']
        if (not isinstance(taxonomy, str) or taxonomy not in catalog or field_name not in catalog[taxonomy]
                or field['concept'] not in catalog[taxonomy][field_name]
                or _taxonomy(field['namespace_uri']) != taxonomy):
            return False
        for name in ('accession', 'form', 'filed', 'period_end'):
            if field[name] != row.get(name):
                return False
        accession = field['accession']; document = field['primary_document']
        if (not isinstance(accession, str) or not re.fullmatch(r'\d{10}-\d{2}-\d{6}', accession, re.ASCII)
                or not isinstance(document, str)
                or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,180}\.(?:htm|html|xhtml)', document)
                or '..' in document
                or any(not isinstance(field[k], str) or not _ID.fullmatch(field[k])
                       for k in ('fact_id', 'context_id', 'unit_id'))):
            return False
        url = f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace("-", "")}/{document}'
        if field['source_url'] != url or field['source_ref'] != url + '#' + field['fact_id']:
            return False
        if not isinstance(field['payload_sha256'], str) or not re.fullmatch(r'[0-9a-f]{64}', field['payload_sha256']):
            return False
        start, end, filed = (_iso_date(field[k]) for k in ('period_start', 'period_end', 'filed'))
        row_start = _iso_date(row.get('period_start'))
        observed = _utc_timestamp(field['observed_at']); accepted = _utc_timestamp(field['accepted_at'])
        context_observed = _utc_timestamp(context.get('observed_at'))
        if (not all((start, end, filed, row_start, observed, accepted, context_observed))
                or not end <= filed <= observed.date() or not end <= accepted.date() <= observed.date()
                or not accepted <= observed <= context_observed):
            return False
        minimum, maximum = (300, 430) if annual else (70, 105)
        if not minimum <= (end - row_start).days <= maximum:
            return False
        if cumulative:
            if not start < row_start or not 105 < (end-start).days <= 320:
                return False
            bucket = row.get('cumulative_fields')
            if not isinstance(bucket, Mapping) or not 1 <= len(bucket) <= len(catalog[taxonomy]):
                return False
            for sibling in bucket.values():
                if not isinstance(sibling, Mapping) or any(sibling.get(k) != field[k] for k in (
                        'period_start', 'period_end', 'accession', 'form', 'filed', 'unit')):
                    return False
        elif field['period_start'] != row.get('period_start'):
            return False
        literal = field['reported_text']
        if not isinstance(literal, str) or not 0 < len(literal) <= 100 or literal != literal.strip():
            return False
        if field['transformation'] == 'fixed-zero':
            if literal not in {'-', '\u2013', '\u2014'} and not _ZERO.fullmatch(literal):
                return False
        elif not _NUMERIC.fullmatch(literal):
            return False
        if type(field['value']) not in {int, float} or not math.isfinite(field['value']) or abs(field['value']) > 1e20:
            return False
        proof = dict(field, raw_text=literal)
        return valid_numeric_proof(proof)
    except (TypeError, ValueError, KeyError, AttributeError, OverflowError, RecursionError):
        return False
