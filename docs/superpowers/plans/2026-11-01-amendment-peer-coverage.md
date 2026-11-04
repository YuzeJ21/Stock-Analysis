# Amendment Scope and Peer Coverage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Resolve the exact AMD annual EPS amendment gap using affirmative source evidence and expose honest industry peer-valuation coverage.

**Architecture:** A separate byte-pinned bridge validates original Inline XBRL EPS against Companyfacts without weakening the shared parser. A session audit revalidates per-target source packets through existing peer rules; separate presentation composes the audit in Discover and scope trace in Company Workbench.

**Tech Stack:** Existing Python, pytest, Streamlit, SEC exact-source adapters and yfinance; no new dependencies.

**Spec:** docs/superpowers/specs/2026-11-01-amendment-peer-coverage-design.md

## Global Constraints

- Personal Research only; no canonical/rights/readiness/universe changes; no raw source or actual EPS fixtures committed.
- AMD bridge only known CIK/accessions/report/filed/accepted/document pairs and exact original/amendment hashes in the spec; both fresh<=24h, bounded<=32MiB, exact URLs and current unique metadata. Record false AmendmentFlag without weakening generic validation.
- Original direct dimensionless annual diluted EPS,350–380days, USD/shares divided unit, exact original-accession Companyfacts agreement. All existing valuation gates retained.
- Default15declared targets;<=20unique normalized symbols; one subject per explicit action, per-target packets, session-only resume, explicit retry, pause after2consecutive subject source failures; no hidden fetch.
- Counts include all requested targets, separate subjectPE/reference assessment/comparison/pending; subject blocked means references unassessed, not zero. Group only source-bound industry/SIC; adapter operations are not HTTP counts.
- Final automated/full guard and desktop/phone evidence, exact-head developer sync, private packet and held PR draft; hosted CI separate; no PR/merge/deploy/publish/purchase/credentials change.

## Review Focus

- A later/malformed amendment or changed scope bytes must not revive original EPS (Task1).
- Segment/continuing-operations EPS, reversed units, duplicate facts and Companyfacts conflicts must remain withheld (Task1).
- Blocked subjects and unknown industries remain in the requested denominator without fabricated zero-peer counts (Task2).
- Stale or tampered per-target source packets cannot revive stored comparison/industry labels; pause/retry never hides failures (Task2).
- Source scope discrepancy, partial coverage and unassessed rows remain understandable on a phone, without altering saved tools or financial-universe state (Task3).

---

### Task 1: Exact AMD scope bridge and source integration

**Files:** Create src/annual_amendment_evidence.py and tests/test_annual_amendment_evidence.py; modify src/online_peer_sources.py and src/online_peer_valuation.py; add focused integration assertions to existing peer tests.

**Interfaces:** `fetch_amendment_evidence(ticker,cik,profile,*,user_agent,fetcher=None,observed_at=None,workspace_mode='research') -> dict`; `validate_amendment_evidence(packet,*,ticker,cik,filings,as_of) -> dict` returns parsed original EPS plus metadata/scope only for the pinned policy. Collector stores `amendment_evidence` only for eligible current metadata. Core `_resolved_annual_eps` uses ordinary selection first, then the independently validated bridge for the precise missing-amendment gap and Companyfacts agreement.

- [ ] Write synthetic tests with a monkeypatched test-only policy, no real document fixture: success/trace, missing bridge, both changed hashes, new annual/amendment/tie/missing acceptance, metadata/redirect/mode/freshness/base64 limits, DEI mismatch, dimensional/short/wrong unit/definition/conflicting EPS and Companyfacts disagreement; unchanged generic flag rejection.
- [ ] Run `python3 -m pytest tests/test_annual_amendment_evidence.py -q`; expect missing-feature failures.
- [ ] Implement the isolated proof/fetcher and integrate source-bound original EPS recovery and diagnostics. Do not change src/sec_inline_filing.py.
- [ ] Run `python3 -m pytest tests/test_annual_amendment_evidence.py tests/test_online_peer_valuation.py tests/test_online_peer_sources.py tests/test_online_peer_earnings.py tests/test_sec_inline_filing.py -q`; expect all pass; verify real saved receipts through the new code privately.
- [ ] Commit code/tests; complete with the same focused command and record RED/GREEN.

