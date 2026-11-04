from copy import deepcopy
from datetime import timedelta
import base64,hashlib
import pytest

from selected_security_fixtures import fixture,install,validate,digest,NOW


def test_literal_selected_common_is_rederived_without_assigning_other_symbols(monkeypatch):
    policy,row,packet,_=fixture();install(monkeypatch,policy);before=deepcopy(packet)
    result=validate(policy,row,packet)
    assert result['status']=='supported_common' and result['original_eps']['eps']==1
    assert result['original_eps']['period_start']=='2025-01-01'
    assert result['issuer_symbols']==['FICT','FP'] and result['alias_mappings_established'] is False
    assert [d['selected_common']['ticker'] for d in result['documents']]==['FICT','FICT']
    assert result['commercial_eligible'] is False and packet==before


@pytest.mark.parametrize('change',[
    lambda p,r,s:s['documents']['annual'].update(payload_sha256='a'*64),
    lambda p,r,s:s['documents']['cover'].update(payload_raw_base64=base64.b64encode(b'changed').decode()),
    lambda p,r,s:s['documents']['cover'].update(source_url='https://www.sec.gov/elsewhere.htm'),
    lambda p,r,s:s['documents']['annual'].update(observed_at='2026-10-01T00:00:00Z'),
    lambda p,r,s:s['documents']['annual'].update(observed_at='2026-11-02T00:00:00Z'),
    lambda p,r,s:s.update(ticker='OTHER'),
    lambda p,r,s:r['profile']['payload']['tickers'].append('NEW'),
    lambda p,r,s:r['profile']['payload']['filings']['recent']['primaryDocument'].__setitem__(1,'new-cover.htm'),
])
def test_changed_source_or_current_identity_never_revives_a_scope(monkeypatch,change):
    policy,row,packet,_=fixture();change(policy,row,packet);row['profile']['normalized_sha256']=digest(row['profile']['payload']);install(monkeypatch,policy)
    assert validate(policy,row,packet)['status']=='withheld'


@pytest.mark.parametrize('mutate',[
    lambda raw:raw.replace(b'>FICT<',b'>OTHER<'),
    lambda raw:raw.replace(b'0000001001</x:identifier>',b'0000009999</x:identifier>'),
    lambda raw:raw.replace(b'<x:measure>iso:USD</x:measure>',b'<x:measure>iso:CAD</x:measure>'),
    lambda raw:raw.replace(b'>1</ix:nonFraction>',b'>2</ix:nonFraction>',1)+b'broken',
    lambda raw:raw.replace(b'g:CommonStockMember',b'g:OtherCommonMember'),
    lambda raw:raw.replace(b'id="note"',b'id="removed"'),
])
def test_resealed_documents_still_require_literal_context_unit_and_note_proof(monkeypatch,mutate):
    policy,row,packet,raw=fixture();changed=mutate(raw['annual']);sha=hashlib.sha256(changed).hexdigest();policy['documents']['annual']['sha256']=sha
    packet['documents']['annual'].update(payload_sha256=sha,payload_raw_base64=base64.b64encode(changed).decode());install(monkeypatch,policy)
    assert validate(policy,row,packet)['status']=='withheld'


def test_newer_cover_and_changed_issuer_set_withhold(monkeypatch):
    policy,row,packet,_=fixture();install(monkeypatch,policy)
    assert validate(policy,row,packet,issuer_symbols={'FICT','FP','FCOMMON'})['status']=='withheld'
    recent=row['profile']['payload']['filings']['recent']
    for key,values in recent.items():values.append('2026-10-29' if key in {'reportDate','filingDate'} else '2026-10-29T00:00:00Z' if key=='acceptanceDateTime' else '0000001001-26-000099' if key=='accessionNumber' else values[-1])
    row['profile']['normalized_sha256']=digest(row['profile']['payload'])
    assert validate(policy,row,packet)['status']=='withheld'


def test_common_title_alone_cannot_overrule_a_known_depositary_method_gap(monkeypatch):
    policy,row,packet,_=fixture();policy.update(kind='inspection_only',reason='depositary_security_requires_separate_method');install(monkeypatch,policy)
    result=validate(policy,row,packet)
    assert result['status']=='inspection_only' and result['reason']=='depositary_security_requires_separate_method'
    assert 'original_eps' not in result


