# Public Demo Readiness Pack

This pack is research-only. It shows readiness states, blocked inputs, and proof commands; it is not investment advice and it does not connect to brokers or route orders.

Start with the product flow before opening operator proof commands:

```text
Home -> Stock Selector -> Single-Stock Report -> Data Health -> Proof History
```

Use the table below as evidence after the visitor can already explain what is ready, what is blocked, what is excluded, and what proof changed a lane. Status, provider setup, and proof-ledger commands are operator evidence; they do not refresh data, unlock blocked inputs, or replace the public workflow.

## Shareable Proof Set

| Slot | Artifact / command | What it proves |
| --- | --- | --- |
| Visitor workflow | `make dashboard` then follow Home -> Stock Selector -> Single-Stock Report -> Data Health -> Proof History | First-screen product path and readiness-first route sequence. |
| Status gate | `make project-status-check` | Current safest proof path, provider setup boundary, and whether company candidates are executable. |
| Provider setup | `make provider-setup-checklist` | Source setup steps when source-proof queues are exhausted; no imports or generated data are applied. |
| Scope selection | `make universe-scope TOP_N=10` | Choose active-universe, ticker-list, sector/theme, ready-only, or missing-data scope before deeper review. |
| Risk context | `make risk-context` | Read-only liquidity, correlation, and proxy-risk context after scope is chosen. |
| Data Health lane board | `make readiness-ops-center`, `make coverage-frontier TOP_N=10`, or dashboard `Data Health` | Lane counts, blocker themes, next safe commands, and locked/manual lanes. |
| Ready report | `make stock-report-md TICKER=NVDA` | Ready company report with local DCF review and source-readiness boundaries. |
| Blocked report | `make stock-report-md TICKER=META` | Blocked/missing-input report that keeps valuation gated. |
| Excluded / monitor example | `make stock-report-md TICKER=QQQ` | ETF/index monitor context where operating-company DCF is excluded, not failed. |

## Current proof timeline

Latest reviewed proof: run `make reviewed-data-proof` for the current ledger row.

Use `make reviewed-data-proof` to show the latest durable lane-level proof rows.
Use `make reviewed-batch-proof` to show the latest reviewed batch outcomes.
Use `make lane-outcome-history` when you need the lane-level outcome history.

This proof review does not refresh data, apply imports, stage files, or unlock blocked inputs. It keeps proof history separate from broad generated CSV churn and from browser screenshots, which remain product evidence only.

## Source-boundary pivot

If `make project-status-check` says current source-proof queues are exhausted, use `make provider-setup-checklist` before reopening broad proof loops. Configure at most one keyed free-tier provider, run that provider's reviewed one-ticker smoke command, then use validate, preview, rejected-row review, and source-provenance checks before any apply step.
