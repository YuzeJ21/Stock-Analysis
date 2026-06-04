# Stock Research Command Center

A local, CSV-first research dashboard for screening stocks, reviewing portfolio names, and seeing exactly which data is ready enough to trust.

> Data readiness first, analysis second, research decision last.

![Dashboard preview](docs/assets/dashboard-preview.svg)

## What It Does

This project turns a broad stock universe into a research workflow:

- Checks market data readiness before showing analysis.
- Separates `Research Now`, `Monitor`, and `Blocked by Data` review queues.
- Explains missing prices, fundamentals, DCF inputs, peers, earnings, and analyst estimates.
- Generates transparent CSV outputs for market direction, momentum, portfolio review, valuation context, watchlists, and research decisions.
- Provides a Streamlit dashboard plus single-stock reports with source/freshness notes.

## Why It Matters

Many stock tools jump straight to rankings. This command center treats missing data as a first-class signal: if a ticker is not ready for a specific analysis, it says why and shows the next local data-unlock step. That makes the output more trustworthy, not weaker.

## What You Can Analyze

When trusted local data is available, the command center can produce:

- Price, momentum, liquidity, and market-direction context.
- Portfolio purpose checks and thesis-review flags.
- DCF readiness and conservative scenario valuation.
- Peer-context readiness without pretending missing peer valuation exists.
- ETF/index monitor reports where operating-company DCF is excluded.
- Single-stock reports with risks, blockers, next research steps, and source/freshness notes.

Most blocked rows are not errors. They are data gaps the command center exposes instead of hiding.

## Current Snapshot

The local sample currently tracks a broad universe of 3,538 tickers, with a smaller subset ready for each analysis feature. Exact ready counts can change after local refresh/import work, so use `make status-check TOP_N=5` or the dashboard Home page for the current snapshot.

## What Works Today

This is a working local research prototype with deterministic CSV outputs, dashboard smoke coverage, and regression tests. Strongest today: readiness gates, single-stock explanations, ETF/index monitor context, and DCF-ready company review. Main modes: `DCF-ready review`, `Standalone DCF review`, `Price/setup review only`, `Monitor-only context`, and `Data-unlock only`.

Useful with limits: price/momentum, fundamentals/DCF, peer workflow, and final decision buckets when trusted local data exists. Intentionally locked: broad-universe fundamentals, peer valuation, earnings, and analyst estimates until trusted rows are imported. Not built to be: a full-market data vendor, real-time recommendation service, broker workflow, or auto-refreshing trading system.

## Preview

The dashboard is designed as an operator console:

- `Overview`: readiness, blockers, and next commands.
- `Monthly Picks`: conservative research candidates when data supports them.
- `Market Direction`: theme and sector/ETF context.
- `Momentum Leaders`: trend, relative strength, extension risk, and setup status.
- `Portfolio Review`: holdings reviewed against declared purpose and risk.
- `Value / Re-rating`: DCF and valuation modes with ready, locked, and monitor-only guardrails.
- `Final Watchlist`: readiness-state output, not an action list.
- `Single-Stock Report`: ticker-level report with source/freshness audit.
- `Data Health`: import paths, rejected-row reports, and unlock queues.

## Quick Start

```bash
pip install -e .[dev]
make pipeline
make readiness
make stock-report TICKER=NVDA
make dashboard-smoke
make dashboard
```

## Visitor-Friendly Commands

Use these from the repository root:

```bash
make help
make status-check TOP_N=5
make pipeline
make readiness
make project-status
make research-health-check TOP_N=10
make stock-report TICKER=NVDA
make dashboard
```

## Try This Demo Path

```bash
make stock-report TICKER=NVDA   # company report with DCF assumptions
make stock-report TICKER=QQQ    # ETF/index report with DCF excluded
make stock-report TICKER=SMH    # sector ETF monitor report
make stock-report TICKER=APLD   # partial-data blocker report
make dashboard
```

In the dashboard, start on `Home`, then open `Single-Stock Report` for one ticker or `Data Health` when the Home page says analysis is blocked. Technical file paths and update commands are intentionally tucked into advanced sections.

For a deeper local runbook, see [Operator Guide](docs/OPERATOR_GUIDE.md).

Targeted data-unlock examples:

```bash
make price-worklist TOP_N=10
make focus-fundamentals TICKER=NVDA
make peer-mapping-queue TOP_N=10
make optional-context-worklist TOP_N=10
```

For a larger local price refresh, use capped batches instead of repeating small commands manually:

```bash
make price-refresh-loop DRY_RUN=1
make price-refresh-loop BATCHES=5 TOP_N=100 PROVIDER=yahoo SLEEP_SECONDS=30
```

Preview-first import flow:

```bash
make templates
make imports-validate
make imports-preview
make imports-apply
```

## Generated Data Hygiene

Small example outputs are included for review. Large refreshed files such as `data/prices.csv`, readiness CSVs, and generated report CSVs are local working data by default. Review them before committing; do not publish broad refresh churn unless intentionally selected.

## Analysis Logic Provenance

The stock-analysis logic is implemented in this repository: readiness gates, momentum rules, DCF assumptions, relative-valuation checks, peer readiness, and report wording live under `src/`. Standard Python packages support data handling and UI; optional `yfinance` is an unofficial research-grade adapter. Codex plugins or skills are development helpers, not shipped product dependencies: the analysis rules, valuation gates, decision buckets, and research-only guardrails come from repo code plus local CSV inputs. See [Analysis Capability Audit](docs/analysis_capability_audit.md) for what is strong today, what remains limited, and where the logic lives.

## Core Outputs

The main pipeline writes deterministic CSVs under `outputs/`:

- `purpose_classification.csv`
- `market_direction.csv`
- `momentum_leaders.csv`
- `portfolio_review.csv`
- `undervalued_candidates.csv`
- `final_watchlist.csv`
- `research_decisions.csv`

Readiness and source-health reports live under `data/reports/`.

## Research-Only Guardrails

This is investment research software, not investment advice and not a trading system.

It does not:

- place orders;
- connect to brokers;
- route trades;
- auto-trade;
- recommend option trades;
- provide direct buy/sell instructions;
- fabricate prices, fundamentals, peers, earnings, analyst estimates, valuation inputs, or recommendations.

That constraint is intentional. The product is useful because it says when data is missing instead of pretending every ticker is ready.

## Architecture

- `src/dashboard.py`: Streamlit command center.
- `src/readiness_engine.py`: ticker and feature readiness checks.
- `src/research_decisions.py`: readiness-aware decision buckets.
- `src/stock_report.py`: single-stock report CLI and Markdown output.
- `src/providers/`: local CSV provider interfaces plus optional research-grade adapters.
- `data/`: local CSV inputs and readiness reports.
- `outputs/`: generated research outputs.
- `tests/`: regression coverage for calculations, readiness gates, dashboard helpers, and safety guardrails.

The project is CSV-first and deterministic by default. Optional network-backed data stays behind provider interfaces and is labeled as research-grade when used.

## Roadmap Snapshot

The next product stage is not more unsupported indicators. It is better operator workflow: clearer readiness history, trusted fundamentals/DCF unlocks, source-backed peer mappings, optional earnings/estimate imports, and sharper source/freshness auditability.
