# Point-in-Time Benchmark and Universe Foundation Design

## Purpose

Priority 4 establishes a provider-neutral, read-only evidence boundary for
historical benchmark membership and research-universe membership. It must make
survivorship, identifier, corporate-action, delisting, cutoff, source-rights,
revision, and leakage failures explicit before any historical result is called
out-of-sample evidence.

This design does not select a provider, fetch data, modify the current
universe, rebuild readiness, calculate an investment recommendation, or make
historical data commercially usable. Synthetic fixtures prove software
behavior only. Priority 4 remains incomplete until one bounded permitted real
dataset passes every exit gate and reproduces from its immutable manifest.

## Approved Approach

Use an isolated validation layer rather than extending the current
`src/universe_builder.py` merge path.

The existing universe builder remains a current-state metadata workflow keyed
primarily by ticker. It may preview and merge contemporary membership sources,
but it cannot prove historical identity or membership. Reusing that path would
risk silently substituting today's ticker, constituents, listing state, or
source retrieval for historical evidence.

The new layer consumes an operator-supplied immutable manifest plus four
explicit evidence contracts. It validates and classifies rows in memory and
returns deterministic diagnostics. It never writes a normalized file, repairs
an input, maps a ticker by inference, applies a row, or changes canonical data.

## Scope

The first implementation slice includes:

1. exact schemas for security identity, membership observations,
   corporate-action and listing-status events, and an immutable manifest;
2. deterministic file-integrity and manifest validation;
3. independent technical, temporal, identity, membership, corporate-action,
   delisting, source-rights, reproduction, and leakage decisions;
4. in-memory `raw`, `normalized`, `excluded`, and `analysis_eligible`
   classifications with stable reason codes;
5. deterministic membership counts and membership digests at a declared
   cutoff;
6. read-only status and preview interfaces;
7. synthetic, test-only fixtures and no-write tests.

The first slice excludes:

- provider selection, provider calls, keys, accounts, or license changes;
- writing, recording, applying, refreshing, rebuilding, or publishing data;
- migration of `data/universe.csv`, `data/universe_master.csv`, or
  `data/universe_active.csv`;
- price adjustment, benchmark return calculation, model training,
  backtesting, calibration, or probability;
- Company Workbench, Discover, Monitor, or public UI integration;
- broad coverage, automated source mapping, or current-ticker fallback;
- declaring Priority 4 complete from schemas, fixtures, or green tests.

## Architecture

Create one focused module, `src/point_in_time_universe.py`, with no dependency
on the existing universe apply path. The module may reuse
`src.commercial_source_rights` for exact-source commercial eligibility and
registered field-scope review.

The module has five responsibilities:

1. load the manifest and referenced files without modifying them;
2. verify manifest identity, schema version, file hashes, row counts, and
   cutoff policy;
3. validate each evidence contract and its revision lineage;
4. compose independent readiness decisions without collapsing their states;
5. produce a deterministic read-only status or preview packet.

Parsing, validation, lineage resolution, cutoff selection, and rendering stay
separate so each unit has one observable contract and can be tested without
provider or repository data.

## Input Contracts

All timestamps are timezone-aware RFC 3339 UTC values ending in `Z`. Dates use
real calendar `YYYY-MM-DD` values. Blank strings do not satisfy required
fields. Identifiers are case-sensitive opaque strings except tickers, which
are normalized to uppercase for display only.

### Security identity observations

Required columns:

| Column | Meaning |
| --- | --- |
| `identity_row_id` | Immutable unique row identifier |
| `security_id` | Stable security identifier; never derived from ticker |
| `issuer_id` | Stable issuer identifier; must not equal `security_id` |
| `ticker` | Ticker observed during the validity interval |
| `exchange` | Listing venue observed during the validity interval |
| `security_type` | Explicit security type |
| `currency` | Trading currency |
| `valid_from` | Inclusive identity-validity timestamp |
| `valid_to` | Exclusive validity timestamp or blank for an open interval |
| `source_id` | Exact source-rights registry identifier |
| `source_ref` | Durable source reference |
| `source_published_at` | When the source made the observation available |
| `retrieved_at` | When the evidence was retrieved |
| `supersedes_identity_row_id` | Exact prior row or blank for a root |

