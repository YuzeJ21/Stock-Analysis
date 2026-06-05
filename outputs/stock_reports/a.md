# A Single-Stock Research Report

Research-only local report. It summarizes readiness and does not provide allocation instructions.

## At A Glance
- Mode: `Standalone DCF review`.
- Decision view: Research Candidate - DCF Ready But Peer Blocked.
- DCF: Ready for scenario review.
- Peer context: Locked until source-backed peer inputs are ready.
- Optional context: Locked until trusted earnings and analyst-estimate rows exist.
- Method: project readiness gates decide what can appear; DCF uses local free-cash-flow inputs, discounted cash flows, discounted terminal value, cash/debt adjustment, and fair value per share when ready.
- Next local step: Add trusted price history for mapped peers: DHR, TMO, WAT.

## How To Read This Report
- Read top-down: readiness state first, supported analysis second, blocked or excluded analysis third.
- Current use: Standalone DCF review: company DCF assumptions can be reviewed, while peer-relative valuation stays locked until source-backed peer inputs are ready.
- Logic source: project code implements readiness gates and report wording; libraries and adapters support data handling/UI, but shipped analysis comes from project code and local data.
- Boundary: this is research context only. It does not provide allocation instructions, account actions, or direct recommendations.

## Executive Summary
- Bottom line: A is in `Standalone DCF review` mode. DCF assumptions can be reviewed, but peer-relative valuation remains limited until trusted peer inputs are ready.
- Use now: Company-level review can use local price context, fundamentals, and standalone DCF assumptions. Peer-relative valuation is shown only if trusted peer mappings and peer metrics are also ready.
- Do not infer: Blocked features: earnings, analyst estimates. Excluded features: portfolio. Unavailable sections are intentionally locked; missing data is not inferred.
- Next step: Add trusted price history for mapped peers: DHR, TMO, WAT.

## Analysis Mode Guide
- `DCF-ready review` (other): Fullest company review: price, fundamentals, DCF, and source-backed peer context are ready.
- `Standalone DCF review` (current): Company DCF can be reviewed, but peer-relative valuation remains blocked.
- `Price/setup review only` (other): Use trend/setup context only; company valuation waits for trusted fundamentals and DCF inputs.
- `Monitor-only context` (other): Use ETF/index/fund market or risk context; operating-company DCF is excluded, not failed.
- `Data-unlock only` (other): Reference state for tickers with no trusted local inputs yet; add the first missing input before drawing conclusions.

## One-Minute Status
A state: partial. Decision: Research Candidate - DCF Ready But Peer Blocked. DCF: ready. Primary blocker: peers. Peer workflow: peer price missing. Optional earnings or analyst-estimate context is unavailable until trusted local CSV rows exist. Next: Add trusted price history for mapped peers: DHR, TMO, WAT.

## What We Can Analyze Now
- Ready inputs: price, momentum, market direction, liquidity, correlation, fundamentals, DCF.
- Supported now: Company-level review can use local price context, fundamentals, and standalone DCF assumptions. Peer-relative valuation is shown only if trusted peer mappings and peer metrics are also ready.
- Still locked or excluded: Blocked features: earnings, analyst estimates. Excluded features: portfolio. Unavailable sections are intentionally locked; missing data is not inferred.

## Data Vs Product Logic
- Source inputs: local CSV rows or labeled provider-assisted rows supply prices, fundamentals, peers, earnings, and estimates.
- Product checks: project readiness gates decide whether each input is usable before report sections appear.
- Product DCF logic: calculated locally from trusted price, fundamentals, cash-flow or margin, share count, and cash/debt inputs; the report does not ask a third party or model to create a valuation opinion.
- Product peer logic: blocked locally until source-backed peer mappings and peer metrics exist; sector or industry fallback is not treated as trusted peer valuation.
- Optional context logic: locked locally until trusted earnings and analyst-estimate rows pass import validation; empty optional files are an intentional locked state, not hidden analysis.
- Output wording: supported, blocked, partial, and excluded sections are written from project code so missing data cannot become a weak conclusion.

## Analysis Quality
- Analysis mode: Standalone DCF review.
- Why: DCF assumptions can be reviewed, but peer-relative valuation remains limited until trusted peer inputs are ready.
- Optional context: Earnings and analyst estimates stay locked until trusted local rows exist.

## Methodology
- Method order: readiness gate first, supported analysis second, valuation math third, explanation last.
- Input boundary: local or provider-assisted rows supply data; project rules decide readiness, calculations, blockers, and report wording.
- Fundamental analysis: local revenue, cash-flow, margin, share-count, cash/debt, and source fields are reviewed only when present; missing fields are not inferred.
- DCF formula path: base FCF -> projected FCF -> discounted FCF plus discounted terminal value -> enterprise value -> equity value -> fair value per share.
- DCF status boundary: ready means assumptions can be reviewed, blocked means required company inputs are missing, and excluded means the method does not fit ETF/index/fund monitor context.
- DCF method: standalone DCF projects free cash flow under bear/base/bull assumptions, discounts projected cash flows and terminal value by WACC, adjusts for cash/debt or net debt, and divides by shares outstanding.
- Peer method: peer-relative valuation stays withheld until source-backed peer mappings and peer valuation inputs are ready.
- Score boundary: setup, watchlist, confidence, and monthly scores are triage aids for review order only; they are not price targets, expected returns, or allocation instructions.
- Report method: text is generated from local readiness, DCF, peer, decision, and source/freshness outputs; blocked or excluded sections are explained instead of filled.

