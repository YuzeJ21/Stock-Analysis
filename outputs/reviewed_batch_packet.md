# Reviewed Batch Run Packet

Research-only: this packet plans data-readiness work. It is not investment advice, does not connect to brokers, does not route orders, and does not provide direct buy/sell instructions.

- Batch ID: `RB-20260613T014434Z`
- Selected lane: `prices`
- Lane scope: `price_coverage`
- Ticker scope: `top 10`
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
- Dry-run command: `make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N=10 PROVIDER=yahoo`
- Capped execution command: `make price-refresh-loop MAX_CANDIDATES=3500 TOP_N=10 PROVIDER=yahoo SLEEP_SECONDS=30`
- Validate: `make price-validate`
- Preview: `make price-preview`
- Apply gate: `make price-apply only for reviewed trusted rows`
- Post-run verification: `make readiness && make price-coverage TOP_N=10 && make status-check TOP_N=5`
- Readiness comparison: `make reviewed-batch-compare LANE=prices BATCH_ID=RB-20260613T014434Z REVIEW_DATE=<yyyy-mm-dd>`
- Proof ledger record: `make reviewed-batch-proof-record BATCH_ID="RB-20260613T014434Z" LANE="price_coverage" REVIEW_DATE="<yyyy-mm-dd>" FINAL_OUTCOME="<supported|still_blocked|skipped|excluded>" COMMAND_RUN="<exact reviewed command>" VALIDATION_RESULT="<pass/fail/not_run>" PREVIEW_RESULT="<reviewed/not_run>" APPLY_RESULT="<applied/not_run/skipped>" CHANGED_READINESS_COUNTS="<from reviewed-batch-compare>" CHANGED_TICKERS="<from reviewed-batch-compare>"`
- Expected artifacts: data/prices.csv; data/reports/price_coverage_report.csv; outputs/reviewed_batch_packet.csv
- Rollback checklist: If refreshed prices are incomplete or suspicious, keep generated CSV churn unstaged and restore reviewed local price files from git or the readiness snapshot.
- Do not proceed if: readiness artifacts are missing or stale; source proof is unavailable; validation fails; preview shows unexpected rows; rejected-row reports contain unresolved rows; the operator cannot identify changed source files

Lane proof instructions:
- Record pre-run price-ready, momentum-ready, liquidity, and correlation counts before any refresh.
- Use dry-run output to cap scope; do not treat provider availability as reviewed data.
- After execution, rerun readiness and compare changed readiness counts before keeping artifacts.
- Use make reviewed-batch-compare after make readiness so the proof ledger records changed counts and changed tickers without guessing.

### Price Coverage: ARDX

- Workflow mode: `dry_run_first`
- Source/freshness context: Provider-assisted price rows can be planned at scale; dry-run and capped review come first. Freshness: current: Readiness artifacts are current relative to watched source files.
- Dry-run command: `make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N=10 PROVIDER=yahoo`
- Capped execution command: `make price-refresh-loop MAX_CANDIDATES=3500 TOP_N=10 PROVIDER=yahoo SLEEP_SECONDS=30`
- Validate: `make price-validate`
- Preview: `make price-preview`
- Apply gate: `make price-apply only for reviewed trusted rows`
- Post-run verification: `make readiness && make price-coverage TOP_N=10 && make status-check TOP_N=5`
- Readiness comparison: `make reviewed-batch-compare LANE=prices BATCH_ID=RB-20260613T014434Z REVIEW_DATE=<yyyy-mm-dd>`
- Proof ledger record: `make reviewed-batch-proof-record BATCH_ID="RB-20260613T014434Z" LANE="price_coverage" REVIEW_DATE="<yyyy-mm-dd>" FINAL_OUTCOME="<supported|still_blocked|skipped|excluded>" COMMAND_RUN="<exact reviewed command>" VALIDATION_RESULT="<pass/fail/not_run>" PREVIEW_RESULT="<reviewed/not_run>" APPLY_RESULT="<applied/not_run/skipped>" CHANGED_READINESS_COUNTS="<from reviewed-batch-compare>" CHANGED_TICKERS="<from reviewed-batch-compare>"`
- Expected artifacts: data/prices.csv; data/reports/price_coverage_report.csv; outputs/reviewed_batch_packet.csv
- Rollback checklist: If refreshed prices are incomplete or suspicious, keep generated CSV churn unstaged and restore reviewed local price files from git or the readiness snapshot.
- Do not proceed if: readiness artifacts are missing or stale; source proof is unavailable; validation fails; preview shows unexpected rows; rejected-row reports contain unresolved rows; the operator cannot identify changed source files

