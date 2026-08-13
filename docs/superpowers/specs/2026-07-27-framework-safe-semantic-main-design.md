# Framework-Safe Semantic Main Design

## Decision

Give the Streamlit primary content container exactly one stable semantic
`main` landmark through a bounded, idempotent accessibility bridge.

The bridge modifies accessibility metadata only. It does not wrap or move
research content, inspect field values, change routing, trigger actions, write
state, or alter readiness.

## Problem

The current Streamlit DOM exposes the primary application content through
`[data-testid="stMain"]`, but current browser snapshots do not expose a `main`
landmark. Rendering an isolated `<main>` through Markdown would create a tiny
sibling rather than semantically containing the actual Streamlit page.

Forking Streamlit or replacing the dashboard framework is disproportionate.
Pretending the small skip target is the full main content would be inaccurate.

## Approaches Considered

### 1. Idempotent parent-DOM accessibility bridge — approved

Use a minimal same-origin Streamlit component to locate the existing primary
container and set stable landmark attributes. This preserves the real content
container and can be verified directly.

### 2. Standalone Markdown `<main>` — rejected

Streamlit cannot safely keep a Markdown tag open across later widget renders.
The resulting landmark would not contain the page content.

### 3. Fork or replace Streamlit — rejected

This would create a large maintenance and regression burden for one semantic
contract.

## Landmark Contract

The bridge targets exactly one `[data-testid="stMain"]` in the parent document
and sets:

- `role="main"`;
- `id="research-main"`;
- `aria-label="Stock research workspace"`.

If the native container later becomes an actual `<main>` or already has
`role="main"`, the bridge must reuse it and avoid creating a second landmark.

There must be exactly one visible main landmark after each route render.
Sidebar, Streamlit chrome, dialogs, expanders, and Advanced evidence remain
outside or inside the existing framework structure as Streamlit renders them;
the bridge does not move those nodes.

## Bridge Boundary

Create one focused helper responsible for rendering the component script. The
script:

- runs only on the local app page;
- uses `window.parent.document` and the exact Streamlit main test ID;
- applies attributes idempotently;
- uses a bounded `MutationObserver` to reapply after Streamlit rerenders;
- disconnects or replaces its prior observer before installing another;
- records no telemetry;
- reads no form values, cookies, storage, clipboard, network response, or
  research content;
- performs no network request;
- invokes no button, form, navigation, or Streamlit callback.

The helper is called once per dashboard run after theme initialization and
before page content is rendered.

## Failure Behavior

If the main container is absent or ambiguous:

- do not create a false landmark on another node;
- do not throw a user-visible traceback;
- keep the existing skip-target behavior;
- expose a deterministic bridge status for engineering tests;
- fail the accessibility browser gate until exactly one container is resolved.

The bridge is an accessibility enhancement, never a readiness or research
availability gate.

## Security And Privacy

The bridge contains a fixed local script with no user-provided interpolation.
It transmits nothing and persists nothing. Content Security Policy, sandbox, and
same-origin behavior must be verified against the pinned Streamlit version.

No external script, package, CDN, analytics service, or hosted account is added.

## Testing

Unit/source contract tests:

- fixed target selector and landmark attributes;
- no dynamic user-content interpolation;
- no fetch, XHR, WebSocket, storage, clipboard, or form-value access;
- idempotent observer replacement;
- helper called exactly once.

Direct browser tests across Research Desk, Discover, Company Workbench, Monitor,
Data Health, and Proof History:

- exactly one visible main landmark;
- landmark contains the page-answer target and route-specific H1;
- skip activation focuses content inside the landmark;
- rerender and route navigation retain exactly one landmark;
- desktop and `390x844` behavior match;
- no console error or traceback.

Automated DOM evidence does not establish screen-reader usability or WCAG
conformance. Manual screen-reader landmark navigation remains required.

## Acceptance Criteria

1. Every Personal Research route exposes exactly one main landmark.
2. The landmark is the actual Streamlit primary content container.
3. No page content is moved or duplicated.
4. The bridge is idempotent, local, non-writing, and non-networked.
5. Existing readiness, evidence, authoring, and navigation tests remain green.
6. Full release, hygiene, and exact-head CI gates pass.
