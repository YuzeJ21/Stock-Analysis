# MRVL After-Tax Reconciliation Implementation Plan

**Goal:** Verify and explain the issuer's exact annual after-tax reconciliation without qualifying normalized earnings or changing valuation inputs.

**Architecture:** One pure reconciliation module; an optional sibling in the existing sealed MRVL packet; existing collector and renderer integration. No new provider, storage schema or valuation engine.

**Tech stack:** Existing Python/Streamlit, SEC receipt transport, HTML parsing, decimal arithmetic, pytest and desktop/phone browser checks.

**Spec:** `docs/superpowers/specs/2026-11-08-mrvl-after-tax-design.md`.

## Global constraints

- Personal Research inspection only. No canonical data, rights registry, approved fields, saved receipt schema, readiness or peer admission changes.
- Reuse Companyfacts and MRVL profile; at most two additional fixed SEC HTML URLs, only during explicit financial refresh; no retries or ordinary-read fetches.
- Preserve annual GAAP EPS, same-day completed close, 35-day fiscal windows and at least three references. Issuer non-GAAP EPS is not a new multiple.
- Synthetic committed fixtures; live source observations outside Git. Annual/quarterly, dollars/millions/per-share, pretax/after-tax and reported/normalized measures stay separate.

## Review focus

- Same annual/quarter ending date must not select the wrong column; source spans and duration headers govern.
- Hidden/duplicate/conflicting rows or extra adjustment rows cannot silently produce a verified bridge.
- Pretax signs and aggregate tax effects must reconcile at source precision; EPS/share inputs are independent disclosures.
- Changed metadata, amendments, raw bytes or observations must withhold this extension without erasing valid independent fields.
- A valid issuer bridge cannot grant gain-only tax allocation, recurring earnings or adjusted-peer valuation.

### Task 1: Pure exact-source reconciliation

**Files:** create `src/mrvl_after_tax_reconciliation.py` and `tests/test_mrvl_after_tax_reconciliation.py`.

**Interfaces:** `select_mrvl_after_tax_source(profile_receipt, *, as_of=None)` returns selected metadata or a withheld reason. `build_mrvl_after_tax_reconciliation(evidence, *, profile_receipt, annual_fields, annual_filing, as_of=None)` returns verified issuer observations/checks or a local withheld result. Evidence schema is `mrvl-after-tax-reconciliation-v1`, with `primary` and `exhibit` raw receipts. Selected results expose component rows, reported GAAP/non-GAAP net income/EPS/shares, source refs and explicit independent gaps; never grant a valuation denominator.

- [x] Observe failing exact source, table, arithmetic, annual anchor and failure tests.
- [x] Implement bounded source/visibility/column validation and signed decimal checks.
- [x] Verify constructed cases and privately replay the actual SEC documents; preserve raw values and source locations without committing real fixtures.

### Task 2: Collector and review integration

**Files:** modify `src/mrvl_earnings_sources.py`, `src/mrvl_earnings_review.py`, relevant collector/review/annual-history tests.

- [x] Test absent/qualified/currently changed 8-K scope, two-request bound and source failure isolation before implementation.
- [x] Attach optional evidence using the already fetched MRVL profile; no extra Companyfacts/submissions fetch.
- [x] Bound new bytes before parent hashing; validate into `quality.after_tax_reconciliation`. Replace only the qualified aggregate-bridge gap; keep old packets, annual fields, AVGO and valuation output unchanged.

### Task 3: Existing Workbench disclosure

**Files:** modify `src/mrvl_earnings_review_ui.py` and the existing MRVL UI/Workbench/browser tests.

- [x] Observe missing-reconciliation UI failure, then add a compact source-backed disclosure and readable remaining gaps.
- [x] Exercise 1440×1000 desktop and 390×844 phone; inspect signed component rows, sources, English and overflow. Keep Overview clean.
- [x] Reuse loaded evidence through sections and Monitor return without refetch; failed refresh drops prior verified reconciliation while retaining valid annual evidence.

### Task 4: Verify, review, document and synchronize

- [x] Reconcile live SEC evidence with implemented output; preserve source rights and canonical hashes.
- [x] Run affected regression, desktop/phone, render/health and public/hygiene checks. Review independently and resolve actual findings.
- [ ] Update README, roadmap, method and release packet; commit verified code and synchronize main without force; confirm exact remote head.

## Execution ledger

- Baseline `f6e84abb3614f81dc7028df71f0a666e600cc131`, clean and synced with origin/main. Existing linked worktree reused on `codex/mrvl-aftertax-reconciliation`; unrelated worktrees preserved.
- Baseline affected MRVL tests: **161 passed in 1.98s**, one existing dependency deprecation warning.
- Ruling: use the user-authorized next-stage scope without another design/test handoff. The smallest useful path is the issuer aggregate bridge; a gain-only normalized denominator remains unsupported.
- Ruling: extend the sealed packet additively, retain the exact MRVL/AVGO component keys and isolate reconciliation failures. No general-purpose SEC or bank parser changes are needed.
- Ruling: use focused affected-system checks plus live/browser evidence, expanding only for failures or cross-cutting changes. Do not repeat the previous 42-minute whole-repository baseline solely for this isolated extension.

- Pure exact-source implementation delegated to a fresh implementer; source/architecture research and whole-source review were independent. Existing transport and generic parsers were not broadened.
- Collector RED: six missing-extension/request-bound failures; GREEN: six passed. Parent review/size-guard RED: three missing-integration failures; GREEN with existing review/source tests: 156 passed.
- Whole-source review: two P2 findings (share scale convention; conflicting local unit/duration header). Both fixed with observed RED/GREEN cases; component scale is a multiplier, and the actual builder-to-UI path preserves millions of shares. No unresolved important finding remains.
- Live precision correction: large monetary bridge values now retain original million precision; the regression was observed failing before the renderer fix.
- Protected affected-system regression: **537 passed in 58.65s**, one existing dependency warning, no skips; guard exit 0. Final browser/UI/Workbench regression: **24 passed in 29.92s**.
- Current real SEC replay: fifteen annual observations, zero subtotal/net-income residuals, separate GAAP/non-GAAP EPS rounding checks passed, both eligibility flags false. Raw observations stay outside Git.
- Six research renders, fresh HTTP health, commercial-beta and 64-file wording checks passed. All 78 tracked data/config/assets files match baseline. Live desktop/phone and Monitor return passed without a human tester.
