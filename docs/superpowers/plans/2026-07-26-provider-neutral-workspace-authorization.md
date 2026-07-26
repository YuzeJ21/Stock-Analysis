# Provider-Neutral Workspace Authorization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build one pure, provider-neutral, deny-by-default workspace authorization decision that enforces principal/workspace isolation, least privilege, append-only research records, and privacy-safe audit obligations.

**Architecture:** Add a single standard-library policy module whose frozen domain types form the supported trust boundary and whose evaluator returns an immutable allow/deny decision for every expected request. Keep the first slice isolated from Streamlit, ledgers, readiness, providers, persistence, and hosted infrastructure; update only truthful architecture and roadmap evidence after the policy tests pass.

**Tech Stack:** Python 3, standard-library `dataclasses`, `enum`, and `unicodedata`; pytest; Markdown contract tests; existing Make release and hygiene gates.

## Global Constraints

- The authoritative design is `docs/superpowers/specs/2026-07-26-provider-neutral-workspace-authorization-design.md`.
- The evaluator must be pure, provider-neutral, deterministic, and deny by default.
- The module must depend only on the Python standard library.
- Identifiers must be strings of 1–128 Unicode scalar values with no leading/trailing whitespace, C0/C1 controls, Unicode line/paragraph separators, or surrogate code points.
- `authenticated` and `active` must be exact booleans; role, action, and resource must be members of their declared enums.
- Expected authorization failures return immutable denied decisions and do not raise.
- Research records are append-only: `update` and `delete` are denied for every role.
- Every decision carries a privacy-safe audit obligation; the evaluator never persists an audit event.
- No dashboard, ledger, readiness, source-rights, provider, file, environment, network, or generated-data integration is permitted in this slice.
- Do not claim runtime authentication, hosted isolation, persistence, audit storage, retention, monitoring, rollback, incident response, operated capacity, or market validation.
- Do not run readiness rebuilds, broad refreshes, or generated CSV/JSON/report commands.
- Keep the 18 existing generated CSV/report changes unstaged and preserve their diff fingerprint `a2c2f428b489dbb291dd54fd8a6e1e7f4ad9481414320ca248c54be89f4062b9`.
- Stage or synchronize exact intentional paths only; never use `git add -A`.
- Push only to `codex/personal-research-mode-mvp`; keep PR #113 open and draft; do not merge or deploy.

## File Map

- Create `src/hosted_access_control.py`: frozen authorization domain types, structural validation, static policy matrix, audit-obligation factory, and pure evaluator.
- Create `tests/test_hosted_access_control.py`: exhaustive policy, denial-order, malformed-input, Unicode, immutability, audit, privacy, and side-effect tests.
- Modify `docs/PRIVATE_BETA_ARCHITECTURE.md`: describe the local policy contract without promoting hosted readiness.
- Modify `ROADMAP.md`: record the completed local Priority 6 slice and preserve the external hosted exit gate.
- Modify `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`: add the exact local lineage and next safe lane while preserving external blockers.
- Modify `tests/test_public_v1_release_docs.py`: lock the provider-neutral, deny-by-default, append-only, audit, and non-claim language.

---

### Task 1: Define The Frozen Trust-Boundary Types And Structural Validation

**Files:**
- Create: `src/hosted_access_control.py`
- Create: `tests/test_hosted_access_control.py`

**Interfaces:**
- Consumes: no project modules; Python standard library only.
- Produces: `WorkspaceRole`, `WorkspaceAction`, `WorkspaceResource`, `PrincipalContext`, `WorkspaceMembership`, `WorkspaceAccessRequest`, `AuditObligation`, `WorkspaceAccessDecision`, and `evaluate_workspace_access(principal: object, membership: object, request: object) -> WorkspaceAccessDecision`.

- [ ] **Step 1: Write failing tests for malformed trust-boundary inputs**

Create `tests/test_hosted_access_control.py` with the imports, valid fixture factory, and structural-denial cases:

