"""Runtime authorization for a server-selected research workspace."""
from dataclasses import dataclass
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import stat
import time
from uuid import uuid4

from src.hosted_access_control import (
    PrincipalContext, WorkspaceAction, WorkspaceMembership, WorkspaceResource,
    WorkspaceRole, evaluate_workspace_access, WorkspaceAccessRequest,
)

CONFIG_ENV = 'STOCK_RESEARCH_WORKSPACE_CONFIG'
WORKSPACE_ENV = 'STOCK_RESEARCH_WORKSPACE_ID'
MODE_ENV = 'STOCK_RESEARCH_ACCESS_MODE'


class WorkspaceAccessDenied(ValueError):
    def __init__(self, reason='workspace_access_denied'):
        super().__init__('Workspace access denied.')
        self.reason = reason


@dataclass(frozen=True)
class WorkspaceSession:
    workspace_id: str
    profile_key: str
    storage_root: Path
    principal_id: str


def protected_workspace_mode():
    return (os.getenv(MODE_ENV, 'local') != 'local'
            or CONFIG_ENV in os.environ or WORKSPACE_ENV in os.environ)


def _identifier(value, maximum=128):
    return (isinstance(value, str) and 0 < len(value) <= maximum
            and value.strip() == value and all(character.isprintable() for character in value))


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate configuration field')
        result[key] = value
    return result


def _configuration():
    try:
        if os.getenv(MODE_ENV, 'workspace') != 'workspace':
            raise ValueError('Conflicting access mode')
        selected = os.environ[WORKSPACE_ENV]
        path = Path(os.environ[CONFIG_ENV])
        if not path.is_absolute() or any(parent.is_symlink() for parent in (path, *path.parents)):
            raise ValueError('Absolute membership path required')
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(descriptor, 'rb') as stream:
            info = os.fstat(stream.fileno())
            if (not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= 1024 * 1024
                    or info.st_uid != os.getuid() or info.st_mode & 0o022):
                raise ValueError('Invalid membership file')
            config = json.loads(stream.read(1024 * 1024 + 1), object_pairs_hook=_unique_object)
        if (set(config) != {'schema_version', 'issuer', 'audience', 'storage_root', 'workspaces'}
                or config['schema_version'] != 'research-workspace-access-v1'
                or not _identifier(config['issuer'], 512) or not config['issuer'].startswith('https://')
                or not _identifier(config['audience'], 512)):
            raise ValueError('Invalid membership schema')
        root = Path(config['storage_root'])
        if not root.is_absolute() or root.is_symlink():
            raise ValueError('Absolute workspace storage required')
        workspaces = config['workspaces']
        if not isinstance(workspaces, dict) or not 0 < len(workspaces) <= 100:
            raise ValueError('Invalid workspace registry')
        profiles = set()
        for workspace_id, workspace in workspaces.items():
            if (not _identifier(workspace_id) or not isinstance(workspace, dict)
                    or set(workspace) != {'profile_key', 'members'}
                    or not _identifier(workspace['profile_key']) or workspace['profile_key'] in profiles
                    or not isinstance(workspace['members'], list) or len(workspace['members']) > 1000):
                raise ValueError('Invalid or aliased workspace')
            profiles.add(workspace['profile_key'])
            subjects = set()
            for member in workspace['members']:
                if (not isinstance(member, dict) or set(member) != {'subject', 'role', 'active'}
                        or not _identifier(member['subject'], 512) or member['subject'] in subjects
                        or member['role'] not in {role.value for role in WorkspaceRole}
                        or type(member['active']) is not bool):
                    raise ValueError('Invalid membership')
                subjects.add(member['subject'])
        if selected not in workspaces:
            raise ValueError('Unconfigured workspace')
        return config, selected, root.resolve()
    except (KeyError, OSError, ValueError, TypeError, UnicodeError, AttributeError, RecursionError):
        raise WorkspaceAccessDenied('workspace_configuration_unavailable') from None


