# Research Scope and Valuation Clarity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Make company research paths and peer valuation understandable while adding exact bank income evidence without unsupported conclusions.
**Architecture:** Pure source-bound projections and strict comparison contracts; thin Streamlit composition. Existing parser guards serve a separate bank schema. Existing population, canonical data and readiness stay intact.
**Tech Stack:** Python, Streamlit, standard-library XML/HTML, pytest, IAB browser.
**Spec:** docs/superpowers/specs/2026-10-31-research-scope-valuation-design.md

## Global Constraints

- Reuse the existing isolated codex/next-stage-truth-20261029 worktree; task base b5cef3db4bcd42ae92291394fd0870e3a71c5b1c.
- Preserve data/fundamentals.csv, data/reports/ticker_readiness_report.csv, config/source_rights.yml and the5954candidate checkpoint.
- Source dates, units, periods, rights, identities and unknowns remain explicit; no readiness or universe-counter promotion.
- Personal Research only for new inspection; no source fetch on rerender and no canonical writes.
- Full make test and actual1280/390/195 browser checks precede authorized branch push; no PR/merge/deploy/publish/purchase/credentials changes.

## Review Focus

- Conflicting wrapper and issuer observations remain separate; a fund or warrant never becomes an ordinary-company valuation solely from its ticker.
- Forged bank classification, changed CIK or receipt cannot activate the bank parser schema.
- Peer aggregate counts never substitute for per-metric contributing observations; duplicate/self peers and nonpositive inputs cannot imply a cheap valuation.
- Missing/contradictory financial basis, price dates, references or rights withhold the affected metric, including when old readiness says ready.
- Company switch, stale/failed cache and illustrative examples cannot leak values into another company's primary answer.

### Task 1: Source-bound research paths
**Files:** Create src/company_research_scope.py and tests/test_company_research_scope.py; modify src/security_classification_view.py and its tests.
**Interfaces:** research_scope(context,ticker) -> dict; research_scope_html(result) -> str; consumes validated_company_context, does not mutate it.
- [ ] Write test_fund_bank_blank_check_and_operating_profiles_have_distinct_paths; assert path literals and eligibilityFalse.
- [ ] Write test_wrapper_does_not_become_underlying_company and test_invalid_or_switched_context_is_unresolved; assert no inferred eligibility.
- [ ] Run tests; Expected: RED for missing module.
- [ ] Implement pure projection and add it to selected-company security details with scoped responsive markup.
- [ ] Run pytest tests/test_company_research_scope.py tests/test_security_classification_view.py tests/test_security_classification.py -q; Expected: pass.
- [ ] Commit code/tests/spec/plan and record task result.

### Task 2: Exact bank income context
**Files:** Modify src/sec_inline_filing.py, src/sec_exact_filing.py, src/sec_exact_filing_view.py; create tests/test_sec_inline_bank_context.py.
**Interfaces:** bank schema sec-exact-bank-context-v1; bank source sec_archive_inline_bank; existing generic signatures remain compatible. Selection attaches bank_scope with CIK/SIC and same submissions receipt. Parser emits six field slots with unsupported fields held; validator selects matching schema/catalog.
- [ ] Write test_bank_income_anchor_does_not_invent_revenue; use synthetic XML with no revenue and direct net interest50/noninterest20, verify reported fields and revenue hold.
- [ ] Write bank classification/receipt/CIK/currency/period conflict and conflicting numeric tests; Expected: RED before implementation.
- [ ] Add separate bank catalog/anchor and validated classification binding without relaxing generic parser rules.
- [ ] Show bank-specific labels and definition warning in exact-filing cards.
- [ ] Replay captured FITB exact source; retain bytes/digests/selection/packet privately. Expected: direct bank fields, generic revenue held, no canonical/count change.
- [ ] Run pytest tests/test_sec_inline_bank_context.py tests/test_sec_inline_filing.py tests/test_sec_exact_filing.py tests/test_sec_exact_filing_view.py tests/test_sec_html_bank.py -q; Expected: pass; commit and record.

### Task 3: Primary valuation explanation and release
**Files:** Create src/company_valuation_overview.py and tests/test_company_valuation_overview.py; modify src/dashboard.py, matching AppTest, README.md, ROADMAP.md and online research docs.
**Interfaces:** build_valuation_overview(ticker,report_payload=None) -> dict; valuation_overview_html(view) -> str; render_single_stock_report receives optional selected_valuation_target. Online pages use explicit withheld state; real report values require per-metric comparison_inputs evidence and existing quant/readiness gates.
- [ ] Write test_compatible_peers_show_hand_checked_median_and_premium; subject30x/peers20x,25x,40x => median25x,premium20%,threecontributors.
- [ ] Write tests for distinct metric coverage, self/duplicate/two peers, negative/zero/nonfinite/bool values, mixed basis/period/currency/price date, missing rights/references, ticker switch, stale quant and funds. Expected: RED.
- [ ] Implement strict per-metric comparison with clear source/reason records; synthetic illustration remains isolated and labelled.
- [ ] Integrate primary summary into saved and online-only company paths; keep one H1 and existing explicit source actions.
- [ ] Run focused views, source tests, AppTest and existing docs contracts; Expected: pass.
- [ ] Capture before/after IAB screenshots for saved AMD, online FITB, fund and illustrative disclosure at1280/390/195; inspect geometry and meaningful controls; save local audit.
- [ ] Commit final implementation; one fresh whole-task reviewer, one RED/GREEN repair pass for Important/Critical findings.
- [ ] Run final make test on committed head after stopping test server; Expected: complete pass and unchanged artifact guard.
- [ ] Verify protected hashes/checkpoint unchanged; archive source/release evidence and held PR draft; push developer branch, verify exact remote/main/CI status; preserve worktree and unrelated files.
