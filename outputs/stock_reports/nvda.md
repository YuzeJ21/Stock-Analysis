# NVDA Single-Stock Research Report

Research-only local report. It summarizes readiness and does not provide allocation instructions.

## At A Glance
- Mode: `DCF-ready review`.
- Decision view: Research Candidate - Core Data Ready.
- DCF: Ready for scenario review.
- Peer context: Ready for source-backed peer review.
- Optional context: Locked until trusted earnings and analyst-estimate rows exist.
- Method: project readiness gates decide what can appear; DCF uses local free-cash-flow inputs, discounted cash flows, discounted terminal value, cash/debt adjustment, and fair value per share when ready.
- Next local step: Optional context missing for NVDA; leave unavailable unless trusted local CSVs exist.

## Reader Guide
- Analyze now: Company-level review can use local price context, fundamentals, and standalone DCF assumptions. Peer-relative valuation is shown only if trusted peer mappings and peer metrics are also ready.
- Still locked: Blocked features: earnings, analyst estimates. Excluded features: none. Unavailable sections are intentionally locked; missing data is not inferred.
- Trusted input: Trusted optional earnings or analyst-estimate CSV rows, only if you have a source you trust.
- Copy next: `make optional-context-worklist TICKERS=NVDA TOP_N=10`.
- Next research step: Optional context missing for NVDA; leave unavailable unless trusted local CSVs exist.

## How To Read This Report
- Read top-down: readiness state first, supported analysis second, blocked or excluded analysis third.
- Current use: DCF-ready review for company-level assumptions and sensitivity when trusted local fundamentals are ready.
- Logic source: project code implements readiness gates and report wording; libraries and adapters support data handling/UI, but shipped analysis comes from project code and local data.
- Boundary: this is research context only. It does not provide allocation instructions, account actions, or direct recommendations.

## Executive Summary
- Bottom line: NVDA is in `DCF-ready review` mode. Price, fundamentals, standalone DCF, and peer context are ready for a fuller research pass.
- Use now: Company-level review can use local price context, fundamentals, and standalone DCF assumptions. Peer-relative valuation is shown only if trusted peer mappings and peer metrics are also ready.
- Do not infer: Blocked features: earnings, analyst estimates. Excluded features: none. Unavailable sections are intentionally locked; missing data is not inferred.
- Next step: Optional context missing for NVDA; leave unavailable unless trusted local CSVs exist.

## Analysis Mode Guide
- `DCF-ready review` (current): Fullest company review: price, fundamentals, DCF, and source-backed peer context are ready.
- `Standalone DCF review` (other): Company DCF can be reviewed, but peer-relative valuation remains blocked.
- `Price/setup review only` (other): Use trend/setup context only; company valuation waits for trusted fundamentals and DCF inputs.
- `Monitor-only context` (other): Use ETF/index/fund market or risk context; operating-company DCF is excluded, not failed.
- `Data-unlock only` (other): Reference state for tickers with no trusted local inputs yet; add the first missing input before drawing conclusions.

## One-Minute Status
NVDA state: partial. Decision: Research Candidate - Core Data Ready. DCF: ready. Primary blocker: earnings. Peer workflow: ready for source-backed peer context. Optional earnings or analyst-estimate context is unavailable until trusted local CSV rows exist. Next: Optional context missing for NVDA; leave unavailable unless trusted local CSVs exist.

## What We Can Analyze Now
- Ready inputs: price, momentum, market direction, liquidity, correlation, fundamentals, DCF, peer, portfolio.
- Supported now: Company-level review can use local price context, fundamentals, and standalone DCF assumptions. Peer-relative valuation is shown only if trusted peer mappings and peer metrics are also ready.
- Still locked or excluded: Blocked features: earnings, analyst estimates. Excluded features: none. Unavailable sections are intentionally locked; missing data is not inferred.

