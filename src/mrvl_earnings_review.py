"""Pure, bounded annual SEC evidence review; no valuation or admission authority."""
from collections.abc import Mapping
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import base64
import binascii
import hashlib
import json
import math
import re
import xml.etree.ElementTree as ET

from src.company_sec_online_preview import _iso_date, _utc_timestamp
from src.online_company_identity import _mode_reason
from src.sec_inline_filing import _tree, _qname, _date_fact, X, IX, XSI
from src.sec_exact_filing import MAX_FILING_BYTES

SCHEMA = 'mrvl-earnings-review-v1'
MRVL_CIK = '0001835632'
AVGO_CIK = '0001730168'
RIGHTS = 'personal_research_only_commercial_and_redistribution_unverified'
MAX_NORMALIZED_BYTES = 2 * 1024 * 1024
FISCAL_WINDOW_DAYS = 35
FIELDS = (
    ('diluted_eps', 'EarningsPerShareDiluted', 'USD/shares'),
    ('net_income', 'NetIncomeLoss', 'USD'),
    ('cash_from_operations', 'NetCashProvidedByUsedInOperatingActivities', 'USD'),
    ('capital_expenditures', 'PaymentsToAcquirePropertyPlantAndEquipment', 'USD'),
    ('share_based_compensation', 'ShareBasedCompensation', 'USD'),
    ('amortization_of_intangibles', 'AmortizationOfIntangibleAssets', 'USD'),
    ('gain_on_sale_of_business', 'GainLossOnSaleOfBusiness', 'USD'),
)
POLICIES = {
    'MRVL': dict(sec_cik=MRVL_CIK, accession='0001835632-26-000011', form='10-K',
        filed='2026-03-11', period_start='2025-02-02', period_end='2026-01-31',
        primary_document='mrvl-20260131.htm',
        source_url='https://www.sec.gov/Archives/edgar/data/1835632/000183563226000011/mrvl-20260131.htm'),
    'AVGO': dict(sec_cik=AVGO_CIK, accession='0001730168-25-000121', form='10-K',
        filed='2025-12-18', period_start='2024-11-04', period_end='2025-11-02',
        primary_document='avgo-20251102.htm',
        source_url='https://www.sec.gov/Archives/edgar/data/1730168/000173016825000121/avgo-20251102.htm'),
}
MRVL = POLICIES['MRVL']
AVGO = POLICIES['AVGO']
_SHA = re.compile(r'[0-9a-f]{64}\Z')
_PROFILE_COLUMNS = ('form', 'reportDate', 'filingDate', 'accessionNumber', 'primaryDocument')
_FACT_COLUMNS = ('val', 'start', 'end', 'accn', 'form', 'filed', 'fp', 'fy')
_NORMALIZATION = 'mrvl_annual_evidence_subset_v1'
_ERRORS = (ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError)


class _Hold(ValueError):
    pass


def _need(condition, reason):
    if not condition:
        raise _Hold(reason)


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def _digest(value):
    return hashlib.sha256(_json(value)).hexdigest()


def _cik(value):
    _need(type(value) in {int, str} and re.fullmatch(r'\d{1,10}', str(value)) is not None
          and int(value) > 0, 'review_issuer_identity_mismatch')
    return str(int(value)).zfill(10)


def _sha(value):
    return isinstance(value, str) and _SHA.fullmatch(value) is not None


def _now(value):
    now = datetime.now(timezone.utc) if value is None else value
    _need(isinstance(now, datetime) and now.utcoffset() is not None, 'review_observation_invalid')
    return now.astimezone(timezone.utc)


def _fresh(value, now):
    observed = _utc_timestamp(value)
    _need(observed is not None and timedelta(0) <= now-observed <= timedelta(hours=24),
          'review_source_stale_or_future')
    return observed


def _source_ref(receipt):
    return {k: receipt[k] for k in ('source_url', 'observed_at', 'payload_sha256')}


def _base_receipt(receipt, url, now=None):
    _need(isinstance(receipt, Mapping) and receipt.get('status') == 'ready'
          and receipt.get('source_url') == url, 'review_source_unavailable_or_mismatched')
    _need(_sha(receipt.get('payload_sha256')), 'review_raw_digest_missing')
    _need(_utc_timestamp(receipt.get('observed_at')) is not None, 'review_observation_invalid')
    if now is not None:
        _fresh(receipt['observed_at'], now)


