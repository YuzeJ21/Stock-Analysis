# Canonical Quarterly Ledger Fail-Closed Plan

1. Add failing loader-to-packet and dashboard/cohort regression tests for a CSV
   containing one accepted and one rejected row.
2. Extend the quarterly trend packet with immutable canonical rejection
   evidence and a load-result-aware fail-closed builder.
3. Route both dashboard canonical consumers through that boundary and suppress
   accepted-subset cohort derivation when rejection evidence exists.
4. Show row-numbered rejection reasons only under Advanced quarterly evidence.
5. Update methodology, provenance, roadmap, continuation contract, and focused
   public/dashboard contract tests.
6. Run focused tests, the full suite, all product/release/pilot gates, PR-range
   and generated-artifact hygiene, exact staging checks, commit, push, update
   draft PR #113, and verify hosted CI at the exact head.
