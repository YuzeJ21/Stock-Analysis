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
