# In-App Research-Record Authoring Design

## Status

The user approved the unified Company Workbench composer design and this written specification on 2026-07-22. The test-first implementation plan is recorded in `docs/superpowers/plans/2026-07-22-in-app-research-record-authoring.md`. No production implementation has started.

## Purpose

Company Workbench can read the selected profile's thesis journal, catalyst timeline, and research-outcome ledger, but recording those reviewed entries still requires command-line preparation. Priority 3 adds a command-line-free path for a researcher to create and revisit thesis, evidence, catalyst, and outcome records without changing any analytical result or treating a draft as evidence.

## Scope

Add one Company Workbench composer with an explicit `Validate -> Preview -> Confirm and save` flow for four user-facing record types:

1. Thesis, persisted through the existing research thesis journal.
2. Evidence, persisted through the existing research thesis journal with `entry_type=evidence`.
3. Catalyst, persisted through the existing catalyst evidence ledger.
4. Outcome, persisted through the existing research outcome review ledger.

The slice does not add a generic ledger, rich-text editor, attachment upload, automated research text, source discovery, source-rights approval, readiness promotion, forecast input, probability, score, ranking, recommendation, portfolio action, or transaction behavior.

## Chosen Architecture

Create a focused composition module, `src/research_record_authoring.py`, between the Streamlit page and the three existing persistence engines. The module owns authoring state, context binding, preview receipts, cross-ledger reference checks, and safe dispatch. It does not duplicate the validators or CSV append implementations in:

- `src/research_thesis_journal.py`;
- `src/catalyst_evidence_timeline.py`; or
- `src/research_outcome_review.py`.

The composition module exposes immutable draft, preview, and save-result contracts. It converts a user draft into the existing record dataclass, invokes the existing validator or preview function, and dispatches a confirmed record to exactly one existing append function.

The dashboard owns only widget collection and rendering. It must not open or write a ledger directly.

## Alternatives Rejected

### Separate Forms In Each Report Section

This would reduce the first implementation's orchestration code, but it would scatter confirmation rules across the thesis, Forward View, and outcome sections. Researchers would need to learn multiple save patterns, and stale-preview protection would be easy to implement inconsistently.

### One New Universal Research Ledger

A universal schema would appear simpler at the UI boundary, but it would duplicate validated domain contracts, require migration or dual reads, and create a new path that could disagree with the existing thesis, catalyst, and outcome engines.

### Direct Dashboard Calls To Existing Append Functions

This would reuse persistence but leave context binding, receipt validation, reference checks, and error normalization embedded in a large dashboard module. A small composition boundary is easier to test and prevents UI reruns from becoming persistence logic.

## User Workflow

The composer appears after the selected-ticker journal answer and research-learning card, before Advanced history. It is collapsed by default under the label `Add a reviewed research record`. Authoring is a research action, not technical evidence, but it stays below the primary company answer so it cannot displace usable and withheld findings.

1. The page displays the selected profile and ticker as locked scope.
2. The researcher chooses Thesis, Evidence, Catalyst, or Outcome.
3. The composer shows only fields used by that record's existing contract.
4. The researcher enters the claim, reviewer identity, effective or observation dates, and source provenance where required.
5. `Validate and preview` performs no write and returns either deterministic field errors or an exact preview.
6. A valid preview displays every persisted field, the destination ledger label, the append-only correction rule, and the research-only boundary.
7. The researcher checks `I reviewed this exact record and its source evidence` and selects `Confirm and save`.
8. Confirmation revalidates the preview receipt and current ledger before appending exactly one row.
9. The page reloads the selected-ticker state and shows the saved record identifier plus the correction path: append a revision or new record; never edit or delete history.

On phone, fields use one column, buttons use the available width, preview content wraps, and no raw dataframe is required to understand whether a record was saved or rejected.

## Record Contracts

### Shared Context

