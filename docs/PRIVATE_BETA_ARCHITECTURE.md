# Private Beta Architecture

## Boundary

The repository contains a deterministic readiness contract for a future private beta. It does not implement runtime authentication, private workspaces, hosted persistence, user accounts, entitlements, audit storage, monitoring, health checks, or hosting. Real user evidence remains `awaiting_external_review`.

The contract is available through `src.private_beta_readiness.build_private_beta_readiness()`. It accepts only declared review facts; it does not inspect environment variables, scan files, open accounts, contact a host, or read secret material.

| Classification | Meaning | Required action |
| --- | --- | --- |
| `local_ready` | Repository-side guidance is present, while account-backed capabilities remain external. | Complete the external setup below. |
| `external_account_required` | An individual capability needs a real hosted account or service. | Do not represent the capability as available. |
| `manual_verification_required` | An external setup has been declared, but it has not been independently verified. | Verify the live behavior before any access or product claim. |
| `unsafe_secret_blocked` | A tracked or otherwise unsafe secret condition has been declared. | Remove it from tracked files, rotate it outside the repository, then repeat the review. |

## Data Boundaries

Private-beta data, when it exists, must be partitioned by authenticated user and workspace. Per-user watchlists, thesis journals, saved scenarios, audit events, and entitlement data belong in the external private-beta service, not in tracked repository files, public demo data, screenshots, generated reports, or logs.

The future service must enforce workspace authorization server-side for every read and write. Client-side visibility, UI routing, or a workspace identifier alone does not establish isolation. Research evidence and readiness remain source-bound and research-only; private access does not turn incomplete data into a trusted input or an investment recommendation.

Credentials, tokens, account identifiers, license documents, and secret values remain outside Git. The repository may carry only blank templates and variable names. Usage and error telemetry must exclude credentials and research-workspace contents unless a separately reviewed retention policy authorizes a minimal, documented record.

## External Setup Sequence

1. Create the chosen hosting, identity, and managed-persistence accounts outside this repository.
2. Configure an identity provider, an allowed-user invitation path, session expiry, and account recovery; verify them with non-production test accounts.
3. Create private workspaces and server-side authorization rules that scope watchlists, journals, scenarios, and uploaded evidence to the authenticated user and workspace.
4. Configure encrypted platform secret storage. Add only the required variable names, never secret values, to repository templates; rotate any credential exposed outside that store.
5. Configure audit events for sign-in, workspace membership, export, deletion, and entitlement changes. Define a retention and deletion policy before retaining beta-user data.
6. Configure role and entitlement rules, including revocation, and test that unauthorized users cannot read or modify another workspace.
7. Configure privacy-safe usage and error monitoring, alert routing, and health checks for the hosted entrypoint and backing services.
8. Run a supervised external verification with real test accounts. Record the outcome as `awaiting_external_review`, `manual_verification_required`, or another evidence-backed state; do not infer readiness from setup alone.

## Local Contract

The classifier reports the following areas: authentication, workspaces, user data separation, secrets, audit, retention, entitlements, monitoring, and health checks. It is intentionally read-only.

```python
from src.private_beta_readiness import build_private_beta_readiness

readiness = build_private_beta_readiness()
assert readiness.classification == "local_ready"
```

Passing `external_setup_declared=True` produces `manual_verification_required`, not a hosted or authenticated claim. Passing `unsafe_secret_detected=True` produces `unsafe_secret_blocked`; pass only the declared condition, never a credential or secret value.

## Non-Claims

No current repository state proves that a private-beta host exists, authentication is live, user data is separated, retention works, entitlements are enforced, audit logs are stored, monitoring receives events, or health checks run. Do not present this contract as commercial launch readiness, hosting evidence, or user validation.
