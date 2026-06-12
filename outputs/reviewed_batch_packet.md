# Reviewed Batch Run Packet

Research-only: this packet plans data-readiness work. It is not investment advice, does not connect to brokers, does not route orders, and does not provide direct buy/sell instructions.

- Batch ID: `RB-20260612T031422Z`
- Selected lane: `prices`
- Lane scope: `price_coverage`
- Ticker scope: `top 3`
- Freshness status: `current`
- Freshness note: Readiness artifacts are current relative to watched source files.
- Refresh command if blocked: `make readiness`

## Readiness Snapshot

- Pre-run snapshot command: `make readiness-snapshot`
- Refresh saved readiness reports before relying on final counts: `make readiness`
- Current operations view: `make readiness-ops-center`
- Current frontier view: `make coverage-frontier TOP_N=10`

## Proposed Actions

### Price Coverage: ARCT

- Workflow mode: `dry_run_first`
- Source/freshness context: Provider-assisted price rows can be planned at scale; dry-run and capped review come first. Freshness: current: Readiness artifacts are current relative to watched source files.
- Dry-run command: `make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N=3 PROVIDER=yahoo`
- Capped execution command: `make price-refresh-loop MAX_CANDIDATES=3500 TOP_N=3 PROVIDER=yahoo SLEEP_SECONDS=30`
- Validate: `make price-validate`
- Preview: `make price-preview`
- Apply gate: `make price-apply only for reviewed trusted rows`
- Post-run verification: `make readiness && make price-coverage TOP_N=3 && make status-check TOP_N=5`
- Expected artifacts: data/prices.csv; data/reports/price_coverage_report.csv; outputs/reviewed_batch_packet.csv
- Rollback checklist: If refreshed prices are incomplete or suspicious, keep generated CSV churn unstaged and restore reviewed local price files from git or the readiness snapshot.
- Do not proceed if: readiness artifacts are missing or stale; source proof is unavailable; validation fails; preview shows unexpected rows; rejected-row reports contain unresolved rows; the operator cannot identify changed source files

### Price Coverage: ARDX

- Workflow mode: `dry_run_first`
- Source/freshness context: Provider-assisted price rows can be planned at scale; dry-run and capped review come first. Freshness: current: Readiness artifacts are current relative to watched source files.
- Dry-run command: `make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N=3 PROVIDER=yahoo`
- Capped execution command: `make price-refresh-loop MAX_CANDIDATES=3500 TOP_N=3 PROVIDER=yahoo SLEEP_SECONDS=30`
- Validate: `make price-validate`
- Preview: `make price-preview`
- Apply gate: `make price-apply only for reviewed trusted rows`
- Post-run verification: `make readiness && make price-coverage TOP_N=3 && make status-check TOP_N=5`
- Expected artifacts: data/prices.csv; data/reports/price_coverage_report.csv; outputs/reviewed_batch_packet.csv
- Rollback checklist: If refreshed prices are incomplete or suspicious, keep generated CSV churn unstaged and restore reviewed local price files from git or the readiness snapshot.
- Do not proceed if: readiness artifacts are missing or stale; source proof is unavailable; validation fails; preview shows unexpected rows; rejected-row reports contain unresolved rows; the operator cannot identify changed source files

### Price Coverage: ARE

- Workflow mode: `dry_run_first`
- Source/freshness context: Provider-assisted price rows can be planned at scale; dry-run and capped review come first. Freshness: current: Readiness artifacts are current relative to watched source files.
- Dry-run command: `make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N=3 PROVIDER=yahoo`
- Capped execution command: `make price-refresh-loop MAX_CANDIDATES=3500 TOP_N=3 PROVIDER=yahoo SLEEP_SECONDS=30`
- Validate: `make price-validate`
- Preview: `make price-preview`
- Apply gate: `make price-apply only for reviewed trusted rows`
- Post-run verification: `make readiness && make price-coverage TOP_N=3 && make status-check TOP_N=5`
- Expected artifacts: data/prices.csv; data/reports/price_coverage_report.csv; outputs/reviewed_batch_packet.csv
- Rollback checklist: If refreshed prices are incomplete or suspicious, keep generated CSV churn unstaged and restore reviewed local price files from git or the readiness snapshot.
- Do not proceed if: readiness artifacts are missing or stale; source proof is unavailable; validation fails; preview shows unexpected rows; rejected-row reports contain unresolved rows; the operator cannot identify changed source files

## Review Checklist

- Confirm readiness artifacts are current or run `make readiness`.
- Confirm the dry run matches the intended lane and capped scope.
- Confirm source files are trusted and local.
- For mutating workflows, run validate -> preview -> apply only after review.
- Check rejected-row reports before treating any lane as supported.
- Run post-run readiness verification and record supported, still_blocked, skipped, or excluded honestly.

## Proof Row Template

- batch_id:
- lane:
- tickers:
- pre_run_readiness_snapshot:
- command_run:
- validation_result:
- preview_result:
- apply_result:
- post_run_readiness_snapshot:
- reviewer:
- review_date:
- source_files:
- notes:

## Guardrails

- Do not fabricate prices, fundamentals, peers, earnings, analyst estimates, valuation inputs, or recommendations.
- Do not treat a high unlock-impact lane as a security ranking.
- Do not stage broad generated CSV/JSON churn unless it is intentionally reviewed evidence.
- Do not proceed when source proof, validation, preview, rejected-row checks, or rollback path is unclear.
