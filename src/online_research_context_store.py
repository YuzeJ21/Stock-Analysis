"""Bounded private normalized online research snapshots, with offline replay only.

These receipts are separate from annual SEC review receipts and canonical inputs.
A checksum verifies saved bytes; it is not a source approval or a signature.
"""
from __future__ import annotations

from base64 import b64decode, b64encode
from datetime import datetime, timezone
from hashlib import sha256
from itertools import islice
import json
import math
import os
from pathlib import Path
import re
import stat
import zlib

from src.sec_cover_observations import COVER_FIELDS, validate_cover_scope
from src.sec_reported_numeric import valid_reported_numeric


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_VERSION = 'online-research-snapshot-v1'
CONTEXT_SCHEMA_VERSION = 'online-company-research-v1'
MAX_SNAPSHOT_BYTES = 512 * 1024
MAX_EXPANDED_SNAPSHOT_BYTES = 1024 * 1024
_COMPRESSED_SCHEMA = 'online-research-snapshot-zlib-v1'
MAX_SNAPSHOTS_PER_SCOPE = 100
MAX_RESEARCH_SCOPES = 100
MAX_JSON_DEPTH = 32
MAX_JSON_NODES = 40000
REPLAY_NOTICE = 'Historical saved research context. Explicitly refresh company research for current observations.'
_SCOPE_KEYS = ('profile_key', 'ticker', 'sec_cik')
_SNAPSHOT_KEYS = {'schema_version', 'snapshot_id', 'snapshot_sha256', 'profile_key', 'ticker',
    'sec_cik', 'saved_at', 'observed_at', 'source_revision', 'context', 'historical', 'current', 'replay_notice'}
_RAW_KEYS = {'raw', 'body', 'raw_body', 'raw_payload', 'raw_response', 'response_body', 'payload',
    'bytes', 'base64', 'archive', 'archives', 'raw_archive', 'archive_body', 'html', 'xml'}
_METADATA_KEYS = {'observed_at', 'observed_at_utc', 'retrieved_at', 'retrieved_at_utc', 'fetched_at',
    'source_observed_at', 'association_observed_at', 'payload_sha256', 'raw_payload_sha256',
    'response_sha256', 'association_payload_sha256', 'source_last_modified', 'last_modified',
    'receipt_id', 'inventory_id', 'source_metadata_revision', 'metadata_revision', 'attempted_at',
    'packet_digest', 'digest', 'sha256'}


class ResearchSnapshotSizeError(ValueError):
    """The snapshot exceeds a storage or expansion limit."""

    def __init__(self, message, *, limit_kind='expanded'):
        super().__init__(message)
        self.limit_kind = limit_kind


def _json(value, *, max_bytes=None, limit_kind='expanded'):
    try:
        encoder = json.JSONEncoder(sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)
        if max_bytes is None:
            return encoder.encode(value).encode('ascii')
        output = bytearray()
        for chunk in encoder.iterencode(value):
            encoded = chunk.encode('ascii')
            if len(output) + len(encoded) > max_bytes:
                raise ResearchSnapshotSizeError('Research snapshot size limit exceeded', limit_kind=limit_kind)
            output.extend(encoded)
        return bytes(output)
    except ResearchSnapshotSizeError:
        raise
    except (TypeError, ValueError, RecursionError, OverflowError) as exc:
        raise ValueError('Research context must be finite normalized JSON') from exc


def _digest(value):
    return sha256(_json(value)).hexdigest()


