# Prospective Price Lineage Preservation Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Let one prospectively reviewed price row preserve an explicit durable source reference and retrieval timestamp through the existing normalize, validate, preview, and apply contracts without coupling technical OHLCV validity to commercial evidence.

**Architecture:** Widen the staged/canonical optional price metadata contract in `src.price_import_normalizer` and `src.data_update`. Normalization accepts explicit metadata only and never invents it. Validation normalizes retrieval timestamps and attaches an independent lineage summary to the existing technical result. Preview and later reviewed apply inherit the retained columns through the existing merge path.

**Tech Stack:** Python 3, pandas, argparse, pytest, Make.

**Constraints:** Do not run repository `price-normalize`, `price-apply`, `make readiness`, or any source refresh; use only temporary test fixtures; do not create or stage CSV, JSON, reports, sample reports, screenshots, timings, caches, or canonical data; do not generate defaults for `source_ref` or `retrieved_at`; do not make lineage completeness equivalent to rights approval, registered `prices` scope, reviewer approval, freshness, readiness, or apply authorization.

## Task 1: Normalizer preserves explicit lineage metadata

**Files:**

- Modify `tests/test_price_import_normalizer.py`
- Modify `src/price_import_normalizer.py`

- [ ] Add a failing test that passes `source_ref="https://example.test/prices/NVDA/2026-01-02"` and `retrieved_at="2026-01-03T23:00:00Z"` into `normalize_price_imports(...)` and asserts both exact fields exist in the staged temporary CSV.
- [ ] Add a test that omits both arguments and asserts both columns are present but blank; normalization time, file time, observation date, and `as_of_date` must not appear in either field.
- [ ] Run `python3 -m pytest tests/test_price_import_normalizer.py -q` and confirm the new signature/columns fail before implementation.
- [ ] Add `source_ref` and `retrieved_at` to `STAGED_PRICE_COLUMNS` after `source`.
- [ ] Pass explicit values through `_normalize_one_file(...)` and `normalize_price_imports(...)`; default both to `None`/blank.
- [ ] Add CLI `--source-ref` and `--retrieved-at` arguments and pass them unchanged into normalization.
- [ ] Preserve existing date/ticker/duplicate/invalid-row behavior and existing output ordering.
- [ ] Run the focused normalizer tests and require them to pass.

## Task 2: Validation reports independent lineage completeness

**Files:**

- Modify `tests/test_data_update.py`
- Modify `src/data_update.py`

- [ ] Extend the temporary import fixture with `source_ref` and `retrieved_at` values for valid rows.
- [ ] Add assertions that `validate_price_imports(...)` retains both fields in `valid_frame` and returns `lineage_status="lineage_complete"`, complete row count 2, review-required row count 0, and no missing lineage fields.
- [ ] Add a separate technically valid fixture with missing source reference and invalid retrieval timestamp; require technical status to remain valid or valid-with-warnings while lineage is `lineage_review_required`.
- [ ] Run the focused validation tests and confirm the summary assertions fail before implementation.
- [ ] Add `source_ref` and `retrieved_at` to optional/output price import columns.
- [ ] Normalize nonblank retrieval timestamps to UTC ISO-8601 and blank invalid values without inventing current time.
- [ ] Compute lineage completeness over retained valid rows using exact nonblank `source`, nonblank `source_ref`, and parseable `retrieved_at`.
- [ ] Return `lineage_status`, `lineage_complete_rows`, `lineage_review_required_rows`, and sorted `lineage_missing_fields` for valid, invalid, and missing-file paths.
- [ ] Add a concise warning when otherwise valid rows require lineage review; do not change the technical row count or reject the row.
- [ ] Run focused data-update tests and require them to pass.

## Task 3: Preview and temporary apply preserve lineage

**Files:**

- Modify `tests/test_data_update.py`
- Modify `src/data_update.py` only if the existing merge logic needs correction

- [ ] Assert `preview_price_import_merge(...)` returns the same lineage summary as validation and still reports existing new/updated/unchanged counts.
- [ ] In the existing temporary apply test, assert updated and new NVDA rows preserve exact `source_ref` and normalized `retrieved_at` values.
- [ ] Assert the unrelated MSFT canonical row remains present and its missing new fields remain empty.
- [ ] Run `python3 -m pytest tests/test_data_update.py -q` and confirm any preservation gap fails before correction.
- [ ] If needed, widen `PRICE_IMPORT_OUTPUT_COLUMNS` and retain optional columns through canonical reindex/merge; do not change merge keys or backup/no-delete behavior.
- [ ] Run focused normalizer/data-update tests and require them to pass.

## Task 4: Safe CLI and Make routing

**Files:**

- Modify `Makefile`
- Modify `tests/test_launchers.py`
- Modify public or operator docs only where the reviewed command contract is described

- [ ] Add failing launcher assertions that `price-normalize` conditionally passes quoted `--source-ref "$(SOURCE_REF)"` and `--retrieved-at "$(RETRIEVED_AT)"` only when supplied.
- [ ] Update Make help with one reviewed example containing `SOURCE`, `SOURCE_REF`, and `RETRIEVED_AT`; keep the default example valid for local research.
- [ ] Keep user-supplied values quoted and never echo credentials; the fields are evidence identifiers/timestamps, not secrets.
- [ ] Run focused launcher tests and `make public-wording-check`.

## Task 5: Durable contracts and current next step

**Files:**

- Modify `ROADMAP.md`
- Modify `docs/METHODOLOGY.md`
- Modify `docs/PROVENANCE_CONTRACT.md`
- Modify `docs/DATA_STRATEGY.md`
- Modify `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`
- Modify documentation contract tests as needed

- [ ] Record that the staged path can now preserve prospective lineage but current canonical history remains unchanged and unproven.
- [ ] Record that missing lineage does not invalidate technical local-research rows, while complete lineage still does not establish rights, registered field scope, reviewer approval, or apply authorization.
- [ ] Add the design/plan lineage anchor and exact next external unblock condition to the continuation prompt.
- [ ] Keep the current 146-row DCF audit result unchanged; no new canonical row exists from this code slice.
- [ ] Run focused documentation/launcher/normalizer/data-update tests, `git diff --check`, and `make diff-hygiene-summary`.

## Task 6: Full verification, exact staging, commit, push, and PR update

- [ ] Run `python3 -m pytest tests -q`.
- [ ] Run `make dashboard-smoke`.
- [ ] Run `make research-dashboard-render-smoke`.
- [ ] Run `make public-wording-check`.
- [ ] Run `make public-check`.
- [ ] Run `make commercial-beta-check`.
- [ ] Run `make commercial-beta-release-check`.
- [ ] Run `make pilot-readiness-check TOP_N=10` and preserve the stale-readiness blocker.
- [ ] Run `make diff-hygiene-summary` and `git diff --check`.
- [ ] Verify no repository price-normalize/apply or generated-data command ran and no generated artifact changed.
- [ ] Stage only the exact source, test, Make, and documentation paths; never use `git add -A`.
- [ ] Run `make staged-hygiene-check` and `git diff --cached --check`.
- [ ] Commit one coherent implementation/documentation slice.
- [ ] Push only `codex/personal-research-mode-mvp` and verify 0/0 alignment.
- [ ] Update draft PR #113 with verified behavior, test counts, artifact boundary, remaining rights/source requirement, and next executable step.
- [ ] Verify PR #113 remains open and draft; do not merge or deploy.
