# Sector Financials and U.S. Universe Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Support exact-source industry/IFRS statements and full observed U.S.-listing coverage denominators with honest progress and gaps.

**Architecture:** Additive direct-field definitions and a separate IFRS inspection contract; official listing receipts form an inventory fingerprint; serialized issuer probes feed a reduced session-only coverage ledger.

**Tech Stack:** Existing Python, Streamlit, pytest, browser automation; no new dependencies.

**Spec:** docs/superpowers/specs/2026-10-30-sector-and-us-universe-design.md

## Global Constraints
- Preserve canonical data and config/source_rights.yml; no raw source redistribution.
- Personal inspection only for listing/SIC/price metadata; no readiness or valuation activation.
- No USD/native currency mixing, invented quarterly periods, inferred bank/utility sums or missing denominator entries.
- Source requests serialized and bounded; explicit UI actions only; no price batch.
- Only code/tests/neutral documentation pushed to the existing feature branch after complete checks; no PR/merge/deploy.

## Review Focus
- Newer malformed or different-unit amendments must hold affected evidence instead of reviving old values (Task 1).
- Multiple currencies/concepts in one source must not silently join translations or definitions (Task 1).
- Directory aliases, duplicate share classes, unknown venues and SEC-only listings must not inflate issuer coverage (Task 2).
- Old/incompatible inventories, failed attempts and unprobed rows must not disappear or inflate success (Task 2).
- Cached or non-Personal rendering must not leak invalid amounts, trigger network access or overflow phone layouts (Task 3).

### Task 1: Direct bank, utility and IFRS financial support
**Files:** Modify src/providers/sec_companyfacts.py, src/company_sec_online_preview.py, src/sec_quarterly_history.py, src/sec_annual_history.py; create src/sec_foreign_financials.py; tests/test_sec_industry_financials.py.
**Interfaces:** Existing fetch_sec_online_research_view returns an additional foreign_financials source-bound contract. build_sec_foreign_financials(ticker,payload,*,expected_cik,observed_at,source_url,payload_sha256) and validated_foreign_financials(view) return direct native-unit annual/quarter/interim evidence or a withheld reason.
- [ ] Write tests for bank/utility annual and quarters, native IFRS/non-USD preference and currency ambiguity, 6-K exact durations, no derived totals, malformed/newer revisions, rights and issuer mismatch.
- [ ] Run python3 -m pytest tests/test_sec_industry_financials.py -q; Expected: feature assertions fail.
- [ ] Implement the direct definitions and independent IFRS path with strict source identity/period/unit validation and no writes.
- [ ] Run python3 -m pytest tests/test_sec_industry_financials.py tests/test_sec_annual_history.py tests/test_sec_quarterly_history.py -q; Expected: all pass.
- [ ] Commit the reviewed task scope.

### Task 2: Official full inventory and serialized coverage progression
**Files:** Create src/online_us_universe.py; modify src/online_research_coverage.py; tests/test_online_us_universe.py.
**Interfaces:** load_online_us_universe(*,user_agent,fetcher=None,observed_at=None,workspace_mode='research') returns a source-bound inventory. build_universe_coverage(inventory,observations) returns recomputed reduced counts; inspect_next_universe_batch(state,*,user_agent,batch_size=20,source_fetcher=None,observed_at=None,workspace_mode='research') returns updated session progress.
- [ ] Write tests for full directory/SEC union, test/ETF exclusions, unknown/missing venues, ambiguous aliases, issuer de-duplication, no-request loading/rerenders, stale fingerprints, source errors and failed/unprobed denominators.
- [ ] Run python3 -m pytest tests/test_online_us_universe.py -q; Expected: feature assertions fail.
- [ ] Implement schema/date/digest validated receipts, union reconciliation, full denominators, per-CIK batch progression and optional --scan-all CLI. Integrate native IFRS availability with existing reduced field counts without currency comparisons.
- [ ] Run python3 -m pytest tests/test_online_us_universe.py tests/test_online_research_coverage.py -q; Expected: all pass.
- [ ] Commit the task scope.

### Task 3: Product integration, live evidence and release verification
**Files:** Modify src/dashboard.py, src/online_research_expansion_view.py; create src/online_us_universe_view.py; modify README.md, ROADMAP.md, docs/ONLINE_RESEARCH_COVERAGE.md, docs/ONLINE_COMPANY_RESEARCH.md; tests/test_online_us_universe_view.py and tests/test_online_research_expansion_view.py.
**Interfaces:** foreign_financials_html(view) displays validated native-unit evidence; universe_coverage_html(state) displays validated full inventory/progress; Discover exposes explicit load/next-batch controls.
- [ ] Write failing behavior tests for exact labels, stale/non-Personal/no-fetch holds and display validation; run them and observe expected failures.
- [ ] Implement compact source-labelled views and controls; document actual remaining venue/definition/rights gates.
- [ ] Run focused integration tests; Expected: all pass.
- [ ] Record live official full inventory and a bank/utility/foreign evidence run.
- [ ] Check desktop/phone/narrow-phone browser geometry and source displays; Expected: no horizontal overflow or invalid evidence.
- [ ] Run make public-wording-check and staged hygiene; Expected: pass. Commit code/test/neutral docs only.
- [ ] Run fresh whole-branch independent review and fix Important/Critical findings with reproducing RED-to-GREEN tests.
- [ ] Run make test at the final committed SHA; Expected: complete suite and no-write guard pass.
- [ ] Verify protected hashes, push authorized feature branch, verify exact remote head and hosted-check state; archive local release evidence and held PR draft.
