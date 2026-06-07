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

## Reader Guide
- Analyze now: Company-level review can use local price context, fundamentals, and standalone DCF assumptions. Peer-relative valuation is shown only if trusted peer mappings and peer metrics are also ready.
- Still locked: Blocked features: earnings, analyst estimates. Excluded features: portfolio. Unavailable sections are intentionally locked; missing data is not inferred.
- Trusted input: Source-backed peer mappings and peer valuation inputs.
- Data Health lane: Peer Mapping Unlock. Suggested local check: `make focus-peers TICKER=A`. Confirm with `make readiness && make peer-mapping-queue TICKERS=A TOP_N=10` before treating the lane as unlocked.
- Next research step: Add trusted price history for mapped peers: DHR, TMO, WAT.

## Best Review Path
- First read: Start with DCF Calculation Path and Valuation Boundary Checklist. Peer-relative valuation stays locked until source-backed peer inputs pass readiness.
- Then check: What We Can Analyze Now, Valuation Boundary Checklist, and Source Readiness Check.
- Optional context: Optional earnings and analyst-estimate context remains locked unless trusted local rows exist.
- Copy-only proof step: `make focus-peers TICKER=A`

## How To Read This Report
- Read top-down: readiness state first, supported analysis second, blocked or excluded analysis third.
- Current use: Standalone DCF review: company DCF assumptions can be reviewed, while peer-relative valuation stays locked until source-backed peer inputs are ready.
- Method source: project code implements readiness gates and report wording; libraries and adapters support data handling/UI, but shipped analysis comes from project code and local data.
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

## Data And App Method
- Source inputs: local CSV rows or labeled provider-assisted rows supply prices, fundamentals, peers, earnings, and estimates.
- Product checks: project readiness gates decide whether each input is usable before report sections appear.
- DCF method: calculated locally from trusted price, fundamentals, cash-flow or margin, share count, and cash/debt inputs; the report does not ask a third party or model to create a valuation opinion.
- Peer method: blocked locally until source-backed peer mappings and peer metrics exist; sector or industry fallback is not treated as trusted peer valuation.
- Optional context method: locked locally until trusted earnings and analyst-estimate rows pass import validation; empty optional files are an intentional locked state, not hidden analysis.
- Output wording: supported, blocked, partial, and excluded sections are written from project code so missing data cannot become a weak conclusion.

## Analysis Quality
- Analysis mode: Standalone DCF review.
- Confidence: medium: standalone DCF inputs are ready, but peer-relative valuation remains locked.
- Why: DCF assumptions can be reviewed, but peer-relative valuation remains limited until trusted peer inputs are ready.
- Optional context: Earnings and analyst estimates stay locked until trusted local rows exist.

## Methodology
- Method order: readiness gate first, supported analysis second, valuation math third, explanation last.
- Input boundary: local or provider-assisted rows supply data; project rules decide readiness, calculations, blockers, and report wording.
- Analysis recipe: prices unlock setup/trend review; fundamentals unlock field review and DCF input quality; DCF unlocks scenario math; source-backed peers unlock peer context; optional earnings and estimates add timing or consensus context only.
- Black-box check: every supported section should trace back to a ready input, a visible formula or score, or an explicit blocker listed in this report.
- Methodology proof ladder: input row -> readiness gate -> local calculation or score -> supported/blocked/excluded label -> explicit next step.
- Reader check path: start with Source Readiness, then Data Readiness, then DCF Calculation Path or Peer Workflow; if any step is missing, the related conclusion stays withheld.
- Fundamental analysis: local revenue, cash-flow, margin, share-count, cash/debt, and source fields are reviewed only when present; missing fields are not inferred.
- DCF formula path: base FCF -> projected FCF -> discounted FCF plus discounted terminal value -> enterprise value -> equity value -> fair value per share.
- DCF status boundary: ready means assumptions can be reviewed, blocked means required company inputs are missing, and excluded means the method does not fit ETF/index/fund monitor context.
- DCF method: standalone DCF projects free cash flow under bear/base/bull assumptions, discounts projected cash flows and terminal value by WACC, adjusts for cash/debt or net debt, and divides by shares outstanding.
- Peer method: peer-relative valuation stays withheld until source-backed peer mappings and peer valuation inputs are ready.
- Score boundary: setup, watchlist, confidence, and monthly scores are triage aids for review order only; they are not price targets, expected returns, or allocation instructions.
- Report method: text is built from local readiness, DCF, peer, decision, and source readiness outputs; blocked or excluded sections are explained instead of filled.

