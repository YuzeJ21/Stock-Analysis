"""Offline validation of TSM's normalized, inspection-only annual evidence."""
import re

from src.company_sec_online_preview import _utc_timestamp
from src.online_filing_context import validated_filing_inventory
from src.sec_exact_filing import RIGHTS
from src.sec_inline_filing import valid_numeric_proof
from src.sec_selected_security import _url
from src.sec_selected_security_policies import POLICIES


POLICY_ID = 'tsm-identity-gap-2026-v2'
TICKER, CIK = 'TSM', '0001046179'
REASON = 'depositary_security_requires_separate_method'
SUBJECT_PATH = ('peer_read_through', 'subject_source_context', 'selected_security_scope')
_FACT_FIELDS = ('entity_cik', 'period_start', 'period_end', 'dimensions', 'context_id', 'concept', 'namespace_uri')


def _historical_annual(context, doc, metadata):
    now = _utc_timestamp(context.get('observed_at'))
    observed = _utc_timestamp(doc.get('observed_at'))
    accepted = _utc_timestamp(metadata['acceptanceDateTime'])
    if not (now and observed and accepted and accepted <= observed <= now):
        return False
    inventory = validated_filing_inventory(context.get('filing_inventory'), ticker=TICKER, expected_cik=CIK,
                                          as_of=now, allow_historical=True)
    anchor = inventory['latest']['annual'] if inventory else None
    return bool(anchor and anchor['accession'] == metadata['accessionNumber']
                and anchor['period_end'] == metadata['reportDate'] and anchor['filed'] == metadata['filingDate']
                and anchor['form'] == metadata['form'] and anchor['source_url'] == doc['source_ref']
                and _utc_timestamp(anchor['accepted_at']) == accepted)


def _document_matches(doc, policy, context):
    if not isinstance(doc, dict):
        return False
    metadata = policy['metadata']
    expected = dict(role='annual', **metadata, source_ref=_url(CIK, metadata),
                    body_sha256=policy['body_sha256'], binding_normalization=policy['normalization'],
                    reference_capture_sha256=policy['sha256'])
    return (set(doc) == {*expected, 'observed_at', 'payload_sha256'}
            and all(type(doc[key]) is type(value) and doc[key] == value for key, value in expected.items())
            and isinstance(doc['payload_sha256'], str) and re.fullmatch(r'[0-9a-f]{64}', doc['payload_sha256'])
            and _historical_annual(context, doc, metadata))


def _observation_matches(row, rule, doc):
    if not isinstance(row, dict) or row.get('financial_eligible') is not False:
        return False
    url = doc['source_ref']
    expected = dict(kind=rule['kind'], label=rule['label'], filing_cik=CIK, financial_eligible=False,
                    role=doc['role'], observed_at=doc['observed_at'], publication_date=doc['filingDate'],
                    accession=doc['accessionNumber'], rights_status=RIGHTS, source_ref=url)
    if rule['kind'] == 'element_note':
        expected.update(location=rule['path'], text_sha256=rule['text_sha256'])
        if rule.get('extract') == 'ads_common_ratio':
            ratio = row.get('value')
            if type(ratio) is not int or not 1 <= ratio <= 9999:
                return False
            expected.update(value=ratio, unit='ordinary_shares/ADS')
        return row == expected
    expected.update({key: rule[key] for key in _FACT_FIELDS})
    expected.update(source_ref=url + '#' + rule['fact_id'], context_source_ref=url + '#' + rule['context_id'])
    if rule['kind'] == 'note':
        expected.update(text_sha256=rule['text_sha256'],
                        source_refs=[url + '#' + fact for fact in (rule['fact_id'], *rule['continuations'])])
        return row == expected
    expected.update(unit=rule['currency'] + '/shares', unit_source_ref=url + '#' + rule['unit_id'],
                    currency_basis=rule['currency_basis'], security_basis=rule['security_basis'],
                    scale=0, sign='', decimals='2', transformation=None)
    literal = row.get('raw_text')
    return (set(row) == {*expected, 'raw_text', 'value'}
            and all(row[key] == value for key, value in expected.items())
            and isinstance(literal, str) and re.fullmatch(r'[0-9]+\.[0-9]{2}', literal) is not None
            and type(row['value']) in {int, float} and valid_numeric_proof(row))


def saved_tsm_numeric_observation_indices(scope, *, context):
    """Permit literal tokens only after checking the complete recorded scope.

    The live producer checks the original filing bytes. This replay check binds
    the normalized rows to that reviewed filing contract and rederives literals.
    """
    if (not isinstance(scope, dict) or (context.get('ticker'), context.get('sec_cik')) != (TICKER, CIK)
            or scope.get('alias_mappings_established') is not False or scope.get('commercial_eligible') is not False
            or scope.get('technical_interpretation_only') is not True):
        return ()
    peer = context['peer_read_through']
    owner = peer['subject_source_context']
    if (owner.get('sec_cik') != CIK or owner.get('ticker', TICKER) != TICKER
            or peer.get('status') != 'withheld' or peer.get('reason') != REASON or peer.get('peers')
            or any(peer.get(key) is not None for key in ('subject', 'peer_median', 'premium_fraction'))):
        return ()
    policy = next((p for p in POLICIES if (p['policy_id'], p['ticker'], p['sec_cik'], p['kind'])
                   == (POLICY_ID, TICKER, CIK, 'inspection_only')), None)
    if not policy:
        return ()
    expected = dict(status='inspection_only', reason=REASON, policy_id=POLICY_ID, ticker=TICKER, sec_cik=CIK,
                    issuer_symbols=policy['issuer_symbols'], unassigned_issuer_symbols=['TSMWF'], basis_refs=[],
                    alias_mappings_established=False, technical_interpretation_only=True,
                    commercial_eligible=False, rights_status=RIGHTS)
    if (set(scope) != {*expected, 'documents', 'evidence_observations'}
            or any(scope[key] != value for key, value in expected.items())):
        return ()
    annual = policy['documents']['annual']
    documents, rows = scope['documents'], scope['evidence_observations']
    rules = annual['inspection_observations']
    if (not isinstance(documents, list) or len(documents) != 1
            or not _document_matches(documents[0], annual, context)
            or not isinstance(rows, list) or len(rows) != len(rules)
            or not all(_observation_matches(row, rule, documents[0]) for row, rule in zip(rows, rules))):
        return ()
    return tuple(index for index, rule in enumerate(rules) if rule['kind'] == 'numeric')
