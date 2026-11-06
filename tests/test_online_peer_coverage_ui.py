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


def _discover_app():
    import streamlit as st
    from src.online_peer_coverage import DISCOVER_SAMPLE
    from src.online_peer_coverage_ui import render_peer_coverage

    render_peer_coverage(st, tickers=DISCOVER_SAMPLE)


def test_discover_explicit_pending_selection_requests_only_on_button_click(monkeypatch):
    import src.online_peer_coverage_ui as ui
    from src.online_peer_coverage import get_peer_coverage

    calls = []

    def unavailable(**kwargs):
        calls.append("classification")
        return {"status": "unavailable", "reason": "classification_source_unavailable"}

    def get(state, **kwargs):
        return get_peer_coverage(state, **kwargs, dependencies={"classification": unavailable}, as_of=NOW)

    monkeypatch.setattr(ui, "get_peer_coverage", get)
    app = AppTest.from_function(_discover_app).run()
    assert not app.exception and not calls
    select = app.selectbox(key="peer-coverage-pending")
    assert select.options[:9] == ["AMD", "JPM", "DUK", "TXN", "BAC", "SO", "QCOM", "WFC", "NEE"]
    select.select("NEE").run()
    assert not calls
    app.button(key="peer-coverage-inspect-selected").click().run()
    assert not app.exception and calls == ["classification"]
    assert "NEE" not in app.selectbox(key="peer-coverage-pending").options
    assert app.selectbox(key="peer-coverage-retry").options == ["NEE"]
    text = "\n".join(item.value for item in app.markdown)
    assert "1 / 19" in text and "18 / 19" in text
    app.run()
    assert calls == ["classification"]


def test_qcom_detail_shows_candidate_outcomes_without_fetching(monkeypatch):
    import src.online_peer_coverage_ui as ui
    from src.online_peer_coverage import DISCOVER_SESSION_KEY
    from src.online_peer_valuation import _empty

    view = audit({}, tickers=("QCOM",))
    view["rows"][0].update(
        attempted=True, comparison_state="withheld", subject_pe_state="available",
        reference_state="partially_assessed", accepted_reference_count=0,
        primary_reason="at_least_three_compatible_industry_references_required",
        candidate_basis="reviewed_qcom_sec_sic_3663", candidate_count=3,
        checked_candidate_count=2, pending_candidate_count=1,
        excluded=[{"ticker": "BKTI", "reason": "peer_fiscal_window_differs",
                   "listing_venue_evidence": {
                       "source_url": "https://www.sec.gov/Archives/edgar/data/2186/000143774926032498/bkti20261012_8k.htm"}},
                  {"ticker": "AIRG", "reason": "annual_eps_confirmed_loss",
                   "annual_eps_audit": {
                       "reason": "annual_eps_confirmed_loss",
                       "source_url": "https://www.sec.gov/Archives/edgar/data/1272842/000119312526076752/airg-20251231.htm#F_527a0f43-6da8-463a-ba07-fd1fabfea911"}},
                  {"ticker": "MSI", "reason": "source_paused_after_repeated_failures"}],
    )
    calls = []

    def get(state, *, detail_ticker=None, **kwargs):
        calls.append(kwargs)
        detail = _empty("QCOM", "at_least_three_compatible_industry_references_required") if detail_ticker == "QCOM" else None
        return {**view, "selected_detail": detail}

    monkeypatch.setattr(ui, "get_peer_coverage", get)
    app = AppTest.from_function(_discover_app)
    app.session_state[DISCOVER_SESSION_KEY] = {"requested_tickers": ["QCOM"], "packets": {"QCOM": {}}}
    app.run()
    app.selectbox(key="peer-coverage-detail").select("QCOM").run()

    assert not app.exception
    detail = next(item.value for item in app.markdown if 'aria-label="QCOM SEC SIC 3663 候选"' in item.value)
    assert "候选已核查 2 / 3 · 候选待核查 1 家" in detail
    assert "BKTI</strong> · 未通过 · 实际财年起止日期差异超过 35 天" in detail
    assert detail.count("NYSE American 交易所核对") == 1
    assert 'href="https://www.sec.gov/Archives/edgar/data/2186/000143774926032498/bkti20261012_8k.htm"' in detail
    assert "AIRG</strong> · 未通过 · 10-K 与 Companyfacts 均确认年度摊薄 EPS 为负" in detail
    assert 'airg-20251231.htm#F_527a0f43-6da8-463a-ba07-fd1fabfea911"' in detail
    assert "MSI</strong> · 待核查 · 连续来源失败" in detail
    assert "相同供应商行业" in detail and "至少 3 家" in detail
    assert all(not any(call.get(key) for key in ("inspect_requested", "inspect_ticker", "retry_ticker")) for call in calls)
