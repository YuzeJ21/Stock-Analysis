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

## Function Quality Matrix

| Function area | Supported today | Needs trusted data | What it refuses to do | Main implementation |
| --- | --- | --- | --- | --- |
| Readiness gates | Yes. This is the strongest layer because every deeper output depends on it. | Local ticker, price, fundamentals, peer, earnings, and estimate readiness rows. | It does not turn missing data into a weak conclusion. | `src/readiness_engine.py` |
| Price and momentum | Yes when local price history is present. | Daily OHLCV rows with enough history for returns, averages, liquidity, and volatility context. | It does not invent missing price history or fill broad-universe gaps silently. | `src/indicators.py`, `src/momentum_engine.py` |
| Fundamentals and DCF | Useful for DCF-ready companies only. | Trusted fundamentals with revenue, free cash flow or FCF margin, shares outstanding, price, cash, and debt where available. | It does not label not-ready companies undervalued or overvalued. | `src/value_engine.py`, `src/valuation.py` |
| Peer comparison | Workflow-ready, but coverage-limited until peers are imported. | Source-backed peer mappings plus peer price/fundamentals rows. | It does not treat sector or industry fallback as trusted peer valuation. | `src/readiness_engine.py`, `src/valuation.py` |
| ETF/index monitor context | Supports market, theme, liquidity, and risk monitoring. | Price, liquidity, correlation, and theme context. | It does not run operating-company DCF for ETFs, index proxies, or funds. | `src/research_decisions.py`, `src/stock_report.py` |
| Single-stock report | Explains one ticker's supported and blocked analysis in plain language. | Current local readiness, price, decision, DCF, peer, and optional-context outputs. | It does not provide allocation instructions or unsupported recommendations. | `src/stock_report.py`, `src/dashboard.py` |

## What Is Intentionally Limited

- Broad-universe coverage depends on local data; many tickers may be blocked.
- Fundamentals and DCF coverage only improve when trusted SEC or manual rows are imported.
- Peer valuation stays unavailable until peer mappings and peer metrics are present.
- Earnings and analyst estimates stay unavailable until trusted local rows are imported.
- The app does not infer missing prices, fundamentals, peer relationships, estimates, or valuation inputs.

## Analysis Modes

The product now uses the same plain modes across the dashboard and single-stock workflow:

| Mode | Supported today | Not supported yet |
| --- | --- | --- |
| `DCF-ready review` | Company DCF assumptions, scenarios, and sensitivity when trusted inputs exist. | Unsupported recommendations or allocation instructions. |
| `Standalone DCF review` | Reviewing company DCF assumptions before peer context is ready. | Peer-relative valuation until source-backed peer inputs exist. |
| `Price/setup review only` | Local price, setup, and missing-data diagnosis. | Company valuation or quality conclusions. |
| `Monitor-only context` | ETF/index/fund market, theme, liquidity, and risk monitoring. | Operating-company DCF, which is excluded rather than failed. |
| `Data-unlock only` | Identifying the next trusted local input to add. | Any analytical conclusion beyond the visible blocker. |

## Where The Logic Comes From

The analysis logic is implemented in this repository under `src/`. The shipped product is not a wrapper around external investing services, ranking services, account-execution tools, or broker workflows:

- `src/indicators.py`: moving averages, returns, relative strength, ATR/volatility proxy.
- `src/momentum_engine.py`: rule-based setup classification.
- `src/value_engine.py`: fundamentals quality, valuation context, value-trap flags, and peer-relative context.
- `src/valuation.py`: DCF assumptions, scenarios, sensitivity, and relative-valuation calculations.
- `src/readiness_engine.py`: ticker/feature readiness gates and peer unlock worklists.
- `src/research_decisions.py`: readiness-aware research buckets, blockers, confidence, and next actions.
- `src/stock_report.py`: single-stock report assembly and Markdown output.

The project uses standard Python libraries such as `pandas`, `numpy`, `PyYAML`, and `streamlit` for data handling and UI. Optional `yfinance` support is an unofficial research-grade data adapter. These dependencies support the workflow; they are not the analysis rules, recommendation logic, or account-execution systems.

## Development Helper Boundary

Development-side plugins or assistant skills are optional helpers outside the shipped product. They are not shipped analysis rules, embedded valuation logic, recommendation logic, broker integrations, or sources of trusted runtime data.

If those plugins are used during development, their output still has to be translated into deterministic repo code, local CSV schemas, tests, and research-only wording before it belongs in the product. The public product should be judged by the files in this repository, the local data it is given, and the tests that verify readiness gates and guardrails.

## Supported-Today Assessment

The current functions are strong enough for a transparent local research prototype, single-stock review, market/ETF monitoring, and DCF-ready company analysis when trusted data exists. They are not yet a full-market data platform because fundamentals, peer data, earnings, and analyst estimates are intentionally sparse until trusted rows are imported.

The next quality unlock is not more indicators. It is better data coverage, better source/freshness visibility, more trusted fundamentals/peer rows, and continued UI polish so blocked analysis feels intentional rather than broken.
