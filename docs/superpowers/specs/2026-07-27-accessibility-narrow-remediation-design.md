# Accessibility Narrow Remediation Design

## Decision

Implement the five currently reproduced accessibility repairs as one bounded UI
slice:

1. first application-focus skip placement;
2. visible labelled mobile workflow navigation;
3. ticker-specific Discover action names;
4. disclosure-summary focus visibility;
5. field-level authoring error association.

This slice does not claim WCAG conformance and does not replace keyboard,
screen-reader, zoom/reflow, forced-colors, reduced-motion, or independent human
testing.

## Current Evidence

Direct review at desktop and `390x844` reproduced:

- Streamlit sidebar controls precede `Skip to page answer` in focus order;
- the phone workflow has no visible labelled Research Desk -> Discover ->
  Company Workbench -> Monitor navigation;
- Discover exposes repeated `Open review` link names for different companies;
- native `summary` elements have no explicit `:focus-visible` contract;
- `thesis_id is required` appears in a global alert, while the Thesis Id input
  has neither `aria-invalid` nor `aria-describedby`.

These are current defects, not historical or screenshot-only findings.

## Goals

- Make the skip link the first application-owned focus target after unavoidable
  browser/framework chrome.
- Keep a visible, labelled, route-preserving workflow navigation at narrow
  widths.
- Give every Discover action a unique ticker-specific accessible name.
- Make every native disclosure summary visibly focused.
- Bind preview validation errors to the responsible authoring field.
- Preserve the research-only and preview-before-confirm behavior.

## Non-Goals

- No semantic `main` implementation in this slice; it has its own approved
  design.
- No replacement of Streamlit widgets or routing.
- No changes to evidence, readiness, forecasts, ledgers, or generated data.
- No automated claim of screen-reader success or WCAG conformance.

## Architecture

### Focus entry

Render one route-preserving skip link before all application-owned sidebar
widgets. Framework-owned browser or Streamlit chrome may remain before it only
when the app cannot safely control that element. Hidden framework controls must
not remain keyboard-focusable.

The destination remains `#public-page-answer`, `target="_self"`, and
`tabindex="-1"`. Activation must preserve `mode`, `page`, `ticker`, and `open`
query parameters and move focus to the target without rerunning the route.

### Mobile workflow navigation

Add a semantic `nav` labelled `Personal research workflow` containing the four
route links. It is visible at narrow widths and may remain compact at desktop.
The active route uses `aria-current="page"`. Company Workbench preserves the
selected ticker when one exists. Navigation does not expose Operator-only
routes.

### Discover action names

Keep concise visible copy while adding the ticker to both visible and accessible
text:

- `Open AVGO review`
- `Open COHR review`

The destination and readiness ordering do not change.

### Disclosure focus

Add `summary:focus-visible` to the shared focus ring contract. Do not suppress
the browser outline without a visible replacement. The rule applies to
Streamlit expanders and native project disclosures.

### Field-level validation

Map each rejected preview reason to the relevant field contract. After a
validation attempt:

- the field's accessible label identifies the error;
- the field receives `aria-invalid="true"`;
- `aria-describedby` points to one stable field-error element;
- the error element remains inside the locked authoring composer and is also
  announced through the existing alert behavior;
- focus moves to the first invalid field only after a user-triggered validation
  attempt.

The accessibility binding is presentation state only. It cannot change the
draft digest, preview receipt, confirmation state, append engine, or ledger.

Where Streamlit does not expose the required ARIA attributes directly, use the
same bounded, idempotent accessibility bridge specified for the semantic-main
work. The bridge may set accessibility attributes and focus only; it cannot
read or transmit field values or invoke application actions.

## Error Handling

- If no invalid field mapping exists, keep the global alert and do not guess a
  field.
- If the DOM bridge cannot find an exact labelled field, leave the global alert
  visible and record the binding failure in test diagnostics; never bind the
  error to a different field.
- If no ticker exists, do not render a Company Workbench link that implies a
  selected company.
- Navigation must preserve the current route if a query parameter is unknown;
  it must not broaden into Operator mode.

## Testing

Contract tests:

- skip link renders before application-owned sidebar widgets;
- narrow navigation has one labelled `nav`, four unique links, and one
  `aria-current`;
- Discover actions include exact ticker names and unique destinations;
- shared CSS includes `summary:focus-visible`;
- validation error mapping is deterministic and cannot affect preview/confirm.

Browser tests at desktop and `390x844`:

- Tab reaches the skip link before application widgets;
- activating the link preserves the full route and focuses the answer target;
- mobile navigation is visible and labelled;
- ten rendered Discover links have unique accessible names;
- authoring disclosure shows a visible focus ring;
- empty thesis preview produces one field-bound Thesis Id error;
- no horizontal overflow or traceback.

The browser checks are supporting engineering evidence only. Manual assistive
technology tasks remain open.

## Acceptance Criteria

1. All five reproduced defects pass direct browser retest.
2. No research or ledger behavior changes.
3. Public and Personal Research route boundaries remain unchanged.
4. Empty ledgers remain empty.
5. Automated evidence is not described as accessibility conformance.
6. Full release, hygiene, and exact-head CI gates pass.
