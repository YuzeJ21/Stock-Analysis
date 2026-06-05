# APLD Single-Stock Research Report

Research-only local report. It summarizes readiness and does not provide allocation instructions.

## At A Glance
- Mode: `Data-unlock only`.
- Decision view: Blocked by Data - Missing Price.
- DCF: Blocked until trusted fundamentals and DCF inputs are ready.
- Peer context: Locked until source-backed peer inputs are ready.
- Optional context: Locked until trusted earnings and analyst-estimate rows exist.
- Method: project readiness gates decide what can appear; DCF uses local free-cash-flow inputs, discounted cash flows, discounted terminal value, cash/debt adjustment, and fair value per share when ready.
- Next local step: Add or refresh trusted local price history for APLD; run `make focus-price TICKER=APLD` before interpreting setup, fundamentals, DCF, or peer context.

## How To Read This Report
- Read top-down: readiness state first, supported analysis second, blocked or excluded analysis third.
- Current use: Data-unlock only until trusted price, fundamentals, DCF, and peer inputs are ready.
- Logic source: project code implements readiness gates and report wording; libraries and adapters support data handling/UI, but shipped analysis comes from project code and local data.
- Boundary: this is research context only. It does not provide allocation instructions, account actions, or direct recommendations.

This is a data-unlock report because local price history is not ready for price-backed analysis yet.
First blocker to resolve: No local price rows were found for APLD.

## Executive Summary
- Bottom line: APLD is in `Data-unlock only` mode. Start with verified local price history before relying on momentum, liquidity, valuation, or peer context.
- Use now: Use available price or setup context only. Company-level valuation stays blocked until trusted fundamentals, free cash flow or margin inputs, share count, and DCF fields are ready.
- Do not infer: Blocked features: price, momentum, market direction, liquidity, correlation, fundamentals, DCF, peer, earnings, analyst estimates. Excluded features: portfolio. Unavailable sections are intentionally locked; missing data is not inferred.
- Next step: Add or refresh trusted local price history for APLD; run `make focus-price TICKER=APLD` before interpreting setup, fundamentals, DCF, or peer context.

## Analysis Mode Guide
- `DCF-ready review` (other): Fullest company review: price, fundamentals, DCF, and source-backed peer context are ready.
- `Standalone DCF review` (other): Company DCF can be reviewed, but peer-relative valuation remains blocked.
- `Price/setup review only` (other): Use trend/setup context only; company valuation waits for trusted fundamentals and DCF inputs.
- `Monitor-only context` (other): Use ETF/index/fund market or risk context; operating-company DCF is excluded, not failed.
- `Data-unlock only` (current): Pause analysis for this ticker until the first trusted local input is available.

## One-Minute Status
APLD state: blocked. Decision: Blocked by Data - Missing Price. Primary blocker: price. DCF: blocked. Peer workflow: waits for trusted price, fundamentals, and DCF inputs first. Optional earnings or analyst-estimate context is unavailable until trusted local CSV rows exist. Next: Add or refresh trusted local price history for APLD; run `make focus-price TICKER=APLD` before interpreting setup, fundamentals, DCF, or peer context.

## What We Can Analyze Now
- Ready inputs: none yet.
- Supported now: Use available price or setup context only. Company-level valuation stays blocked until trusted fundamentals, free cash flow or margin inputs, share count, and DCF fields are ready.
- Still locked or excluded: Blocked features: price, momentum, market direction, liquidity, correlation, fundamentals, DCF, peer, earnings, analyst estimates. Excluded features: portfolio. Unavailable sections are intentionally locked; missing data is not inferred.

## Analysis Quality
- Analysis mode: Data-unlock only.
- Why: Start with verified local price history before relying on momentum, liquidity, valuation, or peer context.
- Optional context: Earnings and analyst estimates stay locked until trusted local rows exist.

## Methodology
- Method order: readiness gate first, supported analysis second, valuation math third, explanation last.
- Input boundary: local or provider-assisted rows supply data; project rules decide readiness, calculations, blockers, and report wording.
- Fundamental analysis: local revenue, cash-flow, margin, share-count, cash/debt, and source fields are reviewed only when present; missing fields are not inferred.
- DCF formula path: base FCF -> projected FCF -> discounted FCF plus discounted terminal value -> enterprise value -> equity value -> fair value per share.
- DCF method: standalone DCF stays blocked until trusted local price, revenue, free cash flow or FCF margin, shares outstanding, and DCF fields pass readiness checks.
- Peer method: peer-relative valuation stays withheld until source-backed peer mappings and peer valuation inputs are ready.
- Score boundary: setup, watchlist, confidence, and monthly scores are triage aids for review order only; they are not price targets, expected returns, or allocation instructions.
- Report method: text is generated from local readiness, DCF, peer, decision, and source/freshness outputs; blocked or excluded sections are explained instead of filled.

