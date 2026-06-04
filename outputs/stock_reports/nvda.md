# NVDA Single-Stock Research Report

Research-only local report. It summarizes readiness and does not provide allocation instructions.

## How To Read This Report
- Read top-down: readiness state first, supported analysis second, blocked or excluded analysis third.
- Current use: Good enough for company-level DCF assumption and sensitivity review when trusted local fundamentals are ready.
- Logic source: repo-native code under `src/`; libraries and adapters support data handling/UI, and external plugins are development aids, not runtime analysis engines.
- Boundary: this is research context only. It does not provide allocation instructions, account actions, or direct recommendations.

## Executive Summary
NVDA state: partial. Decision: Research Candidate - Core Data Ready. DCF: ready. Primary blocker: earnings. Peer workflow: Not available. Optional earnings or analyst-estimate context is unavailable until trusted local CSV rows exist. Next: Optional context missing for NVDA; leave unavailable unless trusted local CSVs exist.

## One-Minute Status
NVDA state: partial. Decision: Research Candidate - Core Data Ready. DCF: ready. Primary blocker: earnings. Peer workflow: Not available. Optional earnings or analyst-estimate context is unavailable until trusted local CSV rows exist. Next: Optional context missing for NVDA; leave unavailable unless trusted local CSVs exist.

## What We Can Analyze Now
- Ready inputs: price, momentum, market_direction, liquidity, correlation, fundamentals, dcf, peer, portfolio.
- Supported now: Company-level review can use local price context, fundamentals, and standalone DCF assumptions. Peer-relative valuation is shown only if trusted peer mappings and peer metrics are also ready.
- Still locked or excluded: Blocked features: earnings, analyst_estimates. Excluded features: Not available. Unavailable sections are intentionally locked; missing data is not inferred.

## Analysis Quality
- Current quality label: Good for deeper company review.
- Why: Price, fundamentals, standalone DCF, and peer context are ready enough for a fuller research pass.
- Optional context: Earnings and analyst estimates stay locked until trusted local rows exist.

## Evaluation Function Check
- Readiness gate: strongest function; it decides ready, blocked, or excluded before any conclusion is shown.
- Price and setup: ready for local trend/setup review.
- Risk context: ready for local liquidity/correlation context.
- Fundamentals / DCF: ready for standalone DCF assumptions and sensitivity review.
- Peer comparison: ready for peer-relative review.
- Optional context: locked until trusted local earnings and analyst-estimate rows exist.
- Logic source: readiness gates, DCF boundaries, peer blockers, and report wording are repo-native under `src/`; standard libraries/adapters support data handling and UI, and external plugins are development aids, not runtime analysis engines.

## What This Stock Is
- Ticker: NVDA
- Asset type: company
- Current role: Momentum Leader. Judge the brief through trend, relative strength, extension risk, and setup quality; current state is Review Thesis.

## Decision
- Bucket: Research Now
- Subtype: Research Candidate - Core Data Ready
- Primary blocker: earnings
- Main reason: Core data is ready for a supported research pass.
- Next action: Optional context missing for NVDA; leave unavailable unless trusted local CSVs exist.

## Purpose Evaluation
Research-only purpose brief. It separates what local data supports from what remains locked or excluded.
- Thesis: Momentum Leader. Judge the brief through trend, relative strength, extension risk, and setup quality; current state is Review Thesis.
- Alignment: Purpose alignment needs review: Momentum Leader requires relative strength support, but current local outputs flag weak relative strength.
- Operator summary: Purpose alignment needs review: Momentum Leader requires relative strength support, but current local outputs flag weak relative strength; Research Candidate - Core Data Ready. Next blocker: earnings. Withheld: earnings timing or surprise context, analyst estimate trend context. Invalidation: Invalidate the momentum research setup if relative strength weakens, trend support fails, or extension risk dominates the setup.
- Setup: Momentum setup: Setup Forming; final state: Review Thesis. Check relative strength, trend, volume context, and extension risk before deeper research. Base score 45 from final state `Review Thesis`. Added 3 points because the ticker is already a holding. Adjusted +0 points for value category `Insufficient Data`.
- Valuation boundary: DCF inputs are ready, but valuation interpretation is constrained by Insufficient Data and peer status `Peer Data Unavailable`.

## Supported Analysis
- Supported analysis: price history, setup and momentum context, market/theme context, liquidity context, correlation/risk context, fundamental context, standalone DCF scenario analysis, peer-relative comparison. Purpose-specific support: momentum review can use trend, setup, and relative-strength context, while valuation remains secondary.

## Blocked Analysis
- Unsupported analysis: earnings timing or surprise context, analyst estimate trend context.

## Setup / Momentum
- Momentum setup: Setup Forming; final state: Review Thesis. Check relative strength, trend, volume context, and extension risk before deeper research. Base score 45 from final state `Review Thesis`. Added 3 points because the ticker is already a holding. Adjusted +0 points for value category `Insufficient Data`.
- 1M performance: 0.0785914771056635
- 3M performance: 0.1646384474113991
- 1Y performance: 0.5470220422023522