## Data Vs Product Logic
- Source inputs: local CSV rows or labeled provider-assisted rows supply prices, fundamentals, peers, earnings, and estimates.
- Product checks: project readiness gates decide whether each input is usable before report sections appear.
- Product DCF logic: calculated locally from trusted price, fundamentals, cash-flow or margin, share count, and cash/debt inputs; the report does not ask a third party or model to create a valuation opinion.
- Product peer logic: available only from source-backed peer mappings and peer valuation inputs; sector or industry fallback is not treated as trusted peer valuation.
- Optional context logic: locked locally until trusted earnings and analyst-estimate rows pass import validation; empty optional files are an intentional locked state, not hidden analysis.
- Output wording: supported, blocked, partial, and excluded sections are written from project code so missing data cannot become a weak conclusion.

## Analysis Quality
- Analysis mode: DCF-ready review.
- Why: Price, fundamentals, standalone DCF, and peer context are ready for a fuller research pass.
- Optional context: Earnings and analyst estimates stay locked until trusted local rows exist.

## Methodology
- Method order: readiness gate first, supported analysis second, valuation math third, explanation last.
- Input boundary: local or provider-assisted rows supply data; project rules decide readiness, calculations, blockers, and report wording.
- Analysis recipe: prices unlock setup/trend review; fundamentals unlock field review and DCF input quality; DCF unlocks scenario math; source-backed peers unlock peer context; optional earnings and estimates add timing or consensus context only.
- Black-box check: every supported section should trace back to a ready input, a visible formula or score, or an explicit blocker listed in this report.
- Fundamental analysis: local revenue, cash-flow, margin, share-count, cash/debt, and source fields are reviewed only when present; missing fields are not inferred.
- DCF formula path: base FCF -> projected FCF -> discounted FCF plus discounted terminal value -> enterprise value -> equity value -> fair value per share.
- DCF status boundary: ready means assumptions can be reviewed, blocked means required company inputs are missing, and excluded means the method does not fit ETF/index/fund monitor context.
- DCF method: standalone DCF projects free cash flow under bear/base/bull assumptions, discounts projected cash flows and terminal value by WACC, adjusts for cash/debt or net debt, and divides by shares outstanding.
- Peer method: peer-relative valuation can be reviewed because source-backed peer inputs are ready.
- Score boundary: setup, watchlist, confidence, and monthly scores are triage aids for review order only; they are not price targets, expected returns, or allocation instructions.
- Report method: text is generated from local readiness, DCF, peer, decision, and source/freshness outputs; blocked or excluded sections are explained instead of filled.

## Evaluation Function Check
- Readiness gate: strongest function; it decides ready, blocked, or excluded before any conclusion is shown.
- Price and setup: ready for local trend/setup review.
- Risk context: ready for local liquidity/correlation context.
- Fundamentals / DCF: ready for standalone DCF assumptions and sensitivity review.
- Peer comparison: ready for peer-relative review.
- Optional context: locked until trusted local earnings and analyst-estimate rows exist.
- Logic source: readiness gates, DCF boundaries, peer blockers, and report wording are implemented in project code; standard libraries/adapters support data handling and UI, but shipped analysis comes from project code and local data.

## What This Stock Is
- Ticker: NVDA
- Asset type: company
- Current role: Momentum Leader. Judge the brief through trend, relative strength, extension risk, and setup quality; current state is Review Thesis.

## Decision
- Bucket: Research Now
- Subtype: Research Candidate - Core Data Ready
- Boundary: Workflow state only: ready for deeper manual research using supported local evidence, not a final conclusion.
- Primary blocker: earnings
- Main reason: Core data is ready for a supported research pass.
- Next action: Optional context missing for NVDA; leave unavailable unless trusted local CSVs exist.