- `profile_key` and `ticker` come only from the active Company Workbench context and are not editable text fields.
- The reviewer must enter a non-empty identity. The UI does not infer identity from the local machine, Git configuration, or a future hosted account.
- A technical record identifier may be generated by the application. It carries no research meaning and cannot supply evidence content.
- The actual UTC preview timestamp is captured when validation creates the preview and is shown in that preview. Journal `recorded_at` uses that exact timestamp. The catalyst ledger has no separate recording field, so `retrieved_at` remains an explicit researcher input; outcome `reviewed_at` also remains an explicit researcher input. The UI never invents when a source was retrieved or an outcome was reviewed.
- User-entered effective, publication, retrieval, review, and observation timestamps must satisfy the existing temporal validators. Confirmation persists the exact previewed values and does not silently replace them.

### Thesis

- Uses `JournalEntry` with `entry_type=thesis`.
- Requires thesis identifier, summary, effective time, reviewer, and review date fields accepted by the existing contract.
- A revision must explicitly select the current thesis entry it supersedes. The UI cannot silently overwrite or infer a prior entry.

### Evidence

- Uses `JournalEntry` with `entry_type=evidence`.
- Requires an existing thesis identifier in the same profile/ticker scope, evidence direction, summary, source, source reference, source publication time, effective time, and reviewer.
- Supporting, conflicting, and contextual directions remain documentation categories only. They cannot change a forecast, readiness state, or conclusion automatically.

### Catalyst

- Uses `CatalystEvent` and the existing event-type and evidence-state vocabularies.
- Requires title, summary, effective, publication, and retrieval timestamps, exact source and reference, evidence state, and reviewer.
- `candidate_context_only` remains untrusted context. `supported` remains subject to independent exact-source rights and commercial field-scope checks when composed for Commercial Research.

### Outcome

- Uses `ResearchOutcome` and the existing outcome-state vocabulary.
- Requires an existing thesis entry in the same profile/ticker scope, observation window, reviewed time, summary, learning, source provenance, and reviewer.
- The composer rejects a missing or cross-profile/cross-ticker thesis reference even if the lower-level row schema is otherwise valid.
- No return, price-performance, skill grade, expected-return score, or company-ranking field is introduced.

## Preview Receipt And Concurrency Contract

A successful preview produces a session-only receipt containing deterministic hashes of:

- the normalized record kind and every prospective persisted field;
- the selected `profile_key` and normalized ticker;
- the resolved destination ledger identifier; and
- the destination ledger's current bytes, including the empty-ledger state.

The receipt and prospective record remain in `st.session_state` only. They are not written to CSV, JSON, a report, canonical data, readiness data, screenshots, or timing output.

Before confirmation, the composition layer must:

1. require the explicit confirmation boolean;
2. reconstruct and revalidate the exact prospective record;
3. confirm the active profile, ticker, and record kind still match;
4. confirm the draft digest still matches the preview;
5. confirm the destination ledger fingerprint is unchanged; and
6. rerun all existing duplicate, temporal, provenance, and append-only validation.

Any mismatch returns `preview_stale` and performs no write. The researcher must preview again. A successful save consumes the receipt so a rerun or double click cannot append the same record twice.

## Empty-Ledger And Persistence Behavior

- Loading a missing ledger returns the existing empty state and creates no file.
- Validation and preview create no directories or files.
- Confirmation may create only the one existing destination ledger when it is absent, using its established header and append function.
- The implementation and automated tests never append to repository production ledgers. Persistence tests use temporary paths.
- A failed or stale confirmation leaves all scoped files byte-identical.
- A successful confirmation appends one row and preserves every previous byte before the append boundary.
- Saved entries are never edited, deleted, compacted, reordered, or automatically superseded.

## Error And Recovery Behavior

- Field errors identify the exact rejected field without exposing a stack trace.
- An invalid existing ledger fails the entire corresponding record type closed; the composer does not skip malformed history or create a replacement ledger.
- A missing thesis reference blocks evidence and outcome confirmation.
- A duplicate technical identifier or semantic duplicate blocks confirmation.
- A changed selected company, profile, record type, draft, or ledger invalidates the preview.
- A filesystem failure reports that no save was confirmed and leaves the researcher on the preview/retry path.
- After a successful save, the UI displays the persisted identifier and reloads read-side state from disk rather than claiming success from session state alone.

