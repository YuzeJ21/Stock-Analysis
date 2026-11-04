"""Disposable Streamlit integration for generic company review and Monitor."""
from streamlit.testing.v1 import AppTest
from tests.test_multi_company_sec_review import issuer_view, capture
from src.sec_research_review import save_review,list_reviews


def app():
    import streamlit as st
    from src.sec_research_review_ui import render_company_review,render_review_monitor
    route=st.radio('Test route',['company','monitor'])
    if route=='company':render_company_review(st,st.session_state['test_ticker'],st.session_state['test_view'],profile_key='test')
    else:render_review_monitor(st,profile_key='test')


def test_amd_save_twice_replay_and_monitor_company_selection(tmp_path,monkeypatch):
    from src import sec_research_review_ui as ui
    monkeypatch.setattr(ui,'PROJECT_ROOT',tmp_path)
    at=AppTest.from_function(app);at.session_state['test_ticker']='AMD';at.session_state['test_view']=issuer_view();at.run()
    assert not at.exception
    assert not any('核查营业利润原始申报'==b.label for b in at.button)
    at.button(key='sec-review-save:test:AMD').click().run()
    at.button(key='sec-review-save:test:AMD').click().run()
    assert not at.exception and any('未变化' in s.value for s in at.success)
    assert len(list_reviews(tmp_path,'test','AMD'))==2
    save_review(capture('DUK','0001326160'),tmp_path)
    at.radio[0].set_value('monitor').run()
    assert not at.exception
    assert '已保存 2 家公司' in '\n'.join(c.value for c in at.caption)
    at.selectbox(key='sec-review-monitor-company:test').select('DUK').run()
    text='\n'.join(m.value for m in at.markdown)
    assert 'DUK' in text and 'ticker=DUK' in text and '等待比较基线' in text
    assert not (tmp_path/'data').exists()
    fresh=AppTest.from_function(app);fresh.session_state['test_ticker']='AMD';fresh.session_state['test_view']={};fresh.run()
    assert not fresh.exception and any('未变化' in s.value for s in fresh.success)


def test_selected_company_cannot_save_another_cached_issuer(tmp_path,monkeypatch):
    from src import sec_research_review_ui as ui
    monkeypatch.setattr(ui,'PROJECT_ROOT',tmp_path)
    at=AppTest.from_function(app);at.session_state['test_ticker']='DUK';at.session_state['test_view']=issuer_view();at.run()
    assert at.button(key='sec-review-save:test:DUK').disabled
    assert not list(tmp_path.rglob('*.json'))


def test_company_without_supported_observation_explains_scope(tmp_path,monkeypatch):
    from src import sec_research_review_ui as ui
    monkeypatch.setattr(ui,'PROJECT_ROOT',tmp_path)
    at=AppTest.from_function(app);at.session_state['test_ticker']='TSM';at.session_state['test_view']={};at.run()
    assert at.button(key='sec-review-save:test:TSM').disabled
    assert 'US-GAAP' in '\n'.join(c.value for c in at.caption)


def test_corrupt_company_visible_without_hiding_healthy_company(tmp_path,monkeypatch):
    from src import sec_research_review_ui as ui
    monkeypatch.setattr(ui,'PROJECT_ROOT',tmp_path)
    save_review(capture(),tmp_path);bad=save_review(capture('DUK','0001326160'),tmp_path);bad.write_bytes(b'{}')
    at=AppTest.from_function(app);at.session_state['test_ticker']='AMD';at.session_state['test_view']={};at.run()
    at.radio[0].set_value('monitor').run()
    assert not at.exception
    assert '不可读 1' in '\n'.join(c.value for c in at.caption)
    at.selectbox(key='sec-review-monitor-company:test').select('DUK').run()
    assert any('无法核验' in w.value for w in at.warning)
    at.selectbox(key='sec-review-monitor-company:test').select('AMD').run()
    assert not at.exception and any('等待比较基线' in m.value for m in at.markdown)