def _hex(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


def _scope(profile_key, ticker, sec_cik):
    if (not isinstance(profile_key, str) or not 1 <= len(profile_key) <= 200
            or any(ord(c) < 32 for c in profile_key)):
        raise ValueError('Invalid research profile scope')
    if (not isinstance(ticker, str) or re.fullmatch(r'[A-Z0-9][A-Z0-9.-]{0,19}', ticker) is None
            or '..' in ticker):
        raise ValueError('Invalid research ticker scope')
    if not isinstance(sec_cik, str) or re.fullmatch('[0-9]{10}', sec_cik) is None or int(sec_cik) == 0:
        raise ValueError('Invalid research CIK scope')
    return dict(profile_key=profile_key, ticker=ticker, sec_cik=sec_cik)


def _timestamp(value):
    if not isinstance(value, str) or len(value) > 40:
        raise ValueError('Invalid research snapshot timestamp')
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError('Invalid research snapshot timestamp') from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError('Research snapshot timestamp requires a timezone')
    return parsed.astimezone(timezone.utc)


def _eps_numeric_proof(value):
    """Recognize a bounded numeric provenance token, never a transport body.

    The existing inline parser rederives the amount from text/scale/sign. This
    permits exact replay of normalized EPS evidence without approving a source
    or treating a stored proof as a substitute for its original filing receipt.
    """
    required = {'value', 'raw_text', 'scale', 'sign', 'decimals', 'transformation',
        'context_id', 'unit_id', 'unit', 'concept', 'namespace_uri', 'source_ref'}
    optional = {'context_source_ref', 'unit_source_ref'}
    if (not isinstance(value, dict) or not required <= value.keys()
            or not value.keys() <= required | optional
            or value.get('concept') != 'EarningsPerShareDiluted' or value.get('unit') != 'USD/shares'
            or not isinstance(value.get('namespace_uri'), str)
            or re.fullmatch(r'https?://fasb.org/us-gaap/\d{4}', value['namespace_uri']) is None
            or type(value.get('value')) not in {int, float}):
        return False
    token = value.get('raw_text')
    if not isinstance(token, str) or not 0 <= len(token) <= 100 or token != token.strip():
        return False
    if value.get('transformation') == 'fixed-zero' and token not in {'', '-', '\u2013', '\u2014'}:
        if re.fullmatch(r'[+-]?0+(?:\.0+)?', token) is None:
            return False
    for name in ('context_id', 'unit_id'):
        if not isinstance(value.get(name), str) or re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.:-]{0,199}', value[name]) is None:
            return False
    pattern = (r'https://www\.sec\.gov/Archives/edgar/data/[1-9]\d{0,9}/\d{18}/'
               r'([A-Za-z0-9][A-Za-z0-9_.-]{0,180}\.(?:htm|html|xhtml))#([A-Za-z0-9_][A-Za-z0-9_.:-]{0,199})')
    for key in ('source_ref', *optional):
        if key not in value:
            continue
        match = re.fullmatch(pattern, value[key]) if isinstance(value[key], str) else None
        if match is None or '..' in match[1]:
            return False
        if key in optional and match[2] != value['context_id' if key == 'context_source_ref' else 'unit_id']:
            return False
    try:
        from src.sec_inline_filing import valid_numeric_proof
        return math.isfinite(value['value']) and abs(value['value']) <= 1e20 and valid_numeric_proof(value)
    except (TypeError, ValueError, OverflowError, AttributeError):
        return False