Lane proof instructions:
- Record pre-run price-ready, momentum-ready, liquidity, and correlation counts before any refresh.
- Use dry-run output to cap scope; do not treat provider availability as reviewed data.
- After execution, rerun readiness and compare changed readiness counts before keeping artifacts.
- Use make reviewed-batch-compare after make readiness so the proof ledger records changed counts and changed tickers without guessing.

### Price Coverage: ARE

- Workflow mode: `dry_run_first`
- Source/freshness context: Provider-assisted price rows can be planned at scale; dry-run and capped review come first. Freshness: current: Readiness artifacts are current relative to watched source files.
- Dry-run command: `make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N=10 PROVIDER=yahoo`
- Capped execution command: `make price-refresh-loop MAX_CANDIDATES=3500 TOP_N=10 PROVIDER=yahoo SLEEP_SECONDS=30`
- Validate: `make price-validate`
- Preview: `make price-preview`
- Apply gate: `make price-apply only for reviewed trusted rows`
- Post-run verification: `make readiness && make price-coverage TOP_N=10 && make status-check TOP_N=5`
- Readiness comparison: `make reviewed-batch-compare LANE=prices BATCH_ID=RB-20260613T014434Z REVIEW_DATE=<yyyy-mm-dd>`
- Proof ledger record: `make reviewed-batch-proof-record BATCH_ID="RB-20260613T014434Z" LANE="price_coverage" REVIEW_DATE="<yyyy-mm-dd>" FINAL_OUTCOME="<supported|still_blocked|skipped|excluded>" COMMAND_RUN="<exact reviewed command>" VALIDATION_RESULT="<pass/fail/not_run>" PREVIEW_RESULT="<reviewed/not_run>" APPLY_RESULT="<applied/not_run/skipped>" CHANGED_READINESS_COUNTS="<from reviewed-batch-compare>" CHANGED_TICKERS="<from reviewed-batch-compare>"`
- Expected artifacts: data/prices.csv; data/reports/price_coverage_report.csv; outputs/reviewed_batch_packet.csv
- Rollback checklist: If refreshed prices are incomplete or suspicious, keep generated CSV churn unstaged and restore reviewed local price files from git or the readiness snapshot.
- Do not proceed if: readiness artifacts are missing or stale; source proof is unavailable; validation fails; preview shows unexpected rows; rejected-row reports contain unresolved rows; the operator cannot identify changed source files

Lane proof instructions:
- Record pre-run price-ready, momentum-ready, liquidity, and correlation counts before any refresh.
- Use dry-run output to cap scope; do not treat provider availability as reviewed data.
- After execution, rerun readiness and compare changed readiness counts before keeping artifacts.
- Use make reviewed-batch-compare after make readiness so the proof ledger records changed counts and changed tickers without guessing.

### Price Coverage: AREC

- Workflow mode: `dry_run_first`
- Source/freshness context: Provider-assisted price rows can be planned at scale; dry-run and capped review come first. Freshness: current: Readiness artifacts are current relative to watched source files.
- Dry-run command: `make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N=10 PROVIDER=yahoo`
- Capped execution command: `make price-refresh-loop MAX_CANDIDATES=3500 TOP_N=10 PROVIDER=yahoo SLEEP_SECONDS=30`
- Validate: `make price-validate`
- Preview: `make price-preview`
- Apply gate: `make price-apply only for reviewed trusted rows`
- Post-run verification: `make readiness && make price-coverage TOP_N=10 && make status-check TOP_N=5`
- Readiness comparison: `make reviewed-batch-compare LANE=prices BATCH_ID=RB-20260613T014434Z REVIEW_DATE=<yyyy-mm-dd>`
- Proof ledger record: `make reviewed-batch-proof-record BATCH_ID="RB-20260613T014434Z" LANE="price_coverage" REVIEW_DATE="<yyyy-mm-dd>" FINAL_OUTCOME="<supported|still_blocked|skipped|excluded>" COMMAND_RUN="<exact reviewed command>" VALIDATION_RESULT="<pass/fail/not_run>" PREVIEW_RESULT="<reviewed/not_run>" APPLY_RESULT="<applied/not_run/skipped>" CHANGED_READINESS_COUNTS="<from reviewed-batch-compare>" CHANGED_TICKERS="<from reviewed-batch-compare>"`
- Expected artifacts: data/prices.csv; data/reports/price_coverage_report.csv; outputs/reviewed_batch_packet.csv
- Rollback checklist: If refreshed prices are incomplete or suspicious, keep generated CSV churn unstaged and restore reviewed local price files from git or the readiness snapshot.
- Do not proceed if: readiness artifacts are missing or stale; source proof is unavailable; validation fails; preview shows unexpected rows; rejected-row reports contain unresolved rows; the operator cannot identify changed source files

