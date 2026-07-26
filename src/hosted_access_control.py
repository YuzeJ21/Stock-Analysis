"""Provider-neutral, deny-by-default workspace authorization policy."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from enum import Enum


class WorkspaceRole(str, Enum):
    VIEWER = "viewer"
    EDITOR = "editor"
    OWNER = "owner"


class WorkspaceAction(str, Enum):
    READ = "read"
    APPEND = "append"
    UPDATE = "update"
    DELETE = "delete"
    EXPORT = "export"
    MANAGE = "manage"


class WorkspaceResource(str, Enum):
    RESEARCH_RECORD = "research_record"
    SAVED_WORKSPACE_STATE = "saved_workspace_state"
    WORKSPACE_MEMBERSHIP = "workspace_membership"
    WORKSPACE_AUDIT = "workspace_audit"


@dataclass(frozen=True)
class PrincipalContext:
    principal_id: object
    authenticated: object


@dataclass(frozen=True)
class WorkspaceMembership:
    principal_id: object
    workspace_id: object
    role: object
    active: object


@dataclass(frozen=True)
class WorkspaceAccessRequest:
    request_id: object
    workspace_id: object
    action: object
    resource: object


@dataclass(frozen=True)
class AuditObligation:
    event_type: str
    outcome: str
    reason_code: str
    required_fields: tuple[str, ...]


@dataclass(frozen=True)
class WorkspaceAccessDecision:
    allowed: bool
    reason_code: str
    audit: AuditObligation


_AUDIT_FIELDS = (
    "request_id",
    "principal_id",
    "workspace_id",
    "resource",
    "action",
    "outcome",
    "reason_code",
    "occurred_at",
)


def _valid_identifier(value: object) -> bool:
    if type(value) is not str or not 1 <= len(value) <= 128:
        return False
    if value != value.strip():
        return False
    return all(
        unicodedata.category(character) not in {"Cc", "Cs", "Zl", "Zp"}
        for character in value
    )


def _decision(*, allowed: bool, reason_code: str) -> WorkspaceAccessDecision:
    outcome = "allowed" if allowed else "denied"
    return WorkspaceAccessDecision(
        allowed=allowed,
        reason_code=reason_code,
        audit=AuditObligation(
            event_type="workspace_access_decision",
            outcome=outcome,
            reason_code=reason_code,
            required_fields=_AUDIT_FIELDS,
        ),
    )


def _structurally_valid(
    principal: object,
    membership: object,
    request: object,
) -> bool:
    return (
        type(principal) is PrincipalContext
        and type(membership) is WorkspaceMembership
        and type(request) is WorkspaceAccessRequest
        and _valid_identifier(principal.principal_id)
        and type(principal.authenticated) is bool
        and _valid_identifier(membership.principal_id)
        and _valid_identifier(membership.workspace_id)
        and isinstance(membership.role, WorkspaceRole)
        and type(membership.active) is bool
        and _valid_identifier(request.request_id)
        and _valid_identifier(request.workspace_id)
        and isinstance(request.action, WorkspaceAction)
        and isinstance(request.resource, WorkspaceResource)
    )


_ALLOWED_ACTIONS = {
    WorkspaceResource.RESEARCH_RECORD: {
        WorkspaceRole.VIEWER: frozenset({WorkspaceAction.READ}),
        WorkspaceRole.EDITOR: frozenset(
            {WorkspaceAction.READ, WorkspaceAction.APPEND}
        ),
        WorkspaceRole.OWNER: frozenset(
            {
                WorkspaceAction.READ,
                WorkspaceAction.APPEND,
                WorkspaceAction.EXPORT,
            }
        ),
    },
    WorkspaceResource.SAVED_WORKSPACE_STATE: {
        WorkspaceRole.VIEWER: frozenset({WorkspaceAction.READ}),
        WorkspaceRole.EDITOR: frozenset(
            {
                WorkspaceAction.READ,
                WorkspaceAction.APPEND,
                WorkspaceAction.UPDATE,
            }
        ),
        WorkspaceRole.OWNER: frozenset(
            {
                WorkspaceAction.READ,
                WorkspaceAction.APPEND,
                WorkspaceAction.UPDATE,
                WorkspaceAction.DELETE,
                WorkspaceAction.EXPORT,
            }
        ),
    },
    WorkspaceResource.WORKSPACE_MEMBERSHIP: {
        WorkspaceRole.VIEWER: frozenset(),
        WorkspaceRole.EDITOR: frozenset(),
        WorkspaceRole.OWNER: frozenset(
            {WorkspaceAction.READ, WorkspaceAction.MANAGE}
        ),
    },
    WorkspaceResource.WORKSPACE_AUDIT: {
        WorkspaceRole.VIEWER: frozenset(),
        WorkspaceRole.EDITOR: frozenset(),
        WorkspaceRole.OWNER: frozenset(
            {WorkspaceAction.READ, WorkspaceAction.EXPORT}
        ),
    },
}


def evaluate_workspace_access(
    principal: object,
    membership: object,
    request: object,
) -> WorkspaceAccessDecision:
    """Return one immutable policy decision without side effects."""
    if not _structurally_valid(principal, membership, request):
        return _decision(allowed=False, reason_code="invalid_request")
    if principal.authenticated is not True:
        return _decision(
            allowed=False,
            reason_code="authentication_required",
        )
    if membership.principal_id != principal.principal_id:
        return _decision(allowed=False, reason_code="principal_mismatch")
    if membership.active is not True:
        return _decision(allowed=False, reason_code="membership_inactive")
    if request.workspace_id != membership.workspace_id:
        return _decision(allowed=False, reason_code="workspace_mismatch")
    if (
        request.resource is WorkspaceResource.RESEARCH_RECORD
        and request.action in {WorkspaceAction.UPDATE, WorkspaceAction.DELETE}
    ):
        return _decision(
            allowed=False,
            reason_code="append_only_mutation_denied",
        )
    allowed_actions = _ALLOWED_ACTIONS[request.resource][membership.role]
    if request.action not in allowed_actions:
        return _decision(allowed=False, reason_code="role_action_denied")
    return _decision(allowed=True, reason_code="allowed")
