"""Normalized EPS numeric tokens are provenance, while source bodies stay excluded."""
from copy import deepcopy

import pytest

from src.online_research_context_store import save_research_context, load_research_context, compare_research_contexts
from test_online_research_context_store import context, SCOPE


def _proof():
    return dict(value=1.25,raw_text='1.25',scale=0,sign='',decimals='2',transformation=None,
        context_id='annual',unit_id='usd-per-share',unit='USD/shares',concept='EarningsPerShareDiluted',
        namespace_uri='http://fasb.org/us-gaap/2025',
        source_ref='https://www.sec.gov/Archives/edgar/data/1234/000000123426000001/annual.htm#eps')


def _with_proof(location, proof=None):
    eps=dict(period_start='2025-01-01',period_end='2025-12-31',eps=1.25,proofs=[_proof() if proof is None else proof])
    evidence=dict(amendment_scope=dict(status='supported',original_eps=eps,
        commercial_eligible=False,readiness_promoted=False))
    peer=dict(status='withheld',reason='at_least_three_compatible_industry_references_required')
    if location=='subject': peer['subject']=evidence
    elif location=='peer': peer.update(status='research_comparison',peers=[evidence])
    else: peer['excluded']=[dict(reason='unqualified_peer',diagnostics=dict(annual_eps_observation=evidence))]
    return context(peer_read_through=peer)


@pytest.mark.parametrize('location',['subject','peer','excluded'])
def test_normalized_eps_numeric_provenance_roundtrips_exactly_in_peer_results(tmp_path,location):
    value=_with_proof(location); before=deepcopy(value)
    saved=save_research_context(value,**SCOPE,project_root=tmp_path)
    reopened=load_research_context(saved['snapshot_id'],**SCOPE,project_root=tmp_path)
    assert reopened['context']==before and value==before
    assert compare_research_contexts(value,reopened)['status']=='unchanged'
    assert reopened['historical'] is True and reopened['current'] is False
    assert reopened['context']['saved_readiness_promoted'] is False
    assert reopened['context']['peer_read_through']['status']==before['peer_read_through']['status']


@pytest.mark.parametrize('change',['value','markup','fixed_zero_markup','long_token','missing_unit','concept',
    'namespace','source','source_path','context','scale','extra_body'])
def test_numeric_proof_exception_cannot_admit_malformed_values_or_source_bodies(tmp_path,change):
    proof=_proof()
    if change=='value': proof['value']=99
    elif change=='markup': proof['raw_text']='<html>source body</html>'
    elif change=='fixed_zero_markup': proof.update(raw_text='<html>source body</html>',value=0,transformation='fixed-zero')
    elif change=='long_token': proof['raw_text']='1'*101
    elif change=='missing_unit': proof.pop('unit_id')
    elif change=='concept': proof['concept']='TextBlockDisclosure'
    elif change=='namespace': proof['namespace_uri']='https://example.com/us-gaap/2025'
    elif change=='source': proof['source_ref']='https://example.com/annual.htm#eps'
    elif change=='source_path': proof['source_ref']='https://www.sec.gov/Archives/edgar/data/1234/000000123426000001/../annual.htm#eps'
    elif change=='context': proof['context_id']=''
    elif change=='scale': proof['scale']=True
    else: proof['raw_body']='a source body'
    with pytest.raises(ValueError,match='normalized|raw/archive'):
        save_research_context(_with_proof('subject',proof),**SCOPE,project_root=tmp_path)
    assert list(tmp_path.iterdir())==[]


def test_arbitrary_raw_text_is_still_rejected_outside_recognized_numeric_provenance(tmp_path):
    value=context(notes={'raw_text':'123.45'})
    with pytest.raises(ValueError,match='normalized|raw/archive'):
        save_research_context(value,**SCOPE,project_root=tmp_path)
    assert list(tmp_path.iterdir())==[]


