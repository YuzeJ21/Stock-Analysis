from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256

import pytest

from test_online_peer_valuation import digest


NOW = datetime(2026, 11, 6, 15, tzinfo=timezone.utc)
CIK = '0001272842'
BODY = (b'<html><body><table><tr><td>Diluted net loss per share</td><td>'
        b'<ix:nonfraction id="reviewed" name="us-gaap:EarningsPerShareDiluted" '
        b'contextref="annual" unitref="dollarsPerShare" decimals="2" sign="-">0.54</ix:nonfraction>'
        b'</td></tr></table></body></html>')


@pytest.fixture
def audit(monkeypatch):
    from src import online_peer_annual_audit as audit

    monkeypatch.delenv('COMMERCIAL_RESEARCH_MODE', raising=False)
    scope = audit._SCOPES['AIRG', CIK]
    reviewed = replace(scope, fact_id='reviewed', body_sha256=sha256(BODY).hexdigest())
    monkeypatch.setitem(audit._SCOPES, ('AIRG', CIK), replace(
        reviewed, reviewed_fact_sha256=audit._reviewed_value_digest(reviewed, -0.54)))
    return audit


def profile(amended=False):
    rows = [dict(form='10-K', reportDate='2025-12-31', filingDate='2026-02-26',
                 acceptanceDateTime='2026-02-26T21:05:30Z', accessionNumber='0001193125-26-076752',
                 primaryDocument='airg-20251231.htm', isInlineXBRL=1, isXBRL=1)]
    if amended:
        rows.append(dict(rows[0], form='10-K/A', filingDate='2026-03-01', acceptanceDateTime='2026-03-01T21:00:00Z',
                         accessionNumber='0001193125-26-076753'))
    body = dict(cik=CIK, tickers=['AIRG'], filings={'recent': {key: [r[key] for r in rows] for key in rows[0]}})
    return dict(status='ready', source_url=f'https://data.sec.gov/submissions/CIK{CIK}.json',
                observed_at=NOW.isoformat(), payload_sha256=digest(body), normalized_sha256=digest(body), payload=body)


def test_reviewed_direct_loss_requires_matching_companyfacts(audit):
    current = profile()
    fetch = lambda url, agent: (BODY, {}, url)
    receipt = audit.fetch_annual_eps_audit('AIRG', CIK, current, user_agent='Synthetic contact',
                                           fetcher=fetch, observed_at=NOW)
    assert receipt['status'] == 'observed'
    assert 'payload_raw_base64' not in receipt and 'Diluted net loss per share' not in str(receipt)
    facts = dict(accession='0001193125-26-076752', form='10-K', filed='2026-02-26',
                 period_start='2025-01-01', period_end='2025-12-31', eps=-0.54)
    verified = audit.annual_eps_audit_result(receipt, ticker='AIRG', cik=CIK, profile=current, eps=facts, as_of=NOW)
    assert verified['reason'] == 'annual_eps_confirmed_loss'
    assert verified['source_url'].endswith('airg-20251231.htm#reviewed')
    conflict = audit.annual_eps_audit_result(receipt, ticker='AIRG', cik=CIK, profile=current,
                                            eps=dict(facts, eps=0.54), as_of=NOW)
    assert conflict['reason'] == 'annual_eps_exact_filing_conflict'
    assert audit.annual_eps_audit_result(receipt, ticker='AIRG', cik=CIK, profile=current,
                                         eps=None, as_of=NOW)['reason'] == 'annual_eps_companyfacts_not_matched'


def test_unreviewed_amendment_cannot_reuse_original_loss(audit):
    def forbidden(*args):
        pytest.fail('An unreviewed amendment cannot reuse the original filing.')

    receipt = audit.fetch_annual_eps_audit('AIRG', CIK, profile(amended=True), user_agent='Synthetic contact',
                                           fetcher=forbidden, observed_at=NOW)
    assert receipt == {'status': 'withheld', 'reason': 'annual_eps_filing_version_unreviewed'}


def test_changed_filing_bytes_cannot_create_verified_loss(audit):
    receipt = audit.fetch_annual_eps_audit('AIRG', CIK, profile(), user_agent='Synthetic contact',
                                           fetcher=lambda url, agent: (BODY.replace(b'0.54', b'0.52'), {}, url),
                                           observed_at=NOW)
    assert receipt == {'status': 'withheld', 'reason': 'annual_eps_exact_filing_unverified'}


def test_zero_eps_is_distinct_from_loss_and_a_stale_receipt(audit, monkeypatch):
    from datetime import timedelta

    zero_body = BODY.replace(b' sign="-"', b'').replace(b'0.54', b'0.00')
    scope = audit._SCOPES['AIRG', CIK]
    monkeypatch.setitem(audit._SCOPES, ('AIRG', CIK), replace(
        scope, body_sha256=sha256(zero_body).hexdigest(), reviewed_fact_sha256=audit._reviewed_value_digest(scope, 0.0)))
    current = profile()
    receipt = audit.fetch_annual_eps_audit('AIRG', CIK, current, user_agent='Synthetic contact',
                                           fetcher=lambda url, agent: (zero_body, {}, url), observed_at=NOW)
    facts = dict(accession='0001193125-26-076752', form='10-K', filed='2026-02-26',
                 period_start='2025-01-01', period_end='2025-12-31', eps=0.0)
    result = audit.annual_eps_audit_result(receipt, ticker='AIRG', cik=CIK, profile=current, eps=facts, as_of=NOW)
    assert result['reason'] == 'annual_eps_confirmed_zero'
    stale = audit.annual_eps_audit_result(receipt, ticker='AIRG', cik=CIK, profile=current,
                                          eps=facts, as_of=NOW + timedelta(days=2))
    assert 'source_url' not in stale
