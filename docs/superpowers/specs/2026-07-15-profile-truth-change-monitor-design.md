# Profile Truth Layer And Research Change Monitor Design

**Status:** Approved on 2026-07-15

**Product:** Stock Research Command Center

**Principle:** Data readiness first. Analysis second. Research decision last.

## Objective

Connect the existing readiness, source-proof, filing, Nowcast, and report surfaces into a repeatable research-review workflow without adding another disconnected command center.

The work has two dependent parts:

1. Establish one authoritative profile and freshness context everywhere profile-specific data or counts appear.
2. Build an append-only Research Change Monitor and a derived Review Queue from evidence-backed changes within that selected profile.

The feature is research-only. It does not provide investment advice, rankings, trade instructions, broker actions, order routing, auto-trading, or inferred source data.

## User Questions

The Profile Truth Layer answers:

> Which data profile am I viewing, how current is it, and which snapshot produced these coverage counts?

The Research Change Monitor answers:

> What changed since the last comparable review, what evidence supports the change, and what research task should I perform next?

The Review Queue answers:

> Which unresolved evidence-backed changes require attention first?

## Approved Architecture

### 1. Central profile context

Add one read-only profile context module used by dashboard pages and profile-specific status commands. It resolves all paths through `src.paths` and never falls back from the selected profile to another profile.

The context contains:

- profile key: `default`, `demo`, or `local`
- public label: `Default`, `Demo`, or `Local Research`
- selected data directory
- selected outputs directory
- latest underlying source date
- readiness snapshot generation time
- snapshot identity
- freshness state: `current`, `stale`, `missing`, or `mixed`
- freshness explanation and safe next action
- selected-profile coverage counts
- lane-specific source dates for advanced detail

All coverage counts come from the selected profile's readiness artifacts. A missing selected-profile artifact produces a missing state; it does not read the default profile.

### 2. Time semantics

The compact UI shows two distinct times:

- **Sources through:** the latest valid source/as-of date observed in selected-profile canonical inputs.
- **Readiness built:** the generation or modification time of the selected-profile readiness snapshot.

These values must not be merged into a single ambiguous date. Lane-specific source dates remain available under Advanced.

When source dates differ by lane, the compact value is a summary only. It must not imply that every lane is equally fresh.

### 3. Snapshot identity

Snapshot identity provides traceability, not proof of correctness or freshness.

- `demo`: use the tracked demo manifest identity and file hashes.
- `local` and `default`: compute a deterministic fingerprint from the selected canonical source files and selected readiness artifact.
- Missing inputs are included explicitly in the fingerprint contract so the same present files do not collide with a complete snapshot.
- Paths are represented relative to the selected profile root; absolute machine paths are not part of the identity.
- The identity is shortened for display and retained in full in the context payload.

### 4. Freshness rules

Freshness is fail-closed:

- `current`: selected readiness artifacts exist and are not older than relevant canonical source files.
- `stale`: selected readiness artifacts exist but relevant source files are newer.
- `missing`: required selected-profile readiness artifacts do not exist.
- `mixed`: lane artifacts disagree or only some required artifacts exist.

Existing artifact-freshness helpers should be reused or made profile-aware. Dashboard freshness checks must not hard-code `data/` or `outputs/`.

### 5. Global trust strip

Every public and operator page receives the same compact trust strip near the global app shell:

> Local Research | Sources through 2026-07-15 | Readiness built 2026-07-15 20:04 EDT | Current

The strip also shows selected-profile Price-ready, Fundamentals-ready, DCF-ready, and Peer-ready counts where space permits.

Responsive behavior:

- Desktop shows profile, both times, freshness, and compact counts.
- Mobile always keeps profile and freshness visible; dates and counts may wrap or move into one collapsed detail row.
- No text may overflow or obscure the primary page action.

Advanced profile details show selected paths, full snapshot identity, lane dates, freshness explanation, and the read-only refresh command. Raw paths and hashes do not appear in the first public viewport.

### 6. Status command contract

Profile-specific status views print the same context before profile-specific counts. Initial integration covers:

- project status
- status check
- readiness operations center
- coverage frontier
- trusted-data pilot candidates and packets
- profile-specific pilot/public readiness views when they display data counts

Commands that do not consume profile data, such as license status, do not need this preamble.

The command contract uses the same context builder as the dashboard. It must not maintain separate label, fingerprint, or freshness logic.

## Research Change Monitor

### 7. Event model

Changes are normalized into an append-only event contract. An event contains:

- event ID
- ticker or explicit profile-level scope
- event family
- event subtype
- prior value/state
- current value/state
- source
- source reference
- source publication time, when known
- retrieval time, when known
- detection time
- selected profile
- prior snapshot identity
- current snapshot identity
- evidence status
- materiality category
- suggested research task
- review status
- review resolution and timestamp, when resolved

An event is not created unless there is comparable before/after evidence. A missing baseline produces a `baseline_missing` diagnostic, not a fabricated change.

### 8. Event families

The first supported families are:

- SEC filing arrived
- readiness state changed
- price or momentum readiness changed
- fundamentals field revised
- share-count field revised
- DCF input or availability changed
- Nowcast consensus or evidence changed
- input became stale
- input became blocked
- previously blocked input became available

Peer and news evidence remains candidate context unless reviewed trusted proof exists. Candidate context never changes trusted readiness automatically.

### 9. Event generation

Event generation is deterministic and read-only.

Inputs may include:

- current and previous ticker-readiness reports
- reviewed proof ledgers
- selected-profile SEC submissions and filing metadata caches
- selected-profile fundamentals and price inputs
- append-only Nowcast actuals, consensus, and evidence rows
- existing report/source provenance

