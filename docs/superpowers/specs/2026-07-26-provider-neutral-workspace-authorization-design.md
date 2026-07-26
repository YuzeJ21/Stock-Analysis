# Provider-Neutral Workspace Authorization Design

## Status

Approved design direction for the first local slice of Roadmap Priority 6.

This specification defines a deterministic, deny-by-default authorization and
workspace-isolation contract. It is local software evidence only. It does not
implement or prove authentication, hosting, private persistence, audit storage,
retention, monitoring, rollback, incident response, or operated capacity.

## Problem

`src.private_beta_readiness` truthfully classifies future hosted capabilities
as external, and `docs/PRIVATE_BETA_ARCHITECTURE.md` states that every hosted
read and write must be authorized server-side. The repository does not yet
have a reusable policy decision that can answer:

- whether the caller is authenticated;
- whether the caller and membership refer to the same principal;
- whether the membership is active;
- whether the request and membership refer to the same workspace;
- whether the role may perform the requested action on the resource class;
- whether append-only research records are protected from update or deletion;
- and which privacy-safe audit event a future hosted adapter must record.

Without one shared decision contract, future identity, storage, API, or UI
adapters could independently reconstruct these rules and drift on
cross-workspace denial, revocation, append-only behavior, or audit obligations.

## Goals

1. Add one pure provider-neutral authorization decision used by future hosted
   adapters.
2. Deny by default for missing, malformed, unauthenticated, inactive,
   mismatched, unsupported, or unauthorized requests.
3. Make principal and workspace isolation explicit and independently tested.
4. Preserve append-only behavior for thesis, evidence, catalyst, and outcome
   research records.
5. Return stable, non-sensitive reason codes and an audit obligation for every
   allow or deny decision.
6. Keep the contract independent from Streamlit, research ledgers, readiness,
   source rights, forecasts, probabilities, and generated artifacts.

## Non-Goals

This slice does not:

- choose or integrate an identity provider;
- create sessions, accounts, invitations, password recovery, or MFA;
- choose a hosting, database, storage, logging, monitoring, or secrets vendor;
- read environment variables, tokens, cookies, headers, credentials, or
  research content;
- persist audit events;
- implement retention, deletion execution, backup, recovery, or rollback;
- add private workspace UI or connect the public/local dashboard to the
  contract;
- migrate local thesis, evidence, catalyst, outcome, watchlist, or scenario
  data;
- change readiness, source rights, research conclusions, forecasts,
  probabilities, recommendations, ranking, or transaction behavior;
- claim hosted authentication, isolation, commercial launch readiness, or user
  validation.

## Considered Approaches

### A. Pure policy decision with stable domain contracts — selected

Create one focused module with immutable request, membership, decision, and
audit-obligation types plus a pure evaluator. This gives future adapters a
single testable boundary without choosing infrastructure or touching local
research data.

### B. Full hosted-control abstraction

Define authentication, persistence, retention, audit storage, monitoring, and
rollback interfaces together. This was rejected for the first slice because it
would combine independent operating systems, encourage speculative vendor
abstractions, and make local code look stronger than direct hosted evidence.

### C. Documentation-only threat model

Expand `docs/PRIVATE_BETA_ARCHITECTURE.md` without executable policy. This was
rejected because it would not prevent future adapters from drifting on
principal, workspace, revocation, append-only, or audit rules.

## Threat Boundary

The contract addresses only authorization-policy risks that can be decided
from already authenticated, provider-neutral facts:

- an unauthenticated caller reaches a future adapter;
- a caller substitutes another principal identifier;
- a caller substitutes another workspace identifier;
- a stale or revoked membership is reused;
- a caller requests an unknown action or resource class;
- a role exceeds its least-privilege boundary;
- an editor or owner attempts to update or delete append-only research
  records;
- a future adapter records a decision without the required privacy-safe audit
  fields;
- structural identifiers contain controls, separators, non-scalar values, or
  unreasonable lengths that could corrupt logs or comparisons.

The contract does not validate credentials or establish that an authentication
provider, session, membership record, or audit sink is genuine. A future
adapter must supply those facts from its approved environment.