def trusted_user_claims():
    """Read only Streamlit's server-provided OIDC identity, never route or widget state."""
    import streamlit as st

    return st.user.to_dict()


def _session(profile_key=None, action=WorkspaceAction.READ, resource=WorkspaceResource.SAVED_WORKSPACE_STATE):
    config, selected, root = _configuration()
    workspace = config['workspaces'][selected]
    try:
        claims = trusted_user_claims()
        now = time.time()
        expiry = claims.get('exp')
        audience = claims.get('aud')
        audiences = audience if isinstance(audience, list) else [audience]
        valid_time = type(expiry) in {int, float} and math.isfinite(expiry) and expiry > now
        for key in ('nbf', 'iat'):
            if key in claims:
                value = claims[key]
                valid_time = valid_time and type(value) in {int, float} and math.isfinite(value) and value <= now
        if (claims.get('is_logged_in') is not True or claims.get('iss') != config['issuer']
                or not _identifier(claims.get('sub'), 512) or config['audience'] not in audiences
                or not valid_time):
            raise ValueError('Unverified principal')
        subject = claims['sub']
    except (ValueError, TypeError, KeyError, AttributeError, RuntimeError):
        raise WorkspaceAccessDenied('authentication_required') from None
    principal_id = sha256(json.dumps([config['issuer'], subject]).encode()).hexdigest()
    member = next((row for row in workspace['members'] if row['subject'] == subject), None)
    membership = WorkspaceMembership(principal_id, selected,
        WorkspaceRole(member['role']) if member else WorkspaceRole.VIEWER,
        member['active'] if member else False)
    if profile_key not in (None, workspace['profile_key']):
        raise WorkspaceAccessDenied('workspace_mismatch')
    decision = evaluate_workspace_access(PrincipalContext(principal_id, True), membership,
        WorkspaceAccessRequest(uuid4().hex, selected, action, resource))
    if not decision.allowed:
        raise WorkspaceAccessDenied(decision.reason_code)
    return WorkspaceSession(selected, workspace['profile_key'], root, principal_id)


def selected_workspace_session():
    return _session() if protected_workspace_mode() else None


def require_workspace_access(profile_key, action=WorkspaceAction.READ,
                             resource=WorkspaceResource.SAVED_WORKSPACE_STATE):
    if protected_workspace_mode():
        return _session(profile_key, action, resource)
    return None


def can_workspace_access(profile_key, action=WorkspaceAction.READ,
                         resource=WorkspaceResource.SAVED_WORKSPACE_STATE):
    try:
        require_workspace_access(profile_key, action, resource)
        return True
    except WorkspaceAccessDenied:
        return False


def workspace_storage_root(default_root):
    return _configuration()[2] if protected_workspace_mode() else Path(default_root).resolve()


def require_record_destination(path, profile_key, ticker, action=WorkspaceAction.APPEND):
    session = require_workspace_access(profile_key, action, WorkspaceResource.RESEARCH_RECORD)
    if session is None:
        return
    directory = session.storage_root / 'outputs/local/company-research-notes' / sha256(profile_key.encode()).hexdigest()
    destination = Path(path)
    try:
        relative = destination.resolve().relative_to(directory.resolve())
        if (len(relative.parts) != 3 or relative.parts[1] != ticker
                or len(relative.parts[0]) != 10 or not relative.parts[0].isascii() or not relative.parts[0].isdigit()
                or int(relative.parts[0]) == 0 or relative.parts[2] not in {
                    'research_thesis_journal.csv', 'catalyst_evidence.csv', 'research_outcome_reviews.csv'}):
            raise ValueError('Unscoped research record')
        if any(part.is_symlink() for part in (destination, *destination.parents)):
            raise ValueError('Symlinked research record')
    except (ValueError, OSError):
        raise WorkspaceAccessDenied('record_destination_mismatch') from None


def require_record_read_path(path):
    if not protected_workspace_mode():
        return
    session = selected_workspace_session()
    require_record_destination(path, session.profile_key, Path(path).parent.name, WorkspaceAction.READ)