@pytest.mark.parametrize('mode',['commercial','invalid'])
def test_mode_guard_precedes_any_source_request(monkeypatch,mode):
    from src.sec_selected_security import fetch_selected_security_evidence
    policy,row,_,_=fixture();install(monkeypatch,policy)
    def forbidden(*args):raise AssertionError('transport called')
    result=fetch_selected_security_evidence('FICT','0000001001',row['profile'],user_agent='Synthetic contact',fetcher=forbidden,observed_at=NOW,workspace_mode=mode)
    assert result['status']=='unavailable'


@pytest.mark.parametrize('failure',['redirect','oversize','exception'])
def test_failed_bounded_fetch_does_not_emit_supported_source(monkeypatch,failure):
    from src.sec_selected_security import fetch_selected_security_evidence
    policy,row,_,raw=fixture();install(monkeypatch,policy)
    def fetch(url,agent):
        if failure=='exception':raise OSError('source unavailable')
        return (b'x'*(32*1024*1024+1) if failure=='oversize' else raw['annual']),{},url+'/redirect' if failure=='redirect' else url
    assert fetch_selected_security_evidence('FICT','0000001001',row['profile'],user_agent='Synthetic contact',fetcher=fetch,observed_at=NOW)['status']=='unavailable'


def test_selected_security_evidence_qualifies_only_the_literal_common_eps(monkeypatch):
    from selected_security_fixtures import scoped_collection
    from test_online_peer_valuation import build
    policy,c=scoped_collection();install(monkeypatch,policy);result=build(c)
    assert result['subject']['multiple']==30 and result['peer_median']==25
    assert result['subject']['selected_security_scope']['alias_mappings_established'] is False
    c['issuers'][0]['facts']['payload']['facts']['us-gaap']['EarningsPerShareDiluted']['units']['USD/shares'][0]['val']=2
    assert build(c)['reason']=='selected_security_eps_conflict'


def test_a_genuine_other_common_listing_is_not_resolved_by_raw_symbol_count_override(monkeypatch):
    from selected_security_fixtures import scoped_collection
    from test_online_peer_valuation import build
    policy,c=scoped_collection(other_common=True);install(monkeypatch,policy)
    assert build(c)['subject'] is None


def test_unknown_wrapper_inspection_does_not_acquire_a_common_valuation(monkeypatch):
    from selected_security_fixtures import scoped_collection
    from test_online_peer_valuation import build
    policy,c=scoped_collection();policy.update(kind='inspection_only',reason='depositary_security_requires_separate_method');install(monkeypatch,policy)
    result=build(c)
    assert result['subject'] is None and result['reason']=='depositary_security_requires_separate_method'
    assert result['subject_source_context']['selected_security_scope']['status']=='inspection_only'


@pytest.mark.parametrize('change',[
    lambda r:r.replace(b'>Nasdaq<',b'>New York Stock Exchange LLC<'),
    lambda r:r.replace(b'</x:segment>',b'<d:typedMember dimension="g:OtherAxis"><value>other</value></d:typedMember></x:segment>'),
    lambda r:r.replace(b'id="symbol"',b'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:nil="true" id="symbol"'),
])
def test_scope_cannot_join_conflicting_exchange_extra_dimensions_or_nil_cover_facts(monkeypatch,change):
    from selected_security_fixtures import scoped_collection
    from test_online_peer_valuation import build
    policy,c=scoped_collection();packet=c['issuers'][0]['selected_security_evidence'];changed=change(base64.b64decode(packet['documents']['annual']['payload_raw_base64']));sha=hashlib.sha256(changed).hexdigest()
    policy['documents']['annual']['sha256']=sha;packet['documents']['annual'].update(payload_sha256=sha,payload_raw_base64=base64.b64encode(changed).decode());install(monkeypatch,policy)
    assert build(c)['subject'] is None


def test_new_unreviewed_filing_is_a_scope_gap_without_a_source_access_attempt(monkeypatch):
    from src.sec_selected_security import fetch_selected_security_evidence
    policy,row,_,_=fixture();install(monkeypatch,policy);row['profile']['payload']['filings']['recent']['primaryDocument'][1]='new.htm';row['profile']['normalized_sha256']=digest(row['profile']['payload'])
    def forbidden(*args):raise AssertionError('unreviewed scope fetched')
    result=fetch_selected_security_evidence('FICT','0000001001',row['profile'],user_agent='Synthetic contact',fetcher=forbidden,observed_at=NOW)
    assert result['status']=='not_applicable'


