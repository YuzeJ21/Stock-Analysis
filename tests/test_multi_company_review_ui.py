"""Disposable Streamlit integration for generic company review and Monitor."""
import pytest
from streamlit.testing.v1 import AppTest
from tests.test_multi_company_sec_review import issuer_view, capture
from src.sec_research_review import save_review,list_reviews


def app():
    import streamlit as st
    from src.sec_research_review_ui import render_company_review,render_review_monitor
    route=st.radio('Test route',['company','monitor'])
    if route=='company':render_company_review(st,st.session_state['test_ticker'],st.session_state['test_view'],profile_key='test')
    else:render_review_monitor(st,profile_key='test')


def issuer_scoped_app():
    import streamlit as st
    from src.sec_research_review_ui import render_company_review
    render_company_review(st,st.session_state.get('test_ticker','MRVL'),st.session_state.get('test_view',{}),
        profile_key='portfolio',expected_cik=st.session_state['test_expected_cik'])


def test_selected_issuer_cannot_save_same_ticker_for_another_cik(tmp_path,monkeypatch):
    from src import sec_research_review_ui as ui
    monkeypatch.setattr(ui,'PROJECT_ROOT',tmp_path)
    at=AppTest.from_function(issuer_scoped_app)
    at.session_state['test_expected_cik']='0001835632'
    at.session_state['test_view']=issuer_view('MRVL','0001060405')
    at.run()
    assert not at.exception
    assert at.button(key='sec-review-save:portfolio:MRVL').disabled
    warnings='\n'.join(w.value for w in at.warning)
    assert '0001835632' in warnings and '0001060405' in warnings
    assert not list(tmp_path.rglob('*.json'))


def test_selected_issuer_cannot_import_same_ticker_for_another_cik(tmp_path,monkeypatch):
    import io
    import streamlit as st
    from src import sec_research_review_ui as ui
    from src.sec_research_review import encode_review
    monkeypatch.setattr(ui,'PROJECT_ROOT',tmp_path)
    raw=encode_review(capture('MRVL','0001060405',profile='portfolio'))
    monkeypatch.setattr(st,'file_uploader',lambda *a,**k:io.BytesIO(raw))
    at=AppTest.from_function(issuer_scoped_app)
    at.session_state['test_expected_cik']='0001835632'
    at.run()
    assert not at.exception
    at.button(key='sec-review-import:portfolio:MRVL').click().run()
    assert not at.exception
    assert any('issuer CIK mismatch' in error.value for error in at.error)
    assert not list(tmp_path.rglob('*.json'))


@pytest.mark.parametrize('expected_cik',[None,'0001835632'])
def test_valid_import_preserves_profile_with_optional_issuer_guard(tmp_path,monkeypatch,expected_cik):
    import io
    import streamlit as st
    from src import sec_research_review_ui as ui
    from src.sec_research_review import encode_review
    monkeypatch.setattr(ui,'PROJECT_ROOT',tmp_path)
    packet=capture('MRVL','0001835632',profile='portfolio')
    monkeypatch.setattr(st,'file_uploader',lambda *a,**k:io.BytesIO(encode_review(packet)))
    at=AppTest.from_function(issuer_scoped_app)
    at.session_state['test_expected_cik']=expected_cik
    at.run()
    assert not at.exception
    at.button(key='sec-review-import:portfolio:MRVL').click().run()
    assert not at.exception and not at.error
    assert list_reviews(tmp_path,'portfolio','MRVL')==[packet]
    assert not list_reviews(tmp_path,'test','MRVL')
    assert at.selectbox(key='sec-review-current:portfolio:MRVL:1').value==0


