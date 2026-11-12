from copy import deepcopy
from datetime import timedelta

import pytest

from src.company_answer_summary import build_company_answers
from src.company_workbench_sections import workbench_projection
from src.online_filing_context import _digest
from src.online_research_context_store import compare_research_contexts, load_research_context, save_research_context
from src.sec_exact_filing_view import bank_quarter_comparison_html
from src.sec_ibn_quarter_comparison import compare_ibn_quarters
from test_ibn_workbench import SCOPE, _context
from test_sec_online_ibn_interim_evidence import OBSERVED, comparison_sources, online


def test_independent_quarter_pair_survives_exact_snapshot_replay(tmp_path):
    financial = online(comparison_sources()[0])
    context = _context(financial, as_of=OBSERVED)
    trend = context['business_trend']
    prior = trend['bank_interim_comparison']['baseline']
    current = trend['bank_interim']
    assert prior['period_end'] == '2026-06-30' and current['period_end'] == '2026-09-30'
    assert prior['accession'] != current['accession']
    assert len(prior['periods']) == 1
    assert all('cash_from_operations' not in packet['periods'][0]['fields'] for packet in (prior, current))
    assert 'cash_from_operations' in current['periods'][1]['fields']
    assert context['filing_inventory']['review_triggers'] and 'review_triggers' not in context['forward_view']
    changes = compare_ibn_quarters(current, trend['bank_interim_comparison'])
    assert changes['status'] == 'changed' and len(changes['fields']) == 5
    assert 'cash_from_operations' not in changes['fields']
    saved = save_research_context(context, project_root=tmp_path, **SCOPE)
    reopened = load_research_context(saved['snapshot_id'], project_root=tmp_path, **SCOPE)
    assert reopened == saved and compare_research_contexts(saved, reopened)['status'] == 'unchanged'


def test_workbench_comparison_exposes_both_primary_filings_but_no_cumulative_amounts():
    values, september, _, june = comparison_sources()
    financial = online(values)
    projection = workbench_projection('IBN', financial, {}, expected_cik=SCOPE['sec_cik'], as_of=OBSERVED)
    current, pair = projection['bank_interim'], projection['bank_interim_comparison']
    html = bank_quarter_comparison_html(current, pair)
    assert '2026-06-30 → 2026-09-30 · changed' in html and june in html and september in html
    assert 'Quarterly cash flow stays withheld' in html and '35,000,000' not in html
    summary = next(card for card in build_company_answers('IBN', projection, financial, {}, {}, {}) if card['key'] == 'financial')
    assert summary['headline'].startswith('Quarterly net profit ')
    assert ('Prior quarter SEC 6-K', june) in summary['links']


def test_interim_pair_rejects_resealed_cash_and_transport_only_refresh(tmp_path):
    values = comparison_sources()[0]
    first = _context(online(values), as_of=OBSERVED)
    later = OBSERVED + timedelta(minutes=1)
    second = _context(online(values, observed_at=later), as_of=later)
    assert compare_research_contexts(first, second)['status'] == 'source_metadata_only'
    changed = deepcopy(first)
    trend = changed['business_trend']
    pair = trend['bank_interim_comparison']
    baseline = pair['baseline']
    row = baseline['periods'][0]
    row['fields']['cash_from_operations'] = trend['bank_interim']['periods'][1]['fields']['cash_from_operations']
    del row['withheld_fields']['cash_from_operations']
    for packet in (baseline, pair):
        packet['packet_digest'] = _digest({k: v for k, v in packet.items() if k != 'packet_digest'})
    with pytest.raises(ValueError, match='interim comparison'):
        save_research_context(changed, project_root=tmp_path, **SCOPE)