Ticker uniqueness is not required globally because symbols may change or be
reused. A security may have only one active identity interval at an evaluated
instant. Overlapping unresolved intervals, unknown parents, forks, cycles,
cross-security supersession, and reversed validity are excluded.
Adjacent chronological intervals for one stable `security_id` must retain the
same `issuer_id`; no corporate-action event authorizes stable-ID reuse across
issuers. A same-effective superseding correction may replace an erroneous
issuer observation before the effective history is evaluated.

### Membership observations

Required columns:

| Column | Meaning |
| --- | --- |
| `membership_row_id` | Immutable unique row identifier |
| `universe_id` | Stable benchmark or research-universe identifier |
| `universe_kind` | Exactly `benchmark` or `research_universe` |
| `security_id` | Stable security identifier |
| `membership_state` | Exactly `included` or `excluded` |
| `effective_from` | Inclusive membership timestamp |
| `effective_to` | Exclusive membership timestamp or blank |
| `observation_at` | Point in time represented by the observation |
| `source_id` | Exact source-rights registry identifier |
| `source_ref` | Durable source reference |
| `source_published_at` | Source publication timestamp |
| `retrieved_at` | Evidence retrieval timestamp |
| `supersedes_membership_row_id` | Exact prior row or blank for a root |

A membership row is not usable unless its security identity is valid at the
evaluation timestamp. Missing exclusions are not inferred from missing
inclusions. An input must declare its coverage semantics in the manifest as
either `complete_snapshot` or `event_history`; the validator never guesses
which representation was supplied.

### Corporate-action and listing-status events

Required columns:

| Column | Meaning |
| --- | --- |
| `event_row_id` | Immutable unique row identifier |
| `security_id` | Affected stable security identifier |
| `event_type` | One declared event type |
| `effective_at` | Event-effective timestamp |
| `successor_security_id` | Explicit successor security or blank |
| `ratio_numerator` | Explicit action ratio numerator or blank |
| `ratio_denominator` | Explicit action ratio denominator or blank |
| `listing_state_after` | `active`, `delisted`, `suspended`, or blank |
| `source_id` | Exact source-rights registry identifier |
| `source_ref` | Durable source reference |
| `source_published_at` | Source publication timestamp |
| `retrieved_at` | Evidence retrieval timestamp |
| `supersedes_event_row_id` | Exact prior row or blank for a root |

Allowed event types are `listing`, `ticker_change`, `exchange_change`,
`split`, `reverse_split`, `merger`, `acquisition`, `spinoff`, `delisting`,
`suspension`, and `reactivation`.

Split and reverse-split events require positive finite numerator and
denominator values. Merger, acquisition, and spinoff events require an
explicit successor when the original security ceases to represent the same
economic security. Delisting requires `listing_state_after=delisted`.
Successor relationships are never inferred from ticker similarity.

### Evaluation observations

Required columns:

| Column | Meaning |
| --- | --- |
| `evaluation_row_id` | Immutable unique evaluation identifier |
| `universe_id` | Evaluated benchmark or research universe |
| `evaluation_at` | Historical evaluation timestamp |
| `available_at` | Earliest timestamp the evaluation was available |
| `partition` | `train`, `validation`, `test`, or `walk_forward` |
| `source_ref` | Durable evaluation reference |

This file contains evaluation cutoffs, not forecasts, returns, labels, or
probabilities. An evaluation row is excluded when `available_at` is after
`evaluation_at`, its universe is undeclared, or its partition violates the
manifest boundary policy.

## Immutable Manifest

The JSON manifest contains:

- `schema_version`, initially exactly `point_in_time_universe_v1`;
- `dataset_id` and `manifest_id`;
- `manifest_created_at`;
- `observation_cutoff_at`;
- `coverage_semantics`, exactly `complete_snapshot` or `event_history`;
- `declared_universes`, including one or more IDs and their kinds;
- `allowed_source_ids`;
- `source_rights_registry_sha256`;
- `files`, with relative path, contract name, SHA-256, and row count for each
  of the four CSV inputs;
- `evaluation_policy`, exactly one of:
  - chronological non-overlapping `train`, `validation`, and `test`
    boundaries; or
  - chronological `walk_forward` with a positive minimum history count;
- `corporate_action_policy`, which must declare every allowed event type as
  `required`, `not_applicable`, or `unsupported`;
- `delisting_policy`, including whether delisted securities remain in
  historical membership and how missing delisting evidence is treated;
- `survivorship_policy`, which must prohibit filtering historical membership
  by current listing state;
- `reproduction_contract`, initially
  `membership_count_and_sha256_at_cutoff_v1`.

