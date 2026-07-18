# Monitor Answer-First Design

## Purpose

Monitor should answer whether source-backed research work is queued before it
shows technical Earnings Nowcast readiness evidence. The current route renders
the weekly summary, then a five-company readiness card, and only afterward the
actual research-change answer. On both desktop and phone, this pushes the
truthful empty-queue state below the first view. The empty state also uses the
success treatment even though no queued change is a neutral wait condition, not
proof that no real-world event occurred.

This slice changes presentation hierarchy and one navigation affordance only.
It does not change weekly-summary derivation, event identity, queue ordering,
deduplication, wait conditions, cohort membership, readiness calculations, or
evidence status.

## Current Audit Evidence

The default-profile Monitor route was captured on 2026-07-18 at `1280x720`
and `390x844`. Both widths showed the weekly summary before Earnings evidence
readiness, while `Research change monitor` and the empty-queue answer appeared
after the five-company readiness card. No details element was open and neither
viewport overflowed horizontally. Screenshots were saved outside the repository
and remain product-flow evidence only.

## Approaches Considered

1. Keep the current order and add an anchor to the monitor answer. This retains
   the first-view interruption and makes the user navigate around evidence that
   is not required for the primary answer.
2. Build a new combined Monitor summary component. This could create a compact
   answer, but it would duplicate existing weekly and queue semantics and add a
   second aggregation contract.
3. Reorder the existing components and collapse technical readiness evidence.
   This is the selected approach because it reuses proven helpers, changes no
   data flow, and follows the answer-first pattern already verified on Research
   Desk, Discover, and Company Workbench.

## Product Contract

The Monitor route will render in this order:

1. Personal Research workspace header with freshness, research-only boundary,
   and the existing change-review or wait instruction.
2. Existing weekly research summary cards.
3. `Research change monitor` and the existing deduplicated queue frame or the
   truthful empty-queue answer.
4. When the queue is empty, one `Open Discover` action. A non-empty queue keeps
   the review rows as the next task and does not add a competing action.
5. One collapsed `Advanced: five-company Earnings Nowcast readiness` drawer
   containing the existing readiness heading, cards, full cohort rows, and
   blocker caption.
6. The existing collapsed Advanced Evidence note and separate research-change
   evidence drawer.

The empty-queue note uses the neutral treatment. It continues to say that the
state is not a stock ranking and that the researcher may use Discover or wait
for a comparable source-backed change.

## Architecture And Data Flow

`src/dashboard.py` remains the composition owner. `render_research_monitor()`
will compute `research_monitor_frame(...)` before loading and rendering the
Nowcast cohort. It will render the monitor answer immediately after the weekly
summary, add the existing Discover route only in the empty branch, then place
the unchanged readiness cards and dataframe inside the existing five-company
Advanced drawer.

No helper signature, query parameter, loader, dataframe column, queue rule, or
readiness payload changes. Actuals, consensus, Revenue, EPS, valuation,
catalysts, outcomes, backtesting, and calibration remain independent.

## Failure And Boundary Behavior

- An empty queue means no saved comparable source-backed change is queued. It
  never proves that nothing changed in the real world.
- A non-empty queue remains deduplicated and unranked, with evidence status,
  effective date, review state, next research task, and wait condition intact.
- Missing consensus, Q4, split-basis, backtest, and calibration evidence remain
  separately visible under Advanced and cannot unlock a forecast.
- Candidate context cannot alter a deterministic scenario or become trusted
  evidence.
- Synthetic fixtures remain test-only.
- The route writes no source data and creates no generated report artifact.

## Accessibility And Responsive Behavior

The primary answer must appear before the technical readiness drawer in DOM and
visual order. The empty state must not rely on a success color to communicate
meaning. `Open Discover` uses the existing primary link-button pattern; its
nested Markdown text must preserve the button's white foreground instead of
inheriting the page's muted paragraph color. It must remain usable at desktop
and phone widths. At `1280x720` and `390x844`, Advanced stays closed by default
and the document width must match the viewport without horizontal scrolling.

## Documentation And Verification

`ROADMAP.md` will mark all four Personal Research routes answer-first and move
the next executable work to the permitted prospective consensus source path.
`docs/PERSONAL_RESEARCH_MODE.md` and `docs/DASHBOARD_QA.md` will record the new
order and live evidence.

Tests will protect source order, the empty-state Discover action, the neutral
treatment, unchanged Nowcast evidence inside Advanced, and answer-based browser
performance markers. Verification includes focused and full pytest, dashboard
and research render smoke, the 48-sample commercial performance gate, public
wording and public share gates, pilot readiness, diff and staged hygiene,
whitespace checks, and fresh desktop/phone browser review. Screenshots, timing
JSON, CSV, JSON, report, and sample-report churn remain excluded.
