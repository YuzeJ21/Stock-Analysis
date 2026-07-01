# Public Demo Walkthrough

Use this when sharing the project from GitHub or LinkedIn. The walkthrough is read-only until you intentionally run local report commands, and it does not refresh broad data or import trusted rows.

## One-Minute Story

This project is a local research command center. It checks data readiness before analysis, shows what can be reviewed now, and keeps missing or non-applicable analysis visibly locked or excluded.

Best visitor path:

1. Open the README and dashboard preview.
2. Run `make demo` to print the safe walkthrough.
3. Run `make dashboard` and open `http://localhost:8501/?mode=public` for the clean visitor view.
4. Open Stock Selector at `?mode=public&page=stock-selector` to show the readiness-backed queue before one-ticker analysis.
5. Open `?mode=public&page=single-stock-report&ticker=NVDA&open=1` for a DCF-ready company example.
6. Open Data Health at `?mode=public&page=data-health` when a selector row or report section is blocked by source data.
7. Check Proof History at `?mode=public&page=proof-history` before trusting changed readiness.
8. Run `make status-check TOP_N=5` only when you want terminal proof of current coverage and blockers.
9. Open `outputs/stock_reports/mu.md` for standalone DCF with mapped-peer valuation inputs still locked.
10. Open `outputs/stock_reports/qqq.md` for ETF/index monitor context where operating-company DCF is excluded.
11. Run `make project-status`, then `make data-coverage-proof-queues TOP_N=10`, to show the current honest coverage-improvement path.
12. Run `make trusted-data-pilot-candidates TOP_N=10` only when project status shows executable company candidates; if the shortlist starts with peer inputs, open `make trusted-data-pilot-packet TICKER=MU`; for fundamentals/DCF proof, open `make trusted-data-pilot-packet TICKER=CRDO`.

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
make project-status
make data-coverage-proof-queues TOP_N=10
make trusted-data-pilot-candidates TOP_N=10
make trusted-data-pilot-packet TICKER=MU
make trusted-data-pilot-packet TICKER=CRDO
make dashboard
```

The dashboard defaults to Public visitor mode. The first path is the real workflow: Home readiness snapshot -> Stock Selector -> Single-Stock Report -> Data Health source-proof lane -> Proof History. Stock Selector is the public stock-selection surface; Single-Stock Report stays one ticker at a time; Data Health explains blocked source inputs; Proof History records source-proof changes before a changed state is trusted. Switch Public visitor mode off in the sidebar only when you want operator boards, detailed proof tables, coverage frontier workflows, or validate / preview / apply guidance.

## What To Say About Data Gaps

The current sample is intentionally partial. Prices can be refreshed through capped preview-first workflows. Fundamentals, peer inputs, earnings, and analyst estimates require trusted source review before they can unlock deeper analysis.

Missing data is not a product failure here. It is the product's quality control layer.

Pilot packets are still read-only. Local file presence, row counts, staged files, and rejected-row reports are inspection cues, not proof that a lane is ready.

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
