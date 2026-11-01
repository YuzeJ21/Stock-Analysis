# Online Peer Valuation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect an online, source-bound annual P/E industry comparison to Company Workbench with transparent dates, sources and missing reasons.

**Architecture:** A pure evidence validator/calculator consumes bounded source collections. An explicit-action collector reuses listing, SEC and daily-price adapters and adds normalized vendor context/filing observations. One presenter serves both the valuation answer and Sources disclosure, separately from saved models.

**Tech Stack:** Existing Python, Streamlit, yfinance, pytest/AppTest and automated browser tooling; no dependency installation or credential changes.

**Spec:** `docs/superpowers/specs/2026-11-01-online-peer-valuation-design.md`

## Global Constraints

- Reuse current linked worktree and branch; preserve unrelated files and canonical data.
- Personal Research only; no source-rights approval, saved readiness or coverage promotion.
- Annual GAAP diluted EPS, USD/shares; 350–380 days; financial age at most550 days; boundary tolerance35 days; same completed price date within7 days; source observations within24 hours.
- At least3 distinct accepted peers, at most12 other candidates. Explicit refresh only, failures cached and revalidated.
- No ADR/FX/split/TTM/adjusted-earnings inference, overall valuation score or recommendation.
- Automated tests and desktop/phone checks; no human testing. Authorized developer-branch push only, no PR/merge/deployment/publication/purchase/credential change.

## Review Focus

- Filing-agent accession prefixes differ from issuer CIK; resolve issuer from the vendor link and independent metadata (Task1).
- Latest annual amendments or tied/conflicting EPS may lack a usable value; do not fall back silently (Task1).
- Quote/bar dates, intraday observations and post-period splits can make a plausible ratio invalid (Task1).
- Cached successes must not survive a failed explicit retry, identity change, stale source or commercial-mode transition (Task2).
- Online results and source disclosure must not merge with saved scenario qualification, records or another company's data (Task3).

### Task 1: Source validation and comparison

**Files:** Create `src/online_peer_valuation.py`, `tests/test_online_peer_valuation.py`.

**Interfaces:** Consumes a collection with classification, industry receipt and issuer source packets. Produces `build_online_peer_valuation(collection, *, ticker, expected_cik=None, as_of=None) -> dict`, immutable source-derived observations, included/excluded peers and numeric comparison only after all guards pass.

- [ ] Write synthetic-source tests for hand-checked median/premium and all five relevant evidence failure classes above, including exact boundary cases and no input mutation.
- [ ] Run `python3 -m pytest tests/test_online_peer_valuation.py -q`; expected RED: missing implementation.
- [ ] Implement pure validation, independently bound issuer filing identity, exact annual EPS selection and declared fiscal-window comparison. No I/O or approvals.
- [ ] Run `python3 -m pytest tests/test_online_peer_valuation.py tests/test_company_valuation_overview.py tests/test_security_classification.py tests/test_online_company_prices.py -q`; expected all pass.
- [ ] Commit the independent evidence/calculation component.

### Task 2: Bounded online acquisition and session reuse

**Files:** Create `src/online_peer_sources.py`, `tests/test_online_peer_sources.py`.

**Interfaces:** Produces `get_online_peer_valuation(ticker, state, *, refresh_requested, expected_cik=None, user_agent=None, dependencies=None, as_of=None) -> dict`; consumes Task1 builder. Injectable dependency functions support deterministic transport tests without real source data fixtures.

- [ ] Write RED tests for no-action/no-transport, candidate bound, unknown/duplicate/failed sources, malformed vendor fields, fresh successful and failed cache replacement, stale/tampered cache, ticker/CIK changes and mode guards.
- [ ] Run `python3 -m pytest tests/test_online_peer_sources.py -q`; expected RED.
- [ ] Implement normalized vendor observations through public installed SDK methods, official listing/SEC receipts, existing prices, explicit refresh and source-scoped failures. Preserve source dates/digests and distinguish normalized/raw digests.
- [ ] Run `python3 -m pytest tests/test_online_peer_sources.py tests/test_online_peer_valuation.py tests/test_integrated_company_workbench.py -q`; expected all pass.
- [ ] Commit the bounded collector.

### Task 3: Company-page answer, source details and delivery

**Files:** Create `src/online_peer_valuation_ui.py`, `tests/test_online_peer_valuation_ui.py`; modify `src/company_workbench_ui.py`, applicable documentation and focused browser contracts.

**Interfaces:** Presenter `online_peer_valuation_html(view, *, sources_only=False) -> str` consumes Task2 validated views. Compositor owns the explicit valuation action and cached Sources reuse; saved callback signature remains unchanged.

- [ ] Write RED rendering and real AppTest tests: higher/lower/thin/error, safe source links and missing fields, current ticker, one online answer, separate saved tools and no hidden network or record writes.
- [ ] Run `python3 -m pytest tests/test_online_peer_valuation_ui.py -q`; expected RED.
- [ ] Implement the online answer and disclosures with responsive native controls, reuse Sources, preserve saved/default and online-only routes. Update roadmap and method/source documentation.
- [ ] Run focused integration/browser contracts and perform automated desktop/phone checks of the real route, including a live source-backed case and explicit blocked case. Expected clean page, readable labels, no overflow/exceptions, no pane-switch requests.
- [ ] Commit integration and neutral documentation. Prepare whole-task review package from9adb15335 and request one independent review; repair material findings with RED/GREEN evidence.
- [ ] Run `make test` sequentially with no concurrent repository/test writers; expected full guarded suite pass (retain the known absent-receipt skip).
- [ ] Verify protected data and clean delta, archive local evidence/held PR draft, push the tested developer head, verify exact GitHub head and report hosted CI separately. Preserve existing worktree and unrelated scratch; remove only this plan's archived scratch.
