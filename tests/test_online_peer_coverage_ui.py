from copy import deepcopy

import pytest
from streamlit.testing.v1 import AppTest

from test_online_peer_coverage import audit,dependencies
from test_online_peer_valuation import SYMBOLS,NOW


def test_coverage_summary_names_its_denominator_pending_and_separate_eligibility():
    from src.online_peer_coverage_ui import peer_coverage_html
    d,calls=dependencies();state={};view=audit(state,inspect=True,deps=d);before=deepcopy(view)
    html=peer_coverage_html(view)
    assert '行业同行估值覆盖' in html and '指定查询对象' in html and '完整美国市场' in html
    assert '本公司年度 P/E 可用' in html and '同行比较可用' in html
    assert '1 / 4' in html and '待核查' in html and '3 / 4' in html
    assert '会话内' in html and '行业待核对' in html
    assert 'semiconductors' in html and '3674' in html and 'FICT' in html
    assert '已完成参照核查' in html and 'not_assessed' not in html
    assert 'ticker=FICT' in html and 'online=1' in html and 'section=valuation' in html
    assert view==before


def test_blocked_subject_and_candidate_reasons_are_not_conflated():
    from src.online_peer_coverage_ui import peer_coverage_html
    d,calls=dependencies();d['vendor']=lambda *a,**kw:dict(status='unavailable')
    html=peer_coverage_html(audit({},inspect=True,deps=d))
    assert '同行尚未核查' in html and '供应商' in html and '未取得' in html
    assert '主要缺口' in html and '候选参照排除原因' in html
    assert '第一项阻碍' in html and '唯一发行人数量' in html


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
    next(b for b in at.button if b.label=='核查下一家公司').click().run(timeout=30)
    assert calls and not at.exception and '1 / 4' in '\n'.join(m.value for m in at.markdown)
    before=list(calls);at.run();assert calls==before
    assert any(s.label=='重新核查公司' for s in at.selectbox)
    next(b for b in at.button if b.label=='重试所选公司').click().run(timeout=30)
    assert len(calls)>len(before) and not at.exception


def test_reset_clears_session_progress_without_fetching(monkeypatch):
    calls=setup(monkeypatch);at=AppTest.from_function(_app).run()
    next(b for b in at.button if b.label=='核查下一家公司').click().run(timeout=30)
    before=list(calls);next(b for b in at.button if b.label=='重新开始样本').click().run()
    assert calls==before and '0 / 4' in '\n'.join(m.value for m in at.markdown) and not at.exception


@pytest.mark.parametrize('sources_only',[False,True])
def test_amendment_scope_sources_and_flag_discrepancy_are_visible_in_both_company_panes(monkeypatch,sources_only):
    from test_annual_amendment_evidence import fixture
    from test_online_peer_valuation import build
    from src.online_peer_valuation_ui import online_peer_valuation_html
    c,p,policy=fixture(monkeypatch);html=online_peer_valuation_html(build(c),sources_only=sources_only)
    assert '原始年度申报 EPS' in html and '修订范围' in html
    assert 'AmendmentFlag=false' in html and '技术证据解释' in html
    assert policy['original_sha256'] in html and policy['amendment_sha256'] in html
    assert '0000001001-26-000001' in html and '0000001001-26-000002' in html


def test_company_valuation_links_directly_to_the_industry_audit():
    from test_online_peer_valuation import build
    from src.online_peer_valuation_ui import online_peer_valuation_html
    html=online_peer_valuation_html(build())
    assert '查看跨行业同行覆盖' in html and 'page=discover#peer-coverage-sample' in html


def test_inspected_company_detail_opens_without_another_source_request(monkeypatch):
    calls = setup(monkeypatch)
    at = AppTest.from_function(_app).run()
    at.button(key="peer-coverage-next").click().run(timeout=30)
    before = list(calls)
    at.selectbox(key="peer-coverage-detail").select("FICT").run(timeout=30)
    text = "\n".join(item.value for item in at.markdown)
    assert "年度 P/E 高于同行参照 20.0%" in text
    assert "2026-10-30" in text
    assert "查看实际财年、价格与来源" in text
    assert calls == before and not at.exception
    at.button(key="peer-coverage-reset").click().run(timeout=30)
    assert "年度 P/E 高于同行参照" not in "\n".join(item.value for item in at.markdown)
    assert calls == before and not at.exception
