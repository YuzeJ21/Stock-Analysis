# Public Demo Readiness Pack

This pack is research-only. It shows readiness states, blocked inputs, and proof commands; it is not investment advice and it does not connect to brokers or route orders.

## Shareable Proof Set

| Slot | Artifact / command | What it proves |
| --- | --- | --- |
| Home | `make dashboard` then open Home | First-screen coverage snapshot and visitor routes. |
| Data Health lane board | `make readiness-ops-center`, `make coverage-frontier TOP_N=10`, or dashboard `Data Health` | Lane counts, blocker themes, next safe commands, and locked/manual lanes. |
| Ready report | `make stock-report-md TICKER=NVDA` | Ready company report with local DCF review and source-readiness boundaries. |
| Blocked report | `make stock-report-md TICKER=META` | Blocked/missing-input report that keeps valuation gated. |
| Excluded / monitor example | `make stock-report-md TICKER=QQQ` | ETF/index monitor context where operating-company DCF is excluded, not failed. |

## Latest Proof Timeline

Latest reviewed proof: `RDP-2026-06-12-001` on `2026-06-12` for `Peer valuation inputs proof path` ended `still_blocked`.

Use `make reviewed-data-proof`, `make lane-outcome-history`, and `make reviewed-batch LANE=prices TOP_N=10` to show durable proof and batch-planning artifacts without relying on broad generated CSV churn.
