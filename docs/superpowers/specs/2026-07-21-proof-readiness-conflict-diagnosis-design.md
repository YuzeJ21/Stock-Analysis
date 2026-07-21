# Proof-Readiness Conflict Diagnosis Design

**Date:** 2026-07-21

**Status:** Approved direction; written specification awaiting final review

## Purpose

Make proof-readiness reconciliation explain two independent questions without weakening fail-closed readiness:

1. Does a historical batch outcome apply to this exact ticker and lane?
2. What observable current input prevents the lane from being ready now?

The reconciliation remains read-only. Current saved readiness remains authoritative. Historical proof never restores canonical data, promotes readiness, rewrites proof history, or proves current source rights, field scope, provenance, payload truth, commercial use, hosting, reviewer adoption, or market validation.

## Current Evidence

The current saved snapshot contains 21,246 reconciliation rows across 3,541 tickers and six canonical lanes. It reports 3,506 `historical_supported_currently_blocked` rows:

- fundamentals: 2,615
- share count: 862
- DCF: 20
- price: 6
- peer mapping: 3

The fundamentals audit found:

- 2,607 conflicts whose latest proof explicitly names the ticker in `changed_tickers`;
- 8 conflicts whose ticker appears only in batch scope and is not named in `changed_tickers`;
- 2,605 conflicts with no current canonical fundamentals row;
- 10 conflicts with a current SEC Companyfacts row that lacks one or more required fundamentals fields.

Across all conflict lanes, 44 rows are scope-only or otherwise lack explicit ticker-change attribution: 8 fundamentals, 15 DCF, and 21 share-count rows. A supporting batch outcome cannot truthfully establish ticker-level support for those rows.

The historical ledger records batch-level outcomes and narrative notes. It does not preserve a structured per-ticker, per-field payload snapshot or a structured exact-source rights/scope decision. The system therefore cannot reliably determine whether a genuine historical/current divergence resulted from data removal, a changed readiness contract, a changed source-rights decision, a changed field-scope decision, or another historical event. It must state that limitation instead of guessing.

Snapshot counts are audit evidence only. They are not durable coverage claims and may change when the saved inputs change.

## Design Principles

1. **Two independent axes.** Historical applicability and current blocking evidence must never be collapsed into one label.
2. **Explicit ticker attribution.** A batch-level supporting outcome applies to a ticker only when the normalized ticker appears in the proof row's structured `changed_tickers` field.
3. **Current state is authoritative.** Current readiness and current blocker fields come only from the saved readiness inputs.
4. **No narrative inference.** `notes`, `scope`, `command_run`, and other free text may be displayed as historical context but cannot establish source identity, rights, supported fields, payload truth, or a root cause.
5. **Fail closed on malformed evidence.** Missing, placeholder, malformed, ambiguous, or out-of-universe ticker-change evidence is not supporting ticker-level proof.
6. **No writes.** The command and dashboard integration do not change canonical data, proof ledgers, readiness reports, generated artifacts, or external services.
7. **Advanced evidence only.** Detailed reconciliation remains in the CLI/JSON contract and Advanced Proof History. The four primary research routes remain unchanged.

## Historical Applicability Contract

Every applicable historical proof receives one `proof_applicability` value:

- `explicit_ticker_change`: the proof has a valid review date, an explicitly supporting outcome, and the ticker is listed in normalized `changed_tickers`.
- `scope_only_not_supported`: the ticker is in the batch `tickers` scope but not in a nonempty normalized `changed_tickers` set.
- `missing_ticker_change_detail`: the proof is otherwise applicable by lane and scope, but `changed_tickers` is blank, placeholder, malformed, or a reviewed no-change value.
- `non_supporting_outcome`: the latest proof outcome is not one of `supported`, `auto_supported`, or `human_reviewed_supported`.
- `malformed_review_date`: the latest proof date is invalid and cannot support.
- `no_applicable_proof`: no valid ticker-and-lane proof row exists.

Only `explicit_ticker_change` is ticker-level supporting evidence.

The existing `tickers` field remains the batch scope used to locate potentially applicable proof rows. It does not become proof of a ticker-level change. `changed_tickers` is normalized using the same comma/semicolon token rules and current-universe validation as batch scope.

When multiple proof rows apply, the existing deterministic latest-proof ordering remains: valid ISO review dates outrank malformed dates, later valid dates outrank earlier dates, and append order breaks exact-date ties. Applicability is evaluated after selecting the latest proof. The system does not search backward for an older supporting row when the latest row is non-supporting or malformed.

## Current Blocker Contract

Every reconciliation row receives structured current-state fields:

- `current_blocker_code`
- `current_blocker_fields`
- `current_blocker_detail`
- `next_safe_review`

