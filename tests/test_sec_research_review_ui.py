"""Exercise explicit actions with disposable storage and synthetic SEC facts."""
from streamlit.testing.v1 import AppTest
from tests.test_sec_research_review import view


def app():
    import streamlit as st
    from src.sec_research_review_ui import render_company_review,render_review_monitor
    page=st.radio('Test route',['company','monitor'])
    if page=='company':render_company_review(st,'NEM',st.session_state['test_view'],profile_key='test')
    else:render_review_monitor(st,profile_key='test',monitor_origin=st.session_state.get('test_monitor_origin'))


def test_save_twice_replay_and_monitor_survive_fresh_session(tmp_path,monkeypatch):
    from src import sec_research_review_ui as ui
    monkeypatch.setattr(ui,'PROJECT_ROOT',tmp_path)
    at=AppTest.from_function(app);at.session_state['test_view']=view();at.run()
    assert not at.exception
    at.button(key='sec-review-save:test:NEM').click().run()
    at.button(key='sec-review-save:test:NEM').click().run()
    assert not at.exception
    assert any('未变化' in e.value for e in at.success)
    assert len(list(tmp_path.rglob('*.json')))==2
    at.radio[0].set_value('monitor').run()
    assert not at.exception
    assert '未变化' in '\n'.join(x.value for x in at.markdown)
    fresh=AppTest.from_function(app);fresh.session_state['test_view']={'status':'not_requested'};fresh.run()
    assert not fresh.exception
    assert any('未变化' in e.value for e in fresh.success)
    assert fresh.button(key='sec-review-save:test:NEM').disabled


def test_monitor_reports_gaps_without_process_records(tmp_path,monkeypatch):
    from src import sec_research_review_ui as ui
    monkeypatch.setattr(ui,'PROJECT_ROOT',tmp_path)
    v=view();v['approved_direct_fields'].pop()
    at=AppTest.from_function(app);at.session_state['test_view']=v;at.run()
    at.button(key='sec-review-save:test:NEM').click().run()
    at.radio[0].set_value('monitor').run()
    assert not at.exception
    assert '资本支出' in '\n'.join(x.value for x in at.markdown)
    assert not (tmp_path/'data').exists()


def test_nem_monitor_pins_pair_and_persists_disposition(tmp_path, monkeypatch):
    from src import sec_research_review_ui as ui
    from src.research_workspace import MonitorOrigin
    from src.sec_research_review import capture_review, save_review

    monkeypatch.setattr(ui, 'PROJECT_ROOT', tmp_path)
    first, second = (capture_review(view(), profile_key='test', saved_at=stamp)
                     for stamp in ('2026-11-02T22:00:00Z', '2026-11-02T22:01:00Z'))
    original = {path: path.read_bytes() for path in (save_review(first, tmp_path), save_review(second, tmp_path))}
    at = AppTest.from_function(app)
    at.session_state['test_view'] = {'status': 'not_requested'}
    at.session_state['test_monitor_origin'] = MonitorOrigin('test', 'NEM', 'notes', '0001164727')
    at.run().radio[0].set_value('monitor').run()
    at.button('sec-review-open-pair').click().run()
    token = first['receipt_id'] + '.' + second['receipt_id']
    assert at.query_params['sec_pair'] == [token]
    assert 'online' not in at.query_params

    online = AppTest.from_function(app)
    online.session_state['test_view'] = {'status': 'not_requested'}
    online.query_params.update(sec_pair=token, online='1')
    online.run()
    assert online.warning
    assert not any('已固定的 SEC 证据比较' in e.value for e in online.markdown)

    third = capture_review(view(), profile_key='test', saved_at='2026-11-02T22:02:00Z')
    save_review(third, tmp_path)
    at.radio[0].set_value('company').run()
    visible = '\n'.join(e.value for e in at.caption)
    assert first['receipt_id'] in visible and second['receipt_id'] in visible
    assert third['receipt_id'] not in visible
    assert any('未变化' in e.value for e in at.success)

    at.radio[0].set_value('monitor').run()
    at.radio[1].set_value('still_open')
    next(b for b in at.button if b.label == '保存复核状态').click().run()
    assert at.error
    at.text_area[0].set_value('  Keep the source gap open.  ')
    next(b for b in at.button if b.label == '保存复核状态').click().run()
    assert any('Keep the source gap open.' == e.value for e in at.text)
    assert not at.exception

    fresh = AppTest.from_function(app)
    fresh.session_state['test_view'] = {'status': 'not_requested'}
    fresh.query_params['sec_pair'] = token
    fresh.run().radio[0].set_value('monitor').run()
    assert any('Keep the source gap open.' == e.value for e in fresh.text)
    fresh.radio[1].set_value('reviewed')
    fresh.text_area[0].set_value('Reviewed the evidence.')
    next(b for b in fresh.button if b.label == '保存复核状态').click().run()
    assert any('Reviewed the evidence.' == e.value for e in fresh.text)
    assert all(path.read_bytes() == raw for path, raw in original.items())

    fresh.query_params['sec_pair'] = first['receipt_id'] + '.' + 'f' * 64
    fresh.run()
    assert fresh.warning
    assert not any(b.label == '保存复核状态' for b in fresh.button)


