# Security Types and IBN Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement task-by-task. Steps use checkbox syntax.

**Goal:** Source-labelled listing/issuer classifications, a bounded IBN annual HTML financial path, and completion of the saved issuer queue.
**Architecture:** Separate classification observations from financial availability; separate HTML-bank packets from Inline XBRL. Shared exact-source transport, personal-only sessions and unchanged canonical/readiness gates.
**Tech Stack:** Python, standard HTMLParser/Decimal, existing Streamlit/pytest/Playwright; no new dependencies.
**Spec:** docs/superpowers/specs/2026-10-31-security-types-ibn-design.md

## Global Constraints
- Exact official sources, dates/digests,32MiB/30s/no redirects; unregistered personal inspection only.
- No canonical/right-registry changes, financial coverage promotion, source-data fixtures, price joins, unsupported arithmetic or eligibility inference.
- Preserve all5954 coverage candidates and original3100 observations; private census checkpoint stays outside protected roots during tests.
- Explicit actions only; source-specific caches validated and ticker-scoped;1280/390/195 browser widths.
- Code/tests/neutral docs only in Git. Branch push authorized; PR/merge/deploy/publication/purchase/credentials not authorized.

## Review Focus
- Underlying-equity words in warrant/unit/depositary/preferred descriptions must not misclassify primary instruments; conflicting descriptions remain unknown (Task1).
- Investment-company or annual filing forms must never become security type, domicile or financial eligibility; ambiguous CIK/class associations hold (Task1).
- IBN rounded summaries, standalone statements, translation columns, note numbers, row spans and negative purchase signs must not become consolidated direct facts (Task2).
- New malformed/tied amendments or unsupported formats must never restore an older filing; source/currency/period changes hold (Task2).
- Personal caches, company switches, restored snapshots and new UI buttons must not leak/fetch/promote or break existing route contracts (Task3).

### Task 1: Source-labelled listing classification and issuer profiles
**Files:** Create src/security_classification.py and tests/test_security_classification.py.
**Interfaces:** classify_description(name,etf) -> type/rule/reason; build_classification(inventory,directory_rows) -> versioned packet; validated_classification(packet) -> packet/None; fetch_classification(user_agent,fetcher=None) -> dated packet; issuer_profile(cik,receipt) -> independent reporting profile; get_company_security_context(ticker,state,refresh_requested,user_agent,expected_cik) -> scoped context.
- [ ] Write failing tests for all categories, composites/unknowns, duplicate identities, source-binding/digest edits, issuer-profile independence, commercial and cache isolation.
- [ ] Run pytest tests/test_security_classification.py -q; Expected: new feature assertions fail.
- [ ] Implement bounded official-source observations and validation; SEC-only issuer names stay unclassified.
- [ ] Run the same tests; Expected: all pass. Capture live full observed classification privately.
- [ ] Commit, then task-done with the same suite.

### Task 2: IBN consolidated annual HTML-table evidence
**Files:** Create src/sec_html_bank.py and tests/test_sec_html_bank.py; modify src/sec_exact_filing.py and tests/test_sec_exact_filing.py.
**Interfaces:** extract_bank_html(raw,selection,receipt) -> sec-html-bank-v1 packet/held; validated_bank_html(packet,ticker,period_kind) -> packet/None. select_sec_filing adds allow_non_inline=False; fetch enables it only for IBN annual and dispatches by selected adapter. Existing validation delegates only the separate source ID.
- [ ] Write synthetic failing tests with issuer cover, consolidated captions, actual anchor patterns, INR-thousands and dated spans; assert scaled direct values and purchase sign.
- [ ] Add malformed/tied publication, currency/basis/period, duplicate row/anchor, nested/rowspan/header ambiguity, summary/standalone rejection and cache tampering cases.
- [ ] Run pytest tests/test_sec_html_bank.py tests/test_sec_exact_filing.py -q; Expected: new assertions fail.
- [ ] Implement strict table extraction and separate packet validation with source coordinates; keep unsupported fields held.
- [ ] Run that suite plus existing Inline XBRL tests; Expected: all pass. Replay exact live IBN source into private evidence.
- [ ] Commit and task-done.

### Task 3: Explicit UI, docs, census completion and release
**Files:** Create src/security_classification_view.py; modify src/sec_exact_filing_view.py, src/dashboard.py, README.md, ROADMAP.md, docs/ONLINE_COMPANY_RESEARCH.md, docs/ONLINE_RESEARCH_COVERAGE.md; matching view, AppTest and documentation contracts.
**Interfaces:** classification_html(packet) and company_security_html(context) render source-labelled independent observations; filing_preview_html dispatches bank packet to separate qualified cards.
- [ ] Write failing UI tests for personal-only no-fetch default, source/unknown labels, bank field definitions, responsive layout and exact button contracts.
- [ ] Implement explicit Discover/classification and selected-company actions; keep full census and classification source dates separate.
- [ ] Run focused source/view, full public-v1 docs and affected AppTest suites; Expected: all pass.
- [ ] Verify saved census completion or exact source-access blocker; prove original3100 unchanged and no duplicate CIKs.
- [ ] Run actual1280/390/195 browser checks with IBN and classification; verify geometry/identity/units.
- [ ] Commit code/tests/neutral docs; one fresh whole-task reviewer, then RED-to-GREEN Important/Critical repairs only.
- [ ] Run final make test and no-write guard; Expected: complete pass. Save default checkpoint only afterward.
- [ ] Audit hashes/range hygiene, archive local evidence and held PR draft; push developer branch, verify remote head/main/CI state, preserve worktree.
