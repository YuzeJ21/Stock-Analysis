# LinkedIn Project Brief

## Short Version

I built a local, CSV-first stock research command center that focuses on data readiness before analysis. Instead of producing unsupported stock picks, it checks whether each ticker has enough trusted local data for price, momentum, liquidity, correlation, fundamentals, DCF, peer comparison, earnings, and analyst-estimate context.

The system generates readiness-aware research decisions, single-stock reports, source/freshness audits, and a Streamlit dashboard for deciding what can be researched now and what data should be imported next. Single-stock reports also include `Analysis Quality` and `Evaluation Function Check` sections so readers can see whether a ticker is in `DCF-ready review`, `Standalone DCF review`, `Price/setup review only`, `Monitor-only context`, or `Data-unlock only` mode.

## Suggested LinkedIn Post

I have been building a local Python stock research command center focused on a simple principle:

Data readiness first. Analysis second. Research decision last.

The project tracks a broad market universe, separates it from an active research list, and makes every analysis feature explicit: price, momentum, liquidity, correlation, fundamentals, DCF, peer data, earnings, and analyst estimates.

What I like most about the design is that missing data does not disappear. If a ticker is not ready, the app shows the exact blocker and the next local CSV workflow to unlock it. If an analysis does not apply, such as operating-company DCF for ETF/index proxies, the output labels it as excluded instead of failed.

Current features:

- Market-wide ticker readiness model.
- Purpose-aware research decisions.
- Streamlit command center dashboard.
- Single-stock Markdown reports.
- Analysis Quality labels that separate DCF-ready companies, standalone DCF review, price/setup-only reviews, ETF/index monitor context, and data-unlock mode.
- Evaluation Function Check tables that show which functions are ready, blocked, excluded, or optional for a selected ticker.
- Source and freshness audit sections.
- CSV-first staged import workflows.
- Repo-native analysis logic under `src/`; Python libraries and optional provider adapters support data handling and UI, while plugins remain development helpers rather than shipped product logic.
- Research-only guardrails: no broker integration, no order routing, no auto-trading, and no direct buy/sell instructions.

This was a great project for practicing product thinking, deterministic data workflows, test coverage, and financial-analysis guardrails in Python.

GitHub: https://github.com/YuzeJ21/Stock-Analysis

## Resume Bullet Options

- Built a Python and Streamlit stock research command center that evaluates market-wide ticker readiness before generating research decisions.
- Designed a CSV-first data pipeline covering price, momentum, liquidity, correlation, fundamentals, DCF, peer mapping, earnings, and analyst-estimate readiness.
- Implemented readiness-aware decision outputs that separate `Research Now`, `Monitor`, and `Blocked by Data` states with explicit blockers and next actions.
- Added single-stock Analysis Quality and Evaluation Function Check sections to explain whether each report supports DCF-ready review, standalone DCF review, monitor-only context, price/setup review, or data-unlock work.
- Added source/freshness auditability, staged import validation, rejected-row reporting, and research-only guardrails to prevent unsupported conclusions.
- Documented that development plugins or assistant skills are optional helpers, not shipped analysis rules, recommendation logic, or broker integrations.
- Created deterministic tests for report wording, dashboard helpers, readiness gates, decision consistency, and no broker/order/trading language.

## Demo Talking Points

- Start with `make project-status` to show the command-center summary.
- Open `outputs/stock_reports/nvda.md` to show a company report with DCF assumptions, Analysis Quality notes, and the Evaluation Function Check.
- Open `outputs/stock_reports/qqq.md` or `outputs/stock_reports/smh.md` to show ETF/index monitor handling where DCF and peer valuation are excluded, not failed.
- Open `outputs/stock_reports/apld.md` to show how the product handles partial data without inventing valuation conclusions.
- Run `make dashboard` locally to show readiness cards, next-action cards, and single-stock drilldowns.
- Point to `docs/analysis_capability_audit.md` when someone asks where the analysis logic lives, what is strong or intentionally limited today, and why development helpers are not hidden product dependencies.
- Mention that the project is intentionally research-only and does not connect to a broker or place trades.
