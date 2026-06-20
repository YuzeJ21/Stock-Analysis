# Pilot Readiness Packet

> Data readiness first. Analysis second. Research decision last.

This packet is a read-only reviewer summary. It does not refresh data, apply imports, record proof, stage files, commit, push, connect to brokers, route orders, auto-trade, or provide direct buy/sell instructions.

## Verdict: blocked

- Gate counts: green: 4, manual: 3, blocked: 1.
- Manual gates still required: 3.
- Blocked gates: 1.
- Blocked source inputs remain blocked until trusted source proof and review gates pass.

## Reviewer Handoff Summary

| Question | Status | Answer | Next safe command | Boundary |
| --- | --- | --- | --- | --- |
| Can this be shared as a pilot? | blocked | blocked | make diff-hygiene-summary | Pilot readiness is a packaging gate, not an analysis or recommendation unlock. |
| What must be reviewed first? | blocked | Generated artifact hygiene | make diff-hygiene-summary | Stop before pilot packaging until product files are staged/committed or intentionally left local. |
| What blocks deeper analysis? | partial | DCF Input Proof Batches | make dcf-input-proof-queue TOP_N=10 | 3,458 blocked item(s); top blockers: fundamentals_bundle_plus_shares: 3459, fundamentals_bundle: 12, shares_outstanding: 5, fcf_margin: 1 |
| What stays out of staging? | manual | 25 generated artifact(s) excluded by default | make diff-hygiene-summary | Keep these broad generated patterns out by default: data/*.csv; data/reports/*.csv; outputs/*.csv; data/reports/ticker_readiness_report.previous.csv. Stage only a specific artifact if it is intentionally reviewed evidence. |
| What should the reviewer run next? | copy-only | outputs/pilot_readiness_packet.md | make pilot-readiness-packet OUTPUT=outputs/pilot_readiness_packet.md | The packet is read-only; it does not refresh data, apply imports, record proof, stage files, commit, or push. |

## Commit Package Handoff

| Step | Status | Copy-only command | Boundary |
| --- | --- | --- | --- |
| Stage reviewed product package | ready_to_stage | git add -- docs/DASHBOARD_QA.md src/browser_qa_evidence.py src/dashboard.py src/readiness_queue_dashboard.py tests/test_browser_qa_evidence.py tests/test_dashboard_helpers.py tests/test_readiness_queue_dashboard.py | 7 product/code/docs/test or reviewed Markdown file(s) are eligible for staging. Review the diff first; do not use git add -A. |
| Verify staged package | copy-only | make staged-hygiene-check && git diff --cached --check | Stop if staged hygiene shows generated CSV/JSON churn or manual-review paths. |
| Commit reviewed package | copy-only | git commit -m "Package reviewed product changes" | Commit only after tests, public wording, and staged hygiene pass. |
| Keep generated churn out | excluded | make diff-hygiene-summary | 25 generated CSV/JSON/report artifact(s) remain excluded by default. Keep these patterns out by default: data/*.csv; data/reports/*.csv; outputs/*.csv; data/reports/ticker_readiness_report.previous.csv. Stage only a specific reviewed evidence artifact if intentionally selected. |

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
| GitHub sync | green | GitHub branch state | ## main...origin/main; local branch is not ahead of the tracked remote. | git status --short --branch |
| Generated artifact hygiene | blocked | Dirty tree classification | 7 product/code/docs/test file(s), 0 sample report(s), and 0 manual-review path(s) are dirty. | make diff-hygiene-summary |
| Readiness freshness | green | Readiness artifacts are current | Readiness artifacts are current relative to watched source files. | make status-check TOP_N=5 |
| Source proof gates | manual | DCF Input Proof Batches leads the source-review queue | 13,911 blocked and 47 partial proof item(s) remain across DCF inputs, trusted fundamentals, share count, peer mapping, and peer valuation inputs. That is acceptable for pilot review only if missing inputs stay visible. | make data-coverage-proof-queues TOP_N=10 |
| Proof ledger | green | 7 reviewed batch proof row(s) | Latest outcome: supported; lane: prices; batch: RB-PRICE-COVERAGE-20260614. | make reviewed-batch-proof |
| Browser QA evidence | manual | Public screenshot ready; workflow captures pending | 3 committed screenshot asset(s) ready; pending workflow capture(s): Single-stock workflow fit screenshot, Data Health proof lane screenshot, Data Health queue drawer routing screenshot. Screenshots are product evidence only and do not refresh data or unlock blocked inputs. Reviewed asset staging command is available from browser QA JSON and capture plan after visual review. | make browser-qa-evidence |
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

- Source proof gates: Do not call a lane supported until source proof, validate, preview, rejected-row review, apply/skip decision, rebuilt readiness, and proof record pass.
- Browser QA evidence: Use committed real public screenshots now; capture pending workflow views in a normal browser before claiming full workflow evidence.
- Public safety: Stop before public pilot sharing if public-check, public wording, dashboard smoke, or whitespace checks fail.

## Stop Rules

- GitHub sync: Stop if a later status check shows unreviewed commits or divergence.
- Generated artifact hygiene: Stop before pilot packaging until product files are staged/committed or intentionally left local.
- Readiness freshness: Stop before quoting final counts or proof deltas if readiness artifacts are stale or missing.
- Source proof gates: Do not call a lane supported until source proof, validate, preview, rejected-row review, apply/skip decision, rebuilt readiness, and proof record pass.
- Proof ledger: Do not record supported outcomes without reviewed proof-row fields and generated-artifact review.
- Browser QA evidence: Use committed real public screenshots now; capture pending workflow views in a normal browser before claiming full workflow evidence.
- Public safety: Stop before public pilot sharing if public-check, public wording, dashboard smoke, or whitespace checks fail.
- Research guardrails: Stop if any public or dashboard wording turns readiness queues into advice or trade instructions.

## Exact Next Safest Commands

- `git status --short --branch`
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
