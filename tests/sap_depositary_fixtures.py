"""Constructed SAP receipts; external transport is replaced, validation is real."""
from copy import deepcopy
from hashlib import sha256
import socket

from test_depositary_listing_inspection import dependencies
from test_online_peer_sources import get

CIK = '0001000184'
_CONNECT = socket.socket.connect
POLICY_ID = 'sap-nyse-ads-2026-v2'
RATIO = 'Currently each ADR represents one ordinary share.'
RESTRICTION = 'Ordinary shares are registered for the depositary program.'
BODY = f'''<html xmlns="http://www.w3.org/1999/xhtml"
 xmlns:x="http://www.xbrl.org/2003/instance" xmlns:ix="http://www.xbrl.org/2013/inlineXBRL"
 xmlns:f="https://xbrl.ifrs.org/taxonomy/2025-03-27/ifrs-full"
 xmlns:iso="http://www.xbrl.org/2003/iso4217"
 xmlns:ixt="http://www.xbrl.org/inlineXBRL/transformation/2020-02-12">
 <body><p>{RATIO}</p><p>{RESTRICTION}</p>
 <x:context id="annual"><x:entity><x:identifier scheme="http://www.sec.gov/CIK">{CIK}</x:identifier></x:entity>
 <x:period><x:startDate>2025-01-01</x:startDate><x:endDate>2025-12-31</x:endDate></x:period></x:context>
 <x:unit id="eur-shares"><x:divide><x:unitNumerator><x:measure>iso:EUR</x:measure></x:unitNumerator>
 <x:unitDenominator><x:measure>x:shares</x:measure></x:unitDenominator></x:divide></x:unit>
 <ix:nonFraction id="annual-eps" name="f:DilutedEarningsLossPerShare" contextRef="annual"
 unitRef="eur-shares" decimals="2" format="ixt:num-dot-decimal">4.20</ix:nonFraction></body></html>'''.encode()


def fixture(monkeypatch, *, raw=BODY, token_hash=None):
    import test_depositary_listing_inspection as receipts
    import src.sec_selected_security as security

    monkeypatch.setattr(receipts, 'BODY', raw)
    monkeypatch.setattr(receipts, 'NOTE', RATIO)
    deps, calls = dependencies(monkeypatch)
    policy = deepcopy(security.POLICIES[0])
    policy['policy_id'] = POLICY_ID
    doc = policy['documents']['annual']
    doc['inspection_observations'] = [
        dict(kind='element_note', label='Ordinary shares per ADR (filing disclosure)',
             path='/html[1]/body[1]/p[1]', text_sha256=sha256(RATIO.encode()).hexdigest(),
             extract='adr_ordinary_ratio'),
        dict(kind='element_note', label='Ordinary-share registration scope',
             path='/html[1]/body[1]/p[2]', text_sha256=sha256(RESTRICTION.encode()).hexdigest()),
        dict(kind='numeric', label='Reported annual diluted EPS (native currency)',
             fact_id='annual-eps', namespace_uri='https://xbrl.ifrs.org/taxonomy/2025-03-27/ifrs-full',
             concept='DilutedEarningsLossPerShare', unit_id='eur-shares', currency='EUR',
             security_basis='ordinary', currency_basis='native', context_id='annual', entity_cik=CIK,
             period_start='2025-01-01', period_end='2025-12-31', dimensions=[],
             raw_text_sha256=token_hash or sha256(b'4.20').hexdigest()),
    ]
    monkeypatch.setattr(security, 'POLICIES', (policy,))
    return policy, deps, calls


def observed(monkeypatch):
    policy, deps, calls = fixture(monkeypatch)
    state = {}
    peer = get(state, refresh=True, dependencies=deps, ticker='SAP', expected_cik=CIK)
    return policy, peer, state, deps, calls


