# Pilot Readiness Packet

> Data readiness first. Analysis second. Research decision last.

This packet is a read-only reviewer summary. It does not refresh data, apply imports, record proof, stage files, commit, push, connect to brokers, route orders, auto-trade, or provide direct buy/sell instructions.

## Verdict: pilot-ready with manual gates

- Gate counts: green: 3, manual: 4, blocked: 0.
- Manual gates still required: 4.
- Blocked gates: 0.
- Blocked source inputs remain blocked until trusted source proof and review gates pass.

## Readiness Snapshot

| Metric | Current saved value |
| --- | --- |
| Tracked tickers | 3538 |
| Price-ready | 3538/3538 |
| Momentum usable | 3529/3538 |
| DCF-ready | 59/3538 |
| Peer-ready | 26/3538 |
| Data sources available | 5/10 |
| Optional/manual lanes locked | 5 |
| Missing-data steps | 14077 |
| Urgent missing-data steps | 11 |

## Pilot Gates

| Area | Status | Gate | Detail | Command |
| --- | --- | --- | --- | --- |
| GitHub sync | manual | GitHub branch state | ## main...origin/main [ahead 2]; reviewed local commits still need a push before the GitHub pilot link is current. | git push origin main |
| Generated artifact hygiene | manual | Dirty tree classification | 1 reviewed pilot packet artifact(s) pending; 25 generated CSV/JSON/report artifact(s) are dirty and excluded by default. | make diff-hygiene-summary |
| Readiness freshness | green | Readiness artifacts are current | Readiness artifacts are current relative to watched source files. | make status-check TOP_N=5 |
| Source proof gates | manual | DCF Input Proof Batches leads the source-review queue | 13,911 blocked and 47 partial proof item(s) remain across DCF inputs, trusted fundamentals, share count, peer mapping, and peer valuation inputs. That is acceptable for pilot review only if missing inputs stay visible. | make data-coverage-proof-queues TOP_N=10 |
| Proof ledger | green | 7 reviewed batch proof row(s) | Latest outcome: supported; lane: prices; batch: RB-PRICE-COVERAGE-20260614. | make reviewed-batch-proof |
| Public safety | manual | Run the public share gate before pilot sharing | The pilot checklist is read-only; public-check remains the explicit test, wording, dashboard smoke, and visitor-demo gate. | make public-check |
| Research guardrails | green | Research-only boundary remains required | Pilot surfaces must stay readiness-first and must not include broker integration, order routing, auto-trading, direct buy/sell instructions, fabricated inputs, or recommendations. | make public-wording-check |

## Source-Proof Queue Summary

| Queue | State | Ready | Partial | Blocked | Top blockers | Next safest command |
| --- | --- | --- | --- | --- | --- | --- |
| DCF Input Proof Batches | partial | 59 | 21 | 3458 | fundamentals_bundle_plus_shares: 3459, fundamentals_bundle: 12, shares_outstanding: 5, fcf_margin: 1 | make dcf-input-proof-queue TOP_N=10 |
| Shares Outstanding Proof | partial | 74 | 5 | 3464 | shares_outstanding: 3464; share-count-only blockers: 5 | make share-count-proof-queue TOP_N=10 |
| Trusted Fundamentals Proof Queue | partial | 59 | 21 | 3458 | fundamentals_bundle_plus_shares: 3459, fundamentals_bundle: 12, fcf_margin: 1 | make dcf-input-source-command-plan FAMILY=fundamentals_bundle_plus_shares TOP_N=10 |
| Peer Mapping Proof Queue | partial | 26 | 0 | 3512 | source-backed peer mappings: 3512 | DRY_RUN=1 make peer-mapping-source-review TOP_N=10 |
| Peer Valuation Input Proof Queue | partial | 7 | 0 | 19 | peer prices: 0; peer fundamentals: 19; mapped-peer valuation blockers: 0 | make peer-mapping-queue TOP_N=25 |

## Latest Reviewed Batch Proof

- RB-PRICE-COVERAGE-20260614 / prices / supported / Capped Yahoo price refresh only; research-grade price rows; no fundamentals/earnings/estimates/recommendations/broker actions unlocked

## Manual Gates Still Required

- GitHub sync: Do not push if unreviewed product changes or generated churn are staged.
- Generated artifact hygiene: Do not stage broad generated churn unless those exact artifacts are reviewed pilot evidence.
- Source proof gates: Do not call a lane supported until source proof, validate, preview, rejected-row review, apply/skip decision, rebuilt readiness, and proof record pass.
- Public safety: Stop before public pilot sharing if public-check, public wording, dashboard smoke, or whitespace checks fail.

## Stop Rules

- GitHub sync: Do not push if unreviewed product changes or generated churn are staged.
- Generated artifact hygiene: Do not stage broad generated churn unless those exact artifacts are reviewed pilot evidence.
- Readiness freshness: Stop before quoting final counts or proof deltas if readiness artifacts are stale or missing.
- Source proof gates: Do not call a lane supported until source proof, validate, preview, rejected-row review, apply/skip decision, rebuilt readiness, and proof record pass.
- Proof ledger: Do not record supported outcomes without reviewed proof-row fields and generated-artifact review.
- Public safety: Stop before public pilot sharing if public-check, public wording, dashboard smoke, or whitespace checks fail.
- Research guardrails: Stop if any public or dashboard wording turns readiness queues into advice or trade instructions.

## Exact Next Safest Commands

- `git push origin main`
- `make diff-hygiene-summary`
- `make status-check TOP_N=5`
- `make data-coverage-proof-queues TOP_N=10`
- `make reviewed-batch-proof`
- `make public-check`
- `make public-wording-check`

## Generated Artifacts Excluded From Staging

- `data/analyst_estimates_readiness.csv`
- `data/dcf_readiness.csv`
- `data/earnings_readiness.csv`
- `data/fundamentals.csv`
- `data/price_coverage_report.csv`
- `data/prices.csv`
- `data/reports/analyst_estimates_readiness_report.csv`
- `data/reports/data_source_status.csv`
- `data/reports/dcf_readiness_report.csv`
- `data/reports/earnings_readiness_report.csv`
- `data/reports/feature_readiness_summary.csv`
- `data/reports/fundamentals_coverage_report.csv`
- `data/reports/peer_readiness_report.csv`
- `data/reports/peer_unlock_worklist.csv`
- `data/reports/price_coverage_report.csv`
- `data/reports/ticker_readiness_report.csv`
- `data/reports/universe_coverage_report.csv`
- `outputs/correlation_risk.csv`
- `outputs/data_quality_wizard.csv`
- `outputs/feature_readiness_summary.csv`
- `outputs/liquidity_risk.csv`
- `outputs/peer_unlock_worklist.csv`
- `outputs/purpose_evaluation_summary.csv`
- `outputs/research_action_queue.csv`
- `data/reports/ticker_readiness_report.previous.csv`

## Research-Only Guardrails

- This is research software, not investment advice.
- No broker integration, order routing, auto-trading, options recommendations, or direct buy/sell instructions.
- Do not fabricate prices, fundamentals, shares, market cap, peers, earnings, estimates, valuation inputs, metrics, or recommendations.
- Preserve ready, partial, blocked, excluded, supported, still_blocked, and skipped states.
- Keep broad generated CSV/JSON/report churn out of commits unless a specific artifact is intentionally reviewed evidence.
