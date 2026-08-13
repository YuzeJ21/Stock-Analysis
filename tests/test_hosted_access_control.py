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
    ("principal", "membership", "access_request"),
    [
        (object.__new__(PrincipalContext),) + _valid_inputs()[1:],
        (
            _valid_inputs()[0],
            object.__new__(WorkspaceMembership),
            _valid_inputs()[2],
        ),
        _valid_inputs()[:2] + (object.__new__(WorkspaceAccessRequest),),
    ],
)
def test_incomplete_exact_type_objects_fail_closed(
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


_ALLOWED_CASES = (
    (WorkspaceRole.VIEWER, WorkspaceResource.RESEARCH_RECORD, WorkspaceAction.READ),
    (WorkspaceRole.EDITOR, WorkspaceResource.RESEARCH_RECORD, WorkspaceAction.READ),
    (WorkspaceRole.EDITOR, WorkspaceResource.RESEARCH_RECORD, WorkspaceAction.APPEND),
    (WorkspaceRole.OWNER, WorkspaceResource.RESEARCH_RECORD, WorkspaceAction.READ),
    (WorkspaceRole.OWNER, WorkspaceResource.RESEARCH_RECORD, WorkspaceAction.APPEND),
    (WorkspaceRole.OWNER, WorkspaceResource.RESEARCH_RECORD, WorkspaceAction.EXPORT),
    (WorkspaceRole.VIEWER, WorkspaceResource.SAVED_WORKSPACE_STATE, WorkspaceAction.READ),
    (WorkspaceRole.EDITOR, WorkspaceResource.SAVED_WORKSPACE_STATE, WorkspaceAction.READ),
    (WorkspaceRole.EDITOR, WorkspaceResource.SAVED_WORKSPACE_STATE, WorkspaceAction.APPEND),
    (WorkspaceRole.EDITOR, WorkspaceResource.SAVED_WORKSPACE_STATE, WorkspaceAction.UPDATE),
    (WorkspaceRole.OWNER, WorkspaceResource.SAVED_WORKSPACE_STATE, WorkspaceAction.READ),
    (WorkspaceRole.OWNER, WorkspaceResource.SAVED_WORKSPACE_STATE, WorkspaceAction.APPEND),
    (WorkspaceRole.OWNER, WorkspaceResource.SAVED_WORKSPACE_STATE, WorkspaceAction.UPDATE),
    (WorkspaceRole.OWNER, WorkspaceResource.SAVED_WORKSPACE_STATE, WorkspaceAction.DELETE),
    (WorkspaceRole.OWNER, WorkspaceResource.SAVED_WORKSPACE_STATE, WorkspaceAction.EXPORT),
    (WorkspaceRole.OWNER, WorkspaceResource.WORKSPACE_MEMBERSHIP, WorkspaceAction.READ),
    (WorkspaceRole.OWNER, WorkspaceResource.WORKSPACE_MEMBERSHIP, WorkspaceAction.MANAGE),
    (WorkspaceRole.OWNER, WorkspaceResource.WORKSPACE_AUDIT, WorkspaceAction.READ),
    (WorkspaceRole.OWNER, WorkspaceResource.WORKSPACE_AUDIT, WorkspaceAction.EXPORT),
)


@pytest.mark.parametrize(("role", "resource", "action"), _ALLOWED_CASES)
def test_exact_policy_matrix_allows_only_declared_entries(role, resource, action):
    decision = evaluate_workspace_access(
        *_valid_inputs(role=role, resource=resource, action=action)
    )

    assert decision.allowed is True
    assert decision.reason_code == "allowed"
    assert decision.audit.outcome == "allowed"
    assert decision.audit.reason_code == "allowed"


_ALLOWED_SET = set(_ALLOWED_CASES)
_DENIED_CASES = tuple(
    (role, resource, action)
    for role in WorkspaceRole
    for resource in WorkspaceResource
    for action in WorkspaceAction
    if (role, resource, action) not in _ALLOWED_SET
)


@pytest.mark.parametrize(("role", "resource", "action"), _DENIED_CASES)
def test_every_absent_policy_entry_is_denied(role, resource, action):
    decision = evaluate_workspace_access(
        *_valid_inputs(role=role, resource=resource, action=action)
    )

    expected = (
        "append_only_mutation_denied"
        if resource is WorkspaceResource.RESEARCH_RECORD
        and action in {WorkspaceAction.UPDATE, WorkspaceAction.DELETE}
        else "role_action_denied"
    )
    assert decision.allowed is False
    assert decision.reason_code == expected
    assert decision.audit.outcome == "denied"
    assert decision.audit.reason_code == expected


@pytest.mark.parametrize("role", tuple(WorkspaceRole))
@pytest.mark.parametrize(
    "action",
    (WorkspaceAction.UPDATE, WorkspaceAction.DELETE),
)
def test_no_role_can_mutate_append_only_research_records(role, action):
    decision = evaluate_workspace_access(
        *_valid_inputs(
            role=role,
            resource=WorkspaceResource.RESEARCH_RECORD,
            action=action,
        )
    )

    assert decision.allowed is False
    assert decision.reason_code == "append_only_mutation_denied"


@pytest.mark.parametrize(
    ("changes", "reason_code"),
    [
        ({"authenticated": False}, "authentication_required"),
        ({"membership_principal_id": "principal-2"}, "principal_mismatch"),
        ({"active": False}, "membership_inactive"),
        ({"request_workspace_id": "workspace-2"}, "workspace_mismatch"),
    ],
)
def test_isolation_denials_follow_declared_order(changes, reason_code):
    decision = evaluate_workspace_access(*_valid_inputs(**changes))

    assert decision.allowed is False
    assert decision.reason_code == reason_code


def test_earlier_denial_cannot_be_overridden_by_later_allow_rule():
    decision = evaluate_workspace_access(
        *_valid_inputs(
            authenticated=False,
            membership_principal_id="principal-2",
            active=False,
            request_workspace_id="workspace-2",
            role=WorkspaceRole.OWNER,
            resource=WorkspaceResource.SAVED_WORKSPACE_STATE,
            action=WorkspaceAction.DELETE,
        )
    )

    assert decision.reason_code == "authentication_required"


def test_principal_mismatch_precedes_inactive_membership_and_workspace_mismatch():
    decision = evaluate_workspace_access(
        *_valid_inputs(
            membership_principal_id="principal-2",
            active=False,
            request_workspace_id="workspace-2",
        )
    )

    assert decision.reason_code == "principal_mismatch"


def test_membership_inactive_precedes_workspace_mismatch():
    decision = evaluate_workspace_access(
        *_valid_inputs(
            active=False,
            request_workspace_id="workspace-2",
        )
    )

    assert decision.reason_code == "membership_inactive"


def test_workspace_mismatch_precedes_append_only_policy_denial():
    decision = evaluate_workspace_access(
        *_valid_inputs(
            request_workspace_id="workspace-2",
            role=WorkspaceRole.OWNER,
            resource=WorkspaceResource.RESEARCH_RECORD,
            action=WorkspaceAction.DELETE,
        )
    )

    assert decision.reason_code == "workspace_mismatch"


def test_valid_unicode_scalar_identifiers_are_accepted_deterministically():
    inputs = _valid_inputs(
        principal_id="研究员-😀",
        membership_principal_id="研究员-😀",
        membership_workspace_id="工作区-α",
        request_workspace_id="工作区-α",
        request_id="请求-1",
    )

    first = evaluate_workspace_access(*inputs)
    second = evaluate_workspace_access(*inputs)

    assert first == second
    assert first.allowed is True


@pytest.mark.parametrize(
    "changes",
    [
        {},
        {"authenticated": False},
        {"membership_principal_id": "principal-2"},
        {"active": False},
        {"request_workspace_id": "workspace-2"},
        {"action": WorkspaceAction.MANAGE},
        {
            "resource": WorkspaceResource.RESEARCH_RECORD,
            "action": WorkspaceAction.DELETE,
            "role": WorkspaceRole.OWNER,
        },
    ],
)
def test_every_decision_has_the_exact_privacy_safe_audit_obligation(changes):
    decision = evaluate_workspace_access(*_valid_inputs(**changes))

    assert decision.audit.event_type == "workspace_access_decision"
    assert decision.audit.outcome == ("allowed" if decision.allowed else "denied")
    assert decision.audit.reason_code == decision.reason_code
    assert decision.audit.required_fields == (
        "request_id",
        "principal_id",
        "workspace_id",
        "resource",
        "action",
        "outcome",
        "reason_code",
        "occurred_at",
    )
    assert "principal-1" not in decision.reason_code
    assert "workspace-1" not in decision.reason_code


def test_public_contract_contains_no_secret_or_research_content_fields():
    public_fields = {
        *PrincipalContext.__dataclass_fields__,
        *WorkspaceMembership.__dataclass_fields__,
        *WorkspaceAccessRequest.__dataclass_fields__,
        *AuditObligation.__dataclass_fields__,
        *WorkspaceAccessDecision.__dataclass_fields__,
    }
    forbidden = {
        "credential",
        "token",
        "cookie",
        "api_key",
        "session_secret",
        "thesis",
        "evidence",
        "catalyst",
        "research_outcome",
        "forecast",
        "probability",
        "recommendation",
        "position",
        "transaction",
    }

    assert public_fields.isdisjoint(forbidden)


def test_evaluation_does_not_mutate_inputs_or_write_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    principal, membership, request = _valid_inputs()
    before = (
        (principal.principal_id, principal.authenticated),
        (
            membership.principal_id,
            membership.workspace_id,
            membership.role,
            membership.active,
        ),
        (
            request.request_id,
            request.workspace_id,
            request.action,
            request.resource,
        ),
    )

    evaluate_workspace_access(principal, membership, request)

    after = (
        (principal.principal_id, principal.authenticated),
        (
            membership.principal_id,
            membership.workspace_id,
            membership.role,
            membership.active,
        ),
        (
            request.request_id,
            request.workspace_id,
            request.action,
            request.resource,
        ),
    )
    assert after == before
    assert list(tmp_path.iterdir()) == []


def test_module_uses_only_the_approved_standard_library_imports():
    import ast
    import inspect

    import src.hosted_access_control as module

    tree = ast.parse(inspect.getsource(module))
    imported_roots = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_roots.update(
        node.module.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module != "__future__"
    )

    assert imported_roots == {"dataclasses", "enum", "unicodedata"}
