# Quarterly Cash-Generation Adapter Acceptance Design

## Decision

Add a pure, read-only acceptance harness for one company's in-memory quarterly cash-generation observations. The harness evaluates whether a proposed adapter batch is safe to review; it does not fetch data, read an input file, write an output file, change source rights, activate production output, or promote any readiness state.

The existing `QuarterlyBusinessObservation` and `derive_quarterly_business_metrics` contracts remain authoritative for observation validity, explicit filed-Q4 evidence, cutoff handling, revision resolution, component compatibility, formulas, and source lineage.

## Why This Is The Next Local Step

The calculation contract is implemented, but production correctly supplies no supplemental observations because no reviewed adapter exists. The next locally executable gap is the boundary between an adapter candidate and the existing domain contract: one deterministic decision must explain whether a single-company batch has approved rights, supported fields, coherent identity, complete compatible components, and reviewable derived output.

This increases adapter readiness without pretending that a real source payload, entitlement, or reviewer decision exists. The current checked-in SEC Companyfacts rights record does not list operating income, cash from operations, or capital expenditures, so it must remain blocked for this purpose until the registry is explicitly reviewed and changed through a separate rights decision.

## Alternatives Considered

### 1. Dedicated pure acceptance module — selected

Create a small module that composes the source-rights registry and the existing cash-generation derivation. It returns one immutable result with stable blockers and an `accepted_for_review` state. This keeps source onboarding separate from formulas and makes the boundary directly testable without persistence.

### 2. Add acceptance logic to `quarterly_cash_generation.py` — rejected

This would mix adapter governance with metric validation and derivation. The current domain module has one clear purpose and should remain independent of commercial-source policy.

### 3. Add a CSV validator or Make command — rejected

A file-facing validator would introduce a premature input/output contract, invite generated churn, and imply an onboarding path before a reviewed source exists. This slice deliberately accepts only already-constructed in-memory observations.

## Public Interface

Create `src/quarterly_cash_generation_adapter.py` with:

- `QuarterlyAdapterAcceptance`, an immutable result containing ticker, source ID, status, blockers, accepted observation count, reviewed metric names, derived point count, explicit-Q4 periods, rights status, `production_activation=False`, and `readiness_promotions=()`;
- `assess_quarterly_cash_generation_adapter(...)`, a pure function accepting one ticker, one source ID, an iterable of `QuarterlyBusinessObservation`, compatible Revenue actuals, an explicit source-rights registry, and an optional cutoff.

The only success state is `accepted_for_review`. It means the in-memory candidate passed the local acceptance contract; it does not mean reviewed, production-ready, commercially activated, or source-backed in the repository.

## Acceptance Rules

The candidate is `accepted_for_review` only when all of these are true:

1. The requested ticker and source ID are non-empty.
2. At least one observation exists.
3. Every observation belongs to exactly the requested ticker and source ID.
4. The source exists in the supplied registry and commercial use is explicitly approved.
5. The rights record explicitly supports `operating_income`, `cash_from_operations`, and `capital_expenditures`.
6. The existing observation constructor has already enforced finite values, timestamps, fiscal-period syntax, and explicit filed-Q4 state.
7. The existing derivation reports no post-cutoff, ambiguous-revision, missing-compatibility, or component-definition blocker.
8. At least one fiscal period produces operating margin, free cash flow, and FCF margin from compatible explicit components and Revenue.

Any failed rule returns `blocked` with deterministic blockers. The function reports all safely knowable blockers in one call so operators do not need trial-and-error retries.

## Source-Rights Boundary

The harness receives an explicit immutable registry; it does not mutate or silently extend `config/source_rights.yml`. Unknown sources, unverified commercial rights, and approved sources whose `supported_fields` omit any required component all fail closed.

Tests may construct an in-memory synthetic rights record that explicitly supports the three metrics. That registry is test-only and does not change the checked-in rights decision. The checked-in SEC record remains blocked for these fields unless a separate reviewed rights change is made.

## Q4, Cutoff, Revision, And Compatibility Behavior

- Q4 rows can reach the harness only with `q4_evidence_state=explicit_filed_quarter`; annual-minus-nine-month derivation remains forbidden.
- A publication time after the requested cutoff blocks acceptance and produces no accepted-for-review result.
- Exact duplicates may collapse through the existing derivation; one explicit revision leaf may supersede an older reference; conflicting unresolved leaves block acceptance.
- Currency, unit scale, accounting basis, duration basis, fiscal period, and period end must remain compatible under the existing derivation rules.
- Capital expenditures preserve the reported sign. Free cash flow remains cash from operations plus reported capital expenditures.

## No-Activation And No-Persistence Boundary

The result always sets `production_activation=False` and `readiness_promotions=()`. Acceptance cannot change Revenue, EPS, operating-margin, free-cash-flow, FCF-margin, consensus, valuation, catalyst, outcome, peer, backtest, or calibration readiness.

The module adds no CLI, Make target, loader, writer, template, data directory, CSV, JSON, report, sample report, screenshot, timing output, or canonical row. It performs no network request and reads no credentials.

## Tests

Use synthetic in-memory dataclasses only. Cover:

- one complete compatible one-company batch accepted for review;
- empty input;
- mixed tickers;
- source-ID mismatch;
- unknown source;
- unverified commercial rights;
- approved rights missing one or more required fields;
- explicit Q4 acceptance and constructor-level rejection without filed-quarter evidence;
- post-cutoff observations;
- explicit revision success and ambiguous revision failure;
- incompatible currency, scale, accounting basis, duration basis, or period end;
- missing Revenue and missing component behavior;
- immutable `production_activation=False` and empty readiness promotions;
- no persistence, network, CLI, Make, or generated-artifact surface.

After implementation, run focused tests, the full suite, dashboard smoke, all four Research route render checks, public wording, public check, commercial-beta checks, pilot readiness, diff hygiene, whitespace checks, and staged hygiene. Stage exact code, documentation, and test paths only.

## Documentation And PR Update

Update methodology, provenance, Personal Research guidance, ROADMAP, and the persistent continuation prompt to distinguish:

- `accepted_for_review`: local contract acceptance only;
- `external_source_and_review_required`: real adapter payload and reviewer evidence still absent;
- production activation: still false;
- market maturity: improved adapter governance, not real-company coverage or validation.

Update draft PR #113 with the implementation, test evidence, no-file boundary, current source-rights blocker, and exact external resume condition. Keep the PR draft and do not merge or deploy.

## Completion Boundary

This slice is complete when the pure acceptance result, deterministic blocker coverage, documentation, and regression gates pass with a clean pushed branch and zero generated artifacts.

It does not complete the external adapter gate. Real-company cash-generation output remains withheld until a permitted source supplies a reviewed one-company payload and the applicable rights record explicitly supports the required fields.
