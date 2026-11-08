# Bank peer packet retention implementation plan

Goal: preserve complete bank peer source evidence within the existing retained limits, without changing valuation admission rules.

Design: docs/superpowers/specs/2026-11-08-bank-peer-packet-retention-design.md.

## Work and owners

- [x] Root: verify live checkout/default branch/rights state and reproduce JPM size failure; record private full source packet and baseline tests.
- [x] Codec agent: failing tests, bounded lossless codec and adversarial integrity/resource cases in the new storage module.
- [x] Root: integration regressions, compact/expand/reference-pruning support, precise retained-storage diagnostics and legacy compatibility.
- [x] Root: capture BAC/C through the same production adapters, compare unchanged source objects/documents and recomputed valuation/exclusion results. Keep all gaps and denominators visible.
- [x] Browser agent: constructed six-attempt study with three banks, explicit recheck, source-free reads, desktop/phone screenshots and unchanged-data checks.
- [x] Root/reviewer: affected regression, six route renders, preserved 89-file manifest, wording/hygiene, independent review and bounded fix wave.
- [ ] Root: update current method/roadmap/release evidence, commit, synchronize GitHub main and verify exact remote content.

## Execution ledger

- Reused the existing isolated checkout on codex/bank-peer-packet-retention. Baseline main 1f7e149d verified through the Git remote and independent GitHub API; clean before changes. Other worktrees unchanged.
- Baseline peer/coverage tests: 108 passed in 3.67 seconds. Existing dateutil warning retained.
- Fresh JPM referenced packet: 74,100,090 bytes; lossless zlib: 5,274,077 bytes. Full capture, observation metadata and component measurements remain under /tmp/bank-peer-packets-20261108; no real source data added to Git.

- The codec's 92 adversarial cases and five integration cases pass. The final affected group passed 855 tests in 33.73 seconds; desktop/phone passed two cases in 96.49 seconds; all six research renders passed. Source-rule files remain unchanged.
- JPM/BAC/C each restore a complete 74.1 MB original packet from approximately 7.03 MB stored evidence, with all twelve embedded raw receipts preserved, identical original conclusions and three eligible references. A fresh production JPM retry also passed.
- The review's company-scope mismatch was fixed with a red/green regression. Phone proof contrast was repaired without changing legacy provenance. Normalized snapshot acceptance of raw_cover_observations/raw_symbol remains a separate next stage; no acceptance gate or user store was changed. All 89 protected files remain unchanged.