The generator:

1. Resolves the selected profile.
2. Loads a comparable prior and current snapshot from that profile only.
3. Emits normalized candidate events.
4. Deduplicates by stable event identity.
5. Writes nothing in dry-run/read-only mode.
6. Appends only after an explicit reviewed event-recording action.

No data import, readiness apply, report refresh, commit, or push is triggered by event generation.

### 10. Evidence states

Events use explicit evidence states:

- `source_backed`
- `reviewed_proof`
- `candidate_context_only`
- `baseline_missing`
- `stale`
- `still_blocked`
- `excluded`

The state describes evidence usability. It is not an investment conclusion or confidence score.

### 11. Derived Review Queue

The Review Queue is a deterministic view over unresolved events. It is not a second source of truth and does not duplicate event storage.

Priority order:

1. Previously usable analysis became blocked or stale.
2. A new filing or reviewed source-backed record arrived.
3. DCF or Nowcast inputs changed.
4. Readiness improved and requires evidence review.
5. Context-only price or momentum state changed.

Tie breakers are deterministic: materiality, source publication time, detection time, ticker, and event ID.

Each queue row contains one research task, such as:

- review the new filing
- inspect the changed source row
- validate and preview the staged source-backed update
- rebuild readiness after approved source review
- confirm that a stale input should remain withheld

Tasks never contain buy, sell, hold, outperform, target-price, allocation, or execution instructions.

### 12. Review resolution

Review outcomes are append-only and preserve the original event:

- `open`
- `reviewed_no_change`
- `reviewed_supported`
- `still_blocked`
- `skipped`
- `excluded`
- `intentionally_deferred`

Resolving a task does not change source data or readiness. Any readiness change still uses the existing validate, preview, apply, rebuild, and proof gates.

## Product Integration

### 13. No new top-level command center

The monitor is integrated into the existing five-page workflow:

- **Home:** compact `Changed since last review` summary and open-event count.
- **Stock Selector:** optional `Needs review` filter and change-reason column.
- **Single-Stock Report:** ticker-specific evidence timeline below the selected-ticker answer.
- **Data Health:** readiness/source-change events and the route to existing proof controls.
- **Proof History:** reviewed event outcomes alongside existing proof evidence.
- **Operator Advanced:** full event ledger, diagnostics, and read-only generation/closeout commands.

Public pages show the answer and one next action first. Raw event rows, hashes, commands, and diagnostics remain collapsed.

### 14. Empty and failure states

- No comparable baseline: explain that change detection cannot run yet and show the baseline action.
- No changes: state that no evidence-backed changes were detected for the selected comparison.
- Stale snapshot: withhold a definitive change summary and route to the existing readiness refresh boundary.
- Missing event ledger: show derived read-only changes if comparable snapshots exist; otherwise show unavailable.
- Parse or schema failure: fail closed, preserve existing readiness, and expose diagnostics only under Advanced.

## Storage And Hygiene

- Generated event previews and queue exports live under selected-profile outputs and remain unstaged by default.
- A durable reviewed event ledger, if introduced, is append-only and intentionally small.
- Generated CSV/JSON/report/screenshots remain excluded unless an exact artifact is intentionally reviewed.
- No `git add -A` workflow is introduced.
- Profile directories remain isolated.

## Testing

### Profile context

- profile labels and selected paths
- no cross-profile fallback
- separate source and readiness timestamps
- deterministic snapshot identity
- demo manifest identity
- current, stale, missing, and mixed freshness
- profile-matched coverage counts
- command preamble consistency
- desktop and mobile trust-strip rendering

### Change monitor

- readiness transition detection
- filing arrival detection
- fundamentals and share-count revisions
- DCF availability changes
- Nowcast evidence changes
- stale and blocked transitions
- no event without a comparable baseline
- cross-profile comparison rejection
- stable event deduplication
- deterministic priority order
- candidate context cannot promote trusted readiness
- review resolution does not mutate source data
- prohibited advice/execution wording absent

### Integration

- all five public routes keep their question/answer/next-action contract
- public first viewport does not expose raw diagnostics
- existing proof and import gates remain unchanged
- full test suite, dashboard smoke, browser QA, public wording, public check, pilot readiness, diff hygiene, and `git diff --check`

## Delivery Sequence

1. Implement the profile context and tests.
2. Integrate the trust strip and status command preambles.
3. Add the event contract and deterministic read-only generator.
4. Add the derived Review Queue and review-resolution contract.
5. Integrate compact summaries into the existing five-page workflow.
6. Run desktop/mobile and profile-isolation verification.
7. Update README, roadmap, methodology, provenance, and operator documentation.

Each slice is committed only after focused and full verification. Generated data churn is never included by default.

## Acceptance Criteria

The design is complete when:

1. Every profile-specific UI page and core status view identifies the selected profile.
2. Source date, readiness time, snapshot identity, freshness, and counts all come from that profile.
3. No selected-profile read silently falls back to default data.
4. Comparable source-backed changes produce stable append-only event candidates.
5. The Review Queue is derived from unresolved events and prioritizes deterministic research tasks.
6. Public pages gain compact change context without becoming more fragmented.
7. Existing readiness, source-proof, no-fabrication, and research-only gates remain intact.
8. Tests and live browser checks prove desktop/mobile behavior and no regressions.

## Explicitly Deferred

- Hosted alerts and notifications
- Scheduled mutating refreshes
- Automatic source-data apply
- Automatic thesis changes
- Numerical investment scores
- Post-earnings price prediction
- Broker or account integrations

Those items require separate evidence, design approval, and operational safeguards.
