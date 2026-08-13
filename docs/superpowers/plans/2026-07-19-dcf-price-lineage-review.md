# DCF Price Lineage Review Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend the existing stdout-only readiness preview with a fail-closed review of the exact latest canonical price row supporting each proposed DCF promotion.

**Architecture:** Add a pure `src.dcf_price_lineage` module that selects one latest usable row per proposed DCF promotion and independently evaluates selection, lineage, exact-source rights, and registered `prices` support. Integrate its frozen review result into `src.readiness_preview` after the existing in-memory readiness build. Keep the Make target, production readiness, price provider, canonical schema, valuation math, and no-write boundary unchanged.

**Tech Stack:** Python 3, frozen dataclasses, pandas, PyYAML-backed immutable source-rights registry, pytest, Make.

**Constraints:** Do not run `make readiness`; do not mutate or migrate canonical price data; do not write or stage CSV, JSON, reports, sample reports, screenshots, timing files, caches, or readiness artifacts; do not infer a provider from file names, adapters, dates, values, or history; do not split composite source identifiers; preserve technical DCF readiness independently from price selection, lineage, rights, registered field scope, reviewer approval, and rebuild authorization.

## Task 1: Pure DCF price-lineage contract

**Files:**

- Create `tests/test_dcf_price_lineage.py`
- Create `src/dcf_price_lineage.py`

- [ ] Add a test where `AAA` moves `dcf_ready=False -> True`, `BBB` remains ready, and `CCC` only promotes fundamentals; assert only `AAA` enters the DCF price review.
- [ ] Define test price rows where `AAA` has two valid dates and complete latest-row evidence: `source=approved_prices`, `source_ref=https://example.test/prices/AAA/2026-01-03`, and `retrieved_at=2026-01-03T23:00:00Z`.
- [ ] Define an exact rights record with `commercial_use=approved` and `supported_fields=("prices",)`; require `status="price_lineage_review_complete"`.
- [ ] Run `python3 -m pytest tests/test_dcf_price_lineage.py -q` and confirm collection fails because `src.dcf_price_lineage` does not exist.
- [ ] Add frozen `DcfPriceLineageEvidence` and `DcfPriceLineageReview` dataclasses with explicit aggregate counts, capped evidence rows, and `top_n`.
- [ ] Implement `review_dcf_price_lineage(saved, proposed, prices, *, rights_registry, top_n=20)` as a pure function.
- [ ] Normalize ticker text without mutating inputs; identify only false-to-true `dcf_ready` changes.
- [ ] Select valid rows using parsed `date`, numeric positive `close`, maximum date, and exactly one row at that date.
- [ ] Evaluate exact `source`, `source_ref`, and `retrieved_at`; call `commercial_eligibility` with the complete source string; require explicit registered `prices` support.
- [ ] Return `no_dcf_promotions`, `price_lineage_review_complete`, or `price_lineage_review_required` without changing either readiness frame.
- [ ] Run `python3 -m pytest tests/test_dcf_price_lineage.py -q` and require the initial success case to pass.

## Task 2: Fail-closed edge cases and independent counts

**Files:**

- Modify `tests/test_dcf_price_lineage.py`
- Modify `src/dcf_price_lineage.py`

- [ ] Add failing tests for a missing price row, invalid date, nonpositive close, and duplicate latest-date rows.
- [ ] Add failing tests for independently missing `source`, `source_ref`, and `retrieved_at`.
- [ ] Add cases for an unknown exact source, a composite exact source, unverified commercial rights, and an approved source whose registry omits `prices`.
- [ ] Assert a missing/ambiguous latest row yields rights `not_evaluated_missing_evidence` or `not_evaluated_ambiguous_evidence` rather than evaluating guessed data.
- [ ] Assert `TOP_N=1` caps evidence rows while all aggregate counts retain the full promotion population.
- [ ] Assert `top_n < 1` raises `ValueError`.
- [ ] Implement explicit blockers: `missing_latest_price_row`, `ambiguous_latest_price_row`, `missing_provenance:<field>`, `commercial_rights:<status>`, and `registered_price_scope_incomplete`.
- [ ] Count usable latest rows, ambiguous rows, lineage completeness, approved rights, registered price scope, exact sources, and rights statuses independently.
- [ ] Run `python3 -m pytest tests/test_dcf_price_lineage.py -q` and require all pure-contract tests to pass.

## Task 3: Integrate the audit into the one no-write preview

**Files:**

- Modify `tests/test_readiness_preview.py`
- Modify `src/readiness_preview.py`
- Modify `Makefile` only if its help text needs clarification