def _tsm_context():
    from src.online_filing_context import build_filing_inventory
    from src.sec_exact_filing import RIGHTS
    from src.sec_selected_security_policies import POLICIES
    from test_online_filing_context import NOW, _profile, _receipt

    policy = next(row for row in POLICIES if row['policy_id'] == 'tsm-identity-gap-2026-v2')
    ticker, cik = policy['ticker'], policy['sec_cik']
    annual = policy['documents']['annual']
    meta = annual['metadata']
    url = ('https://www.sec.gov/Archives/edgar/data/1046179/'
           + meta['accessionNumber'].replace('-', '') + '/' + meta['primaryDocument'])
    profile_url = f'https://data.sec.gov/submissions/CIK{cik}.json'
    profile = _profile([meta])
    profile.update(cik=int(cik), tickers=policy['issuer_symbols'])
    receipt = _receipt(profile, profile_url)
    inventory = build_filing_inventory(receipt, ticker=ticker, expected_cik=cik, as_of=NOW)
    observed = receipt['observed_at']
    document = dict(role='annual', **meta, source_ref=url, observed_at=observed,
                    payload_sha256='c' * 64, body_sha256=annual['body_sha256'],
                    binding_normalization=annual['normalization'], reference_capture_sha256=annual['sha256'])
    observations = []
    for rule in annual['inspection_observations']:
        row = dict(kind=rule['kind'], label=rule['label'], filing_cik=cik, financial_eligible=False,
                   role='annual', observed_at=observed, publication_date=meta['filingDate'],
                   accession=meta['accessionNumber'], rights_status=RIGHTS, source_ref=url)
        if rule['kind'] == 'element_note':
            row.update(location=rule['path'], text_sha256=rule['text_sha256'])
            if rule.get('extract'):
                row.update(value=5, unit='ordinary_shares/ADS')
        else:
            row.update({key: rule[key] for key in ('entity_cik', 'period_start', 'period_end', 'dimensions',
                                                   'context_id', 'concept', 'namespace_uri')})
            row.update(source_ref=url + '#' + rule['fact_id'], context_source_ref=url + '#' + rule['context_id'])
            if rule['kind'] == 'numeric':
                row.update(value=10.25, raw_text='10.25', sign='', scale=0, decimals='2', transformation=None,
                           unit=rule['currency'] + '/shares', unit_source_ref=url + '#' + rule['unit_id'],
                           security_basis=rule['security_basis'], currency_basis=rule['currency_basis'])
            else:
                row.update(text_sha256=rule['text_sha256'],
                           source_refs=[url + '#' + fact for fact in [rule['fact_id'], *rule['continuations']]])
        observations.append(row)
    scope = dict(status='inspection_only', reason=policy['reason'], policy_id=policy['policy_id'],
                 ticker=ticker, sec_cik=cik, issuer_symbols=policy['issuer_symbols'],
                 unassigned_issuer_symbols=['TSMWF'], documents=[document], basis_refs=[],
                 evidence_observations=observations, alias_mappings_established=False,
                 technical_interpretation_only=True, commercial_eligible=False, rights_status=RIGHTS)
    peer = dict(status='withheld', reason=policy['reason'], subject=None, peers=[], peer_median=None,
                premium_fraction=None, subject_source_context=dict(sec_cik=cik, selected_security_scope=scope))
    return context(ticker=ticker, sec_cik=cik, observed_at=observed,
                   filing_inventory=inventory, peer_read_through=peer)


def test_tsm_ifrs_eps_and_all_source_notes_replay_exactly_with_ads_valuation_withheld(tmp_path):
    from src.online_peer_valuation_ui import saved_tsm_security_html

    value = _tsm_context()
    scope = {key: value[key] for key in SCOPE}
    saved = save_research_context(value, **scope, project_root=tmp_path)
    reopened = load_research_context(saved['snapshot_id'], **scope, project_root=tmp_path)
    peer = reopened['context']['peer_read_through']
    assert reopened['context'] == value
    assert compare_research_contexts(value, reopened)['status'] == 'unchanged'
    assert peer['status'] == 'withheld' and peer['subject'] is None and peer['peer_median'] is None
    html = saved_tsm_security_html(reopened['context'])
    assert 'ADS valuation remains withheld.' in html
    assert all('#' + fact in html for fact in ('f-388', 'f-389', 'f-396', 'f-397'))


@pytest.mark.parametrize('issue', [
    'raw_body', 'fixed_zero', 'value', 'wrong_filing', 'wrong_dimension', 'wrong_basis', 'missing_fact',
    'note_digest', 'valuation_eligible', 'valuation_result', 'future_filing', 'detached_scope', 'wrong_inventory',
])
def test_tsm_replay_rejects_altered_exact_evidence(tmp_path, issue):
    value = _tsm_context()
    peer = value['peer_read_through']
    owner = peer['subject_source_context']
    evidence = owner['selected_security_scope']
    row = evidence['evidence_observations'][0]
    doc = evidence['documents'][0]
    if issue == 'raw_body':
        row['raw_text'] = '<html>source body</html>'
    elif issue == 'fixed_zero':
        row.update(raw_text='arbitrary text', value=0, transformation='fixed-zero')
    elif issue == 'value':
        row['value'] = 1
    elif issue == 'wrong_filing':
        row['source_ref'] = row['source_ref'].replace('tsm-20251231.htm', 'elsewhere.htm')
    elif issue == 'wrong_dimension':
        evidence['evidence_observations'][2]['dimensions'] = []
    elif issue == 'wrong_basis':
        row['currency_basis'] = 'convenience'
    elif issue == 'missing_fact':
        evidence['evidence_observations'].pop(0)
    elif issue == 'note_digest':
        evidence['evidence_observations'][-1]['text_sha256'] = []
    elif issue == 'valuation_eligible':
        row['financial_eligible'] = True
    elif issue == 'valuation_result':
        peer.update(status='research_comparison', peer_median=10)
    elif issue == 'future_filing':
        doc['observed_at'] = '2026-11-09T12:00:00Z'
    elif issue == 'detached_scope':
        value['notes'] = owner.pop('selected_security_scope')
    else:
        value['filing_inventory'] = {}
    scope = {key: value[key] for key in SCOPE}
    with pytest.raises(ValueError, match='Normalized TSM security observations|raw/archive'):
        save_research_context(value, **scope, project_root=tmp_path)
    assert not list(tmp_path.iterdir())