@pytest.mark.parametrize('variant',['exchange_name','legacy_date_transform'])
def test_exact_sec_cover_variants_keep_identity_dates_separate_from_financial_duration(monkeypatch,variant):
    policy,row,packet,raw=fixture()
    for role,body in raw.items():
        if variant=='exchange_name':body=body.replace(b'>Nasdaq<',b'>The New York Stock Exchange<')
        elif role=='cover':body=body.replace(b'<html ',b'<html xmlns:ixt="http://www.xbrl.org/inlineXBRL/transformation/2015-02-26" ',1).replace(b'name="dei:DocumentPeriodEndDate" contextRef="base">2026-10-20',b'format="ixt:datemonthdayyearen" name="dei:DocumentPeriodEndDate" contextRef="base">October 20, 2026')
        sha=hashlib.sha256(body).hexdigest();policy['documents'][role]['sha256']=sha;packet['documents'][role].update(payload_sha256=sha,payload_raw_base64=base64.b64encode(body).decode())
    if variant=='exchange_name':row['profile']['payload']['exchanges']=['NYSE','NYSE'];row['profile']['normalized_sha256']=digest(row['profile']['payload'])
    install(monkeypatch,policy);result=validate(policy,row,packet)
    assert result['status']=='supported_common' and result['original_eps']['period_start']=='2025-01-01'


def test_a_recorded_annual_gap_cannot_survive_new_annual_metadata(monkeypatch):
    policy,row,packet,_=fixture();policy.update(kind='inspection_only',reason='successor_annual_basis_unverified',requires_absent_annual=True);policy['documents']={'cover':policy['documents']['cover']};install(monkeypatch,policy)
    assert validate(policy,row,packet)['status']=='withheld'


@pytest.mark.parametrize('variant',['different_request_path','no_transport_decoration','financial_change','inline_script','script_attributes','non_tail_script'])
def test_explicit_sec_body_binding_preserves_raw_receipts_and_never_ignores_financial_changes(monkeypatch,variant):
    policy,row,packet,raw=fixture()
    old_script=b'<script type="text/javascript"  src="/old/path/token"></script>'
    new_script=b'<script type="text/javascript"  src="/new/request/token"></script>'
    for role,body in raw.items():
        reference=body.replace(b'</html>',old_script+b'</body></html>') if b'</body>' not in body else body.replace(b'</body>',old_script+b'</body>')
        # Fixture html has no body wrapper; use a complete literal body for both captures.
        if b'<body>' not in body:
            body=body.replace(b'<x:context',b'<body><x:context',1).replace(b'</html>',b'</body></html>');reference=body.replace(b'</body>',old_script+b'</body>')
        changed=body if variant=='no_transport_decoration' else body.replace(b'</body>',new_script+b'</body>')
        if variant=='financial_change':changed=changed.replace(b'>1</ix:nonFraction>',b'>2</ix:nonFraction>')
        if variant=='inline_script':changed=changed.replace(b'></script>',b'>changed()</script>')
        if variant=='script_attributes':changed=changed.replace(b'<script type=',b'<script data-extra="x" type=')
        if variant=='non_tail_script':changed=changed.replace(new_script,new_script+b'<p>after</p>')
        policy['documents'][role].update(sha256=hashlib.sha256(reference).hexdigest(),body_sha256=hashlib.sha256(body).hexdigest(),normalization='sec-empty-tail-script-v1')
        packet['documents'][role].update(payload_sha256=hashlib.sha256(changed).hexdigest(),payload_raw_base64=base64.b64encode(changed).decode())
    install(monkeypatch,policy);result=validate(policy,row,packet)
    assert (result['status']=='supported_common')==(variant in {'different_request_path','no_transport_decoration'})
    if result['status']=='supported_common':
        assert result['documents'][0]['payload_sha256']==packet['documents']['annual']['payload_sha256']
        assert result['documents'][0]['body_sha256']==policy['documents']['annual']['body_sha256']


@pytest.mark.parametrize('form',['8-K12B','8-K12B/A'])
def test_new_successor_identity_filing_withdraws_the_earlier_common_scope(monkeypatch,form):
    from selected_security_fixtures import scoped_collection
    from test_online_peer_valuation import build
    policy,c=scoped_collection();install(monkeypatch,policy);profile=c['issuers'][0]['profile'];recent=profile['payload']['filings']['recent']
    changed=dict(form=form,reportDate='2026-10-29',filingDate='2026-10-29',acceptanceDateTime='2026-10-29T12:00:00Z',accessionNumber='0000001001-26-000099',primaryDocument='successor.htm',isInlineXBRL=1,isXBRL=1)
    for k,v in recent.items():v.append(changed[k])
    profile['normalized_sha256']=digest(profile['payload']);assert build(c)['subject'] is None
