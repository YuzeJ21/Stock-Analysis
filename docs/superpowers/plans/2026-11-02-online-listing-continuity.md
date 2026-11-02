# Online listing continuity implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep the online company workflow usable during temporary listing-source failures with explicit, original-dated session receipts.

**Architecture:** A focused session helper validates complete classification packets, selects a dated receipt after an unavailable acquisition and derives disclosure context. Existing valuation rules remain authoritative. Source acquisition records bounded diagnostics, without hidden retry or disk persistence.

**Tech Stack:** Python, existing Streamlit compositor, pytest and in-app browser.

**Spec:** docs/superpowers/specs/2026-11-02-online-listing-continuity-design.md

## Global Constraints

- No new dependencies, credentials, disk source cache, source approval, canonical writes or readiness updates.
- Preserve four-source observation freshness: 0 through 24 hours inclusive. Directory creation: 0 through seven days inclusive.
- No automatic network retries; source exceptions never expose messages or headers.
- Existing financial, identity, rights and minimum-three reference gates remain authoritative.
- User already requests execution without human testers; implement inline and use one independent final review.

## Review Focus

- A failed fresh financial update must withdraw the old valuation even when listing recovery succeeds.
- Future, expired or tampered classification cannot reach issuer transport through recovery.
- A malformed nominally successful classification must not be treated as an access failure.
- Reusing listing evidence must not relabel its original source dates as this attempt.
- Switching ticker or expected CIK must recheck identity before vendor/price transport.

### Task 1: Strict primitive SEC contexts

**Files:** Modify src/sec_selected_security.py and src/sec_security_observations.py; extend tests/test_cross_security_evidence.py and tests/test_security_inspection_observations.py.

**Interfaces:** Existing exact-source validators retain signatures and outputs; identifier/start/end nodes must be leaves.

- [ ] Add resealed nested identifier/start/end negatives; require subject withdrawal and inspection rejection.
- [ ] Run new tests and observe RED from accepted malformed primitives.
- [ ] Add minimal leaf guards without numeric-parser changes.
- [ ] Run `python3 -m pytest -q -p no:cacheprovider tests/test_cross_security_evidence.py tests/test_security_inspection_observations.py tests/test_sec_selected_security.py tests/test_bank_peer_security.py`; expected all pass.
- [ ] Commit the strict-context change.

### Task 2: Dated session recovery and visible acquisition evidence

**Files:** Create src/online_listing_session.py and tests/test_online_listing_session.py. Modify src/security_classification.py, src/online_peer_sources.py, src/online_peer_coverage.py, src/online_peer_valuation_ui.py and src/company_workbench_ui.py. Extend their existing tests.

**Interfaces:** `fresh_classification(packet, as_of)` returns a revalidated packet or None. `acquire_classification(state, fetch, *, as_of)` returns `(packet_or_none, disclosure)` and stores only the last validated packet in a versioned sealed session envelope. Collector cache can retain optional listing disclosure separately from the financial collection.

- [ ] Write tests for empty directory diagnostics; recent receipt recovery with new financial collection; no prior/expired/future/tampered/malformed-success recovery; 24-hour boundary; seven-day creation boundary; unchanged packet dates/digests; CIK/mode withdrawal; live replacement; no-fetch renders; financial failure after recovery withdraws verdict.
- [ ] Run new tests; expected missing recovery/diagnostic assertions fail.
- [ ] Implement the focused helper and collector integration, shared freshness validation and sanitized per-source acquisition diagnostics. Do not add retry or file I/O.
- [ ] Add failing UI tests for distinct attempt/listing dates, visible reuse/failure, safe source links and source-pane reuse with no hidden fetches; implement within existing components.
- [ ] Run listing, collector, coverage, valuation and integrated Workbench focused suites; expected all pass.
- [ ] Commit the recovery change.

### Task 3: Product decision, release evidence and exact-head verification

**Files:** Update ROADMAP.md and docs/ONLINE_PEER_VALUATION.md. Add docs/PRODUCT_REVIEW_2026-11-02.md and docs/goals/ONLINE_RESEARCH_NEXT_STAGES.md with market source links, tradeoffs, ordered exit gates and reusable goal.

**Interfaces:** Private outputs/local packet records exact commit/results/source dates, protected hashes, browser capture provenance, unresolved gates and held PR text. Public docs contain neutral descriptions, no source-derived reports.

- [ ] Record review of Discover → Company → valuation → sources from current screenshots and current official competitor pages. Distinguish observed product behavior from positioning hypotheses.
- [ ] Update roadmap to prioritize continuity and reproducible company review, then bounded coverage and separately qualified metrics.
- [ ] Run focused docs/hygiene checks; expected pass. Commit documentation.
- [ ] Obtain one independent whole-stage code review; fix Critical/Important findings by RED/GREEN. Record deferred minors.
- [ ] Check desktop/phone returned, recovered and expired/blocked states in the real compositor, labelled synthetic for controlled outage cases; retain one actual live acquisition result without inventing recovery if no live session receipt exists.
- [ ] Run guarded `make test` sequentially on final committed code; expected exit zero, with actual skips/warnings reported.
- [ ] Verify protected hashes and clean diff. Seal private packet, synchronize authorized developer branch and verify exact remote SHA; main, PR, merge, deployment and source rights remain separate.