## Evaluation Function Check
- Readiness gate: strongest function; it decides ready, blocked, or excluded before any conclusion is shown.
- Price and setup: ready for local trend/setup review.
- Risk context: ready for local liquidity/correlation context.
- Fundamentals / DCF: ready for standalone DCF assumptions and sensitivity review.
- Peer comparison: blocked until source-backed peer mappings and peer valuation inputs are ready.
- Optional context: locked until trusted local earnings and analyst-estimate rows exist.
- Method source: readiness gates, DCF boundaries, peer blockers, and report wording are implemented in project code; standard libraries/adapters support data handling and UI, but shipped analysis comes from project code and local data.

## What This Stock Is
- Ticker: A
- Asset type: company
- Current role: Core Compounder. Test whether trend, fundamentals, and DCF support the long-duration thesis; current state is Setup Forming.

## Decision
- Bucket: Research Now
- Subtype: Research Candidate - DCF Ready But Peer Blocked
- Boundary: Workflow state only: standalone company and DCF review can continue, but peer-relative valuation stays locked until trusted peer inputs are ready.
- Primary blocker: peers
- Main reason: Core data is ready for a supported research pass.
- Next action: Add trusted price history for mapped peers: DHR, TMO, WAT.

## Purpose Evaluation
Research-only purpose brief. It separates what local data supports from what remains locked or excluded.
- Thesis: Core Compounder. Test whether trend, fundamentals, and DCF support the long-duration thesis; current state is Setup Forming.
- Alignment: Purpose alignment appears consistent with current setup `Setup Forming` for Core Compounder, subject to the missing-data limits below.
- Research review summary: Purpose alignment appears consistent with current setup `Setup Forming` for Core Compounder, subject to the missing-data limits below; Research Candidate - DCF Ready But Peer Blocked. Next blocker: peers. Withheld: peer-relative valuation or opportunity-cost comparison, earnings timing or surprise context, analyst estimate trend context. Invalidation: Invalidate the compounder thesis review if trend conflict persists and updated fundamentals/DCF no longer support the stated purpose.
- Setup: Compounder setup: Setup Forming; final state: Setup Forming. Track trend quality alongside fundamentals and DCF before treating the long-duration thesis as well supported. Base score 68 from final state `Setup Forming`. Adjusted +0 points for value category `Insufficient Data`.
- Valuation boundary: DCF inputs are ready, but valuation interpretation is constrained by Insufficient Data and peer status `Insufficient Peer Data`.

## Supported Analysis
- Supported analysis: price history, setup and momentum context, market/theme context, liquidity context, correlation/risk context, fundamental context, standalone DCF scenario analysis. Purpose-specific support: compounder review can use fundamentals and standalone DCF, but thesis quality still depends on trend and source readiness.

## Blocked Analysis
- Unsupported analysis: peer-relative valuation or opportunity-cost comparison, earnings timing or surprise context, analyst estimate trend context.

## Setup / Momentum
- Compounder setup: Setup Forming; final state: Setup Forming. Track trend quality alongside fundamentals and DCF before treating the long-duration thesis as well supported. Base score 68 from final state `Setup Forming`. Adjusted +0 points for value category `Insufficient Data`.
- 1M performance: -0.3%
- 3M performance: -7.5%
- 1Y performance: Not available
- ATR / volatility: Not available; missing values stay visible instead of guessed.

## Risk Notes
- Risk watchpoint: peer-relative context is incomplete, so valuation comparison and opportunity cost remain uncertain.
- Invalidation condition: Invalidate the compounder thesis review if trend conflict persists and updated fundamentals/DCF no longer support the stated purpose.

## Next Research Step
- Next research question: Do trend, fundamentals, DCF assumptions, and thesis conflict notes still support the compounder purpose?
- Review priority: High review priority: core company data is ready, but peer-relative context is still limiting valuation interpretation.
- Data-confidence explanation: Data confidence is medium: core price, fundamentals, and DCF are ready; blockers still reduce breadth: peer, earnings, analyst estimates.

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
- Base DCF assumptions: input path=direct free cash flow, revenue growth=6.4%, FCF margin=25.8%, WACC=9.0%, terminal growth=3.0%, forecast years=5.
- Scenario coverage: bear, base, bull.
- Sensitivity table: calculated; it tests fair value across WACC and terminal-growth assumptions when per-share DCF inputs are ready.
- Sensitivity snapshot: at WACC 9.0%, TG 2.0% -> $69.94; TG 3.0% -> $79.75; TG 4.0% -> $93.49.
- Relative valuation: blocked until trusted peer mappings and peer valuation inputs are ready; current status=peer data unavailable; peer count=3.
- Valuation conclusion is shown only when trusted DCF and peer inputs support it; missing valuation inputs are not inferred.