def _normalized(value):
    """Bound complexity before serializing, reject transport bodies at every level."""
    active = set()
    nodes = 0
    cover_documents = set()

    def cover_owner(path, owner):
        if path in {('peer_read_through', 'subject'), ('peer_read_through', 'subject_source_context')}:
            if (owner.get('ticker', value.get('ticker')), owner.get('sec_cik')) != (value.get('ticker'), value.get('sec_cik')):
                raise ValueError('Normalized selected-security cover owner scope mismatch')
            return value.get('ticker'), value.get('sec_cik')
        if len(path) == 3 and path[:2] == ('peer_read_through', 'peers') and type(path[2]) is int:
            return owner.get('ticker'), owner.get('sec_cik')
        if (len(path) in {4, 5} and path[:2] == ('peer_read_through', 'excluded')
                and type(path[2]) is int and path[3] == 'diagnostics'
                and (len(path) == 4 or path[4] == 'independent_observation_not_in_benchmark')):
            excluded = value['peer_read_through']['excluded'][path[2]]
            diagnostics = excluded.get('diagnostics')
            ticker, cik = owner.get('ticker'), owner.get('sec_cik')
            if (not isinstance(diagnostics, dict) or excluded.get('ticker') != ticker
                    or excluded.get('sec_cik', cik) != cik
                    or (diagnostics.get('ticker'), diagnostics.get('sec_cik')) != (ticker, cik)):
                raise ValueError('Normalized selected-security excluded cover owner scope mismatch')
            return ticker, cik
        raise ValueError('Normalized cover evidence is outside selected-security document scope')

    def visit(item, depth, path=()):
        nonlocal nodes
        nodes += 1
        if depth > MAX_JSON_DEPTH or nodes > MAX_JSON_NODES:
            raise ValueError('Research context depth or node limit exceeded')
        if item is None or isinstance(item, bool):
            return
        if isinstance(item, (int, float)) and not isinstance(item, bool):
            if isinstance(item, float) and not math.isfinite(item):
                raise ValueError('Research context must contain finite numbers')
            return
        if isinstance(item, str):
            if len(item) > MAX_SNAPSHOT_BYTES:
                raise ResearchSnapshotSizeError('Research snapshot size limit exceeded', limit_kind='field')
            if item.lstrip().lower().startswith('data:') and ';base64,' in item.lower():
                raise ValueError('Research context must contain normalized observations, not base64 bodies')
            return
        if not isinstance(item, (dict, list)):
            raise ValueError('Research context must contain normalized JSON values')
        if id(item) in active:
            raise ValueError('Research context depth or cycle limit exceeded')
        active.add(id(item))
        if isinstance(item, dict):
            if any(isinstance(key, str) and key.lower() in {'reported_text', 'reported_numeric_schema'} for key in item):
                typed = (len(path) == 5 and path[:2] == ('business_trend', 'periods')
                    and type(path[2]) is int and path[3] in {'fields', 'cumulative_fields'}
                    and isinstance(path[4], str))
                row = value['business_trend']['periods'][path[2]] if typed else None
                if not typed or not valid_reported_numeric(item, context=value, row=row,
                        field_name=path[4], cumulative=path[3] == 'cumulative_fields'):
                    raise ValueError('Normalized reported numeric proof is invalid or outside its typed filing field')
            for key, child in item.items():
                if not isinstance(key, str) or not key or len(key) > 200:
                    raise ValueError('Invalid normalized research context key')
                name = key.lower()
                if name in COVER_FIELDS and (key != name or path not in cover_documents):
                    raise ValueError('Normalized cover fields require a validated selected-security document')
                numeric_token = name == 'raw_text' and _eps_numeric_proof(item)
                if (name in _RAW_KEYS or 'base64' in name or name.endswith('_body')
                        or name.endswith('_bytes') or name.startswith('raw_') and not name.endswith(('_sha256', '_digest')) and not numeric_token):
                    raise ValueError('Research context must contain normalized observations, not raw/archive fields')
                if key == 'selected_security_scope' and isinstance(child, dict) and child.get('status') == 'supported_common':
                    ticker, cik = cover_owner(path, item)
                    validate_cover_scope(child, ticker=ticker, cik=cik)
                    cover_documents.update(path + (key, 'documents', index) for index, document in enumerate(child['documents'])
                        if 'cover_observations' in document)
                visit(child, depth + 1, path + (key,))
        else:
            for index, child in enumerate(item):
                visit(child, depth + 1, path + (index,))
        active.remove(id(item))

    visit(value, 0)
    raw = _json(value, max_bytes=MAX_EXPANDED_SNAPSHOT_BYTES)
    return json.loads(raw)


def _context(context, scope=None):
    if not isinstance(context, dict) or context.get('schema_version') != CONTEXT_SCHEMA_VERSION:
        raise ValueError('Unsupported research context schema')
    own_scope = _scope(*(context.get(key) for key in _SCOPE_KEYS))
    if scope is not None and scope != own_scope:
        raise ValueError('Research context scope mismatch')
    _timestamp(context.get('observed_at'))
    revision = context.get('source_revision')
    if not isinstance(revision, str) or not 1 <= len(revision) <= 200 or any(ord(c) < 32 for c in revision):
        raise ValueError('Invalid semantic source revision')
    if context.get('saved_readiness_promoted') is not False or context.get('commercial_eligible') is not False:
        raise ValueError('Research context cannot promote saved readiness or commercial eligibility')
    return _normalized(context)


def _identity(context):
    return dict(schema_version=SCHEMA_VERSION, **{key: context[key] for key in _SCOPE_KEYS}, context=context)


def _snapshot(context):
    result = dict(schema_version=SCHEMA_VERSION, snapshot_id=_digest(_identity(context)),
        **{key: context[key] for key in _SCOPE_KEYS},
        saved_at=datetime.now(timezone.utc).isoformat(), observed_at=context['observed_at'],
        source_revision=context['source_revision'], context=context, historical=True, current=False,
        replay_notice=REPLAY_NOTICE)
    result['snapshot_sha256'] = _digest(result)
    return result


