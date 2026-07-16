# Peer Read-Through Map Design

## Goal

Add a read-only evidence map to the existing Single-Stock Report so a reviewer can see which peer relationships are trusted, which are candidate context only, whether a source-backed peer result exists, and whether fiscal timing is explicit enough to support contextual read-through review.

The map does not create peer mappings, change readiness, alter Earnings Nowcast numbers, rank companies, or produce an investment action.

## Product Placement

The map lives inside the existing detailed `Valuation` tab, immediately before peer-relative valuation. It does not add a public route or another command-center page.

The visible order is:

1. relationship layer: trusted or candidate-only;
2. business-overlap evidence;
3. fiscal timing;
4. peer-result evidence;
5. read-through review state;
6. exact missing proof.

Raw source references and evidence rows remain under a collapsed detail drawer.

## Evidence Contract

### Trusted relationship

A relationship is trusted only when it comes from the canonical trusted peer dataset and includes a non-empty source plus an as-of date. Its business-overlap explanation uses only explicit relationship rationale, industry, or peer-group fields.

### Candidate relationship

Rows from the candidate peer layer always remain `candidate_context_only`. Candidate rows can route source review but cannot unlock trusted-peer readiness or contextual read-through.

### Peer result evidence

A peer result is source-backed only when the local earnings row contains at least one explicit actual metric, source provenance, and a reported or last-earnings date. A date-only row is not a result.

### Fiscal timing

Fiscal timing is explicit only when the target and peer fiscal periods are both present. The product displays those periods; it does not infer comparability from calendar dates, sector, or company similarity.

### Read-through state

`reviewable_context` requires all of:

- trusted relationship;
- explicit business-overlap evidence;
- source-backed peer result;
- explicit target and peer fiscal periods.

Every other state fails closed:

- `candidate_context_only`
- `relationship_context_only`
- `awaiting_peer_result`
- `awaiting_fiscal_timing`
- `excluded`

Even `reviewable_context` is directional research context only. It does not change a forecast, DCF, readiness state, score, recommendation, or probability.

## Data Flow

The local market-data provider exposes sanitized trusted and candidate relationship rows in the existing peer summary. The map builder consumes the stock-report payload and returns immutable edge records plus a deterministic identity. No canonical data is written.

## UI States

- Empty trusted and candidate layers: explain that no relationship evidence is loaded.
- Candidate-only: show candidate count and the trusted-promotion boundary.
- Trusted relationship without result: show relationship evidence and withhold read-through.
- Trusted result without fiscal timing: show the result evidence and withhold read-through.
- Reviewable context: show the peer, explicit periods, actual metrics available, and source evidence while preserving the no-forecast-mutation boundary.
- ETF/index/fund: excluded from operating-company peer read-through.

## Verification

- Core tests cover candidate isolation, missing source, date-only earnings, missing timing, reviewable context, deterministic identity, and excluded assets.
- Provider tests prove relationship/result provenance is exposed without promoting candidates.
- Dashboard tests prove public wording and collapsed evidence behavior.
- Full public and pilot gates remain green.
