# LinkedIn Project Brief

## Short Version

I built a local, CSV-first stock research command center that focuses on data readiness before analysis. Instead of jumping straight to stock picks, it checks whether each ticker has enough trusted local data for price, momentum, liquidity, correlation, fundamentals, DCF, peer comparison, earnings, and analyst-estimate context.

The system generates readiness-aware research decisions, single-stock reports, source readiness checks, and a Streamlit dashboard for deciding what can be researched now and what data should be imported next. Single-stock reports open with a visitor scan cue, then `At A Glance`, `Reader Guide`, `Evaluation Snapshot`, `Proof Checklist`, and `Best Review Path` before deeper methodology sections, so readers can quickly see the report mode, valuation boundary, which data-confidence cue applies, which local method is being used, what to read first, which command proves the next trusted input, current proof, and next trusted input.

The scan path covers `DCF-ready review`, `Standalone DCF review`, `Price/setup review only`, `Monitor-only context`, and `Data needed before analysis` modes, with the valuation boundary and DCF method path visible before detailed report tables.

## Suggested LinkedIn Post

I have been building a local Python stock research command center focused on a simple principle:

Data readiness first. Analysis second. Research decision last.

The project tracks a broad market universe, separates it from an active research list, and makes every analysis feature explicit: price, momentum, liquidity, correlation, fundamentals, DCF, peer data, earnings, and analyst estimates.

What I like most about the design is that missing data does not disappear. If a ticker is not ready, the app shows the exact blocker and the next local CSV workflow that would prove the analysis is ready. If an analysis does not apply, such as operating-company DCF for ETF/index proxies, the output labels it as excluded instead of failed.

Current features:

- Market-wide ticker readiness model.
- Purpose-aware research decisions.
- Streamlit command center dashboard.
- Single-stock Markdown reports.
- At A Glance summaries that put mode, decision view, DCF state, peer context, optional context, method cue, and next local step at the top.
- Evaluation Snapshot summaries that state supported evaluation, valuation boundary, data-confidence cue, next proof step, and stop rule before detailed sections.
- Proof Checklist sections that show why the current mode is allowed and what must stay withheld until trusted rows exist.
- Best Review Path cards that tell readers whether to review DCF and peers, prove fundamentals readiness, use monitor context, or start with price coverage.
- Analysis Quality labels and data-confidence cues that separate DCF-ready companies, standalone DCF review, price/setup-only reviews, ETF/index monitor context, and the data-needed-before-analysis mode.
- Methodology sections that show the DCF formula path, readiness gates, peer boundaries, and why missing fields are not inferred.
- Evaluation Function Check tables that show which functions are ready, blocked, excluded, or optional for a selected ticker.
- Copyable Proof Commands that keep next steps local, capped, and research-only.
- Source-readiness sections.
- A public Data Strategy guide for what can refresh safely, what needs trusted local input, and why the next coverage milestone should be a 5-10 company pilot instead of fabricated full-universe readiness.
- A read-only `make trusted-data-pilot-candidates TOP_N=10` command that ranks current company blockers with a compact shortlist, quick path, and review board without importing rows or fabricating data; `VERBOSE=1` adds full file status, decision gates, rejected-row paths, and evidence expectations.
- A plain selection rule for the pilot: choose 5-10 operating companies only when source proof exists, review the lane mix, and treat a useful pilot win as before/after report evidence plus rebuilt readiness, not just a new CSV row.
- A read-only `make trusted-data-pilot-packet TICKER=CRDO` command that prints the before report, focused blocker check, lane review path, review decision, evidence expectation, validate/apply step, rejected-row report, rebuild proof, and evidence row for one company.
- A follow-up `make trusted-data-pilot TICKERS=<chosen names> TOP_N=10` command that prints the evidence loop for selected pilot companies.
- A suggested starter company pilot: `NVDA,AVGO,AMD,MU,CRDO,COHR,LITE,HOOD,TSLA,META`, with `QQQ` and `SMH` kept as ETF/index monitor demos rather than operating-company DCF targets.
- A pilot evidence bundle: before/after readiness counts, one regenerated Markdown report per company, and the validation commands that changed the state.
- A one-company evidence packet: baseline readiness, before report, focused blocker check, lane review path, review decision, evidence expectation, validate/preview/apply, rejected-row check, rebuild proof, and still-blocked evidence row.
- CSV-first, preview-first local import workflows.
- Original local analysis rules for readiness gates, DCF boundaries, peer readiness, decision buckets, and report wording; Python libraries and optional provider adapters support data handling and UI.
- Research-only guardrails: no broker integration, no order routing, no auto-trading, and no direct buy/sell instructions.

