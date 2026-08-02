# Public Single-Stock Stop Rule First-Viewport Design

## Problem

A fresh Public workflow audit at the current branch head reproduced one narrow
phone-layout regression on the selected NVDA Single-Stock Report. At
`390x844`, the selected answer, `Use now`, `Still withheld`, and the existing
44-pixel `Open Data Health` action remain visible with no horizontal overflow.
The research-only stop rule begins at `y=857.9px`, approximately `13.9px`
below the first viewport.

The selected-ticker markup and reading order are correct. The overflow is
vertical density inside the phone action block: its grid gap is applied between
all three children while the stop-rule `small` element also retains its desktop
top margin. Those two spacing mechanisms accumulate between the explanatory
sentence and stop rule. Data, readiness, routing, quant calculations, and the
desktop layout are not involved.

## Approved Decision

Preserve the current information and fail-closed reading order:

1. Selected ticker
2. Use now
3. Still withheld
4. Open Data Health
5. Next-action explanation
6. Research-only stop rule

Inside the existing `@media (max-width: 640px)` block only:

- reduce `.public-ticker-action` from the desktop `0.55rem` grid gap to a
  compact `0.2rem` phone gap;
- remove the inherited top margin from `.public-ticker-action small`;
- retain the existing summary grid, typography, copy, DOM order, colors,
  borders, and 44-pixel primary-action target;
- leave all desktop rules unchanged.

The expected reduction is approximately 17.9 pixels: two phone grid gaps save
approximately 11.2 pixels relative to the inherited gap, and removing the
stop-rule top margin saves approximately 6.7 pixels. The exact acceptance
criterion is measured browser behavior, not the arithmetic estimate.

### Implementation Evidence Addendum

The first live `390x844` recapture after those two declarations correctly
stopped the implementation because the complete two-line stop rule still ended
at `871.90625px`, leaving `-27.90625px` of bottom clearance. The original
hypothesis explained only the action-block spacing and did not account for the
phone summary retaining the desktop `margin-top: 0.78rem`.

Direct geometry showed 30.703125px between the trust strip and summary. A
second red-green cycle therefore added one selector-local phone override,
`margin-top: -1rem`, to `.public-ticker-summary`. This supersedes the original
two-declaration implementation detail while preserving the approved objective
and every product boundary: the resulting trust-strip-to-summary gap remains
positive at 2.2265625px, the complete stop rule ends at `843.4296875px`, and
desktop is unchanged. No additional layout change was stacked without first
stopping, remeasuring, and protecting the measured cause with a failing test.

## Alternatives Rejected

- **Shorten or merge the explanation and stop-rule copy:** saves height by
  changing the research boundary instead of fixing the duplicated spacing.
- **Move the stop rule ahead of the action or withheld evidence:** weakens the
  established fail-closed reading order.
- **Relax the first-viewport contract:** permits the safety boundary to remain
  below the fold and contradicts the Public UX review protocol.
- **Compress the entire public shell or trust strip:** changes unrelated pages
  and creates unnecessary responsive risk.

## Components

### Public phone CSS

`src/dashboard.py` owns the existing Public shell and selected-ticker styles.
The implementation changes only phone media-query spacing for
`.public-ticker-summary`, `.public-ticker-action`, and its `small` child. No
Python interface, renderer, route, or data contract changes.

### Regression contract

`tests/test_dashboard_helpers.py` adds one focused rendered-CSS contract that
captures the actual style emitted by `render_public_shell_mode_styles()`,
extracts the Public phone media query, and requires all three selector-local
spacing declarations. The test failed before each production correction and
passes only while the phone-scoped rules exist.

The test protects the production break being fixed: removing either compact
phone declaration would restore the accumulated vertical spacing. Browser
measurement remains the authoritative layout proof because a source contract
alone cannot prove viewport position.

### Live browser evidence

The existing Public Single-Stock Report route will be reviewed at `390x844`
and `1280x720`. The phone check will measure the stop-rule bounding box,
primary-action height, selected-answer order, document width, collapsed
Advanced state, and rendered error state. The desktop check protects the
unchanged four-column summary.

Any temporary evidence stays outside the repository. No Figma artifact is
required or created.

## Error And Boundary Handling

- If the stop rule still ends below `844px`, the hypothesis is not confirmed;
  stop and remeasure rather than stacking another spacing change. This branch
  followed that rule: the first recapture failed, a separate measurement found
  the inherited summary margin, and the additional override received its own
  red-green and mutation evidence before the final recapture.
- If the action target becomes shorter than 44 pixels, reject the fix.
- If the DOM order changes, copy disappears, Advanced content opens, a
  traceback appears, or horizontal overflow appears, reject the fix.
- Browser-extension console noise must be distinguished from application
  errors by checking the repository bundle, rendered traceback state, and
  route behavior. It cannot be reported as a clean application result without
  that classification.

## Test And Release Strategy

Use a strict red-green cycle:

1. Add the focused phone-action spacing test.
2. Run it and confirm the expected failure against current CSS.
3. Add the two initially approved phone declarations; if live acceptance still
   fails, stop and add no further change until direct measurement identifies a
   bounded phone-only cause and a new failing contract protects it.
4. Run the focused helper and Public workflow tests.
5. Verify the live `390x844` and `1280x720` route behavior.
6. Run the complete pytest, dashboard, render, accessibility, wording, Public,
   pilot, release, whitespace, diff, protected-artifact, and staged-hygiene
   gates required by the continuation contract.
7. Update `ROADMAP.md`, `docs/DASHBOARD_QA.md`, the continuation contract, and
   draft PR #113 only with direct verified results.
8. Push only `codex/personal-research-mode-mvp` and require successful
   exact-head GitHub Actions before treating the repair as synchronized.

## Generated-Artifact Boundary

- Do not run `make readiness`, broad refreshes, canonical-data writers, report
  generators, sample-report generators, screenshot writers, or timing writers.
- Preserve the existing 18 generated CSV/report/output modifications exactly,
  unstaged and hash-verified.
- Stage only the exact reviewed product, test, specification, plan, roadmap,
  QA, and continuation files needed by this slice.
- Never use `git add -A`.

## Acceptance Criteria

1. At `390x844`, the complete stop rule is inside the first viewport with a
   non-negative bottom clearance.
2. Selected ticker, `Use now`, `Still withheld`, `Open Data Health`, the
   explanation, and the stop rule retain their current DOM and visual order.
3. `Open Data Health` retains a target height of at least 44 pixels.
4. The phone document has no horizontal overflow, traceback, or newly opened
   Advanced content.
5. At `1280x720`, the existing desktop summary layout and content are
   unchanged.
6. No readiness, source, evidence, forecast, probability, valuation,
   catalyst, outcome, backtest, or calibration state changes.
7. Focused and full verification pass with the protected generated artifacts
   unchanged and excluded.
8. PR #113 remains open and draft, and exact-head CI succeeds before the slice
   is considered synchronized.

## Product Boundary

This is a Public workflow usability and safety-visibility correction only. It
does not add investment advice, recommendations, rankings, expected-return
scores, position sizing, transactions, broker integration, order routing,
auto-trading, or post-earnings price prediction. It does not fabricate or
activate research evidence.
