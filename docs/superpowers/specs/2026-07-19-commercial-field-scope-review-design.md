# Commercial Field-Scope Review Design

## Purpose

Consensus source validation and prospective consensus collection currently implement the same commercial-evidence decision independently. Both resolve an exact source ID, evaluate checked-in commercial rights, derive the fields required by populated Revenue/EPS values, compare those fields with the exact registry record, and combine rights plus scope into one evidence state.

That duplication can drift even though the two paths must agree. Add one pure immutable field-scope decision in the source-rights module and make both consensus paths consume it while retaining their separate technical, cutoff, lineage, candidate/history, preview, and write contracts.

This is a local decision-contract refactor. It does not edit the source-rights registry, approve a provider, fetch data, record a snapshot, rebuild readiness, or write generated artifacts.

## Approaches Considered

### Selected: domain-neutral structured decision

Add a frozen `CommercialFieldScopeReview` and a pure `review_commercial_field_scope(...)` function to `commercial_source_rights.py`. The function returns exact-source rights, the ordered required fields, ordered missing fields, and the combined commercial-evidence state.

It does not generate consensus-specific blocker strings. The source validator and collector continue to render their existing `commercial_rights:*` and `registered_consensus_scope_missing:*` evidence so their public contracts remain stable.

### Rejected: consensus helper in the collector

Putting shared logic in `earnings_consensus_collector.py` would make the read-only source validator depend on a mutation-oriented module and would place general registry semantics below a domain consumer.

### Rejected: configurable blocker-string generator

Passing prefixes or callbacks into the shared function could remove a few additional lines, but it would mix domain presentation with the underlying rights/scope decision and create an unnecessary configuration surface.

## Shared Contract

Add:

```python
@dataclass(frozen=True)
class CommercialFieldScopeReview:
    source_id: str
    rights_status: str
    commercial_rights_approved: bool
    required_supported_fields: tuple[str, ...]
    missing_supported_fields: tuple[str, ...]
    commercial_evidence_ready: bool
```

And:

```python
def review_commercial_field_scope(
    registry: Mapping[str, SourceRights],
    source_id: str,
    required_fields: Sequence[str],
) -> CommercialFieldScopeReview:
```

The function will:

1. trim the source ID without splitting, aliasing, or lowercasing it;
2. trim each required field while preserving supplied order;
3. reject blank or duplicate required fields as caller-contract errors;
4. reuse `commercial_eligibility` for the exact source-rights decision;
5. use only the exact registry record's `supported_fields`;
6. retain each required field absent from that record in stable order;
7. set `commercial_evidence_ready` only when rights are approved and no required field is missing.

An empty required-field sequence is valid and represents a source-rights-only decision. Unknown and composite source IDs remain exact unknown values with every non-empty required field missing.

## Consumer Integration

### Prospective collector

`_collection_preview` derives the populated Revenue/EPS field tuple exactly as it does today, calls the shared review once, and maps its fields into the existing `CollectionPreview`. Technical `write_allowed`, `commercial_write_allowed`, snapshot identity, reasons, blockers, batch behavior, and pre-mutation guard remain unchanged.

### Upstream source validator

The validator calls the shared review with no required fields for its source-level rights result, then once per technically accepted row with that row's populated Revenue/EPS fields. It maps the shared review into the existing row and aggregate result types. Technical rejections, review cutoff, history scope, candidate/history counts, row numbering, and `auto_apply=false` remain unchanged.

Rows rejected technically never receive a row-level commercial review. Source-level exact rights remain visible even when every row is rejected.

## Error And Boundary Behavior

- Blank required field: raise `ValueError` before returning a decision.
- Duplicate required field: raise `ValueError`; do not silently deduplicate caller mistakes.
- Empty required fields: rights-only decision; ready only if rights are approved.
- Unknown source: `unknown_source`, rights false, all required fields missing.
- Registered unverified source: rights false; field-scope completeness remains independently reported.
- Approved scope-incomplete source: rights true; missing fields remain explicit; combined state false.
- Approved scope-complete source: combined state true.

The helper reports registry metadata only. It cannot validate payloads, lineage, timestamps, comparability, reviewer intent, collection, activation, readiness, backtesting, calibration, hosting, or market validation.

## Testing

Test-first coverage will prove:

1. the new result is frozen;
2. approved complete fields are ready in supplied order;
3. approved missing fields remain ordered and block the combined state;
4. unverified rights and supported scope remain independent;
5. unknown/composite exact sources remain unknown and miss all required fields;
6. empty required fields produce a rights-only decision;
7. blank and duplicate required fields fail explicitly;
8. collector outputs for Revenue-only, EPS-only, mixed, unknown, and unverified cases remain byte-for-byte equivalent at the dataclass field level;
9. source-validator outputs for the same cases remain unchanged;
10. the two consensus consumers import and call the shared decision rather than reimplement registry lookup and missing-scope calculation.

## Completion Criteria

- One pure source-rights function owns the exact-source rights plus required-field scope decision used by both consensus paths.
- Existing collector and validator public evidence remains behaviorally unchanged.
- Technical validation and commercial evidence remain independent.
- Consumer-specific blockers and write rules remain local.
- Other price, DCF, fundamentals, and cash-generation evidence models remain untouched because their domain contracts differ.
- The checked-in registry, canonical data, readiness outputs, ledgers, CSV/JSON/report assets, screenshots, and timing artifacts remain unchanged.
