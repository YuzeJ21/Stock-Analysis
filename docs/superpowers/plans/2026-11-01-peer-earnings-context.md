# Peer Earnings Context Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Explain reported annual earnings changes beside online P/E and fix the measured one-year price observation limitation.

**Architecture:** Pure comparative EPS extraction augments independently bound issuer observations. A bounded optional chart range expands only the peer collection; the presenter shares the same observation across Valuation and Sources.

**Tech Stack:** Existing Python, pytest, Streamlit, SEC receipts and chart adapter; no new dependencies.

**Spec:** docs/superpowers/specs/2026-11-01-peer-earnings-context-design.md

## Global Constraints

- Personal research only; no source-rights, saved-model, canonical, readiness or universe mutation.
- Same accession/form/publication/concept/unit; prior end exactly current start minus one day, duration 350–380 days, positive prior for percentage, finite magnitude at most 1e6.
- Only 1y/2y ranges; default 1y, peer requests 2y, respective bar limits 400/800, exact URL/range binding; actual split/quote/identity gates retained.
- Fiscal window remains reference-relative-to-subject 35 days; no TTM, forecasts, PEG, fair-value or full-universe claims.
- Automated tests and desktop/phone checks; exact tested developer-head sync, private evidence, held PR draft, hosted CI separate.

## Review Focus

- Same filing comparative EPS revised from older reports: select the matched filing's value, not an earlier accession (Task1).
- Missing or invalid comparative EPS must not silently remove the company's valid annual P/E or change its median membership (Task1).
- Claimed two-year range with less actual history or a post-period split stays withheld (Task2).
- Extended history must not allow mismatched source URLs, more than 800 rows, public/commercial requests or cached identity substitution (Task2).
- Growth missingness and negative bases remain understandable in both source and valuation panes on a narrow phone (Task3).

---

### Task 1: Comparative annual EPS evidence

**Files:** Create src/online_peer_earnings.py and tests/test_online_peer_earnings.py; modify src/online_peer_valuation.py.

**Interfaces:** Produces `annual_eps_context(facts: Mapping, current: Mapping) -> dict`, with status/reason, current/prior periods and EPS, and growth_fraction. Consumes already validated direct EPS and SEC facts. Existing issuer output gains `earnings_context`; excluded EPS diagnostics use the same helper. No network/state writes.

- [ ] Write tests for +25% hand calculation, actual same-filing revised prior, identical duplicates, wrong accession/form/filed/unit, nonfinite/conflicting/absent/short/nonadjacent prior, nonpositive base, and input immutability. Assert valid P/E and membership remain intact despite missing context.
- [ ] Run `python3 -m pytest tests/test_online_peer_earnings.py -q`; expect missing-helper failures before implementation.
- [ ] Implement pure helper and source-bound integration, never alternate-accession fallback.
- [ ] Run `python3 -m pytest tests/test_online_peer_earnings.py tests/test_online_peer_valuation.py tests/test_online_peer_sources.py -q`; expect all pass.
- [ ] Commit task code/tests; record RED/GREEN and complete with the same command.

### Task 2: Bounded two-year peer price observation

**Files:** Modify src/online_company_prices.py, src/online_research_history_view.py, src/online_peer_sources.py, src/online_peer_valuation.py; add tests/test_peer_price_coverage.py.

**Interfaces:** `price_source_url(symbol, history_range='1y')`; `fetch_online_company_prices(..., history_range='1y')`. Peer collection calls prices with history_range='2y'. Issuer output adds actual first/last price observation dates and requested range; validator binds range to exact URL and limits. Existing default callers unchanged.

- [ ] Write tests for >400 valid two-year bars, one-year limit, invalid ranges without transport, redirect/range mismatch, 800 cap, peer explicit range, old-period recovery, insufficient actual range and post-period split rejection. Include all-mode/legacy defaults and source diagnostics.
- [ ] Run `python3 -m pytest tests/test_peer_price_coverage.py -q`; expect missing optional range/output behavior failures.
- [ ] Implement bounded optional range and validated integration without relaxing actual coverage gates.
- [ ] Run `python3 -m pytest tests/test_peer_price_coverage.py tests/test_online_company_prices.py tests/test_online_research_history_view.py tests/test_online_peer_earnings.py tests/test_online_peer_valuation.py tests/test_online_peer_sources.py -q`; expect all pass.
- [ ] Commit task code/tests; complete with the same verified focused set.

### Task 3: Readable context and complete delivery

**Files:** Modify src/online_peer_valuation_ui.py and its tests; update docs/ONLINE_PEER_VALUATION.md, ROADMAP.md and prior internal design fiscal-window wording. Private outputs remain ignored.

**Interfaces:** Existing `online_peer_valuation_html(view, sources_only=False)` renders new evidence only; no fetch or writes. Preserve header and saved compositor contracts.

- [ ] Write failing UI/integration assertions for explicit prior/current dates/values, signed growth, missing and nonpositive base reasons, source URL/digest and actual price range in both panes; growth absent must not erase valid P/E. Run the affected tests and observe expected failures.
- [ ] Implement a separately labelled reported EPS context block; retain mobile readable cards and existing source disclosures. Update neutral docs and clarify the unchanged fiscal-window rule.
- [ ] Run `python3 -m pytest tests/test_online_peer_valuation_ui.py tests/test_integrated_company_workbench.py tests/test_online_peer_earnings.py tests/test_peer_price_coverage.py -q`; expect all pass.
- [ ] Commit, perform one fresh whole-stage review, fix any Important/Critical findings through RED/GREEN, retain Minor notes. Verify real desktop/phone states at final code, preserve private dated source receipts and protected hashes.
- [ ] Run `make test` sequentially with no preview server competing; expect guarded full suite exit0, explicitly recording any existing skipped receipt test.
- [ ] Verify unchanged protected data, authorized exact-head developer push and remote match, separate hosted CI status, restore preview. Archive ledger/tests/screenshots/rights/rulings/private PR draft into a hash-verified ignored packet; remove only this plan's archived scratch.
