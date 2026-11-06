"""Exact reviewed annual diluted EPS observations for seven QCOM candidates."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256

from src.company_sec_online_preview import _utc_timestamp
from src.online_company_identity import _mode_reason
from src.sec_exact_filing import MAX_FILING_BYTES, RIGHTS, _digest, _fetch_html, _reference_valid, select_sec_filing
from src.sec_listing_cover import FilingCase, document_receipt
from src.sec_selected_security import _bound_body, _fresh, valid_profile_metadata_shape

_SCHEMA = 'peer-annual-eps-audit-v1'
QCOM_ANNUAL_AUDIT_BASIS = 'qcom-reviewed-annual-eps-v1'
_UNIT = 'USD/shares'
_CONCEPT = 'EarningsPerShareDiluted'


@dataclass(frozen=True)
class _AuditScope:
    case: FilingCase
    period_start: str
    period_end: str
    fact_id: str
    body_sha256: str
    reviewed_fact_sha256: str


# The reviewed fact digest binds the literal annual statement value, not a derived amount.
# It binds accession, actual duration, inline anchor, unit, concept and numeric value.
_SCOPES = {
    ('AIRG', '0001272842'): _AuditScope(
        FilingCase('AIRG', '0001272842', '0001193125-26-076752', 'airg-20251231.htm', '10-K'),
        '2025-01-01', '2025-12-31', 'F_527a0f43-6da8-463a-ba07-fd1fabfea911',
        'fda46da7edd7636fab84440a027600645d8f5c7ceca52e5b427fd0fd77f488bc',
        'a9ad091bed881f98479221578103efd1f95ec7a53c0fa5932c16ddaa5a80022b',
    ),
    ('CMTL', '0000023197'): _AuditScope(
        FilingCase('CMTL', '0000023197', '0000023197-26-000114', 'cmtl-20260731.htm', '10-K'),
        '2025-08-01', '2026-07-31', 'f-227',
        '05e4866144ed78f7c81a228f722e35d9a666256e70e2b998b6b1b49ef755c47b',
        'f5f6fec690e085b2b46b8f5b88894f486d4a7a9a63ad38079b2dbdfee5851a13',
    ),
    ('HLIT', '0000851310'): _AuditScope(
        FilingCase('HLIT', '0000851310', '0001193125-26-067506', 'hlit-20251231.htm', '10-K'),
        '2025-01-01', '2025-12-31', 'F_0692f075-a83d-4ec8-b58d-c776d59f2516',
        '5063f68eb6737c9bebee7188ed77bcd91a4d67abe2bf4b6acb0c5416d0bfb6a3',
        'a7b2604a09bca7279a4a5df2c8a11b828a0ecb8716dc5c112f8a537cdfaa0e44',
    ),
    ('ONDS', '0001646188'): _AuditScope(
        FilingCase('ONDS', '0001646188', '0001213900-26-035981', 'ea0282911-10k_ondas.htm', '10-K'),
        '2025-01-01', '2025-12-31', 'ixv-18596',
        '5a3bd41266aab6a2b6e29b7129117f04e45ea7f1f419a0ec68c3a40ec8dbad13',
        'e21a724daeb6148b946eac2fcfd03e52cdbd4f8fa5dc519508b8a02bf81c6171',
    ),
    ('UMAC', '0001956955'): _AuditScope(
        FilingCase('UMAC', '0001956955', '0001683168-26-001730', 'umac_i10k-123125.htm', '10-K'),
        '2025-01-01', '2025-12-31', 'Fact000267',
        'e0c707c9ccfa647be50997ab8cc393415f9e10689589b9bdea015022b89fc963',
        '24bf1be829aaa69070a485eb053ed302139346c56bba07615c335c19243695f8',
    ),
    ('VUZI', '0001463972'): _AuditScope(
        FilingCase('VUZI', '0001463972', '0001104659-26-027163', 'vuzi-20251231x10k.htm', '10-K'),
        '2025-01-01', '2025-12-31', 'Tc_m664vb21dEu_1aw1ZHG-Yw_50_2_2',
        'd48ff47fd3a13437dad971c4cf13c468c1aa5558155b0d4418ac54c06b099a3c',
        'b06a1473f4147fcc5f5e8705fb1f3e1fa3c5b30620779d09f332a3765241dc64',
    ),
    ('WATT', '0001575793'): _AuditScope(
        FilingCase('WATT', '0001575793', '0001104659-26-035214', 'watt-20251231x10k.htm', '10-K'),
        '2025-01-01', '2025-12-31', 'Tc_EfcKFiM7IESUZ-XQoxvIDQ_22_3_2',
        '3d2a8a8b0b16bb6fc258264395cda4a5d89fa1c47a28dcb172f2c459f9c9968e',
        '11480c04ce890e5ce144c10206b588aa123e7b5fd6d865d26ac8c0e45ff5a036',
    ),
}


def known_annual_audit_scope(ticker, cik):
    return (ticker, cik) in _SCOPES


def _reviewed_selection(scope, profile, now):
    case = scope.case
    if (not _reference_valid(profile, case.metadata_url) or not _fresh(profile['observed_at'], now)
        or profile.get('status') != 'ready' or not isinstance(profile.get('payload'), Mapping)):
        return None
    body = profile['payload']
    recent = body.get('filings', {}).get('recent')
    if (body.get('tickers') != [case.symbol]
        or not valid_profile_metadata_shape(recent, max_rows=2000)
        or 'normalized_sha256' in profile and profile['normalized_sha256'] != _digest(body)):
        return None
    selected = select_sec_filing(case.symbol, case.cik, profile, period_kind='annual')
    if (selected.get('status') != 'selected' or selected['source_url'] != case.source_url
        or selected['form'] != case.form or selected['period_end'] != scope.period_end):
        return None
    if any(form == '10-K/A' and period == scope.period_end for form, period in zip(recent['form'], recent['reportDate'])):
        return None
    return selected


def _reviewed_value_digest(scope, value):
    return _digest((scope.case.accession, scope.period_start, scope.period_end, scope.fact_id, _UNIT, _CONCEPT, float(value)))


def fetch_annual_eps_audit(ticker, cik, profile, *, user_agent, fetcher=None, observed_at=None, workspace_mode='research'):
    if reason := _mode_reason(workspace_mode):
        return dict(status='unavailable', reason=reason)
    scope = _SCOPES.get((ticker, cik))
    if scope is None:
        return dict(status='not_applicable')
    try:
        now = observed_at if observed_at is not None else datetime.now(timezone.utc)
        if not isinstance(now, datetime) or now.utcoffset() is None:
            return dict(status='withheld', reason='annual_eps_exact_filing_unverified')
        now = now.astimezone(timezone.utc)
        if _reviewed_selection(scope, profile, now) is None:
            return dict(status='withheld', reason='annual_eps_filing_version_unreviewed')
        if not isinstance(user_agent, str) or not user_agent.strip() or any(c in user_agent for c in '\r\n'):
            return dict(status='unavailable', reason='annual_eps_exact_filing_unavailable')
        url = scope.case.source_url
        raw, _, final = (fetcher or _fetch_html)(url, user_agent.strip())
        doc = document_receipt(raw, final, scope.case, now, max_bytes=MAX_FILING_BYTES)
        if doc is None or sha256(_bound_body(raw, 'sec-empty-tail-script-v1')).hexdigest() != scope.body_sha256:
            return dict(status='withheld', reason='annual_eps_exact_filing_unverified')
        packet = dict(schema_version=_SCHEMA, status='observed', ticker=ticker, sec_cik=cik,
                      profile_sha256=profile['payload_sha256'],
                      document=dict(doc, source_url=url, body_sha256=scope.body_sha256))
        return dict(packet, packet_digest=_digest(packet))
    except (OSError, RuntimeError):
        return dict(status='unavailable', reason='annual_eps_exact_filing_unavailable')
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError):
        return dict(status='withheld', reason='annual_eps_exact_filing_unverified')


def annual_eps_audit_result(packet, *, ticker, cik, profile, eps, as_of):
    """Bind the exact filing receipt to the existing same-accession Companyfacts observation."""
    held = dict(reason='annual_eps_exact_filing_unverified')
    scope = _SCOPES.get((ticker, cik))
    if _mode_reason('research') or scope is None:
        return held
    try:
        selected = _reviewed_selection(scope, profile, as_of)
        if selected is None:
            return dict(reason='annual_eps_filing_version_unreviewed')
        if not isinstance(packet, Mapping):
            return held
        if packet.get('status') == 'unavailable':
            return dict(reason='annual_eps_exact_filing_unavailable')
        if (packet.get('schema_version') != _SCHEMA or packet.get('status') != 'observed'
            or (packet.get('ticker'), packet.get('sec_cik')) != (ticker, cik)
            or packet.get('profile_sha256') != profile['payload_sha256']
            or packet.get('packet_digest') != _digest({key: val for key, val in packet.items() if key != 'packet_digest'})):
            return held
        doc = packet['document']
        if (not _reference_valid(doc, scope.case.source_url) or not _fresh(doc['observed_at'], as_of)
            or _utc_timestamp(doc['observed_at']) < _utc_timestamp(selected['accepted_at'])
            or doc.get('body_sha256') != scope.body_sha256):
            return held
        evidence = dict(source_url=f"{doc['source_url']}#{scope.fact_id}", observed_at=doc['observed_at'],
                        payload_sha256=doc['payload_sha256'], body_sha256=scope.body_sha256,
                        accession=selected['accession'], form=selected['form'], filed=selected['filed'],
                        period_start=scope.period_start, period_end=scope.period_end,
                        concept=_CONCEPT, unit=_UNIT, rights_status=RIGHTS)
        if eps is None:
            return dict(evidence, reason='annual_eps_companyfacts_not_matched')
        value = eps['eps']
        if (not all(eps.get(key) == evidence[key] for key in ('accession', 'form', 'filed', 'period_start', 'period_end'))
            or type(value) not in {int, float} or _reviewed_value_digest(scope, value) != scope.reviewed_fact_sha256):
            return dict(evidence, reason='annual_eps_exact_filing_conflict')
        if value < 0:
            return dict(evidence, reason='annual_eps_confirmed_loss')
        if value == 0:
            return dict(evidence, reason='annual_eps_confirmed_zero')
        return dict(evidence, reason='annual_eps_confirmed_positive')
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError, RecursionError):
        return held
