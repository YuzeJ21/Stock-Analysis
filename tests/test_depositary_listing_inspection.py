"""Constructed SEC and directory receipts for the inspection-only ADS path."""
from hashlib import sha256
import json

import pytest

from test_online_peer_sources import get
from test_online_peer_valuation import NOW, sec_receipt
from test_online_us_universe import E_URL, M_URL, N_URL, O_URL

CIK = '0001000184'
NOTE = 'Synthetic NYSE SAP ADS represents one ordinary share.'
BODY = f'<html xmlns="http://www.w3.org/1999/xhtml"><body><p>{NOTE}</p></body></html>'.encode()


def dependencies(monkeypatch, *, title='Synthetic SAP SE ADS', exchange='NYSE', conflict=False):
    from src import sec_selected_security
    from src.security_classification import fetch_classification

    meta = dict(form='20-F', reportDate='2025-12-31', filingDate='2026-02-26',
                acceptanceDateTime='2026-02-26T12:01:22Z', accessionNumber='0001104659-26-020058',
                primaryDocument='annual.htm', isInlineXBRL=1, isXBRL=1)
    policy = dict(policy_id='synthetic-sap-ads', ticker='SAP', sec_cik=CIK, issuer_symbols=['SAP', 'SAPGF'],
                  kind='inspection_only', reason='depositary_security_requires_separate_method',
                  depositary_directory_title='Synthetic SAP SE ADS', documents={'annual': dict(metadata=meta,
                      sha256=sha256(BODY).hexdigest(), inspection_observations=[dict(kind='element_note',
                          label='NYSE ADS listing and one ordinary share per ADS', path='/html[1]/body[1]/p[1]',
                          text_sha256=sha256(NOTE.encode()).hexdigest())])})
    monkeypatch.setattr(sec_selected_security, 'POLICIES', (policy,))
    objects = {
        N_URL: ('Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot Size|ETF|NextShares\n'
                'ZZZZ|Synthetic ZZZZ Common Stock|Q|N|N|100|N|N\nFile Creation Time: 1030202615:41|||||||\n').encode(),
        O_URL: ('ACT Symbol|Security Name|Exchange|CQS Symbol|ETF|Round Lot Size|Test Issue|NASDAQ Symbol\n'
                f'SAP|{title}|N|SAP|N|100|N|SAP\nFile Creation Time: 1030202615:41|||||||\n').encode(),
        M_URL: json.dumps({str(i): dict(ticker=t, cik_str=int(CIK) if t != 'SAP' or not conflict else 1111,
                                       title='Synthetic SAP SE') for i, t in enumerate(('SAP', 'SAPGF'))}).encode(),
        E_URL: json.dumps(dict(fields=['cik', 'name', 'ticker', 'exchange'],
            data=[[1111 if conflict else int(CIK), 'Synthetic SAP SE', 'SAP', 'NYSE'],
                  [int(CIK), 'Synthetic SAP SE', 'SAPGF', 'OTC']])).encode(),
    }
    profile = sec_receipt(CIK, 'profile', dict(cik=int(CIK), tickers=['SAP', 'SAPGF'], exchanges=[exchange, 'OTC'],
        entityType='operating', sic='7372', filings={'recent': {k: [v] for k, v in meta.items()}}))
    calls = []

    def classify(**kwargs):
        return fetch_classification(fetcher=lambda url, agent: (objects[url], {}, url), **kwargs)

    def sec(url, **kwargs):
        calls.append(url)
        assert url == profile['source_url']
        return profile

    def security(*args, **kwargs):
        def fetch(url, agent):
            calls.append(url)
            return BODY, {}, url
        return sec_selected_security.fetch_selected_security_evidence(*args, fetcher=fetch, **kwargs)

    def forbidden(*args, **kwargs):
        pytest.fail('Deposit-only inspection requested valuation-provider data')

    return dict(classification=classify, sec=sec, security=security,
                vendor=forbidden, prices=forbidden, industry=forbidden, history=forbidden), calls


def test_exact_ads_listing_has_evidence_and_no_valuation(monkeypatch):
    deps, calls = dependencies(monkeypatch)
    state = {}
    result = get(state, refresh=True, dependencies=deps, ticker='SAP', expected_cik=CIK)
    assert result['reason'] == 'depositary_security_requires_separate_method'
    context = result['subject_source_context']
    listing = context['selected_depositary_listing']
    assert (context['sec_cik'], listing['ticker'], listing['security_type'], listing['venue']) == (
        CIK, 'SAP', 'depositary_receipt', 'NYSE')
    assert listing['source_url'] == O_URL
    scope = context['selected_security_scope']
    assert scope['status'] == 'inspection_only' and scope['unassigned_issuer_symbols'] == ['SAPGF']
    assert scope['evidence_observations'][0]['financial_eligible'] is False
    assert result['subject'] is None and result['peer_count'] == 0 and result['premium_fraction'] is None
    assert len(calls) == 2
    assert get(state, dependencies=deps, ticker='SAP', expected_cik=CIK) == result
    assert len(calls) == 2


@pytest.mark.parametrize('change', ['common', 'preferred', 'different_ads', 'wrong_cik', 'wrong_exchange'])
def test_wrong_security_or_issuer_cannot_reuse_ads_proof(monkeypatch, change):
    options = {'common': dict(title='Synthetic SAP Ordinary Shares'),
               'preferred': dict(title='Synthetic SAP Preferred Stock'),
               'different_ads': dict(title='Synthetic SAP Preferred Shares ADS'),
               'wrong_cik': dict(conflict=True), 'wrong_exchange': dict(exchange='Nasdaq')}
    deps, calls = dependencies(monkeypatch, **options[change])
    result = get({}, refresh=True, dependencies=deps, ticker='SAP', expected_cik=CIK)
    assert result['status'] == 'withheld' and result['subject'] is None
    assert result['reason'] != 'depositary_security_requires_separate_method'
    assert not result.get('subject_source_context', {}).get('selected_depositary_listing')
    assert len(calls) <= 1
