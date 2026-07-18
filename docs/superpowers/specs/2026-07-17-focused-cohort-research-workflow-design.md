# Focused Cohort Research Workflow Design

## Purpose

Personal Research Mode should support a repeated owner workflow, not another broad coverage dashboard. A deterministic cohort of 25-50 operating companies will connect Research Desk, Discover, Company Workbench, Monitor, and a weekly summary while preserving every existing readiness and research-only gate.

## Product Contract

The cohort is selected by evidence availability and reviewability, never expected return. Eligible rows must be operating companies or ADRs, active listings when that field is known, and price-ready. DCF, fundamentals, peer, and active-universe readiness improve review priority without becoming a score or recommendation. Stable alphabetical tie-breaking makes the same input snapshot produce the same cohort.

The cohort may contain companies without quarterly trend evidence. Those members remain useful for price/setup or valuation-boundary review, while Business Trend fails closed until comparable source-backed quarterly observations exist. The product reports the verified cohort size and never pads it with excluded or invalid securities.

## Architecture

### Focused cohort

`src/focused_research_cohort.py` owns cohort eligibility, deterministic ordering, member state, and tabular presentation. It consumes the existing ticker-readiness report and universe master data without writing either source.

Each member exposes ticker, company name, source-backed sector and industry when present, cohort rationale, usable lanes, blocked lanes, freshness, last review date, and next review reason. The selection contract contains no recommendation score or performance forecast.

### Quarterly business trend

`src/quarterly_business_trend.py` consumes the existing `QuarterlyActual` contract. It groups versioned rows by ticker and fiscal period, resolves only explicit revision chains, compares only matching units and accounting definitions, and calculates sequential and year-over-year changes only when the required periods are present. Conflicting or ambiguous rows withhold the affected metric.

Revenue and EPS are supported by the current point-in-time actuals contract. Operating margin and free-cash-flow metrics remain unavailable until an equally explicit versioned source contract exists; they are not inferred from annual fundamentals or unrelated fields. Q4 is never derived from nine-month values.

### Change monitor and weekly summary

The existing event identity remains the deduplication key. `research_monitor_frame` will expose prior/current state, source/effective timestamps, affected section, task, and wait condition. `src/weekly_research_summary.py` will group unique cohort events and reviewer-authored journal state into traceable weekly sections without rankings or generated investment narrative.

### Dashboard composition

Research Desk shows cohort/change/staleness answers and a weekly summary before Advanced Evidence. Discover filters the focused cohort by readiness rather than presenting the whole universe as equally usable. Company Workbench answers what changed, Business Trend, Valuation, Forward View, withheld evidence, conclusion state, and one next task. Monitor remains a research task queue, not an alert feed.

Public and Operator workspaces retain their existing route and evidence contracts.

## Failure and Boundary Behavior

- Missing cohort inputs return an empty, unavailable contract rather than guessed members.
- Fewer than 25 eligible companies produce the truthful maximum and `awaiting_reviewed_source`.
- Missing or non-comparable quarterly periods withhold changes per metric.
- Duplicate identical events collapse by event identity; unresolved changed identities remain visible.
- Empty weeks render a monitoring answer, not fabricated narrative.
- Generated summaries remain local and unstaged by default.

## Verification

Focused tests cover deterministic selection, exclusions, duplicate handling, missing inputs, quarterly revisions, incompatible definitions, missing comparison periods, monitor deduplication, empty weeks, and recommendation-free wording. Full tests, public checks, render smoke, browser QA, desktop/mobile review, staged hygiene, and whitespace checks remain release gates.
