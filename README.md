# Stock Research Command Center

A local, CSV-first research dashboard for screening stocks, reviewing portfolio names, and seeing exactly which data is ready to support analysis.

> Data readiness first, analysis second, research decision last.

![Dashboard preview](docs/assets/dashboard-preview.svg)

## What It Does

This project turns a broad stock universe into a readiness-first research dashboard. It checks market data before analysis, separates `Research Now`, `Monitor`, and `Blocked by Data` review states, explains missing prices, fundamentals, DCF inputs, peers, earnings, and analyst estimates, and produces Streamlit pages plus single-stock reports with At A Glance status, a plain-English Reader Guide, an Evaluation Snapshot, a Proof Checklist, Best Review Path, confidence cues, source readiness notes, and copyable local proof commands.

```mermaid
flowchart LR
    Home["Home: ready vs blocked"] --> Report["Single-stock report"]
    Report --> Health["Data Health: missing input"]
    Health --> Pilot["Trusted-data pilot"]
```

## Why It Matters

Many stock tools jump straight to rankings. This product treats missing data as a first-class signal: if a ticker is not ready for a specific analysis, it says why and shows the next local proof step. That makes the output more trustworthy, not weaker.

## What You Can Analyze

When trusted local data is available, the product can produce:

- Price, momentum, liquidity, and market-direction context.
- Portfolio purpose checks and thesis-review flags.
- DCF readiness and conservative scenario valuation.
- Peer-context readiness without pretending missing peer valuation exists.
- ETF/index monitor reports where operating-company DCF is excluded.
- Single-stock reports with At A Glance status, a Reader Guide, an Evaluation Snapshot, a Proof Checklist, Best Review Path, confidence cues, methodology, risks, blockers, copyable local proof commands, and source readiness notes.

Most blocked rows are not errors. They are data gaps the command center exposes instead of hiding.

## How Analysis Works

The report is not a black box: local data rows provide inputs, and project rules decide what can be analyzed.

1. Readiness gate: checks prices, fundamentals, DCF fields, peers, earnings, and estimates before deeper analysis appears.
2. Supported analysis: price-ready rows can support setup/risk context, DCF-ready rows can support assumptions and sensitivity, and peer-ready rows can support source-backed relative context.
3. Locked or excluded boundaries: missing fundamentals, peer inputs, earnings, or estimates stay locked; company valuation is excluded for ETF/index/fund monitor rows, not failed.
4. Report explanation: single-stock reports show what came from source rows, what the product calculated, what stayed withheld, and the next local proof step.

## Current Snapshot

The local sample currently tracks a broad universe of 3,538 tickers, with a smaller subset ready for each analysis feature. Exact ready counts can change after local refresh/import work, so use `make status-check TOP_N=5` or the dashboard Home page for the current snapshot.

Visitor status: the product workflow, dashboard, single-stock reports, readiness gates, demo path, and public checks are working. Broad fundamentals, DCF, peers, earnings, and analyst estimates remain visibly blocked by missing trusted data until trusted rows exist, so those gaps should be read as source-proof work rather than broken analysis.

## Data Coverage Strategy

The product separates refreshable data from judgment-required data:

| Data lane | Best next move | Why it matters |
| --- | --- | --- |
| Prices | Use `make price-refresh-loop DRY_RUN=1` before capped refreshes. | Price coverage can scale safely, but refreshed CSVs should be reviewed before commit. |
| Fundamentals / DCF | Use `make trusted-data-pilot-candidates TOP_N=10`, inspect one ticker with `make trusted-data-pilot-packet TICKER=CRDO`, then use SEC staging or trusted manual imports. | Company valuation only appears after required fields, validation, rejected-row review, and readiness proof pass. |
| Peers | Add source-backed peer mappings and peer inputs. | Peer trend and peer valuation stay separate; guessed peers do not become valuation. |
| Earnings / estimates | Keep locked until trusted local rows exist. | Empty optional context is intentional, not a broken chart. |

## What Works Today

This is a working local research prototype with deterministic outputs, dashboard smoke coverage, and regression tests. Strongest today: readiness gates, single-stock explanations, ETF/index monitor context, and DCF-ready company review. Main modes: `DCF-ready review`, `Standalone DCF review`, `Price/setup review only`, `Monitor-only context`, and `Data needed before analysis`.

Useful with limits: price/momentum, fundamentals/DCF, peer review, and final decision buckets when trusted local data exists. Intentionally locked: broad-universe fundamentals, peer comparison, earnings, and analyst estimates until trusted rows are imported. Not built to be: a full-market data vendor, real-time recommendation service, broker/execution system, or auto-refreshing trading system.

## Product Tour

Start with the three paths the dashboard is built around:

