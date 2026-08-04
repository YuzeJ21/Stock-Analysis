# Evidence Monitor Brief Design

## Status

The layout direction was approved on 2026-08-04. This written specification is
the review gate before an implementation plan is created.

## Decision

Recompose the top of Personal Research Mode's Monitor page into one compact,
read-only **Evidence Monitor Brief**. The brief will render existing saved
research contracts in a denser four-question layout and will remove repetitive
primary-page rows when no process transition is due.

This is a presentation and view-composition change. It is not a second event
model, research-priority algorithm, catalyst model, readiness calculation, or
source of truth.

The selected direction borrows the reference dashboard's panel-based
scanability, not its market-regime composites, confidence percentages,
investment-expression language, risk budgets, or terminal-density styling.
The reference screenshot is visual inspiration only and is not product, data,
source, calibration, accessibility, or market-validation evidence.

## Product Purpose

Monitor should let a researcher answer four questions without scanning a table
of identical `Monitor` rows:

1. What traceable research evidence changed?
2. What saved research-process follow-up needs review?
3. What saved process context is scheduled?
4. Is the saved evidence and market-observation context current enough to
   interpret?

The page remains a research-process monitor, not an alert feed, market regime
model, company ranking, or portfolio action surface.

## Current Evidence And Constraint

The current route already has the required semantics:

- `WeeklyResearchSummary` provides a fixed seven-day, deduplicated, traceable
  cohort summary;
- `ResearchDisciplineRow` provides the existing deterministic `Needs review`,
  `Scheduled`, `Monitor`, and `Unavailable` process states in saved cohort
  order;
- the existing research-change queue provides unresolved comparable
  before-and-after evidence changes;
- `ProfileContext` provides saved-readiness freshness and source dates; and
- `ObservationRecencySet` provides an independent current, stale, or
  unavailable market-observation interpretation.

The implementation must reuse those immutable results. It must not reload the
same journals, outcomes, or catalysts through a second path, parse meaning out
of rendered prose, or derive another precedence rule in Streamlit.

This specification supersedes only the Monitor presentation order defined by
the earlier answer-first and workflow-maturity designs. Their evidence,
ordering, fail-closed, no-ranking, and Advanced-detail contracts remain in
force.

## Approaches Considered

### A. Recompose existing contracts into one brief — selected

Replace the separate weekly-summary card group and three discipline-summary
cards with one four-card view. Filter the primary discipline table to saved
rows whose state is not `Monitor`, preserve original cohort order, and keep the
complete table and identities under Advanced.

This removes duplication while preserving one derivation path and one source
of truth.

### B. Add a new dashboard above the existing sections — rejected

Adding four new panels while retaining the current weekly and discipline cards
would increase vertical length and repeat the same facts. It would make the
page look denser without making it easier to understand.

### C. Build a macro-regime or CIO decision terminal — rejected

Liquidity composites, cross-asset confirmation, regime confidence, portfolio
expression, risk budgets, and trade triggers require different data rights,
methodology, calibration, accessibility, and product approvals. They also
conflict with the current research-only boundary.

## Primary Monitor Layout

The Monitor route will render in this order:

1. Existing Personal Research workspace header, research-only boundary, saved
   readiness, and observation-recency interpretation.
2. `Evidence Monitor Brief` as a responsive four-card grid.
3. A compact process-attention section containing only `Needs review`,
   `Scheduled`, and `Unavailable` rows, in saved focused-cohort order.
4. The existing `Research change monitor` with its unresolved rows or truthful
   neutral empty state.
5. `Advanced: Research Discipline evidence`, containing the complete stable-
   order discipline table and existing identities.
6. Existing collapsed five-company Earnings Nowcast readiness and other
   Advanced evidence.

The literal `WEEKLY RESEARCH SUMMARY` first-useful marker remains inside the
brief so existing performance and release evidence can be migrated explicitly
rather than silently discarded.

## Four-Question Brief Contract

### 1. Weekly research summary

This card renders the existing `WeeklyResearchSummary` status, traceable item
count, fixed seven-day window, and cohort size.

- Only an existing `new_evidence` item or a source-backed queue event may be
  described as source-backed evidence change.
- Reviewer-authored invalidation or review-date items remain traceable process
  context and must not be relabelled as externally verified evidence.
- An empty summary says that no traceable saved cohort item requires review in
  the saved window. It does not claim that no real-world event occurred.

### 2. Research follow-up

