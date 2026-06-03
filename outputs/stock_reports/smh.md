# SMH Single-Stock Research Report

Research-only local report. It summarizes readiness and does not provide allocation instructions.

## Executive Summary
SMH state: partial. Decision: Monitor - ETF Market Proxy. DCF: excluded. Monitor context: operating-company DCF and peer valuation are excluded. Optional earnings or analyst-estimate context is unavailable until trusted local CSV rows exist. Next: Review SMH as ETF/index/fund monitor context; operating-company DCF and peer valuation stay excluded.

## One-Minute Status
SMH state: partial. Decision: Monitor - ETF Market Proxy. DCF: excluded. Monitor context: operating-company DCF and peer valuation are excluded. Optional earnings or analyst-estimate context is unavailable until trusted local CSV rows exist. Next: Review SMH as ETF/index/fund monitor context; operating-company DCF and peer valuation stay excluded.

## What This Stock Is
- Ticker: SMH
- Asset type: etf
- Current role: ETF / Defensive / Hedge. Evaluate as market, theme, liquidity, or risk context; operating-company valuation remains excluded.

## Decision
- Bucket: Monitor
- Subtype: Monitor - ETF Market Proxy
- Primary blocker: monitor_context
- Main reason: etf is usable for market/risk monitoring and excluded from company DCF.
- Next action: Review SMH as ETF/index/fund monitor context; operating-company DCF and peer valuation stay excluded.

## Purpose Evaluation
Research-only purpose brief. It separates what local data supports from what remains locked or excluded.
- Thesis: ETF / Defensive / Hedge. Evaluate as market, theme, liquidity, or risk context; operating-company valuation remains excluded.
- Alignment: ETF / Defensive / Hedge is evaluated as market/risk context when price, liquidity, and correlation data are ready; operating-company valuation is not applicable.
- Operator summary: Monitor context; Monitor - ETF Market Proxy. Monitor role: market, theme, liquidity, or risk proxy. Withheld: operating-company DCF and peer valuation are excluded. Invalidation: proxy usefulness weakens if liquidity, correlation, or theme trend no longer supports monitoring.
- Setup: Setup Forming; final state: Setup Forming. Base score 68 from final state `Setup Forming`. Adjusted +0 points for value category `Insufficient Data`. Capped score at 50 because valuation readiness is `not_ready`; treat as monitor-only until missing data is resolved.
- Valuation boundary: Operating-company DCF is excluded for this asset type; use market/risk context instead of valuation conclusions.

## Supported Analysis
- Supported analysis: price history, setup and momentum context, market/theme context, liquidity context, correlation/risk context, ETF/index monitoring, not operating-company valuation. Purpose-specific support: ETF/hedge review can use market, theme, liquidity, and correlation context; company valuation is excluded.

## Blocked Analysis
- Unsupported analysis: fundamental quality and operating-company valuation, peer-relative valuation or opportunity-cost comparison, earnings timing or surprise context, analyst estimate trend context, operating-company DCF conclusions.

## Setup / Momentum
- Setup Forming; final state: Setup Forming. Base score 68 from final state `Setup Forming`. Adjusted +0 points for value category `Insufficient Data`. Capped score at 50 because valuation readiness is `not_ready`; treat as monitor-only until missing data is resolved.
- 1M performance: 0.19605686421929436
- 3M performance: 0.39585351799197777
- 1Y performance: 1.3867147240267887

## Risk Notes
- Risk watchpoint: monitor liquidity, correlation, and theme exposure; company-specific DCF does not apply.
- Invalidation condition: Invalidate market-proxy usefulness if liquidity, correlation, or theme trend no longer supports the intended monitoring role.

## Next Research Step
- Next research question: Which source-backed peer mappings or peer metrics would make the market-proxy comparison more trustworthy?
- Review priority: Monitor priority: use this proxy for market, theme, liquidity, or risk context; do not treat it as operating-company valuation.
- Confidence explanation: Confidence is low: monitoring is supported by price, momentum, market_direction, liquidity, correlation, while fundamentals, peer, earnings, analyst_estimates remains unavailable.

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
- Blocked features: fundamentals, peer, earnings, analyst_estimates
- Excluded features: dcf, portfolio

## Price Coverage
- Price rows: 616
- First date: 2023-12-07
- Last date: 2026-05-22
- Missing price reason: Not available

## Valuation Readiness
- DCF applicability: excluded for ETF/index/fund monitor context; this is not a failed valuation input.
- Valuation conclusion: not shown because operating-company DCF and peer valuation do not apply to this monitor role.

## Peer Workflow
- Peer blocker type: monitor_context
- Mapping status: monitor_context
- Peer count: 0
- Trend comparison ready: False
- Valuation comparison ready: False
- DCF peer comparison ready: False
- Sample peers: Not available
- Next peer action: No peer import is required; operating-company peer valuation is excluded for ETF/index/fund monitor context.

## Missing Data
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
- local:fundamentals.csv: research-grade / local, retrieved 2026-06-03T19:02:40+00:00; No local fundamentals row was found for this ticker.
- local:earnings.csv: research-grade / local, retrieved 2026-06-03T19:02:40+00:00; Earnings fields are unavailable from the bundled local sample files.
- local:analyst_estimates.csv: research-grade / local, retrieved 2026-06-03T19:02:40+00:00; Analyst estimate fields are unavailable from the bundled local sample files.

## Source/Freshness Audit
- Prices: True; local source `data/prices.csv`; coverage 2023-12-07 to 2026-05-22; rows=616; staged path `data/staged/prices/` or `data/imports/prices.csv`; rejected rows `data/rejected/price_import_rejected.csv`.
- Fundamentals / DCF: excluded; local source `data/fundamentals.csv`; reason DCF excluded for etf; use ETF/rotation analysis instead of operating-company DCF.; SEC_USER_AGENT present; staged path `data/staged/fundamentals/` or `data/imports/fundamentals.csv`; rejected rows `data/rejected/fundamentals_import_rejected.csv`.
- Peers: monitor context; local source `data/peers.csv`; staged path `data/imports/peers.csv`; next peer action No peer import is required; operating-company peer valuation is excluded for ETF/index/fund monitor context.
- Earnings: False; trusted local CSV only; staged path `data/staged/earnings/`; command `make import-earnings`; rejected rows `data/rejected/earnings_import_rejected.csv`.
- Analyst estimates: False; trusted local CSV only; staged path `data/staged/analyst_estimates/`; command `make import-analyst-estimates`; rejected rows `data/rejected/analyst_estimates_import_rejected.csv`.
- Credentials: SEC_USER_AGENT present; STOOQ_API_KEY missing; missing remote credentials should not break local CSV reports or staged import workflows.
- Report command: `make stock-report TICKER=SMH`. Research-only output; copyable command only.