```python
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
    ("principal", "membership", "request"),
    [
        (object(),) + _valid_inputs()[1:],
        (_valid_inputs()[0], object(), _valid_inputs()[2]),
        _valid_inputs()[:2] + (object(),),
    ],
)
def test_malformed_boundary_objects_fail_closed(principal, membership, request):
    decision = evaluate_workspace_access(principal, membership, request)

    assert decision.allowed is False
    assert decision.reason_code == "invalid_request"


@pytest.mark.parametrize(
    ("principal", "membership", "request"),
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
    principal, membership, request
):
    decision = evaluate_workspace_access(principal, membership, request)

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
```

- [ ] **Step 2: Run the new structural tests and confirm the missing-module failure**

Run:

```bash
python3 -m pytest tests/test_hosted_access_control.py -q
```

Expected: test collection fails with `ModuleNotFoundError: No module named 'src.hosted_access_control'`.

- [ ] **Step 3: Implement enums, frozen dataclasses, identifier validation, and invalid-request decisions**

Create `src/hosted_access_control.py`:

```python
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
    if not isinstance(value, str) or not 1 <= len(value) <= 128:
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


_MISSING_FIELD = object()


def _structurally_valid(
    principal: object,
    membership: object,
    request: object,
) -> bool:
    if (
        type(principal) is not PrincipalContext
        or type(membership) is not WorkspaceMembership
        or type(request) is not WorkspaceAccessRequest
    ):
        return False

    principal_id = getattr(principal, "principal_id", _MISSING_FIELD)
    authenticated = getattr(principal, "authenticated", _MISSING_FIELD)
    membership_principal_id = getattr(
        membership,
        "principal_id",
        _MISSING_FIELD,
    )
    membership_workspace_id = getattr(
        membership,
        "workspace_id",
        _MISSING_FIELD,
    )
    role = getattr(membership, "role", _MISSING_FIELD)
    active = getattr(membership, "active", _MISSING_FIELD)
    request_id = getattr(request, "request_id", _MISSING_FIELD)
    request_workspace_id = getattr(request, "workspace_id", _MISSING_FIELD)
    action = getattr(request, "action", _MISSING_FIELD)
    resource = getattr(request, "resource", _MISSING_FIELD)

    return (
        _valid_identifier(principal_id)
        and type(authenticated) is bool
        and _valid_identifier(membership_principal_id)
        and _valid_identifier(membership_workspace_id)
        and isinstance(role, WorkspaceRole)
        and type(active) is bool
        and _valid_identifier(request_id)
        and _valid_identifier(request_workspace_id)
        and isinstance(action, WorkspaceAction)
        and isinstance(resource, WorkspaceResource)
    )


def evaluate_workspace_access(
    principal: object,
    membership: object,
    request: object,
) -> WorkspaceAccessDecision:
    """Return one immutable policy decision without side effects."""
    if not _structurally_valid(principal, membership, request):
        return _decision(allowed=False, reason_code="invalid_request")
    return _decision(allowed=False, reason_code="role_action_denied")
```

- [ ] **Step 4: Run the structural tests**

Run:

```bash
python3 -m pytest tests/test_hosted_access_control.py -q
```

Expected: all structural and immutability tests pass.

- [ ] **Step 5: Run a focused style and whitespace check**

Run:

```bash
python3 -m ruff check src/hosted_access_control.py tests/test_hosted_access_control.py
git diff --check -- src/hosted_access_control.py tests/test_hosted_access_control.py
```

Expected: both commands exit 0.

- [ ] **Step 6: Synchronize the exact Task 1 paths as one coherent commit**

Because the original worktree index is read-only and stale, do not use it to recommit the already synchronized Priority 4 package. Create a controlled writable clone from the current remote head or use the GitHub Git Data API, include only:

```text
src/hosted_access_control.py
tests/test_hosted_access_control.py
```

Commit message:

```text
Add workspace authorization trust boundary
```

Verify the remote compare shows exactly those two paths and zero generated artifacts.

---

### Task 2: Implement Deterministic Isolation, Least Privilege, And Audit Decisions

**Files:**
- Modify: `src/hosted_access_control.py`
- Modify: `tests/test_hosted_access_control.py`

**Interfaces:**
- Consumes: the Task 1 enums, frozen dataclasses, `_decision`, and `_structurally_valid`.
- Produces: the complete `evaluate_workspace_access(principal: object, membership: object, request: object) -> WorkspaceAccessDecision` policy.

- [ ] **Step 1: Add failing tests for the exact allow matrix**