## Evaluation Function Check
- Readiness gate: strongest function; it decides ready, blocked, or excluded before any conclusion is shown.
- Price and setup: ready for local trend/setup review.
- Risk context: ready for local liquidity/correlation context.
- Fundamentals / DCF: ready for standalone DCF assumptions and sensitivity review.
- Peer comparison: blocked until source-backed peer mappings and peer valuation inputs are ready.
- Optional context: locked until trusted local earnings and analyst-estimate rows exist.
- Logic source: readiness gates, DCF boundaries, peer blockers, and report wording are implemented in project code; standard libraries/adapters support data handling and UI, but shipped analysis comes from project code and local data.

## What This Stock Is
- Ticker: A
- Asset type: company
- Current role: Core Compounder. Test whether trend, fundamentals, and DCF support the long-duration thesis; current state is Setup Forming.

## Decision
- Bucket: Research Now
- Subtype: Research Candidate - DCF Ready But Peer Blocked
- Primary blocker: peers
- Main reason: Core data is ready for a supported research pass.
- Next action: Add trusted price history for mapped peers: DHR, TMO, WAT.

## Purpose Evaluation
Research-only purpose brief. It separates what local data supports from what remains locked or excluded.
- Thesis: Core Compounder. Test whether trend, fundamentals, and DCF support the long-duration thesis; current state is Setup Forming.
- Alignment: Purpose alignment appears consistent with current setup `Setup Forming` for Core Compounder, subject to the missing-data limits below.
- Operator summary: Purpose alignment appears consistent with current setup `Setup Forming` for Core Compounder, subject to the missing-data limits below; Research Candidate - DCF Ready But Peer Blocked. Next blocker: peers. Withheld: earnings timing or surprise context, analyst estimate trend context. Invalidation: Invalidate the compounder thesis review if trend conflict persists and updated fundamentals/DCF no longer support the stated purpose.
- Setup: Compounder setup: Setup Forming; final state: Setup Forming. Track trend quality alongside fundamentals and DCF before treating the long-duration thesis as well supported. Base score 68 from final state `Setup Forming`. Adjusted +0 points for value category `Insufficient Data`.
- Valuation boundary: DCF inputs are ready, but valuation interpretation is constrained by Insufficient Data and peer status `Insufficient Peer Data`.

## Supported Analysis
- Supported analysis: price history, setup and momentum context, market/theme context, liquidity context, correlation/risk context, fundamental context, standalone DCF scenario analysis. Partial inputs present: peer. Purpose-specific support: compounder review can use fundamentals and standalone DCF, but thesis quality still depends on trend and source freshness.

## Blocked Analysis
- Unsupported analysis: earnings timing or surprise context, analyst estimate trend context.

## Setup / Momentum
- Compounder setup: Setup Forming; final state: Setup Forming. Track trend quality alongside fundamentals and DCF before treating the long-duration thesis as well supported. Base score 68 from final state `Setup Forming`. Adjusted +0 points for value category `Insufficient Data`.
- 1M performance: -0.3%
- 3M performance: -7.5%
- 1Y performance: Not available
- ATR / volatility: Not available; missing values stay visible instead of guessed.

## Risk Notes
- Risk watchpoint: monitor setup deterioration, valuation-input quality, and missing optional context.
- Invalidation condition: Invalidate the compounder thesis review if trend conflict persists and updated fundamentals/DCF no longer support the stated purpose.

## Next Research Step
- Next research question: Do trend, fundamentals, DCF assumptions, and thesis conflict notes still support the compounder purpose?
- Review priority: High review priority: core company data is ready, but peer-relative context is still limiting valuation interpretation.
- Confidence explanation: Confidence is medium: core price, fundamentals, and DCF are ready; blockers still reduce breadth: earnings, analyst estimates.

## Data Readiness
- Overall state: partial
- Price ready: ready
- Momentum ready: ready
- Liquidity ready: ready
- Correlation ready: ready
- Fundamentals ready: ready
- DCF ready: ready
- Peer ready: not ready
- Earnings ready: not ready
- Analyst estimates ready: not ready
- Blocked features: earnings, analyst estimates
- Excluded features: portfolio

## Price Coverage
- Price rows: 616
- First date: 2023-12-11
- Last date: 2026-05-27
- Missing price reason: none

