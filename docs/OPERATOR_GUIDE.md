# Local Workflow Guide

Use this guide when you want to run the command center locally after reading the short README.
For the higher-level data coverage strategy, see `docs/DATA_STRATEGY.md`.

The product principle stays the same:

1. Data readiness first.
2. Analysis second.
3. Research decision last.

The app is research-only. It does not connect to brokers, place orders, auto-trade, recommend option trades, or provide direct buy/sell instructions.

## First Local Run

Run these from the repository root:

```bash
make pipeline
make readiness
make project-status
make stock-report-md TICKER=NVDA
make dashboard
```

If you only want a fast health check:

```bash
make status-check TOP_N=5
make dashboard-smoke
```

## What To Open First

- Open `make dashboard` for the product page.
- Start on `Home` to see readiness, blockers, and next safe commands.
- Open the Home page `Example reports` section to compare richer company, standalone DCF, price/setup gated, monitor-only, and blocked-data examples without opening data files first.
- Open `Single-Stock Report` for one ticker when you want the clearest stock-level explanation.
- Open `Data Health` when the app says analysis is blocked by missing local data.

## Single-Stock Demo Path

These examples show the main states without needing a full-market refresh:

```bash
make stock-report-md TICKER=NVDA
make stock-report-md TICKER=A
make stock-report-md TICKER=META
make stock-report-md TICKER=QQQ
make stock-report-md TICKER=SMH
make stock-report-md TICKER=APLD
```

For public demos, prefer `make stock-report-md TICKER=NVDA`. Use `make stock-report TICKER=NVDA` only when you want the optional machine-readable report data for local inspection.

- `NVDA` demonstrates company-level DCF assumptions and source-backed peer context when trusted local inputs are ready.
- `A` demonstrates standalone DCF review where peer-relative valuation is still waiting on source-backed peers.
- `META` demonstrates price/setup review where valuation remains gated until trusted fundamentals and DCF inputs are ready.
- `QQQ` and `SMH` demonstrate ETF/index monitor context where operating-company DCF is excluded, not failed.
- `APLD` demonstrates partial-data handling where valuation stays blocked instead of being invented.

Read `At A Glance` first. It gives the mode, decision view, DCF state, peer context, optional context, method cue, and next local step before the detailed tables. Then read `Best Review Path` to see whether to inspect DCF and peers, unlock fundamentals, use monitor context, or start with price coverage.

Then read `Analysis Quality`, `Methodology`, and `Evaluation Function Check`. They explain which functions are ready, blocked, excluded, or optional. The At A Glance method cue and the `Methodology` section show the DCF formula path so the valuation workflow is not a black box.

When a ticker is blocked or partial, use `Copyable Unlock Commands` next. Those are local research commands to copy when you choose; the report does not run imports or refreshes and does not connect to external accounts.

## Analysis Modes

The dashboard and single-stock report use plain modes before showing detailed tables:

- `DCF-ready review`: company DCF inputs are ready for assumptions, scenarios, and sensitivity review.
- `Standalone DCF review`: company DCF can be reviewed, but peer-relative valuation is still waiting on source-backed peers.
- `Price/setup review only`: local price/setup context is available, but company valuation remains blocked.
- `Monitor-only context`: ETF/index/fund rows can support market, theme, liquidity, or risk monitoring; operating-company DCF is excluded.
- `Data-unlock only`: the ticker needs trusted local inputs before analysis should be interpreted.

## Data Unlock Workflows

Use targeted unlock commands instead of broad refreshes by default:

```bash
make price-worklist TOP_N=10
make focus-fundamentals TICKER=NVDA
make peer-mapping-queue TOP_N=10
make optional-context-worklist TOP_N=10
```

For local import files, use preview before apply:

```bash
make templates
make imports-validate
make imports-preview
make imports-apply
```

For larger price refreshes, dry-run first and keep batches capped:

```bash
make price-refresh-loop DRY_RUN=1
make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N=100 PROVIDER=yahoo
make readiness-snapshot
make price-refresh-loop MAX_CANDIDATES=3500 TOP_N=100 PROVIDER=yahoo SLEEP_SECONDS=30
make diff-hygiene
```

The dry run shows the planned loop command and total capped candidates before local files change. This is the scalable path for broad coverage work; set `MAX_CANDIDATES` to the approximate number of missing-price rows you want to cover, dry-run again, snapshot readiness, then run one capped loop instead of repeating 25-ticker refreshes manually unless you are intentionally doing a tiny targeted check. Large refreshed CSVs are local working data, so review generated changes before committing them.

Provider boundary: price refreshes can improve research-grade local price rows, but they do not create fundamentals, source-backed peers, earnings, analyst estimates, DCF inputs, or research conclusions. Use Data Health and the trusted-data pilot for those lanes.

## Function Quality Checklist

- Readiness gates are the strongest layer; they decide whether deeper analysis is allowed.
- Price and momentum are useful when local price history is present.
- Fundamentals and DCF are useful for DCF-ready companies only.
- Peer comparison waits for source-backed peer mappings and peer metrics.
- Earnings and analyst estimates remain optional context until trusted local rows exist.
- ETF/index/fund reports are monitor context; operating-company DCF is excluded.

See `docs/analysis_capability_audit.md` for the deeper function-quality and provenance explanation.

## What Powers The Analysis

The shipped analysis comes from project code under `src/` plus trusted local CSV inputs. Standard Python libraries support data handling, UI, and tests; optional `yfinance` is only a research-grade adapter.

Support tools and libraries are not the stock-analysis rules. The shipped readiness gates, valuation gates, decision buckets, and research-only guardrails come from project code under `src/` plus trusted local CSV inputs.
