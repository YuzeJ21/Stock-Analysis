# Quant Interpretation Eligibility Design

## Status

The user approved approach A on 2026-07-28. The reviewed implementation is at
`195ea18da9d1d6e06c36f8320509ccde46cdaa57`; that anchor implements the shared
overlay without changing calculation or readiness states. It is local
implementation evidence, not a hosted, source-rights, current-market,
nowcast, calibration, or commercial-completion claim. Later revisions require
their own exact-head verification.

## Decision

Add one provider-neutral interpretation-eligibility overlay for valuation,
indicator, and review/risk-metric results. Existing calculations remain
unchanged. The overlay decides only whether an already calculated result may be
described as current context, historical/review-only context, or withheld.

Calculation availability, observation recency, provenance, source rights,
field scope, and commercial eligibility remain independent facts. No one state
may silently promote another.

## Problem

The current modules answer different questions:

- `src/valuation.py` reports whether valuation math was calculated;
- `src/indicators.py` reports whether enough rows existed for indicator math;
- `src/review_metrics.py` reports ready, partial, blocked, or excluded metric
  states; and
- `src/observation_recency.py` independently reports whether saved price
  observations are current, stale, or unavailable.

A calculated or ready result does not prove that its observations are current,
that its sources are traceable, or that the exact fields are permitted for the
intended display. Without a shared overlay, consumers can accidentally turn
calculation readiness into a current-market claim.

## Scope

Create `src/quant_interpretation_eligibility.py` with immutable evidence and
decision contracts plus pure evaluation helpers. Add thin family-specific
adapters for:

1. valuation results;
2. price-derived indicator rows; and
3. review/risk metrics.

The adapters do not recalculate values and do not modify existing result
objects. Dashboard consumers receive the original result and the independent
eligibility decision.

This slice does not add a provider, fetch data, rebuild readiness, change a
forecast, activate a nowcast, expose a probability, approve source rights, or
make a recommendation.

Structured external provenance and exact-source rights proof remain absent for
the current local quant inputs. Consequently, the overlay preserves those
results only as historical/review-only context or withholds them wherever the
required proof is absent; it does not upgrade a local calculation into current
market context or commercial eligibility.

## Approaches Considered

### A. Independent typed overlay — approved

Use one pure evaluator and explicit adapters. This preserves existing module
contracts while giving every consumer the same fail-closed interpretation
rules.

### B. Add eligibility fields to every existing result dataclass — rejected

This would couple calculation code to presentation, provenance, and commercial
policy. It would also require invasive changes across established result
contracts.

### C. Add dashboard-only conditional copy — rejected

UI-only checks would duplicate policy and allow reports, APIs, or future
consumers to disagree with the dashboard.

## Core Contracts

`QuantEvidenceAssessment` contains:

- `family`: `valuation`, `indicator`, or `review_metric`;
- `scope`: ticker and, where applicable, metric or result name;
- `calculation_state`: `available`, `partial`, `unavailable`, or `excluded`;
- `observation_state`: `current`, `stale_review_only`, or `unavailable`;
- `observation_through_date`: the exact accepted date or empty;
- `provenance_state`: `verified`, `unverified`, `missing`, or `invalid`;
- `rights_state`: `permitted`, `unverified`, `restricted`, or
  `not_applicable`;
- `field_scope_state`: `permitted`, `unverified`, `restricted`, or
  `not_applicable`; and
- `evidence_notes`: deterministic explanations from the adapters.

`QuantInterpretationEligibility` contains:

- the same family and scope identity;
- `interpretation_state`: `current_context_eligible`,
  `historical_review_only`, or `withheld`;
- `commercial_eligible`: a separate boolean;
- `reasons`: ordered, deduplicated reason codes;
- `summary`: concise research-only copy; and
- `boundary`: fixed copy stating that eligibility is not a recommendation,
  forecast, probability, or readiness promotion.

No adapter may infer `verified` or `permitted` from a non-empty free-text source
description. Those states require explicit structured evidence supplied by the
caller.

## Decision Rules

Evaluate in this order without overwriting the independent input states:

1. `unavailable` or `excluded` calculation state produces `withheld`.
2. An unavailable, malformed, future, or otherwise rejected observation
   produces `withheld`.
3. Explicitly invalid provenance or restricted rights/field scope produces
   `withheld`.
4. A stale observation with an available or partial calculation produces
   `historical_review_only` when provenance is not invalid and rights/field
   scope are not restricted.
5. A current observation with unverified or missing provenance, rights, or
   field scope produces `historical_review_only`; it cannot be described as
   current-market context.
