# Public Mobile Zero-Scroll Stop-Rule Design

## Status

The owner approved Scheme A and the Home phone ordering decision on
2026-08-08 with the exact authorization:

`批准方案 A，并批准 Home 手机端将 stop rule 移到 metrics 前`

This document formalizes that approved direction. Implementation remains
behind the written-spec review gate.

## Objective

At an explicit top-of-page `390x844` viewport, keep the complete research-only
stop rule inside the initial viewport on Public Home and the selected NVDA
Single-Stock Report. Preserve all visible copy, the 44-pixel primary actions,
the established evidence-first reading order, desktop layout, route behavior,
and every data, readiness, source, research, quant, and generated-artifact
boundary.

## Current Evidence

The current branch is synchronized at
`d3b396406844338a768f045f26026214699e2c32`. Its only working changes are the
18 protected generated CSV/report/output paths, which remain excluded from
staging.

A fresh zero-scroll browser audit at `390x844` recorded:

- `window.scrollY=0`, document and body scroll offsets of zero, and
  `stMain.scrollTop=0`;
- `scroll_width=390` on both routes;
- Home DOM order `primary -> metrics -> stop`, with the 44-pixel action ending
  at `799.421875`, metrics ending at `979.640625`, and the stop rule ending at
  `1059.609375`;
- Single-Stock Report trust-strip bottom `523.3125`, summary top `525.53125`,
  action bottom `808.0625`, and stop-rule bottom `886.3125`;
- a positive `2.21875`-pixel trust-strip-to-summary gap, so the existing
  `margin-top: -1rem` cannot safely become more negative;
- no horizontal overflow or traceback, and the Single-Stock primary action
  remains exactly 44 pixels high.

The Single-Stock result is identical on the archived evidence tree
`60492ffa5475fc00cebbc2d4c2dff0c2b140c467` and the audited product tree
`2e58e00bb6ddff6791299a514b562c96ce911196`. No later tracked product change
caused the current failure. The earlier `stop_bottom=843.4296875` evidence did
not record scroll position and cannot prove a top-of-page pass.

## Approved Design

### Home: breakpoint-specific semantic placement from one copy source

Render two breakpoint-specific `.public-home-stop` containers from one shared
copy fragment in `public_home_overview_html()`: a phone instance before
`.public-home-metrics` and a desktop instance after it. CSS must keep exactly
one instance displayed and therefore present in the accessibility tree at each
breakpoint. This makes the phone rendered DOM and visual order:

1. Start explanation and `Start with Stock Selector` action
2. Complete `No data, no conclusion` stop rule
3. Readiness metrics

Do not use CSS `order` or grid placement to create a visual/source-order
mismatch. Preserve the desktop rendered DOM and visual order by hiding the
phone instance in the base rules. Inside the existing `max-width: 640px`
block, hide the desktop instance and display the phone instance. Both
containers must be built from the same local `stop_copy` value so the visible
wording cannot drift between breakpoints.

Use a zero phone grid gap between the primary block and phone stop rule,
compact only the stop-rule padding and line height, and restore a separate top
margin before metrics. This keeps the boundary attached to the action while
retaining comfortable separation before the secondary counts. Desktop keeps
its existing primary/metrics first row and full-width stop row without
explicit visual reordering.

The implementation must not remove a metric, shorten the stop rule, reduce the
primary action below 44 pixels, or change the desktop two-column first row.

### Single-Stock Report: selector-local Scheme A compaction

Keep the complete DOM order:

1. Selected ticker
2. Use now
3. Still withheld
4. `Open Data Health`
5. Next-action explanation
6. Research-only stop rule

Do not move the summary into the trust strip, make the existing negative
margin larger, shorten copy, hide context, or compress the shared Public
shell. Instead, reuse the already-shipped Personal Research phone pattern only
inside the existing Public `.public-ticker-summary` phone rules:

- render the selected-ticker label and ticker value on one baseline-aligned
  flex row;
- reduce the summary grid gap from `0.25rem` to `0.2rem`;
- retain `margin-top: -1rem`, but reduce summary top/bottom padding to
  `0 0 0.25rem`;
- reduce only the phone top margins on answer paragraphs and answer-context
  small text;
- reduce phone line height while preserving the existing `0.86rem` paragraph
  and `0.74rem` small-text font sizes;
- retain the existing zero stop-rule top margin and compact action grid gap;
- retain the 44-pixel filled `Open Data Health` action and every border,
  color, word, route, and state.

The target declarations should save more than the current `42.3125`-pixel
deficit without consuming the positive trust-strip gap. Direct browser
geometry, not the arithmetic estimate or CSS source alone, decides whether the
repair passes.

## Alternatives Considered

### A. Approved: responsive semantic Home placement plus selector-local compaction

This changes only the two defective answer surfaces, preserves content and
desktop behavior, and follows an existing compact summary pattern already used
by Personal Research mode.

### B. Compress the shared Public shell or route navigation

Rejected. It would change unrelated Public routes, create route-to-route shell
inconsistency if scoped only to Single-Stock Report, and solve an answer-surface
problem through global framing.

