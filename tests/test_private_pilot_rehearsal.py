"""Local pilot recovery rehearsals using disposable stores and constructed sources."""
import json
from pathlib import Path
import socket
import subprocess
import sys

import pytest

from src import online_research_context_store as store
from src.commercial_source_rights import load_source_rights_registry, review_commercial_field_scope
from src.online_peer_sources import get_online_peer_valuation
from src.private_beta_readiness import build_private_beta_readiness
from tests.test_online_peer_sources import NOW, source_dependencies
from tests.test_online_research_context_store import context


PROJECT = Path(__file__).resolve().parents[1]
ROLLBACK_REVISION = '3682b320cf27a2c5b7af84c6d4566e808057a7e5'


@pytest.fixture(autouse=True)
def prohibit_external_transport(monkeypatch):
    def deny(*args, **kwargs):
        pytest.fail('The local pilot rehearsal attempted network access')

    monkeypatch.setattr(socket.socket, 'connect', deny)
    monkeypatch.setattr(socket.socket, 'connect_ex', deny)
    monkeypatch.delenv('COMMERCIAL_RESEARCH_MODE', raising=False)


def test_provider_failure_holds_old_answer_and_explicit_retry_recovers(tmp_path):
    dependencies, calls = source_dependencies()
    state = {}

    def request(*, refresh=False, sources=dependencies, as_of=NOW):
        return get_online_peer_valuation('FICT', state, refresh_requested=refresh,
            expected_cik='0000001001', user_agent='Synthetic local rehearsal',
            dependencies=sources, as_of=as_of)

    accepted = request(refresh=True)
    assert accepted['status'] == 'research_comparison'
    scope = dict(profile_key='pilot/alpha', ticker='FICT', sec_cik='0000001001')
    original = context(**scope, peer_read_through=accepted)
    saved = store.save_research_context(original, **scope, project_root=tmp_path)
    snapshot_path = next(tmp_path.rglob(saved['snapshot_id'] + '.json'))
    saved_bytes = snapshot_path.read_bytes()
    before = list(calls)
    assert request() == accepted and calls == before

    def outage(*args, **kwargs):
        calls.append(('injected_outage',))
        raise TimeoutError('Synthetic private transport diagnostic')

    held = request(refresh=True, sources={**dependencies, 'vendor': outage})
    assert held['status'] == 'withheld'
    assert held['subject'] is None
    assert held['peer_median'] is None and held['premium_fraction'] is None
    assert 'private transport diagnostic' not in json.dumps(held)
    before = list(calls)
    assert request() == held and calls == before
    assert store.load_research_context(saved['snapshot_id'], **scope, project_root=tmp_path) == saved

    restored = request(refresh=True)
    assert restored['status'] == accepted['status']
    for key in ('subject', 'peers', 'excluded', 'peer_count', 'peer_median', 'premium_fraction'):
        assert restored[key] == accepted[key]
    before = list(calls)
    assert request() == restored and calls == before
    assert snapshot_path.read_bytes() == saved_bytes


def test_previous_reader_rollback_reopens_both_profiles_and_rolls_forward(tmp_path):
    snapshots = {}
    for profile in ('pilot/alpha', 'pilot/beta'):
        scope = dict(profile_key=profile, ticker='FICT', sec_cik='0000001234')
        snapshots[profile] = [store.save_research_context(
            context(**scope, notes={'thesis': profile + ' observation ' + str(index)}),
            **scope, project_root=tmp_path,
        ) for index in (1, 2)]
    before = {path: path.read_bytes() for path in tmp_path.rglob('*.json')}
    for profile, records in snapshots.items():
        other_profile = next(name for name in snapshots if name != profile)
        with pytest.raises(ValueError, match='scope'):
            store.save_research_context(records[0]['context'], profile_key=other_profile,
                ticker='FICT', sec_cik='0000001234', project_root=tmp_path)
    assert {path: path.read_bytes() for path in tmp_path.rglob('*.json')} == before
    previous_source = subprocess.run(
        ['git', 'show', ROLLBACK_REVISION + ':src/online_research_context_store.py'],
        cwd=PROJECT, text=True, capture_output=True, check=True, timeout=10,
    ).stdout
    assert previous_source != (PROJECT / 'src/online_research_context_store.py').read_text(encoding='utf-8')
    reader = tmp_path / 'previous_reader.py'
    reader.write_text(previous_source, encoding='utf-8')
    program = '''
import importlib.util
import json
from pathlib import Path
import socket
import sys

def deny(*args, **kwargs):
    raise AssertionError('Rollback replay attempted external transport')

socket.socket.connect = socket.socket.connect_ex = deny
root = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location('pilot_previous_reader', root / 'previous_reader.py')
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
cases = json.load(sys.stdin)
for profile, snapshots in cases.items():
    scope = dict(profile_key=profile, ticker='FICT', sec_cik='0000001234', project_root=root)
    read = [previous.load_research_context(row['snapshot_id'], **scope) for row in snapshots]
    assert read == snapshots
    assert previous.compare_research_contexts(read[0], read[0])['status'] == 'unchanged'
    comparison = previous.compare_research_contexts(*read)
    assert comparison['status'] == 'user_inputs_changed' and comparison['notes_changed']
    other = next(value for key, value in cases.items() if key != profile)
    try:
        previous.load_research_context(other[0]['snapshot_id'], **scope)
    except ValueError:
        pass
    else:
        raise AssertionError('Previous reader exposed another profile')
print('previous_reader_verified')
'''
    rolled_back = subprocess.run([sys.executable, '-c', program, str(tmp_path)],
        cwd=PROJECT, input=json.dumps(snapshots), text=True, capture_output=True,
        check=True, timeout=20)
    assert rolled_back.stdout.strip() == 'previous_reader_verified'
    for profile, records in snapshots.items():
        scope = dict(profile_key=profile, ticker='FICT', sec_cik='0000001234')
        for row in records:
            assert store.load_research_context(row['snapshot_id'], **scope, project_root=tmp_path) == row
            assert store.save_research_context(row['context'], **scope, project_root=tmp_path) == row
    assert {path: path.read_bytes() for path in tmp_path.rglob('*.json')} == before


def test_recovery_does_not_clear_source_rights_or_hosted_pilot_gates():
    registry = load_source_rights_registry(PROJECT / 'config/source_rights.yml')
    prices = review_commercial_field_scope(registry, 'yfinance', ('prices',))
    eps = review_commercial_field_scope(registry, 'sec_companyfacts', ('diluted_eps',))
    assert not prices.commercial_evidence_ready
    assert prices.rights_status == 'commercial_rights_unverified'
    assert not eps.commercial_evidence_ready and eps.missing_supported_fields == ('diluted_eps',)
    areas = {check.area: check.status for check in build_private_beta_readiness().checks}
    for key in ('authentication', 'workspaces', 'user_data_separation', 'audit', 'retention', 'monitoring'):
        assert areas[key] == 'external_account_required'
    for key in ('rollback', 'incident_response', 'owner_capacity'):
        assert areas[key] == 'external_operations_required'