| Path | Use it when | First place to open |
| --- | --- | --- |
| Review one stock | You want a ticker-level research note with ready, blocked, excluded, and confidence states. | `Single-Stock Report` |
| Improve data coverage | You want to understand what trusted input is missing and how to add it safely. | `Data Health` |
| Explore ready names | You want to browse what the current local data can already support. | `Monthly Picks` |

The dashboard keeps methodology, file paths, and update commands in collapsed sections so visitors can read the product first. Focused pages cover Monthly Picks, Market Direction, Momentum Leaders, Portfolio Review, Value / Re-rating, Final Watchlist as readiness-state output, not an action list, Single-Stock Report, and Data Health.

Two-minute visitor tour:

1. Open `Home` to see what is ready, blocked, and intentionally locked.
2. Run one proof report, usually `make stock-report-md TICKER=NVDA`.
3. Open one blocked or excluded example, then run `make trusted-data-pilot-candidates TOP_N=10` to see how the next trusted-data review step would be chosen.

## Quick Start

Run these from the repository root so `make` can find the project targets. This first path is visitor-safe: it does not rebuild broad generated outputs before you have seen the product.

```bash
pip install -e '.[dev]'
make demo
make status-check TOP_N=5
make stock-report-md TICKER=NVDA
make dashboard
```

When you want to rebuild local outputs after changing data, use the deeper [Local Workflow Guide](docs/OPERATOR_GUIDE.md) for rebuild, import, refresh, and proof steps.

## Try This Demo Path

```bash
make demo                       # prints the visitor proof trail
make dashboard                  # open Home and follow the three public paths
make stock-report-md TICKER=NVDA # company report with DCF assumptions
make stock-report-md TICKER=META # price/setup report with valuation still gated
make stock-report-md TICKER=QQQ  # ETF/index report with DCF excluded
make stock-report-md TICKER=MU   # standalone DCF report with peer valuation still locked
make stock-report-md TICKER=CRDO # fundamentals/DCF proof packet example
make trusted-data-pilot-candidates TOP_N=10 # read-only coverage candidate list
```

Optional extra report states:

```bash
make stock-report-md TICKER=SMH  # sector ETF monitor report
make stock-report-md TICKER=APLD # price/setup report with fundamentals still locked
```

The shortest public walkthrough is: Home -> NVDA proof report -> META blocked example -> QQQ excluded example -> MU peer-limited example -> CRDO fundamentals-gated example -> trusted-data pilot. That shows the core idea quickly: the product can analyze ready data, explain blocked data, exclude methods that do not apply, show peer-limited DCF, and print the trusted-data proof path without pretending missing rows exist.

Example map:

| Example | What it demonstrates | What to check |
| --- | --- | --- |
| [NVDA](outputs/stock_reports/nvda.md) | Company DCF assumptions and source-backed peer context from trusted local inputs. | Reader Guide, assumptions, sensitivity, peer caveats, source readiness notes. |
| [A](outputs/stock_reports/a.md) / [MU](outputs/stock_reports/mu.md) | Standalone DCF review where peer-relative valuation is still locked. | Reader Guide, DCF assumptions, and the next peer missing-data step. |
| [META](outputs/stock_reports/meta.md) | Price/setup review where valuation remains gated until trusted fundamentals/DCF inputs are ready. | Reader Guide, supported setup analysis, valuation blockers, and caveats. |
| [QQQ](outputs/stock_reports/qqq.md) / [SMH](outputs/stock_reports/smh.md) | ETF/index or sector monitor context. | Reader Guide plus Operating-company DCF is excluded, not failed. |
| [APLD](outputs/stock_reports/apld.md) / [CRDO](outputs/stock_reports/crdo.md) | Price/setup review with valuation still locked, plus fundamentals-gated proof workflow. | Reader Guide, supported setup context, one-company pilot packet, and the next trusted fundamentals proof step. |

In the dashboard, start on `Home`, then open `Single-Stock Report` for one ticker or `Data Health` when the Home page says analysis is blocked. Markdown reports start with a visitor scan cue, then `At A Glance`, a `Reader Guide`, an `Evaluation Snapshot`, a `Proof Checklist`, and `Best Review Path` so readers know what can be analyzed now, what is still locked or excluded, what valuation is supported or blocked, what confidence cue applies, what evidence proves the current mode, what to read first, what trusted input matters next, and which copy-only command or proof step to run. They only show `Copyable Proof Commands` when local data gaps block analysis. File paths and update commands stay inside collapsed help sections so visitors can read the product first. For public demos, prefer `make stock-report-md TICKER=NVDA`; use `make stock-report TICKER=NVDA` only when you want the optional local report data for inspection.