def test_selected_issuer_replay_excludes_other_ciks_and_explains_them(tmp_path,monkeypatch):
    from src import sec_research_review_ui as ui
    monkeypatch.setattr(ui,'PROJECT_ROOT',tmp_path)
    first=capture('MRVL','0001835632',profile='portfolio')
    second=capture('MRVL','0001835632',profile='portfolio',when='2026-11-02T22:01:00Z')
    other=capture('MRVL','0001060405',profile='portfolio',when='2026-11-02T22:02:00Z')
    paths=[save_review(packet,tmp_path) for packet in (first,second,other)]
    original={path:path.read_bytes() for path in paths}
    at=AppTest.from_function(issuer_scoped_app)
    at.session_state['test_expected_cik']='0001835632'
    at.run()
    assert not at.exception
    assert len(at.selectbox(key='sec-review-current:portfolio:MRVL:2').options)==2
    assert len(at.selectbox(key='sec-review-before:portfolio:MRVL:2:1').options)==3
    assert any('No change' in success.value for success in at.success)
    warnings='\n'.join(w.value for w in at.warning)
    assert 'Excluded 1' in warnings and '0001060405' in warnings and '0001835632' in warnings
    sources='\n'.join(c.value for c in at.caption)
    assert 'CIK 0001835632' in sources and 'CIK 0001060405' not in sources
    # A changed online selection in the same session must bind replay to the new issuer.
    at.session_state['test_expected_cik']='0001060405'
    at.run()
    assert not at.exception
    assert len(at.selectbox(key='sec-review-current:portfolio:MRVL:1').options)==1
    assert any('awaiting a comparison baseline' in item.value for item in at.info)
    assert all(path.read_bytes()==raw for path,raw in original.items())


def test_selected_issuer_with_only_other_cik_receipts_has_no_replay(tmp_path,monkeypatch):
    from src import sec_research_review_ui as ui
    monkeypatch.setattr(ui,'PROJECT_ROOT',tmp_path)
    save_review(capture('MRVL','0001060405',profile='portfolio'),tmp_path)
    at=AppTest.from_function(issuer_scoped_app)
    at.session_state['test_expected_cik']='0001835632'
    at.run()
    assert not at.exception and not at.selectbox
    assert any('Excluded 1' in warning.value for warning in at.warning)
    assert any('No saved evidence matches' in info.value for info in at.info)
    assert len(list_reviews(tmp_path,'portfolio','MRVL'))==1


def test_selected_issuer_saves_and_replays_under_actual_profile(tmp_path,monkeypatch):
    from src import sec_research_review_ui as ui
    monkeypatch.setattr(ui,'PROJECT_ROOT',tmp_path)
    at=AppTest.from_function(issuer_scoped_app)
    at.session_state['test_expected_cik']='0001835632'
    at.session_state['test_view']=issuer_view('MRVL','0001835632')
    at.run()
    assert not at.exception
    at.button(key='sec-review-save:portfolio:MRVL').click().run()
    assert not at.exception
    packets=list_reviews(tmp_path,'portfolio','MRVL')
    assert len(packets)==1 and packets[0]['sec_cik']=='0001835632'
    assert not list_reviews(tmp_path,'test','MRVL') and not (tmp_path/'data').exists()
    fresh=AppTest.from_function(issuer_scoped_app)
    fresh.session_state['test_expected_cik']='0001835632'
    fresh.run()
    assert not fresh.exception
    assert fresh.selectbox(key='sec-review-current:portfolio:MRVL:1').value==0
    assert not any(button.label=='Save review status' for button in fresh.button)


@pytest.mark.parametrize('expected_cik',['','0000000000','1835632','00018356321',1835632,'０００１８３５６３２'])
def test_invalid_selected_cik_cannot_save_import_or_replay(tmp_path,monkeypatch,expected_cik):
    import io
    import streamlit as st
    from src import sec_research_review_ui as ui
    from src.sec_research_review import encode_review
    monkeypatch.setattr(ui,'PROJECT_ROOT',tmp_path)
    packet=capture('MRVL','0001835632',profile='portfolio')
    saved=save_review(packet,tmp_path)
    original=saved.read_bytes()
    monkeypatch.setattr(st,'file_uploader',lambda *a,**k:io.BytesIO(encode_review(packet)))
    at=AppTest.from_function(issuer_scoped_app)
    at.session_state['test_expected_cik']=expected_cik
    at.session_state['test_view']=issuer_view('MRVL','0001835632')
    at.run()
    assert not at.exception
    assert any('nonzero 10-digit CIK' in error.value for error in at.error)
    assert not at.button and not at.selectbox
    assert saved.read_bytes()==original and len(list(tmp_path.rglob('*.json')))==1


