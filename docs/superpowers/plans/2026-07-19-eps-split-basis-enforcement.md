# EPS Split-Basis Enforcement Implementation Plan

1. Add failing quarterly-trend, focused-cohort, and backtest tests for the
   Companyfacts unverified split-basis sentinel.
2. Centralize the sentinel constant in the earnings evidence contract.
3. Filter sentinel EPS observations from Business Trend values/comparisons and
   retain an explicit partial or blocked reason without affecting Revenue.
4. Withhold sentinel target/prior-year EPS outcomes from backtest metrics and
   exclude events with no comparable target metric.
5. Update methodology, provenance, roadmap, continuation contract, and relevant
   UI/coverage contracts.
6. Run focused/full tests and every required product, release, pilot, and hygiene
   check; stage exact files, commit, push, update draft PR #113, and verify hosted
   CI on the exact pushed head.