The blocker is derived only from current saved readiness inputs.

### Fundamentals

- `current_canonical_row_missing` when `fundamentals_ready=false` and no current canonical fundamentals row exists.
- `current_required_fields_missing` when a current canonical row exists and the current DCF readiness row names missing required fields.
- `current_readiness_input_unavailable` when the required current input cannot be loaded or interpreted.
- `none` when current readiness is true.

`current_blocker_fields` contains only canonical current field names in deterministic order: `free_cash_flow`, `shares_outstanding`, `revenue`, `fcf_margin`, and `price` when applicable. Fundamentals diagnosis uses the current canonical fundamentals row to distinguish absent payload from incomplete payload; it does not claim that price alone is a fundamentals field.

### DCF and Share Count

- `current_required_fields_missing` from current `missing_dcf_fields` when the DCF input is available.
- `current_canonical_row_missing` when the current canonical fundamentals row is absent and the required DCF fields are missing.
- `current_readiness_input_unavailable` when the DCF readiness input is unavailable or malformed.
- `none` when the authoritative lane field is true.

Share-count diagnosis reports `shares_outstanding` only. It does not turn other missing DCF fields into share-count blockers.

### Price

- `current_price_missing` when `price_ready=false`.
- `current_readiness_input_unavailable` when current ticker readiness is unavailable or malformed.
- `none` when `price_ready=true`.

The diagnosis does not infer a provider, source, refresh failure, or source-rights status.

### Peer Mapping and Peer Valuation Inputs

- `current_peer_mapping_missing` when `peer_ready=false` for peer mapping.
- `current_peer_valuation_inputs_missing` when `peer_valuation_ready=false`.
- `current_readiness_input_unavailable` when the required peer input is unavailable or malformed.
- `none` when the authoritative lane field is true.

The diagnosis does not fabricate peers, comparability, valuation anchors, or source proof.

## Historical Evidence-Limitation Contract

Every row with a historical proof also receives:

- `historical_payload_status`
- `historical_evidence_limit`

The current ledger does not contain a structured per-ticker/per-field payload snapshot, so existing proof rows use:

- `historical_payload_status=structured_payload_not_recorded`
- `historical_evidence_limit=Historical batch proof cannot distinguish payload removal, readiness-contract change, source-rights change, field-scope change, or another historical cause.`

This limitation remains present even when `proof_applicability=explicit_ticker_change`. Free-text notes cannot upgrade it.

Future structured proof rows may introduce a versioned per-ticker/per-field evidence contract in a separate design. This slice does not modify the append-only proof schema or retroactively manufacture structured evidence.

## Reconciliation State Changes

The existing state names remain stable for consumers, but ticker-level support is recalculated from `proof_applicability`:

- `current_supported_with_matching_proof` requires current readiness true and `explicit_ticker_change`.
- `historical_supported_currently_blocked` requires current readiness false and `explicit_ticker_change`.
- `current_ready_proof_not_supporting` includes current-ready rows whose latest proof is scope-only, missing ticker-change detail, malformed, non-supporting, or absent.
- `currently_blocked_with_non_supporting_history` includes current-blocked rows with a proof that is scope-only, missing ticker-change detail, malformed, or non-supporting.
- `no_proof_record` and `not_applicable` retain their existing meanings.

This reclassification removes false ticker-level historical-support claims. It does not make any current lane ready.

## Interfaces

### Python

`ProofReadinessReconciliationRow` gains the following immutable fields:

- `proof_applicability: str`
- `current_blocker_code: str`
- `current_blocker_fields: tuple[str, ...]`
- `current_blocker_detail: str`
- `next_safe_review: str`
- `historical_payload_status: str`
- `historical_evidence_limit: str`

`build_proof_readiness_reconciliation` additionally accepts the current canonical fundamentals frame. Loading remains tolerant of missing or malformed files and fails closed to explicit unavailable states.

### CLI and JSON

`make proof-readiness-reconciliation TOP_N=20` remains the only command. No writing target is added.

Text output adds:

- applicability counts;
- current blocker counts;
- `Proof applicability`, `Current blocker`, and `Next safe review` columns for displayed rows;
- a boundary stating that blocker diagnosis describes current observable inputs and not the historical cause.

JSON adds the new row fields plus top-level `proof_applicability_counts` and `current_blocker_counts`. Existing keys remain available.

### Advanced Proof History

The global reconciliation card continues to show the historical-support/current-readiness conflict count. Its body adds the largest current blocker category and explicitly distinguishes current blocker evidence from historical cause.

For a selected ticker, the second card names:

- canonical conflicting lanes;
- proof applicability;
- current blocker fields or blocker code;
- the safe next review.

Cards expose no mutation command. Raw ledger details remain collapsed below the cards. Research Desk, Discover, Company Workbench, and Monitor do not receive this technical detail.