def test_selected_cik_also_guards_pinned_company_pair(tmp_path,monkeypatch):
    from src import sec_research_review_ui as ui
    monkeypatch.setattr(ui,'PROJECT_ROOT',tmp_path)
    first=capture('AMD','0000002488',profile='portfolio')
    second=capture('AMD','0000002488',profile='portfolio',when='2026-11-02T22:01:00Z')
    for packet in (first,second):save_review(packet,tmp_path)
    at=AppTest.from_function(issuer_scoped_app)
    at.session_state['test_ticker']='AMD'
    at.session_state['test_expected_cik']='0000002488'
    at.query_params['sec_pair']=first['receipt_id']+'.'+second['receipt_id']
    at.run()
    assert not at.exception
    assert any('Pinned SEC evidence comparison' in item.value for item in at.markdown)
    at.session_state['test_expected_cik']='0001045810'
    at.run()
    assert not at.exception
    assert not any('Pinned SEC evidence comparison' in item.value for item in at.markdown)
    warnings='\n'.join(w.value for w in at.warning)
    assert '0001045810' in warnings and 'excluded' in warnings.lower()
    assert not any('CIK 0000002488' in item.value for item in at.caption)


def test_amd_save_twice_replay_and_monitor_company_selection(tmp_path,monkeypatch):
    from src import sec_research_review_ui as ui
    monkeypatch.setattr(ui,'PROJECT_ROOT',tmp_path)
    at=AppTest.from_function(app);at.session_state['test_ticker']='AMD';at.session_state['test_view']=issuer_view();at.run()
    assert not at.exception
    assert not any('Check the operating income filing'==b.label for b in at.button)
    at.button(key='sec-review-save:test:AMD').click().run()
    at.button(key='sec-review-save:test:AMD').click().run()
    assert not at.exception and any('No change' in s.value for s in at.success)
    assert len(list_reviews(tmp_path,'test','AMD'))==2
    save_review(capture('DUK','0001326160'),tmp_path)
    at.radio[0].set_value('monitor').run()
    assert not at.exception
    assert 'Saved companies 2' in '\n'.join(c.value for c in at.caption)
    at.selectbox(key='sec-review-monitor-company:test').select('DUK').run()
    text='\n'.join(m.value for m in at.markdown)
    assert 'DUK' in text and 'ticker=DUK' in text and 'awaiting a comparison baseline' in text
    assert not (tmp_path/'data').exists()
    fresh=AppTest.from_function(app);fresh.session_state['test_ticker']='AMD';fresh.session_state['test_view']={};fresh.run()
    assert not fresh.exception and any('No change' in s.value for s in fresh.success)


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
    assert 'Unreadable 1' in '\n'.join(c.value for c in at.caption)
    at.selectbox(key='sec-review-monitor-company:test').select('DUK').run()
    assert any('cannot be verified' in w.value for w in at.warning)
    at.selectbox(key='sec-review-monitor-company:test').select('AMD').run()
    assert not at.exception and any('awaiting a comparison baseline' in m.value for m in at.markdown)


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
    assert any('company or research profile mismatch' in e.value for e in at.error)
    assert not list(tmp_path.rglob('*.json'))


def test_monitor_honors_company_return_route(tmp_path,monkeypatch):
    from src import sec_research_review_ui as ui
    monkeypatch.setattr(ui,'PROJECT_ROOT',tmp_path)
    save_review(capture(),tmp_path);save_review(capture('DUK','0001326160'),tmp_path)
    at=AppTest.from_function(app);at.session_state['test_ticker']='AMD';at.session_state['test_view']={};at.query_params['return_ticker']='DUK';at.run()
    at.radio[0].set_value('monitor').run()
    assert at.selectbox(key='sec-review-monitor-company:test').value=='DUK'
    assert any('>View saved DUK evidence</a>' in item.value for item in at.markdown)


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
    assert any('Saved SEC evidence' in m.value for m in at.markdown)
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
    assert 'Saved companies 1' in '\n'.join(c.value for c in at.caption)
    assert any('Unverified entries in the SEC evidence folder · 1' in w.value for w in at.warning)
    assert at.selectbox(key='sec-review-monitor-company:test').value=='AMD'