def _validate_snapshot(snapshot, *, scope=None, snapshot_id=None):
    if not isinstance(snapshot, dict) or set(snapshot) != _SNAPSHOT_KEYS or snapshot.get('schema_version') != SCHEMA_VERSION:
        raise ValueError('Invalid saved research snapshot schema')
    own_scope = _scope(*(snapshot.get(key) for key in _SCOPE_KEYS))
    if scope is not None and own_scope != scope:
        raise ValueError('Saved research snapshot scope mismatch')
    context = _context(snapshot['context'], own_scope)
    _timestamp(snapshot['saved_at'])
    if (snapshot['observed_at'] != context['observed_at'] or snapshot['source_revision'] != context['source_revision']
            or snapshot['historical'] is not True or snapshot['current'] is not False
            or snapshot['replay_notice'] != REPLAY_NOTICE):
        raise ValueError('Invalid historical research snapshot metadata')
    if (not _hex(snapshot['snapshot_id']) or snapshot_id is not None and snapshot_id != snapshot['snapshot_id']
            or snapshot['snapshot_id'] != _digest(_identity(context))):
        raise ValueError('Research snapshot identity digest mismatch')
    if (not _hex(snapshot['snapshot_sha256']) or snapshot['snapshot_sha256'] !=
            _digest({key: value for key, value in snapshot.items() if key != 'snapshot_sha256'})):
        raise ValueError('Research snapshot checksum mismatch')
    return snapshot


def _root(project_root):
    return Path(PROJECT_ROOT if project_root is None else project_root).resolve()


def _safe(path, root):
    if not path.is_relative_to(root):
        raise ValueError('Research snapshot path escaped its store')
    cursor = path
    while cursor != root:
        if cursor.is_symlink():
            raise ValueError('Research snapshot store contains a symlink')
        cursor = cursor.parent
    if not path.resolve().is_relative_to(root):
        raise ValueError('Research snapshot path escaped its store')
    return path


def _profile_path(profile_key, project_root):
    # Validate the profile without accepting path-bearing ticker/CIK inputs.
    _scope(profile_key, 'VALID', '0000000001')
    root = _root(project_root)
    return _safe(root / 'outputs/local/online-research-contexts' / sha256(profile_key.encode()).hexdigest(), root), root


def _directory(scope, project_root):
    profile, root = _profile_path(scope['profile_key'], project_root)
    return _safe(profile / scope['sec_cik'] / scope['ticker'], root), root


def _entries(directory, root, limit):
    _safe(directory, root)
    try:
        with os.scandir(directory) as entries:
            paths = [Path(entry.path) for entry in islice(entries, limit + 1)]
    except FileNotFoundError:
        return []
    if len(paths) > limit:
        raise ValueError('Saved research history limit exceeded')
    return sorted(paths)


def _read(path, root):
    _safe(path, root)
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
        with os.fdopen(descriptor, 'rb') as handle:
            info = os.fstat(handle.fileno())
            if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= MAX_SNAPSHOT_BYTES:
                raise ValueError('Saved research snapshot size/type limit exceeded')
            raw = handle.read(MAX_SNAPSHOT_BYTES + 1)
    except FileNotFoundError as exc:
        raise ValueError('Saved research snapshot not found') from exc
    if not 0 < len(raw) <= MAX_SNAPSHOT_BYTES:
        raise ValueError('Saved research snapshot size limit exceeded')
    snapshot = _parse_json(raw)
    if isinstance(snapshot, dict) and snapshot.get('schema_version') == _COMPRESSED_SCHEMA:
        snapshot = _expand_snapshot(snapshot)
    return snapshot


def _parse_json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Saved research snapshot has a duplicate JSON key')
            result[key] = value
        return result

    def constant(_):
        raise ValueError('Saved research snapshot has a nonfinite number')

    try:
        return json.loads(raw, object_pairs_hook=unique, parse_constant=constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError, OverflowError) as exc:
        raise ValueError('Saved research snapshot could not be parsed') from exc


