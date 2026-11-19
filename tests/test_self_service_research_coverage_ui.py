"""Compact sample coverage cannot imply a market-wide research census."""
from contextlib import nullcontext
from copy import deepcopy

import pytest


def test_initial_study_shows_all_unattempted_companies_and_fixed_denominator():
    from src.self_service_research_coverage import get_self_service_coverage
    from src.self_service_research_coverage_ui import self_service_coverage_html
    view = get_self_service_coverage({})
    html = self_service_coverage_html(view)
    assert 'Self-service research coverage' in html
    assert '0 / 12' in html
    assert 'not market-wide coverage' in html
    for group in ('Semiconductors','Banks','Utilities','Foreign issuers'):
        assert group in html
    assert 'Unattempted' in html and '3' in html


def test_malformed_reduced_counts_never_reach_the_display():
    from src.self_service_research_coverage import get_self_service_coverage
    from src.self_service_research_coverage_ui import self_service_coverage_html
    view = deepcopy(get_self_service_coverage({}))
    view['counts']['dated_price'] = 999
    html = self_service_coverage_html(view)
    assert '999' not in html


def test_dated_comparison_recounts_the_fixed_sample_and_distinguishes_unattempted():
    from src.self_service_research_coverage import CAPABILITY_LABELS, SAMPLE
    from src.self_service_research_coverage_ui import dated_coverage_comparison_html

    before = {key: ('AMD', 'C') for key in CAPABILITY_LABELS}
    common = {key: ('held', 'current_filing_facts_pending') for key in CAPABILITY_LABELS}
    rows = {ticker: dict(common) for ticker in SAMPLE if ticker != 'AMD'}
    rows['C']['direct_quarter'] = ('available', 'current_exact_reported_period')
    rows['DUK']['direct_quarter'] = ('available', 'current_exact_reported_period')
    report = dict(baseline_date='2026-11-08', measured_date='2026-11-16', baseline_available=before,
                  rows=rows)
    html = dated_coverage_comparison_html(report)
    assert 'Dated study results' in html and '2026-11-08' in html and '2026-11-16' in html
    assert '11 / 12 attempted' in html
    assert 'Now available · DUK' in html and 'Unattempted · AMD' in html
    assert 'Previously available, now blocked · AMD' not in html
    assert 'current filing facts pending' in html


def test_same_source_tsm_recheck_preserves_original_study_results():
    from src.self_service_research_coverage_ui import dated_coverage_comparison_html
    from src.self_service_study_results import DATED_STUDY

    html = dated_coverage_comparison_html(DATED_STUDY)
    assert 'Exact private research replay · <strong>10 / 12 → 10 / 12' in html
    assert 'Same-source replay recheck</strong> · 10 / 12 → 11 / 12' in html
    assert 'TSM reopened unchanged using the retained study inputs. ADS valuation remains withheld.' in html


def test_storage_proof_uses_readable_scoped_surface_and_escaped_metadata():
    from src.self_service_research_coverage_ui import STYLE,peer_storage_proof_html
    html=peer_storage_proof_html(dict(status='retained',encoding='zlib+base64',expanded_bytes=74100090,
        stored_bytes=7032521,packet_digest='<script>changed</script>',reason='full_original_peer_packet_restored'))
    assert 'aria-label="Peer source storage proof"' in html
    assert '74,100,090' in html and '7,032,521' in html
    assert '<script>' not in html and '&lt;script&gt;' in html
    assert '[data-peer-source-storage]' in STYLE and 'background:#fff!important' in STYLE

def test_paused_study_keeps_manual_recheck_available(monkeypatch):
    from src import self_service_research_coverage_ui as ui
    buttons = {}
    class Surface:
        session_state = {}
        def caption(self, *args, **kwargs): pass
        def markdown(self, *args, **kwargs): pass
        def button(self, label, *, key, disabled=False):
            buttons[key] = disabled
            return False
        def selectbox(self, label, options, **kwargs): return options[0]
        def radio(self, label, options, **kwargs): return options[0]
    view = {'status':'inspection_only','paused':True,'pending_count':11,
        'rows':[{'ticker':'AMD','attempted':True}]}
    monkeypatch.setattr(ui,'get_self_service_coverage',lambda *a,**k:view)
    monkeypatch.setattr(ui,'sec_request_identification',lambda *a:None)
    monkeypatch.setattr(ui,'self_service_coverage_html',lambda *a:'')
    monkeypatch.setattr(ui,'validated_coverage_view',lambda *a:view)
    monkeypatch.setattr(ui,'_company_details',lambda *a:None)
    ui.render_self_service_coverage(Surface())
    assert buttons['self-service-coverage-next'] is True
    assert buttons['self-service-coverage-retry'] is False
    assert buttons['self-service-coverage-reset'] is False


@pytest.mark.parametrize('lane,ticker', [('general', 'AMD'), ('bank', 'IBN'), ('available', 'AMD')])
def test_retained_replay_action_is_scoped_to_an_eligible_selected_company(monkeypatch, lane, ticker):
    from src import self_service_research_coverage_ui as ui

    class Rerun(Exception):
        pass

    replay_key = 'self-service-coverage-replay'
    calls, buttons, captions = [], [], []

    class Surface:
        def __init__(self):
            self.session_state = {}

        def caption(self, message):
            captions.append(message)

        def markdown(self, *args, **kwargs):
            pass

        def button(self, label, *, key, disabled=False):
            buttons.append((label, key, disabled))
            return key == replay_key

        def radio(self, label, options, **kwargs):
            return ticker

        def spinner(self, message):
            return nullcontext()

        def rerun(self):
            raise Rerun

    hold = {'status': 'held', 'reason': 'snapshot_proof_needs_explicit_recheck'}
    available = {'status': 'available', 'reason': 'exact_private_context_replay'}
    row = {'ticker': ticker, 'attempted': True, 'snapshot_replay': hold if lane == 'general' else available}
    if lane == 'bank':
        row.update(snapshot_replay={'status': 'held', 'reason': 'usable_current_research_fields_required'},
                   bank_evidence={'snapshot_replay': hold})
    view = {'status': 'inspection_only', 'paused': True, 'pending_count': 10,
            'rows': [{'ticker': 'NVDA', 'attempted': True, 'snapshot_replay': hold}, row]}

    def coverage(state, **kwargs):
        calls.append(kwargs)
        return view

    monkeypatch.setattr(ui, 'get_self_service_coverage', coverage)
    monkeypatch.setattr(ui, 'sec_request_identification', lambda st: None)
    monkeypatch.setattr(ui, 'validated_coverage_view', lambda value: value)
    monkeypatch.setattr(ui, 'self_service_coverage_html', lambda value: '')
    monkeypatch.setattr(ui, '_company_details', lambda st, value: None)
    if lane == 'available':
        ui.render_self_service_coverage(Surface())
        assert all(key != replay_key for _, key, _ in buttons)
        assert calls == [{'user_agent': None}]
    else:
        with pytest.raises(Rerun):
            ui.render_self_service_coverage(Surface())
        assert ('Recheck retained replay', replay_key, False) in buttons
        assert any('existing observations' in text and 'no provider refresh' in text for text in captions)
        assert calls == [{'user_agent': None}, {'replay_ticker': ticker}]
