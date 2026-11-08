"""Lossless parsed cover evidence and bounded historical snapshot admission."""
from copy import deepcopy
import base64
import hashlib
import json

import pytest

from selected_security_fixtures import fixture, install, validate
from test_online_research_context_store import context as base_context


SCHEMA = 'sec-cover-observations-v1'
SCOPE = dict(profile_key='personal/demo', ticker='FICT', sec_cik='0000001001')


def selected_scope(monkeypatch):
    policy, row, packet, _ = fixture()
    install(monkeypatch, policy)
    scope = validate(policy, row, packet)
    # Construct the proposed persisted representation independently of the producer.
    for document in scope['documents']:
        if 'raw_cover_observations' in document:
            document['cover_observations'] = [
                dict(trading_symbol=value['raw_symbol'], title=value['title'],
                    exchange=value['exchange'], context_id=value['context_id'])
                for value in document.pop('raw_cover_observations')]
        document['cover_observation_schema'] = SCHEMA
    return scope


def research_context(monkeypatch):
    value = base_context(**SCOPE)
    value['peer_read_through']['subject'] = dict(ticker='FICT', sec_cik=SCOPE['sec_cik'],
        selected_security_scope=selected_scope(monkeypatch))
    return value


def document(value):
    return value['peer_read_through']['subject']['selected_security_scope']['documents'][0]


def save(value, root):
    from src.online_research_context_store import save_research_context
    return save_research_context(value, project_root=root, **SCOPE)


def test_producer_preserves_literal_preferred_and_debt_observations_in_order(monkeypatch):
    policy, row, packet, bodies = fixture()
    for role, raw in bodies.items():
        context = raw[raw.index(b'<x:context id="common">'):raw.index(b'</x:context>', raw.index(b'<x:context id="common">')) + len(b'</x:context>')]
        additions = b''
        for number, symbol in enumerate(('FICT PrB', 'FICT/32')):
            identity = f'other-{number}'
            additions += context.replace(b'id="common"', f'id="{identity}"'.encode())
            for concept, text in (('Security12bTitle', 'Preferred Stock' if number == 0 else 'Callable Notes'),
                    ('TradingSymbol', symbol), ('SecurityExchangeName', 'Nasdaq')):
                additions += (f'<ix:nonNumeric id="{identity}-{concept}" name="dei:{concept}" '
                    f'contextRef="{identity}">{text}</ix:nonNumeric>').encode()
        changed = raw.replace(b'</html>', additions + b'</html>')
        digest = hashlib.sha256(changed).hexdigest()
        policy['documents'][role]['sha256'] = digest
        packet['documents'][role].update(payload_sha256=digest,
            payload_raw_base64=base64.b64encode(changed).decode())
    install(monkeypatch, policy)
    original_packet = deepcopy(packet)
    result = validate(policy, row, packet)
    assert result['status'] == 'supported_common'
    for retained in result['documents']:
        assert retained.get('cover_observation_schema') == SCHEMA
        assert retained['cover_observations'] == [
            dict(trading_symbol='FICT', title='Common Stock', exchange='Nasdaq', context_id='common'),
            dict(trading_symbol='FICT PrB', title='Preferred Stock', exchange='Nasdaq', context_id='other-0'),
            dict(trading_symbol='FICT/32', title='Callable Notes', exchange='Nasdaq', context_id='other-1')]
        assert 'raw_cover_observations' not in retained
    assert packet == original_packet
    assert result['original_eps']['eps'] == 1
    assert result['alias_mappings_established'] is False


