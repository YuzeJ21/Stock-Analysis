"""Real Streamlit interaction; only the external transport is replaced."""
from pathlib import Path
import json
import pytest

from streamlit.testing.v1 import AppTest
from test_workspace_authorization import configured


def app_source(tmp_path):
    return f'''from pathlib import Path
import streamlit as st
from fx_reference_fixtures import XML, URL, NOW
from sap_depositary_fixtures import priced_research_context
from src.sap_fx_review_ui import render_sap_fx_review
value = priced_research_context()
value['profile_key'] = st.selectbox('Profile', ['one', 'two'])
st.selectbox('View', ['valuation', 'sources'])
def fetch(url):
    assert url == URL
    with Path({str(tmp_path/'calls.txt')!r}).open('a') as handle: handle.write('fetch\\n')
    return XML, {{}}, URL
render_sap_fx_review(st, value, fetcher=fetch, clock=lambda:NOW)
'''


def test_render_and_route_changes_do_not_fetch_but_explicit_action_reuses_exact_context(tmp_path):
    app = AppTest.from_string(app_source(tmp_path), default_timeout=45).run()
    assert not app.exception and not (tmp_path/'calls.txt').exists()
    next(button for button in app.button if button.label == 'Fetch FX reference').click().run()
    assert not app.exception
    assert (tmp_path/'calls.txt').read_text().splitlines() == ['fetch']
    assert any('7.625000 USD/ordinary share' in row.value for row in app.markdown)
    app.run()
    next(box for box in app.selectbox if box.label == 'View').select('sources').run()
    assert (tmp_path/'calls.txt').read_text().splitlines() == ['fetch']
    assert any('7.625000 USD/ordinary share' in row.value for row in app.markdown)
    next(box for box in app.selectbox if box.label == 'Profile').select('two').run()
    assert not any('7.625000 USD/ordinary share' in row.value for row in app.markdown)
    assert (tmp_path/'calls.txt').read_text().splitlines() == ['fetch']


def test_unmatched_price_basis_disables_source_action():
    app = AppTest.from_string('''import streamlit as st
from sap_depositary_fixtures import research_context
from src.sap_fx_review_ui import render_sap_fx_review
render_sap_fx_review(st, research_context())
''', default_timeout=45).run()
    assert not app.exception
    button = next(button for button in app.button if button.label == 'Fetch FX reference')
    assert button.disabled


def test_current_sources_exposes_separate_currency_review_without_automatic_transport():
    app = AppTest.from_string('''import streamlit as st
from sap_depositary_fixtures import priced_research_context
from src.online_research_tools_ui import render_online_tools
render_online_tools(st,'sources',{'research_context':priced_research_context()})
''', default_timeout=45).run()
    assert not app.exception
    assert any(button.label == 'Fetch FX reference' for button in app.button)


@pytest.mark.parametrize('role',['viewer','editor','owner'])
def test_protected_ui_does_not_build_or_register_a_currency_download(configured,role,tmp_path,monkeypatch):
    from src import sap_fx_review_ui as ui
    path,config,_=configured
    config['workspaces']['alpha']['members'][0]['role']=role
    path.write_text(json.dumps(config))
    monkeypatch.delenv('COMMERCIAL_RESEARCH_MODE',raising=False)
    def forbidden_package(*args,**kwargs): raise AssertionError('Protected UI built export')
    monkeypatch.setattr(ui,'currency_review_zip',forbidden_package)
    source=app_source(tmp_path).replace("value['profile_key'] = st.selectbox('Profile', ['one', 'two'])",
                                        "value['profile_key'] = 'workspace-alpha'")
    app=AppTest.from_string(source,default_timeout=45).run()
    next(button for button in app.button if button.label=='Fetch FX reference').click().run()
    assert not app.exception
    assert any('7.625000 USD/ordinary share' in row.value for row in app.markdown)
    assert not any('Download currency review' in str(getattr(row,'label','')) for row in app.get('download_button'))


def test_actual_current_and_saved_sections_reuse_review_and_monitor_has_no_fx_action(tmp_path,monkeypatch):
    import socket
    from src import ecb_fx_reference as fx,online_research_tools_ui as ui,online_research_context_store as store
    from fx_reference_fixtures import write_fx_review_app
    monkeypatch.setattr(socket.socket,'connect',socket.socket.connect)
    monkeypatch.setattr(fx,'_fetch',fx._fetch)
    monkeypatch.setattr(ui,'PROJECT_ROOT',ui.PROJECT_ROOT)
    monkeypatch.setattr(store,'PROJECT_ROOT',store.PROJECT_ROOT)
    app=AppTest.from_file(str(write_fx_review_app(tmp_path)),default_timeout=45).run()
    assert not app.exception and not (tmp_path/'calls.txt').exists()
    next(button for button in app.button if button.label=='Fetch FX reference').click().run()
    assert not app.exception
    for view in ('sources','saved valuation','saved sources'):
        next(box for box in app.radio if box.label=='View').set_value(view).run()
        assert not app.exception
        assert any('7.625000 USD/ordinary share' in row.value for row in app.markdown)
        assert (tmp_path/'calls.txt').read_text().splitlines()==['fetch']
    next(box for box in app.radio if box.label=='View').set_value('monitor').run()
    assert not app.exception
    assert not any(button.label=='Fetch FX reference' for button in app.button)
    assert not any('7.625000 USD/ordinary share' in row.value for row in app.markdown)
    assert (tmp_path/'calls.txt').read_text().splitlines()==['fetch']
