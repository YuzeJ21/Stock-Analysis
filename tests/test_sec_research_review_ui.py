"""Exercise explicit actions with disposable storage and synthetic SEC facts."""
from streamlit.testing.v1 import AppTest
from tests.test_sec_research_review import view


def app():
    import streamlit as st
    from src.sec_research_review_ui import render_company_review,render_review_monitor
    page=st.radio('Test route',['company','monitor'])
    if page=='company':render_company_review(st,'NEM',st.session_state['test_view'],profile_key='test')
    else:render_review_monitor(st,profile_key='test')


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


def test_non_nem_has_no_receipt_controls(tmp_path,monkeypatch):
    from src import sec_research_review_ui as ui
    monkeypatch.setattr(ui,'PROJECT_ROOT',tmp_path)
    def other():
        import streamlit as st
        from src.sec_research_review_ui import render_company_review
        render_company_review(st,'AMD',{},profile_key='test')
    at=AppTest.from_function(other).run()
    assert not at.button and not at.exception
