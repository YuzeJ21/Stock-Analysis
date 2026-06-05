# META Single-Stock Research Report

Research-only local report. It summarizes readiness and does not provide allocation instructions.

## At A Glance
- Mode: `Price/setup review only`.
- Decision view: Blocked by Data - Missing Fundamentals.
- DCF: Blocked until trusted fundamentals and DCF inputs are ready.
- Peer context: Locked until source-backed peer inputs are ready.
- Optional context: Locked until trusted earnings and analyst-estimate rows exist.
- Method: project readiness gates decide what can appear; DCF uses local free-cash-flow inputs, discounted cash flows, discounted terminal value, cash/debt adjustment, and fair value per share when ready.
- Next local step: Complete trusted fundamentals for META; missing fields: shares outstanding. Run `make focus-fundamentals TICKER=META`, then use SEC import draft workflow or the manual fundamentals import workflow.

## Reader Guide
- What can I analyze now? Use available price or setup context only. Company-level valuation stays blocked until trusted fundamentals, free cash flow or margin inputs, share count, and DCF fields are ready.
- What is still locked or excluded? Blocked features: DCF, earnings, analyst estimates. Excluded features: none. Unavailable sections are intentionally locked; missing data is not inferred.
- What trusted input matters next? Trusted fundamentals such as revenue, free cash flow or margin, and shares outstanding.
- Next copy-only command: `make focus-fundamentals TICKER=META`.
- Next research step: Complete trusted fundamentals for META; missing fields: shares outstanding. Run `make focus-fundamentals TICKER=META`, then use SEC import draft workflow or the manual fundamentals import workflow.

## How To Read This Report
- Read top-down: readiness state first, supported analysis second, blocked or excluded analysis third.
- Current use: Price/setup review only until trusted fundamentals, DCF, and peer inputs are ready.
- Logic source: project code implements readiness gates and report wording; libraries and adapters support data handling/UI, but shipped analysis comes from project code and local data.
- Boundary: this is research context only. It does not provide allocation instructions, account actions, or direct recommendations.

## Executive Summary
- Bottom line: META is in `Price/setup review only` mode. Use price and setup context only. Company valuation stays blocked until trusted fundamentals and DCF inputs exist.
- Use now: Use available price or setup context only. Company-level valuation stays blocked until trusted fundamentals, free cash flow or margin inputs, share count, and DCF fields are ready.
- Do not infer: Blocked features: DCF, earnings, analyst estimates. Excluded features: none. Unavailable sections are intentionally locked; missing data is not inferred.
- Next step: Complete trusted fundamentals for META; missing fields: shares outstanding. Run `make focus-fundamentals TICKER=META`, then use SEC import draft workflow or the manual fundamentals import workflow.

## Analysis Mode Guide
- `DCF-ready review` (other): Fullest company review: price, fundamentals, DCF, and source-backed peer context are ready.
- `Standalone DCF review` (other): Company DCF can be reviewed, but peer-relative valuation remains blocked.
- `Price/setup review only` (current): Use trend/setup context only; company valuation waits for trusted fundamentals and DCF inputs.
- `Monitor-only context` (other): Use ETF/index/fund market or risk context; operating-company DCF is excluded, not failed.
- `Data-unlock only` (other): Reference state for tickers with no trusted local inputs yet; add the first missing input before drawing conclusions.

## One-Minute Status
META state: partial. Decision: Blocked by Data - Missing Fundamentals. DCF: blocked. Primary blocker: fundamentals. Peer workflow: waits for trusted price, fundamentals, and DCF inputs first. Optional earnings or analyst-estimate context is unavailable until trusted local CSV rows exist. Next: Complete trusted fundamentals for META; missing fields: shares outstanding. Run `make focus-fundamentals TICKER=META`, then use SEC import draft workflow or the manual fundamentals import workflow.