Lane proof instructions:
- Record pre-run price-ready, momentum-ready, liquidity, and correlation counts before any refresh.
- Use dry-run output to cap scope; do not treat provider availability as reviewed data.
- After execution, rerun readiness and compare changed readiness counts before keeping artifacts.
- Use make reviewed-batch-compare after make readiness so the proof ledger records changed counts and changed tickers without guessing.

### Price Coverage: ARES

- Workflow mode: `dry_run_first`
- Source/freshness context: Provider-assisted price rows can be planned at scale; dry-run and capped review come first. Freshness: current: Readiness artifacts are current relative to watched source files.
- Dry-run command: `make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N=10 PROVIDER=yahoo`
- Capped execution command: `make price-refresh-loop MAX_CANDIDATES=3500 TOP_N=10 PROVIDER=yahoo SLEEP_SECONDS=30`
- Validate: `make price-validate`
- Preview: `make price-preview`
- Apply gate: `make price-apply only for reviewed trusted rows`
- Post-run verification: `make readiness && make price-coverage TOP_N=10 && make status-check TOP_N=5`
- Readiness comparison: `make reviewed-batch-compare LANE=prices BATCH_ID=RB-20260613T014434Z REVIEW_DATE=<yyyy-mm-dd>`
- Proof ledger record: `make reviewed-batch-proof-record BATCH_ID="RB-20260613T014434Z" LANE="price_coverage" REVIEW_DATE="<yyyy-mm-dd>" FINAL_OUTCOME="<supported|still_blocked|skipped|excluded>" COMMAND_RUN="<exact reviewed command>" VALIDATION_RESULT="<pass/fail/not_run>" PREVIEW_RESULT="<reviewed/not_run>" APPLY_RESULT="<applied/not_run/skipped>" CHANGED_READINESS_COUNTS="<from reviewed-batch-compare>" CHANGED_TICKERS="<from reviewed-batch-compare>"`
- Expected artifacts: data/prices.csv; data/reports/price_coverage_report.csv; outputs/reviewed_batch_packet.csv
- Rollback checklist: If refreshed prices are incomplete or suspicious, keep generated CSV churn unstaged and restore reviewed local price files from git or the readiness snapshot.
- Do not proceed if: readiness artifacts are missing or stale; source proof is unavailable; validation fails; preview shows unexpected rows; rejected-row reports contain unresolved rows; the operator cannot identify changed source files

Lane proof instructions:
- Record pre-run price-ready, momentum-ready, liquidity, and correlation counts before any refresh.
- Use dry-run output to cap scope; do not treat provider availability as reviewed data.
- After execution, rerun readiness and compare changed readiness counts before keeping artifacts.
- Use make reviewed-batch-compare after make readiness so the proof ledger records changed counts and changed tickers without guessing.

### Price Coverage: ARHS

