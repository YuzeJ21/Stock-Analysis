# MRVL Peer and Earnings Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Explain MRVL annual earnings quality and a source-backed AVGO relationship without changing valuation eligibility.

**Architecture:** Independent validated SEC evidence packet from the existing financial refresh; a pure review layer and a compact Workbench renderer. The online P/E engine, saved model tools and SEC record schemas remain unchanged.

**Tech Stack:** Existing Python/Streamlit, SEC receipt transports, pytest and browser gates; no new dependency.

**Spec:** `docs/superpowers/specs/2026-11-07-mrvl-peer-earnings-design.md`.

## Global Constraints

- Personal Research only; no source-rights registry, canonical data, saved receipt schema, model readiness or trading changes.
- Reuse Companyfacts once; at most two additional submissions and two exact annual documents, on explicit financial refresh only.
- Preserve same-day completed close, annual EPS, 35-day fiscal boundaries and minimum three references.
- Never manufacture adjusted/recurring EPS, a pretax-to-after-tax bridge, FCF or an additional multiple.
- Synthetic committed fixtures; live observations/screenshots outside Git. Ordinary reads perform no network or writes.

## Review Focus

- Wrong issuer or late amendment must withhold the named scope, not use an older filing.
- Quarter/YTD cash flow cannot enter annual earnings context.
- Missing components and nonfinite/conflicting values must remain visible independently.
- Economic relevance must not add AVGO to qualified references or approved peer roles.
- Failed documents/price sources must not erase valid independent evidence or revive an old verdict.

### Task 1: Pure evidence review

**Files:** create `src/mrvl_earnings_review.py`, `tests/test_mrvl_earnings_review.py`.

**Interfaces:** Implement the normalization, sealing, builder and financial-view validation functions in the spec. Return quality fields, flags/gaps, peer_context and source_refs with explicit inspection rights; do not return a valuation conclusion.

- [x] Write and observe failing exact-period, scope, field, receipt and relationship tests.
- [x] Implement strict bounded validation and per-field outcomes.
- [x] Verify all negative cases and numeric-peer result invariance.

### Task 2: Online collector and financial refresh

**Files:** create `src/mrvl_earnings_sources.py`, `tests/test_mrvl_earnings_sources.py`; modify `src/sec_annual_history.py` and its focused tests.

**Interfaces:** Consume Task 1 helpers; produce the packet under `financial_view['mrvl_earnings_review']` after MRVL identity is verified. Use `source_fetcher` for controlled JSON/HTML fixture transport and existing exact-source defaults otherwise.

- [x] Observe failing explicit request, mode, identity, failure isolation and request-bound tests.
- [x] Add the bounded collector and nonfatal MRVL hook.
- [x] Verify no extra Companyfacts fetch, no non-MRVL requests, no ordinary-read transport and no approved-field/schema changes.

### Task 3: Workbench explanation

**Files:** create `src/mrvl_earnings_review_ui.py`, UI tests and a dedicated disposable MRVL browser fixture; modify `src/company_workbench_ui.py`.

**Interfaces:** Consume validated financial-view packet, render concise annual quality and named-peer context plus sources_only mode. Existing peer view continues to own all prices, comparison statistics and admission.

- [x] Observe missing explanation in a test before implementation.
- [x] Render in Valuation & Peers and Data Sources; retain clean Overview and existing tools.
- [x] Verify English, safe source links, source/period/rights details and missing reasons.
- [x] Exercise desktop/phone disclosure and section/Monitor reuse without refetch or canonical writes.

### Task 4: Source verification, release and sync

**Files:** update online peer method, active roadmap/history and release evidence; keep roadmap within its existing line limit.

- [x] Reconcile live MRVL facts and exact MRVL/AVGO annual documents with the implemented path.
- [x] Obtain independent code review and resolve findings with regressions.
- [x] Freeze source and run appropriate repository, UI, wording, hygiene and unchanged-data checks.
- [x] Commit tested work, synchronize GitHub main without force/unrelated changes, and independently verify remote head.

## Execution ledger

- Baseline main `15b04442a0e4660d2091f786df5013f6b4a64105`; clean, synced existing linked worktree reused; branch `codex/mrvl-peer-earnings`.
- Baseline relevant tests: 150 passed in 2.45s.
- Ruling: follow the user's authorized next-stage execution without another approval/test handoff; add the independent explanation rather than a new multiple or general redesign.
- Ruling: attach to financial refresh rather than peer acquisition so listing/price outages do not hide financial evidence. Exact source changes and new registered commercial fields remain gaps.

- Focused final regression: 451 passed in 61.80s; browser/UI/Workbench layout regression: 16 passed in 28.00s.
- Live phone caption regression reproduced and corrected; 315px caption width, 72px height at 390px viewport, no horizontal overflow.
- Independent whole-branch review: no actionable P1/P2 findings; 181 focused checks passed in 2.84s.

- Frozen code commit `adefcdbdd54821401914749952312b9406da9c15`: full protected-artifact suite **9,330 passed, 3 skipped, 1 warning in 2,531.33s**; guard exit 0. All 78 canonical/config/assets tracked files match baseline.
- Six research routes, fresh dashboard HTTP health and commercial-beta checks passed. Three skips are absent historical private receipts and two opt-in AMD/QCOM live cases; MRVL browser cases ran.
- Tested code synchronized to GitHub main with remote ref independently confirmed. Final README next-stage correction and verification ledger are documentation only; runtime code and tests remain identical to the tested commit.