This card reports existing `Needs review` and `Unavailable` rows as separate
counts; unavailable evidence must not be relabelled as a review finding. It may
show the first reason in saved cohort order as a compact example, but it must
not sort by perceived severity, market movement, valuation, expected return,
or attractiveness.

Conflict, overdue-review, invalidation-follow-up, outcome-rights blocker, and
source-change precedence remain exactly as already derived by the Research
Decision Lab contract.

### 3. Scheduled context

This card counts existing rows whose attention label is `Scheduled` and may
show the first exact saved date in cohort order.

It is scheduled research-process context, not urgency or a prediction. The
first slice does not claim to be a comprehensive catalyst watch: a ticker with
a higher-precedence review state can also have a saved catalyst that is not
represented by its single attention row. Full per-company catalyst evidence
remains in Company Workbench.

Candidate-only context cannot be called verified, trusted, or source-backed and
cannot change a forecast, conclusion, readiness state, or deterministic
scenario.

### 4. Evidence freshness

This card composes two existing independent interpretations:

- saved-readiness freshness from `ProfileContext`; and
- profile market-observation recency from
  `ObservationRecencySet.profile_price_lane`.

It does not calculate a second freshness policy or merge the two states. A
date-current saved artifact does not make a market observation current, and a
current market observation does not promote readiness or source rights.
Exact source dates and machine-oriented diagnostics remain under Advanced.

## Primary Rows And Empty States

The primary process-attention table excludes only rows whose exact attention
state is `monitor`. This is filtering, not ranking. Remaining rows preserve
their original `cohort_order`.

- `Unavailable` rows stay visible.
- If all valid rows are `Monitor`, the page displays one neutral summary such
  as `25 companies remain in saved monitoring state; no saved process
  transition is currently due.`
- That empty state does not claim no market event, risk, catalyst, or external
  research need exists.
- The complete discipline table, including every `Monitor` row, remains under
  Advanced for auditability.
- One ticker's invalid evidence cannot change another ticker's valid state or
  order. A malformed shared ledger may make only that shared evidence dimension
  unavailable for its applicable cohort, without erasing valid independent
  dimensions or changing cohort order.

## Architecture And Data Flow

`src/dashboard.py` remains the route composition owner. The existing one-pass
load of journal, outcome, catalyst, cohort, weekly, change-queue, profile, and
observation-recency evidence remains unchanged.

A pure presentation composer adjacent to the current research-workspace
helpers will accept the already-built objects and return:

- four display-card contracts;
- the non-`Monitor` primary rows in unchanged cohort order; and
- the count of rows collapsed into the neutral monitoring summary.

The composer performs no file, environment, network, provider, cache, refresh,
snapshot, export, or persistence operation. It does not create a new event ID,
research state, priority, readiness state, forecast, or evidence record.

The dashboard renders the returned contracts with the existing semantic card
and table patterns. Python remains authoritative; HTML is presentation only.
There is no automatic or manual download action in this slice.

## No-Write And Artifact Boundary

Ordinary Monitor navigation and rerendering must not call or transitively call:

- readiness materialization or rebuild paths;
- source refresh, collection, import, validate/apply, or provider paths;
- ledger append or authoring-confirmation paths;
- snapshot, report, sample-report, screenshot, or timing writers;
- dataframe CSV/JSON/Excel writers; or
- HTML/PDF export or download preparation.

The feature intentionally persists no application-owned CSV, JSON, Excel,
HTML, report, sample-report, screenshot, timing, readiness, canonical-data,
journal, catalyst, outcome, or proof artifact in the repository or elsewhere
on the user's computer. Existing saved inputs are read-only.
Any future explicit export remains a separate approved action and must not be
required for ordinary app use.

## Research And Methodology Boundaries

The brief must never contain or imply:

- company rank, attractiveness, expected return, recommendation, or buy/sell
  instruction;
- allocation, position size, entry/exit level, stop-loss, take-profit, trade
  trigger, broker action, or auto-trading;
- market-regime, liquidity, cross-asset, or risk-appetite composite without a
  separately approved source and methodology contract;
- numerical confidence, Beat/Miss probability, or calibrated likelihood;
- fabricated events, catalysts, peers, data, timestamps, reviewers, rights,
  summaries, or conclusions; or
- promotion of synthetic fixtures, candidate context, screenshots, or empty
  ledgers into trusted evidence.

Actuals, consensus, Revenue, EPS, valuation, catalysts, outcomes, backtesting,
calibration, readiness, and observation recency remain independent. Explicit
Q4 and EPS split-basis boundaries remain unchanged.

