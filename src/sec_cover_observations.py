"""Bounded parsed cover documents for offline normalized research snapshots.

This checks recorded shape and relationships only. Exact filing-body validation
belongs to the selected-security producer; this format does not approve sources.
"""
from datetime import date, datetime
import html
import math
import re


COVER_OBSERVATION_SCHEMA = 'sec-cover-observations-v1'
COVER_FIELDS = frozenset({'cover_observations', 'cover_observation_schema'})
MAX_COVER_ROWS = 128
# Some literal BAC cover context IDs are 207 characters; do not truncate them.
MAX_CONTEXT_ID = 512
_ROW_KEYS = {'trading_symbol', 'title', 'exchange', 'context_id'}
_COMMON_KEYS = {'ticker', 'title', 'exchange', 'venue', 'context_id', 'fact_refs'}
_COMMON_OPTIONAL = {'context_source_ref', 'consistent_duplicate_refs'}
_META_KEYS = {'form', 'reportDate', 'filingDate', 'acceptanceDateTime', 'accessionNumber',
    'primaryDocument', 'isInlineXBRL', 'isXBRL'}
_DOCUMENT_KEYS = _META_KEYS | {'role', 'source_ref', 'observed_at', 'payload_sha256',
    'body_sha256', 'binding_normalization', 'reference_capture_sha256'}
_SCOPE_KEYS = {'status', 'reason', 'policy_id', 'ticker', 'sec_cik', 'issuer_symbols',
    'unassigned_issuer_symbols', 'documents', 'basis_refs', 'evidence_observations',
    'alias_mappings_established', 'technical_interpretation_only', 'commercial_eligible',
    'rights_status', 'original_eps'}
_VENUES = {'The New York Stock Exchange': 'NYSE', 'New York Stock Exchange': 'NYSE',
    'New York Stock Exchange LLC': 'NYSE', 'NYSE': 'NYSE', 'Nasdaq': 'Nasdaq', 'NASDAQ': 'Nasdaq'}


def _require(condition):
    if not condition:
        raise ValueError('Invalid normalized selected-security cover evidence')


def _text(value, maximum):
    _require(isinstance(value, str) and 0 < len(value) <= maximum
        and not any(ord(char) < 32 or 127 <= ord(char) <= 159 for char in value))
    decoded = value
    # Reject encoded markup too, without changing any retained literal text.
    while True:
        _require('<' not in decoded and '>' not in decoded
            and not decoded.lstrip().lower().startswith('data:'))
        unescaped = html.unescape(decoded)
        if unescaped == decoded:
            break
        decoded = unescaped
    return value


def _identifier(value):
    _require(isinstance(value, str) and re.fullmatch(
        rf'[A-Za-z0-9_][A-Za-z0-9_.:-]{{0,{MAX_CONTEXT_ID - 1}}}', value) is not None)
    return value


def _day(value):
    _require(isinstance(value, str) and re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value) is not None)
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError('Invalid normalized cover date') from exc


def _stamp(value):
    _require(isinstance(value, str) and len(value) <= 40)
    try:
        stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError('Invalid normalized cover timestamp') from exc
    _require(stamp.tzinfo is not None and stamp.utcoffset() is not None)
    return stamp


def _ticker(value):
    _require(isinstance(value, str) and re.fullmatch(r'[A-Z0-9][A-Z0-9.-]{0,19}', value) is not None
        and '..' not in value)
    return value


def _filename(value):
    _require(isinstance(value, str) and re.fullmatch(
        r'[A-Za-z0-9][A-Za-z0-9_.-]{0,199}\.(?:htm|html|xhtml)', value) is not None and '..' not in value)
    return value


def _reference(value, sources, *, fragment=None):
    _require(isinstance(value, str) and value.count('#') == 1)
    source, identity = value.split('#')
    _require(source in sources)
    _identifier(identity)
    if fragment is not None:
        _require(identity == fragment)


def _document(document, cik):
    _require(isinstance(document, dict))
    role = document.get('role')
    _require(isinstance(role, str))
    companion = role in {'annual_companion', 'cover_companion', 'quarter_companion'}
    _require(companion or role in {'annual', 'cover', 'quarter'})
    keys = _DOCUMENT_KEYS | ({'parent_form', 'parent_source_ref', 'parent_href'} if companion
        else {'selected_common', *COVER_FIELDS})
    _require(set(document) == keys)
    _text(document['form'], 40)
    report, filed = _day(document['reportDate']), _day(document['filingDate'])
    accepted, observed = _stamp(document['acceptanceDateTime']), _stamp(document['observed_at'])
    _require(report <= filed <= observed.date() and accepted <= observed)
    _require(all(type(document[name]) is int and document[name] in {0, 1}
        for name in ('isInlineXBRL', 'isXBRL')))
    accession = document['accessionNumber']
    _require(isinstance(accession, str) and re.fullmatch(r'[0-9]{10}-[0-9]{2}-[0-9]{6}', accession) is not None)
    # Accessions may start with a filing agent CIK rather than the issuer CIK.
    source = f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace("-", "")}/{_filename(document["primaryDocument"])}'
    _require(document['source_ref'] == source)
    for field in ('payload_sha256', 'body_sha256', 'reference_capture_sha256'):
        _require(isinstance(document[field], str) and re.fullmatch(r'[0-9a-f]{64}', document[field]) is not None)
    _require(isinstance(document['binding_normalization'], str)
        and document['binding_normalization'] in {'identity_bytes', 'sec-empty-tail-script-v1'})
    if not companion:
        forms = {'10-K', '10-K/A', '20-F', '20-F/A'} if role == 'annual' else {'10-Q', '10-Q/A'} if role == 'quarter' else {'8-K', '8-K/A', '8-K12B', '8-K12B/A'}
        _require(document['form'] in forms)
    return companion


