# Public Demo Readiness Pack

This pack is research-only. It shows readiness states, blocked inputs, and proof commands; it is not investment advice and it does not connect to brokers or route orders.

## Shareable Proof Set

| Slot | Artifact / command | What it proves |
| --- | --- | --- |
| Home | `make dashboard` then open Home | First-screen coverage snapshot and visitor routes. |
| Status gate | `make project-status` | Current safest proof path, provider setup boundary, and whether company candidates are executable. |
| Provider setup | `make provider-setup-checklist` | Source setup steps when source-proof queues are exhausted; no imports or generated data are applied. |
| Data Health lane board | `make readiness-ops-center`, `make coverage-frontier TOP_N=10`, or dashboard `Data Health` | Lane counts, blocker themes, next safe commands, and locked/manual lanes. |
| Ready report | `make stock-report-md TICKER=NVDA` | Ready company report with local DCF review and source-readiness boundaries. |
| Blocked report | `make stock-report-md TICKER=META` | Blocked/missing-input report that keeps valuation gated. |
| Excluded / monitor example | `make stock-report-md TICKER=QQQ` | ETF/index monitor context where operating-company DCF is excluded, not failed. |

## Current proof timeline

Use `make reviewed-data-proof` to show the latest durable lane-level proof rows.
Use `make reviewed-batch-proof` to show the latest reviewed batch outcomes.
Use `make lane-outcome-history` when you need the lane-level outcome history.

This proof review does not refresh data, apply imports, stage files, or unlock blocked inputs. It keeps proof history separate from broad generated CSV churn and from browser screenshots, which remain product evidence only.

## Source-boundary pivot

If `make project-status` says current source-proof queues are exhausted, use `make provider-setup-checklist` before reopening broad proof loops. Configure at most one keyed free-tier provider, run that provider's one-ticker smoke command, then use validate, preview, rejected-row review, and source-provenance checks before any apply step.
