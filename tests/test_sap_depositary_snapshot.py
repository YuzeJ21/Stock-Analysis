"""Replay requires the reviewed SAP literal, not just self-consistent numbers."""
from copy import deepcopy

import pytest

from sap_depositary_fixtures import research_context
from src.online_research_context_store import save_research_context, load_research_context, compare_research_contexts


def _scope(value):
    return {k: value[k] for k in ('profile_key', 'ticker', 'sec_cik')}


def test_sap_native_basis_saves_reopens_and_renders_as_exact_withheld_history(tmp_path):
    from src import online_peer_valuation_ui as ui

    value = research_context()
    before = deepcopy(value)
    saved = save_research_context(value, **_scope(value), project_root=tmp_path)
    reopened = load_research_context(saved['snapshot_id'], **_scope(value), project_root=tmp_path)
    assert value == before and reopened['context'] == before
    assert reopened['historical'] is True and reopened['current'] is False
    assert compare_research_contexts(value, reopened)['status'] == 'unchanged'
    html = ui.saved_depositary_security_html(reopened['context'])
    assert 'Saved SAP filing evidence' in html and '6.10 EUR/common share' in html
    assert '1 ordinary shares/ADR' in html and 'ADS valuation remains withheld.' in html
    assert '2025-12-31' in html and '2026-02-26' in html and '2026-11-08' in html
    assert 'otherlisted.txt' in html
    assert '6.10 USD' not in html and '6.10 EUR/ADS' not in html


@pytest.mark.parametrize('issue', [
    'consistent_edited_literal', 'ratio', 'boolean_ratio', 'currency', 'context', 'dimension',
    'fact_source', 'period', 'entity', 'owner_cik', 'listing_type', 'listing_ticker', 'listing_title',
    'missing_listing', 'body_digest', 'future_document', 'future_listing', 'future_profile',
    'eligible', 'commercial', 'valuation', 'missing_observation', 'inventory', 'detached', 'old_policy', 'raw_body',
])
def test_resealed_edits_cannot_gain_sap_numeric_replay_permission(tmp_path, issue):
    value = research_context()
    peer = value['peer_read_through']
    owner = peer['subject_source_context']
    evidence = owner['selected_security_scope']
    ratio, _, eps = evidence['evidence_observations']
    if issue == 'consistent_edited_literal': eps.update(raw_text='6.20', value=6.2)
    elif issue == 'ratio': ratio['value'] = 2
    elif issue == 'boolean_ratio': ratio['value'] = True
    elif issue == 'currency': eps['unit'] = 'USD/shares'
    elif issue == 'context': eps['context_id'] = 'other'
    elif issue == 'dimension': eps['dimensions'] = [['extra', 'dimension', 'other', 'share']]
    elif issue == 'fact_source': eps['source_ref'] += '-other'
    elif issue == 'period': eps['period_end'] = '2024-12-31'
    elif issue == 'entity': eps['entity_cik'] = '0000001111'
    elif issue == 'owner_cik': owner['sec_cik'] = '0000001111'
    elif issue == 'listing_type': owner['selected_depositary_listing']['security_type'] = 'common_shares'
    elif issue == 'listing_ticker': owner['selected_depositary_listing']['ticker'] = 'SAPGF'
    elif issue == 'listing_title': owner['selected_depositary_listing']['description'] = 'SAP Common Stock'
    elif issue == 'missing_listing': owner.pop('selected_depositary_listing')
    elif issue == 'body_digest': evidence['documents'][0]['body_sha256'] = '0' * 64
    elif issue == 'future_document': evidence['documents'][0]['observed_at'] = '2026-11-09T12:00:00Z'
    elif issue == 'future_listing': owner['selected_depositary_listing']['observed_at'] = '2026-11-09T12:00:00Z'
    elif issue == 'future_profile': owner['profile_observed_at'] = '2026-11-09T12:00:00Z'
    elif issue == 'eligible': eps['financial_eligible'] = True
    elif issue == 'commercial': evidence['commercial_eligible'] = True
    elif issue == 'valuation': peer.update(status='research_comparison', peer_median=20)
    elif issue == 'missing_observation': evidence['evidence_observations'].pop()
    elif issue == 'inventory': value['filing_inventory'] = {}
    elif issue == 'detached': value['notes'] = owner.pop('selected_security_scope')
    elif issue == 'old_policy': evidence['policy_id'] = 'sap-nyse-ads-2026-v1'
    else: eps['raw_body'] = '<html>not a token</html>'
    with pytest.raises(ValueError):
        save_research_context(value, **_scope(value), project_root=tmp_path)
    assert not list(tmp_path.iterdir())