## Risk Notes
- Risk watchpoint: momentum purpose is sensitive to relative-strength deterioration, extension risk, and trend breaks.
- Invalidation condition: Invalidate the momentum research setup if relative strength weakens, trend support fails, or extension risk dominates the setup.

## Next Research Step
- Next research question: Does relative strength, trend quality, and extension risk still support the momentum purpose after reviewing the latest local price context?
- Review priority: High review priority: momentum purpose has enough core data for trend/relative-strength review, but confirm setup quality manually.
- Confidence explanation: Confidence is medium: core price, fundamentals, and DCF are ready; blockers still reduce breadth: earnings, analyst_estimates.

## Data Readiness
- Overall state: partial
- Price ready: True
- Momentum ready: True
- Liquidity ready: True
- Correlation ready: True
- Fundamentals ready: True
- DCF ready: True
- Peer ready: True
- Earnings ready: False
- Analyst estimates ready: False
- Blocked features: earnings, analyst_estimates
- Excluded features: Not available

## Price Coverage
- Price rows: 621
- First date: 2023-12-07
- Last date: 2026-05-22
- Missing price reason: Not available

## Valuation Readiness
- DCF status: calculated.
- DCF missing fields: Not available.
- Reason not ready: Not available.
- Base DCF fair value per share: $143.42.
- Base DCF assumptions: method=fcf_direct, revenue growth=40.0%, FCF margin=44.8%, WACC=9.0%, terminal growth=3.0%, forecast years=5.
- Scenario coverage: bear, base, bull.
- Sensitivity table: calculated; it tests fair value across WACC and terminal-growth assumptions when per-share DCF inputs are ready.
- Relative valuation: blocked until trusted peer mappings and peer valuation inputs are ready; current status=calculated; peer count=2.
- Valuation conclusion is shown only when trusted DCF and peer inputs support it; missing valuation inputs are not inferred.

## Peer Workflow
- Peer blocker type: Not available
- Mapping status: mapped
- Peer count: 2
- Trend comparison ready: True
- Valuation comparison ready: True
- DCF peer comparison ready: True
- Sample peers: AMD, AVGO
- Next peer action: Peer trend and valuation comparison are ready for NVDA.

## Missing Data
- No local analyst-estimate dataset is configured in the CSV-first pipeline.
- No local earnings dataset is configured in the CSV-first pipeline.
- Normalized growth target was reduced to keep it conservatively below WACC.
- Observed FCF margin 47.8% exceeded the conservative margin cap of 45.0% and was normalized before projection.
- Observed revenue growth 61.5% exceeded the conservative start-growth cap of 40.0% and was normalized before projection.
- Observed revenue growth 65.5% exceeded the conservative start-growth cap of 40.0% and was normalized before projection.
- Observed revenue growth 69.5% exceeded the conservative start-growth cap of 40.0% and was normalized before projection.
- Valuation missing field: ebitda
- analyst_estimates has no local row for this ticker.
- earnings has no local row for this ticker.

## Source / Freshness
- local:prices.csv: research-grade / local, retrieved 2026-06-03T18:35:06.424153090+00:00; Local CSV-backed research data.
- local:fundamentals.csv: research-grade / local, retrieved 2026-05-27T21:34:35.086026430+00:00; Local fundamentals data.; Dataset row source: sec_companyfacts
- local:earnings.csv: research-grade / local, retrieved 2026-06-04T04:21:20+00:00; Earnings fields are unavailable from the bundled local sample files.
- local:analyst_estimates.csv: research-grade / local, retrieved 2026-06-04T04:21:20+00:00; Analyst estimate fields are unavailable from the bundled local sample files.

## Source/Freshness Audit
- Prices: True; local source `data/prices.csv`; coverage 2023-12-07 to 2026-05-22; rows=621; staged path `data/staged/prices/` or `data/imports/prices.csv`; rejected rows `data/rejected/price_import_rejected.csv`.
- Fundamentals / DCF: ready; local source `data/fundamentals.csv`; reason Not available; SEC_USER_AGENT present; staged path `data/staged/fundamentals/` or `data/imports/fundamentals.csv`; rejected rows `data/rejected/fundamentals_import_rejected.csv`.
- Peers: ready; local source `data/peers.csv`; staged path `data/imports/peers.csv`; next peer action Peer trend and valuation comparison are ready for NVDA.
- Earnings: False; trusted local CSV only; staged path `data/staged/earnings/`; command `make import-earnings`; rejected rows `data/rejected/earnings_import_rejected.csv`.
- Analyst estimates: False; trusted local CSV only; staged path `data/staged/analyst_estimates/`; command `make import-analyst-estimates`; rejected rows `data/rejected/analyst_estimates_import_rejected.csv`.
- Credentials: SEC_USER_AGENT present; STOOQ_API_KEY missing; missing remote credentials should not break local CSV reports or staged import workflows.
- Report command: `make stock-report TICKER=NVDA`. Research-only output; copyable command only.