## Module Boundary

Create `src/hosted_access_control.py`. It must depend only on the Python
standard library and must not import dashboard, ledger, readiness, provider,
source-rights, or generated-data modules.

The module exposes:

```python
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


def evaluate_workspace_access(
    principal: object,
    membership: object,
    request: object,
) -> WorkspaceAccessDecision:
    ...
```

The public evaluator accepts `object` at the trust boundary so malformed
caller values fail closed through one stable decision rather than raising
before policy evaluation. The immutable dataclasses remain the supported
well-formed inputs.

## Structural Input Contract

`principal_id`, `workspace_id`, and `request_id` are opaque identifiers, not
display labels or secrets. A valid identifier:

- is a Python `str`;
- is between 1 and 128 Unicode scalar values;
- has no leading or trailing whitespace;
- contains no C0/C1 controls, Unicode line or paragraph separators, or lone
  surrogate code points.

Ordinary non-ASCII scalar identifiers are allowed. The evaluator never
normalizes, truncates, repairs, hashes, aliases, or prints an invalid value.

`authenticated` and `active` must be exact booleans. Role, action, and resource
must be members of their declared enums; arbitrary strings do not gain
authority.

Malformed objects or fields return `invalid_request` and never raise an
expected authorization exception.

## Decision Order

The evaluator applies one deterministic order:

1. Validate the three object types and every structural field. Otherwise deny
   with `invalid_request`.
2. Require `principal.authenticated is True`. Otherwise deny with
   `authentication_required`.
3. Require `membership.principal_id == principal.principal_id`. Otherwise deny
   with `principal_mismatch`.
4. Require `membership.active is True`. Otherwise deny with
   `membership_inactive`.
5. Require `request.workspace_id == membership.workspace_id`. Otherwise deny
   with `workspace_mismatch`.
6. Apply the static role/resource/action policy. If no exact allow rule exists,
   deny with the most specific stable policy reason below.
7. Return `allowed` only for an exact allow rule.

No later rule can override an earlier denial. Input order, object identity, or
caller-supplied labels cannot change the result.

## Policy Matrix

| Resource | Viewer | Editor | Owner |
| --- | --- | --- | --- |
| `research_record` | `read` | `read`, `append` | `read`, `append`, `export` |
| `saved_workspace_state` | `read` | `read`, `append`, `update` | `read`, `append`, `update`, `delete`, `export` |
| `workspace_membership` | none | none | `read`, `manage` |
| `workspace_audit` | none | none | `read`, `export` |

Additional invariant:

- `update` and `delete` on `research_record` are always denied with
  `append_only_mutation_denied`, including for owners.

Other well-formed actions that are absent from the exact matrix are denied
with `role_action_denied`. The evaluator grants no wildcard, role inheritance
outside the table, implicit owner bypass, or caller-configurable policy.

The `research_record` class represents thesis, evidence, catalyst, and outcome
records only. This slice does not authorize writes to canonical market data,
readiness, source-rights records, forecasts, probabilities, or proof ledgers.

## Audit Obligation

Every decision returns an `AuditObligation`; the evaluator does not persist it.

The obligation is:

```python
AuditObligation(
    event_type="workspace_access_decision",
    outcome="allowed" or "denied",
    reason_code=<same stable reason as the decision>,
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
)
```

The contract requires identifiers and policy metadata only. It must not accept
or request:

- credentials, tokens, cookies, API keys, session secrets, or headers;
- thesis, evidence, catalyst, outcome, scenario, watchlist, filing, consensus,
  or valuation content;
- source documents, URLs, excerpts, forecasts, probabilities, recommendations,
  position data, or transaction data.

An audit obligation is not an audit event and does not prove that any sink
stored it.

## Stable Reason Codes

The first slice supports exactly:

- `allowed`
- `invalid_request`
- `authentication_required`
- `principal_mismatch`
- `membership_inactive`
- `workspace_mismatch`
- `append_only_mutation_denied`
- `role_action_denied`

