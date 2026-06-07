# Product Spec

## Product Purpose

This project is a local, CSV-first stock research command center. It helps a user understand which tickers are available, which tickers are actively being researched, which analyses are trustworthy today, and what data should be imported next.

The product is not a trading bot. It does not place orders, connect to brokers, recommend options trades, or fabricate missing market, fundamentals, earnings, or analyst-estimate data.

## Target User

The target user is an individual investor or research reviewer who wants a deterministic local workflow for:

- maintaining a broad market universe;
- narrowing that universe into an active research list;
- reviewing portfolio holdings;
- tracking readiness by analysis feature;
- generating watchlists only when the needed data exists;
- seeing exact data blockers and next import actions.

## Non-Goals

- Broker integration.
- Auto-trading.
- Buy/sell/option-trade recommendations.
- Bloomberg-style full-provider coverage.
- Fabricated prices, fundamentals, earnings, analyst estimates, peers, or tickers.
- Hiding missing data behind unsupported rankings.
- Running expensive full-market analysis on every dashboard refresh.

## Core Product Principle

The product order is:

1. Data readiness first.
2. Analysis second.
3. Research decision last.

Operationally:

- No data, no conclusion.
- Insufficient data, show exactly what is missing.
- Sufficient data, run the relevant analysis.
- Completed analysis, generate research decisions.
- Blocked analysis must not be rendered as an unsupported recommendation.

## Market-Wide Expansion Goal

The product should grow from a small watchlist workflow into a market-wide research system. Market-wide support means the product can store and report on a large master universe, while scoped analysis remains efficient and explicit.

Large-universe rules:

- Do not require all master tickers to have data.
- Do not analyze all master tickers by default.
- Support active-universe, selected-sector, selected-ticker, missing-only, and ready-only scopes.
- Keep human-readable CSV outputs.
- Keep active-watchlist workflows fast even when the master universe is large.

## Universe Layers

`master market universe`

All known tickers the product can reference. It is broad metadata, not a promise of analysis coverage.

`active research universe`

The smaller set the user currently wants to research. This preserves compatibility with the old `data/universe.csv` workflow.

`portfolio universe`

Tickers currently present in `data/holdings.csv`.

`watchlist`

Ticker-level research outputs from analysis and decision layers.

`analysis-ready subset`

The per-feature subset of tickers with enough data for a specific module, such as momentum, DCF, liquidity, or earnings.

## Core User Decisions

- What should I research now?
- What should I monitor?
- What is blocked by missing data?
- What should I exclude because the analysis does not apply?
- What data should I import next?
- Which analyses are trustworthy today?

## Current Product Surfaces

The product is now organized around a few research-facing surfaces:

- `Home`: plain-language readiness cards and next-action cards first, with methodology ladder and example report comparisons in collapsed sections.
- `Single-Stock Report`: ticker-level At A Glance status, Best Review Path, methodology cue, analysis quality, valuation state, source readiness check, and copyable local unlock commands.
- `Data Health`: trusted local data paths, import validation, rejected-row reports, and unlock queues.
- `Value / Re-rating`: DCF-ready, peer-limited, blocked, and ETF/index/fund excluded valuation states.
- Markdown reports under `outputs/stock_reports/`: small visitor-readable examples of richer company, standalone DCF, price/setup gated, monitor-only, and blocked-data modes.

These surfaces must show supported, blocked, partial, and excluded states before showing detailed tables. Broad-universe tables should stay filtered and row-limited by default.

## MVP Definition

The MVP is successful when:

- the app can run locally from CSV files;
- master and active universe concepts exist;
- readiness is reported per ticker and per feature;
- blocked and excluded states are visible;
- final research decisions are readiness-aware;
- preview-first manual import files are available;
- invalid import rows are rejected into CSV files;
- dashboard smoke passes with missing credentials and empty import-draft folders.

## Public Share Definition

The public-facing project is shareable only when:

- the README has a short demo path and dashboard preview;
- sample reports show `At A Glance`, `Best Review Path`, methodology, evaluation function checks, source readiness, and copyable local unlock commands;
- public docs explain that project code provides readiness gates, DCF math, peer boundaries, and report wording;
- `make public-check` passes;
- generated CSV/JSON churn is reviewed before staging and is not committed by default;
- no public surface contains broker, order-routing, auto-trading, options recommendation, or direct buy/sell instruction language.

## Future Research Enhancements Not Implemented Yet

These items may fit the product if they preserve the readiness-first, research-only model:

- Paid or licensed data-provider integrations for trusted research inputs.
- Full SEC financial-statement modeling beyond preview-first fundamentals imports.
- Full market-scale background job scheduling for local refresh/import workflows.
- Parquet or SQLite caches for very large local datasets.
- Automated peer suggestions only when clearly labeled as fallback, not trusted manual peer data.

## Permanently Out Of Scope

These items do not fit the product purpose:

- Broker connections.
- Automated order routing.
- Auto-trading.
- Direct buy/sell/hold recommendations.
- Options trade recommendations.
- Fabricated prices, fundamentals, peers, earnings, analyst estimates, valuation inputs, or research conclusions.