6. `current_context_eligible` requires an available calculation, a current
   accepted observation, verified provenance, and permitted or genuinely
   not-applicable rights and field scope.
7. `commercial_eligible` is true only when current-context requirements pass
   and every applicable rights and field-scope state is explicitly permitted.

`partial` calculations can never become `current_context_eligible`. They may
remain visible as `historical_review_only` when every other fail-closed
condition permits that limited use.

Reason codes are additive. For example, a stale result with unverified rights
retains both `observation_stale` and `rights_unverified`; the evaluator does not
collapse them into one generic blocker.

## Family Adapters

### Valuation

The adapter consumes the existing valuation status, explicit observation
recency for every market-sensitive input, structured `source_metadata`, and an
explicit source-rights/field-scope review when one exists.

DCF arithmetic may remain calculated and visible under Advanced Evidence while
its interpretation is historical/review-only. A current share price cannot
make stale or unverified fundamentals current. Relative valuation also requires
independent peer comparability and peer-source eligibility; this overlay does
not replace the peer gate.

### Indicators

The adapter consumes the row's exact `date`, calculation sufficiency, and
independent recency/provenance/rights states for the selected ticker and every
benchmark used by the metric.

Relative-strength results require eligible ticker and benchmark observations.
One current leg cannot promote a stale, missing, future, or malformed leg.
Cross-sectional percentile output also remains independent from point-in-time
universe, survivorship, and leakage gates and cannot become a company ranking.

### Review And Risk Metrics

The adapter consumes each metric's existing state and value, exact price or
fundamental observation dates, benchmark dependencies, structured provenance,
and rights/field scope.

`ready` continues to mean mathematical sufficiency only. Historical return,
drawdown, volatility, beta, Sharpe, and Sortino values must be labelled
historical/review-only unless every current-context gate passes. They are not
expected-return estimates or investing instructions.

## UI And Reporting Contract

- Primary research answers show at most one concise eligibility statement.
- Technical states, dates, reason codes, source metadata, and rights details
  stay under Advanced Evidence unless they are required to explain why a
  primary result is withheld.
- Historical/review-only values may be shown with their exact through date and
  limitation; they cannot use `current market`, `current valuation`, `signal`,
  `opportunity`, or equivalent present-tense decision language.
- Withheld results show the principal blocker and preserve the underlying
  calculation for audit only; no zero, placeholder, or fabricated replacement
  is displayed.
- The overlay cannot modify saved readiness, forecasts, scenarios, consensus,
  Revenue, EPS, valuation math, peer comparability, catalysts, outcomes,
  backtesting, or calibration.

## Error Handling

- Missing structured provenance is `missing`, never verified.
- Unknown state tokens are rejected by the constructor or evaluator and do not
  default to eligible.
- A future or malformed observation never becomes current.
- Missing benchmark evidence affects only metrics that require that benchmark.
- An adapter identity mismatch between ticker, metric, result, or recency scope
  raises a deterministic error rather than borrowing another scope.
- Empty inputs return a withheld assessment and never create data.

## Testing

Test-first coverage must include literal boundary fixtures for:

- current, stale, missing, malformed, and future observations;
- verified, unverified, missing, and invalid provenance;
- permitted, unverified, restricted, and not-applicable rights/field scope;
- available, partial, unavailable, and excluded calculations;
- independent ticker and benchmark states;
- valuation, indicator, and review-metric adapter identity mismatches;
- stale calculations preserved as historical/review-only;
- current observations with incomplete provenance remaining
  historical/review-only;
- restricted evidence being withheld;
- no mutation of original valuation, indicator, metric, readiness, or ledger
  objects; and
- no current-market, recommendation, probability, ranking, or transaction
  language from ineligible results.

The expected decisions must be hand-derived literals. Tests may use synthetic
fixtures only and must not write repository data.

## Acceptance Criteria

1. All three quant families use the same pure eligibility evaluator.
2. Existing calculation results and readiness states remain unchanged.
3. Stale calculations are preserved only as historical/review-only context.
4. Missing, malformed, future, invalid, or restricted evidence fails closed.
5. Current-context claims require current observations, verified provenance,
   and explicitly permitted applicable rights/field scope.
6. Benchmark and peer dependencies remain independent.
7. Technical evidence stays under Advanced unless it explains a withheld
   primary result.
8. No nowcast, probability, recommendation, ranking, or transaction behavior
   is activated.
9. Focused, full, render, release, hygiene, and exact-head CI gates pass with
   no generated artifact changes.
