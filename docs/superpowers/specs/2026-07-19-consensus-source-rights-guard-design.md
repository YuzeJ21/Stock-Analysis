# Prospective Consensus Source-Rights Guard Design

## Purpose

The prospective consensus collector already validates point-in-time timestamps, immutable snapshot identity, append-only revision lineage, review confirmation, and collection cutoffs. It does not currently join the exact declared source to the checked-in commercial source-rights registry. A technically valid row can therefore be previewed and appended without showing whether commercial rights are approved or whether the registered source covers the supplied Revenue and EPS consensus fields.

Add independent source-rights evidence to every collection preview and a fail-closed write guard in explicit Commercial Research mode. Preserve the existing reviewed local-research workflow. This slice uses temporary test ledgers only and does not collect provider data, write repository CSV or JSON files, or rebuild readiness.

## Selected Contract

- Technical collection validity remains independent from commercial evidence readiness.
- `write_allowed` continues to mean that the record satisfies the reviewed append-only research contract.
- Every preview also reports exact-source commercial-rights status, required consensus scopes, missing scopes, deterministic blockers, and `commercial_write_allowed`.
- A non-empty Revenue value requires exact `revenue_consensus` membership in the registered source's `supported_fields`.
- A non-empty EPS value requires exact `eps_consensus` membership in the registered source's `supported_fields`.
- Revenue-only evidence can therefore be commercially ready even when EPS scope is unavailable, and the inverse is also true. No umbrella estimate field may silently unlock both metrics.
- Unknown, blank, composite, unverified, or scope-incomplete source declarations fail closed. The collector does not split, normalize, or infer provider identities.
- Research mode remains backward compatible: a technically valid, explicitly reviewed local row can still be appended through the existing manual path.
- Explicit Commercial Research mode refuses a write before directory creation or ledger mutation unless both the technical and commercial evidence gates pass.
- Rights approval and field scope do not prove payload accuracy, point-in-time history, freshness, reviewer approval, calibration, or Earnings Nowcast readiness.

## Preview Evidence

Extend `CollectionPreview` with:

- `rights_status` from the exact registry lookup;
- `commercial_rights_approved`;
- `required_supported_fields` in deterministic Revenue-then-EPS order;
- `missing_supported_fields`;
- `commercial_evidence_ready`;
- `commercial_write_allowed`;
- ordered `commercial_blockers`.

The ordered blockers are:

1. `commercial_rights:<status>` when commercial rights are not approved;
2. `registered_consensus_scope_missing:<field>` for every required scope absent from the exact rights record.

The evidence is computed even when a row is technically rejected, so preview users can see independent failure dimensions. `commercial_write_allowed` is true only when both `write_allowed` and `commercial_evidence_ready` are true.

## Mode And Registry Inputs

Production defaults to the existing `COMMERCIAL_RESEARCH_MODE` environment contract and checked-in `config/source_rights.yml`. Tests may pass an explicit mode and injected immutable registry so decisions are deterministic without editing real rights records.

The preview and append paths use the same registry instance. The current checked-in registry contains no commercially approved prospective-consensus source or `revenue_consensus` / `eps_consensus` scope, so the real Commercial Research path remains truthfully blocked until explicit rights evidence is reviewed and registered.

## Testing

Test-first temporary-fixture coverage will prove:

1. an approved source with both scopes is commercially writeable after technical review;
2. Revenue-only and EPS-only records require only their present metric scope;
3. a mixed record preserves independent scope blockers when one metric is unsupported;
4. unknown, unverified, and composite exact sources fail closed without provider inference;
5. research mode preserves the existing append behavior for `reviewed_csv`;
6. commercial mode blocks an unregistered source before creating or mutating a ledger;
7. a fully approved commercial fixture can append in a temporary directory;
8. no repository data, generated artifact, source-rights record, or readiness file changes.

## Completion Criteria

- Prospective consensus preview makes technical and commercial evidence states independently visible.
- Revenue and EPS source scopes remain independent.
- Explicit Commercial Research mode cannot append unapproved or scope-incomplete consensus evidence.
- Research-only behavior remains compatible and still requires explicit review confirmation.
- The real-company nowcast and numerical Beat/Miss probability remain withheld until their separate data and calibration gates are satisfied.
