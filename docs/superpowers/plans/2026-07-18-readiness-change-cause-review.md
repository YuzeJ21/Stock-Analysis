# Readiness Change Cause Review Implementation Plan

**Goal:** Make every major saved-versus-proposed readiness transition semantically inspectable without writing artifacts or changing readiness decisions.

**Architecture:** Add a behavior-equivalent named-reason interface to `src.company_analysis_scope`, then add a pure change-transition review to `src.readiness_preview`. The existing preview builder supplies proposed metadata plus canonical fundamentals to the review after its single no-write readiness build.

## Task 1: Named company-scope reasons

- Add failing tests for each existing exclusion family, overlapping reasons, nonpositive-revenue inputs, and unchanged boolean results.
- Implement ordered named patterns and `company_dcf_exclusion_reasons`.
- Keep `COMPANY_DCF_EXCLUDED_TEXT_PATTERNS` and boolean helpers backward compatible.
- Run focused company-scope and readiness-engine tests.

## Task 2: Pure readiness transition review

- Add failing tests for added/removed rows, ready/partial/excluded set transitions, primary DCF reason counts, and unexplained exclusions.
- Add frozen change-review structures and pure set parsing.
- Integrate the review using proposed ticker metadata and canonical fundamentals without a second readiness build.
- Render counts under `Readiness Change Cause Review` with an explicit non-mutually-exclusive transition boundary.
- Prove the real command preserves a complete before/after byte fingerprint.

## Task 3: Documentation and verification

- Update ROADMAP, methodology, provenance, data strategy, continuation prompt, Make help, and contract tests.
- Run focused tests, full tests, dashboard and Personal Research render smoke, public wording/check, commercial beta/release, pilot readiness, diff hygiene, and whitespace checks.
- Stage exact code/test/docs/Make files only; run staged hygiene; commit and push only the feature branch.
- Update draft PR #113 with verified counts and keep it draft.

## Stop Rules

- Do not run `make readiness`.
- Do not change the exclusion decision or infer a reason from absent evidence.
- Do not write or stage CSV, JSON, reports, screenshots, timings, caches, or sample reports.
- Do not describe an exclusion as a negative research conclusion.
