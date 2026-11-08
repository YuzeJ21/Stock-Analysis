"""Bounded, lossless storage for classification-referenced private peer packets.

An envelope is storage evidence only. Its decoded packet still requires the
original classification, original packet digest and unchanged source validators.
No source fields or inner packet digests are rewritten here.
"""
from __future__ import annotations

from base64 import b64decode, b64encode
from hashlib import sha256
import json
import math
import re
import zlib


SCHEMA = 'retained-peer-packet-v1'
MAX_STORED_BYTES = 8 * 1024 * 1024
MAX_EXPANDED_BYTES = 128 * 1024 * 1024
MAX_JSON_DEPTH = 128
MAX_JSON_NODES = 1_000_000
_ENCODING = 'zlib+base64'
_KEYS = frozenset({'schema_version', 'encoding', 'ticker', 'classification_ref', 'expanded_bytes',
    'expanded_sha256', 'compressed_bytes', 'compressed_sha256', 'payload_base64'})
_HASH = re.compile(r'[0-9a-f]{64}\Z')
_TICKER = re.compile(r'[A-Z0-9][A-Z0-9.-]{0,19}\Z')
_BASE64 = re.compile(r'[A-Za-z0-9+/]*={0,2}\Z')
_JSON_TOKENS = re.compile(rb'["\\{}\[\],:]|[^"\s\\{}\[\],:]+')
_FAILURES = (ValueError, TypeError, OverflowError, RecursionError, MemoryError, UnicodeError, zlib.error)


def _hash(value):
    return type(value) is str and _HASH.fullmatch(value) is not None


def _compact_metadata(packet):
    if (type(packet) is not dict or packet.get('schema_version') == SCHEMA
        or type(packet.get('ticker')) is not str or _TICKER.fullmatch(packet['ticker']) is None):
        return None
    collection = packet.get('collection')
    if collection is None:
        return packet['ticker'], None
    if (type(collection) is not dict or 'classification' in collection
        or not _hash(collection.get('classification_ref'))
        or ('ticker' in collection and collection['ticker'] != packet['ticker'])):
        return None
    return packet['ticker'], collection['classification_ref']


def _json_shape(value):
    """Reject implicit JSON conversions, cycles and excessive object structure."""
    remaining = MAX_JSON_NODES
    active = set()

    def visit(item, depth):
        nonlocal remaining
        remaining -= 1
        if remaining < 0 or depth > MAX_JSON_DEPTH:
            raise ValueError('peer_packet_json_structure_limit')
        kind = type(item)
        if item is None or kind in (bool, int):
            return
        if kind is str:
            if len(item) > MAX_EXPANDED_BYTES:
                raise ValueError('peer_packet_expanded_size_limit')
            return
        if kind is float:
            if not math.isfinite(item):
                raise ValueError('peer_packet_nonfinite_number')
            return
        if kind not in (dict, list) or id(item) in active:
            raise ValueError('peer_packet_not_lossless_json')
        active.add(id(item))
        if kind is dict:
            for key, child in item.items():
                if type(key) is not str:
                    raise ValueError('peer_packet_non_string_key')
                visit(key, depth + 1)
                visit(child, depth + 1)
        else:
            for child in item:
                visit(child, depth + 1)
        active.remove(id(item))

    visit(value, 0)


def _canonical_bytes(value, limit):
    chunks = []
    size = 0
    encoder = json.JSONEncoder(sort_keys=True, separators=(',', ':'), allow_nan=False, ensure_ascii=True)
    for chunk in encoder.iterencode(value):
        encoded = chunk.encode('ascii')
        size += len(encoded)
        if size > limit:
            raise ValueError('peer_packet_json_size_limit')
        chunks.append(encoded)
    return b''.join(chunks)