## Independence And Safety Invariants

- Authoring is research-only and provides no investment advice.
- No direct buy/sell instruction, allocation, position sizing, account import, broker integration, order routing, auto-trading, or post-earnings price prediction is added.
- Saving one record type cannot append or promote another record type.
- No draft, preview, or saved record changes deterministic forecasts, DCF assumptions, scenarios, consensus, historical valuation, readiness, source rights, peer trust, backtesting, calibration, or numerical probability.
- Candidate context cannot become trusted evidence through authoring.
- Empty valuation, catalyst, outcome, consensus, and other ledgers remain visibly empty until an explicitly confirmed record is appended to that exact ledger.
- EPS split basis remains unverified without explicit primary proof.
- Q4 actuals still require an explicit SEC-filed Q4 table.
- Synthetic fixtures remain test-only.

## Test-First Implementation Slices

### Slice A — Pure Authoring Composition

Add failing unit tests for normalized drafts, locked profile/ticker scope, exact field mapping, cross-ledger thesis references, read-only previews, receipt contents, stale receipt rejection, and one-ledger-only dispatch. Implement only the pure composition and temporary-path persistence behavior needed to pass them.

### Slice B — Thesis And Evidence UI

Add failing dashboard-helper and render tests for the collapsed composer, locked scope, record-type-specific fields, preview errors, exact confirmation language, saved receipt, and correction path. Wire thesis and evidence through the composition module.

### Slice C — Catalyst And Outcome UI

Add failing tests for catalyst source/evidence-state fields, outcome observation/reference fields, candidate-context wording, cross-scope rejection, and no performance scoring. Wire catalyst and outcome through the same composer.

### Slice D — Workflow And Release Evidence

Add render and browser contracts covering fresh desktop and phone Company Workbench authoring states without writing production ledgers. Verify that the primary answer remains above the composer, Advanced evidence remains collapsed, and the complete Research Desk -> Discover -> Company Workbench -> Monitor path is unchanged.

Each slice uses a strict red-green-refactor cycle and may be committed only after its focused and required full verification passes.

## Verification

For each implementation slice, run focused tests for every changed module, then:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests -q`
- `make dashboard-smoke`
- `make research-dashboard-render-smoke`
- `make public-wording-check`
- `make public-check`
- `make linkedin-share-check`
- `make browser-qa-evidence`
- `make pilot-readiness-check TOP_N=10`
- `make commercial-beta-release-check`
- `make diff-hygiene-summary`
- `git diff --check`
- `make staged-hygiene-check` after exact staging
- `git diff --cached --check`

Fresh desktop and phone evidence must cover validation rejection, valid preview, stale preview, confirmed save against temporary ledgers, persisted reload, and the absence of horizontal overflow or hidden confirmation state. Screenshots or generated browser evidence stay ephemeral and are not staged.

## Acceptance Criteria

Priority 3 is complete only when direct current evidence proves all of the following:

1. A researcher can create and revisit all four record types in Company Workbench without command-line use.
2. Every record follows the exact `Validate -> Preview -> Confirm and save` state sequence.
3. Preview performs no write, explicit confirmation is required, and stale receipts fail closed.
4. Profile/ticker scope, reviewer identity, timestamps, provenance, duplicates, and thesis references are validated.
5. Exactly one established append-only ledger receives exactly one row after a successful confirmation.
6. Missing or invalid ledgers, invalid drafts, and failed confirmations create no content.
7. Saved results and append-only correction instructions are visible on desktop and phone.
8. No generated research content, fabricated evidence, recommendation, rank, score, return attribution, or transaction language is introduced.
9. Forecasts, probabilities, recommendations, readiness, source-rights decisions, and all independent evidence lanes remain byte-identical or behaviorally unchanged.
10. Focused tests, the full repository suite, every required release/hygiene gate, exact-file staging, pushed exact-head CI, and draft PR #113 all pass.
