"""Synthetic distinct security/currency observations; never a valuation input."""
from copy import deepcopy
import hashlib
import pytest
from selected_security_fixtures import fixture


def observation_fixture():
    _,_,_,raw=fixture();body=raw['annual'].replace(b'xmlns:dei=',b'xmlns:f="https://xbrl.ifrs.org/taxonomy/2025-03-27/ifrs-full" xmlns:e="https://example.test/2025" xmlns:dei=',1)
    extra=b'''<x:context id="ads"><x:entity><x:identifier scheme="http://www.sec.gov/CIK">0000001001</x:identifier><x:segment><d:explicitMember dimension="f:ClassesOfShareCapitalAxis">e:ADSMember</d:explicitMember></x:segment></x:entity><x:period><x:startDate>2025-01-01</x:startDate><x:endDate>2025-12-31</x:endDate></x:period></x:context><x:unit id="twd"><x:divide><x:unitNumerator><x:measure>iso:TWD</x:measure></x:unitNumerator><x:unitDenominator><x:measure>x:shares</x:measure></x:unitDenominator></x:divide></x:unit><ix:nonFraction id="ads-native" name="f:DilutedEarningsLossPerShare" contextRef="ads" unitRef="twd" decimals="2">15.21</ix:nonFraction><ix:nonFraction id="ads-usd" name="f:DilutedEarningsLossPerShare" contextRef="ads" unitRef="eps" decimals="2">0.49</ix:nonFraction><ix:nonNumeric id="fx-note" name="f:DisclosureOfEffectOfChangesInForeignExchangeRatesExplanatory" contextRef="base" continuedAt="note-tail">Convenience presentation</ix:nonNumeric><ix:continuation id="note-tail">Native accounts; no market FX conversion.</ix:continuation><div>Each wrapper represents five shares.</div>'''
    body=body.replace(b'</html>',extra+b'</html>')
    ctx=dict(context_id='ads',entity_cik='0000001001',period_start='2025-01-01',period_end='2025-12-31',dimensions=[['https://xbrl.ifrs.org/taxonomy/2025-03-27/ifrs-full','ClassesOfShareCapitalAxis','https://example.test/2025','ADSMember']])
    ns='https://xbrl.ifrs.org/taxonomy/2025-03-27/ifrs-full'
    c=[dict(kind='numeric',label='ADS native diluted EPS',fact_id='ads-native',namespace_uri=ns,concept='DilutedEarningsLossPerShare',unit_id='twd',currency='TWD',security_basis='ADS',currency_basis='native',**ctx),dict(kind='numeric',label='ADS convenience diluted EPS',fact_id='ads-usd',namespace_uri=ns,concept='DilutedEarningsLossPerShare',unit_id='eps',currency='USD',security_basis='ADS',currency_basis='convenience',**ctx)]
    c.append(dict(kind='note',label='Convenience basis',fact_id='fx-note',namespace_uri=ns,concept='DisclosureOfEffectOfChangesInForeignExchangeRatesExplanatory',context_id='base',entity_cik='0000001001',period_start='2025-01-01',period_end='2025-12-31',dimensions=[],continuations=['note-tail']))
    text='Each wrapper represents five shares.'
    c.append(dict(kind='element_note',label='Wrapper ratio disclosure',path='/html[1]/div[1]',text_sha256=hashlib.sha256(text.encode()).hexdigest()))
    return body,c


def parse(body,contracts):
    from src.sec_security_observations import inspect_observations
    return inspect_observations(body,cik='0000001001',metadata={'reportDate':'2025-12-31'},url='https://www.sec.gov/Archives/edgar/data/1001/000000100126000001/annual.htm',contracts=contracts)


def test_direct_ads_native_and_convenience_facts_keep_distinct_source_context_and_units():
    body,contracts=observation_fixture();r=parse(body,contracts)
    assert [o['value'] for o in r[:2]]==[15.21,0.49]
    assert [o['unit'] for o in r[:2]]==['TWD/shares','USD/shares']
    assert [o['currency_basis'] for o in r[:2]]==['native','convenience']
    assert r[0]['security_basis']=='ADS' and r[0]['context_source_ref'].endswith('#ads') and r[0]['unit_source_ref'].endswith('#twd')
    assert r[2]['source_refs'][-1].endswith('#note-tail') and r[3]['location']=='/html[1]/div[1]'
    assert all(o['financial_eligible'] is False for o in r)


