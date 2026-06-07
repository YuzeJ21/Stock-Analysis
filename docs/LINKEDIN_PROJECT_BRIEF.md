# LinkedIn Project Brief

## Short Version

I built a local, CSV-first stock research command center that focuses on data readiness before analysis. Instead of producing unsupported stock picks, it checks whether each ticker has enough trusted local data for price, momentum, liquidity, correlation, fundamentals, DCF, peer comparison, earnings, and analyst-estimate context.

The system generates readiness-aware research decisions, single-stock reports, source readiness checks, and a Streamlit dashboard for deciding what can be researched now and what data should be imported next. Single-stock reports now open with `At A Glance`, then `Best Review Path`, then `Analysis Quality`, `Methodology`, `Evaluation Function Check`, and `Copyable Unlock Commands` sections so readers can see whether a ticker is in `DCF-ready review`, `Standalone DCF review`, `Price/setup review only`, `Monitor-only context`, or `Data-unlock only` mode, which local method is being used, what to read first, and what command would unlock the next trusted input.

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
- At A Glance summaries that put mode, decision view, DCF state, peer context, optional context, method cue, and next local step at the top.
- Best Review Path cards that tell readers whether to review DCF and peers, unlock fundamentals, use monitor context, or start with price coverage.
- Analysis Quality labels that separate DCF-ready companies, standalone DCF review, price/setup-only reviews, ETF/index monitor context, and data-unlock mode.
- Methodology sections that show the DCF formula path, readiness gates, peer boundaries, and why missing fields are not inferred.
- Evaluation Function Check tables that show which functions are ready, blocked, excluded, or optional for a selected ticker.
- Copyable Unlock Commands that keep next steps local, capped, and research-only.
- Source-readiness sections.
- A public Data Strategy guide for what can refresh safely, what needs trusted local input, and why the next coverage milestone should be a 5-10 company pilot instead of a fabricated full-universe unlock.
- CSV-first, preview-first local import workflows.
- Original local analysis rules for readiness gates, DCF boundaries, peer readiness, decision buckets, and report wording; Python libraries and optional provider adapters support data handling and UI.
- Research-only guardrails: no broker integration, no order routing, no auto-trading, and no direct buy/sell instructions.

This was a great project for practicing product thinking, deterministic data workflows, test coverage, and financial-analysis guardrails in Python.

GitHub: https://github.com/YuzeJ21/Stock-Analysis

## Resume Bullet Options

- Built a Python and Streamlit stock research command center that evaluates market-wide ticker readiness before generating research decisions.
- Designed a CSV-first data pipeline covering price, momentum, liquidity, correlation, fundamentals, DCF, peer mapping, earnings, and analyst-estimate readiness.
- Implemented readiness-aware decision outputs that separate `Research Now`, `Monitor`, and `Blocked by Data` states with explicit blockers and next actions.
- Added single-stock At A Glance, Best Review Path, Analysis Quality, Methodology, Evaluation Function Check, and Copyable Unlock Commands sections to explain whether each report supports DCF-ready review, standalone DCF review, monitor-only context, price/setup review, or data-unlock work, with the DCF method path visible before detailed report tables.
- Added source readiness checks, preview-first local import validation, rejected-row reporting, and research-only guardrails to prevent unsupported conclusions.
- Documented which parts are original analysis rules, which parts are support libraries, and which actions remain permanently out of scope.
- Created deterministic tests for report wording, dashboard helpers, readiness gates, decision consistency, and no broker/order/trading language.

## Demo Talking Points

- In GitHub, start with the README example map and click the tracked sample reports under `outputs/stock_reports/`.
- Start with `make project-status` to show the command-center summary.
- Open `outputs/stock_reports/nvda.md` to show a company report with At A Glance status, Best Review Path, method cue, DCF assumptions, DCF formula path, Analysis Quality notes, Methodology, Evaluation Function Check, and Copyable Unlock Commands.
- Open `outputs/stock_reports/a.md` to show standalone DCF review where peer-relative valuation is still locked.
- Open `outputs/stock_reports/meta.md` to show price/setup review where valuation remains gated until trusted fundamentals and DCF inputs are ready.
- Open `outputs/stock_reports/qqq.md` or `outputs/stock_reports/smh.md` to show ETF/index monitor handling where DCF and peer valuation are excluded, not failed.
- Open `outputs/stock_reports/apld.md` to show how the product handles blocked data without inventing valuation conclusions, including the exact copyable local commands for the next unlock.
- Run `make dashboard` locally to show readiness cards, next-action cards, and single-stock drilldowns.
- Point to `docs/METHODOLOGY.md` when someone asks how the analysis is calculated, to `docs/analysis_capability_audit.md` when someone asks what is strong or intentionally limited today, and to `docs/DATA_STRATEGY.md` when someone asks how coverage can improve without fabricating fundamentals, peers, earnings, or estimates.
- Mention that the project is intentionally research-only and does not connect to a broker or place trades.