def test_legacy_note_only_sap_snapshots_remain_unchanged(tmp_path):
    value = research_context()
    scope = value['peer_read_through']['subject_source_context']['selected_security_scope']
    scope['policy_id'] = 'sap-nyse-ads-2026-v1'
    scope['evidence_observations'].pop()
    scope['evidence_observations'][0].pop('value')
    scope['evidence_observations'][0].pop('unit')
    scope['evidence_observations'][0]['label'] = 'NYSE ADS listing and one ordinary share per ADS'
    saved = save_research_context(value, **_scope(value), project_root=tmp_path)
    reopened = load_research_context(saved['snapshot_id'], **_scope(value), project_root=tmp_path)
    assert reopened['context'] == value
    assert len(scope['evidence_observations']) == 2


@pytest.mark.parametrize('issue', ['peer_ticker', 'peer_commercial', 'peer_readiness', 'peer_rights',
    'future_directory_clock', 'stale_directory_clock', 'directory_receipt_digest', 'missing_directory_context',
    'profile_before_filing', 'annual_lead', 'facts_lead'])
def test_review_parent_permission_chronology_and_source_conflicts_fail_closed(tmp_path, issue):
    value = research_context()
    peer = value['peer_read_through']
    owner = peer['subject_source_context']
    listing = owner['selected_depositary_listing']
    if issue == 'peer_ticker': peer['ticker'] = 'TSM'
    elif issue == 'peer_commercial': peer['commercial_eligible'] = True
    elif issue == 'peer_readiness': peer['saved_readiness_promoted'] = True
    elif issue == 'peer_rights': peer['rights_status'] = 'commercially_licensed'
    elif issue == 'future_directory_clock': listing['source_created_at'] = '2026-11-08T23:59'
    elif issue == 'stale_directory_clock': listing['source_created_at'] = '2016-11-08T06:59'
    elif issue == 'directory_receipt_digest': peer['listing_context']['source_receipts'][0]['payload_sha256'] = '0' * 64
    elif issue == 'missing_directory_context': peer.pop('listing_context')
    elif issue == 'profile_before_filing': owner['profile_observed_at'] = '2020-01-01T00:00:00Z'
    elif issue == 'annual_lead': owner['annual_versions'][0]['period_end'] = '2024-12-31'
    else: owner['facts_query_ref'] = 'https://data.sec.gov/api/xbrl/companyfacts/CIK0001046179.json'
    with pytest.raises(ValueError):
        save_research_context(value, **_scope(value), project_root=tmp_path)


@pytest.mark.parametrize('policy_id', ['sap-nyse-ads-2026-v1', 'unknown', None])
def test_review_resealed_legacy_numeric_record_cannot_render_invented_usd_ads(tmp_path, policy_id):
    from src import online_research_context_store as store

    original = research_context()
    saved = save_research_context(original, **_scope(original), project_root=tmp_path)
    changed = deepcopy(original)
    scope = changed['peer_read_through']['subject_source_context']['selected_security_scope']
    scope['policy_id'] = policy_id
    eps = scope['evidence_observations'][-1]
    eps.pop('raw_text')
    eps.update(value=61.7, unit='USD/shares', security_basis='ADS')
    forged = store._snapshot(changed)
    directory = next(tmp_path.rglob(saved['snapshot_id'] + '.json')).parent
    path = directory / (forged['snapshot_id'] + '.json')
    path.write_bytes(store._json(forged))
    with pytest.raises(ValueError):
        load_research_context(forged['snapshot_id'], **_scope(original), project_root=tmp_path)
    assert load_research_context(saved['snapshot_id'], **_scope(original), project_root=tmp_path)['context'] == original


