# Stock Research Command Center

A local, CSV-first research dashboard for screening stocks, reviewing portfolio names, and seeing exactly which data is ready to support analysis.

> Data readiness first, analysis second, research decision last.

![Dashboard preview](docs/assets/dashboard-preview.svg)

## What It Does

This project turns a broad stock universe into a research workflow:

- Checks market data readiness before showing analysis.
- Separates `Research Now`, `Monitor`, and `Blocked by Data` review queues.
- Explains missing prices, fundamentals, DCF inputs, peers, earnings, and analyst estimates.
- Generates transparent CSV outputs for market direction, momentum, portfolio review, valuation context, watchlists, and research decisions.
- Provides a Streamlit dashboard plus single-stock reports with At A Glance status, source/freshness notes, and copyable local unlock commands, plus a plain-English Reader Guide.

## Why It Matters

Many stock tools jump straight to rankings. This command center treats missing data as a first-class signal: if a ticker is not ready for a specific analysis, it says why and shows the next local data-unlock step. That makes the output more trustworthy, not weaker.

## What You Can Analyze

When trusted local data is available, the command center can produce:

- Price, momentum, liquidity, and market-direction context.
- Portfolio purpose checks and thesis-review flags.
- DCF readiness and conservative scenario valuation.
- Peer-context readiness without pretending missing peer valuation exists.
- ETF/index monitor reports where operating-company DCF is excluded.
- Single-stock reports with At A Glance status, methodology, risks, blockers, copyable local unlock commands, source/freshness notes, and a Reader Guide.

Most blocked rows are not errors. They are data gaps the command center exposes instead of hiding.

## How Analysis Works

The report is not a black box: local data rows provide inputs, and project rules decide what can be analyzed.

1. Readiness gate: checks prices, fundamentals, DCF fields, peers, earnings, and estimates before deeper analysis appears.
2. Supported analysis: price-ready rows can support setup/risk context, DCF-ready rows can support assumptions and sensitivity, and peer-ready rows can support source-backed relative context.
3. Locked or excluded boundaries: missing fundamentals, peer inputs, earnings, or estimates stay locked; ETF/index/fund DCF is excluded, not failed.
4. Report explanation: single-stock reports show what came from source rows, what the product calculated, what stayed withheld, and the next copy-only local step.

## Current Snapshot

The local sample currently tracks a broad universe of 3,538 tickers, with a smaller subset ready for each analysis feature. Exact ready counts can change after local refresh/import work, so use `make status-check TOP_N=5` or the dashboard Home page for the current snapshot.

## What Works Today

This is a working local research prototype with deterministic CSV outputs, dashboard smoke coverage, and regression tests. Strongest today: readiness gates, single-stock explanations, ETF/index monitor context, and DCF-ready company review. Main modes: `DCF-ready review`, `Standalone DCF review`, `Price/setup review only`, `Monitor-only context`, and `Data-unlock only`.

Useful with limits: price/momentum, fundamentals/DCF, peer workflow, and final decision buckets when trusted local data exists. Intentionally locked: broad-universe fundamentals, peer valuation, earnings, and analyst estimates until trusted rows are imported. Not built to be: a full-market data vendor, real-time recommendation service, broker workflow, or auto-refreshing trading system.

## Preview

The dashboard is designed as an operator console: `Home` shows readiness, blockers, methodology, examples, and next commands; focused pages cover Monthly Picks, Market Direction, Momentum Leaders, Portfolio Review, Value / Re-rating, Final Watchlist as readiness-state output, not an action list, Single-Stock Report, and Data Health.

## Quick Start

Run these from the repository root so `make` can find the project targets:

```bash
pip install -e '.[dev]'
make pipeline
make readiness
make demo
make stock-report-md TICKER=NVDA
make public-check
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
make stock-report-md TICKER=NVDA
make public-check
make dashboard
```

## Try This Demo Path

```bash
make demo                       # prints the clean visitor path
make stock-report-md TICKER=NVDA # company report with DCF assumptions
make stock-report-md TICKER=A    # standalone DCF report with peer workflow still locked
make stock-report-md TICKER=META # price/setup report with valuation still gated
make stock-report-md TICKER=QQQ  # ETF/index report with DCF excluded
make stock-report-md TICKER=SMH  # sector ETF monitor report
make stock-report-md TICKER=APLD # partial-data blocker report
make dashboard
```

Example map:

