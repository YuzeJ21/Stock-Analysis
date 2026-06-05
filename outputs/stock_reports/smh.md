# SMH Single-Stock Research Report

Research-only local report. It summarizes readiness and does not provide allocation instructions.

## At A Glance
- Mode: `Monitor-only context`.
- Decision view: Monitor - ETF Market Proxy.
- DCF: Excluded for ETF/index/fund monitor context.
- Peer context: Excluded for monitor context.
- Optional context: Locked until trusted earnings and analyst-estimate rows exist.
- Method: project readiness gates decide what can appear; DCF uses local free-cash-flow inputs, discounted cash flows, discounted terminal value, cash/debt adjustment, and fair value per share when ready.
- Next local step: Review SMH as ETF/index/fund monitor context; operating-company DCF and peer valuation stay excluded.

## How To Read This Report
- Read top-down: readiness state first, supported analysis second, blocked or excluded analysis third.
- Current use: Monitor-only context when local price, liquidity, correlation, or theme inputs are ready.
- Logic source: project code implements readiness gates and report wording; libraries and adapters support data handling/UI, but shipped analysis comes from project code and local data.
- Boundary: this is research context only. It does not provide allocation instructions, account actions, or direct recommendations.

## Executive Summary
- Bottom line: SMH is in `Monitor-only context` mode. Use market, theme, liquidity, or risk context. Operating-company DCF and peer valuation are excluded, not failed.
- Use now: Monitor context is supported where local price, liquidity, correlation, and theme data are available. Operating-company DCF and peer valuation are excluded rather than treated as failed inputs.
- Do not infer: Blocked features: fundamentals, peer, earnings, analyst estimates. Excluded features: DCF, portfolio. Unavailable sections are intentionally locked; missing data is not inferred.
- Next step: Review SMH as ETF/index/fund monitor context; operating-company DCF and peer valuation stay excluded.

## Analysis Mode Guide
- `DCF-ready review` (other): Fullest company review: price, fundamentals, DCF, and source-backed peer context are ready.
- `Standalone DCF review` (other): Company DCF can be reviewed, but peer-relative valuation remains blocked.
- `Price/setup review only` (other): Use trend/setup context only; company valuation waits for trusted fundamentals and DCF inputs.
- `Monitor-only context` (current): Use ETF/index/fund market or risk context; operating-company DCF is excluded, not failed.
- `Data-unlock only` (other): Reference state for tickers with no trusted local inputs yet; add the first missing input before drawing conclusions.

## One-Minute Status
SMH state: partial. Decision: Monitor - ETF Market Proxy. DCF: excluded. Monitor context: operating-company DCF and peer valuation are excluded. Optional earnings or analyst-estimate context is unavailable until trusted local CSV rows exist. Next: Review SMH as ETF/index/fund monitor context; operating-company DCF and peer valuation stay excluded.

## What We Can Analyze Now
- Ready inputs: price, momentum, market direction, liquidity, correlation.
- Supported now: Monitor context is supported where local price, liquidity, correlation, and theme data are available. Operating-company DCF and peer valuation are excluded rather than treated as failed inputs.
- Still locked or excluded: Blocked features: fundamentals, peer, earnings, analyst estimates. Excluded features: DCF, portfolio. Unavailable sections are intentionally locked; missing data is not inferred.

## Data Vs Product Logic
- Source inputs: local CSV rows or labeled provider-assisted rows supply prices, fundamentals, peers, earnings, and estimates.
- Product checks: project readiness gates decide whether each input is usable before report sections appear.
- Product DCF logic: excluded by asset-type gate; the report does not ask a third party or model to create a valuation opinion.
- Product peer logic: excluded for monitor context; sector or industry fallback is not treated as trusted peer valuation.
- Optional context logic: locked locally until trusted earnings and analyst-estimate rows pass import validation; empty optional files are an intentional locked state, not hidden analysis.
- Output wording: supported, blocked, partial, and excluded sections are written from project code so missing data cannot become a weak conclusion.

## Analysis Quality
- Analysis mode: Monitor-only context.
- Why: Use market, theme, liquidity, or risk context. Operating-company DCF and peer valuation are excluded, not failed.
- Optional context: Earnings and analyst estimates stay locked until trusted local rows exist.

