from copy import deepcopy
from datetime import timedelta
import json

import pytest

from test_sec_exact_filing import MAP, _submission
from test_sec_inline_filing import OBSERVED


TICKER = 'NEE'
CIK = '0000753308'
FACTS = f'https://data.sec.gov/api/xbrl/companyfacts/CIK{CIK}.json'
SUB = f'https://data.sec.gov/submissions/CIK{CIK}.json'
SCOPE = dict(profile_key='personal/demo', ticker=TICKER, sec_cik=CIK)


def online_nee(*, structured=False, calls=None, observed_at=OBSERVED):
    from src.sec_annual_history import fetch_sec_online_research_view
    from test_sec_inline_nee_capital_purchase import nee_filing

    raw, selection, _ = nee_filing()
    profile = _submission()
    profile.update(cik=int(CIK), name='Constructed NextEra Energy', tickers=[TICKER], sic='4911',
                   fiscalYearEnd='1231', entityType='operating')
    profile['filings']['recent'].update(
        accessionNumber=[selection['accession']], reportDate=[selection['period_end']], filingDate=[selection['filed']],
        acceptanceDateTime=[selection['accepted_at']], primaryDocument=[selection['primary_document']],
    )
    fact = dict(start='2026-07-01', end='2026-09-30', filed=selection['filed'], form='10-Q',
                accn=selection['accession'], val=9_876_000_000)
    facts = {'RegulatedAndUnregulatedOperatingRevenue': {'units': {'USD': [fact]}}} if structured else {}
    catalog = {MAP: {'0': {'ticker': TICKER, 'cik_str': int(CIK)}}, SUB: profile,
               FACTS: {'cik': int(CIK), 'entityName': 'Constructed NextEra Energy', 'facts': {'us-gaap': facts}},
               selection['source_url']: raw}

    def fetch(url, _agent):
        if calls is not None:
            calls.append(url)
        body = catalog[url]
        return (body if isinstance(body, bytes) else json.dumps(body).encode()), {}, url

    return fetch_sec_online_research_view(TICKER, user_agent='Constructed research contact',
                                         source_fetcher=fetch, observed_at=observed_at)


def _context(financial, as_of=OBSERVED):
    from src.online_research_tools import build_online_research_context

    return build_online_research_context(financial, {}, ticker=TICKER, expected_cik=CIK,
                                         profile_key=SCOPE['profile_key'], as_of=as_of)


@pytest.mark.parametrize('structured', [False, True])
def test_nee_supplement_uses_one_exact_source_and_never_promotes_generic_capex(structured):
    from src.sec_online_quarter_evidence import validated_archive_quarter

    calls = []
    financial = online_nee(structured=structured, calls=calls)
    archive = validated_archive_quarter(financial, ticker=TICKER, expected_cik=CIK, as_of=OBSERVED)
    assert calls == [MAP, FACTS, SUB, archive['source_url']]
    evidence = archive['capital_purchase_evidence']
    assert evidence['period_kind'] == 'cumulative' and evidence['period_start'] == '2026-01-01'
    assert evidence['period_end'] == '2026-09-30' and evidence['source_url'] == calls[-1]
    assert evidence['capital_expenditures_equivalent'] is evidence['cash_generation_eligible'] is False
    assert evidence['commercial_eligible'] is evidence['saved_readiness_promoted'] is False
    assert len(evidence['fields']) == 5
    assert all(field['reported_numeric_schema'] == 'sec-nee-capital-purchase-number-v1' for field in evidence['fields'].values())
    assert all('capital_expenditures' not in row['fields'] for row in archive['periods'])
    assert '"raw_text"' not in json.dumps(evidence)
    context = _context(financial)
    if structured:
        row = next(row for row in context['business_trend']['periods'] if row['period_end'] == '2026-09-30')
        assert row['fields']['revenue']['source_ref'] == FACTS
    metrics = [metric for metric in context['business_trend']['metrics'] if metric['key'] == 'cfo_less_ppe']
    assert metrics and all(metric['status'] == 'withheld' for metric in metrics)


def test_nee_supplement_saved_replay_validates_and_refresh_is_metadata_only(tmp_path):
    from src.online_research_context_store import compare_research_contexts, load_research_context, save_research_context

    current = _context(online_nee())
    assert current['business_trend']['capital_purchase_evidence']['fields']
    saved = save_research_context(current, project_root=tmp_path, **SCOPE)
    reopened = load_research_context(saved['snapshot_id'], project_root=tmp_path, **SCOPE)
    assert reopened == saved and compare_research_contexts(saved, reopened)['status'] == 'unchanged'
    later = OBSERVED + timedelta(minutes=1)
    refreshed = _context(online_nee(observed_at=later), as_of=later)
    assert compare_research_contexts(current, refreshed)['status'] == 'source_metadata_only'


@pytest.mark.parametrize('problem', ['numeric', 'source', 'eligibility'])
def test_resealed_nee_supplement_fails_replay_without_removing_standard_evidence(tmp_path, problem):
    from src.online_filing_context import _digest
    from src.online_research_context_store import save_research_context
    from src.sec_online_quarter_evidence import validated_archive_quarter

    financial = online_nee()
    context = _context(financial)
    packet = context['business_trend']['capital_purchase_evidence']
    field = packet['fields']['reported_capital_investment_total']
    if problem == 'numeric':
        field['value'] += 1
    elif problem == 'source':
        field['source_ref'] += '?wrong=1'
    else:
        packet['cash_generation_eligible'] = True
    packet['packet_digest'] = _digest({key: value for key, value in packet.items() if key != 'packet_digest'})
    with pytest.raises(ValueError, match='capital[- ]purchase'):
        save_research_context(context, project_root=tmp_path, **SCOPE)
    assert not list(tmp_path.iterdir())
    invalid = deepcopy(financial)
    wrapper = invalid['archive_quarterly']
    source = wrapper['source_packet']
    source['capital_purchase_evidence']['cash_generation_eligible'] = True
    source['packet_digest'] = _digest({key: value for key, value in source.items() if key != 'packet_digest'})
    wrapper['source_packet_digest'] = source['packet_digest']
    wrapper['packet_digest'] = _digest({key: value for key, value in wrapper.items() if key != 'packet_digest'})
    archive = validated_archive_quarter(invalid, as_of=OBSERVED)
    assert archive['periods'] and 'capital_purchase_evidence' not in archive
