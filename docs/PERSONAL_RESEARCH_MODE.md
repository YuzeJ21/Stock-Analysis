# Personal Research Mode

Personal Research is the default local workspace for repeated company review. It composes existing readiness, Single-Stock Report, Change Monitor, Thesis Journal, Scenario Lab, peer-context, freshness, and Earnings Outlook capabilities. It does not introduce a second calculation or data-persistence system.

## Workflow

1. **Research Desk** starts with one **Today's Research Brief**: what saved work needs attention, one traceable reason, the saved-readiness warning, and one action to Monitor or Discover. It deduplicates overlapping weekly and source-change counts rather than adding them. A zero-item answer applies only to evidence loaded in the workspace and never proves that no external event or research need exists. Weekly, cohort, observation, coverage, and source-change detail remains under collapsed Advanced Evidence.
2. **Discover** answers two different questions separately. **Screen eligibility — when supported** applies the unchanged strict Daily Momentum & Valuation evidence gates. **Browse saved companies** is an alphabetical, readiness-only evidence-access list that explains why each company is inspectable, what evidence is usable, and the main evidence gap before opening its Company Brief. Browsing is not screen eligibility, ranking, opportunity scoring, or a recommendation, and it does not read legacy ranking outputs.
3. **Company Workbench** starts with one Company Brief answering `Use now -> Still withheld -> What changed -> Next research task`, followed by the visible research-only stop rule and ticker-preserving Data Health action. `Open evidence and analysis modules` restores the existing Research Decision Lab, business trend, valuation, forward context, authoring, conclusion detail, methodology, and offline HTML brief for the current session. The primary task is not repeated in the detailed layer; the same task object still feeds the HTML snapshot. Technical lane coverage and Decision Lab evidence remain under collapsed Advanced sections.

After that explicit action, the detailed sequence remains `What Changed -> Research Decision Lab -> Business Trend` before valuation, forward context, withheld evidence, and conclusion detail.
4. **Monitor** now answers one question through one **Follow-up Queue**: **Since the last review**, **Needs verification**, **Waiting on evidence**, **Scheduled context**, and **Evidence freshness**. When saved actionable evidence exists, five compact panels render once and any due process rows stay in focused-cohort order. When every actionable count is zero, Monitor renders one concise empty state, explicitly says this does not prove that no external event, risk, or research need exists, and provides one **Open Discover** action.

The Follow-up Queue reuses the fixed seven-day summary, unresolved saved source-change rows, existing discipline precedence, and independent readiness/observation freshness. Full process rows, stable identities, and source-change evidence remain under `Advanced: Monitor evidence`. Monitor-only rows are retained there; they are not deleted, promoted, rescored, or reinterpreted. Five-company Earnings Nowcast readiness remains a separate collapsed Advanced section. Ordinary route use writes nothing.

Company Workbench arbitrates one overall next task. Its change context is explicitly `none`, `snapshot_only`, or `source_backed`, so an empty queue receives a neutral no-queued-change badge and is never mislabeled as snapshot evidence. Only a change carrying separate explicit source-backed eligibility can win: open review keeps the event's suggested task, `still_blocked` keeps its `wait_for_evidence` condition, and `intentionally_deferred` keeps its `monitor` condition. Snapshot-only context receives no source-backed badge and cannot outrank the existing ordered Research Conclusion priority. Forward View guidance stays lane-specific and does not compete for the overall task. This presentation leaves readiness and evidence states independent and unchanged.

Data Health and Proof History remain available through **Advanced Evidence**. Operator mode remains the place for source setup, validation, preview, proof, and maintenance commands. Public mode retains the controlled five-page demonstration.

Data Health and Proof History stay inside Personal Research mode when opened from Company Workbench Advanced Evidence. Both preserve the selected ticker and show a direct **Return to Company Workbench** action before evidence content; a missing ticker returns to Research Desk instead of inventing a company. This navigation does not change readiness or evidence state, record a review outcome, expose Operator commands, or promote blocked inputs.

## Research States

Personal Research may route work only as:

- `review_now`: verified evidence changed or a reviewed task is open.
- `monitor`: no immediate evidence task is available.
- `wait_for_evidence`: required source proof or freshness is unavailable.
- `excluded`: the analysis is not applicable.

These are workflow states. They are not rankings, expected-return claims, investment recommendations, or transaction instructions.

## Research Decision Lab

Company Workbench shows exactly one compact six-lane research-process summary for Plan, Evidence, Invalidation, Scenario, Review trigger, and Learning after `What Changed`. It composes saved evidence only and cannot replace `Use now`, `Still withheld`, the Data Health handoff, Research Conclusion, or Next Research Task. Identities, evidence summaries, and technical details remain under `Advanced: Decision Lab evidence`.