def research_context():
    """Constructed normalized record matching the reviewed source contract.

    The filed token is explicit test data. This is not a real captured session.
    """
    from src.online_filing_context import build_filing_inventory
    from src.sec_exact_filing import RIGHTS
    from src.sec_selected_security_policies import POLICIES
    from test_online_filing_context import NOW as SAVED_NOW, _profile, _receipt
    from test_online_research_context_store import context

    policy = next(p for p in POLICIES if p['ticker'] == 'SAP')
    annual = policy['documents']['annual']
    meta = annual['metadata']
    url = f'https://www.sec.gov/Archives/edgar/data/1000184/{meta["accessionNumber"].replace("-", "")}/{meta["primaryDocument"]}'
    profile_url = f'https://data.sec.gov/submissions/CIK{CIK}.json'
    profile = _profile([meta])
    profile.update(cik=int(CIK), tickers=['SAP', 'SAPGF'], exchanges=['NYSE', 'OTC'])
    receipt = _receipt(profile, profile_url)
    inventory = build_filing_inventory(receipt, ticker='SAP', expected_cik=CIK, as_of=SAVED_NOW)
    stamp = receipt['observed_at']
    doc = dict(role='annual', **meta, source_ref=url, observed_at=stamp,
               payload_sha256='c' * 64, body_sha256=annual['body_sha256'],
               binding_normalization=annual['normalization'], reference_capture_sha256=annual['sha256'])
    observations = []
    for rule in annual['inspection_observations']:
        row = dict(kind=rule['kind'], label=rule['label'], filing_cik=CIK, financial_eligible=False,
                   role='annual', observed_at=stamp, publication_date=meta['filingDate'],
                   accession=meta['accessionNumber'], rights_status=RIGHTS, source_ref=url)
        if rule['kind'] == 'element_note':
            row.update(location=rule['path'], text_sha256=rule['text_sha256'])
            if rule.get('extract'):
                row.update(value=1, unit='ordinary_shares/ADR')
        else:
            row.update({k: rule[k] for k in ('entity_cik', 'period_start', 'period_end', 'dimensions',
                                           'context_id', 'concept', 'namespace_uri')})
            row.update(value=6.1, raw_text='6.10', sign='', scale=0, decimals='2', transformation='num-dot-decimal',
                       unit='EUR/shares', unit_source_ref=url + '#' + rule['unit_id'],
                       source_ref=url + '#' + rule['fact_id'], context_source_ref=url + '#' + rule['context_id'],
                       security_basis='ordinary', currency_basis='native')
        observations.append(row)
    scope = dict(status='inspection_only', reason=policy['reason'], policy_id=policy['policy_id'],
                 ticker='SAP', sec_cik=CIK, issuer_symbols=['SAP', 'SAPGF'], unassigned_issuer_symbols=['SAPGF'],
                 documents=[doc], basis_refs=[], evidence_observations=observations,
                 alias_mappings_established=False, technical_interpretation_only=True,
                 commercial_eligible=False, rights_status=RIGHTS)
    listing = dict(ticker='SAP', sec_cik=CIK, venue='NYSE', description='SAP SE ADS',
                   security_type='depositary_receipt',
                   source_url='https://www.nasdaqtrader.com/dynamic/symdir/otherlisted.txt',
                   source_created_at='2026-11-06T15:00', observed_at=stamp, payload_sha256='d' * 64)
    owner = dict(sec_cik=CIK, profile_source_ref=profile_url, profile_observed_at=stamp,
                 profile_sha256=receipt['payload_sha256'], selected_depositary_listing=listing,
                 selected_security_scope=scope, facts_query_ref=f'https://data.sec.gov/api/xbrl/companyfacts/CIK{CIK}.json',
                 annual_versions=[dict(form=meta['form'], period_end=meta['reportDate'], filed=meta['filingDate'],
                     accepted_at=meta['acceptanceDateTime'], accession=meta['accessionNumber'], source_ref=url)])
    listing_context = dict(schema_version='online-listing-session-v1', attempt_status='returned',
        selection='returned_receipt', attempted_at=stamp, completed_at=stamp, observed_from=stamp, observed_to=stamp,
        classification_digest='f' * 64, reason=None, source_attempts=[],
        source_receipts=[{k:listing[k] for k in ('source_url','observed_at','payload_sha256','source_created_at')}])
    peer = dict(ticker='SAP', status='withheld', reason=policy['reason'], metric='reported_annual_diluted_pe',
                subject=None, peers=[], excluded=[], peer_count=0, peer_median=None, premium_fraction=None,
                commercial_eligible=False, saved_readiness_promoted=False,
                rights_status='personal_research_only_commercial_and_redistribution_unverified',
                fiscal_window_days=35, minimum_peers=3, candidate_count=0, attempted_at=stamp,
                subject_source_context=owner, listing_context=listing_context)
    return context(ticker='SAP', sec_cik=CIK, observed_at=stamp, filing_inventory=inventory,
                   source_receipts={'financial': dict(source_url=f'https://data.sec.gov/api/xbrl/companyfacts/CIK{CIK}.json',
                       observed_at=stamp, payload_sha256='e' * 64)}, peer_read_through=peer,
                   scenario=None, scenario_base=dict(status='withheld', reason='annual_revenue_base_unavailable'),
                   business_trend=dict(status='withheld', metrics=[], periods=[], gaps=[]))


