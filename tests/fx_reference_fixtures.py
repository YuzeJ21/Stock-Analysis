"""Constructed ECB-format source, never a claim of an actual captured rate."""
from datetime import datetime, timezone

NOW = datetime(2026, 11, 9, 12, tzinfo=timezone.utc)
URL = 'https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml'
XML = b'''<?xml version="1.0" encoding="UTF-8"?>
<gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01"
 xmlns="http://www.ecb.int/vocabulary/2002-08-01/eurofxref">
<gesmes:subject>Reference rates</gesmes:subject>
<gesmes:Sender><gesmes:name>European Central Bank</gesmes:name></gesmes:Sender>
<Cube><Cube time="2026-11-06"><Cube currency="USD" rate="1.2500"/>
<Cube currency="CAD" rate="1.5000"/></Cube></Cube></gesmes:Envelope>'''


def captured():
    from src.ecb_fx_reference import capture_ecb_usd
    return capture_ecb_usd('2026-11-06', fetcher=lambda url:(XML, {}, URL), clock=lambda:NOW)


def write_fx_review_app(root):
    from pathlib import Path
    project = Path(__file__).resolve().parents[1]
    app = root / 'src' / 'dashboard.py'
    app.parent.mkdir(parents=True, exist_ok=True)
    app.write_text(f'''import sys
from pathlib import Path
sys.path[:0] = [{str(project)!r}, {str(project/'tests')!r}]
import streamlit as st
from fx_reference_fixtures import XML, URL, NOW
from sap_depositary_fixtures import priced_research_context, install_provider_guard
from src import ecb_fx_reference as fx
from src import online_research_tools_ui as ui, online_research_context_store as store
from src.company_workbench_ui import render_saved_company_replay
from src.online_research_context_store import save_research_context
install_provider_guard(Path({str(root)!r}))
st.set_page_config(layout="wide")
view = st.selectbox('View', ['valuation', 'sources', 'saved valuation', 'saved sources', 'monitor'])
value = priced_research_context()
value['profile_key'] = st.selectbox('Profile', ['one', 'two'])
value['notes'] = {{'thesis':'private-thesis-unique'}}
def fetch(url):
    assert url == URL
    with Path({str(root/'calls.txt')!r}).open('a') as handle: handle.write('fetch\\n')
    return XML, {{}}, URL
fx._fetch = fetch
ui.PROJECT_ROOT = store.PROJECT_ROOT = Path({str(root)!r})
if view == 'monitor':
    ui.render_online_research_monitor(st, profile_key=value['profile_key'])
elif view.startswith('saved '):
    snapshot = save_research_context(value, project_root=ui.PROJECT_ROOT,
        **{{key:value[key] for key in ('profile_key','ticker','sec_cik')}})
    st.query_params['section'] = view.split(' ', 1)[1]
    render_saved_company_replay(st, snapshot)
else:
    ui.render_online_tools(st, view, {{'research_context':value, 'online_scenario_key':'fixture-fx-scenario'}})
''')
    return app
