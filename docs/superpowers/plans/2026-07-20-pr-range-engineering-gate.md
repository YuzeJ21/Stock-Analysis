# Pull-Request Range Engineering Gate Plan

1. Add failing workflow and hygiene tests for full history, explicit event SHAs,
   range commands, and a generated file committed between two temporary SHAs.
2. Add commit-resolution and range-status loading to the existing read-only
   hygiene script, with a generated-churn fail result.
3. Add a Make target accepting explicit `BASE_SHA` and `HEAD_SHA`.
4. Update the workflow to check out exact head with full history and run both
   hygiene and whitespace against `BASE...HEAD`.
5. Update roadmap, methodology/provenance where relevant, continuation contract,
   and focused launcher/workflow contracts.
6. Run focused/full tests and all product/release/pilot/local/range/staged hygiene
   checks; commit, push, update draft PR #113, and require exact-head hosted CI.
