"""Trust-boundary tests for the runtime workspace adapter."""
import json
import time

import pytest

from src import workspace_authorization as access
from src.hosted_access_control import WorkspaceAction


@pytest.fixture
def configured(tmp_path, monkeypatch):
    config = dict(schema_version='research-workspace-access-v1', issuer='https://identity.example',
        audience='stock-research', storage_root=str(tmp_path / 'store'), workspaces={
            'alpha': dict(profile_key='workspace-alpha', members=[dict(subject='alice', role='editor', active=True)]),
            'beta': dict(profile_key='workspace-beta', members=[dict(subject='bob', role='viewer', active=True)]),
        })
    path = tmp_path / 'access.json'
    path.write_text(json.dumps(config))
    monkeypatch.setenv(access.CONFIG_ENV, str(path))
    monkeypatch.setenv(access.WORKSPACE_ENV, 'alpha')
    monkeypatch.setenv(access.MODE_ENV, 'workspace')
    claims = dict(is_logged_in=True, iss=config['issuer'], aud=config['audience'], sub='alice', exp=time.time() + 3600)
    monkeypatch.setattr(access, 'trusted_user_claims', lambda: claims)
    return path, config, claims


def test_personal_mode_preserves_existing_access_without_identity_lookup(monkeypatch):
    for name in (access.MODE_ENV, access.CONFIG_ENV, access.WORKSPACE_ENV):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(access, 'trusted_user_claims', lambda: pytest.fail('Personal mode queried hosted identity'))
    assert access.selected_workspace_session() is None
    assert access.require_workspace_access('personal') is None


def test_membership_rechecked_and_profile_bound_to_server(configured):
    path, config, _ = configured
    session = access.require_workspace_access('workspace-alpha', WorkspaceAction.APPEND)
    assert session.workspace_id == 'alpha' and session.profile_key == 'workspace-alpha'
    with pytest.raises(access.WorkspaceAccessDenied, match='Workspace access denied'):
        access.require_workspace_access('workspace-beta')
    config['workspaces']['alpha']['members'][0]['active'] = False
    path.write_text(json.dumps(config))
    assert not access.can_workspace_access('workspace-alpha')
    with pytest.raises(access.WorkspaceAccessDenied):
        access.require_workspace_access('workspace-alpha', WorkspaceAction.APPEND)


@pytest.mark.parametrize('changes', [
    {'is_logged_in': False}, {'is_logged_in': 1}, {'iss': 'https://other.example'},
    {'aud': 'different-app'}, {'sub': 'bob'}, {'exp': 0}, {'exp': True}, {'exp': 'future'},
    {'exp': float('inf')}, {'nbf': time.time() + 3600}, {'iat': time.time() + 3600},
])
def test_unverified_or_expired_principal_denied(configured, changes):
    _, _, claims = configured
    claims.update(changes)
    with pytest.raises(access.WorkspaceAccessDenied):
        access.selected_workspace_session()


def test_missing_identity_and_expiry_denied(configured):
    _, _, claims = configured
    claims.pop('exp')
    with pytest.raises(access.WorkspaceAccessDenied):
        access.selected_workspace_session()
    claims.clear()
    with pytest.raises(access.WorkspaceAccessDenied):
        access.selected_workspace_session()


def test_viewer_cannot_append_but_can_read(configured):
    path, config, _ = configured
    config['workspaces']['alpha']['members'][0]['role'] = 'viewer'
    path.write_text(json.dumps(config))
    assert access.can_workspace_access('workspace-alpha')
    assert not access.can_workspace_access('workspace-alpha', WorkspaceAction.APPEND)


def test_audience_list_validated_and_expiry_rechecked(configured):
    _, _, claims = configured
    claims['aud'] = ['another-app', 'stock-research']
    assert access.selected_workspace_session().profile_key == 'workspace-alpha'
    claims['exp'] = time.time() - 1
    with pytest.raises(access.WorkspaceAccessDenied):
        access.selected_workspace_session()


@pytest.mark.parametrize('change', ['writable', 'symlink', 'duplicate_json_key'])
def test_untrusted_membership_file_rejected(configured, change):
    path, config, _ = configured
    if change == 'writable':
        path.chmod(0o666)
    elif change == 'symlink':
        real = path.with_suffix('.real')
        path.rename(real)
        path.symlink_to(real)
    else:
        path.write_text(json.dumps(config)[:-1] + ',"issuer":"https://identity.example"}')
    with pytest.raises(access.WorkspaceAccessDenied):
        access.selected_workspace_session()


@pytest.mark.parametrize('change', ['duplicate_profile', 'duplicate_member', 'malformed', 'removed', 'local_mode'])
def test_broken_registry_never_falls_back_to_personal(configured, monkeypatch, change):
    path, config, _ = configured
    if change == 'duplicate_profile':
        config['workspaces']['beta']['profile_key'] = 'workspace-alpha'
    elif change == 'duplicate_member':
        config['workspaces']['alpha']['members'] *= 2
    elif change == 'local_mode':
        monkeypatch.setenv(access.MODE_ENV, 'local')
    if change == 'removed':
        path.unlink()
    else:
        path.write_text('{' if change == 'malformed' else json.dumps(config))
    with pytest.raises(access.WorkspaceAccessDenied):
        access.selected_workspace_session()
