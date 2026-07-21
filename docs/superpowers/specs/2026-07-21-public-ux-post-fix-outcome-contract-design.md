# Public UX Post-Fix Outcome Contract Design

## Problem

The completed phone-width Single-Stock Report review is recorded as `resolved_post_fix` so the audit retains the fact that a defect was observed, corrected, and recaptured. The public UX status parser currently treats every classification except literal `resolved` and `pending` as a problem. That makes a fully completed ten-row review report `review_limited` and causes project status to understate public UX maturity.

This is an evidence-state classification defect. It does not affect research readiness, data freshness, source rights, forecasts, or the rendered product workflow.

## Decision

Add `resolved_post_fix` as a second explicit successful public UX review outcome.

- `resolved` means the reviewed route and viewport passed without a recorded corrective cycle.
- `resolved_post_fix` means an observed issue was corrected and fresh route/viewport evidence passed.
- Both outcomes satisfy the public UX share-review gate.
- Their raw classification counts remain separate so the audit history is not flattened.
- Project-status evidence sums both successful outcomes when reporting the resolved-row numerator.
- `pending` remains incomplete.
- `intentionally_deferred`, `environment_limited`, `skipped`, `blocked_with_evidence`, and every unknown classification remain fail-closed problem outcomes.

The implementation must use an explicit successful-outcome set. It must not use prefix matching such as `classification.startswith("resolved")`, because that would silently accept misspelled or invented classifications.

## Components

### Public UX review checklist

`src/public_ux_review_checklist.py` owns the outcome vocabulary and the review-note status decision. It will expose the two successful outcomes through one explicit constant, include `resolved_post_fix` in the rendered review instructions, and use the constant when separating successful rows from problem rows.

The status payload continues to preserve raw `classification_counts`. A ten-row review with nine `resolved` rows and one `resolved_post_fix` row must return:

- `status=review_complete`
- `share_review_gate=share_review_ready`
- `pending_rows=0`
- `problem_rows=[]`
- raw counts of `resolved: 9` and `resolved_post_fix: 1`

### Project status

`src/project_status.py` will calculate the resolved-row numerator as the sum of the two explicit successful outcomes. The resulting evidence must say `10/10 public desktop/mobile review rows resolved` for the verified audit while retaining the raw distinction in the underlying review-note status.

### Documentation

`ROADMAP.md`, `docs/DASHBOARD_QA.md`, and the commercial-beta continuation contract will state that the verified ten-row desktop/phone audit is `share_review_ready`, with one row resolved after a corrective recapture. This is local screenshot-based product QA only; it does not establish hosted behavior, accessibility conformance, external reviewer validation, data freshness, or market validation.

## Test Strategy

Use a strict red-green cycle.

1. Add a public UX review-note regression test with nine `resolved` rows and one `resolved_post_fix` row. Verify it fails because the current parser returns `review_limited`.
2. Add a project-status regression assertion that successful outcomes are summed to `10/10`.
3. Implement the smallest explicit-outcome-set change.
4. Run focused tests for the checklist and project-status modules.
5. Run the full repository, dashboard, render, public, commercial-beta, release, pilot, and hygiene gates.

Unknown classifications must remain covered by the existing fail-closed problem-row behavior.

## Boundaries

- Do not edit or stage the `/tmp` review notes or screenshots.
- Do not run `make readiness` or generate readiness, CSV, JSON, report, sample-report, screenshot, or timing artifacts.
- Do not change research readiness, source evidence, forecasts, valuation, consensus, catalysts, outcomes, backtesting, or calibration.
- Keep PR #113 open and draft.
- Stage only the exact product, test, and documentation files required by this slice.

## Acceptance Criteria

1. The existing verified notes file reports `review_complete` and `share_review_ready` without being edited.
2. Raw counts remain `resolved: 9` and `resolved_post_fix: 1`.
3. Project status reports `10/10` resolved public UX rows.
4. Deferred, limited, blocked, skipped, unknown, and pending states continue to fail closed.
5. Focused and full verification pass.
6. No generated artifact enters the working tree, commit range, or staging area.