Monitor derives the same contract independently for each saved focused-cohort ticker. One invalid ticker becomes unavailable without changing another ticker, and display order remains the existing cohort order rather than process severity, market value, or expected return. Source-change evidence remains independently preserved inside `Advanced: Monitor evidence`; the primary Follow-up Queue composes it without changing its review state.

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

Research Desk composes its brief and a read-only coverage matrix for every focused-cohort company. The matrix separates adjusted daily price history, quarterly Revenue, quarterly EPS, margins, free cash flow, cash/debt, shares outstanding, trusted peers, filing dates, earnings dates, and exact-period point-in-time consensus. Each lane is labeled `usable_now`, `partial`, `candidate_context_only`, `blocked`, or `excluded` from saved source evidence only. The single brief renders first; weekly cards, concise cohort cards, observation detail, the full company-by-lane matrix, and source-change rows remain under Advanced Evidence.

Closing Advanced Evidence does not remove or combine cohort states. A DCF-ready flag does not fabricate quarterly actuals, earnings dates, or consensus. Candidate peers do not become trusted peers. Missing source provenance remains blocked, and non-company rows remain excluded rather than forced through operating-company analysis.

In Company Workbench, the Peer Read-Through Map answers result-context and valuation-anchor questions separately. `core_peer` and `secondary_peer` are the only roles that can become anchors, and only with explicit source, as-of date, relationship rationale, comparability basis, and `valuation_anchor_eligible=yes`. Aspirational, negative, excluded-close, not-clean, candidate, and legacy-unreviewed relationships remain visible context without entering peer medians.

Discover evaluates only saved `momentum_ready` rows through a strict, unweighted intersection: price above SMA50, SMA50 above SMA200, positive three- and six-month returns, positive SPY-relative return, a current commercial-eligible own-history valuation percentile at or below 40, positive free cash flow, non-negative revenue growth, and debt to equity no higher than the configured quality-value limit. Current-market recency, price and fundamental provenance, exact-source rights, and registered field scope must also pass. Missing, stale, non-finite, malformed, unverified, or restricted evidence withholds the row. Eligible results are alphabetical research candidates with ticker-bound Company Workbench routes, never a score or investment ranking.

The separate saved-company browser reads focused-cohort ticker readiness only, filters to company rows, and sorts by ticker. It never imports queue rank, score, priority, or legacy decision/watchlist output. A saved row may be opened to inspect available evidence even when it does not qualify for the strict screen. Each row therefore answers **Why inspectable**, **Usable evidence**, and **Main evidence gap** and uses one `Open <TICKER> Company Brief` action.

The first implementation is read-only and accepts no prior saved queue, so Discover labels current eligible rows without claiming they are newly eligible; `new_today`, `still_qualifies`, and `exited_today` remain unavailable until a separately approved operating slice supplies comparable snapshots. It writes no CSV, JSON, report, screenshot, timing, readiness, canonical-data, or ledger artifact. Current repository inputs have no historical-valuation ledger and no approved commercial price lineage, so the truthful real-data result is an empty eligible set with blockers under `Advanced: daily queue evidence`.

Company Workbench keeps the existing selected-ticker coverage calculation under `Advanced: selected-company lane coverage`. The primary brief composes existing selected-answer, change, and next-task contracts without recalculating or promoting any lane. Detailed modules are closed by default and return only after the explicit session-local action; that action writes no file, changes no canonical evidence, and changes no readiness. Closing the lane cards does not infer coverage, combine readiness states, or unlock a report section.

Monitor also carries one compact five-company Earnings Nowcast evidence answer. Company Workbench keeps historical valuation regime, catalyst evidence, and research outcome learning inside the existing Valuation, Forward View, and Thesis Journal sequence. Their raw rows stay under Advanced. These helpers do not add a route, refresh a provider, apply an import, or change canonical readiness.

Historical valuation is descriptive only and requires a denominator that was public at the matching price timestamp. Research outcomes preserve reviewed learning without return attribution or skill scoring. Catalyst events require source and cutoff timestamps and cannot change forecasts, valuation inputs, readiness, or recommendations.

Header-only templates live at `docs/templates/historical_valuation_observations.csv`, `docs/templates/research_outcome_reviews.csv`, and `docs/templates/catalyst_evidence.csv`. Outcome and catalyst inputs must be previewed before the explicit `CONFIRM_REVIEWED=1` record command. The canonical ledgers remain local working evidence unless one exact artifact is intentionally reviewed for a controlled package.