## What We Can Analyze Now
- Ready inputs: price, momentum, market direction, liquidity, correlation, portfolio.
- Supported now: Use available price or setup context only. Company-level valuation stays blocked until trusted fundamentals, free cash flow or margin inputs, share count, and DCF fields are ready.
- Still locked or excluded: Blocked features: DCF, earnings, analyst estimates. Excluded features: none. Unavailable sections are intentionally locked; missing data is not inferred.

## Data Vs Product Logic
- Source inputs: local CSV rows or labeled provider-assisted rows supply prices, fundamentals, peers, earnings, and estimates.
- Product checks: project readiness gates decide whether each input is usable before report sections appear.
- Product DCF logic: blocked locally because required price, fundamentals, cash-flow or margin, share count, or DCF fields are missing; the report does not ask a third party or model to create a valuation opinion.
- Product peer logic: blocked locally until source-backed peer mappings and peer metrics exist; sector or industry fallback is not treated as trusted peer valuation.
- Optional context logic: locked locally until trusted earnings and analyst-estimate rows pass import validation; empty optional files are an intentional locked state, not hidden analysis.
- Output wording: supported, blocked, partial, and excluded sections are written from project code so missing data cannot become a weak conclusion.

## Analysis Quality
- Analysis mode: Price/setup review only.
- Why: Use price and setup context only. Company valuation stays blocked until trusted fundamentals and DCF inputs exist.
- Optional context: Earnings and analyst estimates stay locked until trusted local rows exist.

## Methodology
- Method order: readiness gate first, supported analysis second, valuation math third, explanation last.
- Input boundary: local or provider-assisted rows supply data; project rules decide readiness, calculations, blockers, and report wording.
- Fundamental analysis: local revenue, cash-flow, margin, share-count, cash/debt, and source fields are reviewed only when present; missing fields are not inferred.
- DCF formula path: base FCF -> projected FCF -> discounted FCF plus discounted terminal value -> enterprise value -> equity value -> fair value per share.
- DCF status boundary: ready means assumptions can be reviewed, blocked means required company inputs are missing, and excluded means the method does not fit ETF/index/fund monitor context.
- DCF method: standalone DCF stays blocked until trusted local price, revenue, free cash flow or FCF margin, shares outstanding, and DCF fields pass readiness checks.
- Peer method: peer-relative valuation stays withheld until source-backed peer mappings and peer valuation inputs are ready.
- Score boundary: setup, watchlist, confidence, and monthly scores are triage aids for review order only; they are not price targets, expected returns, or allocation instructions.
- Report method: text is generated from local readiness, DCF, peer, decision, and source/freshness outputs; blocked or excluded sections are explained instead of filled.

## Evaluation Function Check
- Readiness gate: strongest function; it decides ready, blocked, or excluded before any conclusion is shown.
- Price and setup: ready for local trend/setup review.
- Risk context: ready for local liquidity/correlation context.
- Fundamentals / DCF: blocked until trusted fundamentals, cash-flow or margin, share-count, and DCF inputs are ready.
- Peer comparison: blocked until source-backed peer mappings and peer valuation inputs are ready.
- Optional context: locked until trusted local earnings and analyst-estimate rows exist.
- Logic source: readiness gates, DCF boundaries, peer blockers, and report wording are implemented in project code; standard libraries/adapters support data handling and UI, but shipped analysis comes from project code and local data.

## What This Stock Is
- Ticker: META
- Asset type: company
- Current role: Core Compounder. Test whether trend, fundamentals, and DCF support the long-duration thesis; current state needs thesis review.

## Decision
- Bucket: Blocked by Data
- Subtype: Blocked by Data - Missing Fundamentals
- Boundary: Data-unlock state: fundamentals blocks evaluation, so conclusions stay withheld.
- Primary blocker: fundamentals
- Main reason: Company research is blocked by missing DCF data.
- Next action: Complete trusted fundamentals for META; missing fields: shares outstanding. Run `make focus-fundamentals TICKER=META`, then use SEC import draft workflow or the manual fundamentals import workflow.