## Evaluation Function Check
- Readiness gate: strongest function; it decides ready, blocked, or excluded before any conclusion is shown.
- Price and setup: locked until enough trusted price history is available.
- Risk context: partial until liquidity and correlation inputs pass readiness checks.
- Fundamentals / DCF: blocked until trusted fundamentals, cash-flow or margin, share-count, and DCF inputs are ready.
- Peer comparison: blocked until source-backed peer mappings and peer valuation inputs are ready.
- Optional context: locked until trusted local earnings and analyst-estimate rows exist.
- Logic source: readiness gates, DCF boundaries, peer blockers, and report wording are implemented in project code; standard libraries/adapters support data handling and UI, but shipped analysis comes from project code and local data.

## What This Stock Is
- Ticker: APLD
- Asset type: company
- Current role: Core Compounder. Test whether trend, fundamentals, and DCF support the long-duration thesis; current state is not prioritized.

## Decision
- Bucket: Blocked by Data
- Subtype: Blocked by Data - Missing Price
- Primary blocker: price
- Main reason: Missing usable price data.
- Next action: Add or refresh trusted local price history for APLD; run `make focus-price TICKER=APLD` before interpreting setup, fundamentals, DCF, or peer context.

## Purpose Evaluation
Research-only purpose brief. It separates what local data supports from what remains locked or excluded.
- Thesis: Core Compounder. Test whether trend, fundamentals, and DCF support the long-duration thesis; current state is not prioritized.
- Alignment: Purpose alignment for Core Compounder cannot be checked until usable price history exists.
- Operator summary: Purpose alignment for Core Compounder cannot be checked until usable price history exists; Blocked by Data - Missing Price. Next blocker: price. Withheld: trend, setup, liquidity, volatility, and relative strength, fundamental quality and operating-company valuation, DCF interpretation, peer-relative valuation or opportunity-cost comparison, earnings timing or surprise context, analyst estimate trend context, compounder thesis confirmation. Invalidation: Invalidation cannot be defined from local price data until price history is available.
- Setup: Setup cannot be evaluated because usable price history is missing.
- Valuation boundary: Valuation conclusion is blocked until trusted DCF/fundamental inputs are complete.

## Supported Analysis
- Supported analysis: none yet; this row is an unlock checklist until core inputs are available.

## Blocked Analysis
- Unsupported analysis: trend, setup, liquidity, volatility, and relative strength, fundamental quality and operating-company valuation, DCF interpretation, peer-relative valuation or opportunity-cost comparison, earnings timing or surprise context, analyst estimate trend context, compounder thesis confirmation.

## Setup / Momentum
- Setup cannot be evaluated because usable price history is missing.

## Risk Notes
- Risk watchpoint: Primary risk is analytical blindness from missing price history; do not interpret trend or volatility yet.
- Invalidation condition: Invalidation cannot be defined from local price data until price history is available.

## Next Research Step
- Next research question: Can trusted local price rows be added before interpreting setup, risk, or relative strength?
- Review priority: Unlock priority: price is the first blocker before setup, valuation, or risk interpretation should be trusted.
- Confidence explanation: Confidence is blocked: primary blocker is price; blocked features are price, momentum, market direction, liquidity, correlation, fundamentals, DCF, peer, earnings, analyst estimates.

## Data Readiness
- Overall state: blocked
- Asset type: company
- Price ready: not ready
- Momentum ready: not ready
- Fundamentals ready: not ready
- DCF ready: not ready
- Peer ready: not ready
- Earnings ready: not ready
- Analyst estimates ready: not ready
- Blocked features: price, momentum, market direction, liquidity, correlation, fundamentals, DCF, peer, earnings, analyst estimates
- Excluded features: portfolio

## Price Coverage
- Price rows: 0
- Missing price reason: needs at least 5 valid price rows with positive close

