# Analysis Capability Audit

This project is a local research command center. It is strongest when the user has trusted local CSV data and weakest when a ticker is missing prices, fundamentals, peers, earnings, or analyst-estimate rows.

## What Is Strong Today

- **Readiness gating:** every ticker is checked before deeper analysis appears.
- **Price and momentum review:** moving averages, returns, relative strength, volume context, and volatility/ATR proxy are calculated from local price rows.
- **Fundamentals readiness:** company fundamentals are validated for the fields needed by DCF and quality checks.
- **DCF workflow:** DCF uses explicit assumptions, conservative caps, scenario outputs, and sensitivity tables when required inputs are available.
- **Peer workflow:** peer comparison is withheld until source-backed peer mappings and peer metrics exist.
- **ETF/index handling:** operating-company DCF is excluded for ETF/index/fund monitor context instead of being shown as failed.
- **Single-stock report:** one ticker can be reviewed with readiness, supported analysis, blocked analysis, valuation state, risk notes, next step, and source/freshness notes.

## What Is Intentionally Limited

- Broad-universe coverage depends on local data; many tickers may be blocked.
- Fundamentals and DCF coverage only improve when trusted SEC or manual rows are imported.
- Peer valuation stays unavailable until peer mappings and peer metrics are present.
- Earnings and analyst estimates stay unavailable until trusted local rows are imported.
- The app does not infer missing prices, fundamentals, peer relationships, estimates, or valuation inputs.

## Where The Logic Comes From

The analysis logic is implemented in this repository under `src/`:

- `src/indicators.py`: moving averages, returns, relative strength, ATR/volatility proxy.
- `src/momentum_engine.py`: rule-based setup classification.
- `src/value_engine.py`: fundamentals quality, valuation context, value-trap flags, and peer-relative context.
- `src/valuation.py`: DCF assumptions, scenarios, sensitivity, and relative-valuation calculations.
- `src/readiness_engine.py`: ticker/feature readiness gates and peer unlock worklists.
- `src/research_decisions.py`: readiness-aware research buckets, blockers, confidence, and next actions.
- `src/stock_report.py`: single-stock report assembly and Markdown output.

The project uses standard Python libraries such as `pandas`, `numpy`, `PyYAML`, and `streamlit` for data handling and UI. Optional `yfinance` support is an unofficial research-grade data adapter. These dependencies are not copied stock-analysis skills, ranking engines, or account-execution systems.

## Good-Enough Assessment

The current functions are good enough for a transparent local research prototype and single-stock review when trusted data exists. They are not yet a full-market data platform because fundamentals, peer data, earnings, and analyst estimates are intentionally sparse until the user imports trusted rows.

The next quality unlock is not more indicators. It is better data coverage, better source/freshness visibility, and more trusted fundamentals/peer rows.