## Methodology
- Method order: readiness gate first, supported analysis second, valuation math third, explanation last.
- Input boundary: local or provider-assisted rows supply data; project rules decide readiness, calculations, blockers, and report wording.
- Fundamental analysis: local revenue, cash-flow, margin, share-count, cash/debt, and source fields are reviewed only when present; missing fields are not inferred.
- DCF formula path: base FCF -> projected FCF -> discounted FCF plus discounted terminal value -> enterprise value -> equity value -> fair value per share.
- DCF status boundary: ready means assumptions can be reviewed, blocked means required company inputs are missing, and excluded means the method does not fit ETF/index/fund monitor context.
- DCF method: operating-company DCF is excluded because this ticker is treated as ETF/index/fund monitor context; use ready price, liquidity, correlation, theme, or risk context instead.
- Peer method: peer-relative company valuation is excluded for monitor context.
- Score boundary: setup, watchlist, confidence, and monthly scores are triage aids for review order only; they are not price targets, expected returns, or allocation instructions.
- Report method: text is generated from local readiness, DCF, peer, decision, and source/freshness outputs; blocked or excluded sections are explained instead of filled.

## Evaluation Function Check
- Readiness gate: strongest function; it decides ready, blocked, or excluded before any conclusion is shown.
- Price and setup: ready for local trend/setup review.
- Risk context: ready for local liquidity/correlation context.
- Fundamentals / DCF: excluded for ETF/index/fund monitor context, not failed.
- Peer comparison: excluded for monitor context.
- Optional context: locked until trusted local earnings and analyst-estimate rows exist.
- Logic source: readiness gates, DCF boundaries, peer blockers, and report wording are implemented in project code; standard libraries/adapters support data handling and UI, but shipped analysis comes from project code and local data.

## What This Stock Is
- Ticker: SMH
- Asset type: etf
- Current role: ETF / Defensive / Hedge. Evaluate as market, theme, liquidity, or risk context; operating-company valuation remains excluded.

## Decision
- Bucket: Monitor
- Subtype: Monitor - ETF Market Proxy
- Primary blocker: monitor context
- Main reason: etf is usable for market/risk monitoring and excluded from company DCF.
- Next action: Review SMH as ETF/index/fund monitor context; operating-company DCF and peer valuation stay excluded.

## Purpose Evaluation
Research-only purpose brief. It separates what local data supports from what remains locked or excluded.
- Thesis: ETF / Defensive / Hedge. Evaluate as market, theme, liquidity, or risk context; operating-company valuation remains excluded.
- Alignment: ETF / Defensive / Hedge is evaluated as market/risk context when price, liquidity, and correlation data are ready; operating-company valuation is not applicable.
- Operator summary: Monitor context; Monitor - ETF Market Proxy. Monitor role: market, theme, liquidity, or risk proxy. Withheld: operating-company DCF and peer valuation are excluded. Invalidation: proxy usefulness weakens if liquidity, correlation, or theme trend no longer supports monitoring.
- Setup: Setup Forming; final state: Setup Forming. Base score 68 from final state `Setup Forming`. Adjusted +0 points for value category `Insufficient Data`. Capped score at 50 because valuation readiness is not ready; treat as data-limited review until missing data is resolved.
- Valuation boundary: Operating-company DCF is excluded for this asset type; use market/risk context instead of valuation conclusions.

## Supported Analysis
- Supported analysis: price history, setup and momentum context, market/theme context, liquidity context, correlation/risk context, ETF/index monitoring, not operating-company valuation. Purpose-specific support: ETF/hedge review can use market, theme, liquidity, and correlation context; company valuation is excluded.

## Blocked Analysis
- Unsupported analysis: fundamental quality and operating-company valuation, peer-relative valuation or opportunity-cost comparison, earnings timing or surprise context, analyst estimate trend context, operating-company DCF conclusions.

## Setup / Momentum
- Setup Forming; final state: Setup Forming. Base score 68 from final state `Setup Forming`. Adjusted +0 points for value category `Insufficient Data`. Capped score at 50 because valuation readiness is not ready; treat as data-limited review until missing data is resolved.
- 1M performance: 19.6%
- 3M performance: 39.6%
- 1Y performance: 138.7%
- ATR / volatility: Not available; missing values stay visible instead of guessed.

## Risk Notes
- Risk watchpoint: monitor liquidity, correlation, and theme exposure; company-specific DCF does not apply.
- Invalidation condition: Invalidate market-proxy usefulness if liquidity, correlation, or theme trend no longer supports the intended monitoring role.

## Next Research Step
- Next research question: Which source-backed peer mappings or peer metrics would make the market-proxy comparison more trustworthy?
- Review priority: Monitor priority: use this proxy for market, theme, liquidity, or risk context; do not treat it as operating-company valuation.
- Confidence explanation: Confidence is low: monitoring is supported by price, momentum, market direction, liquidity, correlation, while fundamentals, peer, earnings, analyst estimates remains unavailable.

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
- Blocked features: fundamentals, peer, earnings, analyst estimates
- Excluded features: DCF, portfolio