## Purpose Evaluation
Research-only purpose brief. It separates what local data supports from what remains locked or excluded.
- Thesis: Momentum Leader. Judge the brief through trend, relative strength, extension risk, and setup quality; current state is Review Thesis.
- Alignment: Purpose alignment needs review: Momentum Leader requires relative strength support, but current local outputs flag weak relative strength.
- Operator summary: Purpose alignment needs review: Momentum Leader requires relative strength support, but current local outputs flag weak relative strength; Research Candidate - Core Data Ready. Next blocker: earnings. Withheld: earnings timing or surprise context, analyst estimate trend context. Invalidation: Invalidate the momentum research setup if relative strength weakens, trend support fails, or extension risk dominates the setup.
- Setup: Momentum setup: Setup Forming; final state: Review Thesis. Check relative strength, trend, volume context, and extension risk before deeper research. Base score 45 from final state `Review Thesis`. Added 3 points because the ticker is already a holding. Adjusted +0 points for value category `Insufficient Data`.
- Valuation boundary: Report-local peer valuation is calculated from trusted peer inputs; broad value labels may still remain limited when optional value-engine fields are missing.

## Supported Analysis
- Supported analysis: price history, setup and momentum context, market/theme context, liquidity context, correlation/risk context, fundamental context, standalone DCF scenario analysis, peer-relative comparison. Purpose-specific support: momentum review can use trend, setup, and relative-strength context, while valuation remains secondary.

## Blocked Analysis
- Unsupported analysis: earnings timing or surprise context, analyst estimate trend context.

## Setup / Momentum
- Momentum setup: Setup Forming; final state: Review Thesis. Check relative strength, trend, volume context, and extension risk before deeper research. Base score 45 from final state `Review Thesis`. Added 3 points because the ticker is already a holding. Adjusted +0 points for value category `Insufficient Data`.
- 1M performance: 7.9%
- 3M performance: 16.5%
- 1Y performance: 54.7%
- ATR / volatility: Not available; missing values stay visible instead of guessed.

## Risk Notes
- Risk watchpoint: momentum purpose is sensitive to relative-strength deterioration, extension risk, and trend breaks.
- Invalidation condition: Invalidate the momentum research setup if relative strength weakens, trend support fails, or extension risk dominates the setup.

## Next Research Step
- Next research question: Does relative strength, trend quality, and extension risk still support the momentum purpose after reviewing the latest local price context?
- Review priority: High review priority: momentum purpose has enough core data for trend/relative-strength review, but confirm setup quality manually.
- Data-confidence explanation: Data confidence is medium: core price, fundamentals, and DCF are ready; blockers still reduce breadth: earnings, analyst estimates.

## Data Readiness
- Overall state: partial
- Price ready: ready
- Momentum ready: ready
- Liquidity ready: ready
- Correlation ready: ready
- Fundamentals ready: ready
- DCF ready: ready
- Peer ready: ready
- Earnings ready: not ready
- Analyst estimates ready: not ready
- Blocked features: earnings, analyst estimates
- Excluded features: none

## Price Coverage
- Price rows: 621
- First date: 2023-12-07
- Last date: 2026-05-22
- Missing price reason: none

## Valuation Readiness
- DCF status: calculated.
- Base DCF fair value per share: $143.42.
- DCF input trace: base revenue=$215.9B; base FCF=$96.7B; FCF margin=44.8%; shares outstanding=24.2B; balance-sheet adjustment uses cash=$13.2B; debt=$8.5B.
- Base DCF assumptions: input path=direct free cash flow, revenue growth=40.0%, FCF margin=44.8%, WACC=9.0%, terminal growth=3.0%, forecast years=5.
- Scenario coverage: bear, base, bull.
- Sensitivity table: calculated; it tests fair value across WACC and terminal-growth assumptions when per-share DCF inputs are ready.
- Sensitivity snapshot: at WACC 9.0%, TG 2.0% -> $126.33; TG 3.0% -> $143.42; TG 4.0% -> $167.35.
- Relative valuation: calculated from trusted peer inputs, with caveats; peer count=2. Missing peer valuation fields: ebitda.
- Valuation conclusion is shown only when trusted DCF and peer inputs support it; missing valuation inputs are not inferred.