def _normalization_input(receipt, kind):
    _need(isinstance(receipt, Mapping) and isinstance(receipt.get('payload'), Mapping),
          'review_normalization_invalid')
    body = receipt['payload']
    cik = _cik(body.get('cik'))
    if kind == 'facts':
        _need(cik == MRVL_CIK, 'review_issuer_identity_mismatch')
    else:
        _need(cik in {MRVL_CIK, AVGO_CIK}, 'review_issuer_identity_mismatch')
    prefix = 'api/xbrl/companyfacts' if kind == 'facts' else 'submissions'
    _base_receipt(receipt, f'https://data.sec.gov/{prefix}/CIK{cik}.json')
    if 'normalized_sha256' in receipt:
        _need(receipt.get('normalization') == _NORMALIZATION
              and receipt['normalized_sha256'] == _digest(body), 'review_normalized_payload_changed')
    return body


def _normalized(receipt, payload):
    _need(len(_json(payload)) <= MAX_NORMALIZED_BYTES, 'review_normalized_payload_oversized')
    return dict(status='ready', **_source_ref(receipt), payload=deepcopy(payload),
                normalized_sha256=_digest(payload), normalization=_NORMALIZATION)


def normalize_review_facts(receipt):
    """Keep exactly the seven concepts; raw and reduced payload digests stay distinct."""
    try:
        body = _normalization_input(receipt, 'facts')
        facts = body.get('facts')
        _need(isinstance(facts, Mapping) and isinstance(facts.get('us-gaap'), Mapping),
              'review_facts_schema_invalid')
        selected = {}
        for _, concept, _ in FIELDS:
            if concept not in facts['us-gaap']:
                continue
            fact = facts['us-gaap'][concept]
            _need(isinstance(fact, Mapping) and isinstance(fact.get('units'), Mapping)
                  and len(fact['units']) <= 16, 'review_facts_schema_invalid')
            units = {}
            for unit, rows in fact['units'].items():
                _need(isinstance(unit, str) and len(unit) <= 80 and isinstance(rows, list)
                      and len(rows) <= 10000 and all(isinstance(r, Mapping) for r in rows),
                      'review_facts_schema_invalid')
                selected_rows = []
                for r in rows:
                    row = {k: r[k] for k in _FACT_COLUMNS if k in r}
                    # JSON numeric overflow can decode as infinity. Preserve an
                    # explicit unusable marker so other fields remain reviewable;
                    # the original HTTP digest is never replaced by this subset.
                    if type(row.get('val')) is float and not math.isfinite(row['val']):
                        row['val'] = 'nonfinite_source_number'
                    selected_rows.append(row)
                units[unit] = selected_rows
            selected[concept] = {'units': units}
        return _normalized(receipt, dict(cik=body['cik'], facts={'us-gaap': selected}))
    except _ERRORS:
        return dict(status='unavailable', reason='review_facts_normalization_invalid')


def normalize_review_profile(receipt):
    """Retain current annual/amendment metadata, never a selected older fallback."""
    try:
        body = _normalization_input(receipt, 'profile')
        filings = body.get('filings')
        recent = filings.get('recent') if isinstance(filings, Mapping) else None
        columns = _PROFILE_COLUMNS + tuple(k for k in ('acceptanceDateTime', 'isInlineXBRL', 'isXBRL')
                                           if isinstance(recent, Mapping) and k in recent)
        _need(isinstance(recent, Mapping) and all(isinstance(recent.get(k), list) for k in columns),
              'review_profile_schema_invalid')
        count = len(recent['form'])
        _need(0 < count <= 2000 and all(len(recent[k]) == count for k in columns),
              'review_profile_schema_invalid')
        return _normalized(receipt, dict(cik=body['cik'], tickers=body.get('tickers'),
            filings={'recent': {k: recent[k] for k in columns}}))
    except _ERRORS:
        return dict(status='unavailable', reason='review_profile_normalization_invalid')


def seal_review_packet(packet):
    """Return an independent content seal; validation still occurs on every read."""
    try:
        _need(isinstance(packet, Mapping), 'review_packet_invalid')
        result = deepcopy({k: v for k, v in packet.items() if k != 'packet_digest'})
        result['packet_digest'] = _digest(result)
        return result
    except _ERRORS:
        return dict(schema_version=SCHEMA, ticker='MRVL', reason='review_packet_unsealable')


def _receipt_payload(receipt, url, now):
    _base_receipt(receipt, url, now)
    body = receipt.get('payload')
    _need(isinstance(body, Mapping) and receipt.get('normalization') == _NORMALIZATION
          and len(_json(body)) <= MAX_NORMALIZED_BYTES
          and receipt.get('normalized_sha256') == _digest(body), 'review_normalized_payload_changed')
    return body


