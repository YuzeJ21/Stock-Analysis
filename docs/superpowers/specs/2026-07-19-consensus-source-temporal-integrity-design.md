# Consensus Source Temporal Integrity Design

## Purpose

The upstream consensus source-row validator now derives source rights correctly, but its technical contract still has three fail-open time behaviors: it accepts a snapshot recorded after its retrieval timestamp, has no explicit review cutoff, and treats every unrecognized or missing `history_scope` as current-only candidate context.

Add a deterministic temporal review boundary before a supplied row can become candidate context or historical-reviewable evidence. Keep time validity independent from exact-source rights and Revenue/EPS field scope.

This slice validates supplied in-memory rows only. It does not call a provider, collect or append evidence, modify a ledger, rebuild readiness, or write generated artifacts.

## Approaches Considered

### Selected: mandatory cutoff, explicit scope, and ordered timestamps

Require a keyword-only `as_of` value for every validation call. Require `history_scope` to be exactly `current_only` or `point_in_time`, and accept a technically valid row only when `snapshot_at <= retrieved_at <= as_of`.

There are no production callers, so making the cutoff mandatory removes an avoidable fail-open compatibility path. Both candidate and historical rows use the same temporal truth because future or reversed current-only context is also unsafe review evidence.

### Rejected: optional cutoff

An optional cutoff would avoid updating test callers, but any omitted value would preserve the current inability to prove what was knowable at review time. It would create two technical contracts for the same validator.

### Rejected: historical-only time enforcement

Applying the rules only to `point_in_time` rows would prevent some leakage but still admit future or reversed provider estimates as candidate context. Candidate context cannot alter forecasts, but it must still be truthfully timestamped.

## Public Contract

Change the validator signature to:

```python
def validate_source_rows(
    provider: str,
    rows: Sequence[Mapping[str, object]],
    *,
    as_of: object,
    rights_registry: Mapping[str, SourceRights] | None = None,
) -> SourceValidationResult:
```

Parse `as_of` once with the label `review cutoff`. An invalid cutoff is a caller-contract error and raises `ValueError` before any row is reviewed. Add the normalized UTC cutoff to `SourceValidationResult.review_cutoff` so every result identifies the boundary used.

## Row Validation Flow

For each row in supplied order:

1. require `history_scope` to be exactly `current_only` or `point_in_time` after trim/lower normalization;
2. apply the existing field requirements, including the complete comparability fields for point-in-time rows;
3. parse `snapshot_at` and `retrieved_at` independently with existing UTC-only validation;
4. when both timestamps parse, reject `snapshot_at > retrieved_at`;
5. reject either timestamp later than the normalized review cutoff;
6. run the existing `ConsensusSnapshot` value, fiscal-period, metric, and comparability validation;
7. only after all technical checks pass, add the row to candidate/history counts and derive its independent commercial review.

One invalid row does not suppress valid sibling rows. Original one-based row numbers remain stable in technical rejection and commercial review evidence.

## Error And State Behavior

- Missing or unknown scope: reject with `history_scope must be current_only or point_in_time`.
- Invalid cutoff: raise `ValueError` labeled `review cutoff` before processing rows.
- Invalid row timestamp: retain the existing timestamp-specific parser reason.
- Snapshot later than retrieval: reject with `snapshot_at cannot be after retrieved_at`.
- Snapshot or retrieval later than cutoff: reject with a field-specific `is after review cutoff` reason.
- Timestamp exactly equal to retrieval or cutoff: accept if every other technical check passes.
- No technically accepted rows: `still_blocked`; no commercial-review rows.
- Valid current-only rows: `candidate_context_only`.
- Valid point-in-time rows: `historical_evidence_reviewable`.

Time rejection remains technical evidence only. It cannot change the source-rights registry, grant or remove commercial permission, create a provider identity, or promote readiness.

## Testing

Test-first in-memory coverage will prove:

1. all existing valid calls supply and expose one normalized review cutoff;
2. an invalid review cutoff raises before row review;
3. missing and unknown scopes are rejected rather than classified as candidate context;
4. a snapshot after retrieval is rejected;
5. a snapshot after the review cutoff is rejected;
6. a retrieval after the review cutoff is rejected;
7. exact equality at retrieval and cutoff is accepted;
8. technical time rejection produces no commercial review row and does not alter the independent source-level rights decision;
9. a mixed batch preserves valid-row counts and original row numbering;
10. `auto_apply` remains false and no filesystem path is introduced.

## Completion Criteria

- Every accepted source row has an explicit valid scope and proves `snapshot_at <= retrieved_at <= review_cutoff`.
- Every result exposes the normalized cutoff used.
- Temporal technical validity remains independent from exact-source rights and populated Revenue/EPS scope.
- Candidate context remains non-activating and cannot bypass the cutoff.
- The checked-in source-rights registry and all canonical/generated data remain byte-unchanged.
- No real consensus snapshot, readiness promotion, backtest event, calibration evidence, provider claim, or market-validation claim is created.