## Purpose Evaluation
Research-only purpose brief. It separates what local data supports from what remains locked or excluded.
- Thesis: Core Compounder. Test whether trend, fundamentals, and DCF support the long-duration thesis; current state needs thesis review.
- Alignment: Purpose alignment needs review: Core Compounder depends on durable thesis support, but current local outputs flag trend/thesis conflict. Used holding primary purpose. Trend support failed below both 50SMA and 200SMA. Marked as Core Compounder but trend is below the 50SMA. Close is below the 50SMA. Position percent 0.00% is within allowed max 15.00%, portfolio concentration threshold 20.00%. Holding trend support failed. valuation is not ready: required DCF inputs are incomplete. Available fundamentals are too incomplete to support a reliable value classification. DCF readiness missing: shares outstanding. Trap flags: below 50SMA with no recovery. Not enough valuation multiples are available for a peer comparison. Missing data: EPS growth, gross margin, debt to equity, P/E, forward P/E, EV/sales, EV/EBITDA, price to free cash flow, FCF yield.
- Operator summary: Purpose alignment needs review: Core Compounder depends on durable thesis support, but current local outputs flag trend/thesis conflict. Used holding primary purpose. Trend support failed below both 50SMA and 200SMA. Marked as Core Compounder but trend is below the 50SMA. Close is below the 50SMA. Position percent 0.00% is within allowed max 15.00%, portfolio concentration threshold 20.00%. Holding trend support failed. valuation is not ready: required DCF inputs are incomplete. Available fundamentals are too incomplete to support a reliable value classification. DCF readiness missing: shares outstanding. Trap flags: below 50SMA with no recovery. Not enough valuation multiples are available for a peer comparison. Missing data: EPS growth, gross margin, debt to equity, P/E, forward P/E, EV/sales, EV/EBITDA, price to free cash flow, FCF yield; Blocked by Data - Missing Fundamentals. Next blocker: fundamentals. Withheld: DCF interpretation, earnings timing or surprise context, analyst estimate trend context, compounder thesis confirmation. Invalidation: Already flagged for trend/purpose review in the current local setup state.
- Setup: Compounder setup: Thesis Review Needed; final state: Thesis Review Needed. Trend conflict matters because it can challenge the stated long-duration purpose. Base score 10 from final state `Thesis Review Needed`. Added 3 points because the ticker is already a holding. Adjusted +0 points for value category `Insufficient Data`. Capped score at 50 because valuation readiness is not ready; treat as data-limited review until missing data is resolved.
- Valuation boundary: Valuation conclusion is blocked until trusted DCF/fundamental inputs are complete.

## Supported Analysis
- Supported analysis: price history, setup and momentum context, market/theme context, liquidity context, correlation/risk context. Partial inputs present: fundamentals, peer.

## Blocked Analysis
- Unsupported analysis: DCF interpretation, earnings timing or surprise context, analyst estimate trend context, compounder thesis confirmation.

## Setup / Momentum
- Compounder setup: Thesis Review Needed; final state: Thesis Review Needed. Trend conflict matters because it can challenge the stated long-duration purpose. Base score 10 from final state `Thesis Review Needed`. Added 3 points because the ticker is already a holding. Adjusted +0 points for value category `Insufficient Data`. Capped score at 50 because valuation readiness is not ready; treat as data-limited review until missing data is resolved.
- 1M performance: -7.4%
- 3M performance: -4.2%
- 1Y performance: -4.0%
- ATR / volatility: Not available; missing values stay visible instead of guessed.

## Risk Notes
- Risk watchpoint: compounder purpose is under thesis review because final state is `Thesis Review Needed`. Used holding primary purpose. Trend support failed below both 50SMA and 200SMA. Marked as Core Compounder but trend is below the 50SMA. Close is below the 50SMA. Position percent 0.00% is within allowed max 15.00%, portfolio concentration threshold 20.00%. Holding trend support failed. valuation is not ready: required DCF inputs are incomplete. Available fundamentals are too incomplete to support a reliable value classification. DCF readiness missing: shares outstanding. Trap flags: below 50SMA with no recovery. Not enough valuation multiples are available for a peer comparison. Missing data: EPS growth, gross margin, debt to equity, P/E, forward P/E, EV/sales, EV/EBITDA, price to free cash flow, FCF yield.
- Invalidation condition: Already flagged for trend/purpose review in the current local setup state.