The weekly summary is derived from deduplicated, source-backed Change Monitor events from the prior seven days plus reviewer-authored journal review dates. The Desk brief composes that saved summary with the unresolved source-change queue using the larger saved count, not their sum. It writes no data and does not turn a missing event into a no-change claim.

Quarterly business trend is descriptive evidence, not a forecast. Revenue and EPS comparisons require explicit versioned quarterly actuals with compatible definitions. Operating margin, free cash flow, and FCF margin now have a separate in-memory evidence contract and independent states, but production values remain withheld until a **reviewed quarterly source adapter** supplies explicit compatible observations. Sequential and year-over-year changes are withheld when matching periods or definitions are unavailable. Q4 is never derived from annual results; every Q4 component requires explicit filed-quarter evidence. Primary cards show the research answer only; component values, formulas, and source references stay in the collapsed Advanced quarterly evidence table. The local acceptance harness evaluates in-memory candidates only: **no adapter file is loaded or written**, and an accepted candidate is not supplied to Company Workbench or promoted into readiness.

## Mobile First-Action Density

At phone width, the compact profile context keeps Data profile, Sources through, Freshness, Price-ready, and DCF-ready visible in two rows. The route card omits only its duplicate freshness row while preserving the page, selected scope or ticker, next action, and research-only boundary. Discover therefore shows its search task and first review row sooner; Monitor shows the weekly state sooner; and Company Workbench shows `Selected Company`, a collapsed `Review path`, and the first-read answer without the full sequence consuming the viewport.

This mobile first-action density improvement does not change readiness, source dates, coverage, evidence, forecasts, valuation, or research conclusions. Desktop profile and route metadata remain unchanged. Company Workbench keeps the complete review path available through the same collapsed disclosure at desktop and phone widths.

## SEC Quarterly Cash-Generation Pilot

The read-only NVIDIA Q1 FY2027 pilot proves that one exact SEC accession can supply compatible Revenue, operating income, cash from operations, and explicitly signed capital expenditures for adapter review. Run `make sec-quarterly-cash-preview AS_OF=<timezone-aware-cutoff>` only when `SEC_USER_AGENT` is configured. The command fetches three exact SEC endpoints in memory and writes no cache or generated artifact.

Its success state is deliberately narrow: **accepted_for_review is not production activation**. Company Workbench continues to withhold real-company operating margin, free cash flow, and FCF margin until a separate activation review connects compatible observations. The pilot does not change saved readiness, Earnings Nowcast, consensus, valuation, catalysts, outcomes, backtesting, calibration, or another company or quarter.

## Explicit Company Workbench Cash-Generation Preview

The bounded route `?mode=research&page=company-workbench&ticker=NVDA&open=1&cash_preview=1` adds one explicit, read-only **Cash-generation review preview — not production evidence** below the canonical Business Trend answer. The fixed review cutoff is `2026-07-20T23:59:59-04:00`. The normal Company Workbench route does not call the preview loader and continues to show only canonical production evidence and its existing withheld states.

AMD Q1 FY2026 accession `0000002488-26-000076` is the second exact filing available through the explicit `cash_preview=1` route. NVIDIA and AMD now provide bounded two-company portability through the same immutable loader, complete-withholding contract, preview-only cards, and Advanced lineage. Normal Company Workbench routes remain canonical and never load the preview.

The preview is all-or-nothing: operating margin, free cash flow, and FCF margin appear only when an accepted NVIDIA Q1 FY2027 or AMD Q1 FY2026 SEC evidence packet passes the complete identity, source-rights, cutoff, accession, acceptance-time, component, capex-sign, and compatibility contract. Any required failure withholds all three preview metrics. Accession, source URL, timestamps, component values, definitions, and blockers stay in the collapsed Advanced evidence section. The route writes no cache or canonical data, creates no readiness or generated artifact, and cannot promote any product lane.

## Repeated Review Routine

- **Daily or after a source refresh:** open Discover and check strict screen eligibility; an empty result is valid and does not relax the gates. Independently browse an alphabetical saved company to inspect its usable evidence and gaps, then use Monitor for unresolved source tasks.
- **Company review:** use Discover, open one Company Workbench, read What Changed, Business Trend, Valuation, Forward View, and What Remains Withheld before recording a conclusion.
- **Weekly:** review the weekly summary, overdue journal reviews, and wait conditions. A no-change summary means no traceable saved event in the review window, not that the company had no real-world change.
- **Operator handoff:** use Data Health or Proof History only when source proof, blocked inputs, or event evidence is the question.