def _profile(receipt, ticker, now):
    policy = POLICIES[ticker]
    body = _receipt_payload(receipt, f'https://data.sec.gov/submissions/CIK{policy["sec_cik"]}.json', now)
    _need(_cik(body.get('cik')) == policy['sec_cik'] and body.get('tickers') == [ticker],
          'review_profile_identity_mismatch')
    recent = body.get('filings', {}).get('recent')
    columns = _PROFILE_COLUMNS + (('acceptanceDateTime',) if isinstance(recent, Mapping) and 'acceptanceDateTime' in recent else ())
    _need(isinstance(recent, Mapping) and all(isinstance(recent.get(k), list) for k in columns),
          'review_profile_schema_invalid')
    count = len(recent['form'])
    _need(0 < count <= 2000 and all(len(recent[k]) == count for k in columns), 'review_profile_schema_invalid')
    annual = []
    for i in range(count):
        form = recent['form'][i]
        _need(isinstance(form, str), 'review_profile_schema_invalid')
        if form not in {'10-K', '10-K/A', '20-F', '20-F/A', '40-F', '40-F/A'}:
            continue
        row = {k: recent[k][i] for k in columns}
        end, filed = _iso_date(row['reportDate']), _iso_date(row['filingDate'])
        _need(end is not None and filed is not None and end <= filed <= now.date(),
              'review_annual_metadata_invalid')
        _need(isinstance(row['accessionNumber'], str) and re.fullmatch(r'\d{10}-\d{2}-\d{6}', row['accessionNumber'])
              and isinstance(row['primaryDocument'], str)
              and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,180}\.(?:htm|html|xhtml)', row['primaryDocument'])
              and '..' not in row['primaryDocument'], 'review_annual_metadata_invalid')
        if 'acceptanceDateTime' in row:
            accepted = _utc_timestamp(row['acceptanceDateTime'])
            _need(accepted is not None and end <= accepted.date() <= filed and accepted <= now,
                  'review_annual_metadata_invalid')
        annual.append(row)
    _need(bool(annual), 'review_current_annual_unavailable')
    latest_end = max(r['reportDate'] for r in annual)
    latest = [r for r in annual if r['reportDate'] == latest_end]
    latest_filed = max(r['filingDate'] for r in latest)
    latest = [r for r in latest if r['filingDate'] == latest_filed]
    if len(latest) > 1 and 'acceptanceDateTime' in columns:
        accepted = max(r['acceptanceDateTime'] for r in latest)
        latest = [r for r in latest if r['acceptanceDateTime'] == accepted]
    _need(len(latest) == 1, 'review_latest_annual_conflict')
    row = latest[0]
    _need((row['accessionNumber'], row['form'], row['filingDate'], row['reportDate'], row['primaryDocument']) ==
          (policy['accession'], policy['form'], policy['filed'], policy['period_end'], policy['primary_document']),
          'review_latest_annual_scope_unreviewed')
    _need(any(r['form'].endswith('/A') and r['filingDate'] >= policy['filed'] for r in annual) is False,
          'review_latest_annual_scope_unreviewed')
    return deepcopy(policy)


def _field_rows(receipt, policy, reason=None):
    payload = receipt.get('payload', {}) if isinstance(receipt, Mapping) else {}
    concepts = payload.get('facts', {}).get('us-gaap', {}) if isinstance(payload, Mapping) else {}
    output = []
    for field, concept, unit in FIELDS:
        row = dict(field=field, concept=concept, taxonomy='us-gaap', unit=unit,
            status='withheld', reason=reason or 'review_exact_annual_fact_missing', value=None,
            **{k: policy[k] for k in ('accession', 'form', 'filed', 'period_start', 'period_end')},
            source_ref=receipt.get('source_url') if isinstance(receipt, Mapping) else None,
            observed_at=receipt.get('observed_at') if isinstance(receipt, Mapping) else None,
            payload_sha256=receipt.get('payload_sha256') if isinstance(receipt, Mapping) else None)
        if reason is None:
            fact = concepts.get(concept) if isinstance(concepts, Mapping) else None
            units = fact.get('units') if isinstance(fact, Mapping) else None
            items = units.get(unit) if isinstance(units, Mapping) else None
            if not isinstance(items, list) or not 0 < len(items) <= 10000:
                row['reason'] = 'review_exact_unit_or_concept_missing'
            elif any(not isinstance(r, Mapping) for r in items):
                row['reason'] = 'review_fact_schema_invalid'
            else:
                def matches(r):
                    return all(r.get(k) == policy[p] for k, p in (
                        ('accn', 'accession'), ('form', 'form'), ('filed', 'filed'),
                        ('start', 'period_start'), ('end', 'period_end')))
                matches_unit = [r for r in items if matches(r)]
                other_units = [r for u, rs in units.items() if u != unit and isinstance(rs, list)
                               for r in rs if isinstance(r, Mapping) and matches(r)]
                if other_units:
                    row['reason'] = 'review_conflicting_annual_units'
                elif matches_unit:
                    values = [r.get('val') for r in matches_unit]
                    try:
                        finite = all(type(v) in {int, float} and math.isfinite(v) and abs(v) <= 1e20 for v in values)
                    except (OverflowError, ValueError):
                        finite = False
                    if not finite:
                        row['reason'] = 'review_fact_nonfinite_or_invalid'
                    elif len(set(values)) != 1:
                        row['reason'] = 'review_conflicting_annual_facts'
                    else:
                        row.update(status='available', reason=None, value=values[0])
        output.append(row)
    return output


