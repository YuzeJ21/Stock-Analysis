# Personal Research Mode

Personal Research is the default local workspace for repeated company review. It composes existing readiness, Single-Stock Report, Change Monitor, Thesis Journal, Scenario Lab, peer-context, freshness, and Earnings Outlook capabilities. It does not introduce a second calculation or data-persistence system.

## Workflow

1. **Research Desk** starts with a traceable weekly summary, what changed, what is blocked or stale, what to review next, and the Discover action. Deterministic cohort scope, concise lane coverage, and full matrices remain under collapsed Advanced Evidence.
2. **Discover** starts with the readiness-backed Stock Selector, limits it to the focused cohort, and opens one company directly in Company Workbench. Cohort scope and lane-coverage context remain available under a collapsed Advanced section after the selection task.
3. **Company Workbench** starts with the selected company's compact usable/withheld answer, then keeps changed evidence, quarterly business trend, valuation boundaries, forward context, withheld inputs, conclusion, and one next research task in one review path. Technical lane-coverage cards remain available under a collapsed Advanced section.
4. **Monitor** starts with the weekly summary and the deduplicated unresolved source-backed change answer. An empty queue is a neutral wait state with one Discover action, not proof that nothing changed. Five-company Earnings Nowcast readiness remains available under collapsed Advanced evidence without ranking companies or combining blockers.

Data Health and Proof History remain available through **Advanced Evidence**. Operator mode remains the place for source setup, validation, preview, proof, and maintenance commands. Public mode retains the controlled five-page demonstration.

Data Health and Proof History stay inside Personal Research mode when opened from Company Workbench Advanced Evidence. Both preserve the selected ticker and show a direct **Return to Company Workbench** action before evidence content; a missing ticker returns to Research Desk instead of inventing a company. This navigation does not change readiness or evidence state, record a review outcome, expose Operator commands, or promote blocked inputs.

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
- Source-backed peer relationships do not automatically become valuation anchors. Peer role, economic comparability, and anchor eligibility are reviewed independently; legacy or context-only rows are withheld from peer medians.
- Numerical Beat/Miss probability remains withheld without calibration evidence.
- Scenarios remain bounded, session-local assumption tests and do not change canonical data.
- The Change Monitor and Thesis Journal do not mutate readiness or source rows.
- Broad universe tracking does not imply broad analysis readiness.

## Focused-Use Strategy

The current saved profile deterministically selects up to 25 eligible operating companies or ADRs with price-ready evidence. Active-universe and deeper ready lanes affect review order only; they do not create a score, expected return, or recommendation. If fewer than 25 eligible companies exist, the cohort reports `awaiting_reviewed_source` and is never padded.

## Focused Cohort Coverage

Research Desk composes a read-only coverage matrix for every focused-cohort company. The matrix separates adjusted daily price history, quarterly Revenue, quarterly EPS, margins, free cash flow, cash/debt, shares outstanding, trusted peers, filing dates, earnings dates, and exact-period point-in-time consensus. Each lane is labeled `usable_now`, `partial`, `candidate_context_only`, `blocked`, or `excluded` from saved source evidence only. The weekly summary and four direct research answers render first; concise cohort cards and the full company-by-lane matrix remain under Advanced Evidence.

Closing Advanced Evidence does not remove or combine cohort states. A DCF-ready flag does not fabricate quarterly actuals, earnings dates, or consensus. Candidate peers do not become trusted peers. Missing source provenance remains blocked, and non-company rows remain excluded rather than forced through operating-company analysis.

In Company Workbench, the Peer Read-Through Map answers result-context and valuation-anchor questions separately. `core_peer` and `secondary_peer` are the only roles that can become anchors, and only with explicit source, as-of date, relationship rationale, comparability basis, and `valuation_anchor_eligible=yes`. Aspirational, negative, excluded-close, not-clean, candidate, and legacy-unreviewed relationships remain visible context without entering peer medians.

Discover uses the same deterministic cohort but keeps the primary company-selection task first. Its search control and compact readiness-backed rows render before the collapsed cohort context, so a researcher can choose a company without reading technical coverage evidence. This order changes no cohort membership, readiness state, ranking, or Company Workbench route.

