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
make stock-report-md TICKER=MU
make stock-report-md TICKER=META
make stock-report-md TICKER=QQQ
make stock-report-md TICKER=SMH
make stock-report-md TICKER=APLD
make stock-report-md TICKER=CRDO
```

For public demos, prefer `make stock-report-md TICKER=NVDA`. Use `make stock-report TICKER=NVDA` only when you want the optional local report data for inspection.

- `NVDA` demonstrates company-level DCF assumptions and source-backed peer context when trusted local inputs are ready.
- `A` and `MU` demonstrate standalone DCF review where peer-relative valuation is still waiting on source-backed peers.
- `META` demonstrates price/setup review where valuation remains gated until trusted fundamentals and DCF inputs are ready.
- `QQQ` and `SMH` demonstrate ETF/index monitor context where operating-company DCF is excluded, not failed.
- `APLD` and `CRDO` demonstrate partial-data handling where valuation stays blocked instead of being invented; `CRDO` also shows the one-company trusted-data pilot packet path.

Read the visitor scan cue first, then `At A Glance`. Those lines give the mode, decision view, DCF state, peer context, optional context, method cue, and next local step before the detailed tables. Then read `Reader Guide` and `Evaluation Snapshot` to see what evaluation is supported, what valuation boundary applies, the data-confidence cue, the next proof step, and the stop rule. Then read `Proof Checklist` to see what evidence proves the current mode, what readiness proof comes next, and what must stay withheld. Then read `Best Review Path` to see whether to inspect DCF and peers, prove fundamentals readiness, use monitor context, or start with price coverage.

Then read `Analysis Quality`, `Methodology`, and `Evaluation Function Check`. They explain which functions are ready, blocked, excluded, or optional. The At A Glance method cue and the `Methodology` section show the DCF formula path so the valuation workflow is not a black box.

When a ticker is blocked or partial, use the Reader Guide's one-company pilot packet line and then `Copyable Proof Commands`. Those are local research commands to copy when you choose; the report does not run imports or refreshes and does not connect to external accounts.

## Analysis Modes

The dashboard and single-stock report use plain modes before showing detailed tables:

- `DCF-ready review`: company DCF inputs are ready for assumptions, scenarios, and sensitivity review.
- `Standalone DCF review`: company DCF can be reviewed, but peer-relative valuation is still waiting on source-backed peers.
- `Price/setup review only`: local price/setup context is available, but company valuation remains blocked.
- `Monitor-only context`: ETF/index/fund rows can support market, theme, liquidity, or risk monitoring; operating-company DCF is excluded.
- `Data needed before analysis`: the ticker needs trusted local inputs before analysis should be interpreted.

## Data Proof Workflows

Use targeted proof commands instead of broad refreshes by default:

```bash
make price-worklist TOP_N=10
make focus-fundamentals TICKER=NVDA
make peer-mapping-queue TOP_N=10
make optional-context-worklist TOP_N=10
```

For local import files, use preview before apply:

```bash
make templates
make imports-validate IMPORT_TICKERS=<ticker-or-reviewed-batch>
make imports-preview IMPORT_TICKERS=<ticker-or-reviewed-batch>
make imports-apply IMPORT_TICKERS=<ticker-or-reviewed-batch>
```

Broad `make imports-apply` requires `ALLOW_BROAD_IMPORT_APPLY=1` and should only be used after the full staged import scope is intentionally reviewed.

For unattended source-backed refresh planning, use the auto-refresh orchestrator:

```bash
make auto-refresh-plan
make auto-refresh-daily
make auto-refresh-weekly
make auto-refresh-optional
make auto-refresh-runbook
```

The auto-refresh plan is scheduler-ready but still gate-first. Use `make auto-refresh-runbook SCHEDULE=daily`, `SCHEDULE=weekly`, or `SCHEDULE=optional` when you want a compact unattended checklist instead of the full policy dump. `auto_supported` means the deterministic gate passed validation, preview, rejected-row, source-provenance, scope, and no-fabrication checks. `human_reviewed_supported` means a person reviewed the evidence. `candidate_context_only` can route research, especially peer candidates, but it is not trusted proof. Rows that fail a source path should be recorded as `still_blocked`, `skipped`, or `excluded` and the workflow should pivot instead of retrying the same unavailable provider.

Use `make auto-apply-gate` before any unattended apply step. The gate must see valid validation/preview results, zero rejected rows, source provenance, no fabricated values, expected scope, and a batch size within the lane policy. If any condition fails, it returns `still_blocked` and exits nonzero by default so an unsafe `&& make imports-apply` chain stops before applying. Scheduler/report loops that only need to record the blocked outcome and pivot can use `ALLOW_BLOCKED_GATE=1 make auto-apply-gate ...`; do not use that option in the same shell chain as `imports-apply`.

For larger price refreshes, dry-run first and keep batches capped:

```bash
make price-refresh-loop DRY_RUN=1
make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N=100 PROVIDER=auto
make readiness-snapshot
make price-refresh-loop MAX_CANDIDATES=3500 TOP_N=100 PROVIDER=auto SLEEP_SECONDS=30
make diff-hygiene
```

The dry run shows the planned loop command and total capped candidates before local files change. This is the scalable path for broad coverage work; set `MAX_CANDIDATES` to the approximate number of missing-price rows you want to cover, dry-run again, snapshot readiness, then run one capped loop instead of repeating 25-ticker refreshes manually unless you are intentionally doing a tiny targeted check. `PROVIDER=auto` tries Yahoo, Stooq, then configured FMP, Alpha Vantage, and Finnhub price fallbacks when `FMP_API_KEY`, `ALPHA_VANTAGE_API_KEY`, or `FINNHUB_API_KEY` exists. If a provider batch fails, the loop records the source-path outcome, stops retrying that path in the same session, rebuilds proof outputs, and returns control to the coverage workflow. Large refreshed CSVs are local working data, so review generated changes before committing them.

Provider boundary: price refreshes can improve research-grade local price rows, but they do not create fundamentals, source-backed peers, optional context, DCF inputs, or research conclusions. Use Data Health and the trusted-data pilot for those lanes. Optional earnings and analyst-estimate rows can be staged through the optional-context source ladder, but they still stay locked until validation, preview, reviewed apply, and readiness rebuild pass.

For fundamentals and share-count blockers, run the session preflight once before source-backed coverage work:

```bash
make session-source-preflight
make fundamentals-source-ladder-queue TOP_N=10
make imports-validate IMPORT_TICKERS=<ticker-or-reviewed-batch>
make imports-preview IMPORT_TICKERS=<ticker-or-reviewed-batch>
```

The fundamentals source ladder automatically skips providers the current session already marked unavailable. It tries configured source-backed paths in order: SEC, Yahoo/yfinance, FMP, Alpha Vantage, then Finnhub. Reviewed local fundamentals rows stay available, but they are only prioritized when they actually match the current share-count or DCF blockers; otherwise the configured API fallback remains the next executable path. FMP, Alpha Vantage, and Finnhub require `FMP_API_KEY`, `ALPHA_VANTAGE_API_KEY`, or `FINNHUB_API_KEY`; missing keys are recorded as unavailable paths, not filled by inference. Apply staged rows only after validation and preview show the source-backed changes are intended.

For optional earnings and analyst-estimate context, use provider-assisted staging before falling back to manual files:

```bash
make optional-context-source-ladder-queue TOP_N=10
make imports-validate IMPORT_TICKERS=<ticker-or-reviewed-batch>
make imports-preview IMPORT_TICKERS=<ticker-or-reviewed-batch>
make imports-apply IMPORT_TICKERS=<ticker-or-reviewed-batch>
make optional-context-readiness
```

The optional-context source ladder tries yfinance, FMP, Alpha Vantage, then Finnhub when the session and configured keys allow it. Provider rows are research context only and are staged into `data/imports/earnings.csv` and `data/imports/analyst_estimates.csv`; they are not public data freshness proof and do not unlock analysis without the normal import review gates.

To avoid retyping credentials every session, copy `config/provider_keys.env.example` to `config/provider_keys.env` or create `.env` in the project root. The command-line workflows load those local files automatically, while `.gitignore` keeps the real key files out of GitHub. Exported terminal variables still win over local files when both are present. For the provider-by-provider setup boundary, use `docs/SOURCE_ACTIVATION_GUIDE.md`.

## Function Quality Checklist

- Readiness gates are the strongest layer; they decide whether deeper analysis is allowed.
- Price and momentum are useful when local price history is present.
- Fundamentals and DCF are useful for DCF-ready companies only.
- Peer comparison waits for source-backed peer mappings and peer metrics.
- Earnings and analyst estimates remain optional context until trusted local or reviewed provider-assisted rows pass the import gates.
- ETF/index/fund reports are monitor context; operating-company DCF is excluded.

See `docs/analysis_capability_audit.md` for the deeper function-quality and provenance explanation.

## What Powers The Analysis

The shipped analysis comes from project code under `src/` plus trusted local CSV inputs. Standard Python libraries support data handling, UI, and tests; optional `yfinance` is only a research-grade adapter.

Support tools and libraries are not the stock-analysis rules. The shipped readiness gates, valuation gates, decision buckets, and research-only guardrails come from project code under `src/` plus trusted local CSV inputs.
