from copy import deepcopy
import re

import pytest
from streamlit.testing.v1 import AppTest

from test_online_peer_coverage import audit,dependencies
from test_online_peer_valuation import SYMBOLS,NOW


def test_peer_coverage_renders_english_with_denominator_and_three_reference_gate():
    from src.online_peer_coverage_ui import peer_coverage_html
    d,_=dependencies();view=audit({},inspect=True,deps=d)
    html=peer_coverage_html(view)
    assert not re.search(r'[\u3400-\u9fff]',html)
    assert '1 / 4' in html
    assert 'at least 3' in html.lower()
    assert 'session' in html.lower() and 'personal research' in html.lower()


def test_coverage_summary_names_its_denominator_pending_and_separate_eligibility():
    from src.online_peer_coverage_ui import peer_coverage_html
    d,calls=dependencies();state={};view=audit(state,inspect=True,deps=d);before=deepcopy(view)
    html=peer_coverage_html(view)
    assert 'Industry peer valuation coverage' in html and 'specified companies' in html and 'full US market' in html
    assert 'Selected-company annual P/E available' in html and 'Reference comparison available' in html
    assert '1 / 4' in html and 'Pending' in html and '3 / 4' in html
    assert 'within this session' in html and 'Industry unverified' in html
    assert 'semiconductors' in html and '3674' in html and 'FICT' in html
    assert 'References assessed' in html and 'not_assessed' not in html
    assert 'ticker=FICT' in html and 'online=1' in html and 'section=valuation' in html
    assert view==before


def test_blocked_subject_and_candidate_reasons_are_not_conflated():
    from src.online_peer_coverage_ui import peer_coverage_html
    d,calls=dependencies();d['vendor']=lambda *a,**kw:dict(status='unavailable')
    html=peer_coverage_html(audit({},inspect=True,deps=d))
    assert 'References remain unassessed' in html and 'Provider' in html and 'unavailable' in html
    assert 'Main gaps' in html and 'Candidate exclusions' in html
    assert 'First blocker' in html and 'unique-issuer count' in html


def test_coverage_links_and_text_are_escaped_without_executing_source_markup():
    from src.online_peer_coverage_ui import peer_coverage_html
    d,calls=dependencies();view=audit({},inspect=True,deps=d)
    view['rows'][0]['industry_label']='<script>bad</script>'
    view['rows'][0]['source_refs'][0]['source_url']='javascript:alert(1)'
    html=peer_coverage_html(view)
    assert '<script>' not in html and 'javascript:' not in html


def _app():
    import streamlit as st
    from src.online_peer_coverage_ui import render_peer_coverage
    render_peer_coverage(st)


def setup(monkeypatch):
    import src.online_peer_coverage_ui as ui
    from src.online_peer_coverage import get_peer_coverage
    d,calls=dependencies()
    def get(state,**kwargs):
        kwargs.update(tickers=SYMBOLS,dependencies=d,as_of=NOW)
        return get_peer_coverage(state,**kwargs)
    monkeypatch.setattr(ui,'get_peer_coverage',get)
    return calls


def test_real_coverage_controls_only_fetch_on_explicit_next_or_retry(monkeypatch):
    calls=setup(monkeypatch);at=AppTest.from_function(_app).run()
    assert not calls and not at.exception
    next(b for b in at.button if b.label=='Inspect next company').click().run(timeout=30)
    assert calls and not at.exception and '1 / 4' in '\n'.join(m.value for m in at.markdown)
    before=list(calls);at.run();assert calls==before
    assert any(s.label=='Company to retry' for s in at.selectbox)
    next(b for b in at.button if b.label=='Retry selected company').click().run(timeout=30)
    assert len(calls)>len(before) and not at.exception


def test_reset_clears_session_progress_without_fetching(monkeypatch):
    calls=setup(monkeypatch);at=AppTest.from_function(_app).run()
    next(b for b in at.button if b.label=='Inspect next company').click().run(timeout=30)
    before=list(calls);next(b for b in at.button if b.label=='Restart sample').click().run()
    assert calls==before and '0 / 4' in '\n'.join(m.value for m in at.markdown) and not at.exception


@pytest.mark.parametrize('sources_only',[False,True])
def test_amendment_scope_sources_and_flag_discrepancy_are_visible_in_both_company_panes(monkeypatch,sources_only):
    from test_annual_amendment_evidence import fixture
    from test_online_peer_valuation import build
    from src.online_peer_valuation_ui import online_peer_valuation_html
    c,p,policy=fixture(monkeypatch);html=online_peer_valuation_html(build(c),sources_only=sources_only)
    assert 'Original annual EPS' in html and 'Amendment scope' in html
    assert 'AmendmentFlag=false' in html and 'bounded technical evidence interpretation' in html
    assert policy['original_sha256'] in html and policy['amendment_sha256'] in html
    assert '0000001001-26-000001' in html and '0000001001-26-000002' in html


def test_company_valuation_links_directly_to_the_industry_audit():
    from test_online_peer_valuation import build
    from src.online_peer_valuation_ui import online_peer_valuation_html
    html=online_peer_valuation_html(build())
    assert 'View cross-industry peer coverage' in html and 'page=discover#peer-coverage-sample' in html
