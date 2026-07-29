# Semantic Main Transport Migration Design

## Status

The user approved approach A on 2026-07-28. This written specification is the
review gate before an implementation plan is created.

## Decision

Keep the approved fixed semantic-main bridge and replace only its deprecated
Streamlit transport:

```python
st.html(SEMANTIC_MAIN_BRIDGE_HTML, unsafe_allow_javascript=True)
```

Raise the supported Streamlit range to `streamlit>=1.52,<2`. Streamlit 1.52.0
is the first release with the `unsafe_allow_javascript` parameter required by
this design. The upper bound prevents an unverified major-version migration
from silently changing the bridge contract.

## Problem

The existing bridge uses `st.components.v1.html`. Current Streamlit emits a
deprecation warning and directs callers toward an iframe API. Replacing the
bridge with an iframe would break its defining contract: the bridge must modify
the same document that contains the actual Streamlit main content, skip target,
route state, and rerun lifecycle.

Direct local evidence on Streamlit 1.59.2 showed that `st.html` is not iframed,
executes the fixed bridge when JavaScript is explicitly enabled, and preserves
one exact main landmark containing the answer target.

## Scope

- Change only the bridge renderer and supported Streamlit dependency range.
- Preserve the exact bridge script, target selector, ownership rules,
  MutationObserver lifecycle, failure statuses, and dashboard call location.
- Update AppTest and browser-gate inspection so they no longer depend on an
  iframe `srcdoc`.
- Add a compatibility failure with a clear message if the runtime does not
  provide the required `st.html` JavaScript contract.

This slice does not redesign navigation, content structure, accessibility
copy, research data, or Streamlit itself.

## Approaches Considered

### A. Same-document `st.html` transport with an explicit version range — approved

This removes the deprecated component while preserving same-document landmark
ownership and creates a testable dependency boundary.

### B. Prefer `st.html` and fall back to `st.components.v1.html` — rejected

The fallback would retain the removal risk, keep two runtime paths, and allow
an old environment to pass while still emitting the warning.

### C. Replace the bridge with `st.iframe` — rejected

An iframe has a separate document and cannot make the parent Streamlit content
the single owned main landmark.

### D. Pin an older Streamlit release and keep the deprecated component — rejected

This would defer rather than resolve the removal and maintenance risk.

## Renderer Contract

`render_semantic_main_bridge` accepts a renderer dependency for focused tests
and defaults to `streamlit.html`. It passes:

- the exact immutable `SEMANTIC_MAIN_BRIDGE_HTML` constant;
- `unsafe_allow_javascript=True`; and
- no user content, research content, URL, external script, height, scrolling,
  or iframe arguments.

The fixed script continues to:

- target exactly one parent-document `[data-testid="stMain"]`;
- set `role="main"`, `id="research-main"`, and
  `aria-label="Stock research workspace"`;
- remove only bridge-owned attributes when the target becomes missing or
  ambiguous;
- replace its prior observer before installing the next observer;
- recover after same-document reruns and route transitions; and
- perform no network, storage, clipboard, form-value, navigation, or research
  operation.

## Compatibility Contract

Both `requirements.txt` and `pyproject.toml` declare
`streamlit>=1.52,<2`. Hosted-readiness fixtures and packaging tests use the
same literal range.

The application does not dynamically fall back to a deprecated transport. A
runtime without a callable `st.html` interface supporting
`unsafe_allow_javascript` fails closed with a concise engineering error during
startup or the bridge call. It must not silently render an iframe or omit the
landmark while claiming the accessibility gate passed.

## Layout Contract

The script-only `st.html` element must create no visible content, blank vertical
gap, horizontal overflow, or focusable control. The existing skip link remains
the first product-owned focus target and its destination stays inside the
unique main landmark.

## Testing

Test-first coverage must prove:

- the renderer receives the fixed constant and
  `unsafe_allow_javascript=True`;
- no deprecated component, iframe, dynamic string, or untrusted input is used;
- unsupported renderer signatures fail closed;
- requirements, packaging, and hosted-readiness contracts agree on
  `streamlit>=1.52,<2`;
- all existing bridge ownership, ambiguity, observer, and cleanup unit tests
  remain green;
- AppTest can inspect the rendered `st.html` element without an iframe;
- direct desktop and `390x844` browser runs expose exactly one main landmark,
  one contained answer target, one route H1, and bridge status `applied`;
- skip activation, exact query retention, same-document rerun recovery, route
  away-and-back transitions, and mutation recovery still pass;
- the browser console contains no deprecation warning, error, or page error;
  and
- there is no visible bridge box, layout gap, or horizontal overflow.

Direct browser evidence remains engineering evidence only. It does not prove
screen-reader usability, WCAG conformance, hosted compatibility, or future
Streamlit-major compatibility.

## Acceptance Criteria

1. No product path calls `st.components.v1.html`.
2. The supported dependency range is exactly `streamlit>=1.52,<2` everywhere.
3. The bridge remains fixed, local, same-document, idempotent, non-networked,
   and non-writing.
4. Every tested Research route retains exactly one actual main landmark
   containing its answer.
5. Skip-link, routing, query, rerun, mutation, layout, and error contracts pass
   at desktop and phone widths.
6. No generated data, screenshot, report, JSON, or timing artifact is created
   or staged.
7. Focused, full, render, release, hygiene, and exact-head CI gates pass.
