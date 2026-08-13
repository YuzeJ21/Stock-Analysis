# Public Mobile Evidence Handoff Design

## Problem

Fresh desktop and 390x844 browser evidence for the five-page public workflow shows healthy reflow, no horizontal overflow, no tracebacks, and answer-first content on all ten page/viewport combinations. Home and Stock Selector expose their primary actions in the first phone viewport. Data Health and Proof History correctly use their first screens for lane and evidence review.

Single-Stock Report is the exception. Its first phone viewport preserves the selected ticker, usable evidence, and withheld evidence, but the existing **Open Data Health** handoff begins below the viewport. Desktop already shows the same handoff correctly.

## Decision

Keep the current information and fail-closed reading order:

1. Selected ticker
2. Use now
3. Still withheld
4. Evidence handoff

Do not move the action ahead of withheld evidence and do not remove methodology or boundary text. On viewports at or below 640px:

- reduce only the vertical gap and padding inside `.public-ticker-summary`;
- place `.public-primary-action` first inside the final `.public-ticker-action` block;
- keep the explanatory next-action sentence and stop rule immediately after the link;
- leave desktop layout and all readiness, evidence, source, forecast, and research states unchanged.

## Alternatives Rejected

- **Move the full action block ahead of Still withheld:** exposes the link earlier but weakens the required fail-closed sequence.
- **Hide context or stop-rule copy on phone:** saves space by removing evidence-boundary information.
- **Add new calls to action to Data Health and Proof History:** invents workflow pressure on pages whose job is to review lane state and evidence.

## Acceptance Evidence

- A source contract proves the phone-only rules exist and desktop grid rules remain unchanged.
- A rendered 390x844 Single-Stock Report check proves:
  - selected ticker, Use now, and Still withheld appear before Open Data Health in document order;
  - Open Data Health is fully inside the first viewport;
  - no horizontal overflow or traceback appears;
  - Advanced sections remain collapsed.
- Existing public and Personal Research render tests remain green.
- Full tests, release gates, pilot check, PR-range hygiene, staged hygiene, and exact-head GitHub CI pass.

## Boundaries

This is a public-workflow usability correction only. It does not refresh or rebuild readiness, change source rights, activate blocked evidence, modify canonical data, create forecasts or probabilities, add a provider or hosted service, or generate/stage CSV, JSON, report, sample-report, screenshot, timing, readiness, canonical-data, or manual-review churn.