## DCF Calculation Path
- State: ready; standalone DCF math is calculated locally from trusted price and fundamentals inputs.
- Formula path: base FCF -> projected FCF -> discounted FCF plus discounted terminal value -> enterprise value -> equity value -> fair value per share.
- Input source: local price/fundamentals rows; base revenue=$4.5B; base FCF=$1.2B; shares outstanding=282.6M.
- Assumptions used: revenue growth=6.4%; FCF margin=25.8%; WACC=9.0%; terminal growth=3.0%; forecast years=5.
- Sensitivity: calculated; reader should compare WACC and terminal-growth cases before interpreting fair value.
- Sensitivity snapshot: at WACC 9.0%, TG 2.0% -> $69.94; TG 3.0% -> $79.75; TG 4.0% -> $93.49.
- Reader takeaway: this is scenario math and methodology evidence, not a price target or direct recommendation.

## DCF Input Triage
- DCF input triage: required inputs passed readiness for standalone DCF review.
- Next check: review assumptions, sensitivity, and source readiness; do not convert fair value math into a recommendation.

## Valuation Boundary Checklist
- DCF boundary: ready for assumption, scenario, and sensitivity review; still research context, not a price target.
- Peer-relative boundary: blocked until source-backed peer mappings and peer valuation inputs pass readiness.
- Optional-context boundary: locked until trusted local earnings and analyst-estimate rows pass import validation.
- Conclusion boundary: missing or excluded inputs do not become intrinsic value, peer-relative value, undervalued, or overvalued conclusions.

## Peer Workflow
- What this means: standalone DCF can be reviewed, but peer-relative valuation is locked by peer price missing.
- What can be reviewed now: DCF assumptions and sensitivity; peer trend status=not ready until mapped peer price history is sufficient. Mapped peer count=3.
- What is still locked: peer valuation, peer-relative premium/discount, and peer DCF comparison until source-backed peer mappings and peer valuation inputs pass readiness.
- Trusted input path: add source-backed rows in `data/imports/peers.csv`, then run `make templates`, `make imports-validate`, `make imports-preview`, and `make imports-apply`.
- Next peer action: Add trusted price history for mapped peers: DHR, TMO, WAT.
- Fallback boundary: sector or industry context is fallback only; it is not trusted manual peer data. Current mapping status=mapped.
- Peer ladder: standalone DCF can be reviewed before peer valuation is ready.
- Mapping evidence: mapping status=mapped; peer count=3; blocker=peer price missing.
- Trend evidence: not ready until mapped peer price history is sufficient.
- Valuation evidence: locked; do not show peer-relative premium/discount, peer valuation comparison, or peer DCF comparison.
- Trusted peer path: add source-backed rows in `data/imports/peers.csv`, then run `make imports-validate`, `make imports-preview`, `make imports-apply`, `make readiness`, and `make peer-mapping-queue TOP_N=25`.
- Peer blocker type: peer price missing
- Mapping status: mapped
- Peer count: 3
- Trend comparison ready: not ready
- Valuation comparison ready: not ready
- DCF peer comparison ready: not ready
- Sample peers: DHR, TMO, WAT
- Next peer action: Add trusted price history for mapped peers: DHR, TMO, WAT.

## Optional Context Workflow
- Optional context ladder: earnings and analyst estimates add timing, consensus, and revision context only; they never create a valuation conclusion by themselves.
- Earnings evidence: locked; missing trusted local CSV input is an intentional state, not broken analysis. Use schema-only templates first; templates are not data.
- Analyst-estimate evidence: locked; missing trusted local CSV input is an intentional state, not hidden consensus analysis.
- Earnings path: `make templates` -> place trusted rows in `data/staged/earnings/` -> `make import-earnings` -> `make imports-validate` -> `make imports-preview` -> `make imports-apply`.
- Analyst-estimates path: `make templates` -> place trusted rows in `data/staged/analyst_estimates/` -> `make import-analyst-estimates` -> `make imports-validate` -> `make imports-preview` -> `make imports-apply`.
- Rejected-row checks: review `data/rejected/earnings_import_rejected.csv` and `data/rejected/analyst_estimates_import_rejected.csv` before trusting optional context.
- Rebuild proof: run `make optional-context-readiness`, then `make stock-report-md TICKER=A` to confirm optional sections changed from locked to available.
- No-conclusion boundary: missing earnings or estimates must not appear as event timing, consensus, revision, upside, downside, undervalued, or overvalued analysis.