## DCF Calculation Path
- State: ready; standalone DCF math is calculated locally from trusted price and fundamentals inputs.
- Formula path: base FCF -> projected FCF -> discounted FCF plus discounted terminal value -> enterprise value -> equity value -> fair value per share.
- Input source: local price/fundamentals rows; base revenue=$215.9B; base FCF=$96.7B; shares outstanding=24.2B.
- Assumptions used: revenue growth=40.0%; FCF margin=44.8%; WACC=9.0%; terminal growth=3.0%; forecast years=5.
- Sensitivity: calculated; reader should compare WACC and terminal-growth cases before interpreting fair value.
- Sensitivity snapshot: at WACC 9.0%, TG 2.0% -> $126.33; TG 3.0% -> $143.42; TG 4.0% -> $167.35.
- Reader takeaway: this is scenario math and methodology evidence, not a price target or direct recommendation.

## DCF Input Triage
- DCF input triage: required inputs passed readiness for standalone DCF review.
- Next check: review assumptions, sensitivity, and source freshness; do not convert fair value math into a recommendation.

## Valuation Boundary Checklist
- DCF boundary: ready for assumption, scenario, and sensitivity review; still research context, not a price target.
- Peer-relative boundary: available only from trusted peer mappings and peer valuation inputs.
- Optional-context boundary: locked until trusted local earnings and analyst-estimate rows pass import validation.
- Conclusion boundary: missing or excluded inputs do not become intrinsic value, peer-relative value, undervalued, or overvalued conclusions.

## Peer Workflow
- What this means: peer context is ready from source-backed peer inputs; review mapped peers and freshness before interpreting relative valuation.
- What can be reviewed now: peer trend status=ready; peer valuation status=ready; peer count=2.
- What is still locked: any missing peer metric listed below stays unavailable and should not be inferred from sector or industry fallback.
- Trusted input path: review `data/peers.csv` and rerun `make focus-peers TICKER=NVDA` before relying on peer-relative context.
- Peer ladder: ready for source-backed peer context.
- Mapping evidence: mapping status=mapped; peer count=2.
- Trend evidence: ready from mapped peer price history.
- Valuation evidence: available only from trusted peer mappings and peer valuation inputs; review freshness before interpretation.
- Next safe command: `make focus-peers TICKER=NVDA` to inspect mapped peer evidence before reading relative context.
- Peer blocker type: ready
- Mapping status: mapped
- Peer count: 2
- Trend comparison ready: ready
- Valuation comparison ready: ready
- DCF peer comparison ready: ready
- Sample peers: AMD, AVGO
- Next peer action: Peer trend and valuation comparison are ready for NVDA.

## Optional Context Workflow
- Optional context ladder: earnings and analyst estimates add timing, consensus, and revision context only; they never create a valuation conclusion by themselves.
- Earnings evidence: locked; missing trusted local CSV input is an intentional state, not broken analysis. Use schema-only templates first; templates are not data.
- Analyst-estimate evidence: locked; missing trusted local CSV input is an intentional state, not hidden consensus analysis.
- Earnings path: `make templates` -> place trusted rows in `data/staged/earnings/` -> `make import-earnings` -> `make imports-validate` -> `make imports-preview` -> `make imports-apply`.
- Analyst-estimates path: `make templates` -> place trusted rows in `data/staged/analyst_estimates/` -> `make import-analyst-estimates` -> `make imports-validate` -> `make imports-preview` -> `make imports-apply`.
- Rejected-row checks: review `data/rejected/earnings_import_rejected.csv` and `data/rejected/analyst_estimates_import_rejected.csv` before trusting optional context.
- Rebuild proof: run `make optional-context-readiness`, then `make stock-report-md TICKER=NVDA` to confirm optional sections changed from locked to available.
- No-conclusion boundary: missing earnings or estimates must not appear as event timing, consensus, revision, upside, downside, undervalued, or overvalued analysis.