def _business_proof(root, ticker):
    """Match this reviewed source's affirmative clause in plainly visible blocks."""
    html = 'http://www.w3.org/1999/xhtml'
    buffers = []
    supported = False

    def hidden(node):
        local = node.tag.rsplit('}', 1)[-1].lower()
        attrs = {k.lower(): v for k, v in node.attrib.items()}
        if (local in {'head', 'script', 'style', 'template'} or node.tag == f'{{{IX}}}hidden'
            or 'hidden' in attrs or attrs.get('aria-hidden', '').strip().lower() == 'true'):
            return True
        declarations = re.sub(r'\s+', '', attrs.get('style', '').lower()).split(';')
        return any(re.fullmatch(r'(?:display:none|visibility:hidden|opacity:(?:0+(?:\.0*)?|\.0+))(?:!important)?', declaration)
                   for declaration in declarations)

    def append(text):
        if text:
            for i, value in enumerate(buffers):
                if len(value) <= 16000:
                    buffers[i] = (value+text)[:16001]

    def affirmative(text):
        text = ' '.join(text.split()).lower()
        if len(text) > 8000:
            return False
        if ticker == 'MRVL':
            match = re.match(r'companies that compete directly with our businesses include\b.{0,800}?\bbroadcom\b', text)
            if match is None:
                return False
            clause = re.sub(r'\bbut are not limited to\b', '', match[0])
            return re.search(r'\b(?:not|no|never|neither|nor|except|excluding|exclude|excludes|without|other than)\b', clause) is None
        return re.match(r'we have two reportable segments:\s*semiconductor solutions and infrastructure software\b', text) is not None

    def visit(node, depth):
        nonlocal supported
        if supported or hidden(node):
            return
        _need(depth <= 256, 'review_document_visible_text_depth_exceeded')
        block = node.tag in {f'{{{html}}}p', f'{{{html}}}div'}
        if block:
            buffers.append('')
        append(node.text)
        for child in node:
            visit(child, depth+1)
            append(child.tail)
            if supported:
                break
        if block:
            supported = affirmative(buffers.pop()) or supported

    visit(root, 0)
    return supported