## Responsive And Accessibility Contract

- At desktop width, the four cards form a compact two-by-two grid without
  truncating the primary answer.
- At `390x844`, the cards reflow to one column with no horizontal overflow.
- Each card has a visible text heading and state label; state is never
  communicated by red/green color alone.
- Text remains readable without terminal-style microcopy, unexplained
  abbreviations, or hover-only definitions.
- Existing semantic main, skip-link, focus, forced-colors, reduced-motion, and
  route-navigation behavior remains intact.
- Technical identities, source references, raw timestamps, and machine states
  remain under Advanced unless needed to explain the primary research answer.

This automated contract does not establish human keyboard, zoom, screen-
reader, WCAG, hosted, or independent-user evidence.

## Explicit First-Slice Exclusions

- No `7D / 30D / 90D` selector. The existing seven-day weekly derivation stays
  fixed; changing the window is a separate semantic and test contract.
- No comprehensive multi-company catalyst timeline.
- No macro, liquidity, rates, cross-asset, news, or market-regime panels.
- No charting package, new route, navigation taxonomy, provider, ledger,
  database, hosted service, or Figma dependency.
- No change to Research Desk, Discover, or Company Workbench.
- No roadmap-priority completion claim and no change to any external unblock
  condition.

## Test-First Verification Contract

Focused tests must prove:

1. the four cards are composed only from the supplied immutable inputs;
2. empty weekly, discipline, queue, and recency inputs produce truthful neutral
   or unavailable states without invented content;
3. source-backed changes remain distinct from reviewer-authored context;
4. `Monitor` rows alone are removed from the primary table while complete rows
   remain available under Advanced;
5. `Needs review`, `Scheduled`, and `Unavailable` rows preserve exact cohort
   order;
6. candidate catalyst context is never labelled verified or trusted;
7. saved readiness and market-observation recency stay independent;
8. forbidden probability, scoring, ranking, recommendation, portfolio, and
   transaction language is absent;
9. ordinary Monitor rendering cannot reach writer, refresh, exporter,
   provider, or authoring-confirmation paths; and
10. protected `data/`, `outputs/`, report, screenshot, timing, and manual-review
    artifacts remain byte-for-byte unchanged.

Route and browser evidence must prove:

- workspace header -> `Evidence Monitor Brief` -> filtered process attention
  -> `Research change monitor` -> Advanced evidence order;
- the preserved `WEEKLY RESEARCH SUMMARY` first-useful marker;
- desktop two-by-two and phone one-column layout;
- visible non-color state labels, no horizontal overflow, no traceback, and
  unchanged route/focus behavior; and
- the full Research Desk -> Discover -> Company Workbench -> Monitor workflow
  remains intact.

After focused tests, the implementation plan must retain the current full
pytest, dashboard smoke, research-render, accessibility-browser, performance,
public-wording, public-share, commercial-beta, pilot-readiness, diff-hygiene,
staged-hygiene, whitespace, protected-artifact, push, draft-PR, and exact-head
CI gates applicable to a Monitor UI change.

## Acceptance Criteria

1. The first Monitor view answers the four approved research questions without
   introducing another semantic source of truth.
2. Separate weekly and discipline summary-card groups are replaced, not
   duplicated.
3. Non-actionable `Monitor` rows no longer dominate the primary page; complete
   stable-order evidence remains under Advanced.
4. No source, readiness, observation, attention, catalyst, outcome, forecast,
   probability, or conclusion semantics change.
5. Empty, stale, malformed, candidate-only, and unavailable inputs remain
   explicit and fail closed.
6. Ordinary route use is in-memory and creates no generated artifact or saved
   output.
7. Research-only, accessibility, responsive, and Advanced-evidence boundaries
   pass direct current-head verification.
8. The change does not claim source coverage, current-market validity,
   predictive accuracy, accessibility conformance, hosted operation,
   independent adoption, commercial demand, or product-market fit.

## Roadmap Placement

This is a bounded local usability and synthesis refinement inside the existing
Commercial Research Beta foundation. It does not replace or complete the
external point-in-time universe, consensus/peer, hosted-control,
accessibility-human-review, independent-session, or calibration priorities.

After implementation passes direct evidence, `ROADMAP.md`, Personal Research
documentation, Dashboard QA, release contracts, and draft PR #113 should record
the exact verified presentation change. Until then, this document records an
approved design only.
