# APLD Single-Stock Research Report

Research-only local report. It summarizes readiness and does not provide allocation instructions.

## How To Read This Report
- Read top-down: readiness state first, supported analysis second, blocked or excluded analysis third.
- Current use: Price/setup review only until trusted fundamentals, DCF, and peer inputs are ready.
- Logic source: repo-native code under `src/`; libraries and adapters support data handling/UI, and plugins can help development review, but shipped analysis comes from repo code and local data.
- Boundary: this is research context only. It does not provide allocation instructions, account actions, or direct recommendations.

## Executive Summary
APLD state: partial. Decision: Blocked by Data - Missing Fundamentals. DCF: blocked. Primary blocker: fundamentals. Peer workflow: waits for trusted price, fundamentals, and DCF inputs first. Optional earnings or analyst-estimate context is unavailable until trusted local CSV rows exist. Next: Import trusted fundamentals for APLD. If SEC_USER_AGENT is configured, use SEC staging; otherwise use the manual fundamentals import workflow.

## One-Minute Status
APLD state: partial. Decision: Blocked by Data - Missing Fundamentals. DCF: blocked. Primary blocker: fundamentals. Peer workflow: waits for trusted price, fundamentals, and DCF inputs first. Optional earnings or analyst-estimate context is unavailable until trusted local CSV rows exist. Next: Import trusted fundamentals for APLD. If SEC_USER_AGENT is configured, use SEC staging; otherwise use the manual fundamentals import workflow.

## What We Can Analyze Now
- Ready inputs: price, momentum, market_direction, liquidity, correlation.
- Supported now: Use available price or setup context only. Company-level valuation stays blocked until trusted fundamentals, free cash flow or margin inputs, share count, and DCF fields are ready.
- Still locked or excluded: Blocked features: fundamentals, dcf, peer, earnings, analyst_estimates. Excluded features: portfolio. Unavailable sections are intentionally locked; missing data is not inferred.

## Analysis Quality
- Analysis mode: Price/setup review only.
- Why: Use price and setup context only. Company valuation stays blocked until trusted fundamentals and DCF inputs exist.
- Optional context: Earnings and analyst estimates stay locked until trusted local rows exist.

## Evaluation Function Check
- Readiness gate: strongest function; it decides ready, blocked, or excluded before any conclusion is shown.
- Price and setup: ready for local trend/setup review.
- Risk context: ready for local liquidity/correlation context.
- Fundamentals / DCF: blocked until trusted fundamentals, cash-flow or margin, share-count, and DCF inputs are ready.
- Peer comparison: blocked until source-backed peer mappings and peer valuation inputs are ready.
- Optional context: locked until trusted local earnings and analyst-estimate rows exist.
- Logic source: readiness gates, DCF boundaries, peer blockers, and report wording are repo-native under `src/`; standard libraries/adapters support data handling and UI, and plugins can help development review, but shipped analysis comes from repo code and local data.

## What This Stock Is
- Ticker: APLD
- Asset type: company
- Current role: Core Compounder. Test whether trend, fundamentals, and DCF support the long-duration thesis; current state is Ignore.

## Decision
- Bucket: Blocked by Data
- Subtype: Blocked by Data - Missing Fundamentals
- Primary blocker: fundamentals
- Main reason: Company research is blocked by missing dcf, fundamentals data.
- Next action: Import trusted fundamentals for APLD. If SEC_USER_AGENT is configured, use SEC staging; otherwise use the manual fundamentals import workflow.

## Purpose Evaluation
Research-only purpose brief. It separates what local data supports from what remains locked or excluded.
- Thesis: Core Compounder. Test whether trend, fundamentals, and DCF support the long-duration thesis; current state is Ignore.
- Alignment: Purpose alignment appears consistent with current setup `Avoid` for Core Compounder, subject to the missing-data limits below.
- Operator summary: Purpose alignment appears consistent with current setup `Avoid` for Core Compounder, subject to the missing-data limits below; Blocked by Data - Missing Fundamentals. Next blocker: fundamentals. Withheld: fundamental quality and operating-company valuation, DCF interpretation, peer-relative valuation or opportunity-cost comparison, earnings timing or surprise context, analyst estimate trend context, compounder thesis confirmation. Invalidation: Invalidate the compounder thesis review if trend conflict persists and updated fundamentals/DCF no longer support the stated purpose.
- Setup: Compounder setup: Avoid; final state: Ignore. Track trend quality alongside fundamentals and DCF before treating the long-duration thesis as well supported. Ignored names are left unranked.
- Valuation boundary: Valuation conclusion is blocked until trusted DCF/fundamental inputs are complete.

## Supported Analysis
- Supported analysis: price history, setup and momentum context, market/theme context, liquidity context, correlation/risk context.

## Blocked Analysis
- Unsupported analysis: fundamental quality and operating-company valuation, DCF interpretation, peer-relative valuation or opportunity-cost comparison, earnings timing or surprise context, analyst estimate trend context, compounder thesis confirmation.

## Setup / Momentum
- Compounder setup: Avoid; final state: Ignore. Track trend quality alongside fundamentals and DCF before treating the long-duration thesis as well supported. Ignored names are left unranked.
- 1M performance: 0.39970798910099226
- 3M performance: 0.7164338740742906
- 1Y performance: Not available

