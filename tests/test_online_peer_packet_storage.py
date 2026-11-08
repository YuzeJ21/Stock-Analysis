"""Lossless private storage must not change or qualify source evidence."""
from base64 import b64decode, b64encode
from copy import deepcopy
from hashlib import sha256
import json
import zlib

import pytest


CLASSIFICATION_REF = 'a' * 64
MAX_STORED_BYTES = 8 * 1024 * 1024


def _bytes(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def _packet():
    raw = b'<html><body>Common shares; annual diluted EPS: 12.50.</body></html>\x00\xff'
    return dict(ticker='JPM', collection=dict(ticker='JPM', classification_ref=CLASSIFICATION_REF,
        observed_at='2026-11-08T19:00:00Z', issuers=[dict(ticker='JPM', excluded_candidates=[
            dict(ticker='PREFERRED', reason='ordinary_share_basis_unverified')], selected_security_evidence=dict(
                source_url='https://www.sec.gov/Archives/edgar/data/19617/annual.htm',
                source_observed_at='2026-11-08T18:59:00Z', source_rights=dict(
                    purpose='private_research', redistribution=False, approval=None),
                payload_sha256=sha256(raw).hexdigest(), payload_raw_base64=b64encode(raw).decode()))]),
        observed_at='2026-11-08T19:00:00Z', error=None, packet_digest='9' * 64,
        listing_context=dict(label='JPMorgan — selected common shares', unchanged=[True, None, -0.0, 1.25]))


def _envelope(raw, *, ticker='JPM', classification_ref=CLASSIFICATION_REF):
    compressed = zlib.compress(raw)
    return dict(schema_version='retained-peer-packet-v1', encoding='zlib+base64', ticker=ticker,
        classification_ref=classification_ref, expanded_bytes=len(raw), expanded_sha256=sha256(raw).hexdigest(),
        compressed_bytes=len(compressed), compressed_sha256=sha256(compressed).hexdigest(),
        payload_base64=b64encode(compressed).decode())


def test_round_trip_preserves_raw_documents_provenance_exclusions_and_original_digest():
    from src.online_peer_packet_storage import pack_peer_packet, unpack_peer_packet
    packet = _packet()
    before = deepcopy(packet)
    packed = pack_peer_packet(packet, max_stored_bytes=MAX_STORED_BYTES)
    assert packed is not None
    assert set(packed) == {'schema_version', 'encoding', 'ticker', 'classification_ref', 'expanded_bytes',
        'expanded_sha256', 'compressed_bytes', 'compressed_sha256', 'payload_base64'}
    assert packed['schema_version'] == 'retained-peer-packet-v1'
    assert packed['encoding'] == 'zlib+base64'
    assert packed['expanded_bytes'] == len(_bytes(packet))
    assert packed['expanded_sha256'] == sha256(_bytes(packet)).hexdigest()
    compressed = b64decode(packed['payload_base64'], validate=True)
    assert len(compressed) == packed['compressed_bytes']
    assert sha256(compressed).hexdigest() == packed['compressed_sha256']
    restored = unpack_peer_packet(packed)
    assert restored == before and _bytes(restored) == _bytes(before)
    assert restored['packet_digest'] == '9' * 64
    assert packet == before
    evidence = restored['collection']['issuers'][0]['selected_security_evidence']
    assert sha256(b64decode(evidence['payload_raw_base64'])).hexdigest() == evidence['payload_sha256']


def test_failure_packet_without_classification_can_round_trip():
    from src.online_peer_packet_storage import pack_peer_packet, unpack_peer_packet, peer_classification_ref
    packet = dict(ticker='BAC', collection=None, error='vendor_context_source_unavailable', packet_digest='7' * 64)
    packed = pack_peer_packet(packet, max_stored_bytes=MAX_STORED_BYTES)
    assert packed['classification_ref'] is None
    assert peer_classification_ref(packet) is None and peer_classification_ref(packed) is None
    assert unpack_peer_packet(packed) == packet


def test_exact_encoded_budget_is_enforced_without_mutating_the_packet():
    from src.online_peer_packet_storage import pack_peer_packet
    packet = _packet()
    packed = pack_peer_packet(packet, max_stored_bytes=MAX_STORED_BYTES)
    size = len(_bytes(packed))
    assert pack_peer_packet(packet, max_stored_bytes=size) == packed
    assert pack_peer_packet(packet, max_stored_bytes=size - 1) is None
    assert packet == _packet()


@pytest.mark.parametrize('limit', [None, False, True, 0, -1, 1.5, '100', MAX_STORED_BYTES + 1])
def test_invalid_budget_cannot_raise_the_global_retained_limit(limit):
    from src.online_peer_packet_storage import pack_peer_packet
    with pytest.raises(ValueError):
        pack_peer_packet(_packet(), max_stored_bytes=limit)


@pytest.mark.parametrize('bad', [None, [], {}, {'ticker': True}, {'ticker': 'jpm'}, {'ticker': 'JPM', 'collection': {}},
    {'ticker': 'JPM', 'collection': {'classification_ref': 'a' * 63}},
    {'ticker': 'JPM', 'collection': {'classification_ref': CLASSIFICATION_REF, 'classification': {}}},
    {'ticker': 'JPM', 'collection': {'classification_ref': CLASSIFICATION_REF, 'ticker': 'BAC'}},
    {'ticker': 'JPM', 'collection': []}, {'ticker': 'JPM', 'value': float('nan')},
    {'ticker': 'JPM', 'value': float('inf')}, {'ticker': 'JPM', 'value': (1, 2)},
    {'ticker': 'JPM', 'value': {1: 'non-string key'}}, {'ticker': 'JPM', 'value': object()}])
def test_non_json_or_non_compact_packets_are_not_silently_changed(bad):
    from src.online_peer_packet_storage import pack_peer_packet
    assert pack_peer_packet(bad, max_stored_bytes=MAX_STORED_BYTES) is None


@pytest.mark.parametrize('field,bad', [
    ('schema_version', 'retained-peer-packet-v2'), ('encoding', 'gzip+base64'), ('ticker', 'BAC'),
    ('ticker', True), ('classification_ref', 'b' * 64), ('classification_ref', None),
    ('classification_ref', 'A' * 64), ('expanded_bytes', True), ('expanded_bytes', 0),
    ('expanded_bytes', -1), ('expanded_bytes', 1.0), ('expanded_bytes', 128 * 1024 * 1024 + 1),
    ('compressed_bytes', False), ('compressed_bytes', 0), ('compressed_bytes', 1.0),
    ('compressed_bytes', MAX_STORED_BYTES), ('expanded_sha256', '0' * 64),
    ('expanded_sha256', 'A' * 64), ('compressed_sha256', '0' * 64),
    ('payload_base64', ''), ('payload_base64', None), ('payload_base64', '%%%%'),
    ('payload_base64', 'a' * (MAX_STORED_BYTES + 4)),
], ids=lambda value: repr(value)[:80])
def test_changed_or_unbounded_envelope_metadata_is_rejected(field, bad):
    from src.online_peer_packet_storage import unpack_peer_packet
    packed = _envelope(_bytes(_packet()))
    packed[field] = bad
    assert unpack_peer_packet(packed) is None


@pytest.mark.parametrize('kind', ['extra', 'missing', 'not_mapping', 'plain_packet'])
def test_decode_accepts_only_the_exact_storage_contract(kind):
    from src.online_peer_packet_storage import unpack_peer_packet
    packed = _envelope(_bytes(_packet()))
    if kind == 'extra':
        packed['approved'] = True
    elif kind == 'missing':
        del packed['compressed_bytes']
    elif kind == 'not_mapping':
        packed = []
    else:
        packed = _packet()
    assert unpack_peer_packet(packed) is None


@pytest.mark.parametrize('problem', ['truncated', 'trailing_junk', 'concatenated', 'corrupt', 'wrong_length',
    'wrong_expanded_length', 'invalid_base64', 'base64_whitespace', 'non_ascii_base64'])
def test_invalid_streams_fail_even_with_recomputed_compressed_hash(problem):
    from src.online_peer_packet_storage import unpack_peer_packet
    packed = _envelope(_bytes(_packet()))
    compressed = b64decode(packed['payload_base64'])
    if problem == 'truncated':
        compressed = compressed[:-1]
    elif problem == 'trailing_junk':
        compressed += b'junk'
    elif problem == 'concatenated':
        compressed += zlib.compress(b'{}')
    elif problem == 'corrupt':
        compressed = b'not a zlib stream'
    elif problem == 'wrong_length':
        packed['compressed_bytes'] += 1
    elif problem == 'wrong_expanded_length':
        packed['expanded_bytes'] -= 1
    packed['payload_base64'] = b64encode(compressed).decode()
    if problem == 'invalid_base64':
        packed['payload_base64'] = '!' + packed['payload_base64'][1:]
    elif problem == 'base64_whitespace':
        packed['payload_base64'] += '\n'
    elif problem == 'non_ascii_base64':
        packed['payload_base64'] = 'é' + packed['payload_base64'][1:]
    if problem != 'wrong_length':
        packed['compressed_bytes'] = len(compressed)
    packed['compressed_sha256'] = sha256(compressed).hexdigest()
    assert unpack_peer_packet(packed) is None


@pytest.mark.parametrize('raw', [b'{"ticker":"JPM","ticker":"BAC"}', b'{"ticker":"JPM","value":NaN}',
    b'{"ticker":"JPM","value":Infinity}', b'{"ticker":"JPM","value":-Infinity}',
    b'{"ticker":"JPM","value":1e9999}', b'{"ticker":"JPM","nested":{"x":1,"x":2}}',
    b'{"ticker":"JPM", "value":1}', b'{"value":1,"ticker":"JPM"}', b'{"ticker":"JPM"}\n',
    b'{"ticker":"JPM","value":"\xff"}', b'[]', b'{"ticker":"BAC"}',
    b'{"ticker":"JPM","collection":{"classification_ref":"a"}}',
    b'{"ticker":"JPM","value":"\\u0041"}', b'{"ticker":"JPM","value":1.00}',
    b'{"ticker":"JPM","value":1e0}', b'{"ticker":"JPM","value":' + b'[' * 1100 + b'0' + b']' * 1100 + b'}'],
    ids=lambda value: repr(value)[:80])
def test_malicious_or_noncanonical_json_is_rejected_before_source_replay(raw):
    from src.online_peer_packet_storage import unpack_peer_packet
    assert unpack_peer_packet(_envelope(raw, classification_ref=None)) is None


def test_declared_small_output_never_expands_or_parses_a_large_compression_bomb(monkeypatch):
    from src import online_peer_packet_storage as storage
    raw = b' ' * (2 * 1024 * 1024)
    packed = _envelope(raw, classification_ref=None)
    packed['expanded_bytes'] = 32
    def unexpected_parse(*args, **kwargs):
        raise AssertionError('oversized data reached JSON parsing')
    monkeypatch.setattr(storage.json, 'loads', unexpected_parse)
    assert storage.unpack_peer_packet(packed) is None


def test_expanded_limit_applies_to_pack_and_decode_before_json_parsing(monkeypatch):
    from src import online_peer_packet_storage as storage
    packet = _packet()
    packed = _envelope(_bytes(packet))
    monkeypatch.setattr(storage, 'MAX_EXPANDED_BYTES', 64)
    assert storage.pack_peer_packet(packet, max_stored_bytes=MAX_STORED_BYTES) is None
    def unexpected_parse(*args, **kwargs):
        raise AssertionError('oversized declaration reached JSON parsing')
    monkeypatch.setattr(storage.json, 'loads', unexpected_parse)
    assert storage.unpack_peer_packet(packed) is None


def test_resource_failures_do_not_escape_the_storage_boundary(monkeypatch):
    from src import online_peer_packet_storage as storage
    packed = _envelope(_bytes(_packet()))
    def exhausted(*args, **kwargs):
        raise MemoryError('constructed allocation failure')
    monkeypatch.setattr(storage.zlib, 'compress', exhausted)
    assert storage.pack_peer_packet(_packet(), max_stored_bytes=MAX_STORED_BYTES) is None
    monkeypatch.setattr(storage.zlib, 'decompressobj', exhausted)
    assert storage.unpack_peer_packet(packed) is None


def test_reference_extraction_preserves_shared_classification_without_decompression(monkeypatch):
    from src import online_peer_packet_storage as storage
    packet = _packet()
    packed = _envelope(_bytes(packet))
    def unexpected_decode(*args, **kwargs):
        raise AssertionError('classification pruning decompressed a peer packet')
    monkeypatch.setattr(storage.zlib, 'decompressobj', unexpected_decode)
    assert storage.peer_classification_ref(packet) == CLASSIFICATION_REF
    assert storage.peer_classification_ref(packed) == CLASSIFICATION_REF
    malformed = deepcopy(packed)
    malformed['classification_ref'] = 'not a hash'
    assert storage.peer_classification_ref(malformed) is None
    malformed = deepcopy(packed)
    malformed['extra'] = True
    assert storage.peer_classification_ref(malformed) is None
    assert storage.peer_classification_ref(None) is None
    assert storage.peer_classification_ref({'collection': {'classification_ref': CLASSIFICATION_REF}}) is None


def test_cyclic_input_is_rejected_without_recursion_or_mutation():
    from src.online_peer_packet_storage import pack_peer_packet
    packet = _packet()
    packet['cycle'] = packet
    assert pack_peer_packet(packet, max_stored_bytes=MAX_STORED_BYTES) is None
    assert packet['cycle'] is packet


@pytest.mark.parametrize('dimension', ['depth', 'nodes'])
def test_structural_resource_limits_are_checked_before_json_parsing(monkeypatch, dimension):
    from src import online_peer_packet_storage as storage
    if dimension == 'depth':
        raw = b'{"ticker":"JPM","values":' + b'[' * 150 + b'0' + b']' * 150 + b'}'
    else:
        raw = b'{"ticker":"JPM","values":[0,0,0,0,0,0,0,0,0,0]}'
        monkeypatch.setattr(storage, 'MAX_JSON_NODES', 8)
    packed = _envelope(raw, classification_ref=None)
    def unexpected_parse(*args, **kwargs):
        raise AssertionError('excessive structure reached JSON parsing')
    monkeypatch.setattr(storage.json, 'loads', unexpected_parse)
    assert storage.unpack_peer_packet(packed) is None


def test_envelope_metadata_must_agree_with_the_decoded_collection_ticker():
    from src.online_peer_packet_storage import unpack_peer_packet
    packet = _packet()
    packet['collection']['ticker'] = 'BAC'
    assert unpack_peer_packet(_envelope(_bytes(packet))) is None


def test_noncanonical_base64_pad_bits_cannot_represent_the_same_stream():
    from src.online_peer_packet_storage import unpack_peer_packet
    raw = b'{"ticker":"JPM","x":"abc"}'
    packed = _envelope(raw, classification_ref=None)
    # This stream has one padding character. Change only discarded pad bits.
    alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
    payload = packed['payload_base64']
    assert payload.endswith('=') and not payload.endswith('==')
    index = alphabet.index(payload[-2])
    changed = payload[:-2] + alphabet[index + 1] + '='
    assert b64decode(changed) == b64decode(payload)
    packed['payload_base64'] = changed
    assert unpack_peer_packet(packed) is None


def test_structure_limits_do_not_mistake_string_content_or_escapes_for_nodes():
    from src.online_peer_packet_storage import pack_peer_packet, unpack_peer_packet
    packet = _packet()
    packet['literal'] = '\\"[{},:]' * 1000 + '☃ \\u0041'
    packed = pack_peer_packet(packet, max_stored_bytes=MAX_STORED_BYTES)
    assert packed is not None
    assert unpack_peer_packet(packed) == packet


def test_global_envelope_limit_includes_metadata_and_precedes_base64_allocation(monkeypatch):
    from src import online_peer_packet_storage as storage
    packed = _envelope(_bytes(_packet()))
    packed['compressed_bytes'] = MAX_STORED_BYTES * 3 // 4
    packed['payload_base64'] = 'A' * MAX_STORED_BYTES
    def unexpected_decode(*args, **kwargs):
        raise AssertionError('oversized full envelope reached base64 decoding')
    monkeypatch.setattr(storage, 'b64decode', unexpected_decode)
    assert storage.unpack_peer_packet(packed) is None


def test_compressed_integrity_is_checked_before_any_stream_expansion(monkeypatch):
    from src import online_peer_packet_storage as storage
    packed = _envelope(_bytes(_packet()))
    packed['compressed_sha256'] = '0' * 64
    def unexpected_expand(*args, **kwargs):
        raise AssertionError('corrupt compressed bytes reached stream expansion')
    monkeypatch.setattr(storage.zlib, 'decompressobj', unexpected_expand)
    assert storage.unpack_peer_packet(packed) is None


def test_json_allocation_failure_is_a_held_storage_result(monkeypatch):
    from src import online_peer_packet_storage as storage
    packed = _envelope(_bytes(_packet()))
    def exhausted(*args, **kwargs):
        raise MemoryError('constructed JSON allocation failure')
    monkeypatch.setattr(storage.json, 'loads', exhausted)
    assert storage.unpack_peer_packet(packed) is None