- Workflow mode: `dry_run_first`
- Source/freshness context: Provider-assisted price rows can be planned at scale; dry-run and capped review come first. Freshness: current: Readiness artifacts are current relative to watched source files.
- Dry-run command: `make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N=10 PROVIDER=yahoo`
- Capped execution command: `make price-refresh-loop MAX_CANDIDATES=3500 TOP_N=10 PROVIDER=yahoo SLEEP_SECONDS=30`
- Validate: `make price-validate`
- Preview: `make price-preview`
- Apply gate: `make price-apply only for reviewed trusted rows`
- Post-run verification: `make readiness && make price-coverage TOP_N=10 && make status-check TOP_N=5`
- Readiness comparison: `make reviewed-batch-compare LANE=prices BATCH_ID=RB-20260613T014434Z REVIEW_DATE=<yyyy-mm-dd>`
- Proof ledger record: `make reviewed-batch-proof-record BATCH_ID="RB-20260613T014434Z" LANE="price_coverage" REVIEW_DATE="<yyyy-mm-dd>" FINAL_OUTCOME="<supported|still_blocked|skipped|excluded>" COMMAND_RUN="<exact reviewed command>" VALIDATION_RESULT="<pass/fail/not_run>" PREVIEW_RESULT="<reviewed/not_run>" APPLY_RESULT="<applied/not_run/skipped>" CHANGED_READINESS_COUNTS="<from reviewed-batch-compare>" CHANGED_TICKERS="<from reviewed-batch-compare>"`
- Expected artifacts: data/prices.csv; data/reports/price_coverage_report.csv; outputs/reviewed_batch_packet.csv
- Rollback checklist: If refreshed prices are incomplete or suspicious, keep generated CSV churn unstaged and restore reviewed local price files from git or the readiness snapshot.
- Do not proceed if: readiness artifacts are missing or stale; source proof is unavailable; validation fails; preview shows unexpected rows; rejected-row reports contain unresolved rows; the operator cannot identify changed source files

Lane proof instructions:
- Record pre-run price-ready, momentum-ready, liquidity, and correlation counts before any refresh.
- Use dry-run output to cap scope; do not treat provider availability as reviewed data.
- After execution, rerun readiness and compare changed readiness counts before keeping artifacts.
- Use make reviewed-batch-compare after make readiness so the proof ledger records changed counts and changed tickers without guessing.

### Price Coverage: ARKO

- Workflow mode: `dry_run_first`
- Source/freshness context: Provider-assisted price rows can be planned at scale; dry-run and capped review come first. Freshness: current: Readiness artifacts are current relative to watched source files.
- Dry-run command: `make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N=10 PROVIDER=yahoo`
- Capped execution command: `make price-refresh-loop MAX_CANDIDATES=3500 TOP_N=10 PROVIDER=yahoo SLEEP_SECONDS=30`
- Validate: `make price-validate`
- Preview: `make price-preview`
- Apply gate: `make price-apply only for reviewed trusted rows`
- Post-run verification: `make readiness && make price-coverage TOP_N=10 && make status-check TOP_N=5`
- Readiness comparison: `make reviewed-batch-compare LANE=prices BATCH_ID=RB-20260613T014434Z REVIEW_DATE=<yyyy-mm-dd>`
- Proof ledger record: `make reviewed-batch-proof-record BATCH_ID="RB-20260613T014434Z" LANE="price_coverage" REVIEW_DATE="<yyyy-mm-dd>" FINAL_OUTCOME="<supported|still_blocked|skipped|excluded>" COMMAND_RUN="<exact reviewed command>" VALIDATION_RESULT="<pass/fail/not_run>" PREVIEW_RESULT="<reviewed/not_run>" APPLY_RESULT="<applied/not_run/skipped>" CHANGED_READINESS_COUNTS="<from reviewed-batch-compare>" CHANGED_TICKERS="<from reviewed-batch-compare>"`
- Expected artifacts: data/prices.csv; data/reports/price_coverage_report.csv; outputs/reviewed_batch_packet.csv
- Rollback checklist: If refreshed prices are incomplete or suspicious, keep generated CSV churn unstaged and restore reviewed local price files from git or the readiness snapshot.
- Do not proceed if: readiness artifacts are missing or stale; source proof is unavailable; validation fails; preview shows unexpected rows; rejected-row reports contain unresolved rows; the operator cannot identify changed source files

Lane proof instructions:
- Record pre-run price-ready, momentum-ready, liquidity, and correlation counts before any refresh.
- Use dry-run output to cap scope; do not treat provider availability as reviewed data.
- After execution, rerun readiness and compare changed readiness counts before keeping artifacts.
- Use make reviewed-batch-compare after make readiness so the proof ledger records changed counts and changed tickers without guessing.

### Price Coverage: ARKR