## Risk Notes
- Risk watchpoint: peer-relative context is incomplete, so valuation comparison and opportunity cost remain uncertain.
- Invalidation condition: Invalidate the compounder thesis review if trend conflict persists and updated fundamentals/DCF no longer support the stated purpose.

## Next Research Step
- Next research question: Which trusted fundamentals or DCF fields are needed to confirm whether the compounder thesis remains supported?
- Review priority: Unlock priority: price context exists, but fundamentals blocks deeper analysis.
- Confidence explanation: Confidence is low: primary blocker is fundamentals; blocked features are fundamentals, dcf, peer, earnings, analyst_estimates.

## Data Readiness
- Overall state: partial
- Price ready: True
- Momentum ready: True
- Liquidity ready: True
- Correlation ready: True
- Fundamentals ready: False
- DCF ready: False
- Peer ready: False
- Earnings ready: False
- Analyst estimates ready: False
- Blocked features: fundamentals, dcf, peer, earnings, analyst_estimates
- Excluded features: portfolio

## Price Coverage
- Price rows: 615
- First date: 2023-12-15
- Last date: 2026-06-01
- Missing price reason: Not available

## Valuation Readiness
- DCF status: insufficient_data.
- DCF missing fields: free_cash_flow, shares_outstanding, revenue, fcf_margin.
- Reason not ready: missing free_cash_flow, shares_outstanding, revenue, fcf_margin.
- DCF assumptions: hidden until price, fundamentals, free cash flow or FCF margin, and share-count inputs are ready.
- Sensitivity table: unavailable until the base DCF can be calculated.
- Relative valuation: blocked until trusted peer mappings and peer valuation inputs are ready; current status=insufficient_data; peer count=0.
- Valuation conclusion is shown only when trusted DCF and peer inputs support it; missing valuation inputs are not inferred.

## Peer Workflow
- Peer blocker type: blocked_until_fundamentals_dcf
- Mapping status: wait_for_core_data
- Peer count: 0
- Trend comparison ready: False
- Valuation comparison ready: False
- DCF peer comparison ready: False
- Sample peers: Not available
- Next peer action: Peer-relative valuation should wait until trusted price, fundamentals, and DCF inputs are ready.

## Missing Data
- 1Y performance is unavailable from the current local price history.
- EPS is unavailable from the current local fundamentals dataset.
- Free cash flow is unavailable from the current local fundamentals dataset.
- No local analyst-estimate dataset is configured in the CSV-first pipeline.
- No local earnings dataset is configured in the CSV-first pipeline.
- Normalized growth target was reduced to keep it conservatively below WACC.
- Revenue is unavailable from the current local fundamentals dataset.
- Valuation missing field: cash
- Valuation missing field: debt
- Valuation missing field: ebitda
- Valuation missing field: eps
- Valuation missing field: fcf_margin
- Valuation missing field: free_cash_flow
- Valuation missing field: market_cap_or_price_and_shares
- Valuation missing field: revenue
- analyst_estimates has no local row for this ticker.
- earnings has no local row for this ticker.
- fundamentals has no local row for this ticker.

## Source / Freshness
- local:prices.csv: research-grade / local, retrieved 2026-06-03T18:35:06.424153090+00:00; Local CSV-backed research data.
- local:fundamentals.csv: research-grade / local, retrieved 2026-06-04T04:54:31+00:00; No local fundamentals row was found for this ticker.
- local:earnings.csv: research-grade / local, retrieved 2026-06-04T04:54:31+00:00; Earnings fields are unavailable from the bundled local sample files.
- local:analyst_estimates.csv: research-grade / local, retrieved 2026-06-04T04:54:31+00:00; Analyst estimate fields are unavailable from the bundled local sample files.

## Source/Freshness Audit
- Prices: True; local source `data/prices.csv`; coverage 2023-12-15 to 2026-06-01; rows=615; staged path `data/staged/prices/` or `data/imports/prices.csv`; rejected rows `data/rejected/price_import_rejected.csv`.
- Fundamentals / DCF: blocked; local source `data/fundamentals.csv`; reason missing free_cash_flow, shares_outstanding, revenue, fcf_margin; SEC_USER_AGENT present; staged path `data/staged/fundamentals/` or `data/imports/fundamentals.csv`; rejected rows `data/rejected/fundamentals_import_rejected.csv`.
- Peers: blocked until fundamentals / DCF; local source `data/peers.csv`; staged path `data/imports/peers.csv`; next peer action Peer-relative valuation should wait until trusted price, fundamentals, and DCF inputs are ready.
- Earnings: False; trusted local CSV only; staged path `data/staged/earnings/`; command `make import-earnings`; rejected rows `data/rejected/earnings_import_rejected.csv`.
- Analyst estimates: False; trusted local CSV only; staged path `data/staged/analyst_estimates/`; command `make import-analyst-estimates`; rejected rows `data/rejected/analyst_estimates_import_rejected.csv`.
- Credentials: SEC_USER_AGENT present; STOOQ_API_KEY missing; missing remote credentials should not break local CSV reports or staged import workflows.
- Report command: `make stock-report TICKER=APLD`. Research-only output; copyable command only.