The manifest may reference files only beneath its own directory after path
resolution. Absolute paths, parent traversal, symlink escape, duplicate
contract entries, missing contracts, unlisted files, and hash or row-count
mismatches fail closed.

Manifest containers are limited to 64 nested levels before immutable semantic
freezing. Source identifiers must be scalar, control-free structural tokens.
Both boundaries fail closed with stable nonzero CLI errors, without traceback
or package mutation; ordinary Unicode scalar identifiers remain supported.

The rights digest binds validation to the exact reviewed registry state.
Changing the source-rights registry requires a new manifest and validation;
the validator does not silently reuse a previous commercial decision.

## Validation and State Model

The preview packet reports these states independently:

| State | Pass condition |
| --- | --- |
| `manifest_integrity` | Schema, paths, hashes, row counts, and registry digest match |
| `technical_validity` | Required fields, types, enums, identifiers, and ratios are valid |
| `temporal_validity` | Publication, retrieval, validity, membership, event, and evaluation timestamps obey the cutoff |
| `identity_coverage` | Every evaluated membership has one unambiguous valid security identity |
| `membership_coverage` | Declared coverage semantics and membership lineage are complete for the evaluated cutoff |
| `corporate_action_coverage` | Required action types are explicitly covered and resolvable |
| `delisting_coverage` | Listing state and delisted historical members are handled by the declared policy |
| `source_rights_eligibility` | Every populated evidence field has approved exact-source commercial rights and registered scope |
| `reproduction_ready` | Recomputed counts and membership digests are deterministic |
| `leakage_safe` | No evidence unavailable at an evaluation cutoff enters that evaluation |

Each state is one of `passed`, `blocked`, or `not_applicable`. One passed state
cannot promote another. The packet is `analysis_eligible` only when every
applicable state passes and at least one benchmark evaluation and one research
universe evaluation remain eligible. A technically valid row with unverified
rights remains technically valid but commercially ineligible.

`analysis_eligible` is local evidence eligibility only. It does not activate
Company Workbench, readiness, backtesting, calibration, or a public claim.

## Row Classification

The validator preserves four in-memory collections:

- `raw`: ordered input rows with file and one-based source-row identity;
- `normalized`: technically parseable rows with canonical timestamps and
  display tickers;
- `excluded`: rows withheld from an evaluation, each with stable reason codes;
- `analysis_eligible`: rows that pass every applicable gate for one exact
  evaluation cutoff.

The first slice does not write any collection. Preview output is capped and
contains counts, reason-code summaries, deterministic digests, and a bounded
sample; it does not echo an entire proprietary dataset.

Initial stable reason-code families are:

- `manifest_*`;
- `schema_*`;
- `lineage_*`;
- `identity_*`;
- `membership_*`;
- `corporate_action_*`;
- `delisting_*`;
- `source_rights_*`;
- `cutoff_*`;
- `leakage_*`;
- `partition_*`;
- `reproduction_*`.

Reason codes are machine-stable; human explanations may improve without
changing the code.

## Revision and Cutoff Rules

Every contract uses one unique row ID and an optional exact supersession
parent. Within the same logical scope, lineage must form one append-ordered,
timestamp-increasing root-to-leaf chain. Duplicate IDs, missing parents,
cross-scope parents, multiple roots, forks, cycles, reversed order, and
non-leaf supersession are excluded.

For a given evaluation:

1. `source_published_at <= evaluation_at`;
2. `retrieved_at <= evaluation_at`;
3. `observation_at <= evaluation_at`;
4. identity and membership effective intervals contain `evaluation_at`;
5. event evidence used for resolution is effective and available no later
   than `evaluation_at`;
6. only the latest unambiguous lineage leaf available by the cutoff is used;
7. later revisions remain invisible even when they describe an earlier
   effective date.

Today's constituents, ticker, listing state, prices, fundamentals, or
source-rights decision are never substituted for the historical cutoff.

## Reproduction Contract

For each `universe_id` and evaluation cutoff, the validator:

1. selects eligible included stable `security_id` values;
2. sorts them by Unicode code point;
3. joins them with a single newline and no trailing newline;
4. computes SHA-256 over UTF-8 bytes;
5. reports the member count and digest.

Repeated validation of identical bytes and registry state must reproduce the
same count, digest, exclusions, reason counts, and state decisions. The
manifest does not contain an expected result in the first slice because that
would permit circular self-attestation. A later reviewed real-data acceptance
step records the independently reviewed expected count and digest in a
separate evidence record.

