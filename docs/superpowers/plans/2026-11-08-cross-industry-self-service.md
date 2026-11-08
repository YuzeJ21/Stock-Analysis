# Cross-industry self-service implementation plan

**Goal:** Verify a declared four-family twelve-company sample and repair the largest evidence-backed shared gaps.

**Architecture:** Shared filing/history adapters plus a separate failure-inclusive self-service capability study using the actual Workbench and private snapshot functions. Preserve legacy studies and gates.

**Tech stack:** Existing Python/Streamlit/pytest/Playwright and free SEC/personal price paths; no dependencies or account changes.

**Spec:** docs/superpowers/specs/2026-11-08-cross-industry-self-service-design.md.

## Constraints and review focus

- Raw catalogs versus financial period semantics; malformed latest versions must not restore older facts.
- Foreign event date versus independently reported duration, native currency versus convenience USD.
- Unattempted/source failed/unsupported/method excluded remain different states and all stay in the declared denominator.
- Recomputed capabilities, exact source identity/dates/rights and immutable private replay; no canonical promotion or public source material.
- SEC access pauses, stale caches, new-filing publication lag and failed retries must not show prior success as current.

### Task 1 — Shared filing catalog and foreign-period qualification

Files: src/online_filing_context.py, tests/test_online_filing_context.py, relevant tests/test_online_research_tools.py.

- [x] Reproduce raw-bank-row, event chronology and safe legacy-document failures with constructed sources, then implement bounded metadata fixes.
- [x] Reproduce valid 6-K quarter/interim qualification gaps; join exact filing metadata without deriving a fiscal period from event dates.
- [x] Verify unsafe paths, invalid newest financial versions, ambiguous amendments and units remain held. Re-evaluate the twelve frozen source receipts privately.

### Task 2 — Actual self-service capability collector and reduced summary

Files: create src/self_service_research_coverage.py and tests/test_self_service_research_coverage.py.

- [x] Build explicit next/retry/restart collection and revalidation over the declared sample; preserve every denominator and precise state.
- [x] Reuse existing financial/price/identity/peer/context functions and disposable private-store replay checks. No synthetic success flags or user-store writes.
- [x] Test known failed/unattempted/stale/mismatched/mode-held inputs, source access pause, and identical replay. Supply stable UI-ready contracts.

### Task 3 — Workbench adapter integration and clear Discover study

Files: src/online_research_tools.py, src/sec_foreign_financials.py only for measured gaps; new src/self_service_research_coverage_ui.py; src/dashboard.py integration; relevant focused and browser tests.

- [x] Use the catalog's explicit quarter/interim qualification; preserve current native reporting definitions and conservative model eligibility.
- [x] Render one compact study in Discover Coverage studies with group fractions, selected-company details, sources, dates, exclusions and unattempted scope.
- [x] Verify representative semiconductor/bank/utility/foreign paths, snapshot replay and Monitor at desktop/phone dimensions. Preserve the clean company layout.

### Task 4 — Evidence, independent review and synchronization

- [x] Recompute before/after results from identical saved source observations, then verify online collection with measured counts and exact source receipts kept private.
- [x] Run affected regressions, real browser matrix, render/health/rights/wording/hygiene and unchanged-data checks. Independent review and bounded fix wave.
- [x] Update method, roadmap and release evidence; commit and fast-forward GitHub main; confirm exact remote content, clean checkout and remaining gates.

## Execution ledger

- Baseline c3996559 clean/synced; reused isolated worktree on codex/cross-industry-self-service. Other worktrees untouched.
- Declared sample before acquisition: AMD,NVDA,QCOM,JPM,BAC,C,DUK,SO,NEE,TSM,SAP,IBN. Live baseline retrieved financials/prices for12; catalogs usable5/12, seven metadata failures; no peer request yet. Read-only baseline regression162 passed7.06s.
- Ruling: proceed with the already-authorized existing platform and measured shared repairs; no design approval or human test handoff. Source-specific/model exclusions stay visible.

- Same-source catalog replay improved from 5/12 to 12/12; all 24 captured source bodies retain their original digests. Current annual facts: 9/12; direct quarters: 5/12; dated closes: 12/12; trends: 11/12; scenarios: 5/12; exact replay: 10/12. Fresh retained-source peer comparison: 1/12 (NVDA); all remaining reasons retained.
- Final affected regression: 772 passed in 30.93 seconds; desktop/phone: 2 passed in 93.77 seconds. Six research renders and isolated HTTP health passed. Independent reviews are clean after bounded fixes. All 89 protected files remain unchanged; the private reduced evidence packet is under outputs/local/releases/cross-industry-self-service-20261108.

- Implementation e9a72686767b0b0c53a53ad0be1e210428b88b0b fast-forwarded GitHub main. The Git remote and independent GitHub API matched; the README local/remote blob c34e2160f0539fae356e2887d783398cdd0beb29 matched. The original main checkout in the other worktree was untouched. This evidence-only follow-up records verification; CI is triggered by pull requests, so no resulting-main CI pass is claimed.