def test_versioned_cover_snapshot_is_idempotent_exact_and_historical(monkeypatch, tmp_path):
    from src.online_research_context_store import load_research_context, compare_research_contexts
    value = research_context(monkeypatch)
    literal = dict(trading_symbol='FICT PrB', title='Preferred Stock', exchange='Nasdaq',
        context_id='c-' + 'a' * 205)
    document(value)['cover_observations'].append(literal)
    original = deepcopy(value)
    first = save(value, tmp_path)
    second = save(value, tmp_path)
    reopened = load_research_context(first['snapshot_id'], project_root=tmp_path, **SCOPE)
    assert first == second == reopened
    assert reopened['context'] == original == value
    assert document(reopened['context'])['cover_observations'][-1] == literal
    assert reopened['historical'] is True and reopened['current'] is False
    assert compare_research_contexts(first, second)['status'] == 'unchanged'
    assert len(list(tmp_path.rglob('*.json'))) == 1


@pytest.mark.parametrize('change', [
    lambda d: d.update(cover_observation_schema='unrecognized'),
    lambda d: d.pop('cover_observation_schema'),
    lambda d: d.update(cover_observations='filing text'),
    lambda d: d.update(cover_observations=[]),
    lambda d: d.update(cover_observations=d['cover_observations'] * 129),
    lambda d: d['cover_observations'][0].update(trading_symbol={'text': 'FICT'}),
    lambda d: d['cover_observations'][0].update(extra='unrelated'),
    lambda d: d['cover_observations'][0].update(title='<html>filing text</html>'),
    lambda d: d['cover_observations'][0].update(title='&lt;html&gt;filing text&lt;/html&gt;'),
    lambda d: d['cover_observations'][0].update(title='x' * 2001),
    lambda d: d['cover_observations'][0].update(trading_symbol='x' * 129),
    lambda d: d['cover_observations'][0].update(exchange='x' * 257),
    lambda d: d['cover_observations'][0].update(context_id='x' * 513),
    lambda d: d['cover_observations'][0].update(context_id='bad/context'),
    lambda d: d['cover_observations'][0].update(trading_symbol='FICT\x00'),
    lambda d: d['selected_common'].update(ticker='OTHER'),
    lambda d: d['selected_common'].update(title='Unmatched'),
    lambda d: d['selected_common'].update(venue='invented'),
    lambda d: d['selected_common'].update(fact_refs=d['selected_common']['fact_refs'][:2]),
    lambda d: d['selected_common']['fact_refs'].__setitem__(0, 'https://www.sec.gov/Archives/edgar/data/9999/000000100126000001/annual.htm#title'),
    lambda d: d['selected_common']['fact_refs'].__setitem__(0, d['source_ref'] + '#bad/fragment'),
    lambda d: d['selected_common'].update(context_source_ref=d['source_ref'] + '#other'),
    lambda d: d.update(source_ref=d['source_ref'].replace('/1001/', '/9999/')),
    lambda d: d.update(accessionNumber='0000001001-26-999999'),
    lambda d: d.update(primaryDocument='other.htm'),
    lambda d: d.update(body_sha256='invalid'),
    lambda d: d.update(isInlineXBRL=True),
    lambda d: d.update(filingDate='2025-01-01'),
    lambda d: d.update(extra={'text': 'filing body'}),
])
def test_malformed_or_unbound_cover_evidence_is_rejected_before_writing(monkeypatch, tmp_path, change):
    value = research_context(monkeypatch)
    change(document(value))
    with pytest.raises(ValueError, match='cover|selected'):
        save(value, tmp_path)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('placement', ['notes', 'notes_scope', 'selected_common', 'scope'])
def test_cover_fields_cannot_wrap_body_content_outside_document_contract(monkeypatch, tmp_path, placement):
    value = research_context(monkeypatch)
    if placement == 'notes':
        value['notes']['cover_observations'] = [{'title': '<html>body</html>'}]
    elif placement == 'notes_scope':
        value['notes']['selected_security_scope'] = deepcopy(value['peer_read_through']['subject']['selected_security_scope'])
    elif placement == 'selected_common':
        document(value)['selected_common']['cover_observations'] = []
    else:
        value['peer_read_through']['subject']['selected_security_scope']['cover_observations'] = []
    with pytest.raises(ValueError, match='cover|selected'):
        save(value, tmp_path)