### C. Use CSS visual ordering on Home or hide/shorten safety content

Rejected. CSS-only reordering would diverge from reading order. Hiding,
truncating, or moving the stop rule ahead of withheld evidence would weaken the
research boundary rather than fix layout density.

## Components And Interfaces

### `src/dashboard.py`

- `public_home_overview_html()` derives two responsive stop containers from
  one local copy fragment.
- `render_public_shell_mode_styles()` adds breakpoint visibility for the two
  Home placements plus phone-only Home/Single-Stock density rules.
- No Python API, route, query parameter, data loader, readiness decision, or
  research renderer changes.

### `tests/test_dashboard_helpers.py`

Add focused contracts that fail against the current source before production
changes:

- Home HTML must contain one shared stop-copy source and two breakpoint
  containers in `primary -> phone stop -> metrics -> desktop stop` order.
- Base Home CSS must hide only the phone instance; phone CSS must hide only the
  desktop instance, attach the visible phone stop rule to the action, and
  separate metrics afterward.
- Phone Single-Stock CSS must keep the existing negative margin unchanged and
  require the approved inline ticker, compact gap/padding, answer margins, and
  line-height rules.
- Existing 44-pixel action, content-order, route, and Public shell contracts
  remain green.

Source contracts protect the intended declarations but do not prove viewport
geometry.

### Browser evidence

Use a fresh local Demo-profile app and inspect both routes at `390x844` and
`1280x720`. Before measuring either phone route, require all of:

- `window.scrollY == 0`;
- `document.documentElement.scrollTop == 0`;
- `document.body.scrollTop == 0`;
- `document.querySelector('[data-testid="stMain"]').scrollTop == 0`.

Then record:

- viewport and document widths;
- action and stop-rule rectangles;
- Home DOM child order and metrics position;
- Single-Stock trust-strip bottom, summary top, complete content order, and
  open Advanced-details count;
- rendered traceback and console/page-error state.

No screenshot artifact is required. If a screenshot is captured for visual
inspection, keep it outside the repository unless separately reviewed.

## Failure Handling

- If either complete stop rule ends below `844px` at zero scroll, stop and
  remeasure. Do not stack another negative margin or remove content.
- If the Single-Stock summary overlaps the trust strip or their gap becomes
  negative, reject the repair.
- If either primary action becomes shorter than 44 pixels, reject the repair.
- If Home visual order differs from DOM order, reject the repair.
- If desktop Home loses its primary/metrics first row or Single-Stock loses its
  four-column summary, reject the repair.
- If copy, routes, selected ticker, readiness state, Advanced state,
  horizontal width, or traceback state changes, reject the repair.
- Browser measurement is unfinished until the app is stable and every scroll
  offset is explicitly recorded. Partial output is not evidence.

## Verification Strategy

1. Add focused failing HTML/CSS contracts.
2. Confirm RED against the current source.
3. Apply only the approved Home markup/CSS and Single-Stock phone CSS.
4. Run the focused helper and Public workflow tests.
5. Run fresh zero-scroll phone and desktop browser measurements.
6. Update `ROADMAP.md`, `docs/DASHBOARD_QA.md`, the continuation contract, and
   the local ten-row Public UX review note only with observed final values.
7. Run the full required release matrix:
   - focused tests;
   - full test suite;
   - `make dashboard-smoke`;
   - `make research-dashboard-render-smoke`;
   - `make commercial-beta-release-check`;
   - `make pilot-readiness-check TOP_N=10`;
   - `make public-check`;
   - `make diff-hygiene-summary`;
   - `git diff --check` and staged whitespace;
   - protected-artifact identity verification;
   - exact staging and `make staged-hygiene-check`.
8. Commit and push only `codex/personal-research-mode-mvp`, keep PR #113 open
   and draft, and require successful exact-head GitHub Actions.

## Acceptance Criteria

1. At explicit zero scroll and `390x844`, Home has exactly one visible stop
   rule with `stop_bottom <= 844`; it appears after the 44-pixel action but
   before metrics in both the rendered accessibility order and visual order.
2. At explicit zero scroll and `390x844`, Single-Stock has
   `stop_bottom <= 844` while the trust-strip-to-summary gap remains
   non-negative.
3. Both phone routes have `scroll_width <= 390`, no traceback, no unexpected
   open Advanced content, and no missing or altered safety copy.
4. At `1280x720`, Home retains the primary/metrics first row plus full-width
   stop row, and Single-Stock retains four summary columns.
5. Both primary actions remain at least 44 pixels high.
6. No data, readiness, source rights, evidence, forecast, probability,
   valuation, catalyst, outcome, backtest, calibration, hosted, or reviewer
   state changes.
7. All focused, full, release, hygiene, protected-artifact, synchronization,
   and exact-head CI gates pass.

## Product Boundary

This is a Public responsive usability and safety-visibility repair only. It
does not add investment advice, recommendations, rankings, expected-return
scores, position sizing, transactions, broker integration, order routing,
auto-trading, stop/profit instructions, or predictive claims. It does not
fabricate or activate research evidence and does not advance Priorities 4-9.