This was a great project for practicing product thinking, deterministic data workflows, test coverage, and financial-analysis guardrails in Python.

GitHub: https://github.com/YuzeJ21/Stock-Analysis

## Resume Bullet Options

- Built a Python and Streamlit stock research command center that evaluates market-wide ticker readiness before generating research decisions.
- Designed a CSV-first data pipeline covering price, momentum, liquidity, correlation, fundamentals, DCF, peer mapping, earnings, and analyst-estimate readiness.
- Implemented readiness-aware decision outputs that separate `Research Now`, `Monitor`, and `Blocked by Data` states with explicit blockers and next actions.
- Added single-stock At A Glance, Reader Guide, Evaluation Snapshot, Proof Checklist, Best Review Path, Analysis Quality, Methodology, Evaluation Function Check, and Copyable Proof Commands sections to explain whether each report supports DCF-ready review, standalone DCF review, monitor-only context, price/setup review, or data-needed-before-analysis work, with the valuation boundary and DCF method path visible before detailed report tables.
- Added source readiness checks, preview-first local import validation, rejected-row reporting, and research-only guardrails to prevent overclaims.
- Documented which parts are original analysis rules, which parts are support libraries, and which actions remain permanently out of scope.
- Created deterministic tests for report wording, dashboard helpers, readiness gates, decision consistency, and no broker/order/trading language.

## Demo Talking Points

- In GitHub, start with the README example map and click the tracked sample reports under `outputs/stock_reports/`.
- Use `docs/PUBLIC_DEMO_WALKTHROUGH.md` as the short live-demo script.
- Start with `make status-check TOP_N=5` to show the read-only command-center summary without refreshing local artifacts.
- Open `outputs/stock_reports/nvda.md` to show a company report with At A Glance status, Evaluation Snapshot, Proof Checklist, Best Review Path, method cue, DCF assumptions, DCF formula path, Analysis Quality notes, Methodology, Evaluation Function Check, and Copyable Proof Commands.
- Open `outputs/stock_reports/a.md` or `outputs/stock_reports/mu.md` to show standalone DCF review where peer-relative valuation is still locked; `MU` now shows mapped-peer valuation inputs as the next proof path.
- Open `outputs/stock_reports/meta.md` to show price/setup review where valuation remains gated until trusted fundamentals and DCF inputs are ready.
- Open `outputs/stock_reports/qqq.md` or `outputs/stock_reports/smh.md` to show ETF/index monitor handling where DCF and peer valuation are excluded, not failed.
- Open `outputs/stock_reports/apld.md` or `outputs/stock_reports/crdo.md` to show how the product handles blocked data without inventing valuation conclusions, including the exact copyable local commands for the next proof step and one-company pilot packet.
- Run `make trusted-data-pilot-candidates TOP_N=10` to show which company blockers the current local data suggests improving next; use `VERBOSE=1` only when you want local proof detail.
- Run `make trusted-data-pilot-packet TICKER=CRDO` to show the one-company evidence packet without importing or applying rows.
- Then run `make trusted-data-pilot TICKERS=<chosen names> TOP_N=10` to show the safe company-focused path for trusted fundamentals, DCF, and peer inputs.
- Use the one-company evidence packet to explain that a useful coverage win needs before/after proof, source evidence, and a rebuilt report, not just a new CSV row.
- Explain that the pilot is intentionally small: pick 5-10 operating companies where the missing input can be source-reviewed, and leave the rest visibly blocked by missing data until trusted rows exist.
- Mention that `QQQ` and `SMH` demonstrate monitor context; the company pilot should use operating-company tickers.
- Run `make dashboard` locally to show readiness cards, next-action cards, and single-stock drilldowns.
- Point to `docs/METHODOLOGY.md` when someone asks how the analysis is calculated, to `docs/analysis_capability_audit.md` when someone asks what is strong or intentionally limited today, and to `docs/DATA_STRATEGY.md` when someone asks how coverage can improve without fabricating fundamentals, peers, earnings, or estimates.
- Mention that the project is intentionally research-only and does not connect to a broker or place trades.