## Next Research Step
- Next research question: Which trusted fundamentals or DCF fields are needed to confirm whether the compounder thesis remains supported?
- Review priority: High review priority: compounder purpose conflicts with current trend/thesis state and needs manual thesis review.
- Confidence explanation: Confidence is low: primary blocker is fundamentals; blocked features are DCF, earnings, analyst estimates.

## Data Readiness
- Overall state: partial
- Price ready: ready
- Momentum ready: ready
- Liquidity ready: ready
- Correlation ready: ready
- Fundamentals ready: not ready
- DCF ready: not ready
- Peer ready: not ready
- Earnings ready: not ready
- Analyst estimates ready: not ready
- Blocked features: DCF, earnings, analyst estimates
- Excluded features: none

## Price Coverage
- Price rows: 616
- First date: 2023-12-07
- Last date: 2026-05-22
- Missing price reason: none

## Valuation Readiness
- DCF status: blocked.
- DCF missing inputs: shares outstanding.
- Why DCF is blocked: missing shares outstanding.
- DCF assumptions: withheld until price, fundamentals, free cash flow or FCF margin, and share-count inputs are ready.
- Sensitivity table: unavailable until the base DCF can be calculated.
- Relative valuation: withheld until trusted fundamentals and DCF readiness pass; background relative-multiple calculation is not reader-ready yet (status=calculated; peer count=2).
- Valuation conclusion is shown only when trusted DCF and peer inputs support it; missing valuation inputs are not inferred.

## DCF Calculation Path
- State: blocked; the product withholds DCF math until trusted company inputs pass readiness checks.
- Required local inputs: trusted price, revenue, free cash flow or FCF margin, shares outstanding, and cash/debt or net-debt context.
- Missing now: shares outstanding.
- Formula path: withheld before base FCF, projected FCF, terminal value, equity value, or fair value/share are calculated.
- Sensitivity: unavailable until the base DCF can be calculated from trusted inputs.

## Valuation Boundary Checklist
- DCF boundary: blocked until trusted price, fundamentals, cash-flow or margin, share-count, and DCF fields pass readiness.
- Peer-relative boundary: withheld until trusted fundamentals and DCF readiness pass first.
- Optional-context boundary: locked until trusted local earnings and analyst-estimate rows pass import validation.
- Conclusion boundary: missing or excluded inputs do not become intrinsic value, peer-relative value, undervalued, or overvalued conclusions.

## Peer Workflow
- Peer blocker type: blocked until fundamentals / DCF
- Mapping status: waiting for price, fundamentals, and DCF
- Peer count: 2
- Trend comparison ready: not ready
- Valuation comparison ready: not ready
- DCF peer comparison ready: not ready
- Sample peers: AAPL, GOOG
- Next peer action: Peer-relative valuation should wait until trusted price, fundamentals, and DCF inputs are ready.

## Missing Data
- Fair value per share could not be derived because shares outstanding is unavailable.
- No local analyst-estimate dataset is configured in the CSV-first pipeline.
- No local earnings dataset is configured in the CSV-first pipeline.
- Normalized growth target was reduced to keep it conservatively below WACC.
- Observed FCF margin 110.4% exceeded the conservative margin cap of 45.0% and was normalized before projection.
- Observed FCF margin 113.4% exceeded the conservative margin cap of 45.0% and was normalized before projection.
- Observed FCF margin 116.4% exceeded the conservative margin cap of 45.0% and was normalized before projection.
- Observed revenue growth 43.1% exceeded the conservative start-growth cap of 40.0% and was normalized before projection.
- Observed revenue growth 47.1% exceeded the conservative start-growth cap of 40.0% and was normalized before projection.
- Observed revenue growth 51.1% exceeded the conservative start-growth cap of 40.0% and was normalized before projection.
- Peer inputs for pe were unavailable for: GOOG.
- Valuation missing field: ebitda
- Valuation missing field: market cap, price, and share count
- Valuation missing field: shares outstanding
- analyst estimates has no local row for this ticker.
- earnings has no local row for this ticker.