For deeper local missing-data details, use the [Local Workflow Guide](docs/OPERATOR_GUIDE.md). For the coverage strategy behind prices, fundamentals, peers, earnings, and analyst estimates, read [Data Strategy](docs/DATA_STRATEGY.md). Those guides cover targeted worklists, preview-first imports, capped price refresh loops, readiness snapshots, and diff hygiene without making the README feel like an operations runbook.

When you are ready to improve real coverage, start with `make trusted-data-pilot-candidates TOP_N=10`. It ranks current operating-company blockers from local readiness outputs without importing or fabricating data. The default output is compact for visitors; add `VERBOSE=1` when you want full per-candidate file status, decision gates, rejected-row paths, and evidence expectations. Then run `make trusted-data-pilot-packet TICKER=CRDO` for a one-company before report, local file status, review path, validate/apply step, rejected-row report, and rebuild-proof packet, or `make trusted-data-pilot TICKERS=<comma-separated candidates> TOP_N=10` for the broader copyable evidence loop.

The pilot proof loop is simple: snapshot the baseline, review source proof, validate/preview and check rejected rows, rebuild readiness and the stock report, then compare the after report. Only the rebuilt report can prove a lane changed; if the source proof is missing or the report remains blocked, keep that blocker visible and move to the next candidate.

The trusted-data pilot has one simple decision rule: proceed only when source proof exists for the missing input. Otherwise, keep the ticker visibly blocked by missing data and move to the next candidate.

The broader read-only checklist is still available as `make trusted-data-pilot TOP_N=10` when you want the general pilot sequence before choosing tickers.

## Local Data Hygiene

Small example reports are included for review. Large refreshed files such as `data/prices.csv`, readiness CSVs, and report CSVs are local working data by default. Review them before committing; do not publish broad refresh changes unless intentionally selected.

Before sharing or committing, run `make public-check`, then `make diff-hygiene`. For a large dirty tree, run `make diff-hygiene-files` and review the ignored local pathspec files under `outputs/staging/` before staging. After staging, run `make staged-hygiene-check` before committing. The public check includes `make public-wording-check`, which scans visitor-facing docs, dashboard/report copy, and sample reports for unsupported advice, execution language, internal development notes, and stale repo links. Use the safe staging suggestion for product files and reviewed Markdown reports, and leave large generated CSV/JSON changes out unless they are the specific artifact you intend to publish.

The tracked `data/holdings.csv` file is a zero-position sample for portfolio-review demos. Keep real holdings, account exports, and personal cost-basis details out of the public branch.

## License

Reuse terms are not specified yet because no `LICENSE` file has been selected. Visitors can review the project, but reuse rights are not granted until a license is added. See [License Decision Guide](docs/LICENSE_DECISION_GUIDE.md) before promoting the repo broadly.

## Analysis Methodology

The stock-analysis method is implemented in this repository: readiness gates, momentum rules, DCF assumptions, relative-valuation checks, peer readiness, and report wording live under `src/`. Standard Python packages support data handling and UI; optional `yfinance` is an unofficial research-grade adapter. The analysis rules, valuation gates, decision buckets, and research-only guardrails come from project code plus local CSV inputs. Fundamentals-ready means trusted company fields can be reviewed, DCF-ready means scenario math can be reviewed, and peer-ready means source-backed relative context can be reviewed. See [Research Methodology](docs/METHODOLOGY.md) for the calculation flow and [Analysis Capability Audit](docs/analysis_capability_audit.md) for what is strong today, what remains limited, and where the method lives.

## Core Outputs

The main build creates deterministic research files under `outputs/`, including purpose classification, market direction, momentum leaders, portfolio review, valuation-readiness context, final watchlist, and research decisions. `undervalued_candidates.csv` is a legacy filename for valuation-readiness and re-rating context, not automatic undervalued calls. Readiness and source-health reports live under `data/reports/`.

## Research-Only Guardrails

This is investment research software, not investment advice and not a trading system. It does not place orders, connect to brokers, route trades, auto-trade, recommend option trades, provide direct buy/sell instructions, or fabricate prices, fundamentals, peers, earnings, analyst estimates, valuation inputs, or recommendations.

That constraint is intentional. The product is useful because it says when data is missing instead of pretending every ticker is ready.

## Architecture

The app is organized around dashboard, readiness, decision, report, provider, local-data, and test modules. It is CSV-first and deterministic by default. Optional network-backed data stays behind provider interfaces and is labeled as research-grade when used.

## Roadmap Snapshot

The next product stage is not more indicators. It is a clearer research review path: readiness history, trusted fundamentals/DCF proof paths, source-backed peer mappings, optional earnings/estimate imports, and sharper source readiness explanations.
