# Runtime workspace authorization plan

Connect the existing workspace policy to the production Workbench and Monitor routes and their persistence APIs. Use one server-selected workspace per protected process. Preserve the existing personal workflow when no workspace settings exist.

## Accepted scope

- Trust Streamlit OIDC claims and a server-owned membership registry. Revalidate issuer, audience, subject, expiry and active membership at every protected operation.
- Bind profile and storage roots on the server. Refuse foreign workspace reads and writes, mismatched file destinations, viewer writes and revoked confirmations. Clear retained app state after identity changes.
- Enter protected routes before personal data, cohort or event loaders. Reuse online company search, Workbench and the scoped Monitor lanes. Keep source-rights gaps visible and hold export until delivery authorization is available.
- Exercise direct persistence APIs and stale UI actions using synthetic users on desktop and phone. Retain local-mode regressions and protect existing data during the run.

## Implementation and verification

`src/workspace_authorization.py` adapts the existing policy. `src/workspace_authorization_ui.py` composes the protected routes. Snapshot, note, authoring, ledger, SEC receipt and disposition modules enforce scope before their filesystem operations. UI controls reflect permitted actions and persistence guards independently enforce them.

`make workspace-authorization-check` runs the adapter, storage, ledger, authorization, legacy compatibility and browser cases under the protected-artifact guard. The pilot audit records the resulting count and remaining deployment gates. Real OIDC configuration, hosted testing, durable audit, retention and provider permissions remain open.
