# Readiness Promotion Evidence Review Implementation Plan

**Goal:** Extend the existing stdout-only readiness preview with a fail-closed explanation of proposed fundamentals and DCF promotions by exact source, provenance, commercial-rights status, and registered field scope.

**Architecture:** Add pure promotion-review structures and comparison helpers to `src.readiness_preview`. The integrated builder reuses the already computed in-memory readiness frames, reads canonical fundamentals and the checked-in immutable source-rights registry, and attaches an independent evidence review to the technical impact preview. The existing Make command, no-write behavior, and rebuild boundary remain unchanged.

**Constraints:** Do not run `make readiness`; do not add an output path or file format; do not write or stage CSV, JSON, reports, screenshots, timings, caches, or readiness artifacts; do not split composite source identifiers or infer rights/field support; preserve technical readiness independently from commercial/evidence review.

## Task 1: Pure promotion-evidence contract

**Files:**

- Modify `tests/test_readiness_preview.py`
- Modify `src/readiness_preview.py`

1. Add failing tests for false-to-true fundamentals/DCF selection, exact source-rights decisions, required field support, provenance completeness, duplicate ticker failure, and `TOP_N` capping.
2. Run `python3 -m pytest tests/test_readiness_preview.py -q` and confirm the new contract fails before implementation.
3. Add frozen `ReadinessPromotionEvidence` and `ReadinessPromotionReview` structures.
4. Implement a pure `review_readiness_promotions(...)` helper that:
   - indexes saved/proposed readiness deterministically;
   - identifies unique fundamentals/DCF promotions only;
   - fails closed on duplicate/missing canonical fundamentals evidence;
   - evaluates the complete source value with `commercial_eligibility`;
   - checks source, as-of date, SEC accession/source reference, and registered required-field coverage;
   - returns counts plus capped rows without mutating inputs.
5. Run the focused tests and keep the stable readiness comparison behavior unchanged.

## Task 2: Integrated no-write preview and operator wording

**Files:**

- Modify `tests/test_readiness_preview.py`
- Modify `src/readiness_preview.py`
- Modify `tests/test_public_v1_release_docs.py`
- Modify `Makefile` help text only if the existing description no longer explains the expanded review.

1. Add failing integration assertions that the preview builder passes `write_outputs=False`, loads the checked-in registry, attaches the review, and preserves the complete filesystem manifest.
2. Require output to distinguish technical promotions from provenance, rights, field-scope, DCF price-source, and rebuild decisions.
3. Integrate the review after the one in-memory production readiness build; do not invoke a second build.
4. Render total and capped evidence summaries under `Promotion Evidence Review`.
5. Prove `make readiness-preview TOP_N=20` leaves a before/after file fingerprint unchanged.
6. Run `python3 -m pytest tests/test_readiness_preview.py tests/test_public_v1_release_docs.py -q`.

## Task 3: Durable methodology and continuation contract

**Files:**

- Modify `ROADMAP.md`
- Modify `docs/METHODOLOGY.md`
- Modify `docs/PROVENANCE_CONTRACT.md`
- Modify `docs/DATA_STRATEGY.md`
- Modify `docs/internal/COMMERCIAL_RESEARCH_BETA_CONTINUATION_GOAL_PROMPT.md`
- Modify documentation contract tests as required

1. Record that proposed technical promotions do not establish provenance, field support, commercial rights, complete DCF price provenance, or rebuild approval.
2. Record the exact-source fail-closed rule and the current review result without turning in-memory counts into current product claims.
3. Keep the continuation prompt's next step executable and no-write.
4. Run focused documentation and preview tests, `git diff --check`, and `make diff-hygiene-summary`.

## Task 4: Full verification, commit, push, and PR evidence

1. Run:
   - `python3 -m pytest tests -q`
   - `make dashboard-smoke`
   - the repository's Personal Research render smoke target
   - `make public-wording-check`
   - `make public-check`
   - `make commercial-beta-check`
   - `make commercial-beta-release-check`
   - `make pilot-readiness-check TOP_N=10`
   - `make diff-hygiene-summary`
   - `git diff --check`
2. Confirm the pilot remains blocked by stale saved readiness and no generated artifact is tracked or staged.
3. Stage exact code/test/docs/Make files only and run `make staged-hygiene-check`.
4. Commit the coherent implementation and documentation slice.
5. Push only `codex/personal-research-mode-mvp`.
6. Update draft PR #113 with verified counts, checks, boundaries, external dependency classification, and the next executable step. Keep it draft; do not merge or deploy.