- Workflow mode: `dry_run_first`
- Source/freshness context: Provider-assisted price rows can be planned at scale; dry-run and capped review come first. Freshness: current: Readiness artifacts are current relative to watched source files.
- Dry-run command: `make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N=10 PROVIDER=yahoo`
- Capped execution command: `make price-refresh-loop MAX_CANDIDATES=3500 TOP_N=10 PROVIDER=yahoo SLEEP_SECONDS=30`
- Validate: `make price-validate`
- Preview: `make price-preview`
- Apply gate: `make price-apply only for reviewed trusted rows`
- Post-run verification: `make readiness && make price-coverage TOP_N=10 && make status-check TOP_N=5`
- Readiness comparison: `make reviewed-batch-compare LANE=prices BATCH_ID=RB-20260613T014434Z REVIEW_DATE=<yyyy-mm-dd>`
- Proof ledger record: `make reviewed-batch-proof-record BATCH_ID="RB-20260613T014434Z" LANE="price_coverage" REVIEW_DATE="<yyyy-mm-dd>" FINAL_OUTCOME="<supported|still_blocked|skipped|excluded>" COMMAND_RUN="<exact reviewed command>" VALIDATION_RESULT="<pass/fail/not_run>" PREVIEW_RESULT="<reviewed/not_run>" APPLY_RESULT="<applied/not_run/skipped>" CHANGED_READINESS_COUNTS="<from reviewed-batch-compare>" CHANGED_TICKERS="<from reviewed-batch-compare>"`
- Expected artifacts: data/prices.csv; data/reports/price_coverage_report.csv; outputs/reviewed_batch_packet.csv
- Rollback checklist: If refreshed prices are incomplete or suspicious, keep generated CSV churn unstaged and restore reviewed local price files from git or the readiness snapshot.
- Do not proceed if: readiness artifacts are missing or stale; source proof is unavailable; validation fails; preview shows unexpected rows; rejected-row reports contain unresolved rows; the operator cannot identify changed source files

Lane proof instructions:
- Record pre-run price-ready, momentum-ready, liquidity, and correlation counts before any refresh.
- Use dry-run output to cap scope; do not treat provider availability as reviewed data.
- After execution, rerun readiness and compare changed readiness counts before keeping artifacts.
- Use make reviewed-batch-compare after make readiness so the proof ledger records changed counts and changed tickers without guessing.

### Price Coverage: AROW

- Workflow mode: `dry_run_first`
- Source/freshness context: Provider-assisted price rows can be planned at scale; dry-run and capped review come first. Freshness: current: Readiness artifacts are current relative to watched source files.
- Dry-run command: `make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N=10 PROVIDER=yahoo`
- Capped execution command: `make price-refresh-loop MAX_CANDIDATES=3500 TOP_N=10 PROVIDER=yahoo SLEEP_SECONDS=30`
- Validate: `make price-validate`
- Preview: `make price-preview`
- Apply gate: `make price-apply only for reviewed trusted rows`
- Post-run verification: `make readiness && make price-coverage TOP_N=10 && make status-check TOP_N=5`
- Readiness comparison: `make reviewed-batch-compare LANE=prices BATCH_ID=RB-20260613T014434Z REVIEW_DATE=<yyyy-mm-dd>`
- Proof ledger record: `make reviewed-batch-proof-record BATCH_ID="RB-20260613T014434Z" LANE="price_coverage" REVIEW_DATE="<yyyy-mm-dd>" FINAL_OUTCOME="<supported|still_blocked|skipped|excluded>" COMMAND_RUN="<exact reviewed command>" VALIDATION_RESULT="<pass/fail/not_run>" PREVIEW_RESULT="<reviewed/not_run>" APPLY_RESULT="<applied/not_run/skipped>" CHANGED_READINESS_COUNTS="<from reviewed-batch-compare>" CHANGED_TICKERS="<from reviewed-batch-compare>"`
- Expected artifacts: data/prices.csv; data/reports/price_coverage_report.csv; outputs/reviewed_batch_packet.csv
- Rollback checklist: If refreshed prices are incomplete or suspicious, keep generated CSV churn unstaged and restore reviewed local price files from git or the readiness snapshot.
- Do not proceed if: readiness artifacts are missing or stale; source proof is unavailable; validation fails; preview shows unexpected rows; rejected-row reports contain unresolved rows; the operator cannot identify changed source files

Lane proof instructions:
- Record pre-run price-ready, momentum-ready, liquidity, and correlation counts before any refresh.
- Use dry-run output to cap scope; do not treat provider availability as reviewed data.
- After execution, rerun readiness and compare changed readiness counts before keeping artifacts.
- Use make reviewed-batch-compare after make readiness so the proof ledger records changed counts and changed tickers without guessing.

### Price Coverage: ARQ