Append:

```python
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
```

- [ ] **Step 2: Add failing exhaustive deny-matrix and append-only tests**

Append:

```python
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
```

- [ ] **Step 3: Add failing tests for deterministic denial precedence**

Append:

```python
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
```

- [ ] **Step 4: Run the policy tests and confirm they fail against the Task 1 fallback**

Run:

```bash
python3 -m pytest tests/test_hosted_access_control.py -q
```

Expected: allow-matrix and ordered-denial assertions fail because the evaluator still returns `role_action_denied` for all structurally valid inputs.

- [ ] **Step 5: Implement the static matrix and deterministic decision order**

Insert above the evaluator:

```python
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
```

Replace the evaluator body with:

```python
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
```

- [ ] **Step 6: Run the complete focused authorization suite**

Run:

```bash
python3 -m pytest tests/test_hosted_access_control.py -q
```

Expected: all tests pass.

- [ ] **Step 7: Add audit privacy, Unicode, determinism, and side-effect tests**

Append:

```python
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
    before = (principal, membership, request)

    evaluate_workspace_access(principal, membership, request)

    assert (principal, membership, request) == before
    assert list(tmp_path.iterdir()) == []
```

- [ ] **Step 8: Add an import-boundary test**

Append:

```python
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
```

- [ ] **Step 9: Run focused authorization and existing private-beta tests**

Run:

```bash
python3 -m pytest \
  tests/test_hosted_access_control.py \
  tests/test_private_beta_readiness.py \
  -q
python3 -m ruff check src/hosted_access_control.py tests/test_hosted_access_control.py
git diff --check -- src/hosted_access_control.py tests/test_hosted_access_control.py
```

Expected: all tests and both static checks pass. Existing authentication, workspace, separation, audit, retention, entitlements, monitoring, health-check, incident, rollback, and owner-capacity states remain external or manually verified; none becomes hosted-ready.

- [ ] **Step 10: Synchronize the exact Task 2 paths as one coherent commit**

Include only:

```text
src/hosted_access_control.py
tests/test_hosted_access_control.py
```

Commit message:

```text
Enforce fail-closed workspace authorization
```

Verify the remote compare contains no dashboard, ledger, provider, readiness artifact, generated CSV/JSON/report, screenshot, or timing path.

---

### Task 3: Reconcile Truthful Priority 6 Documentation And Regression Evidence

**Files:**
- Modify: `docs/PRIVATE_BETA_ARCHITECTURE.md`
- Modify: `ROADMAP.md`
- Modify: `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`
- Modify: `tests/test_public_v1_release_docs.py`

**Interfaces:**
- Consumes: the implemented `src.hosted_access_control.evaluate_workspace_access` contract and passing Task 2 tests.
- Produces: truthful local-evidence documentation that leaves all real hosted and operated states external.

- [ ] **Step 1: Write the failing documentation regression test**

Append to `tests/test_public_v1_release_docs.py`:

```python
def test_provider_neutral_workspace_authorization_is_documented_without_hosted_claims():
    architecture = _read("docs/PRIVATE_BETA_ARCHITECTURE.md")
    roadmap = _read("ROADMAP.md")
    continuation = _read(
        "docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md"
    )

    for document in (architecture, roadmap, continuation):
        normalized = " ".join(document.split())
        assert "provider-neutral" in normalized
        assert "deny-by-default" in normalized
        assert "append-only" in normalized
        assert "privacy-safe audit obligation" in normalized
        assert "does not prove hosted authentication" in normalized

    assert "src.hosted_access_control.evaluate_workspace_access" in architecture
    assert "actual hosted environment" in roadmap
    assert "Do not create or change hosted accounts" in continuation
```

- [ ] **Step 2: Run the documentation test and confirm the missing-language failure**

Run:

```bash
python3 -m pytest \
  tests/test_public_v1_release_docs.py::test_provider_neutral_workspace_authorization_is_documented_without_hosted_claims \
  -q
```

Expected: FAIL because the three documents do not yet contain the exact local contract and non-claim language.

- [ ] **Step 3: Add the local contract section to the private-beta architecture**

In `docs/PRIVATE_BETA_ARCHITECTURE.md`, after `## Local Contract`, add:

```markdown
### Provider-Neutral Authorization Policy

`src.hosted_access_control.evaluate_workspace_access()` is a local,
provider-neutral, deny-by-default policy contract. It requires exact
authenticated-principal, active-membership, and workspace matches before an
explicit role/resource/action rule can allow a request. Thesis, evidence,
catalyst, and outcome research records remain append-only, and every allow or
deny result carries a privacy-safe audit obligation that a future approved
adapter must record.

The evaluator performs no authentication, persistence, audit storage,
retention, monitoring, network, provider, dashboard, ledger, readiness, or
generated-artifact operation. This local contract does not prove hosted
authentication, private-workspace isolation in a deployed service, audit
storage, retention execution, monitoring, rollback, incident response, or
operated capacity. All such states remain external until directly verified in
the actual approved environment.
```

- [ ] **Step 4: Record the completed local slice and unchanged exit gate in ROADMAP**

Under `### Priority 6 — Controlled hosted operating boundary`, insert after the current-lane paragraph:

```markdown
**Implemented locally:** `src.hosted_access_control.evaluate_workspace_access`
now provides one pure, provider-neutral, deny-by-default policy decision.
Structural validation, authenticated-principal matching, active membership,
exact workspace matching, least-privilege role/resource/action rules,
append-only research-record protection, stable privacy-safe reasons, and a
privacy-safe audit obligation are independently tested. The module has no
dashboard, ledger, readiness, provider, persistence, environment, network, or
generated-artifact integration. This local contract does not prove hosted
authentication, deployed isolation, audit storage, retention, monitoring,
rollback, incident response, operated capacity, or market validation.
```

Retain the existing sentence:

```markdown
**Exit gate:** the actual hosted environment directly proves every claimed control, including an observed rollback rehearsal and named owner. Local code, configuration, or a URL alone is insufficient.
```

- [ ] **Step 5: Reconcile the continuation contract with exact lineage and next lane**

Under `Priority 6 — Controlled hosted operating boundary` in `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`, add:

```markdown
- The first local slice implements
  `src.hosted_access_control.evaluate_workspace_access`, a pure,
  provider-neutral, deny-by-default contract for authenticated-principal,
  active-membership, workspace, role/resource/action, append-only
  research-record, stable reason, and privacy-safe audit-obligation decisions.
  It does not prove hosted authentication, deployed isolation, persistence,
  audit storage, retention, monitoring, rollback, incident response, operated
  capacity, or market validation.
- Reverify the exact implementation commit and exact-head CI before relying on
  the local contract. Do not create or change hosted accounts, choose a
  provider, use credentials, deploy, or publish without explicit approval.
- After this local policy slice passes, the next provider-neutral executable
  lane is a separately reviewed retention/deletion or append-only audit-event
  interface design. Provider-specific integration remains blocked until the
  exact identity, storage, logging, host, and operating environment are
  explicitly approved.
```

During the synchronization step, replace “the exact implementation commit” with the actual remote SHA rather than a guessed or local stale SHA.

- [ ] **Step 6: Run the focused documentation and private-beta regression suite**

Run:

```bash
python3 -m pytest \
  tests/test_public_v1_release_docs.py \
  tests/test_private_beta_readiness.py \
  tests/test_hosted_access_control.py \
  -q
git diff --check -- \
  docs/PRIVATE_BETA_ARCHITECTURE.md \
  ROADMAP.md \
  docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md \
  tests/test_public_v1_release_docs.py
```

Expected: all tests pass and whitespace is clean.

- [ ] **Step 7: Synchronize the exact Task 3 documentation commit**

Include only:

```text
docs/PRIVATE_BETA_ARCHITECTURE.md
ROADMAP.md
docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md
tests/test_public_v1_release_docs.py
```

Commit message:

```text
Document workspace authorization boundary
```

Verify the remote compare contains exactly those four files and zero generated artifacts.

---

### Task 4: Run Full Release Verification And Update Draft PR Evidence

**Files:**
- Verify only: all six Task 1–3 intentional paths plus this reviewed plan,
  for seven paths total.
- Update externally: draft PR #113 description.
- Do not modify: generated CSV/JSON/report/sample-report/screenshot/timing artifacts.

