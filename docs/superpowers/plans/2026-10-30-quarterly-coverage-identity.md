# Quarterly Coverage and Identity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add source-bound quarterly research, measured cross-industry financial coverage and a qualified price/SEC listing association, then synchronize passing code to the existing work branch.

**Architecture:** Pure evidence builders and validators sit outside the dashboard. Explicit actions fetch bounded SEC receipts and reuse one Companyfacts response; a bounded study shares the SEC ticker map. Session-only views retain source context and independent holds.

**Tech Stack:** Python, urllib, Streamlit, pytest, Playwright; no new dependency or paid source.

**Spec:** `docs/superpowers/specs/2026-10-30-quarterly-coverage-identity-design.md`

## Global Constraints

- Preserve canonical data, readiness, credentials and source-rights decisions.
- No PR, merge, deployment, purchase or publication is included.
- Default page renders make no new network request.
- No fuzzy company-name join is permitted.
- Values are latest reported as observed, including revisions, rather than historical point-in-time evidence.

## Review Focus

- Partial-year cumulative facts must never become single-quarter financial values.
- A later revision or malformed latest row must not silently fall back to an older successful value.
- Share classes, multiple SEC exchanges and provider venue aliases must not produce an unqualified issuer join.
- Missing or failed industry observations must remain in the sample denominator.
- Optional identity/profile failure must not suppress valid sibling annual, quarterly or price evidence.

### Task 1: Bounded receipts and quarterly evidence

**Files:** create `src/online_sec_receipt.py`, `src/sec_quarterly_history.py`, `tests/test_online_sec_receipt.py`, `tests/test_sec_quarterly_history.py`; modify `src/sec_annual_history.py` and its integration tests.

**Interfaces:** `fetch_sec_json_receipt(url, *, user_agent, fetcher=None, observed_at=None)` returns an in-memory payload and exact source receipt; `build_sec_quarterly_history(ticker, payload, *, expected_cik, observed_at, source_url, payload_sha256, anchor_concept=None)` returns validated direct/cumulative period evidence. The existing SEC wrapper attaches `companyfacts_identity` and `quarterly_history` without canonical inputs.

- [ ] Write and run failing tests for bounded receipts, exact source/identity/context, quarterly values, cumulative separation, ambiguity, mixed units and malformed raw facts. Expected: feature assertions fail before implementation.
- [ ] Implement receipt and quarterly contracts, integrate the shared response and validate at the display boundary. Expected: focused quarterly, annual and preview tests pass without network or CSV reads in synthetic cases.
- [ ] Commit the independently verified core after its focused checks. Expected: no generated data is staged.

### Task 2: SEC profile and price listing association

**Files:** create `src/online_company_identity.py`, `tests/test_online_company_identity.py`; modify `src/online_company_prices.py` and price tests.

**Interfaces:** `fetch_sec_company_profile(cik, *, user_agent, fetcher=None, observed_at=None)` retains SEC SIC/tickers/exchanges and receipt; `build_price_filing_association(ticker, financial_identity, prices, profile)` returns a qualified association or explicit reason. `get_price_filing_association` adds explicit-action, ticker-scoped session reuse.

- [ ] Write and run failing tests for exact CIK/symbol/venue, class alias, multi-venue ambiguity, missing vendor identifier, stale observations, mode isolation and profile failure. Expected: feature assertions fail.
- [ ] Implement personal-inspection metadata and qualified linkage; preserve independent financial/price results. Expected: identity and price checks pass with no writes or implicit refresh.
- [ ] Commit the verified identity path. Expected: rights/config/data untouched.

### Task 3: Coverage study and research UI

**Files:** create `src/online_research_coverage.py`, `src/online_research_expansion_view.py` and focused tests; modify dashboard, research guide, README and roadmap.

**Interfaces:** `summarize_online_research_coverage(observations, requested_tickers)` retains all attempts; `run_online_coverage_study(tickers, *, user_agent, ...)` serializes at most twenty explicit requests using a shared map. Pure HTML functions render quarterly, association and coverage evidence.

- [ ] Write and run failing coverage/UI tests, including failure denominators, latest-period holds, unknown SIC, cached action behavior and real Streamlit HTML composition at desktop/phone/narrow widths. Expected: feature assertions fail.
- [ ] Implement explicit Workbench evidence and Discover study actions; add the read-only study CLI and neutral documentation. Expected: focused integration/browser/wording checks pass.
- [ ] Run bounded live cross-industry checks and per-company association checks, record actual gaps locally and obtain one fresh whole-change review. Expected: no fabricated coverage or identity approval; findings resolved or explicitly held.
- [ ] Run complete `make test` with no concurrent repository artifact writes, then staged hygiene and protected hashes. Expected: exit 0, unchanged canonical/rights digests.
- [ ] Commit verified code/docs/tests, verify remote ancestry, push normally to the existing work branch and verify the exact remote SHA. Preserve local evidence and held PR draft. Expected: clean synchronized worktree, no PR/merge/deploy.
