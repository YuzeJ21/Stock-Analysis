# SAP Price Basis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Resolve a bounded SAP listing/price context and show remaining method holds.
**Architecture:** Pure assessment over validated normalized SAP scope and retained price metadata; one shared HTML projection for current/saved presentation.
**Tech Stack:** Python, existing Streamlit and pytest/Playwright contracts; no dependencies.
**Spec:** docs/superpowers/specs/2026-11-27-sap-price-basis-design.md

## Global Constraints
No USD EPS/P/E/peer eligibility. No new network, source rights, current-market claim,
canonical artifact write, legacy migration, generic identity relaxation or TSM change.
Reuse the existing isolated worktree on a new branch based on PR124's exact tree.

## Review Focus
- Reject currency/venue/OTC confusion: Task 1 mutation cases.
- Preserve chronological cutoff: Task 1 future/24-hour/incomplete-close cases.
- Legacy missing metadata preserves native EPS: Task 2 save/render case.
- Keep independent financial/rights holds: both tasks assert false eligibility.
- Reuse identical current/historical presentation: Task 2 UI/browser checks.

### Task 1: Dated listing/price assessment
Files: create src/sap_price_basis.py and tests/test_sap_price_basis.py;
modify src/online_research_tools.py.
Interface: consumes normalized SAP context; produces assess_sap_price_basis(context)
with status/reason and independent holds. Price metadata uses existing source names.
- [x] Write positive retained-shape and negative price/receipt/chronology tests.
- [x] Observe RED for the absent assessment and dropped metadata.
- [x] Implement the pure assessment and SAP-only metadata retention.
- [x] Run new tests plus existing research-context/price/depositary regression files.
- [x] Commit verified code and test changes.

### Task 2: Current/saved UI, source proof and release evidence
Files: modify src/online_peer_valuation_ui.py, src/online_research_tools_ui.py,
tests/sap_depositary_fixtures.py, tests/test_sap_depositary_browser.py,
.github/workflows/commercial-research-beta.yml; create docs/SAP_PRICE_BASIS_RELEASE.md.
Interface: consumes Task 1 assessment; produces sap_price_basis_html(context).
- [x] Write RED visibility/persistence/legacy tests and extend actual browser assertions.
- [x] Add shared HTML to current Valuation & Peers/Sources and saved SAP region.
- [x] Rebuild actual SAP context from retained inputs at original cutoff; no transport,
  source mutation, coverage promotion or fake FX. Test save/reload unchanged.
- [x] Run focused integration, wording, whitespace, protected manifest and range checks.
- [x] Obtain one independent whole-branch review; fix material findings with RED/GREEN.
- [x] Record official FX source/convention and failed capture boundaries; update roadmap.
- [ ] Sync exact committed tree as a new draft PR; inspect actual CI without borrowing
  previous revision results. Existing full CI remains necessary for release.

Execution: local assessment/UI complete; independent review material findings fixed
in one RED/GREEN pass; 404 focused checks passed. Exact-head CI is still required.