| Example | What it demonstrates | What to check |
| --- | --- | --- |
| [NVDA](outputs/stock_reports/nvda.md) | Company DCF assumptions and source-backed peer context from trusted local inputs. | Reader Guide, assumptions, sensitivity, peer caveats, source/freshness notes. |
| [A](outputs/stock_reports/a.md) | Standalone DCF review where peer-relative valuation is still locked. | Reader Guide, DCF assumptions, and the next peer data-unlock step. |
| [META](outputs/stock_reports/meta.md) | Price/setup review where valuation remains gated until trusted fundamentals/DCF inputs are ready. | Reader Guide, supported setup analysis, valuation blockers, and caveats. |
| [QQQ](outputs/stock_reports/qqq.md) / [SMH](outputs/stock_reports/smh.md) | ETF/index or sector monitor context. | Reader Guide plus Operating-company DCF is excluded, not failed. |
| [APLD](outputs/stock_reports/apld.md) | Blocked-data handling. | Reader Guide. No valuation conclusion appears until trusted price rows exist. |

In the dashboard, start on `Home`, then open `Single-Stock Report` for one ticker or `Data Health` when the Home page says analysis is blocked. Markdown reports start with `At A Glance`, then a `Reader Guide` that answers what can be analyzed now, what is still locked or excluded, what trusted input matters next, and which copy-only command to run. They only show `Copyable Unlock Commands` when local data gaps block analysis. File paths and update commands stay inside collapsed help sections so visitors can read the product first. For public demos, prefer `make stock-report-md TICKER=NVDA`; use `make stock-report TICKER=NVDA` only when you want the optional machine-readable report data for local inspection.

Dashboard pages also support simple local deep links such as `http://localhost:8501/?page=single-stock-report`.

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

The dry run prints the planned batch size and total capped candidates before changing local files. If you need broader coverage, raise `BATCHES` first, dry-run again, then run the capped loop only when you are ready to update local CSVs and review the generated data churn. You should not need to repeat a 25-ticker command 100+ times.

Preview-first import flow:

```bash
make templates
make imports-validate
make imports-preview
make imports-apply
```

## Generated Data Hygiene

Small example outputs are included for review. Large refreshed files such as `data/prices.csv`, readiness CSVs, and generated report CSVs are local working data by default. Review them before committing; do not publish broad refresh churn unless intentionally selected.

Before sharing or committing, run `make public-check`, then `make diff-hygiene`. For a large dirty tree, run `make diff-hygiene-files` and review the ignored local pathspec files under `outputs/staging/` before staging. After staging, run `make staged-hygiene-check` before committing. The public check includes `make public-wording-check`, which scans visitor-facing docs, dashboard/report copy, and sample reports for unsupported advice, execution language, internal development notes, and stale repo links. Use the safe staging suggestion for product files and reviewed Markdown reports, and leave generated CSV/JSON churn out unless it is the specific artifact you intend to publish.

The tracked `data/holdings.csv` file is a zero-position sample for portfolio-review demos. Keep real holdings, account exports, and personal cost-basis details out of the public branch.

## License

Reuse terms are not specified yet because no `LICENSE` file has been selected. Visitors can review the project, but reuse rights are not granted until a license is added. See [License Decision Guide](docs/LICENSE_DECISION_GUIDE.md) before promoting the repo broadly.

## Analysis Methodology

The stock-analysis logic is implemented in this repository: readiness gates, momentum rules, DCF assumptions, relative-valuation checks, peer readiness, and report wording live under `src/`. Standard Python packages support data handling and UI; optional `yfinance` is an unofficial research-grade adapter. The analysis rules, valuation gates, decision buckets, and research-only guardrails come from project code plus local CSV inputs. Fundamentals-ready means trusted company fields can be reviewed, DCF-ready means scenario math can be reviewed, and peer-ready means source-backed relative context can be reviewed. See [Research Methodology](docs/METHODOLOGY.md) for the calculation flow and [Analysis Capability Audit](docs/analysis_capability_audit.md) for what is strong today, what remains limited, and where the logic lives.

## Core Outputs

The main pipeline writes deterministic CSVs under `outputs/`, including purpose classification, market direction, momentum leaders, portfolio review, valuation-readiness context, final watchlist, and research decisions. `undervalued_candidates.csv` is a legacy filename for valuation-readiness and re-rating context, not automatic undervalued calls. Readiness and source-health reports live under `data/reports/`.

## Research-Only Guardrails

This is investment research software, not investment advice and not a trading system. It does not place orders, connect to brokers, route trades, auto-trade, recommend option trades, provide direct buy/sell instructions, or fabricate prices, fundamentals, peers, earnings, analyst estimates, valuation inputs, or recommendations.

That constraint is intentional. The product is useful because it says when data is missing instead of pretending every ticker is ready.

## Architecture

The app is organized around `src/dashboard.py`, `src/readiness_engine.py`, `src/research_decisions.py`, `src/stock_report.py`, `src/providers/`, local `data/` CSVs, generated `outputs/`, and regression tests. It is CSV-first and deterministic by default. Optional network-backed data stays behind provider interfaces and is labeled as research-grade when used.

## Roadmap Snapshot

The next product stage is not more unsupported indicators. It is better operator workflow: clearer readiness history, trusted fundamentals/DCF unlocks, source-backed peer mappings, optional earnings/estimate imports, and sharper source/freshness auditability.
