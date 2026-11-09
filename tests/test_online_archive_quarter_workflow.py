"""Exact archive facts join existing research; source bodies never join snapshots."""
from copy import deepcopy
import json

from test_sec_online_quarter_evidence import _financial, _wrapper, CIK, OBSERVED


def _view():
    result = _financial()
    result['archive_quarterly'] = _wrapper(result)
    return result


def _context(view):
    from src.online_research_tools import build_online_research_context
    return build_online_research_context(view, {}, ticker='FICT', profile_key='personal',
        expected_cik=CIK, as_of=OBSERVED)


def test_current_archive_quarter_does_not_relabel_pending_companyfacts():
    from src.online_filing_context import corroborate_online_financials
    view = _view(); before = deepcopy(view)
    result = corroborate_online_financials(view, view['filing_inventory'], as_of=OBSERVED)
    state = result['current']['quarterly']
    assert state['status'] == 'corroborated'
    assert state['reason'] == 'exact_archive_quarter_and_filing'
    assert result['structured_quarterly']['status'] == 'facts_pending'
    assert view == before


def test_business_trend_keeps_direct_quarter_separate_from_ytd_cash_and_saves_proof(tmp_path):
    from src.online_research_context_store import save_research_context, load_research_context
    c = _context(_view())
    quarter = next(p for p in c['business_trend']['periods'] if p['kind'] == 'quarterly')
    assert quarter['current'] and quarter['status'] == 'available'
    assert quarter['fields']['revenue']['value'] == 1234000000
    assert quarter['fields']['revenue']['reported_text'] == '1,234'
    assert quarter['fields']['revenue']['rights_status'] == 'unregistered_sec_archive_personal_inspection_only'
    assert quarter['fields']['revenue']['source_ref'].startswith('https://www.sec.gov/Archives/')
    cash = [m for m in c['business_trend']['metrics'] if m['key'] == 'cfo_less_ppe']
    assert next(m for m in cash if m['period_kind'] == 'quarterly')['status'] == 'withheld'
    assert next(m for m in cash if m['period_kind'] == 'cumulative')['value'] == 300000000
    assert c['scenario_base']['status'] == 'withheld'
    encoded = json.dumps(c)
    assert not any(key in encoded for key in ('"raw_text"', '"source_packet"', '"bank_scope"', 'base64'))
    assert any(r['source'] == 'exact_quarter_receipt' for r in c['source_receipts'])
    scope = dict(profile_key='personal', ticker='FICT', sec_cik=CIK, project_root=tmp_path)
    saved = save_research_context(c, **scope)
    replay = load_research_context(saved['snapshot_id'], **scope)
    assert replay['context'] == c


def test_first_screen_uses_latest_exact_quarter_with_correct_source_label(monkeypatch):
    from src.company_workbench_sections import workbench_projection
    from src.company_answer_summary import _financial_answer
    from src import sec_online_quarter_evidence
    real = sec_online_quarter_evidence.validated_archive_quarter
    monkeypatch.setattr(sec_online_quarter_evidence, 'validated_archive_quarter', lambda *a, **kw: real(*a, **{**kw, 'as_of': OBSERVED}))
    view = _view()
    projection = workbench_projection('FICT', view, {}, expected_cik=CIK)
    assert projection['quarter_count'] == 1
    assert projection['period_kind'] == 'quarterly'
    assert projection['facts']['revenue']['value'] == 1234000000
    answer = _financial_answer(projection, view)
    assert any(label == 'Exact SEC filing fact' for label, _ in answer['links'])
    assert any('personal inspection' in e.lower() for e in answer['evidence'])
    from src.company_workbench_presentation import financial_workspace_html
    from src.sec_online_quarter_view import archive_quarter_html
    table = financial_workspace_html('FICT', view, period_kind='quarterly')
    assert projection['period_end'] in table and '1,234.00' in table
    panel = archive_quarter_html(view, as_of=OBSERVED)
    assert 'Source and reporting basis' in panel and 'Personal inspection only' in panel
    assert 'not single-quarter cash flow' in panel and 'Withheld' in panel


def test_invalid_archive_packet_cannot_fill_the_gap_or_create_a_trend():
    view = _view(); view['archive_quarterly']['source_packet']['periods'][0]['fields']['revenue']['value'] += 1
    c = _context(view)
    assert c['filing_coverage']['current']['quarterly']['status'] != 'corroborated'
    assert not c['business_trend']['periods']


def test_productive_asset_purchases_do_not_become_ppe_cash_generation():
    from test_sec_inline_filing import _xml, _extract
    view = _financial()
    packet = _extract(_xml().replace('PaymentsToAcquirePropertyPlantAndEquipment', 'PaymentsToAcquireProductiveAssets'))
    view['archive_quarterly'] = _wrapper(view, packet)
    c = _context(view)
    metric = next(m for m in c['business_trend']['metrics'] if m['key'] == 'cfo_less_ppe' and m['period_kind'] == 'cumulative')
    assert metric['status'] == 'withheld' and metric['value'] is None


def test_headline_comparison_uses_replacement_archive_value_and_same_definition(monkeypatch):
    from src.sec_quarterly_history import build_sec_quarterly_history
    from src.company_workbench_sections import workbench_projection
    from src.company_answer_summary import _financial_answer
    from src import sec_online_quarter_evidence
    real = sec_online_quarter_evidence.validated_archive_quarter
    monkeypatch.setattr(sec_online_quarter_evidence, 'validated_archive_quarter', lambda *a, **kw: real(*a, **{**kw, 'as_of': OBSERVED}))
    view = _view()
    def history(concept):
        facts = dict(cik=1234, facts={'us-gaap': {concept: {'units': {'USD': [
            dict(start='2025-04-01', end='2025-06-30', val=1000000000, form='10-Q',
                 filed='2025-08-01', accn='0000001234-25-000001', fy=2025, fp='Q2'),
            dict(start='2026-04-01', end='2026-06-30', val=600000000, form='10-Q',
                 filed='2026-07-31', accn='0000001234-26-000020', fy=2026, fp='Q2'),
        ]}}}})
        return build_sec_quarterly_history('FICT', facts, expected_cik=CIK,
            observed_at=view['companyfacts_identity']['observed_at'], source_url=view['companyfacts_identity']['source_url'], payload_sha256='d'*64)
    view['quarterly_history'] = history('RegulatedAndUnregulatedOperatingRevenue')
    answer = _financial_answer(workbench_projection('FICT', view, {}), view)
    assert 'Revenue increased vs prior-year quarter' in answer['context']
    view['quarterly_history'] = history('Revenues')
    answer = _financial_answer(workbench_projection('FICT', view, {}), view)
    assert 'Comparable change needs verification' in answer['context']