@pytest.mark.parametrize('field', ['raw', 'raw_body', 'payload_raw_base64', 'raw_symbol', 'raw_cover_observations'])
def test_original_archive_guard_still_rejects_every_raw_field(monkeypatch, tmp_path, field):
    value = research_context(monkeypatch)
    value['notes'][field] = 'normalized-looking text'
    with pytest.raises(ValueError, match='raw/archive'):
        save(value, tmp_path)


def test_resealed_structurally_tampered_snapshot_still_rejects_on_replay(monkeypatch, tmp_path):
    from src import online_research_context_store as store
    first = save(research_context(monkeypatch), tmp_path)
    path = next(tmp_path.rglob(first['snapshot_id'] + '.json'))
    changed = deepcopy(first)
    document(changed['context'])['selected_common']['fact_refs'][0] = 'https://www.sec.gov/Archives/edgar/data/9999/000000100126000001/annual.htm#title'
    changed['snapshot_id'] = store._digest(store._identity(changed['context']))
    changed['snapshot_sha256'] = store._digest({key: child for key, child in changed.items() if key != 'snapshot_sha256'})
    path.unlink()
    path.with_name(changed['snapshot_id'] + '.json').write_text(json.dumps(changed))
    with pytest.raises(ValueError, match='cover|selected'):
        store.load_research_context(changed['snapshot_id'], project_root=tmp_path, **SCOPE)


def test_historical_replay_uses_recorded_relationships_without_mutable_policy(monkeypatch, tmp_path):
    from src import sec_selected_security
    from src.online_research_context_store import load_research_context
    value = research_context(monkeypatch)
    # A filer agent accession is valid when the issuer directory and recorded metadata agree.
    annual = document(value)
    old = annual['accessionNumber']
    new = '0001193125-26-000001'
    encoded = json.dumps(value).replace(old, new).replace(old.replace('-', ''), new.replace('-', ''))
    value = json.loads(encoded)
    first = save(value, tmp_path)
    monkeypatch.setattr(sec_selected_security, 'POLICIES', ())
    assert load_research_context(first['snapshot_id'], project_root=tmp_path, **SCOPE) == first


@pytest.mark.parametrize('field', ['role', 'binding_normalization'])
def test_non_string_document_discriminators_fail_closed(monkeypatch, tmp_path, field):
    value = research_context(monkeypatch)
    document(value)[field] = []
    with pytest.raises(ValueError, match='cover|selected'):
        save(value, tmp_path)


def test_scope_eps_proof_cannot_omit_the_existing_numeric_token_guard(monkeypatch, tmp_path):
    value = research_context(monkeypatch)
    proof = value['peer_read_through']['subject']['selected_security_scope']['original_eps']['proofs'][0]
    proof.pop('raw_text')
    with pytest.raises(ValueError, match='cover|selected|raw/archive'):
        save(value, tmp_path)


@pytest.mark.parametrize('change', [
    lambda value, scope: scope.update(ticker='OTHER'),
    lambda value, scope: scope.update(sec_cik='0000009999'),
    lambda value, scope: scope.update(commercial_eligible=True),
    lambda value, scope: scope.update(alias_mappings_established=True),
    lambda value, scope: scope.update(unassigned_issuer_symbols=['OTHER']),
    lambda value, scope: scope['original_eps'].update(period_end='2025-12-30'),
    lambda value, scope: scope['original_eps']['proofs'][0].update(source_ref=scope['documents'][1]['source_ref'] + '#eps-fact'),
    lambda value, scope: value['peer_read_through']['subject'].update(sec_cik='0000009999'),
    lambda value, scope: value['notes'].update(duplicate_document=scope['documents'][0]),
])
def test_recorded_scope_and_eps_relationships_cannot_be_rebound(monkeypatch, tmp_path, change):
    value = research_context(monkeypatch)
    scope = value['peer_read_through']['subject']['selected_security_scope']
    change(value, scope)
    with pytest.raises(ValueError, match='cover|selected'):
        save(value, tmp_path)


