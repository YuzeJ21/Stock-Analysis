# Private Beta Architecture

## Boundary

The [November 18 Workbench and Monitor audit](PILOT_READINESS_AUDIT.md#workbench-and-monitor-private-pilot) records the private pilot hold, the tested local controls, and the evidence needed for hosted operation.

The repository contains a deterministic readiness contract and an opt-in runtime authorization adapter for Workbench and Monitor. Protected processes use Streamlit's authenticated identity and a server-owned workspace registry, with a separate local SQLite access-decision log. Authentication-provider setup, hosted persistence and audit continuity, retention, monitoring, health checks and operated recovery still need verification in the intended environment. Real user evidence remains `awaiting_external_review`. [Runtime configuration and scope](WORKSPACE_AUTHORIZATION.md)

The contract is available through `src.private_beta_readiness.build_private_beta_readiness()`. It accepts only declared review facts; it does not inspect environment variables, scan files, open accounts, contact a host, or read secret material.

| Classification | Meaning | Required action |
| --- | --- | --- |
| `local_ready` | Repository-side guidance is present, while account-backed capabilities remain external. | Complete the external setup below. |
| `external_account_required` | An individual capability needs a real hosted account or service. | Do not represent the capability as available. |
| `external_operations_required` | An operating control needs a staffed hosted rehearsal, not only repository guidance. | Assign owners and rehearse the control in the actual environment before claiming it. |
| `manual_verification_required` | An external setup has been declared, but it has not been independently verified. | Verify the live behavior before any access or product claim. |
| `unsafe_secret_blocked` | A tracked or otherwise unsafe secret condition has been declared. | Remove it from tracked files, rotate it outside the repository, then repeat the review. |

## Data Boundaries

Private-beta data, when it exists, must be partitioned by authenticated user and workspace. Per-user watchlists, thesis journals, saved scenarios, audit events, and entitlement data belong in the external private-beta service, not in tracked repository files, public demo data, screenshots, generated reports, or logs.

The runtime adapter enforces the selected workspace and live membership before private snapshot, note, SEC receipt and disposition reads and writes. It also guards the low-level record paths and rechecks previously rendered confirmations. The deployment must bind a real authenticated identity to those requests and verify the controls there. Research evidence and readiness retain their independent source and eligibility gates.

Credentials, tokens, account identifiers, license documents, and secret values remain outside Git. The repository may carry only blank templates and variable names. Usage and error telemetry must exclude credentials and research-workspace contents unless a separately reviewed retention policy authorizes a minimal, documented record.

## External Setup Sequence

1. Create the chosen hosting, identity, and managed-persistence accounts outside this repository.
2. Configure an identity provider, an allowed-user invitation path, session expiry, and account recovery; verify them with non-production test accounts.
3. Create private workspaces and server-side authorization rules that scope watchlists, journals, scenarios, and uploaded evidence to the authenticated user and workspace.
4. Configure encrypted platform secret storage. Add only the required variable names, never secret values, to repository templates; rotate any credential exposed outside that store.
5. Configure audit events for sign-in, workspace membership, export, deletion, and entitlement changes. Define a retention and deletion policy before retaining beta-user data.
6. Configure role and entitlement rules, including revocation, and test that unauthorized users cannot read or modify another workspace.
7. Configure privacy-safe usage and error monitoring, alert routing, and health checks for the hosted entrypoint and backing services.
8. Define incident response severity, escalation, reviewer-access shutdown, evidence preservation, communication ownership, and recovery criteria.
9. Keep the previous verified revision available, rehearse rollback in the hosted environment, and record who can execute and verify recovery.
10. Confirm owner capacity for source failures, access incidents, reviewer support, and recovery; a named document without available coverage is not operating proof.
11. Run a supervised external verification with real test accounts. Record the outcome as `awaiting_external_review`, `manual_verification_required`, or another evidence-backed state; do not infer readiness from setup alone.

## Local Contract

### Provider-Neutral Authorization Policy

`src.hosted_access_control.evaluate_workspace_access()` is a local,
provider-neutral, deny-by-default policy contract. It requires exact
authenticated-principal, active-membership, and workspace matches before an
explicit role/resource/action rule can allow a request. Thesis, evidence,
catalyst, and outcome research records remain append-only, and every allow or
deny result carries a privacy-safe audit obligation. The protected runtime
adapter persists the decision before permitting access.

`src.workspace_authorization` connects this evaluator to the protected research routes and stores. A server process selects one workspace, and each operation reloads membership and revalidates the trusted user's issuer, audience, subject and token expiry. `src.workspace_authorization_ui` enters before the personal model and event loaders. Protected-mode legacy and operator routes are unavailable. The existing single-user personal mode remains available when no workspace settings are present.

`src.workspace_audit` supplies the protected adapter's separate, explicitly configured local sink. It records versioned pseudonymous access decisions, including pre-policy denials, without research contents or raw identity claims. Missing or unusable storage denies private access. The log records authorization, not completed mutation, and is application-append-only rather than administrator-tamper-proof. Personal mode does not open it. Hosted persistence, backup, retention/deletion and additional identity/administration events remain external gates. [Audit contract and limits](WORKSPACE_AUTHORIZATION.md#durable-access-decisions)

The evaluator performs no authentication, persistence, audit storage,
retention, monitoring, network, provider, dashboard, ledger, readiness, or
generated-artifact operation. This local contract does not prove hosted
authentication, private-workspace isolation in a deployed service, audit
storage, retention execution, monitoring, rollback, incident response, or
operated capacity. All such states remain external until directly verified in
the actual approved environment.

The classifier reports authentication, workspaces, user data separation, secrets, audit, retention, entitlements, monitoring, and health checks independently from incident response, rollback, and owner capacity. It is intentionally read-only.

A local runbook does not prove that an incident owner is available, rollback works on the host, or recovery can be staffed. Without a real rehearsal, those controls remain `external_operations_required`; declaring external setup moves them only to `manual_verification_required`.

```python
from src.private_beta_readiness import build_private_beta_readiness

readiness = build_private_beta_readiness()
assert readiness.classification == "local_ready"
```

Passing `external_setup_declared=True` produces `manual_verification_required`, not a hosted or authenticated claim. Passing `unsafe_secret_detected=True` produces `unsafe_secret_blocked`; pass only the declared condition, never a credential or secret value.

## Deployment evidence still required

Local automated tests use synthetic authenticated claims and server-side memberships. They verify the guarded app routes and storage actions. A private-beta host, real identity-provider sessions, managed storage isolation, retention, durable audit, monitoring, incident staffing and recovery still need evidence in the intended environment. Source permissions and independent researcher completion remain open.
