"""A later reference translation never becomes reported EPS or historical eligibility."""
from copy import deepcopy
from datetime import datetime, timezone
from io import BytesIO
import json
from zipfile import ZipFile

import pytest

from fx_reference_fixtures import captured, NOW, XML
from sap_depositary_fixtures import priced_research_context
from test_workspace_authorization import configured


def review(context=None, packet=None, at=NOW):
    from src.sap_fx_review import build_sap_fx_review
    return build_sap_fx_review(context or priced_research_context(), packet or captured(), reviewed_at=at)


def test_exact_historical_ordinary_share_translation_keeps_original_and_later_times_separate():
    value, packet = priced_research_context(), captured()
    before = deepcopy(value)
    result = review(value, packet)
    assert result['status'] == 'derived_historical_translation'
    assert result['native_amount_decimal'] == '6.10'
    assert result['rate_literal'] == '1.2500'
    assert result['derived_amount_decimal'] == '7.625000'
    assert result['unit'] == 'USD/ordinary_share'
    assert result['original_observed_at'] == '2026-11-08T12:00:00Z'
    assert result['fx_observed_at'] == '2026-11-09T12:00:00Z'
    assert result['observation_after_original_cutoff'] is True
    assert result['first_publication_status'] == 'unverified'
    assert all(result[key] is False for key in ('valuation_eligible','commercial_eligible','point_in_time_eligible'))
    assert not {'pe', 'usd_eps', 'ads_eps', 'peer_median', 'premium'} & result.keys()
    assert value == before


@pytest.mark.parametrize('change', ['rate','direction','currency','date','digest','source','promotion','extra_receipt',
    'raw','future_receipt','future_context','before_review','naive_review','price_date','bad_price','bad_scope',
    'earlier_receipt','last_modified','private_revision','dict_revision','missing_profile'])
def test_wrong_or_relabelled_inputs_cannot_produce_a_currency_review(change):
    value, packet, at = priced_research_context(), captured(), NOW
    if change == 'rate': packet['receipt']['rate_literal'] = '9.9000'
    elif change == 'direction': packet['receipt']['quote_convention'] = 'EUR_per_USD'
    elif change == 'currency': packet['receipt']['base_currency'] = 'USD'
    elif change == 'date': packet['receipt']['reference_date'] = '2026-11-05'
    elif change == 'digest': packet['receipt']['payload_sha256'] = 'f' * 64
    elif change == 'source': packet['receipt']['source_url'] = 'https://example.invalid/'
    elif change == 'promotion': packet['receipt']['commercial_eligible'] = True
    elif change == 'extra_receipt': packet['receipt']['point_in_time_eligible'] = True
    elif change == 'raw': packet['xml'] = XML.replace(b'1.2500',b'9.9000')
    elif change == 'future_receipt': packet['receipt']['observed_at'] = '2026-11-10T12:00:00Z'
    elif change == 'future_context': value['observed_at'] = '2026-11-10T12:00:00Z'
    elif change == 'before_review': at = datetime(2026,11,8,12,tzinfo=timezone.utc)
    elif change == 'naive_review': at = datetime(2026,11,9,12)
    elif change == 'price_date':
        value['price_context']['last_price_date'] = '2026-11-05'
        value['source_receipts'][-1]['price_identity']['last_price_date'] = '2026-11-05'
    elif change == 'bad_price': value['price_context']['currency'] = 'EUR'
    elif change == 'earlier_receipt': packet['receipt']['observed_at'] = value['observed_at']
    elif change == 'last_modified': packet['receipt']['last_modified'] = 'private-marker'
    elif change == 'private_revision': value['source_revision'] = 'private-revision-marker'
    elif change == 'dict_revision': value['source_revision'] = {'private':'marker'}
    elif change == 'missing_profile': value.pop('profile_key')
    else: value['peer_read_through']['subject_source_context']['selected_security_scope']['policy_id'] = 'unreviewed'
    result = review(value, packet, at)
    assert result['status'] == 'withheld' and 'derived_amount_decimal' not in result


def test_download_contains_exact_public_source_and_minimal_review_without_private_notes():
    from src.sap_fx_review import currency_review_zip
    value = priced_research_context()
    value['profile_key'] = 'private-person-unique'
    value['notes'] = {'thesis':'private-thesis-unique'}
    body = currency_review_zip(value, captured(), reviewed_at=NOW)
    with ZipFile(BytesIO(body)) as archive:
        assert set(archive.namelist()) == {'fx.xml','receipt.json','SOURCE.txt','review.json'}
        assert archive.read('fx.xml') == XML
        result = json.loads(archive.read('review.json'))
        assert result['derived_amount_decimal'] == '7.625000'
        text = b'\n'.join(archive.read(name) for name in archive.namelist()).decode()
        assert 'private-person-unique' not in text and 'private-thesis-unique' not in text
        assert 'European Central Bank' in text and 'derived' in text
    value['price_context']['close'] = 1
    with pytest.raises(ValueError): currency_review_zip(value, captured(), reviewed_at=NOW)


def test_subsecond_later_retrieval_cannot_be_reported_before_original_cutoff():
    from src.ecb_fx_reference import capture_ecb_usd
    from fx_reference_fixtures import URL
    value=priced_research_context()
    value['observed_at']='2026-11-08T12:00:00.500000Z'
    packet=capture_ecb_usd('2026-11-06',fetcher=lambda url:(XML,{},URL),
        clock=lambda:datetime(2026,11,8,12,0,0,900000,tzinfo=timezone.utc))
    result=review(value,packet,datetime(2026,11,8,12,0,1,100000,tzinfo=timezone.utc))
    assert result['observation_after_original_cutoff'] is True
    assert result['fx_observed_at']=='2026-11-08T12:00:00.900000Z'
    assert result['reviewed_at']=='2026-11-08T12:00:01.100000Z'


@pytest.mark.parametrize('role',['viewer','editor','owner'])
def test_protected_currency_export_is_held_at_boundary_for_every_role(configured,role,monkeypatch):
    from src.sap_fx_review import currency_review_zip
    from src import workspace_authorization as access
    path,config,_=configured
    config['workspaces']['alpha']['members'][0]['role']=role
    path.write_text(json.dumps(config))
    monkeypatch.delenv('COMMERCIAL_RESEARCH_MODE',raising=False)
    assert access.require_workspace_access('workspace-alpha')
    value=priced_research_context();value['profile_key']='workspace-alpha'
    with pytest.raises(ValueError):currency_review_zip(value,captured(),reviewed_at=NOW)