## Missing Data
- No local analyst-estimate dataset is configured in the CSV-first pipeline.
- No local earnings dataset is configured in the CSV-first pipeline.
- Normalized growth target was reduced to keep it conservatively below WACC.
- Observed FCF margin 47.8% exceeded the conservative margin cap of 45.0% and was normalized before projection.
- Observed revenue growth 61.5% exceeded the conservative start-growth cap of 40.0% and was normalized before projection.
- Observed revenue growth 65.5% exceeded the conservative start-growth cap of 40.0% and was normalized before projection.
- Observed revenue growth 69.5% exceeded the conservative start-growth cap of 40.0% and was normalized before projection.
- Valuation missing field: ebitda
- analyst estimates has no local row for this ticker.
- earnings has no local row for this ticker.

## Source / Freshness
- local:prices.csv: research-grade / local; freshness: daily CSV through 2026-05-22; Saved local research data.
- local:fundamentals.csv: research-grade / local; freshness: dataset row as of 2026-01-25; Local fundamentals data.; Dataset row source: sec_companyfacts
- local:earnings.csv: research-grade / local; freshness: not available in local CSVs; Earnings fields are unavailable from the bundled local sample files.
- local:analyst_estimates.csv: research-grade / local; freshness: not available in local CSVs; Analyst estimate fields are unavailable from the bundled local sample files.

## Data Unlock Summary
- Price unlock: Price history is usable now (621 local row(s)); keep it fresh before relying on setup or risk context.
- Fundamentals / DCF unlock: Fundamentals and standalone DCF inputs are usable now; review assumptions, sensitivity, and source freshness before interpreting valuation context.
- Peer unlock: Peer context is usable now; review mapped peers and freshness before interpreting peer-relative context.
- Optional context unlock: Earnings and analyst estimates remain optional and locked until trusted local rows are imported with `make templates`, `make imports-validate`, `make imports-preview`, and `make imports-apply`.
- Import paths, rejected-row files, and credential state are listed in the Source/Freshness Audit below.

## Copyable Unlock Commands
- Copy-only: these are local research commands to copy when you choose; the report does not execute imports, refreshes, broker actions, or trades.
- Inspect this ticker: `make stock-report-md TICKER=NVDA`.
- Price freshness: `make focus-price TICKER=NVDA`.
- DCF review: `make focus-fundamentals TICKER=NVDA`.
- Peer review: `make focus-peers TICKER=NVDA`.
- Optional context queue: `make optional-context-worklist TICKERS=NVDA TOP_N=10`.
- Optional templates: `make templates`.
- Earnings import: `make import-earnings`.
- Analyst-estimates import: `make import-analyst-estimates`.
- Optional import safety: `make imports-validate && make imports-preview && make imports-apply`.
- Optional-context rebuild proof: `make optional-context-readiness && make readiness` before treating earnings or estimates as available context.

## Source/Freshness Audit
- Prices: ready; local source `data/prices.csv`; coverage 2023-12-07 to 2026-05-22; rows=621; import draft path `data/staged/prices/` or `data/imports/prices.csv`; rejected rows `data/rejected/price_import_rejected.csv`.
- Fundamentals / DCF: ready; local source `data/fundamentals.csv`; SEC_USER_AGENT present; import draft path `data/staged/fundamentals/` or `data/imports/fundamentals.csv`; rejected rows `data/rejected/fundamentals_import_rejected.csv`.
- Peers: ready; local source `data/peers.csv`; import draft path `data/imports/peers.csv`; next peer action Peer trend and valuation comparison are ready for NVDA.
- Earnings: not ready; trusted local CSV only; import draft path `data/staged/earnings/`; command `make import-earnings`; rejected rows `data/rejected/earnings_import_rejected.csv`.
- Analyst estimates: not ready; trusted local CSV only; import draft path `data/staged/analyst_estimates/`; command `make import-analyst-estimates`; rejected rows `data/rejected/analyst_estimates_import_rejected.csv`.
- Credentials: SEC_USER_AGENT present; STOOQ_API_KEY missing; missing remote credentials should not break local CSV reports or preview-first local import workflows.
- Report command: `make stock-report-md TICKER=NVDA`. Research-only Markdown output; copyable command only.