## Price Coverage
- Price rows: 616
- First date: 2023-12-07
- Last date: 2026-05-22
- Missing price reason: none

## Valuation Readiness
- DCF applicability: excluded for ETF/index/fund monitor context; this is not a failed valuation input.
- Valuation conclusion: not shown because operating-company DCF and peer valuation do not apply to this monitor role.

## Peer Workflow
- Peer blocker type: monitor context
- Mapping status: monitor context
- Peer count: 0
- Trend comparison ready: not ready
- Valuation comparison ready: not ready
- DCF peer comparison ready: not ready
- Sample peers: none configured
- Next peer action: No peer import is required; operating-company peer valuation is excluded for ETF/index/fund monitor context.

## Missing Data
- Operating-company DCF and peer valuation are excluded for this monitor context, so company valuation fields are not treated as repair items.
- No local analyst-estimate dataset is configured in the CSV-first pipeline.
- No local earnings dataset is configured in the CSV-first pipeline.
- Normalized growth target was reduced to keep it conservatively below WACC.
- analyst estimates has no local row for this ticker.
- earnings has no local row for this ticker.

## Source / Freshness
- local:prices.csv: research-grade / local; freshness: daily CSV through 2026-05-22; Saved local research data.
- local:fundamentals.csv: research-grade / local; freshness: not available in local CSVs; No local fundamentals row was found for this ticker.
- local:earnings.csv: research-grade / local; freshness: not available in local CSVs; Earnings fields are unavailable from the bundled local sample files.
- local:analyst_estimates.csv: research-grade / local; freshness: not available in local CSVs; Analyst estimate fields are unavailable from the bundled local sample files.

## Data Unlock Summary
- Price unlock: Price history is usable now (616 local row(s)); keep it fresh before relying on setup or risk context.
- Fundamentals / DCF unlock: Operating-company DCF is excluded for this ETF/index/fund monitor context; no fundamentals import is required for company valuation.
- Peer unlock: Peer valuation is excluded for monitor context; peer rows are optional context, not a required unlock.
- Optional context unlock: Earnings and analyst estimates remain optional and locked until trusted local rows are imported with `make templates`, `make imports-validate`, `make imports-preview`, and `make imports-apply`.
- Import paths, rejected-row files, and credential state are listed in the Source/Freshness Audit below.

## Copyable Unlock Commands
- Copy-only: these are local research commands to copy when you choose; the report does not execute imports, refreshes, broker actions, or trades.
- Inspect this ticker: `make stock-report-md TICKER=SMH`.
- Price freshness: `make focus-price TICKER=SMH`.
- Fundamentals / DCF: no operating-company DCF command is required for ETF/index/fund monitor context.
- Peers: no peer-valuation command is required for ETF/index/fund monitor context.
- Optional context queue: `make optional-context-worklist TICKERS=SMH TOP_N=10`.
- Optional templates: `make templates`.
- Earnings import: `make import-earnings`.
- Analyst-estimates import: `make import-analyst-estimates`.
- Optional import safety: `make imports-validate && make imports-preview && make imports-apply`.

## Source/Freshness Audit
- Prices: ready; local source `data/prices.csv`; coverage 2023-12-07 to 2026-05-22; rows=616; import draft path `data/staged/prices/` or `data/imports/prices.csv`; rejected rows `data/rejected/price_import_rejected.csv`.
- Fundamentals / DCF: excluded; local source `data/fundamentals.csv`; reason dcf excluded for etf, use etf/rotation analysis instead of operating-company dcf; SEC_USER_AGENT present; import draft path `data/staged/fundamentals/` or `data/imports/fundamentals.csv`; rejected rows `data/rejected/fundamentals_import_rejected.csv`.
- Peers: monitor context; local source `data/peers.csv`; import draft path `data/imports/peers.csv`; next peer action No peer import is required; operating-company peer valuation is excluded for ETF/index/fund monitor context.
- Earnings: not ready; trusted local CSV only; import draft path `data/staged/earnings/`; command `make import-earnings`; rejected rows `data/rejected/earnings_import_rejected.csv`.
- Analyst estimates: not ready; trusted local CSV only; import draft path `data/staged/analyst_estimates/`; command `make import-analyst-estimates`; rejected rows `data/rejected/analyst_estimates_import_rejected.csv`.
- Credentials: SEC_USER_AGENT present; STOOQ_API_KEY missing; missing remote credentials should not break local CSV reports or preview-first local import workflows.
- Report command: `make stock-report-md TICKER=SMH`. Research-only Markdown output; copyable command only.
