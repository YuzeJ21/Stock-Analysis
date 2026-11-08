"""Compact sample coverage cannot imply a market-wide research census."""
from copy import deepcopy


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