## Valuation Readiness
- DCF status: calculated.
- Base DCF fair value per share: $79.75.
- DCF input trace: base revenue=$4.5B; base FCF=$1.2B; FCF margin=25.8%; shares outstanding=282.6M; balance-sheet adjustment uses cash=$1.8B; debt=$3.0B.
- Base DCF assumptions: method=fcf_direct, revenue growth=6.4%, FCF margin=25.8%, WACC=9.0%, terminal growth=3.0%, forecast years=5.
- Scenario coverage: bear, base, bull.
- Sensitivity table: calculated; it tests fair value across WACC and terminal-growth assumptions when per-share DCF inputs are ready.
- Relative valuation: blocked until trusted peer mappings and peer valuation inputs are ready; current status=peer data unavailable; peer count=3.
- Valuation conclusion is shown only when trusted DCF and peer inputs support it; missing valuation inputs are not inferred.

## Peer Workflow
- Peer blocker type: peer price missing
- Mapping status: mapped
- Peer count: 3
- Trend comparison ready: not ready
- Valuation comparison ready: not ready
- DCF peer comparison ready: not ready
- Sample peers: DHR, TMO, WAT
- Next peer action: Add trusted price history for mapped peers: DHR, TMO, WAT.

## Missing Data
- 1Y performance is unavailable from the current local price history.
- No local analyst-estimate dataset is configured in the CSV-first pipeline.
- No local earnings dataset is configured in the CSV-first pipeline.
- Normalized growth target was reduced to keep it conservatively below WACC.
- Peer data is unavailable or insufficient, so only standalone multiples are shown.
- Peer inputs for p_fcf were unavailable for: DHR, TMO, WAT.
- Peer inputs for pe were unavailable for: DHR, TMO, WAT.
- Peer inputs for ps were unavailable for: DHR, TMO, WAT.
- Valuation missing field: ebitda
- analyst estimates has no local row for this ticker.
- earnings has no local row for this ticker.

## Source / Freshness
- local:prices.csv: research-grade / local; freshness: daily CSV through 2026-05-27; Saved local research data.
- local:fundamentals.csv: research-grade / local; freshness: dataset row as of 2017-10-31; Local fundamentals data.; Dataset row source: sec_companyfacts
- local:earnings.csv: research-grade / local; freshness: not available in local CSVs; Earnings fields are unavailable from the bundled local sample files.
- local:analyst_estimates.csv: research-grade / local; freshness: not available in local CSVs; Analyst estimate fields are unavailable from the bundled local sample files.

## Data Unlock Summary
- Price unlock: Price history is usable now (616 local row(s)); keep it fresh before relying on setup or risk context.
- Fundamentals / DCF unlock: Fundamentals and standalone DCF inputs are usable now; review assumptions, sensitivity, and source freshness before interpreting valuation context.
- Peer unlock: Peer context is the next unlock after DCF: Add trusted price history for mapped peers: DHR, TMO, WAT. Add source-backed mappings in `data/imports/peers.csv`.
- Optional context unlock: Earnings and analyst estimates remain optional and locked until trusted local rows are imported with `make templates`, `make imports-validate`, `make imports-preview`, and `make imports-apply`.
- Import paths, rejected-row files, and credential state are listed in the Source/Freshness Audit below.

## Copyable Unlock Commands
- Copy-only: these are local research commands to copy when you choose; the report does not execute imports, refreshes, broker actions, or trades.
- Inspect this ticker: `make stock-report-md TICKER=A`.
- Price freshness: `make focus-price TICKER=A`.
- DCF review: `make focus-fundamentals TICKER=A`.
- Peer mapping: `make focus-peers TICKER=A`.
- Peer queue: `make peer-mapping-queue TICKERS=A TOP_N=10`.
- Peer import safety: `make templates && make imports-validate && make imports-preview && make imports-apply`.
- Optional context queue: `make optional-context-worklist TICKERS=A TOP_N=10`.
- Optional templates: `make templates`.
- Earnings import: `make import-earnings`.
- Analyst-estimates import: `make import-analyst-estimates`.
- Optional import safety: `make imports-validate && make imports-preview && make imports-apply`.

## Source/Freshness Audit
- Prices: ready; local source `data/prices.csv`; coverage 2023-12-11 to 2026-05-27; rows=616; import draft path `data/staged/prices/` or `data/imports/prices.csv`; rejected rows `data/rejected/price_import_rejected.csv`.
- Fundamentals / DCF: ready; local source `data/fundamentals.csv`; SEC_USER_AGENT present; import draft path `data/staged/fundamentals/` or `data/imports/fundamentals.csv`; rejected rows `data/rejected/fundamentals_import_rejected.csv`.
- Peers: peer price missing; local source `data/peers.csv`; import draft path `data/imports/peers.csv`; next peer action Add trusted price history for mapped peers: DHR, TMO, WAT.
- Earnings: not ready; trusted local CSV only; import draft path `data/staged/earnings/`; command `make import-earnings`; rejected rows `data/rejected/earnings_import_rejected.csv`.
- Analyst estimates: not ready; trusted local CSV only; import draft path `data/staged/analyst_estimates/`; command `make import-analyst-estimates`; rejected rows `data/rejected/analyst_estimates_import_rejected.csv`.
- Credentials: SEC_USER_AGENT present; STOOQ_API_KEY missing; missing remote credentials should not break local CSV reports or preview-first local import workflows.
- Report command: `make stock-report-md TICKER=A`. Research-only Markdown output; copyable command only.
