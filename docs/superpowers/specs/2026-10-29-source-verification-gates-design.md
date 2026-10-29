# Source Verification Gates Design

## Intent

Give a local reviewer reproducible evidence for two held decisions: whether the inherited release baseline is byte-identical to its inventory, and whether a dated pair of U.S. listing directory receipts is internally consistent. Neither check grants source rights, declares a complete U.S. company universe, or changes canonical data.

## Approaches

The chosen approach is two small read-only commands with synthetic regression tests. A single combined command would blur independent release and listing decisions. Transferring the held feature branch's writer would expose a canonical import path before identity and rights review. Existing ignored receipts and disposition files stay local inputs; the committed code and tests contain only synthetic records.

## Release baseline audit

`src/release_baseline_audit.py` accepts an inventory TSV, a disposition TSV, an exact reviewed-history TSV, a repository root, and a base Git ref. It verifies the exact tracked path set under `data/`, `outputs/`, and `docs/assets/`, per-path SHA-256 values, strict unique relative paths and schema, allowed conservative dispositions, and every changed path/blob pair across `base..HEAD` commits even if the path is later deleted or the blob already existed in the base. It rejects any pair absent from the reviewed-history list and any rights-registry change. It reports hold counts and failures in JSON. A successful integrity audit still returns a held distribution state; review classifications cannot turn it into rights clearance.

## Listing receipt audit

`src/us_listing_receipt_audit.py` accepts a saved local snapshot directory only. It validates the exact two official Nasdaq Trader directory receipt identities, file hashes, observation and modification times, source creation times, CSV schemas, flags, unique symbols, known venue codes, and test-issue exclusion. It returns aggregate counts and dated source metadata only. It does not fetch, copy, return raw rows, infer issuer domicile or security type, claim current active status, or write to the master/readiness files. Rights and import status remain held.

## Boundaries and acceptance

- The current branch remains an isolated code-only worktree; `data/`, `config/`, `outputs/`, and `docs/assets/` have no tracked diff from `main`.
- Both commands are deterministic, read-only, and fail closed on missing or malformed inputs, mismatched receipts, symlinks, path traversal, bad hashes, missing inventory rows, or unreviewed changed history. The directory creation time has no stated time zone and is not compared as an instant with UTC observation time.
- Synthetic tests prove the accept and reject cases; the ignored real 114-path disposition and saved directory receipt provide local replay evidence. No source-derived fixture enters Git.
- Company-period and peer review remain separate: exact NVDA receipt replay can be accepted for review, while AMD–NVIDIA product competition does not establish valuation-anchor eligibility.
