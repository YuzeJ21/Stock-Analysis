# Durable workspace access audit

## Goal and scope

Persist privacy-minimized authorization decisions for protected Workbench and Monitor reads, append/update attempts and denials before permitting the corresponding operation. Keep source-rights holds and the personal local workflow unchanged.

The implementation is limited to `src/workspace_audit.py`, the workspace authorization adapter and route entry, explicit protected-test configuration, automated audit tests, the Makefile verification target and current product/runbook documentation. No new product dashboard, hosting, source-rights approval, retention automation or schema change to saved research is included.

## Acceptance

- An independent, explicitly configured local SQLite sink survives server restarts, serializes concurrent writers and commits decisions before access proceeds.
- Both policy and pre-policy denials are recorded. Missing/unusable audit storage prevents protected access. Personal mode does not initialize audit storage.
- Events use fixed versioned fields, UTC timestamps, random request IDs, hashed verified principal/workspace identifiers, action, resource, outcome and bounded reason codes. They exclude claims, tokens, personal research, ticker/issuer identifiers, source payloads and storage paths.
- Events describe access decisions, not proof that a subsequent mutation completed. Read-only capability probes do not become recorded write attempts. There is no application update/delete API for audit events.
- Automated tests cover identity/configuration failures, role/scope denials, concurrency, restart persistence, invalid schema/corrupt/unsafe/unavailable storage, and no private-store mutation on audit failure.
- Desktop and phone exercise exact saved Workbench–Monitor replay, one editor append, stale/revoked/foreign access, visible source-rights gaps and audit outage. Canonical data and source-rights registry remain unchanged.

## Execution

1. Confirm a failing browser case on the baseline (protected reads produced no audit database).
2. Add the backend and authorization wiring; test the storage contract and private read/write failure paths.
3. Run the expanded `make workspace-authorization-check`, research-route renders and public-document/hygiene checks with the declared runtime.
4. Update local evidence and remaining hosted/retention gates, commit only reviewed files and synchronize GitHub main without rewriting history.

## Limits

The SQLite file is local, application-append-only evidence. A same-user administrator can replace it. Real identity-provider/host verification, off-host backup and tamper resistance, retention/deletion policy, identity-provider sign-in events and administrative membership changes remain separate work. An unavailable sink cannot record its own failure; protected operations stop and emit only a generic server diagnostic.