def write_replay_app(root):
    """Harness around production save, Monitor and historical-render functions."""
    from pathlib import Path
    project = Path(__file__).resolve().parents[1]
    app = root / 'src' / 'dashboard.py'
    app.parent.mkdir(parents=True, exist_ok=True)
    app.write_text(f'''import sys
from pathlib import Path
sys.path[:0] = [{str(project)!r}, {str(project / 'tests')!r}]
import streamlit as st
from sap_depositary_fixtures import research_context, install_provider_guard
from src import online_research_tools_ui as ui
from src import online_research_context_store as store
from src.company_workbench_ui import render_saved_company_replay
from src.research_workspace import research_monitor_origin, resolve_saved_monitor_origin
from src.online_peer_valuation_ui import online_peer_valuation_html
from src.online_research_context_store import load_research_context
ui.PROJECT_ROOT = Path({str(root)!r})
store.PROJECT_ROOT = ui.PROJECT_ROOT
install_provider_guard(ui.PROJECT_ROOT)
st.set_page_config(layout="wide")
if not st.query_params.get("page"):
    st.query_params.from_dict(dict(mode="research", page="company-workbench", ticker="SAP", section="valuation"))
value = research_context()
if st.query_params.get("page") == "monitor":
    origin = research_monitor_origin(st.session_state, value["profile_key"], "SAP")
    if origin is None:
        origin = resolve_saved_monitor_origin(st.query_params, value["profile_key"], "SAP")
        if origin is not None:
            st.session_state["research_monitor_origin"] = origin
    ui.render_online_research_monitor(st, profile_key=value["profile_key"], monitor_origin=origin)
elif st.query_params.get("research_snapshot"):
    saved = load_research_context(st.query_params["research_snapshot"], profile_key=value["profile_key"],
        ticker="SAP", sec_cik=value["sec_cik"], project_root=ui.PROJECT_ROOT)
    st.caption(saved["replay_notice"])
    render_saved_company_replay(st, saved)
else:
    st.markdown(online_peer_valuation_html(value["peer_read_through"]), unsafe_allow_html=True)
    ui._snapshots(st, value, dict(financial=dict(companyfacts_identity=dict(status="source_matched"))))
''')
    return app


def install_provider_guard(root):
    """Block and record Python provider connections in the app process."""
    def connect(sock, address):
        if isinstance(address, tuple) and address[0] not in {'127.0.0.1', 'localhost', '::1'}:
            with (root / 'server-provider-attempts.txt').open('a') as handle:
                handle.write('unexpected external connection\n')
            raise AssertionError('Source rendering/replay attempted provider transport')
        return _CONNECT(sock, address)
    socket.socket.connect = connect
