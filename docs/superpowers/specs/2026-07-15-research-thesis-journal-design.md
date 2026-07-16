# Research Thesis and Evidence Journal Design

## Purpose

The Research Thesis and Evidence Journal answers: "What is the current research hypothesis, what evidence supports or conflicts with it, and what would invalidate it?"

The journal connects the existing selected-profile truth, Research Change Monitor, Review Queue, and Single-Stock Report. It is research documentation only. It never generates a recommendation, changes readiness, applies source data, or converts generated product copy into a user-owned thesis.

## Product Boundary

The journal is part of the existing five-page workflow, not a sixth public page:

`Home -> Stock Selector -> Single-Stock Report -> Data Health -> Proof History`

The Single-Stock Report shows a compact journal answer for the selected ticker. Raw history stays under one Advanced control. Operator commands remain outside the public first viewport.

Generated `purpose_thesis` and `invalidation_condition` fields are contextual prompts only. They are never written into the journal unless a reviewer explicitly records a new entry.

## Append-Only Contract

The canonical reviewed ledger is `data/research_thesis_journal.csv`. Every row is immutable evidence of one reviewer action.

Required columns:

- `schema_version`
- `entry_id`
- `profile_key`
- `ticker`
- `thesis_id`
- `entry_type`
- `recorded_at`
- `effective_at`
- `reviewer`
- `summary`
- `evidence_direction`
- `source`
- `source_ref`
- `source_published_at`
- `confidence`
- `review_due_date`
- `supersedes_entry_id`

Allowed entry types are `thesis`, `evidence`, `catalyst`, `risk`, `invalidation`, `confidence`, and `review`.

Validation rules:

1. Profile and ticker are always explicit.
2. All timestamps are ISO-8601 and cannot be after `recorded_at` when they describe published or effective evidence.
3. `evidence` requires `supporting`, `conflicting`, or `context` direction.
4. `evidence`, `catalyst`, `risk`, and `invalidation` require source, durable source reference, and source publication timestamp.
5. Confidence, when present, is a decimal from 0 through 1. It measures the reviewer's confidence in the documented hypothesis, not investment conviction or expected return.
6. A thesis revision must point to the prior thesis entry through `supersedes_entry_id`; prior rows are retained.
7. Duplicate `entry_id` values are rejected.
8. Cross-profile or cross-ticker supersession is rejected.
9. Recording requires an explicit reviewed confirmation; preview is read-only by default.

## Derived Journal State

The product derives, without rewriting the ledger:

- current thesis entry
- thesis revision count and change history
- latest confidence and confidence history
- supporting, conflicting, and contextual evidence
- current catalysts and risks
- invalidation conditions
- latest review timestamp and next review date
- overdue state
- source and timestamp completeness

Missing evidence remains visible. An empty journal is `not_started`, not a generated thesis. A journal with a thesis but no invalidation condition is `incomplete`. A supersession chain with invalid references fails closed.

## Change Monitor Integration

Research Change events may create a suggested research task that points a reviewer to the journal. They do not create or modify journal rows. Review Queue resolutions also do not alter the journal. This preserves the boundary between source change detection, reviewer workflow, and authored research documentation.

## Public UI Contract

The Single-Stock Report journal section answers in this order:

1. Is a reviewed thesis recorded for this selected profile and ticker?
2. What is the current hypothesis?
3. What supporting and conflicting evidence is recorded?
4. What catalyst, risk, and invalidation conditions remain active?
5. When was it reviewed and when is the next review due?
6. What is the one next research action?

No journal produces buy, sell, hold, ranking, target-price, or position-sizing language. Raw entries, IDs, source references, and confidence history stay under Advanced.

## Commands

- `make thesis-journal TICKER=<ticker>` renders the selected-profile journal read-only.
- `make thesis-journal-preview ...` validates and prints one prospective entry without writing.
- `CONFIRM_REVIEWED=1 make thesis-journal-record ...` appends one validated reviewed entry.

The commands never refresh providers, mutate readiness, stage files, commit, or push.

## Verification

- contract and validation tests
- append-only and supersession tests
- profile isolation tests
- no-fabrication and no-recommendation wording tests
- dashboard helper and route tests
- Makefile and diff-hygiene tests
- full suite, dashboard smoke, browser QA, public checks, and clean diff checks

## Explicitly Deferred

- collaborative editing and authentication
- hosted notifications
- automatic thesis updates
- LLM-authored journal entries
- portfolio/account data
- investment scores or performance claims
