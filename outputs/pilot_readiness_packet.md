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
| What must be reviewed first? | manual | Generated artifact hygiene | make diff-hygiene-summary | Do not stage broad generated churn unless those exact artifacts are reviewed pilot evidence. |
| What blocks deeper analysis? | partial | DCF Input Proof Batches | make dcf-input-proof-queue TOP_N=10 | 3,498 blocked item(s); top blockers: fundamentals_bundle_plus_shares: 3497, fundamentals_bundle: 7, shares_outstanding: 4, price: 3, fcf_margin: 1 |
| What stays out of staging? | green | No generated churn detected | make diff-hygiene-summary | Keep these broad generated patterns out by default: data/*.csv; data/reports/*.csv; outputs/*.csv; data/reports/ticker_readiness_report.previous.csv. Stage only a specific artifact if it is intentionally reviewed evidence. |
| What should the reviewer run next? | copy-only | outputs/pilot_readiness_packet.md | make pilot-readiness-packet OUTPUT=outputs/pilot_readiness_packet.md | The packet is read-only; it does not refresh data, apply imports, record proof, stage files, commit, or push. |

## Commit Package Handoff

| Step | Status | Copy-only command | Boundary |
| --- | --- | --- | --- |
| Stage reviewed product package | ready_to_stage | git add -- outputs/pilot_readiness_packet.md | 1 product/code/docs/test or reviewed Markdown file(s) are eligible for staging. Review the diff first; do not use git add -A. |
| Verify staged package | copy-only | make staged-hygiene-check && git diff --cached --check | Stop if staged hygiene shows generated CSV/JSON churn or manual-review paths. |
| Commit reviewed package | copy-only | git commit -m "Package reviewed product changes" | Commit only after tests, public wording, and staged hygiene pass. |
| Keep generated churn out | none | make diff-hygiene-summary | 0 generated CSV/JSON/report artifact(s) remain excluded by default. Keep these patterns out by default: data/*.csv; data/reports/*.csv; outputs/*.csv; data/reports/ticker_readiness_report.previous.csv. Stage only a specific reviewed evidence artifact if intentionally selected. |

## Readiness Snapshot

| Metric | Current saved value |
| --- | --- |
| Tracked tickers | 3538 |
| Price-ready | 265/3538 |
| Momentum usable | 262/3538 |
| DCF-ready | 23/3538 |
| Peer-ready | 9/3538 |
| Data sources available | 5/10 |
| Optional/manual lanes locked | 5 |
| Missing-data steps | 17391 |
| Urgent missing-data steps | 3276 |

## Pilot Gates

| Area | Status | Gate | Detail | Command |
| --- | --- | --- | --- | --- |
| GitHub sync | manual | GitHub branch state | ## main...origin/main [ahead 1]; reviewed local commits still need a push before the GitHub pilot link is current. | git push origin main |
| Generated artifact hygiene | manual | Dirty tree classification | 1 reviewed pilot packet artifact(s) pending; 0 generated CSV/JSON/report artifact(s) are dirty and excluded by default. | make diff-hygiene-summary |
| Readiness freshness | green | Readiness artifacts are current | Readiness artifacts are current relative to watched source files. | make status-check TOP_N=5 |
| Source proof gates | manual | DCF Input Proof Batches leads the source-review queue | 14,029 blocked and 38 partial proof item(s) remain across DCF inputs, trusted fundamentals, share count, peer mapping, and peer valuation inputs. That is acceptable for pilot review only if missing inputs stay visible. | make data-coverage-proof-queues TOP_N=10 |
| Proof ledger | green | 8 reviewed batch proof row(s) | Latest outcome: still_blocked; lane: share_count; batch: RB-SHARE-ABLV-20260621-001. | make reviewed-batch-proof |
| Browser QA evidence | green | Real screenshot evidence is ready | 3 committed screenshot asset(s) ready; pending workflow capture(s): none. Screenshots are product evidence only and do not refresh data or unlock blocked inputs. Reviewed asset staging command is available from browser QA JSON and capture plan after visual review. | make browser-qa-evidence |
| Public safety | manual | Run the public share gate before pilot sharing | The pilot checklist is read-only; public-check remains the explicit test, wording, dashboard smoke, and visitor-demo gate. | make public-check |
| Research guardrails | green | Research-only boundary remains required | Pilot surfaces must stay readiness-first and must not include broker integration, order routing, auto-trading, direct buy/sell instructions, fabricated inputs, or recommendations. | make public-wording-check |

## Source-Proof Queue Summary

| Queue | State | Ready | Partial | Blocked | Top blockers | Next safest command |
| --- | --- | --- | --- | --- | --- | --- |
| DCF Input Proof Batches | partial | 23 | 17 | 3498 | fundamentals_bundle_plus_shares: 3497, fundamentals_bundle: 7, shares_outstanding: 4, price: 3, fcf_margin: 1 | make dcf-input-proof-queue TOP_N=10 |
| Shares Outstanding Proof | partial | 37 | 4 | 3501 | shares_outstanding: 3501; share-count-only blockers: 4 | make share-count-proof-queue TOP_N=10 |
| Trusted Fundamentals Proof Queue | partial | 23 | 17 | 3498 | fundamentals_bundle_plus_shares: 3497, fundamentals_bundle: 7, fcf_margin: 1 | make dcf-input-source-command-plan FAMILY=fundamentals_bundle_plus_shares TOP_N=10 |
| Peer Mapping Proof Queue | partial | 9 | 0 | 3512 | source-backed peer mappings: 3512 | DRY_RUN=1 make peer-mapping-source-review TOP_N=10 |
| Peer Valuation Input Proof Queue | partial | 6 | 0 | 20 | peer prices: 17; peer fundamentals: 3; mapped-peer valuation blockers: 0 | make peer-mapping-queue TOP_N=25 |

## Latest Reviewed Batch Proof

- RB-SHARE-ABLV-20260621-001 / share_count / still_blocked / ABLV has price, revenue, free cash flow, and FCF margin, but shares_outstanding is missing. Local SEC-derived row states shares outstanding was unavailable from SEC Companyfacts; SEC and Yahoo staging are unavailable this session; report remains Price/setup review only.

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
- No generated CSV/JSON/report churn is currently dirty.

## Research-Only Guardrails

- This is research software, not investment advice.
- No broker integration, order routing, auto-trading, options recommendations, or direct buy/sell instructions.
- Do not fabricate prices, fundamentals, shares, market cap, peers, earnings, estimates, valuation inputs, metrics, or recommendations.
- Preserve ready, partial, blocked, excluded, supported, still_blocked, and skipped states.
- Keep broad generated CSV/JSON/report churn out of commits unless a specific artifact is intentionally reviewed evidence.
