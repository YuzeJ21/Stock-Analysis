# Pilot Readiness Packet

> Data readiness first. Analysis second. Research decision last.

This packet is a read-only reviewer summary. It does not refresh data, apply imports, record proof, stage files, commit, push, connect to brokers, route orders, auto-trade, or provide direct buy/sell instructions.

## Verdict: pilot-ready with manual gates

- Gate counts: green: 4, manual: 4, blocked: 0.
- Manual gates still required: 4.
- Blocked gates: 0.
- Blocked source inputs remain blocked until trusted source proof and review gates pass.

## Reviewer Handoff Summary

| Question | Status | Answer | Next safe command | Boundary |
| --- | --- | --- | --- | --- |
| Can this be shared as a pilot? | manual | pilot-ready with manual gates | make diff-hygiene-summary | Pilot readiness is a packaging gate, not an analysis or recommendation unlock. |
| What must be reviewed first? | manual | Generated artifact hygiene | make diff-hygiene-summary | Do not stage broad generated stock reports or broad generated churn unless those exact artifacts are reviewed pilot evidence. |
| What blocks deeper analysis? | partial | DCF Input Proof Batches | make dcf-input-proof-queue TOP_N=10 | 90 blocked item(s); top blockers: fundamentals_bundle: 242, fundamentals_bundle_plus_shares: 91 |
| What stays out of staging? | manual | 35 generated artifact(s) excluded by default | make diff-hygiene-summary | Keep these broad generated patterns out by default: data/*.csv; data/reports/*.csv; outputs/*.csv; data/reports/ticker_readiness_report.previous.csv. Stage only a specific artifact if it is intentionally reviewed evidence. |
| What should the reviewer run next? | copy-only | outputs/pilot_readiness_packet.md | make pilot-readiness-packet OUTPUT=outputs/pilot_readiness_packet.md | The packet is read-only; it does not refresh data, apply imports, record proof, stage files, commit, or push. |

## Commit Package Handoff

| Step | Status | Copy-only command | Boundary |
| --- | --- | --- | --- |
| Stage reviewed product package | no_product_changes | # no product/code/docs/test files to stage | 0 product/code/docs/test file(s) are eligible for staging. 2876 sample report artifact(s) stay excluded unless individually reviewed. Review the diff first; do not use git add -A. |
| Verify staged package | copy-only | make staged-hygiene-check && git diff --cached --check | Stop if staged hygiene shows generated CSV/JSON churn or manual-review paths. |
| Commit reviewed package | copy-only | # no reviewed product package to commit | Do not create a release commit just for excluded generated churn. |
| Keep generated churn out | excluded | make diff-hygiene-summary | 35 generated CSV/JSON/report artifact(s) and 2876 broad generated stock report artifact(s) remain excluded by default. Keep these patterns out by default: data/*.csv; data/reports/*.csv; outputs/*.csv; data/reports/ticker_readiness_report.previous.csv. Stage only a specific reviewed evidence artifact if intentionally selected. |

## Readiness Snapshot

| Metric | Current saved value |
| --- | --- |
| Tracked tickers | 3538 |
| Price-ready | 3537/3538 |
| Momentum usable | 3535/3538 |
| DCF-ready | 2691/3538 |
| Peer-ready | 29/3538 |
| Data sources available | 7/10 |
| Optional/manual lanes locked | 3 |
| Missing-data steps | 0 |
| Urgent missing-data steps | 0 |

## Pilot Gates

| Area | Status | Gate | Detail | Command |
| --- | --- | --- | --- | --- |
| GitHub sync | manual | GitHub branch state | ## main...origin/main [ahead 103]; reviewed local commits still need a push before the GitHub pilot link is current. | git push origin main |
| Generated artifact hygiene | manual | Dirty tree classification | 2876 broad sample report artifact(s) pending review; 35 generated CSV/JSON/report artifact(s) are dirty and excluded by default. | make diff-hygiene-summary |
| Readiness freshness | green | Readiness artifacts are current | Readiness artifacts are current relative to watched source files. | make status-check TOP_N=5 |
| Source proof gates | manual | DCF Input Proof Batches leads the source-review queue | 3,778 blocked and 486 partial proof item(s) remain across DCF inputs, trusted fundamentals, share count, peer mapping, and peer valuation inputs. That is acceptable for pilot review only if missing inputs stay visible. | make data-coverage-proof-queues TOP_N=10 |
| Proof ledger | green | 1151 reviewed batch proof row(s) | Latest outcome: candidate_context_only; lane: optional_context; batch: RB-20260701-OPTIONAL-YF-CONTEXT-NOAPPLY-002. | make reviewed-batch-proof |
| Browser QA evidence | green | Real screenshot evidence is ready | 3 committed screenshot asset(s) ready; pending workflow capture(s): none. Screenshots are product evidence only and do not refresh data or unlock blocked inputs. Reviewed asset staging command is available from browser QA JSON and capture plan after visual review. | make browser-qa-evidence |
| Public safety | manual | Run the public share gate before pilot sharing | The pilot checklist is read-only; public-check remains the explicit test, wording, dashboard smoke, and visitor-demo gate. | make public-check |
| Research guardrails | green | Research-only boundary remains required | Pilot surfaces must stay readiness-first and must not include broker integration, order routing, auto-trading, direct buy/sell instructions, fabricated inputs, or recommendations. | make public-wording-check |

## Source-Proof Queue Summary

| Queue | State | Ready | Partial | Blocked | Top blockers | Next safest command |
| --- | --- | --- | --- | --- | --- | --- |
| DCF Input Proof Batches | partial | 2691 | 243 | 90 | fundamentals_bundle: 242, fundamentals_bundle_plus_shares: 91 | make dcf-input-proof-queue TOP_N=10 |
| Shares Outstanding Proof | partial | 3447 | 0 | 91 | shares_outstanding: 91; share-count-only blockers: 0 | make share-count-proof-queue TOP_N=10 |
| Trusted Fundamentals Proof Queue | partial | 2691 | 243 | 90 | fundamentals_bundle: 242, fundamentals_bundle_plus_shares: 91 | make dcf-input-source-command-plan FAMILY=fundamentals_bundle TOP_N=10 |
| Peer Mapping Proof Queue | partial | 29 | 0 | 3507 | source-backed peer mappings: 3507 | DRY_RUN=1 make peer-mapping-source-review TOP_N=10 |
| Peer Valuation Input Proof Queue | ready | 29 | 0 | 0 | peer prices: 0; peer fundamentals: 0; mapped-peer valuation blockers: 0 | make peer-mapping-queue TOP_N=25 |

## Latest Reviewed Batch Proof

- RB-20260701-OPTIONAL-YF-CONTEXT-NOAPPLY-002 / optional_context / candidate_context_only / yfinance source-backed optional context can route research only. Earnings rows contain next_earnings_date without EPS/revenue actuals or estimates; analyst rows contain price-target context only. No recommendations, no readiness unlock.

## Manual Gates Still Required

- GitHub sync: Do not push if unreviewed product changes or generated churn are staged.
- Generated artifact hygiene: Do not stage broad generated stock reports or broad generated churn unless those exact artifacts are reviewed pilot evidence.
- Source proof gates: Do not call a lane supported until source proof, validate, preview, rejected-row review, apply/skip decision, rebuilt readiness, and proof record pass.
- Public safety: Stop before public pilot sharing if public-check, public wording, dashboard smoke, or whitespace checks fail.

## Stop Rules

- GitHub sync: Do not push if unreviewed product changes or generated churn are staged.
- Generated artifact hygiene: Do not stage broad generated stock reports or broad generated churn unless those exact artifacts are reviewed pilot evidence.
- Readiness freshness: Stop before quoting final counts or proof deltas if readiness artifacts are stale or missing.
- Source proof gates: Do not call a lane supported until source proof, validate, preview, rejected-row review, apply/skip decision, rebuilt readiness, and proof record pass.
- Proof ledger: Do not record supported outcomes without reviewed proof-row fields and generated-artifact review.
- Browser QA evidence: Stop if later screenshots are generated thumbnails, tracebacks, or stale proof substitutes.
- Public safety: Stop before public pilot sharing if public-check, public wording, dashboard smoke, or whitespace checks fail.
- Research guardrails: Stop if any public or dashboard wording turns readiness queues into advice or trade instructions.

## Exact Next Safest Commands

- `git push origin main`
- `make diff-hygiene-summary`
- `make status-check TOP_N=5`
- `make data-coverage-proof-queues TOP_N=10`
- `make reviewed-batch-proof`
- `make browser-qa-evidence`
- `make public-check`
- `make public-wording-check`

## Generated Artifacts Excluded From Staging

Default broad exclusion patterns:
- `data/*.csv`
- `data/reports/*.csv`
- `outputs/*.csv`
- `data/reports/ticker_readiness_report.previous.csv`

Currently dirty generated artifacts:
- `data/analyst_estimates_readiness.csv`
- `data/dcf_readiness.csv`
- `data/earnings_readiness.csv`
- `data/fundamentals.csv`
- `data/outputs/research_decisions.csv`
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
- `outputs/final_watchlist.csv`
- `outputs/liquidity_risk.csv`
- `outputs/market_direction.csv`
- `outputs/momentum_leaders.csv`
- `outputs/peer_unlock_worklist.csv`
- `outputs/purpose_classification.csv`
- `outputs/purpose_evaluation_summary.csv`
- `outputs/research_action_queue.csv`
- `outputs/research_decisions.csv`
- `outputs/undervalued_candidates.csv`
- `data/analyst_estimates.csv`
- `data/earnings.csv`
- `data/reports/ticker_readiness_report.previous.csv`
- `outputs/session_source_preflight.json`

## Research-Only Guardrails

- This is research software, not investment advice.
- No broker integration, order routing, auto-trading, options recommendations, or direct buy/sell instructions.
- Do not fabricate prices, fundamentals, shares, market cap, peers, earnings, estimates, valuation inputs, metrics, or recommendations.
- Preserve ready, partial, blocked, excluded, supported, still_blocked, and skipped states.
- Keep broad generated CSV/JSON/report churn out of commits unless a specific artifact is intentionally reviewed evidence.
