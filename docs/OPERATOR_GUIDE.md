# Operator Guide

Use this guide when you want to run the command center locally after reading the short README.

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
make stock-report TICKER=NVDA
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
- Open `Single-Stock Report` for one ticker when you want the clearest stock-level explanation.
- Open `Data Health` when the app says analysis is blocked by missing local data.

## Single-Stock Demo Path

These examples show the main states without needing a full-market refresh:

```bash
make stock-report TICKER=NVDA
make stock-report TICKER=QQQ
make stock-report TICKER=SMH
make stock-report TICKER=APLD
```

- `NVDA` demonstrates company-level DCF assumptions when trusted local inputs are ready enough.
- `QQQ` and `SMH` demonstrate ETF/index monitor context where operating-company DCF is excluded, not failed.
- `APLD` demonstrates partial-data handling where valuation stays blocked instead of being invented.

Read the `Analysis Quality` and `Evaluation Function Check` sections first. They explain which functions are ready, blocked, excluded, or optional before the detailed tables.

## Data Unlock Workflows

Use targeted unlock commands instead of broad refreshes by default:

```bash
make price-worklist TOP_N=10
make focus-fundamentals TICKER=NVDA
make peer-mapping-queue TOP_N=10
make optional-context-worklist TOP_N=10
```

For staged local imports, use preview before apply:

```bash
make templates
make imports-validate
make imports-preview
make imports-apply
```

For larger price refreshes, dry-run first and keep batches capped:

```bash
make price-refresh-loop DRY_RUN=1
make price-refresh-loop BATCHES=5 TOP_N=100 PROVIDER=yahoo SLEEP_SECONDS=30
```

Large refreshed CSVs are local working data. Review generated changes before committing them.

## Function Quality Checklist

- Readiness gates are the strongest layer; they decide whether deeper analysis is allowed.
- Price and momentum are useful when local price history is present.
- Fundamentals and DCF are useful for DCF-ready companies only.
- Peer comparison waits for source-backed peer mappings and peer metrics.
- Earnings and analyst estimates remain optional context until trusted local rows exist.
- ETF/index/fund reports are monitor context; operating-company DCF is excluded.

See `docs/analysis_capability_audit.md` for the deeper function-quality and provenance explanation.

## What Powers The Analysis

The shipped analysis comes from repo code under `src/` plus trusted local CSV inputs. Standard Python libraries support data handling, UI, and tests; optional `yfinance` is only a research-grade adapter.

Codex plugins or skills, including Public Equity Investing and Investment Banking, are development aids only. They are not runtime dependencies, hidden recommendation systems, copied stock-analysis skills, or broker integrations.