def _common(document, ticker, sources):
    _require(document['cover_observation_schema'] == COVER_OBSERVATION_SCHEMA)
    rows = document['cover_observations']
    _require(isinstance(rows, list) and 0 < len(rows) <= MAX_COVER_ROWS)
    for row in rows:
        _require(isinstance(row, dict) and set(row) == _ROW_KEYS)
        _text(row['trading_symbol'], 128)
        _text(row['title'], 2000)
        _text(row['exchange'], 256)
        _identifier(row['context_id'])
    common = document['selected_common']
    _require(isinstance(common, dict) and _COMMON_KEYS <= common.keys()
        and common.keys() <= _COMMON_KEYS | _COMMON_OPTIONAL)
    _require(common['ticker'] == ticker)
    _text(common['title'], 2000)
    _text(common['exchange'], 256)
    _require(isinstance(common['venue'], str) and _VENUES.get(common['exchange']) == common['venue'])
    _identifier(common['context_id'])
    _require(any(row == dict(trading_symbol=ticker, title=common['title'],
        exchange=common['exchange'], context_id=common['context_id']) for row in rows))
    refs = common['fact_refs']
    _require(isinstance(refs, list) and len(refs) == 3)
    for reference in refs:
        _reference(reference, sources)
    _require(len(set(refs)) == 3)
    if 'context_source_ref' in common:
        _reference(common['context_source_ref'], sources, fragment=common['context_id'])
    if 'consistent_duplicate_refs' in common:
        duplicates = common['consistent_duplicate_refs']
        _require(isinstance(duplicates, list) and 0 < len(duplicates) <= 8)
        for reference in duplicates:
            _reference(reference, sources)
        _require(len(set(duplicates)) == len(duplicates))


def validate_cover_scope(scope, *, ticker, cik):
    """Validate a versioned normalized scope using its recorded issuer/doc set.

    No policies, source transports or current-time freshness checks are consulted.
    Values and row ordering are neither normalized nor changed by this check.
    """
    _ticker(ticker)
    _require(isinstance(cik, str) and re.fullmatch(r'[0-9]{10}', cik) is not None and int(cik) > 0)
    _require(isinstance(scope, dict) and set(scope) == _SCOPE_KEYS
        and scope['status'] == 'supported_common' and (scope['ticker'], scope['sec_cik']) == (ticker, cik)
        and scope['alias_mappings_established'] is False and scope['technical_interpretation_only'] is True
        and scope['commercial_eligible'] is False)
    for name in ('reason', 'policy_id', 'rights_status'):
        _text(scope[name], 200)
    symbols = scope['issuer_symbols']
    _require(isinstance(symbols, list) and 0 < len(symbols) <= 128)
    for symbol in symbols:
        _ticker(symbol)
    _require(len(set(symbols)) == len(symbols) and ticker in symbols
        and scope['unassigned_issuer_symbols'] == [symbol for symbol in symbols if symbol != ticker])
    documents = scope['documents']
    _require(isinstance(documents, list) and 0 < len(documents) <= 4)
    primary = {}
    companions = []
    for document in documents:
        if _document(document, cik):
            companions.append(document)
        else:
            _require(document['role'] not in primary)
            primary[document['role']] = document
    _require('annual' in primary and len(primary) <= 2)
    sources = {role: {document['source_ref']} for role, document in primary.items()}
    seen = set()
    for companion in companions:
        role = companion['role'].removesuffix('_companion')
        parent = primary.get(role)
        _require(parent is not None and role not in seen)
        seen.add(role)
        _require(companion['parent_source_ref'] == parent['source_ref']
            and companion['parent_form'] == parent['form']
            and isinstance(companion['parent_href'], str)
            and re.fullmatch(re.escape(companion['primaryDocument']) + r'(?:#[A-Za-z0-9_.:-]{1,200})?', companion['parent_href']) is not None
            and companion['source_ref'] != parent['source_ref'])
        for field in _META_KEYS - {'form', 'primaryDocument'}:
            _require(companion[field] == parent[field])
        sources[role].add(companion['source_ref'])
    for role, document in primary.items():
        _common(document, ticker, sources[role])
    basis = scope['basis_refs']
    _require(isinstance(basis, list) and 0 < len(basis) <= 16 and scope['evidence_observations'] == [])
    for reference in basis:
        _require(isinstance(reference, dict) and set(reference) == {'concept', 'source_ref', 'context_id'})
        _text(reference['concept'], 200)
        _identifier(reference['context_id'])
        _reference(reference['source_ref'], sources['annual'])
    eps = scope['original_eps']
    _require(isinstance(eps, dict) and set(eps) == {'period_start', 'period_end', 'eps', 'proofs'}
        and eps['period_end'] == primary['annual']['reportDate']
        and type(eps['eps']) in {int, float} and math.isfinite(eps['eps']))
    _require(_day(eps['period_start']) < _day(eps['period_end']))
    proofs = eps['proofs']
    _require(isinstance(proofs, list) and 0 < len(proofs) <= 128)
    for proof in proofs:
        _require(isinstance(proof, dict) and 'raw_text' in proof and type(proof.get('value')) in {int, float}
            and math.isfinite(proof['value']) and proof['value'] == eps['eps'])
        _reference(proof.get('source_ref'), sources['annual'])
        for field, identity in (('context_source_ref', 'context_id'), ('unit_source_ref', 'unit_id')):
            if field in proof:
                _reference(proof[field], sources['annual'], fragment=proof.get(identity))
