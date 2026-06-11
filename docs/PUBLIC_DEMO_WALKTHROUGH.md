# Public Demo Walkthrough

Use this when sharing the project from GitHub or LinkedIn. The walkthrough is read-only until you intentionally run local report commands, and it does not refresh broad data or import trusted rows.

## One-Minute Story

This project is a local research command center. It checks data readiness before analysis, shows what can be reviewed now, and keeps missing or non-applicable analysis visibly locked or excluded.

Best visitor path:

1. Open the README and dashboard preview.
2. Run `make demo` to print the safe walkthrough.
3. Run `make status-check TOP_N=5` to show current coverage and blockers.
4. Open `outputs/stock_reports/nvda.md` for a DCF-ready company example.
5. Open `outputs/stock_reports/mu.md` for standalone DCF with mapped-peer valuation inputs still locked.
6. Open `outputs/stock_reports/qqq.md` for ETF/index monitor context where operating-company DCF is excluded.
7. Run `make trusted-data-pilot-candidates TOP_N=10` to show the next honest coverage-improvement path.

## Demo Examples

| Example | What it proves | Good line to point out |
| --- | --- | --- |
| `NVDA` | Ready company review. | DCF assumptions and source readiness appear because inputs passed readiness. |
| `MU` | Standalone DCF, peer valuation still locked. | Mapped-peer price/fundamental inputs are required before peer-relative valuation appears. |
| `META` | Price/setup review with valuation gated. | Missing fundamentals keep valuation locked instead of inferred. |
| `QQQ` / `SMH` | ETF/index or sector monitor context. | Operating-company DCF is excluded, not failed. |
| `CRDO` / `APLD` | Blocked company examples. | The report shows the next trusted-data proof step instead of fabricating inputs. |

## Local Commands

```bash
make demo
make status-check TOP_N=5
make stock-report-md TICKER=NVDA
make stock-report-md TICKER=MU
make stock-report-md TICKER=QQQ
make trusted-data-pilot-candidates TOP_N=10
make dashboard
```

## What To Say About Data Gaps

The current sample is intentionally partial. Prices can be refreshed through capped preview-first workflows. Fundamentals, peer inputs, earnings, and analyst estimates require trusted source review before they can unlock deeper analysis.

Missing data is not a product failure here. It is the product's quality control layer.

When improving real coverage, snapshot the baseline, review source proof, validate/preview and check rejected rows, rebuild readiness and the stock report, then compare the after report. If source proof is unavailable, leave the section blocked and move to the next candidate.

Read the outcome in three states: `Supported` means rebuilt readiness and the regenerated report show the lane is ready; `Still blocked` means validation failed, rejected rows appeared, or the report stayed locked; `Skip` means source proof is unavailable, so no placeholder rows are applied.

## What Not To Claim

- Do not call this investment advice.
- Do not describe the output as a buy/sell system.
- Do not imply broad fundamentals, peer valuation, earnings, or estimates are complete.
- Do not claim blocked sections are negative company signals.
- Do not say the app places orders, has broker integration, or automates execution.

## Strongest Public Message

The project is useful because it refuses to overclaim. It can analyze ready data, explain blocked data, exclude methods that do not fit, and show the exact local proof step required to unlock the next research layer.