@pytest.mark.parametrize('tag', ['identifier', 'startDate', 'endDate'])
def test_inspection_context_primitives_cannot_hide_nested_markup(tag):
    body,contracts=observation_fixture();closing=f'</x:{tag}>'.encode()
    with pytest.raises(ValueError):
        parse(body.replace(closing,b'<span>ignored content</span>'+closing),contracts)


@pytest.mark.parametrize('old,new',[
    (b'e:ADSMember',b'e:OrdinaryMember'),(b'iso:TWD',b'iso:USD'),(b'2025-01-01',b'2024-01-01'),
    (b'0000001001</x:identifier>',b'0000009999</x:identifier>'),
    (b'f:DilutedEarningsLossPerShare',b'f:BasicEarningsLossPerShare'),
    (b'contextRef="ads"',b'contextRef="base"'),
    (b'id="ads-native"',b'id="ads-native" continuedAt="other"'),
    (b'<x:segment>',b'<x:segment><d:typedMember dimension="e:Other"><value>x</value></d:typedMember>'),
    (b'</x:entity>',b'<x:scenario/></x:entity>'),
    (b'id="note-tail"',b'id="note-tail" continuedAt="fx-note"'),
    (b'id="note-tail"',b'id="missing"'),
    (b'Each wrapper',b'Different wrapper'),
])
def test_changed_class_currency_period_entity_fact_or_note_chain_cannot_survive_resealing(old,new):
    body,contracts=observation_fixture()
    with pytest.raises(ValueError):parse(body.replace(old,new),contracts)


def test_extra_ads_dimension_and_unsupported_numeric_markup_are_rejected():
    body,contracts=observation_fixture()
    with pytest.raises(ValueError):parse(body.replace(b'</x:segment>',b'<d:explicitMember dimension="e:OtherAxis">e:OtherMember</d:explicitMember></x:segment>'),contracts)
    with pytest.raises(ValueError):parse(body.replace(b'>15.21</ix:nonFraction>',b'><table><tr><td>15.21</td></tr></table></ix:nonFraction>'),contracts)


def test_html_paragraph_is_an_exact_source_location_not_an_invented_fragment():
    body=b'<html><body><p>First &amp; only</p><p>Second&nbsp;paragraph</p></body></html>'
    c=[dict(kind='html_paragraph',label='Successor evidence',paragraph_ordinal=2,text_sha256=hashlib.sha256('Second paragraph'.encode()).hexdigest())]
    r=parse(body,c)[0]
    assert r['source_ref'].endswith('annual.htm') and r['location']=='p[2]' and r['financial_eligible'] is False
    with pytest.raises(ValueError):parse(body.replace(b'Second',b'Other'),c)
    with pytest.raises(ValueError):parse(body,[{**c[0],'paragraph_ordinal':3}])


def test_inspection_scope_cannot_promote_direct_ads_observations_to_common_earnings(monkeypatch):
    from selected_security_fixtures import scoped_collection,install
    from test_online_peer_valuation import build
    policy,c=scoped_collection();policy.update(kind='inspection_only',reason='depositary_security_requires_separate_method');doc=policy['documents']['annual'];packet=c['issuers'][0]['selected_security_evidence']['documents']['annual']
    import base64
    body,contracts=observation_fixture();doc['sha256']=hashlib.sha256(body).hexdigest();doc['inspection_observations']=contracts;packet.update(payload_sha256=doc['sha256'],payload_raw_base64=base64.b64encode(body).decode());install(monkeypatch,policy)
    v=build(c);scope=v['subject_source_context']['selected_security_scope']
    assert scope['evidence_observations'][0]['value']==15.21 and 'original_eps' not in scope
    assert v['subject'] is None and v['premium_fraction'] is None


def test_ads_ratio_is_parsed_from_bound_disclosure_without_multiplying_rounded_eps():
    body,contracts=observation_fixture();body=body.replace(b'Each wrapper represents five shares.',b'Each ADS represents seven (7) common shares.')
    c=contracts[-1];c.update(extract='ads_common_ratio',text_sha256=hashlib.sha256(b'Each ADS represents seven (7) common shares.').hexdigest())
    r=parse(body,[c])[0]
    assert r['value']==7 and r['unit']=='ordinary_shares/ADS' and r['financial_eligible'] is False
    assert 'eps' not in r
