# Personal Research Mode

Personal Research is the default local workspace for repeated company review. It composes existing readiness, Single-Stock Report, Change Monitor, Thesis Journal, Scenario Lab, peer-context, freshness, and Earnings Outlook capabilities. It does not introduce a second calculation or data-persistence system.

## Workflow

1. **Research Desk** shows the deterministic focused cohort, a traceable weekly summary, what changed, what is blocked or stale, and what to review next.
2. **Discover** limits the existing readiness-backed Stock Selector to the focused cohort and opens one company directly in Company Workbench.
3. **Company Workbench** keeps the selected company, changed evidence, quarterly business trend, valuation boundaries, forward context, withheld inputs, conclusion, and one next research task in one review path.
4. **Monitor** shows the weekly summary plus deduplicated unresolved source-backed changes and wait conditions without ranking companies.

Data Health and Proof History remain available through **Advanced Evidence**. Operator mode remains the place for source setup, validation, preview, proof, and maintenance commands. Public mode retains the controlled five-page demonstration.

## Research States

Personal Research may route work only as:

- `review_now`: verified evidence changed or a reviewed task is open.
- `monitor`: no immediate evidence task is available.
- `wait_for_evidence`: required source proof or freshness is unavailable.
- `excluded`: the analysis is not applicable.

These are workflow states. They are not rankings, expected-return claims, investment recommendations, or transaction instructions.

## Truth Boundaries

- Missing trend, valuation, peer, earnings, estimate, or nowcast inputs stay unavailable rather than inferred.
- Candidate peers and news context cannot become trusted peer proof or modify numerical forecasts.
- Numerical Beat/Miss probability remains withheld without calibration evidence.
- Scenarios remain bounded, session-local assumption tests and do not change canonical data.
- The Change Monitor and Thesis Journal do not mutate readiness or source rows.
- Broad universe tracking does not imply broad analysis readiness.

## Focused-Use Strategy

The current saved profile deterministically selects up to 25 eligible operating companies or ADRs with price-ready evidence. Active-universe and deeper ready lanes affect review order only; they do not create a score, expected return, or recommendation. If fewer than 25 eligible companies exist, the cohort reports `awaiting_reviewed_source` and is never padded.

## Focused Cohort Coverage

Research Desk composes a read-only coverage matrix for every focused-cohort company. The matrix separates adjusted daily price history, quarterly Revenue, quarterly EPS, margins, free cash flow, cash/debt, shares outstanding, trusted peers, filing dates, earnings dates, and exact-period point-in-time consensus. Each lane is labeled `usable_now`, `partial`, `candidate_context_only`, `blocked`, or `excluded` from saved source evidence only.

The concise usable/gated answer appears on Research Desk; the full company-by-lane matrix remains under Advanced Evidence. A DCF-ready flag does not fabricate quarterly actuals, earnings dates, or consensus. Candidate peers do not become trusted peers. Missing source provenance remains blocked, and non-company rows remain excluded rather than forced through operating-company analysis.

The weekly summary is derived from deduplicated, source-backed Change Monitor events from the prior seven days plus reviewer-authored journal review dates. It writes no data and does not turn a missing event into a no-change claim.

Quarterly business trend is descriptive evidence, not a forecast. Revenue and EPS comparisons require explicit versioned quarterly actuals with compatible definitions. Sequential and year-over-year changes are withheld when matching periods or definitions are unavailable. Q4 is never derived from annual results; it requires an explicit filed-quarter row. Operating margin, free cash flow, and FCF margin remain withheld until they have their own versioned quarterly source contract.

## Repeated Review Routine

- **Daily or after a source refresh:** open Research Desk, review traceable changes, then use Monitor for unresolved source tasks.
- **Company review:** use Discover, open one Company Workbench, read What Changed, Business Trend, Valuation, Forward View, and What Remains Withheld before recording a conclusion.
- **Weekly:** review the weekly summary, overdue journal reviews, and wait conditions. A no-change summary means no traceable saved event in the review window, not that the company had no real-world change.
- **Operator handoff:** use Data Health or Proof History only when source proof, blocked inputs, or event evidence is the question.
