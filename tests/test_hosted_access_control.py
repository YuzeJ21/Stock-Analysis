from dataclasses import FrozenInstanceError

import pytest

from src.hosted_access_control import (
    AuditObligation,
    PrincipalContext,
    WorkspaceAccessDecision,
    WorkspaceAccessRequest,
    WorkspaceAction,
    WorkspaceMembership,
    WorkspaceResource,
    WorkspaceRole,
    evaluate_workspace_access,
)


def _valid_inputs(
    *,
    principal_id: object = "principal-1",
    membership_principal_id: object = "principal-1",
    membership_workspace_id: object = "workspace-1",
    request_workspace_id: object = "workspace-1",
    request_id: object = "request-1",
    authenticated: object = True,
    active: object = True,
    role: object = WorkspaceRole.EDITOR,
    action: object = WorkspaceAction.READ,
    resource: object = WorkspaceResource.RESEARCH_RECORD,
) -> tuple[PrincipalContext, WorkspaceMembership, WorkspaceAccessRequest]:
    return (
        PrincipalContext(
            principal_id=principal_id,
            authenticated=authenticated,
        ),
        WorkspaceMembership(
            principal_id=membership_principal_id,
            workspace_id=membership_workspace_id,
            role=role,
            active=active,
        ),
        WorkspaceAccessRequest(
            request_id=request_id,
            workspace_id=request_workspace_id,
            action=action,
            resource=resource,
        ),
    )


@pytest.mark.parametrize(
    ("principal", "membership", "access_request"),
    [
        (object(),) + _valid_inputs()[1:],
        (_valid_inputs()[0], object(), _valid_inputs()[2]),
        _valid_inputs()[:2] + (object(),),
    ],
)
def test_malformed_boundary_objects_fail_closed(
    principal, membership, access_request
):
    decision = evaluate_workspace_access(principal, membership, access_request)

    assert decision.allowed is False
    assert decision.reason_code == "invalid_request"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("principal_id", None),
        ("principal_id", ""),
        ("principal_id", " leading"),
        ("principal_id", "trailing "),
        ("principal_id", "line\nbreak"),
        ("principal_id", "c1\u0085control"),
        ("principal_id", "line\u2028separator"),
        ("principal_id", "paragraph\u2029separator"),
        ("principal_id", "\ud800"),
        ("principal_id", "x" * 129),
        ("membership_principal_id", 7),
        ("membership_workspace_id", "\x00"),
        ("request_workspace_id", "\tworkspace"),
        ("request_id", False),
        ("authenticated", 1),
        ("active", "true"),
        ("role", "editor"),
        ("action", "read"),
        ("resource", "research_record"),
    ],
)
def test_malformed_fields_fail_closed(field, value):
    decision = evaluate_workspace_access(*_valid_inputs(**{field: value}))

    assert decision == WorkspaceAccessDecision(
        allowed=False,
        reason_code="invalid_request",
        audit=AuditObligation(
            event_type="workspace_access_decision",
            outcome="denied",
            reason_code="invalid_request",
            required_fields=(
                "request_id",
                "principal_id",
                "workspace_id",
                "resource",
                "action",
                "outcome",
                "reason_code",
                "occurred_at",
            ),
        ),
    )


def test_hostile_string_subclass_fails_closed_without_calling_strip():
    class HostileIdentifier(str):
        def strip(self):
            raise AssertionError("hostile strip must not be invoked")

    decision = evaluate_workspace_access(
        *_valid_inputs(principal_id=HostileIdentifier("principal-1"))
    )

    assert decision.allowed is False
    assert decision.reason_code == "invalid_request"


def test_frozen_inputs_and_decisions_cannot_be_mutated():
    principal, membership, request = _valid_inputs()
    decision = evaluate_workspace_access(principal, membership, request)

    with pytest.raises(FrozenInstanceError):
        principal.principal_id = "other"
    with pytest.raises(FrozenInstanceError):
        membership.role = WorkspaceRole.OWNER
    with pytest.raises(FrozenInstanceError):
        request.workspace_id = "other"
    with pytest.raises(FrozenInstanceError):
        decision.allowed = True