- [ ] Extend the integrated preview fixture with a proposed DCF promotion and a canonical `data/prices.csv` row carrying complete test provenance.
- [ ] Assert `build_ticker_readiness_report(..., write_outputs=False)` remains the only readiness build.
- [ ] Assert the attached price review is independent from `promotion_review` and contains the expected complete result.
- [ ] Add a missing-price-file integration case that produces `price_lineage_review_required` without writing a file.
- [ ] Require rendered output under `DCF Price Lineage Review` to show technical promotions, latest-row selection, lineage, rights, registered price scope, exact sources, rights statuses, and capped evidence rows.
- [ ] Require wording that file origin, observation date, and adapter availability are not provider provenance; the audit changes no readiness state and authorizes no rebuild.
- [ ] Run `python3 -m pytest tests/test_readiness_preview.py tests/test_dcf_price_lineage.py -q` and confirm the integration assertions fail before implementation.
- [ ] Add `dcf_price_lineage_review: DcfPriceLineageReview | None` to `ReadinessImpactPreview`.
- [ ] Load `data/prices.csv` read-only after a saved snapshot exists, normalize columns, and call `review_dcf_price_lineage(...)` with the existing saved/proposed frames and rights registry.
- [ ] Render the independent review after `Promotion Evidence Review`; retain all existing final no-write and research-only boundaries.
- [ ] Run the focused tests and require them to pass.

## Task 4: Prove no-write behavior on current repository data

**Files:**

- Modify `tests/test_readiness_preview.py` only if the integration manifest needs additional coverage

- [ ] Capture a byte-level manifest for tracked and untracked repository files before the command.
- [ ] Run `PYTHONDONTWRITEBYTECODE=1 make readiness-preview TOP_N=20`.
- [ ] Capture the same manifest afterward and assert it is identical.
- [ ] Record the live aggregate result without calling it current readiness or rebuild approval.
- [ ] Confirm no source provider is inferred for rows whose canonical evidence is absent.
- [ ] Run `git status --short` and verify no CSV, JSON, report, sample-report, screenshot, timing, cache, or bytecode artifact changed.

## Task 5: Durable methodology and continuation contract

**Files:**

- Modify `ROADMAP.md`
- Modify `docs/METHODOLOGY.md`
- Modify `docs/PROVENANCE_CONTRACT.md`
- Modify `docs/DATA_STRATEGY.md`
- Modify `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`
- Modify `tests/test_public_v1_release_docs.py` if contract assertions need expansion

- [ ] Record the exact latest-price selection rule and required row-level `source`, `source_ref`, and `retrieved_at` contract.
- [ ] Record that `as_of_date`, observation date, local file label, file modification time, adapter presence, and refresh warning text do not substitute for row-level provenance.
- [ ] Record independent technical DCF, price selection, lineage, rights, registered field scope, freshness, reviewer, and rebuild states.
- [ ] Add the implementation lineage anchor and current live no-write result to the continuation prompt without turning proposed counts into current product claims.
- [ ] Set the next executable local lane based on the new evidence; do not authorize canonical migration, source-rights edits, or `make readiness` without reviewed proof and explicit write approval.
- [ ] Run `python3 -m pytest tests/test_dcf_price_lineage.py tests/test_readiness_preview.py tests/test_public_v1_release_docs.py -q`.
- [ ] Run `git diff --check` and `make diff-hygiene-summary`.

## Task 6: Full verification, exact staging, commit, push, and PR evidence

- [ ] Run `python3 -m pytest tests -q`.
- [ ] Run `make dashboard-smoke`.
- [ ] Run the repository's six Personal Research render smoke targets.
- [ ] Run `make public-wording-check`.
- [ ] Run `make public-check`.
- [ ] Run `make commercial-beta-check`.
- [ ] Run `make commercial-beta-release-check`.
- [ ] Run `make pilot-readiness-check TOP_N=10` and preserve the truthful stale-readiness blocker.
- [ ] Run `make diff-hygiene-summary` and `git diff --check`.
- [ ] Review `git status --short`, `git diff --stat`, and exact changed paths.
- [ ] Stage only the intentional source, test, documentation, and Make paths; never use `git add -A`.
- [ ] Run `make staged-hygiene-check` and `git diff --cached --check`.
- [ ] Commit one coherent implementation/documentation slice.
- [ ] Push only `codex/personal-research-mode-mvp` and verify 0/0 alignment.
- [ ] Add a concise evidence comment to draft PR #113 with live counts, checks, boundaries, external-dependency classification, and exact next step.
- [ ] Verify PR #113 remains open and draft; do not merge or deploy.