Company Workbench keeps the existing selected-ticker coverage calculation but moves its cards under `Advanced: selected-company lane coverage`. The unchanged report renderer supplies the first expanded company answer and continues to show supported evidence, withheld inputs, source-backed changes, uncertainty, and one next task. Closing the lane cards does not infer coverage, combine readiness states, or unlock a report section.

Monitor also carries one compact five-company Earnings Nowcast evidence answer. Company Workbench keeps historical valuation regime, catalyst evidence, and research outcome learning inside the existing Valuation, Forward View, and Thesis Journal sequence. Their raw rows stay under Advanced. These helpers do not add a route, refresh a provider, apply an import, or change canonical readiness.

Historical valuation is descriptive only and requires a denominator that was public at the matching price timestamp. Research outcomes preserve reviewed learning without return attribution or skill scoring. Catalyst events require source and cutoff timestamps and cannot change forecasts, valuation inputs, readiness, or recommendations.

Header-only templates live at `docs/templates/historical_valuation_observations.csv`, `docs/templates/research_outcome_reviews.csv`, and `docs/templates/catalyst_evidence.csv`. Outcome and catalyst inputs must be previewed before the explicit `CONFIRM_REVIEWED=1` record command. The canonical ledgers remain local working evidence unless one exact artifact is intentionally reviewed for a controlled package.

The weekly summary is derived from deduplicated, source-backed Change Monitor events from the prior seven days plus reviewer-authored journal review dates. It writes no data and does not turn a missing event into a no-change claim.

Quarterly business trend is descriptive evidence, not a forecast. Revenue and EPS comparisons require explicit versioned quarterly actuals with compatible definitions. Operating margin, free cash flow, and FCF margin now have a separate in-memory evidence contract and independent states, but production values remain withheld until a **reviewed quarterly source adapter** supplies explicit compatible observations. Sequential and year-over-year changes are withheld when matching periods or definitions are unavailable. Q4 is never derived from annual results; every Q4 component requires explicit filed-quarter evidence. Primary cards show the research answer only; component values, formulas, and source references stay in the collapsed Advanced quarterly evidence table. The local acceptance harness evaluates in-memory candidates only: **no adapter file is loaded or written**, and an accepted candidate is not supplied to Company Workbench or promoted into readiness.

## Mobile First-Action Density

At phone width, the compact profile context keeps Data profile, Sources through, Freshness, Price-ready, and DCF-ready visible in two rows. The route card omits only its duplicate freshness row while preserving the page, selected scope or ticker, next action, and research-only boundary. Discover therefore shows its search task and first review row sooner; Monitor shows the weekly state sooner; and Company Workbench shows `Selected Company`, a collapsed `Review path`, and the first-read answer without the full sequence consuming the viewport.

This mobile first-action density improvement does not change readiness, source dates, coverage, evidence, forecasts, valuation, or research conclusions. Desktop profile and route metadata remain unchanged. Company Workbench keeps the complete review path available through the same collapsed disclosure at desktop and phone widths.

## SEC Quarterly Cash-Generation Pilot

The read-only NVIDIA Q1 FY2027 pilot proves that one exact SEC accession can supply compatible Revenue, operating income, cash from operations, and explicitly signed capital expenditures for adapter review. Run `make sec-quarterly-cash-preview AS_OF=<timezone-aware-cutoff>` only when `SEC_USER_AGENT` is configured. The command fetches three exact SEC endpoints in memory and writes no cache or generated artifact.

Its success state is deliberately narrow: **accepted_for_review is not production activation**. Company Workbench continues to withhold real-company operating margin, free cash flow, and FCF margin until a separate activation review connects compatible observations. The pilot does not change saved readiness, Earnings Nowcast, consensus, valuation, catalysts, outcomes, backtesting, calibration, or another company or quarter.

## Repeated Review Routine

- **Daily or after a source refresh:** open Research Desk, review traceable changes, then use Monitor for unresolved source tasks.
- **Company review:** use Discover, open one Company Workbench, read What Changed, Business Trend, Valuation, Forward View, and What Remains Withheld before recording a conclusion.
- **Weekly:** review the weekly summary, overdue journal reviews, and wait conditions. A no-change summary means no traceable saved event in the review window, not that the company had no real-world change.
- **Operator handoff:** use Data Health or Proof History only when source proof, blocked inputs, or event evidence is the question.
