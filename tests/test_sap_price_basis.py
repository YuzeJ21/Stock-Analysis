"""A listing match cannot become an FX, issuer-ID, or valuation approval."""
from copy import deepcopy

import pytest

from sap_depositary_fixtures import priced_research_context


def assess(value):
    from src.sap_price_basis import assess_sap_price_basis
    return assess_sap_price_basis(value)


def test_exact_sap_listing_and_dated_usd_price_match_without_valuation_or_mutation():
    value = priced_research_context()
    before = deepcopy(value)
    result = assess(value)
    assert result['status'] == 'matched_listing_context'
    assert result['ticker'] == 'SAP' and result['sec_cik'] == '0001000184'
    assert result['price_date'] == '2026-11-06'
    assert result['valuation_eligible'] is False and result['commercial_eligible'] is False
    assert result['fx_status'] == result['vendor_issuer_identity_status'] == result['continuity_status'] == 'unverified'
    assert not {'pe', 'converted_eps', 'peer_median', 'premium'} & result.keys()
    assert value == before


@pytest.mark.parametrize('key,bad', [
    ('ticker','SAPGF'), ('provider_symbol','SAPGF'), ('currency','EUR'), ('source_id','unreviewed'),
    ('source_url','https://example.invalid/SAP'), ('instrument_type','ETF'), ('exchange_code','PNK'),
    ('full_exchange_name','OTC'), ('exchange_timezone','UTC'), ('payload_sha256','bad'),
    ('close',True), ('close',0), ('close',float('nan')), ('commercial_eligible',True),
    ('rights_status','approved'), ('observed_at','2026-11-09T12:00:00Z'),
    ('last_price_date','2026-11-08'), ('last_price_date','2026-11-09'),
])
def test_bad_price_identity_cannot_match_even_with_valid_sap_filing(key, bad):
    value = priced_research_context()
    value['price_context'][key] = bad
    assert assess(value)['status'] == 'withheld'


@pytest.mark.parametrize('change', ['missing_metadata','receipt_digest','duplicate_receipt','missing_receipt',
    'future_receipt','future_profile','old_price','before_close','wrong_issuer','bad_scope','promoted'])
def test_cross_source_binding_and_historical_cutoff_cannot_be_skipped(change):
    value = priced_research_context()
    price = value['price_context']
    if change == 'missing_metadata': price.pop('exchange_code')
    elif change == 'receipt_digest': value['source_receipts'][-1]['payload_sha256'] = 'b' * 64
    elif change == 'duplicate_receipt': value['source_receipts'].append(deepcopy(value['source_receipts'][-1]))
    elif change == 'missing_receipt': value['source_receipts'].pop()
    elif change == 'future_receipt': value['source_receipts'][-1]['observed_at'] = '2026-11-09T12:00:00Z'
    elif change == 'future_profile': value['peer_read_through']['subject_source_context']['profile_observed_at'] = '2026-11-09T12:00:00Z'
    elif change == 'old_price':
        price['observed_at'] = value['source_receipts'][-1]['observed_at'] = '2026-11-06T21:01:00Z'
    elif change == 'before_close':
        price['observed_at'] = value['source_receipts'][-1]['observed_at'] = '2026-11-06T20:59:00Z'
    elif change == 'wrong_issuer': value['sec_cik'] = '0000000001'
    elif change == 'bad_scope': value['peer_read_through']['subject_source_context']['selected_security_scope']['policy_id'] = 'unreviewed'
    else: value['saved_readiness_promoted'] = True
    assert assess(value)['status'] == 'withheld'


def test_match_is_recomputed_after_real_save_reload_and_missing_legacy_fields_stay_held(tmp_path):
    from src.online_research_context_store import save_research_context, load_research_context
    from src.online_peer_valuation_ui import saved_depositary_security_html
    value = priced_research_context()
    scope = {k:value[k] for k in ('ticker','sec_cik','profile_key')}
    saved = save_research_context(value, project_root=tmp_path, **scope)
    loaded = load_research_context(saved['snapshot_id'], project_root=tmp_path, **scope)
    assert assess(loaded['context'])['status'] == 'matched_listing_context'
    assert 'Selected NYSE ADS price context matched' in saved_depositary_security_html(loaded['context'])
    legacy = deepcopy(value)
    legacy['price_context'].pop('exchange_code')
    html = saved_depositary_security_html(legacy)
    assert 'Price listing context remains unverified' in html
    assert '6.10 EUR/common share' in html and 'ADS valuation remains withheld.' in html


