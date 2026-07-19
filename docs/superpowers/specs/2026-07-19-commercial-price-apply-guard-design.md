# Commercial Price Apply Guard Design

## Purpose

Staged price validation and preview now report technical validity, lineage completeness, exact-source commercial rights, and registered `prices` scope independently. The final apply function still treats those review states as informational in every mode. That is correct for ordinary local research compatibility, but explicit Commercial Research mode must not write a staged batch whose commercial-evidence gates are incomplete.

Add a fail-closed guard immediately before price mutation in explicit commercial mode. The guard uses the already computed preview evidence and returns a non-writing blocked result when any required state is incomplete. This slice uses temporary test directories only; it does not apply repository data or rebuild readiness.

## Selected Contract

- Research mode remains backward compatible: technically valid staged rows can still follow the existing separately reviewed local apply path even when commercial evidence is incomplete.
- Commercial mode requires all valid staged rows to be `lineage_complete`, `rights_approved`, and `price_scope_complete` before mutation.
- Existing missing-file and technical-invalid behavior remains unchanged and non-writing.
- The guard runs before backup creation or canonical-file writes.
- A blocked result returns `applied=false`, `backup_path=null`, `apply_status=commercial_evidence_review_required`, and deterministic `apply_blockers`.
- A permitted commercial batch still requires an explicit apply invocation; passing the guard does not trigger automatic apply or readiness rebuild.

## Mode And Registry Inputs

Production defaults to the existing `COMMERCIAL_RESEARCH_MODE` environment contract. Tests may pass an explicit boolean and injected immutable rights registry so behavior is deterministic and cannot edit the checked-in registry.

The apply function passes the same injected/default registry through preview and validation. It never substitutes a different source decision between review and mutation.

## Blockers

The ordered blocker list may contain:

- `price_lineage_review_required`;
- `commercial_rights_review_required`;
- `registered_price_scope_review_required`.

Counts and distinct-source evidence stay in the returned preview summary. Unknown, blank, composite, unverified, or scope-incomplete sources therefore remain explainable without provider inference.

## Testing

Test-first temporary-fixture coverage will prove:

1. research mode preserves the existing apply behavior for an unregistered source;
2. commercial mode blocks that same batch before backup or canonical mutation;
3. a lineage-incomplete but rights-approved batch remains blocked;
4. a rights-approved source without `prices` scope remains blocked;
5. a complete approved price source can pass the guard and preserve the existing merge/no-delete behavior;
6. no repository data, generated artifact, rights record, or readiness file changes.

## Completion Criteria

- Explicit commercial mode cannot apply a staged price batch until all three commercial-evidence states are complete.
- Research mode behavior remains compatible.
- Blocked outcomes are non-writing, deterministic, and explainable.
- Documentation and PR #113 record that guard passage is necessary but not proof of payload correctness, reviewer approval, freshness, readiness, or market validation.
