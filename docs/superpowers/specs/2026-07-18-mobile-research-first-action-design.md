# Mobile Research First-Action Density Design

**Date:** 2026-07-18
**Status:** Approved by the active continuation contract

## Purpose

Make the Personal Research workflow faster to understand at a 390x844 phone viewport without hiding readiness, freshness, source, or research-only boundaries.

The current desktop and phone audit confirms that Research Desk, Discover, Company Workbench, and Monitor render successfully and remain answer-first. The remaining local usability problem is repetition: the compact profile strip and the route workspace card both repeat freshness context before the route-specific task appears. On Company Workbench, the full review path adds another multi-line block before the selected-company answer.

This slice improves first-action visibility. It does not change research data, readiness, source rights, forecasts, valuation, evidence, or navigation.

## Current Audit Evidence

Fresh screenshots were captured outside the repository at 1280x720 and 390x844 for all four Personal Research routes. They are audit evidence only and remain unstaged.

The audit found:

1. Desktop routes clearly show saved-readiness context, freshness, one next action, and the research-only boundary.
2. Discover presents search before advanced filters, but the first company result begins below the desktop viewport.
3. Company Workbench presents the selected-company answer after the route card and a long review-path caption; at phone width, the `Selected Company` heading falls below the first screen.
4. Monitor truthfully distinguishes an empty evidence queue from a market conclusion, but the weekly summary begins near the bottom of the phone viewport.
5. At phone width, the compact profile strip uses three rows and the route card repeats freshness already shown immediately above it.
6. No route showed a traceback, browser console error, fabricated evidence, ranking, recommendation, or missing research-only boundary.

## Considered Approaches

### 1. Compact the existing research chrome at phone width — selected

Keep the current components and information architecture. Add semantic classes to existing fields, use responsive CSS to reduce repeated content, and collapse the Workbench review path.

Benefits:

- smallest behavioral surface;
- desktop remains unchanged;
- no new route or component system;
- all readiness and source boundaries remain present;
- directly improves the audited phone bottleneck.

### 2. Replace the profile strip and route card with one unified component

This could remove more duplication, but it would broaden the slice across public, research, and operator shells and create unnecessary regression risk.

### 3. Hide most status context on phone

This would maximize visible content but would weaken the evidence-first contract. Source date, freshness, and research-only boundaries must remain discoverable before a research answer.

## Design

### Profile context

The existing compact profile strip remains the authoritative profile context. At widths of 640 pixels or less:

- use three columns instead of two so its five facts occupy two rows;
- reduce gaps and horizontal padding without reducing the existing text content;
- keep Data profile, Sources through, Freshness, Price-ready, and DCF-ready visible;
- preserve the existing stale/current/mixed/missing color states.

No field is removed or moved into generated output.

### Research route card

The existing route workspace card remains the primary answer boundary. Add stable semantic classes to its freshness and next-action rows.

At widths of 640 pixels or less:

- reduce card padding and vertical margins;
- hide only the duplicated route-card freshness row because the authoritative compact profile strip is immediately above it;
- keep the route title, selected ticker or focused scope, next action, and research-only statement visible;
- use the existing visual language, colors, borders, typography, and spacing scale.

Desktop rendering keeps both route freshness and next action unchanged.

### Company Workbench review path

Replace the always-visible full review-path caption with a collapsed `Review path` expander. Its content remains unchanged and in the same order:

`Selected Company -> What Changed -> Business Trend -> Valuation -> Forward View -> What Remains Withheld -> Research Conclusion -> Next Research Task`

The expander appears immediately after the `Selected Company` heading and before the detailed report. The path is guidance, not evidence required to understand the primary answer, so it stays collapsed while the first-read content follows directly beneath it.

### Other routes

Research Desk, Discover, and Monitor keep their current content order. They benefit automatically from the shared responsive compaction:

- Research Desk exposes more of the weekly summary;
- Discover exposes the search control and more of the review queue;
- Monitor exposes the weekly state and change-monitor answer sooner.

## Data And Readiness Boundaries

This slice must not:

- change profile selection, readiness counts, source dates, freshness calculation, or coverage;
- promote any actuals, consensus, Revenue, EPS, cash-generation, valuation, catalyst, outcome, peer, backtest, or calibration state;
- create or consume CSV, JSON, report, sample-report, committed screenshot, or timing artifacts; temporary audit screenshots remain outside the repository;
- alter candidate-context or synthetic-fixture treatment;
- add investment advice, rankings, recommendations, price predictions, broker actions, or trade instructions.

## Accessibility

The route card keeps a labelled `section` and semantic description list. Hiding the duplicated freshness row on phone removes it from the mobile accessibility tree, but the same freshness value remains in the preceding labelled profile strip.

The Workbench path uses a native Streamlit expander, preserving a keyboard-operable disclosure control. The selected-company answer moves earlier in reading order; the path content remains available on request.

Screenshot evidence can confirm visible hierarchy and responsive reflow. It cannot prove full keyboard, screen-reader, contrast, or WCAG compliance; existing automated and manual accessibility checks remain separate.

## Testing

Behavior changes use test-first coverage:

1. Extend the research workspace HTML contract test to require semantic freshness and next-action classes.
2. Add a dashboard contract test proving the Workbench selected-company answer precedes the collapsed review path and the report details remain after the answer.
3. Add a style contract test for phone-only three-column profile context, hidden duplicated route freshness, and compact route spacing.
4. Run focused research workspace and dashboard contract tests.
5. Run the full suite and all required dashboard, render, public, commercial-beta, release, pilot, hygiene, whitespace, and staged checks.
6. Re-capture all four Personal Research routes at 1280x720 and 390x844 outside the repository and compare before and after.

## Acceptance Criteria

- All four routes retain profile, source-date, freshness, next-action, and research-only context.
- At 390x844, the profile strip uses no more than two rows for its five facts.
- At 390x844, the route card does not repeat the freshness row.
- Discover shows its search control within the first phone viewport.
- Company Workbench shows the `Selected Company` first-read within the first phone viewport.
- Monitor shows at least the start of its weekly summary within the first phone viewport.
- Company Workbench keeps its complete review path in a collapsed disclosure after the `Selected Company` heading and before the detailed report.
- Desktop information and behavior remain unchanged.
- No readiness state, data input, generated artifact, or external dependency changes.
