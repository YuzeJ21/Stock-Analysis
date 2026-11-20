# Workspace authorization

Workbench and Monitor can enforce the existing workspace policy at runtime. Protected mode uses Streamlit's authenticated OIDC user and a server-owned membership registry. Each process serves one configured workspace. Its profile, storage root and membership roles come from that registry. Client query parameters and session widgets cannot assign identity, roles or a storage profile.

## Configure the protected process

Install the workspace authentication dependency with `pip install -e '.[workspace]'`. Configure Streamlit OIDC authentication outside Git using its normal secrets configuration. Identity claims must include `is_logged_in`, `iss`, `sub`, `aud` and a future numeric `exp`. If present, `nbf` and `iat` must permit use at the current time. Issuer and audience must match the registry. The app checks these claims again at each protected operation. [Streamlit authentication](https://docs.streamlit.io/develop/concepts/connections/authentication)

Create an untracked, absolute, canonical registry path owned by the server user. Its file permissions must prohibit group and other writes. Symlinked configuration paths are rejected. Use atomic file replacement when changing membership. The following identifiers are synthetic.

```json
{
  "schema_version": "research-workspace-access-v1",
  "issuer": "https://identity.example",
  "audience": "stock-research",
  "storage_root": "/absolute/private/research-store",
  "workspaces": {
    "alpha": {
      "profile_key": "workspace-alpha",
      "members": [
        {"subject": "alice", "role": "editor", "active": true},
        {"subject": "bob", "role": "viewer", "active": true}
      ]
    }
  }
}
```

Set `STOCK_RESEARCH_WORKSPACE_CONFIG` to that file and `STOCK_RESEARCH_WORKSPACE_ID` to `alpha` before starting the server. Also set `STOCK_RESEARCH_WORKSPACE_AUDIT_DB` to an absolute, canonical file path in a dedicated private local directory outside Git and the research stores. Its immediate directory must belong to the server user with mode `0700`; the adapter can create that one directory if its parent already exists. Audit files must have mode `0600`. Symlinks, hard-linked files and unsafe permissions are rejected. The adapter creates the SQLite file and its separate private initialization lock.

`STOCK_RESEARCH_ACCESS_MODE=workspace` may be set explicitly. Either workspace setting activates protection. Missing, conflicting, unreadable or malformed settings deny access. Protected mode requires the independent audit setting; it does not silently choose a personal-data path. Explicit `local` mode conflicts with workspace settings and is rejected. An installation with no workspace settings retains its personal local workflow. The audit setting alone neither activates protected mode nor opens a log in personal mode.

Profiles must be unique across the workspace registry. The adapter binds private snapshots, notes, SEC receipts and review decisions to the selected profile in the configured storage root. Caller-supplied roots cannot redirect these operations. Optional workspace model paths use `workspaces/<workspace-id SHA-256>/data` and `outputs` under the same root. Protected routes start with company search and the scoped evidence workflow. Personal legacy journals, operator routes and shared personal model files are outside that route.

## Reads and writes

The existing policy governs viewer, editor and owner actions. Viewers can read their workspace research. Editors and owners can append research records and snapshots and update exact-pair review decisions. Notes remain append-only. Protected record paths must match the configured root, selected profile, issuer and ticker. The guards run before filesystem reads, locks and writes, including direct store calls and confirmation of a previously rendered authoring preview.

Membership is read again for every operation. Downgrade or revocation therefore applies to a stale save action and to the next page load. Identity changes clear the app's retained research state. Already delivered content cannot be recalled from a browser. Export through Streamlit's prebuilt download artifacts is held in protected mode pending an authorized delivery endpoint. Source permissions continue to govern data independently of workspace role.

## Durable access decisions

`src.workspace_audit` commits an event before an audited authorization check can permit access. Events survive process restart. SQLite uses rollback journaling with `synchronous=EXTRA`, a bounded transaction timeout and a separate private lock for concurrent initialization. The adapter checks the effective synchronization setting and versioned schema. [SQLite synchronization](https://www.sqlite.org/pragma.html#pragma_synchronous) · [SQLite transaction locking](https://www.sqlite.org/lockingv3.html)

The fixed `research-workspace-audit-v1` record contains a sequence number, `workspace_access_decision` event type, random request ID, UTC occurrence time, hashed verified principal, hashed selected workspace, resource, action, `allowed`/`denied` outcome and a bounded reason code. Invalid or missing authentication never contributes a claimed principal. Invalid configuration contributes neither a principal nor a workspace. No email, subject, token, raw claims, profile, ticker, CIK, research text, snapshot ID, provider payload or filesystem path is logged. Hashes are pseudonymous identifiers and still need a retention policy.

Records cover route access and the private store guards, including snapshot/notes/SEC reads, append/update authorization, invalid identity/configuration, inactive memberships, wrong profiles, role denials, invalid record destinations and unavailable protected routes. An unknown saved ID is indistinguishable from a foreign one: an authorized lookup can remain unavailable without identifying or opening the other workspace's record. UI capability probes that decide whether to show an editor control are not write attempts and do not emit events. Actual store checks remain mandatory.

An event records an authorization decision, not confirmation that a later read or mutation completed. One page or save can invoke several guards and produce several events with distinct request IDs. A write that fails after authorization retains the allowed decision without claiming a completed write. Audit and research files do not form one cross-file transaction. Saved research inputs and source-rights decisions are unchanged by auditing.

Missing, corrupt, schema-incompatible, unsafe, locked or unwritable audit storage blocks protected reads and writes. The browser shows the same generic access-unavailable state. If the sink itself is unavailable it cannot persist that failure; the server emits only a generic diagnostic without content or paths. It never falls back to a memory buffer or continues an unlogged private operation. Recover the retained sink before retrying; do not erase it to bypass a hold.

There is no application update/delete API or product log viewer. Database triggers reject event updates and deletions. Server operators can inspect a bounded sequence of retained events using `read_workspace_audit(path, limit=1000)` in a trusted local process. Keep the database and its sidecar files outside public artifacts and exports. A same-user administrator can still replace or alter the database. This is local application-append-only evidence; off-host backup, tamper resistance, retention/deletion execution, identity-provider sign-in events and administrative membership-change auditing remain separate controls.

## Verification and remaining gates

Run `make workspace-authorization-check`. The expanded audit run passed **580 cases in 171.66 seconds** on November 20, 2026 with the declared Streamlit 1.62.0 and Playwright 1.62.0 runtime. There were zero skips and one existing dateutil warning. It exercises claims, registry failures, direct snapshot/notes/SEC access, role restrictions, foreign paths, revoked confirmations, changes during queued writes, personal-mode compatibility, concurrent audit writers, invalid/unavailable audit storage and the real Workbench and Monitor routes on desktop and phone. All six personal research routes rendered, and 97 public-document checks passed separately. Browser identities and membership changes are synthetic and confined to disposable test servers. Production code reads `st.user`; it has no test identity input or client-assigned principal.

The current adapter requires a real identity-provider configuration and deployment review before hosted use. Local durable access-decision storage does not complete hosted audit continuity, backup, session revocation at the identity provider, retention and deletion, authorized export delivery, shared provider-rate controls or operated recovery. These need verification in the intended environment. The source-rights registry still holds Yahoo commercial use and redistribution. [Pilot audit](PILOT_READINESS_AUDIT.md) · [Private beta architecture](PRIVATE_BETA_ARCHITECTURE.md)
