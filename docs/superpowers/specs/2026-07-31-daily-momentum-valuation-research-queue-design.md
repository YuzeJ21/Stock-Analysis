# Daily Momentum And Valuation Research Queue Design

**Status:** Approved by the owner on 2026-07-31.

## Objective

Add a read-only `Daily Momentum & Valuation Research Queue` to Personal
Research Mode. The queue identifies companies that merit deeper research
because they simultaneously satisfy a transparent momentum contract, a
point-in-time historical-valuation contract, and minimum value-trap safeguards.

The queue is a research-prioritization surface. It is not a stock-pick list,
recommendation, company score, expected-return model, portfolio instruction, or
transaction system.

## Approved Scope

The first version evaluates only companies whose saved readiness row says
`momentum_ready=true`. It does not expand coverage, refresh data, fetch a
provider, rebuild readiness, or use the legacy Monthly Picks, Momentum Leaders,
Final Watchlist, or portfolio surfaces as an input.

The approved selection policy is a strict intersection:

1. the row is momentum-ready;
2. current price is above the 50-day simple moving average;
3. the 50-day simple moving average is above the 200-day simple moving average;
4. three-month and six-month total returns are positive;
5. benchmark-relative return versus SPY is positive;
6. the point-in-time Historical Valuation Regime is `ready`;
7. its latest multiple is at or below the fortieth percentile of its own
   compatible historical observations;
8. its latest valuation observation is current under the existing 120-day
   policy;
9. free cash flow is positive;
10. revenue growth is non-negative;
11. debt to equity does not exceed the configured quality-value threshold; and
12. every required current-market, provenance, exact-source-rights, and field
    scope gate is eligible.

RSI and volume may be shown as descriptive context later, but they do not
change first-version eligibility. No weighted score or ranking is calculated.

## Product Behavior

Discover places the queue before the general company selector so the first
screen answers which companies are currently eligible for deeper review.

The queue exposes these states:

- `eligible`: every approved condition passes;
- `withheld`: at least one condition is missing, stale, unverified, restricted,
  invalid, or false;
- `baseline_missing`: the current eligibility result is available, but no
  comparable prior queue snapshot was supplied;
- `new_today`: eligible now and not eligible in the supplied prior snapshot;
- `still_qualifies`: eligible in both snapshots;
- `exited_today`: eligible in the prior snapshot and no longer eligible now.

When no prior snapshot exists, Discover shows current eligible companies and
states that daily-entry and exit comparisons are unavailable. It never labels
all current rows `new_today`.

Within every group, rows are ordered alphabetically by ticker. The queue does
not expose a company score, rank, winner, target price, probability, expected
return, buy/sell/hold language, position size, stop, or portfolio action.

Each visible eligible or exited row includes:

- ticker and company name;
- observation-through date;
- concise momentum evidence;
- historical valuation percentile and metric;
- minimum fundamental-safeguard state;
- the deterministic inclusion or exit reason; and
- a ticker-bound `Open Company Workbench` route.

Technical evidence, individual gate states, exact sources, and blocker details
stay under Advanced. An empty eligible set is a valid product state and never
causes a threshold to be relaxed.

## Architecture

### Pure queue contract

Add a focused module, `src/daily_research_queue.py`, with immutable result
objects and pure evaluation functions. The module accepts normalized,
caller-supplied rows or packets and performs no file, environment, network,
Streamlit, clock, or provider access.

The module owns:

- the fixed first-version policy;
- deterministic per-ticker evaluation;
- ordered blocker codes and user-readable explanations;
- current eligible/withheld partitioning;
- optional prior/current comparison; and
- presentation-safe row/card payloads.

Actuals, consensus, Revenue, EPS, valuation, catalysts, outcomes, backtesting,
calibration, indicators, and review metrics retain independent readiness. Queue
eligibility is derived research context and cannot modify any of them.

### Dashboard adapter

Add one read-only dashboard loader that:

1. reads selected-profile readiness, prices, fundamentals, universe metadata,
   the source-rights registry, and historical valuation observations;
2. builds indicator snapshots in memory with the existing indicator engine;
3. builds the existing commercial Historical Valuation Regime packet per
   eligible ticker;
