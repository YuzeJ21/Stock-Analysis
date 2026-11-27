# ECB Reference and SAP Currency Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement task-by-task.

**Goal:** Capture exact public FX evidence and provide a separate historical ordinary-share currency translation.
**Architecture:** Bounded source adapter, pure Decimal review, explicit session-scoped UI; source acquisition is separate from offline release checks.
**Tech Stack:** Python standard library, existing Streamlit and pytest/Playwright; no new dependencies.
**Spec:** docs/superpowers/specs/2026-11-27-sap-fx-review-design.md

## Global Constraints
Fixed ECB URL, one request, 20-second timeout, 2 MiB maximum; no retries/credentials.
No original snapshot writes, private source upload, P/E, ADS mapping, peer/readiness,
commercial, source-authentication or point-in-time eligibility promotion.
Keep the existing minimal engineering workflow offline; source acquisition is PR-open only.
Keep original and later retrieval/review times distinct. Use exact original price date.

## Review Focus
- Hostile XML/duplicate observations: Task 1 malformed, namespace, sender, DTD, oversized, date/rate tests.
- Wrong direction or mutated receipts: Task 1 parse contract and Task 2 raw reparse/resealed metadata tests.
- Historical cutoff leakage: Task 2 later retrieval is explicitly ineligible for point-in-time use; future review fails.
- Session/profile mixup or auto-fetch: Task 3 real UI rerender/scope tests with transport replaced at its boundary.
- Download/publication scope: Tasks 1/3 output allowlist and ZIP exclusion of private notes/profile/context.

### Task 1: Exact public FX source adapter and capture command
Files: create src/ecb_fx_reference.py, tests/test_ecb_fx_reference.py and
.github/workflows/ecb-reference-capture.yml.
Interfaces: parse_ecb_usd(raw, *, reference_date, observed_at, last_modified=None)
returns normalized receipt or raises ValueError; capture_ecb_usd(reference_date,
*, fetcher=None, clock=None) returns {status,receipt,xml:bytes} or withheld.
CLI main(argv=None, *, fetcher=None, clock=None) writes only fixed public files
into a fresh explicit disposable output directory; exit 0 on captured, 2 on held.
- [x] Write RED exact-decimal/date/size/XML and transport-mode/redirect tests.
- [x] Implement bounded fetch and source parser; test original byte digest and literal precision.
- [x] Test CLI allowlist, no clobber, guarded canonical destinations and honest held output.
- [x] Add separate same-repo PR-open-only capture workflow for 2026-11-23; upload only three named public files with upload-artifact@v7.
- [x] Run focused tests, inspect source/workflow scope, commit.

### Task 2: Separate historical conversion and inspectable package
Files: create src/sap_fx_review.py, tests/test_sap_fx_review.py.
Consumes Task 1 packet/receipt and assess_sap_price_basis(context).
Produces build_sap_fx_review(context,capture,*,reviewed_at) JSON-safe held/derived
review and currency_review_zip(context,capture,*,reviewed_at) downloadable bytes.
- [x] Write RED hand-calculated EUR6.10 × USD/EUR1.2500 = USD7.625000 per ordinary share.
- [x] Test raw/receipt mismatch, wrong date/unit, future times and late retrieval without original-context mutation.
- [x] Implement exact Decimal computation and minimal source/context-digest provenance; all eligibility false.
- [x] Test ZIP contains only fx.xml,receipt.json,SOURCE.txt,review.json, with no original notes/profile IDs.
- [x] Run source/review/source-store regressions; commit.

### Task 3: Explicit UI action and actual acquisition verification
Files: create src/sap_fx_review_ui.py, tests/test_sap_fx_review_ui.py,
tests/test_sap_fx_review_browser.py; modify current/historical UI callsites,
.github/workflows/commercial-research-beta.yml to add offline tests, ROADMAP.md;
create docs/SAP_FX_REFERENCE_RELEASE.md.
Consumes Tasks 1/2; produces render_sap_fx_review(st,context,*,fetcher=None,clock=None).
- [x] Write RED no-action/no-fetch, explicit fetch, rerender/cache, scope-change, held and download tests.
- [x] Implement closed expander, explicit action, exact-context cache and safe recomputed projection/download; no Monitor fetch.
- [x] Add desktop/phone source-inspection/download assertions without weakening existing save/Monitor/no-fetch checks.
- [x] Run focused integration, wording/range/whitespace/protected manifest checks.
- [x] Obtain independent final review and fix material findings with RED/GREEN in one pass.
- [ ] Sync fixed committed tree as a draft PR; inspect separate acquisition receipt/artifact and current-head browser/journey/full CI.
- [ ] Reuse captured source bytes to review actual retained SAP context at its original dates, reporting later retrieval honestly; record remaining external gates.

Local execution and one material-review fix pass completed; 503 focused checks pass.
Actual acquisition and current-head browser/full CI remain required.