def _expand_snapshot(wrapper):
    size = wrapper.get('expanded_bytes')
    payload = wrapper.get('payload_base64')
    if (set(wrapper) != {'schema_version', 'expanded_bytes', 'payload_base64'}
            or type(size) is not int or not 0 < size <= MAX_EXPANDED_SNAPSHOT_BYTES
            or not isinstance(payload, str) or not payload):
        raise ValueError('Invalid compressed research snapshot envelope')
    try:
        compressed = b64decode(payload, validate=True)
        if b64encode(compressed).decode('ascii') != payload:
            raise ValueError('Noncanonical compressed research snapshot encoding')
        decoder = zlib.decompressobj()
        expanded = decoder.decompress(compressed, size + 1)
    except (ValueError, zlib.error) as exc:
        raise ValueError('Invalid compressed research snapshot payload') from exc
    if (len(expanded) != size or not decoder.eof
            or decoder.unconsumed_tail or decoder.unused_data):
        raise ValueError('Invalid compressed research snapshot stream or size')
    return _parse_json(expanded)


def _stored_snapshot(snapshot):
    raw = _json(snapshot, max_bytes=MAX_EXPANDED_SNAPSHOT_BYTES - 1) + b'\n'
    if len(raw) <= MAX_SNAPSHOT_BYTES:
        return raw
    compressed = zlib.compress(raw)
    wrapper = dict(schema_version=_COMPRESSED_SCHEMA, expanded_bytes=len(raw),
                   payload_base64=b64encode(compressed).decode('ascii'))
    return _json(wrapper, max_bytes=MAX_SNAPSHOT_BYTES - 1, limit_kind='stored') + b'\n'


def _limit(value, maximum):
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= maximum:
        raise ValueError('Invalid saved research list limit')
    return value


def load_research_context(snapshot_id, *, profile_key, ticker, sec_cik, project_root=None):
    """Read one exact selected-profile/company snapshot; never fetch or mark live."""
    scope = _scope(profile_key, ticker, sec_cik)
    if not _hex(snapshot_id):
        raise ValueError('Invalid research snapshot identifier')
    directory, root = _directory(scope, project_root)
    return _validate_snapshot(_read(directory / (snapshot_id + '.json'), root), scope=scope, snapshot_id=snapshot_id)


def list_research_contexts(*, profile_key, ticker, sec_cik, project_root=None, limit=20):
    """Return newest first; invalid matching saved content fails this exact scope."""
    scope = _scope(profile_key, ticker, sec_cik)
    _limit(limit, MAX_SNAPSHOTS_PER_SCOPE)
    directory, root = _directory(scope, project_root)
    result = []
    for path in _entries(directory, root, MAX_SNAPSHOTS_PER_SCOPE):
        _safe(path, root)
        if path.suffix != '.json' or not _hex(path.stem):
            raise ValueError('Invalid saved research snapshot file identity')
        result.append(_validate_snapshot(_read(path, root), scope=scope, snapshot_id=path.stem))
    return sorted(result, key=lambda row: (_timestamp(row['saved_at']), row['snapshot_id']), reverse=True)[:limit]


def save_research_context(context, *, profile_key, ticker, sec_cik, project_root=None):
    """Save an immutable normalized copy; exact repeated inputs are idempotent."""
    scope = _scope(profile_key, ticker, sec_cik)
    snapshot = _snapshot(_context(context, scope))
    raw = _stored_snapshot(snapshot)
    directory, root = _directory(scope, project_root)
    existing = list_research_contexts(**scope, project_root=project_root, limit=MAX_SNAPSHOTS_PER_SCOPE)
    for saved in existing:
        if saved['snapshot_id'] == snapshot['snapshot_id']:
            return saved
    if len(existing) >= MAX_SNAPSHOTS_PER_SCOPE:
        raise ValueError('Saved research history limit exceeded')
    directory.mkdir(parents=True, exist_ok=True)
    target = _safe(directory / (snapshot['snapshot_id'] + '.json'), root)
    try:
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600)
        with os.fdopen(descriptor, 'wb') as handle:
            handle.write(raw)
    except FileExistsError:
        # Another save may have completed after the bounded directory read.
        return load_research_context(snapshot['snapshot_id'], **scope, project_root=project_root)
    return snapshot


def _metadata_key(key):
    return key in _METADATA_KEYS or key.endswith(('_sha256', '_observed_at'))


def _without_metadata(value):
    if isinstance(value, dict):
        return {key: _without_metadata(child) for key, child in value.items() if not _metadata_key(key)}
    if isinstance(value, list):
        return [_without_metadata(child) for child in value]
    return value


def _metadata(value, path=''):
    result = {}
    if isinstance(value, dict):
        for key, child in value.items():
            name = path + '/' + key
            if _metadata_key(key):
                result[name] = child
            else:
                result.update(_metadata(child, name))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            result.update(_metadata(child, path + '/' + str(index)))
    return result