### Task 2: Failure-inclusive session industry audit

**Files:** Create src/online_peer_coverage.py and tests/test_online_peer_coverage.py; extend independently validated metadata in src/online_peer_valuation.py and reduced vendor/profile fields in src/online_peer_sources.py.

**Interfaces:** `get_peer_coverage(session_state,*,inspect_requested=False,reset_requested=False,retry_ticker=None,tickers=DEFAULT_SAMPLE,user_agent=None,dependencies=None,as_of=None,workspace_mode='research') -> dict`. Per-target existing peer getter states remain under the new session key. Summary contains requested/attempted/PE/reference/comparison/pending counts, source-bound by_industry groups, primary/excluded reason counts and one row per requested target.

- [ ] Write failing synthetic tests for denominator/pending/source/identity failures, unassessed vs zero, unknown/source-bound industries, per-target reuse/no network, stale/tampered packets, request changes, partial candidate pauses,2source-failure audit pause and explicit retry/reset, all modes, adapter counts and unchanged financial checkpoint.
- [ ] Run `python3 -m pytest tests/test_online_peer_coverage.py -q`; expect missing-feature failures.
- [ ] Implement bounded progressive state and recomputed summary; no persistent checkpoint writer or market-wide inference.
- [ ] Run `python3 -m pytest tests/test_online_peer_coverage.py tests/test_annual_amendment_evidence.py tests/test_online_peer_sources.py tests/test_online_peer_valuation.py tests/test_online_research_coverage.py -q`; expect all pass.
- [ ] Commit; complete with the same command.

### Task 3: Clear company scope, coverage UI and delivery

**Files:** Create src/online_peer_coverage_ui.py and tests/test_online_peer_coverage_ui.py; modify src/online_peer_valuation_ui.py and tests, compact Discover call in src/dashboard.py; update ROADMAP.md and docs/ONLINE_PEER_VALUATION.md, add docs/PEER_COVERAGE_METHOD.md.

**Interfaces:** `peer_coverage_html(summary) -> str`, `render_peer_coverage(st_api) -> dict` owns explicit audit actions, no network during ordinary reads. Existing online peer presenter shows original financial identity separately from amendment scope and flag discrepancy in both panes.

- [ ] Write failing UI/AppTest assertions for scope sources/digests/discrepancy, sample denominators/pending/unknown/unassessed language, first blocker and candidate reason separation, session-only scope, explicit retry and no hidden requests, safe links/escaping, saved isolation.
- [ ] Run new/affected UI tests; expect missing behavior failures.
- [ ] Implement compact coverage panel and source scope disclosure; update neutral docs. Verify live15target sample privately, preserve failures and source receipts; no all-company coverage claim.
- [ ] Run `python3 -m pytest tests/test_online_peer_coverage_ui.py tests/test_online_peer_valuation_ui.py tests/test_online_peer_coverage.py tests/test_annual_amendment_evidence.py tests/test_integrated_company_workbench.py -q`; expect all pass.
- [ ] Commit, perform one fresh whole-stage review, regress/fix Important/Critical findings once and ledger Minors. Capture final-head desktop/phone AMD/TXN valuation/sources and Discover industry coverage including pending/failure reasons.
- [ ] Stop only owned preview before `make test`; expect guarded full suite exit0, record existing skips/warnings explicitly. Verify protected hashes and exact tested-head developer push/remote match; report CI separately.
- [ ] Restore preview, deliver private source/evidence/rights/review/localPRdraft with verified manifest, archive ledger before deleting only this plan's scratch.
