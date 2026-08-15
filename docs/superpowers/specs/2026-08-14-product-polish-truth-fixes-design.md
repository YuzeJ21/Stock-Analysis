# Product Polish And Truth Fixes Design

**Status:** Approved direction for bounded local implementation; no push,
deployment, generated-artifact mutation, or product-scope expansion is
authorized.

## Objective

Turn the current live audit into three small repairs in the existing calm
institutional workspace:

1. keep the Research Desk supporting-evidence explanation readable at desktop
   widths;
2. describe saved peer coverage without implying reviewed peer-valuation
   evidence; and
3. prevent missing provider-status evidence from being presented as a
   configured provider.

The existing Streamlit product is the prototype. The work does not introduce a
parallel mock application, new route, new workflow, new data source, or new
visual language.

## Considered Approaches

### A. Targeted root-cause repairs — selected

Keep the existing information architecture and component system. Scope the
layout correction to the Research Desk evidence row, change the Public Home
metric label to the product's established mapped-peer terminology, and make
project status fail closed when saved provider evidence is unavailable.

This is the smallest approach that repairs what users actually see without
changing readiness calculations or widening the product.

### B. Copy-only workaround — rejected

Shorten the Research Desk freshness warning until it happens to fit, and leave
the shared grid unchanged. This would hide the current symptom while another
long translated label could reproduce it.

### C. Broad visual/status refactor — rejected

Redesign all evidence rows and consolidate every status command around a new
state model. This would create unnecessary regression risk across Public,
Personal Research, and Operator modes.

## Design Decisions

### Research Desk supporting evidence

The current three-column row allows the unbounded freshness message in the
middle column to consume the available width and collapse the reason paragraph
to zero pixels. The Research Desk row will use a bounded two-column reading
pattern:

- lane and semantic state on the left;
- freshness message and explanation on the right;
- the explanation starts on its own line; and
- at phone width, the existing single-column stack remains.

The change is scoped to `.research-desk-brief` so other dense evidence tables
retain their established layout. Text remains complete, selectable, and in DOM
order; no truncation, ellipsis, line clamp, nested scrolling, or hidden copy is
allowed. Because the scoped desktop selector is more specific than the generic
phone rule, the `640px` media query must include its own scoped reset to a
single column with normal grid placement.

### Public Home peer metric

The saved `peer_ready` count measures mapped peer price/trend context. It does
not prove an independently reviewed peer relationship or trusted peer-relative
valuation inputs. Public Home will label the metric **Mapped peer trend**.

The count and calculation remain unchanged. Data Health continues to explain
that peer valuation is independently gated and withheld when its direct
evidence is absent.

### Provider-status truth

`outputs/session_source_preflight.json` is optional saved evidence. Its absence
must not imply that FMP is configured.

When the saved operator summary is unavailable or malformed, the FMP stage will
be classified as `source_status_review_required`, with evidence that provider
configuration is not established from saved status and a read-only next action
to run `make provider-setup-checklist`. Project status describes only the saved
session-source evidence; the checklist describes current local key setup. It
will not claim either that a key is configured or that a secret is definitely
absent.

When saved evidence explicitly lists FMP as needing setup, the existing
`awaiting_external_setup` result remains. When saved evidence explicitly shows
that FMP is configured, the existing reviewed one-ticker smoke boundary
remains. Secret values are never printed.

## Error And Boundary Behavior

- Long evidence text wraps normally and cannot collapse the adjacent reason.
- Missing or malformed provider status fails closed to review-required.
- An explicit configured or missing provider state retains its current path.
- No provider probe, network call, refresh, import, apply, materialization, or
  generated-file write is added.
- No peer count, readiness threshold, source-rights state, recommendation, or
  ranking changes.

## Verification

Test-first regressions must prove:

- the Research Desk desktop evidence row reserves usable width for the reason,
  retains full text, and still stacks at phone width;
- Public Home renders `Mapped peer trend` and never renders `Trusted peers`;
- absent or malformed saved source status cannot produce
  `configured_smoke_required` or `FMP_API_KEY appears configured`;
- explicit missing and configured saved states retain their established
  behavior; and
- `make project-status-check` and `make next-stage` no longer contradict each
  other in the current no-provider-evidence state.

After focused GREEN tests, capture matching before/after Research Desk desktop,
Public Home desktop, and Research Desk phone screenshots. Measure the desktop
reason width and row height in the live DOM. Run only the smallest affected
browser routes unless a shared selector or browser-gate contract changes. Ask
for independent review before any local commit beyond the design record.

## Explicit Non-Goals

- no visual redesign or Figma artifact;
- no new dashboard, indicator, recommendation, or analytical function;
- no provider configuration, source activation, refresh, or data mutation;
- no hosted deployment, publishing, PR update, merge, or push; and
- no claim of WCAG, screen-reader, human-keyboard, or production readiness from
  automated evidence alone.
