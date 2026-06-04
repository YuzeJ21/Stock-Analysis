# Analysis Capability Audit

This project is a local research command center. It is strongest when the user has trusted local CSV data and weakest when a ticker is missing prices, fundamentals, peers, earnings, or analyst-estimate rows.

## Plain Answer

The current functions are good enough for a transparent local research prototype, single-stock review, ETF/index monitoring, and DCF-ready company analysis when trusted local inputs exist.

They are not good enough for broad-universe valuation conclusions without more trusted data. Missing fundamentals, peer mappings, earnings, or analyst estimates are intentionally shown as locked or blocked states instead of being turned into weak analysis.

The shipped analysis logic is repo-native. Open-source Python packages support data handling, UI, tests, and optional provider access, but they are not the stock-analysis rules. Development plugins or assistant skills can help review the project, but they are not shipped product logic or trusted runtime data.

## What Is Strong Today

- **Readiness gating:** every ticker is checked before deeper analysis appears.
- **Price and momentum review:** moving averages, returns, relative strength, volume context, and volatility/ATR proxy are calculated from local price rows.
- **Fundamentals readiness:** company fundamentals are validated for the fields needed by DCF and quality checks.
- **DCF workflow:** DCF uses explicit assumptions, conservative caps, scenario outputs, and sensitivity tables when required inputs are available.
- **Peer workflow:** peer comparison is withheld until source-backed peer mappings and peer metrics exist.
- **ETF/index handling:** operating-company DCF is excluded for ETF/index/fund monitor context instead of being shown as failed.
- **Single-stock report:** one ticker can be reviewed with readiness, supported analysis, blocked analysis, valuation state, risk notes, next step, and source/freshness notes.

## Function Quality Matrix

| Function area | Quality verdict | Best use today | Needs trusted data | What it refuses to do | Main implementation |
| --- | --- | --- | --- | --- | --- |
| Readiness gates | Strong today. | Decide whether a ticker can support deeper review. | Local ticker, price, fundamentals, peer, earnings, and estimate readiness rows. | It does not turn missing data into a weak conclusion. | `src/readiness_engine.py` |
| Price and momentum | Good when local price history is ready. | Review setup, trend, liquidity, and market context. | Daily OHLCV rows with enough history for returns, averages, liquidity, and volatility context. | It does not invent missing price history or fill broad-universe gaps silently. | `src/indicators.py`, `src/momentum_engine.py` |
| Fundamentals and DCF | Good for DCF-ready companies only. | Review assumptions, scenarios, and sensitivity with trusted local inputs. | Trusted fundamentals with revenue, free cash flow or FCF margin, shares outstanding, price, cash, and debt where available. | It does not label not-ready companies undervalued or overvalued. | `src/value_engine.py`, `src/valuation.py` |
| Peer comparison | Workflow-ready, coverage-limited. | Use as a peer data-unlock workflow until source-backed peers and peer metrics are ready. | Source-backed peer mappings plus peer price/fundamentals rows. | It does not treat sector or industry fallback as trusted peer valuation. | `src/readiness_engine.py`, `src/valuation.py` |
| ETF/index monitor context | Good for monitor context only. | Review market, theme, liquidity, and risk context without operating-company DCF. | Price, liquidity, correlation, and theme context. | It does not run operating-company DCF for ETFs, index proxies, or funds. | `src/research_decisions.py`, `src/stock_report.py` |
| Single-stock report | Strongest visitor-facing workflow. | See one ticker's ready, blocked, excluded, optional, and source/freshness states step by step. | Current local readiness, price, decision, DCF, peer, and optional-context outputs. | It does not provide allocation instructions or unsupported recommendations. | `src/stock_report.py`, `src/dashboard.py` |
| Dependencies | Support layer, not analysis logic. | Handle data frames, UI, tests, YAML config, and optional research-grade provider access. | Local CSV inputs remain the source of truth by default. | They do not replace repo-native analysis rules or trusted local data. | `pyproject.toml` |

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

The project uses standard Python libraries for support work. Based on `pyproject.toml`, shipped dependencies are:

| Dependency | Role in this project | Analysis boundary |
| --- | --- | --- |
| `numpy` | Numeric support for calculations and data preparation. | Not a stock-analysis rule source. |
| `pandas` | CSV/data-frame loading, joins, validation, and report tables. | Not a stock-analysis rule source. |
| `PyYAML` | Configuration loading. | Not a valuation or decision engine. |
| `streamlit` | Local dashboard UI. | Not analysis logic. |
| `yfinance` | Optional unofficial research-grade data adapter. | Optional provider access only; local CSVs and source/freshness checks still gate analysis. |
| `pytest` | Development/test dependency. | Verifies behavior; not product logic. |

These dependencies support the workflow; they are not the analysis rules, recommendation logic, valuation gates, or account-execution systems.

## Development Helper Boundary

Development-side plugins or assistant skills are optional helpers outside the shipped product. They are not shipped analysis rules, embedded valuation logic, recommendation logic, broker integrations, or sources of trusted runtime data.

If those plugins are used during development, their output still has to be translated into deterministic repo code, local CSV schemas, tests, and research-only wording before it belongs in the product. The public product should be judged by the files in this repository, the local data it is given, and the tests that verify readiness gates and guardrails.

The Public Equity Investing and Investment Banking plugins are not listed in `pyproject.toml` and are not runtime dependencies of this product. If used during development review, they remain helper context only; they do not supply trusted prices, fundamentals, peer mappings, earnings, analyst estimates, valuation inputs, or shipped recommendations.

## Supported-Today Assessment

The current functions are strong enough for a transparent local research prototype, single-stock review, market/ETF monitoring, and DCF-ready company analysis when trusted data exists. They are not yet a full-market data platform because fundamentals, peer data, earnings, and analyst estimates are intentionally sparse until trusted rows are imported.

The next quality unlock is not more indicators. It is better data coverage, better source/freshness visibility, more trusted fundamentals/peer rows, and continued UI polish so blocked analysis feels intentional rather than broken.