## Source-Rights Boundary

The validator uses the existing exact-source registry but does not modify
`config/source_rights.yml`.

Commercially eligible real evidence requires approved rights and registered
field scope for:

- `security_identity`;
- `universe_membership`;
- `corporate_actions`;
- `delistings`.

If those scopes or rights are absent, technical validation may proceed while
`source_rights_eligibility` remains blocked. Tests inject an isolated synthetic
registry; test registry entries do not authorize production or commercial use.

## Read-Only Interfaces

The planned command contracts are:

```text
make point-in-time-universe-status MANIFEST=<path>
make point-in-time-universe-preview MANIFEST=<path> TOP_N=20
```

Both commands:

- read only the supplied manifest, referenced files, and rights registry;
- perform no network access;
- create no directory or artifact;
- never mutate canonical or generated data;
- emit research-only and no-completion boundaries;
- return nonzero only for invocation or unreadable/invalid manifest errors;
- return zero with explicit blocked states for a readable evidence package
  that fails eligibility gates.

Status emits the independent states and counts. Preview adds capped row and
exclusion samples plus deterministic membership digests. Neither command
offers an apply, record, refresh, or rebuild instruction.

## Error Handling

Invocation errors identify the missing or invalid argument without a
traceback. Unreadable JSON, unsafe paths, malformed CSV shape, hash mismatch,
or unsupported schema stops package evaluation because input identity is
unreliable.

Row-level failures remain reviewable when the manifest is trustworthy. They
produce blocked independent states and stable exclusions rather than silently
dropping rows or repairing values.

No exception path may create a file, partially write output, change readiness,
or fall back to current universe data.

## Testing Strategy

Tests use temporary directories and synthetic fixtures only.

Required test groups:

1. valid bounded package and deterministic count/digest reproduction;
2. missing/extra file, path traversal, symlink escape, hash mismatch, row-count
   mismatch, schema mismatch, and registry-digest mismatch;
3. stable security identity across ticker change and ticker reuse across
   different securities;
4. overlapping identity, unresolved membership, lineage fork/cycle, and
   ambiguous leaf exclusions;
5. split, merger/successor, spinoff, suspension, reactivation, and delisting
   policy validation;
6. current-constituent and current-listing-state substitution rejection;
7. post-cutoff publication, retrieval, revision, membership, event, and
   evaluation leakage;
8. non-overlapping partition and chronological walk-forward validation;
9. independent technical and commercial-rights states;
10. empty package, no benchmark, no research universe, and all-excluded
    behavior;
11. CLI and Make status/preview rendering;
12. byte-for-byte no-write assertions covering the entire temporary root.

Focused tests must run before the full suite. Every implementation behavior
starts with a failing test. Release checks remain the existing dashboard,
public wording, public, commercial-beta, pilot, diff-hygiene, staged-hygiene,
and whitespace gates.

## Product and Evidence Boundaries

This foundation is research infrastructure, not an investing output.

- It does not rank companies or securities.
- It does not issue buy, sell, allocation, sizing, stop-loss, take-profit, or
  transaction instructions.
- It does not predict price or earnings outcomes.
- It does not turn candidate context into trusted evidence.
- It does not activate Revenue, EPS, valuation, catalyst, outcome, backtest,
  calibration, or probability readiness.
- Technical evidence remains outside the primary research answer unless a
  later separately approved UI design places a concise state under Advanced.

## Acceptance Criteria

The local implementation slice is accepted only when:

1. every named contract and state is implemented exactly and tested;
2. status and preview are demonstrably write-free;
3. stable IDs, historical intervals, revision lineage, actions, delistings,
   survivorship, source rights, cutoffs, reproduction, and leakage remain
   independent fail-closed gates;
4. no current-state fallback or inferred mapping exists;
5. synthetic fixtures remain test-only;
6. existing current-universe workflows are unchanged;
7. focused, full, release, and hygiene gates pass;
8. exact intentional files are committed and pushed to
   `codex/personal-research-mode-mvp`;
9. draft PR #113 has exact-head CI evidence.

Priority 4 itself exits only after one bounded permitted real dataset passes
all local gates, an independently reviewed expected membership count and digest
reproduce from the immutable manifest, and the exact source rights and
historical coverage are directly evidenced. The local implementation slice
does not satisfy that exit gate by itself.
