"""Non-XBRL bank evidence reaches self-service Workbench without Companyfacts or CSVs."""
from copy import deepcopy
from datetime import timedelta
import json
from urllib.error import HTTPError

import pytest

from src.company_answer_summary import build_company_answers
from src.company_workbench_sections import workbench_projection
from src.online_research_context_store import compare_research_contexts, load_research_context, save_research_context
from src.online_research_tools import build_online_research_context
from src.sec_annual_history import fetch_sec_online_research_view
from test_sec_exact_filing import _submission
from test_sec_html_bank import URL, html
from test_sec_inline_filing import OBSERVED


SCOPE = dict(profile_key='personal/demo', ticker='IBN', sec_cik='0001103838')


def _financial(calls=None, *, as_of=OBSERVED):
    body = _submission()
    body.update(cik=1103838, tickers=['IBN'], name='ICICI BANK LIMITED', entityType='operating',
                sic='6029', fiscalYearEnd='0331')
    body['filings']['recent'].update(form=['20-F'], reportDate=['2026-03-31'], isInlineXBRL=[0], isXBRL=[0])

    def fetch(url, _agent):
        if calls is not None:
            calls.append(url)
        if url.endswith('company_tickers.json'):
            payload = json.dumps({'0': {'ticker': 'IBN', 'cik_str': 1103838}}).encode()
        elif url.endswith('/submissions/CIK0001103838.json'):
            payload = json.dumps(body).encode()
        elif url == URL:
            payload = html().encode()
        else:
            raise HTTPError(url, 404, 'Unavailable', {}, None)
        return payload, {}, url

    return fetch_sec_online_research_view('IBN', user_agent='Constructed research contact',
                                         source_fetcher=fetch, observed_at=as_of)


def _context(financial, *, cik=SCOPE['sec_cik'], as_of=OBSERVED):
    return build_online_research_context(financial, {}, ticker='IBN', profile_key=SCOPE['profile_key'],
                                         expected_cik=cik, as_of=as_of)


def test_bank_financials_have_their_own_coverage_and_replay(tmp_path):
    calls = []
    financial = _financial(calls)
    original = deepcopy(financial)
    assert calls.count(URL) == 1
    assert financial.get('companyfacts_identity', {}).get('status') != 'source_matched'
    context = _context(financial)
    coverage = context['filing_coverage']
    assert coverage['current']['annual']['reason'] == 'exact_ibn_annual_table_and_filing'
    assert coverage['structured_annual']['status'] != 'corroborated'
    assert coverage['current']['quarterly']['status'] == coverage['current']['interim']['status'] == 'withheld'
    bank = context['business_trend']['bank_annual']
    assert bank['accounting_basis'] == 'Indian GAAP' and bank['unit'] == 'INR'
    assert len(bank['periods']) == 3 and bank['periods'][0]['fields']['total_income']['value'] == 120000
    assert bank['periods'][0]['fields']['fixed_asset_purchases']['value'] == -4000
    assert 'revenue' in bank['withheld_fields'] and 'revenue' not in bank['periods'][0]['fields']
    assert context['scenario_base']['status'] == 'excluded' and context['scenario_base']['revenue'] is None
    assert context['status'] == 'inspection_only' and context['peer_read_through']['status'] != 'research_comparison'
    projection = workbench_projection('IBN', financial, {}, expected_cik=SCOPE['sec_cik'], as_of=OBSERVED)
    answer = next(card for card in build_company_answers('IBN', projection, financial, {}, {}, {})
                  if card['key'] == 'financial')
    assert projection['annual_count'] == 3 and projection['quarter_count'] == 0
    assert 'Profit attributable to the Group' in answer['headline'] and '7.1%' in answer['headline']
    assert ('Exact SEC annual filing', URL) in answer['links']
    first = save_research_context(context, project_root=tmp_path, **SCOPE)
    reopened = load_research_context(first['snapshot_id'], project_root=tmp_path, **SCOPE)
    assert first == reopened and compare_research_contexts(first, reopened)['status'] == 'unchanged'
    assert financial == original and calls.count(URL) == 1
    assert not (tmp_path / 'data').exists()


def test_bank_evidence_stays_within_expected_issuer_scope():
    financial = _financial()
    wrong = '0000001234'
    projection = workbench_projection('IBN', financial, {}, expected_cik=wrong, as_of=OBSERVED)
    assert projection['identity_conflict'] and projection['bank_annual'] is None
    assert not _context(financial, cik=wrong)['business_trend'].get('bank_annual')


def test_identical_bank_filing_refreshed_later_is_metadata_only():
    first = _context(_financial())
    later = OBSERVED + timedelta(minutes=1)
    second = _context(_financial(as_of=later), as_of=later)
    compared = compare_research_contexts(first, second)
    assert compared['status'] == 'source_metadata_only'
    assert compared['source_metadata_changed'] and not compared['financial_changed']


@pytest.mark.parametrize('change', ['amount', 'scope', 'strip_proof'])
def test_snapshot_rechecks_bank_fields(tmp_path, change):
    context = _context(_financial())
    field = context['business_trend']['bank_annual']['periods'][0]['fields']['total_income']
    if change == 'amount':
        field['value'] += 1
    elif change == 'scope':
        field['source_ref'] = field['source_ref'].replace('1103838', '999')
    else:
        del field['reported_numeric_schema']
        del field['reported_text']
    with pytest.raises(ValueError, match='bank evidence'):
        save_research_context(context, project_root=tmp_path, **SCOPE)
    assert not list(tmp_path.iterdir())