def test_actual_save_monitor_and_historical_renderers_keep_sap_basis_visible(monkeypatch, tmp_path):
    from streamlit.testing.v1 import AppTest
    from sap_depositary_fixtures import write_replay_app
    from src import online_research_tools_ui as ui
    from src import online_research_context_store as store
    import socket

    monkeypatch.setattr(ui, 'PROJECT_ROOT', tmp_path)
    monkeypatch.setattr(store, 'PROJECT_ROOT', tmp_path)
    monkeypatch.setattr(socket.socket, 'connect', socket.socket.connect)
    app_file = str(write_replay_app(tmp_path))
    app = AppTest.from_file(app_file, default_timeout=45).run()
    assert not app.exception
    app.button(key='online-research-save').click().run()
    assert not app.exception and len(app.success) == 1
    app.button(key='online-research-replay-open').click().run()
    first = app.query_params['research_snapshot'][0]
    # Reload the saved URL in a fresh session. Older local AppTest retains the
    # outgoing selectbox after the production handler's explicit st.rerun().
    # The browser test covers the continuous section-navigation interaction.
    app = AppTest.from_file(app_file, default_timeout=45)
    app.query_params.update(mode='research', page='company-workbench', ticker='SAP',
        research_snapshot=first, research_cik='0001000184', section='sources')
    app.run()
    assert not app.exception
    assert any('Saved SAP filing evidence' in row.value for row in app.markdown)
    decoy = research_context()
    decoy['observed_at'] = '2026-11-08T13:00:00Z'
    decoy['notes'] = {'thesis': 'A newer decoy must not replace the selected snapshot.'}
    second = save_research_context(decoy, **_scope(decoy), project_root=tmp_path)
    assert second['snapshot_id'] != first
    app.button(key='online-research-replay-monitor').click().run()
    assert not app.exception and app.query_params['page'] == ['monitor']
    assert any('Saved SAP filing evidence' in row.value and '6.10 EUR/common share' in row.value for row in app.markdown)
    assert app.query_params['return_research_snapshot'] == [first]
    next(button for button in app.button if button.label == 'Reopen exact saved research').click().run()
    assert not app.exception and app.query_params.get('research_snapshot')
    assert app.query_params['research_snapshot'] == [first] and app.query_params['section'] == ['sources']
    assert any('Saved SAP filing evidence' in row.value and '6.10 EUR/common share' in row.value for row in app.markdown)
    assert not (tmp_path / 'server-provider-attempts.txt').exists()


@pytest.mark.parametrize('section', ['overview', 'valuation'])
def test_historical_workbench_does_not_present_invented_sap_usd_earnings(tmp_path, section):
    from streamlit.testing.v1 import AppTest
    from src import online_research_context_store as store
    import json

    value = research_context()
    value['business_trend']['narrative'] = ['Independent financial evidence remains available.']
    scope = value['peer_read_through']['subject_source_context']['selected_security_scope']
    scope['policy_id'] = 'sap-nyse-ads-2026-v1'
    eps = scope['evidence_observations'][-1]
    eps.pop('raw_text')
    eps.update(value=61.7, unit='USD/shares', security_basis='ADS')
    path = tmp_path / 'untrusted.json'
    path.write_text(json.dumps(store._snapshot(value)))
    code = f'''import json
import streamlit as st
from pathlib import Path
from src.company_workbench_ui import render_saved_company_replay
st.query_params["section"] = {section!r}
render_saved_company_replay(st, json.loads(Path({str(path)!r}).read_text()))
'''
    app = AppTest.from_string(code, default_timeout=45).run()
    assert not app.exception
    assert not any('61.7 USD/ADS' in row.value for row in app.markdown)
    assert any('could not be verified' in row.value for row in app.warning)
    if section == 'overview':
        assert any('Independent financial evidence remains available.' in row.value for row in app.markdown)