def _envelope_metadata(envelope):
    """Check bounded storage metadata without expanding the compressed body."""
    if (type(envelope) is not dict or set(envelope) != _KEYS
        or envelope.get('schema_version') != SCHEMA or envelope.get('encoding') != _ENCODING
        or type(envelope.get('ticker')) is not str or _TICKER.fullmatch(envelope['ticker']) is None
        or (envelope['classification_ref'] is not None and not _hash(envelope['classification_ref']))
        or type(envelope['expanded_bytes']) is not int
        or not 0 < envelope['expanded_bytes'] <= MAX_EXPANDED_BYTES
        or type(envelope['compressed_bytes']) is not int
        or not 0 < envelope['compressed_bytes'] <= MAX_STORED_BYTES * 3 // 4
        or not _hash(envelope['expanded_sha256']) or not _hash(envelope['compressed_sha256'])):
        return None
    payload = envelope['payload_base64']
    if (type(payload) is not str or not payload or len(payload) > MAX_STORED_BYTES
        or len(payload) != 4 * ((envelope['compressed_bytes'] + 2) // 3)
        or _BASE64.fullmatch(payload) is None):
        return None
    # Canonical base64 needs no JSON escaping, so the exact encoded size can be
    # checked without allocating another full copy of its large payload string.
    metadata = dict(envelope, payload_base64='')
    if len(_canonical_bytes(metadata, MAX_STORED_BYTES)) + len(payload) > MAX_STORED_BYTES:
        return None
    return envelope['ticker'], envelope['classification_ref']


def pack_peer_packet(compact_packet, *, max_stored_bytes):
    """Return an exact JSON storage envelope, or None on invalidity/capacity.

    ``max_stored_bytes`` is the caller's remaining packet budget; invalid budgets
    raise ValueError and can never increase the global 8 MiB storage bound.
    """
    if type(max_stored_bytes) is not int or not 0 < max_stored_bytes <= MAX_STORED_BYTES:
        raise ValueError('invalid_peer_packet_storage_budget')
    try:
        metadata = _compact_metadata(compact_packet)
        if metadata is None:
            return None
        _json_shape(compact_packet)
        expanded = _canonical_bytes(compact_packet, MAX_EXPANDED_BYTES)
        compressed = zlib.compress(expanded, level=6)
        # Reject before base64 allocation if even its body cannot fit the budget.
        if 4 * ((len(compressed) + 2) // 3) > max_stored_bytes:
            return None
        envelope = dict(schema_version=SCHEMA, encoding=_ENCODING, ticker=metadata[0],
            classification_ref=metadata[1], expanded_bytes=len(expanded),
            expanded_sha256=sha256(expanded).hexdigest(), compressed_bytes=len(compressed),
            compressed_sha256=sha256(compressed).hexdigest(), payload_base64=b64encode(compressed).decode('ascii'))
        if len(_canonical_bytes(envelope, max_stored_bytes)) > max_stored_bytes:
            return None
        return envelope
    except _FAILURES:
        return None


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('peer_packet_duplicate_json_key')
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError('peer_packet_nonfinite_number')


def _bounded_json_structure(raw):
    """Bound JSON nodes/depth before the parser allocates its object tree.

    The byte tokenizer skips long string bodies in one match; escaped quotes or
    punctuation inside source strings never count as object structure. Syntax
    itself remains the strict JSON parser's responsibility.
    """
    nodes = depth = escaped_until = 0
    in_string = False
    for token in _JSON_TOKENS.finditer(raw):
        start = token.start()
        char = raw[start]
        if in_string:
            if start < escaped_until:
                continue
            if char == 92:  # backslash escapes the next byte, including a quote
                escaped_until = start + 2
            elif char == 34:
                in_string = False
            continue
        if char in (125, 93):
            depth -= 1
            continue
        if char in (44, 58):
            continue
        nodes += 1
        if nodes > MAX_JSON_NODES or depth > MAX_JSON_DEPTH:
            raise ValueError('peer_packet_json_structure_limit')
        if char == 34:
            in_string = True
        elif char in (123, 91):
            depth += 1


def unpack_peer_packet(envelope):
    """Strictly decode one bounded stream; never reseal the original packet."""
    try:
        metadata = _envelope_metadata(envelope)
        if metadata is None:
            return None
        compressed = b64decode(envelope['payload_base64'], validate=True)
        if (len(compressed) != envelope['compressed_bytes']
            or b64encode(compressed).decode('ascii') != envelope['payload_base64']
            or sha256(compressed).hexdigest() != envelope['compressed_sha256']):
            return None
        decoder = zlib.decompressobj()
        # A false small declaration also bounds allocation, before parsing. Do
        # not call flush(), which could emit unbounded remaining stream output.
        expanded = decoder.decompress(compressed, envelope['expanded_bytes'] + 1)
        if (len(expanded) != envelope['expanded_bytes'] or not decoder.eof
            or decoder.unconsumed_tail or decoder.unused_data
            or sha256(expanded).hexdigest() != envelope['expanded_sha256']):
            return None
        _bounded_json_structure(expanded)
        packet = json.loads(expanded.decode('utf-8'), object_pairs_hook=_unique_object,
            parse_constant=_reject_constant)
        if _compact_metadata(packet) != metadata:
            return None
        _json_shape(packet)
        if _canonical_bytes(packet, envelope['expanded_bytes']) != expanded:
            return None
        return packet
    except _FAILURES:
        return None


def peer_classification_ref(packet):
    """Extract a structurally valid reference without decoding storage bodies.

    This supports classification pruning only; it is not source integrity or
    valuation approval. Actual replay must call unpack_peer_packet first.
    """
    try:
        if type(packet) is dict and packet.get('schema_version') == SCHEMA:
            metadata = _envelope_metadata(packet)
        else:
            metadata = _compact_metadata(packet)
        return metadata[1] if metadata is not None else None
    except _FAILURES:
        return None
