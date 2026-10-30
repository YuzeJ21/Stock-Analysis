# Exact Filings and Coverage Resume Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Inspect the missing exact SEC company periods and continue source-bound issuer coverage with recoverable progress.

**Architecture:** Separate archive receipt/selection, namespace-aware extraction and presentation; a validated reduced coverage checkpoint supplies continuation without canonical changes.

**Tech Stack:** Existing Python/Streamlit/pytest/Playwright and standard-library XML/Decimal/POSIX locking; no new dependencies.

**Spec:** docs/superpowers/specs/2026-10-30-exact-filings-and-coverage-resume-design.md

## Global Constraints
- Preserve canonical data, readiness and config/source_rights.yml; archive rights remain unregistered personal inspection only.
- Exact SEC archive URLs;32MiB document bound;30s timeout; no redirect; identifying User-Agent; source-access limits pause probes.
- Annual300–430days; quarter70–105days; cumulative105–320days. No dimensional aggregates, FX, ADS conversion, derived quarter, FCF or valuation.
- Only explicit source actions; cached results validated; no network during ordinary rerender/restore.
- Checkpoints contain normalized metadata/reduced availability only, use0600/lock/atomic writes/backup, and never overwrite unrelated/canonical paths.
- Only code/tests/neutral docs pushed after final complete tests; no PR, merge, deploy, publish, purchase or credentials changes.

## Review Focus
- Combined filings, aliased namespace prefixes and dimensioned duplicate facts must never select a subsidiary or wrong taxonomy (Task1).
- Scale/sign/precision, unit translations, nil/conflicting facts and missing quarter cash flows must not become invented values (Task1).
- Newer malformed amendments, acceptance-time ties and agent accessions must hold or correctly bind source identity (Task1).
- Crash/concurrent writers, corrupt or mismatched checkpoints and source-access limits must preserve valid progress without double-counting (Task2).
- Rerenders, company switches, restore and non-Personal contexts must not fetch/leak/overflow or inflate readiness/coverage (Task3).

### Task 1: Exact filing selection, receipt and direct Inline XBRL packet
**Files:** Create src/sec_exact_filing.py and src/sec_inline_filing.py; tests/test_sec_exact_filing.py and tests/test_sec_inline_filing.py.
**Interfaces:** select_sec_filing(ticker,cik,submissions_receipt,*,period_kind) returns exact metadata or held reason; fetch_sec_filing_preview(ticker,*,period_kind,user_agent,fetcher=None,observed_at=None,expected_cik=None) returns source-bound inspection packet. extract_inline_filing(raw,selection,receipt) and validated_filing_preview(packet,ticker,period_kind) return direct annual/quarter/cumulative fields or explicit holds.
- [ ] Write synthetic tests for exact selection/agent accession/amendment holds, safe URL/limits/redirects, issuer/dimension/namespace matching, scale/sign/decimals, currencies and direct versus cumulative fields.
- [ ] Run python3 -m pytest tests/test_sec_exact_filing.py tests/test_sec_inline_filing.py -q; Expected: feature assertions fail.
- [ ] Implement bounded source selection/transport and namespace-aware direct extraction, retaining complete source identities and rights holds.
- [ ] Run the same task suite; Expected: all pass.
- [ ] Inspect DUK/SO2026-06-30 and TSM2025-12-31 against live SEC primary documents; record exact available/held fields without canonical writes.
- [ ] Commit the task scope.

### Task 2: Reduced coverage checkpoints and safe continuation
**Files:** Create src/online_coverage_checkpoint.py; modify src/online_us_universe.py, src/online_sec_receipt.py, src/online_research_coverage.py; tests/test_online_coverage_checkpoint.py and tests/test_online_us_universe.py.
**Interfaces:** load_coverage_checkpoint(path) returns validated state plus checkpoint digest; save_coverage_checkpoint(path,state,*,expected_digest) atomically saves explicit local audit state. CLI accepts --checkpoint and --resume plus bounded --batches/--scan-all. Existing inspect_next_universe_batch retains source failures and returns a paused marker on access-limited responses.
- [ ] Write tests for save/reload/resume without repeated CIK probes, corrupt/wrong-contract/wrong-inventory inputs, unrelated/symlink/canonical paths,0600/backup/atomic rollback/concurrent digest conflicts and source-access pause.
- [ ] Run python3 -m pytest tests/test_online_coverage_checkpoint.py tests/test_online_us_universe.py -q; Expected: new assertions fail.
- [ ] Implement reduced schema/digest validation, POSIX locking and atomic persistence, source-limit propagation and resumable CLI with full denominator retention.
- [ ] Run python3 -m pytest tests/test_online_coverage_checkpoint.py tests/test_online_us_universe.py tests/test_online_research_coverage.py tests/test_online_sec_receipt.py -q; Expected: all pass.
- [ ] Commit the task scope.

### Task 3: Workbench/Discover integration, issuer continuation and release
**Files:** Create src/sec_exact_filing_view.py; modify src/dashboard.py, src/online_us_universe_view.py, README.md, ROADMAP.md, docs/ONLINE_COMPANY_RESEARCH.md, docs/ONLINE_RESEARCH_COVERAGE.md; tests/test_sec_exact_filing_view.py and tests/test_online_us_universe_view.py.
**Interfaces:** get_company_filing_preview(ticker,state,*,period_kind,refresh_requested,user_agent,...) is ticker/period-scoped; filing_preview_html(packet,ticker,period_kind) renders only validated personal inspection. Discover offers explicit save/restore reduced progress using the checkpoint contract.
- [ ] Write failing behavior tests for no-fetch rerenders, company switches, personal-only cache boundaries, source/rights/period labels and phone reflow.
- [ ] Implement compact source-bound filing views and explicit save/restore controls, keeping Companyfacts counters and readiness separate.
- [ ] Run focused source/UI/coverage tests; Expected: all pass.
- [ ] Measure a substantial continued issuer tranche from a valid checkpoint; record failures/unprobed and stop at access limits. Source-derived checkpoints stay local.
- [ ] Verify actual desktop/phone/narrow filing and restored-coverage flows; Expected: no overflow, incorrect entity or mixed duration/currency.
- [ ] Run wording/staged hygiene/whitespace checks and commit only code/tests/neutral documentation.
- [ ] Fresh whole-branch independent review; fix Important/Critical findings with RED-to-GREEN regressions.
- [ ] Run make test on the final committed SHA; Expected: complete suite and no-write guard pass. Keep ongoing source checkpoints outside protected roots during this run.
- [ ] Verify protected hashes and exact remote head; push authorized feature branch, archive private evidence and held PR draft.