@pytest.mark.parametrize('kind', ['financial', 'cover'])
def test_companion_fact_context_and_eps_sources_survive_exact_snapshot(monkeypatch, tmp_path, kind):
    from document_set_fixtures import document_set_fixture
    from src.online_research_context_store import load_research_context
    policy, row, packet, _ = document_set_fixture(kind)
    install(monkeypatch, policy)
    scope = validate(policy, row, packet)
    value = base_context(**SCOPE)
    value['peer_read_through']['subject'] = dict(ticker='FICT', sec_cik=SCOPE['sec_cik'], selected_security_scope=scope)
    first = save(value, tmp_path)
    assert load_research_context(first['snapshot_id'], project_root=tmp_path, **SCOPE)['context'] == value
    assert len(scope['documents']) == (3 if kind == 'financial' else 4)


@pytest.mark.parametrize('field', ['parent_source_ref', 'parent_form', 'accessionNumber', 'parent_href'])
def test_companion_relationship_tamper_cannot_relabel_source_documents(monkeypatch, tmp_path, field):
    from document_set_fixtures import document_set_fixture
    policy, row, packet, _ = document_set_fixture('cover')
    install(monkeypatch, policy)
    scope = validate(policy, row, packet)
    value = base_context(**SCOPE)
    value['peer_read_through']['subject'] = dict(ticker='FICT', sec_cik=SCOPE['sec_cik'], selected_security_scope=scope)
    scope['documents'][1][field] = 'unrelated'
    with pytest.raises(ValueError, match='cover|selected'):
        save(value, tmp_path)


def excluded_bank_context(monkeypatch):
    from test_bank_peer_security import bank_collection
    from test_online_peer_valuation import build
    from selected_security_fixtures import digest
    collection = bank_collection(monkeypatch)
    peer = collection['issuers'][1]
    peer['profile']['payload']['sic'] = '6022'
    peer['profile']['normalized_sha256'] = digest(peer['profile']['payload'])
    result = build(collection)
    assert result['status'] == 'withheld' and result['peer_count'] == 2
    assert result['excluded'][0]['reason'] == 'sec_industry_differs'
    value = base_context(**SCOPE)
    value['peer_read_through'] = result
    return value


def test_excluded_bank_keeps_its_independent_observation_outside_benchmark(monkeypatch, tmp_path):
    from src.online_research_context_store import load_research_context
    value = excluded_bank_context(monkeypatch)
    independent = value['peer_read_through']['excluded'][0]['diagnostics']['independent_observation_not_in_benchmark']
    assert independent['ticker'] == 'FA' and independent['selected_security_scope']['status'] == 'supported_common'
    first = save(value, tmp_path)
    reopened = load_research_context(first['snapshot_id'], project_root=tmp_path, **SCOPE)
    assert reopened['context'] == value
    result = reopened['context']['peer_read_through']
    assert result['status'] == 'withheld' and result['peer_count'] == 2
    assert result['peer_median'] is None and result['premium_fraction'] is None
    assert [peer['ticker'] for peer in result['peers']] == ['FB', 'FC']
    assert result['excluded'][0]['diagnostics']['independent_observation_not_in_benchmark'] == independent


@pytest.mark.parametrize('owner,field', [
    ('excluded', 'ticker'), ('diagnostics', 'ticker'), ('diagnostics', 'sec_cik'),
    ('independent', 'ticker'), ('independent', 'sec_cik'),
])
def test_excluded_independent_cover_cannot_diverge_from_recorded_owners(monkeypatch, tmp_path, owner, field):
    value = excluded_bank_context(monkeypatch)
    excluded = value['peer_read_through']['excluded'][0]
    diagnostics = excluded['diagnostics']
    target = {'excluded': excluded, 'diagnostics': diagnostics,
        'independent': diagnostics['independent_observation_not_in_benchmark']}[owner]
    target[field] = 'OTHER' if field == 'ticker' else '0000009999'
    with pytest.raises(ValueError, match='cover|selected'):
        save(value, tmp_path)


