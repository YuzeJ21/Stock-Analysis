# Open-Source Product Map

This map reviews public research/dashboard projects as product inspiration only.
No large code blocks were copied into this repository.

## QuantGT Product Inspiration

Useful product ideas:

- monthly research-candidate cadence
- compact top-five candidate experience
- benchmark comparison panel
- track-record and archive sections
- plain-language methodology explanation

Adapted here:

- `src/monthly_picks.py` generates transparent local research candidates
- `src/track_record.py` calculates only when local price history supports it
- `src/dashboard.py` adds a Monthly Picks tab with source and missing-data context

Avoided:

- proprietary claims
- copied branding, copy, pricing, or visual design
- unverified performance claims
- trade instructions

## HQM Momentum Scanner

Repository: `luram94/momentum_trader`
License status: MIT.

Useful ideas:

- multi-timeframe momentum
- high-quality momentum scoring
- top-ranked candidate lists
- risk and volatility metrics

Safe features to adapt:

- transparent momentum quality components
- volume and volatility context
- watchlist-style candidate ranking

Features to avoid:

- portfolio execution language
- external data dependencies as mandatory inputs

Mapping into this repo:

- `src/monthly_picks.py` uses existing multi-timeframe returns, RS percentile, setup state, volume, and volatility context
- future work can expand `src/momentum_engine.py` with more explicit HQM-style component columns

## Powerfolio

Repository: `illyanyc/powerfolio`
License status: no license detected by GitHub API, so code reuse is not assumed.

Useful ideas:

- portfolio analytics
- efficient-frontier style visual thinking
- blend of fundamentals and technicals

Safe features to adapt:

- research-only risk overview panels
- explanatory portfolio analytics

Features to avoid:

- copying code without a clear license
- trading/backtest settings that imply execution

Mapping into this repo:

- portfolio risk concepts remain in `src/portfolio_review.py` and `src/risk.py`
- dashboard cards can borrow the general idea of clean portfolio analytics

## Daily US Stock Market Dashboard

Repository: `hieuimba/stock-mkt-dashboard`
License status: MIT.

Useful ideas:

- market overview
- sector heatmap
- correlation panel
- distribution charts

Safe features to adapt:

- Data Health and Market Direction panels
- future research-only sector distribution charts

Features to avoid:

- mandatory live data fetches
- unexplained market calls

Mapping into this repo:

- `src/market_direction.py` and the dashboard Market Direction tab are the natural homes

## OpenBB

Repository: `OpenBB-finance/OpenBB`
License status: AGPLv3 noted in the project README; GitHub API did not provide an SPDX id for the current default branch.

Useful ideas:

- provider architecture
- multi-surface research data access
- structured data objects before UI rendering

Safe features to adapt:

- optional provider adapters
- source/freshness metadata discipline

Features to avoid:

- making OpenBB mandatory
- adding broad provider dependency trees
- copying AGPL code into this repo

Mapping into this repo:

- provider boundaries already live under `src/providers/`

## Real-Time Stock Price Dashboard

Repository: `peterajhgraham/real-time-stock-dashboard`
License status: MIT.

Useful ideas:

- ticker detail charts
- technical indicator visuals
- Streamlit dashboard ergonomics

Safe features to adapt:

- chart layout ideas for Stock Report Beta and Monthly Picks
- local-only technical context display

Features to avoid:

- making yfinance mandatory
- real-time claims without a real-time data source

Mapping into this repo:

- `src/dashboard.py` can show local chart context from `data/prices.csv`

## Ghostfolio

Repository: `ghostfolio/ghostfolio`
License status: AGPL-3.0.

Useful ideas:

- polished portfolio UX
- responsive cards
- risk overview
- clean dark-mode inspiration

Safe features to adapt:

- high-contrast card layout ideas
- risk and data-health overview design patterns

Features to avoid:

- copying AGPL code
- importing portfolio/account-management assumptions that do not fit this research-only app

Mapping into this repo:

- dashboard card and overview polish only

## StockIQ

Repository: `Mamun/stockIQ`
License status: MIT.

Useful ideas:

- S&P 500 technical scanner UX
- moving-average stack context
- RSI and squeeze scanner ideas

Safe features to adapt:

- MA stack status
- RSI context
- transparent setup-quality labels

Features to avoid:

- AI forecast claims
- trade-signal language

Mapping into this repo:

- `src/monthly_picks.py` now includes MA stack and RSI context
- future work can expand `src/momentum_engine.py` with more columns

## TheAIQuant StockScreener Streamlit

Repository: `TheAIQuant/StockScreener_Streamlit`
License status: no license detected by GitHub API, so code reuse is not assumed.

Useful ideas:

- filtering UX
- NASDAQ screener layout
- sortable exploration tables

Safe features to adapt:

- filter ergonomics
- stock-detail drilldowns

Features to avoid:

- black-box predictions unless clearly labeled experimental
- copying unlicensed code

Mapping into this repo:

- dashboard filter/search patterns stay in `src/dashboard.py`

## Implementation Rules

- Keep all adapted ideas CSV-first and provider-bounded.
- Attribute material inspiration in docs.
- Do not add order execution, broker integration, or direct recommendation language.
- Do not fabricate track records or performance claims.