4. evaluates current observation recency and price provenance/rights;
5. passes normalized evidence to the pure queue contract; and
6. catches malformed or unavailable inputs and returns a fail-closed result.

The dashboard adapter does not use `outputs/momentum_leaders.csv`,
`outputs/final_watchlist.csv`, `src/monthly_picks.py`, or any other legacy
ranking output.

### Temporal comparison

The first implementation accepts an optional prior eligibility snapshot through
the pure comparison API, but adds no writer or scheduler. Discover therefore
defaults to `baseline_missing` unless a later approved operating slice supplies
a comparable prior snapshot.

This keeps the first slice read-only and prevents new CSV, JSON, report,
sample-report, screenshot, or timing churn. A future scheduler may persist
ignored local snapshots only through a separately reviewed design.

## Fail-Closed Evidence Rules

The entire current-market queue is withheld when the profile price lane or SPY
benchmark observation is stale or unavailable. Per-ticker eligibility is also
withheld when:

- fewer than 200 usable price observations prevent the approved moving-average
  and six-month tests;
- the ticker observation is stale or unavailable;
- price provenance or exact-source commercial rights are not verified and
  permitted for the required price-history scope;
- a momentum input is non-finite or absent;
- the historical valuation ledger is absent, malformed, insufficient,
  commercially blocked, stale, above the percentile threshold, or definition
  incompatible;
- a required fundamental is absent or non-finite;
- free cash flow is not positive;
- revenue growth is negative;
- debt to equity exceeds the configured threshold; or
- required fundamental provenance/rights are absent or restricted.

Current repository truth is expected to produce an honest withheld or empty
queue because the historical valuation ledger is absent and current local
price evidence lacks approved commercial price rights. Synthetic fixtures may
exercise eligible cases in tests only.

## Error Handling

Malformed or unavailable inputs produce stable blocker codes and a useful empty
state, not a traceback or partial recommendation. One ticker's malformed
evidence cannot suppress other independently evaluable tickers.

The queue never falls back from the selected profile to another profile, never
infers a provider from a filename or value shape, and never treats a saved
artifact's freshness as current-market observation recency.

## Testing

Focused tests cover:

- the exact momentum intersection;
- the fortieth-percentile boundary;
- valuation history, freshness, definition, and commercial-rights failures;
- positive free cash flow, non-negative revenue growth, and debt threshold;
- missing, non-finite, stale, provenance, and rights failures;
- deterministic blocker ordering;
- alphabetical presentation;
- no score, rank, recommendation, probability, expected-return, or transaction
  fields;
- optional prior/current comparison and truthful missing-baseline behavior;
- an empty valuation ledger;
- isolation between ticker failures;
- no file writes by status, evaluation, comparison, or rendering helpers; and
- Discover integration with ticker-bound Company Workbench links and Advanced
  evidence containment.

Release verification includes focused tests, the complete test suite,
dashboard smoke and render smoke, public wording and public checks, commercial
beta and pilot gates, diff/staged hygiene, `git diff --check`, and the direct
Research workflow browser matrix when the local browser environment supports
it.

## Out Of Scope

- rankings, scores, “top stocks,” “best value,” or “buy now” labels;
- direct investment advice or portfolio action;
- legacy Monthly Picks or action-language reactivation;
- provider activation, broad data refresh, readiness rebuild, or source-rights
  approval;
- email, push, or external notifications;
- hosted scheduling or persistence;
- probability, calibration, expected return, target price, or post-earnings
  price prediction;
- automatic thesis, evidence, catalyst, outcome, forecast, readiness, or ledger
  mutation; and
- generated CSV, JSON, report, screenshot, or timing artifacts.

## Acceptance Criteria

1. Discover contains one answer-first, read-only daily queue surface.
2. Eligibility is the exact approved strict intersection with no composite
   score or ranking.
3. Missing, stale, unverified, restricted, or malformed evidence fails closed.
4. Current repository inputs render an honest empty/withheld state without
   fabricating a real candidate.
5. Synthetic eligible fixtures remain test-only.
6. The feature writes no repository or runtime artifact.
7. Existing readiness, evidence, forecast, probability, authoring, and legacy
   contracts remain behaviorally independent.
8. Focused, full, product, browser where available, and hygiene gates pass on
   the exact implementation tree.