## Source / Freshness
- local:prices.csv: research-grade / local; freshness: daily CSV through 2026-05-22; Saved local research data.
- local:fundamentals.csv: research-grade / local; freshness: dataset row as of 2017-12-31; Local fundamentals data.; Dataset row source: sec_companyfacts
- local:earnings.csv: research-grade / local; freshness: not available in local CSVs; Earnings fields are unavailable from the bundled local sample files.
- local:analyst_estimates.csv: research-grade / local; freshness: not available in local CSVs; Analyst estimate fields are unavailable from the bundled local sample files.

## Data Unlock Summary
- Price unlock: Price history is usable now (616 local row(s)); keep it fresh before relying on setup or risk context.
- Fundamentals / DCF unlock: Fundamentals / DCF are blocked: missing shares outstanding. Run `make focus-fundamentals TICKER=META` before looking for valuation context.
- Peer unlock: Peer valuation should wait until trusted price, fundamentals, and DCF inputs are ready.
- Optional context unlock: Earnings and analyst estimates remain optional and locked until trusted local rows are imported with `make templates`, `make imports-validate`, `make imports-preview`, and `make imports-apply`.
- Import paths, rejected-row files, and credential state are listed in the Source/Freshness Audit below.

## Copyable Unlock Commands
- Copy-only: these are local research commands to copy when you choose; the report does not execute imports, refreshes, broker actions, or trades.
- Inspect this ticker: `make stock-report-md TICKER=META`.
- Price freshness: `make focus-price TICKER=META`.
- Fundamentals / DCF: `make focus-fundamentals TICKER=META`.
- SEC/manual import review: `make sec-stage-queue TICKERS=META TOP_N=10`.
- Fundamentals import safety: `make imports-validate && make imports-preview && make imports-apply`.
- Peer mapping: `make focus-peers TICKER=META`.
- Peer queue: `make peer-mapping-queue TICKERS=META TOP_N=10`.
- Peer import safety: `make templates && make imports-validate && make imports-preview && make imports-apply`.
- Optional context queue: `make optional-context-worklist TICKERS=META TOP_N=10`.
- Optional templates: `make templates`.
- Earnings import: `make import-earnings`.
- Analyst-estimates import: `make import-analyst-estimates`.
- Optional import safety: `make imports-validate && make imports-preview && make imports-apply`.

## Source/Freshness Audit
- Prices: ready; local source `data/prices.csv`; coverage 2023-12-07 to 2026-05-22; rows=616; import draft path `data/staged/prices/` or `data/imports/prices.csv`; rejected rows `data/rejected/price_import_rejected.csv`.
- Fundamentals / DCF: blocked; local source `data/fundamentals.csv`; reason missing shares outstanding; SEC_USER_AGENT present; import draft path `data/staged/fundamentals/` or `data/imports/fundamentals.csv`; rejected rows `data/rejected/fundamentals_import_rejected.csv`.
- Peers: blocked until fundamentals / DCF; local source `data/peers.csv`; import draft path `data/imports/peers.csv`; next peer action Peer-relative valuation should wait until trusted price, fundamentals, and DCF inputs are ready.
- Earnings: not ready; trusted local CSV only; import draft path `data/staged/earnings/`; command `make import-earnings`; rejected rows `data/rejected/earnings_import_rejected.csv`.
- Analyst estimates: not ready; trusted local CSV only; import draft path `data/staged/analyst_estimates/`; command `make import-analyst-estimates`; rejected rows `data/rejected/analyst_estimates_import_rejected.csv`.
- Credentials: SEC_USER_AGENT present; STOOQ_API_KEY missing; missing remote credentials should not break local CSV reports or preview-first local import workflows.
- Report command: `make stock-report-md TICKER=META`. Research-only Markdown output; copyable command only.