**Interfaces:**
- Consumes: the synchronized authorization module, tests, and documentation.
- Produces: current local and exact-head CI evidence for the isolated Priority 6 slice.

- [ ] **Step 1: Run the focused authorization and documentation suites**

Run:

```bash
python3 -m pytest \
  tests/test_hosted_access_control.py \
  tests/test_private_beta_readiness.py \
  tests/test_public_v1_release_docs.py \
  -q
```

Expected: all focused tests pass.

- [ ] **Step 2: Run the complete automated test suite**

Run:

```bash
python3 -m pytest tests -q
```

Expected: the complete suite passes, except only an already classified environment-limited skip or existing dependency warning may remain.

- [ ] **Step 3: Run the required product and release gates**

Run each command independently:

```bash
make dashboard-smoke
make research-dashboard-render
make commercial-beta-check
make commercial-beta-performance-check
make public-wording-check
make browser-qa-evidence-check
make pilot-readiness-check TOP_N=10
make diff-hygiene-summary
git diff --check
```

Expected:

- dashboard, render, commercial-beta, performance, public wording, browser evidence, diff hygiene, and whitespace gates pass;
- pilot readiness may remain truthfully blocked because saved readiness is stale;
- no command writes or promotes readiness artifacts.

- [ ] **Step 4: Confirm generated-artifact exclusion**

Run:

```bash
git diff -- \
  data/analyst_estimates_readiness.csv \
  data/dcf_readiness.csv \
  data/earnings_readiness.csv \
  data/price_coverage_report.csv \
  data/reports/analyst_estimates_readiness_report.csv \
  data/reports/data_source_status.csv \
  data/reports/dcf_readiness_report.csv \
  data/reports/earnings_readiness_report.csv \
  data/reports/feature_readiness_summary.csv \
  data/reports/fundamentals_coverage_report.csv \
  data/reports/peer_readiness_report.csv \
  data/reports/peer_unlock_worklist.csv \
  data/reports/price_coverage_report.csv \
  data/reports/ticker_readiness_report.csv \
  data/reports/universe_coverage_report.csv \
  data/universe_master.csv \
  outputs/feature_readiness_summary.csv \
  outputs/peer_unlock_worklist.csv | shasum -a 256
```

Expected:

```text
a2c2f428b489dbb291dd54fd8a6e1e7f4ad9481414320ca248c54be89f4062b9  -
```

- [ ] **Step 5: Verify the final remote compare and draft PR state**

Confirm:

```text
branch: codex/personal-research-mode-mvp
PR: #113
state: open
draft: true
merged: false
generated paths in this slice: 0
```

The authoritative reviewed slice from
`3c5a2bc8fc47ac144290087e9dad513bb683252c` must contain only these seven
paths:

```text
src/hosted_access_control.py
tests/test_hosted_access_control.py
docs/PRIVATE_BETA_ARCHITECTURE.md
ROADMAP.md
docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md
tests/test_public_v1_release_docs.py
docs/superpowers/plans/2026-07-26-provider-neutral-workspace-authorization.md
```

- [ ] **Step 6: Require exact-head GitHub Actions success**

Wait for the current PR head’s `Commercial Research Beta` workflow to complete. Require successful:

```text
full test suite
dashboard startup
Personal Research route render
public wording
generated-artifact hygiene
whitespace
```

Do not reuse an earlier commit’s CI result.

- [ ] **Step 7: Update draft PR #113 with truthful evidence**

Record:

- the exact implementation and documentation commit SHAs;
- focused and full test counts;
- each release-gate result;
- unchanged generated-artifact fingerprint;
- the provider-neutral, deny-by-default, cross-principal, cross-workspace, append-only, and audit-obligation behavior;
- that authentication, deployed isolation, audit storage, retention, monitoring, rollback, incident response, operated capacity, external validation, and market maturity remain unproven;
- the exact next safe executable lane.

Keep the PR open and draft. Do not merge or deploy.

- [ ] **Step 8: Hand off the verified slice**

Report:

- authoritative remote branch and PR status;
- product stage;
- files and behavior added;
- focused/full/release/CI evidence;
- generated artifacts excluded;
- external dependencies and exact unblock conditions;
- remaining maturity gates;
- exact next executable step;
- whether the branch is safe for review;
- whether the overall goal remains active.