def test_other_company_without_observation_has_disabled_receipt_controls(tmp_path,monkeypatch):
    from src import sec_research_review_ui as ui
    monkeypatch.setattr(ui,'PROJECT_ROOT',tmp_path)
    def other():
        import streamlit as st
        from src.sec_research_review_ui import render_company_review
        render_company_review(st,'AMD',{},profile_key='test')
    at=AppTest.from_function(other).run()
    assert not at.exception
    assert at.button(key='sec-review-save:test:AMD').disabled
    assert not any('核查营业利润原始申报'==b.label for b in at.button)


def test_normal_nem_company_route_exposes_receipts_without_fetch(tmp_path,monkeypatch):
    from src import sec_research_review_ui as ui
    from src.sec_research_review import capture_review,save_review
    monkeypatch.setattr(ui,'PROJECT_ROOT',tmp_path)
    p=capture_review(view(),profile_key='test');save_review(p,tmp_path)
    def workbench():
        import streamlit as st
        from src.company_workbench_ui import render_integrated_company
        render_integrated_company(st,'NEM',profile_scope='test',saved_available=False,
            render_saved=lambda section:None,render_sources=lambda bundle:None)
    at=AppTest.from_function(workbench);at.query_params['section']='notes';at.run()
    assert not at.exception
    assert at.button(key='sec-review-save:test:NEM').disabled
    assert at.selectbox[0].value==0
    assert any('SEC 财报证据复核' in x.value for x in at.markdown)


def test_exact_gap_check_save_replay_and_monitor(tmp_path,monkeypatch):
    from src import sec_research_review_ui as ui
    from tests.test_nem_operating_income_review import preview
    monkeypatch.setattr(ui,'PROJECT_ROOT',tmp_path)
    calls=[]
    def fetch(*args,**kwargs):
        calls.append(1);return preview()
    monkeypatch.setattr(ui,'get_company_filing_preview',fetch)
    v=view();v['approved_direct_fields']=[r for r in v['approved_direct_fields'] if r['field']!='operating_income']
    at=AppTest.from_function(app);at.session_state['test_view']=v;at.run()
    assert not calls
    at.button(key='sec-review-exact:test:NEM').click().run()
    assert not at.exception and len(calls)==1
    at.button(key='sec-review-save:test:NEM').click().run()
    at.button(key='sec-review-save:test:NEM').click().run()
    assert not at.exception and len(calls)==1
    assert any('未变化' in e.value for e in at.success)
    assert '没有匹配的标准营业利润直接事实' in '\n'.join(e.value for e in at.markdown)
    at.radio[0].set_value('monitor').run()
    assert 'nem-synthetic.htm' in '\n'.join(e.value for e in at.markdown)
    assert not (tmp_path/'data').exists()
    # Offline new session replays the exact provenance without transport.
    fresh=AppTest.from_function(app);fresh.session_state['test_view']={'status':'not_requested'};fresh.run()
    assert not fresh.exception and len(calls)==1
    assert 'nem-synthetic.htm' in '\n'.join(e.value for e in fresh.markdown)
    # Failed explicit refresh must clear the previous successful attachment.
    at.radio[0].set_value('company').run()
    monkeypatch.setattr(ui,'get_company_filing_preview',lambda *a,**k:{'status':'withheld','reason':'sec_filing_unavailable'})
    at.button(key='sec-review-exact:test:NEM').click().run()
    assert any('未接入' in e.value for e in at.warning)
    at.button(key='sec-review-save:test:NEM').click().run()
    from src.sec_research_review import list_reviews
    assert list_reviews(tmp_path,'test')[-1]['schema_version']=='sec-research-review-v1'


def test_cached_check_cannot_attach_to_changed_companyfacts_observation(tmp_path,monkeypatch):
    from src import sec_research_review_ui as ui
    from tests.test_nem_operating_income_review import preview
    from src.sec_research_review import list_reviews
    monkeypatch.setattr(ui,'PROJECT_ROOT',tmp_path)
    monkeypatch.setattr(ui,'get_company_filing_preview',lambda *a,**k:preview())
    v=view();v['approved_direct_fields']=[r for r in v['approved_direct_fields'] if r['field']!='operating_income']
    at=AppTest.from_function(app);at.session_state['test_view']=v;at.run()
    at.button(key='sec-review-exact:test:NEM').click().run()
    v['companyfacts_identity']['payload_sha256']='f'*64;at.session_state['test_view']=v;at.run()
    at.button(key='sec-review-save:test:NEM').click().run()
    assert list_reviews(tmp_path,'test')[-1]['schema_version']=='sec-research-review-v1'