def test_normalization_retains_price_identity_and_binds_it_to_semantic_revision():
    from datetime import datetime, timezone
    from src.online_research_tools import build_online_research_context
    price = priced_research_context()['price_context']
    price['bars'] = [dict(date=price['last_price_date'], close=price.pop('close'))]
    def build():
        return build_online_research_context({}, price, ticker='SAP', expected_cik='0001000184',
            profile_key='personal', as_of=datetime(2026,11,8,12,tzinfo=timezone.utc))
    value = build()
    assert value['price_context']['exchange_code'] == 'NYQ'
    assert value['price_context']['instrument_type'] == 'EQUITY'
    assert value['price_context']['rights_status'] == 'exact_source_unregistered_personal_inspection_only'
    receipt = next(row for row in value['source_receipts'] if row['source'] == 'daily_prices')
    assert receipt['price_identity']['last_price_date'] == '2026-11-06'
    assert receipt['price_identity']['close'] == 17.25
    assert receipt['price_identity']['exchange_code'] == 'NYQ'
    price['exchange_code'] = 'PNK'
    assert build()['source_revision'] != value['source_revision']


def test_current_sources_show_the_same_listing_basis_and_unresolved_fx():
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_string('''import streamlit as st
from sap_depositary_fixtures import priced_research_context
from src.online_research_tools_ui import render_online_tools
render_online_tools(st, 'sources', {'research_context': priced_research_context()})
''', default_timeout=45).run()
    assert not app.exception
    assert any('Selected NYSE ADS price context matched' in row.value for row in app.markdown)
    assert any('FX observation remains unverified' in row.value for row in app.markdown)


def test_default_saved_valuation_shows_the_price_basis_review(tmp_path):
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_string(f'''import streamlit as st
from pathlib import Path
from sap_depositary_fixtures import priced_research_context
from src.company_workbench_ui import render_saved_company_replay
from src.online_research_context_store import save_research_context
value = priced_research_context()
snapshot = save_research_context(value, project_root=Path({str(tmp_path)!r}),
    **{{k:value[k] for k in ('ticker','sec_cik','profile_key')}})
st.query_params['section'] = 'valuation'
render_saved_company_replay(st, snapshot)
''', default_timeout=45).run()
    assert not app.exception
    assert any('Selected NYSE ADS price context matched' in row.value for row in app.markdown)
    assert any('FX observation remains unverified' in row.value for row in app.markdown)


@pytest.mark.parametrize('shape', ['no_peer_scope', 'legacy_notes'])
def test_saved_legacy_research_has_the_same_safe_held_basis_as_current(shape):
    from src.online_peer_valuation_ui import sap_price_basis_html, saved_depositary_security_html
    value = priced_research_context()
    if shape == 'no_peer_scope':
        value['peer_read_through'] = dict(status='withheld', reason='online_peer_update_not_requested')
    else:
        scope = value['peer_read_through']['subject_source_context']['selected_security_scope']
        scope['policy_id'] = 'sap-nyse-ads-2026-v1'
        scope['evidence_observations'] = scope['evidence_observations'][:2]
        scope['evidence_observations'][0]['label'] = 'NYSE ADS listing and one ordinary share per ADS'
        scope['evidence_observations'][0].pop('value')
        scope['evidence_observations'][0].pop('unit')
    expected = 'Price listing context remains unverified'
    assert expected in sap_price_basis_html(value)
    assert expected in saved_depositary_security_html(value)


@pytest.mark.parametrize('key,changed', [('last_price_date','2026-11-05'), ('close',1)])
def test_resealed_price_edit_cannot_reuse_the_original_daily_receipt(tmp_path, key, changed):
    from src.online_research_context_store import save_research_context, load_research_context
    value = priced_research_context()
    value['price_context'][key] = changed
    scope = {k:value[k] for k in ('ticker','sec_cik','profile_key')}
    saved = save_research_context(value, project_root=tmp_path, **scope)
    loaded = load_research_context(saved['snapshot_id'], project_root=tmp_path, **scope)
    assert assess(loaded['context'])['status'] == 'withheld'


def test_missing_source_price_projection_keeps_price_basis_held():
    value = priced_research_context()
    value['source_receipts'][-1].pop('price_identity', None)
    assert assess(value)['status'] == 'withheld'
