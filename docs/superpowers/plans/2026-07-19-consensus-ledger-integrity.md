# Consensus Ledger Integrity Implementation Plan

1. Add failing tests for invalid existing ledgers, all linear-chain violations,
   non-leaf revisions, row-numbered errors, and unchanged bytes on failure.
2. Add failing tests for preview cutoff/input/ledger/commercial-mode receipt
   binding and required record arguments.
3. Separate validated existing-ledger loading from individually validated
   proposed-batch loading.
4. Implement semantic digests, full chain validation, leaf-only revision checks,
   normalized cutoff output, and deterministic preview receipts.
5. Require exact cutoff and receipt at programmatic and CLI/Make record boundaries;
   revalidate and recompute before append.
6. Update Make targets, methodology, provenance, operator/pilot docs, roadmap, and
   continuation contract without changing the source-review input contract.
7. Run focused/full tests and every required product, release, pilot, PR-range,
   and hygiene check; stage exact files, commit, push, update draft PR #113, and
   verify hosted CI on the exact head.
