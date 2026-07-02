# Pilot Readiness Packet

> Data readiness first. Analysis second. Research decision last.

This packet is a read-only reviewer summary. It does not refresh data, apply imports, record proof, stage files, commit, push, connect to brokers, route orders, auto-trade, or provide direct buy/sell instructions.

## Verdict: pilot-ready with manual gates

- Gate counts: green: 4, manual: 5, blocked: 0.
- Manual gates still required: 5.
- Blocked gates: 0.
- Blocked source inputs remain blocked until trusted source proof and review gates pass.

## Reviewer Handoff Summary

| Question | Status | Answer | Next safe command | Boundary |
| --- | --- | --- | --- | --- |
| What is the share package answer? | manual | Share as portfolio/demo only with manual gates; keep generated churn excluded; source-proof blockers stay visible; license boundary still applies. | make public-check | This is a packaging answer only; it does not unlock analysis, source proof, reuse rights, or data freshness. |
| Can this be shared as a pilot? | manual | pilot-ready with manual gates | make diff-hygiene-summary | Pilot readiness is a packaging gate, not an analysis or recommendation unlock. |
| What must be reviewed first? | manual | Generated artifact hygiene | make diff-hygiene-summary | Do not stage broad generated stock reports or broad generated churn unless those exact artifacts are reviewed pilot evidence. |
| What blocks deeper analysis? | manual | Check source-proof gate | make project-status | 3,778 blocked and 486 partial proof item(s) remain visible, but current proof queues are already reviewed or non-actionable. Use project-status and provider setup before reopening broad proof queues. |
| What stays out of staging? | manual | 35 generated artifact(s) excluded by default | make diff-hygiene-summary | Keep these broad generated patterns out by default: data/*.csv; data/reports/*.csv; outputs/*.csv; data/reports/ticker_readiness_report.previous.csv. Stage only a specific artifact if it is intentionally reviewed evidence. |
| What license boundary applies? | manual | No root LICENSE file found | make license-status | Do not claim reuse rights until a root LICENSE is selected and README wording is updated. |
| What should the reviewer run next? | copy-only | outputs/pilot_readiness_packet.md | make pilot-readiness-packet OUTPUT=outputs/pilot_readiness_packet.md | The packet is read-only; it does not refresh data, apply imports, record proof, stage files, commit, or push. |

## Commit Package Handoff

| Step | Status | Copy-only command | Boundary |
| --- | --- | --- | --- |
| Stage reviewed product package | ready_to_stage | git add -- outputs/pilot_readiness_packet.md outputs/pilot_share_brief.md | 2 product/code/docs/test file(s) are eligible for staging. 2876 sample report artifact(s) stay excluded unless individually reviewed. Review the diff first; do not use git add -A. |
| Verify staged package | copy-only | make staged-hygiene-check && git diff --cached --check | Stop if staged hygiene shows generated CSV/JSON churn or manual-review paths. |
| Commit reviewed package | copy-only | git commit -m "Package reviewed product changes" | Commit only after tests, public wording, and staged hygiene pass. |
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
| GitHub sync | manual | GitHub branch state | ## main...origin/main [ahead 9]; reviewed local commits still need a push before the GitHub pilot link is current. | git push origin main |
| Generated artifact hygiene | manual | Dirty tree classification | 1 reviewed pilot packet artifact(s) pending; 2876 broad sample report artifact(s) pending review; 1 reviewed share brief artifact(s) pending; 35 generated CSV/JSON/report artifact(s) are dirty and excluded by default. | make diff-hygiene-summary |
| Readiness freshness | green | Readiness artifacts are current | Readiness artifacts are current relative to watched source files. | make status-check TOP_N=5 |
| Source proof gates | manual | Source-proof queues reviewed or exhausted | 3,778 blocked and 486 partial proof item(s) remain visible, but current proof queues are already reviewed or non-actionable. Use project-status and provider setup before reopening broad proof queues. | make project-status |
| Proof ledger | green | 1151 reviewed batch proof row(s) | Latest outcome: candidate_context_only; lane: optional_context; batch: RB-20260701-OPTIONAL-YF-CONTEXT-NOAPPLY-002. | make reviewed-batch-proof |
| Browser QA evidence | green | Real screenshot evidence is ready | 3 committed screenshot asset(s) ready; pending workflow capture(s): none. Screenshots are product evidence only and do not refresh data or unlock blocked inputs. Reviewed asset staging command is available from browser QA JSON and capture plan after visual review. | make browser-qa-evidence |
| Public safety | manual | Run the public share gate before pilot sharing | The pilot checklist is read-only; public-check remains the explicit test, wording, dashboard smoke, and visitor-demo gate. | make public-check |
| License status | manual | No root LICENSE file found | Share as portfolio/demo only; do not describe as open source or grant reuse rights. Product screenshots and demo evidence may be shared as portfolio context only; they do not grant copying, redistribution, adaptation, or software reuse rights. | make license-status |
| Research guardrails | green | Research-only boundary remains required | Pilot surfaces must stay readiness-first and must not include broker integration, order routing, auto-trading, direct buy/sell instructions, fabricated inputs, or recommendations. | make public-wording-check |

## Source-Proof Queue Summary

| Queue | State | Ready | Partial | Blocked | Top blockers | Next safest command |
| --- | --- | --- | --- | --- | --- | --- |
| DCF Input Proof Batches | partial | 2691 | 243 | 90 | fundamentals_bundle: 242, fundamentals_bundle_plus_shares: 91 | make dcf-input-proof-queue TOP_N=10 |
| Shares Outstanding Proof | partial | 3447 | 0 | 91 | shares_outstanding: 91; share-count-only blockers: 0 | make share-count-proof-queue TOP_N=10 |
| Trusted Fundamentals Proof Queue | partial | 2691 | 243 | 90 | fundamentals_bundle: 242, fundamentals_bundle_plus_shares: 91 | make dcf-input-source-command-plan FAMILY=fundamentals_bundle TOP_N=10 |
| Peer Mapping Proof Queue | partial | 29 | 0 | 3507 | source-backed peer mappings: 3507 | DRY_RUN=1 make peer-mapping-source-review TOP_N=10 |
| Peer Valuation Input Proof Queue | ready | 29 | 0 | 0 | peer prices: 0; peer fundamentals: 0; mapped-peer valuation blockers: 0 | make peer-mapping-queue TOP_N=25 |

## Provider Setup Checklist

Use `make provider-setup-checklist` for the current checklist-style setup view. Real key values are never printed.

### Source Buckets

- Free public sources: SEC Companyfacts, SEC submissions, SEC filing documents, Stooq, Yahoo/yfinance
- Keyed free-tier fallbacks: configured -; needs key FMP free tier, Alpha Vantage free tier, Finnhub free tier
- Optional broker boundary: IBKR read-only

### Provider Activation Plan

- Run make project-status first; if it says queues are exhausted, do not reopen broad proof loops.
- Configure at most one missing keyed free-tier provider locally, then rerun make session-source-preflight.
- Run that provider's one-ticker smoke command only; do not start a broad batch from setup.
- Continue only through validate, preview, rejected-row review, and source-provenance checks.
- If no source-backed row is staged, record still_blocked/skipped/excluded and pivot.

### One-Provider Setup Decision

- Configure first: FMP free tier.
- Why first: Broadest keyed fallback here: price, fundamentals, share count, and the largest stated free-tier daily cap.
- Setup env: `FMP_API_KEY`.
- One-ticker smoke command: `make fmp-stage TICKERS=<ticker> && make imports-validate IMPORT_TICKERS=<ticker> && make imports-preview IMPORT_TICKERS=<ticker>`.
- Do not configure all missing providers at once; configure one, rerun preflight, smoke one ticker, then validate/preview before any apply.

| Provider | Setup state | Unlock lanes | Usage | Smoke command | Cannot unlock | Safe next step |
| --- | --- | --- | --- | --- | --- | --- |
| SEC Companyfacts | available | fundamentals, share_count | source_backed_companyfacts | not_applicable | Peers, earnings estimates, recommendations, or inferred missing values. | Run make session-source-preflight before using this source path. |
| SEC submissions | available | metadata | metadata_evidence_only | not_applicable | DCF, valuation, earnings, analyst estimates, or share count unless a filing document has an explicit fact. | Run make session-source-preflight before using this source path. |
| SEC filing documents | available | share_count | explicit_filing_document_evidence | not_applicable | Inferred shares, market cap-derived shares, or missing fundamentals. | Run make session-source-preflight before using this source path. |
| Stooq | available | price | free_public_daily_ohlcv | make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=1 TOP_N=1 PROVIDER=stooq | Fundamentals, shares, peers, earnings, estimates, or valuation inputs. | Run make session-source-preflight before using this source path. |
| Yahoo/yfinance | available | price, fundamentals, optional_context | provider_assisted_research_data | not_applicable | Trusted proof without validate, preview, rejected-row review, and apply gates. | Run make session-source-preflight before using this source path. |
| FMP free tier | needs_key | price, fundamentals, share_count | keyed_free_tier_fallback | make fmp-stage TICKERS=<ticker> && make imports-validate IMPORT_TICKERS=<ticker> && make imports-preview IMPORT_TICKERS=<ticker> | Full-universe refresh without caps, recommendations, order routing, or unreviewed valuation inputs. | Set FMP_API_KEY in config/provider_keys.env, then rerun make session-source-preflight. |
| Alpha Vantage free tier | needs_key | price, fundamentals, share_count | keyed_free_tier_fallback | make alpha-vantage-stage TICKERS=<ticker> && make imports-validate IMPORT_TICKERS=<ticker> && make imports-preview IMPORT_TICKERS=<ticker> | Full-universe refresh without caps, recommendations, order routing, or unreviewed valuation inputs. | Set ALPHA_VANTAGE_API_KEY in config/provider_keys.env, then rerun make session-source-preflight. |
| Finnhub free tier | needs_key | price, fundamentals, share_count | keyed_free_tier_fallback | make finnhub-stage TICKERS=<ticker> && make imports-validate IMPORT_TICKERS=<ticker> && make imports-preview IMPORT_TICKERS=<ticker> | Full-universe refresh without caps, recommendations, order routing, or unreviewed valuation inputs. | Set FINNHUB_API_KEY in config/provider_keys.env, then rerun make session-source-preflight. |
| IBKR read-only | optional_disabled | price | read_only_daily_ohlcv | make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=1 TOP_N=1 PROVIDER=ibkr | Broker actions, order routing, auto-trading, fundamentals, shares, peers, earnings, or estimates. | Leave disabled unless intentionally using read-only daily OHLCV. |

## Latest Reviewed Batch Proof

- RB-20260701-OPTIONAL-YF-CONTEXT-NOAPPLY-002 / optional_context / candidate_context_only / yfinance source-backed optional context can route research only. Earnings rows contain next_earnings_date without EPS/revenue actuals or estimates; analyst rows contain price-target context only. No recommendations, no readiness unlock.

## Manual Gates Still Required

- GitHub sync: Do not push if unreviewed product changes or generated churn are staged.
- Generated artifact hygiene: Do not stage broad generated stock reports or broad generated churn unless those exact artifacts are reviewed pilot evidence.
- Source proof gates: Do not reopen broad proof queues until project-status shows executable company candidates, new source-backed rows, keyed providers, reviewed manual rows, or changed blockers.
- Public safety: Stop before public pilot sharing if public-check, public wording, dashboard smoke, or whitespace checks fail.
- License status: Do not claim reuse rights until a root LICENSE is selected and README wording is updated.

## License Decision Options

| Goal | Path | Visitor expectation |
| --- | --- | --- |
| Portfolio showcase only | Keep no license for now | Visitors can read the code, but reuse rights are not granted. |
| Let others reuse with attribution | Add MIT or Apache-2.0 | Visitors can reuse under the selected license terms. |
| Keep stronger control | Add a custom or proprietary notice | Visitors should ask before reuse; use legal review for custom wording. |

## Stop Rules

- GitHub sync: Do not push if unreviewed product changes or generated churn are staged.
- Generated artifact hygiene: Do not stage broad generated stock reports or broad generated churn unless those exact artifacts are reviewed pilot evidence.
- Readiness freshness: Stop before quoting final counts or proof deltas if readiness artifacts are stale or missing.
- Source proof gates: Do not reopen broad proof queues until project-status shows executable company candidates, new source-backed rows, keyed providers, reviewed manual rows, or changed blockers.
- Proof ledger: Do not record supported outcomes without reviewed proof-row fields and generated-artifact review.
- Browser QA evidence: Stop if later screenshots are generated thumbnails, tracebacks, or stale proof substitutes.
- Public safety: Stop before public pilot sharing if public-check, public wording, dashboard smoke, or whitespace checks fail.
- License status: Do not claim reuse rights until a root LICENSE is selected and README wording is updated.
- Research guardrails: Stop if any public or dashboard wording turns readiness queues into advice or trade instructions.

## Exact Next Safest Commands

- `git push origin main`
- `make diff-hygiene-summary`
- `make status-check TOP_N=5`
- `make project-status`
- `make reviewed-batch-proof`
- `make browser-qa-evidence`
- `make public-check`
- `make license-status`
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