## Valuation Readiness
- DCF status: insufficient data.
- DCF missing inputs: free cash flow, shares outstanding, revenue, FCF margin, price.
- Why DCF is blocked: missing free cash flow, shares outstanding, revenue, FCF margin, price.
- DCF assumptions: withheld until price, fundamentals, free cash flow or FCF margin, and share-count inputs are ready.
- Sensitivity table: unavailable until the base DCF can be calculated.
- Relative valuation: withheld until trusted fundamentals and DCF readiness pass; background relative-multiple status=insufficient data; peer count=0.
- Valuation conclusion is shown only when trusted DCF and peer inputs support it; missing valuation inputs are not inferred.

## Peer Workflow
- Peer blocker type: blocked until fundamentals / DCF
- Mapping status: waiting for price, fundamentals, and DCF
- Peer count: 0
- Trend comparison ready: not ready
- Valuation comparison ready: not ready
- Next peer action: Peer-relative valuation should wait until trusted price, fundamentals, and DCF inputs are ready.

## Missing Data
- needs at least 5 valid price rows with positive close; DCF: free cash flow, shares outstanding, revenue, FCF margin, price; peers: needs at least 2 source-backed peer mappings; earnings: trusted local CSV input; analyst estimates: trusted local CSV input

## Data Unlock Summary
- Price unlock: Price history is the first unlock. Run `make focus-price TICKER=APLD` or use the price import flow before interpreting setup.
- Fundamentals / DCF unlock: Wait on fundamentals / DCF interpretation until price coverage starts. After `make focus-price TICKER=APLD` is resolved, run `make focus-fundamentals TICKER=APLD` for the next DCF fields.
- Peer unlock: Peer valuation should wait until trusted price, fundamentals, and DCF inputs are ready.
- Optional context unlock: Earnings and analyst estimates remain optional and locked until trusted local rows are imported with `make templates`, `make imports-validate`, `make imports-preview`, and `make imports-apply`.
- Import paths, rejected-row files, and credential state are listed in the Source/Freshness Audit below.

## Copyable Unlock Commands
- Copy-only: these are local research commands to copy when you choose; the report does not execute imports, refreshes, broker actions, or trades.
- Inspect this ticker: `make stock-report-md TICKER=APLD`.
- Price first: `make focus-price TICKER=APLD`.
- Price queue: `make price-worklist TICKERS=APLD TOP_N=10`.
- Price import safety: `make price-validate && make price-preview && make price-apply`.
- Fundamentals / DCF: `make focus-fundamentals TICKER=APLD`.
- SEC/manual import review: `make sec-stage-queue TICKERS=APLD TOP_N=10`.
- Fundamentals import safety: `make imports-validate && make imports-preview && make imports-apply`.
- Peer mapping: `make focus-peers TICKER=APLD`.
- Peer queue: `make peer-mapping-queue TICKERS=APLD TOP_N=10`.
- Peer import safety: `make templates && make imports-validate && make imports-preview && make imports-apply`.
- Optional context queue: `make optional-context-worklist TICKERS=APLD TOP_N=10`.
- Optional templates: `make templates`.
- Earnings import: `make import-earnings`.
- Analyst-estimates import: `make import-analyst-estimates`.
- Optional import safety: `make imports-validate && make imports-preview && make imports-apply`.

## Source/Freshness Audit
- Prices: not ready; local source `data/prices.csv`; coverage unknown to unknown; rows=0; import draft path `data/staged/prices/` or `data/imports/prices.csv`; rejected rows `data/rejected/price_import_rejected.csv`.
- Fundamentals / DCF: blocked; local source `data/fundamentals.csv`; reason missing free cash flow, shares outstanding, revenue, FCF margin, price; SEC_USER_AGENT present; import draft path `data/staged/fundamentals/` or `data/imports/fundamentals.csv`; rejected rows `data/rejected/fundamentals_import_rejected.csv`.
- Peers: blocked until fundamentals / DCF; local source `data/peers.csv`; import draft path `data/imports/peers.csv`; next peer action Peer-relative valuation should wait until trusted price, fundamentals, and DCF inputs are ready.
- Earnings: not ready; trusted local CSV only; import draft path `data/staged/earnings/`; command `make import-earnings`; rejected rows `data/rejected/earnings_import_rejected.csv`.
- Analyst estimates: not ready; trusted local CSV only; import draft path `data/staged/analyst_estimates/`; command `make import-analyst-estimates`; rejected rows `data/rejected/analyst_estimates_import_rejected.csv`.
- Credentials: SEC_USER_AGENT present; STOOQ_API_KEY missing; missing remote credentials should not break local CSV reports or preview-first local import workflows.
- Report command: `make stock-report-md TICKER=APLD`. Research-only Markdown output; copyable command only.