## Missing Data
- 1Y performance is unavailable from the current local price history.
- No trusted analyst-estimate CSV has been added yet.
- No trusted earnings CSV has been added yet.
- Normalized growth target was reduced to keep it conservatively below WACC.
- Peer data is unavailable or insufficient, so only standalone multiples are shown.
- Peer inputs for p_fcf were unavailable for: DHR, TMO, WAT.
- Peer inputs for pe were unavailable for: DHR, TMO, WAT.
- Peer inputs for ps were unavailable for: DHR, TMO, WAT.
- Valuation missing field: ebitda
- analyst estimates has no local row for this ticker.
- earnings has no local row for this ticker.

## Source Readiness
- local:prices.csv: research-grade / local; source readiness: daily CSV through 2026-05-27; Saved local research data.
- local:fundamentals.csv: research-grade / local; source readiness: dataset row as of 2017-10-31; Local fundamentals data.; Dataset row source: sec_companyfacts
- local:earnings.csv: research-grade / local; source readiness: not available in local CSVs; Earnings fields stay locked until trusted rows are imported.
- local:analyst_estimates.csv: research-grade / local; source readiness: not available in local CSVs; Analyst-estimate fields stay locked until trusted rows are imported.

## Data Unlock Summary
- Data Health lane: Peer Mapping Unlock. Suggested local check: `make focus-peers TICKER=A`. Confirm with `make readiness && make peer-mapping-queue TICKERS=A TOP_N=10` before treating the lane as unlocked.
- Price unlock: Price history is usable now (616 local row(s)); keep it fresh before relying on setup or risk context.
- Fundamentals / DCF unlock: Fundamentals and standalone DCF inputs are usable now; review assumptions, sensitivity, and source readiness before interpreting valuation context.
- Peer unlock: Peer context is the next unlock after DCF: Add trusted price history for mapped peers: DHR, TMO, WAT. Add source-backed mappings in `data/imports/peers.csv`.
- Optional context unlock: Earnings and analyst estimates remain optional and locked until trusted local rows are imported with `make templates`, `make imports-validate`, `make imports-preview`, and `make imports-apply`.
- Import paths, rejected-row files, and credential state are listed in the Source Readiness Check below.

## Copyable Unlock Commands
- Copy-only: these are local research commands to copy when you choose; the report does not execute imports, refreshes, broker actions, or trades.
- Inspect this ticker: `make stock-report-md TICKER=A`.
- Price source readiness: `make focus-price TICKER=A`.
- DCF review: `make focus-fundamentals TICKER=A`.
- Peer mapping: `make focus-peers TICKER=A`.
- Peer mapping checklist: `make peer-mapping-queue TICKERS=A TOP_N=10`.
- Peer import safety: `make templates && make imports-validate && make imports-preview && make imports-apply`.
- Peer rebuild proof: `make readiness && make peer-mapping-queue TICKERS=A TOP_N=10` before reading peer-relative valuation.
- Optional context checklist: `make optional-context-worklist TICKERS=A TOP_N=10`.
- Optional templates: `make templates`.
- Earnings import: `make import-earnings`.
- Analyst-estimates import: `make import-analyst-estimates`.
- Optional import safety: `make imports-validate && make imports-preview && make imports-apply`.
- Optional-context rebuild proof: `make optional-context-readiness && make readiness` before treating earnings or estimates as available context.

## Source Readiness Check
- Prices: ready; local source `data/prices.csv`; coverage 2023-12-11 to 2026-05-27; rows=616; import file path `data/staged/prices/` or `data/imports/prices.csv`; rejected rows `data/rejected/price_import_rejected.csv`.
- Fundamentals / DCF: ready; local source `data/fundamentals.csv`; SEC_USER_AGENT present; import file path `data/staged/fundamentals/` or `data/imports/fundamentals.csv`; rejected rows `data/rejected/fundamentals_import_rejected.csv`.
- Peers: peer price missing; local source `data/peers.csv`; import file path `data/imports/peers.csv`; next peer action Add trusted price history for mapped peers: DHR, TMO, WAT.
- Earnings: not ready; trusted local CSV only; import file path `data/staged/earnings/`; command `make import-earnings`; rejected rows `data/rejected/earnings_import_rejected.csv`.
- Analyst estimates: not ready; trusted local CSV only; import file path `data/staged/analyst_estimates/`; command `make import-analyst-estimates`; rejected rows `data/rejected/analyst_estimates_import_rejected.csv`.
- Credentials: SEC_USER_AGENT present; STOOQ_API_KEY missing; missing remote credentials should not break local CSV reports or preview-first local import workflows.
- Report command: `make stock-report-md TICKER=A`. Research-only Markdown output; copyable command only.