## Safe Next-Review Rules

Next-review text is deterministic and non-writing:

- scope-only or missing change detail: review the proof row; do not reuse it as ticker-level support;
- canonical fundamentals row missing: obtain and review a permitted source payload for the exact ticker before any import or readiness rebuild;
- required fields missing: review the named missing fields through the existing source-review and preview-first workflow;
- price missing: inspect the exact ticker's current price evidence without inferring a provider;
- peer mapping missing: review a source-backed relationship through the existing peer evidence contract;
- peer valuation inputs missing: review current peer valuation inputs independently from mapping readiness;
- unavailable input: restore or inspect the current saved input before drawing a conclusion.

The reconciliation does not run any suggested workflow.

## Error Handling

- Missing current ticker readiness returns an unavailable summary and no inferred rows.
- Missing DCF, peer, or canonical fundamentals inputs produce lane-specific unavailable diagnoses without blocking independent lanes.
- Duplicate ticker tokens are deduplicated deterministically.
- Placeholder `changed_tickers` values such as `-`, `none`, `n/a`, `not available`, and `unknown` do not support.
- Unknown proof outcomes fail closed as `non_supporting_outcome`.
- Malformed review dates remain non-supporting and cannot outrank a valid dated proof.
- Unknown missing-field tokens are excluded from canonical blocker fields and surfaced only in a fail-closed detail message.
- No free text is parsed for source identity, rights, field scope, or historical root cause.

## Testing Strategy

Tests must be written and observed failing before production changes.

Focused unit coverage will prove:

1. A scope-only ticker with a supporting batch outcome is not ticker-level supported.
2. An explicitly changed ticker retains historical-support conflict classification when current readiness is false.
3. Placeholder or no-change `changed_tickers` fails closed.
4. Latest-proof ordering remains deterministic and does not fall back to older support.
5. A missing canonical fundamentals row produces `current_canonical_row_missing`.
6. An incomplete canonical fundamentals row produces exact ordered missing fields.
7. Share-count diagnosis reports only `shares_outstanding`.
8. Price and peer lanes retain independent blocker diagnoses.
9. Missing current inputs affect only their dependent lanes.
10. JSON and text output expose both axes and retain existing keys.
11. Free-text source claims cannot upgrade the historical evidence limitation.
12. The command remains filesystem read-only.

Dashboard tests will prove:

1. The global Advanced Proof History card distinguishes current blockers from historical causes.
2. A selected ticker card shows only its own lanes and blocker evidence.
3. Cards contain no command.
4. The four primary research routes remain unchanged.
5. All six Research Mode render contracts still pass.

Full release verification remains:

- focused changed-module tests;
- `python3 -m pytest tests -q`;
- `make dashboard-smoke`;
- `make research-dashboard-render-smoke`;
- `make public-wording-check`;
- `make commercial-beta-check`;
- `make public-check`;
- `make commercial-beta-release-check`;
- `make pilot-readiness-check TOP_N=10`;
- `make diff-hygiene-summary`;
- `git diff --check`;
- `make staged-hygiene-check` and `git diff --cached --check` after exact staging;
- exact-head GitHub CI after pushing.

## Documentation and Delivery

After implementation verification:

- update `ROADMAP.md` with the implemented applicability and diagnosis boundary;
- update `docs/OPERATOR_GUIDE.md` with the two-axis interpretation;
- update `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md` with the new safe continuation rule;
- update the existing release-document contract tests;
- update draft PR #113 with current-snapshot counts and verification evidence;
- stage exact product/code/docs/test files only;
- preserve all generated CSV, JSON, report, sample-report, screenshot, timing, and canonical-data churn as unstaged unless separately reviewed and approved;
- push only `codex/personal-research-mode-mvp` and keep PR #113 draft.

## Non-Goals

This slice does not:

- rebuild readiness;
- restore or delete canonical rows;
- edit historical proof rows;
- infer historical causes from narrative text;
- approve yfinance or another source for commercial use;
- add source rights or supported fields;
- fetch a provider or run a broad refresh;
- create per-field historical evidence retroactively;
- activate Earnings Nowcast, consensus, calibration, valuation, catalysts, outcomes, or backtesting;
- change Q4 or EPS split-basis boundaries;
- change the primary research workflow;
- prove hosting, authentication, external reviewer adoption, operating readiness, commercial demand, or product-market fit.

## Future Maturity Stage

Design a versioned append-only per-ticker/per-field proof record that preserves exact source ID, durable reference, as-of date, retrieval time, reviewed field scope, rights decision reference, payload digest, readiness contract version, and reviewer decision. Adoption must be prospective. Existing narrative batch proof remains historical audit context and must never be silently upgraded.
