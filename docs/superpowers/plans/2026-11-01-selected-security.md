# Selected Security and Peer Coverage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Qualify exact DUK/JPM selected-common evidence and expose the remaining NEM/TSM/XOM gaps without weakening annual peer rules.

**Architecture:** Isolated byte-bound source scopes supplement current listing observations. A separate bounded historical SEC identity match never alters annual financial selection. Existing company/coverage presenters consume recomputed source evidence.

**Tech Stack:** Existing Python/pytest/Streamlit/SEC adapters; no dependency additions.

**Spec:** docs/superpowers/specs/2026-11-01-selected-security-design.md

## Global Constraints

- Personal Research only; preserve canonical financials/readiness/source rights/5954candidate checkpoint and unrelated work. No paid source, credentials changes, PR/merge/deploy/publication.
- Exact source policies only;32MiB/document, exact URL/no redirects, <=24h freshness. No real numeric EPS fixtures or raw sources committed. Literal selected common identity; raw other symbols stay unassigned.
- Validated profile projection <=50000raw rows; retain all relevant periodic/cover/investment-company rows, no blind truncation. Financial selector <=2000projected rows.
- Historical vendor identity: <=1archive,<=100current pointers,<=50000rows,<=2MiB retained JSON. Unique pointer and exact target, raw reparse; never merge old metadata into current annual selection.
- Existing3peer/12candidate/SIC/fiscal/price/currency/split/source-pause rules and no hidden network remain. Separate selected security/issuer domicile/activity/financial eligibility/point-in-time coverage.

## Review Focus

- TSM Common Shares DEI title with nontrading footnote must never enter ordinary P/E.
- New annual/8-K, changed sibling sets, raw aliases or mixed-context facts must not revive old scope.
- Malformed large recent metadata and omitted investment-company forms cannot be silently discarded.
- A valid old vendor filing cannot become the latest annual denominator or conceal a newer amendment.
- Invalid/stale sources, failed retry and cached/resealed proof must withhold without hidden refresh or canonical writes.

---

### Task 1: Exact selected-security proof and source/core integration

**Files:** Create src/sec_selected_security_policies.py, src/sec_selected_security.py, tests/selected_security_fixtures.py, tests/test_sec_selected_security.py; modify src/online_peer_sources.py, src/online_peer_valuation.py and their tests.

**Interfaces:** fetch_selected_security_evidence(ticker,cik,profile,*,user_agent,fetcher=None,observed_at=None,workspace_mode='research')->dict; validate_selected_security_evidence(packet,*,ticker,cik,profile,issuer_symbols,as_of)->dict returns supported_common with direct annual EPS + source scopes for DUK/JPM; inspection_only with explicit reason for NEM/TSM/XOM. Optional issuer row.selected_security_evidence. Supported observation becomes subject.selected_security_scope; blocked observations become subject_source_context.selected_security_scope.

- [ ] Synthetic proof tests: literal common success/EPSagreement, raw other symbols retained; missing/changed hash, metadata/new version/sibling set, context/units/dimension/duplicate conflicts, stale/future/ticker/CIK/source URL/redirect/size/mode, raw cache tamper; general DEI false-common TSM-like inspection remains held.
- [ ] Run python3 -m pytest tests/test_sec_selected_security.py -q; Expected: missing-feature RED.
- [ ] Implement source-bound proof, profile projection and optional proof consumer. Keep legacy path unchanged without proof. Source reduction must preserve unknown malformed metadata as a hold; allow inspection collection only for exact declared scope pairs.
- [ ] Run python3 -m pytest tests/test_sec_selected_security.py tests/test_online_peer_sources.py tests/test_online_peer_valuation.py tests/test_online_peer_coverage.py -q; Expected: GREEN. Replay saved official sources privately with original observations.
- [ ] Commit; complete task with the same focused command.

### Task 2: Bounded archived SEC vendor identity

**Files:** Create src/online_peer_sec_history.py and tests/test_online_peer_sec_history.py; modify src/online_sec_receipt.py, src/online_peer_sources.py, src/online_peer_valuation.py and relevant tests.

**Interfaces:** fetch_vendor_history_match(cik,profile,vendor,*,user_agent,fetcher=None,observed_at=None)->dict; validated_vendor_history_match(packet,*,cik,profile,vendor,as_of)->list exact matched historical metadata only. Optional issuer row.vendor_history. Profile retains filings.files, validated source references separately from current recent.

- [ ] Synthetic tests: exact older match succeeds independently, latest annual EPS unchanged; unique pointer/target, wrongCIK/date/filename/columns/digest/bytes/freshness, unavailable/oversize/redirect, at-most-one archive and no transport if already matched; recent huge projection retains fund/new amendments, malformed columns hold.
- [ ] Run python3 -m pytest tests/test_online_peer_sec_history.py -q; Expected: missing-feature RED.
- [ ] Implement strict archive URL allowlist and explicit fetch/read validation. Never append archive rows to financial recent. Preserve existing vendor conflict checks.
- [ ] Run python3 -m pytest tests/test_online_peer_sec_history.py tests/test_sec_selected_security.py tests/test_online_sec_receipt.py tests/test_online_peer_sources.py tests/test_online_peer_valuation.py -q; Expected: GREEN.
- [ ] Commit; complete with same command.

### Task 3: Source explanation, measured coverage and delivery

**Files:** Modify src/online_peer_valuation_ui.py, src/online_peer_coverage.py, relevant UI/coverage tests, ROADMAP.md, docs/PEER_COVERAGE_METHOD.md and docs/ONLINE_PEER_VALUATION.md.

**Interfaces:** Existing presenters show recomputed selected_security_scope evidence, current/historical vendor-source roles, raw sibling sets and explicit gaps in valuation/sources/industry sample. New coverage method reported-annual-pe-selected-security-v1 requires explicit reset of old audit state.

- [ ] UI tests: scope does not promote withheld NEM/TSM/XOM; original/current document refs, publication/observation/digests, unassigned siblings, history identity vs annual denominator, escaping and no pane-read network.
- [ ] Run python3 -m pytest tests/test_online_peer_valuation_ui.py tests/test_online_peer_coverage_ui.py tests/test_online_peer_coverage.py tests/test_sec_selected_security.py tests/test_online_peer_sec_history.py tests/test_integrated_company_workbench.py -q; Expected: RED for missing presenter behavior, then GREEN.
- [ ] Explicitly refresh5blocked targets with production sources; revalidate10other saved packets preserving observations; compare counts/reasons against prior15target evidence. No full-US claim.
- [ ] Commit. One fresh independent whole-stage review; regrade effects, fix Important/Critical once through RED->GREEN; ledger all declined judgments and deferred Minors.
- [ ] Capture exact-head desktop/phone5target valuation/source states plus sample outcomes using labelled real saved-source replay and real online refresh. Stop only owned previews; run guarded full suite once at final head through task-done; Expected: exit0 with exact counts/skips/warnings.
- [ ] Verify public wording/protected hashes/source-only diff/clean worktree, normal tested-head developer push and remote/API equality. Hosted CI separate. Restore real preview and deliver private rights/source/browser/review/localPRdraft packet; archive scratch before removing only this plan directory.
