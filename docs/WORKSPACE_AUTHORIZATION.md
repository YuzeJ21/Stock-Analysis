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

Set `STOCK_RESEARCH_WORKSPACE_CONFIG` to that file and `STOCK_RESEARCH_WORKSPACE_ID` to `alpha` before starting the server. `STOCK_RESEARCH_ACCESS_MODE=workspace` may be set explicitly. Either workspace setting activates protection. Missing, conflicting, unreadable or malformed settings deny access. Explicit `local` mode conflicts with workspace settings and is rejected. An installation with no workspace settings retains its personal local workflow.

Profiles must be unique across the workspace registry. The adapter binds private snapshots, notes, SEC receipts and review decisions to the selected profile in the configured storage root. Caller-supplied roots cannot redirect these operations. Optional workspace model paths use `workspaces/<workspace-id SHA-256>/data` and `outputs` under the same root. Protected routes start with company search and the scoped evidence workflow. Personal legacy journals, operator routes and shared personal model files are outside that route.

## Reads and writes

The existing policy governs viewer, editor and owner actions. Viewers can read their workspace research. Editors and owners can append research records and snapshots and update exact-pair review decisions. Notes remain append-only. Protected record paths must match the configured root, selected profile, issuer and ticker. The guards run before filesystem reads, locks and writes, including direct store calls and confirmation of a previously rendered authoring preview.

Membership is read again for every operation. Downgrade or revocation therefore applies to a stale save action and to the next page load. Identity changes clear the app's retained research state. Already delivered content cannot be recalled from a browser. Export through Streamlit's prebuilt download artifacts is held in protected mode pending an authorized delivery endpoint. Source permissions continue to govern data independently of workspace role.

## Verification and remaining gates

Run `make workspace-authorization-check`. It passed 561 cases on November 20, 2026 with the declared Streamlit 1.62.0 runtime. It exercises claims, registry failures, direct snapshot/notes/SEC access, role restrictions, foreign paths, revoked confirmations, changes during queued writes, personal-mode compatibility and the real Workbench and Monitor routes on desktop and phone. Browser identities and membership changes are synthetic and confined to disposable test servers. Production code reads `st.user`; it has no test identity input or client-assigned principal.

The current adapter requires a real identity-provider configuration and deployment review before hosted use. Durable access auditing, session revocation at the identity provider, retention and deletion, authorized export delivery, shared provider-rate controls and operated recovery need verification in the intended environment. The source-rights registry still holds Yahoo commercial use and redistribution. [Pilot audit](PILOT_READINESS_AUDIT.md) · [Private beta architecture](PRIVATE_BETA_ARCHITECTURE.md)
