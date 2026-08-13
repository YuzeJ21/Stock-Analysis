# Filed-Q4 Split-Proof Correction Design

## Problem

Explicit filed-Q4 extraction correctly required a primary Q4 table, but it
defaulted missing or malformed split-basis language to `as_reported`. Downstream
comparability treated that invented declaration as verified and could unlock
EPS without primary proof.

## Contract

- Missing or unparsable filed-Q4 split evidence yields
  `primary_split_basis_unverified`, never `as_reported`.
- Both Companyfacts and primary-proof unverified sentinels fail the shared EPS
  comparability predicate.
- Only declared supported basis tokens (`as_reported`, `pre_split`, and dated
  `post_split`/`split_adjusted` forms) pass; arbitrary nonempty text does not.
- Revenue remains independently usable.
- EPS trend, readiness, backtesting, and comparison paths continue to use the
  shared predicate and therefore withhold the unverified filed-Q4 value.
- Explicitly parsed retrospective split proof retains its dated adjusted basis.

## Boundaries

This does not infer an as-reported basis, create primary proof, alter Q4 table
requirements, or change any canonical/readiness artifact.
