# Accessibility Media Preferences Design

## Status

The user approved the recommended forced-colors and reduced-motion engineering
design on 2026-07-31. This written specification is the review gate before an
implementation plan is created.

## Decision

Extend the existing read-only Research accessibility browser gate so every
current Research route and viewport is exercised under emulated forced-colors
and reduced-motion preferences after its normal initial render. Add shared CSS
fallbacks that preserve visible focus, current-route identification, readable
boundaries, and motion reduction without changing product data or research
behavior.

This is automated engineering evidence only. It does not complete the manual
forced-colors or reduced-motion tasks, prove assistive-technology behavior,
establish WCAG conformance, or replace independent-human review.

## Problem

The current six-route, two-viewport browser matrix directly verifies semantic
landmarks, route transitions, focus entry, navigation, authoring errors,
dynamic states, overflow, and runtime errors. The shared visual contract has no
explicit `forced-colors` or `prefers-reduced-motion` rules, and the browser gate
does not exercise either preference.

Consequently, an ordinary rendering pass can stay green while:

- a focus indicator, current-route marker, or research boundary becomes
  indistinguishable when author colors are replaced by system colors; or
- a newly introduced animation, transition, or smooth-scroll behavior ignores
  a user's reduced-motion preference.

The local Playwright version supports deterministic media emulation. That is
enough to add regression protection, but it is not equivalent to operating a
real platform high-contrast mode or completing a human review task.

## Scope

The slice changes only:

1. shared dashboard CSS for forced colors and reduced motion;
2. pure media-preference observation evaluation in the existing accessibility
   browser-gate module;
3. the existing route-and-viewport browser measurement;
4. focused tests for the new fail-closed contracts; and
5. accessibility evidence, roadmap, continuation, and PR text after direct
   verification.

It adds no route, component, source, dataset, readiness state, research record,
forecast, score, probability, recommendation, writer, report, or generated
artifact.

## Shared CSS Contract

### Forced colors

Under `@media (forced-colors: active)`:

- interactive focus uses a solid system `Highlight` outline with a visible
  offset and no author-color shadow dependency;
- `.research-workflow-link[aria-current="page"]` retains a non-color marker
  using a system-color border or outline in addition to its semantic state;
- `.research-workspace-boundary` and compact status containers retain a system
  `CanvasText` border;
- text remains present for stale, blocked, withheld, usable, and research-only
  states, so no state depends on color alone; and
- the product does not opt broad containers out of forced-color adjustment.

The rule reuses existing elements and semantic labels. It does not introduce
new visual tokens or alter the normal color theme.

### Reduced motion

Under `@media (prefers-reduced-motion: reduce)`:

- animations complete in a near-zero duration and do not repeat;
- transitions complete in a near-zero duration;
- smooth scrolling becomes immediate; and
- content, focus movement, validation, reruns, and route behavior remain
  available.

The rule is scoped to the application surface and its pseudo-elements. It does
not hide loading, stale, error, withheld, or completion text.

## Browser-Gate Architecture

The existing `_measure_route` flow remains the owner of each route and viewport
context. After the normal initial page is stable, it performs two bounded,
sequential checks in that same page:

1. emulate forced colors, observe the rendered contract, and restore ordinary
   media preferences;
2. emulate reduced motion, observe the rendered contract, and restore ordinary
   media preferences.

The gate then continues its existing same-document rerun and away/return route
checks. Reusing the current context avoids multiplying Streamlit startup,
browser contexts, navigation samples, or server processes.

Each media observation is converted into literal values and passed to a pure
evaluator. Browser-side code only reads bounded computed styles, media-query
matches, visibility, and viewport geometry. It does not mutate application
state, click an action, read field values, or write a file.

## Forced-Colors Assertions

For every route at `1280x720` and `390x844`, the gate requires:

- the `forced-colors: active` media query to match;
- the page's current `.research-workflow-link`, when the route has one, to
  retain `aria-current="page"` and a visible system-color border or outline;
- one physical Tab from cleared application focus to focus the sole
  `.public-skip-link`, whose computed outline is non-`none` with positive
  width;
- the visible `.research-workspace-boundary` to retain a nonzero border;
- required state text and the research-only boundary to remain visible;
- no horizontal overflow, rendered traceback, console error, or page error.

Secondary routes without a primary workflow link retain their existing
absence contract. The evaluator must not invent an active link for them.

## Reduced-Motion Assertions

For every route and viewport, the gate requires:

- the `prefers-reduced-motion: reduce` media query to match;
- representative application elements to report no repeating animation and
  near-zero animation and transition duration;
- computed scroll behavior to be non-smooth;
- the route heading, research boundary, and primary next action or state to
  remain visible; and
- no horizontal overflow, rendered traceback, console error, or page error.

The check does not claim that no motion exists anywhere in browser or framework
chrome. It verifies the application-owned surface covered by the shared CSS.

## Fail-Closed Behavior

- If media emulation is unsupported or raises, the affected route result fails
  with the exception type; the gate does not silently skip the mode.
- If a required element has zero or multiple matches, the relevant assertion
  fails instead of choosing an arbitrary element.
- If an expected computed style is missing or unparsable, the assertion fails.
- Ordinary media preferences are restored in a `finally` path before the
  existing rerun and navigation checks continue.
- A media-mode failure cannot change readiness, research data, source rights,
  or any ledger.

## Testing

Test-first coverage must prove:

- literal passing forced-colors observations are accepted;
- each missing media match, focus outline, current-route marker, boundary
  border, visible text, overflow, or runtime-safety requirement fails
  independently;
- literal passing reduced-motion observations are accepted;
- repeating animation, excessive duration, smooth scroll, missing content,
  overflow, or runtime errors fail independently;
- `_measure_route` restores ordinary media preferences after each emulated
  mode, including when observation raises;
- the existing fake browser tests remain fail closed without weakening bridge,
  landmark, navigation, authoring, or state-transition coverage;
- all 12 route-and-viewport results exercise both media contracts; and
- the repository fingerprint remains unchanged by the browser gate.

Direct browser verification remains `make research-accessibility-browser-check`
against the Demo profile. Full dashboard, render, public, pilot, commercial
beta, hygiene, and exact-head CI gates remain required after implementation.

## Evidence Classification

Passing results may be described only as:

- automated forced-colors emulation engineering evidence; and
- automated reduced-motion emulation engineering evidence.

They must not be described as:

- a completed manual forced-colors or reduced-motion task;
- screen-reader or assistive-technology validation;
- independent-human review;
- WCAG conformance;
- hosted-environment validation; or
- market, source-rights, readiness, or investment evidence.

The corresponding manual tasks remain `blocked_environment` until a suitable
review environment and human reviewer complete the task protocol and material
defect retests.

## Acceptance Criteria

1. Shared CSS provides explicit forced-colors and reduced-motion behavior while
   preserving the existing normal theme.
2. Every existing Research route at desktop and phone widths passes both
   emulated media-preference contracts in the existing browser context.
3. Normal landmark, focus, navigation, authoring, state, route-transition,
   overflow, runtime, and repository-write checks remain green.
4. No research data, readiness state, source-rights decision, forecast,
   probability, recommendation, ledger, or generated artifact changes.
5. Documentation records the exact tested commit and retains all manual,
   assistive-technology, independent-human, hosted, and WCAG boundaries.
6. Focused tests, the full repository suite, browser and render checks, release
   gates, hygiene checks, exact staging, draft-PR update, push, and exact-head
   CI all pass.