def _document(receipt, ticker, now):
    policy = POLICIES[ticker]
    _base_receipt(receipt, policy['source_url'], now)
    encoded = receipt.get('payload_raw_base64')
    _need(isinstance(encoded, str) and 0 < len(encoded) <= 4*((MAX_FILING_BYTES+2)//3),
          'review_document_raw_bytes_missing_or_oversized')
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error):
        raise _Hold('review_document_raw_bytes_invalid') from None
    _need(0 < len(raw) <= MAX_FILING_BYTES and hashlib.sha256(raw).hexdigest() == receipt['payload_sha256'],
          'review_document_raw_digest_changed')
    try:
        root, namespaces = _tree(raw)
    except (ValueError, TypeError, ET.ParseError):
        raise _Hold('review_document_xml_invalid') from None
    contexts = set()
    for context in root.iter(f'{{{X}}}context'):
        entity, period = context.find(f'{{{X}}}entity'), context.find(f'{{{X}}}period')
        if entity is None or period is None or len(context) != 2 or len(entity) != 1 or len(period) != 2:
            continue
        identifier = entity.find(f'{{{X}}}identifier')
        start, end = period.find(f'{{{X}}}startDate'), period.find(f'{{{X}}}endDate')
        if (isinstance(context.get('id'), str) and 0 < len(context.get('id')) <= 200
            and identifier is not None and identifier.get('scheme') == 'http://www.sec.gov/CIK'
            and isinstance(identifier.text, str) and re.fullmatch(r'\d{1,10}', identifier.text.strip())
            and str(int(identifier.text)).zfill(10) == policy['sec_cik']
            and start is not None and end is not None
            and start.text == policy['period_start'] and end.text == policy['period_end']):
            contexts.add(context.get('id'))
    metadata = {k: [] for k in ('EntityCentralIndexKey', 'DocumentType', 'DocumentPeriodEndDate')}
    for node in root.iter(f'{{{IX}}}nonNumeric'):
        uri, name = _qname(node.get('name'), namespaces)
        if not uri or not re.fullmatch(r'https?://xbrl.sec.gov/dei/\d{4}', uri) or name not in metadata:
            continue
        _need(node.get('contextRef') in contexts and node.get('continuedAt') is None
              and node.get('target') in {None, ''} and node.get(f'{{{XSI}}}nil') in {None, 'false', '0'},
              'review_document_metadata_unbound')
        metadata[name].append(node)
    ciks = {' '.join(''.join(n.itertext()).split()) for n in metadata['EntityCentralIndexKey']}
    forms = {' '.join(''.join(n.itertext()).split()) for n in metadata['DocumentType']}
    ends = {_date_fact(n, namespaces) for n in metadata['DocumentPeriodEndDate']}
    _need(ciks and all(re.fullmatch(r'\d{1,10}', v) and str(int(v)).zfill(10) == policy['sec_cik'] for v in ciks)
          and forms == {policy['form']} and ends == {_iso_date(policy['period_end'])},
          'review_document_metadata_mismatch')
    _need(_business_proof(root, ticker), 'review_business_relationship_evidence_missing')
    return deepcopy(policy)


def _empty(reason):
    return dict(status='withheld', reason=reason, ticker='MRVL', sec_cik=MRVL_CIK,
        rights_status=RIGHTS, commercial_eligible=False, readiness_promoted=False,
        quality=dict(status='withheld', reason=reason, filing=None,
            fields=_field_rows({}, MRVL, reason), flags=[], gaps=[reason]),
        peer_context=dict(status='withheld', reason=reason, subject_filing=None, peer_filing=None,
            relationship_supported=False, business_mix_difference=False, period_end_gap_days=None,
            fiscal_window_days=FISCAL_WINDOW_DAYS, numerical_admission='not_granted'), source_refs=[])


