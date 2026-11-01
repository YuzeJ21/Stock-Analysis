# Integrated Company Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans for native task-by-task execution. User already authorized direct execution and synchronization after automated checks; do not ask another handoff question.

**Goal:** Integrate existing online research and saved tools into five coherent company sections.
**Architecture:** A pure, source-validated projection and a lazy Streamlit compositor reuse current adapters/presenters. A narrow section mode reuses existing saved-report preparation and routes only valuation or journal/HTML tools. Public/Operator behavior remains unchanged.
**Tech Stack:** Existing Python, Streamlit, standard library, pytest and IAB browser.
**Spec:** docs/superpowers/specs/2026-10-31-integrated-company-workbench-design.md

## Global Constraints
- Reuse existing isolated codex/next-stage-truth-20261029; base 6c59b1cf1eb24dd420cf72d32f30cb825c273ee2.
- Preserve canonical fundamentals, readiness, rights registry and 5,954-observation checkpoint.
- Five sections in exact order: 概览、财务趋势、估值与同行、研究记录、数据来源. One H1; only selected section renders.
- Explicit fetch only; reuse scoped unavailable and successful attempts. Facts do not unlock saved models.
- Preserve all source, duration, units, rights, journal confirmation and historical-input labels.
- Automated full tests/browser checks before authorized branch push; no PR/merge/deploy/publish/fees/credential changes.

## Review Focus
- Failed or same-symbol/wrong-CIK observations never leak fields or unlock saved analysis.
- One source failure does not hide validated sibling evidence; pane switches never refetch.
- Switching ticker/profile/snapshot never reuses another saved report or journal context.
- Annual/quarterly/native-currency and cumulative cash-flow scope remains explicit; old fields cannot claim current model readiness.
- Opening five-section notes retains exact brief and authoring integrity, keyboard access and native control targets; Public/Operator behavior remains distinct.

### Task 1: Source-bound section projection
**Files:** create src/company_workbench_sections.py, tests/test_company_workbench_sections.py.
**Interfaces:** workbench_projection(ticker, financial_view, prices, expected_cik=None) -> dict; workbench_header_html(ticker, projection, saved_scope) -> str. Existing strict financial validators/presenters remain authoritative. Five-section constant and normalized selection are pure.
- [ ] RED tests for exact sections, available annual/quarterly versus blocked model status, wrong ticker/CIK, malformed cached facts, unavailable sibling sources and zero versus missing.
- [ ] Implement read-only projection; no network or state mutation.
- [ ] Run new tests plus existing online financial/history tests; commit and ledger exact results.

### Task 2: Integrated company UI and saved tools
**Files:** create src/company_workbench_ui.py and integration/AppTest tests; modify src/dashboard.py, compact history presenters, peer empty-state rendering and native control styles.
**Interfaces:** render_integrated_company(st_api, ticker, financial_view, prices, association, expected_cik, online_candidate, saved_available, callbacks) renders one selected pane. render_single_stock_report(..., workbench_section=None) reuses existing scoped saved preparation and dispatches only valuation or notes when supplied; default behavior unchanged.
- [ ] RED tests for all five visible sections, one selected body, no legacy unavailable-quarter statement beside loaded online facts, no refetch on pane switch, combined explicit update, source-failure independence and saved/online identity isolation.
- [ ] Reuse existing annual/quarterly/foreign charts, price chart, exact source controls, DCF controls, authoring and HTML brief. Add compact history mode without changing default presenters.
- [ ] Update obsolete journey/recording-double tests to the approved flow, retaining their data-isolation and protected-write checks. Extend native light/dark regression to enabled form-submit controls.
- [ ] Run focused suites including all dashboard contracts; commit and ledger results.

### Task 3: Browser regression and delivery
**Files:** adapt src/research_accessibility_browser_gate.py and its journey tests; update PRODUCT_SPEC.md, ROADMAP.md and online/personal workflow docs.
- [ ] Keep old HTML brief visibility, occlusion, export and semantic checks; navigate through 研究记录 to reach the same artifact, retaining pointer/keyboard activation evidence.
- [ ] Actual IAB desktop/phone/narrow checks over five panes, one live combined online fetch, source dates/identity, company switch and readable controls. Capture accepted before/after screenshots privately.
- [ ] One fresh whole-task reviewer; Critical/Important findings receive one RED/GREEN repair pass; no review loop.
- [ ] Commit final implementation, stop own preview, run fresh full make test under no-write guard. Do not write protected output roots during that run.
- [ ] Verify protected hashes, archive evidence and scratch, create held PR draft, push developer branch normally, verify exact remote/main/hosted CI status and restore local preview. Preserve unrelated worktrees/data.
