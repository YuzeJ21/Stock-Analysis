"""Exact, inspection-only SAP literal permission for normalized historical replay."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import re
from zoneinfo import ZoneInfo

from src.company_sec_online_preview import _utc_timestamp
from src.online_filing_context import validated_filing_inventory
from src.online_peer_valuation import RIGHTS as PEER_RIGHTS, FISCAL_WINDOW_DAYS, MIN_PEERS
from src.sec_exact_filing import RIGHTS
from src.sec_inline_filing import valid_numeric_proof
from src.sec_selected_security import _url
from src.sec_selected_security_policies import POLICIES

POLICY_ID = 'sap-nyse-ads-2026-v2'
LEGACY_POLICY_ID = 'sap-nyse-ads-2026-v1'
TICKER, CIK = 'SAP', '0001000184'
SUBJECT_PATH = ('peer_read_through', 'subject_source_context', 'selected_security_scope')
REASON = 'depositary_security_requires_separate_method'
_FACT_FIELDS = ('entity_cik', 'period_start', 'period_end', 'dimensions', 'context_id', 'concept', 'namespace_uri')


def _hash(value):
    return isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value) is not None


def _listing_matches(listing, policy, now, peer, *, legacy):
    expected = dict(ticker=TICKER, sec_cik=CIK, venue='NYSE', security_type='depositary_receipt',
                    source_url='https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt')
    if (not isinstance(listing, dict) or set(listing) != {*expected, 'description', 'source_created_at', 'observed_at', 'payload_sha256'}
            or any(listing[key] != value for key, value in expected.items())
            or not isinstance(listing['description'], str)
            or ' '.join(listing['description'].split()).casefold() != policy['depositary_directory_title'].casefold()
            or not _hash(listing['payload_sha256'])):
        return False
    observed = _utc_timestamp(listing['observed_at'])
    clock = listing['source_created_at']
    created = datetime.strptime(clock, '%Y-%m-%dT%H:%M')
    if created.strftime('%Y-%m-%dT%H:%M') != clock:
        return False
    created = created.replace(tzinfo=ZoneInfo('America/New_York')).astimezone(timezone.utc)
    if not (observed and observed <= now and timedelta(0) <= observed-created <= timedelta(days=7)):
        return False
    listing_context = peer.get('listing_context')
    if legacy and listing_context is None:
        return True
    if (not isinstance(listing_context, dict) or listing_context.get('schema_version') != 'online-listing-session-v1'
            or not isinstance(listing_context.get('source_receipts'), list)):
        return False
    receipts = [ref for ref in listing_context['source_receipts']
                if isinstance(ref, dict) and ref.get('source_url') == listing['source_url']]
    return len(receipts) == 1 and all(receipts[0].get(key) == listing[key] for key in
        ('source_url', 'observed_at', 'payload_sha256', 'source_created_at'))


def _rules(annual, *, legacy):
    if not legacy:
        return annual['inspection_observations']
    notes = [dict(rule) for rule in annual['inspection_observations'] if rule['kind'] == 'element_note']
    notes[0].pop('extract', None)
    notes[0]['label'] = 'NYSE ADS listing and one ordinary share per ADS'
    return notes


def _observation_matches(row, rule, doc):
    if not isinstance(row, dict) or row.get('financial_eligible') is not False:
        return False
    url = doc['source_ref']
    expected = dict(kind=rule['kind'], label=rule['label'], filing_cik=CIK, financial_eligible=False,
                    role='annual', observed_at=doc['observed_at'], publication_date=doc['filingDate'],
                    accession=doc['accessionNumber'], rights_status=RIGHTS, source_ref=url)
    if rule['kind'] == 'element_note':
        expected.update(location=rule['path'], text_sha256=rule['text_sha256'])
        if rule.get('extract') == 'adr_ordinary_ratio':
            if type(row.get('value')) is not int:
                return False
            expected.update(value=1, unit='ordinary_shares/ADR')
        return row == expected
    if rule['kind'] != 'numeric':
        return False
    expected.update({key: rule[key] for key in _FACT_FIELDS})
    expected.update(source_ref=url + '#' + rule['fact_id'], context_source_ref=url + '#' + rule['context_id'],
                    unit=rule['currency'] + '/shares', unit_source_ref=url + '#' + rule['unit_id'],
                    currency_basis=rule['currency_basis'], security_basis=rule['security_basis'],
                    scale=0, sign='', decimals='2', transformation='num-dot-decimal')
    literal = row.get('raw_text')
    return (set(row) == {*expected, 'raw_text', 'value'}
            and all(type(row[key]) is type(value) and row[key] == value for key, value in expected.items())
            and isinstance(literal, str) and sha256(literal.encode()).hexdigest() == rule['raw_text_sha256']
            and type(row['value']) in {int, float} and valid_numeric_proof(row))


def saved_sap_numeric_observation_indices(scope, *, context):
    """Return v2 indices, an empty tuple for legacy notes, or None for invalid data."""
    try:
        if (not isinstance(scope, dict) or (context.get('ticker'), context.get('sec_cik')) != (TICKER, CIK)
                or scope.get('alias_mappings_established') is not False or scope.get('commercial_eligible') is not False
                or scope.get('technical_interpretation_only') is not True):
            return None
        peer = context['peer_read_through']
        owner = peer['subject_source_context']
        now = _utc_timestamp(context['observed_at'])
        legacy = scope.get('policy_id') == LEGACY_POLICY_ID
        if (not now or owner.get('sec_cik') != CIK or owner.get('ticker', TICKER) != TICKER
                or peer.get('ticker') != TICKER or peer.get('metric') != 'reported_annual_diluted_pe'
                or peer.get('commercial_eligible') is not False or peer.get('saved_readiness_promoted') is not False
                or peer.get('rights_status') != PEER_RIGHTS
                or type(peer.get('fiscal_window_days')) is not int or peer['fiscal_window_days'] != FISCAL_WINDOW_DAYS
                or type(peer.get('minimum_peers')) is not int or peer['minimum_peers'] != MIN_PEERS
                or peer.get('status') != 'withheld' or peer.get('reason') != REASON or peer.get('peers') != []
                or type(peer.get('peer_count')) is not int or peer['peer_count'] != 0
                or any(peer.get(key) is not None for key in ('subject', 'peer_median', 'premium_fraction'))
                or owner.get('profile_source_ref') != f'https://data.sec.gov/submissions/CIK{CIK}.json'
                or not _hash(owner.get('profile_sha256'))):
            return None
        profile_stamp = _utc_timestamp(owner.get('profile_observed_at'))
        if not profile_stamp or profile_stamp > now:
            return None
        policy = next((p for p in POLICIES if (p['policy_id'], p['ticker'], p['sec_cik'], p['kind'])
                       == (POLICY_ID, TICKER, CIK, 'inspection_only')), None)
        if not policy or not _listing_matches(owner.get('selected_depositary_listing'), policy, now, peer, legacy=legacy):
            return None
        expected = dict(status='inspection_only', reason=REASON, policy_id=LEGACY_POLICY_ID if legacy else POLICY_ID, ticker=TICKER, sec_cik=CIK,
                        issuer_symbols=policy['issuer_symbols'], unassigned_issuer_symbols=['SAPGF'], basis_refs=[],
                        alias_mappings_established=False, technical_interpretation_only=True,
                        commercial_eligible=False, rights_status=RIGHTS)
        if (set(scope) != {*expected, 'documents', 'evidence_observations'}
                or any(scope[key] != value for key, value in expected.items())
                or not isinstance(scope['documents'], list) or len(scope['documents']) != 1):
            return None
        annual = policy['documents']['annual']
        meta = annual['metadata']
        doc = scope['documents'][0]
        binding = dict(role='annual', **meta, source_ref=_url(CIK, meta), body_sha256=annual['body_sha256'],
                       binding_normalization=annual['normalization'], reference_capture_sha256=annual['sha256'])
        if (not isinstance(doc, dict) or set(doc) != {*binding, 'observed_at', 'payload_sha256'}
                or any(type(doc[key]) is not type(value) or doc[key] != value for key, value in binding.items())
                or not _hash(doc['payload_sha256'])):
            return None
        observed, accepted = _utc_timestamp(doc['observed_at']), _utc_timestamp(meta['acceptanceDateTime'])
        if not (observed and accepted and accepted <= observed <= now and accepted <= profile_stamp <= now):
            return None
        versions = [dict(form=meta['form'], period_end=meta['reportDate'], filed=meta['filingDate'],
                         accepted_at=meta['acceptanceDateTime'], accession=meta['accessionNumber'],
                         source_ref=doc['source_ref'])]
        if (owner.get('annual_versions') != versions
                or owner.get('facts_query_ref') != f'https://data.sec.gov/api/xbrl/companyfacts/CIK{CIK}.json'):
            return None
        inventory = validated_filing_inventory(context.get('filing_inventory'), ticker=TICKER,
                                              expected_cik=CIK, as_of=now, allow_historical=True)
        anchor = inventory['latest']['annual'] if inventory else None
        if not (anchor and anchor['accession'] == meta['accessionNumber'] and anchor['period_end'] == meta['reportDate']
                and anchor['filed'] == meta['filingDate'] and anchor['form'] == meta['form']
                and anchor['source_url'] == doc['source_ref'] and _utc_timestamp(anchor['accepted_at']) == accepted):
            return None
        rows, rules = scope['evidence_observations'], _rules(annual, legacy=legacy)
        if (not isinstance(rows, list) or len(rows) != len(rules)
                or not all(_observation_matches(row, rule, doc) for row, rule in zip(rows, rules))):
            return None
        return tuple(i for i, rule in enumerate(rules) if rule['kind'] == 'numeric')
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError):
        return None