def test_excluded_independent_cover_scope_is_not_admitted_under_extra_nesting(monkeypatch, tmp_path):
    value = excluded_bank_context(monkeypatch)
    diagnostics = value['peer_read_through']['excluded'][0]['diagnostics']
    independent = diagnostics.pop('independent_observation_not_in_benchmark')
    diagnostics['extra'] = {'independent_observation_not_in_benchmark': independent}
    with pytest.raises(ValueError, match='cover|selected'):
        save(value, tmp_path)


def test_official_filing_day_can_follow_utc_acceptance_day(monkeypatch, tmp_path):
    from src.online_research_context_store import load_research_context
    value = research_context(monkeypatch)
    annual = document(value)
    annual['filingDate'] = '2026-02-02'
    annual['acceptanceDateTime'] = '2026-02-01T23:14:52Z'
    first = save(value, tmp_path)
    assert load_research_context(first['snapshot_id'], project_root=tmp_path, **SCOPE)['context'] == value


@pytest.mark.parametrize('field,stamp', [
    ('acceptanceDateTime', '2026-11-08T12:00:00Z'),
    ('filingDate', '2026-11-08'), ('filingDate', '2026-99-01'),
])
def test_independent_metadata_dates_remain_bounded_by_recorded_capture(monkeypatch, tmp_path, field, stamp):
    value = research_context(monkeypatch)
    document(value)[field] = stamp
    with pytest.raises(ValueError, match='cover|selected'):
        save(value, tmp_path)


def test_source_validated_fragment_companion_href_roundtrips_literally(monkeypatch, tmp_path):
    from document_set_fixtures import document_set_fixture, reseal
    from src.online_research_context_store import load_research_context
    policy, row, packet, raw = document_set_fixture('financial')
    companion = policy['documents']['annual']['companion']
    original = companion['href']
    companion['href'] = original + '#section:1'
    raw['annual'] = raw['annual'].replace(f'href="{original}"'.encode(), f'href="{companion["href"]}"'.encode())
    reseal(policy, packet, raw, 'annual')
    install(monkeypatch, policy)
    scope = validate(policy, row, packet)
    assert scope['status'] == 'supported_common'
    assert scope['documents'][1]['parent_href'] == 'annual-linked.htm#section:1'
    value = base_context(**SCOPE)
    value['peer_read_through']['subject'] = dict(ticker='FICT', sec_cik=SCOPE['sec_cik'], selected_security_scope=scope)
    first = save(value, tmp_path)
    assert load_research_context(first['snapshot_id'], project_root=tmp_path, **SCOPE)['context'] == value


@pytest.mark.parametrize('href', ['other.htm#section', 'annual-linked.htm#',
    'annual-linked.htm#bad/fragment', 'annual-linked.htm#' + 'a' * 201,
    'annual-linked.htm#section#other', 'annual-linked.htm?query=1#section'])
def test_fragment_companion_href_rejects_wrong_filename_or_unsafe_fragment(monkeypatch, tmp_path, href):
    from document_set_fixtures import document_set_fixture
    policy, row, packet, _ = document_set_fixture('financial')
    install(monkeypatch, policy)
    scope = validate(policy, row, packet)
    scope['documents'][1]['parent_href'] = href
    value = base_context(**SCOPE)
    value['peer_read_through']['subject'] = dict(ticker='FICT', sec_cik=SCOPE['sec_cik'], selected_security_scope=scope)
    with pytest.raises(ValueError, match='cover|selected'):
        save(value, tmp_path)
