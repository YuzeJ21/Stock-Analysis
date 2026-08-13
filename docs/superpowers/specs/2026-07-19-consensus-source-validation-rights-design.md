# Consensus Source Validation Rights Design

## Purpose

The upstream consensus-source validator currently accepts a caller-supplied `rights_status` string and treats three labels as sufficient for technical row acceptance. A caller can therefore overstate commercial evidence without an exact source-rights registry record or the metric-specific field scope already required by the prospective collector.

Replace that self-declared label with checked-in, exact-source registry evidence. Preserve technically valid research and candidate context even when commercial evidence is incomplete, and make historical rows reviewable rather than calling them commercially ready.

This slice validates supplied in-memory rows only. It does not fetch provider data, append a ledger, activate evidence, rebuild readiness, or write generated artifacts.

## Approaches Considered

### Selected: independent technical acceptance and registry-derived commercial review

Remove the caller-supplied rights label. Resolve the exact normalized provider against the checked-in rights registry, derive the Revenue and EPS scopes required by each technically accepted row, and return immutable row-level plus aggregate commercial-review evidence.

Technical schema and comparability validity continue to determine `accepted_count` and `rejected_rows`. Commercial rights and field scope are reported separately and cannot turn an invalid payload into an accepted row or prevent a valid research-only row from being reviewed.

### Rejected: require commercial permission for technical acceptance

Rejecting all rows whose commercial evidence is incomplete would be fail-closed for commercial use, but it would couple source licensing to research review and suppress truthful candidate context. It would also disagree with the independent readiness contract used by the prospective collector.

### Rejected: retain the result shape and silently replace the label

Deriving only `rights_status` from the registry would prevent caller spoofing, but would not show whether Revenue, EPS, or both lack registered scope. It would retain the ambiguous `historical_evidence_ready` state and provide insufficient review evidence.

## Validation Contract

`validate_source_rows(provider, rows, *, rights_registry=None)` will:

1. normalize `provider` once as an exact source ID by trimming whitespace and lowercasing;
2. load the checked-in registry unless an immutable test/review registry is injected;
3. validate each row's required fields, timestamps, fiscal period, metric values, and comparability using the existing technical contract;
4. reject technically invalid rows without calculating a commercial-ready count for them;
5. for each technically accepted row, require `revenue_consensus` scope only when Revenue is populated and `eps_consensus` only when EPS is populated;
6. derive exact-source rights through `commercial_eligibility` and field support from only that exact registry record;
7. preserve current-only rows as `candidate_context_only` and return technically valid point-in-time rows as `historical_evidence_reviewable`;
8. keep `auto_apply=false` in every result.

Provider aliases, composite labels, configured keys, file origins, and caller assertions are never split or inferred into a registered source.

## Evidence Model

Add immutable `SourceCommercialReview` rows with:

- one-based `row_number`;
- `required_supported_fields` in stable Revenue-then-EPS order;
- `missing_supported_fields` in that same order;
- `commercial_evidence_ready`;
- independent stable `commercial_blockers`.

Extend `SourceValidationResult` with:

- registry-derived `rights_status` and `commercial_rights_approved`;
- `commercial_ready_count` and `commercial_review_required_count` across technically accepted rows;
- aggregate `commercial_evidence_ready`, true only when at least one row is technically accepted and every accepted row is commercially ready;
- deduplicated, stable aggregate `commercial_blockers`;
- ordered `commercial_review_rows`.

The source-level rights decision is shared by every accepted row because the function accepts one exact provider. Metric scope stays row-specific because Revenue and EPS may be populated independently.

## State And Boundary Behavior

- No technically accepted rows: `still_blocked`; commercial evidence is not ready.
- One or more current-only accepted rows and no historical rows: `candidate_context_only`.
- One or more point-in-time accepted rows: `historical_evidence_reviewable`.
- Unknown or composite exact source: `rights_status=unknown_source`; required metric scopes are missing.
- Registered but unapproved source: `rights_status=commercial_rights_unverified`; scope is still reported independently.
- Approved source missing one populated metric scope: rights pass, that metric scope fails.
- Approved exact source with every populated metric scope: commercial evidence is ready for the validator result only.

Commercial evidence readiness remains necessary but insufficient for collection, activation, nowcast readiness, backtesting, calibration, hosting, or market validation.

## Testing

Test-first temporary/in-memory coverage will prove:

1. the default checked-in registry keeps a valid current-only Alpha Vantage row as candidate context while reporting unknown commercial rights and both missing scopes;
2. a technically incomplete historical row remains rejected and does not enter commercial-ready counts;
3. a technically valid historical row is `historical_evidence_reviewable`, not `historical_evidence_ready`;
4. approved Revenue-only, EPS-only, and mixed rows require only their populated metric scopes;
5. an approved source missing EPS scope reports rights ready and EPS scope incomplete independently;
6. a composite provider remains one unknown exact source;
7. the caller-supplied rights parameter no longer exists;
8. every result remains non-writing and `auto_apply=false`.

## Completion Criteria

- No caller can grant source rights through a label passed to `validate_source_rows`.
- Technical acceptance, candidate/history classification, exact-source rights, Revenue scope, and EPS scope remain independently visible.
- Historical evidence is described as reviewable, not activated or commercially ready by implication.
- The checked-in registry remains unchanged and still approves no prospective-consensus source or consensus scope.
- No real snapshot, ledger, readiness artifact, CSV, JSON, report, screenshot, or timing artifact is created or modified.
