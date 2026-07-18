# Peer Evidence Quality Design

## Problem

The product currently treats a source-backed row in `data/peers.csv` as a trusted relationship and may use any such peer with sufficient local financial data in relative valuation. The row preserves a source, as-of date, peer group, sector, and industry, but it does not durably preserve a reviewer-assigned peer role, an explicit economic-comparability rationale, or a decision about whether the relationship may anchor valuation. Sector or industry similarity is therefore capable of becoming stronger valuation evidence than the documented methodology allows.

## Decision

Add a fail-closed peer evidence-quality contract that evaluates five states independently:

1. relationship provenance;
2. reviewer-assigned peer role;
3. documented economic comparability;
4. result read-through evidence; and
5. valuation-anchor eligibility.

The canonical peer row gains four optional evidence fields:

- `peer_role`: one of `core_peer`, `secondary_peer`, `aspirational_peer`, `negative_peer`, `excluded_close_peer`, or `not_clean_comp`;
- `relationship_rationale`: the source-backed reason the companies are related;
- `comparability_basis`: the reviewed economic dimensions that support or limit comparison, such as business model, geography, size, growth, margin, leverage, cyclicality, liquidity, or accounting basis;
- `valuation_anchor_eligible`: explicit `yes` or `no`.

Only `core_peer` and `secondary_peer` rows with relationship provenance, a non-placeholder relationship rationale, a non-placeholder comparability basis, and explicit `valuation_anchor_eligible=yes` may enter peer-median valuation calculations. Other reviewed roles remain context-only. Missing or invalid fields produce named blockers; legacy rows are never upgraded by inference.

## Data Flow

The peer source-review packet and template collect the four fields. The write-back guard preserves them in its exact CSV scaffold. Local schema validation recognizes them as optional columns, so older files remain readable while their valuation-anchor state stays withheld.

A focused `peer_evidence_quality` module owns role validation and the deterministic anchor decision. Both the local provider and readiness engine call the same contract:

- the provider exposes quality state with each trusted relationship and sends only eligible rows into relative valuation;
- the readiness engine keeps relationship/trend readiness separate from valuation-anchor readiness and reports explicit anchor blockers;
- the Peer Read-Through Map displays role, comparability, and valuation-anchor state while retaining its independent result/fiscal-timing gate.

Candidate peer rows never enter this contract as trusted relationships and cannot become valuation anchors.

## User Experience

Company Workbench answers the primary question first: which peer results can be reviewed as business context, and which peer relationships are eligible to anchor valuation. The compact table adds `Peer Role`, `Comparability`, and `Valuation Anchor`. Raw sources, identity hashes, and full evidence objects remain under Advanced.

When no rows meet the anchor contract, relative peer valuation is withheld and standalone multiples may still be shown. The product names the missing peer-role or comparability proof instead of suggesting a peer median is usable.

## Compatibility And Migration

Existing seven-column peer files remain schema-valid. Their rows retain source-backed relationship and trend context, but become `comparability_unreviewed` and `valuation_anchor_withheld` until an explicit review adds the new fields. Synthetic fixtures that exercise valuation readiness must declare the fields explicitly; test-only data remains visibly synthetic.

No existing canonical row is automatically migrated or assigned a role. No broad peer refresh or source loop is part of this slice.

## Safety Boundaries

- Peer evidence remains research-only and cannot produce investment advice or transaction instructions.
- Candidate context cannot satisfy relationship provenance, comparability, or valuation-anchor eligibility.
- A peer role never supplies missing price, fundamentals, fiscal periods, result evidence, source rights, or freshness.
- Result read-through remains directional context and never changes Earnings Nowcast, DCF assumptions, deterministic forecasts, or probabilities.
- The slice does not fabricate roles, comparability evidence, peers, sources, or timestamps.

## Verification

Focused tests cover role validation, legacy-row fail-closed behavior, explicit context-only roles, eligible anchors, provider filtering, independent readiness states, source-review/write-back preservation, and Company Workbench presentation. Full repository and public-release gates must pass, followed by exact-path staging and generated-artifact hygiene checks.
