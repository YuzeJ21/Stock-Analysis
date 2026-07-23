# Accessibility Evidence

This document records direct local accessibility evidence for the supported
Personal Research workflow. It is an evidence log, not a WCAG conformance
claim.

## 2026-07-23 partial workflow audit

Scope:

- Local Streamlit dashboard in Personal Research mode.
- Research Desk -> Discover -> Company Workbench -> Monitor.
- Desktop viewport: `1280x720`.
- Phone viewport: `390x844`.
- Browser: local Chromium-based browser.
- Company Workbench review ticker: `AVGO`.
- No readiness rebuild, data refresh, evidence recording, or repository
  screenshot generation was performed.

Directly observed:

- All four routes rendered at desktop and phone widths without document-level
  horizontal overflow.
- The document language was `en`.
- Visible form controls exposed labels or accessible names in the inspected
  DOM.
- No duplicate element IDs were found in the inspected routes.
- A focused Data Health link showed a visible three-pixel teal outline.
- Research-only and no-account-action boundaries remained visible.
- The Monitor `Open Discover` action initially rendered white normal-size text
  on Streamlit red, measured at approximately `3.3:1`.
- The local theme now gives primary link buttons a `#0b3b36` background and
  border with white text. Runtime retest measured the Monitor action at
  `12.4:1`.
- A route-preserving `Skip to page answer` link is now present in the
  accessibility tree on all four Personal Research routes. Direct desktop and
  phone retest verified the correct route, ticker, and open-state parameters
  for the Company Workbench link and a focusable `tabindex="-1"` answer target.
- Primary route sections now follow each route `h1` with `h2` headings.
  Direct desktop and phone DOM retest verified the complete Workbench sequence
  from `What Changed` through `Advanced Evidence`; Monitor retains the nested,
  non-empty `h3` for `Earnings evidence readiness`.
- The semantic correction was retested at `1280x720` and `390x844` with no
  document-level horizontal overflow. New screenshots remain ephemeral under
  `/tmp/stock-research-accessibility-audit-2026-07-23/` and are not repository
  or release artifacts.

Open findings:

- The inspected routes still expose no `main` landmark.
- Current local Streamlit `1.59.2` containers expose layout and key parameters
  but no semantic role or element parameter. A client-side workaround would
  require unsafe JavaScript tied to framework-owned DOM selectors. That
  approach is not accepted as a stable landmark implementation without a
  separately reviewed design and direct runtime evidence.
- The skip link is structurally present and uses the existing visible-on-focus
  CSS contract, but a complete keyboard traversal has not yet directly proved
  first-focus placement, focus transfer, or return-path behavior.
- Framework help controls measured approximately `16x16` CSS pixels and
  dataframe toolbar controls approximately `22x22`. Hidden native radio inputs
  also measured small, but their visible labels are larger and require separate
  hit-target review rather than treating the input box alone as the target.
- The inspected routes exposed no explicit live region. Dynamic update and
  validation announcements still require task-level assistive-technology
  testing.
- Browser automation did not prove the complete keyboard traversal order.
- Direct screen-reader tasks, 200% and 400% zoom, forced-colors behavior,
  reduced-motion environment verification, and error-association tasks remain
  untested.

Classification:

- `partial_local_accessibility_evidence`
- The contrast, route heading hierarchy, and route-preserving skip-link defects
  above are fixed and directly retested within the stated scope.
- Priority 7 remains incomplete. Screenshots, DOM inspection, and one focused
  contrast/semantic retest do not prove keyboard accessibility,
  assisted-technology support, or WCAG conformance.

Next safe local step:

1. Execute `docs/ACCESSIBILITY_TASK_PROTOCOL.md` in a suitable review
   environment and record direct keyboard traversal, focus, disclosure,
   search, navigation, validation, and error-recovery evidence.
2. Complete zoom/reflow, forced-colors, and screen-reader tasks from the same
   protocol.
3. Revisit the `main` landmark only through a stable Streamlit capability or a
   separately reviewed design; do not inject an unverified DOM-mutation patch.

The protocol is not completion evidence and no task result is inferred merely
because the protocol now exists.