Reason codes contain no caller values. Rendering or logging a decision therefore
cannot echo an identifier, secret, or research content through the reason.

## Error Handling

Expected authorization failures return denied decisions. The evaluator does
not:

- throw for an unauthenticated, inactive, mismatched, unknown, or unauthorized
  request;
- contact an external system;
- fall back to viewer, editor, owner, public, operator, or local mode;
- infer a role or workspace;
- repair malformed identifiers;
- retry a decision;
- mutate any input;
- write a file, ledger, report, cache, environment variable, or audit record.

Unexpected programmer defects remain ordinary exceptions; tests must not catch
broad exceptions and convert them into an allow result.

## Integration Boundary

The first slice remains isolated:

- no dashboard route imports the module;
- no local research ledger calls the evaluator;
- no readiness state is promoted;
- no current public, research, operator, or legacy mode changes;
- no generated data or runtime configuration is added.

`docs/PRIVATE_BETA_ARCHITECTURE.md`, `ROADMAP.md`, and the continuation contract
will record that a local policy contract exists while all runtime and operated
controls remain external. `src.private_beta_readiness` may describe the local
contract in existing check detail, but authentication, workspaces, user-data
separation, audit, retention, entitlements, monitoring, health checks,
incident response, rollback, and owner capacity must retain their current
external or manual states.

## Testing Strategy

Create `tests/test_hosted_access_control.py` with real pure-function tests:

1. Parameterize every exact allow entry in the policy matrix.
2. Parameterize representative absent entries for every role and resource.
3. Prove research-record update and delete are denied for every role.
4. Prove unauthenticated, principal-mismatched, inactive, and
   workspace-mismatched requests fail in the declared order.
5. Prove malformed objects, booleans, enums, empty identifiers, surrounding
   whitespace, controls, separators, lone surrogates, and identifiers longer
   than 128 values return `invalid_request`.
6. Prove ordinary Unicode scalar identifiers remain deterministic.
7. Prove equal inputs return equal immutable decisions and input objects are
   unchanged.
8. Prove every allow and deny result carries the exact audit obligation.
9. Prove the public dataclasses and audit requirements contain no secret,
   credential, research-content, recommendation, position, or transaction
   field.
10. Prove the module performs no file, environment, ledger, network, provider,
    dashboard, or readiness operation.

Documentation regression tests must preserve:

- deny-by-default and cross-workspace language;
- append-only research-record protection;
- privacy-safe audit obligations;
- provider-neutral isolation;
- unchanged external hosted and operated gates;
- no claim of runtime authentication, hosting, audit storage, or market
  validation.

## Verification

After implementation:

1. Run the new focused authorization tests and existing private-beta readiness
   tests.
2. Run documentation regression tests.
3. Run the complete test suite.
4. Run Research route render, commercial-beta, performance, public-wording,
   browser-evidence, pilot-readiness, diff-hygiene, staged-hygiene, and
   whitespace gates.
5. Confirm the 18 existing generated CSV/report changes and their fingerprint
   remain unchanged and unstaged.
6. Synchronize exact intentional code, tests, and documentation only to
   `codex/personal-research-mode-mvp`.
7. Keep PR #113 open and draft and require exact-head CI.

## Acceptance Criteria

The slice is complete only when direct current evidence proves:

1. one pure provider-neutral evaluator owns the policy;
2. every missing, malformed, unauthenticated, inactive, mismatched,
   unsupported, and unauthorized request is denied;
3. cross-principal and cross-workspace requests cannot pass;
4. append-only research records cannot be updated or deleted by any role;
5. every allow and deny result carries the stable privacy-safe audit
   obligation;
6. reason codes never contain caller values;
7. the evaluator has no persistence, network, environment, dashboard, ledger,
   readiness, provider, or generated-artifact side effect;
8. existing private-beta checks keep runtime and operated controls external;
9. full local verification and exact-head CI pass;
10. generated artifacts remain excluded;
11. no hosted, authenticated, isolated, audited, retained, monitored,
    recoverable, operated, or market-ready capability is claimed from the
    local contract.