def _comparison_context(value):
    if isinstance(value, dict) and value.get('schema_version') == SCHEMA_VERSION:
        return _validate_snapshot(value)['context']
    return _context(value)


def _assumptions(context):
    value = context.get('assumptions')
    scenario = context.get('scenario')
    if value is None and isinstance(scenario, dict):
        # The current context schema stores a result with nested assumptions;
        # a direct parameter dictionary is also useful for retained drafts.
        value = scenario.get('assumptions') if 'schema_version' in scenario or 'status' in scenario else scenario
    if isinstance(value, dict):
        return {key: child for key, child in value.items()
            if key not in {'source_revenue', 'source_period_start', 'source_period_end', 'growth_path'}}
    return value


def compare_research_contexts(before, after):
    """Separate source facts/versions, transport metadata and user-authored inputs."""
    right = _comparison_context(after)
    result = dict(status='baseline_missing', source_changed=False, financial_changed=False,
        filing_changed=False, source_metadata_changed=False, assumptions_changed=False,
        notes_changed=False, changed_sections=[])
    if before is None:
        return result
    left = _comparison_context(before)
    if any(left[key] != right[key] for key in _SCOPE_KEYS):
        raise ValueError('Research snapshot comparison scope mismatch')
    sections = ('business_trend', 'earnings_components', 'filing_inventory', 'filing_coverage',
        'peer_read_through', 'forward_view', 'decision_lab', 'gaps', 'status')
    result['changed_sections'] = [key for key in sections
        if _without_metadata(left.get(key)) != _without_metadata(right.get(key))]
    result['source_changed'] = left['source_revision'] != right['source_revision']
    result['financial_changed'] = any(key in result['changed_sections'] for key in ('business_trend', 'earnings_components'))
    result['filing_changed'] = any(key in result['changed_sections'] for key in ('filing_inventory', 'filing_coverage'))
    result['source_metadata_changed'] = (left.get('source_receipts') != right.get('source_receipts') or
        _metadata({key: value for key, value in left.items() if key not in ('notes', 'scenario', 'assumptions')}) !=
        _metadata({key: value for key, value in right.items() if key not in ('notes', 'scenario', 'assumptions')}))
    result['assumptions_changed'] = _assumptions(left) != _assumptions(right)
    result['notes_changed'] = left.get('notes') != right.get('notes')
    result['status'] = ('changed' if result['source_changed'] or result['financial_changed'] or result['filing_changed']
        else 'user_inputs_changed' if result['assumptions_changed'] or result['notes_changed']
        else 'source_metadata_only' if result['source_metadata_changed']
        else 'changed' if result['changed_sections'] else 'unchanged')
    return result


def list_research_context_scopes(profile_key, *, project_root=None, limit=MAX_RESEARCH_SCOPES):
    """Bounded Monitor index; a damaged company does not hide verified scopes."""
    _limit(limit, MAX_RESEARCH_SCOPES)
    profile, root = _profile_path(profile_key, project_root)
    result = dict(scopes=[], errors=[])
    try:
        issuers = _entries(profile, root, MAX_RESEARCH_SCOPES)
    except (ValueError, OSError):
        result['errors'].append('Saved online research issuer list could not be verified or exceeds its limit.')
        return result
    examined = 0
    for issuer in issuers:
        try:
            _safe(issuer, root)
            _scope(profile_key, 'VALID', issuer.name)
            companies = _entries(issuer, root, MAX_RESEARCH_SCOPES)
        except (ValueError, OSError):
            result['errors'].append('A saved online research issuer scope could not be verified.')
            continue
        for company in companies:
            if examined >= limit:
                result['errors'].append('Additional saved online research scopes exceed this bounded Monitor list. Exact snapshot links remain available.')
                return result
            examined += 1
            try:
                scope = _scope(profile_key, company.name, issuer.name)
                rows = list_research_contexts(**scope, project_root=project_root, limit=MAX_SNAPSHOTS_PER_SCOPE)
                if rows:
                    result['scopes'].append(dict(**scope, snapshot_count=len(rows),
                        latest_snapshot_id=rows[0]['snapshot_id'], saved_at=rows[0]['saved_at']))
            except (ValueError, OSError):
                result['errors'].append('A saved online research company scope could not be verified.')
    return result