def test_wrong_company_import_is_rejected_before_any_write(tmp_path,monkeypatch):
    import io
    import streamlit as st
    from src import sec_research_review_ui as ui
    from src.sec_research_review import encode_review
    monkeypatch.setattr(ui,'PROJECT_ROOT',tmp_path)
    raw=encode_review(capture('DUK','0001326160'))
    monkeypatch.setattr(st,'file_uploader',lambda *a,**k:io.BytesIO(raw))
    at=AppTest.from_function(app);at.session_state['test_ticker']='AMD';at.session_state['test_view']={};at.run()
    at.button(key='sec-review-import:test:AMD').click().run()
    assert not at.exception
    assert any('公司或研究集合不符' in e.value for e in at.error)
    assert not list(tmp_path.rglob('*.json'))


def test_monitor_honors_company_return_route(tmp_path,monkeypatch):
    from src import sec_research_review_ui as ui
    monkeypatch.setattr(ui,'PROJECT_ROOT',tmp_path)
    save_review(capture(),tmp_path);save_review(capture('DUK','0001326160'),tmp_path)
    at=AppTest.from_function(app);at.session_state['test_ticker']='AMD';at.session_state['test_view']={};at.query_params['return_ticker']='DUK';at.run()
    at.radio[0].set_value('monitor').run()
    assert at.selectbox(key='sec-review-monitor-company:test').value=='DUK'


def test_saved_online_only_company_has_offline_route_without_registration(tmp_path,monkeypatch):
    from types import SimpleNamespace
    from src import dashboard,sec_research_review_ui as ui
    monkeypatch.setattr(ui,'PROJECT_ROOT',tmp_path)
    save_review(capture('FICT','0000001234'),tmp_path)
    seen=[]
    monkeypatch.setattr(dashboard,'render_integrated_company',lambda *a,**k:seen.append((a,k)))
    monkeypatch.setattr(dashboard,'search_sec_company_candidates',lambda *a,**k:(_ for _ in ()).throw(AssertionError('replay must not fetch identity')))
    class FakeSt:
        query_params={'ticker':'FICT','section':'notes'}
        session_state={}
        def caption(self,*a,**k):pass
        def markdown(self,*a,**k):pass
    monkeypatch.setattr(dashboard,'st',FakeSt())
    monkeypatch.setattr(dashboard,'render_research_workspace_header',lambda *a,**k:None)
    context=SimpleNamespace(profile_key='test',freshness_state='stale')
    dashboard.render_company_workbench(SimpleNamespace(list_local_tickers=lambda:[]),context,{},None)
    assert seen and seen[0][0][1]=='FICT'
    assert seen[0][1]['saved_available'] is False
    assert seen[0][1]['online_candidate'] is None


def test_offline_unregistered_receipt_renders_without_company_csv_or_network(tmp_path,monkeypatch):
    from src import dashboard,sec_research_review_ui as ui
    monkeypatch.setattr(ui,'PROJECT_ROOT',tmp_path)
    save_review(capture('FICT','0000001234'),tmp_path)
    def no_transport(*a,**k):raise AssertionError('offline replay attempted identity transport')
    monkeypatch.setattr(dashboard,'search_sec_company_candidates',no_transport)
    def offline_app():
        import streamlit as st
        from types import SimpleNamespace
        from src.dashboard import render_company_workbench
        render_company_workbench(SimpleNamespace(list_local_tickers=lambda:[]),SimpleNamespace(profile_key='test',freshness_state='stale'),{},None)
    at=AppTest.from_function(offline_app);at.query_params.update(ticker='FICT',section='notes');at.run()
    assert not at.exception
    assert any('已保存 SEC 证据' in m.value for m in at.markdown)
    assert at.button(key='sec-review-save:test:FICT').disabled
    assert at.selectbox(key='sec-review-current:test:FICT:1').value==0
    assert not (tmp_path/'data').exists()


def test_malformed_inventory_entry_is_visible_separately_from_company_counts(tmp_path,monkeypatch):
    from src import sec_research_review_ui as ui
    from src.sec_research_review import _profile_directory
    monkeypatch.setattr(ui,'PROJECT_ROOT',tmp_path)
    save_review(capture(),tmp_path)
    (_profile_directory(tmp_path,'test')/'DUK.bak').mkdir()
    at=AppTest.from_function(app);at.session_state['test_ticker']='AMD';at.session_state['test_view']={};at.run()
    at.radio[0].set_value('monitor').run()
    assert not at.exception
    assert '已保存 1 家公司' in '\n'.join(c.value for c in at.caption)
    assert any('1 个名称无法核验' in w.value for w in at.warning)
    assert at.selectbox(key='sec-review-monitor-company:test').value=='AMD'