- Workflow mode: `dry_run_first`
- Source/freshness context: Provider-assisted price rows can be planned at scale; dry-run and capped review come first. Freshness: current: Readiness artifacts are current relative to watched source files.
- Dry-run command: `make price-refresh-loop DRY_RUN=1 MAX_CANDIDATES=3500 TOP_N=10 PROVIDER=yahoo`
- Capped execution command: `make price-refresh-loop MAX_CANDIDATES=3500 TOP_N=10 PROVIDER=yahoo SLEEP_SECONDS=30`
- Validate: `make price-validate`
- Preview: `make price-preview`
- Apply gate: `make price-apply only for reviewed trusted rows`
- Post-run verification: `make readiness && make price-coverage TOP_N=10 && make status-check TOP_N=5`
- Readiness comparison: `make reviewed-batch-compare LANE=prices BATCH_ID=RB-20260613T014434Z REVIEW_DATE=<yyyy-mm-dd>`
- Proof ledger record: `make reviewed-batch-proof-record BATCH_ID="RB-20260613T014434Z" LANE="price_coverage" REVIEW_DATE="<yyyy-mm-dd>" FINAL_OUTCOME="<supported|still_blocked|skipped|excluded>" COMMAND_RUN="<exact reviewed command>" VALIDATION_RESULT="<pass/fail/not_run>" PREVIEW_RESULT="<reviewed/not_run>" APPLY_RESULT="<applied/not_run/skipped>" CHANGED_READINESS_COUNTS="<from reviewed-batch-compare>" CHANGED_TICKERS="<from reviewed-batch-compare>"`
- Expected artifacts: data/prices.csv; data/reports/price_coverage_report.csv; outputs/reviewed_batch_packet.csv
- Rollback checklist: If refreshed prices are incomplete or suspicious, keep generated CSV churn unstaged and restore reviewed local price files from git or the readiness snapshot.
- Do not proceed if: readiness artifacts are missing or stale; source proof is unavailable; validation fails; preview shows unexpected rows; rejected-row reports contain unresolved rows; the operator cannot identify changed source files

Lane proof instructions:
- Record pre-run price-ready, momentum-ready, liquidity, and correlation counts before any refresh.
- Use dry-run output to cap scope; do not treat provider availability as reviewed data.
- After execution, rerun readiness and compare changed readiness counts before keeping artifacts.
- Use make reviewed-batch-compare after make readiness so the proof ledger records changed counts and changed tickers without guessing.

## Review Checklist

- Confirm readiness artifacts are current or run `make readiness`.
- Confirm the dry run matches the intended lane and capped scope.
- Confirm source files are trusted and local.
- For mutating workflows, run validate -> preview -> apply only after review.
- Check rejected-row reports before treating any lane as supported.
- Run post-run readiness verification and record supported, still_blocked, skipped, or excluded honestly.
- Record changed readiness counts and changed tickers only when the before/after proof supports them.
- Classify generated CSV/JSON artifacts as kept evidence or excluded local churn before staging.

## Proof Row Template

Ledger path suggestion: `data/reviewed_batch_proofs.csv` or the existing reviewed data proof ledger.
Final outcome options: supported, still_blocked, skipped, excluded.

- batch_id:
- lane:
- scope:
- tickers:
- pre_run_readiness_snapshot:
- command_run:
- validation_result:
- preview_result:
- apply_result:
- post_run_readiness_snapshot:
- changed_readiness_counts:
- changed_tickers:
- reviewer:
- review_date:
- source_files:
- generated_artifacts_reviewed:
- final_outcome:
- notes:

CSV template row:

`RB-20260613T014434Z,price_coverage,prices,top 10,make readiness-snapshot or saved readiness counts before command,<copy exact command>,<pass/fail/not_applicable>,<reviewed rows / no unexpected rows / not_applicable>,<not_run/applied/skipped>,make readiness && lane proof command,<before -> after counts, or none>,<tickers changed, or none>,<name>,<YYYY-MM-DD>,<trusted local source files reviewed>,<CSV/JSON artifacts kept/excluded>,supported|still_blocked|skipped|excluded,<source proof, blockers, rollback notes>`

## Guardrails

- Do not fabricate prices, fundamentals, peers, earnings, analyst estimates, valuation inputs, or recommendations.
- Do not treat a high unlock-impact lane as a security ranking.
- Do not stage broad generated CSV/JSON churn unless it is intentionally reviewed evidence.
- Do not proceed when source proof, validation, preview, rejected-row checks, or rollback path is unclear.