def build_mrvl_earnings_review(packet, *, expected_cik=None, as_of=None):
    """Revalidate every read; independent gaps cannot grant numeric peer admission."""
    try:
        mode = _mode_reason('research')
        _need(mode is None, mode or 'review_personal_research_required')
        now = _now(as_of)
        _need(isinstance(packet, Mapping) and packet.get('schema_version') == SCHEMA
              and packet.get('ticker') == 'MRVL' and packet.get('sec_cik') == MRVL_CIK
              and (expected_cik is None or expected_cik == MRVL_CIK), 'review_scope_unsupported')
        for receipt in packet.get('documents', {}).values():
            if isinstance(receipt, Mapping) and isinstance(receipt.get('payload_raw_base64'), str):
                _need(len(receipt['payload_raw_base64']) <= 4*((MAX_FILING_BYTES+2)//3), 'review_document_oversized')
        _need(packet.get('packet_digest') == _digest({k: v for k, v in packet.items() if k != 'packet_digest'}),
              'review_packet_changed')
        _fresh(packet.get('observed_at'), now)
        facts = packet.get('facts')
        body = _receipt_payload(facts, f'https://data.sec.gov/api/xbrl/companyfacts/CIK{MRVL_CIK}.json', now)
        _need(_cik(body.get('cik')) == MRVL_CIK, 'review_issuer_identity_mismatch')
        canonical_facts = normalize_review_facts(facts)
        _need(canonical_facts.get('status') == 'ready' and canonical_facts['payload'] == body,
              'review_facts_schema_invalid')
        profiles, documents = packet.get('profiles'), packet.get('documents')
        _need(isinstance(profiles, Mapping) and isinstance(documents, Mapping)
              and set(profiles) == {'MRVL', 'AVGO'} and set(documents) == {'MRVL', 'AVGO'},
              'review_packet_components_invalid')
    except _ERRORS as exc:
        return _empty(str(exc) if isinstance(exc, _Hold) else 'review_packet_invalid')
    result = _empty('review_evidence_unavailable')
    refs = [_source_ref(facts)]
    selected, source_gaps = {}, []
    for ticker in ('MRVL', 'AVGO'):
        try:
            selected[ticker] = _profile(profiles[ticker], ticker, now)
            refs.append(_source_ref(profiles[ticker]))
        except _ERRORS as exc:
            source_gaps.append(ticker.lower()+'_'+(str(exc) if isinstance(exc, _Hold) else 'review_profile_invalid'))
    quality = result['quality']
    mrvl_reason = None if 'MRVL' in selected else next(g for g in source_gaps if g.startswith('mrvl_'))
    quality['fields'] = _field_rows(facts, MRVL, mrvl_reason)
    available = {r['field']: r['value'] for r in quality['fields'] if r['status'] == 'available'}
    quality.update(status='inspection_only' if len(available) == 7 else 'partial' if available else 'withheld',
        reason=None if len(available) == 7 else 'review_annual_fields_incomplete', filing=selected.get('MRVL'))
    quality['gaps'] = [r['field']+'_'+r['reason'] for r in quality['fields'] if r['reason']]
    quality['gaps'] += ['adjusted_after_tax_reconciliation_unresolved', 'latest_quarter_outside_annual_review']
    quality['flags'] = []
    if available.get('gain_on_sale_of_business', 0) > 0:
        quality['flags'].append('disposal_gain_affects_reported_earnings')
    if {'net_income', 'cash_from_operations'} <= set(available) and available['net_income'] != available['cash_from_operations']:
        quality['flags'].append('operating_cash_flow_differs_from_net_income')
    for field, flag in (('share_based_compensation', 'share_based_compensation_requires_care'),
                        ('amortization_of_intangibles', 'amortization_requires_care')):
        if field in available and available[field] != 0:
            quality['flags'].append(flag)
    verified_docs = {}
    for ticker in ('MRVL', 'AVGO'):
        try:
            verified_docs[ticker] = _document(documents[ticker], ticker, now)
            refs.append(_source_ref(documents[ticker]))
        except _ERRORS as exc:
            source_gaps.append(ticker.lower()+'_'+(str(exc) if isinstance(exc, _Hold) else 'review_document_invalid'))
    peer = result['peer_context']
    peer.update(subject_filing=selected.get('MRVL'), peer_filing=selected.get('AVGO'))
    if len(selected) == 2 and len(verified_docs) == 2:
        gap = abs((_iso_date(selected['MRVL']['period_end'])-_iso_date(selected['AVGO']['period_end'])).days)
        peer.update(status='research_context', reason='peer_fiscal_window_differs' if gap > FISCAL_WINDOW_DAYS else 'numerical_peer_prerequisites_not_assessed',
            relationship_supported=True, business_mix_difference=True, period_end_gap_days=gap)
    else:
        peer['reason'] = source_gaps[0] if source_gaps else 'review_relationship_evidence_unavailable'
    quality['gaps'] += source_gaps
    supported = bool(available) or peer['status'] == 'research_context'
    result.update(status='inspection_only' if supported else 'withheld',
                  reason=None if supported else quality['reason'], source_refs=refs)
    return result


def validated_mrvl_review(financial_view, *, expected_cik=None, as_of=None):
    """Require the same issuer and original Companyfacts receipt as the loaded view."""
    try:
        _need(isinstance(financial_view, Mapping) and financial_view.get('ticker') == 'MRVL'
              and financial_view.get('sec_cik') == MRVL_CIK
              and (expected_cik is None or expected_cik == MRVL_CIK), 'review_financial_view_identity_mismatch')
        packet = financial_view.get('mrvl_earnings_review')
        _need(isinstance(packet, Mapping), 'review_not_requested')
        identity, facts = financial_view.get('companyfacts_identity'), packet.get('facts')
        _need(isinstance(identity, Mapping) and isinstance(facts, Mapping)
              and identity.get('status') == 'source_matched' and identity.get('ticker') == 'MRVL'
              and identity.get('sec_cik') == MRVL_CIK
              and all(identity.get(k) == facts.get(k) for k in ('source_url', 'observed_at', 'payload_sha256')),
              'review_companyfacts_receipt_mismatch')
        return build_mrvl_earnings_review(packet, expected_cik=expected_cik, as_of=as_of)
    except _ERRORS:
        return _empty('review_companyfacts_receipt_mismatch')
