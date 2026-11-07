# Research Task Hierarchy Implementation Plan

> **For agentic workers:** Use subagent-driven development for isolated presentation helpers and the company compositor; root integrates dashboard composition. Check off tasks after their evidence passes.

**Goal:** Make the existing product start with company research and expose one clear task per page.

**Architecture:** Reuse the online SEC search, immutable review queue, five company sections, saved tools and Monitor. Change presentation and content order. Preserve source collection, financial definitions, eligibility, source rights and persistence contracts.

**Tech Stack:** Existing Python/Streamlit app and pinned automated browser environment.

**Spec:** The Design section below records the scoped correction following the live product audit.

## Design

The November 7 audit found repeated stale-readiness prose dominating Research Desk and Monitor, overlapping search instructions in Discover, and three empty summary cards preceding company research. The user requests a cleaner, structured app and retains the established automatic testing and sync workflow.

Use task-focused composition: Research Desk searches online companies and resumes saved SEC research; Discover browses companies with optional coverage tools folded; Overview owns the complete company summary; other company sections use compact context; Monitor leads with actionable evidence review and actual process follow-ups. Workspace context and diagnostics remain accessible in closed details. Original tools remain reachable in their sections.

Approaches considered: another copy-only pass would retain the reproduced hierarchy problem; a new frontend would duplicate working research behavior. The chosen implementation reorders existing components and introduces only small display helpers, minimizing the regression surface.

## Global Constraints

- English UI; preserve source excerpts and canonical data.
- No inferred current listing, coverage, model eligibility or approval from saved receipts.
- Preserve same-day closes, annual diluted EPS, 35-day fiscal window and at least three qualified references.
- No implicit online requests from rendering, navigation or disclosure opening.
- Exact-pair, profile, issuer, receipt bytes and same-session return remain binding.
- No dependency or data-source changes; existing worktree and navigation remain in use.

## Review Focus

Empty stores; malformed stored issuer paths; identity conflicts; stale observations; saved versus online-only company paths. Keep readable failures and explicit gaps, safe links and HTML escaping. Native closed disclosures must remain keyboard accessible and phone layouts must not overflow.

## Tasks

- [x] Add a task header and bounded saved-SEC cards in `src/research_task_layout.py`; test escaping, empty/corrupt stores and original source scope.
- [x] Update `src/dashboard.py`: concise shared online search on Desk/Discover; saved research on Desk; retain old brief and workspace evidence in closed details; consolidate coverage studies; keep Monitor actions primary and move diagnostics into advanced evidence.
- [x] Update the company compositor and summary renderers: one initial load prompt, full Overview answers, compact other tabs, smaller controls, disclosed price history, notes-first ordinary saved research and leading pinned SEC pairs.
- [x] Update exact layout contracts to the new route-specific hierarchy while retaining all source, value, identity, rights, no-fetch and persistence assertions. Add only the meaningful desktop/phone hierarchy cases.
- [x] Freeze sources, run focused unit/integration checks, the existing ten browser regressions and the new desktop/phone cases under unchanged-data guards. Inspect the actual app at both widths.
- [x] Review the final diff, log roadmap changes, commit reviewed code/docs/tests, sync main and verify remote commit. Save local screenshots and exact results.

## Verification and follow-up

Focused functional checks passed (239 cases). Desktop/phone workflow verification passed the twelve-case suite, with a fresh two-case hierarchy check after the final routing/copy/freshness refinements. The last scoped popover CSS repair passed twenty-one control/section checks, including actual framework rendering at 1280, 390 and 320 pixels in both light and dark appearance with normal/hover states. Source/provider, receipt, and no-write assertions remain independent of presentation.

The legacy Company visual document collector predates the integrated Workbench. It was not expanded into a new document-gate rewrite in this slice; the dedicated rendered company regressions cover the current five-section workflow. Reconcile that internal collector before relying on its historical whole-matrix result for a future release. Focused verification is not a full-suite or human accessibility claim. Exact tested source hashes and screenshots are retained in the local release packet.
