# Pilot Readiness Packet

> Data readiness first. Analysis second. Research decision last.

This packet is a read-only reviewer summary. It does not refresh data, apply imports, record proof, stage files, commit, push, connect to brokers, route orders, auto-trade, or provide direct buy/sell instructions.

## Verdict: blocked

- Gate counts: green: 6, manual: 2, blocked: 2.
- Manual gates still required: 2.
- Blocked gates: 2.
- Blocked source inputs remain blocked until trusted source proof and review gates pass.

## Reviewer Handoff Summary

| Question | Status | Answer | Next safe command | Boundary |
| --- | --- | --- | --- | --- |
| What is the share package answer? | blocked | Share as controlled portfolio/demo evidence with manual gates; keep generated churn excluded; source-proof blockers stay visible; the root LICENSE keeps reuse restricted. | make public-check | This is a packaging answer only; it does not unlock analysis, source proof, reuse rights, or data freshness. |
| Can this be shared as a pilot? | blocked | blocked | make diff-hygiene-summary | Pilot readiness is a packaging gate, not an analysis or recommendation unlock. |
| What must be reviewed first? | blocked | Generated artifact hygiene | make diff-hygiene-summary | Stop before pilot packaging until product files are staged/committed or intentionally left local. |
| What blocks deeper analysis? | partial | DCF Input Proof Batches | make dcf-input-proof-queue TOP_N=10 | 2,862 blocked item(s); top blockers: fundamentals_bundle_plus_shares: 2862, fundamentals_bundle: 41, price: 3 |
| What stays out of staging? | manual | 18 generated artifact(s) excluded by default | make diff-hygiene-summary | Keep these broad generated patterns out by default: data/*.csv; data/reports/*.csv; outputs/*.csv; data/reports/ticker_readiness_report.previous.csv. Stage only a specific artifact if it is intentionally reviewed evidence. |
| What license boundary applies? | green | Controlled demo LICENSE is present | make license-status | Stop if public wording claims open-source or broad reuse rights that the root LICENSE does not grant. |
| What should the reviewer run next? | copy-only | outputs/pilot_readiness_packet.md | make pilot-readiness-packet PROFILE=default OUTPUT=outputs/pilot_readiness_packet.md | The packet is read-only; it does not refresh data, apply imports, record proof, stage files, commit, or push. |

## Commit Package Handoff

| Step | Status | Copy-only command | Boundary |
| --- | --- | --- | --- |
| Stage reviewed product package | ready_to_stage | git add -- outputs/pilot_readiness_packet.md src/pilot_readiness.py tests/test_pilot_readiness.py | 3 product/code/docs/test file(s) are eligible for staging. 0 sample report artifact(s) stay excluded unless individually reviewed. Review the diff first; do not use git add -A. |
| Verify staged package | copy-only | make staged-hygiene-check && git diff --cached --check | Stop if staged hygiene shows generated CSV/JSON churn or manual-review paths. |
| Commit reviewed package | copy-only | git commit -m "Package reviewed product changes" | Commit only after tests, public wording, and staged hygiene pass. |
| Keep generated churn out | excluded | make diff-hygiene-summary | 18 generated CSV/JSON/report artifact(s) and 0 broad generated stock report artifact(s) remain excluded by default. Keep these patterns out by default: data/*.csv; data/reports/*.csv; outputs/*.csv; data/reports/ticker_readiness_report.previous.csv. Stage only a specific reviewed evidence artifact if intentionally selected. |

## Readiness Snapshot

| Metric | Current saved value |
| --- | --- |
| Tracked tickers | 3541 |
| Price-ready | 265/3541 |
| Momentum usable | 262/3541 |
| DCF-ready | 169/3541 |
| Peer-ready | 9/3541 |
| Data sources available | 7/15 |
| Optional/manual lanes locked | 4 |
| Missing-data steps | 17431 |
| Urgent missing-data steps | 3301 |

## Pilot Gates

| Area | Status | Gate | Detail | Command |
| --- | --- | --- | --- | --- |
| GitHub sync | green | GitHub branch state | ## codex/personal-research-mode-mvp...origin/codex/personal-research-mode-mvp; HEAD is aligned with origin/codex/personal-research-mode-mvp. | git status --short --branch |
| Generated artifact hygiene | blocked | Dirty tree classification | 2 product/code/docs/test file(s), 0 sample report(s), and 0 manual-review path(s) are dirty. | make diff-hygiene-summary |
| Readiness freshness | green | Readiness artifacts are current | Readiness artifacts are current relative to watched source files. | make status-check TOP_N=5 |
| Readiness evidence | blocked | Readiness release evidence is working_artifact_uncommitted | Readiness artifacts differ from HEAD and are not tracked release evidence. | make readiness-preview TOP_N=20 |
| Source proof gates | manual | DCF Input Proof Batches leads the source-review queue | 12,116 blocked and 97 partial proof item(s) remain across DCF inputs, trusted fundamentals, share count, peer mapping, and peer valuation inputs. That is acceptable for pilot review only if missing inputs stay visible. | make data-coverage-proof-queues TOP_N=10 |
| Proof ledger | green | 1342 reviewed batch proof row(s) | Latest outcome: still_blocked; lane: price_history; batch: RB-20260711-FLY-SHORT-HISTORY-001. | make reviewed-batch-proof |
| Browser QA evidence | green | Real screenshot evidence is ready | 3 committed screenshot asset(s) ready; pending workflow capture(s): none. Screenshots are product evidence only and do not refresh data or unlock blocked inputs. Reviewed asset staging command is available from browser QA JSON and capture plan after visual review. | make browser-qa-evidence |
| Public safety | manual | Run the public share gate before pilot sharing | The pilot checklist is read-only; public-check remains the explicit test, wording, dashboard smoke, browser evidence, license-status, and visitor-demo gate. | make public-check |
| License status | green | Controlled demo LICENSE is present | Share as controlled portfolio/demo evidence under the root LICENSE; do not describe as open source or reusable software. Visitors may review the project for evaluation, but copying, redistribution, sublicensing, hosted reuse, and modified-publication rights are not granted without written permission. | make license-status |
| Research guardrails | green | Research-only boundary remains required | Pilot surfaces must stay readiness-first and must not include broker integration, order routing, auto-trading, direct buy/sell instructions, fabricated inputs, or recommendations. | make public-wording-check |

## Source-Proof Queue Summary

| Queue | State | Ready | Partial | Blocked | Top blockers | Next safest command |
| --- | --- | --- | --- | --- | --- | --- |
| DCF Input Proof Batches | partial | 169 | 44 | 2862 | fundamentals_bundle_plus_shares: 2862, fundamentals_bundle: 41, price: 3 | make dcf-input-proof-queue TOP_N=10 |
| Shares Outstanding Proof | partial | 679 | 0 | 2862 | shares_outstanding: 2862; share-count-only blockers: 0 | make share-count-proof-queue TOP_N=10 |
| Trusted Fundamentals Proof Queue | partial | 169 | 44 | 2862 | fundamentals_bundle_plus_shares: 2862, fundamentals_bundle: 41 | make dcf-input-source-command-plan FAMILY=fundamentals_bundle_plus_shares TOP_N=10 |
| Peer Mapping Proof Queue | partial | 9 | 0 | 3510 | source-backed peer mappings: 3510 | DRY_RUN=1 make peer-mapping-source-review TOP_N=10 |
| Peer Valuation Input Proof Queue | partial | 0 | 9 | 20 | peer prices: 20; peer fundamentals: 0; mapped-peer valuation blockers: 0 | make peer-mapping-queue TOP_N=25 |

## Provider Setup Checklist

Use `make provider-setup-checklist` for the current checklist-style setup view. Real key values are never printed.

### Source Buckets

- Free public sources: SEC Companyfacts, SEC submissions, SEC filing documents, Stooq, Yahoo/yfinance
- Keyed free-tier fallbacks: configured -; needs key FMP free tier, Alpha Vantage free tier, Finnhub free tier
- Optional broker boundary: IBKR read-only (disabled unless explicitly configured)

### Provider Activation Plan

- Run make project-status-check first; if it says queues are exhausted, do not reopen broad proof loops.
- Configure at most one missing keyed free-tier provider locally, then rerun make session-source-preflight.
- Run that provider's reviewed one-ticker smoke command only; do not start a broad batch from setup.
- Continue only through validate, preview, rejected-row review, and source-provenance checks.
- If no source-backed row is staged, record still_blocked/skipped/excluded and pivot.

### One-Provider Setup Decision

- Configure first: FMP free tier.
- Why first: Broadest keyed fallback here: price, fundamentals, share count, and the largest stated free-tier daily cap.
- Setup env: `FMP_API_KEY`.
- Reviewed one-ticker smoke command: `make fmp-smoke TICKER=<ticker>`.
- Do not configure all missing providers at once; configure one, rerun preflight, run a reviewed one-ticker smoke command, then validate/preview before any apply.

| Provider | Setup state | Unlock lanes | Usage | Smoke command | Cannot unlock | Safe next step |
| --- | --- | --- | --- | --- | --- | --- |
| SEC Companyfacts | available | fundamentals, share_count | source_backed_companyfacts | not_applicable | Peers, earnings estimates, recommendations, or inferred missing values. | Run make session-source-preflight before using this source path. |
| SEC submissions | available | metadata | metadata_evidence_only | not_applicable | DCF, valuation, earnings, analyst estimates, or share count unless a filing document has an explicit fact. | Run make session-source-preflight before using this source path. |
| SEC filing documents | available | share_count | explicit_filing_document_evidence | not_applicable | Inferred shares, market cap-derived shares, or missing fundamentals. | Run make session-source-preflight before using this source path. |
| Stooq | available | price | free_public_daily_ohlcv | make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=1 TOP_N=1 PROVIDER=stooq | Fundamentals, shares, peers, earnings, estimates, or valuation inputs. | Run make session-source-preflight before using this source path. |
| Yahoo/yfinance | available | price, fundamentals, optional_context | provider_assisted_research_data | not_applicable | Trusted proof without validate, preview, rejected-row review, and apply gates. | Run make session-source-preflight before using this source path. |
| FMP free tier | needs_key | price, fundamentals, share_count | keyed_free_tier_fallback | make fmp-smoke TICKER=<ticker> | Full-universe refresh without caps, recommendations, order routing, or unreviewed valuation inputs. | Set FMP_API_KEY in config/provider_keys.env, then rerun make session-source-preflight. |
| Alpha Vantage free tier | needs_key | price, fundamentals, share_count | keyed_free_tier_fallback | make alpha-vantage-smoke TICKER=<ticker> | Full-universe refresh without caps, recommendations, order routing, or unreviewed valuation inputs. | Set ALPHA_VANTAGE_API_KEY in config/provider_keys.env, then rerun make session-source-preflight. |
| Finnhub free tier | needs_key | price, fundamentals, share_count | keyed_free_tier_fallback | make finnhub-smoke TICKER=<ticker> | Full-universe refresh without caps, recommendations, order routing, or unreviewed valuation inputs. | Set FINNHUB_API_KEY in config/provider_keys.env, then rerun make session-source-preflight. |
| IBKR read-only | optional_disabled | price | read_only_daily_ohlcv | make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=1 TOP_N=1 PROVIDER=ibkr | Broker actions, order routing, auto-trading, fundamentals, shares, peers, earnings, or estimates. | Leave disabled unless intentionally using read-only daily OHLCV. |

## Latest Reviewed Batch Proof

- RB-20260711-FLY-SHORT-HISTORY-001 / price_history / still_blocked / Yahoo returned only available post-listing history after Stooq 404. FLY remains below preferred 1Y canonical history depth; do not retry without changed provider history, canonical import proof, or verified manual OHLCV.

## Manual Gates Still Required

- Source proof gates: Do not call a lane supported until source proof, validate, preview, rejected-row review, apply/skip decision, rebuilt readiness, and proof record pass.
- Public safety: Stop before public pilot sharing if public-check, public wording, dashboard smoke, whitespace, browser evidence, or the license boundary fails.

## License Decision Options

| Goal | Path | Visitor expectation |
| --- | --- | --- |
| Controlled portfolio showcase | Keep the current controlled demo license | Visitors can review the project, but reuse rights are not granted. |
| Let others reuse with attribution | Add MIT or Apache-2.0 | Visitors can reuse under the selected license terms. |
| Keep stronger control | Add a custom or proprietary notice | Visitors should ask before reuse; use legal review for custom wording. |

## Stop Rules

- GitHub sync: Stop if a later comparison shows unreviewed commits or divergence.
- Generated artifact hygiene: Stop before pilot packaging until product files are staged/committed or intentionally left local.
- Readiness freshness: Stop before quoting final counts or proof deltas if readiness artifacts are stale or missing. In-memory preview only; it does not refresh or persist saved readiness.
- Readiness evidence: Stop before treating working readiness as tracked release evidence. In-memory preview only; it does not refresh or persist saved readiness.
- Source proof gates: Do not call a lane supported until source proof, validate, preview, rejected-row review, apply/skip decision, rebuilt readiness, and proof record pass.
- Proof ledger: Do not record supported outcomes without reviewed proof-row fields and generated-artifact review.
- Browser QA evidence: Stop if later screenshots are generated thumbnails, tracebacks, or stale proof substitutes.
- Public safety: Stop before public pilot sharing if public-check, public wording, dashboard smoke, whitespace, browser evidence, or the license boundary fails.
- License status: Stop if public wording claims open-source or broad reuse rights that the root LICENSE does not grant.
- Research guardrails: Stop if any public or dashboard wording turns readiness queues into advice or trade instructions.

## Exact Next Safest Commands

- `git status --short --branch`
- `make diff-hygiene-summary`
- `make status-check TOP_N=5`
- `make readiness-preview TOP_N=20`
- `make data-coverage-proof-queues TOP_N=10`
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
- `data/price_coverage_report.csv`
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
- `data/universe_master.csv`
- `outputs/feature_readiness_summary.csv`
- `outputs/peer_unlock_worklist.csv`

## Research-Only Guardrails

- This is research software, not investment advice.
- No broker integration, order routing, auto-trading, options recommendations, or direct buy/sell instructions.
- Do not fabricate prices, fundamentals, shares, market cap, peers, earnings, estimates, valuation inputs, metrics, or recommendations.
- Preserve ready, partial, blocked, excluded, supported, still_blocked, and skipped states.
- Keep broad generated CSV/JSON/report churn out of commits unless a specific artifact is intentionally reviewed evidence.
